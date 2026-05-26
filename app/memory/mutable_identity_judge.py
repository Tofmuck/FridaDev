from __future__ import annotations

from typing import Any

from memory import mutable_identity_judge_common as judge_common


SCHEMA_VERSION = 'mutable_judge_v1_removed'
MODEL_SLOT = judge_common.MODEL_SLOT
CALLER = judge_common.CALLER
WINDOW_PAIRS_COUNT = judge_common.WINDOW_PAIRS_COUNT
JUDGE_WINDOW_MAX_CHARS = judge_common.JUDGE_WINDOW_MAX_CHARS
JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT = judge_common.JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT
TECHNICAL_REASON_CODES = judge_common.TECHNICAL_REASON_CODES
LEGACY_STATUS = 'legacy_mutable_judge_v1_removed'


def runtime_model_settings() -> dict[str, Any]:
    """Compatibility accessor for operator checks; the active caller is v2."""
    return judge_common.runtime_model_settings()


def run_mutable_identity_judge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Disabled v1 shim kept so stale callers fail closed and content-free."""
    return {
        'status': 'skipped',
        'reason_code': LEGACY_STATUS,
        'schema_version': SCHEMA_VERSION,
        'active_schema_version': 'mutable_judge_v2',
        'writes_applied': False,
    }
