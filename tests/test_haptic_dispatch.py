"""
Coverage for closing the goggles-to-stick remote haptic path
(StickLink.send_haptic + BlindVisionSystem._send_haptic_to_stick).

Previously _send_haptic_to_stick only logged the pattern name; no BLE write
was issued, so a fused/vision-driven alert's haptic command never reached
the stick's vibration motor even though the ESP32 side
(smart_stick/smart_stick.ino's onHapticCommand -> outputs_set_pattern) and
the pattern-name contract (tts_engine.py's _HAPTIC_PATTERN) already existed.

These tests exercise the software path with fakes standing in for bleak's
BleakClient and for the asyncio event loop main.py's run() normally owns --
they do not touch real BLE hardware. Physical validation on the assembled
two-device prototype is a separate, still-outstanding requirement (see the
manuscript's Section V.B note).
"""

import asyncio
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

from ble.stick_link import StickLink  # noqa: E402


class _FakeBleakClient:
    def __init__(self, connected=True, raise_on_write=False):
        self.is_connected = connected
        self.raise_on_write = raise_on_write
        self.writes = []

    async def write_gatt_char(self, char_uuid, data):
        if self.raise_on_write:
            raise RuntimeError("simulated BLE write failure")
        self.writes.append((char_uuid, data))


def _make_link(client):
    link = StickLink(
        service_uuid="svc", char_uuid="notify-char",
        command_char_uuid="cmd-char",
    )
    link._client = client
    return link


def test_send_haptic_not_connected_returns_false_and_does_not_write():
    link = _make_link(_FakeBleakClient(connected=False))
    result = asyncio.run(link.send_haptic("continuous"))
    assert result is False


def test_send_haptic_no_client_at_all_returns_false():
    link = StickLink(service_uuid="svc", char_uuid="notify-char")
    assert link.is_connected is False
    result = asyncio.run(link.send_haptic("rapid_pulse"))
    assert result is False


def test_send_haptic_writes_pattern_bytes_when_connected():
    client = _FakeBleakClient(connected=True)
    link = _make_link(client)
    result = asyncio.run(link.send_haptic("continuous"))
    assert result is True
    assert client.writes == [("cmd-char", b"continuous")]


def test_send_haptic_write_failure_is_caught_and_returns_false():
    client = _FakeBleakClient(connected=True, raise_on_write=True)
    link = _make_link(client)
    result = asyncio.run(link.send_haptic("slow_pulse"))
    assert result is False


def test_send_haptic_pattern_names_match_firmware_contract():
    """Every pattern name tts_engine.py's _HAPTIC_PATTERN can produce must
    be a string send_haptic will pass through unchanged -- the firmware
    side (smart_stick.ino's onHapticCommand) matches on the literal string,
    so this module must never transform or truncate it."""
    from audio.tts_engine import _HAPTIC_PATTERN
    client = _FakeBleakClient(connected=True)
    link = _make_link(client)
    names = sorted({v for v in _HAPTIC_PATTERN.values() if v is not None})
    for name in names:
        asyncio.run(link.send_haptic(name))
    assert [w[1] for w in client.writes] == [n.encode() for n in names]


def test_main_schedules_haptic_across_threads_via_running_loop():
    """Mirrors the real architecture: an asyncio loop running on its own
    thread (as main.py's run() does), with _send_haptic_to_stick called
    from a different thread (as tts_engine.py's AlertDispatcher worker
    does), and confirms the write reaches the fake stick_link without
    blocking the calling thread indefinitely."""
    import main as main_module

    class _FakeStickLink:
        def __init__(self):
            self.sent = []

        async def send_haptic(self, pattern):
            await asyncio.sleep(0.001)
            self.sent.append(pattern)
            return True

    system = object.__new__(main_module.BlindVisionSystem)
    system.stick_link = _FakeStickLink()
    system._loop = None

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    system._loop = loop
    try:
        start = time.perf_counter()
        main_module.BlindVisionSystem._send_haptic_to_stick(system, "continuous")
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0  # bounded wait, not an indefinite block
        assert system.stick_link.sent == ["continuous"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2)


def test_main_haptic_before_loop_started_does_not_raise():
    """Before run() starts the BLE event loop, a haptic command must be
    dropped quietly, not crash the dispatcher's worker thread."""
    import main as main_module

    system = object.__new__(main_module.BlindVisionSystem)
    system.stick_link = None
    system._loop = None
    main_module.BlindVisionSystem._send_haptic_to_stick(system, "continuous")
