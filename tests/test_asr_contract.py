from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from asr_config import (  # noqa: E402
    FasterWhisperConfig,
    make_faster_whisper_config,
    normalize_source_language,
    resolve_model_revision,
)
from core.state import ProjectState  # noqa: E402
from services.project_service import ProjectService  # noqa: E402
from services.segment_service import SegmentService  # noqa: E402
import whisper_processor  # noqa: E402


class _FakeWhisperModel:
    _capcap_runtime_device = "cpu"
    _capcap_model_name = "fixture-model"

    def __init__(self) -> None:
        self.generator_exhausted = False
        self.kwargs = {}

    def transcribe(self, _audio_path: str, **kwargs):
        self.kwargs = dict(kwargs)

        def generate():
            yield SimpleNamespace(
                start=0.25,
                end=1.75,
                text=" 你好，世界  ",
                avg_logprob=math.log(0.8),
                words=[
                    SimpleNamespace(start=0.25, end=0.8, word="你好", probability=0.9),
                    SimpleNamespace(start=0.8, end=1.75, word="世界", probability=0.85),
                ],
            )
            self.generator_exhausted = True

        return generate(), SimpleNamespace(language="zh")


class AsrConfigurationTests(unittest.TestCase):
    def test_only_explicit_chinese_and_english_are_supported(self) -> None:
        self.assertEqual("zh", normalize_source_language("Mandarin"))
        self.assertEqual("en", normalize_source_language("English"))
        for invalid in ("", "auto", "vi", "ja"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "Chinese.*English"):
                    normalize_source_language(invalid)

    def test_locked_config_rejects_translate_task(self) -> None:
        with self.assertRaisesRegex(ValueError, "task='transcribe'"):
            FasterWhisperConfig(
                source_language="en",
                requested_model="small",
                resolved_model="small",
                model_revision="fixture",
                requested_device="auto",
                effective_device="cpu",
                compute_type="int8",
                task="translate",
            )

    def test_snapshot_directory_supplies_immutable_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
            snapshot.mkdir(parents=True)
            self.assertEqual("abc123", resolve_model_revision(str(snapshot)))

    def test_configuration_contains_runtime_and_package_contract(self) -> None:
        config = make_faster_whisper_config(
            language="en",
            requested_model="small",
            resolved_model="small",
            requested_device="auto",
            effective_device="cuda",
            compute_type="int8_float16",
            use_batched=True,
            batch_size=8,
        ).to_dict()
        expected = {
            "engine",
            "source_language",
            "requested_model",
            "resolved_model",
            "model_revision",
            "faster_whisper_version",
            "ctranslate2_version",
            "requested_device",
            "effective_device",
            "compute_type",
            "beam_size",
            "vad_filter",
            "word_timestamps",
            "task",
            "use_batched",
            "batch_size",
            "schema_version",
        }
        self.assertEqual(expected, set(config))
        self.assertEqual("transcribe", config["task"])

    def test_transcription_materializes_generator_and_emits_metadata(self) -> None:
        model = _FakeWhisperModel()
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "speech.wav"
            audio.touch()
            with (
                patch.object(
                    whisper_processor,
                    "_resolve_model_name",
                    return_value="fixture-model",
                ),
                patch.object(
                    whisper_processor,
                    "_detect_faster_whisper_runtime",
                    return_value={"device": "cpu", "compute_type": "int8", "label": "CPU / int8"},
                ),
            ):
                result = whisper_processor.transcribe_audio_with_model(
                    model,
                    str(audio),
                    language="zh",
                    use_batched=False,
                    model_path="fixture-model",
                )

        self.assertTrue(model.generator_exhausted)
        self.assertEqual("zh", model.kwargs["language"])
        self.assertEqual("transcribe", model.kwargs["task"])
        self.assertEqual(5, model.kwargs["beam_size"])
        self.assertEqual("你好，世界", result[0]["text"])
        self.assertAlmostEqual(0.8, result[0]["confidence"])
        self.assertEqual("zh", result[0]["source_language"])
        self.assertEqual("faster-whisper", result[0]["asr_provenance"]["engine"])

    def test_unicode_timed_cues_keep_stable_ids_and_provenance(self) -> None:
        provenance = {"engine": "faster-whisper", "model_revision": "abc123"}
        raw = [
            {
                "start": 0.1,
                "end": 1.2,
                "text": "你好，CapCap 2",
                "confidence": 0.91,
                "asr_provenance": provenance,
            },
            {"start": 1.3, "end": 2.4, "text": "Accuracy first", "confidence": 0.88},
        ]
        cues = SegmentService().transcript_dicts_to_models(
            raw,
            source_language="zh",
            asr_provenance=provenance,
        )
        self.assertEqual(["seg-000001", "seg-000002"], [cue.id for cue in cues])
        self.assertEqual("你好，CapCap 2", cues[0].original_text)
        self.assertEqual("zh", cues[1].source_language)
        self.assertEqual("abc123", cues[1].provenance["asr"]["model_revision"])

    def test_project_reopen_and_signature_preserve_asr_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "audio.wav"
            audio.write_bytes(b"fixture")
            service = ProjectService(str(root))
            config = make_faster_whisper_config(
                language="en",
                requested_model="small",
                resolved_model="small",
                requested_device="cpu",
                effective_device="cpu",
                compute_type="int8",
            ).to_dict()
            first = service.build_transcription_signature(
                str(audio), whisper_model="small", source_language="en", asr_config=config
            )
            changed = dict(config)
            changed["model_revision"] = "new-revision"
            second = service.build_transcription_signature(
                str(audio), whisper_model="small", source_language="en", asr_config=changed
            )
            self.assertNotEqual(first, second)

            project_root = root / "project"
            state = ProjectState(
                project_id="fixture",
                project_root=str(project_root),
                input_video=str(root / "video.mp4"),
            )
            state.set_segments(
                SegmentService().transcript_dicts_to_models(
                    [{"start": 0.0, "end": 1.0, "text": "English café"}],
                    source_language="en",
                    asr_provenance=config,
                )
            )
            state.set_provenance("asr", {"config": config, "input_signature": first})
            state_path = service.save_project(state)
            reopened = service.load_project(state_path)
            self.assertEqual("English café", reopened.segments[0].original_text)
            self.assertEqual(config["model_revision"], reopened.segments[0].provenance["asr"]["model_revision"])
            self.assertEqual(first, reopened.provenance["asr"]["input_signature"])


if __name__ == "__main__":
    unittest.main()
