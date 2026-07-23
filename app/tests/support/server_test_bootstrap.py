from __future__ import annotations

import importlib
import sys

from admin import runtime_settings
from core import active_conversation_documents
from core import conv_store
from memory import memory_store


def load_server_module_for_tests():
    """Import the server module with DB bootstrap disabled for repo test scripts."""

    original_init_db = memory_store.init_db
    original_active_documents_init_db = active_conversation_documents.init_db
    original_ensure_conv_dir = conv_store.ensure_conv_dir
    original_init_catalog_db = conv_store.init_catalog_db
    original_init_messages_db = conv_store.init_messages_db
    original_runtime_settings_init = runtime_settings.init_runtime_settings_db
    original_runtime_settings_bootstrap = runtime_settings.bootstrap_runtime_settings_from_env
    original_runtime_secret_backfill = runtime_settings.backfill_runtime_secrets_from_env
    sys.modules.pop('server', None)
    memory_store.init_db = lambda: None
    active_conversation_documents.init_db = lambda: None
    conv_store.ensure_conv_dir = lambda: None
    conv_store.init_catalog_db = lambda: None
    conv_store.init_messages_db = lambda: None
    runtime_settings.init_runtime_settings_db = lambda: {
        'tables': (),
        'sql_path': 'test_bootstrap_disabled',
    }
    runtime_settings.bootstrap_runtime_settings_from_env = lambda: {
        'inserted_sections': (),
        'inserted_fields': (),
        'updated_sections': (),
        'updated_fields': (),
    }
    runtime_settings.backfill_runtime_secrets_from_env = lambda: {
        'updated_sections': (),
        'updated_fields': (),
    }
    try:
        return importlib.import_module('server')
    finally:
        runtime_settings.backfill_runtime_secrets_from_env = original_runtime_secret_backfill
        runtime_settings.bootstrap_runtime_settings_from_env = original_runtime_settings_bootstrap
        runtime_settings.init_runtime_settings_db = original_runtime_settings_init
        memory_store.init_db = original_init_db
        active_conversation_documents.init_db = original_active_documents_init_db
        conv_store.ensure_conv_dir = original_ensure_conv_dir
        conv_store.init_catalog_db = original_init_catalog_db
        conv_store.init_messages_db = original_init_messages_db
