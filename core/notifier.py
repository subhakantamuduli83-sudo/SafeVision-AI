import os
import time
import html
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

def load_env_file():
    """Loads environment variables from root .env file."""
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ[k] = v
        except Exception as e:
            print(f"[Notifier Env Error] Failed to read .env: {e}")

load_env_file()

def save_env_telegram(token: str, chat_id: str, enabled: bool):
    """Saves Telegram configuration to root .env file and updates os.environ."""
    try:
        lines = []
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        filtered = [
            l for l in lines
            if not l.startswith("TELEGRAM_BOT_TOKEN=")
            and not l.startswith("TELEGRAM_CHAT_ID=")
            and not l.startswith("TELEGRAM_ENABLED=")
        ]
        
        filtered.append(f"TELEGRAM_BOT_TOKEN={token}\n")
        filtered.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
        filtered.append(f"TELEGRAM_ENABLED={'true' if enabled else 'false'}\n")
        
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(filtered)
            
        os.environ["TELEGRAM_BOT_TOKEN"] = token
        os.environ["TELEGRAM_CHAT_ID"] = chat_id
        os.environ["TELEGRAM_ENABLED"] = "true" if enabled else "false"
        return True
    except Exception as e:
        print(f"[Notifier Env Save Error] Failed to save .env: {e}")
        return False

class IncidentNotifier:
    """Dispatches real-time incident notifications and evidence snapshots to Telegram & Webhooks."""

    def __init__(self):
        load_env_file()
        self.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        enabled_val = os.environ.get("TELEGRAM_ENABLED", "true").strip().lower()
        self.telegram_enabled = (enabled_val in ["true", "1", "yes"]) and bool(self.telegram_token and self.telegram_chat_id)
        self.webhook_url = os.environ.get("INCIDENT_WEBHOOK_URL", "").strip()
        self.last_sent_time = {}
        self.throttle_cooldown = 5.0 # Seconds cooldown between duplicate incident dispatches

    @property
    def enabled(self) -> bool:
        return self.telegram_enabled

    @enabled.setter
    def enabled(self, val: bool):
        self.telegram_enabled = bool(val)

    def update_config(self, token: str, chat_id: str, enabled: bool = True):
        """Updates runtime config, updates environment variables, and returns state."""
        self.telegram_token = token.strip()
        self.telegram_chat_id = chat_id.strip()
        self.telegram_enabled = bool(enabled and self.telegram_token and self.telegram_chat_id)
        
        os.environ["TELEGRAM_BOT_TOKEN"] = self.telegram_token
        os.environ["TELEGRAM_CHAT_ID"] = self.telegram_chat_id
        os.environ["TELEGRAM_ENABLED"] = "true" if self.telegram_enabled else "false"
        
        return {
            "telegram_enabled": self.telegram_enabled,
            "has_token": bool(self.telegram_token),
            "chat_id": self.telegram_chat_id,
            "is_configured": self.is_configured()
        }

    def is_configured(self) -> bool:
        """Validates if a real Telegram Bot token and Chat ID are configured."""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        tok = self.telegram_token.lower()
        if "dummy" in tok or "test" in tok or len(self.telegram_token) < 15 or ":" not in self.telegram_token:
            return False
        if self.telegram_chat_id in ["12345", "0", "chat_id_here", "your_chat_id", "dummy"]:
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
        
        # HTML formatting is immune to markdown entity parse failures on special chars (_, *, etc.)
        safe_zone = html.escape(str(zone))
        safe_type = html.escape(str(incident_type))
        safe_severity = html.escape(str(severity))
        safe_details = html.escape(str(details)[:350])
        safe_ts = html.escape(timestamp)

        caption_html = (
            f"{severity_emoji} <b>SAFEVISION AI INCIDENT ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Zone:</b> <code>{safe_zone}</code>\n"
            f"⚠️ <b>Type:</b> <b>{safe_type}</b>\n"
            f"⚡ <b>Severity:</b> <code>{safe_severity}</code>\n"
            f"📝 <b>Details:</b> {safe_details}\n"
            f"🕒 <b>Timestamp:</b> <code>{safe_ts}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Automated Industrial Edge AI Dispatch</i>"
        )

        caption_plain = (
            f"{severity_emoji} SAFEVISION AI INCIDENT ALERT\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Zone: {zone}\n"
            f"⚠️ Type: {incident_type}\n"
            f"⚡ Severity: {severity}\n"
            f"📝 Details: {str(details)[:350]}\n"
            f"🕒 Timestamp: {timestamp}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Automated Industrial Edge AI Dispatch"
        )

        # 1. Telegram Dispatch
        if self.telegram_enabled and self.is_configured():
            sent = False
            # Attempt to send photo
            if photo_path and os.path.exists(photo_path):
                try:
                    url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                    with open(photo_path, "rb") as photo_file:
                        data = {
                            "chat_id": self.telegram_chat_id,
                            "caption": caption_html,
                            "parse_mode": "HTML"
                        }
                        files = {"photo": photo_file}
                        resp = requests.post(url, data=data, files=files, timeout=7.0)
                        if resp.status_code == 200:
                            print(f"[Notifier] Dispatched Telegram photo alert for {incident_type} in {zone}")
                            sent = True
                        else:
                            print(f"[Notifier Warning] HTML sendPhoto returned {resp.status_code}: {resp.text}. Retrying plain text...")
                            photo_file.seek(0)
                            data_plain = {
                                "chat_id": self.telegram_chat_id,
                                "caption": caption_plain
                            }
                            resp2 = requests.post(url, data=data_plain, files=files, timeout=7.0)
                            if resp2.status_code == 200:
                                print(f"[Notifier] Dispatched Telegram photo alert (plain text) for {incident_type} in {zone}")
                                sent = True
                            else:
                                print(f"[Notifier Error] Telegram sendPhoto failed ({resp2.status_code}): {resp2.text}")
                except Exception as e:
                    print(f"[Notifier Error] Telegram photo dispatch exception: {e}")

            # Fallback to sendMessage if photo was not sent or failed
            if not sent:
                try:
                    msg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                    resp = requests.post(msg_url, json={
                        "chat_id": self.telegram_chat_id,
                        "text": caption_html,
                        "parse_mode": "HTML"
                    }, timeout=6.0)
                    if resp.status_code == 200:
                        print(f"[Notifier] Dispatched Telegram text fallback alert for {incident_type} in {zone}")
                    else:
                        resp2 = requests.post(msg_url, json={
                            "chat_id": self.telegram_chat_id,
                            "text": caption_plain
                        }, timeout=6.0)
                        if resp2.status_code == 200:
                            print(f"[Notifier] Dispatched Telegram plain text fallback alert for {incident_type} in {zone}")
                        else:
                            print(f"[Notifier Error] Telegram text fallback failed ({resp2.status_code}): {resp2.text}")
                except Exception as e:
                    print(f"[Notifier Error] Telegram sendMessage fallback exception: {e}")

        elif self.telegram_enabled:
            # Simulation / Demo Mode log
            print(f"[Notifier DEMO] Real Telegram alert suppressed (Bot Token / Chat ID not yet configured). Simulated dispatch for {incident_type} in {zone}: {details}")

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
        if force_mock:
            return {
                "status": "mock",
                "message": "[SIMULATION] Demo Dispatch Simulated: Edge pipeline verified! To receive real photo alerts on your phone, enter your Bot Token from @BotFather and your Chat ID from @userinfobot."
            }

        if not self.is_configured():
            return {
                "status": "error",
                "message": "👉 Telegram is not configured! Please enter your real Bot Token from @BotFather and numeric Chat ID from @userinfobot."
            }

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            test_msg_html = (
                "🛡️ <b>SafeVision AI — System Test Alert</b>\n\n"
                "✅ <b>Connected successfully to Edge Safety Monitoring Node!</b>\n"
                f"🕒 <b>Server Time:</b> <code>{timestamp}</code>\n\n"
                "🚀 Your system is now armed and ready to dispatch instant photo evidence whenever safety violations occur."
            )
            
            resp = requests.post(url, json={
                "chat_id": self.telegram_chat_id,
                "text": test_msg_html,
                "parse_mode": "HTML"
            }, timeout=7.0)
            
            if resp.status_code == 200:
                return {
                    "status": "success",
                    "message": "✅ Test alert delivered to your Telegram app successfully!"
                }
            else:
                try:
                    err_json = resp.json()
                    desc = err_json.get("description", resp.text)
                    desc_lower = desc.lower()
                    
                    if "unauthorized" in desc_lower:
                        return {
                            "status": "error",
                            "message": "❌ Invalid Bot Token! Please re-copy the exact API token from @BotFather."
                        }
                    elif "chat not found" in desc_lower or "bot can't initiate" in desc_lower:
                        if self.telegram_chat_id.startswith("@"):
                            return {
                                "status": "error",
                                "message": f"👉 Chat not found! Chat ID must be your numeric ID (e.g. 987654321), not username '{self.telegram_chat_id}'. Send any message to @userinfobot on Telegram to get your numeric ID, and make sure to tap START on your bot."
                            }
                        return {
                            "status": "error",
                            "message": "👉 Chat not found! Please open your bot in Telegram and tap the 'START' button first, then retry."
                        }
                    elif "blocked" in desc_lower:
                        return {
                            "status": "error",
                            "message": "👉 Bot was blocked by user! Unblock the bot in Telegram and send /start."
                        }
                    return {"status": "error", "message": f"Telegram API error: {desc}"}
                except Exception:
                    return {"status": "error", "message": f"Telegram API returned status {resp.status_code}: {resp.text}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "⏱️ Connection timed out reaching api.telegram.org. Please check your internet connection."}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "🌐 Network connection error. Unable to reach Telegram servers."}
        except Exception as e:
            return {"status": "error", "message": f"Dispatch error: {str(e)}"}

# Global singleton
notifier = IncidentNotifier()
