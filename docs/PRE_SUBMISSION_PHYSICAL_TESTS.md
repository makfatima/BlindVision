# BlindVision: Pre-Submission Physical Tests

This document defines the three physical validation tests to be completed before submission. These tests supplement the existing seven-protocol `docs/PHYSICAL_TEST_PROTOCOLS.md` and validate the specific hardware/software paths addressed during the pre-submission audit.

**Protocol freeze rule:** This test matrix is fixed before data collection. Do not change the conditions after seeing results, discard failed trials, or selectively repeat unfavorable trials. Preserve all raw measurements and report exact outcomes.

---

# Test 1: Five-Transducer Ultrasonic Characterization, Downward Sensing, and Cross-Talk

## Objective

Characterize the complete five-transducer Smart Stick array and evaluate measurement accuracy, variation, close-range behavior, downward drop-off sensing, and interference caused by concurrent transducer operation.

## 1.1 Directional Sensor Array

**Sensors:** Front, Left, Right, Rear.

**Target materials:**
- Drywall / painted wall
- Raw wood
- Heavy fabric

**Normal-incidence conditions (0°):**
- 30 cm (inside the 0–0.5 m Critical band)
- 50 cm
- 100 cm
- 150 cm
- 200 cm
- 250 cm

**Off-axis conditions:**
- −30° at 50, 150, and 250 cm
- +30° at 50, 150, and 250 cm

This gives **12 conditions per sensor/material combination**:

6 normal-incidence conditions + 3 negative-angle conditions + 3 positive-angle conditions = 12.

**Sample count:**

4 sensors × 3 materials × 12 conditions × 10 readings = **1,440 readings**.

## 1.2 Downward Sensor Surface and Drop-Off Characterization

The downward transducer is evaluated against the ground rather than a vertical wall.

**Floor surfaces:**
- Tile
- Carpet
- Concrete

**Sensor-to-ground reference heights:**
- 30 cm
- 50 cm
- 100 cm

**Edge states:**
- Flat floor
- Drop-off ledge: the sensor positioned over a 15 cm step-down (fixed before data collection)

Each combination receives 10 readings.

**Sample count:**

3 surfaces × 3 reference heights × 2 edge states × 10 readings = **180 readings**.

For every reading, also record whether the firmware raised its drop-off flag; this is the behaviour the drop-off test is meant to validate. For the drop-off condition, independently record the actual vertical drop/ground geometry. The 30/50/100 cm values refer to the predefined sensor-to-ground reference height, not the depth of the drop.

## 1.3 Cross-Talk Interference Test

The cross-talk experiment compares the Front sensor under isolated operation with the same measurement while all five transducers operate concurrently.

**Firing modes:**
1. Solo firing: the Front sensor is active while the other transducers are inactive. The released firmware has no single-sensor mode (it always fires all five in sequence), so disconnect the trigger wires of the Left, Right, Rear and Downward sensors for this mode and note this in the log.
2. Concurrent firing: all five transducers are active.

**Distances:**
- 50 cm
- 150 cm
- 250 cm

**Target materials:**
- Drywall / painted wall
- Raw wood
- Heavy fabric

Record 10 readings per mode/distance/material condition.

**Sample count:**

2 modes × 3 distances × 3 materials × 10 readings = **180 readings**.

## 1.4 Total Ultrasonic Sample Count

| Component | Readings |
|---|---:|
| Directional Front/Left/Right/Rear characterization | 1,440 |
| Downward surface/drop-off characterization | 180 |
| Cross-talk interference | 180 |
| **Total** | **1,800** |

The arithmetic is therefore:

**1,440 + 180 + 180 = 1,800 readings.**

## 1.5 Ground Truth

For directional target positions, use an independent laser distance meter.

For downward measurements, independently document the sensor-to-ground reference height and, for drop-off trials, the actual vertical drop geometry.

## 1.6 Required Metrics

For each applicable sensor/test condition report:

- **Bias:** mean(measured distance − ground-truth distance)
- **MAE:** mean(|measured distance − ground-truth distance|)
- **RMSE:** sqrt(mean((measured distance − ground-truth distance)²))
- **Standard deviation (SD)** of measurement error
- **Worst Error:** max(|measured distance − ground-truth distance|)
- **No-echo count and rate:** readings with no valid distance (timeout / 0xFFFF); recorded as no-echo, never estimated, and excluded from the error metrics above
- **Outlier rate:** percentage of valid readings with |measured − ground truth| > 10 cm (rule fixed here, before data collection)
- **Drop-off detection (downward sensor):** flag raised / total, separately for flat-floor and drop-off trials

For cross-talk, additionally report the change in error between solo and concurrent operation.

## 1.7 Procedure

1. Mount the Smart Stick rigidly at a fixed height of 90 cm for the directional and cross-talk tests, and record it.
2. Position each target at the specified distance and angle.
3. Verify target position using the independent ground-truth measurement.
4. Collect exactly 10 readings for each predefined condition.
5. Complete the directional matrix for all four sensors and three materials.
6. Complete the downward matrix using the three surfaces, three reference heights, and two edge states.
7. Complete the cross-talk matrix using Front-solo and all-five concurrent operation.
8. Preserve every raw reading, including no-echo and anomalous readings.
9. Compute the statistical metrics only after all planned measurements are complete.

---

# Test 2: Vision-Only Physical Fault-Injection Test

## Objective

Validate the physical Vision-Only fallback path when the Smart Stick is unavailable and `VISION_DISTANCE_VALIDATED = False`.

This test validates semantic camera-direction warnings without claiming validated monocular distance estimation.

## Configuration

- Power off or disconnect the Smart Stick.
- Start the Vision Node with:
  ```python
  VISION_DISTANCE_VALIDATED = False
  ```
- Wait **more than 5 seconds** after disconnecting the Smart Stick so that Vision-Only mode is active.
- Use stationary recognizable people/objects for the primary trials.
- Before each block of trials, confirm from the goggles log that the mode is `vision_only`.
- A detection below the 0.60 confidence threshold produces no warning by design; record it as "no warning" together with the logged confidence.
- Do not use door, pole, or stairs as primary test classes because the current detector configuration does not reliably support those classes for this validation.

## Trial Matrix

Run **exactly 20 trials per camera channel**, for **80 total trials**.

| Camera | Stationary Test Setup | Expected Semantic Warning |
|---|---|---|
| Front | Recognizable person/object in front-camera field | Person detected front — distance unknown, proceed with caution |
| Left | Recognizable person/object in left-camera field | Person detected left — distance unknown, proceed with caution |
| Right | Recognizable person/object in right-camera field | Person detected right — distance unknown, proceed with caution |
| Rear | Recognizable person/object in rear-camera field | Person detected rear — distance unknown, proceed with caution |

Record the actual runtime warning text rather than altering it to match the expected wording.

## Procedure

1. Power off/disconnect the Smart Stick.
2. Launch the Vision Node with `VISION_DISTANCE_VALIDATED = False`.
3. Wait more than 5 seconds.
4. Present the stationary test object/person in the selected camera's field.
5. Record detected class, confidence, camera direction, warning text, latency, and outcome. Latency is measured from object placement to speech onset, read from a phone video that captures both.
6. Complete exactly 20 trials for each camera.
7. Preserve all failures and anomalies.
8. Do not selectively repeat failed trials.

## Report

For each camera report:
- Successful warnings / 20
- Detected class
- Direction correctness
- Warning latency
- Failure count and observed failure mode where identifiable

---

# Test 3: Camera-Triggered Haptic Actuation and Speech Pre-Emption

## Objective

Validate the **goggles-to-stick Bluetooth haptic path** and emergency speech pre-emption behavior.

The normal haptic test must use an obstacle visible to a camera but outside the Smart Stick's ultrasonic sensing path. This prevents the Smart Stick's local sensor logic from independently triggering the haptic motor and bypassing the software path under test.

## Timing Method

Do **not** compare software timestamps from the Smart Stick and goggles because the two devices do not have a synchronized clock.

Instead, record the Smart Stick motor and the goggles' speaker simultaneously in **one phone slow-motion video**. Determine physical event ordering from the unified optical recording.

The speech source is the goggles/vision device, not the Smart Stick.

## Part A: Camera-Triggered Haptic-Before-Speech Ordering

**Trials: N = 15.**

1. Position a stationary recognizable obstacle/person so that a selected camera can detect it.
2. Ensure it is outside the Smart Stick's ultrasonic sensing path.
3. Trigger the camera-based warning.
4. Record the Smart Stick motor and goggles speaker simultaneously using one slow-motion phone video.
5. Determine whether visible haptic actuation occurs before the corresponding speech begins.
6. Read from the video the time of first visible motor movement (t_motor) and first audible speech (t_speech); record t_speech − t_motor.
7. Record success/failure and retain the video evidence.

**Success condition:** the camera warning causes the Smart Stick to actuate its haptic motor, and the haptic actuation is observed before the corresponding speech output.

Report the exact result, such as 15/15, including any failures, plus the mean, median, SD and maximum of t_speech − t_motor, and the goggles-logged decision-to-BLE-write time for reference (same device clock, so this one may be read from software).

## Part B: SOS Speech Pre-Emption

**Trials: N = 15.**

1. Start a longer-duration speech alert on the goggles.
2. Press the Smart Stick SOS button while speech is actively playing.
3. Record the Smart Stick motor and goggles speaker simultaneously using the same slow-motion method.
4. Determine whether ongoing speech is interrupted.
5. Determine whether the SOS haptic pattern activates without waiting for the normal speech alert to finish. Note: the stick also vibrates its SOS pattern locally when its own button is pressed, so SOS vibration alone does not prove the goggles path; the key result for the fixed code is the speech interruption on the goggles.
6. Record every trial outcome.

Report:
- Speech interrupted: N/15
- SOS haptic activated: N/15
- Observed event order
- Button-press-to-speech-stop and button-press-to-SOS-speech times (mean, median, SD, maximum), read from the video
- Trigger-to-haptic latency where measurable from video
- Failed or ambiguous trials

---

# Data Integrity and Reporting Rules

1. Freeze this protocol before collecting data.
2. Complete all pre-specified trials.
3. Do not discard failed trials.
4. Do not repeat trials solely because a result is unfavorable.
5. Preserve raw sensor readings and all relevant logs.
6. Preserve the slow-motion recordings for Test 3.
7. Report exact numerators and denominators.
8. Keep physical measurements separate from software-only unit-test results.
9. Do not claim validated vision distance estimation from Test 2.
10. Update the manuscript only after the raw results have been archived.
11. If a protocol cannot be completed, report it as not completed rather than substituting an easier experiment.
