'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const test = require('node:test');
const { chromium } = require('playwright');

const WEB_DIR = path.resolve(__dirname, '../../../web');
const STREAM_CONTROL_PREFIX = '\x1e';

function contentTypeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.html') return 'text/html; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.png') return 'image/png';
  return 'application/octet-stream';
}

async function createStaticWebServer() {
  const server = http.createServer(async (req, res) => {
    const requestUrl = new URL(req.url || '/', 'http://127.0.0.1');
    const pathname = requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname;
    const normalized = path.normalize(decodeURIComponent(pathname)).replace(/^(\.\.[/\\])+/, '');
    const filePath = path.resolve(WEB_DIR, normalized.replace(/^[/\\]+/, ''));

    if (!filePath.startsWith(`${WEB_DIR}${path.sep}`) && filePath !== WEB_DIR) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    try {
      const body = await fs.readFile(filePath);
      res.writeHead(200, { 'Content-Type': contentTypeFor(filePath) });
      res.end(body);
    } catch (error) {
      res.writeHead(error && error.code === 'ENOENT' ? 404 : 500);
      res.end('Not found');
    }
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function openBrowserPage({ pathSuffix = '/', mockScript, afterPage = null }, runTest) {
  const server = await createStaticWebServer();
  let browser = null;

  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ locale: 'fr-FR' });
    const pageErrors = [];
    page.on('pageerror', (error) => {
      pageErrors.push(error);
    });

    await page.route('https://fonts.googleapis.com/**', (route) =>
      route.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    await page.route('https://fonts.gstatic.com/**', (route) =>
      route.fulfill({ status: 204, body: '' }));

    if (mockScript) {
      await page.addInitScript(mockScript);
    }
    await page.goto(`${server.baseUrl}${pathSuffix}`, { waitUntil: 'domcontentloaded' });
    if (typeof afterPage === 'function') {
      await afterPage(page);
    }
    await runTest(page);
    assert.deepEqual(pageErrors.map((error) => error.message), []);
  } finally {
    if (browser) {
      await browser.close();
    }
    await server.close();
  }
}

function chatMockScript({ streamMode }) {
  const nominalTerminal = `${STREAM_CONTROL_PREFIX}${JSON.stringify({
    kind: 'frida-stream-control',
    event: 'done',
    updated_at: '2026-05-03T10:00:00Z',
  })}\n`;
  const errorTerminal = `${STREAM_CONTROL_PREFIX}${JSON.stringify({
    kind: 'frida-stream-control',
    event: 'error',
    error_code: 'conversation_persist_failed',
  })}\n`;
  const streamBody = streamMode === 'error'
    ? `Réponse partielle non persistée${errorTerminal}`
    : `Réponse nominale${nominalTerminal}`;
  const messagesAfterError = [
    {
      role: 'user',
      content: 'Bonjour erreur',
      timestamp: '2026-05-03T10:10:00Z',
    },
  ];

  return `
    (() => {
      const encoder = new TextEncoder();
      const state = {
        streamMode: ${JSON.stringify(streamMode)},
        chatSubmitted: false,
        updatedAt: "2026-05-03T09:00:00Z",
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
          const item = {
            id: "conv-browser",
            conversation_id: "conv-browser",
            title: "Thread navigateur",
            created_at: "2026-05-03T09:00:00Z",
            updated_at: state.updatedAt,
            message_count: state.streamMode === "error" && state.chatSubmitted ? 1 : (state.chatSubmitted ? 2 : 0),
            last_message_preview: state.chatSubmitted ? "Dernier message" : "",
          };
          return new Response(JSON.stringify({ ok: true, items: [item] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-browser/messages" && method === "GET") {
          state.messageFetches += 1;
          const messages = state.streamMode === "error" && state.chatSubmitted ? ${JSON.stringify(messagesAfterError)} : [];
          return new Response(JSON.stringify({ ok: true, messages }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/chat" && method === "POST") {
          state.chatSubmitted = true;
          if (state.streamMode !== "error") {
            state.updatedAt = "2026-05-03T10:00:00Z";
          }
          return new Response(encoder.encode(${JSON.stringify(streamBody)}), {
            status: 200,
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
              "X-Conversation-Id": "conv-browser",
              "X-Conversation-Created-At": "2026-05-03T09:00:00Z",
            },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('chat stream nominal handles done terminal, assistant bubble, timestamp and refresh', async () => {
  await openBrowserPage({ mockScript: chatMockScript({ streamMode: 'done' }) }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');
    await page.fill('#message', 'Bonjour nominal');
    await page.click('#ask button[type="submit"]');

    await page.waitForFunction(() =>
      Array.from(document.querySelectorAll('.msg-wrapper:not(.me) .msg'))
        .some((node) => node.textContent.includes('Réponse nominale')));
    await page.waitForFunction(() => window.__fridaBrowserState.conversationFetches >= 2);

    const assistantBubble = page.locator('.msg-wrapper:not(.me) .msg').last();
    await assertTextContains(assistantBubble, 'Réponse nominale');
    const statusText = await page.locator('.msg-wrapper:not(.me) .msg-stream-status').last().textContent();
    assert.equal(String(statusText || '').trim(), '');

    const threadTime = await page.locator('#threads li.active .thread-time').textContent();
    assert.equal(String(threadTime || '').trim(), '2026-05-03 10:00');

    const fetchCalls = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    const chatPost = fetchCalls.find((call) => call.method === 'POST' && call.path === '/api/chat');
    assert.ok(chatPost, 'chat POST should be called');
    assert.equal(JSON.parse(chatPost.body).stream, true);
    assert.ok(fetchCalls.filter((call) => call.method === 'GET' && call.path === '/api/conversations').length >= 2);
  });
});

test('chat stream error without updated_at rehydrates and avoids canonical optimistic assistant', async () => {
  await openBrowserPage({ mockScript: chatMockScript({ streamMode: 'error' }) }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');
    await page.fill('#message', 'Bonjour erreur');
    await page.click('#ask button[type="submit"]');

    await page.waitForFunction(() =>
      Array.from(document.querySelectorAll('.msg-wrapper:not(.me) .msg-stream-status'))
        .some((node) => !node.hidden && node.textContent.includes('Interrompu côté serveur')));

    const visibleAssistantTexts = await page
      .locator('.msg-wrapper:not(.me) .msg')
      .evaluateAll((nodes) => nodes.map((node) => node.textContent.trim()).filter(Boolean));
    assert.deepEqual(visibleAssistantTexts, ['Réponse interrompue côté serveur.']);

    const bylineText = await page.locator('.msg-wrapper:not(.me) .byline').last().textContent();
    assert.equal(String(bylineText || '').trim(), 'Frida');

    const fetchCalls = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    assert.ok(
      fetchCalls.filter((call) => call.method === 'GET' && call.path === '/api/conversations/conv-browser/messages').length >= 2,
      'error terminal without updated_at should force conversation message rehydration',
    );
    assert.ok(fetchCalls.filter((call) => call.method === 'GET' && call.path === '/api/conversations').length >= 2);
    assert.equal(visibleAssistantTexts.some((text) => text.includes('Réponse partielle non persistée')), false);
  });
});

function adminStatusPayload() {
  const sections = {};
  for (const key of [
    'main_model',
    'arbiter_model',
    'summary_model',
    'stimmung_agent_model',
    'validation_agent_model',
    'embedding',
    'database',
    'services',
    'resources',
  ]) {
    sections[key] = { source: 'db', source_reason: 'db_row' };
  }
  return {
    ok: true,
    db_state: 'db_rows',
    bootstrap: { database_dsn_mode: 'external_bootstrap' },
    sections,
  };
}

function settingField(value) {
  return { value, origin: 'db' };
}

function secretField() {
  return { is_set: true, origin: 'db' };
}

function sectionPayload(route) {
  const common = {
    ok: true,
    source: 'db',
    source_reason: 'db_row',
    readonly_info: {},
    secret_sources: {},
    payload: {},
  };
  if (route === 'main-model') {
    return {
      ...common,
      secret_sources: { api_key: 'db_encrypted' },
      payload: {
        base_url: settingField('https://openrouter.example/api/v1'),
        model: settingField('openai/test-model'),
        referer: settingField('https://fridadev.frida-system.fr'),
        referer_llm: settingField('https://fridadev.frida-system.fr/llm'),
        referer_arbiter: settingField('https://fridadev.frida-system.fr/arbiter'),
        referer_identity_extractor: settingField('https://fridadev.frida-system.fr/identity'),
        referer_resumer: settingField('https://fridadev.frida-system.fr/resumer'),
        referer_stimmung_agent: settingField('https://fridadev.frida-system.fr/stimmung'),
        referer_validation_agent: settingField('https://fridadev.frida-system.fr/validation'),
        app_name: settingField('FridaDev'),
        title_llm: settingField('Frida LLM'),
        title_arbiter: settingField('Frida Arbiter'),
        title_identity_extractor: settingField('Frida Identity'),
        title_resumer: settingField('Frida Resumer'),
        title_stimmung_agent: settingField('Frida Stimmung'),
        title_validation_agent: settingField('Frida Validation'),
        temperature: settingField(0.7),
        top_p: settingField(0.9),
        response_max_tokens: settingField(900),
        api_key: secretField(),
      },
    };
  }
  if (route === 'arbiter-model') {
    return {
      ...common,
      payload: {
        model: settingField('openai/arbiter'),
        temperature: settingField(0),
        top_p: settingField(1),
        timeout_s: settingField(30),
      },
    };
  }
  if (route === 'summary-model') {
    return {
      ...common,
      payload: {
        model: settingField('openai/summary'),
        temperature: settingField(0.2),
        top_p: settingField(0.9),
      },
    };
  }
  if (route === 'stimmung-agent-model') {
    return {
      ...common,
      payload: {
        primary_model: settingField('openai/stimmung'),
        fallback_model: settingField('openai/stimmung-fallback'),
        timeout_s: settingField(20),
        temperature: settingField(0.4),
        top_p: settingField(0.9),
        max_tokens: settingField(300),
      },
    };
  }
  if (route === 'validation-agent-model') {
    return {
      ...common,
      payload: {
        primary_model: settingField('openai/validation'),
        fallback_model: settingField('openai/validation-fallback'),
        timeout_s: settingField(20),
        temperature: settingField(0.2),
        top_p: settingField(0.9),
        max_tokens: settingField(300),
      },
    };
  }
  if (route === 'embedding') {
    return {
      ...common,
      secret_sources: { token: 'db_encrypted' },
      payload: {
        endpoint: settingField('https://embedding.example/v1'),
        model: settingField('embedding-model'),
        dimensions: settingField(1024),
        top_k: settingField(8),
        token: secretField(),
      },
    };
  }
  if (route === 'database') {
    return {
      ...common,
      secret_sources: { dsn: 'db_encrypted' },
      payload: {
        backend: settingField('postgres'),
        dsn: secretField(),
      },
    };
  }
  if (route === 'services') {
    return {
      ...common,
      secret_sources: { crawl4ai_token: 'db_encrypted' },
      payload: {
        searxng_url: settingField('https://search.example'),
        searxng_results: settingField(5),
        crawl4ai_url: settingField('https://crawl.example'),
        crawl4ai_top_n: settingField(3),
        crawl4ai_max_chars: settingField(8000),
        crawl4ai_explicit_url_max_chars: settingField(8000),
        crawl4ai_token: secretField(),
      },
    };
  }
  if (route === 'resources') {
    return {
      ...common,
      payload: {
        llm_identity_path: settingField('/app/state/identity/llm_static.md'),
        user_identity_path: settingField('/app/state/identity/user_static.md'),
      },
    };
  }
  throw new Error(`Unknown route ${route}`);
}

function adminMockScript() {
  return `
    (() => {
      const state = { calls: [] };
      window.__fridaBrowserState = state;
      const routePayloads = ${JSON.stringify({
        'main-model': sectionPayload('main-model'),
        'arbiter-model': sectionPayload('arbiter-model'),
        'summary-model': sectionPayload('summary-model'),
        'stimmung-agent-model': sectionPayload('stimmung-agent-model'),
        'validation-agent-model': sectionPayload('validation-agent-model'),
        embedding: sectionPayload('embedding'),
        database: sectionPayload('database'),
        services: sectionPayload('services'),
        resources: sectionPayload('resources'),
      })};

      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        const body = typeof init.body === "string" ? init.body : "";
        state.calls.push({ method, path: url.pathname, search: url.search, body });

        if (url.pathname === "/api/admin/settings/status" && method === "GET") {
          return new Response(JSON.stringify(${JSON.stringify(adminStatusPayload())}), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        const sectionMatch = /^\\/api\\/admin\\/settings\\/([^/]+)(?:\\/validate)?$/.exec(url.pathname);
        if (sectionMatch && method === "GET") {
          const payload = routePayloads[sectionMatch[1]];
          if (!payload) throw new Error("Unexpected settings section " + sectionMatch[1]);
          return new Response(JSON.stringify(payload), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/settings/main-model/validate" && method === "POST") {
          const data = body ? JSON.parse(body) : {};
          const nextModel = data.payload && data.payload.model && "value" in data.payload.model
            ? String(data.payload.model.value || "")
            : "openai/test-model";
          const valid = Boolean(nextModel.trim());
          return new Response(JSON.stringify({
            ok: true,
            valid,
            checks: valid
              ? [{ name: "model", ok: true, detail: "Modele renseigne." }]
              : [{ name: "model", ok: false, detail: "Modele requis." }],
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/settings/main-model" && method === "PATCH") {
          return new Response(JSON.stringify({ ok: false, error: "validation failed" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('admin settings validate/save shows invalid checks and blocks patch', async () => {
  await openBrowserPage({ pathSuffix: '/admin.html', mockScript: adminMockScript() }, async (page) => {
    await page.waitForSelector('#adminMainModel-model:not([disabled])');
    await page.fill('#adminMainModel-model', '');
    await page.click('#adminMainModelValidate');

    await page.waitForFunction(() =>
      document.querySelector('#adminMainModelStatus')?.textContent.includes('Validation technique incomplete'));
    await assertTextContains(page.locator('#adminMainModelChecks'), 'Modele requis.');

    await page.click('#adminMainModelSave');
    await page.waitForFunction(() =>
      window.__fridaBrowserState.calls.filter((call) =>
        call.method === 'POST' && call.path === '/api/admin/settings/main-model/validate').length >= 2);

    const calls = await page.evaluate(() => window.__fridaBrowserState.calls);
    assert.equal(
      calls.some((call) => call.method === 'PATCH' && call.path === '/api/admin/settings/main-model'),
      false,
      'invalid admin save should not call PATCH',
    );
  });
});

function logsMockScript() {
  return `
    (() => {
      const state = { calls: [], downloads: [] };
      window.__fridaBrowserState = state;
      window.URL.createObjectURL = (blob) => {
        state.downloads.push({ type: blob.type, size: blob.size });
        return "blob:fridadev-test";
      };
      window.URL.revokeObjectURL = (url) => {
        state.revokedUrl = url;
      };
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        state.calls.push({ method, path: url.pathname, search: url.search });

        if (url.pathname === "/api/admin/logs/chat/metadata" && method === "GET") {
          const conversationId = url.searchParams.get("conversation_id") || "";
          return new Response(JSON.stringify({
            ok: true,
            selected_conversation_id: conversationId,
            conversations: [{ conversation_id: "conv-1", events_count: 3 }],
            turns: conversationId ? [{ turn_id: "turn-1", events_count: 2 }] : [],
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/logs/chat" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            count: 1,
            total: 1,
            next_offset: null,
            items: [{
              event_id: "evt-1",
              conversation_id: "conv-1",
              turn_id: "turn-1",
              stage: "llm_call",
              status: "ok",
              ts: "2026-05-03T10:00:00Z",
              duration_ms: 12,
              payload: { model: "test-model" },
            }],
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/logs/chat/export.md" && method === "GET") {
          return new Response("# export\\n", {
            status: 200,
            headers: {
              "Content-Type": "text/markdown; charset=utf-8",
              "Content-Disposition": "attachment; filename=\\"chat-logs-conv-1-turn-1.md\\"",
            },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('logs page applies filters and exports scoped markdown in browser', async () => {
  await openBrowserPage({ pathSuffix: '/log.html', mockScript: logsMockScript() }, async (page) => {
    await page.waitForFunction(() =>
      Boolean(document.querySelector('#logConversationId option[value="conv-1"]')));
    await page.selectOption('#logConversationId', 'conv-1');
    await page.waitForFunction(() => !document.querySelector('#logTurnId')?.disabled);
    await page.selectOption('#logTurnId', 'turn-1');
    await page.selectOption('#logStage', 'llm_call');
    await page.selectOption('#logStatus', 'ok');
    await page.click('#logFiltersForm button[type="submit"]');

    await page.waitForFunction(() =>
      document.querySelector('#logStatusBanner')?.textContent.includes('Lecture ok'));
    await assertTextContains(page.locator('#logGroups'), 'llm_call');
    assert.equal(await page.locator('#exportTurnLogs').isDisabled(), false);

    await page.click('#exportTurnLogs');
    await page.waitForFunction(() =>
      document.querySelector('#logStatusBanner')?.textContent.includes('Export Markdown ok (turn).'));

    const state = await page.evaluate(() => window.__fridaBrowserState);
    const readCall = state.calls
      .filter((call) => call.method === 'GET' && call.path === '/api/admin/logs/chat')
      .at(-1);
    assert.ok(readCall, 'filtered logs read should be called');
    const readParams = new URLSearchParams(readCall.search);
    assert.equal(readParams.get('conversation_id'), 'conv-1');
    assert.equal(readParams.get('turn_id'), 'turn-1');
    assert.equal(readParams.get('stage'), 'llm_call');
    assert.equal(readParams.get('status'), 'ok');

    const exportCall = state.calls
      .filter((call) => call.method === 'GET' && call.path === '/api/admin/logs/chat/export.md')
      .at(-1);
    assert.ok(exportCall, 'turn export should be called');
    const exportParams = new URLSearchParams(exportCall.search);
    assert.equal(exportParams.get('conversation_id'), 'conv-1');
    assert.equal(exportParams.get('turn_id'), 'turn-1');
    assert.deepEqual(state.downloads, [{ type: 'text/markdown;charset=utf-8', size: 9 }]);
  });
});

async function assertTextContains(locator, expectedText) {
  const text = await locator.textContent();
  assert.match(String(text || ''), new RegExp(escapeRegExp(expectedText)));
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
