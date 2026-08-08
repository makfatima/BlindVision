"""
COCO -> BlindVision class mapping.

The bundled checkpoint (`training/models/yolov8n_coco_pretrained.pt`)
is COCO-pretrained, not fine-tuned on the manuscript's own 10-class
dataset (Table II). Rather than shipping a detector that reports raw
COCO labels the rest of the codebase doesn't know about, this module
maps the subset of COCO's 80 classes that correspond to BlindVision's
semantic categories, and marks everything else as unmapped (dropped).

Coverage vs. Table II's 10 classes:
    person    <- COCO "person"                              (direct)
    vehicle   <- COCO "car", "truck", "bus", "motorcycle"    (merged)
    bicycle   <- COCO "bicycle"                              (direct)
    chair     <- COCO "chair"                                (direct)
    backpack  <- COCO "backpack"                              (direct)
    laptop    <- COCO "laptop"                                (direct)
    bottle    <- COCO "bottle"                                (direct)
    door      <- no COCO equivalent -> requires fine-tuning
    pole      <- no COCO equivalent -> requires fine-tuning
    stairs    <- no COCO equivalent -> requires fine-tuning

`high_risk_visual_classes` in config/fusion_config.yaml (person,
vehicle, bicycle) is fully covered by this mapping, so Algorithm 1's
tier-3 escalation logic works correctly on the pretrained checkpoint
without any fine-tuning.

Once you fine-tune on your own data with training/data.yaml's class
list, point goggles/main.py at your trained checkpoint instead and set
`vision.class_mapping: identity` in config/fusion_config.yaml (or just
skip this module — the fine-tuned model already emits BlindVision
class names directly).
"""

from __future__ import annotations

from typing import Optional

# COCO class name -> BlindVision class name. Classes not listed here
# are unmapped and dropped by `map_class()` (return None), rather than
# leaking raw COCO labels (e.g. "airplane", "toothbrush") into a
# system whose fusion/priority logic only knows the Table II vocabulary.
_COCO_TO_BLINDVISION = {
    "person": "person",
    "bicycle": "bicycle",
    "car": "vehicle",
    "motorcycle": "vehicle",
    "bus": "vehicle",
    "truck": "vehicle",
    "chair": "chair",
    "backpack": "backpack",
    "laptop": "laptop",
    "bottle": "bottle",
}

# BlindVision classes with no COCO equivalent -- listed explicitly so
# it's clear this is a known, documented gap rather than an oversight.
UNMAPPED_BLINDVISION_CLASSES = frozenset({"door", "pole", "stairs"})


def map_class(coco_class_name: str) -> Optional[str]:
    """Return the BlindVision class name for a COCO detection, or None
    if this COCO class has no BlindVision equivalent and should be
    dropped from the detection list before it reaches the fusion engine."""
    return _COCO_TO_BLINDVISION.get(coco_class_name)


def is_mapped(coco_class_name: str) -> bool:
    return coco_class_name in _COCO_TO_BLINDVISION


def mapped_classes() -> frozenset:
    """The set of BlindVision class names reachable from COCO without
    fine-tuning."""
    return frozenset(_COCO_TO_BLINDVISION.values())
