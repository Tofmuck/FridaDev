'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');
const { openWorkshop } = require('./helpers/document_workshop_fixture.js');
const { adoptionScript } = require('./helpers/document_adoption_fixture.js');

// Deliberately hostile synthetic diagnostics must never become product text.
const RAW = '<img src=x onerror="window.__rawRendered=true"> RAW_PRIVATE_DIAGNOSTIC';
const cases = [
  ['document_remote_identity_invalid', /Identité distante absente ou non vérifiable/],
  ['document_remote_version_invalid', /Version distante absente ou non vérifiable/],
  ['document_remote_size_invalid', /Taille du fichier absente ou invalide/],
  ['document_type_unsupported', /Format de fichier non pris en charge/],
  ['document_source_limit', /fichier ou son contenu extrait dépasse les limites de lecture/],
  ['document_remote_response_limit', /réponse distante dépasse les limites de lecture/],
  ['document_ocr_required', /reconnaissance de texte \(OCR\)/],
  ['document_extraction_incomplete', /texte ne peut pas être extrait intégralement/],
  ['document_archive_invalid', /structure du document est invalide ou non prise en charge/],
  ['document_parse_error', /fichier ne peut pas être lu dans ce format/],
  ['document_empty_text', /Aucun texte lisible/],
  ['document_remote_incompatible', /informations distantes ne permettent pas une lecture sûre/],
  ['document_path_invalid', /chemin ne respecte pas les règles du répertoire Documents/],
  ['document_path_segment_limit', /nom dépasse la longueur autorisée/],
  ['document_path_depth_limit', /chemin dépasse le nombre de sous-répertoires autorisé/],
  ['document_path_byte_limit', /chemin complet dépasse la longueur autorisée/],
  ['document_local_collision', /fichier local occupe déjà ce chemin/],
  ['document_remote_changed', /changé depuis sa lecture.*Actualisez la collection/],
  ['document_remote_missing', /disparu ou a été déplacée.*Actualisez la collection/],
  ['document_reference_invalid', /référence de document n’est plus valide.*Actualisez la collection/],
];
const retryCases = [
  ['document_remote_unavailable', /lecture distante est actuellement indisponible/],
  ['document_runtime_unavailable', /lecture de ce format est actuellement indisponible/],
  ['document_source_processing_failed', /lecture complète du document a échoué/],
  ['document_adoption_storage_unavailable', /adoption n’a pas pu être enregistrée/],
  ['document_context_scope_changed', /contexte documentaire a changé.*rouvrez l’atelier/],
  ['document_context_scope_mismatch', /contexte documentaire a changé.*rouvrez l’atelier/],
  ['document_adoption_commit_unknown', /Résultat de l’adoption incertain.*Aucun nouvel essai automatique.*Actualiser/],
];
function reasonScript() {
  return adoptionScript() + `(() => {
    const previous=window.fetch;
    const raw=${JSON.stringify(RAW)};
    const unsafe={error:raw,message:raw,detail:raw,content:raw,href:'https://synthetic.invalid/RAW_PRIVATE_DIAGNOSTIC'};
    const failureStatuses={document_remote_missing:404,document_local_collision:409,document_remote_changed:409,
      document_reference_invalid:409,document_context_scope_changed:409,document_context_scope_mismatch:409,
      document_source_limit:413,document_remote_response_limit:413,document_path_segment_limit:413,
      document_path_depth_limit:413,document_path_byte_limit:413,document_remote_unavailable:503,
      document_runtime_unavailable:503,document_adoption_storage_unavailable:503,document_adoption_commit_unknown:503};
    const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
    window.fetch=async(input,init={})=>{
      const state=window.__m2,url=new URL(input,location.origin),method=init.method||'GET';
      const lane=url.pathname.endsWith('/remote')?'remote':url.pathname.endsWith('/adopt')?'adopt':null;
      if(lane && (Object.hasOwn(state,lane+'Failure') || state[lane+'Throw'])){
        state.calls.push({path:url.pathname,method,query:Object.fromEntries(url.searchParams),body:typeof init.body==='string'?JSON.parse(init.body):null});
        if(state[lane+'Throw'])throw new Error(raw);
        const reason=state[lane+'Failure'];
        const status=typeof reason==='string' && Object.hasOwn(failureStatuses,reason)?failureStatuses[reason]:422;
        return json({ok:false,reason_code:reason,...unsafe},status);
      }
      const response=await previous(input,init);
      if(lane==='remote' && state.reasonRows){const payload=await response.json();payload.items=state.reasonRows.map((reason,index)=>({reference:'reason-'+index,name:'Cas '+index+'.md',relative_path:'Documents/Cas '+index+'.md',is_collection:false,category:reason==='document_local_collision'?'collision':'incompatible',reason_code:reason,...unsafe}));return json(payload);}
      return response;
    };
  })();`;
}
const setup = { mockScript: reasonScript(), beforePage: async page => page.setDefaultTimeout(4000) };
async function editing(page) {
  await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path.endsWith('/active-documents')));
  await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state=editing]');
}
async function settled(page) { await page.waitForSelector('#documentWorkshopBrowse:not([disabled])'); }
async function noRaw(page) {
  assert.doesNotMatch(await page.locator('#documentWorkshop').textContent(),/RAW_PRIVATE_DIAGNOSTIC|synthetic\.invalid/);
  assert.equal(await page.locator('#documentWorkshop img').count(),0);
  assert.equal(await page.evaluate(()=>window.__rawRendered===true),false);
}

test('M2 G-R1 incompatible rows expose precise fixed reasons without recommending futile refresh',async()=>{
  await openBrowserPage(setup,async page=>{
    await editing(page);await page.evaluate(reasons=>window.__m2.reasonRows=reasons,cases.map(([reason])=>reason));
    await page.click('#documentWorkshopBrowse');await settled(page);
    for(const [index,[reason,expected]] of cases.entries()){
      const row=page.locator('#documentRemoteList li').nth(index);assert.match(await row.textContent(),expected,reason);
      assert.equal(await row.locator('button').count(),0);
      if(index<17)assert.doesNotMatch(await row.textContent(),/Actualis|réessay/i,reason);
    }
    await noRaw(page);assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),0);
  });
});

test('M2 G-R1 navigation failures distinguish fixed limits and conflicts without partial results',async()=>{
  await openBrowserPage(setup,async page=>{
    await editing(page);
    for(const [reason,expected] of [...cases,...retryCases]){
      const before=await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/remote')).length);
      await page.evaluate(reason=>window.__m2.remoteFailure=reason,reason);await page.click('#documentWorkshopBrowse');await settled(page);
      assert.match(await page.locator('#documentRemoteStatus').textContent(),expected,reason);
      assert.equal(await page.locator('#documentRemoteList li').count(),0);await noRaw(page);
      assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/remote')).length),before+1);
    }
  });
});

test('M2 G-R1 adoption failures preserve useful reasons, uncertainty and one POST per explicit attempt',async()=>{
  await openBrowserPage(setup,async page=>{
    await editing(page);await page.fill('#message','Brouillon conservé');
    for(const [index,[reason,expected]] of [...cases,...retryCases].entries()){
      await page.click('#documentWorkshopBrowse');await settled(page);
      await page.evaluate(reason=>window.__m2.adoptFailure=reason,reason);
      await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).click();await settled(page);
      assert.match(await page.locator('#documentRemoteStatus').textContent(),expected,reason);
      if(index<17)assert.doesNotMatch(await page.locator('#documentRemoteStatus').textContent(),/Actualis|réessay/i,reason);
      assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),index+1);
      assert.equal(await page.locator('#documentRemoteList button').count(),0);await noRaw(page);
    }
    assert.equal(await page.locator('#message').inputValue(),'Brouillon conservé');assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');
    assert.equal(await page.evaluate(()=>window.__m1.selections.length),0);assert.equal(await page.locator('#log .msg').count(),0);
  });
});

test('M2 G-R1 unknown and inherited keys use generic fixed fallbacks; raw transport errors stay private',async()=>{
  await openBrowserPage(setup,async page=>{
    await editing(page);await page.evaluate(()=>window.__m2.reasonRows=['unknown_reason','constructor','toString',null,{}]);
    await page.click('#documentWorkshopBrowse');await settled(page);
    for(const row of await page.locator('#documentRemoteList li').all())assert.match(await row.textContent(),/Cette ressource ne peut pas être adoptée/);
    await noRaw(page);await page.evaluate(()=>delete window.__m2.reasonRows);
    for(const reason of ['unknown_reason','constructor','toString',null,{}]){
      await page.evaluate(reason=>window.__m2.remoteFailure=reason,reason);await page.click('#documentWorkshopBrowse');await settled(page);
      assert.match(await page.locator('#documentRemoteStatus').textContent(),/Impossible d’(?:obtenir|actualiser) la liste complète/);await noRaw(page);
      await page.evaluate(reason=>{delete window.__m2.remoteFailure;window.__m2.adoptFailure=reason;},reason);await page.click('#documentWorkshopBrowse');await settled(page);
      await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).click();await settled(page);
      assert.match(await page.locator('#documentRemoteStatus').textContent(),/Adoption non confirmée/);await noRaw(page);
    }
    await page.evaluate(()=>{delete window.__m2.adoptFailure;window.__m2.remoteThrow=true;});await page.click('#documentWorkshopBrowse');await settled(page);await noRaw(page);
    await page.evaluate(()=>{window.__m2.remoteThrow=false;window.__m2.adoptThrow=true;});await page.click('#documentWorkshopBrowse');await settled(page);
    await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).click();await settled(page);
    assert.match(await page.locator('#documentRemoteStatus').textContent(),/Résultat de l’adoption incertain/);await noRaw(page);
  });
});
