"""Read-only client for Frida Catalogue / doc-pipeline.

This module is deliberately isolated from chat, prompt construction, frontend
state and database writes.  It is the Lot 2 foundation for native Biblio: a
small GET-only client with content-free errors and observability helpers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote, urlparse

import requests

try:  # pragma: no cover - fallback only matters in unusual import layouts.
    import config as default_config
except Exception:  # pragma: no cover
    default_config = None  # type: ignore[assignment]


DEFAULT_CATALOGUE_BASE_URL = "http://platform-doc-pipeline-api:8090"
DEFAULT_TIMEOUT_S = 8

ENDPOINT_HEALTH = "health"
ENDPOINT_CATALOG = "catalog"
ENDPOINT_DOCUMENT = "document"
ENDPOINT_METADATA = "metadata"
ENDPOINT_CHAPTERS = "chapters"
ENDPOINT_PAGE = "page"
ENDPOINT_LOCATE = "locate"
ENDPOINT_CONTEXT = "context"
ENDPOINT_SEARCH = "search"

REASON_FORBIDDEN_METHOD = "biblio_catalogue_forbidden_method"
REASON_FORBIDDEN_ROUTE = "biblio_catalogue_forbidden_route"
REASON_INVALID_BASE_URL = "biblio_catalogue_invalid_base_url"
REASON_SERVICE_UNAVAILABLE = "biblio_catalogue_service_unavailable"
REASON_TIMEOUT = "biblio_catalogue_timeout"
REASON_INVALID_JSON = "biblio_catalogue_invalid_json"
REASON_NOT_FOUND = "biblio_catalogue_not_found"
REASON_UNEXPECTED_STATUS = "biblio_catalogue_unexpected_status"
REASON_INVALID_PARAMETER = "biblio_catalogue_invalid_parameter"

CATALOG_LIMIT_MIN = 1
CATALOG_LIMIT_MAX = 500
CATALOG_OFFSET_MIN = 0
CATALOG_OFFSET_MAX = 100_000
CHAPTERS_LIMIT_MIN = 1
CHAPTERS_LIMIT_MAX = 1_000
CHAPTERS_OFFSET_MIN = 0
CHAPTERS_OFFSET_MAX = 100_000
PAGE_NO_MIN = 1
PAGE_NO_MAX = 100_000
LOCATE_LIMIT_MIN = 1
LOCATE_LIMIT_MAX = 1_000
CONTEXT_PAGE_NO_MIN = 1
CONTEXT_PAGE_NO_MAX = 100_000
CONTEXT_PARA_NO_MIN = 1
CONTEXT_PARA_NO_MAX = 100_000
CONTEXT_PARAGRAPH_ID_MIN = 1
CONTEXT_PARAGRAPH_ID_MAX = 2_147_483_647
CONTEXT_CHAR_OFFSET_MIN = 0
CONTEXT_CHAR_OFFSET_MAX = 1_000_000
CONTEXT_WINDOW_CHARS_MIN = 80
CONTEXT_WINDOW_CHARS_MAX = 8_000
SEARCH_LIMIT_MIN = 1
SEARCH_LIMIT_MAX = 100

_ALLOWED_STATIC_GET_PATHS = {
    "/health",
    "/catalog",
    "/search",
}
_FORBIDDEN_MUTATING_PATHS = {
    "/settings",
    "/settings/reset",
    "/progress/recent/clear",
}


@dataclass(frozen=True)
class CatalogueClientConfig:
    base_url: str
    timeout_s: int


@dataclass(frozen=True)
class CatalogueResponse:
    endpoint_kind: str
    status_code: int
    payload: dict[str, Any]
    duration_ms: int
    result_count: int | None = None
    doc_id_short: str = ""
    content_chars: int = 0

    def to_observability(self) -> dict[str, Any]:
        return {
            "endpoint_kind": self.endpoint_kind,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "result_count": self.result_count,
            "doc_id_short": self.doc_id_short,
            "content_chars": self.content_chars,
        }


@dataclass(frozen=True)
class CatalogueEndpointObservation:
    endpoint_kind: str
    status_code: int | None = None
    duration_ms: int = 0
    result_count: int | None = None
    doc_id_short: str = ""
    content_chars: int = 0
    reason_code: str = ""
    error_class: str = ""

    def to_observability(self) -> dict[str, Any]:
        observed: dict[str, Any] = {
            "endpoint_kind": self.endpoint_kind,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "result_count": self.result_count,
            "doc_id_short": self.doc_id_short,
            "content_chars": self.content_chars,
        }
        if self.reason_code:
            observed["reason_code"] = self.reason_code
        if self.error_class:
            observed["error_class"] = self.error_class
        return observed


def observe_catalogue_response(response: CatalogueResponse) -> CatalogueEndpointObservation:
    return CatalogueEndpointObservation(
        endpoint_kind=response.endpoint_kind,
        status_code=response.status_code,
        duration_ms=response.duration_ms,
        result_count=response.result_count,
        doc_id_short=response.doc_id_short,
        content_chars=response.content_chars,
    )


class CatalogueClientError(Exception):
    reason_code = "biblio_catalogue_error"

    def __init__(
        self,
        *,
        endpoint_kind: str = "",
        status_code: int | None = None,
        duration_ms: int = 0,
        doc_id: str = "",
        error_class: str = "",
        detail: str = "",
    ) -> None:
        self.endpoint_kind = endpoint_kind
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.doc_id_short = short_doc_id(doc_id)
        self.error_class = error_class
        self.detail = detail
        super().__init__(self.__str__())

    def __str__(self) -> str:
        parts = [self.reason_code]
        if self.endpoint_kind:
            parts.append(f"endpoint={self.endpoint_kind}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.doc_id_short:
            parts.append(f"doc_id_short={self.doc_id_short}")
        if self.error_class:
            parts.append(f"error_class={self.error_class}")
        if self.detail:
            parts.append(f"detail={self.detail}")
        return " ".join(parts)

    def to_observability(self) -> dict[str, Any]:
        return {
            "endpoint_kind": self.endpoint_kind,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "doc_id_short": self.doc_id_short,
            "reason_code": self.reason_code,
            "error_class": self.error_class,
        }


class CatalogueForbiddenMethod(CatalogueClientError):
    reason_code = REASON_FORBIDDEN_METHOD


class CatalogueForbiddenRoute(CatalogueClientError):
    reason_code = REASON_FORBIDDEN_ROUTE


class CatalogueInvalidBaseUrl(CatalogueClientError):
    reason_code = REASON_INVALID_BASE_URL


class CatalogueServiceUnavailable(CatalogueClientError):
    reason_code = REASON_SERVICE_UNAVAILABLE


class CatalogueTimeout(CatalogueClientError):
    reason_code = REASON_TIMEOUT


class CatalogueInvalidJson(CatalogueClientError):
    reason_code = REASON_INVALID_JSON


class CatalogueNotFound(CatalogueClientError):
    reason_code = REASON_NOT_FOUND


class CatalogueUnexpectedStatus(CatalogueClientError):
    reason_code = REASON_UNEXPECTED_STATUS


class CatalogueInvalidParameter(CatalogueClientError):
    reason_code = REASON_INVALID_PARAMETER


def get_catalogue_client_config(config_module: Any = None) -> CatalogueClientConfig:
    source = config_module if config_module is not None else default_config
    base_url = str(
        getattr(source, "BIBLIO_CATALOGUE_BASE_URL", DEFAULT_CATALOGUE_BASE_URL)
        or DEFAULT_CATALOGUE_BASE_URL
    ).strip()
    timeout_s = _positive_int(
        getattr(source, "BIBLIO_CATALOGUE_TIMEOUT_S", DEFAULT_TIMEOUT_S),
        DEFAULT_TIMEOUT_S,
    )
    return CatalogueClientConfig(base_url=base_url.rstrip("/"), timeout_s=timeout_s)


def short_doc_id(doc_id: str) -> str:
    return str(doc_id or "").strip()[:8]


class CatalogueClient:
    def __init__(
        self,
        *,
        config: CatalogueClientConfig | None = None,
        config_module: Any = None,
        requests_module: Any = requests,
        monotonic: Any = time.monotonic,
    ) -> None:
        self.config = config if config is not None else get_catalogue_client_config(config_module)
        self._requests = requests_module
        self._monotonic = monotonic
        _validate_base_url(self.config.base_url)

    def health(self) -> CatalogueResponse:
        return self._get(ENDPOINT_HEALTH, "/health")

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> CatalogueResponse:
        params: dict[str, Any] = {
            "limit": _bounded_int(
                limit,
                endpoint_kind=ENDPOINT_CATALOG,
                name="limit",
                minimum=CATALOG_LIMIT_MIN,
                maximum=CATALOG_LIMIT_MAX,
            ),
            "offset": _bounded_int(
                offset,
                endpoint_kind=ENDPOINT_CATALOG,
                name="offset",
                minimum=CATALOG_OFFSET_MIN,
                maximum=CATALOG_OFFSET_MAX,
            ),
        }
        if q is not None:
            params["q"] = str(q)
        return self._get(ENDPOINT_CATALOG, "/catalog", params=params)

    def document(self, doc_id: str) -> CatalogueResponse:
        path = f"/doc/{_quote_path_segment(doc_id)}"
        return self._get(ENDPOINT_DOCUMENT, path, doc_id=doc_id)

    def metadata(self, doc_id: str) -> CatalogueResponse:
        path = f"/doc/{_quote_path_segment(doc_id)}/metadata"
        return self._get(ENDPOINT_METADATA, path, doc_id=doc_id)

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> CatalogueResponse:
        path = f"/doc/{_quote_path_segment(doc_id)}/chapters"
        params = {
            "limit": _bounded_int(
                limit,
                endpoint_kind=ENDPOINT_CHAPTERS,
                name="limit",
                minimum=CHAPTERS_LIMIT_MIN,
                maximum=CHAPTERS_LIMIT_MAX,
                doc_id=doc_id,
            ),
            "offset": _bounded_int(
                offset,
                endpoint_kind=ENDPOINT_CHAPTERS,
                name="offset",
                minimum=CHAPTERS_OFFSET_MIN,
                maximum=CHAPTERS_OFFSET_MAX,
                doc_id=doc_id,
            ),
        }
        return self._get(ENDPOINT_CHAPTERS, path, params=params, doc_id=doc_id)

    def page(self, doc_id: str, page_no: int) -> CatalogueResponse:
        safe_page_no = _bounded_int(
            page_no,
            endpoint_kind=ENDPOINT_PAGE,
            name="page_no",
            minimum=PAGE_NO_MIN,
            maximum=PAGE_NO_MAX,
            doc_id=doc_id,
        )
        path = f"/doc/{_quote_path_segment(doc_id)}/page/{safe_page_no}"
        return self._get(ENDPOINT_PAGE, path, doc_id=doc_id)

    def locate(
        self,
        doc_id: str,
        locator: str,
        *,
        kind: str = "stephanus",
        limit: int = 200,
    ) -> CatalogueResponse:
        path = f"/doc/{_quote_path_segment(doc_id)}/locate"
        params = {
            "kind": str(kind),
            "label": str(locator),
            "limit": _bounded_int(
                limit,
                endpoint_kind=ENDPOINT_LOCATE,
                name="limit",
                minimum=LOCATE_LIMIT_MIN,
                maximum=LOCATE_LIMIT_MAX,
                doc_id=doc_id,
            ),
        }
        return self._get(ENDPOINT_LOCATE, path, params=params, doc_id=doc_id)

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> CatalogueResponse:
        path = f"/doc/{_quote_path_segment(doc_id)}/context"
        params: dict[str, Any] = {
            "char_offset": _bounded_int(
                char_offset,
                endpoint_kind=ENDPOINT_CONTEXT,
                name="char_offset",
                minimum=CONTEXT_CHAR_OFFSET_MIN,
                maximum=CONTEXT_CHAR_OFFSET_MAX,
                doc_id=doc_id,
            ),
            "window_chars": _bounded_int(
                window_chars,
                endpoint_kind=ENDPOINT_CONTEXT,
                name="window_chars",
                minimum=CONTEXT_WINDOW_CHARS_MIN,
                maximum=CONTEXT_WINDOW_CHARS_MAX,
                doc_id=doc_id,
            ),
        }
        if paragraph_id is not None:
            params["paragraph_id"] = _bounded_int(
                paragraph_id,
                endpoint_kind=ENDPOINT_CONTEXT,
                name="paragraph_id",
                minimum=CONTEXT_PARAGRAPH_ID_MIN,
                maximum=CONTEXT_PARAGRAPH_ID_MAX,
                doc_id=doc_id,
            )
        else:
            if page_no is None or para_no is None:
                raise CatalogueInvalidParameter(
                    endpoint_kind=ENDPOINT_CONTEXT,
                    doc_id=doc_id,
                    detail="context_locator_required",
                )
            params["page_no"] = _bounded_int(
                page_no,
                endpoint_kind=ENDPOINT_CONTEXT,
                name="page_no",
                minimum=CONTEXT_PAGE_NO_MIN,
                maximum=CONTEXT_PAGE_NO_MAX,
                doc_id=doc_id,
            )
            params["para_no"] = _bounded_int(
                para_no,
                endpoint_kind=ENDPOINT_CONTEXT,
                name="para_no",
                minimum=CONTEXT_PARA_NO_MIN,
                maximum=CONTEXT_PARA_NO_MAX,
                doc_id=doc_id,
            )
        return self._get(ENDPOINT_CONTEXT, path, params=params, doc_id=doc_id)

    def search(self, q: str, *, limit: int = 20) -> CatalogueResponse:
        return self._get(
            ENDPOINT_SEARCH,
            "/search",
            params={
                "q": str(q),
                "limit": _bounded_int(
                    limit,
                    endpoint_kind=ENDPOINT_SEARCH,
                    name="limit",
                    minimum=SEARCH_LIMIT_MIN,
                    maximum=SEARCH_LIMIT_MAX,
                ),
            },
        )

    def _get(
        self,
        endpoint_kind: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        doc_id: str = "",
    ) -> CatalogueResponse:
        return self._request(
            "GET",
            path,
            endpoint_kind=endpoint_kind,
            params=params,
            doc_id=doc_id,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        endpoint_kind: str = "",
        params: Mapping[str, Any] | None = None,
        doc_id: str = "",
    ) -> CatalogueResponse:
        normalized_method = str(method or "").strip().upper()
        if normalized_method != "GET":
            raise CatalogueForbiddenMethod(
                endpoint_kind=endpoint_kind,
                doc_id=doc_id,
                detail=normalized_method or "missing_method",
            )

        safe_path = _validate_get_path(path, endpoint_kind=endpoint_kind, doc_id=doc_id)
        url = _join_base_url(self.config.base_url, safe_path)
        started = self._monotonic()
        try:
            response = self._requests.get(
                url,
                params=_clean_params(params),
                timeout=self.config.timeout_s,
            )
        except Exception as exc:
            duration_ms = _duration_ms(started, self._monotonic)
            if _is_timeout_exception(exc, self._requests):
                raise CatalogueTimeout(
                    endpoint_kind=endpoint_kind,
                    duration_ms=duration_ms,
                    doc_id=doc_id,
                    error_class=exc.__class__.__name__,
                ) from exc
            raise CatalogueServiceUnavailable(
                endpoint_kind=endpoint_kind,
                duration_ms=duration_ms,
                doc_id=doc_id,
                error_class=exc.__class__.__name__,
            ) from exc

        duration_ms = _duration_ms(started, self._monotonic)
        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code == 404:
            raise CatalogueNotFound(
                endpoint_kind=endpoint_kind,
                status_code=status_code,
                duration_ms=duration_ms,
                doc_id=doc_id,
            )
        if status_code in {502, 503, 504}:
            raise CatalogueServiceUnavailable(
                endpoint_kind=endpoint_kind,
                status_code=status_code,
                duration_ms=duration_ms,
                doc_id=doc_id,
            )
        if status_code < 200 or status_code >= 300:
            raise CatalogueUnexpectedStatus(
                endpoint_kind=endpoint_kind,
                status_code=status_code,
                duration_ms=duration_ms,
                doc_id=doc_id,
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise CatalogueInvalidJson(
                endpoint_kind=endpoint_kind,
                status_code=status_code,
                duration_ms=duration_ms,
                doc_id=doc_id,
                error_class=exc.__class__.__name__,
            ) from exc
        if not isinstance(payload, dict):
            raise CatalogueInvalidJson(
                endpoint_kind=endpoint_kind,
                status_code=status_code,
                duration_ms=duration_ms,
                doc_id=doc_id,
                error_class=type(payload).__name__,
            )

        return CatalogueResponse(
            endpoint_kind=endpoint_kind,
            status_code=status_code,
            payload=payload,
            duration_ms=duration_ms,
            result_count=_result_count(payload),
            doc_id_short=short_doc_id(doc_id),
            content_chars=_content_chars(payload),
        )


def _validate_base_url(base_url: str) -> None:
    parsed = urlparse(str(base_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CatalogueInvalidBaseUrl(detail="base_url_must_be_http")
    if parsed.query or parsed.fragment:
        raise CatalogueInvalidBaseUrl(detail="base_url_must_not_have_query_or_fragment")


def _validate_get_path(path: str, *, endpoint_kind: str = "", doc_id: str = "") -> str:
    normalized = str(path or "").strip()
    parsed = urlparse(normalized)
    if parsed.scheme or parsed.netloc or parsed.params or parsed.query or parsed.fragment:
        raise CatalogueForbiddenRoute(endpoint_kind=endpoint_kind, doc_id=doc_id, detail="absolute_or_query_path")
    if not normalized.startswith("/") or normalized.startswith("//"):
        raise CatalogueForbiddenRoute(endpoint_kind=endpoint_kind, doc_id=doc_id, detail="invalid_path")
    if any(segment in {"..", "."} for segment in normalized.split("/")):
        raise CatalogueForbiddenRoute(endpoint_kind=endpoint_kind, doc_id=doc_id, detail="path_traversal")
    if normalized in _FORBIDDEN_MUTATING_PATHS:
        raise CatalogueForbiddenRoute(endpoint_kind=endpoint_kind, doc_id=doc_id, detail="forbidden_mutating_path")
    if normalized in _ALLOWED_STATIC_GET_PATHS:
        return normalized

    parts = normalized.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "doc" and parts[1]:
        if len(parts) == 2:
            return normalized
        if len(parts) == 3 and parts[2] in {"metadata", "chapters", "locate", "context"}:
            return normalized
        if len(parts) == 4 and parts[2] == "page" and parts[3].isdigit():
            return normalized

    raise CatalogueForbiddenRoute(endpoint_kind=endpoint_kind, doc_id=doc_id, detail="not_in_get_allowlist")


def _join_base_url(base_url: str, path: str) -> str:
    clean_base = str(base_url or "").rstrip("/")
    return f"{clean_base}{path}"


def _quote_path_segment(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise CatalogueForbiddenRoute(detail="empty_path_segment")
    return quote(text, safe="")


def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in dict(params or {}).items():
        if value is None:
            continue
        cleaned[str(key)] = value
    return cleaned


def _result_count(payload: Mapping[str, Any]) -> int | None:
    count = payload.get("count")
    if isinstance(count, int):
        return count
    for key in ("items", "results", "chapters"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def _content_chars(payload: Mapping[str, Any]) -> int:
    total = 0
    for key in ("text", "context", "markdown", "raw_text"):
        value = payload.get(key)
        if isinstance(value, str):
            total += len(value)
    return total


def _positive_int(value: Any, default: int) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return default
    return integer if integer > 0 else default


def _bounded_int(
    value: Any,
    *,
    endpoint_kind: str,
    name: str,
    minimum: int,
    maximum: int,
    doc_id: str = "",
) -> int:
    integer = _strict_int_parameter(
        value,
        endpoint_kind=endpoint_kind,
        name=name,
        doc_id=doc_id,
    )

    if integer < minimum or integer > maximum:
        raise CatalogueInvalidParameter(
            endpoint_kind=endpoint_kind,
            doc_id=doc_id,
            detail=f"{name}_out_of_range",
        )
    return integer


def _strict_int_parameter(value: Any, *, endpoint_kind: str, name: str, doc_id: str) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise CatalogueInvalidParameter(
        endpoint_kind=endpoint_kind,
        doc_id=doc_id,
        detail=f"{name}_must_be_integer",
    )


def _duration_ms(started: float, monotonic: Any) -> int:
    return int(max((monotonic() - started) * 1000, 0))


def _is_timeout_exception(exc: Exception, requests_module: Any) -> bool:
    timeout_cls = getattr(getattr(requests_module, "exceptions", None), "Timeout", None)
    if timeout_cls is not None and isinstance(exc, timeout_cls):
        return True
    return isinstance(exc, TimeoutError) or "timeout" in exc.__class__.__name__.lower()
