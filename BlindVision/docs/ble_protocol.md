# BLE Protocol — Smart Stick ↔ Smart Goggles

Source of truth for the wire format: `stick/include/packet.h` (firmware
side) and `goggles/ble/packet.py` (Raspberry Pi side). The two **must**
stay byte-for-byte identical; both are covered by tests
(`goggles/tests/test_packet.py`) and cross-referenced in comments in
each file.

## Link

- BLE 5.0, using the Raspberry Pi's built-in Bluetooth radio and the
  ESP32's BLE stack.
- Standard Bluetooth AES-CCM pairing/bonding encryption (Section III).
  No separate application-layer cipher is implemented in this
  prototype; key material is held in device flash/NVS and there is no
  key-rotation mechanism.
- Device name: `BlindVision-Stick`
- Service UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
- Packet characteristic UUID: `6e400002-b5a3-f393-e0a9-e50e24dcca9e`
  (NOTIFY + READ)
- Expected packet period: ~50 ms (~20 Hz)
- Link timeout: no packet for **> 5 s** → goggles fall back to
  Vision-Only Mode (`config/fusion_config.yaml: stick_link_timeout_s`)

## Packet layout (24 bytes, little-endian)

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0 | 1 | `protocol_version` | `uint8`, currently `1` |
| 1 | 1 | `flags` | `uint8` bitfield — bit0 SOS, bit1 water, bit2 fall, bit3 calibrated |
| 2 | 2 | `front_mm` | `uint16`, millimeters, `0xFFFF` = out of range |
| 4 | 2 | `left_mm` | `uint16` |
| 6 | 2 | `right_mm` | `uint16` |
| 8 | 2 | `rear_mm` | `uint16` |
| 10 | 2 | `down_mm` | `uint16`, downward ultrasonic (near-field ground) |
| 12 | 2 | `ir_down_mm` | `uint16`, downward IR (drop-off sensing) |
| 14 | 1 | `battery_pct` | `uint8`, 0–100 |
| 15 | 1 | `reserved` | padding, always `0` |
| 16 | 4 | `seq` | `uint32`, monotonic packet sequence number |
| 20 | 4 | `uptime_ms` | `uint32`, stick's uptime at sample time |

Total: 24 bytes. `stick/include/packet.h` enforces this with a
`static_assert`; `goggles/ble/packet.py` enforces it with an `assert`
on the computed `struct.calcsize()`.

## Flags bitfield

| Bit | Name | Meaning |
|---|---|---|
| 0 | `FLAG_SOS` | SOS pushbutton currently pressed |
| 1 | `FLAG_WATER` | Resistive water sensor triggered |
| 2 | `FLAG_FALL` | IMU spike consistent with a fall |
| 3 | `FLAG_CALIBRATED` | Tip in normal ground-contact posture (FSR-derived) |

## Distance encoding

Distances are millimeters as `uint16`. `0xFFFF` represents "out of
range / no echo" and decodes to `float('inf')` on the Python side —
the fusion engine's `prox()` function correctly maps this to a
proximity contribution of `0`.

## Sequencing

`seq` increments every packet and is used by consumers to detect
dropped notifications; it is not currently used to reorder packets
(BLE notifications are delivered in order over a single connection).

## Extending the protocol

If you add a field: bump `protocol_version`, extend both `packet.h`
and `packet.py` together, keep the struct `#pragma pack(push, 1)` /
`<` (little-endian, no alignment padding) intact, and add a round-trip
test in `goggles/tests/test_packet.py` before changing firmware
behavior that depends on the new field.
