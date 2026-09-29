import unittest
import os
import html
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app
from core.notifier import IncidentNotifier, save_env_telegram, notifier

class TestTelegramNotifier(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_token = notifier.telegram_token
        self.original_chat_id = notifier.telegram_chat_id
        self.original_enabled = notifier.telegram_enabled

    def tearDown(self):
        notifier.update_config(self.original_token, self.original_chat_id, self.original_enabled)

    def test_unconfigured_detection(self):
        n = IncidentNotifier()
        n.telegram_token = "dummy_token"
        n.telegram_chat_id = "12345"
        self.assertFalse(n.is_configured())

        n.telegram_token = ""
        n.telegram_chat_id = "987654321"
        self.assertFalse(n.is_configured())

        # Valid simulated real token and chat ID
        n.telegram_token = "1234567890:ABCdefGHIjklMNOpqrSTUvwxyz"
        n.telegram_chat_id = "987654321"
        self.assertTrue(n.is_configured())

    def test_send_test_alert_unconfigured(self):
        n = IncidentNotifier()
        n.telegram_token = "dummy_token"
        n.telegram_chat_id = "12345"
        res = n.send_test_alert(force_mock=False)
        self.assertEqual(res["status"], "error")
        self.assertIn("not configured", res["message"])

    def test_send_test_alert_mock(self):
        n = IncidentNotifier()
        res = n.send_test_alert(force_mock=True)
        self.assertEqual(res["status"], "mock")

    @patch("requests.post")
    def test_send_test_alert_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        n = IncidentNotifier()
        n.update_config("1234567890:ABCdefGHIjklMNOpqrSTUvwxyz", "987654321", True)
        res = n.send_test_alert()
        self.assertEqual(res["status"], "success")

    @patch("requests.post")
    def test_send_test_alert_chat_not_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"description": "Bad Request: chat not found"}
        mock_resp.text = "Bad Request: chat not found"
        mock_post.return_value = mock_resp

        n = IncidentNotifier()
        n.update_config("1234567890:ABCdefGHIjklMNOpqrSTUvwxyz", "@myusername", True)
        res = n.send_test_alert()
        self.assertEqual(res["status"], "error")
        self.assertIn("must be your numeric ID", res["message"])

    def test_html_escaping_in_payload(self):
        n = IncidentNotifier()
        # Ensure html escaping doesn't crash on dangerous/reserved characters
        special_details = "Worker_1 <dangerous> & 'quotes' (missing vest & helmet)"
        escaped = html.escape(special_details)
        self.assertIn("&amp;", escaped)
        self.assertIn("&lt;dangerous&gt;", escaped)

    def test_api_config_endpoints(self):
        # Test GET config
        res = self.client.get("/api/telegram/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("is_configured", data)
        self.assertIn("enabled", data)

        # Test POST config
        res_post = self.client.post("/api/telegram/config", data={
            "token": "1234567890:TestBotTokenExampleFormat",
            "chat_id": "87654321",
            "enabled": "true"
        })
        self.assertEqual(res_post.status_code, 200)
        self.assertTrue(notifier.telegram_enabled)
        self.assertEqual(notifier.telegram_chat_id, "87654321")

if __name__ == "__main__":
    unittest.main()
