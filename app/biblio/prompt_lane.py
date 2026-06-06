"""Prompt lane builder for extracted native Biblio passages.

Lot 5 formats already extracted passages into a dedicated prompt block.  It
does not resolve documents, call Catalogue, touch chat state, write data, or
mix Biblio with active conversation documents.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Sequence

from .passage_extractor import BiblioPassageResult, STATUS_EXTRACTED


LANE_HEADER = "[PASSAGES DE BIBLIOTHEQUE CONSULTES]"
LANE_FOOTER = "[/PASSAGES DE BIBLIOTHEQUE CONSULTES]"

DEFAULT_MAX_PASSAGES = 3
DEFAULT_MAX_TOTAL_CHARS = 8_000
MIN_MAX_PASSAGES = 1
MAX_MAX_PASSAGES = 10
MIN_MAX_TOTAL_CHARS = 1
MAX_MAX_TOTAL_CHARS = 50_000

REASON_INJECTED = "biblio_prompt_passage_injected"
REASON_NON_EXTRACTED = "biblio_prompt_non_extracted_status"
REASON_EMPTY_PASSAGE = "biblio_prompt_empty_passage"
REASON_MAX_PASSAGES_REACHED = "biblio_prompt_max_passages_reached"
REASON_MAX_TOTAL_CHARS_REACHED = "biblio_prompt_max_total_chars_reached"
REASON_INVALID_LIMIT = "biblio_prompt_invalid_limit"

TRUTH_EXACT_PASSAGE = "exact_passage"
TRUTH_PLAUSIBLE_CANDIDATE = "plausible_candidate"
TRUTH_CONTEXTUAL_APPROXIMATION = "contextual_approximation"
TRUTH_CLARIFICATION_REQUIRED = "clarification_required"


@dataclass(frozen=True)
class BiblioPromptPassageDecision:
    index: int
    status: str
    injected: bool
    reason_code: str
    source_reason_code: str = ""
    doc_id_short: str = ""
    passage_chars: int = 0
    passage_hash: str = ""
    lane_chars_if_injected: int = 0
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    excerpt_start: int | None = None
    excerpt_end: int | None = None
    text_length: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "injected": self.injected,
            "reason_code": self.reason_code,
            "source_reason_code": self.source_reason_code,
            "doc_id_short": self.doc_id_short,
            "passage_chars": self.passage_chars,
            "passage_hash": self.passage_hash,
            "lane_chars_if_injected": self.lane_chars_if_injected,
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "text_length": self.text_length,
        }


@dataclass(frozen=True)
class BiblioPromptLane:
    message: dict[str, Any] | None = field(default=None, repr=False, compare=False)
    decisions: tuple[BiblioPromptPassageDecision, ...] = field(default_factory=tuple)
    max_passages: int = DEFAULT_MAX_PASSAGES
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS
    chars: int = 0
    product_truth: str = ""

    @property
    def passage_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.injected)

    @property
    def skipped_count(self) -> int:
        return sum(1 for decision in self.decisions if not decision.injected)

    def to_observability(self) -> dict[str, Any]:
        injected = [decision for decision in self.decisions if decision.injected]
        return {
            "present": self.message is not None,
            "passage_count": len(injected),
            "skipped_count": self.skipped_count,
            "chars": self.chars,
            "max_passages": self.max_passages,
            "max_total_chars": self.max_total_chars,
            "product_truth": self.product_truth,
            "hashes": [decision.passage_hash for decision in injected],
            "doc_id_shorts": [decision.doc_id_short for decision in injected],
            "positions": [
                {
                    "page_no": decision.page_no,
                    "para_no": decision.para_no,
                    "paragraph_id": decision.paragraph_id,
                    "excerpt_start": decision.excerpt_start,
                    "excerpt_end": decision.excerpt_end,
                    "text_length": decision.text_length,
                }
                for decision in injected
            ],
            "decisions": [decision.to_observability() for decision in self.decisions],
        }


def build_biblio_prompt_lane(
    passage_results: Sequence[BiblioPassageResult] | None,
    *,
    max_passages: int = DEFAULT_MAX_PASSAGES,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
    product_truth: str = "",
) -> BiblioPromptLane:
    max_passages = _bounded_int(
        max_passages,
        minimum=MIN_MAX_PASSAGES,
        maximum=MAX_MAX_PASSAGES,
    )
    max_total_chars = _bounded_int(
        max_total_chars,
        minimum=MIN_MAX_TOTAL_CHARS,
        maximum=MAX_MAX_TOTAL_CHARS,
    )

    results = tuple(result for result in (passage_results or ()) if isinstance(result, BiblioPassageResult))
    truth = _safe_product_truth(product_truth)
    if not results:
        return BiblioPromptLane(
            max_passages=max_passages,
            max_total_chars=max_total_chars,
            product_truth=truth,
        )

    body_lines = _contract_lines(truth)
    decisions: list[BiblioPromptPassageDecision] = []
    injected_count = 0

    for index, result in enumerate(results, start=1):
        base_decision = _decision_from_result(result, index=index)
        if result.status != STATUS_EXTRACTED:
            decisions.append(_replace_decision(base_decision, injected=False, reason_code=REASON_NON_EXTRACTED))
            continue
        if not result.passage:
            decisions.append(_replace_decision(base_decision, injected=False, reason_code=REASON_EMPTY_PASSAGE))
            continue
        if injected_count >= max_passages:
            decisions.append(
                _replace_decision(base_decision, injected=False, reason_code=REASON_MAX_PASSAGES_REACHED)
            )
            continue

        candidate_lines = [
            *body_lines,
            *_passage_lines(result, passage_no=injected_count + 1, product_truth=truth),
        ]
        candidate_content = _lane_content(candidate_lines)
        candidate_chars = len(candidate_content)
        if candidate_chars > max_total_chars:
            decisions.append(
                _replace_decision(
                    base_decision,
                    injected=False,
                    reason_code=REASON_MAX_TOTAL_CHARS_REACHED,
                    lane_chars_if_injected=candidate_chars,
                )
            )
            continue

        body_lines = candidate_lines
        injected_count += 1
        decisions.append(
            _replace_decision(
                base_decision,
                injected=True,
                reason_code=REASON_INJECTED,
                lane_chars_if_injected=candidate_chars,
            )
        )

    if injected_count == 0:
        return BiblioPromptLane(
            decisions=tuple(decisions),
            max_passages=max_passages,
            max_total_chars=max_total_chars,
            product_truth=truth,
        )

    content = _lane_content(body_lines)
    return BiblioPromptLane(
        message={"role": "system", "content": content},
        decisions=tuple(decisions),
        max_passages=max_passages,
        max_total_chars=max_total_chars,
        chars=len(content),
        product_truth=truth,
    )


def _contract_lines(product_truth: str) -> list[str]:
    lines = [
        "Contrat d'interpretation:",
        "- Les passages ci-dessous proviennent d'une bibliotheque persistante consultee a la demande.",
        "- Ils ne prouvent pas que tout l'ouvrage ou tout le corpus a ete lu.",
        "- Respecte le statut de resolution, les limites et les ambiguites.",
        "- Ne confonds pas ces passages avec les documents actifs, la memoire, le web, l'identite ou le resume.",
    ]
    truth_label = _product_truth_label(product_truth)
    if truth_label:
        lines.append(f"- Niveau de resolution: {truth_label}.")
    if product_truth == TRUTH_PLAUSIBLE_CANDIDATE:
        lines.append("- Les passages fournis sont des candidats plausibles; ne les presente pas comme un passage exact.")
    elif product_truth == TRUTH_CONTEXTUAL_APPROXIMATION:
        lines.append("- Le passage fourni est une approximation contextuelle issue de recherche+contexte, pas une localisation canonique certaine.")
    elif product_truth == TRUTH_EXACT_PASSAGE:
        lines.append("- Le passage fourni correspond a une extraction exacte telle que resolue par la bibliotheque.")
    return lines


def _passage_lines(result: BiblioPassageResult, *, passage_no: int, product_truth: str) -> list[str]:
    return [
        _passage_heading(passage_no, product_truth=product_truth),
        f"Source: {_source_line(result)}",
        "Texte:",
        _neutralize_lane_tags(result.passage),
    ]


def _source_line(result: BiblioPassageResult) -> str:
    fields = []
    doc_id_short = _doc_id_short(result)
    fields.append(f"catalogue_doc={doc_id_short or 'unknown'}")
    if result.page_no is not None:
        fields.append(f"page={result.page_no}")
    if result.para_no is not None:
        fields.append(f"paragraphe={result.para_no}")
    if result.paragraph_id is not None:
        fields.append(f"paragraph_id={result.paragraph_id}")
    return ", ".join(fields)


def _lane_content(body_lines: Sequence[str]) -> str:
    return "\n".join([LANE_HEADER, *body_lines, LANE_FOOTER])


def _decision_from_result(result: BiblioPassageResult, *, index: int) -> BiblioPromptPassageDecision:
    passage_hash = _observable_passage_hash(result)
    passage_chars = result.passage_chars or (len(result.passage) if result.passage else 0)
    return BiblioPromptPassageDecision(
        index=index,
        status=result.status,
        injected=False,
        reason_code="",
        source_reason_code=result.reason_code,
        doc_id_short=_doc_id_short(result),
        passage_chars=passage_chars,
        passage_hash=passage_hash,
        page_no=result.page_no,
        para_no=result.para_no,
        paragraph_id=result.paragraph_id,
        excerpt_start=result.excerpt_start,
        excerpt_end=result.excerpt_end,
        text_length=result.text_length,
    )


def _replace_decision(
    decision: BiblioPromptPassageDecision,
    *,
    injected: bool,
    reason_code: str,
    lane_chars_if_injected: int | None = None,
) -> BiblioPromptPassageDecision:
    return BiblioPromptPassageDecision(
        index=decision.index,
        status=decision.status,
        injected=injected,
        reason_code=reason_code,
        source_reason_code=decision.source_reason_code,
        doc_id_short=decision.doc_id_short,
        passage_chars=decision.passage_chars,
        passage_hash=decision.passage_hash,
        lane_chars_if_injected=decision.lane_chars_if_injected
        if lane_chars_if_injected is None
        else lane_chars_if_injected,
        page_no=decision.page_no,
        para_no=decision.para_no,
        paragraph_id=decision.paragraph_id,
        excerpt_start=decision.excerpt_start,
        excerpt_end=decision.excerpt_end,
        text_length=decision.text_length,
    )


def _safe_product_truth(value: str) -> str:
    token = str(value or "").strip()
    if token in {
        TRUTH_EXACT_PASSAGE,
        TRUTH_PLAUSIBLE_CANDIDATE,
        TRUTH_CONTEXTUAL_APPROXIMATION,
        TRUTH_CLARIFICATION_REQUIRED,
    }:
        return token
    return ""


def _product_truth_label(value: str) -> str:
    return {
        TRUTH_EXACT_PASSAGE: "passage exact",
        TRUTH_PLAUSIBLE_CANDIDATE: "candidat plausible",
        TRUTH_CONTEXTUAL_APPROXIMATION: "approximation contextuelle",
        TRUTH_CLARIFICATION_REQUIRED: "clarification necessaire",
    }.get(value, "")


def _passage_heading(passage_no: int, *, product_truth: str) -> str:
    if product_truth == TRUTH_EXACT_PASSAGE:
        return f"Passage exact {passage_no}"
    if product_truth == TRUTH_PLAUSIBLE_CANDIDATE:
        return f"Passage candidat {passage_no}"
    if product_truth == TRUTH_CONTEXTUAL_APPROXIMATION:
        return f"Approximation contextuelle {passage_no}"
    return f"Passage {passage_no}"


def _doc_id_short(result: BiblioPassageResult) -> str:
    text = str(result.doc_id_short or "").strip()
    if text:
        return text[:8]
    resolution = result.resolution
    if resolution and resolution.document:
        return str(resolution.document.doc_id_short or "").strip()[:8]
    return ""


def _bounded_int(value: Any, *, minimum: int, maximum: int) -> int:
    if type(value) is int:
        integer = value
    elif isinstance(value, str) and value.isdecimal():
        integer = int(value)
    else:
        raise ValueError(REASON_INVALID_LIMIT)
    if integer < minimum or integer > maximum:
        raise ValueError(REASON_INVALID_LIMIT)
    return integer


def _neutralize_lane_tags(value: str) -> str:
    return str(value or "").replace(
        LANE_FOOTER,
        "[BALISE BIBLIO NEUTRALISEE: /PASSAGES DE BIBLIOTHEQUE CONSULTES]",
    ).replace(
        LANE_HEADER,
        "[BALISE BIBLIO NEUTRALISEE: PASSAGES DE BIBLIOTHEQUE CONSULTES]",
    )


def _observable_passage_hash(result: BiblioPassageResult) -> str:
    if result.passage:
        return _short_hash(result.passage)
    return _strict_short_hash(result.passage_hash)


def _strict_short_hash(value: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 12:
        return ""
    if any(char not in "0123456789abcdef" for char in text):
        return ""
    return text


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
