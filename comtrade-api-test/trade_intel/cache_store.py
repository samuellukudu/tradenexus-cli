"""Disk cache with TTL (JSON for structured payloads)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from trade_intel.config import get_config


def _key_path(cache_dir: Path, key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return cache_dir / f"{h}.json"


def cache_get(key: str) -> Any | None:
    cfg = get_config()
    if not cfg.cache_enabled:
        return None
    path = _key_path(cfg.cache_dir, key)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - raw.get("_cached_at", 0) > cfg.cache_ttl_seconds:
            path.unlink(missing_ok=True)
            return None
        return raw.get("data")
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def cache_set(key: str, data: Any) -> None:
    cfg = get_config()
    if not cfg.cache_enabled:
        return
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    path = _key_path(cfg.cache_dir, key)
    payload = {"_cached_at": time.time(), "data": data}
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def make_key(prefix: str, **parts: Any) -> str:
    items = [prefix] + [f"{k}={parts[k]}" for k in sorted(parts)]
    return "|".join(str(x) for x in items)
