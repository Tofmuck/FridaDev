from __future__ import annotations

import unittest

from core import workspace_folder_generated_images
from core import workspace_folder_generated_images_store


IMAGE_ID = "11111111-2222-4333-8444-555555555555"
FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
TARGET_NAME = "generated-image-11111111-2222-4333-8444-555555555555.png"


class _FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(" ".join(str(sql).split()))


class _FailingConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        raise RuntimeError("raw image db failure prompt SecretPrompt target remote.php")


class _FakeLogger:
    def __init__(self):
        self.records = []

    def warning(self, message, *args, **kwargs):
        self.records.append((message, args, kwargs))


class _UpsertCursor:
    def __init__(self):
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.params = params

    def fetchone(self):
        params = self.params
        return {
            "id": params[0],
            "workspace_folder_id": params[1],
            "display_name": params[2],
            "display_name_hash": params[3],
            "target_name_internal": params[4],
            "target_ref": params[5],
            "mime_type": params[6],
            "image_format": params[7],
            "byte_size": params[8],
            "width": params[9],
            "height": params[10],
            "content_hash": params[11],
            "content_hash_short": params[12],
            "generator_key": params[13],
            "provider_model": params[14],
            "aspect_ratio": params[15],
            "image_size": params[16],
            "prompt_present": params[17],
            "prompt_length_bucket": params[18],
            "local_state": params[19],
            "nextcloud_sync_state": params[20],
            "etag_value": params[21],
            "etag_hash": params[22],
            "last_reason_code": params[23],
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
            "deleted_at": None,
        }


class _UpsertConnection:
    def __init__(self):
        self.cursor_instance = _UpsertCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return self.cursor_instance

    def commit(self):
        return None


def _image(**overrides):
    payload = {
        "id": IMAGE_ID,
        "workspace_folder_id": FOLDER_ID,
        "display_name": "Image sensible",
        "display_name_hash": "abc123def456",
        "target_name_internal": TARGET_NAME,
        "target_ref": "generated-image-target:456defabc123",
        "mime_type": "image/png",
        "image_format": "png",
        "byte_size": 512,
        "width": 1024,
        "height": 768,
        "content_hash": (
            "789abc123def789abc123def789abc123def789abc123def789abc123def789a"
        ),
        "content_hash_short": "789abc123def",
        "generator_key": "image_generator_flux",
        "provider_model": "black-forest-labs/flux.2-pro",
        "aspect_ratio": "4:3",
        "image_size": "1K",
        "prompt_present": True,
        "prompt_length_bucket": "chars_251_to_500",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "etag_value": '"raw-etag-secret"',
        "etag_hash": "123456abcdef",
        "last_reason_code": "folder_generated_image_list_ok",
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


class WorkspaceFolderGeneratedImagesTests(unittest.TestCase):
    def test_schema_creates_dedicated_table_fail_closed_without_foreign_models(self) -> None:
        cur = _FakeCursor()

        workspace_folder_generated_images_store.ensure_schema(cur)

        sql = "\n".join(cur.queries).lower()
        self.assertIn("create table if not exists workspace_folder_generated_images", sql)
        self.assertIn("workspace_folder_id uuid", sql)
        self.assertIn("references workspace_folders(id) on delete cascade", sql)
        self.assertIn("target_name_internal", sql)
        self.assertIn("target_ref", sql)
        self.assertIn("nextcloud_sync_state text not null default 'sync_error'", sql)
        self.assertIn("alter column nextcloud_sync_state set default 'sync_error'", sql)
        self.assertIn("workspace_folder_generated_images_target_name_chk", sql)
        self.assertIn("workspace_folder_generated_images_target_ref_chk", sql)
        self.assertIn("generated-image-[0-9a-f]{8}-[0-9a-f]{4}", sql)
        self.assertIn("generated-image-target:[0-9a-f]{12}", sql)
        self.assertIn("workspace_folder_generated_images_folder_target_active_idx", sql)
        self.assertNotIn("prompt text", sql)
        self.assertNotIn("prompt_hash", sql)
        self.assertNotIn("image_bytes", sql)
        self.assertNotIn("base64", sql)
        self.assertNotIn("data_url", sql)
        self.assertNotIn("payload provider", sql)
        self.assertNotIn("references workspace_files", sql)
        self.assertNotIn("references workspace_folder_exports", sql)
        self.assertNotIn("references workspace_folder_notes", sql)

    def test_upsert_without_remote_proof_never_returns_linked(self) -> None:
        row = workspace_folder_generated_images_store.upsert_generated_image(
            generated_image_id=IMAGE_ID,
            workspace_folder_id=FOLDER_ID,
            display_name="Image locale",
            target_name_internal=TARGET_NAME,
            mime_type="image/png",
            image_format="png",
            nextcloud_sync_state="linked",
            remote_proof=False,
            last_reason_code="folder_generated_image_store_ok",
            db_conn_func=lambda: _UpsertConnection(),
            logger=_FakeLogger(),
        )

        self.assertEqual(row["nextcloud_sync_state"], "sync_error")
        self.assertEqual(row["last_reason_code"], "folder_generated_image_nextcloud_error_redacted")
        user = workspace_folder_generated_images.build_user_projection(row)
        technical = workspace_folder_generated_images.build_technical_projection(row)
        self.assertEqual(user["sync_label"], "synchronisation incomplete")
        self.assertEqual(technical["nextcloud_sync_state"], "sync_error")
        self.assertNotEqual(technical["nextcloud_sync_state"], "linked")

    def test_upsert_with_remote_proof_can_persist_linked_metadata_only(self) -> None:
        row = workspace_folder_generated_images_store.upsert_generated_image(
            generated_image_id=IMAGE_ID,
            workspace_folder_id=FOLDER_ID,
            display_name="Image durable",
            target_name_internal=TARGET_NAME,
            mime_type="image/png",
            image_format="png",
            nextcloud_sync_state="linked",
            remote_proof=True,
            last_reason_code="folder_generated_image_store_ok",
            db_conn_func=lambda: _UpsertConnection(),
            logger=_FakeLogger(),
        )

        self.assertEqual(row["nextcloud_sync_state"], "linked")
        self.assertEqual(row["last_reason_code"], "folder_generated_image_store_ok")
        self.assertEqual(row["target_name_internal"], TARGET_NAME)
        self.assertTrue(row["target_ref"].startswith("generated-image-target:"))

    def test_target_internal_is_mandatory_and_not_reconstructed_from_display_name(self) -> None:
        with self.assertRaises(
            workspace_folder_generated_images_store.WorkspaceFolderGeneratedImagePersistenceError
        ):
            workspace_folder_generated_images_store.upsert_generated_image(
                generated_image_id=IMAGE_ID,
                workspace_folder_id=FOLDER_ID,
                display_name="Nom utilisatrice sensible",
                target_name_internal="",
                mime_type="image/png",
                image_format="png",
                db_conn_func=lambda: _UpsertConnection(),
                logger=_FakeLogger(),
            )

    def test_user_projection_keeps_display_name_and_technical_projection_redacts_it(self) -> None:
        item = workspace_folder_generated_images.apply_generated_image_projection(
            {
                **_image(),
                "prompt": "PROMPT_BRUT_A_NE_PAS_EXPOSER",
                "prompt_hash": "hash prompt interdit",
                "bytes": "raw bytes",
                "image_bytes": b"raw image",
                "base64": "AAAA",
                "data_url": "data:image/png;base64,AAAA",
                "image_data_url": "data:image/png;base64,BBBB",
                "provider_payload": {"secret": "payload"},
                "dav_url": "https://example.test/remote.php/dav/files/secret",
                "xml": "<d:multistatus>secret</d:multistatus>",
                "authorization": "Bearer secret",
            }
        )

        user = item["generated_image_v1_user"]
        technical = item["generated_image_v1_technical"]
        self.assertEqual(user["display_name"], "Image sensible")
        self.assertEqual(user["format"], "png")
        self.assertTrue(user["can_download"])
        self.assertTrue(user["can_open"])
        self.assertTrue(user["can_delete"])
        self.assertEqual(
            user["actions"]["download_reason_code"],
            "folder_generated_image_download_ok",
        )
        self.assertEqual(
            user["actions"]["open_reason_code"],
            "folder_generated_image_open_ok",
        )
        self.assertEqual(
            user["actions"]["delete_reason_code"],
            "folder_generated_image_delete_ok",
        )
        self.assertEqual(technical["display_name_hash"], "abc123def456")
        self.assertEqual(technical["target_ref"], "generated-image-target:456defabc123")
        self.assertEqual(technical["content_hash_short"], "789abc123def")
        self.assertTrue(technical["etag_present"])
        self.assertNotIn("content_hash", item)
        self.assertNotIn(_image()["content_hash"], str(item))
        technical_text = str(technical)
        self.assertNotIn("Image sensible", technical_text)
        self.assertNotIn(TARGET_NAME, technical_text)
        self.assertNotIn("raw-etag-secret", technical_text)
        self.assertNotIn("PROMPT_BRUT", technical_text)
        self.assertNotIn("data:image", technical_text)
        self.assertNotIn("remote.php", technical_text)
        self.assertNotIn("Bearer", technical_text)
        for forbidden in (
            "prompt",
            "prompt_hash",
            "bytes",
            "image_bytes",
            "base64",
            "data_url",
            "image_data_url",
            "provider_payload",
            "dav_url",
            "xml",
            "authorization",
            "content_hash",
            "target_name_internal",
            "etag_value",
        ):
            self.assertNotIn(forbidden, item)

    def test_user_actions_stay_disabled_when_image_is_not_linked_or_target_invalid(self) -> None:
        cases = (
            _image(nextcloud_sync_state="sync_error"),
            _image(local_state="sync_error"),
            _image(target_name_internal="ClientSecretTarget.png"),
            _image(image_format="gif"),
        )

        for image in cases:
            with self.subTest(image=image):
                user = workspace_folder_generated_images.build_user_projection(image)
                self.assertFalse(user["can_download"])
                self.assertFalse(user["can_open"])
                self.assertFalse(user["can_delete"])
                self.assertNotEqual(
                    user["actions"]["download_reason_code"],
                    "folder_generated_image_download_ok",
                )

    def test_formats_are_limited_to_png_jpeg_and_webp(self) -> None:
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("png"), "png")
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("jpg"), "jpeg")
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("jpeg"), "jpeg")
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("webp"), "webp")
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("gif"), "")
        self.assertEqual(workspace_folder_generated_images.normalize_image_format("svg"), "")
        self.assertEqual(workspace_folder_generated_images.normalize_mime_type("image/gif"), "")
        self.assertEqual(workspace_folder_generated_images.normalize_mime_type("image/svg+xml"), "")

    def test_prompt_length_buckets_are_non_ambiguous(self) -> None:
        cases = {
            1: "chars_001_to_250",
            250: "chars_001_to_250",
            251: "chars_251_to_500",
            500: "chars_251_to_500",
            501: "chars_501_to_1000",
            1001: "chars_1001_to_1500",
            1501: "chars_1501_to_2000",
            2001: "",
        }
        for length, bucket in cases.items():
            with self.subTest(length=length):
                self.assertEqual(
                    workspace_folder_generated_images.prompt_length_bucket_for_length(length),
                    bucket,
                )
        self.assertEqual(
            workspace_folder_generated_images.normalize_prompt_length_bucket("1_250"),
            "",
        )

    def test_deleted_generated_images_are_excluded_from_active_projection_list(self) -> None:
        active = _image(id=IMAGE_ID, display_name="Active")
        deleted = _image(
            id="22222222-3333-4444-8555-666666666666",
            display_name="Deleted",
            local_state="deleted",
            deleted_at="2026-06-19T10:10:00Z",
        )

        items = workspace_folder_generated_images.apply_generated_image_list([active, deleted])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["generated_image_v1_user"]["display_name"], "Active")

    def test_invalid_ids_are_redacted_in_technical_refs(self) -> None:
        technical = workspace_folder_generated_images.build_technical_projection(
            _image(id="SecretImageName", workspace_folder_id="ProjetPrive")
        )

        self.assertNotIn("SecretImageName", str(technical))
        self.assertNotIn("ProjetPrive", str(technical))
        self.assertTrue(
            technical["image_ref"].startswith("workspace-generated-image:redacted:")
        )
        self.assertTrue(technical["folder_ref"].startswith("workspace-folder:redacted:"))

    def test_store_serialization_keeps_internal_target_but_projection_hides_it(self) -> None:
        row = workspace_folder_generated_images_store.serialize_generated_image_row(_image())

        self.assertIsNotNone(row)
        self.assertEqual(row["target_name_internal"], TARGET_NAME)
        self.assertEqual(row["etag_value"], '"raw-etag-secret"')
        projected = workspace_folder_generated_images.apply_generated_image_projection(row)
        technical_text = str(projected["generated_image_v1_technical"])
        self.assertNotIn(TARGET_NAME, technical_text)
        self.assertNotIn("raw-etag-secret", technical_text)
        self.assertNotIn("etag_value", technical_text)
        self.assertNotIn("target_name_internal", technical_text)

    def test_raw_alnum_target_ref_is_not_exposed_and_is_recomputed_from_target(self) -> None:
        row = workspace_folder_generated_images_store.serialize_generated_image_row(
            _image(target_ref="ClientSecretImageName")
        )

        self.assertIsNotNone(row)
        self.assertNotEqual(row["target_ref"], "ClientSecretImageName")
        self.assertEqual(
            row["target_ref"],
            workspace_folder_generated_images.target_ref_for_target(TARGET_NAME),
        )
        technical = workspace_folder_generated_images.build_technical_projection(row)
        self.assertEqual(technical["target_ref"], row["target_ref"])
        self.assertNotIn("ClientSecretImageName", str(technical))

    def test_target_ref_is_empty_when_stored_ref_and_internal_target_are_invalid(self) -> None:
        technical = workspace_folder_generated_images.build_technical_projection(
            _image(target_ref="ClientSecretImageName", target_name_internal="ClientSecretTarget")
        )

        self.assertEqual(technical["target_ref"], "")
        self.assertNotIn("ClientSecretImageName", str(technical))
        self.assertNotIn("ClientSecretTarget", str(technical))

    def test_safe_target_ref_accepts_only_structured_generated_image_target_refs(self) -> None:
        self.assertEqual(
            workspace_folder_generated_images.safe_target_ref("generated-image-target:456defabc123"),
            "generated-image-target:456defabc123",
        )
        self.assertEqual(workspace_folder_generated_images.safe_target_ref("ClientSecretImageName"), "")
        self.assertEqual(workspace_folder_generated_images.safe_target_ref("generated-image-target:nothex"), "")

    def test_list_generated_images_fail_closed_without_raw_cause(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(
            workspace_folder_generated_images_store.WorkspaceFolderGeneratedImageLookupError
        ) as ctx:
            workspace_folder_generated_images_store.list_generated_images(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertEqual(str(ctx.exception), "folder_generated_image_lookup_failed")
        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(ctx.exception.workspace_folder_id, FOLDER_ID)
        log_text = str(logger.records)
        self.assertIn("folder_generated_image_lookup_failed", log_text)
        self.assertNotIn("SecretPrompt", log_text)
        self.assertNotIn("remote.php", log_text)

    def test_get_generated_image_fail_closed_without_raw_cause(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(
            workspace_folder_generated_images_store.WorkspaceFolderGeneratedImageLookupError
        ) as ctx:
            workspace_folder_generated_images_store.get_generated_image(
                IMAGE_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertEqual(ctx.exception.operation, "get")
        self.assertEqual(str(ctx.exception), "folder_generated_image_lookup_failed")
        self.assertIsNone(ctx.exception.__cause__)
        self.assertNotIn("raw image db failure", str(ctx.exception))

    def test_lookup_soft_compatibility_is_explicit(self) -> None:
        self.assertEqual(
            workspace_folder_generated_images_store.list_generated_images(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=None,
                fail_closed=False,
            ),
            [],
        )
        self.assertIsNone(
            workspace_folder_generated_images_store.get_generated_image(
                IMAGE_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=None,
                fail_closed=False,
            )
        )

    def test_tombstone_generated_image_db_failure_is_not_silent(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(
            workspace_folder_generated_images_store.WorkspaceFolderGeneratedImageTombstoneError
        ) as ctx:
            workspace_folder_generated_images_store.tombstone_generated_image(
                IMAGE_ID,
                expected_workspace_folder_id=FOLDER_ID,
                expected_target_name_internal=TARGET_NAME,
                expected_target_ref=workspace_folder_generated_images.target_ref_for_target(
                    TARGET_NAME
                ),
                expected_parent_folder_ref="workspace-folder:aaaaaaaa:abc123def456",
                expected_parent_name_hash="abc123def456",
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
            )

        self.assertEqual(str(ctx.exception), "folder_generated_image_local_persistence_failed")
        self.assertEqual(ctx.exception.generated_image_id, IMAGE_ID)
        self.assertIsNone(ctx.exception.__cause__)
        self.assertNotIn("raw image db failure", str(ctx.exception))
        log_text = str(logger.records)
        self.assertIn("tombstone_failed", log_text)
        self.assertNotIn("SecretPrompt", log_text)
        self.assertNotIn("remote.php", log_text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
