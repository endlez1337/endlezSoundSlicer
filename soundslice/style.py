"""Restrained dark theme and small icons drawn using Qt only."""

import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def configure_fonts(app):
    # Some restricted Windows environments cannot enumerate system fonts.
    # Read the already installed fonts; do not ship copies or add a dependency.
    if os.name == "nt" and not QFontDatabase.families():
        font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "consola.ttf", "consolab.ttf"):
            try:
                QFontDatabase.addApplicationFontFromData(QByteArray((font_directory / name).read_bytes()))
            except OSError:
                pass
    if "Segoe UI" in QFontDatabase.families():
        app.setFont(QFont("Segoe UI", 10))


STYLESHEET = """
QWidget { background: #101317; color: #e8edf3; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow { background: #101317; }
QLabel { background: transparent; }
QLabel#brand { font-size: 23px; font-weight: 700; letter-spacing: -0.6px; }
QLabel#muted, QLabel#fileMeta, QLabel#hint { color: #8996a7; }
QLabel#fileName { font-size: 18px; font-weight: 600; }
QLabel#time { font-family: 'Consolas'; font-size: 24px; font-weight: 600; color: #ecf5f7; }
QLabel#totalTime { font-family: 'Consolas'; font-size: 14px; color: #8996a7; }
QLabel#selectionLength { color: #86dacb; font-family: 'Consolas'; }
QLabel#badge { color: #91ddcd; background: #1b3432; border-radius: 7px; padding: 5px 9px; }
QFrame#panel { background: #191e25; border: 1px solid #29313c; border-radius: 14px; }
QFrame#panel QLabel { background: transparent; }
QPushButton { background: #222a34; border: 1px solid #35404e; border-radius: 9px;
              padding: 10px 16px; font-weight: 600; min-height: 20px; }
QPushButton:hover { background: #2b3542; border-color: #56667a; }
QPushButton:pressed { background: #344152; }
QPushButton:focus { border-color: #7dcfc0; }
QPushButton:disabled { background: #1b2129; color: #626f80; border-color: #2a323c; }
QPushButton#primary { background: #85dccb; color: #112622; border-color: #85dccb; }
QPushButton#primary:hover { background: #a5eadc; border-color: #a5eadc; }
QPushButton#primary:pressed { background: #60c5b1; }
QPushButton#primary:disabled { background: #29443f; color: #668980; border-color: #29443f; }
QPushButton#small { padding: 7px 10px; font-size: 12px; }
QAbstractSpinBox { background: #11171e; border: 1px solid #35404e; border-radius: 8px;
                  padding: 10px 12px; min-height: 20px; font-family: 'Consolas'; font-size: 16px; }
QAbstractSpinBox:focus { border-color: #85dccb; }
QAbstractSpinBox:disabled { color: #626f80; border-color: #29313c; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button { width: 0px; }
QSlider { background: transparent; min-height: 22px; }
QSlider::groove:horizontal { height: 4px; background: #313c49; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #85dccb; border-radius: 2px; }
QSlider::handle:horizontal { background: #e2f8f3; width: 12px; margin: -4px 0; border-radius: 6px; }
QProgressBar { background: #29333d; border: none; border-radius: 2px; max-height: 3px; }
QProgressBar::chunk { background: #85dccb; border-radius: 2px; }
QStatusBar { background: #101317; color: #8996a7; border-top: 1px solid #262e38; }
QStatusBar::item { border: none; }
QScrollBar:horizontal { background: #141a22; height: 10px; margin: 0px; border-radius: 5px; }
QScrollBar::handle:horizontal { background: #344252; min-width: 30px; border-radius: 5px; }
QScrollBar::handle:horizontal:hover { background: #4a5c72; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: transparent; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QScrollBar:vertical { background: #141a22; width: 10px; margin: 0px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #344252; min-height: 30px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #4a5c72; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QLineEdit { background: #11171e; border: 1px solid #35404e; border-radius: 8px;
            padding: 8px 12px; color: #ecf5f7; font-size: 13px; }
QLineEdit:focus { border-color: #85dccb; }
QDialog { background: #101317; }
QScrollArea { background: transparent; border: none; }
QToolTip { background: #27323e; color: #eef4f9; border: 1px solid #445568; padding: 6px; }
QMessageBox { background: #191e25; }
"""


def icon(name: str, color: str = "#d9e4ef", size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 24, size / 24)
    painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if name == "help":
        painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        path = QPainterPath()
        path.moveTo(9.5, 9.5)
        path.cubicTo(9.5, 7, 14.5, 7, 14.5, 9.5)
        path.cubicTo(14.5, 11.5, 12, 12, 12, 14)
        painter.drawPath(path)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(11.2, 16.2, 1.6, 1.6))
    elif name == "search":
        painter.drawEllipse(QRectF(4, 4, 11, 11))
        painter.drawLine(12.5, 12.5, 19, 19)
    elif name == "play":
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))
    elif name == "pause":
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(7, 5, 3, 14), 1, 1)
        painter.drawRoundedRect(QRectF(14, 5, 3, 14), 1, 1)
    elif name == "stop":
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
    elif name == "open":
        painter.drawPolyline(QPolygonF([QPointF(3, 8), QPointF(3, 5), QPointF(9, 5), QPointF(12, 8), QPointF(21, 8)]))
        painter.drawPolygon(QPolygonF([QPointF(3, 9), QPointF(21, 9), QPointF(18, 19), QPointF(5, 19)]))
    elif name == "export":
        painter.drawLine(12, 3, 12, 15)
        painter.drawPolyline(QPolygonF([QPointF(8, 11), QPointF(12, 15), QPointF(16, 11)]))
        painter.drawPolyline(QPolygonF([QPointF(4, 15), QPointF(4, 20), QPointF(20, 20), QPointF(20, 15)]))
    elif name == "cut":
        painter.drawEllipse(QRectF(3, 14, 6, 6))
        painter.drawEllipse(QRectF(3, 4, 6, 6))
        painter.drawLine(8, 9, 20, 20)
        painter.drawLine(8, 15, 20, 4)
    elif name == "undo":
        painter.drawPolyline(QPolygonF([QPointF(8, 4), QPointF(3, 9), QPointF(8, 14)]))
        painter.drawArc(QRectF(3, 8, 17, 12), -100 * 16, 260 * 16)
    elif name == "redo":
        painter.drawPolyline(QPolygonF([QPointF(16, 4), QPointF(21, 9), QPointF(16, 14)]))
        painter.drawArc(QRectF(4, 8, 17, 12), -80 * 16, -260 * 16)
    elif name == "fade_in":
        painter.setPen(QPen(QColor("#4e5f73"), 1.2, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(4, 19, 20, 19)
        painter.setPen(QPen(QColor(color), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        path = QPainterPath()
        path.moveTo(4, 19)
        path.cubicTo(10, 19, 14, 5, 20, 5)
        painter.drawPath(path)
    elif name == "fade_out":
        painter.setPen(QPen(QColor("#4e5f73"), 1.2, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(4, 19, 20, 19)
        painter.setPen(QPen(QColor(color), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        path = QPainterPath()
        path.moveTo(4, 5)
        path.cubicTo(10, 5, 14, 19, 20, 19)
        painter.drawPath(path)
    elif name == "normalize":
        painter.setPen(QPen(QColor("#4e5f73"), 1.2, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(3, 4, 21, 4)
        painter.drawLine(3, 20, 21, 20)
        painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPolyline(QPolygonF([
            QPointF(4, 12),
            QPointF(8, 7),
            QPointF(12, 17),
            QPointF(16, 4),
            QPointF(20, 12),
        ]))
    elif name == "delete_selection":
        painter.setPen(QPen(QColor("#4e5f73"), 1.2, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(8, 4, 8, 20)
        painter.drawLine(16, 4, 16, 20)
        painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(3, 12, 10, 12)
        painter.drawPolyline(QPolygonF([QPointF(7, 9), QPointF(10, 12), QPointF(7, 15)]))
        painter.drawLine(21, 12, 14, 12)
        painter.drawPolyline(QPolygonF([QPointF(17, 9), QPointF(14, 12), QPointF(17, 15)]))
    elif name == "zoom_in":
        painter.drawEllipse(QRectF(3.5, 3.5, 12, 12))
        painter.drawLine(12, 12, 19, 19)
        painter.drawLine(6.5, 9.5, 12.5, 9.5)
        painter.drawLine(9.5, 6.5, 9.5, 12.5)
    elif name == "zoom_out":
        painter.drawEllipse(QRectF(3.5, 3.5, 12, 12))
        painter.drawLine(12, 12, 19, 19)
        painter.drawLine(6.5, 9.5, 12.5, 9.5)
    elif name == "zoom_fit":
        painter.drawLine(3, 4, 3, 20)
        painter.drawLine(21, 4, 21, 20)
        painter.drawLine(6, 12, 18, 12)
        painter.drawPolyline(QPolygonF([QPointF(9, 9), QPointF(6, 12), QPointF(9, 15)]))
        painter.drawPolyline(QPolygonF([QPointF(15, 9), QPointF(18, 12), QPointF(15, 15)]))
    elif name == "stereo":
        painter.drawLine(4, 7, 20, 7)
        painter.drawLine(4, 17, 20, 17)
        painter.drawPolyline(QPolygonF([QPointF(6, 7), QPointF(9, 4), QPointF(12, 10), QPointF(15, 7)]))
        painter.drawPolyline(QPolygonF([QPointF(6, 17), QPointF(9, 14), QPointF(12, 20), QPointF(15, 17)]))
    elif name == "globe":
        painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        painter.drawLine(3.5, 12, 20.5, 12)
        painter.drawEllipse(QRectF(7, 3.5, 10, 17))
    painter.end()
    return QIcon(pixmap)


def app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#1c302f"))
    painter.drawRoundedRect(QRectF(1, 1, 62, 62), 16, 16)
    painter.setPen(QPen(QColor("#85dccb"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for x, height in [(16, 10), (24, 24), (32, 38), (40, 20), (48, 8)]:
        painter.drawLine(x, 32 - height // 2, x, 32 + height // 2)
    painter.end()
    return QIcon(pixmap)
