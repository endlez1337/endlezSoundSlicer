"""Audio operations independent of Qt; called from background jobs."""

from dataclasses import dataclass
from pathlib import Path
import math
import os
import subprocess
import tempfile
import uuid

import imageio_ffmpeg
import numpy as np
import soundfile as sf


MAX_DURATION_SECONDS = 30 * 60
MAX_DECODED_BYTES = 256 * 1024 * 1024


class AudioError(Exception):
    """An error safe to show to the user."""


def format_time(milliseconds: int | float) -> str:
    milliseconds = max(0, round(milliseconds))
    seconds, fraction = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{fraction:03d}"


@dataclass(frozen=True)
class AudioClip:
    samples: np.ndarray  # shape: frames x channels, float32; never changed in place
    sample_rate: int
    source_path: Path

    @property
    def duration_ms(self) -> int:
        return max(1, round(len(self.samples) * 1000 / self.sample_rate))

    @property
    def channels(self) -> int:
        return self.samples.shape[1]


@dataclass(frozen=True)
class PreparedClip:
    clip: AudioClip
    peaks: np.ndarray
    preview_path: Path
    channel_peaks: tuple[np.ndarray, ...] = ()


def ffmpeg_executable() -> str:
    try:
        executable = imageio_ffmpeg.get_ffmpeg_exe()
        if not executable:
            raise RuntimeError("Kein FFmpeg gefunden")
        return executable
    except (RuntimeError, OSError) as error:
        raise AudioError(
            "FFmpeg wurde nicht gefunden. Installiere imageio-ffmpeg oder setze "
            "IMAGEIO_FFMPEG_EXE auf den vollständigen Pfad zu ffmpeg.exe."
        ) from error


def run_ffmpeg(arguments: list[str]) -> None:
    command = [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *arguments]
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, timeout=180, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as error:
        raise AudioError("Die Audioverarbeitung dauert zu lange. Bitte eine kleinere Datei verwenden.") from error
    except OSError as error:
        raise AudioError("FFmpeg konnte nicht gestartet werden. Bitte die FFmpeg-Installation prüfen.") from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[-900:]
        raise AudioError("FFmpeg konnte die Datei nicht verarbeiten.\n" + detail)


def _read_wav(path: Path, source_path: Path) -> AudioClip:
    try:
        with sf.SoundFile(str(path)) as audio_file:
            if audio_file.format not in {"WAV", "WAVEX", "RF64"}:
                raise AudioError("Die Datei enthält keine gültigen WAV-Audiodaten.")
            if audio_file.frames < 1:
                raise AudioError("Die Audio-Datei ist leer.")
            if audio_file.channels not in (1, 2):
                raise AudioError("Bitte eine Mono- oder Stereo-Datei verwenden.")
            if audio_file.frames / audio_file.samplerate > MAX_DURATION_SECONDS:
                raise AudioError("Dieser kleine Editor unterstützt Dateien bis zu 30 Minuten Länge.")
            if audio_file.frames * audio_file.channels * 4 > MAX_DECODED_BYTES:
                raise AudioError("Die entpackten Audiodaten sind zu groß (maximal 256 MiB).")
            samples = audio_file.read(dtype="float32", always_2d=True)
            sample_rate = audio_file.samplerate
        if len(samples) < 1:
            raise AudioError("Die Audio-Datei enthält keine lesbaren Samples.")
        for start in range(0, len(samples), 65536):
            if not np.isfinite(samples[start:start + 65536]).all():
                raise AudioError("Die Datei enthält ungültige Audio-Samples.")
        samples.flags.writeable = False
        return AudioClip(samples, sample_rate, source_path)
    except (sf.LibsndfileError, OSError, ValueError) as error:
        raise AudioError("Die WAV-Datei konnte nicht gelesen werden. Sie ist beschädigt oder nicht unterstützt.") from error


SUPPORTED_IMPORT_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".aiff", ".aif", ".wma",
}
SUPPORTED_EXPORT_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".aiff", ".aif", ".wma",
}


def load_audio(path: str | Path) -> AudioClip:
    path = Path(path).resolve()
    if not path.is_file():
        raise AudioError("Die ausgewählte Datei wurde nicht gefunden.")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_IMPORT_EXTENSIONS:
        raise AudioError("Bitte eine unterstützte Audiodatei (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma) öffnen.")
    if suffix == ".wav":
        return _read_wav(path, path)
    # Decode to a temporary file instead of holding another full PCM copy in RAM.
    with tempfile.TemporaryDirectory(prefix="soundslice-decode-") as directory:
        decoded = Path(directory) / "decoded.wav"
        run_ffmpeg([
            "-i", str(path), "-map", "0:a:0", "-vn", "-t", str(MAX_DURATION_SECONDS + 1),
            "-c:a", "pcm_f32le", str(decoded),
        ])
        return _read_wav(decoded, path)


def crop_audio(clip: AudioClip, start_ms: int, end_ms: int) -> AudioClip:
    if not (0 <= start_ms < end_ms <= clip.duration_ms):
        raise AudioError("Der Start muss vor dem Ende liegen und innerhalb der Datei sein.")
    first = min(len(clip.samples), round(start_ms * clip.sample_rate / 1000))
    last = len(clip.samples) if end_ms == clip.duration_ms else round(end_ms * clip.sample_rate / 1000)
    last = min(last, len(clip.samples))
    if last <= first:
        raise AudioError("Die Auswahl ist zu kurz. Bitte einen größeren Bereich auswählen.")
    # A copy frees the excluded audio when the previous document is released.
    samples = clip.samples[first:last].copy()
    samples.flags.writeable = False
    return AudioClip(samples, clip.sample_rate, clip.source_path)


def delete_audio_range(clip: AudioClip, start_ms: int, end_ms: int) -> AudioClip:
    """Schneidet den markierten Zeitbereich heraus und fügt die verbleibenden Teile nahtlos zusammen."""
    if not (0 <= start_ms < end_ms <= clip.duration_ms):
        raise AudioError("Der Start muss vor dem Ende liegen und innerhalb der Datei sein.")
    first = min(len(clip.samples), round(start_ms * clip.sample_rate / 1000))
    last = len(clip.samples) if end_ms == clip.duration_ms else round(end_ms * clip.sample_rate / 1000)
    last = min(last, len(clip.samples))
    if last <= first:
        raise AudioError("Der ausgewählte Bereich zum Herausschneiden ist zu kurz.")
    if first == 0 and last == len(clip.samples):
        raise AudioError("Die gesamte Datei kann nicht herausgeschnitten werden (Ergebnis wäre leer).")

    parts = []
    if first > 0:
        parts.append(clip.samples[:first])
    if last < len(clip.samples):
        parts.append(clip.samples[last:])
    samples = np.concatenate(parts, axis=0).copy()
    samples.flags.writeable = False
    return AudioClip(samples, clip.sample_rate, clip.source_path)


def apply_fade(clip: AudioClip, start_ms: int, end_ms: int, fade_in: bool = True) -> AudioClip:
    if not (0 <= start_ms < end_ms <= clip.duration_ms):
        raise AudioError("Der Start muss vor dem Ende liegen und innerhalb der Datei sein.")
    first = min(len(clip.samples), round(start_ms * clip.sample_rate / 1000))
    last = len(clip.samples) if end_ms == clip.duration_ms else round(end_ms * clip.sample_rate / 1000)
    last = min(last, len(clip.samples))
    if last <= first:
        raise AudioError("Der ausgewählte Bereich für das Aus-/Einblenden ist zu kurz.")
    length = last - first
    t = np.linspace(0.0, 1.0, length, dtype=np.float32)
    # Sanfter S-Kurven-Verlauf (Half-Cosine / Raised Cosine):
    # fade_in: 0.0 -> 1.0 mit horizontaler Tangente an beiden Enden (kein Knacken)
    # fade_out: 1.0 -> 0.0 mit horizontaler Tangente an beiden Enden
    curve = 0.5 * (1.0 - np.cos(np.pi * t)) if fade_in else 0.5 * (1.0 + np.cos(np.pi * t))
    curve = curve[:, None]

    new_samples = clip.samples.copy()
    new_samples[first:last] *= curve
    new_samples.flags.writeable = False
    return AudioClip(new_samples, clip.sample_rate, clip.source_path)


def normalize_audio(clip: AudioClip, target_peak_db: float = -0.1) -> tuple[AudioClip, float]:
    """Normalisiert die Lautstärke des gesamten Clips auf den Ziel-Spitzenpegel in dBFS.

    Gibt ein Tupel aus (normalisierter AudioClip, angewandte Pegelanpassung in dB) zurück.
    """
    if len(clip.samples) == 0:
        raise AudioError("Die Datei enthält keine Audiodaten.")
    if target_peak_db > 0.0:
        raise AudioError("Der Zielpegel darf 0.0 dBFS nicht überschreiten.")

    current_peak = float(np.max(np.abs(clip.samples)))
    if current_peak < 1e-9:
        raise AudioError("Die Datei enthält nur Stille und kann nicht normalisiert werden.")

    target_linear = 10.0 ** (target_peak_db / 20.0)
    gain = target_linear / current_peak
    gain_db = 20.0 * math.log10(gain)

    new_samples = np.clip(clip.samples * gain, -1.0, 1.0).astype(np.float32)
    new_samples.flags.writeable = False
    return AudioClip(new_samples, clip.sample_rate, clip.source_path), gain_db


def waveform_peaks(samples: np.ndarray, bins: int = 2400) -> np.ndarray:
    if len(samples) < 1 or bins < 1:
        return np.empty((0, 2), dtype=np.float32)
    step = max(1, math.ceil(len(samples) / bins))
    starts = np.arange(0, len(samples), step)
    # Keep both channels' extrema; opposite-phase stereo must not vanish.
    low = np.minimum.reduceat(samples, starts, axis=0).min(axis=1)
    high = np.maximum.reduceat(samples, starts, axis=0).max(axis=1)
    return np.clip(np.column_stack((low, high)), -1.0, 1.0)


def channel_waveform_peaks(samples: np.ndarray, bins: int = 2400) -> tuple[np.ndarray, ...]:
    if len(samples) < 1 or bins < 1:
        return ()
    step = max(1, math.ceil(len(samples) / bins))
    starts = np.arange(0, len(samples), step)
    channels = samples.shape[1]
    result = []
    for ch in range(channels):
        ch_samples = samples[:, ch]
        low = np.minimum.reduceat(ch_samples, starts, axis=0)
        high = np.maximum.reduceat(ch_samples, starts, axis=0)
        result.append(np.clip(np.column_stack((low, high)), -1.0, 1.0))
    return tuple(result)


def prepare_clip(clip: AudioClip, cache_directory: Path) -> PreparedClip:
    preview = cache_directory / f"{uuid.uuid4().hex}.wav"
    try:
        sf.write(str(preview), clip.samples, clip.sample_rate, format="WAV", subtype="PCM_16")
        return PreparedClip(
            clip,
            waveform_peaks(clip.samples),
            preview,
            channel_waveform_peaks(clip.samples),
        )
    except (sf.LibsndfileError, OSError, ValueError) as error:
        preview.unlink(missing_ok=True)
        raise AudioError("Die Datei für die Wiedergabe konnte nicht erstellt werden. Bitte freien Speicher prüfen.") from error


def export_audio(clip: AudioClip, destination: str | Path) -> Path:
    destination = Path(destination).resolve()
    suffix = destination.suffix.lower()
    if suffix not in SUPPORTED_EXPORT_EXTENSIONS:
        raise AudioError("Zum Export bitte eine unterstützte Dateiendung (.wav, .mp3, .flac, .ogg, .opus, .m4a, .aac, .aiff, .wma) verwenden.")
    temporary: Path | None = None
    try:
        # Write beside the destination, then replace atomically. Failed exports
        # never truncate an existing source or destination file.
        handle, name = tempfile.mkstemp(prefix=".soundslice-", suffix=suffix, dir=destination.parent)
        os.close(handle)
        temporary = Path(name)
        if suffix == ".wav":
            sf.write(str(temporary), clip.samples, clip.sample_rate, format="WAV", subtype="PCM_24")
        elif suffix == ".flac":
            sf.write(str(temporary), clip.samples, clip.sample_rate, format="FLAC", subtype="PCM_24")
        elif suffix == ".ogg":
            sf.write(str(temporary), clip.samples, clip.sample_rate, format="OGG", subtype="VORBIS")
        elif suffix in {".aiff", ".aif"}:
            sf.write(str(temporary), clip.samples, clip.sample_rate, format="AIFF", subtype="PCM_24")
        else:
            with tempfile.TemporaryDirectory(prefix="soundslice-export-") as directory:
                source = Path(directory) / "source.wav"
                sf.write(str(source), clip.samples, clip.sample_rate, format="WAV", subtype="FLOAT")
                if suffix == ".mp3":
                    arguments = ["-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame", "-q:a", "2"]
                    # MP3 supports only a fixed set of rates. Preserve standard rates.
                    if clip.sample_rate not in {8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000}:
                        arguments += ["-ar", "48000"]
                elif suffix == ".m4a":
                    arguments = ["-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
                elif suffix == ".aac":
                    arguments = ["-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "aac", "-b:a", "192k"]
                elif suffix == ".opus":
                    arguments = ["-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "libopus", "-b:a", "128k"]
                elif suffix == ".wma":
                    arguments = ["-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "wmav2", "-b:a", "192k"]
                else:
                    raise AudioError(f"Nicht unterstütztes Format: {suffix}")
                run_ffmpeg([*arguments, str(temporary)])
        if temporary.stat().st_size == 0:
            raise AudioError("Der Export hat eine leere Datei erzeugt.")
        os.replace(temporary, destination)
        return destination
    except (sf.LibsndfileError, OSError, ValueError) as error:
        raise AudioError("Die Datei konnte nicht gespeichert werden. Bitte Pfad, Zugriffsrechte und freien Speicher prüfen.") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
