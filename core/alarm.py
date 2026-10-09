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
            
            # 0. MASTER SPEAKER / GENERAL TEST: Industrial 4-tone ascending factory air horn blast
            if "MASTER" in atype or "TEST" in atype:
                winsound.Beep(350, 160)
                winsound.Beep(520, 160)
                winsound.Beep(740, 200)
                winsound.Beep(1050, 320)

            # 1. FIRE / EVACUATION: Urgent high-low European emergency evacuation warble
            elif "FIRE" in atype:
                for _ in range(2):
                    winsound.Beep(1300, 160)
                    winsound.Beep(750, 160)
            
            # 2. WORKER FALL / MAN-DOWN: Medical code descending distress sequence
            elif "FALL" in atype or "COLLAPSE" in atype:
                winsound.Beep(1100, 180)
                winsound.Beep(850, 180)
                winsound.Beep(580, 220)
                winsound.Beep(330, 300)
            
            # 3. HEIGHT SAFETY / HARNESS: Rapid high-frequency emergency whistle flutter
            elif "HARNESS" in atype or "HEIGHT" in atype:
                winsound.Beep(1650, 90)
                time.sleep(0.04)
                winsound.Beep(1760, 110)
                time.sleep(0.04)
                winsound.Beep(1900, 160)

            # 4. CRANE SUSPENDED LOAD: Heavy sub-bass drop-zone foghorn
            elif "SUSPENDED" in atype or "LOAD" in atype or "CRANE" in atype:
                winsound.Beep(260, 340)
                time.sleep(0.07)
                winsound.Beep(300, 380)

            # 5. GEOFENCE / DANGER PERIMETER: High-speed laser tripwire sweep
            elif "GEOFENCE" in atype or "PERIMETER" in atype:
                winsound.Beep(1250, 90)
                winsound.Beep(850, 90)
                winsound.Beep(1250, 90)
                winsound.Beep(850, 90)

            # 6. NIGHT INTRUSION / LOCKDOWN: Tactical police security strobe wail
            elif "NIGHT" in atype or "INTRUSION" in atype:
                winsound.Beep(1100, 110)
                winsound.Beep(1550, 110)
                winsound.Beep(1100, 110)
                winsound.Beep(1550, 110)
                winsound.Beep(1700, 220)

            # 7. TRENCH EXCAVATION MARGIN: Sub-bass ground-rumble caution buzz
            elif "TRENCH" in atype:
                winsound.Beep(220, 340)
                time.sleep(0.06)
                winsound.Beep(196, 380)

            # 8. CONFINED SPACE WATCHDOG: Resonant subterranean 3-bell timeout chime
            elif "CONFINED" in atype:
                winsound.Beep(520, 200)
                time.sleep(0.05)
                winsound.Beep(390, 200)
                time.sleep(0.05)
                winsound.Beep(260, 350)

            # 9. HOT WORK / NO EXTINGUISHER: Welding electric arc spark crackle
            elif "HOT_WORK" in atype or "WELDING" in atype:
                for _ in range(3):
                    winsound.Beep(1500, 60)
                    winsound.Beep(750, 60)

            # 10. PPE - NO HELMET: Bright ascending compliance double-chirp
            elif "HELMET" in atype:
                winsound.Beep(650, 130)
                winsound.Beep(1100, 180)

            # 11. PPE - NO VEST: Harmonic safety tri-tone chord (C5 - E5 - G5)
            elif "VEST" in atype:
                winsound.Beep(523, 110)
                winsound.Beep(659, 110)
                winsound.Beep(784, 160)

            # 11b. PPE - NO GLOVES: Dual tactical cautionary pulse (A4 - E5)
            elif "GLOVE" in atype:
                winsound.Beep(440, 120)
                time.sleep(0.04)
                winsound.Beep(659, 160)

            # 11c. PPE - NO GOGGLES: High-frequency optical alert chime (F5 - A5)
            elif "GOGGLE" in atype or "GLASSES" in atype:
                winsound.Beep(698, 110)
                time.sleep(0.03)
                winsound.Beep(880, 170)

            # 11d. PPE - NO SAFETY SHOES / BOOTS: Ground-step dual caution pulse (D4 - G4)
            elif "SHOE" in atype or "BOOT" in atype:
                winsound.Beep(294, 130)
                time.sleep(0.04)
                winsound.Beep(392, 170)

            # 12. PHONE DISTRACTION: Digital mobile SMS double-ping
            elif "PHONE" in atype:
                winsound.Beep(1760, 70)
                time.sleep(0.04)
                winsound.Beep(2093, 120)

            # 13. PROXIMITY HAZARD / FORKLIFT: Rapid reversing ultrasonic collision sonar
            elif "PROXIMITY" in atype or "FORKLIFT" in atype or "MACHINERY" in atype:
                winsound.Beep(1400, 60)
                time.sleep(0.03)
                winsound.Beep(1400, 60)
                time.sleep(0.03)
                winsound.Beep(1600, 70)
                time.sleep(0.03)
                winsound.Beep(1800, 110)

            # 14. SMART TURNSTILE GATE PASS: Pleasant ascending arpeggio chime (C-E-G-C)
            elif "GATE_PASS" in atype:
                winsound.Beep(523, 80)
                winsound.Beep(659, 80)
                winsound.Beep(784, 80)
                winsound.Beep(1046, 170)

            # 15. SMART TURNSTILE GATE FAIL: Harsh low rejection double buzz
            elif "GATE_FAIL" in atype or "GATE_DENIED" in atype:
                winsound.Beep(330, 180)
                time.sleep(0.05)
                winsound.Beep(220, 280)

            # 16. HEAT HAZARD / THERMAL: Undulating solar thermal caution wave
            elif "HEAT" in atype or "THERMAL" in atype:
                winsound.Beep(440, 180)
                winsound.Beep(580, 180)
                winsound.Beep(440, 180)
                winsound.Beep(580, 240)

            # 17. AUTOPILOT AWAY MODE: System active confirmation chime
            elif "AUTOPILOT" in atype:
                winsound.Beep(880, 100)
                winsound.Beep(1320, 160)

            # General fallbacks by severity
            elif level == "CRITICAL":
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
