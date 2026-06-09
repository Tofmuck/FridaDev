from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from agenda import agent_contract


META_KEY = 'agenda_pending_state'
SCHEMA_VERSION = 'frida_agenda_pending_store_v1'
PERSISTENCE_MODE = 'conversation_message_meta'
DEFAULT_TTL_SECONDS = 30 * 60
MAX_ACTIONS = 12

STATUS_PENDING = 'pending'
STATUS_CANCELLED = 'cancelled'
STATUS_EXPIRED = 'expired'
STATUS_EXECUTED = 'executed'

OPERATION_CREATE = 'create'
OPERATION_UPDATE = 'update'
OPERATION_DELETE = 'delete'
OPERATIONS = {OPERATION_CREATE, OPERATION_UPDATE, OPERATION_DELETE}

CONFIRMATION_SIMPLE = 'simple'
CONFIRMATION_REINFORCED = 'reinforced'

_SAFE_TOKEN_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-')
_PRIVATE_DRAFTS: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class AgendaPendingAction:
    pending_action_id: str
    operation: str
    confirmation_level: str
    risk_flags: tuple[str, ...] = ()
    created_at: str = ''
    expires_at: str = ''
    status: str = STATUS_PENDING
    action_hash: str = ''
    draft: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def active(self) -> bool:
        return self.status == STATUS_PENDING

    def expired_at(self, now_iso: str) -> bool:
        expires = _parse_iso(self.expires_at)
        now = _parse_iso(now_iso)
        return bool(expires is not None and now is not None and expires <= now)

    def with_status(self, status: str) -> 'AgendaPendingAction':
        next_status = status if status in {STATUS_PENDING, STATUS_CANCELLED, STATUS_EXPIRED, STATUS_EXECUTED} else self.status
        return AgendaPendingAction(
            pending_action_id=self.pending_action_id,
            operation=self.operation,
            confirmation_level=self.confirmation_level,
            risk_flags=self.risk_flags,
            created_at=self.created_at,
            expires_at=self.expires_at,
            status=next_status,
            action_hash=self.action_hash,
            draft=dict(self.draft) if next_status == STATUS_PENDING else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'pending_action_id': self.pending_action_id,
            'operation': self.operation,
            'confirmation_level': self.confirmation_level,
            'risk_flags': list(self.risk_flags),
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'status': self.status,
            'action_hash': self.action_hash,
            'draft_private': bool(self.draft),
            'draft_hash': self.action_hash,
        }

    def to_content_free_dict(self) -> dict[str, Any]:
        return {
            'pending_action_id': self.pending_action_id,
            'operation': self.operation,
            'confirmation_level': self.confirmation_level,
            'risk_flags': list(self.risk_flags),
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'status': self.status,
            'action_hash': self.action_hash,
            'draft_private': bool(self.draft),
            'content_free': True,
        }


@dataclass(frozen=True)
class AgendaPendingState:
    schema_version: str = SCHEMA_VERSION
    conversation_id: str = ''
    actions: tuple[AgendaPendingAction, ...] = ()
    updated_at: str = ''

    @classmethod
    def empty(cls, *, conversation_id: str = '') -> 'AgendaPendingState':
        return cls(conversation_id=_safe_token(conversation_id, max_chars=160))

    @classmethod
    def from_mapping(cls, value: Any, *, conversation_id: str = '') -> 'AgendaPendingState':
        data = _mapping(value)
        if data.get('schema_version') != SCHEMA_VERSION:
            return cls.empty(conversation_id=conversation_id)
        actions = tuple(
            action
            for action in (_action_from_mapping(item) for item in _sequence(data.get('actions')))
            if action is not None
        )[:MAX_ACTIONS]
        return cls(
            conversation_id=_safe_token(data.get('conversation_id'), max_chars=160)
            or _safe_token(conversation_id, max_chars=160),
            actions=actions,
            updated_at=_safe_timestamp(data.get('updated_at')),
        )

    @property
    def present(self) -> bool:
        return bool(self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': SCHEMA_VERSION,
            'conversation_id': self.conversation_id,
            'actions': [action.to_dict() for action in self.actions],
            'updated_at': self.updated_at,
        }

    def to_agent_state(self, *, now_iso: str = '') -> dict[str, Any]:
        state = expire_pending_actions(self, now_iso=now_iso) if now_iso else self
        active = [action for action in state.actions if action.status == STATUS_PENDING]
        return {
            'schema_version': SCHEMA_VERSION,
            'persistence_mode': PERSISTENCE_MODE,
            'pending_action_count': len(active),
            'pending_actions': [action.to_content_free_dict() for action in active[:MAX_ACTIONS]],
            'content_free': True,
        }

    def to_observability(self, *, now_iso: str = '') -> dict[str, Any]:
        state = expire_pending_actions(self, now_iso=now_iso) if now_iso else self
        active = [action for action in state.actions if action.status == STATUS_PENDING]
        return {
            'schema_version': SCHEMA_VERSION,
            'persistence_mode': PERSISTENCE_MODE,
            'present': state.present,
            'action_count': len(state.actions),
            'active_action_count': len(active),
            'pending_action_hashes': [agent_contract.sha256_12(action.pending_action_id) for action in active],
            'operation_counts': _operation_counts(active),
            'updated_at_present': bool(state.updated_at),
            'content_free': True,
        }


def read_state_from_conversation(conversation: Mapping[str, Any]) -> AgendaPendingState:
    conversation_id = _safe_token(conversation.get('id'), max_chars=160)
    top_level_state = _mapping(conversation.get(META_KEY))
    if top_level_state:
        return AgendaPendingState.from_mapping(top_level_state, conversation_id=conversation_id)
    for message in reversed(_sequence(conversation.get('messages'))):
        meta = _mapping(_mapping(message).get('meta'))
        raw_state = meta.get(META_KEY)
        if raw_state:
            state = AgendaPendingState.from_mapping(raw_state, conversation_id=conversation_id)
            if state.present:
                return state
    return AgendaPendingState.empty(conversation_id=conversation_id)


def attach_state_to_latest_user_message(
    conversation: dict[str, Any],
    state: AgendaPendingState | None,
) -> bool:
    if state is None or not state.present:
        return False
    messages = conversation.get('messages')
    if not isinstance(messages, list):
        return False
    for message in reversed(messages):
        if not isinstance(message, dict) or str(message.get('role') or '') != 'user':
            continue
        meta = message.get('meta')
        if not isinstance(meta, dict):
            meta = {}
        meta[META_KEY] = state.to_dict()
        message['meta'] = meta
        return True
    return False


def create_pending_action(
    state: AgendaPendingState,
    *,
    operation: str,
    confirmation_level: str,
    risk_flags: Sequence[str] = (),
    draft: Mapping[str, Any] | None = None,
    now_iso: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    id_factory: Callable[[], str] | None = None,
) -> tuple[AgendaPendingState, AgendaPendingAction]:
    base = expire_pending_actions(state, now_iso=now_iso)
    created_at = _format_iso(_parse_iso(now_iso) or datetime.now(timezone.utc))
    expires_at = _format_iso((_parse_iso(created_at) or datetime.now(timezone.utc)) + timedelta(seconds=max(1, int(ttl_seconds))))
    safe_draft = _safe_draft(draft or {})
    action = AgendaPendingAction(
        pending_action_id=_new_pending_action_id(id_factory=id_factory),
        operation=operation if operation in OPERATIONS else OPERATION_CREATE,
        confirmation_level=(
            confirmation_level
            if confirmation_level in {CONFIRMATION_SIMPLE, CONFIRMATION_REINFORCED}
            else CONFIRMATION_SIMPLE
        ),
        risk_flags=tuple(_safe_token(flag, max_chars=80) for flag in risk_flags if _safe_token(flag, max_chars=80))[:12],
        created_at=created_at,
        expires_at=expires_at,
        status=STATUS_PENDING,
        action_hash=_draft_hash(safe_draft),
        draft=safe_draft,
    )
    _remember_private_draft(action)
    all_actions = tuple([*base.actions, action])
    actions = all_actions[-MAX_ACTIONS:]
    kept_ids = {item.pending_action_id for item in actions}
    for removed in all_actions:
        if removed.pending_action_id not in kept_ids:
            _forget_private_draft(removed.pending_action_id)
    return (
        AgendaPendingState(
            conversation_id=base.conversation_id,
            actions=actions,
            updated_at=created_at,
        ),
        action,
    )


def find_pending_action(
    state: AgendaPendingState,
    pending_action_id: str,
    *,
    now_iso: str = '',
) -> tuple[AgendaPendingState, AgendaPendingAction | None]:
    normalized = _safe_token(pending_action_id, max_chars=160)
    current = expire_pending_actions(state, now_iso=now_iso) if now_iso else state
    for action in current.actions:
        if action.pending_action_id == normalized:
            return current, action
    return current, None


def cancel_pending_action(
    state: AgendaPendingState,
    pending_action_id: str,
    *,
    now_iso: str,
) -> tuple[AgendaPendingState, AgendaPendingAction | None]:
    current, action = find_pending_action(state, pending_action_id, now_iso=now_iso)
    if action is None:
        return current, None
    updated_actions = tuple(
        item.with_status(STATUS_CANCELLED) if item.pending_action_id == action.pending_action_id else item
        for item in current.actions
    )
    cancelled = next(item for item in updated_actions if item.pending_action_id == action.pending_action_id)
    _forget_private_draft(cancelled.pending_action_id)
    return (
        AgendaPendingState(
            conversation_id=current.conversation_id,
            actions=updated_actions,
            updated_at=_format_iso(_parse_iso(now_iso) or datetime.now(timezone.utc)),
        ),
        cancelled,
    )


def mark_pending_action_executed(
    state: AgendaPendingState,
    pending_action_id: str,
    *,
    now_iso: str,
) -> tuple[AgendaPendingState, AgendaPendingAction | None]:
    current, action = find_pending_action(state, pending_action_id, now_iso=now_iso)
    if action is None or action.status != STATUS_PENDING:
        return current, action
    updated_actions = tuple(
        item.with_status(STATUS_EXECUTED) if item.pending_action_id == action.pending_action_id else item
        for item in current.actions
    )
    executed = next(item for item in updated_actions if item.pending_action_id == action.pending_action_id)
    _forget_private_draft(executed.pending_action_id)
    return (
        AgendaPendingState(
            conversation_id=current.conversation_id,
            actions=updated_actions,
            updated_at=_format_iso(_parse_iso(now_iso) or datetime.now(timezone.utc)),
        ),
        executed,
    )


def expire_pending_actions(state: AgendaPendingState, *, now_iso: str) -> AgendaPendingState:
    if not now_iso or not state.actions:
        return state
    changed = False
    actions: list[AgendaPendingAction] = []
    for action in state.actions:
        if action.status == STATUS_PENDING and action.expired_at(now_iso):
            _forget_private_draft(action.pending_action_id)
            actions.append(action.with_status(STATUS_EXPIRED))
            changed = True
        else:
            actions.append(action)
    if not changed:
        return state
    return AgendaPendingState(
        conversation_id=state.conversation_id,
        actions=tuple(actions),
        updated_at=_format_iso(_parse_iso(now_iso) or datetime.now(timezone.utc)),
    )


def build_content_free_draft(plan: agent_contract.AgendaAgentPlan, *, operation: str) -> dict[str, Any]:
    tool_refs: list[dict[str, Any]] = []
    for call in plan.tool_calls:
        params = dict(call.params or {})
        tool_refs.append(
            {
                'tool_name': str(call.tool_name or ''),
                'event_id_hash': agent_contract.sha256_12(params.get('event_id')),
                'calendar_id_hash': agent_contract.sha256_12(params.get('calendar_id')),
                'query_hash': agent_contract.sha256_12(params.get('query')),
            }
        )
    calendar_ids = tuple(str(item or '') for item in (plan.calendar_scope.get('calendar_ids') or ()))
    return {
        'schema_version': 'frida_agenda_pending_draft_v1',
        'product_method': str(plan.product_method or ''),
        'operation': operation,
        'intent_hash': agent_contract.sha256_12(plan.intent),
        'intent_chars': len(str(plan.intent or '')),
        'calendar_count': len(calendar_ids),
        'calendar_id_hashes': [agent_contract.sha256_12(item) for item in calendar_ids],
        'family_calendar': bool(plan.calendar_scope.get('family_calendar')),
        'time_kind': str(plan.time_scope.get('kind') or ''),
        'start': str(plan.time_scope.get('start') or ''),
        'end': str(plan.time_scope.get('end') or ''),
        'timezone': str(plan.time_scope.get('timezone') or ''),
        'tool_refs': tool_refs[:4],
        'content_free': True,
    }


def private_draft_for_action(action: AgendaPendingAction | None) -> dict[str, Any]:
    if action is None:
        return {}
    draft = dict(action.draft or {})
    if draft:
        return draft
    stored = _PRIVATE_DRAFTS.get(action.pending_action_id) or {}
    if stored and _draft_hash(stored) == action.action_hash:
        return dict(stored)
    return {}


def _action_from_mapping(value: Any) -> AgendaPendingAction | None:
    data = _mapping(value)
    pending_action_id = _safe_token(data.get('pending_action_id'), max_chars=160)
    operation = _safe_token(data.get('operation'), max_chars=40)
    confirmation_level = _safe_token(data.get('confirmation_level'), max_chars=40)
    status = _safe_token(data.get('status'), max_chars=40) or STATUS_PENDING
    if not pending_action_id or operation not in OPERATIONS:
        return None
    if confirmation_level not in {CONFIRMATION_SIMPLE, CONFIRMATION_REINFORCED}:
        return None
    if status not in {STATUS_PENDING, STATUS_CANCELLED, STATUS_EXPIRED, STATUS_EXECUTED}:
        status = STATUS_PENDING
    return AgendaPendingAction(
        pending_action_id=pending_action_id,
        operation=operation,
        confirmation_level=confirmation_level,
        risk_flags=tuple(_safe_token(flag, max_chars=80) for flag in _sequence(data.get('risk_flags')))[:12],
        created_at=_safe_timestamp(data.get('created_at')),
        expires_at=_safe_timestamp(data.get('expires_at')),
        status=status,
        action_hash=_safe_hash(data.get('action_hash')),
        draft=_private_draft_from_mapping(pending_action_id, data),
    )


def _safe_draft(value: Any) -> dict[str, Any]:
    data = _mapping(value)
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=True, default=str)
    if len(encoded) > 4000:
        return {'schema_version': 'frida_agenda_pending_draft_v1', 'truncated': True, 'content_free': True}
    return json.loads(encoded) if encoded else {}


def _remember_private_draft(action: AgendaPendingAction) -> None:
    if action.draft:
        _PRIVATE_DRAFTS[action.pending_action_id] = dict(action.draft)


def _forget_private_draft(pending_action_id: str) -> None:
    _PRIVATE_DRAFTS.pop(str(pending_action_id or ''), None)


def _private_draft_from_mapping(pending_action_id: str, data: Mapping[str, Any]) -> dict[str, Any]:
    stored = _PRIVATE_DRAFTS.get(pending_action_id) or {}
    if stored and _draft_hash(stored) == _safe_hash(data.get('action_hash')):
        return dict(stored)
    return {}


def _draft_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(value), sort_keys=True, ensure_ascii=True, default=str)
    return agent_contract.sha256_12(encoded)


def _new_pending_action_id(*, id_factory: Callable[[], str] | None = None) -> str:
    if id_factory is not None:
        candidate = _safe_token(id_factory(), max_chars=160)
        if candidate:
            return candidate
    return f'agenda-pending-{uuid.uuid4().hex[:12]}'


def _operation_counts(actions: Sequence[AgendaPendingAction]) -> dict[str, int]:
    return {
        operation: sum(1 for action in actions if action.operation == operation)
        for operation in sorted(OPERATIONS)
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return ()


def _safe_token(value: Any, *, max_chars: int) -> str:
    text = str(value or '').strip()
    if not text or len(text) > max_chars:
        return ''
    if any(char not in _SAFE_TOKEN_CHARS for char in text):
        return ''
    lowered = text.lower()
    if lowered.startswith(('uid:', 'uid=', 'etag:', 'etag=')) or '://' in lowered:
        return ''
    return text


def _safe_timestamp(value: Any) -> str:
    text = str(value or '').strip()
    if not text or len(text) > 40:
        return ''
    return _format_iso(_parse_iso(text)) if _parse_iso(text) is not None else ''


def _safe_hash(value: Any) -> str:
    text = str(value or '').strip()
    if len(text) == 12 and all(char in '0123456789abcdef' for char in text):
        return text
    return ''


def _parse_iso(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_iso(value: datetime | None) -> str:
    if value is None:
        return ''
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
