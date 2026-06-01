from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests


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

    def test_active_mode_calls_model_and_validates_json_without_using_response(self) -> None:
        fake = _FakeModelClient(_valid_json())
        result = agent.BiblioLibrarianAgent(fake).run(
            _request(settings=contract.BiblioLibrarianAgentSettings(mode=contract.MODE_ACTIVE, primary_model="model/x"))
        )

        self.assertEqual(result.status, agent.STATUS_ACTIVE_READY)
        self.assertEqual(result.reason_code, agent.REASON_ACTIVE_VALIDATED)
        self.assertFalse(result.used_for_response)
        self.assertTrue(result.model_called)
        self.assertTrue(result.fallback_deterministic)
        self.assertIsNotNone(result.candidate_plan)
        self.assertEqual(fake.calls, 1)

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

    def test_local_validation_rejects_payloads_outside_announced_schema(self) -> None:
        base = json.loads(_valid_json())
        cases = [
            ("extra_root", {**base, "extra": "oops"}, contract.REASON_SCHEMA_INVALID),
            ("missing_intent", {key: value for key, value in base.items() if key != "intent"}, contract.REASON_SCHEMA_INVALID),
            ("missing_answer_mode", {key: value for key, value in base.items() if key != "answer_mode"}, contract.REASON_SCHEMA_INVALID),
            ("bad_risk_flags_type", {**base, "risk_flags": "oops"}, contract.REASON_SCHEMA_INVALID),
            ("too_many_risk_flags", {**base, "risk_flags": [f"flag_{index}" for index in range(13)]}, contract.REASON_SCHEMA_INVALID),
            (
                "extra_call_key",
                {**base, "tool_calls": [{**base["tool_calls"][0], "extra": "oops"}]},
                contract.REASON_SCHEMA_INVALID,
            ),
            (
                "missing_call_method",
                {
                    **base,
                    "tool_calls": [
                        {key: value for key, value in base["tool_calls"][0].items() if key != "method"}
                    ],
                },
                contract.REASON_SCHEMA_INVALID,
            ),
            (
                "extra_param",
                {
                    **base,
                    "tool_calls": [
                        {"tool_name": tools.TOOL_CATALOG_LIST, "method": "GET", "params": {"limit": 10, "raw": "x"}}
                    ],
                },
                contract.REASON_TOOL_NOT_EXECUTABLE,
            ),
            (
                "huge_limit",
                {
                    **base,
                    "tool_calls": [
                        {"tool_name": tools.TOOL_CATALOG_LIST, "method": "GET", "params": {"limit": 999999}}
                    ],
                },
                contract.REASON_TOOL_NOT_EXECUTABLE,
            ),
            (
                "bad_param_type",
                {
                    **base,
                    "tool_calls": [
                        {"tool_name": tools.TOOL_CATALOG_LIST, "method": "GET", "params": {"limit": "10"}}
                    ],
                },
                contract.REASON_TOOL_NOT_EXECUTABLE,
            ),
        ]
        for name, payload, reason in cases:
            with self.subTest(name=name):
                validation = contract.validate_agent_payload(payload)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, reason)

    def test_local_validation_rejects_non_object_params_without_normalizing_to_empty(self) -> None:
        base = json.loads(_valid_json())
        for raw_params in [None, [], "", 0, False]:
            with self.subTest(params_type=type(raw_params).__name__):
                validation = contract.validate_agent_payload(
                    {
                        **base,
                        "tool_calls": [
                            {
                                "tool_name": tools.TOOL_CATALOG_LIST,
                                "method": "GET",
                                "params": raw_params,
                            }
                        ],
                    }
                )
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_SCHEMA_INVALID)

        validation = contract.validate_agent_payload(
            {
                **base,
                "tool_calls": [
                    {
                        "tool_name": tools.TOOL_CATALOG_LIST,
                        "method": "GET",
                        "params": {},
                    }
                ],
            }
        )
        self.assertEqual(validation.status, contract.STATUS_VALIDATED)

    def test_local_validation_rejects_tool_contract_mismatches_before_execution(self) -> None:
        base = json.loads(_valid_json())
        cases = [
            (
                "catalog_search_no_query",
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "method": "GET", "params": {}},
            ),
            (
                "document_toc_no_document_id",
                {"tool_name": tools.TOOL_DOCUMENT_TOC, "method": "GET", "params": {"limit": 10}},
            ),
            (
                "passage_context_no_position",
                {"tool_name": tools.TOOL_PASSAGE_CONTEXT, "method": "GET", "params": {"document_id": "doc-1"}},
            ),
            (
                "catalog_search_limit_too_high",
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "method": "GET", "params": {"query": "x", "limit": 500}},
            ),
            (
                "document_open_summary_limit_too_high",
                {"tool_name": tools.TOOL_DOCUMENT_OPEN_SUMMARY, "method": "GET", "params": {"document_id": "doc-1", "limit": 500}},
            ),
            (
                "locate_limit_too_high",
                {"tool_name": tools.TOOL_LOCATE, "method": "GET", "params": {"document_id": "doc-1", "locator": "126b", "limit": 500}},
            ),
            (
                "catalog_search_offset_disallowed",
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "method": "GET", "params": {"query": "x", "offset": 10}},
            ),
        ]
        for name, call in cases:
            with self.subTest(name=name):
                validation = contract.validate_agent_payload({**base, "tool_calls": [call]})
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)

    def test_local_validation_accepts_tool_contract_valid_cases(self) -> None:
        base = json.loads(_valid_json())
        cases = [
            {
                "tool_name": tools.TOOL_CATALOG_SEARCH,
                "method": "GET",
                "params": {"query": "x", "limit": 50, "offset": 0},
            },
            {
                "tool_name": tools.TOOL_DOCUMENT_TOC,
                "method": "GET",
                "params": {"document_id": "doc-1", "limit": 500},
            },
            {
                "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                "method": "GET",
                "params": {"document_id": "doc-1", "paragraph_id": 123, "window_chars": 700},
            },
        ]
        for call in cases:
            with self.subTest(tool=call["tool_name"]):
                validation = contract.validate_agent_payload({**base, "tool_calls": [call]})
                self.assertEqual(validation.status, contract.STATUS_VALIDATED)

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
                attempt_count=1,
            ),
            openrouter.BiblioLibrarianAgentModelResponse(
                status=openrouter.STATUS_ERROR,
                reason_code=openrouter.REASON_PROVIDER_ERROR,
                status_code=502,
                attempt_count=1,
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
                self.assertTrue(result.model_called)

    def test_no_model_or_provider_key_does_not_claim_model_called(self) -> None:
        for response in [
            openrouter.BiblioLibrarianAgentModelResponse(
                status=openrouter.STATUS_ERROR,
                reason_code=openrouter.REASON_MODEL_NOT_CONFIGURED,
                attempt_count=0,
            ),
            openrouter.BiblioLibrarianAgentModelResponse(
                status=openrouter.STATUS_ERROR,
                reason_code=openrouter.REASON_PROVIDER_NOT_CONFIGURED,
                attempt_count=0,
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
                self.assertFalse(result.model_called)

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

    def test_product_fixtures_are_transmitted_to_model_context_without_regex_runtime_claim(self) -> None:
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
                        recent_dialogue=(
                            {"role": "user", "content": RAW_DIALOGUE},
                            {"role": "assistant", "content": "assistant state"},
                        ),
                        biblio_state={"present": True, "last_result": {"doc_id_short": "abc123"}},
                        settings=contract.BiblioLibrarianAgentSettings(
                            mode=contract.MODE_SHADOW,
                            primary_model="model/x",
                        ),
                    )
                )
                self.assertEqual(result.status, agent.STATUS_SHADOW_READY)
                self.assertEqual(fake.calls, 1)
                self.assertEqual(fake.requests[0].user_message, sample)
                payload = openrouter.build_librarian_agent_payload(fake.requests[0])
                model_context = json.loads(payload["messages"][1]["content"])
                self.assertEqual(model_context["current_user_message"], sample)
                self.assertEqual(len(model_context["recent_dialogue"]), 2)
                self.assertIn(tools.TOOL_CATALOG_SEARCH, model_context["available_tools"])
                self.assertTrue(model_context["biblio_state"]["present"])
                self.assertNotIn(sample, _json(result.to_observability()))

    def test_response_format_is_strict_json_schema(self) -> None:
        response_format = openrouter.build_librarian_agent_response_format(max_tool_calls=2)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(response_format["json_schema"]["name"], contract.SCHEMA_VERSION)
        self.assertFalse(response_format["json_schema"]["schema"]["additionalProperties"])
        tool_items = response_format["json_schema"]["schema"]["properties"]["tool_calls"]["items"]
        self.assertEqual(len(tool_items["oneOf"]), len(tools.LOT3_TOOL_NAMES))
        catalog_search = next(
            item for item in tool_items["oneOf"] if item["properties"]["tool_name"]["enum"] == [tools.TOOL_CATALOG_SEARCH]
        )
        params = catalog_search["properties"]["params"]
        self.assertFalse(params["additionalProperties"])
        self.assertEqual(params["properties"]["limit"]["maximum"], 50)
        self.assertEqual(params["properties"]["offset"]["maximum"], 0)

    def test_settings_from_config_keeps_json_contract_required_without_operator_disable(self) -> None:
        settings = contract.BiblioLibrarianAgentSettings.from_config(
            SimpleNamespace(
                BIBLIO_LIBRARIAN_AGENT_MODE="shadow",
                BIBLIO_LIBRARIAN_AGENT_MODEL="deepseek/deepseek-v4-pro",
                BIBLIO_LIBRARIAN_AGENT_REQUIRE_PARAMETERS="false",
                BIBLIO_LIBRARIAN_AGENT_REASONING_EFFORT="high",
            )
        )

        self.assertEqual(settings.mode, contract.MODE_SHADOW)
        self.assertEqual(settings.primary_model, "deepseek/deepseek-v4-pro")
        self.assertEqual(settings.reasoning_effort, "high")
        self.assertTrue(settings.to_observability()["json_contract_required"])
        self.assertTrue(settings.to_observability()["require_parameters"])
        self.assertEqual(settings.to_observability()["reasoning_effort"], "high")

    def test_openrouter_payload_uses_biblio_headers_and_required_parameters(self) -> None:
        settings = contract.BiblioLibrarianAgentSettings.from_config(
            SimpleNamespace(
                BIBLIO_LIBRARIAN_AGENT_MODE="shadow",
                BIBLIO_LIBRARIAN_AGENT_MODEL="deepseek/deepseek-v4-pro",
                BIBLIO_LIBRARIAN_AGENT_REQUIRE_PARAMETERS="false",
                BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS=1,
                BIBLIO_LIBRARIAN_AGENT_TIMEOUT_S=120,
                BIBLIO_LIBRARIAN_AGENT_MAX_TOKENS=16000,
                BIBLIO_LIBRARIAN_AGENT_REASONING_EFFORT="high",
            )
        )
        payload = openrouter.build_librarian_agent_payload(_request(settings=settings), settings=settings)

        self.assertEqual(payload["model"], "deepseek/deepseek-v4-pro")
        self.assertEqual(payload["max_tokens"], 16000)
        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["top_p"], 1.0)
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertEqual(payload["provider"], {"require_parameters": True})
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(len(payload["messages"]), 2)

    def test_openrouter_payload_omits_reasoning_effort_when_disabled(self) -> None:
        settings = contract.BiblioLibrarianAgentSettings(
            mode=contract.MODE_ACTIVE,
            primary_model="model/x",
            reasoning_effort="none",
        )
        payload = openrouter.build_librarian_agent_payload(_request(settings=settings), settings=settings)

        self.assertNotIn("reasoning_effort", payload)

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
        self.assertEqual(response.attempt_count, 0)

        response = client.complete(
            _request(
                settings=contract.BiblioLibrarianAgentSettings(
                    mode=contract.MODE_SHADOW,
                    primary_model="model/x",
                )
            )
        )

        self.assertEqual(response.reason_code, openrouter.REASON_PROVIDER_NOT_CONFIGURED)
        self.assertFalse(called["value"])
        self.assertEqual(response.attempt_count, 0)

    def test_openrouter_client_uses_fallback_model_when_budget_allows(self) -> None:
        calls: list[str] = []

        def fake_post(*_args: Any, **kwargs: Any) -> _FakeHTTPResponse:
            calls.append(kwargs["json"]["model"])
            if len(calls) == 1:
                raise requests.Timeout()
            return _FakeHTTPResponse(
                {
                    "model": "fallback/model",
                    "choices": [
                        {"message": {"content": _valid_json()}, "finish_reason": "stop"},
                    ],
                }
            )

        client = openrouter.OpenRouterBiblioLibrarianAgentClient(
            requests_post=fake_post,
            config_module=_provider_config(),
            monotonic=_FakeClock(),
        )
        response = client.complete(
            _request(
                settings=contract.BiblioLibrarianAgentSettings(
                    mode=contract.MODE_SHADOW,
                    primary_model="primary/model",
                    fallback_model="fallback/model",
                    max_model_calls=2,
                )
            )
        )

        self.assertEqual(response.status, openrouter.STATUS_OK)
        self.assertEqual(calls, ["primary/model", "fallback/model"])
        self.assertTrue(response.fallback_model_used)
        self.assertEqual(response.attempt_count, 2)
        self.assertEqual(response.primary_reason_code, openrouter.REASON_TIMEOUT)

    def test_openrouter_client_does_not_use_fallback_when_model_call_budget_is_one(self) -> None:
        calls: list[str] = []

        def fake_post(*_args: Any, **kwargs: Any) -> _FakeHTTPResponse:
            calls.append(kwargs["json"]["model"])
            raise requests.Timeout()

        client = openrouter.OpenRouterBiblioLibrarianAgentClient(
            requests_post=fake_post,
            config_module=_provider_config(),
            monotonic=_FakeClock(),
        )
        response = client.complete(
            _request(
                settings=contract.BiblioLibrarianAgentSettings(
                    mode=contract.MODE_SHADOW,
                    primary_model="primary/model",
                    fallback_model="fallback/model",
                    max_model_calls=1,
                )
            )
        )

        self.assertEqual(response.status, openrouter.STATUS_ERROR)
        self.assertEqual(response.reason_code, openrouter.REASON_TIMEOUT)
        self.assertEqual(response.attempt_count, 1)
        self.assertFalse(response.fallback_model_used)
        self.assertEqual(calls, ["primary/model"])


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
        self.requests: list[contract.BiblioLibrarianAgentRequest] = []

    def complete(self, *_args: Any, **_kwargs: Any) -> openrouter.BiblioLibrarianAgentModelResponse:
        self.calls += 1
        if _args:
            self.requests.append(_args[0])
        if self._response is not None:
            return self._response
        return openrouter.BiblioLibrarianAgentModelResponse(
            status=openrouter.STATUS_OK,
            reason_code=openrouter.REASON_OK,
            content=self._content,
            model_effective="model/x",
            finish_reason=self._finish_reason,
            response_chars=len(self._content),
            attempt_count=1,
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


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClock:
    def __init__(self) -> None:
        self._value = 100.0

    def __call__(self) -> float:
        self._value += 0.01
        return self._value


def _provider_config() -> SimpleNamespace:
    return SimpleNamespace(
        OR_KEY="secret",
        OR_BASE="https://openrouter.ai/api/v1",
        OR_REFERER_BIBLIO_LIBRARIAN="https://fridadev.frida-system.fr/openrouter/biblio-librarian",
        OR_TITLE_BIBLIO_LIBRARIAN="FridaDev / Biblio Librarian Agent",
    )


if __name__ == "__main__":
    unittest.main()
