from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from typing import Any

from core.models import (
    SEGMENT_SCHEMA_VERSION,
    Segment,
    coerce_segments,
    normalize_segment_id,
    validate_segments,
)
from core.state import PROJECT_SCHEMA_VERSION, ProjectState


def _atomic_write_json(path: str, payload: Any) -> None:
    """Write UTF-8 JSON beside its target, then atomically replace it."""

    target = os.path.abspath(path)
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(target)}.", suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
    except BaseException:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


class ProjectService:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.projects_root = os.path.join(workspace_root, "projects")

    def ensure_project(
        self,
        video_path: str,
        *,
        mode: str = "subtitle",
        translator_ai: bool = True,
        translator_style: str = "",
        input_language: str = "auto",
        target_language: str = "vi",
    ) -> ProjectState:
        os.makedirs(self.projects_root, exist_ok=True)
        project_id = self._build_project_id(video_path)
        project_root = os.path.join(self.projects_root, project_id)
        self._ensure_project_dirs(project_root)
 
        state_path = self.project_file(project_root)
        if os.path.exists(state_path):
            state = self.load_project(state_path)
            state.input_video = video_path
            state.mode = mode
            state.translator_ai = translator_ai
            state.translator_style = translator_style
            state.input_language = input_language
            state.target_language = target_language
            state.source_fingerprint = self._file_signature(video_path)
            self.save_project(state)
            return state
 
        state = ProjectState(
            project_id=project_id,
            project_root=project_root,
            input_video=video_path,
            input_language=input_language,
            target_language=target_language,
            mode=mode,
            translator_ai=translator_ai,
            translator_style=translator_style,
            source_fingerprint=self._file_signature(video_path),
        )
        self.save_project(state)
        return state

    def load_project(self, state_path: str) -> ProjectState:
        with open(state_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Project JSON root must be an object")
        try:
            source_version = int(payload.get("schema_version", 1) or 1)
        except (TypeError, ValueError):
            source_version = 1
        state = ProjectState.from_dict(payload)
        if not state.project_root:
            state.project_root = os.path.dirname(os.path.abspath(state_path))
        recovered_segments = False
        if not state.segments:
            legacy_segments = self._load_best_legacy_segment_artifact(state)
            if legacy_segments:
                state.set_segments(legacy_segments)
                recovered_segments = True
        if not state.source_fingerprint and state.input_video:
            state.source_fingerprint = self._file_signature(state.input_video)
        if source_version < PROJECT_SCHEMA_VERSION or recovered_segments:
            self._write_migration_backup(state_path, source_version)
            self.save_project(state)
        return state

    def save_project(self, state: ProjectState) -> str:
        self._ensure_project_dirs(state.project_root)
        state.segments = validate_segments(state.segments)
        state.touch()
        state_path = self.project_file(state.project_root)
        _atomic_write_json(state_path, state.to_dict())
        return state_path

    def save_json_artifact(
        self,
        state: ProjectState,
        artifact_name: str,
        relative_path: str,
        payload: Any,
    ) -> str:
        output_path = self._project_relative_path(state.project_root, relative_path)
        _atomic_write_json(output_path, payload)
        state.set_artifact(artifact_name, output_path)
        self.save_project(state)
        return output_path

    def save_segment_artifact(
        self,
        state: ProjectState,
        artifact_name: str,
        relative_path: str,
        segments: list[Segment],
    ) -> str:
        return self.save_json_artifact(
            state,
            artifact_name,
            relative_path,
            [segment.to_dict() for segment in validate_segments(segments)],
        )

    def load_json_artifact(self, state: ProjectState, artifact_name: str, default: Any = None) -> Any:
        path = state.artifacts.get(artifact_name, "")
        if path and not os.path.isabs(path):
            path = os.path.join(state.project_root, path)
        if not path or not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def load_segment_artifact(self, state: ProjectState, artifact_name: str) -> list[Segment]:
        payload = self.load_json_artifact(state, artifact_name, default=[])
        return coerce_segments(payload or [])

    def update_step(self, state: ProjectState, step_name: str, status: str, *, save: bool = True) -> ProjectState:
        state.set_step_status(step_name, status)
        if save:
            self.save_project(state)
        return state

    def update_artifact(self, state: ProjectState, artifact_name: str, path: str, *, save: bool = True) -> ProjectState:
        state.set_artifact(artifact_name, path)
        if save:
            self.save_project(state)
        return state

    def project_file(self, project_root: str) -> str:
        return os.path.join(project_root, "project.json")

    def build_path(self, state: ProjectState, *parts: str) -> str:
        return os.path.join(state.project_root, *parts)

    def _ensure_project_dirs(self, project_root: str) -> None:
        for relative_dir in (
            "source",
            "analysis",
            "translation",
            os.path.join("audio", "separated"),
            os.path.join("audio", "tts_segments"),
            "subtitle",
            os.path.join("preview", "cache"),
            "export",
            "logs",
        ):
            os.makedirs(os.path.join(project_root, relative_dir), exist_ok=True)

    def _build_project_id(self, video_path: str) -> str:
        video_name = os.path.splitext(os.path.basename(video_path))[0] or "project"
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", video_name).strip("_").lower() or "project"
        digest = hashlib.sha1(os.path.abspath(video_path).encode("utf-8")).hexdigest()[:8]
        return f"{slug}_{digest}"

    def _hash_payload(self, payload: Any) -> str:
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _project_relative_path(self, project_root: str, relative_path: str) -> str:
        root = os.path.abspath(project_root)
        candidate = os.path.abspath(os.path.join(root, str(relative_path or "")))
        if os.path.commonpath([root, candidate]) != root:
            raise ValueError(f"Artifact path escapes project root: {relative_path!r}")
        return candidate

    def _write_migration_backup(self, state_path: str, source_version: int) -> str:
        backup_path = f"{os.path.abspath(state_path)}.schema-v{source_version}.bak"
        try:
            with open(state_path, "rb") as source, open(backup_path, "xb") as backup:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    backup.write(block)
                backup.flush()
                os.fsync(backup.fileno())
        except FileExistsError:
            pass
        return backup_path

    def _load_best_legacy_segment_artifact(self, state: ProjectState) -> list[Segment]:
        for artifact_name in (
            "translation_final",
            "translation_refined",
            "translation_raw",
            "transcript_segments",
        ):
            path = str(state.artifacts.get(artifact_name, "") or "")
            if path and not os.path.isabs(path):
                path = os.path.join(state.project_root, path)
            if not path or not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list) and payload:
                return validate_segments(payload)
        return []

    @staticmethod
    def _segment_value(segment: Segment | dict[str, Any], *keys: str) -> Any:
        if isinstance(segment, Segment):
            for key in keys:
                if hasattr(segment, key):
                    value = getattr(segment, key)
                    if value not in (None, ""):
                        return value
                value = segment.metadata.get(key)
                if value not in (None, ""):
                    return value
            return ""
        current = dict(segment or {})
        for key in keys:
            value = current.get(key)
            if value not in (None, ""):
                return value
        return ""

    def build_translation_provenance(
        self,
        *,
        provider: str = "",
        model: str = "",
        model_revision: str = "",
        prompt_version: int | str = 3,
        schema_version: int = SEGMENT_SCHEMA_VERSION,
        normalizer_version: str = "",
        fallback_provider: str = "",
        fallback_model: str = "",
    ) -> dict[str, Any]:
        resolved_provider = str(
            provider or os.getenv("OPENAI_PROVIDER") or os.getenv("AI_POLISHER_PROVIDER") or "google"
        ).strip().lower()
        if not model:
            if resolved_provider in {"google", "google_ai_studio", "gemini"}:
                model = os.getenv("GOOGLE_AI_STUDIO_MODEL", "") or os.getenv("OPENAI_MODEL", "")
            elif resolved_provider == "ollama":
                model = os.getenv("OLLAMA_MODEL", "") or os.getenv("OPENAI_MODEL", "")
            elif resolved_provider == "openai":
                model = os.getenv("OPENAI_MODEL", "")
        return {
            "stage": "translation",
            "provider": resolved_provider,
            "engine": "translation_orchestrator",
            "model": str(model or "").strip(),
            "model_revision": str(model_revision or "").strip(),
            "prompt_version": str(prompt_version),
            "schema_version": int(schema_version),
            "normalizer_version": str(normalizer_version or "").strip(),
            "fallback_provider": str(fallback_provider or "").strip().lower(),
            "fallback_model": str(fallback_model or "").strip(),
        }

    def build_voice_provenance(
        self,
        *,
        voice_name: str,
        provider: str = "",
        engine: str = "tts",
        model: str = "",
        model_revision: str = "",
        prompt_version: int | str = "",
        schema_version: int = SEGMENT_SCHEMA_VERSION,
        normalizer_version: str = "",
    ) -> dict[str, Any]:
        resolved_provider = str(provider or "").strip().lower()
        if not resolved_provider:
            raw_voice = str(voice_name or "").strip()
            resolved_provider = raw_voice.split(":", 1)[0].lower() if ":" in raw_voice else "piper"
        return {
            "stage": "generate_tts",
            "provider": resolved_provider,
            "engine": str(engine or "tts").strip().lower(),
            "model": str(model or "").strip(),
            "model_revision": str(model_revision or "").strip(),
            "prompt_version": str(prompt_version or ""),
            "schema_version": int(schema_version),
            "normalizer_version": str(normalizer_version or "").strip(),
        }

    def _file_signature(self, path: str) -> dict[str, Any]:
        normalized = str(path or "").strip()
        if not normalized:
            return {"path": "", "exists": False}
        try:
            stat = os.stat(normalized)
            return {
                "path": os.path.abspath(normalized),
                "exists": True,
                "size": int(stat.st_size),
                "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
            }
        except OSError:
            return {"path": os.path.abspath(normalized), "exists": False}

    def build_translation_signature(
        self,
        source_segments: list[Segment | dict[str, Any]],
        *,
        src_lang: str = "auto",
        target_lang: str = "vi",
        enable_polish: bool = True,
        optimize_subtitles: bool = False,
        style_instruction: str = "",
        provider: str = "",
        model: str = "",
        model_revision: str = "",
        prompt_version: int | str = 3,
        schema_version: int = SEGMENT_SCHEMA_VERSION,
        normalizer_version: str = "",
        fallback_provider: str = "",
        fallback_model: str = "",
    ) -> str:
        payload = {
            "signature_version": 4,
            "stage": "translation",
            "producer": self.build_translation_provenance(
                provider=provider,
                model=model,
                model_revision=model_revision,
                prompt_version=prompt_version,
                schema_version=schema_version,
                normalizer_version=normalizer_version,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            ),
            "src_lang": str(src_lang or "auto").strip().lower(),
            "target_lang": str(target_lang or "vi").strip().lower(),
            "enable_polish": bool(enable_polish),
            "optimize_subtitles": bool(optimize_subtitles),
            "style_instruction": str(style_instruction or "").strip(),
            "segments": [
                {
                    "id": normalize_segment_id(self._segment_value(seg, "id"), index),
                    "start": round(float(self._segment_value(seg, "start") or 0.0), 3),
                    "end": round(float(self._segment_value(seg, "end") or 0.0), 3),
                    "original_text": str(
                        self._segment_value(seg, "original_text", "source_text", "text") or ""
                    ).strip(),
                }
                for index, seg in enumerate(list(source_segments or []), start=1)
            ],
        }
        return self._hash_payload(payload)

    def build_voice_signature(
        self,
        segments: list[Segment | dict[str, Any]],
        *,
        audio_handling_mode: str = "fast",
        voice_name: str = "",
        voice_speed: float = 1.0,
        timing_sync_mode: str = "off",
        background_path: str = "",
        original_volume: int = 50,
        dub_volume: int = 100,
        normalizer_signature: str = "",
        provider: str = "",
        engine: str = "tts",
        model: str = "",
        model_revision: str = "",
        prompt_version: int | str = "",
        schema_version: int = SEGMENT_SCHEMA_VERSION,
        normalizer_version: str = "",
    ) -> str:
        safe_voice_speed = max(0.5, min(1.30, float(voice_speed or 1.0)))
        def _segment_voice_text(seg) -> str:
            return str(
                self._segment_value(seg, "dubbing_vi", "tts_text", "subtitle_vi", "text") or ""
            ).strip()
        payload = {
            "signature_version": 3,
            "stage": "generate_tts",
            "producer": self.build_voice_provenance(
                voice_name=voice_name,
                provider=provider,
                engine=engine,
                model=model,
                model_revision=model_revision,
                prompt_version=prompt_version,
                schema_version=schema_version,
                normalizer_version=normalizer_version,
            ),
            "audio_handling_mode": str(audio_handling_mode or "fast").strip().lower(),
            "voice_name": str(voice_name or "").strip(),
            "voice_speed": round(safe_voice_speed, 3),
            "timing_sync_mode": str(timing_sync_mode or "off").strip().lower(),
            # Voice generation produces the standalone TS1 track.  Original,
            # Music, and per-track volume values belong to the later mix
            # stage and must not invalidate/re-run TTS when only the mix is
            # edited. Keep the parameters in the API for old callers.
            # The pronunciation dictionary changes generated audio without
            # changing the subtitle text.  Include its fingerprint so a
            # project edit invalidates the existing voice-track cache.
            "normalizer_signature": str(normalizer_signature or "").strip(),
            "segments": [
                {
                    "id": normalize_segment_id(self._segment_value(seg, "id"), index),
                    "start": round(float(self._segment_value(seg, "start") or 0.0), 3),
                    "end": round(float(self._segment_value(seg, "end") or 0.0), 3),
                    "text": _segment_voice_text(seg),
                    "group_id": str(self._segment_value(seg, "tts_group_id") or "").strip(),
                    # Per-speaker selections are resolved onto the segment by
                    # the editor.  They must participate in this signature so
                    # an assignment change cannot reuse an old voice track.
                    "voice_name": str(
                        self._segment_value(seg, "voice_profile_id", "voice_name") or ""
                    ).strip(),
                }
                for index, seg in enumerate(list(segments or []), start=1)
            ],
        }
        return self._hash_payload(payload)

    def build_extraction_signature(self, video_path: str) -> str:
        return self._hash_payload(
            {
                "video": self._file_signature(video_path),
            }
        )

    def build_ocr_transcription_signature(self, video_path: str, *, region: str = "bottom") -> str:
        """Fingerprint all inputs that affect video-subtitle OCR output."""
        return self._hash_payload(
            {
                # OCR text filtering and temporal merging are part of the
                # transcription result, not just a display concern.
                "version": 5,
                "video": self._file_signature(video_path),
                "region": str(region or "bottom").strip().lower(),
                "subtitle_rect": str(os.getenv("OCR_SUBTITLE_RECT") or "").strip(),
                "crop_ratio": str(os.getenv("OCR_CROP_RATIO") or "0.25").strip(),
                "sampling_fps": str(os.getenv("OCR_SAMPLING_FPS") or "auto").strip().lower(),
            }
        )

    def build_separation_signature(self, extracted_audio_path: str, *, audio_handling_mode: str = "fast") -> str:
        return self._hash_payload(
            {
                "version": 2,
                "audio_handling_mode": str(audio_handling_mode or "fast").strip().lower(),
                "extracted_audio": self._file_signature(extracted_audio_path),
            }
        )

    def build_transcription_signature(
        self,
        audio_path: str,
        *,
        whisper_model: str,
        source_language: str = "auto",
        audio_handling_mode: str = "fast",
        asr_config: dict[str, Any] | None = None,
    ) -> str:
        return self._hash_payload(
            {
                "audio": self._file_signature(audio_path),
                "whisper_model": str(whisper_model or "").strip(),
                "source_language": str(source_language or "auto").strip().lower(),
                "audio_handling_mode": str(audio_handling_mode or "fast").strip().lower(),
                "asr_config": dict(asr_config or {}),
            }
        )
