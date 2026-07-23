from __future__ import annotations

from typing import Any, Callable

from flask import Flask, Response, jsonify, request


def register_workspace_folder_generated_image_routes(
    app: Flask,
    *,
    workspace_folder_generated_images_service_module: Any,
    get_workspace_folders_module: Callable[[], Any],
    get_workspace_folder_generated_images_module: Callable[[], Any],
    get_workspace_folder_generated_image_nextcloud_runtime_module: Callable[[], Any],
    get_workspace_folder_generated_image_content_service_module: Callable[[], Any],
) -> None:
    def api_list_workspace_folder_generated_images(folder_id: str):
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        payload, status = (
            workspace_folder_generated_images_service_module
            .list_workspace_folder_generated_images_response(
                folder_id,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
            )
        )
        return jsonify(payload), status

    def api_get_workspace_folder_generated_image(folder_id: str, image_id: str):
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        payload, status = (
            workspace_folder_generated_images_service_module
            .get_workspace_folder_generated_image_response(
                folder_id,
                image_id,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
            )
        )
        return jsonify(payload), status

    def api_download_workspace_folder_generated_image(folder_id: str, image_id: str):
        content_service_module = (
            get_workspace_folder_generated_image_content_service_module()
        )
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        result = (
            content_service_module
            .download_workspace_folder_generated_image_response(
                folder_id,
                image_id,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
                disposition="attachment",
            )
        )
        if result.ok:
            return Response(result.content, status=result.status, headers=dict(result.headers or {}))
        return jsonify(dict(result.payload or {})), result.status

    def api_open_workspace_folder_generated_image(folder_id: str, image_id: str):
        content_service_module = (
            get_workspace_folder_generated_image_content_service_module()
        )
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        result = (
            content_service_module
            .download_workspace_folder_generated_image_response(
                folder_id,
                image_id,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
                disposition="inline",
            )
        )
        if result.ok:
            return Response(result.content, status=result.status, headers=dict(result.headers or {}))
        return jsonify(dict(result.payload or {})), result.status

    def api_delete_workspace_folder_generated_image(folder_id: str, image_id: str):
        content_service_module = (
            get_workspace_folder_generated_image_content_service_module()
        )
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        payload, status = (
            content_service_module
            .delete_workspace_folder_generated_image_response(
                folder_id,
                image_id,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
            )
        )
        return jsonify(payload), status

    def api_create_workspace_folder_generated_image(folder_id: str):
        data = request.get_json(silent=True) or {}
        workspace_folders_module = get_workspace_folders_module()
        generated_images_module = get_workspace_folder_generated_images_module()
        generated_images_runtime_module = (
            get_workspace_folder_generated_image_nextcloud_runtime_module()
        )
        payload, status = (
            workspace_folder_generated_images_service_module
            .create_workspace_folder_generated_image_response(
                folder_id,
                data,
                workspace_folders_module=workspace_folders_module,
                generated_images_module=generated_images_module,
                generated_images_runtime_module=generated_images_runtime_module,
            )
        )
        return jsonify(payload), status

    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images',
        endpoint='api_list_workspace_folder_generated_images',
        view_func=api_list_workspace_folder_generated_images,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images/<image_id>',
        endpoint='api_get_workspace_folder_generated_image',
        view_func=api_get_workspace_folder_generated_image,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images/<image_id>/download',
        endpoint='api_download_workspace_folder_generated_image',
        view_func=api_download_workspace_folder_generated_image,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images/<image_id>/open',
        endpoint='api_open_workspace_folder_generated_image',
        view_func=api_open_workspace_folder_generated_image,
        methods=['GET'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images/<image_id>',
        endpoint='api_delete_workspace_folder_generated_image',
        view_func=api_delete_workspace_folder_generated_image,
        methods=['DELETE'],
    )
    app.add_url_rule(
        '/api/workspace-folders/<folder_id>/generated-images',
        endpoint='api_create_workspace_folder_generated_image',
        view_func=api_create_workspace_folder_generated_image,
        methods=['POST'],
    )
