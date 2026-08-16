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
from benchmark.suites.identity_extractor import campaign as identity_campaign
from benchmark.suites.identity_periodic import adapter as identity_periodic_adapter
from benchmark.suites.stimmung import campaign as stimmung_campaign
from benchmark.suites.summary import adapter as summary_adapter
from benchmark.suites.summary import campaign as summary_campaign
from benchmark.suites.validation_agent import adapter as validation_agent_adapter
from benchmark.suites.validation_agent import campaign as validation_agent_campaign
from benchmark.suites.web_search import adapter as web_search_adapter
from benchmark.suites.web_search import campaign as web_search_campaign


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

DEFAULT_IDENTITY_EXTRACTOR_MODELS = [
    "openai/gpt-5.4-mini",
    "anthropic/claude-haiku-4.5",
    "google/gemini-3.1-flash-lite",
    "mistralai/mistral-small-2603",
]

DEFAULT_IDENTITY_PERIODIC_MODELS = [
    "anthropic/claude-haiku-4.5",
]

DEFAULT_STIMMUNG_MODELS = [
    "openai/gpt-5.4-mini",
    "anthropic/claude-haiku-4.5",
    "google/gemini-3.1-flash-lite",
    "mistralai/mistral-small-2603",
]

DEFAULT_VALIDATION_AGENT_MODELS = [
    "openai/gpt-5.4-mini",
    "google/gemini-3.1-flash-lite",
    "mistralai/mistral-small-2603",
    "anthropic/claude-haiku-4.5",
]

DEFAULT_WEB_SEARCH_MODELS = [
    "openai/gpt-5.1",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FridaDev model caller benchmarks.")
    suite_choices = [
        "arbiter",
        "summary",
        "identity_extractor",
        "identity_periodic",
        "stimmung",
        "validation_agent",
        "web_search",
    ]
    parser.add_argument("suite_positional", nargs="?", choices=suite_choices)
    parser.add_argument("--suite", choices=suite_choices, default=None)
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fixture-set", default="diagnostic")
    parser.add_argument("--arbiter-tournament", action="store_true")
    parser.add_argument("--summary-input-file", default=None)
    parser.add_argument("--summary-max-tokens", type=int, default=None)
    parser.add_argument("--validation-agent-max-tokens", type=int, default=None)
    parser.add_argument("--validation-agent-compare-with", default=None)
    parser.add_argument("--web-search-arms", nargs="*", default=None)
    parser.add_argument("--web-search-max-results", type=int, default=web_search_adapter.DEFAULT_MAX_RESULTS)
    parser.add_argument("--web-search-max-total-results", type=int, default=web_search_adapter.DEFAULT_MAX_TOTAL_RESULTS)
    parser.add_argument("--web-search-context-size", default=web_search_adapter.DEFAULT_SEARCH_CONTEXT_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    repo_root = REPO_ROOT
    suite = args.suite or args.suite_positional or "arbiter"
    campaign_id = args.campaign_id
    if not campaign_id:
        if args.dry_run:
            campaign_id = f"{suite}-dry-run"
        else:
            raise SystemExit("--campaign-id is required outside dry-run mode")

    if suite == "summary":
        default_models = DEFAULT_SUMMARY_MODELS
    elif suite == "identity_extractor":
        default_models = DEFAULT_IDENTITY_EXTRACTOR_MODELS
    elif suite == "identity_periodic":
        default_models = DEFAULT_IDENTITY_PERIODIC_MODELS
    elif suite == "stimmung":
        default_models = DEFAULT_STIMMUNG_MODELS
    elif suite == "validation_agent":
        default_models = DEFAULT_VALIDATION_AGENT_MODELS
    elif suite == "web_search":
        default_models = DEFAULT_WEB_SEARCH_MODELS
    else:
        default_models = DEFAULT_ARBITER_MODELS
    if args.models is None:
        models = list(default_models)
    else:
        models = ensure_unique_models(args.models)
    if not models:
        raise SystemExit("at least one model is required")
    if suite == "arbiter" and "openai/gpt-5.4-nano" in models:
        raise SystemExit("openai/gpt-5.4-nano is intentionally excluded from the first arbiter campaign")
    output_dir = args.output_dir or f"benchmark/results/{suite}"

    config = CampaignConfig(
        campaign_id=campaign_id,
        suite=suite,
        repo_root=repo_root,
        output_dir=(repo_root / output_dir).resolve(),
        models=models,
        dry_run=bool(args.dry_run),
        timeout_s=int(args.timeout_s),
    )

    web_search_arms_for_client: list[str] | None = None
    if suite == "web_search":
        try:
            web_search_arms_for_client = web_search_adapter.normalize_arms(args.web_search_arms)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    needs_openrouter_client = not config.dry_run and (
        suite != "web_search"
        or any(str(arm).startswith("openrouter_") for arm in (web_search_arms_for_client or []))
    )
    client = None if not needs_openrouter_client else OpenRouterClient.from_env(
        base_url=args.base_url,
        title=f"FridaDev/Benchmark/{suite.title()}",
    )

    if suite == "summary":
        if not args.summary_input_file:
            raise SystemExit("--summary-input-file is required for the summary suite")
        result = summary_campaign.run_summary_human_reading_campaign(
            config=config,
            input_path=(repo_root / args.summary_input_file).resolve()
            if not Path(args.summary_input_file).is_absolute()
            else Path(args.summary_input_file).resolve(),
            client=client,
            generation_params=summary_adapter.generation_params(
                max_tokens=args.summary_max_tokens,
            ),
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['markdown_path']}")
        return 0

    if suite == "identity_extractor":
        result = identity_campaign.run_identity_human_campaign(
            config=config,
            client=client,
            fixture_set=args.fixture_set,
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['technical_path']}")
        print(f"wrote {result['hermeneutic_path']}")
        for output_file in result.get("output_files") or []:
            print(f"wrote {output_file}")
        return 0

    if suite == "identity_periodic":
        from benchmark.suites.identity_periodic import campaign as identity_periodic_campaign

        result = identity_periodic_campaign.run_identity_periodic_smoke_campaign(
            config=config,
            client=client,
            fixture_set=args.fixture_set,
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['markdown_path']}")
        print(
            "threshold "
            f"BUFFER_TARGET_PAIRS={identity_periodic_adapter.buffer_target_pairs(repo_root)} "
            "(complete user/assistant buffer pairs)"
        )
        return 0

    if suite == "stimmung":
        result = stimmung_campaign.run_stimmung_primary_campaign(
            config=config,
            client=client,
            fixture_set=args.fixture_set,
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['markdown_path']}")
        return 0

    if suite == "validation_agent":
        result = validation_agent_campaign.run_validation_agent_campaign(
            config=config,
            client=client,
            generation_params=validation_agent_adapter.generation_params(
                max_tokens=args.validation_agent_max_tokens,
            ),
            comparison_path=(Path(args.validation_agent_compare_with) if args.validation_agent_compare_with else None),
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['markdown_path']}")
        return 0

    if suite == "web_search":
        arms = web_search_arms_for_client or web_search_adapter.normalize_arms(args.web_search_arms)
        result = web_search_campaign.run_web_search_campaign(
            config=config,
            client=client,
            arms=arms,
            max_results=args.web_search_max_results,
            max_total_results=args.web_search_max_total_results,
            search_context_size=args.web_search_context_size,
        )
        print(f"wrote {result['json_path']}")
        print(f"wrote {result['jsonl_path']}")
        print(f"wrote {result['markdown_path']}")
        return 0

    if args.arbiter_tournament:
        tournament = arbiter_tournament.run_tournament(
            campaign_id=campaign_id,
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
