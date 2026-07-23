from __future__ import annotations

from typing import Any, Callable

from flask import Flask, Response, jsonify, request


def register_workspace_folder_export_routes(
    app: Flask,
    *,
    workspace_folder_exports_service_module: Any,
    workspace_folder_export_content_service_module: Any,
    get_workspace_folders_module: Callable[[], Any],
    get_workspace_folder_exports_module: Callable[[], Any],
    get_workspace_folder_export_nextcloud_runtime_module: Callable[[], Any],
    get_conversation_store_module: Callable[[], Any],
) -> None:
    def api_list_workspace_folder_exports(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_exports_module = get_workspace_folder_exports_module()
        payload, status = (
            workspace_folder_exports_service_module
            .list_workspace_folder_exports_response(
                folder_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_exports_module=workspace_folder_exports_module,
            )
        )
        return jsonify(payload), status

    def api_get_workspace_folder_export(folder_id: str, export_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_exports_module = get_workspace_folder_exports_module()
        payload, status = (
            workspace_folder_exports_service_module
            .get_workspace_folder_export_response(
                folder_id,
                export_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_exports_module=workspace_folder_exports_module,
            )
        )
        return jsonify(payload), status

    def api_download_workspace_folder_export(folder_id: str, export_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_exports_module = get_workspace_folder_exports_module()
        result = (
            workspace_folder_export_content_service_module
            .download_workspace_folder_export_response(
                folder_id,
                export_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_exports_module=workspace_folder_exports_module,
                disposition="attachment",
            )
        )
        if result.ok:
            return Response(result.content, status=result.status, headers=dict(result.headers or {}))
        return jsonify(dict(result.payload or {})), result.status

    def api_open_workspace_folder_export(folder_id: str, export_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_exports_module = get_workspace_folder_exports_module()
        result = (
            workspace_folder_export_content_service_module
            .download_workspace_folder_export_response(
                folder_id,
                export_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_exports_module=workspace_folder_exports_module,
                disposition="inline",
            )
        )
        if result.ok:
            return Response(result.content, status=result.status, headers=dict(result.headers or {}))
        return jsonify(dict(result.payload or {})), result.status

    def api_create_workspace_folder_export(folder_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_exports_module = get_workspace_folder_exports_module()
        exports_nextcloud_runtime_module = (
            get_workspace_folder_export_nextcloud_runtime_module()
        )
        conversation_store_module = get_conversation_store_module()
        payload, status = (
            workspace_folder_exports_service_module
            .create_workspace_folder_export_response(
                folder_id,
                data,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_exports_module=workspace_folder_exports_module,
                exports_nextcloud_runtime_module=exports_nextcloud_runtime_module,
                conversation_store_module=conversation_store_module,
            )
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/exports',
        endpoint='api_list_workspace_folder_exports',
        view_func=api_list_workspace_folder_exports,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/exports/<export_id>',
        endpoint='api_get_workspace_folder_export',
        view_func=api_get_workspace_folder_export,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/exports/<export_id>/download',
        endpoint='api_download_workspace_folder_export',
        view_func=api_download_workspace_folder_export,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/exports/<export_id>/open',
        endpoint='api_open_workspace_folder_export',
        view_func=api_open_workspace_folder_export,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/exports',
        endpoint='api_create_workspace_folder_export',
        view_func=api_create_workspace_folder_export,
        methods=['POST'],
    )
