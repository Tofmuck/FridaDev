'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');
const { mockScript, showFolder, closeSidebar, openWorkshop } = require('./helpers/document_workshop_fixture.js');

const SOURCE_ID = 'a1111111-1111-4111-8111-111111111111';
function preparationScript({ delayed = false, initial404 = false } = {}) {
  return mockScript() + `;(() => {
    const baseFetch=window.fetch;
    const state=window.__m4={calls:[],messages:[],actions:{},action:null,normalCalls:0,documentaryCalls:0,delayed:${delayed},initial404:${initial404},reads404:0};
    let restorePromise;
    const restore=()=>restorePromise||(restorePromise=Promise.resolve().then(async()=>{const snapshot=typeof window.__m4ReadServer==='function'?await window.__m4ReadServer():null;if(snapshot){window.__m1.contexts=snapshot.contexts;state.actions=snapshot.actions||(snapshot.action?{[snapshot.action.id]:snapshot.action}:{});state.action=state.actions[snapshot.action?.id]||null;state.messages=snapshot.messages;}}));
    const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
    const caps={prepare:true,confirm:false,formats:['markdown'],operations:['create','copy'],update:false};
    const actionCaps=record=>({confirm:false,cancel:['preparing','pending'].includes(record?.state)});
    const publicAction=(record=state.action)=>({...record,capabilities:actionCaps(record)});
    window.fetch=async(input,init={})=>{
      await restore();
      const path=new URL(input,location.origin).pathname,method=init.method||'GET';
      const body=typeof init.body==='string'?JSON.parse(init.body):null;
      state.calls.push({path,method,body});
      if(path==='/api/chat'){
        if(!body.document_context_id){state.normalCalls++;return baseFetch(input,init);}
        state.documentaryCalls++;
        if(state.rejectChat)return json({ok:false,reason_code:'document_source_selection_changed',error:'Préparation documentaire non confirmée.'},409);
        const context=window.__m1.contexts.find(c=>c.id===body.document_context_id);
        state.action={id:body.client_turn_id,context_id:context.id,turn_id:body.client_turn_id,conversation_id:body.conversation_id,
          workspace_folder_id:context.workspace_folder_id,state:'preparing',phase:'user_saved',received_content_codepoints:0,reason_code:null,
          revision_id:null,artifact_id:null,operation:null,format:null,name:null,relative_path:null,limitations:[],created_at:'2026-10-06T10:00:00Z',updated_at:'2026-10-06T10:00:00Z'};
        state.actions[state.action.id]=state.action;
        state.messages.push({role:'user',content:body.message,meta:{client_turn_id:body.client_turn_id,document_source_file_ids:body.document_source_file_ids,
          document_workshop:{context_id:context.id,action_id:body.client_turn_id,revision_id:null}}});
        if(state.failChat){Object.assign(state.action,{state:'failed',phase:'failed',reason_code:'document_preparation_failed'});throw new TypeError('synthetic offline');}
        if(state.delayed) await new Promise(resolve=>state.release=resolve);
        if(state.action.state==='cancelled') return json({ok:false,reason_code:'conversation_claim_lost',error:'Préparation documentaire non confirmée.'},503);
        Object.assign(state.action,{state:'pending',phase:'prepared',received_content_codepoints:83,revision_id:'revision-'+state.action.id,artifact_id:'artifact-'+state.action.id,
          operation:'create',format:'markdown',name:'Synthèse.md',relative_path:'Documents/Synthèse.md',limitations:['markdown_pagination_reader_dependent','markdown_style_reader_dependent','write_confirmation_unavailable','docx_pdf_unavailable','update_unavailable']});
        const answer='Le document est préparé. L’écriture reste indisponible.';
        state.messages.push({role:'assistant',content:answer,timestamp:'2026-10-06T10:01:00Z',meta:{document_workshop:{context_id:context.id,action_id:body.client_turn_id,revision_id:state.action.revision_id}}});
        return new Response(answer+'\\x1e'+JSON.stringify({kind:'frida-stream-control',event:'done',updated_at:'2026-10-06T10:01:00Z'})+'\\n',{headers:{'Content-Type':'text/plain'}});
      }
      if(path.startsWith('/api/document-workshop/actions/')){
        if(path.endsWith('/cancel')){
          if(state.failCancel)return json({ok:false,reason_code:'document_cancel_unavailable'},503);
          const target=state.actions[path.split('/')[4]];
          if(!target || target.context_id!==body?.context_id)return json({ok:false,reason_code:'document_action_not_found'},404);
          Object.assign(target,{state:'cancelled',reason_code:'document_preparation_cancelled'});
          return json({ok:true,action:{...target,capabilities:{confirm:false,cancel:false}}});
        }
        if(state.blockPendingReads && state.action?.state==='pending'){state.blockedReads=(state.blockedReads||0)+1;await new Promise(()=>{});}
        if(state.initial404 && !state.reads404++){return json({ok:false,reason_code:'document_action_not_found'},404);}
        const target=state.actions[path.split('/')[4]];
        const snapshot=target?publicAction(target):null;
        if(state.delayActionRead){state.delayActionRead=false;await new Promise(resolve=>state.releaseActionRead=resolve);}
        return snapshot?json({ok:true,action:snapshot}):json({ok:false},404);
      }
      if(path.endsWith('/messages'))return json({ok:true,messages:state.messages});
      const response=await baseFetch(input,init);
      if(path.startsWith('/api/document-workshop/contexts')){
        const data=await response.json();if(data.context){data.context.capabilities=caps;data.context.preparation=state.action?publicAction():null;}
        return json(data,response.status);
      }
      if(path.endsWith('/files')){const data=await response.json();data.items.forEach(item=>item.id='${SOURCE_ID}');return json(data);}
      if(path.includes('/workspace-file-selections')){
        const data=await response.json();data.items.forEach(item=>item.file_id='${SOURCE_ID}');return json(data);
      }
      return response;
    };
  })();`;
}
async function ready(page) {
  page.setDefaultTimeout(5000);
  await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
}
async function send(page,text='Prépare un document de synthèse.') {
  await page.fill('#message',text);
  await page.click('#ask button[type="submit"]');
}
for(const mobile of [false,true])for(const theme of ['light','dark']){
  test(`M4 mounted preparation uses one canonical turn, selected sources and compact pending: ${mobile?'phone':'desktop'} ${theme}`,async()=>{
    await openBrowserPage({mockScript:preparationScript(),beforePage:async page=>{
      await page.setViewportSize({width:mobile?390:1280,height:mobile?844:900});
      await page.addInitScript(value=>localStorage.setItem('frida.chat.theme',value),theme);
    }},async page=>{
      await ready(page);await showFolder(page,'folder-a');
      await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input[type=checkbox]').check();
      await closeSidebar(page);await openWorkshop(page);
      await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing');
      await send(page);
      await page.waitForFunction(()=>window.__m4.documentaryCalls===1);
      await page.waitForSelector('.document-action-card[data-state="pending"]');
      const calls=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path==='/api/chat'));
      assert.equal(calls.length,1);assert.equal(calls[0].body.message,'Prépare un document de synthèse.');
      assert.equal(calls[0].body.document_context_id,'context-0');assert.deepEqual(calls[0].body.document_source_file_ids,[SOURCE_ID]);
      assert.equal(calls[0].body.input_mode,'keyboard');assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
      assert.equal(await page.locator('#log .msg.me').count(),1);
      const card=page.locator('#log .document-action-card[data-state="pending"]').last();
      assert.equal(await page.locator('#log .document-action-card').count(),1,'one action card for the canonical turn');
      assert.match(await card.textContent(),/Synthèse.md.*markdown.*Documents\/Synthèse.md/s);
      assert.equal(await card.locator('[data-document-confirm]').isDisabled(),true);
      assert.match(await card.locator('[data-document-confirm]').textContent(),/indisponible/);
      assert.match(await card.textContent(),/mise en forme dépend du lecteur Markdown/);
      assert.doesNotMatch(await card.textContent(),/markdown_style_reader_dependent|write_confirmation_unavailable|\(M4\)/);
      assert.equal(await page.locator('#btnDialogueMode').isDisabled(),true);
      assert.ok(await page.locator('#btnDialogueMode').evaluate(el=>Number(getComputedStyle(el).opacity)<1),'Dialogue must visibly reflect its unavailable state');
      const storage=await page.evaluate(()=>[...Array(sessionStorage.length)].map((_,i)=>sessionStorage.getItem(sessionStorage.key(i))).join(''));
      assert.equal(storage.includes('Prépare un document'),false);assert.equal(storage.includes('Synthèse.md'),false);
      assert.equal(await page.locator('.document-action-card pre,.document-action-card textarea,.document-action-card [data-preview]').count(),0);
      assert.equal(calls.some(c=>JSON.stringify(c.body).includes('canonical')),false);
      const bounds=await card.boundingBox();assert.ok(bounds.width<= (mobile?390:1280));
    });
  });
}
test('M4 preparation exposes honest progress after temporary 404 and durable cancel neutralizes late response',async()=>{
  await openBrowserPage({mockScript:preparationScript({delayed:true,initial404:true})},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="preparing"]');
    await page.waitForFunction(()=>window.__m4.reads404===1);
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('Demande enregistrée'));
    assert.equal(await page.locator('#documentWorkshop').textContent().then(t=>/%/.test(t)),false);
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    await page.waitForFunction(()=>window.__m4.action.state==='cancelled');
    const cancel=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path.endsWith('/cancel')));
    assert.equal(cancel.length,1);assert.deepEqual(cancel[0].body,{context_id:'context-0'});
    await page.evaluate(()=>window.__m4.release());
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.actionState==='cancelled');
    assert.equal(await page.locator('.document-action-card[data-state="pending"]').count(),0);
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);
  });
});
test('M4 pending cancel from rehydrated message remains durable and never confirms',async()=>{
  await openBrowserPage({mockScript:preparationScript()},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    const card=page.locator('#log .document-action-card[data-state="pending"]').last();await card.waitFor();
    await page.click('#documentWorkshopExit');
    await card.locator('[data-document-cancel]').click();
    await page.waitForFunction(()=>window.__m4.action.state==='cancelled');
    assert.equal(await page.evaluate(()=>window.__m4.calls.filter(c=>c.path.endsWith('/confirm')).length),0);
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);
  });
});
for(const selector of ['#btnWebSearch','#btnBiblioMode','#btnAgendaMode','#btnAdobeMode','#btnNotesMode','#btnImageGeneration']){
  test(`M4 incompatible ${selector} preserves draft and active control before optimistic effects`,async()=>{
    await openBrowserPage({mockScript:preparationScript()},async page=>{
      await ready(page);await openWorkshop(page);await page.click(selector);
      if(selector==='#btnAdobeMode')await page.click('[data-adobe-product="photoshop"]');
      await send(page,'Brouillon intact');
      assert.equal(await page.locator('#message').inputValue(),'Brouillon intact',selector);
      assert.equal(await page.locator('#log .msg.me').count(),0);
      assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),0);
      assert.match(await page.locator('#documentWorkshopStatus').textContent(),/incompatible|désactivez/i);
      if(selector==='#btnImageGeneration')assert.equal(await page.locator(selector).getAttribute('aria-expanded'),'true');
      else assert.equal(await page.locator(selector).getAttribute('aria-pressed'),'true');
    });
  });
}

for(const delayed of [false,true]){
  test(`M4 reload restores ${delayed?'preparing':'pending'} by reference without replaying a model turn`,async()=>{
    let snapshot=null;
    await openBrowserPage({mockScript:preparationScript({delayed}),beforePage:page=>page.exposeFunction('__m4ReadServer',()=>snapshot)},async page=>{
      await ready(page);await openWorkshop(page);await send(page);
      await page.waitForSelector(`#documentWorkshop .document-action-card[data-state="${delayed?'preparing':'pending'}"]`);
      snapshot=await page.evaluate(()=>({contexts:window.__m1.contexts,action:window.__m4.action,messages:window.__m4.messages}));
      const actionId=snapshot.action.id;
      assert.equal(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt')).action_id),actionId);
      await page.reload();await ready(page);
      await page.waitForSelector(`#documentWorkshop .document-action-card[data-state="${delayed?'preparing':'pending'}"]`);
      assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),0);
      assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
      assert.equal(await page.evaluate(()=>window.__m4.calls.filter(c=>c.path==='/api/document-workshop/contexts' && c.method==='POST').length),0);
      assert.ok(await page.evaluate(()=>window.__m4.calls.some(c=>c.path.startsWith('/api/document-workshop/contexts/'))));
      assert.equal(await page.locator('#log .msg.me').count(),1);
      await page.locator('#documentWorkshop [data-document-cancel]').click();
      await page.waitForFunction(()=>window.__m4.action.state==='cancelled');
    });
  });
}
test('M4 cancelled preparation refuses an older preparing snapshot still in flight',async()=>{
  await openBrowserPage({mockScript:preparationScript({delayed:true})},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('Demande enregistrée'));
    await page.evaluate(()=>window.__m4.delayActionRead=true);
    await page.waitForFunction(()=>typeof window.__m4.releaseActionRead==='function');
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.actionState==='cancelled');
    await page.evaluate(()=>window.__m4.releaseActionRead());
    await page.waitForTimeout(100);
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-action-state'),'cancelled');
    await page.evaluate(()=>window.__m4.release());
  });
});
test('M4 navigation and explicit return invalidate late preparation UI without replay',async()=>{
  for(const navigate of [false,true])await openBrowserPage({mockScript:preparationScript({delayed:true})},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="preparing"]');
    if(navigate){await showFolder(page,'folder-b');await page.click('#threads li[data-conversation-id="conv-b"]');await closeSidebar(page);}
    else await page.click('#documentWorkshopExit');
    await page.evaluate(()=>window.__m4.release());
    await page.waitForFunction(()=>window.__m4.action.state==='pending');
    await page.waitForTimeout(150);
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
    if(navigate)assert.equal(await page.locator('#log .document-action-card').count(),0);
    else await page.waitForSelector('#log .document-action-card[data-state="pending"]');
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);
    assert.equal(await page.locator('#btnDialogueMode').isDisabled(),false);
  });
});


test('M4 failed durable cancel keeps preparation state and an explicit reread notice',async()=>{
  await openBrowserPage({mockScript:preparationScript({delayed:true})},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="preparing"]');
    await page.evaluate(()=>window.__m4.failCancel=true);
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    await page.waitForFunction(()=>window.__m4.calls.some(c=>c.path.endsWith('/cancel')));
    await page.waitForTimeout(100);
    assert.match(await page.locator('#documentWorkshopStatus').textContent(),/Annulation non confirmée/);
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-action-state'),'preparing');
    assert.equal(await page.evaluate(()=>window.__m4.calls.filter(c=>c.path==='/api/chat').length),1);
    await page.evaluate(()=>window.__m4.release());
  });
});
test('M4 network failure after durable user rereads transcript references without retry or invented assistant success',async()=>{
  await openBrowserPage({mockScript:preparationScript()},async page=>{
    await ready(page);await openWorkshop(page);await page.evaluate(()=>window.__m4.failChat=true);
    await send(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="failed"]');
    await page.waitForTimeout(150);
    assert.equal(await page.evaluate(()=>window.__m4.messages.filter(m=>m.role==='assistant').length),0);
    assert.equal(await page.locator('#log .msg.me').count(),1);
    assert.ok(await page.evaluate(()=>window.__m4.calls.filter(c=>c.path.endsWith('/messages')).length)>=2,'failure must reread durable user references');
    assert.equal(await page.locator('#log .document-action-card[data-state="failed"]').count(),1);
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);
    assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
  });
});

// These mounted tests prove browser projections, not database authority. Their
// state transitions correspond to the real HTTP/PostgreSQL chain in
// test_action_cancellation_postgresql.ActionCancellationPostgresqlTests:
// test_cancel_old_pending_preserves_preparing_successor_authority_and_result
// and test_cancel_preparing_successor_preserves_old_pending_and_fences_late_result.
test('P2-M4-01 historical A cancellation preserves B progress, pending and identities after refresh',async()=>{
  let snapshot=null;
  await openBrowserPage({mockScript:preparationScript(),beforePage:page=>page.exposeFunction('__m4ReadServer',()=>snapshot)},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    const oldCard=page.locator('#log .document-action-card[data-state="pending"]').last();await oldCard.waitFor();
    const first=await page.evaluate(()=>window.__m4.action);
    await page.evaluate(()=>window.__m4.delayed=true);await send(page,'Seconde préparation');
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="preparing"]');
    const second=await page.evaluate(()=>window.__m4.action);assert.notEqual(first.id,second.id);
    assert.equal(second.context_id,first.context_id);
    const identity={context_id:second.context_id,conversation_id:'conv-a',workspace_folder_id:'folder-a',action_id:second.id};
    await page.evaluate(()=>window.__m4.delayActionRead=true);
    await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>typeof window.__m4.releaseActionRead==='function');
    await oldCard.locator('[data-document-cancel]').focus();await page.keyboard.press('Enter');
    await page.waitForSelector('#log .document-action-card[data-state="cancelled"]');
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-action-state'),'preparing');
    const attempt=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt')));
    assert.deepEqual(attempt,{...identity,state:'preparing'});
    const cancels=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path.endsWith('/cancel')));
    assert.deepEqual(cancels.map(({path,method,body})=>({path,method,body})),[
      {path:`/api/document-workshop/actions/${first.id}/cancel`,method:'POST',body:{context_id:first.context_id}},
    ]);
    // A late read of B remains a read of B; cancelling A grants no authority to
    // replace the current action. The next synthetic provider input advances B.
    await page.evaluate(()=>{Object.assign(window.__m4.action,{phase:'provider_content',received_content_codepoints:17});window.__m4.releaseActionRead();});
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('17 caractères reçus'));
    await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing'
      && document.querySelector('#documentWorkshopStatus').textContent.includes('17 caractères reçus'));
    assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt'))),{...identity,state:'preparing'});
    await page.evaluate(()=>window.__m4.release());
    await page.waitForSelector('#log .document-action-card[data-state="pending"]');
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.actionState==='pending');
    assert.equal(await page.locator('#log .document-action-card[data-state="cancelled"]').count(),1);
    assert.equal(await page.locator('#log .document-action-card[data-state="pending"]').count(),1);
    assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt'))),{...identity,state:'pending'});
    const submits=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path==='/api/chat'));
    assert.deepEqual(submits.map(c=>c.body.client_turn_id),[first.id,second.id]);
    assert.equal(submits.every(c=>c.body.document_context_id===first.context_id),true);
    assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
    assert.equal(await page.locator('#log .msg.me').count(),2);
    snapshot=await page.evaluate(()=>({contexts:window.__m1.contexts,actions:window.__m4.actions,action:window.__m4.action,messages:window.__m4.messages}));
    await page.reload();await ready(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="pending"]');
    await page.waitForSelector('#log .document-action-card[data-state="cancelled"]');
    assert.equal(await page.locator('#log .document-action-card[data-state="pending"]').count(),1);
    assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt'))),{...identity,state:'pending'});
    assert.deepEqual(await page.evaluate(()=>window.__m4.calls.filter(c=>c.method==='POST')),[],'refresh must replay no turn, context creation or cancellation');
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-state'),'editing');
  });
});

test('P2-M4-01 current B cancellation preserves historical A pending and rejects late responses after refresh',async()=>{
  let snapshot=null;
  await openBrowserPage({mockScript:preparationScript(),beforePage:page=>page.exposeFunction('__m4ReadServer',()=>snapshot)},async page=>{
    await ready(page);await openWorkshop(page);await send(page);
    await page.waitForSelector('#log .document-action-card[data-state="pending"]');
    const first=await page.evaluate(()=>window.__m4.action);
    await page.evaluate(()=>window.__m4.delayed=true);await send(page,'Seconde préparation');
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="preparing"]');
    const second=await page.evaluate(()=>window.__m4.action);assert.notEqual(first.id,second.id);
    const identity={context_id:first.context_id,conversation_id:'conv-a',workspace_folder_id:'folder-a',action_id:second.id};
    await page.evaluate(()=>window.__m4.delayActionRead=true);
    await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>typeof window.__m4.releaseActionRead==='function');
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.actionState==='cancelled');
    assert.equal(await page.locator('#log .document-action-card[data-state="pending"]').count(),1);
    assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt'))),{...identity,state:'cancelled'});
    const cancels=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path.endsWith('/cancel')));
    assert.deepEqual(cancels.map(({path,method,body})=>({path,method,body})),[
      {path:`/api/document-workshop/actions/${second.id}/cancel`,method:'POST',body:{context_id:first.context_id}},
    ]);
    await page.evaluate(()=>{window.__m4.releaseActionRead();window.__m4.release();});
    await page.waitForSelector('#log .document-action-card[data-state="cancelled"]');
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-action-state'),'cancelled');
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-state'),'editing');
    assert.equal(await page.locator('#log .document-action-card[data-state="pending"]').count(),1);
    assert.equal(await page.locator('#log .document-action-card[data-state="preparing"]').count(),0);
    assert.equal(await page.locator('#log .msg.me').count(),2);
    const submits=await page.evaluate(()=>window.__m4.calls.filter(c=>c.path==='/api/chat'));
    assert.deepEqual(submits.map(c=>c.body.client_turn_id),[first.id,second.id]);
    assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
    snapshot=await page.evaluate(()=>({contexts:window.__m1.contexts,actions:window.__m4.actions,action:window.__m4.action,messages:window.__m4.messages}));
    await page.reload();await ready(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="cancelled"]');
    await page.waitForSelector('#log .document-action-card[data-state="pending"]');
    assert.equal(await page.locator('#log .document-action-card[data-state="cancelled"]').count(),1);
    assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('frida.document-workshop.attempt'))),{...identity,state:'cancelled'});
    assert.deepEqual(await page.evaluate(()=>window.__m4.calls.filter(c=>c.method==='POST')),[],'refresh must replay no turn, context creation or cancellation');
  });
});

test('M4 refusal before initial SQL transaction rereads an absent action without fake continuing preparation',async()=>{
  await openBrowserPage({mockScript:preparationScript()},async page=>{
    await ready(page);await openWorkshop(page);await page.evaluate(()=>window.__m4.rejectChat=true);
    await send(page);
    await page.waitForFunction(()=>window.__m4.documentaryCalls===1);
    await page.waitForTimeout(250);
    assert.equal(await page.locator('#documentWorkshop .document-action-card[data-state="preparing"]').count(),0);
    assert.match(await page.locator('#documentWorkshopStatus').textContent(),/absente|non confirmée/);
    assert.equal(await page.locator('#log .msg.me').count(),0);
    const reads=await page.evaluate(()=>window.__m4.calls.length);
    await page.waitForTimeout(850);
    assert.equal(await page.evaluate(()=>window.__m4.calls.length),reads,'settled refusal must stop automatic operation reads');
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);assert.equal(await page.evaluate(()=>window.__m4.normalCalls),0);
  });
});

test('M4 completed canonical turn releases chat even if pending state rereads remain blocked',async()=>{
  await openBrowserPage({mockScript:preparationScript()},async page=>{
    await ready(page);await openWorkshop(page);await page.evaluate(()=>window.__m4.blockPendingReads=true);
    await send(page);
    await page.waitForFunction(()=>window.__m4.action?.state==='pending' && window.__m4.blockedReads>0);
    await page.waitForFunction(()=>[...document.querySelectorAll('#log .msg')].some(node=>node.textContent.includes('Le document est préparé.')));
    await page.click('#documentWorkshopExit');
    await send(page,'Retour au chat normal');
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(()=>window.__m4.normalCalls),1,'state GET must not retain the canonical chat busy guard');
    assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),1);
  });
});
