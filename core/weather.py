import os
import math
import time
import threading
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Load environment variables manually from .env if present
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
            print(f"[Weather Env Error] Failed to read .env: {e}")

load_env_file()


def calculate_noaa_heat_index(temp_c: float, humidity: float) -> float:
    """
    Calculates the Heat Index using the National Oceanic and Atmospheric Administration (NOAA) /
    Rothfusz regression equation with Steadman formula fallback for moderate temperatures.
    
    Formula input: Temperature in Fahrenheit (°F), Relative Humidity in %.
    Formula output: Heat Index in Celsius (°C), rounded to 1 decimal place.
    """
    if temp_c < 15.0:
        # Heat index is only meaningful for warm temperatures; return ambient temp
        return round(temp_c, 1)

    # Convert Celsius to Fahrenheit
    tf = (temp_c * 9.0 / 5.0) + 32.0
    rh = max(0.0, min(100.0, float(humidity)))

    # Steadman simple formula for mild conditions
    hi_f = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))

    # If average heat index is 80°F (26.7°C) or higher, use full NOAA Rothfusz regression
    if hi_f >= 80.0:
        hi_f = (
            -42.379
            + (2.04901523 * tf)
            + (10.14333127 * rh)
            - (0.22475541 * tf * rh)
            - (0.00683783 * (tf ** 2))
            - (0.05481717 * (rh ** 2))
            + (0.00122874 * (tf ** 2) * rh)
            + (0.00085282 * tf * (rh ** 2))
            - (0.00000199 * (tf ** 2) * (rh ** 2))
        )

        # Low humidity adjustment
        if rh < 13.0 and 80.0 <= tf <= 112.0:
            adj = ((13.0 - rh) / 4.0) * math.sqrt(max(0.0, (17.0 - abs(tf - 95.0)) / 17.0))
            hi_f -= adj
        # High humidity adjustment
        elif rh > 85.0 and 80.0 <= tf <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
            hi_f += adj

    # Convert Fahrenheit back to Celsius
    hi_c = (hi_f - 32.0) * 5.0 / 9.0
    return round(hi_c, 1)


class WeatherManager:
    """
    Singleton manager for real-time weather monitoring, NOAA Heat Index calculation,
    explainable thermal anomaly detection, and alert dispatching.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.api_key = os.getenv("WEATHER_API_KEY", "").strip()
        self.provider = os.getenv("WEATHER_PROVIDER", "open-meteo").lower().strip()
        self.location_name = os.getenv("WEATHER_LOCATION", "Bhubaneswar, Odisha, India")
        self.latitude = float(os.getenv("WEATHER_LAT", "20.2961"))
        self.longitude = float(os.getenv("WEATHER_LON", "85.8245"))
        self.update_interval = int(os.getenv("WEATHER_UPDATE_INTERVAL", "300")) # 5 mins

        # Configurable Risk Thresholds (°C)
        self.threshold_moderate = float(os.getenv("HEAT_INDEX_THRESHOLD_MODERATE", "32.0"))
        self.threshold_high = float(os.getenv("HEAT_INDEX_THRESHOLD_HIGH", "39.0"))
        self.threshold_critical = float(os.getenv("HEAT_INDEX_THRESHOLD_CRITICAL", "46.0"))
        self.rate_change_threshold = float(os.getenv("TEMP_RATE_CHANGE_THRESHOLD", "2.5"))
        self.z_score_threshold = float(os.getenv("Z_SCORE_THRESHOLD", "2.0"))

        # State storage
        self.last_successful_data: Optional[Dict[str, Any]] = None
        self.last_api_status: str = "initialized" # "online", "offline", "demo"
        self.last_error_message: str = ""
        self.last_fetch_time: float = 0
        self.history_readings: List[Dict[str, Any]] = [] # Sliding in-memory buffer of recent readings

        # Demo / Simulation Mode State
        self.demo_mode: bool = False
        self.demo_temp: float = 41.5
        self.demo_humidity: float = 76.0

        # Background Worker
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._background_poll_loop, daemon=True)
        self.worker_thread.start()

    def set_demo_mode(self, enabled: bool, temp: Optional[float] = None, humidity: Optional[float] = None):
        """Toggles Demo Simulation Mode."""
        with self.lock:
            self.demo_mode = enabled
            if temp is not None:
                self.demo_temp = float(temp)
            if humidity is not None:
                self.demo_humidity = float(humidity)
        
        # Trigger immediate refresh with new settings
        return self.fetch_weather_data(force=True)

    def update_config(self, location: str, lat: float, lon: float, 
                      thresh_mod: float = 32.0, thresh_high: float = 39.0, thresh_crit: float = 46.0):
        """Updates geographical location and risk thresholds."""
        with self.lock:
            self.location_name = location
            self.latitude = lat
            self.longitude = lon
            self.threshold_moderate = thresh_mod
            self.threshold_high = thresh_high
            self.threshold_critical = thresh_crit
        return self.fetch_weather_data(force=True)

    def _fetch_from_open_meteo(self) -> Dict[str, Any]:
        """Queries Open-Meteo API (High reliability, real-time meteorological feed, no API key needed)."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,weather_code",
            "timezone": "auto"
        }
        resp = requests.get(url, params=params, timeout=6.0)
        resp.raise_for_status()
        data = resp.json()
        
        current = data.get("current", {})
        temp = float(current.get("temperature_2m", 0.0))
        humidity = float(current.get("relative_humidity_2m", 0.0))
        wind_speed = float(current.get("wind_speed_10m", 0.0))
        pressure = float(current.get("surface_pressure", 1013.25))
        wcode = current.get("weather_code", 0)

        # Map Open-Meteo WMO weather codes to human readable text
        condition_map = {
            0: "Clear Sky",
            1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing Rime Fog",
            51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
            61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
            80: "Rain Showers", 81: "Moderate Showers", 82: "Violent Showers",
            95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Severe Thunderstorm"
        }
        condition = condition_map.get(wcode, "Clear")

        return {
            "temperature": round(temp, 1),
            "humidity": round(humidity, 1),
            "wind_speed": round(wind_speed, 1),
            "pressure": round(pressure, 1),
            "condition": condition,
            "source": "Open-Meteo Real-Time Weather API",
            "is_demo": False
        }

    def _fetch_from_openweathermap(self) -> Dict[str, Any]:
        """Queries OpenWeatherMap API using WEATHER_API_KEY."""
        if not self.api_key:
            raise ValueError("OpenWeatherMap selected but WEATHER_API_KEY is missing.")
        
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": self.latitude,
            "lon": self.longitude,
            "appid": self.api_key,
            "units": "metric"
        }
        resp = requests.get(url, params=params, timeout=6.0)
        resp.raise_for_status()
        data = resp.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        weather_list = data.get("weather", [{}])

        temp = float(main.get("temp", 0.0))
        humidity = float(main.get("humidity", 0.0))
        pressure = float(main.get("pressure", 1013.25))
        wind_speed = float(wind.get("speed", 0.0)) * 3.6 # m/s to km/h
        condition = weather_list[0].get("description", "Clear").title()

        return {
            "temperature": round(temp, 1),
            "humidity": round(humidity, 1),
            "wind_speed": round(wind_speed, 1),
            "pressure": round(pressure, 1),
            "condition": condition,
            "source": "OpenWeatherMap Real-Time API",
            "is_demo": False
        }

    def _generate_demo_data(self) -> Dict[str, Any]:
        """Generates explicit simulation data when Demo Mode is explicitly enabled."""
        return {
            "temperature": round(self.demo_temp, 1),
            "humidity": round(self.demo_humidity, 1),
            "wind_speed": 5.2,
            "pressure": 1008.0,
            "condition": "Severe Heatwave (Simulated)",
            "source": "🧪 DEMO SIMULATION MODE (Testing Only)",
            "is_demo": True
        }

    def _analyze_risk_and_anomalies(self, temp: float, humidity: float, heat_index: float) -> Dict[str, Any]:
        """
        Multi-factor explainable anomaly and risk detection engine.
        Evaluates NOAA Heat Index, rate-of-change (ΔT/Δt), and statistical Z-score.
        """
        reasons: List[str] = []
        is_anomaly = False
        anomaly_type = "NORMAL"

        # 1. Heat Index Threshold Evaluation (OSHA / NOAA Standard)
        if heat_index >= self.threshold_critical:
            risk_level = "CRITICAL"
            risk_color = "red"
            risk_badge = "🔴 CRITICAL"
            reasons.append(f"Heat Index ({heat_index}°C) exceeded critical hazard threshold ({self.threshold_critical}°C). Extreme danger of heatstroke.")
        elif heat_index >= self.threshold_high:
            risk_level = "HIGH"
            risk_color = "orange"
            risk_badge = "🟠 HIGH"
            reasons.append(f"Heat Index ({heat_index}°C) reached high risk threshold ({self.threshold_high}°C). Heat cramps and exhaustion likely with prolonged activity.")
        elif heat_index >= self.threshold_moderate:
            risk_level = "MODERATE"
            risk_color = "yellow"
            risk_badge = "🟡 MODERATE"
            reasons.append(f"Heat Index ({heat_index}°C) in caution range ({self.threshold_moderate}°C - {self.threshold_high}°C). Increased fatigue possible.")
        else:
            risk_level = "LOW"
            risk_color = "green"
            risk_badge = "🟢 LOW"
            reasons.append(f"Heat Index ({heat_index}°C) within normal occupational safety limits.")

        # 2. Ambient Temperature Factors
        if temp >= 40.0:
            reasons.append(f"Extremely high ambient temperature ({temp}°C) creates severe heat stress.")
        elif temp >= 35.0:
            reasons.append(f"Elevated ambient temperature ({temp}°C).")

        # 3. Humidity Factors
        if humidity >= 75.0:
            reasons.append(f"High relative humidity ({humidity}%) severely impedes body's evaporative sweat cooling.")
        elif humidity >= 60.0:
            reasons.append(f"Elevated humidity ({humidity}%) increases apparent temperature feel.")
        elif humidity < 30.0:
            reasons.append(f"Dry air ({humidity}%). Stay hydrated.")

        # 4. Rate-of-Change Anomaly Detection
        recent_temps = [r["temperature"] for r in self.history_readings[-10:] if not r.get("is_demo", False)]
        if len(recent_temps) >= 2:
            prev_temp = recent_temps[-1]
            delta_t = temp - prev_temp
            if delta_t >= self.rate_change_threshold:
                is_anomaly = True
                anomaly_type = "RAPID_HEAT_SPIKE"
                reasons.append(f"Unusual temperature spike: +{delta_t:.1f}°C sudden surge compared to previous reading ({prev_temp}°C).")
            elif delta_t <= -self.rate_change_threshold:
                reasons.append(f"Rapid temperature drop: {delta_t:.1f}°C decrease detected.")

        # 5. Statistical Moving Average & Z-Score Anomaly
        if len(recent_temps) >= 5:
            mean_temp = sum(recent_temps) / len(recent_temps)
            variance = sum((x - mean_temp) ** 2 for x in recent_temps) / len(recent_temps)
            std_dev = math.sqrt(variance)
            
            if std_dev > 0.4:
                z_score = (temp - mean_temp) / std_dev
                if z_score >= self.z_score_threshold:
                    is_anomaly = True
                    anomaly_type = "STATISTICAL_SURGE"
                    reasons.append(f"Statistical Anomaly: Temperature is {abs(temp - mean_temp):.1f}°C above the recent rolling average ({mean_temp:.1f}°C, Z-score: +{z_score:.2f}).")

        # Determine Trend
        if len(recent_temps) >= 2:
            diff = temp - recent_temps[-1]
            if diff > 0.3:
                trend = "RISING"
                trend_icon = "↑"
            elif diff < -0.3:
                trend = "FALLING"
                trend_icon = "↓"
            else:
                trend = "STEADY"
                trend_icon = "→"
        else:
            trend = "STEADY"
            trend_icon = "→"

        # Humidity Status Description
        if humidity > 75.0:
            humidity_status = "Hazardous / High Moisture"
        elif humidity >= 60.0:
            humidity_status = "Elevated Humidity"
        elif humidity >= 30.0:
            humidity_status = "Optimal / Comfortable"
        else:
            humidity_status = "Dry Air"

        # Temperature Status Description
        if temp >= 40.0:
            temp_status = "Extreme Heat"
        elif temp >= 35.0:
            temp_status = "High Temperature"
        elif temp >= 28.0:
            temp_status = "Warm"
        elif temp >= 18.0:
            temp_status = "Comfortable"
        else:
            temp_status = "Cool"

        # Summary conclusion
        conclusion = (
            f"Heat risk level evaluated as {risk_level} with Heat Index of {heat_index}°C. "
            + ("Thermal safety alert active." if risk_level in ["HIGH", "CRITICAL"] else "Environmental conditions are stable.")
        )

        return {
            "risk_level": risk_level,
            "risk_badge": risk_badge,
            "risk_color": risk_color,
            "temp_status": temp_status,
            "humidity_status": humidity_status,
            "trend": trend,
            "trend_icon": trend_icon,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "reasons": reasons,
            "conclusion": conclusion
        }

    def fetch_weather_data(self, force: bool = False) -> Dict[str, Any]:
        """
        Fetches fresh weather data, computes Heat Index & Risk Anomaly, 
        persists to database, and returns standard response dictionary.
        """
        now = time.time()
        with self.lock:
            # Throttle fetches to at least 10 seconds unless forced
            if not force and self.last_successful_data and (now - self.last_fetch_time < 10):
                return self.last_successful_data

            is_demo = self.demo_mode

        # 1. Fetch raw weather data
        raw_data = None
        error_msg = ""
        try:
            if is_demo:
                raw_data = self._generate_demo_data()
                api_status = "demo"
            elif self.provider == "openweathermap" and self.api_key:
                raw_data = self._fetch_from_openweathermap()
                api_status = "online"
            else:
                # Default to Open-Meteo
                raw_data = self._fetch_from_open_meteo()
                api_status = "online"
        except Exception as ex:
            error_msg = str(ex)
            api_status = "offline"
            print(f"[Weather API Warning] Failed to fetch live weather: {ex}")

        # 2. Process Result or Handle Offline State
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_time = datetime.now().strftime("%d-%b-%Y %I:%M %p")

        if raw_data is not None:
            temp = raw_data["temperature"]
            humidity = raw_data["humidity"]
            heat_index = calculate_noaa_heat_index(temp, humidity)
            
            # Anomaly & Risk Analysis
            analysis = self._analyze_risk_and_anomalies(temp, humidity, heat_index)

            result = {
                "status": "success",
                "api_status": api_status,
                "is_offline": False,
                "location": self.location_name,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "temperature": temp,
                "temp_unit": "°C",
                "temp_status": analysis["temp_status"],
                "trend": analysis["trend"],
                "trend_icon": analysis["trend_icon"],
                "humidity": humidity,
                "humidity_unit": "%",
                "humidity_status": analysis["humidity_status"],
                "heat_index": heat_index,
                "heat_index_formula": f"{temp}°C (Temp) + {humidity}% (Humidity) → {heat_index}°C (Heat Index)",
                "wind_speed": raw_data["wind_speed"],
                "wind_unit": "km/h",
                "pressure": raw_data["pressure"],
                "pressure_unit": "hPa",
                "condition": raw_data["condition"],
                "risk_level": analysis["risk_level"],
                "risk_badge": analysis["risk_badge"],
                "risk_color": analysis["risk_color"],
                "is_anomaly": analysis["is_anomaly"],
                "anomaly_type": analysis["anomaly_type"],
                "reasons": analysis["reasons"],
                "conclusion": analysis["conclusion"],
                "last_updated": formatted_time,
                "timestamp_raw": timestamp_str,
                "data_source": raw_data["source"],
                "is_demo": raw_data["is_demo"],
                "thresholds": {
                    "moderate": self.threshold_moderate,
                    "high": self.threshold_high,
                    "critical": self.threshold_critical
                }
            }

            # Update in-memory sliding buffer
            with self.lock:
                self.last_successful_data = result
                self.last_api_status = api_status
                self.last_error_message = ""
                self.last_fetch_time = now
                self.history_readings.append({
                    "timestamp": formatted_time,
                    "temperature": temp,
                    "humidity": humidity,
                    "heat_index": heat_index,
                    "risk_level": analysis["risk_level"],
                    "is_anomaly": analysis["is_anomaly"],
                    "is_demo": raw_data["is_demo"]
                })
                # Keep last 100 points
                if len(self.history_readings) > 100:
                    self.history_readings.pop(0)

            # Persist reading to database
            try:
                from core.database import log_weather_reading, log_incident
                log_weather_reading(
                    timestamp=timestamp_str,
                    temperature=temp,
                    humidity=humidity,
                    heat_index=heat_index,
                    wind_speed=raw_data["wind_speed"],
                    pressure=raw_data["pressure"],
                    condition=raw_data["condition"],
                    risk_level=analysis["risk_level"],
                    is_anomaly=1 if analysis["is_anomaly"] else 0,
                    anomaly_reasons=" | ".join(analysis["reasons"]),
                    is_demo=1 if raw_data["is_demo"] else 0
                )

                # If thermal emergency is CRITICAL or HIGH, also log incident and trigger audible voice alert
                if analysis["risk_level"] in ["CRITICAL", "HIGH"] or analysis["is_anomaly"]:
                    log_incident(
                        zone=f"Environmental Safety - {self.location_name}",
                        incident_type=f"Thermal Hazard ({analysis['risk_level']})",
                        severity=analysis["risk_level"],
                        details=f"Heat Index: {heat_index}°C, Temp: {temp}°C, Humidity: {humidity}%. Reasons: {', '.join(analysis['reasons'][:2])}"
                    )
                    
                    # Voice alert through alarm engine
                    try:
                        from core.alarm import alarm_manager
                        alarm_manager.trigger_alert(
                            alert_type="HEAT_HAZARD",
                            message=f"Caution: High heat index of {int(heat_index)} degrees detected in factory area. Ensure worker hydration.",
                            severity=analysis["risk_level"]
                        )
                    except Exception:
                        pass

            except Exception as dbe:
                print(f"[Weather DB Error] Failed to log weather reading: {dbe}")

            return result

        else:
            # Offline fallback handling
            with self.lock:
                self.last_api_status = "offline"
                self.last_error_message = error_msg
                
                if self.last_successful_data:
                    # Return last known data marked as stale
                    stale_data = dict(self.last_successful_data)
                    stale_data["api_status"] = "offline"
                    stale_data["is_offline"] = True
                    stale_data["error_message"] = f"Weather API Offline ({error_msg}). Data may be stale."
                    return stale_data
                else:
                    # No previous data available
                    return {
                        "status": "error",
                        "api_status": "offline",
                        "is_offline": True,
                        "location": self.location_name,
                        "temperature": None,
                        "humidity": None,
                        "heat_index": None,
                        "risk_level": "UNKNOWN",
                        "risk_badge": "🔴 OFFLINE",
                        "risk_color": "gray",
                        "reasons": [f"Weather API unreachable: {error_msg}. Check internet connection or API settings."],
                        "conclusion": "Weather monitoring offline.",
                        "last_updated": "Never",
                        "data_source": "Weather API (Offline)",
                        "error_message": error_msg,
                        "is_demo": False
                    }

    def get_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieves history for frontend multi-metric Chart.js graph."""
        try:
            from core.database import get_recent_weather_logs
            db_logs = get_recent_weather_logs(limit=limit)
            if db_logs:
                # Format timestamps for display
                formatted = []
                for row in reversed(db_logs): # chronological order
                    formatted.append({
                        "timestamp": row["timestamp"].split(" ")[-1] if " " in row["timestamp"] else row["timestamp"],
                        "full_timestamp": row["timestamp"],
                        "temperature": row["temperature"],
                        "humidity": row["humidity"],
                        "heat_index": row["heat_index"],
                        "risk_level": row["risk_level"],
                        "is_anomaly": bool(row["is_anomaly"]),
                        "is_demo": bool(row["is_demo"])
                    })
                return formatted
        except Exception as e:
            print(f"[Weather History DB Error] {e}")

        # In-memory fallback
        with self.lock:
            return self.history_readings[-limit:]

    def _background_poll_loop(self):
        """Dedicated background thread to automatically poll weather data every update_interval."""
        # Initial immediate fetch after 1 second startup delay
        time.sleep(1.0)
        try:
            self.fetch_weather_data(force=True)
        except Exception as e:
            print(f"[Weather Initial Fetch Error] {e}")

        while self.is_running:
            try:
                time.sleep(self.update_interval)
                if not self.demo_mode:
                    self.fetch_weather_data(force=True)
            except Exception as e:
                print(f"[Weather Poll Worker Error] {e}")
                time.sleep(10.0)


# Global singleton instance
weather_manager = WeatherManager()
