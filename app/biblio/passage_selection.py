"""Content-free selection of validated Biblio passage contexts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .passage_candidate_search import BiblioPassageCandidate


STATUS_SELECTED = "selected"
STATUS_AMBIGUOUS = "ambiguous"

REASON_SINGLE_PLAUSIBLE_CONTEXT = "single_plausible_context"
REASON_DOMINANT_CONTEXT = "dominant_context"
REASON_SELECTION_GAP_TOO_SMALL = "selection_gap_too_small"
REASON_SELECTION_EVIDENCE_INSUFFICIENT = "selection_evidence_insufficient"

MIN_DOMINANT_SCORE_GAP = 8.0
MIN_ACCEPTABLE_CONTEXT_CHARS = 80
MAX_COMFORTABLE_CONTEXT_CHARS = 6_000

_STRONG_EVIDENCE_CODES = {
    "exact_theme_variant",
    "folded_theme_variant",
    "multi_variant_hit",
    "work_document_match",
    "work_theme_proximity",
}


@dataclass(frozen=True)
class BiblioPassageSelectionInput:
    index: int
    candidate: BiblioPassageCandidate = field(repr=False, compare=False)
    context_chars: int = 0


@dataclass(frozen=True)
class BiblioPassageSelectionScore:
    index: int
    doc_id_short: str = ""
    score: float = 0.0
    candidate_score: float = 0.0
    context_chars: int = 0
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_observability(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "doc_id_short": self.doc_id_short,
            "score": round(float(self.score), 3),
            "candidate_score": round(float(self.candidate_score), 3),
            "context_chars": self.context_chars,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class BiblioPassageSelectionDecision:
    status: str
    reason_code: str
    selected_index: int | None = None
    scores: tuple[BiblioPassageSelectionScore, ...] = field(default_factory=tuple)
    top_score: float = 0.0
    runner_up_score: float = 0.0
    score_gap: float = 0.0
    ambiguous: bool = False

    @property
    def selected_count(self) -> int:
        return 1 if self.selected_index is not None else 0

    @property
    def selected_score(self) -> BiblioPassageSelectionScore | None:
        if self.selected_index is None:
            return None
        for score in self.scores:
            if score.index == self.selected_index:
                return score
        return None

    def score_for_index(self, index: int) -> BiblioPassageSelectionScore | None:
        for score in self.scores:
            if score.index == index:
                return score
        return None

    def to_observability(self) -> dict[str, Any]:
        selected = self.selected_score
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "selected_count": self.selected_count,
            "selected_index": self.selected_index,
            "ambiguous": self.ambiguous,
            "top_score": round(float(self.top_score), 3),
            "runner_up_score": round(float(self.runner_up_score), 3),
            "score_gap": round(float(self.score_gap), 3),
            "selected_reason_codes": list(selected.reason_codes) if selected else [],
            "scores": [score.to_observability() for score in self.scores],
        }


def select_biblio_passage(
    candidates: Sequence[BiblioPassageSelectionInput],
) -> BiblioPassageSelectionDecision:
    scores = tuple(sorted((_score_candidate(candidate) for candidate in candidates), key=_score_sort_key))
    if not scores:
        return BiblioPassageSelectionDecision(
            status=STATUS_AMBIGUOUS,
            reason_code=REASON_SELECTION_EVIDENCE_INSUFFICIENT,
            ambiguous=True,
        )

    top = scores[0]
    runner = scores[1] if len(scores) > 1 else None
    top_score = top.score
    runner_score = runner.score if runner else 0.0
    score_gap = top_score - runner_score if runner else top_score
    if runner is None:
        return BiblioPassageSelectionDecision(
            status=STATUS_SELECTED,
            reason_code=REASON_SINGLE_PLAUSIBLE_CONTEXT,
            selected_index=top.index,
            scores=scores,
            top_score=top_score,
            runner_up_score=0.0,
            score_gap=score_gap,
            ambiguous=False,
        )

    if score_gap >= MIN_DOMINANT_SCORE_GAP and _has_strong_evidence(top):
        return BiblioPassageSelectionDecision(
            status=STATUS_SELECTED,
            reason_code=REASON_DOMINANT_CONTEXT,
            selected_index=top.index,
            scores=scores,
            top_score=top_score,
            runner_up_score=runner_score,
            score_gap=score_gap,
            ambiguous=False,
        )

    reason = REASON_SELECTION_GAP_TOO_SMALL if score_gap < MIN_DOMINANT_SCORE_GAP else REASON_SELECTION_EVIDENCE_INSUFFICIENT
    return BiblioPassageSelectionDecision(
        status=STATUS_AMBIGUOUS,
        reason_code=reason,
        selected_index=None,
        scores=scores,
        top_score=top_score,
        runner_up_score=runner_score,
        score_gap=score_gap,
        ambiguous=True,
    )


def _score_candidate(candidate: BiblioPassageSelectionInput) -> BiblioPassageSelectionScore:
    source = candidate.candidate
    score = float(source.score)
    reasons = set(source.reason_codes)
    selection_reasons: set[str] = {"candidate_score"}

    if "work_document_match" in reasons:
        score += 8
        selection_reasons.add("work_document_match")
    if "work_theme_proximity" in reasons:
        score += 4
        selection_reasons.add("work_theme_proximity")
    if "exact_theme_variant" in reasons:
        score += 4
        selection_reasons.add("exact_theme_variant")
    elif "folded_theme_variant" in reasons:
        score += 2
        selection_reasons.add("folded_theme_variant")
    if "multi_variant_hit" in reasons:
        score += 2
        selection_reasons.add("multi_variant_hit")
    if source.catalogue_rank_score is not None and source.catalogue_rank_score > 0:
        score += min(float(source.catalogue_rank_score) * 3, 2)
        selection_reasons.add("catalogue_rank_signal")
    if source.first_result_index == 1:
        score += 1
        selection_reasons.add("first_result")

    if MIN_ACCEPTABLE_CONTEXT_CHARS <= candidate.context_chars <= MAX_COMFORTABLE_CONTEXT_CHARS:
        score += 2
        selection_reasons.add("acceptable_context_length")
    elif candidate.context_chars < MIN_ACCEPTABLE_CONTEXT_CHARS:
        score -= 4
        selection_reasons.add("short_context")
    else:
        score -= 2
        selection_reasons.add("large_context")

    return BiblioPassageSelectionScore(
        index=candidate.index,
        doc_id_short=source.doc_id_short,
        score=score,
        candidate_score=source.score,
        context_chars=candidate.context_chars,
        reason_codes=tuple(sorted(selection_reasons)),
    )


def _has_strong_evidence(score: BiblioPassageSelectionScore) -> bool:
    return bool(_STRONG_EVIDENCE_CODES.intersection(score.reason_codes))


def _score_sort_key(score: BiblioPassageSelectionScore) -> tuple[float, int]:
    return -score.score, score.index
