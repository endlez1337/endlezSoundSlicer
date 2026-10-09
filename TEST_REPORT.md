# Prüfbericht

Geprüft am **8. Oktober 2026** unter Windows, 64 Bit.

## Ergebnis

**48 automatisierte Tests bestanden**; Gesamtlaufzeit des letzten Durchlaufs: ca. 14 Sekunden.
Zusätzlich wurde `main.py` mit einer beim Start übergebenen WAV-Datei gestartet und regulär
beendet, einschließlich Bereinigung der Vorschau-Dateien (Exit-Code 0).

## Geprüfte Abläufe

- Sprachumschaltung (Deutsch / Englisch): Nahtloses Umschalten aller Buttons, Labels, Tooltips, Statusmeldungen, Dialoge und Hilfetexte per Klick auf den Sprach-Button.
- Integrierter Hilfe-Assistent (`HelpDialog`): Vollständig zweisprachig (DE / EN), Echtzeit-Filterung bei der Suche nach Begriffen, Titeln, Beschreibungen und Tastenkürzeln.
- Hilfe-Kategorienfilter: Filterung nach Tastenkürzeln, Schnittwerkzeugen, Effekten, Waveform und Grundlagen in beiden Sprachen.
- Hilfe-Dialog-Integration: Button in der Hauptwerkzeugleiste, Shortcuts `F1` und `?`, modaler Dialogaufruf und barrierefreie Tastaturbedienung (`Esc`).
- WAV laden, exakte Samplegrenzen beim Zuschneiden, Mono/Stereo und Abtastrate erhalten.
- WAV mit 24-Bit PCM exportieren und erneut einlesen.
- FLAC mit 24-Bit PCM verlustfrei exportieren und bitgenau einlesen.
- AIFF mit 24-Bit PCM verlustfrei exportieren und bitgenau einlesen.
- OGG Vorbis exportieren, dekodieren und verifizieren.
- Opus mit FFmpeg kodieren, dekodieren und verifizieren.
- MP3 tatsächlich mit FFmpeg kodieren, dekodieren und das Audiosignal vergleichen.
- M4A und AAC tatsächlich mit FFmpeg kodieren, dekodieren und Roundtrips prüfen.
- WMA tatsächlich mit FFmpeg kodieren, dekodieren und Roundtrips prüfen.
- Bereich herausschneiden (Delete Selection): mittleren, vorderen und hinteren Bereich entfernen, verbleibende Teile nahtlos verbinden, Sample-Grenzen und Kanalintegrität prüfen.
- Ungültige Bereiche für das Herausschneiden abfangen (z. B. vollständige Datei löschen).
- Fade-In und Fade-Out mit natürlicher S-Kurve berechnen, Sample-Pegel und Kanal-Integrität prüfen.
- Ungültige Zeitbereiche für Fades abfangen.
- Lautstärke normalisieren (Peak Normalization auf -0.1 dBFS): Pegelanpassung in dB, Stille-Erkennung, Pegelreduzierung bei lauten Dateien und Pegelanhebung bei leisen Dateien.
- Multi-Level Undo & Redo (Verlauf bis zu 25 Schritte): sequenzielles Zurücknehmen und Wiederherstellen über mehrere Aktionen (Zuschneiden, Herausschneiden, Normalisieren, Fade) sowie Stack-Kappung bei Verzweigungen.
- Zweikanalige Stereo-Ansicht: getrennte Peaks pro Kanal für Stereo sowie kombinierte Peaks für Mono berechnen.
- Stereo-Umschalter: Sichtbarkeit und Status exklusiv bei 2-Kanal-Dateien, Umschalten zwischen getrennter und kombinierter Waveform.
- Waveform-Zooming: Skalierung (1.0x bis 100.0x), Vergrößern/Verkleinern per Buttons, Tastenkürzel (Strg++, Strg+-, Strg+0), Mausrad am Cursorpunkt und Reset auf Gesamtansicht.
- Horizontale Scrollbar und Panning: Synchronisation von View-Offset und Scrollbar-Range bei Zoom.
- Exakte Pixel- und Zeitkoordinaten-Projektion bei allen Zoomstufen für Marker A, B und Wiedergabeposition.
- Qt-Ablauf: laden, auswählen, zuschneiden, herausschneiden, Fade-In / Fade-Out, Normalisieren, mehrstufiges Rückgängig/Wiederholen, exportieren.
- WAVs mit einer für MP3 ungeeigneten Abtastrate umrechnen und exportieren.
- Alles vor bzw. nach der Auswahl entfernen; vollständiges Dateiende erhalten.
- Beschädigte, leere, mehrkanalige und ungültige Dateien aller Formate abfangen.
- Bestehende Exportdatei bei einem Encoderfehler erhalten und temporäre Ausgabe entfernen.
- Quelldatei nach erfolgreichem Export ersetzen.
- Dateigröße vor dem Laden der Samples begrenzen.
- Gegenphasige Stereo-Kanäle und den letzten kurzen Ausschlag in der Waveform erhalten.
- Abspielen, Pause, Position ändern, Stop und Auswahlvorschau am Bereichsende anhalten.
- Auswahl mit der Maus ziehen, Grenzen verschieben und Zeitwerte eingeben.
- Automatische Dateiendungsergänzung für alle Exportfilter (WAV, MP3, FLAC, OGG, Opus, M4A, AAC, AIFF, WMA).
- Drag-and-Drop für alle unterstützten Formate.
- Nach einem fehlgeschlagenen Ladevorgang das bisherige Audio behalten und die Bedienung freigeben.
- Nach einem fehlgeschlagenen Export den Status nicht exportierter Änderungen erhalten.
- Während eines Hintergrundauftrags beim Schließen dessen Ende abwarten.
- Bei der minimalen Fenstergröße überlappende Layoutzeilen verhindern.

Die Oberfläche wurde zusätzlich als echte Qt-Vorschau in 1120 × 760 und 960 × 680 Pixeln
gerendert und visuell geprüft. `preview.png` zeigt die größere Darstellung.

## Testumgebung

| Komponente | Version |
| --- | --- |
| Python | 3.14.4 |
| PySide6 | 6.11.2 |
| NumPy | 2.5.3 |
| SoundFile | 0.13.1 |
| imageio-ffmpeg | 0.6.0 |
| mitgeliefertes FFmpeg | 7.1, Essentials Build |

Die Qt-Tests liefen mit `QT_QPA_PLATFORM=offscreen`. Qt Multimedia bestätigte die
Wiedergabezustände, Positionsfortschritte und das Anhalten. Die **tatsächliche hörbare Ausgabe**
an Lautsprechern/Kopfhörern wurde hier nicht beurteilt. Native Windows-Dateidialoge wurden
in den automatisierten Tests durch vorgegebene Antworten ersetzt.

Ausführen auf dem eigenen Rechner: siehe [README](README.md#tests-ausführen).
