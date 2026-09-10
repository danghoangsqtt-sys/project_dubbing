from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from runtime_paths import bin_path, subprocess_text_kwargs


class MediaValidationError(RuntimeError):
    pass


def probe_media(path: str, *, ffprobe_path: str = "", timeout: int = 30) -> dict[str, Any]:
    media_path = Path(str(path or ""))
    if not media_path.is_file():
        raise MediaValidationError(f"Media file does not exist: {media_path}")
    ffprobe = str(ffprobe_path or bin_path("ffmpeg", "ffprobe.exe"))
    if not Path(ffprobe).is_file():
        raise MediaValidationError(f"ffprobe is unavailable: {ffprobe}")
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(media_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        shell=False,
        timeout=max(1, int(timeout)),
        **subprocess_text_kwargs(),
    )
    if result.returncode != 0:
        raise MediaValidationError(result.stderr or result.stdout or "ffprobe failed")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise MediaValidationError(f"ffprobe returned invalid JSON: {exc}") from exc
    streams = list(payload.get("streams", []) or [])
    duration = float((payload.get("format", {}) or {}).get("duration", 0.0) or 0.0)
    summary = {
        "path": str(media_path.resolve()),
        "duration_seconds": duration,
        "video_streams": sum(1 for stream in streams if stream.get("codec_type") == "video"),
        "audio_streams": sum(1 for stream in streams if stream.get("codec_type") == "audio"),
        "video_codecs": [str(stream.get("codec_name") or "") for stream in streams if stream.get("codec_type") == "video"],
        "audio_codecs": [str(stream.get("codec_name") or "") for stream in streams if stream.get("codec_type") == "audio"],
    }
    if summary["duration_seconds"] <= 0 or summary["video_streams"] < 1:
        raise MediaValidationError(
            f"Invalid video output: duration={duration}, video_streams={summary['video_streams']}"
        )
    return summary


def ffmpeg_supports_encoder(
    encoder: str, *, ffmpeg_path: str = "", timeout: int = 15
) -> bool:
    ffmpeg = str(ffmpeg_path or bin_path("ffmpeg", "ffmpeg.exe"))
    if not Path(ffmpeg).is_file():
        return False
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        capture_output=True,
        shell=False,
        timeout=max(1, int(timeout)),
        **subprocess_text_kwargs(),
    )
    return result.returncode == 0 and str(encoder or "") in (result.stdout or "")


def build_export_plan(*, ffmpeg_path: str = "") -> dict[str, Any]:
    nvenc = ffmpeg_supports_encoder("h264_nvenc", ffmpeg_path=ffmpeg_path)
    return {
        "preferred_encoder": "h264_nvenc" if nvenc else "libx264",
        "fallback_encoder": "libx264" if nvenc else "",
        "nvenc_supported": nvenc,
        "video_encode_passes": 1,
        "intermediate_video_codec": "copy",
        "validation": "ffprobe",
    }
