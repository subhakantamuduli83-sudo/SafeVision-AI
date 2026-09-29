import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List

class SafetyCopilot:
    """
    AI Safety Copilot & OSHA/ISO-45001 Compliance Intelligence Assistant.
    Analyzes live safety records, thermal conditions, and provides actionable recommendations.
    """

    def __init__(self, db_path: str = "safety_records.db"):
        self.db_path = db_path
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    def get_context_summary(self) -> Dict[str, Any]:
        """Gathers latest database metrics, recent violations, and weather data for context grounding."""
        summary = {
            "total_incidents": 0,
            "violations_by_type": {},
            "recent_incidents": [],
            "risk_status": "NORMAL"
        }
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM incidents")
            summary["total_incidents"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT incident_type, COUNT(*) as cnt 
                FROM incidents 
                GROUP BY incident_type 
                ORDER BY cnt DESC
            """)
            for row in cursor.fetchall():
                summary["violations_by_type"][row["incident_type"]] = row["cnt"]

            cursor.execute("""
                SELECT id, timestamp, zone, incident_type, severity, details, acknowledged 
                FROM incidents 
                ORDER BY id DESC LIMIT 8
            """)
            summary["recent_incidents"] = [dict(r) for r in cursor.fetchall()]
            conn.close()
        except Exception as e:
            print(f"[Copilot Context Error] {e}")
        return summary

    def ask(self, query: str, weather_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Processes a natural language query using AI or the expert safety rule engine."""
        query_clean = query.strip()
        context = self.get_context_summary()

        # If Gemini API key is configured, attempt LLM call
        if self.gemini_api_key:
            try:
                import requests
                prompt = (
                    f"You are SafeVision AI Copilot, an expert Industrial Health & Safety (EHS) Advisor specializing in OSHA and ISO 45001.\n"
                    f"Live Factory Data Context:\n"
                    f"- Total Incidents Recorded: {context['total_incidents']}\n"
                    f"- Violations Breakdown: {json.dumps(context['violations_by_type'])}\n"
                    f"- Recent 8 Incidents: {json.dumps(context['recent_incidents'])}\n"
                    f"- Current Weather/Heat Context: {json.dumps(weather_context or {})}\n\n"
                    f"User Query: {query_clean}\n\n"
                    f"Provide a clear, highly professional, executive response with OSHA/ISO safety guidance and 2-3 specific action items."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                resp = requests.post(url, headers=headers, json=payload, timeout=8.0)
                if resp.status_code == 200:
                    result = resp.json()
                    answer = result["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "response": answer,
                        "mode": "Gemini-1.5-Flash (Cloud AI)",
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
            except Exception as e:
                print(f"[Copilot LLM Fallback] {e}")

        # Expert Industrial Rule-Based Reasoning Engine (Deterministic & Fast Fallback)
        answer = self._generate_expert_response(query_clean, context, weather_context)
        return {
            "response": answer,
            "mode": "SafeVision Edge Expert Engine (OSHA/ISO-45001)",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    def _generate_expert_response(self, query: str, ctx: Dict[str, Any], weather: Dict[str, Any]) -> str:
        q = query.lower()
        total = ctx["total_incidents"]
        by_type = ctx["violations_by_type"]
        recents = ctx["recent_incidents"]
        heat_idx = weather.get("heat_index") if weather else None
        temp = weather.get("temperature") if weather else None

        # 1. Summary / Overview Request
        if any(w in q for w in ["summary", "overview", "status", "report", "today", "shift"]):
            lines = [
                f"### 🛡️ SafeVision AI Shift Safety Executive Summary\n",
                f"- **Total Recorded Events:** `{total}` incidents in database.",
                f"- **Top Violation Categories:**"
            ]
            if by_type:
                for k, v in list(by_type.items())[:4]:
                    lines.append(f"  • **{k}:** {v} incidents")
            else:
                lines.append("  • *No active non-compliance logged yet today.*")

            if heat_idx:
                lines.append(f"- **Thermal Stress Index:** `{heat_idx}°C` (Ambient Temp: `{temp}°C`)")

            lines.append("\n**Recommended Supervisor Actions (OSHA 1910.132 / 1926.100):**")
            lines.append("1. Conduct a mandatory 5-minute toolbox talk on PPE donning before next shift entry.")
            lines.append("2. Inspect physical barrier geofences around machinery zones.")
            lines.append("3. Ensure cold hydration stations are accessible if Heat Index exceeds 38°C.")
            return "\n".join(lines)

        # 2. OSHA / Regulation Queries
        if any(w in q for w in ["osha", "iso", "standard", "regulation", "law", "rule", "protocol"]):
            return (
                "### 📜 OSHA & ISO 45001 Regulatory Guidance\n\n"
                "1. **OSHA 1926.100 (Head Protection):** Mandatory hardhat protection where danger of falling objects, head strikes, or electrical contact exists.\n"
                "2. **OSHA 1910.132 (General PPE Requirements):** Personal protective equipment must be provided, used, and maintained in a sanitary and reliable condition.\n"
                "3. **OSHA General Duty Clause Section 5(a)(1):** Employers must furnish a workplace free from recognized hazards causing or likely to cause death or serious physical harm.\n"
                "4. **ISO 45001 Clause 8.1.2:** Implement hierarchy of controls: Elimination → Substitution → Engineering Controls → Administrative Controls → PPE."
            )

        # 3. Fall / Man-Down & Emergency Questions
        if any(w in q for w in ["fall", "man down", "faint", "injury", "medical", "emergency", "collapse"]):
            return (
                "### 🚨 Man-Down & Fall Emergency Response Protocol\n\n"
                "- **Detection Latency:** Edge AI detects horizontal posture collapse in < 2.5 seconds.\n"
                "- **Automatic Escalation:**\n"
                "  1. Continuous dual-tone audio alarm + TTS floor announcement.\n"
                "  2. Incident snapshot dispatched immediately to Safety Supervisor's Telegram.\n"
                "  3. On-screen pulsing red emergency status.\n"
                "- **OSHA Standard:** First-aid personnel and medical response must be dispatched within 3-4 minutes."
            )

        # 4. Height Safety & Harness Tethering (OSHA 1926 Subpart M)
        if any(w in q for w in ["height", "harness", "scaffold", "ladder", "elevated", "fall arrest", "lanyard"]):
            return (
                "### 🏗️ OSHA 1926 Subpart M: Fall Protection & Height Safety\n\n"
                "- **Mandatory Trigger Height:** Full-body harness and shock-absorbing lanyards are mandatory for any work at or above **6 feet (1.8 meters)** in construction, or **4 feet (1.2 meters)** in general industry.\n"
                "- **Edge AI Action:** SafeVision AI inspects worker torso for cross-body harness webbing and verifies anchor lines in designated elevated zones.\n"
                "- **Immediate Response:** Any unharnessed worker in an elevated zone triggers a CRITICAL siren and instant supervisor notification."
            )

        # 5. Overhead Crane & Suspended Load Hazards (OSHA 1926.1400)
        if any(w in q for w in ["crane", "suspended load", "drop zone", "line of fire", "hoist", "rigging"]):
            return (
                "### 🏗️ OSHA 1926.1400: Suspended Loads & Line-of-Fire Safety\n\n"
                "- **Core Rule:** No employee is permitted to stand, pass, or work under a suspended load (OSHA 1926.1425).\n"
                "- **Drop Shadow Projection:** SafeVision AI detects hoisted cargo and projects a dynamic circular **Drop Hazard Zone** on the floor with rotating radar sweeps.\n"
                "- **Automatic Hazard Alarm:** Workers stepping into the projected drop shadow trigger a high-decibel warning to evacuate the line of fire immediately."
            )

        # 6. Confined Space Management (OSHA 1910.146)
        if any(w in q for w in ["confined space", "manhole", "tank", "silo", "headcount", "overstay", "toxic gas"]):
            return (
                "### 🚪 OSHA 1910.146: Permit-Required Confined Space Protocols\n\n"
                "- **Headcount & Entry Control:** An attendant must maintain continuous, exact headcounts of all entrants entering tanks, manholes, or silos.\n"
                "- **Safe Stay Timers:** In hazardous atmospheres, max stay limits (e.g., 30–45 mins) must be strictly enforced.\n"
                "- **SafeVision Watchdog:** Edge AI tracks worker entry/exit counts in real-time and triggers automatic overstay evacuation alarms if the limit is exceeded."
            )

        # 7. Hot Work & Welding Fire Watch (OSHA 1910.252)
        if any(w in q for w in ["hot work", "welding", "spark", "extinguisher", "cutting", "torch", "fire watch"]):
            return (
                "### 🔥 OSHA 1910.252: Hot Work & Fire Watch Protocols\n\n"
                "- **The 35-Foot Rule:** All combustible materials must be moved at least 35 feet (10.6m) away from welding or cutting operations.\n"
                "- **Mandatory Fire Extinguisher:** A charged, operable fire extinguisher must be immediately accessible within the hot work perimeter.\n"
                "- **SafeVision AI Watch:** Edge AI continuously checks for active welding sparks and verifies the presence of an extinguisher within a 5-meter radius."
            )

        # 8. Trenching, Excavations & Cave-in Margins (OSHA 1926 Subpart P)
        if any(w in q for w in ["trench", "excavation", "cave-in", "shoring", "setback", "trench margin"]):
            return (
                "### ⚠️ OSHA 1926 Subpart P: Excavation & Trench Safety\n\n"
                "- **Spoil Pile & Equipment Setback:** Heavy machinery, spoil piles, and material must be kept at least **2 feet (0.6 meters)** away from trench edges to prevent cave-ins.\n"
                "- **Protective Systems:** Trenches 5 feet (1.5m) or deeper require proper shoring, shielding (trench box), or sloping.\n"
                "- **SafeVision Edge Margins:** AI monitors the setback buffer line and alerts workers or heavy equipment operating too close to unsupported trench lips."
            )

        # 9. Danger Zone / Geofencing Questions
        if any(w in q for w in ["danger zone", "geofence", "perimeter", "restricted", "boundary"]):
            return (
                "### 🛑 Virtual Danger Zone & Geofencing Protocols\n\n"
                "- **Purpose:** Prevents unauthorized worker proximity to high-risk robotic arms, conveyor pinch points, and heavy equipment.\n"
                "- **Mechanism:** Polygon intersection algorithms (`cv2.pointPolygonTest`) continuously monitor worker centroids.\n"
                "- **Corrective Action:** Workers crossing marked hazard perimeters receive immediate vocal sirens and a logged breach record."
            )

        # 10. Weather / Heat Stress Questions
        if any(w in q for w in ["heat", "weather", "temperature", "humidity", "thermal", "dehydration"]):
            hi_val = heat_idx or 32.0
            risk = "HIGH" if hi_val >= 39 else "MODERATE" if hi_val >= 32 else "LOW"
            return (
                f"### ☀️ Thermal Stress & Environmental Risk Assessment\n\n"
                f"- **Current Calculated Heat Index:** `{hi_val}°C` (Risk: **{risk}**)\n"
                f"- **NOAA Guidelines:**\n"
                f"  • **32°C - 38°C (Caution):** Fatigue possible with prolonged exposure; schedule 10-min hydration breaks per hour.\n"
                f"  • **39°C - 45°C (Danger):** Heat cramps and exhaustion likely. Increase mandatory shaded rest cycles to 15 mins.\n"
                f"  • **> 46°C (Extreme Danger):** High risk of heat stroke. Suspend non-essential heavy outdoor labor."
            )

        # 11. Default Smart Safety Advisor Answer
        return (
            f"### 🛡️ SafeVision AI Industrial Safety Advisor\n\n"
            f"Based on your site's current live telemetry:\n"
            f"- **Active Monitored Zone:** Main Construction / Plant Floor\n"
            f"- **Logged Incidents:** `{total}` events recorded\n\n"
            f"**Key Recommendations:**\n"
            f"1. **Height Safety:** Ensure safety harnesses are donned before accessing elevated scaffolding.\n"
            f"2. **Crane Zones:** Keep clear of active suspended load drop shadows.\n"
            f"3. **Confined Spaces:** Monitor entry headcount and stay duration limits.\n"
            f"4. **Hot Work:** Ensure a dedicated fire extinguisher is present before striking arcs.\n"
            f"5. **OSHA Compliance Audit:** Export the PDF Safety Audit report at the end of every shift."
        )

# Global singleton
copilot = SafetyCopilot()
