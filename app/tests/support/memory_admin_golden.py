from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from admin import admin_identity_read_model_service
from admin import runtime_settings
from memory import arbiter
from memory import memory_store


RAW_MEMORY_QUERY = "SYNTHETIC-MEMORY-QUERY-CONTENT"
RAW_TRACE_CONTENT = "SYNTHETIC-MEMORY-TRACE-CONTENT"
RAW_SUMMARY_CONTENT = "SYNTHETIC-MEMORY-SUMMARY-CONTENT"
RAW_LEGACY_IDENTITY = "SYNTHETIC-LEGACY-IDENTITY-CONTENT"
RAW_SETTINGS_SECRET = "SYNTHETIC-RUNTIME-SETTINGS-SECRET"
RAW_SETTINGS_CIPHERTEXT = "SYNTHETIC-RUNTIME-SETTINGS-CIPHERTEXT"
RAW_SENTINELS = (
    RAW_MEMORY_QUERY,
    RAW_TRACE_CONTENT,
    RAW_SUMMARY_CONTENT,
    RAW_LEGACY_IDENTITY,
    RAW_SETTINGS_SECRET,
    RAW_SETTINGS_CIPHERTEXT,
)


EXPECTED_MEMORY_ARBITER_MATRIX = {
    "public_roles": ("user",),
    "public_has_internal_scores": False,
    "internal_sources": (("summary", "summaries", "summary-1"), ("trace", "global", "trace-1")),
    "kept_candidate_ids": ("summary-1",),
    "decisions": (
        ("summary-1", True, "llm", "synthetic-memory-arbiter"),
        ("trace-1", False, "llm", "synthetic-memory-arbiter"),
    ),
}

EXPECTED_IDENTITY_MATRIX = {
    "status": 200,
    "ok": True,
    "read_model_version": "v2",
    "active_identity_source": "identity_mutables",
    "subjects": ("llm", "user"),
    "canonical_layers_present": ((True, True), (True, True)),
    "legacy_runtime_authority": ("historical_only", "historical_only"),
    "legacy_content_minimized": (True, True),
    "legacy_item_raw_keys_present": (False, False),
    "legacy_drives_active_injection": False,
}

EXPECTED_SETTINGS_MATRIX = {
    "read": {
        "fields": ("api_key", "model"),
        "secret_keys": ("is_secret", "is_set", "origin"),
        "secret_is_set": True,
        "secret_value_present": False,
    },
    "validation": {
        "section": "identity_governance",
        "valid": True,
        "source": "candidate",
        "source_reason": "validate_payload",
        "failed_checks": (),
    },
    "patch": {
        "fields": ("api_key", "model"),
        "origins": ("admin_ui", "admin_ui"),
        "secret_is_set": True,
        "plain_secret_present": False,
        "encrypted_secret_present": True,
    },
}


def exercise_memory_arbiter_matrix() -> dict[str, Any]:
    embedding_view = runtime_settings.RuntimeSectionView(
        section="embedding",
        payload=runtime_settings.normalize_stored_payload(
            "embedding",
            {
                "endpoint": {"value": "https://synthetic.invalid/embedding", "origin": "test"},
                "model": {"value": "synthetic-embedding", "origin": "test"},
                "token": {"value_encrypted": "synthetic-cipher", "origin": "test"},
                "dimensions": {"value": 3, "origin": "test"},
                "top_k": {"value": 5, "origin": "test"},
            },
        ),
        source="test",
        source_reason="golden",
    )

    trace = {
        "candidate_id": "trace-1",
        "conversation_id": "conversation-trace",
        "role": "user",
        "content": RAW_TRACE_CONTENT,
        "timestamp": "2026-08-19T08:00:00Z",
        "timestamp_iso": "2026-08-19T08:00:00Z",
        "summary_id": None,
        "score": 0.81,
        "source_kind": "trace",
        "source_lane": "global",
    }
    summary = {
        "candidate_id": "summary-1",
        "conversation_id": "conversation-summary",
        "role": "summary",
        "content": RAW_SUMMARY_CONTENT,
        "timestamp": "2026-08-19T08:05:00Z",
        "timestamp_iso": "2026-08-19T08:05:00Z",
        "start_ts": "2026-08-19T08:00:00Z",
        "end_ts": "2026-08-19T08:05:00Z",
        "summary_id": "summary-1",
        "score": 0.92,
        "retrieval_score": 0.92,
        "semantic_score": 0.92,
        "source_kind": "summary",
        "source_lane": "summaries",
    }

    def fake_merge(*, dense_candidates, lexical_candidates, top_k, include_internal_scores=False):
        del lexical_candidates, top_k
        row = dict(dense_candidates[0])
        if include_internal_scores:
            row["retrieval_score"] = row["score"]
            row["semantic_score"] = row["score"]
        return [row]

    with (
        patch.object(memory_store.runtime_settings, "get_embedding_settings", return_value=embedding_view),
        patch.object(memory_store, "embed", return_value=[0.1, 0.2, 0.3]),
        patch.object(memory_store, "_conn", return_value=object()),
        patch.object(memory_store.memory_traces_summaries, "_retrieve_dense_candidates", return_value=[trace]),
        patch.object(memory_store.memory_traces_summaries, "_retrieve_lexical_candidates", return_value=[]),
        patch.object(memory_store.memory_traces_summaries, "_merge_hybrid_candidates", side_effect=fake_merge),
        patch.object(memory_store.memory_traces_summaries, "_retrieve_summary_candidates", return_value=[summary]),
        patch.object(memory_store.memory_traces_summaries.chat_turn_logger, "emit", return_value=None),
    ):
        public_rows = memory_store.retrieve(RAW_MEMORY_QUERY)
        internal_rows = memory_store.retrieve_for_arbiter(RAW_MEMORY_QUERY)

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "decisions": [
                                        {
                                            "candidate_id": "summary-1",
                                            "keep": True,
                                            "semantic_relevance": 0.92,
                                            "contextual_gain": 0.92,
                                            "redundant_with_recent": False,
                                            "reason": "synthetic-summary-selected",
                                        },
                                        {
                                            "candidate_id": "trace-1",
                                            "keep": False,
                                            "semantic_relevance": 0.81,
                                            "contextual_gain": 0.20,
                                            "redundant_with_recent": False,
                                            "reason": "synthetic-trace-rejected",
                                        },
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

    settings = {
        "model": "synthetic-memory-arbiter",
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 128,
        "timeout_s": 1,
    }
    with (
        patch.object(arbiter, "_runtime_memory_arbiter_settings", return_value=settings),
        patch.object(arbiter, "_load_prompt", return_value="synthetic-arbiter-contract"),
        patch.object(arbiter.llm_client, "with_provider_attribution", side_effect=lambda payload, caller: payload),
        patch.object(arbiter.llm_client, "or_chat_completions_url", return_value="https://synthetic.invalid/chat"),
        patch.object(arbiter.llm_client, "or_headers", return_value={}),
        patch.object(arbiter.llm_client, "log_provider_metadata", return_value=None),
        patch.object(arbiter.requests, "post", return_value=FakeResponse()),
    ):
        kept, decisions = arbiter.filter_traces_with_diagnostics(internal_rows, [])

    return {
        "public_roles": tuple(row["role"] for row in public_rows),
        "public_has_internal_scores": any("semantic_score" in row for row in public_rows),
        "internal_sources": tuple(
            (row["source_kind"], row["source_lane"], row["candidate_id"])
            for row in internal_rows
        ),
        "kept_candidate_ids": tuple(row["candidate_id"] for row in kept),
        "decisions": tuple(
            (item["candidate_id"], item["keep"], item["decision_source"], item["model"])
            for item in decisions
        ),
    }


def exercise_identity_read_model_matrix() -> dict[str, Any]:
    canonical_static = "SYNTHETIC-CANONICAL-STATIC"
    canonical_mutable = "SYNTHETIC-CANONICAL-MUTABLE"

    identity_module = SimpleNamespace(
        build_identity_input=lambda: {
            "schema_version": "v2",
            "frida": {
                "static": {"content": canonical_static, "source": "synthetic-static"},
                "mutable": {"content": canonical_mutable, "source_trace_id": "trace-llm"},
            },
            "user": {
                "static": {"content": canonical_static, "source": "synthetic-static"},
                "mutable": {"content": canonical_mutable, "source_trace_id": "trace-user"},
            },
        },
        build_identity_block=lambda: ("synthetic-active-block", ["identity-active-1"]),
    )

    def collection(subject: str, limit: int | None = None) -> dict[str, Any]:
        return {
            "total_count": 1,
            "limit": limit,
            "items": [
                {
                    "identity_id": f"{subject}-legacy-1",
                    "content": RAW_LEGACY_IDENTITY,
                    "content_norm": RAW_LEGACY_IDENTITY,
                    "reason": RAW_LEGACY_IDENTITY,
                    "content_a": RAW_LEGACY_IDENTITY,
                    "content_b": RAW_LEGACY_IDENTITY,
                    "status": "accepted",
                }
            ],
        }

    memory_module = SimpleNamespace(
        list_identity_fragments=collection,
        list_identity_evidence=collection,
        list_identity_conflicts=collection,
        get_latest_mutable_identity_audit=lambda _subject: {},
        get_latest_identity_staging_state=lambda: {},
    )
    static_module = SimpleNamespace(
        read_static_identity_snapshot=lambda subject: SimpleNamespace(
            subject=subject,
            resource_field=f"{subject}_identity_path",
            configured_path=f"synthetic/{subject}.txt",
            resolution_kind="synthetic",
            resolved_path=f"/synthetic/{subject}.txt",
            content=canonical_static,
            raw_content=canonical_static,
        )
    )

    payload, status = admin_identity_read_model_service.identity_read_model_response(
        {"limit": 2},
        memory_store_module=memory_module,
        identity_module=identity_module,
        static_identity_content_module=static_module,
    )
    if status != 200:
        raise AssertionError(f"identity read-model fixture failed: {payload.get('error_code')}")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if RAW_LEGACY_IDENTITY in encoded:
        raise AssertionError("legacy identity content escaped the minimized read-model projection")

    subjects = tuple(sorted(payload["subjects"]))
    blocks = tuple(payload["subjects"][subject] for subject in subjects)
    return {
        "status": status,
        "ok": payload["ok"],
        "read_model_version": payload["read_model_version"],
        "active_identity_source": payload["active_runtime"]["active_identity_source"],
        "subjects": subjects,
        "canonical_layers_present": tuple(
            (bool(block["static"]["content"]), bool(block["mutable"]["content"]))
            for block in blocks
        ),
        "legacy_runtime_authority": tuple(
            block["legacy_fragments"]["runtime_authority"] for block in blocks
        ),
        "legacy_content_minimized": tuple(
            block["legacy_fragments"]["content_minimized"] for block in blocks
        ),
        "legacy_item_raw_keys_present": tuple(
            any(
                key in block["legacy_fragments"]["items"][0]
                for key in admin_identity_read_model_service.LEGACY_RAW_TEXT_KEYS
            )
            for block in blocks
        ),
        "legacy_drives_active_injection": payload["active_runtime"]["legacy_drives_active_injection"],
    }


def exercise_runtime_settings_matrix() -> dict[str, Any]:
    stored = runtime_settings.normalize_stored_payload(
        "main_model",
        {
            "model": {"value": "synthetic-main-model", "origin": "db"},
            "api_key": {"value_encrypted": RAW_SETTINGS_CIPHERTEXT, "origin": "db"},
        },
    )
    read_view = runtime_settings.redact_payload_for_api("main_model", stored)

    validation = runtime_settings.validate_runtime_section(
        "identity_governance",
        {"IDENTITY_MIN_CONFIDENCE": {"value": 0.75}},
        fetcher=lambda: {},
    )

    with patch.object(
        runtime_settings.runtime_secrets,
        "encrypt_runtime_secret_value",
        return_value=RAW_SETTINGS_CIPHERTEXT,
    ):
        normalized_patch = runtime_settings.normalize_admin_patch_payload(
            "main_model",
            {
                "model": {"value": "synthetic-next-model"},
                "api_key": {"replace_value": RAW_SETTINGS_SECRET},
            },
        )

    secret_read = read_view["api_key"]
    secret_patch = normalized_patch["api_key"]
    return {
        "read": {
            "fields": tuple(sorted(read_view)),
            "secret_keys": tuple(sorted(secret_read)),
            "secret_is_set": secret_read["is_set"],
            "secret_value_present": "value" in secret_read or "value_encrypted" in secret_read,
        },
        "validation": {
            "section": validation["section"],
            "valid": validation["valid"],
            "source": validation["source"],
            "source_reason": validation["source_reason"],
            "failed_checks": tuple(
                check["name"] for check in validation["checks"] if not check["ok"]
            ),
        },
        "patch": {
            "fields": tuple(sorted(normalized_patch)),
            "origins": tuple(
                normalized_patch[field]["origin"] for field in sorted(normalized_patch)
            ),
            "secret_is_set": secret_patch["is_set"],
            "plain_secret_present": "value" in secret_patch or "replace_value" in secret_patch,
            "encrypted_secret_present": "value_encrypted" in secret_patch,
        },
    }


def assert_content_free(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    leaked = [sentinel for sentinel in RAW_SENTINELS if sentinel in encoded]
    if leaked:
        raise AssertionError(f"raw synthetic sentinel leaked: {leaked}")
