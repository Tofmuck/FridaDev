from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from typing import Any, Iterable, Mapping

from tools import adobe_docs_sources


DEFAULT_PASSAGE_CHARS = 1200
DEFAULT_PASSAGE_COUNT = 6
DEFAULT_PROMPT_BUDGET_CHARS = 5000

EVIDENCE_SUFFICIENT = 'sufficient'
EVIDENCE_PARTIAL = 'partial'
EVIDENCE_INSUFFICIENT = 'insufficient'

REASON_SPLIT_SECTION = 'split_section'
REASON_SPLIT_CHUNK = 'split_chunk'
REASON_NAVIGATION_EXCLUDED = 'navigation_excluded'
REASON_SCORE_LEXICAL_OVERLAP = 'score_lexical_overlap'
REASON_SCORE_HEADING_OVERLAP = 'score_heading_overlap'
REASON_SCORE_ALIAS_OVERLAP = 'score_alias_overlap'
REASON_SCORE_SOURCE_TYPE = 'score_source_type'
REASON_SOURCE_RELEASE_QUERY = 'source_release_query'
REASON_SOURCE_ISSUE_QUERY = 'source_issue_query'
REASON_SOURCE_USAGE_QUERY = 'source_usage_query'
REASON_SELECTION_LIMIT_APPLIED = 'selection_limit_applied'
REASON_BUDGET_LIMIT_APPLIED = 'budget_limit_applied'
REASON_NO_RELEVANT_PASSAGE = 'no_relevant_passage'

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)')
_WORD_RE = re.compile(r'[a-z0-9]{3,}')
_RELEASE_TERMS = {
    'changelog',
    'maj',
    'mise a jour',
    'new feature',
    'nouveaute',
    'nouveautes',
    'quoi de neuf',
    'release',
    'release note',
    'release notes',
    'update',
    'version',
    'versions',
    'whats new',
}
_ISSUE_TERMS = {
    'bug',
    'connu',
    'connue',
    'connues',
    'connus',
    'corrige',
    'corrigee',
    'corrigees',
    'corriges',
    'crash',
    'depannage',
    'erreur',
    'fixed',
    'issue',
    'known issue',
    'known issues',
    'plante',
    'probleme',
    'problemes',
    'troubleshoot',
}
_NAVIGATION_TERMS = {
    'all apps',
    'buy now',
    'choose your region',
    'cookie',
    'cookies',
    'creative cloud',
    'download',
    'language navigation',
    'legal notices',
    'privacy',
    'quick links',
    'search',
    'share this page',
    'sign in',
    'was this page helpful',
}
_STOPWORDS = {
    'avec',
    'dans',
    'des',
    'for',
    'les',
    'pour',
    'the',
    'une',
    'vous',
    'your',
}
_ADOBE_TERM_ALIASES = {
    'calque': {'layer', 'layers'},
    'calques': {'layer', 'layers'},
    'exporter': {'export'},
    'masque': {'mask', 'masks'},
    'masques': {'mask', 'masks'},
    'outil': {'tool', 'tools'},
    'outils': {'tool', 'tools'},
    'plume': {'pen', 'tool'},
    'selection': {'selections'},
    'selections': {'selection'},
    'trace': {'path', 'paths'},
    'traces': {'path', 'paths'},
}
_GENERIC_ALIAS_TOKENS = {'tool', 'tools'}


@dataclass(frozen=True, repr=False)
class AdobePassage:
    product: str
    source_type: str
    canonical_url: str
    url_sha256_12: str
    text: str
    heading: str = ''
    section_path: tuple[str, ...] = ()
    title: str = ''
    chars: int = 0
    score: int = 0
    reason_codes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "AdobePassage("
            f"product={self.product!r}, source_type={self.source_type!r}, "
            f"url_sha256_12={self.url_sha256_12!r}, chars={self.chars!r}, "
            f"score={self.score!r}, heading_chars={len(self.heading)!r}, "
            f"section_depth={len(self.section_path)!r}, reason_codes={self.reason_codes!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'product': self.product,
            'source_type': self.source_type,
            'url_sha256_12': self.url_sha256_12,
            'chars': self.chars,
            'score': self.score,
            'heading_chars': len(self.heading),
            'section_depth': len(self.section_path),
            'title_chars': len(self.title),
            'reason_codes': list(self.reason_codes),
        }


@dataclass(frozen=True, repr=False)
class AdobePassageSelection:
    evidence: str
    passages: tuple[AdobePassage, ...]
    candidate_count: int = 0
    selected_count: int = 0
    total_chars: int = 0
    reason_codes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "AdobePassageSelection("
            f"evidence={self.evidence!r}, candidate_count={self.candidate_count!r}, "
            f"selected_count={self.selected_count!r}, total_chars={self.total_chars!r}, "
            f"reason_codes={self.reason_codes!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'evidence': self.evidence,
            'candidate_count': self.candidate_count,
            'selected_count': self.selected_count,
            'total_chars': self.total_chars,
            'reason_codes': list(self.reason_codes),
            'passages': [passage.as_content_free_dict() for passage in self.passages],
        }


def split_adobe_markdown(
    markdown: str,
    source_metadata: Any,
    *,
    max_passage_chars: int = DEFAULT_PASSAGE_CHARS,
) -> tuple[AdobePassage, ...]:
    metadata = _metadata_from_source(source_metadata)
    limit = _safe_positive_int(max_passage_chars, DEFAULT_PASSAGE_CHARS)
    candidates: list[AdobePassage] = []
    section_heading = ''
    section_path: list[str] = []
    section_lines: list[str] = []

    def flush() -> None:
        if not section_lines:
            return
        cleaned_lines, noise_removed = _clean_section_lines(section_lines)
        body_text = _normalize_passage_text('\n'.join(cleaned_lines))
        if not _looks_like_useful_passage(body_text):
            return
        heading_prefix = f'{section_heading}\n\n' if section_heading else ''
        body_limit = limit
        if heading_prefix and len(heading_prefix) < limit:
            body_limit = max(1, limit - len(heading_prefix))
        body_chunks = _chunk_text(body_text, body_limit)
        for chunk in body_chunks:
            text = _with_heading_prefix(chunk, heading_prefix, limit)
            reason_codes = [REASON_SPLIT_SECTION]
            if noise_removed:
                reason_codes.append(REASON_NAVIGATION_EXCLUDED)
            if len(body_chunks) > 1:
                reason_codes.append(REASON_SPLIT_CHUNK)
            candidates.append(
                AdobePassage(
                    product=metadata['product'],
                    source_type=metadata['source_type'],
                    canonical_url=metadata['canonical_url'],
                    url_sha256_12=_sha256_12(metadata['canonical_url']),
                    text=text,
                    heading=section_heading,
                    section_path=tuple(section_path),
                    title=metadata['title'],
                    chars=len(text),
                    reason_codes=_dedupe_codes(reason_codes),
                )
            )

    for raw_line in str(markdown or '').splitlines():
        line = raw_line.rstrip()
        heading = _heading_text(line)
        if heading is not None:
            flush()
            section_lines = []
            section_heading = heading
            section_path = _next_section_path(section_path, line, heading)
            continue
        section_lines.append(line)
    flush()
    return tuple(candidates)


def rank_adobe_passages(
    question: str,
    passages: Iterable[AdobePassage],
) -> tuple[AdobePassage, ...]:
    question_tokens = _tokens(question)
    question_alias_tokens = _alias_tokens(question_tokens)
    query_kind, query_reason = _query_kind(question)
    ranked: list[tuple[int, int, AdobePassage]] = []
    for index, passage in enumerate(passages):
        score, reason_codes = _score_passage(
            passage,
            question_tokens,
            question_alias_tokens,
            query_kind,
            query_reason,
        )
        if score <= 0:
            continue
        ranked.append((
            score,
            index,
            _replace_passage_score(passage, score, (*passage.reason_codes, *reason_codes)),
        ))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in ranked)


def select_adobe_passages(
    question: str,
    read_results: Iterable[Any],
    *,
    max_passage_chars: int = DEFAULT_PASSAGE_CHARS,
    passage_count: int = DEFAULT_PASSAGE_COUNT,
    prompt_budget_chars: int = DEFAULT_PROMPT_BUDGET_CHARS,
) -> AdobePassageSelection:
    candidates: list[AdobePassage] = []
    for read_result in read_results:
        markdown = str(_value(read_result, 'markdown', '') or '')
        if not markdown:
            continue
        candidates.extend(
            split_adobe_markdown(
                markdown,
                read_result,
                max_passage_chars=max_passage_chars,
            )
        )

    ranked = rank_adobe_passages(question, candidates)
    selected: list[AdobePassage] = []
    total_chars = 0
    reason_codes: list[str] = []
    max_count = _safe_positive_int(passage_count, DEFAULT_PASSAGE_COUNT)
    budget = _safe_positive_int(prompt_budget_chars, DEFAULT_PROMPT_BUDGET_CHARS)
    for passage in ranked:
        if len(selected) >= max_count:
            reason_codes.append(REASON_SELECTION_LIMIT_APPLIED)
            break
        if total_chars + passage.chars > budget:
            reason_codes.append(REASON_BUDGET_LIMIT_APPLIED)
            continue
        selected.append(passage)
        total_chars += passage.chars

    if not selected:
        evidence = EVIDENCE_INSUFFICIENT
        reason_codes.append(REASON_NO_RELEVANT_PASSAGE)
    elif len(selected) >= 2 and selected[0].score >= 40:
        evidence = EVIDENCE_SUFFICIENT
    else:
        evidence = EVIDENCE_PARTIAL

    return AdobePassageSelection(
        evidence=evidence,
        passages=tuple(selected),
        candidate_count=len(candidates),
        selected_count=len(selected),
        total_chars=total_chars,
        reason_codes=_dedupe_codes(reason_codes),
    )


def _score_passage(
    passage: AdobePassage,
    question_tokens: set[str],
    question_alias_tokens: set[str],
    query_kind: str,
    query_reason: str,
) -> tuple[int, tuple[str, ...]]:
    passage_tokens = _tokens(passage.text)
    heading_tokens = _tokens(passage.heading)
    overlap = question_tokens & passage_tokens
    heading_overlap = question_tokens & heading_tokens
    alias_overlap = _alias_overlap(
        question_tokens,
        question_alias_tokens,
        passage_tokens | heading_tokens,
        overlap | heading_overlap,
    )
    score = 0
    reason_codes: list[str] = [query_reason]
    if overlap:
        score += len(overlap) * 12
        reason_codes.append(REASON_SCORE_LEXICAL_OVERLAP)
    if heading_overlap:
        score += len(heading_overlap) * 10
        reason_codes.append(REASON_SCORE_HEADING_OVERLAP)
    if alias_overlap:
        score += len(alias_overlap) * 10
        reason_codes.append(REASON_SCORE_ALIAS_OVERLAP)
    source_bonus = _source_type_bonus(passage.source_type, query_kind)
    if source_bonus and (overlap or heading_overlap or alias_overlap):
        score += source_bonus
        reason_codes.append(REASON_SCORE_SOURCE_TYPE)
    if _looks_navigation_heavy(passage.text):
        score -= 50
        reason_codes.append(REASON_NAVIGATION_EXCLUDED)
    return max(0, score), _dedupe_codes(reason_codes)


def _source_type_bonus(source_type: str, query_kind: str) -> int:
    if query_kind == 'release':
        return {
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES: 30,
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES: 8,
        }.get(source_type, 0)
    if query_kind == 'issue':
        return {
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES: 30,
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES: 8,
        }.get(source_type, 0)
    return {
        adobe_docs_sources.SOURCE_TYPE_HELP_PAGE: 20,
        adobe_docs_sources.SOURCE_TYPE_HUB: 4,
    }.get(source_type, 0)


def _metadata_from_source(source_metadata: Any) -> dict[str, str]:
    product = str(_value(source_metadata, 'product', '') or '')
    if product:
        product = adobe_docs_sources.validate_product(product)
    source_type = str(_value(source_metadata, 'source_type', '') or adobe_docs_sources.SOURCE_TYPE_HELP_PAGE)
    if source_type not in adobe_docs_sources.VALID_SOURCE_TYPES:
        source_type = adobe_docs_sources.SOURCE_TYPE_HELP_PAGE
    canonical_url = str(_value(source_metadata, 'canonical_url', '') or '')
    title = str(_value(source_metadata, 'title', '') or '')
    return {
        'product': product,
        'source_type': source_type,
        'canonical_url': canonical_url,
        'title': title,
    }


def _value(source: Any, field: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field, default)
    return getattr(source, field, default)


def _heading_text(line: str) -> str | None:
    match = _HEADING_RE.match(str(line or '').strip())
    if not match:
        return None
    return _clean_heading(match.group(2))


def _next_section_path(previous: list[str], line: str, heading: str) -> list[str]:
    match = _HEADING_RE.match(str(line or '').strip())
    level = len(match.group(1)) if match else 1
    base = previous[: max(0, level - 1)]
    base.append(heading)
    return base


def _clean_section_lines(lines: list[str]) -> tuple[list[str], bool]:
    cleaned: list[str] = []
    noise_removed = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if cleaned and cleaned[-1]:
                cleaned.append('')
            continue
        if _is_navigation_line(stripped):
            noise_removed = True
            continue
        cleaned.append(stripped)
    return cleaned, noise_removed


def _is_navigation_line(line: str) -> bool:
    normalized = _normalize_text(line)
    if any(term in normalized for term in _NAVIGATION_TERMS):
        return True
    link_count = len(_LINK_RE.findall(line))
    word_count = len(_tokens(line))
    if link_count >= 1 and word_count <= 8:
        return True
    if link_count >= 3:
        return True
    return False


def _looks_like_useful_passage(text: str) -> bool:
    tokens = _tokens(text)
    if len(tokens) < 8:
        return False
    if _looks_navigation_heavy(text):
        return False
    return True


def _looks_navigation_heavy(text: str) -> bool:
    link_count = len(_LINK_RE.findall(text))
    tokens = _tokens(text)
    if not tokens:
        return True
    return link_count >= 3 and link_count >= len(tokens) / 6


def _chunk_text(text: str, max_chars: int) -> tuple[str, ...]:
    normalized = _normalize_passage_text(text)
    if len(normalized) <= max_chars:
        return (normalized,)
    paragraphs = [item.strip() for item in normalized.split('\n\n') if item.strip()]
    chunks: list[str] = []
    current = ''
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ''
            chunks.extend(_hard_wrap(paragraph, max_chars))
            continue
        candidate = f'{current}\n\n{paragraph}' if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return tuple(chunks)


def _with_heading_prefix(chunk: str, heading_prefix: str, max_chars: int) -> str:
    if not heading_prefix:
        return chunk
    candidate = _normalize_passage_text(f'{heading_prefix}{chunk}')
    return candidate if len(candidate) <= max_chars else chunk


def _hard_wrap(text: str, max_chars: int) -> tuple[str, ...]:
    words = text.split()
    chunks: list[str] = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word[:max_chars]
    if current:
        chunks.append(current)
    return tuple(chunks)


def _replace_passage_score(
    passage: AdobePassage,
    score: int,
    reason_codes: tuple[str, ...],
) -> AdobePassage:
    return AdobePassage(
        product=passage.product,
        source_type=passage.source_type,
        canonical_url=passage.canonical_url,
        url_sha256_12=passage.url_sha256_12,
        text=passage.text,
        heading=passage.heading,
        section_path=passage.section_path,
        title=passage.title,
        chars=passage.chars,
        score=score,
        reason_codes=_dedupe_codes(reason_codes),
    )


def _query_kind(question: str) -> tuple[str, str]:
    normalized = _normalize_text(question)
    if any(term in normalized for term in _ISSUE_TERMS):
        return 'issue', REASON_SOURCE_ISSUE_QUERY
    if any(term in normalized for term in _RELEASE_TERMS):
        return 'release', REASON_SOURCE_RELEASE_QUERY
    return 'usage', REASON_SOURCE_USAGE_QUERY


def _tokens(text: str) -> set[str]:
    normalized = _normalize_text(text)
    return {
        token
        for token in _WORD_RE.findall(normalized)
        if token not in _STOPWORDS and not token.isdigit()
    }


def _alias_tokens(tokens: set[str]) -> set[str]:
    aliases: set[str] = set()
    for token in tokens:
        aliases.update(_ADOBE_TERM_ALIASES.get(token, set()))
    return aliases - tokens


def _alias_overlap(
    question_tokens: set[str],
    question_alias_tokens: set[str],
    passage_tokens: set[str],
    direct_overlap: set[str],
) -> set[str]:
    overlap = question_alias_tokens & passage_tokens
    if not overlap:
        return set()
    if overlap - _GENERIC_ALIAS_TOKENS:
        return overlap
    if direct_overlap and question_tokens - {'outil', 'outils'}:
        return overlap
    return set()


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(text or '').lower())
    ascii_text = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', ascii_text).strip()


def _normalize_passage_text(text: str) -> str:
    lines = [line.strip() for line in str(text or '').splitlines()]
    compact = '\n'.join(lines)
    compact = re.sub(r'\n{3,}', '\n\n', compact)
    return compact.strip()


def _clean_heading(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '').strip())


def _safe_positive_int(value: int, default: int) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else default


def _sha256_12(value: str) -> str:
    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _dedupe_codes(codes: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        text = str(code or '').strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)
