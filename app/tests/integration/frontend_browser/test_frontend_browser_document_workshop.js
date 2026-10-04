'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');

function mockScript({ noConversation = false, failCreation = false, delayContext = false, delayCreation = false, delayUpload = false, failContext = false } = {}) {
  return `(() => {
    const state = window.__m1 = { calls: [], docs: [], contexts: [], selections: [], uploadFiles: [], nextCreated: 0, picker: 0, changes: 0, inputChangeBindings: 0, fileButtonBindings: 0,
      conversations: ${noConversation ? '[]' : '[{id:"conv-a", title:"Conversation A",workspace_folder_id:"folder-a"},{id:"conv-b",title:"Conversation B",workspace_folder_id:"folder-b"}]'},
      delayContext: ${delayContext}, delayUpload: ${delayUpload}, failContext: ${failContext}, delayCreation: ${delayCreation}, failCreation: ${failCreation} };
    const originalAdd = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
      if(this.id==='activeDocumentFileInput' && type==='change') state.inputChangeBindings++;
      if(this.id==='btnActiveDocument' && type==='click') state.fileButtonBindings++;
      return originalAdd.call(this,type,listener,options);
    };
    const originalClick = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function() { if(this.id==='activeDocumentFileInput') state.picker++; return originalClick.call(this); };
    document.addEventListener('change', e => {if(e.target.id==='activeDocumentFileInput') state.changes++;});
    const json = (data, status=200) => new Response(JSON.stringify(data), {status,headers:{'Content-Type':'application/json'}});
    window.fetch = async (input, init={}) => {
      const path = new URL(input,location.origin).pathname, method=init.method||'GET';
      const body = typeof init.body==='string' ? JSON.parse(init.body) : null;
      state.calls.push({path,method,body});
      if(path==='/api/workspace-folders') return json({ok:true,items:[{id:'folder-a',display_name:'Recherche',nextcloud_sync_state:'linked'},{id:'folder-b',display_name:'Autre',nextcloud_sync_state:'linked'}]});
      if(path.endsWith('/files')) return json({ok:true,items:[{id:'file-a',workspace_folder_id:path.split('/')[3],display_name:'Ébauche.md',source_extension:'.md',status:'active',content_kind:'document',media_kind:'text',document_nextcloud_sync_state:'linked'}]});
      if(path==='/api/conversations' && method==='GET' && state.delayInventory) await new Promise(resolve=>state.releaseInventory=resolve);
      if(path==='/api/conversations' && method==='GET') return json({ok:true,items:state.conversations,total:state.conversations.length,limit:200,offset:0});
      if(path==='/api/conversations' && method==='POST') {
        if(${noConversation} && !state.bootstrapAttempt) {state.bootstrapAttempt=true;return json({ok:false,error:'Bootstrap synthétique indisponible'},503);}
        const id = state.nextCreated++ ? 'conv-later' : 'conv-new';
        if(state.delayCreation) {state.delayCreation=false;await new Promise(resolve=>state.releaseCreation=resolve);}
        if(state.failCreation) return json({ok:false,error:'Création impossible'},503);
        const conversation={id,title:'Nouvelle conversation',workspace_folder_id:null};
        state.conversations.push(conversation); return json({ok:true,conversation},201);
      }
      if(path.startsWith('/api/conversations/') && method==='PATCH') {
        const conversation=state.conversations.find(c=>c.id===path.split('/')[3]);
        Object.assign(conversation,body); return json({ok:true,conversation});
      }
      if(path.endsWith('/messages')) return json({ok:true,messages:[]});
      if(path.includes('/workspace-file-selections')) {
        if(method==='POST') state.selections.push(body.file_id);
        return json({ok:true,items:state.selections.map(file_id=>({file_id,conversation_id:'conv-a',workspace_folder_id:'folder-a',active:true})),selection:{file_id:body?.file_id}});
      }
      if(path.endsWith('/active-documents') && method==='POST') {
        const file=init.body.get('file');state.uploadFiles.push(file.name);
        if(state.delayUpload) {state.delayUpload=false;await new Promise(resolve=>state.releaseUpload=resolve);}
        if(file.name==='refus.bin') return json({ok:false,reason_code:'document_type_unsupported',document:{filename:file.name,status:'unsupported'}},422);
        const document={document_id:'doc-'+state.docs.length,filename:file.name,byte_size:file.size,source_extension:'.txt',status:'active',media_kind:'text',text_chars:4};
        state.docs.push(document); return json({ok:true,document},201);
      }
      if(path.endsWith('/active-documents')) return json({ok:true,items:state.docs});
      if(path.includes('/active-documents/') && method==='DELETE') {state.docs=[];return json({ok:true});}
      if(path==='/api/document-workshop/contexts' && method==='POST') {
        if(state.delayContext) await new Promise(resolve=>state.releaseContext=resolve);
        if(state.failContext) return json({ok:false,reason_code:'document_context_scope_mismatch'},409);
        const context={id:'context-'+state.contexts.length,conversation_id:body.conversation_id,workspace_folder_id:body.workspace_folder_id,target_file_id:body.target_file_id||null,target_relative_path:body.target_file_id?'Documents/Ébauche.md':null,state:'editing',capabilities:{prepare:false}};
        state.contexts.push(context); return json({ok:true,context},201);
      }
      if(path.startsWith('/api/document-workshop/contexts/')) {
        if(state.delayRead) await new Promise(resolve=>state.releaseRead=resolve);
        return json({ok:true,context:state.contexts.find(c=>c.id===path.split('/').pop())});
      }
      if(path==='/api/chat') return json({ok:true,text:'Réponse normale',conversation_id:'conv-a'});
      if(path==='/api/chat/main-reasoning') return json({ok:true,level:'medium',supported:true});
      return json({ok:true,items:[]});
    };
  })();`;
}

async function showFolder(page, id) {
  if(await page.locator('#btnMenu').isVisible()) await page.click('#btnMenu');
  const toggle=page.locator(`.workspace-folder-row[data-workspace-folder-id="${id}"] .workspace-folder-toggle`);
  await toggle.waitFor();
  if(await toggle.getAttribute('aria-expanded')==='false') await toggle.click();
}
async function closeSidebar(page) {
  if(await page.locator('#btnSidebarClose').isVisible()) await page.click('#btnSidebarClose');
}
async function openWorkshop(page) {
  await page.click('#btnActiveDocument');
  await page.click('#documentFileMenu [data-file-action="workshop"]');
}

for (const mobile of [false,true]) for (const theme of ['light','dark']) {
  test(`M1 mounted menu, real picker/change/upload and editing guard: ${mobile?'mobile':'desktop'} ${theme}`, async () => {
    await openBrowserPage({mockScript:mockScript(),beforePage:async page=>{
      page.setDefaultTimeout(5000);
      await page.setViewportSize({width:mobile?390:1280,height:mobile?844:900});
      await page.addInitScript(value=>localStorage.setItem('frida.chat.theme',value),theme);
    }}, async page=>{
      await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
      assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),theme);
      assert.equal(await page.locator('#activeDocumentFileInput').count(),1);
      assert.equal(await page.locator('#activeDocumentFileInput').getAttribute('multiple'),'');
      assert.deepEqual(await page.evaluate(()=>[window.__m1.inputChangeBindings,window.__m1.fileButtonBindings]),[1,1]);
      const accept=await page.locator('#activeDocumentFileInput').getAttribute('accept');
      for(const extension of ['.pdf','.docx','.odt','.md','.txt','.png','.jpg','.jpeg','.webp']) assert.ok(accept.includes(extension));
      await page.click('#btnActiveDocument');
      assert.equal(await page.locator('#documentFileMenu button').count(),2);
      assert.deepEqual(await page.locator('#documentFileMenu button').allTextContents(),['Ajouter un fichier existant','Créer ou modifier un document']);
      assert.equal(await page.evaluate(()=>window.__m1.picker),0);
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.fileAction),'upload');
      await page.keyboard.press('ArrowDown');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.fileAction),'workshop');
      await page.keyboard.press('Home');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.fileAction),'upload');
      await page.keyboard.press('Escape'); assert.equal(await page.locator('#documentFileMenu').isVisible(),false);
      assert.equal(await page.locator('#btnActiveDocument').getAttribute('aria-expanded'),'false');
      assert.equal(await page.evaluate(()=>document.activeElement.id),'btnActiveDocument');
      await page.click('#btnActiveDocument'); await page.click('#message');
      assert.equal(await page.locator('#documentFileMenu').isVisible(),false);
      await page.click('#btnActiveDocument');
      const chooser=page.waitForEvent('filechooser');
      await page.click('#documentFileMenu [data-file-action="upload"]');
      await (await chooser).setFiles([{name:'premier.txt',mimeType:'text/plain',buffer:Buffer.from('synthetic')},{name:'second.md',mimeType:'text/markdown',buffer:Buffer.from('synthetic')}]);
      await page.waitForFunction(()=>window.__m1.docs.length===2 && !document.querySelector('#btnActiveDocument').disabled);
      const uploadState=await page.evaluate(()=>({picker:window.__m1.picker,changes:window.__m1.changes,calls:window.__m1.calls.filter(c=>c.method==='POST'&&c.path.endsWith('/active-documents'))}));
      assert.equal(uploadState.picker,1);assert.equal(uploadState.changes,1);assert.equal(uploadState.calls.length,2);
      // Existing reading checkbox is not a target choice.
      await showFolder(page,'folder-a');
      await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input[type=checkbox]').check();
      await closeSidebar(page);
      await openWorkshop(page); await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing');
      assert.equal(await page.evaluate(()=>window.__m1.contexts[0].target_file_id),null);
      assert.equal(await page.evaluate(()=>window.__m1.picker),1);
      await page.fill('#message','Brouillon préservé');
      const before=await page.locator('#log').textContent();
      await page.click('#ask button[type="submit"]');
      assert.equal(await page.locator('#message').inputValue(),'Brouillon préservé');
      assert.equal(await page.locator('#log').textContent(),before);
      assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.path==='/api/chat').length),0);
      assert.equal(await page.locator('#documentWorkshop [data-prepare]').count(),0);
      await page.selectOption('#documentWorkshopTarget','file-a');
      await page.waitForFunction(()=>window.__m1.contexts.length===2 && document.querySelector('#documentWorkshop').dataset.state==='editing');
      assert.equal(await page.evaluate(()=>window.__m1.contexts[1].target_file_id),'file-a');
      await page.click('#documentWorkshopReload');
      await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path.startsWith('/api/document-workshop/contexts/')));
      await page.click('#documentWorkshopExit');
      await page.click('#ask button[type="submit"]');
      await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/chat'));
      if(mobile){await page.click('#btnMobileTools');await page.click('#btnActiveDocument');
        assert.equal(await page.locator('#ask').evaluate(el=>el.classList.contains('mobile-tools-expanded')),false);}
    });
  });
}

test('M1 missing conversation: create once, explicit folder association, then context; failure creates none', async()=>{
  for(const failCreation of [false,true]) await openBrowserPage({mockScript:mockScript({noConversation:true,failCreation})}, async page=>{
    await page.waitForSelector('#message:not([disabled])');
    await page.waitForFunction(()=>window.__m1.bootstrapAttempt);
    await openWorkshop(page);
    await page.waitForFunction(()=>window.__m1.calls.filter(c=>c.path==='/api/conversations'&&c.method==='POST').length===2);
    if(failCreation){await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('Impossible'));
      assert.equal(await page.evaluate(()=>window.__m1.contexts.length),0);
      assert.equal(await page.locator('#documentWorkshopFolder').isDisabled(),true);
      assert.equal(await page.locator('#documentWorkshopBindFolder').isDisabled(),true);
      assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.method==='PATCH').length),0);return;}
    await page.waitForSelector('#documentWorkshopFolder:not([disabled])');
    await page.selectOption('#documentWorkshopFolder','folder-a');
    await page.click('#documentWorkshopBindFolder');
    await page.waitForFunction(()=>window.__m1.contexts.length===1);
    const calls=await page.evaluate(()=>window.__m1.calls.filter(c=>c.method==='POST'||c.method==='PATCH'));
    assert.deepEqual(calls.slice(-3).map(c=>c.path),['/api/conversations','/api/conversations/conv-new','/api/document-workshop/contexts']);
  });
});

test('M1 double click and late context response cannot reopen another conversation',async()=>{
  await openBrowserPage({mockScript:mockScript({delayContext:true})},async page=>{
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await openWorkshop(page);await page.waitForFunction(()=>!!window.__m1.releaseContext);
    await openWorkshop(page); // Opening already pending: never a duplicate POST.
    assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.path==='/api/document-workshop/contexts').length),1);
    await showFolder(page,'folder-b');
    await page.click('#threads li[data-conversation-id="conv-b"]');
    await page.evaluate(()=>window.__m1.releaseContext());
    await page.waitForFunction(()=>window.__m1.contexts.length===1);
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-state'),null);
  });
});


test('M1 upload stays sequential, errors and drag/drop/removal keep their real listeners',async()=>{
  await openBrowserPage({mockScript:mockScript({delayUpload:true})},async page=>{
    page.setDefaultTimeout(5000);
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await page.click('#btnActiveDocument'); const picker=page.waitForEvent('filechooser');
    await page.click('#documentFileMenu [data-file-action="upload"]');
    await (await picker).setFiles([{name:'refus.bin',mimeType:'application/octet-stream',buffer:Buffer.from('synthetic')},
      {name:'valide.md',mimeType:'text/markdown',buffer:Buffer.from('synthetic')}]);
    await page.waitForFunction(()=>!!window.__m1.releaseUpload);
    assert.deepEqual(await page.evaluate(()=>window.__m1.uploadFiles),['refus.bin']);
    await page.evaluate(()=>window.__m1.releaseUpload());
    await page.waitForFunction(()=>window.__m1.docs.length===1&&!document.querySelector('#btnActiveDocument').disabled);
    assert.deepEqual(await page.evaluate(()=>window.__m1.uploadFiles),['refus.bin','valide.md']);
    assert.match(await page.locator('#activeDocumentsStatus').textContent(),/Format non pris en charge/);
    assert.equal(await page.locator('#activeDocumentsStatus').evaluate(el=>el.classList.contains('is-error')),true);
    await page.evaluate(()=>{
      const dt=new DataTransfer();dt.items.add(new File(['synthetic'],'déposé.txt',{type:'text/plain'}));
      document.querySelector('.chat').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));
    });
    await page.waitForFunction(()=>window.__m1.docs.length===2&&!document.querySelector('#btnActiveDocument').disabled);
    assert.deepEqual(await page.evaluate(()=>window.__m1.uploadFiles),['refus.bin','valide.md','déposé.txt']);
    await page.locator('.active-document-remove').first().click();
    await page.waitForFunction(()=>window.__m1.docs.length===0);
    assert.equal(await page.evaluate(()=>window.__m1.picker),1);
  });
});

test('M1 deferred GET is invalidated by navigation and never reopens editing',async()=>{
  await openBrowserPage({mockScript:mockScript()},async page=>{
    page.setDefaultTimeout(5000);
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await openWorkshop(page);await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing');
    await page.evaluate(()=>window.__m1.delayRead=true);await page.click('#documentWorkshopReload');
    await page.waitForFunction(()=>!!window.__m1.releaseRead);
    await showFolder(page,'folder-b');await page.click('li[data-conversation-id="conv-b"]');
    await page.evaluate(()=>window.__m1.releaseRead());
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-b/messages'));
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
  });
});

test('M1 folder reassignment through existing drop binding invalidates deferred POST',async()=>{
  await openBrowserPage({mockScript:mockScript({delayContext:true})},async page=>{
    page.setDefaultTimeout(5000);
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await openWorkshop(page);await page.waitForFunction(()=>!!window.__m1.releaseContext);
    await page.evaluate(()=>window.__m1.delayInventory=true);
    await page.evaluate(()=>{
      const dt=new DataTransfer();dt.setData('application/x-fridadev-conversation-id','conv-a');
      document.querySelector('.workspace-folder-row[data-workspace-folder-id="folder-b"]').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));
    });
    await page.waitForFunction(()=>window.__m1.conversations.find(c=>c.id==='conv-a').workspace_folder_id==='folder-b');
    await page.waitForFunction(()=>!!window.__m1.releaseInventory);
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').hidden);
    await page.evaluate(()=>{window.__m1.releaseContext();window.__m1.releaseInventory();});
    await page.waitForFunction(()=>window.__m1.contexts.length===1);
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-state'),null);
  });
});

test('M1 late conversation creation is fenced before selection and creates no context',async()=>{
  await openBrowserPage({mockScript:mockScript({noConversation:true,delayCreation:true})},async page=>{
    page.setDefaultTimeout(5000);
    await page.waitForFunction(()=>window.__m1.bootstrapAttempt);
    await openWorkshop(page);await page.waitForFunction(()=>!!window.__m1.releaseCreation);
    await page.click('#newChat');await page.waitForSelector('li[data-conversation-id="conv-later"].active');
    await page.evaluate(()=>window.__m1.releaseCreation());
    await page.waitForFunction(()=>window.__m1.conversations.length===2);
    assert.equal(await page.locator('li[data-conversation-id="conv-later"].active').count(),1);
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
    assert.equal(await page.evaluate(()=>window.__m1.contexts.length),0);
  });
});

test('M1 opening refusal projects no editing state, preserves draft and offers an explicit exit',async()=>{
  await openBrowserPage({mockScript:mockScript({failContext:true})},async page=>{
    page.setDefaultTimeout(5000);
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await page.fill('#message','Brouillon intact');await openWorkshop(page);
    await page.waitForFunction(()=>document.querySelector('#documentWorkshopStatus').textContent.includes('Impossible'));
    assert.equal(await page.locator('#documentWorkshop').getAttribute('data-state'),null);
    await page.click('#ask button[type=submit]');
    assert.equal(await page.locator('#message').inputValue(),'Brouillon intact');
    assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.path==='/api/chat').length),0);
    assert.equal(await page.locator('#log .msg').count(),0);
    await page.click('#documentWorkshopExit');assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
  });
});
