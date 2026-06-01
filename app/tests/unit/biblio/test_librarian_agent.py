from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import librarian_agent as agent
from biblio import librarian_agent_contract as contract
from biblio import librarian_agent_openrouter as openrouter
from biblio import librarian_tools as tools


RAW_USER = "RAW USER QUERY MUST NOT LEAK"
RAW_DIALOGUE = "RAW DIALOGUE TURN MUST NOT LEAK"
RAW_TITLE = "RAW TITLE MUST NOT LEAK"
RAW_PASSAGE = "RAW PASSAGE MUST NOT LEAK"


class BiblioLibrarianAgentTests(unittest.TestCase):
    def test_off_mode_does_not_call_model(self) -> None:
        fake = _FakeModelClient(_valid_json())
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_OFF))
        )

        self.assertEqual(result.status, agent.STATUS_SKIPPED)
        self.assertEqual(result.reason_code, agent.REASON_MODE_OFF)
        self.assertFalse(result.model_called)
        self.assertEqual(fake.calls, 0)

    def test_shadow_mode_validates_json_without_using_response(self) -> None:
        fake = _FakeModelClient(_valid_json(tool_name=tools.TOOL_CATALOG_SEARCH, params={"query": RAW_TITLE}))
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_SHADOW, primary_model="model/x"))
        )
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(result.status, agent.STATUS_SHADOW_READY)
        self.assertEqual(result.reason_code, agent.REASON_SHADOW_VALIDATED)
        self.assertTrue(result.model_called)
        self.assertFalse(result.used_for_response)
        self.assertTrue(result.fallback_deterministic)
        self.assertEqual(fake.calls, 1)
        self.assertIn(tools.TOOL_CATALOG_SEARCH, observed["validation"]["tool_names"])
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_USER, encoded)
        self.assertNotIn(RAW_DIALOGUE, encoded)

    def test_candidate_mode_keeps_deterministic_path_as_controller(self) -> None:
        fake = _FakeModelClient(_valid_json())
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_CANDIDATE, primary_model="model/x"))
        )

        self.assertEqual(result.status, agent.STATUS_CANDIDATE_READY)
        self.assertEqual(result.reason_code, agent.REASON_CANDIDATE_VALIDATED)
        self.assertFalse(result.used_for_response)
        self.assertTrue(result.fallback_deterministic)
        self.assertIsNotNone(result.candidate_plan)

    def test_active_mode_is_not_enabled_by_lot_7(self) -> None:
        fake = _FakeModelClient(_valid_json())
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_ACTIVE, primary_model="model/x"))
        )

        self.assertEqual(result.status, agent.STATUS_FALLBACK_DETERMINISTIC)
        self.assertEqual(result.reason_code, agent.REASON_ACTIVE_NOT_ENABLED)
        self.assertFalse(result.used_for_response)

    def test_invalid_json_and_free_text_fall_back(self) -> None:
        cases = [
            ("{not-json", contract.REASON_JSON_INVALID),
            ("voici mon plan en prose", contract.REASON_JSON_FREE_TEXT),
        ]
        for raw, reason in cases:
            with self.subTest(reason=reason):
                fake = _FakeModelClient(raw)
                result = agent.BiblioLibrarianAgent(fake).run(
                    _request(
                        settings=contract.BiblioLibrarianAgentSettings(
                            mode=contract.MODE_SHADOW,
                            primary_model="model/x",
                        )
                    )
                )
                self.assertEqual(result.status, agent.STATUS_FALLBACK_DETERMINISTIC)
                self.assertEqual(result.reason_code, reason)

    def test_truncated_output_falls_back(self) -> None:
        fake = _FakeModelClient(_valid_json(), finish_reason="length")
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_SHADOW, primary_model="model/x"))
        )

        self.assertEqual(result.status, agent.STATUS_FALLBACK_DETERMINISTIC)
        self.assertEqual(result.reason_code, contract.REASON_JSON_TRUNCATED)

    def test_forbidden_unknown_and_mutating_tool_are_rejected(self) -> None:
        cases = [
            (_valid_json(tool_name="latest/page"), contract.REASON_TOOL_FORBIDDEN),
            (_valid_json(tool_name="page_read"), contract.REASON_TOOL_FORBIDDEN),
            (_valid_json(tool_name="made_up_tool"), contract.REASON_TOOL_UNKNOWN),
            (_valid_json(method="POST"), contract.REASON_METHOD_FORBIDDEN),
        ]
        for raw, reason in cases:
            with self.subTest(reason=reason):
                result = agent.BiblioLibrarianAgent(_FakeModelClient(raw)).run(
                    _request(
                        settings=contract.BiblioLibrarianAgentSettings(
                            mode=contract.MODE_SHADOW,
                            primary_model="model/x",
                        )
                    )
                )
                self.assertEqual(result.status, agent.STATUS_FALLBACK_DETERMINISTIC)
                self.assertEqual(result.reason_code, reason)

    def test_budget_exceeded_before_and_after_model_call(self) -> None:
        no_model_budget = agent.BiblioLibrarianAgent(_FakeModelClient(_valid_json())).run(
            _request(
                settings=contract.BiblioLibrarianAgentSettings(
                    mode=contract.MODE_SHADOW,
                    primary_model="model/x",
                    max_model_calls=0,
                )
            )
        )
        self.assertEqual(no_model_budget.reason_code, agent.REASON_MODEL_CALL_BUDGET_EXHAUSTED)

        tool_budget = agent.BiblioLibrarianAgent(_FakeModelClient(_valid_json(tool_count=2))).run(
            _request(
                settings=contract.BiblioLibrarianAgentSettings(
                    mode=contract.MODE_SHADOW,
                    primary_model="model/x",
                    max_tool_calls=1,
                )
            )
        )
        self.assertEqual(tool_budget.reason_code, contract.REASON_BUDGET_EXCEEDED)

    def test_timeout_and_provider_errors_fall_back(self) -> None:
        for response in [
            openrouter.BiblioLibrarianAgentModelResponse(
                status=openrouter.STATUS_ERROR,
                reason_code=openrouter.REASON_TIMEOUT,
            ),
            openrouter.BiblioLibrarianAgentModelResponse(
                status=openrouter.STATUS_ERROR,
                reason_code=openrouter.REASON_PROVIDER_ERROR,
                status_code=502,
            ),
        ]:
            with self.subTest(reason=response.reason_code):
                result = agent.BiblioLibrarianAgent(_FakeModelClient(response=response)).run(
                    _request(
                        settings=contract.BiblioLibrarianAgentSettings(
                            mode=contract.MODE_SHADOW,
                            primary_model="model/x",
                        )
                    )
                )
                self.assertEqual(result.status, agent.STATUS_FALLBACK_DETERMINISTIC)
                self.assertEqual(result.reason_code, response.reason_code)

    def test_recent_dialogue_is_bounded_and_observable_without_content(self) -> None:
        request = _request(
            recent_dialogue=tuple({"role": "user", "content": f"{RAW_DIALOGUE} {index}"} for index in range(8)),
            settings=contract.BiblioLibrarianAgentSettings(max_recent_turns=3),
        )
        observed = request.to_observability()

        self.assertEqual(len(request.bounded_recent_dialogue()), 3)
        self.assertEqual(observed["bounded_recent_dialogue_count"], 3)
        self.assertNotIn(RAW_DIALOGUE, _json(observed))
        self.assertNotIn(RAW_USER, _json(observed))

    def test_repr_and_observability_are_content_free(self) -> None:
        fake = _FakeModelClient(_valid_json(params={"query": RAW_TITLE}))
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(
                biblio_state={"raw_title": RAW_TITLE, "raw_passage": RAW_PASSAGE},
                settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_SHADOW, primary_model="model/x"),
            )
        )
        encoded = _json(result.to_observability()) + repr(result)

        for marker in [RAW_USER, RAW_DIALOGUE, RAW_TITLE, RAW_PASSAGE]:
            self.assertNotIn(marker, encoded)

    def test_product_fixtures_can_be_handled_by_structured_agent_without_regex_runtime(self) -> None:
        samples = [
            "Tu peux me reprendre le passage dont on parlait ?",
            "Dans le même ouvrage, cherche le passage sur la maïeutique.",
            "Non, pas celui-là, plutôt celui où Socrate parle comme une sage-femme.",
            "Donne-moi la table des matières du livre dont on parle.",
            "Retrouve le passage juste avant celui-ci.",
        ]
        for sample in samples:
            with self.subTest(input_len=len(sample)):
                fake = _FakeModelClient(_valid_json())
                result = agent.BiblioLibrarianAgent(fake).run(
                    _request(
                        user_message=sample,
                        settings=contract.BiblioLibrarianAgentSettings(
                            mode=contract.MODE_SHADOW,
                            primary_model="model/x",
                        ),
                    )
                )
                self.assertEqual(result.status, agent.STATUS_SHADOW_READY)
                self.assertEqual(fake.calls, 1)

    def test_response_format_is_strict_json_schema(self) -> None:
        response_format = openrouter.build_librarian_agent_response_format(max_tool_calls=2)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(response_format["json_schema"]["name"], contract.SCHEMA_VERSION)
        self.assertFalse(response_format["json_schema"]["schema"]["additionalProperties"])

    def test_settings_from_config_keeps_agent_off_and_parses_booleans(self) -> None:
        settings = contract.BiblioLibrarianAgentSettings.from_config(
            SimpleNamespace(
                BIBLIO_LIBRARIAN_AGENT_MODE="shadow",
                BIBLIO_LIBRARIAN_AGENT_MODEL="deepseek/deepseek-v4-pro",
                BIBLIO_LIBRARIAN_AGENT_JSON_CONTRACT_ENABLED="0",
                BIBLIO_LIBRARIAN_AGENT_REQUIRE_PARAMETERS="false",
            )
        )

        self.assertEqual(settings.mode, contract.MODE_SHADOW)
        self.assertEqual(settings.primary_model, "deepseek/deepseek-v4-pro")
        self.assertFalse(settings.json_contract_enabled)
        self.assertFalse(settings.require_parameters)

    def test_openrouter_payload_uses_biblio_headers_and_required_parameters(self) -> None:
        settings = contract.BiblioLibrarianAgentSettings(
            mode=contract.MODE_SHADOW,
            primary_model="deepseek/deepseek-v4-pro",
            max_recent_turns=1,
        )
        payload = openrouter.build_librarian_agent_payload(_request(settings=settings), settings=settings)

        self.assertEqual(payload["model"], "deepseek/deepseek-v4-pro")
        self.assertEqual(payload["provider"], {"require_parameters": True})
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(len(payload["messages"]), 2)

    def test_openrouter_client_does_not_call_without_model_or_key(self) -> None:
        called = {"value": False}

        def fake_post(*_args: Any, **_kwargs: Any) -> None:
            called["value"] = True

        client = openrouter.OpenRouterBiblioLibrarianAgentClient(
            requests_post=fake_post,
            config_module=SimpleNamespace(OR_KEY="", OR_BASE="https://openrouter.ai/api/v1"),
        )
        response = client.complete(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_SHADOW))
        )

        self.assertEqual(response.reason_code, openrouter.REASON_MODEL_NOT_CONFIGURED)
        self.assertFalse(called["value"])


class _FakeModelClient:
    def __init__(
        self,
        content: str = "",
        *,
        response: openrouter.BiblioLibrarianAgentModelResponse | None = None,
        finish_reason: str = "stop",
    ) -> None:
        self._content = content
        self._response = response
        self._finish_reason = finish_reason
        self.calls = 0

    def complete(self, *_args: Any, **_kwargs: Any) -> openrouter.BiblioLibrarianAgentModelResponse:
        self.calls += 1
        if self._response is not None:
            return self._response
        return openrouter.BiblioLibrarianAgentModelResponse(
            status=openrouter.STATUS_OK,
            reason_code=openrouter.REASON_OK,
            content=self._content,
            model_effective="model/x",
            finish_reason=self._finish_reason,
            response_chars=len(self._content),
        )


def _request(
    *,
    user_message: str = RAW_USER,
    recent_dialogue: tuple[dict[str, Any], ...] = ({"role": "user", "content": RAW_DIALOGUE},),
    biblio_state: Any = None,
    settings: contract.BiblioLibrarianAgentSettings | None = None,
) -> contract.BiblioLibrarianAgentRequest:
    return contract.BiblioLibrarianAgentRequest(
        user_message=user_message,
        recent_dialogue=recent_dialogue,
        biblio_state=biblio_state,
        deterministic_plan={"status": "deterministic"},
        settings=settings or contract.BiblioLibrarianAgentSettings(),
    )


def _valid_json(
    *,
    tool_name: str = tools.TOOL_CATALOG_LIST,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    tool_count: int = 1,
) -> str:
    tool_calls = [
        {"tool_name": tool_name, "method": method, "params": dict(params or {"limit": 10})}
        for _ in range(tool_count)
    ]
    return json.dumps(
        {
            "schema_version": contract.SCHEMA_VERSION,
            "intent": "list_catalog",
            "tool_calls": tool_calls,
            "answer_mode": "catalog_list",
            "risk_flags": [],
            "fallback_reason": "",
        },
        ensure_ascii=False,
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
