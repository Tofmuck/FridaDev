"""Confirmable workshop paths: validation preserves every displayed codepoint."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from urllib.parse import quote

from .document_workshop_contract import DOCUMENT_EXTENSIONS, DocumentWorkshopError

_SEPARATORS = set("/\\∕⁄／＼⧸⧵⧹∖﹨")
_FORBIDDEN = _SEPARATORS | set(':*?"<>|')
_ENCODED = re.compile(r"%[0-9a-fA-F]{2}")


def _validate_segment(segment: object) -> str:
    if type(segment) is not str or not segment or segment in {".", ".."}:
        raise DocumentWorkshopError("document_path_invalid")
    if segment != segment.strip() or segment.endswith(".") or _ENCODED.search(segment):
        raise DocumentWorkshopError("document_path_invalid")
    if any(char in _FORBIDDEN or unicodedata.category(char).startswith("C")
           or unicodedata.category(char) in {"Zl", "Zp"} for char in segment):
        raise DocumentWorkshopError("document_path_invalid")
    # Canonical-equivalent French combining accents remain admissible and
    # unchanged. Compatibility spellings (fullwidth, ligatures, exotic spaces)
    # are refused rather than silently rewritten into another confirmable name.
    if unicodedata.normalize("NFKC", segment) != unicodedata.normalize("NFC", segment):
        raise DocumentWorkshopError("document_path_invalid")
    if len(segment) > 180 or len(segment.encode("utf-8")) > 255:
        raise DocumentWorkshopError("document_path_segment_limit")
    return segment


@dataclass(frozen=True, repr=False)
class DocumentTargetPath:
    relative_path: str
    collision_key: str
    segments: tuple[str, ...]

    @property
    def encoded_relative_path(self) -> str:
        return "/".join(quote(segment, safe="") for segment in self.segments)

    def dav_segments(self, server_folder_name: str) -> tuple[str, ...]:
        """Server-resolved folder mapping; DAV root/user prefixes belong to client.

        This pure projection grants no DAV capability or mutation authority.
        Its Documents-prefixed suffix is exactly the representation validated,
        counted and displayed, without trimming any part of the relative path.
        """
        return (_validate_segment(server_folder_name), *self.segments)


def _validate_document_relative_path(relative_path: object, *, is_collection: bool) -> DocumentTargetPath:
    """One segment authority for product targets and remote source inventory."""
    if type(relative_path) is not str:
        raise DocumentWorkshopError("document_path_invalid")
    parts = relative_path.split("/")
    if len(parts) < (1 if is_collection else 2) or parts[0] != "Documents":
        raise DocumentWorkshopError("document_path_invalid")
    for segment in parts:
        _validate_segment(segment)
    if len(parts) - (1 if is_collection else 2) > 8:
        raise DocumentWorkshopError("document_path_depth_limit")
    if len(relative_path.encode("utf-8")) > 1024:
        raise DocumentWorkshopError("document_path_byte_limit")
    collision_key = unicodedata.normalize("NFC", relative_path).casefold()
    return DocumentTargetPath(relative_path, collision_key, tuple(parts))


def validate_document_collection_path(relative_path: object) -> DocumentTargetPath:
    return _validate_document_relative_path(relative_path, is_collection=True)


def validate_document_source_path(relative_path: object) -> DocumentTargetPath:
    path = _validate_document_relative_path(relative_path, is_collection=False)
    if not path.segments[-1].lower().endswith((".txt", ".md", ".markdown", ".docx", ".odt", ".pdf")):
        raise DocumentWorkshopError("document_type_unsupported")
    return path


def validate_document_path(relative_path: object, *, format: str) -> DocumentTargetPath:
    if type(format) is not str or format not in DOCUMENT_EXTENSIONS:
        raise DocumentWorkshopError("document_path_invalid")
    path = _validate_document_relative_path(relative_path, is_collection=False)
    if not path.segments[-1].lower().endswith(DOCUMENT_EXTENSIONS[format]):
        raise DocumentWorkshopError("document_path_invalid")
    return path
