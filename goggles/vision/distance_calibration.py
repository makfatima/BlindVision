"""
Vision distance estimation: bounding-box-height-to-frame-height ratio
-> approximate distance in meters.

Section III/V.A: the same estimation principle used in the
proof-of-concept ("an estimated relative distance ... from the
bounding-box-height-to-image-height ratio") is carried into the full
system.

The model is `distance_m = k / bbox_height_ratio` (inverse relationship:
an object twice as far away occupies half the frame height, for a
fixed-focal-length camera and roughly constant real-world object
height). `k` is a single calibration constant, in effect
"reference object height, camera-and-lens-normalized". It should be
fit from real measurements of *your* camera rig with `tools/calibrate_vision_distance.py`
rather than assumed - the value below is the fitted result on a
representative reference calibration (see calibration/vision_calibration.json)
and should be re-fit for your own hardware.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("blindvision.vision.calibration")

DEFAULT_CALIBRATION_PATH = Path(__file__).resolve().parent / "calibration" / "vision_calibration.json"

_MIN_DISTANCE_M = 0.2
_MAX_DISTANCE_M = 8.0  # D_vmax, Section IV


@dataclass(frozen=True)
class DistanceCalibration:
    k: float                 # fitted constant: distance_m = k / bbox_height_ratio
    reference_object: str
    fit_r_squared: float
    n_samples: int


def _fit_inverse_model(samples: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Least-squares fit of distance = k / ratio, i.e. a linear fit of
    distance against 1/ratio with zero intercept. Returns (k, r_squared).

    samples: list of (bbox_height_ratio, known_distance_m) pairs.
    """
    if len(samples) < 2:
        raise ValueError("Need at least 2 calibration samples to fit a curve.")

    inv_ratios = [1.0 / ratio for ratio, _ in samples]
    distances = [d for _, d in samples]

    # Zero-intercept least squares: k = sum(x*y) / sum(x*x)
    sum_xy = sum(x * y for x, y in zip(inv_ratios, distances))
    sum_xx = sum(x * x for x in inv_ratios)
    k = sum_xy / sum_xx if sum_xx > 0 else 1.0

    # R^2 against the fitted line through the origin.
    mean_y = sum(distances) / len(distances)
    ss_tot = sum((y - mean_y) ** 2 for y in distances)
    ss_res = sum((y - k * x) ** 2 for x, y in zip(inv_ratios, distances))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    return k, r_squared


def fit_and_save_calibration(
    samples: List[Tuple[float, float]],
    reference_object: str,
    out_path: Path = DEFAULT_CALIBRATION_PATH,
) -> DistanceCalibration:
    k, r_squared = _fit_inverse_model(samples)
    calib = DistanceCalibration(
        k=k, reference_object=reference_object, fit_r_squared=r_squared, n_samples=len(samples)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "k": calib.k,
        "reference_object": calib.reference_object,
        "fit_r_squared": calib.fit_r_squared,
        "n_samples": calib.n_samples,
        "samples": samples,
    }, indent=2))
    return calib


def load_calibration(path: Path = DEFAULT_CALIBRATION_PATH) -> DistanceCalibration:
    if not path.exists():
        logger.warning(
            "No vision distance calibration found at %s; using an uncalibrated "
            "default (k=1.0, i.e. distance_m = 1/ratio). Run "
            "tools/calibrate_vision_distance.py against your own camera rig "
            "before trusting distance-based alert tiers.",
            path,
        )
        return DistanceCalibration(k=1.0, reference_object="uncalibrated_default", fit_r_squared=0.0, n_samples=0)

    data = json.loads(path.read_text())
    return DistanceCalibration(
        k=data["k"],
        reference_object=data["reference_object"],
        fit_r_squared=data["fit_r_squared"],
        n_samples=data["n_samples"],
    )


class DistanceEstimator:
    """Wraps a fitted DistanceCalibration for use by CameraWorker."""

    def __init__(self, calibration: Optional[DistanceCalibration] = None) -> None:
        self.calibration = calibration or load_calibration()

    def estimate_m(self, bbox_height_ratio: float) -> float:
        if bbox_height_ratio <= 0:
            return _MAX_DISTANCE_M
        d = self.calibration.k / bbox_height_ratio
        return max(_MIN_DISTANCE_M, min(_MAX_DISTANCE_M, d))
