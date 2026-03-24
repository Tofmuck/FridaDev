from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Tuple

import config


SECTION_NAMES: Tuple[str, ...] = (
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

    def public_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
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
    fields: Tuple[FieldSpec, ...]

    def field_names(self) -> Tuple[str, ...]:
        return tuple(field.key for field in self.fields)

    def field_map(self) -> Dict[str, FieldSpec]:
        return {field.key: field for field in self.fields}

    def public_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'fields': [field.public_dict() for field in self.fields],
        }


@dataclass(frozen=True)
class SectionSeedBundle:
    section: str
    payload: Dict[str, Dict[str, Any]]
    secret_values: Dict[str, str]


SECTION_SPECS: Dict[str, SectionSpec] = {
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


def list_sections() -> Tuple[str, ...]:
    return SECTION_NAMES


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


def describe_section(section: str) -> Dict[str, Any]:
    return get_section_spec(section).public_dict()


def normalize_stored_payload(
    section: str,
    payload: Mapping[str, Any],
    *,
    default_origin: str = 'manual_sql',
) -> Dict[str, Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise TypeError('payload must be a mapping')

    normalized: Dict[str, Dict[str, Any]] = {}
    for field_name, raw_value in payload.items():
        spec = get_field_spec(section, field_name)
        if not isinstance(raw_value, Mapping):
            raise TypeError(f'field payload must be a mapping: {section}.{field_name}')

        origin = str(raw_value.get('origin') or default_origin)

        if spec.is_secret:
            if 'value' in raw_value:
                raise ValueError(f'secret field does not accept plain value: {section}.{field_name}')

            encrypted_value = raw_value.get('value_encrypted')
            is_set = bool(raw_value.get('is_set') or encrypted_value)
            field_payload: Dict[str, Any] = {
                'is_secret': True,
                'is_set': is_set,
                'origin': origin,
            }
            if encrypted_value not in (None, ''):
                field_payload['value_encrypted'] = encrypted_value
        else:
            if 'value_encrypted' in raw_value:
                raise ValueError(f'non-secret field does not accept encrypted value: {section}.{field_name}')
            if 'value' not in raw_value:
                raise ValueError(f'non-secret field requires value: {section}.{field_name}')
            field_payload = {
                'value': raw_value.get('value'),
                'is_secret': False,
                'origin': origin,
            }

        normalized[str(field_name)] = field_payload

    return normalized


def redact_payload_for_api(section: str, payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    redacted: Dict[str, Dict[str, Any]] = {}
    for field_name, field_payload in normalize_stored_payload(section, payload).items():
        spec = get_field_spec(section, field_name)
        if spec.is_secret:
            redacted[field_name] = {
                'is_secret': True,
                'is_set': bool(field_payload.get('is_set')),
                'origin': field_payload.get('origin'),
            }
        else:
            redacted[field_name] = dict(field_payload)
    return redacted


def _seed_value(section: str, field: str) -> Any:
    values: Dict[tuple[str, str], Any] = {
        ('main_model', 'base_url'): config.OR_BASE,
        ('main_model', 'model'): config.OR_MODEL,
        ('main_model', 'api_key'): config.OR_KEY,
        ('main_model', 'referer'): config.OR_REFERER,
        ('main_model', 'app_name'): config.OR_TITLE_BASE,
        ('main_model', 'title_llm'): config.OR_TITLE_LLM,
        ('main_model', 'title_arbiter'): config.OR_TITLE_ARBITER,
        ('main_model', 'title_resumer'): config.OR_TITLE_RESUMER,
        ('main_model', 'temperature'): 0.4,
        ('main_model', 'top_p'): 1.0,
        ('arbiter_model', 'model'): config.ARBITER_MODEL,
        ('arbiter_model', 'temperature'): 0.0,
        ('arbiter_model', 'top_p'): 1.0,
        ('arbiter_model', 'timeout_s'): config.ARBITER_TIMEOUT_S,
        ('summary_model', 'model'): config.SUMMARY_MODEL,
        ('summary_model', 'temperature'): 0.3,
        ('summary_model', 'top_p'): 1.0,
        ('embedding', 'endpoint'): config.EMBED_BASE_URL,
        ('embedding', 'model'): 'intfloat/multilingual-e5-small',
        ('embedding', 'token'): config.EMBED_TOKEN,
        ('embedding', 'dimensions'): config.EMBED_DIM,
        ('embedding', 'top_k'): config.MEMORY_TOP_K,
        ('database', 'backend'): 'postgresql',
        ('services', 'searxng_url'): config.SEARXNG_URL,
        ('services', 'searxng_results'): config.SEARXNG_RESULTS,
        ('services', 'crawl4ai_url'): config.CRAWL4AI_URL,
        ('services', 'crawl4ai_token'): config.CRAWL4AI_TOKEN,
        ('services', 'crawl4ai_top_n'): config.CRAWL4AI_TOP_N,
        ('services', 'crawl4ai_max_chars'): config.CRAWL4AI_MAX_CHARS,
        ('resources', 'llm_identity_path'): config.FRIDA_LLM_IDENTITY_PATH,
        ('resources', 'user_identity_path'): config.FRIDA_USER_IDENTITY_PATH,
    }
    spec = get_field_spec(section, field)
    return values.get((section, field), spec.seed_default)


def build_env_seed_bundle(section: str) -> SectionSeedBundle:
    spec = get_section_spec(section)
    payload: Dict[str, Dict[str, Any]] = {}
    secret_values: Dict[str, str] = {}

    for field in spec.fields:
        value = _seed_value(section, field.key)

        if field.is_secret:
            is_set = False
            if field.seed_from_env and value not in (None, ''):
                secret_values[field.key] = str(value)
                is_set = True

            payload[field.key] = {
                'is_secret': True,
                'is_set': is_set,
                'origin': 'env_seed',
            }
            continue

        payload[field.key] = {
            'value': value,
            'is_secret': False,
            'origin': 'env_seed',
        }

    return SectionSeedBundle(section=section, payload=payload, secret_values=secret_values)


def get_unseeded_sections(existing_sections: Iterable[str]) -> Tuple[str, ...]:
    existing = {str(section) for section in existing_sections}
    return tuple(section for section in SECTION_NAMES if section not in existing)


def build_env_seed_plan(existing_sections: Iterable[str] = ()) -> Tuple[SectionSeedBundle, ...]:
    return tuple(build_env_seed_bundle(section) for section in get_unseeded_sections(existing_sections))
