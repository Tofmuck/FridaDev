from __future__ import annotations

"""Content-free Generated Images V1 reason codes."""


REASON_FOLDER_INVALID = "folder_generated_image_folder_invalid"
REASON_FOLDER_DELETED = "folder_generated_image_folder_deleted"
REASON_FOLDER_NOT_LINKED = "folder_generated_image_folder_not_linked"
REASON_FOLDER_NOT_ELIGIBLE = "folder_generated_image_folder_not_eligible"
REASON_IMAGES_TARGET_MISSING = "folder_generated_image_images_target_missing"
REASON_IMAGES_TARGET_NOT_COLLECTION = "folder_generated_image_images_target_not_collection"
REASON_IMAGES_TARGET_UNAVAILABLE = "folder_generated_image_images_target_unavailable"
REASON_CLIENT_IMAGE_ID_FORBIDDEN = "folder_generated_image_client_image_id_forbidden"
REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN = (
    "folder_generated_image_client_workspace_folder_id_forbidden"
)
REASON_PROMPT_MISSING = "folder_generated_image_prompt_missing"
REASON_PROMPT_TOO_LARGE = "folder_generated_image_prompt_too_large"
REASON_GENERATOR_UNSUPPORTED = "folder_generated_image_generator_unsupported"
REASON_ASPECT_RATIO_UNSUPPORTED = "folder_generated_image_aspect_ratio_unsupported"
REASON_SIZE_UNSUPPORTED = "folder_generated_image_size_unsupported"
REASON_PROVIDER_TIMEOUT = "folder_generated_image_provider_timeout"
REASON_PROVIDER_ERROR_REDACTED = "folder_generated_image_provider_error_redacted"
REASON_PROVIDER_NO_IMAGE = "folder_generated_image_provider_no_image"
REASON_PROVIDER_PAYLOAD_INVALID = "folder_generated_image_provider_payload_invalid"
REASON_DATA_URL_INVALID = "folder_generated_image_data_url_invalid"
REASON_DATA_URL_TOO_LARGE = "folder_generated_image_data_url_too_large"
REASON_FORMAT_UNSUPPORTED = "folder_generated_image_format_unsupported"
REASON_MIME_INVALID = "folder_generated_image_mime_invalid"
REASON_TOO_LARGE = "folder_generated_image_too_large"
REASON_DIMENSIONS_INVALID = "folder_generated_image_dimensions_invalid"
REASON_NAME_INVALID = "folder_generated_image_name_invalid"
REASON_NAME_CONFLICT = "folder_generated_image_name_conflict"
REASON_CREATE_OK = "folder_generated_image_create_ok"
REASON_STORE_OK = "folder_generated_image_store_ok"
REASON_STORE_FAILED_REDACTED = "folder_generated_image_store_failed_redacted"
REASON_LOCAL_PERSISTENCE_FAILED = "folder_generated_image_local_persistence_failed"
REASON_REMOTE_COMPENSATION_OK = "folder_generated_image_remote_compensation_ok"
REASON_REMOTE_COMPENSATION_FAILED = "folder_generated_image_remote_compensation_failed"
REASON_LIST_OK = "folder_generated_image_list_ok"
REASON_LOOKUP_OK = "folder_generated_image_lookup_ok"
REASON_LOOKUP_FAILED = "folder_generated_image_lookup_failed"
REASON_IMAGE_ID_INVALID = "folder_generated_image_id_invalid"
REASON_NOT_FOUND = "folder_generated_image_not_found"
REASON_DELETED = "folder_generated_image_deleted"
REASON_NOT_LINKED = "folder_generated_image_not_linked"
REASON_ACCESS_NOT_PREPARED = "folder_generated_image_access_not_prepared"
REASON_DOWNLOAD_OK = "folder_generated_image_download_ok"
REASON_OPEN_OK = "folder_generated_image_open_ok"
REASON_DELETE_OK = "folder_generated_image_delete_ok"
REASON_DELETE_FAILED_REDACTED = "folder_generated_image_delete_failed_redacted"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_generated_image_nextcloud_error_redacted"

REASON_CODE_CATALOG = frozenset(
    {
        REASON_FOLDER_INVALID,
        REASON_FOLDER_DELETED,
        REASON_FOLDER_NOT_LINKED,
        REASON_FOLDER_NOT_ELIGIBLE,
        REASON_IMAGES_TARGET_MISSING,
        REASON_IMAGES_TARGET_NOT_COLLECTION,
        REASON_IMAGES_TARGET_UNAVAILABLE,
        REASON_CLIENT_IMAGE_ID_FORBIDDEN,
        REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN,
        REASON_PROMPT_MISSING,
        REASON_PROMPT_TOO_LARGE,
        REASON_GENERATOR_UNSUPPORTED,
        REASON_ASPECT_RATIO_UNSUPPORTED,
        REASON_SIZE_UNSUPPORTED,
        REASON_PROVIDER_TIMEOUT,
        REASON_PROVIDER_ERROR_REDACTED,
        REASON_PROVIDER_NO_IMAGE,
        REASON_PROVIDER_PAYLOAD_INVALID,
        REASON_DATA_URL_INVALID,
        REASON_DATA_URL_TOO_LARGE,
        REASON_FORMAT_UNSUPPORTED,
        REASON_MIME_INVALID,
        REASON_TOO_LARGE,
        REASON_DIMENSIONS_INVALID,
        REASON_NAME_INVALID,
        REASON_NAME_CONFLICT,
        REASON_CREATE_OK,
        REASON_STORE_OK,
        REASON_STORE_FAILED_REDACTED,
        REASON_LOCAL_PERSISTENCE_FAILED,
        REASON_REMOTE_COMPENSATION_OK,
        REASON_REMOTE_COMPENSATION_FAILED,
        REASON_LIST_OK,
        REASON_LOOKUP_OK,
        REASON_LOOKUP_FAILED,
        REASON_IMAGE_ID_INVALID,
        REASON_NOT_FOUND,
        REASON_DELETED,
        REASON_NOT_LINKED,
        REASON_ACCESS_NOT_PREPARED,
        REASON_DOWNLOAD_OK,
        REASON_OPEN_OK,
        REASON_DELETE_OK,
        REASON_DELETE_FAILED_REDACTED,
        REASON_NEXTCLOUD_ERROR_REDACTED,
    }
)

REASON_CODE_EXPORTS = {
    name: value
    for name, value in globals().items()
    if name.startswith("REASON_") and name != "REASON_CODE_EXPORTS"
}
