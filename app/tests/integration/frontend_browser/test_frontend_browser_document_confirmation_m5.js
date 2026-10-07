'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');
const { mockScript, showFolder, closeSidebar, openWorkshop } = require('./helpers/document_workshop_fixture.js');

// Static app and real controller; only fetch is synthetic. No Flask/DAV claim.
function confirmationScript({ available = true, failure = null } = {}) {
  return mockScript() + `;(() => {
    const baseFetch=window.fetch, json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
    const context={id:'context-0',conversation_id:'conv-a',workspace_folder_id:'folder-a',target_file_id:null,target_relative_path:null,state:'editing',capabilities:{prepare:true,confirm:${available},update:false}};
    const state=window.__m5={calls:[],failure:${JSON.stringify(failure)},action:{id:'a1111111-1111-4111-8111-111111111111',context_id:context.id,conversation_id:'conv-a',workspace_folder_id:'folder-a',
      state:'pending',revision_id:'b1111111-1111-4111-8111-111111111111',operation:'create',format:'markdown',name:'Synthétique.md',relative_path:'Documents/Section/Synthétique.md',collections:['Documents/Section'],limitations:[]}};
    state.actions={[state.action.id]:state.action};
    const project=(record=state.action)=>({...record,capabilities:{confirm:${available}&&record.state==='pending',cancel:['preparing','pending','executing'].includes(record.state)}});
    let restored;
    const restore=()=>restored||(restored=Promise.resolve().then(async()=>{if(typeof window.__m5ReadServer==='function'){const saved=await window.__m5ReadServer();if(saved){state.action=saved;state.actions[saved.id]=saved;}}}));
    window.fetch=async(input,init={})=>{
      await restore();
      const path=new URL(input,location.origin).pathname,method=init.method||'GET',body=typeof init.body==='string'?JSON.parse(init.body):null;
      state.calls.push({path,method,body});
      if(path.startsWith('/api/document-workshop/contexts')){
        const snapshot={...context,preparation:project()};
        if(method==='GET'&&state.delayContextRead){state.delayContextRead=false;await new Promise(resolve=>state.releaseRead=resolve);}
        return json({ok:true,context:snapshot},method==='POST'?201:200);
      }
      if(path.endsWith('/messages'))return json({ok:true,messages:path.includes('conv-a')?[{role:'assistant',content:'Proposition préparée.',meta:{document_workshop:{context_id:context.id,action_id:state.action.id,revision_id:state.action.revision_id}}}]:[]});
      if(path.startsWith('/api/document-workshop/actions/')){
        const target=state.actions[path.split('/')[4]]||state.action;
        if(path.endsWith('/confirm')){
          state.sent=body;
          if(state.rejectConfirm)return json({ok:false,reason_code:'conversation_turn_conflict'},409);
          if(state.failure==='not_received')throw new TypeError('synthetic lost before server');
          if(state.failure==='after_received'){state.action.state='remote_uncertain';throw new TypeError('synthetic lost after server');}
          if(state.failure==='reply_lost'){state.action.state='executing';throw new TypeError('synthetic execution reply lost');}
          state.action.state='executing';await new Promise(resolve=>state.release=resolve);
          state.action.state='succeeded';return json({ok:true,action:project()});
        }
        if(path.endsWith('/cancel')){target.state=target.state==='executing'?'remote_uncertain':'cancelled';return json({ok:true,action:project(target)});}
        const snapshot=project(target);
        if(state.delayRead){state.delayRead=false;await new Promise(resolve=>state.releaseRead=resolve);state.readReleased=true;}
        return json({ok:true,action:snapshot});
      }
      return baseFetch(input,init);
    };
  })();`;
}
async function ready(page, state='pending') {
  page.setDefaultTimeout(5000);
  await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
  await showFolder(page,'folder-a');await closeSidebar(page); await openWorkshop(page);
  await page.waitForSelector(`#documentWorkshop .document-action-card[data-state="${state}"]`);
  await page.waitForSelector(`#log .document-action-card[data-state="${state}"]`);
}
const confirms = () => window.__m5.calls.filter(c=>c.path.endsWith('/confirm'));
for(const mobile of [false,true])for(const theme of ['light','dark']) {
  test(`M5 confirmation synchronously removes every button and rejects detached double clicks: ${mobile?'phone':'desktop'} ${theme}`,async()=>{
    await openBrowserPage({mockScript:confirmationScript(),beforePage:async page=>{
      await page.setViewportSize({width:mobile?390:1280,height:mobile?844:900});
      await page.addInitScript(value=>localStorage.setItem('frida.chat.theme',value),theme);
    }},async page=>{
      await ready(page);
      assert.equal(await page.locator('[data-document-confirm]').count(),2);
      assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').isEnabled(),true);
      await page.evaluate(()=>window.__oldConfirmButtons=[...document.querySelectorAll('[data-document-confirm]')]);
      await page.locator('#documentWorkshop [data-document-confirm]').click();
      await page.waitForFunction(()=>typeof window.__m5.release==='function');
      assert.equal(await page.locator('[data-document-confirm]').count(),0,'remove before POST resolves');
      await page.evaluate(()=>window.__oldConfirmButtons.forEach(button=>{button.click();button.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));}));
      assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);
      const body=await page.evaluate(()=>window.__m5.sent);
      assert.deepEqual(Object.keys(body).sort(),['context_id','conversation_id','request_id','revision_id','workspace_folder_id']);
      assert.equal(body.context_id,'context-0');assert.equal(body.conversation_id,'conv-a');assert.equal(body.workspace_folder_id,'folder-a');
      assert.match(body.request_id,/^[0-9a-f-]{36}$/);assert.equal(body.revision_id,'b1111111-1111-4111-8111-111111111111');
      assert.equal(await page.evaluate(()=>window.__m5.calls.filter(c=>c.path==='/api/chat').length),0);
      await page.evaluate(()=>window.__m5.release());
      await page.waitForSelector('#documentWorkshop .document-action-card[data-state="succeeded"]');
      assert.equal(await page.locator('[data-document-confirm]').count(),0);
    });
  });
}
test('M5 keyboard confirmation consumes the same action once',async()=>{
  await openBrowserPage({mockScript:confirmationScript()},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(()=>typeof window.__m5.release==='function');await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);assert.equal(await page.locator('[data-document-confirm]').count(),0);
    await page.evaluate(()=>window.__m5.release());
  });
});
for(const failure of ['not_received','after_received'])test(`M5 ${failure} rereads honest state and refresh never posts or rearms`,async()=>{
  let snapshot=null;
  await openBrowserPage({mockScript:confirmationScript({failure}),beforePage:page=>page.exposeFunction('__m5ReadServer',()=>snapshot)},async page=>{
    await ready(page);
    const reads=await page.evaluate(()=>window.__m5.calls.filter(c=>c.path.startsWith('/api/document-workshop/actions/')&&c.method==='GET').length);
    await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(count=>window.__m5.calls.filter(c=>c.path.startsWith('/api/document-workshop/actions/')&&c.method==='GET').length>count,reads);
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    if(failure==='not_received'){
      // The request counter observes dispatch, before its JSON response renders.
      await page.waitForFunction(()=>/non établie|non confirmée|incertain/i.test(document.querySelector('#documentWorkshop .document-action-card')?.textContent||''));
      assert.equal(await page.evaluate(()=>window.__m5.action.state),'pending');
      assert.match(await page.locator('#documentWorkshop .document-action-card').textContent(),/non établie|non confirmée|incertain/i);
      assert.equal(await page.locator('.document-action-card[data-state="executing"],.document-action-card[data-state="succeeded"]').count(),0);
    }else await page.waitForSelector('#documentWorkshop .document-action-card[data-state="remote_uncertain"]');
    const stored=await page.evaluate(()=>sessionStorage.getItem('frida.document-workshop.confirmations'));
    assert.ok(stored);assert.equal(/Synthétique|Documents|canonical|Proposition/.test(stored),false);
    snapshot=await page.evaluate(()=>window.__m5.action);
    await page.reload();await ready(page, failure==='not_received'?'pending':'remote_uncertain');
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    assert.deepEqual(await page.evaluate(confirms),[]);
    await page.click('#documentWorkshopReload');
    assert.deepEqual(await page.evaluate(confirms),[]);assert.equal(await page.locator('[data-document-confirm]').count(),0);
  });
});
test('M5 a late pending reread cannot restore a consumed confirmation',async()=>{
  await openBrowserPage({mockScript:confirmationScript()},async page=>{
    await ready(page);await page.evaluate(()=>window.__m5.delayContextRead=true);await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>typeof window.__m5.releaseRead==='function');
    await page.locator('#log [data-document-confirm]').click();await page.waitForFunction(()=>typeof window.__m5.release==='function');
    await page.evaluate(()=>window.__m5.releaseRead());
    assert.equal(await page.locator('[data-document-confirm]').count(),0);assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);
    await page.evaluate(()=>window.__m5.release());
  });
});
test('M5 a delayed fallback read cannot overwrite the cancellation of its execution',async()=>{
  await openBrowserPage({mockScript:confirmationScript({failure:'reply_lost'})},async page=>{
    await ready(page);await page.evaluate(()=>window.__m5.delayRead=true);
    await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m5.releaseRead==='function');
    await page.locator('#documentWorkshop [data-document-cancel]').click();
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="remote_uncertain"]');
    await page.evaluate(()=>window.__m5.releaseRead());
    await page.waitForFunction(()=>window.__m5.readReleased);
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    assert.equal(await page.locator('#documentWorkshop .document-action-card').getAttribute('data-state'),'remote_uncertain');
    assert.equal(await page.locator('#log .document-action-card').getAttribute('data-state'),'remote_uncertain');
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);
  });
});
test('M5 confirming historical A does not stop the active preparation B rereads',async()=>{
  await openBrowserPage({mockScript:confirmationScript()},async page=>{
    await ready(page);
    await page.evaluate(()=>{
      window.__m5.action={...window.__m5.action,id:'c1111111-1111-4111-8111-111111111111',state:'preparing',revision_id:null,phase:'user_saved',received_content_codepoints:0};
      window.__m5.actions[window.__m5.action.id]=window.__m5.action;
      window.__m5.delayRead=true;window.__m5.rejectConfirm=true;
    });
    await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>typeof window.__m5.releaseRead==='function');
    await page.locator('#log [data-document-confirm]').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(()=>window.__m5.calls.some(c=>c.path.endsWith('/confirm')));
    await page.evaluate(()=>{Object.assign(window.__m5.action,{phase:'provider_content',received_content_codepoints:17});window.__m5.releaseRead();});
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('17 caractères reçus'));
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-action-state'),'preparing');
    assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);
    assert.equal(await page.locator('#log [data-document-confirm]').count(),0);
  });
});
test('M5 refresh during an unresolved confirmation reads executing and never posts again',async()=>{
  let snapshot=null;
  await openBrowserPage({mockScript:confirmationScript(),beforePage:page=>page.exposeFunction('__m5ReadServer',()=>snapshot)},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m5.release==='function');
    snapshot=await page.evaluate(()=>window.__m5.action);
    assert.equal(snapshot.state,'executing');
    await page.reload();await ready(page,'executing');
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    assert.deepEqual(await page.evaluate(confirms),[]);
    assert.ok(await page.evaluate(()=>window.__m5.calls.some(c=>c.path.startsWith('/api/document-workshop/actions/')&&c.method==='GET')));
  });
});
test('M5 navigation isolates a late result from the other conversation and folder',async()=>{
  await openBrowserPage({mockScript:confirmationScript()},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();await page.waitForFunction(()=>typeof window.__m5.release==='function');
    await showFolder(page,'folder-b');await page.click('#threads li[data-conversation-id="conv-b"]');await closeSidebar(page);
    await page.evaluate(()=>window.__m5.release());
    await page.waitForFunction(()=>window.__m5.action.state==='succeeded');
    assert.equal(await page.locator('#log .document-action-card').count(),0);assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
    assert.equal(await page.evaluate(confirms).then(rows=>rows.length),1);
  });
});
test('M5 public unavailable capability cannot be activated by changing a disabled DOM button',async()=>{
  await openBrowserPage({mockScript:confirmationScript({available:false})},async page=>{
    await ready(page);assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').isDisabled(),true);
    await page.locator('#documentWorkshop [data-document-confirm]').evaluate(button=>{button.disabled=false;button.click();});
    assert.deepEqual(await page.evaluate(confirms),[]);
  });
});
test('M5 unavailable local attempt storage prevents sending a confirmation',async()=>{
  await openBrowserPage({mockScript:confirmationScript(),beforePage:page=>page.addInitScript(()=>{
    const set=Storage.prototype.setItem;
    Storage.prototype.setItem=function(key,value){if(key==='frida.document-workshop.confirmations')throw new DOMException('synthetic quota','QuotaExceededError');return set.call(this,key,value);};
  })},async page=>{
    await ready(page);assert.equal(await page.locator('#documentWorkshop [data-document-confirm]').isDisabled(),true);
    await page.locator('#documentWorkshop [data-document-confirm]').evaluate(button=>{button.disabled=false;button.click();});
    assert.deepEqual(await page.evaluate(confirms),[]);
  });
});
for(const count of [1,null,0])test(`M5 retained collections are reported honestly with ${count===null?'unknown':count===0?'zero observed':'known'} creation count`,async()=>{
  let snapshot=null;
  await openBrowserPage({mockScript:confirmationScript(),beforePage:page=>page.exposeFunction('__m5ReadServer',()=>snapshot)},async page=>{
    await ready(page);
    snapshot=await page.evaluate(value=>({...window.__m5.action,state:value===1?'failed':'remote_uncertain',
      created_collections_count:value,confirmation_turn_id:'d1111111-1111-4111-8111-111111111111'}),count);
    await page.reload();await ready(page,count===1?'failed':'remote_uncertain');
    for(const selector of ['#documentWorkshop .document-action-card','#log .document-action-card']){
      const message=await page.locator(selector).textContent();
      assert.match(message,count===1?/1 sous-répertoire.*subsister.*vide/i:count===0?/sous-répertoires.*état.*vérifi/i:/sous-répertoires.*création.*vérifi/i);
      if(count!==1)assert.doesNotMatch(message,/1 sous-répertoire/);
      else assert.match(message,/Exécution documentaire échouée/);
    }
    assert.equal(await page.locator('[data-document-confirm]').count(),0);
    assert.deepEqual(await page.evaluate(confirms),[]);
  });
});
