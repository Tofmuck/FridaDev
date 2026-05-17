'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  assertTextContains,
  openBrowserPage,
} = require('./helpers/browser_test_helpers.js');

function activeDocumentsMockScript() {
  return `
    (() => {
      const docsStorageKey = "frida-test-active-documents";
      const readActiveDocs = () => {
        try {
          return JSON.parse(window.localStorage.getItem(docsStorageKey) || "[]");
        } catch {
          return [];
        }
      };
      const writeActiveDocs = (docs) => {
        window.localStorage.setItem(docsStorageKey, JSON.stringify(Array.isArray(docs) ? docs : []));
      };
      const state = {
        fetchCalls: [],
        conversationFetches: 0,
        messageFetches: 0,
      };
      window.__fridaBrowserState = state;
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        state.fetchCalls.push({
          method,
          path: url.pathname,
          search: url.search,
          body: typeof init.body === "string" ? init.body : "",
        });

        if (url.pathname === "/api/conversations" && method === "GET") {
          state.conversationFetches += 1;
          return new Response(JSON.stringify({
            ok: true,
            items: [{
              id: "conv-browser",
              conversation_id: "conv-browser",
              title: "Thread navigateur",
              created_at: "2026-05-03T09:00:00Z",
              updated_at: "2026-05-03T09:00:00Z",
              message_count: 0,
              last_message_preview: "",
            }],
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-browser/messages" && method === "GET") {
          state.messageFetches += 1;
          return new Response(JSON.stringify({ ok: true, messages: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-browser/active-documents" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, conversation_id: "conv-browser", items: readActiveDocs() }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-browser/active-documents" && method === "POST") {
          const file = init.body && typeof init.body.get === "function" ? init.body.get("file") : null;
          const name = String(file && file.name || "document");
          if (name.endsWith(".bin")) {
            return new Response(JSON.stringify({
              ok: false,
              reason_code: "document_type_unsupported",
              document: { filename: name, status: "unsupported", reason_code: "document_type_unsupported" },
            }), {
              status: 422,
              headers: { "Content-Type": "application/json" },
            });
          }
          const ocrFailures = {
            "timeout.pdf": "document_ocr_timeout",
            "failed.pdf": "document_ocr_failed",
            "empty.pdf": "document_ocr_empty",
            "too-large.pdf": "document_ocr_too_large",
            "too-many-pages.pdf": "document_ocr_too_many_pages",
          };
          if (Object.prototype.hasOwnProperty.call(ocrFailures, name)) {
            const reason = ocrFailures[name];
            return new Response(JSON.stringify({
              ok: false,
              reason_code: reason,
              document: { filename: name, status: "ocr_failed", reason_code: reason },
            }), {
              status: 422,
              headers: { "Content-Type": "application/json" },
            });
          }
          if (name === "scan.pdf") {
            await new Promise((resolve) => setTimeout(resolve, 180));
          }
          const docs = readActiveDocs();
          const item = {
            document_id: "doc-browser-" + String(docs.length + 1),
            conversation_id: "conv-browser",
            filename: name,
            media_type: String(file && file.type || "text/plain"),
            source_extension: name.slice(name.lastIndexOf(".")),
            byte_size: Number(file && file.size || 0),
            text_chars: 37,
            text_sha256_12: "abc123def456",
            token_estimate: 8,
            status: "active",
            active: true,
            created_at: "2026-05-03T09:01:00Z",
            deactivated_at: "",
            last_injected_turn_id: "",
            last_excluded_reason_code: "",
            ocr_applied: name === "scan.pdf",
            ocr_engine: name === "scan.pdf" ? "stirling-pdf" : "",
            ocr_languages: name === "scan.pdf" ? "fra+eng+deu" : "",
            ocr_duration_ms: name === "scan.pdf" ? 1200 : 0,
            source: "active_conversation_documents",
          };
          docs.push(item);
          writeActiveDocs(docs);
          return new Response(JSON.stringify({ ok: true, conversation_id: "conv-browser", document: item }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          });
        }

        const activeDelete = url.pathname.match(/^\\/api\\/conversations\\/conv-browser\\/active-documents\\/([^/]+)$/);
        if (activeDelete && method === "DELETE") {
          writeActiveDocs(readActiveDocs().filter((item) => item.document_id !== decodeURIComponent(activeDelete[1])));
          return new Response(JSON.stringify({ ok: true, conversation_id: "conv-browser", document_id: decodeURIComponent(activeDelete[1]) }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('chat active conversation documents upload, OCR states, reload and remove without rendering content', async () => {
  await openBrowserPage({
    mockScript: activeDocumentsMockScript(),
    afterPage: (page) => page.setViewportSize({ width: 390, height: 760 }),
  }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');

    await dropFile(page, 'note.txt', 'text/plain', 'CONTENU BRUT NE DOIT PAS APPARAITRE');
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsList')?.textContent.includes('note.txt'));
    await assertTextContains(page.locator('#activeDocumentsBar'), 'Documents actifs de conversation');
    await assertTextContains(page.locator('#activeDocumentsBar'), 'note.txt');
    const activeText = await page.locator('#activeDocumentsBar').textContent();
    assert.equal(String(activeText || '').includes('CONTENU BRUT NE DOIT PAS APPARAITRE'), false);
    const callsBeforeReload = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    assert.ok(callsBeforeReload.some((call) => call.method === 'POST' && call.path === '/api/conversations/conv-browser/active-documents'));

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsList')?.textContent.includes('note.txt'));

    const box = await page.locator('#ask').boundingBox();
    assert.ok(box && box.width <= 390, 'composer should fit mobile viewport');

    await page.click('#activeDocumentsList .active-document-remove');
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsStatus')?.textContent.includes('Document actif retiré'));
    assert.equal((await page.locator('#activeDocumentsList').textContent()).includes('note.txt'), false);

    await dropFile(page, 'archive.bin', 'application/octet-stream', 'unsupported');
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsStatus')?.textContent.includes('Format non pris en charge'));

    const ocrFailures = [
      ['timeout.pdf', 'OCR trop long'],
      ['failed.pdf', 'OCR impossible'],
      ['empty.pdf', 'OCR sans texte lisible'],
      ['too-large.pdf', "PDF trop volumineux pour l'OCR de conversation"],
      ['too-many-pages.pdf', "PDF trop long pour l'OCR de conversation"],
    ];
    for (const [filename, label] of ocrFailures) {
      await dropFile(page, filename, 'application/pdf', 'ocr failure');
      await page.waitForFunction((expected) =>
        document.querySelector('#activeDocumentsStatus')?.textContent.includes(expected), label);
      const statusText = await page.locator('#activeDocumentsStatus').textContent();
      assert.equal(String(statusText || '').includes('document_ocr_'), false);
    }

    await dropFile(page, 'scan.pdf', 'application/pdf', 'TEXTE OCR BRUT NE DOIT PAS APPARAITRE');
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsStatus')?.textContent.includes('OCR si nécessaire'));
    const pendingOcrText = await page.locator('#activeDocumentsStatus').textContent();
    assert.equal(String(pendingOcrText || '').includes('%'), false);
    await page.waitForFunction(() =>
      document.querySelector('#activeDocumentsList')?.textContent.includes('OCRisé'));
    const ocrBarText = await page.locator('#activeDocumentsBar').textContent();
    assert.equal(String(ocrBarText || '').includes('TEXTE OCR BRUT NE DOIT PAS APPARAITRE'), false);
    await assertTextContains(page.locator('#activeDocumentsBar'), 'Documents actifs de conversation');

    await page.setViewportSize({ width: 1024, height: 760 });
    const desktopBarBox = await page.locator('#activeDocumentsBar').boundingBox();
    assert.ok(
      desktopBarBox && desktopBarBox.x >= 0 && desktopBarBox.x + desktopBarBox.width <= 1024,
      'active documents OCR bar should fit desktop viewport'
    );

    const calls = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    assert.ok(calls.some((call) => call.method === 'DELETE' && call.path.includes('/api/conversations/conv-browser/active-documents/')));
  });
});

async function dropFile(page, filename, type, content) {
  await page.evaluate(({ filename: name, type: mimeType, content: text }) => {
    const file = new File([text], name, { type: mimeType });
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    document.querySelector('.chat').dispatchEvent(new DragEvent('drop', {
      bubbles: true,
      cancelable: true,
      dataTransfer,
    }));
  }, { filename, type, content });
}
