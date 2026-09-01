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
    stream_status = pyqtSignal(bool, float) # (is_connected, fps)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        import cv2
        interval = 1.0 / 30.0
        stream_url = "https://fretted-tarnish-anchor.ngrok-free.dev/stream"
        
        cap = cv2.VideoCapture(stream_url)
        fail_count = 0
        fps_list = []
        
        while self._running:
            t0 = time.monotonic()
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    fail_count = 0
                    self.frame_ready.emit(frame)
                else:
                    fail_count += 1
                    self.msleep(100)
            except Exception as e:
                print(f"[VideoWorker] {e}")
                fail_count += 1
                
            elapsed = time.monotonic() - t0
            
            # FPS tracking
            if fail_count == 0 and elapsed > 0:
                fps_list.append(1.0 / elapsed)
                if len(fps_list) > 30:
                    fps_list.pop(0)
            
            # Watchdog reconnect logic
            if fail_count > 10:
                self.stream_status.emit(False, 0.0)
                cap.release()
                self.msleep(1500)  # Wait before retry
                cap = cv2.VideoCapture(stream_url)
                fail_count = 0
                fps_list.clear()
            elif fail_count == 0:
                avg_fps = sum(fps_list) / len(fps_list) if fps_list else 0.0
                self.stream_status.emit(True, avg_fps)
                
            sleep = max(0.0, interval - elapsed)
            if sleep > 0:
                self.msleep(int(sleep * 1000))
                
        cap.release()

    def stop(self):
        self._running = False
        self.wait(2000)
