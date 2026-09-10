from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.models import (  # noqa: E402
    SEGMENT_SCHEMA_VERSION,
    Segment,
    SegmentValidationError,
    validate_segments,
)
from core.state import PROJECT_SCHEMA_VERSION, ProjectMigrationError, ProjectState  # noqa: E402
from services.gui_project_bridge import GUIProjectBridge  # noqa: E402
from services.project_service import ProjectService  # noqa: E402
from services.project_service import _atomic_write_json  # noqa: E402
from services.segment_service import SegmentMappingError, SegmentService  # noqa: E402


class SegmentMigrationTests(unittest.TestCase):
    def test_legacy_segment_keeps_three_independent_text_fields(self) -> None:
        segment = Segment.from_dict(
            {
                "id": 7,
                "start": 1.25,
                "end": 3.5,
                "original_text": "今天发布第 2 版",
                "final_text": "Hôm nay phát hành phiên bản 2",
                "tts_text": "Hôm nay ta ra mắt bản hai",
                "speaker": "SPEAKER_01",
                "voice_name": "vieneu:nam_minh",
                "confidence": 0.93,
                "provider": "google_ai_studio",
                "manual_note": "giữ nguyên tên riêng",
            }
        )

        self.assertEqual("7", segment.id)
        self.assertEqual("今天发布第 2 版", segment.original_text)
        self.assertEqual("Hôm nay phát hành phiên bản 2", segment.subtitle_vi)
        self.assertEqual("Hôm nay ta ra mắt bản hai", segment.dubbing_vi)
        self.assertEqual("SPEAKER_01", segment.speaker_id)
        self.assertEqual("vieneu:nam_minh", segment.voice_profile_id)
        self.assertEqual("google_ai_studio", segment.provenance["translation"]["provider"])
        self.assertEqual("giữ nguyên tên riêng", segment.metadata["legacy_fields"]["manual_note"])

        segment.subtitle_vi = "Phụ đề đã sửa"
        self.assertEqual("Hôm nay ta ra mắt bản hai", segment.dubbing_vi)
        segment.dubbing_vi = "Lời đọc đã sửa"
        self.assertEqual("Phụ đề đã sửa", segment.subtitle_vi)

        saved = segment.to_dict()
        self.assertEqual(SEGMENT_SCHEMA_VERSION, saved["schema_version"])
        self.assertNotIn("final_text", saved)
        self.assertNotIn("tts_text", saved)

    def test_missing_ids_are_deterministic_and_duplicates_are_rejected(self) -> None:
        first = Segment.from_dict({"start": 0.0, "end": 1.0, "text": "one"}, default_id=3)
        again = Segment.from_dict({"start": 0.0, "end": 1.0, "text": "one"}, default_id=3)
        self.assertEqual("seg-000003", first.id)
        self.assertEqual(first.id, again.id)

        with self.assertRaisesRegex(SegmentValidationError, "Duplicate segment ID"):
            validate_segments(
                [
                    Segment("same", 0.0, 1.0),
                    Segment("same", 1.0, 2.0),
                ]
            )

    def test_legacy_alias_properties_remain_compatible(self) -> None:
        segment = Segment("cue-a", 0.0, 1.0, original_text="Hello")
        segment.raw_translation = "Xin chào"
        self.assertEqual("Xin chào", segment.final_text)
        segment.refined_translation = "Chào bạn"
        self.assertEqual("Chào bạn", segment.subtitle_vi)
        self.assertEqual("Chào bạn", segment.refined_translation)
        segment.tts_text = "Chào nhé"
        self.assertEqual("Chào nhé", segment.dubbing_vi)
        self.assertEqual("Chào nhé", segment.tts_source_text)

    def test_translation_mapping_preserves_ids_and_rejects_reordering(self) -> None:
        service = SegmentService()
        base = [
            Segment("cue-a", 0.0, 1.0, original_text="Hello"),
            Segment("cue-b", 1.0, 2.0, original_text="world"),
        ]
        mapped = service.apply_translations(
            base,
            [
                {"start": 0.0, "end": 1.0, "text": "Xin chào"},
                {"start": 1.0, "end": 2.0, "text": "thế giới"},
            ],
        )
        self.assertEqual(["cue-a", "cue-b"], [segment.id for segment in mapped])

        with self.assertRaisesRegex(SegmentMappingError, "IDs/count/order"):
            service.apply_translations(
                base,
                [
                    {"id": "cue-b", "start": 1.0, "end": 2.0, "text": "thế giới"},
                    {"id": "cue-a", "start": 0.0, "end": 1.0, "text": "Xin chào"},
                ],
            )


class ProjectStateMigrationTests(unittest.TestCase):
    def test_legacy_project_preserves_unknown_fields_and_signatures(self) -> None:
        state = ProjectState.from_dict(
            {
                "project_id": "legacy",
                "project_root": "project-root",
                "input_video": "source.mp4",
                "settings": {"translation_signature": "old-signature"},
                "custom_layout": {"zoom": 1.4},
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 2.0,
                        "original_text": "Hello",
                        "final_text": "Xin chào",
                        "tts_text": "Chào bạn",
                    }
                ],
            }
        )

        self.assertEqual(PROJECT_SCHEMA_VERSION, state.schema_version)
        self.assertEqual("old-signature", state.provenance["translation"]["input_signature"])
        self.assertEqual({"zoom": 1.4}, state.extensions["custom_layout"])
        self.assertEqual("Xin chào", state.segments[0].subtitle_vi)
        self.assertEqual("Chào bạn", state.segments[0].dubbing_vi)
        self.assertEqual(1, state.migration_history[-1]["from"])
        self.assertEqual({"zoom": 1.4}, state.to_dict()["custom_layout"])

    def test_future_project_schema_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProjectMigrationError, "newer than supported"):
            ProjectState.from_dict(
                {
                    "schema_version": PROJECT_SCHEMA_VERSION + 1,
                    "project_id": "future",
                    "project_root": "root",
                    "input_video": "video.mp4",
                }
            )

    def test_legacy_parallel_segment_lists_merge_without_losing_source(self) -> None:
        state = ProjectState.from_dict(
            {
                "project_id": "legacy-lists",
                "project_root": "root",
                "input_video": "video.mp4",
                "current_segments": [
                    {"id": 9, "start": 0.0, "end": 1.0, "text": "Hello"}
                ],
                "current_translated_segments": [
                    {"id": 9, "start": 0.0, "end": 1.0, "text": "Xin chào", "tts_text": "Chào bạn"}
                ],
            }
        )
        self.assertEqual("9", state.segments[0].id)
        self.assertEqual("Hello", state.segments[0].original_text)
        self.assertEqual("Xin chào", state.segments[0].subtitle_vi)
        self.assertEqual("Chào bạn", state.segments[0].dubbing_vi)

    def test_service_migrates_legacy_artifact_with_non_overwriting_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project_root = workspace / "projects" / "legacy"
            translation_path = project_root / "translation" / "translation_final.json"
            translation_path.parent.mkdir(parents=True)
            translation_path.write_text(
                json.dumps(
                    [
                        {
                            "id": 4,
                            "start": 0.0,
                            "end": 1.5,
                            "original_text": "Good morning",
                            "final_text": "Chào buổi sáng",
                            "tts_text": "Chào buổi sáng nhé",
                            "speaker": "speaker-1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            legacy_payload = {
                "project_id": "legacy",
                "project_root": str(project_root),
                "input_video": str(workspace / "video.mp4"),
                "artifacts": {"translation_final": str(translation_path)},
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
            state_path = project_root / "project.json"
            state_path.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

            service = ProjectService(str(workspace))
            migrated = service.load_project(str(state_path))
            backup_path = Path(f"{state_path}.schema-v1.bak")

            self.assertTrue(backup_path.is_file())
            self.assertEqual(legacy_payload, json.loads(backup_path.read_text(encoding="utf-8")))
            self.assertEqual("4", migrated.segments[0].id)
            self.assertEqual("Chào buổi sáng", migrated.segments[0].subtitle_vi)
            self.assertEqual("Chào buổi sáng nhé", migrated.segments[0].dubbing_vi)

            saved_payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(PROJECT_SCHEMA_VERSION, saved_payload["schema_version"])
            self.assertEqual("speaker-1", saved_payload["segments"][0]["speaker_id"])
            backup_before = backup_path.read_bytes()
            service.load_project(str(state_path))
            self.assertEqual(backup_before, backup_path.read_bytes())
            self.assertEqual([], list(project_root.glob(".*.tmp")))

    def test_atomic_project_and_artifact_save_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project_root = workspace / "projects" / "roundtrip"
            service = ProjectService(str(workspace))
            state = ProjectState(
                project_id="roundtrip",
                project_root=str(project_root),
                input_video=str(workspace / "video.mp4"),
                input_language="zh",
                segments=[
                    Segment(
                        "cue-001",
                        0.0,
                        2.0,
                        original_text="你好",
                        subtitle_vi="Xin chào",
                        dubbing_vi="Chào bạn",
                        speaker_id="speaker-a",
                        voice_profile_id="vieneu:nu-thu",
                        confidence=0.98,
                        qa_flags=["name_review"],
                        provenance={"translation": {"provider": "ollama", "model": "qwen"}},
                    )
                ],
            )
            state_path = Path(service.save_project(state))
            service.save_json_artifact(state, "facts", "analysis/facts.json", {"text": "Tiếng Việt"})
            reopened = service.load_project(str(state_path))

            self.assertEqual("cue-001", reopened.segments[0].id)
            self.assertEqual("你好", reopened.segments[0].original_text)
            self.assertEqual("Xin chào", reopened.segments[0].subtitle_vi)
            self.assertEqual("Chào bạn", reopened.segments[0].dubbing_vi)
            self.assertEqual("speaker-a", reopened.segments[0].speaker_id)
            self.assertEqual("vieneu:nu-thu", reopened.segments[0].voice_profile_id)
            self.assertEqual({"text": "Tiếng Việt"}, service.load_json_artifact(reopened, "facts"))
            self.assertEqual([], list(project_root.rglob("*.tmp")))

    def test_atomic_replace_failure_preserves_previous_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project.json"
            target.write_text('{"stable": true}\n', encoding="utf-8")
            with patch("services.project_service.os.replace", side_effect=OSError("locked")):
                with self.assertRaisesRegex(OSError, "locked"):
                    _atomic_write_json(str(target), {"stable": False})
            self.assertEqual({"stable": True}, json.loads(target.read_text(encoding="utf-8")))
            self.assertEqual([], list(Path(directory).glob(".*.tmp")))

    def test_setting_signature_is_mirrored_to_stage_provenance(self) -> None:
        state = ProjectState("signature", "root", "video.mp4")
        state.set_provenance("translation", {"provider": "ollama", "model": "qwen"})
        state.set_setting("translation_signature", "sha256-value")
        self.assertEqual(
            {"provider": "ollama", "model": "qwen", "input_signature": "sha256-value"},
            state.provenance["translation"],
        )

    def test_artifact_path_cannot_escape_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = ProjectService(directory)
            state = ProjectState("safe", str(Path(directory) / "projects" / "safe"), "video.mp4")
            with self.assertRaisesRegex(ValueError, "escapes project root"):
                service.save_json_artifact(state, "bad", "../../outside.json", {})

    def test_gui_bridge_persists_canonical_state_and_returns_copies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            service = ProjectService(str(workspace))
            bridge = GUIProjectBridge(service)
            state = ProjectState("bridge", str(workspace / "projects" / "bridge"), "video.mp4", input_language="en")
            source_models = bridge.persist_transcription(
                state,
                [{"id": "cue-1", "start": 0.0, "end": 1.0, "text": "Hello"}],
            )
            bridge.persist_translation(
                state,
                source_models,
                [
                    {
                        "id": "cue-1",
                        "start": 0.0,
                        "end": 1.0,
                        "text": "Xin chào",
                        "dubbing_vi": "Chào bạn",
                        "provider": "ollama",
                    }
                ],
            )

            reopened = service.load_project(service.project_file(state.project_root))
            context = bridge.load_context(reopened)
            current = context["current_translated_segments"][0]
            self.assertEqual("cue-1", current["id"])
            self.assertEqual("Hello", current["original_text"])
            self.assertEqual("Xin chào", current["subtitle_vi"])
            self.assertEqual("Chào bạn", current["dubbing_vi"])
            context["current_translated_segment_models"][0].subtitle_vi = "changed in UI"
            self.assertEqual("Xin chào", reopened.segments[0].subtitle_vi)


class ProvenanceSignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ProjectService("workspace")
        self.segments = [
            {
                "id": "cue-1",
                "start": 0.0,
                "end": 1.0,
                "original_text": "Hello 2026",
                "subtitle_vi": "Xin chào năm 2026",
                "dubbing_vi": "Chào bạn trong năm hai nghìn không trăm hai mươi sáu",
            }
        ]

    def test_translation_signature_covers_full_provenance(self) -> None:
        baseline_options = {
            "src_lang": "en",
            "target_lang": "vi",
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "model_revision": "sha-a",
            "prompt_version": 3,
            "schema_version": 2,
            "normalizer_version": "norm-a",
            "fallback_provider": "openai",
            "fallback_model": "gpt-4o-mini",
        }
        baseline = self.service.build_translation_signature(self.segments, **baseline_options)
        variants = {
            "provider": "openai",
            "model": "qwen2.5:14b",
            "model_revision": "sha-b",
            "prompt_version": 4,
            "schema_version": 3,
            "normalizer_version": "norm-b",
            "fallback_provider": "google_ai_studio",
            "fallback_model": "gemini-flash",
        }
        for key, value in variants.items():
            with self.subTest(key=key):
                options = dict(baseline_options)
                options[key] = value
                self.assertNotEqual(
                    baseline,
                    self.service.build_translation_signature(self.segments, **options),
                )

        changed_id = [{**self.segments[0], "id": "cue-2"}]
        changed_text = [{**self.segments[0], "original_text": "Goodbye"}]
        self.assertNotEqual(baseline, self.service.build_translation_signature(changed_id, **baseline_options))
        self.assertNotEqual(baseline, self.service.build_translation_signature(changed_text, **baseline_options))

    def test_voice_signature_covers_provenance_but_ignores_mix_volume(self) -> None:
        options = {
            "voice_name": "vieneu:nu-thu",
            "provider": "vieneu",
            "engine": "vieneu",
            "model": "vieneu-tts-v3-turbo",
            "model_revision": "rev-a",
            "prompt_version": "rewrite-v1",
            "schema_version": 2,
            "normalizer_version": "norm-v1",
            "normalizer_signature": "dict-a",
        }
        baseline = self.service.build_voice_signature(
            self.segments, original_volume=20, dub_volume=80, **options
        )
        mix_only = self.service.build_voice_signature(
            self.segments, original_volume=90, dub_volume=30, **options
        )
        self.assertEqual(baseline, mix_only)

        for key, value in {
            "provider": "piper",
            "engine": "piper",
            "model": "other-model",
            "model_revision": "rev-b",
            "prompt_version": "rewrite-v2",
            "schema_version": 3,
            "normalizer_version": "norm-v2",
            "normalizer_signature": "dict-b",
        }.items():
            with self.subTest(key=key):
                changed = dict(options)
                changed[key] = value
                self.assertNotEqual(baseline, self.service.build_voice_signature(self.segments, **changed))


if __name__ == "__main__":
    unittest.main()
