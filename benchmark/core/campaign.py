from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from benchmark.core.openrouter import OpenRouterClient


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    suite: str
    repo_root: Path
    output_dir: Path
    models: list[str]
    dry_run: bool = False
    timeout_s: int = 90


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_model_campaign(
    *,
    config: CampaignConfig,
    prompt_path: Path,
    fixture_path: Path,
    generation_params: dict[str, Any],
    cases: list[dict[str, Any]],
    build_payload: Callable[[dict[str, Any], str, str], dict[str, Any]],
    score_response: Callable[[dict[str, Any], str | None, str | None], dict[str, Any]],
    summarize_model: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
    client: OpenRouterClient | None,
) -> dict[str, Any]:
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    fixture_hash = sha256_file(fixture_path)
    prompt_hash = sha256_text(prompt_text)
    model_results: list[dict[str, Any]] = []

    for model in config.models:
        calls: list[dict[str, Any]] = []
        for case in cases:
            payload = build_payload(case, model, prompt_text)
            request_signature = {
                "messages_sha256": sha256_text(json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)),
                "generation_params": {
                    "temperature": payload.get("temperature"),
                    "top_p": payload.get("top_p"),
                    "max_tokens": payload.get("max_tokens"),
                },
            }

            if config.dry_run:
                provider = {
                    "ok": True,
                    "status_code": None,
                    "elapsed_ms": 0.0,
                    "error": None,
                    "raw_text": None,
                    "usage": {},
                    "cost_estimate_usd": None,
                    "cost_estimate_source": "dry_run",
                }
                score = score_response(case, None, None)
            else:
                if client is None:
                    raise RuntimeError("client is required outside dry-run mode")
                result = client.chat_completion(payload, caller=config.suite, timeout_s=config.timeout_s)
                provider = result
                score = score_response(case, result.get("raw_text"), result.get("error"))

            calls.append(
                {
                    "case_id": case["id"],
                    "case_tags": list(case.get("tags") or []),
                    "expected_keep_ids": sorted(case.get("expected_keep_ids") or []),
                    "provider": provider,
                    "request_signature": request_signature,
                    "score": score,
                }
            )

        summary = summarize_model(model, calls)
        model_results.append({"model": model, "summary": summary, "calls": calls})

    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": config.suite,
        "dry_run": config.dry_run,
        "models": config.models,
        "generation_params": generation_params,
        "prompt_path": str(prompt_path.relative_to(config.repo_root)),
        "prompt_sha256": prompt_hash,
        "fixture_path": str(fixture_path.relative_to(config.repo_root)),
        "fixture_sha256": fixture_hash,
        "case_count": len(cases),
        "secrets_written": False,
        "results": model_results,
    }


def ensure_unique_models(models: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for model in models:
        value = str(model or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
