from __future__ import annotations

from pathlib import Path

# Keep unittest discovery under tests/unit working while preventing this
# test package from masking the real application package app/memory.
APP_MEMORY_DIR = Path(__file__).resolve().parents[3] / "memory"
if APP_MEMORY_DIR.is_dir():
    __path__.append(str(APP_MEMORY_DIR))
