from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Mapping

from tools import web_search_profile


SOURCE_FIRST_POLICY_KIND = 'source_first_authority_map_v0'
SOURCE_FIRST_DISABLED_POLICY_KIND = 'none'

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]*")
_GENERIC_TERMS = {
    'api',
    'apis',
    'centre',
    'checkout',
    'compose',
    'documentation',
    'docs',
    'doc',
    'fetch',
    'guide',
    'help',
    'manuel',
    'official',
    'officiel',
    'officielle',
    'reference',
    'references',
    'search',
    'support',
    'web',
}


@dataclass(frozen=True)
class SourceFirstPlan:
    policy_kind: str
    active: bool
    authority: str = ''
    product: str = ''
    probable_domains: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    authority_terms: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'source_first_policy_kind': self.policy_kind,
            'source_first_active': self.active,
            'source_first_authority': self.authority,
            'source_first_product': self.product,
            'source_first_probable_domains': list(self.probable_domains),
            'source_first_reason_codes': list(self.reason_codes),
            'source_first_authority_terms': list(self.authority_terms),
        }

    def as_observability_fields(self) -> dict[str, Any]:
        return {
            'source_first_policy_kind': self.policy_kind,
            'source_first_active': self.active,
            'source_first_authority': self.authority,
            'source_first_product': self.product,
            'source_first_probable_domains': list(self.probable_domains),
            'source_first_reason_codes': list(self.reason_codes),
        }


@dataclass(frozen=True)
class _AuthorityRule:
    authority: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    product_rules: tuple[tuple[str, tuple[str, ...]], ...] = ()


_AUTHORITY_RULES = (
    _AuthorityRule(
        authority='Adobe',
        aliases=('adobe',),
        domains=('helpx.adobe.com', 'developer.adobe.com', 'adobe.com'),
        product_rules=(
            ('Photoshop', ('photoshop',)),
            ('Illustrator', ('illustrator',)),
        ),
    ),
    _AuthorityRule(
        authority='Microsoft',
        aliases=('microsoft',),
        domains=('learn.microsoft.com',),
        product_rules=(('Graph API', ('graph api', 'microsoft graph', 'graph')),),
    ),
    _AuthorityRule(
        authority='Stripe',
        aliases=('stripe',),
        domains=('docs.stripe.com',),
        product_rules=(('Checkout', ('checkout', 'stripe checkout')),),
    ),
    _AuthorityRule(
        authority='OpenRouter',
        aliases=('openrouter',),
        domains=('openrouter.ai/docs', 'docs.openrouter.ai', 'openrouter.ai'),
        product_rules=(('web search', ('web_search', 'web search', 'openrouter web_search')),),
    ),
    _AuthorityRule(
        authority='MDN / Mozilla',
        aliases=('mdn', 'mozilla'),
        domains=('developer.mozilla.org',),
        product_rules=(('fetch API', ('fetch api', 'fetch')),),
    ),
    _AuthorityRule(
        authority='Docker',
        aliases=('docker',),
        domains=('docs.docker.com',),
        product_rules=(('Compose', ('docker compose', 'compose')),),
    ),
)


def empty_plan() -> SourceFirstPlan:
    return SourceFirstPlan(
        policy_kind=SOURCE_FIRST_DISABLED_POLICY_KIND,
        active=False,
        reason_codes=('not_applicable',),
    )


def empty_observability_fields() -> dict[str, Any]:
    return empty_plan().as_observability_fields()


def build_source_first_plan(
    user_msg: str,
    primary_query: str = '',
    search_profile: str = '',
) -> SourceFirstPlan:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    if profile != web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE:
        return empty_plan()

    combined = f'{user_msg} {primary_query}'
    normalized = _normalize_text(combined)
    if not _looks_like_documentation_request(normalized):
        return SourceFirstPlan(
            policy_kind=SOURCE_FIRST_POLICY_KIND,
            active=False,
            reason_codes=('documentation_request_not_detected',),
        )

    for rule in _AUTHORITY_RULES:
        if not any(alias in normalized for alias in rule.aliases):
            continue
        product = _product_for_rule(rule, normalized)
        terms = _authority_terms(rule.authority, product)
        return SourceFirstPlan(
            policy_kind=SOURCE_FIRST_POLICY_KIND,
            active=True,
            authority=rule.authority,
            product=product,
            probable_domains=rule.domains,
            reason_codes=('authority_catalog_match', 'documentation_request_detected'),
            authority_terms=terms,
        )

    authority, product = _extract_generic_authority_and_product(combined)
    if not authority:
        return SourceFirstPlan(
            policy_kind=SOURCE_FIRST_POLICY_KIND,
            active=False,
            reason_codes=('generic_documentation_request_without_authority',),
        )

    return SourceFirstPlan(
        policy_kind=SOURCE_FIRST_POLICY_KIND,
        active=True,
        authority=authority,
        product=product,
        probable_domains=(),
        reason_codes=('authority_extracted_without_domain_map', 'documentation_request_detected'),
        authority_terms=_authority_terms(authority, product),
    )


def plan_from_mapping(value: Mapping[str, Any] | None) -> SourceFirstPlan:
    data = value if isinstance(value, Mapping) else {}
    return SourceFirstPlan(
        policy_kind=str(data.get('source_first_policy_kind') or SOURCE_FIRST_DISABLED_POLICY_KIND),
        active=bool(data.get('source_first_active', False)),
        authority=str(data.get('source_first_authority') or ''),
        product=str(data.get('source_first_product') or ''),
        probable_domains=tuple(str(item) for item in data.get('source_first_probable_domains') or [] if str(item)),
        reason_codes=tuple(str(item) for item in data.get('source_first_reason_codes') or [] if str(item)),
        authority_terms=tuple(str(item) for item in data.get('source_first_authority_terms') or [] if str(item)),
    )


def _looks_like_documentation_request(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            'api reference',
            'centre aide officiel',
            'documentation',
            'docs',
            'guide officiel',
            'help center officiel',
            'manuel officiel',
            'official documentation',
            'official docs',
            'support officiel',
        )
    )


def _product_for_rule(rule: _AuthorityRule, normalized: str) -> str:
    for product, aliases in rule.product_rules:
        if any(alias in normalized for alias in aliases):
            return product
    return ''


def _extract_generic_authority_and_product(value: str) -> tuple[str, str]:
    words = [word.strip('.,;:!?()[]{}') for word in _WORD_RE.findall(str(value or ''))]
    candidates: list[str] = []
    seen: set[str] = set()
    for word in words:
        normalized = _normalize_text(word)
        if normalized in _GENERIC_TERMS or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(word)
    if not candidates:
        return '', ''
    authority = candidates[0]
    product_terms: list[str] = []
    for word in candidates[1:4]:
        normalized = _normalize_text(word)
        if normalized in _GENERIC_TERMS:
            continue
        product_terms.append(word.replace('_', ' '))
    return authority, ' '.join(product_terms).strip()


def _authority_terms(authority: str, product: str) -> tuple[str, ...]:
    terms: list[str] = []
    for value in (authority, product):
        for token in re.findall(r'[a-z0-9]{3,}', _normalize_text(value)):
            if token not in _GENERIC_TERMS and token not in terms:
                terms.append(token)
    return tuple(terms)


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize('NFKD', str(value or ''))
    ascii_text = ''.join(char for char in text if not unicodedata.combining(char))
    ascii_text = ascii_text.lower().replace("'", ' ')
    return re.sub(r'\s+', ' ', ascii_text).strip()
