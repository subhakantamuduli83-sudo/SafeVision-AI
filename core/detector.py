import cv2
import numpy as np
import time
import os
from datetime import datetime
from core.database import log_incident
from core.alarm import alarm_manager

SNAPSHOT_DIR = os.path.join("static", "incidents")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

class SafetyDetector:
    """AI Engine for Safety Gear Compliance (PPE) and Fire/Smoke Detection."""

    def __init__(self, model_path: str = "yolov8n.pt", conf_thresh: float = 0.40):
        self.conf_thresh = conf_thresh
        self.model_path = model_path
        self.model = None
        self.custom_ppe_model = False
        self.last_snapshot_time = {}
        self.snapshot_cooldown = 4.0 # Seconds between saving snapshots for same violation

        self._load_model()

    def _load_model(self):
        """Loads YOLOv8 model. Automatically detects if custom PPE weights are provided."""
        try:
            from ultralytics import YOLO
            
            # Check if custom fine-tuned weights exist in workspace
            if os.path.exists("best.pt"):
                print("[Detector] Loading custom trained PPE weights: best.pt")
                self.model = YOLO("best.pt")
                self.custom_ppe_model = True
            elif os.path.exists("ppe_yolov8.pt"):
                print("[Detector] Loading PPE model: ppe_yolov8.pt")
                self.model = YOLO("ppe_yolov8.pt")
                self.custom_ppe_model = True
            else:
                print(f"[Detector] Loading base YOLO model: {self.model_path}")
                self.model = YOLO(self.model_path)
                self.custom_ppe_model = False
                
        except Exception as e:
            print(f"[Detector Error] Failed to load YOLO: {e}")
            self.model = None

    def _detect_fire_smoke_hsv(self, frame):
        """Detects fire and smoke using dynamic color spectrum and high-energy contours."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Fire color range (bright yellow/orange/red flame tones)
        lower_fire = np.array([5, 120, 200], dtype=np.uint8)
        upper_fire = np.array([30, 255, 255], dtype=np.uint8)
        
        # Red spectrum wraps around 0 and 180
        lower_red2 = np.array([170, 120, 200], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower_fire, upper_fire)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        fire_mask = cv2.bitwise_or(mask1, mask2)
        
        # Blur & filter noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_OPEN, kernel)
        fire_mask = cv2.dilate(fire_mask, kernel, iterations=2)

        contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fire_boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1200: # Minimum flame area threshold
                x, y, w, h = cv2.boundingRect(cnt)
                fire_boxes.append((x, y, x + w, y + h, area))
                
        return fire_boxes

    def _analyze_worker_ppe_heuristics(self, frame, person_box):
        """Analyzes upper-body and head regions for helmet & high-vis vest compliance."""
        px1, py1, px2, py2 = person_box
        p_h = py2 - py1
        p_w = px2 - px1
        
        if p_h < 40 or p_w < 20:
            return {"helmet": True, "vest": True, "status": "UNKNOWN"}

        # Extract Head Region (Top 25% of person)
        head_y2 = py1 + int(p_h * 0.25)
        head_roi = frame[py1:head_y2, px1:px2]
        
        # Extract Torso Region (20% to 65% of person)
        torso_y1 = py1 + int(p_h * 0.20)
        torso_y2 = py1 + int(p_h * 0.65)
        torso_roi = frame[torso_y1:torso_y2, px1:px2]

        has_helmet = False
        has_vest = False

        # 1. Helmet check (detects hardhat colors: Yellow, White, Orange, Blue, Red hardhats)
        if head_roi.size > 0:
            hsv_head = cv2.cvtColor(head_roi, cv2.COLOR_BGR2HSV)
            # High-visibility hardhat colors
            mask_yellow = cv2.inRange(hsv_head, np.array([15, 70, 120]), np.array([35, 255, 255]))
            mask_orange = cv2.inRange(hsv_head, np.array([5, 80, 120]), np.array([18, 255, 255]))
            mask_white = cv2.inRange(hsv_head, np.array([0, 0, 180]), np.array([180, 50, 255]))
            mask_blue = cv2.inRange(hsv_head, np.array([90, 80, 80]), np.array([130, 255, 255]))
            
            combined_helmet = cv2.bitwise_or(mask_yellow, mask_orange)
            combined_helmet = cv2.bitwise_or(combined_helmet, mask_white)
            combined_helmet = cv2.bitwise_or(combined_helmet, mask_blue)
            
            helmet_pixels = cv2.countNonZero(combined_helmet)
            total_head_pixels = head_roi.shape[0] * head_roi.shape[1]
            if (helmet_pixels / total_head_pixels) > 0.12:
                has_helmet = True

        # 2. Safety Vest check (Neon Green, Fluorescent Yellow, Bright Orange)
        if torso_roi.size > 0:
            hsv_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2HSV)
            mask_neon_green = cv2.inRange(hsv_torso, np.array([30, 80, 100]), np.array([75, 255, 255]))
            mask_neon_orange = cv2.inRange(hsv_torso, np.array([5, 100, 120]), np.array([25, 255, 255]))
            
            combined_vest = cv2.bitwise_or(mask_neon_green, mask_neon_orange)
            vest_pixels = cv2.countNonZero(combined_vest)
            total_torso_pixels = torso_roi.shape[0] * torso_roi.shape[1]
            if (vest_pixels / total_torso_pixels) > 0.14:
                has_vest = True

        return {
            "helmet": has_helmet,
            "vest": has_vest,
            "compliant": has_helmet and has_vest
        }

    def process_frame(self, frame, zone_id: str = "Zone 1 - Main Floor"):
        """Processes a single video frame, draws bounding boxes, triggers audio and logs incidents."""
        if frame is None:
            return None, {}

        annotated_frame = frame.copy()
        h, w, _ = frame.shape

        stats = {
            "total_workers": 0,
            "compliant_workers": 0,
            "violations_count": 0,
            "fire_detected": False,
            "active_violations": [],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        # 1. Fire and Smoke Detection
        fire_boxes = self._detect_fire_smoke_hsv(frame)
        if fire_boxes:
            stats["fire_detected"] = True
            for (fx1, fy1, fx2, fy2, area) in fire_boxes:
                # Draw pulsing fire hazard box
                cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), (0, 69, 255), 3)
                cv2.putText(annotated_frame, "CRITICAL: FIRE HAZARD DETECTED", (fx1, max(30, fy1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Trigger Alarm & Log
            alarm_manager.trigger_alert("FIRE", f"Emergency! Fire hazard detected in {zone_id}!", severity="CRITICAL")
            self._save_incident_snapshot(annotated_frame, zone_id, "Fire Hazard", "CRITICAL", "Open flame / fire signature detected")

        # 2. Worker & PPE Detection
        if self.model is not None:
            try:
                results = self.model(frame, conf=self.conf_thresh, verbose=False)[0]
                
                # If using dedicated multi-class PPE model
                if self.custom_ppe_model:
                    # Parse custom classes (e.g. 0: 'helmet', 1: 'vest', 2: 'no-helmet', 3: 'no-vest', 4: 'person')
                    for box in results.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = results.names.get(cls_id, str(cls_id))
                        conf = float(box.conf[0])
                        bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                        
                        color = (0, 255, 0) if "no" not in cls_name.lower() else (0, 0, 255)
                        cv2.rectangle(annotated_frame, (bx1, by1), (bx2, by2), color, 2)
                        cv2.putText(annotated_frame, f"{cls_name} {conf:.2f}", (bx1, max(20, by1 - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        if "no" in cls_name.lower():
                            stats["violations_count"] += 1
                            stats["active_violations"].append(cls_name)
                            alarm_manager.trigger_alert("PPE_VIOLATION", f"Warning: {cls_name} in {zone_id}", severity="HIGH")

                else:
                    # Using base YOLO (detects Person class 0) + Spatial PPE Heuristic Engine
                    person_boxes = []
                    for box in results.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        if cls_id == 0 and conf >= self.conf_thresh: # Person
                            bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                            # Clamp within frame bounds
                            bx1, by1 = max(0, bx1), max(0, by1)
                            bx2, by2 = min(w, bx2), min(h, by2)
                            person_boxes.append((bx1, by1, bx2, by2, conf))

                    stats["total_workers"] = len(person_boxes)

                    for (px1, py1, px2, py2, p_conf) in person_boxes:
                        ppe_res = self._analyze_worker_ppe_heuristics(frame, (px1, py1, px2, py2))
                        
                        is_compliant = ppe_res["compliant"]
                        missing_items = []
                        if not ppe_res["helmet"]:
                            missing_items.append("No Helmet")
                        if not ppe_res["vest"]:
                            missing_items.append("No Vest")

                        if is_compliant:
                            stats["compliant_workers"] += 1
                            box_color = (0, 255, 0) # Green
                            status_label = f"SAFE WORKER [OK] ({p_conf:.2f})"
                        else:
                            stats["violations_count"] += 1
                            box_color = (0, 0, 255) # Red
                            v_desc = " & ".join(missing_items)
                            status_label = f"VIOLATION: {v_desc}"
                            stats["active_violations"].append(v_desc)

                            # Trigger Speaker Voice & Siren Alarm
                            alarm_msg = f"Alert! Worker detected with {v_desc} in {zone_id}"
                            alarm_manager.trigger_alert(f"PPE_{v_desc}", alarm_msg, severity="HIGH")
                            
                            # Snapshot & Database Log
                            self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH", f"Worker missing: {v_desc}")

                        # Draw worker box
                        cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), box_color, 2)
                        # Header badge
                        cv2.rectangle(annotated_frame, (px1, max(0, py1 - 25)), (px2, py1), box_color, -1)
                        cv2.putText(annotated_frame, status_label, (px1 + 5, py1 - 7),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            except Exception as e:
                print(f"[Detector Inference Error] {e}")

        # Compute Compliance Rate %
        if stats["total_workers"] > 0:
            stats["compliance_rate"] = round((stats["compliant_workers"] / stats["total_workers"]) * 100, 1)
        else:
            stats["compliance_rate"] = 100.0

        # Draw HUD info overlay on top left
        self._draw_hud(annotated_frame, stats, zone_id)

        return annotated_frame, stats

    def _draw_hud(self, frame, stats, zone_id):
        """Draws top HUD overlay for live camera view."""
        # Top banner background
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (20, 20, 20), -1)
        
        # Zone & Live indicator
        cv2.circle(frame, (20, 20), 6, (0, 255, 0), -1)
        cv2.putText(frame, f"LIVE FEED: {zone_id}", (35, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Worker count & compliance rate
        comp_color = (0, 255, 0) if stats["compliance_rate"] >= 80 else (0, 165, 255) if stats["compliance_rate"] >= 50 else (0, 0, 255)
        text_stats = f"Workers: {stats['total_workers']} | Compliance: {stats['compliance_rate']}% | Violations: {stats['violations_count']}"
        cv2.putText(frame, text_stats, (frame.shape[1] - 440, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, comp_color, 1)

    def _save_incident_snapshot(self, frame, zone, incident_type, severity, details):
        """Throttles and saves a snapshot image, then records to DB."""
        now = time.time()
        last_time = self.last_snapshot_time.get(incident_type, 0)
        
        if (now - last_time) >= self.snapshot_cooldown:
            self.last_snapshot_time[incident_type] = now
            filename = f"incident_{int(now)}.jpg"
            rel_path = os.path.join("static", "incidents", filename)
            cv2.imwrite(rel_path, frame)
            
            # Log in SQLite Database
            log_incident(zone, incident_type, severity, details, snapshot_path=f"/static/incidents/{filename}")
            print(f"[Snapshot Logged] {incident_type} -> {rel_path}")
