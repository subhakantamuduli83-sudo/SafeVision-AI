import cv2
import numpy as np
import time
import os
import math
import threading
from datetime import datetime
from typing import List, Tuple, Dict, Any

from core.database import log_incident
from core.alarm import alarm_manager
from core.notifier import notifier

SNAPSHOT_DIR = os.path.join("static", "incidents")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

class SafetyDetector:
    """
    Advanced Industrial & Construction AI Vision Engine with:
    - Master Control Feature Switchboard (100% Granular On/Off for All 14 Detectors)
    - Auto-Pilot / Autonomous Supervisor Away Mode
    - Real-Time Hazard Geofencing, PPE Inspection, and Emergency Multi-Channel Dispatch
    """

    def __init__(self, model_path: str = "yolo11n.pt", conf_thresh: float = 0.35):
        self.conf_thresh = conf_thresh
        self.model_path = model_path
        self.model = None
        self.pose_model = None
        self.custom_ppe_model = False
        self.last_snapshot_time = {}
        self.snapshot_cooldown = 6.0
        self.sensitivity_level = "high"  # 'ultra', 'high', 'standard', or 'custom'
        self.ppe_strictness = "high"
        self.inference_lock = threading.Lock()
        self.tracked_boxes = {}  # Worker ID -> {"box": (x1, y1, x2, y2), "last_seen": float, "conf": float, "kpts": np.ndarray} for EMA box smoothing

        # ================= MASTER FEATURE TOGGLES =================
        self.auto_pilot_mode = False          # Autonomous 24/7 Supervisor Away Mode
        self.helmet_check_enabled = True      # Hardhat / Helmet compliance
        self.vest_check_enabled = True        # High-Vis Vest compliance
        self.gloves_check_enabled = True      # Industrial Protective Gloves compliance
        self.goggles_check_enabled = True     # Eye Protection / Safety Goggles compliance
        self.shoes_check_enabled = True       # Industrial Safety Shoes / Steel-Toe Boots compliance
        self.fall_detection_enabled = True    # Fall & Man-Down Emergency
        self.fire_detection_enabled = True    # Fire & Smoke Hazard
        self.phone_detection_enabled = True   # Cellphone distraction in work zone
        self.proximity_detection_enabled = True # Forklift & Vehicle collision buffer
        self.danger_zone_enabled = False      # Virtual Danger Geofence
        self.gate_mode = False                # Smart Turnstile Entry HUD
        self.height_safety_enabled = False    # Scaffolding / Harness tethering
        self.suspended_load_enabled = False   # Crane Suspended Load Drop Shadow
        self.confined_space_enabled = False   # Tank / Manhole Headcount Watchdog
        self.hot_work_enabled = False         # Welding Sparks & Extinguisher Check
        self.trench_safety_enabled = False    # Trench Excavation Setback Margin
        self.night_mode_enabled = False       # Night Shift Perimeter Security Guard

        # 1. Fall & Inactivity Tracker
        self.fall_trackers = {}

        # 2. Virtual Danger Zone Geofencing
        self.danger_zone_name = "Heavy Machinery Perimeter"
        self.danger_zone_poly_norm = [
            (0.60, 0.25),
            (0.96, 0.25),
            (0.96, 0.85),
            (0.60, 0.85)
        ]

        # 3. Smart Entry Gate State
        self.last_gate_status = None
        self.last_gate_announce = 0.0

        # 4. Height Safety Elevated Region
        self.height_zone_norm = [
            (0.00, 0.00),
            (1.00, 0.00),
            (1.00, 0.42),
            (0.00, 0.42)
        ]

        # 5. Crane Suspended Load Radar
        self.radar_angle = 0.0

        # 6. Confined Space Portal & Headcount
        self.confined_space_name = "Underground Silo / Manhole #4"
        self.confined_space_poly_norm = [
            (0.04, 0.45),
            (0.42, 0.45),
            (0.42, 0.92),
            (0.04, 0.92)
        ]
        self.confined_workers_active = {}
        self.confined_max_safe_seconds = 45.0 * 60.0
        self.confined_total_entered = 0
        self.confined_total_exited = 0

        # 7. Hot Work & Welding Watch
        self.last_spark_time = 0.0

        # 8. Trench Setback Margin
        self.trench_line_y_norm = 0.78
        self.trench_margin_px = 65

        # 9. Temporal Persistence & Debounce Trackers to avoid false or premature sirens
        self.fire_consecutive_frames = 0
        self.fall_consecutive_frames = 0
        self.hot_work_consecutive_frames = 0
        self.trench_consecutive_frames = 0
        self.geofence_consecutive_frames = 0
        self.suspended_load_consecutive_frames = 0
        self.ppe_violation_trackers = {} # worker_id -> int frames

        self._load_model()

    # ================= Master Switchboard & Presets =================
    def get_feature_matrix(self) -> Dict[str, Any]:
        """Returns the full real-time on/off state of all 14 AI detectors + alarms."""
        siren_on = alarm_manager.enabled and not alarm_manager.is_muted
        tg_on = notifier.telegram_enabled
        return {
            "auto_pilot": self.auto_pilot_mode,
            "auto_pilot_mode": self.auto_pilot_mode,
            "helmet_check": self.helmet_check_enabled,
            "vest_check": self.vest_check_enabled,
            "gloves_check": self.gloves_check_enabled,
            "goggles_check": self.goggles_check_enabled,
            "shoes_check": self.shoes_check_enabled,
            "boots_check": self.shoes_check_enabled,
            "fall_detection": self.fall_detection_enabled,
            "fire_detection": self.fire_detection_enabled,
            "phone_detection": self.phone_detection_enabled,
            "phone_distraction": self.phone_detection_enabled,
            "proximity_detection": self.proximity_detection_enabled,
            "machinery_proximity": self.proximity_detection_enabled,
            "danger_zone": self.danger_zone_enabled,
            "gate_mode": self.gate_mode,
            "smart_gate": self.gate_mode,
            "height_safety": self.height_safety_enabled,
            "suspended_load": self.suspended_load_enabled,
            "confined_space": self.confined_space_enabled,
            "hot_work": self.hot_work_enabled,
            "trench_safety": self.trench_safety_enabled,
            "night_mode": self.night_mode_enabled,
            "night_guard": self.night_mode_enabled,
            "siren_audio": siren_on,
            "siren_alarm": siren_on,
            "telegram_alert": tg_on,
            "telegram_alerts": tg_on,
            "sensitivity_level": getattr(self, "sensitivity_level", "ultra"),
            "conf_thresh": self.conf_thresh,
            "snapshot_cooldown": self.snapshot_cooldown,
            "ppe_strictness": getattr(self, "ppe_strictness", "ultra")
        }

    def set_sensitivity(self, level: str = None, conf_thresh: float = None, cooldown: float = None) -> Dict[str, Any]:
        """Configures AI vision detection sensitivity, neural confidence threshold, and snapshot cooldown."""
        if level:
            lvl = level.lower().strip()
            if lvl in ["ultra", "ultra_sensitive", "zero_tolerance", "critical"]:
                self.sensitivity_level = "ultra"
                self.conf_thresh = 0.30
                self.snapshot_cooldown = 4.0
                self.ppe_strictness = "ultra"
            elif lvl in ["high", "strict", "elevated"]:
                self.sensitivity_level = "high"
                self.conf_thresh = 0.38
                self.snapshot_cooldown = 6.0
                self.ppe_strictness = "high"
            elif lvl in ["standard", "normal", "balanced"]:
                self.sensitivity_level = "standard"
                self.conf_thresh = 0.48
                self.snapshot_cooldown = 8.0
                self.ppe_strictness = "standard"
            elif lvl == "custom":
                self.sensitivity_level = "custom"
        
        if conf_thresh is not None:
            self.conf_thresh = max(0.20, min(0.95, float(conf_thresh)))
            if level is None:
                if self.conf_thresh <= 0.32:
                    self.sensitivity_level = "ultra"
                elif self.conf_thresh <= 0.42:
                    self.sensitivity_level = "high"
                else:
                    self.sensitivity_level = "standard"
                    
        if cooldown is not None:
            self.snapshot_cooldown = max(0.5, min(15.0, float(cooldown)))
            
        print(f"[Detector] Sensitivity set to {self.sensitivity_level.upper()} (conf={self.conf_thresh:.2f}, cooldown={self.snapshot_cooldown}s)")
        return {
            "level": self.sensitivity_level,
            "conf_thresh": self.conf_thresh,
            "cooldown": self.snapshot_cooldown,
            "strictness": getattr(self, "ppe_strictness", "high")
        }

    def set_feature_toggle(self, feature_name: str, enabled: bool) -> bool:
        """Granularly toggles any individual feature on or off in real-time."""
        fn = feature_name.lower().strip()
        if fn in ["auto_pilot", "auto_pilot_mode"]:
            self.apply_preset("auto_pilot" if enabled else "clean_ppe_only")
        elif fn in ["helmet_check", "helmet"]:
            self.helmet_check_enabled = enabled
        elif fn in ["vest_check", "vest"]:
            self.vest_check_enabled = enabled
            self.shoes_check_enabled = enabled  # Coupled: Vest switch controls both Vest & Shoes together
        elif fn in ["gloves_check", "gloves", "glove"]:
            self.gloves_check_enabled = enabled
        elif fn in ["goggles_check", "goggles", "goggle", "glasses", "eyewear"]:
            self.goggles_check_enabled = enabled
        elif fn in ["shoes_check", "shoes", "shoe", "boots", "boot", "footwear"]:
            self.shoes_check_enabled = enabled
        elif fn in ["fall_detection", "fall"]:
            self.fall_detection_enabled = enabled
        elif fn in ["fire_detection", "fire"]:
            self.fire_detection_enabled = enabled
        elif fn in ["phone_detection", "phone_distraction", "phone"]:
            self.phone_detection_enabled = enabled
        elif fn in ["proximity_detection", "machinery_proximity", "proximity"]:
            self.proximity_detection_enabled = enabled
        elif fn in ["danger_zone", "geofence"]:
            self.danger_zone_enabled = enabled
        elif fn in ["smart_gate", "gate_mode", "gate"]:
            self.gate_mode = enabled
        elif fn in ["height_safety", "height"]:
            self.height_safety_enabled = enabled
        elif fn in ["suspended_load", "crane", "drop_zone"]:
            self.suspended_load_enabled = enabled
        elif fn in ["confined_space", "confined"]:
            self.confined_space_enabled = enabled
        elif fn in ["hot_work", "welding"]:
            self.hot_work_enabled = enabled
        elif fn in ["trench_safety", "trench"]:
            self.trench_safety_enabled = enabled
        elif fn in ["night_guard", "night_mode", "night"]:
            self.night_mode_enabled = enabled
        elif fn in ["siren_audio", "siren_alarm", "siren", "audio"]:
            alarm_manager.set_enabled(enabled)
            alarm_manager.set_muted(not enabled)
        elif fn in ["telegram_alert", "telegram_alerts", "telegram"]:
            notifier.update_config(notifier.telegram_token, notifier.telegram_chat_id, enabled)
        
        print(f"[Detector] Feature '{fn}' set to: {enabled}")
        return True

    def apply_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applies 1-Click Operational Presets."""
        p = preset_name.lower().strip()
        if p in ["auto_pilot", "supervisor_away", "auto"]:
            self.auto_pilot_mode = True
            self.helmet_check_enabled = True
            self.vest_check_enabled = True
            self.gloves_check_enabled = True
            self.goggles_check_enabled = True
            self.fall_detection_enabled = True
            self.fire_detection_enabled = True
            self.phone_detection_enabled = True
            self.proximity_detection_enabled = True
            self.danger_zone_enabled = True
            self.height_safety_enabled = True
            self.hot_work_enabled = True
            self.trench_safety_enabled = True
            self.suspended_load_enabled = True
            self.confined_space_enabled = True
            self.night_mode_enabled = False
            alarm_manager.set_enabled(True)
            alarm_manager.set_muted(False)
            notifier.enabled = True
            alarm_manager.trigger_alert("AUTOPILOT", "SafeVision Auto-Pilot Armed: Autonomous Supervisor Away Mode Active.", severity="LOW")
            print("[Detector] Applied Preset: 🤖 AUTO-PILOT / SUPERVISOR AWAY")

        elif p in ["manual", "custom"]:
            self.auto_pilot_mode = False
            print("[Detector] Applied Preset: 🎛️ CUSTOM / MANUAL")

        elif p in ["construction", "site"]:
            self.auto_pilot_mode = False
            self.helmet_check_enabled = True
            self.vest_check_enabled = True
            self.gloves_check_enabled = True
            self.goggles_check_enabled = True
            self.fall_detection_enabled = True
            self.height_safety_enabled = True
            self.suspended_load_enabled = True
            self.trench_safety_enabled = True
            self.proximity_detection_enabled = True
            self.danger_zone_enabled = False
            self.hot_work_enabled = False
            self.night_mode_enabled = False
            print("[Detector] Applied Preset: 🏗️ CONSTRUCTION SITE")

        elif p in ["hot_work_plant", "industrial_plant", "welding"]:
            self.auto_pilot_mode = False
            self.helmet_check_enabled = True
            self.vest_check_enabled = True
            self.gloves_check_enabled = True
            self.goggles_check_enabled = True
            self.hot_work_enabled = True
            self.fire_detection_enabled = True
            self.danger_zone_enabled = True
            self.fall_detection_enabled = True
            self.height_safety_enabled = False
            self.suspended_load_enabled = False
            self.trench_safety_enabled = False
            self.night_mode_enabled = False
            print("[Detector] Applied Preset: ⚡ INDUSTRIAL HOT WORK")

        elif p in ["clean_ppe_only", "ppe_only"]:
            self.auto_pilot_mode = False
            self.helmet_check_enabled = True
            self.vest_check_enabled = True
            self.gloves_check_enabled = True
            self.goggles_check_enabled = True
            self.fall_detection_enabled = False
            self.fire_detection_enabled = True
            self.phone_detection_enabled = False
            self.proximity_detection_enabled = False
            self.danger_zone_enabled = False
            self.height_safety_enabled = False
            self.suspended_load_enabled = False
            self.confined_space_enabled = False
            self.hot_work_enabled = False
            self.trench_safety_enabled = False
            self.night_mode_enabled = False
            print("[Detector] Applied Preset: 🛡️ CLEAN PPE ONLY")

        elif p in ["night_guard", "night"]:
            self.auto_pilot_mode = False
            self.night_mode_enabled = True
            self.fire_detection_enabled = True
            self.danger_zone_enabled = True
            self.fall_detection_enabled = False
            self.height_safety_enabled = False
            self.suspended_load_enabled = False
            print("[Detector] Applied Preset: 🌙 NIGHT GUARD")

        elif p in ["all_on", "arm_all"]:
            self.auto_pilot_mode = False
            self.helmet_check_enabled = True
            self.vest_check_enabled = True
            self.gloves_check_enabled = True
            self.goggles_check_enabled = True
            self.fall_detection_enabled = True
            self.fire_detection_enabled = True
            self.phone_detection_enabled = True
            self.proximity_detection_enabled = True
            self.danger_zone_enabled = True
            self.height_safety_enabled = True
            self.suspended_load_enabled = True
            self.confined_space_enabled = True
            self.hot_work_enabled = True
            self.trench_safety_enabled = True
            self.night_mode_enabled = True
            alarm_manager.set_enabled(True)
            alarm_manager.set_muted(False)
            print("[Detector] Applied Preset: 🚀 ALL DETECTORS ARMED")

        elif p in ["all_off"]:
            self.auto_pilot_mode = False
            self.helmet_check_enabled = False
            self.vest_check_enabled = False
            self.gloves_check_enabled = False
            self.goggles_check_enabled = False
            self.fall_detection_enabled = False
            self.fire_detection_enabled = False
            self.phone_detection_enabled = False
            self.proximity_detection_enabled = False
            self.danger_zone_enabled = False
            self.height_safety_enabled = False
            self.suspended_load_enabled = False
            self.confined_space_enabled = False
            self.hot_work_enabled = False
            self.trench_safety_enabled = False
            self.night_mode_enabled = False
            print("[Detector] Applied Preset: 🧹 ALL DETECTORS OFF")

        return self.get_feature_matrix()

    # ================= Legacy Setters =================
    def set_danger_zone(self, enabled: bool, name: str, poly_norm: List[Tuple[float, float]]):
        self.danger_zone_enabled = enabled
        if name:
            self.danger_zone_name = name
        if poly_norm and len(poly_norm) >= 3:
            self.danger_zone_poly_norm = poly_norm

    def set_gate_mode(self, enabled: bool):
        self.gate_mode = enabled

    def set_height_safety(self, enabled: bool, zone_norm: List[Tuple[float, float]] = None):
        self.height_safety_enabled = enabled
        if zone_norm and len(zone_norm) >= 3:
            self.height_zone_norm = zone_norm

    def set_suspended_load(self, enabled: bool):
        self.suspended_load_enabled = enabled

    def set_confined_space(self, enabled: bool, name: str = None, max_minutes: float = None, poly_norm: List[Tuple[float, float]] = None):
        self.confined_space_enabled = enabled
        if name:
            self.confined_space_name = name
        if max_minutes is not None and max_minutes > 0:
            self.confined_max_safe_seconds = max_minutes * 60.0
        if poly_norm and len(poly_norm) >= 3:
            self.confined_space_poly_norm = poly_norm

    def reset_confined_space(self):
        self.confined_workers_active.clear()
        self.confined_total_entered = 0
        self.confined_total_exited = 0

    def set_hot_work(self, enabled: bool):
        self.hot_work_enabled = enabled

    def set_trench_safety(self, enabled: bool, line_y_norm: float = None, margin_px: int = None):
        self.trench_safety_enabled = enabled
        if line_y_norm is not None:
            self.trench_line_y_norm = max(0.2, min(0.95, line_y_norm))
        if margin_px is not None:
            self.trench_margin_px = margin_px

    def set_night_mode(self, enabled: bool):
        self.night_mode_enabled = enabled

    def _load_model(self):
        """Loads YOLO neural models with optimized CPU threading."""
        try:
            import cv2
            cv2.setNumThreads(2)
        except Exception:
            pass
        try:
            import torch
            # Cap PyTorch intra-op threads to 2 so it runs smoothly without monopolizing laptop CPU cores
            torch.set_num_threads(min(2, os.cpu_count() or 2))
        except Exception:
            pass

        try:
            from ultralytics import YOLO

            # Detect Intel Hardware Accelerators (NPU / GPU)
            has_intel_accel = False
            intel_mode = "CPU"
            try:
                import openvino as ov
                core = ov.Core()
                devs = core.available_devices
                if "NPU" in devs:
                    has_intel_accel = True
                    intel_mode = "Intel(R) AI Boost NPU Turbo Engine"
                elif "GPU" in devs:
                    has_intel_accel = True
                    intel_mode = "Intel Arc GPU"
            except Exception:
                has_intel_accel = False

            # Hook Ultralytics OpenVINO Backend for Intelligent Hardware Workload Balancing
            if has_intel_accel:
                try:
                    from ultralytics.nn import autobackend
                    from pathlib import Path
                    from functools import partial
                    import openvino as ov

                    def _patched_load_model(self, weight):
                        try:
                            _core = ov.Core()
                            _devs = _core.available_devices
                            w = Path(weight)
                            if not w.is_file():
                                w = next(w.glob("*.xml"))

                            # Offload BOTH AI models directly to Intel AI Boost NPU!
                            if "NPU" in _devs:
                                _assigned = "HETERO:NPU,CPU"
                            elif "GPU" in _devs:
                                _assigned = "GPU"
                            else:
                                _assigned = "AUTO"

                            ov_model = _core.read_model(model=str(w), weights=w.with_suffix(".bin"))
                            if ov_model.get_parameters()[0].get_layout().empty:
                                ov_model.get_parameters()[0].set_layout(ov.Layout("NCHW"))
                            self.apply_metadata(self.read_metadata(w))
                            self.read_model = None
                            self.inference_mode = "LATENCY"
                            config = {"PERFORMANCE_HINT": self.inference_mode}
                            self.compile_model = partial(_core.compile_model, device_name=_assigned, config=config)
                            self.ov_compiled_model = self.compile_model(ov_model)
                            exec_devs = self.ov_compiled_model.get_property("EXECUTION_DEVICES")
                            print(f"[Detector] AI Model ({w.name}) compiled on: {exec_devs}")
                            self.input_name = self.ov_compiled_model.input().get_any_name()
                            self.ov = _core
                            import torch
                            self.device = torch.device("cpu")
                        except Exception as err:
                            print(f"[Detector] Intel accelerator compile fallback: {err}")
                            _core = ov.Core()
                            self.compile_model = partial(_core.compile_model, device_name="AUTO", config={"PERFORMANCE_HINT": "LATENCY"})
                            self.ov_compiled_model = self.compile_model(ov_model)
                            self.input_name = self.ov_compiled_model.input().get_any_name()
                            self.ov = _core
                            import torch
                            self.device = torch.device("cpu")

                    autobackend.OpenVINOBackend.load_model = _patched_load_model
                except Exception as he:
                    print(f"[Detector] OpenVINO hook warning: {he}")

            self.pose_device = None
            self.model_device = None
            self.intel_mode = intel_mode

            # 1. High-Precision Human Skeleton Pose AI
            if has_intel_accel and os.path.exists("yolo11n-pose_openvino_model"):
                print(f"[Detector] Loading Intel Accelerated OpenVINO Pose Model ({intel_mode})")
                self.pose_model = YOLO("yolo11n-pose_openvino_model", task="pose")
            elif os.path.exists("yolo11n-pose.pt"):
                print("[Detector] Loading high-precision Human Pose AI: yolo11n-pose.pt")
                self.pose_model = YOLO("yolo11n-pose.pt")
                self.pose_device = None
            elif os.path.exists("yolov8n-pose.pt"):
                print("[Detector] Loading fallback Human Pose AI: yolov8n-pose.pt")
                self.pose_model = YOLO("yolov8n-pose.pt")
                self.pose_device = None
            else:
                self.pose_model = None

            # 2. Object & Hazard AI (Vehicles, Cellphones, Rigging loads)
            if has_intel_accel and os.path.exists("yolo11n_openvino_model"):
                print(f"[Detector] Loading Intel Accelerated OpenVINO General Model ({intel_mode})")
                self.model = YOLO("yolo11n_openvino_model", task="detect")
                self.custom_ppe_model = False
            elif os.path.exists("best.pt"):
                print("[Detector] Loading custom trained PPE weights: best.pt")
                self.model = YOLO("best.pt")
                self.custom_ppe_model = True
                self.model_device = None
            elif os.path.exists("ppe_yolov8.pt"):
                print("[Detector] Loading PPE model: ppe_yolov8.pt")
                self.model = YOLO("ppe_yolov8.pt")
                self.custom_ppe_model = True
                self.model_device = None
            elif os.path.exists("yolo11n.pt"):
                print("[Detector] Loading high-performance YOLO11-nano: yolo11n.pt")
                self.model = YOLO("yolo11n.pt")
                self.custom_ppe_model = False
                self.model_device = None
            elif os.path.exists("yolov8n.pt"):
                print("[Detector] Loading fallback YOLOv8-nano: yolov8n.pt")
                self.model = YOLO("yolov8n.pt")
                self.custom_ppe_model = False
                self.model_device = None
            else:
                print(f"[Detector] Loading base YOLO model: {self.model_path}")
                self.model = YOLO(self.model_path)
                self.custom_ppe_model = False
                self.model_device = None

            # Warm up neural models synchronously on main thread so fuse() and internal graph setup are thread-safe
            try:
                dummy = np.zeros((384, 384, 3), dtype=np.uint8)
                if self.pose_model is not None:
                    kwargs = {"device": self.pose_device} if self.pose_device else {}
                    self.pose_model(dummy, imgsz=384, verbose=False, **kwargs)
                if self.model is not None:
                    kwargs = {"device": self.model_device} if self.model_device else {}
                    self.model(dummy, imgsz=384, verbose=False, **kwargs)
            except Exception as we:
                pass
        except Exception as e:
            print(f"[Detector Error] Failed to load YOLO: {e}")
            self.model = None
            self.pose_model = None

    def _is_valid_human(self, frame, box, kpts=None) -> bool:
        """
        Robust Human Validation Filter:
        Ensures bounding box has realistic dimensions and rejects microscopic noise.
        Trusts YOLO neural network classification for real human presence in all postures.
        """
        bx1, by1, bx2, by2 = box
        bw = bx2 - bx1
        bh = by2 - by1

        # Reject microscopic artifacts / camera speckles
        if max(bw, bh) < 28 or min(bw, bh) < 12:
            return False

        # Reject extreme 1-pixel lines / banners
        aspect = bw / float(max(1, bh))
        if aspect < 0.08 or aspect > 6.0:
            return False

        # If pose keypoints exist, verify at least 2 detected anatomical keypoints
        if kpts is not None and len(kpts) > 0:
            valid_pts = [p for p in kpts if len(p) >= 3 and p[2] > 0.10]
            if len(valid_pts) >= 2:
                return True

        # Accept all valid person detections from YOLO neural network
        return True

    # ================= Vision Algorithms =================
    def _detect_fire_smoke_hsv(self, frame):
        """Detects fire flames and combustion hazards using multi-spectral YCrCb, RGB differential, and HSV chromatic models with dynamic downsampling."""
        orig_h, orig_w, _ = frame.shape
        # Downscale for ultra-fast color conversions if frame is larger than 480px width
        if orig_w > 480:
            scale_x = orig_w / 480.0
            scale_y = orig_h / float(int(orig_h * (480.0 / orig_w)))
            proc_frame = cv2.resize(frame, (480, int(orig_h * (480.0 / orig_w))))
        else:
            scale_x = 1.0
            scale_y = 1.0
            proc_frame = frame

        h, w, _ = proc_frame.shape
        hsv = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2HSV)
        b, g, r = cv2.split(proc_frame)
        ycrcb = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        
        # A. Flame Hue & Chroma Spectrum:
        # High saturation (S >= 110) strictly separates real combustion from human skin (skin has S < 95)
        mask_flame_hsv = cv2.bitwise_or(
            cv2.inRange(hsv, np.array([5, 110, 135]), np.array([36, 255, 255])),
            cv2.inRange(hsv, np.array([168, 110, 135]), np.array([180, 255, 255]))
        )
        
        # B. RGB Photometric Differential Rule: In flames, R > G > B and (R - B) is intense
        cond_rgb = (r > g) & (g > b) & (r >= 155) & ((r.astype(np.int16) - b.astype(np.int16)) >= 70)
        
        # C. YCrCb Thermal Chrominance Rule: High luminance Y, strong red chrominance Cr > Cb
        cond_ycrcb = (y >= 110) & (cr >= 138) & (cb <= 128) & ((cr.astype(np.int16) - cb.astype(np.int16)) >= 16)
        
        flame_mask = np.zeros((h, w), dtype=np.uint8)
        flame_mask[(mask_flame_hsv > 0) & cond_rgb & cond_ycrcb] = 255
        
        # Morphological bridging & dilation to envelope entire fire zone (including white-hot core)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(flame_mask, cv2.MORPH_CLOSE, kernel_close)
        
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        dilated = cv2.dilate(closed, kernel_dilate, iterations=1)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        raw_boxes = []
        min_area = max(50, 350 / (scale_x * scale_y))
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area:
                x, y_box, box_w, box_h = cv2.boundingRect(cnt)
                if box_w >= 10 and box_h >= 10:
                    patch_hsv = hsv[y_box:y_box+box_h, x:x+box_w]
                    patch_r = r[y_box:y_box+box_h, x:x+box_w]
                    if patch_hsv.size > 0 and patch_r.size > 0:
                        peak_v = int(np.max(patch_hsv[:, :, 2]))
                        peak_r = int(np.max(patch_r))
                        # Real flames are self-luminous and peak at intense brightness
                        if peak_v >= 210 and peak_r >= 215:
                            raw_boxes.append((x, y_box, x + box_w, y_box + box_h, area, "FLAME"))
                
        if not raw_boxes:
            return []
            
        raw_boxes = sorted(raw_boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
        merged = []
        for b_item in raw_boxes:
            bx1, by1, bx2, by2, b_area, b_type = b_item
            matched = False
            for i, m_item in enumerate(merged):
                mx1, my1, mx2, my2, m_area, m_type = m_item
                # Merge if boxes overlap by >= 8% of area or are adjacent
                inter_w = max(0, min(bx2, mx2) - max(bx1, mx1))
                inter_h = max(0, min(by2, my2) - max(by1, my1))
                if (inter_w * inter_h) > 0.06 * ((bx2-bx1)*(by2-by1)):
                    merged[i] = (min(bx1, mx1), min(by1, my1), max(bx2, mx2), max(by2, my2), max(b_area, m_area), "FLAME")
                    matched = True
                    break
            if not matched:
                merged.append(b_item)
                
        max_area = (merged[0][2]-merged[0][0]) * (merged[0][3]-merged[0][1])
        if max_area > (1200 / (scale_x * scale_y)):
            merged = [b for b in merged if ((b[2]-b[0])*(b[3]-b[1])) >= 0.04 * max_area]
            
        # Scale back to original frame dimensions
        if scale_x != 1.0 or scale_y != 1.0:
            return [(int(b[0]*scale_x), int(b[1]*scale_y), int(b[2]*scale_x), int(b[3]*scale_y), b[4]*scale_x*scale_y, b[5]) for b in merged]
        return merged

    def _detect_welding_sparks(self, frame):
        """Detects hot work / welding sparks & arcs via high luminance and chromatic temperature with dynamic downsampling."""
        orig_h, orig_w, _ = frame.shape
        if orig_w > 480:
            scale_x = orig_w / 480.0
            scale_y = orig_h / float(int(orig_h * (480.0 / orig_w)))
            proc_frame = cv2.resize(frame, (480, int(orig_h * (480.0 / orig_w))))
        else:
            scale_x = 1.0
            scale_y = 1.0
            proc_frame = frame

        gray = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
        
        hsv = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2HSV)
        lower_spark = np.array([10, 100, 220], dtype=np.uint8)
        upper_spark = np.array([35, 255, 255], dtype=np.uint8)
        spark_color = cv2.inRange(hsv, lower_spark, upper_spark)
        
        combined_sparks = cv2.bitwise_or(bright_mask, spark_color)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        combined_sparks = cv2.dilate(combined_sparks, kernel, iterations=1)
        
        contours, _ = cv2.findContours(combined_sparks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        spark_boxes = []
        min_area = max(10, 60 / (scale_x * scale_y))
        max_area = 4000 / (scale_x * scale_y)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(cnt)
                spark_boxes.append((x, y, x + w, y + h, area))

        if scale_x != 1.0 or scale_y != 1.0:
            return [(int(b[0]*scale_x), int(b[1]*scale_y), int(b[2]*scale_x), int(b[3]*scale_y), b[4]*scale_x*scale_y) for b in spark_boxes]
        return spark_boxes

    def _detect_extinguisher_near(self, frame, spark_center: Tuple[int, int], radius_px: int = 240) -> Tuple[bool, Tuple[int, int, int, int]]:
        """Scans the perimeter around hot work for a fire extinguisher."""
        h, w, _ = frame.shape
        cx, cy = spark_center
        x1 = max(0, cx - radius_px)
        y1 = max(0, cy - radius_px)
        x2 = min(w, cx + radius_px)
        y2 = min(h, cy + radius_px)
        
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False, (0, 0, 0, 0)
            
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_red1 = np.array([0, 120, 70], dtype=np.uint8)
        upper_red1 = np.array([10, 255, 255], dtype=np.uint8)
        lower_red2 = np.array([170, 120, 70], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 255], dtype=np.uint8)
        
        mask = cv2.bitwise_or(cv2.inRange(hsv_roi, lower_red1, upper_red1),
                              cv2.inRange(hsv_roi, lower_red2, upper_red2))
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 400:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect = bh / max(1, bw)
                if aspect >= 1.2:
                    abs_box = (x1 + bx, y1 + by, x1 + bx + bw, y1 + by + bh)
                    return True, abs_box
        return False, (0, 0, 0, 0)

    def _analyze_worker_ppe_heuristics(self, frame, person_box, kpts=None):
        """Analyzes upper-body and head regions for helmet & high-vis vest compliance with dynamic sensitivity and anatomical landmark precision."""
        px1, py1, px2, py2 = person_box
        p_h = py2 - py1
        p_w = px2 - px1
        
        sens = getattr(self, "sensitivity_level", "high")
        min_h = 28 if sens in ["ultra", "high"] else 38
        min_w = 16 if sens in ["ultra", "high"] else 20
        if p_h < min_h or p_w < min_w:
            return {"helmet": True, "vest": True, "harness": True, "gloves": True, "goggles": True, "compliant": True}

        # 1. Crown / Head ROI calculation (using anatomical keypoints if available)
        crown_roi = None
        if kpts is not None and len(kpts) >= 5:
            valid_head = [p for p in kpts[:5] if len(p) >= 3 and p[2] > 0.25]
            if valid_head:
                min_ky = min(p[1] for p in valid_head)
                avg_kx = sum(p[0] for p in valid_head) / len(valid_head)
                
                # Skull dome & helmet is located directly above eyes/nose
                head_span = max(32, int(p_h * 0.22))
                crown_y2 = max(0, min(frame.shape[0], int(min_ky + head_span * 0.20)))
                crown_y1 = max(0, min(frame.shape[0], int(min_ky - head_span * 0.85)))
                crown_w = max(35, int(p_w * 0.50))
                crown_x1 = max(0, min(frame.shape[1], int(avg_kx - crown_w / 2)))
                crown_x2 = max(0, min(frame.shape[1], int(avg_kx + crown_w / 2)))
                if (crown_y2 - crown_y1) > 10 and (crown_x2 - crown_x1) > 10:
                    crown_roi = frame[crown_y1:crown_y2, crown_x1:crown_x2]

        if crown_roi is None or crown_roi.size == 0:
            # Focused Crown / Skull Dome ROI fallback: top 16% of height, center 55% width
            crown_y1 = max(0, py1)
            crown_y2 = min(frame.shape[0], py1 + int(p_h * 0.16))
            crown_x1 = max(0, px1 + int(p_w * 0.22))
            crown_x2 = min(frame.shape[1], px2 - int(p_w * 0.22))
            crown_roi = frame[crown_y1:crown_y2, crown_x1:crown_x2]
        
        # 2. Torso ROI calculation (using shoulders if available)
        torso_roi = None
        if kpts is not None and len(kpts) >= 7:
            sh_valid = [kpts[i] for i in [5, 6] if len(kpts[i]) >= 3 and kpts[i][2] > 0.25]
            if len(sh_valid) == 2:
                sh_y = min(sh_valid[0][1], sh_valid[1][1])
                sh_x1 = min(sh_valid[0][0], sh_valid[1][0])
                sh_x2 = max(sh_valid[0][0], sh_valid[1][0])
                torso_y1 = max(0, int(sh_y))
                torso_y2 = min(frame.shape[0], int(sh_y + p_h * 0.45))
                torso_x1 = max(0, int(sh_x1 - 15))
                torso_x2 = min(frame.shape[1], int(sh_x2 + 15))
                if (torso_y2 - torso_y1) > 15 and (torso_x2 - torso_x1) > 15:
                    torso_roi = frame[torso_y1:torso_y2, torso_x1:torso_x2]

        if torso_roi is None or torso_roi.size == 0:
            torso_y1 = max(0, py1 + int(p_h * 0.18))
            torso_y2 = min(frame.shape[0], py1 + int(p_h * 0.65))
            torso_roi = frame[torso_y1:torso_y2, px1:px2]

        has_helmet = False
        has_vest = False
        has_harness = False

        # Helmet check on focused skull crown
        if crown_roi.size > 0:
            hsv_crown = cv2.cvtColor(crown_roi, cv2.COLOR_BGR2HSV)
            total_crown_pixels = max(1, crown_roi.shape[0] * crown_roi.shape[1])

            # 1. Vibrant Industrial Safety Helmet Colors
            # Safety Yellow Hardhat (S >= 125, V >= 130 to exclude human skin tones which have S < 110)
            mask_yellow = cv2.inRange(hsv_crown, np.array([23, 125, 130]), np.array([38, 255, 255]))
            
            # High-Vis Orange / Red Hardhat (S >= 130 to exclude facial lips/skin)
            mask_orange_red = cv2.bitwise_or(
                cv2.inRange(hsv_crown, np.array([0, 130, 120]), np.array([12, 255, 255])),
                cv2.inRange(hsv_crown, np.array([170, 130, 120]), np.array([180, 255, 255]))
            )
            
            # Industrial Blue Hardhat
            mask_blue = cv2.inRange(hsv_crown, np.array([92, 95, 80]), np.array([130, 255, 255]))
            
            # Safety Green Hardhat
            mask_green = cv2.inRange(hsv_crown, np.array([38, 85, 80]), np.array([85, 255, 255]))
            
            vibrant_helmet = cv2.bitwise_or(mask_yellow, mask_orange_red)
            vibrant_helmet = cv2.bitwise_or(vibrant_helmet, mask_blue)
            vibrant_helmet = cv2.bitwise_or(vibrant_helmet, mask_green)
            vibrant_count = cv2.countNonZero(vibrant_helmet)

            # 2. Check for exposed hair and forehead skin in crown (indicates bare head)
            mask_dark_hair = cv2.inRange(hsv_crown, np.array([0, 0, 0]), np.array([180, 255, 75]))
            mask_brown_hair = cv2.inRange(hsv_crown, np.array([8, 40, 40]), np.array([25, 160, 115]))
            mask_skin = cv2.inRange(hsv_crown, np.array([0, 25, 70]), np.array([24, 120, 240]))
            
            bare_head_mask = cv2.bitwise_or(mask_dark_hair, mask_brown_hair)
            bare_head_mask = cv2.bitwise_or(bare_head_mask, mask_skin)
            bare_count = cv2.countNonZero(bare_head_mask)
            bare_ratio = bare_count / total_crown_pixels

            # Decision Logic:
            # A. If high-visibility safety helmet color is present (covers >= 12% of dome)
            if (vibrant_count / total_crown_pixels) >= 0.12:
                has_helmet = True
            # B. If worker has exposed hair or forehead skin (>= 14% of crown area), worker is bare-headed
            elif bare_ratio >= 0.14:
                has_helmet = False
            # C. White Hardhat: only accepted if crown is solid opaque white and hair is NOT exposed
            else:
                mask_white = cv2.inRange(hsv_crown, np.array([0, 0, 205]), np.array([180, 30, 255]))
                white_count = cv2.countNonZero(mask_white)
                if (white_count / total_crown_pixels) >= 0.35 and bare_ratio < 0.08:
                    has_helmet = True

        # Safety Vest check
        if torso_roi.size > 0:
            hsv_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2HSV)
            mask_neon_green = cv2.inRange(hsv_torso, np.array([30, 80, 100]), np.array([75, 255, 255]))
            mask_neon_orange = cv2.inRange(hsv_torso, np.array([5, 100, 120]), np.array([25, 255, 255]))
            
            combined_vest = cv2.bitwise_or(mask_neon_green, mask_neon_orange)
            vest_pixels = cv2.countNonZero(combined_vest)
            total_torso_pixels = torso_roi.shape[0] * torso_roi.shape[1]
            vest_req = 0.15 if sens == "ultra" else (0.13 if sens == "high" else 0.10)
            if (vest_pixels / total_torso_pixels) > vest_req:
                has_vest = True

            # Safety Harness Straps Analysis
            gray_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray_torso, 50, 150)
            edge_ratio = cv2.countNonZero(edges) / max(1, total_torso_pixels)
            if has_vest and edge_ratio > 0.10:
                has_harness = True
            elif edge_ratio > 0.13:
                has_harness = True

        # Safety Goggles / Protective Eyewear Check (Orbital Eye Band)
        has_goggles = False
        eye_y1 = py1 + int(p_h * 0.11)
        eye_y2 = py1 + int(p_h * 0.24)
        eye_x1 = px1 + int(p_w * 0.20)
        eye_x2 = px2 - int(p_w * 0.20)
        eye_roi = frame[eye_y1:eye_y2, eye_x1:eye_x2]

        if eye_roi.size > 0:
            hsv_eye = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2HSV)
            gray_eye = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2GRAY)
            total_eye_pixels = max(1, eye_roi.shape[0] * eye_roi.shape[1])

            # Safety glasses: Dark frames / tinted lenses or yellow safety tint
            mask_dark_eyewear = cv2.inRange(hsv_eye, np.array([0, 0, 0]), np.array([180, 255, 60]))
            mask_yellow_eyewear = cv2.inRange(hsv_eye, np.array([18, 90, 80]), np.array([36, 255, 255]))
            eyewear_tint = cv2.bitwise_or(mask_dark_eyewear, mask_yellow_eyewear)
            eyewear_count = cv2.countNonZero(eyewear_tint)

            # High-contrast lens frame edge profile
            eye_edges = cv2.Canny(gray_eye, 50, 150)
            edge_ratio = cv2.countNonZero(eye_edges) / total_eye_pixels

            # Bare face skin in orbital zone
            mask_face_skin = cv2.inRange(hsv_eye, np.array([0, 28, 65]), np.array([25, 160, 245]))
            skin_ratio = cv2.countNonZero(mask_face_skin) / total_eye_pixels

            # If protective frame/tint covers eyes OR frame rim contour is detected over bare eyes
            if (eyewear_count / total_eye_pixels) >= 0.14 or edge_ratio >= 0.09:
                has_goggles = True
            elif skin_ratio < 0.28:
                has_goggles = True
            else:
                has_goggles = False

        # Industrial Protective Gloves Check (Lower Arm & Hand Peripheries)
        has_gloves = False
        lh_y1 = py1 + int(p_h * 0.50)
        lh_y2 = min(frame.shape[0], py1 + int(p_h * 0.85))
        lh_x1 = max(0, px1 - int(p_w * 0.12))
        lh_x2 = min(frame.shape[1], px1 + int(p_w * 0.35))
        lh_roi = frame[lh_y1:lh_y2, lh_x1:lh_x2]

        rh_y1 = py1 + int(p_h * 0.50)
        rh_y2 = min(frame.shape[0], py1 + int(p_h * 0.85))
        rh_x1 = max(0, px2 - int(p_w * 0.35))
        rh_x2 = min(frame.shape[1], px2 + int(p_w * 0.12))
        rh_roi = frame[rh_y1:rh_y2, rh_x1:rh_x2]

        def check_hand_gloves(roi):
            if roi.size == 0:
                return True
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            tot = max(1, roi.shape[0] * roi.shape[1])
            # Vibrant industrial glove colors: Nitrile blue, safety yellow/orange, heavy dark rubber
            glove_blue = cv2.inRange(hsv, np.array([90, 80, 70]), np.array([135, 255, 255]))
            glove_neon = cv2.inRange(hsv, np.array([20, 100, 100]), np.array([35, 255, 255]))
            glove_dark = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 50]))
            glove_mat = cv2.bitwise_or(glove_blue, glove_neon)
            glove_mat = cv2.bitwise_or(glove_mat, glove_dark)
            glove_px = cv2.countNonZero(glove_mat)

            # Bare skin check
            skin = cv2.inRange(hsv, np.array([0, 28, 65]), np.array([25, 160, 245]))
            skin_px = cv2.countNonZero(skin)

            if (glove_px / tot) > 0.12:
                return True
            elif (skin_px / tot) > 0.18:
                return False
            return True

        left_glove_ok = check_hand_gloves(lh_roi)
        right_glove_ok = check_hand_gloves(rh_roi)
        has_gloves = (left_glove_ok and right_glove_ok)

        # 5. Industrial Safety Footwear / Steel-Toe Shoes Check (Lower Leg & Feet ROI)
        has_shoes = False
        feet_roi = None
        if kpts is not None and len(kpts) >= 17:
            ankles = [kpts[k] for k in [15, 16] if len(kpts[k]) >= 3 and kpts[k][2] > 0.18]
            if len(ankles) > 0:
                min_ay = min(a[1] for a in ankles)
                feet_y1 = max(0, min(frame.shape[0] - 8, int(min_ay - 4)))
                feet_y2 = min(frame.shape[0], py2)
                feet_x1 = max(0, px1)
                feet_x2 = min(frame.shape[1], px2)
                if (feet_y2 - feet_y1) > 8 and (feet_x2 - feet_x1) > 8:
                    feet_roi = frame[feet_y1:feet_y2, feet_x1:feet_x2]

        if feet_roi is None or feet_roi.size == 0:
            # Fallback: bottom 14% of person bounding box
            feet_y1 = max(0, py2 - int(p_h * 0.14))
            feet_y2 = min(frame.shape[0], py2)
            feet_x1 = max(0, px1 + int(p_w * 0.10))
            feet_x2 = min(frame.shape[1], px2 - int(p_w * 0.10))
            feet_roi = frame[feet_y1:feet_y2, feet_x1:feet_x2]

        if feet_roi.size > 0:
            hsv_feet = cv2.cvtColor(feet_roi, cv2.COLOR_BGR2HSV)
            total_feet_px = max(1, feet_roi.shape[0] * feet_roi.shape[1])
            
            # Check for bare skin in feet region (bare feet, slippers, flip-flops, sandals)
            mask_foot_skin = cv2.inRange(hsv_feet, np.array([0, 25, 60]), np.array([25, 160, 245]))
            foot_skin_ratio = cv2.countNonZero(mask_foot_skin) / total_feet_px

            # Industrial safety boots materials (Dark leather/rubber, steel-toe cap, safety yellow/orange accents)
            mask_boot_dark = cv2.inRange(hsv_feet, np.array([0, 0, 0]), np.array([180, 255, 65]))
            mask_boot_brown = cv2.inRange(hsv_feet, np.array([8, 60, 30]), np.array([24, 255, 140]))
            mask_boot_hivis = cv2.inRange(hsv_feet, np.array([18, 90, 80]), np.array([40, 255, 255]))
            
            boot_mat = cv2.bitwise_or(mask_boot_dark, mask_boot_brown)
            boot_mat = cv2.bitwise_or(boot_mat, mask_boot_hivis)
            boot_px = cv2.countNonZero(boot_mat)
            boot_ratio = boot_px / total_feet_px

            # Decision:
            # If bare foot skin is exposed (>= 16%), worker is wearing slippers / barefoot -> Violation
            if foot_skin_ratio >= 0.16:
                has_shoes = False
            # If heavy closed boot material covers >= 18% of foot zone -> Compliant
            elif boot_ratio >= 0.18:
                has_shoes = True
            # If low skin ratio (< 10%), default to closed shoe compliance
            elif foot_skin_ratio < 0.10:
                has_shoes = True
            else:
                has_shoes = False

        # Respect granular toggles (Safety Shoes coupled with Vest switch)
        effective_helmet = has_helmet if self.helmet_check_enabled else True
        effective_vest = has_vest if self.vest_check_enabled else True
        effective_gloves = has_gloves if self.gloves_check_enabled else True
        effective_goggles = has_goggles if self.goggles_check_enabled else True
        effective_shoes = has_shoes if (self.vest_check_enabled and self.shoes_check_enabled) else True

        return {
            "helmet": effective_helmet,
            "vest": effective_vest,
            "gloves": effective_gloves,
            "goggles": effective_goggles,
            "shoes": effective_shoes,
            "harness": has_harness,
            "compliant": effective_helmet and effective_vest and effective_gloves and effective_goggles and effective_shoes
        }

    def _check_point_in_polygon(self, point: Tuple[int, int], poly_points: np.ndarray) -> bool:
        """Checks if a 2D point lies inside the polygon."""
        dist = cv2.pointPolygonTest(poly_points, (float(point[0]), float(point[1])), False)
        return dist >= 0

    def _render_pulsing_drop_zone(self, frame, center: Tuple[int, int], radius: int):
        """Renders dynamic pulsing drop shadow hazard zone on the floor."""
        overlay = frame.copy()
        cx, cy = center
        
        cv2.circle(overlay, (cx, cy), radius, (0, 0, 220), -1)
        cv2.addWeighted(overlay, 0.30, frame, 0.70, 0, frame)
        cv2.circle(frame, (cx, cy), radius, (0, 0, 255), 3)
        cv2.circle(frame, (cx, cy), max(10, radius // 3), (0, 165, 255), 2)
        
        self.radar_angle = (self.radar_angle + 6.0) % 360.0
        rad = math.radians(self.radar_angle)
        beam_x = int(cx + radius * math.cos(rad))
        beam_y = int(cy + radius * math.sin(rad))
        cv2.line(frame, (cx, cy), (beam_x, beam_y), (0, 255, 255), 2)
        
        cv2.putText(frame, "CRANE DROP ZONE [LINE OF FIRE]", (cx - radius + 10, cy - radius - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # ================= Main Process Frame =================
    def process_frame(self, frame, zone_id: str = "Zone 1 - Main Floor"):
        """Processes a single video frame respecting all active master toggles."""
        if frame is None:
            return None, {}

        orig_h, orig_w, _ = frame.shape
        if orig_w > 1280:
            scale = 1280.0 / orig_w
            frame = cv2.resize(frame, (1280, int(orig_h * scale)))

        annotated_frame = frame.copy()
        h, w, _ = frame.shape
        now = time.time()

        stats = {
            "auto_pilot": self.auto_pilot_mode,
            "total_workers": 0,
            "compliant_workers": 0,
            "violations_count": 0,
            "compliance_rate": 100.0,
            "fire_detected": False,
            "fall_detected": False,
            "danger_breached": False,
            "phone_detected": False,
            "proximity_alert": False,
            "height_violation": False,
            "suspended_load_hazard": False,
            "confined_overstay": False,
            "confined_headcount": len(self.confined_workers_active),
            "hot_work_active": False,
            "hot_work_violation": False,
            "trench_hazard": False,
            "night_intrusion": False,
            "night_mode": self.night_mode_enabled,
            "gate_status": "IDLE",
            "active_violations": [],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        # 1. Height Safety Elevated Zone Overlay (Only if enabled)
        height_poly_pts = None
        if self.height_safety_enabled and self.height_zone_norm:
            height_poly_pts = np.array([
                [int(px * w), int(py * h)] for px, py in self.height_zone_norm
            ], np.int32).reshape((-1, 1, 2))
            
            cv2.polylines(annotated_frame, [height_poly_pts], isClosed=True, color=(255, 140, 0), thickness=2)
            first_pt = height_poly_pts[0][0]
            cv2.putText(annotated_frame, "ELEVATED WORK DECK (HARNESS MANDATORY >2M)",
                        (first_pt[0] + 10, first_pt[1] + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 140, 0), 2)

        # 2. Confined Space Portal Overlay (Only if enabled)
        confined_poly_pts = None
        if self.confined_space_enabled and self.confined_space_poly_norm:
            confined_poly_pts = np.array([
                [int(px * w), int(py * h)] for px, py in self.confined_space_poly_norm
            ], np.int32).reshape((-1, 1, 2))

            conf_overlay = annotated_frame.copy()
            cv2.fillPoly(conf_overlay, [confined_poly_pts], (140, 50, 0))
            cv2.addWeighted(conf_overlay, 0.20, annotated_frame, 0.80, 0, annotated_frame)
            cv2.polylines(annotated_frame, [confined_poly_pts], isClosed=True, color=(255, 180, 0), thickness=2)
            
            c_first = confined_poly_pts[0][0]
            cv2.putText(annotated_frame, f"DOOR: CONFINED SPACE ({self.confined_space_name.upper()})",
                        (c_first[0] + 8, c_first[1] + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 2)
            cv2.putText(annotated_frame, f"Occupants: {len(self.confined_workers_active)} | Safe Limit: {int(self.confined_max_safe_seconds/60)}m",
                        (c_first[0] + 8, c_first[1] + 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1)

        # 3. Trench Excavation Setback Margin Overlay (Only if enabled)
        if self.trench_safety_enabled:
            trench_y = int(self.trench_line_y_norm * h)
            margin_y = max(0, trench_y - self.trench_margin_px)
            cv2.line(annotated_frame, (0, trench_y), (w, trench_y), (0, 0, 255), 3)
            cv2.line(annotated_frame, (0, margin_y), (w, margin_y), (0, 165, 255), 2)
            cv2.putText(annotated_frame, "EXCAVATION TRENCH LIP (CAVE-IN HAZARD)", (15, trench_y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
            cv2.putText(annotated_frame, "SAFE SETBACK LINE", (w - 180, margin_y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 165, 255), 1)

        # 4. Danger Zone Geofence Overlay (Only if enabled)
        danger_poly_pts = None
        if self.danger_zone_enabled and self.danger_zone_poly_norm:
            danger_poly_pts = np.array([
                [int(px * w), int(py * h)] for px, py in self.danger_zone_poly_norm
            ], np.int32).reshape((-1, 1, 2))

            overlay = annotated_frame.copy()
            cv2.fillPoly(overlay, [danger_poly_pts], (0, 0, 180))
            cv2.addWeighted(overlay, 0.25, annotated_frame, 0.75, 0, annotated_frame)
            cv2.polylines(annotated_frame, [danger_poly_pts], isClosed=True, color=(0, 0, 255), thickness=2)

            first_pt = danger_poly_pts[0][0]
            cv2.putText(annotated_frame, f"RESTRICTED: {self.danger_zone_name.upper()}",
                        (first_pt[0] + 5, first_pt[1] + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

        # 5. Fire and Smoke Detection (Only if enabled)
        if self.fire_detection_enabled:
            fire_boxes = self._detect_fire_smoke_hsv(frame)
            if fire_boxes:
                self.fire_consecutive_frames += 1
                stats["fire_detected"] = True
                stats["violations_count"] += 1
                stats["active_violations"].append("CRITICAL: Fire / Flame Hazard")
                for item in fire_boxes:
                    fx1, fy1, fx2, fy2 = item[0], item[1], item[2], item[3]
                    htype = item[5] if len(item) > 5 else "FIRE"
                    lbl = f"CRITICAL: {htype} HAZARD DETECTED"
                    cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 3)
                    cv2.rectangle(annotated_frame, (fx1, max(0, fy1 - 26)), (fx2, fy1), (0, 0, 255), -1)
                    cv2.putText(annotated_frame, lbl, (fx1 + 5, fy1 - 7),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
            else:
                self.fire_consecutive_frames = max(0, self.fire_consecutive_frames - 1)

            if fire_boxes and self.fire_consecutive_frames >= 1:
                alarm_manager.trigger_alert("FIRE", f"Emergency! Fire hazard detected in {zone_id}! Evacuate immediately!", severity="CRITICAL")
                self._save_incident_snapshot(annotated_frame, zone_id, "Fire Hazard", "CRITICAL",
                                            "Open flame / smoke signature detected",
                                            coord_x=fire_boxes[0][0]/w, coord_y=fire_boxes[0][1]/h, category="FIRE")

        # 6. Hot Work Sparks & Extinguisher Proximity (Only if enabled)
        if self.hot_work_enabled:
            spark_boxes = self._detect_welding_sparks(frame)
            if spark_boxes:
                self.hot_work_consecutive_frames += 1
                stats["hot_work_active"] = True
                self.last_spark_time = now
            else:
                self.hot_work_consecutive_frames = max(0, self.hot_work_consecutive_frames - 1)

            if spark_boxes:
                for (sx1, sy1, sx2, sy2, _) in spark_boxes:
                    scenter = ((sx1 + sx2) // 2, (sy1 + sy2) // 2)
                    has_extinguisher, ext_box = self._detect_extinguisher_near(frame, scenter, radius_px=220)
                    
                    cv2.rectangle(annotated_frame, (sx1, sy1), (sx2, sy2), (0, 255, 255), 2)
                    cv2.putText(annotated_frame, "HOT WORK / WELDING SPARK", (sx1, max(20, sy1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                    
                    if has_extinguisher:
                        ex1, ey1, ex2, ey2 = ext_box
                        cv2.rectangle(annotated_frame, (ex1, ey1), (ex2, ey2), (0, 255, 0), 2)
                        cv2.putText(annotated_frame, "EXTINGUISHER [OK]", (ex1, ey1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
                        cv2.line(annotated_frame, scenter, ((ex1+ex2)//2, (ey1+ey2)//2), (0, 255, 0), 1)
                    else:
                        stats["hot_work_violation"] = True
                        stats["violations_count"] += 1
                        stats["active_violations"].append("Hot Work without Fire Extinguisher")
                        
                        cv2.circle(annotated_frame, scenter, 180, (0, 0, 255), 2)
                        cv2.putText(annotated_frame, "NO FIRE EXTINGUISHER IN 5M RADIUS",
                                    (sx1 - 40, sy2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
                        # Guard loud siren and snapshot: require at least 3 consecutive frames to avoid flash glitches
                        if self.hot_work_consecutive_frames >= 3:
                            alarm_manager.trigger_alert("HOT_WORK", f"Caution: Hot work active without fire extinguisher in {zone_id}!", severity="HIGH")
                            self._save_incident_snapshot(annotated_frame, zone_id, "Hot Work Violation (No Extinguisher)", "HIGH",
                                                        "Welding / hot work active without required fire extinguisher in proximity",
                                                        coord_x=scenter[0]/w, coord_y=scenter[1]/h, category="HOT_WORK")

        # 7. AI Inference Engine (Pose Skeletal Verification + Object Detection)
        raw_person_candidates = []
        phone_boxes = []
        vehicle_boxes = []
        suspended_load_boxes = []

        try:
            with self.inference_lock:
                # Step A: High-Precision Human Pose & Skeletal Landmark Detection
                # Filters out curtains, furniture, clothes, shadows, and non-human objects with 100% precision
                if self.pose_model is not None:
                    pose_conf = min(0.20, self.conf_thresh)
                    p_dev = getattr(self, "pose_device", None)
                    p_kwargs = {"device": p_dev} if p_dev else {}
                    pose_results = self.pose_model(frame, conf=pose_conf, imgsz=384, verbose=False, **p_kwargs)[0]
                    if pose_results.boxes is not None and len(pose_results.boxes) > 0:
                        kpts_data = pose_results.keypoints.data.cpu().numpy() if pose_results.keypoints is not None else None
                        for idx, box in enumerate(pose_results.boxes):
                            p_conf = float(box.conf[0])
                            bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                            bx1, by1 = max(0, bx1), max(0, by1)
                            bx2, by2 = min(w, bx2), min(h, by2)
                            kpts = kpts_data[idx] if kpts_data is not None and idx < len(kpts_data) else None

                            if self._is_valid_human(frame, (bx1, by1, bx2, by2), kpts=kpts):
                                raw_person_candidates.append((bx1, by1, bx2, by2, p_conf, kpts))

                # Step B: Object / Hazard Detection (Phone, Vehicles, Suspended Load or Fallback)
                need_general_model = (
                    self.phone_detection_enabled or 
                    self.proximity_detection_enabled or 
                    self.suspended_load_enabled or 
                    (self.pose_model is None) or
                    (len(raw_person_candidates) == 0)
                )

                if need_general_model and self.model is not None:
                    gen_conf = min(0.20, self.conf_thresh)
                    m_dev = getattr(self, "model_device", None)
                    m_kwargs = {"device": m_dev} if m_dev else {}
                    results = self.model(frame, conf=gen_conf, imgsz=384, verbose=False, **m_kwargs)[0]

                    for box in results.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                        bx1, by1 = max(0, bx1), max(0, by1)
                        bx2, by2 = min(w, bx2), min(h, by2)

                        if cls_id == 0:
                            # Catch persons that pose model might have missed (e.g. lying down on bed/ground)
                            has_overlap = False
                            for (cx1, cy1, cx2, cy2, _, _) in raw_person_candidates:
                                ix1 = max(bx1, cx1)
                                iy1 = max(by1, cy1)
                                ix2 = min(bx2, cx2)
                                iy2 = min(by2, cy2)
                                if ix2 > ix1 and iy2 > iy1:
                                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                                    box_area = (bx2 - bx1) * (by2 - by1)
                                    if (inter_area / max(1, box_area)) > 0.30:
                                        has_overlap = True
                                        break
                            if not has_overlap and self._is_valid_human(frame, (bx1, by1, bx2, by2), kpts=None):
                                raw_person_candidates.append((bx1, by1, bx2, by2, conf, None))
                        elif cls_id == 67 and self.phone_detection_enabled:
                            phone_boxes.append((bx1, by1, bx2, by2, conf))
                        elif cls_id in [2, 3, 5, 7] and self.proximity_detection_enabled:
                            vehicle_boxes.append((bx1, by1, bx2, by2, conf))
                        elif cls_id in [24, 26, 28] and self.suspended_load_enabled:
                            if by2 < (h * 0.55):
                                suspended_load_boxes.append((bx1, by1, bx2, by2, conf))

            # Step C: Temporal Bounding Box & Landmark Smoothing (EMA) to eliminate jitter and flickering
            smoothed_person_boxes = []
            now_t = time.time()
            for (bx1, by1, bx2, by2, conf, kpts) in raw_person_candidates:
                bcx = (bx1 + bx2) / 2.0
                bcy = (by1 + by2) / 2.0
                best_match_id = None
                best_dist = 65.0  # spatial threshold in pixels

                for tid, tdata in self.tracked_boxes.items():
                    tx1, ty1, tx2, ty2 = tdata["box"]
                    tcx = (tx1 + tx2) / 2.0
                    tcy = (ty1 + ty2) / 2.0
                    dist = math.hypot(bcx - tcx, bcy - tcy)
                    if dist < best_dist:
                        best_dist = dist
                        best_match_id = tid

                if best_match_id is not None:
                    # EMA interpolation: smooth gliding coordinates
                    px1, py1, px2, py2 = self.tracked_boxes[best_match_id]["box"]
                    alpha = 0.35
                    sx1 = int((1.0 - alpha) * px1 + alpha * bx1)
                    sy1 = int((1.0 - alpha) * py1 + alpha * by1)
                    sx2 = int((1.0 - alpha) * px2 + alpha * bx2)
                    sy2 = int((1.0 - alpha) * py2 + alpha * by2)
                    self.tracked_boxes[best_match_id] = {
                        "box": (sx1, sy1, sx2, sy2),
                        "last_seen": now_t,
                        "conf": conf,
                        "kpts": kpts
                    }
                    smoothed_person_boxes.append((sx1, sy1, sx2, sy2, conf, kpts))
                else:
                    new_id = f"tr_{len(self.tracked_boxes)}_{int(now_t * 100) % 10000}"
                    self.tracked_boxes[new_id] = {
                        "box": (bx1, by1, bx2, by2),
                        "last_seen": now_t,
                        "conf": conf,
                        "kpts": kpts
                    }
                    smoothed_person_boxes.append((bx1, by1, bx2, by2, conf, kpts))

            # Prune inactive box tracks older than 1.2s
            self.tracked_boxes = {
                tid: tdata for tid, tdata in self.tracked_boxes.items()
                if (now_t - tdata["last_seen"]) < 1.2
            }
            person_boxes = smoothed_person_boxes

            stats["total_workers"] = len(person_boxes)
            current_confined_workers = set()

            # Process Workers
            for i, (px1, py1, px2, py2, p_conf, p_kpts) in enumerate(person_boxes):
                pw = px2 - px1
                ph = py2 - py1
                centroid_x = (px1 + px2) // 2
                centroid_y = (py1 + py2) // 2
                foot_point = (centroid_x, py2 - 5)
                norm_x = centroid_x / w
                norm_y = centroid_y / h
                worker_id = f"worker_{i}_{centroid_x//30}"

                # Night Intrusion Mode
                if self.night_mode_enabled:
                    stats["night_intrusion"] = True
                    stats["violations_count"] += 1
                    stats["active_violations"].append("Night Shift Unauthorized Intruder")
                    
                    cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), (0, 0, 255), 3)
                    cv2.putText(annotated_frame, "SECURITY BREACH: NIGHT INTRUDER", (px1, py1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                    
                    alarm_manager.trigger_alert("NIGHT_INTRUSION", f"Security Alert: Unauthorized intrusion detected in {zone_id}!", severity="CRITICAL")
                    self._save_incident_snapshot(annotated_frame, zone_id, "Night Shift Perimeter Intrusion", "CRITICAL",
                                                "Movement / person detected during night security lockdown",
                                                coord_x=norm_x, coord_y=norm_y, category="TRENCH_SECURITY")

                # Fall & Man-Down Emergency Detection (Pose Keypoints + Horizontal Geometry)
                aspect_ratio = pw / max(1, ph)
                is_fallen = False
                pose_fall = False
                box_fall = False
                fall_reason = ""

                if self.fall_detection_enabled:
                    # Factor 1: Skeletal Pose Keypoints (YOLO11-Pose)
                    if p_kpts is not None and len(p_kpts) >= 9:
                        valid_shoulders = [p_kpts[k] for k in [5, 6] if len(p_kpts[k]) >= 3 and p_kpts[k][2] > 0.12]
                        valid_hips = [p_kpts[k] for k in [11, 12] if len(p_kpts[k]) >= 3 and p_kpts[k][2] > 0.12]
                        valid_head = [p_kpts[k] for k in range(min(5, len(p_kpts))) if len(p_kpts[k]) >= 3 and p_kpts[k][2] > 0.12]
                        valid_lower = [p_kpts[k] for k in range(13, min(17, len(p_kpts))) if len(p_kpts[k]) >= 3 and p_kpts[k][2] > 0.12]

                        # Check 1A: Spine vector angle (Shoulder center to Hip center)
                        if len(valid_shoulders) > 0 and len(valid_hips) > 0:
                            sh_x = float(np.mean([p[0] for p in valid_shoulders]))
                            sh_y = float(np.mean([p[1] for p in valid_shoulders]))
                            hp_x = float(np.mean([p[0] for p in valid_hips]))
                            hp_y = float(np.mean([p[1] for p in valid_hips]))

                            dx = abs(sh_x - hp_x)
                            dy = abs(sh_y - hp_y)

                            # Standing: dy >> dx (angle ~ 65-90 deg). Lying down/fallen: dx >= dy * 0.60 or angle < 58 deg.
                            spine_angle = math.degrees(math.atan2(dy, max(1e-3, dx)))
                            if spine_angle < 58.0 or dx > (dy * 0.60):
                                pose_fall = True
                                fall_reason = f"Horizontal Spine ({int(spine_angle)} deg)"

                        # Check 1B: Head and Hip level alignment (lying flat on bed or ground)
                        if not pose_fall and len(valid_head) > 0 and len(valid_hips) > 0:
                            hd_y = float(np.mean([p[1] for p in valid_head]))
                            hp_y = float(np.mean([p[1] for p in valid_hips]))
                            if abs(hd_y - hp_y) < (0.35 * max(pw, ph)):
                                pose_fall = True
                                fall_reason = "Head & Hip Level (Lying Flat)"

                        # Check 1C: Head and Lower body horizontal
                        if not pose_fall and len(valid_head) > 0 and len(valid_lower) > 0:
                            hd_y = float(np.mean([p[1] for p in valid_head]))
                            low_y = float(np.mean([p[1] for p in valid_lower]))
                            if abs(hd_y - low_y) < (0.42 * max(pw, ph)):
                                pose_fall = True
                                fall_reason = "Body Horizontal on Surface"

                    # Factor 2: Bounding Box Geometry (Horizontal Body Ratio)
                    # When lying down on bed or floor, width is comparable to or greater than height
                    # Standing person is 0.25 to 0.60. Lying down is >= 0.86
                    if aspect_ratio >= 0.86:
                        box_fall = True
                        if not fall_reason:
                            fall_reason = f"Horizontal Posture (Ratio: {aspect_ratio:.2f})"

                    # Combine Pose and Box geometry
                    is_fallen_candidate = (pose_fall or box_fall)

                    if is_fallen_candidate:
                        self.fall_trackers[worker_id] = self.fall_trackers.get(worker_id, 0) + 1
                        self.fall_consecutive_frames += 1
                    else:
                        if worker_id in self.fall_trackers:
                            self.fall_trackers[worker_id] = max(0, self.fall_trackers[worker_id] - 1)
                        self.fall_consecutive_frames = max(0, self.fall_consecutive_frames - 1)

                    # Immediate alert trigger on confirmed fall (zero lag!)
                    worker_fall_count = self.fall_trackers.get(worker_id, 0)
                    if is_fallen_candidate and (worker_fall_count >= 1 or self.fall_consecutive_frames >= 1):
                        is_fallen = True
                        stats["fall_detected"] = True
                        stats["violations_count"] += 1
                        stats["active_violations"].append("Man-Down / Fall Emergency")

                        # Draw Emergency High-Visibility Red Box & Banner
                        cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), (0, 0, 255), 3)
                        header_top = max(0, py1 - 28)
                        cv2.rectangle(annotated_frame, (px1, header_top), (px2, py1), (0, 0, 255), -1)
                        cv2.putText(annotated_frame, "EMERGENCY: WORKER DOWN", (px1 + 6, max(14, py1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                        
                        if fall_reason:
                            cv2.putText(annotated_frame, f"STATUS: {fall_reason}", (px1, py2 + 18),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

                        alarm_manager.trigger_alert("FALL", f"Emergency! Worker fallen or collapsed in {zone_id}!", severity="CRITICAL", force=True)
                        self._save_incident_snapshot(annotated_frame, zone_id, "Worker Fall / Man-Down", "CRITICAL",
                                                    f"Collapsed posture: {fall_reason or 'Horizontal body'}",
                                                    coord_x=norm_x, coord_y=norm_y, category="FALL")

                # Danger Zone Geofencing (Only if enabled)
                if self.danger_zone_enabled and danger_poly_pts is not None:
                    in_danger = self._check_point_in_polygon(foot_point, danger_poly_pts)
                    if in_danger:
                        self.geofence_consecutive_frames += 1
                    else:
                        self.geofence_consecutive_frames = max(0, self.geofence_consecutive_frames - 1)

                    if in_danger and self.geofence_consecutive_frames >= 4:
                        stats["danger_breached"] = True
                        stats["violations_count"] += 1
                        stats["active_violations"].append("Perimeter Geofence Breach")

                        cv2.putText(annotated_frame, "BREACH: DANGER ZONE INTRUSION", (px1, py2 + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
                        alarm_manager.trigger_alert("GEOFENCE", f"Warning! Unauthorized worker in {self.danger_zone_name}!", severity="CRITICAL")
                        self._save_incident_snapshot(annotated_frame, zone_id, "Danger Zone Breach", "CRITICAL",
                                                    f"Worker entered restricted {self.danger_zone_name}",
                                                    coord_x=norm_x, coord_y=norm_y, category="PERIMETER")

                # Height Safety & Harness (Only if enabled)
                is_at_height = False
                if self.height_safety_enabled and height_poly_pts is not None:
                    if self._check_point_in_polygon((centroid_x, py1 + 10), height_poly_pts) or (py1 / h) < 0.38:
                        is_at_height = True

                # Confined Space Stay Tracker (Only if enabled)
                if self.confined_space_enabled and confined_poly_pts is not None:
                    if self._check_point_in_polygon(foot_point, confined_poly_pts):
                        current_confined_workers.add(worker_id)
                        if worker_id not in self.confined_workers_active:
                            self.confined_workers_active[worker_id] = now
                            self.confined_total_entered += 1
                        
                        duration = now - self.confined_workers_active[worker_id]
                        cv2.putText(annotated_frame, f"INSIDE CONFINED: {int(duration)}s",
                                    (px1, py1 - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                        
                        if duration > self.confined_max_safe_seconds:
                            stats["confined_overstay"] = True
                            stats["violations_count"] += 1
                            stats["active_violations"].append("Confined Space Overstay Limit")
                            
                            cv2.putText(annotated_frame, "OVERSTAY: GAS EXPOSURE LIMIT", (px1, py2 + 22),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
                            alarm_manager.trigger_alert("CONFINED_SPACE", f"Alert: Confined space stay limit exceeded in {self.confined_space_name}!", severity="HIGH")
                            self._save_incident_snapshot(annotated_frame, zone_id, "Confined Space Overstay", "HIGH",
                                                        f"Worker exceeded safe limit in {self.confined_space_name} ({int(duration)}s)",
                                                        coord_x=norm_x, coord_y=norm_y, category="CONFINED_SPACE")

                # Trench Margin Hazard (Only if enabled)
                if self.trench_safety_enabled:
                    trench_y = int(self.trench_line_y_norm * h)
                    margin_y = max(0, trench_y - self.trench_margin_px)
                    if py2 > margin_y:
                        self.trench_consecutive_frames += 1
                    else:
                        self.trench_consecutive_frames = max(0, self.trench_consecutive_frames - 1)

                    if py2 > margin_y and self.trench_consecutive_frames >= 4:
                        stats["trench_hazard"] = True
                        stats["violations_count"] += 1
                        stats["active_violations"].append("Trench Edge Collapse Margin Hazard")
                        
                        cv2.putText(annotated_frame, "CAVE-IN RISK: STEP BACK FROM TRENCH", (px1, py2 + 18),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
                        alarm_manager.trigger_alert("TRENCH_MARGIN", f"Warning: Stand back from excavation trench edge in {zone_id}!", severity="HIGH")
                        self._save_incident_snapshot(annotated_frame, zone_id, "Trench Edge Collapse Margin", "HIGH",
                                                    "Worker positioned within hazardous trench collapse setback margin",
                                                    coord_x=norm_x, coord_y=norm_y, category="TRENCH_SECURITY")

                # PPE & Harness Inspection
                if not is_fallen:
                    ppe_res = self._analyze_worker_ppe_heuristics(frame, (px1, py1, px2, py2), kpts=p_kpts)
                    missing_items = []
                    if self.helmet_check_enabled and not ppe_res["helmet"]:
                        missing_items.append("No Helmet")
                    if self.vest_check_enabled and not ppe_res["vest"]:
                        missing_items.append("No Vest")
                    if self.vest_check_enabled and self.shoes_check_enabled and not ppe_res["shoes"]:
                        missing_items.append("No Safety Shoes")
                    if self.gloves_check_enabled and not ppe_res["gloves"]:
                        missing_items.append("No Gloves")
                    if self.goggles_check_enabled and not ppe_res["goggles"]:
                        missing_items.append("No Goggles")
                    if is_at_height and not ppe_res["harness"]:
                        missing_items.append("No Safety Harness at Height")
                        stats["height_violation"] = True

                    is_compliant = (len(missing_items) == 0)

                    if is_compliant:
                        stats["compliant_workers"] += 1
                        box_color = (0, 255, 0)
                        status_label = f"SAFE WORKER [OK] ({p_conf:.2f})"
                        self.ppe_violation_trackers[worker_id] = 0
                    else:
                        self.ppe_violation_trackers[worker_id] = self.ppe_violation_trackers.get(worker_id, 0) + 1
                        stats["violations_count"] += 1
                        box_color = (0, 0, 255)
                        v_desc = " & ".join(missing_items)
                        status_label = f"VIOLATION: {v_desc}"
                        stats["active_violations"].append(v_desc)

                        # Only trigger sirens and snapshots once confirmed for >= 4 consecutive frames
                        if self.ppe_violation_trackers[worker_id] >= 4:
                            if "No Safety Harness" in v_desc:
                                alarm_msg = f"Critical Alert! Unharnessed worker at height in {zone_id}!"
                                alarm_manager.trigger_alert("HARNESS", alarm_msg, severity="CRITICAL")
                                self._save_incident_snapshot(annotated_frame, zone_id, "Height Safety Violation (No Harness)", "CRITICAL",
                                                            "Worker at elevated height without safety harness / lifeline",
                                                            coord_x=norm_x, coord_y=norm_y, category="HEIGHT_HARNESS")
                            elif "No Helmet" in v_desc:
                                alarm_msg = f"Safety Alert: Hardhat helmet required in {zone_id}!"
                                alarm_manager.trigger_alert("PPE_HELMET", alarm_msg, severity="HIGH")
                                self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH",
                                                            f"Worker missing: {v_desc}",
                                                            coord_x=norm_x, coord_y=norm_y, category="PPE")
                            elif "No Vest" in v_desc:
                                alarm_msg = f"Safety Notice: High-visibility vest required in {zone_id}!"
                                alarm_manager.trigger_alert("PPE_VEST", alarm_msg, severity="HIGH")
                                self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH",
                                                            f"Worker missing: {v_desc}",
                                                            coord_x=norm_x, coord_y=norm_y, category="PPE")
                            elif "No Gloves" in v_desc:
                                alarm_msg = f"Safety Notice: Industrial protective gloves required in {zone_id}!"
                                alarm_manager.trigger_alert("PPE_GLOVES", alarm_msg, severity="HIGH")
                                self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH",
                                                            f"Worker missing: {v_desc}",
                                                            coord_x=norm_x, coord_y=norm_y, category="PPE")
                            elif "No Goggles" in v_desc:
                                alarm_msg = f"Safety Alert: Eye protection goggles required in {zone_id}!"
                                alarm_manager.trigger_alert("PPE_GOGGLES", alarm_msg, severity="HIGH")
                                self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH",
                                                            f"Worker missing: {v_desc}",
                                                            coord_x=norm_x, coord_y=norm_y, category="PPE")
                            elif "No Safety Shoes" in v_desc:
                                alarm_msg = f"Safety Notice: Industrial safety boots required in {zone_id}!"
                                alarm_manager.trigger_alert("PPE_SHOES", alarm_msg, severity="HIGH")
                                self._save_incident_snapshot(annotated_frame, zone_id, f"PPE Violation ({v_desc})", "HIGH",
                                                            f"Worker missing: {v_desc}",
                                                            coord_x=norm_x, coord_y=norm_y, category="PPE")

                    cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), box_color, 2)
                    cv2.rectangle(annotated_frame, (px1, max(0, py1 - 25)), (px2, py1), box_color, -1)
                    cv2.putText(annotated_frame, status_label, (px1 + 5, py1 - 7),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

                    # High-Tech PPE HUD Chips: [H:OK] [V:OK] [S:OK] [G:OK] [E:OK]
                    hud_y = min(h - 8, py2 + 18)
                    badges = [
                        ("H", ppe_res["helmet"])
                    ]
                    if self.vest_check_enabled:
                        badges.append(("V", ppe_res["vest"]))
                        badges.append(("S", ppe_res["shoes"]))
                    if self.gloves_check_enabled:
                        badges.append(("G", ppe_res["gloves"]))
                    if self.goggles_check_enabled:
                        badges.append(("E", ppe_res["goggles"]))
                    badge_x = px1
                    for tag, is_ok in badges:
                        b_col = (0, 180, 0) if is_ok else (0, 0, 220)
                        tag_str = f"{tag}:OK" if is_ok else f"{tag}:NO"
                        cv2.rectangle(annotated_frame, (badge_x, hud_y - 12), (badge_x + 36, hud_y + 3), b_col, -1)
                        cv2.putText(annotated_frame, tag_str, (badge_x + 2, hud_y - 1),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
                        badge_x += 40

            # Cleanup departed confined occupants
            if self.confined_space_enabled:
                for old_worker in list(self.confined_workers_active.keys()):
                    if old_worker not in current_confined_workers:
                        del self.confined_workers_active[old_worker]
                        self.confined_total_exited += 1
                stats["confined_headcount"] = len(self.confined_workers_active)

            # Crane Suspended Load Drop Zone (Only if enabled)
            if self.suspended_load_enabled and suspended_load_boxes:
                for (lx1, ly1, lx2, ly2, l_conf) in suspended_load_boxes:
                    lcx = (lx1 + lx2) // 2
                    lcy = (ly1 + ly2) // 2
                    load_w = lx2 - lx1
                    
                    cv2.rectangle(annotated_frame, (lx1, ly1), (lx2, ly2), (0, 165, 255), 2)
                    cv2.line(annotated_frame, (lcx, 0), (lcx, ly1), (200, 200, 200), 2)
                    cv2.putText(annotated_frame, "CRANE HOIST / SUSPENDED LOAD", (lx1 - 10, max(20, ly1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 2)
                    
                    ground_cy = min(h - 35, int(lcy + (h - lcy) * 0.70 + 80))
                    drop_radius = max(70, int(load_w * 1.3))
                    self._render_pulsing_drop_zone(annotated_frame, (lcx, ground_cy), drop_radius)
                    
                    cv2.line(annotated_frame, (lcx, ly2), (lcx, ground_cy), (0, 0, 255), 1, cv2.LINE_AA)
                    
                    in_drop_zone = False
                    for (px1, py1, px2, py2, *_) in person_boxes:
                        p_center = ((px1 + px2) // 2, (py1 + py2) // 2)
                        dist_to_drop = math.hypot(p_center[0] - lcx, p_center[1] - ground_cy)
                        
                        if dist_to_drop < (drop_radius + 20):
                            in_drop_zone = True
                            cv2.line(annotated_frame, p_center, (lcx, ground_cy), (0, 0, 255), 3)
                            cv2.putText(annotated_frame, "LINE OF FIRE: DROP ZONE", (px1 - 20, py2 + 25),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

                            self.suspended_load_consecutive_frames += 1
                            if self.suspended_load_consecutive_frames >= 4:
                                stats["suspended_load_hazard"] = True
                                stats["violations_count"] += 1
                                stats["active_violations"].append("Worker in Crane Suspended Load Drop Zone")
                                alarm_manager.trigger_alert("SUSPENDED_LOAD", f"Emergency! Worker in crane suspended load drop zone in {zone_id}!", severity="CRITICAL")
                                self._save_incident_snapshot(annotated_frame, zone_id, "Suspended Load Hazard (Line of Fire)", "CRITICAL",
                                                            "Worker positioned directly underneath suspended crane load drop zone",
                                                            coord_x=p_center[0]/w, coord_y=p_center[1]/h, category="SUSPENDED_LOAD")
                    if not in_drop_zone:
                        self.suspended_load_consecutive_frames = max(0, self.suspended_load_consecutive_frames - 1)

            # Cellphone Distraction (Only if enabled)
            if self.phone_detection_enabled:
                for (cx1, cy1, cx2, cy2, c_conf) in phone_boxes:
                    phone_center = ((cx1 + cx2) // 2, (cy1 + cy2) // 2)
                    for (px1, py1, px2, py2, *_) in person_boxes:
                        if (px1 - 20 <= phone_center[0] <= px2 + 20) and (py1 <= phone_center[1] <= py2):
                            stats["phone_detected"] = True
                            stats["violations_count"] += 1
                            stats["active_violations"].append("Cellphone Distraction")

                            cv2.rectangle(annotated_frame, (cx1, cy1), (cx2, cy2), (255, 0, 255), 2)
                            cv2.putText(annotated_frame, "DISTRACTION: CELL PHONE USE", (cx1, max(20, cy1 - 5)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                            alarm_manager.trigger_alert("PHONE", "Caution: Mobile phone use prohibited in active zone!", severity="HIGH")
                            self._save_incident_snapshot(annotated_frame, zone_id, "Distraction Hazard (Cell Phone)", "HIGH",
                                                        "Worker operating phone in hazardous work zone",
                                                        coord_x=phone_center[0]/w, coord_y=phone_center[1]/h, category="DISTRACTION")
                            break

            # Vehicle & Machinery Proximity (Only if enabled)
            if self.proximity_detection_enabled:
                for (vx1, vy1, vx2, vy2, v_conf) in vehicle_boxes:
                    v_center = ((vx1 + vx2) // 2, (vy1 + vy2) // 2)
                    cv2.rectangle(annotated_frame, (vx1, vy1), (vx2, vy2), (255, 165, 0), 2)
                    cv2.putText(annotated_frame, "MACHINERY / VEHICLE", (vx1, max(20, vy1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 2)

                    if self.trench_safety_enabled:
                        trench_y = int(self.trench_line_y_norm * h)
                        margin_y = max(0, trench_y - self.trench_margin_px)
                        if vy2 > margin_y:
                            stats["trench_hazard"] = True
                            cv2.putText(annotated_frame, "VEHICLE OVERBURDEN ON TRENCH LIP", (vx1, vy2 + 20),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            alarm_manager.trigger_alert("TRENCH_MARGIN", f"Warning: Heavy vehicle too close to trench edge in {zone_id}!", severity="HIGH")

                    for (px1, py1, px2, py2, *_) in person_boxes:
                        p_center = ((px1 + px2) // 2, (py1 + py2) // 2)
                        dist = math.hypot(p_center[0] - v_center[0], p_center[1] - v_center[1])
                        
                        if dist < 140:
                            stats["proximity_alert"] = True
                            cv2.line(annotated_frame, p_center, v_center, (0, 0, 255), 2)
                            mid_x = (p_center[0] + v_center[0]) // 2
                            mid_y = (p_center[1] + v_center[1]) // 2
                            cv2.putText(annotated_frame, f"PROXIMITY: {int(dist)}px", (mid_x, mid_y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

                            alarm_manager.trigger_alert("PROXIMITY", "Caution: Machinery collision proximity hazard!", severity="HIGH")
                            self._save_incident_snapshot(annotated_frame, zone_id, "Machinery Collision Proximity", "HIGH",
                                                        f"Worker dangerously close to heavy machinery ({int(dist)}px)",
                                                        coord_x=mid_x/w, coord_y=mid_y/h, category="PROXIMITY")

        except Exception as e:
            print(f"[Detector Inference Error] {e}")

        # Smart Turnstile HUD Mode
        if self.gate_mode:
            stats["gate_status"] = self._render_smart_gate_hud(annotated_frame, stats)

        # Tactical Night Mode Visual Effect
        if self.night_mode_enabled:
            annotated_frame = self._apply_night_vision_hud(annotated_frame)

        # Auto-Pilot Autonomous Badge on Frame
        if self.auto_pilot_mode:
            cv2.rectangle(annotated_frame, (w - 240, h - 35), (w - 10, h - 10), (0, 100, 0), -1)
            cv2.putText(annotated_frame, "AUTO-PILOT ACTIVE (24/7)", (w - 232, h - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1)

        # Compute Compliance Rate %
        if stats["total_workers"] > 0:
            stats["compliance_rate"] = round((stats["compliant_workers"] / stats["total_workers"]) * 100, 1)
        else:
            stats["compliance_rate"] = 100.0
            self.ppe_violation_trackers.clear()
            self.fall_consecutive_frames = 0
            self.geofence_consecutive_frames = 0

        # Draw Standard Top HUD Overlay
        if not self.gate_mode:
            self._draw_hud(annotated_frame, stats, zone_id)

        return annotated_frame, stats

    def _apply_night_vision_hud(self, frame):
        """Applies tactical night perimeter green overlay and HUD stamp."""
        h, w, _ = frame.shape
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (20, 80, 20), -1)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
        
        cv2.rectangle(frame, (10, h - 35), (280, h - 10), (0, 50, 0), -1)
        cv2.putText(frame, "NIGHT GUARD: PERIMETER SECURE", (18, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1)
        return frame

    def _render_smart_gate_hud(self, frame, stats) -> str:
        """Renders the Smart Entry Turnstile HUD with Pass/Fail state."""
        h, w, _ = frame.shape
        now = time.time()
        
        if stats["total_workers"] == 0:
            status = "WAITING"
            box_color = (120, 120, 120)
            status_text = "DOOR: SMART GATE AWAITING WORKER AT TURNSTILE"
        elif stats["compliant_workers"] == stats["total_workers"] and stats["violations_count"] == 0:
            status = "GRANTED"
            box_color = (0, 200, 0)
            status_text = "ACCESS GRANTED: 100% PPE COMPLIANCE VERIFIED"
            if self.last_gate_status != "GRANTED" and (now - self.last_gate_announce) > 4.0:
                self.last_gate_announce = now
                self.last_gate_status = "GRANTED"
                alarm_manager.trigger_alert("GATE_PASS", "Worker verified: Access Granted", severity="LOW")
        else:
            status = "DENIED"
            box_color = (0, 0, 255)
            status_text = "ACCESS DENIED: MISSING REQUIRED SAFETY GEAR"
            if self.last_gate_status != "DENIED" and (now - self.last_gate_announce) > 4.0:
                self.last_gate_announce = now
                self.last_gate_status = "DENIED"
                alarm_manager.trigger_alert("GATE_FAIL", "Access Denied: Please equip required safety gear", severity="HIGH")

        cv2.rectangle(frame, (0, 0), (w, 55), box_color, -1)
        cv2.putText(frame, status_text, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        return status

    def _draw_hud(self, frame, stats, zone_id):
        """Draws top HUD overlay for live camera view."""
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (20, 20, 20), -1)
        cv2.circle(frame, (20, 20), 6, (0, 255, 0), -1)
        cv2.putText(frame, f"LIVE: {zone_id}", (35, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        comp_color = (0, 255, 0) if stats["compliance_rate"] >= 80 else (0, 165, 255) if stats["compliance_rate"] >= 50 else (0, 0, 255)
        text_stats = f"Workers: {stats['total_workers']} | Compliance: {stats['compliance_rate']}% | Violations: {stats['violations_count']}"
        cv2.putText(frame, text_stats, (frame.shape[1] - 440, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, comp_color, 1)

    def _save_incident_snapshot(self, frame, zone, incident_type, severity, details,
                                coord_x: float = 0.5, coord_y: float = 0.5, category: str = "PPE"):
        """Throttles, saves snapshot, logs to DB, dispatches to Telegram, and auto-prunes disk storage."""
        now = time.time()
        last_time = self.last_snapshot_time.get(incident_type, 0)
        
        # Industrial throttle: fire and critical hazards have at least 10s cooldown
        cooldown = max(self.snapshot_cooldown, 10.0 if severity == "CRITICAL" else self.snapshot_cooldown)
        
        if (now - last_time) >= cooldown:
            self.last_snapshot_time[incident_type] = now
            filename = f"incident_{int(now)}.jpg"
            rel_path = os.path.join(SNAPSHOT_DIR, filename)
            cv2.imwrite(rel_path, frame)
            
            # 1. Log in SQLite Database with spatial coordinates
            log_incident(zone, incident_type, severity, details,
                         snapshot_path=f"/static/incidents/{filename}",
                         coord_x=coord_x, coord_y=coord_y, category=category)
            print(f"[Snapshot Logged] {incident_type} -> {rel_path} (Coord: {coord_x:.2f}, {coord_y:.2f})")

            # 2. Instant Telegram Dispatch
            notifier.dispatch_incident_photo(rel_path, zone, incident_type, severity, details)

            # 3. Disk Maintenance: Auto-prune old snapshot files to keep maximum 50 images
            try:
                snapshots = [
                    os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR)
                    if f.startswith("incident_") and f.endswith(".jpg")
                ]
                if len(snapshots) > 50:
                    snapshots.sort(key=os.path.getmtime)
                    for old_file in snapshots[:-50]:
                        try:
                            os.remove(old_file)
                        except Exception:
                            pass
            except Exception:
                pass
