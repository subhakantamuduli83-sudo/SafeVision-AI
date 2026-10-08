import os
import cv2
import json
import time
import threading
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from core.detector import SafetyDetector

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONES_CONFIG_PATH = os.path.join(ROOT_DIR, "zones_config.json")

DEFAULT_ZONES_CONFIG = {
    "active_zone_id": "zone_1",
    "zones": [
        {
            "id": "zone_1",
            "name": "Zone 1 - Main Floor",
            "description": "Main Industrial Assembly Hall & Work Areas",
            "cameras": [
                {
                    "id": "cam_01",
                    "name": "CAM 01 - PPE Entry Gate",
                    "source": "0",
                    "type": "webcam",
                    "focus": "Turnstile Helmet & High-Vis Vest Inspection"
                },
                {
                    "id": "cam_02",
                    "name": "CAM 02 - Scaffolding Heights",
                    "source": "static/images/features/height_safety_harness.jpg",
                    "type": "industrial_feed",
                    "focus": "Elevated Lifeline & Safety Harness Compliance"
                },
                {
                    "id": "cam_03",
                    "name": "CAM 03 - Crane Suspended Load",
                    "source": "static/images/features/crane_suspended_load.jpg",
                    "type": "industrial_feed",
                    "focus": "Drop Zone Perimeter & Line of Fire Clearance"
                },
                {
                    "id": "cam_04",
                    "name": "CAM 04 - Hot Work & Welding Bay",
                    "source": "static/images/features/hot_work_welding.jpg",
                    "type": "industrial_feed",
                    "focus": "Welding Flash & Fire Extinguisher Readiness"
                }
            ]
        }
    ]
}


class ThreadedCameraReader:
    """
    Dedicated Zero-Latency Camera Grabber Thread.
    Continuously drains OpenCV's internal frame queue in a background daemon thread.
    Prevents TCP/HTTP network buffer overflow, eliminating stream freezing in DroidCam, RTSP, and USB webcams.
    """
    def __init__(self, cap, is_file: bool = False):
        self.cap = cap
        self.is_file = is_file
        self.lock = threading.Lock()
        self.latest_frame = None
        self.frame_id = 0
        self.is_running = True
        self.consecutive_empty = 0
        self.last_frame_ts = time.time()
        
        self.thread = threading.Thread(target=self._drain_loop, daemon=True)
        self.thread.start()

    def _drain_loop(self):
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.latest_frame = frame
                    self.frame_id += 1
                    self.consecutive_empty = 0
                    self.last_frame_ts = time.time()
                if self.is_file:
                    time.sleep(0.033) # 30 FPS pacing for local video files
                else:
                    time.sleep(0.008) # ~120 FPS continuous buffer drainage (low CPU context switching)
            else:
                if self.is_file and self.cap:
                    # Loop video file smoothly
                    try:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    except Exception:
                        pass
                    time.sleep(0.03)
                    continue
                with self.lock:
                    self.consecutive_empty += 1
                time.sleep(0.02)

    def read(self) -> Tuple[bool, Optional[np.ndarray], int]:
        with self.lock:
            if self.latest_frame is not None:
                if not self.is_file and (time.time() - self.last_frame_ts) > 4.5:
                    return False, None, self.frame_id
                return True, self.latest_frame, self.frame_id
            return False, None, 0

    def release(self):
        self.is_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None


class SingleCameraWorker:
    """Manages video capture, round-robin AI processing, and JPEG caching for one camera."""

    def __init__(self, cam_id: str, name: str, source: Any, cam_type: str, focus: str, zone_name: str, detector: SafetyDetector):
        self.cam_id = cam_id
        self.name = name
        self.raw_source = source
        self.cam_type = cam_type
        self.focus = focus
        self.zone_name = zone_name
        self.detector = detector

        self.reader: Optional[ThreadedCameraReader] = None
        self.last_annotated_frame = None
        self.is_running = True
        self.lock = threading.Lock()
        
        self.current_frame = None
        self.cached_jpeg = None
        self.stats = {
            "total_workers": 0,
            "compliant_workers": 0,
            "violations_count": 0,
            "compliance_rate": 100.0,
            "fire_detected": False,
            "active_violations": [],
            "timestamp": "--:--:--"
        }
        self.last_ai_time = 0.0
        self.ai_interval = 0.08 # Ultra-responsive ~12 FPS AI evaluation powered by Intel AI Boost NPU (<22ms latency)
        self.needs_reprocess = True
        self.has_processed_static = False

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _sanitize_source(self, source):
        if isinstance(source, str):
            s = source.strip().strip('"').strip("'")
            if s.isdigit():
                return int(s)
            if not s.startswith("http://") and not s.startswith("https://") and not s.startswith("rtsp://") and not os.path.exists(s):
                if any(x in s for x in [":4747", ":8080", ":8000", ":8554", "/video", "/mjpegfeed"]):
                    s = "http://" + s
            return s
        return source

    def _open_camera(self) -> Optional[ThreadedCameraReader]:
        cleaned = self._sanitize_source(self.raw_source)
        try:
            if isinstance(cleaned, (int, str)) and (isinstance(cleaned, int) or cleaned.startswith("rtsp://") or cleaned.startswith("http://")):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2500000|buffer_size;1024000"
                if isinstance(cleaned, int):
                    # DirectShow for Windows USB webcams (zero latency, no freeze)
                    cap = cv2.VideoCapture(cleaned, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(cleaned)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                else:
                    cap = cv2.VideoCapture(cleaned)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if cap and cap.isOpened():
                    return ThreadedCameraReader(cap, is_file=False)
                return None

            elif isinstance(cleaned, str) and os.path.isfile(cleaned) and cleaned.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                cap = cv2.VideoCapture(cleaned)
                if cap and cap.isOpened():
                    return ThreadedCameraReader(cap, is_file=True)
                return None
        except Exception as e:
            print(f"[{self.name}] Camera open error: {e}")
        return None

    def _create_placeholder(self, message="Connecting..."):
        img = 25 * np.ones((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(img, (0, 0), (640, 480), (40, 45, 55), 2)
        cv2.putText(img, f"SAFEVISION CCTV: {self.name.upper()}", (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2)
        cv2.putText(img, message, (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(img, f"Focus: {self.focus}", (30, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)
        return img

    def _run_loop(self):
        cached_static_raw = None
        last_source_str = None

        while self.is_running:
            cleaned = self._sanitize_source(self.raw_source)
            if str(cleaned) != str(last_source_str):
                last_source_str = str(cleaned)
                cached_static_raw = None
                self.has_processed_static = False
                self.needs_reprocess = True
                if self.reader:
                    self.reader.release()
                    self.reader = None

            is_static_image = isinstance(cleaned, str) and (
                cleaned.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')) or
                (os.path.isfile(cleaned) and not cleaned.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')))
            )

            # 1. Static Industrial Photo Inspection (Zero CPU after initial processing)
            if is_static_image:
                if self.has_processed_static and not self.needs_reprocess:
                    time.sleep(0.04) # Rest at 0% CPU
                    continue

                if cached_static_raw is None and os.path.exists(cleaned):
                    cached_static_raw = cv2.imread(cleaned)

                raw_frame = cached_static_raw
                if raw_frame is not None:
                    try:
                        annotated, stats = self.detector.process_frame(raw_frame.copy(), zone_id=f"{self.zone_name} - {self.name}")
                        self._update_frame(annotated, stats)
                    except Exception as e:
                        print(f"[{self.name}] Static frame inference error: {e}")
                        self._update_frame(raw_frame, self.stats)
                    self.has_processed_static = True
                    self.needs_reprocess = False
                    time.sleep(0.04)
                    continue
                else:
                    placeholder = self._create_placeholder("Image Not Found")
                    self._update_frame(placeholder, self.stats)
                    time.sleep(1.0)
                    continue

            # 2. Live Video / RTSP / Webcam / DroidCam
            if self.reader is None:
                self.reader = self._open_camera()
                if self.reader is None:
                    placeholder = self._create_placeholder("Connecting to stream...")
                    self._update_frame(placeholder, self.stats)
                    time.sleep(1.0)
                    continue

            ret, frame, fid = self.reader.read()
            if not ret or frame is None:
                # Reconnect only if stream persistently lost for > 40 checks (~1.5s)
                if getattr(self.reader, "consecutive_empty", 0) > 40:
                    if self.reader:
                        self.reader.release()
                    self.reader = None
                    placeholder = self._create_placeholder("Reconnecting to stream...")
                    self._update_frame(placeholder, self.stats)
                    time.sleep(0.8)
                else:
                    time.sleep(0.01)
                continue

            # Skip redundant processing if camera hasn't delivered a new frame yet
            if fid == getattr(self, "last_processed_fid", -1) and not self.needs_reprocess:
                time.sleep(0.005)
                continue

            self.last_processed_fid = fid
            self.needs_reprocess = False
            raw_frame = frame

            # Real-time AI inference and frame dispatch (30 FPS Balanced Pacing)
            t_start = time.time()
            try:
                annotated, stats = self.detector.process_frame(raw_frame, zone_id=f"{self.zone_name} - {self.name}")
                self._update_frame(annotated, stats)
            except Exception as e:
                self._update_frame(raw_frame, self.stats)

            # Balanced 30 FPS Pacing:
            # Prevents 100% compute pegging on GPU/CPU while keeping camera video ultra-fluid (Zero Lag)
            elapsed = time.time() - t_start
            sleep_time = max(0.006, 0.033 - elapsed)
            time.sleep(sleep_time)

            # Periodic memory garbage collection: frees up tensor allocations every ~4 seconds
            if fid % 120 == 0:
                import gc
                gc.collect()

    def _update_frame(self, frame, stats):
        with self.lock:
            self.current_frame = frame
            self.stats = stats
            # Optimized 75% JPEG quality: ultra-crisp with minimal bandwidth & zero latency
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                self.cached_jpeg = jpeg.tobytes()

    def get_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self.cached_jpeg

    def set_source(self, new_source: Any, zone_name: Optional[str] = None):
        with self.lock:
            self.raw_source = new_source
            if zone_name:
                self.zone_name = zone_name
            self.needs_reprocess = True
            self.has_processed_static = False
            if self.reader:
                try:
                    self.reader.release()
                except Exception:
                    pass
                self.reader = None

    def reprocess(self):
        with self.lock:
            self.needs_reprocess = True
            self.last_ai_time = 0.0

    def stop(self):
        self.is_running = False
        if self.reader:
            try:
                self.reader.release()
            except Exception:
                pass
            self.reader = None


class ZoneCameraManager:
    """Enterprise Multi-Zone & Multi-Camera Orchestrator."""

    def __init__(self, detector: Optional[SafetyDetector] = None):
        self.detector = detector if detector is not None else SafetyDetector()
        self.lock = threading.Lock()
        self.config = self._load_config()
        self.workers: Dict[str, SingleCameraWorker] = {}
        self.focused_cam_id = "cam_01"

        # Start workers for the active zone
        self._sync_active_zone_workers()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(ZONES_CONFIG_PATH):
            try:
                with open(ZONES_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "zones" in data and len(data["zones"]) > 0:
                        return data
            except Exception as e:
                print(f"[Zone Manager] Error reading zones_config.json: {e}")
        
        # Save default config if not existing or invalid
        self._save_config(DEFAULT_ZONES_CONFIG)
        return DEFAULT_ZONES_CONFIG

    def _save_config(self, cfg: Dict[str, Any]):
        try:
            with open(ZONES_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"[Zone Manager] Error saving zones_config.json: {e}")

    def _sync_active_zone_workers(self):
        """Spins up workers for cameras in the currently active zone and stops others."""
        with self.lock:
            active_zone = self.get_active_zone()
            active_cams = active_zone.get("cameras", [])
            active_ids = {c["id"]: c for c in active_cams}

            # Stop workers no longer active
            for old_id in list(self.workers.keys()):
                if old_id not in active_ids:
                    self.workers[old_id].stop()
                    del self.workers[old_id]

            # Start or update workers for active zone
            for cam in active_cams:
                cid = cam["id"]
                if cid not in self.workers:
                    worker = SingleCameraWorker(
                        cam_id=cid,
                        name=cam["name"],
                        source=cam["source"],
                        cam_type=cam.get("type", "industrial_feed"),
                        focus=cam.get("focus", "General Safety"),
                        zone_name=active_zone["name"],
                        detector=self.detector
                    )
                    self.workers[cid] = worker

            # Ensure focused camera is valid
            if active_cams:
                if self.focused_cam_id not in active_ids:
                    self.focused_cam_id = active_cams[0]["id"]

    def get_all_zones(self) -> Dict[str, Any]:
        """Returns all configured zones, camera counts, and current active zone ID."""
        with self.lock:
            return {
                "active_zone_id": self.config.get("active_zone_id", "zone_1"),
                "active_zone_name": self.get_active_zone().get("name", "Zone 1 - Main Floor"),
                "zones": self.config.get("zones", []),
                "focused_cam_id": self.focused_cam_id
            }

    def get_active_zone(self) -> Dict[str, Any]:
        active_id = self.config.get("active_zone_id", "zone_1")
        for z in self.config.get("zones", []):
            if z["id"] == active_id:
                return z
        if self.config.get("zones"):
            return self.config["zones"][0]
        return DEFAULT_ZONES_CONFIG["zones"][0]

    def set_active_zone(self, zone_id: str) -> bool:
        """Switches the active zone and instantly reconfigures the camera grid."""
        with self.lock:
            found = False
            for z in self.config.get("zones", []):
                if z["id"] == zone_id:
                    self.config["active_zone_id"] = zone_id
                    found = True
                    break
            if found:
                self._save_config(self.config)
        
        if found:
            self._sync_active_zone_workers()
            print(f"[Zone Manager] Switched active zone to: {zone_id}")
            return True
        return False

    def add_zone(self, name: str, description: str = "") -> Dict[str, Any]:
        """Adds a new customizable zone."""
        with self.lock:
            clean_name = name.strip()
            new_id = f"zone_{len(self.config['zones']) + 1}_{int(time.time()) % 1000}"
            new_zone = {
                "id": new_id,
                "name": clean_name if clean_name else f"Zone {len(self.config['zones']) + 1}",
                "description": description.strip() if description else "Custom Industrial Safety Zone",
                "cameras": [
                    {
                        "id": f"cam_{new_id}_1",
                        "name": f"CAM 01 - {clean_name} Main",
                        "source": "static/images/features/helmet_inspection.jpg",
                        "type": "industrial_feed",
                        "focus": "PPE Helmet & Safety Vest Inspection"
                    }
                ]
            }
            self.config["zones"].append(new_zone)
            self._save_config(self.config)
            print(f"[Zone Manager] Added new zone: {new_zone['name']} ({new_id})")
            return new_zone

    def delete_zone(self, zone_id: str) -> bool:
        """Deletes a zone (must have at least one remaining)."""
        with self.lock:
            if len(self.config.get("zones", [])) <= 1:
                return False # Cannot delete the only zone
            self.config["zones"] = [z for z in self.config["zones"] if z["id"] != zone_id]
            if self.config.get("active_zone_id") == zone_id:
                self.config["active_zone_id"] = self.config["zones"][0]["id"]
            self._save_config(self.config)
        self._sync_active_zone_workers()
        return True

    def add_camera_to_zone(self, zone_id: str, name: str, source: str, cam_type: str = "industrial_feed", focus: str = "General Safety") -> Optional[Dict[str, Any]]:
        """Adds a camera to the specified zone."""
        with self.lock:
            target_zone = None
            for z in self.config.get("zones", []):
                if z["id"] == zone_id:
                    target_zone = z
                    break
            if not target_zone:
                return None
            
            cam_num = len(target_zone.get("cameras", [])) + 1
            new_cam_id = f"cam_{zone_id}_{cam_num}_{int(time.time()) % 1000}"
            new_cam = {
                "id": new_cam_id,
                "name": name.strip() if name.strip() else f"CAM {cam_num:02d} - {focus}",
                "source": source.strip(),
                "type": cam_type.strip(),
                "focus": focus.strip()
            }
            target_zone["cameras"].append(new_cam)
            self._save_config(self.config)
            print(f"[Zone Manager] Added camera '{new_cam['name']}' to zone {zone_id}")

        self._sync_active_zone_workers()
        return new_cam

    def delete_camera_from_zone(self, zone_id: str, cam_id: str) -> bool:
        """Deletes a camera from a zone."""
        with self.lock:
            for z in self.config.get("zones", []):
                if z["id"] == zone_id:
                    if len(z.get("cameras", [])) <= 1:
                        return False # Keep at least 1 camera
                    z["cameras"] = [c for c in z["cameras"] if c["id"] != cam_id]
                    self._save_config(self.config)
                    break
        self._sync_active_zone_workers()
        return True

    def set_focused_camera(self, cam_id: str) -> bool:
        with self.lock:
            self.focused_cam_id = cam_id
            return True

    def get_camera_jpeg(self, cam_id: str) -> Optional[bytes]:
        worker = self.workers.get(cam_id)
        if worker:
            return worker.get_jpeg()
        # Fallback placeholder
        return None

    def get_focused_jpeg(self) -> Optional[bytes]:
        """Returns JPEG of the currently focused camera for backward-compatible /video_feed."""
        if self.focused_cam_id in self.workers:
            return self.workers[self.focused_cam_id].get_jpeg()
        if self.workers:
            first_key = next(iter(self.workers))
            return self.workers[first_key].get_jpeg()
        return None

    def get_active_zone_cameras_status(self) -> List[Dict[str, Any]]:
        """Returns metadata & live safety statistics for each camera in the active zone."""
        res = []
        active_zone = self.get_active_zone()
        for cam in active_zone.get("cameras", []):
            cid = cam["id"]
            worker = self.workers.get(cid)
            stats = worker.stats if worker else {}
            res.append({
                "id": cid,
                "name": cam["name"],
                "source": cam["source"],
                "type": cam.get("type", "industrial_feed"),
                "focus": cam.get("focus", "General Safety"),
                "is_focused": cid == self.focused_cam_id,
                "stats": stats
            })
        return res

    def get_focused_stats(self) -> Dict[str, Any]:
        """Returns the real-time AI compliance statistics for the currently focused camera."""
        with self.lock:
            worker = self.workers.get(self.focused_cam_id)
            if worker and worker.stats:
                return worker.stats.copy()
            if self.workers:
                first_w = next(iter(self.workers.values()))
                return first_w.stats.copy()
            return {
                "total_workers": 0,
                "compliant_workers": 0,
                "violations_count": 0,
                "compliance_rate": 100.0,
                "fire_detected": False,
                "active_violations": [],
                "timestamp": "--:--:--"
            }

    def get_focused_worker(self) -> Optional[SingleCameraWorker]:
        with self.lock:
            return self.workers.get(self.focused_cam_id)

    def update_camera_source(self, cam_id: str, new_source: Any, zone_name: Optional[str] = None) -> bool:
        """Dynamically updates the source of a camera worker and persists to config."""
        with self.lock:
            worker = self.workers.get(cam_id)
            if worker:
                worker.set_source(new_source, zone_name)
            active_z = self.get_active_zone()
            for cam in active_z.get("cameras", []):
                if cam["id"] == cam_id:
                    cam["source"] = str(new_source)
                    break
            self._save_config(self.config)
            return True

    def invalidate_static_caches(self):
        """Signals all workers displaying static images to re-infer AI with new detector rules."""
        with self.lock:
            for worker in self.workers.values():
                worker.reprocess()

# Global orchestrator singleton
camera_manager = ZoneCameraManager()
