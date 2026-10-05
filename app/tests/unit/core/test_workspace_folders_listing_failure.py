"""P2-M2-04: distinguish unknown inventory from successful empty inventory."""
import unittest
from unittest.mock import Mock, patch

from core import workspace_folders_store as store
from core import workspace_folder_nextcloud_runtime as runtime
from core import workspace_folder_nextcloud_reconcile as reconcile
from core import workspace_folder_standard_subfolders as standards
from tests.support.workspace_folder_listing_fixture import ListingDatabase, folder_row, FOLDER_ID, DIAGNOSTIC


class WorkspaceFoldersListingFailureTests(unittest.TestCase):
    def listing(self, database, **options):
        return store.list_workspace_folders(db_conn_func=database.connect, logger=self.logger, **options)

    def setUp(self):
        self.logger = Mock()

    def reconcile_after_remote_observation(self, final_rows):
        from tests.unit.core.test_workspace_folders_contract import _FakeNextcloudFolderClient
        initial = {**folder_row(link_workspace_folder_id=FOLDER_ID,
                               link_nextcloud_sync_state="linked",
                               link_nextcloud_folder_ref="workspace-folder:test",
                               link_nextcloud_name_hash="abc123def456"),
                   "display_name": "Philosophie"}
        database = ListingDatabase([initial])
        client = _FakeNextcloudFolderClient()
        client.statuses["Philosophie"] = 207
        for name in ["Documents", "Notes", "Exports", "Images"]:
            client.path_statuses[("Philosophie", name)] = 207
        status = client.folder_status
        def status_then_change_inventory(name):
            observed = status(name)
            database.rows = [initial] if final_rows is None else final_rows
            return observed
        client.folder_status = status_then_change_inventory
        result = reconcile.reconcile_existing_workspace_folders(
            db_conn_func=database.connect, logger=self.logger, client=client)
        self.assertEqual(database.connections, 2)
        self.assertEqual(len(database.queries), 2)
        self.assertTrue(all(query.startswith("SELECT") for query in database.queries))
        self.assertEqual(database.commits, 0)
        self.assertEqual(client.status_checked, ["Philosophie"])
        self.assertEqual(client.path_status_checked, [("Philosophie", name)
            for name in ["Documents", "Notes", "Exports", "Images"]])
        self.assertEqual(client.created + client.created_paths + client.moved + client.deleted, [])
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts_before"]["active"], 1)
        initial_record, final_record = result["records"][0], result["records"][-1]
        self.assertEqual(initial_record["case_id"], "LOT9_INVENTORY_ACTIVE_FOLDERS")
        self.assertEqual(initial_record["examples"]["philosophie"], "present_reconciled")
        self.assertEqual(initial_record["counts_before"], result["counts_before"])
        self.assertEqual(final_record["case_id"], "LOT9_FINAL_STATE")
        self.assertEqual(final_record["verdict"], "met")
        self.assertEqual(final_record["counts_after"], result["counts_after"])
        return result, final_record

    def test_p2_m2_05_final_empty_does_not_reuse_initial_examples(self):
        result, final_record = self.reconcile_after_remote_observation([])
        self.assertEqual(result["counts_after"]["active"], 0)
        self.assertEqual(final_record["examples"], {
            "philosophie": "expected_example_absent", "conflit_lycee": "expected_example_absent"})
        self.assertEqual(result["examples"], final_record["examples"])

    def test_p2_m2_05_present_final_inventory_control(self):
        result, final_record = self.reconcile_after_remote_observation(None)
        self.assertEqual(result["counts_after"]["active"], 1)
        self.assertEqual(result["examples"], final_record["examples"])
        self.assertEqual(result["examples"]["philosophie"], "present_reconciled")

    def test_p2_m2_05_different_nonempty_final_inventory_is_authoritative(self):
        for state, expected in [("linked", "present_reconciled"),
                                ("local_only", "present_pending"),
                                ("conflict", "present_no_go"), ("error", "present_no_go")]:
            with self.subTest(state=state):
                final = {**folder_row(link_workspace_folder_id=FOLDER_ID,
                                     link_nextcloud_sync_state=state,
                                     link_nextcloud_folder_ref="workspace-folder:test",
                                     link_nextcloud_name_hash="abc123def456"),
                         "display_name": "Conflit lycée"}
                result, final_record = self.reconcile_after_remote_observation([final])
                self.assertEqual(result["counts_after"]["active"], 1)
                self.assertEqual(result["examples"], final_record["examples"])
                self.assertEqual(result["examples"], {
                    "philosophie": "expected_example_absent", "conflit_lycee": expected})

    def test_successful_empty_is_a_real_list(self):
        database = ListingDatabase()
        self.assertEqual(self.listing(database), [])
        self.assertEqual(database.connections, 1)
        self.logger.warning.assert_not_called()

    def test_success_preserves_projection_and_listing_options(self):
        database = ListingDatabase([folder_row()])
        for include_deleted in [False, True]:
            with self.subTest(include_deleted=include_deleted):
                items = self.listing(database, include_deleted=include_deleted)
                self.assertEqual(items[0]["id"], FOLDER_ID)
                self.assertEqual(items[0]["icon_key"], "book")
                self.assertEqual(items[0]["nextcloud_sync_state"], "local_only")
                self.assertEqual("WHERE folders.deleted_at IS NULL" in database.queries[-1], not include_deleted)
                self.assertIn("ORDER BY folders.sort_order ASC, folders.created_at ASC, folders.display_name ASC", database.queries[-1])

    def test_connection_execute_and_fetch_failures_are_not_empty_success(self):
        for failure in ["connect", "execute", "fetch"]:
            with self.subTest(failure=failure):
                database = ListingDatabase([folder_row()], failure=failure)
                with self.assertRaisesRegex(RuntimeError, "workspace_folder_list_failed"):
                    self.listing(database)
                self.assertEqual(database.connections, 1)
                self.assertEqual(database.commits, 0)

    def test_serialization_failure_after_valid_row_never_returns_partial_inventory(self):
        database = ListingDatabase([folder_row(), {**folder_row(), "sort_order": "invalid"}])
        with self.assertRaisesRegex(RuntimeError, "workspace_folder_list_failed"):
            self.listing(database)
        self.assertEqual(database.connections, 1)

    def test_local_create_and_rename_do_not_write_after_failed_name_listing(self):
        for operation in ["create", "rename"]:
            with self.subTest(operation=operation):
                database = ListingDatabase(failure="connect")
                if operation == "create":
                    result = store.create_workspace_folder(display_name="Synthetic new", db_conn_func=database.connect, logger=self.logger)
                else:
                    result = store.update_workspace_folder(FOLDER_ID, display_name="Synthetic new", db_conn_func=database.connect, logger=self.logger)
                self.assertIsNone(result)
                self.assertEqual(database.connections, 1)
                self.assertEqual(database.queries, [])
                self.assertEqual(database.commits, 0)

    def test_initial_runtime_listing_failure_prevents_sql_and_dav_mutation(self):
        for operation in ["create", "rename"]:
            with self.subTest(operation=operation):
                database = ListingDatabase(failure="connect")
                client = Mock()
                with patch.object(store, "get_workspace_folder", return_value={**folder_row(), "nextcloud_sync_state": "linked"}):
                    if operation == "create":
                        result = runtime.create_workspace_folder_nextcloud_first(display_name="Synthetic new", icon_key="book",
                            description="", sort_order=1000, db_conn_func=database.connect, logger=self.logger, client=client)
                    else:
                        result = runtime.rename_workspace_folder_nextcloud_first(FOLDER_ID, display_name="Synthetic new",
                            db_conn_func=database.connect, logger=self.logger, client=client)
                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], "workspace_folder_list_failed")
                self.assertEqual(result["status"], 503)
                self.assertEqual(database.queries, [])
                self.assertEqual(client.mock_calls, [])

    def test_initial_reconciliation_and_standard_inventory_failure_are_unknown(self):
        for module, name in [(reconcile, "reconcile_existing_workspace_folders"),
                             (standards, "ensure_standard_subfolders_for_linked_folders")]:
            with self.subTest(module=name):
                database = ListingDatabase(failure="connect")
                client = Mock()
                result = getattr(module, name)(db_conn_func=database.connect, logger=self.logger, client=client)
                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], "workspace_folder_list_failed")
                counts_key = "counts_before" if module is reconcile else "folder_counts"
                self.assertIsNone(result[counts_key])
                self.assertTrue(all(record["verdict"] != "not_applicable" for record in result["records"]))
                self.assertEqual(client.mock_calls, [])

    def test_explicit_recovery_has_no_automatic_retry(self):
        database = ListingDatabase(failure="connect")
        with self.assertRaises(RuntimeError):
            self.listing(database)
        self.assertEqual(database.connections, 1)
        database.failure = None
        self.assertEqual(self.listing(database), [])
        self.assertEqual(database.connections, 2)

    def test_create_validation_reread_after_mkcol_keeps_existing_partial_result(self):
        from tests.unit.core.test_workspace_folders_contract import _FakeNextcloudFolderClient
        database = ListingDatabase()
        client = _FakeNextcloudFolderClient()
        def connect():
            if database.connections == 1:
                database.connections += 1
                raise RuntimeError(DIAGNOSTIC)
            return database.connect()
        result = runtime.create_workspace_folder_nextcloud_first(display_name="Synthetic new", icon_key="book",
            description="", sort_order=1000, db_conn_func=connect, logger=self.logger, client=client)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
        self.assertEqual(result["rollback_reason_code"], "workspace_folder_nextcloud_rollback_ownership_unverified")
        self.assertEqual(client.created, ["Synthetic-new"])
        self.assertEqual(len(client.created_paths), 4)
        self.assertEqual(client.deleted, [])
        self.assertEqual(database.connections, 2)
        self.assertFalse(any("INSERT INTO" in query for query in database.queries))

    def test_rename_validation_reread_preserves_rollback_and_rollback_failure(self):
        from tests.unit.core.test_workspace_folder_rename_commit_projection import (
            _RelationalDatabase, _RelationalCursor, _StatefulNextcloud, NEW_DISPLAY_NAME,
            OLD_TARGET, NEW_TARGET,
        )
        execute = _RelationalCursor.execute
        for failed_rollback in [False, True]:
            with self.subTest(failed_rollback=failed_rollback):
                database = _RelationalDatabase()
                client = _StatefulNextcloud(fail_move_calls={2} if failed_rollback else set())
                reads = []
                def execute_with_failure(cursor, sql, params=None):
                    if "FROM workspace_folders folders" in sql and "LIMIT 1" not in sql:
                        reads.append(sql)
                        if len(reads) == 2:
                            raise RuntimeError(DIAGNOSTIC)
                    return execute(cursor, sql, params)
                with patch.object(_RelationalCursor, "execute", execute_with_failure):
                    result = runtime.rename_workspace_folder_nextcloud_first(FOLDER_ID, display_name=NEW_DISPLAY_NAME,
                        db_conn_func=database.connect, logger=self.logger, client=client)
                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
                self.assertEqual(result["rollback_reason_code"], "workspace_folder_nextcloud_rollback_failed"
                    if failed_rollback else "workspace_folder_nextcloud_rollback_ok")
                self.assertEqual(client.moves, [(OLD_TARGET, NEW_TARGET), (NEW_TARGET, OLD_TARGET)])
                self.assertEqual(database.folder_update_attempts, 0)
                self.assertEqual(database.folder["display_name"], "Alpha Workspace")
                self.assertEqual(client.folders, {NEW_TARGET if failed_rollback else OLD_TARGET})
                self.assertEqual(len(reads), 2)

    def test_final_reconciliation_failure_keeps_completed_actions_and_unknown_final_counts(self):
        from tests.unit.core.test_workspace_folders_contract import _FakeNextcloudFolderClient
        row = folder_row(link_workspace_folder_id=FOLDER_ID, link_nextcloud_sync_state="linked",
                         link_nextcloud_folder_ref="workspace-folder:test", link_nextcloud_name_hash="abc123def456")
        database = ListingDatabase([row])
        client = _FakeNextcloudFolderClient()
        client.statuses["Synthetic-workspace"] = 207
        status = client.folder_status
        def status_then_fail(name):
            result = status(name)
            database.failure = "connect"
            return result
        client.folder_status = status_then_fail
        result = reconcile.reconcile_existing_workspace_folders(db_conn_func=database.connect, logger=self.logger, client=client)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_list_failed")
        self.assertEqual(result["counts_before"]["active"], 1)
        self.assertIsNone(result["counts_after"])
        self.assertIsNone(result["examples"])
        self.assertEqual(result["records"][-1]["verdict"], "partial")
        self.assertEqual(result["records"][-1]["operation"], "final_state")
        self.assertEqual(len(client.created_paths), 4)
        self.assertEqual(client.deleted, [])
        self.assertEqual(database.connections, 2)

    def test_final_reconciliation_listing_failure_after_client_failure_is_also_unknown(self):
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientError, REASON_UNAVAILABLE
        database = ListingDatabase([folder_row()])
        def fail_client(_):
            database.failure = "connect"
            raise NextcloudFolderClientError(REASON_UNAVAILABLE)
        with patch.object(reconcile, "_client", fail_client):
            result = reconcile.reconcile_existing_workspace_folders(db_conn_func=database.connect, logger=self.logger)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["counts_after"])
        self.assertIsNone(result["examples"])
        self.assertEqual(result["reason_code"], "workspace_folder_list_failed")
        self.assertTrue(any(record["reason_code"] == REASON_UNAVAILABLE for record in result["records"]))
