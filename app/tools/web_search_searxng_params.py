from __future__ import annotations

from dataclasses import dataclass

from tools import web_search_profile


@dataclass(frozen=True)
class SearxngProfileParams:
    kind: str
    policy: str = 'historical_baseline'
    categories: tuple[str, ...] = ()
    engines: tuple[str, ...] = ()
    time_range: str = ''
    language: str = 'fr-FR'
    safesearch: str = '0'

    def as_request_params(self) -> dict[str, str]:
        params = {
            'language': self.language,
            'safesearch': self.safesearch,
        }
        if self.categories:
            params['categories'] = ','.join(self.categories)
        if self.engines:
            params['engines'] = ','.join(self.engines)
        if self.time_range:
            params['time_range'] = self.time_range
        return params

    def as_observability_fields(self) -> dict[str, object]:
        return {
            'searxng_profile_params_kind': self.kind,
            'searxng_profile_params_policy': self.policy,
            'searxng_categories': list(self.categories),
            'searxng_engines': list(self.engines),
            'searxng_time_range': self.time_range,
            'searxng_language': self.language,
            'searxng_safesearch': self.safesearch,
        }


HISTORICAL_PARAMS = SearxngProfileParams(kind='historical')


def build_profile_params(search_profile: str, *, enabled: bool = True) -> SearxngProfileParams:
    if not enabled:
        return HISTORICAL_PARAMS

    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    if profile in {web_search_profile.PROFILE_EXPLICIT_URL, web_search_profile.PROFILE_GENERAL}:
        return HISTORICAL_PARAMS
    if profile == web_search_profile.PROFILE_ACTUALITE:
        return SearxngProfileParams(
            kind='profiled_actualite_year_general',
            policy='soft_broad_hints',
            categories=('general',),
            time_range='year',
            language='fr-FR',
            safesearch='0',
        )
    if profile == web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE:
        return SearxngProfileParams(
            kind='profiled_technique_officielle_general_all',
            policy='soft_broad_hints',
            categories=('general',),
            language='all',
            safesearch='0',
        )
    if profile == web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS:
        return SearxngProfileParams(
            kind='profiled_institutionnel_francais_general_fr',
            policy='soft_broad_hints',
            categories=('general',),
            language='fr-FR',
            safesearch='0',
        )
    if profile == web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE:
        return SearxngProfileParams(
            kind='profiled_academique_philosophique_general_all',
            policy='soft_broad_hints',
            categories=('general',),
            language='all',
            safesearch='0',
        )
    return HISTORICAL_PARAMS


def empty_observability_fields(kind: str = 'none') -> dict[str, object]:
    return SearxngProfileParams(
        kind=str(kind or 'none'),
        policy='none',
        language='',
        safesearch='',
    ).as_observability_fields()
