"""
Integration test for the vision pipeline: runs the actual bundled
COCO-pretrained checkpoint (not a mock) against a real image and
checks that goggles/vision/coco_mapping.py produces class names the
fusion engine understands.

Skipped automatically if ultralytics/torch aren't installed (e.g. a
minimal CI runner that only exercises the fusion engine) or if the
bundled checkpoint is missing.
"""

from pathlib import Path

import pytest

from goggles.vision.coco_mapping import map_class, mapped_classes
from goggles.fusion.fusion_engine import FusionThresholds

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = REPO_ROOT / "training" / "models" / "yolov8n_coco_pretrained.pt"

ultralytics = pytest.importorskip("ultralytics", reason="ultralytics not installed")


@pytest.fixture(scope="module")
def sample_image_path() -> str:
    from ultralytics.utils import ASSETS
    return str(ASSETS / "bus.jpg")  # ships with ultralytics; contains people + a bus


@pytest.mark.skipif(not CHECKPOINT.exists(), reason="bundled checkpoint not present")
def test_bundled_checkpoint_detects_and_maps_person_and_vehicle(sample_image_path):
    from ultralytics import YOLO

    model = YOLO(str(CHECKPOINT))
    results = model.predict(sample_image_path, conf=0.45, verbose=False)

    mapped_names = set()
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            raw_name = model.names[cls_id]
            mapped = map_class(raw_name)
            if mapped is not None:
                mapped_names.add(mapped)

    # The sample image contains people and a bus; both should map onto
    # BlindVision classes the fusion engine's high-risk-class check uses.
    assert "person" in mapped_names
    assert "vehicle" in mapped_names


def test_mapped_classes_are_a_subset_of_fusion_high_risk_plus_others():
    thresholds = FusionThresholds()
    # Every high-risk class the fusion engine escalates on must be
    # reachable from the bundled checkpoint without any fine-tuning.
    assert thresholds.high_risk_visual_classes.issubset(mapped_classes())
