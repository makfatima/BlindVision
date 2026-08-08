"""
Per-camera capture + on-device YOLOv8 detection worker.

Section III: "The four streams are processed concurrently -- one
detection thread/process per camera, run in parallel rather than
round-robin -- so that all four directions are refreshed at comparable
intervals rather than one direction waiting on the others."

Each worker owns one USB camera (1080p, 120 deg FOV), runs inference,
and estimates an approximate distance from the bounding-box-height-to
-frame-height ratio (the same estimation principle used in the
proof-of-concept, Section V.A, carried into the full system).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..fusion.models import Bearing, VisionDetection
from .coco_mapping import map_class
from .distance_calibration import DistanceEstimator

logger = logging.getLogger("blindvision.vision")

# Distance estimation: distance_m = k / bbox_height_ratio, with k fit
# from real measurements against your own camera rig. See
# tools/calibrate_vision_distance.py and
# goggles/vision/calibration/vision_calibration.json (currently seeded
# with a documented pinhole-model placeholder — recalibrate before
# trusting distance-based alert tiers in the field).
_distance_estimator = DistanceEstimator()


def estimate_distance_m(bbox_height_ratio: float) -> float:
    """bbox_height_ratio = detected box height / frame height, in (0, 1]."""
    return _distance_estimator.estimate_m(bbox_height_ratio)


@dataclass
class CameraConfig:
    camera_id: str
    device_index: int
    bearing: Bearing
    confidence_threshold: float = 0.45


class CameraWorker:
    """Runs in its own thread; owns one camera + one YOLO model instance."""

    def __init__(
        self,
        config: CameraConfig,
        model_path: str = "training/models/yolov8n_coco_pretrained.pt",
        on_detections: Optional[Callable[[str, List[VisionDetection]], None]] = None,
        apply_coco_mapping: bool = True,
    ) -> None:
        self.config = config
        self.model_path = model_path
        self.on_detections = on_detections
        # True for the bundled COCO-pretrained checkpoint (default); set
        # False once you swap in your own fine-tuned BlindVision 10-class
        # model, which already emits BlindVision class names directly
        # (see goggles/vision/coco_mapping.py and training/README.md).
        self.apply_coco_mapping = apply_coco_mapping
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.latest_detections: List[VisionDetection] = []

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=f"cam-{self.config.camera_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            import cv2  # local import: optional hardware dependency
            from ultralytics import YOLO
        except ImportError:
            logger.error(
                "OpenCV/ultralytics not available; camera worker %s cannot start. "
                "Install with `pip install -r goggles/requirements.txt`.",
                self.config.camera_id,
            )
            return

        model = YOLO(self.model_path)
        cap = cv2.VideoCapture(self.config.device_index)
        if not cap.isOpened():
            logger.error("Could not open camera %s (index %d)",
                         self.config.camera_id, self.config.device_index)
            return

        logger.info("Camera worker %s started (bearing=%s)",
                    self.config.camera_id, self.config.bearing.value)

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame_h = frame.shape[0]
                results = model.predict(
                    frame, conf=self.config.confidence_threshold, verbose=False
                )

                detections: List[VisionDetection] = []
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        raw_cls_name = model.names[cls_id]

                        if self.apply_coco_mapping:
                            cls_name = map_class(raw_cls_name)
                            if cls_name is None:
                                continue  # unmapped COCO class, e.g. "airplane" - drop
                        else:
                            cls_name = raw_cls_name

                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        bbox_height_ratio = (y2 - y1) / frame_h
                        distance_m = estimate_distance_m(bbox_height_ratio)

                        detections.append(
                            VisionDetection(
                                object_class=cls_name,
                                confidence=conf,
                                distance_m=distance_m,
                                bearing=self.config.bearing,
                                camera_id=self.config.camera_id,
                            )
                        )

                self.latest_detections = detections
                if self.on_detections is not None:
                    self.on_detections(self.config.camera_id, detections)
        finally:
            cap.release()
            logger.info("Camera worker %s stopped", self.config.camera_id)
