# endlez Sound Slicer

Ein schneller, moderner Audio-Editor für Windows: **Öffnen → Anhören → Auswählen → Schneiden → Exportieren**.
Entwickelt von **endlez**. Die Oberfläche ist vollständig mit PySide6 gebaut, im modernen Dark Mode mit Zoom-Waveform und Stereo-Split.

![endlez Sound Slicer mit Waveform und Auswahl](preview.png)

## Voraussetzungen

- Windows 10/11, 64 Bit
- Python **3.11 bis 3.14**, 64 Bit; Python 3.12 oder 3.13 ist ebenfalls geeignet
- Ein eingerichtetes Audio-Ausgabegerät für die Wiedergabe
- Internetzugang einmalig zum Installieren der Abhängigkeiten

## Installation

Repository klonen oder ZIP entpacken und eine PowerShell im Projektordner öffnen. Dann:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Falls der Python-Befehl auf deinem Rechner `py` heißt, ersetze den ersten Befehl durch
`py -3 -m venv .venv`. Eine Aktivierung der virtuellen Umgebung ist nicht erforderlich.

## Starten

```powershell
.\.venv\Scripts\python.exe main.py
```

Nach der Installation funktioniert auch ein Doppelklick auf **`start.bat`**.
Eine Datei lässt sich direkt beim Start übergeben:

```powershell
.\.venv\Scripts\python.exe main.py "C:\Audio\aufnahme.mp3"
```

## Unterstützte Audioformate & FFmpeg

- **WAV, FLAC & AIFF:** Verlustfreie Formate (24-Bit PCM). Bearbeitung und Export erfolgen direkt über SoundFile.
- **OGG Vorbis:** Freies, verlustbehaftetes Format. Export direkt über SoundFile Vorbis.
- **MP3, M4A, AAC, Opus & WMA:** Komprimierte Formate werden mit FFmpeg dekodiert. Der Export nutzt die bewährten Encoder:
  - MP3: `libmp3lame` (VBR Q2)
  - M4A: `aac` (192 kbps, MP4-Container mit `+faststart`)
  - AAC: `aac` (192 kbps, ADTS-Rohstream)
  - Opus: `libopus` (128 kbps)
  - WMA: `wmav2` (192 kbps)

Das über `requirements.txt` installierte Paket **imageio-ffmpeg** enthält bei der normalen
Windows-Installation bereits eine passende FFmpeg-Datei. Eine separate Installation oder
`ffprobe` ist dann nicht nötig.

Eine eigene FFmpeg-Version kannst du über [die FFmpeg-Downloadseite](https://ffmpeg.org/download.html)
beziehen und für die aktuelle PowerShell festlegen:

```powershell
$env:IMAGEIO_FFMPEG_EXE = "C:\Tools\ffmpeg\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe main.py
```

Es wird zuerst `IMAGEIO_FFMPEG_EXE`, anschließend das mitgelieferte FFmpeg und danach
gegebenenfalls eine vorhandene Systeminstallation gesucht.
Details zur Suche: [imageio-ffmpeg-Dokumentation](https://github.com/imageio/imageio-ffmpeg#environment-variables).

## Bedienung

1. **Öffnen** klicken und eine Datei auswählen (`.wav`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.m4a`, `.aac`, `.aiff`, `.wma`). Alternativ eine Datei ins Fenster ziehen.
2. **Abspielen**, **Pause** und **Stop** verwenden. Stop setzt die Position auf den Dateianfang zurück.
3. In die Waveform klicken, um zu einer Stelle zu springen. Auch der Regler unter der Wiedergabe springt zu einer Position.
4. Einen Bereich in der Waveform ziehen oder die Griffe **A** und **B** verschieben.
   Für genaue Werte die Felder **Auswahl Start** und **Auswahl Ende** bearbeiten, z. B. `01:23.450`,
   und mit Enter bestätigen. Dezimalkomma wird ebenfalls akzeptiert.
5. **Auswahl anhören** spielt nur den markierten Bereich. Die Wiedergabe hält an dessen Ende an.
6. **Zuschneiden** behält ausschließlich die Auswahl (Freistellen).
7. **Bereich herausschneiden** (Strg+X) entfernt den markierten Bereich und fügt die verbleibenden Teile davor und danach nahtlos zusammen.
8. Das Ergebnis anhören und über **Exportieren** in einem beliebigen unterstützten Format speichern.

Weitere kleine Hilfen:

- **Waveform-Zoom & Navigation:** Flexibles Zoomen von 100 % (Vollansicht) bis 10.000 % (hochauflösende Detailansicht).
  - Zoomen per **Strg+Mausrad** (zentriert auf den Mauszeiger) oder über die Buttons **+** / **−** / **Ganze Datei**.
  - Horizontale Scrollbar für zentimetergenaue Navigation bei Vergrößerung sowie Panning per mittlerer Maustaste (oder Mausrad-Klick & Ziehen).
  - Dynamisches High-Definition-Peak-Sampling sorgt auch bei 100-fachem Zoom für gestochen scharfe Wellenformen bis in den Millisekunden-Bereich.
  - Automatisches Mitführen der Ansicht (Auto-Follow) während der Wiedergabe.
- **Zweikanalige Stereo-Ansicht:** Bei Stereo-Audiodateien werden linker (L) und rechter (R) Kanal automatisch getrennt übereinander mit dezenten Kanal-Badges und Mittelachsen dargestellt.
  - Über den Button **Stereo getrennt / kombiniert** kann jederzeit zwischen der getrennten zweikanaligen Ansicht und einer kombinierten Monomischung umgeschaltet werden.
  - Bei echten Monodateien bleibt die Anzeige auf eine saubere Einzelspur fokussiert.
- **Zweisprachig (Deutsch / English):** Über den **EN / DE**-Button in der oberen Leiste kann die gesamte Benutzeroberfläche (Menüs, Buttons, Tooltips, Statusmeldungen, Dialoge und Hilfethemen) jederzeit nahtlos im laufenden Betrieb zwischen Deutsch und Englisch umgeschaltet werden.
- **Integrierter Hilfe-Assistent & Shortcuts (F1 / ?):** Schnelles, durchsuchbares Hilfefenster im Dark Mode.
  - Findet in Echtzeit alle Funktionen, Schnittwerkzeuge, Audio-Effekte und Tastenkürzel (z. B. nach „schneiden“, „fade“, „normalisieren“, „Strg+Z“).
  - Filter-Chips nach Kategorien (*Tastenkürzel*, *Bearbeiten*, *Effekte*, *Waveform & Zoom*, *Grundlagen*).
  - Aufrufbar per Klick auf **Hilfe** oder direkt mit der Taste **F1** bzw. **?**.
- **Bereich herausschneiden:** Markierten Bereich entfernen und Lücke nahtlos schließen (Strg+X).
- **Rückgängig & Wiederholen (Multi-Undo / Verlauf):** Bis zu 25 Bearbeitungsschritte können mit **Strg+Z** rückgängig gemacht und mit **Strg+Y** (oder **Strg+Umschalt+Z**) wiederholt werden. Die Buttons zeigen im Tooltip stets den jeweiligen Aktionsnamen und die Anzahl verbleibender Schritte im Verlauf an.
- **Fade In / Fade Out:** Sanftes Ein- bzw. Ausblenden über den aktuell markierten Bereich (natürliche, klickfreie S-Kurve).
- **Normalisieren:** Die gesamte Datei auf den optimalen Spitzenpegel (-0.1 dBFS) aussteuern – maximiert die Lautstärke sauber ohne Übersteuerung und verhindert Clipping bei komprimiertem Export.
- **Start = Position / Ende = Position:** Aktuelle Wiedergabeposition als Grenze übernehmen.
- **Alles davor entfernen:** Alles vor A entfernen, ab A bis zum Dateiende behalten.
- **Alles danach entfernen:** Alles nach B entfernen, vom Dateianfang bis B behalten.
- **Alles auswählen:** Auswahl auf die vollständige Datei zurücksetzen.

Beim Öffnen und Schneiden wird die Originaldatei nicht verändert. Erst der Export schreibt eine Datei.
Vor dem Ersetzen einer vorhandenen Datei erscheint eine Rückfrage. Fehlgeschlagene Exporte beschädigen
vorhandene Dateien nicht. Ein Stern im Fenstertitel zeigt noch nicht exportierte Änderungen an.
Beim Schließen oder Öffnen einer anderen Datei gibt es dafür eine Rückfrage.

Der Export speichert immer die **gesamte aktuell bearbeitete Datei**. Eine Auswahl allein verändert
das Audio noch nicht; dafür zuerst zuschneiden oder herausschneiden. Die Dateiendung bestimmt das Exportformat.
Ohne eingegebene Endung wird die Endung des gewählten Dateifilters ergänzt.

## Tastenkürzel

| Taste | Aktion |
| --- | --- |
| F1 / ? | Hilfe & Tastenkürzel durchsuchen |
| Strg+O | Öffnen |
| Strg+S | Exportieren |
| Strg+Z | Rückgängig machen (Multi-Undo) |
| Strg+Y / Strg+Umschalt+Z | Wiederholen (Redo) |
| Strg+X | Bereich herausschneiden |
| Strg++ / Strg+= | Waveform vergrößern (Zoom In) |
| Strg+- | Waveform verkleinern (Zoom Out) |
| Strg+0 | Ganze Datei anzeigen (Zoom zurücksetzen) |
| Strg+Mausrad | Stufenlos am Mauszeiger zoomen |
| Leertaste | Abspielen / Pause |
| Esc | Stop |
| A | Start auf die aktuelle Position setzen |
| B | Ende auf die aktuelle Position setzen |

## Bewusste Grenzen

- Eine Datei zur Zeit, Mono oder Stereo; keine Mehrspur-Bearbeitung.
- Maximal **30 Minuten** und **256 MiB** dekodierte Float32-Samples, um den Speicherbedarf klein zu halten.
  Bei hohen Abtastraten kann die Speichergrenze bereits früher erreicht sein.
- WAV-, FLAC- & AIFF-Export: **24-Bit PCM** (verlustfrei), ursprüngliche Abtastrate und Kanalanzahl.
- MP3, OGG, Opus, M4A, AAC & WMA: Komprimierte Formate werden neu kodiert und sind verlustbehaftet; für verlustfreie Weiterverarbeitung vorzugsweise WAV, FLAC oder AIFF exportieren.
- Auswahl und Anzeige haben Millisekunden-Auflösung; geschnitten wird an der nächstgelegenen Samplegrenze.
  Bei einer vollständigen Auswahl bleibt auch das letzte Sample erhalten.
- Tags, Coverbilder und andere Metadaten werden nicht übernommen.
- Für die Wiedergabe wird lokal eine temporäre 16-Bit-WAV erstellt. Sehr laute Float-WAV-Samples außerhalb
  des Bereichs -1 bis +1 werden beim PCM-Export bzw. in dieser Vorschau begrenzt.
- Audiodaten werden lokal verarbeitet. Es gibt keinen Upload und keinen Cloud-Dienst.

Laden, Zuschneiden und Export laufen in einem Hintergrundthread. Währenddessen sind Bearbeitungsaktionen
gesperrt; das Fenster bleibt reaktionsfähig. Beim Schließen während einer Verarbeitung wird deren Ende
abgewartet. Temporäre Dateien werden beim Beenden bereinigt, soweit Windows keine Dateihandles mehr hält.

## Projektaufbau

```text
main.py                   Einstiegspunkt
start.bat                 Windows-Starthelfer
requirements.txt          Vier direkte Abhängigkeiten
soundslice/
  audio.py                Laden, Samples schneiden, Waveform-Daten, Export
  help_dialog.py          Zweisprachiger Hilfe- und Shortcut-Assistent (F1)
  i18n.py                 Internationalisierung (Deutsch / Englisch)
  jobs.py                 Hintergrundverarbeitung
  waveform.py             Waveform, Zoom und Stereo-Split mit QPainter
  window.py               Oberfläche und Bedienung
  style.py                Dark Mode und Icons
tests/
  test_audio.py            Echte WAV-/MP3-Roundtrips und Fehlerfälle
  test_ui.py               Qt-Integration inklusive Wiedergabe und Auswahl
```

## Tests ausführen

Die Tests benötigen nur die normalen Projektabhängigkeiten und Pythons `unittest`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Für eine Prüfung ohne sichtbares Fenster:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Der Wiedergabetest überprüft die Zustände und die fortschreitende Position von Qt Multimedia.
Die tatsächliche hörbare Ausgabe muss zusätzlich am eigenen Ausgabegerät geprüft werden.

---

## English Quickstart

**endlez Sound Slicer** is a lightweight, responsive desktop audio editor built with PySide6 for Windows.

### Key Features
- **9 Audio Formats:** Lossless editing & export for WAV, FLAC, AIFF (24-bit PCM); compressed support for MP3, M4A, AAC, OGG Vorbis, Opus, and WMA.
- **Waveform Zoom & Panning:** Seamless zoom from 100% to 10,000% centered at cursor (`Ctrl+Mouse Wheel`), horizontal scrollbar, and middle-drag panning.
- **Dual-Channel Stereo View:** Automatic split into stacked Left and Right tracks with center axes and badges. Toggle back to combined mono view anytime.
- **Precise Editing Tools:** Trim / crop selection, delete range (`Ctrl+X`), remove before/after, markers A and B.
- **Audio Effects:** Click-free S-curve Fade In / Fade Out, Peak Normalization to -0.1 dBFS.
- **25-Level Multi-Undo/Redo:** Full history with tooltips (`Ctrl+Z`, `Ctrl+Y`).
- **Bilingual Interface:** Live toggle between English and German via the toolbar button (`EN` / `DE`).
- **Interactive Help (F1 / ?):** Real-time search across all tools, shortcuts, and audio effects.

### Getting Started

```powershell
# 1. Clone repository and set up virtual environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Run endlez Sound Slicer
.\.venv\Scripts\python.exe main.py
# Or double-click start.bat on Windows
```

Libraries used: [Qt for Python](https://doc.qt.io/qtforpython-6/),
[SoundFile](https://python-soundfile.readthedocs.io/), [NumPy](https://numpy.org/),
[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg).
Licensed under the [MIT License](LICENSE).
#   n d l e z - s o u n d - s l i c e r  
 #   n d l e z - s o u n d - s l i c e r  
 