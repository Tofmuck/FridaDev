'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {openBrowserPage}=require('./helpers/browser_test_helpers.js');
const {showFolder,closeSidebar,openWorkshop}=require('./helpers/document_workshop_fixture.js');
const {adoptionScript,exactPath}=require('./helpers/document_adoption_fixture.js');
const setup=(extra={})=>({mockScript:adoptionScript(),beforePage:async page=>{page.setDefaultTimeout(4000);},...extra});
async function ready(page){await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));}
async function editing(page){await ready(page);await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state=editing]');}
async function browse(page){await page.click('#documentWorkshopBrowse');await page.waitForSelector('#documentRemoteList button');}
async function nested(page){await browse(page);await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();await page.getByRole('button',{name:'Adopter Étude  française.md',exact:true}).waitFor();}
const adopted=page=>page.getByRole('button',{name:'Adopter Étude  française.md',exact:true});

for(const mobile of [false,true])for(const theme of ['light','dark'])test(`M2 explicit lazy navigation and adoption in mounted app: ${mobile?'mobile':'desktop'} ${theme}`,async()=>{
  await openBrowserPage(setup({beforePage:async page=>{page.setDefaultTimeout(4000);await page.setViewportSize({width:mobile?390:1280,height:mobile?844:900});await page.addInitScript(t=>localStorage.setItem('frida.chat.theme',t),theme);}}),async page=>{
    await ready(page);assert.match(await page.title(),/Frida/);
    await showFolder(page,'folder-a');await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input').check();await closeSidebar(page);
    await page.click('#btnActiveDocument');assert.equal(await page.locator('#documentFileMenu button').count(),2);
    assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.includes('/documents/')).length),0);
    await page.click('[data-file-action=workshop]');await page.waitForSelector('#documentWorkshop[data-state=editing]');
    assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.includes('/documents/')).length),0);
    assert.equal(await page.locator('#documentWorkshopBrowse').count(),1);
    await browse(page);
    assert.deepEqual(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/remote')).map(c=>c.query)),[{context_id:'context-0'}]);
    for(const category of ['Déjà lié','Adoptable','Collision locale','Incompatible'])assert.ok((await page.locator('#documentRemoteList').textContent()).includes(category));
    assert.equal(await page.locator('#documentRemoteList b, #documentRemoteList img').count(),0);
    assert.equal(await page.getByRole('button',{name:'Ouvrir Dossier incompatible',exact:true}).count(),0);
    await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();await adopted(page).waitFor();
    assert.equal(await page.locator('#documentRemotePath').textContent(),'Documents/Sous  dossier');
    assert.ok((await page.locator('#documentRemoteList').textContent()).includes(exactPath));
    await page.fill('#message','Brouillon intact');await adopted(page).click();
    await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
    assert.deepEqual(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).map(c=>c.body)),[{context_id:'context-0',resource_ref:'nested-ref'}]);
    assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');
    assert.equal(await page.locator('#documentWorkshopTarget option[value="adopted-file"]').textContent(),exactPath);
    assert.equal(await page.evaluate(()=>window.__m1.selections.length),1);
    assert.equal(await page.locator('#log .msg').count(),0);
    assert.equal(await page.locator('#activeDocumentsList').textContent(),'');
    await page.click('#ask button[type=submit]');assert.equal(await page.locator('#message').inputValue(),'Brouillon intact');
    assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.path==='/api/chat').length),0);
    const boxes=await page.evaluate(()=>['documentWorkshop','message','btnActiveDocument'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right};}));
    assert.ok(boxes[0].top>=0);assert.ok(boxes[0].bottom<=boxes[1].top);assert.ok(boxes[0].bottom<=boxes[2].top);
    await showFolder(page,'folder-a');const row=page.locator('.workspace-folder-file').filter({hasText:exactPath});
    assert.equal(await row.locator('.workspace-folder-file-select').isChecked(),false);assert.equal(await row.locator('.workspace-folder-file-delete').isDisabled(),true);
    assert.equal(await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input').isChecked(),true);
    await closeSidebar(page);await page.click('#documentWorkshopExit');await page.click('#ask button[type=submit]');await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/chat'));
  });
});

for(const incomplete of [false,true])test(`M2 refuses oversized or incomplete listing (${incomplete}) without partial success`,async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await page.evaluate(flag=>window.__m2[flag?'incomplete':'overflow']=true,incomplete);await page.click('#documentWorkshopBrowse');
    await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus')?.textContent.includes('liste complète'));
    assert.equal(await page.locator('#documentRemoteList li').count(),0);assert.equal(await page.locator('#documentRemoteStatus img').count(),0);
  });
});

for(const operation of ['root','sub-ref','adopt','inventory'])test(`M2 late ${operation} cannot reopen or repopulate after exit`,async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);
    if(operation==='sub-ref')await browse(page);else if(['adopt','inventory'].includes(operation))await nested(page);
    await page.evaluate(key=>window.__m2.deferred[key]=true,operation);
    if(operation==='root')await page.click('#documentWorkshopBrowse');else if(operation==='sub-ref')await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();else await adopted(page).click();
    await page.waitForFunction(key=>!!window.__m2.release[key],operation);
    const beforeFinished=await page.evaluate(key=>window.__m2.finished.filter(k=>k===key).length,operation);
    await page.click('#documentWorkshopExit');await page.evaluate(key=>window.__m2.release[key](),operation);
    await page.waitForFunction(({key,count})=>window.__m2.finished.filter(k=>k===key).length>count,{key:operation,count:beforeFinished});
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);assert.equal(await page.locator('#documentRemoteList li').count(),0);
    assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),0);
    if(operation==='inventory'){
      await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state=editing]');
      assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),0);
    }
  });
});

test('M2 invalidated frozen target keeps a visible refusal after adoption reread',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await page.selectOption('#documentWorkshopTarget','file-a');await page.waitForFunction(()=>window.__m1.contexts.length===2);
    await nested(page);await page.evaluate(()=>window.__m2.failRead=true);await adopted(page).click();
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state!=='editing');
    assert.match(await page.locator('#documentWorkshopStatus').textContent(),/Impossible d’ouvrir ce contexte/);
    assert.equal(await page.locator('#documentWorkshopTarget').isDisabled(),true);
    assert.equal(await page.locator('#documentWorkshopBrowse').isDisabled(),true);
  });
});

for(const operation of ['root','adopt','inventory'])test(`M2 late ${operation} loses authority on conversation navigation`,async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);if(operation!=='root')await nested(page);
    await page.evaluate(key=>window.__m2.deferred[key]=true,operation);
    if(operation==='root')await page.click('#documentWorkshopBrowse');else await adopted(page).click();
    await page.waitForFunction(key=>!!window.__m2.release[key],operation);
    await showFolder(page,'folder-b');await page.click('#threads li[data-conversation-id="conv-b"]');await closeSidebar(page);
    await page.evaluate(key=>window.__m2.release[key](),operation);
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-b/messages'));
    assert.equal(await page.locator('#documentWorkshop').isVisible(),false);assert.equal(await page.locator('#documentRemoteList li').count(),0);
    await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state=editing]');
    assert.equal(await page.locator('#documentWorkshopFolder').inputValue(),'folder-b');assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),0);
    assert.equal(await page.evaluate(()=>window.__m1.selections.length),0);
  });
});

test('M2 context target change invalidates pending root and browsing needs a new explicit click',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await page.evaluate(()=>window.__m2.deferred.root=true);await page.click('#documentWorkshopBrowse');await page.waitForFunction(()=>!!window.__m2.release.root);
    await page.selectOption('#documentWorkshopTarget','file-a');await page.waitForFunction(()=>window.__m1.contexts.length===2);await page.evaluate(()=>window.__m2.release.root());
    await page.waitForFunction(()=>window.__m2.finished.includes('root'));assert.equal(await page.locator('#documentRemoteBrowser').isVisible(),false);assert.equal(await page.locator('#documentRemoteList li').count(),0);
    assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'file-a');assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/remote')).length),1);
  });
});

test('M2 explicit existing-link adoption keeps the workspace ID and never selects it',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await browse(page);await page.evaluate(()=>window.__m2.linked=true);
    await page.getByRole('button',{name:'Actualiser l’adoption Lié.md',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Adoption enregistrée'));
    assert.equal(await page.locator('#documentWorkshopTarget option[value=file-a]').count(),1);assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');
    assert.equal(await page.evaluate(()=>window.__m1.selections.length),0);assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt'))[0].body.resource_ref),'linked-ref');
    assert.equal(await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).count(),1);
    assert.equal(await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).count(),1);
  });
});

test('M2 explicit refresh repairs inventory after acknowledged adoption without another POST',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await nested(page);await page.evaluate(()=>window.__m2.failInventory=true);await adopted(page).click();
    await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('inventaire indisponible'));
    await page.evaluate(()=>window.__m2.failInventory=false);await page.click('#documentRemoteRefresh');
    await page.getByRole('button',{name:'Actualiser l’adoption Étude  française.md',exact:true}).waitFor();assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),1);
    assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'');assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),1);
  });
});

test('M2 old navigation loses authority when root is explicitly reopened',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await browse(page);await page.evaluate(()=>window.__m2.deferred['sub-ref']=true);
    await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();await page.waitForFunction(()=>!!window.__m2.release['sub-ref']);
    await page.click('#documentRemoteRoot');await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).waitFor();
    await page.evaluate(()=>window.__m2.release['sub-ref']());await page.waitForFunction(()=>window.__m2.finished.includes('sub-ref'));
    assert.equal(await page.locator('#documentRemotePath').textContent(),'Documents');assert.equal(await adopted(page).count(),0);
  });
});

for(const uncertain of [false,true])test(`M2 double activation and ${uncertain?'uncertain':'rejected'} adoption never replay POST`,async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await nested(page);await page.evaluate(flag=>{window.__m2.deferred.adopt=true;window.__m2[flag?'uncertain':'reject']=true;},uncertain);
    await adopted(page).dblclick();await page.waitForFunction(()=>!!window.__m2.release.adopt);await page.evaluate(()=>window.__m2.release.adopt());
    await page.waitForFunction(uncertain=>document.querySelector('#documentRemoteStatus').textContent.includes(uncertain?'Actualiser':'Un fichier local'),uncertain);
    assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),1);assert.equal(await adopted(page).count(),0);
    await page.click('#documentRemoteRefresh');await adopted(page).waitFor();assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),1);
  });
});

test('M2 PDF adoption remains only a source, existing explicit target stays unchanged',async()=>{
  await openBrowserPage(setup(),async page=>{await editing(page);await page.selectOption('#documentWorkshopTarget','file-a');await page.waitForFunction(()=>window.__m1.contexts.length===2);
    await page.evaluate(()=>window.__m2.pdf=true);await browse(page);await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).click();
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/document-workshop/contexts/context-1'));
    await page.waitForSelector('#documentWorkshop[data-state=editing]');assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),'file-a');
    assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),0);assert.equal(await page.evaluate(()=>window.__m1.selections.length),0);
  });
});

for(const scenario of ['pending-exit','uncertain-context','inventory-context'])test(`M2 R1 explicit read reconciles affected inventory across ${scenario} without adoption replay`,async()=>{
  await openBrowserPage(setup(),async page=>{
    await ready(page);await showFolder(page,'folder-a');await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input').check();await closeSidebar(page);
    await editing(page);await nested(page);
    await page.evaluate(mode=>{
      if(mode==='pending-exit')window.__m2.deferred.adopt=true;
      if(mode==='uncertain-context'){window.__m2.uncertain=true;window.__m2.commitUncertain=true;}
      if(mode==='inventory-context')window.__m2.failInventory=true;
    },scenario);
    await adopted(page).click();
    if(scenario==='pending-exit'){
      await page.waitForFunction(()=>!!window.__m2.release.adopt);await page.click('#documentWorkshopExit');await page.evaluate(()=>window.__m2.release.adopt());await page.waitForFunction(()=>window.__m2.adopted);
      assert.equal(await page.locator('#documentWorkshop').isVisible(),false);
      await openWorkshop(page);await page.waitForSelector('#documentWorkshop[data-state=editing]');
    }else{
      await page.waitForFunction(()=>document.querySelector('#documentRemoteStatus').textContent.includes('Actualiser'));
      await page.evaluate(()=>window.__m2.failInventory=false);
      await page.selectOption('#documentWorkshopTarget','file-a');await page.waitForFunction(()=>window.__m1.contexts.length===2 && document.querySelector('#documentWorkshop').dataset.state==='editing');
    }
    // Teardown and late callbacks must still not publish the old response.
    assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),0);
    const before=await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/files')).length);
    await page.click('#documentWorkshopBrowse');await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
    assert.equal(await page.locator('#documentWorkshopTarget option[value=adopted-file]').count(),1);
    assert.equal(await page.locator('#documentWorkshopTarget').inputValue(),scenario==='pending-exit'?'':'file-a');
    assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/files')).length),before+1);
    if(scenario==='pending-exit'){
      await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();await page.getByRole('button',{name:'Actualiser l’adoption Étude  française.md',exact:true}).waitFor();
      await page.click('#documentRemoteRefresh');await page.getByRole('button',{name:'Actualiser l’adoption Étude  française.md',exact:true}).waitFor();
    }
    assert.equal(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/adopt')).length),1);
    assert.equal(await page.evaluate(()=>window.__m1.selections.length),1);
    assert.equal(await page.evaluate(()=>window.__m1.calls.filter(c=>c.path==='/api/chat').length),0);
    assert.equal(await page.locator('#log .msg').count(),0);
    await showFolder(page,'folder-a');const row=page.locator('.workspace-folder-file').filter({hasText:exactPath});
    assert.equal(await row.locator('.workspace-folder-file-select').isChecked(),false);
    assert.equal(await page.locator('.workspace-folder-file').filter({hasText:'Ébauche.md'}).first().locator('input').isChecked(),true);
  });
});

test('M2 R2 root refresh and parent use their opaque root reference and actual root items',async()=>{
  await openBrowserPage(setup(),async page=>{
    await editing(page);await browse(page);await page.click('#documentRemoteRefresh');await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
    assert.equal(await page.locator('#documentRemotePath').textContent(),'Documents');
    assert.equal(await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).count(),1);
    assert.equal(await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).count(),1);
    assert.equal(await page.locator('#documentRemoteBack').isDisabled(),true);
    await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).click();await adopted(page).waitFor();
    assert.equal(await page.locator('#documentRemotePath').textContent(),'Documents/Sous  dossier');
    await page.click('#documentRemoteBack');await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
    assert.equal(await page.locator('#documentRemotePath').textContent(),'Documents');
    assert.equal(await page.getByRole('button',{name:'Ouvrir Sous  dossier',exact:true}).count(),1);
    assert.equal(await page.getByRole('button',{name:'Adopter Source.pdf',exact:true}).count(),1);assert.equal(await adopted(page).count(),0);
    assert.equal(await page.locator('#documentRemoteBack').isDisabled(),true);
    assert.deepEqual(await page.evaluate(()=>window.__m2.calls.filter(c=>c.path.endsWith('/remote')).map(c=>c.query)),[
      {context_id:'context-0'},{context_id:'context-0',collection_ref:'root-ref'},
      {context_id:'context-0',collection_ref:'sub-ref'},{context_id:'context-0',collection_ref:'root-ref'}]);
  });
});
