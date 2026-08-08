"""
BlindVision sensor-fusion engine.

Implements, verbatim, the score-level fusion and priority-tier
arbitration described in Section IV of the manuscript ("Sensor Fusion
and Algorithms") and reproduced there as Algorithm 1:

    1: if stick.sos_pressed then return SOS
    2: if stick.down_distance > 0.5 m then return CRITICAL_DROPOFF
    3: if nearest_stick_distance < 0.5 m or
          (vision_class in HIGH_RISK and nearest_vision_distance <= 2.0 m)
       then return CRITICAL_OBSTACLE
    4: if stick.water_detected then return WATER_HAZARD
    5: if stick.fall_detected then return FALL_ALERT
    6: R <- 0.40*C + 0.20*P + 0.25*U + 0.15*W
    7: if R >= 0.8 then return HIGH_RISK_FUSED
    8: if min(nearest_stick_distance, nearest_vision_distance) < 1.2 m
       then return MEDIUM
    9: if min(nearest_stick_distance, nearest_vision_distance) < 2.0 m
       then return LOW
    10: if stick.battery_pct < 20% then return LOW_BATTERY
    11: return ROUTINE

Complexity (Section IV): O(n) per cycle in the number of currently
detected vision objects to build C/P, then O(1) to evaluate the ten
tiers; O(1) memory — only the current frame's readings and the previous
tier decision are retained, no history buffer.

Degraded-mode behavior (Section III/IV): if the stick disconnects,
priority tiers 2-6 are simply unavailable (not defaulted to a false-safe
value); an out-of-calibration sensor term is dropped from the weighted
sum rather than substituted with an assumed value. This is implemented
below by treating missing components as contributing 0 to R and by
skipping stick-only tiers when `stick` is None.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .models import AlertTier, Bearing, FusionResult, StickReading, VisionDetection


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def prox(distance_m: Optional[float], d_max: float) -> float:
    """Linear proximity-normalization function shared by both subsystems.

    prox(d, D_max) = clip(1 - d/D_max, 0, 1)
    A missing/None distance contributes zero proximity risk (degraded mode).
    """
    if distance_m is None:
        return 0.0
    return clip(1.0 - (distance_m / d_max))


@dataclass(frozen=True)
class FusionWeights:
    w_vc: float = 0.40
    w_vp: float = 0.20
    w_sp: float = 0.25
    w_sc: float = 0.15


@dataclass(frozen=True)
class FusionThresholds:
    d_vmax_m: float = 8.0
    d_smax_m: float = 3.0
    high_risk_fused_threshold: float = 0.8
    critical_band_m: float = 0.5
    medium_band_m: float = 1.2
    low_band_m: float = 2.0
    dropoff_threshold_m: float = 0.5
    low_battery_pct: float = 20.0
    high_risk_visual_classes: frozenset = frozenset({"person", "vehicle", "bicycle"})


class FusionEngine:
    """Stateless, single-cycle fusion + arbitration engine.

    One call to `evaluate()` corresponds to one fusion cycle (Section
    VI.C reports a 9 ms measured computation time for this step).
    """

    def __init__(
        self,
        weights: FusionWeights = FusionWeights(),
        thresholds: FusionThresholds = FusionThresholds(),
    ) -> None:
        self.weights = weights
        self.thresholds = thresholds

    # -- helpers -----------------------------------------------------

    @staticmethod
    def _nearest_vision(detections: Iterable[VisionDetection]) -> Optional[VisionDetection]:
        detections = list(detections)
        if not detections:
            return None
        return min(detections, key=lambda d: d.distance_m)

    @staticmethod
    def _nearest_stick_distance(stick: Optional[StickReading]) -> Optional[float]:
        if stick is None or not stick.ultrasonic_m:
            return None
        return min(stick.ultrasonic_m.values())

    def _vision_risk(self, nearest: Optional[VisionDetection]) -> float:
        """R_vision = w_vc * c + w_vp * prox(d_vision, D_vmax)."""
        if nearest is None:
            return 0.0
        c_term = self.weights.w_vc * clip(nearest.confidence)
        p_term = self.weights.w_vp * prox(nearest.distance_m, self.thresholds.d_vmax_m)
        return c_term + p_term

    def _stick_risk(self, stick: Optional[StickReading]) -> float:
        """R_stick = w_sp * prox(d_stick, D_smax) + w_sc * flag(d_stick < 0.5 m)."""
        if stick is None:
            return 0.0
        nearest = self._nearest_stick_distance(stick)
        p_term = self.weights.w_sp * prox(nearest, self.thresholds.d_smax_m)
        flag_term = self.weights.w_sc * (
            1.0 if (nearest is not None and nearest < self.thresholds.critical_band_m) else 0.0
        )
        return p_term + flag_term

    # -- main entry point ---------------------------------------------

    def evaluate(
        self,
        vision_detections: List[VisionDetection],
        stick: Optional[StickReading],
    ) -> FusionResult:
        nearest_vision = self._nearest_vision(vision_detections)
        nearest_stick_distance = self._nearest_stick_distance(stick)

        # --- Tier 1: SOS overrides everything -------------------------------
        if stick is not None and stick.sos_pressed:
            return FusionResult(
                tier=AlertTier.SOS,
                risk_score=1.0,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation="SOS pushbutton pressed on Smart Stick.",
            )

        # --- Tier 2: critical drop-off --------------------------------------
        if stick is not None and stick.down_distance_m > self.thresholds.dropoff_threshold_m:
            return FusionResult(
                tier=AlertTier.CRITICAL_DROPOFF,
                risk_score=1.0,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=(
                    f"Downward IR reports no ground return within "
                    f"{self.thresholds.dropoff_threshold_m} m "
                    f"(measured {stick.down_distance_m:.2f} m)."
                ),
            )

        # --- Tier 3: critical obstacle ---------------------------------------
        stick_critical = (
            nearest_stick_distance is not None
            and nearest_stick_distance < self.thresholds.critical_band_m
        )
        vision_critical = (
            nearest_vision is not None
            and nearest_vision.object_class in self.thresholds.high_risk_visual_classes
            and nearest_vision.distance_m <= self.thresholds.low_band_m
        )
        if stick_critical or vision_critical:
            reason = "stick proximity < 0.5 m" if stick_critical else (
                f"high-risk vision class '{nearest_vision.object_class}' within 2.0 m"
            )
            return FusionResult(
                tier=AlertTier.CRITICAL_OBSTACLE,
                risk_score=1.0,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=f"Critical obstacle: {reason}.",
            )

        # --- Tier 4: water hazard --------------------------------------------
        if stick is not None and stick.water_detected:
            return FusionResult(
                tier=AlertTier.WATER_HAZARD,
                risk_score=0.9,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation="Resistive water sensor triggered.",
            )

        # --- Tier 5: fall alert ------------------------------------------------
        if stick is not None and stick.fall_detected:
            return FusionResult(
                tier=AlertTier.FALL_ALERT,
                risk_score=0.9,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation="IMU spike consistent with a fall.",
            )

        # --- Tier 6/7: weighted fused risk score --------------------------
        risk_score = self._vision_risk(nearest_vision) + self._stick_risk(stick)
        if risk_score >= self.thresholds.high_risk_fused_threshold:
            return FusionResult(
                tier=AlertTier.HIGH_RISK_FUSED,
                risk_score=risk_score,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=f"Fused risk score R={risk_score:.2f} >= 0.80.",
            )

        # --- Tier 8/9: distance-band fallback -------------------------------
        candidates = [d for d in (nearest_stick_distance,
                                   nearest_vision.distance_m if nearest_vision else None)
                      if d is not None]
        min_distance = min(candidates) if candidates else None

        if min_distance is not None and min_distance < self.thresholds.medium_band_m:
            return FusionResult(
                tier=AlertTier.MEDIUM,
                risk_score=risk_score,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=f"Nearest reading {min_distance:.2f} m < 1.2 m.",
            )
        if min_distance is not None and min_distance < self.thresholds.low_band_m:
            return FusionResult(
                tier=AlertTier.LOW,
                risk_score=risk_score,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=f"Nearest reading {min_distance:.2f} m < 2.0 m.",
            )

        # --- Tier 10: low battery ---------------------------------------------
        if stick is not None and stick.battery_pct < self.thresholds.low_battery_pct:
            return FusionResult(
                tier=AlertTier.LOW_BATTERY,
                risk_score=risk_score,
                nearest_vision=nearest_vision,
                nearest_stick_distance_m=nearest_stick_distance,
                explanation=f"Stick battery {stick.battery_pct:.0f}% < 20%.",
            )

        # --- Tier 11: routine ---------------------------------------------------
        return FusionResult(
            tier=AlertTier.ROUTINE,
            risk_score=risk_score,
            nearest_vision=nearest_vision,
            nearest_stick_distance_m=nearest_stick_distance,
            explanation="No hazard tier matched.",
        )


def load_engine_from_config(config: dict) -> FusionEngine:
    """Build a FusionEngine from the parsed contents of fusion_config.yaml."""
    f = config["fusion"]
    weights = FusionWeights(**f["weights"])
    thresholds = FusionThresholds(
        d_vmax_m=f["normalization"]["D_vmax_m"],
        d_smax_m=f["normalization"]["D_smax_m"],
        high_risk_fused_threshold=f["high_risk_fused_threshold"],
        critical_band_m=config["distance_bands_m"]["critical"],
        medium_band_m=config["distance_bands_m"]["medium"],
        low_band_m=config["distance_bands_m"]["low"],
        dropoff_threshold_m=config["dropoff_threshold_m"],
        low_battery_pct=config["low_battery_pct"],
        high_risk_visual_classes=frozenset(config["high_risk_visual_classes"]),
    )
    return FusionEngine(weights=weights, thresholds=thresholds)
