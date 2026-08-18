from __future__ import annotations

from dataclasses import dataclass
import json
from types import SimpleNamespace
from typing import Any

from biblio import answer_object
from biblio import catalogue_client as catalogue
from biblio import librarian_agent_contract as agent_contract
from biblio import librarian_agent_first
from biblio import librarian_planner
from biblio import librarian_product_methods as product_methods
from biblio import librarian_tools


RAW_QUERY = "SYNTHETIC-BIBLIO-QUERY-CONTENT"
RAW_TITLE = "SYNTHETIC-BIBLIO-TITLE-CONTENT"
RAW_CHAPTER = "SYNTHETIC-BIBLIO-CHAPTER-CONTENT"
RAW_PASSAGE = "SYNTHETIC-BIBLIO-PASSAGE-CONTENT"
RAW_SENTINELS = (RAW_QUERY, RAW_TITLE, RAW_CHAPTER, RAW_PASSAGE)


@dataclass(frozen=True)
class MethodGoldenCase:
    name: str
    product_method: str
    case_id: str
    expected_tool_names: tuple[str, ...]
    expected_endpoint_kinds: tuple[str, ...]


METHOD_CASES = (
    MethodGoldenCase(
        name="work_lookup",
        product_method=product_methods.PRODUCT_METHOD_WORK_LOOKUP,
        case_id="P03",
        expected_tool_names=(
            librarian_tools.TOOL_CATALOG_SEARCH,
            librarian_tools.TOOL_DOCUMENT_OPEN_SUMMARY,
        ),
        expected_endpoint_kinds=(catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_METADATA),
    ),
    MethodGoldenCase(
        name="document_toc",
        product_method=product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
        case_id="P09",
        expected_tool_names=(
            librarian_tools.TOOL_CATALOG_SEARCH,
            librarian_tools.TOOL_DOCUMENT_TOC,
        ),
        expected_endpoint_kinds=(catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CHAPTERS),
    ),
    MethodGoldenCase(
        name="passage_search",
        product_method=product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        case_id="P05",
        expected_tool_names=(
            librarian_tools.TOOL_CATALOG_SEARCH,
            librarian_tools.TOOL_PASSAGE_CONTEXT,
        ),
        expected_endpoint_kinds=(catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT),
    ),
)


class FakeBiblioCatalogueClient:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def catalog(self, q: str = "", *, limit: int = 20, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return _response(
            catalogue.ENDPOINT_CATALOG,
            {"total": 1, "items": [{"id": "doc-golden", "title": RAW_TITLE}]},
            result_count=1,
        )

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        return _response(
            catalogue.ENDPOINT_SEARCH,
            {
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-golden",
                        "title": RAW_TITLE,
                        "text": RAW_PASSAGE,
                        "page_no": 12,
                        "para_no": 3,
                        "paragraph_id": 99,
                    }
                ],
            },
            result_count=1,
        )

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata", doc_id))
        return _response(
            catalogue.ENDPOINT_METADATA,
            {"document_id": doc_id, "title": RAW_TITLE, "source_type": "pdf"},
            result_count=1,
            doc_id=doc_id,
        )

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return _response(
            catalogue.ENDPOINT_CHAPTERS,
            {
                "document_id": doc_id,
                "total": 1,
                "chapters": [{"chapter_no": 1, "title": RAW_CHAPTER, "unit_no": 7}],
            },
            result_count=1,
            doc_id=doc_id,
        )

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(
            ("context", doc_id, paragraph_id, page_no, para_no, char_offset, window_chars)
        )
        return _response(
            catalogue.ENDPOINT_CONTEXT,
            {"document_id": doc_id, "text": RAW_PASSAGE},
            result_count=1,
            doc_id=doc_id,
            content_chars=len(RAW_PASSAGE),
        )


def exercise_method_case(case: MethodGoldenCase) -> dict[str, Any]:
    client = FakeBiblioCatalogueClient()
    plan = librarian_planner.BiblioLibrarianPlan(
        schema_version=librarian_planner.SCHEMA_VERSION,
        case_id=case.case_id,
        intent="golden_method_matrix",
        product_method=case.product_method,
        tool_calls=(
            librarian_planner.BiblioLibrarianToolCall(
                tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                method="GET",
                params={"query": RAW_QUERY, "limit": 5},
            ),
        ),
        answer_mode="tool",
    )
    comparison = SimpleNamespace(
        settings=agent_contract.BiblioLibrarianAgentSettings(mode=agent_contract.MODE_ACTIVE),
        agent_result=SimpleNamespace(candidate_plan=plan),
    )
    result = librarian_agent_first.run_agent_first_plan(
        comparison=comparison,
        client=client,
        deterministic_plan=SimpleNamespace(intent="golden_method_matrix"),
    )
    if result is None or result.loop_result is None:
        raise AssertionError("Biblio method golden did not traverse the agent-first runtime")
    if result.answer_object is None or result.rendered_answer is None:
        raise AssertionError("Biblio method golden did not build an answer and rendering")
    lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
    loop_observation = result.loop_result.to_observability()
    observation = {
        "case_id": case.case_id,
        "product_method": case.product_method,
        "status": result.status,
        "reason_code": result.reason_code,
        "tool_names": tuple(loop_observation.get("tool_names", ())),
        "endpoint_kinds": tuple(loop_observation.get("endpoint_kinds", ())),
        "answer": result.answer_object.to_observability(),
        "rendered": result.rendered_answer.to_observability(),
        "final_lock": lock.to_observability(),
        "client_call_kinds": tuple(call[0] for call in client.calls),
    }
    return {
        "case": case,
        "client": client,
        "result": result,
        "observation": observation,
    }


def assert_content_free(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    leaked = [marker for marker in RAW_SENTINELS if marker in encoded]
    if leaked:
        raise AssertionError(f"raw Biblio sentinel leaked: {leaked}")


def _response(
    endpoint_kind: str,
    payload: dict[str, Any],
    *,
    result_count: int,
    doc_id: str = "",
    content_chars: int = 0,
) -> catalogue.CatalogueResponse:
    return catalogue.CatalogueResponse(
        endpoint_kind=endpoint_kind,
        status_code=200,
        payload=payload,
        duration_ms=1,
        result_count=result_count,
        doc_id_short=catalogue.short_doc_id(doc_id),
        content_chars=content_chars,
    )
