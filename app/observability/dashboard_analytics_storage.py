from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from observability.dashboard_observable_modules import observable_module_keys
from observability.dashboard_analytics_projection import (
    CALCULATION_VERSION,
    RECENT_GRANULARITY_DAYS,
    RETENTION_DAYS,
    SCHEMA_VERSION,
    _iso,
    _json,
    _mapping,
    _parse_ts,
    _retention_start,
    _sequence,
    _to_int,
    build_dashboard_analytics,
    build_dashboard_conversation_summaries,
    build_dashboard_materialization_status,
    build_dashboard_metric_buckets,
)

_MODULE_KEYS = tuple(observable_module_keys())


def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except ValueError:
            return {}
        if isinstance(loaded, Mapping):
            return dict(loaded)
    return {}


def _json_sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except ValueError:
            return []
        if isinstance(loaded, list):
            return loaded
    return []


def _fact_from_persisted_row(row: Sequence[Any]) -> dict[str, Any]:
    return {
        'kind': 'dashboard_turn_fact',
        'schema_version': SCHEMA_VERSION,
        'calculation_version': str(row[22] or CALCULATION_VERSION),
        'conversation_id': str(row[0] or ''),
        'turn_id': str(row[1] or ''),
        'first_ts': _iso(_parse_ts(row[2])),
        'latest_ts': _iso(_parse_ts(row[3])),
        'classification': str(row[4] or 'legacy_incomplete'),
        'score': _to_int(row[5]),
        'source_event_ids': _json_sequence(row[6]),
        'source_event_count': _to_int(row[7]),
        'source_first_event_id': row[8],
        'source_latest_event_id': row[9],
        'persistence': _json_mapping(row[10]),
        'providers': _json_mapping(row[11]),
        'rag': _json_mapping(row[12]),
        'identity': _json_mapping(row[13]),
        'hermeneutic': _json_mapping(row[14]),
        'web': _json_mapping(row[15]),
        'node_state': _json_mapping(row[16]),
        'latencies': _json_mapping(row[17]),
        'errors': _json_mapping(row[18]),
        'stage_counts': _json_mapping(row[19]),
        'flags': _json_mapping(row[20]),
        'content_availability': _json_mapping(row[21]),
        'redaction': {
            'raw_content_stored': False,
            'raw_event_payloads_included': False,
        },
    }


def _dashboard_turn_fact_select_sql() -> str:
    return '''
        SELECT
            conversation_id,
            turn_id,
            first_ts,
            latest_ts,
            classification,
            score,
            source_event_ids,
            source_event_count,
            source_first_event_id,
            source_latest_event_id,
            persistence_json,
            providers_json,
            rag_json,
            identity_json,
            hermeneutic_json,
            web_json,
            node_state_json,
            latencies_json,
            errors_json,
            stage_counts_json,
            flags_json,
            content_availability_json,
            calculation_version
        FROM observability.dashboard_turn_facts
    '''


def _read_conversation_ids_for_window(cur: Any, window_start: Any, window_end: Any) -> set[str]:
    cur.execute(
        '''
        SELECT DISTINCT conversation_id
        FROM observability.dashboard_turn_facts
        WHERE latest_ts >= %s::timestamptz
          AND latest_ts < %s::timestamptz
        ''',
        (window_start, window_end),
    )
    return {
        str(row[0] or '').strip()
        for row in cur.fetchall()
        if str(row[0] or '').strip()
    }


def _read_persisted_facts_for_conversations(cur: Any, conversation_ids: Sequence[str]) -> list[dict[str, Any]]:
    ids = [str(value or '').strip() for value in conversation_ids if str(value or '').strip()]
    if not ids:
        return []
    cur.execute(
        _dashboard_turn_fact_select_sql()
        + '''
        WHERE conversation_id = ANY(%s)
        ORDER BY latest_ts ASC, conversation_id ASC, turn_id ASC
        ''',
        (ids,),
    )
    return [_fact_from_persisted_row(row) for row in cur.fetchall()]


def _bucket_start_dt(value: datetime, granularity: str) -> datetime:
    if granularity == 'hour':
        return value.replace(minute=0, second=0, microsecond=0)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _bucket_end_dt(value: datetime, granularity: str) -> datetime:
    if granularity == 'hour':
        return value.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return value.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)


def _affected_bucket_specs(
    *,
    window_start: Any,
    window_end: Any,
    now: datetime,
    recent_granularity_days: int,
    extra_latest_times: Sequence[Any] = (),
) -> list[tuple[str, datetime, datetime]]:
    start = _parse_ts(window_start)
    end = _parse_ts(window_end)
    if not start or not end or start >= end:
        return []
    specs_by_key: dict[tuple[str, str], tuple[str, datetime, datetime]] = {}

    def add_spec(granularity: str, bucket_start: datetime) -> None:
        specs_by_key[(granularity, _iso(bucket_start) or '')] = (
            granularity,
            bucket_start,
            _bucket_end_dt(bucket_start, granularity),
        )

    day_start = _bucket_start_dt(start, 'day')
    while day_start < end:
        add_spec('day', day_start)
        day_start = _bucket_end_dt(day_start, 'day')

    recent_start = now - timedelta(days=max(1, int(recent_granularity_days)))
    hour_start = _bucket_start_dt(max(start, recent_start), 'hour')
    while hour_start < end:
        add_spec('hour', hour_start)
        hour_start = _bucket_end_dt(hour_start, 'hour')

    for value in extra_latest_times:
        parsed = _parse_ts(value)
        if not parsed:
            continue
        add_spec('day', _bucket_start_dt(parsed, 'day'))
        if parsed >= recent_start:
            add_spec('hour', _bucket_start_dt(parsed, 'hour'))

    return [
        specs_by_key[key]
        for key in sorted(specs_by_key)
    ]


def _read_persisted_facts_for_bucket(
    cur: Any,
    *,
    bucket_start: datetime,
    bucket_end: datetime,
) -> list[dict[str, Any]]:
    cur.execute(
        _dashboard_turn_fact_select_sql()
        + '''
        WHERE latest_ts >= %s::timestamptz
          AND latest_ts < %s::timestamptz
        ORDER BY latest_ts ASC, conversation_id ASC, turn_id ASC
        ''',
        (_iso(bucket_start), _iso(bucket_end)),
    )
    return [_fact_from_persisted_row(row) for row in cur.fetchall()]


def _insert_conversation_summary(cur: Any, summary: Mapping[str, Any]) -> None:
    cur.execute(
        '''
        INSERT INTO observability.dashboard_conversation_summaries (
            conversation_id, display_label, display_label_source,
            first_ts, latest_ts, turns_count, last_turn_id,
            last_classification, classification_counts_json,
            persistence_counts_json, modules_involved_json,
            memory_used_turns, web_requested_turns, web_success_turns,
            web_injected_turns, error_count, fallback_count,
            last_problem_reason_code, source_json, calculation_version,
            materialized_ts
        )
        VALUES (
            %s, %s, %s,
            %s::timestamptz, %s::timestamptz, %s, %s,
            %s, %s::jsonb,
            %s::jsonb, %s::jsonb,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s::jsonb, %s,
            now()
        )
        ON CONFLICT (conversation_id) DO UPDATE SET
            display_label = EXCLUDED.display_label,
            display_label_source = EXCLUDED.display_label_source,
            first_ts = EXCLUDED.first_ts,
            latest_ts = EXCLUDED.latest_ts,
            turns_count = EXCLUDED.turns_count,
            last_turn_id = EXCLUDED.last_turn_id,
            last_classification = EXCLUDED.last_classification,
            classification_counts_json = EXCLUDED.classification_counts_json,
            persistence_counts_json = EXCLUDED.persistence_counts_json,
            modules_involved_json = EXCLUDED.modules_involved_json,
            memory_used_turns = EXCLUDED.memory_used_turns,
            web_requested_turns = EXCLUDED.web_requested_turns,
            web_success_turns = EXCLUDED.web_success_turns,
            web_injected_turns = EXCLUDED.web_injected_turns,
            error_count = EXCLUDED.error_count,
            fallback_count = EXCLUDED.fallback_count,
            last_problem_reason_code = EXCLUDED.last_problem_reason_code,
            source_json = EXCLUDED.source_json,
            calculation_version = EXCLUDED.calculation_version,
            materialized_ts = now()
        ''',
        (
            summary.get('conversation_id'),
            summary.get('display_label'),
            summary.get('display_label_source'),
            summary.get('first_ts'),
            summary.get('latest_ts'),
            _to_int(summary.get('turns_count')),
            summary.get('last_turn_id'),
            summary.get('last_classification'),
            _json(summary.get('classification_counts') or {}),
            _json(summary.get('persistence_counts') or {}),
            _json(summary.get('modules_involved') or {}),
            _to_int(summary.get('memory_used_turns')),
            _to_int(summary.get('web_requested_turns')),
            _to_int(summary.get('web_success_turns')),
            _to_int(summary.get('web_injected_turns')),
            _to_int(summary.get('error_count')),
            _to_int(summary.get('fallback_count')),
            summary.get('last_problem_reason_code'),
            _json(summary.get('source') or {}),
            summary.get('calculation_version') or CALCULATION_VERSION,
        ),
    )


def _insert_metric_bucket(cur: Any, bucket: Mapping[str, Any]) -> None:
    cur.execute(
        '''
        INSERT INTO observability.dashboard_metric_buckets (
            granularity, bucket_start, bucket_end, module_key,
            turn_count, event_count, metrics_json,
            calculation_version, materialized_ts
        )
        VALUES (%s, %s::timestamptz, %s::timestamptz, %s, %s, %s, %s::jsonb, %s, now())
        ON CONFLICT (granularity, bucket_start, module_key) DO UPDATE SET
            bucket_end = EXCLUDED.bucket_end,
            turn_count = EXCLUDED.turn_count,
            event_count = EXCLUDED.event_count,
            metrics_json = EXCLUDED.metrics_json,
            calculation_version = EXCLUDED.calculation_version,
            materialized_ts = now()
        ''',
        (
            bucket.get('granularity'),
            bucket.get('bucket_start'),
            bucket.get('bucket_end'),
            bucket.get('module_key'),
            _to_int(bucket.get('turn_count')),
            _to_int(bucket.get('event_count')),
            _json(bucket.get('metrics') or {}),
            bucket.get('calculation_version') or CALCULATION_VERSION,
        ),
    )


def _replace_conversation_summaries_from_persisted_facts(
    cur: Any,
    conversation_ids: Sequence[str],
) -> list[dict[str, Any]]:
    ids = [str(value or '').strip() for value in conversation_ids if str(value or '').strip()]
    if not ids:
        return []
    cur.execute(
        '''
        DELETE FROM observability.dashboard_conversation_summaries
        WHERE conversation_id = ANY(%s)
        ''',
        (ids,),
    )
    facts = _read_persisted_facts_for_conversations(cur, ids)
    summaries = build_dashboard_conversation_summaries(facts)
    for summary in summaries:
        _insert_conversation_summary(cur, summary)
    return summaries


def _replace_metric_buckets_from_persisted_facts(
    cur: Any,
    *,
    window_start: Any,
    window_end: Any,
    now: datetime,
    recent_granularity_days: int,
    extra_latest_times: Sequence[Any] = (),
) -> list[dict[str, Any]]:
    rebuilt: list[dict[str, Any]] = []
    for granularity, bucket_start, bucket_end in _affected_bucket_specs(
        window_start=window_start,
        window_end=window_end,
        now=now,
        recent_granularity_days=recent_granularity_days,
        extra_latest_times=extra_latest_times,
    ):
        cur.execute(
            '''
            DELETE FROM observability.dashboard_metric_buckets
            WHERE granularity = %s
              AND bucket_start = %s::timestamptz
            ''',
            (granularity, _iso(bucket_start)),
        )
        facts = _read_persisted_facts_for_bucket(
            cur,
            bucket_start=bucket_start,
            bucket_end=bucket_end,
        )
        buckets = build_dashboard_metric_buckets(
            facts,
            now=now,
            recent_granularity_days=recent_granularity_days,
        )
        for bucket in buckets:
            if (
                bucket.get('granularity') == granularity
                and bucket.get('bucket_start') == _iso(bucket_start)
                and bucket.get('module_key') in _MODULE_KEYS
            ):
                _insert_metric_bucket(cur, bucket)
                rebuilt.append(bucket)
    return rebuilt


def execute_dashboard_analytics_schema(cur: Any) -> None:
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_turn_facts (
            conversation_id             TEXT        NOT NULL,
            turn_id                     TEXT        NOT NULL,
            first_ts                    TIMESTAMPTZ NOT NULL,
            latest_ts                   TIMESTAMPTZ NOT NULL,
            classification              TEXT        NOT NULL,
            score                       INTEGER,
            source_event_ids            JSONB       NOT NULL DEFAULT '[]'::jsonb,
            source_event_count          INTEGER     NOT NULL DEFAULT 0,
            source_first_event_id       TEXT,
            source_latest_event_id      TEXT,
            persistence_json            JSONB       NOT NULL DEFAULT '{}'::jsonb,
            providers_json              JSONB       NOT NULL DEFAULT '{}'::jsonb,
            rag_json                    JSONB       NOT NULL DEFAULT '{}'::jsonb,
            identity_json               JSONB       NOT NULL DEFAULT '{}'::jsonb,
            hermeneutic_json            JSONB       NOT NULL DEFAULT '{}'::jsonb,
            web_json                    JSONB       NOT NULL DEFAULT '{}'::jsonb,
            node_state_json             JSONB       NOT NULL DEFAULT '{}'::jsonb,
            latencies_json              JSONB       NOT NULL DEFAULT '{}'::jsonb,
            errors_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            stage_counts_json           JSONB       NOT NULL DEFAULT '{}'::jsonb,
            flags_json                  JSONB       NOT NULL DEFAULT '{}'::jsonb,
            content_availability_json   JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_event_payloads_included BOOLEAN     NOT NULL DEFAULT false,
            PRIMARY KEY (conversation_id, turn_id),
            CHECK (raw_event_payloads_included = false)
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_turn_facts_latest_ts_idx
        ON observability.dashboard_turn_facts (latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_turn_facts_conversation_latest_ts_idx
        ON observability.dashboard_turn_facts (conversation_id, latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_conversation_summaries (
            conversation_id             TEXT        PRIMARY KEY,
            display_label               TEXT        NOT NULL,
            display_label_source        TEXT        NOT NULL,
            first_ts                    TIMESTAMPTZ,
            latest_ts                   TIMESTAMPTZ,
            turns_count                 INTEGER     NOT NULL DEFAULT 0,
            last_turn_id                TEXT,
            last_classification         TEXT,
            classification_counts_json  JSONB       NOT NULL DEFAULT '{}'::jsonb,
            persistence_counts_json     JSONB       NOT NULL DEFAULT '{}'::jsonb,
            modules_involved_json       JSONB       NOT NULL DEFAULT '{}'::jsonb,
            memory_used_turns           INTEGER     NOT NULL DEFAULT 0,
            web_requested_turns         INTEGER     NOT NULL DEFAULT 0,
            web_success_turns           INTEGER     NOT NULL DEFAULT 0,
            web_injected_turns          INTEGER     NOT NULL DEFAULT 0,
            error_count                 INTEGER     NOT NULL DEFAULT 0,
            fallback_count              INTEGER     NOT NULL DEFAULT 0,
            last_problem_reason_code    TEXT,
            source_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_conversation_summaries_latest_ts_idx
        ON observability.dashboard_conversation_summaries (latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_metric_buckets (
            granularity                 TEXT        NOT NULL,
            bucket_start                TIMESTAMPTZ NOT NULL,
            bucket_end                  TIMESTAMPTZ NOT NULL,
            module_key                  TEXT        NOT NULL,
            turn_count                  INTEGER     NOT NULL DEFAULT 0,
            event_count                 INTEGER     NOT NULL DEFAULT 0,
            metrics_json                JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (granularity, bucket_start, module_key),
            CHECK (granularity IN ('hour', 'day'))
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_metric_buckets_module_window_idx
        ON observability.dashboard_metric_buckets (module_key, granularity, bucket_start DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_materialization_status (
            materializer_key            TEXT        PRIMARY KEY,
            calculation_version         TEXT        NOT NULL,
            status                      TEXT        NOT NULL,
            window_start                TIMESTAMPTZ,
            window_end                  TIMESTAMPTZ,
            retention_days              INTEGER     NOT NULL,
            recent_granularity_days     INTEGER     NOT NULL,
            old_granularity             TEXT        NOT NULL,
            source_events_count         BIGINT      NOT NULL DEFAULT 0,
            source_events_truncated     BOOLEAN     NOT NULL DEFAULT false,
            event_limit_dependency      BOOLEAN     NOT NULL DEFAULT false,
            last_event_id               TEXT,
            last_event_ts               TIMESTAMPTZ,
            lag_seconds                 BIGINT,
            turns_materialized_count    INTEGER     NOT NULL DEFAULT 0,
            conversations_materialized_count INTEGER NOT NULL DEFAULT 0,
            buckets_materialized_count  INTEGER     NOT NULL DEFAULT 0,
            error_count                 INTEGER     NOT NULL DEFAULT 0,
            last_error_code             TEXT,
            last_error_chars            INTEGER     NOT NULL DEFAULT 0,
            last_error_sha256_12        TEXT,
            backfill_status             TEXT        NOT NULL,
            status_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            updated_ts                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CHECK (source_events_truncated = false),
            CHECK (event_limit_dependency = false)
        );
        '''
    )


def init_dashboard_analytics_storage(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> None:
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE SCHEMA IF NOT EXISTS observability;')
                execute_dashboard_analytics_schema(cur)
            conn.commit()
        logger_instance.info('dashboard_analytics_storage_init ok')
    except Exception as exc:
        logger_instance.error('dashboard_analytics_storage_init_failed err=%s', exc)


def persist_dashboard_analytics(
    analytics: Mapping[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> dict[str, Any]:
    turn_facts = list(_sequence(analytics.get('turn_facts')))
    status = _mapping(analytics.get('materialization_status'))
    window = _mapping(analytics.get('window'))
    window_start = window.get('start')
    window_end = window.get('end')
    incoming_conversation_ids = sorted(
        {
            str(fact.get('conversation_id') or '').strip()
            for fact in turn_facts
            if str(fact.get('conversation_id') or '').strip()
        }
    )
    now_dt = _parse_ts(status.get('updated_ts')) or datetime.now(timezone.utc)
    rebuilt_conversation_summaries: list[dict[str, Any]] = []
    rebuilt_metric_buckets: list[dict[str, Any]] = []

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                affected_conversation_ids = set(incoming_conversation_ids)
                if window_start and window_end:
                    affected_conversation_ids.update(
                        _read_conversation_ids_for_window(cur, window_start, window_end)
                    )
                    cur.execute(
                        '''
                        DELETE FROM observability.dashboard_turn_facts
                        WHERE latest_ts >= %s::timestamptz
                          AND latest_ts < %s::timestamptz
                        ''',
                        (window_start, window_end),
                    )

                for fact in turn_facts:
                    cur.execute(
                        '''
                        INSERT INTO observability.dashboard_turn_facts (
                            conversation_id, turn_id, first_ts, latest_ts,
                            classification, score, source_event_ids, source_event_count,
                            source_first_event_id, source_latest_event_id,
                            persistence_json, providers_json, rag_json, identity_json,
                            hermeneutic_json, web_json, node_state_json, latencies_json,
                            errors_json, stage_counts_json, flags_json,
                            content_availability_json, calculation_version,
                            raw_event_payloads_included, materialized_ts
                        )
                        VALUES (
                            %s, %s, %s::timestamptz, %s::timestamptz,
                            %s, %s, %s::jsonb, %s,
                            %s, %s,
                            %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s,
                            false, now()
                        )
                        ON CONFLICT (conversation_id, turn_id) DO UPDATE SET
                            first_ts = EXCLUDED.first_ts,
                            latest_ts = EXCLUDED.latest_ts,
                            classification = EXCLUDED.classification,
                            score = EXCLUDED.score,
                            source_event_ids = EXCLUDED.source_event_ids,
                            source_event_count = EXCLUDED.source_event_count,
                            source_first_event_id = EXCLUDED.source_first_event_id,
                            source_latest_event_id = EXCLUDED.source_latest_event_id,
                            persistence_json = EXCLUDED.persistence_json,
                            providers_json = EXCLUDED.providers_json,
                            rag_json = EXCLUDED.rag_json,
                            identity_json = EXCLUDED.identity_json,
                            hermeneutic_json = EXCLUDED.hermeneutic_json,
                            web_json = EXCLUDED.web_json,
                            node_state_json = EXCLUDED.node_state_json,
                            latencies_json = EXCLUDED.latencies_json,
                            errors_json = EXCLUDED.errors_json,
                            stage_counts_json = EXCLUDED.stage_counts_json,
                            flags_json = EXCLUDED.flags_json,
                            content_availability_json = EXCLUDED.content_availability_json,
                            calculation_version = EXCLUDED.calculation_version,
                            raw_event_payloads_included = false,
                            materialized_ts = now()
                        ''',
                        (
                            fact.get('conversation_id'),
                            fact.get('turn_id'),
                            fact.get('first_ts'),
                            fact.get('latest_ts'),
                            fact.get('classification'),
                            fact.get('score'),
                            _json(fact.get('source_event_ids') or []),
                            _to_int(fact.get('source_event_count')),
                            fact.get('source_first_event_id'),
                            fact.get('source_latest_event_id'),
                            _json(fact.get('persistence') or {}),
                            _json(fact.get('providers') or {}),
                            _json(fact.get('rag') or {}),
                            _json(fact.get('identity') or {}),
                            _json(fact.get('hermeneutic') or {}),
                            _json(fact.get('web') or {}),
                            _json(fact.get('node_state') or {}),
                            _json(fact.get('latencies') or {}),
                            _json(fact.get('errors') or {}),
                            _json(fact.get('stage_counts') or {}),
                            _json(fact.get('flags') or {}),
                            _json(fact.get('content_availability') or {}),
                            fact.get('calculation_version') or CALCULATION_VERSION,
                        ),
                    )

                rebuilt_conversation_summaries = _replace_conversation_summaries_from_persisted_facts(
                    cur,
                    sorted(affected_conversation_ids),
                )

                if window_start and window_end:
                    rebuilt_metric_buckets = _replace_metric_buckets_from_persisted_facts(
                        cur,
                        window_start=window_start,
                        window_end=window_end,
                        now=now_dt,
                        recent_granularity_days=(
                            _to_int(status.get('recent_granularity_days'))
                            or RECENT_GRANULARITY_DAYS
                        ),
                        extra_latest_times=[
                            fact.get('latest_ts')
                            for fact in turn_facts
                        ],
                    )

                status_for_persist = dict(status)
                status_for_persist['conversations_materialized_count'] = len(rebuilt_conversation_summaries)
                status_for_persist['buckets_materialized_count'] = len(rebuilt_metric_buckets)

                cur.execute(
                    '''
                    INSERT INTO observability.dashboard_materialization_status (
                        materializer_key, calculation_version, status,
                        window_start, window_end, retention_days, recent_granularity_days,
                        old_granularity, source_events_count, source_events_truncated,
                        event_limit_dependency, last_event_id, last_event_ts, lag_seconds,
                        turns_materialized_count, conversations_materialized_count,
                        buckets_materialized_count, error_count, last_error_code,
                        last_error_chars, last_error_sha256_12, backfill_status,
                        status_json, updated_ts
                    )
                    VALUES (
                        %s, %s, %s,
                        %s::timestamptz, %s::timestamptz, %s, %s,
                        %s, %s, false,
                        false, %s, %s::timestamptz, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s::jsonb, %s::timestamptz
                    )
                    ON CONFLICT (materializer_key) DO UPDATE SET
                        calculation_version = EXCLUDED.calculation_version,
                        status = EXCLUDED.status,
                        window_start = EXCLUDED.window_start,
                        window_end = EXCLUDED.window_end,
                        retention_days = EXCLUDED.retention_days,
                        recent_granularity_days = EXCLUDED.recent_granularity_days,
                        old_granularity = EXCLUDED.old_granularity,
                        source_events_count = EXCLUDED.source_events_count,
                        source_events_truncated = false,
                        event_limit_dependency = false,
                        last_event_id = EXCLUDED.last_event_id,
                        last_event_ts = EXCLUDED.last_event_ts,
                        lag_seconds = EXCLUDED.lag_seconds,
                        turns_materialized_count = EXCLUDED.turns_materialized_count,
                        conversations_materialized_count = EXCLUDED.conversations_materialized_count,
                        buckets_materialized_count = EXCLUDED.buckets_materialized_count,
                        error_count = EXCLUDED.error_count,
                        last_error_code = EXCLUDED.last_error_code,
                        last_error_chars = EXCLUDED.last_error_chars,
                        last_error_sha256_12 = EXCLUDED.last_error_sha256_12,
                        backfill_status = EXCLUDED.backfill_status,
                        status_json = EXCLUDED.status_json,
                        updated_ts = EXCLUDED.updated_ts
                    ''',
                    (
                        status_for_persist.get('materializer_key') or 'dashboard_long_term_observability',
                        status_for_persist.get('calculation_version') or CALCULATION_VERSION,
                        status_for_persist.get('status') or 'unknown',
                        status_for_persist.get('window_start'),
                        status_for_persist.get('window_end'),
                        _to_int(status_for_persist.get('retention_days')) or RETENTION_DAYS,
                        _to_int(status_for_persist.get('recent_granularity_days')) or RECENT_GRANULARITY_DAYS,
                        status_for_persist.get('old_granularity') or 'day',
                        _to_int(status_for_persist.get('source_events_count')),
                        status_for_persist.get('last_event_id'),
                        status_for_persist.get('last_event_ts'),
                        status_for_persist.get('lag_seconds'),
                        _to_int(status_for_persist.get('turns_materialized_count')),
                        _to_int(status_for_persist.get('conversations_materialized_count')),
                        _to_int(status_for_persist.get('buckets_materialized_count')),
                        _to_int(status_for_persist.get('error_count')),
                        status_for_persist.get('last_error_code'),
                        _to_int(status_for_persist.get('last_error_chars')),
                        status_for_persist.get('last_error_sha256_12'),
                        status_for_persist.get('backfill_status') or 'unknown',
                        _json(status_for_persist),
                        status_for_persist.get('updated_ts'),
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger_instance.error('dashboard_analytics_persist_failed err=%s', exc)
        raise

    return {
        'ok': True,
        'turn_facts_written': len(turn_facts),
        'conversation_summaries_written': len(rebuilt_conversation_summaries),
        'metric_buckets_written': len(rebuilt_metric_buckets),
        'materialization_status_written': bool(status),
    }


def _row_to_event(row: Sequence[Any]) -> dict[str, Any]:
    payload_json = row[7]
    if not isinstance(payload_json, dict):
        payload_json = {}
    return {
        'event_id': str(row[0] or ''),
        'conversation_id': str(row[1] or ''),
        'turn_id': str(row[2] or ''),
        'ts': _iso(_parse_ts(row[3])) if row[3] is not None else '',
        'stage': str(row[4] or ''),
        'status': str(row[5] or ''),
        'duration_ms': int(row[6]) if row[6] is not None else None,
        'payload_json': payload_json,
    }


def materialize_dashboard_analytics_window(
    *,
    ts_from: str | None = None,
    ts_to: str | None = None,
    now: datetime | None = None,
    retention_days: int = RETENTION_DAYS,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> dict[str, Any]:
    """Read compact events for the chosen window, build and persist analytics.

    This intentionally has no event_limit parameter. Historical backfill remains
    an explicit caller decision; the default window is the current retention
    horizon.
    """
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = _parse_ts(ts_from) if ts_from else _retention_start(now_dt, retention_days)
    end = _parse_ts(ts_to) if ts_to else now_dt
    if start is None:
        raise ValueError(f'invalid ts_from timestamp: {ts_from}')
    if end is None:
        raise ValueError(f'invalid ts_to timestamp: {ts_to}')
    if start >= end:
        raise ValueError('ts_from must be before ts_to')

    rows: list[Sequence[Any]] = []
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    WITH touched_turns AS (
                        SELECT DISTINCT conversation_id, turn_id
                        FROM observability.chat_log_events
                        WHERE ts >= %s::timestamptz
                          AND ts < %s::timestamptz
                    )
                    SELECT
                        events.event_id,
                        events.conversation_id,
                        events.turn_id,
                        events.ts,
                        events.stage,
                        events.status,
                        events.duration_ms,
                        events.payload_json
                    FROM observability.chat_log_events AS events
                    JOIN touched_turns
                      ON touched_turns.conversation_id = events.conversation_id
                     AND touched_turns.turn_id = events.turn_id
                    ORDER BY events.ts ASC, events.event_id ASC
                    ''',
                    (_iso(start), _iso(end)),
                )
                rows = cur.fetchall()
    except Exception as exc:
        status = build_dashboard_materialization_status(
            events=[],
            turn_facts=[],
            conversation_summaries=[],
            metric_buckets=[],
            now=now_dt,
            window_start=start,
            window_end=end,
            retention_days=retention_days,
            recent_granularity_days=recent_granularity_days,
            error=exc,
        )
        analytics = {
            'kind': 'dashboard_analytics_materialization',
            'schema_version': SCHEMA_VERSION,
            'calculation_version': CALCULATION_VERSION,
            'window': {
                'start': _iso(start),
                'end': _iso(end),
                'retention_days': int(retention_days),
                'recent_granularity_days': int(recent_granularity_days),
                'old_granularity': 'day',
            },
            'turn_facts': [],
            'conversation_summaries': [],
            'metric_buckets': [],
            'materialization_status': status,
            'redaction': {
                'raw_content_stored': False,
                'raw_event_payloads_included': False,
            },
        }
        try:
            persist_dashboard_analytics(
                analytics,
                conn_factory=conn_factory,
                logger_instance=logger_instance,
            )
        except Exception:
            pass
        logger_instance.error('dashboard_analytics_materialize_read_failed err=%s', exc)
        return analytics

    analytics = build_dashboard_analytics(
        [_row_to_event(row) for row in rows],
        now=now_dt,
        window_start=start,
        window_end=end,
        retention_days=retention_days,
        recent_granularity_days=recent_granularity_days,
        filter_events_to_window=False,
    )
    persist_result = persist_dashboard_analytics(
        analytics,
        conn_factory=conn_factory,
        logger_instance=logger_instance,
    )
    analytics['persist'] = persist_result
    return analytics
