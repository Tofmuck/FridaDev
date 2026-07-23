from __future__ import annotations

from typing import Any, Callable

from flask import Flask, jsonify, request


def register_workspace_folder_file_routes(
    app: Flask,
    *,
    workspace_folders_service_module: Any,
    workspace_files_service_module: Any,
    workspace_file_ocr_service_module: Any,
    get_workspace_folders_module: Callable[[], Any],
    get_workspace_files_module: Callable[[], Any],
    get_workspace_document_nextcloud_runtime_module: Callable[[], Any],
) -> None:
    def api_list_workspace_folders():
        workspace_folders_module = get_workspace_folders_module()
        payload = workspace_folders_service_module.list_workspace_folders(
            request.args,
            workspace_folders_module=workspace_folders_module,
        )
        return jsonify(payload)

    def api_create_workspace_folder():
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        payload, status = workspace_folders_service_module.create_workspace_folder(
            data,
            workspace_folders_module=workspace_folders_module,
        )
        return jsonify(payload), status

    def api_patch_workspace_folder(folder_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        payload, status = workspace_folders_service_module.patch_workspace_folder(
            folder_id,
            data,
            workspace_folders_module=workspace_folders_module,
        )
        return jsonify(payload), status

    def api_delete_workspace_folder(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        payload, status = workspace_folders_service_module.delete_workspace_folder(
            folder_id,
            workspace_folders_module=workspace_folders_module,
        )
        return jsonify(payload), status

    def api_list_workspace_folder_files(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        payload, status = workspace_files_service_module.list_workspace_files_response(
            folder_id,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
        )
        return jsonify(payload), status

    def api_upload_workspace_folder_file(folder_id: str):
        body_guard = workspace_files_service_module.upload_body_size_guard_response(
            request.content_length
        )
        if body_guard:
            payload, status = body_guard
            return jsonify(payload), status

        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        documents_nextcloud_runtime_module = (
            get_workspace_document_nextcloud_runtime_module()
        )
        payload, status = workspace_files_service_module.upload_workspace_file_response(
            folder_id,
            request.files,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
            documents_nextcloud_runtime_module=documents_nextcloud_runtime_module,
        )
        return jsonify(payload), status

    def api_delete_workspace_folder_file(folder_id: str, file_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        documents_nextcloud_runtime_module = (
            get_workspace_document_nextcloud_runtime_module()
        )
        payload, status = workspace_files_service_module.delete_workspace_file_response(
            folder_id,
            file_id,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
            documents_nextcloud_runtime_module=documents_nextcloud_runtime_module,
        )
        return jsonify(payload), status

    def api_ocr_workspace_folder_file(folder_id: str, file_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        payload, status = workspace_file_ocr_service_module.ocr_workspace_file_response(
            folder_id,
            file_id,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
        )
        return jsonify(payload), status

    def api_get_workspace_folder_file_ocr_markdown(folder_id: str, file_id: str):
        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        payload, status = workspace_file_ocr_service_module.get_ocr_markdown_response(
            folder_id,
            file_id,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
        )
        return jsonify(payload), status

    def api_patch_workspace_folder_file_ocr_markdown(folder_id: str, file_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        workspace_files_module = get_workspace_files_module()
        payload, status = workspace_file_ocr_service_module.patch_ocr_markdown_response(
            folder_id,
            file_id,
            data,
            workspace_folders_module=workspace_folders_module,
            workspace_files_module=workspace_files_module,
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/workspace-folders',
        endpoint='api_list_workspace_folders',
        view_func=api_list_workspace_folders,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders',
        endpoint='api_create_workspace_folder',
        view_func=api_create_workspace_folder,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>',
        endpoint='api_patch_workspace_folder',
        view_func=api_patch_workspace_folder,
        methods=['PATCH'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>',
        endpoint='api_delete_workspace_folder',
        view_func=api_delete_workspace_folder,
        methods=['DELETE'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files',
        endpoint='api_list_workspace_folder_files',
        view_func=api_list_workspace_folder_files,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files',
        endpoint='api_upload_workspace_folder_file',
        view_func=api_upload_workspace_folder_file,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files/<file_id>',
        endpoint='api_delete_workspace_folder_file',
        view_func=api_delete_workspace_folder_file,
        methods=['DELETE'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files/<file_id>/ocr',
        endpoint='api_ocr_workspace_folder_file',
        view_func=api_ocr_workspace_folder_file,
        methods=['POST'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown',
        endpoint='api_get_workspace_folder_file_ocr_markdown',
        view_func=api_get_workspace_folder_file_ocr_markdown,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown',
        endpoint='api_patch_workspace_folder_file_ocr_markdown',
        view_func=api_patch_workspace_folder_file_ocr_markdown,
        methods=['PATCH'],
    )
