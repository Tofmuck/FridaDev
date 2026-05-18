from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.core.campaign import CampaignConfig, run_model_campaign, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.core.reporting import write_markdown_report
from benchmark.suites.arbiter import adapter, scorer


ROUND1_MODELS = [
    "openai/gpt-5.4-mini",
    "google/gemini-3.1-flash-lite",
    "qwen/qwen3.6-flash",
    "mistralai/mistral-small-2603",
]


def run_tournament(
    *,
    campaign_id: str,
    repo_root: Path,
    output_dir: Path,
    dry_run: bool,
    timeout_s: int,
    client: OpenRouterClient | None,
) -> dict[str, Any]:
    round1 = _run_round(
        campaign_id=f"{campaign_id}-round1",
        repo_root=repo_root,
        output_dir=output_dir,
        fixture_set="tournament_round1",
        models=ROUND1_MODELS,
        dry_run=dry_run,
        timeout_s=timeout_s,
        client=client,
    )
    finalists = _select_finalists(round1, count=2)
    final = _run_round(
        campaign_id=f"{campaign_id}-final",
        repo_root=repo_root,
        output_dir=output_dir,
        fixture_set="tournament_final",
        models=finalists,
        dry_run=dry_run,
        timeout_s=timeout_s,
        client=client,
    )
    summary = _tournament_summary(round1, final, finalists)
    return {"round1": round1, "final": final, "summary": summary}


def write_tournament_artifacts(output_dir: Path, campaign_id: str, tournament: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    round1 = tournament["round1"]
    final = tournament["final"]
    write_json(output_dir / f"{campaign_id}-round1.json", round1)
    write_markdown_report(output_dir / f"{campaign_id}-round1.md", round1)
    write_json(output_dir / f"{campaign_id}-final.json", final)
    write_markdown_report(output_dir / f"{campaign_id}-final.md", final)
    write_json(output_dir / f"{campaign_id}-summary.json", tournament["summary"])
    (output_dir / f"{campaign_id}-summary.md").write_text(
        render_tournament_summary(tournament["summary"]),
        encoding="utf-8",
    )


def render_tournament_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"# Arbiter tournament - {summary['campaign_id']}",
        "",
        "## Round 1",
        "",
        "| Model | Weighted score | Hard score | FP | FN | Provider errors | Cost est. | Avg latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["round1_ranking"]:
        lines.append(_summary_row(item))
    lines.extend(
        [
            "",
            f"Finalists: {', '.join(f'`{model}`' for model in summary['finalists'])}",
            "",
            "## Final",
            "",
            "| Model | Weighted score | Hard score | FP | FN | Provider errors | Cost est. | Avg latency |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in summary["final_ranking"]:
        lines.append(_summary_row(item))
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Pure relevance winner: `{summary['pure_relevance_winner']}`",
            f"- Relevance/cost/latency winner: `{summary['value_winner']}`",
            f"- Baseline comparison: {summary['baseline_comparison']}",
            f"- Recommendation: {summary['recommendation']}",
            "",
            "## Divergences",
            "",
        ]
    )
    if not summary["divergences"]:
        lines.append("- No model divergence on keep/drop decisions.")
    else:
        shown = min(20, len(summary["divergences"]))
        lines.append(f"- Showing {shown} of {len(summary['divergences'])} divergent cases.")
        for item in summary["divergences"][:20]:
            lines.append(
                f"- `{item['round']}` / `{item['case_id']}` expected `{item['expected_keep_ids']}`: "
                + ", ".join(f"`{model}` -> `{kept}`" for model, kept in item["by_model"].items())
            )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- Real cases are anonymized or reformulated from FridaDev work patterns.",
            "- Gold labels are human development labels, not previous arbiter decisions.",
            "- No production model or runtime setting is changed by this tournament.",
        ]
    )
    return "\n".join(lines) + "\n"


def _run_round(
    *,
    campaign_id: str,
    repo_root: Path,
    output_dir: Path,
    fixture_set: str,
    models: list[str],
    dry_run: bool,
    timeout_s: int,
    client: OpenRouterClient | None,
) -> dict[str, Any]:
    config = CampaignConfig(
        campaign_id=campaign_id,
        suite="arbiter",
        repo_root=repo_root,
        output_dir=output_dir,
        models=models,
        dry_run=dry_run,
        timeout_s=timeout_s,
    )
    campaign = run_model_campaign(
        config=config,
        prompt_path=adapter.prompt_path(repo_root),
        fixture_path=adapter.fixture_path(repo_root, fixture_set=fixture_set),
        generation_params=adapter.GENERATION_PARAMS,
        cases=adapter.load_cases(repo_root, fixture_set=fixture_set),
        build_payload=adapter.build_payload,
        score_response=scorer.score_response,
        summarize_model=scorer.summarize_model,
        client=client,
    )
    campaign["fixture_set"] = fixture_set
    campaign["campaign_verdict"] = scorer.campaign_verdict(campaign["results"])
    campaign["divergences"] = _divergences(campaign)
    campaign["origin_counts"] = _origin_counts(campaign)
    return campaign


def _select_finalists(round1: dict[str, Any], *, count: int) -> list[str]:
    summaries = [dict(result["summary"], model=result["model"]) for result in round1["results"]]
    return [item["model"] for item in scorer.rank_summaries(summaries)[:count]]


def _tournament_summary(round1: dict[str, Any], final: dict[str, Any], finalists: list[str]) -> dict[str, Any]:
    round1_summaries = [dict(result["summary"], model=result["model"]) for result in round1["results"]]
    final_summaries = [dict(result["summary"], model=result["model"]) for result in final["results"]]
    final_ranking = scorer.rank_summaries(final_summaries)
    value_ranking = scorer.value_rank_summaries(final_summaries)
    baseline = next((item for item in round1_summaries if item["model"] == "openai/gpt-5.4-mini"), None)
    pure_winner = final_ranking[0]["model"] if final_ranking else ""
    value_winner = value_ranking[0]["model"] if value_ranking else ""
    recommendation = _recommendation(final_ranking, value_ranking)
    return {
        "campaign_id": final["campaign_id"].removesuffix("-final"),
        "round1_case_count": round1["case_count"],
        "final_case_count": final["case_count"],
        "round1_origin_counts": round1["origin_counts"],
        "final_origin_counts": final["origin_counts"],
        "finalists": finalists,
        "round1_ranking": scorer.rank_summaries(round1_summaries),
        "final_ranking": final_ranking,
        "value_ranking": value_ranking,
        "pure_relevance_winner": pure_winner,
        "value_winner": value_winner,
        "baseline_comparison": _baseline_comparison(baseline, finalists, final_summaries),
        "recommendation": recommendation,
        "divergences": [
            *[dict(item, round="round1") for item in round1["divergences"]],
            *[dict(item, round="final") for item in final["divergences"]],
        ],
    }


def _divergences(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    by_case: dict[str, dict[str, Any]] = {}
    for result in campaign["results"]:
        model = result["model"]
        for call in result["calls"]:
            item = by_case.setdefault(
                call["case_id"],
                {"case_id": call["case_id"], "expected_keep_ids": call["expected_keep_ids"], "by_model": {}},
            )
            item["by_model"][model] = call["score"].get("predicted_keep_ids") or []
    return [item for item in by_case.values() if len({tuple(v) for v in item["by_model"].values()}) > 1]


def _origin_counts(campaign: dict[str, Any]) -> dict[str, int]:
    seen: dict[str, str] = {}
    for result in campaign["results"][:1]:
        for call in result["calls"]:
            seen[call["case_id"]] = call.get("case_origin") or "unknown"
    counts: dict[str, int] = {}
    for origin in seen.values():
        counts[origin] = counts.get(origin, 0) + 1
    return counts


def _summary_row(item: dict[str, Any]) -> str:
    cost = item.get("cost_estimate_usd")
    cost_text = f"${float(cost):.6f}" if isinstance(cost, (int, float)) else "n/a"
    return (
        f"| `{item['model']}` | {float(item.get('weighted_score') or 0.0):.1f} | "
        f"{float(item.get('hard_weighted_score') or 0.0):.1f} | {item.get('false_positives', 0)} | "
        f"{item.get('false_negatives', 0)} | {float(item.get('provider_error_rate') or 0.0):.0%} | "
        f"{cost_text} | {float(item.get('avg_latency_ms') or 0.0):.0f} ms |"
    )


def _baseline_comparison(baseline: dict[str, Any] | None, finalists: list[str], final_summaries: list[dict[str, Any]]) -> str:
    if baseline is None:
        return "Baseline openai/gpt-5.4-mini was not present in round 1."
    if "openai/gpt-5.4-mini" not in finalists:
        return "Baseline openai/gpt-5.4-mini did not reach the final."
    final_baseline = next((item for item in final_summaries if item["model"] == "openai/gpt-5.4-mini"), None)
    if final_baseline is None:
        return "Baseline reached the final but has no final summary."
    return (
        f"Baseline final weighted score {final_baseline['weighted_score']:.1f}, "
        f"FP={final_baseline['false_positives']}, FN={final_baseline['false_negatives']}."
    )


def _recommendation(final_ranking: list[dict[str, Any]], value_ranking: list[dict[str, Any]]) -> str:
    if not final_ranking:
        return "Tester encore: no final result was produced."
    best = final_ranking[0]
    ties = [
        item
        for item in final_ranking
        if float(item.get("weighted_score") or 0.0) == float(best.get("weighted_score") or 0.0)
        and int(item.get("false_positives") or 0) == int(best.get("false_positives") or 0)
    ]
    if len(ties) > 1:
        return (
            "Tester encore avant de decider: pertinence pure trop serree entre "
            + ", ".join(item["model"] for item in ties)
            + "."
        )
    value_best = value_ranking[0] if value_ranking else best
    if best["model"] == "openai/gpt-5.4-mini":
        return "Garder gpt-5.4-mini pour l'instant; il gagne la finale en pertinence pure."
    if best["model"] == value_best["model"]:
        return f"Basculer vers {best['model']} devient defendable au prochain lot de decouplage."
    return f"Tester encore: {best['model']} gagne en pertinence pure mais {value_best['model']} gagne en cout/latence."
