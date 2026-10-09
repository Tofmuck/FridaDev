'use strict';
// Native browser -> actual Flask -> isolated PostgreSQL -> production DAV.
// No fetch, executor or receipt substitution. Fixture controls only local peers.
const test=require('node:test'),assert=require('node:assert/strict');
const {randomUUID,createHash}=require('node:crypto');
const {chromium}=require('playwright');
const {showFolder,openWorkshop}=require('./helpers/document_workshop_fixture.js');
const base=process.env.M7_HTTP_BASE;
const hash=text=>createHash('sha256').update(text).digest('hex');
const mutations=s=>s.dav.filter(d=>['PUT','DELETE','MKCOL'].includes(d.method));
const puts=s=>s.dav.filter(d=>d.method==='PUT');
async function session(run,{phone=false,theme='light'}={}) {
  assert.ok(base,'dedicated M7 native HTTP required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',hasTouch:phone,isMobile:phone,
      viewport:{width:phone?390:1280,height:phone?844:900}});
    page.setDefaultTimeout(10000);await page.addInitScript(value=>localStorage.setItem('frida.chat.theme',value),theme);
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const state=async()=> (await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    await control({operation:'create',copy_source:null,block_put:false,release_put:true,race_put:false,drop_put:false,lose_commit_reply:false,inventory_failure:false,block_inventory:false});
    await page.goto(base,{waitUntil:'domcontentloaded'});
    assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),theme);
    const initial=await state();
    await choose(page,initial,initial.conversation);
    await run(page,state,control,initial);assert.deepEqual(errors,[]);
  } finally {await browser.close();}
}
async function waitForNativeSelection(page,conversation) {
  // selectThread renders the selection and closes the phone menu after
  // loadThread. Observe that completion; a second close click races its exit.
  await page.waitForFunction(id=>{
    const selected=[...document.querySelectorAll('#threads li.active')]
      .some(row=>row.dataset.conversationId===id);
    if(!selected)return false;
    if(document.documentElement.dataset.presentationContext!=='phone')return true;
    const sidebar=document.querySelector('.sidebar'),backdrop=document.querySelector('#sidebarBackdrop');
    return !sidebar.classList.contains('open')&&sidebar.getAttribute('aria-hidden')==='true'
      &&document.querySelector('#btnMenu').getAttribute('aria-expanded')==='false'
      &&!backdrop.classList.contains('show')&&getComputedStyle(backdrop).display==='none'
      &&!sidebar.getAnimations().some(a=>a.transitionProperty==='transform'&&(a.playState==='running'||a.pending))
      &&sidebar.getBoundingClientRect().right<=0;
  },conversation);
}
async function choose(page,s,conversation) {
  await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${conversation}"]`).click();
  await waitForNativeSelection(page,conversation);
}
async function open(page) {
  if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
  await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
}
async function prepare(page,control,{path,fileId,text='M7RevisionSentinel',operation=null,expected='pending'}) {
  await open(page);
  if(fileId){await page.selectOption('#documentWorkshopTarget',fileId);await page.waitForFunction(id=>document.querySelector('#documentWorkshopTarget').value===id&&document.querySelector('#documentWorkshop').dataset.state==='editing',fileId);}
  await control({operation:operation||(fileId?'update':'create'),next_path:path,document_text:text});
  await page.fill('#message','M7RealWordsSentinel Modification explicitement demandée.');
  await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
  await page.waitForSelector(`#documentWorkshop .document-action-card[data-state="${expected}"]`);
  const card=page.locator('#documentWorkshop .document-action-card');
  const id=await card.getAttribute('data-action-id');
  // The card's identity comes from the native messages/context authority.
  const ctx=(await (await page.request.get(base+'/api/conversations/'+(await (await page.request.get(base+'/__m6/state')).json()).conversation+'/messages')).json()).messages.filter(m=>m.meta?.document_workshop).at(-1).meta.document_workshop;
  return (await (await page.request.get(base+'/api/document-workshop/actions/'+(id||ctx.action_id))).json()).action;
}
async function confirm(page,expected='succeeded') {
  await page.locator('#documentWorkshop [data-document-confirm]').click();
  await page.waitForSelector(`#documentWorkshop .document-action-card[data-state="${expected}"]`);
}
async function seed(page,state,control) {
  const path='Documents/M7-'+randomUUID()+'.md';
  const action=await prepare(page,control,{path,text:'M7OriginalSentinel'});await confirm(page);
  const published=(await (await page.request.get(base+'/api/document-workshop/actions/'+action.id)).json()).action;
  // Publication and the asynchronous shared-inventory GET are distinct. Observe
  // the owner's actual DOM publication before opening a new target context.
  await page.waitForFunction(path=>[...document.querySelectorAll('.workspace-folder-file-name')].some(node=>node.textContent===path),path);
  return {path,fileId:published.receipt.workspace_file_id,created:published,version:(await state()).versions.find(v=>v.file_id===published.receipt.workspace_file_id)};
}
async function getAction(page,id){return (await (await page.request.get(base+'/api/document-workshop/actions/'+id)).json()).action;}
async function replay(page,a) {
  return page.request.post(base+'/api/document-workshop/actions/'+a.id+'/confirm',{data:{context_id:a.context_id,conversation_id:a.conversation_id,workspace_folder_id:a.workspace_folder_id,revision_id:a.revision_id,request_id:randomUUID()}});
}

for(const phone of [false,true])for(const theme of ['light','dark'])
test(`M7 native stable Frida identity, two revisions, inventory and lanes: ${phone?'phone':'desktop'} ${theme}`,async()=>session(async(page,state,control,s)=>{
  const target=await seed(page,state,control),before=await state();
  const first=await prepare(page,control,{...target,text:'M7FirstSentinel'});
  assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').textContent(),'Modifier le fichier');
  assert.ok((await page.locator('#documentWorkshop .document-action-card').textContent()).includes(target.path));
  assert.equal(puts(await state()).length,puts(before).length);
  await page.locator('#documentWorkshop [data-document-confirm]').evaluate(button=>{button.click();button.click();});
  assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').count(),0);
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
  const done=await getAction(page,first.id),receipt=done.receipt,after=await state();
  assert.equal(receipt.workspace_file_id,target.fileId);assert.equal(receipt.nextcloud_file_id,target.version.remote_id);
  assert.equal(receipt.creation_author,'frida');assert.equal(receipt.revision_author,'frida');
  assert.equal(after.counts.workspace_files,before.counts.workspace_files);
  const put=puts(after).at(-1);assert.equal(put.if_match,target.version.etag);assert.equal(put.if_none,null);assert.equal(put.sha256,hash('M7FirstSentinel\n'));
  assert.equal(mutations(after).length,mutations(before).length+1);
  assert.equal((await replay(page,first)).status(),200);assert.equal(puts(await state()).length,puts(after).length);
  await prepare(page,control,{...target,text:'M7SecondSentinel'});await confirm(page);
  assert.deepEqual((await getAction(page,first.id)).receipt,receipt);
  assert.equal((await getAction(page,target.created.id)).state,'succeeded');
  assert.equal((await (await page.request.get(base+receipt.product_link)).body()).toString(),'M7SecondSentinel\n');
  const inventory=(await (await page.request.get(base+'/api/workspace-folders/'+s.folder+'/files')).json()).items;
  assert.equal(inventory.filter(f=>f.id===target.fileId).length,1);assert.equal(inventory.find(f=>f.id===target.fileId).document_relative_path,target.path);
  await page.click('#documentWorkshopExit');await choose(page,s,s.other_conversation);
  assert.deepEqual((await (await page.request.get(base+'/api/conversations/'+s.other_conversation+'/workspace-file-selections')).json()).items,[]);
  await choose(page,s,s.conversation);await page.reload();await choose(page,s,s.conversation);
  await page.waitForSelector('#log [data-document-receipt-link]');const rehydrated=await state();
  assert.equal(puts(rehydrated).length,puts(after).length+1);
  const response=await page.request.post(base+'/api/chat',{data:{conversation_id:s.conversation,client_turn_id:randomUUID(),message:'M7RealWordsSentinel trace du dernier update',stream:false}});
  assert.equal(response.status(),200);let observed=await state(),payload=observed.providers.at(-1),manifest=observed.manifests.at(-1);
  assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
  const lane=manifest.messages.find(m=>m.logical_roles.includes('document_receipt_lane'));
  assert.ok(payload.messages[lane.index].content.includes('update'));assert.ok(payload.messages[lane.index].content.includes(target.path));
  assert.equal(JSON.stringify(payload).includes('M7SecondSentinel'),false);
  // A new preparation without a target reads only the latest receipt metadata.
  await prepare(page,control,{path:'Documents/Unconfirmed-'+randomUUID()+'.md'});
  observed=await state();payload=observed.providers.at(-1);manifest=observed.manifests.at(-1);
  assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
  assert.equal(manifest.budgets.prompt.estimated_prompt_tokens,observed.sent_estimates.at(-1));assert.ok(observed.sent_estimates.at(-1)+24000<=400000);
  assert.equal(JSON.stringify(payload).includes('M7SecondSentinel'),false);
  for(const capture of [...observed.faculties,...observed.memory_snapshots]) {
    const text=JSON.stringify(capture);for(const marker of ['M7OriginalSentinel','M7FirstSentinel','M7SecondSentinel',target.path])assert.equal(text.includes(marker),false);
  }
  await page.locator('#documentWorkshop [data-document-cancel]').click();
}, {phone,theme}));

test('M7 native explicit external adoption and update preserve external creation authorship',async()=>session(async(page,state,control,s)=>{
  await control({seed_external:true});await open(page);await page.click('#documentWorkshopBrowse');
  await page.locator('#documentRemoteList > *').filter({hasText:'External.md'}).getByRole('button',{name:'Adopter External.md',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
  const external=(await (await page.request.get(base+'/api/workspace-folders/'+s.folder+'/files')).json()).items.find(f=>f.document_relative_path==='Documents/External.md');
  const before=await state(),a=await prepare(page,control,{path:'Documents/External.md',fileId:external.id,text:'M7ExternalRevisionSentinel'});await confirm(page);
  const receipt=(await getAction(page,a.id)).receipt,after=await state();
  assert.equal(receipt.workspace_file_id,external.id);assert.equal(receipt.nextcloud_file_id,'7777');assert.equal(receipt.creation_author,'external');assert.equal(receipt.revision_author,'frida');
  assert.equal(after.origins[external.id],'external');assert.equal(after.counts.workspace_files,before.counts.workspace_files);
  assert.equal(mutations(after).length,mutations(before).length+1);
}));

test('M7 native changed-before-click and changed-after-read conflicts preserve competing bytes',async()=>session(async(page,state,control)=>{
  const target=await seed(page,state,control),a=await prepare(page,control,target),before=await state();
  await control({change_path:target.path});await confirm(page,'conflict');
  assert.equal(puts(await state()).length,puts(before).length);assert.equal((await getAction(page,a.id)).state,'conflict');
  const race=await seed(page,state,control),prepared=await prepare(page,control,race),prior=await state();
  await control({race_put:true});await confirm(page,'conflict');const after=await state();
  assert.equal(puts(after).length,puts(prior).length+1);assert.equal(puts(after).at(-1).if_match,race.version.etag);
  assert.equal(after.remote[race.path].sha256,hash('M7ConcurrentSentinel\n'));assert.equal((await getAction(page,prepared.id)).state,'conflict');
  assert.equal(mutations(after).length,mutations(prior).length+1);
}));

test('M7 native SQL rollback repair, lost commit reply and lost DAV reply never replay writes',async()=>session(async(page,state,control)=>{
  const target=await seed(page,state,control),a=await prepare(page,control,target),before=await state();
  await control({rollback_sql:true,rollback_once:true});
  const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/confirm'));
  await page.locator('#documentWorkshop [data-document-confirm]').click();assert.equal((await response).status(),503);
  // The first native GET then repairs SQL; the sequence survives the true
  // rollback, so the synthetic fault affects precisely the publication attempt.
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');await control({restore_sql:true});
  const repaired=await state();assert.equal(puts(repaired).length,puts(before).length+1);assert.equal(mutations(repaired).length,mutations(before).length+1);
  assert.equal((await getAction(page,a.id)).receipt.workspace_file_id,target.fileId);
  const next=await seed(page,state,control),commit=await prepare(page,control,next),prior=await state();
  await control({lose_commit_reply:true});await confirm(page);const committed=await state();
  assert.equal(committed.commit_reply_lost,true,'commit reply fault was not reached');
  assert.equal(puts(committed).length,puts(prior).length+1);assert.equal((await getAction(page,commit.id)).state,'succeeded');
  await control({lose_commit_reply:false});const lost=await seed(page,state,control),unknown=await prepare(page,control,lost),previous=await state();
  await control({drop_put:true});await confirm(page,'remote_uncertain');await control({drop_put:false});
  await page.reload();await choose(page,await state(),(await state()).conversation);
  assert.equal((await getAction(page,unknown.id)).state,'remote_uncertain');assert.equal((await replay(page,unknown)).status(),503);
  assert.equal(puts(await state()).length,puts(previous).length+1);assert.equal((await state()).counts.document_receipts,previous.counts.document_receipts);
}));

test('M7 native navigation, duplicate confirmation and lease loss fence late update without compensation',async()=>session(async(page,state,control,s)=>{
  const target=await seed(page,state,control),a=await prepare(page,control,target),before=await state();
  await control({block_put:true});const finished=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/confirm'));
  await page.locator('#documentWorkshop [data-document-confirm]').click();assert.equal((await (await page.request.get(base+'/__m6/await-put')).json()).arrived,true);
  const duplicate=await replay(page,a);assert.equal(duplicate.status(),200);assert.equal((await duplicate.json()).action.state,'executing');
  await control({lose_lease:true});await page.click('#documentWorkshopReload');await page.waitForSelector('#documentWorkshop .document-action-card[data-state="remote_uncertain"]');
  await page.click('#documentWorkshopExit');await choose(page,s,s.other_conversation);
  await control({release_put:true,block_put:false});await finished;
  const after=await state();assert.equal(puts(after).length,puts(before).length+1);assert.equal(mutations(after).length,mutations(before).length+1);
  assert.equal(after.counts.document_receipts,before.counts.document_receipts);assert.equal(await page.locator('#log [data-document-receipt-link]').count(),0);
  assert.equal((await getAction(page,a.id)).state,'remote_uncertain');assert.equal((await replay(page,a)).status(),503);
  assert.equal(puts(await state()).length,puts(after).length);
}));

test('M7 native explicit read source also selected as target keeps one fresh observation and prepares update',async()=>session(async(page,state,control,s)=>{
  const target=await seed(page,state,control);
  const selected=await page.request.post(base+'/api/conversations/'+s.conversation+'/workspace-file-selections',{data:{file_id:target.fileId}});assert.equal(selected.status(),201);
  try {
    await page.reload();await choose(page,s,s.conversation);
    const a=await prepare(page,control,target);await confirm(page);
    assert.equal((await getAction(page,a.id)).receipt.workspace_file_id,target.fileId);
  } finally {await page.request.delete(base+'/api/conversations/'+s.conversation+'/workspace-file-selections/'+target.fileId);}
}));

test('M7 native read source without explicit target refuses update with zero write',async()=>session(async(page,state,control,s)=>{
  const target=await seed(page,state,control),before=await state();
  assert.equal((await page.request.post(base+'/api/conversations/'+s.conversation+'/workspace-file-selections',{data:{file_id:target.fileId}})).status(),201);
  try {
    await page.reload();await choose(page,s,s.conversation);
    const a=await prepare(page,control,{path:target.path,operation:'update',expected:'failed'});
    assert.equal(a.state,'failed');assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').count(),0);
    assert.equal(puts(await state()).length,puts(before).length);
  } finally {await page.request.delete(base+'/api/conversations/'+s.conversation+'/workspace-file-selections/'+target.fileId);}
}));

test('M7 native shared inventory refresh failure preserves durable update and refresh never posts again',async()=>session(async(page,state,control,s)=>{
  const target=await seed(page,state,control),a=await prepare(page,control,target),before=await state();
  const confirmationRequests=[];page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/confirm'))confirmationRequests.push(r.url());});
  await control({inventory_failure:true});await confirm(page);
  await page.waitForFunction(()=>document.querySelector('#documentWorkshop .document-action-card').textContent.includes('Inventaire non actualisé'));
  assert.equal((await getAction(page,a.id)).state,'succeeded');await control({inventory_failure:false});
  await page.reload();await choose(page,s,s.conversation);await page.waitForSelector('#log [data-document-receipt-link]');
  assert.equal(confirmationRequests.length,1);assert.equal(puts(await state()).length,puts(before).length+1);
}));

test('M7 native successful update closes stale target authority and preserves draft without another POST',async()=>session(async(page,state,control)=>{
  const target=await seed(page,state,control);await prepare(page,control,target);await confirm(page);
  const requests=[];page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/chat'))requests.push(r.url());});
  await page.fill('#message','M7NewRequestDraft');await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
  await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('nouvelle demande'));
  assert.equal(requests.length,0);assert.equal(await page.locator('#message').inputValue(),'M7NewRequestDraft');
}));

test('M7 native delayed shared inventory populates reopened target selector without implicit selection',async()=>session(async(page,state,control)=>{
  const path='Documents/M7-Delayed-'+randomUUID()+'.md';
  const a=await prepare(page,control,{path,text:'M7DelayedOriginal'});
  await control({block_inventory:true});await confirm(page);
  assert.equal((await (await page.request.get(base+'/__m7/await-inventory')).json()).arrived,true);
  const done=await getAction(page,a.id),fileId=done.receipt.workspace_file_id;
  await open(page);
  assert.equal(await page.locator(`#documentWorkshopTarget option[value="${fileId}"]`).count(),0);
  assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');
  await control({block_inventory:false});
  await page.locator(`#documentWorkshopTarget option[value="${fileId}"]`).waitFor({state:'attached'});
  assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');
  const update=await prepare(page,control,{path,fileId});await confirm(page);
  assert.equal((await getAction(page,update.id)).receipt.workspace_file_id,fileId);
}));
