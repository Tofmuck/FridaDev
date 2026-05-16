from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from core import chat_llm_flow
from core import chat_memory_flow
from memory import summarizer


ACTIVE_DOC_TEXT = "CONTENU_DOCUMENT_ACTIF_NE_DOIT_PAS_CONTAMINER"


class _RuntimeSettings:
    class RuntimeSettingsSecretRequiredError(Exception):
        pass

    class RuntimeSettingsSecretResolutionError(Exception):
        pass

    def get_runtime_secret_value(self, *_args, **_kwargs):
        return "present"


class _AdminLogs:
    def __init__(self):
        self.events: list[tuple[str, dict[str, object]]] = []

    def log_event(self, event: str, **fields):
        self.events.append((event, dict(fields)))


class ActiveDocumentNonContaminationLot5Test(unittest.TestCase):
    def test_active_document_prompt_is_not_persisted_as_memory_trace_or_identity_candidate(self):
        prompt_messages = [
            {
                "role": "system",
                "content": f"[DOCUMENTS ACTIFS DE CONVERSATION]\n{ACTIVE_DOC_TEXT}\n[/DOCUMENTS ACTIFS DE CONVERSATION]",
            },
            {"role": "user", "content": "Question courte"},
        ]
        conversation = {
            "id": "conv-active-doc-barrier",
            "created_at": "2026-05-16T12:00:00Z",
            "messages": [{"role": "user", "content": "Question courte", "timestamp": "2026-05-16T12:00:00Z"}],
        }
        observed: dict[str, object] = {}

        def fake_post(_url, *, json, **_kwargs):
            observed["llm_messages"] = list(json["messages"])
            return SimpleNamespace(raise_for_status=lambda: None)

        def fake_save_new_traces(saved_conversation):
            observed["memory_trace_messages"] = [
                dict(message) for message in saved_conversation.get("messages", [])
            ]

        def fake_record_identity_entries(_conversation_id, turn_pair, **_kwargs):
            observed["identity_turn_pair"] = [dict(message) for message in turn_pair]

        llm_module = SimpleNamespace(
            or_headers=lambda caller="llm": {"X-Caller": caller},
            build_payload=lambda messages, temperature, top_p, max_tokens, stream=False: {
                "model": "model-test",
                "messages": list(messages),
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": stream,
            },
            resolve_provider_title=lambda _caller: "test-provider",
            read_openrouter_response_payload=lambda _response: {"ok": True},
            extract_openrouter_provider_metadata=lambda _payload, requested_model=None: {
                "requested_model": requested_model,
            },
            build_provider_observability_fields=lambda caller, provider_metadata: {
                "provider_caller": caller,
                "provider_title": "test-provider",
                "provider_model": provider_metadata.get("requested_model", ""),
            },
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda _payload: "Reponse assistant",
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv["messages"].append(
                {"role": role, "content": content, "timestamp": timestamp}
            ),
            save_conversation=lambda *_args, **_kwargs: None,
        )
        memory_store_module = SimpleNamespace(
            save_new_traces=fake_save_new_traces,
            reactivate_identities=lambda _identity_ids: None,
        )

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=prompt_messages,
            runtime_main_model="model-test",
            temperature=0.1,
            top_p=1.0,
            max_tokens=200,
            stream_req=False,
            current_mode="shadow",
            identity_ids=[],
            runtime_settings_module=_RuntimeSettings(),
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            assistant_output_policy=None,
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=fake_post,
                exceptions=SimpleNamespace(RequestException=Exception),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 1),
            admin_logs_module=_AdminLogs(),
            config_module=SimpleNamespace(OR_BASE="https://example.invalid", TIMEOUT_S=10),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            web_input=None,
            now_iso_func=lambda: "2026-05-16T12:01:00Z",
            record_identity_entries_for_mode=fake_record_identity_entries,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, _updated_at: {},
        )

        self.assertEqual(result["status"], 200)
        self.assertIn(ACTIVE_DOC_TEXT, _joined_contents(observed["llm_messages"]))
        self.assertNotIn(ACTIVE_DOC_TEXT, _joined_contents(observed["memory_trace_messages"]))
        self.assertNotIn(ACTIVE_DOC_TEXT, _joined_contents(observed["identity_turn_pair"]))

    def test_memory_retrieval_uses_user_message_only_not_active_document_text(self):
        observed_queries: list[str] = []

        class MemoryStore:
            def retrieve_for_arbiter_with_status(self, query):
                observed_queries.append(str(query))
                return {"status": "ok", "traces": []}

            def get_recent_context_hints(self, **_kwargs):
                return []

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            MEMORY_TOP_K=5,
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-barrier",
            "messages": [
                {"role": "system", "content": ACTIVE_DOC_TEXT},
                {"role": "user", "content": "Question utilisateur"},
            ],
        }

        with mock.patch.object(chat_memory_flow.memory_chain_snapshot, "emit_memory_chain_snapshot", return_value=None):
            result = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg="Question utilisateur",
                config_module=config_module,
                memory_store_module=MemoryStore(),
                arbiter_module=SimpleNamespace(),
                admin_logs_module=_AdminLogs(),
            )

        self.assertEqual(observed_queries, ["Question utilisateur"])
        self.assertNotIn(ACTIVE_DOC_TEXT, observed_queries[0])
        self.assertEqual(result.memory_traces, [])
        self.assertEqual(result.context_hints, [])

    def test_summary_generation_uses_only_dialogue_not_active_document_lane(self):
        conversation = {
            "id": "conv-summary-barrier",
            "messages": [
                {"role": "system", "content": ACTIVE_DOC_TEXT},
                {"role": "user", "content": "Ancienne question 1", "timestamp": "2026-05-16T10:00:00Z"},
                {"role": "assistant", "content": "Ancienne reponse 1", "timestamp": "2026-05-16T10:01:00Z"},
                {"role": "user", "content": "Ancienne question 2", "timestamp": "2026-05-16T10:02:00Z"},
                {"role": "assistant", "content": "Ancienne reponse 2", "timestamp": "2026-05-16T10:03:00Z"},
            ],
        }
        observed: dict[str, object] = {}

        def fake_estimate_tokens(messages, _model):
            observed["threshold_messages"] = [dict(message) for message in messages]
            return 999

        def fake_summarize_conversation(turns, _model):
            observed["summary_turns"] = [dict(turn) for turn in turns]
            return "resume compact"

        with (
            mock.patch.object(summarizer.config, "SUMMARY_THRESHOLD_TOKENS", 10),
            mock.patch.object(summarizer.config, "SUMMARY_KEEP_TURNS", 1),
            mock.patch.object(summarizer, "estimate_tokens", side_effect=fake_estimate_tokens),
            mock.patch.object(summarizer, "summarize_conversation", side_effect=fake_summarize_conversation),
            mock.patch.object(summarizer, "_runtime_summary_model_name", return_value="summary-model"),
            mock.patch("memory.memory_store.save_summary", return_value=None),
            mock.patch("memory.memory_store.update_traces_summary_id", return_value=None),
        ):
            self.assertTrue(summarizer.maybe_summarize(conversation, "model-test"))

        self.assertNotIn(ACTIVE_DOC_TEXT, _joined_contents(observed["threshold_messages"]))
        self.assertNotIn(ACTIVE_DOC_TEXT, _joined_contents(observed["summary_turns"]))
        self.assertEqual(
            [message["role"] for message in observed["threshold_messages"]],
            ["user", "assistant", "user", "assistant"],
        )


def _joined_contents(messages) -> str:
    return "\n".join(str(message.get("content") or "") for message in messages)


if __name__ == "__main__":
    unittest.main()
