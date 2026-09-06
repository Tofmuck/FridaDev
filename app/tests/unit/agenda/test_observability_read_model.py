from __future__ import annotations

import copy
import json
import unittest
from types import SimpleNamespace

from agenda import agent_contract, chat_runtime, observability_projection, observability_read_model, pending_store
from observability import observability_payload_guard
from tests.support.agenda_runtime_golden import (
    FakeAgendaModelClient,
    assert_content_free,
    propose_create_payload,
)


FORBIDDEN_VALUES = (
    'Fixture Private Title',
    'Fixture Private Location',
    'Fixture Private Description',
    'uid:fixture-private',
    'etag-fixture-private',
    '/remote.php/dav/calendars/tof/private/event.ics',
    'BEGIN:VCALENDAR',
    'BEGIN:VEVENT',
    'Authorization: Bearer fixture',
    'Cookie: fixture',
    'fixture-app-password',
)


def _encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class AgendaObservabilityReadModelTests(unittest.TestCase):
    def assert_content_free(self, value: object) -> None:
        encoded = _encoded(value)
        for marker in FORBIDDEN_VALUES:
            self.assertNotIn(marker, encoded)

    def test_real_pending_writer_payload_projects_pending_fields(self) -> None:
        agent_payload = propose_create_payload()
        agent_payload['calendar_scope'] = {
            'calendar_ids': ['family'],
            'family_calendar': True,
            'ambiguity': 'none',
        }
        agent_payload['draft']['calendar_id'] = 'family'
        agent_payload['mutation']['confirmation_level'] = 'reinforced'
        agent_payload['risk_flags'] = ['family_calendar']
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='SYNTHETIC-USER-CONTENT',
            now_iso='2026-06-08T00:00:00Z',
            config_module=SimpleNamespace(FRIDA_TIMEZONE='UTC'),
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=FakeAgendaModelClient(agent_payload),
            pending_id_factory=lambda: 'agenda-pending-observability-writer',
        )

        self.assertIsNotNone(result.proposal_execution_result)
        self.assertEqual(result.proposal_execution_result.pending_status, 'pending')
        payload = result.observability_payload
        self.assertEqual(payload['pending_status'], 'pending')
        self.assertEqual(payload['pending_confirmation_level'], 'reinforced')
        self.assertEqual(payload['pending_risk_flags'], ['family_calendar'])
        assert_content_free(payload)
        guard_decision = observability_payload_guard.guard_payload(payload)
        self.assertTrue(
            guard_decision.accepted,
            guard_decision.payload.get('issue_classes'),
        )

        projected = observability_projection.project_observability_payload(payload)
        self.assertEqual(projected['pending_action_status'], 'pending')
        self.assertEqual(projected['confirmation_level'], 'reinforced')
        self.assertEqual(projected['risk_flags'], ['family_calendar'])
        assert_content_free(projected)

        nested_only = dict(payload)
        for key in (
            'pending_status',
            'pending_confirmation_level',
            'pending_risk_flags',
            'confirmation_level',
        ):
            nested_only.pop(key, None)
        nested_projected = observability_projection.project_observability_payload(nested_only)
        self.assertEqual(nested_projected['pending_action_status'], 'pending')
        self.assertEqual(nested_projected['confirmation_level'], 'reinforced')
        self.assertEqual(nested_projected['risk_flags'], ['family_calendar'])

        read_model = observability_read_model.build_admin_observability(
            log_events=[
                {
                    'stage': 'agenda',
                    'status': 'ok',
                    'ts': '2026-06-08T00:00:01Z',
                    'payload': payload,
                }
            ]
        )
        summary = read_model['event_summary']
        self.assertEqual(summary['pending_status_counts'], {'pending': 1})
        self.assertEqual(summary['confirmation_levels'], ['reinforced'])
        self.assertEqual(summary['risk_flags'], ['family_calendar'])
        assert_content_free(read_model)

    def test_pending_projection_keeps_absence_empty_and_neutralizes_invalid_values(self) -> None:
        absent = observability_projection.project_observability_payload(
            {'schema_version': 'frida_agenda_lot6_pending_v1'}
        )
        self.assertEqual(absent['pending_action_status'], '')
        self.assertEqual(absent['confirmation_level'], '')
        self.assertEqual(absent['risk_flags'], [])

        invalid = observability_projection.project_observability_payload(
            {
                'schema_version': 'frida_agenda_lot6_pending_v1',
                'pending_status': 'https://calendar.example.invalid/private',
                'pending_confirmation_level': 'BEGIN:VEVENT',
                'pending_risk_flags': ['uid:fixture-private'],
                'pending_action_status': 'pending',
                'confirmation_level': 'reinforced',
                'risk_flags': ['family_calendar'],
                'content_free': True,
            }
        )
        self.assertEqual(invalid['pending_action_status'], '')
        self.assertEqual(invalid['confirmation_level'], '')
        self.assertEqual(invalid['risk_flags'], [])
        self.assert_content_free(invalid)

    def test_real_pending_guard_rejects_sensitive_container_mutations(self) -> None:
        agent_payload = propose_create_payload()
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='SYNTHETIC-USER-CONTENT',
            now_iso='2026-06-08T00:00:00Z',
            config_module=SimpleNamespace(FRIDA_TIMEZONE='UTC'),
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=FakeAgendaModelClient(agent_payload),
            pending_id_factory=lambda: 'agenda-pending-guard-negative',
        )
        payload = result.observability_payload
        sensitive_fields = (
            ('content', 'Fixture Private Title'),
            ('draft', {'title': 'Fixture Private Title'}),
            ('title', 'Fixture Private Title'),
            ('location', 'Fixture Private Location'),
            ('description', 'Fixture Private Description'),
            ('uid', 'uid:fixture-private'),
            ('etag', 'etag-fixture-private'),
            ('url', 'https://calendar.example.invalid/private'),
            ('caldav_path', '/remote.php/dav/calendars/tof/private/event.ics'),
            ('raw_ics', 'BEGIN:VEVENT'),
            ('raw_xml', '<?xml version="1.0"?><fixture/>'),
            ('headers', {'Authorization': 'Bearer fixture'}),
            ('credentials', {'app_password': 'fixture-app-password'}),
        )

        for container_name in ('final_response', 'pending_execution'):
            for key, value in sensitive_fields:
                with self.subTest(container=container_name, key=key):
                    mutated = copy.deepcopy(payload)
                    mutated[container_name][key] = value
                    decision = observability_payload_guard.guard_payload(mutated)
                    self.assertFalse(decision.accepted)
                    self.assert_content_free(decision.payload)

        sensitive_text_values = (
            'Fixture Private Title',
            'https://calendar.example.invalid/private',
            '/remote.php/dav/private/event.ics',
            'BEGIN:VEVENT',
            '<?xml version="1.0"?><fixture/>',
            'etag:fixture-private',
            'Authorization: Bearer fixture',
        )
        for container_name, key in (
            ('final_response', 'source'),
            ('pending_execution', 'product_method'),
        ):
            for value in sensitive_text_values:
                with self.subTest(container=container_name, key=key, kind='value', value=value):
                    mutated = copy.deepcopy(payload)
                    mutated[container_name][key] = value
                    decision = observability_payload_guard.guard_payload(mutated)
                    self.assertFalse(decision.accepted)
                    self.assert_content_free(decision.payload)

        for container_name, key, value in (
            ('final_response', 'agenda_risk_flags', ['BEGIN:VEVENT']),
            ('pending_execution', 'risk_flags', ['uid:fixture-private']),
        ):
            with self.subTest(container=container_name, key=key, kind='list_value'):
                mutated = copy.deepcopy(payload)
                mutated[container_name][key] = value
                decision = observability_payload_guard.guard_payload(mutated)
                self.assertFalse(decision.accepted)
                self.assert_content_free(decision.payload)

        wrong_types = (
            ('final_response', 'agenda_caldav_access', 'false'),
            ('final_response', 'content_chars', '42'),
            ('pending_execution', 'target_clear', 'false'),
            ('pending_execution', 'risk_flags', 'family_calendar'),
        )
        for container_name, key, value in wrong_types:
            with self.subTest(container=container_name, key=key, kind='type'):
                mutated = copy.deepcopy(payload)
                mutated[container_name][key] = value
                decision = observability_payload_guard.guard_payload(mutated)
                self.assertFalse(decision.accepted)
                self.assert_content_free(decision.payload)

        nested_sensitive = (
            ('draft_summary', 'title', 'Fixture Private Title'),
            ('draft_summary', 'caldav_path', '/remote.php/dav/private/event.ics'),
            ('write_execution', 'uid', 'uid:fixture-private'),
            ('write_execution', 'raw_ics', 'BEGIN:VEVENT'),
        )
        for nested_name, key, value in nested_sensitive:
            with self.subTest(container='pending_execution', nested=nested_name, key=key):
                mutated = copy.deepcopy(payload)
                mutated['pending_execution'][nested_name][key] = value
                decision = observability_payload_guard.guard_payload(mutated)
                self.assertFalse(decision.accepted)
                self.assert_content_free(decision.payload)

    def test_conversation_read_model_projects_pending_actions_without_raw_draft(self) -> None:
        state, action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda-observability'),
            operation=pending_store.OPERATION_DELETE,
            confirmation_level=pending_store.CONFIRMATION_REINFORCED,
            risk_flags=('family_calendar',),
            draft={
                'title': 'Fixture Private Title',
                'location': 'Fixture Private Location',
                'description': 'Fixture Private Description',
                'target': {
                    'technical_ref': {
                        'uid': 'uid:fixture-private',
                        'etag': 'etag-fixture-private',
                        'caldav_path': '/remote.php/dav/calendars/tof/private/event.ics',
                    },
                    'source_ics': 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nEND:VEVENT\nEND:VCALENDAR',
                },
            },
            now_iso='2026-06-09T15:00:00Z',
            id_factory=lambda: 'agenda-pending-observable',
        )
        conversation = {
            'id': 'conv-agenda-observability',
            'messages': [
                {
                    'role': 'assistant',
                    'content': 'Fixture Private Title',
                    'meta': {
                        'source': 'agenda_pending_proposal_response',
                        'reason_code': 'agenda_pending_action_created',
                        'agenda_schema_version': 'frida_agenda_agent_v1',
                        'agenda_product_method': 'propose_delete_event',
                        'agenda_pending_action_id': action.pending_action_id,
                        'agenda_pending_action_hash': action.action_hash,
                        'agenda_operation': 'delete',
                        'agenda_pending_status': 'pending',
                        'agenda_pending_expires_at': action.expires_at,
                        'agenda_confirmation_level': 'reinforced',
                        'agenda_risk_flags': ['family_calendar'],
                        'agenda_caldav_access': False,
                        'agenda_nextcloud_access': False,
                        'agenda_secret_access': False,
                        'agenda_mutation_attempted': False,
                        'content_free_meta': True,
                        'title': 'Fixture Private Title',
                        'location': 'Fixture Private Location',
                        'description': 'Fixture Private Description',
                        'uid': 'uid:fixture-private',
                        'etag': 'etag-fixture-private',
                        'caldav_path': '/remote.php/dav/calendars/tof/private/event.ics',
                        'raw_ics': 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nEND:VEVENT\nEND:VCALENDAR',
                        'authorization': 'Authorization: Bearer fixture',
                        'cookie': 'Cookie: fixture',
                        'app_password': 'fixture-app-password',
                    },
                },
                {
                    'role': 'user',
                    'content': 'Confirme',
                    'meta': {
                        pending_store.META_KEY: state.to_dict(),
                    },
                },
            ],
        }

        read_model = observability_read_model.build_admin_observability(conversation=conversation)

        self.assertEqual(read_model['schema_version'], observability_read_model.READ_MODEL_SCHEMA_VERSION)
        self.assertTrue(read_model['content_free'])
        self.assertTrue(read_model['redacted'])
        summary = read_model['conversation_summary']
        self.assertEqual(summary['pending_action_count'], 1)
        self.assertEqual(summary['operation_counts'], {'delete': 1})
        self.assertEqual(summary['pending_status_counts'], {'pending': 1})
        self.assertEqual(summary['confirmation_levels'], ['reinforced'])
        self.assertEqual(summary['risk_flags'], ['family_calendar'])
        self.assertEqual(
            summary['pending_actions'][0],
            {
                'pending_action_id': 'agenda-pending-observable',
                'action_hash': action.action_hash,
                'operation': 'delete',
                'confirmation_level': 'reinforced',
                'risk_flags': ['family_calendar'],
                'created_at': '2026-06-09T15:00:00Z',
                'expires_at': action.expires_at,
                'status': 'pending',
                'draft_private': True,
                'content_free': True,
            },
        )
        self.assert_content_free(read_model)

    def test_observability_payload_projection_ignores_raw_nested_payloads(self) -> None:
        event = {
            'stage': 'agenda',
            'status': 'ok',
            'ts': '2026-06-09T15:30:00Z',
            'payload': {
                'schema_version': 'frida_agenda_lot7a_confirmed_write_v1',
                'status': 'ok',
                'reason_code': 'agenda_write_delete_ok',
                'product_method': 'confirm_delete_event',
                'pending_action_id': 'agenda-pending-observable',
                'pending_action_hash': 'abc123def456',
                'pending_operation': 'delete',
                'confirmation_level': 'reinforced',
                'risk_flags': ['family_calendar'],
                'caldav_access': True,
                'nextcloud_access': True,
                'secret_access': True,
                'mutation_attempted': True,
                'final_response_override': True,
                'write_execution': {
                    'method_names': ['DELETE'],
                    'status': 'ok',
                    'reason_code': 'agenda_write_delete_ok',
                    'uid': 'uid:fixture-private',
                    'etag': 'etag-fixture-private',
                    'caldav_path': '/remote.php/dav/calendars/tof/private/event.ics',
                    'raw_ics': 'BEGIN:VEVENT',
                },
                'pending_execution': {
                    'pending_action_status': 'executed',
                },
                'title': 'Fixture Private Title',
                'location': 'Fixture Private Location',
                'description': 'Fixture Private Description',
                'authorization': 'Authorization: Bearer fixture',
                'cookie': 'Cookie: fixture',
                'app_password': 'fixture-app-password',
                'content_free': True,
            },
        }

        read_model = observability_read_model.build_admin_observability(log_events=[event])

        summary = read_model['event_summary']
        self.assertEqual(summary['event_count'], 1)
        self.assertEqual(summary['schema_versions'], ['frida_agenda_lot7a_confirmed_write_v1'])
        self.assertEqual(summary['reason_codes'], ['agenda_write_delete_ok'])
        self.assertEqual(summary['product_methods'], ['confirm_delete_event'])
        self.assertEqual(summary['write_method_names'], ['DELETE'])
        self.assertEqual(summary['operation_counts'], {'delete': 1})
        self.assertEqual(summary['pending_status_counts'], {'executed': 1})
        self.assertEqual(summary['confirmation_levels'], ['reinforced'])
        self.assertEqual(summary['risk_flags'], ['family_calendar'])
        self.assertEqual(summary['caldav_access_count'], 1)
        self.assertEqual(summary['nextcloud_access_count'], 1)
        self.assertEqual(summary['secret_access_count'], 1)
        self.assertEqual(summary['mutation_attempted_count'], 1)
        self.assertEqual(summary['final_response_override_count'], 1)
        self.assert_content_free(read_model)

    def test_sensitive_values_in_allowed_fields_are_dropped(self) -> None:
        projected = observability_projection.project_observability_payload(
            {
                'schema_version': 'frida_agenda_lot5_readonly_v1',
                'reason_code': 'BEGIN:VEVENT',
                'product_method': 'read_today',
                'read_tool_names': ['event_query_range', 'Authorization: Bearer fixture'],
                'pending_action_id': '/remote.php/dav/calendars/tof/private/event.ics',
                'content_free': True,
            }
        )

        self.assertEqual(projected['schema_version'], 'frida_agenda_lot5_readonly_v1')
        self.assertEqual(projected['reason_code'], '')
        self.assertEqual(projected['tool_names'], ['event_query_range'])
        self.assertEqual(projected['pending_action_id'], '')
        self.assert_content_free(projected)

    def test_projection_prefers_read_child_error_over_agent_active_ready(self) -> None:
        projected = observability_read_model.project_observability_payload(
            {
                'schema_version': 'frida_agenda_lot5_readonly_v1',
                'status': 'active_ready',
                'reason_code': 'agenda_agent_active_validated',
                'read_execution_status': 'error',
                'read_execution_reason_code': 'agenda_readonly_client_resolution_error',
                'read_execution': {
                    'status': 'error',
                    'reason_code': 'agenda_readonly_client_resolution_error',
                    'calendar_id_hashes': [],
                    'event_id_hashes': [],
                    'redacted': True,
                    'content_free': True,
                },
                'content_free': True,
            }
        )

        self.assertEqual(projected['status'], 'error')
        self.assertEqual(projected['reason_code'], 'agenda_readonly_client_resolution_error')
        self.assert_content_free(projected)

    def test_projection_prefers_pending_child_error_over_agent_active_ready(self) -> None:
        projected = observability_read_model.project_observability_payload(
            {
                'schema_version': 'frida_agenda_lot6_pending_v1',
                'status': 'active_ready',
                'reason_code': 'agenda_agent_active_validated',
                'pending_execution_status': 'error',
                'pending_execution_reason_code': 'agenda_pending_read_client_resolution_error',
                'pending_execution': {
                    'status': 'error',
                    'reason_code': 'agenda_pending_read_client_resolution_error',
                    'target_verification_tool_names': ['event_query_range'],
                    'target_verification_error_class': 'RuntimeError',
                    'write_execution': {},
                    'redacted': True,
                    'content_free': True,
                },
                'content_free': True,
            }
        )

        self.assertEqual(projected['status'], 'error')
        self.assertEqual(projected['reason_code'], 'agenda_pending_read_client_resolution_error')
        self.assert_content_free(projected)


if __name__ == '__main__':
    unittest.main()
