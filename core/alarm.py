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

                # Play alarm siren tone
                self._play_siren(siren_level)

                # Announce via Text-To-Speech
                if engine and message:
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

                time.sleep(0.2)
                self.speech_queue.task_done()
            except Exception as ex:
                print(f"[Audio Worker Exception] {ex}")
                time.sleep(0.5)

    def _play_siren(self, level: str):
        """Generates audio frequencies on Windows speaker."""
        if not WINSOUND_AVAILABLE:
            return
        
        try:
            if level == "CRITICAL":
                # Fire alarm high-pitched pulsating warble
                for _ in range(3):
                    winsound.Beep(1200, 150)
                    winsound.Beep(800, 150)
            elif level == "HIGH":
                # Safety violation double beep
                winsound.Beep(900, 200)
                time.sleep(0.05)
                winsound.Beep(900, 200)
            else:
                # Mild notice
                winsound.Beep(700, 250)
        except Exception as e:
            print(f"[Siren Error] {e}")

    def trigger_alert(self, alert_type: str, message: str, severity: str = "HIGH"):
        """Triggers an audible alarm if outside the cooldown window."""
        with self.lock:
            if not self.enabled or self.is_muted:
                return

            now = time.time()
            last_time = self.last_alert_time.get(alert_type, 0)

            # Check cooldown debounce to avoid audio spam
            if (now - last_time) >= self.cooldown_seconds:
                self.last_alert_time[alert_type] = now
                # Enqueue audio task
                if self.speech_queue.qsize() < 4:
                    self.speech_queue.put((alert_type, message, severity))

    def set_muted(self, muted: bool):
        self.is_muted = muted

    def set_enabled(self, enabled: bool):
        self.enabled = enabled


# Global singleton instance
alarm_manager = SafetyAlarmManager(cooldown_seconds=5.0)
