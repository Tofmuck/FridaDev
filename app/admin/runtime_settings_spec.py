from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SECTION_NAMES: tuple[str, ...] = (
    'main_model',
    'arbiter_model',
    'summary_model',
    'embedding',
    'database',
    'services',
    'resources',
)


@dataclass(frozen=True)
class FieldSpec:
    key: str
    value_type: str
    is_secret: bool = False
    env_var: str | None = None
    seed_from_env: bool = True
    seed_default: Any = None

    def public_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            'key': self.key,
            'value_type': self.value_type,
            'is_secret': self.is_secret,
            'seed_from_env': self.seed_from_env,
        }
        if self.env_var:
            out['env_var'] = self.env_var
        if self.seed_default is not None:
            out['seed_default'] = self.seed_default
        return out


@dataclass(frozen=True)
class SectionSpec:
    name: str
    fields: tuple[FieldSpec, ...]

    def field_names(self) -> tuple[str, ...]:
        return tuple(field.key for field in self.fields)

    def field_map(self) -> dict[str, FieldSpec]:
        return {field.key: field for field in self.fields}

    def public_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'fields': [field.public_dict() for field in self.fields],
        }


SECRET_V1_FIELDS: tuple[tuple[str, str], ...] = (
    ('main_model', 'api_key'),
    ('embedding', 'token'),
    ('services', 'crawl4ai_token'),
    ('database', 'dsn'),
)


SECTION_SPECS: dict[str, SectionSpec] = {
    'main_model': SectionSpec(
        name='main_model',
        fields=(
            FieldSpec('base_url', 'text', env_var='OPENROUTER_BASE'),
            FieldSpec('model', 'text', env_var='OPENROUTER_MODEL'),
            FieldSpec('api_key', 'text', is_secret=True, env_var='OPENROUTER_API_KEY'),
            FieldSpec('referer', 'text', env_var='OPENROUTER_REFERER'),
            FieldSpec('app_name', 'text', env_var='OPENROUTER_APP_NAME'),
            FieldSpec('title_llm', 'text', env_var='OPENROUTER_TITLE_LLM'),
            FieldSpec('title_arbiter', 'text', env_var='OPENROUTER_TITLE_ARBITER'),
            FieldSpec('title_resumer', 'text', env_var='OPENROUTER_TITLE_RESUMER'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.4),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
            FieldSpec('response_max_tokens', 'int', seed_from_env=False, seed_default=1500),
        ),
    ),
    'arbiter_model': SectionSpec(
        name='arbiter_model',
        fields=(
            FieldSpec('model', 'text', env_var='ARBITER_MODEL'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.0),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
            FieldSpec('timeout_s', 'int', env_var='ARBITER_TIMEOUT_S'),
        ),
    ),
    'summary_model': SectionSpec(
        name='summary_model',
        fields=(
            FieldSpec('model', 'text', env_var='SUMMARY_MODEL'),
            FieldSpec('temperature', 'float', seed_from_env=False, seed_default=0.3),
            FieldSpec('top_p', 'float', seed_from_env=False, seed_default=1.0),
        ),
    ),
    'embedding': SectionSpec(
        name='embedding',
        fields=(
            FieldSpec('endpoint', 'text', env_var='EMBED_BASE_URL'),
            FieldSpec('model', 'text', seed_from_env=False, seed_default='intfloat/multilingual-e5-small'),
            FieldSpec('token', 'text', is_secret=True, env_var='EMBED_TOKEN'),
            FieldSpec('dimensions', 'int', env_var='EMBED_DIM'),
            FieldSpec('top_k', 'int', env_var='MEMORY_TOP_K'),
        ),
    ),
    'database': SectionSpec(
        name='database',
        fields=(
            FieldSpec('backend', 'text', seed_from_env=False, seed_default='postgresql'),
            FieldSpec('dsn', 'text', is_secret=True, env_var='FRIDA_MEMORY_DB_DSN', seed_from_env=False),
        ),
    ),
    'services': SectionSpec(
        name='services',
        fields=(
            FieldSpec('searxng_url', 'text', env_var='SEARXNG_URL'),
            FieldSpec('searxng_results', 'int', env_var='SEARXNG_RESULTS'),
            FieldSpec('crawl4ai_url', 'text', env_var='CRAWL4AI_URL'),
            FieldSpec('crawl4ai_token', 'text', is_secret=True, env_var='CRAWL4AI_TOKEN'),
            FieldSpec('crawl4ai_top_n', 'int', env_var='CRAWL4AI_TOP_N'),
            FieldSpec('crawl4ai_max_chars', 'int', env_var='CRAWL4AI_MAX_CHARS'),
        ),
    ),
    'resources': SectionSpec(
        name='resources',
        fields=(
            FieldSpec('llm_identity_path', 'text', env_var='FRIDA_LLM_IDENTITY_PATH'),
            FieldSpec('user_identity_path', 'text', env_var='FRIDA_USER_IDENTITY_PATH'),
        ),
    ),
}


def list_sections() -> tuple[str, ...]:
    return SECTION_NAMES


def list_secret_v1_fields() -> tuple[tuple[str, str], ...]:
    return SECRET_V1_FIELDS


def get_section_spec(section: str) -> SectionSpec:
    try:
        return SECTION_SPECS[str(section)]
    except KeyError as exc:
        raise KeyError(f'unknown runtime settings section: {section}') from exc


def get_field_spec(section: str, field: str) -> FieldSpec:
    field_map = get_section_spec(section).field_map()
    try:
        return field_map[str(field)]
    except KeyError as exc:
        raise KeyError(f'unknown runtime settings field: {section}.{field}') from exc


def describe_section(section: str) -> dict[str, Any]:
    return get_section_spec(section).public_dict()
