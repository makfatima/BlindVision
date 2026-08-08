"""
Tests for the FusionEngine against the ten priority tiers of Algorithm 1
(Section IV of the manuscript), including the worked example given in
the text: an approaching person at 4 m (c=0.8) plus a car at 10 m
(c=0.9), with the stick's forward ultrasound reading 0.4 m -> expected
tier is CRITICAL_OBSTACLE, driven by the stick reading, regardless of
the fused vision-side score.
"""

import pytest

from goggles.fusion.fusion_engine import FusionEngine
from goggles.fusion.models import AlertTier, Bearing, StickReading, VisionDetection


def make_stick(
    front=3.0, left=3.0, right=3.0, rear=3.0, down=0.3,
    water=False, fall=False, sos=False, battery=100.0,
) -> StickReading:
    return StickReading(
        ultrasonic_m={"front": front, "left": left, "right": right, "rear": rear},
        down_distance_m=down,
        water_detected=water,
        fall_detected=fall,
        sos_pressed=sos,
        battery_pct=battery,
        timestamp_ms=0,
    )


@pytest.fixture
def engine() -> FusionEngine:
    return FusionEngine()


def test_sos_overrides_everything(engine):
    stick = make_stick(sos=True, water=True, fall=True, down=1.0)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.SOS


def test_critical_dropoff(engine):
    stick = make_stick(down=0.8)  # > 0.5 m => no ground return => dropoff
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.CRITICAL_DROPOFF


def test_critical_obstacle_from_stick_proximity(engine):
    stick = make_stick(front=0.4)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.CRITICAL_OBSTACLE


def test_critical_obstacle_from_high_risk_vision_class(engine):
    detections = [
        VisionDetection("person", confidence=0.8, distance_m=1.5, bearing=Bearing.FRONT, camera_id="fl")
    ]
    stick = make_stick()  # nothing close on the stick
    result = engine.evaluate(detections, stick)
    assert result.tier == AlertTier.CRITICAL_OBSTACLE


def test_worked_example_stick_wins_over_fused_vision(engine):
    """Section IV worked example: person @ 4m (c=0.8) + car @ 10m (c=0.9),
    stick forward reading 0.4 m => CRITICAL_OBSTACLE from the stick,
    ahead of HIGH_RISK_FUSED / MEDIUM / LOW."""
    detections = [
        VisionDetection("person", confidence=0.8, distance_m=4.0, bearing=Bearing.FRONT, camera_id="fl"),
        VisionDetection("vehicle", confidence=0.9, distance_m=10.0, bearing=Bearing.FRONT, camera_id="fr"),
    ]
    stick = make_stick(front=0.4)
    result = engine.evaluate(detections, stick)
    assert result.tier == AlertTier.CRITICAL_OBSTACLE


def test_vehicle_at_exactly_2m_triggers_critical(engine):
    detections = [
        VisionDetection("vehicle", confidence=0.9, distance_m=2.0, bearing=Bearing.FRONT, camera_id="fr")
    ]
    stick = make_stick()
    result = engine.evaluate(detections, stick)
    assert result.tier == AlertTier.CRITICAL_OBSTACLE


def test_vehicle_beyond_2m_does_not_trigger_critical(engine):
    detections = [
        VisionDetection("vehicle", confidence=0.9, distance_m=2.1, bearing=Bearing.FRONT, camera_id="fr")
    ]
    stick = make_stick()
    result = engine.evaluate(detections, stick)
    assert result.tier != AlertTier.CRITICAL_OBSTACLE


def test_water_hazard(engine):
    stick = make_stick(water=True)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.WATER_HAZARD


def test_fall_alert(engine):
    stick = make_stick(fall=True)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.FALL_ALERT


def test_high_risk_fused(engine):
    # Push a non-critical-class, non-critical-band vision confidence high
    # enough, combined with moderate stick proximity, to cross R >= 0.8
    # without tripping any earlier tier.
    detections = [
        VisionDetection("chair", confidence=1.0, distance_m=0.0, bearing=Bearing.FRONT, camera_id="fl")
    ]
    stick = make_stick(front=0.6)  # inside medium band, not critical (<0.5m)
    result = engine.evaluate(detections, stick)
    assert result.tier == AlertTier.HIGH_RISK_FUSED
    assert result.risk_score >= 0.8


def test_medium_band(engine):
    stick = make_stick(front=0.9)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.MEDIUM


def test_low_band(engine):
    stick = make_stick(front=1.8)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.LOW


def test_low_battery(engine):
    stick = make_stick(front=2.5, battery=15.0)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.LOW_BATTERY


def test_routine(engine):
    stick = make_stick(front=2.9, battery=90.0)
    result = engine.evaluate([], stick)
    assert result.tier == AlertTier.ROUTINE


def test_degraded_mode_missing_stick(engine):
    """If the stick disconnects, tiers 2-6 are simply unavailable rather
    than defaulted to a false-safe value (Section IV)."""
    detections = [
        VisionDetection("person", confidence=0.5, distance_m=5.0, bearing=Bearing.FRONT, camera_id="fl")
    ]
    result = engine.evaluate(detections, stick=None)
    assert result.tier not in (
        AlertTier.SOS, AlertTier.CRITICAL_DROPOFF, AlertTier.WATER_HAZARD, AlertTier.FALL_ALERT,
    )


def test_no_detections_no_stick_is_routine(engine):
    result = engine.evaluate([], stick=None)
    assert result.tier == AlertTier.ROUTINE
    assert result.risk_score == 0.0
