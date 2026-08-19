from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from memory import memory_traces_summaries


class MemoryTraceSummaryStoreBoundaryTests(unittest.TestCase):
    def test_facade_delegates_trace_persistence_with_compatibility_hooks(self) -> None:
        observed: dict[str, object] = {}

        def fake_save_new_traces(conversation, **kwargs) -> None:
            observed["conversation"] = conversation
            observed.update(kwargs)

        fake_store = SimpleNamespace(save_new_traces=fake_save_new_traces)
        conversation = {"id": "synthetic-boundary", "messages": []}
        conn_factory = lambda: object()
        embed_fn = lambda *_args, **_kwargs: [0.1]
        logger = SimpleNamespace()

        with patch.object(
            memory_traces_summaries,
            "memory_trace_summary_store",
            fake_store,
            create=True,
        ):
            memory_traces_summaries.save_new_traces(
                conversation,
                conn_factory=conn_factory,
                embed_fn=embed_fn,
                logger=logger,
            )

        self.assertIs(observed.get("conversation"), conversation)
        self.assertIs(observed["conn_factory"], conn_factory)
        self.assertIs(observed["embed_fn"], embed_fn)
        self.assertIs(observed["logger"], logger)
        self.assertIs(
            observed["message_is_trace_eligible_fn"],
            memory_traces_summaries._message_is_trace_eligible,
        )
        self.assertIs(
            observed["trace_exists_for_message_fn"],
            memory_traces_summaries._trace_exists_for_message,
        )
        self.assertIs(
            observed["embed_with_purpose_fn"],
            memory_traces_summaries._embed_with_purpose,
        )


if __name__ == "__main__":
    unittest.main()
