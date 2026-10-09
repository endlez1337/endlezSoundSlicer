"""Qt integration tests. Can run headlessly using QT_QPA_PLATFORM=offscreen."""

from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf
from PySide6.QtCore import QPoint, QUrl, Qt
from PySide6.QtGui import QValidator
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from soundslice.audio import AudioError, load_audio
from soundslice.help_dialog import HELP_TOPICS, HelpDialog
from soundslice.i18n import get_language, set_language
from soundslice.style import STYLESHEET, configure_fonts
from soundslice.window import EditorWindow, TimeEdit


APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
configure_fonts(APP)
APP.setStyleSheet(STYLESHEET)


def wait_until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Timed out waiting for Qt/audio operation")
        QTest.qWait(10)
    APP.processEvents()


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="soundslice-ui-test-")
        self.root = Path(self.directory.name)
        self.source = self.root / "Testaufnahme.wav"
        rate = 48000
        t = np.arange(4 * rate) / rate
        sf.write(self.source, 0.3 * np.sin(2 * np.pi * 440 * t), rate)
        self.window = EditorWindow()
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        set_language("de")
        wait_until(lambda: self.window._job is None)
        self.window._dirty = False
        self.window.close()
        self.window.cleanup()
        self.window.deleteLater()
        APP.processEvents()
        self.directory.cleanup()

    def load(self):
        self.window.open_path(self.source)
        self.assertFalse(self.window.open_button.isEnabled())
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 4000)
        wait_until(lambda: self.window.player.mediaStatus() in (
            QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia,
        ))

    def test_complete_load_select_trim_export_and_undo(self):
        self.load()
        self.window.start_edit.setValue(500)
        self.window.end_edit.setValue(2000)
        self.assertTrue(self.window.crop_button.isEnabled())
        self.assertEqual(self.window.selection_length.text(), "00:01.500")
        QTest.mouseClick(self.window.crop_button, Qt.MouseButton.LeftButton)
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 1500)
        self.assertTrue(self.window._dirty)
        self.assertEqual((self.window.start_edit.value(), self.window.end_edit.value()), (0, 1500))
        self.assertEqual(self.window.player.source(), QUrl.fromLocalFile(str(self.window._prepared.preview_path)))
        target = self.root / "export.mp3"
        with patch("soundslice.window.QFileDialog.getSaveFileName", return_value=(str(target), "MP3 Audio (*.mp3)")):
            self.window.export_dialog()
        wait_until(lambda: self.window._job is None)
        self.assertEqual(load_audio(target).duration_ms, 1500)
        self.assertFalse(self.window._dirty)
        self.window.undo()
        self.assertEqual(self.window.duration_ms, 4000)
        self.assertTrue(self.window._dirty)
        self.assertFalse(self.window.undo_button.isEnabled())

    def test_fade_in_fade_out_and_undo(self):
        self.load()
        old_first = self.window._prepared.clip.samples[0].copy()
        self.window._set_selection(0, 1000)
        self.window.fade_in()
        wait_until(lambda: self.window._job is None)
        self.assertTrue(self.window._dirty)
        self.assertTrue(self.window._edited)
        self.assertTrue(self.window.undo_button.isEnabled())
        np.testing.assert_allclose(self.window._prepared.clip.samples[0], np.zeros_like(old_first), atol=1e-5)
        self.window.undo()
        np.testing.assert_allclose(self.window._prepared.clip.samples[0], old_first, atol=1e-5)

    def test_normalize_and_undo(self):
        self.assertFalse(self.window.normalize_button.isEnabled())
        self.load()
        old_samples = self.window._prepared.clip.samples.copy()
        self.assertTrue(self.window.normalize_button.isEnabled())

        QTest.mouseClick(self.window.normalize_button, Qt.MouseButton.LeftButton)
        wait_until(lambda: self.window._job is None)

        self.assertTrue(self.window._dirty)
        self.assertTrue(self.window._edited)
        self.assertTrue(self.window.undo_button.isEnabled())
        new_peak = float(np.max(np.abs(self.window._prepared.clip.samples)))
        target_linear = 10.0 ** (-0.1 / 20.0)
        self.assertAlmostEqual(new_peak, target_linear, places=5)
        self.assertIn("Normalisiert", self.window.statusBar().currentMessage())

        self.window.undo()
        self.assertTrue(self.window._dirty)
        np.testing.assert_allclose(self.window._prepared.clip.samples, old_samples, atol=1e-6)
        self.assertFalse(self.window.undo_button.isEnabled())

    def test_delete_selection_button_and_action(self):
        self.assertFalse(self.window.delete_selection_button.isEnabled())
        self.load()
        # Full selection: delete selection should be disabled
        self.assertFalse(self.window.delete_selection_button.isEnabled())
        # Partial selection: 1000 to 2000 ms (1 second selected)
        self.window._set_selection(1000, 2000)
        self.assertTrue(self.window.delete_selection_button.isEnabled())

        QTest.mouseClick(self.window.delete_selection_button, Qt.MouseButton.LeftButton)
        wait_until(lambda: self.window._job is None)

        self.assertEqual(self.window.duration_ms, 3000)
        self.assertTrue(self.window._dirty)
        self.assertTrue(self.window._edited)
        self.assertTrue(self.window.undo_button.isEnabled())
        self.assertIn("herausgeschnitten", self.window.statusBar().currentMessage())

    def test_multi_level_undo_and_redo_stack(self):
        self.load()
        self.assertFalse(self.window.undo_button.isEnabled())
        self.assertFalse(self.window.redo_button.isEnabled())

        # Action 1: Crop selection 1000..3000 -> 2000ms
        self.window._set_selection(1000, 3000)
        self.window.crop_selection()
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 2000)
        self.assertTrue(self.window.undo_button.isEnabled())
        self.assertIn("Zuschneiden", self.window.undo_button.toolTip())

        # Action 2: Delete selection 500..1500 -> 1000ms
        self.window._set_selection(500, 1500)
        self.window.delete_selection()
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 1000)
        self.assertIn("Bereich herausschneiden", self.window.undo_button.toolTip())
        self.assertIn("2 im Verlauf", self.window.undo_button.toolTip())

        # Action 3: Normalize
        self.window.normalize()
        wait_until(lambda: self.window._job is None)
        self.assertIn("Normalisieren", self.window.undo_button.toolTip())
        self.assertIn("3 im Verlauf", self.window.undo_button.toolTip())

        # Undo 1: Reverts Normalize
        self.window.undo()
        self.assertEqual(self.window.duration_ms, 1000)
        self.assertTrue(self.window.redo_button.isEnabled())
        self.assertIn("Normalisieren", self.window.redo_button.toolTip())
        self.assertIn("Bereich herausschneiden", self.window.undo_button.toolTip())

        # Undo 2: Reverts Delete Selection -> back to 2000ms
        self.window.undo()
        self.assertEqual(self.window.duration_ms, 2000)
        self.assertIn("Bereich herausschneiden", self.window.redo_button.toolTip())
        self.assertIn("Zuschneiden", self.window.undo_button.toolTip())

        # Undo 3: Reverts Crop -> back to initial 4000ms
        self.window.undo()
        self.assertEqual(self.window.duration_ms, 4000)
        self.assertFalse(self.window.undo_button.isEnabled())
        self.assertTrue(self.window.redo_button.isEnabled())

        # Redo 1: Re-applies Crop -> back to 2000ms
        self.window.redo()
        self.assertEqual(self.window.duration_ms, 2000)
        self.assertTrue(self.window.undo_button.isEnabled())
        self.assertTrue(self.window.redo_button.isEnabled())

        # Branching edit: Fade in should clear the remaining redo stack
        self.window._set_selection(0, 500)
        self.window.fade_in()
        wait_until(lambda: self.window._job is None)
        self.assertFalse(self.window.redo_button.isEnabled())
        self.assertIn("Fade In", self.window.undo_button.toolTip())

    def test_play_pause_seek_stop_and_selection_preview(self):
        self.load()
        self.window.toggle_play()
        wait_until(lambda: self.window.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        wait_until(lambda: self.window.player.position() >= 100)
        self.assertEqual(self.window.play_button.text(), "Pause")
        self.window.toggle_play()
        self.assertEqual(self.window.player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
        self.window.seek(1200)
        self.assertEqual(self.window.position_label.text(), "00:01.200")
        self.window.stop()
        self.assertEqual(self.window.player.position(), 0)
        self.assertEqual(self.window.position_slider.value(), 0)
        self.window._set_selection(200, 550)
        self.window.play_selection()
        wait_until(lambda: self.window.player.playbackState() == QMediaPlayer.PlaybackState.PausedState)
        self.assertEqual(self.window.player.position(), 550)

    def test_mouse_selection_handles_seek_and_time_fields(self):
        self.load()
        graph = self.window.waveform.graph_rect()
        y = round(graph.center().y())
        start_x = round(self.window.waveform.x_at_time(700))
        end_x = round(self.window.waveform.x_at_time(2700))
        QTest.mousePress(self.window.waveform, Qt.MouseButton.LeftButton, pos=QPoint(start_x, y))
        QTest.mouseMove(self.window.waveform, QPoint(end_x, y), 20)
        QTest.mouseRelease(self.window.waveform, Qt.MouseButton.LeftButton, pos=QPoint(end_x, y))
        self.assertAlmostEqual(self.window.start_edit.value(), 700, delta=5)
        self.assertAlmostEqual(self.window.end_edit.value(), 2700, delta=5)
        new_x = round(self.window.waveform.x_at_time(1100))
        QTest.mousePress(self.window.waveform, Qt.MouseButton.LeftButton, pos=QPoint(start_x, y))
        QTest.mouseMove(self.window.waveform, QPoint(new_x, y), 20)
        QTest.mouseRelease(self.window.waveform, Qt.MouseButton.LeftButton, pos=QPoint(new_x, y))
        self.assertAlmostEqual(self.window.start_edit.value(), 1100, delta=5)
        seek_x = round(self.window.waveform.x_at_time(1800))
        QTest.mouseClick(self.window.waveform, Qt.MouseButton.LeftButton, pos=QPoint(seek_x, y))
        self.assertAlmostEqual(self.window.player.position(), 1800, delta=5)
        self.window.start_edit.setFocus()
        self.window.start_edit.lineEdit().selectAll()
        QTest.keyClicks(self.window.start_edit, "00:00.450")
        QTest.keyClick(self.window.start_edit, Qt.Key.Key_Return)
        self.assertEqual(self.window.start_edit.value(), 450)

    def test_before_after_removal_and_selection_invariants(self):
        self.load()
        self.window._set_selection(1000, 3000)
        self.window.remove_before()
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 3000)
        self.window._set_selection(500, 1500)
        self.window.remove_after()
        wait_until(lambda: self.window._job is None)
        self.assertEqual(self.window.duration_ms, 1500)
        self.window.start_edit.setValue(1200)
        self.window.end_edit.setValue(700)
        self.assertLess(self.window.start_edit.value(), self.window.end_edit.value())

    def test_failed_load_keeps_current_audio_and_reenables_controls(self):
        self.load()
        old = self.window._prepared
        bad = self.root / "broken.wav"
        bad.write_text("broken")
        with patch("soundslice.window.QMessageBox.warning") as warning:
            self.window.open_path(bad)
            wait_until(lambda: self.window._job is None)
            warning.assert_called_once()
        self.assertIs(self.window._prepared, old)
        self.assertTrue(self.window.open_button.isEnabled())
        self.assertTrue(self.window.export_button.isEnabled())

    def test_export_filter_appends_extension_and_failed_save_keeps_dirty(self):
        self.load()
        self.window._set_selection(500, 1500)
        self.window.crop_selection()
        wait_until(lambda: self.window._job is None)
        target = self.root / "no_extension"
        with patch("soundslice.window.QFileDialog.getSaveFileName", return_value=(str(target), "MP3 Audio (*.mp3)")):
            self.window.export_dialog()
        wait_until(lambda: self.window._job is None)
        self.assertTrue(target.with_suffix(".mp3").exists())
        self.window._dirty = True
        with patch("soundslice.window.QFileDialog.getSaveFileName", return_value=(str(self.root / "bad.wav"), "WAV Audio (*.wav)")), \
             patch("soundslice.window.export_audio", side_effect=AudioError("Disk full")), \
             patch("soundslice.window.QMessageBox.warning"):
            self.window.export_dialog()
            wait_until(lambda: self.window._job is None)
        self.assertTrue(self.window._dirty)

    def test_export_filter_appends_all_extensions(self):
        self.load()
        for ext, filter_name in [
            (".flac", "FLAC Audio (*.flac)"),
            (".ogg", "OGG Vorbis (*.ogg)"),
            (".opus", "Opus Audio (*.opus)"),
            (".m4a", "M4A Audio (*.m4a)"),
            (".aac", "AAC Audio (*.aac)"),
            (".aiff", "AIFF Audio (*.aiff)"),
            (".wma", "WMA Audio (*.wma)"),
        ]:
            target = self.root / f"no_ext_{ext.replace('.', '')}"
            with patch("soundslice.window.QFileDialog.getSaveFileName", return_value=(str(target), filter_name)):
                self.window.export_dialog()
            wait_until(lambda: self.window._job is None)
            self.assertTrue(target.with_suffix(ext).exists())

    def test_default_export_filename_keeps_dotted_source_name(self):
        dotted = self.root / "Aufnahme.v2.wav"
        dotted.write_bytes(self.source.read_bytes())
        self.window.open_path(dotted)
        wait_until(lambda: self.window._job is None)
        with patch("soundslice.window.QFileDialog.getSaveFileName", return_value=("", "")) as dialog:
            self.window.export_dialog()
        self.assertEqual(Path(dialog.call_args.args[2]).name, "Aufnahme.v2_cut.wav")

    def test_close_during_job_waits_for_thread(self):
        def operation():
            time.sleep(0.15)
            return None
        self.window._begin_job("Test", operation, lambda _: None)
        self.window.close()
        self.assertTrue(self.window.isVisible())
        wait_until(lambda: self.window._job is None)
        wait_until(lambda: not self.window.isVisible())

    def test_time_field_validation(self):
        field = TimeEdit("Test")
        self.assertEqual(field.valueFromText("01:23.450"), 83450)
        self.assertEqual(field.valueFromText("01:23,4"), 83400)
        self.assertEqual(field.validate("01:99.000", 0)[0], QValidator.State.Invalid)

    def test_stereo_toggle_visibility_and_action(self):
        # 1. Mono audio: stereo toggle should be hidden
        self.load()
        self.assertFalse(self.window.stereo_toggle_button.isVisible())

        # 2. Stereo audio: stereo toggle should be visible
        stereo_source = self.root / "stereo_test.wav"
        rate = 48000
        t = np.arange(2 * rate) / rate
        stereo_data = np.column_stack((0.3 * np.sin(2 * np.pi * 440 * t), -0.3 * np.sin(2 * np.pi * 440 * t)))
        sf.write(stereo_source, stereo_data, rate)
        self.window.open_path(stereo_source)
        wait_until(lambda: self.window._job is None)
        self.assertTrue(self.window.stereo_toggle_button.isVisible())
        self.assertEqual(self.window.stereo_toggle_button.text(), "Stereo getrennt")
        self.assertTrue(self.window.waveform.split_stereo)

        # Toggle to combined
        QTest.mouseClick(self.window.stereo_toggle_button, Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.waveform.split_stereo)
        self.assertEqual(self.window.stereo_toggle_button.text(), "Stereo kombiniert")

        # Toggle back to split
        QTest.mouseClick(self.window.stereo_toggle_button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.waveform.split_stereo)
        self.assertEqual(self.window.stereo_toggle_button.text(), "Stereo getrennt")

    def test_waveform_zoom_and_scrollbar_interactions(self):
        self.load()
        self.assertEqual(self.window.zoom_label.text(), "100%")
        self.assertFalse(self.window.waveform_scrollbar.isEnabled())
        self.assertFalse(self.window.zoom_fit_button.isEnabled())
        self.assertFalse(self.window.zoom_out_button.isEnabled())
        self.assertTrue(self.window.zoom_in_button.isEnabled())

        # Zoom in
        QTest.mouseClick(self.window.zoom_in_button, Qt.MouseButton.LeftButton)
        self.assertGreater(self.window.waveform.zoom_level, 1.0)
        self.assertTrue(self.window.waveform_scrollbar.isEnabled())
        self.assertTrue(self.window.zoom_fit_button.isEnabled())
        self.assertTrue(self.window.zoom_out_button.isEnabled())
        self.assertIn("%", self.window.zoom_label.text())

        # Scrollbar panning
        self.window.waveform_scrollbar.setValue(500)
        self.assertEqual(self.window.waveform.view_start_ms, 500)

        # Zoom out
        QTest.mouseClick(self.window.zoom_out_button, Qt.MouseButton.LeftButton)

        # Reset to full file
        QTest.mouseClick(self.window.zoom_fit_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.waveform.zoom_level, 1.0)
        self.assertEqual(self.window.zoom_label.text(), "100%")
        self.assertFalse(self.window.waveform_scrollbar.isEnabled())
        self.assertFalse(self.window.zoom_fit_button.isEnabled())

    def test_waveform_coordinate_scaling_with_zoom(self):
        self.load()
        graph = self.window.waveform.graph_rect()
        self.assertEqual(self.window.waveform.time_at_x(graph.left()), 0)
        self.assertEqual(self.window.waveform.time_at_x(graph.right()), self.window.duration_ms)

        # Zoom in to 2.0x centered at 2000ms
        self.window.waveform.set_zoom(2.0, center_time_ms=2000)
        self.assertEqual(self.window.waveform.visible_duration_ms(), 2000)
        self.assertEqual(self.window.waveform.view_start_ms, 1000)
        self.assertEqual(self.window.waveform.view_end_ms, 3000)
        self.assertEqual(self.window.waveform.time_at_x(graph.left()), 1000)
        self.assertEqual(self.window.waveform.time_at_x(graph.right()), 3000)

    def test_minimum_window_size_has_no_overlapping_rows(self):
        self.window.resize(self.window.minimumSize())
        APP.processEvents()
        layout = self.window.centralWidget().layout()
        previous_bottom = 0
        for index in range(layout.count()):
            geometry = layout.itemAt(index).geometry()
            self.assertGreaterEqual(geometry.top(), previous_bottom)
            previous_bottom = geometry.bottom() + 1
        self.assertLessEqual(previous_bottom, self.window.centralWidget().height())

    def test_help_dialog_search_and_category_filtering(self):
        dialog = HelpDialog(self.window)
        dialog.show()
        APP.processEvents()
        total_topics = len(HELP_TOPICS)
        self.assertGreaterEqual(total_topics, 15)
        self.assertIn(f"{total_topics} Hilfethemen", dialog.count_label.text())
        self.assertTrue(dialog.empty_label.isHidden())

        # Test search query matching
        dialog.search_edit.setText("Strg+X")
        visible_cards = [c for c in dialog._cards if not c.isHidden()]
        self.assertEqual(len(visible_cards), 1)
        self.assertEqual(visible_cards[0].topic.title, "Bereich herausschneiden (Löschen)")

        # Test category filtering
        dialog.search_edit.clear()
        dialog._set_category("Effekte")
        visible_cards = [c for c in dialog._cards if not c.isHidden()]
        self.assertTrue(all(c.topic.category == "Effekte" for c in visible_cards))
        self.assertGreater(len(visible_cards), 0)

        # Test empty state on nonsense query
        dialog.search_edit.setText("unbekannter_audio_effekt_xyz")
        self.assertFalse(dialog.empty_label.isHidden())
        self.assertEqual(len([c for c in dialog._cards if not c.isHidden()]), 0)

        # Test reset
        dialog.search_edit.clear()
        dialog._set_category("Alle")
        self.assertEqual(len([c for c in dialog._cards if not c.isHidden()]), total_topics)
        dialog.close()

    def test_help_dialog_integration_in_window(self):
        self.assertTrue(self.window.help_button.isEnabled())
        self.assertIn("F1", self.window.help_button.toolTip())
        with patch.object(HelpDialog, "exec") as mock_exec:
            self.window.help_button.click()
            mock_exec.assert_called_once()

    def test_language_toggle_switches_all_ui_elements(self):
        # Default German state
        self.assertEqual(get_language(), "de")
        self.assertEqual(self.window.lang_button.text(), "EN")
        self.assertEqual(self.window.open_button.text(), "Öffnen")
        self.assertEqual(self.window.export_button.text(), "Exportieren")
        self.assertEqual(self.window.crop_button.text(), "Zuschneiden")
        self.assertEqual(self.window.delete_selection_button.text(), "Bereich herausschneiden")
        self.assertEqual(self.window.help_button.text(), "Hilfe")

        # Toggle to English
        self.window.lang_button.click()
        self.assertEqual(get_language(), "en")
        self.assertEqual(self.window.lang_button.text(), "DE")
        self.assertEqual(self.window.open_button.text(), "Open")
        self.assertEqual(self.window.export_button.text(), "Export")
        self.assertEqual(self.window.crop_button.text(), "Trim")
        self.assertEqual(self.window.delete_selection_button.text(), "Delete Selection")
        self.assertEqual(self.window.help_button.text(), "Help")
        self.assertIn("simple audio editor", self.window.brand_subtitle.text())
        self.assertEqual(self.window.volume_label.text(), "Volume")
        self.assertEqual(self.window.start_label.text(), "A · Selection Start")
        self.assertEqual(self.window.end_label.text(), "B · Selection End")
        self.assertEqual(self.window.length_label.text(), "Selected Length")

        # English HelpDialog
        en_dialog = HelpDialog(self.window, lang="en")
        self.assertIn("Help & Shortcuts", en_dialog.windowTitle())
        self.assertEqual(en_dialog.categories[0], "All")
        self.assertEqual(en_dialog._cards[0].topic.title, "Open File & Drag and Drop")
        en_dialog.close()

        # Toggle back to German
        self.window.lang_button.click()
        self.assertEqual(get_language(), "de")
        self.assertEqual(self.window.lang_button.text(), "EN")
        self.assertEqual(self.window.open_button.text(), "Öffnen")
        self.assertEqual(self.window.crop_button.text(), "Zuschneiden")


if __name__ == "__main__":
    unittest.main()
