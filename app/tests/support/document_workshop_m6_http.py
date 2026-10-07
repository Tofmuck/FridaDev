"""Owned M6 proof process. Real Flask/SQL/DAV and bounded synthetic providers.

Unrelated faculty services use the existing synthetic chat-pipeline boundaries;
their input captures prove non-contamination, not real model semantics.

Run exclusively in the network-none proof container with dedicated PG socket.
The control endpoints below belong to this fixture, never to the product.
"""
import copy
import hashlib
import json
import os
import signal
import threading
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, quote
from unittest.mock import patch
from uuid import uuid4

from flask import jsonify, request
from werkzeug.serving import make_server
from core import conv_store, document_workshop_contexts as contexts, token_utils
from core import workspace_file_selections, active_conversation_documents
from core import conversation_turn_claims as claims, document_workshop_actions as actions
from core import workspace_files, workspace_folders, workspace_document_adoption_store
from observability import main_payload_manifest
from core import document_workshop_execution_store as execution
from tests.integration.document_workshop.test_execution_postgresql import ExecutionPostgresqlTests
from tests.integration.document_workshop.test_claim_transport_postgresql import SyntheticResponse
from tests.support.server_chat_pipeline import patch_server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.unit.core.test_document_workshop_canonical_paths import canonical
from tests.unit.core.test_workspace_document_read_client_m2 import resource, multistatus, PREFIX

DOCUMENT_MARKER = 'M6DocumentContentSentinel'
RECEIPT_MARKER = 'M6_RECEIPT_METADATA_SENTINEL'
WORDS_MARKER = 'M6_REAL_DIALOGUE_SENTINEL'


def main(*,m7=False):
    if not os.environ.get('M5_PROOF_PG_SOCKET') or not os.environ.get('M6_PROOF_ROOT'):
        raise RuntimeError('dedicated proof environment required')
    stores=(conv_store,contexts,claims,actions,execution,workspace_files,workspace_folders,workspace_document_adoption_store,
            workspace_file_selections,active_conversation_documents)
    real_connections={module:module._db_conn for module in stores}
    real_roots={module:module._storage_root for module in (workspace_files,workspace_file_selections)}
    fixture = ExecutionPostgresqlTests('runTest')
    fixture.setUp()
    if m7:
        with fixture.conn() as db:
            db.execute(Path('/workspace/app/core/sql/document_workshop_update_m7.sql').read_text())
    stack = ExitStack()
    dav_release, dav_arrived = threading.Event(), threading.Event()
    inventory_release, inventory_arrived = threading.Event(), threading.Event()
    dav_release.set()
    inventory_release.set()
    state = dict(files={}, collections={'Documents'}, dav=[], providers=[], manifests=[], faculties=[],
                 copy_source=None, inventory_failure=False, block_inventory=False, next_path=f'Documents/Section/{RECEIPT_MARKER}.md',
                 operation='create', block_put=False, refuse_delete=False,
                 race_put=False,drop_put=False,lose_commit_reply=False,commit_reply_lost=False,
                 document_text=DOCUMENT_MARKER)
    conn = fixture.conn
    for module in (workspace_file_selections, active_conversation_documents):
        stack.enter_context(patch.object(module,'_db_conn',conn))
    conv_store.init_catalog_db()
    stack.enter_context(patch.object(workspace_file_selections,'_storage_root',lambda:fixture.env.root))
    active_conversation_documents.init_db()
    # Keep the production schema, but remove the fixture's prebuilt action.
    with conn() as db:
        db.execute('DELETE FROM document_actions; DELETE FROM document_revisions; DELETE FROM document_artifacts; '
                   'DELETE FROM conversation_turn_claims; DELETE FROM document_workshop_contexts; '
                   'DELETE FROM conversation_messages')
    conversation = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=fixture.conversation)
    conversation['workspace_folder_id'] = fixture.folder
    assert conv_store.save_conversation(conversation).ok
    other = str(uuid4())
    second = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=other)
    second['workspace_folder_id'] = fixture.folder
    assert conv_store.save_conversation(second).ok

    class DAV(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        do_PROPFIND = do_GET = do_MKCOL = do_PUT = do_DELETE = lambda self: self.reply()

        def reply(self):
            path = unquote(self.path.removeprefix(PREFIX))
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            state['dav'].append(dict(method=self.command, path=path, size=len(body),
                sha256=hashlib.sha256(body).hexdigest(), if_none=self.headers.get('If-None-Match'),
                if_match=self.headers.get('If-Match')))
            status, headers, content = 404, {}, b''
            files = state['files']
            if self.command == 'PROPFIND':
                if path in state['collections']:
                    nodes = [self.node(path)]
                    if self.headers.get('Depth') == '1':
                        for child in sorted(state['collections'] | set(files)):
                            if child != path and child.rsplit('/',1)[0] == path:
                                nodes.append(self.node(child))
                    status,content = 207,multistatus(*nodes)
                elif path in files: status,content = 207,multistatus(self.node(path))
                if m7 and self.headers.get('If-Match') and (path not in files or self.headers['If-Match']!=files[path]['etag']):
                    status,content=412,b''
            elif self.command == 'MKCOL':
                status = 405 if path in state['collections'] else 201
                state['collections'].add(path)
            elif self.command == 'PUT':
                if state['block_put']:
                    dav_arrived.set()
                    if not dav_release.wait(30): raise RuntimeError('causal proof gate timed out')
                if m7 and state['race_put']:
                    state['race_put']=False;files[path].update(content=b'M7ConcurrentSentinel\n',etag='"concurrent-v3"')
                if m7 and self.headers.get('If-Match'):
                    if path not in files or self.headers['If-Match']!=files[path]['etag']:status=412
                    else:
                        old=files[path];version=old.get('version',1)+1
                        old.update(content=body,etag='"m7-v'+str(version)+'"',version=version)
                        status,headers=204,{'ETag':old['etag']}
                elif path in files or self.headers.get('If-None-Match') != '*': status=412
                else:
                    files[path] = dict(content=body, etag='"created-'+str(len(files)+1)+'"', id=str(len(files)+10))
                    status,headers = 201,{'ETag':files[path]['etag']}
                if m7 and state['drop_put'] and status in (200,201,204):
                    import socket
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            elif self.command == 'GET' and path in files:
                status,content,headers = 200,files[path]['content'],{'ETag':files[path]['etag']}
                if m7 and self.headers.get('If-Match') and self.headers['If-Match']!=files[path]['etag']:
                    status,headers,content=412,{},b''
            elif self.command == 'DELETE' and path in files:
                if state['refuse_delete'] or self.headers.get('If-Match') != files[path]['etag']: status=412
                else: del files[path];status=204
            self.send_response(status)
            for key,value in headers.items(): self.send_header(key,value)
            self.send_header('Content-Length',str(len(content)));self.end_headers()
            try: self.wfile.write(content)
            except (BrokenPipeError,ConnectionResetError): pass

        def node(self,path):
            if path in state['collections']: return resource(path,file_id=str(1000+sorted(state['collections']).index(path)),href=PREFIX+quote(path,safe='/'))
            file = state['files'][path]
            return resource(path,collection=False,file_id=file['id'],etag=file['etag'],
                size=len(file['content']),media_type='text/markdown',href=PREFIX+quote(path,safe='/'))

    class Provider(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            payload = json.loads(raw)
            state['providers'].append(payload)
            proposal = dict(operation=state['operation'],format='markdown',relative_path=state['next_path'],
                source_file_ids=[state['copy_source']] if state['copy_source'] else [],limitations=[],canonical=canonical(state['document_text']))
            value = dict(schema_version=1,status='prepared',surface_text='M6 réelle proposition courte.',proposal=proposal)
            lines = [dict(model='openai/gpt-5.1',choices=[dict(index=0,delta=dict(content=json.dumps(value,ensure_ascii=False)),finish_reason=None)]),
                     dict(model='openai/gpt-5.1',choices=[dict(index=0,delta={},finish_reason='stop')])]
            wire=(''.join('data: '+json.dumps(line,ensure_ascii=False)+'\n\n' for line in lines)+'data: [DONE]\n\n').encode()
            self.send_response(200);self.send_header('Content-Type','text/event-stream')
            self.send_header('Content-Length',str(len(wire)));self.end_headers();self.wfile.write(wire)

    peers=[]
    for handler in (DAV,Provider):
        peer=ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=peer.serve_forever,daemon=True).start();peers.append(peer)
    dav,provider=peers
    password=fixture.env.root/'synthetic-password';password.write_text('synthetic-only')
    stack.enter_context(patch.dict(os.environ,dict(FRIDA_NEXTCLOUD_BASE_URL=f'http://127.0.0.1:{dav.server_port}',
        FRIDA_NEXTCLOUD_USERNAME='test',FRIDA_NEXTCLOUD_ROOT_NAME='Frida',FRIDA_NEXTCLOUD_APP_PASSWORD_FILE=str(password))))
    server=load_server_module_for_tests()
    if m7:
        actual_listing=workspace_files.list_workspace_files_strict
        def controlled_listing(folder_id):
            if m7 and state['block_inventory']:
                inventory_arrived.set()
                if not inventory_release.wait(30):raise RuntimeError('causal inventory gate timed out')
            if state['inventory_failure']:
                from core.workspace_files_store import WorkspaceFileListUnavailable
                raise WorkspaceFileListUnavailable('workspace_files_lookup_failed')
            return actual_listing(folder_id)
        stack.enter_context(patch.object(workspace_files,'list_workspace_files_strict',controlled_listing))
    # Exercise the runtime connection/bootstrap and common root resolution too.
    # Only the existing configuration values name the dedicated synthetic DB.
    stack.enter_context(patch.object(server.config,'FRIDA_MEMORY_DB_DSN',
        'host='+os.environ['M5_PROOF_PG_SOCKET']+' dbname=m1proof user=m1proof'))
    stack.enter_context(patch.object(server.config,'WORKSPACE_FILES_DIR',str(fixture.env.root)))
    for module,value in real_connections.items():stack.enter_context(patch.object(module,'_db_conn',value))
    for module,value in real_roots.items():stack.enter_context(patch.object(module,'_storage_root',value))
    if m7:
        actual_connection=execution._db_conn
        class CommitReply:
            def __init__(self):self.real=actual_connection();self.published=False
            def __enter__(self):return self
            def __getattr__(self,key):return getattr(self.real,key)
            def execute(self,query,args=()):
                if "SET state='succeeded',phase='complete'" in query:self.published=True
                return self.real.execute(query,args)
            def __exit__(self,kind,value,tb):
                if kind is None and self.published and state['lose_commit_reply'] and not state['commit_reply_lost']:
                    self.real.commit();self.real.close();state['commit_reply_lost']=True
                    raise OSError('synthetic lost commit reply')
                return self.real.__exit__(kind,value,tb)
        stack.enter_context(patch.object(execution,'_db_conn',lambda:CommitReply()))
    original={key:getattr(conv_store,key) for key in ('normalize_conversation_id','load_conversation','save_conversation','new_conversation','append_message','build_prompt_messages')}
    builder=server.llm.build_payload
    counter=server.token_utils.count_tokens
    def normal_provider(*args,**kwargs):
        payload=kwargs.get('json') or {}
        state['faculties'].append(dict(stage='provider',payload=copy.deepcopy(payload))) if payload.get('model')!='openai/gpt-5.1' else None
        if payload.get('model')=='openai/gpt-5.1':state['providers'].append(copy.deepcopy(payload))
        return SyntheticResponse()
    observed,restore=patch_server_chat_pipeline(server,conversation=conversation,requests_post=normal_provider,
        existing_conversation=True,disable_chat_log_storage=True,claim_store=claims,runtime_model='openai/gpt-5.1')
    stack.callback(restore)
    for key,value in original.items(): stack.enter_context(patch.object(conv_store,key,value))
    stack.enter_context(patch.object(server.llm,'build_payload',builder))
    stack.enter_context(patch.object(server.token_utils,'count_tokens',counter))
    stack.enter_context(patch.object(server.llm,'or_chat_completions_url',lambda:f'http://127.0.0.1:{provider.server_port}/v1/chat/completions'))
    stack.enter_context(patch.object(server.config,'CONTINUITY_CAPSULE_ENABLED',True))
    stack.enter_context(patch.object(server.config,'CONTINUITY_CAPSULE_TEXT','M6 fixed synthetic capsule'))
    # Observe both pre-composition and deferred seams without changing their data.
    def observe(obj,name,label):
        actual=getattr(obj,name)
        def wrapper(*args,**kwargs):
            captured=json.loads(json.dumps(dict(args=args,kwargs=kwargs),default=lambda value:dict(type=type(value).__name__)))
            result=actual(*args,**kwargs)
            captured['result']=json.loads(json.dumps(result,default=lambda value:dict(type=type(value).__name__)))
            state['faculties'].append(dict(stage=label,**captured))
            return result
        stack.enter_context(patch.object(obj,name,wrapper))
    for obj,name,label in ((server.summarizer,'maybe_summarize','summary'),
        (server.memory_store,'save_new_traces','memory_deferred'),
        (server.memory_store,'retrieve_for_arbiter_with_status','memory_input'),
        (server.identity,'build_identity_input','identity_input'),
        (server.chat_service,'_record_identity_entries_for_mode','identity_deferred'),
        (server.chat_service.biblio_chat_runtime,'run_biblio_chat_turn','biblio_input'),
        (server.chat_service.stimmung_agent,'build_affective_turn_signal','stimmung'),
        (server.chat_service,'_run_hermeneutic_node_insertion_point','faculties')):
        observe(obj,name,label)
    stack.enter_context(patch.object(main_payload_manifest,'emit_main_payload_manifest',lambda value,**_:state['manifests'].append(copy.deepcopy(value))))

    @server.app.get('/__m6/state')
    def proof_state():
        with conn() as db:
            counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in
                ('document_receipts','workspace_files','document_revision_renders','document_actions')}
            counts['confirmations']=db.execute("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'").fetchone()[0]
            origins=dict(db.execute('SELECT workspace_file_id::text,document_origin FROM workspace_file_nextcloud_links').fetchall())
            versions=[dict(file_id=str(row[0]),etag=row[1],remote_id=row[2],sha256=row[3]) for row in db.execute('SELECT workspace_file_id,nextcloud_etag,nextcloud_file_id,observed_sha256 FROM workspace_file_nextcloud_links').fetchall()]
        return jsonify(conversation=fixture.conversation,other_conversation=other,folder=fixture.folder,
            dav=state['dav'],counts=counts,origins=origins,versions=versions,put_arrived=dav_arrived.is_set(),
            remote={path:dict(size=len(file['content']),sha256=hashlib.sha256(file['content']).hexdigest()) for path,file in state['files'].items()},
            providers=state['providers'],manifests=state['manifests'],faculties=state['faculties'],commit_reply_lost=state['commit_reply_lost'],
            sent_estimates=[token_utils.estimate_tokens(value['messages'],value['model']) for value in state['providers']],
            memory_snapshots=observed['save_new_traces_calls'])

    @server.app.post('/__m6/control')
    def proof_control():
        data=request.get_json()
        for key in ('operation','next_path','copy_source','block_put','refuse_delete','race_put','drop_put','lose_commit_reply','document_text','inventory_failure'):
            if key in data:state[key]=data[key]
        if data.get('block_put'):dav_release.clear();dav_arrived.clear()
        if data.get('release_put'):dav_release.set()
        if m7 and 'block_inventory' in data:
            state['block_inventory']=data['block_inventory']
            if data['block_inventory']:inventory_release.clear();inventory_arrived.clear()
            else:inventory_release.set()
        if data.get('seed_external'):
            state['files']['Documents/External.md']=dict(content=b'Synthetic external source\n',etag='"external-v1"',id='7777')
        if data.get('change_external'):
            state['files']['Documents/External.md']=dict(content=b'Synthetic modified source\n',etag='"external-v2"',id='7777')
        if m7 and data.get('change_path'):
            path=data['change_path'];file=state['files'][path]
            file.update(content=b'M7OutsideSentinel\n',etag=data.get('etag','"outside"'))
            if data.get('replace_identity'):file['id']='999999'
        if m7 and data.get('remove_path'):state['files'].pop(data['remove_path'])
        if data.get('seed_collision'):
            state['files'][state['next_path']]=dict(content=b'Synthetic concurrent owner\n',etag='"concurrent-v1"',id='8888')
        if data.get('lose_lease'):
            with conn() as db:
                db.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE kind='confirmation' AND state='active'")
        if data.get('rollback_sql'):
            with conn() as db:
                if m7 and data.get('rollback_once'):
                    db.execute("CREATE SEQUENCE proof_fail_counter; CREATE FUNCTION proof_fail_render() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF nextval('proof_fail_counter')=1 THEN RAISE EXCEPTION 'synthetic'; END IF; RETURN NEW; END $$; CREATE TRIGGER proof_fail_render BEFORE INSERT ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION proof_fail_render()")
                else:db.execute("CREATE FUNCTION proof_fail_render() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER proof_fail_render BEFORE INSERT ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION proof_fail_render()")
        if data.get('restore_sql'):
            with conn() as db:db.execute('DROP TRIGGER proof_fail_render ON document_revision_renders; DROP FUNCTION proof_fail_render(); DROP SEQUENCE IF EXISTS proof_fail_counter')
        return jsonify(ok=True)

    @server.app.get('/__m6/await-put')
    def proof_arrival():
        return jsonify(arrived=dav_arrived.wait(5))

    if m7:
        @server.app.get('/__m7/await-inventory')
        def proof_inventory_arrival():
            return jsonify(arrived=inventory_arrived.wait(5))

    port=8767 if m7 else 8766
    http=make_server('127.0.0.1',port,server.app,threaded=True)
    def stop(*_):threading.Thread(target=http.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    Path(os.environ['M6_PROOF_ROOT'],'http-ready').write_text(str(port))
    try:http.serve_forever()
    finally:
        dav_release.set();inventory_release.set();http.server_close()
        for peer in peers:peer.shutdown();peer.server_close()
        stack.close();fixture.doCleanups()


if __name__=='__main__':main()
