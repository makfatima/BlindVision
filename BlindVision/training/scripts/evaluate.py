#!/usr/bin/env python3
"""
Evaluate a trained BlindVision detection model on a held-out test
split, reporting the same metric set as Tables III-V of the
manuscript:

  Table III - Precision, Recall, F1, mAP@0.50, mAP@0.50:0.95
  Table IV  - Sensitivity, false-alarm rate (1 - precision), FNR
              (specificity/accuracy are deliberately not reported --
              see Section VI.B: open-set detection has no intrinsic
              true-negative count)
  Table V   - per-class TP/FP/FN/precision/recall

Usage:
    python training/scripts/evaluate.py --weights training/runs/blindvision_yolov8n/weights/best.pt \
        --data training/data.yaml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ultralytics import YOLO

CONFIDENCE_THRESHOLD = 0.45  # matches Table III/IV
IOU_THRESHOLD = 0.50         # matches Table III/IV


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, help="Path to a trained .pt checkpoint.")
    parser.add_argument("--data", required=True, help="Path to the YOLO data.yaml.")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--out", default=None, help="Optional path to dump metrics as JSON.")
    args = parser.parse_args()

    model = YOLO(args.weights)
    metrics = model.val(
        data=args.data,
        split=args.split,
        conf=CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
    )

    # Pooled metrics (Table III)
    precision = float(metrics.box.mp)       # mean precision across classes
    recall = float(metrics.box.mr)          # mean recall across classes
    map50 = float(metrics.box.map50)
    map50_95 = float(metrics.box.map)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    print("\n=== Pooled metrics (Table III-style) ===")
    print(f"Precision:        {precision * 100:.1f}%")
    print(f"Recall:           {recall * 100:.1f}%")
    print(f"F1-score:         {f1 * 100:.1f}%")
    print(f"mAP@0.50:         {map50 * 100:.1f}%")
    print(f"mAP@0.50:0.95:    {map50_95 * 100:.1f}%")

    # Table IV: sensitivity, false-alarm rate, FNR.
    # Specificity/accuracy intentionally omitted (Section VI.B rationale).
    sensitivity = recall
    false_alarm_rate = 1.0 - precision
    fnr = 1.0 - recall

    print("\n=== Reliability metrics (Table IV-style) ===")
    print(f"Sensitivity:            {sensitivity * 100:.1f}%")
    print(f"False-alarm rate (1-P): {false_alarm_rate * 100:.1f}%")
    print(f"False Negative Rate:    {fnr * 100:.1f}%")

    # Table V: per-class precision/recall (TP/FP/FN require confusion
    # matrix internals; ultralytics exposes per-class P/R directly).
    print("\n=== Per-class metrics (Table V-style) ===")
    names = metrics.names
    per_class = {}
    try:
        p_per_class = metrics.box.p        # precision per class
        r_per_class = metrics.box.r        # recall per class
        for i, cls_name in names.items():
            if i < len(p_per_class):
                per_class[cls_name] = {
                    "precision": float(p_per_class[i]),
                    "recall": float(r_per_class[i]),
                }
                print(f"{cls_name:12s}  P={p_per_class[i]*100:5.1f}%  R={r_per_class[i]*100:5.1f}%")
    except (AttributeError, IndexError):
        print("(Per-class breakdown unavailable for this ultralytics version; "
              "see metrics.box for the raw fields.)")

    if args.out:
        payload = {
            "pooled": {
                "precision": precision, "recall": recall, "f1": f1,
                "map50": map50, "map50_95": map50_95,
            },
            "reliability": {
                "sensitivity": sensitivity,
                "false_alarm_rate": false_alarm_rate,
                "false_negative_rate": fnr,
            },
            "per_class": per_class,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "iou_threshold": IOU_THRESHOLD,
            "split": args.split,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2))
        print(f"\nWrote metrics to {args.out}")


if __name__ == "__main__":
    main()
