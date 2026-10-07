'use strict';
// Native browser fetch -> mounted Flask -> dedicated PostgreSQL -> production DAV.
// No route/fetch substitution. The __m6 endpoints control only the synthetic peers.
const test=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {showFolder,closeSidebar,openWorkshop}=require('./helpers/document_workshop_fixture.js');
const base=process.env.M6_HTTP_BASE;
const DOC='M6DocumentContentSentinel', RECEIPT='M6_RECEIPT_METADATA_SENTINEL', WORDS='M6_REAL_DIALOGUE_SENTINEL';

async function session(run) {
  assert.ok(base,'owned isolated Flask server required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR'});page.setDefaultTimeout(10000);
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const state=async()=> (await page.request.get(base+'/__m6/state')).json();
    const control=async value=> {const r=await page.request.post(base+'/__m6/control',{data:value});assert.equal(r.status(),200);};
    await page.goto(base,{waitUntil:'domcontentloaded'});
    await run(page,state,control);
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
}
async function choose(page,folder,conversation) {
  await showFolder(page,folder);
  await page.locator(`[data-conversation-id="${conversation}"]`).click();
  await closeSidebar(page);
}
async function prepare(page,text) {
  await openWorkshop(page);
  await page.waitForFunction(()=>document.querySelector('#documentWorkshop')?.dataset.state==='editing'||document.querySelector('#documentWorkshopStatus')?.textContent.includes('Préparation'));
  await page.fill('#message',text);await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
}
function putCount(state){return state.dav.filter(item=>item.method==='PUT').length;}
function assertReceiptPayload(payload,manifest){
  assert.equal(manifest.messages.length,payload.messages.length);
  for(const entry of manifest.messages){
    const message=payload.messages[entry.index];
    assert.equal(entry.provider_role,message.role);
    assert.equal(entry.content_chars,Array.from(message.content).length);
  }
  const receipts=manifest.messages.filter(m=>m.logical_roles.includes('document_receipt_lane'));
  assert.equal(receipts.length,1);
  const documentary=payload.max_tokens===24000;
  assert.equal(receipts[0].index,payload.messages.length-(documentary?3:2));
  assert.equal(receipts[0].origin,'core.document_workshop_receipts');
  const capsuleIndex=receipts[0].index+1;
  assert.ok(manifest.messages[capsuleIndex].logical_roles.includes('continuity_capsule'));
  assert.ok(payload.messages[capsuleIndex].content.includes('M6 fixed synthetic capsule'));
  if(documentary)assert.ok(payload.messages.at(-1).content.startsWith('Return one complete JSON envelope'));
}

test('M6 native HTTP create, nested copy, lost response, shared inventory, durable links and both next-turn lanes',async()=>session(async(page,state,control)=>{
  const initial=await state();await choose(page,initial.folder,initial.conversation);
  await prepare(page,WORDS+' Crée le Markdown au chemin proposé.');
  let s=await state();assert.equal(putCount(s),0);assert.equal(s.counts.workspace_files,0);
  assert.equal(s.providers.length,1);assert.equal(s.manifests.at(-1).lane_statuses.document_receipt_lane.injected_count,0);
  assert.ok((await page.locator('#documentWorkshop .document-action-card').textContent()).includes('Documents/Section'));
  const preparedContext=(await (await page.request.get(base+'/api/conversations/'+initial.conversation+'/messages')).json()).messages.find(m=>m.meta?.document_workshop)?.meta.document_workshop;
  const preparedId=preparedContext.action_id;
  await control({block_put:true});
  const firstButton=page.locator('#documentWorkshop [data-document-confirm]');
  await firstButton.evaluate(button=>{window.__m6Detached=button;button.click();button.click();});
  assert.equal((await (await page.request.get(base+'/__m6/await-put')).json()).arrived,true);
  const executing=(await (await page.request.get(base+'/api/document-workshop/actions/'+preparedId)).json()).action;
  const duplicate=await page.request.post(base+'/api/document-workshop/actions/'+preparedId+'/confirm',{data:{context_id:executing.context_id,conversation_id:executing.conversation_id,workspace_folder_id:executing.workspace_folder_id,revision_id:executing.revision_id,request_id:require('node:crypto').randomUUID()}});
  assert.equal(duplicate.status(),200);assert.equal((await duplicate.json()).action.state,'executing');
  assert.equal((await state()).counts.confirmations,1);
  assert.equal(await page.locator('[data-document-confirm]').count(),0);
  // Abort the first browser response through navigation, while the real server
  // remains executing; reopening must observe the same action by GET only.
  await page.reload();await choose(page,initial.folder,initial.conversation);
  await page.waitForSelector('#log .document-action-card[data-state="executing"]');
  await control({release_put:true,block_put:false});
  await page.waitForSelector('#log [data-document-receipt-link]');
  s=await state();assert.equal(putCount(s),1);assert.equal(s.counts.document_receipts,1);
  assert.equal(s.providers.length,1,'confirmation must never call a model');
  const href=await page.locator('#log [data-document-receipt-link]').getAttribute('href');
  const bytes=await (await page.request.get(base+href)).body();assert.equal(bytes.toString(),DOC+'\n');
  const put=s.dav.find(item=>item.method==='PUT');assert.equal(put.if_none,'*');assert.equal(put.size,bytes.length);
  const actionId=(await (await page.request.get(base+'/api/conversations/'+initial.conversation+'/messages')).json()).messages.find(m=>m.meta?.document_workshop)?.meta.document_workshop.action_id;
  const action=(await (await page.request.get(base+'/api/document-workshop/actions/'+actionId)).json()).action;
  const replay=await page.request.post(base+'/api/document-workshop/actions/'+actionId+'/confirm',{data:{context_id:action.context_id,conversation_id:action.conversation_id,workspace_folder_id:action.workspace_folder_id,revision_id:action.revision_id,request_id:require('node:crypto').randomUUID()}});
  assert.equal(replay.status(),200);assert.equal(putCount(await state()),1);
  if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
  await choose(page,initial.folder,initial.other_conversation);
  const inventory=(await (await page.request.get(base+'/api/workspace-folders/'+initial.folder+'/files')).json()).items;
  assert.equal(inventory.length,1);
  const selections=await (await page.request.get(base+'/api/conversations/'+initial.other_conversation+'/workspace-file-selections')).json();
  assert.deepEqual(selections.items,[]);assert.equal(await page.locator('#log [data-document-receipt-link]').count(),0);
  await choose(page,initial.folder,initial.conversation);
  await page.waitForSelector('#log [data-document-receipt-link]');
  // The normal route uses the same lane, with no selected source.
  const normal=await page.request.post(base+'/api/chat',{data:{conversation_id:initial.conversation,client_turn_id:require('node:crypto').randomUUID(),message:WORDS+' Quelle est la trace de cette création ?',stream:false}});
  assert.equal(normal.status(),200,await normal.text());
  s=await state();let payload=s.providers.at(-1),manifest=s.manifests.at(-1);
  assert.ok(JSON.stringify(payload.messages).includes(RECEIPT));assert.equal(JSON.stringify(payload.messages).includes(DOC),false);
  assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
  assert.equal(manifest.lane_conflicts.message_lane_status_mismatch_count,0);
  assert.ok(manifest.messages.find(m=>m.logical_roles.includes('document_receipt_lane')));
  assertReceiptPayload(payload,manifest);
  // New documentary preparation, without mobilization: latest metadata only.
  await control({next_path:'Documents/Second.md'});
  await prepare(page,WORDS+' Prépare un autre document, sans relire le premier.');
  s=await state();payload=s.providers.at(-1);manifest=s.manifests.at(-1);
  assert.ok(JSON.stringify(payload.messages).includes(RECEIPT));assert.equal(JSON.stringify(payload.messages).includes(DOC),false);
  assert.equal(payload.max_tokens,24000);assert.equal(manifest.lane_statuses.document_lane.injected_count,0);
  assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
  assert.ok(manifest.budgets.prompt.estimated_prompt_tokens+24000<=400000);
  assert.equal(manifest.budgets.prompt.estimated_prompt_tokens,s.sent_estimates.at(-1));
  assertReceiptPayload(payload,manifest);
  for(const capture of [...s.faculties,...s.memory_snapshots]){
    const text=JSON.stringify(capture);assert.equal(text.includes(DOC),false);assert.equal(text.includes(RECEIPT),false);
  }
  assert.ok(JSON.stringify(s.memory_snapshots).includes(WORDS));
  for(const stage of ['summary','memory_input','memory_deferred','identity_input','identity_deferred','stimmung','biblio_input','faculties']){
    assert.ok(s.faculties.some(capture=>capture.stage===stage),'missing observed boundary '+stage);
  }
  for(const stage of ['summary','memory_input','memory_deferred','stimmung','biblio_input','faculties']){
    assert.ok(JSON.stringify(s.faculties.filter(capture=>capture.stage===stage)).includes(WORDS),'legitimate words lost at '+stage);
  }
  // Cancel this unconfirmed preparation, then make an explicit copy with one
  // source selected through the actual existing selection endpoint.
  await page.locator('#documentWorkshop [data-document-cancel]').click();
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="cancelled"]');
  await page.click('#documentWorkshopExit');
  const fileId=action.receipt.workspace_file_id;
  const select=await page.request.post(base+'/api/conversations/'+initial.conversation+'/workspace-file-selections',{data:{file_id:fileId}});
  assert.equal(select.status(),201,await select.text());
  await page.reload();await choose(page,initial.folder,initial.conversation);
  await control({operation:'copy',copy_source:fileId,next_path:'Documents/Section/Copy.md'});
  await prepare(page,WORDS+' Copie explicitement le document sélectionné vers Documents/Section/Copy.md.');
  const before=await state();assert.equal(putCount(before),1);
  await page.locator('#documentWorkshop [data-document-confirm]').click();
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
  s=await state();assert.equal(putCount(s),2);assert.equal(s.counts.document_receipts,2);assert.equal(s.counts.workspace_files,2);
  for(const capture of [...s.faculties,...s.memory_snapshots])assert.equal(JSON.stringify(capture).includes(DOC),false);
  const copyHref=await page.locator('#documentWorkshop [data-document-receipt-link]').getAttribute('href');
  assert.notEqual(copyHref,href);assert.equal((await (await page.request.get(base+copyHref)).body()).toString(),DOC+'\n');
  assert.ok(s.dav.some(d=>d.method==='GET'&&d.path.includes(RECEIPT)),'explicit copy source must be read fresh');
  await page.click('#documentWorkshopExit');await page.reload();await choose(page,initial.folder,initial.conversation);
  await page.waitForFunction(()=>document.querySelectorAll('#log [data-document-receipt-link]').length===2);
  assert.equal(putCount(await state()),2);
  // Two durable receipts exist, but extra history is explicitly zero.
  await page.request.delete(base+'/api/conversations/'+initial.conversation+'/workspace-file-selections/'+fileId);
  const next=await page.request.post(base+'/api/chat',{data:{conversation_id:initial.conversation,client_turn_id:require('node:crypto').randomUUID(),message:WORDS+' Reprends la conversation.',stream:false}});
  assert.equal(next.status(),200);s=await state();manifest=s.manifests.at(-1);payload=s.providers.at(-1);
  const entries=manifest.messages.filter(m=>m.logical_roles.includes('document_receipt_lane'));
  assert.equal(entries.length,1);assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
  const latest=payload.messages[entries[0].index].content;
  assert.ok(latest.includes('Documents/Section/Copy.md'));assert.equal(latest.includes(RECEIPT),false);
}));

test('M6 native HTTP explicit adoption and copy preserve external origin; changed source prevents a later copy',async()=>session(async(page,state,control)=>{
  const initial=await state();await choose(page,initial.folder,initial.other_conversation);
  await control({seed_external:true,operation:'copy',next_path:'Documents/Section/ExternalCopy.md'});
  if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
  await openWorkshop(page);await page.click('#documentWorkshopBrowse');
  const row=page.locator('#documentRemoteList > *').filter({hasText:'External.md'});
  await row.getByRole('button',{name:'Adopter External.md',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
  const inventory=(await (await page.request.get(base+'/api/workspace-folders/'+initial.folder+'/files')).json()).items;
  const external=inventory.find(f=>f.document_relative_path==='Documents/External.md');assert.equal(external.document_origin,'external');
  const before=await state();await page.click('#documentWorkshopExit');
  const select=await page.request.post(base+'/api/conversations/'+initial.other_conversation+'/workspace-file-selections',{data:{file_id:external.id}});assert.equal(select.status(),201);
  await control({copy_source:external.id});await page.reload();await choose(page,initial.folder,initial.other_conversation);
  await prepare(page,WORDS+' Copie explicitement la source adoptée vers la destination proposée.');
  await page.locator('#documentWorkshop [data-document-confirm]').click();
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
  const after=await state();assert.equal(putCount(after),putCount(before)+1);
  const files=(await (await page.request.get(base+'/api/workspace-folders/'+initial.folder+'/files')).json()).items;
  assert.equal(files.find(f=>f.id===external.id).document_origin,'external');
  const copy=files.find(f=>f.document_relative_path==='Documents/Section/ExternalCopy.md');assert.equal(after.origins[copy.id],'frida');assert.notEqual(copy.id,external.id);
  await page.click('#documentWorkshopExit');await control({next_path:'Documents/ChangedCopy.md'});
  await prepare(page,WORDS+' Copie de nouveau explicitement la même source.');await control({change_external:true});
  await page.locator('#documentWorkshop [data-document-confirm]').click();
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="invalidated"]');
  assert.equal(putCount(await state()),putCount(after));assert.equal(await page.locator('#documentWorkshop [data-document-receipt-link]').count(),0);
}));

test('M6 native HTTP collision after preflight preserves concurrent bytes without receipt or rename',async()=>session(async(page,state,control)=>{
  const initial=await state();await choose(page,initial.folder,initial.other_conversation);
  await page.request.delete(base+'/api/conversations/'+initial.other_conversation+'/workspace-file-selections/'+(await (await page.request.get(base+'/api/conversations/'+initial.other_conversation+'/workspace-file-selections')).json()).items[0].workspace_file_id);
  if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
  await control({operation:'create',copy_source:null,next_path:'Documents/Collision.md',block_put:true});
  await page.reload();await choose(page,initial.folder,initial.other_conversation);await prepare(page,WORDS+' Crée ce Markdown après confirmation.');
  const before=await state();await page.locator('#documentWorkshop [data-document-confirm]').click();
  assert.equal((await (await page.request.get(base+'/__m6/await-put')).json()).arrived,true);
  await control({seed_collision:true,release_put:true,block_put:false});
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="failed"]');
  const after=await state();assert.equal(putCount(after),putCount(before)+1);assert.equal(after.counts.document_receipts,before.counts.document_receipts);
  assert.equal(await page.locator('#documentWorkshop [data-document-receipt-link]').count(),0);
  assert.equal(after.dav.filter(d=>d.method==='PUT'&&d.path==='Documents/Collision.md').length,1);
  assert.equal(after.remote['Documents/Collision.md'].sha256,require('node:crypto').createHash('sha256').update('Synthetic concurrent owner\n').digest('hex'));
}));

test('M6 native HTTP lost lease during PUT fences late publication and GET never replays',async()=>session(async(page,state,control)=>{
  const initial=await state();await choose(page,initial.folder,initial.other_conversation);
  if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
  await control({operation:'create',copy_source:null,next_path:'Documents/Lease.md',block_put:true});
  await prepare(page,WORDS+' Crée ce dernier Markdown de preuve.');
  const before=await state();
  const terminalResponse=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/confirm'));
  await page.locator('#documentWorkshop [data-document-confirm]').click();
  assert.equal((await (await page.request.get(base+'/__m6/await-put')).json()).arrived,true);
  await control({lose_lease:true});await page.click('#documentWorkshopReload');
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="remote_uncertain"]');
  await control({release_put:true,block_put:false});
  await terminalResponse;
  const after=await state();assert.equal(after.counts.document_receipts,before.counts.document_receipts);assert.equal(putCount(after),putCount(before)+1);
  assert.equal(await page.locator('#documentWorkshop [data-document-receipt-link]').count(),0);
  await page.reload();await choose(page,initial.folder,initial.other_conversation);
  assert.equal(putCount(await state()),putCount(after));
}));

test('M6 native HTTP DAV success then real SQL rollback and refused compensation never yields receipt or executable link',async()=>session(async(page,state,control)=>{
  const initial=await state();await choose(page,initial.folder,initial.other_conversation);
  await control({operation:'create',copy_source:null,next_path:'Documents/Failure.md',rollback_sql:true,refuse_delete:true});
  try {
    await prepare(page,WORDS+' Crée ce Markdown de preuve.');
    const before=await state();await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="remote_uncertain"]');
    const after=await state();assert.equal(putCount(after),putCount(before)+1);
    assert.equal(after.counts.document_receipts,before.counts.document_receipts);
    assert.equal(after.counts.workspace_files,before.counts.workspace_files);
    assert.equal(await page.locator('#documentWorkshop [data-document-receipt-link]').count(),0);
    assert.ok(after.dav.some(item=>item.method==='DELETE'&&item.if_match));
    await page.reload();await choose(page,initial.folder,initial.other_conversation);
    await page.waitForSelector('#log .document-action-card[data-state="remote_uncertain"]');
    assert.equal(putCount(await state()),putCount(after));
  } finally {await control({restore_sql:true,refuse_delete:false});}
}));
