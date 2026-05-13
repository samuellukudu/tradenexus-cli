"""
tradenexus/utils.py

Shared utility helpers — port of extractJsonFromText() and other small
helpers from geminiService.ts.
"""

from __future__ import annotations
import json
import re


def extract_json_from_text(text: str | None) -> object | None:
    """
    Port of extractJsonFromText() from geminiService.ts.
    Tries multiple strategies to parse JSON out of a model response.
    """
    if not text:
        return None

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Markdown code block
    code_block = re.search(r"```(?:json)?\s*\n?([\s\S]*?)```", text)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. First JSON object
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. First JSON array
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def normalize_confidence(raw) -> int:
    """Convert any confidence value (0-1 float or 0-100 int) to a 0-100 int."""
    if not isinstance(raw, (int, float)):
        return 85
    if 0 < raw <= 1:
        return round(raw * 100)
    return round(raw)


def extract_grounding_urls(response) -> list[str]:
    """Pull web URIs out of a Gemini grounding metadata object."""
    urls: list[str] = []
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        for chunk in chunks:
            if hasattr(chunk, "web") and chunk.web and chunk.web.uri:
                urls.append(chunk.web.uri)
    except (AttributeError, IndexError, TypeError):
        pass
    return urls


def extract_grounding_sources(response) -> list[dict]:
    """Return list of {title, url} dicts from grounding metadata."""
    sources: list[dict] = []
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        for chunk in chunks:
            if hasattr(chunk, "web") and chunk.web and chunk.web.uri:
                sources.append({"title": chunk.web.title or "Web Source", "url": chunk.web.uri})
    except (AttributeError, IndexError, TypeError):
        pass
    seen: set[str] = set()
    unique: list[dict] = []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)
    return unique
