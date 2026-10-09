'use strict';
// Owned proof copies exercise the actual M7 choose/wait and every retained assertion.
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const assert=require('node:assert/strict'),{performance}=require('node:perf_hooks');
const variant=process.env.OBS_VARIANT;
assert.ok(['completed','pending','no-wait','old-click'].includes(variant));
const original=path.resolve('app/tests/integration/frontend_browser/test_frontend_browser_document_http_m7.js');
const {closeSidebar}=require(path.join(path.dirname(original),'helpers/document_workshop_fixture.js'));
const controls=new WeakMap();
function observeBrowser(){
  const events=[];window.__m7NavigationProof={events};
  const snap=()=>{
    const menu=document.querySelector('.sidebar'),backdrop=document.querySelector('#sidebarBackdrop'),button=document.querySelector('#btnMenu');
    return {presentation:document.documentElement.dataset.presentationContext||'desktop',theme:document.documentElement.dataset.theme,
      viewport:[innerWidth,innerHeight],open:menu.classList.contains('open'),hidden:menu.getAttribute('aria-hidden'),
      expanded:button.getAttribute('aria-expanded'),backdropShow:backdrop.classList.contains('show'),backdropDisplay:getComputedStyle(backdrop).display,
      menu:menu.getBoundingClientRect().toJSON(),closeButton:document.querySelector('#btnSidebarClose').getBoundingClientRect().toJSON(),
      animations:menu.getAnimations().map(a=>({property:a.transitionProperty,state:a.playState,pending:a.pending})),
      selected:[...document.querySelectorAll('#threads li.active')].map(li=>li.dataset.conversationId)};
  };
  window.__m7NavigationProof.snapshot=snap;
  const remove=DOMTokenList.prototype.remove;
  DOMTokenList.prototype.remove=function(...args){
    const result=remove.apply(this,args);
    if(this===document.querySelector('.sidebar')?.classList&&args.includes('open'))events.push({kind:'native-close',at:performance.now(),stack:new Error().stack});
    return result;
  };
  document.addEventListener('transitionend',e=>{
    if(e.target===document.querySelector('.sidebar')&&e.propertyName==='transform')events.push({kind:'sidebar-transform-end',at:performance.now(),open:e.target.classList.contains('open')});
  },true);
  document.addEventListener('click',e=>{
    if(e.target.closest?.('#btnMenu,#btnSidebarClose'))events.push({kind:'native-button-click',at:performance.now(),id:e.target.closest('#btnMenu,#btnSidebarClose').id,trusted:e.isTrusted});
  },true);
}
const snapshot=page=>page.evaluate(()=>window.__m7NavigationProof.snapshot());
async function counts(page){
  const s=await (await page.request.get(process.env.M7_HTTP_BASE+'/__m6/state')).json();
  return {counts:s.counts,dav:s.dav.filter(d=>['PUT','DELETE','MKCOL'].includes(d.method)).map(d=>d.method)};
}
function assertClosed(s){
  assert.equal(s.presentation,'phone');assert.equal(s.open,false);assert.equal(s.hidden,'true');assert.equal(s.expanded,'false');
  assert.equal(s.backdropShow,false);assert.equal(s.backdropDisplay,'none');assert.ok(s.menu.right<=0);
  assert.equal(s.animations.some(a=>a.property==='transform'&&(a.state==='running'||a.pending)),false);
}
async function nativeClosed(page){
  // Ordering instrument only: delay observing the real helper until closure has
  // already ended. No CSS/state/response/event is fabricated.
  await page.waitForFunction(()=>{
    const s=document.querySelector('.sidebar');
    return !s.classList.contains('open')&&s.getBoundingClientRect().right<=0
      &&!s.getAnimations().some(a=>a.transitionProperty==='transform'&&(a.playState==='running'||a.pending));
  });
}
async function install(page,browser,{phone,theme}){
  const events=[],errors=[];const emit=(kind,data={})=>events.push({kind,at:performance.now(),...data});
  let heldResolve;const held=new Promise(resolve=>heldResolve=resolve);
  const c={phone,theme,events,emit,held,heldResolve,index:0,armed:false,complete:false,release:null};controls.set(page,c);
  await page.addInitScript(observeBrowser);
  page.on('pageerror',e=>errors.push({name:e.name}));
  for(const type of ['request','response'])page.on(type,value=>{
    const request=type==='request'?value:value.request(),url=new URL(request.url());
    if(url.pathname.startsWith('/api/'))emit(type,{method:request.method(),path:url.pathname,status:type==='response'?value.status():undefined});
  });
  if(['pending','no-wait'].includes(variant))await page.route('**/api/conversations/*/workspace-file-selections',async route=>{
    if(!c.armed||route.request().method()!=='GET'||!route.request().url().includes('/'+c.conversation+'/'))return route.continue();
    emit('real-GET-held');c.heldResolve();
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('owned-selection-gate-timeout')),5000);
      c.release=()=>{clearTimeout(timer);resolve();};
    });
    emit('real-GET-continued');await route.continue();
  });
  const close=browser.close.bind(browser);
  browser.close=async()=>{
    if(c.release)c.release();
    const report={variant,phone,theme,nodeOrigin:performance.timeOrigin,events,errors,complete:c.complete,captureErrors:[]};
    try{
      try{report.dom=await page.evaluate(()=>({events:window.__m7NavigationProof.events,snapshot:window.__m7NavigationProof.snapshot()}));}
      catch(e){report.captureErrors.push({stage:'dom',name:e.name});}
      try{report.finalCounts=await counts(page);}catch(e){report.captureErrors.push({stage:'counts',name:e.name});}
      fs.writeFileSync(`/evidence/fix-${variant}-${phone?'phone':'desktop'}-${theme}.json`,JSON.stringify(report,null,2)+'\n');
    }finally{await close();}
  };
}
async function beforeChoose(page,s,conversation,actual){
  const c=controls.get(page);c.index++;c.emit('choose-enter',{index:c.index,conversation});
  const armed=c.index===3&&(c.phone||variant==='completed');
  if(armed){c.armed=true;c.conversation=conversation;c.before=await counts(page);c.emit('barrier-armed',{index:c.index,counts:c.before});}
  await actual(page,s,conversation);c.emit('choose-return',{index:c.index,snapshot:await snapshot(page)});
  if(armed){
    assert.ok(c.reached,'navigation barrier not reached');c.armed=false;
    if(c.phone){
      assertClosed(await snapshot(page));
      // Keep the shared helper and its real native button gesture under proof.
      await page.click('#btnMenu');assert.equal((await snapshot(page)).open,true);
      await closeSidebar(page);await nativeClosed(page);assertClosed(await snapshot(page));
      c.emit('explicit-close-complete',{nativeEvents:await page.evaluate(()=>window.__m7NavigationProof.events)});
    }else assert.equal((await snapshot(page)).hidden,'false');
    const after=await counts(page);assert.deepEqual(after,c.before,'navigation added a confirmation, receipt or DAV mutation');
    c.emit('navigation-counts-identical',{counts:after});
  }
}
async function wait(page,conversation,actual){
  const c=controls.get(page);if(!c.armed)return actual(page,conversation);
  c.reached=true;c.emit('wait-enter',{conversation});
  if(variant==='completed'||variant==='old-click'){
    if(c.phone){await nativeClosed(page);const s=await snapshot(page);assertClosed(s);c.emit('closed-before-wait',{snapshot:s});}
    if(variant==='old-click'){c.emit('old-click-call');await closeSidebar(page);}
    await actual(page,conversation);c.emit('wait-return',{snapshot:await snapshot(page),nativeEvents:await page.evaluate(()=>window.__m7NavigationProof.events)});
  }else{
    await Promise.race([c.held,new Promise((_,reject)=>setTimeout(()=>reject(new Error('real-selection-GET-not-reached')),5000))]);
    const s=await snapshot(page);assert.equal(s.open,true);assert.equal(s.hidden,'false');c.emit('selection-still-loading',{snapshot:s});
    let done=false;
    const waiting=(variant==='no-wait'?Promise.resolve():actual(page,conversation)).then(()=>{done=true;c.emit('wait-return');});
    try{
      // Two real frames let an immediate/active-only mutant settle. This is a
      // scheduler barrier, not a substitute for the delivered predicate.
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      assert.equal(done,false,'selection-wait-returned-before-real-GET-release');c.emit('wait-pending-before-release');
    }finally{c.emit('GET-release-independent-of-click');c.release();}
    await waiting;assertClosed(await snapshot(page));c.emit('wait-state',{snapshot:await snapshot(page),nativeEvents:await page.evaluate(()=>window.__m7NavigationProof.events)});
  }
}
let source=fs.readFileSync(original,'utf8');
function replace(from,to){assert.equal(source.split(from).length,2,'unique proof anchor: '+from);source=source.replace(from,to);}
const boundary=source.indexOf("test('M7 native explicit external adoption");assert.ok(boundary>0);source=source.slice(0,boundary);
if(variant!=='completed')replace('for(const phone of [false,true])','for(const phone of [true])');
replace('    const errors=[];', '    await global.__fixInstall(page,browser,{phone,theme});\n    const errors=[];');
replace('await run(page,state,control,initial);assert.deepEqual(errors,[]);','await run(page,state,control,initial);assert.deepEqual(errors,[]);global.__fixComplete(page);');
replace('test(`M7 native stable Frida identity, two revisions, inventory and lanes:', 'test(`OBS-M7-UI-01 '+variant+' stable identity, navigation and native closure:');
source+='\nconst originalChoose=choose,originalWait=waitForNativeSelection;\nchoose=(page,s,id)=>global.__fixChoose(page,s,id,originalChoose);\nwaitForNativeSelection=(page,id)=>global.__fixWait(page,id,originalWait);\n';
global.__fixInstall=install;global.__fixChoose=beforeChoose;global.__fixWait=wait;
global.__fixComplete=page=>{const c=controls.get(page);assert.ok(c.reached,'barrier must be reached');c.complete=true;c.emit('historical-assertions-complete');};
fs.writeFileSync(`/evidence/fix-${variant}-owned-test.js`,source);
const loaded=new Module(original,module.parent);loaded.filename=original;loaded.paths=Module._nodeModulePaths(path.dirname(original));loaded._compile(source,original);
