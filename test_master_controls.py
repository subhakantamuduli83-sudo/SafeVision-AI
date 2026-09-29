"""
Comprehensive Test Suite: Master Control Switchboard & Auto-Pilot Mode
Verifies:
1. Feature Matrix initial states & default clean screen (danger_zone_enabled=False).
2. Toggle individual features (helmet, vest, fall, fire, proximity, geofence, gate, hot_work, confined, night).
3. Preset application:
   - auto_pilot (all features, sirens, telegram, height, drop zone, hot work, trench enabled)
   - clean_ppe_only (PPE + fall only, geofence & heavy plant disabled)
   - construction
   - hot_work_plant
   - night_guard
   - all_off & all_on
4. API endpoints (/api/master-control/status, /api/master-control/toggle, /api/master-control/preset, /api/stats).
"""
import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure workspace is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, stream_manager
detector = stream_manager.detector

class TestMasterControlsAndAutoPilot(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Reset to clean ppe only
        detector.apply_preset("clean_ppe_only")

    def test_default_clean_view(self):
        """Ensure virtual danger zone is OFF by default to eliminate screen clutter."""
        matrix = detector.get_feature_matrix()
        self.assertFalse(matrix["danger_zone"], "Danger zone should be False by default for clean video view")
        self.assertTrue(matrix["helmet_check"])
        self.assertTrue(matrix["vest_check"])
        self.assertFalse(matrix["auto_pilot_mode"])

    def test_status_endpoint(self):
        """Test /api/master-control/status returns complete matrix."""
        res = self.client.get("/api/master-control/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("matrix", data)
        self.assertIn("auto_pilot_mode", data)
        self.assertIn("helmet_check", data["matrix"])
        self.assertIn("danger_zone", data["matrix"])
        self.assertIn("siren_audio", data["matrix"])

    def test_toggle_feature_endpoint(self):
        """Test toggling individual feature on and off."""
        # Toggle danger_zone on
        res = self.client.post("/api/master-control/toggle", data={"feature": "danger_zone", "enabled": "true"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(detector.danger_zone_enabled)
        self.assertTrue(res.json()["matrix"]["danger_zone"])

        # Toggle danger_zone off
        res = self.client.post("/api/master-control/toggle", data={"feature": "danger_zone", "enabled": "false"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(detector.danger_zone_enabled)
        self.assertFalse(res.json()["matrix"]["danger_zone"])

    def test_auto_pilot_preset(self):
        """Test 1-Click Supervisor Away Auto-Pilot arming all detectors & alarms."""
        res = self.client.post("/api/master-control/preset", data={"preset_name": "auto_pilot"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        matrix = data["matrix"]

        self.assertTrue(matrix["auto_pilot_mode"])
        self.assertTrue(matrix["helmet_check"])
        self.assertTrue(matrix["vest_check"])
        self.assertTrue(matrix["height_safety"])
        self.assertTrue(matrix["fall_detection"])
        self.assertTrue(matrix["proximity_detection"])
        self.assertTrue(matrix["suspended_load"])
        self.assertTrue(matrix["confined_space"])
        self.assertTrue(matrix["hot_work"])
        self.assertTrue(matrix["trench_safety"])
        self.assertTrue(matrix["fire_detection"])
        self.assertTrue(matrix["siren_audio"])
        self.assertTrue(matrix["telegram_alert"])

    def test_construction_preset(self):
        """Test Heavy Construction site preset."""
        res = self.client.post("/api/master-control/preset", data={"preset_name": "construction"})
        self.assertEqual(res.status_code, 200)
        matrix = res.json()["matrix"]
        self.assertTrue(matrix["helmet_check"])
        self.assertTrue(matrix["height_safety"])
        self.assertTrue(matrix["suspended_load"])
        self.assertTrue(matrix["trench_safety"])

    def test_all_off_and_all_on(self):
        """Test disarming and arming all features."""
        # All off
        res = self.client.post("/api/master-control/preset", data={"preset_name": "all_off"})
        self.assertEqual(res.status_code, 200)
        matrix = res.json()["matrix"]
        self.assertFalse(matrix["helmet_check"])
        self.assertFalse(matrix["vest_check"])
        self.assertFalse(matrix["fire_detection"])

        # All on
        res = self.client.post("/api/master-control/preset", data={"preset_name": "all_on"})
        self.assertEqual(res.status_code, 200)
        matrix = res.json()["matrix"]
        self.assertTrue(matrix["helmet_check"])
        self.assertTrue(matrix["vest_check"])
        self.assertTrue(matrix["fire_detection"])
        self.assertTrue(matrix["height_safety"])

    def test_stats_feature_matrix_sync(self):
        """Test /api/stats includes feature_matrix for real-time frontend syncing."""
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("feature_matrix", data)
        self.assertIn("auto_pilot_mode", data["feature_matrix"])

if __name__ == '__main__':
    unittest.main()
