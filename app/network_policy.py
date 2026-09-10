from __future__ import annotations

import os
from urllib.parse import urlparse


class OfflineLockError(RuntimeError):
    """Raised before a request can leave the local computer."""


def offline_lock_enabled() -> bool:
    value = str(os.getenv("CAPCAP_OFFLINE_LOCK", "0") or "0").strip().lower()
    return value in {"1", "true", "yes", "on", "enabled"}


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    hostname = str(parsed.hostname or "").strip().lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def assert_network_allowed(url: str, *, purpose: str = "provider request") -> None:
    if offline_lock_enabled() and not is_loopback_url(url):
        raise OfflineLockError(
            f"Offline Lock blocked {purpose} to {url}. Select local Ollama or disable Offline Lock."
        )
