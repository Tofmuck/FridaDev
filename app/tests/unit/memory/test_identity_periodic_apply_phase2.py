from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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

import config
from identity import active_identity_projection
from memory import memory_identity_periodic_apply


def _supportive_buffer(*, proposition: str, support_indexes: set[int]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for index in range(15):
        if index in support_indexes:
            user_content = f'Utilisateur confirme que {proposition}'
            assistant_content = f'Assistant reformule: {proposition}'
        else:
            user_content = f'utilisateur {index} parle d autre chose'
            assistant_content = f'assistant {index} ne reprend pas ce trait'
        pairs.append(
            {
                'user': {'role': 'user', 'content': user_content},
                'assistant': {'role': 'assistant', 'content': assistant_content},
            }
        )
    return pairs


def _contract_for_user_operations(*operations: dict[str, Any]) -> dict[str, Any]:
    return {
        'llm': {
            'operations': [
                {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
            ]
        },
        'user': {'operations': list(operations)},
        'meta': {
            'execution_status': 'complete',
            'buffer_pairs_count': 15,
            'window_complete': True,
        },
    }


def _build_near_target_mutable(*, slack: int = 70) -> str:
    lines: list[str] = []
    content = ''
    index = 1
    while len(content) < (int(config.IDENTITY_MUTABLE_TARGET_CHARS) - max(1, int(slack))):
        lines.append(f'Trait de fond stable numero {index}.')
        content = '\n'.join(lines)
        index += 1
    return content


class _MutableStore:
    def __init__(self, initial: dict[str, dict[str, Any]] | None = None) -> None:
        self.mutable = copy.deepcopy(initial or {})
        self.upsert_calls: list[tuple[str, str, str, str]] = []
        self.clear_calls: list[str] = []

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        item = self.mutable.get(subject)
        return copy.deepcopy(item) if item is not None else None

    def upsert_mutable_identity(
        self,
        subject: str,
        content: str,
        source_trace_id: str | None = None,
        *,
        updated_by: str = 'system',
        update_reason: str = '',
    ) -> dict[str, Any]:
        payload = {
            'subject': subject,
            'content': content,
            'source_trace_id': source_trace_id,
            'updated_by': updated_by,
            'update_reason': update_reason,
        }
        self.mutable[subject] = payload
        self.upsert_calls.append((subject, content, updated_by, update_reason))
        return copy.deepcopy(payload)

    def clear_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        self.clear_calls.append(subject)
        previous = self.mutable.pop(subject, None)
        return copy.deepcopy(previous) if previous is not None else None


class IdentityPeriodicApplyPhase2Tests(unittest.TestCase):
    def test_deferred_candidate_does_not_write_canonical_mutable(self) -> None:
        proposition = 'Tof revient souvent a une attention patiente.'
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'mid signal'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes={10, 11, 12, 13, 14},
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.upsert_calls, [])
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['reason_code'], 'strength_deferred')
        self.assertEqual(user_outcome['threshold_verdict'], 'deferred')
        self.assertEqual(user_outcome['support_pairs'], 5)

    def test_promotes_strongest_candidate_to_static_when_mutable_is_full(self) -> None:
        strong = 'Tof maintient une orientation stable et ritualisee.'
        medium = 'Tof garde un gout stable pour les architectures lisibles.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=70),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text('Tof garde une orientation stable.', encoding='utf-8')
            old_ts = 1_700_000_000
            os.utime(llm_path, (old_ts, old_ts))
            os.utime(user_path, (old_ts, old_ts))

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                )

            def write_static(subject: str, content: str) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            composite_buffer: list[dict[str, Any]] = []
            medium_support_indexes = {7, 8, 9, 10, 11, 12, 13, 14}
            for index in range(15):
                user_content = f'Utilisateur confirme que {strong}'
                assistant_content = f'Assistant reformule: {strong}'
                if index in medium_support_indexes:
                    user_content += f' {medium}'
                composite_buffer.append(
                    {
                        'user': {'role': 'user', 'content': user_content},
                        'assistant': {'role': 'assistant', 'content': assistant_content},
                    }
                )

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': strong, 'reason': 'strong signal'},
                    {'kind': 'add', 'proposition': medium, 'reason': 'secondary signal'},
                ),
                buffer_pairs=composite_buffer,
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'ok')
            self.assertEqual(summary['reason_code'], 'applied')
            self.assertTrue(summary['writes_applied'])
            self.assertEqual(summary['promotion_count'], 1)
            self.assertEqual(summary['promotions'][0]['promotion_reason_code'], 'promoted_to_static')
            self.assertEqual(summary['promotions'][0]['operation_kind'], 'add')
            self.assertAlmostEqual(summary['promotions'][0]['strength'], 1.0, places=4)
            updated_static = user_path.read_text(encoding='utf-8').strip()
            self.assertIn(strong, updated_static)
            self.assertNotIn(strong, store.mutable['user']['content'])
            self.assertIn(medium, store.mutable['user']['content'])
            self.assertLessEqual(len(store.mutable['user']['content']), int(config.IDENTITY_MUTABLE_TARGET_CHARS))
            self.assertEqual(store.upsert_calls[-1][2], 'identity_periodic_agent')
            self.assertEqual(store.upsert_calls[-1][3], 'periodic_agent_promotion')

            projection = active_identity_projection.resolve_active_identity_projection(
                llm_static=llm_path.read_text(encoding='utf-8').strip(),
                user_static=updated_static,
                get_mutable_identity_fn=store.get_mutable_identity,
            )
            self.assertIn(strong, projection.block)
            self.assertNotIn(strong, projection.user_mutable['content'])
            self.assertIn(medium, projection.user_mutable['content'])

    def test_double_saturation_suspends_canonization_without_writing(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=20),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text(('Trait statique plein. ' * 180).strip(), encoding='utf-8')
            old_ts = 1_700_000_000
            os.utime(llm_path, (old_ts, old_ts))
            os.utime(user_path, (old_ts, old_ts))
            initial_static = user_path.read_text(encoding='utf-8')
            initial_mutable = store.mutable['user']['content']

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                )

            def write_static(subject: str, content: str) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
                ),
                buffer_pairs=_supportive_buffer(
                    proposition=proposition,
                    support_indexes=set(range(15)),
                ),
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'skipped')
            self.assertEqual(summary['reason_code'], 'double_saturation')
            self.assertFalse(summary['writes_applied'])
            self.assertTrue(summary['auto_canonization_suspended'])
            self.assertEqual(summary['promotion_count'], 0)
            self.assertEqual(user_path.read_text(encoding='utf-8'), initial_static)
            self.assertEqual(store.mutable['user']['content'], initial_mutable)

    def test_recent_admin_mutable_guard_blocks_tighten_on_recent_operator_edit(self) -> None:
        current = 'Tof garde une clarte durable.'
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'admin_identity_mutable_edit',
                    'updated_ts': datetime.now(timezone.utc).isoformat(),
                    'update_reason': 'correction operateur',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'tighten',
                    'target': current,
                    'proposition': proposition,
                    'reason': 'strong signal',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'all_or_nothing_rejected')
        self.assertEqual(summary['rejection_reasons'], {'user': 'recent_admin_mutable_guard'})
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], current)

    def test_recent_static_edit_guard_suspends_promotion(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=20),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text('Tof garde une orientation stable.', encoding='utf-8')

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                )

            def write_static(subject: str, content: str) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
                ),
                buffer_pairs=_supportive_buffer(
                    proposition=proposition,
                    support_indexes=set(range(15)),
                ),
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'skipped')
            self.assertEqual(summary['reason_code'], 'static_recent_operator_edit_guard')
            self.assertTrue(summary['auto_canonization_suspended'])
            self.assertFalse(summary['writes_applied'])
            self.assertEqual(user_path.read_text(encoding='utf-8').strip(), 'Tof garde une orientation stable.')


if __name__ == '__main__':
    unittest.main()
