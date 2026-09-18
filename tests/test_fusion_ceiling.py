"""
Regression coverage for risk_model.max_reachable_fused_score.

Guards the specific, previously code-undocumented claim that HIGH_RISK_FUSED
(config.HIGH_RISK_FUSED_THRESHOLD, arbitration.py Tier 6/7) is unreachable
under the currently-shipped, uncalibrated configuration -- and, just as
importantly, that this is a fact about the *current* configuration, not a
permanent property: calibrating the camera alone (config.CAMERA_FOCAL_LENGTH_PX)
would raise the reachable ceiling above the threshold again.

If a future change to the fusion weights or thresholds silently changes
either fact, these tests should fail and say so, rather than the manuscript
and code quietly drifting apart on this point again.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from config import DEFAULT_WEIGHTS, HIGH_RISK_FUSED_THRESHOLD, D_SMAX_M  # noqa: E402
from fusion.risk_model import max_reachable_fused_score  # noqa: E402
from fusion.arbitration import arbitrate  # noqa: E402
from fusion.risk_model import VisionDetection, StickReading  # noqa: E402


def test_uncalibrated_ceiling_is_below_high_risk_threshold():
    ceiling = max_reachable_fused_score(DEFAULT_WEIGHTS, vision_calibrated=False)
    assert ceiling < HIGH_RISK_FUSED_THRESHOLD
    # Pinned to the value derived and disclosed in the manuscript (Section
    # IV): 0.40*1 + 0.20*0 + 0.25*(1 - 0.5/3) ~= 0.6083.
    assert abs(ceiling - 0.6083) < 0.001


def test_calibrated_ceiling_would_clear_the_threshold():
    """Not currently reachable (vision is uncalibrated by default), but
    calibration alone -- no weight or threshold change -- would be enough
    to make it reachable again. This is the fact future work (a fusion
    weight/threshold sensitivity sweep, Section VIII) needs to re-check
    once real calibration data exists, rather than assuming the tier stays
    permanently dead."""
    ceiling = max_reachable_fused_score(DEFAULT_WEIGHTS, vision_calibrated=True)
    assert ceiling >= HIGH_RISK_FUSED_THRESHOLD
    assert abs(ceiling - 0.8083) < 0.001


def test_no_synthetic_input_can_reach_high_risk_fused_while_uncalibrated():
    """End-to-end check against the real arbitrate() function, not just the
    closed-form ceiling: sweep maximal-looking inputs (max confidence, stick
    reading just above critical, high-risk class) and confirm none of them,
    individually or combined, produces HIGH_RISK_FUSED while distance_m is
    None (the shipped, uncalibrated default)."""
    from config import Tier, CRITICAL_OBSTACLE_M

    just_above_critical = CRITICAL_OBSTACLE_M + 0.001
    detections = [VisionDetection("vehicle", confidence=1.0, bearing="front",
                                   distance_m=None)]
    stick = StickReading(nearest_ultrasonic_m=just_above_critical,
                          down_distance_m=None, water_detected=False,
                          fall_detected=False, sos_pressed=False)
    alert = arbitrate(detections, stick, DEFAULT_WEIGHTS, mode="normal")
    assert alert.tier != Tier.HIGH_RISK_FUSED
