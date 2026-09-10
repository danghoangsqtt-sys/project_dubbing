from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from network_policy import OfflineLockError, assert_network_allowed, is_loopback_url  # noqa: E402
from translation.orchestrator import TranslationOrchestrator  # noqa: E402
from translation.providers.google_web_translator import GoogleWebTranslatorProvider  # noqa: E402
from translation.srt_utils import clone_with_texts  # noqa: E402
from translation.validation import annotate_translation_issues  # noqa: E402
from workflows.voice_workflow import VoiceWorkflow  # noqa: E402


class _ConfiguredProvider:
    model_name = "fixture-model"

    @staticmethod
    def is_configured() -> bool:
        return True


class TranslationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segments = [
            {"id": "seg-a", "start": 0.0, "end": 2.0, "text": "Alice bought RTX 3060 for 399 dollars."},
            {"id": "seg-b", "start": 2.0, "end": 4.0, "text": "Second line"},
        ]

    def test_network_policy_blocks_public_hosts_but_allows_loopback(self) -> None:
        self.assertTrue(is_loopback_url("http://localhost:11434/v1"))
        with patch.dict(os.environ, {"CAPCAP_OFFLINE_LOCK": "1"}, clear=False):
            assert_network_allowed("http://127.0.0.1:11434/v1", purpose="Ollama")
            with self.assertRaisesRegex(OfflineLockError, "Offline Lock blocked"):
                assert_network_allowed("https://api.openai.com/v1", purpose="OpenAI")

    def test_google_provider_is_blocked_before_request(self) -> None:
        provider = GoogleWebTranslatorProvider()
        with (
            patch.dict(os.environ, {"CAPCAP_OFFLINE_LOCK": "true"}, clear=False),
            patch("translation.providers.google_web_translator.requests.get") as request,
        ):
            with self.assertRaises(OfflineLockError):
                provider.translate_batch(["hello"], src_lang="en", target_lang="vi")
        request.assert_not_called()

    def test_hybrid_uses_google_fallback_after_primary_failure(self) -> None:
        orchestrator = TranslationOrchestrator()
        orchestrator.google_web.translate_batch = Mock(return_value=["Alice mua RTX 3060 giá 399 đô.", "Dòng hai"])
        with (
            patch.dict(os.environ, {"CAPCAP_OFFLINE_LOCK": "0", "OPENAI_PROVIDER": "openai"}, clear=False),
            patch.object(orchestrator, "_resolve_ai_provider", return_value=("openai", _ConfiguredProvider())),
            patch.object(orchestrator, "_run_ai_batches", side_effect=RuntimeError("primary unavailable")),
        ):
            result = orchestrator.translate_segments(segments=self.segments, src_lang="en")
        self.assertTrue(result.success)
        self.assertTrue(result.used_fallback)
        self.assertEqual("google-web", result.primary_provider)
        self.assertEqual(["seg-a", "seg-b"], [item["id"] for item in result.segments])

    def test_offline_local_failure_never_calls_google(self) -> None:
        orchestrator = TranslationOrchestrator()
        orchestrator.google_web.translate_batch = Mock(side_effect=AssertionError("network fallback called"))
        with (
            patch.dict(os.environ, {"CAPCAP_OFFLINE_LOCK": "1", "OPENAI_PROVIDER": "openai", "OPENAI_API_KEY": "local"}, clear=False),
            patch.object(orchestrator, "_resolve_ai_provider", return_value=("ollama", _ConfiguredProvider())),
            patch.object(orchestrator, "_run_ai_batches", side_effect=RuntimeError("ollama unavailable")),
        ):
            result = orchestrator.translate_segments(segments=self.segments, src_lang="en")
        self.assertFalse(result.success)
        self.assertEqual("offline_translation", result.stage)
        orchestrator.google_web.translate_batch.assert_not_called()

    def test_optimization_runs_only_when_enabled(self) -> None:
        orchestrator = TranslationOrchestrator()
        optimized = clone_with_texts(self.segments, ["Alice mua RTX 3060 giá 399 đô.", "Dòng hai"], "openai", True)
        with (
            patch.dict(os.environ, {"CAPCAP_OFFLINE_LOCK": "0"}, clear=False),
            patch.object(orchestrator, "_resolve_ai_provider", return_value=("openai", _ConfiguredProvider())),
            patch.object(
                orchestrator,
                "_run_ai_batches",
                return_value=(["Alice mua RTX 3060 giá 399 đô.", "Dòng hai"], ["openai"], []),
            ),
            patch.object(orchestrator, "_maybe_optimize_subtitle_segments", return_value=optimized) as optimize,
        ):
            enabled = orchestrator.translate_segments(
                segments=self.segments, src_lang="en", optimize_subtitles=True
            )
            disabled = orchestrator.translate_segments(
                segments=self.segments, src_lang="en", optimize_subtitles=False
            )
        self.assertTrue(enabled.success and disabled.success)
        self.assertEqual(1, optimize.call_count)

    def test_mapping_and_protected_facts_are_validated(self) -> None:
        translated = clone_with_texts(self.segments, ["Alice đã mua card đồ họa.", "Dòng hai"], "fixture")
        annotated = annotate_translation_issues(self.segments, translated)
        self.assertEqual("seg-a", annotated[0]["id"])
        self.assertIn("missing_number:3060", annotated[0]["qa_flags"])
        self.assertIn("missing_number:399", annotated[0]["qa_flags"])
        with self.assertRaisesRegex(ValueError, "ID mismatch"):
            annotate_translation_issues(
                self.segments,
                [{**translated[0], "id": "wrong"}, translated[1]],
            )

    def test_dubbing_rewrite_is_independent_and_preferred_by_tts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workflow = VoiceWorkflow(tmp)
            with patch.object(workflow, "_plan_initial_dubbing_text", return_value="Alice mua RTX 3060.") as rewrite:
                prepared = workflow._prepare_segments_for_tts(
                    [
                        {
                            "id": "seg-a",
                            "start": 0.0,
                            "end": 3.0,
                            "original_text": "Alice bought RTX 3060.",
                            "subtitle_vi": "Alice đã mua RTX 3060 với mức giá tốt.",
                            "text": "Alice đã mua RTX 3060 với mức giá tốt.",
                        }
                    ],
                    voice_provider="vieneu",
                    ai_rewrite_dubbing=True,
                    source_language="en",
                    log=False,
                )
        rewrite.assert_called_once()
        self.assertEqual("Alice đã mua RTX 3060 với mức giá tốt.", prepared[0]["subtitle_vi"])
        self.assertEqual("Alice mua RTX 3060.", prepared[0]["dubbing_vi"])
        self.assertEqual("Alice mua RTX 3060.", workflow._segment_tts_text(prepared[0]))


if __name__ == "__main__":
    unittest.main()
