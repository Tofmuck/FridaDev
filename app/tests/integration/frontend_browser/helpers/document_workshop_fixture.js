'use strict';
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


module.exports = { mockScript, showFolder, closeSidebar, openWorkshop };
