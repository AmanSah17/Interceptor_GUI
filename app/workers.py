"""
workers.py
QThread-based background workers for video and telemetry.
Both emit Qt signals so they can safely update the GUI thread.
"""
import sys
import time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'backend'))

from PyQt6.QtCore import QThread, pyqtSignal, QObject
import numpy as np

from telemetry_sim import get_telemetry
from video_generator import generate_frame
import database as db


# ── Telemetry Worker (60 Hz) ──────────────────────────────────────────────────
class TelemetryWorker(QThread):
    """Emits a fresh telemetry dict ~60 times per second."""
    data_ready = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        interval = 1.0 / 60.0
        while self._running:
            t0 = time.monotonic()
            data = get_telemetry()
            db.log_telemetry(data)          # throttled to 1 Hz inside
            self.data_ready.emit(data)
            elapsed = time.monotonic() - t0
            sleep = max(0.0, interval - elapsed)
            if sleep > 0:
                self.msleep(int(sleep * 1000))

    def stop(self):
        self._running = False
        self.wait(2000)


# ── Video Worker (30 FPS) ─────────────────────────────────────────────────────
class VideoWorker(QThread):
    """Emits raw OpenCV BGR numpy frames at ~30 FPS."""
    frame_ready = pyqtSignal(object)   # emits np.ndarray (BGR)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        interval = 1.0 / 30.0
        while self._running:
            t0 = time.monotonic()
            try:
                # generate_frame() returns JPEG bytes; decode back to ndarray
                import cv2
                buf = generate_frame()
                arr = np.frombuffer(buf, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    self.frame_ready.emit(frame)
            except Exception as e:
                print(f"[VideoWorker] {e}")
            elapsed = time.monotonic() - t0
            sleep = max(0.0, interval - elapsed)
            if sleep > 0:
                self.msleep(int(sleep * 1000))

    def stop(self):
        self._running = False
        self.wait(2000)
