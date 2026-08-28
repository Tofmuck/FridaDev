from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Mapping, Sequence

from admin import runtime_settings
from core import chat_stream_control
from core import conversations_store
from core import workspace_folder_notes_prompt_lane
from core.chat_document_prompt_reads import ActiveDocumentsPromptRead
from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.validation import validation_agent

from tests.support.server_chat_pipeline import patch_server_chat_pipeline


STIMMUNG_PRIMARY_MODEL = "lot4/stimmung-primary"
STIMMUNG_FALLBACK_MODEL = "lot4/stimmung-fallback"
VALIDATION_PRIMARY_MODEL = "lot4/validation-primary"
VALIDATION_FALLBACK_MODEL = "lot4/validation-fallback"
MAIN_MODEL = "lot4/main"


def affective_signal(tone: str, strength: int, *, confidence: float = 0.8) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "present": True,
        "tones": [{"tone": str(tone), "strength": int(strength)}],
        "dominant_tone": str(tone),
        "confidence": float(confidence),
    }


@dataclass(frozen=True)
class StimmungTurnOutcome:
    primary: Mapping[str, Any] | str
    fallback: Mapping[str, Any] | str | None = None


def primary_signal(signal: Mapping[str, Any]) -> StimmungTurnOutcome:
    return StimmungTurnOutcome(primary=copy.deepcopy(dict(signal)))


def fallback_signal(signal: Mapping[str, Any]) -> StimmungTurnOutcome:
    return StimmungTurnOutcome(primary="error", fallback=copy.deepcopy(dict(signal)))


def double_failure() -> StimmungTurnOutcome:
    return StimmungTurnOutcome(primary="error", fallback="error")


def _runtime_view(section: str, values: Mapping[str, Any]) -> runtime_settings.RuntimeSectionView:
    payload = {
        key: {"value": value, "origin": "test_fixture"}
        for key, value in values.items()
    }
    return runtime_settings.RuntimeSectionView(
        section=section,
        payload=payload,
        source="test_fixture",
        source_reason="lot4_causal_golden",
    )


def _assistant_payload(text: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": text}}],
        "model": "lot4/synthetic-observed",
    }


class _FakeResponse:
    encoding = None

    def __init__(self, text: str, *, stream: bool = False) -> None:
        self._text = text
        self._stream = bool(stream)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return _assistant_payload(self._text)

    def iter_lines(self, decode_unicode: bool = True, delimiter: str = "\n"):
        del decode_unicode, delimiter
        if not self._stream:
            return
        yield "data: " + json.dumps(
            {"choices": [{"delta": {"content": self._text}}]},
            ensure_ascii=True,
            separators=(",", ":"),
        )
        yield "data: [DONE]"


def _serialized_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(list(messages), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


class _SilentStoreLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _CatalogWriteCursor:
    def __init__(self, store: "_StimmungConversationStore") -> None:
        self._store = store
        self._returned: dict[str, Any] | None = None

    def __enter__(self) -> "_CatalogWriteCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def execute(self, _sql: str, params: Sequence[Any]) -> None:
        self._store.catalog_row = {
            "id": params[0],
            "title": params[1],
            "created_at": params[2],
            "updated_at": params[3],
            "message_count": params[4],
            "last_message_preview": params[5],
            "workspace_folder_id": params[6],
            "deleted_at": None,
        }
        self._returned = {"id": params[0]}

    def fetchone(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._returned)


class _MessageWriteCursor:
    def __init__(self, store: "_StimmungConversationStore") -> None:
        self._store = store

    def __enter__(self) -> "_MessageWriteCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def execute(self, _sql: str, _params: Sequence[Any]) -> None:
        self._store.message_rows = []

    def executemany(self, _sql: str, rows: Sequence[Sequence[Any]]) -> None:
        self._store.message_rows = [tuple(row) for row in rows]


class _AtomicWriteConnection:
    def __init__(self, store: "_StimmungConversationStore") -> None:
        self._store = store
        self._cursor_index = 0

    def __enter__(self) -> "_AtomicWriteConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def cursor(self, **_kwargs: Any) -> _CatalogWriteCursor | _MessageWriteCursor:
        self._cursor_index += 1
        if self._cursor_index == 1:
            return _CatalogWriteCursor(self._store)
        return _MessageWriteCursor(self._store)

    def commit(self) -> None:
        return None


class _CatalogReadCursor:
    def __init__(self, store: "_StimmungConversationStore") -> None:
        self._store = store

    def __enter__(self) -> "_CatalogReadCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def fetchone(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._store.catalog_row)


class _MessageReadCursor:
    def __init__(self, store: "_StimmungConversationStore") -> None:
        self._store = store

    def __enter__(self) -> "_MessageReadCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def fetchall(self) -> list[dict[str, Any]]:
        loaded: list[dict[str, Any]] = []
        for row in self._store.message_rows:
            json_meta = row[7]
            meta = copy.deepcopy(json_meta.obj) if json_meta is not None else None
            loaded.append(
                {
                    "role": row[2],
                    "content": row[3],
                    "timestamp": row[4],
                    "summarized_by": row[5],
                    "embedded": row[6],
                    "meta": meta,
                }
            )
        return loaded


class _ReadConnection:
    def __init__(self, cursor: _CatalogReadCursor | _MessageReadCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> "_ReadConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def cursor(self, **_kwargs: Any) -> _CatalogReadCursor | _MessageReadCursor:
        return self._cursor


class _StimmungConversationStore:
    """Exercise the product store functions over bounded in-memory row results."""

    def __init__(self) -> None:
        self.catalog_row: dict[str, Any] | None = None
        self.message_rows: list[tuple[Any, ...]] = []
        self.logger = _SilentStoreLogger()

    @staticmethod
    def _ts_to_iso(raw: Any) -> str:
        return conversations_store.ts_to_iso(
            raw,
            now_iso_func=lambda: "2026-08-28T09:00:00Z",
        )

    @classmethod
    def _normalize_messages(cls, messages: Any) -> list[dict[str, Any]]:
        return conversations_store.normalize_messages_for_storage(
            messages,
            ts_to_iso_func=cls._ts_to_iso,
            coerce_bool_func=conversations_store.coerce_bool,
        )

    @classmethod
    def _metadata(cls, conversation: dict[str, Any]) -> dict[str, Any]:
        return conversations_store.conversation_metadata(
            conversation,
            safe_title_func=conversations_store.safe_title,
            ts_to_iso_func=cls._ts_to_iso,
            now_iso_func=lambda: "2026-08-28T09:00:00Z",
            default_title=conversations_store.DEFAULT_TITLE,
            infer_title_from_messages_func=lambda messages: conversations_store.infer_title_from_messages(
                messages,
                collapse_ws_func=conversations_store.collapse_ws,
                safe_title_func=conversations_store.safe_title,
            ),
            last_message_preview_func=lambda messages: conversations_store.last_message_preview(
                messages,
                collapse_ws_func=conversations_store.collapse_ws,
                preview_max_chars=conversations_store.PREVIEW_MAX_CHARS,
            ),
        )

    def save(self, conversation: Mapping[str, Any], *, updated_at: str | None) -> Any:
        mutable = conversation if isinstance(conversation, dict) else dict(conversation)

        def atomic_save(saved: dict[str, Any], preserve_deleted: bool) -> tuple[bool, bool, str | None]:
            return conversations_store.save_conversation_catalog_and_messages_atomic(
                saved,
                preserve_deleted=preserve_deleted,
                conversation_metadata_func=self._metadata,
                normalize_conversation_id_func=conversations_store.normalize_conversation_id,
                normalize_messages_for_storage_func=self._normalize_messages,
                db_conn_func=lambda: _AtomicWriteConnection(self),
                parse_iso_to_dt_func=conversations_store.parse_iso_to_dt,
                logger=self.logger,
            )

        return conversations_store.save_conversation(
            mutable,
            updated_at=updated_at,
            preserve_deleted=False,
            now_iso_func=lambda: "2026-08-28T09:00:00Z",
            normalize_messages_for_storage_func=self._normalize_messages,
            logger=self.logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            upsert_conversation_catalog_func=lambda *_args, **_kwargs: None,
            upsert_conversation_messages_func=lambda *_args, **_kwargs: False,
            atomic_save_func=atomic_save,
        )

    def load(self, conversation_id: str, system_prompt: str) -> dict[str, Any]:
        def get_summary(conv_id: str) -> dict[str, Any] | None:
            return conversations_store.get_conversation_summary(
                conv_id,
                include_deleted=True,
                normalize_conversation_id_func=conversations_store.normalize_conversation_id,
                db_conn_func=lambda: _ReadConnection(_CatalogReadCursor(self)),
                serialize_catalog_row_func=lambda row: conversations_store.serialize_catalog_row(
                    row,
                    safe_title_func=conversations_store.safe_title,
                    ts_to_iso_func=self._ts_to_iso,
                    default_title=conversations_store.DEFAULT_TITLE,
                ),
                logger=self.logger,
            )

        def load_messages(conv_id: str) -> list[dict[str, Any]] | None:
            return conversations_store.load_messages_from_db(
                conv_id,
                normalize_conversation_id_func=conversations_store.normalize_conversation_id,
                db_conn_func=lambda: _ReadConnection(_MessageReadCursor(self)),
                ts_to_iso_func=self._ts_to_iso,
                logger=self.logger,
            )

        def build(summary: dict[str, Any], messages: list[dict[str, Any]], prompt: str) -> dict[str, Any]:
            return conversations_store.build_conversation_from_catalog(
                summary,
                messages,
                prompt,
                default_title=conversations_store.DEFAULT_TITLE,
                now_iso_func=lambda: "2026-08-28T09:00:00Z",
                normalize_conversation_func=lambda data, conv_id, system: conversations_store.normalize_conversation(
                    data,
                    conv_id,
                    system,
                    now_iso_func=lambda: "2026-08-28T09:00:00Z",
                    safe_title_func=conversations_store.safe_title,
                    find_system_message_func=conversations_store.find_system_message,
                ),
            )

        loaded = conversations_store.load_conversation(
            conversation_id,
            system_prompt,
            normalize_conversation_id_func=conversations_store.normalize_conversation_id,
            get_conversation_summary_func=get_summary,
            load_messages_from_db_func=load_messages,
            build_conversation_from_catalog_func=build,
            logger=self.logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
        )
        if loaded is None:
            raise AssertionError("synthetic Stimmung store failed to reload the conversation")
        return loaded


def capture_validation_request(canonical_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Capture the real bounded Validation request without a provider call."""

    calls: list[dict[str, Any]] = []

    class FakeRequests:
        class exceptions:
            class RequestException(Exception):
                pass

            class Timeout(RequestException):
                pass

        @staticmethod
        def post(*_args: Any, **kwargs: Any) -> _FakeResponse:
            calls.append(copy.deepcopy(dict(kwargs.get("json") or {})))
            return _FakeResponse(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "final_judgment_posture": "answer",
                        "final_output_regime": "simple",
                        "arbiter_reason": "lot4_synthetic_validation",
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
            )

    primary_payload = primary_node.build_primary_node(
        conversation_id="conv-lot4-validation-capture",
        updated_at="2026-08-28T09:00:00Z",
        time_input={
            "schema_version": "v1",
            "now_utc_iso": "2026-08-28T09:00:00Z",
            "timezone": "UTC",
            "now_local_iso": "2026-08-28T09:00:00+00:00",
            "local_date": "2026-08-28",
            "local_time": "09:00",
            "local_weekday": "friday",
            "day_part_class": "morning",
            "day_part_human": "matin",
        },
        user_turn_input={
            "schema_version": "v1",
            "geste_dialogique_dominant": "exposition",
            "regime_probatoire": {
                "principe": "maximal_possible",
                "types_de_preuve_attendus": [],
                "provenances": [],
                "regime_de_vigilance": "standard",
                "composition_probatoire": "isolee",
            },
            "qualification_temporelle": {
                "portee_temporelle": "atemporale",
                "ancrage_temporel": "non_ancre",
            },
        },
        user_turn_signals={
            "present": True,
            "ambiguity_present": False,
            "underdetermination_present": False,
            "active_signal_families": [],
            "active_signal_families_count": 0,
        },
    )["primary_verdict"]

    original_settings = validation_agent.runtime_settings.get_validation_agent_model_settings
    original_url = validation_agent.llm_client.or_chat_completions_url
    original_headers = validation_agent.llm_client.or_headers
    try:
        validation_agent.runtime_settings.get_validation_agent_model_settings = lambda: _runtime_view(
            "validation_agent_model",
            {
                "primary_model": VALIDATION_PRIMARY_MODEL,
                "fallback_model": VALIDATION_FALLBACK_MODEL,
                "timeout_s": 2,
                "temperature": 0.0,
                "top_p": 1.0,
                "max_tokens": 120,
            },
        )
        validation_agent.llm_client.or_chat_completions_url = lambda: "https://lot4.invalid/chat"
        validation_agent.llm_client.or_headers = lambda **_kwargs: {}
        result = validation_agent.build_validated_output(
            primary_verdict=primary_payload,
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [
                    {
                        "role": "user",
                        "content": "LOT4_SYNTHETIC_VALIDATION_TURN",
                        "timestamp": "2026-08-28T09:00:00Z",
                    }
                ],
            },
            canonical_inputs=copy.deepcopy(dict(canonical_inputs)),
            requests_module=FakeRequests,
        )
    finally:
        validation_agent.llm_client.or_headers = original_headers
        validation_agent.llm_client.or_chat_completions_url = original_url
        validation_agent.runtime_settings.get_validation_agent_model_settings = original_settings

    if len(calls) != 1:
        raise AssertionError("Validation capture expected exactly one provider request")
    return {
        "messages": calls[0]["messages"],
        "result": result,
        "user_content": str(calls[0]["messages"][1]["content"]),
    }


def exercise_stimmung_dialogue(
    server_module: Any,
    *,
    outcomes: Sequence[StimmungTurnOutcome],
    stream: bool = False,
    corrupt_signal_after_turns: Sequence[int] = (),
) -> dict[str, Any]:
    """Traverse chat and the real store functions over bounded provider/row fakes."""

    if not outcomes:
        raise ValueError("at least one synthetic turn is required")

    conversation_id = "44444444-4444-4444-8444-444444444444"
    initial_conversation = {
        "id": conversation_id,
        "created_at": "2026-08-28T09:00:00Z",
        "messages": [
            {
                "role": "system",
                "content": "LOT4_SYNTHETIC_SYSTEM",
                "timestamp": "2026-08-28T09:00:00Z",
            }
        ],
    }
    store = _StimmungConversationStore()
    seeded = store.save(initial_conversation, updated_at="2026-08-28T09:00:00Z")
    if not seeded.ok:
        raise AssertionError("synthetic Stimmung store seed failed")
    durable_json = json.dumps(
        store.load(conversation_id, "LOT4_SYNTHETIC_SYSTEM"),
        ensure_ascii=True,
        sort_keys=True,
    )
    durable_snapshots: list[dict[str, Any]] = []
    reload_snapshots: list[dict[str, Any]] = []
    reload_instances: list[dict[str, Any]] = []
    reload_object_ids: list[int] = []
    provider_calls: list[dict[str, Any]] = []
    validation_messages: list[list[dict[str, Any]]] = []
    main_messages: list[list[dict[str, Any]]] = []
    node_calls: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    chat_response_calls: list[dict[str, Any]] = []
    active_turn = {"index": 0}
    real_chat_response = server_module.chat_service.chat_response
    real_stimmung_caller = server_module.chat_service.stimmung_agent.build_affective_turn_signal
    real_prompt_builder = server_module.conv_store.build_prompt_messages

    def save_durable(conversation: Mapping[str, Any], **kwargs: Any) -> Any:
        nonlocal durable_json
        result = store.save(conversation, updated_at=kwargs.get("updated_at"))
        snapshot = store.load(conversation_id, "LOT4_SYNTHETIC_SYSTEM")
        durable_json = json.dumps(snapshot, ensure_ascii=True, sort_keys=True)
        durable_snapshots.append(snapshot)
        return result

    request_error_class = server_module.requests.exceptions.RequestException

    def requests_post(*_args: Any, **kwargs: Any) -> _FakeResponse:
        payload = kwargs.get("json") if isinstance(kwargs.get("json"), dict) else {}
        model = str(payload.get("model") or "")
        messages = copy.deepcopy(list(payload.get("messages") or []))
        provider_calls.append(
            {
                "model": model,
                "stream": bool(kwargs.get("stream")),
                "messages_chars": len(_serialized_messages(messages)),
            }
        )

        if model in {STIMMUNG_PRIMARY_MODEL, STIMMUNG_FALLBACK_MODEL}:
            outcome = outcomes[active_turn["index"]]
            selected = outcome.primary if model == STIMMUNG_PRIMARY_MODEL else outcome.fallback
            if selected == "error" or selected is None:
                raise request_error_class("lot4_synthetic_transport_error")
            if selected == "invalid_json":
                return _FakeResponse("LOT4_INVALID_JSON")
            return _FakeResponse(json.dumps(dict(selected), ensure_ascii=True, separators=(",", ":")))

        if model in {VALIDATION_PRIMARY_MODEL, VALIDATION_FALLBACK_MODEL}:
            validation_messages.append(messages)
            return _FakeResponse(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "final_judgment_posture": "answer",
                        "final_output_regime": "simple",
                        "arbiter_reason": "lot4_synthetic_validation",
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
            )

        if model == MAIN_MODEL:
            main_messages.append(messages)
            return _FakeResponse(
                f"LOT4_SYNTHETIC_ASSISTANT_{active_turn['index'] + 1:02d}",
                stream=bool(kwargs.get("stream")),
            )

        raise AssertionError(f"unexpected synthetic model: {model}")

    base_observed, restore_base = patch_server_chat_pipeline(
        server_module,
        conversation=initial_conversation,
        requests_post=requests_post,
        build_prompt_messages=real_prompt_builder,
        save_conversation_result=save_durable,
        runtime_model=MAIN_MODEL,
        existing_conversation=True,
        summarize_user_turn=False,
        hermeneutic_mode="enforced_all",
        disable_chat_log_storage=True,
    )

    originals: list[tuple[Any, str, Any]] = []

    def patch_attr(obj: Any, name: str, value: Any) -> None:
        originals.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    real_node = server_module.chat_service._run_hermeneutic_node_insertion_point

    def load_durable(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        conversation = store.load(conversation_id, "LOT4_SYNTHETIC_SYSTEM")
        # Keep references alive so object identity cannot be recycled across reloads.
        reload_instances.append(conversation)
        reload_object_ids.append(id(conversation))
        reload_snapshots.append(copy.deepcopy(conversation))
        return conversation

    def observed_node(**kwargs: Any) -> dict[str, Any]:
        call = {
            "stimmung_input": copy.deepcopy(dict(kwargs.get("stimmung_input") or {})),
        }
        result = real_node(**kwargs)
        primary_payload = copy.deepcopy(dict(result.get("primary_payload") or {}))
        validated_result = result.get("validated_result")
        call["primary_payload"] = primary_payload
        call["validated_status"] = str(getattr(validated_result, "status", ""))
        call["validated_output"] = copy.deepcopy(dict(getattr(validated_result, "validated_output", {}) or {}))
        node_calls.append(call)
        return result

    def observed_chat_response(data: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
        chat_response_calls.append(
            {
                "stream": bool(data.get("stream")),
                "conversation_id_present": bool(data.get("conversation_id")),
            }
        )
        return real_chat_response(data, **kwargs)

    clock_origin = datetime(2026, 8, 28, 9, 1, tzinfo=timezone.utc)

    def now_iso() -> str:
        value = clock_origin + timedelta(minutes=active_turn["index"])
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    def record_event(event: Mapping[str, Any], **_kwargs: Any) -> dict[str, bool]:
        events.append(copy.deepcopy(dict(event)))
        return {"inserted": True}

    try:
        patch_attr(server_module.conv_store, "load_conversation", load_durable)
        patch_attr(server_module.conv_store, "normalize_conversation_id", lambda _raw: conversation_id)
        patch_attr(server_module.conv_store, "_get_active_summary", lambda _conversation_id: None)
        patch_attr(server_module.chat_service.stimmung_agent, "build_affective_turn_signal", real_stimmung_caller)
        patch_attr(
            server_module.runtime_settings,
            "get_stimmung_agent_model_settings",
            lambda: _runtime_view(
                "stimmung_agent_model",
                {
                    "primary_model": STIMMUNG_PRIMARY_MODEL,
                    "fallback_model": STIMMUNG_FALLBACK_MODEL,
                    "timeout_s": 2,
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_tokens": 96,
                },
            ),
        )
        patch_attr(
            server_module.runtime_settings,
            "get_validation_agent_model_settings",
            lambda: _runtime_view(
                "validation_agent_model",
                {
                    "primary_model": VALIDATION_PRIMARY_MODEL,
                    "fallback_model": VALIDATION_FALLBACK_MODEL,
                    "timeout_s": 2,
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_tokens": 120,
                },
            ),
        )
        patch_attr(server_module.llm, "or_chat_completions_url", lambda: "https://lot4.invalid/chat")
        patch_attr(server_module.chat_service, "chat_response", observed_chat_response)
        patch_attr(server_module.chat_service, "_run_hermeneutic_node_insertion_point", observed_node)
        patch_attr(server_module.chat_service, "_now_iso", now_iso)
        patch_attr(server_module.chat_turn_logger, "_now_iso", now_iso)
        patch_attr(server_module.chat_turn_logger.log_store, "insert_chat_log_event", record_event)
        patch_attr(
            server_module,
            "_finish_chat_turn_and_refresh_dashboard",
            lambda token, *, final_status: server_module.chat_turn_logger.end_turn(
                token,
                final_status=final_status,
            ),
        )
        patch_attr(
            server_module.chat_service,
            "_active_documents_for_prompt",
            lambda **_kwargs: ActiveDocumentsPromptRead(status="empty"),
        )
        patch_attr(
            server_module.chat_service,
            "_workspace_files_for_prompt",
            lambda **_kwargs: ActiveDocumentsPromptRead(status="empty"),
        )
        patch_attr(
            server_module.chat_service.workspace_folder_notes_prompt_lane,
            "read_workspace_folder_notes_for_prompt",
            lambda **_kwargs: workspace_folder_notes_prompt_lane.WorkspaceFolderNotesPromptRead(
                status=workspace_folder_notes_prompt_lane.READ_STATUS_EMPTY,
            ),
        )

        client = server_module.app.test_client()
        corrupt_after = {int(value) for value in corrupt_signal_after_turns}
        for index in range(len(outcomes)):
            active_turn["index"] = index
            response = client.post(
                "/api/chat",
                json={
                    "message": f"LOT4_SYNTHETIC_USER_{index + 1:02d}",
                    "stream": bool(stream),
                    "conversation_id": conversation_id,
                },
            )
            raw = response.get_data()
            visible_text = ""
            terminal = None
            if stream:
                visible_text, terminal = chat_stream_control.split_text_and_terminal(raw)
            responses.append(
                {
                    "status_code": response.status_code,
                    "visible_text": visible_text,
                    "terminal": copy.deepcopy(terminal),
                    "json": None if stream else response.get_json(),
                }
            )
            if response.status_code != 200:
                raise AssertionError(f"synthetic chat turn failed: {response.status_code}")

            if index + 1 in corrupt_after:
                stored = store.load(conversation_id, "LOT4_SYNTHETIC_SYSTEM")
                user_messages = [
                    item
                    for item in stored.get("messages", [])
                    if isinstance(item, dict) and item.get("role") == "user"
                ]
                if not user_messages:
                    raise AssertionError("synthetic corruption target missing")
                user_messages[-1].setdefault("meta", {})["affective_turn_signal"] = {
                    "schema_version": "v1",
                    "present": True,
                    "tones": [{"tone": "lot4_invalid", "strength": 99}],
                    "dominant_tone": "lot4_invalid",
                    "confidence": 2.0,
                }
                corruption_saved = store.save(stored, updated_at=stored.get("updated_at"))
                if not corruption_saved.ok:
                    raise AssertionError("synthetic Stimmung corruption save failed")
                durable_json = json.dumps(
                    store.load(conversation_id, "LOT4_SYNTHETIC_SYSTEM"),
                    ensure_ascii=True,
                    sort_keys=True,
                )

        repeated_reload_a = load_durable()
        repeated_reload_b = load_durable()
    finally:
        while originals:
            obj, name, value = originals.pop()
            setattr(obj, name, value)
        restore_base()

    caller_events = [event for event in events if event.get("stage") == "stimmung_agent"]
    return {
        "base_observed": base_observed,
        "caller_events": caller_events,
        "chat_response_calls": chat_response_calls,
        "durable": json.loads(durable_json),
        "durable_json": durable_json,
        "durable_snapshots": durable_snapshots,
        "events": events,
        "main_messages": main_messages,
        "node_calls": node_calls,
        "provider_calls": provider_calls,
        "reload_object_ids": reload_object_ids,
        "reload_snapshots": reload_snapshots,
        "repeated_reloads": [repeated_reload_a, repeated_reload_b],
        "responses": responses,
        "stored_message_row_count": len(store.message_rows),
        "validation_messages": validation_messages,
    }
