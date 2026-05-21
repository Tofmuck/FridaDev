from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from tools import web_search_profile


RERANK_POLICY = "soft_reorder_no_drop_v0"
RERANK_DISABLED_POLICY = "none"
RERANK_PROFILES = {
    web_search_profile.PROFILE_ACTUALITE,
    web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE,
    web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS,
    web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE,
}

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_STOPWORDS = {
    "avec",
    "cette",
    "dans",
    "des",
    "document",
    "donne",
    "donner",
    "elle",
    "est",
    "les",
    "leur",
    "leurs",
    "pour",
    "quelle",
    "quels",
    "quelles",
    "source",
    "sources",
    "sur",
    "une",
}
_DICTIONARY_DOMAINS = {
    "larousse.fr",
    "www.larousse.fr",
    "fr.wiktionary.org",
    "wiktionary.org",
    "dictionnaire.lerobert.com",
    "www.lerobert.com",
    "cnrtl.fr",
    "www.cnrtl.fr",
}
_CONJUGATOR_DOMAINS = {
    "leconjugueur.lefigaro.fr",
    "bescherelle.com",
    "conjugaison.lemonde.fr",
    "www.conjugaison.com",
}
_GENERIC_ENCYCLOPEDIA_DOMAINS = {
    "fr.wikipedia.org",
    "wikipedia.org",
    "www.wikipedia.org",
}
_INSTITUTIONNEL_FR_DOMAINS = {
    "service-public.fr",
    "www.service-public.fr",
    "ants.gouv.fr",
    "www.ants.gouv.fr",
    "legifrance.gouv.fr",
    "www.legifrance.gouv.fr",
}
_TECHNICAL_OFFICIAL_DOMAINS = {
    "openrouter.ai",
    "docs.openrouter.ai",
    "platform.openai.com",
    "docs.github.com",
    "developer.mozilla.org",
}
_ACADEMIC_DOMAINS = {
    "journals.openedition.org",
    "openedition.org",
    "www.openedition.org",
    "cairn.info",
    "www.cairn.info",
    "persee.fr",
    "www.persee.fr",
    "plato.stanford.edu",
    "jstor.org",
    "www.jstor.org",
    "hal.science",
    "erudit.org",
    "www.erudit.org",
}
_EU_OFFICIAL_SUFFIXES = (
    ".europa.eu",
)
_EU_OFFICIAL_DOMAINS = {
    "europa.eu",
    "ec.europa.eu",
    "digital-strategy.ec.europa.eu",
    "commission.europa.eu",
    "artificialintelligenceact.eu",
}


@dataclass(frozen=True)
class _Candidate:
    result: dict[str, Any]
    raw_rank: int
    domain: str
    score: float
    reasons: tuple[str, ...]


def empty_observability_fields(*, applied: bool = False, policy: str = RERANK_DISABLED_POLICY) -> dict[str, Any]:
    return {
        "rerank_applied": bool(applied),
        "rerank_policy": str(policy or RERANK_DISABLED_POLICY),
        "rerank_input_count": 0,
        "rerank_output_count": 0,
        "rerank_profile": "",
        "rerank_top_domains_before": [],
        "rerank_top_domains_after": [],
        "rerank_reason_counts": {},
        "rerank_promoted_count": 0,
        "rerank_downranked_count": 0,
    }


def rerank_results(
    results: list[dict[str, Any]],
    *,
    user_msg: str,
    primary_query: str,
    search_profile: str,
    max_results: int,
    enabled: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    original_results = [dict(result or {}) for result in results or []]
    if not enabled or profile not in RERANK_PROFILES or len(original_results) <= 1:
        return original_results, {
            **empty_observability_fields(applied=False),
            "rerank_profile": profile,
            "rerank_input_count": len(original_results),
            "rerank_output_count": len(original_results),
            "rerank_top_domains_before": _top_domains(original_results),
            "rerank_top_domains_after": _top_domains(original_results),
        }

    limit = int(max_results or 0)
    essential_terms = _essential_terms(user_msg, primary_query, profile)
    candidates = [
        _score_candidate(
            dict(result),
            raw_rank=index,
            profile=profile,
            essential_terms=essential_terms,
        )
        for index, result in enumerate(original_results, 1)
    ]
    ranked = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.raw_rank))
    diversified = _apply_domain_diversity(ranked, max_results=limit)
    if limit > 0:
        diversified = diversified[:limit]

    output: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    promoted_count = 0
    downranked_count = 0
    for reranked_rank, candidate in enumerate(diversified, 1):
        result = dict(candidate.result)
        reasons = list(candidate.reasons)
        if reranked_rank < candidate.raw_rank:
            bucket = "promoted"
            promoted_count += 1
        elif reranked_rank > candidate.raw_rank:
            bucket = "downranked"
            downranked_count += 1
        else:
            bucket = "kept"
        if bucket != "kept" and bucket not in reasons:
            reasons.append(bucket)
        reason_counts.update(reasons)
        result["raw_rank"] = candidate.raw_rank
        result["reranked_rank"] = reranked_rank
        result["rerank_score"] = round(candidate.score, 3)
        result["rerank_bucket"] = bucket
        result["rerank_reason_codes"] = sorted(dict.fromkeys(reasons))
        output.append(result)

    return output, {
        "rerank_applied": True,
        "rerank_policy": RERANK_POLICY,
        "rerank_input_count": len(original_results),
        "rerank_output_count": len(output),
        "rerank_profile": profile,
        "rerank_top_domains_before": _top_domains(original_results),
        "rerank_top_domains_after": _top_domains(output),
        "rerank_reason_counts": dict(sorted(reason_counts.items())),
        "rerank_promoted_count": promoted_count,
        "rerank_downranked_count": downranked_count,
    }


def _score_candidate(
    result: dict[str, Any],
    *,
    raw_rank: int,
    profile: str,
    essential_terms: set[str],
) -> _Candidate:
    url = str(result.get("url") or "")
    domain = _domain(url)
    title = str(result.get("title") or "")
    content = str(result.get("content") or "")
    searchable = _normalize_text(" ".join([title, content, url]))
    score = 1000.0 - (raw_rank * 2.0)
    reasons: list[str] = []

    if str(result.get("query_source_kind") or result.get("_query_source_kind") or "") == "secondary":
        score += 8.0
        reasons.append("secondary_query_soft_bonus")

    matched_terms = [term for term in essential_terms if term in searchable]
    if matched_terms:
        score += min(45.0, 7.0 * len(matched_terms))
        reasons.append("essential_terms_soft_bonus")

    if not title.strip() and not content.strip():
        score -= 25.0
        reasons.append("thin_result_soft_downrank")

    score, reasons = _apply_profile_score(
        profile=profile,
        domain=domain,
        url=url,
        title=title,
        searchable=searchable,
        score=score,
        reasons=reasons,
    )
    return _Candidate(
        result=result,
        raw_rank=raw_rank,
        domain=domain,
        score=score,
        reasons=tuple(reasons),
    )


def _apply_profile_score(
    *,
    profile: str,
    domain: str,
    url: str,
    title: str,
    searchable: str,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    if profile == web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS:
        if _domain_in(domain, _INSTITUTIONNEL_FR_DOMAINS) or domain.endswith(".gouv.fr"):
            score += 105.0
            reasons.append("profile_official_domain_soft_bonus")
        score, reasons = _dictionary_or_conjugator_downrank(domain, title, score, reasons)
        return score, reasons

    if profile == web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE:
        if _domain_in(domain, _TECHNICAL_OFFICIAL_DOMAINS):
            score += 105.0
            reasons.append("profile_official_domain_soft_bonus")
        if "/docs" in url.lower() or "documentation" in searchable or "api" in searchable:
            score += 24.0
            reasons.append("technical_documentation_soft_bonus")
        score, reasons = _dictionary_or_conjugator_downrank(domain, title, score, reasons)
        return score, reasons

    if profile == web_search_profile.PROFILE_ACTUALITE:
        if _is_eu_official_domain(domain):
            score += 100.0
            reasons.append("profile_official_domain_soft_bonus")
        if any(marker in searchable for marker in ("2026", "recent", "actuel", "actualite", "news", "press", "communique")):
            score += 22.0
            reasons.append("freshness_hint_soft_bonus")
        if _domain_in(domain, _GENERIC_ENCYCLOPEDIA_DOMAINS):
            score -= 55.0
            reasons.append("generic_encyclopedia_soft_downrank")
        score, reasons = _dictionary_or_conjugator_downrank(domain, title, score, reasons)
        return score, reasons

    if profile == web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE:
        if _domain_in(domain, _ACADEMIC_DOMAINS):
            score += 105.0
            reasons.append("profile_academic_domain_soft_bonus")
        if any(marker in searchable for marker in ("derrida", "philosophie", "philosophy", "trace", "deconstruction")):
            score += 20.0
            reasons.append("academic_concept_soft_bonus")
        if "trace-colmar" in domain or "trace colmar" in searchable:
            score -= 125.0
            reasons.append("homonym_soft_downrank")
        score, reasons = _dictionary_or_conjugator_downrank(domain, title, score, reasons)
        return score, reasons

    return score, reasons


def _dictionary_or_conjugator_downrank(
    domain: str,
    title: str,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    title_n = _normalize_text(title)
    if _domain_in(domain, _CONJUGATOR_DOMAINS) or "conjugaison" in title_n or "conjuguer" in title_n:
        score -= 125.0
        reasons.append("conjugator_soft_downrank")
    if _domain_in(domain, _DICTIONARY_DOMAINS) or "dictionnaire" in title_n or "wiktionnaire" in title_n:
        score -= 90.0
        reasons.append("dictionary_soft_downrank")
    return score, reasons


def _apply_domain_diversity(candidates: list[_Candidate], *, max_results: int) -> list[_Candidate]:
    if len(candidates) <= 2:
        return candidates
    limit = int(max_results or len(candidates))
    if limit <= 0:
        limit = len(candidates)
    domains = [candidate.domain for candidate in candidates if candidate.domain]
    if len(set(domains)) <= 1:
        return candidates

    per_domain_cap = 2 if limit >= 4 else 1
    selected: list[_Candidate] = []
    delayed: list[_Candidate] = []
    selected_domains: Counter[str] = Counter()
    for candidate in candidates:
        domain = candidate.domain or "domain_unknown"
        if selected_domains[domain] >= per_domain_cap and _has_selectable_other_domain(
            candidates,
            selected,
            domain,
        ):
            delayed.append(_with_reason(candidate, "domain_concentration_soft_downrank", score_delta=-6.0))
            continue
        selected.append(candidate)
        selected_domains[domain] += 1
    selected.extend(delayed)
    return selected


def _has_selectable_other_domain(candidates: list[_Candidate], selected: list[_Candidate], domain: str) -> bool:
    selected_ids = {id(candidate) for candidate in selected}
    for candidate in candidates:
        if id(candidate) in selected_ids:
            continue
        if (candidate.domain or "domain_unknown") != domain:
            return True
    return False


def _with_reason(candidate: _Candidate, reason: str, *, score_delta: float) -> _Candidate:
    reasons = list(candidate.reasons)
    if reason not in reasons:
        reasons.append(reason)
    return _Candidate(
        result=candidate.result,
        raw_rank=candidate.raw_rank,
        domain=candidate.domain,
        score=candidate.score + score_delta,
        reasons=tuple(reasons),
    )


def _essential_terms(user_msg: str, primary_query: str, profile: str) -> set[str]:
    terms = {
        token
        for token in _TOKEN_RE.findall(_normalize_text(" ".join([user_msg, primary_query])))
        if token not in _STOPWORDS and len(token) > 2
    }
    if profile == web_search_profile.PROFILE_ACTUALITE:
        terms.update({"2026", "act", "ai", "europe", "intelligence", "artificial"})
    elif profile == web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE:
        terms.update({"api", "docs", "documentation", "official", "officielle"})
    elif profile == web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS:
        terms.update({"cni", "carte", "identite", "renouvellement", "procedure"})
    elif profile == web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE:
        terms.update({"derrida", "trace", "philosophie", "philosophy", "academique"})
    return terms


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _domain(url: str) -> str:
    return urlparse(str(url or "")).netloc.strip().lower().removeprefix("www.")


def _domain_in(domain: str, domains: set[str]) -> bool:
    candidates = {domain, f"www.{domain}"}
    return any(candidate in domains for candidate in candidates)


def _is_eu_official_domain(domain: str) -> bool:
    if _domain_in(domain, _EU_OFFICIAL_DOMAINS):
        return True
    return any(domain.endswith(suffix) for suffix in _EU_OFFICIAL_SUFFIXES)


def _top_domains(results: list[dict[str, Any]], *, limit: int = 5) -> list[str]:
    domains: list[str] = []
    for result in results:
        domain = _domain(str(result.get("url") or ""))
        if domain and domain not in domains:
            domains.append(domain)
        if len(domains) >= limit:
            break
    return domains
