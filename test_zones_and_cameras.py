import unittest
from fastapi.testclient import TestClient
from app import app
from core.camera_manager import camera_manager

class TestZonesAndMultiCamera(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_zones(self):
        res = self.client.get("/api/zones")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("active_zone_id", data)
        self.assertIn("zones", data)
        self.assertGreaterEqual(len(data["zones"]), 1)
        
        # Verify default zone 1 exists
        z1 = next((z for z in data["zones"] if z["id"] == "zone_1"), None)
        self.assertIsNotNone(z1)
        self.assertGreaterEqual(len(z1["cameras"]), 1)

    def test_get_active_zone_cameras(self):
        res = self.client.get("/api/zone/cameras")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("active_zone", data)
        self.assertIn("cameras", data)
        self.assertGreaterEqual(len(data["cameras"]), 1)
        self.assertIn("id", data["cameras"][0])
        self.assertIn("name", data["cameras"][0])

    def test_add_and_delete_custom_zone(self):
        # 1. Add Zone 2
        res_add = self.client.post("/api/zones/add", data={
            "name": "Zone 2 - Scaffolding Heights",
            "description": "High elevation work zone"
        })
        self.assertEqual(res_add.status_code, 200)
        new_zone = res_add.json()["zone"]
        new_zone_id = new_zone["id"]
        self.assertEqual(new_zone["name"], "Zone 2 - Scaffolding Heights")

        # 2. Add Camera to Zone 2
        res_cam = self.client.post(f"/api/zones/{new_zone_id}/cameras/add", data={
            "name": "CAM 02 - Lifeline Inspector",
            "source": "static/images/features/height_safety_harness.jpg",
            "cam_type": "industrial_feed",
            "focus": "Harness 100% Tie-Off"
        })
        self.assertEqual(res_cam.status_code, 200)
        self.assertEqual(res_cam.json()["status"], "success")

        # 3. Switch to Zone 2
        res_switch = self.client.post("/api/zones/active", data={"zone_id": new_zone_id})
        self.assertEqual(res_switch.status_code, 200)
        self.assertEqual(camera_manager.config["active_zone_id"], new_zone_id)

        # 4. Switch back to Zone 1
        self.client.post("/api/zones/active", data={"zone_id": "zone_1"})
        self.assertEqual(camera_manager.config["active_zone_id"], "zone_1")

        # 5. Delete Zone 2
        res_del = self.client.post("/api/zones/delete", data={"zone_id": new_zone_id})
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "success")

    def test_set_camera_focus(self):
        res = self.client.post("/api/zone/camera/focus", data={"cam_id": "cam_02"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(camera_manager.focused_cam_id, "cam_02")

if __name__ == "__main__":
    unittest.main()
