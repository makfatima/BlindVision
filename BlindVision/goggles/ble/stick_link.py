"""
BLE 5.0 link to the Smart Stick, using the Raspberry Pi's built-in
Bluetooth radio (Section III). Uses `bleak` for a cross-platform BLE
client. If no packet arrives within `link_timeout_s` (default 5s, per
Section III/IV), the link is considered lost and the goggles should
fall back to Vision-Only Mode.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from .packet import DecodedPacket, decode
from ..fusion.models import StickReading

logger = logging.getLogger("blindvision.ble")

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover - hardware dependency, optional at import time
    BleakClient = None
    BleakScanner = None


def decoded_to_reading(pkt: DecodedPacket) -> StickReading:
    """Adapt the wire-format packet into the fusion engine's StickReading."""
    return StickReading(
        ultrasonic_m={
            "front": pkt.front_m,
            "left": pkt.left_m,
            "right": pkt.right_m,
            "rear": pkt.rear_m,
            "down": pkt.down_m,
        },
        down_distance_m=pkt.down_ir_m,
        water_detected=pkt.water_detected,
        fall_detected=pkt.fall_detected,
        sos_pressed=pkt.sos_pressed,
        battery_pct=float(pkt.battery_pct),
        timestamp_ms=pkt.uptime_ms,
    )


class StickLink:
    """Maintains the BLE connection to the stick and tracks link health."""

    def __init__(
        self,
        device_name: str,
        service_uuid: str,
        packet_char_uuid: str,
        link_timeout_s: float = 5.0,
        on_reading: Optional[Callable[[StickReading], None]] = None,
    ) -> None:
        self.device_name = device_name
        self.service_uuid = service_uuid
        self.packet_char_uuid = packet_char_uuid
        self.link_timeout_s = link_timeout_s
        self.on_reading = on_reading

        self._client: Optional["BleakClient"] = None
        self._last_packet_time: float = 0.0
        self.latest_reading: Optional[StickReading] = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def link_healthy(self) -> bool:
        """False once we exceed the stick-disconnect timeout with no
        packet — the trigger for Vision-Only Mode (Section III/IV)."""
        if self._last_packet_time == 0.0:
            return False
        return (time.monotonic() - self._last_packet_time) < self.link_timeout_s

    async def connect(self) -> None:
        if BleakScanner is None:
            raise RuntimeError("bleak is not installed; `pip install bleak` on the Pi")

        logger.info("Scanning for stick device %r ...", self.device_name)
        device = await BleakScanner.find_device_by_filter(
            lambda d, adv: d.name == self.device_name
        )
        if device is None:
            raise ConnectionError(f"Smart Stick '{self.device_name}' not found")

        self._client = BleakClient(device)
        await self._client.connect()
        await self._client.start_notify(self.packet_char_uuid, self._handle_notification)
        logger.info("Connected to Smart Stick at %s", device.address)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.stop_notify(self.packet_char_uuid)
            await self._client.disconnect()
            self._client = None

    def _handle_notification(self, _sender: int, data: bytearray) -> None:
        try:
            pkt = decode(bytes(data))
        except ValueError:
            logger.warning("Dropped malformed stick packet (%d bytes)", len(data))
            return

        self._last_packet_time = time.monotonic()
        reading = decoded_to_reading(pkt)
        self.latest_reading = reading
        if self.on_reading is not None:
            self.on_reading(reading)

    async def run_reconnect_loop(self, retry_interval_s: float = 3.0) -> None:
        """Keep the link alive, retrying on disconnect. Intended to run
        as a background asyncio task alongside the main fusion loop."""
        while True:
            try:
                if not self.is_connected:
                    await self.connect()
                await asyncio.sleep(retry_interval_s)
            except (ConnectionError, RuntimeError, OSError) as exc:
                logger.warning("Stick link error: %s (retrying in %.1fs)", exc, retry_interval_s)
                await asyncio.sleep(retry_interval_s)
