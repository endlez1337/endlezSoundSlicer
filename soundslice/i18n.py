"""Lightweight internationalization (German / English) for endlez Sound Slicer."""

from typing import Callable

_current_lang = "de"
_listeners: list[Callable[[str], None]] = []


TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        "app_title": "endlez Sound Slicer",
        "app_subtitle": "Der einfache Audio-Editor",
        "open": "Öffnen",
        "open_tooltip": "Audio-Datei öffnen (Strg+O)",
        "help": "Hilfe",
        "help_tooltip": "Hilfe und Tastenkürzel anzeigen (F1 oder ?)",
        "undo": "Rückgängig",
        "undo_tooltip": "Rückgängig (Strg+Z)",
        "redo": "Wiederholen",
        "redo_tooltip": "Wiederholen (Strg+Y)",
        "export": "Exportieren",
        "export_tooltip": "Die gesamte bearbeitete Datei exportieren (Strg+S)",
        "lang_btn": "EN",
        "lang_tooltip": "Switch to English / Auf Englisch wechseln",
        "empty_file_name": "Platz für deinen nächsten Schnitt",
        "empty_file_meta": "Öffnen → Anhören → Auswählen → Zuschneiden → Exportieren",
        "play": "Abspielen",
        "pause": "Pause",
        "play_tooltip": "Abspielen / Pause (Leertaste)",
        "stop": "Stop",
        "stop_tooltip": "Wiedergabe stoppen und zum Anfang springen (Esc)",
        "preview_button": "Auswahl anhören",
        "preview_tooltip": "Nur die Auswahl abspielen, ohne die Datei zu verändern",
        "crop": "Zuschneiden",
        "crop_tooltip": "Nur die Auswahl behalten; alles davor und danach entfernen",
        "delete_selection": "Bereich herausschneiden",
        "delete_selection_tooltip": "Ausgewählten Bereich entfernen und verbleibende Teile nahtlos zusammenfügen (Strg+X)",
        "set_start": "Start = Position",
        "set_start_tooltip": "Startpunkt auf die aktuelle Position setzen (A)",
        "set_end": "Ende = Position",
        "set_end_tooltip": "Endpunkt auf die aktuelle Position setzen (B)",
        "select_all": "Alles auswählen",
        "select_all_tooltip": "Auswahl auf die vollständige Datei zurücksetzen",
        "fade_in": "Fade In",
        "fade_in_tooltip": "Sanftes Einblenden über die markierte Auswahl",
        "fade_out": "Fade Out",
        "fade_out_tooltip": "Sanftes Ausblenden über die markierte Auswahl",
        "normalize": "Normalisieren",
        "normalize_tooltip": "Gesamte Datei auf optimalen Spitzenpegel (-0.1 dBFS) aussteuern",
        "remove_before": "Alles davor entfernen",
        "remove_before_tooltip": "Alles vor A entfernen; Audio ab A bis zum Dateiende behalten",
        "remove_after": "Alles danach entfernen",
        "remove_after_tooltip": "Alles nach B entfernen; Audio vom Dateianfang bis B behalten",
        "zoom_out_tooltip": "Verkleinern (Strg+-)",
        "zoom_in_tooltip": "Vergrößern (Strg++)",
        "zoom_fit": "Ganze Datei",
        "zoom_fit_tooltip": "Ganze Datei anzeigen (Strg+0)",
        "stereo_split": "Stereo getrennt",
        "stereo_combined": "Stereo kombiniert",
        "stereo_tooltip": "Zwischen getrennter linker/rechter Spur und kombinierter Ansicht umschalten",
        "selection_start": "A · Auswahl Start",
        "selection_end": "B · Auswahl Ende",
        "selected_length": "Ausgewählte Länge",
        "status_ready": "Bereit · Audio-Datei öffnen (WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA)",
        "status_loaded": "Geladen · Bereich in der Waveform ziehen oder Zeiten eingeben",
        "status_loading": "Audio wird geladen …",
        "status_cropping": "Auswahl wird zugeschnitten …",
        "status_cropped": "Zugeschnitten",
        "status_deleting": "Bereich wird herausgeschnitten …",
        "status_deleted": "Bereich herausgeschnitten",
        "status_normalizing": "Lautstärke wird normalisiert …",
        "status_normalized": "Normalisiert ({gain_db:+.1f} dB)",
        "status_fading_in": "Fade In wird angewendet …",
        "status_faded_in": "Fade In angewendet",
        "status_fading_out": "Fade Out wird angewendet …",
        "status_faded_out": "Fade Out angewendet",
        "status_exporting": "Audio wird exportiert …",
        "status_exported": "Exportiert nach {filename}",
        "status_undone": "Rückgängig gemacht: {action}",
        "status_redone": "Wiederholt: {action}",
        "history_single": "1 im Verlauf",
        "history_multi": "{count} im Verlauf",
        "action_crop": "Zuschneiden",
        "action_delete": "Bereich herausschneiden",
        "action_normalize": "Normalisieren",
        "action_fade_in": "Fade In",
        "action_fade_out": "Fade Out",
        "action_remove_before": "Alles davor entfernen",
        "action_remove_after": "Alles danach entfernen",
        "discard_title": "Änderungen verwerfen?",
        "discard_text": "Die letzten Änderungen wurden noch nicht exportiert. Verwerfen?",
        "discard_btn": "Verwerfen",
        "cancel_btn": "Abbrechen",
        "export_replace_title": "Datei ersetzen?",
        "export_replace_text": "'{name}' existiert bereits. Überschreiben?",
        "export_replace_btn": "Ersetzen",
        "file_dialog_open_title": "Audio-Datei öffnen",
        "file_dialog_export_title": "Audio exportieren",
        "file_filter_all": "Alle unterstützten Audioformate",
        "waveform_drop_prompt": "Audiodatei hier ablegen oder Öffnen klicken",
        "waveform_drop_subtext": "WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA · Bis zu 30 Minuten",
        "channel_mono": "Mono",
        "channel_stereo": "Stereo",
            "badge_edited": "Bearbeitet",
        "volume": "Lautstärke",
        "waveform_open_prompt": "Audiodatei hier ablegen oder Öffnen klicken",
        "waveform_open_subtext": "WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA · Bis zu 30 Minuten",
        "waveform_tooltip": "Klicken: Abspielen · Ziehen: Bereich · Strg+Mausrad: Zoomen · Mausrad: Scrollen",
        "waveform_empty_tooltip": "Hier klicken oder Audiodatei per Drag & Drop ablegen",
        "waveform_hint": "Klicken: Abspielen · Ziehen: Bereich · A/B: Grenzen · Strg+Mausrad: Zoomen · Mausrad: Scrollen",
        "scrollbar_tooltip": "Horizontales Scrollen durch die Waveform bei aktivem Zoom",
        "slider_tooltip": "Wiedergabeposition verschieben",
        "time_edit_tooltip": "Zeit eingeben, z. B. 01:23.450. Pfeiltasten ändern die Zeit um eine Sekunde.",
        "playback_unavailable": "Wiedergabe nicht verfügbar · {message}",
        "status_action_done": "{action} angewendet · Bei Bedarf exportieren",
        "status_action_running": "{action} wird ausgeführt …",
        "status_fade_running": "{action} wird berechnet …",
        "status_fade_done": "{action} angewendet · Bei Bedarf mit Strg+Z zurücknehmen",
        "status_normalizing_running": "Audio wird normalisiert …",
        "status_normalized_done": "Normalisiert (-0.1 dBFS, Pegelanpassung: {sign}{gain_db:.1f} dB) · Strg+Z zum Rückgängigmachen",
        "status_closing": "Die laufende Verarbeitung wird beendet; danach schließt das Fenster.",
        "invalid_ext_title": "Ungültiger Dateiname",
        "invalid_ext_text": "Bitte eine unterstützte Dateiendung (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma) verwenden.",
        "error_audio_processing": "Audio konnte nicht verarbeitet werden",
},
    "en": {
        "app_title": "endlez Sound Slicer",
        "app_subtitle": "The simple audio editor",
        "open": "Open",
        "open_tooltip": "Open audio file (Ctrl+O)",
        "help": "Help",
        "help_tooltip": "Show help and keyboard shortcuts (F1 or ?)",
        "undo": "Undo",
        "undo_tooltip": "Undo (Ctrl+Z)",
        "redo": "Redo",
        "redo_tooltip": "Redo (Ctrl+Y)",
        "export": "Export",
        "export_tooltip": "Export the entire edited audio file (Ctrl+S)",
        "lang_btn": "DE",
        "lang_tooltip": "Auf Deutsch wechseln / Switch to German",
        "empty_file_name": "Ready for your next cut",
        "empty_file_meta": "Open → Listen → Select → Trim → Export",
        "play": "Play",
        "pause": "Pause",
        "play_tooltip": "Play / Pause (Space)",
        "stop": "Stop",
        "stop_tooltip": "Stop playback and rewind to start (Esc)",
        "preview_button": "Play Selection",
        "preview_tooltip": "Play only the selection without modifying the file",
        "crop": "Trim",
        "crop_tooltip": "Keep only the selection; remove everything before and after",
        "delete_selection": "Delete Selection",
        "delete_selection_tooltip": "Delete selected range and seamlessly merge remaining parts (Ctrl+X)",
        "set_start": "Start = Position",
        "set_start_tooltip": "Set selection start to current playback position (A)",
        "set_end": "End = Position",
        "set_end_tooltip": "Set selection end to current playback position (B)",
        "select_all": "Select All",
        "select_all_tooltip": "Select the entire audio file",
        "fade_in": "Fade In",
        "fade_in_tooltip": "Smoothly fade in over the selected range",
        "fade_out": "Fade Out",
        "fade_out_tooltip": "Smoothly fade out over the selected range",
        "normalize": "Normalize",
        "normalize_tooltip": "Normalize entire file to optimal peak level (-0.1 dBFS)",
        "remove_before": "Remove Before",
        "remove_before_tooltip": "Remove audio before A; keep audio from A to the end",
        "remove_after": "Remove After",
        "remove_after_tooltip": "Remove audio after B; keep audio from start to B",
        "zoom_out_tooltip": "Zoom Out (Ctrl+-)",
        "zoom_in_tooltip": "Zoom In (Ctrl++)",
        "zoom_fit": "Full File",
        "zoom_fit_tooltip": "Fit entire file into view (Ctrl+0)",
        "stereo_split": "Split Stereo",
        "stereo_combined": "Combined Stereo",
        "stereo_tooltip": "Toggle between split left/right tracks and combined view",
        "selection_start": "A · Selection Start",
        "selection_end": "B · Selection End",
        "selected_length": "Selected Length",
        "status_ready": "Ready · Open an audio file (WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA)",
        "status_loaded": "Loaded · Drag on waveform to select or enter times",
        "status_loading": "Loading audio …",
        "status_cropping": "Trimming selection …",
        "status_cropped": "Trimmed",
        "status_deleting": "Deleting selection …",
        "status_deleted": "Selection deleted",
        "status_normalizing": "Normalizing volume …",
        "status_normalized": "Normalized ({gain_db:+.1f} dB)",
        "status_fading_in": "Applying Fade In …",
        "status_faded_in": "Fade In applied",
        "status_fading_out": "Applying Fade Out …",
        "status_faded_out": "Fade Out applied",
        "status_exporting": "Exporting audio …",
        "status_exported": "Exported to {filename}",
        "status_undone": "Undone: {action}",
        "status_redone": "Redone: {action}",
        "history_single": "1 in history",
        "history_multi": "{count} in history",
        "action_crop": "Trim",
        "action_delete": "Delete Selection",
        "action_normalize": "Normalize",
        "action_fade_in": "Fade In",
        "action_fade_out": "Fade Out",
        "action_remove_before": "Remove Before",
        "action_remove_after": "Remove After",
        "discard_title": "Discard changes?",
        "discard_text": "Recent changes have not been exported yet. Discard?",
        "discard_btn": "Discard",
        "cancel_btn": "Cancel",
        "export_replace_title": "Replace file?",
        "export_replace_text": "'{name}' already exists. Overwrite?",
        "export_replace_btn": "Replace",
        "file_dialog_open_title": "Open Audio File",
        "file_dialog_export_title": "Export Audio",
        "file_filter_all": "All supported audio formats",
        "waveform_drop_prompt": "Drop audio file here or click Open",
        "waveform_drop_subtext": "WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA · Up to 30 minutes",
        "channel_mono": "Mono",
        "channel_stereo": "Stereo",
        "badge_edited": "Edited",
        "volume": "Volume",
        "waveform_open_prompt": "Drop audio file here or click Open",
        "waveform_open_subtext": "WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA · Up to 30 minutes",
        "waveform_tooltip": "Click: Play · Drag: Selection · Ctrl+Wheel: Zoom · Scroll: Pan",
        "waveform_empty_tooltip": "Click here or drag and drop an audio file to open",
        "waveform_hint": "Click: Play · Drag: Selection · A/B: Bounds · Ctrl+Wheel: Zoom · Scroll: Pan",
        "scrollbar_tooltip": "Scroll horizontally through waveform when zoomed in",
        "slider_tooltip": "Seek playback position",
        "time_edit_tooltip": "Enter time, e.g. 01:23.450. Arrow keys adjust by 1 second.",
        "playback_unavailable": "Playback unavailable · {message}",
        "status_action_done": "{action} applied · Export when ready",
        "status_action_running": "Applying {action} …",
        "status_fade_running": "Calculating {action} …",
        "status_fade_done": "{action} applied · Press Ctrl+Z to undo",
        "status_normalizing_running": "Normalizing audio …",
        "status_normalized_done": "Normalized (-0.1 dBFS, gain adjustment: {sign}{gain_db:.1f} dB) · Ctrl+Z to undo",
        "status_closing": "Finishing current operation before closing.",
        "invalid_ext_title": "Invalid file format",
        "invalid_ext_text": "Please choose a supported file extension (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma).",
        "error_audio_processing": "Audio processing failed",
    },
}


def get_language() -> str:
    """Return currently active language code ('de' or 'en')."""
    return _current_lang


def set_language(lang: str) -> None:
    """Set the active language ('de' or 'en') and notify registered listeners."""
    global _current_lang
    if lang not in TRANSLATIONS:
        lang = "de"
    if _current_lang != lang:
        _current_lang = lang
        for callback in list(_listeners):
            try:
                callback(_current_lang)
            except Exception:
                pass


def toggle_language() -> str:
    """Toggle between German and English and return the new language."""
    new_lang = "en" if _current_lang == "de" else "de"
    set_language(new_lang)
    return new_lang


def register_listener(callback: Callable[[str], None]) -> None:
    """Register a callback invoked whenever the language changes."""
    if callback not in _listeners:
        _listeners.append(callback)


def unregister_listener(callback: Callable[[str], None]) -> None:
    """Unregister a language change callback."""
    if callback in _listeners:
        _listeners.remove(callback)


def t(key: str, **kwargs) -> str:
    """Translate key for current language with optional string formatting."""
    lang_dict = TRANSLATIONS.get(_current_lang, TRANSLATIONS["de"])
    template = lang_dict.get(key)
    if template is None:
        template = TRANSLATIONS["de"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
