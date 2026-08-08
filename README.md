# BlindVision

A dual-device sensor-fusion platform for assistive navigation for
blind and visually impaired (BVI) users, pairing a vision-equipped
**Smart Goggles** head-worn unit with a ground-sensing **Smart Stick**
cane. Vision-based object detection is fused with near-field hazard
sensing so that ground-level safety does not depend on AI availability
or connectivity.



> [github.com/makfatima/BlindVision](https://github.com/makfatima/BlindVision) —


## Why two devices

- **Smart Goggles** (Raspberry Pi 4B + 4 cameras + on-device YOLOv8):
  long-range vision and global awareness — people, vehicles, signage —
  across ~360° with ~30° camera overlap.
- **Smart Stick** (ESP32 + ultrasonic/IR/water/IMU/force sensors + SOS
  button): near-field ground hazards — steps, curbs, pits, water —
  sensed independently, so the cane keeps working even if the goggles
  fail, lose power, or disconnect.
- A **fusion engine** on the goggles merges both streams into a single
  risk score and a strict priority-tier alert order (Algorithm 1),
  delivered via audio (earbud) and haptics (stick vibration motor).
- A **caregiver layer** relays only anonymized event metadata over
  GPS/cellular — no raw images or audio ever leave the goggles.

See [`docs/architecture.md`](docs/architecture.md) for the full system
diagram and [`docs/fusion_algorithm.md`](docs/fusion_algorithm.md) for
the fusion math and priority arbitration.

## Repository layout

```
BlindVision/
├── config/fusion_config.yaml   # tuned weights, thresholds, pin/sensor layout
├── goggles/                    # Raspberry Pi software (Python)
│   ├── vision/                 # 4x concurrent YOLOv8 camera workers
│   ├── ble/                    # stick packet codec + BLE client
│   ├── fusion/                 # Algorithm 1 engine + alert messages
│   ├── audio/                  # offline-preferred TTS
│   ├── caregiver/              # anonymized event relay (TLS 1.2)
│   ├── main.py                 # process entry point
│   └── tests/
├── stick/                      # ESP32 firmware (PlatformIO)
│   ├── include/                # packet.h, pins.h, sensors.h, ble_server.h
│   └── src/                    # main.cpp, sensors.cpp, ble_server.cpp
├── poc/                        # Section V.A proof-of-concept
│   ├── server/                 # FastAPI + cloud YOLOv8n detection API
│   └── firmware/               # ESP32-CAM Arduino client
├── backend/                    # caregiver backend service (reference impl)
├── training/                   # fine-tuning pipeline + bundled COCO checkpoint
│   ├── models/                 # yolov8n_coco_pretrained.pt (sha256-verified)
│   └── scripts/                # train.py, evaluate.py
├── tools/                      # calibration utilities
│   ├── calibrate_vision_distance.py
│   └── calibrate_ir_sensor.py
└── docs/
    ├── architecture.md
    ├── fusion_algorithm.md
    ├── ble_protocol.md
    ├── calibration.md
    └── hardware_bringup.md
```

## Quick start

### 1. Fusion engine + full test suite (no hardware required)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r goggles/requirements.txt -r backend/requirements.txt

PYTHONPATH=. pytest goggles/tests backend/tests -v
```

This runs the fusion engine, BLE packet codec, and backend service
tests entirely on your machine — no Raspberry Pi, ESP32, or cameras
needed. It's the fastest way to confirm the algorithm behaves as
Section IV describes (including the paper's own worked example).

### 2. Proof-of-concept cloud detection API

```bash
cd poc
pip install -r requirements.txt
uvicorn server.app:app --reload
# or: docker compose up --build
```

POST a JPEG to `http://localhost:8000/detect` to get back sorted,
priority-classified detections, matching Section V.A.

### 3. Smart Stick firmware

```bash
cd stick
pio run -e esp32dev          # build
pio run -e esp32dev -t upload  # flash to an ESP32 DevKit V1
```

Update `stick/include/pins.h` to match your physical wiring before
flashing — the pin numbers there are a reference assignment.

### 4. Smart Goggles (Raspberry Pi)

```bash
cd goggles
pip install -r requirements.txt
python -m goggles.main --config ../config/fusion_config.yaml
```

Requires four USB cameras, Bluetooth enabled, and a paired Smart
Stick advertising as `BlindVision-Stick`.

### 5. Caregiver backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Design notes carried over from the manuscript

- **Score-level, not decision-level, fusion.** Each modality produces
  a normalized confidence/proximity value; the fusion engine combines
  those scores (Section IV), rather than merging independent go/no-go
  alerts from each subsystem.
- **Fails safe, not silent.** If the BLE link drops for more than 5 s,
  the goggles fall back to Vision-Only Mode rather than assuming a
  safe ground state; if the goggles lose power, the stick keeps
  vibrating on its own local thresholds (Offline Stick Mode).
- **Privacy by design.** The wire formats and backend schema in this
  repo have no field for raw images or audio — only typed event
  metadata (object type, direction, distance, hazard flag, timestamp,
  device state, source sensor, location where available).
- **Weights are a starting point, not a proven optimum.** The tuned
  weights in `config/fusion_config.yaml` come from manual bench
  calibration across staged scenarios (Section IV), not an automated
  search. A sensitivity sweep against your own navigation protocol is
  recommended before relying on them in the field.

## Detection model: works out of the box, trainable for the full class set

`training/models/yolov8n_coco_pretrained.pt` is the official
Ultralytics COCO-pretrained YOLOv8n checkpoint (sha256-verified — see
`training/models/README.md`). `goggles/vision/coco_mapping.py` maps
six of the manuscript's ten object classes directly from COCO
(`person`, `bicycle`, `vehicle` ← car/truck/bus/motorcycle, `chair`,
`backpack`, `laptop`, `bottle`) — including all three
`high_risk_visual_classes` the fusion engine escalates on — so the
goggles software produces real, correctly-classified detections today,
with no training required
(`goggles/tests/test_vision_integration.py` proves this against a real
image, not a mock). `door`, `pole`, and `stairs` have no COCO
equivalent; `training/` contains a full fine-tuning pipeline
(`training/README.md`) to add them once you have labeled data — the
manuscript's own dataset isn't public yet (Section V.D).

## Calibration

Two distance estimates are hardware-dependent and ship with a
documented placeholder rather than a blind guess:

- **Vision distance** (bbox-height → meters): seeded from a
  pinhole-camera-model estimate, replaceable with a real fit from your
  own camera via `tools/calibrate_vision_distance.py` (interactive,
  live-camera mode with least-squares curve fitting and an R² sanity
  check).
- **Stick IR sensor** (drop-off detection): seeded from the Sharp
  GP2Y0A21YK0F datasheet curve, replaceable with a real fit from your
  own sensor unit via `tools/calibrate_ir_sensor.py` (log-log
  regression from a CSV of ADC-reading/known-distance pairs).

See `docs/calibration.md` for the full walkthrough. Both fitting
routines are unit-tested against synthetic data with known ground
truth to confirm the math itself is correct.

## Verifying stick wiring before you trust it

`stick/include/pins.h` is a reference pin assignment, not something
verified against physical hardware in this environment. `pio run -e
esp32dev_selftest -t upload -t monitor` flashes a self-test firmware
that exercises every sensor and output pin with live Serial feedback
and flags implausible readings (stuck-at-zero, always-out-of-range) as
likely wiring faults — run this on any new or rewired board *before*
flashing the main firmware. Walkthrough: `docs/hardware_bringup.md`.

## Status / what's not (yet) in this repo

Faithful to the manuscript's own **Reproducibility Resources** (Section
V.D) and **Data Availability** statement: the authors' own trained
10-class YOLOv8 weights, epoch-wise training logs, full confusion
matrix, and raw timestamped latency/power/trial logs are not public
yet. What this repo adds beyond that baseline: a real, sha256-verified
pretrained detector that already works for the high-risk classes
(above), a full fine-tuning pipeline for the rest, calibration tooling
for both hardware-dependent distance curves, and a hardware self-test
firmware for pin verification — so the remaining gap is genuinely just
"bring your own labeled dataset and your own physical board," not
missing tooling.

**This is a navigation-assistance aid, not a certified safety device.**
It has not been independently validated beyond the trials reported in
the source manuscript (predominantly sighted testers, seven BVI
participants across a subset of trials) and should not be relied upon
as a sole means of hazard avoidance.

## License

MIT — see [`LICENSE`](LICENSE). (The manuscript does not specify a
license for the authors' own release; MIT is chosen here as a
permissive default for this independent reference implementation.)

## Citation

If you build on this work, please cite the source manuscript:

```bibtex
@article{blindvision2026,
  title   = {BlindVision: A Dual-Device Sensor-Fusion System for
             Assistive Navigation --- Implementation and Experimental
             Validation},
  note    = {Author list and venue to be inserted; code availability:
             https://github.com/makfatima/BlindVision},
  year    = {2026}
}
```
