from __future__ import annotations

"""Structured content-free refs for Exports V1 projections."""

import hashlib
import re
from typing import Any


SOURCE_REF_PREFIXES = frozenset(
    {
        "workspace-note",
        "workspace-file",
        "workspace-export",
        "conversation",
        "message-selection",
        "frida-response",
    }
)

_SOURCE_REF_RE = re.compile(
    r"^(?:workspace-note|workspace-file|workspace-export|conversation|"
    r"message-selection|frida-response):(?:[0-9a-f]{8}|redacted):[0-9a-f]{12}$"
)


def safe_source_ref(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text if _SOURCE_REF_RE.fullmatch(text) else ""


def hash12(value: Any) -> str:
    text = str(value or "")
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def build_source_ref(prefix: str, value: Any) -> str:
    if prefix not in SOURCE_REF_PREFIXES:
        return ""
    raw = " ".join(str(value or "").strip().split())
    short = _uuid_short(raw) or "redacted"
    return f"{prefix}:{short}:{hash12(raw or prefix)}"


def _uuid_short(value: str) -> str:
    match = re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        value,
    )
    return value[:8].lower() if match else ""
