"""
main_window.py
Interceptor GCS — Main application window.

Layout
------
  ┌─ Header bar ──────────────────────────────────────────────────┐
  │  INTERCEPTOR logo | [MODE TOGGLE] | Clock | Connection status  │
  ├─ Video Panel (left 65%) ────┬─ Sidebar (right 35%) ───────────┤
  │                              │  Flight Telemetry cards         │
  │  Live camera feed            │  Compass rose                   │
  │  Bounding boxes              │  Detection list                 │
  │  Artificial horizon          │  Minimap                        │
  │                              │                                 │
  └──────────────────────────────┴─────────────────────────────────┤
  │ Status bar: GPS | Distance | Mode | UTC                        │
  └────────────────────────────────────────────────────────────────┘
"""

import sys
import math
import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QSizePolicy, QStatusBar, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore    import Qt, QTimer, pyqtSlot
from PyQt6.QtGui     import QColor, QFont, QIcon, QPalette

# Local widgets
from video_panel      import VideoPanel
from compass_widget   import CompassWidget
from minimap_widget   import FloatingMapWidget as MinimapWidget
from workers          import TelemetryWorker, VideoWorker

# Backend
import sys as _sys
import pathlib
_sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'backend'))
from telemetry_sim import set_mode, get_mode
import database as db


ACCENT  = "#00ff88"
AMBER   = "#ffb300"
DANGER  = "#ff3355"
BLUE    = "#00aaff"
TEXT_DIM = "#4a7060"
BG_CARD  = "#0d1219"
BG_PANEL = "#0a0e14"


def _label(text: str, style: str = "", size: int = 0) -> QLabel:
    lbl = QLabel(text)
    if style:
        lbl.setStyleSheet(style)
    if size:
        f = lbl.font()
        f.setPointSize(size)
        lbl.setFont(f)
    return lbl


def _card(parent=None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("panelCard")
    frame.setStyleSheet(f"""
        QFrame#panelCard {{
            background: {BG_CARD};
            border: 1px solid rgba(0,255,136,0.14);
            border-radius: 4px;
        }}
    """)
    return frame


class TelemetryCard(QFrame):
    """Single telemetry metric card."""
    def __init__(self, label: str, unit: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid rgba(0,255,136,0.3);
                border-radius: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(1)

        self._lbl_label = QLabel(label)
        self._lbl_label.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;"
        )
        self._lbl_value = QLabel("---")
        self._lbl_value.setStyleSheet(
            f"color:{ACCENT};font-family:Consolas;font-size:26px;font-weight:bold;"
        )
        self._lbl_unit = QLabel(unit)
        self._lbl_unit.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;"
        )

        layout.addWidget(self._lbl_label)
        layout.addWidget(self._lbl_value)
        layout.addWidget(self._lbl_unit)

    def set_value(self, val: str, colour: str = ACCENT):
        self._lbl_value.setText(val)
        self._lbl_value.setStyleSheet(
            f"color:{colour};font-family:Consolas;font-size:26px;font-weight:bold;"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INTERCEPTOR  —  Ground Control Station")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 860)
        self._build_ui()
        self._start_workers()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    # =========================================================================
    # UI Construction
    # =========================================================================
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_main(), stretch=1)

        self.setCentralWidget(root)
        self._build_statusbar()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background:{BG_PANEL};border-bottom:1px solid rgba(0,255,136,0.15);")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)

        # Brand
        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = QLabel("INTERCEPTOR")
        title.setStyleSheet(
            f"color:{ACCENT};font-family:Consolas;font-size:17px;"
            f"font-weight:bold;letter-spacing:5px;"
        )
        sub = QLabel("GROUND CONTROL STATION  v2.0")
        sub.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:8px;letter-spacing:3px;"
        )
        brand.addWidget(title)
        brand.addWidget(sub)
        layout.addLayout(brand)

        layout.addStretch()

        # Mode toggle button
        self._mode_btn = QPushButton("⏵  AUTONOMOUS")
        self._mode_btn.setObjectName("modeButton")
        self._mode_btn.setFixedSize(190, 34)
        self._mode_btn.clicked.connect(self._toggle_mode)
        self._mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_mode_style("AUTONOMOUS")
        layout.addWidget(self._mode_btn)

        layout.addSpacing(24)

        # Clock
        self._clock_lbl = QLabel("--:--:--")
        self._clock_lbl.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:13px;letter-spacing:2px;"
        )
        layout.addWidget(self._clock_lbl)

        layout.addSpacing(24)

        # Connection indicator
        conn_row = QHBoxLayout()
        conn_row.setSpacing(6)
        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet(f"color:{DANGER};font-size:10px;")
        self._conn_lbl = QLabel("OFFLINE")
        self._conn_lbl.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;"
        )
        conn_row.addWidget(self._conn_dot)
        conn_row.addWidget(self._conn_lbl)
        layout.addLayout(conn_row)

        return bar

    # ── Main area ─────────────────────────────────────────────────────────────
    def _build_main(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Video panel (left, larger)
        self._video = VideoPanel()
        layout.addWidget(self._video, stretch=65)

        # Floating Minimap over video panel
        self._minimap = MinimapWidget(self._video)

        # Sidebar (right)
        sidebar = self._build_sidebar()
        layout.addWidget(sidebar, stretch=35)

        return container

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(6)

        # ── Telemetry grid ─────────────────────────────────────────────────
        telem_card = _card()
        telem_layout = QVBoxLayout(telem_card)
        telem_layout.setContentsMargins(10, 8, 10, 10)
        telem_layout.setSpacing(6)

        title_lbl = QLabel("▌ FLIGHT TELEMETRY")
        title_lbl.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:3px;"
        )
        telem_layout.addWidget(title_lbl)

        # 2-column grid of metric cards
        grid_widget = QWidget()
        grid = QHBoxLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        right_col = QVBoxLayout()
        right_col.setSpacing(4)

        self._card_alt     = TelemetryCard("ALTITUDE",  "METRES AGL")
        self._card_speed   = TelemetryCard("SPEED",     "KM/H")
        self._card_heading = TelemetryCard("HEADING",   "DEGREES")
        self._card_vspeed  = TelemetryCard("V · SPEED", "M/S")

        left_col.addWidget(self._card_alt)
        left_col.addWidget(self._card_heading)
        right_col.addWidget(self._card_speed)
        right_col.addWidget(self._card_vspeed)

        grid.addLayout(left_col)
        grid.addLayout(right_col)
        telem_layout.addWidget(grid_widget)

        # Battery
        batt_row = QWidget()
        batt_layout = QVBoxLayout(batt_row)
        batt_layout.setContentsMargins(0, 0, 0, 0)
        batt_layout.setSpacing(2)
        batt_top = QHBoxLayout()
        batt_lbl = QLabel("BATTERY")
        batt_lbl.setStyleSheet(f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;")
        self._batt_val = QLabel("---%")
        self._batt_val.setStyleSheet(f"color:{ACCENT};font-family:Consolas;font-size:20px;font-weight:bold;")
        batt_top.addWidget(batt_lbl)
        batt_top.addStretch()
        batt_top.addWidget(self._batt_val)
        self._batt_bar = QProgressBar()
        self._batt_bar.setRange(0, 100)
        self._batt_bar.setValue(100)
        self._batt_bar.setTextVisible(False)
        self._batt_bar.setFixedHeight(6)
        self._batt_bar.setStyleSheet(f"""
            QProgressBar {{ background:rgba(255,255,255,0.05); border:1px solid rgba(0,255,136,0.12);
                           border-radius:2px; }}
            QProgressBar::chunk {{ background:{ACCENT}; border-radius:2px; }}
        """)
        batt_layout.addLayout(batt_top)
        batt_layout.addWidget(self._batt_bar)
        telem_layout.addWidget(batt_row)

        # Signal
        sig_row = QHBoxLayout()
        sig_lbl = QLabel("SIGNAL")
        sig_lbl.setStyleSheet(f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;")
        self._sig_val = QLabel("---%")
        self._sig_val.setStyleSheet(f"color:{ACCENT};font-family:Consolas;font-size:20px;font-weight:bold;")
        sig_row.addWidget(sig_lbl)
        sig_row.addStretch()
        sig_row.addWidget(self._sig_val)
        telem_layout.addLayout(sig_row)

        layout.addWidget(telem_card)

        # ── Compass ────────────────────────────────────────────────────────
        compass_card = _card()
        comp_layout  = QVBoxLayout(compass_card)
        comp_layout.setContentsMargins(10, 8, 10, 10)
        comp_layout.setSpacing(4)
        comp_title = QLabel("▌ COMPASS")
        comp_title.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:3px;"
        )
        comp_layout.addWidget(comp_title)

        comp_row = QHBoxLayout()
        self._compass = CompassWidget()
        comp_row.addWidget(self._compass)
        comp_info = QVBoxLayout()
        comp_info.setSpacing(2)
        self._hdg_val = QLabel("000°")
        self._hdg_val.setStyleSheet(
            f"color:{ACCENT};font-family:Consolas;font-size:22px;font-weight:bold;"
        )
        self._hdg_dir = QLabel("N")
        self._hdg_dir.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:11px;letter-spacing:3px;"
        )
        comp_info.addStretch()
        comp_info.addWidget(self._hdg_val)
        comp_info.addWidget(self._hdg_dir)
        comp_info.addStretch()
        comp_row.addLayout(comp_info)
        comp_layout.addLayout(comp_row)

        layout.addWidget(compass_card)

        # ── Detection Table ────────────────────────────────────────────────
        det_card = _card()
        det_layout = QVBoxLayout(det_card)
        det_layout.setContentsMargins(10, 8, 10, 10)
        det_layout.setSpacing(4)
        det_title = QLabel("▌ ACTIVE DETECTIONS")
        det_title.setStyleSheet(
            f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:3px;"
        )
        det_layout.addWidget(det_title)
        
        self._det_table = QTableWidget(0, 3)
        self._det_table.setFixedHeight(120)
        self._det_table.setHorizontalHeaderLabels(["Target", "Conf", "Coords"])
        self._det_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._det_table.verticalHeader().setVisible(False)
        self._det_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._det_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._det_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._det_table.setStyleSheet(f"""
            QTableWidget {{
                background:transparent;
                border:1px solid rgba(0,255,136,0.15);
                font-family:Consolas;font-size:10px;color:#e0ffe8;
                gridline-color: rgba(0,255,136,0.1);
            }}
            QHeaderView::section {{
                background-color: {BG_CARD};
                color: {TEXT_DIM};
                border: 1px solid rgba(0,255,136,0.1);
                font-family:Consolas;font-size:9px;
            }}
            QTableWidget::item:selected {{
                background: rgba(0,255,136,0.2);
                color: #ffffff;
            }}
        """)
        det_layout.addWidget(self._det_table)
        layout.addWidget(det_card)

        inner.setLayout(layout)
        scroll.setWidget(inner)
        return scroll

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{ background:{BG_PANEL};color:{TEXT_DIM};
                          font-family:Consolas;font-size:9px;letter-spacing:2px;
                          border-top:1px solid rgba(0,255,136,0.12); }}
        """)
        self._sb_gps  = QLabel("GPS: ---.------- / ---.-------")
        self._sb_dist = QLabel("DIST: --- m")
        self._sb_mode = QLabel("MODE: ---")
        self._sb_time = QLabel("UTC --:--:--")
        for w in [self._sb_gps, self._sb_dist, self._sb_mode, self._sb_time]:
            w.setStyleSheet(f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;")
        sb.addWidget(self._sb_gps)
        sb.addPermanentWidget(self._sb_dist)
        sb.addPermanentWidget(self._sb_mode)
        sb.addPermanentWidget(self._sb_time)

    # =========================================================================
    # Workers
    # =========================================================================
    def _start_workers(self):
        # Telemetry
        self._telem_worker = TelemetryWorker()
        self._telem_worker.data_ready.connect(self._on_telemetry)
        self._telem_worker.start()

        # Video
        self._video_worker = VideoWorker()
        self._video_worker.frame_ready.connect(self._video.set_frame)
        self._video_worker.stream_status.connect(self._on_stream_status)
        self._video_worker.start()

    # =========================================================================
    # Slots
    # =========================================================================
    @pyqtSlot(bool, float)
    def _on_stream_status(self, connected: bool, fps: float):
        self._set_connected(connected, fps)
        self._video.set_stream_status(connected)

    @pyqtSlot(dict)
    def _on_telemetry(self, data: dict):
        alt  = data['altitude']
        spd  = data['speed']
        hdg  = data['heading']
        vs   = data['vspeed']
        batt = data['battery']
        sig  = data['signal']
        mode = data['mode']

        # Telemetry cards
        self._card_alt.set_value(f"{alt:.1f}")
        self._card_speed.set_value(f"{spd:.1f}")
        self._card_heading.set_value(f"{hdg:.1f}°")

        vs_col = ACCENT if vs >= 0 else DANGER
        self._card_vspeed.set_value(f"{'+' if vs>=0 else ''}{vs:.1f}", vs_col)

        # Battery
        batt_i = int(batt)
        self._batt_val.setText(f"{batt:.1f}%")
        self._batt_bar.setValue(batt_i)
        if batt > 50:
            batt_style = f"QProgressBar::chunk{{background:{ACCENT};border-radius:2px;}}"
        elif batt > 20:
            batt_style = f"QProgressBar::chunk{{background:{AMBER};border-radius:2px;}}"
        else:
            batt_style = f"QProgressBar::chunk{{background:{DANGER};border-radius:2px;}}"
        self._batt_bar.setStyleSheet(
            f"QProgressBar{{background:rgba(255,255,255,0.05);border:1px solid rgba(0,255,136,0.12);"
            f"border-radius:2px;}}" + batt_style
        )

        # Signal
        self._sig_val.setText(f"{int(sig*100)}%")

        # Mode badge
        self._apply_mode_style(mode)

        # Compass
        self._compass.set_heading(hdg)
        self._hdg_val.setText(f"{hdg:.0f}°".zfill(4))
        self._hdg_dir.setText(self._heading_to_dir(hdg))

        # Horizon in video panel
        pitch = max(-15.0, min(15.0, vs * 2.0))
        self._video.set_horizon(pitch, 0)

        # Bounding boxes
        self._video.set_boxes(data.get('boxes', []))

        # Detection table
        boxes = data.get('boxes', [])
        self._det_table.setRowCount(0)
        if boxes:
            self._det_table.setRowCount(len(boxes))
            for i, b in enumerate(boxes):
                t_item = QTableWidgetItem(f" {b['label']}")
                c_item = QTableWidgetItem(f"{int(b['conf']*100)}%")
                c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                xy_item = QTableWidgetItem(f"[{b['x']:.2f}, {b['y']:.2f}]")
                xy_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._det_table.setItem(i, 0, t_item)
                self._det_table.setItem(i, 1, c_item)
                self._det_table.setItem(i, 2, xy_item)

        # Minimap
        self._minimap.update_position(data['lat'], data['lon'], hdg)

        # Status bar
        self._sb_gps.setText(f"GPS: {data['lat']:.6f} / {data['lon']:.6f}")
        self._sb_dist.setText(f"DIST: {data['distance']:.0f} m")
        self._sb_mode.setText(f"MODE: {mode}")
        now = __import__('datetime').datetime.utcnow()
        self._sb_time.setText(f"UTC {now.strftime('%H:%M:%S')}")

    def _toggle_mode(self):
        current = get_mode()
        new_mode = "MANUAL" if current == "AUTONOMOUS" else "AUTONOMOUS"
        db.log_mode_change(current, new_mode)
        set_mode(new_mode)
        self._apply_mode_style(new_mode)

    def _apply_mode_style(self, mode: str):
        if mode == "AUTONOMOUS":
            self._mode_btn.setText("⏵  AUTONOMOUS")
            self._mode_btn.setStyleSheet(f"""
                QPushButton {{
                    color:{BLUE}; border:1px solid {BLUE};
                    background:rgba(0,170,255,0.10);
                    font-family:Consolas; font-size:11px; font-weight:bold;
                    letter-spacing:3px; padding:6px 20px; border-radius:3px;
                    min-width:175px;
                }}
                QPushButton:hover {{ background:rgba(0,170,255,0.20); }}
                QPushButton:pressed {{ background:rgba(0,170,255,0.30); }}
            """)
        else:
            self._mode_btn.setText("⏸  MANUAL")
            self._mode_btn.setStyleSheet(f"""
                QPushButton {{
                    color:{AMBER}; border:1px solid {AMBER};
                    background:rgba(255,179,0,0.10);
                    font-family:Consolas; font-size:11px; font-weight:bold;
                    letter-spacing:3px; padding:6px 20px; border-radius:3px;
                    min-width:175px;
                }}
                QPushButton:hover {{ background:rgba(255,179,0,0.22); }}
                QPushButton:pressed {{ background:rgba(255,179,0,0.35); }}
            """)

    def _set_connected(self, state: bool, fps: float = 0.0):
        if state:
            self._conn_dot.setStyleSheet(f"color:{ACCENT};font-size:10px;")
            self._conn_lbl.setText(f"LIVE ({int(fps)} FPS)")
            self._conn_lbl.setStyleSheet(f"color:{ACCENT};font-family:Consolas;font-size:9px;letter-spacing:2px;")
        else:
            self._conn_dot.setStyleSheet(f"color:{DANGER};font-size:10px;")
            self._conn_lbl.setText("OFFLINE / RECONNECTING")
            self._conn_lbl.setStyleSheet(f"color:{TEXT_DIM};font-family:Consolas;font-size:9px;letter-spacing:2px;")

    def _tick_clock(self):
        import datetime
        self._clock_lbl.setText(datetime.datetime.now().strftime("%H:%M:%S"))

    @staticmethod
    def _heading_to_dir(h: float) -> str:
        dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                'S','SSW','SW','WSW','W','WNW','NW','NNW']
        return dirs[round(h / 22.5) % 16]

    # =========================================================================
    # Cleanup
    # =========================================================================
    def closeEvent(self, event):
        self._telem_worker.stop()
        self._video_worker.stop()
        db.end_session()
        event.accept()
