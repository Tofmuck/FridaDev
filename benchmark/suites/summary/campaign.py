from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.summary import adapter


def run_summary_human_reading_campaign(
    *,
    config: CampaignConfig,
    input_path: Path,
    client: OpenRouterClient | None,
    generation_params: dict[str, Any] | None = None,
) -> dict[str, str]:
    campaign = build_summary_human_reading_campaign(
        config=config,
        input_path=input_path,
        client=client,
        generation_params=generation_params,
    )
    output_dir = config.output_dir
    json_path = output_dir / f"{config.campaign_id}.json"
    markdown_path = output_dir / f"{config.campaign_id}.md"
    write_json(json_path, campaign)
    markdown_path.write_text(render_summary_human_reading_report(campaign), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def build_summary_human_reading_campaign(
    *,
    config: CampaignConfig,
    input_path: Path,
    client: OpenRouterClient | None,
    generation_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt = adapter.prompt_path(config.repo_root).read_text(encoding="utf-8").strip()
    material = adapter.load_material(input_path)
    prompt_sha = sha256_text(prompt)
    user_content = str(material["user_content"])
    resolved_generation_params = dict(generation_params or adapter.GENERATION_PARAMS)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for model in config.models:
        payload = adapter.build_payload(
            model=model,
            prompt_text=prompt,
            user_content=user_content,
            generation_params=resolved_generation_params,
        )
        request_signature = {
            "messages_sha256": sha256_text(json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)),
            "generation_params": {
                "temperature": payload.get("temperature"),
                "top_p": payload.get("top_p"),
                "max_tokens": payload.get("max_tokens"),
            },
        }
        if config.dry_run:
            provider = _dry_provider()
            summary_text = f"[dry-run summary for {model}]"
        else:
            if client is None:
                raise RuntimeError("client is required outside dry-run mode")
            provider = client.chat_completion(payload, caller="resumer", timeout_s=config.timeout_s)
            summary_text = str(provider.get("raw_text") or "").strip()

        summary_path = output_dir / f"{config.campaign_id}__{adapter.safe_model_slug(model)}.md"
        summary_path.write_text(
            render_summary_output_file(
                campaign_id=config.campaign_id,
                model=model,
                prompt_sha256=prompt_sha,
                material_sha256=str(material["user_content_sha256"]),
                provider=provider,
                summary_text=summary_text,
                generation_params=resolved_generation_params,
            ),
            encoding="utf-8",
        )
        completion_budget_reached = _completion_budget_reached(
            provider,
            resolved_generation_params["max_tokens"],
        )
        termination_assessment = _termination_assessment(provider, summary_text, completion_budget_reached)
        results.append(
            {
                "model": model,
                "ok": bool(provider.get("ok")) and bool(summary_text),
                "provider": _provider_public_metadata(provider),
                "request_signature": request_signature,
                "summary_file": _path_for_report(summary_path, config.repo_root),
                "summary_chars": len(summary_text),
                "summary_sha256": sha256_text(summary_text) if summary_text else None,
                "completion_budget_reached": completion_budget_reached,
                "termination_assessment": termination_assessment,
                "notes": _result_notes(provider, summary_text, completion_budget_reached, termination_assessment),
            }
        )

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "summary",
        "dry_run": config.dry_run,
        "models": config.models,
        "generation_params": resolved_generation_params,
        "timeout_s": config.timeout_s,
        "prompt_path": str(adapter.prompt_path(config.repo_root).relative_to(config.repo_root)),
        "prompt_sha256": prompt_sha,
        "material": adapter.material_public_metadata(material),
        "secrets_written": False,
        "raw_material_written": False,
        "human_judgment_required": True,
        "results": results,
    }


def render_summary_output_file(
    *,
    campaign_id: str,
    model: str,
    prompt_sha256: str,
    material_sha256: str,
    provider: dict[str, Any],
    summary_text: str,
    generation_params: dict[str, Any],
) -> str:
    usage = provider.get("usage") if isinstance(provider.get("usage"), dict) else {}
    completion_budget_reached = _completion_budget_reached(provider, generation_params.get("max_tokens"))
    lines = [
        f"# Résumé conversationnel - {model}",
        "",
        f"- Campaign: `{campaign_id}`",
        f"- Model: `{model}`",
        f"- Prompt SHA256: `{prompt_sha256}`",
        f"- Material SHA256: `{material_sha256}`",
        f"- Provider OK: `{bool(provider.get('ok'))}`",
        f"- Latency: `{provider.get('elapsed_ms')} ms`",
        f"- Prompt tokens: `{usage.get('prompt_tokens')}`",
        f"- Completion tokens: `{usage.get('completion_tokens')}`",
        f"- Total tokens: `{usage.get('total_tokens')}`",
        f"- Cost estimate USD: `{provider.get('cost_estimate_usd')}`",
        f"- Finish reason: `{provider.get('finish_reason')}`",
        f"- Native finish reason: `{provider.get('native_finish_reason')}`",
        f"- Completion budget reached: `{completion_budget_reached}`",
        f"- Termination assessment: `{_termination_assessment(provider, summary_text, completion_budget_reached)}`",
        "",
        "## Résumé brut",
        "",
        summary_text.strip(),
        "",
    ]
    return "\n".join(lines)


def render_summary_human_reading_report(campaign: dict[str, Any]) -> str:
    material = campaign.get("material") or {}
    lines = [
        f"# Benchmark summary - {campaign['campaign_id']}",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)",
        "- Goal: produire les résumés complets du même matériau réel pour lecture humaine.",
        "- Verdict: non attribué automatiquement; décision humaine de Tof requise.",
        "- Production runtime changed: `False`",
        "",
        "## Matériau",
        "",
        f"- Source kind: `{material.get('source_kind')}`",
        f"- Conversation id: `{material.get('conversation_id')}`",
        f"- Window: `{material.get('first_ts')}` -> `{material.get('last_ts')}`",
        f"- Turns: `{material.get('turn_count')}`",
        f"- Approx tokens: `{material.get('approx_tokens')}`",
        f"- User content chars: `{material.get('char_count')}`",
        f"- User content SHA256: `{material.get('user_content_sha256')}`",
        f"- Raw material written: `{material.get('raw_material_written')}`",
        "",
        "## Paramètres communs",
        "",
        f"- Models: `{len(campaign.get('models') or [])}`",
        f"- temperature: `{(campaign.get('generation_params') or {}).get('temperature')}`",
        f"- top_p: `{(campaign.get('generation_params') or {}).get('top_p')}`",
        f"- max_tokens: `{(campaign.get('generation_params') or {}).get('max_tokens')}`",
        f"- timeout_s: `{campaign.get('timeout_s')}`",
        "",
        "## Sorties à lire",
        "",
        "| Modèle | Provider OK | Finish reason | Latence | Prompt tokens | Completion tokens | Coût estimé | Terminaison | Note | Résumé complet |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for result in campaign.get("results", []):
        provider = result.get("provider") or {}
        usage = provider.get("usage") if isinstance(provider.get("usage"), dict) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{result.get('model')}`",
                    str(bool(result.get("ok"))),
                    str(provider.get("finish_reason")),
                    f"{float(provider.get('elapsed_ms') or 0.0):.0f} ms",
                    str(usage.get("prompt_tokens")),
                    str(usage.get("completion_tokens")),
                    _format_cost(provider.get("cost_estimate_usd")),
                    str(result.get("termination_assessment") or ""),
                    str(result.get("notes") or ""),
                    f"`{result.get('summary_file')}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Ce que cette campagne mesure",
            "",
            "- La qualité lisible du résumé conversationnel produit à prompt et matériau identiques.",
            "- La capacité du modèle à tenir un gros dialogue réel Frida et à rester utile pour la suite.",
            "",
            "## Ce que cette campagne ne prouve pas",
            "",
            "- Aucun score automatique ne départage les modèles.",
            "- Aucun changement de modèle de production n'est effectué.",
            "- La décision de découplage du résumé reste ouverte jusqu'à lecture humaine.",
            "",
        ]
    )
    return "\n".join(lines)


def _provider_public_metadata(provider: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(provider.get("ok")),
        "status_code": provider.get("status_code"),
        "elapsed_ms": provider.get("elapsed_ms"),
        "error": provider.get("error"),
        "usage": provider.get("usage") if isinstance(provider.get("usage"), dict) else {},
        "cost_estimate_usd": provider.get("cost_estimate_usd"),
        "cost_estimate_source": provider.get("cost_estimate_source"),
        "finish_reason": provider.get("finish_reason"),
        "native_finish_reason": provider.get("native_finish_reason"),
    }


def _dry_provider() -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": None,
        "elapsed_ms": 0.0,
        "error": None,
        "raw_text": None,
        "usage": {},
        "cost_estimate_usd": None,
        "cost_estimate_source": "dry_run",
        "finish_reason": "dry_run",
        "native_finish_reason": "dry_run",
    }


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"


def _path_for_report(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _completion_budget_reached(provider: dict[str, Any], max_tokens: Any) -> bool:
    usage = provider.get("usage") if isinstance(provider.get("usage"), dict) else {}
    try:
        completion_tokens = int(usage.get("completion_tokens") or 0)
        limit = int(max_tokens or 0)
    except (TypeError, ValueError):
        return False
    return limit > 0 and completion_tokens >= int(limit * 0.95)


def _termination_assessment(
    provider: dict[str, Any],
    summary_text: str,
    completion_budget_reached: bool,
) -> str:
    finish_reason = str(provider.get("finish_reason") or "").strip().lower()
    native_finish_reason = str(provider.get("native_finish_reason") or "").strip().lower()
    if finish_reason in {"length", "max_tokens"} or native_finish_reason in {"length", "max_tokens"}:
        return "provider_declares_length_stop"
    if not summary_text.strip():
        return "empty_output"
    if completion_budget_reached:
        return "near_completion_budget"
    if finish_reason in {"stop", "end_turn", "eos_token"} or native_finish_reason in {"stop", "end_turn", "eos_token"}:
        return "provider_declares_clean_stop"
    if summary_text.rstrip().endswith((".", "!", "?", "…", "```")):
        return "text_ends_cleanly_but_provider_unclear"
    return "ending_suspect_or_provider_unclear"


def _result_notes(
    provider: dict[str, Any],
    summary_text: str,
    completion_budget_reached: bool,
    termination_assessment: str,
) -> str:
    if not provider.get("ok"):
        return "Erreur provider; sortie brute indisponible ou partielle."
    if not summary_text.strip():
        return "Provider OK mais sortie vide."
    if termination_assessment == "provider_declares_length_stop":
        return "Le provider signale une fin par longueur; sortie probablement tronquee."
    if completion_budget_reached or termination_assessment == "near_completion_budget":
        return "Budget de completion presque atteint; verifier une possible troncature a la lecture."
    return "Sortie brute a lire humainement; aucun score automatique."
