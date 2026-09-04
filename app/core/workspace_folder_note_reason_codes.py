from __future__ import annotations

"""Content-free Notes V1 reason codes."""


REASON_FOLDER_NOT_LINKED = "folder_note_folder_not_linked"
REASON_NOTES_TARGET_MISSING = "folder_note_notes_target_missing"
REASON_NOTES_TARGET_NOT_COLLECTION = "folder_note_notes_target_not_collection"
REASON_NOTES_TARGET_UNAVAILABLE = "folder_note_notes_target_unavailable"
REASON_NAME_INVALID = "folder_note_name_invalid"
REASON_NAME_CONFLICT = "folder_note_name_conflict"
REASON_CREATE_OK = "folder_note_create_ok"
REASON_APPEND_OK = "folder_note_append_ok"
REASON_APPEND_EMPTY = "folder_note_append_empty"
REASON_READ_OK = "folder_note_read_ok"
REASON_LIST_OK = "folder_note_list_ok"
REASON_LOOKUP_OK = "folder_note_lookup_ok"
REASON_LOOKUP_AMBIGUOUS = "folder_note_lookup_ambiguous"
REASON_LOOKUP_FAILED = "folder_note_lookup_failed"
REASON_NOT_FOUND = "folder_note_not_found"
REASON_TOO_LARGE = "folder_note_too_large"
REASON_APPEND_TOO_LARGE = "folder_note_append_too_large"
REASON_VERSION_CONFLICT = "folder_note_version_conflict"
REASON_ETAG_MISSING = "folder_note_etag_missing"
REASON_REMOTE_READ_FAILED = "folder_note_remote_read_failed"
REASON_REMOTE_WRITE_FAILED = "folder_note_remote_write_failed"
REASON_LOCAL_PERSISTENCE_FAILED = "folder_note_local_persistence_failed"
REASON_REMOTE_COMPENSATION_OK = "folder_note_remote_compensation_ok"
REASON_REMOTE_COMPENSATION_MISSING = "folder_note_remote_compensation_missing"
REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED = (
    "folder_note_remote_compensation_precondition_failed"
)
REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED = (
    "folder_note_remote_compensation_ownership_unverified"
)
REASON_REMOTE_COMPENSATION_FAILED = "folder_note_remote_compensation_failed"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_note_nextcloud_error_redacted"
REASON_TURN_LIMIT_EXCEEDED = "folder_note_turn_limit_exceeded"

REASON_CODE_CATALOG = frozenset(
    {
        REASON_FOLDER_NOT_LINKED,
        REASON_NOTES_TARGET_MISSING,
        REASON_NOTES_TARGET_NOT_COLLECTION,
        REASON_NOTES_TARGET_UNAVAILABLE,
        REASON_NAME_INVALID,
        REASON_NAME_CONFLICT,
        REASON_CREATE_OK,
        REASON_APPEND_OK,
        REASON_APPEND_EMPTY,
        REASON_READ_OK,
        REASON_LIST_OK,
        REASON_LOOKUP_OK,
        REASON_LOOKUP_AMBIGUOUS,
        REASON_LOOKUP_FAILED,
        REASON_NOT_FOUND,
        REASON_TOO_LARGE,
        REASON_APPEND_TOO_LARGE,
        REASON_VERSION_CONFLICT,
        REASON_ETAG_MISSING,
        REASON_REMOTE_READ_FAILED,
        REASON_REMOTE_WRITE_FAILED,
        REASON_LOCAL_PERSISTENCE_FAILED,
        REASON_REMOTE_COMPENSATION_OK,
        REASON_REMOTE_COMPENSATION_MISSING,
        REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
        REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
        REASON_REMOTE_COMPENSATION_FAILED,
        REASON_NEXTCLOUD_ERROR_REDACTED,
        REASON_TURN_LIMIT_EXCEEDED,
    }
)

REASON_CODE_EXPORTS = {
    name: value
    for name, value in globals().items()
    if name.startswith("REASON_") and name != "REASON_CODE_EXPORTS"
}
