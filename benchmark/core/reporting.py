from __future__ import annotations

from pathlib import Path
from typing import Any


def write_markdown_report(path: Path, campaign: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(campaign), encoding="utf-8")


def render_markdown_report(campaign: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Benchmark {campaign['suite']} - {campaign['campaign_id']}")
    lines.append("")
    lines.append(f"- Created UTC: `{campaign['created_at_utc']}`")
    lines.append(f"- Dry run: `{campaign['dry_run']}`")
    lines.append(f"- Prompt: `{campaign['prompt_path']}` (`{campaign['prompt_sha256'][:12]}`)")
    lines.append(f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)")
    params = campaign.get("generation_params") or {}
    lines.append(
        "- Fixed parameters: "
        f"`temperature={params.get('temperature')}`, "
        f"`top_p={params.get('top_p')}`, "
        f"`max_tokens={params.get('max_tokens')}`"
    )
    lines.append("")
    lines.append("## What this campaign measures")
    lines.append("")
    lines.append("- Whether each model returns valid arbiter JSON for the production arbiter prompt.")
    lines.append("- Whether each model keeps or drops the expected memory candidates on diagnostic fixtures.")
    lines.append("- False positives, false negatives, latency, provider errors and estimated cost when available.")
    lines.append("")
    lines.append("## What this campaign does not prove")
    lines.append("")
    lines.append("- It is not a general model benchmark.")
    lines.append("- It does not prove behavior on the full live memory distribution.")
    lines.append("- It does not change production runtime settings or choose the final decoupled arbiter slot by itself.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Model | Weighted score | Hard score | JSON valid | Schema valid | FP | FN | Avg latency | Cost est. | Provider errors | Verdict | Notes |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for result in campaign.get("results", []):
        summary = result["summary"]
        weighted_score = float(summary.get("weighted_score", summary.get("score", 0.0)) or 0.0)
        hard_score = float(summary.get("hard_weighted_score", weighted_score) or 0.0)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{result['model']}`",
                    f"{weighted_score:.1f}",
                    f"{hard_score:.1f}",
                    f"{summary['json_valid_rate']:.0%}",
                    f"{summary['schema_valid_rate']:.0%}",
                    str(summary["false_positives"]),
                    str(summary["false_negatives"]),
                    f"{summary['avg_latency_ms']:.0f} ms",
                    _format_cost(summary.get("cost_estimate_usd")),
                    f"{summary['provider_error_rate']:.0%}",
                    summary["verdict"],
                    summary["notes"],
                ]
            )
            + " |"
        )
    lines.append("")
    verdict = campaign.get("campaign_verdict")
    if isinstance(verdict, dict):
        lines.append("## Campaign verdict")
        lines.append("")
        lines.append(f"- Verdict: `{verdict.get('verdict', 'n/a')}`")
        summary = str(verdict.get("summary") or "").strip()
        if summary:
            lines.append(f"- Summary: {summary}")
        next_step = str(verdict.get("next_step") or "").strip()
        if next_step:
            lines.append(f"- Next step: {next_step}")
        lines.append("")
    lines.append("## Fixture limits")
    lines.append("")
    lines.append("- The fixture set is intentionally small and diagnostic.")
    lines.append("- It emphasizes French memory arbitration, redundancy, weak circumstantial memories and temporal claims.")
    lines.append("- A production switch still needs caller-by-caller review and a bounded decoupling lot.")
    return "\n".join(lines) + "\n"


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"
