import json
import tempfile
from pathlib import Path

from goggles.vision.distance_calibration import (
    DistanceEstimator,
    fit_and_save_calibration,
    load_calibration,
)


def test_fit_recovers_known_k():
    # Perfect inverse relationship with k=2.0: ratio = 2.0/distance
    samples = [(2.0 / d, d) for d in (1.0, 2.0, 4.0, 8.0)]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "calib.json"
        calib = fit_and_save_calibration(samples, reference_object="synthetic", out_path=out)
        assert abs(calib.k - 2.0) < 1e-6
        assert calib.fit_r_squared > 0.999
        assert out.exists()


def test_load_calibration_roundtrip():
    samples = [(0.5, 2.0), (0.25, 4.0), (0.125, 8.0)]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "calib.json"
        fit_and_save_calibration(samples, reference_object="test-object", out_path=out)
        loaded = load_calibration(out)
        assert loaded.reference_object == "test-object"
        assert loaded.n_samples == 3


def test_load_calibration_missing_file_returns_default():
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "does_not_exist.json"
        calib = load_calibration(missing)
        assert calib.k == 1.0
        assert calib.n_samples == 0


def test_distance_estimator_uses_fitted_k():
    estimator = DistanceEstimator.__new__(DistanceEstimator)
    from goggles.vision.distance_calibration import DistanceCalibration
    estimator.calibration = DistanceCalibration(k=1.7, reference_object="x", fit_r_squared=1.0, n_samples=5)

    # distance = k / ratio
    assert abs(estimator.estimate_m(0.5) - 3.4) < 1e-6


def test_distance_estimator_clamps_to_valid_range():
    from goggles.vision.distance_calibration import DistanceCalibration
    estimator = DistanceEstimator.__new__(DistanceEstimator)
    estimator.calibration = DistanceCalibration(k=1.0, reference_object="x", fit_r_squared=1.0, n_samples=5)

    assert estimator.estimate_m(0.0001) <= 8.0   # clamped to D_vmax
    assert estimator.estimate_m(100.0) >= 0.2    # clamped to min distance
