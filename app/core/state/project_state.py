from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.models import Segment, validate_segments


PROJECT_SCHEMA_VERSION = 2

DEFAULT_STEP_STATUSES = {
    "extract_audio": "pending",
    "transcribe": "pending",
    "translate_raw": "pending",
    "refine_translation": "pending",
    "separate_audio": "pending",
    "generate_tts": "pending",
    "build_subtitle": "pending",
    "mix_audio": "pending",
    "export": "pending",
}


class ProjectMigrationError(ValueError):
    """Raised when project state cannot be migrated without risking data loss."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _schema_version(data: dict[str, Any]) -> int:
    raw = data.get("schema_version", 1)
    try:
        version = int(raw or 1)
    except (TypeError, ValueError) as exc:
        raise ProjectMigrationError(f"Invalid project schema_version: {raw!r}") from exc
    if version < 1:
        raise ProjectMigrationError(f"Invalid project schema_version: {version}")
    if version > PROJECT_SCHEMA_VERSION:
        raise ProjectMigrationError(
            f"Project schema {version} is newer than supported schema {PROJECT_SCHEMA_VERSION}"
        )
    return version


def _legacy_provenance(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    provenance: dict[str, dict[str, Any]] = {}
    for key, value in settings.items():
        if not key.endswith("_signature") or not str(value or "").strip():
            continue
        stage = key[: -len("_signature")]
        provenance[stage] = {"input_signature": str(value).strip(), "migrated": True}
    return provenance


def _segment_payload(data: dict[str, Any]) -> list[dict[str, Any]]:
    canonical = data.get("segments")
    if canonical is not None:
        if not isinstance(canonical, list):
            raise ProjectMigrationError("Project segments must be a list")
        return [deepcopy(item) for item in canonical]

    originals = data.get("current_segments") or []
    translations = data.get("current_translated_segments") or []
    if not isinstance(originals, list) or not isinstance(translations, list):
        raise ProjectMigrationError("Legacy project segment collections must be lists")
    if not translations:
        return [deepcopy(item) for item in originals]

    merged: list[dict[str, Any]] = []
    for index, translated in enumerate(translations):
        current = deepcopy(dict(translated or {}))
        source = dict(originals[index] or {}) if index < len(originals) else {}
        current.setdefault("id", source.get("id"))
        current.setdefault("start", source.get("start", 0.0))
        current.setdefault("end", source.get("end", 0.0))
        current.setdefault("original_text", source.get("original_text") or source.get("text", ""))
        current.setdefault("subtitle_vi", current.get("text", ""))
        merged.append(current)
    return merged


@dataclass
class ProjectState:
    project_id: str
    project_root: str
    input_video: str
    input_language: str = "auto"
    target_language: str = "vi"
    mode: str = "subtitle"
    translator_ai: bool = True
    translator_style: str = ""
    source_fingerprint: dict[str, Any] = field(default_factory=dict)
    segments: list[Segment] = field(default_factory=list)
    steps: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_STEP_STATUSES))
    settings: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, dict[str, Any]] = field(default_factory=dict)
    migration_history: list[dict[str, Any]] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    schema_version: int = PROJECT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.project_id = str(self.project_id or "")
        self.project_root = str(self.project_root or "")
        self.input_video = str(self.input_video or "")
        self.input_language = str(self.input_language or "auto").strip().lower()
        self.target_language = str(self.target_language or "vi").strip().lower()
        self.mode = str(self.mode or "subtitle")
        self.translator_style = str(self.translator_style or "")
        self.source_fingerprint = deepcopy(dict(self.source_fingerprint or {}))
        self.segments = validate_segments(list(self.segments or []))
        merged_steps = dict(DEFAULT_STEP_STATUSES)
        merged_steps.update(dict(self.steps or {}))
        self.steps = merged_steps
        self.settings = deepcopy(dict(self.settings or {}))
        self.artifacts = {str(key): str(value) for key, value in dict(self.artifacts or {}).items()}
        self.provenance = deepcopy(dict(self.provenance or {}))
        self.migration_history = deepcopy(list(self.migration_history or []))
        self.extensions = deepcopy(dict(self.extensions or {}))
        self.created_at = str(self.created_at or _utc_now_iso())
        self.updated_at = str(self.updated_at or self.created_at)
        self.schema_version = PROJECT_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectState":
        if not isinstance(data, dict):
            raise ProjectMigrationError("Project state payload must be a dictionary")
        source_version = _schema_version(data)
        settings = deepcopy(dict(data.get("settings", {}) or {}))
        provenance = deepcopy(dict(data.get("provenance", {}) or {}))
        for stage, record in _legacy_provenance(settings).items():
            provenance.setdefault(stage, record)

        segment_payload = _segment_payload(data)

        known_keys = {
            "schema_version", "project_id", "project_root", "input_video", "input_language",
            "target_language", "mode", "translator_ai", "translator_style",
            "source_fingerprint", "segments", "current_segments", "current_translated_segments",
            "steps", "settings", "artifacts", "provenance", "migration_history", "extensions",
            "created_at", "updated_at",
        }
        extensions = deepcopy(dict(data.get("extensions", {}) or {}))
        extensions.update({key: deepcopy(value) for key, value in data.items() if key not in known_keys})

        migration_history = deepcopy(list(data.get("migration_history", []) or []))
        if source_version < PROJECT_SCHEMA_VERSION:
            migration_history.append(
                {
                    "from": source_version,
                    "to": PROJECT_SCHEMA_VERSION,
                    "migrated_at": _utc_now_iso(),
                }
            )

        return cls(
            project_id=str(data.get("project_id", "")),
            project_root=str(data.get("project_root", "")),
            input_video=str(data.get("input_video", "")),
            input_language=str(data.get("input_language", "auto") or "auto"),
            target_language=str(data.get("target_language", "vi") or "vi"),
            mode=str(data.get("mode", "subtitle") or "subtitle"),
            translator_ai=bool(data.get("translator_ai", True)),
            translator_style=str(data.get("translator_style", "") or ""),
            source_fingerprint=deepcopy(dict(data.get("source_fingerprint", {}) or {})),
            segments=[Segment.from_dict(item, default_id=index) for index, item in enumerate(segment_payload, 1)],
            steps=deepcopy(dict(data.get("steps", {}) or {})),
            settings=settings,
            artifacts=deepcopy(dict(data.get("artifacts", {}) or {})),
            provenance=provenance,
            migration_history=migration_history,
            extensions=extensions,
            created_at=str(data.get("created_at") or _utc_now_iso()),
            updated_at=str(data.get("updated_at") or data.get("created_at") or _utc_now_iso()),
        )

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()

    def set_step_status(self, step_name: str, status: str) -> None:
        self.steps[str(step_name)] = str(status)
        self.touch()

    def set_artifact(self, name: str, path: str) -> None:
        self.artifacts[str(name)] = str(path)
        self.touch()

    def set_setting(self, name: str, value: Any) -> None:
        setting_name = str(name)
        self.settings[setting_name] = deepcopy(value)
        if setting_name.endswith("_signature") and str(value or "").strip():
            stage = setting_name[: -len("_signature")]
            record = dict(self.provenance.get(stage, {}) or {})
            record["input_signature"] = str(value).strip()
            self.provenance[stage] = record
        self.touch()

    def set_segments(self, segments: list[Segment | dict[str, Any]]) -> None:
        self.segments = validate_segments(list(segments or []))
        self.touch()

    def set_provenance(self, stage: str, record: dict[str, Any]) -> None:
        stage_id = str(stage or "").strip()
        if not stage_id:
            raise ValueError("Provenance stage must not be empty")
        self.provenance[stage_id] = deepcopy(dict(record or {}))
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        payload = deepcopy(self.extensions)
        payload.update(
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "project_id": self.project_id,
                "project_root": self.project_root,
                "input_video": self.input_video,
                "input_language": self.input_language,
                "target_language": self.target_language,
                "mode": self.mode,
                "translator_ai": self.translator_ai,
                "translator_style": self.translator_style,
                "source_fingerprint": deepcopy(self.source_fingerprint),
                "segments": [segment.to_dict() for segment in validate_segments(self.segments)],
                "steps": deepcopy(self.steps),
                "settings": deepcopy(self.settings),
                "artifacts": deepcopy(self.artifacts),
                "provenance": deepcopy(self.provenance),
                "migration_history": deepcopy(self.migration_history),
                "extensions": deepcopy(self.extensions),
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )
        return payload
