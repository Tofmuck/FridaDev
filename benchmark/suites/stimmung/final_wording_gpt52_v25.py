from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import json
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from benchmark.core import openrouter as openrouter_transport
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.stimmung import final_wording_execution_v2 as execution_v2
from benchmark.suites.stimmung import final_wording_protocol_v2 as v24
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


PROTOCOL_VERSION = "lot4c4_final_wording_gpt52_replication_v2_5"
ARTIFACT_VERSION = "lot4c4_final_wording_gpt52_results_v2_5"
FREEZE_MANIFEST = "stimmung_final_wording_freeze_v2_5.json"
BASELINE_HEAD = "7fcf26d8d3991b6d64f586b89025b9404316e30e"
V24_FREEZE_SHA256 = "736cb6d83ab8c0626de8f7cc4cf3ba4a9c7ab494d69353a2d0383f361ca25f91"
TARGET_MODEL = "openai/gpt-5.2"
ALLOWED_OBSERVED_MODELS = {TARGET_MODEL}
REASONING = {"effort": "high", "exclude": True}
MAX_TOKENS = 8192
TIMEOUT_S = 900
EXPECTED_CALLS = 24
ABSOLUTE_COST_CAP_USD = 4.0
PRICING_OBSERVED_AT = "2026-09-01"
PRICING_USD_PER_TOKEN = {"prompt": 0.00000175, "completion": 0.000014}
EXPECTED_CONTEXT_LENGTH = 400_000
EXPECTED_MAX_COMPLETION_TOKENS = 128_000
REQUIRED_ENDPOINT_CAPABILITIES = {
    "reasoning": ("reasoning",),
    "output_token_limit": ("max_tokens",),
}
V25_MUTATION_MATRIX = (
    "model_other_than_openai_gpt_5_2",
    "reasoning_effort_not_high_or_visible",
    "gpt_5_1_provenance_presented_as_gpt_5_2",
    "call_count_exceeds_24",
    "absolute_cost_cap_exceeds_4_usd",
    "fallback_retry_or_service_tier_added",
    "v2_4_messages_candidate_corpus_scorer_or_thresholds_changed",
    "metadata_preflight_missing_or_stale",
)

_V24_MODEL = v24.ACTIVE_MAIN_MODEL
_V24_COST_CAP = v24.ABSOLUTE_COST_CAP_USD
_V24_BUILD_UNFROZEN = v24._build_unfrozen_protocol
_V24_EXPECTED_MANIFEST = v24.expected_freeze_manifest
_V24_VALIDATE_LEDGER = rating_v2.validate_ledger


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _v24_freeze_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_4.json"


def _adapter_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/final_wording_gpt52_v25.py"


@contextmanager
def _patch(target: Any, **changes: Any) -> Iterator[None]:
    previous = {name: getattr(target, name) for name in changes}
    try:
        for name, value in changes.items():
            setattr(target, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(target, name, value)


def _build_unfrozen(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    result = _V24_BUILD_UNFROZEN(repo_root, freeze_commit=freeze_commit)
    if v24._sha256_file(_v24_freeze_path(repo_root)) != V24_FREEZE_SHA256:
        raise ValueError("v24_freeze_fingerprint_changed")
    result["input_fingerprints"].update(
        {
            "base_freeze_v2_4_sha256": V24_FREEZE_SHA256,
            "gpt52_adapter_sha256": v24._sha256_file(_adapter_path(repo_root)),
        }
    )
    result.update(
        {
            "allowed_observed_models": sorted(ALLOWED_OBSERVED_MODELS),
            "campaign_path_version": "v2.5",
            "comparison_contract": {
                "base_protocol_version": "lot4c4_final_wording_bounded_candidate_v2_4",
                "base_model": _V24_MODEL,
                "unique_provider_visible_variable": "model_slug",
                "target_model": TARGET_MODEL,
            },
            "fresh_metadata_requirements": {
                "reasoning_effort": "high",
                "minimum_context_length": EXPECTED_CONTEXT_LENGTH,
                "minimum_max_completion_tokens": EXPECTED_MAX_COMPLETION_TOKENS,
                "prompt_price_usd_per_token": PRICING_USD_PER_TOKEN["prompt"],
                "completion_price_usd_per_token": PRICING_USD_PER_TOKEN["completion"],
            },
            "v2_5_mutation_matrix": list(V25_MUTATION_MATRIX),
        }
    )
    return result


def _expected_manifest(protocol: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    result = _V24_EXPECTED_MANIFEST(protocol, repo_root)
    result.update(
        {
            "schema_version": "stimmung_final_wording_freeze_v2_5",
            "status": "gpt52_replication_frozen_human_rating_required_after_provider",
            "supersedes": {
                "protocol_version": "lot4c4_final_wording_bounded_candidate_v2_4",
                "relationship": "cross_model_replication_source",
                "model": _V24_MODEL,
                "campaign_reused": False,
            },
            "unique_variable": copy.deepcopy(protocol["comparison_contract"]),
            "allowed_observed_models": copy.deepcopy(
                protocol["allowed_observed_models"]
            ),
            "fresh_metadata_requirements": copy.deepcopy(
                protocol["fresh_metadata_requirements"]
            ),
            "v2_5_mutation_matrix": list(V25_MUTATION_MATRIX),
        }
    )
    return result


def _normalize_v25_ledger(
    ledger: Mapping[str, Any], *, require_complete: bool = False
) -> dict[str, Any]:
    records = ledger.get("records")
    if (
        ledger.get("model") != TARGET_MODEL
        or ledger.get("absolute_cost_cap_usd") != ABSOLUTE_COST_CAP_USD
        or ledger.get("planned_call_count") != EXPECTED_CALLS
        or ledger.get("absolute_call_cap") != EXPECTED_CALLS
        or not isinstance(records, list)
        or len(records) != EXPECTED_CALLS
    ):
        raise ValueError("v25_call_ledger_provenance_invalid")
    for record in records:
        if record.get("requested_model") != TARGET_MODEL:
            raise ValueError("v25_call_ledger_requested_model_invalid")
        if record.get("status") == "valid" and record.get("observed_model") not in ALLOWED_OBSERVED_MODELS:
            raise ValueError("v25_call_ledger_observed_model_invalid")
    observed = round(sum(float(record.get("cost_usd") or 0.0) for record in records), 8)
    accounted = round(sum(float(record.get("accounted_cost_usd") or 0.0) for record in records), 8)
    if (observed, accounted) != (
        ledger.get("observed_cost_usd"),
        ledger.get("accounted_cost_usd"),
    ):
        raise ValueError("v25_call_ledger_cost_invalid")
    if accounted > ABSOLUTE_COST_CAP_USD and ledger.get(
        "terminal_reason_code"
    ) != "absolute_cost_cap_exceeded":
        raise ValueError("v25_call_ledger_cost_cap_invalid")
    normalized = copy.deepcopy(dict(ledger))
    normalized["model"] = _V24_MODEL
    normalized["absolute_cost_cap_usd"] = _V24_COST_CAP
    for record in normalized["records"]:
        for key in ("calculated_ceiling_cost_usd", "accounted_cost_usd"):
            record[key] = round(float(record[key]) / 2, 8)
        if record["cost_usd"] is not None:
            record["cost_usd"] = round(float(record["cost_usd"]) / 2, 8)
        record["requested_model"] = _V24_MODEL
    normalized["observed_cost_usd"] = round(
        sum(float(item.get("cost_usd") or 0.0) for item in normalized["records"]), 8
    )
    normalized["accounted_cost_usd"] = round(
        sum(float(item["accounted_cost_usd"]) for item in normalized["records"]), 8
    )
    return _V24_VALIDATE_LEDGER(normalized, require_complete=require_complete)


def expected_live_campaign_paths(protocol: Mapping[str, Any]) -> tuple[Path, Path]:
    freeze_commit = str(protocol.get("freeze_commit") or "")
    if len(freeze_commit) != 40:
        raise ValueError("freeze_commit_invalid")
    stem = f"lot4c4-final-wording-v2.5-{freeze_commit[:12]}"
    return Path(f"/tmp/{stem}-private"), Path(f"/tmp/{stem}-review")


@contextmanager
def _campaign_profile() -> Iterator[None]:
    with _patch(
        v24,
        PROTOCOL_VERSION=PROTOCOL_VERSION,
        ARTIFACT_VERSION=ARTIFACT_VERSION,
        SUPERSEDED_V23_PROTOCOL_VERSION="lot4c4_final_wording_bounded_candidate_v2_4",
        DEFAULT_FREEZE_MANIFEST=FREEZE_MANIFEST,
        ACTIVE_MAIN_MODEL=TARGET_MODEL,
        ACTIVE_MAX_TOKENS=MAX_TOKENS,
        ACTIVE_REASONING=dict(REASONING),
        ACTIVE_TIMEOUT_S=TIMEOUT_S,
        REQUIRED_ENDPOINT_CAPABILITIES=copy.deepcopy(REQUIRED_ENDPOINT_CAPABILITIES),
        ABSOLUTE_COST_CAP_USD=ABSOLUTE_COST_CAP_USD,
        PRICING_OBSERVED_AT=PRICING_OBSERVED_AT,
        PRICING_USD_PER_TOKEN=copy.deepcopy(PRICING_USD_PER_TOKEN),
        BASELINE_HEAD=BASELINE_HEAD,
        _build_unfrozen_protocol=_build_unfrozen,
        expected_freeze_manifest=_expected_manifest,
    ), _patch(
        execution_v2,
        _ALLOWED_OBSERVED_MODELS=set(ALLOWED_OBSERVED_MODELS),
        expected_live_campaign_paths=expected_live_campaign_paths,
    ), _patch(rating_v2, validate_ledger=_normalize_v25_ledger):
        yield


def build_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    with _campaign_profile():
        return v24.build_protocol(repo_root, freeze_commit=freeze_commit)


def build_request_schedule(repo_root: Path, protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    with _campaign_profile():
        return v24.build_request_schedule(repo_root, protocol)


def classify_provider_result(response: Mapping[str, Any]) -> dict[str, Any]:
    with _campaign_profile():
        return execution_v2._classify_provider_result(response)


def run_campaign(**kwargs: Any) -> dict[str, Any]:
    with _campaign_profile():
        return execution_v2.run_campaign(**kwargs)


def validate_model_metadata(
    *,
    capability_summary: Mapping[str, Any],
    model_metadata: Mapping[str, Any] | None,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    summary = {
        "model": TARGET_MODEL,
        "metadata_http_status": capability_summary.get("metadata_http_status"),
        "endpoint_count": int(capability_summary.get("endpoint_count") or 0),
        "compatible_endpoint_count": int(capability_summary.get("compatible_endpoint_count") or 0),
        "required_capabilities": sorted(REQUIRED_ENDPOINT_CAPABILITIES),
        "requested_reasoning_effort": "high",
        "reasoning_effort_high_supported": False,
        "context_length": None,
        "max_completion_tokens": None,
        "prompt_price_usd_per_token": None,
        "completion_price_usd_per_token": None,
        "budget_with_safety_margin_usd": None,
        "absolute_cost_cap_usd": ABSOLUTE_COST_CAP_USD,
    }
    if capability_summary.get("status") != "compatible":
        return {**summary, "status": capability_summary.get("status"), "reason_code": capability_summary.get("reason_code")}
    if not isinstance(model_metadata, Mapping) or model_metadata.get("id") != TARGET_MODEL:
        return {**summary, "status": "model_metadata_mismatch", "reason_code": "model_metadata_mismatch"}
    reasoning = model_metadata.get("reasoning")
    efforts = reasoning.get("supported_efforts") if isinstance(reasoning, Mapping) else ()
    high_supported = efforts is None or isinstance(efforts, list) and "high" in efforts
    top_provider = model_metadata.get("top_provider")
    pricing = model_metadata.get("pricing")
    try:
        context = int(model_metadata.get("context_length"))
        output = int(top_provider.get("max_completion_tokens"))
        prompt_price = float(pricing.get("prompt"))
        completion_price = float(pricing.get("completion"))
    except (AttributeError, TypeError, ValueError):
        return {**summary, "status": "model_metadata_mismatch", "reason_code": "model_metadata_fields_invalid"}
    budget = round(
        (
            int(protocol["prompt_token_estimate_sum"]) * prompt_price
            + int(protocol["completion_token_ceiling"]) * completion_price
        )
        * float(protocol["cost_safety_margin"]),
        8,
    )
    observed = {
        **summary,
        "reasoning_effort_high_supported": high_supported,
        "context_length": context,
        "max_completion_tokens": output,
        "prompt_price_usd_per_token": prompt_price,
        "completion_price_usd_per_token": completion_price,
        "budget_with_safety_margin_usd": budget,
    }
    if not high_supported:
        return {**observed, "status": "no_compatible_endpoint", "reason_code": "reasoning_effort_high_not_supported"}
    frozen = protocol["fresh_metadata_requirements"]
    if (
        context < frozen["minimum_context_length"]
        or output < frozen["minimum_max_completion_tokens"]
        or prompt_price != frozen["prompt_price_usd_per_token"]
        or completion_price != frozen["completion_price_usd_per_token"]
        or budget > protocol["absolute_cost_cap_usd"]
    ):
        return {**observed, "status": "metadata_contract_mismatch", "reason_code": "fresh_model_metadata_differs_from_freeze"}
    return {**observed, "status": "compatible", "reason_code": "compatible_endpoint_and_model_metadata_available"}


class GPT52OpenRouterClient(OpenRouterClient):
    def __init__(self, *args: Any, protocol: Mapping[str, Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._protocol = copy.deepcopy(dict(protocol))

    def preflight_model_capabilities(
        self, model: str, required_capabilities: dict[str, tuple[str, ...]]
    ) -> dict[str, Any]:
        if model != TARGET_MODEL or required_capabilities != REQUIRED_ENDPOINT_CAPABILITIES:
            raise ValueError("v25_preflight_contract_invalid")
        capabilities = super().preflight_model_capabilities(model, required_capabilities)
        metadata_status = None
        metadata = None
        if capabilities.get("status") == "compatible":
            try:
                response = openrouter_transport.requests.get(
                    f"{self.config.base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=20,
                )
                metadata_status = int(response.status_code)
                payload = response.json() if metadata_status == 200 else None
                data = payload.get("data") if isinstance(payload, Mapping) else None
                if isinstance(data, list):
                    metadata = next(
                        (item for item in data if isinstance(item, Mapping) and item.get("id") == TARGET_MODEL),
                        None,
                    )
            except Exception:
                pass
        result = validate_model_metadata(
            capability_summary=capabilities,
            model_metadata=metadata,
            protocol=self._protocol,
        )
        return {**result, "model_metadata_http_status": metadata_status}


def dry_run(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    protocol = build_protocol(repo_root, freeze_commit=freeze_commit)
    with _campaign_profile():
        summary = v24.validate_protocol(protocol, repo_root)
    return {
        **summary,
        "status": "ready_offline",
        "decision": "provider_campaign_required",
        "model": TARGET_MODEL,
        "protocol_sha256": v24.protocol_sha256(protocol),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lot 4C.4 v2.5 GPT-5.2 replication")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--review-export-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute_live:
        raise SystemExit("choose exactly one of --dry-run or --execute-live")
    if args.resume and not args.execute_live:
        raise SystemExit("--resume requires --execute-live")
    protocol = build_protocol(args.repo_root, freeze_commit=args.freeze_commit)
    if args.dry_run:
        print(_compact_json(dry_run(args.repo_root, freeze_commit=args.freeze_commit)))
        return 0
    if args.output_dir is None or args.review_export_dir is None:
        raise SystemExit("--output-dir and --review-export-dir are required")
    execution_v2.verify_live_preflight(args.repo_root, freeze_commit=args.freeze_commit)
    if (args.output_dir.resolve(), args.review_export_dir.resolve()) != expected_live_campaign_paths(protocol):
        raise SystemExit("live paths must match the frozen v2.5 campaign identity")
    base = OpenRouterClient.from_env(title="FridaDev/Lot4C4-GPT52-v2.5", fetch_pricing=False)
    client = GPT52OpenRouterClient(
        base.config,
        pricing_by_model={TARGET_MODEL: dict(PRICING_USD_PER_TOKEN)},
        protocol=protocol,
    )
    result = run_campaign(
        repo_root=args.repo_root,
        protocol=protocol,
        client=client,
        output_dir=args.output_dir,
        review_export_dir=args.review_export_dir,
        execution_authorized=True,
        evidence_source="main_model_provider",
        progress=lambda current, total, _record: print(
            _compact_json({"status": "running", "completed": current, "total": total}),
            flush=True,
        ) if current == 1 or current % 6 == 0 or current == total else None,
        capability_progress=lambda summary: print(
            _compact_json({"status": "capability_preflight", **dict(summary)}),
            flush=True,
        ),
        resume=args.resume,
    )
    print(_compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
