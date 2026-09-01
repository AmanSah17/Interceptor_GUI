"""
compass_widget.py
Custom QPainter compass rose widget.
Smoothly interpolates heading with every update.
"""
import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore    import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui     import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QPainterPath, QConicalGradient, QRadialGradient
)

ACCENT  = QColor(0,   255, 136)
RED     = QColor(255, 51,  85)
DIM     = QColor(30,  80,  50)
BG      = QColor(8,   18,  12)
GOLD    = QColor(255, 200, 50)


class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(160, 160)
        self._current  = 0.0
        self._target   = 0.0
        self._timer    = QTimer(self)
        self._timer.timeout.connect(self._interpolate)
        self._timer.start(16)   # ~60 fps interpolation

    def set_heading(self, heading: float):
        self._target = heading % 360

    def _interpolate(self):
        diff = self._target - self._current
        if diff > 180:  diff -= 360
        if diff < -180: diff += 360
        if abs(diff) < 0.15:
            self._current = self._target
        else:
            self._current += diff * 0.14
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        R = min(cx, cy) - 4

        # ── Background circle ─────────────────────────────────────────────
        bg_grad = QRadialGradient(cx, cy, R)
        bg_grad.setColorAt(0.0, QColor(12, 28, 18))
        bg_grad.setColorAt(1.0, QColor(5,  10,  7))
        p.setBrush(QBrush(bg_grad))
        p.setPen(QPen(QColor(0, 255, 136, 40), 1))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # ── Outer ring ────────────────────────────────────────────────────
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        p.setPen(QPen(QColor(0, 255, 136, 80), 1.5))
        p.drawEllipse(QPointF(cx, cy), R - 1, R - 1)
        p.setPen(QPen(QColor(0, 255, 136, 30), 0.8))
        p.drawEllipse(QPointF(cx, cy), R - 8, R - 8)

        # ── Rotate for heading ────────────────────────────────────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._current)

        # Tick marks
        for deg in range(0, 360, 5):
            is_major   = deg % 45 == 0
            is_mid     = deg % 15 == 0 and not is_major
            tick_len   = 10 if is_major else (6 if is_mid else 3)
            tick_width = 1.5 if is_major else 0.8
            col        = ACCENT if is_major else (DIM if is_mid else QColor(15, 50, 25))
            rad = math.radians(deg - 90)
            x1 = (R - 2) * math.cos(rad)
            y1 = (R - 2) * math.sin(rad)
            x2 = (R - 2 - tick_len) * math.cos(rad)
            y2 = (R - 2 - tick_len) * math.sin(rad)
            p.setPen(QPen(col, tick_width))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Cardinal labels
        cardinals = [("N", 0, RED), ("E", 90, ACCENT), ("S", 180, ACCENT), ("W", 270, ACCENT)]
        label_r = R - 20
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        for name, deg, col in cardinals:
            rad = math.radians(deg - 90)
            lx = label_r * math.cos(rad)
            ly = label_r * math.sin(rad)
            p.setPen(QPen(col, 1))
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(name)
            p.drawText(QPointF(lx - tw / 2, ly + 4), name)

        p.restore()

        # ── North arrow (always points up, rotates with map) ─────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._current)

        # N arrow (red, pointing up)
        arrow_n = QPainterPath()
        arrow_n.moveTo(0, -(R - 22))
        arrow_n.lineTo(-7, 8)
        arrow_n.lineTo(0, 4)
        arrow_n.lineTo(7, 8)
        arrow_n.closeSubpath()
        p.fillPath(arrow_n, QBrush(RED))

        # S arrow (green, pointing down)
        arrow_s = QPainterPath()
        arrow_s.moveTo(0, R - 22)
        arrow_s.lineTo(-5, -6)
        arrow_s.lineTo(0, -2)
        arrow_s.lineTo(5, -6)
        arrow_s.closeSubpath()
        p.fillPath(arrow_s, QBrush(QColor(0, 200, 80, 150)))

        p.restore()

        # ── Centre hub ────────────────────────────────────────────────────
        p.setBrush(QBrush(QColor(8, 18, 12)))
        p.setPen(QPen(ACCENT, 1.5))
        p.drawEllipse(QPointF(cx, cy), 6, 6)

        p.end()
