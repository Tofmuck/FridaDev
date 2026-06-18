from __future__ import annotations

"""Markdown and TXT rendering for Exports V1 fake/local generation."""

import re
from typing import Any

from .workspace_folder_export_sources import ExportSource


def render_markdown_export(source: ExportSource, *, title: Any = "") -> str:
    heading = _clean_line(title) or source.title or "Export Frida"
    body = str(source.content or "").strip()
    return f"# {heading}\n\n{body}\n"


def render_txt_export(source: ExportSource, *, title: Any = "") -> str:
    markdown = render_markdown_export(source, title=title)
    lines = [_markdown_line_to_text(line) for line in markdown.splitlines()]
    text = "\n".join(lines).strip()
    return f"{text}\n" if text else ""


def _markdown_line_to_text(line: str) -> str:
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    text = re.sub(r"^\s{0,3}>\s?", "", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text.rstrip()


def _clean_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())
