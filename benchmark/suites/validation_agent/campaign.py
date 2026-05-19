"""Campaign runner for the validation_agent benchmark suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.validation_agent import adapter, scorer


def run_validation_agent_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    generation_params: dict[str, Any] | None = None,
    comparison_path: Path | None = None,
) -> dict[str, str]:
    campaign = build_validation_agent_campaign(
        config=config,
        client=client,
        generation_params=generation_params,
        comparison_path=comparison_path,
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / f"{config.campaign_id}.json"
    markdown_path = config.output_dir / f"{config.campaign_id}.md"
    write_json(json_path, campaign)
    markdown_path.write_text(render_markdown_report(campaign), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def build_validation_agent_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    generation_params: dict[str, Any] | None = None,
    comparison_path: Path | None = None,
) -> dict[str, Any]:
    prompt_path = config.repo_root / adapter.PROMPT_PATH
    fixture_path = config.repo_root / adapter.FIXTURE_PATH
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    cases = adapter.load_fixtures(fixture_path)
    generation_settings = generation_params or adapter.generation_params()
    results: list[dict[str, Any]] = []

    for model in config.models:
        calls: list[dict[str, Any]] = []
        for case in cases:
            payload = adapter.build_payload(
                case,
                model,
                prompt_text,
                generation_settings=generation_settings,
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
                provider = _dry_provider(case)
                score = scorer.score_output(case, provider.get("raw_text") or "")
            else:
                if client is None:
                    raise RuntimeError("client is required outside dry-run mode")
                provider = client.chat_completion(payload, caller="validation_agent", timeout_s=config.timeout_s)
                score = scorer.score_output(case, provider.get("raw_text") or "", provider.get("error"))

            calls.append(
                {
                    "case_id": case["id"],
                    "case_tags": list(case.get("tags") or []),
                    "case_origin": str(case.get("origin") or ""),
                    "case_source_reference": str(case.get("source_reference") or ""),
                    "case_design_note": str(case.get("design_note") or ""),
                    "expected": dict(case.get("expected") or {}),
                    "provider": _compact_provider(provider),
                    "request_signature": request_signature,
                    "score": score,
                }
            )
        summary = scorer.summarize_model_results([call["score"] for call in calls])
        summary.update(_provider_summary(calls))
        summary["provisional_verdict"] = scorer.provisional_verdict(summary)
        results.append({"model": model, "summary": summary, "calls": calls})

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "validation_agent",
        "caller": "validation_agent_primary",
        "dry_run": config.dry_run,
        "models": config.models,
        "generation_params": generation_settings,
        "timeout_s": config.timeout_s,
        "prompt_path": str(prompt_path.relative_to(config.repo_root)),
        "prompt_sha256": sha256_text(prompt_text),
        "fixture_path": str(fixture_path.relative_to(config.repo_root)),
        "fixture_sha256": sha256_file(fixture_path),
        "case_count": len(cases),
        "cases": _public_cases(cases),
        "secrets_written": False,
        "production_runtime_changed": False,
        "fallback_benchmarked": False,
        "human_decision_required": True,
        "retention": "compact JSON only: raw model text removed after scoring; hashes, sizes, metrics and parsed decisions retained",
        "comparison_baseline": _comparison_baseline(
            comparison_path,
            repo_root=config.repo_root,
        ),
        "results": results,
    }


def render_markdown_report(campaign: dict[str, Any]) -> str:
    params = campaign.get("generation_params") or {}
    lines = [
        f"# Benchmark validation_agent primaire - {campaign['campaign_id']}",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)",
        f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)",
        f"- temperature: `{params.get('temperature')}`",
        f"- top_p: `{params.get('top_p')}`",
        f"- max_tokens: `{params.get('max_tokens')}`",
        f"- timeout_s: `{campaign.get('timeout_s')}`",
        "- Production runtime changed: `False`",
        "- Retention: raw model text is not retained; parsed decisions, hashes, sizes and metrics are kept.",
        "",
        "## Ce que cette campagne mesure",
        "",
        "Elle compare le caller OpenRouter primaire `validation_agent` sur le vrai prompt de production.",
        "Elle teste le micro-arbitrage de posture finale: `answer|clarify|suspend` et `simple|meta`.",
        "",
        "## Ce que cette campagne ne prouve pas",
        "",
        "- Elle ne choisit pas automatiquement le modele de production.",
        "- Elle ne teste pas le style de la reponse finale.",
        "- Elle ne benchmarke pas le fallback.",
        "- Elle ne remplace pas une lecture humaine de Tof sur les cas limites.",
        "",
        "## Synthese technique",
        "",
        "| Modele | JSON | Schema | Pass | Score | Unsafe answer | Clarifie trop | Suspend trop | Meta inutile | Hard guard | Latence moy. | Cout estime | Completion tok. moy. | Finish | Verdict provisoire |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for result in campaign.get("results", []):
        summary = result.get("summary") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{result.get('model')}`",
                    _count(summary, "json_valid", "cases"),
                    _count(summary, "schema_valid", "cases"),
                    _count(summary, "passes", "cases"),
                    f"{float(summary.get('avg_score') or 0.0):.2f}",
                    str(summary.get("unsafe_answers")),
                    str(summary.get("over_clarify")),
                    str(summary.get("over_suspend")),
                    str(summary.get("meta_overuse")),
                    str(summary.get("hard_guard_violations")),
                    f"{float(summary.get('avg_latency_ms') or 0.0):.0f} ms",
                    _format_cost(summary.get("cost_estimate_usd")),
                    f"{float(summary.get('avg_completion_tokens') or 0.0):.1f}",
                    ", ".join(summary.get("finish_reasons") or []) or "n/a",
                    str(summary.get("provisional_verdict") or ""),
                ]
            )
            + " |"
        )

    lines.extend(_overall_reading_lines(campaign))
    lines.extend(_comparison_lines(campaign))
    lines.extend(["", "## Cas testes", ""])
    for case in campaign.get("cases", []):
        expected = case.get("expected") or {}
        lines.extend(
            [
                f"### {case['id']}",
                "",
                f"- Provenance: `{case.get('origin')}` - `{case.get('source_reference')}`",
                f"- Tags: `{', '.join(case.get('tags') or [])}`",
                f"- Attendu: `{expected.get('final_judgment_posture')}/{expected.get('final_output_regime')}`",
                f"- Note: {case.get('design_note')}",
                "",
            ]
        )

    lines.extend(["## Lecture hermeneutique par modele", ""])
    for result in campaign.get("results", []):
        lines.extend(_model_reading_lines(result))

    lines.extend(_divergence_lines(campaign))
    lines.extend(
        [
            "## Recommandation provisoire",
            "",
            _provisional_recommendation(campaign),
            "",
        ]
    )
    return "\n".join(lines)


def _dry_provider(case: dict[str, Any]) -> dict[str, Any]:
    raw_text = adapter.dry_run_response(case)
    return {
        "ok": True,
        "status_code": None,
        "elapsed_ms": 0.0,
        "error": None,
        "raw_text": raw_text,
        "finish_reason": "dry_run",
        "native_finish_reason": "dry_run",
        "usage": {"completion_tokens": 0},
        "cost_estimate_usd": None,
        "cost_estimate_source": "dry_run",
    }


def _compact_provider(provider: dict[str, Any]) -> dict[str, Any]:
    compact = dict(provider)
    raw_text = str(compact.pop("raw_text", "") or "")
    compact["raw_text_retained"] = False
    compact["raw_text_chars"] = len(raw_text)
    compact["raw_text_sha256"] = sha256_text(raw_text) if raw_text else ""
    return compact


def _provider_summary(calls: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(calls)
    elapsed = [float((call.get("provider") or {}).get("elapsed_ms") or 0.0) for call in calls]
    costs = [
        float((call.get("provider") or {}).get("cost_estimate_usd"))
        for call in calls
        if isinstance((call.get("provider") or {}).get("cost_estimate_usd"), (int, float))
    ]
    completion_tokens = [
        float(((call.get("provider") or {}).get("usage") or {}).get("completion_tokens") or 0.0)
        for call in calls
    ]
    finish_reasons = sorted(
        {
            str((call.get("provider") or {}).get("finish_reason") or "")
            for call in calls
            if (call.get("provider") or {}).get("finish_reason")
        }
    )
    return {
        "avg_latency_ms": round(sum(elapsed) / max(1, count), 2),
        "cost_estimate_usd": round(sum(costs), 8) if costs else None,
        "avg_completion_tokens": round(sum(completion_tokens) / max(1, count), 2),
        "finish_reasons": finish_reasons,
    }


def _comparison_baseline(path: Path | None, *, repo_root: Path) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = path if path.is_absolute() else repo_root / path
    if not resolved.exists():
        return {
            "available": False,
            "path": str(path),
            "error": "baseline_not_found",
        }
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "available": True,
        "path": str(resolved.relative_to(repo_root)) if resolved.is_relative_to(repo_root) else str(resolved),
        "campaign_id": payload.get("campaign_id"),
        "generation_params": dict(payload.get("generation_params") or {}),
        "summaries": {
            str(result.get("model")): dict(result.get("summary") or {})
            for result in payload.get("results", [])
        },
    }


def _public_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "origin": str(case.get("origin") or ""),
            "source_reference": str(case.get("source_reference") or ""),
            "tags": list(case.get("tags") or []),
            "design_note": str(case.get("design_note") or ""),
            "expected": dict(case.get("expected") or {}),
        }
        for case in cases
    ]


def _overall_reading_lines(campaign: dict[str, Any]) -> list[str]:
    lines = ["", "## Lecture synthetique post-run", ""]
    results = campaign.get("results") or []
    if not results:
        return lines + ["Aucun resultat.", ""]
    ranked = sorted(
        results,
        key=lambda result: (
            int((result.get("summary") or {}).get("passes") or 0),
            float((result.get("summary") or {}).get("avg_score") or 0.0),
            -int((result.get("summary") or {}).get("unsafe_answers") or 0),
            -int((result.get("summary") or {}).get("meta_overuse") or 0),
        ),
        reverse=True,
    )
    top = ranked[0]
    lines.append(
        "Le meilleur signal quantitatif revient ici a "
        f"`{top.get('model')}`: "
        f"{(top.get('summary') or {}).get('passes')}/{campaign.get('case_count')} pass, "
        f"score moyen {(top.get('summary') or {}).get('avg_score')}. "
        "La decision reste humaine: il faut surtout lire les erreurs de posture et les meta inutiles."
    )
    lines.append("")
    for result in results:
        lines.append(f"- `{result.get('model')}`: {_qualitative_profile(result.get('summary') or {})}")
    lines.append("")
    return lines


def _comparison_lines(campaign: dict[str, Any]) -> list[str]:
    baseline = campaign.get("comparison_baseline") or {}
    if not baseline.get("available"):
        return []
    current_by_model = {
        str(result.get("model")): dict(result.get("summary") or {})
        for result in campaign.get("results", [])
    }
    baseline_by_model = dict(baseline.get("summaries") or {})
    baseline_params = baseline.get("generation_params") or {}
    current_params = campaign.get("generation_params") or {}
    lines = [
        "",
        "## Comparaison avec le run precedent",
        "",
        f"- Baseline: `{baseline.get('path')}`",
        f"- max_tokens baseline: `{baseline_params.get('max_tokens')}`",
        f"- max_tokens courant: `{current_params.get('max_tokens')}`",
        "",
        "| Modele | JSON | Schema | Pass | Unsafe answer | Finish | Lecture courte |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for model, current in current_by_model.items():
        previous = baseline_by_model.get(model) or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{model}`",
                    _shift(previous, current, "json_valid", "cases"),
                    _shift(previous, current, "schema_valid", "cases"),
                    _shift(previous, current, "passes", "cases"),
                    f"{previous.get('unsafe_answers', 0)} -> {current.get('unsafe_answers', 0)}",
                    f"{', '.join(previous.get('finish_reasons') or []) or 'n/a'} -> {', '.join(current.get('finish_reasons') or []) or 'n/a'}",
                    _comparison_reading(previous, current),
                ]
            )
            + " |"
        )
    return lines


def _shift(previous: dict[str, Any], current: dict[str, Any], key: str, total_key: str) -> str:
    return (
        f"{previous.get(key, 0)}/{previous.get(total_key, 0)}"
        f" -> {current.get(key, 0)}/{current.get(total_key, 0)}"
    )


def _comparison_reading(previous: dict[str, Any], current: dict[str, Any]) -> str:
    if current.get("json_valid") > previous.get("json_valid", 0):
        return "validite JSON retrouvee partiellement ou totalement"
    if current.get("passes") > previous.get("passes", 0):
        return "posture mieux notee sans gain JSON"
    if current.get("unsafe_answers", 0) > previous.get("unsafe_answers", 0):
        return "plus permissif malgre plus de place"
    if current.get("json_valid") == current.get("cases") == previous.get("json_valid"):
        return "JSON deja stable, juger surtout la posture"
    return "pas de gain net"


def _model_reading_lines(result: dict[str, Any]) -> list[str]:
    summary = result.get("summary") or {}
    lines = [
        f"### `{result.get('model')}`",
        "",
        f"- Verdict provisoire: {summary.get('provisional_verdict')}",
        f"- Profil: {_qualitative_profile(summary)}",
    ]
    interesting = _interesting_examples(result.get("calls") or [])
    if not interesting:
        lines.append("- Aucun ecart majeur releve par le scorer.")
    else:
        lines.append("- Ecarts utiles a lire:")
        for call in interesting[:8]:
            score = call.get("score") or {}
            lines.append(
                "  - "
                f"`{call.get('case_id')}`: produit "
                f"`{score.get('final_judgment_posture')}/{score.get('final_output_regime')}`, "
                f"attendu `{score.get('expected_posture')}/{score.get('expected_output_regime')}`, "
                f"notes=`{', '.join(score.get('notes') or [])}`"
            )
    lines.append("")
    return lines


def _divergence_lines(campaign: dict[str, Any]) -> list[str]:
    lines = ["## Divergences entre modeles", ""]
    for case in campaign.get("cases", []):
        decisions: dict[str, str] = {}
        for result in campaign.get("results", []):
            call = _call_by_case(result, case["id"])
            if call:
                score = call.get("score") or {}
                decisions[str(result.get("model"))] = (
                    f"{score.get('final_judgment_posture')}/{score.get('final_output_regime')}"
                )
        if len(set(decisions.values())) <= 1:
            continue
        lines.append(
            f"- `{case['id']}`: "
            + ", ".join(f"`{model}`={decision}" for model, decision in decisions.items())
        )
    if len(lines) == 2:
        lines.append("- Aucune divergence de posture/regime detectee.")
    lines.append("")
    return lines


def _interesting_examples(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [call for call in calls if not (call.get("score") or {}).get("pass")]


def _qualitative_profile(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    if summary.get("schema_valid") != summary.get("cases"):
        parts.append("schema strict fragile")
    else:
        parts.append("schema strict stable")
    if int(summary.get("unsafe_answers") or 0):
        parts.append(f"{summary.get('unsafe_answers')} reponse(s) trop permissive(s)")
    else:
        parts.append("pas de permissivite dangereuse detectee")
    if int(summary.get("over_clarify") or 0):
        parts.append(f"{summary.get('over_clarify')} clarification(s) excessive(s)")
    else:
        parts.append("clarification contenue")
    if int(summary.get("over_suspend") or 0):
        parts.append(f"{summary.get('over_suspend')} suspension(s) excessive(s)")
    else:
        parts.append("suspension contenue")
    if int(summary.get("meta_overuse") or 0):
        parts.append(f"{summary.get('meta_overuse')} meta inutile(s)")
    else:
        parts.append("meta sobre")
    return "; ".join(parts) + "."


def _provisional_recommendation(campaign: dict[str, Any]) -> str:
    results = campaign.get("results") or []
    if not results:
        return "Aucun resultat exploitable."
    ranked = sorted(
        results,
        key=lambda result: (
            int((result.get("summary") or {}).get("passes") or 0),
            float((result.get("summary") or {}).get("avg_score") or 0.0),
            -int((result.get("summary") or {}).get("unsafe_answers") or 0),
            -int((result.get("summary") or {}).get("meta_overuse") or 0),
        ),
        reverse=True,
    )
    top = ranked[0]
    comparison = next((item for item in ranked[1:] if item.get("model") != top.get("model")), None)
    if comparison is None:
        return (
            f"Recommandation provisoire de lecture: relire `{top.get('model')}`. "
            "Aucun changement de production n'est propose par cette campagne."
        )
    return (
        f"Recommandation provisoire de lecture: relire d'abord `{top.get('model')}` contre "
        f"`{comparison.get('model')}` sur les divergences. Aucun changement de production n'est propose par cette campagne."
    )


def _call_by_case(result: dict[str, Any], case_id: str) -> dict[str, Any] | None:
    for call in result.get("calls", []):
        if call.get("case_id") == case_id:
            return call
    return None


def _count(summary: dict[str, Any], key: str, total_key: str) -> str:
    return f"{summary.get(key, 0)}/{summary.get(total_key, 0)}"


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"
