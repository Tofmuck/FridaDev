# Example configuration file for public repository
# Keep secrets in app/.env (not versioned).
# Thresholds are starting points and should be tuned with metrics.

#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    _env = Path(__file__).with_name('.env')
    if _env.exists():
        load_dotenv(_env)
except Exception:
    pass


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}


# OpenRouter
OR_BASE = os.environ.get('OPENROUTER_BASE', 'https://openrouter.ai/api/v1').rstrip('/')
OR_MODEL = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-5.1')
OR_KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()
OR_REFERER = os.environ.get('OPENROUTER_REFERER', os.environ.get('OPENROUTER_SITE_URL', '')).strip()
OR_TITLE_BASE = os.environ.get('OPENROUTER_APP_NAME', 'FridaDev').strip() or 'FridaDev'
OR_TITLE_LLM = os.environ.get('OPENROUTER_TITLE_LLM', f'{OR_TITLE_BASE}/LLM').strip() or f'{OR_TITLE_BASE}/LLM'
OR_TITLE_ARBITER = os.environ.get('OPENROUTER_TITLE_ARBITER', f'{OR_TITLE_BASE}/Arbiter').strip() or f'{OR_TITLE_BASE}/Arbiter'
OR_TITLE_RESUMER = os.environ.get('OPENROUTER_TITLE_RESUMER', f'{OR_TITLE_BASE}/Resumer').strip() or f'{OR_TITLE_BASE}/Resumer'
OR_TITLE_STIMMUNG_AGENT = os.environ.get(
    'OPENROUTER_TITLE_STIMMUNG_AGENT',
    f'{OR_TITLE_BASE}/StimmungAgent',
).strip() or f'{OR_TITLE_BASE}/StimmungAgent'
OR_TITLE = OR_TITLE_LLM

# SearXNG
SEARXNG_URL = os.environ.get('SEARXNG_URL', 'http://127.0.0.1:8092')
SEARXNG_RESULTS = _env_int('SEARXNG_RESULTS', 5)

# Crawl4AI
CRAWL4AI_URL = os.environ.get('CRAWL4AI_URL', 'http://127.0.0.1:11235')
CRAWL4AI_TOKEN = os.environ.get('CRAWL4AI_TOKEN', '')
CRAWL4AI_TOP_N = _env_int('CRAWL4AI_TOP_N', 2)
CRAWL4AI_MAX_CHARS = _env_int('CRAWL4AI_MAX_CHARS', 5000)
CRAWL4AI_EXPLICIT_URL_MAX_CHARS = _env_int('CRAWL4AI_EXPLICIT_URL_MAX_CHARS', 25000)

# Server
WEB_PORT = _env_int('FRIDA_WEB_PORT', 8089)
TIMEOUT_S = _env_int('FRIDA_TIMEOUT', 900)

# Admin API security
FRIDA_ADMIN_TOKEN = os.environ.get('FRIDA_ADMIN_TOKEN', '').strip()
FRIDA_ADMIN_LAN_ONLY = _env_bool('FRIDA_ADMIN_LAN_ONLY', False)
FRIDA_ADMIN_ALLOWED_CIDRS = os.environ.get(
    'FRIDA_ADMIN_ALLOWED_CIDRS',
    '127.0.0.1/32,::1/128',
)

# LLM context window
MAX_TOKENS = _env_int('FRIDA_MAX_TOKENS', 35000)

# Prompt files
MAIN_SYSTEM_PROMPT_PATH = os.environ.get('MAIN_SYSTEM_PROMPT_PATH', 'prompts/main_system.txt')
MAIN_HERMENEUTICAL_PROMPT_PATH = os.environ.get(
    'MAIN_HERMENEUTICAL_PROMPT_PATH',
    'prompts/main_hermeneutical.txt',
)
SUMMARY_SYSTEM_PROMPT_PATH = os.environ.get('SUMMARY_SYSTEM_PROMPT_PATH', 'prompts/summary_system.txt')
WEB_REFORMULATION_PROMPT_PATH = os.environ.get(
    'WEB_REFORMULATION_PROMPT_PATH',
    'prompts/web_reformulation.txt',
)

# Local timezone
FRIDA_TIMEZONE = os.environ.get('FRIDA_TIMEZONE', 'Europe/Paris')

# Identity files
FRIDA_LLM_IDENTITY_PATH = os.environ.get('FRIDA_LLM_IDENTITY_PATH', 'data/identity/llm_identity.txt')
FRIDA_USER_IDENTITY_PATH = os.environ.get('FRIDA_USER_IDENTITY_PATH', 'data/identity/user_identity.txt')

# PostgreSQL / pgvector
FRIDA_MEMORY_DB_DSN = os.environ.get('FRIDA_MEMORY_DB_DSN', 'postgresql://user:password@127.0.0.1:5432/fridadev')
FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY = os.environ.get('FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY', '').strip()

# Embedding service
EMBED_BASE_URL = os.environ.get('EMBED_BASE_URL', 'https://embed.example.com')
EMBED_TOKEN = os.environ.get('EMBED_TOKEN', '')
EMBED_DIM = _env_int('EMBED_DIM', 384)
MEMORY_TOP_K = _env_int('MEMORY_TOP_K', 5)

# Evolving identities
IDENTITY_DECAY_FACTOR = _env_float('IDENTITY_DECAY_FACTOR', 0.95)
IDENTITY_TOP_N = _env_int('IDENTITY_TOP_N', 15)

# Memory arbiter
ARBITER_MODEL = os.environ.get('ARBITER_MODEL', 'openai/gpt-5.4-mini')
ARBITER_TIMEOUT_S = _env_int('ARBITER_TIMEOUT_S', 10)
ARBITER_PROMPT_PATH = os.environ.get('ARBITER_PROMPT_PATH', 'prompts/arbiter.txt')
IDENTITY_EXTRACTOR_PROMPT_PATH = os.environ.get('IDENTITY_EXTRACTOR_PROMPT_PATH', 'prompts/identity_extractor.txt')

# Periodic summaries
SUMMARY_THRESHOLD_TOKENS = _env_int('SUMMARY_THRESHOLD_TOKENS', 35000)
SUMMARY_TARGET_TOKENS = _env_int('SUMMARY_TARGET_TOKENS', 2000)
SUMMARY_KEEP_TURNS = _env_int('SUMMARY_KEEP_TURNS', 5)
SUMMARY_MODEL = os.environ.get('SUMMARY_MODEL', 'openai/gpt-5.4-mini')

# Hermeneutics.
# These thresholds are seeds, not fixed truths.
HERMENEUTIC_SCHEMA_VERSION = os.environ.get('HERMENEUTIC_SCHEMA_VERSION', 'v1')

_ALLOWED_HERMENEUTIC_MODES = {
    'off',
    'shadow',
    'enforced_identities',
    'enforced_all',
}


def _normalize_hermeneutic_mode(raw: str) -> str:
    mode = str(raw or 'shadow').strip().lower()
    aliases = {
        'enforced': 'enforced_all',
        'enforced_full': 'enforced_all',
        'enforced_memory': 'enforced_all',
        'enforced_identity': 'enforced_identities',
    }
    mode = aliases.get(mode, mode)
    if mode not in _ALLOWED_HERMENEUTIC_MODES:
        return 'shadow'
    return mode


HERMENEUTIC_MODE = _normalize_hermeneutic_mode(os.environ.get('HERMENEUTIC_MODE', 'shadow'))

ARBITER_MIN_SEMANTIC_RELEVANCE = _env_float('ARBITER_MIN_SEMANTIC_RELEVANCE', 0.62)
ARBITER_MIN_CONTEXTUAL_GAIN = _env_float('ARBITER_MIN_CONTEXTUAL_GAIN', 0.55)
ARBITER_MAX_KEPT_TRACES = _env_int('ARBITER_MAX_KEPT_TRACES', 3)

IDENTITY_MIN_CONFIDENCE = _env_float('IDENTITY_MIN_CONFIDENCE', 0.72)
IDENTITY_DEFER_MIN_CONFIDENCE = _env_float('IDENTITY_DEFER_MIN_CONFIDENCE', 0.58)
IDENTITY_MIN_RECURRENCE_FOR_DURABLE = _env_int('IDENTITY_MIN_RECURRENCE_FOR_DURABLE', 2)
IDENTITY_RECURRENCE_WINDOW_DAYS = _env_int('IDENTITY_RECURRENCE_WINDOW_DAYS', 30)
IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS = _env_int('IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS', 2)
IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS = _env_int('IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS', 6)

CONTEXT_HINTS_MAX_ITEMS = _env_int('CONTEXT_HINTS_MAX_ITEMS', 2)
CONTEXT_HINTS_MAX_TOKENS = _env_int('CONTEXT_HINTS_MAX_TOKENS', 120)
CONTEXT_HINTS_MAX_AGE_DAYS = _env_int('CONTEXT_HINTS_MAX_AGE_DAYS', 7)
CONTEXT_HINTS_MIN_CONFIDENCE = _env_float('CONTEXT_HINTS_MIN_CONFIDENCE', 0.60)

IDENTITY_MAX_TOKENS = _env_int('IDENTITY_MAX_TOKENS', 500)


def log_hermeneutic_effective_config(logger: Any) -> None:
    logger.info(
        'hermeneutic_config mode=%s schema=%s min_semantic=%.3f min_gain=%.3f max_kept=%s '
        'id_conf=%.3f id_defer=%.3f recur_days=%s recur_distinct=%s recur_gap_h=%s '
        'ctx_items=%s ctx_tokens=%s ctx_age_days=%s ctx_min_conf=%.3f id_max_tokens=%s',
        HERMENEUTIC_MODE,
        HERMENEUTIC_SCHEMA_VERSION,
        ARBITER_MIN_SEMANTIC_RELEVANCE,
        ARBITER_MIN_CONTEXTUAL_GAIN,
        ARBITER_MAX_KEPT_TRACES,
        IDENTITY_MIN_CONFIDENCE,
        IDENTITY_DEFER_MIN_CONFIDENCE,
        IDENTITY_RECURRENCE_WINDOW_DAYS,
        IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS,
        IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS,
        CONTEXT_HINTS_MAX_ITEMS,
        CONTEXT_HINTS_MAX_TOKENS,
        CONTEXT_HINTS_MAX_AGE_DAYS,
        CONTEXT_HINTS_MIN_CONFIDENCE,
        IDENTITY_MAX_TOKENS,
    )
