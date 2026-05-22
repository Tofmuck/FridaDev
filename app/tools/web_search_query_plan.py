from __future__ import annotations

import re
import unicodedata

from tools import web_search_profile


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


def _technique_officielle_queries(original_user_message: str, primary_query: str) -> list[str]:
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


def _institutionnel_francais_queries(original_user_message: str, primary_query: str) -> list[str]:
    text = _context_text(original_user_message, primary_query)
    if _contains_any(text, ('cni', 'carte nationale', 'identite', 'passeport')):
        return [
            'renouvellement carte nationale identite site:service-public.fr',
            'renouvellement carte identite site:ants.gouv.fr',
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


def _academique_philosophique_queries(original_user_message: str, primary_query: str) -> list[str]:
    text = _context_text(original_user_message, primary_query)
    if _contains_any(text, ('derrida', 'trace')):
        return [
            'Derrida trace sources universitaires OpenEdition Cairn',
            'Derrida trace Stanford Encyclopedia philosophy',
        ]
    return [
        f'{primary_query} sources universitaires OpenEdition Cairn Persee',
        f'{primary_query} Stanford Encyclopedia JSTOR',
    ]


def build_specialized_queries(
    original_user_message: str,
    primary_query: str,
    search_profile: str,
) -> list[str]:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    if profile == web_search_profile.PROFILE_EXPLICIT_URL:
        return []

    primary = _clean_query(primary_query) or _clean_query(original_user_message)
    if not primary:
        return []

    if profile == web_search_profile.PROFILE_ACTUALITE:
        raw_candidates = _actualite_queries(original_user_message, primary)
    elif profile == web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE:
        raw_candidates = _technique_officielle_queries(original_user_message, primary)
    elif profile == web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS:
        raw_candidates = _institutionnel_francais_queries(original_user_message, primary)
    elif profile == web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE:
        raw_candidates = _academique_philosophique_queries(original_user_message, primary)
    else:
        raw_candidates = []

    seen = {_normalize_query(primary)}
    candidates: list[str] = []
    for candidate in raw_candidates:
        _append_query(candidates, seen, candidate)
        if len(candidates) >= MAX_SECONDARY_QUERIES:
            break
    return candidates
