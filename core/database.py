import sqlite3
import os
from datetime import datetime

DB_PATH = "safety_records.db"

def init_db():
    """Initializes the SQLite database for safety incidents, compliance logs, and weather history."""
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
            acknowledged INTEGER DEFAULT 0
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
    conn.commit()
    conn.close()

def log_incident(zone: str, incident_type: str, severity: str, details: str, snapshot_path: str = ""):
    """Logs a safety violation or hazard incident."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO incidents (timestamp, zone, incident_type, severity, details, snapshot_path, acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (now_str, zone, incident_type, severity, details, snapshot_path))
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

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_type LIKE '%Thermal%' OR incident_type LIKE '%Heat%'")
    thermal_hazards = cursor.fetchone()[0] or 0

    conn.close()
    return {
        "total_incidents": total_incidents,
        "helmet_violations": helmet_violations,
        "vest_violations": vest_violations,
        "fire_hazards": fire_hazards,
        "thermal_hazards": thermal_hazards
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


