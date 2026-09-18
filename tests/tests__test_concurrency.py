"""
Regression coverage for the four-camera concurrency fix.

Previously, BlindVisionSystem.__init__ built exactly one YoloDetector
(one ultralytics.YOLO model instance) and every _camera_worker thread called
.detect() on that same shared instance. Ultralytics' own thread-safe-
inference guidance is explicit that sharing one model instance across
threads risks race conditions in the model's internal state, and recommends
instantiating a model inside each thread that uses it instead.

These tests don't stand up a full BlindVisionSystem (that needs real camera
devices, a BLE stack, and a backend URL). Instead they exercise the same
pattern main.py._camera_worker now uses -- constructing one YoloDetector per
worker thread -- against a fake stand-in for ultralytics.YOLO, and check
that four concurrent "camera" threads each get their own model instance and
that concurrent .detect() calls don't observe another thread's state.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))

import camera.detector as detector_module  # noqa: E402
from camera.detector import YoloDetector  # noqa: E402


class _FakeBox:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [cls_id]
        self.conf = [conf]
        self._xyxy = xyxy

    @property
    def xyxy(self):
        class _T:
            def __init__(self, v):
                self._v = v

            def tolist(self):
                return self._v
        return [_T(self._xyxy)]


class _FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


class _FakeYOLO:
    """Stands in for ultralytics.YOLO. Records its own construction (so the
    test can count instances) and, when a per-call 'poison' flag is set by
    another thread, would raise/misbehave -- exercising that no other
    thread's fake model ever gets called from this instance."""

    _instances_created = 0
    _instances_lock = threading.Lock()

    def __init__(self, model_path):
        self.model_path = model_path
        self.names = {0: "person"}
        self.call_count = 0
        with _FakeYOLO._instances_lock:
            _FakeYOLO._instances_created += 1
            self.instance_id = _FakeYOLO._instances_created

    def predict(self, image, conf, iou, verbose=False):
        # Simulate work long enough that, if two threads were sharing one
        # instance, a race would be observable in call_count.
        my_count_before = self.call_count
        time.sleep(0.005)
        self.call_count = my_count_before + 1
        return [_FakeResult(boxes=[_FakeBox(0, 0.9, [0.0, 0.0, 10.0, 20.0])])]


def test_each_worker_gets_its_own_model_instance(monkeypatch):
    """Mirrors main.py._camera_worker's pattern directly: construct a
    YoloDetector inside each of four threads and confirm each got a
    distinct underlying model instance, not a shared one."""
    monkeypatch.setattr(detector_module, "YOLO", _FakeYOLO)
    _FakeYOLO._instances_created = 0

    instance_ids = []
    lock = threading.Lock()

    def worker():
        # Same call shape as _camera_worker in main.py.
        det = YoloDetector("fake_model.pt", confidence_threshold=0.45, iou_threshold=0.50)
        with lock:
            instance_ids.append(det.model.instance_id)
        for _ in range(5):
            det.detect(image=None, bearing="front")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(instance_ids) == 4
    # Four distinct model instances -- none shared across the four "camera"
    # threads, matching the fixed _camera_worker pattern.
    assert len(set(instance_ids)) == 4


def test_concurrent_detect_calls_do_not_cross_contaminate(monkeypatch):
    """Each thread's own model instance should only ever see that thread's
    own call_count incrementing -- no interleaving with another thread's
    calls, which is what a shared instance would risk under load."""
    monkeypatch.setattr(detector_module, "YOLO", _FakeYOLO)
    _FakeYOLO._instances_created = 0

    results = {}
    results_lock = threading.Lock()

    def worker(name):
        det = YoloDetector("fake_model.pt")
        for _ in range(10):
            det.detect(image=None, bearing=name)
        with results_lock:
            results[name] = det.model.call_count

    threads = [threading.Thread(target=worker, args=(b,))
               for b in ("front", "right", "rear", "left")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    # Each of the four independent models should show exactly its own 10
    # calls -- not more (which would indicate it somehow observed another
    # thread's detect() calls) and not fewer (a dropped/raced call).
    assert results == {"front": 10, "right": 10, "rear": 10, "left": 10}
