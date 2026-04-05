from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
HOST_STATE_ROOT = REPO_ROOT / 'state'


@dataclass(frozen=True)
class StaticIdentityPathResolution:
    configured_path: str
    checked_paths: tuple[Path, ...]
    resolved_path: Path | None
    resolution_kind: str

    @property
    def exists(self) -> bool:
        return self.resolved_path is not None and self.resolved_path.is_file()

    def validation_detail(self, field: str) -> str:
        checked = ', '.join(str(path) for path in self.checked_paths) or 'none'
        resolved = str(self.resolved_path) if self.resolved_path is not None else 'unresolved'
        configured = self.configured_path or 'missing'
        return (
            f'{field}={configured}; '
            f'resolved_path={resolved}; '
            f'resolution={self.resolution_kind}; '
            f'checked_paths=[{checked}]'
        )


def resolve_static_identity_path(path_str: str) -> StaticIdentityPathResolution:
    configured = str(path_str or '').strip()
    if not configured:
        return StaticIdentityPathResolution(
            configured_path='',
            checked_paths=(),
            resolved_path=None,
            resolution_kind='missing_configured_path',
        )

    candidate = Path(configured)
    if candidate.is_absolute():
        absolute_path = candidate.resolve()
        return StaticIdentityPathResolution(
            configured_path=configured,
            checked_paths=(absolute_path,),
            resolved_path=absolute_path if absolute_path.is_file() else None,
            resolution_kind='absolute' if absolute_path.is_file() else 'absolute_missing',
        )

    runtime_path = (APP_ROOT / candidate).resolve()
    checked_paths = [runtime_path]
    if runtime_path.is_file():
        return StaticIdentityPathResolution(
            configured_path=configured,
            checked_paths=tuple(checked_paths),
            resolved_path=runtime_path,
            resolution_kind='app_relative',
        )

    if candidate.parts and candidate.parts[0] == 'data':
        host_state_path = (HOST_STATE_ROOT / candidate).resolve()
        checked_paths.append(host_state_path)
        if host_state_path.is_file():
            return StaticIdentityPathResolution(
                configured_path=configured,
                checked_paths=tuple(checked_paths),
                resolved_path=host_state_path,
                resolution_kind='host_state_mirror',
            )

    return StaticIdentityPathResolution(
        configured_path=configured,
        checked_paths=tuple(checked_paths),
        resolved_path=None,
        resolution_kind='relative_missing',
    )
