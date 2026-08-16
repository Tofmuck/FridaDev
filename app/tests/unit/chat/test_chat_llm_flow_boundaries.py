from __future__ import annotations

import importlib
import importlib.util
import inspect
import unittest

from core import chat_llm_flow


_PROVIDER_DELEGATIONS = (
    'require_main_model_secret(',
    'prepare_provider_call(',
    'read_non_stream_provider_response(',
    'iter_stream_provider_content(',
    'emit_provider_response_observability(',
)
_FINALIZATION_DELEGATIONS = (
    'append_assistant_message(',
    'append_and_persist_assistant(',
    'persist_assistant_attempt(',
    'rollback_assistant_attempt(',
    'persist_user_turn_after_error(',
    'run_chat_post_persistence_effects(',
)
_FORBIDDEN_FLOW_OPERATIONS = (
    'requests_module.post(',
    'conv_store_module.append_message(',
    'conv_store_module.save_conversation(',
)


def _assert_boundary_source(
    testcase: unittest.TestCase,
    module_source: str,
    coordinator_source: str,
) -> None:
    for delegation in _PROVIDER_DELEGATIONS + _FINALIZATION_DELEGATIONS:
        testcase.assertIn(delegation, module_source)
    for low_level_operation in _FORBIDDEN_FLOW_OPERATIONS:
        testcase.assertNotIn(low_level_operation, module_source)
        testcase.assertNotIn(low_level_operation, coordinator_source)


class ChatLlmFlowBoundaryTests(unittest.TestCase):
    def test_named_boundaries_have_single_responsibility_owners(self) -> None:
        expected_owners = {
            'core.chat_llm_provider_exchange': _PROVIDER_DELEGATIONS,
            'core.chat_assistant_finalization': _FINALIZATION_DELEGATIONS,
        }
        missing_modules = [
            module_name
            for module_name in expected_owners
            if importlib.util.find_spec(module_name) is None
        ]
        self.assertEqual(missing_modules, [])

        for module_name, function_calls in expected_owners.items():
            module = importlib.import_module(module_name)
            for function_call in function_calls:
                function_name = function_call.removesuffix('(')
                with self.subTest(module=module_name, function=function_name):
                    function = getattr(module, function_name)
                    self.assertEqual(function.__module__, module_name)

    def test_flow_delegates_provider_and_persistence_mechanics(self) -> None:
        module_source = inspect.getsource(chat_llm_flow)
        coordinator_source = inspect.getsource(chat_llm_flow.run_llm_exchange)

        _assert_boundary_source(self, module_source, coordinator_source)

    def test_boundary_golden_rejects_removed_or_reintroduced_operations(self) -> None:
        canonical_source = '\n'.join(
            _PROVIDER_DELEGATIONS + _FINALIZATION_DELEGATIONS
        )
        _assert_boundary_source(self, canonical_source, canonical_source)

        for delegation in _PROVIDER_DELEGATIONS + _FINALIZATION_DELEGATIONS:
            with self.subTest(mutation='removed', delegation=delegation):
                mutated = canonical_source.replace(delegation, '', 1)
                with self.assertRaises(AssertionError):
                    _assert_boundary_source(self, mutated, mutated)
        for low_level_operation in _FORBIDDEN_FLOW_OPERATIONS:
            with self.subTest(mutation='reintroduced', operation=low_level_operation):
                mutated = canonical_source + '\n' + low_level_operation
                with self.assertRaises(AssertionError):
                    _assert_boundary_source(self, mutated, mutated)


if __name__ == '__main__':
    unittest.main()
