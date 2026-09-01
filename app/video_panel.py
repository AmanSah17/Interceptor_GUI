"""
video_panel.py
Primary video display widget with HUD overlay drawn via QPainter.

Features:
  - Displays OpenCV BGR frames (converted to QPixmap)
  - Bounding boxes with military corner brackets
  - Confidence labels
  - Mini artificial horizon (top-left)
  - Frame rate counter (top-right)
"""
import math
import time

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore    import Qt, QRect, QRectF, QPointF, QTimer
from PyQt6.QtGui     import (
    QPainter, QPen, QBrush, QColor, QImage, QPixmap,
    QFont, QFontMetrics, QPainterPath, QLinearGradient
)

ACCENT   = QColor(0, 255, 136)
AMBER    = QColor(255, 179, 0)
DANGER   = QColor(255, 51,  85)
WHITE    = QColor(255, 255, 255)
BLACK    = QColor(0,   0,   0)
SKY_COL  = QColor(0,  30,  60,  180)
GND_COL  = QColor(20, 50,  20,  180)


class VideoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background: #000;")

        self._pixmap   : QPixmap | None = None
        self._boxes    : list[dict]     = []
        self._pitch    : float          = 0.0
        self._roll     : float          = 0.0
        self._fps      : float          = 0.0
        self._frame_ts : list[float]    = []

    # ── Public update methods ─────────────────────────────────────────────────
    def set_frame(self, frame: np.ndarray):
        """Accept an OpenCV BGR frame and schedule a repaint."""
        # Track FPS
        now = time.monotonic()
        self._frame_ts.append(now)
        self._frame_ts = [t for t in self._frame_ts if now - t < 1.0]
        self._fps = len(self._frame_ts)

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(img)
        self.update()

    def set_boxes(self, boxes: list[dict]):
        self._boxes = boxes

    def set_horizon(self, pitch: float, roll: float):
        self._pitch = pitch
        self._roll  = roll

    # ── Qt painting ───────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        W, H = self.width(), self.height()

        # ── Draw video frame ─────────────────────────────────────────────────
        if self._pixmap:
            scaled = self._pixmap.scaled(
                W, H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (W - scaled.width())  // 2
            y = (H - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            self._video_rect = QRect(x, y, scaled.width(), scaled.height())
        else:
            self._video_rect = QRect(0, 0, W, H)
            p.fillRect(0, 0, W, H, QColor(0, 0, 0))
            p.setPen(QPen(ACCENT, 1))
            p.setFont(QFont("Consolas", 12))
            p.drawText(QRect(0, 0, W, H), Qt.AlignmentFlag.AlignCenter,
                       "AWAITING VIDEO FEED…")

        # ── Scanline overlay ─────────────────────────────────────────────────
        scan_col = QColor(0, 255, 136, 12)
        for y in range(0, H, 4):
            p.fillRect(0, y, W, 1, scan_col)

        # ── Corner brackets ──────────────────────────────────────────────────
        self._draw_corner_brackets(p, W, H)

        # ── Crosshair ────────────────────────────────────────────────────────
        self._draw_crosshair(p, W, H)

        # ── Bounding boxes ────────────────────────────────────────────────────
        vr = self._video_rect
        for box in self._boxes:
            self._draw_box(p, box, vr.x(), vr.y(), vr.width(), vr.height())

        # ── Artificial horizon ────────────────────────────────────────────────
        self._draw_horizon(p, W, H)

        # ── FPS counter ───────────────────────────────────────────────────────
        p.setPen(QPen(ACCENT, 1))
        p.setFont(QFont("Consolas", 9))
        p.drawText(W - 100, 14, f"{self._fps:.0f} FPS")
        p.drawText(W - 100, 28, "1280×720")

        p.end()

    def _draw_corner_brackets(self, p: QPainter, W: int, H: int):
        arm = 36
        pen = QPen(ACCENT, 2)
        p.setPen(pen)
        corners = [(0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)]
        margin  = 18
        for cx, cy, sx, sy in corners:
            x, y = cx + sx * margin, cy + sy * margin
            p.drawLine(int(x), int(y), int(x + sx * arm), int(y))
            p.drawLine(int(x), int(y), int(x), int(y + sy * arm))

    def _draw_crosshair(self, p: QPainter, W: int, H: int):
        cx, cy = W // 2, H // 2
        gap, arm = 16, 28
        pen = QPen(ACCENT, 1)
        p.setPen(pen)
        p.drawLine(cx - arm - gap, cy, cx - gap, cy)
        p.drawLine(cx + gap, cy, cx + arm + gap, cy)
        p.drawLine(cx, cy - arm - gap, cx, cy - gap)
        p.drawLine(cx, cy + gap, cx, cy + arm + gap)
        p.drawEllipse(QPointF(cx, cy), 3, 3)

    def _draw_box(self, p: QPainter, box: dict,
                  ox: int, oy: int, fw: int, fh: int):
        x = int(ox + box['x'] * fw)
        y = int(oy + box['y'] * fh)
        w = int(box['w'] * fw)
        h = int(box['h'] * fh)
        arm = int(min(w, h) * 0.22)
        colour = AMBER if box['label'] == 'Unknown' else ACCENT

        pen = QPen(colour, 2)
        p.setPen(pen)
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))

        # Semi-transparent fill
        fill_col = QColor(colour)
        fill_col.setAlpha(10)
        p.fillRect(x, y, w, h, fill_col)

        # Corner brackets
        pts = [
            [(x,       y),       (x + arm,  y),       (x,       y + arm)],
            [(x + w,   y),       (x+w-arm,  y),       (x + w,   y + arm)],
            [(x,       y + h),   (x + arm,  y + h),   (x,       y+h-arm)],
            [(x + w,   y + h),   (x+w-arm,  y + h),   (x + w,   y+h-arm)],
        ]
        for corner in pts:
            a, b, c = corner
            p.drawLine(a[0], a[1], b[0], b[1])
            p.drawLine(a[0], a[1], c[0], c[1])

        # Label
        conf_pct = int(box['conf'] * 100)
        label_text = f"{box['label']}  {conf_pct}%"
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(label_text)
        lx, ly = x, y - 16
        if ly < 0:
            ly = y + h + 14
        p.fillRect(lx - 2, ly - 12, tw + 8, 16, QColor(0, 0, 0, 160))
        p.setPen(QPen(colour, 1))
        p.drawText(lx + 2, ly, label_text)

    def _draw_horizon(self, p: QPainter, W: int, H: int):
        """Mini artificial horizon — bottom-left of video."""
        cx, cy, R = 70, H - 75, 52
        p.save()
        p.translate(cx, cy)
        p.rotate(self._roll)

        # Clip to circle
        clip = QPainterPath()
        clip.addEllipse(QPointF(0, 0), R, R)
        p.setClipPath(clip)

        # Sky
        pitch_px = self._pitch * 1.5
        grad = QLinearGradient(0, -R, 0, R)
        grad.setColorAt(0.0, SKY_COL)
        horizon_pos = 0.5 - pitch_px / (2 * R)
        grad.setColorAt(max(0.0, min(1.0, horizon_pos)), SKY_COL)
        grad.setColorAt(max(0.0, min(1.0, horizon_pos + 0.001)), GND_COL)
        grad.setColorAt(1.0, GND_COL)
        p.fillRect(-R, -R, R * 2, R * 2, grad)

        # Horizon line
        p.setClipping(False)
        pen = QPen(ACCENT, 1.5)
        p.setPen(pen)
        p.drawLine(-R, int(pitch_px), R, int(pitch_px))

        # Pitch tick marks
        p.setPen(QPen(ACCENT, 0.8))
        for deg in [-20, -10, 10, 20]:
            py = int(pitch_px - deg * 1.5)
            if -R < py < R:
                hw = 16 if abs(deg) == 20 else 10
                p.drawLine(-hw, py, hw, py)

        p.restore()

        # Outer ring
        p.save()
        p.translate(cx, cy)
        pen = QPen(ACCENT, 1.5)
        p.setPen(pen)
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        p.drawEllipse(QPointF(0, 0), R, R)

        # Fixed aircraft wings
        p.setPen(QPen(WHITE, 2))
        p.drawLine(-R + 6, 0, -8, 0)
        p.drawLine(-8, 0, -4, 5)
        p.drawLine(R - 6, 0, 8, 0)
        p.drawLine(8, 0, 4, 5)
        p.drawEllipse(QPointF(0, 0), 3, 3)
        p.restore()

        # AH label
        p.setPen(QPen(ACCENT, 1))
        p.setFont(QFont("Consolas", 8))
        p.drawText(cx - 10, H - 15, "AH")
