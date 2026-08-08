from goggles.ble.packet import PACKET_SIZE, decode, encode


def test_packet_size_is_24_bytes():
    assert PACKET_SIZE == 24


def test_encode_decode_roundtrip():
    raw = encode(
        sos_pressed=False,
        water_detected=True,
        fall_detected=False,
        calibrated=True,
        front_m=0.42,
        left_m=1.5,
        right_m=2.9,
        rear_m=3.0,
        down_m=0.3,
        down_ir_m=0.8,
        battery_pct=76,
        seq=42,
        uptime_ms=98765,
    )
    assert len(raw) == PACKET_SIZE

    decoded = decode(raw)
    assert decoded.sos_pressed is False
    assert decoded.water_detected is True
    assert decoded.fall_detected is False
    assert decoded.calibrated is True
    assert abs(decoded.front_m - 0.42) < 1e-3
    assert abs(decoded.left_m - 1.5) < 1e-3
    assert decoded.battery_pct == 76
    assert decoded.seq == 42
    assert decoded.uptime_ms == 98765


def test_out_of_range_distance_encodes_as_infinity():
    raw = encode(front_m=float("inf"))
    decoded = decode(raw)
    assert decoded.front_m == float("inf")


def test_decode_rejects_wrong_size():
    import pytest
    with pytest.raises(ValueError):
        decode(b"\x00" * 10)


def test_sos_flag_roundtrip():
    raw = encode(sos_pressed=True)
    decoded = decode(raw)
    assert decoded.sos_pressed is True
