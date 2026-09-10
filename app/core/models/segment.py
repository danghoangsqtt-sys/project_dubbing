from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


SEGMENT_SCHEMA_VERSION = 2


class SegmentValidationError(ValueError):
    """Raised when a canonical segment violates an integrity invariant."""


def normalize_segment_id(value: Any, default_id: int | str = 0) -> str:
    """Return a stable string ID, generating one only when the input has none."""

    raw = "" if value is None else str(value).strip()
    if raw:
        return raw
    try:
        index = max(1, int(default_id))
        return f"seg-{index:06d}"
    except (TypeError, ValueError):
        fallback = str(default_id or "1").strip()
        return f"seg-{fallback}"


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


@dataclass
class Segment:
    id: str
    start: float
    end: float
    original_text: str = ""
    subtitle_vi: str = ""
    dubbing_vi: str = ""
    source_language: str = ""
    speaker_id: str = ""
    voice_profile_id: str = ""
    confidence: float | None = None
    qa_flags: list[str] = field(default_factory=list)
    provenance: dict[str, dict[str, Any]] = field(default_factory=dict)
    voice_file: str = ""
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SEGMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.id = normalize_segment_id(self.id)
        self.start = float(self.start or 0.0)
        self.end = float(self.end or 0.0)
        self.original_text = str(self.original_text or "")
        self.subtitle_vi = str(self.subtitle_vi or "")
        self.dubbing_vi = str(self.dubbing_vi or "")
        self.source_language = str(self.source_language or "").strip().lower()
        self.speaker_id = str(self.speaker_id or "").strip()
        self.voice_profile_id = str(self.voice_profile_id or "").strip()
        self.voice_file = str(self.voice_file or "")
        self.status = str(self.status or "pending")
        self.qa_flags = list(dict.fromkeys(str(flag) for flag in (self.qa_flags or []) if str(flag)))
        self.provenance = deepcopy(dict(self.provenance or {}))
        self.metadata = deepcopy(dict(self.metadata or {}))
        self.schema_version = SEGMENT_SCHEMA_VERSION
        if self.confidence is not None:
            try:
                self.confidence = float(self.confidence)
            except (TypeError, ValueError):
                self.confidence = None
                self._add_qa_flag("invalid_confidence")
        if self.start < 0 or self.end <= self.start:
            self._add_qa_flag("invalid_timing")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            self._add_qa_flag("invalid_confidence")

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_id: int | str = 0) -> "Segment":
        if not isinstance(data, dict):
            raise TypeError("Segment payload must be a dictionary")

        metadata = deepcopy(dict(data.get("metadata", {}) or {}))
        generic_text = str(data.get("text", "") or "").strip()
        explicit_original = _first_text(data.get("original_text"), data.get("source_text"))
        original_text = explicit_original or generic_text

        subtitle_vi = _first_text(
            data.get("subtitle_vi"),
            data.get("final_text"),
            data.get("refined_translation"),
            data.get("raw_translation"),
        )
        if not subtitle_vi and explicit_original and generic_text != explicit_original:
            subtitle_vi = generic_text
        dubbing_vi = _first_text(data.get("dubbing_vi"), data.get("tts_text"))

        speaker_id = _first_text(
            data.get("speaker_id"), data.get("speaker"), metadata.get("speaker_id"), metadata.get("speaker")
        )
        voice_profile_id = _first_text(
            data.get("voice_profile_id"),
            data.get("voice_name"),
            metadata.get("voice_profile_id"),
            metadata.get("voice_name"),
        )
        if speaker_id:
            metadata.setdefault("speaker", speaker_id)
        if voice_profile_id:
            metadata.setdefault("voice_name", voice_profile_id)

        for key in (
            "words",
            "manual_highlights",
            "auto_highlights",
            "tts_group_id",
            "tts_group_start",
            "tts_group_end",
            "voice_edited",
        ):
            if key in data and key not in metadata:
                metadata[key] = deepcopy(data.get(key))
        raw_audio_end = data.get("_audio_end")
        if raw_audio_end is not None and "_audio_end" not in metadata:
            try:
                metadata["_audio_end"] = float(raw_audio_end)
            except (TypeError, ValueError):
                pass
        if data.get("refined_translation") or data.get("polished"):
            metadata["translation_refined"] = True

        provenance = deepcopy(dict(data.get("provenance", {}) or {}))
        legacy_provider = str(data.get("provider", "") or "").strip()
        if legacy_provider and "translation" not in provenance:
            provenance["translation"] = {"provider": legacy_provider}

        known_keys = {
            "schema_version", "id", "start", "end", "source_language", "original_text",
            "source_text", "subtitle_vi", "dubbing_vi", "raw_translation",
            "refined_translation", "final_text", "tts_text", "speaker_id", "speaker",
            "voice_profile_id", "voice_name", "confidence", "qa_flags", "provenance",
            "voice_file", "status", "metadata", "text", "provider", "polished", "words",
            "manual_highlights", "auto_highlights", "tts_group_id", "tts_group_start",
            "tts_group_end", "voice_edited", "_audio_end",
        }
        legacy_fields = {key: deepcopy(value) for key, value in data.items() if key not in known_keys}
        if legacy_fields:
            preserved = dict(metadata.get("legacy_fields", {}) or {})
            preserved.update(legacy_fields)
            metadata["legacy_fields"] = preserved

        return cls(
            id=normalize_segment_id(data.get("id"), default_id),
            start=float(data.get("start", 0.0) or 0.0),
            end=float(data.get("end", 0.0) or 0.0),
            original_text=original_text,
            subtitle_vi=subtitle_vi,
            dubbing_vi=dubbing_vi,
            source_language=str(data.get("source_language", "") or ""),
            speaker_id=speaker_id,
            voice_profile_id=voice_profile_id,
            confidence=data.get("confidence", metadata.get("confidence")),
            qa_flags=list(data.get("qa_flags", metadata.get("qa_flags", [])) or []),
            provenance=provenance,
            voice_file=str(data.get("voice_file", "") or ""),
            status=str(data.get("status", "pending") or "pending"),
            metadata=metadata,
        )

    @classmethod
    def from_transcript_dict(cls, data: dict[str, Any], segment_id: int | str) -> "Segment":
        payload = dict(data or {})
        payload.setdefault("id", normalize_segment_id(payload.get("id"), segment_id))
        payload.setdefault("original_text", payload.get("text", ""))
        payload.setdefault("status", "transcribed")
        return cls.from_dict(payload, default_id=segment_id)

    def validate(self) -> None:
        if not self.id:
            raise SegmentValidationError("Segment ID must not be empty")
        if self.start < 0 or self.end <= self.start:
            raise SegmentValidationError(
                f"Segment {self.id!r} has invalid timing: start={self.start}, end={self.end}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise SegmentValidationError(
                f"Segment {self.id!r} has confidence outside 0..1: {self.confidence}"
            )

    def apply_translation(self, translated_text: str, *, refined: bool = False) -> None:
        self.subtitle_vi = str(translated_text or "").strip()
        self.metadata["translation_refined"] = bool(refined)
        self.status = "translated"

    def apply_dubbing(self, spoken_text: str) -> None:
        self.dubbing_vi = str(spoken_text or "").strip()
        self.metadata["voice_edited"] = bool(self.dubbing_vi)

    def set_provenance(self, stage: str, record: dict[str, Any]) -> None:
        stage_id = str(stage or "").strip()
        if not stage_id:
            raise ValueError("Provenance stage must not be empty")
        self.provenance[stage_id] = deepcopy(dict(record or {}))

    def _add_qa_flag(self, flag: str) -> None:
        if flag and flag not in self.qa_flags:
            self.qa_flags.append(flag)

    @property
    def raw_translation(self) -> str:
        return self.subtitle_vi

    @raw_translation.setter
    def raw_translation(self, value: str) -> None:
        self.subtitle_vi = str(value or "")

    @property
    def refined_translation(self) -> str:
        return self.subtitle_vi if self.metadata.get("translation_refined") else ""

    @refined_translation.setter
    def refined_translation(self, value: str) -> None:
        self.subtitle_vi = str(value or "")
        self.metadata["translation_refined"] = bool(self.subtitle_vi)

    @property
    def final_text(self) -> str:
        return self.subtitle_vi

    @final_text.setter
    def final_text(self, value: str) -> None:
        self.subtitle_vi = str(value or "")

    @property
    def tts_text(self) -> str:
        return self.dubbing_vi

    @tts_text.setter
    def tts_text(self, value: str) -> None:
        self.dubbing_vi = str(value or "")

    @property
    def subtitle_text(self) -> str:
        return self.subtitle_vi or self.original_text

    @property
    def tts_source_text(self) -> str:
        return self.dubbing_vi or self.subtitle_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SEGMENT_SCHEMA_VERSION,
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "source_language": self.source_language,
            "original_text": self.original_text,
            "subtitle_vi": self.subtitle_vi,
            "dubbing_vi": self.dubbing_vi,
            "speaker_id": self.speaker_id,
            "voice_profile_id": self.voice_profile_id,
            "confidence": self.confidence,
            "qa_flags": list(self.qa_flags),
            "provenance": deepcopy(self.provenance),
            "voice_file": self.voice_file,
            "status": self.status,
            "metadata": deepcopy(self.metadata),
        }

    def to_subtitle_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.subtitle_text,
            "source_language": self.source_language,
            "source_text": self.original_text,
            "original_text": self.original_text,
            "subtitle_vi": self.subtitle_vi,
            "dubbing_vi": self.dubbing_vi,
            "tts_text": self.dubbing_vi,
            "speaker_id": self.speaker_id,
            "voice_profile_id": self.voice_profile_id,
            "confidence": self.confidence,
            "qa_flags": list(self.qa_flags),
            "provenance": deepcopy(self.provenance),
        }
        if self.speaker_id:
            payload["speaker"] = self.speaker_id
        if self.voice_profile_id:
            payload["voice_name"] = self.voice_profile_id
        for key in (
            "tts_group_id", "tts_group_start", "tts_group_end", "words",
            "manual_highlights", "auto_highlights", "voice_edited",
        ):
            if key in self.metadata:
                payload[key] = deepcopy(self.metadata.get(key))
        if "_audio_end" in self.metadata:
            try:
                payload["_audio_end"] = float(self.metadata["_audio_end"])
            except (TypeError, ValueError):
                pass
        translation_provenance = self.provenance.get("translation", {})
        if translation_provenance.get("provider"):
            payload["provider"] = str(translation_provenance["provider"])
        if self.metadata.get("translation_refined"):
            payload["polished"] = True
        return payload

    def to_original_subtitle_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.original_text,
            "original_text": self.original_text,
            "source_language": self.source_language,
            "confidence": self.confidence,
            "qa_flags": list(self.qa_flags),
            "provenance": deepcopy(self.provenance),
        }
        if self.metadata.get("words"):
            payload["words"] = deepcopy(self.metadata.get("words"))
        if self.speaker_id:
            payload["speaker"] = self.speaker_id
            payload["speaker_id"] = self.speaker_id
        return payload


def coerce_segments(segments: list[Any]) -> list[Segment]:
    normalized: list[Segment] = []
    for idx, segment in enumerate(segments or [], start=1):
        if isinstance(segment, Segment):
            normalized.append(segment)
        elif isinstance(segment, dict):
            normalized.append(Segment.from_dict(segment, default_id=idx))
        else:
            raise TypeError(f"Unsupported segment type: {type(segment)!r}")
    return normalized


def validate_segments(segments: list[Any]) -> list[Segment]:
    normalized = coerce_segments(segments)
    seen: set[str] = set()
    for segment in normalized:
        segment.validate()
        if segment.id in seen:
            raise SegmentValidationError(f"Duplicate segment ID: {segment.id!r}")
        seen.add(segment.id)
    return normalized


def segments_to_dicts(segments: list[Any]) -> list[dict[str, Any]]:
    return [segment.to_dict() for segment in validate_segments(segments)]
