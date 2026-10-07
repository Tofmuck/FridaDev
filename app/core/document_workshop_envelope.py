"""Closed M4 response: a real surface and an optional immutable proposal.

Validation grants no write capability. Source ownership/freshness and the
selected root are revalidated by the turn boundary before committing a pending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import unicodedata
from uuid import UUID

from .document_canonical import ValidatedCanonical, strict_json_loads, validate_canonical
from .document_workshop_contract import DOCUMENT_PROFILE, MAX_CANONICAL_JSON_BYTES, DocumentWorkshopError
from .workspace_document_paths import validate_document_path


MAX_DOCUMENT_ENVELOPE_BYTES = MAX_CANONICAL_JSON_BYTES + 65_536
MAX_DOCUMENT_SURFACE_CODEPOINTS = 2_000
DOCUMENT_LIMITATION_CODES = frozenset({
    "markdown_pagination_reader_dependent", "markdown_style_reader_dependent",
    "write_confirmation_unavailable",
    "docx_pdf_unavailable", "update_unavailable",
})


def _invalid() -> None:
    raise DocumentWorkshopError("document_envelope_invalid")


def _closed(value: object, fields: set[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        _invalid()
    return value


def _surface(value: object) -> str:
    if (type(value) is not str or not value.strip()
            or len(value) > MAX_DOCUMENT_SURFACE_CODEPOINTS):
        _invalid()
    if any(unicodedata.category(char) == "Cs"
           or (unicodedata.category(char) == "Cc" and char not in "\r\n\t")
           for char in value):
        _invalid()
    # Inspect complete JSON objects/arrays even when surrounded by prose or
    # fences. At most 2000 starts are inspected: this is a bounded protocol
    # guard, not a classifier of arbitrary source quotations. Accepted speech
    # is preserved byte-for-byte, without trim or rewrite.
    decoder = json.JSONDecoder()
    pending = []
    for index, char in enumerate(value):
        if char not in "{[":
            continue
        try:
            parsed, _end = decoder.raw_decode(value, index)
        except (ValueError, RecursionError):
            continue
        pending.append(parsed)
    while pending:
        item = pending.pop()
        if type(item) is dict:
            if type(item.get("schema_version")) is int and item["schema_version"] == 1:
                if item.get("profile") == DOCUMENT_PROFILE and "blocks" in item:
                    _invalid()
                if (type(item.get("status")) is str and item["status"] in {"prepared", "clarify", "refuse"}
                        and "surface_text" in item and "proposal" in item):
                    _invalid()
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return value


def _source_ids(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        _invalid()
    ids = []
    for item in value:
        if type(item) is not str:
            _invalid()
        try:
            ids.append(str(UUID(item)))
        except (ValueError, AttributeError):
            _invalid()
    if len(set(ids)) != len(ids):
        _invalid()
    return tuple(ids)


def _limitations(value: object) -> tuple[str, ...]:
    if (type(value) is not list
            or any(type(code) is not str or code not in DOCUMENT_LIMITATION_CODES for code in value)
            or len(set(value)) != len(value)):
        _invalid()
    return tuple(value)


@dataclass(frozen=True, repr=False)
class DocumentEnvelope:
    status: str
    surface_text: str = field(repr=False)
    canonical: ValidatedCanonical | None = field(default=None, repr=False)
    operation: str | None = None
    relative_path: str | None = field(default=None, repr=False)
    source_file_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    format: str | None = None

    def as_dict(self) -> dict:
        proposal = None
        if self.canonical is not None:
            proposal = {
                "operation": self.operation, "format": self.format,
                "relative_path": self.relative_path,
                "source_file_ids": list(self.source_file_ids),
                "limitations": list(self.limitations),
                "canonical": self.canonical.as_dict(),
            }
        return {"schema_version": 1, "status": self.status,
                "surface_text": self.surface_text, "proposal": proposal}


def read_document_envelope(raw: str) -> DocumentEnvelope:
    if type(raw) is not str:
        _invalid()
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError:
        _invalid()
    if size > MAX_DOCUMENT_ENVELOPE_BYTES:
        raise DocumentWorkshopError("document_json_envelope_limit")
    try:
        value = strict_json_loads(raw)
    except DocumentWorkshopError:
        _invalid()
    root = _closed(value, {"schema_version", "status", "surface_text", "proposal"})
    if (type(root["schema_version"]) is not int or root["schema_version"] != 1
            or type(root["status"]) is not str
            or root["status"] not in {"prepared", "clarify", "refuse"}):
        _invalid()
    surface = _surface(root["surface_text"])
    status = root["status"]
    if status != "prepared":
        if root["proposal"] is not None:
            _invalid()
        return DocumentEnvelope(status, surface)
    proposal = _closed(root["proposal"], {
        "operation", "format", "relative_path", "source_file_ids", "limitations", "canonical",
    })
    if (type(proposal["operation"]) is not str or proposal["operation"] not in {"create", "copy", "update"}
            or type(proposal["format"]) is not str or proposal["format"] != "markdown"):
        _invalid()
    path = validate_document_path(proposal["relative_path"], format="markdown")
    sources = _source_ids(proposal["source_file_ids"])
    if proposal["operation"] == "copy" and not sources:
        _invalid()
    limitations = _limitations(proposal["limitations"])
    canonical = validate_canonical(proposal["canonical"])
    return DocumentEnvelope(status, surface, canonical, proposal["operation"],
                            path.relative_path, sources, limitations, "markdown")


# Exactly one root response schema is appended before admission. The nested
# canonical forms are described here, rather than appending the M0 root schema.
DOCUMENT_ENVELOPE_INSTRUCTIONS = """Return one complete JSON envelope, no fence or commentary.
The root has exactly these required keys:
{schema_version:1, status:"prepared"|"clarify"|"refuse", surface_text:string, proposal:object|null}.
surface_text is your real, short response to the user, nonblank, at most 2000
Unicode codepoints. Preserve the user's meaning; do not invent a successful write.
Do not put document/source content, canonical JSON or the response envelope in
surface_text, including a JSON fence. The surface is speech, not a document preview.
For clarify/refuse, proposal must be null: ask the necessary question or state the refusal.
For prepared, proposal has exactly these required keys:
{operation:"create"|"copy"|"update", format:"markdown", relative_path:string,
 source_file_ids:[UUID strings], limitations:[codes], canonical:object}.
Update requires the explicitly selected server target and advertised capability.
For update, use that exact target path/name; never choose another target or identity.
DOCX and PDF preparation are unavailable. The path is exactly
Documents/<optional subdirectories>/<name.md>, relative to the selected folder:
at most 8 subdirectories, 180 codepoints/255 UTF-8 bytes per segment, 1024 UTF-8
bytes for the full path. No traversal, encoded separator or renamed/trimmed target.
Use only explicitly supplied source file UUIDs, each at most once; copy requires
at least one source. Limitations are unique codes from
markdown_pagination_reader_dependent, write_confirmation_unavailable,
markdown_style_reader_dependent, docx_pdf_unavailable, update_unavailable.
No free-form limitations or extra keys.
The nested canonical has exactly {schema_version:1, profile:"frida_document_v1", blocks:[...]}.
blocks is nonempty. Required, closed block forms:
paragraph/quote: {type, spans}; heading: {type, level (integer 1..6), spans};
list: {type:"list", ordered (boolean), items (nonempty array of spans arrays)};
table: {type:"table", rows (nonempty rectangular array of cells/spans arrays)};
page_break: {type:"page_break"}. A span has exactly {text (nonempty string),
bold (boolean), italic (boolean), link (null or passive absolute http/https URL without credentials)}.
No images, executable references, macros, commands or active HTML nodes.
Include all canonical text: at most 10000 words and 75000 Unicode codepoints
across text and URL targets, and at most 1048576 UTF-8 bytes of compact canonical JSON.
The fixed frida_document_v1 layout profile is A4, 12pt, line spacing 1.5,
with 2.5cm margins; Markdown cannot establish that binary layout.
The complete response envelope is at most 1114112 UTF-8 bytes.
No truncation, summary or rewriting to evade limits. Markdown pagination depends
on the reader; inline style delimiters also depend on the reader and adjacency.
No page count or full style fidelity is established. Preparation cannot write;
execution requires separate human confirmation and the advertised server capability.
"""
