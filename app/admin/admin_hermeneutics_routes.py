from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from admin import admin_hermeneutics_service


def register_admin_hermeneutics_routes(
    app: Flask,
    *,
    memory_store_module: Any,
    arbiter_module: Any,
    admin_logs_module: Any,
    config_module: Any,
) -> None:
    def api_admin_hermeneutics_identity_candidates():
        payload, status = admin_hermeneutics_service.identity_candidates_response(
            request.args,
            memory_store_module=memory_store_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_arbiter_decisions():
        payload, status = admin_hermeneutics_service.arbiter_decisions_response(
            request.args,
            memory_store_module=memory_store_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_identity_force_accept():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_hermeneutics_service.identity_force_accept_response(
            data,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_identity_force_reject():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_hermeneutics_service.identity_force_reject_response(
            data,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_identity_relabel():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_hermeneutics_service.identity_relabel_response(
            data,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_dashboard():
        payload, status = admin_hermeneutics_service.dashboard_response(
            request.args,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
            config_module=config_module,
        )
        return jsonify(payload), status

    def api_admin_hermeneutics_corrections_export():
        payload, status = admin_hermeneutics_service.corrections_export_response(
            request.args,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/admin/hermeneutics/identity-candidates',
        endpoint='api_admin_hermeneutics_identity_candidates',
        view_func=api_admin_hermeneutics_identity_candidates,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/arbiter-decisions',
        endpoint='api_admin_hermeneutics_arbiter_decisions',
        view_func=api_admin_hermeneutics_arbiter_decisions,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/identity/force-accept',
        endpoint='api_admin_hermeneutics_identity_force_accept',
        view_func=api_admin_hermeneutics_identity_force_accept,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/identity/force-reject',
        endpoint='api_admin_hermeneutics_identity_force_reject',
        view_func=api_admin_hermeneutics_identity_force_reject,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/identity/relabel',
        endpoint='api_admin_hermeneutics_identity_relabel',
        view_func=api_admin_hermeneutics_identity_relabel,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/dashboard',
        endpoint='api_admin_hermeneutics_dashboard',
        view_func=api_admin_hermeneutics_dashboard,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/hermeneutics/corrections-export',
        endpoint='api_admin_hermeneutics_corrections_export',
        view_func=api_admin_hermeneutics_corrections_export,
        methods=['GET'],
    )
