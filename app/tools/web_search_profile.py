from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


PROFILE_EXPLICIT_URL = 'explicit_url'
PROFILE_ACTUALITE = 'actualite'
PROFILE_TECHNIQUE_OFFICIELLE = 'technique_officielle'
PROFILE_INSTITUTIONNEL_FRANCAIS = 'institutionnel_francais'
PROFILE_ACADEMIQUE_PHILOSOPHIQUE = 'academique_philosophique'
PROFILE_GENERAL = 'general'

SEARCH_PROFILES = {
    PROFILE_EXPLICIT_URL,
    PROFILE_ACTUALITE,
    PROFILE_TECHNIQUE_OFFICIELLE,
    PROFILE_INSTITUTIONNEL_FRANCAIS,
    PROFILE_ACADEMIQUE_PHILOSOPHIQUE,
    PROFILE_GENERAL,
}

_EXPLICIT_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_URL_TRAILING_PUNCTUATION = '.,;:!?)]}\'"'

_ACTUALITE_MARKERS = (
    'actualite',
    'actualites',
    'aujourd hui',
    'dernieres infos',
    'dernieres nouvelles',
    'derniere nouvelle',
    'dernier communique',
    'dernieres annonces',
    'changements recents',
    'informations recentes',
    'infos recentes',
    'recentement',
    'nouveautes',
    'news',
)

_TECHNICAL_MARKERS = (
    'api',
    'sdk',
    'librairie',
    'library',
    'framework',
    'outil',
    'package',
    'module',
    'server tool',
    'web_search',
    'web fetch',
    'endpoint',
)
_OFFICIAL_DOC_MARKERS = (
    'documentation officielle',
    'docs officielles',
    'doc officielle',
    'official docs',
    'official documentation',
    'dans la documentation',
    'selon la documentation',
    'docs ',
)

_INSTITUTION_FR_MARKERS = (
    'service public',
    'service-public',
    'gouv fr',
    'gouvernement',
    'ministere',
    'prefecture',
    'ants',
    'legifrance',
    'bulletin officiel',
    'bo ',
    'droit',
    'demarche administrative',
    'procedure administrative',
    'procedure officielle',
    'carte nationale d identite',
    'cni',
    'passeport',
    'cerfa',
    'impots',
    'securite sociale',
    'renouvellement de carte',
    'renouveler ma carte',
)

_ACADEMIC_PHILOSOPHY_MARKERS = (
    'academique',
    'universitaire',
    'article scientifique',
    'article academique',
    'revue scientifique',
    'source universitaire',
    'sources universitaires',
    'philosophie',
    'philosophique',
    'derrida',
    'heidegger',
    'kant',
    'deleuze',
    'foucault',
    'aristote',
    'platon',
    'notion de',
    'concept de',
    'trace chez',
    'jstor',
    'openedition',
    'cairn',
    'persee',
    'stanford encyclopedia',
)


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize('NFKD', str(value or ''))
    ascii_text = ''.join(char for char in text if not unicodedata.combining(char))
    ascii_text = ascii_text.lower().replace("'", ' ')
    return re.sub(r'\s+', ' ', ascii_text).strip()


def _contains_explicit_url(value: str) -> bool:
    for match in _EXPLICIT_URL_RE.finditer(str(value or '')):
        candidate = match.group(0).rstrip(_URL_TRAILING_PUNCTUATION)
        parsed = urlparse(candidate)
        if parsed.scheme in {'http', 'https'} and parsed.netloc:
            return True
    return False


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _contains_official_technical_request(text: str) -> bool:
    return _contains_any(text, _OFFICIAL_DOC_MARKERS) and _contains_any(text, _TECHNICAL_MARKERS)


def classify_search_profile(user_msg: str, *, explicit_url: str | None = None) -> str:
    if explicit_url or _contains_explicit_url(user_msg):
        return PROFILE_EXPLICIT_URL

    text = _normalize_text(user_msg)
    if not text:
        return PROFILE_GENERAL

    if _contains_any(text, _ACTUALITE_MARKERS):
        return PROFILE_ACTUALITE
    if _contains_official_technical_request(text):
        return PROFILE_TECHNIQUE_OFFICIELLE
    if _contains_any(text, _INSTITUTION_FR_MARKERS):
        return PROFILE_INSTITUTIONNEL_FRANCAIS
    if _contains_any(text, _ACADEMIC_PHILOSOPHY_MARKERS):
        return PROFILE_ACADEMIQUE_PHILOSOPHIQUE
    return PROFILE_GENERAL
