"""
theme.py  —  White & Blue professional theme for Interceptor GCS.
"""
from PyQt6.QtGui import QColor, QPalette

# ── Palette ────────────────────────────────────────────────────────────────
BG_BASE     = "#DDE8F8"   # light blue-white wash (main window bg)
BG_PANEL    = "#FFFFFF"   # pure white panels / cards
BG_HEADER   = "#0D2137"   # dark navy header
BG_CARD     = "#F4F8FF"   # faint-blue card tint
BG_VIDEO    = "#060A10"   # keep video area dark

ACCENT      = "#1565C0"   # cobalt blue (primary accent)
ACCENT_BRT  = "#2979FF"   # bright blue (hover / glow)
ACCENT_LITE = "#E8F0FE"   # very light blue (chip bg)

AUTO_COL    = "#1565C0"   # AUTONOMOUS  → blue
AUTO_BG     = "#E3F0FF"   # AUTONOMOUS bg strip
MANUAL_COL  = "#E65100"   # MANUAL → deep orange
MANUAL_BG   = "#FFF3E0"   # MANUAL bg strip

AMBER       = "#F57C00"
DANGER      = "#C62828"
SUCCESS     = "#2E7D32"

TEXT_HEADER = "#FFFFFF"   # text on dark header
TEXT_PRI    = "#0D1B3E"   # dark navy on white
TEXT_DIM    = "#5C7099"   # blue-grey dim

BORDER      = "rgba(21, 101, 192, 0.20)"
BORDER_MED  = "rgba(21, 101, 192, 0.40)"


def apply_palette(app):
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,         QColor(BG_BASE))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_PRI))
    p.setColor(QPalette.ColorRole.Base,            QColor(BG_PANEL))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.Text,            QColor(TEXT_PRI))
    p.setColor(QPalette.ColorRole.Button,          QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(ACCENT))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.Link,            QColor(ACCENT_BRT))
    app.setPalette(p)


STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 6px; border: none; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {ACCENT};
    border-radius: 3px; min-height: 20px;
    opacity: 0.5;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Card panels ─────────────────────────────────────────────────────────── */
QFrame#panelCard {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* ── Progress bar (battery) ─────────────────────────────────────────────── */
QProgressBar {{
    background: #D0DCF0;
    border: none;
    border-radius: 3px;
    height: 7px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

/* ── List widget (detections) ───────────────────────────────────────────── */
QListWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: {TEXT_PRI};
}}
QListWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {BORDER};
}}
QListWidget::item:selected {{
    background: {ACCENT_LITE};
    color: {ACCENT};
}}

/* ── Status bar ─────────────────────────────────────────────────────────── */
QStatusBar {{
    background: {BG_HEADER};
    color: rgba(255,255,255,0.55);
    font-family: "Consolas", monospace;
    font-size: 9px;
    letter-spacing: 1px;
    border-top: 1px solid rgba(255,255,255,0.08);
}}

/* ── Tooltip ────────────────────────────────────────────────────────────── */
QToolTip {{
    background: {BG_HEADER};
    color: white;
    border: 1px solid {ACCENT};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}
"""
