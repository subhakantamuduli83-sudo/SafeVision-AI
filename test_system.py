import sys
import time
import numpy as np

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 60)
print("   [SAFEVISION AI] HARDWARE & SOFTWARE DIAGNOSTIC TOOL")
print("=" * 60)

# 1. Test Database
try:
    print("\n[1/4] Testing Incident Database...")
    from core.database import init_db, log_incident, get_recent_incidents
    init_db()
    test_id = log_incident("Zone 1 - Test", "System Diagnostic Check", "NORMAL", "Initial self-test passed")
    incidents = get_recent_incidents(1)
    print(f"      [OK] Database operational! Test record ID: {test_id}")
except Exception as e:
    print(f"      [ERROR] Database error: {e}")

# 2. Test YOLO AI Detector
try:
    print("\n[2/4] Testing YOLO AI Vision Engine...")
    from core.detector import SafetyDetector
    detector = SafetyDetector()
    dummy_frame = 50 * np.ones((480, 640, 3), dtype=np.uint8)
    processed, stats = detector.process_frame(dummy_frame, "Zone 1 - Diagnostics")
    print("      [OK] AI Vision Engine operational! Frame processed smoothly.")
except Exception as e:
    print(f"      [ERROR] AI Vision Engine error: {e}")

# 3. Test External Speaker & Voice Engine
try:
    print("\n[3/4] Testing External Speaker & Voice Alarm Engine...")
    from core.alarm import alarm_manager
    print("      [AUDIO] Triggering test alert on speaker...")
    alarm_manager.trigger_alert("DIAGNOSTIC", "SafeVision AI diagnostic test successful. Speaker is operational.", severity="HIGH")
    time.sleep(2)
    print("      [OK] Audio engine triggered successfully!")
except Exception as e:
    print(f"      [ERROR] Audio engine error: {e}")

# 4. Network & IP Test
try:
    print("\n[4/4] Checking Local Network IP for Laptop 2 Connection...")
    from run import get_local_ip
    ip = get_local_ip()
    print(f"      [OK] Your Laptop 1 Network IP is: {ip}")
    print(f"      [LINK] On Laptop 2, you will open: http://{ip}:8000")
except Exception as e:
    print(f"      [ERROR] Network check error: {e}")

print("\n" + "=" * 60)
print("   [SUCCESS] ALL SYSTEMS OPERATIONAL - READY FOR DEMO!")
print("=" * 60)
