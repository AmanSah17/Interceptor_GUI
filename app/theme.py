"""
theme.py
Dark military QSS stylesheet + QPalette for Interceptor GCS.
"""
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt


ACCENT         = "#00ff88"
ACCENT_DIM     = "#00cc6a"
AMBER          = "#ffb300"
DANGER         = "#ff3355"
BLUE_AUTO      = "#00aaff"
BG_BASE        = "#05070a"
BG_PANEL       = "#0a0e14"
BG_CARD        = "#0d1219"
TEXT_PRIMARY   = "#e0ffe8"
TEXT_DIM       = "#4a7060"
BORDER         = "rgba(0,255,136,0.18)"


def apply_palette(app):
    """Apply a dark QPalette to the entire application."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(BG_BASE))
    p.setColor(QPalette.ColorRole.WindowText,       QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Base,             QColor(BG_PANEL))
    p.setColor(QPalette.ColorRole.AlternateBase,    QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.ToolTipBase,      QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.ToolTipText,      QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Text,             QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Button,           QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.ButtonText,       QColor(ACCENT))
    p.setColor(QPalette.ColorRole.BrightText,       QColor(ACCENT))
    p.setColor(QPalette.ColorRole.Link,             QColor(ACCENT))
    p.setColor(QPalette.ColorRole.Highlight,        QColor(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText,  QColor(BG_BASE))
    app.setPalette(p)


STYLESHEET = f"""
/* ── Global ── */
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Consolas", monospace;
    font-size: 13px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: {BG_BASE};
    width: 6px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #1a3a28;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Panel cards ── */
#panelCard {{
    background: {BG_CARD};
    border: 1px solid rgba(0,255,136,0.15);
    border-radius: 4px;
}}

/* ── Panel title labels ── */
.panelTitle {{
    color: {TEXT_DIM};
    font-size: 9px;
    letter-spacing: 3px;
    text-transform: uppercase;
}}

/* ── Telemetry value labels ── */
.telemValue {{
    color: {ACCENT};
    font-family: "Consolas", monospace;
    font-size: 28px;
    font-weight: bold;
}}

.telemUnit {{
    color: {TEXT_DIM};
    font-size: 9px;
    letter-spacing: 2px;
}}

.telemLabel {{
    color: {TEXT_DIM};
    font-size: 9px;
    letter-spacing: 2px;
}}

/* ── Mode toggle button ── */
#modeButton {{
    font-family: "Consolas", monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 6px 20px;
    border-radius: 3px;
    border: 1px solid;
    cursor: pointer;
    min-width: 160px;
}}

#modeButton[mode="AUTONOMOUS"] {{
    color: {BLUE_AUTO};
    border-color: {BLUE_AUTO};
    background: rgba(0,170,255,0.10);
}}

#modeButton[mode="AUTONOMOUS"]:hover {{
    background: rgba(0,170,255,0.20);
}}

#modeButton[mode="MANUAL"] {{
    color: {AMBER};
    border-color: {AMBER};
    background: rgba(255,179,0,0.10);
}}

#modeButton[mode="MANUAL"]:hover {{
    background: rgba(255,179,0,0.22);
}}

#modeButton:pressed {{
    opacity: 0.7;
}}

/* ── Connection status ── */
#connLabel {{
    font-family: "Consolas", monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: {TEXT_DIM};
}}

/* ── Status bar ── */
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    font-family: "Consolas", monospace;
    font-size: 9px;
    border-top: 1px solid rgba(0,255,136,0.12);
}}

/* ── Battery bar ── */
QProgressBar {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(0,255,136,0.12);
    border-radius: 2px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    border-radius: 2px;
    background: {ACCENT};
}}

QProgressBar[level="mid"]::chunk {{ background: {AMBER}; }}
QProgressBar[level="low"]::chunk {{ background: {DANGER}; }}

/* ── Detection list ── */
QListWidget {{
    background: transparent;
    border: none;
    font-family: "Consolas", monospace;
    font-size: 10px;
}}

QListWidget::item {{
    background: rgba(0,255,136,0.04);
    border: 1px solid rgba(0,255,136,0.10);
    border-radius: 3px;
    padding: 4px 8px;
    margin: 1px 0;
    color: {TEXT_PRIMARY};
}}

QListWidget::item:selected {{
    background: rgba(0,255,136,0.12);
    border-color: {ACCENT};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: rgba(0,255,136,0.08);
    width: 4px;
    height: 4px;
}}

/* ── Header bar ── */
#headerBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid rgba(0,255,136,0.15);
}}

#brandTitle {{
    font-family: "Consolas", monospace;
    font-size: 16px;
    font-weight: bold;
    color: {ACCENT};
    letter-spacing: 4px;
}}

#brandSubtitle {{
    font-family: "Consolas", monospace;
    font-size: 8px;
    color: {TEXT_DIM};
    letter-spacing: 3px;
}}

#clockLabel {{
    font-family: "Consolas", monospace;
    font-size: 13px;
    color: {TEXT_DIM};
    letter-spacing: 2px;
}}
"""
