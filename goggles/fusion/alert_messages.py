"""
Maps a FusionResult to the spoken phrase and haptic pattern described in
Sections III-IV, e.g. "Pole left 0.8 meters", continuous vibration for
drop-offs, three distinct SOS pulses that never overlap a normal hazard
signal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import AlertTier, FusionResult


@dataclass(frozen=True)
class HapticPattern:
    continuous: bool
    pulse_hz: float           # increasing pulse rate as distance decreases
    pulse_count: int = 0      # 0 = continuous / not pulse-counted


# SOS pattern: three distinct pulses, reserved and never reused elsewhere.
SOS_PATTERN = HapticPattern(continuous=False, pulse_hz=2.0, pulse_count=3)

_HAPTIC_BY_TIER = {
    AlertTier.SOS: SOS_PATTERN,
    AlertTier.CRITICAL_DROPOFF: HapticPattern(continuous=True, pulse_hz=0.0),
    AlertTier.CRITICAL_OBSTACLE: HapticPattern(continuous=True, pulse_hz=0.0),
    AlertTier.WATER_HAZARD: HapticPattern(continuous=False, pulse_hz=4.0),
    AlertTier.FALL_ALERT: HapticPattern(continuous=False, pulse_hz=5.0),
    AlertTier.HIGH_RISK_FUSED: HapticPattern(continuous=False, pulse_hz=3.0),
    AlertTier.MEDIUM: HapticPattern(continuous=False, pulse_hz=2.0),
    AlertTier.LOW: HapticPattern(continuous=False, pulse_hz=1.0),
    AlertTier.LOW_BATTERY: HapticPattern(continuous=False, pulse_hz=0.5),
    AlertTier.ROUTINE: HapticPattern(continuous=False, pulse_hz=0.0),
}


def haptic_pattern_for(tier: AlertTier) -> HapticPattern:
    return _HAPTIC_BY_TIER[tier]


def spoken_phrase_for(result: FusionResult) -> str:
    """Build a short, unambiguous spoken phrase for TTS output."""
    tier = result.tier

    if tier == AlertTier.SOS:
        return "SOS activated. Notifying your caregiver with your location."
    if tier == AlertTier.CRITICAL_DROPOFF:
        return "Stop. Drop-off ahead."
    if tier == AlertTier.CRITICAL_OBSTACLE:
        v = result.nearest_vision
        if v is not None and v.distance_m <= (result.nearest_stick_distance_m or 999):
            return f"{v.object_class.capitalize()} {v.bearing.value} {v.distance_m:.1f} meters."
        d = result.nearest_stick_distance_m or 0.0
        return f"Obstacle ahead, {d:.1f} meters."
    if tier == AlertTier.WATER_HAZARD:
        return "Caution: water ahead."
    if tier == AlertTier.FALL_ALERT:
        return "Fall detected. Notifying your caregiver."
    if tier == AlertTier.HIGH_RISK_FUSED:
        v = result.nearest_vision
        label = v.object_class if v is not None else "object"
        return f"Caution: {label} nearby."
    if tier == AlertTier.MEDIUM:
        return "Caution: obstacle ahead."
    if tier == AlertTier.LOW:
        return "Note: obstacle nearby."
    if tier == AlertTier.LOW_BATTERY:
        return "Battery low. Please recharge soon."
    return ""  # ROUTINE: silent, no announcement
