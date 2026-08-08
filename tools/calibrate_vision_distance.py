#!/usr/bin/env python3
"""
Calibrate the vision distance-estimation model against your own camera
rig (Section III: 1080p, 120 deg FOV USB cameras).

The model is `distance_m = k / bbox_height_ratio` (see
goggles/vision/distance_calibration.py for the rationale). `k` depends
on your camera's focal length/FOV and the real-world height of the
reference object you calibrate against, so it must be fit per-rig,
not assumed.

Two modes:

1. Live camera (needs a webcam + the bundled/your YOLO checkpoint):
   have a person (or a known-height object) stand at several measured
   distances; the tool detects them and records (distance, bbox ratio)
   pairs interactively.

       python tools/calibrate_vision_distance.py live --camera-index 0

2. Manual entry (no camera needed right now — e.g. you already have
   measurements written down, or want to seed a default calibration
   from a pinhole-camera-model estimate before your rig is assembled):

       python tools/calibrate_vision_distance.py manual \
           --reference-object "adult, 1.7m" \
           --sample 1.0:0.85 --sample 2.0:0.43 --sample 3.0:0.29

   Each --sample is `distance_m:bbox_height_ratio`.

Either mode writes `goggles/vision/calibration/vision_calibration.json`
(fit constant, R^2, and the raw samples used), which
`goggles/vision/distance_calibration.py` loads automatically.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from goggles.vision.distance_calibration import DEFAULT_CALIBRATION_PATH, fit_and_save_calibration  # noqa: E402


def run_manual(args: argparse.Namespace) -> None:
    samples: List[Tuple[float, float]] = []
    for raw in args.sample:
        try:
            dist_str, ratio_str = raw.split(":")
            samples.append((float(ratio_str), float(dist_str)))
        except ValueError:
            print(f"Skipping malformed --sample '{raw}'; expected distance_m:bbox_height_ratio")

    if len(samples) < 2:
        print("Need at least 2 valid samples to fit a curve. Aborting.")
        sys.exit(1)

    calib = fit_and_save_calibration(samples, reference_object=args.reference_object, out_path=DEFAULT_CALIBRATION_PATH)
    _report(calib, DEFAULT_CALIBRATION_PATH)


def run_live(args: argparse.Namespace) -> None:
    try:
        import cv2
        from ultralytics import YOLO
    except ImportError:
        print("Live mode needs opencv-python and ultralytics: "
              "pip install -r goggles/requirements.txt")
        sys.exit(1)

    model = YOLO(args.weights)
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        print(f"Could not open camera index {args.camera_index}")
        sys.exit(1)

    samples: List[Tuple[float, float]] = []
    print(f"Live calibration against class '{args.target_class}'.")
    print("Position the reference object at a known distance, then press ENTER "
          "in this terminal (with the camera preview window focused is fine too).")
    print("Type 'done' instead of a distance to finish and fit the curve.\n")

    try:
        while True:
            entry = input("Known distance to reference object now, in meters (or 'done'): ").strip()
            if entry.lower() == "done":
                break
            try:
                known_distance_m = float(entry)
            except ValueError:
                print("Please enter a number of meters, or 'done'.")
                continue

            ok, frame = cap.read()
            if not ok:
                print("Frame capture failed; try again.")
                continue

            frame_h = frame.shape[0]
            results = model.predict(frame, conf=0.45, verbose=False)

            best_ratio = None
            best_conf = 0.0
            for r in results:
                for box in r.boxes:
                    cls_name = model.names[int(box.cls[0])]
                    if cls_name != args.target_class:
                        continue
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        best_ratio = (y2 - y1) / frame_h
                        best_conf = conf

            if best_ratio is None:
                print(f"No '{args.target_class}' detected in this frame; try again "
                      "(check lighting/position).")
                continue

            samples.append((best_ratio, known_distance_m))
            print(f"  Recorded: distance={known_distance_m:.2f}m, "
                  f"bbox_height_ratio={best_ratio:.4f}, confidence={best_conf:.2f}")
    finally:
        cap.release()

    if len(samples) < 2:
        print("Need at least 2 samples to fit a curve. No calibration saved.")
        sys.exit(1)

    calib = fit_and_save_calibration(samples, reference_object=args.target_class, out_path=DEFAULT_CALIBRATION_PATH)
    _report(calib, DEFAULT_CALIBRATION_PATH)


def _report(calib, path: Path) -> None:
    print("\n--- Calibration fit ---")
    print(f"k (distance_m = k / bbox_height_ratio): {calib.k:.4f}")
    print(f"R^2 of fit:                              {calib.fit_r_squared:.4f}")
    print(f"Samples used:                            {calib.n_samples}")
    print(f"Reference object:                        {calib.reference_object}")
    print(f"Saved to:                                 {path}")
    if calib.fit_r_squared < 0.9:
        print("\nWARNING: R^2 < 0.9 suggests noisy measurements or a bad model fit. "
              "Consider re-measuring, using more distance points, or spreading them "
              "further apart before trusting distance-based alert tiers on this rig.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    live = subparsers.add_parser("live", help="Calibrate against a live camera feed.")
    live.add_argument("--camera-index", type=int, default=0)
    live.add_argument("--weights", default=str(REPO_ROOT / "training" / "models" / "yolov8n_coco_pretrained.pt"))
    live.add_argument("--target-class", default="person")
    live.set_defaults(func=run_live)

    manual = subparsers.add_parser("manual", help="Enter pre-measured samples directly.")
    manual.add_argument("--reference-object", required=True)
    manual.add_argument("--sample", action="append", required=True,
                         help="distance_m:bbox_height_ratio, repeatable")
    manual.set_defaults(func=run_manual)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
