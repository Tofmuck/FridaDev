from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from flask import Flask, Response, jsonify, request


def register_admin_logs_dashboard_routes(
    app: Flask,
    *,
    admin_logs_module: Any,
    admin_log_projection_module: Any,
    log_store_module: Any,
    log_markdown_export_module: Any,
    dashboard_read_model_module: Any,
    dashboard_materialization_runtime_module: Any,
) -> None:
    def _ensure_dashboard_recent_for_admin_read(reason: str) -> datetime | None:
        freshness = (
            dashboard_materialization_runtime_module
            .ensure_recent_dashboard_analytics_fresh(
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                reason=reason,
            )
        )
        read_now = freshness.get('read_now') if isinstance(freshness, dict) else None
        return read_now if isinstance(read_now, datetime) else None

    def _admin_error_response(
        *,
        status_code: int,
        error: str,
        error_code: str,
        reason_code: str,
    ) -> tuple[Response, int]:
        return jsonify({
            'ok': False,
            'error': error,
            'error_code': error_code,
            'reason_code': reason_code,
        }), status_code

    def _admin_bad_request_response(reason_code: str) -> tuple[Response, int]:
        return _admin_error_response(
            status_code=400,
            error='requete admin invalide',
            error_code='admin_bad_request',
            reason_code=reason_code,
        )

    def _admin_not_found_response(reason_code: str) -> tuple[Response, int]:
        return _admin_error_response(
            status_code=404,
            error='ressource admin introuvable',
            error_code='admin_not_found',
            reason_code=reason_code,
        )

    def _safe_export_filename_token(value: str | None, fallback: str) -> str:
        token = str(value or '').strip()
        if not token:
            return fallback
        normalized = re.sub(r'[^a-zA-Z0-9._-]+', '-', token).strip('-')
        return normalized or fallback

    def api_admin_logs():
        raw_limit = request.args.get("limit", "200")
        try:
            limit = max(1, min(int(raw_limit), 1000))
        except ValueError:
            limit = 200
        try:
            raw_logs = admin_logs_module.read_logs(limit=limit, fail_closed=True)
        except RuntimeError:
            return jsonify({'ok': False, 'error': 'admin_logs_read_failed', 'reason_code': 'admin_logs_read_failed'}), 500
        logs, redaction = admin_log_projection_module.project_legacy_admin_log_entries(raw_logs)
        return jsonify(
            {
                "ok": True,
                "logs": logs,
                "count": len(logs),
                "redaction": redaction,
                "payload_projection_schema": admin_log_projection_module.SCHEMA_VERSION,
            }
        )

    def api_admin_chat_logs():
        raw_limit = request.args.get('limit', '100')
        raw_offset = request.args.get('offset', '0')
        try:
            limit = int(raw_limit)
            offset = int(raw_offset)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

        if limit <= 0 or offset < 0:
            return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

        try:
            listing = log_store_module.read_chat_log_events(
                limit=limit,
                offset=offset,
                conversation_id=request.args.get('conversation_id'),
                turn_id=request.args.get('turn_id'),
                stage=request.args.get('stage'),
                status=request.args.get('status'),
                ts_from=request.args.get('ts_from'),
                ts_to=request.args.get('ts_to'),
                payload_projection='admin',
                fail_closed=True,
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_logs_bad_request')
        except RuntimeError:
            return jsonify({'ok': False, 'error': 'chat_log_events_read_failed', 'reason_code': 'chat_log_events_read_failed'}), 500
        listing = admin_log_projection_module.project_event_listing(listing)

        return jsonify(
            {
                'ok': True,
                'items': listing['items'],
                'count': listing['count'],
                'total': listing['total'],
                'limit': listing['limit'],
                'offset': listing['offset'],
                'next_offset': listing['next_offset'],
                'filters': listing['filters'],
                'redaction': listing['redaction'],
            }
        )

    def api_admin_chat_logs_metadata():
        try:
            metadata = log_store_module.read_chat_log_metadata(
                conversation_id=request.args.get('conversation_id'),
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_logs_metadata_bad_request')
        except RuntimeError:
            return (
                jsonify(
                    {
                        'ok': False,
                        'error': 'chat_log_metadata_read_failed',
                        'reason_code': 'chat_log_metadata_read_failed',
                    }
                ),
                500,
            )

        return jsonify(
            {
                'ok': True,
                'selected_conversation_id': metadata['selected_conversation_id'],
                'conversations': metadata['conversations'],
                'turns': metadata['turns'],
            }
        )

    def api_admin_chat_log_turns():
        raw_limit = request.args.get('limit', '50')
        raw_offset = request.args.get('offset', '0')
        try:
            limit = int(raw_limit)
            offset = int(raw_offset)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

        if limit <= 0 or offset < 0:
            return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

        try:
            turns = log_store_module.read_chat_turn_pipeline(
                limit=limit,
                offset=offset,
                conversation_id=request.args.get('conversation_id'),
                turn_id=request.args.get('turn_id'),
                ts_from=request.args.get('ts_from'),
                ts_to=request.args.get('ts_to'),
                fail_closed=True,
                conn_factory=log_store_module._conn,
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_log_turns_bad_request')
        except RuntimeError:
            return (
                jsonify(
                    {
                        'ok': False,
                        'error': 'chat_log_turns_read_failed',
                        'reason_code': 'chat_log_turns_read_failed',
                    }
                ),
                500,
            )

        return jsonify({'ok': True, **turns})

    def api_admin_chat_logs_metrics():
        raw_event_limit = request.args.get('event_limit', '2000')
        try:
            event_limit = int(raw_event_limit)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid event_limit parameter'}), 400
        if event_limit <= 0:
            return jsonify({'ok': False, 'error': 'invalid event_limit parameter'}), 400

        try:
            metrics = log_store_module.read_full_turn_metrics_snapshot(
                ts_from=request.args.get('ts_from'),
                ts_to=request.args.get('ts_to'),
                event_limit=event_limit,
                fail_closed=True,
                conn_factory=log_store_module._conn,
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_log_metrics_bad_request')
        except RuntimeError:
            return (
                jsonify(
                    {
                        'ok': False,
                        'error': 'chat_log_metrics_read_failed',
                        'reason_code': 'chat_log_metrics_read_failed',
                    }
                ),
                500,
            )

        return jsonify({'ok': True, **metrics})

    def api_admin_dashboard_overview():
        try:
            dashboard_now = _ensure_dashboard_recent_for_admin_read('dashboard_overview_read')
            payload = dashboard_read_model_module.read_dashboard_overview(
                request.args,
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                now=dashboard_now,
            )
        except ValueError:
            return _admin_bad_request_response('admin_dashboard_overview_bad_request')
        return jsonify({'ok': True, **payload})

    def api_admin_dashboard_conversations():
        try:
            dashboard_now = _ensure_dashboard_recent_for_admin_read('dashboard_conversations_read')
            payload = dashboard_read_model_module.read_dashboard_conversations(
                request.args,
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                now=dashboard_now,
            )
        except ValueError:
            return _admin_bad_request_response('admin_dashboard_conversations_bad_request')
        return jsonify({'ok': True, **payload})

    def api_admin_dashboard_conversation_turns(conversation_id: str):
        try:
            dashboard_now = _ensure_dashboard_recent_for_admin_read('dashboard_conversation_turns_read')
            payload = dashboard_read_model_module.read_dashboard_conversation_turns(
                conversation_id,
                request.args,
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                now=dashboard_now,
            )
        except ValueError:
            return _admin_bad_request_response('admin_dashboard_conversation_turns_bad_request')
        return jsonify({'ok': True, **payload})

    def api_admin_dashboard_turn_inspection(turn_id: str):
        try:
            dashboard_now = _ensure_dashboard_recent_for_admin_read('dashboard_turn_inspection_read')
            payload = dashboard_read_model_module.read_dashboard_turn_inspection(
                turn_id,
                request.args,
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                now=dashboard_now,
            )
        except ValueError:
            return _admin_bad_request_response('admin_dashboard_turn_inspection_bad_request')
        except LookupError:
            return _admin_not_found_response('admin_dashboard_turn_inspection_not_found')
        return jsonify({'ok': True, **payload})

    def api_admin_dashboard_turn_content(turn_id: str):
        def _audit_dashboard_content_gate(event: dict[str, Any]) -> bool:
            payload = event.get('payload_json') if isinstance(event.get('payload_json'), dict) else {}
            admin_logs_module.log_event(
                'dashboard_content_gate',
                conversation_id=event.get('conversation_id'),
                turn_id=event.get('turn_id'),
                audit_event_id=event.get('event_id'),
                **payload,
            )
            return True

        try:
            dashboard_now = _ensure_dashboard_recent_for_admin_read('dashboard_turn_content_read')
            payload = dashboard_read_model_module.read_dashboard_turn_content(
                turn_id,
                request.args,
                conn_factory=log_store_module._conn,
                logger_instance=log_store_module.logger,
                audit_fn=_audit_dashboard_content_gate,
                now=dashboard_now,
            )
        except ValueError:
            return _admin_bad_request_response('admin_dashboard_turn_content_bad_request')
        except LookupError:
            return _admin_not_found_response('admin_dashboard_turn_content_not_found')
        return jsonify({'ok': True, **payload})

    def api_admin_chat_logs_delete():
        try:
            deletion = log_store_module.delete_chat_log_events(
                conversation_id=request.args.get('conversation_id'),
                turn_id=request.args.get('turn_id'),
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_logs_delete_bad_request')
        except RuntimeError:
            return jsonify({'ok': False, 'error': 'chat_log_delete_failed', 'reason_code': 'chat_log_delete_failed'}), 500

        return jsonify(
            {
                'ok': True,
                'scope': deletion['scope'],
                'conversation_id': deletion['conversation_id'],
                'turn_id': deletion['turn_id'],
                'deleted_count': deletion['deleted_count'],
            }
        )

    def api_admin_chat_logs_export_markdown():
        conversation_id = request.args.get('conversation_id')
        turn_id = request.args.get('turn_id')
        try:
            exported = log_markdown_export_module.export_chat_logs_markdown(
                conversation_id=conversation_id,
                turn_id=turn_id,
            )
        except ValueError:
            return _admin_bad_request_response('admin_chat_logs_export_bad_request')
        except RuntimeError:
            return jsonify({'ok': False, 'error': 'chat_log_export_failed', 'reason_code': 'chat_log_export_failed'}), 500

        conversation_slug = _safe_export_filename_token(exported['conversation_id'], 'conversation')
        if exported['scope'] == 'turn':
            turn_slug = _safe_export_filename_token(exported['turn_id'], 'turn')
            filename = f'chat-logs-{conversation_slug}-{turn_slug}.md'
        else:
            filename = f'chat-logs-{conversation_slug}.md'

        response = Response(exported['markdown'], content_type='text/markdown; charset=utf-8')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    app.add_url_rule(
        '/api/admin/logs',
        endpoint='api_admin_logs',
        view_func=api_admin_logs,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat',
        endpoint='api_admin_chat_logs',
        view_func=api_admin_chat_logs,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat/metadata',
        endpoint='api_admin_chat_logs_metadata',
        view_func=api_admin_chat_logs_metadata,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat/turns',
        endpoint='api_admin_chat_log_turns',
        view_func=api_admin_chat_log_turns,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat/metrics',
        endpoint='api_admin_chat_logs_metrics',
        view_func=api_admin_chat_logs_metrics,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/dashboard/overview',
        endpoint='api_admin_dashboard_overview',
        view_func=api_admin_dashboard_overview,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/dashboard/conversations',
        endpoint='api_admin_dashboard_conversations',
        view_func=api_admin_dashboard_conversations,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/dashboard/conversations/<conversation_id>/turns',
        endpoint='api_admin_dashboard_conversation_turns',
        view_func=api_admin_dashboard_conversation_turns,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/dashboard/turns/<turn_id>/inspection',
        endpoint='api_admin_dashboard_turn_inspection',
        view_func=api_admin_dashboard_turn_inspection,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/dashboard/turns/<turn_id>/content',
        endpoint='api_admin_dashboard_turn_content',
        view_func=api_admin_dashboard_turn_content,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat',
        endpoint='api_admin_chat_logs_delete',
        view_func=api_admin_chat_logs_delete,
        methods=['DELETE'],
    )
    app.add_url_rule(
        '/api/admin/logs/chat/export.md',
        endpoint='api_admin_chat_logs_export_markdown',
        view_func=api_admin_chat_logs_export_markdown,
        methods=['GET'],
    )
