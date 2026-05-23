from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from tools import web_search_profile, web_search_source_first


POLICY_KIND = 'local_web_profile_policy_v0'
SOURCE_EVIDENCE_POLICY_KIND = 'local_web_profile_source_evidence_v0'
LATENCY_TARGET_NORMAL_S = 25
LATENCY_TARGET_FAST_S = 20

_SITUATED_UNION_DOMAINS = (
    'sudeducation.org',
    'solidaires.org',
    'cgt.fr',
    'cgteduc.fr',
    'cgteducactionnice.org',
)
_GENERAL_DOWNRANK_DOMAINS = (
    'larousse.fr',
    'fr.wiktionary.org',
    'dictionnaire.lerobert.com',
    'leconjugueur.lefigaro.fr',
    'bescherelle.com',
    'conjugaison.lemonde.fr',
)


@dataclass(frozen=True)
class WebSearchProfilePolicy:
    profile: str
    mode: str
    expected_domains: tuple[str, ...] = ()
    secondary_domains: tuple[str, ...] = ()
    downrank_domains: tuple[str, ...] = ()
    situated_secondary_domains: tuple[str, ...] = ()
    crawl_top_n_budget: int = 0
    crawl_max_chars_budget: int = 0
    manual_latency_target_s: int = LATENCY_TARGET_NORMAL_S
    reason_codes: tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        return POLICY_KIND

    def as_dict(self) -> dict[str, Any]:
        return {
            'profile_policy_kind': self.kind,
            'profile_policy_mode': self.mode,
            'profile_expected_domains': list(self.expected_domains),
            'profile_secondary_domains': list(self.secondary_domains),
            'profile_downrank_domains': list(self.downrank_domains),
            'profile_situated_secondary_domains': list(self.situated_secondary_domains),
            'profile_policy_reason_codes': list(self.reason_codes),
            'profile_crawl_top_n_budget': self.crawl_top_n_budget,
            'profile_crawl_max_chars_budget': self.crawl_max_chars_budget,
            'profile_manual_latency_target_s': self.manual_latency_target_s,
        }

    def as_observability_fields(self) -> dict[str, Any]:
        return self.as_dict()


def empty_observability_fields() -> dict[str, Any]:
    return {
        'profile_policy_kind': 'none',
        'profile_policy_mode': 'none',
        'profile_expected_domains': [],
        'profile_secondary_domains': [],
        'profile_downrank_domains': [],
        'profile_situated_secondary_domains': [],
        'profile_policy_reason_codes': [],
        'profile_crawl_top_n_budget': 0,
        'profile_crawl_max_chars_budget': 0,
        'profile_manual_latency_target_s': 0,
        **empty_source_evidence_fields(),
    }


def empty_source_evidence_fields() -> dict[str, Any]:
    return {
        'profile_source_evidence_policy_kind': SOURCE_EVIDENCE_POLICY_KIND,
        'profile_expected_source_present': False,
        'profile_expected_material_used': False,
        'profile_secondary_source_present': False,
        'profile_secondary_material_used': False,
        'profile_situated_source_present': False,
        'profile_situated_material_used': False,
        'profile_downrank_source_present': False,
        'profile_downrank_material_used': False,
        'profile_insufficient_evidence': False,
        'profile_insufficient_evidence_reason_codes': [],
        'profile_source_domain_counts': {
            'expected_seen': 0,
            'expected_used': 0,
            'secondary_seen': 0,
            'secondary_used': 0,
            'situated_seen': 0,
            'situated_used': 0,
            'downrank_seen': 0,
            'downrank_used': 0,
            'neutral_seen': 0,
            'neutral_used': 0,
        },
    }


def build_profile_policy(
    search_profile: str,
    *,
    source_first_plan: web_search_source_first.SourceFirstPlan | Mapping[str, Any] | None = None,
) -> WebSearchProfilePolicy:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    source_plan = (
        source_first_plan
        if isinstance(source_first_plan, web_search_source_first.SourceFirstPlan)
        else web_search_source_first.plan_from_mapping(source_first_plan)
    )
    if profile == web_search_profile.PROFILE_EXPLICIT_URL:
        return WebSearchProfilePolicy(
            profile=profile,
            mode='explicit_url_direct_read_priority',
            crawl_top_n_budget=2,
            crawl_max_chars_budget=5000,
            manual_latency_target_s=LATENCY_TARGET_NORMAL_S,
            reason_codes=('explicit_url_direct_path_unchanged',),
        )
    if profile == web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE:
        if source_plan.active and source_plan.probable_domains:
            return WebSearchProfilePolicy(
                profile=profile,
                mode='source_first_strict_when_authority_named',
                expected_domains=tuple(source_plan.probable_domains),
                secondary_domains=(
                    'learn.microsoft.com',
                    'developer.mozilla.org',
                    'docs.docker.com',
                    'docs.stripe.com',
                ),
                downrank_domains=(
                    'stackoverflow.com',
                    'askubuntu.com',
                    'superuser.com',
                    'github.com',
                    'medium.com',
                    'dev.to',
                    *_GENERAL_DOWNRANK_DOMAINS,
                ),
                crawl_top_n_budget=3,
                crawl_max_chars_budget=7000,
                manual_latency_target_s=LATENCY_TARGET_NORMAL_S,
                reason_codes=(
                    'source_first_authority_named_strict',
                    'third_party_qa_secondary_not_primary',
                ),
            )
        return WebSearchProfilePolicy(
            profile=profile,
            mode='open_assisted_when_authority_unknown_or_floue',
            secondary_domains=(
                'learn.microsoft.com',
                'developer.mozilla.org',
                'docs.docker.com',
                'docs.stripe.com',
            ),
            downrank_domains=(
                'stackoverflow.com',
                'askubuntu.com',
                'superuser.com',
                'github.com',
                'medium.com',
                'dev.to',
                *_GENERAL_DOWNRANK_DOMAINS,
            ),
            crawl_top_n_budget=3,
            crawl_max_chars_budget=7000,
            manual_latency_target_s=LATENCY_TARGET_NORMAL_S,
            reason_codes=(
                'documentation_open_assisted_no_invented_authority',
                'generic_documentation_terms_not_sufficient_for_strong_promotion',
            ),
        )
    if profile == web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS:
        return WebSearchProfilePolicy(
            profile=profile,
            mode='french_administrative_official_first_with_situated_counterpoints',
            expected_domains=(
                'service-public.fr',
                'ants.gouv.fr',
                'legifrance.gouv.fr',
                '.gouv.fr',
                'education.gouv.fr',
                'eduscol.education.fr',
                'enseignementsup-recherche.gouv.fr',
                'onisep.fr',
                'ac-*.fr',
            ),
            secondary_domains=_SITUATED_UNION_DOMAINS,
            downrank_domains=_GENERAL_DOWNRANK_DOMAINS,
            situated_secondary_domains=_SITUATED_UNION_DOMAINS,
            crawl_top_n_budget=3,
            crawl_max_chars_budget=6500,
            manual_latency_target_s=LATENCY_TARGET_NORMAL_S,
            reason_codes=(
                'french_official_sources_first',
                'education_nationale_domains_expected',
                'union_sources_situated_secondary_not_administrative_authority',
            ),
        )
    if profile == web_search_profile.PROFILE_ACADEMIQUE:
        return WebSearchProfilePolicy(
            profile=profile,
            mode='broad_academic_open_with_academic_source_preference',
            expected_domains=(
                'arxiv.org',
                'openaire.eu',
                'explore.openaire.eu',
                'pubmed.ncbi.nlm.nih.gov',
                'hal.science',
                'journals.openedition.org',
                'openedition.org',
                'cairn.info',
                'persee.fr',
                'doi.org',
            ),
            secondary_domains=(
                'plato.stanford.edu',
                'jstor.org',
                'erudit.org',
                'univ-*.fr',
                '.edu',
            ),
            downrank_domains=(
                'fr.wikipedia.org',
                'wikipedia.org',
                'medium.com',
                'blogspot.com',
                *_GENERAL_DOWNRANK_DOMAINS,
            ),
            crawl_top_n_budget=3,
            crawl_max_chars_budget=8000,
            manual_latency_target_s=LATENCY_TARGET_NORMAL_S,
            reason_codes=('academic_profile_broad_not_philosophy_only', 'academic_sources_preferred_softly'),
        )
    if profile == web_search_profile.PROFILE_ACTUALITE:
        return WebSearchProfilePolicy(
            profile=profile,
            mode='fresh_news_institutional_first_not_single_source',
            expected_domains=('reuters.com', 'europa.eu', '.europa.eu', '.gouv.fr'),
            secondary_domains=('bing.com/news',),
            downrank_domains=('fr.wikipedia.org', 'wikipedia.org', *_GENERAL_DOWNRANK_DOMAINS),
            crawl_top_n_budget=2,
            crawl_max_chars_budget=4500,
            manual_latency_target_s=LATENCY_TARGET_FAST_S,
            reason_codes=('freshness_target_normal_web_manual', 'reuters_never_single_source'),
        )
    return WebSearchProfilePolicy(
        profile=web_search_profile.PROFILE_GENERAL,
        mode='plural_general_divers_sober',
        secondary_domains=('wikipedia.org', 'fr.wikipedia.org', 'wikidata.org'),
        downrank_domains=(),
        crawl_top_n_budget=2,
        crawl_max_chars_budget=5000,
        manual_latency_target_s=LATENCY_TARGET_FAST_S,
        reason_codes=('general_divers_plural_sober', 'mojeek_secondary_candidate_not_sovereign'),
    )


def effective_crawl_top_n(search_profile: str, runtime_top_n: int | None) -> int:
    runtime_value = _to_int(runtime_top_n)
    if runtime_value <= 0:
        return runtime_value
    budget = build_profile_policy(search_profile).crawl_top_n_budget
    if budget <= 0:
        return runtime_value
    return min(runtime_value, budget)


def effective_crawl_max_chars(search_profile: str, runtime_max_chars: int | None) -> int:
    runtime_value = _to_int(runtime_max_chars)
    if runtime_value <= 0:
        return runtime_value
    budget = build_profile_policy(search_profile).crawl_max_chars_budget
    if budget <= 0:
        return runtime_value
    return min(runtime_value, budget)


def evaluate_profile_evidence(
    search_profile: str,
    *,
    sources: Sequence[Mapping[str, Any]],
    policy_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_from_fields(search_profile, policy_fields)
    counts = dict(empty_source_evidence_fields()['profile_source_domain_counts'])
    seen_expected = seen_secondary = seen_situated = seen_downrank = False
    used_expected = used_secondary = used_situated = used_downrank = False
    used_count = 0
    used_kinds: set[str] = set()
    for source in sources or ():
        source_data = source if isinstance(source, Mapping) else {}
        used = _source_used(source_data)
        if used:
            used_count += 1
            used_kinds.add(str(source_data.get('used_content_kind') or 'none'))
        category = _classify_source(source_data, policy)
        counts[f'{category}_seen'] += 1
        if used:
            counts[f'{category}_used'] += 1
        if category == 'situated':
            counts['secondary_seen'] += 1
            if used:
                counts['secondary_used'] += 1
        if category == 'expected':
            seen_expected = True
            used_expected = used_expected or used
        elif category == 'secondary':
            seen_secondary = True
            used_secondary = used_secondary or used
        elif category == 'situated':
            seen_secondary = True
            seen_situated = True
            used_secondary = used_secondary or used
            used_situated = used_situated or used
        elif category == 'downrank':
            seen_downrank = True
            used_downrank = used_downrank or used

    insufficient_reasons: list[str] = []
    if used_count <= 0:
        insufficient_reasons.append('no_prompt_material')
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    expected_required = bool(policy.expected_domains) and profile in {
        web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
    }
    if expected_required and not used_expected:
        insufficient_reasons.append('expected_authority_material_missing')
    if profile == web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS and used_situated and not used_expected:
        insufficient_reasons.append('situated_secondary_without_official_material')
    if profile in {
        web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
        web_search_profile.PROFILE_ACADEMIQUE,
        web_search_profile.PROFILE_ACTUALITE,
    } and used_kinds == {'search_snippet'}:
        insufficient_reasons.append('snippet_only_profile_material')

    return {
        'profile_source_evidence_policy_kind': SOURCE_EVIDENCE_POLICY_KIND,
        'profile_expected_source_present': seen_expected,
        'profile_expected_material_used': used_expected,
        'profile_secondary_source_present': seen_secondary,
        'profile_secondary_material_used': used_secondary,
        'profile_situated_source_present': seen_situated,
        'profile_situated_material_used': used_situated,
        'profile_downrank_source_present': seen_downrank,
        'profile_downrank_material_used': used_downrank,
        'profile_insufficient_evidence': bool(insufficient_reasons),
        'profile_insufficient_evidence_reason_codes': _dedupe(insufficient_reasons),
        'profile_source_domain_counts': counts,
    }


def classify_source_against_policy(source: Mapping[str, Any], policy: WebSearchProfilePolicy) -> str:
    return _classify_source(source, policy)


def _policy_from_fields(search_profile: str, fields: Mapping[str, Any] | None) -> WebSearchProfilePolicy:
    data = fields if isinstance(fields, Mapping) else {}
    if data.get('profile_policy_kind'):
        return WebSearchProfilePolicy(
            profile=str(search_profile or web_search_profile.PROFILE_GENERAL),
            mode=str(data.get('profile_policy_mode') or ''),
            expected_domains=tuple(str(value) for value in _sequence(data.get('profile_expected_domains')) if str(value)),
            secondary_domains=tuple(str(value) for value in _sequence(data.get('profile_secondary_domains')) if str(value)),
            downrank_domains=tuple(str(value) for value in _sequence(data.get('profile_downrank_domains')) if str(value)),
            situated_secondary_domains=tuple(
                str(value) for value in _sequence(data.get('profile_situated_secondary_domains')) if str(value)
            ),
            crawl_top_n_budget=_to_int(data.get('profile_crawl_top_n_budget')),
            crawl_max_chars_budget=_to_int(data.get('profile_crawl_max_chars_budget')),
            manual_latency_target_s=_to_int(data.get('profile_manual_latency_target_s')),
            reason_codes=tuple(str(value) for value in _sequence(data.get('profile_policy_reason_codes')) if str(value)),
        )
    return build_profile_policy(search_profile)


def _classify_source(source: Mapping[str, Any], policy: WebSearchProfilePolicy) -> str:
    if _matches_any(source, policy.situated_secondary_domains):
        return 'situated'
    if _matches_any(source, policy.expected_domains):
        return 'expected'
    if _matches_any(source, policy.secondary_domains):
        return 'secondary'
    if _matches_any(source, policy.downrank_domains):
        return 'downrank'
    return 'neutral'


def _matches_any(source: Mapping[str, Any], patterns: Sequence[str]) -> bool:
    return any(_source_matches_pattern(source, pattern) for pattern in patterns)


def _source_matches_pattern(source: Mapping[str, Any], pattern: str) -> bool:
    expected = str(pattern or '').strip().lower()
    if not expected:
        return False
    url = str(source.get('url') or '').strip().lower()
    domain = _source_domain(source)
    if '/' in expected and expected in url:
        return True
    expected_domain = expected.split('/', 1)[0]
    if expected_domain == '.gouv.fr':
        return domain == 'gouv.fr' or domain.endswith('.gouv.fr')
    if expected_domain == '.europa.eu':
        return domain == 'europa.eu' or domain.endswith('.europa.eu')
    if expected_domain == '.edu':
        return domain.endswith('.edu')
    if '*' in expected_domain:
        regex = '^' + re.escape(expected_domain).replace('\\*', '[a-z0-9-]+') + '$'
        return bool(re.match(regex, domain))
    return domain == expected_domain or domain.endswith(f'.{expected_domain}')


def _source_domain(source: Mapping[str, Any]) -> str:
    domain = str(source.get('source_domain') or '').strip().lower().removeprefix('www.')
    if domain:
        return domain
    parsed = urlparse(str(source.get('url') or ''))
    return parsed.netloc.lower().removeprefix('www.')


def _source_used(source: Mapping[str, Any]) -> bool:
    return (
        bool(source.get('used_in_prompt', False))
        and str(source.get('used_content_kind') or 'none') != 'none'
        and bool(str(source.get('content_used') or source.get('search_snippet') or '').strip())
    )


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text and text not in output:
            output.append(text)
    return output
