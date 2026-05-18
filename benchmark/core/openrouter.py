from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any

import requests


@dataclass(frozen=True)
class OpenRouterConfig:
    base_url: str
    api_key: str
    referer: str = ""
    title: str = "FridaDev/Benchmark"


class OpenRouterClient:
    def __init__(self, config: OpenRouterConfig, *, pricing_by_model: dict[str, dict[str, float]] | None = None) -> None:
        self.config = config
        self.pricing_by_model = pricing_by_model or {}

    @classmethod
    def from_env(cls, *, base_url: str | None = None, title: str = "FridaDev/Benchmark") -> "OpenRouterClient":
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for a live benchmark")
        resolved_base = (base_url or os.environ.get("OPENROUTER_BASE") or "https://openrouter.ai/api/v1").rstrip("/")
        referer = os.environ.get("OPENROUTER_REFERER", "").strip()
        config = OpenRouterConfig(
            base_url=resolved_base,
            api_key=api_key,
            referer=referer,
            title=title,
        )
        return cls(config, pricing_by_model=fetch_model_pricing(config))

    def chat_completion(self, payload: dict[str, Any], *, caller: str, timeout_s: int) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                headers=self._headers(caller=caller),
                timeout=timeout_s,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            status_code = response.status_code
            data = response.json() if response.content else {}
            if response.status_code >= 400:
                return {
                    "ok": False,
                    "status_code": status_code,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "error": _compact_error(data) or response.text[:500],
                    "raw_text": None,
                    "usage": _usage(data),
                    "cost_estimate_usd": None,
                    "cost_estimate_source": "provider_error",
                }
            raw_text = _extract_text(data)
            usage = _usage(data)
            cost, source = self._estimate_cost(str(payload.get("model") or ""), usage)
            return {
                "ok": True,
                "status_code": status_code,
                "elapsed_ms": round(elapsed_ms, 3),
                "error": None,
                "raw_text": raw_text,
                "usage": usage,
                "cost_estimate_usd": cost,
                "cost_estimate_source": source,
            }
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "ok": False,
                "status_code": None,
                "elapsed_ms": round(elapsed_ms, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                "raw_text": None,
                "usage": {},
                "cost_estimate_usd": None,
                "cost_estimate_source": "exception",
            }

    def _headers(self, *, caller: str) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "X-Frida-Caller": caller,
        }
        if self.config.referer:
            headers["HTTP-Referer"] = self.config.referer
        if self.config.title:
            headers["X-OpenRouter-Title"] = self.config.title
            headers["X-Title"] = self.config.title
        return headers

    def _estimate_cost(self, model: str, usage: dict[str, Any]) -> tuple[float | None, str]:
        direct = usage.get("cost")
        if isinstance(direct, (int, float)):
            return round(float(direct), 8), "provider_usage_cost"
        pricing = self.pricing_by_model.get(model) or {}
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")
        prompt_tokens = _int_or_zero(usage.get("prompt_tokens"))
        completion_tokens = _int_or_zero(usage.get("completion_tokens"))
        if prompt_price is None or completion_price is None or (prompt_tokens + completion_tokens) <= 0:
            return None, "unavailable"
        cost = (prompt_tokens * prompt_price) + (completion_tokens * completion_price)
        return round(cost, 8), "openrouter_models_pricing"


def fetch_model_pricing(config: OpenRouterConfig) -> dict[str, dict[str, float]]:
    try:
        response = requests.get(
            f"{config.base_url}/models",
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {}

    pricing_by_model: dict[str, dict[str, float]] = {}
    for item in data.get("data", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        pricing = item.get("pricing") or {}
        if not model_id or not isinstance(pricing, dict):
            continue
        prompt = _float_or_none(pricing.get("prompt"))
        completion = _float_or_none(pricing.get("completion"))
        if prompt is not None and completion is not None:
            pricing_by_model[model_id] = {"prompt": prompt, "completion": completion}
    return pricing_by_model


def _extract_text(data: dict[str, Any]) -> str:
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception:
        return ""


def _usage(data: dict[str, Any]) -> dict[str, Any]:
    usage = data.get("usage") if isinstance(data, dict) else None
    return dict(usage) if isinstance(usage, dict) else {}


def _compact_error(data: Any) -> str:
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("code") or "").strip()
            return message[:500]
        if isinstance(error, str):
            return error[:500]
    return ""


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
