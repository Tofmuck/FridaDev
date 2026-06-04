"""Declarative product methods for the Biblio librarian contract.

Lot B introduces a stable layer above raw GET-only tools:

- product cases belong to the product grammar;
- product methods are the runtime-facing execution contract;
- raw tools stay technical primitives used by those methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import librarian_tools as tools


TRUTH_LEVEL_EXACT = "exact"
TRUTH_LEVEL_PLAUSIBLE = "plausible"
TRUTH_LEVEL_CONTEXTUAL = "contextuel"

CANONICAL_FAMILY_INVENTORY_METADATA = "inventory_metadata"
CANONICAL_FAMILY_DOCUMENT_RESOLUTION = "document_resolution"
CANONICAL_FAMILY_DOCUMENT_STRUCTURE = "document_structure"
CANONICAL_FAMILY_SCOPED_SEARCH = "scoped_search"
CANONICAL_FAMILY_EXTRACTION = "extraction"
CANONICAL_FAMILY_READER_NAVIGATION = "reader_navigation"
CANONICAL_FAMILY_PROVENANCE = "provenance"
CANONICAL_FAMILY_DISAMBIGUATION = "disambiguation"
CANONICAL_FAMILY_ANCHORING_STATE = "anchoring_state"

EXECUTION_STATUS_SUCCESS = "success"
EXECUTION_STATUS_CLARIFICATION = "clarification"
EXECUTION_STATUS_NOT_FOUND = "not_found"
EXECUTION_STATUS_ERROR = "error"

PRODUCT_METHOD_INVENTORY_METADATA = "inventory_metadata"
PRODUCT_METHOD_DOCUMENT_RESOLUTION = "document_resolution"
PRODUCT_METHOD_CATALOG_LIST_FULL = "catalog_list_full"
PRODUCT_METHOD_CATALOG_LIST_BOUNDED = "catalog_list_bounded"
PRODUCT_METHOD_WORK_LOOKUP = "work_lookup"
PRODUCT_METHOD_DOCUMENT_TOC_SHOW = "document_toc_show"
PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE = "passage_extract_canonical_range"
PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE = "passage_set_current_reference"
PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK = "passage_search_in_work"
PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT = "passage_explain_current"
PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT = "passage_show_around_current"
PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES = "passage_compare_candidates"
PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT = "passage_move_previous_segment"
PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT = "passage_continue_next_segment"
PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK = "passage_origin_check"
PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK = "passage_search_external_work"
PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST = "clarify_biblio_request"

CASE_IDS = tuple(f"P{index:02d}" for index in range(1, 19))
CASE_ID_SET = frozenset(CASE_IDS)


@dataclass(frozen=True)
class BiblioProductMethodSpec:
    product_method: str
    canonical_family: str = ""
    case_ids: tuple[str, ...] = ()
    allowed_tool_names: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    truth_levels: tuple[str, ...] = ()
    execution_statuses: tuple[str, ...] = ()
    requires_tool_calls: bool = True


METHOD_SPECS = (
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_INVENTORY_METADATA,
        canonical_family=CANONICAL_FAMILY_INVENTORY_METADATA,
        case_ids=(),
        allowed_tool_names=(
            tools.TOOL_CATALOG_LIST,
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
        ),
        preconditions=("biblio_enabled",),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_DOCUMENT_RESOLUTION,
        canonical_family=CANONICAL_FAMILY_DOCUMENT_RESOLUTION,
        case_ids=(),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
        ),
        preconditions=("biblio_enabled", "document_or_work_signal_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CATALOG_LIST_FULL,
        canonical_family=CANONICAL_FAMILY_INVENTORY_METADATA,
        case_ids=("P01",),
        allowed_tool_names=(tools.TOOL_CATALOG_LIST,),
        preconditions=("biblio_enabled",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CATALOG_LIST_BOUNDED,
        canonical_family=CANONICAL_FAMILY_INVENTORY_METADATA,
        case_ids=("P02",),
        allowed_tool_names=(tools.TOOL_CATALOG_LIST,),
        preconditions=("biblio_enabled",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_WORK_LOOKUP,
        canonical_family=CANONICAL_FAMILY_DOCUMENT_RESOLUTION,
        case_ids=("P03",),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
        ),
        preconditions=("biblio_enabled", "work_signal_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
        canonical_family=CANONICAL_FAMILY_DOCUMENT_STRUCTURE,
        case_ids=("P09",),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_CATALOG_SEARCH,
        ),
        preconditions=("biblio_enabled", "resolved_document_or_unique_match"),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
        canonical_family=CANONICAL_FAMILY_EXTRACTION,
        case_ids=("P04",),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_SEARCH_CHAPTERS,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PAGE_READ,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "canonical_locator_present", "resolved_document_or_unique_match"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        canonical_family=CANONICAL_FAMILY_ANCHORING_STATE,
        case_ids=("P10",),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_SEARCH_CHAPTERS,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PAGE_READ,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("exact_passage_anchor_available",),
        truth_levels=(TRUTH_LEVEL_EXACT,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        canonical_family=CANONICAL_FAMILY_SCOPED_SEARCH,
        case_ids=("P05", "P06", "P07", "P08"),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_SEARCH_CHAPTERS,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PAGE_READ,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "theme_query_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT,
        canonical_family=CANONICAL_FAMILY_READER_NAVIGATION,
        case_ids=("P11",),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT,
        canonical_family=CANONICAL_FAMILY_READER_NAVIGATION,
        case_ids=("P12",),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL,),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES,
        canonical_family=CANONICAL_FAMILY_DISAMBIGUATION,
        case_ids=(),
        allowed_tool_names=(tools.TOOL_PASSAGE_CONTEXT,),
        preconditions=("candidate_context_positions_present",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT,
        canonical_family=CANONICAL_FAMILY_READER_NAVIGATION,
        case_ids=("P13",),
        allowed_tool_names=(tools.TOOL_PAGE_READ, tools.TOOL_PASSAGE_CONTEXT),
        preconditions=("current_document_anchor_present", "navigation_anchor_present"),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT,
        canonical_family=CANONICAL_FAMILY_READER_NAVIGATION,
        case_ids=("P14",),
        allowed_tool_names=(tools.TOOL_PAGE_READ, tools.TOOL_PASSAGE_CONTEXT),
        preconditions=("current_document_anchor_present", "navigation_anchor_present"),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK,
        canonical_family=CANONICAL_FAMILY_PROVENANCE,
        case_ids=("P15",),
        allowed_tool_names=(
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_LOCATE,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("current_passage_anchor_present",),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        canonical_family=CANONICAL_FAMILY_SCOPED_SEARCH,
        case_ids=("P16", "P17", "P18"),
        allowed_tool_names=(
            tools.TOOL_SEARCH_DOCUMENT,
            tools.TOOL_SEARCH_WORK,
            tools.TOOL_SEARCH_SECTION,
            tools.TOOL_RESOLVE_WORK,
            tools.TOOL_RESOLVE_SECTION,
            tools.TOOL_SECTION_BOUNDS,
            tools.TOOL_CATALOG_SEARCH,
            tools.TOOL_SEARCH_CHAPTERS,
            tools.TOOL_DOCUMENT_OPEN_SUMMARY,
            tools.TOOL_DOCUMENT_TOC,
            tools.TOOL_LOCATE,
            tools.TOOL_PAGE_READ,
            tools.TOOL_PASSAGE_CONTEXT,
        ),
        preconditions=("biblio_enabled", "theme_query_present"),
        truth_levels=(TRUTH_LEVEL_EXACT, TRUTH_LEVEL_PLAUSIBLE, TRUTH_LEVEL_CONTEXTUAL),
        execution_statuses=(EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_CLARIFICATION, EXECUTION_STATUS_NOT_FOUND, EXECUTION_STATUS_ERROR),
    ),
    BiblioProductMethodSpec(
        product_method=PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST,
        canonical_family=CANONICAL_FAMILY_DISAMBIGUATION,
        case_ids=(),
        allowed_tool_names=(),
        preconditions=("insufficient_resolution",),
        truth_levels=(TRUTH_LEVEL_CONTEXTUAL,),
        execution_statuses=(EXECUTION_STATUS_CLARIFICATION,),
        requires_tool_calls=False,
    ),
)

METHODS_BY_NAME = {spec.product_method: spec for spec in METHOD_SPECS}

CASE_REFERENCE_SIGNATURES: dict[str, dict[str, Any]] = {
    "P01": {
        "product_method": PRODUCT_METHOD_CATALOG_LIST_FULL,
        "signature": "catalogue complet sans borne demandee",
        "example": "Quels ouvrages as-tu dans la bibliotheque ?",
    },
    "P02": {
        "product_method": PRODUCT_METHOD_CATALOG_LIST_BOUNDED,
        "signature": "catalogue avec borne explicite 100 ou tous si <= 100",
        "example": "Il y a 100 ouvrages ? Liste-les tous.",
    },
    "P03": {
        "product_method": PRODUCT_METHOD_WORK_LOOKUP,
        "signature": "retrouver l'ouvrage ou la cible documentaire",
        "example": "Trouve-moi le Theetete de Platon.",
    },
    "P04": {
        "product_method": PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
        "signature": "extraire une plage canonique explicite",
        "example": "Dans le Theetete de Platon, sors-moi 126b a 128a.",
    },
    "P05": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        "signature": "theme dans une oeuvre, forme canonique accentuee avec ancre thematique directe",
        "example": "Dans le Théétète, trouve le passage où Socrate parle de la maïeutique.",
    },
    "P06": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        "signature": "theme dans une oeuvre, variante sans accents ou translitteree",
        "example": "Dans le Theetete, trouve le passage ou Socrate parle de la maieutique.",
    },
    "P07": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        "signature": "theme dans une oeuvre, voisinage lexical ou metaphore proche",
        "example": "Dans le Theetete, trouve le passage sur la sage-femme.",
    },
    "P08": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        "signature": "theme dans une oeuvre, paraphrase plus libre",
        "example": "Dans le Theetete, trouve le passage sur accoucher les ames.",
    },
    "P09": {
        "product_method": PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
        "signature": "table des matieres de l'ouvrage cible",
        "example": "Montre-moi la table des matieres du Theetete.",
    },
    "P10": {
        "product_method": PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        "signature": "faire du passage exact extrait la reference courante",
        "example": "Dans le Theetete de Platon, sors-moi 126b a 128a.",
    },
    "P11": {
        "product_method": PRODUCT_METHOD_PASSAGE_EXPLAIN_CURRENT,
        "signature": "expliquer le passage courant",
        "example": "Explique ce passage.",
    },
    "P12": {
        "product_method": PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT,
        "signature": "montrer le voisinage du passage courant",
        "example": "Autour de ce passage.",
    },
    "P13": {
        "product_method": PRODUCT_METHOD_PASSAGE_MOVE_PREVIOUS_SEGMENT,
        "signature": "aller plus haut avant le passage courant",
        "example": "Plus haut.",
    },
    "P14": {
        "product_method": PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT,
        "signature": "continuer apres le passage courant",
        "example": "Continue.",
    },
    "P15": {
        "product_method": PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK,
        "signature": "verifier d'ou vient le passage courant",
        "example": "D'ou vient ce passage ?",
    },
    "P16": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        "signature": "theme dans une autre oeuvre, formulation de base",
        "example": "Dans Qu'est-ce que les Lumieres ? de Kant, trouve le passage sur Sapere aude.",
    },
    "P17": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        "signature": "theme dans une autre oeuvre, reformulation conceptuelle voisine",
        "example": "Dans Qu'est-ce que les Lumieres ? de Kant, trouve le passage ou Kant parle de penser par soi-meme.",
    },
    "P18": {
        "product_method": PRODUCT_METHOD_PASSAGE_SEARCH_EXTERNAL_WORK,
        "signature": "theme dans une autre oeuvre, paraphrase ou citation voisine",
        "example": "Dans Qu'est-ce que les Lumieres ? de Kant, trouve le passage sur oser se servir de son propre entendement.",
    },
}


def all_product_method_names() -> tuple[str, ...]:
    return tuple(METHODS_BY_NAME.keys())


def all_canonical_family_names() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            spec.canonical_family
            for spec in METHOD_SPECS
            if spec.canonical_family
        )
    )


def get_product_method_spec(product_method: str) -> BiblioProductMethodSpec | None:
    return METHODS_BY_NAME.get(str(product_method or "").strip())


def canonical_family_for_method(product_method: str) -> str:
    spec = get_product_method_spec(product_method)
    return str(spec.canonical_family or "").strip() if spec else ""


def is_known_product_method(product_method: Any) -> bool:
    return get_product_method_spec(str(product_method or "").strip()) is not None


def normalize_case_id(case_id: Any) -> str:
    return str(case_id or "").strip().upper()


def is_known_case_id(case_id: Any) -> bool:
    text = normalize_case_id(case_id)
    return bool(text) and text in CASE_ID_SET


def method_accepts_case_id(product_method: str, case_id: str) -> bool:
    spec = get_product_method_spec(product_method)
    if spec is None:
        return False
    case = normalize_case_id(case_id)
    if not case:
        return True
    return case in spec.case_ids


def method_allows_tool(product_method: str, tool_name: str) -> bool:
    spec = get_product_method_spec(product_method)
    if spec is None:
        return False
    return str(tool_name or "").strip() in set(spec.allowed_tool_names)


def method_requires_tool_calls(product_method: str) -> bool:
    spec = get_product_method_spec(product_method)
    return bool(spec and spec.requires_tool_calls)


def default_case_id_for_method(product_method: str) -> str:
    spec = get_product_method_spec(product_method)
    if spec is None or len(spec.case_ids) != 1:
        return ""
    return spec.case_ids[0]


def case_reference_signatures() -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for case_id in CASE_IDS:
        payload = CASE_REFERENCE_SIGNATURES.get(case_id, {})
        rows.append(
            {
                "case_id": case_id,
                "product_method": str(payload.get("product_method") or ""),
                "signature": str(payload.get("signature") or ""),
                "example": str(payload.get("example") or ""),
            }
        )
    return tuple(rows)


def infer_case_id_for_legacy_payload(
    *,
    product_method: Any,
    intent: Any,
    answer_mode: Any,
    tool_names: list[str] | tuple[str, ...],
) -> str:
    """Return a conservative case_id for repaired legacy payloads.

    Lot B guarantees the product_method layer first. During transition, a legacy
    payload may be honest about the method while still being unable to
    discriminate a precise case inside the family. In that situation we keep
    case_id empty instead of guessing.
    """

    _ = (product_method, intent, answer_mode, tool_names)
    return ""


def infer_product_method(*, intent: Any, answer_mode: Any, tool_names: list[str] | tuple[str, ...]) -> str:
    clean_intent = str(intent or "").strip()
    clean_answer_mode = str(answer_mode or "").strip()
    unique_tools = tuple(dict.fromkeys(str(name or "").strip() for name in tool_names if str(name or "").strip()))
    tool_set = set(unique_tools)

    if clean_answer_mode == "clarify" or clean_intent == "clarify" or not unique_tools:
        return PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST
    if clean_intent == CANONICAL_FAMILY_INVENTORY_METADATA:
        return PRODUCT_METHOD_INVENTORY_METADATA
    if clean_intent == CANONICAL_FAMILY_DOCUMENT_RESOLUTION:
        return PRODUCT_METHOD_DOCUMENT_RESOLUTION
    if clean_intent == "list_catalog":
        return PRODUCT_METHOD_CATALOG_LIST_BOUNDED
    if clean_intent == "show_table_of_contents":
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if clean_intent == "resolve_work":
        return PRODUCT_METHOD_DOCUMENT_RESOLUTION
    if tools.TOOL_RESOLVE_WORK in tool_set or tools.TOOL_SEARCH_WORK in tool_set or tools.TOOL_SEARCH_DOCUMENT in tool_set:
        return PRODUCT_METHOD_DOCUMENT_RESOLUTION
    if clean_intent == "compare_passages":
        return PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES
    if (
        clean_intent in {"extract_passage", "extract_range", "document_locator"}
        or tools.TOOL_LOCATE in tool_set
        or tools.TOOL_RESOLVE_SECTION in tool_set
        or tools.TOOL_SECTION_BOUNDS in tool_set
    ):
        return PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE
    if clean_intent == "search_catalog":
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    if clean_answer_mode == "catalog_list":
        return PRODUCT_METHOD_INVENTORY_METADATA
    if clean_answer_mode == "toc":
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if clean_answer_mode in {"passage", "conceptual_search"}:
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    if tools.TOOL_DOCUMENT_TOC in tool_set:
        return PRODUCT_METHOD_DOCUMENT_TOC_SHOW
    if tools.TOOL_CATALOG_LIST in tool_set:
        return PRODUCT_METHOD_CATALOG_LIST_BOUNDED
    if tools.TOOL_SEARCH_SECTION in tool_set:
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    if tools.TOOL_PASSAGE_CONTEXT in tool_set or tools.TOOL_CATALOG_SEARCH in tool_set:
        return PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK
    return ""
