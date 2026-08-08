"""
BlindVision proof-of-concept detection API.

Section V.A: "The ESP32-CAM captures a JPEG frame and posts it over
Wi-Fi to a FastAPI cloud endpoint; the endpoint runs YOLOv8n inference
at a 0.45 confidence threshold and returns the detected object, its
horizontal position (left/center/right, from the bounding-box center
relative to image thirds), an estimated relative distance (very
close/close/near/moderate/far, from the bounding-box-height-to-image
-height ratio), and a priority classified from a static per-class
lookup [...]. Detections are sorted by priority, and a natural-language
message for the highest-priority detection is returned as JSON."
"""

from __future__ import annotations

import io
import time
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO

app = FastAPI(title="BlindVision PoC Detection API", version="0.1.0")

CONFIDENCE_THRESHOLD = 0.45

# Static per-class priority lookup (Section V.A).
PRIORITY_BY_CLASS = {
    "person": "high", "vehicle": "high", "bicycle": "high",
    "chair": "medium", "stairs": "medium", "door": "medium", "backpack": "medium",
    "bottle": "low", "laptop": "low", "pole": "low",
}
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
PULSE_COUNT_BY_PRIORITY = {"high": 3, "medium": 2, "low": 1}

_model: Optional[YOLO] = None


def get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


class Detection(BaseModel):
    object_class: str
    confidence: float
    horizontal_position: str   # left | center | right
    relative_distance: str     # very_close | close | near | moderate | far
    priority: str              # high | medium | low
    pulse_count: int


class DetectionResponse(BaseModel):
    detections: List[Detection]
    top_message: str
    inference_ms: float


def _horizontal_position(x_center: float, image_width: int) -> str:
    third = image_width / 3.0
    if x_center < third:
        return "left"
    if x_center < 2 * third:
        return "center"
    return "right"


def _relative_distance(bbox_height: float, image_height: int) -> str:
    ratio = bbox_height / image_height
    if ratio > 0.75:
        return "very_close"
    if ratio > 0.5:
        return "close"
    if ratio > 0.3:
        return "near"
    if ratio > 0.15:
        return "moderate"
    return "far"


def _priority_for(object_class: str) -> str:
    return PRIORITY_BY_CLASS.get(object_class, "low")


def _natural_language_message(det: Detection) -> str:
    distance_phrase = {
        "very_close": "very close",
        "close": "close",
        "near": "nearby",
        "moderate": "ahead",
        "far": "far ahead",
    }[det.relative_distance]
    return f"{det.object_class.capitalize()} {det.horizontal_position}, {distance_phrase}."


@app.post("/detect", response_model=DetectionResponse)
async def detect(image: UploadFile = File(...)) -> DetectionResponse:
    if image.content_type not in ("image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Expected a JPEG frame from the ESP32-CAM.")

    raw = await image.read()
    pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
    width, height = pil_image.size

    model = get_model()
    start = time.monotonic()
    results = model.predict(pil_image, conf=CONFIDENCE_THRESHOLD, verbose=False)
    inference_ms = (time.monotonic() - start) * 1000.0

    detections: List[Detection] = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x_center = (x1 + x2) / 2.0
            bbox_height = y2 - y1
            priority = _priority_for(cls_name)

            detections.append(
                Detection(
                    object_class=cls_name,
                    confidence=conf,
                    horizontal_position=_horizontal_position(x_center, width),
                    relative_distance=_relative_distance(bbox_height, height),
                    priority=priority,
                    pulse_count=PULSE_COUNT_BY_PRIORITY[priority],
                )
            )

    detections.sort(key=lambda d: PRIORITY_RANK[d.priority])
    top_message = _natural_language_message(detections[0]) if detections else ""

    return DetectionResponse(
        detections=detections,
        top_message=top_message,
        inference_ms=inference_ms,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
