"""Finding 8: a populated focal length alone must not activate vision
distance; per-camera values must be used per bearing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))
import config
from camera import detector


def _est(bearing):
    return detector.YoloDetector._estimate_distance_m("person", 170.0, bearing)


def test_focal_set_but_not_validated_gives_none(monkeypatch):
    monkeypatch.setattr(config, "CAMERA_FOCAL_LENGTH_PX", 1000.0)
    monkeypatch.setattr(config, "VISION_DISTANCE_VALIDATED", False)
    assert _est("front") is None


def test_per_bearing_focal_used_when_validated(monkeypatch):
    monkeypatch.setattr(config, "CAMERA_FOCAL_LENGTH_PX", None)
    monkeypatch.setattr(config, "CAMERA_FOCAL_LENGTH_PX_BY_BEARING",
                        {"front": 1000.0, "right": 500.0, "rear": None, "left": None})
    monkeypatch.setattr(config, "VISION_DISTANCE_VALIDATED", True)
    assert abs(_est("front") - 10.0) < 1e-9   # 1.7 m * 1000 px / 170 px
    assert abs(_est("right") - 5.0) < 1e-9
    assert _est("rear") is None


def test_released_default_is_disabled():
    assert config.VISION_DISTANCE_VALIDATED is False
    assert all(v is None for v in config.CAMERA_FOCAL_LENGTH_PX_BY_BEARING.values())
