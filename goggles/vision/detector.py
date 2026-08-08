"""
Aggregates the four CameraWorker instances (front-left, front-right,
rear-left, rear-right - Section III) into a single, thread-safe view of
"all currently detected objects" for the fusion engine to consume each
cycle.
"""

from __future__ import annotations

import threading
from typing import Dict, List

from ..fusion.models import Bearing, VisionDetection
from .camera_worker import CameraConfig, CameraWorker

# Default four-camera layout matching Section III: mounted at
# front-left, front-right, rear-left, rear-right at ~90 degree
# intervals, 120 degree FOV each (480 degree summed coverage, ~30
# degree overlap between adjacent cameras).
DEFAULT_CAMERA_LAYOUT = [
    CameraConfig(camera_id="front_left", device_index=0, bearing=Bearing.FRONT),
    CameraConfig(camera_id="front_right", device_index=1, bearing=Bearing.FRONT),
    CameraConfig(camera_id="rear_left", device_index=2, bearing=Bearing.REAR),
    CameraConfig(camera_id="rear_right", device_index=3, bearing=Bearing.REAR),
]


class MultiCameraDetector:
    def __init__(
        self,
        camera_configs: List[CameraConfig] = None,
        model_path: str = "training/models/yolov8n_coco_pretrained.pt",
        apply_coco_mapping: bool = True,
    ) -> None:
        self.camera_configs = camera_configs or DEFAULT_CAMERA_LAYOUT
        self.model_path = model_path
        self.apply_coco_mapping = apply_coco_mapping
        self._lock = threading.Lock()
        self._by_camera: Dict[str, List[VisionDetection]] = {}
        self._workers: List[CameraWorker] = []

    def start(self) -> None:
        for cfg in self.camera_configs:
            worker = CameraWorker(
                cfg,
                model_path=self.model_path,
                on_detections=self._on_detections,
                apply_coco_mapping=self.apply_coco_mapping,
            )
            worker.start()
            self._workers.append(worker)

    def stop(self) -> None:
        for worker in self._workers:
            worker.stop()

    def _on_detections(self, camera_id: str, detections: List[VisionDetection]) -> None:
        with self._lock:
            self._by_camera[camera_id] = detections

    def snapshot(self) -> List[VisionDetection]:
        """All detections currently held across all cameras, for one
        fusion cycle."""
        with self._lock:
            merged: List[VisionDetection] = []
            for dets in self._by_camera.values():
                merged.extend(dets)
            return merged
