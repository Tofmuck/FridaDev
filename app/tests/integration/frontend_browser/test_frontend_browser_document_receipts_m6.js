'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {openBrowserPage}=require('./helpers/browser_test_helpers.js');
const {mockScript,showFolder,closeSidebar,openWorkshop}=require('./helpers/document_workshop_fixture.js');

function receiptScript({executing=false,missingReceipt=false,failInventory=false,sameFolder=false,failReadOnce=false}={}) {
  return mockScript()+`;(()=>{
    const base=window.fetch,json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
    const context={id:'ctx-m6',conversation_id:'conv-a',workspace_folder_id:'folder-a',target_file_id:null,target_relative_path:null,state:'editing',capabilities:{prepare:true,confirm:true,update:false}};
    const action={id:'a1111111-1111-4111-8111-111111111111',context_id:context.id,conversation_id:'conv-a',workspace_folder_id:'folder-a',revision_id:'b1111111-1111-4111-8111-111111111111',state:${executing?'"executing"':'"pending"'},operation:'create',format:'markdown',relative_path:'Documents/Section/M6.md',name:'M6.md',collections:['Documents/Section'],limitations:[]};
    const receipt={id:'receipt-m6',action_id:action.id,conversation_id:action.conversation_id,workspace_folder_id:action.workspace_folder_id,workspace_file_id:'file-m6',revision_id:action.revision_id,relative_path:action.relative_path,name:action.name,product_link:'/api/workspace-folders/folder-a/files/file-m6/content',publication_evidence:'historical'};
    const state=window.__m6={action,receipt,calls:[],terminal:sessionStorage.getItem('m6.synthetic.completed')==='yes',failInventory:${failInventory},missingReceipt:${missingReceipt}};
    if(${sameFolder})window.__m1.conversations[1].workspace_folder_id='folder-a';
    state.failReadOnce=${failReadOnce};
    if(state.terminal)action.state='succeeded';
    const project=()=>({...action,capabilities:{confirm:action.state==='pending',cancel:action.state==='executing'||action.state==='pending'},...(action.state==='succeeded'&&!state.missingReceipt?{receipt}:{} )});
    window.fetch=async(input,init={})=>{
      const path=new URL(input,location.origin).pathname,method=init.method||'GET';state.calls.push({path,method});
      if(path.startsWith('/api/document-workshop/contexts'))return json({ok:true,context:{...context,preparation:project()}},method==='POST'?201:200);
      if(path.endsWith('/messages'))return json({ok:true,messages:[{role:'assistant',content:'Parole réelle.',meta:{document_workshop:{context_id:context.id,action_id:action.id,revision_id:action.revision_id}}}]});
      if(path.startsWith('/api/document-workshop/actions/')) {
        if(path.endsWith('/confirm')) {action.state='executing';await new Promise(resolve=>state.release=resolve);action.state='succeeded';sessionStorage.setItem('m6.synthetic.completed','yes');return json({ok:true,action:project()});}
        if(state.failReadOnce){state.failReadOnce=false;return json({ok:false},503);}
        if(state.terminal)action.state='succeeded';return json({ok:true,action:project()});
      }
      if(path==='/api/workspace-folders/folder-a/files'&&action.state==='succeeded') {
        if(state.failInventory)return json({ok:false,reason_code:'workspace_files_lookup_failed'},503);
        return json({ok:true,items:[{id:'file-m6',workspace_folder_id:'folder-a',display_name:'M6.md',status:'active',content_kind:'document',media_kind:'text',source_extension:'.md'}]});
      }
      return base(input,init);
    };
  })();`;
}
async function ready(page,state='pending') {
  page.setDefaultTimeout(5000);
  await page.waitForSelector('#log .document-action-card');
  await showFolder(page,'folder-a');await closeSidebar(page);await openWorkshop(page);
  await page.waitForSelector('#documentWorkshop .document-action-card[data-state="'+state+'"]');
}
for(const phone of [false,true])for(const theme of ['light','dark'])test(`M6 receipt link and common inventory after confirmation: ${phone?'phone':'desktop'} ${theme}`,async()=>{
  await openBrowserPage({mockScript:receiptScript(),beforePage:async page=>{await page.setViewportSize({width:phone?390:1280,height:phone?844:900});await page.addInitScript(value=>localStorage.setItem('frida.chat.theme',value),theme);}},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m6.release==='function');await page.evaluate(()=>window.__m6.release());
    await page.waitForSelector('#log [data-document-receipt-link]');
    assert.equal(await page.locator('#log [data-document-receipt-link]').getAttribute('href'),'/api/workspace-folders/folder-a/files/file-m6/content');
    await page.waitForFunction(()=>window.__m6.calls.some(c=>c.path.endsWith('/folder-a/files')&&window.__m6.action.state==='succeeded'));
    await page.click('#documentWorkshopExit');await page.reload();
    await page.waitForSelector('#log [data-document-receipt-link]');
    assert.equal(await page.evaluate(()=>window.__m6.calls.filter(c=>c.path.endsWith('/confirm')).length),0);
  });
});
test('M6 rehydrated executing action becomes terminal by GET while workshop is closed',async()=>{
  await openBrowserPage({mockScript:receiptScript({executing:true})},async page=>{
    await page.waitForSelector('#log .document-action-card[data-state="executing"]');
    await page.evaluate(()=>window.__m6.terminal=true);
    await page.waitForSelector('#log [data-document-receipt-link]');
    assert.equal(await page.evaluate(()=>window.__m6.calls.filter(c=>c.method==='POST').length),0);
  });
});
test('M6 inventory refresh failure preserves durable receipt and never repeats confirmation',async()=>{
  await openBrowserPage({mockScript:receiptScript({failInventory:true})},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m6.release==='function');await page.evaluate(()=>window.__m6.release());
    await page.waitForSelector('#log [data-document-receipt-link]');
    await page.waitForFunction(()=>document.querySelector('#log').textContent.includes('Inventaire non actualisé'));
    assert.equal(await page.evaluate(()=>window.__m6.calls.filter(c=>c.path.endsWith('/confirm')).length),1);
  });
});
test('M6 unproved success has no executable link or claim of creation',async()=>{
  await openBrowserPage({mockScript:receiptScript({executing:true,missingReceipt:true})},async page=>{
    await page.waitForSelector('#log .document-action-card');await page.evaluate(()=>window.__m6.terminal=true);
    await page.waitForSelector('#log .document-action-card[data-state="succeeded"]');
    assert.equal(await page.locator('#log [data-document-receipt-link]').count(),0);
    assert.equal(await page.locator('#log').textContent().then(s=>s.includes('Document créé')),false);
  });
});
test('M6 late confirmation refreshes its original shared folder without projecting A into B',async()=>{
  await openBrowserPage({mockScript:receiptScript({sameFolder:true})},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m6.release==='function');
    await showFolder(page,'folder-a');await page.locator('[data-conversation-id="conv-b"]').click();await closeSidebar(page);
    const before=await page.evaluate(()=>window.__m6.calls.filter(c=>c.path.endsWith('/folder-a/files')).length);
    await page.evaluate(()=>window.__m6.release());
    await page.waitForFunction(count=>window.__m6.calls.filter(c=>c.path.endsWith('/folder-a/files')).length>count,before);
    assert.equal(await page.locator('#log [data-document-receipt-link]').count(),0);
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
  });
});
test('M6 explicit context reload retries only failed inventory refresh',async()=>{
  await openBrowserPage({mockScript:receiptScript({failInventory:true})},async page=>{
    await ready(page);await page.locator('#documentWorkshop [data-document-confirm]').click();
    await page.waitForFunction(()=>typeof window.__m6.release==='function');await page.evaluate(()=>window.__m6.release());
    await page.waitForFunction(()=>document.querySelector('#log').textContent.includes('Inventaire non actualisé'));
    await page.evaluate(()=>window.__m6.failInventory=false);await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>document.querySelector('#log [data-document-receipt-link]')&&!document.querySelector('#log').textContent.includes('Inventaire non actualisé'));
    assert.equal(await page.evaluate(()=>window.__m6.calls.filter(c=>c.path.endsWith('/confirm')).length),1);
  });
});
test('M6 a transient GET failure during executing does not permanently block terminal rehydration',async()=>{
  await openBrowserPage({mockScript:receiptScript({executing:true,failReadOnce:true})},async page=>{
    // The first card GET fails; context reopening supplies the same executing identity.
    await showFolder(page,'folder-a');await closeSidebar(page);await openWorkshop(page);
    await page.waitForSelector('#documentWorkshop .document-action-card[data-state="executing"]');
    await page.evaluate(()=>{window.__m6.failReadOnce=true;window.__m6.terminal=true;});
    await page.waitForSelector('#documentWorkshop [data-document-receipt-link]');
    assert.equal(await page.evaluate(()=>window.__m6.calls.filter(c=>c.path.endsWith('/confirm')).length),0);
  });
});
