"""
tile_map_widget.py
Floating, draggable, resizable minimap with live OpenStreetMap tiles.

Features:
  - Real OSM tiles fetched in background thread
  - Disk cache at backend/tile_cache/ (tiles valid 7 days)
  - Drag to reposition anywhere in the parent window
  - Resize via bottom-right corner grip
  - Zoom in/out with scroll wheel
  - Drone arrow + GPS trail overlay
"""

import math
import os
import time
import hashlib
from pathlib import Path
from collections import deque, OrderedDict
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtWidgets import QWidget, QSizeGrip, QVBoxLayout, QLabel, QHBoxLayout, QApplication
from PyQt6.QtCore    import Qt, QThread, pyqtSignal, QPoint, QPointF, QRectF, QSize, QTimer
from PyQt6.QtGui     import (
    QPainter, QPen, QBrush, QColor, QPixmap, QFont,
    QPainterPath, QImage, QCursor
)

# ── Tile cache dirs ───────────────────────────────────────────────────────────
CACHE_DIR   = Path(__file__).parent.parent / "backend" / "tile_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TILE_TTL    = 7 * 24 * 3600   # 7 days
TILE_SIZE   = 256
MEM_CACHE_MAX = 256

OSM_URL     = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT  = "InterceptorGCS/2.0 (github.com/AmanSah17/Interceptor_GUI)"

ACCENT  = QColor(21,  101, 192)
TRAIL   = QColor(21,  101, 192, 100)
DRONE   = QColor(21,  101, 192)
HOME_C  = QColor(230, 100,   0)
TEXT_D  = QColor(92,  112, 153)


# ─────────────────────────────────────────────────────────────────────────────
# Math helpers
# ─────────────────────────────────────────────────────────────────────────────
def _lat_lon_to_tile(lat, lon, zoom):
    n   = 1 << zoom
    tx  = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    ty  = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return tx, ty

def _tile_nw_lat_lon(tx, ty, zoom):
    n    = 1 << zoom
    lon  = tx / n * 360.0 - 180.0
    lat  = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / n))))
    return lat, lon

def _lat_lon_to_pixel(lat, lon, zoom, tile_x, tile_y):
    """Pixel offset within a tile grid anchored at (tile_x, tile_y)."""
    n       = 1 << zoom
    px_x    = (lon + 180.0) / 360.0 * n * TILE_SIZE - tile_x * TILE_SIZE
    lat_r   = math.radians(lat)
    py_y    = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n * TILE_SIZE - tile_y * TILE_SIZE
    return px_x, py_y


# ─────────────────────────────────────────────────────────────────────────────
# Tile fetcher thread
# ─────────────────────────────────────────────────────────────────────────────
class TileFetcher(QThread):
    tile_ready = pyqtSignal(int, int, int, QPixmap)   # z, x, y, pixmap

    def __init__(self):
        super().__init__()
        self._queue   : list[tuple[int,int,int]] = []
        self._fetched : set[tuple[int,int,int]]  = set()
        self._running = True

    def request_tile(self, z: int, x: int, y: int):
        key = (z, x, y)
        if key not in self._fetched:
            self._fetched.add(key)
            self._queue.append(key)

    def run(self):
        while self._running:
            if not self._queue:
                self.msleep(30)
                continue
            z, x, y = self._queue.pop(0)
            px = self._load_tile(z, x, y)
            if px:
                self.tile_ready.emit(z, x, y, px)

    def _load_tile(self, z, x, y) -> QPixmap | None:
        cache_path = CACHE_DIR / str(z) / str(x) / f"{y}.png"
        # Check disk cache
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < TILE_TTL:
                px = QPixmap()
                px.load(str(cache_path))
                if not px.isNull():
                    return px
        # Fetch from network
        url = OSM_URL.format(z=z, x=x, y=y)
        try:
            req  = Request(url, headers={"User-Agent": USER_AGENT})
            data = urlopen(req, timeout=8).read()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            img  = QImage.fromData(data)
            return QPixmap.fromImage(img) if not img.isNull() else None
        except Exception:
            return None

    def stop(self):
        self._running = False
        self.wait(1000)


# ─────────────────────────────────────────────────────────────────────────────
# Floating map widget
# ─────────────────────────────────────────────────────────────────────────────
class FloatingMapWidget(QWidget):
    """
    Minimap overlay window (fixed size).
    Parent should be the VideoPanel.
    """
    MIN_W, MIN_H = 260, 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(self.MIN_W, self.MIN_H)

        if parent:
            pw, ph = parent.width(), parent.height()
            self.move(pw - self.width() - 16, ph - self.height() - 16)

        self._tile_cache : OrderedDict[tuple, QPixmap] = OrderedDict()
        self._trail      : deque[tuple[float,float]]   = deque(maxlen=400)
        self._lat        : float | None = None
        self._lon        : float | None = None
        self._heading    : float = 0.0
        self._home_lat   : float | None = None
        self._home_lon   : float | None = None
        self._zoom       : int   = 16
        self._loading    : bool  = False

        # Tile fetcher
        self._fetcher = TileFetcher()
        self._fetcher.tile_ready.connect(self._on_tile_ready)
        self._fetcher.start()

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    # ── Public API ────────────────────────────────────────────────────────────
    def update_position(self, lat: float, lon: float, heading: float):
        if self._home_lat is None:
            self._home_lat, self._home_lon = lat, lon
        self._lat, self._lon, self._heading = lat, lon, heading
        self._trail.append((lat, lon))
        self._request_tiles()
        self.update()

    # ── Tile management ───────────────────────────────────────────────────────
    def _request_tiles(self):
        if self._lat is None:
            return
        z     = self._zoom
        cx, cy = _lat_lon_to_tile(self._lat, self._lon, z)
        W, H  = self.width(), self.height()
        r     = math.ceil(max(W, H) / (2 * TILE_SIZE)) + 1
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                tx, ty = cx + dx, cy + dy
                if (z, tx, ty) not in self._tile_cache:
                    self._fetcher.request_tile(z, tx, ty)

    def _on_tile_ready(self, z: int, x: int, y: int, px: QPixmap):
        if z != self._zoom:
            return
        key = (z, x, y)
        self._tile_cache[key] = px
        # LRU eviction
        while len(self._tile_cache) > MEM_CACHE_MAX:
            self._tile_cache.popitem(last=False)
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        W, H = self.width(), self.height()
        map_y = 0
        map_h = H

        p.fillRect(0, 0, W, H, QColor("#E8EEF8"))

        if self._lat is None:
            p.setPen(QPen(TEXT_D, 1))
            p.setFont(QFont("Consolas", 9))
            p.drawText(QRectF(0, 0, W, H),
                       Qt.AlignmentFlag.AlignCenter, "GPS ACQUIRING…")
            
            p.setPen(QPen(QColor(0, 255, 136, 180), 2))
            p.setBrush(QBrush(QColor(0, 0, 0, 0)))
            p.drawRect(1, 1, W - 2, H - 2)
            p.end()
            return

        # ── Tile rendering ─────────────────────────────────────────────────
        z     = self._zoom
        cx, cy = _lat_lon_to_tile(self._lat, self._lon, z)
        # Pixel offset of centre lat/lon within the centre tile
        nw_lat, nw_lon = _tile_nw_lat_lon(cx, cy, z)
        offset_x, offset_y = _lat_lon_to_pixel(self._lat, self._lon, z, cx, cy)

        # Where the drone sits on screen (centre of map area)
        screen_cx = W // 2
        screen_cy = map_y + map_h // 2

        r = math.ceil(max(W, H) / (2 * TILE_SIZE)) + 1
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                tx, ty = cx + dx, cy + dy
                key    = (z, tx, ty)
                tile_screen_x = screen_cx + (dx * TILE_SIZE) - int(offset_x)
                tile_screen_y = screen_cy + (dy * TILE_SIZE) - int(offset_y)
                if tx < 0 or ty < 0:
                    continue
                if key in self._tile_cache:
                    p.drawPixmap(tile_screen_x, tile_screen_y,
                                 TILE_SIZE, TILE_SIZE, self._tile_cache[key])
                else:
                    p.fillRect(tile_screen_x, tile_screen_y, TILE_SIZE, TILE_SIZE,
                               QColor(200, 215, 235))
                    p.setPen(QPen(QColor(180, 200, 220), 1))
                    p.drawRect(tile_screen_x, tile_screen_y, TILE_SIZE, TILE_SIZE)

        # ── Clip map area ─────────────────────────────────────────────────
        p.setClipRect(0, map_y, W, map_h)

        # ── GPS trail ─────────────────────────────────────────────────────
        if len(self._trail) > 1:
            pts = list(self._trail)
            path = QPainterPath()
            first = True
            for lat, lon in pts:
                px_x = screen_cx + (_lat_lon_to_pixel(lat, lon, z, cx, cy)[0] - offset_x)
                px_y = screen_cy + (_lat_lon_to_pixel(lat, lon, z, cx, cy)[1] - offset_y)
                if first:
                    path.moveTo(px_x, px_y)
                    first = False
                else:
                    path.lineTo(px_x, px_y)
            pen = QPen(TRAIL, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(0, 0, 0, 0)))
            p.drawPath(path)

        # ── Home marker ───────────────────────────────────────────────────
        if self._home_lat is not None:
            hx = screen_cx + (_lat_lon_to_pixel(self._home_lat, self._home_lon, z, cx, cy)[0] - offset_x)
            hy = screen_cy + (_lat_lon_to_pixel(self._home_lat, self._home_lon, z, cx, cy)[1] - offset_y)
            p.setBrush(QBrush(HOME_C))
            p.setPen(QPen(QColor(255, 255, 255), 1.5))
            p.drawEllipse(QPointF(hx, hy), 7, 7)
            p.setPen(QPen(HOME_C, 1))
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(int(hx + 9), int(hy + 4), "HOME")

        # ── Drone arrow (always screen centre since map follows drone) ────
        p.save()
        p.translate(screen_cx, screen_cy)
        p.rotate(self._heading)
        arrow = QPainterPath()
        arrow.moveTo(0, -14)
        arrow.lineTo(-7, 9)
        arrow.lineTo(0, 5)
        arrow.lineTo(7, 9)
        arrow.closeSubpath()
        p.fillPath(arrow, QBrush(ACCENT))
        p.setPen(QPen(QColor(255, 255, 255), 1.5))
        p.drawPath(arrow)
        p.restore()

        # ── Scale bar ─────────────────────────────────────────────────────
        # metres per pixel at this zoom+lat
        lat_r   = math.radians(self._lat)
        m_per_px = 156543.0 * math.cos(lat_r) / (1 << z)
        bar_m    = 100 if m_per_px < 5 else 500
        bar_px   = int(bar_m / m_per_px)
        bx, by   = 10, H - 18
        p.setPen(QPen(QColor(40, 60, 120), 2))
        p.drawLine(bx, by, bx + bar_px, by)
        p.drawLine(bx, by - 4, bx, by + 4)
        p.drawLine(bx + bar_px, by - 4, bx + bar_px, by + 4)
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor(40, 60, 120), 1))
        p.drawText(bx + bar_px // 2 - 12, by - 5, f"{bar_m} m")

        p.setClipping(False)

        # ── Border ────────────────────────────────────────────────────────
        p.setPen(QPen(QColor(0, 255, 136, 180), 2))
        p.setBrush(QBrush(QColor(0, 0, 0, 0)))
        p.drawRect(1, 1, W - 2, H - 2)
        p.end()

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        if delta > 0:
            self._zoom = min(19, self._zoom + 1)
        else:
            self._zoom = max(10, self._zoom - 1)
        self._tile_cache.clear()
        self._fetcher._fetched.clear()
        self._request_tiles()
        self.update()

    def stop(self):
        self._fetcher.stop()
