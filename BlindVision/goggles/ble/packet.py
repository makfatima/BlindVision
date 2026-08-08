"""
Wire format for the structured sensor packet the Smart Stick streams
continuously to the Smart Goggles over BLE (Section III), containing
status flags (fall, SOS, water) and distances from each
ultrasonic/IR sensor. This module must stay in lock-step with the
C struct `StickPacket` in stick/src/packet.h.

Layout (little-endian, 24 bytes, matches stick/src/packet.h):

  offset  size  field
  0       1     protocol_version (uint8)
  1       1     flags (uint8 bitfield: bit0 SOS, bit1 water, bit2 fall,
                        bit3 stick_calibrated)
  2       2     front_mm   (uint16, 0-9999, 0xFFFF = out of range)
  4       2     left_mm    (uint16)
  6       2     right_mm   (uint16)
  8       2     rear_mm    (uint16)
  10      2     down_mm    (uint16)   # downward ultrasonic, near-field
  12      2     ir_down_mm (uint16)   # downward IR (drop-off sensing)
  14      1     battery_pct (uint8, 0-100)
  15      1     reserved
  16      4     seq (uint32)          # monotonic packet sequence number
  20      4     uptime_ms (uint32)    # stick's uptime at sample time
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

_STRUCT_FMT = "<BBHHHHHHBBII"  # little-endian, matches the layout above
PACKET_SIZE = struct.calcsize(_STRUCT_FMT)
assert PACKET_SIZE == 24, f"unexpected packet size {PACKET_SIZE}"

PROTOCOL_VERSION = 1

_FLAG_SOS = 0b0001
_FLAG_WATER = 0b0010
_FLAG_FALL = 0b0100
_FLAG_CALIBRATED = 0b1000

_OUT_OF_RANGE = 0xFFFF


@dataclass(frozen=True)
class DecodedPacket:
    protocol_version: int
    sos_pressed: bool
    water_detected: bool
    fall_detected: bool
    calibrated: bool
    front_m: float
    left_m: float
    right_m: float
    rear_m: float
    down_m: float
    down_ir_m: float
    battery_pct: int
    seq: int
    uptime_ms: int


def _mm_to_m(mm: int) -> float:
    if mm == _OUT_OF_RANGE:
        return float("inf")
    return mm / 1000.0


def _m_to_mm(m: float) -> int:
    if m == float("inf") or m > 9.999:
        return _OUT_OF_RANGE
    return int(round(m * 1000))


def decode(raw: bytes) -> DecodedPacket:
    if len(raw) != PACKET_SIZE:
        raise ValueError(f"expected {PACKET_SIZE} bytes, got {len(raw)}")
    (
        version, flags, front, left, right, rear, down, ir_down,
        battery, _reserved, seq, uptime_ms,
    ) = struct.unpack(_STRUCT_FMT, raw)

    return DecodedPacket(
        protocol_version=version,
        sos_pressed=bool(flags & _FLAG_SOS),
        water_detected=bool(flags & _FLAG_WATER),
        fall_detected=bool(flags & _FLAG_FALL),
        calibrated=bool(flags & _FLAG_CALIBRATED),
        front_m=_mm_to_m(front),
        left_m=_mm_to_m(left),
        right_m=_mm_to_m(right),
        rear_m=_mm_to_m(rear),
        down_m=_mm_to_m(down),
        down_ir_m=_mm_to_m(ir_down),
        battery_pct=battery,
        seq=seq,
        uptime_ms=uptime_ms,
    )


def encode(
    *,
    sos_pressed: bool = False,
    water_detected: bool = False,
    fall_detected: bool = False,
    calibrated: bool = True,
    front_m: float = 3.0,
    left_m: float = 3.0,
    right_m: float = 3.0,
    rear_m: float = 3.0,
    down_m: float = 0.3,
    down_ir_m: float = 0.3,
    battery_pct: int = 100,
    seq: int = 0,
    uptime_ms: int = 0,
) -> bytes:
    """Encode a packet — used by the PC-side simulator/tests and by any
    tooling that needs to emit synthetic stick traffic."""
    flags = 0
    flags |= _FLAG_SOS if sos_pressed else 0
    flags |= _FLAG_WATER if water_detected else 0
    flags |= _FLAG_FALL if fall_detected else 0
    flags |= _FLAG_CALIBRATED if calibrated else 0

    return struct.pack(
        _STRUCT_FMT,
        PROTOCOL_VERSION,
        flags,
        _m_to_mm(front_m),
        _m_to_mm(left_m),
        _m_to_mm(right_m),
        _m_to_mm(rear_m),
        _m_to_mm(down_m),
        _m_to_mm(down_ir_m),
        max(0, min(100, battery_pct)),
        0,
        seq & 0xFFFFFFFF,
        uptime_ms & 0xFFFFFFFF,
    )
