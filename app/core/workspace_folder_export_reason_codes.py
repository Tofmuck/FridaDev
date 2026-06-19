from __future__ import annotations

"""Content-free Exports V1 reason codes."""


REASON_FOLDER_NOT_LINKED = "folder_export_folder_not_linked"
REASON_FOLDER_INVALID = "folder_export_folder_invalid"
REASON_FOLDER_DELETED = "folder_export_folder_deleted"
REASON_EXPORTS_TARGET_MISSING = "folder_export_exports_target_missing"
REASON_EXPORTS_TARGET_NOT_COLLECTION = "folder_export_exports_target_not_collection"
REASON_EXPORTS_TARGET_UNAVAILABLE = "folder_export_exports_target_unavailable"
REASON_NAME_INVALID = "folder_export_name_invalid"
REASON_NAME_CONFLICT = "folder_export_name_conflict"
REASON_CLIENT_EXPORT_ID_FORBIDDEN = "folder_export_client_export_id_forbidden"
REASON_EXPORT_NOT_FOUND = "folder_export_not_found"
REASON_EXPORT_DELETED = "folder_export_deleted"
REASON_CONTENT_ACCESS_NOT_PREPARED = "folder_export_access_not_prepared"
REASON_SOURCE_MISSING = "folder_export_source_missing"
REASON_SOURCE_AMBIGUOUS = "folder_export_source_ambiguous"
REASON_SOURCE_UNSUPPORTED = "folder_export_source_unsupported"
REASON_SOURCE_UNAVAILABLE = "folder_export_source_unavailable"
REASON_SOURCE_NOT_PREPARED = "folder_export_source_not_prepared"
REASON_SOURCE_READ_UNAVAILABLE = "folder_export_source_read_unavailable"
REASON_SOURCE_READ_TOO_LARGE = "folder_export_source_read_too_large"
REASON_FORMAT_UNSUPPORTED = "folder_export_format_unsupported"
REASON_DEPENDENCY_UNAVAILABLE = "folder_export_dependency_unavailable"
REASON_TOO_LARGE = "folder_export_too_large"
REASON_GENERATION_FAILED_REDACTED = "folder_export_generation_failed_redacted"
REASON_CREATE_OK = "folder_export_create_ok"
REASON_STORE_OK = "folder_export_store_ok"
REASON_LIST_OK = "folder_export_list_ok"
REASON_LOOKUP_OK = "folder_export_lookup_ok"
REASON_LOOKUP_FAILED = "folder_export_lookup_failed"
REASON_DOWNLOAD_OK = "folder_export_download_ok"
REASON_REUSE_OK = "folder_export_reuse_ok"
REASON_LOCAL_PERSISTENCE_FAILED = "folder_export_local_persistence_failed"
REASON_REMOTE_COMPENSATION_OK = "folder_export_remote_compensation_ok"
REASON_REMOTE_COMPENSATION_FAILED = "folder_export_remote_compensation_failed"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_export_nextcloud_error_redacted"

REASON_CODE_CATALOG = frozenset(
    {
        REASON_FOLDER_NOT_LINKED,
        REASON_FOLDER_INVALID,
        REASON_FOLDER_DELETED,
        REASON_EXPORTS_TARGET_MISSING,
        REASON_EXPORTS_TARGET_NOT_COLLECTION,
        REASON_EXPORTS_TARGET_UNAVAILABLE,
        REASON_NAME_INVALID,
        REASON_NAME_CONFLICT,
        REASON_CLIENT_EXPORT_ID_FORBIDDEN,
        REASON_EXPORT_NOT_FOUND,
        REASON_EXPORT_DELETED,
        REASON_CONTENT_ACCESS_NOT_PREPARED,
        REASON_SOURCE_MISSING,
        REASON_SOURCE_AMBIGUOUS,
        REASON_SOURCE_UNSUPPORTED,
        REASON_SOURCE_UNAVAILABLE,
        REASON_SOURCE_NOT_PREPARED,
        REASON_SOURCE_READ_UNAVAILABLE,
        REASON_SOURCE_READ_TOO_LARGE,
        REASON_FORMAT_UNSUPPORTED,
        REASON_DEPENDENCY_UNAVAILABLE,
        REASON_TOO_LARGE,
        REASON_GENERATION_FAILED_REDACTED,
        REASON_CREATE_OK,
        REASON_STORE_OK,
        REASON_LIST_OK,
        REASON_LOOKUP_OK,
        REASON_LOOKUP_FAILED,
        REASON_DOWNLOAD_OK,
        REASON_REUSE_OK,
        REASON_LOCAL_PERSISTENCE_FAILED,
        REASON_REMOTE_COMPENSATION_OK,
        REASON_REMOTE_COMPENSATION_FAILED,
        REASON_NEXTCLOUD_ERROR_REDACTED,
    }
)

REASON_CODE_EXPORTS = {
    name: value
    for name, value in globals().items()
    if name.startswith("REASON_") and name != "REASON_CODE_EXPORTS"
}
