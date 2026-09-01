"""
run_app.py
Interceptor GCS — Application launcher.

Usage:
    D:\\CUDA_ENV\\CUDA_ENV\\Scripts\\python.exe run_app.py
"""

import sys
import os

# Ensure the app/ and backend/ directories are importable
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'app'))
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QIcon, QFont

# Initialise database before anything else
import database as db
db.init_db()
db.start_session()

from main_window import MainWindow
from theme       import apply_palette, STYLESHEET


def main():
    # High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Interceptor GCS")
    app.setOrganizationName("Interceptor UAV")
    app.setApplicationVersion("2.0.0")

    # Apply dark theme
    apply_palette(app)
    app.setStyleSheet(STYLESHEET)

    # System font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    code = app.exec()
    sys.exit(code)


if __name__ == "__main__":
    main()
