import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from config import DEFAULT_WEIGHTS, D_VMAX_M, D_SMAX_M
from fusion.risk_model import prox, vision_risk, stick_risk, fused_risk, VisionDetection, StickReading


def test_prox_bounds():
    assert prox(None, 8.0) == 0.0
    assert prox(0.0, 8.0) == 1.0
    assert prox(8.0, 8.0) == 0.0
    assert prox(100.0, 8.0) == 0.0  # clipped, not negative


def test_prox_linear():
    assert abs(prox(4.0, 8.0) - 0.5) < 1e-9


def test_weights_ordering_holds():
    assert DEFAULT_WEIGHTS.validate_ordering()


def test_vision_risk_none_is_zero():
    assert vision_risk(None, DEFAULT_WEIGHTS) == 0.0


def test_stick_risk_none_is_zero():
    assert stick_risk(None, DEFAULT_WEIGHTS) == 0.0


def test_fused_risk_matches_worked_formula():
    # A confidently classified, close object: c=0.9, d_vision=1.0m (D_vmax=8)
    detection = VisionDetection("person", confidence=0.9, bearing="front", distance_m=1.0)
    # Stick reading well outside critical band: d_stick=2.5m (D_smax=3)
    stick = StickReading(nearest_ultrasonic_m=2.5, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)

    p_vision = prox(1.0, D_VMAX_M)
    p_stick = prox(2.5, D_SMAX_M)
    expected = (DEFAULT_WEIGHTS.w_vc * 0.9 + DEFAULT_WEIGHTS.w_vp * p_vision
                + DEFAULT_WEIGHTS.w_sp * p_stick + DEFAULT_WEIGHTS.w_sc * 0.0)

    r = fused_risk(detection, stick, DEFAULT_WEIGHTS)
    assert abs(r - expected) < 1e-9


def test_tier7_upper_bound_matches_paper():
    """Paper: 'the stick proximity term is capped at prox(0.5m, 3m) = 0.833,
    bounding R at 0.40 + 0.20 + 0.25(0.833) = 0.808 against the 0.80
    threshold.' Reproduce that bound here."""
    detection = VisionDetection("person", confidence=1.0, bearing="front", distance_m=0.0)
    stick = StickReading(nearest_ultrasonic_m=0.5, down_distance_m=None,
                          water_detected=False, fall_detected=False, sos_pressed=False)
    r = fused_risk(detection, stick, DEFAULT_WEIGHTS)
    assert abs(r - 0.808) < 0.001
    assert r >= 0.8  # crosses the HIGH_RISK_FUSED threshold at the extreme
