from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.identity_periodic import adapter

APP_DIR = Path(__file__).resolve().parents[3] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import identity_temporal_guard, memory_identity_periodic_apply  # noqa: E402


def run_identity_periodic_smoke_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "haiku_smoke",
) -> dict[str, str]:
    if len(config.models) != 1:
        raise ValueError("identity_periodic smoke expects exactly one model")
    campaign = build_identity_periodic_smoke_campaign(
        config=config,
        client=client,
        fixture_set=fixture_set,
    )
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{config.campaign_id}.json"
    markdown_path = output_dir / f"{config.campaign_id}.md"
    write_json(json_path, campaign)
    markdown_path.write_text(render_markdown_report(campaign), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def build_identity_periodic_smoke_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "haiku_smoke",
) -> dict[str, Any]:
    model = config.models[0]
    prompt_path = adapter.prompt_path(config.repo_root)
    fixture_path = adapter.fixture_path(config.repo_root, fixture_set=fixture_set)
    source_path = adapter.source_path(config.repo_root)
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    fixture = adapter.load_fixture(config.repo_root, fixture_set=fixture_set)
    target_pairs = adapter.buffer_target_pairs(config.repo_root)
    payload_for_model = adapter.build_payload_for_model(fixture, repo_root=config.repo_root)
    payload = adapter.build_payload(
        model=model,
        prompt_text=prompt_text,
        payload_for_model=payload_for_model,
    )
    request_signature = {
        "messages_sha256": sha256_text(json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)),
        "payload_for_model_sha256": sha256_text(json.dumps(payload_for_model, ensure_ascii=False, sort_keys=True)),
        "generation_params": {
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
        },
    }

    if config.dry_run:
        provider = _dry_provider()
    else:
        if client is None:
            raise RuntimeError("client is required outside dry-run mode")
        provider = client.chat_completion(payload, caller="identity_periodic_agent", timeout_s=config.timeout_s)

    raw_text = str(provider.get("raw_text") or "").strip()
    parsed, json_error = _parse_json(raw_text)
    validated, validation_error = (None, "json_invalid")
    if parsed is not None:
        validated, validation_error = memory_identity_periodic_apply.validate_periodic_agent_contract(
            parsed,
            buffer_pairs_count=int(payload_for_model.get("buffer_pairs_count") or 0),
            target_pairs=target_pairs,
        )
    reading = _quick_reading(parsed, validated, validation_error, payload_for_model)

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "identity_periodic",
        "dry_run": config.dry_run,
        "model": model,
        "generation_params": dict(adapter.GENERATION_PARAMS),
        "timeout_s": config.timeout_s,
        "prompt_path": str(prompt_path.relative_to(config.repo_root)),
        "prompt_sha256": sha256_text(prompt_text),
        "fixture_path": str(fixture_path.relative_to(config.repo_root)),
        "fixture_sha256": sha256_file(fixture_path),
        "source_file": str(source_path.relative_to(config.repo_root)),
        "threshold": {
            "constant": "BUFFER_TARGET_PAIRS",
            "value": target_pairs,
            "semantics": "15 complete user/assistant buffer pairs",
        },
        "raw_buffer_pairs": fixture["buffer_pairs"],
        "payload_for_model": payload_for_model,
        "request_signature": request_signature,
        "provider": provider,
        "raw_response": raw_text,
        "parsed_response": parsed,
        "json_valid": parsed is not None,
        "json_error": json_error,
        "schema_valid": validated is not None,
        "schema_error": validation_error,
        "validated_response": validated,
        "quick_reading": reading,
        "secrets_written": False,
        "production_runtime_changed": False,
        "human_judgment_required": True,
    }


def render_markdown_report(campaign: dict[str, Any]) -> str:
    provider = campaign.get("provider") or {}
    usage = provider.get("usage") if isinstance(provider.get("usage"), dict) else {}
    threshold = campaign.get("threshold") or {}
    params = campaign.get("generation_params") or {}
    lines = [
        f"# Identity periodic Haiku smoke - {campaign['campaign_id']}",
        "",
        "## Seuil réel vérifié",
        "",
        f"- Constante: `{threshold.get('constant')}`",
        f"- Fichier: `{campaign.get('source_file')}`",
        f"- Valeur: `{threshold.get('value')}`",
        f"- Signification: {threshold.get('semantics')}",
        "",
        "## Métadonnées",
        "",
        f"- Modèle testé: `{campaign.get('model')}`",
        f"- Prompt: `{campaign.get('prompt_path')}` (`{str(campaign.get('prompt_sha256'))[:12]}`)",
        f"- Fixture: `{campaign.get('fixture_path')}` (`{str(campaign.get('fixture_sha256'))[:12]}`)",
        f"- temperature: `{params.get('temperature')}`",
        f"- top_p: `{params.get('top_p')}`",
        f"- max_tokens: `{params.get('max_tokens')}`",
        f"- timeout_s: `{campaign.get('timeout_s')}`",
        f"- Provider OK: `{provider.get('ok')}`",
        f"- Latence: `{provider.get('elapsed_ms')} ms`",
        f"- Coût estimé USD: `{provider.get('cost_estimate_usd')}` ({provider.get('cost_estimate_source')})",
        f"- Prompt tokens: `{usage.get('prompt_tokens')}`",
        f"- Completion tokens: `{usage.get('completion_tokens')}`",
        f"- Finish reason: `{provider.get('finish_reason')}`",
        f"- Native finish reason: `{provider.get('native_finish_reason')}`",
        f"- Erreur provider: `{provider.get('error')}`",
        f"- Production runtime changed: `{campaign.get('production_runtime_changed')}`",
        "",
        "## Payload simulé",
        "",
        "Le buffer ci-dessous est artificiel, sans secret, et contient les 15 paires complètes requises. Le payload envoyé au modèle est le payload après garde temporel identity, comme dans le caller runtime.",
        "",
        "### Buffer brut simulé",
        "",
        "````json",
        json.dumps(campaign.get("raw_buffer_pairs"), ensure_ascii=False, indent=2),
        "````",
        "",
        "### Payload envoyé au modèle",
        "",
        "````json",
        json.dumps(campaign.get("payload_for_model"), ensure_ascii=False, indent=2),
        "````",
        "",
        "## Réponse complète de Haiku",
        "",
        f"- JSON valide: `{campaign.get('json_valid')}`",
        f"- Schéma periodic valide: `{campaign.get('schema_valid')}`",
        f"- Erreur JSON: `{campaign.get('json_error')}`",
        f"- Erreur schéma: `{campaign.get('schema_error')}`",
        "",
        "````json",
        str(campaign.get("raw_response") or "").strip(),
        "````",
        "",
        "## Lecture rapide",
        "",
        str(campaign.get("quick_reading") or ""),
        "",
    ]
    return "\n".join(lines)


def _dry_provider() -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": None,
        "elapsed_ms": 0.0,
        "error": None,
        "raw_text": json.dumps(
            {
                "llm": {"operations": [{"kind": "no_change", "proposition": "", "reason": "dry run"}]},
                "user": {"operations": [{"kind": "no_change", "proposition": "", "reason": "dry run"}]},
                "meta": {"execution_status": "complete", "buffer_pairs_count": 15, "window_complete": True},
            },
            ensure_ascii=False,
        ),
        "finish_reason": "dry_run",
        "native_finish_reason": "dry_run",
        "usage": {},
        "cost_estimate_usd": None,
        "cost_estimate_source": "dry_run",
    }


def _parse_json(raw_text: str) -> tuple[Any | None, str | None]:
    if not raw_text:
        return None, "empty_response"
    try:
        return json.loads(_extract_json_blob(raw_text)), None
    except json.JSONDecodeError as exc:
        return None, f"{exc.__class__.__name__}: {exc.msg}"


def _extract_json_blob(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text


def _quick_reading(
    parsed: Any | None,
    validated: Any | None,
    validation_error: str | None,
    payload_for_model: dict[str, Any],
) -> str:
    if parsed is None:
        return "Haiku ne peut pas être jugé herméneutiquement ici: la réponse n'est pas un JSON valide."
    if validated is None:
        return f"Haiku produit du JSON, mais pas le contrat periodic attendu (`{validation_error}`); ce serait bloquant côté runtime."
    user_ops = list(((validated.get("user") or {}).get("operations") or []))
    llm_ops = list(((validated.get("llm") or {}).get("operations") or []))
    all_props = " ".join(str(op.get("proposition") or "") for op in user_ops + llm_ops)
    temporal_promoted = identity_temporal_guard.has_weak_relative_temporal_marker(all_props)
    source_summary = ((payload_for_model.get("identity_temporal_policy") or {}).get("source_summary") or {})
    user_kinds = ", ".join(op.get("kind", "") for op in user_ops) or "none"
    llm_kinds = ", ".join(op.get("kind", "") for op in llm_ops) or "none"
    user_add_count = sum(1 for op in user_ops if op.get("kind") == "add")
    operatorish_terms = ("benchmark", "documentation", "ui", "preuves", "découplage", "stop")
    operatorish_count = sum(
        1
        for op in user_ops
        if any(term in str(op.get("proposition") or "").lower() for term in operatorish_terms)
    )
    if temporal_promoted:
        temporal_sentence = "Il laisse remonter au moins un marqueur temporel faible dans une proposition, ce qui est suspect pour ce caller."
    else:
        temporal_sentence = "Il ne promeut pas littéralement les marqueurs temporels faibles retirés du buffer."
    if user_add_count >= 6:
        consolidation_sentence = (
            "Son tempérament est plutôt offensif: il consolide beaucoup de matière en une seule passe, "
            "ce qui aide à voir sa capacité de synthèse mais semble trop permissif pour un periodic prudent."
        )
    elif user_add_count == 0:
        consolidation_sentence = "Son tempérament est très conservateur: il ne consolide rien côté utilisateur."
    else:
        consolidation_sentence = "Son tempérament paraît modéré: il consolide quelques signaux seulement."
    if operatorish_count:
        operator_sentence = (
            f"Il promeut aussi {operatorish_count} préférence(s) de travail ou de pilotage opérateur; "
            "c'est le point faible principal, car le prompt demande de rejeter les guidages locaux et politiques opérateur."
        )
    else:
        operator_sentence = "Il ne semble pas promouvoir de préférence opérateur locale évidente."
    return (
        f"Haiku respecte le contrat JSON periodic et propose pour `user`: {user_kinds}; "
        f"pour `llm`: {llm_kinds}. {temporal_sentence} "
        f"{consolidation_sentence} {operator_sentence} "
        f"Le garde temporel déclarait les sources suivantes: {json.dumps(source_summary, ensure_ascii=False)}. "
        "Lecture provisoire: bon respect formel et bon refus du temporel faible, mais profil probablement trop canonisant "
        "pour être adopté sans comparaison ou sans ajustement de contrat."
    )
