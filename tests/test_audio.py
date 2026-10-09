"""Round-trip and failure-path tests using real WAV/MP3 files."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from soundslice.audio import (
    AudioClip, AudioError, apply_fade, channel_waveform_peaks, crop_audio,
    delete_audio_range, export_audio, format_time, load_audio, normalize_audio,
    prepare_clip, waveform_peaks,
)


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="soundslice-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sample_rate = 48000
        time = np.arange(self.sample_rate * 2, dtype=np.float32) / self.sample_rate
        left = 0.6 * np.sin(2 * np.pi * 440 * time)
        self.samples = np.column_stack((left, -left))
        self.source = self.root / "Prüfung mit Leerzeichen.wav"
        sf.write(self.source, self.samples, self.sample_rate, subtype="FLOAT")
        self.clip = load_audio(self.source)

    def test_wav_round_trip_keeps_stereo_rate_and_audio(self):
        result = export_audio(self.clip, self.root / "Ergebnis.wav")
        loaded = load_audio(result)
        self.assertEqual((loaded.duration_ms, loaded.channels, loaded.sample_rate), (2000, 2, 48000))
        np.testing.assert_allclose(loaded.samples, self.samples, atol=1.3e-7)
        self.assertEqual(sf.info(result).subtype, "PCM_24")

    def test_crop_has_exact_sample_boundaries_and_preserves_source(self):
        original_bytes = self.source.read_bytes()
        trimmed = crop_audio(self.clip, 125, 1125)
        np.testing.assert_array_equal(trimmed.samples, self.clip.samples[6000:54000])
        self.assertEqual(trimmed.duration_ms, 1000)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertFalse(trimmed.samples.flags.writeable)

    def test_remove_before_and_after_can_keep_the_opposite_side(self):
        before_removed = crop_audio(self.clip, 500, self.clip.duration_ms)
        after_removed = crop_audio(self.clip, 0, 1500)
        np.testing.assert_array_equal(before_removed.samples, self.clip.samples[24000:])
        np.testing.assert_array_equal(after_removed.samples, self.clip.samples[:72000])

    def test_delete_audio_range_middle_and_edges(self):
        # 1. Delete middle segment (500ms to 1500ms from 2000ms clip)
        middle_cut = delete_audio_range(self.clip, 500, 1500)
        self.assertEqual(middle_cut.duration_ms, 1000)
        self.assertEqual(len(middle_cut.samples), 48000)
        self.assertFalse(middle_cut.samples.flags.writeable)
        # First 500ms (24000 samples) must match original prefix
        np.testing.assert_array_equal(middle_cut.samples[:24000], self.clip.samples[:24000])
        # Last 500ms (24000 samples) must match original suffix
        np.testing.assert_array_equal(middle_cut.samples[24000:], self.clip.samples[72000:])

        # 2. Delete from start (0 to 500ms)
        start_cut = delete_audio_range(self.clip, 0, 500)
        self.assertEqual(start_cut.duration_ms, 1500)
        np.testing.assert_array_equal(start_cut.samples, self.clip.samples[24000:])

        # 3. Delete until end (1500ms to 2000ms)
        end_cut = delete_audio_range(self.clip, 1500, 2000)
        self.assertEqual(end_cut.duration_ms, 1500)
        np.testing.assert_array_equal(end_cut.samples, self.clip.samples[:72000])

    def test_delete_audio_range_invalid_ranges(self):
        # Full file deletion is rejected (would leave 0 samples)
        with self.assertRaises(AudioError):
            delete_audio_range(self.clip, 0, self.clip.duration_ms)
        with self.assertRaises(AudioError):
            delete_audio_range(self.clip, 500, 500)
        with self.assertRaises(AudioError):
            delete_audio_range(self.clip, 800, 500)
        with self.assertRaises(AudioError):
            delete_audio_range(self.clip, -100, 500)
        with self.assertRaises(AudioError):
            delete_audio_range(self.clip, 0, 5000)

    def test_apply_fade_in_and_fade_out(self):
        faded_in = apply_fade(self.clip, 0, 500, fade_in=True)
        self.assertEqual(faded_in.duration_ms, self.clip.duration_ms)
        np.testing.assert_allclose(faded_in.samples[0], [0.0, 0.0], atol=1e-5)
        np.testing.assert_allclose(faded_in.samples[24000], self.clip.samples[24000], atol=1e-4)
        np.testing.assert_array_equal(faded_in.samples[24001:], self.clip.samples[24001:])

        faded_out = apply_fade(self.clip, 1500, 2000, fade_in=False)
        self.assertEqual(faded_out.duration_ms, self.clip.duration_ms)
        np.testing.assert_array_equal(faded_out.samples[:72000], self.clip.samples[:72000])
        np.testing.assert_allclose(faded_out.samples[-1], [0.0, 0.0], atol=1e-5)

    def test_apply_fade_invalid_ranges(self):
        with self.assertRaises(AudioError):
            apply_fade(self.clip, 500, 500)
        with self.assertRaises(AudioError):
            apply_fade(self.clip, 1000, 500)
        with self.assertRaises(AudioError):
            apply_fade(self.clip, -100, 500)
        with self.assertRaises(AudioError):
            apply_fade(self.clip, 0, 5000)

    def test_normalize_audio_quiet_and_loud(self):
        target_linear = 10.0 ** (-0.1 / 20.0)
        # 1. Quiet clip (peak ~0.6)
        normalized, gain_db = normalize_audio(self.clip, target_peak_db=-0.1)
        self.assertEqual(normalized.duration_ms, self.clip.duration_ms)
        self.assertEqual(normalized.sample_rate, self.clip.sample_rate)
        self.assertFalse(normalized.samples.flags.writeable)
        self.assertAlmostEqual(float(np.max(np.abs(normalized.samples))), target_linear, places=5)
        self.assertGreater(gain_db, 4.0)

        # 2. Already normalized clip: second pass should apply ~0 dB gain
        renormalized, gain_db_2 = normalize_audio(normalized, target_peak_db=-0.1)
        self.assertAlmostEqual(gain_db_2, 0.0, places=4)
        self.assertAlmostEqual(float(np.max(np.abs(renormalized.samples))), target_linear, places=5)

        # 3. Clip peaking at 1.0: should be attenuated to -0.1 dBFS (~ -0.1 dB gain)
        loud_samples = self.samples.copy()
        loud_samples[100, 0] = 1.0
        loud_clip = AudioClip(loud_samples, self.sample_rate, self.source)
        attenuated, gain_db_3 = normalize_audio(loud_clip, target_peak_db=-0.1)
        self.assertAlmostEqual(gain_db_3, -0.1, places=3)
        self.assertAlmostEqual(float(np.max(np.abs(attenuated.samples))), target_linear, places=5)

    def test_normalize_audio_silence_and_invalid_params(self):
        # Pure silence
        silent_samples = np.zeros_like(self.samples)
        silent_clip = AudioClip(silent_samples, self.sample_rate, self.source)
        with self.assertRaises(AudioError) as cm:
            normalize_audio(silent_clip)
        self.assertIn("Stille", str(cm.exception))

        # Target peak > 0.0 dBFS
        with self.assertRaises(AudioError):
            normalize_audio(self.clip, target_peak_db=1.0)

        # Empty clip
        empty_clip = AudioClip(np.empty((0, 2), dtype=np.float32), self.sample_rate, self.source)
        with self.assertRaises(AudioError):
            normalize_audio(empty_clip)

    def test_mp3_real_encoder_decoder_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.mp3")
        decoded = load_audio(target)
        self.assertEqual((decoded.duration_ms, decoded.sample_rate, decoded.channels), (1000, 48000, 2))
        self.assertGreater(target.stat().st_size, 100)
        error = np.sqrt(np.mean((decoded.samples - self.clip.samples[12000:60000]) ** 2))
        self.assertLess(error, 0.03)

    def test_m4a_real_encoder_decoder_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.m4a")
        decoded = load_audio(target)
        self.assertAlmostEqual(decoded.duration_ms, 1000, delta=30)
        self.assertEqual((decoded.sample_rate, decoded.channels), (48000, 2))
        self.assertGreater(target.stat().st_size, 100)

    def test_aac_real_encoder_decoder_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.aac")
        decoded = load_audio(target)
        self.assertAlmostEqual(decoded.duration_ms, 1000, delta=30)
        self.assertEqual((decoded.sample_rate, decoded.channels), (48000, 2))
        self.assertGreater(target.stat().st_size, 100)

    def test_flac_real_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.flac")
        decoded = load_audio(target)
        self.assertEqual((decoded.duration_ms, decoded.sample_rate, decoded.channels), (1000, 48000, 2))
        self.assertEqual(sf.info(target).subtype, "PCM_24")
        self.assertGreater(target.stat().st_size, 100)
        np.testing.assert_allclose(decoded.samples, self.clip.samples[12000:60000], atol=1.3e-7)

    def test_ogg_real_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.ogg")
        decoded = load_audio(target)
        self.assertAlmostEqual(decoded.duration_ms, 1000, delta=25)
        self.assertEqual((decoded.sample_rate, decoded.channels), (48000, 2))
        self.assertGreater(target.stat().st_size, 100)

    def test_opus_real_encoder_decoder_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.opus")
        decoded = load_audio(target)
        self.assertAlmostEqual(decoded.duration_ms, 1000, delta=25)
        self.assertEqual((decoded.sample_rate, decoded.channels), (48000, 2))
        self.assertGreater(target.stat().st_size, 100)

    def test_aiff_real_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.aiff")
        decoded = load_audio(target)
        self.assertEqual((decoded.duration_ms, decoded.sample_rate, decoded.channels), (1000, 48000, 2))
        self.assertEqual(sf.info(target).subtype, "PCM_24")
        self.assertGreater(target.stat().st_size, 100)
        np.testing.assert_allclose(decoded.samples, self.clip.samples[12000:60000], atol=1.3e-7)

    def test_wma_real_encoder_decoder_round_trip(self):
        target = export_audio(crop_audio(self.clip, 250, 1250), self.root / "Schnitt ü.wma")
        decoded = load_audio(target)
        self.assertAlmostEqual(decoded.duration_ms, 1000, delta=40)
        self.assertEqual((decoded.sample_rate, decoded.channels), (48000, 2))
        self.assertGreater(target.stat().st_size, 100)

    def test_nonstandard_mp3_sample_rate_is_resampled(self):
        source = self.root / "odd.wav"
        sf.write(source, self.samples[:9600, :1], 9600, subtype="PCM_16")
        target = export_audio(load_audio(source), self.root / "odd.mp3")
        decoded = load_audio(target)
        self.assertEqual(decoded.sample_rate, 48000)
        self.assertEqual(decoded.channels, 1)
        self.assertEqual(decoded.duration_ms, 1000)

    def test_failed_export_leaves_existing_file_and_no_temporary_output(self):
        target = self.root / "existing.mp3"
        target.write_bytes(b"original data")
        with patch("soundslice.audio.run_ffmpeg", side_effect=AudioError("Encoder failed")):
            with self.assertRaises(AudioError):
                export_audio(self.clip, target)
        self.assertEqual(target.read_bytes(), b"original data")
        self.assertFalse(list(self.root.glob(".soundslice-*")))

    def test_export_can_replace_original_after_success(self):
        trimmed = crop_audio(self.clip, 300, 800)
        export_audio(trimmed, self.source)
        self.assertEqual(load_audio(self.source).duration_ms, 500)

    def test_invalid_inputs_and_ranges(self):
        for extension in ("wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "aiff", "wma"):
            bad = self.root / f"broken.{extension}"
            bad.write_bytes(b"not an audio file")
            with self.assertRaises(AudioError):
                load_audio(bad)
        for start, end in [(-1, 100), (10, 10), (200, 100), (0, 2001)]:
            with self.subTest(start=start, end=end), self.assertRaises(AudioError):
                crop_audio(self.clip, start, end)
        with self.assertRaises(AudioError):
            load_audio(self.root / "missing.wav")
        with self.assertRaises(AudioError):
            export_audio(self.clip, self.root / "wrong.xyz")

    def test_empty_multichannel_and_nonfinite_wavs_are_rejected(self):
        for name, samples in [("empty", np.empty((0, 1))),
                              ("multichannel", np.zeros((100, 3))),
                              ("nonfinite", np.array([[np.nan]], dtype=np.float32))]:
            path = self.root / (name + ".wav")
            sf.write(path, samples, 48000, subtype="FLOAT")
            with self.subTest(name=name), self.assertRaises(AudioError):
                load_audio(path)

    def test_size_guard_runs_before_decoding(self):
        with patch("soundslice.audio.MAX_DECODED_BYTES", 100):
            with self.assertRaises(AudioError):
                load_audio(self.source)

    def test_waveform_retains_opposite_phase_channels_and_last_transient(self):
        samples = np.zeros((10001, 2), dtype=np.float32)
        samples[100, :] = (0.8, -0.8)
        samples[-1, :] = (1, -1)
        peaks = waveform_peaks(samples, 100)
        self.assertLessEqual(len(peaks), 100)
        self.assertAlmostEqual(float(peaks[:, 0].min()), -1)
        self.assertAlmostEqual(float(peaks[:, 1].max()), 1)
        np.testing.assert_array_equal(peaks[-1], [-1, 1])

    def test_channel_waveform_peaks_mono_and_stereo(self):
        # Stereo audio with distinct signals on Left and Right
        samples = np.zeros((1000, 2), dtype=np.float32)
        samples[:, 0] = 0.5   # Left is constant 0.5
        samples[:, 1] = -0.7  # Right is constant -0.7
        ch_peaks = channel_waveform_peaks(samples, bins=10)
        self.assertEqual(len(ch_peaks), 2)
        # Left channel peaks
        np.testing.assert_allclose(ch_peaks[0][:, 0], 0.5)
        np.testing.assert_allclose(ch_peaks[0][:, 1], 0.5)
        # Right channel peaks
        np.testing.assert_allclose(ch_peaks[1][:, 0], -0.7)
        np.testing.assert_allclose(ch_peaks[1][:, 1], -0.7)

        # Mono audio
        mono_samples = samples[:, :1]
        mono_ch_peaks = channel_waveform_peaks(mono_samples, bins=10)
        self.assertEqual(len(mono_ch_peaks), 1)
        np.testing.assert_allclose(mono_ch_peaks[0][:, 0], 0.5)

        # PreparedClip includes channel_peaks
        prepared = prepare_clip(self.clip, self.root)
        self.assertEqual(len(prepared.channel_peaks), 2)

    def test_preview_is_playable_wav(self):
        prepared = prepare_clip(self.clip, self.root)
        self.assertEqual(sf.info(prepared.preview_path).subtype, "PCM_16")
        self.assertEqual(load_audio(prepared.preview_path).duration_ms, 2000)

    def test_time_format(self):
        self.assertEqual(format_time(83450), "01:23.450")
        self.assertEqual(format_time(3600000), "60:00.000")
        self.assertEqual(format_time(-1), "00:00.000")
        self.assertEqual(format_time(59999.6), "01:00.000")


if __name__ == "__main__":
    unittest.main()
