import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from calibrate_ir_sensor import fit_power_law  # noqa: E402


def test_fit_recovers_known_power_law():
    A_true, B_true = 27.86, -1.15
    samples = []
    for dist_cm in (5, 10, 15, 20, 25, 30, 40, 50):
        voltage = (dist_cm / A_true) ** (1.0 / B_true)
        samples.append((voltage, dist_cm))

    A_fit, B_fit, r_squared = fit_power_law(samples)

    assert abs(A_fit - A_true) < 0.1
    assert abs(B_fit - B_true) < 0.01
    assert r_squared > 0.999
