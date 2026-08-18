from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from agenda import agent_contract, agent_openrouter, client_resolution
from agenda.caldav_read_client import CalDavReadClient
from tests.support.agenda_runtime_golden import propose_create_payload


ACTIVE_SETTINGS = agent_contract.AgendaAgentSettings(
    mode=agent_contract.MODE_ACTIVE,
    caldav_secret_configured=True,
)


class _RuntimeSecretSettings:
    def __init__(self, value: str = "fixture-secret-value") -> None:
        self.value = value
        self.secret_reads = 0

    def get_runtime_secret_value(self, section, field):
        self.secret_reads += 1
        return SimpleNamespace(section=section, field=field, value=self.value)


class _ExplodingRuntimeSecretSettings:
    def get_runtime_secret_value(self, section, field):
        del section, field
        raise RuntimeError("RAW_SYNTHETIC_SECRET_FAILURE")


class AgendaClientResolutionTests(unittest.TestCase):
    def test_injected_clients_win_without_runtime_resolution(self) -> None:
        injected_model = object()
        injected_read = object()
        runtime_settings = _RuntimeSecretSettings()

        resolved_model = client_resolution.resolve_agent_model_client(
            settings=ACTIVE_SETTINGS,
            injected_client=injected_model,
            runtime_settings_module=runtime_settings,
            llm_module=None,
            requests_module=None,
            config_module=None,
        )
        resolved_read = client_resolution.resolve_read_client(
            settings=ACTIVE_SETTINGS,
            injected_client=injected_read,
            runtime_settings_module=runtime_settings,
            requests_module=None,
            config_module=None,
        )

        self.assertIs(resolved_model, injected_model)
        self.assertIs(resolved_read.client, injected_read)
        self.assertEqual(resolved_read.status, "ok")
        self.assertFalse(resolved_read.live_caldav)
        self.assertEqual(runtime_settings.secret_reads, 0)

    def test_default_model_client_is_built_only_from_complete_active_dependencies(self) -> None:
        requests_module = SimpleNamespace(post=lambda *args, **kwargs: None)
        runtime_settings = _RuntimeSecretSettings()

        resolved = client_resolution.resolve_agent_model_client(
            settings=ACTIVE_SETTINGS,
            runtime_settings_module=runtime_settings,
            llm_module=SimpleNamespace(),
            requests_module=requests_module,
            config_module=SimpleNamespace(),
        )

        self.assertIsInstance(resolved, agent_openrouter.OpenRouterAgendaAgentClient)
        self.assertIsNone(
            client_resolution.resolve_agent_model_client(
                settings=agent_contract.AgendaAgentSettings(
                    mode=agent_contract.MODE_OFF,
                    caldav_secret_configured=True,
                ),
                runtime_settings_module=runtime_settings,
                llm_module=SimpleNamespace(),
                requests_module=requests_module,
                config_module=SimpleNamespace(),
            )
        )

    def test_live_read_resolution_reads_secret_once_and_marks_live_client(self) -> None:
        runtime_settings = _RuntimeSecretSettings()

        resolved = client_resolution.resolve_read_client(
            settings=ACTIVE_SETTINGS,
            runtime_settings_module=runtime_settings,
            requests_module=SimpleNamespace(),
            config_module=SimpleNamespace(),
        )

        self.assertEqual(resolved.status, "ok")
        self.assertTrue(resolved.live_caldav)
        self.assertIsInstance(resolved.client, CalDavReadClient)
        self.assertEqual(runtime_settings.secret_reads, 1)

    def test_read_resolution_error_keeps_only_error_class_and_reason_code(self) -> None:
        resolved = client_resolution.resolve_read_client(
            settings=ACTIVE_SETTINGS,
            runtime_settings_module=_ExplodingRuntimeSecretSettings(),
            requests_module=SimpleNamespace(),
            config_module=SimpleNamespace(),
        )

        self.assertTrue(resolved.is_error)
        self.assertEqual(resolved.status, "error")
        self.assertEqual(resolved.reason_code, "agenda_readonly_client_resolution_error")
        self.assertEqual(resolved.error_class, "RuntimeError")
        self.assertNotIn("RAW_SYNTHETIC_SECRET_FAILURE", json.dumps(resolved.__dict__, sort_keys=True))

    def test_proposal_without_executable_resolution_path_never_reads_secret(self) -> None:
        validation = agent_contract.validate_agent_payload(
            propose_create_payload(),
            settings=ACTIVE_SETTINGS,
        )
        self.assertEqual(validation.status, agent_contract.STATUS_VALIDATED)
        self.assertIsNotNone(validation.plan)
        runtime_settings = _RuntimeSecretSettings()

        resolved = client_resolution.resolve_proposal_read_client(
            settings=ACTIVE_SETTINGS,
            plan=validation.plan,
            runtime_settings_module=runtime_settings,
            requests_module=SimpleNamespace(),
            config_module=SimpleNamespace(),
        )

        self.assertEqual(resolved.status, "unavailable")
        self.assertIsNone(resolved.client)
        self.assertFalse(resolved.live_caldav)
        self.assertEqual(runtime_settings.secret_reads, 0)


if __name__ == "__main__":
    unittest.main()
