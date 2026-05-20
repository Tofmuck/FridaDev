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
        workspaceUploadCalls: [],
        activeDocumentUploadCalls: [],
        selectionCalls: [],
        ocrCalls: [],
      };
      window.__fridaWorkspaceFolderState = state;
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
          state.files.push({
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
          });
          return new Response(JSON.stringify({
            ok: true,
            workspace_folder_id: "folder-1",
            source_file_id: "file-ocr-source",
            file: state.files[state.files.length - 1],
          }), { status: 201, headers: { "Content-Type": "application/json" } });
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
          return new Response(JSON.stringify({ ok: true, items: state.conversations }), {
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
          return new Response(JSON.stringify({ ok: true, messages: [] }), {
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

test('workspace folders render above outside conversations and move by select', async () => {
  await openBrowserPage({ mockScript: workspaceFoldersMockScript() }, async (page) => {
    await page.waitForSelector('.workspace-folder-row');
    await assertTextContains(page.locator('.workspace-folder-row'), 'Projet Tulu');
    await assertTextContains(page.locator('.workspace-folder-files'), 'note.md');
    await assertTextContains(page.locator('.workspace-folder-files'), 'MD · 2 ko · 42 caractères');
    await assertTextContains(page.locator('.workspace-folder-files'), 'scan.pdf');
    await assertTextContains(page.locator('.workspace-folder-files'), 'OCR requis');
    await assertTextContains(page.locator('.workspace-folder-separator'), 'Conversations hors répertoire');
    await assertTextContains(page.locator('li.in-workspace-folder .title'), 'Conversation dedans');

    await page.locator('.workspace-folder-file-select').first().check();
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.selectionCalls.length === 1);
    const selectionCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.selectionCalls);
    assert.deepEqual(selectionCalls, [{
      conversationId: 'conv-in',
      method: 'POST',
      payload: { file_id: 'file-1' },
    }]);

    const outsideSelect = page.locator('li', { hasText: 'Conversation dehors' }).locator('.thread-folder-select');
    await outsideSelect.selectOption('folder-1');
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.patchCalls.length === 1);

    const patchCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.patchCalls);
    assert.deepEqual(patchCalls, [{
      conversationId: 'conv-out',
      payload: { workspace_folder_id: 'folder-1' },
    }]);

    await page.locator('li', { hasText: 'Conversation dehors' }).dragTo(page.locator('.workspace-folder-separator'), {
      sourcePosition: { x: 12, y: 8 },
      targetPosition: { x: 12, y: 8 },
    });
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.patchCalls.length === 2);
    let dragCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.patchCalls);
    assert.deepEqual(dragCalls[1], {
      conversationId: 'conv-out',
      payload: { workspace_folder_id: null },
    });

    await page.locator('li', { hasText: 'Conversation dehors' }).dragTo(page.locator('.workspace-folder-row'), {
      sourcePosition: { x: 12, y: 8 },
      targetPosition: { x: 12, y: 8 },
    });
    await page.waitForFunction(() => window.__fridaWorkspaceFolderState.patchCalls.length === 3);
    dragCalls = await page.evaluate(() => window.__fridaWorkspaceFolderState.patchCalls);
    assert.deepEqual(dragCalls[2], {
      conversationId: 'conv-out',
      payload: { workspace_folder_id: 'folder-1' },
    });

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
  });
});
