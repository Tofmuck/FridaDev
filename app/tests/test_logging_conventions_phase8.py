from __future__ import annotations

import re
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent

LOGGER_EXPECTATIONS = {
    APP_DIR / 'identity' / 'identity.py': 'frida.identity',
    APP_DIR / 'admin' / 'admin_logs.py': 'frida.adminlog',
    APP_DIR / 'tools' / 'web_search.py': 'frida.web_search',
    APP_DIR / 'memory' / 'memory_store.py': 'frida.memory_store',
    APP_DIR / 'core' / 'conv_store.py': 'frida.conv',
    APP_DIR / 'memory' / 'summarizer.py': 'frida.summarizer',
    APP_DIR / 'memory' / 'arbiter.py': 'frida.arbiter',
}

LEGACY_TOKEN_EXCLUDE_PREFIXES = (
    Path('docs/todo-done'),
    Path('docs/states/legacy'),
    Path('docs/states/baselines'),
)


class LoggingConventionsPhase8Tests(unittest.TestCase):
    def test_repo_has_no_legacy_logger_token(self) -> None:
        legacy_token = 'ki' + 'ki'
        matches: list[str] = []
        for path in sorted(APP_DIR.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(APP_DIR)
            if '__pycache__' in relative.parts:
                continue
            if any(
                prefix == relative or prefix in relative.parents
                for prefix in LEGACY_TOKEN_EXCLUDE_PREFIXES
            ):
                continue
            try:
                payload = path.read_bytes()
            except OSError as exc:
                self.fail(f'unable to read {relative}: {exc.__class__.__name__}')
            if b'\x00' in payload:
                continue
            text = payload.decode('utf-8', errors='ignore')
            for line_number, line in enumerate(text.splitlines(), start=1):
                if legacy_token.casefold() in line.casefold():
                    matches.append(f'{relative}:{line_number}')
        self.assertEqual(
            matches,
            [],
            msg='legacy token still present:\n' + '\n'.join(matches),
        )

    def test_target_modules_keep_standard_logging_getlogger_calls(self) -> None:
        for path, logger_name in LOGGER_EXPECTATIONS.items():
            source = path.read_text(encoding='utf-8')
            pattern = re.compile(r"logging\.getLogger\((['\"])" + re.escape(logger_name) + r"\1\)")
            self.assertRegex(source, pattern, msg=f'missing canonical logger in {path}')


if __name__ == '__main__':
    unittest.main()
