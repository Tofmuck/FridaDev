"""Synthetic DB boundary, never an implementation of folder listing."""
from copy import deepcopy

FOLDER_ID = "11111111-2222-4333-8444-555555555555"
DIAGNOSTIC = "synthetic SQL diagnostic must remain private"


def folder_row(**fields):
    return dict(id=FOLDER_ID, display_name="Synthetic workspace", icon_key="book",
                description="", sort_order=1000, created_at="2026-10-05T00:00:00Z",
                updated_at="2026-10-05T00:00:00Z", deleted_at=None, **fields)


class ListingDatabase:
    def __init__(self, rows=(), failure=None):
        self.rows = list(rows)
        self.failure = failure
        self.queries = []
        self.commits = 0
        self.connections = 0

    def connect(self):
        self.connections += 1
        if self.failure == "connect":
            raise RuntimeError(DIAGNOSTIC)
        return ListingConnection(self)


class ListingConnection:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self, **_):
        return ListingCursor(self.database)

    def commit(self):
        self.database.commits += 1


class ListingCursor:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.database.queries.append(" ".join(sql.split()))
        if self.database.failure == "execute":
            raise RuntimeError(DIAGNOSTIC)

    def fetchall(self):
        if self.database.failure == "fetch":
            raise RuntimeError(DIAGNOSTIC)
        return deepcopy(self.database.rows)


def backend_listing_responses():
    """Capture real Flask/route/service/wrapper/store bytes for frontend proof."""
    from unittest.mock import patch
    from tests.support.server_test_bootstrap import load_server_module_for_tests
    from core import workspace_folders
    server = load_server_module_for_tests()
    result = {}
    for label, database in [("empty", ListingDatabase()), ("error", ListingDatabase(failure="connect"))]:
        with patch.object(server, "workspace_folders", workspace_folders), patch.object(workspace_folders, "_db_conn", database.connect):
            response = server.app.test_client().get("/api/workspace-folders")
            result[label] = dict(status=response.status_code, payload=response.get_json())
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(backend_listing_responses(), ensure_ascii=False))
