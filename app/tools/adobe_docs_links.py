from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from typing import Iterable
from urllib.parse import urljoin

from tools import adobe_docs_sources


DEFAULT_FOLLOW_LINK_LIMIT = 6
MAX_FOLLOW_LINK_LIMIT = 8

REASON_MARKDOWN_LINK_EXTRACTED = 'markdown_link_extracted'
REASON_RELATIVE_LINK_RESOLVED = 'relative_link_resolved'
REASON_SEED_CANDIDATE = 'seed_candidate'
REASON_DUPLICATE_CANONICAL_URL = 'duplicate_canonical_url'
REASON_RANK_RELEASE_QUERY = 'rank_release_query'
REASON_RANK_ISSUE_QUERY = 'rank_issue_query'
REASON_RANK_USAGE_QUERY = 'rank_usage_query'
REASON_RANK_LIMIT_APPLIED = 'rank_limit_applied'

_MARKDOWN_LINK_RE = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+["\'][^)]*["\'])?\)')
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


@dataclass(frozen=True, repr=False)
class AdobeDocsLink:
    product: str
    source_type: str
    canonical_url: str
    url_sha256_12: str
    anchor_text_chars: int = 0
    reason_codes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "AdobeDocsLink("
            f"product={self.product!r}, source_type={self.source_type!r}, "
            f"url_sha256_12={self.url_sha256_12!r}, "
            f"anchor_text_chars={self.anchor_text_chars!r}, "
            f"reason_codes={self.reason_codes!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'product': self.product,
            'source_type': self.source_type,
            'url_sha256_12': self.url_sha256_12,
            'anchor_text_chars': self.anchor_text_chars,
            'reason_codes': list(self.reason_codes),
        }


@dataclass(frozen=True, repr=False)
class RankedAdobeDocsLink:
    rank: int
    product: str
    source_type: str
    canonical_url: str
    url_sha256_12: str
    score: int
    reason_codes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "RankedAdobeDocsLink("
            f"rank={self.rank!r}, product={self.product!r}, "
            f"source_type={self.source_type!r}, url_sha256_12={self.url_sha256_12!r}, "
            f"score={self.score!r}, reason_codes={self.reason_codes!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'rank': self.rank,
            'product': self.product,
            'source_type': self.source_type,
            'url_sha256_12': self.url_sha256_12,
            'score': self.score,
            'reason_codes': list(self.reason_codes),
        }


def extract_adobe_links(markdown: str, base_url: str, product: str) -> tuple[AdobeDocsLink, ...]:
    normalized_product = adobe_docs_sources.validate_product(product)
    links: list[AdobeDocsLink] = []
    seen: set[str] = set()
    for match in _MARKDOWN_LINK_RE.finditer(str(markdown or '')):
        anchor_text = str(match.group(1) or '')
        raw_href = _strip_markdown_href(match.group(2))
        if not raw_href:
            continue

        resolved_url = urljoin(str(base_url or ''), raw_href)
        validation = adobe_docs_sources.validate_adobe_url(resolved_url, normalized_product)
        if not validation.ok:
            continue
        if validation.canonical_url in seen:
            continue
        seen.add(validation.canonical_url)

        reason_codes = list(validation.reason_codes)
        reason_codes.append(REASON_MARKDOWN_LINK_EXTRACTED)
        if resolved_url != raw_href:
            reason_codes.append(REASON_RELATIVE_LINK_RESOLVED)
        links.append(
            AdobeDocsLink(
                product=normalized_product,
                source_type=validation.source_type,
                canonical_url=validation.canonical_url,
                url_sha256_12=_sha256_12(validation.canonical_url),
                anchor_text_chars=len(anchor_text),
                reason_codes=_dedupe_codes(reason_codes),
            )
        )
    return tuple(links)


def rank_adobe_links(
    question: str,
    links: Iterable[AdobeDocsLink],
    product: str,
    limit: int = DEFAULT_FOLLOW_LINK_LIMIT,
) -> tuple[RankedAdobeDocsLink, ...]:
    normalized_product = adobe_docs_sources.validate_product(product)
    query_kind, query_reason = _query_kind(question)
    candidates = _dedupe_links_with_seeds(links, normalized_product)

    scored: list[tuple[int, int, AdobeDocsLink, tuple[str, ...]]] = []
    for index, link in enumerate(candidates):
        score, score_reasons = _score_link(link, query_kind)
        reason_codes = _dedupe_codes((*link.reason_codes, query_reason, *score_reasons))
        scored.append((score, index, link, reason_codes))

    scored.sort(key=lambda item: (-item[0], item[1]))
    effective_limit = _safe_limit(limit)
    selected = scored[:effective_limit]
    limit_applied = len(scored) > effective_limit
    ranked: list[RankedAdobeDocsLink] = []
    for rank, (score, _index, link, reason_codes) in enumerate(selected, start=1):
        final_reasons = reason_codes
        if limit_applied:
            final_reasons = _dedupe_codes((*final_reasons, REASON_RANK_LIMIT_APPLIED))
        ranked.append(
            RankedAdobeDocsLink(
                rank=rank,
                product=link.product,
                source_type=link.source_type,
                canonical_url=link.canonical_url,
                url_sha256_12=link.url_sha256_12,
                score=score,
                reason_codes=final_reasons,
            )
        )
    return tuple(ranked)


def _dedupe_links_with_seeds(links: Iterable[AdobeDocsLink], product: str) -> tuple[AdobeDocsLink, ...]:
    seen: set[str] = set()
    result: list[AdobeDocsLink] = []
    for link in links:
        if link.product != product or not link.canonical_url or link.canonical_url in seen:
            continue
        validation = adobe_docs_sources.validate_adobe_url(link.canonical_url, product)
        if not validation.ok:
            continue
        seen.add(validation.canonical_url)
        result.append(link)

    for source in adobe_docs_sources.sources_for_product(product):
        if source.url in seen:
            continue
        seen.add(source.url)
        result.append(
            AdobeDocsLink(
                product=product,
                source_type=source.source_type,
                canonical_url=source.url,
                url_sha256_12=_sha256_12(source.url),
                anchor_text_chars=0,
                reason_codes=(REASON_SEED_CANDIDATE,),
            )
        )
    return tuple(result)


def _score_link(link: AdobeDocsLink, query_kind: str) -> tuple[int, tuple[str, ...]]:
    source_type = str(link.source_type or '')
    if query_kind == 'release':
        weights = {
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES: 100,
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES: 35,
            adobe_docs_sources.SOURCE_TYPE_HELP_PAGE: 20,
            adobe_docs_sources.SOURCE_TYPE_HUB: 10,
        }
    elif query_kind == 'issue':
        weights = {
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES: 100,
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES: 35,
            adobe_docs_sources.SOURCE_TYPE_HELP_PAGE: 20,
            adobe_docs_sources.SOURCE_TYPE_HUB: 10,
        }
    else:
        weights = {
            adobe_docs_sources.SOURCE_TYPE_HELP_PAGE: 70,
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES: 30,
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES: 25,
            adobe_docs_sources.SOURCE_TYPE_HUB: 10,
        }
    return int(weights.get(source_type, 0)), (f'rank_source_type_{source_type or "unknown"}',)


def _query_kind(question: str) -> tuple[str, str]:
    normalized = _normalize_query(question)
    if any(term in normalized for term in _ISSUE_TERMS):
        return 'issue', REASON_RANK_ISSUE_QUERY
    if any(term in normalized for term in _RELEASE_TERMS):
        return 'release', REASON_RANK_RELEASE_QUERY
    return 'usage', REASON_RANK_USAGE_QUERY


def _normalize_query(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(text or '').lower())
    ascii_text = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', ascii_text).strip()


def _strip_markdown_href(value: str) -> str:
    href = str(value or '').strip()
    if href.startswith('<') and href.endswith('>'):
        href = href[1:-1].strip()
    return href


def _safe_limit(limit: int) -> int:
    try:
        value = int(limit or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return DEFAULT_FOLLOW_LINK_LIMIT
    return max(1, min(value, MAX_FOLLOW_LINK_LIMIT))


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
