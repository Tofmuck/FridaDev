from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_identity_periodic_scoring


def _buffer_pairs(*, proposition: str, supporting_indexes: set[int]) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for index in range(15):
        if index in supporting_indexes:
            user_content = f'Utilisateur confirme clairement que {proposition}'
        else:
            user_content = f'utilisateur {index} parle d autre chose'
        pairs.append(
            {
                'user': {'role': 'user', 'content': user_content},
                'assistant': {'role': 'assistant', 'content': f'assistant {index}'},
            }
        )
    return pairs


class IdentityPeriodicScoringPhase2Tests(unittest.TestCase):
    def test_score_operation_with_no_support_stays_rejected(self) -> None:
        proposition = 'Tof garde une orientation stable et ritualisee.'
        score = memory_identity_periodic_scoring.score_operation(
            {'kind': 'add', 'proposition': proposition, 'reason': 'no support'},
            buffer_pairs=_buffer_pairs(
                proposition=proposition,
                supporting_indexes=set(),
            ),
        )

        self.assertEqual(score['support_pairs'], 0)
        self.assertEqual(score['last_occurrence_distance'], 15)
        self.assertEqual(score['frequency_norm'], 0.0)
        self.assertEqual(score['recency_norm'], 0.0)
        self.assertEqual(score['strength'], 0.0)
        self.assertEqual(score['threshold_verdict'], 'rejected')

    def test_score_operation_reports_support_frequency_recency_and_strength(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        score = memory_identity_periodic_scoring.score_operation(
            {'kind': 'add', 'proposition': proposition, 'reason': 'durable identity signal'},
            buffer_pairs=_buffer_pairs(
                proposition=proposition,
                supporting_indexes={1, 4, 8, 12, 14},
            ),
        )

        self.assertEqual(score['support_pairs'], 5)
        self.assertEqual(score['last_occurrence_distance'], 0)
        self.assertEqual(score['frequency_norm'], 0.3333)
        self.assertEqual(score['recency_norm'], 1.0)
        self.assertEqual(score['strength'], 0.5333)
        self.assertEqual(score['threshold_verdict'], 'deferred')

    def test_score_operation_rejects_low_support_candidate(self) -> None:
        proposition = 'Frida garde une methode d ecriture stable et compacte.'
        score = memory_identity_periodic_scoring.score_operation(
            {'kind': 'add', 'proposition': proposition, 'reason': 'weak signal'},
            buffer_pairs=_buffer_pairs(
                proposition=proposition,
                supporting_indexes={0, 1, 2, 3},
            ),
        )

        self.assertEqual(score['support_pairs'], 4)
        self.assertEqual(score['last_occurrence_distance'], 11)
        self.assertEqual(score['frequency_norm'], 0.2667)
        self.assertEqual(score['recency_norm'], 0.2143)
        self.assertEqual(score['strength'], 0.251)
        self.assertEqual(score['threshold_verdict'], 'rejected')

    def test_score_operation_accepts_high_support_candidate(self) -> None:
        proposition = 'Tof revient souvent a une attention patiente et stable.'
        score = memory_identity_periodic_scoring.score_operation(
            {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
            buffer_pairs=_buffer_pairs(
                proposition=proposition,
                supporting_indexes={0, 2, 4, 6, 8, 10, 12, 14},
            ),
        )

        self.assertEqual(score['support_pairs'], 8)
        self.assertEqual(score['last_occurrence_distance'], 0)
        self.assertEqual(score['frequency_norm'], 0.5333)
        self.assertEqual(score['recency_norm'], 1.0)
        self.assertEqual(score['strength'], 0.6733)
        self.assertEqual(score['threshold_verdict'], 'accepted')

    def test_tighten_scoring_ignores_support_for_legacy_target_text(self) -> None:
        target = 'Tof garde une clarte durable.'
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        score = memory_identity_periodic_scoring.score_operation(
            {
                'kind': 'tighten',
                'target': target,
                'proposition': proposition,
                'reason': 'target support alone is not enough',
            },
            buffer_pairs=_buffer_pairs(
                proposition=target,
                supporting_indexes=set(range(15)),
            ),
        )

        self.assertEqual(score['support_pairs'], 0)
        self.assertEqual(score['last_occurrence_distance'], 15)
        self.assertEqual(score['frequency_norm'], 0.0)
        self.assertEqual(score['recency_norm'], 0.0)
        self.assertEqual(score['strength'], 0.0)
        self.assertEqual(score['threshold_verdict'], 'rejected')

    def test_merge_scoring_ignores_support_for_legacy_targets_when_merge_text_is_absent(self) -> None:
        target_a = 'Tof garde une clarte durable.'
        target_b = 'Tof garde un axe de travail stable.'
        proposition = 'Tof garde une clarte durable et un axe de travail stable.'
        pairs: list[dict[str, object]] = []
        for index in range(15):
            pairs.append(
                {
                    'user': {'role': 'user', 'content': f'Utilisateur confirme {target_a} {target_b}'},
                    'assistant': {'role': 'assistant', 'content': f'Assistant reprend {target_a} {target_b}'},
                }
            )

        score = memory_identity_periodic_scoring.score_operation(
            {
                'kind': 'merge',
                'targets': [target_a, target_b],
                'proposition': proposition,
                'reason': 'merge text itself is not supported',
            },
            buffer_pairs=pairs,
        )

        self.assertEqual(score['support_pairs'], 0)
        self.assertEqual(score['strength'], 0.0)
        self.assertEqual(score['threshold_verdict'], 'rejected')

    def test_tighten_scoring_keeps_supported_final_proposition_admissible(self) -> None:
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        score = memory_identity_periodic_scoring.score_operation(
            {
                'kind': 'tighten',
                'target': 'Tof garde une clarte durable.',
                'proposition': proposition,
                'reason': 'supported final wording',
            },
            buffer_pairs=_buffer_pairs(
                proposition=proposition,
                supporting_indexes={0, 2, 4, 6, 8, 10, 12, 14},
            ),
        )

        self.assertEqual(score['support_pairs'], 8)
        self.assertEqual(score['threshold_verdict'], 'accepted')

    def test_threshold_verdict_boundaries_follow_contract(self) -> None:
        self.assertEqual(memory_identity_periodic_scoring.threshold_verdict(0.3499), 'rejected')
        self.assertEqual(memory_identity_periodic_scoring.threshold_verdict(0.35), 'deferred')
        self.assertEqual(memory_identity_periodic_scoring.threshold_verdict(0.5999), 'deferred')
        self.assertEqual(memory_identity_periodic_scoring.threshold_verdict(0.60), 'accepted')


if __name__ == '__main__':
    unittest.main()
