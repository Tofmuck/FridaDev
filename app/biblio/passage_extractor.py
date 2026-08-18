"""Public bounded passage extraction facade for native Biblio.

The facade validates the request and resolves its document/locator. Mechanical
context/page extraction is delegated only after a unique resolution exists.
"""

from __future__ import annotations

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueInvalidParameter,
    CatalogueNotFound,
    CatalogueResponse,
)
from .document_resolver import (
    BiblioDocumentResolver,
    BiblioResolutionResult,
    BiblioResolveRequest,
    LocatorCandidate,
    STATUS_AMBIGUOUS,
    STATUS_CATALOGUE_UNAVAILABLE,
    STATUS_INVALID_REQUEST,
    STATUS_NOT_FOUND,
    STATUS_RESOLVED,
)
from .passage_extraction import (
    BiblioCanonicalIntervalHint,
    BiblioPassageRequest,
    BiblioPassageResult,
    DEFAULT_CONTEXT_WINDOW_CHARS,
    DEFAULT_MAX_PASSAGE_CHARS,
    InvalidPassageParameter,
    MAX_CHAR_OFFSET,
    MAX_CONTEXT_WINDOW_CHARS,
    MAX_MAX_PASSAGE_CHARS,
    MAX_RANGE_PAGES,
    MAX_RANGE_PARAGRAPHS,
    MIN_CHAR_OFFSET,
    MIN_CONTEXT_WINDOW_CHARS,
    MIN_MAX_PASSAGE_CHARS,
    PassageExtractionOptions,
    REASON_CATALOGUE_UNAVAILABLE,
    REASON_INCOHERENT_CATALOGUE_RESPONSE,
    REASON_INVALID_CATALOGUE_REQUEST,
    REASON_INVALID_PASSAGE_PARAMETER,
    REASON_LOCATOR_CONTEXT_TARGET_MISSING,
    REASON_LOCATOR_REQUIRED,
    REASON_PASSAGE_EMPTY,
    REASON_PASSAGE_EXTRACTED,
    REASON_PASSAGE_NOT_FOUND,
    REASON_PASSAGE_TOO_LONG,
    REASON_RANGE_EXTRACTED,
    REASON_RANGE_EXTRACTION_NOT_SUPPORTED,
    REASON_RANGE_SEGMENT_EXTRACTED,
    ResolvedPassageExtractor,
    STATUS_EMPTY,
    STATUS_EXTRACTED,
    STATUS_INCOHERENT_CATALOGUE,
    STATUS_SEGMENT_EXTRACTED,
    STATUS_TOO_LONG,
    passage_extraction_options,
    passage_result_from_resolution,
)


class BiblioPassageExtractor:
    def __init__(
        self,
        client: CatalogueClient,
        *,
        resolver: BiblioDocumentResolver | None = None,
    ) -> None:
        self._client = client
        self._resolver = resolver if resolver is not None else BiblioDocumentResolver(client)
        self._resolved_extractor = ResolvedPassageExtractor(client)

    def extract(self, request: BiblioPassageRequest) -> BiblioPassageResult:
        try:
            options = passage_extraction_options(request)
        except InvalidPassageParameter:
            return BiblioPassageResult(
                status=STATUS_INVALID_REQUEST,
                reason_code=REASON_INVALID_PASSAGE_PARAMETER,
            )

        resolution = self._resolver.resolve(request.resolve_request)
        if resolution.status != STATUS_RESOLVED:
            return passage_result_from_resolution(resolution, options)
        return self._resolved_extractor.extract(resolution, options)
