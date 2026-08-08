"""
Voice-guidance output. Section III: "informational audio is delivered
via the Bluetooth earbud using an offline-preferred TTS engine (e.g.,
pyttsx3 or Coqui TTS) to minimize cloud dependence."

Includes a short per-message cooldown so a stationary obstacle does not
re-trigger the same announcement every fusion cycle (mirroring the
proof-of-concept's 3-second per-class cooldown, Section V.A, applied
here at the message level for the full system).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("blindvision.audio")


class TTSAlerter:
    def __init__(self, rate_wpm: int = 175, cooldown_s: float = 3.0) -> None:
        self.rate_wpm = rate_wpm
        self.cooldown_s = cooldown_s
        self._last_message: Optional[str] = None
        self._last_time: float = 0.0
        self._engine = self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate_wpm)
            return engine
        except Exception:  # pragma: no cover - no audio hardware in CI/dev
            logger.warning("pyttsx3 unavailable; falling back to log-only TTS stub.")
            return None

    def say(self, phrase: str, force: bool = False) -> None:
        if not phrase:
            return

        now = time.monotonic()
        if not force and phrase == self._last_message and (now - self._last_time) < self.cooldown_s:
            return  # suppress duplicate/flickering alert

        self._last_message = phrase
        self._last_time = now

        if self._engine is not None:
            self._engine.say(phrase)
            self._engine.runAndWait()
        else:
            logger.info("[TTS] %s", phrase)
