# BlindVision Physical Validation Protocols
## Release-candidate branch: submission/v92-validation-freeze

This document defines the focused validation required before making any new physical-performance claim for the current release candidate. It does not assert that any test has been completed.

## 1. Camera calibration and vision-distance validation
- Hardware: each of the four deployed USB cameras, Raspberry Pi 4, final mounting geometry.
- Target: printed checkerboard or equivalent calibration target with documented square size.
- Capture: at least 15 usable views per camera spanning center, corners, multiple distances, and tilt angles.
- Fit: intrinsic matrix and distortion coefficients per camera.
- Report: focal length in pixels (fx, fy), principal point, distortion coefficients, RMS reprojection error, image resolution, calibration date, camera identifier.
- Validate distance: place a planar target at at least 5 known distances within the intended operating range; report estimated distance, absolute error, MAE, RMSE, and maximum absolute error.
- Acceptance: calibration quality must be reported numerically; no threshold is assumed by this protocol.
- Record the exact calibration artifact and commit SHA.

## 2. Weighted-fusion reachable-state experiment
- Freeze fusion weights and thresholds before collecting final fusion data.
- Test cases: vision-only; stick-only; concordant vision + stick; conflicting modalities; high-confidence vision with distant stick; low-confidence vision with close stick; and cases intended to cross HIGH_RISK_FUSED.
- For each trial log timestamp, bearing, vision class/confidence/distance, stick distance, W flag, C/P/U/W terms, R, selected tier, and emitted alert.
- Demonstrate at least one reachable HIGH_RISK_FUSED event if the paper retains that contribution.
- Run a one-parameter-at-a-time +/-20% sensitivity analysis around the frozen weights.
- Do not retune weights on the final evaluation trials.

## 3. Vision-Only physical fault injection
- Assemble the final goggles and stick.
- Establish normal operation.
- Interrupt/remove the stick BLE connection for more than 5 s.
- Present camera-detectable obstacles with calibrated and, where relevant, unavailable distance.
- Repeat across all four camera bearings.
- Log expected vs actual alert tier, spoken message, latency, and false-silence events.
- Restore the stick and verify mode recovery.
- Report success/failure counts and all exceptions.

## 4. Goggles-to-stick haptic actuation
- Establish BLE connection using the release-candidate firmware/software.
- Issue each supported remote haptic pattern from the goggles.
- Verify physical motor activation at the stick.
- Repeat each pattern at least 20 times.
- Log command timestamp, write success, stick-side receipt, motor activation, failures, and command-to-actuation latency where instrumentation permits.
- Report per-pattern success rate and latency distribution.
- Do not infer motor actuation from a successful BLE write alone.

## 5. Four-camera throughput benchmark
- Run the current one-model-per-camera-thread implementation.
- Use fixed resolution, model, confidence settings, and camera configuration.
- Perform at least 5 repeated runs of at least 60 s each.
- Record total FPS, per-camera frame counts, dropped frames, CPU utilization, RAM, temperature, errors, and run duration.
- Report mean, standard deviation, minimum, and maximum aggregate FPS.
- Preserve raw run logs and identify the exact commit SHA.

## 6. Five-transducer ultrasonic array characterization
- Test all five ultrasonic channels independently.
- Distances: use a documented grid spanning the claimed operating range.
- Materials: at least three representative target materials.
- Angles: include normal incidence and oblique incidence.
- Repeat measurements at each condition.
- Test simultaneous and near-simultaneous firing for cross-talk.
- Report per-transducer MAE, RMSE, bias, standard deviation, outlier/failure rate, and cross-talk effects.
- Do not generalize a single-transducer MAE to the array.

## 7. Final held-out navigation evaluation
- Freeze all weights, thresholds, firmware, software, and calibration artifacts first.
- Define the evaluation route and pass/fail criteria before testing.
- Record trial/session identifier, configuration, outcome, hazard events, false alerts, missed hazards, and failures.
- Keep participant/session identifiers separate from sensitive participant information.
- Do not use the final evaluation sessions for further tuning.

## Release traceability
Record: Git commit SHA; model/checkpoint identifier; calibration artifact hashes; firmware version; hardware revision; configuration hash; test dates; operator ID; raw-log archive identifier.

A result may be described as a current measured property only when the measurement was obtained using this release candidate or a later explicitly identified release.