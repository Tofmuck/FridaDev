from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import summarizer
import config


class _SummaryStorageDouble:
    def __init__(self, *, fail_summary_write: bool = False, fail_trace_update: bool = False) -> None:
        self.fail_summary_write = fail_summary_write
        self.fail_trace_update = fail_trace_update
        self.summary_rows: dict[str, dict[str, object]] = {}
        self.connection_attempts = 0
        self.trace_update_attempts = 0

    def connection(self):
        self.connection_attempts += 1
        storage = self

        class Cursor:
            def __init__(self) -> None:
                self.row = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params):
                compact_sql = ' '.join(str(sql).split())
                if compact_sql.startswith('INSERT INTO summaries'):
                    if storage.fail_summary_write:
                        raise RuntimeError('SYNTHETIC_WRITER_DB_DIAGNOSTIC')
                    summary_id, conversation_id, start_ts, end_ts, content, embedding = params
                    already_present = str(summary_id) in storage.summary_rows
                    storage.summary_rows.setdefault(
                        str(summary_id),
                        {
                            'id': str(summary_id),
                            'conversation_id': str(conversation_id),
                            'start_ts': start_ts,
                            'end_ts': end_ts,
                            'content': str(content),
                            'embedding': embedding,
                        },
                    )
                    self.row = None if already_present else (str(summary_id),)
                    return
                if compact_sql.startswith('UPDATE traces'):
                    storage.trace_update_attempts += 1
                    if storage.fail_trace_update:
                        raise RuntimeError('SYNTHETIC_TRACE_LINK_DIAGNOSTIC')
                    return
                if compact_sql.startswith('SELECT 1 FROM summaries'):
                    summary_id, conversation_id, start_ts, end_ts, content = params
                    existing = storage.summary_rows.get(str(summary_id))
                    self.row = (1,) if existing and (
                        existing['conversation_id'] == str(conversation_id)
                        and existing['start_ts'] == start_ts
                        and existing['end_ts'] == end_ts
                        and existing['content'] == str(content)
                    ) else None
                    return
                if 'FROM summaries' in compact_sql:
                    conversation_id = str(params[0])
                    candidates = [
                        row for row in storage.summary_rows.values()
                        if row['conversation_id'] == conversation_id
                    ]
                    self.row = dict(candidates[-1]) if candidates else None
                    return
                raise AssertionError(f'unexpected SQL in summary storage double: {compact_sql}')

            def fetchone(self):
                return self.row

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, **_kwargs):
                return Cursor()

            def commit(self):
                return None

        return Connection()


class SummarizerPhase4ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _conversation(self):
        return {
            'id': 'conv-test',
            'messages': [
                {'role': 'user', 'content': 'message un ' * 120, 'timestamp': '2026-03-24T10:00:00Z'},
                {'role': 'assistant', 'content': 'reponse un ' * 120, 'timestamp': '2026-03-24T10:01:00Z'},
                {'role': 'user', 'content': 'message deux ' * 120, 'timestamp': '2026-03-24T10:02:00Z'},
                {'role': 'assistant', 'content': 'reponse deux ' * 120, 'timestamp': '2026-03-24T10:03:00Z'},
            ],
        }

    def test_maybe_summarize_threshold_counts_only_unsummarized_dialogue(self) -> None:
        observed = {'messages': None}
        original_estimate_tokens = summarizer.estimate_tokens
        original_threshold = config.SUMMARY_THRESHOLD_TOKENS

        def fake_estimate_tokens(messages, model):
            observed['messages'] = [dict(message) for message in messages]
            return 0

        conversation = {
            'id': 'conv-dialogue-only',
            'messages': [
                {'role': 'system', 'content': 'SYSTEM ' * 10000, 'timestamp': '2026-03-24T09:00:00Z'},
                {'role': 'user', 'content': 'deja resume', 'timestamp': '2026-03-24T09:10:00Z', 'summarized_by': 'summary-old'},
                {'role': 'assistant', 'content': 'deja resume aussi', 'timestamp': '2026-03-24T09:11:00Z', 'summarized_by': 'summary-old'},
                {'role': 'user', 'content': 'message courant', 'timestamp': '2026-03-24T10:00:00Z'},
                {'role': 'assistant', 'content': 'reponse courante', 'timestamp': '2026-03-24T10:01:00Z'},
            ],
        }

        summarizer.estimate_tokens = fake_estimate_tokens
        config.SUMMARY_THRESHOLD_TOKENS = 1
        try:
            changed = summarizer.maybe_summarize(conversation, 'token-model')
        finally:
            summarizer.estimate_tokens = original_estimate_tokens
            config.SUMMARY_THRESHOLD_TOKENS = original_threshold

        self.assertFalse(changed)
        self.assertEqual(
            observed['messages'],
            [
                {'role': 'user', 'content': 'message courant'},
                {'role': 'assistant', 'content': 'reponse courante'},
            ],
        )

    def test_maybe_summarize_marks_old_messages_and_keeps_recent_turns_unsummarized(self) -> None:
        original_estimate_tokens = summarizer.estimate_tokens
        original_summarize_conversation = summarizer.summarize_conversation
        original_get_settings = summarizer.runtime_settings.get_summary_model_settings
        original_threshold = config.SUMMARY_THRESHOLD_TOKENS
        original_keep_turns = config.SUMMARY_KEEP_TURNS

        import memory.memory_store as memory_store
        original_save_summary = memory_store.save_summary
        original_update_summary_id = memory_store.update_traces_summary_id

        conversation = self._conversation()
        summarizer.estimate_tokens = lambda _messages, _model: 999
        summarizer.summarize_conversation = lambda _turns: 'resume test'
        summarizer.runtime_settings.get_summary_model_settings = lambda: runtime_settings.RuntimeSectionView(
            section='summary_model',
            payload=runtime_settings.build_env_seed_bundle('summary_model').payload,
            source='env',
            source_reason='test',
        )
        memory_store.save_summary = lambda conv_id, summary_entry: True
        memory_store.update_traces_summary_id = lambda conv_id, summary_id, start_ts, end_ts: None
        config.SUMMARY_THRESHOLD_TOKENS = 1
        config.SUMMARY_KEEP_TURNS = 1
        try:
            changed = summarizer.maybe_summarize(conversation, 'token-model')
        finally:
            summarizer.estimate_tokens = original_estimate_tokens
            summarizer.summarize_conversation = original_summarize_conversation
            summarizer.runtime_settings.get_summary_model_settings = original_get_settings
            memory_store.save_summary = original_save_summary
            memory_store.update_traces_summary_id = original_update_summary_id
            config.SUMMARY_THRESHOLD_TOKENS = original_threshold
            config.SUMMARY_KEEP_TURNS = original_keep_turns

        self.assertTrue(changed)
        first_summary_id = conversation['messages'][0].get('summarized_by')
        self.assertTrue(first_summary_id)
        self.assertEqual(conversation['messages'][1].get('summarized_by'), first_summary_id)
        self.assertNotIn('summarized_by', conversation['messages'][2])
        self.assertNotIn('summarized_by', conversation['messages'][3])

    def test_maybe_summarize_calls_summarize_conversation_without_model_argument(self) -> None:
        observed = {'arg_count': None, 'turn_count': None}
        original_summarize_conversation = summarizer.summarize_conversation
        original_save_summary = None
        original_update_summary_id = None
        original_threshold = config.SUMMARY_THRESHOLD_TOKENS
        original_keep_turns = config.SUMMARY_KEEP_TURNS

        def fake_summarize_conversation(*args):
            observed['arg_count'] = len(args)
            observed['turn_count'] = len(args[0])
            return 'resume test'

        import memory.memory_store as memory_store
        original_save_summary = memory_store.save_summary
        original_update_summary_id = memory_store.update_traces_summary_id
        memory_store.save_summary = lambda conv_id, summary_entry: True
        memory_store.update_traces_summary_id = lambda conv_id, summary_id, start_ts, end_ts: None
        config.SUMMARY_THRESHOLD_TOKENS = 1
        config.SUMMARY_KEEP_TURNS = 1
        summarizer.summarize_conversation = fake_summarize_conversation
        try:
            changed = summarizer.maybe_summarize(self._conversation(), 'token-model')
        finally:
            summarizer.summarize_conversation = original_summarize_conversation
            memory_store.save_summary = original_save_summary
            memory_store.update_traces_summary_id = original_update_summary_id
            config.SUMMARY_THRESHOLD_TOKENS = original_threshold
            config.SUMMARY_KEEP_TURNS = original_keep_turns

        self.assertTrue(changed)
        self.assertEqual(observed['arg_count'], 1)
        self.assertEqual(observed['turn_count'], 2)

    def test_missing_summary_prompt_skips_provider_and_preserves_conversation(self) -> None:
        conversation = self._conversation()
        before = copy.deepcopy(conversation)

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer.prompt_loader, 'get_summary_system_prompt', return_value='  \n'),
            patch.object(
                summarizer,
                '_runtime_summary_settings',
                side_effect=AssertionError('runtime settings must not be read'),
            ) as runtime_settings_read,
            patch.object(
                summarizer.llm_client,
                'or_chat_completions_url',
                side_effect=AssertionError('provider URL must not be resolved'),
            ) as provider_url,
            patch.object(
                summarizer.requests,
                'post',
                side_effect=AssertionError('summary provider must not run'),
            ) as provider_post,
            self.assertLogs('frida.summarizer', level='WARNING') as captured,
        ):
            changed = summarizer.maybe_summarize(conversation, 'token-model')

        self.assertFalse(changed)
        provider_post.assert_not_called()
        provider_url.assert_not_called()
        runtime_settings_read.assert_not_called()
        self.assertEqual(conversation, before)
        rendered_logs = '\n'.join(captured.output)
        self.assertIn('reason=prompt_missing', rendered_logs)
        self.assertIn('prompt_id=summary_system', rendered_logs)
        self.assertNotIn('summary provider must not run', rendered_logs)

    def test_transport_failure_log_omits_exception_text_and_preserves_fallback(self) -> None:
        marker = 'SYNTHETIC_SUMMARY_TRANSPORT_DETAIL'
        conversation = self._conversation()
        before = copy.deepcopy(conversation)

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(
                summarizer,
                'summarize_conversation',
                side_effect=summarizer.requests.exceptions.InvalidHeader(marker),
            ),
            self.assertLogs('frida.summarizer', level='ERROR') as captured,
        ):
            changed = summarizer.maybe_summarize(conversation, 'token-model')

        rendered_logs = '\n'.join(captured.output)
        self.assertFalse(changed)
        self.assertEqual(conversation, before)
        self.assertIn('reason=provider_transport_error', rendered_logs)
        self.assertIn('err_class=InvalidHeader', rendered_logs)
        self.assertNotIn(marker, rendered_logs)

    def test_local_persistence_failure_keeps_existing_private_diagnostic(self) -> None:
        marker = 'SYNTHETIC_PRIVATE_DB_DIAGNOSTIC'
        conversation = self._conversation()
        before = copy.deepcopy(conversation)

        import memory.memory_store as memory_store

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer, 'summarize_conversation', return_value='synthetic summary'),
            patch.object(memory_store, 'save_summary', side_effect=RuntimeError(marker)),
            patch.object(memory_store, 'update_traces_summary_id') as update_summary_id,
            self.assertLogs('frida.summarizer', level='ERROR') as captured,
        ):
            changed = summarizer.maybe_summarize(conversation, 'token-model')

        rendered_logs = '\n'.join(captured.output)
        self.assertFalse(changed)
        self.assertEqual(conversation, before)
        update_summary_id.assert_not_called()
        self.assertIn('summary_db_save_failed', rendered_logs)
        self.assertIn(marker, rendered_logs)

    def test_ambiguous_none_storage_result_fails_closed(self) -> None:
        conversation = self._conversation()
        before = copy.deepcopy(conversation)

        import memory.memory_store as memory_store

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer, 'summarize_conversation', return_value='synthetic summary'),
            patch.object(memory_store, 'save_summary', return_value=None),
            patch.object(memory_store, 'update_traces_summary_id') as update_summary_id,
            self.assertLogs('frida.summarizer', level='ERROR') as captured,
        ):
            changed = summarizer.maybe_summarize(conversation, 'token-model')

        self.assertFalse(changed)
        self.assertEqual(conversation, before)
        update_summary_id.assert_not_called()
        self.assertIn('summary_db_save_failed', '\n'.join(captured.output))

    def test_writer_persistence_failure_does_not_acquire_summary_through_real_facades(self) -> None:
        marker = 'SYNTHETIC_WRITER_DB_DIAGNOSTIC'
        import memory.memory_store as memory_store

        for has_previous_summary in (False, True):
            with self.subTest(has_previous_summary=has_previous_summary):
                conversation = self._conversation()
                if has_previous_summary:
                    conversation['messages'][0:0] = [
                        {
                            'role': 'user',
                            'content': 'previously summarized user',
                            'timestamp': '2026-03-24T09:00:00Z',
                            'summarized_by': 'summary-previous',
                        },
                        {
                            'role': 'assistant',
                            'content': 'previously summarized assistant',
                            'timestamp': '2026-03-24T09:01:00Z',
                            'summarized_by': 'summary-previous',
                        },
                    ]
                before = copy.deepcopy(conversation)
                storage = _SummaryStorageDouble(fail_summary_write=True)

                with (
                    patch.object(summarizer, 'estimate_tokens', return_value=999),
                    patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
                    patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
                    patch.object(summarizer, 'summarize_conversation', return_value='synthetic summary'),
                    patch.object(memory_store, '_conn', side_effect=storage.connection),
                    patch.object(memory_store, 'embed', return_value=[0.1, 0.2]),
                    self.assertLogs('frida.memory_store', level='ERROR') as storage_logs,
                    self.assertLogs('frida.summarizer', level='INFO') as summarizer_logs,
                ):
                    changed = summarizer.maybe_summarize(conversation, 'token-model')

                self.assertFalse(changed)
                self.assertEqual(conversation, before)
                self.assertEqual(storage.connection_attempts, 1)
                self.assertEqual(storage.trace_update_attempts, 0)
                self.assertEqual(storage.summary_rows, {})
                self.assertIn(marker, '\n'.join(storage_logs.output))
                rendered_summarizer_logs = '\n'.join(summarizer_logs.output)
                self.assertIn('summary_db_save_failed', rendered_summarizer_logs)
                self.assertNotIn('summarize_done', rendered_summarizer_logs)

    def test_failed_writer_keeps_messages_eligible_for_next_successful_pass(self) -> None:
        conversation = self._conversation()
        storage = _SummaryStorageDouble(fail_summary_write=True)

        import memory.memory_store as memory_store

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer, 'summarize_conversation', return_value='synthetic retry summary') as generate,
            patch.object(memory_store, '_conn', side_effect=storage.connection),
            patch.object(memory_store, 'embed', return_value=[0.1, 0.2]),
            self.assertLogs('frida', level='ERROR'),
        ):
            self.assertFalse(summarizer.maybe_summarize(conversation, 'token-model'))
            self.assertEqual(len(summarizer._raw_dialogue(conversation)), 4)
            storage.fail_summary_write = False
            self.assertTrue(summarizer.maybe_summarize(conversation, 'token-model'))

        self.assertEqual(generate.call_count, 2)
        self.assertEqual(len(storage.summary_rows), 1)
        self.assertEqual(storage.trace_update_attempts, 1)
        self.assertEqual(len(summarizer._raw_dialogue(conversation)), 2)
        stored = next(iter(storage.summary_rows.values()))
        self.assertEqual(stored['content'], 'synthetic retry summary')

    def test_text_storage_without_embedding_is_readable_and_injected_with_recent_turns(self) -> None:
        conversation = self._conversation()
        storage = _SummaryStorageDouble()

        from core import conversations_prompt_window
        import memory.memory_store as memory_store

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer, 'summarize_conversation', return_value='synthetic durable text summary'),
            patch.object(memory_store, '_conn', side_effect=storage.connection),
            patch.object(memory_store, 'embed', side_effect=RuntimeError('SYNTHETIC_EMBEDDING_FAILURE')),
            self.assertLogs('frida.memory_store', level='WARNING') as storage_logs,
        ):
            changed = summarizer.maybe_summarize(conversation, 'token-model')

        self.assertTrue(changed)
        stored = next(iter(storage.summary_rows.values()))
        self.assertIsNone(stored['embedding'])
        self.assertIn('summary_embed_skip', '\n'.join(storage_logs.output))

        def get_active_summary(_conversation_id):
            return conversations_prompt_window.get_active_summary(
                conversation['id'],
                normalize_conversation_id_func=lambda value: str(value) if value else None,
                db_conn_func=storage.connection,
                ts_to_iso_func=lambda value: str(value),
                logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
            )

        prompt_messages = conversations_prompt_window.build_prompt_messages(
            conversation,
            'token-model',
            now='2026-03-24T10:04:00Z',
            ensure_system_message_func=lambda _messages: {'role': 'system', 'content': 'SYSTEM'},
            get_active_summary_func=get_active_summary,
            summary_cutoff_iso_func=lambda summary: conversations_prompt_window.summary_cutoff_iso(
                summary,
                ts_to_iso_func=lambda value: str(value),
            ),
            message_is_after_summary_func=lambda message, cutoff: conversations_prompt_window.message_is_after_summary(
                message,
                cutoff,
                parse_iso_to_dt_func=lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')),
            ),
            make_summary_message_func=conversations_prompt_window.make_summary_message,
            make_context_hints_message_func=lambda *_args: None,
            make_memory_context_message_func=lambda *_args: None,
            make_memory_message_func=lambda *_args: None,
            count_tokens_func=lambda *_args: 1,
            max_tokens=1000,
            now_iso_func=lambda: '2026-03-24T10:04:00Z',
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, warning=lambda *_args, **_kwargs: None),
            admin_log_event_func=lambda *_args, **_kwargs: None,
            silence_label_func=lambda *_args: '',
            delta_t_label_func=lambda *_args: '',
        )

        rendered_prompt = '\n'.join(message['content'] for message in prompt_messages)
        self.assertIn('synthetic durable text summary', rendered_prompt)
        self.assertNotIn('message un', rendered_prompt)
        self.assertNotIn('reponse un', rendered_prompt)
        self.assertIn('message deux', rendered_prompt)
        self.assertIn('reponse deux', rendered_prompt)

    def test_trace_attachment_failure_keeps_stored_summary_without_regeneration(self) -> None:
        conversation = self._conversation()
        storage = _SummaryStorageDouble(fail_trace_update=True)

        import memory.memory_store as memory_store

        with (
            patch.object(summarizer, 'estimate_tokens', return_value=999),
            patch.object(config, 'SUMMARY_THRESHOLD_TOKENS', 1),
            patch.object(config, 'SUMMARY_KEEP_TURNS', 1),
            patch.object(summarizer, 'summarize_conversation', return_value='synthetic linked summary') as generate,
            patch.object(memory_store, '_conn', side_effect=storage.connection),
            patch.object(memory_store, 'embed', return_value=[0.1, 0.2]),
            self.assertLogs('frida.memory_store', level='ERROR') as storage_logs,
        ):
            self.assertTrue(summarizer.maybe_summarize(conversation, 'token-model'))
            self.assertFalse(summarizer.maybe_summarize(conversation, 'token-model'))

        self.assertEqual(generate.call_count, 1)
        self.assertEqual(len(storage.summary_rows), 1)
        self.assertEqual(storage.trace_update_attempts, 1)
        self.assertEqual(next(iter(storage.summary_rows.values()))['content'], 'synthetic linked summary')
        self.assertIn('update_traces_summary_id_error', '\n'.join(storage_logs.output))
        self.assertEqual(len(summarizer._raw_dialogue(conversation)), 2)

    def test_summarize_conversation_logs_provider_metadata_and_uses_runtime_summary_slot(self) -> None:
        observed = {'url': None, 'payload': None, 'headers': None, 'timeout': None, 'provider_logs': []}
        original_post = summarizer.requests.post
        original_get_settings = summarizer.runtime_settings.get_summary_model_settings
        original_url = summarizer.llm_client.or_chat_completions_url
        original_or_headers = summarizer.llm_client.or_headers
        original_log_provider_metadata = summarizer.llm_client.log_provider_metadata
        original_get_summary_system_prompt = summarizer.prompt_loader.get_summary_system_prompt

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    'id': 'gen-summary',
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {'prompt_tokens': 21, 'completion_tokens': 9, 'total_tokens': 30},
                    'choices': [{'message': {'content': 'resume test'}}],
                }

        def fake_get_summary_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='summary_model',
                payload=runtime_settings.normalize_stored_payload(
                    'summary_model',
                    {
                        'model': {'value': 'openrouter/summary-runtime', 'origin': 'db'},
                        'temperature': {'value': 0.42, 'origin': 'db'},
                        'top_p': {'value': 0.77, 'origin': 'db'},
                        'max_tokens': {'value': 1234, 'origin': 'db'},
                        'timeout_s': {'value': 56, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        def fake_post(url, *, json, headers, timeout):
            observed['url'] = url
            observed['payload'] = dict(json)
            observed['headers'] = dict(headers)
            observed['timeout'] = timeout
            return FakeResponse()

        summarizer.requests.post = fake_post
        summarizer.runtime_settings.get_summary_model_settings = fake_get_summary_model_settings
        summarizer.llm_client.or_chat_completions_url = lambda: 'https://openrouter.runtime.test/chat/completions'
        summarizer.llm_client.or_headers = lambda caller='llm': {'Authorization': f'caller={caller}'}
        summarizer.llm_client.log_provider_metadata = lambda _logger, event_name, provider_metadata: observed['provider_logs'].append(
            (event_name, dict(provider_metadata))
        )
        summarizer.prompt_loader.get_summary_system_prompt = lambda: 'SYSTEM SUMMARY'
        try:
            result = summarizer.summarize_conversation(
                [{'role': 'user', 'content': 'bonjour', 'timestamp': '2026-03-24T10:00:00Z'}],
            )
        finally:
            summarizer.requests.post = original_post
            summarizer.runtime_settings.get_summary_model_settings = original_get_settings
            summarizer.llm_client.or_chat_completions_url = original_url
            summarizer.llm_client.or_headers = original_or_headers
            summarizer.llm_client.log_provider_metadata = original_log_provider_metadata
            summarizer.prompt_loader.get_summary_system_prompt = original_get_summary_system_prompt

        self.assertEqual(result, 'resume test')
        self.assertEqual(observed['url'], 'https://openrouter.runtime.test/chat/completions')
        self.assertEqual(observed['headers'], {'Authorization': 'caller=resumer'})
        self.assertEqual(observed['timeout'], 56)
        self.assertEqual(observed['payload']['model'], 'openrouter/summary-runtime')
        self.assertEqual(observed['payload']['temperature'], 0.42)
        self.assertEqual(observed['payload']['top_p'], 0.77)
        self.assertEqual(observed['payload']['max_tokens'], 1234)
        self.assertEqual(observed['payload']['metadata']['frida_caller'], 'summary')
        self.assertEqual(observed['payload']['metadata']['frida_slot'], 'summary_model')
        self.assertEqual(observed['payload']['trace']['trace_name'], 'FridaDev')
        self.assertEqual(
            observed['provider_logs'],
            [
                (
                    'summarizer_provider_response',
                    {
                        'provider_generation_id': 'gen-summary',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 21,
                        'provider_completion_tokens': 9,
                        'provider_total_tokens': 30,
                    },
                )
            ],
        )


if __name__ == '__main__':
    unittest.main()
