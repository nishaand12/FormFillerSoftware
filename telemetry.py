"""Lightweight local telemetry logger."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from app_paths import get_log_path


TELEMETRY_VERSION = 1


def _telemetry_file() -> Path:
    return get_log_path("telemetry.jsonl")


def log_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Append a telemetry event to the local JSONL log."""
    record = {
        "timestamp": time.time(),
        "event": event_type,
        "version": TELEMETRY_VERSION,
        "payload": payload,
    }

    try:
        path = _telemetry_file()
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Telemetry should never break the app; swallow errors.
        pass

