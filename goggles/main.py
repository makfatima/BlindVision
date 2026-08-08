"""
BlindVision Smart Goggles - main process.

Ties together (Section III):
  - MultiCameraDetector   (4x on-device YOLOv8 camera workers)
  - StickLink             (BLE 5.0 packet stream from the Smart Stick)
  - FusionEngine          (Algorithm 1 priority-tier arbitration)
  - TTSAlerter            (offline-preferred spoken guidance)
  - CaregiverRelay        (anonymized event push over TLS 1.2)

Implements the four operation modes described in Section III:
  Normal          - goggles + stick both healthy, full fusion
  Vision-Only     - stick link lost > stick_link_timeout_s -> tiers 2-6
                    from the stick are simply unavailable
  Offline Stick   - (runs on the ESP32 itself; not modeled here)
  Degraded        - an out-of-calibration sensor's term is dropped from
                    the weighted sum rather than substituted

Run with:
    python -m goggles.main --config config/fusion_config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from pathlib import Path

import yaml

from .audio.tts_alert import TTSAlerter
from .ble.stick_link import StickLink
from .caregiver.relay import CaregiverRelay
from .fusion.alert_messages import spoken_phrase_for
from .fusion.fusion_engine import load_engine_from_config
from .vision.detector import MultiCameraDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("blindvision.main")


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class GogglesApp:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.engine = load_engine_from_config(config)
        self.detector = MultiCameraDetector(
            model_path=config["vision"]["weights_path"],
            apply_coco_mapping=(config["vision"].get("class_mapping", "coco") == "coco"),
        )
        self.tts = TTSAlerter(rate_wpm=config["audio"]["rate_wpm"])
        self.caregiver = CaregiverRelay(
            backend_url=config["caregiver"]["backend_url"],
            geofence_check_interval_s=config["caregiver"]["geofence_check_interval_s"],
        )
        self.stick = StickLink(
            device_name=config["ble"]["device_name"],
            service_uuid=config["ble"]["service_uuid"],
            packet_char_uuid=config["ble"]["packet_char_uuid"],
            link_timeout_s=config["stick_link_timeout_s"],
        )

    def current_mode(self) -> str:
        if self.stick.link_healthy:
            return "normal"
        return "vision_only"

    async def fusion_loop(self, cycle_hz: float = 10.0) -> None:
        period_s = 1.0 / cycle_hz
        while True:
            start = time.monotonic()

            detections = self.detector.snapshot()
            stick_reading = self.stick.latest_reading if self.stick.link_healthy else None
            mode = self.current_mode()

            result = self.engine.evaluate(detections, stick_reading)
            phrase = spoken_phrase_for(result)
            if phrase:
                self.tts.say(phrase)

            if result.tier.value not in ("ROUTINE",):
                event = self.caregiver.to_event(result, device_state=mode, lat=None, lon=None)
                self.caregiver.push_event(event)

            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0.0, period_s - elapsed))

    async def run(self) -> None:
        self.detector.start()
        stick_task = asyncio.create_task(self.stick.run_reconnect_loop())
        fusion_task = asyncio.create_task(self.fusion_loop())
        try:
            await asyncio.gather(stick_task, fusion_task)
        finally:
            self.detector.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="BlindVision Smart Goggles")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "fusion_config.yaml"),
    )
    args = parser.parse_args()

    config = load_config(args.config)
    app = GogglesApp(config)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
