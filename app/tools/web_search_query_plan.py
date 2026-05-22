from __future__ import annotations

import re
import unicodedata

from tools import web_search_profile, web_search_source_first


MAX_SECONDARY_QUERIES = 2


def _normalize_query(value: str) -> str:
    text = unicodedata.normalize('NFKD', str(value or ''))
    ascii_text = ''.join(char for char in text if not unicodedata.combining(char))
    ascii_text = ascii_text.lower().replace("'", ' ')
    return re.sub(r'\s+', ' ', ascii_text).strip()


def _clean_query(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip(' .,;:!?')


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _append_query(candidates: list[str], seen: set[str], value: str) -> None:
    query = _clean_query(value)
    normalized = _normalize_query(query)
    if not query or not normalized or normalized in seen:
        return
    seen.add(normalized)
    candidates.append(query)


def _context_text(original_user_message: str, primary_query: str) -> str:
    return _normalize_query(f'{original_user_message} {primary_query}')


def _actualite_queries(original_user_message: str, primary_query: str) -> list[str]:
    text = _context_text(original_user_message, primary_query)
    if _contains_any(text, ('europe', 'ia', 'intelligence artificielle', 'regulation', 'ai act')):
        return [
            f'{primary_query} actualite recente sources officielles',
            'AI Act intelligence artificielle Europe 2026 site:ec.europa.eu',
        ]
    return [
        f'{primary_query} actualite recente sources officielles',
        f'{primary_query} dernieres annonces source officielle',
    ]


def _documentation_officielle_queries(
    original_user_message: str,
    primary_query: str,
    source_first_plan: web_search_source_first.SourceFirstPlan | None,
) -> list[str]:
    plan = source_first_plan or web_search_source_first.empty_plan()
    if plan.active and plan.authority:
        base = _clean_query(" ".join(part for part in (plan.authority, plan.product) if part))
        if plan.probable_domains:
            queries = [f'{base} documentation officielle site:{plan.probable_domains[0]}']
            if len(plan.probable_domains) > 1:
                queries.append(f'{base} official documentation site:{plan.probable_domains[1]}')
            else:
                queries.append(f'{base} official documentation')
            return queries
        return [
            f'{base} documentation officielle',
            f'{base} official documentation',
        ]

    text = _context_text(original_user_message, primary_query)
    if 'openrouter' in text:
        return [
            'OpenRouter openrouter:web_search documentation officielle',
            'openrouter:web_search parametres cout site:openrouter.ai/docs',
        ]
    return [
        f'{primary_query} documentation officielle',
        f'{primary_query} official documentation',
    ]


def _administratif_francais_queries(original_user_message: str, primary_query: str) -> list[str]:
    text = _context_text(original_user_message, primary_query)
    if _contains_any(text, ('cni', 'carte nationale', 'identite', 'passeport')):
        return [
            'renouvellement carte nationale identite site:service-public.fr',
            'renouvellement carte identite site:ants.gouv.fr',
        ]
    if _contains_any(text, ('caf', 'allocation logement', 'aide logement')):
        return [
            f'{primary_query} site:caf.fr',
            f'{primary_query} site:service-public.fr',
        ]
    if _contains_any(text, ('education nationale', 'eduscol', 'programme scolaire', 'terminale')):
        return [
            f'{primary_query} site:education.gouv.fr',
            f'{primary_query} site:eduscol.education.fr',
        ]
    if _contains_any(text, ('droit', 'loi', 'decret', 'arrete', 'legifrance')):
        return [
            f'{primary_query} site:service-public.fr',
            f'{primary_query} site:legifrance.gouv.fr',
        ]
    return [
        f'{primary_query} site:service-public.fr',
        f'{primary_query} site:gouv.fr',
    ]


def _academique_queries(original_user_message: str, primary_query: str) -> list[str]:
    text = _context_text(original_user_message, primary_query)
    if _contains_any(text, ('arxiv', 'physique', 'mathematique', 'sciences exactes', 'noether', 'crispr', 'pubmed')):
        return [
            f'{primary_query} arXiv PubMed OpenAIRE HAL',
            f'{primary_query} article scientifique DOI',
        ]
    if _contains_any(text, ('derrida', 'trace', 'bourdieu', 'sociologie', 'philosophie', 'shs')):
        return [
            f'{primary_query} sources universitaires OpenEdition Cairn Persee',
            f'{primary_query} Stanford Encyclopedia HAL JSTOR',
        ]
    return [
        f'{primary_query} sources universitaires HAL OpenAIRE',
        f'{primary_query} article scientifique DOI',
    ]


def build_specialized_queries(
    original_user_message: str,
    primary_query: str,
    search_profile: str,
    source_first_plan: web_search_source_first.SourceFirstPlan | None = None,
) -> list[str]:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    if profile == web_search_profile.PROFILE_EXPLICIT_URL:
        return []

    primary = _clean_query(primary_query) or _clean_query(original_user_message)
    if not primary:
        return []
    if source_first_plan is None and profile == web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE:
        source_first_plan = web_search_source_first.build_source_first_plan(
            original_user_message,
            primary,
            profile,
        )

    if profile == web_search_profile.PROFILE_ACTUALITE:
        raw_candidates = _actualite_queries(original_user_message, primary)
    elif profile == web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE:
        raw_candidates = _documentation_officielle_queries(original_user_message, primary, source_first_plan)
    elif profile == web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS:
        raw_candidates = _administratif_francais_queries(original_user_message, primary)
    elif profile == web_search_profile.PROFILE_ACADEMIQUE:
        raw_candidates = _academique_queries(original_user_message, primary)
    else:
        raw_candidates = []

    seen = {_normalize_query(primary)}
    candidates: list[str] = []
    for candidate in raw_candidates:
        _append_query(candidates, seen, candidate)
        if len(candidates) >= MAX_SECONDARY_QUERIES:
            break
    return candidates
