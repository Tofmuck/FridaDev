from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit


PRODUCT_PHOTOSHOP = 'photoshop'
PRODUCT_ILLUSTRATOR = 'illustrator'
VALID_PRODUCTS = (PRODUCT_PHOTOSHOP, PRODUCT_ILLUSTRATOR)

SOURCE_TYPE_HUB = 'hub'
SOURCE_TYPE_RELEASE_NOTES = 'release_notes'
SOURCE_TYPE_KNOWN_ISSUES = 'known_issues'
SOURCE_TYPE_HELP_PAGE = 'help_page'
VALID_SOURCE_TYPES = (
    SOURCE_TYPE_HUB,
    SOURCE_TYPE_RELEASE_NOTES,
    SOURCE_TYPE_KNOWN_ISSUES,
    SOURCE_TYPE_HELP_PAGE,
)

HELPX_HOST = 'helpx.adobe.com'
LANGUAGE_POLICY = 'prefer_fr_then_en_with_caveat'

REASON_ACCEPTED = 'accepted'
REASON_INVALID_PRODUCT = 'invalid_product'
REASON_INVALID_URL = 'invalid_url'
REASON_INVALID_SCHEME = 'invalid_scheme'
REASON_COMMUNITY_FORBIDDEN = 'community_forbidden'
REASON_LEARN_FORBIDDEN = 'learn_forbidden'
REASON_MARKETING_FORBIDDEN = 'marketing_forbidden'
REASON_ACCOUNT_FORBIDDEN = 'account_forbidden'
REASON_HOST_NOT_HELPX = 'host_not_helpx'
REASON_EXCLUDED_EXTENSION = 'excluded_extension'
REASON_EXCLUDED_ARCHIVE_PATH = 'excluded_archive_path'
REASON_WRONG_PRODUCT = 'wrong_product'
REASON_PRODUCT_PATH_MISSING = 'product_path_missing'
REASON_FRAGMENT_REMOVED = 'fragment_removed'
REASON_QUERY_REMOVED = 'query_removed'
REASON_DUPLICATE_CANONICAL_URL = 'duplicate_canonical_url'

_IMAGE_EXTENSIONS = (
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.webp',
    '.svg',
    '.avif',
    '.bmp',
    '.ico',
)
_VIDEO_EXTENSIONS = (
    '.mp4',
    '.mov',
    '.m4v',
    '.webm',
    '.avi',
    '.mkv',
)
_DOCUMENT_EXTENSIONS = (
    '.pdf',
    '.doc',
    '.docx',
    '.ppt',
    '.pptx',
    '.xls',
    '.xlsx',
)
_ARCHIVE_EXTENSIONS = (
    '.zip',
    '.tar',
    '.gz',
    '.tgz',
    '.rar',
    '.7z',
)
_EXCLUDED_EXTENSIONS = _IMAGE_EXTENSIONS + _VIDEO_EXTENSIONS + _DOCUMENT_EXTENSIONS + _ARCHIVE_EXTENSIONS


@dataclass(frozen=True)
class AdobeDocsSource:
    product: str
    source_type: str
    url: str
    title: str
    language_policy: str = LANGUAGE_POLICY

    def as_dict(self) -> dict[str, str]:
        return {
            'product': self.product,
            'source_type': self.source_type,
            'url': self.url,
            'title': self.title,
            'language_policy': self.language_policy,
        }


@dataclass(frozen=True)
class AdobeUrlValidation:
    ok: bool
    url: str
    product: str
    canonical_url: str = ''
    source_type: str = ''
    reason_code: str = ''
    reason_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            'ok': self.ok,
            'url': self.url,
            'product': self.product,
            'canonical_url': self.canonical_url,
            'source_type': self.source_type,
            'reason_code': self.reason_code,
            'reason_codes': list(self.reason_codes),
        }


_SOURCES_BY_PRODUCT = {
    PRODUCT_PHOTOSHOP: (
        AdobeDocsSource(
            product=PRODUCT_PHOTOSHOP,
            source_type=SOURCE_TYPE_HUB,
            url='https://helpx.adobe.com/photoshop/desktop.html',
            title='Photoshop desktop hub',
        ),
        AdobeDocsSource(
            product=PRODUCT_PHOTOSHOP,
            source_type=SOURCE_TYPE_RELEASE_NOTES,
            url='https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html',
            title='Photoshop desktop release notes',
        ),
        AdobeDocsSource(
            product=PRODUCT_PHOTOSHOP,
            source_type=SOURCE_TYPE_KNOWN_ISSUES,
            url='https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html',
            title='Photoshop known and fixed issues',
        ),
    ),
    PRODUCT_ILLUSTRATOR: (
        AdobeDocsSource(
            product=PRODUCT_ILLUSTRATOR,
            source_type=SOURCE_TYPE_HUB,
            url='https://helpx.adobe.com/illustrator/desktop.html',
            title='Illustrator desktop hub',
        ),
        AdobeDocsSource(
            product=PRODUCT_ILLUSTRATOR,
            source_type=SOURCE_TYPE_RELEASE_NOTES,
            url='https://helpx.adobe.com/illustrator/desktop/new-features/release-notes.html',
            title='Illustrator desktop release notes',
        ),
        AdobeDocsSource(
            product=PRODUCT_ILLUSTRATOR,
            source_type=SOURCE_TYPE_KNOWN_ISSUES,
            url='https://helpx.adobe.com/illustrator/desktop/troubleshoot/known-and-fixed-issues.html',
            title='Illustrator known and fixed issues',
        ),
    ),
}


def validate_product(product: str) -> str:
    normalized = str(product or '').strip().lower()
    if normalized not in VALID_PRODUCTS:
        raise ValueError(REASON_INVALID_PRODUCT)
    return normalized


def sources_for_product(product: str) -> tuple[AdobeDocsSource, ...]:
    normalized = validate_product(product)
    return _SOURCES_BY_PRODUCT[normalized]


def source_type_for_url(canonical_url: str, product: str) -> str:
    normalized = validate_product(product)
    for source in sources_for_product(normalized):
        if canonical_url == source.url:
            return source.source_type

    path = urlsplit(canonical_url).path.lower()
    if 'known-and-fixed-issues' in path:
        return SOURCE_TYPE_KNOWN_ISSUES
    if 'release-notes' in path or '/whats-new/' in path or '/new-features/' in path:
        return SOURCE_TYPE_RELEASE_NOTES
    if path.rstrip('/').endswith(f'/{normalized}/desktop.html'):
        return SOURCE_TYPE_HUB
    return SOURCE_TYPE_HELP_PAGE


def validate_adobe_url(url: str, product: str) -> AdobeUrlValidation:
    raw_url = str(url or '').strip()
    try:
        normalized_product = validate_product(product)
    except ValueError:
        return _invalid(raw_url, str(product or ''), REASON_INVALID_PRODUCT)

    parsed = urlsplit(raw_url)
    if not raw_url or not parsed.scheme or not parsed.netloc:
        return _invalid(raw_url, normalized_product, REASON_INVALID_URL)

    scheme = parsed.scheme.lower()
    host = (parsed.netloc or '').lower().rstrip('.')
    path = parsed.path or '/'
    path_lower = path.lower()
    reason_codes: list[str] = []

    if parsed.fragment:
        reason_codes.append(REASON_FRAGMENT_REMOVED)
    if parsed.query:
        reason_codes.append(REASON_QUERY_REMOVED)

    canonical_url = urlunsplit((scheme, host, path, '', ''))

    if scheme != 'https':
        return _invalid(raw_url, normalized_product, REASON_INVALID_SCHEME, canonical_url, reason_codes)
    if host == 'community.adobe.com':
        return _invalid(raw_url, normalized_product, REASON_COMMUNITY_FORBIDDEN, canonical_url, reason_codes)
    if _is_learn_url(host, path_lower):
        return _invalid(raw_url, normalized_product, REASON_LEARN_FORBIDDEN, canonical_url, reason_codes)
    if _is_account_url(host, path_lower):
        return _invalid(raw_url, normalized_product, REASON_ACCOUNT_FORBIDDEN, canonical_url, reason_codes)
    if _is_marketing_url(host):
        return _invalid(raw_url, normalized_product, REASON_MARKETING_FORBIDDEN, canonical_url, reason_codes)
    if host != HELPX_HOST:
        return _invalid(raw_url, normalized_product, REASON_HOST_NOT_HELPX, canonical_url, reason_codes)
    if _has_excluded_extension(path_lower):
        return _invalid(raw_url, normalized_product, REASON_EXCLUDED_EXTENSION, canonical_url, reason_codes)
    if _is_archive_path(path_lower):
        return _invalid(raw_url, normalized_product, REASON_EXCLUDED_ARCHIVE_PATH, canonical_url, reason_codes)

    other_product = PRODUCT_ILLUSTRATOR if normalized_product == PRODUCT_PHOTOSHOP else PRODUCT_PHOTOSHOP
    if f'/{other_product}/' in path_lower:
        return _invalid(raw_url, normalized_product, REASON_WRONG_PRODUCT, canonical_url, reason_codes)
    if f'/{normalized_product}/' not in path_lower:
        return _invalid(raw_url, normalized_product, REASON_PRODUCT_PATH_MISSING, canonical_url, reason_codes)

    reason_codes.append(REASON_ACCEPTED)
    return AdobeUrlValidation(
        ok=True,
        url=raw_url,
        product=normalized_product,
        canonical_url=canonical_url,
        source_type=source_type_for_url(canonical_url, normalized_product),
        reason_code='',
        reason_codes=tuple(reason_codes),
    )


def dedupe_valid_adobe_urls(urls: Iterable[str], product: str) -> tuple[AdobeUrlValidation, ...]:
    seen: set[str] = set()
    deduped: list[AdobeUrlValidation] = []
    for url in urls:
        validation = validate_adobe_url(url, product)
        if not validation.ok or validation.canonical_url in seen:
            continue
        seen.add(validation.canonical_url)
        deduped.append(validation)
    return tuple(deduped)


def _invalid(
    url: str,
    product: str,
    reason_code: str,
    canonical_url: str = '',
    prior_reason_codes: Iterable[str] = (),
) -> AdobeUrlValidation:
    reason_codes = _dedupe_codes((*prior_reason_codes, reason_code))
    return AdobeUrlValidation(
        ok=False,
        url=url,
        product=product,
        canonical_url=canonical_url,
        reason_code=reason_code,
        reason_codes=reason_codes,
    )


def _dedupe_codes(codes: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        normalized = str(code or '').strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def _is_learn_url(host: str, path_lower: str) -> bool:
    if host not in {'adobe.com', 'www.adobe.com'}:
        return False
    parts = [part for part in path_lower.split('/') if part]
    return 'learn' in parts


def _is_marketing_url(host: str) -> bool:
    return host in {'adobe.com', 'www.adobe.com'}


def _is_account_url(host: str, path_lower: str) -> bool:
    if host in {'account.adobe.com', 'accounts.adobe.com', 'auth.services.adobe.com'}:
        return True
    parts = [part for part in path_lower.split('/') if part]
    return any(part in {'account', 'accounts'} for part in parts)


def _has_excluded_extension(path_lower: str) -> bool:
    return any(path_lower.endswith(extension) for extension in _EXCLUDED_EXTENSIONS)


def _is_archive_path(path_lower: str) -> bool:
    parts = [part for part in path_lower.split('/') if part]
    return 'archive' in parts or 'archives' in parts
