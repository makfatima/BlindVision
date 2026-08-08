#!/usr/bin/env python3
"""
Fine-tune YOLOv8n on the BlindVision 10-class detection dataset.

Starts from `training/models/yolov8n_coco_pretrained.pt` -- the
official Ultralytics COCO-pretrained checkpoint (AGPL-3.0, see
training/models/README.md) -- rather than random weights, consistent
with Table XIX ("On-device YOLO model (full system): YOLOv8n (nano)").

The manuscript does not specify epoch count, batch size, input
resolution, optimizer, or augmentation settings (Section V.A: "training
hyperparameters not otherwise stated in this manuscript ... will be
specified in the repository release"). The defaults below are
reasonable, commonly used starting points for a 10-class, ~7000-image
dataset on this model size -- treat them as a starting point to tune
against your own held-out split, not as the authors' undisclosed
values.

Usage:
    python training/scripts/train.py --data training/data.yaml
    python training/scripts/train.py --data training/data.yaml --epochs 150 --imgsz 640
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_CHECKPOINT = REPO_ROOT / "training" / "models" / "yolov8n_coco_pretrained.pt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(REPO_ROOT / "training" / "data.yaml"),
                         help="Path to a YOLO-format data.yaml (see training/data.yaml).")
    parser.add_argument("--base-checkpoint", default=str(DEFAULT_BASE_CHECKPOINT),
                         help="Pretrained checkpoint to fine-tune from.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--patience", type=int, default=20, help="Early-stopping patience (epochs).")
    parser.add_argument("--device", default=None, help="e.g. 'cpu', '0' for GPU 0; default lets ultralytics choose.")
    parser.add_argument("--project", default=str(REPO_ROOT / "training" / "runs"))
    parser.add_argument("--name", default="blindvision_yolov8n")
    args = parser.parse_args()

    model = YOLO(args.base_checkpoint)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=args.device,
        project=args.project,
        name=args.name,
        # Match the confidence/IoU thresholds reported in Table III/IV
        # for validation-time metric computation.
        conf=0.45,
        iou=0.50,
    )

    print(f"\nTraining complete. Best weights: {args.project}/{args.name}/weights/best.pt")
    print("Run training/scripts/evaluate.py against your held-out test split "
          "to reproduce Table III/IV/V-style metrics.")


if __name__ == "__main__":
    main()
