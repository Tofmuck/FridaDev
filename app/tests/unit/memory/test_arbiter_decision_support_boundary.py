from __future__ import annotations

import copy
import unittest

from memory import arbiter


class ArbiterDecisionSupportBoundaryTests(unittest.TestCase):
    def test_support_completes_and_selects_decisions_by_stable_candidate_id(self) -> None:
        support = getattr(arbiter, "arbiter_decision_support", None)
        self.assertIsNotNone(support)

        traces = [
            {
                "candidate_id": "candidate-kept",
                "content": "synthetic durable alpha",
                "semantic_score": 0.91,
            },
            {
                "candidate_id": "candidate-redundant",
                "content": "synthetic durable beta",
                "semantic_score": 0.82,
            },
            {
                "candidate_id": "candidate-missing",
                "content": "synthetic durable gamma",
                "semantic_score": 0.73,
            },
        ]
        decisions = [
            {
                "candidate_id": "candidate-kept",
                "keep": False,
                "semantic_relevance": 0.91,
                "contextual_gain": 0.81,
                "redundant_with_recent": False,
                "reason": "synthetic-rejected-copy",
                "decision_source": "llm",
            },
            {
                "candidate_id": "candidate-kept",
                "keep": True,
                "semantic_relevance": 0.91,
                "contextual_gain": 0.81,
                "redundant_with_recent": False,
                "reason": "synthetic-kept-copy",
                "decision_source": "llm",
            },
            {
                "candidate_id": "candidate-redundant",
                "keep": True,
                "semantic_relevance": 0.82,
                "contextual_gain": 0.72,
                "redundant_with_recent": True,
                "reason": "synthetic-redundant",
                "decision_source": "llm",
            },
            {
                "candidate_id": "candidate-unknown",
                "keep": True,
                "semantic_relevance": 1.0,
                "contextual_gain": 1.0,
                "redundant_with_recent": False,
                "reason": "synthetic-unknown",
                "decision_source": "llm",
            },
        ]

        kept, completed = support.complete_and_select_decisions(
            traces,
            decisions,
            recent_turns=[],
            model="synthetic-memory-arbiter",
            min_semantic_relevance=0.5,
            min_contextual_gain=0.4,
            max_kept_traces=2,
        )

        projection = {
            "kept": tuple(trace["candidate_id"] for trace in kept),
            "decisions": tuple(
                (
                    decision["candidate_id"],
                    decision["keep"],
                    decision["decision_source"],
                    decision["model"],
                    decision["reason"],
                )
                for decision in completed
            ),
        }
        expected = {
            "kept": ("candidate-kept",),
            "decisions": (
                (
                    "candidate-kept",
                    True,
                    "llm",
                    "synthetic-memory-arbiter",
                    "synthetic-kept-copy",
                ),
                (
                    "candidate-redundant",
                    False,
                    "llm",
                    "synthetic-memory-arbiter",
                    "synthetic-redundant | redundant_with_recent",
                ),
                (
                    "candidate-missing",
                    False,
                    "llm",
                    "synthetic-memory-arbiter",
                    "missing_from_llm_output",
                ),
            ),
        }
        self.assertEqual(projection, expected)

        wrong_candidate_binding = copy.deepcopy(projection)
        wrong_candidate_binding["kept"] = ("candidate-redundant",)
        with self.assertRaises(AssertionError):
            self.assertEqual(wrong_candidate_binding, expected)


if __name__ == "__main__":
    unittest.main()
