from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import media_contract  # noqa: E402
from core.models import Segment  # noqa: E402
from media_contract import MediaValidationError, build_export_plan, probe_media  # noqa: E402
from subtitle_builder import generate_srt  # noqa: E402
from workflows.export_workflow import ExportWorkflow  # noqa: E402


class MediaExportContractTests(unittest.TestCase):
    def test_utf8_srt_is_atomic_and_independent_of_tts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "phụ-đề.srt"
            segments = [
                Segment(
                    id="seg-zh",
                    start=0.0,
                    end=1.25,
                    original_text="你好",
                    subtitle_vi="Xin chào Việt Nam",
                    dubbing_vi="",
                )
            ]
            self.assertTrue(generate_srt(segments, str(output)))
            content = output.read_text(encoding="utf-8")
            self.assertIn("Xin chào Việt Nam", content)
            self.assertIn("00:00:00,000 --> 00:00:01,250", content)
            self.assertEqual([], list(output.parent.glob(f".{output.name}.*.tmp")))

    def test_probe_media_uses_argument_list_and_validates_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "video.mp4"
            tool = Path(tmp) / "ffprobe.exe"
            media.touch()
            tool.touch()
            completed = SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": {"duration": "2.5"},
                        "streams": [
                            {"codec_type": "video", "codec_name": "h264"},
                            {"codec_type": "audio", "codec_name": "aac"},
                        ],
                    }
                ),
                stderr="",
            )
            with patch.object(media_contract.subprocess, "run", return_value=completed) as run:
                result = probe_media(str(media), ffprobe_path=str(tool))
            self.assertEqual(1, result["video_streams"])
            self.assertEqual(2.5, result["duration_seconds"])
            self.assertIsInstance(run.call_args.args[0], list)
            self.assertFalse(run.call_args.kwargs["shell"])

    def test_probe_rejects_output_without_video_or_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "bad.mp4"
            tool = Path(tmp) / "ffprobe.exe"
            media.touch()
            tool.touch()
            completed = SimpleNamespace(returncode=0, stdout='{"format":{"duration":"0"},"streams":[]}', stderr="")
            with patch.object(media_contract.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(MediaValidationError, "Invalid video output"):
                    probe_media(str(media), ffprobe_path=str(tool))

    def test_export_plan_records_nvenc_and_cpu_fallback(self) -> None:
        with patch.object(media_contract, "ffmpeg_supports_encoder", return_value=True):
            accelerated = build_export_plan()
        self.assertEqual("h264_nvenc", accelerated["preferred_encoder"])
        self.assertEqual("libx264", accelerated["fallback_encoder"])
        self.assertEqual(1, accelerated["video_encode_passes"])
        with patch.object(media_contract, "ffmpeg_supports_encoder", return_value=False):
            cpu = build_export_plan()
        self.assertEqual("libx264", cpu["preferred_encoder"])

    def test_both_mode_intermediate_mux_never_encodes_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "source.mp4"
            audio = root / "voice.wav"
            srt = root / "vi.srt"
            ass = root / "live_preview_vi.ass"
            output = root / "final.mp4"
            for path in (video, audio, srt, ass):
                path.touch()
            workflow = ExportWorkflow(str(root))
            workflow.engine_runtime.get_video_dimensions = Mock(return_value=(1920, 1080))
            workflow.engine_runtime.mux_audio_for_preview = Mock(
                side_effect=lambda _video, _audio, target, **_kwargs: Path(target).touch()
            )

            def render(**kwargs):
                Path(kwargs["output_path"]).touch()

            with (
                patch("workflows.export_workflow.probe_media", side_effect=[{"duration_seconds": 2.0}, {"duration_seconds": 2.0, "video_streams": 1}]),
                patch("workflows.export_workflow.build_export_plan", return_value={"video_encode_passes": 1, "preferred_encoder": "h264_nvenc", "fallback_encoder": "libx264"}),
                patch.object(workflow, "_export_subtitle_video", side_effect=render) as final_encode,
            ):
                result = workflow.run(
                    video_path=str(video),
                    output_path=str(output),
                    mode="both",
                    srt_path=str(srt),
                    ass_path=str(ass),
                    audio_path=str(audio),
                    output_fps="30",
                    project_temp_dir=str(root / "work"),
                )
            self.assertEqual(str(output), result)
            self.assertEqual(1, final_encode.call_count)
            mux_kwargs = workflow.engine_runtime.mux_audio_for_preview.call_args.kwargs
            self.assertIsNone(mux_kwargs["output_fps"])
            self.assertIsNone(mux_kwargs.get("target_width"))


if __name__ == "__main__":
    unittest.main()
