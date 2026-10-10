'use strict';
// Autonomous diagnostic: historical helper extraction, real DOM/CSS/handlers,
// fetch simulated by the unchanged M4 fixture. No historical file is rewritten.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');
const root = path.resolve(__dirname, '../../..');
const historical = path.join(root, 'app/tests/integration/frontend_browser/test_frontend_browser_document_preparation_m4.js');
const source = fs.readFileSync(historical, 'utf8');
const anchor = 'for(const mobile of [false,true])';
assert.equal(source.split(anchor).length, 2);
const helperPrefix = source.slice(0, source.indexOf(anchor));
const sandbox = { require: createRequire(historical), module: { exports: {} } };
vm.runInNewContext(helperPrefix + '\nmodule.exports={preparationScript,ready,send,openWorkshop,openBrowserPage};', sandbox, { filename: historical });
const { preparationScript, ready, send, openWorkshop, openBrowserPage } = sandbox.module.exports;
const mode = process.argv[2] || 'observe';
assert.ok(['observe','witness','adverse','adverse-reduced'].includes(mode));
const controlled=mode!=='observe';
const reduced=mode==='adverse-reduced';
const digest = text => crypto.createHash('sha256').update(text).digest('hex');
const patches = {};
function change(text, from, to) {
  assert.equal(text.split(from).length, 2, from);
  return text.replace(from, to);
}
function instrument(filename, text) {
  const original = text;
  if (filename === 'app.js' && !reduced) {
    text = change(text, '  async function submitCanonicalChatMessage(text, inputMode) {',
      '  async function submitCanonicalChatMessage(text, inputMode) {\n    window.__obsM4.trace("canonical-enter", {inputMode, busy:chatRequestInFlight});');
    text = change(text, '      documentSubmission = documentWorkshopController.prepareSubmission?.({ inputMode, incompatibleModes });',
      '      window.__obsM4.trace("incompatible-computed", {incompatibleModes});\n      documentSubmission = documentWorkshopController.prepareSubmission?.({ inputMode, incompatibleModes });\n      window.__obsM4.trace("prepare-result", {ok:documentSubmission?.ok, reason:documentSubmission?.reason});');
    text = change(text, '        documentWorkshopController.refuseSubmission(documentSubmission);',
      '        window.__obsM4.trace("refuse-call", {reason:documentSubmission?.reason});\n        documentWorkshopController.refuseSubmission(documentSubmission);');
    text = change(text, '    addMsg("user", text);',
      '    window.__obsM4.trace("optimistic-user-before");\n    addMsg("user", text);\n    window.__obsM4.trace("optimistic-user-after");');
  } else if (filename === 'chat_document_workshop.js' && !reduced) {
    text = change(text, "  function render(message = '') {", "  function render(message = '') {\n    window.__obsM4.trace('workshop-render', {visible,busy,contextId:context?.id||null,contextState:context?.state||null,prepare:context?.capabilities?.prepare||false,currentScope:currentScope()});");
    text = change(text, '  function exit({ focus = true } = {}) {', "  function exit({ focus = true } = {}) {\n    window.__obsM4.trace('workshop-exit', {focus,stack:new Error().stack});");
    text = change(text, '  function scopeChanged() {', "  function scopeChanged() {\n    window.__obsM4.trace('scope-change', {visible,currentScope:currentScope(),pendingScope,contextId:context?.id||null});");
    text = change(text, '    blocksSubmission: () => visible,', "    blocksSubmission: () => (window.__obsM4.trace('blocks-submission', {visible}), visible),");
    text = change(text, '    prepareSubmission({ inputMode, incompatibleModes = false } = {}) {', "    prepareSubmission({ inputMode, incompatibleModes = false } = {}) {\n      window.__obsM4.trace('prepare-enter', {visible,busy,contextId:context?.id||null,contextState:context?.state||null,inputMode,incompatibleModes});");
  } else if (filename === 'chat_image_generation.js' && reduced) {
    text=change(text, 'window.setTimeout(() => promptEl.focus(), 0);', 'window.__obsM4.scheduleFocus(() => promptEl.focus());');
  } else if (filename === 'chat_image_generation.js') {
    text = change(text, '  const open = () => {', "  const open = () => {\n    window.__obsM4.trace('image-open-enter', {open:state.open});");
    text = change(text, '      window.setTimeout(() => promptEl.focus(), 0);', "      window.setTimeout(() => {window.__obsM4.trace('image-focus-before');promptEl.focus();window.__obsM4.trace('image-focus-after');}, 0);");
    text = change(text, '  const submit = async () => {', "  const submit = async () => {\n    window.__obsM4.trace('image-submit-enter', {busy:state.busy});");
  }
  if(controlled && !reduced && filename==='chat_image_generation.js') {
    text=change(text, "window.setTimeout(() => {window.__obsM4.trace('image-focus-before');promptEl.focus();window.__obsM4.trace('image-focus-after');}, 0);", "window.__obsM4.scheduleFocus(() => {window.__obsM4.trace('image-focus-before');promptEl.focus();window.__obsM4.trace('image-focus-after');});");
  }
  assert.notEqual(text, original);
  patches[filename] = { original_sha256: digest(original), instrumented_sha256: digest(text), original_bytes:Buffer.byteLength(original), instrumented_source:text };
  return text;
}
const init = `;(() => {
  const events=[];
  const snapshot=()=>({draftLength:document.querySelector('#message')?.value.length||0,
    draftIntact:document.querySelector('#message')?.value==='Brouillon intact',
    workshopHidden:document.querySelector('#documentWorkshop')?.hidden??null,
    workshopState:document.querySelector('#documentWorkshop')?.dataset.state||null,
    imageHidden:document.querySelector('#imageGenerationPanel')?.classList.contains('hidden')??null,
    imageExpanded:document.querySelector('#btnImageGeneration')?.getAttribute('aria-expanded')||null,
    imagePromptLength:document.querySelector('#imageGenerationPrompt')?.value.length||0,
    imagePromptHasDraft:document.querySelector('#imageGenerationPrompt')?.value==='Brouillon intact',
    optimisticUsers:document.querySelectorAll('#log .msg.me').length,
    activeElement:document.activeElement?.id||document.activeElement?.tagName||null});
  const trace=(kind,data={})=>events.push({seq:events.length,ms:performance.now(),kind,...data,snapshot:snapshot()});
  window.__obsM4={events,trace,snapshot,focusArmed:false,focusReached:false,focusReleased:false,insertReached:false};
  window.__obsM4.armFocus=()=>{if(window.__obsM4.focusArmed)throw new Error('focus-already-armed');window.__obsM4.focusArmed=true;trace('focus-barrier-armed');};
  window.__obsM4.scheduleFocus=callback=>{
    if(!window.__obsM4.focusArmed)throw new Error('focus-not-armed');
    window.setTimeout(()=>{
      if(window.__obsM4.focusReached)throw new Error('focus-reached-twice');
      window.__obsM4.focusReached=true;trace('focus-barrier-reached');
      window.__obsM4.releaseFocus=()=>{
        if(window.__obsM4.focusReleased)throw new Error('focus-released-twice');
        window.__obsM4.focusReleased=true;trace('focus-release-before');callback();trace('focus-release-after');
      };
    },0);
  };
  if(!${reduced}) {
  const descriptor=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value');
  Object.defineProperty(HTMLTextAreaElement.prototype,'value',{...descriptor,set(value){
    if(this.id==='message')trace('draft-write-before',{nextLength:String(value).length,stack:new Error().stack});
    descriptor.set.call(this,value);
    if(this.id==='message')trace('draft-write-after');
  }});
  const fetchBase=window.fetch;
  window.fetch=async(input,options={})=>{
    const pathname=new URL(input,location.origin).pathname;
    const body=typeof options.body==='string'?JSON.parse(options.body):null;
    trace('fetch-call',{pathname,method:options.method||'GET',documentary:Boolean(body?.document_context_id)});
    const response=await fetchBase(input,options);
    trace('fetch-response',{pathname,status:response.status});
    return response;
  };
  for(const type of ['pointerdown','pointerup','click','submit','input','focusin']) document.addEventListener(type,event=>{
    const el=event.target;trace('dom-'+type,{target:el.id||el.closest?.('button')?.id||el.tagName,form:el.form?.id||null,trusted:event.isTrusted});
  },true);
  }
})();`;
const result = { mode, controlled, reduced, transport:'historical M4 simulated fetch; static HTTP files only; no Flask/DAV/provider', helper_prefix_sha256:digest(helperPrefix), historical_sha256:digest(source), patches, events:[], outcome:null };
(async () => {
  let livePage=null, releaseInsert=null, pendingSend=null, originalInsert=null, Keyboard=null;
  if(controlled){
    // In-memory hook at the real Playwright textarea fill -> keyboard boundary.
    const modulePath=path.join(root,'node_modules/playwright-core/lib/server/input.js');
    Keyboard=require(modulePath).Keyboard;originalInsert=Keyboard.prototype._insertText;
    result.keyboard_hook={module_sha256:digest(fs.readFileSync(modulePath)),original_method:String(originalInsert)};
    Keyboard.prototype._insertText=async function(progress,text){
      if(text==='Brouillon intact' && livePage){
        const before=await livePage.evaluate(()=>window.__obsM4.snapshot());
        assert.equal(before.activeElement,'message','real fill must have focused message before insertion');
        const held=mode!=='witness'?new Promise(resolve=>releaseInsert=resolve):null;
        await livePage.evaluate(()=>{window.__obsM4.insertReached=true;window.__obsM4.trace('insert-barrier-reached');});
        if(held)await held;
        await livePage.evaluate(()=>window.__obsM4.trace('real-insert-before'));
        const value=await originalInsert.call(this,progress,text);
        await livePage.evaluate(()=>window.__obsM4.trace('real-insert-after'));
        return value;
      }
      return originalInsert.call(this,progress,text);
    };
  }
  try {
    await openBrowserPage({mockScript:preparationScript()+init,beforePage:async page=>{
      const selected=reduced?/\/chat_image_generation\.js$/:/\/(app|chat_document_workshop|chat_image_generation)\.js$/;
      await page.route(selected,async route=>{
        const filename=new URL(route.request().url()).pathname.split('/').pop();
        const text=fs.readFileSync(path.join(root,'app/web',filename),'utf8');
        await route.fulfill({status:200,contentType:'application/javascript',body:instrument(filename,text)});
      });
    }}, async page => {
      result.versions={node:process.version,playwright:require('playwright/package.json').version,chromium:page.context().browser().version()};
      try {
        livePage=page;
        await ready(page);await openWorkshop(page);
        if(controlled){
          await page.waitForFunction(()=>document.querySelector('#documentWorkshop').dataset.state==='editing');
          await page.evaluate(()=>window.__obsM4.armFocus());
        }
        await page.click('#btnImageGeneration');
        if(controlled){
          await page.waitForFunction(()=>window.__obsM4.focusReached);
          if(mode==='witness'){
            await page.evaluate(()=>{window.__obsM4.trace('independent-focus-release-before-fill');window.__obsM4.releaseFocus();});
            await send(page,'Brouillon intact');
          }else{
            pendingSend=send(page,'Brouillon intact').then(()=>null,error=>error);
            await page.waitForFunction(()=>window.__obsM4.insertReached);
            assert.equal(typeof releaseInsert,'function');
            await page.evaluate(()=>{window.__obsM4.trace('independent-focus-release-during-fill');window.__obsM4.releaseFocus();});
            assert.equal(await page.evaluate(()=>document.activeElement.id),'imageGenerationPrompt');
            await page.evaluate(()=>window.__obsM4.trace('independent-insert-release'));
            releaseInsert();releaseInsert=null;
            const sendError=await pendingSend;pendingSend=null;if(sendError)throw sendError;
          }
        }else await send(page,'Brouillon intact');
        result.outcome=await page.evaluate(()=>({snapshot:window.__obsM4.snapshot(),normalCalls:window.__m4.normalCalls,documentaryCalls:window.__m4.documentaryCalls,imageCalls:window.__m4.calls.filter(c=>c.path==='/api/tools/image-generation').length,status:document.querySelector('#documentWorkshopStatus').textContent}));
        // All remaining original business assertions run before the expected
        // draft assertion, so the causal red does not conceal their branches.
        assert.equal(result.outcome.normalCalls,0);assert.equal(result.outcome.imageCalls,0);
        assert.equal(result.outcome.documentaryCalls,0);assert.equal(result.outcome.snapshot.optimisticUsers,0);
        assert.match(result.outcome.status,/incompatible|désactivez/i);
        assert.equal(result.outcome.snapshot.imageExpanded,'true');
        if(controlled){
          const state=await page.evaluate(()=>({focusReached:window.__obsM4.focusReached,focusReleased:window.__obsM4.focusReleased,insertReached:window.__obsM4.insertReached,snapshot:window.__obsM4.snapshot()}));
          assert.ok(state.focusReached && state.focusReleased && state.insertReached);
          assert.equal(state.snapshot.workshopState,'editing');
          assert.equal(state.snapshot.imagePromptHasDraft,mode!=='witness');
          assert.equal(state.snapshot.draftIntact,mode==='witness');
          assert.equal(state.snapshot.draftLength,mode==='witness'?16:0);
          result.causalChecks={status:'passed',...state};
        }
        assert.equal(await page.locator('#message').inputValue(),'Brouillon intact','#btnImageGeneration');
        assert.equal(await page.locator('#log .msg.me').count(),0);
        assert.equal(await page.evaluate(()=>window.__m4.documentaryCalls),0);
        assert.match(await page.locator('#documentWorkshopStatus').textContent(),/incompatible|désactivez/i);
        assert.equal(await page.locator('#btnImageGeneration').getAttribute('aria-expanded'),'true');
        assert.equal(result.outcome.normalCalls,0);assert.equal(result.outcome.imageCalls,0);
      } finally {
        if(releaseInsert){releaseInsert();releaseInsert=null;}
        if(pendingSend){await pendingSend;pendingSend=null;}
        result.events=await page.evaluate(()=>window.__obsM4.events);
        livePage=null;
      }
    });
    result.exit=0;
  } catch(error) {result.exit=1;result.error={name:error.name,message:error.message,actual:error.actual,expected:error.expected,stack:error.stack};}
  finally {if(Keyboard)Keyboard.prototype._insertText=originalInsert;}
  console.log('M4_DIAGNOSTIC '+JSON.stringify(result));
  process.exitCode=result.exit;
})();
