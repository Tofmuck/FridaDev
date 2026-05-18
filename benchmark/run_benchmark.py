#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.core.campaign import CampaignConfig, ensure_unique_models, run_model_campaign, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.core.reporting import write_markdown_report
from benchmark.suites.arbiter import adapter as arbiter_adapter
from benchmark.suites.arbiter import scorer as arbiter_scorer
from benchmark.suites.arbiter import tournament as arbiter_tournament
from benchmark.suites.summary import campaign as summary_campaign


DEFAULT_ARBITER_MODELS = [
    "openai/gpt-5.4-mini",
    "google/gemini-3.1-flash-lite",
    "qwen/qwen3.6-flash",
    "mistralai/mistral-small-2603",
]

DEFAULT_SUMMARY_MODELS = [
    "openai/gpt-5.4-mini",
    "anthropic/claude-sonnet-4.6",
    "mistralai/mistral-medium-3-5",
    "google/gemini-3.1-pro-preview",
    "qwen/qwen3.5-plus-20260420",
    "mistralai/mistral-small-2603",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FridaDev model caller benchmarks.")
    parser.add_argument("--suite", choices=["arbiter", "summary"], default="arbiter")
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fixture-set", default="diagnostic")
    parser.add_argument("--arbiter-tournament", action="store_true")
    parser.add_argument("--summary-input-file", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    repo_root = REPO_ROOT
    default_models = DEFAULT_SUMMARY_MODELS if args.suite == "summary" else DEFAULT_ARBITER_MODELS
    if args.models is None:
        models = list(default_models)
    else:
        models = ensure_unique_models(args.models)
    if not models:
        raise SystemExit("at least one model is required")
    if args.suite == "arbiter" and "openai/gpt-5.4-nano" in models:
        raise SystemExit("openai/gpt-5.4-nano is intentionally excluded from the first arbiter campaign")
    output_dir = args.output_dir or f"benchmark/results/{args.suite}"

    config = CampaignConfig(
        campaign_id=args.campaign_id,
        suite=args.suite,
        repo_root=repo_root,
        output_dir=(repo_root / output_dir).resolve(),
        models=models,
        dry_run=bool(args.dry_run),
        timeout_s=int(args.timeout_s),
    )

    client = None if config.dry_run else OpenRouterClient.from_env(
        base_url=args.base_url,
        title=f"FridaDev/Benchmark/{args.suite.title()}",
    )

    if args.suite == "summary":
        if not args.summary_input_file:
            raise SystemExit("--summary-input-file is required for the summary suite")
        result = summary_campaign.run_summary_human_reading_campaign(
            config=config,
            input_path=(repo_root / args.summary_input_file).resolve()
            if not Path(args.summary_input_file).is_absolute()
            else Path(args.summary_input_file).resolve(),
            client=client,
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['markdown_path']}")
        return 0

    if args.arbiter_tournament:
        tournament = arbiter_tournament.run_tournament(
            campaign_id=args.campaign_id,
            repo_root=repo_root,
            output_dir=config.output_dir,
            dry_run=config.dry_run,
            timeout_s=config.timeout_s,
            client=client,
        )
        arbiter_tournament.write_tournament_artifacts(config.output_dir, args.campaign_id, tournament)
        print(f"wrote tournament artifacts under {config.output_dir}")
        return 0

    campaign = run_model_campaign(
        config=config,
        prompt_path=arbiter_adapter.prompt_path(repo_root),
        fixture_path=arbiter_adapter.fixture_path(repo_root, fixture_set=args.fixture_set),
        generation_params=arbiter_adapter.GENERATION_PARAMS,
        cases=arbiter_adapter.load_cases(repo_root, fixture_set=args.fixture_set),
        build_payload=arbiter_adapter.build_payload,
        score_response=arbiter_scorer.score_response,
        summarize_model=arbiter_scorer.summarize_model,
        client=client,
    )
    campaign["campaign_verdict"] = arbiter_scorer.campaign_verdict(campaign["results"])

    json_path = config.output_dir / f"{config.campaign_id}.json"
    markdown_path = config.output_dir / f"{config.campaign_id}.md"
    write_json(json_path, campaign)
    write_markdown_report(markdown_path, campaign)
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
