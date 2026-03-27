from __future__ import annotations

from typing import Any, Callable


def connect_runtime_database(
    *,
    psycopg_module: Any,
    config_module: Any,
    runtime_settings_module: Any,
    runtime_db_bootstrap_module: Any,
) -> Any:
    return runtime_db_bootstrap_module.connect_runtime_database(
        psycopg_module,
        config_module,
        runtime_settings_module,
    )


def runtime_database_view(
    *,
    runtime_settings_module: Any,
    runtime_db_bootstrap_module: Any,
) -> Any:
    return runtime_db_bootstrap_module.runtime_database_view(runtime_settings_module)


def runtime_database_backend(
    *,
    runtime_settings_module: Any,
    runtime_db_bootstrap_module: Any,
) -> str:
    return runtime_db_bootstrap_module.runtime_database_backend(runtime_settings_module)


def bootstrap_database_dsn(
    *,
    config_module: Any,
    runtime_settings_module: Any,
    runtime_db_bootstrap_module: Any,
) -> str:
    return runtime_db_bootstrap_module.bootstrap_database_dsn(
        config_module,
        runtime_settings_module,
    )


def runtime_embedding_view(*, runtime_settings_module: Any) -> Any:
    return runtime_settings_module.get_embedding_settings()


def runtime_embedding_value(field: str, *, runtime_settings_module: Any) -> Any:
    view = runtime_embedding_view(runtime_settings_module=runtime_settings_module)
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return payload['value']

    env_bundle = runtime_settings_module.build_env_seed_bundle('embedding')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return fallback['value']

    raise KeyError(f'missing embedding runtime value: {field}')


def runtime_embedding_token(*, runtime_settings_module: Any) -> str:
    secret = runtime_settings_module.get_runtime_secret_value('embedding', 'token')
    return str(secret.value)


def init_db(
    *,
    conn_factory: Callable[[], Any],
    runtime_embedding_value_fn: Callable[[str], Any],
    logger: Any,
) -> None:
    """Create tables/indexes if absent. Never crash app startup when DB is unavailable."""
    embed_dim = int(runtime_embedding_value_fn('dimensions'))
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                cur.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS traces (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id TEXT        NOT NULL,
                        role            TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        timestamp       TIMESTAMPTZ,
                        embedding       vector({embed_dim}),
                        summary_id      TEXT
                    );
                    '''
                )

                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS summaries (
                        id              UUID PRIMARY KEY,
                        conversation_id TEXT        NOT NULL,
                        start_ts        TIMESTAMPTZ,
                        end_ts          TIMESTAMPTZ,
                        content         TEXT        NOT NULL,
                        embedding       vector({embed_dim})
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identities (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        subject         TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        weight          FLOAT       DEFAULT 1.0,
                        created_ts      TIMESTAMPTZ DEFAULT now(),
                        last_seen_ts    TIMESTAMPTZ DEFAULT now(),
                        source_trace_id UUID
                    );
                    '''
                )

                # identities migration (idempotent)
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS conversation_id TEXT;")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS stability TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS utterance_mode TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS recurrence TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS evidence_kind TEXT DEFAULT 'weak';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'accepted';")
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS content_norm TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS last_reason TEXT;')
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_state TEXT DEFAULT 'none';")
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_reason TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_actor TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_ts TIMESTAMPTZ;')

                cur.execute(
                    """
                    UPDATE identities
                    SET content_norm = lower(regexp_replace(trim(content), '\\s+', ' ', 'g'))
                    WHERE content_norm IS NULL
                    """
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identity_evidence (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id TEXT,
                        subject         TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        content_norm    TEXT,
                        stability       TEXT        DEFAULT 'unknown',
                        utterance_mode  TEXT        DEFAULT 'unknown',
                        recurrence      TEXT        DEFAULT 'unknown',
                        scope           TEXT        DEFAULT 'unknown',
                        evidence_kind   TEXT        DEFAULT 'weak',
                        confidence      FLOAT       DEFAULT 0.0,
                        status          TEXT        DEFAULT 'accepted',
                        reason          TEXT,
                        source_trace_id UUID,
                        created_ts      TIMESTAMPTZ DEFAULT now()
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS arbiter_decisions (
                        id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id       TEXT        NOT NULL,
                        candidate_id          TEXT        NOT NULL,
                        candidate_role        TEXT,
                        candidate_content     TEXT,
                        candidate_ts          TIMESTAMPTZ,
                        candidate_score       FLOAT,
                        keep                  BOOLEAN     NOT NULL,
                        semantic_relevance    FLOAT       DEFAULT 0.0,
                        contextual_gain       FLOAT       DEFAULT 0.0,
                        redundant_with_recent BOOLEAN     DEFAULT FALSE,
                        reason                TEXT,
                        model                 TEXT,
                        decision_source       TEXT        DEFAULT 'llm',
                        created_ts            TIMESTAMPTZ DEFAULT now()
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identity_conflicts (
                        id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        identity_id_a        UUID NOT NULL,
                        identity_id_b        UUID NOT NULL,
                        confidence_conflict  FLOAT DEFAULT 0.0,
                        reason               TEXT,
                        resolved_state       TEXT DEFAULT 'open',
                        created_ts           TIMESTAMPTZ DEFAULT now(),
                        resolved_ts          TIMESTAMPTZ
                    );
                    '''
                )

                # embedding indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS traces_embedding_hnsw
                    ON traces USING hnsw (embedding vector_cosine_ops);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS summaries_embedding_hnsw
                    ON summaries USING hnsw (embedding vector_cosine_ops);
                    '''
                )

                # identities indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_subject_weight_idx
                    ON identities (subject, weight DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_status_idx
                    ON identities (status);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_content_norm_idx
                    ON identities (content_norm);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_created_ts_idx
                    ON identities (created_ts DESC);
                    '''
                )

                # evidence indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_conversation_created_idx
                    ON identity_evidence (conversation_id, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_status_idx
                    ON identity_evidence (status);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_content_norm_idx
                    ON identity_evidence (content_norm);
                    '''
                )

                # arbiter indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS arbiter_decisions_conversation_created_idx
                    ON arbiter_decisions (conversation_id, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS arbiter_decisions_keep_idx
                    ON arbiter_decisions (keep);
                    '''
                )

                # conflict indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_conflicts_open_idx
                    ON identity_conflicts (resolved_state, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_conflicts_pair_idx
                    ON identity_conflicts (identity_id_a, identity_id_b);
                    '''
                )

            conn.commit()
        logger.info('memory_db_init ok')
    except Exception as exc:
        logger.error('memory_db_init_failed err=%s', exc)


def embed(
    text: str,
    mode: str = 'passage',
    *,
    runtime_embedding_value_fn: Callable[[str], Any],
    runtime_embedding_token_fn: Callable[[], str],
    requests_module: Any,
) -> list[float]:
    """
    Call OVH embedding service.
    mode='passage' for stored docs, mode='query' for retrieval requests.
    """
    prefix = 'query: ' if mode == 'query' else 'passage: '
    endpoint = str(runtime_embedding_value_fn('endpoint')).rstrip('/')
    model = str(runtime_embedding_value_fn('model') or '').strip()
    response = requests_module.post(
        f'{endpoint}/embed',
        headers={
            'X-Embed-Token': runtime_embedding_token_fn(),
            'Content-Type': 'application/json',
        },
        json={
            'inputs': [f'{prefix}{text}'],
            'model': model,
        },
        timeout=(5, 120),
    )
    response.raise_for_status()
    return response.json()[0]
