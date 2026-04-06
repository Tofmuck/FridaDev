from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_governance_service
from admin import runtime_settings


class _FakeRuntimeSettings:
    RuntimeSettingsValidationError = runtime_settings.RuntimeSettingsValidationError
    RuntimeSettingsDbUnavailableError = runtime_settings.RuntimeSettingsDbUnavailableError

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        seeds = runtime_settings.build_env_seed_bundle('identity_governance').payload
        self.payload = runtime_settings.normalize_stored_payload(
            'identity_governance',
            seeds,
            default_origin='env_seed',
        )
        for key, value in (values or {}).items():
            self.payload[key] = {
                'value': value,
                'is_secret': False,
                'origin': 'db',
            }

    def _view(self, *, source: str = 'db', source_reason: str = 'db_row'):
        return runtime_settings.RuntimeSectionView(
            section='identity_governance',
            payload=self.payload,
            source=source,
            source_reason=source_reason,
        )

    def get_runtime_section(self, section: str, *, fetcher=None):
        self._assert_section(section)
        return self._view()

    def get_identity_governance_settings(self, *, fetcher=None):
        return self._view()

    def validate_runtime_section(self, section: str, patch_payload=None):
        self._assert_section(section)
        merged = {
            key: field.get('value')
            for key, field in self.payload.items()
            if isinstance(field, dict)
        }
        for key, field in (patch_payload or {}).items():
            merged[str(key)] = field.get('value')

        min_confidence = float(merged['IDENTITY_MIN_CONFIDENCE'])
        defer_confidence = float(merged['IDENTITY_DEFER_MIN_CONFIDENCE'])
        min_recurrence = int(merged['IDENTITY_MIN_RECURRENCE_FOR_DURABLE'])
        min_distinct = int(merged['IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS'])
        max_items = int(merged['CONTEXT_HINTS_MAX_ITEMS'])
        max_tokens = int(merged['CONTEXT_HINTS_MAX_TOKENS'])
        max_age_days = int(merged['CONTEXT_HINTS_MAX_AGE_DAYS'])
        min_gap_hours = int(merged['IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS'])
        min_context_confidence = float(merged['CONTEXT_HINTS_MIN_CONFIDENCE'])

        checks = [
            {
                'name': 'IDENTITY_DEFER_MIN_CONFIDENCE',
                'ok': 0.0 <= defer_confidence <= min_confidence <= 1.0,
                'detail': 'defer <= accepted',
            },
            {
                'name': 'IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
                'ok': min_recurrence >= min_distinct >= 1,
                'detail': 'recurrence >= distinct conversations',
            },
            {
                'name': 'CONTEXT_HINTS_MAX_ITEMS',
                'ok': max_items >= 1,
                'detail': 'max items >= 1',
            },
            {
                'name': 'CONTEXT_HINTS_MAX_TOKENS',
                'ok': 1 <= max_tokens <= 32000,
                'detail': 'max tokens bounded',
            },
            {
                'name': 'CONTEXT_HINTS_MAX_AGE_DAYS',
                'ok': max_age_days >= 1,
                'detail': 'max age >= 1',
            },
            {
                'name': 'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
                'ok': min_gap_hours >= 1,
                'detail': 'time gap >= 1',
            },
            {
                'name': 'CONTEXT_HINTS_MIN_CONFIDENCE',
                'ok': 0.0 <= min_context_confidence <= 1.0,
                'detail': 'confidence bounded',
            },
        ]
        return {
            'section': section,
            'source': 'candidate',
            'source_reason': 'validate_payload',
            'valid': all(check['ok'] for check in checks),
            'checks': checks,
        }

    def update_runtime_section(self, section: str, patch_payload, *, updated_by='admin_api', fetcher=None):
        self._assert_section(section)
        for key, field in patch_payload.items():
            self.payload[str(key)] = {
                'value': field.get('value'),
                'is_secret': False,
                'origin': 'admin_ui',
            }
        return self._view()

    @staticmethod
    def _assert_section(section: str) -> None:
        if section != 'identity_governance':
            raise AssertionError(section)


class IdentityGovernanceServicePhase5Tests(unittest.TestCase):
    def test_service_module_stays_below_repo_size_limit(self) -> None:
        service_path = APP_DIR / 'admin' / 'admin_identity_governance_service.py'
        with service_path.open('r', encoding='utf-8') as handle:
            line_count = sum(1 for _ in handle)
        self.assertLess(line_count, 500)

    def test_inventory_response_classifies_editable_readonly_and_legacy_items_honestly(self) -> None:
        runtime_module = _FakeRuntimeSettings(
            {
                'IDENTITY_MIN_CONFIDENCE': 0.81,
                'CONTEXT_HINTS_MAX_ITEMS': 3,
            }
        )

        payload, status = admin_identity_governance_service.identity_governance_response(
            {},
            runtime_settings_module=runtime_module,
            identity_module=SimpleNamespace(build_identity_input=lambda: {'schema_version': 'v2'}),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['governance_version'], 'v1')
        self.assertEqual(payload['active_prompt_contract'], 'static + mutable narrative')
        self.assertEqual(payload['identity_input_schema_version'], 'v2')
        items_by_key = {item['key']: item for item in payload['items']}
        self.assertTrue(items_by_key['IDENTITY_MIN_CONFIDENCE']['editable'])
        self.assertEqual(items_by_key['IDENTITY_MIN_CONFIDENCE']['category'], 'active_subpipeline_editable')
        self.assertEqual(items_by_key['CONTEXT_HINTS_MAX_ITEMS']['category'], 'active_runtime_editable')
        self.assertFalse(items_by_key['IDENTITY_MUTABLE_TARGET_CHARS']['editable'])
        self.assertEqual(items_by_key['IDENTITY_MUTABLE_TARGET_CHARS']['category'], 'doctrine_locked_readonly')
        self.assertEqual(items_by_key['identity_extractor_max_tokens']['source_kind'], 'hardcoded')
        self.assertEqual(items_by_key['IDENTITY_TOP_N']['category'], 'legacy_inactive_readonly')
        self.assertEqual(items_by_key['IDENTITY_MAX_TOKENS']['category'], 'legacy_inactive_readonly')
        self.assertGreater(payload['editable_count'], 0)
        self.assertGreater(payload['readonly_count'], 0)
        self.assertGreaterEqual(payload['legacy_inactive_count'], 2)
        self.assertGreater(payload['active_runtime_count'], 0)
        self.assertGreater(payload['active_subpipeline_count'], 0)

    def test_update_response_applies_editable_change_and_keeps_audit_compact(self) -> None:
        runtime_module = _FakeRuntimeSettings({'CONTEXT_HINTS_MAX_ITEMS': 2})
        observed_logs: list[tuple[str, dict[str, Any]]] = []

        payload, status = admin_identity_governance_service.identity_governance_update_response(
            {
                'updates': {'CONTEXT_HINTS_MAX_ITEMS': 3},
                'reason': 'raise visible context hints',
            },
            runtime_settings_module=runtime_module,
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))),
            identity_module=SimpleNamespace(build_identity_input=lambda: {'schema_version': 'v2'}),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['reason_code'], 'update_applied')
        self.assertEqual(payload['changed_keys'], ['CONTEXT_HINTS_MAX_ITEMS'])
        self.assertEqual(
            runtime_module.get_identity_governance_settings().payload['CONTEXT_HINTS_MAX_ITEMS']['value'],
            3,
        )
        event_name, event_payload = observed_logs[0]
        self.assertEqual(event_name, 'identity_governance_admin_edit')
        self.assertEqual(event_payload['changed_keys'], ['CONTEXT_HINTS_MAX_ITEMS'])
        self.assertNotIn('content', event_payload)
        self.assertNotIn('reason', event_payload)

    def test_update_response_rejects_invariant_violation_fail_closed(self) -> None:
        runtime_module = _FakeRuntimeSettings({'IDENTITY_MIN_CONFIDENCE': 0.72})
        observed_logs: list[tuple[str, dict[str, Any]]] = []

        payload, status = admin_identity_governance_service.identity_governance_update_response(
            {
                'updates': {'IDENTITY_DEFER_MIN_CONFIDENCE': 0.95},
                'reason': 'invalid invariant',
            },
            runtime_settings_module=runtime_module,
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))),
            identity_module=SimpleNamespace(build_identity_input=lambda: {'schema_version': 'v2'}),
        )

        self.assertEqual(status, 400)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'IDENTITY_DEFER_MIN_CONFIDENCE')
        self.assertEqual(
            runtime_module.get_identity_governance_settings().payload['IDENTITY_DEFER_MIN_CONFIDENCE']['value'],
            0.58,
        )
        self.assertEqual(observed_logs[0][1]['validation_error'], 'IDENTITY_DEFER_MIN_CONFIDENCE')

    def test_update_response_rejects_readonly_or_legacy_key(self) -> None:
        runtime_module = _FakeRuntimeSettings()
        observed_logs: list[tuple[str, dict[str, Any]]] = []

        payload, status = admin_identity_governance_service.identity_governance_update_response(
            {
                'updates': {'IDENTITY_TOP_N': 7},
                'reason': 'should fail',
            },
            runtime_settings_module=runtime_module,
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))),
            identity_module=SimpleNamespace(build_identity_input=lambda: {'schema_version': 'v2'}),
        )

        self.assertEqual(status, 400)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'governance_key_readonly')
        self.assertEqual(observed_logs[0][1]['validation_error'], 'governance_key_readonly')


if __name__ == '__main__':
    unittest.main()
