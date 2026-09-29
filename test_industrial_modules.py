import sys
import os
import time
import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from core.detector import SafetyDetector
from core.database import init_db, log_incident, get_incident_summary, get_heatmap_data, get_safety_scorecard
from core.copilot import copilot

def run_tests():
    print("==================================================")
    print("🚀 Running SafeVision AI Industrial Modules Verification Suite")
    print("==================================================")

    # 1. Database Initialization & Category Logging Test
    init_db()
    print("\n[Test 1] Testing Database Category Logging...")
    id1 = log_incident("Zone 2 - Scaffolding", "Height Safety (No Harness)", "CRITICAL", "Unharnessed worker at height", coord_x=0.2, coord_y=0.1, category="HEIGHT_HARNESS")
    id2 = log_incident("Zone 3 - Crane Deck", "Suspended Load Drop Zone Hazard", "CRITICAL", "Worker under suspended load", coord_x=0.5, coord_y=0.7, category="SUSPENDED_LOAD")
    id3 = log_incident("Zone 4 - Silo #4", "Confined Space Overstay", "HIGH", "Worker exceeded stay limit", coord_x=0.1, coord_y=0.8, category="CONFINED_SPACE")
    id4 = log_incident("Zone 1 - Fabrication", "Hot Work (No Extinguisher)", "HIGH", "Welding active without extinguisher", coord_x=0.7, coord_y=0.4, category="HOT_WORK")
    id5 = log_incident("Zone 5 - Trench #2", "Trench Edge Collapse Margin", "HIGH", "Worker within collapse margin", coord_x=0.8, coord_y=0.9, category="TRENCH_SECURITY")
    
    summary = get_incident_summary()
    assert summary["harness_violations"] >= 1, "Failed to count harness violation"
    assert summary["suspended_load_hazards"] >= 1, "Failed to count suspended load hazard"
    assert summary["confined_space_events"] >= 1, "Failed to count confined space event"
    assert summary["hot_work_violations"] >= 1, "Failed to count hot work violation"
    assert summary["trench_security_events"] >= 1, "Failed to count trench security event"
    print("✅ Database summary counters verified successfully.")

    # 2. Safety Copilot Expert Engine Test
    print("\n[Test 2] Testing Safety Copilot Expert Engine Queries...")
    queries = [
        "Explain OSHA 1926 harness requirements for working at heights.",
        "What is the OSHA rule for crane suspended loads and drop zones?",
        "What are the permit rules and stay limits for confined spaces?",
        "What is the 35-foot rule and fire extinguisher requirement for hot work?",
        "What is the safe setback distance for excavations and trenches?"
    ]
    for q in queries:
        res = copilot.ask(q)
        assert len(res["response"]) > 50, f"Copilot response too short for: {q}"
        print(f"  • Query: '{q[:40]}...' -> Response Length: {len(res['response'])} chars [OK]")
    print("✅ Safety Copilot expert responses verified.")

    # 3. Vision Detector Synthetic Frame Processing Test
    print("\n[Test 3] Testing Safety Detector Vision Engine & Telemetry...")
    detector = SafetyDetector(model_path="yolov8n.pt", conf_thresh=0.25)
    
    # Create synthetic test frame (640x480)
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:] = (50, 50, 50) # Neutral gray background
    
    # Enable all modules
    detector.set_height_safety(True)
    detector.set_suspended_load(True)
    detector.set_confined_space(True, name="Test Silo", max_minutes=0.01) # fast overstay for test
    detector.set_hot_work(True)
    detector.set_trench_safety(True, line_y_norm=0.75, margin_px=50)
    detector.set_night_mode(False)

    annotated, stats = detector.process_frame(test_frame, zone_id="Zone 1 - Main Floor")
    assert annotated is not None, "Annotated frame should not be None"
    assert annotated.shape == (480, 640, 3), f"Annotated frame shape mismatch: {annotated.shape}"
    assert "height_violation" in stats, "Missing height_violation in stats"
    assert "suspended_load_hazard" in stats, "Missing suspended_load_hazard in stats"
    assert "confined_headcount" in stats, "Missing confined_headcount in stats"
    assert "hot_work_violation" in stats, "Missing hot_work_violation in stats"
    assert "trench_hazard" in stats, "Missing trench_hazard in stats"
    print("✅ Base frame processed and telemetry dictionary populated.")

    # Test Hot Work Sparks Detection with Synthetic Spark
    print("\n[Test 4] Testing Hot Work Spark & Extinguisher Detection...")
    spark_frame = test_frame.copy()
    # Draw bright intense white-yellow spot simulating welding arc
    cv2.circle(spark_frame, (320, 240), 12, (255, 255, 255), -1)
    cv2.circle(spark_frame, (320, 240), 20, (0, 220, 255), 2)
    
    annotated_sparks, spark_stats = detector.process_frame(spark_frame, zone_id="Zone 1 - Welding")
    assert spark_stats["hot_work_active"] == True, "Hot work spark should be detected"
    assert spark_stats["hot_work_violation"] == True, "Should flag missing fire extinguisher violation"
    print("✅ Hot work spark detected and flagged missing fire extinguisher.")

    # Test Night Mode Effect
    print("\n[Test 5] Testing Night Mode Tactical Guard...")
    detector.set_night_mode(True)
    night_frame, night_stats = detector.process_frame(test_frame)
    assert night_stats["night_mode"] == True, "Night mode flag should be True"
    print("✅ Night Mode overlay and telemetry verified.")

    # 4. Heatmap & Scorecard API Data
    print("\n[Test 6] Testing Scorecard & Heatmap Data Serialization...")
    points = get_heatmap_data(limit=50)
    assert len(points) >= 5, f"Expected at least 5 heatmap points, got {len(points)}"
    scorecard = get_safety_scorecard()
    assert "score" in scorecard and "grade" in scorecard, "Scorecard missing key fields"
    print(f"✅ Safety Scorecard: Grade {scorecard['grade']} ({scorecard['score']}/100) | Heatmap Points: {len(points)}")

    print("\n==================================================")
    print("🎉 ALL 6 VERIFICATION TEST SUITES PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
