import threading
import time
import queue
import platform
import os

try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except Exception:
    WINSOUND_AVAILABLE = False


class SafetyAlarmManager:
    """Manages audible speaker sirens and voice announcements with debounce cooldowns."""

    def __init__(self, cooldown_seconds: float = 6.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time = {}
        self.speech_queue = queue.Queue()
        self.is_muted = False
        self.enabled = True
        self.lock = threading.Lock()
        
        # Start background TTS & sound worker
        self.worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.worker_thread.start()

    def _audio_worker(self):
        """Dedicated background thread to play audio without freezing video processing."""
        engine = None
        if TTS_AVAILABLE:
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 160)  # speaking speed
                engine.setProperty('volume', 1.0) # max volume
            except Exception as e:
                print(f"[Alarm Warning] TTS Init failed: {e}")
                engine = None

        while True:
            try:
                alert_item = self.speech_queue.get()
                if alert_item is None:
                    break

                if self.is_muted or not self.enabled:
                    self.speech_queue.task_done()
                    continue

                alert_type, message, siren_level = alert_item

                # Play distinct feature-specific alarm siren tone
                self._play_siren(alert_type, siren_level)

                # Announce via Text-To-Speech
                if engine and message and not self.is_muted and self.enabled:
                    try:
                        engine.say(message)
                        engine.runAndWait()
                    except Exception as e:
                        print(f"[TTS Error] {e}")
                        # Re-init if needed
                        try:
                            engine = pyttsx3.init()
                        except Exception:
                            pass

                time.sleep(0.15)
                self.speech_queue.task_done()
            except Exception as ex:
                print(f"[Audio Worker Exception] {ex}")
                time.sleep(0.5)

    def _play_siren(self, alert_type: str, level: str):
        """Generates distinctive acoustic siren frequencies on Windows speaker for each specific feature."""
        if not WINSOUND_AVAILABLE or self.is_muted or not self.enabled:
            return
        
        try:
            atype = str(alert_type).upper()
            
            # 1. FIRE / EVACUATION: Urgent high-low European emergency evacuation warble
            if "FIRE" in atype:
                for _ in range(2):
                    winsound.Beep(1300, 140)
                    winsound.Beep(800, 140)
            
            # 2. WORKER FALL / MAN-DOWN: Descending medical distress alarm
            elif "FALL" in atype or "COLLAPSE" in atype:
                winsound.Beep(1100, 180)
                winsound.Beep(850, 180)
                winsound.Beep(650, 240)
            
            # 3. HEIGHT SAFETY / HARNESS: Rapid high-frequency emergency chirp
            elif "HARNESS" in atype or "HEIGHT" in atype:
                for _ in range(3):
                    winsound.Beep(1350, 100)
                    time.sleep(0.03)

            # 4. CRANE SUSPENDED LOAD: Heavy pulsed crane radar warning horn
            elif "SUSPENDED" in atype or "LOAD" in atype or "CRANE" in atype:
                winsound.Beep(580, 220)
                time.sleep(0.06)
                winsound.Beep(580, 220)

            # 5. GEOFENCE / PERIMETER / NIGHT INTRUSION: Alternating security strobe siren
            elif any(k in atype for k in ["GEOFENCE", "PERIMETER", "INTRUSION", "NIGHT"]):
                winsound.Beep(980, 140)
                winsound.Beep(1180, 140)
                winsound.Beep(980, 140)

            # 6. TRENCH EXCAVATION MARGIN: Deep warning buzz
            elif "TRENCH" in atype:
                winsound.Beep(480, 280)
                time.sleep(0.05)
                winsound.Beep(480, 180)

            # 7. CONFINED SPACE OVERSTAY: Triple industrial timeout buzzer
            elif "CONFINED" in atype:
                winsound.Beep(620, 130)
                time.sleep(0.04)
                winsound.Beep(740, 130)
                time.sleep(0.04)
                winsound.Beep(620, 180)

            # 8. HOT WORK / NO EXTINGUISHER: Dual-tone spark warning
            elif "HOT_WORK" in atype or "WELDING" in atype:
                winsound.Beep(880, 110)
                time.sleep(0.03)
                winsound.Beep(720, 140)

            # 9. PPE - NO HELMET: Distinct safety chirp (rising tone)
            elif "HELMET" in atype:
                winsound.Beep(780, 160)
                winsound.Beep(980, 200)

            # 10. PPE - NO VEST: Safety notice double beep
            elif "VEST" in atype:
                winsound.Beep(850, 160)
                time.sleep(0.04)
                winsound.Beep(850, 160)

            # 11. PHONE DISTRACTION: Single subtle notification ping
            elif "PHONE" in atype:
                winsound.Beep(820, 130)

            # 12. PROXIMITY HAZARD: Fast proximity sensor double beep
            elif "PROXIMITY" in atype:
                winsound.Beep(1000, 90)
                time.sleep(0.03)
                winsound.Beep(1000, 90)

            # 13. SMART TURNSTILE GATE PASS: Ascending harmonious chime (C-E-G chord)
            elif "GATE_PASS" in atype:
                winsound.Beep(523, 90)
                winsound.Beep(659, 90)
                winsound.Beep(784, 150)

            # 14. SMART TURNSTILE GATE FAIL / ACCESS DENIED: Low rejection double buzz
            elif "GATE_FAIL" in atype or "GATE_DENIED" in atype:
                winsound.Beep(320, 170)
                time.sleep(0.04)
                winsound.Beep(260, 200)

            # 15. HEAT HAZARD / THERMAL: Staccato caution tone
            elif "HEAT" in atype or "THERMAL" in atype:
                winsound.Beep(700, 120)
                winsound.Beep(700, 120)

            # General fallbacks by severity
            elif level == "CRITICAL":
                for _ in range(2):
                    winsound.Beep(1200, 150)
                    winsound.Beep(800, 150)
            elif level == "HIGH":
                winsound.Beep(900, 180)
                time.sleep(0.04)
                winsound.Beep(900, 180)
            else:
                winsound.Beep(680, 200)
        except Exception as e:
            print(f"[Siren Error] {e}")

    def trigger_alert(self, alert_type: str, message: str, severity: str = "HIGH", force: bool = False):
        """Triggers an audible alarm if outside the cooldown window, preventing audio spam while responding accurately."""
        with self.lock:
            if not self.enabled or self.is_muted:
                return

            now = time.time()
            last_time = self.last_alert_time.get(alert_type, 0)
            
            # Dynamic cooldown per severity:
            # Critical alerts (Fire, Fall, Harness, Intrusion) require prompt response (3.5s cooldown)
            # Standard PPE warnings have 6.0s debounce so worker has time to equip gear without noise spam
            if severity == "CRITICAL":
                effective_cooldown = 3.5
            elif severity == "LOW" or "GATE" in alert_type:
                effective_cooldown = 2.0
            else:
                effective_cooldown = self.cooldown_seconds

            if force or (now - last_time) >= effective_cooldown:
                self.last_alert_time[alert_type] = now
                
                # Prevent speech queue stacking: drop older items if queue is getting backed up
                while self.speech_queue.qsize() >= 2:
                    try:
                        self.speech_queue.get_nowait()
                        self.speech_queue.task_done()
                    except Exception:
                        break

                self.speech_queue.put((alert_type, message, severity))

    def set_muted(self, muted: bool):
        self.is_muted = muted

    def set_enabled(self, enabled: bool):
        self.enabled = enabled


# Global singleton instance
alarm_manager = SafetyAlarmManager(cooldown_seconds=5.5)
