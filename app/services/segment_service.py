from __future__ import annotations

from typing import Any

from core.models import Segment, normalize_segment_id, validate_segments


class SegmentMappingError(ValueError):
    """Raised when a transformation loses, duplicates, or reorders stable cue IDs."""


class SegmentService:
    def transcript_dicts_to_models(
        self,
        raw_segments: list[dict[str, Any]],
        *,
        source_language: str = "",
        asr_provenance: dict[str, Any] | None = None,
    ) -> list[Segment]:
        models = [
            self._transcript_to_model(
                raw_segment,
                segment_id=index,
                source_language=source_language,
                asr_provenance=asr_provenance,
            )
            for index, raw_segment in enumerate(raw_segments or [], start=1)
        ]
        return validate_segments(models)

    @staticmethod
    def _transcript_to_model(
        raw_segment: dict[str, Any],
        *,
        segment_id: int,
        source_language: str,
        asr_provenance: dict[str, Any] | None,
    ) -> Segment:
        payload = dict(raw_segment or {})
        payload.setdefault("source_language", source_language)
        provenance = dict(payload.get("provenance", {}) or {})
        record = dict(payload.pop("asr_provenance", {}) or asr_provenance or {})
        if record:
            provenance["asr"] = record
        payload["provenance"] = provenance
        return Segment.from_transcript_dict(payload, segment_id=segment_id)

    def segment_dicts_to_models(
        self, segments: list[dict[str, Any]], *, translated: bool = False
    ) -> list[Segment]:
        models: list[Segment] = []
        for idx, seg in enumerate(segments or [], start=1):
            model = Segment.from_dict(seg, default_id=idx)
            if translated:
                translated_text = seg.get("subtitle_vi", seg.get("text", ""))
                model.apply_translation(translated_text, refined=bool(seg.get("polished")))
                if "words" in seg:
                    model.metadata["words"] = list(seg.get("words") or [])
                if "manual_highlights" in seg:
                    model.metadata["manual_highlights"] = list(seg.get("manual_highlights") or [])
                if "auto_highlights" in seg:
                    model.metadata["auto_highlights"] = list(seg.get("auto_highlights") or [])
            elif not model.original_text:
                model.original_text = str(seg.get("text", "") or "")
                model.status = "transcribed"
            models.append(model)
        return validate_segments(models)

    def apply_translations(
        self,
        base_models: list[Segment | dict[str, Any]],
        translated_segments: list[dict[str, Any]],
    ) -> list[Segment]:
        models: list[Segment] = []
        base_models = validate_segments(list(base_models or []))
        translated_segments = list(translated_segments or [])
        explicit_id_flags = [
            isinstance(segment, dict) and segment.get("id") not in (None, "")
            for segment in translated_segments
        ]
        if any(explicit_id_flags) and not all(explicit_id_flags):
            raise SegmentMappingError("Translated segments contain a partial ID mapping")
        if explicit_id_flags and all(explicit_id_flags):
            translated_ids = [
                normalize_segment_id(segment.get("id")) for segment in translated_segments
            ]
            if len(set(translated_ids)) != len(translated_ids):
                raise SegmentMappingError("Translated segments contain duplicate IDs")
            base_ids = [segment.id for segment in base_models]
            if translated_ids != base_ids:
                raise SegmentMappingError(
                    "Translated segment IDs/count/order do not match source segments"
                )
        # An imported/edited SRT can add or remove cues.  Positional matching
        # is only safe while both lists have the same shape; otherwise use
        # the preserved cue timing to keep source text, speaker IDs, and
        # word metadata attached to the correct translated cue.
        base_by_timing = {}
        if len(base_models) != len(translated_segments):
            for base_model in base_models:
                key = (
                    round(float(getattr(base_model, "start", 0.0) or 0.0), 3),
                    round(float(getattr(base_model, "end", 0.0) or 0.0), 3),
                )
                base_by_timing.setdefault(key, []).append(base_model)
        base_by_id = {segment.id: segment for segment in base_models}
        for idx, seg in enumerate(translated_segments, start=1):
            model = Segment.from_dict(seg, default_id=idx)
            base_model = base_by_id.get(model.id) if all(explicit_id_flags) else None
            if (
                base_model is None
                and len(base_models) == len(translated_segments)
                and idx - 1 < len(base_models)
            ):
                base_model = base_models[idx - 1]
            elif base_by_timing:
                key = (
                    round(float((seg or {}).get("start", 0.0) or 0.0), 3),
                    round(float((seg or {}).get("end", 0.0) or 0.0), 3),
                )
                candidates = base_by_timing.get(key) or []
                if candidates:
                    base_model = candidates.pop(0)
            if base_model is not None:
                if not all(explicit_id_flags):
                    model.id = base_model.id
                # Segment.from_dict treats its generic ``text`` field as an
                # original-text fallback. For translations that field is the
                # translated cue, so only an explicitly retained original
                # should win over the source model.
                explicit_original = str(
                    (seg or {}).get("original_text") or (seg or {}).get("source_text") or ""
                ).strip()
                if not explicit_original:
                    model.original_text = base_model.original_text
                if not model.source_language:
                    model.source_language = base_model.source_language
                if not model.dubbing_vi:
                    model.dubbing_vi = base_model.dubbing_vi
                if not model.speaker_id:
                    model.speaker_id = base_model.speaker_id
                if not model.voice_profile_id:
                    model.voice_profile_id = base_model.voice_profile_id
                if model.confidence is None:
                    model.confidence = base_model.confidence
                model.provenance = {**base_model.provenance, **model.provenance}
                model.qa_flags = list(dict.fromkeys([*base_model.qa_flags, *model.qa_flags]))
                source_words = base_model.metadata.get("words")
                if source_words and "words" not in seg:
                    model.metadata["words"] = list(source_words)
                source_speaker = str(base_model.metadata.get("speaker", "") or "").strip()
                if source_speaker and "speaker" not in seg:
                    model.metadata["speaker"] = source_speaker
                source_highlights = base_model.metadata.get("manual_highlights")
                if source_highlights and "manual_highlights" not in seg:
                    model.metadata["manual_highlights"] = list(source_highlights)
                source_auto_highlights = base_model.metadata.get("auto_highlights")
                if source_auto_highlights and "auto_highlights" not in seg:
                    model.metadata["auto_highlights"] = list(source_auto_highlights)
            translated_text = seg.get("subtitle_vi", seg.get("text", ""))
            model.apply_translation(translated_text, refined=bool(seg.get("polished")))
            provider = str(seg.get("provider", "") or "").strip()
            model.metadata["translation_provider"] = provider
            if provider:
                translation_provenance = dict(model.provenance.get("translation", {}) or {})
                translation_provenance["provider"] = provider
                model.set_provenance("translation", translation_provenance)
            model.metadata["source_text"] = seg.get("source_text", "")
            if "words" in seg:
                model.metadata["words"] = list(seg.get("words") or [])
            if "manual_highlights" in seg:
                model.metadata["manual_highlights"] = list(seg.get("manual_highlights") or [])
            if "auto_highlights" in seg:
                model.metadata["auto_highlights"] = list(seg.get("auto_highlights") or [])
            for key in ("tts_group_id", "tts_group_start", "tts_group_end"):
                if key in seg:
                    model.metadata[key] = seg.get(key)
            models.append(model)
        return validate_segments(models)
