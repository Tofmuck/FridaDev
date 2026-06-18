from __future__ import annotations

"""Structured content-free refs for Exports V1 projections."""

import re
from typing import Any


_SOURCE_REF_RE = re.compile(
    r"^(?:workspace-note|workspace-file|workspace-export|conversation|"
    r"message-selection|frida-response):(?:[0-9a-f]{8}|redacted):[0-9a-f]{12}$"
)


def safe_source_ref(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text if _SOURCE_REF_RE.fullmatch(text) else ""
