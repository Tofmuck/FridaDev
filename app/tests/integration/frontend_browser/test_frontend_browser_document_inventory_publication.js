'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { openBrowserPage } = require('./helpers/browser_test_helpers.js');
const { adoptionScript, exactPath } = require('./helpers/document_adoption_fixture.js');
const { mockScript, openWorkshop, showFolder, closeSidebar } = require('./helpers/document_workshop_fixture.js');

// Only the harness exposes the real inventory owner. Capture the response
// before holding it, so adoption cannot change the old payload retroactively.
const instrumentation = `(() => {
  const state = window.__audit = { holds: [], captured: {}, release: {}, results: {} };
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const path = new URL(args[0], location.origin).pathname;
    const index = state.holds.findIndex(hold => path === '/api/workspace-folders/' + hold.folder + '/files');
    const hold = index < 0 ? null : state.holds.splice(index, 1)[0];
    const received = await originalFetch(...args);
    const response = hold?.error ? new Response(JSON.stringify({ok:false, reason_code:'workspace_files_lookup_failed'}),
      {status:503, headers:{'Content-Type':'application/json'}}) : received;
    if (!hold) return response;
    state.captured[hold.label] = await response.clone().json();
    await new Promise(resolve => state.release[hold.label] = resolve);
    return response;
  };
  let module;
  Object.defineProperty(window, 'FridaChatThreadsSidebar', {
    configurable: true,
    get: () => module,
    set(value) {
      module = {...value, createChatThreadsSidebar(...args) {
        const controller = value.createChatThreadsSidebar(...args);
        window.__auditSidebar = controller;
        // Observe settlement without changing the return or implementation.
        return {...controller, refreshWorkspaceFiles: async (...params) => {
          const result = await controller.refreshWorkspaceFiles(...params);
          state.results.last = result;
          return result;
        }};
      }};
    }
  });
})();`;
const setup = () => ({
  mockScript: adoptionScript() + instrumentation,
  beforePage: async page => page.setDefaultTimeout(5000),
});
async function editing(page) {
  await page.waitForFunction(() => window.__m1.calls.some(c => c.path === '/api/conversations/conv-a/active-documents'));
  await openWorkshop(page);
  await page.waitForSelector('#documentWorkshop[data-state=editing]');
}
async function nested(page) {
  await page.click('#documentWorkshopBrowse');
  await page.getByRole('button', { name: 'Ouvrir Sous  dossier', exact: true }).click();
  await page.getByRole('button', { name: 'Adopter Étude  française.md', exact: true }).waitFor();
}
async function adopt(page) {
  await page.getByRole('button', { name: 'Adopter Étude  française.md', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#documentRemoteStatus').textContent.includes('Inventaire actualisé'));
}
async function armRead(page, mode, error = false) {
  await page.evaluate(({ mode, error }) => {
    window.__audit.holds.push({ label: 'old', folder: 'folder-a', error });
    window.__audit.pending = mode === 'folder_refresh'
      ? window.__auditSidebar.refreshWorkspaceFiles('folder-a')
      : window.__auditSidebar.refreshThreadsFromServer({ keepSelection: true });
  }, { mode, error });
  await page.waitForFunction(() => Boolean(window.__audit.release.old));
  if (error) assert.equal(await page.evaluate(() => window.__audit.captured.old.ok), false);
  else assert.equal(await page.evaluate(() => window.__audit.captured.old.items.some(f => f.id === 'adopted-file')), false);
}
async function releaseRead(page) {
  const failed = await page.evaluate(async () => {
    window.__audit.release.old();
    try { await window.__audit.pending; return false; } catch { return true; }
  });
  assert.equal(failed, false, 'An obsolete error must be ignored by the inventory owner');
}
async function assertRetained(page) {
  const retained = await page.evaluate(() => window.__auditSidebar.getWorkspaceFiles('folder-a').some(f => f.id === 'adopted-file'));
  const status = await page.evaluate(() => window.__auditSidebar.getWorkspaceFilesStatus('folder-a').status);
  await page.click('#documentWorkshopExit');
  await openWorkshop(page);
  await page.waitForSelector('#documentWorkshop[data-state=editing]');
  const offered = await page.locator('#documentWorkshopTarget option[value="adopted-file"]').count();
  const adoptionPosts = await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/adopt')).length);
  console.log(JSON.stringify({ retained, offered, status, adoptionPosts }));
  assert.equal(retained, true, 'Older inventory response must not erase the successful adoption from the shared cache');
  assert.equal(offered, 1, 'Reopening the workshop must retain the adopted target');
  assert.equal(status, 'ok');
  assert.equal(await page.locator('#documentWorkshopTarget').inputValue(), '');
  assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/adopt')).length), 1);
  assert.equal(await page.evaluate(() => window.__m1.selections.length), 0);
  assert.equal(await page.evaluate(() => window.__m1.calls.filter(c => c.path === '/api/chat').length), 0);
  await showFolder(page, 'folder-a');
  const row = page.locator('.workspace-folder-file').filter({ hasText: exactPath });
  assert.equal(await row.locator('.workspace-folder-file-select').isChecked(), false);
  await closeSidebar(page);
}

for (const mode of ['folder_refresh', 'global_refresh']) for (const releaseBefore of [true, false]) {
  test(`P2-M2-01 ${mode} response released ${releaseBefore ? 'before' : 'after'} adoption`, async () => {
    await openBrowserPage(setup(), async page => {
      await editing(page);
      await nested(page);
      await armRead(page, mode);
      if (releaseBefore) await releaseRead(page);
      await adopt(page);
      if (!releaseBefore) await releaseRead(page);
      await assertRetained(page);
    });
  });
}
for (const mode of ['folder_refresh', 'global_refresh']) {
  test(`P2-M2-01 late ${mode} error preserves adopted files and successful status`, async () => {
    await openBrowserPage(setup(), async page => {
      await editing(page);
      await nested(page);
      await armRead(page, mode, true);
      await adopt(page);
      await releaseRead(page);
      await assertRetained(page);
    });
  });
}

for (const phase of ['adoption', 'reconciliation']) {
  test(`P2-M2-01 superseded ${phase} read keeps explicit reconciliation pending`, async () => {
    await openBrowserPage(setup(), async page => {
      await editing(page);
      await nested(page);
      if (phase === 'reconciliation') {
        await page.evaluate(() => window.__m2.failInventory = true);
        await page.getByRole('button', { name: 'Adopter Étude  française.md', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('#documentRemoteStatus').textContent.includes('inventaire indisponible'));
        await page.evaluate(() => window.__m2.failInventory = false);
      }
      await page.evaluate(() => {
        window.__audit.holds.push({ label: 'm2', folder: 'folder-a' });
        delete window.__audit.results.last;
      });
      if (phase === 'adoption') await page.getByRole('button', { name: 'Adopter Étude  française.md', exact: true }).click();
      else await page.click('#documentRemoteRefresh');
      await page.waitForFunction(() => Boolean(window.__audit.release.m2));
      // A legitimate, newer read publishes while M2's captured read is held.
      await page.evaluate(() => window.__auditSidebar.refreshWorkspaceFiles('folder-a'));
      await page.evaluate(() => window.__audit.release.m2());
      await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
      assert.equal(await page.evaluate(() => window.__audit.results.last), null);
      assert.doesNotMatch(await page.locator('#documentRemoteStatus').textContent(), /Inventaire actualisé|Collection complète/);
      assert.match(await page.locator('#documentRemoteStatus').textContent(), /Actualiser/);
      await page.click('#documentWorkshopExit');
      await openWorkshop(page);
      await page.waitForSelector('#documentWorkshop[data-state=editing]');
      const before = await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/files')).length);
      await page.click('#documentWorkshopBrowse');
      await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/files')).length), before + 1,
        'Ignored read must keep the folder reconciliation marker across exit/reopen');
      assert.equal(await page.locator('#documentWorkshopTarget option[value="adopted-file"]').count(), 1);
      assert.equal(await page.locator('#documentWorkshopTarget').inputValue(), '');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/adopt')).length), 1);
      // The successful explicit read cleared the marker; browsing again is not a repair loop.
      await page.click('#documentRemoteRefresh');
      await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/files')).length), before + 1);
    });
  });
}

for (const error of [false, true]) {
  test(`P2-M2-01 exit during M2 inventory ${error ? 'error' : 'success'} keeps authority and explicit repair`, async () => {
    await openBrowserPage(setup(), async page => {
      await editing(page);
      await nested(page);
      await page.evaluate(error => {
        window.__audit.holds.push({ label: 'm2', folder: 'folder-a', error });
        delete window.__audit.results.last;
      }, error);
      await page.getByRole('button', { name: 'Adopter Étude  française.md', exact: true }).click();
      await page.waitForFunction(() => Boolean(window.__audit.release.m2));
      await page.click('#documentWorkshopExit');
      await page.evaluate(() => window.__audit.release.m2());
      await page.waitForFunction(() => Object.hasOwn(window.__audit.results, 'last'));
      assert.equal(await page.evaluate(() => window.__audit.results.last), null);
      assert.equal(await page.locator('#documentWorkshop').isVisible(), false);
      assert.equal(await page.evaluate(() => window.__auditSidebar.getWorkspaceFiles('folder-a').some(f => f.id === 'adopted-file')), false);
      assert.equal(await page.evaluate(() => window.__auditSidebar.getWorkspaceFilesStatus('folder-a').status), 'ok');
      await openWorkshop(page);
      await page.waitForSelector('#documentWorkshop[data-state=editing]');
      assert.equal(await page.locator('#documentWorkshopTarget option[value="adopted-file"]').count(), 0);
      const before = await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/files')).length);
      await page.click('#documentWorkshopBrowse');
      await page.waitForSelector('#documentWorkshopBrowse:not([disabled])');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/files')).length), before + 1);
      assert.equal(await page.locator('#documentWorkshopTarget option[value="adopted-file"]').count(), 1);
      assert.equal(await page.locator('#documentWorkshopTarget').inputValue(), '');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/adopt')).length), 1);
    });
  });
}

const folderListingFaults = `(() => {
  const state = window.__folderListing = { failure: null, reads: 0, chatRelease: null, chatPosts: 0 };
  const base = window.fetch;
  window.fetch = async (input, init = {}) => {
    const path = new URL(input, location.origin).pathname;
    if (path === '/api/chat') state.chatPosts++;
    if (path === '/api/workspace-folders' && (!init.method || init.method === 'GET')) {
      state.reads++;
      if (state.failure === 'network') throw new TypeError('Synthetic listing network rejection');
      if (state.failure === '503') return new Response(JSON.stringify({ ok:false, reason_code:'synthetic_folders_unavailable' }),
        { status:503, headers:{'Content-Type':'application/json'} });
    }
    if (path === '/api/chat' && state.holdChat) {
      state.holdChat = false;
      const body = String.fromCharCode(30) + JSON.stringify({ kind:'frida-stream-control', event:'done', final_text:'Réponse conservée' }) + '\\n';
      await new Promise(resolve => state.chatRelease = resolve);
      state.chatCompleted = true;
      return new Response(body, { headers:{'Content-Type':'text/plain'} });
    }
    if (path.endsWith('/messages') && state.chatCompleted) {
      await base(input, init);
      return new Response(JSON.stringify({ ok:true, messages:[
        { role:'user', content:'Tour synthétique' }, { role:'assistant', content:'Réponse conservée' },
      ] }), { headers:{'Content-Type':'application/json'} });
    }
    return base(input, init);
  };
})();`;

for (const failure of ['503', 'network']) {
  test(`P2-M2-03 mounted ${failure} listing failure preserves adopted target, folders, selection and draft until explicit recovery`, async () => {
    await openBrowserPage({ ...setup(), mockScript: adoptionScript() + folderListingFaults + instrumentation }, async page => {
      await editing(page);
      await nested(page);
      await adopt(page);
      await page.click('#documentWorkshopExit');
      await page.fill('#message', 'Brouillon conservé');
      await showFolder(page, 'folder-a');
      await page.locator('.workspace-folder-file').filter({ hasText: 'Ébauche.md' }).first().locator('input[type=checkbox]').check();
      await page.waitForFunction(() => window.__auditSidebar.getWorkspaceFileSelections('conv-a').length === 1);
      const before = await page.evaluate(() => ({
        folders: window.__auditSidebar.getWorkspaceFolders(),
        files: window.__auditSidebar.getWorkspaceFiles('folder-a'),
        status: window.__auditSidebar.getWorkspaceFilesStatus('folder-a'),
        selections: window.__auditSidebar.getWorkspaceFileSelections('conv-a'),
        current: window.__auditSidebar.getCurrentId(), contexts: window.__m1.contexts,
      }));
      const accepted = await page.evaluate(async failure => {
        window.__folderListing.failure = failure;
        const result = await window.__auditSidebar.refreshThreadsFromServer();
        window.__auditSidebar.renderThreads();
        return result;
      }, failure);
      assert.equal(accepted, false);
      assert.equal(await page.locator('.threads-status').isVisible(), true);
      assert.equal(await page.locator('.threads-status').textContent(), 'Mode hors ligne.');
      assert.deepEqual(await page.evaluate(() => ({
        folders: window.__auditSidebar.getWorkspaceFolders(),
        files: window.__auditSidebar.getWorkspaceFiles('folder-a'),
        status: window.__auditSidebar.getWorkspaceFilesStatus('folder-a'),
        selections: window.__auditSidebar.getWorkspaceFileSelections('conv-a'),
        current: window.__auditSidebar.getCurrentId(), contexts: window.__m1.contexts,
      })), before);
      assert.equal(await page.locator('.workspace-folder-row').count(), 2);
      assert.equal(await page.locator('.workspace-folder-file').filter({ hasText: exactPath }).count(), 1);
      await closeSidebar(page);
      assert.equal(await page.locator('#message').inputValue(), 'Brouillon conservé');
      const recovered = await page.evaluate(async () => {
        window.__folderListing.failure = null;
        const result = await window.__auditSidebar.refreshThreadsFromServer();
        window.__auditSidebar.renderThreads();
        return result;
      });
      assert.equal(recovered, true);
      assert.equal(await page.locator('.threads-status').textContent(), '');
      await openWorkshop(page);
      await page.waitForSelector('#documentWorkshop[data-state=editing]');
      assert.equal(await page.locator('#documentWorkshopTarget option[value="adopted-file"]').count(), 1);
      assert.equal(await page.locator('#documentWorkshopTarget').inputValue(), '');
      await page.click('#documentWorkshopExit');
      assert.equal(await page.locator('#message').inputValue(), 'Brouillon conservé');
      assert.equal(await page.evaluate(() => window.__m2.calls.filter(c => c.path.endsWith('/adopt')).length), 1);
      assert.equal(await page.evaluate(() => window.__m1.calls.filter(c => c.path === '/api/chat').length), 0);
    });
  });
}

test('P2-M2-03 initial listing failure prevents bootstrap conversation or folder creation', async () => {
  await openBrowserPage({ ...setup(), mockScript: mockScript({ noConversation: true }) + folderListingFaults +
    `window.__folderListing.failure = '503';` + instrumentation }, async page => {
    await page.waitForFunction(() => document.querySelector('.threads-status')?.textContent.length > 0);
    assert.equal(await page.locator('.threads-status').textContent(), 'Mode hors ligne.');
    assert.equal(await page.evaluate(() => window.__m1.calls.filter(c => c.method === 'POST').length), 0);
    assert.equal(await page.evaluate(() => window.__auditSidebar.getCurrentId()), null);
    assert.deepEqual(await page.evaluate(() => window.__auditSidebar.getThreads()), []);
    assert.deepEqual(await page.evaluate(() => window.__auditSidebar.getWorkspaceFolders()), []);
    assert.equal(await page.locator('.workspace-folder-row').count(), 0);
    assert.equal(await page.locator('.workspace-folder-empty-global').count(), 0);
  });
});

test('P2-M2-03 confirmed chat result keeps listing failure visible through conversation reload', async () => {
  await openBrowserPage({ ...setup(), mockScript: adoptionScript() + folderListingFaults + instrumentation }, async page => {
    await page.waitForFunction(() => window.__m1.calls.some(c => c.path === '/api/conversations/conv-a/active-documents'));
    await page.evaluate(() => { window.__folderListing.failure = '503'; window.__folderListing.holdChat = true; });
    await page.fill('#message', 'Tour synthétique');
    await page.click('#ask button[type=submit]');
    await page.waitForFunction(() => Boolean(window.__folderListing.chatRelease));
    await page.fill('#message', 'Brouillon suivant');
    await page.evaluate(() => {
      // Observe real message/selection HTTP after the chat's refresh, without replacing the owner.
      window.__folderListing.beforeMessages = window.__m1.calls.filter(c => c.path.endsWith('/messages')).length;
      window.__folderListing.chatRelease();
    });
    await page.waitForFunction(() => window.__m1.calls.filter(c => c.path.endsWith('/messages')).length > window.__folderListing.beforeMessages);
    await page.waitForFunction(() => Array.from(document.querySelectorAll('.msg-wrapper:not(.me) .msg'))
      .some(node => node.textContent.includes('Réponse conservée')));
    assert.equal(await page.locator('.threads-status').textContent(), 'Mode hors ligne.');
    assert.equal(await page.locator('#message').inputValue(), 'Brouillon suivant');
    assert.equal(await page.evaluate(() => window.__folderListing.reads), 2);
    assert.equal(await page.evaluate(() => window.__folderListing.chatPosts), 1);
    assert.equal(await page.evaluate(() => window.__auditSidebar.getWorkspaceFiles('folder-a').length), 1);
  });
});
