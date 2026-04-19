from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.web_read_state import (
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
)


HARD_GUARD_EXPLICIT_URL_NOT_READ = "explicit_url_not_read"
HARD_GUARD_EXTERNAL_VERIFICATION_MISSING = "external_verification_missing"
HARD_GUARD_EFFECT_ANSWER_FORBIDDEN = "answer_forbidden"

_NOT_READ_EXPLICIT_URL_STATES = {
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _stable_unique(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _web_source_materially_used(source: Any) -> bool:
    payload = _mapping(source)
    if not bool(payload.get("used_in_prompt")):
        return False
    if _text(payload.get("used_content_kind")) in {"", "none"}:
        return False
    return bool(_text(payload.get("content_used")))


def _web_evidence_available(web_input: Mapping[str, Any]) -> bool:
    if _text(web_input.get("status")) != "ok":
        return False
    return any(_web_source_materially_used(source) for source in _sequence(web_input.get("sources")))


@dataclass(frozen=True)
class HardGuardDecision:
    applied_hard_guards: tuple[str, ...] = ()
    effect: str | None = None

    @property
    def answer_forbidden(self) -> bool:
        return self.effect == HARD_GUARD_EFFECT_ANSWER_FORBIDDEN

    @property
    def allowed_postures(self) -> tuple[str, ...]:
        if self.answer_forbidden:
            return ("clarify", "suspend")
        return ("answer", "clarify", "suspend")

    def prompt_payload(self) -> dict[str, Any]:
        if not self.applied_hard_guards:
            return {}
        return {
            "applied_hard_guards": list(self.applied_hard_guards),
            "hard_guard_effect": str(self.effect or ""),
            "allowed_postures": list(self.allowed_postures),
        }


def evaluate_hard_guards(
    *,
    primary_verdict: Mapping[str, Any] | None,
    canonical_inputs: Mapping[str, Any] | None,
) -> HardGuardDecision:
    primary_payload = _mapping(primary_verdict)
    canonical_payload = _mapping(canonical_inputs)
    web_input = _mapping(canonical_payload.get("web_input"))

    applied_hard_guards: list[str] = []
    read_state = _text(web_input.get("read_state"))

    if bool(web_input.get("explicit_url_detected")) and read_state in _NOT_READ_EXPLICIT_URL_STATES:
        applied_hard_guards.append(HARD_GUARD_EXPLICIT_URL_NOT_READ)

    if (
        _text(primary_payload.get("proof_regime")) == "verification_externe_requise"
        and not _web_evidence_available(web_input)
    ):
        applied_hard_guards.append(HARD_GUARD_EXTERNAL_VERIFICATION_MISSING)

    stable_guards = _stable_unique(applied_hard_guards)
    return HardGuardDecision(
        applied_hard_guards=stable_guards,
        effect=HARD_GUARD_EFFECT_ANSWER_FORBIDDEN if stable_guards else None,
    )
