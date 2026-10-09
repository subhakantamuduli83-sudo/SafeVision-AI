import cv2
import threading
import time
import asyncio
import os
import json
from fastapi import FastAPI, Request, Response, BackgroundTasks, Form, Body, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from core.database import (
    init_db, get_recent_incidents, acknowledge_incident, get_incident_summary,
    get_heatmap_data, get_safety_scorecard, get_compliance_trend_data
)
from core.alarm import alarm_manager
from core.detector import SafetyDetector
from core.report_generator import generate_pdf_report, generate_pdf_bytes, generate_csv_report
from core.weather import weather_manager
from core.notifier import notifier, save_env_telegram
from core.copilot import copilot
from core.camera_manager import camera_manager

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

# Global Video Streaming & Processing State (Unified with ZoneCameraManager)
class VideoStreamManager:
    """Enterprise Stream Manager: Delegates capture & inference to camera_manager to prevent duplicate device binding and multi-threading overhead."""
    def __init__(self):
        self._zone_name = None
        self._camera_source = None
        self.lock = threading.Lock()

    @property
    def detector(self):
        return camera_manager.detector

    @property
    def zone_name(self):
        if self._zone_name:
            return self._zone_name
        return camera_manager.get_active_zone().get("name", "Zone 1 - Main Floor")

    @zone_name.setter
    def zone_name(self, val):
        self._zone_name = val

    @property
    def camera_source(self):
        if self._camera_source is not None:
            return self._camera_source
        active_zone = camera_manager.get_active_zone()
        cams = active_zone.get("cameras", [])
        if cams:
            for c in cams:
                if c["id"] == camera_manager.focused_cam_id:
                    return c.get("source", 0)
            return cams[0].get("source", 0)
        return 0

    @camera_source.setter
    def camera_source(self, val):
        self._camera_source = val

    @property
    def current_stats(self):
        return camera_manager.get_focused_stats()

    @property
    def current_frame(self):
        worker = camera_manager.get_focused_worker()
        return worker.current_frame if worker else None

    def set_source(self, source, zone_name="Zone 1 - Main Floor"):
        self._camera_source = source
        self._zone_name = zone_name
        camera_manager.update_camera_source(camera_manager.focused_cam_id, source, zone_name=zone_name)
        print(f"[Stream Manager] Synchronized camera source to: {source} ({zone_name})")

    def get_jpeg(self):
        return camera_manager.get_focused_jpeg()

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

async def generate_video_feed(request: Request):
    while True:
        if await request.is_disconnected():
            break
        frame_bytes = stream_manager.get_jpeg()
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        await asyncio.sleep(0.02)

@app.get("/video_feed")
async def video_feed(request: Request):
    return StreamingResponse(
        generate_video_feed(request),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

async def generate_camera_feed(request: Request, cam_id: str):
    while True:
        if await request.is_disconnected():
            break
        frame_bytes = camera_manager.get_camera_jpeg(cam_id)
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        await asyncio.sleep(0.025)

@app.get("/api/stream/{cam_id}")
async def stream_single_camera(request: Request, cam_id: str):
    return StreamingResponse(
        generate_camera_feed(request, cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/snapshot/{cam_id}")
async def camera_snapshot(cam_id: str):
    """Returns a single JPEG frame and immediately closes connection (saving browser socket limits)."""
    frame_bytes = camera_manager.get_camera_jpeg(cam_id)
    if frame_bytes is not None:
        return Response(content=frame_bytes, media_type="image/jpeg")
    return Response(status_code=404)

# ================= Zone & Multi-Camera Endpoints =================
@app.get("/api/zones")
async def get_all_zones():
    return camera_manager.get_all_zones()

@app.post("/api/zones/active")
async def switch_active_zone(zone_id: str = Form(...)):
    success = camera_manager.set_active_zone(zone_id)
    stream_manager.zone_name = camera_manager.get_active_zone().get("name", "Zone 1 - Main Floor")
    return {"status": "success" if success else "error", "data": camera_manager.get_all_zones()}

@app.post("/api/zones/add")
async def add_new_zone(name: str = Form(...), description: str = Form("")):
    new_z = camera_manager.add_zone(name, description)
    return {"status": "success", "zone": new_z, "data": camera_manager.get_all_zones()}

@app.post("/api/zones/delete")
async def delete_zone(zone_id: str = Form(...)):
    ok = camera_manager.delete_zone(zone_id)
    return {"status": "success" if ok else "error", "data": camera_manager.get_all_zones()}

@app.get("/api/zone/cameras")
async def get_active_zone_cameras():
    return {
        "active_zone": camera_manager.get_active_zone(),
        "cameras": camera_manager.get_active_zone_cameras_status(),
        "focused_cam_id": camera_manager.focused_cam_id
    }

@app.post("/api/zone/camera/focus")
async def set_camera_focus(cam_id: str = Form(...)):
    camera_manager.set_focused_camera(cam_id)
    return {"status": "success", "focused_cam_id": cam_id}

@app.post("/api/zones/{zone_id}/cameras/add")
async def add_camera_to_zone(
    zone_id: str,
    name: str = Form(...),
    source: str = Form(...),
    cam_type: str = Form("industrial_feed"),
    focus: str = Form("General Safety")
):
    new_cam = camera_manager.add_camera_to_zone(zone_id, name, source, cam_type, focus)
    return {"status": "success" if new_cam else "error", "camera": new_cam}

@app.post("/api/zones/{zone_id}/cameras/delete")
async def delete_camera_from_zone(zone_id: str, cam_id: str = Form(...)):
    ok = camera_manager.delete_camera_from_zone(zone_id, cam_id)
    return {"status": "success" if ok else "error"}

@app.get("/api/stats")
async def get_stats():
    summary = get_incident_summary()
    weather_data = weather_manager.last_successful_data or {}
    det = stream_manager.detector
    return {
        "live": stream_manager.current_stats,
        "summary": summary,
        "alarm_enabled": alarm_manager.enabled,
        "is_muted": alarm_manager.is_muted,
        "camera_source": str(stream_manager.camera_source),
        "zone_name": stream_manager.zone_name,
        "gate_mode": det.gate_mode,
        "danger_zone": {
            "enabled": det.danger_zone_enabled,
            "name": det.danger_zone_name,
            "poly": det.danger_zone_poly_norm
        },
        "modules": {
            "height_safety": det.height_safety_enabled,
            "suspended_load": det.suspended_load_enabled,
            "confined_space": {
                "enabled": det.confined_space_enabled,
                "name": det.confined_space_name,
                "headcount": len(det.confined_workers_active),
                "safe_minutes": int(det.confined_max_safe_seconds / 60)
            },
            "hot_work": det.hot_work_enabled,
            "trench_safety": det.trench_safety_enabled,
            "night_mode": det.night_mode_enabled
        },
        "telegram_enabled": notifier.telegram_enabled,
        "weather": {
            "temperature": weather_data.get("temperature"),
            "humidity": weather_data.get("humidity"),
            "heat_index": weather_data.get("heat_index"),
            "risk_level": weather_data.get("risk_level", "LOW"),
            "api_status": weather_manager.last_api_status,
            "is_demo": weather_manager.demo_mode
        },
        "sensitivity": {
            "level": getattr(det, "sensitivity_level", "ultra"),
            "conf_thresh": det.conf_thresh,
            "cooldown": det.snapshot_cooldown,
            "strictness": getattr(det, "ppe_strictness", "ultra")
        },
        "feature_matrix": det.get_feature_matrix(),
        "intel_mode": getattr(det, "intel_mode", "Intel AI Boost NPU + Arc GPU Dual-Engine")
    }

# ================= AI Detection Sensitivity Endpoints =================
@app.get("/api/sensitivity")
async def get_sensitivity():
    det = stream_manager.detector
    return {
        "status": "success",
        "level": getattr(det, "sensitivity_level", "ultra"),
        "conf_thresh": det.conf_thresh,
        "cooldown": det.snapshot_cooldown,
        "strictness": getattr(det, "ppe_strictness", "ultra")
    }

@app.post("/api/sensitivity")
async def update_sensitivity(
    level: str = Form(None),
    conf_thresh: float = Form(None),
    cooldown: float = Form(None)
):
    det = stream_manager.detector
    result = det.set_sensitivity(level=level, conf_thresh=conf_thresh, cooldown=cooldown)
    camera_manager.invalidate_static_caches()
    return {"status": "success", **result}

# ================= Master Feature Switchboard & Auto-Pilot Endpoints =================
@app.get("/api/master-control/status")
async def get_master_control_status():
    det = stream_manager.detector
    matrix = det.get_feature_matrix()
    return {
        "status": "success",
        "auto_pilot_mode": det.auto_pilot_mode,
        "auto_pilot": det.auto_pilot_mode,
        "matrix": matrix,
        "features": matrix
    }

@app.post("/api/master-control/toggle")
async def toggle_master_feature(feature: str = Form(...), enabled: bool = Form(...)):
    det = stream_manager.detector
    det.set_feature_toggle(feature, enabled)
    camera_manager.invalidate_static_caches()
    matrix = det.get_feature_matrix()
    return {
        "status": "success",
        "feature": feature,
        "enabled": enabled,
        "auto_pilot_mode": det.auto_pilot_mode,
        "matrix": matrix,
        "features": matrix
    }

@app.post("/api/master-control/preset")
async def apply_master_preset(preset_name: str = Form(None), preset: str = Form(None)):
    target_preset = preset_name or preset or "clean_ppe_only"
    det = stream_manager.detector
    matrix = det.apply_preset(target_preset)
    camera_manager.invalidate_static_caches()
    return {
        "status": "success",
        "preset": target_preset,
        "auto_pilot_mode": det.auto_pilot_mode,
        "auto_pilot": det.auto_pilot_mode,
        "matrix": matrix,
        "features": matrix
    }

# ================= Advanced Construction & Industrial Modules Endpoints =================
@app.get("/api/modules/status")
async def get_modules_status():
    det = stream_manager.detector
    return {
        "height_safety": det.height_safety_enabled,
        "suspended_load": det.suspended_load_enabled,
        "confined_space": {
            "enabled": det.confined_space_enabled,
            "name": det.confined_space_name,
            "headcount": len(det.confined_workers_active),
            "safe_minutes": int(det.confined_max_safe_seconds / 60),
            "entered": det.confined_total_entered,
            "exited": det.confined_total_exited
        },
        "hot_work": det.hot_work_enabled,
        "trench_safety": det.trench_safety_enabled,
        "night_mode": det.night_mode_enabled,
        "gate_mode": det.gate_mode,
        "danger_zone": det.danger_zone_enabled
    }

@app.post("/api/modules/toggle")
async def toggle_module(
    module: str = Form(...),
    enabled: bool = Form(...),
    param: str = Form(None)
):
    """Dynamically enables/disables any of the 5 new industrial safety modules."""
    det = stream_manager.detector
    if module == "height_safety":
        det.set_height_safety(enabled)
    elif module == "suspended_load":
        det.set_suspended_load(enabled)
    elif module == "confined_space":
        det.set_confined_space(enabled, name=param)
    elif module == "hot_work":
        det.set_hot_work(enabled)
    elif module == "trench_safety":
        det.set_trench_safety(enabled)
    elif module == "night_mode":
        det.set_night_mode(enabled)
    elif module == "gate_mode":
        det.set_gate_mode(enabled)
    
    camera_manager.invalidate_static_caches()
    return {"status": "success", "module": module, "enabled": enabled}

@app.post("/api/confined-space/reset")
async def reset_confined_space():
    stream_manager.detector.reset_confined_space()
    return {"status": "success", "message": "Confined space headcount reset to 0"}

# ================= AI Safety Copilot Endpoints =================
@app.post("/api/copilot/chat")
async def copilot_chat(query: str = Form(...)):
    """Conversational AI Safety Advisor grounded in real database records & OSHA standards."""
    weather_data = weather_manager.last_successful_data or {}
    result = copilot.ask(query, weather_context=weather_data)
    return result

# ================= Danger Zone Geofencing Endpoints =================
@app.get("/api/danger-zone")
async def get_danger_zone():
    return {
        "enabled": stream_manager.detector.danger_zone_enabled,
        "name": stream_manager.detector.danger_zone_name,
        "polygon": stream_manager.detector.danger_zone_poly_norm
    }

@app.post("/api/danger-zone")
async def update_danger_zone(
    enabled: bool = Form(...),
    name: str = Form("Heavy Machinery Perimeter"),
    poly_json: str = Form(None)
):
    poly = None
    if poly_json:
        try:
            poly = json.loads(poly_json)
        except Exception:
            pass
    stream_manager.detector.set_danger_zone(enabled, name, poly)
    return {
        "status": "success",
        "enabled": stream_manager.detector.danger_zone_enabled,
        "name": stream_manager.detector.danger_zone_name
    }

# ================= Smart Entry Gate Turnstile Mode =================
@app.post("/api/mode/gate")
async def toggle_gate_mode(enabled: bool = Form(...)):
    stream_manager.detector.set_gate_mode(enabled)
    return {
        "status": "success",
        "gate_mode": stream_manager.detector.gate_mode
    }

# ================= Instant Telegram Alert Endpoints =================
@app.get("/api/telegram/config")
async def get_telegram_config():
    return {
        "enabled": notifier.telegram_enabled,
        "has_token": bool(notifier.telegram_token),
        "token": notifier.telegram_token,
        "chat_id": notifier.telegram_chat_id,
        "is_configured": notifier.is_configured()
    }

@app.post("/api/telegram/config")
async def update_telegram_config(
    token: str = Form(""),
    chat_id: str = Form(""),
    enabled: bool = Form(True)
):
    token = token.strip()
    chat_id = chat_id.strip()
    res = notifier.update_config(token, chat_id, enabled)
    save_env_telegram(token, chat_id, enabled)
    return {"status": "success", "config": res}

@app.post("/api/telegram/test")
async def test_telegram_alert(token: str = Form(None), chat_id: str = Form(None), mock: bool = Form(False)):
    if token is not None and chat_id is not None:
        token = token.strip()
        chat_id = chat_id.strip()
        if token and chat_id:
            notifier.update_config(token, chat_id, True)
            save_env_telegram(token, chat_id, True)
    res = notifier.send_test_alert(force_mock=mock)
    return res

# ================= Analytics: 2D Spatial Heatmap & Executive Scorecard =================
@app.get("/api/analytics/heatmap")
async def get_heatmap():
    data = get_heatmap_data(limit=150)
    return {"points": data}

@app.get("/api/analytics/scorecard")
async def get_scorecard():
    card = get_safety_scorecard()
    return card

@app.get("/api/analytics/compliance-trend")
async def get_compliance_trend():
    """Returns hourly compliance score trends and official AI model benchmark metrics (Precision, Recall, Latency)."""
    return get_compliance_trend_data()

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

UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload-media")
async def upload_media(file: UploadFile = File(...), zone: str = Form("Inspection Test Zone")):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if not ext:
            ext = ".jpg"
        save_path = os.path.join(UPLOAD_DIR, f"inspect_feed{ext}")
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
        
        # Switch stream manager to this file immediately
        stream_manager.set_source(save_path, zone_name=zone)
        
        # Immediate one-shot detection
        stats = {}
        img = cv2.imread(save_path)
        if img is not None:
            _, stats = stream_manager.detector.process_frame(img, zone_id=zone)
            
        return {
            "status": "success",
            "filename": file.filename,
            "source_path": save_path,
            "zone": zone,
            "stats": stats,
            "fire_detected": stats.get("fire_detected", False),
            "violations_count": stats.get("violations_count", 0),
            "active_violations": stats.get("active_violations", [])
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

FEATURE_SIREN_TESTS = {
    "helmet": ("PPE_HELMET", "Safety Alert: Hardhat helmet required in work zone!", "HIGH"),
    "vest": ("PPE_VEST", "Safety Notice: High-visibility vest required in work zone!", "HIGH"),
    "gloves": ("PPE_GLOVES", "Safety Notice: Industrial protective gloves required in work zone!", "HIGH"),
    "goggles": ("PPE_GOGGLES", "Safety Alert: Eye protection goggles required in work zone!", "HIGH"),
    "harness": ("HARNESS", "Critical Warning: Fall arrest safety harness mandatory at height!", "CRITICAL"),
    "fall": ("FALL", "Emergency! Worker fallen or collapsed in Zone 1!", "CRITICAL"),
    "crane": ("SUSPENDED_LOAD", "Danger! Stand clear of crane suspended load drop zone!", "CRITICAL"),
    "fire": ("FIRE", "Emergency! Fire hazard detected in Zone 1! Evacuate immediately!", "CRITICAL"),
    "confined": ("CONFINED_SPACE", "Alert: Confined space safe stay time limit exceeded!", "HIGH"),
    "welding": ("HOT_WORK", "Caution: Hot work active without fire extinguisher in proximity!", "HIGH"),
    "trench": ("TRENCH_MARGIN", "Warning: Stand back from excavation trench collapse edge!", "HIGH"),
    "geofence": ("GEOFENCE", "Warning: Unauthorized worker in restricted machinery perimeter!", "CRITICAL"),
    "night": ("NIGHT_INTRUSION", "Security Alert: Unauthorized intrusion detected in lockdown zone!", "CRITICAL"),
    "gate_pass": ("GATE_PASS", "Worker verified: Access Granted", "LOW"),
    "gate_fail": ("GATE_FAIL", "Access Denied: Please equip mandatory safety gear", "HIGH"),
    "phone": ("PHONE", "Notice: Mobile phone use prohibited in active machinery zone!", "HIGH"),
    "proximity": ("PROXIMITY", "Caution: Machinery collision proximity hazard!", "HIGH"),
    "forklift": ("PROXIMITY", "Caution: Machinery collision proximity hazard!", "HIGH"),
    "heat": ("HEAT_HAZARD", "Caution: High heat index thermal warning in factory area!", "HIGH"),
    "thermal": ("HEAT_HAZARD", "Caution: High heat index thermal warning in factory area!", "HIGH"),
    "weather": ("HEAT_HAZARD", "Caution: High heat index thermal warning in factory area!", "HIGH"),
    "general_test": ("MASTER_TEST", "Attention: SafeVision AI Industrial Master Speaker Siren Active.", "CRITICAL"),
    "master": ("MASTER_TEST", "Attention: SafeVision AI Industrial Master Speaker Siren Active.", "CRITICAL"),
    "speaker": ("MASTER_TEST", "Attention: SafeVision AI Industrial Master Speaker Siren Active.", "CRITICAL"),
    "autopilot": ("AUTOPILOT", "SafeVision Auto-Pilot Armed: Autonomous Supervisor Mode Active.", "LOW"),
}

@app.post("/api/alarm/toggle")
async def toggle_alarm(mute: bool = Form(None), trigger_test: bool = Form(False)):
    if mute is not None:
        alarm_manager.set_muted(mute)
    if trigger_test:
        alarm_manager.trigger_alert("MASTER_TEST", "Attention: SafeVision AI Safety Siren Audio Test.", severity="CRITICAL", force=True)
    return {"status": "success", "is_muted": alarm_manager.is_muted}

@app.post("/api/alarm/test/{feature_key}")
async def test_feature_siren(feature_key: str):
    fkey = feature_key.lower().strip()
    if fkey in FEATURE_SIREN_TESTS:
        atype, msg, sev = FEATURE_SIREN_TESTS[fkey]
        alarm_manager.trigger_alert(atype, msg, severity=sev, force=True)
        return {"status": "success", "feature": fkey, "alert_type": atype, "message": msg, "severity": sev}
    alarm_manager.trigger_alert("MASTER_TEST", "Attention: SafeVision AI Safety Siren Audio Test.", severity="CRITICAL", force=True)
    return {"status": "success", "feature": "general_test"}

@app.get("/api/export/pdf")
async def export_pdf():
    try:
        pdf_bytes = generate_pdf_bytes()
        # Cache local copy silently on disk
        try:
            with open("Safety_Compliance_Audit_Report.pdf", "wb") as f:
                f.write(pdf_bytes)
        except Exception:
            pass
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="Safety_Compliance_Audit_Report.pdf"'}
        )
    except Exception as e:
        if os.path.exists("Safety_Compliance_Audit_Report.pdf"):
            return FileResponse("Safety_Compliance_Audit_Report.pdf", filename="Safety_Compliance_Audit_Report.pdf", media_type="application/pdf")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/export/presentation")
async def export_presentation():
    pres_path = "SafeVision_AI_Presentation.pdf"
    if os.path.exists(pres_path):
        return FileResponse(pres_path, filename="SafeVision_AI_Presentation.pdf", media_type="application/pdf")
    return JSONResponse({"status": "error", "message": "Presentation PDF not found"}, status_code=404)

@app.get("/api/export/csv")
async def export_csv():
    csv_content = generate_csv_report()
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=safety_incidents.csv"})

@app.post("/api/system/shutdown")
async def shutdown_system():
    """Gracefully terminates the AI server and Python process after brief delay."""
    def _delayed_exit():
        time.sleep(0.6)
        print("\n[SafeVision AI] Shutdown requested via Web Dashboard. Server stopped.")
        os._exit(0)
    threading.Thread(target=_delayed_exit, daemon=True).start()
    return {"status": "success", "message": "SafeVision AI is shutting down..."}


if __name__ == "__main__":
    print("Starting AI Safety Compliance Server on port 8000...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
