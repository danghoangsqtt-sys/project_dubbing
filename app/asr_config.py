from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ASR_CONFIG_SCHEMA_VERSION = 1
SUPPORTED_SOURCE_LANGUAGES = frozenset({"zh", "en"})


def normalize_source_language(language: str) -> str:
    """Return a milestone-supported source language or fail visibly."""

    normalized = str(language or "").strip().lower()
    aliases = {
        "chinese": "zh",
        "chinese (simplified)": "zh",
        "mandarin": "zh",
        "english": "en",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_SOURCE_LANGUAGES:
        raise ValueError(
            "Faster-Whisper requires an explicit source language for this project: "
            "choose Chinese (zh) or English (en); automatic detection is disabled."
        )
    return normalized


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def resolve_model_revision(resolved_model: str) -> str:
    """Create a stable revision label without hashing multi-gigabyte weights."""

    raw = str(resolved_model or "").strip()
    configured = str(os.getenv("CAPCAP_WHISPER_REVISION", "") or "").strip()
    if configured:
        return configured
    path = Path(raw)
    if path.is_dir():
        parts = list(path.parts)
        if "snapshots" in parts:
            index = parts.index("snapshots")
            if index + 1 < len(parts):
                return parts[index + 1]
        for name in (".capcap-resource.json", "resource-manifest.json"):
            manifest_path = path / name
            if not manifest_path.is_file():
                continue
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                revision = str(
                    payload.get("revision")
                    or payload.get("commit")
                    or payload.get("sha256")
                    or ""
                ).strip()
                if revision:
                    return revision
            except (OSError, ValueError, TypeError):
                pass
        model_bin = path / "model.bin"
        if model_bin.is_file():
            stat = model_bin.stat()
            identity = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
            digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            return f"local-{digest}"
        return f"local-dir-{path.name}"
    # Named models are resolved through the local Hugging Face cache before
    # inference. The explicit marker prevents cache reuse once a snapshot is
    # installed and its immutable commit directory becomes available.
    return "registry-main-unresolved"


@dataclass(frozen=True)
class FasterWhisperConfig:
    source_language: str
    requested_model: str
    resolved_model: str
    model_revision: str
    requested_device: str
    effective_device: str
    compute_type: str
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = True
    task: str = "transcribe"
    use_batched: bool = True
    batch_size: int = 0
    engine: str = "faster-whisper"
    faster_whisper_version: str = "not-installed"
    ctranslate2_version: str = "not-installed"
    schema_version: int = ASR_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_language", normalize_source_language(self.source_language))
        if self.task != "transcribe":
            raise ValueError("The locked ASR path only permits task='transcribe'.")
        if int(self.beam_size) < 1:
            raise ValueError("Faster-Whisper beam_size must be at least 1.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_faster_whisper_config(
    *,
    language: str,
    requested_model: str,
    resolved_model: str,
    requested_device: str,
    effective_device: str,
    compute_type: str,
    use_batched: bool = True,
    batch_size: int = 0,
) -> FasterWhisperConfig:
    return FasterWhisperConfig(
        source_language=normalize_source_language(language),
        requested_model=str(requested_model or "").strip(),
        resolved_model=str(resolved_model or "").strip(),
        model_revision=resolve_model_revision(resolved_model),
        requested_device=str(requested_device or "auto").strip().lower(),
        effective_device=str(effective_device or "cpu").strip().lower(),
        compute_type=str(compute_type or "int8").strip().lower(),
        use_batched=bool(use_batched),
        batch_size=max(0, int(batch_size or 0)),
        faster_whisper_version=_package_version("faster-whisper"),
        ctranslate2_version=_package_version("ctranslate2"),
    )
