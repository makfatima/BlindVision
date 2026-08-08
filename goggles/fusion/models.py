"""
Shared data structures for the sensor-fusion engine.

These mirror the fields described in Section III/IV of the manuscript:
each detected object yields a class confidence and bearing; each
ultrasonic sensor reports a distance; the stick additionally exposes
boolean/derived flags (drop-off, water, fall, SOS) and battery state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Bearing(str, Enum):
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"
    REAR = "rear"
    DOWN = "down"


@dataclass(frozen=True)
class VisionDetection:
    """A single object detected by the on-device YOLOv8 pipeline."""

    object_class: str
    confidence: float          # c, in [0, 1]
    distance_m: float          # nearest estimated distance to this object
    bearing: Bearing
    camera_id: str


@dataclass(frozen=True)
class StickReading:
    """One decoded BLE packet from the Smart Stick (see ble/packet.py)."""

    ultrasonic_m: dict            # {"front": float, "left": float, ...}
    down_distance_m: float        # downward-facing IR reading
    water_detected: bool
    fall_detected: bool
    sos_pressed: bool
    battery_pct: float
    timestamp_ms: int


class AlertTier(str, Enum):
    """Priority tiers, evaluated top-down in Algorithm 1 (highest wins)."""

    SOS = "SOS"
    CRITICAL_DROPOFF = "CRITICAL_DROPOFF"
    CRITICAL_OBSTACLE = "CRITICAL_OBSTACLE"
    WATER_HAZARD = "WATER_HAZARD"
    FALL_ALERT = "FALL_ALERT"
    HIGH_RISK_FUSED = "HIGH_RISK_FUSED"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    LOW_BATTERY = "LOW_BATTERY"
    ROUTINE = "ROUTINE"


@dataclass(frozen=True)
class FusionResult:
    tier: AlertTier
    risk_score: float
    nearest_vision: Optional[VisionDetection] = None
    nearest_stick_distance_m: Optional[float] = None
    explanation: str = ""
