#!/usr/bin/env python3
"""
Calibrate the Smart Stick's downward IR sensor (Section III: aimed
downward, used for edge/stair detection).

The firmware (stick/src/sensors.cpp::read_ir_down_m) fits an analog
Sharp-GP2Y0A21YK0F-style curve: distance_cm = A * V^B, where V is the
sensor's analog output voltage. This tool fits A and B from real
(raw_adc_count, known_distance_cm) samples you collect on your own
board, via log-log linear regression (a standard, well-conditioned way
to fit a power law): log(distance) = log(A) + B*log(V), solved as an
ordinary least-squares line fit in log-log space.

Usage:

    1. Collect samples: place the sensor at several known distances
       from a flat surface (e.g. 5, 10, 15, 20, 25, 30 cm) and read the
       raw ADC value at each, either via the Serial Monitor with a
       throwaway `Serial.println(analogRead(IR_DOWN_1_PIN))` sketch, or
       by extending stick/src/selftest/selftest_main.cpp to print the
       raw pin reading instead of the converted meters value.

    2. Write them to a CSV (adc_raw,distance_cm), one pair per line:

           120,30
           180,20
           260,15
           410,10
           700,5

    3. Fit and print the constants to paste into sensors.cpp:

           python tools/calibrate_ir_sensor.py samples.csv

    4. Update IR_CALIB_A and IR_CALIB_B in stick/src/sensors.cpp with
       the printed values, then re-flash.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import List, Tuple

ADC_MAX_COUNT = 4095.0
ADC_REF_VOLTAGE = 3.3


def load_samples(csv_path: Path) -> List[Tuple[float, float]]:
    """Returns (voltage, distance_cm) pairs."""
    samples = []
    with open(csv_path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].strip().lower().startswith("adc"):
                continue  # skip blank lines / header
            raw_adc = float(row[0])
            distance_cm = float(row[1])
            voltage = (raw_adc / ADC_MAX_COUNT) * ADC_REF_VOLTAGE
            samples.append((voltage, distance_cm))
    return samples


def fit_power_law(samples: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """Fit distance = A * V^B via log-log ordinary least squares.
    Returns (A, B, r_squared)."""
    log_v = [math.log(v) for v, _ in samples]
    log_d = [math.log(d) for _, d in samples]
    n = len(samples)

    mean_x = sum(log_v) / n
    mean_y = sum(log_d) / n

    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_v, log_d))
    ss_xx = sum((x - mean_x) ** 2 for x in log_v)

    B = ss_xy / ss_xx if ss_xx > 0 else 0.0
    log_A = mean_y - B * mean_x
    A = math.exp(log_A)

    # R^2 in log-log space
    fitted = [log_A + B * x for x in log_v]
    ss_res = sum((y - f) ** 2 for y, f in zip(log_d, fitted))
    ss_tot = sum((y - mean_y) ** 2 for y in log_d)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    return A, B, r_squared


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path, help="CSV of adc_raw,distance_cm samples")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"File not found: {args.csv_path}")
        sys.exit(1)

    samples = load_samples(args.csv_path)
    if len(samples) < 3:
        print(f"Only {len(samples)} valid samples found; recommend at least 5-6 "
              "spread across your sensor's working range for a stable fit.")
        if len(samples) < 2:
            sys.exit(1)

    A, B, r_squared = fit_power_law(samples)

    print(f"\nFitted {len(samples)} samples: distance_cm = {A:.4f} * V^{B:.4f}")
    print(f"R^2 (log-log space): {r_squared:.4f}")
    if r_squared < 0.9:
        print("WARNING: R^2 < 0.9 -- check for measurement noise, a sensor near "
              "its min/max range, or reflective/dark surfaces that confuse IR "
              "ranging, before trusting this fit.")

    print("\nPaste into stick/src/sensors.cpp:")
    print(f"    constexpr float IR_CALIB_A = {A:.4f}f;")
    print(f"    constexpr float IR_CALIB_B = {B:.4f}f;")


if __name__ == "__main__":
    main()
