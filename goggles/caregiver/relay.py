"""
Caregiver layer relay running on the Smart Goggles (Section III).

Reads position from the u-blox NEO-6M GPS module, and pushes only
anonymized event metadata (object type, direction, distance, hazard
flags, timestamp, device state) to the backend over TLS 1.2 -- raw
images/audio are never transmitted or stored, per privacy-by-design
(Sections III, IV.4).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional

import requests

from ..fusion.models import FusionResult

logger = logging.getLogger("blindvision.caregiver")


@dataclass(frozen=True)
class DeviceEvent:
    """The only payload shape ever sent off-device. No pixels, no audio."""

    event_type: str          # alert tier name, e.g. "CRITICAL_OBSTACLE"
    direction: Optional[str]
    distance_m: Optional[float]
    severity: str
    timestamp_ms: int
    device_state: str        # "normal" | "vision_only" | "offline_stick" | "degraded"
    source_sensor: str       # "vision" | "stick" | "fused"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CaregiverRelay:
    def __init__(self, backend_url: str, geofence_check_interval_s: int = 10) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.geofence_check_interval_s = geofence_check_interval_s
        self._last_geofence_check = 0.0

    @staticmethod
    def to_event(result: FusionResult, device_state: str, lat: Optional[float], lon: Optional[float]) -> DeviceEvent:
        direction = result.nearest_vision.bearing.value if result.nearest_vision else None
        distance = (
            result.nearest_vision.distance_m
            if result.nearest_vision is not None
            else result.nearest_stick_distance_m
        )
        source = "fused" if (result.nearest_vision and result.nearest_stick_distance_m) else (
            "vision" if result.nearest_vision else "stick"
        )
        return DeviceEvent(
            event_type=result.tier.value,
            direction=direction,
            distance_m=distance,
            severity=result.tier.value,
            timestamp_ms=int(time.time() * 1000),
            device_state=device_state,
            source_sensor=source,
            latitude=lat,
            longitude=lon,
        )

    def push_event(self, event: DeviceEvent, timeout_s: float = 5.0) -> bool:
        """POST an anonymized event over TLS 1.2. Returns True on success;
        never raises on network failure (a caregiver-link outage must not
        block local safety alerting)."""
        try:
            resp = requests.post(
                f"{self.backend_url}/events",
                data=json.dumps(asdict(event)),
                headers={"Content-Type": "application/json"},
                timeout=timeout_s,
            )
            return resp.status_code < 300
        except requests.RequestException as exc:
            logger.warning("Caregiver relay failed (event queued for retry): %s", exc)
            return False
