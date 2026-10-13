'use strict';
// Native browser -> production composition -> isolated SQL/DAV/Writer.
// No fetch replacement; only the provider/faculties are synthetic peers.
const test=require('node:test'),assert=require('node:assert/strict');
const {randomUUID,createHash}=require('node:crypto');
const {chromium}=require('playwright');
const {showFolder,openWorkshop}=require('./helpers/document_workshop_fixture.js');
const base=process.env.M9A_HTTP_BASE;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');

test('M9-A native DOCX card confirmation download reload and metadata continuity',async()=>{
  assert.ok(base,'dedicated native HTTP fixture required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});
    page.setDefaultTimeout(15000);
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const state=async()=>(await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    const choose=async s=>{await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${s.conversation}"]`).click();
      await page.waitForFunction(id=>document.querySelector('#threads li.active')?.dataset.conversationId===id,s.conversation);};
    await page.goto(base,{waitUntil:'domcontentloaded'});assert.equal(new URL(page.url()).origin,base);
    assert.ok(await page.title());await choose(await state());
    const originalText='M9BrowserSourceSentinel',updatedText='M9BrowserUpdatedSentinel';
    let created;
    for(const operation of ['create','copy','update']) {
      if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
      await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
      assert.match(await page.locator('#documentWorkshopStatus').textContent(),/Markdown.*DOCX/);
      assert.doesNotMatch(await page.locator('#documentWorkshopStatus').textContent(),/PDF|M9-B/);
      if(operation==='copy') {
        const s=await state();assert.equal((await page.request.post(base+'/api/conversations/'+s.conversation+'/workspace-file-selections',{data:{file_id:created.workspace_file_id}})).status(),201);
        await page.reload();await choose(s);await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
      }
      if(operation==='update') {
        const s=await state();await page.request.delete(base+'/api/conversations/'+s.conversation+'/workspace-file-selections/'+created.workspace_file_id);
        await page.selectOption('#documentWorkshopTarget',created.workspace_file_id);
        await page.waitForFunction(id=>document.querySelector('#documentWorkshopTarget').value===id&&document.querySelector('#documentWorkshop').dataset.state==='editing',created.workspace_file_id);
      }
      const path=operation==='create'?'Documents/Browser-'+randomUUID()+'.docx':operation==='copy'?'Documents/Copy-'+randomUUID()+'.docx':created.relative_path;
      await control({operation,next_path:path,copy_source:operation==='copy'?created.workspace_file_id:null,document_text:operation==='update'?updatedText:originalText,document_format:'docx'});
      await page.fill('#message','Demande synthétique explicite '+operation+' du DOCX.');
      const before=await state();await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
      assert.equal((await state()).dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
      assert.match(await page.locator('#documentWorkshop .document-action-card').textContent(),/docx/);
      await page.locator('#documentWorkshop [data-document-confirm]').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
      const s=await state();
      const messages=(await (await page.request.get(base+'/api/conversations/'+s.conversation+'/messages')).json()).messages;
      const id=messages.filter(m=>m.meta?.document_workshop).at(-1).meta.document_workshop.action_id;
      const action=(await (await page.request.get(base+'/api/document-workshop/actions/'+id)).json()).action;
      const receipt=action.receipt;assert.equal(receipt.format,'docx');
      if(operation==='create')created=receipt;
      if(operation==='update')assert.equal(receipt.workspace_file_id,created.workspace_file_id);
      const link=page.locator('#documentWorkshop [data-document-receipt-link]');assert.equal(await link.getAttribute('href'),receipt.product_link);
      const download=page.waitForEvent('download');await link.click();assert.equal((await download).suggestedFilename(),receipt.name);
      const response=await page.request.get(base+receipt.product_link);assert.equal(response.headers()['content-type'],'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      assert.equal(sha(await response.body()),receipt.content_sha256);
      assert.equal(s.dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length+1);
      assert.equal(s.dav.some(r=>r.path.endsWith('.pdf')),false);
      await page.waitForFunction(path=>[...document.querySelectorAll('.workspace-folder-file-name')].some(n=>n.textContent===path),path);
    }
    const before=await state();await page.click('#documentWorkshopExit');await page.reload();await choose(await state());
    await page.waitForSelector('#log [data-document-receipt-link]');
    assert.equal((await state()).dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
    const s=await state();const response=await page.request.post(base+'/api/chat',{data:{conversation_id:s.conversation,client_turn_id:randomUUID(),message:'Trace du dernier document',stream:false}});
    assert.equal(response.status(),200);const after=await state(),payload=after.providers.at(-1),manifest=after.manifests.at(-1);
    assert.equal(manifest.lane_statuses.document_receipt_lane.injected_count,1);
    const lane=manifest.messages.find(m=>m.logical_roles.includes('document_receipt_lane'));
    assert.match(payload.messages[lane.index].content,/docx/);
    assert.equal(JSON.stringify(payload).includes(updatedText),false);
    for(const capture of [...after.faculties,...after.memory_snapshots])for(const text of [originalText,updatedText,created.relative_path])assert.equal(JSON.stringify(capture).includes(text),false);
    await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
    await control({operation:'create',next_path:'Documents/Markdown-card.md',document_text:'Markdown synthétique',document_format:'markdown'});
    await page.fill('#message','Créer explicitement ce document Markdown.');
    await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
    const card=await page.locator('#documentWorkshop .document-action-card').textContent();
    assert.doesNotMatch(card,/formats DOCX et PDF sont indisponibles/);
    assert.match(card,/publication PDF est indisponible/);
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    assert.equal((await state()).dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
    assert.deepEqual(errors,[]);
    if(process.env.M9A_SCREENSHOT)await page.screenshot({path:process.env.M9A_SCREENSHOT});
  } finally {await browser.close();}
});

test('M9A-REAUTH native 303 followed to HTML, reload and same-attempt human resumption',async()=>{
  assert.ok(base,'dedicated native HTTP fixture required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',viewport:{width:390,height:844}});page.setDefaultTimeout(15000);
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const state=async()=>(await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    const choose=async()=>{const s=await state();await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${s.conversation}"]`).click();
      await page.waitForFunction(id=>document.querySelector('#threads li.active')?.dataset.conversationId===id,s.conversation);};
    await page.goto(base,{waitUntil:'domcontentloaded'});assert.equal(new URL(page.url()).origin,base);assert.ok(await page.title());
    await choose();await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
    const initial=await state(),priorRequests=initial.confirmation_requests.length;
    await control({document_format:'markdown',next_path:'Documents/Reauth-'+randomUUID()+'.md',confirmation_transport:'reauth'});
    await page.fill('#message','Créer ce Markdown synthétique pour vérifier la confirmation.');
    await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
    const redirected=page.waitForResponse(r=>r.url()===base+'/__m9a/login'&&r.status()===200);
    await page.locator('#documentWorkshop [data-document-confirm]').click();await redirected;
    await page.waitForFunction(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.confirmations'))[0]?.state==='unknown');
    const before=await state(),first=before.confirmation_requests.at(-1);
    assert.equal(before.confirmation_requests.length,priorRequests+1);assert.equal(before.confirmation_handled,initial.confirmation_handled);
    assert.equal(before.counts.confirmations,initial.counts.confirmations);assert.equal(before.counts.document_receipts,initial.counts.document_receipts);assert.equal(before.dav.slice(initial.dav.length).some(r=>r.method==='PUT'),false);
    const marker=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.confirmations'))[0]);
    const read=await (await page.request.get(base+'/api/document-workshop/actions/'+marker.action_id)).json();
    assert.equal(read.action.state,'pending');assert.equal(read.action.phase,'complete');assert.equal(read.action.revision_id,first.revision_id);
    assert.equal(read.action.confirmation_turn_id,null);assert.equal(read.action.confirmed_at,null);
    await control({confirmation_transport:'lost_reply'}); // Auth restored; lose the application's successful reply next.
    await page.reload();await choose();await openWorkshop(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
    assert.equal((await state()).confirmation_requests.length,priorRequests+1,'reload does not POST');
    assert.equal(await page.locator('#documentWorkshop [data-document-confirm]:enabled').count(),1,'new human gesture is possible after real HTTP reread');
    await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
    const after=await state();assert.deepEqual(after.confirmation_requests.slice(priorRequests),[first,first]);assert.equal(after.confirmation_handled,initial.confirmation_handled+1);
    assert.equal(after.counts.confirmations,initial.counts.confirmations+1);assert.equal(after.counts.document_receipts,initial.counts.document_receipts+1);assert.equal(after.counts.document_revision_renders,initial.counts.document_revision_renders+1);
    assert.deepEqual(after.dav.slice(initial.dav.length).filter(r=>['PUT','DELETE','MKCOL'].includes(r.method)).map(r=>r.method),['PUT']);
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    await page.reload();await choose();await page.waitForSelector('#log [data-document-receipt-link]');
    const final=await state();assert.equal(final.confirmation_requests.length,priorRequests+2);assert.equal(final.counts.document_receipts,initial.counts.document_receipts+1);
    assert.equal(final.dav.slice(initial.dav.length).filter(r=>r.method==='PUT').length,1);assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});

test('M9-B native external DOCX target-only warning before click, update and stale refusal',async()=>{
  assert.ok(base,'dedicated native HTTP fixture required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});page.setDefaultTimeout(20000);
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const state=async()=>(await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    const choose=async()=>{const s=await state();await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${s.conversation}"]`).click();
      await page.waitForFunction(id=>document.querySelector('#threads li.active')?.dataset.conversationId===id,s.conversation);};
    await page.goto(base,{waitUntil:'domcontentloaded'});await choose();
    await control({seed_external_docx:true,external_docx_candidate:true,confirmation_transport:'normal'});
    await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
    await page.click('#documentWorkshopBrowse');
    await page.getByRole('button',{name:'Adopter External.docx',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
    const s=await state(),path='Documents/External.docx';
    const file=(await (await page.request.get(base+'/api/workspace-folders/'+s.folder+'/files')).json()).items.find(f=>f.document_relative_path===path);
    assert.ok(file);assert.equal(s.origins[file.id],'external');
    const initialPuts=s.dav.filter(r=>r.method==='PUT').length,initialReceipts=s.counts.document_receipts;
    for(const stale of [false,true]) {
      if(stale){await page.click('#documentWorkshopExit');await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');}
      await page.selectOption('#documentWorkshopTarget',file.id);
      await page.waitForFunction(id=>document.querySelector('#documentWorkshopTarget').value===id&&document.querySelector('#documentWorkshop').dataset.state==='editing',file.id);
      await control({operation:'update',next_path:path,copy_source:null,document_format:'docx'});
      await page.fill('#message','Remplacer uniquement Original text par Revised text dans la cible DOCX externe.');
      await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
      const card=page.locator('#documentWorkshop .document-action-card');
      assert.match(await card.textContent(),/Ce DOCX externe sera remis en forme dans le profil Writer V1/);
      assert.match(await card.textContent(),/conservation d’une mise en page arbitraire n’est pas garantie/);
      assert.equal(await card.locator('[data-document-confirm]:enabled').count(),1);
      if(!stale && process.env.M9B_SCREENSHOT)await page.screenshot({path:process.env.M9B_SCREENSHOT,fullPage:true});
      const pending=await state();assert.equal(pending.dav.filter(r=>r.method==='PUT').length,initialPuts+(stale?1:0));
      // The synthetic model returns limitations=[]; the application owns this warning.
      const sourceData=pending.providers.at(-1).messages.find(m=>m.content.startsWith('Untrusted document data'));
      assert.ok(sourceData);assert.match(sourceData.content,/selected_update_target/);
      if(stale)await control({change_path:path});
      await card.locator('[data-document-confirm]').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="'+(stale?'conflict':'succeeded')+'"]');
      const after=await state();
      assert.equal(after.dav.filter(r=>r.method==='PUT').length,initialPuts+1);
      assert.equal(after.counts.document_receipts,initialReceipts+1);assert.equal(after.origins[file.id],'external');
      const put=after.dav.filter(r=>r.method==='PUT').at(-1);assert.equal(put.path,path);assert.equal(put.if_match,'"external-docx-v1"');
      assert.equal(after.counts.workspace_files,s.counts.workspace_files);
    }
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});
