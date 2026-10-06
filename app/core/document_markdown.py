"""Direct passive Markdown serialization of a validated canonical snapshot.

Page breaks use the fixed `<!-- frida-page-break -->` marker. Its display and
pagination depend on the reader. A table has a synthetic empty Markdown header:
no canonical data row is silently promoted to header semantics.
CommonMark emphasis cannot express every style boundary next to punctuation;
the reader-dependent style limitation is distinct from pagination. No extra
text or raw HTML styles are inserted to force a delimiter to render.
"""
from __future__ import annotations

import string

from .document_canonical import ValidatedCanonical
from .document_workshop_contract import DocumentWorkshopError


MARKDOWN_PAGE_BREAK = "<!-- frida-page-break -->"
_TEXT_ENTITIES = {"&": "&amp;", "<": "&lt;", ">": "&gt;",
                  "\r": "&#13;", "\n": "&#10;", "\t": "&#9;"}


def _text(text: str) -> str:
    # Newlines/tabs stay text inside the canonical block, never new Markdown
    # blocks, image syntax, table rows or executable HTML supplied by the model.
    return "".join(_TEXT_ENTITIES[char] if char in _TEXT_ENTITIES
                   else "\\" + char if char in string.punctuation else char
                   for char in text)


def _destination(url: str) -> str:
    # An angle destination tolerates parentheses/brackets without link breakout.
    # Its terminators/backslash and the table delimiter are encoded; ampersands
    # cannot become an entity reference changing the target. No URL is fetched.
    return url.replace("\\", "%5C").replace("<", "%3C").replace(">", "%3E").replace(
        "|", "%7C").replace("&", "&amp;")


def _styled(text: str, bold: bool, italic: bool, link: str | None) -> str:
    # Keep edge whitespace outside emphasis so Markdown delimiter rules do not
    # consume it as an invalid opening/closing delimiter. Every character stays.
    left, right = 0, len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    core = _text(text[left:right])
    if core:
        marker = "*" * (2 * bold + italic)
        core = marker + core + marker
    rendered = _text(text[:left]) + core + _text(text[right:])
    if link is not None:
        rendered = "[" + rendered + "](<" + _destination(link) + ">)"
    return rendered


def _spans(spans: list[dict]) -> str:
    parts = []
    run_text = ""
    run_style = None
    for span in spans:
        style = (span["bold"], span["italic"], span["link"])
        if run_style is not None and style != run_style:
            parts.append(_styled(run_text, *run_style))
            run_text = ""
        run_style = style
        run_text += span["text"]
    if run_style is not None:
        parts.append(_styled(run_text, *run_style))
    text = "".join(parts)
    # Leading literal spaces could turn a paragraph into an indented code block.
    leading = len(text) - len(text.lstrip(" "))
    text = "&#32;" * leading + text[leading:]
    trailing = len(text) - len(text.rstrip(" "))
    return text[:-trailing] + "&#32;" * trailing if trailing else text


def serialize_markdown(canonical: ValidatedCanonical) -> str:
    if not isinstance(canonical, ValidatedCanonical):
        raise DocumentWorkshopError("document_canonical_invalid")
    blocks = []
    for block in canonical.as_dict()["blocks"]:
        kind = block["type"]
        if kind == "page_break":
            rendered = MARKDOWN_PAGE_BREAK
        elif kind == "list":
            rendered = "\n".join((str(index) + ". " if block["ordered"] else "- ") + _spans(item)
                                 for index, item in enumerate(block["items"], 1))
        elif kind == "table":
            width = len(block["rows"][0])
            rows = ["| " + " | ".join([""] * width) + " |",
                    "| " + " | ".join(["---"] * width) + " |"]
            rows.extend("| " + " | ".join(_spans(cell) for cell in row) + " |" for row in block["rows"])
            rendered = "\n".join(rows)
        else:
            prefix = "#" * block["level"] + " " if kind == "heading" else "> " if kind == "quote" else ""
            rendered = prefix + _spans(block["spans"])
        blocks.append(rendered)
    return "\n\n".join(blocks) + "\n"
