from __future__ import annotations

from typing import Any, Callable

from flask import Flask, jsonify, request


def register_workspace_folder_note_routes(
    app: Flask,
    *,
    workspace_folder_notes_service_module: Any,
    get_workspace_folders_module: Callable[[], Any],
    get_workspace_folder_notes_module: Callable[[], Any],
    get_workspace_folder_notes_append_module: Callable[[], Any],
    get_workspace_folder_notes_read_module: Callable[[], Any],
    get_workspace_folder_note_nextcloud_runtime_module: Callable[[], Any],
) -> None:
    def api_list_workspace_folder_notes(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        payload, status = (
            workspace_folder_notes_service_module
            .list_workspace_folder_notes_response(
                folder_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
            )
        )
        return jsonify(payload), status

    def api_lookup_workspace_folder_note(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        payload, status = (
            workspace_folder_notes_service_module
            .lookup_workspace_folder_note_response(
                folder_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                title=request.args.get("title", ""),
                note_id=request.args.get("note_id", ""),
            )
        )
        return jsonify(payload), status

    def api_get_workspace_folder_note(folder_id: str, note_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        payload, status = (
            workspace_folder_notes_service_module
            .lookup_workspace_folder_note_response(
                folder_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                note_id=note_id,
            )
        )
        return jsonify(payload), status

    def api_append_workspace_folder_note(folder_id: str, note_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        notes_append_module = get_workspace_folder_notes_append_module()
        payload, status = (
            workspace_folder_notes_service_module
            .append_workspace_folder_note_response(
                folder_id,
                note_id,
                data,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                notes_append_module=notes_append_module,
            )
        )
        return jsonify(payload), status

    def api_prepare_workspace_folder_note(folder_id: str, note_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        notes_read_module = get_workspace_folder_notes_read_module()
        payload, status = (
            workspace_folder_notes_service_module
            .prepare_workspace_folder_note_response(
                folder_id,
                note_id,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                notes_read_module=notes_read_module,
            )
        )
        return jsonify(payload), status

    def api_create_workspace_folder_note(folder_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        workspace_folder_notes_module = get_workspace_folder_notes_module()
        notes_nextcloud_runtime_module = (
            get_workspace_folder_note_nextcloud_runtime_module()
        )
        payload, status = (
            workspace_folder_notes_service_module
            .create_workspace_folder_note_response(
                folder_id,
                data,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                notes_nextcloud_runtime_module=notes_nextcloud_runtime_module,
            )
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes',
        endpoint='api_list_workspace_folder_notes',
        view_func=api_list_workspace_folder_notes,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes/lookup',
        endpoint='api_lookup_workspace_folder_note',
        view_func=api_lookup_workspace_folder_note,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes/<note_id>',
        endpoint='api_get_workspace_folder_note',
        view_func=api_get_workspace_folder_note,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes/<note_id>/append',
        endpoint='api_append_workspace_folder_note',
        view_func=api_append_workspace_folder_note,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes/<note_id>/prepare',
        endpoint='api_prepare_workspace_folder_note',
        view_func=api_prepare_workspace_folder_note,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/notes',
        endpoint='api_create_workspace_folder_note',
        view_func=api_create_workspace_folder_note,
        methods=['POST'],
    )
