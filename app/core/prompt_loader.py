from __future__ import annotations

from pathlib import Path

import config


APP_DIR = Path(__file__).resolve().parents[1]


def resolve_app_prompt_path(path_str: str) -> Path:
    return APP_DIR / str(path_str)


def read_prompt_text(path_str: str) -> str:
    try:
        return resolve_app_prompt_path(path_str).read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def get_main_system_prompt() -> str:
    return read_prompt_text(str(config.MAIN_SYSTEM_PROMPT_PATH))


def get_main_hermeneutical_prompt() -> str:
    return read_prompt_text(str(config.MAIN_HERMENEUTICAL_PROMPT_PATH))
