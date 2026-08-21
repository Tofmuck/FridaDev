"""Campaign runner for the validation_agent benchmark suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.validation_agent import adapter, evaluation, scorer


def run_validation_agent_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    generation_params: dict[str, Any] | None = None,
    comparison_path: Path | None = None,
    fixture_path: Path | None = None,
    model_roles: dict[str, str] | None = None,
    reasoning_efforts: dict[str, str] | None = None,
    repetitions: int = 1,
    screening: bool = False,
) -> dict[str, str]:
    campaign = build_validation_agent_campaign(
        config=config,
        client=client,
        generation_params=generation_params,
        comparison_path=comparison_path,
        fixture_path=fixture_path,
        model_roles=model_roles,
        reasoning_efforts=reasoning_efforts,
        repetitions=repetitions,
        screening=screening,
    )
    if campaign.get("content_free_decision_artifact"):
        assert_presence_campaign_content_free(campaign)
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
    fixture_path: Path | None = None,
    model_roles: dict[str, str] | None = None,
    reasoning_efforts: dict[str, str] | None = None,
    repetitions: int = 1,
    screening: bool = False,
) -> dict[str, Any]:
    prompt_path = config.repo_root / adapter.PROMPT_PATH
    fixture_path = fixture_path or (config.repo_root / adapter.FIXTURE_PATH)
    if not fixture_path.is_absolute():
        fixture_path = config.repo_root / fixture_path
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    fixture_document = adapter.load_fixture_document(fixture_path)
    cases = fixture_document["cases"]
    presence_corpus = fixture_document.get("schema_version") == "validation_presence_corpus_v1"
    if repetitions < 1 or repetitions > 3:
        raise ValueError("validation_agent repetitions must be between 1 and 3")
    resolved_model_roles = {
        model: str((model_roles or {}).get(model) or "unspecified")
        for model in config.models
    }
    if any(role not in {"primary", "fallback", "unspecified"} for role in resolved_model_roles.values()):
        raise ValueError("validation_agent model roles must be primary, fallback or unspecified")
    unknown_reasoning_models = sorted(set(reasoning_efforts or {}) - set(config.models))
    if unknown_reasoning_models:
        raise ValueError(
            "validation_agent reasoning effort references unknown models: "
            + ", ".join(unknown_reasoning_models)
        )
    resolved_reasoning_efforts: dict[str, str] = {}
    for model, effort in (reasoning_efforts or {}).items():
        normalized_effort = str(effort).strip().lower()
        if normalized_effort not in adapter.REASONING_EFFORTS:
            raise ValueError(f"unsupported validation_agent reasoning effort: {effort}")
        resolved_reasoning_efforts[model] = normalized_effort
    if presence_corpus and len(cases) * len(config.models) * repetitions > 144:
        raise ValueError("validation_agent Presence campaign exceeds the 144-call safety cap")
    if screening and not presence_corpus:
        raise ValueError("validation_agent screening requires the Presence corpus")
    if screening and repetitions != 1:
        raise ValueError("validation_agent screening requires exactly one repetition")
    if screening and any(role != "unspecified" for role in resolved_model_roles.values()):
        raise ValueError("validation_agent screening cannot assign runtime roles")
    if presence_corpus and not config.dry_run:
        if fixture_document.get("human_validation_status") != "validated":
            raise ValueError("live Presence benchmark requires a human-validated corpus")
        if not screening and sorted(resolved_model_roles.values()) != ["fallback", "primary"]:
            raise ValueError("live Presence benchmark requires one primary and one fallback model")
    generation_settings = generation_params or adapter.generation_params(
        timeout_s=config.timeout_s,
    )
    if presence_corpus and int(generation_settings.get("timeout_s") or 0) != config.timeout_s:
        raise ValueError("Presence campaign timeout metadata must match the provider timeout")
    results: list[dict[str, Any]] = []

    for model in config.models:
        reasoning_effort = resolved_reasoning_efforts.get(model)
        calls: list[dict[str, Any]] = []
        for case in cases:
            for repetition_index in range(1, repetitions + 1):
                payload = adapter.build_payload(
                    case,
                    model,
                    prompt_text,
                    generation_settings=generation_settings,
                    reasoning_effort=reasoning_effort,
                )
                request_signature = {
                    "messages_sha256": sha256_text(
                        json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)
                    ),
                    "generation_params": {
                        "temperature": payload.get("temperature"),
                        "top_p": payload.get("top_p"),
                        "max_tokens": payload.get("max_tokens"),
                    },
                }
                if reasoning_effort is not None:
                    request_signature["reasoning"] = {
                        "effort": reasoning_effort,
                        "exclude": True,
                    }
                if config.dry_run:
                    provider = _dry_provider(case)
                    score = scorer.score_output(case, provider.get("raw_text") or "")
                else:
                    if client is None:
                        raise RuntimeError("client is required outside dry-run mode")
                    provider = client.chat_completion(
                        payload,
                        caller="validation_agent",
                        timeout_s=config.timeout_s,
                    )
                    score = scorer.score_output(
                        case,
                        provider.get("raw_text") or "",
                        provider.get("error"),
                    )

                model_role = resolved_model_roles[model]
                call = {
                    "case_id": case["id"],
                    "case_tags": list(case.get("tags") or []),
                    "expected": dict(case.get("expected") or {}),
                    "repetition_index": repetition_index,
                    "requested_model": model,
                    "model_role": model_role,
                    "observed_model": str(provider.get("model") or ""),
                    "observed_provider": str(provider.get("provider") or ""),
                    "provider_source": "dry_run" if config.dry_run else model_role,
                    "reasoning_effort_requested": reasoning_effort,
                    "reasoning_excluded": reasoning_effort is not None,
                    "provider": _compact_provider(provider),
                    "request_signature": request_signature,
                    "score": score,
                }
                if presence_corpus:
                    call.update(
                        {
                            "semantic_family": str(case.get("semantic_family") or ""),
                            "false_presence_severity": str(case.get("false_presence_severity") or ""),
                            "synthetic_provenance_tags": list(
                                case.get("synthetic_provenance_tags") or []
                            ),
                        }
                    )
                else:
                    call.update(
                        {
                            "case_origin": str(case.get("origin") or ""),
                            "case_source_reference": str(case.get("source_reference") or ""),
                            "case_design_note": str(case.get("design_note") or ""),
                        }
                    )
                calls.append(call)
        summary = scorer.summarize_model_results([call["score"] for call in calls])
        summary.update(_provider_summary(calls))
        if presence_corpus:
            summary.update(
                evaluation.summarize_presence_repetitions(
                    cases=cases,
                    calls=calls,
                    thresholds=dict(fixture_document.get("proposed_safety_thresholds") or {}),
                    repetitions=repetitions,
                )
            )
        summary["provisional_verdict"] = scorer.provisional_verdict(summary)
        results.append(
            {
                "model": model,
                "model_role": resolved_model_roles[model],
                "summary": summary,
                "calls": calls,
            }
        )

    campaign = {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "validation_agent",
        "caller": "validation_agent",
        "dry_run": config.dry_run,
        "models": config.models,
        "model_roles": resolved_model_roles,
        "reasoning_efforts": resolved_reasoning_efforts,
        "screening": screening,
        "repetitions": repetitions,
        "planned_call_count": len(cases) * len(config.models) * repetitions,
        "generation_params": generation_settings,
        "timeout_s": config.timeout_s,
        "prompt_path": str(prompt_path.relative_to(config.repo_root)),
        "prompt_sha256": sha256_text(prompt_text),
        "fixture_path": str(fixture_path.relative_to(config.repo_root)),
        "fixture_sha256": sha256_file(fixture_path),
        "case_count": len(cases),
        "cases": _public_cases(cases, content_free=presence_corpus),
        "secrets_written": False,
        "production_runtime_changed": False,
        "fallback_benchmarked": "fallback" in resolved_model_roles.values(),
        "human_decision_required": True,
        "retention": "compact JSON only: raw model text and free-form model reasons removed after scoring; hashes, sizes and bounded decisions retained",
        "comparison_baseline": _comparison_baseline(
            comparison_path,
            repo_root=config.repo_root,
        ),
        "results": results,
    }
    if presence_corpus:
        boundary_cases = list(fixture_document.get("runtime_boundary_cases") or [])
        campaign.update(
            {
                "corpus_schema_version": fixture_document["schema_version"],
                "human_validation_status": fixture_document["human_validation_status"],
                "human_validation_date": fixture_document.get("human_validation_date"),
                "validated_contract_sha256": fixture_document.get("validated_contract_sha256"),
                "proposed_safety_thresholds": dict(
                    fixture_document.get("proposed_safety_thresholds") or {}
                ),
                "runtime_boundary_case_count": len(boundary_cases),
                "runtime_boundary_cases": _public_boundary_cases(boundary_cases),
                "content_free_decision_artifact": True,
                "raw_fixture_content_included": False,
                "raw_model_output_included": False,
                "free_form_model_reason_included": False,
                "provider_route_observability_complete": bool(
                    not config.dry_run
                    and all(
                        call.get("observed_model") and call.get("observed_provider")
                        for result in results
                        for call in result.get("calls") or []
                    )
                ),
            }
        )
        campaign["benchmark_decision_ready"] = bool(
            not config.dry_run
            and not screening
            and repetitions == 3
            and campaign["provider_route_observability_complete"]
            and all((result.get("summary") or {}).get("safety_thresholds_met") for result in results)
        )
    else:
        campaign["content_free_decision_artifact"] = False
    return campaign


def render_markdown_report(campaign: dict[str, Any]) -> str:
    params = campaign.get("generation_params") or {}
    if campaign.get("screening"):
        benchmark_scope = "candidats de criblage"
        scope_sentence = (
            "Elle compare des candidats de criblage sans leur attribuer de role "
            "runtime primaire ou fallback."
        )
    else:
        benchmark_scope = (
            "primaire et fallback"
            if campaign.get("fallback_benchmarked")
            else "primaire"
        )
        scope_sentence = (
            f"Elle compare les roles {benchmark_scope} du caller OpenRouter "
            "`validation_agent` sur le vrai prompt de production."
        )
    lines = [
        f"# Benchmark validation_agent {benchmark_scope} - {campaign['campaign_id']}",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)",
        f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)",
        f"- temperature: `{params.get('temperature')}`",
        f"- top_p: `{params.get('top_p')}`",
        f"- max_tokens: `{params.get('max_tokens')}`",
        f"- timeout_s: `{campaign.get('timeout_s')}`",
        f"- Repetitions par cas: `{campaign.get('repetitions', 1)}`",
        f"- Appels planifies: `{campaign.get('planned_call_count')}`",
        f"- Roles: `{json.dumps(campaign.get('model_roles') or {}, sort_keys=True)}`",
        f"- Reasoning efforts demandes: `{json.dumps(campaign.get('reasoning_efforts') or {}, sort_keys=True)}`",
        f"- Screening: `{campaign.get('screening', False)}`",
        f"- Routes provider observees: `{campaign.get('provider_route_observability_complete')}`",
        f"- Decision de benchmark prete: `{campaign.get('benchmark_decision_ready')}`",
        "- Production runtime changed: `False`",
        "- Retention: raw model text is not retained; parsed decisions, hashes, sizes and metrics are kept.",
        "",
        "## Ce que cette campagne mesure",
        "",
        scope_sentence,
        "Elle teste le micro-arbitrage de posture finale: `answer|clarify|suspend` et `simple|meta|presence`.",
        "",
        "## Ce que cette campagne ne prouve pas",
        "",
        "- Elle ne choisit pas automatiquement le modele de production.",
        "- Elle ne teste pas le style de la reponse finale.",
        "- Elle ne modifie ni le modele, ni le prompt, ni les reglages de production.",
        "- Elle ne remplace pas une lecture humaine de Tof sur les cas limites.",
        "",
        "## Synthese technique",
        "",
        "| Modele | Role | Effort | JSON | Schema | Pass | Faux Presence | Presence manquee | Non-reponse bureaucratique | Unsafe answer | Stabilite | Rappel Presence | Seuils | Reasoning tokens | Provider observe | Latence moy. | Cout estime |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |",
    ]
    for result in campaign.get("results", []):
        summary = result.get("summary") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{result.get('model')}`",
                    f"`{result.get('model_role')}`",
                    f"`{(campaign.get('reasoning_efforts') or {}).get(result.get('model'), 'default')}`",
                    _count(summary, "json_valid", "cases"),
                    _count(summary, "schema_valid", "cases"),
                    _count(summary, "passes", "cases"),
                    str(summary.get("false_presence")),
                    str(summary.get("missed_presence")),
                    str(summary.get("bureaucratic_non_answer")),
                    str(summary.get("unsafe_answers")),
                    _format_rate(summary.get("repetition_stability_rate")),
                    _format_rate(summary.get("required_presence_rate")),
                    _format_threshold_status(summary),
                    str(summary.get("reasoning_tokens_total") or 0),
                    ", ".join(summary.get("observed_providers") or []) or "n/a",
                    f"{float(summary.get('avg_latency_ms') or 0.0):.0f} ms",
                    _format_cost(summary.get("cost_estimate_usd")),
                ]
            )
            + " |"
        )

    lines.extend(_overall_reading_lines(campaign))
    lines.extend(_comparison_lines(campaign))
    lines.extend(["", "## Cas testes", ""])
    for case in campaign.get("cases", []):
        expected = case.get("expected") or {}
        lines.extend([f"### {case['id']}", ""])
        if campaign.get("content_free_decision_artifact"):
            lines.extend(
                [
                    f"- Famille: `{case.get('semantic_family')}`",
                    f"- Gravite faux positif: `{case.get('false_presence_severity')}`",
                    f"- Tags synthetiques: `{', '.join(case.get('synthetic_provenance_tags') or [])}`",
                ]
            )
        else:
            lines.extend(
                [
                    f"- Provenance: `{case.get('origin')}` - `{case.get('source_reference')}`",
                    f"- Tags: `{', '.join(case.get('tags') or [])}`",
                    f"- Note: {case.get('design_note')}",
                ]
            )
        lines.extend(
            [
                f"- Attendu: `{expected.get('final_judgment_posture')}/{expected.get('final_output_regime')}`",
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
        "generation_id": "",
        "model": "",
        "provider": "",
    }


def _compact_provider(provider: dict[str, Any]) -> dict[str, Any]:
    compact = dict(provider)
    raw_text = str(compact.pop("raw_text", "") or "")
    error_present = bool(compact.pop("error", None))
    compact["raw_text_retained"] = False
    compact["raw_text_chars"] = len(raw_text)
    compact["raw_text_sha256"] = sha256_text(raw_text) if raw_text else ""
    compact["error_present"] = error_present
    compact["error_code"] = "provider_error" if error_present else None
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
    reasoning_tokens = [
        _reasoning_tokens((call.get("provider") or {}).get("usage") or {})
        for call in calls
    ]
    finish_reasons = sorted(
        {
            str((call.get("provider") or {}).get("finish_reason") or "")
            for call in calls
            if (call.get("provider") or {}).get("finish_reason")
        }
    )
    observed_models = sorted(
        {str(call.get("observed_model")) for call in calls if call.get("observed_model")}
    )
    observed_providers = sorted(
        {str(call.get("observed_provider")) for call in calls if call.get("observed_provider")}
    )
    return {
        "avg_latency_ms": round(sum(elapsed) / max(1, count), 2),
        "cost_estimate_usd": round(sum(costs), 8) if costs else None,
        "avg_completion_tokens": round(sum(completion_tokens) / max(1, count), 2),
        "reasoning_tokens_total": sum(reasoning_tokens),
        "avg_reasoning_tokens": round(sum(reasoning_tokens) / max(1, count), 2),
        "finish_reasons": finish_reasons,
        "observed_models": observed_models,
        "observed_providers": observed_providers,
        "observed_model_present_rate": round(
            sum(1 for call in calls if call.get("observed_model")) / max(1, count),
            4,
        ),
        "observed_provider_present_rate": round(
            sum(1 for call in calls if call.get("observed_provider")) / max(1, count),
            4,
        ),
    }


def _reasoning_tokens(usage: dict[str, Any]) -> int:
    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        return 0
    try:
        return int(details.get("reasoning_tokens") or 0)
    except (TypeError, ValueError):
        return 0


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


def _public_cases(
    cases: list[dict[str, Any]],
    *,
    content_free: bool,
) -> list[dict[str, Any]]:
    if content_free:
        return [
            {
                "id": case["id"],
                "semantic_family": str(case.get("semantic_family") or ""),
                "false_presence_severity": str(case.get("false_presence_severity") or ""),
                "synthetic_provenance_tags": list(case.get("synthetic_provenance_tags") or []),
                "tags": list(case.get("tags") or []),
                "expected": dict(case.get("expected") or {}),
            }
            for case in cases
        ]
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


def _public_boundary_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "semantic_family": str(case.get("semantic_family") or ""),
            "boundary_kind": str(case.get("boundary_kind") or ""),
            "false_presence_severity": str(case.get("false_presence_severity") or ""),
            "synthetic_provenance_tags": list(case.get("synthetic_provenance_tags") or []),
            "final_lock_candidates": list(case.get("final_lock_candidates") or []),
            "expected_final_source": str(case.get("expected_final_source") or ""),
            "expected_presence_retained": bool(case.get("expected_presence_retained")),
            "reason_code": str(case.get("reason_code") or ""),
        }
        for case in cases
    ]


_PRESENCE_ARTIFACT_FORBIDDEN_KEYS = {
    "arbiter_reason",
    "case_design_note",
    "case_source_reference",
    "content",
    "current_user_message",
    "design_note",
    "dialogue",
    "error",
    "human_justification",
    "raw_text",
}


def assert_presence_campaign_content_free(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = _PRESENCE_ARTIFACT_FORBIDDEN_KEYS.intersection(value)
        if forbidden:
            raise ValueError(f"presence campaign contains forbidden keys: {sorted(forbidden)}")
        for child in value.values():
            assert_presence_campaign_content_free(child)
        return
    if isinstance(value, list):
        for child in value:
            assert_presence_campaign_content_free(child)


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
        f"{(top.get('summary') or {}).get('passes')}/{(top.get('summary') or {}).get('cases')} pass, "
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
    if "repetition_stability_rate" in summary:
        lines.extend(
            [
                f"- Stabilite: {_format_rate(summary.get('repetition_stability_rate'))}",
                f"- Rappel Presence requis: {_format_rate(summary.get('required_presence_rate'))}",
                f"- Seuils de securite: {'OK' if summary.get('safety_thresholds_met') else 'ECHEC'}",
            ]
        )
        threshold_failures = list(summary.get("safety_threshold_failures") or [])
        unstable_case_ids = list(summary.get("unstable_case_ids") or [])
        if threshold_failures:
            lines.append(f"- Seuils rates: `{', '.join(threshold_failures)}`")
        if unstable_case_ids:
            lines.append(f"- Cas instables: `{', '.join(unstable_case_ids)}`")
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
    if campaign.get("content_free_decision_artifact") and not campaign.get(
        "benchmark_decision_ready"
    ):
        if campaign.get("dry_run"):
            return (
                "Campagne dry-run: aucune route provider n'a ete observee et aucune "
                "decision de benchmark n'est possible. Aucun changement de production "
                "n'est propose par cette campagne."
            )
        failures = [
            str(result.get("model"))
            for result in results
            if not (result.get("summary") or {}).get("safety_thresholds_met")
        ]
        if failures:
            return (
                "Decision de benchmark non prete: au moins un seuil de securite "
                f"echoue pour `{', '.join(failures)}`. Aucun changement de production "
                "n'est propose par cette campagne."
            )
        return (
            "Decision de benchmark non prete: repetitions ou routes provider "
            "incompletes. Aucun changement de production n'est propose par cette "
            "campagne."
        )
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


def _format_rate(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{100.0 * float(value):.1f}%"
    return "n/a"


def _format_threshold_status(summary: dict[str, Any]) -> str:
    if "safety_thresholds_met" not in summary:
        return "n/a"
    return "OK" if summary.get("safety_thresholds_met") else "ECHEC"
