import os
import time
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any

def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[Notifier Env Error] Failed to read .env: {e}")

load_env_file()

class IncidentNotifier:
    """Dispatches real-time incident notifications and evidence snapshots to Telegram & Webhooks."""

    def __init__(self):
        load_env_file()
        self.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.webhook_url = os.environ.get("INCIDENT_WEBHOOK_URL", "").strip()
        self.last_sent_time = {}
        self.throttle_cooldown = 5.0 # Seconds cooldown between duplicate incident dispatches

    def update_config(self, token: str, chat_id: str, enabled: bool = True):
        self.telegram_token = token.strip()
        self.telegram_chat_id = chat_id.strip()
        self.telegram_enabled = enabled and bool(self.telegram_token and self.telegram_chat_id)
        return {
            "telegram_enabled": self.telegram_enabled,
            "has_token": bool(self.telegram_token),
            "chat_id": self.telegram_chat_id
        }

    def is_configured(self) -> bool:
        """Validates if a real Telegram Bot token and Chat ID are configured."""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        tok = self.telegram_token.lower()
        if "dummy" in tok or "test" in tok or len(self.telegram_token) < 15 or ":" not in self.telegram_token:
            return False
        if self.telegram_chat_id in ["12345", "0", "chat_id_here"]:
            return False
        return True

    def dispatch_incident_photo(self, photo_path: str, zone: str, incident_type: str, severity: str, details: str):
        """Asynchronously dispatches an incident snapshot with rich metadata."""
        now = time.time()
        dedup_key = f"{zone}_{incident_type}"
        if (now - self.last_sent_time.get(dedup_key, 0)) < self.throttle_cooldown:
            return # Throttled
        self.last_sent_time[dedup_key] = now

        # Run dispatch in a background daemon thread to avoid blocking the video pipeline
        thread = threading.Thread(
            target=self._send_payload,
            args=(photo_path, zone, incident_type, severity, details),
            daemon=True
        )
        thread.start()

    def _send_payload(self, photo_path: str, zone: str, incident_type: str, severity: str, details: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        severity_emoji = "🚨" if severity == "CRITICAL" else "⚠️" if severity == "HIGH" else "ℹ️"
        
        caption = (
            f"{severity_emoji} *SAFEVISION AI INCIDENT ALERT*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Zone:* `{zone}`\n"
            f"⚠️ *Type:* *{incident_type}*\n"
            f"⚡ *Severity:* `{severity}`\n"
            f"📝 *Details:* {details}\n"
            f"🕒 *Timestamp:* `{timestamp}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"_Automated Industrial Edge AI Dispatch_"
        )

        # 1. Telegram Dispatch
        if self.telegram_enabled and self.is_configured():
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, "rb") as photo_file:
                        data = {
                            "chat_id": self.telegram_chat_id,
                            "caption": caption,
                            "parse_mode": "Markdown"
                        }
                        files = {"photo": photo_file}
                        resp = requests.post(url, data=data, files=files, timeout=6.0)
                        if resp.status_code == 200:
                            print(f"[Notifier] Dispatched Telegram alert for {incident_type} in {zone}")
                        else:
                            print(f"[Notifier] Telegram dispatch returned {resp.status_code}: {resp.text}")
                else:
                    # Send text message fallback if no photo file
                    msg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                    requests.post(msg_url, json={
                        "chat_id": self.telegram_chat_id,
                        "text": caption,
                        "parse_mode": "Markdown"
                    }, timeout=5.0)
            except Exception as e:
                print(f"[Notifier Error] Telegram dispatch failed: {e}")
        elif self.telegram_enabled:
            # Simulation / Demo Mode log
            print(f"[Notifier DEMO] Simulated Telegram alert for {incident_type} in {zone}: {details} (Snapshot: {photo_path})")

        # 2. Generic Webhook Dispatch
        if self.webhook_url:
            try:
                payload = {
                    "event": "SAFETY_INCIDENT",
                    "zone": zone,
                    "incident_type": incident_type,
                    "severity": severity,
                    "details": details,
                    "timestamp": timestamp,
                    "photo_path": photo_path
                }
                requests.post(self.webhook_url, json=payload, timeout=4.0)
            except Exception as e:
                print(f"[Notifier Error] Webhook dispatch failed: {e}")

    def send_test_alert(self, force_mock: bool = False) -> Dict[str, Any]:
        """Sends a test notification to verify connectivity with clear user guidance."""
        if force_mock or not self.is_configured():
            return {
                "status": "mock",
                "message": "[SIMULATION] Demo Dispatch Simulated: Edge pipeline verified! To receive real photo alerts on your phone, enter your Bot Token from @BotFather and your Chat ID from @userinfobot."
            }
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            test_msg = (
                "🛡️ *SafeVision AI - System Test Alert*\n\n"
                "✅ Connected successfully to Edge Safety Monitoring Node.\n"
                f"🕒 Server Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                "Ready to receive real-time incident snapshots!"
            )
            resp = requests.post(url, json={
                "chat_id": self.telegram_chat_id,
                "text": test_msg,
                "parse_mode": "Markdown"
            }, timeout=6.0)
            
            if resp.status_code == 200:
                return {"status": "success", "message": "✅ Test alert delivered to your phone successfully!"}
            else:
                try:
                    err_json = resp.json()
                    desc = err_json.get("description", resp.text)
                    if "chat not found" in desc.lower() or "bot can't initiate" in desc.lower():
                        return {
                            "status": "error",
                            "message": "👉 Chat not found! Please open your bot in Telegram and tap 'START' button first, then retry."
                        }
                    elif "unauthorized" in desc.lower():
                        return {
                            "status": "error",
                            "message": "👉 Invalid Bot Token! Please re-check the full token from @BotFather."
                        }
                    return {"status": "error", "message": f"Telegram: {desc}"}
                except Exception:
                    return {"status": "error", "message": f"Telegram API error: {resp.text}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Global singleton
notifier = IncidentNotifier()
