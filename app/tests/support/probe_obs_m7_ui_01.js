'use strict';
// Autonomous diagnostic. Historical modules are compiled in owned memory only.
// No DOM state, CSS, transport response, timeout or product handler is replaced.
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const assert=require('node:assert/strict'),test=require('node:test');
const {performance}=require('node:perf_hooks');
const variant=process.env.OBS_VARIANT||'passive';
const out='/evidence', records=[];
const controls=new WeakMap();
const stamp=(kind,data={})=>records.push({node_ms:performance.now(),kind,...data});
const original=path.resolve('app/tests/integration/frontend_browser/test_frontend_browser_document_http_m7.js');

function browserProbe() {
  const events=[];window.__obs={events};
  const name=e=>e?`${e.tagName.toLowerCase()}${e.id?'#'+e.id:''}${typeof e.className==='string'?'.'+e.className.trim().replaceAll(' ','.'):''}`:null;
  const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
  const describe=e=>{if(!e)return null;const s=getComputedStyle(e);return {name:name(e),class:e.className,hidden:e.getAttribute('aria-hidden'),expanded:e.getAttribute('aria-expanded'),rect:rect(e),transform:s.transform,transition:s.transition,display:s.display,visibility:s.visibility,pointerEvents:s.pointerEvents,zIndex:s.zIndex,scroll:[e.scrollLeft,e.scrollTop],animations:e.getAnimations().map(a=>({state:a.playState,time:a.currentTime,property:a.transitionProperty}))};};
  const snapshot=(kind,extra={})=>{
    const button=document.querySelector('#btnSidebarClose'),r=rect(button);
    const point=r?{x:r.x+r.width/2,y:r.y+r.height/2}:null;
    const root=document.documentElement;
    const value={browser_ms:performance.now(),origin:performance.timeOrigin,kind,...extra,
      presentation:root?{...root.dataset}:null,viewport:[innerWidth,innerHeight],screen:[screen.width,screen.height],touch:navigator.maxTouchPoints,
      media:{coarse:matchMedia('(pointer: coarse)').matches,narrow:matchMedia('(max-width: 640px)').matches},
      visualViewport:visualViewport?{width:visualViewport.width,height:visualViewport.height,offsetLeft:visualViewport.offsetLeft,offsetTop:visualViewport.offsetTop,scale:visualViewport.scale}:null,
      scroll:[scrollX,scrollY],button:describe(button),sidebar:describe(document.querySelector('.sidebar')),backdrop:describe(document.querySelector('#sidebarBackdrop')),menu:describe(document.querySelector('#btnMenu')),topbar:describe(document.querySelector('.topbar')),
      point,receiver:point?name(document.elementFromPoint(point.x,point.y)):null,
      stack:point?document.elementsFromPoint(point.x,point.y).map(name):[]};
    events.push(value);return value;
  };
  window.__obs.snapshot=snapshot;
  for(const method of ['add','remove']) {
    const actual=DOMTokenList.prototype[method];
    DOMTokenList.prototype[method]=function(...tokens) {
      const result=actual.apply(this,tokens);
      if(this===document.querySelector('.sidebar')?.classList)
        events.push({browser_ms:performance.now(),origin:performance.timeOrigin,kind:'sidebar-class-call',method,tokens,stack:new Error().stack});
      return result;
    };
  }
  for(const type of ['click','pointerdown','pointerup']) {
    for(const capture of [true,false])document.addEventListener(type,e=>{
      if(e.target.closest?.('#btnMenu,#btnSidebarClose,#sidebarBackdrop,[data-conversation-id],.workspace-folder-toggle'))
        snapshot(type+(capture?':capture':':bubble'),{target:name(e.target),trusted:e.isTrusted,client:[e.clientX,e.clientY]});
    },capture);
  }
  for(const type of ['transitionrun','transitionstart','transitionend','transitioncancel'])
    document.addEventListener(type,e=>{if(e.target.matches('.sidebar'))snapshot(type,{property:e.propertyName,elapsed:e.elapsedTime});},true);
  for(const type of ['DOMContentLoaded','frida:presentation-context-change'])document.addEventListener(type,()=>snapshot(type));
  for(const type of ['pageshow','resize'])addEventListener(type,()=>snapshot(type));
  addEventListener('pagehide',()=>{snapshot('pagehide');void window.__obsFlush(events);});
  new MutationObserver(mutations=>{
    for(const m of mutations)if(m.target.matches?.('.sidebar,#sidebarBackdrop,#btnMenu,html'))
      snapshot('mutation',{target:name(m.target),attribute:m.attributeName,old:m.oldValue});
  }).observe(document,{subtree:true,attributes:true,attributeOldValue:true,attributeFilter:['class','aria-hidden','aria-expanded','data-presentation-context','data-presentation-theme','data-theme']});
}

async function install(page,browser,options) {
  const id=`${options.phone?'phone':'desktop'}-${options.theme}`;
  const nodeEvents=[],documents=[],pageErrors=[];
  const emit=(kind,data={})=>nodeEvents.push({node_ms:performance.now(),kind,...data});
  const control={armed:false,releases:[],held:0,emit};controls.set(page,control);
  const minimal=variant.startsWith('minimal-');
  page.on('pageerror',error=>pageErrors.push({name:error.name}));
  if(!minimal) {
    await page.exposeFunction('__obsFlush',events=>documents.push(events));
    await page.addInitScript(browserProbe);
  }
  const locator=page.locator.bind(page);
  page.locator=(selector,...args)=>{
    const result=locator(selector,...args);
    if(selector==='#btnSidebarClose') {
      const visible=result.isVisible.bind(result);
      result.isVisible=(...args)=>visible(...args).then(value=>{emit('helper-isVisible-result',{selector,value});return value;});
    }
    return result;
  };
  const click=page.click.bind(page);
  page.click=(selector,...args)=>{
    emit('page-click-call',{selector});
    const invoke=()=>click(selector,...args).then(value=>{
      emit('page-click-return',{selector});
      if(selector==='#btnSidebarClose'&&control.armed&&variant==='before-close') {
        emit('barrier-release',{held:control.held});control.armed=false;
        for(const release of control.releases)release();
        assert.ok(control.held>0,'real selection GET must have been held');
      }
      return value;
    },error=>{emit('page-click-error',{selector,message:error.message});throw error;});
    if(selector==='#btnSidebarClose'&&control.armed&&['after-close','after-transition','minimal-after','minimal-target'].includes(variant)) {
      emit('barrier-enter');control.armed=false;
      // The original helper has already completed its isVisible() here.
      // Wait only for the REAL class removal, never remove it ourselves.
      return page.evaluate(waitTransition=>new Promise((resolve,reject)=>{
        const menu=document.querySelector('.sidebar');
        const alreadyClosed=!menu.classList.contains('open');
        const finish=reason=>{
          clearTimeout(timer);observer.disconnect();menu.removeEventListener('transitionend',end);
          resolve({alreadyClosed,reason});
        };
        const check=()=>{
          if(menu.classList.contains('open'))return;
          if(!waitTransition)return finish('real-class-removal');
          // A frame lets the real CSS transition be scheduled. No geometry
          // measurement, state write, CSS change or synthetic event.
          requestAnimationFrame(()=>{
            if(!menu.classList.contains('open')&&!menu.getAnimations().some(a=>a.transitionProperty==='transform'&&a.playState==='running'))
              finish('closed-no-active-transform-transition');
          });
        };
        const end=e=>{if(e.target===menu&&e.propertyName==='transform'&&!menu.classList.contains('open'))finish('native-transitionend');};
        const timer=setTimeout(()=>{observer.disconnect();menu.removeEventListener('transitionend',end);reject(new Error('real-close-not-observed'));},5000);
        const observer=new MutationObserver(check);
        observer.observe(menu,{attributes:true,attributeFilter:['class']});
        menu.addEventListener('transitionend',end);check();
      }),variant!=='after-close').then(result=>{emit('barrier-observed-real-close',result);return invoke();});
    }
    return invoke();
  };
  for(const type of ['request','response'])page.on(type,value=>{
    const req=type==='request'?value:value.request();
    const url=new URL(req.url());
    if(url.pathname.startsWith('/api/'))emit(type,{method:req.method(),path:url.pathname,status:type==='response'?value.status():undefined});
  });
  const reload=page.reload.bind(page);
  page.reload=(...args)=>{emit('reload-call');return reload(...args).then(value=>{emit('reload-return');return value;});};
  const close=browser.close.bind(browser);
  browser.close=async()=>{
    const report={id,variant,node_origin_ms:performance.timeOrigin,nodeEvents,documents,pageErrors,captureErrors:[]};
    try {
      for(const release of control.releases)release();
      try {documents.push(await page.evaluate(minimal=>{
        if(!minimal){window.__obs.snapshot('session-end');return window.__obs.events;}
        const menu=document.querySelector('.sidebar'),button=document.querySelector('#btnSidebarClose');
        return [{kind:'post-outcome-only',class:menu.className,hidden:menu.getAttribute('aria-hidden'),rect:button.getBoundingClientRect().toJSON()}];
      },minimal));}
      catch(error){report.captureErrors.push({stage:'browser-events',name:error.name});}
      try {
        const state=await (await page.request.get(process.env.M7_HTTP_BASE+'/__m6/state')).json();
        report.finalState={counts:state.counts,dav:state.dav.map(d=>({method:d.method})),providerCount:state.providers.length};
      } catch(error){report.captureErrors.push({stage:'state',name:error.name});}
      try {if(options.phone)await page.screenshot({path:`${out}/${variant}-${id}.png`});}
      catch(error){report.captureErrors.push({stage:'screenshot',name:error.name});}
      fs.writeFileSync(`${out}/${variant}-${id}.json`,JSON.stringify(report,null,2)+'\n');
    } finally {await close();}
  };
  stamp('installed',{id});
}

function compile(source) {
  const loaded=new Module(original,module.parent);
  loaded.filename=original;loaded.paths=Module._nodeModulePaths(path.dirname(original));
  loaded._compile(source,original);return loaded.exports;
}
function replaceOnce(source,from,to) {
  assert.equal(source.split(from).length,2,'instrumentation anchor must be unique');
  return source.replace(from,to);
}

if(['passive','after-close','after-transition','before-close','minimal-after','minimal-target'].includes(variant)) {
  let source=fs.readFileSync(original,'utf8');
  // Four existing stable-identity variants only; nine other M7 cases excluded.
  const boundary=source.indexOf("test('M7 native explicit external adoption");
  assert.ok(boundary>0,'four-case boundary must exist');
  source=source.slice(0,boundary);
  if(variant!=='passive') {
    source=replaceOnce(source,"for(const phone of [false,true])", "for(const phone of [true])");
    const sequence='await choose(page,s,s.conversation);await page.reload();await choose(page,s,s.conversation);';
    source=replaceOnce(source,sequence,'await global.__obsArm(page);await choose(page,s,s.conversation);await page.reload();await choose(page,s,s.conversation);');
  }
  source=replaceOnce(source,"    const errors=[];",`    await global.__obsInstall(page,browser,{phone,theme});\n    const errors=[];`);
  global.__obsInstall=install;
  global.__obsArm=async page=>{
    const control=controls.get(page);control.armed=true;control.emit('barrier-armed');
    if(variant==='before-close')await page.route('**/api/conversations/*/workspace-file-selections',async route=>{
      if(!control.armed||route.request().method()!=='GET')return route.continue();
      control.held++;control.emit('real-GET-held',{path:new URL(route.request().url()).pathname});
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('selection-GET-gate-timeout')),5000);
        control.releases.push(()=>{clearTimeout(timer);resolve();});
      });
      control.emit('real-GET-continue');await route.continue();
    });
  };
  fs.writeFileSync(`${out}/${variant}-owned-test.js`,source);
  compile(source);
} else {
  throw new Error('unknown diagnostic variant');
}
process.on('exit',()=>fs.writeFileSync(`${out}/${variant}-node.json`,JSON.stringify(records,null,2)+'\n'));
