from __future__ import annotations

import json
import unittest

from agenda import observability_projection, observability_read_model, pending_store


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
                'pending_action_status': 'executed',
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
