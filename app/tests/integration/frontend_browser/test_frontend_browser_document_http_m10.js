'use strict';
// Native browser -> production composition -> isolated SQL/DAV/Writer.
// No fetch replacement; only the provider/faculties are synthetic peers.
const test=require('node:test'),assert=require('node:assert/strict');
const {randomUUID,createHash}=require('node:crypto');
const {chromium}=require('playwright');
const {showFolder,openWorkshop}=require('./helpers/document_workshop_fixture.js');
const base=process.env.M9A_HTTP_BASE;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');

test('M10 native PDF card reauth human confirmation update rehydration exact download',async()=>{
  assert.ok(base,'dedicated native HTTP fixture required');
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});page.setDefaultTimeout(20000);
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const state=async()=>(await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    const choose=async()=>{const s=await state();await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${s.conversation}"]`).click();
      await page.waitForFunction(id=>document.querySelector('#threads li.active')?.dataset.conversationId===id,s.conversation);};
    await page.goto(base,{waitUntil:'domcontentloaded'});await choose();let created;
    for(const operation of ['create','update']) {
      if(await page.locator('#documentWorkshop').isVisible())await page.click('#documentWorkshopExit');
      await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
      assert.match(await page.locator('#documentWorkshopStatus').textContent(),/Markdown.*DOCX.*PDF/);
      if(created){await page.selectOption('#documentWorkshopTarget',created.workspace_file_id);
        await page.waitForFunction(id=>document.querySelector('#documentWorkshopTarget').value===id&&document.querySelector('#documentWorkshop').dataset.state==='editing',created.workspace_file_id);}
      const path=created?.relative_path||'Documents/Study-'+randomUUID()+'.pdf';
      await control({clarify_pdf:false,operation,next_path:path,copy_source:null,document_format:'pdf',external_docx_candidate:false,
        document_text:operation==='create'?'Français éè — création':'Révision été et cœur',confirmation_transport:operation==='create'?'reauth':'normal'});
      const before=await state();await page.fill('#message',operation==='create'?'Créer explicitement le PDF au nom proposé.':'Modifier ce PDF Frida, même nom et identité.');
      await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
      const card=await page.locator('#documentWorkshop .document-action-card').textContent();
      assert.match(card,/pdf/);assert.match(card,/Document limité à 20 pages/);assert.doesNotMatch(card,/PDF.*indisponible|pagination dépend du lecteur Markdown/);
      assert.equal((await state()).dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
      if(operation==='create') {
        if(process.env.M9B_SCREENSHOT)await page.screenshot({path:process.env.M9B_SCREENSHOT,fullPage:true});
        const redirected=page.waitForResponse(r=>r.url()===base+'/__m9a/login'&&r.status()===200);
        await page.locator('#documentWorkshop [data-document-confirm]').click();await redirected;
        await page.waitForFunction(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.confirmations'))[0]?.state==='unknown');
        const waiting=await state();await control({confirmation_transport:'normal'});
        await page.reload();await choose();await openWorkshop(page);
        await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
        const reloaded=await state();assert.equal(reloaded.confirmation_requests.length,waiting.confirmation_requests.length);
        assert.equal(reloaded.counts.document_receipts,before.counts.document_receipts);
      }
      await page.locator('#documentWorkshop [data-document-confirm]:enabled').click();
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
      const after=await state();const messages=(await (await page.request.get(base+'/api/conversations/'+after.conversation+'/messages')).json()).messages;
      const id=messages.filter(m=>m.meta?.document_workshop).at(-1).meta.document_workshop.action_id;
      const action=(await (await page.request.get(base+'/api/document-workshop/actions/'+id)).json()).action,r=action.receipt;
      assert.equal(r.format,'pdf');if(created)assert.equal(r.workspace_file_id,created.workspace_file_id);else created=r;
      const response=await page.request.get(base+r.product_link);assert.equal(response.headers()['content-type'],'application/pdf');
      assert.equal(sha(await response.body()),r.content_sha256);assert.equal((await response.body()).subarray(0,5).toString(),'%PDF-');
      const download=page.waitForEvent('download');await page.locator('#documentWorkshop [data-document-receipt-link]').click();
      const artifact=await download;const downloaded=[];for await (const chunk of await artifact.createReadStream())downloaded.push(chunk);
      assert.equal(await artifact.failure(),null);assert.equal(sha(Buffer.concat(downloaded)),r.content_sha256);
      assert.equal(artifact.suggestedFilename(),r.name);
      const puts=after.dav.slice(before.dav.length).filter(row=>row.method==='PUT');assert.equal(puts.length,1);
      assert.equal(puts[0].path,path);assert.equal(puts[0].sha256,r.content_sha256);assert.equal(puts[0].size,(await response.body()).length);
      assert.equal(after.counts.document_receipts,before.counts.document_receipts+1);
      if(operation==='update')assert.ok(after.providers.at(-1).messages.some(m=>m.content.includes('"target_pdf_has_frida_revision": true')));
    }
    const before=await state();await page.reload();await choose();await page.waitForSelector('#log [data-document-receipt-link]');
    const after=await state();assert.equal(after.confirmation_requests.length,before.confirmation_requests.length);
    assert.equal(after.counts.document_receipts,before.counts.document_receipts);assert.equal(after.dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
});

test('M10 native external PDF clarifies then explicitly selected copy to new PDF',async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});page.setDefaultTimeout(20000);
    const state=async()=>(await page.request.get(base+'/__m6/state')).json();
    const control=async data=>assert.equal((await page.request.post(base+'/__m6/control',{data})).status(),200);
    const choose=async()=>{const s=await state();await showFolder(page,s.folder);await page.locator(`[data-conversation-id="${s.conversation}"]`).click();
      await page.waitForFunction(id=>document.querySelector('#threads li.active')?.dataset.conversationId===id,s.conversation);};
    await page.goto(base,{waitUntil:'domcontentloaded'});await choose();
    await control({seed_external_pdf:true,clarify_pdf:true,confirmation_transport:'normal'});
    await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');await page.click('#documentWorkshopBrowse');
    await page.getByRole('button',{name:'Adopter External.pdf',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
    const before=await state(),files=(await (await page.request.get(base+'/api/workspace-folders/'+before.folder+'/files')).json()).items;
    const file=files.find(f=>f.document_relative_path==='Documents/External.pdf');assert.ok(file);
    await page.selectOption('#documentWorkshopTarget',file.id);
    await page.waitForFunction(id=>document.querySelector('#documentWorkshopTarget').value===id&&document.querySelector('#documentWorkshop').dataset.state==='editing',file.id);
    await page.fill('#message','Modifier ce PDF externe.');await page.locator('button[type="submit"][aria-label="Envoyer"]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="clarify"]');
    assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').count(),0);
    const clarified=await state();assert.equal(clarified.counts.document_receipts,before.counts.document_receipts);
    assert.ok(clarified.providers.at(-1).messages.some(m=>m.content.includes('"target_pdf_has_frida_revision": false')));
    assert.ok(clarified.providers.at(-1).messages.some(m=>m.content.includes('NEW document')));
    assert.equal((await page.request.post(base+'/api/conversations/'+before.conversation+'/workspace-file-selections',{data:{file_id:file.id}})).status(),201);
    await page.reload();await choose();await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state="editing"]');
    const changed=page.waitForResponse(r=>r.url().endsWith('/api/document-workshop/contexts')&&r.request().method()==='POST');
    await page.selectOption('#documentWorkshopTarget','');await changed;
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopTarget').value===''&&document.querySelector('#documentWorkshop').dataset.state==='editing'&&!document.querySelector('#documentWorkshopTarget').disabled);
    await control({clarify_pdf:false,operation:'copy',copy_source:file.id,next_path:'Documents/Nouveau accepté.pdf',document_format:'pdf',document_text:'Synthetic page 1 — modification explicitement demandée'});
    await page.fill('#message','Créer une copie modifiée depuis le PDF sélectionné, nouveau document PDF nommé Nouveau accepté.pdf.');
    await page.locator('button[type="submit"][aria-label="Envoyer"]').click();await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
    assert.equal((await state()).dav.filter(r=>r.method==='PUT').length,before.dav.filter(r=>r.method==='PUT').length);
    await page.locator('#documentWorkshop [data-document-confirm]').click();await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
    const after=await state(),puts=after.dav.slice(before.dav.length).filter(r=>r.method==='PUT');
    assert.equal(puts.length,1);assert.equal(puts[0].path,'Documents/Nouveau accepté.pdf');assert.equal(puts[0].if_none,'*');
    assert.deepEqual(after.remote['Documents/External.pdf'],before.remote['Documents/External.pdf']);
    assert.equal(after.origins[file.id],'external');assert.equal(after.counts.document_receipts,before.counts.document_receipts+1);
  } finally {await browser.close();}
});
