from __future__ import annotations

import importlib
import sys

from core import conv_store
from memory import memory_store


def load_server_module_for_tests():
    """Import the server module with DB bootstrap disabled for repo test scripts."""

    original_init_db = memory_store.init_db
    original_init_catalog_db = conv_store.init_catalog_db
    original_init_messages_db = conv_store.init_messages_db
    sys.modules.pop('server', None)
    memory_store.init_db = lambda: None
    conv_store.init_catalog_db = lambda: None
    conv_store.init_messages_db = lambda: None
    try:
        return importlib.import_module('server')
    finally:
        memory_store.init_db = original_init_db
        conv_store.init_catalog_db = original_init_catalog_db
        conv_store.init_messages_db = original_init_messages_db
