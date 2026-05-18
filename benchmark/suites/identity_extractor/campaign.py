from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.identity_extractor import adapter, scorer


def run_identity_human_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "human",
) -> dict[str, Any]:
    campaign = build_identity_human_campaign(config=config, client=client, fixture_set=fixture_set)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{config.campaign_id}.json"
    technical_path = output_dir / f"{config.campaign_id}-technical.md"
    hermeneutic_path = output_dir / f"{config.campaign_id}-hermeneutic.md"

    write_json(json_path, campaign)
    technical_path.write_text(render_technical_report(campaign), encoding="utf-8")
    hermeneutic_path.write_text(render_hermeneutic_report(campaign), encoding="utf-8")
    for result in campaign.get("results", []):
        model_path = output_dir / f"{config.campaign_id}__{adapter.safe_model_slug(result['model'])}.md"
        model_path.write_text(render_model_output_file(campaign, result), encoding="utf-8")
        result["output_file"] = _path_for_report(model_path, config.repo_root)
    write_json(json_path, campaign)
    technical_path.write_text(render_technical_report(campaign), encoding="utf-8")
    hermeneutic_path.write_text(render_hermeneutic_report(campaign), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "technical_path": str(technical_path),
        "hermeneutic_path": str(hermeneutic_path),
        "output_files": [result.get("output_file") for result in campaign.get("results", [])],
    }


def build_identity_human_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "human",
) -> dict[str, Any]:
    prompt_path = adapter.prompt_path(config.repo_root)
    fixture_path = adapter.fixture_path(config.repo_root, fixture_set=fixture_set)
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    cases = adapter.load_cases(config.repo_root, fixture_set=fixture_set)
    results: list[dict[str, Any]] = []

    for model in config.models:
        calls: list[dict[str, Any]] = []
        for case in cases:
            payload = adapter.build_payload(case, model, prompt_text)
            request_signature = {
                "messages_sha256": sha256_text(json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)),
                "generation_params": {
                    "temperature": payload.get("temperature"),
                    "top_p": payload.get("top_p"),
                    "max_tokens": payload.get("max_tokens"),
                },
            }
            if config.dry_run:
                provider = _dry_provider(model)
                score = scorer.score_response(case, provider.get("raw_text"), None)
            else:
                if client is None:
                    raise RuntimeError("client is required outside dry-run mode")
                provider = client.chat_completion(payload, caller="identity_extractor", timeout_s=config.timeout_s)
                score = scorer.score_response(case, provider.get("raw_text"), provider.get("error"))

            calls.append(
                {
                    "case_id": case["id"],
                    "case_subject": case["subject"],
                    "case_tags": list(case.get("tags") or []),
                    "case_design_note": str(case.get("design_note") or ""),
                    "provider": provider,
                    "request_signature": request_signature,
                    "score": score,
                }
            )
        results.append({"model": model, "summary": scorer.summarize_model(model, calls), "calls": calls})

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "identity_extractor",
        "dry_run": config.dry_run,
        "models": config.models,
        "generation_params": dict(adapter.GENERATION_PARAMS),
        "timeout_s": config.timeout_s,
        "prompt_path": str(prompt_path.relative_to(config.repo_root)),
        "prompt_sha256": sha256_text(prompt_text),
        "fixture_path": str(fixture_path.relative_to(config.repo_root)),
        "fixture_sha256": sha256_file(fixture_path),
        "case_count": len(cases),
        "cases": _public_cases(cases),
        "secrets_written": False,
        "human_judgment_required": True,
        "production_runtime_changed": False,
        "results": results,
    }


def render_technical_report(campaign: dict[str, Any]) -> str:
    params = campaign.get("generation_params") or {}
    lines = [
        f"# Benchmark identity extractor - {campaign['campaign_id']} - technique",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)",
        f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)",
        f"- temperature: `{params.get('temperature')}`",
        f"- top_p: `{params.get('top_p')}`",
        f"- max_tokens: `{params.get('max_tokens')}`",
        f"- Production runtime changed: `{campaign.get('production_runtime_changed')}`",
        "",
        "## Synthese technique",
        "",
        "| Modele | Provider OK | JSON valide | Schema valide | Entrees | Taille sortie | Latence moyenne | Cout estime | Finish reason(s) | Sorties completes | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for result in campaign.get("results", []):
        summary = result.get("summary") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{result.get('model')}`",
                    f"{1.0 - float(summary.get('provider_error_rate') or 0.0):.0%}",
                    f"{float(summary.get('json_valid_rate') or 0.0):.0%}",
                    f"{float(summary.get('schema_valid_rate') or 0.0):.0%}",
                    str(summary.get("entry_count")),
                    f"{int(summary.get('output_chars') or 0)} chars",
                    f"{float(summary.get('avg_latency_ms') or 0.0):.0f} ms",
                    _format_cost(summary.get("cost_estimate_usd")),
                    ", ".join(summary.get("finish_reasons") or []) or "n/a",
                    f"`{result.get('output_file', '')}`",
                    str(summary.get("notes") or ""),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Ce que cette campagne mesure",
            "",
            "- La capacite de chaque modele a respecter le prompt de production `identity_extractor`.",
            "- La validite JSON, le respect du schema, la latence, le cout et les erreurs provider.",
            "- La matiere complete necessaire a une lecture humaine de discernement identitaire.",
            "",
            "## Ce que cette campagne ne prouve pas",
            "",
            "- Aucun score automatique ne choisit le modele de production.",
            "- Les dix cas sont courts et diagnostiques; ils ne remplacent pas une validation longue sur trafic reel.",
            "- Aucun slot runtime `identity_extractor_model` n'est cree ou modifie dans ce lot.",
            "",
        ]
    )
    return "\n".join(lines)


def render_hermeneutic_report(campaign: dict[str, Any]) -> str:
    lines = [
        f"# Benchmark identity extractor - {campaign['campaign_id']} - lecture hermeneutique",
        "",
        "Cette campagne compare le discernement des modeles sur le vrai prompt de production de l'extracteur identity.",
        "Elle ne choisit pas automatiquement un modele: les sorties completes ci-dessous sont la matiere de lecture pour Tof.",
        "",
        "## Cas testes",
        "",
    ]
    for case in campaign.get("cases", []):
        lines.extend(
            [
                f"### {case['id']} - `{case['subject']}`",
                "",
                f"> {case['message']}",
                "",
                f"- Note de conception: {case['design_note']}",
                f"- Tags: `{', '.join(case.get('tags') or [])}`",
                "",
            ]
        )

    lines.append("## Sorties completes par cas")
    lines.append("")
    cases_by_id = {case["id"]: case for case in campaign.get("cases", [])}
    for case_id, case in cases_by_id.items():
        lines.extend([f"### {case_id}", "", f"Message: {case['message']}", ""])
        for result in campaign.get("results", []):
            call = _call_by_case(result, case_id)
            raw_text = str((call.get("provider") or {}).get("raw_text") or "").strip()
            if not raw_text:
                raw_text = f"[pas de sortie: {(call.get('provider') or {}).get('error')}]"
            lines.extend(
                [
                    f"#### `{result.get('model')}`",
                    "",
                    "````json",
                    raw_text,
                    "````",
                    "",
                ]
            )

    lines.extend(
        [
            "## Lecture qualitative initiale",
            "",
            "Cette section est volontairement prudente: elle oriente la lecture, sans remplacer la decision humaine de Tof.",
            "",
            "- `openai/gpt-5.4-mini`: a completer apres lecture des sorties reelles.",
            "- `anthropic/claude-haiku-4.5`: a completer apres lecture des sorties reelles.",
            "- `google/gemini-3.1-flash-lite`: a completer apres lecture des sorties reelles.",
            "- `mistralai/mistral-small-2603`: a completer apres lecture des sorties reelles.",
            "",
            "## Synthese finale prudente",
            "",
            "A completer apres lecture humaine: pas de changement de production dans cette campagne.",
            "",
        ]
    )
    return "\n".join(lines)


def render_model_output_file(campaign: dict[str, Any], result: dict[str, Any]) -> str:
    summary = result.get("summary") or {}
    lines = [
        f"# Identity extractor - sorties completes - {result['model']}",
        "",
        f"- Campaign: `{campaign['campaign_id']}`",
        f"- Model: `{result['model']}`",
        f"- Prompt SHA256: `{campaign['prompt_sha256']}`",
        f"- Fixture SHA256: `{campaign['fixture_sha256']}`",
        f"- JSON valid rate: `{summary.get('json_valid_rate')}`",
        f"- Schema valid rate: `{summary.get('schema_valid_rate')}`",
        f"- Cost estimate USD: `{summary.get('cost_estimate_usd')}`",
        "",
    ]
    cases = {case["id"]: case for case in campaign.get("cases", [])}
    for call in result.get("calls", []):
        case = cases.get(call["case_id"]) or {}
        provider = call.get("provider") or {}
        lines.extend(
            [
                f"## {call['case_id']} - `{call.get('case_subject')}`",
                "",
                f"> {case.get('message', '')}",
                "",
                f"- Note de conception: {case.get('design_note', '')}",
                f"- Provider OK: `{provider.get('ok')}`",
                f"- Latency: `{provider.get('elapsed_ms')} ms`",
                f"- Finish reason: `{provider.get('finish_reason')}`",
                f"- Completion tokens: `{(provider.get('usage') or {}).get('completion_tokens') if isinstance(provider.get('usage'), dict) else None}`",
                f"- Schema valid: `{(call.get('score') or {}).get('schema_valid')}`",
                "",
                "````json",
                str(provider.get("raw_text") or provider.get("error") or "").strip(),
                "````",
                "",
            ]
        )
    return "\n".join(lines)


def _dry_provider(model: str) -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": None,
        "elapsed_ms": 0.0,
        "error": None,
        "raw_text": json.dumps(
            {
                "entries": [
                    {
                        "subject": "user",
                        "content": f"dry-run identity candidate for {model}",
                        "stability": "unknown",
                        "utterance_mode": "unknown",
                        "recurrence": "unknown",
                        "scope": "user",
                        "evidence_kind": "weak",
                        "confidence": 0.1,
                        "reason": "dry-run placeholder",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        "finish_reason": "dry_run",
        "native_finish_reason": "dry_run",
        "usage": {},
        "cost_estimate_usd": None,
        "cost_estimate_source": "dry_run",
    }


def _public_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "subject": case["subject"],
            "message": case["message"],
            "design_note": case["design_note"],
            "tags": list(case.get("tags") or []),
            "origin": case.get("origin"),
            "difficulty": case.get("difficulty"),
        }
        for case in cases
    ]


def _call_by_case(result: dict[str, Any], case_id: str) -> dict[str, Any]:
    for call in result.get("calls", []):
        if call.get("case_id") == case_id:
            return call
    return {}


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"


def _path_for_report(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
