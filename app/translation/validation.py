from __future__ import annotations

import re


_PROTECTED_TOKEN = re.compile(
    r"(?<!\w)(?:\d+(?:[.,:/-]\d+)*|[A-Z][A-Za-z0-9_.-]{1,}|[A-Za-z]+\d+[A-Za-z0-9_.-]*)(?!\w)"
)


def protected_tokens(text: str) -> list[str]:
    return list(dict.fromkeys(_PROTECTED_TOKEN.findall(str(text or ""))))


def protected_fact_flags(source_text: str, translated_text: str) -> list[str]:
    target = str(translated_text or "")
    flags = []
    for token in protected_tokens(source_text):
        if token not in target:
            category = "number" if any(char.isdigit() for char in token) else "name_or_product"
            flags.append(f"missing_{category}:{token}")
    return flags


def annotate_translation_issues(
    source_segments: list[dict], translated_segments: list[dict]
) -> list[dict]:
    if len(source_segments) != len(translated_segments):
        raise ValueError("Translated segment count does not match source segment count.")
    output = []
    for index, (source, translated) in enumerate(zip(source_segments, translated_segments), start=1):
        item = dict(translated or {})
        source_id = str((source or {}).get("id") or "").strip()
        translated_id = str(item.get("id") or "").strip()
        if source_id and translated_id and source_id != translated_id:
            raise ValueError(
                f"Translated cue ID mismatch at position {index}: expected {source_id!r}, got {translated_id!r}."
            )
        if source_id:
            item["id"] = source_id
        source_text = str(
            (source or {}).get("original_text")
            or (source or {}).get("source_text")
            or (source or {}).get("text")
            or ""
        )
        flags = list(item.get("qa_flags", []) or [])
        flags.extend(protected_fact_flags(source_text, str(item.get("text") or "")))
        item["qa_flags"] = list(dict.fromkeys(flags))
        output.append(item)
    return output
