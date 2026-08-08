# Pretrained checkpoint provenance

`yolov8n_coco_pretrained.pt` is the official Ultralytics YOLOv8n
checkpoint, pretrained on COCO (80 classes), used here only as the
**fine-tuning starting point** for `training/scripts/train.py` and as
a **drop-in, works-out-of-the-box detector** for the goggles software
before you have your own trained BlindVision 10-class model.

- Source: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt`
- SHA-256: `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`
- Size: 6,549,796 bytes
- License: AGPL-3.0 (Ultralytics). If you distribute a product built on
  this checkpoint or a model fine-tuned from it, review the AGPL-3.0
  terms or obtain an Ultralytics Enterprise license.

Verify the file you have matches, before trusting it:

```bash
sha256sum training/models/yolov8n_coco_pretrained.pt
# f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36
```

If it doesn't match (or the file is missing), re-fetch it directly
rather than trusting a stale copy:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
# downloads to ./yolov8n.pt in the current directory; move it to
# training/models/yolov8n_coco_pretrained.pt
```

## Why COCO-pretrained and not random-init

Table XIX confirms the on-device model is YOLOv8n (nano), CPU-only
inference on the Raspberry Pi 4. The manuscript's own 10-class
detector (Table II: person, door, chair, backpack, laptop, bottle,
pole, vehicle, bicycle, stairs) is fine-tuned rather than trained from
scratch — most of those classes (person, chair, backpack, laptop,
bottle, bicycle; "vehicle" ≈ COCO car/truck/bus/motorcycle) already
exist in COCO, so starting from COCO weights and fine-tuning on a
smaller labeled set is both the standard practice and the only
approach that's practical on the ~5,600-image training split reported
in Table II.

## What you get without any fine-tuning

Six of the ten BlindVision classes overlap with COCO almost directly.
`goggles/vision/coco_mapping.py` maps the relevant COCO classes onto
BlindVision's semantic categories (and the `high_risk_visual_classes`
used by the fusion engine), so **the goggles software produces real,
meaningful detections today**, using this checkpoint, with zero
training required. `door`, `pole`, and `stairs` have no direct COCO
equivalent and will not be detected until you fine-tune on your own
labeled data — see `training/README.md`.
