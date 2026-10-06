"""Explicit authority double for historical provider/persistence unit fixtures.

Never a SQL proof. M3 integration fixtures supply the real store instead.
"""
from types import SimpleNamespace
from uuid import uuid4
from core.conversation_turn_claims import ClaimError, ClaimAdmission


class SyntheticChatClaims:
    ClaimError = ClaimError
    LEASE_SECONDS = 90
    RENEW_SECONDS = 15

    def read(self, turn_id):
        return None

    def acquire(self, *, conversation_id, turn_id, request_fingerprint):
        return ClaimAdmission(SimpleNamespace(turn_id=turn_id, conversation_id=conversation_id,
            owner_id=str(uuid4()), generation=1), {})

    def renew(self, token):
        pass

    def finish(self, token, state=None):
        pass
