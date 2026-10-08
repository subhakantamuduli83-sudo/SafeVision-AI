import sys
import numpy as np
import cv2
import math

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from core.detector import SafetyDetector

def test_fall():
    print("=" * 60)
    print("[TEST] Testing Fall & Man-Down AI Engine (Ground & Bed Scenarios)")
    print("=" * 60)

    detector = SafetyDetector()
    detector.fall_detection_enabled = True

    print("\n[Test 1] Testing horizontal human geometry (e.g. lying on bed/floor)...")
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:] = 60

    # Draw simulated horizontal worker on bed/floor
    cv2.rectangle(test_frame, (150, 260), (450, 360), (120, 150, 180), -1)
    cv2.circle(test_frame, (190, 310), 20, (180, 190, 210), -1) # head

    # Verify fallback human validator accepts horizontal humans
    box_horizontal = (150, 260, 450, 360)
    is_valid = detector._is_valid_human(test_frame, box_horizontal, kpts=None)
    print(f"Horizontal human validation test (w=300, h=100, aspect=3.0): {is_valid}")
    assert is_valid == True, "Failed to validate horizontal human posture!"

    # Test pose skeletal angle with horizontal spine
    print("\n[Test 2] Testing horizontal spine pose calculation...")
    # 17 keypoints: [x, y, conf]
    kpts = np.zeros((17, 3), dtype=np.float32)
    kpts[:, 2] = 0.8 # high confidence
    # Lying horizontal: Shoulders at x=200, y=300; Hips at x=340, y=305
    kpts[5] = [190, 295, 0.85] # left shoulder
    kpts[6] = [210, 305, 0.85] # right shoulder
    kpts[11] = [330, 300, 0.85] # left hip
    kpts[12] = [350, 310, 0.85] # right hip
    kpts[0] = [150, 300, 0.90] # nose

    is_valid_pose = detector._is_valid_human(test_frame, box_horizontal, kpts=kpts)
    print(f"Pose keypoints human validation (lying horizontal): {is_valid_pose}")
    assert is_valid_pose == True, "Failed to validate horizontal pose keypoints!"

    print("\n[OK] ALL FALL DETECTION UNIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_fall()
