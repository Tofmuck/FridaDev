from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
HOST_STATE_ROOT = REPO_ROOT / 'state'
ALLOWED_RELATIVE_PREFIX = ('data', 'identity')


@dataclass(frozen=True)
class StaticIdentityPathResolution:
    configured_path: str
    checked_paths: tuple[Path, ...]
    resolved_path: Path | None
    resolution_kind: str
    within_allowed_roots: bool = False

    @property
    def exists(self) -> bool:
        return (
            self.resolved_path is not None
            and self.resolved_path.is_file()
            and self.within_allowed_roots
        )

    def validation_detail(self, field: str) -> str:
        checked = ', '.join(str(path) for path in self.checked_paths) or 'none'
        resolved = str(self.resolved_path) if self.resolved_path is not None else 'unresolved'
        configured = self.configured_path or 'missing'
        allowed_roots = ', '.join(str(path) for path in allowed_static_identity_roots())
        return (
            f'{field}={configured}; '
            f'resolved_path={resolved}; '
            f'resolution={self.resolution_kind}; '
            f'within_allowed_roots={self.within_allowed_roots}; '
            f'allowed_roots=[{allowed_roots}]; '
            f'checked_paths=[{checked}]'
        )


def allowed_static_identity_roots() -> tuple[Path, ...]:
    return (
        (APP_ROOT / 'data' / 'identity').resolve(),
        (HOST_STATE_ROOT / 'data' / 'identity').resolve(),
    )


def is_within_allowed_static_identity_roots(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        resolved = path.resolve()
    except Exception:
        return False
    return any(resolved == root or root in resolved.parents for root in allowed_static_identity_roots())


def resolve_static_identity_path(path_str: str) -> StaticIdentityPathResolution:
    configured = str(path_str or '').strip()
    if not configured:
        return StaticIdentityPathResolution(
            configured_path='',
            checked_paths=(),
            resolved_path=None,
            resolution_kind='missing_configured_path',
            within_allowed_roots=False,
        )

    candidate = Path(configured)
    if candidate.is_absolute():
        absolute_path = candidate.resolve()
        within_allowed = absolute_path.is_file() and is_within_allowed_static_identity_roots(absolute_path)
        return StaticIdentityPathResolution(
            configured_path=configured,
            checked_paths=(absolute_path,),
            resolved_path=absolute_path if absolute_path.is_file() else None,
            resolution_kind=(
                'absolute'
                if absolute_path.is_file() and within_allowed
                else 'absolute_outside_allowed_roots'
                if absolute_path.is_file()
                else 'absolute_missing'
            ),
            within_allowed_roots=within_allowed,
        )

    runtime_path = (APP_ROOT / candidate).resolve()
    checked_paths = [runtime_path]
    if candidate.parts[:2] != ALLOWED_RELATIVE_PREFIX:
        return StaticIdentityPathResolution(
            configured_path=configured,
            checked_paths=tuple(checked_paths),
            resolved_path=runtime_path if runtime_path.is_file() else None,
            resolution_kind='relative_outside_allowed_roots',
            within_allowed_roots=False,
        )
    if runtime_path.is_file():
        within_allowed = is_within_allowed_static_identity_roots(runtime_path)
        return StaticIdentityPathResolution(
            configured_path=configured,
            checked_paths=tuple(checked_paths),
            resolved_path=runtime_path,
            resolution_kind='app_relative' if within_allowed else 'app_relative_outside_allowed_roots',
            within_allowed_roots=within_allowed,
        )

    if candidate.parts and candidate.parts[0] == 'data':
        host_state_path = (HOST_STATE_ROOT / candidate).resolve()
        checked_paths.append(host_state_path)
        if host_state_path.is_file():
            within_allowed = is_within_allowed_static_identity_roots(host_state_path)
            return StaticIdentityPathResolution(
                configured_path=configured,
                checked_paths=tuple(checked_paths),
                resolved_path=host_state_path,
                resolution_kind='host_state_mirror' if within_allowed else 'host_state_outside_allowed_roots',
                within_allowed_roots=within_allowed,
            )

    return StaticIdentityPathResolution(
        configured_path=configured,
        checked_paths=tuple(checked_paths),
        resolved_path=None,
        resolution_kind='relative_missing',
        within_allowed_roots=False,
    )
