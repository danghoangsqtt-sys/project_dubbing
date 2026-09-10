from __future__ import annotations

import math
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import tts_processor  # noqa: E402
import vieneu_tts  # noqa: E402
from utils.voice_preview_utils import clamp_requested_speed  # noqa: E402
from workflows.voice_workflow import VoiceWorkflow  # noqa: E402


def _write_pcm16(path: Path, *, rate: int, amplitude: int) -> None:
    frames = bytearray()
    for index in range(rate // 10):
        value = int(amplitude * math.sin(2 * math.pi * 220 * index / rate))
        frames.extend(value.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(bytes(frames))


class VieNeuTimingContractTests(unittest.TestCase):
    def test_speed_is_bounded_to_milestone_range(self) -> None:
        self.assertEqual(0.92, clamp_requested_speed(0.5))
        self.assertEqual(1.12, clamp_requested_speed(1.5))
        self.assertEqual(1.0, clamp_requested_speed(1.0))

    def test_wav_validator_rejects_silence_and_accepts_48khz_speech(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            silent = Path(tmp) / "silent.wav"
            speech = Path(tmp) / "speech.wav"
            _write_pcm16(silent, rate=48000, amplitude=0)
            _write_pcm16(speech, rate=48000, amplitude=1000)
            with self.assertRaisesRegex(RuntimeError, "silence"):
                tts_processor._validate_generated_wav(str(silent))
            tts_processor._validate_generated_wav(str(speech))
            with wave.open(str(speech), "rb") as wav_file:
                self.assertEqual(48000, wav_file.getframerate())

    def test_vieneu_native_output_remains_48khz(self) -> None:
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy unavailable")

        class FakeModel:
            def infer(self, _text, **_kwargs):
                samples = np.arange(4800, dtype=np.float32)
                return 0.1 * np.sin(2 * np.pi * 220 * samples / 48000)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cue.wav"
            with patch.object(vieneu_tts, "get_cached_vieneu_model", return_value=FakeModel()):
                vieneu_tts.vieneu_synthesize_wav_16k_mono(
                    text="Xin chào",
                    wav_path=str(output),
                    voice_id="vieneu:Adam",
                    speed=1.0,
                    tmp_dir=tmp,
                )
            with wave.open(str(output), "rb") as wav_file:
                self.assertEqual(48000, wav_file.getframerate())

    def test_inference_lock_serializes_vieneu_calls(self) -> None:
        active = 0
        peak = 0
        guard = threading.Lock()

        class FakeModel:
            def infer(self, _text, **_kwargs):
                nonlocal active, peak
                try:
                    import numpy as np
                except ImportError:
                    return [0.1] * 480
                with guard:
                    active += 1
                    peak = max(peak, active)
                time.sleep(0.03)
                with guard:
                    active -= 1
                return np.full(480, 0.1, dtype=np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            model = FakeModel()

            def synth(index: int) -> None:
                vieneu_tts.vieneu_synthesize_wav_16k_mono(
                    text="Thử giọng",
                    wav_path=str(Path(tmp) / f"{index}.wav"),
                    voice_id="vieneu:Adam",
                    tmp_dir=tmp,
                )

            with patch.object(vieneu_tts, "get_cached_vieneu_model", return_value=model):
                threads = [threading.Thread(target=synth, args=(index,)) for index in range(2)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        self.assertEqual(1, peak)

    def test_audition_uses_dubbing_text_and_safe_speed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow = VoiceWorkflow(tmp)
            workflow.engine_runtime.synthesize_segment = Mock(return_value=str(Path(tmp) / "audition.wav"))
            result = workflow.audition_segment(
                {"subtitle_vi": "Phụ đề dài", "dubbing_vi": "Lời đọc ngắn"},
                output_wav_path=str(Path(tmp) / "audition.wav"),
                speed=1.8,
            )
        self.assertTrue(result.endswith("audition.wav"))
        kwargs = workflow.engine_runtime.synthesize_segment.call_args.kwargs
        self.assertEqual("Lời đọc ngắn", kwargs["text"])
        self.assertEqual(1.12, kwargs["speed"])

    def test_out_of_band_timing_is_marked_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "long.wav"
            _write_pcm16(wav_path, rate=48000, amplitude=1000)
            workflow = VoiceWorkflow(tmp)
            segment = {"text": "Xin chào", "subtitle_vi": "Xin chào", "dubbing_vi": "Chào"}
            workflow._finalize_segment_result(
                seg=segment,
                wav_path=str(wav_path),
                target_duration=0.05,
                attempt_count=2,
                action_taken="retry",
            )
        self.assertEqual("needs_review", segment["timing_status"])
        self.assertIn("tts_timing_review", segment["qa_flags"])

    def test_vieneu_provenance_is_reportable(self) -> None:
        record = vieneu_tts.vieneu_provenance(voice_id="vieneu:Adam", speed=1.4)
        self.assertEqual("pnnbao-ump/VieNeu-TTS-v3-Turbo", record["model"])
        self.assertEqual("v3turbo", record["mode"])
        self.assertEqual(48000, record["sample_rate"])
        self.assertEqual(1.12, record["speed"])


if __name__ == "__main__":
    unittest.main()
