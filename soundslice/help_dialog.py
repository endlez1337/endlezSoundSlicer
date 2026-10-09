"""Searchable help and keyboard shortcuts dialog for endlez Sound Slicer (German / English)."""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .i18n import get_language
from .style import app_icon, icon


@dataclass(frozen=True)
class HelpTopic:
    title: str
    category: str
    shortcut: str = ""
    description: str = ""
    keywords: tuple[str, ...] = ()
    icon_name: str = "help"


HELP_TOPICS_DE: tuple[HelpTopic, ...] = (
    HelpTopic(
        title="Datei öffnen & Drag & Drop",
        category="Grundlagen",
        shortcut="Strg+O",
        description="Öffnet eine Audiodatei (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma). Alternativ kannst du eine Datei direkt per Drag & Drop in das Fenster ziehen.",
        keywords=("öffnen", "open", "laden", "drag", "drop", "import", "datei", "audio"),
        icon_name="open",
    ),
    HelpTopic(
        title="Audio exportieren",
        category="Grundlagen",
        shortcut="Strg+S",
        description="Speichert die gesamte bearbeitete Audiodatei. Die Dateiendung oder der gewählte Filter bestimmt das Format (WAV/FLAC/AIFF verlustfrei; MP3/M4A/AAC/OGG/Opus/WMA komprimiert).",
        keywords=("exportieren", "speichern", "save", "export", "mp3", "wav", "flac", "m4a", "ogg"),
        icon_name="export",
    ),
    HelpTopic(
        title="Wiedergabe & Pause",
        category="Wiedergabe",
        shortcut="Leertaste",
        description="Startet oder pausiert das Abspielen an der aktuellen Wiedergabeposition.",
        keywords=("abspielen", "play", "pause", "leertaste", "space", "anhören", "wiedergabe"),
        icon_name="play",
    ),
    HelpTopic(
        title="Wiedergabe stoppen",
        category="Wiedergabe",
        shortcut="Esc",
        description="Hält die Wiedergabe sofort an und setzt den Abspielzeiger auf den Dateianfang (00:00.000) zurück.",
        keywords=("stop", "stoppen", "halt", "anhalten", "escape", "esc", "dateianfang"),
        icon_name="stop",
    ),
    HelpTopic(
        title="Auswahl vorhören",
        category="Wiedergabe",
        shortcut="",
        description="Spielt ausschließlich den markierten Bereich zwischen Marker A und Marker B ab und stoppt am Ende automatisch.",
        keywords=("auswahl anhören", "preview", "vorhören", "abspielen", "auswahl"),
        icon_name="play",
    ),
    HelpTopic(
        title="Zuschneiden (Freistellen)",
        category="Bearbeiten",
        shortcut="",
        description="Behält ausschließlich den markierten Bereich zwischen A und B. Alle Audiodaten davor und danach werden abgeschnitten.",
        keywords=("zuschneiden", "crop", "freistellen", "trim", "auswahl", "behalten"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Bereich herausschneiden (Löschen)",
        category="Bearbeiten",
        shortcut="Strg+X",
        description="Entfernt den markierten Bereich zwischen A und B und fügt die verbleibenden Teile davor und danach nahtlos ohne Lücke zusammen.",
        keywords=("herausschneiden", "delete", "entfernen", "löschen", "cut", "lücke", "strg+x"),
        icon_name="delete_selection",
    ),
    HelpTopic(
        title="Rückgängig (Multi-Undo)",
        category="Bearbeiten",
        shortcut="Strg+Z",
        description="Macht den letzten Bearbeitungsschritt rückgängig. endlez Sound Slicer speichert bis zu 25 Bearbeitungsschritte im Verlauf.",
        keywords=("rückgängig", "undo", "zurück", "verlauf", "history", "strg+z"),
        icon_name="undo",
    ),
    HelpTopic(
        title="Wiederholen (Redo)",
        category="Bearbeiten",
        shortcut="Strg+Y / Strg+Umschalt+Z",
        description="Stellt zuvor rückgängig gemachte Schritte wieder her.",
        keywords=("wiederholen", "redo", "vorwärts", "verlauf", "strg+y"),
        icon_name="redo",
    ),
    HelpTopic(
        title="Fade In (Sanft einblenden)",
        category="Effekte",
        shortcut="",
        description="Blendet die Lautstärke über den markierten Auswahlbereich sanft von Stille bis zum vollen Pegel ein (natürliche, klickfreie S-Kurve).",
        keywords=("fade in", "einblenden", "fade", "anfang", "leise", "lautstärke", "kurve"),
        icon_name="fade_in",
    ),
    HelpTopic(
        title="Fade Out (Sanft ausblenden)",
        category="Effekte",
        shortcut="",
        description="Blendet die Lautstärke über den markierten Auswahlbereich sanft vom vollen Pegel bis zur Stille aus (natürliche, klickfreie S-Kurve).",
        keywords=("fade out", "ausblenden", "fade", "ende", "leise", "lautstärke", "kurve"),
        icon_name="fade_out",
    ),
    HelpTopic(
        title="Lautstärke normalisieren",
        category="Effekte",
        shortcut="",
        description="Steuert die gesamte Audiodatei optimal auf einen Spitzenpegel von -0.1 dBFS aus. Maximiert die Lautstärke sauber ohne Übersteuerung und verhindert Clipping bei komprimiertem Export.",
        keywords=("normalisieren", "normalize", "lauter", "lautstärke", "pegel", "dbfs", "gain", "clipping"),
        icon_name="normalize",
    ),
    HelpTopic(
        title="Waveform vergrößern & verkleinern",
        category="Waveform & Zoom",
        shortcut="Strg++ / Strg+- / Strg+Mausrad",
        description="Zoomt stufenlos von 100 % (Gesamtansicht) bis 10.000 % in die Wellenform. Zoomen per Strg+Mausrad zentriert sich direkt am Mauszeiger.",
        keywords=("zoom", "zoomen", "vergrößern", "verkleinern", "lupe", "mausrad", "detail", "waveform"),
        icon_name="zoom_in",
    ),
    HelpTopic(
        title="Zoom zurücksetzen (Ganze Datei)",
        category="Waveform & Zoom",
        shortcut="Strg+0",
        description="Setzt die Ansicht sofort auf die vollständige Audiodatei (100 %) zurück.",
        keywords=("zoom zurücksetzen", "ganze datei", "fit", "100%", "reset", "vollansicht"),
        icon_name="zoom_fit",
    ),
    HelpTopic(
        title="Navigation & Panning",
        category="Waveform & Zoom",
        shortcut="Mausrad / Mittlere Maustaste",
        description="Bei vergrößerter Waveform kannst du die horizontale Scrollbar verwenden, mit dem Mausrad seitlich scrollen oder mit gedrückter mittlerer Maustaste die Wellenform greifen und verschieben.",
        keywords=("scrollen", "panning", "verschieben", "scrollbar", "mittlere maustaste", "navigieren"),
        icon_name="zoom_out",
    ),
    HelpTopic(
        title="Zweikanalige Stereo-Ansicht (Split L/R)",
        category="Waveform & Zoom",
        shortcut="",
        description="Bei Stereo-Audiodateien werden der linke und rechte Kanal getrennt übereinander mit Pegelachsen und Kanal-Badges angezeigt. Der Button 'Stereo getrennt / kombiniert' schaltet auf Wunsch um.",
        keywords=("stereo", "mono", "kanäle", "links", "rechts", "split", "zweikanalig", "l", "r"),
        icon_name="stereo",
    ),
    HelpTopic(
        title="Marker A an aktuelle Position setzen",
        category="Bearbeiten",
        shortcut="A",
        description="Setzt den Startpunkt A der Auswahl exakt auf die aktuelle Wiedergabe- bzw. Playhead-Position.",
        keywords=("marker a", "start", "position", "anfang", "a"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Marker B an aktuelle Position setzen",
        category="Bearbeiten",
        shortcut="B",
        description="Setzt den Endpunkt B der Auswahl exakt auf die aktuelle Wiedergabe- bzw. Playhead-Position.",
        keywords=("marker b", "ende", "position", "schluss", "b"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Alles davor / danach entfernen",
        category="Bearbeiten",
        shortcut="",
        description="'Alles davor entfernen' löscht den Bereich vor Marker A. 'Alles danach entfernen' löscht den Bereich nach Marker B.",
        keywords=("alles davor", "alles danach", "trim", "anfang löschen", "ende löschen"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Hilfe & Tastenkürzel aufrufen",
        category="Grundlagen",
        shortcut="F1 oder ?",
        description="Öffnet dieses durchsuchbare Hilfe- und Tastenkürzelfenster.",
        keywords=("hilfe", "help", "faq", "tastatur", "shortcuts", "f1", "fragezeichen"),
        icon_name="help",
    ),
)


HELP_TOPICS_EN: tuple[HelpTopic, ...] = (
    HelpTopic(
        title="Open File & Drag and Drop",
        category="Basics",
        shortcut="Ctrl+O",
        description="Opens an audio file (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma). You can also drag and drop an audio file directly into the window.",
        keywords=("open", "load", "import", "file", "drag", "drop", "audio"),
        icon_name="open",
    ),
    HelpTopic(
        title="Export Audio",
        category="Basics",
        shortcut="Ctrl+S",
        description="Exports the complete edited audio file. The file extension or selected filter determines the format (WAV/FLAC/AIFF lossless; MP3/M4A/AAC/OGG/Opus/WMA compressed).",
        keywords=("export", "save", "mp3", "wav", "flac", "m4a", "ogg", "opus"),
        icon_name="export",
    ),
    HelpTopic(
        title="Play & Pause",
        category="Playback",
        shortcut="Space",
        description="Starts or pauses audio playback at the current playhead position.",
        keywords=("play", "pause", "space", "listen", "playback"),
        icon_name="play",
    ),
    HelpTopic(
        title="Stop Playback",
        category="Playback",
        shortcut="Esc",
        description="Immediately stops playback and rewinds the playhead to the beginning of the file (00:00.000).",
        keywords=("stop", "halt", "rewind", "start", "esc", "escape"),
        icon_name="stop",
    ),
    HelpTopic(
        title="Play Selection",
        category="Playback",
        shortcut="",
        description="Plays only the selected audio range between Marker A and Marker B, automatically stopping at the end.",
        keywords=("preview", "selection", "play selection", "listen"),
        icon_name="play",
    ),
    HelpTopic(
        title="Trim (Crop Selection)",
        category="Edit",
        shortcut="",
        description="Keeps only the selected range between Marker A and Marker B. All audio before and after is discarded.",
        keywords=("trim", "crop", "keep", "cut", "isolate"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Delete Selection",
        category="Edit",
        shortcut="Ctrl+X",
        description="Deletes the selected range between Marker A and Marker B and seamlessly joins the remaining parts before and after without a gap.",
        keywords=("delete", "cut", "remove", "gap", "ctrl+x"),
        icon_name="delete_selection",
    ),
    HelpTopic(
        title="Undo (Multi-Level History)",
        category="Edit",
        shortcut="Ctrl+Z",
        description="Reverts the last editing action. endlez Sound Slicer retains up to 25 steps in its undo history.",
        keywords=("undo", "revert", "history", "ctrl+z", "back"),
        icon_name="undo",
    ),
    HelpTopic(
        title="Redo",
        category="Edit",
        shortcut="Ctrl+Y / Ctrl+Shift+Z",
        description="Restores previously undone editing actions.",
        keywords=("redo", "forward", "history", "ctrl+y"),
        icon_name="redo",
    ),
    HelpTopic(
        title="Fade In",
        category="Effects",
        shortcut="",
        description="Smoothly fades in volume across the active selection from silence to full volume (click-free S-curve).",
        keywords=("fade in", "fade", "volume", "quiet", "start", "curve"),
        icon_name="fade_in",
    ),
    HelpTopic(
        title="Fade Out",
        category="Effects",
        shortcut="",
        description="Smoothly fades out volume across the active selection from full volume to silence (click-free S-curve).",
        keywords=("fade out", "fade", "volume", "quiet", "end", "curve"),
        icon_name="fade_out",
    ),
    HelpTopic(
        title="Normalize Audio",
        category="Effects",
        shortcut="",
        description="Optimizes the overall loudness so the loudest peak reaches exactly -0.1 dBFS. Maximizes clarity and prevents clipping in lossy exports.",
        keywords=("normalize", "loudness", "gain", "peak", "dbfs", "clipping", "volume"),
        icon_name="normalize",
    ),
    HelpTopic(
        title="Waveform Zoom In & Out",
        category="Waveform & Zoom",
        shortcut="Ctrl++ / Ctrl+- / Ctrl+Wheel",
        description="Seamlessly zooms the waveform from 100% (full file) up to 10,000%. Ctrl+Mouse Wheel zooms centered directly at your cursor position.",
        keywords=("zoom", "magnify", "scale", "wheel", "mouse", "detail"),
        icon_name="zoom_in",
    ),
    HelpTopic(
        title="Reset Zoom (Full File)",
        category="Waveform & Zoom",
        shortcut="Ctrl+0",
        description="Instantly resets the waveform zoom to display the entire audio file (100%).",
        keywords=("reset zoom", "fit", "full file", "100%", "all"),
        icon_name="zoom_fit",
    ),
    HelpTopic(
        title="Navigation & Panning",
        category="Waveform & Zoom",
        shortcut="Mouse Wheel / Middle Drag",
        description="When zoomed in, use the horizontal scrollbar, scroll with the mouse wheel, or middle-click and drag to pan across the waveform.",
        keywords=("pan", "panning", "scroll", "scrollbar", "middle mouse", "navigate"),
        icon_name="zoom_out",
    ),
    HelpTopic(
        title="Dual-Channel Stereo View (Split L/R)",
        category="Waveform & Zoom",
        shortcut="",
        description="For stereo files, the left and right channels are rendered stacked with center axes and badges. Toggle button switches to a combined mono view.",
        keywords=("stereo", "mono", "channels", "left", "right", "split", "dual"),
        icon_name="stereo",
    ),
    HelpTopic(
        title="Set Marker A to Current Position",
        category="Edit",
        shortcut="A",
        description="Snaps start point A of the selection directly to the current playback position.",
        keywords=("marker a", "start", "position", "snap", "a"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Set Marker B to Current Position",
        category="Edit",
        shortcut="B",
        description="Snaps end point B of the selection directly to the current playback position.",
        keywords=("marker b", "end", "position", "snap", "b"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Remove Before / Remove After",
        category="Edit",
        shortcut="",
        description="'Remove Before' deletes all audio before Marker A. 'Remove After' deletes all audio after Marker B.",
        keywords=("remove before", "remove after", "trim edges", "crop start", "crop end"),
        icon_name="cut",
    ),
    HelpTopic(
        title="Open Help & Shortcuts",
        category="Basics",
        shortcut="F1 or ?",
        description="Opens this searchable help and shortcuts dialog.",
        keywords=("help", "shortcuts", "keys", "faq", "f1", "question"),
        icon_name="help",
    ),
)

# For backward compatibility with existing tests
HELP_TOPICS = HELP_TOPICS_DE


class TopicCard(QFrame):
    """Visual card displaying a single help topic with icon, category, and shortcut badge."""

    def __init__(self, topic: HelpTopic, parent: QWidget | None = None):
        super().__init__(parent)
        self.topic = topic
        self.setObjectName("topicCard")
        self.setStyleSheet("""
            QFrame#topicCard {
                background: #181d24;
                border: 1px solid #28313c;
                border-radius: 10px;
            }
            QFrame#topicCard:hover {
                border-color: #3f4e60;
                background: #1c222b;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: #172826; border-radius: 8px; border: 1px solid #23433f;")
        icon_label.setPixmap(icon(topic.icon_name, "#85dccb", size=20).pixmap(20, 20))
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title_label = QLabel(topic.title)
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #ecf5f7;")
        header_row.addWidget(title_label)

        cat_badge = QLabel(topic.category)
        cat_badge.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #7f8f9f; background: #222a33; "
            "border-radius: 4px; padding: 2px 6px;"
        )
        header_row.addWidget(cat_badge)
        header_row.addStretch()
        text_layout.addLayout(header_row)

        desc_label = QLabel(topic.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; color: #9bb0c4; line-height: 1.4;")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        if topic.shortcut:
            shortcut_badge = QLabel(topic.shortcut)
            shortcut_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            shortcut_badge.setStyleSheet(
                "font-family: 'Consolas'; font-size: 12px; font-weight: 600; "
                "color: #e2f8f3; background: #1f2732; border: 1px solid #364455; "
                "border-radius: 6px; padding: 4px 10px;"
            )
            layout.addWidget(shortcut_badge, 0, Qt.AlignmentFlag.AlignVCenter)

    def matches(self, query: str, category: str) -> bool:
        """Check whether this topic matches the current query and category filter."""
        all_labels = ("Alle", "All")
        shortcut_labels = ("Tastenkürzel", "Shortcuts")

        if category not in all_labels:
            if category in shortcut_labels:
                if not self.topic.shortcut:
                    return False
            elif self.topic.category != category:
                # Map German and English category names if cross-filtered
                cat_pairs = {
                    "Bearbeiten": "Edit", "Edit": "Bearbeiten",
                    "Effekte": "Effects", "Effects": "Effekte",
                    "Grundlagen": "Basics", "Basics": "Grundlagen",
                    "Wiedergabe": "Playback", "Playback": "Wiedergabe",
                    "Waveform & Zoom": "Waveform & Zoom",
                }
                if cat_pairs.get(category) != self.topic.category:
                    return False

        if not query:
            return True

        normalized_query = query.strip().lower()
        if normalized_query in self.topic.title.lower():
            return True
        if normalized_query in self.topic.description.lower():
            return True
        if normalized_query in self.topic.shortcut.lower():
            return True
        for keyword in self.topic.keywords:
            if normalized_query in keyword.lower():
                return True
        return False


class HelpDialog(QDialog):
    """Interactive searchable help and keyboard shortcuts overlay."""

    CATEGORIES_DE = ("Alle", "Tastenkürzel", "Bearbeiten", "Effekte", "Waveform & Zoom", "Grundlagen", "Wiedergabe")
    CATEGORIES_EN = ("All", "Shortcuts", "Edit", "Effects", "Waveform & Zoom", "Basics", "Playback")

    def __init__(self, parent: QWidget | None = None, initial_query: str = "", lang: str | None = None):
        super().__init__(parent)
        self.lang = lang or get_language()
        self.is_en = self.lang == "en"
        self.categories = self.CATEGORIES_EN if self.is_en else self.CATEGORIES_DE
        self._active_category = self.categories[0]
        self._cards: list[TopicCard] = []

        title_text = "endlez Sound Slicer · Help & Shortcuts" if self.is_en else "endlez Sound Slicer · Hilfe & Tastenkürzel"
        self.setWindowTitle(title_text)
        self.setWindowIcon(app_icon())
        self.resize(760, 600)
        self.setMinimumSize(620, 480)

        self._build_ui()
        if initial_query:
            self.search_edit.setText(initial_query)
        self._filter_topics()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 18)
        main_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_icon = QLabel()
        header_icon.setFixedSize(40, 40)
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_icon.setStyleSheet("background: #1b3432; border-radius: 10px;")
        header_icon.setPixmap(icon("help", "#85dccb", size=24).pixmap(24, 24))
        header_row.addWidget(header_icon)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title_str = "endlez Sound Slicer Help & Shortcuts" if self.is_en else "endlez Sound Slicer Hilfe & Shortcuts"
        subtitle_str = (
            "Search all editing tools, keyboard shortcuts, and audio features."
            if self.is_en else
            "Durchsuche alle Bearbeitungswerkzeuge, Tastenkürzel und Audio-Funktionen."
        )
        title = QLabel(title_str)
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #ecf5f7; letter-spacing: -0.4px;")
        subtitle = QLabel(subtitle_str)
        subtitle.setStyleSheet("font-size: 13px; color: #8996a7;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()

        close_top_btn = QPushButton("✕")
        close_top_btn.setFixedSize(30, 30)
        close_top_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 16px; color: #8996a7; border-radius: 6px; }"
            "QPushButton:hover { background: #222a34; color: #ecf5f7; }"
        )
        close_top_btn.clicked.connect(self.accept)
        header_row.addWidget(close_top_btn, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header_row)

        self.search_edit = QLineEdit()
        placeholder_str = (
            "Type to search (e.g. 'trim', 'fade', 'Ctrl+Z', 'normalize', 'stereo')..."
            if self.is_en else
            "Tippe zum Suchen (z. B. 'schneiden', 'fade', 'Strg+Z', 'normalisieren', 'stereo')..."
        )
        self.search_edit.setPlaceholderText(placeholder_str)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet(
            "QLineEdit { background: #131920; border: 1px solid #323d4b; border-radius: 9px; "
            "padding: 10px 14px; font-size: 14px; color: #ecf5f7; } "
            "QLineEdit:focus { border-color: #85dccb; background: #161e27; }"
        )
        self.search_edit.textChanged.connect(self._filter_topics)
        main_layout.addWidget(self.search_edit)

        cats_row = QHBoxLayout()
        cats_row.setSpacing(6)
        self._cat_buttons: dict[str, QPushButton] = {}
        for cat in self.categories:
            btn = QPushButton(cat)
            btn.setObjectName("catButton")
            btn.setCheckable(True)
            if cat == self.categories[0]:
                btn.setChecked(True)
            btn.setStyleSheet(self._cat_button_style(cat == self.categories[0]))
            btn.clicked.connect(lambda checked=False, c=cat: self._set_category(c))
            cats_row.addWidget(btn)
            self._cat_buttons[cat] = btn
        cats_row.addStretch()
        main_layout.addLayout(cats_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(scroll_content)
        self.cards_layout.setContentsMargins(0, 4, 4, 4)
        self.cards_layout.setSpacing(8)

        topics = HELP_TOPICS_EN if self.is_en else HELP_TOPICS_DE
        for topic in topics:
            card = TopicCard(topic, scroll_content)
            self._cards.append(card)
            self.cards_layout.addWidget(card)

        empty_str = "No matching help topics found." if self.is_en else "Keine passenden Hilfethemen gefunden."
        self.empty_label = QLabel(empty_str)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #728294; font-size: 14px; padding: 40px 0;")
        self.empty_label.hide()
        self.cards_layout.addWidget(self.empty_label)

        self.cards_layout.addStretch()
        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(12)
        self.count_label = QLabel()
        self.count_label.setStyleSheet("font-size: 12px; color: #7f8f9f;")
        footer_row.addWidget(self.count_label)
        footer_row.addStretch()

        close_str = "Close (Esc)" if self.is_en else "Schließen (Esc)"
        close_btn = QPushButton(close_str)
        close_btn.setObjectName("small")
        close_btn.clicked.connect(self.accept)
        footer_row.addWidget(close_btn)
        main_layout.addLayout(footer_row)

    def _cat_button_style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background: #85dccb; color: #112622; border: 1px solid #85dccb; "
                "border-radius: 14px; padding: 5px 12px; font-weight: 600; font-size: 12px; } "
                "QPushButton:hover { background: #a2eadc; }"
            )
        return (
            "QPushButton { background: #1c222a; color: #9bb0c4; border: 1px solid #2d3744; "
            "border-radius: 14px; padding: 5px 12px; font-weight: 500; font-size: 12px; } "
            "QPushButton:hover { background: #262e39; color: #e8edf3; border-color: #3e4c5c; }"
        )

    def _set_category(self, category: str):
        self._active_category = category
        for name, btn in self._cat_buttons.items():
            active = name == category
            btn.setChecked(active)
            btn.setStyleSheet(self._cat_button_style(active))
        self._filter_topics()

    def _filter_topics(self):
        query = self.search_edit.text()
        visible_count = 0
        for card in self._cards:
            matches = card.matches(query, self._active_category)
            card.setVisible(matches)
            if matches:
                visible_count += 1

        self.empty_label.setVisible(visible_count == 0)
        total = len(self._cards)
        all_labels = ("Alle", "All")
        if query or self._active_category not in all_labels:
            if self.is_en:
                self.count_label.setText(f"{visible_count} of {total} topics")
            else:
                self.count_label.setText(f"{visible_count} von {total} Themen")
        else:
            if self.is_en:
                self.count_label.setText(f"{total} help topics available")
            else:
                self.count_label.setText(f"{total} Hilfethemen verfügbar")
