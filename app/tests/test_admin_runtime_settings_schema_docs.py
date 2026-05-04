from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings_spec


class AdminRuntimeSettingsSchemaDocsTests(unittest.TestCase):
    def test_schema_doc_lists_runtime_sections_from_executable_spec(self) -> None:
        doc_path = REPO_DIR / 'app' / 'docs' / 'states' / 'specs' / 'admin-runtime-settings-schema.md'
        source = doc_path.read_text(encoding='utf-8')

        documented_sections = tuple(
            re.findall(r'^### `([^`]+)`$', source, flags=re.MULTILINE)
        )
        self.assertEqual(documented_sections, runtime_settings_spec.SECTION_NAMES)

        principles = source.split('## Principes', 1)[1].split('## Secrets runtime V1', 1)[0]
        for section in runtime_settings_spec.SECTION_NAMES:
            self.assertIn(f'`{section}`', principles)

        self.assertIn(
            "`identity_governance` est une section runtime mais n'est pas exposee par `/api/admin/settings/<section>`",
            principles,
        )


if __name__ == '__main__':
    unittest.main()
