"""
minimap_widget.py
GPS trail minimap drawn via QPainter.
Shows drone position as an arrow + historical trail as a polyline.
Works fully offline — no tiles, pure coordinate rendering.
"""
import math
from collections import deque
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore    import Qt, QPointF, QRectF
from PyQt6.QtGui     import (
    QPainter, QPen, QBrush, QColor, QFont,
    QPainterPath, QLinearGradient, QPolygonF
)

ACCENT   = QColor(0,  255, 136)
TRAIL    = QColor(0,  255, 136, 80)
GRID_COL = QColor(0,  255, 136, 18)
BG_DARK  = QColor(5,  12,   8)
BG_MID   = QColor(8,  18,  12)
HOME_COL = QColor(255, 200, 50)
TEXT_DIM = QColor(50, 120,  70)

TRAIL_MAX = 300


class MinimapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 180)

        self._trail   : deque[tuple[float, float]] = deque(maxlen=TRAIL_MAX)
        self._lat     : float | None = None
        self._lon     : float | None = None
        self._heading : float = 0.0
        self._home_lat: float | None = None
        self._home_lon: float | None = None
        self._zoom    : float = 0.0005   # degrees per half-widget dimension

    def update_position(self, lat: float, lon: float, heading: float):
        if self._home_lat is None:
            self._home_lat, self._home_lon = lat, lon
        self._lat     = lat
        self._lon     = lon
        self._heading = heading
        self._trail.append((lat, lon))
        self.update()

    # ── GPS → pixel coordinate ────────────────────────────────────────────────
    def _to_px(self, lat: float, lon: float, W: int, H: int) -> QPointF:
        if self._lat is None:
            return QPointF(W / 2, H / 2)
        dlat = lat - self._lat
        dlon = lon - self._lon
        # Scale: 1 deg lat ≈ 111 320 m, 1 deg lon ≈ 111 320 * cos(lat) m
        scale_lat = (H / 2) / (self._zoom + 1e-9)
        scale_lon = (W / 2) / (self._zoom + 1e-9)
        px = W / 2 + dlon * scale_lon
        py = H / 2 - dlat * scale_lat
        return QPointF(px, py)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # ── Background ───────────────────────────────────────────────────────
        p.fillRect(0, 0, W, H, BG_DARK)

        # ── Grid ─────────────────────────────────────────────────────────────
        p.setPen(QPen(GRID_COL, 0.6))
        step = max(20, min(60, W // 6))
        for x in range(0, W, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H, step):
            p.drawLine(0, y, W, y)

        if self._lat is None:
            p.setPen(QPen(TEXT_DIM, 1))
            p.setFont(QFont("Consolas", 9))
            p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter,
                       "GPS ACQUIRING…")
            p.end()
            return

        # ── Compass rose (mini, top-right) ───────────────────────────────────
        self._draw_mini_compass_ref(p, W, H)

        # ── GPS trail ────────────────────────────────────────────────────────
        if len(self._trail) > 1:
            trail_list = list(self._trail)
            path = QPainterPath()
            pt0 = self._to_px(*trail_list[0], W, H)
            path.moveTo(pt0)
            for pt in trail_list[1:]:
                px = self._to_px(*pt, W, H)
                path.lineTo(px)
            p.setPen(QPen(TRAIL, 1.5))
            p.setBrush(QBrush(QColor(0, 0, 0, 0)))
            p.drawPath(path)

        # ── Home marker ──────────────────────────────────────────────────────
        if self._home_lat is not None:
            hpx = self._to_px(self._home_lat, self._home_lon, W, H)
            p.setPen(QPen(HOME_COL, 1))
            p.setBrush(QBrush(HOME_COL))
            p.drawEllipse(hpx, 4, 4)
            p.setFont(QFont("Consolas", 7))
            p.drawText(QPointF(hpx.x() + 6, hpx.y() + 4), "HOME")

        # ── Drone arrow ──────────────────────────────────────────────────────
        drone_px = self._to_px(self._lat, self._lon, W, H)
        p.save()
        p.translate(drone_px)
        p.rotate(self._heading)
        arrow = QPainterPath()
        arrow.moveTo(0, -12)
        arrow.lineTo(-6, 8)
        arrow.lineTo(0, 5)
        arrow.lineTo(6, 8)
        arrow.closeSubpath()
        p.fillPath(arrow, QBrush(ACCENT))
        p.setPen(QPen(QColor(0, 0, 0, 180), 0.8))
        p.drawPath(arrow)
        p.restore()

        # ── Range ring ───────────────────────────────────────────────────────
        ring_deg  = 0.0002   # ~22 m radius ring
        ring_px_r = ring_deg / (self._zoom + 1e-9) * (W / 2)
        p.setPen(QPen(QColor(0, 255, 136, 25), 1))
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        p.drawEllipse(drone_px, ring_px_r, ring_px_r)

        # ── GPS coordinates ───────────────────────────────────────────────────
        p.setPen(QPen(TEXT_DIM, 1))
        p.setFont(QFont("Consolas", 7))
        p.drawText(4, H - 14,
                   f"LAT {self._lat:.5f}  LON {self._lon:.5f}")

        p.end()

    def _draw_mini_compass_ref(self, p: QPainter, W: int, H: int):
        cx, cy, R = W - 18, 18, 12
        p.setPen(QPen(QColor(0, 255, 136, 50), 1))
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        p.drawEllipse(QPointF(cx, cy), R, R)
        p.setPen(QPen(QColor(255, 51, 85, 160), 1.5))
        p.drawLine(int(cx), int(cy), int(cx), int(cy - R + 2))
        p.setPen(QPen(TEXT_DIM, 1))
        p.setFont(QFont("Consolas", 6))
        p.drawText(int(cx - 3), int(cy - R - 2), "N")
