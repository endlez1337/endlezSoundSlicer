"""Start the small endlez Sound Slicer desktop editor."""

import sys
from pathlib import Path


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
        from soundslice.window import EditorWindow
        from soundslice.style import STYLESHEET, app_icon, configure_fonts
    except ImportError as error:
        print(f"Abhängigkeit fehlt: {error}\nBitte zuerst: python -m pip install -r requirements.txt")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("endlez Sound Slicer")
    app.setOrganizationName("endlez")
    app.setStyle("Fusion")
    configure_fonts(app)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(app_icon())
    window = EditorWindow()
    window.show()
    if len(sys.argv) > 1:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: window.open_path(Path(sys.argv[1])))
    try:
        return app.exec()
    finally:
        window.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
