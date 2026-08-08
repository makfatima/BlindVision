# Calibration

Two distance estimates in this codebase depend on your physical
hardware and **must be calibrated per-rig, not trusted as shipped**:
the vision bounding-box-height-to-distance conversion, and the Smart
Stick's downward IR (drop-off) sensor curve. Both ship with a
documented placeholder so the system runs out of the box, and both
have a tool to replace that placeholder with a real fit from your own
measurements.

## 1. Vision distance (bbox-height-ratio → meters)

**Model:** `distance_m = k / bbox_height_ratio` — implemented in
`goggles/vision/distance_calibration.py`, loaded automatically by
`goggles/vision/camera_worker.py`.

**Shipped default:** `goggles/vision/calibration/vision_calibration.json`,
seeded from a pinhole-camera-model estimate (1080p sensor, ~90° vertical
FOV, 1.7 m reference person) — clearly labeled as a placeholder in the
`reference_object` field. It is internally consistent (R²=1.0 against
its own synthetic samples) but has not been checked against a real
camera.

**Calibrate for real:**

```bash
python tools/calibrate_vision_distance.py live --camera-index 0
```

Stand (or place a fixed-height object) at several known distances from
the camera, entering each distance when prompted; the tool detects the
target class, records the bounding-box height ratio, and fits a new
`k` by least squares once you type `done`. Aim for at least 5–6 points
spread across your expected detection range (Section IV: `D_vmax = 8m`),
not clustered close together — R² is printed so you can tell if the
fit is trustworthy (it warns below 0.9).

No camera handy yet? Seed a documented placeholder manually:

```bash
python tools/calibrate_vision_distance.py manual \
    --reference-object "adult, 1.7m, my rig's actual FOV" \
    --sample 1.0:0.85 --sample 2.0:0.43 --sample 4.0:0.21
```

Each `--sample` is `distance_m:bbox_height_ratio`.

**Do this once per camera model/mounting** — the four cameras in
Section III share a model, so one calibration run should apply to all
four as long as they're the same hardware at the same approximate
mounting height.

## 2. Smart Stick downward IR sensor (drop-off detection)

**Model:** `distance_cm = A * V^B` (Sharp GP2Y0A21YK0F-style analog IR
curve) — implemented in `stick/src/sensors.cpp::read_ir_down_m()`.

**Shipped default:** `A=27.86, B=-1.15`, the commonly cited datasheet
fit for this sensor family. Treat this as a starting point — individual
sensor units vary, and the fit is sensitive to the exact ADC reference
voltage and resistor network on your board.

**Calibrate for real:**

1. Flash `stick/src/selftest/selftest_main.cpp` (`pio run -e
   esp32dev_selftest -t upload -t monitor`) or a throwaway sketch that
   prints `analogRead(IR_DOWN_1_PIN)`.
2. Hold the sensor at several known distances from a flat surface
   (e.g. 5, 10, 15, 20, 25, 30 cm — within the sensor's rated range)
   and record the raw ADC value at each.
3. Write a CSV: `adc_raw,distance_cm` — one pair per line.
4. Fit:

   ```bash
   python tools/calibrate_ir_sensor.py samples.csv
   ```

5. Paste the printed `IR_CALIB_A` / `IR_CALIB_B` constants into
   `stick/src/sensors.cpp` and re-flash.

The fitting tool is unit-tested against synthetic data with known
constants (`goggles/tests/test_ir_calibration_tool.py`) to confirm the
log-log regression itself is correct; what it can't verify for you is
that your physical measurements are accurate — measure carefully, and
re-check R² after fitting.

## 3. Ultrasonic sensors (front/left/right/rear/down)

The five HC-SR04-style ultrasonic sensors (`stick/src/sensors.cpp::read_ultrasonic_m`)
use the standard speed-of-sound round-trip formula and don't need a
curve fit the way IR does — but do verify each one is wired to the
right `trig`/`echo` pins in `stick/include/pins.h` using the
self-test firmware below, since a swapped trig/echo pair, not a bad
formula, is the most common wiring mistake here.

## 4. Verifying pin wiring generally

`stick/src/selftest/selftest_main.cpp` exercises every sensor input
and output pin defined in `stick/include/pins.h`, once per second,
with plain-text Serial output — see `docs/hardware_bringup.md` for how
to run it and what to look for. Run this **before** flashing the main
firmware on any new or rewired board.
