"""Request-owned renewal and persistence fencing, including lazy chat streams."""
import hashlib
import json
import threading
import time
from uuid import UUID, uuid4

from . import conversation_turn_claims as claims, chat_stream_control


def request_identity(data):
    raw = data.get('client_turn_id')
    if 'client_turn_id' in data:
        try:
            if type(raw) is not str:
                raise ValueError()
            turn_id = str(UUID(raw))
        except (ValueError, AttributeError):
            raise claims.ClaimError('client_turn_id_invalid', 400) from None
    else:
        turn_id = str(uuid4())
    # Identity is supplied/random, never the text, seq or fingerprint. The
    # fingerprint only refuses reusing an identity with incompatible inputs.
    request = {k: v for k, v in data.items() if k not in ('client_turn_id', 'stream')}
    request['message'] = str(data.get('message') or '').strip()
    request['input_mode'] = str(data.get('input_mode') or 'keyboard').strip().lower()
    encoded = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return turn_id, hashlib.sha256(encoded).hexdigest()


def error_result(error, *, record=None):
    payload = {'ok': False, 'reason_code': error.reason_code,
               'error': 'Traitement de conversation indisponible.'}
    if record:
        payload['turn'] = {k: record[k] for k in ('turn_id', 'conversation_id', 'state', 'outcome')}
    return {'kind': 'json', 'payload': payload, 'status': error.status, 'headers': {}}


class ChatReservation:
    def __init__(self, token, store=claims):
        self.token, self.store = token, store
        self._stop = threading.Event()
        self._active = threading.Event()
        self._active.set()
        self._lost = False
        self._closed = False
        self._idle_at = time.monotonic()
        self._thread = threading.Thread(target=self._renew, name='chat-lease', daemon=True)
        self._thread.start()

    def _renew(self):
        while not self._stop.wait(self.store.RENEW_SECONDS):
            if not self._active.is_set():
                if time.monotonic() - self._idle_at >= self.store.LEASE_SECONDS:
                    return
                continue
            try:
                self.store.renew(self.token)
            except Exception:
                self._lost = True
                return

    def resume(self):
        if self._closed or self._lost:
            raise claims.ClaimError('conversation_claim_lost')
        self.store.renew(self.token)
        self._active.set()

    def idle(self):
        self._idle_at = time.monotonic()
        self._active.clear()

    def finish(self, state=None):
        if self._closed:
            return
        self._stop.set()
        self._closed = True
        # SQL rechecks independently of the supervisor's local impression.
        self.store.finish(self.token, state)

    def close(self):
        try:
            self.finish('interrupted')
        except Exception:
            # No permissive release: an unavailable/lost claim expires by SQL
            # time, and an old token cannot release its successor.
            pass


class ReservedConversationStore:
    def __init__(self, base, reservation):
        self._base, self.reservation = base, reservation
        self._phase = None

    def __getattr__(self, name):
        return getattr(self._base, name)

    def mark_next_persist_phase(self, phase):
        self._phase = phase
        marker = getattr(self._base, 'mark_next_persist_phase', None)
        if callable(marker):
            marker(phase)

    def save_conversation(self, conversation, *args, **kwargs):
        phase, self._phase = self._phase, None
        outcome = ('succeeded' if phase in ('assistant_final', 'empty_final') else 'interrupted'
                   if phase in ('assistant_interrupted', 'user_turn') else None)
        return self._base.save_conversation(conversation, *args,
            turn_claim=self.reservation.token, claim_outcome=outcome, **kwargs)


class ReservedMemoryStore:
    """Only pre-final conversation state writes need the turn's authority."""
    def __init__(self, base, reservation):
        self._base, self.reservation = base, reservation

    def __getattr__(self, name):
        return getattr(self._base, name)

    def write_hermeneutic_node_state(self, conversation_id, state):
        return self._base.write_hermeneutic_node_state(
            conversation_id, state, turn_claim=self.reservation.token)


class ReservedRequests:
    def __init__(self, base, reservation):
        self._base, self.reservation = base, reservation

    def __getattr__(self, name):
        return getattr(self._base, name)

    def post(self, *args, **kwargs):
        self.reservation.resume()
        return self._base.post(*args, **kwargs)


class ReservedChatStream:
    """close works even before the first next; no generator-finally assumption."""
    def __init__(self, stream, reservation):
        self._stream, self.reservation = iter(stream), reservation
        self._closed = False
        reservation.idle()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        try:
            self.reservation.resume()
            chunk = next(self._stream)
            terminal = chat_stream_control.parse_terminal_chunk(chunk)
            if terminal:
                self.reservation.finish('succeeded' if terminal['event'] == 'done' else None)
                self.close()
            return chunk
        except StopIteration:
            self.close()
            raise
        except claims.ClaimError:
            self.close()
            return chat_stream_control.build_terminal_chunk(
                chat_stream_control.STREAM_TERMINAL_ERROR,
                error_code=chat_stream_control.STREAM_ERROR_CONVERSATION_PERSIST_FAILED)
        except BaseException:
            self.close()
            raise
        finally:
            self.reservation.idle()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            closer = getattr(self._stream, 'close', None)
            if callable(closer):
                closer()
        finally:
            self.reservation.close()
