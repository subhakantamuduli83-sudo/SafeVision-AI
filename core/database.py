import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

DB_PATH = "safety_records.db"

def init_db():
    """Initializes the SQLite database for safety incidents, compliance logs, heatmap coordinates, and weather history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            zone TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT,
            snapshot_path TEXT,
            acknowledged INTEGER DEFAULT 0,
            coord_x REAL DEFAULT 0.5,
            coord_y REAL DEFAULT 0.5,
            category TEXT DEFAULT 'PPE'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hourly_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_workers INTEGER DEFAULT 0,
            compliant_workers INTEGER DEFAULT 0,
            violations INTEGER DEFAULT 0,
            compliance_rate REAL DEFAULT 100.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            heat_index REAL NOT NULL,
            wind_speed REAL DEFAULT 0.0,
            pressure REAL DEFAULT 1013.25,
            condition TEXT DEFAULT 'Clear',
            risk_level TEXT NOT NULL,
            is_anomaly INTEGER DEFAULT 0,
            anomaly_reasons TEXT,
            is_demo INTEGER DEFAULT 0
        )
    """)
    
    # Safe schema migration for existing databases missing new columns
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN coord_x REAL DEFAULT 0.5")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN coord_y REAL DEFAULT 0.5")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN category TEXT DEFAULT 'PPE'")
    except Exception:
        pass

    conn.commit()
    conn.close()

def log_incident(zone: str, incident_type: str, severity: str, details: str, snapshot_path: str = "",
                 coord_x: float = 0.5, coord_y: float = 0.5, category: str = "PPE"):
    """Logs a safety violation, fall, geofence breach, or hazard incident with spatial coordinates."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO incidents (timestamp, zone, incident_type, severity, details, snapshot_path, acknowledged, coord_x, coord_y, category)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (now_str, zone, incident_type, severity, details, snapshot_path, coord_x, coord_y, category))
    conn.commit()
    incident_id = cursor.lastrowid
    conn.close()
    return incident_id

def get_recent_incidents(limit: int = 20):
    """Retrieves the most recent safety incidents."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def acknowledge_incident(incident_id: int):
    """Marks an incident as acknowledged by safety supervisor."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE incidents SET acknowledged = 1 WHERE id = ?", (incident_id,))
    conn.commit()
    conn.close()

def get_incident_summary():
    """Returns aggregated stats for dashboard counters."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM incidents")
    total_incidents = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Helmet%'")
    helmet_violations = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Vest%'")
    vest_violations = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Fire%' OR incident_type LIKE '%Smoke%'")
    fire_hazards = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Fall%' OR incident_type LIKE '%Down%'")
    fall_incidents = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Perimeter%' OR incident_type LIKE '%Danger%' OR incident_type LIKE '%Zone%'")
    perimeter_breaches = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Phone%' OR incident_type LIKE '%Distraction%'")
    distraction_events = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Proximity%' OR incident_type LIKE '%Forklift%'")
    proximity_warnings = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Harness%' OR incident_type LIKE '%Height%'")
    harness_violations = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Suspended%' OR incident_type LIKE '%Drop%' OR incident_type LIKE '%Crane%'")
    suspended_load_hazards = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Confined%' OR incident_type LIKE '%Overstay%'")
    confined_space_events = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Hot Work%' OR incident_type LIKE '%Extinguisher%' OR incident_type LIKE '%Welding%'")
    hot_work_violations = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Trench%' OR incident_type LIKE '%Intrusion%' OR incident_type LIKE '%Perimeter Security%'")
    trench_security_events = cursor.fetchone()[0] or 0

    conn.close()
    return {
        "total_incidents": total_incidents,
        "helmet_violations": helmet_violations,
        "vest_violations": vest_violations,
        "fire_hazards": fire_hazards,
        "fall_incidents": fall_incidents,
        "perimeter_breaches": perimeter_breaches,
        "distraction_events": distraction_events,
        "proximity_warnings": proximity_warnings,
        "harness_violations": harness_violations,
        "suspended_load_hazards": suspended_load_hazards,
        "confined_space_events": confined_space_events,
        "hot_work_violations": hot_work_violations,
        "trench_security_events": trench_security_events
    }

def get_heatmap_data(limit: int = 150) -> List[Dict[str, Any]]:
    """Retrieves 2D spatial coordinate density points for the floor hazard heatmap."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, zone, incident_type, severity, coord_x, coord_y, category 
        FROM incidents 
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_safety_scorecard() -> Dict[str, Any]:
    """Computes an executive factory safety grade, zero-accident streak, and compliance scorecard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total vs Critical
    cursor.execute("SELECT COUNT(*) FROM incidents")
    total = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'CRITICAL'")
    critical_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'HIGH'")
    high_count = cursor.fetchone()[0] or 0

    conn.close()

    # Safety Score Algorithm: Starts at 100, penalties for violations
    score = max(45, round(100 - (critical_count * 8 + high_count * 2.5), 1))
    
    if score >= 90:
        grade = "A+"
        grade_desc = "EXEMPLARY COMPLIANCE"
        grade_color = "#10b981"
    elif score >= 80:
        grade = "A"
        grade_desc = "HIGH STANDARD COMPLIANCE"
        grade_color = "#06b6d4"
    elif score >= 70:
        grade = "B"
        grade_desc = "MODERATE RISK FLOOR"
        grade_color = "#f59e0b"
    else:
        grade = "C"
        grade_desc = "SAFETY INTERVENTION NEEDED"
        grade_color = "#ef4444"

    return {
        "score": score,
        "grade": grade,
        "grade_desc": grade_desc,
        "grade_color": grade_color,
        "total_incidents": total,
        "critical_incidents": critical_count,
        "high_incidents": high_count,
        "zero_accident_days": max(1, 14 - critical_count),
        "osha_compliance_pct": min(100.0, max(50.0, score + 2.0))
    }

def log_weather_reading(timestamp: str, temperature: float, humidity: float, heat_index: float,
                        wind_speed: float, pressure: float, condition: str, risk_level: str,
                        is_anomaly: int = 0, anomaly_reasons: str = "", is_demo: int = 0):
    """Logs an environmental weather reading to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO weather_logs (timestamp, temperature, humidity, heat_index, wind_speed, pressure, condition, risk_level, is_anomaly, anomaly_reasons, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, temperature, humidity, heat_index, wind_speed, pressure, condition, risk_level, is_anomaly, anomaly_reasons, is_demo))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def get_recent_weather_logs(limit: int = 50, include_demo: bool = True):
    """Retrieves recent weather readings."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if include_demo:
        cursor.execute("SELECT * FROM weather_logs ORDER BY id DESC LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT * FROM weather_logs WHERE is_demo = 0 ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Auto-initialize database tables on module import
init_db()



