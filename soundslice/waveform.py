"""A lightweight waveform, draggable selection, multi-channel stereo view, and zoom using QPainter."""

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget

from .audio import AudioClip, channel_waveform_peaks, format_time, waveform_peaks


class WaveformWidget(QWidget):
    selectionChanged = Signal(int, int)
    seekRequested = Signal(int)
    openRequested = Signal()
    zoomChanged = Signal(float, int, int)  # zoom_level, view_start_ms, view_end_ms
    splitStereoChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 200)
        self.setMouseTracking(True)
        self.setAccessibleName("Waveform und Bereichsauswahl")
        self.setToolTip("Klicken: Abspielen · Ziehen: Bereich · Strg+Mausrad: Zoomen · Mausrad: Scrollen")

        self.duration_ms = 0
        self.start_ms = 0
        self.end_ms = 0
        self.position_ms = 0

        self.peaks = np.empty((0, 2), dtype=np.float32)
        self.channel_peaks: tuple[np.ndarray, ...] = ()
        self.clip: AudioClip | None = None
        self.channels: int = 1
        self.split_stereo: bool = True

        self.zoom_level: float = 1.0
        self.view_start_ms: int = 0
        self.view_end_ms: int = 0

        self._wave_cache: QPixmap | None = None
        self._drag: str | None = None
        self._anchor_ms = 0
        self._press_x = 0.0
        self._moved = False
        self._panning = False
        self._pan_start_x = 0.0
        self._pan_start_view = 0

    def graph_rect(self) -> QRectF:
        return QRectF(28, 46, self.width() - 56, self.height() - 90)

    def visible_duration_ms(self) -> int:
        if not self.duration_ms:
            return 0
        return max(50, round(self.duration_ms / self.zoom_level))

    def time_at_x(self, x: float) -> int:
        graph = self.graph_rect()
        vis = self.visible_duration_ms()
        if vis <= 0 or graph.width() <= 0:
            return 0
        ratio = (x - graph.left()) / graph.width()
        time_ms = round(self.view_start_ms + ratio * vis)
        return max(0, min(self.duration_ms, time_ms))

    def x_at_time(self, milliseconds: int) -> float:
        graph = self.graph_rect()
        vis = self.visible_duration_ms()
        if vis <= 0:
            return graph.left()
        return graph.left() + graph.width() * (milliseconds - self.view_start_ms) / vis

    def set_audio(
        self,
        peaks: np.ndarray,
        duration_ms: int,
        channel_peaks: tuple[np.ndarray, ...] = (),
        clip: AudioClip | None = None,
    ):
        self.peaks = peaks
        self.duration_ms = duration_ms
        self.channel_peaks = channel_peaks
        self.clip = clip
        self.channels = clip.channels if clip is not None else (len(channel_peaks) if channel_peaks else 1)
        self.zoom_level = 1.0
        self.view_start_ms = 0
        self.view_end_ms = duration_ms
        self.start_ms, self.end_ms = 0, duration_ms
        self.position_ms = 0
        self._wave_cache = None
        self.zoomChanged.emit(self.zoom_level, self.view_start_ms, self.view_end_ms)
        self.update()

    def set_selection(self, start_ms: int, end_ms: int):
        self.start_ms, self.end_ms = start_ms, end_ms
        self.update()

    def set_position(self, position_ms: int):
        self.position_ms = max(0, min(position_ms, self.duration_ms))
        self.update()

    def set_zoom(self, zoom_level: float, center_time_ms: int | None = None):
        if not self.duration_ms:
            return
        zoom_level = max(1.0, min(100.0, float(zoom_level)))
        if center_time_ms is None:
            center_time_ms = self.view_start_ms + self.visible_duration_ms() // 2
        center_time_ms = max(0, min(self.duration_ms, center_time_ms))

        self.zoom_level = zoom_level
        new_vis = self.visible_duration_ms()

        if zoom_level <= 1.0:
            self.zoom_level = 1.0
            self.view_start_ms = 0
            self.view_end_ms = self.duration_ms
        else:
            self.view_start_ms = max(0, min(self.duration_ms - new_vis, center_time_ms - new_vis // 2))
            self.view_end_ms = self.view_start_ms + new_vis

        self._wave_cache = None
        self.zoomChanged.emit(self.zoom_level, self.view_start_ms, self.view_end_ms)
        self.update()

    def zoom_in(self, factor: float = 1.5):
        center = self.position_ms if (self.view_start_ms <= self.position_ms <= self.view_end_ms) else None
        self.set_zoom(self.zoom_level * factor, center_time_ms=center)

    def zoom_out(self, factor: float = 1.5):
        center = self.position_ms if (self.view_start_ms <= self.position_ms <= self.view_end_ms) else None
        self.set_zoom(self.zoom_level / factor, center_time_ms=center)

    def zoom_fit(self):
        self.set_zoom(1.0)

    def set_view_start(self, start_ms: int):
        new_vis = self.visible_duration_ms()
        self.view_start_ms = max(0, min(max(0, self.duration_ms - new_vis), start_ms))
        self.view_end_ms = self.view_start_ms + new_vis
        self._wave_cache = None
        self.zoomChanged.emit(self.zoom_level, self.view_start_ms, self.view_end_ms)
        self.update()

    def scroll_by_ms(self, delta_ms: int):
        self.set_view_start(self.view_start_ms + delta_ms)

    def set_split_stereo(self, split: bool):
        if self.split_stereo != split:
            self.split_stereo = split
            self._wave_cache = None
            self.splitStereoChanged.emit(split)
            self.update()

    def toggle_split_stereo(self):
        self.set_split_stereo(not self.split_stereo)

    def resizeEvent(self, event):
        self._wave_cache = None
        super().resizeEvent(event)

    def _get_visible_peaks(self) -> tuple[np.ndarray, ...]:
        graph = self.graph_rect()
        bins = max(100, round(graph.width()))
        if self.clip is not None and len(self.clip.samples) > 0 and self.duration_ms > 0:
            first = max(0, min(len(self.clip.samples), round(self.view_start_ms * self.clip.sample_rate / 1000)))
            last = max(first + 1, min(len(self.clip.samples), round(self.view_end_ms * self.clip.sample_rate / 1000)))
            vis_samples = self.clip.samples[first:last]
            if len(vis_samples) > 0:
                return channel_waveform_peaks(vis_samples, bins=bins)
        if self.channel_peaks:
            return self.channel_peaks
        if len(self.peaks):
            return (self.peaks,)
        return ()

    def _draw_waveform_track(
        self,
        painter: QPainter,
        rect: QRectF,
        peaks: np.ndarray,
        color_hex: str = "#81d5c6",
    ):
        if len(peaks) < 1:
            return
        center = rect.center().y()
        amplitude = rect.height() * 0.44
        path = QPainterPath()
        count = len(peaks)
        for index in range(count):
            x = rect.left() + rect.width() * index / max(1, count - 1)
            point = QPointF(x, center - float(peaks[index, 1]) * amplitude)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        for index in range(count - 1, -1, -1):
            x = rect.left() + rect.width() * index / max(1, count - 1)
            path.lineTo(x, center - float(peaks[index, 0]) * amplitude)
        path.closeSubpath()
        painter.setPen(QPen(QColor(color_hex), 1))
        painter.setBrush(QColor(color_hex))
        painter.drawPath(path)

    def _cached_wave(self) -> QPixmap:
        if self._wave_cache is not None:
            return self._wave_cache
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        ch_peaks = self._get_visible_peaks()
        if ch_peaks:
            graph = self.graph_rect()
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if len(ch_peaks) >= 2 and self.split_stereo:
                gap = 6
                half_h = (graph.height() - gap) / 2
                rect_L = QRectF(graph.left(), graph.top(), graph.width(), half_h)
                rect_R = QRectF(graph.left(), graph.top() + half_h + gap, graph.width(), half_h)

                # Center guidelines
                painter.setPen(QPen(QColor("#222c37"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(rect_L.left(), rect_L.center().y()), QPointF(rect_L.right(), rect_L.center().y()))
                painter.drawLine(QPointF(rect_R.left(), rect_R.center().y()), QPointF(rect_R.right(), rect_R.center().y()))

                # Divider
                painter.setPen(QPen(QColor("#2c3846"), 1))
                painter.drawLine(QPointF(graph.left(), graph.top() + half_h + gap / 2),
                                 QPointF(graph.right(), graph.top() + half_h + gap / 2))

                # Waveforms
                self._draw_waveform_track(painter, rect_L, ch_peaks[0], color_hex="#81d5c6")
                self._draw_waveform_track(painter, rect_R, ch_peaks[1], color_hex="#6ec6b7")
            else:
                combined = ch_peaks[0] if len(ch_peaks) == 1 else self.peaks
                if len(combined) == 0 and len(ch_peaks) > 0:
                    combined = ch_peaks[0]
                painter.setPen(QPen(QColor("#222c37"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(graph.left(), graph.center().y()), QPointF(graph.right(), graph.center().y()))
                self._draw_waveform_track(painter, graph, combined, color_hex="#81d5c6")

            painter.end()
        self._wave_cache = pixmap
        return pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#2c3540"), 1))
        painter.setBrush(QColor("#171d24"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)

        graph = self.graph_rect()
        if not self.duration_ms:
            center = self.rect().center()
            painter.setPen(QPen(QColor("#567e79"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for offset, height in [(-32, 16), (-16, 32), (0, 50), (16, 28), (32, 12)]:
                painter.drawLine(center.x() + offset, center.y() - 56 - height // 2,
                                 center.x() + offset, center.y() - 56 + height // 2)
            painter.setPen(QColor("#e8edf3"))
            painter.setFont(QFont("Segoe UI", 17, QFont.Weight.DemiBold))
            painter.drawText(QRectF(0, center.y() - 4, self.width(), 32), Qt.AlignmentFlag.AlignCenter, "Audio-Datei öffnen")
            painter.setPen(QColor("#8996a7"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(0, center.y() + 34, self.width(), 26), Qt.AlignmentFlag.AlignCenter,
                             "WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF · hier ablegen oder oben öffnen")
            painter.end()
            return

        # Grid lines
        painter.setPen(QPen(QColor("#2a333e"), 1))
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = graph.top() + graph.height() * fraction
            painter.drawLine(QPointF(graph.left(), y), QPointF(graph.right(), y))
        for index in range(6):
            x = graph.left() + graph.width() * index / 5
            painter.drawLine(QPointF(x, graph.top()), QPointF(x, graph.bottom()))

        left = self.x_at_time(self.start_ms)
        right = self.x_at_time(self.end_ms)

        # Highlight visible selection
        vis_left = max(graph.left(), min(graph.right(), left))
        vis_right = max(graph.left(), min(graph.right(), right))
        if vis_right > vis_left:
            painter.fillRect(QRectF(vis_left, graph.top(), vis_right - vis_left, graph.height()),
                             QColor(133, 220, 203, 19))

        # Dimmed full wave
        painter.setOpacity(0.32)
        painter.drawPixmap(0, 0, self._cached_wave())
        painter.setOpacity(1.0)

        # Bright wave inside visible selection
        if vis_right > vis_left:
            painter.save()
            painter.setClipRect(QRectF(vis_left, graph.top(), vis_right - vis_left, graph.height()))
            painter.drawPixmap(0, 0, self._cached_wave())
            painter.restore()

        # Channel tags if stereo split
        ch_peaks = self._get_visible_peaks()
        if len(ch_peaks) >= 2 and self.split_stereo:
            gap = 6
            half_h = (graph.height() - gap) / 2
            for tag, top_y in [("L", graph.top() + 4), ("R", graph.top() + half_h + gap + 4)]:
                tag_rect = QRectF(graph.left() + 6, top_y, 16, 15)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(23, 35, 43, 190))
                painter.drawRoundedRect(tag_rect, 4, 4)
                painter.setPen(QColor("#85dccb"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag)

        # Handles A and B
        for x, text in [(left, "A"), (right, "B")]:
            if graph.left() - 9 <= x <= graph.right() + 9:
                painter.setPen(QPen(QColor("#85dccb"), 1.5))
                painter.drawLine(QPointF(x, graph.top()), QPointF(x, graph.bottom()))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#85dccb"))
                painter.drawRoundedRect(QRectF(x - 9, graph.top() - 25, 18, 21), 5, 5)
                painter.setPen(QColor("#152a26"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(QRectF(x - 9, graph.top() - 25, 18, 21), Qt.AlignmentFlag.AlignCenter, text)

        # Playhead
        playhead_x = self.x_at_time(self.position_ms)
        if graph.left() <= playhead_x <= graph.right():
            painter.setPen(QPen(QColor("#f2f5fa"), 1.5))
            painter.drawLine(QPointF(playhead_x, graph.top()), QPointF(playhead_x, graph.bottom()))

        # Time ruler at bottom
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor("#8996a7"))
        vis = self.visible_duration_ms()
        for index in range(6):
            x = graph.left() + graph.width() * index / 5
            label = format_time(round(self.view_start_ms + vis * index / 5))
            width = painter.fontMetrics().horizontalAdvance(label) + 4
            label_x = max(10, min(self.width() - width - 10, x - width / 2))
            painter.drawText(QRectF(label_x, graph.bottom() + 13, width, 20), Qt.AlignmentFlag.AlignCenter, label)

        painter.end()

    def _handle_at(self, x: float) -> str | None:
        left, right = self.x_at_time(self.start_ms), self.x_at_time(self.end_ms)
        graph = self.graph_rect()
        if abs(x - left) <= 10 and abs(x - right) <= 10:
            return "start" if x <= (left + right) / 2 else "end"
        if abs(x - left) <= 10 and (graph.left() - 10 <= left <= graph.right() + 10):
            return "start"
        if abs(x - right) <= 10 and (graph.left() - 10 <= right <= graph.right() + 10):
            return "end"
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if not self.duration_ms:
            if event.button() == Qt.MouseButton.LeftButton:
                self.openRequested.emit()
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start_x = event.position().x()
            self._pan_start_view = self.view_start_ms
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.graph_rect().adjusted(-10, -28, 10, 0).contains(event.position()):
            return
        self._drag = self._handle_at(event.position().x()) or "new"
        self._anchor_ms = self.time_at_x(event.position().x())
        self._press_x = event.position().x()
        self._moved = False

    def mouseMoveEvent(self, event: QMouseEvent):
        x = event.position().x()
        if not self.duration_ms:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            return
        if getattr(self, "_panning", False):
            dx = x - self._pan_start_x
            graph = self.graph_rect()
            if graph.width() > 0:
                ms_per_pixel = self.visible_duration_ms() / graph.width()
                self.set_view_start(round(self._pan_start_view - dx * ms_per_pixel))
            return
        if self._drag is None:
            self.setCursor(Qt.CursorShape.SizeHorCursor if self._handle_at(x) else Qt.CursorShape.CrossCursor)
            return
        if abs(x - self._press_x) < 4 and not self._moved:
            return
        self._moved = True
        time_ms = self.time_at_x(x)
        if self._drag == "start":
            self.start_ms = min(time_ms, self.end_ms - 1)
        elif self._drag == "end":
            self.end_ms = max(time_ms, self.start_ms + 1)
        else:
            self.start_ms, self.end_ms = sorted((self._anchor_ms, time_ms))
            if self.start_ms == self.end_ms:
                self.start_ms = min(self.start_ms, self.duration_ms - 1)
                self.end_ms = self.start_ms + 1
        self.selectionChanged.emit(self.start_ms, self.end_ms)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton and getattr(self, "_panning", False):
            self._panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._drag:
            if not self._moved:
                self.seekRequested.emit(self._anchor_ms)
            self._drag = None
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        if not self.duration_ms:
            return
        delta = event.angleDelta().y() or event.angleDelta().x()
        if not delta:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            center = self.time_at_x(event.position().x())
            factor = 1.25 if delta > 0 else (1.0 / 1.25)
            self.set_zoom(self.zoom_level * factor, center_time_ms=center)
        else:
            if self.zoom_level > 1.0:
                step = max(20, round(self.visible_duration_ms() * 0.08))
                delta_ms = -step if delta > 0 else step
                self.scroll_by_ms(delta_ms)
        event.accept()
