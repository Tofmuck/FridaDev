from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


PROFILE_EXPLICIT_URL = 'explicit_url'
PROFILE_DOCUMENTATION_OFFICIELLE = 'documentation_officielle'
PROFILE_ACTUALITE = 'actualite'
PROFILE_ADMINISTRATIF_FRANCAIS = 'administratif_francais'
PROFILE_ACADEMIQUE = 'academique'
PROFILE_GENERAL_DIVERS = 'general_divers'

# Backward-compatible symbols for the Lot 2-7 implementation. Their values are
# now the Phase 2 canonical regimes, so runtime observability emits the new
# vocabulary while older call sites keep working.
PROFILE_TECHNIQUE_OFFICIELLE = PROFILE_DOCUMENTATION_OFFICIELLE
PROFILE_INSTITUTIONNEL_FRANCAIS = PROFILE_ADMINISTRATIF_FRANCAIS
PROFILE_ACADEMIQUE_PHILOSOPHIQUE = PROFILE_ACADEMIQUE
PROFILE_GENERAL = PROFILE_GENERAL_DIVERS

SEARCH_PROFILES = {
    PROFILE_EXPLICIT_URL,
    PROFILE_DOCUMENTATION_OFFICIELLE,
    PROFILE_ACTUALITE,
    PROFILE_ADMINISTRATIF_FRANCAIS,
    PROFILE_ACADEMIQUE,
    PROFILE_GENERAL_DIVERS,
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
    'annonce recente',
    'communique recent',
    'decision recente',
    'evolution en cours',
)

_DOCUMENTATION_OBJECT_MARKERS = (
    'api',
    'api reference',
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
    'compose',
    'checkout',
    'fetch api',
    'graph api',
)
_OFFICIAL_DOC_MARKERS = (
    'documentation officielle',
    'docs officielles',
    'doc officielle',
    'official docs',
    'official documentation',
    'dans la documentation',
    'selon la documentation',
    'api reference',
    'guide officiel',
    'help center officiel',
    'centre d aide officiel',
    'manuel officiel',
    'support officiel',
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
    'caf',
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
    'ameli',
    'education nationale',
    'education gouv',
    'eduscol',
    'enseignement superieur',
    'enseignementsup recherche',
    'onisep',
    'rectorat',
    'academie de ',
    'ac ',
    'renouvellement de carte',
    'renouveler ma carte',
)

_ACADEMIC_MARKERS = (
    'academique',
    'universitaire',
    'article scientifique',
    'article academique',
    'revue scientifique',
    'source universitaire',
    'sources universitaires',
    'publication scientifique',
    'doi',
    'hal',
    'arxiv',
    'pubmed',
    'openaire',
    'philosophie',
    'philosophique',
    'sociologie',
    'bourdieu',
    'histoire',
    'sciences exactes',
    'mathematique',
    'physique',
    'crispr',
    'medecine',
    'informatique',
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

_TECHNICAL_QA_MARKERS = (
    'stackoverflow',
    'stack overflow',
    'github issue',
    'github issues',
    'askubuntu',
    'ask ubuntu',
    'superuser',
    'super user',
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


def _contains_documentation_request(text: str) -> bool:
    if _contains_any(text, _TECHNICAL_QA_MARKERS):
        return False
    return _contains_any(text, _OFFICIAL_DOC_MARKERS) or (
        _contains_any(text, ('documentation', 'docs', 'doc ', 'guide', 'reference'))
        and _contains_any(text, _DOCUMENTATION_OBJECT_MARKERS)
    )


def classify_search_profile(user_msg: str, *, explicit_url: str | None = None) -> str:
    if explicit_url or _contains_explicit_url(user_msg):
        return PROFILE_EXPLICIT_URL

    text = _normalize_text(user_msg)
    if not text:
        return PROFILE_GENERAL

    if _contains_any(text, _INSTITUTION_FR_MARKERS):
        return PROFILE_ADMINISTRATIF_FRANCAIS
    if _contains_any(text, _ACTUALITE_MARKERS):
        return PROFILE_ACTUALITE
    if _contains_documentation_request(text):
        return PROFILE_DOCUMENTATION_OFFICIELLE
    if _contains_any(text, _ACADEMIC_MARKERS):
        return PROFILE_ACADEMIQUE
    return PROFILE_GENERAL
