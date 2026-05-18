"""Process-wide settings for cache and HTTP pacing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunConfig:
    cache_enabled: bool = True
    cache_dir: Path = Path(os.environ.get("TRADE_INTEL_CACHE", ".trade_intel_cache"))
    cache_ttl_seconds: int = int(os.environ.get("TRADE_INTEL_CACHE_TTL", "86400"))
    min_request_interval: float = float(os.environ.get("TRADE_INTEL_MIN_INTERVAL", "0.35"))


_CONFIG = RunConfig()


def get_config() -> RunConfig:
    return _CONFIG


def set_config(cfg: RunConfig) -> None:
    global _CONFIG
    _CONFIG = cfg
