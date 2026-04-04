from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"

_GESTURE_ORDER = (
    "exposition",
    "interrogation",
    "orientation",
    "positionnement",
    "regulation",
    "adresse_relationnelle",
)
_SIGNAL_FAMILY_ORDER = (
    "referent",
    "visee",
    "critere",
    "portee",
    "ancrage_de_source",
    "coherence",
)
_PROOF_TYPE_ORDER = (
    "factuelle",
    "scientifique",
    "argumentative",
    "hermeneutique",
    "dialogique",
)
_PROVENANCE_ORDER = (
    "dialogue_trace",
    "dialogue_resume",
    "web",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _normalize_text(raw: Any) -> str:
    text = unicodedata.normalize("NFKD", str(raw or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("'", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9?]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_any(text: str, fragments: Sequence[str]) -> bool:
    normalized_text = _normalize_text(text)
    compact_text = normalized_text.replace(" ", "").replace("?", "")
    tokens = {token for token in normalized_text.split() if token}
    for fragment in fragments:
        normalized_fragment = _normalize_text(fragment)
        if not normalized_fragment:
            continue
        if " " in normalized_fragment:
            if normalized_fragment in normalized_text:
                return True
            compact_fragment = normalized_fragment.replace(" ", "").replace("?", "")
            if compact_fragment and compact_fragment in compact_text:
                return True
            continue
        if normalized_fragment in tokens:
            return True
        if len(normalized_fragment) >= 5 and any(token.startswith(normalized_fragment) for token in tokens):
            return True
    return False


def _ordered_unique(values: Sequence[str], order: Sequence[str]) -> list[str]:
    seen = {str(value) for value in values if str(value)}
    return [candidate for candidate in order if candidate in seen]


def _recent_window_messages(recent_window_input_payload: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    payload = _mapping(recent_window_input_payload)
    turns = _sequence(payload.get("turns"))
    messages: list[Mapping[str, Any]] = []
    for turn in turns:
        turn_mapping = _mapping(turn)
        for message in _sequence(turn_mapping.get("messages")):
            message_mapping = _mapping(message)
            if message_mapping:
                messages.append(message_mapping)
    return messages


def _has_resolutive_prior_context(
    *,
    recent_window_input_payload: Mapping[str, Any] | None,
    user_message: str,
) -> bool:
    messages = _recent_window_messages(recent_window_input_payload)
    normalized_user_message = _normalize_text(user_message)
    if messages:
        last_message = _mapping(messages[-1])
        if (
            str(last_message.get("role") or "") == "user"
            and _normalize_text(last_message.get("content")) == normalized_user_message
        ):
            messages = messages[:-1]
    if not messages:
        return False

    contextual_terms = (
        "patch",
        "diff",
        "texte",
        "message",
        "reponse",
        "version",
        "plan",
        "bloc",
        "paragraphe",
        "phrase",
        "section",
        "ligne",
        "code",
        "fichier",
        "contenu",
        "precedent",
        "precedente",
    )
    for message in reversed(messages):
        normalized_content = _normalize_text(_mapping(message).get("content"))
        if not normalized_content:
            continue
        if _contains_any(normalized_content, contextual_terms):
            return True
        return False
    return False


def _is_address_relationnelle(text: str) -> bool:
    relation_terms = ("bonjour", "salut", "merci", "desole", "excuse", "pardon", "bonne nuit", "bonne journee")
    if not _contains_any(text, relation_terms):
        return False
    action_terms = (
        "?",
        "peux tu",
        "pourrais tu",
        "fais",
        "corrige",
        "resume",
        "propose",
        "reponds",
    )
    return not _contains_any(text, action_terms)


def _is_regulation(text: str) -> bool:
    return _contains_any(
        text,
        (
            "arrete",
            "stop",
            "reformule",
            "reprends",
            "recadre",
            "change de methode",
            "change la methode",
            "ralentis",
            "plus lentement",
            "corrige le stt",
            "corrige la transcription",
            "recommence",
        ),
    )


def _is_positionnement(text: str) -> bool:
    return _contains_any(
        text,
        (
            "je prefere",
            "je choisis",
            "je valide",
            "je refuse",
            "je ne suis pas daccord",
            "je suis pas daccord",
            "tu as raison",
            "cest faux",
            "pas ca",
            "non,",
            "non ",
            "daccord",
        ),
    )


def _is_orientation(text: str) -> bool:
    return _contains_any(
        text,
        (
            "peux tu",
            "pourrais tu",
            "merci de",
            "fais",
            "donne",
            "ecris",
            "corrige",
            "resume",
            "propose",
            "reponds",
            "reponds la dessus",
            "reponds la-dessus",
            "cherche",
            "liste",
            "compare",
            "montre",
            "traduis",
        ),
    )


def _is_interrogation(text: str) -> bool:
    return "?" in text or _contains_any(
        text,
        (
            "pourquoi",
            "comment",
            "quel ",
            "quelle ",
            "quels ",
            "quelles ",
            "est ce que",
            "qu est ce",
            "cest quoi",
            "qu est ce que",
        ),
    )


def _resolve_geste_dialogique_dominant(text: str) -> str:
    if _is_address_relationnelle(text):
        return "adresse_relationnelle"
    if _is_regulation(text):
        return "regulation"
    if _is_positionnement(text):
        return "positionnement"
    if _is_orientation(text):
        return "orientation"
    if _is_interrogation(text):
        return "interrogation"
    return "exposition"


def _trace_markers(text: str) -> bool:
    return _contains_any(
        text,
        (
            "on sest dit",
            "tu as dit",
            "je tai dit",
            "j ai dit",
            "plus tot",
            "plus tot",
            "precedent",
            "precedemment",
            "conversation",
        ),
    )


def _summary_markers(text: str) -> bool:
    return _contains_any(text, ("resume", "dans le resume", "selon le resume"))


def _web_markers(text: str) -> bool:
    return _contains_any(
        text,
        (
            "web",
            "internet",
            "site",
            "article",
            "source",
            "sources",
            "reference",
            "references",
            "citation",
            "citations",
            "lien",
            "liens",
        ),
    )


def _resolve_regime_probatoire(text: str) -> dict[str, Any]:
    types: list[str] = []
    provenances: list[str] = []

    if _contains_any(text, ("preuve", "prouve", "verifie", "source", "sources", "reference", "references")):
        types.append("factuelle")
    if _contains_any(text, ("scientifique", "etude", "etudes", "paper", "publication", "publie")):
        types.append("scientifique")
    if _contains_any(
        text,
        (
            "pourquoi",
            "justifie",
            "argumente",
            "quelles raisons",
            "pour quelles raisons",
            "donne les raisons",
        ),
    ):
        types.append("argumentative")
    if _contains_any(text, ("comment comprendre", "que veut dire", "sens", "interpret", "signifie")):
        types.append("hermeneutique")
    if _trace_markers(text) or _summary_markers(text):
        types.append("dialogique")

    if _trace_markers(text):
        provenances.append("dialogue_trace")
    if _summary_markers(text):
        provenances.append("dialogue_resume")
    if _web_markers(text):
        provenances.append("web")

    ordered_types = _ordered_unique(types, _PROOF_TYPE_ORDER)
    ordered_provenances = _ordered_unique(provenances, _PROVENANCE_ORDER)

    return {
        "principe": "maximal_possible",
        "types_de_preuve_attendus": ordered_types,
        "provenances": ordered_provenances,
        "regime_de_vigilance": "renforce" if "web" in ordered_provenances else "standard",
        "composition_probatoire": "appuyee"
        if len(ordered_types) > 1 or len(ordered_provenances) > 1
        else "isolee",
    }


def _resolve_qualification_temporelle(
    *,
    text: str,
    time_input_payload: Mapping[str, Any] | None,
) -> dict[str, str]:
    immediate_markers = _contains_any(text, ("maintenant", "tout de suite", "immediatement", "a linstant"))
    current_markers = _contains_any(text, ("aujourdhui", "actuellement", "en ce moment", "pour le moment"))
    future_markers = _contains_any(text, ("demain", "ensuite", "plus tard", "prochain", "prevoir", "plan", "devra", "fera"))
    summary_markers = _summary_markers(text)
    trace_markers = _trace_markers(text)
    historical_markers = _contains_any(text, ("historiquement", "dans lhistoire", "vient dou", "venait dou")) or bool(
        re.search(r"\b(19|20)\d{2}\b", text)
    )

    if future_markers:
        portee = "prospective"
    elif summary_markers or trace_markers or historical_markers:
        portee = "passee"
    elif immediate_markers:
        portee = "immediate"
    elif current_markers:
        portee = "actuelle"
    else:
        portee = "atemporale"

    anchors: list[str] = []
    if trace_markers:
        anchors.append("dialogue_trace")
    if summary_markers:
        anchors.append("dialogue_resume")
    if historical_markers:
        anchors.append("historique_externe")
    if future_markers:
        anchors.append("projection")
    if immediate_markers or current_markers or (_mapping(time_input_payload) and _contains_any(text, ("ce matin", "cet apres midi", "ce soir"))):
        anchors.append("now")

    unique_anchors = []
    for anchor in anchors:
        if anchor not in unique_anchors:
            unique_anchors.append(anchor)

    if not unique_anchors:
        ancrage = "non_ancre"
    elif len(unique_anchors) == 1:
        ancrage = unique_anchors[0]
    else:
        ancrage = "mixte"

    return {
        "portee_temporelle": portee,
        "ancrage_temporel": ancrage,
    }


def _has_referent_signal(
    *,
    text: str,
    recent_window_input_payload: Mapping[str, Any] | None,
    user_message: str,
) -> bool:
    if not _contains_any(text, ("ca", "cela", "ce point", "la dessus", "la-dessus", "ceci", "lui")):
        return False
    return not _has_resolutive_prior_context(
        recent_window_input_payload=recent_window_input_payload,
        user_message=user_message,
    )


def _has_visee_signal(text: str) -> bool:
    return _contains_any(
        text,
        (
            "reponds la dessus",
            "reponds la-dessus",
            "tu en penses quoi",
            "et donc",
            "reponds",
        ),
    )


def _has_critere_signal(text: str) -> bool:
    has_criterion_word = _contains_any(text, ("meilleur", "mieux", "correct", "propre", "important"))
    has_explicit_basis = _contains_any(text, ("selon", "pour ", "par rapport a"))
    return has_criterion_word and not has_explicit_basis


def _has_portee_signal(text: str) -> bool:
    return _contains_any(
        text,
        (
            "aujourdhui ou",
            "lot entier",
            "on parle de",
            "dans quel perimetre",
            "sur quoi exactement",
        ),
    )


def _has_source_anchor_signal(text: str) -> bool:
    return _contains_any(
        text,
        (
            "sur quoi tu tappuies",
            "sur quoi tu te bases",
            "repo, la memoire ou le web",
            "repo, la memoire ou le web",
            "memoire ou le web",
            "resume ou trace",
            "quelle source",
            "quelles sources",
        ),
    )


def _has_coherence_signal(text: str) -> bool:
    return "mais surtout pas" in text or ("je veux" in text and "mais" in text and "pas" in text)


def _resolve_signal_families(
    *,
    text: str,
    recent_window_input_payload: Mapping[str, Any] | None,
    user_message: str,
) -> list[str]:
    active: list[str] = []
    if _has_referent_signal(
        text=text,
        recent_window_input_payload=recent_window_input_payload,
        user_message=user_message,
    ):
        active.append("referent")
    if _has_visee_signal(text):
        active.append("visee")
    if _has_critere_signal(text):
        active.append("critere")
    if _has_portee_signal(text):
        active.append("portee")
    if _has_source_anchor_signal(text):
        active.append("ancrage_de_source")
    if _has_coherence_signal(text):
        active.append("coherence")
    return _ordered_unique(active, _SIGNAL_FAMILY_ORDER)


def _resolve_user_turn_signals(
    *,
    active_signal_families: Sequence[str],
) -> dict[str, Any]:
    active = [str(value) for value in active_signal_families if str(value)]
    ambiguity_families = {"referent", "coherence"}
    underdetermination_families = {"visee", "critere", "portee", "ancrage_de_source"}
    return {
        "present": True,
        "ambiguity_present": any(family in ambiguity_families for family in active),
        "underdetermination_present": any(family in underdetermination_families for family in active),
        "active_signal_families": active,
        "active_signal_families_count": len(active),
    }


def build_user_turn_input(
    *,
    user_message: str,
    recent_window_input_payload: Mapping[str, Any] | None = None,
    time_input_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_text = _normalize_text(user_message)
    return {
        "schema_version": SCHEMA_VERSION,
        "geste_dialogique_dominant": _resolve_geste_dialogique_dominant(normalized_text),
        "regime_probatoire": _resolve_regime_probatoire(normalized_text),
        "qualification_temporelle": _resolve_qualification_temporelle(
            text=normalized_text,
            time_input_payload=time_input_payload,
        ),
    }


def build_user_turn_signals(
    *,
    user_message: str,
    recent_window_input_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_text = _normalize_text(user_message)
    active_signal_families = _resolve_signal_families(
        text=normalized_text,
        recent_window_input_payload=recent_window_input_payload,
        user_message=str(user_message or ""),
    )
    return _resolve_user_turn_signals(active_signal_families=active_signal_families)


def build_user_turn_bundle(
    *,
    user_message: str,
    recent_window_input_payload: Mapping[str, Any] | None = None,
    time_input_payload: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "user_turn": build_user_turn_input(
            user_message=user_message,
            recent_window_input_payload=recent_window_input_payload,
            time_input_payload=time_input_payload,
        ),
        "user_turn_signals": build_user_turn_signals(
            user_message=user_message,
            recent_window_input_payload=recent_window_input_payload,
        ),
    }
