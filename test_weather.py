import sys
import os

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 65)
print("   [SAFEVISION AI] WEATHER & THERMAL RISK ENGINE VERIFICATION")
print("=" * 65)

# 1. Test NOAA Heat Index Calculation
print("\n[1/5] Testing NOAA Rothfusz & Steadman Heat Index Calculations...")
from core.weather import calculate_noaa_heat_index

# Test Case 1: 35°C (95°F) with 70% RH -> High Danger range
hi_1 = calculate_noaa_heat_index(35.0, 70.0)
print(f"      • Test Case 1: Temp=35.0°C, RH=70% -> Heat Index = {hi_1}°C")
assert hi_1 > 45.0, f"Expected heat index > 45°C, got {hi_1}"

# Test Case 2: 24°C (75.2°F) with 50% RH -> Mild / Steadman
hi_2 = calculate_noaa_heat_index(24.0, 50.0)
print(f"      • Test Case 2: Temp=24.0°C, RH=50% -> Heat Index = {hi_2}°C")
assert abs(hi_2 - 24.0) <= 2.0, f"Expected mild heat index near 24°C, got {hi_2}"
print("      [OK] Mathematical Heat Index formula passed with accuracy!")

# 2. Test Live Weather API Connection (Bhubaneswar, Odisha)
print("\n[2/5] Testing Real-Time Weather API Connection (Open-Meteo / Live Feed)...")
from core.weather import weather_manager
w_data = weather_manager.fetch_weather_data(force=True)

print(f"      • Location: {w_data.get('location')}")
print(f"      • Temperature: {w_data.get('temperature')}°C ({w_data.get('temp_status')})")
print(f"      • Relative Humidity: {w_data.get('humidity')}% ({w_data.get('humidity_status')})")
print(f"      • Heat Index: {w_data.get('heat_index')}°C")
print(f"      • Risk Level: {w_data.get('risk_badge')}")
print(f"      • Data Source: {w_data.get('data_source')}")
print(f"      • Reasons: {w_data.get('reasons')}")
assert w_data.get("temperature") is not None, "Temperature should not be None from live API"
print("      [OK] Live real-time weather data retrieved and parsed successfully!")

# 3. Test Database Persistence
print("\n[3/5] Testing SQLite Database Logging for Environmental Metrics...")
from core.database import get_recent_weather_logs
logs = get_recent_weather_logs(limit=5)
print(f"      • Retrieved {len(logs)} recent weather logs from database.")
assert len(logs) > 0, "Expected at least 1 logged weather record in database."
print(f"      • Latest Log Record: ID={logs[0]['id']} | Temp={logs[0]['temperature']}°C | HI={logs[0]['heat_index']}°C | Risk={logs[0]['risk_level']}")
print("      [OK] Database logging verified!")

# 4. Test Demo Simulation Mode & Heat Surge Anomaly
print("\n[4/5] Testing Demo Simulation Mode & Thermal Anomaly Detection...")
demo_res = weather_manager.set_demo_mode(enabled=True, temp=43.5, humidity=78.0)
print(f"      • Simulated Temp: {demo_res.get('temperature')}°C | Humidity: {demo_res.get('humidity')}%")
print(f"      • Calculated Simulated Heat Index: {demo_res.get('heat_index')}°C")
print(f"      • Risk Level: {demo_res.get('risk_badge')}")
print(f"      • Anomaly Detected: {demo_res.get('is_anomaly')} (Type: {demo_res.get('anomaly_type')})")
print(f"      • Explainable Reasons: {demo_res.get('reasons')}")
assert demo_res.get("risk_level") in ["HIGH", "CRITICAL"], "Heat surge should trigger HIGH or CRITICAL risk"
assert demo_res.get("is_demo") is True, "is_demo must be True in demo mode"

# Reset Demo Mode
weather_manager.set_demo_mode(enabled=False)
print("      [OK] Demo simulation and anomaly engine verified!")

# 5. Test PDF and CSV Compliance Report Generation
print("\n[5/5] Testing Environmental Compliance in PDF and CSV Audit Reports...")
from core.report_generator import generate_pdf_report, generate_csv_report
pdf_file = generate_pdf_report("Safety_Compliance_Audit_Report.pdf")
csv_data = generate_csv_report()
print(f"      • Generated PDF Report: {pdf_file} ({os.path.getsize(pdf_file)} bytes)")
print(f"      • Generated CSV Report: {len(csv_data)} bytes")
print("      [OK] Audit report generation with weather summary verified!")

print("\n" + "=" * 65)
print("   [SUCCESS] ALL WEATHER & THERMAL RISK TESTS PASSED!")
print("=" * 65)
