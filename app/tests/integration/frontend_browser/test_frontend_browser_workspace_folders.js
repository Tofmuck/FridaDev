'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  assertTextContains,
  openBrowserPage,
} = require('./helpers/browser_test_helpers.js');

function workspaceFoldersMockScript() {
  return `
    (() => {
      const state = {
        conversations: [
          {
            id: "conv-in",
            conversation_id: "conv-in",
            title: "Conversation dedans",
            created_at: "2026-05-20T09:00:00Z",
            updated_at: "2026-05-20T09:00:00Z",
            message_count: 0,
            last_message_preview: "",
            workspace_folder_id: "folder-1",
          },
          {
            id: "conv-out",
            conversation_id: "conv-out",
            title: "Conversation dehors",
            created_at: "2026-05-20T10:00:00Z",
            updated_at: "2026-05-20T10:00:00Z",
            message_count: 0,
            last_message_preview: "",
            workspace_folder_id: null,
          },
        ],
        files: [{
          id: "file-1",
          workspace_folder_id: "folder-1",
          display_name: "note.md",
          original_filename: "note.md",
          content_kind: "document",
          media_kind: "text",
          source_extension: ".md",
          byte_size: 2048,
          text_chars: 42,
          status: "active",
          reason_code: "",
          source_kind: "upload",
        }, {
          id: "file-ocr-source",
          workspace_folder_id: "folder-1",
          display_name: "scan.pdf",
          original_filename: "scan.pdf",
          content_kind: "document",
          media_kind: "text",
          mime_type: "application/pdf",
          source_extension: ".pdf",
          byte_size: 3072,
          text_chars: 0,
          status: "ocr_required",
          reason_code: "workspace_file_ocr_required",
          source_kind: "upload",
        }],
        selections: {},
        patchCalls: [],
        messageFetches: [],
        workspaceUploadCalls: [],
        activeDocumentUploadCalls: [],
        selectionCalls: [],
        ocrCalls: [],
        ocrConfirmCalls: [],
        ocrConfirmResult: false,
      };
      window.__fridaWorkspaceFolderState = state;
      window.confirm = (message) => {
        state.ocrConfirmCalls.push(String(message || ""));
        return state.ocrConfirmResult;
      };
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();

        if (url.pathname === "/api/workspace-folders" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            items: [{
              id: "folder-1",
              display_name: "Projet Tulu",
              icon_key: "folder",
              description: "Description UI seulement",
              sort_order: 1000,
              created_at: "2026-05-20T08:00:00Z",
              updated_at: "2026-05-20T08:00:00Z",
              deleted_at: null,
            }],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/workspace-folders/folder-1/files" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, workspace_folder_id: "folder-1", items: state.files }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/workspace-folders/folder-1/files" && method === "POST") {
          state.workspaceUploadCalls.push({ pathname: url.pathname, method });
          return new Response(JSON.stringify({
            ok: true,
            workspace_folder_id: "folder-1",
            file: {
              id: "file-2",
              workspace_folder_id: "folder-1",
              display_name: "upload.txt",
              original_filename: "upload.txt",
              content_kind: "document",
              media_kind: "text",
              source_extension: ".txt",
              byte_size: 7,
              text_chars: 7,
              status: "active",
              reason_code: "",
              source_kind: "upload",
            },
          }), { status: 201, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/workspace-folders/folder-1/files/file-ocr-source/ocr" && method === "POST") {
          state.ocrCalls.push({ pathname: url.pathname, method });
          const existing = state.files.find((item) => (
            item.source_kind === "ocr_derived" && item.source_file_id === "file-ocr-source"
          ));
          const derivative = existing || {
            id: "file-ocr-md",
            workspace_folder_id: "folder-1",
            display_name: "scan.ocr.md",
            original_filename: "scan.ocr.md",
            content_kind: "document",
            media_kind: "text",
            mime_type: "text/markdown",
            source_extension: ".md",
            byte_size: 128,
            text_chars: 90,
            status: "active",
            reason_code: "",
            source_kind: "ocr_derived",
            source_file_id: "file-ocr-source",
          };
          if (!existing) state.files.push(derivative);
          return new Response(JSON.stringify({
            ok: true,
            workspace_folder_id: "folder-1",
            source_file_id: "file-ocr-source",
            file: derivative,
          }), { status: existing ? 200 : 201, headers: { "Content-Type": "application/json" } });
        }

        const selectionCollectionMatch = url.pathname.match(/^\\/api\\/conversations\\/([^/]+)\\/workspace-file-selections$/);
        if (selectionCollectionMatch && method === "GET") {
          const conversationId = selectionCollectionMatch[1];
          return new Response(JSON.stringify({
            ok: true,
            conversation_id: conversationId,
            items: Object.values(state.selections[conversationId] || {}),
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (selectionCollectionMatch && method === "POST") {
          const conversationId = selectionCollectionMatch[1];
          const payload = JSON.parse(init.body || "{}");
          state.selectionCalls.push({ conversationId, method, payload });
          const file = state.files.find((item) => item.id === payload.file_id);
          const selection = {
            conversation_id: conversationId,
            workspace_file_id: payload.file_id,
            workspace_folder_id: "folder-1",
            selected: true,
            selection_status: "selected",
            reason_code: "",
            file,
          };
          state.selections[conversationId] = state.selections[conversationId] || {};
          state.selections[conversationId][payload.file_id] = selection;
          return new Response(JSON.stringify({ ok: true, conversation_id: conversationId, selection }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          });
        }

        const selectionItemMatch = url.pathname.match(/^\\/api\\/conversations\\/([^/]+)\\/workspace-file-selections\\/([^/]+)$/);
        if (selectionItemMatch && method === "DELETE") {
          const conversationId = selectionItemMatch[1];
          const fileId = selectionItemMatch[2];
          state.selectionCalls.push({ conversationId, method, fileId });
          if (state.selections[conversationId]) delete state.selections[conversationId][fileId];
          return new Response(JSON.stringify({ ok: true, conversation_id: conversationId, workspace_file_id: fileId }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations" && method === "GET") {
          const limit = Number.parseInt(url.searchParams.get("limit") || "", 10);
          const offset = Number.parseInt(url.searchParams.get("offset") || "", 10);
          const items = state.conversations.slice(offset, offset + limit);
          return new Response(JSON.stringify({
            ok: true,
            items,
            total: state.conversations.length,
            limit,
            offset,
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        const patchMatch = url.pathname.match(/^\\/api\\/conversations\\/([^/]+)$/);
        if (patchMatch && method === "PATCH") {
          const conversationId = patchMatch[1];
          const payload = JSON.parse(init.body || "{}");
          state.patchCalls.push({ conversationId, payload });
          const item = state.conversations.find((conversation) => conversation.id === conversationId);
          if (item) item.workspace_folder_id = payload.workspace_folder_id || null;
          return new Response(JSON.stringify({ ok: true, conversation: item }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        const messagesMatch = url.pathname.match(/^\\/api\\/conversations\\/([^/]+)\\/messages$/);
        if (messagesMatch && method === "GET") {
          const conversationId = messagesMatch[1];
          state.messageFetches.push(conversationId);
          const messages = conversationId === "conv-in"
            ? [{ role: "user", content: "Message du répertoire", timestamp: "2026-05-20T09:01:00Z" }]
            : [{ role: "user", content: "Message hors répertoire", timestamp: "2026-05-20T10:01:00Z" }];
          return new Response(JSON.stringify({ ok: true, messages }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        const activeDocsMatch = url.pathname.match(/^\\/api\\/conversations\\/([^/]+)\\/active-documents$/);
        if (activeDocsMatch && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (activeDocsMatch && method === "POST") {
          state.activeDocumentUploadCalls.push({ pathname: url.pathname, method });
          return new Response(JSON.stringify({ ok: true }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('workspace folders start collapsed, expand on demand and move by drag-and-drop', async () => {
  await openBrowserPage({ mockScript: workspaceFoldersMockScript() }, async (page) => {
    const consoleIssues = [];
    page.on('console', (message) => {
      if (['warning', 'error'].includes(message.type())) consoleIssues.push(message.text());
    });
    await page.waitForSelector('.workspace-folder-row');
    await assertTextContains(page.locator('.workspace-folder-row'), 'Projet Tulu');
    assert.equal((await page.locator('.workspace-folder-toolbar > span').first().textContent()).trim(), 'DOSSIERS');
    assert.equal(
      await page.locator('.workspace-folder-add [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'plus',
    );
    assert.equal(
      await page.locator('.workspace-folder-toggle [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'chevron-right',
    );
    assert.equal(await page.locator('.workspace-folder-svg').count(), 1);
    assert.equal(await page.locator('.workspace-folder-svg-front').count(), 1);
    assert.equal(await page.locator('.workspace-folder-icon').first().getAttribute('title'), 'Dossier');
    assert.equal(await page.locator('.workspace-folder-row').first().getAttribute('class'), 'workspace-folder-row workspace-folder-collapsed');
    assert.equal(await page.locator('.workspace-folder-toggle').first().getAttribute('aria-expanded'), 'false');
    assert.equal(await page.locator('.workspace-folder-files').count(), 0);
    assert.equal(await page.locator('li.in-workspace-folder').count(), 0);

    await page.locator('.workspace-folder-row').click({ position: { x: 92, y: 10 } });
    await page.waitForSelector('.workspace-folder-files');
    assert.equal(await page.locator('.workspace-folder-toggle').first().getAttribute('aria-expanded'), 'true');
    assert.equal(
      await page.locator('.workspace-folder-toggle [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'chevron-down',
    );
    assert.deepEqual(
      await page.locator('.workspace-folder-actions [data-sidebar-icon]').evaluateAll((nodes) => (
        nodes.map((node) => node.getAttribute('data-sidebar-icon'))
      )),
      ['arrow-up', 'arrow-down', 'pencil', 'file-plus', 'notebook-pen', 'trash-2'],
    );
    const folderGeometry = await page.locator('.workspace-folder-row').first().evaluate((node) => {
      const row = node.getBoundingClientRect();
      const main = node.querySelector('.workspace-folder-main').getBoundingClientRect();
      const actions = node.querySelector('.workspace-folder-actions').getBoundingClientRect();
      return {
        rowWidth: Math.round(row.width),
        mainHeight: Math.round(main.height),
        actionsHeight: Math.round(actions.height),
        actionsOffset: Math.round(actions.left - row.left),
      };
    });
    assert.deepEqual(folderGeometry, {
      rowWidth: 244,
      mainHeight: 34,
      actionsHeight: 20,
      actionsOffset: 24,
    });
    await page.locator('#btnTheme').click();
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
    const darkFolderGeometry = await page.locator('.workspace-folder-row').first().evaluate((node) => {
      const row = node.getBoundingClientRect();
      const main = node.querySelector('.workspace-folder-main').getBoundingClientRect();
      const actions = node.querySelector('.workspace-folder-actions').getBoundingClientRect();
      return {
        rowWidth: Math.round(row.width),
        mainHeight: Math.round(main.height),
        actionsHeight: Math.round(actions.height),
        actionsOffset: Math.round(actions.left - row.left),
      };
    });
    assert.deepEqual(darkFolderGeometry, folderGeometry);
    await page.locator('#btnTheme').click();
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'light');
    await assertTextContains(page.locator('.workspace-folder-files'), 'note.md');
    await assertTextContains(page.locator('.workspace-folder-files'), 'MD · 2 ko · 42 caractères');
    await assertTextContains(page.locator('.workspace-folder-files'), 'scan.pdf');
    await assertTextContains(page.locator('.workspace-folder-files'), 'OCR requis');
    await assertTextContains(page.locator('.workspace-folder-separator'), 'CONVERSATIONS');
    assert.equal(
      await page.locator('.workspace-folder-separator').getAttribute('aria-label'),
      'Conversations hors répertoire',
    );
    const headingStyle = await page.locator('.workspace-folder-toolbar').evaluate((node) => getComputedStyle(node));
    const separatorStyle = await page.locator('.workspace-folder-separator').evaluate((node) => getComputedStyle(node));
    assert.equal(separatorStyle.fontSize, headingStyle.fontSize);
    assert.equal(separatorStyle.textTransform, headingStyle.textTransform);
    await assertTextContains(page.locator('li.in-workspace-folder .title'), 'Conversation dedans');
    assert.equal(
      await page.locator('li.in-workspace-folder .thread-kind-icon').getAttribute('data-sidebar-icon'),
      'message-circle',
    );
    assert.equal(
      await page.locator('li.in-workspace-folder .thread-drag-icon').getAttribute('data-sidebar-icon'),
      'grip-vertical',
    );
    assert.equal(
      await page.locator('li[data-conversation-id="conv-out"] .thread-kind-icon').getAttribute('data-sidebar-icon'),
      'circle',
    );
    assert.equal(
      await page.locator('.workspace-folder-file-type-icon').first().getAttribute('data-sidebar-icon'),
      'file-text',
    );
    assert.equal(
      await page.locator('.workspace-folder-file-delete [data-sidebar-icon]').first().getAttribute('data-sidebar-icon'),
      'trash-2',
    );
    assert.equal(
      await page.locator('.workspace-folder-file-ocr [data-sidebar-icon]').first().getAttribute('data-sidebar-icon'),
      'scan-text',
    );
    assert.equal(
      await page.locator('.workspace-folder-note-create [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'notebook-pen',
    );
    assert.equal(
      await page.locator('.workspace-folder-export-create [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'file-output',
    );
    assert.equal(
      await page.locator('.workspace-folder-generated-image-create [data-sidebar-icon]').getAttribute('data-sidebar-icon'),
      'image',
    );
    assert.equal(await page.locator('.thread-folder-select').count(), 0);
    const compactConversationRow = await page.locator('li.in-workspace-folder', { hasText: 'Conversation dedans' }).evaluate((node) => {
      const style = getComputedStyle(node);
      const edit = node.querySelector('.thread-edit');
      return {
        height: Math.round(node.getBoundingClientRect().height),
        backgroundColor: style.backgroundColor,
        editOpacity: Number(getComputedStyle(edit).opacity),
        dragDisplay: getComputedStyle(node.querySelector('.thread-drag-icon')).display,
      };
    });
    assert.ok(compactConversationRow.height <= 44, `conversation row should stay compact, got ${compactConversationRow.height}px`);
    assert.notEqual(compactConversationRow.backgroundColor, 'rgba(0, 0, 0, 0)');
    assert.ok(compactConversationRow.editOpacity > 0.3);
    assert.notEqual(compactConversationRow.dragDisplay, 'none');

    await page.locator('li.in-workspace-folder', { hasText: 'Conversation dedans' }).hover();
    const nestedHoverState = await page.locator('li.in-workspace-folder', { hasText: 'Conversation dedans' }).evaluate((node) => ({
      editOpacity: Number(getComputedStyle(node.querySelector('.thread-edit')).opacity),
      dragDisplay: getComputedStyle(node.querySelector('.thread-drag-icon')).display,
    }));
    assert.ok(nestedHoverState.editOpacity > 0.3);
    assert.equal(nestedHoverState.dragDisplay, 'none');

    await page.locator('li.in-workspace-folder .thread-edit').first().click();
    await page.waitForSelector('li.in-workspace-folder .rename-input');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('li.in-workspace-folder .rename-input'));

    await page.locator('li.in-workspace-folder', { hasText: 'Conversation dedans' }).click();
    await page.waitForFunction(() => document.querySelector('#log')?.textContent.includes('Message du répertoire'));
    await page.locator('li', { hasText: 'Conversation dehors' }).click();
    await page.waitForFunction(() => document.querySelector('#log')?.textContent.includes('Message hors répertoire'));
    const messageFetches = await page.evaluate(() => window.__fridaWorkspaceFolderState.messageFetches);
    assert.ok(messageFetches.includes('conv-in'));
    assert.ok(messageFetches.includes('conv-out'));

    await page.locator('.workspace-folder-row').click({ position: { x: 92, y: 10 } });
    await page.waitForFunction(() => document.querySelector('.workspace-folder-row')?.classList.contains('workspace-folder-collapsed'));
    assert.equal(await page.locator('.workspace-folder-files').count(), 0);
    assert.equal(await page.locator('li.in-workspace-folder').count(), 0);

    await page.locator('.workspace-folder-row').click({ position: { x: 92, y: 10 } });
    await page.waitForSelector('.workspace-folder-files');
    await assertTextContains(page.locator('li.in-workspace-folder .title'), 'Conversation dedans');
    await page.locator('li.in-workspace-folder', { hasText: 'Conversation dedans' }).click();
    await page.waitForFunction(() => document.querySelector('.workspace-folder-file-select')?.disabled === false);

    await page.locator('.workspace-folder-file-select').first().check();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.selectionCalls.length === 1);
    const selectionCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.selectionCalls);
    assert.deepEqual(selectionCalls, [{
      conversationId: 'conv-in',
      method: 'POST',
      payload: { file_id: 'file-1' },
    }]);
    await page.locator('.workspace-folder-file-select').first().uncheck();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.selectionCalls.length === 2);
    assert.deepEqual(await page.evaluate(() => window.__fridaWorkspaceFolderState.selectionCalls[1]), {
      conversationId: 'conv-in',
      method: 'DELETE',
      fileId: 'file-1',
    });

    await page.locator('li', { hasText: 'Conversation dehors' }).dragTo(page.locator('.workspace-folder-row'), {
      sourcePosition: { x: 12, y: 8 },
      targetPosition: { x: 12, y: 8 },
    });
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.patchCalls.length === 1);
    let dragCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.patchCalls);
    assert.deepEqual(dragCalls[0], {
      conversationId: 'conv-out',
      payload: { workspace_folder_id: 'folder-1' },
    });

    await page.locator('li', { hasText: 'Conversation dehors' }).dragTo(page.locator('.workspace-folder-separator'), {
      sourcePosition: { x: 12, y: 8 },
      targetPosition: { x: 12, y: 8 },
    });
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.patchCalls.length === 2);
    dragCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.patchCalls);
    assert.deepEqual(dragCalls[1], {
      conversationId: 'conv-out',
      payload: { workspace_folder_id: null },
    });

    await page.locator('.workspace-folder-row').hover();
    const chooserPromise = page.waitForEvent('filechooser');
    await page.locator('.workspace-folder-action[title="Ajouter un fichier au répertoire"]').click();
    const chooser = await chooserPromise;
    await chooser.setFiles({
      name: 'upload.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('bonjour'),
    });
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.workspaceUploadCalls.length === 1);
    const uploadState = await page.evaluate(() => ({
      workspace: window.__fridaWorkspaceFolderState.workspaceUploadCalls,
      active: window.__fridaWorkspaceFolderState.activeDocumentUploadCalls,
    }));
    assert.deepEqual(uploadState.workspace, [{ pathname: '/api/workspace-folders/folder-1/files', method: 'POST' }]);
    assert.deepEqual(uploadState.active, []);

    await page.locator('.workspace-folder-file-ocr').first().click();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.ocrCalls.length === 1);
    const ocrCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.ocrCalls);
    assert.deepEqual(ocrCalls, [{
      pathname: '/api/workspace-folders/folder-1/files/file-ocr-source/ocr',
      method: 'POST',
    }]);
    await page.waitForFunction(() => document.querySelector('.workspace-folder-files')?.textContent.includes('scan.ocr.md'));
    await assertTextContains(page.locator('.workspace-folder-files'), 'scan.ocr.md');
    await assertTextContains(page.locator('.threads-status'), 'Markdown OCR créé dans le répertoire.');
    assert.deepEqual(await page.evaluate(() => window.__fridaWorkspaceFolderState.ocrConfirmCalls), []);

    await page.locator('.workspace-folder-file-ocr').first().click();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.ocrConfirmCalls.length === 1);
    let reOcrState = await page.evaluate(() => ({
      calls: window.__fridaWorkspaceFolderState.ocrCalls.length,
      confirmation: window.__fridaWorkspaceFolderState.ocrConfirmCalls[0],
    }));
    assert.equal(reOcrState.calls, 1);
    assert.match(reOcrState.confirmation, /remplacera le Markdown OCR actuel/i);
    assert.match(reOcrState.confirmation, /corrections manuelles/i);

    await page.evaluate(() => {
      window.__fridaWorkspaceFolderState.ocrConfirmResult = true;
    });
    await page.locator('.workspace-folder-file-ocr').first().click();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.ocrCalls.length === 2);
    await page.waitForFunction(() => document.querySelector('.threads-status')?.textContent.includes('mis à jour'));
    await assertTextContains(page.locator('.threads-status'), 'Markdown OCR mis à jour dans le répertoire.');
    reOcrState = await page.evaluate(() => ({
      calls: window.__fridaWorkspaceFolderState.ocrCalls.length,
      confirmations: window.__fridaWorkspaceFolderState.ocrConfirmCalls.length,
      derivativeCount: window.__fridaWorkspaceFolderState.files.filter((item) => item.source_kind === 'ocr_derived').length,
    }));
    assert.deepEqual(reOcrState, { calls: 2, confirmations: 2, derivativeCount: 1 });
    assert.deepEqual(consoleIssues, []);
  });
});
