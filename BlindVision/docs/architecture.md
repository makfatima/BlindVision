# System Architecture

BlindVision is a two-node wearable system plus a backend/caregiver layer,
as described in Section III of the manuscript.

```
                 ┌─────────────────────────────┐
                 │      Smart Goggles           │
                 │  (Raspberry Pi 4B, Linux)    │
                 │                              │
  4x USB camera →│  4x YOLOv8 detection threads │
  (1080p,120°FOV)│           │                  │
                 │           ▼                  │
                 │     Fusion Engine            │──TLS 1.2──▶  Backend /
                 │   (Algorithm 1, Section IV)  │              Caregiver
                 │           │                  │              service
                 │  ┌────────┴────────┐         │                  │
                 │  ▼                 ▼         │                  ▼
                 │ TTS (earbud)   Haptic cmd     │           Caregiver app
                 │                    │          │       (map, geofence,
                 └────────────────────┼──────────┘        device health,
                          BLE 5.0     │                    alert timeline)
                                      ▼
                 ┌─────────────────────────────┐
                 │       Smart Stick            │
                 │  (ESP32 DevKit V1)           │
                 │                              │
                 │  Core 0: sensor poll (~15Hz) │
                 │   5x ultrasonic, 2x IR,      │
                 │   water, IMU, FSR, SOS btn   │
                 │  Core 1: BLE + state machine │
                 │                              │
                 │  Outputs: vibration motor,   │
                 │  piezo buzzer, LED           │
                 └─────────────────────────────┘
```

## Smart Goggles (vision node)

- Raspberry Pi 4 Model B (4 GB, quad-core Cortex-A72 @ 1.5 GHz)
- Four wide-angle USB cameras (1080p, 120° FOV) at front-left,
  front-right, rear-left, rear-right (~90° spacing → ~480° summed FOV,
  ~30° overlap, full 360° azimuth coverage)
- On-device YOLOv8n inference, one detection thread/process per camera
  (`goggles/vision/camera_worker.py`, `goggles/vision/detector.py`)
- BLE 5.0 receiver for the stick's packet stream (`goggles/ble/`)
- u-blox NEO-6M GPS + SIM800L GSM/GPRS for caregiver communication
- Bluetooth earbud (primary) + backup speaker/buzzer for spoken alerts
- 10,000 mAh USB power bank (8.1 h idle / 4.8 h active / 3.9 h max load)

## Smart Stick (ground node)

- ESP32 DevKit V1 (dual-core Xtensa LX6 @ 240 MHz)
- 5x ultrasonic (front/left/right/rear + 1 angled downward)
- 2x downward IR (edge/stair detection)
- Resistive water sensor (tip)
- MPU9250 IMU (fall/knock detection)
- FSR at the tip (ground-contact confirmation)
- SOS pushbutton, vibration motor, piezo buzzer, LED
- 3.7 V 18650 Li-ion (5000 mAh) + TP4056 charging IC
- Core 0: sensor polling (~10–20 Hz) + local safety logic
- Core 1: BLE GATT server + state machine

See `stick/` for the firmware and `goggles/` for the Raspberry Pi
software.

## Backend / caregiver layer

A minimal FastAPI reference service (`backend/`) that accepts only
anonymized event metadata — object type, direction, distance, hazard
flags, timestamp, device state, source sensor, and location where
available — never raw images or audio. See `docs/ble_protocol.md` and
`docs/fusion_algorithm.md` for the wire format and decision logic that
produce these events.

## Operation modes (Section III)

| Mode | Trigger | Behavior |
|---|---|---|
| Normal | Both goggles and stick healthy | Full fusion, all 10 priority tiers active |
| Vision-Only | No stick packet for > 5 s (`stick_link_timeout_s`) | Goggles continue to announce visually detected obstacles; stick-only tiers (2–6) unavailable |
| Offline Stick | Goggles unreachable / powered down | Stick runs its own local haptics off Core 0 sensor data (see `stick/src/main.cpp::drive_local_haptics`) |
| Degraded | An individual sensor is out of calibration | That sensor's term is dropped from the weighted sum rather than substituted with an assumed value |

## Repository layout

```
BlindVision/
├── config/fusion_config.yaml   # tuned weights & thresholds (single source of truth)
├── goggles/                    # Raspberry Pi software (Python)
│   ├── vision/                 # camera workers + YOLOv8
│   ├── ble/                    # stick packet format + BLE client
│   ├── fusion/                 # Algorithm 1 fusion engine + alert messages
│   ├── audio/                  # offline TTS
│   ├── caregiver/              # anonymized event relay
│   └── tests/
├── stick/                      # ESP32 firmware (PlatformIO / Arduino)
│   ├── include/                # packet.h, pins.h, sensors.h, ble_server.h
│   └── src/                    # main.cpp, sensors.cpp, ble_server.cpp
├── poc/                        # Section V.A proof-of-concept
│   ├── server/                 # FastAPI + YOLOv8n cloud detection API
│   └── firmware/               # ESP32-CAM Arduino client
├── backend/                    # caregiver backend service (reference impl)
└── docs/
```
