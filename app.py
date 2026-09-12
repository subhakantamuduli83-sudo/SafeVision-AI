import cv2
import threading
import time
import os
from fastapi import FastAPI, Request, Response, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from core.database import init_db, get_recent_incidents, acknowledge_incident, get_incident_summary
from core.alarm import alarm_manager
from core.detector import SafetyDetector
from core.report_generator import generate_pdf_report, generate_csv_report
from core.weather import weather_manager

# Initialize database
init_db()

app = FastAPI(title="Industrial AI Safety Compliance System")

# Ensure static directories exist
os.makedirs(os.path.join("static", "css"), exist_ok=True)
os.makedirs(os.path.join("static", "js"), exist_ok=True)
os.makedirs(os.path.join("static", "incidents"), exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global Video Streaming & Processing State
class VideoStreamManager:
    def __init__(self):
        self.camera_source = 0 # Default: Laptop webcam or change to IP URL
        self.zone_name = "Zone 1 - Main Floor"
        self.cap = None
        self.detector = SafetyDetector()
        self.current_frame = None
        self.current_stats = {
            "total_workers": 0,
            "compliant_workers": 0,
            "violations_count": 0,
            "compliance_rate": 100.0,
            "fire_detected": False,
            "active_violations": [],
            "timestamp": "--:--:--"
        }
        self.is_running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _sanitize_source(self, source):
        if isinstance(source, str):
            source = source.strip().strip('"').strip("'")
            if source.isdigit():
                return int(source)
            # Auto-prefix http:// if missing on IP inputs
            if not source.startswith("http://") and not source.startswith("https://") and not source.startswith("rtsp://") and not os.path.exists(source):
                if any(x in source for x in [":4747", ":8080", ":8000", ":8554", "/video", "/mjpegfeed"]):
                    source = "http://" + source

            # Automatic formatting for DroidCam and IP Webcam URLs
            if source.startswith("http://") or source.startswith("https://"):
                # DroidCam (Port 4747)
                if ":4747" in source and not any(source.endswith(x) for x in ["/video", "/mjpegfeed"]):
                    source = source.rstrip("/") + "/video"
                # IP Webcam (Port 8080)
                elif ":8080" in source and not any(source.endswith(x) for x in ["/video", "/videofeed", "/shot.jpg"]):
                    source = source.rstrip("/") + "/video"
        return source

    def set_source(self, source, zone_name="Zone 1 - Main Floor"):
        cleaned_source = self._sanitize_source(source)
        with self.lock:
            self.zone_name = zone_name
            self.camera_source = cleaned_source
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
        print(f"[Stream Manager] Switched camera source to: {self.camera_source} ({self.zone_name})")

    def _open_camera(self):
        try:
            print(f"[Stream Manager] Attempting to open video source: {self.camera_source}")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000"
            cap = cv2.VideoCapture(self.camera_source)
            if isinstance(self.camera_source, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
            elif isinstance(self.camera_source, str) and self.camera_source.startswith("http"):
                # Lower buffer size for network streams to avoid lag
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        except Exception as e:
            print(f"[Stream Error] Open camera failed: {e}")
            return None

    def _create_fallback_frame(self, message="Awaiting Video Feed..."):
        """Generates a placeholder frame when camera is connecting or disconnected."""
        img = 30 * np.ones((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "AI SAFETY MONITORING SYSTEM", (140, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(img, message, (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(img, f"Source: {self.camera_source}", (140, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        return img

    def _capture_loop(self):
        import numpy as np
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                self.cap = self._open_camera()
                if self.cap is None or not self.cap.isOpened():
                    # Generate placeholder
                    fallback = self._create_fallback_frame("Connecting to Camera Stream...")
                    with self.lock:
                        self.current_frame = fallback
                    time.sleep(1.5)
                    continue

            ret, raw_frame = self.cap.read()
            if not ret or raw_frame is None:
                print("[Stream Warning] Frame grab failed, retrying...")
                with self.lock:
                    self.current_frame = self._create_fallback_frame("Reconnecting to stream...")
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(1.0)
                continue

            # Process frame with AI Detector
            processed_frame, stats = self.detector.process_frame(raw_frame, zone_id=self.zone_name)
            
            with self.lock:
                self.current_frame = processed_frame
                self.current_stats = stats

            # Small sleep to regulate CPU utilization
            time.sleep(0.02)

    def get_jpeg(self):
        with self.lock:
            if self.current_frame is None:
                return None
            ret, jpeg = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                return jpeg.tobytes()
            return None

stream_manager = VideoStreamManager()


# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    try:
        # Starlette 0.36+ syntax: request as keyword argument
        return templates.TemplateResponse(request=request, name="index.html")
    except Exception:
        # Bulletproof fallback: Read index.html directly
        with open(os.path.join("templates", "index.html"), "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

def generate_video_feed():
    while True:
        frame_bytes = stream_manager.get_jpeg()
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04) # ~25 FPS

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_video_feed(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/stats")
async def get_stats():
    summary = get_incident_summary()
    weather_data = weather_manager.last_successful_data or {}
    return {
        "live": stream_manager.current_stats,
        "summary": summary,
        "alarm_enabled": alarm_manager.enabled,
        "is_muted": alarm_manager.is_muted,
        "camera_source": str(stream_manager.camera_source),
        "zone_name": stream_manager.zone_name,
        "weather": {
            "temperature": weather_data.get("temperature"),
            "humidity": weather_data.get("humidity"),
            "heat_index": weather_data.get("heat_index"),
            "risk_level": weather_data.get("risk_level", "LOW"),
            "api_status": weather_manager.last_api_status,
            "is_demo": weather_manager.demo_mode
        }
    }

@app.get("/api/weather/current")
async def get_current_weather():
    """Returns real-time weather, calculated Heat Index, risk evaluation, and explainable reasons."""
    data = weather_manager.fetch_weather_data(force=False)
    return data

@app.post("/api/weather/refresh")
async def refresh_weather():
    """Forces an immediate refresh from the Real-Time Weather API."""
    data = weather_manager.fetch_weather_data(force=True)
    return data

@app.get("/api/weather/history")
async def get_weather_history(limit: int = 30):
    """Returns historical time-series data for multi-metric graphs."""
    history = weather_manager.get_history(limit=limit)
    return {"history": history}

@app.post("/api/weather/demo-mode")
async def toggle_demo_mode(
    enabled: bool = Form(...),
    temp: float = Form(None),
    humidity: float = Form(None)
):
    """Toggles Demo Simulation Mode with explicit labeling."""
    data = weather_manager.set_demo_mode(enabled, temp, humidity)
    return {
        "status": "success",
        "demo_mode": weather_manager.demo_mode,
        "weather": data
    }

@app.post("/api/weather/config")
async def update_weather_config(
    location: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    thresh_mod: float = Form(32.0),
    thresh_high: float = Form(39.0),
    thresh_crit: float = Form(46.0)
):
    """Updates weather location coordinates and risk thresholds."""
    data = weather_manager.update_config(location, lat, lon, thresh_mod, thresh_high, thresh_crit)
    return {"status": "success", "weather": data}

@app.get("/api/incidents")
async def get_incidents():
    incidents = get_recent_incidents(limit=25)
    return {"incidents": incidents}

@app.post("/api/acknowledge/{incident_id}")
async def acknowledge(incident_id: int):
    acknowledge_incident(incident_id)
    return {"status": "success", "id": incident_id}

@app.post("/api/settings")
async def update_settings(source: str = Form(...), zone: str = Form("Zone 1 - Factory Floor")):
    stream_manager.set_source(source.strip(), zone.strip())
    return {"status": "success", "source": source, "zone": zone}

@app.post("/api/alarm/toggle")
async def toggle_alarm(mute: bool = Form(None), trigger_test: bool = Form(False)):
    if mute is not None:
        alarm_manager.set_muted(mute)
    if trigger_test:
        alarm_manager.trigger_alert("TEST", "Attention: Safety Siren Audio Test.", severity="HIGH")
    return {"status": "success", "is_muted": alarm_manager.is_muted}

@app.get("/api/export/pdf")
async def export_pdf():
    pdf_path = generate_pdf_report("Safety_Compliance_Audit_Report.pdf")
    return FileResponse(pdf_path, filename="Safety_Compliance_Audit_Report.pdf", media_type="application/pdf")

@app.get("/api/export/csv")
async def export_csv():
    csv_content = generate_csv_report()
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=safety_incidents.csv"})


if __name__ == "__main__":
    print("Starting AI Safety Compliance Server on port 8000...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
