"""Minimum spacing between outbound HTTP calls (Comtrade + WITS)."""

from __future__ import annotations

import threading
import time

from trade_intel.config import get_config

_lock = threading.Lock()
_last: float = 0.0


def throttle() -> None:
    """Sleep if needed so consecutive calls are at least min_request_interval apart."""
    global _last
    cfg = get_config()
    if cfg.min_request_interval <= 0:
        return
    with _lock:
        now = time.monotonic()
        wait = cfg.min_request_interval - (now - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
