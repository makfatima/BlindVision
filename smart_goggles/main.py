"""
Smart Goggles main loop (Raspberry Pi 4B).

Wires together: 4-camera concurrent capture -> on-device YOLOv8 -> BLE stick
link -> score-level fusion + priority-tier arbitration (Algorithm 1) ->
TTS/local-haptic alert dispatch -> anonymized event logging to the caregiver
backend. Mirrors the pipeline described in Sections III-VI.
"""

import argparse
import asyncio
import logging
import threading
import time
from typing import List

import config
from camera import CameraManager, YoloDetector
from ble import StickLink, StickPacket, run_stick_link
from fusion import VisionDetection, StickReading, arbitrate
from audio import AlertDispatcher
from modes import ModeManager
from caregiver import EventLogger, HazardEvent
from instrumentation import LatencyRecorder, NullRecorder, VISION_PATH, STICK_PATH

logging.basicConfig(level=logging.INFO,
                     format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("blindvision.main")


class BlindVisionSystem:
    def __init__(self, device_map: dict, recorder: LatencyRecorder = None):
        # Instrumentation is opt-in: normal operation gets a NullRecorder,
        # which does nothing and allocates nothing.
        self.recorder = recorder or NullRecorder()
        self.instrumented = not isinstance(self.recorder, NullRecorder)
        self.mode_manager = ModeManager(stick_link_timeout_s=config.STICK_LINK_TIMEOUT_S)
        # No shared YoloDetector/YOLO instance is built here. Ultralytics'
        # own thread-safety guidance is explicit: sharing one model instance
        # across threads risks race conditions in its internal state;
        # instantiate a model inside each thread that uses it instead. With
        # four concurrent _camera_worker threads (one per bearing, see
        # run()), each thread now loads and owns its own YoloDetector -- see
        # _camera_worker below. This costs one extra model load per camera
        # at startup (four total instead of one) in exchange for eliminating
        # the shared-instance race.
        self.cameras = CameraManager(device_map, resolution=config.CAMERA_RESOLUTION)
        self.stick_link = StickLink(
            config.BLE_STICK_SERVICE_UUID,
            config.BLE_STICK_CHAR_UUID,
            config.BLE_DEVICE_NAME_PREFIX,
            link_timeout_s=config.STICK_LINK_TIMEOUT_S,
        )
        self.dispatcher = AlertDispatcher(rate_wpm=config.TTS_RATE_WPM,
                                           haptic_send=self._send_haptic_to_stick,
                                           on_speech_onset=self._on_speech_onset,
                                           on_speech_end=self._on_speech_end)
        self.event_logger = EventLogger(config.BACKEND_URL)

        # Detections are held per-bearing with the wall-clock time they were
        # produced, so a stalled camera thread cannot leave stale obstacles
        # driving alerts indefinitely.
        self._detections_by_bearing: dict = {}
        self._detection_time: dict = {}
        self._detections_lock = threading.Lock()
        self._latest_stick_reading: StickReading = None

        self._fall_watchdog_start = None

        # Alert pacing state (see config.ALERT_* ).
        self._last_spoken_tier = None
        self._last_spoken_at = 0.0
        self._pending_tier = None
        self._pending_count = 0

        self._latest_stick_event = None

        # Set once run() starts the asyncio event loop that owns the BLE
        # connection; _send_haptic_to_stick (called from the AlertDispatcher's
        # own worker thread, see audio/tts_engine.py) uses this to schedule
        # the write safely across threads via run_coroutine_threadsafe.
        self._loop: "asyncio.AbstractEventLoop" = None

    # -- Stick packet handling -------------------------------------------------
    def _on_stick_packet(self, packet: StickPacket):
        if self.instrumented:
            # Origin of the stick path. The stick's own sensor-read instant
            # is on a different, unsynchronised clock and cannot be stamped
            # from here -- packet arrival is the earliest instant this side
            # can honestly claim.
            event = self.recorder.begin(
                STICK_PATH,
                ble_rtt_ms=self.stick_link.last_rtt_ms,
            )
            event.mark("packet_rx", when=packet.received_perf)
            self._latest_stick_event = event

        reading = StickReading(
            nearest_ultrasonic_m=packet.nearest_ultrasonic_m,
            down_distance_m=packet.down_distance_m,
            drop_off_detected=packet.drop_off_detected,
            # Per-direction distances, so the fused score can pair a
            # detection with the ultrasonic looking the same way instead of
            # with whatever happens to be nearest anywhere.
            distances_by_bearing={
                "front": packet.us_front_m,
                "left": packet.us_left_m,
                "right": packet.us_right_m,
                "rear": packet.us_rear_m,
            },
            age_s=max(0.0, time.perf_counter() - packet.received_perf),
            water_detected=packet.water_detected,
            fall_detected=packet.fall_detected,
            sos_pressed=packet.sos_pressed,
            battery_pct=packet.battery_pct,
        )
        self._latest_stick_reading = reading

        # Fall watchdog: forced SOS if fall detected with no recovery
        # (Section IV) -- goggles-side mirror of the stick's own watchdog.
        if packet.fall_detected:
            if self._fall_watchdog_start is None:
                self._fall_watchdog_start = time.time()
            elif (time.time() - self._fall_watchdog_start) > config.FALL_WATCHDOG_NO_RECOVERY_S:
                reading.sos_pressed = True
        else:
            self._fall_watchdog_start = None

    def _send_haptic_to_stick(self, pattern: str):
        """Issue the fused/vision-driven haptic command to the stick's
        vibration motor over BLE (StickLink.send_haptic ->
        smart_stick.ino's onHapticCommand -> outputs_set_pattern). Runs on
        the AlertDispatcher's own worker thread, not the asyncio thread that
        owns the BLE connection, so the write is scheduled across threads
        via run_coroutine_threadsafe rather than awaited directly.

        This closes what was previously a logging-only stub: the ESP32 side
        (ble_peripheral.cpp's RxCallbacks::onWrite -> onHapticCommand ->
        outputs_set_pattern) and the pattern-name contract (tts_engine.py's
        _HAPTIC_PATTERN) already existed; only this Pi-side write was
        missing. Implemented and unit-tested (see
        tests/test_haptic_dispatch.py) but NOT yet physically validated on
        the assembled two-device prototype -- that requires the actual
        hardware and is not something this fix can claim on its own.
        """
        if self._loop is None:
            logger.debug("Haptic command %r dropped: BLE loop not yet running.", pattern)
            return
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.stick_link.send_haptic(pattern), self._loop)
            # Bounded wait so a stuck BLE write can't block the dispatcher's
            # worker thread (and therefore the next queued spoken alert)
            # indefinitely; the write itself already has bleak's own
            # underlying timeout behaviour.
            sent = future.result(timeout=1.0)
            if not sent:
                logger.debug(
                    "Haptic command %r not delivered (stick not connected).", pattern)
        except Exception:
            logger.exception("Haptic command %r failed to schedule/send", pattern)

    # -- Camera worker -----------------------------------------------------
    def _camera_worker(self, bearing: str):
        stream = self.cameras.streams[bearing]
        # Instantiated here, inside the thread that uses it, per Ultralytics'
        # thread-safe-inference guidance -- not shared with the other three
        # bearings' threads. Same model weights/thresholds as before
        # (config.YOLO_MODEL_PATH / YOLO_CONFIDENCE_THRESHOLD /
        # YOLO_IOU_THRESHOLD); only the sharing pattern changes.
        detector = YoloDetector(
            config.YOLO_MODEL_PATH,
            confidence_threshold=config.YOLO_CONFIDENCE_THRESHOLD,
            iou_threshold=config.YOLO_IOU_THRESHOLD,
        )
        while True:
            frame = stream.latest()
            if frame is None:
                time.sleep(0.02)
                continue
            timing = None
            if self.instrumented:
                timing = self.recorder.begin(
                    VISION_PATH,
                    bearing=bearing,
                    frame_seq=frame.seq,
                    frames_dropped_before=frame.dropped_before,
                )
                # Overwrite the auto-stamped origin with the true capture
                # instant, so the queue wait between capture and inference is
                # visible instead of being folded into the detection stage.
                timing.stamps["capture"] = frame.capture_perf
                timing.mark("detect_start")
            try:
                detections = detector.detect(frame.image, bearing, timing=timing)
            except Exception:
                logger.exception("Detection failed on %s stream", bearing)
                time.sleep(0.1)
                continue
            if timing is not None:
                timing.mark("detect_end")
            with self._detections_lock:
                self._detections_by_bearing[bearing] = detections
                self._detection_time[bearing] = time.time()
            time.sleep(0.01)

    def _fresh_detections(self) -> List[VisionDetection]:
        """Detections from every bearing that has reported within
        DETECTION_TTL_S. A bearing whose thread has stalled simply drops out
        of the fusion input instead of contributing phantom obstacles."""
        now = time.time()
        out: List[VisionDetection] = []
        with self._detections_lock:
            for bearing, dets in self._detections_by_bearing.items():
                if now - self._detection_time.get(bearing, 0.0) <= config.DETECTION_TTL_S:
                    out.extend(dets)
        return out

    def _should_speak(self, alert) -> bool:
        """Confirmation + repeat-suppression gate.

        Two problems this solves. First, at FUSION_LOOP_HZ every iteration
        would enqueue an utterance for the same standing obstacle, behind a
        blocking TTS call, so spoken output drifts unboundedly behind the
        world. Second, a single noisy frame could announce a tier that is
        gone by the next cycle. A new tier must persist for
        ALERT_CONFIRM_FRAMES cycles; a repeat of the current tier waits for
        the repeat interval.
        """
        now = time.time()
        critical = alert.severity == "Emergency"

        if alert.tier != self._last_spoken_tier:
            if alert.tier == self._pending_tier:
                self._pending_count += 1
            else:
                self._pending_tier = alert.tier
                self._pending_count = 1
            # SOS and the other Emergency tiers are announced on sight.
            if not critical and self._pending_count < config.ALERT_CONFIRM_FRAMES:
                return False
            self._pending_tier = None
            self._pending_count = 0
            self._last_spoken_tier = alert.tier
            self._last_spoken_at = now
            return True

        interval = (config.ALERT_CRITICAL_MIN_REPEAT_S if critical
                    else config.ALERT_MIN_REPEAT_S)
        if now - self._last_spoken_at >= interval:
            self._last_spoken_at = now
            return True
        return False

    # -- Fusion loop ---------------------------------------------------------
    def _fusion_loop(self, hz: float = None):
        period = 1.0 / (hz or config.FUSION_LOOP_HZ)
        while True:
            self.mode_manager.update(stick_link_is_stale=self.stick_link.is_stale)
            detections = self._fresh_detections()

            fusion_start = time.perf_counter()
            alert = arbitrate(
                detections,
                self._latest_stick_reading,
                weights=config.DEFAULT_WEIGHTS,
                mode=self.mode_manager.arbitration_mode_str(),
            )

            fusion_end = time.perf_counter()

            if self.instrumented:
                alert.timing = self._attach_timing(
                    alert, detections, fusion_start, fusion_end)

            if alert.tier != config.Tier.ROUTINE and self._should_speak(alert):
                self.dispatcher.dispatch(alert)
                self.event_logger.log(HazardEvent(
                    event_id=EventLogger.new_event_id(),
                    event_type=alert.tier,
                    severity=alert.severity,
                    timestamp=time.time(),
                    device_state=self.mode_manager.mode.value,
                    source_sensor="fused",
                ))
            time.sleep(period)

    # -- instrumentation helpers ---------------------------------------------
    def _attach_timing(self, alert, detections, fusion_start, fusion_end):
        """Bind this alert to the event that actually caused it.

        Which path a tier came from is not a matter of taste: tiers 1, 2, 4,
        5 and 10 are stick-only; the vision clause of tier 3 and the fused
        tiers are vision-driven. Attributing an alert to the wrong path
        would mix the two distributions back together, which is the error
        this whole module exists to avoid.
        """
        stick_only_tiers = {
            config.Tier.SOS, config.Tier.CRITICAL_DROPOFF,
            config.Tier.WATER_HAZARD, config.Tier.FALL_ALERT,
            config.Tier.LOW_BATTERY,
        }
        event = None
        if alert.tier in stick_only_tiers:
            event = self._latest_stick_event
        else:
            candidates = [d.timing for d in detections if d.timing is not None]
            if candidates:
                event = min(candidates, key=lambda e: e.stamps.get("capture", 0.0))
            else:
                event = self._latest_stick_event

        if event is None:
            return None
        event.tier = alert.tier
        event.severity = alert.severity
        event.mark("fusion_start", when=fusion_start)
        event.mark("fusion_end", when=fusion_end)
        event.queue_depth = self.dispatcher.queue_depth
        return event

    def _on_speech_onset(self, alert):
        event = getattr(alert, "timing", None)
        if event is not None:
            event.mark("speech_onset")
            event.announced = True

    def _on_speech_end(self, alert):
        event = getattr(alert, "timing", None)
        if event is not None:
            event.mark("speech_end")
            self.recorder.finish(event)

    def run(self):
        self.cameras.start_all()
        for bearing in self.cameras.streams:
            threading.Thread(target=self._camera_worker, args=(bearing,),
                              daemon=True, name=f"detect-{bearing}").start()

        threading.Thread(target=self._fusion_loop, daemon=True, name="fusion").start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(run_stick_link(self.stick_link, self._on_stick_packet))
        except KeyboardInterrupt:
            logger.info("Shutting down.")
        finally:
            self.cameras.stop_all()


def main():
    parser = argparse.ArgumentParser(description="BlindVision Smart Goggles")
    parser.add_argument("--config", default="config.py", help="(informational) config module path")
    parser.add_argument("--camera-front", type=int, default=0)
    parser.add_argument("--camera-right", type=int, default=1)
    parser.add_argument("--camera-rear", type=int, default=2)
    parser.add_argument("--camera-left", type=int, default=3)
    args = parser.parse_args()

    device_map = {
        "front": args.camera_front,
        "right": args.camera_right,
        "rear": args.camera_rear,
        "left": args.camera_left,
    }
    system = BlindVisionSystem(device_map)
    system.run()


if __name__ == "__main__":
    main()
