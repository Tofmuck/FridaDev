from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.stimmung import adapter, scorer


def run_stimmung_primary_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "primary",
) -> dict[str, Any]:
    campaign = build_stimmung_primary_campaign(config=config, client=client, fixture_set=fixture_set)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{config.campaign_id}.json"
    markdown_path = output_dir / f"{config.campaign_id}.md"
    write_json(json_path, campaign)
    markdown_path.write_text(render_markdown_report(campaign), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def build_stimmung_primary_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    fixture_set: str = "primary",
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
                provider = _dry_provider(case)
                score = scorer.score_response(case, provider.get("raw_text"), None)
            else:
                if client is None:
                    raise RuntimeError("client is required outside dry-run mode")
                provider = client.chat_completion(payload, caller="stimmung_agent", timeout_s=config.timeout_s)
                score = scorer.score_response(case, provider.get("raw_text"), provider.get("error"))

            calls.append(
                {
                    "case_id": case["id"],
                    "case_tags": list(case.get("tags") or []),
                    "case_design_note": str(case.get("design_note") or ""),
                    "expected_acceptables": dict(case.get("expected_acceptables") or {}),
                    "provider": provider,
                    "request_signature": request_signature,
                    "score": score,
                }
            )
        results.append({"model": model, "summary": scorer.summarize_model(model, calls), "calls": calls})

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "stimmung",
        "caller": "stimmung_agent_primary",
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
        "production_runtime_changed": False,
        "fallback_benchmarked": False,
        "human_decision_required": True,
        "results": results,
    }


def render_markdown_report(campaign: dict[str, Any]) -> str:
    params = campaign.get("generation_params") or {}
    lines = [
        f"# Benchmark stimmung agent primaire - {campaign['campaign_id']}",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)",
        f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)",
        f"- temperature: `{params.get('temperature')}`",
        f"- top_p: `{params.get('top_p')}`",
        f"- max_tokens: `{params.get('max_tokens')}`",
        f"- timeout_s: `{campaign.get('timeout_s')}`",
        f"- Production runtime changed: `{campaign.get('production_runtime_changed')}`",
        f"- Fallback benchmarked: `{campaign.get('fallback_benchmarked')}`",
        "",
        "## Ce que cette campagne mesure",
        "",
        "Elle compare le modele primaire du `stimmung_agent` sur le vrai prompt de production.",
        "Elle teste la lecture affective locale du tour courant: assez sensible pour ne pas etre plate, assez prudente pour ne pas psychologiser.",
        "",
        "## Ce que cette campagne ne prouve pas",
        "",
        "- Elle ne choisit pas automatiquement le modele de production.",
        "- Elle ne benchmarke pas le fallback.",
        "- Elle ne teste pas le noeud hermeneutique complet.",
        "- Les cas sont artificiels et diagnostiques, pas un replay de conversations privees.",
        "",
        "## Synthese technique",
        "",
        "| Modele | Provider OK | JSON valide | Schema valide | Pass souple | Avoid hits | Neutre surcode | Trop plat | Latence moy. | Cout estime | Completion tok. moy. | Finish | Verdict provisoire |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
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
                    f"{float(summary.get('hard_pass_rate') or 0.0):.0%}",
                    str(summary.get("avoid_hit_count")),
                    str(summary.get("neutral_overcoded_count")),
                    str(summary.get("flat_miss_count")),
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
    lines.extend(["", "## Cas testes", ""])
    for case in campaign.get("cases", []):
        expected = case.get("expected_acceptables") or {}
        lines.extend(
            [
                f"### {case['id']}",
                "",
                f"> {case['current_user_message']}",
                "",
                f"- Tags: `{', '.join(case.get('tags') or [])}`",
                f"- Attendus souples: dominant parmi `{', '.join(expected.get('dominant_tones') or [])}`",
                f"- Note: {case['design_note']}",
                "",
            ]
        )

    lines.extend(["## Lecture hermeneutique par modele", ""])
    for result in campaign.get("results", []):
        lines.extend(_model_reading_lines(result))

    lines.extend(_divergence_lines(campaign))
    lines.extend(
        [
            "## Verdict provisoire",
            "",
            "Le verdict reste volontairement provisoire: cette campagne fournit une matiere comparative pour Tof, sans changement de production.",
            "",
        ]
    )
    return "\n".join(lines)


def _dry_provider(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected_acceptables") or {}
    tone = str((expected.get("dominant_tones") or ["neutralite"])[0])
    max_strength = expected.get("max_strength")
    strength = 3 if tone == "neutralite" else 6
    if isinstance(max_strength, int):
        strength = min(strength, max_strength)
    raw = json.dumps(
        {
            "schema_version": "v1",
            "present": True,
            "tones": [{"tone": tone, "strength": max(1, min(10, strength))}],
            "dominant_tone": tone,
            "confidence": 0.72,
        },
        ensure_ascii=False,
    )
    return {
        "ok": True,
        "status_code": None,
        "elapsed_ms": 0.0,
        "error": None,
        "raw_text": raw,
        "finish_reason": "dry_run",
        "native_finish_reason": "dry_run",
        "usage": {"completion_tokens": 0},
        "cost_estimate_usd": None,
        "cost_estimate_source": "dry_run",
    }


def _public_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "current_user_message": case["current_user_message"],
            "recent_turns": case.get("recent_turns") or [],
            "tags": list(case.get("tags") or []),
            "design_note": str(case.get("design_note") or ""),
            "expected_acceptables": dict(case.get("expected_acceptables") or {}),
        }
        for case in cases
    ]


def _model_reading_lines(result: dict[str, Any]) -> list[str]:
    summary = result.get("summary") or {}
    calls = result.get("calls") or []
    lines = [
        f"### `{result.get('model')}`",
        "",
        f"- Verdict provisoire: {summary.get('provisional_verdict')}",
        f"- Notes techniques: {summary.get('notes')}",
        f"- Dominantes produites: `{summary.get('dominant_counts')}`",
    ]
    examples = _interesting_examples(calls)
    if not examples:
        lines.append("- Aucun ecart souple majeur releve par le scorer.")
    else:
        lines.append("- Ecarts utiles a lire:")
        for call in examples[:6]:
            score = call.get("score") or {}
            provider = call.get("provider") or {}
            lines.append(
                "  - "
                f"`{call.get('case_id')}`: dominant=`{score.get('dominant_tone')}`, "
                f"tones=`{_tones_label(score.get('tones') or [])}`, "
                f"hard_pass=`{score.get('hard_pass')}`, "
                f"error=`{score.get('error') or provider.get('error') or ''}`"
            )
    lines.append("")
    return lines


def _overall_reading_lines(campaign: dict[str, Any]) -> list[str]:
    lines = ["", "## Lecture synthetique post-run", ""]
    results = campaign.get("results") or []
    if not results:
        return lines + ["Aucun resultat a lire.", ""]

    ranked_by_pass = sorted(
        results,
        key=lambda result: (
            float((result.get("summary") or {}).get("hard_pass_rate") or 0.0),
            -int((result.get("summary") or {}).get("avoid_hit_count") or 0),
            -int((result.get("summary") or {}).get("neutral_overcoded_count") or 0),
        ),
        reverse=True,
    )
    best = ranked_by_pass[0]
    lines.append(
        "Le meilleur signal quantitatif souple revient ici a "
        f"`{best.get('model')}`, avec "
        f"{float((best.get('summary') or {}).get('hard_pass_rate') or 0.0):.0%} de pass souple. "
        "Ce n'est pas une decision de production: il faut lire les divergences, surtout les cas neutres et les pieges de contexte."
    )
    lines.append("")

    for result in results:
        summary = result.get("summary") or {}
        lines.append(f"- `{result.get('model')}`: {_qualitative_profile(summary)}")
    lines.append("")
    return lines


def _qualitative_profile(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    if float(summary.get("schema_valid_rate") or 0.0) < 1.0:
        parts.append("fragile sur le schema strict")
    else:
        parts.append("schema strict stable")
    avoid_hits = int(summary.get("avoid_hit_count") or 0)
    if avoid_hits:
        parts.append(f"{avoid_hits} ton(s) explicitement a eviter touches")
    else:
        parts.append("aucun ton interdit touche")
    neutral_overcoded = int(summary.get("neutral_overcoded_count") or 0)
    if neutral_overcoded:
        parts.append(f"tendance a surcoder {neutral_overcoded} cas neutres")
    else:
        parts.append("neutralite bien tenue")
    flat_miss = int(summary.get("flat_miss_count") or 0)
    if flat_miss:
        parts.append(f"{flat_miss} cas marques lus trop platement")
    else:
        parts.append("pas de platitude forte detectee")
    parts.append(f"verdict provisoire: {summary.get('provisional_verdict')}")
    return "; ".join(parts) + "."


def _interesting_examples(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    interesting: list[dict[str, Any]] = []
    for call in calls:
        score = call.get("score") or {}
        if not score.get("hard_pass"):
            interesting.append(call)
    return interesting


def _divergence_lines(campaign: dict[str, Any]) -> list[str]:
    lines = ["## Divergences entre modeles", ""]
    models = [result.get("model") for result in campaign.get("results", [])]
    for case in campaign.get("cases", []):
        dominant_by_model: dict[str, str] = {}
        for result in campaign.get("results", []):
            call = _call_by_case(result, case["id"])
            if call:
                dominant = (call.get("score") or {}).get("dominant_tone")
                dominant_by_model[str(result.get("model"))] = str(dominant)
        if len(set(dominant_by_model.values())) <= 1:
            continue
        values = ", ".join(f"`{model}`={tone}" for model, tone in dominant_by_model.items())
        lines.append(f"- `{case['id']}`: {values}")
    if len(lines) == 2:
        lines.append("- Aucune divergence de dominante detectee.")
    lines.append("")
    return lines


def _call_by_case(result: dict[str, Any], case_id: str) -> dict[str, Any] | None:
    for call in result.get("calls", []):
        if call.get("case_id") == case_id:
            return call
    return None


def _tones_label(tones: list[dict[str, Any]]) -> str:
    return ", ".join(f"{item.get('tone')}:{item.get('strength')}" for item in tones)


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"
