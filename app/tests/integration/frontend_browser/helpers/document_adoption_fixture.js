'use strict';
const { mockScript } = require('./document_workshop_fixture.js');
const exactPath = 'Documents/Sous  dossier/E\u0301tude  française.md';
function adoptionScript() {
  return mockScript() + `(() => {
    const state = window.__m2 = {calls:[], adopted:false, deferred:{}, release:{}, finished:[]};
    const base=window.fetch;
    const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
    const path=${JSON.stringify(exactPath)};
    const file={id:'adopted-file',workspace_folder_id:'folder-a',display_name:'Étude  française.md',original_filename:'Étude  française.md',document_relative_path:path,document_origin:'external',document_remote_delete_available:false,source_kind:'nextcloud_adoption',source_extension:'.md',status:'active',content_kind:'document',media_kind:'text',document_nextcloud_sync_state:'linked'};
    const item=(reference,name,category,extra={})=>({reference,name,relative_path:'Documents/'+name,is_collection:false,category,reason_code:'document_'+category,...extra});
    const wait=async key=>{if(state.deferred[key]){delete state.deferred[key];await new Promise(resolve=>state.release[key]=resolve);}state.finished.push(key);};
    window.fetch=async(input,init={})=>{
      const url=new URL(input,location.origin),method=init.method||'GET',body=typeof init.body==='string'?JSON.parse(init.body):null;
      if(state.failRead && url.pathname.startsWith('/api/document-workshop/contexts/')) return json({ok:false,reason_code:'document_context_target_changed'},409);
      if(url.pathname.endsWith('/documents/remote')){
        const reference=url.searchParams.get('collection_ref');state.calls.push({path:url.pathname,method,query:Object.fromEntries(url.searchParams)});
        if(reference!==null && reference!=='root-ref' && reference!=='sub-ref') return json({ok:false,reason_code:'document_remote_reference_invalid'},409);
        const nested=reference==='sub-ref';
        await wait(reference||'root');
        if(state.overflow) return json({ok:false,reason_code:'document_remote_listing_too_large',error:'<img src=x onerror=alert(1)>'},422);
        return json({ok:true,workspace_folder_id:'folder-a',complete:state.incomplete!==true,collection:{reference:reference||'root-ref',relative_path:nested?'Documents/Sous  dossier':'Documents',name:nested?'Sous  dossier':'Documents'},items:nested?
          [item('nested-ref','Étude  française.md',state.adopted?'already_linked':'adoptable',{relative_path:path,...(state.adopted?{workspace_file_id:file.id}:{})})]:[
          item('sub-ref','Sous  dossier','incompatible',{is_collection:true,reason_code:'document_collection'}),
          item('linked-ref','Lié.md','already_linked',{workspace_file_id:'file-a'}),item('pdf-ref','Source.pdf','adoptable',{source_extension:'.pdf'}),
          item('collision-ref','Conflit.md','collision'),item('bad-ref','<b>Incompatible</b>','incompatible'),
          item('broken-folder','Dossier incompatible','incompatible',{is_collection:true,reason_code:'document_remote_incompatible'})]});
      }
      if(url.pathname.endsWith('/documents/adopt')){
        state.calls.push({path:url.pathname,method,body});await wait('adopt');
        if(state.uncertain) {if(state.commitUncertain)state.adopted=true;return json({ok:false,reason_code:'document_adoption_commit_unknown'},503);}
        if(state.reject) return json({ok:false,reason_code:'document_local_collision'},409);
        state.adopted=true;return json({ok:true,workspace_folder_id:'folder-a',workspace_file_id:body.resource_ref==='linked-ref'?'file-a':file.id,category:'adopted',file},201);
      }
      if(url.pathname==='/api/workspace-folders/folder-a/files'){
        state.calls.push({path:url.pathname,method});await wait('inventory');
        if(state.failInventory && state.adopted) return json({ok:false,reason_code:'workspace_files_lookup_failed'},503);
        const response=await base(input,init);const data=await response.json();
        if(state.adopted && !state.linked)data.items.push({...file,source_extension:state.pdf?'.pdf':'.md'});
        return json(data);
      }
      return base(input,init);
    };
  })();`;
}
module.exports={adoptionScript,exactPath};
