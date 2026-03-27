from __future__ import annotations

import re
import subprocess
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


class LoggingConventionsPhase8Tests(unittest.TestCase):
    def test_repo_has_no_legacy_logger_token(self) -> None:
        legacy_token = 'ki' + 'ki'
        run = subprocess.run(
            ['rg', '-n', legacy_token, str(REPO_ROOT), '-S'],
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode == 2:
            self.fail(f'rg failed: {run.stderr.strip()}')
        self.assertEqual(
            run.returncode,
            1,
            msg=f'legacy token still present:\n{run.stdout.strip()}',
        )

    def test_target_modules_keep_standard_logging_getlogger_calls(self) -> None:
        for path, logger_name in LOGGER_EXPECTATIONS.items():
            source = path.read_text(encoding='utf-8')
            pattern = re.compile(r"logging\.getLogger\((['\"])" + re.escape(logger_name) + r"\1\)")
            self.assertRegex(source, pattern, msg=f'missing canonical logger in {path}')


if __name__ == '__main__':
    unittest.main()
