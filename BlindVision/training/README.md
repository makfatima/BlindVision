# Training pipeline

Fine-tunes the bundled COCO-pretrained checkpoint on the manuscript's
own 10-class scheme (Table II: person, door, chair, backpack, laptop,
bottle, pole, vehicle, bicycle, stairs).

## What's here

- `models/yolov8n_coco_pretrained.pt` — official Ultralytics COCO
  checkpoint (see `models/README.md` for sha256/provenance). Used both
  as the fine-tuning starting point and as a directly usable detector
  for the six classes that overlap COCO (see below).
- `data.yaml` — Ultralytics dataset config matching Table II's class
  list and ordering. **You need to supply your own labeled images** —
  the manuscript's own dataset is not yet public (Section V.D).
- `scripts/train.py` — fine-tunes from the bundled checkpoint.
- `scripts/evaluate.py` — reports the same metric set as Tables III–V
  (precision/recall/F1/mAP, sensitivity/false-alarm-rate/FNR, per-class
  breakdown) on a held-out split.

## You don't have to train anything to get started

`goggles/vision/coco_mapping.py` maps six of the ten classes directly
from COCO (`person`, `bicycle`, `car`/`truck`/`bus`/`motorcycle` →
`vehicle`, `chair`, `backpack`, `laptop`, `bottle`) — see
`models/README.md` for the exact mapping and its coverage of
`high_risk_visual_classes`. This is enough for the fusion engine's
critical-obstacle escalation (Algorithm 1, tier 3) to work correctly
today, with the bundled checkpoint, with zero training.

## When to actually train

Once you have labeled data (or want `door`, `pole`, `stairs` detected,
which have no COCO equivalent):

```bash
# 1. Arrange your images/labels in Ultralytics YOLO format:
#    data/blindvision_detect/images/{train,val,test}/*.jpg
#    data/blindvision_detect/labels/{train,val,test}/*.txt
# 2. Point data.yaml's `path` at that directory (or pass --data).

python training/scripts/train.py --data training/data.yaml --epochs 100

# 3. Evaluate against your held-out test split:
python training/scripts/evaluate.py \
    --weights training/runs/blindvision_yolov8n/weights/best.pt \
    --data training/data.yaml --out metrics.json

# 4. Point the goggles software at your new weights:
#    config/fusion_config.yaml -> vision.weights_path = <path to best.pt>
#                                  vision.class_mapping = "identity"
```

`class_mapping: identity` skips `coco_mapping.py` entirely — your
fine-tuned model already emits BlindVision's own 10 class names
(`data.yaml`'s `names:` list), so no translation layer is needed.

## Reproducing Table III's reported numbers

Table III's 96%+ precision/recall/mAP figures were measured on the
authors' own 700-image held-out test split, at IoU 0.50 and confidence
0.45 (both are the `evaluate.py` defaults). Your own numbers on your
own dataset will differ — dataset size, class balance, and image
quality all matter — but `evaluate.py` computes the same metric
definitions so the two are directly comparable once you have a
comparable dataset.

## Hyperparameters

The manuscript does not specify epoch count, batch size, input
resolution, optimizer, or augmentation settings (Section V.A). The
defaults in `scripts/train.py` (100 epochs, 640px, batch 16, patience
20) are reasonable, commonly used starting points for a 10-class,
~7,000-image dataset on YOLOv8n — tune against your own held-out
split rather than treating them as the authors' undisclosed values.
