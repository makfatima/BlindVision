"""
Delivers alerts via the Bluetooth earbud using an offline-preferred TTS
engine (pyttsx3 or Coqui TTS) to minimize cloud dependence (Section III),
with a backup speaker/buzzer path, and drives the stick's vibration motor
for haptic feedback via a command sent back over the same BLE link.

Alerts are kept unambiguous: the SOS pattern (three distinct pulses) never
overlaps with any normal hazard signal (Section IV).
"""

import logging
import queue
import threading
from typing import Optional

from fusion.arbitration import Alert
from config import Tier

logger = logging.getLogger("blindvision.audio")

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None


# Haptic pattern names sent to the stick's vibration motor over BLE.
# The stick firmware maps these to pulse counts/intensities (see
# smart_stick/outputs.cpp). SOS uses a distinct three-pulse pattern that
# never overlaps a normal hazard signal.
_HAPTIC_PATTERN = {
    Tier.SOS: "sos_three_pulse",
    Tier.CRITICAL_DROPOFF: "continuous",
    Tier.CRITICAL_OBSTACLE: "continuous",
    Tier.WATER_HAZARD: "rapid_pulse",
    Tier.FALL_ALERT: "rapid_pulse",
    Tier.HIGH_RISK_FUSED: "double_pulse",
    Tier.MEDIUM: "single_pulse",
    Tier.LOW: "slow_pulse",
    # Vision-Only Mode implies the stick link has already timed out
    # (STICK_LINK_TIMEOUT_S, config.py), so this haptic command has nowhere
    # to be delivered; the entry exists for consistency with the other
    # Caution-severity tiers and so a lookup here is explicit, not a
    # silent .get() fallback.
    Tier.VISION_WARNING_UNCALIBRATED: "slow_pulse",
    Tier.LOW_BATTERY: "long_slow_pulse",
    Tier.ROUTINE: None,
}


class AlertDispatcher:
    """Serializes spoken alerts (one at a time) and forwards a haptic-pattern
    command for the stick's vibration motor.

    Ordering: the haptic command is sent BEFORE speech starts, so the motor
    is never delayed by the length of the spoken phrase. SOS pre-empts both
    the queue and any utterance already in progress (interrupted at the next
    word boundary via the pyttsx3 'started-word' callback)."""

    def __init__(self, rate_wpm: int = 175,
                 haptic_send: Optional[callable] = None,
                 on_speech_onset: Optional[callable] = None,
                 on_speech_end: Optional[callable] = None):
        self.engine = pyttsx3.init() if pyttsx3 else None
        if self.engine:
            self.engine.setProperty("rate", rate_wpm)
        self._queue: "queue.Queue[Alert]" = queue.Queue()
        self._haptic_send = haptic_send  # callable(pattern: str) -> None
        # Onset and completion are reported separately: the user has not
        # actually been warned until the phrase carrying the direction has
        # finished, and the gap between the two is the whole utterance.
        self._on_speech_onset = on_speech_onset
        self._on_speech_end = on_speech_end
        # Set by dispatch() when an SOS arrives; checked by the speech
        # engine's word callback, which stops the current utterance. stop()
        # is called from inside the engine's own callback (same thread),
        # which is the pattern pyttsx3 supports.
        self._interrupt = threading.Event()
        if self.engine:
            self.engine.connect("started-word", self._on_word)
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    @property
    def queue_depth(self) -> int:
        """Utterances waiting behind the current one. Non-zero here means
        spoken output is already behind the world."""
        return self._queue.qsize()

    def dispatch(self, alert: Alert):
        if alert.tier == Tier.SOS:
            # SOS pre-empts: drop anything queued, cut off the utterance in
            # progress, and fire the SOS haptic now rather than waiting for
            # the worker thread.
            with self._queue.mutex:
                self._queue.queue.clear()
            self._interrupt.set()
            self._haptic(alert)
        self._queue.put(alert)

    def _on_word(self, name, location, length):
        if self._interrupt.is_set() and self.engine:
            self.engine.stop()

    def _run(self):
        while True:
            alert = self._queue.get()
            self._interrupt.clear()
            if alert.tier != Tier.SOS:      # SOS haptic already sent in dispatch()
                self._haptic(alert)         # haptic first: never waits on speech
            self._speak(alert)

    def _speak(self, alert: Alert):
        text = alert.message or f"{alert.severity}: {alert.tier}"
        logger.info("ALERT[%s/%s] %s", alert.tier, alert.severity, text)
        if self._on_speech_onset:
            self._on_speech_onset(alert)
        if self.engine:
            self.engine.say(text)
            self.engine.runAndWait()
        if self._on_speech_end:
            self._on_speech_end(alert)

    def _haptic(self, alert: Alert):
        pattern = _HAPTIC_PATTERN.get(alert.tier)
        if pattern and self._haptic_send:
            self._haptic_send(pattern)
