from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Any


DEFAULT_VERSION = "continuity_capsule_v1"
DEFAULT_MAX_CHARS = 900

ENV_ENABLED = "FRIDA_CONTINUITY_CAPSULE_ENABLED"
ENV_TEXT = "FRIDA_CONTINUITY_CAPSULE_TEXT"
ENV_VERSION = "FRIDA_CONTINUITY_CAPSULE_VERSION"
ENV_MAX_CHARS = "FRIDA_CONTINUITY_CAPSULE_MAX_CHARS"

STATUS_OK = "ok"
STATUS_DISABLED = "disabled"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_NOT_SELECTED = "not_selected"
STATUS_REFUSED = "refused"

REASON_READY = "continuity_capsule_ready"
REASON_DISABLED = "continuity_capsule_disabled"
REASON_MISSING = "continuity_capsule_missing"
REASON_TOO_LARGE = "continuity_capsule_too_large"
REASON_FINAL_LOCK_BYPASS = "continuity_capsule_final_lock_bypass"
REASON_UNSAFE_CONTENT = "continuity_capsule_unsafe_content"

LOGICAL_ROLE = "continuity_capsule"
ORIGIN = "core.continuity_capsule"
ORIGIN_STAGE = "late_continuity_capsule"
CONTENT_KIND = "continuity_capsule"

_MAX_NONEMPTY_LINES = 8
_LONG_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_ABSOLUTE_PATH_ANYWHERE_RE = re.compile(r"(^|\s)[A-Za-z]:[\\/]")
_PRIVATE_PATH_RE = re.compile(
    r"(^|\s)(/(?:users|home|root|opt|var|etc|srv|tmp|mnt)/|~[\\/]|\\\\)",
    re.IGNORECASE,
)
_CREDENTIAL_SEPARATOR_RE = re.compile(
    r"\b(?:token|secret|password|api[_-]?key|x-api-key|authorization|cookie|set-cookie)\s*[:=]",
    re.IGNORECASE,
)
_WWW_RE = re.compile(r"\bwww\.", re.IGNORECASE)
_UNSAFE_MARKERS = (
    "://",
    "authorization",
    "bearer",
    "cookie",
    "set-cookie",
    "token=",
    "api_key=",
    "api-key=",
    "x-api-key",
    "password=",
    "secret=",
    "base64,",
    "<?xml",
    "dav:",
    "caldav",
    "webdav",
    "begin private key",
    "begin openssh private key",
    "begin rsa private key",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _config_value(config_module: Any, name: str, env_name: str, default: Any) -> Any:
    if config_module is not None and hasattr(config_module, name):
        return getattr(config_module, name)
    return os.environ.get(env_name, default)


def _bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "on", "enabled", "active"}


def _int_value(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _safe_version(value: Any) -> str:
    version = _text(value) or DEFAULT_VERSION
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if len(version) > 80 or not all(char in allowed for char in version):
        return DEFAULT_VERSION
    return version


def _unsafe_content_reason(value: str) -> str:
    text = str(value or "")
    stripped = text.strip()
    lower = stripped.lower()
    if not stripped:
        return ""
    if lower.startswith(("http:", "https:", "www.", "data:")):
        return "unsafe_marker"
    if _WWW_RE.search(stripped):
        return "unsafe_marker"
    if _CREDENTIAL_SEPARATOR_RE.search(stripped):
        return "unsafe_marker"
    if any(marker in lower for marker in _UNSAFE_MARKERS):
        return "unsafe_marker"
    if "</" in lower or "xml:" in lower:
        return "unsafe_marker"
    if "\x00" in text or "\r" in text:
        return "structured_payload"
    nonempty_lines = [line for line in text.splitlines() if line.strip()]
    if len(nonempty_lines) > _MAX_NONEMPTY_LINES:
        return "structured_payload"
    compact = "".join(line.strip() for line in nonempty_lines)
    if _LONG_BASE64_RE.fullmatch(compact):
        return "encoded_payload"
    if _PRIVATE_PATH_RE.search(stripped):
        return "private_path"
    if _WINDOWS_ABSOLUTE_PATH_ANYWHERE_RE.search(stripped):
        return "private_path"
    for line in nonempty_lines or [stripped]:
        line_text = line.strip()
        if (
            line_text.startswith(("/", "~", "\\\\"))
            or _WINDOWS_ABSOLUTE_PATH_RE.match(line_text)
        ):
            return "private_path"
    return ""


def is_unsafe_capsule_content(value: str) -> bool:
    return bool(_unsafe_content_reason(value))


@dataclass(frozen=True, repr=False)
class ContinuityCapsuleResult:
    enabled: bool
    status: str
    reason_code: str
    version: str = DEFAULT_VERSION
    present: bool = False
    content_chars: int = 0
    max_chars: int = DEFAULT_MAX_CHARS
    injected_count: int = 0
    content: str = field(default="", repr=False, compare=False)

    @property
    def should_inject(self) -> bool:
        return bool(
            self.enabled
            and self.present
            and self.status == STATUS_OK
            and self.injected_count == 1
            and self.content
        )

    def as_content_free_dict(self) -> dict[str, Any]:
        return {
            "present": bool(self.present),
            "enabled": bool(self.enabled),
            "version": _safe_version(self.version),
            "status": _text(self.status),
            "reason_code": _text(self.reason_code),
            "content_chars": int(self.content_chars),
            "max_chars": int(self.max_chars),
            "injected_count": int(self.injected_count),
            "raw_content_included": False,
            "raw_prompt_included": False,
            "raw_capsule_content_included": False,
            "fingerprint_included": False,
        }


def resolve_continuity_capsule(
    *,
    config_module: Any = None,
    final_response_lock_present: bool = False,
    enabled: Any = None,
    content: Any = None,
    version: Any = None,
    max_chars: Any = None,
) -> ContinuityCapsuleResult:
    resolved_enabled = _bool_value(
        enabled if enabled is not None else _config_value(config_module, "CONTINUITY_CAPSULE_ENABLED", ENV_ENABLED, False),
        default=False,
    )
    resolved_version = _safe_version(
        version if version is not None else _config_value(config_module, "CONTINUITY_CAPSULE_VERSION", ENV_VERSION, DEFAULT_VERSION)
    )
    resolved_max_chars = _int_value(
        max_chars if max_chars is not None else _config_value(config_module, "CONTINUITY_CAPSULE_MAX_CHARS", ENV_MAX_CHARS, DEFAULT_MAX_CHARS),
        DEFAULT_MAX_CHARS,
    )

    if not resolved_enabled:
        return ContinuityCapsuleResult(
            enabled=False,
            status=STATUS_DISABLED,
            reason_code=REASON_DISABLED,
            version=resolved_version,
            max_chars=resolved_max_chars,
        )

    resolved_content = _text(
        content if content is not None else _config_value(config_module, "CONTINUITY_CAPSULE_TEXT", ENV_TEXT, "")
    )
    content_chars = len(resolved_content)
    if not resolved_content:
        return ContinuityCapsuleResult(
            enabled=True,
            status=STATUS_NOT_CONFIGURED,
            reason_code=REASON_MISSING,
            version=resolved_version,
            present=False,
            max_chars=resolved_max_chars,
        )
    if content_chars > resolved_max_chars:
        return ContinuityCapsuleResult(
            enabled=True,
            status=STATUS_REFUSED,
            reason_code=REASON_TOO_LARGE,
            version=resolved_version,
            present=True,
            content_chars=content_chars,
            max_chars=resolved_max_chars,
        )
    if final_response_lock_present:
        return ContinuityCapsuleResult(
            enabled=True,
            status=STATUS_NOT_SELECTED,
            reason_code=REASON_FINAL_LOCK_BYPASS,
            version=resolved_version,
            present=True,
            content_chars=content_chars,
            max_chars=resolved_max_chars,
        )
    if _unsafe_content_reason(resolved_content):
        return ContinuityCapsuleResult(
            enabled=True,
            status=STATUS_REFUSED,
            reason_code=REASON_UNSAFE_CONTENT,
            version=resolved_version,
            present=True,
            content_chars=content_chars,
            max_chars=resolved_max_chars,
        )
    return ContinuityCapsuleResult(
        enabled=True,
        status=STATUS_OK,
        reason_code=REASON_READY,
        version=resolved_version,
        present=True,
        content_chars=content_chars,
        max_chars=resolved_max_chars,
        injected_count=1,
        content=resolved_content,
    )


def build_capsule_message(result: ContinuityCapsuleResult) -> dict[str, str] | None:
    if not result.should_inject:
        return None
    content = "\n".join(
        (
            "[CONTINUITY CAPSULE]",
            f"Version: {result.version}",
            "Statut: non souveraine, contestable, desactivable.",
            "Priorite: le tour courant, les preuves injectees, les final locks et les guards produit priment.",
            "",
            result.content,
        )
    )
    return {"role": "system", "content": content}


def inject_continuity_capsule(
    prompt_messages: list[dict[str, Any]],
    result: ContinuityCapsuleResult,
) -> bool:
    message = build_capsule_message(result)
    if message is None:
        return False
    prompt_messages.append(message)
    return True
