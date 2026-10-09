from dataclasses import dataclass
from pathlib import Path
import re
import tempfile

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QValidator
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractSpinBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollBar, QSizePolicy, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

from .audio import (
    SUPPORTED_EXPORT_EXTENSIONS, SUPPORTED_IMPORT_EXTENSIONS, PreparedClip,
    apply_fade, crop_audio, delete_audio_range, export_audio, format_time, load_audio,
    normalize_audio, prepare_clip,
)
from .help_dialog import HelpDialog
from .i18n import get_language, set_language, t, toggle_language
from .jobs import AudioJob
from .style import app_icon, icon
from .waveform import WaveformWidget


MAX_HISTORY_STEPS = 25


@dataclass(frozen=True)
class HistoryStep:
    prepared: PreparedClip
    edited: bool
    action_name: str


class TimeEdit(QSpinBox):
    """An integer millisecond field shown as minutes:seconds.milliseconds."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setRange(0, 30 * 60 * 1000)
        self.setSingleStep(1000)
        self.setKeyboardTracking(False)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(156)
        self.setAccessibleName(name)
        self.setToolTip(t("time_edit_tooltip"))

    def textFromValue(self, value: int) -> str:
        return format_time(value)

    def valueFromText(self, text: str) -> int:
        match = re.fullmatch(r"(\d+):([0-5]\d)(?:[.,](\d{1,3}))?", text.strip())
        if not match:
            return self.value()
        minutes, seconds, fraction = match.groups()
        return int(minutes) * 60000 + int(seconds) * 1000 + int((fraction or "0").ljust(3, "0"))

    def validate(self, text: str, position: int):
        text = text.strip()
        if re.fullmatch(r"\d+:[0-5]\d(?:[.,]\d{1,3})?", text):
            state = QValidator.State.Acceptable if self.minimum() <= self.valueFromText(text) <= self.maximum() else QValidator.State.Intermediate
        elif re.fullmatch(r"\d*(?::[0-5]?\d?(?:[.,]\d{0,3})?)?", text):
            state = QValidator.State.Intermediate
        else:
            state = QValidator.State.Invalid
        return state, text, position


def label(text: str, name: str = "", parent=None) -> QLabel:
    widget = QLabel(text, parent)
    if name:
        widget.setObjectName(name)
    return widget


def button(text: str, icon_name: str = "", primary: bool = False) -> QPushButton:
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName("primary")
    if icon_name:
        widget.setIcon(icon(icon_name, "#112622" if primary else "#d9e4ef"))
    return widget


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("app_title"))
        self.resize(1120, 760)
        self.setWindowIcon(app_icon())
        self.setAcceptDrops(True)
        self._cache = tempfile.TemporaryDirectory(prefix="soundslice-", ignore_cleanup_errors=True)
        self._cache_path = Path(self._cache.name)
        self._prepared: PreparedClip | None = None
        self._undo_stack: list[HistoryStep] = []
        self._redo_stack: list[HistoryStep] = []
        self._dirty = False
        self._edited = False
        self._export_path: Path | None = None
        self._job: AudioJob | None = None
        self._success_callback = None
        self._close_requested = False
        self._selection_playback = False

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.errorOccurred.connect(self._playback_error)

        self._build_ui()
        self._connect_controls()
        self._update_controls()
        self.setMinimumSize(960, max(700, self.minimumSizeHint().height()))
        self.statusBar().showMessage(t("status_ready"))

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 20, 28, 16)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        toolbar.addWidget(label("endlez Sound Slicer", "brand"))
        self.brand_subtitle = label("  " + t("app_subtitle"), "muted")
        toolbar.addWidget(self.brand_subtitle)
        toolbar.addStretch()
        self.lang_button = button(t("lang_btn"), "globe")
        self.lang_button.setToolTip(t("lang_tooltip"))
        self.lang_button.setObjectName("small")
        self.open_button = button(t("open"), "open")
        self.open_button.setToolTip(t("open_tooltip"))
        self.undo_button = button(t("undo"), "undo")
        self.undo_button.setToolTip(t("undo_tooltip"))
        self.redo_button = button(t("redo"), "redo")
        self.redo_button.setToolTip(t("redo_tooltip"))
        self.export_button = button(t("export"), "export", primary=True)
        self.export_button.setToolTip(t("export_tooltip"))
        self.help_button = button(t("help"), "help")
        self.help_button.setToolTip(t("help_tooltip"))
        for widget in (self.lang_button, self.open_button, self.undo_button, self.redo_button, self.export_button, self.help_button):
            toolbar.addWidget(widget)
        layout.addLayout(toolbar)

        file_row = QHBoxLayout()
        file_info = QVBoxLayout()
        file_info.setSpacing(5)
        self.filename_label = label(t("empty_file_name"), "fileName")
        self.filename_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.metadata_label = label(t("empty_file_meta"), "fileMeta")
        file_info.addWidget(self.filename_label)
        file_info.addWidget(self.metadata_label)
        file_row.addLayout(file_info, 1)
        self.edited_badge = label(t("badge_edited"), "badge")
        self.edited_badge.hide()
        file_row.addWidget(self.edited_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(file_row)

        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform, 1)

        waveform_toolbar = QHBoxLayout()
        waveform_toolbar.setSpacing(8)
        self.waveform_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.waveform_scrollbar.setRange(0, 0)
        self.waveform_scrollbar.setSingleStep(100)
        self.waveform_scrollbar.setToolTip(t("scrollbar_tooltip"))
        self.waveform_scrollbar.setEnabled(False)
        waveform_toolbar.addWidget(self.waveform_scrollbar, 1)

        self.stereo_toggle_button = button(t("stereo_split"), "stereo")
        self.stereo_toggle_button.setObjectName("small")
        self.stereo_toggle_button.setToolTip("Zwischen getrennter L/R- und kombinierter Waveform umschalten")
        self.stereo_toggle_button.setVisible(False)
        waveform_toolbar.addWidget(self.stereo_toggle_button)

        self.zoom_out_button = button("−", "zoom_out")
        self.zoom_out_button.setObjectName("small")
        self.zoom_out_button.setToolTip("Herauszoomen (Strg+Mausrad runter oder Strg+-)")
        self.zoom_label = label("100%", "muted")
        self.zoom_label.setFixedWidth(46)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_in_button = button("+", "zoom_in")
        self.zoom_in_button.setObjectName("small")
        self.zoom_in_button.setToolTip("Hineinzoomen (Strg+Mausrad hoch oder Strg++)")
        self.zoom_fit_button = button(t("zoom_fit"), "zoom_fit")
        self.zoom_fit_button.setObjectName("small")
        self.zoom_fit_button.setToolTip(t("zoom_fit_tooltip"))

        for widget in (self.zoom_out_button, self.zoom_label, self.zoom_in_button, self.zoom_fit_button):
            waveform_toolbar.addWidget(widget)
        layout.addLayout(waveform_toolbar)

        self.hint_label = label(t("waveform_hint"), "hint")
        layout.addWidget(self.hint_label)

        transport = QHBoxLayout()
        transport.setSpacing(12)
        self.play_button = button(t("play"), "play", primary=True)
        self.play_button.setMinimumWidth(138)
        self.play_button.setToolTip("Abspielen / Pause (Leertaste)")
        self.stop_button = button("Stop", "stop")
        self.stop_button.setToolTip("Wiedergabe stoppen und zum Anfang springen (Esc)")
        transport.addWidget(self.play_button)
        transport.addWidget(self.stop_button)
        self.position_label = label("00:00.000", "time")
        self.duration_label = label("/ 00:00.000", "totalTime")
        transport.addWidget(self.position_label)
        transport.addWidget(self.duration_label)
        transport.addStretch()
        self.volume_label = label("Lautstärke", "muted")
        transport.addWidget(self.volume_label)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setAccessibleName("Lautstärke")
        transport.addWidget(self.volume_slider)
        layout.addLayout(transport)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.setSingleStep(1000)
        self.position_slider.setPageStep(10000)
        self.position_slider.setAccessibleName("Wiedergabeposition")
        self.position_slider.setToolTip(t("slider_tooltip"))
        layout.addWidget(self.position_slider)

        selection_panel = QFrame()
        selection_panel.setObjectName("panel")
        selection_layout = QVBoxLayout(selection_panel)
        selection_layout.setContentsMargins(18, 16, 18, 16)
        selection_layout.setSpacing(14)

        selection_row = QHBoxLayout()
        selection_row.setSpacing(12)
        start_column = QVBoxLayout()
        start_column.setSpacing(7)
        self.start_label = label(t("selection_start"), "muted")
        start_column.addWidget(self.start_label)
        self.start_edit = TimeEdit("Auswahl Start")
        start_column.addWidget(self.start_edit)
        end_column = QVBoxLayout()
        end_column.setSpacing(7)
        self.end_label = label(t("selection_end"), "muted")
        end_column.addWidget(self.end_label)
        self.end_edit = TimeEdit("Auswahl Ende")
        end_column.addWidget(self.end_edit)
        selection_row.addLayout(start_column)
        selection_row.addLayout(end_column)
        length_column = QVBoxLayout()
        length_column.setSpacing(7)
        self.length_label = label(t("selected_length"), "muted")
        length_column.addWidget(self.length_label)
        self.selection_length = label("00:00.000", "selectionLength")
        length_column.addWidget(self.selection_length)
        selection_row.addLayout(length_column)
        selection_row.addStretch()
        self.preview_button = button(t("preview_button"), "play")
        self.preview_button.setToolTip("Nur die Auswahl abspielen, ohne die Datei zu verändern")
        self.crop_button = button(t("crop"), "cut", primary=True)
        self.crop_button.setToolTip("Nur die Auswahl behalten; alles davor und danach entfernen")
        self.delete_selection_button = button(t("delete_selection"), "delete_selection")
        self.delete_selection_button.setToolTip("Ausgewählten Bereich entfernen und verbleibende Teile nahtlos zusammenfügen (Strg+X)")
        selection_row.addWidget(self.preview_button, 0, Qt.AlignmentFlag.AlignBottom)
        selection_row.addWidget(self.crop_button, 0, Qt.AlignmentFlag.AlignBottom)
        selection_row.addWidget(self.delete_selection_button, 0, Qt.AlignmentFlag.AlignBottom)
        selection_layout.addLayout(selection_row)

        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(8)
        self.set_start_button = button(t("set_start"))
        self.set_end_button = button(t("set_end"))
        self.all_button = button(t("select_all"))
        self.fade_in_button = button("Fade In", "fade_in")
        self.fade_in_button.setToolTip("Sanftes Einblenden über die markierte Auswahl")
        self.fade_out_button = button("Fade Out", "fade_out")
        self.fade_out_button.setToolTip("Sanftes Ausblenden über die markierte Auswahl")
        self.normalize_button = button("Normalisieren", "normalize")
        self.normalize_button.setToolTip("Gesamte Datei auf optimalen Spitzenpegel (-0.1 dBFS) aussteuern")
        self.remove_before_button = button(t("remove_before"))
        self.remove_before_button.setToolTip("Alles vor A entfernen; Audio ab A bis zum Dateiende behalten")
        self.remove_after_button = button(t("remove_after"))
        self.remove_after_button.setToolTip("Alles nach B entfernen; Audio vom Dateianfang bis B behalten")
        for widget in (self.set_start_button, self.set_end_button, self.all_button,
                       self.fade_in_button, self.fade_out_button, self.normalize_button,
                       self.remove_before_button, self.remove_after_button):
            widget.setObjectName("small")
            secondary_row.addWidget(widget)
        secondary_row.addStretch()
        selection_layout.addLayout(secondary_row)
        layout.addWidget(selection_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)

    def _connect_controls(self):
        self.lang_button.clicked.connect(self.toggle_language)
        self.open_button.clicked.connect(self.open_dialog)
        self.help_button.clicked.connect(lambda: self.show_help())
        self.export_button.clicked.connect(self.export_dialog)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.preview_button.clicked.connect(self.play_selection)
        self.crop_button.clicked.connect(self.crop_selection)
        self.delete_selection_button.clicked.connect(self.delete_selection)
        self.fade_in_button.clicked.connect(self.fade_in)
        self.fade_out_button.clicked.connect(self.fade_out)
        self.normalize_button.clicked.connect(self.normalize)
        self.remove_before_button.clicked.connect(self.remove_before)
        self.remove_after_button.clicked.connect(self.remove_after)
        self.all_button.clicked.connect(self.select_all)
        self.set_start_button.clicked.connect(self.set_start_at_position)
        self.set_end_button.clicked.connect(self.set_end_at_position)
        self.start_edit.valueChanged.connect(self._start_changed)
        self.end_edit.valueChanged.connect(self._end_changed)
        self.waveform.selectionChanged.connect(self._set_selection)
        self.waveform.seekRequested.connect(self.seek)
        self.waveform.openRequested.connect(self.open_dialog)
        self.waveform.zoomChanged.connect(self._waveform_zoom_changed)
        self.waveform_scrollbar.valueChanged.connect(self.waveform.set_view_start)
        self.zoom_in_button.clicked.connect(lambda: self.waveform.zoom_in())
        self.zoom_out_button.clicked.connect(lambda: self.waveform.zoom_out())
        self.zoom_fit_button.clicked.connect(lambda: self.waveform.zoom_fit())
        self.stereo_toggle_button.clicked.connect(self._toggle_stereo_view)
        self.volume_slider.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        self.position_slider.sliderReleased.connect(lambda: self.seek(self.position_slider.value()))
        self.position_slider.actionTriggered.connect(self._slider_action)

        shortcuts = {
            "Ctrl+O": self.open_dialog, "Ctrl+S": self.export_dialog,
            "Ctrl+Z": self.undo, "Ctrl+Y": self.redo, "Ctrl+Shift+Z": self.redo,
            "Ctrl+X": self.delete_selection,
            "Ctrl++": self.waveform.zoom_in, "Ctrl+=": self.waveform.zoom_in,
            "Ctrl+-": self.waveform.zoom_out, "Ctrl+0": self.waveform.zoom_fit,
            "F1": self.show_help, "?": self.show_help,
            "Space": self.toggle_play, "Escape": self.stop,
            "A": self.set_start_at_position, "B": self.set_end_at_position,
        }
        self._shortcuts = []
        for key, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    @property
    def _undo(self):
        if self._undo_stack:
            return (self._undo_stack[-1].prepared, self._undo_stack[-1].edited)
        return None

    @_undo.setter
    def _undo(self, value):
        if value is None:
            self._undo_stack.clear()
        elif isinstance(value, tuple) and len(value) == 2:
            self._push_undo(value[0], value[1], "Aktion")

    @property
    def duration_ms(self) -> int:
        return self._prepared.clip.duration_ms if self._prepared else 0

    def _update_controls(self):
        ready = self._prepared is not None and self._job is None
        self.open_button.setEnabled(self._job is None)
        for widget in (self.export_button, self.play_button, self.stop_button, self.preview_button,
                       self.all_button, self.start_edit, self.end_edit, self.set_start_button,
                       self.set_end_button, self.fade_in_button, self.fade_out_button,
                       self.normalize_button,
                       self.zoom_in_button, self.zoom_out_button, self.zoom_fit_button,
                       self.position_slider, self.waveform):
            widget.setEnabled(ready or (widget is self.waveform and self._job is None))
        is_stereo = ready and self._prepared.clip.channels == 2
        self.stereo_toggle_button.setVisible(is_stereo)
        self.stereo_toggle_button.setEnabled(is_stereo)
        if is_stereo:
            self.stereo_toggle_button.setText(t("stereo_split") if self.waveform.split_stereo else t("stereo_combined"))

        self._waveform_zoom_changed(self.waveform.zoom_level, self.waveform.view_start_ms, self.waveform.view_end_ms)
        has_undo = ready and len(self._undo_stack) > 0
        has_redo = ready and len(self._redo_stack) > 0
        self.undo_button.setEnabled(has_undo)
        self.redo_button.setEnabled(has_redo)
        self._update_history_tooltips()

        full = self.start_edit.value() == 0 and self.end_edit.value() == self.duration_ms
        can_cut = ready and not full
        self.crop_button.setEnabled(can_cut)
        self.delete_selection_button.setEnabled(can_cut)
        self.remove_before_button.setEnabled(ready and self.start_edit.value() > 0)
        self.remove_after_button.setEnabled(ready and self.end_edit.value() < self.duration_ms)
        self.edited_badge.setVisible(self._edited)
        name = self._prepared.clip.source_path.name if self._prepared else ""
        self.setWindowTitle(f"{'* ' if self._dirty else ''}{name + ' · ' if name else ''}{t('app_title')}")

    def _localize_action(self, action_name: str) -> str:
        mapping = {
            "Zuschneiden": "action_crop",
            "Bereich herausschneiden": "action_delete",
            "Normalisieren": "action_normalize",
            "Fade In": "action_fade_in",
            "Fade Out": "action_fade_out",
            "Alles davor entfernen": "action_remove_before",
            "Alles danach entfernen": "action_remove_after",
        }
        key = mapping.get(action_name)
        return t(key) if key else action_name

    def _update_history_tooltips(self):
        has_undo = self._prepared is not None and len(self._undo_stack) > 0
        has_redo = self._prepared is not None and len(self._redo_stack) > 0
        if has_undo:
            count = len(self._undo_stack)
            action = self._localize_action(self._undo_stack[-1].action_name)
            history_info = t("history_multi", count=count) if count > 1 else t("history_single")
            self.undo_button.setToolTip(f"{t('undo')}: {action} (Strg+Z, {history_info})")
        else:
            self.undo_button.setToolTip(f"{t('undo')} (Strg+Z)")

        if has_redo:
            count = len(self._redo_stack)
            action = self._localize_action(self._redo_stack[-1].action_name)
            history_info = t("history_multi", count=count) if count > 1 else t("history_single")
            self.redo_button.setToolTip(f"{t('redo')}: {action} (Strg+Y, {history_info})")
        else:
            self.redo_button.setToolTip(f"{t('redo')} (Strg+Y)")

    def toggle_language(self):
        toggle_language()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.brand_subtitle.setText("  " + t("app_subtitle"))
        self.lang_button.setText(t("lang_btn"))
        self.lang_button.setToolTip(t("lang_tooltip"))
        self.open_button.setText(t("open"))
        self.open_button.setToolTip(t("open_tooltip"))
        self.undo_button.setText(t("undo"))
        self.redo_button.setText(t("redo"))
        self.export_button.setText(t("export"))
        self.export_button.setToolTip(t("export_tooltip"))
        self.help_button.setText(t("help"))
        self.help_button.setToolTip(t("help_tooltip"))

        if self._prepared is None:
            self.filename_label.setText(t("empty_file_name"))
            self.metadata_label.setText(t("empty_file_meta"))
            self.statusBar().showMessage(t("status_ready"))
        else:
            clip = self._prepared.clip
            channels_str = t("channel_mono") if clip.channels == 1 else t("channel_stereo")
            self.metadata_label.setText(f"{channels_str} · {clip.sample_rate:,} Hz · {format_time(self.duration_ms)}".replace(",", " "))

        self.volume_label.setText(t("volume"))
        self.edited_badge.setText(t("badge_edited"))
        if hasattr(self, "hint_label"):
            self.hint_label.setText(t("waveform_hint"))
        self.waveform_scrollbar.setToolTip(t("scrollbar_tooltip"))
        self.position_slider.setToolTip(t("slider_tooltip"))
        self.start_edit.setToolTip(t("time_edit_tooltip"))
        self.end_edit.setToolTip(t("time_edit_tooltip"))
        self.waveform.retranslate_ui()
        self.start_label.setText(t("selection_start"))
        self.end_label.setText(t("selection_end"))
        self.length_label.setText(t("selected_length"))
        self.preview_button.setText(t("preview_button"))
        self.preview_button.setToolTip(t("preview_tooltip"))
        self.crop_button.setText(t("crop"))
        self.crop_button.setToolTip(t("crop_tooltip"))
        self.delete_selection_button.setText(t("delete_selection"))
        self.delete_selection_button.setToolTip(t("delete_selection_tooltip"))

        self.set_start_button.setText(t("set_start"))
        self.set_start_button.setToolTip(t("set_start_tooltip"))
        self.set_end_button.setText(t("set_end"))
        self.set_end_button.setToolTip(t("set_end_tooltip"))
        self.all_button.setText(t("select_all"))
        self.all_button.setToolTip(t("select_all_tooltip"))
        self.fade_in_button.setText(t("fade_in"))
        self.fade_in_button.setToolTip(t("fade_in_tooltip"))
        self.fade_out_button.setText(t("fade_out"))
        self.fade_out_button.setToolTip(t("fade_out_tooltip"))
        self.normalize_button.setText(t("normalize"))
        self.normalize_button.setToolTip(t("normalize_tooltip"))
        self.remove_before_button.setText(t("remove_before"))
        self.remove_before_button.setToolTip(t("remove_before_tooltip"))
        self.remove_after_button.setText(t("remove_after"))
        self.remove_after_button.setToolTip(t("remove_after_tooltip"))

        self.zoom_out_button.setToolTip(t("zoom_out_tooltip"))
        self.zoom_in_button.setToolTip(t("zoom_in_tooltip"))
        self.zoom_fit_button.setText(t("zoom_fit"))
        self.zoom_fit_button.setToolTip(t("zoom_fit_tooltip"))
        self.stereo_toggle_button.setText(
            t("stereo_split") if self.waveform.split_stereo else t("stereo_combined")
        )
        self.stereo_toggle_button.setToolTip(t("stereo_tooltip"))

        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText(t("pause") if playing else t("play"))
        self.play_button.setToolTip(t("play_tooltip"))
        self.stop_button.setText(t("stop"))
        self.stop_button.setToolTip(t("stop_tooltip"))

        self._update_controls()

    def _ask_discard(self) -> bool:
        if not self._dirty:
            return True
        box = QMessageBox(QMessageBox.Icon.Warning, t("discard_title"),
                          t("discard_text"),
                          QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, self)
        box.button(QMessageBox.StandardButton.Discard).setText(t("discard_btn"))
        box.button(QMessageBox.StandardButton.Cancel).setText(t("cancel_btn"))
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return box.exec() == QMessageBox.StandardButton.Discard

    def show_help(self, query: str = ""):
        dialog = HelpDialog(self, initial_query=query, lang=get_language())
        dialog.exec()

    def open_dialog(self):
        if self._job is not None:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, t("file_dialog_open_title"), "",
            f"{t('file_filter_all')} (*.wav *.mp3 *.flac *.ogg *.opus *.m4a *.aac *.aiff *.aif *.wma);;"
            "WAV Audio (*.wav);;MP3 Audio (*.mp3);;FLAC Audio (*.flac);;OGG Vorbis (*.ogg);;Opus Audio (*.opus);;"
            "M4A Audio (*.m4a);;AAC Audio (*.aac);;AIFF Audio (*.aiff *.aif);;WMA Audio (*.wma)"
        )
        if filename:
            self.open_path(Path(filename))

    def open_path(self, path: Path):
        if self._job is not None or not self._ask_discard():
            return
        self._begin_job(t("status_loading"), lambda: prepare_clip(load_audio(path), self._cache_path), self._loaded)

    def _loaded(self, prepared: PreparedClip):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._dirty = False
        self._edited = False
        self._export_path = None
        self._apply_prepared(prepared)
        self.statusBar().showMessage(t("status_loaded"))

    def _apply_prepared(self, prepared: PreparedClip):
        self.stop()
        self.player.setSource(QUrl())
        self._prepared = prepared
        self.waveform.set_audio(
            prepared.peaks,
            prepared.clip.duration_ms,
            channel_peaks=prepared.channel_peaks,
            clip=prepared.clip,
        )
        self.position_slider.setRange(0, self.duration_ms)
        with QSignalBlocker(self.start_edit), QSignalBlocker(self.end_edit):
            self.start_edit.setRange(0, max(0, self.duration_ms - 1))
            self.end_edit.setRange(1, self.duration_ms)
            self.start_edit.setValue(0)
            self.end_edit.setValue(self.duration_ms)
        self._set_selection(0, self.duration_ms)
        clip = prepared.clip
        self.filename_label.setText(clip.source_path.name)
        self.filename_label.setToolTip(str(clip.source_path))
        channels = "Mono" if clip.channels == 1 else "Stereo"
        self.metadata_label.setText(f"{channels} · {clip.sample_rate:,} Hz · {format_time(self.duration_ms)}".replace(",", " "))
        self.duration_label.setText(f"/ {format_time(self.duration_ms)}")
        self._position_changed(0)
        self.player.setSource(QUrl.fromLocalFile(str(prepared.preview_path)))
        self._update_controls()
        QTimer.singleShot(250, self._prune_previews)

    def _begin_job(self, message, operation, on_success):
        if self._job is not None:
            return
        self._selection_playback = False
        self.player.pause()
        self._success_callback = on_success
        self._job = AudioJob(operation, self)
        self._job.succeeded.connect(self._job_succeeded)
        self._job.failed.connect(self._job_failed)
        self._job.finished.connect(self._job_finished)
        self.progress_bar.show()
        self.statusBar().showMessage(message)
        self._update_controls()
        self._job.start()

    @Slot(object)
    def _job_succeeded(self, result):
        self._success_callback(result)

    @Slot(str)
    def _job_failed(self, message: str):
        self.statusBar().showMessage("Verarbeitung fehlgeschlagen · die aktuelle Datei bleibt erhalten")
        QMessageBox.warning(self, t("error_audio_processing"), message)

    @Slot()
    def _job_finished(self):
        job = self._job
        self._job = None
        self._success_callback = None
        self.progress_bar.hide()
        if job:
            job.deleteLater()
        self._update_controls()
        if self._close_requested:
            self._close_requested = False
            QTimer.singleShot(0, self.close)

    @Slot(int, int)
    def _set_selection(self, start_ms: int, end_ms: int):
        if not self._prepared:
            return
        start_ms = max(0, min(start_ms, self.duration_ms - 1))
        end_ms = max(start_ms + 1, min(end_ms, self.duration_ms))
        # Stop a selection preview when its boundaries are changed.
        if self._selection_playback:
            self._selection_playback = False
            self.player.pause()
        with QSignalBlocker(self.start_edit), QSignalBlocker(self.end_edit):
            self.start_edit.setValue(start_ms)
            self.end_edit.setValue(end_ms)
        self.waveform.set_selection(start_ms, end_ms)
        self.selection_length.setText(format_time(end_ms - start_ms))
        self._update_controls()

    def _start_changed(self, value: int):
        self._set_selection(value, max(value + 1, self.end_edit.value()))

    def _end_changed(self, value: int):
        self._set_selection(min(self.start_edit.value(), value - 1), value)

    def select_all(self):
        if self._job is None:
            self._set_selection(0, self.duration_ms)

    def set_start_at_position(self):
        if self._prepared and self._job is None:
            position = min(self.player.position(), self.duration_ms - 1)
            self._set_selection(position, max(position + 1, self.end_edit.value()))

    def set_end_at_position(self):
        if self._prepared and self._job is None:
            position = max(1, min(self.player.position(), self.duration_ms))
            self._set_selection(min(self.start_edit.value(), position - 1), position)

    def toggle_play(self):
        if not self._prepared or self._job is not None:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self._selection_playback and self.player.position() >= self.end_edit.value():
                self.player.setPosition(self.start_edit.value())
            elif self.player.position() >= self.duration_ms:
                self.player.setPosition(0)
            self.player.play()

    def play_selection(self):
        if not self._prepared or self._job is not None:
            return
        self._selection_playback = True
        self.player.setPosition(self.start_edit.value())
        self.player.play()

    def stop(self):
        self._selection_playback = False
        self.player.stop()
        self._position_changed(0)

    def seek(self, position_ms: int):
        if not self._prepared or self._job is not None:
            return
        self._selection_playback = False
        position_ms = max(0, min(position_ms, self.duration_ms))
        self.player.setPosition(position_ms)
        self._position_changed(position_ms)

    def _slider_action(self, _action):
        if not self.position_slider.isSliderDown():
            self.seek(self.position_slider.sliderPosition())

    @Slot(int)
    def _position_changed(self, position_ms: int):
        position_ms = max(0, min(position_ms, self.duration_ms))
        if self._selection_playback and position_ms >= self.end_edit.value():
            self._selection_playback = False
            self.player.pause()
            position_ms = self.end_edit.value()
            self.player.setPosition(position_ms)
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and self.waveform.zoom_level > 1.0:
            if position_ms > self.waveform.view_end_ms or position_ms < self.waveform.view_start_ms:
                self.waveform.set_view_start(position_ms - self.waveform.visible_duration_ms() // 4)
        self.position_label.setText(format_time(position_ms))
        self.waveform.set_position(position_ms)
        if not self.position_slider.isSliderDown():
            with QSignalBlocker(self.position_slider):
                self.position_slider.setValue(position_ms)

    def _toggle_stereo_view(self):
        self.waveform.toggle_split_stereo()
        is_split = self.waveform.split_stereo
        self.stereo_toggle_button.setText("Stereo getrennt" if is_split else "Stereo kombiniert")

    def _waveform_zoom_changed(self, zoom: float, view_start: int, view_end: int):
        vis = view_end - view_start
        self.zoom_label.setText(f"{round(zoom * 100)}%")
        ready = self._prepared is not None and self._job is None
        with QSignalBlocker(self.waveform_scrollbar):
            if ready and zoom > 1.0 and self.duration_ms > vis:
                self.waveform_scrollbar.setEnabled(True)
                self.waveform_scrollbar.setRange(0, self.duration_ms - vis)
                self.waveform_scrollbar.setPageStep(vis)
                self.waveform_scrollbar.setValue(view_start)
                self.zoom_fit_button.setEnabled(True)
            else:
                self.waveform_scrollbar.setEnabled(False)
                self.waveform_scrollbar.setRange(0, 0)
                self.waveform_scrollbar.setValue(0)
                self.zoom_fit_button.setEnabled(False)
        self.zoom_out_button.setEnabled(ready and zoom > 1.0)
        self.zoom_in_button.setEnabled(ready and zoom < 100.0)

    def _playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText(t("pause") if playing else t("play"))
        self.play_button.setIcon(icon("pause" if playing else "play", "#112622"))

    def _playback_error(self, error, message: str):
        if error != QMediaPlayer.Error.NoError:
            self._selection_playback = False
            self.statusBar().showMessage("Wiedergabe nicht verfügbar · " + message)

    def _push_undo(self, prepared: PreparedClip, old_edited: bool, action_name: str):
        self._undo_stack.append(HistoryStep(prepared, old_edited, action_name))
        if len(self._undo_stack) > MAX_HISTORY_STEPS:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def crop_selection(self):
        self._crop(self.start_edit.value(), self.end_edit.value(), action_name="Zuschneiden")

    def remove_before(self):
        self._crop(self.start_edit.value(), self.duration_ms, action_name="Alles davor entfernen")

    def remove_after(self):
        self._crop(0, self.end_edit.value(), action_name="Alles danach entfernen")

    def _crop(self, start_ms: int, end_ms: int, action_name: str = "Zuschneiden"):
        if not self._prepared or self._job is not None or (start_ms == 0 and end_ms == self.duration_ms):
            return
        previous = self._prepared
        old_edited = self._edited

        def apply(result):
            self._push_undo(previous, old_edited, action_name)
            self._dirty = self._edited = True
            self._apply_prepared(result)
            self.statusBar().showMessage(t("status_action_done", action=self._localize_action(action_name)))

        self._begin_job(
            t("status_action_running", action=self._localize_action(action_name)),
            lambda: prepare_clip(crop_audio(previous.clip, start_ms, end_ms), self._cache_path),
            apply,
        )

    def delete_selection(self):
        if not self._prepared or self._job is not None:
            return
        start_ms = self.start_edit.value()
        end_ms = self.end_edit.value()
        if start_ms >= end_ms or (start_ms == 0 and end_ms == self.duration_ms):
            return
        previous = self._prepared
        old_edited = self._edited

        def apply(result):
            self._push_undo(previous, old_edited, "Bereich herausschneiden")
            self._dirty = self._edited = True
            self._apply_prepared(result)
            self.statusBar().showMessage(t("status_deleted"))

        self._begin_job(
            t("status_deleting"),
            lambda: prepare_clip(delete_audio_range(previous.clip, start_ms, end_ms), self._cache_path),
            apply,
        )

    def undo(self):
        if not self._undo_stack or self._job is not None:
            return
        step = self._undo_stack.pop()
        current = self._prepared
        current_edited = self._edited
        self._redo_stack.append(HistoryStep(current, current_edited, step.action_name))
        self._dirty = True
        self._edited = step.edited
        self._apply_prepared(step.prepared)
        remaining = len(self._undo_stack)
        rem_text = f" (noch {remaining} im Verlauf)" if remaining > 0 else ""
        self.statusBar().showMessage(f"Rückgängig: {step.action_name}{rem_text}")

    def redo(self):
        if not self._redo_stack or self._job is not None:
            return
        step = self._redo_stack.pop()
        current = self._prepared
        current_edited = self._edited
        self._undo_stack.append(HistoryStep(current, current_edited, step.action_name))
        self._dirty = True
        self._edited = True
        self._apply_prepared(step.prepared)
        remaining = len(self._redo_stack)
        rem_text = f" (noch {remaining} verfügbar)" if remaining > 0 else ""
        self.statusBar().showMessage(f"Wiederholen: {step.action_name}{rem_text}")

    def fade_in(self):
        self._apply_fade(fade_in=True)

    def fade_out(self):
        self._apply_fade(fade_in=False)

    def _apply_fade(self, fade_in: bool):
        if not self._prepared or self._job is not None:
            return
        start_ms = self.start_edit.value()
        end_ms = self.end_edit.value()
        if start_ms >= end_ms:
            return
        previous = self._prepared
        old_edited = self._edited
        action_name = "Fade In" if fade_in else "Fade Out"

        def apply(result):
            self._push_undo(previous, old_edited, action_name)
            self._dirty = self._edited = True
            self._apply_prepared(result)
            self.statusBar().showMessage(t("status_fade_done", action=self._localize_action(action_name)))

        self._begin_job(
            t("status_fade_running", action=self._localize_action(action_name)),
            lambda: prepare_clip(apply_fade(previous.clip, start_ms, end_ms, fade_in=fade_in), self._cache_path),
            apply,
        )

    def normalize(self):
        if not self._prepared or self._job is not None:
            return
        previous = self._prepared
        old_edited = self._edited

        def apply(result):
            prepared, gain_db = result
            self._push_undo(previous, old_edited, "Normalisieren")
            self._dirty = self._edited = True
            self._apply_prepared(prepared)
            sign = "+" if gain_db >= 0 else ""
            self.statusBar().showMessage(
                f"Normalisiert (-0.1 dBFS, Pegelanpassung: {sign}{gain_db:.1f} dB) · Rückgängig mit Strg+Z"
            )

        def worker():
            normalized_clip, gain_db = normalize_audio(previous.clip, target_peak_db=-0.1)
            prepared = prepare_clip(normalized_clip, self._cache_path)
            return prepared, gain_db

        self._begin_job(t("status_normalizing_running"), worker, apply)

    def export_dialog(self):
        if not self._prepared or self._job is not None:
            return
        self.player.pause()
        self._selection_playback = False
        source = self._prepared.clip.source_path
        default_suffix = source.suffix if source.suffix.lower() in SUPPORTED_EXPORT_EXTENSIONS else ".wav"
        suggested = self._export_path or source.with_name(f"{source.stem}_cut{default_suffix}")
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, t("file_dialog_export_title"), str(suggested),
            "WAV Audio (*.wav);;MP3 Audio (*.mp3);;FLAC Audio (*.flac);;OGG Vorbis (*.ogg);;Opus Audio (*.opus);;"
            "M4A Audio (*.m4a);;AAC Audio (*.aac);;AIFF Audio (*.aiff);;WMA Audio (*.wma)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not filename:
            return
        destination = Path(filename)
        if not destination.suffix:
            if "*.mp3" in selected_filter:
                destination = destination.with_suffix(".mp3")
            elif "*.flac" in selected_filter:
                destination = destination.with_suffix(".flac")
            elif "*.ogg" in selected_filter:
                destination = destination.with_suffix(".ogg")
            elif "*.opus" in selected_filter:
                destination = destination.with_suffix(".opus")
            elif "*.m4a" in selected_filter:
                destination = destination.with_suffix(".m4a")
            elif "*.aac" in selected_filter:
                destination = destination.with_suffix(".aac")
            elif "*.aiff" in selected_filter:
                destination = destination.with_suffix(".aiff")
            elif "*.wma" in selected_filter:
                destination = destination.with_suffix(".wma")
            else:
                destination = destination.with_suffix(".wav")
        if destination.suffix.lower() not in SUPPORTED_EXPORT_EXTENSIONS:
            QMessageBox.warning(
                self, t("invalid_ext_title"),
                t("invalid_ext_text")
            )
            return
        if destination.exists():
            box = QMessageBox(QMessageBox.Icon.Question, t("export_replace_title"),
                              t("export_replace_text", name=destination.name),
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, self)
            box.button(QMessageBox.StandardButton.Yes).setText(t("export_replace_btn"))
            box.button(QMessageBox.StandardButton.Cancel).setText(t("cancel_btn"))
            box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return
        clip = self._prepared.clip
        self._begin_job(t("status_exporting"), lambda: export_audio(clip, destination), self._exported)

    def _exported(self, destination: Path):
        self._dirty = False
        self._export_path = destination
        self._update_controls()
        self.statusBar().showMessage(f"{t('export')}: {destination}")

    def _prune_previews(self):
        keep = set()
        if self._prepared:
            keep.add(self._prepared.preview_path)
        for step in self._undo_stack:
            keep.add(step.prepared.preview_path)
        for step in self._redo_stack:
            keep.add(step.prepared.preview_path)
        if self._job is not None:
            # A worker may currently be writing a fresh preview file.
            return
        for path in self._cache_path.glob("*.wav"):
            if path not in keep:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # Qt may release its previous file handle a little later.

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if self._job is None and len(urls) == 1 and urls[0].isLocalFile():
            if Path(urls[0].toLocalFile()).suffix.lower() in SUPPORTED_IMPORT_EXTENSIONS:
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            self.open_path(Path(urls[0].toLocalFile()))
            event.acceptProposedAction()

    def closeEvent(self, event):
        if self._job is not None:
            self._close_requested = True
            self.statusBar().showMessage(t("status_closing"))
            event.ignore()
            return
        if not self._ask_discard():
            event.ignore()
            return
        self.stop()
        self.player.setSource(QUrl())
        event.accept()

    def cleanup(self):
        self.player.stop()
        self.player.setSource(QUrl())
        self._cache.cleanup()
