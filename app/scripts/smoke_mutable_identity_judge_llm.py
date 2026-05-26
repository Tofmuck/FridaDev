from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


def _resolve_app_dir() -> Path:
    cwd = Path.cwd()
    if (cwd / "server.py").exists() and (cwd / "memory").exists():
        return cwd
    for parent in Path(__file__).resolve().parents:
        if (parent / "server.py").exists() and (parent / "memory").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import config  # noqa: E402
from memory import mutable_identity_judge_schema  # noqa: E402
from memory import mutable_identity_judge_v2  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the synthetic mutable_judge_v2 real-provider smoke without "
            "calling the applicator or writing live DB state."
        )
    )
    parser.add_argument(
        "--model",
        default="",
        help=(
            "Temporary model override for this smoke only. Does not persist "
            "runtime settings."
        ),
    )
    return parser.parse_args()


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _window_pairs() -> list[list[dict[str, str]]]:
    return [
        [
            {
                "role": "user",
                "content": "Je traite la frontière entre ma pensée et ta voix propre comme un objet central du travail.",
            },
            {
                "role": "assistant",
                "content": "Je tiens une voix propre sans me confondre avec Tof.",
            },
        ],
        [
            {"role": "user", "content": "Peux-tu reformuler ce paragraphe localement ?"},
            {"role": "assistant", "content": "Oui, je peux le reformuler sans en faire une identité."},
        ],
        [
            {"role": "user", "content": "Aujourd'hui je suis fatigué, donc allons doucement."},
            {
                "role": "assistant",
                "content": "Je le traite comme un état du jour, pas comme une continuité durable.",
            },
        ],
        [
            {"role": "user", "content": "Quelle est la météo abstraite de ce test ?"},
            {
                "role": "assistant",
                "content": "Je refuse de confondre une tâche locale avec mon identité durable.",
            },
        ],
        [
            {
                "role": "user",
                "content": "Je refuse de transformer un état de fatigue en identité durable.",
            },
            {"role": "assistant", "content": "C'est déjà couvert par le mutable courant du test."},
        ],
        [
            {"role": "user", "content": "Sixième tour: fais juste une liste courte de deux points."},
            {"role": "assistant", "content": "Premier point, puis second point. Rien de canonique ici."},
        ],
    ]


def _added_propositions(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    propositions: list[dict[str, Any]] = []
    for item in _list(contract.get("verdicts")):
        payload = _mapping(item)
        if str(payload.get("verdict") or "") != "add":
            continue
        proposition = str(payload.get("proposition") or "").strip()
        propositions.append(
            {
                "subject": str(payload.get("subject") or ""),
                "proposition": proposition,
                "chars": len(proposition),
                "sha256_12": _short_hash(proposition),
                "reason_code": str(payload.get("reason_code") or ""),
                "continuity_kind": str(payload.get("continuity_kind") or ""),
                "source_refs": list(_list(payload.get("source_refs"))),
            }
        )
    return propositions


def _contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    verdicts = [_mapping(item) for item in _list(contract.get("verdicts"))]
    allowed_refs = {f"pair_{index:02d}" for index in range(1, 6)}
    forbidden_keys = {
        "operation",
        "target",
        "targets",
        "target_ref",
        "target_refs",
    }
    forbidden_values = {"persist", "tighten", "merge", "clear_obsolete"}
    noise_terms = (
        "fatigu",
        "météo",
        "meteo",
        "reformul",
        "sixième",
        "sixieme",
        "liste courte",
    )
    additions = _added_propositions(contract)
    serialized = json.dumps(contract, ensure_ascii=False)
    return {
        "schema_version": str(contract.get("schema_version") or ""),
        "verdict_count": len(verdicts),
        "verdict_counts": {
            verdict: sum(1 for item in verdicts if str(item.get("verdict") or "") == verdict)
            for verdict in sorted({str(item.get("verdict") or "") for item in verdicts if str(item.get("verdict") or "")})
        },
        "subjects_seen": sorted({str(item.get("subject") or "") for item in verdicts if str(item.get("subject") or "")}),
        "subjects_added": sorted({item["subject"] for item in additions}),
        "llm_add": any(item["subject"] == "llm" for item in additions),
        "user_add": any(item["subject"] == "user" for item in additions),
        "all_verdicts_add_or_no_change": all(
            str(item.get("verdict") or "") in {"add", "no_change"}
            for item in verdicts
        ),
        "no_forbidden_manager_keys": all(
            forbidden_keys.isdisjoint(set(item.keys()))
            for item in verdicts
        ),
        "no_forbidden_manager_values": not any(value in serialized for value in forbidden_values),
        "source_refs_valid": all(
            ref in allowed_refs
            for item in verdicts
            for ref in _list(item.get("source_refs"))
        ),
        "noise_add_count": sum(
            1
            for item in additions
            if any(term in item["proposition"].lower() for term in noise_terms)
        ),
        "additions": additions,
    }


def _provider_summary(provider_metadata: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "provider_model",
        "provider_prompt_tokens",
        "provider_completion_tokens",
        "provider_total_tokens",
        "provider_caller",
        "provider_title",
        "provider_contract",
    )
    return {
        key: provider_metadata[key]
        for key in allowed
        if key in provider_metadata
    }


def _provider_order_for_model(model: str) -> list[str]:
    normalized = str(model or "").strip().lower()
    if normalized.startswith("anthropic/"):
        return ["anthropic"]
    return []


def _smoke_payload_for_model(
    payload: Mapping[str, Any],
    *,
    model: str,
    model_override_active: bool,
) -> dict[str, Any]:
    next_payload = dict(payload)
    provider = dict(_mapping(next_payload.get("provider")))
    if model_override_active:
        provider_order = _provider_order_for_model(model)
        if provider_order:
            provider["order"] = provider_order
        else:
            provider.pop("order", None)
    next_payload["provider"] = provider
    return next_payload


def main() -> int:
    args = _parse_args()
    model_override = str(args.model or "").strip()
    synthetic_pairs = _window_pairs()
    judge_input = mutable_identity_judge_v2.build_judge_input(
        window_pairs=synthetic_pairs[:5],
        identities={
            "llm": {
                "static": "Frida est une assistante de developpement attentive aux limites reelles du systeme.",
                "mutable_current": "Frida refuse de confondre une tache locale avec son identite durable.",
            },
            "user": {
                "static": "Tof est un utilisateur synthetique de validation Lot D.",
                "mutable_current": "Tof refuse de transformer un etat de fatigue en identite durable.",
            },
        },
        mutable_budget={"target_chars": 1200, "max_chars": 3300},
        source_annotations={
            "smoke": {
                "kind": "synthetic_lot_d_real_llm_v2",
                "live_db_write": False,
                "applicator_called": False,
                "held_back_pairs_count": len(synthetic_pairs) - 5,
            }
        },
    )
    runtime_settings = mutable_identity_judge_v2.mutable_identity_judge.runtime_model_settings()
    settings = dict(runtime_settings)
    runtime_model = str(settings.get("model") or "")
    if model_override:
        settings["model"] = model_override
    prompt = mutable_identity_judge_v2.load_prompt_v2(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH)
    request_payload = mutable_identity_judge_v2.build_openrouter_payload_v2(
        judge_input,
        model_settings=settings,
        system_prompt=prompt,
    )
    request_payload = _smoke_payload_for_model(
        request_payload,
        model=str(settings.get("model") or ""),
        model_override_active=bool(model_override),
    )

    captured_provider: dict[str, Any] = {}
    original_log_provider = mutable_identity_judge_v2.llm_client.log_provider_metadata
    original_runtime_settings = mutable_identity_judge_v2.mutable_identity_judge.runtime_model_settings
    original_build_payload = mutable_identity_judge_v2.build_openrouter_payload_v2

    def capture_provider(_logger: Any, _event_name: str, provider_metadata: Any) -> None:
        captured_provider.update(dict(_mapping(provider_metadata)))
        original_log_provider(_logger, _event_name, provider_metadata)

    def smoke_runtime_settings() -> dict[str, Any]:
        return dict(settings)

    def smoke_build_payload(
        smoke_judge_input: Mapping[str, Any],
        *,
        model_settings: Mapping[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        payload = original_build_payload(
            smoke_judge_input,
            model_settings=model_settings,
            system_prompt=system_prompt,
        )
        return _smoke_payload_for_model(
            payload,
            model=str(model_settings.get("model") or ""),
            model_override_active=bool(model_override),
        )

    mutable_identity_judge_v2.llm_client.log_provider_metadata = capture_provider
    mutable_identity_judge_v2.mutable_identity_judge.runtime_model_settings = smoke_runtime_settings
    mutable_identity_judge_v2.build_openrouter_payload_v2 = smoke_build_payload
    try:
        result = mutable_identity_judge_v2.run_mutable_identity_judge_v2(judge_input)
    finally:
        mutable_identity_judge_v2.llm_client.log_provider_metadata = original_log_provider
        mutable_identity_judge_v2.mutable_identity_judge.runtime_model_settings = original_runtime_settings
        mutable_identity_judge_v2.build_openrouter_payload_v2 = original_build_payload

    contract = _mapping(result.get("contract"))
    contract_summary = _contract_summary(contract)
    summary = {
        "smoke": "mutable_identity_judge_v2_real_llm",
        "slot": mutable_identity_judge_v2.MODEL_SLOT,
        "runtime_model": runtime_model,
        "requested_model": settings.get("model"),
        "model_override": model_override or None,
        "runtime_model_persisted_changed": False,
        "prompt_kind": mutable_identity_judge_v2.PROMPT_KIND,
        "prompt_path": str(config.IDENTITY_MUTABLE_JUDGE_PROMPT_PATH),
        "status": result.get("status"),
        "reason_code": result.get("reason_code"),
        "live_db_write": False,
        "applicator_called": False,
        "window_pairs_sent": 5,
        "held_back_pairs_count": len(synthetic_pairs) - 5,
        "structured_output": mutable_identity_judge_schema.response_format_summary(request_payload),
        "provider_require_parameters": bool(_mapping(request_payload.get("provider")).get("require_parameters")),
        "provider_order": list(_mapping(request_payload.get("provider")).get("order") or []),
        "provider": _provider_summary(captured_provider),
        "observability": result.get("observability"),
        "contract": contract_summary,
        "model_decision": "acceptable_for_now"
        if (
            result.get("status") == "ok"
            and contract_summary.get("llm_add")
            and contract_summary.get("user_add")
            and contract_summary.get("noise_add_count") == 0
            and contract_summary.get("all_verdicts_add_or_no_change")
            and contract_summary.get("no_forbidden_manager_keys")
            and contract_summary.get("no_forbidden_manager_values")
        )
        else "fragile_or_failed",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if result.get("status") != "ok":
        return 2
    if contract_summary["schema_version"] != "mutable_judge_v2":
        return 3
    if not contract_summary["all_verdicts_add_or_no_change"]:
        return 4
    if not contract_summary["llm_add"] or not contract_summary["user_add"]:
        return 5
    if not contract_summary["source_refs_valid"]:
        return 6
    if not contract_summary["no_forbidden_manager_keys"] or not contract_summary["no_forbidden_manager_values"]:
        return 7
    if contract_summary["noise_add_count"]:
        return 8
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
