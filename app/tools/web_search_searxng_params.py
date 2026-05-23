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
    reason_codes: tuple[str, ...] = ()
    hard_parameters: tuple[str, ...] = ()
    soft_signal_policy: str = ''

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
            'searxng_params_reason_codes': list(self.reason_codes),
            'searxng_hard_parameters': list(self.hard_parameters),
            'searxng_soft_signal_policy': self.soft_signal_policy,
        }


HISTORICAL_PARAMS = SearxngProfileParams(kind='historical')


_DOCUMENTATION_OFFICIELLE_ENGINES = (
    'microsoft learn',
    'mdn',
    'docker hub',
    'bing',
    'brave',
    'mojeek',
)
_ADMINISTRATIF_FRANCAIS_ENGINES = (
    'bing',
    'brave',
)
_ACADEMIQUE_ENGINES = (
    'arxiv',
    'openairepublications',
    'pubmed',
    'bing',
    'brave',
)
_ACTUALITE_ENGINES = (
    'bing news',
    'reuters',
    'bing',
    'duckduckgo news',
)
_GENERAL_DIVERS_ENGINES = (
    'bing',
    'brave',
    'mojeek',
)


def _governed_params(
    *,
    kind: str,
    categories: tuple[str, ...],
    engines: tuple[str, ...],
    language: str,
    time_range: str = '',
    reason_codes: tuple[str, ...],
) -> SearxngProfileParams:
    hard_parameters = ['categories', 'engines', 'language', 'safesearch']
    if time_range:
        hard_parameters.append('time_range')
    return SearxngProfileParams(
        kind=kind,
        policy='governed_engine_basket_v0',
        categories=categories,
        engines=engines,
        time_range=time_range,
        language=language,
        safesearch='0',
        reason_codes=reason_codes,
        hard_parameters=tuple(hard_parameters),
        soft_signal_policy='source_first_and_rerank_remain_soft_no_drop',
    )


def build_profile_params(search_profile: str, *, enabled: bool = True) -> SearxngProfileParams:
    if not enabled:
        return HISTORICAL_PARAMS

    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    if profile == web_search_profile.PROFILE_EXPLICIT_URL:
        return HISTORICAL_PARAMS
    if profile == web_search_profile.PROFILE_ACTUALITE:
        return _governed_params(
            kind='governed_actualite_news_general',
            categories=('general', 'news'),
            engines=_ACTUALITE_ENGINES,
            time_range='year',
            language='fr-FR',
            reason_codes=(
                'news_and_general_mix_preserves_institutional_sources',
                'reuters_not_single_source',
                'duckduckgo_news_secondary_only',
            ),
        )
    if profile == web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE:
        return _governed_params(
            kind='governed_documentation_officielle_it_general',
            categories=('general', 'it'),
            engines=_DOCUMENTATION_OFFICIELLE_ENGINES,
            language='all',
            reason_codes=(
                'official_docs_engine_basket',
                'source_first_authority_alignment_required_for_strong_bonus',
                'qa_not_primary_authority',
            ),
        )
    if profile == web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS:
        return _governed_params(
            kind='governed_administratif_francais_general',
            categories=('general',),
            engines=_ADMINISTRATIF_FRANCAIS_ENGINES,
            language='fr-FR',
            reason_codes=(
                'french_institutional_site_queries_remain_in_query_plan',
                'bing_brave_general_support_site_operator',
                'no_single_institution_engine',
            ),
        )
    if profile == web_search_profile.PROFILE_ACADEMIQUE:
        return _governed_params(
            kind='governed_academique_science_general',
            categories=('general', 'science'),
            engines=_ACADEMIQUE_ENGINES,
            language='all',
            reason_codes=(
                'academic_profile_remains_broad',
                'arxiv_openaire_pubmed_plus_general_web',
                'google_scholar_and_semantic_scholar_avoided',
            ),
        )
    if profile == web_search_profile.PROFILE_GENERAL:
        return _governed_params(
            kind='governed_general_divers_general',
            categories=('general',),
            engines=_GENERAL_DIVERS_ENGINES,
            language='fr-FR',
            reason_codes=(
                'plural_general_web_basket',
                'mojeek_secondary_candidate',
                'encyclopedias_not_hard_requested',
            ),
        )
    return HISTORICAL_PARAMS


def empty_observability_fields(kind: str = 'none') -> dict[str, object]:
    return SearxngProfileParams(
        kind=str(kind or 'none'),
        policy='none',
        language='',
        safesearch='',
    ).as_observability_fields()
