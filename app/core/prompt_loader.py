from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import config


APP_DIR = Path(__file__).resolve().parents[1]

PROMPT_STATUS_AVAILABLE = 'available'
PROMPT_STATUS_UNAVAILABLE = 'unavailable'
PROMPT_STATUS_UNDECODABLE = 'undecodable'
PROMPT_STATUS_EMPTY = 'empty'


@dataclass(frozen=True)
class PromptLoadResult:
    text: str
    status: str

    @property
    def usable(self) -> bool:
        return self.status == PROMPT_STATUS_AVAILABLE


class RequiredPromptUnavailable(RuntimeError):
    def __init__(self, *, prompt_id: str, status: str) -> None:
        self.prompt_id = str(prompt_id)
        self.status = str(status)
        super().__init__('required_prompt_unavailable')


def resolve_app_prompt_path(path_str: str) -> Path:
    return APP_DIR / str(path_str)


def load_prompt_text(path_str: str) -> PromptLoadResult:
    try:
        text = resolve_app_prompt_path(path_str).read_text(encoding='utf-8').strip()
    except UnicodeError:
        return PromptLoadResult(text='', status=PROMPT_STATUS_UNDECODABLE)
    except OSError:
        return PromptLoadResult(text='', status=PROMPT_STATUS_UNAVAILABLE)
    if not text:
        return PromptLoadResult(text='', status=PROMPT_STATUS_EMPTY)
    return PromptLoadResult(text=text, status=PROMPT_STATUS_AVAILABLE)


def read_prompt_text(path_str: str) -> str:
    return load_prompt_text(path_str).text


def require_usable_prompt_text(text: str, *, prompt_id: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise RequiredPromptUnavailable(
            prompt_id=prompt_id,
            status=PROMPT_STATUS_EMPTY,
        )
    return normalized


def read_required_prompt_text(path_str: str, *, prompt_id: str) -> str:
    result = load_prompt_text(path_str)
    if not result.usable:
        raise RequiredPromptUnavailable(prompt_id=prompt_id, status=result.status)
    return result.text


def get_main_system_prompt() -> str:
    return read_prompt_text(str(config.MAIN_SYSTEM_PROMPT_PATH))


def get_main_hermeneutical_prompt() -> str:
    return read_prompt_text(str(config.MAIN_HERMENEUTICAL_PROMPT_PATH))


def get_summary_system_prompt() -> str:
    return read_prompt_text(str(config.SUMMARY_SYSTEM_PROMPT_PATH))


def get_web_reformulation_prompt() -> str:
    return read_prompt_text(str(config.WEB_REFORMULATION_PROMPT_PATH))
