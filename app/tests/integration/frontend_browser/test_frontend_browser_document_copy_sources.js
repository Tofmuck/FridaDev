'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');
const { mockScript, showFolder, closeSidebar, openWorkshop } = require('./helpers/document_workshop_fixture.js');

const SOURCE = 'a1111111-1111-4111-8111-111111111111';
function sourceScript({ confirm, update }) {
  return mockScript() + `;(() => {
    const baseFetch=window.fetch;
    window.__copyRequests=[];
    const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
    window.fetch=async(input,init={})=>{
      const path=new URL(input,location.origin).pathname;
      if(path==='/api/chat') {
        window.__copyRequests.push(JSON.parse(init.body));
        return json({ok:false,reason_code:'document_preparation_failed'},503);
      }
      const response=await baseFetch(input,init);
      if(path.startsWith('/api/document-workshop/contexts')) {
        const data=await response.json();
        if(data.context) data.context.capabilities={prepare:true,confirm:${confirm},update:${update},formats:['markdown','docx']};
        return json(data,response.status);
      }
      if(path.endsWith('/files')) {
        const data=await response.json();
        data.items.forEach(item=>Object.assign(item,{id:'${SOURCE}',display_name:'Original.docx',source_extension:'.docx',document_relative_path:'Documents/Original.docx'}));
        return json(data);
      }
      return response;
    };
  })();`;
}

for (const scenario of [
  { name:'target only desktop', confirm:true, update:true, selected:false, mobile:false },
  { name:'explicit source phone', confirm:true, update:true, selected:true, mobile:true },
  { name:'copy without update', confirm:true, update:false, selected:false, mobile:false },
  { name:'preparation without writing', confirm:false, update:false, selected:false, mobile:false },
]) test(`M9A copy guidance and unchanged selection: ${scenario.name}`, async()=>{
  await openBrowserPage({mockScript:sourceScript(scenario),beforePage:async page=>{
    page.setDefaultTimeout(5000);
    await page.setViewportSize({width:scenario.mobile?390:1280,height:900});
  }},async page=>{
    await page.waitForFunction(()=>window.__m1.calls.some(c=>c.path==='/api/conversations/conv-a/active-documents'));
    await showFolder(page,'folder-a');
    const checkbox=page.locator('.workspace-folder-file').filter({hasText:'Original.docx'}).first().locator('input[type=checkbox]');
    assert.equal(await checkbox.isChecked(),false);
    if(scenario.selected) await checkbox.check();
    await closeSidebar(page);
    await openWorkshop(page);
    await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing');
    if(scenario.update) {
      await page.selectOption('#documentWorkshopTarget',SOURCE);
      await page.waitForFunction(()=>window.__m1.contexts.length===2 && !document.querySelector('#documentWorkshopTarget').disabled);
    }
    assert.equal(await page.locator('#documentWorkshopStatus').isVisible(),true);
    const status=await page.locator('#documentWorkshopStatus').textContent();
    assert.match(status,/Pour copier, sélectionnez le document comme source de lecture/);
    if(scenario.update) assert.match(status,/Pour modifier, sélectionnez la cible explicite/);
    assert.doesNotMatch(status,/copie ou modification de la cible sélectionnée/);
    assert.deepEqual(await page.evaluate(()=>window.__m1.selections),scenario.selected?[SOURCE]:[]);
    assert.equal(await checkbox.isChecked(),scenario.selected);
    await page.fill('#message','Demande documentaire synthétique.');
    await page.click('#ask button[type=submit]');
    await page.waitForFunction(()=>window.__copyRequests.length===1);
    const requests=await page.evaluate(()=>window.__copyRequests);
    assert.equal(requests.length,1);
    assert.deepEqual(requests[0].document_source_file_ids,scenario.selected?[SOURCE]:[]);
    assert.equal(requests[0].document_context_id,scenario.update?'context-1':'context-0');
    assert.deepEqual(await page.evaluate(()=>window.__m1.selections),scenario.selected?[SOURCE]:[]);
  });
});
