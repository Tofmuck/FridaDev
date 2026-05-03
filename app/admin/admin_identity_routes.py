from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from admin import (
    admin_identity_governance_service,
    admin_identity_mutable_edit_service,
    admin_identity_read_model_service,
    admin_identity_runtime_representations_service,
    admin_identity_static_edit_service,
)


def register_admin_identity_routes(
    app: Flask,
    *,
    memory_store_module: Any,
    identity_module: Any,
    static_identity_content_module: Any,
    log_store_module: Any,
    admin_logs_module: Any,
    runtime_settings_module: Any,
) -> None:
    def api_admin_identity_read_model():
        payload, status = admin_identity_read_model_service.identity_read_model_response(
            request.args,
            memory_store_module=memory_store_module,
            identity_module=identity_module,
            static_identity_content_module=static_identity_content_module,
            log_store_module=log_store_module,
        )
        return jsonify(payload), status

    def api_admin_identity_runtime_representations():
        payload, status = admin_identity_runtime_representations_service.identity_runtime_representations_response(
            identity_module=identity_module,
            memory_store_module=memory_store_module,
            log_store_module=log_store_module,
        )
        return jsonify(payload), status

    def api_admin_identity_mutable_edit():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            data,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    def api_admin_identity_static_edit():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_identity_static_edit_service.identity_static_edit_response(
            data,
            static_identity_content_module=static_identity_content_module,
            admin_logs_module=admin_logs_module,
        )
        return jsonify(payload), status

    def api_admin_identity_governance():
        payload, status = admin_identity_governance_service.identity_governance_response(
            request.args,
            runtime_settings_module=runtime_settings_module,
            identity_module=identity_module,
        )
        return jsonify(payload), status

    def api_admin_identity_governance_update():
        data = request.get_json(force=True, silent=True) or {}
        payload, status = admin_identity_governance_service.identity_governance_update_response(
            data,
            runtime_settings_module=runtime_settings_module,
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/admin/identity/read-model',
        endpoint='api_admin_identity_read_model',
        view_func=api_admin_identity_read_model,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/identity/runtime-representations',
        endpoint='api_admin_identity_runtime_representations',
        view_func=api_admin_identity_runtime_representations,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/identity/mutable',
        endpoint='api_admin_identity_mutable_edit',
        view_func=api_admin_identity_mutable_edit,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/admin/identity/static',
        endpoint='api_admin_identity_static_edit',
        view_func=api_admin_identity_static_edit,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/admin/identity/governance',
        endpoint='api_admin_identity_governance',
        view_func=api_admin_identity_governance,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/admin/identity/governance',
        endpoint='api_admin_identity_governance_update',
        view_func=api_admin_identity_governance_update,
        methods=['POST'],
    )
