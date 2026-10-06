"""Preparation-local progress and independent monotonic inactivity supervision."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Awaitable, Callable

from .document_workshop_contract import DocumentWorkshopError, PREPARATION_INACTIVITY_SECONDS

_STEPS = ("payload_prepared", "admitted", "provider_finished", "canonical_validated")
_INPUT_STEPS = ('user_saved', 'summary_ready', 'identity_ready', 'memory_ready', 'stimmung_ready',
                'hermeneutic_ready', 'dialogue_ready', 'sources_ready')


@dataclass(frozen=True)
class PreparationSnapshot:
    state: str
    phase: str
    completed_steps: tuple[str, ...]
    received_content_codepoints: int
    reason_code: str | None


class DocumentPreparation:
    """One preparation, starting at construction, with no total-time deadline.

    Only completed finite steps and admitted provider content renew progress.
    No polling/lease/animation/heartbeat method exists. Snapshots are content-free.
    This object is neither a pending TTL nor a durable claim/fencing mechanism.
    """

    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic,
                 wait_until: Callable[[float], Awaitable[None]] | None = None):
        self._clock = monotonic
        self._wait_until = wait_until or self._sleep_until
        self._last_progress = monotonic()
        self._state = "preparing"
        self._phase = "preparing"
        self._steps: list[str] = []
        self._received = 0
        self._reason: str | None = None
        self._stopped = asyncio.Event()
        self._exchange_started = False
        self._input_steps: list[str] = []
        self._source_reads: set[str] = set()

    def complete_input_step(self, step: str) -> None:
        """M4 finite upstream work, before the M0 provider exchange."""
        self.check()
        steps = _INPUT_STEPS
        if self._exchange_started or len(self._input_steps) >= len(steps) or steps[len(self._input_steps)] != step:
            raise DocumentWorkshopError('document_progress_invalid')
        self._input_steps.append(step)
        self._phase = step
        self._last_progress = self._clock()

    def complete_source(self, source_id: str) -> None:
        self.check()
        if self._exchange_started or tuple(self._input_steps) != _INPUT_STEPS[:-1] or source_id in self._source_reads:
            raise DocumentWorkshopError('document_progress_invalid')
        self._source_reads.add(source_id)
        self._phase = 'source_read'
        self._last_progress = self._clock()

    async def _sleep_until(self, deadline: float) -> None:
        await asyncio.sleep(max(0.0, deadline - self._clock()))

    def snapshot(self) -> PreparationSnapshot:
        return PreparationSnapshot(self._state, self._phase, tuple(self._steps), self._received, self._reason)

    def check(self) -> None:
        if self._state != "preparing":
            raise DocumentWorkshopError(self._reason or "document_preparation_closed")
        if self._clock() - self._last_progress >= PREPARATION_INACTIVITY_SECONDS:
            self.fail("document_inactivity")
            raise DocumentWorkshopError("document_inactivity")

    def complete_step(self, step: str) -> None:
        self.check()
        if len(self._steps) >= len(_STEPS) or _STEPS[len(self._steps)] != step:
            raise DocumentWorkshopError("document_progress_invalid")
        self._steps.append(step)
        self._phase = step
        self._last_progress = self._clock()

    def begin_exchange(self) -> None:
        self.check()
        if self._exchange_started or tuple(self._steps) != _STEPS[:2]:
            raise DocumentWorkshopError("document_progress_invalid")
        self._exchange_started = True

    def _receive_provider_content(self, content: str) -> None:
        self.check()
        if not self._exchange_started or type(content) is not str or not content:
            raise DocumentWorkshopError("document_progress_invalid")
        self._received += len(content)
        self._phase = "provider_content"
        self._last_progress = self._clock()

    def fail(self, reason_code: str) -> None:
        if self._state == "preparing":
            self._state = "failed"
            self._reason = reason_code
            self._stopped.set()

    def cancel(self) -> None:
        if self._state == "preparing":
            self._state = "cancelled"
            self._reason = "document_cancelled"
            self._stopped.set()

    def succeed(self) -> None:
        self.check()
        if tuple(self._steps) != _STEPS:
            raise DocumentWorkshopError("document_progress_invalid")
        self._state = "succeeded"
        self._stopped.set()

    async def watch_inactivity(self) -> None:
        """Runs independently of a blocked send/read and of SSE byte arrivals.

        Renewed useful progress may move the deadline while the old alarm is
        sleeping. On waking, check the *current* last-progress time, then wait
        until its deadline. Cancellation wakes supervision immediately.
        """
        while True:
            self.check()
            alarm = asyncio.create_task(self._wait_until(self._last_progress + PREPARATION_INACTIVITY_SECONDS))
            stopped = asyncio.create_task(self._stopped.wait())
            try:
                await asyncio.wait((alarm, stopped), return_when=asyncio.FIRST_COMPLETED)
                if alarm.done():
                    alarm.result()
            finally:
                alarm.cancel()
                stopped.cancel()
                await asyncio.gather(alarm, stopped, return_exceptions=True)
            self.check()
