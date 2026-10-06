"""Frozen M2 causal probe; intentionally red, excluded from discovery.

Run against the exact readonly M2 archive, never the M3 production checkout.
Explicit isolated socket required. No model/DAV live; providers are counted fakes.
The executed original used the same literal /proof/pg-socket before this guard.
"""
import os, threading, unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from core import conv_store, document_workshop_contexts as contexts, document_workshop_context_service as scope
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.support.server_chat_pipeline import patch_server_chat_pipeline
import psycopg
C="11111111-1111-4111-8111-111111111111"
F="22222222-2222-4222-8222-222222222222"
O="33333333-3333-4333-8333-333333333333"
T="44444444-4444-4444-8444-444444444444"
@unittest.skipUnless(os.environ.get('M3_BASELINE_PROBE_SOCKET') == '/proof/pg-socket', 'explicit isolated M2 baseline probe required')
class Causal(unittest.TestCase):
 def conn(self): return psycopg.connect(host="/proof/pg-socket",dbname="m1proof",user="m1proof")
 def setUp(self):
  self.server=load_server_module_for_tests()
  with self.conn() as c:
   c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
   c.execute("CREATE TABLE workspace_folders(id uuid PRIMARY KEY,deleted_at timestamptz); CREATE TABLE conversations(id uuid PRIMARY KEY,title text,created_at timestamptz,updated_at timestamptz,message_count integer,last_message_preview text,workspace_folder_id uuid,deleted_at timestamptz); CREATE TABLE conversation_messages(conversation_id uuid REFERENCES conversations(id),seq integer,role text,content text,timestamp timestamptz,summarized_by text,embedded boolean,meta jsonb,PRIMARY KEY(conversation_id,seq)); CREATE TABLE workspace_files(id uuid PRIMARY KEY, workspace_folder_id uuid,status text,content_kind text,media_kind text,source_extension text,deleted_at timestamptz); CREATE TABLE workspace_file_nextcloud_links(workspace_file_id uuid PRIMARY KEY,workspace_folder_id uuid,nextcloud_sync_state text,nextcloud_target_name text,nextcloud_document_ref text,nextcloud_relative_path text,nextcloud_scope_key text,nextcloud_file_id text,nextcloud_etag text);")
   c.execute("INSERT INTO workspace_folders VALUES (%s,NULL),(%s,NULL)",(F,O))
  self.patches=[patch.object(conv_store,"_db_conn",self.conn),patch.object(contexts,"_db_conn",self.conn)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
  v=conv_store.new_conversation("BACKEND SYSTEM PROMPT",conversation_id=C);v["workspace_folder_id"]=F
  self.assertTrue(conv_store.save_conversation(v).ok)
  contexts.init_db()
 def test_round_trip_does_not_restore_context_authority(self):
  r=contexts.create_context(conversation_id=C,workspace_folder_id=F)
  with self.conn() as c:c.execute("UPDATE conversations SET workspace_folder_id=%s WHERE id=%s",(O,C))
  with self.conn() as c:c.execute("UPDATE conversations SET workspace_folder_id=%s WHERE id=%s",(F,C))
  from types import SimpleNamespace
  p,s=scope.get_context(r["id"],store=contexts,conversations=conv_store,folders=SimpleNamespace(get_workspace_folder=lambda _:dict(id=F)),files=None)
  self.assertEqual(s,409)
 def simultaneous(self,same):
  arrived=threading.Event();release=threading.Event();calls=[]
  class Resp:
   def raise_for_status(self):pass
   def json(self):return {"choices":[{"message":{"content":"Synthetic final"}}]}
  def provider(*a,**k):
   if (k.get('json') or {}).get('model') != 'openrouter/runtime-main-model':return Resp()
   calls.append(1);arrived.set();self.assertTrue(release.wait(10));return Resp()
  real_load,real_save=conv_store.load_conversation,conv_store.save_conversation
  _,restore=patch_server_chat_pipeline(self.server,conversation=real_load(C,"BACKEND SYSTEM PROMPT"),requests_post=provider,existing_conversation=True,disable_chat_log_storage=True)
  self.addCleanup(restore)
  with patch.object(conv_store,"normalize_conversation_id",lambda v:str(v)),patch.object(conv_store,"load_conversation",real_load),patch.object(conv_store,"save_conversation",real_save):
   def post(t):
    with self.server.app.test_client() as client:return client.post("/api/chat",json=dict(message="Synthetic request",conversation_id=C,client_turn_id=t))
   with ThreadPoolExecutor(2) as pool:
    a=pool.submit(post,T);self.assertTrue(arrived.wait(10));b=pool.submit(post,T if same else O)
    try:
     # The second call must return while the first provider is still blocked.
     try: r=b.result(timeout=2)
     except TimeoutError:r=None
     self.assertIsNotNone(r,"concurrent request reached the provider instead of returning conflict")
     self.assertEqual(r.status_code,409);self.assertEqual(len(calls),1)
    finally:
     release.set();a.result();b.result();print("causal_main_provider_calls",len(calls))
 def test_same_turn_has_one_protected_start(self):self.simultaneous(True)
 def test_different_turn_same_conversation_has_one_protected_start(self):self.simultaneous(False)
if __name__=="__main__":unittest.main()
