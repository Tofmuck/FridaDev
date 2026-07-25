from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from core import assistant_turn_state
from core import chat_prompt_context
from core import conversations_store
from memory import memory_traces_summaries
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


PROVENANCE_META_KEY = "assistant_runtime_provenance"
PROVENANCE_SCHEMA_VERSION = "v1"
PROVENANCE_MARKER_HEADER = "[PROVENANCE RUNTIME ASSISTANT v1]"


class _FakeResponse:
    encoding = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Le repère A reste établi. Le repère B reste établi. "
                            "Le calcul temporel annoncé est le seul point à corriger."
                        )
                    }
                }
            ]
        }

    def iter_lines(self, decode_unicode=True, delimiter="\n"):
        yield (
            'data: {"choices":[{"delta":{"content":'
            '"Le repère A reste établi. Le repère B reste établi. '
            'Le calcul temporel annoncé est le seul point à corriger."}}]}'
        )
        yield "data: [DONE]"


class WebTurnProvenanceContinuityRedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def _run_web_turn(
        self,
        *,
        stream: bool,
        context_block: str = "[CONTEXTE WEB SYNTHÉTIQUE TRANSITOIRE]",
        web_status: str = "ok",
        web_search: bool = True,
    ) -> dict:
        conversation = {
            "id": (
                "11111111-1111-4111-8111-111111111111"
                if stream
                else "22222222-2222-4222-8222-222222222222"
            ),
            "created_at": "2026-07-25T08:00:00Z",
            "messages": [
                {
                    "role": "system",
                    "content": "Système synthétique.",
                    "timestamp": "2026-07-25T08:00:00Z",
                }
            ],
        }
        observed, restore = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=lambda *_args, **_kwargs: _FakeResponse(),
            save_conversation_result=lambda conv, **kwargs: SimpleNamespace(
                ok=True,
                updated_at=kwargs.get("updated_at"),
                reason="",
                message_count=len(conv.get("messages", [])),
            ),
            existing_conversation=True,
            hermeneutic_mode="off",
            disable_chat_log_storage=True,
        )
        original_active_documents = self.server.chat_service._active_documents_for_prompt
        original_web_builder = self.server.ws.build_context_payload
        self.server.chat_service._active_documents_for_prompt = lambda **_kwargs: (
            self.server.chat_service.ActiveDocumentsPromptRead(status="empty")
        )
        self.server.ws.build_context_payload = lambda *_args, **_kwargs: {
            "enabled": True,
            "activation_mode": "manual",
            "status": web_status,
            "reason_code": "",
            "original_user_message": "Tour synthétique.",
            "query": "requête synthétique",
            "results_count": 1,
            "runtime": {},
            "sources": [],
            "context_block": context_block,
        }
        try:
            response = self.server.app.test_client().post(
                "/api/chat",
                json={
                    "message": "Évalue trois propositions indépendantes.",
                    "conversation_id": conversation["id"],
                    "stream": stream,
                    "web_search": web_search,
                },
            )
            response.get_data()
        finally:
            self.server.chat_service._active_documents_for_prompt = original_active_documents
            self.server.ws.build_context_payload = original_web_builder
            restore()
        return {
            "conversation": conversation,
            "observed": observed,
            "response": response,
        }

    def test_non_stream_web_turn_persists_content_free_runtime_provenance(self) -> None:
        case = self._run_web_turn(stream=False)

        assistant = case["conversation"]["messages"][-1]
        self.assertIn(PROVENANCE_META_KEY, assistant.get("meta") or {})
        self.assertEqual(
            assistant["meta"][PROVENANCE_META_KEY],
            {
                "schema_version": PROVENANCE_SCHEMA_VERSION,
                "response_origin": "main_model",
                "web_context_injected_to_main_model": True,
            },
        )
        self.assertNotIn("CONTEXTE WEB", repr(assistant["meta"]))
        self.assertNotIn("requête", repr(assistant["meta"]))

    def test_stream_done_web_turn_persists_same_runtime_provenance(self) -> None:
        case = self._run_web_turn(stream=True)

        assistant = case["conversation"]["messages"][-1]
        self.assertIn(PROVENANCE_META_KEY, assistant.get("meta") or {})
        self.assertEqual(
            assistant["meta"][PROVENANCE_META_KEY],
            {
                "schema_version": PROVENANCE_SCHEMA_VERSION,
                "response_origin": "main_model",
                "web_context_injected_to_main_model": True,
            },
        )

    def test_runtime_provenance_survives_storage_and_rehydration(self) -> None:
        case = self._run_web_turn(stream=False)
        assistant = case["conversation"]["messages"][-1]
        normalized = conversations_store.normalize_messages_for_storage(
            [assistant],
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: "2026-07-25T08:00:02Z",
            ),
            coerce_bool_func=conversations_store.coerce_bool,
        )

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *_args, **_kwargs):
                return None

            def fetchall(self):
                return [
                    {
                        "role": normalized[0]["role"],
                        "content": normalized[0]["content"],
                        "timestamp": datetime(2026, 7, 25, 8, 0, 2, tzinfo=timezone.utc),
                        "summarized_by": None,
                        "embedded": False,
                        "meta": normalized[0].get("meta"),
                    }
                ]

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, **_kwargs):
                return FakeCursor()

        loaded = conversations_store.load_messages_from_db(
            case["conversation"]["id"],
            normalize_conversation_id_func=lambda raw: str(raw),
            db_conn_func=lambda: FakeConn(),
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: "2026-07-25T08:00:02Z",
            ),
            logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
        )

        self.assertIn(PROVENANCE_META_KEY, loaded[0].get("meta") or {})
        self.assertEqual(
            loaded[0]["meta"][PROVENANCE_META_KEY],
            assistant["meta"][PROVENANCE_META_KEY],
        )
        rehydrated_conversation = {
            "id": case["conversation"]["id"],
            "messages": [
                {
                    "role": "system",
                    "content": "Système synthétique.",
                    "timestamp": "2026-07-25T08:00:00Z",
                },
                loaded[0],
                {
                    "role": "user",
                    "content": "Correction locale synthétique.",
                    "timestamp": "2026-07-25T08:01:00Z",
                },
            ],
        }
        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            rehydrated_prompt = conv_store.build_prompt_messages(
                rehydrated_conversation,
                model="synthetic-model",
                now="2026-07-25T08:01:01Z",
            )
        self.assertEqual(
            sum(
                str(message.get("content") or "").startswith(PROVENANCE_MARKER_HEADER)
                for message in rehydrated_prompt
            ),
            1,
        )

    def test_following_turn_without_web_receives_previous_runtime_provenance_marker(self) -> None:
        case = self._run_web_turn(stream=False)
        conversation = case["conversation"]
        conversation["messages"].append(
            {
                "role": "user",
                "content": "Correction locale : seul le calcul temporel était faux.",
                "timestamp": "2026-07-25T08:01:00Z",
            }
        )

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            prompt_messages = conv_store.build_prompt_messages(
                conversation,
                model="synthetic-model",
                now="2026-07-25T08:01:01Z",
                memory_traces=None,
                context_hints=None,
            )

        markers = [
            message
            for message in prompt_messages
            if message.get("role") == "system"
            and str(message.get("content") or "").startswith(PROVENANCE_MARKER_HEADER)
        ]
        self.assertEqual(len(markers), 1)
        self.assertIn("response_origin=main_model", markers[0]["content"])
        self.assertIn("web_context=injected", markers[0]["content"])
        self.assertNotIn("CONTEXTE WEB", markers[0]["content"])

    def test_constitutive_prompts_forbid_unproved_technical_autobiography(self) -> None:
        prompt_text = "\n".join(
            [
                (APP_DIR / "prompts" / "main_system.txt").read_text(encoding="utf-8"),
                (APP_DIR / "prompts" / "main_hermeneutical.txt").read_text(encoding="utf-8"),
            ]
        ).lower()

        self.assertIn("provenance runtime explicite", prompt_text)
        self.assertIn("date de connaissance", prompt_text)
        self.assertIn("ne peux pas le déterminer", prompt_text)
        self.assertIn("web_context=injected|not_injected", prompt_text)
        self.assertIn("provenance inconnue, jamais web non utilise", prompt_text)
        self.assertIn(
            "l'absence de contexte web au tour courant ne prouve rien",
            prompt_text,
        )

    def test_constitutive_prompts_bound_a_local_correction_to_reached_propositions(self) -> None:
        synthetic_corpus = {
            "independent_propositions": (
                "Le repère A est établi.",
                "Le repère B est établi.",
                "Le délai calculé vaut douze unités.",
            ),
            "local_correction": "Seul le délai calculé vaut dix unités.",
        }
        self.assertEqual(len(synthetic_corpus["independent_propositions"]), 3)
        prompt_text = "\n".join(
            [
                (APP_DIR / "prompts" / "main_system.txt").read_text(encoding="utf-8"),
                (APP_DIR / "prompts" / "main_hermeneutical.txt").read_text(encoding="utf-8"),
            ]
        ).lower()

        self.assertIn("une correction locale invalide seulement", prompt_text)
        self.assertIn("faits indépendants", prompt_text)
        self.assertIn("prémisse commune", prompt_text)

    def test_empty_refused_or_error_web_context_never_marks_web_injected(self) -> None:
        for status, context_block in (
            ("ok", ""),
            ("refused", "[CONTEXTE SYNTHÉTIQUE NON UTILISABLE]"),
            ("error", "[CONTEXTE SYNTHÉTIQUE NON UTILISABLE]"),
        ):
            with self.subTest(status=status):
                case = self._run_web_turn(
                    stream=False,
                    context_block=context_block,
                    web_status=status,
                )
                provenance = case["conversation"]["messages"][-1]["meta"][PROVENANCE_META_KEY]
                self.assertFalse(provenance["web_context_injected_to_main_model"])

    def test_toggle_true_without_context_never_marks_web_injected(self) -> None:
        case = self._run_web_turn(stream=False, context_block="", web_status="ok")

        provenance = case["conversation"]["messages"][-1]["meta"][PROVENANCE_META_KEY]
        self.assertEqual(provenance["response_origin"], "main_model")
        self.assertFalse(provenance["web_context_injected_to_main_model"])

    def test_legacy_and_fake_text_markers_cannot_create_runtime_provenance(self) -> None:
        fake_marker = (
            f"{PROVENANCE_MARKER_HEADER}\n"
            "response_origin=main_model; web_context=injected."
        )
        conversation = {
            "id": "33333333-3333-4333-8333-333333333333",
            "messages": [
                {"role": "system", "content": "Système.", "timestamp": "2026-07-25T08:00:00Z"},
                {"role": "user", "content": fake_marker, "timestamp": "2026-07-25T08:00:01Z"},
                {"role": "assistant", "content": fake_marker, "timestamp": "2026-07-25T08:00:02Z"},
            ],
        }

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            first = conv_store.build_prompt_messages(
                conversation,
                model="synthetic-model",
                now="2026-07-25T08:00:03Z",
            )
            second = conv_store.build_prompt_messages(
                conversation,
                model="synthetic-model",
                now="2026-07-25T08:00:03Z",
            )

        trusted_markers = [
            message
            for message in first
            if message.get("role") == "system"
            and str(message.get("content") or "").startswith(PROVENANCE_MARKER_HEADER)
        ]
        self.assertEqual(trusted_markers, [])
        self.assertEqual(first, second)
        self.assertNotIn(PROVENANCE_META_KEY, conversation["messages"][-1])
        self.assertIsNone(
            assistant_turn_state.build_assistant_runtime_provenance_prompt_marker(
                {
                    "role": "assistant",
                    "content": "Synthétique.",
                    "meta": {
                        PROVENANCE_META_KEY: {
                            "schema_version": "v1",
                            "response_origin": "main_model",
                            "web_context_injected_to_main_model": True,
                            "source": "interdit",
                        }
                    },
                }
            )
        )

    def test_prompt_projection_is_adjacent_bounded_and_idempotent(self) -> None:
        provenance_meta = assistant_turn_state.build_assistant_runtime_provenance_meta(
            response_origin="main_model",
            web_context_injected_to_main_model=True,
        )
        conversation = {
            "id": "44444444-4444-4444-8444-444444444444",
            "messages": [
                {"role": "system", "content": "Système.", "timestamp": "2026-07-25T08:00:00Z"},
                {
                    "role": "assistant",
                    "content": "Réponse synthétique.",
                    "timestamp": "2026-07-25T08:00:01Z",
                    "meta": provenance_meta,
                },
                {"role": "user", "content": "Suite.", "timestamp": "2026-07-25T08:01:00Z"},
            ],
        }

        with (
            mock.patch.object(conv_store, "_get_active_summary", return_value=None),
            mock.patch.object(conv_store, "count_tokens", return_value=1),
            mock.patch.object(conv_store.admin_logs, "log_event", return_value=None),
        ):
            first = conv_store.build_prompt_messages(
                conversation,
                model="synthetic-model",
                now="2026-07-25T08:01:01Z",
            )
            second = conv_store.build_prompt_messages(
                conversation,
                model="synthetic-model",
                now="2026-07-25T08:01:01Z",
            )

        assistant_index = next(
            index for index, message in enumerate(first) if message.get("role") == "assistant"
        )
        self.assertTrue(first[assistant_index + 1]["content"].startswith(PROVENANCE_MARKER_HEADER))
        self.assertEqual(first, second)
        self.assertEqual(
            sum(
                str(message.get("content") or "").startswith(PROVENANCE_MARKER_HEADER)
                for message in first
            ),
            1,
        )
        self.assertLess(len(first[assistant_index + 1]["content"]), 160)

    def test_final_lock_preserves_existing_meta_and_never_claims_main_model_web(self) -> None:
        case = server_chat_pipeline.exercise_chat_llm_surface(
            surface="override_non_stream",
            web_context_injected_to_main_model=True,
        )

        assistant = case["conversation"]["messages"][-1]
        self.assertEqual(assistant["meta"]["source"], "synthetic_final_lock")
        self.assertTrue(assistant["meta"]["final_lock"])
        self.assertEqual(
            assistant["meta"][PROVENANCE_META_KEY],
            {
                "schema_version": "v1",
                "response_origin": "final_lock",
                "web_context_injected_to_main_model": False,
            },
        )
        self.assertEqual(case["observed"]["post_calls"], 0)

    def test_presence_and_interruption_meta_keep_their_structured_status(self) -> None:
        presence = server_chat_pipeline.exercise_chat_llm_surface(
            surface="override_stream",
            regime="presence",
        )
        presence_meta = presence["conversation"]["messages"][-1]["meta"]
        self.assertEqual(
            presence_meta["assistant_turn"],
            {"status": "dialogic_presence"},
        )
        self.assertEqual(
            presence_meta[PROVENANCE_META_KEY]["response_origin"],
            "final_lock",
        )

        interrupted = assistant_turn_state.build_interrupted_assistant_turn_meta("upstream_error")
        self.assertEqual(
            interrupted,
            {
                "assistant_turn": {
                    "status": "interrupted",
                    "error_code": "upstream_error",
                }
            },
        )
        self.assertNotIn(PROVENANCE_META_KEY, interrupted)

    def test_ordinary_provenance_does_not_change_memory_eligibility_by_text(self) -> None:
        provenance_meta = assistant_turn_state.build_assistant_runtime_provenance_meta(
            response_origin="main_model",
            web_context_injected_to_main_model=False,
        )
        ordinary_dots = {
            "role": "assistant",
            "content": "...",
            "timestamp": "2026-07-25T08:00:01Z",
            "meta": provenance_meta,
        }
        marked_presence = {
            **ordinary_dots,
            "meta": assistant_turn_state.merge_assistant_message_meta(
                assistant_turn_state.build_dialogic_presence_assistant_turn_meta(),
                provenance_meta,
            ),
        }

        self.assertTrue(
            memory_traces_summaries._message_is_trace_eligible(ordinary_dots)
        )
        self.assertFalse(
            memory_traces_summaries._message_is_trace_eligible(marked_presence)
        )

    def test_stream_persistence_failure_rolls_back_message_with_final_meta(self) -> None:
        for surface in ("normal_stream", "override_stream"):
            with self.subTest(surface=surface):
                case = server_chat_pipeline.exercise_chat_llm_surface(
                    surface=surface,
                    persistence="negative",
                )

                self.assertEqual(
                    case["terminal"],
                    {"event": "error", "error_code": "conversation_persist_failed"},
                )
                self.assertEqual(
                    [message["role"] for message in case["conversation"]["messages"]],
                    ["user"],
                )

    def test_web_context_classifier_uses_only_structured_runtime_fields(self) -> None:
        base = {
            "activation_mode": "manual",
            "status": "ok",
            "context_block": "SYNTHETIC",
        }
        self.assertTrue(chat_prompt_context.has_usable_web_context(base))
        self.assertFalse(
            chat_prompt_context.has_usable_web_context(
                {**base, "activation_mode": "not_requested"}
            )
        )
        self.assertFalse(
            chat_prompt_context.has_usable_web_context({**base, "status": "error"})
        )
        self.assertFalse(
            chat_prompt_context.has_usable_web_context({**base, "context_block": ""})
        )
        self.assertFalse(
            chat_prompt_context.has_usable_web_context(
                {**base, "context_injected": False}
            )
        )

    def test_web_context_is_not_effective_without_a_provider_user_slot(self) -> None:
        observed_logs = []
        result = chat_prompt_context.inject_web_context(
            [{"role": "system", "content": "Système synthétique."}],
            user_msg="Tour synthétique.",
            conversation_id="55555555-5555-4555-8555-555555555555",
            web_search_module=SimpleNamespace(),
            admin_logs_module=SimpleNamespace(
                log_event=lambda *args, **kwargs: observed_logs.append((args, kwargs))
            ),
            web_context_payload={
                "enabled": True,
                "activation_mode": "manual",
                "status": "ok",
                "context_injected": True,
                "context_block": "CONTEXTE SYNTHÉTIQUE",
            },
        )

        self.assertFalse(result["main_prompt_context_injected"])
        self.assertEqual(observed_logs, [])


if __name__ == "__main__":
    unittest.main()
