"""
SafeVision AI - Quick Demo Clip Recorder
Use this script to easily record a 10-second test video from your webcam or phone camera
and automatically save it to static/demo_clips/ for offline hackathon demos.
"""
import cv2
import time
import os
import sys

def record_clip(cam_source=0, output_name="no_helmet.mp4", duration_seconds=10):
    save_dir = os.path.join("static", "demo_clips")
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, output_name)

    print(f"\n🎥 Opening camera source: {cam_source}...")
    cap = cv2.VideoCapture(cam_source)
    if not cap.isOpened():
        print(f"❌ Failed to open camera {cam_source}. Check if another app is using it.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 30.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    print(f"✅ Camera connected: {width}x{height} @ {fps}fps")
    print(f"🔴 RECORDING for {duration_seconds} seconds -> Saving to: {out_path}")
    print("👉 (Perform your test action in front of the camera: e.g. walk without helmet / lighter flame)")

    start_time = time.time()
    frames_recorded = 0

    while True:
        elapsed = time.time() - start_time
        remaining = max(0, duration_seconds - elapsed)
        ret, frame = cap.read()
        if not ret:
            break

        writer.write(frame)
        frames_recorded += 1

        # Display progress in console
        sys.stdout.write(f"\rRecording: {elapsed:.1f}s / {duration_seconds}s (Frames: {frames_recorded}) | Remaining: {remaining:.1f}s ")
        sys.stdout.flush()

        if elapsed >= duration_seconds:
            break

    cap.release()
    writer.release()
    print(f"\n🎉 Saved successfully: {out_path}")
    print(f"💡 You can now enter '{out_path}' into the SafeVision Dashboard 'Quick Connect' box!\n")

if __name__ == "__main__":
    print("=" * 60)
    print("   SafeVision AI - Quick Demo Clip Creator")
    print("=" * 60)
    print("Choose which clip you want to record:")
    print(" 1. No Helmet / PPE Violation clip (no_helmet.mp4)")
    print(" 2. Fire / Spark / Lighter clip (fire_test.mp4)")
    print(" 3. Worker Fall / Collapse clip (fall_test.mp4)")
    
    choice = input("\nEnter choice [1, 2, or 3] (default 1): ").strip() or "1"
    name_map = {"1": "no_helmet.mp4", "2": "fire_test.mp4", "3": "fall_test.mp4"}
    clip_name = name_map.get(choice, "no_helmet.mp4")

    source_in = input("Enter Camera Index (default 0 for laptop webcam, or 1 for USB DroidCam): ").strip() or "0"
    try:
        source_val = int(source_in)
    except ValueError:
        source_val = source_in

    record_clip(cam_source=source_val, output_name=clip_name, duration_seconds=10)
