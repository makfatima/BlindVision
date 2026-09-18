import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from config import Tier, DEFAULT_WEIGHTS
from fusion.risk_model import VisionDetection, StickReading
from fusion.arbitration import arbitrate


def test_sos_preempts_everything():
    stick = StickReading(nearest_ultrasonic_m=0.1, down_distance_m=0.6,
                          water_detected=True, fall_detected=True, sos_pressed=True)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.SOS
    assert alert.severity == "Emergency"


def test_dropoff_beats_lower_tiers():
    stick = StickReading(nearest_ultrasonic_m=2.0, down_distance_m=0.6,
                          water_detected=True, fall_detected=False, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_DROPOFF


def test_paper_worked_example_person_and_close_stick_reading():
    """Section IV test case: an approaching person 4m ahead (c=0.8)
    and a car 10m ahead (c=0.9); the stick's forward ultrasound reads 0.4m,
    inside the critical band. The test case states this must resolve to
    CRITICAL_OBSTACLE, ahead of the fused HIGH_RISK_FUSED tier the car
    would otherwise trigger once close enough."""
    detections = [
        VisionDetection("person", confidence=0.8, bearing="front", distance_m=4.0),
        VisionDetection("vehicle", confidence=0.9, bearing="front", distance_m=10.0),
    ]
    stick = StickReading(nearest_ultrasonic_m=0.4, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)

    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_OBSTACLE


def test_high_risk_vision_class_within_2m_is_critical_even_without_stick():
    detections = [VisionDetection("vehicle", confidence=0.9, bearing="front", distance_m=1.5)]
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)
    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.CRITICAL_OBSTACLE


def test_water_hazard_tier():
    stick = StickReading(nearest_ultrasonic_m=2.5, down_distance_m=None,
                          water_detected=True, fall_detected=False, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.WATER_HAZARD


def test_fall_alert_tier():
    stick = StickReading(nearest_ultrasonic_m=2.5, down_distance_m=None,
                          water_detected=False, fall_detected=True, sos_pressed=False)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.FALL_ALERT


def test_routine_when_nothing_nearby():
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False,
                          battery_pct=80)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.ROUTINE


def test_low_battery_tier():
    stick = StickReading(nearest_ultrasonic_m=2.9, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False,
                          battery_pct=15)
    alert = arbitrate([], stick, DEFAULT_WEIGHTS)
    assert alert.tier == Tier.LOW_BATTERY


def test_vision_only_mode_ignores_stick_terms():
    """Section III: if the stick disconnects, tiers 2/4/5/10 become
    unavailable and the U/W terms drop from the fused score."""
    detections = [VisionDetection("chair", confidence=0.6, bearing="front", distance_m=1.0)]
    # A stick reading that would otherwise trigger CRITICAL_DROPOFF/WATER
    # must be ignored entirely in vision_only mode.
    stick = StickReading(nearest_ultrasonic_m=0.1, down_distance_m=0.9,
                          water_detected=True, fall_detected=True, sos_pressed=False)
    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS, mode="vision_only")
    assert alert.tier not in (Tier.CRITICAL_DROPOFF, Tier.WATER_HAZARD, Tier.FALL_ALERT)


def test_vision_only_uncalibrated_detection_still_warns():
    """Regression test: with CAMERA_FOCAL_LENGTH_PX unset, VisionDetection
    arrives with distance_m=None, so tiers 3/8/9 cannot fire. Before the
    VISION_WARNING_UNCALIBRATED fallback, this fell through to ROUTINE,
    which main.py's dispatcher never speaks -- i.e. Vision-Only Mode
    produced no alert at all for a camera-detected obstacle. It must not
    silently return to that behaviour."""
    detections = [VisionDetection("person", confidence=0.82, bearing="left",
                                   distance_m=None)]
    alert = arbitrate(detections, stick=None, weights=DEFAULT_WEIGHTS,
                       mode="vision_only")
    assert alert.tier == Tier.VISION_WARNING_UNCALIBRATED
    assert alert.severity == "Caution"
    assert "left" in alert.message
    # No distance figure must be invented in the message.
    assert "m " not in alert.message.split("--")[0]


def test_vision_only_uncalibrated_low_confidence_stays_routine():
    """Below VISION_ONLY_WARNING_CONFIDENCE_MIN, the fallback must not fire
    -- a low-confidence detection with no distance should not out-shout a
    genuinely uncertain read."""
    from config import VISION_ONLY_WARNING_CONFIDENCE_MIN
    detections = [VisionDetection("chair", confidence=VISION_ONLY_WARNING_CONFIDENCE_MIN - 0.05,
                                   bearing="front", distance_m=None)]
    alert = arbitrate(detections, stick=None, weights=DEFAULT_WEIGHTS,
                       mode="vision_only")
    assert alert.tier == Tier.ROUTINE


def test_vision_only_no_detections_stays_routine():
    """No detections at all in Vision-Only Mode is still ROUTINE -- the
    fallback only concerns a real, uncalibrated detection, not an absence
    of detections."""
    alert = arbitrate([], stick=None, weights=DEFAULT_WEIGHTS, mode="vision_only")
    assert alert.tier == Tier.ROUTINE


def test_vision_only_calibrated_distance_takes_priority_over_fallback():
    """Once a distance IS available (calibration done), the existing
    distance-based tiers must still take priority -- the uncalibrated
    fallback must never preempt a calibrated reading."""
    detections = [VisionDetection("chair", confidence=0.9, bearing="front",
                                   distance_m=1.5)]
    alert = arbitrate(detections, stick=None, weights=DEFAULT_WEIGHTS,
                       mode="vision_only")
    assert alert.tier == Tier.LOW
    assert alert.tier != Tier.VISION_WARNING_UNCALIBRATED
