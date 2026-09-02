from __future__ import annotations

import copy
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_memory_flow
from identity import identity
from identity import static_identity_content
from memory import memory_identity_periodic_agent
from memory import mutable_identity_judge_v2


def _event_payloads(events: list[tuple[str, dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    return [payload for event, payload in events if event == name]


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _mutable_verdict(
    *,
    subject: str,
    proposition: str,
    reason_code: str,
    continuity_kind: str,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "subject": subject,
        "verdict": "add",
        "proposition": proposition,
        "reason_code": reason_code,
        "continuity_kind": continuity_kind,
        "source_refs": [source_ref],
        "guard_notes": ["synthetic_final_validation"],
    }


def _mutable_contract(*verdicts: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "mutable_judge_v2",
        "meta": {
            "execution_status": "complete",
            "window_pairs_count": memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            "window_complete": True,
        },
        "verdicts": list(verdicts),
    }


class _ConversationCrashStore:
    def __init__(self) -> None:
        self.mutable: dict[str, dict[str, Any]] = {}
        self.staging: dict[str, dict[str, Any]] = {}
        self.persisted_entries: list[tuple[str, list[dict[str, Any]]]] = []
        self.upsert_calls: list[tuple[str, str, str, str]] = []
        self.audit: list[dict[str, Any]] = []

    def persist_identity_entries(self, conversation_id: str, entries: list[dict[str, Any]]) -> None:
        self.persisted_entries.append((conversation_id, list(entries)))

    def preview_identity_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(entries)

    def record_identity_evidence(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def get_mutable_identity(
        self,
        subject: str,
        *,
        strict: bool = False,
    ) -> dict[str, Any] | None:
        item = self.mutable.get(subject)
        return copy.deepcopy(item) if item is not None else None

    def apply_mutable_identity_subject_updates(
        self,
        updates: list[dict[str, Any]],
        **_staging_fence: Any,
    ) -> list[dict[str, Any]] | None:
        next_mutable = copy.deepcopy(self.mutable)
        next_audit = copy.deepcopy(self.audit)
        next_upserts = list(self.upsert_calls)
        results: list[dict[str, Any]] = []
        for update in list(updates or []):
            subject = str(update.get("subject") or "")
            mutation_kind = str(update.get("mutation_kind") or "")
            old_content = str((next_mutable.get(subject) or {}).get("content") or "")
            if mutation_kind == "set":
                content = str(update.get("content") or "")
                payload = {
                    "subject": subject,
                    "content": content,
                    "source_trace_id": update.get("source_trace_id"),
                    "updated_by": str(update.get("updated_by") or "system"),
                    "update_reason": str(update.get("update_reason") or ""),
                    "created_ts": "2026-05-25T00:00:00Z",
                    "updated_ts": "2026-05-25T00:00:00Z",
                }
                next_mutable[subject] = payload
                next_upserts.append((subject, content, payload["updated_by"], payload["update_reason"]))
                next_audit.append(
                    {
                        "subject": subject,
                        "mutation_kind": "set",
                        "actor": payload["updated_by"],
                        "reason_code": str(update.get("audit_reason_code") or ""),
                        "old_chars": len(old_content),
                        "new_chars": len(content),
                    }
                )
                results.append(copy.deepcopy(payload))
                continue
            if mutation_kind == "clear":
                old = next_mutable.pop(subject, None)
                if old is None:
                    return None
                next_audit.append(
                    {
                        "subject": subject,
                        "mutation_kind": "clear",
                        "actor": str(update.get("updated_by") or "system"),
                        "reason_code": str(update.get("audit_reason_code") or ""),
                        "old_chars": len(old_content),
                        "new_chars": 0,
                    }
                )
                results.append(copy.deepcopy(old))
                continue
            return None
        self.mutable = next_mutable
        self.upsert_calls = next_upserts
        self.audit = next_audit
        return results

    def get_identity_staging_state(self, conversation_id: str) -> dict[str, Any] | None:
        state = self.staging.get(conversation_id)
        return copy.deepcopy(state) if state is not None else None

    def append_identity_staging_pair(
        self,
        conversation_id: str,
        pair: list[dict[str, Any]],
        *,
        target_pairs: int = memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
    ) -> dict[str, Any] | None:
        state = copy.deepcopy(
            self.staging.get(
                conversation_id,
                {
                    "conversation_id": conversation_id,
                    "buffer_pairs": [],
                    "buffer_pairs_count": 0,
                    "buffer_target_pairs": int(target_pairs),
                    "auto_canonization_suspended": False,
                    "last_agent_status": "buffering",
                    "last_agent_reason": None,
                    "last_agent_run_ts": None,
                },
            )
        )
        current_pairs = list(state.get("buffer_pairs") or [])
        if not current_pairs and state.get("last_agent_status") in {
            "applied",
            "completed_no_change",
            "completed_with_open_tension",
            "not_run",
        }:
            state["last_agent_status"] = "buffering"
            state["last_agent_reason"] = None
        if len(current_pairs) >= int(target_pairs):
            state["buffer_pairs"] = current_pairs[: int(target_pairs)]
        else:
            state["buffer_pairs"] = current_pairs + [copy.deepcopy({"user": pair[0], "assistant": pair[1]})]
        state["buffer_pairs_count"] = len(state["buffer_pairs"])
        state["buffer_target_pairs"] = int(target_pairs)
        state["buffer_frozen"] = state["buffer_pairs_count"] >= int(target_pairs)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def mark_identity_staging_status(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = "",
        touch_run_ts: bool = False,
        auto_canonization_suspended: bool | None = None,
        **_expected: Any,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state["last_agent_status"] = status
        state["last_agent_reason"] = reason or None
        if touch_run_ts:
            state["last_agent_run_ts"] = "2026-05-25T00:00:00Z"
        if auto_canonization_suspended is not None:
            state["auto_canonization_suspended"] = bool(auto_canonization_suspended)
        state["transition_applied"] = True
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def identity_staging_processing_lock(
        self,
        _conversation_id: str,
        _window_fingerprint: str,
    ) -> Any:
        return nullcontext(True)

    def clear_identity_staging_buffer(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = "",
        auto_canonization_suspended: bool = False,
        next_pair: list[dict[str, Any]] | None = None,
        **_expected: Any,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state["buffer_pairs"] = (
            [{"user": copy.deepcopy(next_pair[0]), "assistant": copy.deepcopy(next_pair[1])}]
            if next_pair is not None
            else []
        )
        state["buffer_pairs_count"] = len(state["buffer_pairs"])
        state["buffer_frozen"] = False
        state["last_agent_status"] = status
        state["last_agent_reason"] = reason or None
        state["last_agent_run_ts"] = "2026-05-25T00:00:00Z"
        state["auto_canonization_suspended"] = bool(auto_canonization_suspended)
        state["transition_applied"] = True
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)


class MutableIdentityJudgeFinalValidationTests(unittest.TestCase):
    def test_conversation_crash_test_runs_judge_first_pipeline_without_live_db_pollution(self) -> None:
        conversation_id = "conv-lot-c-mutable-add-only-crash-test"
        existing_llm_mutable = "Frida refuse de confondre une tache locale avec son identite durable."
        existing_user_mutable = "Tof refuse de transformer un etat de fatigue en identite durable."
        llm_proposition = "Frida tient une voix propre sans se confondre avec Tof."
        user_proposition = "Tof traite la frontiere entre sa pensee et la voix propre de Frida comme un objet central du travail."
        conversation = [
            [
                {
                    "role": "user",
                    "content": "Je traite la frontiere entre ma pensee et ta voix propre comme un objet central du travail.",
                },
                {
                    "role": "assistant",
                    "content": "Je tiens une voix propre sans me confondre avec toi.",
                },
            ],
            [
                {"role": "user", "content": "Peux-tu reformuler ce paragraphe localement ?"},
                {"role": "assistant", "content": "Oui, je peux le reformuler sans en faire une identite."},
            ],
            [
                {"role": "user", "content": "Je refuse de transformer un etat de fatigue en identite durable."},
                {"role": "assistant", "content": "C'est deja couvert par le mutable utilisateur de ce test."},
            ],
            [
                {"role": "user", "content": "Quelle est la meteo abstraite de ce test ?"},
                {
                    "role": "assistant",
                    "content": "Je refuse de confondre une tache locale avec mon identite durable.",
                },
            ],
            [
                {"role": "user", "content": "Aujourd'hui je suis fatigue, donc allons doucement."},
                {"role": "assistant", "content": "Je le traite comme un etat du jour, pas comme une continuite durable."},
            ],
            [
                {"role": "user", "content": "Sixieme tour: fais juste une liste courte de deux points."},
                {"role": "assistant", "content": "Premier point, puis second point. Rien de canonique ici."},
            ],
        ]
        contract = _mutable_contract(
            _mutable_verdict(
                subject="llm",
                proposition=llm_proposition,
                reason_code="explicit_frida_self_definition_continuity",
                continuity_kind="posture",
                source_ref="pair_01",
            ),
            _mutable_verdict(
                subject="user",
                proposition=user_proposition,
                reason_code="explicit_self_definition_continuity",
                continuity_kind="identity",
                source_ref="pair_01",
            ),
        )
        contract["schema_version"] = "mutable_judge_v2"
        validated_contract, validation_reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(contract)
        self.assertIsNone(validation_reason or None)
        self.assertIsNotNone(validated_contract)

        events: list[tuple[str, dict[str, Any]]] = []
        chat_events: list[tuple[str, dict[str, Any]]] = []
        branch_events: list[tuple[str, str]] = []
        judge_inputs: list[dict[str, Any]] = []
        store = _ConversationCrashStore()

        def fake_run_mutable_identity_judge(payload: dict[str, Any]) -> dict[str, Any]:
            judge_inputs.append(copy.deepcopy(payload))
            return {
                "status": "ok",
                "reason_code": "judge_complete",
                "contract": copy.deepcopy(validated_contract),
                "observability": mutable_identity_judge_v2.build_judge_observability_v2(validated_contract or {}),
            }

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [],
            run_mutable_identity_judge=fake_run_mutable_identity_judge,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        original_llm_static = identity.load_llm_identity
        original_user_static = identity.load_user_identity
        original_get_mutable = identity._get_mutable_identity
        original_static_source = identity._safe_static_identity_source
        original_write_static = static_identity_content.write_static_identity_content
        store.mutable["llm"] = {
            "subject": "llm",
            "content": existing_llm_mutable,
            "source_trace_id": None,
            "updated_by": "seed",
            "update_reason": "seed",
        }
        store.mutable["user"] = {
            "subject": "user",
            "content": existing_user_mutable,
            "source_trace_id": None,
            "updated_by": "seed",
            "update_reason": "seed",
        }
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        identity.load_llm_identity = lambda: "Frida statique de validation Lot C."
        identity.load_user_identity = lambda: "Utilisateur statique de validation Lot C."
        identity._get_mutable_identity = store.get_mutable_identity
        identity._safe_static_identity_source = lambda field: f"test://{field}"
        static_identity_content.write_static_identity_content = (
            lambda *_args, **_kwargs: self.fail("static identity must not be written by mutable judge pipeline")
        )
        try:
            for pair in conversation:
                chat_memory_flow.record_identity_entries_for_mode(
                    conversation_id,
                    pair,
                    mode="enforced_all",
                    arbiter_module=arbiter_module,
                    memory_store_module=store,
                    admin_logs_module=admin_logs_module,
                )
            identity_input = identity.build_identity_input()
            identity_block, used_identity_ids = identity.build_identity_block()
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch
            identity.load_llm_identity = original_llm_static
            identity.load_user_identity = original_user_static
            identity._get_mutable_identity = original_get_mutable
            identity._safe_static_identity_source = original_static_source
            static_identity_content.write_static_identity_content = original_write_static

        self.assertEqual(len(judge_inputs), 1)
        judge_input = judge_inputs[0]
        self.assertEqual(judge_input["schema_version"], "mutable_identity_judge_input_v2")
        self.assertEqual(judge_input["identities"]["llm"]["static"], "Frida statique de validation Lot C.")
        self.assertEqual(judge_input["identities"]["user"]["static"], "Utilisateur statique de validation Lot C.")
        self.assertEqual(judge_input["identities"]["llm"]["mutable_current"], existing_llm_mutable)
        self.assertEqual(judge_input["identities"]["user"]["mutable_current"], existing_user_mutable)
        self.assertTrue(judge_input["judgment_rules"]["judge_reads_full_window"])
        self.assertTrue(judge_input["judgment_rules"]["python_must_not_score_identity"])
        self.assertTrue(judge_input["judgment_rules"]["static_writes_forbidden"])
        self.assertEqual(judge_input["judgment_rules"]["same_regime_for_subjects"], ["llm", "user"])
        self.assertEqual(judge_input["judgment_rules"]["allowed_verdicts"], ["add", "no_change"])
        self.assertNotIn("current_mutables", judge_input)
        self.assertEqual([item["id"] for item in judge_input["window_pairs"]], [f"pair_{index:02d}" for index in range(1, 6)])
        self.assertEqual(
            [
                [pair["user"]["content"], pair["assistant"]["content"]]
                for pair in judge_input["window_pairs"]
            ],
            [[turn[0]["content"], turn[1]["content"]] for turn in conversation[:5]],
        )
        self.assertIn("Aujourd'hui je suis fatigue", repr(judge_input))
        self.assertIn("meteo abstraite", repr(judge_input))
        self.assertIn(existing_llm_mutable, repr(judge_input))
        self.assertIn(existing_user_mutable, repr(judge_input))
        self.assertNotIn(conversation[5][0]["content"], repr(judge_input))

        self.assertEqual(store.mutable["llm"]["content"], f"{existing_llm_mutable}\n{llm_proposition}")
        self.assertEqual(store.mutable["user"]["content"], f"{existing_user_mutable}\n{user_proposition}")
        self.assertEqual(store.mutable["llm"]["content"].count(existing_llm_mutable), 1)
        self.assertEqual(store.mutable["user"]["content"].count(existing_user_mutable), 1)
        self.assertEqual(
            store.upsert_calls,
            [
                ("llm", f"{existing_llm_mutable}\n{llm_proposition}", "mutable_identity_judge_apply", "mutable_judge_add"),
                ("user", f"{existing_user_mutable}\n{user_proposition}", "mutable_identity_judge_apply", "mutable_judge_add"),
            ],
        )
        self.assertEqual(len(store.audit), 2)
        self.assertTrue(all(item["actor"] == "mutable_identity_judge_apply" for item in store.audit))
        self.assertNotIn("fatigue", store.mutable["llm"]["content"])
        self.assertNotIn("meteo", store.mutable["user"]["content"])
        self.assertNotIn("reformuler", store.mutable["llm"]["content"])
        self.assertNotIn("liste courte", store.mutable["user"]["content"])

        staging_state = store.get_identity_staging_state(conversation_id)
        self.assertIsNotNone(staging_state)
        self.assertEqual(staging_state["buffer_pairs_count"], 1)
        self.assertEqual(staging_state["buffer_target_pairs"], 5)
        self.assertFalse(staging_state["buffer_frozen"])
        self.assertEqual(staging_state["buffer_pairs"][0]["user"]["content"], conversation[5][0]["content"])

        apply_events = _event_payloads(events, "mutable_identity_judge_apply")
        self.assertEqual(len(apply_events), 6)
        self.assertEqual(apply_events[4]["status"], "ok")
        self.assertEqual(apply_events[4]["reason_code"], "applied")
        self.assertTrue(apply_events[4]["writes_applied"])
        self.assertEqual(apply_events[4]["runtime_pipeline"], "mutable_identity_judge_v2_add_only")
        self.assertFalse(apply_events[4]["score_first_writer_enabled"])
        self.assertEqual(apply_events[4]["promotion_count"], 0)
        self.assertEqual(apply_events[5]["status"], "buffering")
        self.assertFalse(apply_events[5]["writes_applied"])
        self.assertEqual([event for event, _payload in chat_events].count("mutable_identity_judge"), 1)
        mutable_judge_event = [payload for event, payload in chat_events if event == "mutable_identity_judge"][0]["payload"]
        self.assertEqual(mutable_judge_event["prompt_kind"], "mutable_identity_judge_v2")
        self.assertEqual(mutable_judge_event["runtime_pipeline"], "mutable_identity_judge_v2_add_only")
        self.assertEqual(mutable_judge_event["verdict_counts"], {"add": 2})
        self.assertNotIn("operation_kinds", mutable_judge_event)
        self.assertNotIn("persistent_operation_count", mutable_judge_event)
        self.assertNotIn("target_ref", mutable_judge_event)
        self.assertNotIn("target_refs", mutable_judge_event)
        self.assertEqual(mutable_judge_event["subjects_seen"], ["llm", "user"])
        self.assertEqual(mutable_judge_event["subjects_touched"], ["llm", "user"])
        self.assertEqual(mutable_judge_event["promotion_count"], 0)
        self.assertFalse(mutable_judge_event["score_first_writer_enabled"])
        self.assertEqual(branch_events, [])

        legacy_score_fields = {
            "strength",
            "frequency_norm",
            "recency_norm",
            "threshold_verdict",
            "strength_below_threshold",
        }
        self.assertTrue(legacy_score_fields.isdisjoint(_collect_keys(judge_input)))
        self.assertTrue(legacy_score_fields.isdisjoint(_collect_keys(apply_events)))
        self.assertTrue(legacy_score_fields.isdisjoint(_collect_keys([payload for _event, payload in chat_events])))

        sensitive_payloads = {
            "llm": llm_proposition,
            "user": user_proposition,
            "noise_today": "Aujourd'hui je suis fatigue",
            "noise_weather": "meteo abstraite",
            "window_text": conversation[0][0]["content"],
        }
        serialized_observability = repr({"admin": events, "chat": chat_events, "audit": store.audit})
        for text in sensitive_payloads.values():
            self.assertNotIn(text, serialized_observability)

        self.assertEqual(identity_input["frida"]["static"]["content"], "Frida statique de validation Lot C.")
        self.assertEqual(identity_input["user"]["static"]["content"], "Utilisateur statique de validation Lot C.")
        self.assertEqual(identity_input["frida"]["mutable"]["content"], f"{existing_llm_mutable}\n{llm_proposition}")
        self.assertEqual(identity_input["user"]["mutable"]["content"], f"{existing_user_mutable}\n{user_proposition}")
        self.assertIn(llm_proposition, identity_block)
        self.assertIn(user_proposition, identity_block)
        self.assertEqual(used_identity_ids, [])


if __name__ == "__main__":
    unittest.main()
