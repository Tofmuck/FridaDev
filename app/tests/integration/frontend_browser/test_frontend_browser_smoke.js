'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  assertTextContains,
  openBrowserPage,
  readDownloadText,
} = require('./helpers/browser_test_helpers.js');

const STREAM_CONTROL_PREFIX = '\x1e';

function chatMockScript({ streamMode, imageMode = 'success' }) {
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
        lastUserMessage: "",
        clipboardWrites: [],
        fetchCalls: [],
        imageMode: ${JSON.stringify(imageMode)},
        imageRequests: [],
        conversationFetches: 0,
        messageFetches: 0,
      };
      window.__fridaBrowserState = state;
      Object.defineProperty(window.navigator, "clipboard", {
        configurable: true,
        value: {
          writeText: async (text) => {
            state.clipboardWrites.push(String(text || ""));
          },
        },
      });
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        const body = typeof init.body === "string" ? init.body : "";
        state.fetchCalls.push({
          method,
          path: url.pathname,
          search: url.search,
          body,
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
          let messages = [];
          if (state.streamMode === "error" && state.chatSubmitted) {
            messages = ${JSON.stringify(messagesAfterError)};
          } else if (state.chatSubmitted) {
            messages = [
              {
                role: "user",
                content: state.lastUserMessage || "Bonjour nominal",
                timestamp: "2026-05-03T09:59:00Z",
                conversation_id: "conv-browser",
              },
              {
                role: "assistant",
                content: "Réponse nominale",
                timestamp: "2026-05-03T10:00:00Z",
                meta: { hash: "abc123" },
              },
            ];
          }
          return new Response(JSON.stringify({ ok: true, messages }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-browser/active-documents" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, conversation_id: "conv-browser", items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/tools/image-generation" && method === "POST") {
          let requestPayload = {};
          try {
            requestPayload = JSON.parse(body || "{}");
          } catch {
            requestPayload = {};
          }
          state.imageRequests.push(requestPayload);
          await new Promise((resolve) => setTimeout(resolve, 80));
          if (state.imageMode === "error") {
            return new Response(JSON.stringify({
              ok: false,
              error_code: "provider_error",
              message: "Génération indisponible.",
            }), {
              status: 502,
              headers: { "Content-Type": "application/json" },
            });
          }
          return new Response(JSON.stringify({
            ok: true,
            generator_key: requestPayload.generator_key,
            model: "google/gemini-2.5-flash-image",
            display_name: "Nano Banana",
            pricing_label: "prix API observé",
            aspect_ratio: requestPayload.aspect_ratio,
            image_size: requestPayload.image_size,
            image_data_url: "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NDAiIGhlaWdodD0iMzYwIiB2aWV3Qm94PSIwIDAgNjQwIDM2MCI+PHJlY3Qgd2lkdGg9IjY0MCIgaGVpZ2h0PSIzNjAiIGZpbGw9IiNmOGY2ZjMiLz48Y2lyY2xlIGN4PSIzMjAiIGN5PSIxODAiIHI9IjkwIiBmaWxsPSIjN2JhN2ZmIi8+PC9zdmc+",
            mime_type: "image/svg+xml",
            provider_model: "google/gemini-2.5-flash-image",
            usage: { cost: 0.01 },
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/settings/main-model" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            payload: { reasoning_effort: { value: "high" } },
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/settings/main-model" && method === "PATCH") {
          const payload = JSON.parse(body || "{}").payload || {};
          return new Response(JSON.stringify({ ok: true, payload }), {
            status: 200, headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/chat" && method === "POST") {
          state.chatSubmitted = true;
          try {
            state.lastUserMessage = String(JSON.parse(init.body || "{}").message || "");
          } catch {
            state.lastUserMessage = "";
          }
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

test('image generation tool opens, validates, calls its own route and keeps chat untouched', async () => {
  await openBrowserPage({
    mockScript: chatMockScript({ streamMode: 'done' }),
    afterPage: (page) => page.setViewportSize({ width: 1440, height: 900 }),
  }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');
    await page.click('#btnImageGeneration');
    await page.waitForSelector('#imageGenerationPanel:not(.hidden)');
    await page.waitForSelector('#imageGenerationEmpty:not([hidden])');
    assert.equal(await page.locator('#imageGenerationResult:not([hidden])').count(), 0);

    assert.equal(await page.locator('#imageGenerationModel').inputValue(), 'image_generator_nano_banana');
    await assertTextContains(page.locator('#imageGenerationPricing'), 'image 0.0000003');

    const sizeOptions = await page.locator('#imageGenerationSize option').evaluateAll((nodes) =>
      nodes.map((node) => node.value));
    assert.deepEqual(sizeOptions, ['1K', '2K']);
    assert.equal(sizeOptions.includes('4K'), false);

    await page.click('#imageGenerationSubmit');
    await assertTextContains(page.locator('#imageGenerationStatus'), 'Prompt requis.');
    assert.equal((await page.evaluate(() => window.__fridaBrowserState.imageRequests)).length, 0);

    await page.fill('#imageGenerationPrompt', 'cercle bleu sur fond blanc');
    await page.click('#imageGenerationSubmit');
    await page.waitForFunction(() =>
      document.querySelector('#imageGenerationStatus')?.dataset.imageGenerationState === 'generating');
    await assertTextContains(page.locator('#imageGenerationStatus'), 'Génération en cours.');
    assert.equal(await page.locator('#imageGenerationEmpty:not([hidden])').count(), 0);
    await page.waitForSelector('#imageGenerationPreview:not([hidden])');
    await page.waitForFunction(() => {
      const img = document.querySelector('#imageGenerationPreview');
      return img && img.complete && img.naturalWidth > 0;
    });
    await assertTextContains(page.locator('#imageGenerationStatus'), 'Image générée.');
    await assertTextContains(page.locator('#imageGenerationMeta'), 'Nano Banana');
    assert.equal(await page.locator('#imageGenerationEmpty:not([hidden])').count(), 0);
    assert.equal(await page.locator('#imageGenerationDownload').isEnabled(), true);

    const imageDownloadPromise = page.waitForEvent('download');
    await page.click('#imageGenerationDownload');
    const imageDownload = await imageDownloadPromise;
    assert.match(imageDownload.suggestedFilename(), /^fridadev-image-\d{8}-\d{6}\.svg$/);

    const imageRequests = await page.evaluate(() => window.__fridaBrowserState.imageRequests);
    assert.equal(imageRequests.length, 1);
    assert.deepEqual(imageRequests[0], {
      generator_key: 'image_generator_nano_banana',
      prompt: 'cercle bleu sur fond blanc',
      aspect_ratio: '1:1',
      image_size: '1K',
    });

    const fetchCalls = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    assert.equal(fetchCalls.some((call) => call.method === 'POST' && call.path === '/api/tools/image-generation'), true);
    assert.equal(fetchCalls.some((call) => call.method === 'POST' && call.path === '/api/chat'), false);
    assert.equal(await page.locator('.msg-wrapper').count(), 0);
  });
});

test('image generation panel stays usable on desktop and mobile viewports', async () => {
  for (const viewport of [
    { width: 1440, height: 900, name: 'desktop' },
    { width: 390, height: 780, name: 'mobile' },
  ]) {
    await openBrowserPage({
      mockScript: chatMockScript({ streamMode: 'done' }),
      afterPage: (page) => page.setViewportSize({ width: viewport.width, height: viewport.height }),
    }, async (page) => {
      await page.waitForSelector('#message:not([disabled])');
      await page.click('#btnImageGeneration');
      await page.fill('#imageGenerationPrompt', 'cercle bleu sur fond blanc');
      await page.click('#imageGenerationSubmit');
      await page.waitForSelector('#imageGenerationPreview:not([hidden])');
      await page.waitForFunction(() => {
        const img = document.querySelector('#imageGenerationPreview');
        return img && img.complete && img.naturalWidth > 0;
      });

      const layout = await page.evaluate(() => {
        const rect = (selector) => {
          const box = document.querySelector(selector).getBoundingClientRect();
          return {
            top: box.top,
            right: box.right,
            bottom: box.bottom,
            left: box.left,
            width: box.width,
            height: box.height,
          };
        };
        const panel = document.querySelector('#imageGenerationPanel');
        const panelBox = panel.getBoundingClientRect();
        const ask = rect('#ask');
        const submit = rect('#imageGenerationSubmit');
        const preview = rect('#imageGenerationPreview');
        const footer = rect('#imageGenerationResultFooter');
        panel.scrollTop = panel.scrollHeight;
        const download = rect('#imageGenerationDownload');
        return {
          panel: rect('#imageGenerationPanel'),
          ask,
          submit,
          preview,
          footer,
          download,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
          scrollHeight: panel.scrollHeight,
          clientHeight: panel.clientHeight,
          scrollable: panel.scrollHeight >= panel.clientHeight,
          panelBeforeScrollBottom: panelBox.bottom,
        };
      });

      assert.ok(layout.panel.left >= 0, `${viewport.name} panel should stay inside left viewport edge`);
      assert.ok(layout.panel.right <= layout.viewportWidth + 1, `${viewport.name} panel should stay inside right viewport edge`);
      assert.ok(layout.panel.top >= 0, `${viewport.name} panel should stay below top viewport edge`);
      assert.ok(layout.panelBeforeScrollBottom <= layout.ask.top + 1, `${viewport.name} panel should stay above composer`);
      assert.ok(layout.submit.left >= layout.panel.left && layout.submit.right <= layout.panel.right + 1, `${viewport.name} submit should stay inside panel`);
      assert.ok(layout.preview.width <= layout.panel.width + 1, `${viewport.name} preview should be constrained by panel`);
      assert.ok(layout.preview.height <= 200, `${viewport.name} preview should stay compact`);
      assert.ok(layout.footer.left >= layout.panel.left && layout.footer.right <= layout.panel.right + 1, `${viewport.name} result footer should stay inside panel`);
      assert.ok(layout.download.top >= layout.panel.top && layout.download.bottom <= layout.panel.bottom + 1, `${viewport.name} download should be reachable by panel scroll`);
    });
  }
});

test('image generation tool displays backend errors without chat side effects', async () => {
  await openBrowserPage({
    mockScript: chatMockScript({ streamMode: 'done', imageMode: 'error' }),
  }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');
    await page.click('#btnImageGeneration');
    await page.fill('#imageGenerationPrompt', 'cercle bleu sur fond blanc');
    await page.click('#imageGenerationSubmit');

    await page.waitForFunction(() =>
      document.querySelector('#imageGenerationStatus')?.textContent.includes('Génération indisponible.'));
    await assertTextContains(page.locator('#imageGenerationStatus'), 'Génération indisponible.');
    assert.equal(await page.locator('#imageGenerationPreview:not([hidden])').count(), 0);
    const fetchCalls = await page.evaluate(() => window.__fridaBrowserState.fetchCalls);
    assert.equal(fetchCalls.some((call) => call.method === 'POST' && call.path === '/api/chat'), false);
  });
});

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
    await page.locator('.msg-wrapper:not(.me) .msg-copy').last().click();
    await page.waitForFunction(() => window.__fridaBrowserState.clipboardWrites.includes('Réponse nominale'));
    const clipboardWrites = await page.evaluate(() => window.__fridaBrowserState.clipboardWrites);
    assert.equal(clipboardWrites.at(-1), 'Réponse nominale');

    const downloadPromise = page.waitForEvent('download');
    await page.click('#btnExportConversation');
    const download = await downloadPromise;
    assert.match(download.suggestedFilename(), /^frida-conversation-.*\.md$/);
    const markdown = await readDownloadText(download);
    assert.match(markdown, /^# Conversation avec Frida\n\nExportée le /);
    assert.match(markdown, /## Utilisateur — .*09:59/);
    assert.match(markdown, /## Frida — .*10:00/);
    assert.match(markdown, /Bonjour nominal/);
    assert.match(markdown, /Réponse nominale/);
    assert.equal(markdown.includes('conversation_id'), false);
    assert.equal(markdown.includes('conv-browser'), false);
    assert.equal(markdown.includes('hash'), false);
    assert.equal(markdown.includes('abc123'), false);
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

test('chat composer keeps desktop textarea and action row from overlapping controls', async () => {
  await openBrowserPage({
    mockScript: chatMockScript({ streamMode: 'done' }),
    afterPage: (page) => page.setViewportSize({ width: 1440, height: 900 }),
  }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');

    const layout = await page.evaluate(() => {
      const message = document.querySelector('#message').getBoundingClientRect();
      const imageGeneration = document.querySelector('#btnImageGeneration').getBoundingClientRect();
      const mic = document.querySelector('#btnMic').getBoundingClientRect();
      const activeDocument = document.querySelector('#btnActiveDocument').getBoundingClientRect();
      const adobe = document.querySelector('#btnAdobeMode').getBoundingClientRect();
      const webSearch = document.querySelector('#btnWebSearch').getBoundingClientRect();
      const submit = document.querySelector('#ask button[type="submit"]').getBoundingClientRect();
      const actions = document.querySelector('.composer-actions').getBoundingClientRect();
      const ask = document.querySelector('#ask').getBoundingClientRect();
      return {
        askLeft: ask.left,
        askRight: ask.right,
        actionsWidth: actions.width,
        messageWidth: message.width,
        messageLeft: message.left,
        messageRight: message.right,
        messageTop: message.top,
        messageBottom: message.bottom,
        actionsTop: actions.top,
        actionsBottom: actions.bottom,
        actionsLeft: actions.left,
        actionsRight: actions.right,
        imageGenerationLeft: imageGeneration.left,
        imageGenerationRight: imageGeneration.right,
        micLeft: mic.left,
        micRight: mic.right,
        micTop: mic.top,
        micBottom: mic.bottom,
        activeDocumentLeft: activeDocument.left,
        activeDocumentRight: activeDocument.right,
        activeDocumentTop: activeDocument.top,
        adobeLeft: adobe.left,
        adobeRight: adobe.right,
        adobeTop: adobe.top,
        webSearchLeft: webSearch.left,
        webSearchRight: webSearch.right,
        submitLeft: submit.left,
        submitRight: submit.right,
        submitTop: submit.top,
        viewportWidth: window.innerWidth,
      };
    });

    assert.ok(
      layout.messageWidth > layout.actionsWidth,
      `desktop composer textarea should remain wider than actions: ${layout.messageWidth}px <= ${layout.actionsWidth}px`,
    );
    assert.ok(layout.messageLeft >= layout.askLeft, 'textarea should stay inside the composer');
    assert.ok(layout.messageRight <= layout.askRight + 1, 'textarea should stay inside the composer');
    assert.ok(layout.messageRight <= layout.actionsLeft, 'action grid should sit to the right of the textarea');
    assert.ok(layout.actionsTop >= layout.messageTop - 1, 'action grid should align with the textarea top');
    assert.ok(layout.actionsBottom <= layout.messageBottom + 1, 'action grid should stay within the textarea height');
    assert.ok(layout.actionsLeft >= layout.askLeft, 'action row should stay inside the composer');
    assert.ok(layout.actionsRight <= layout.askRight + 1, 'action row should stay inside the composer');
    assert.ok(layout.micRight <= layout.webSearchLeft, 'mic button should sit before web-search on the first row');
    assert.ok(layout.webSearchRight <= layout.submitLeft, 'web-search button should not overlap the submit button');
    assert.ok(layout.submitTop <= layout.micBottom, 'submit button should stay on the first row');
    assert.ok(layout.activeDocumentRight <= layout.imageGenerationLeft, 'document button should sit before image on the second row');
    assert.ok(layout.imageGenerationRight <= layout.adobeLeft, 'image button should sit before Adobe on the second row');
    assert.ok(layout.adobeTop >= layout.activeDocumentTop - 1, 'Adobe button should stay on the second row');
    assert.ok(layout.submitRight <= layout.actionsRight + 1, 'submit should stay inside action row');
    assert.ok(layout.askLeft >= 0 && layout.askRight <= layout.viewportWidth, 'composer should stay inside the viewport');
  });
});

test('chat reasoning shortcut stays compact on desktop and mobile', async () => {
  for (const viewport of [
    { width: 1440, height: 900, name: 'desktop', maxWidth: 150 },
    { width: 390, height: 780, name: 'mobile', maxWidth: 132 },
  ]) {
    await openBrowserPage({
      mockScript: chatMockScript({ streamMode: 'done' }),
      afterPage: (page) => page.setViewportSize({ width: viewport.width, height: viewport.height }),
    }, async (page) => {
      await page.waitForSelector('#message:not([disabled])');
      await page.waitForSelector('#mainReasoningLevel:not([disabled])');

      const layout = await page.evaluate(() => {
        const rect = (selector) => {
          const box = document.querySelector(selector).getBoundingClientRect();
          return {
            top: box.top,
            right: box.right,
            bottom: box.bottom,
            left: box.left,
            width: box.width,
            height: box.height,
          };
        };
        const label = document.querySelector('.main-reasoning-label');
        return {
          ask: rect('#ask'),
          message: rect('#message'),
          contextRow: rect('#composerContextRow'),
          contextControls: rect('.composer-context-controls'),
          reasoning: rect('.main-reasoning-control'),
          select: rect('#mainReasoningLevel'),
          labelText: String(label?.textContent || '').trim(),
          selectLabel: document.querySelector('#mainReasoningLevel')?.getAttribute('aria-label'),
          viewportWidth: window.innerWidth,
        };
      });

      assert.equal(layout.labelText, 'Rais.');
      assert.equal(layout.selectLabel, 'Niveau de raisonnement global');
      assert.ok(layout.reasoning.width <= viewport.maxWidth + 1, `${viewport.name} reasoning control too wide: ${layout.reasoning.width}px`);
      assert.ok(layout.contextRow.left >= layout.ask.left - 1, `${viewport.name} context row should stay inside composer`);
      assert.ok(layout.contextRow.right <= layout.ask.right + 1, `${viewport.name} context row should stay inside composer`);
      assert.ok(layout.contextRow.bottom <= layout.message.top + 1, `${viewport.name} context row should stay above textarea`);
      assert.ok(layout.contextControls.left >= layout.ask.left - 1, `${viewport.name} context controls should stay inside composer`);
      assert.ok(layout.contextControls.right <= layout.ask.right + 1, `${viewport.name} context controls should stay inside composer`);
      assert.ok(layout.reasoning.left >= layout.ask.left - 1, `${viewport.name} reasoning control should stay inside composer`);
      assert.ok(layout.reasoning.right <= layout.ask.right + 1, `${viewport.name} reasoning control should stay inside composer`);
      assert.ok(layout.reasoning.bottom <= layout.message.top + 1, `${viewport.name} reasoning control should stay above textarea`);
      assert.ok(layout.select.width <= 88 + 1, `${viewport.name} reasoning select should remain compact`);
      assert.ok(layout.ask.left >= 0 && layout.ask.right <= layout.viewportWidth + 1, `${viewport.name} composer should stay inside viewport`);
    });
  }
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
    'identity_extractor_model',
    'identity_periodic_model',
    'memory_arbiter_model',
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
        referer_identity_periodic: settingField('https://fridadev.frida-system.fr/identity-periodic'),
        referer_resumer: settingField('https://fridadev.frida-system.fr/resumer'),
        referer_stimmung_agent: settingField('https://fridadev.frida-system.fr/stimmung'),
        referer_validation_agent: settingField('https://fridadev.frida-system.fr/validation'),
        app_name: settingField('FridaDev'),
        title_llm: settingField('Frida LLM'),
        title_arbiter: settingField('Frida Arbiter'),
        title_identity_extractor: settingField('Frida Identity'),
        title_identity_periodic: settingField('Frida Periodic Identity'),
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
  if (route === 'identity-extractor-model') {
    return {
      ...common,
      payload: {
        model: settingField('openai/gpt-5.4-mini'),
        temperature: settingField(0),
        top_p: settingField(1),
        max_tokens: settingField(700),
        timeout_s: settingField(10),
      },
    };
  }
  if (route === 'identity-periodic-model') {
    return {
      ...common,
      payload: {
        model: settingField('anthropic/claude-haiku-4.5'),
        temperature: settingField(0),
        top_p: settingField(1),
        max_tokens: settingField(1400),
        timeout_s: settingField(10),
      },
    };
  }
  if (route === 'memory-arbiter-model') {
    return {
      ...common,
      payload: {
        model: settingField('mistralai/mistral-small-2603'),
        temperature: settingField(0),
        top_p: settingField(1),
        max_tokens: settingField(600),
        timeout_s: settingField(10),
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
        'identity-extractor-model': sectionPayload('identity-extractor-model'),
        'identity-periodic-model': sectionPayload('identity-periodic-model'),
        'memory-arbiter-model': sectionPayload('memory-arbiter-model'),
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

function logsMockScript({ metricsMode = 'nominal' } = {}) {
  const nominalMetrics = {
    ok: true,
    kind: 'full_turn_metrics_snapshot',
    events_count: 4,
    turns_observed_count: 1,
    checklist: {
      classification_counts: {
        complete: 1,
        degraded: 0,
        partial: 0,
        legacy_incomplete: 0,
      },
    },
    llm_call_provider_metrics: {
      main_llm_call_count: 1,
      secondary_llm_call_count: 1,
      unknown_llm_call_count: 0,
    },
    fallback_fail_open: { total_count: 1, by_stage: { validation_agent: 1 } },
    rag_funnel: {
      retrieved_candidates_total: 2,
      basketed_candidates_total: 1,
      kept_candidates_total: 1,
      injected_candidates_total: 1,
      prompt_fallback_turns: 0,
    },
    web: {
      requested_turns: 1,
      successful_count: 1,
      injected_turns: 1,
      skipped_count: 1,
      error_count: 0,
    },
    errors_by_stage: { validation_agent: 1 },
    skipped_by_stage: { web_search: 1, 'free form stage label': 1 },
    source: { events_total: 4, events_read: 4, events_truncated: false },
    redaction: { raw_event_payloads_included: false },
  };
  const emptyTruncatedMetrics = {
    ok: true,
    kind: 'full_turn_metrics_snapshot',
    events_count: 0,
    turns_observed_count: 0,
    checklist: {
      classification_counts: {
        complete: 0,
        degraded: 0,
        partial: 0,
        legacy_incomplete: 0,
      },
    },
    llm_call_provider_metrics: {
      main_llm_call_count: 0,
      secondary_llm_call_count: 0,
      unknown_llm_call_count: 0,
    },
    fallback_fail_open: { total_count: 0, by_stage: {} },
    rag_funnel: {
      retrieved_candidates_total: 0,
      basketed_candidates_total: 0,
      kept_candidates_total: 0,
      injected_candidates_total: 0,
      prompt_fallback_turns: 0,
    },
    web: {
      requested_turns: 0,
      successful_count: 0,
      injected_turns: 0,
      skipped_count: 0,
      error_count: 0,
    },
    errors_by_stage: {},
    skipped_by_stage: {},
    source: { events_total: 10, events_read: 0, events_truncated: true },
    redaction: { raw_event_payloads_included: false },
  };
  const metricsPayload = metricsMode === 'empty-truncated' ? emptyTruncatedMetrics : nominalMetrics;
  return `
    (() => {
      const state = { calls: [], downloads: [] };
      const metricsPayload = ${JSON.stringify(metricsPayload)};
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

        if (url.pathname === "/api/admin/logs/chat/metrics" && method === "GET") {
          return new Response(JSON.stringify(metricsPayload), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/logs/chat/turns" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            kind: "chat_turn_pipeline_read_model",
            count: 1,
            total: 1,
            next_offset: null,
            source: { source_kind: "chat_log_events", turns_truncated: false },
            redaction: { raw_event_payloads_included: false },
            items: [{
              kind: "chat_turn_pipeline_item",
              conversation_id: "conv-1",
              turn_id: "turn-1",
              classification: "complete",
              score: 100,
              latest_ts: "2026-05-03T10:00:00Z",
              persistence: { status: "saved", assistant_final_saved: true, assistant_interrupted: false },
              providers: {
                main: { status: "ok", response_chars: 42 },
                secondary: {
                  stimmung: { status: "ok" },
                  validation: { status: "ok" },
                  web_reformulation: { status: "not_applicable" },
                },
              },
              rag: { retrieved: 2, basket: 1, kept: 1, injected: 1 },
              identity: { status: "present", chars: 12 },
              hermeneutic: {
                status: "present",
                node_state: { read_valid: true, write_succeeded: true },
              },
              web: { status: "ok", requested: true },
              errors: { error_count: 0, fallback_count: 0 },
              flags: { events_truncated: false, raw_event_payloads_included: false },
            }],
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
              payload: {
                model: "test-model",
                reason_code: "llm_call_ok",
                raw_event_payloads_included: false,
                runtime_source: "https://example.invalid/path?probe=ARTIFICIAL_LOG_UI_SENTINEL_URL",
                unexpected_free_text: "ARTIFICIAL_LOG_UI_SENTINEL_UNKNOWN",
                prompt: "ARTIFICIAL_LOG_UI_SENTINEL_PROMPT",
                content: "ARTIFICIAL_LOG_UI_SENTINEL_CONTENT",
              },
            }, {
              event_id: "evt-token-like",
              conversation_id: "conv-1",
              turn_id: "turn-1",
              stage: "validation_agent",
              status: "error",
              ts: "2026-05-03T10:00:01Z",
              duration_ms: 13,
              payload: {
                reason_code: "xoxb-artificial-lot7-1",
                error_code: "provider_timeout",
                provider_caller: "ghp_artificiallot71abcdef",
                runtime_pipeline: "hf_artificiallot71abcdef",
                source_kind: "sk_live_artificial_lot7_1",
                event_family: "sk_or_artificial_lot7_1",
                model: "sk-live-artificial-lot7-1",
              },
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

test('logs page applies filters from query string and exports scoped markdown in browser', async () => {
  await openBrowserPage({
    pathSuffix: '/log.html?conversation_id=conv-1&turn_id=turn-1',
    mockScript: logsMockScript(),
  }, async (page) => {
    await page.waitForFunction(() => !document.querySelector('#logTurnId')?.disabled);
    await page.waitForFunction(() =>
      document.querySelector('#logConversationId')?.value === 'conv-1'
      && document.querySelector('#logTurnId')?.value === 'turn-1');
    await page.waitForFunction(() =>
      document.querySelector('#logStatusBanner')?.textContent.includes('Lecture ok'));
    await page.selectOption('#logStage', 'llm_call');
    await page.selectOption('#logStatus', 'ok');
    await page.click('#logFiltersForm button[type="submit"]');

    await page.waitForFunction(() =>
      document.querySelector('#logStatusBanner')?.textContent.includes('Lecture ok'));
    await assertTextContains(page.locator('#logCockpitCards'), 'complete=1');
    await assertTextContains(page.locator('#logCockpitCards'), 'checklist.classification_counts');
    await assertTextContains(page.locator('#logCockpitCards'), 'retrieved');
    await assertTextContains(page.locator('#logCockpitCards'), 'success');
    await assertTextContains(page.locator('#logCockpitCards'), 'fallback:validation_agent');
    const miniBarRows = await page.locator('#logCockpitCards .log-mini-bar-row').count();
    assert.ok(miniBarRows >= 12, `expected compact metric bars, got ${miniBarRows}`);
    const cockpitText = await page.locator('#logCockpitCards').textContent();
    assert.equal(String(cockpitText || '').includes('free form stage label'), false);
    await assertTextContains(page.locator('#logTurns'), 'retrieved=2');
    await assertTextContains(page.locator('#logGroups'), 'llm_call');
    await assertTextContains(page.locator('#logGroups'), 'model=test-model');
    await assertTextContains(page.locator('#logGroups'), 'reason_code=llm_call_ok');
    await assertTextContains(page.locator('#logGroups'), 'reason_code=[redacted]');
    await assertTextContains(page.locator('#logGroups'), 'error_code=provider_timeout');
    await assertTextContains(page.locator('#logGroups'), 'raw_event_payloads_included=false');
    await assertTextContains(page.locator('#logGroups'), 'runtime_source=[redacted]');
    const groupsText = await page.locator('#logGroups').textContent();
    assert.equal(String(groupsText || '').includes('xoxb-artificial-lot7-1'), false);
    assert.equal(String(groupsText || '').includes('ghp_artificiallot71abcdef'), false);
    assert.equal(String(groupsText || '').includes('hf_artificiallot71abcdef'), false);
    assert.equal(String(groupsText || '').includes('sk_live_artificial_lot7_1'), false);
    assert.equal(String(groupsText || '').includes('sk_or_artificial_lot7_1'), false);
    assert.equal(String(groupsText || '').includes('sk-live-artificial-lot7-1'), false);
    assert.equal(String(groupsText || '').includes('ARTIFICIAL_LOG_UI_SENTINEL_URL'), false);
    assert.equal(String(groupsText || '').includes('ARTIFICIAL_LOG_UI_SENTINEL_UNKNOWN'), false);
    assert.equal(String(groupsText || '').includes('ARTIFICIAL_LOG_UI_SENTINEL_PROMPT'), false);
    assert.equal(String(groupsText || '').includes('ARTIFICIAL_LOG_UI_SENTINEL_CONTENT'), false);
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

    const metricsCall = state.calls
      .filter((call) => call.method === 'GET' && call.path === '/api/admin/logs/chat/metrics')
      .at(-1);
    assert.ok(metricsCall, 'cockpit metrics should be called');

    const turnsCall = state.calls
      .filter((call) => call.method === 'GET' && call.path === '/api/admin/logs/chat/turns')
      .at(-1);
    assert.ok(turnsCall, 'turn pipeline should be called');
    const turnsParams = new URLSearchParams(turnsCall.search);
    assert.equal(turnsParams.get('conversation_id'), 'conv-1');
    assert.equal(turnsParams.get('turn_id'), 'turn-1');

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

test('logs cockpit renders compact empty and truncated metric states', async () => {
  await openBrowserPage({
    pathSuffix: '/log.html',
    mockScript: logsMockScript({ metricsMode: 'empty-truncated' }),
  }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#logCockpitSourceChip')?.textContent.includes('source tronquee'));

    await assertTextContains(page.locator('#logCockpitCards'), 'Aucun tour observe dans la fenetre.');
    await assertTextContains(page.locator('#logCockpitCards'), 'Aucun signal RAG observe.');
    await assertTextContains(page.locator('#logCockpitCards'), 'Fenetre metrics tronquee');
    await assertTextContains(page.locator('#logCockpitWindowChip'), 'events=0 / 10');
  });
});

function dashboardMockScript({ mode = 'nominal' } = {}) {
  return `
    (() => {
      const state = { calls: [] };
      window.__fridaBrowserState = state;
      const overviewPayload = (windowKey) => {
        const partial = ${JSON.stringify(mode)} === "partial" || windowKey === "30d";
        return {
          ok: true,
          kind: "dashboard_overview",
          window: {
            key: windowKey,
            label_fr: windowKey === "30d" ? "30 j" : "24 h",
            start: "2026-05-14T12:00:00+00:00",
            end: "2026-05-15T12:00:00+00:00",
            granularity: "hour",
          },
          pulse: {
            label_fr: "Pouls global",
            turns_observed: partial ? 0 : 8,
            classification_counts: partial ? {} : { complete: 5, degraded: 2, partial: 1, legacy_incomplete: 0 },
            responses_saved: partial ? 0 : 7,
            memory_injected_total: partial ? 0 : 6,
            web_requested_turns: partial ? 0 : 3,
            web_injected_turns: partial ? 0 : 2,
            problems_count: partial ? 0 : 2,
          },
          module_totals: partial ? {} : {
            pipeline: { turn_count: 8, metrics: { classification_counts: { complete: 5, degraded: 2, partial: 1 } } },
            memory: { metrics: { retrieved_total: 11, kept_total: 7, injected_total: 6 } },
            web: { metrics: { requested_turns: 3, success_turns: 2, injected_turns: 2, error_turns: 1 } },
            providers: { metrics: { main_duration_ms_total: 1250, main_duration_ms_count: 4 } },
            errors: { metrics: { error_count: 1, fallback_count: 1 } },
            persistence: { metrics: { assistant_final_saved_count: 7 } },
          },
          metric_buckets: partial ? [] : [
            {
              granularity: "hour",
              bucket_start: "2026-05-15T09:00:00+00:00",
              bucket_end: "2026-05-15T10:00:00+00:00",
              module_key: "pipeline",
              metrics: { classification_counts: { complete: 2, degraded: 1, partial: 0, legacy_incomplete: 0 } },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T10:00:00+00:00",
              bucket_end: "2026-05-15T11:00:00+00:00",
              module_key: "pipeline",
              metrics: { classification_counts: { complete: 3, degraded: 1, partial: 1, legacy_incomplete: 0 } },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T09:00:00+00:00",
              bucket_end: "2026-05-15T10:00:00+00:00",
              module_key: "memory",
              metrics: { injected_total: 2 },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T10:00:00+00:00",
              bucket_end: "2026-05-15T11:00:00+00:00",
              module_key: "memory",
              metrics: { injected_total: 4 },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T09:00:00+00:00",
              bucket_end: "2026-05-15T10:00:00+00:00",
              module_key: "web",
              metrics: { injected_turns: 1 },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T10:00:00+00:00",
              bucket_end: "2026-05-15T11:00:00+00:00",
              module_key: "web",
              metrics: { injected_turns: 1 },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T09:00:00+00:00",
              bucket_end: "2026-05-15T10:00:00+00:00",
              module_key: "providers",
              metrics: { main_duration_ms_total: 340, main_duration_ms_count: 1, main_duration_ms_p95: 340 },
            },
            {
              granularity: "hour",
              bucket_start: "2026-05-15T10:00:00+00:00",
              bucket_end: "2026-05-15T11:00:00+00:00",
              module_key: "providers",
              metrics: { main_duration_ms_total: 910, main_duration_ms_count: 3, main_duration_ms_p95: 910 },
            },
          ],
          latency: {
            kind: "dashboard_provider_latency_summary",
            source_kind: "dashboard_metric_buckets.providers",
            semantics_fr: "Moyenne de fenetre calculee depuis total/count des buckets providers.",
            main_duration_ms_avg: partial ? null : 313,
            main_duration_ms_count: partial ? 0 : 4,
            bucket_p95_ms_max: partial ? null : 910,
            latest_bucket_avg_ms: partial ? null : 303,
            latest_bucket_p95_ms: partial ? null : 910,
            redaction: { raw_content_included: false },
          },
          summaries_health: partial ? {
            kind: "dashboard_summary_health",
            status: "ok",
            summaries_total: 0,
            summaries_with_text: 0,
            summaries_with_embedding: 0,
            traces_total: 0,
            traces_with_summary_id: 0,
            redaction: { raw_content_included: false },
          } : {
            kind: "dashboard_summary_health",
            status: "ok",
            summaries_total: 2,
            summaries_with_text: 2,
            summaries_with_embedding: 2,
            traces_total: 465,
            traces_with_summary_id: 117,
            redaction: { raw_content_included: false },
          },
          source: {
            status: partial ? "partially_materialized" : "ok",
            coverage: {
              status: partial ? "partial" : "complete",
              complete: !partial,
              materialized_window_start: "2026-05-15T00:00:00+00:00",
              materialized_window_end: "2026-05-15T12:00:00+00:00",
            },
            limits: { event_limit_dependency: false, source_events_truncated: false, raw_content_included: false },
          },
          redaction: { raw_content_included: false },
        };
      };
      const conversationsPayload = (windowKey) => {
        const partial = ${JSON.stringify(mode)} === "partial" || windowKey === "30d";
        return {
          ok: true,
          kind: "dashboard_conversations",
          window: { key: windowKey },
          items: partial ? [] : [
            {
              conversation_id: "conv-browser-1",
              display_label: "Thread navigateur",
              display_label_source: "title",
              latest_ts: "2026-05-15T11:55:00+00:00",
              turns_count: 5,
              classification_counts: { complete: 4, degraded: 1 },
              memory_used_turns: 4,
              web_requested_turns: 2,
              web_injected_turns: 1,
              error_count: 0,
              fallback_count: 1,
            },
            {
              conversation_id: "conv-browser-2",
              display_label: "",
              display_label_source: "fallback",
              latest_ts: "2026-05-15T10:10:00+00:00",
              turns_count: 3,
              classification_counts: { complete: 1, partial: 1 },
              memory_used_turns: 1,
              web_requested_turns: 1,
              web_injected_turns: 1,
              error_count: 1,
              fallback_count: 0,
            },
          ],
          count: partial ? 0 : 2,
          total: partial ? 0 : 2,
          limit: 12,
          offset: 0,
          next_offset: null,
          source: { limits: { event_limit_dependency: false } },
          redaction: { raw_content_included: false },
        };
      };
      const turnsPayload = (conversationId, windowKey) => ({
        ok: true,
        kind: "dashboard_conversation_turns",
        conversation_id: conversationId,
        window: { key: windowKey },
        items: [
          {
            conversation_id: conversationId,
            turn_id: "turn-browser-1",
            first_ts: "2026-05-15T11:50:00+00:00",
            latest_ts: "2026-05-15T11:55:00+00:00",
            classification: "degraded",
            score: 72,
            source_event_count: 8,
            rag: { retrieved: 8, basket: 5, kept: 3, rejected: 2, injected: 2 },
            web: { requested: true, success: true, injected: true, results_count: 4 },
            errors: { error_count: 0, skipped_count: 0, fallback_count: 1 },
          },
          {
            conversation_id: conversationId,
            turn_id: "turn-browser-2",
            first_ts: "2026-05-15T10:50:00+00:00",
            latest_ts: "2026-05-15T10:55:00+00:00",
            classification: "complete",
            score: 100,
            source_event_count: 7,
            rag: { retrieved: 0, basket: 0, kept: 0, rejected: 0, injected: 0 },
            web: { requested: false, success: false, injected: false, results_count: 0 },
            errors: { error_count: 0, skipped_count: 0, fallback_count: 0 },
          },
        ],
        count: 2,
        total: 2,
        limit: 20,
        offset: 0,
        next_offset: null,
        source: { limits: { event_limit_dependency: false } },
        redaction: { raw_content_included: false },
      });
      const inspectionPayload = (conversationId, turnId, windowKey) => ({
        ok: true,
        kind: "dashboard_turn_inspection",
        conversation_id: conversationId,
        turn_id: turnId,
        window: { key: windowKey },
        item: {
          conversation_id: conversationId,
          turn_id: turnId,
          classification: "degraded",
          score: 72,
          source_event_count: 8,
          redaction: { raw_content_included: false },
        },
        story: {
          kind: "dashboard_turn_story",
          title_fr: "Inspection traduite du tour",
          summary_fr: "Tour degrade avec 0 erreur(s) et 1 fallback(s) compacts.",
          proof_level: "translated_compact_inspection",
          content_status_fr: "Contenu complet non charge; utilisez Afficher le contenu complet pour verifier ce qui est disponible.",
          sections: [
            {
              key: "received",
              label_fr: "Ce que Frida a recu",
              items: [
                "Une demande utilisateur est representee par ce tour.",
                "La lecture reste traduite et sans contenu brut: le texte exact de la demande n est pas affiche.",
              ],
            },
            {
              key: "model_context",
              label_fr: "Ce que le modele a recu, en lecture traduite",
              items: [
                "Composition compacte observee: un bloc identite; 2 elements memoire injectes; un jugement hermeneutique observe; un contexte web injecte.",
                "Le contexte modele exact n est pas reconstructible depuis ces seuls faits compacts quand seuls presence, counts, longueurs ou hashes sont disponibles.",
              ],
            },
            {
              key: "modules",
              label_fr: "Modules",
              items: [
                "Memoire: 8 trouve(s), 5 candidat(s), 3 garde(s), 2 rejete(s), 2 injecte(s).",
                "1 trace(s) memoire injectee(s) etaient liee(s) a un summary_id; 1 resume(s) parent(s) correspondant(s) ont ete injecte(s) avec ces traces. Fenetres: parenthash12: 2026-05-01T00:00:00+00:00 -> 2026-05-02T00:00:00+00:00, 1 trace(s) liee(s).",
                "Web: demande oui, reussi oui, injecte oui, resultats comptes 4.",
                "Persistence: etat sauvegarde.",
              ],
            },
            {
              key: "massive_data",
              label_fr: "Donnees massives resumees",
              items: [
                "25 embeddings demandes, 25 reussis.",
                "Les grands blocs, vecteurs, contenus complets des modeles, textes memoire, identite et web ne sont pas dumps dans cette inspection.",
              ],
            },
            {
              key: "proof_limits",
              label_fr: "Preuves et limites",
              items: [
                "Le contenu complet n est pas precharge ici; il peut etre demande volontairement avec l action Afficher le contenu complet.",
                "Manifeste de prompt disponible: non.",
              ],
            },
          ],
          debug_links: [
            { label_fr: "Logs techniques", href: "/log?conversation_id=" + conversationId + "&turn_id=" + turnId },
            { label_fr: "Memory Admin", href: "/memory-admin" },
          ],
          redaction: { raw_content_included: false },
        },
        modules: [
          {
            module_key: "memory",
            label_fr: "Memoire utilisee",
            summary_fr: "La memoire a trouve 8 elements, en a garde 3, et en a injecte 2.",
            degradation_fr: null,
            raw_content_available: false,
            content_status_fr: "Le contenu complet n est pas charge dans cette inspection; seuls les faits compacts materialises sont utilises.",
          },
          {
            module_key: "providers",
            label_fr: "Modeles consultes",
            summary_fr: "Le modele principal a ete consulte et son appel est reussi.",
            degradation_fr: "Un modele secondaire a signale une erreur.",
            raw_content_available: false,
            content_status_fr: "Le contenu complet reste indisponible dans cette vue.",
          },
        ],
        content_gate: {
          kind: "dashboard_content_gate_summary",
          action_available: true,
          action_label_fr: "Afficher le contenu complet",
          default_state: "not_loaded",
          warning_fr: "Action volontaire: peut afficher du contenu brut si un artefact exact existe. Aucun contenu complet n est charge avant ce clic.",
          redaction: { raw_content_included: false },
        },
        source: { limits: { event_limit_dependency: false } },
        redaction: { raw_content_included: false },
      });
      const contentPayload = (conversationId, turnId, windowKey) => ({
        ok: true,
        kind: "dashboard_turn_content_gate",
        conversation_id: conversationId,
        turn_id: turnId,
        window: { key: windowKey },
        availability: {
          status: "partial_available",
          status_fr: "contenu partiel disponible",
          loaded_after_explicit_action: true,
          preloaded: false,
          status_counts: { exact_available: 1, fingerprint_only: 1, not_reconstructible: 1 },
          warning_fr: "Contenu charge uniquement apres action explicite.",
        },
        items: [
          {
            key: "main_model_payload",
            label_fr: "Payload du modele principal",
            status: "exact_available",
            status_fr: "contenu exact disponible",
            content_text: "CONTENU COMPLET TEST APRES CLIC",
            content_chars: 31,
            content_sha256_12: "abcdef123456",
            explanation_fr: "Contenu exact retrouve dans un evenement source existant.",
            source: { evidence: { message_count: 1, model: "model/test" } },
          },
          {
            key: "memory_content",
            label_fr: "Contenu memoire injecte",
            status: "fingerprint_only",
            status_fr: "empreinte seule disponible",
            content_text: null,
            explanation_fr: "Les logs sources prouvent des counts, mais pas le contenu exact.",
            source: { evidence: { retrieved_count: 8, injected_candidate_count: 2 } },
          },
          {
            key: "web_content",
            label_fr: "Contenu web injecte",
            status: "not_reconstructible",
            status_fr: "non reconstructible",
            content_text: null,
            explanation_fr: "Aucun evenement source disponible ne contient ce contenu.",
            source: null,
          },
        ],
        audit: { attempted: true, stored: true, raw_content_included: false },
        redaction: { raw_content_included: true, secret_blocked_count: 0 },
      });
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        state.calls.push({ method, path: url.pathname, search: url.search });
        const windowKey = url.searchParams.get("window") || "custom";
        if (url.pathname === "/api/admin/dashboard/overview" && method === "GET") {
          return new Response(JSON.stringify(overviewPayload(windowKey)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.pathname === "/api/admin/dashboard/conversations" && method === "GET") {
          return new Response(JSON.stringify(conversationsPayload(windowKey)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        const turnsMatch = url.pathname.match(/^\\/api\\/admin\\/dashboard\\/conversations\\/([^/]+)\\/turns$/);
        if (turnsMatch && method === "GET") {
          return new Response(JSON.stringify(turnsPayload(decodeURIComponent(turnsMatch[1]), windowKey)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        const inspectionMatch = url.pathname.match(/^\\/api\\/admin\\/dashboard\\/turns\\/([^/]+)\\/inspection$/);
        if (inspectionMatch && method === "GET") {
          const conversationId = url.searchParams.get("conversation_id") || "conv-browser-1";
          return new Response(JSON.stringify(inspectionPayload(conversationId, decodeURIComponent(inspectionMatch[1]), windowKey)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        const contentMatch = url.pathname.match(/^\\/api\\/admin\\/dashboard\\/turns\\/([^/]+)\\/content$/);
        if (contentMatch && method === "GET") {
          const conversationId = url.searchParams.get("conversation_id") || "conv-browser-1";
          return new Response(JSON.stringify(contentPayload(conversationId, decodeURIComponent(contentMatch[1]), windowKey)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        throw new Error("unexpected dashboard request " + method + " " + url.pathname);
      };
    })();
  `;
}

test('dashboard overview renders pulse and conversations from aggregate endpoints', async () => {
  await openBrowserPage({
    pathSuffix: '/dashboard.html',
    mockScript: dashboardMockScript(),
  }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#dashboardStatusBanner')?.dataset.state === 'ok');
    await assertTextContains(page.locator('h1'), 'Dashboard long terme');
    await assertTextContains(page.locator('#dashboardPulseCards'), 'Tours reussis');
    await assertTextContains(page.locator('#dashboardPulseCards'), 'Reponses degradees');
    await assertTextContains(page.locator('#dashboardPulseCards'), 'Problemes rencontres');
    await assertTextContains(page.locator('#dashboardPulseCards'), 'Latence moyenne');
    await assertTextContains(page.locator('#dashboardPulseCards'), '313 ms');
    await assertTextContains(page.locator('#dashboardTrendCards'), 'Reponses a surveiller');
    await assertTextContains(page.locator('#dashboardTrendCards'), 'Memoire injectee');
    await assertTextContains(page.locator('#dashboardTrendCards'), 'Web utile');
    await assertTextContains(page.locator('#dashboardTrendCards'), 'Latence moyenne');
    assert.equal(await page.locator('#dashboardTrendCards svg.dashboard-sparkline').count(), 4);
    await assertTextContains(page.locator('#dashboardClassificationBars'), 'Tours reussis');
    await assertTextContains(page.locator('#dashboardMemoryBars'), 'Injectes');
    await assertTextContains(page.locator('#dashboardSummariesBars'), 'Avec texte');
    await assertTextContains(page.locator('#dashboardSummariesBars'), 'Traces liees');
    await assertTextContains(page.locator('#dashboardWebBars'), 'Injectee');
    await assertTextContains(page.locator('#dashboardConversationsTable'), 'Thread navigateur');
    await assertTextContains(page.locator('#dashboardConversationsTable'), 'Conversation du');
    await assertTextContains(page.locator('#dashboardSourceChip'), 'Periode complete');

    const visibleText = await page.locator('main').textContent();
    assert.equal(visibleText.includes('legacy_incomplete'), false);
    assert.equal(visibleText.includes('provider_caller'), false);
    assert.equal(visibleText.includes('event_limit'), false);

    await page.click('#dashboardConversationsBody [data-conversation-id="conv-browser-1"]');
    await page.waitForFunction(() =>
      document.querySelector('#dashboardTurnsList')?.textContent.includes('memoire injectee 2'));
    await assertTextContains(page.locator('#dashboardDrilldownStatus'), 'Conversation ouverte');
    await assertTextContains(page.locator('#dashboardSelectedConversation'), 'Thread navigateur');
    await assertTextContains(page.locator('#dashboardTurnsList'), 'Tour du');
    await assertTextContains(page.locator('#dashboardTurnsList'), 'memoire injectee 2');

    await page.click('#dashboardTurnsList [data-turn-id="turn-browser-1"]');
    await page.waitForFunction(() =>
      document.querySelector('#dashboardInspectionBody')?.textContent.includes('Contenu complet non charge'));
    await assertTextContains(page.locator('#dashboardInspectionStatus'), 'Tour ouvert');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Ce que Frida a recu');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Memoire: 8 trouve(s)');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'resume(s) parent(s)');
    await assertTextContains(page.locator('#dashboardInspectionBody'), '25 embeddings demandes, 25 reussis');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'pas reconstructible');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Contenu complet non charge');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Lecture par module');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Afficher le contenu complet');
    assert.equal((await page.locator('#dashboardInspectionBody').textContent()).includes('CONTENU COMPLET TEST APRES CLIC'), false);
    let calls = await page.evaluate(() => window.__fridaBrowserState.calls);
    assert.equal(calls.some((call) => call.path === '/api/admin/dashboard/turns/turn-browser-1/content'), false);

    await page.click('.dashboard-content-action');
    await page.waitForFunction(() =>
      document.querySelector('#dashboardInspectionBody')?.textContent.includes('CONTENU COMPLET TEST APRES CLIC'));
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'empreinte seule disponible');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'non reconstructible');
    await assertTextContains(page.locator('#dashboardInspectionBody'), 'Action auditee');

    await page.click('[data-window="30d"]');
    await page.waitForFunction(() =>
      document.querySelector('#dashboardSourceChip')?.textContent.includes('Donnees partielles'));
    await assertTextContains(page.locator('#dashboardConversationsEmpty'), 'Aucune conversation observee');
    await assertTextContains(page.locator('#dashboardTrendCards'), 'Aucune donnee materialisee');

    calls = await page.evaluate(() => window.__fridaBrowserState.calls);
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/overview' && call.search.includes('window=24h')));
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/conversations' && call.search.includes('window=24h')));
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/conversations/conv-browser-1/turns' && call.search.includes('window=24h')));
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/turns/turn-browser-1/inspection' && call.search.includes('conversation_id=conv-browser-1')));
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/turns/turn-browser-1/content' && call.search.includes('conversation_id=conv-browser-1')));
    assert.ok(calls.some((call) => call.path === '/api/admin/dashboard/overview' && call.search.includes('window=30d')));
    assert.equal(calls.some((call) => call.path.startsWith('/api/admin/logs')), false);

    await page.setViewportSize({ width: 390, height: 760 });
    const shellBox = await page.locator('.admin-shell').boundingBox();
    assert.ok(shellBox && shellBox.width <= 390, 'dashboard shell should fit mobile viewport');
  });
});

function memoryAdminMockScript() {
  return `
    (() => {
      const state = { calls: [] };
      window.__fridaBrowserState = state;
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        state.calls.push({ method, path: url.pathname, search: url.search });

        if (url.pathname === "/api/admin/memory/dashboard" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            surface: { name: "Memory Admin", route: "/memory-admin", reranker_decision: "no_go_for_now" },
            overview: { mode: "enforced_all", summary: "surface memory" },
            scope: { kept_elsewhere: [] },
            sources_legend: [
              { key: "historical_logs", label: "Historique logs", description: "events" },
            ],
            durable_state: {
              source_kind: "durable_persistence",
              traces: { total: 1, with_embedding: 1, with_summary_id: 0, conversations: 1, by_role: { user: 1 } },
              summaries: { total: 0, with_embedding: 0, conversations: 0 },
              arbiter_decisions: { total: 0, kept_count: 0, rejected_count: 0, fallback_count: 0 },
            },
            retrieval: {
              config_source_kind: "calculated_aggregate",
              activity_source_kind: "historical_logs",
              config: { top_k: 5, basket_limit: 8, summary_lane_live: false },
              recent_activity: { turns_observed: 1, avg_dense_candidates: 1, avg_lexical_candidates: 0, avg_top_k_returned: 0 },
            },
            embeddings: {
              settings_source_kind: "calculated_aggregate",
              activity_source_kind: "historical_logs",
              settings: { model: "embed/test", endpoint_host: "embed.test", dimensions: 384, token_configured: true },
              recent_activity: { total_events: 1, error_events: 0, by_source_kind: { query: 1 } },
              health: { source_kind: "calculated_aggregate", count: 1, dimension: 384, coverage_pct: 100, errors: 0, mismatch_events: 0, drift_status: "ok" },
            },
            pre_arbiter_basket: {
              contract_source_kind: "calculated_aggregate",
              recent_activity_source_kind: "historical_logs",
              contract: { basket_limit: 8, dedup_reason_codes: [] },
              recent_activity: { turns_observed: 1, avg_raw_candidates: 3, avg_basket_candidates: 2, avg_kept: 1 },
            },
            arbiter: {
              settings_source_kind: "calculated_aggregate",
              runtime_source_kind: "runtime_process_local",
              durable_source_kind: "durable_persistence",
              admin_logs_source_kind: "historical_logs",
              settings: { model: "arbiter/test", timeout_s: 10 },
              runtime_metrics: {},
              latency_ms: {},
              mode_observation: {},
              persisted_summary: { total: 0, kept_count: 0, rejected_count: 0, fallback_count: 0 },
            },
            injection: {
              source_kind: "historical_logs",
              recent_activity: {
                events_count: 1,
                injected_turns: 1,
                trace_memory_injected_turns: 1,
                summary_context_injected_turns: 0,
                context_hints_injected_turns: 0,
                latest_injected_candidate_ids: [],
              },
            },
            recent_turns: {
              source_kind: "historical_logs",
              items: [{
                conversation_id: "conv-zero",
                turn_id: "turn-zero",
                latest_ts: "2026-05-14T10:00:00Z",
                stages: {
                  memory_chain_snapshot: {
                    status: "ok",
                    payload: {
                      schema_version: "v1",
                      retrieved_count: 0,
                      basket_candidates_count: 0,
                      kept_count: 0,
                      rejected_count: 0,
                      injected_candidate_count: 0,
                      context_hints_count: 0,
                    },
                  },
                  prompt_prepared: {
                    status: "ok",
                    payload: {
                      trace_memory_injected_count: 3,
                      memory_traces_injected_count: 3,
                      context_hints_injected_count: 2,
                      injection_class: "trace_memory_only",
                    },
                  },
                },
              }],
            },
            read_errors: [],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/logs/chat/metadata" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            selected_conversation_id: "conv-zero",
            conversations: [{ conversation_id: "conv-zero", events_count: 2 }],
            turns: [{ turn_id: "turn-zero", events_count: 2 }],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/logs/chat/turns" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            items: [{
              conversation_id: "conv-zero",
              turn_id: "turn-zero",
              classification: "complete",
              score: 100,
              rag: { source_kind: "memory_chain_snapshot", retrieved: 0, basket: 0, kept: 0, rejected: 0, injected: 0, context_hints: 0 },
              source: { memory_chain_snapshot_present: true, events_truncated: false },
            }],
            source: { events_truncated: false },
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/logs/chat" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            items: [
              { stage: "memory_chain_snapshot", status: "ok", payload: { retrieval: { retrieved_count: 0 }, injection: { injected_candidate_count: 0 } } },
              { stage: "prompt_prepared", status: "ok", payload: { memory_prompt_injection: { trace_memory_injected_count: 3 } } },
            ],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/hermeneutics/arbiter-decisions" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('memory admin recent turns keep explicit zero snapshot counts over fallbacks', async () => {
  await openBrowserPage({ pathSuffix: '/memory-admin.html', mockScript: memoryAdminMockScript() }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#memoryAdminStatusBanner')?.textContent.includes('Memory Admin charge'));
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'retrieved=0');
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'basket=0');
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'kept=0');
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'rejected=0');
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'injected=0');
    await assertTextContains(page.locator('#memoryAdminRecentTurns'), 'hints=0');

    const recentText = await page.locator('#memoryAdminRecentTurns').textContent();
    assert.equal(String(recentText || '').includes('injected=3'), false);
    assert.equal(String(recentText || '').includes('hints=2'), false);
  });
});

function hermeneuticAdminMockScript({
  verifiedWriteRecovery = false,
  currentStagingStatus = "buffering",
} = {}) {
  const currentStagingFrozen = currentStagingStatus !== "buffering";
  const latestIdentityActivity = verifiedWriteRecovery
    ? {
        present: true,
        reason_code: "write_recovery_completed",
        runtime_pipeline: "mutable_identity_judge_v2_add_only",
        failure_class: null,
        recovery_action: "completed",
        processing_state: "completed",
        attempt_current: 1,
        attempt_limit: 2,
        window_fingerprint: "0123456789ab",
        next_window_progress: "current_pair_staged",
        writes_previously_applied: true,
        promotion_count: 0,
        open_tension_count: 0,
      }
    : {
        present: true,
        reason_code: "window_too_large",
        runtime_pipeline: "mutable_identity_judge_v2_add_only",
        failure_class: "deterministic_input",
        recovery_action: "terminal_consume_without_write",
        processing_state: "judge_not_called",
        attempt_current: 1,
        attempt_limit: 2,
        window_fingerprint: "0123456789ab",
        next_window_progress: "current_pair_staged",
        writes_previously_applied: false,
        promotion_count: 0,
        open_tension_count: 0,
      };
  return `
    (() => {
      const state = { calls: [] };
      window.__fridaBrowserState = state;

      const identityReadModel = {
        ok: true,
        read_model_version: "v2",
        active_runtime: {
          active_identity_source: "identity_mutables",
          active_prompt_contract: "static + mutable narrative",
          identity_input_schema_version: "v2",
          legacy_identity_pipeline_status: "legacy_diagnostic_only",
          used_identity_ids_count: 0,
          identity_runtime_regime: {
            mutable_budget: { target_chars: 3000, max_chars: 3300 },
            staging_target_pairs: 5,
            staging_not_injected: true,
          },
        },
        identity_staging: {
          present: true,
          actively_injected: false,
          buffer_pairs_count: ${currentStagingFrozen ? 5 : 1},
          buffer_target_pairs: 5,
          buffer_frozen: ${currentStagingFrozen},
          last_agent_status: ${JSON.stringify(currentStagingStatus)},
          last_agent_reason: ${JSON.stringify(
            currentStagingFrozen ? "synthetic_content_free_reason" : null
          )},
          current_buffer: {
            status: ${JSON.stringify(currentStagingStatus)},
            reason_code: ${JSON.stringify(
              currentStagingFrozen ? "synthetic_content_free_reason" : "below_threshold"
            )},
            pairs_count: ${currentStagingFrozen ? 5 : 1},
            target_pairs: 5,
            frozen: ${currentStagingFrozen},
          },
          last_completed_agent: { present: false },
          latest_agent_activity: ${JSON.stringify(latestIdentityActivity)},
        },
        dialogic_context: {
          classification: "temporary_dialogic_context",
          authority: "prompt_context_only",
          logical_subject: "dialogue",
          active_caller: "dialogic_context_hint_extractor",
          identity_writer: false,
          mutable_authority: false,
          present: true,
          count: 1,
          total_count: 1,
          runtime: {
            selection: { max_items: 2, max_tokens: 120, max_age_days: 7, min_confidence: 0.6 },
          },
          latest_activity: {
            present: true,
            status: "ok",
            reason_code: "hints_persisted",
            hint_count: 1,
            identity_write: false,
            mutable_authority: false,
          },
        },
        subjects: {
          llm: {
            static: {
              storage_kind: "resource_path",
              stored: true,
              loaded_for_runtime: true,
              actively_injected: true,
              content: "llm canon",
              resource_field: "llm_identity_path",
              resolution_kind: "absolute",
              editable_via: "/api/admin/identity/static",
            },
            mutable: {
              storage_kind: "identity_mutables",
              stored: true,
              loaded_for_runtime: true,
              actively_injected: true,
              content: "llm mutable",
              updated_by: "identity_periodic_agent",
              update_reason: "periodic_agent",
            },
            legacy_fragments: { total_count: 0, items: [] },
            evidence: { total_count: 0, items: [] },
            conflicts: { total_count: 0, items: [] },
          },
          user: {
            static: {
              storage_kind: "resource_path",
              stored: true,
              loaded_for_runtime: true,
              actively_injected: true,
              content: "user canon",
              resource_field: "user_identity_path",
              resolution_kind: "absolute",
              editable_via: "/api/admin/identity/static",
            },
            mutable: {
              storage_kind: "identity_mutables",
              stored: false,
              loaded_for_runtime: false,
              actively_injected: false,
              content: "",
            },
            legacy_fragments: { total_count: 0, items: [] },
            evidence: { total_count: 0, items: [] },
            conflicts: { total_count: 0, items: [] },
          },
        },
      };

      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        state.calls.push({ method, path: url.pathname, search: url.search });

        if (url.pathname === "/api/admin/hermeneutics/dashboard" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            mode: "enforced_all",
            mode_observation: { current_mode_observed: true, observed_since: "2026-05-14T10:00:00Z" },
            counters: { parse_error_count: 0 },
            rates: { fallback_rate: 0 },
            latency_ms: { primary_node: { p50_ms: 11, p95_ms: 19 } },
            alerts: [],
            runtime_metrics: { arbiter_call_count: 1 },
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/logs/chat/metadata" && method === "GET") {
          const conversationId = url.searchParams.get("conversation_id") || "";
          return new Response(JSON.stringify({
            ok: true,
            selected_conversation_id: conversationId,
            conversations: [{ conversation_id: "conv-herm", events_count: 4 }],
            turns: conversationId
              ? [
                  { turn_id: "turn-1", events_count: 1 },
                  { turn_id: "turn-2", events_count: 1 },
                ]
              : [],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/logs/chat" && method === "GET") {
          const turnId = url.searchParams.get("turn_id") || "";
          const payload = turnId === "turn-2"
            ? { reason_code: "ok", provider_caller: "llm", response_chars: 12 }
            : {
                reason_code: "ok",
                provider_caller: "llm",
                prompt: "RAW_PROMPT_SHOULD_NOT_RENDER",
                messages: ["RAW_MESSAGE_SHOULD_NOT_RENDER"],
                content: "RAW_CONTENT_SHOULD_NOT_RENDER",
                query: "RAW_QUERY_SHOULD_NOT_RENDER",
                context_block: "RAW_CONTEXT_SHOULD_NOT_RENDER",
                canonical_inputs: { content: "RAW_CANONICAL_SHOULD_NOT_RENDER" },
                operator_note: "RAW_UNKNOWN_STAGE_TEXT_SHOULD_NOT_RENDER",
                response_chars: 24,
              };
          return new Response(JSON.stringify({
            ok: true,
            items: [{
              event_id: "evt-" + turnId,
              conversation_id: "conv-herm",
              turn_id: turnId,
              stage: "primary_node",
              status: "ok",
              ts: "2026-05-14T10:00:00Z",
              duration_ms: 12,
              payload,
            }],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/hermeneutics/arbiter-decisions" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/identity/read-model" && method === "GET") {
          return new Response(JSON.stringify(identityReadModel), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/identity/runtime-representations" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            representations_version: "v2",
            active_prompt_contract: "static + mutable narrative",
            identity_input_schema_version: "v2",
            same_identity_basis: true,
            identity_staging: identityReadModel.identity_staging,
            dialogic_context: identityReadModel.dialogic_context,
            structured_identity: {
              technical_name: "identity_input",
              role: "hermeneutic_judgment",
              present: true,
              schema_version: "v2",
              data: { schema_version: "v2" },
            },
            injected_identity_text: {
              technical_name: "identity_block",
              role: "final_model_system_prompt",
              present: true,
              content: "compiled identity",
            },
            used_identity_ids_count: 0,
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/identity/governance" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            governance_version: "v1",
            editable_count: 0,
            readonly_count: 0,
            doctrine_locked_count: 0,
            legacy_inactive_count: 0,
            active_runtime_count: 0,
            active_subpipeline_count: 0,
            regime_section_count: 0,
            items: [],
            regime_sections: [],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/admin/hermeneutics/identity-candidates" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [], legacy_only: true, evidence_only: true }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/admin/hermeneutics/corrections-export" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

test('hermeneutic admin keeps turn selection targeted and stage payloads content-free', async () => {
  await openBrowserPage({ pathSuffix: '/hermeneutic-admin.html', mockScript: hermeneuticAdminMockScript() }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#hermeneuticAdminStatusBanner')?.textContent.includes('Lecture hermeneutique ok'));

    assert.equal(await page.locator('#hermeneuticIdentityRuntimeDisclosure').evaluate((node) => node.open), false);
    assert.ok(await page.locator('#hermeneuticTurnStages details.admin-disclosure').count() >= 1);

    const identityText = String(await page.locator('#hermeneuticIdentityReadModel').textContent() || '');
    const assertIdentityLivenessRendering = (text) => {
      assert.equal(text.includes('buffer=1/5'), true, 'next buffer cardinality must render');
      assert.equal(text.includes('gele=false'), true, 'effective progression must unfreeze the current buffer');
      assert.equal(
        text.includes('buffer_status=buffering'),
        true,
        'authoritative current staging state must render',
      );
      assert.equal(text.includes('classe=deterministic_input'), true, 'failure class must render');
      assert.equal(text.includes('action=terminal_consume_without_write'), true, 'terminal action must render');
      assert.equal(text.includes('tentative=1/2'), true, 'bounded attempt must render');
      assert.equal(text.includes('empreinte=0123456789ab'), true, 'window fingerprint must render');
      assert.equal(text.includes('progression=current_pair_staged'), true, 'effective progression must render');
      assert.equal(text.includes('buffer_status=ok'), false, 'critical staging failure cannot render as ok');
    };
    assertIdentityLivenessRendering(identityText);
    assert.throws(
      () => assertIdentityLivenessRendering(
        identityText.replace('action=terminal_consume_without_write', 'action=completed'),
      ),
      /terminal action must render/,
    );

    const firstTurnText = String(await page.locator('#hermeneuticTurnStages').textContent() || '');
    for (const forbidden of [
      'RAW_PROMPT_SHOULD_NOT_RENDER',
      'RAW_MESSAGE_SHOULD_NOT_RENDER',
      'RAW_CONTENT_SHOULD_NOT_RENDER',
      'RAW_QUERY_SHOULD_NOT_RENDER',
      'RAW_CONTEXT_SHOULD_NOT_RENDER',
      'RAW_CANONICAL_SHOULD_NOT_RENDER',
      'RAW_UNKNOWN_STAGE_TEXT_SHOULD_NOT_RENDER',
    ]) {
      assert.equal(firstTurnText.includes(forbidden), false, `${forbidden} should stay out of rendered stage diagnostics`);
    }
    assert.ok(await page.locator('#hermeneuticTurnStages [data-key="redaction"]').count() >= 1);
    assert.ok(await page.locator('#hermeneuticTurnStages [data-key="operator_note"]').count() >= 1);
    assert.equal(firstTurnText.includes('stimmung_agent'), false, 'absent critical stages should not render empty panels');

    const initialCounts = await page.evaluate(() => {
      const calls = window.__fridaBrowserState.calls;
      const count = (path) => calls.filter((call) => call.method === 'GET' && call.path === path).length;
      return {
        readModel: count('/api/admin/identity/read-model'),
        runtime: count('/api/admin/identity/runtime-representations'),
        governance: count('/api/admin/identity/governance'),
        candidates: count('/api/admin/hermeneutics/identity-candidates'),
        corrections: count('/api/admin/hermeneutics/corrections-export'),
        turnLogs: count('/api/admin/logs/chat'),
      };
    });

    await page.selectOption('#hermeneuticTurnId', 'turn-2');
    await page.waitForFunction(() =>
      document.querySelector('#hermeneuticAdminTurnMeta')?.textContent.includes('turn-2'));

    const afterCounts = await page.evaluate(() => {
      const calls = window.__fridaBrowserState.calls;
      const count = (path) => calls.filter((call) => call.method === 'GET' && call.path === path).length;
      return {
        readModel: count('/api/admin/identity/read-model'),
        runtime: count('/api/admin/identity/runtime-representations'),
        governance: count('/api/admin/identity/governance'),
        candidates: count('/api/admin/hermeneutics/identity-candidates'),
        corrections: count('/api/admin/hermeneutics/corrections-export'),
        turnLogs: count('/api/admin/logs/chat'),
      };
    });

    assert.equal(afterCounts.readModel, initialCounts.readModel);
    assert.equal(afterCounts.runtime, initialCounts.runtime);
    assert.equal(afterCounts.governance, initialCounts.governance);
    assert.equal(afterCounts.candidates, initialCounts.candidates);
    assert.equal(afterCounts.corrections, initialCounts.corrections);
    assert.equal(afterCounts.turnLogs, initialCounts.turnLogs + 1);

    assert.ok(await page.locator('#hermeneuticIdentityStaticEditors textarea[name="content"]').count() >= 2);
    assert.ok(await page.locator('#hermeneuticIdentityMutableEditors textarea[name="content"]').count() >= 2);
  });
});

test('identity surfaces render a verified previously applied write recovery', async () => {
  const mockScript = hermeneuticAdminMockScript({ verifiedWriteRecovery: true });
  const assertVerifiedRecovery = (text) => {
    assert.equal(text.includes('action=completed'), true, 'completed recovery action must render');
    assert.equal(text.includes('tentative=1/2'), true, 'recorded judge attempt must render');
    assert.equal(
      text.includes('ecriture_precedente=true'),
      true,
      'verified prior canonical write must render from the authoritative field',
    );
  };

  await openBrowserPage({ pathSuffix: '/identity.html', mockScript }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#identityStatusBanner')?.textContent.includes('Lecture Identity ok'));
    const text = String(await page.locator('#identityRuntimeSummary').textContent() || '');
    assertVerifiedRecovery(text);
    assert.throws(
      () => assertVerifiedRecovery(text.replace('ecriture_precedente=true', 'ecriture_precedente=false')),
      /verified prior canonical write must render/,
    );
  });

  await openBrowserPage({ pathSuffix: '/hermeneutic-admin.html', mockScript }, async (page) => {
    await page.waitForFunction(() =>
      document.querySelector('#hermeneuticAdminStatusBanner')?.textContent.includes('Lecture hermeneutique ok'));
    const text = String(await page.locator('#hermeneuticIdentityReadModel').textContent() || '');
    assertVerifiedRecovery(text);
    assert.throws(
      () => assertVerifiedRecovery(text.replace('ecriture_precedente=true', 'ecriture_precedente=false')),
      /verified prior canonical write must render/,
    );
  });
});

test('identity surfaces render authoritative active claim and finalization recovery states', async () => {
  const assertDialogicContext = (text, surface) => {
    assert.equal(
      text.includes('Contexte dialogique temporaire'),
      true,
      `temporary dialogic context must render on ${surface}`,
    );
    assert.equal(
      text.includes('caller=dialogic_context_hint_extractor'),
      true,
      `authoritative dialogic caller must render on ${surface}`,
    );
    assert.equal(text.includes('sujet=dialogue'), true, `dialogue subject must render on ${surface}`);
    assert.equal(text.includes('identity_writer=false'), true, `non-writer status must render on ${surface}`);
    assert.equal(text.includes('canonique=false'), true, `non-canonical status must render on ${surface}`);
    assert.equal(text.includes('budget_tokens=120'), true, `selection budget must render on ${surface}`);
    assert.equal(text.includes('max_age_days=7'), true, `selection age must render on ${surface}`);
    assert.equal(text.includes('identity_writer=true'), false, `false writer claim forbidden on ${surface}`);
  };

  for (const currentStagingStatus of [
    "running",
    "judge_attempt_started",
    "terminal_discard_failed",
  ]) {
    const mockScript = hermeneuticAdminMockScript({ currentStagingStatus });
    const expectedChip = `buffer_status=${currentStagingStatus}`;

    await openBrowserPage({ pathSuffix: '/identity.html', mockScript }, async (page) => {
      await page.waitForFunction(() =>
        document.querySelector('#identityStatusBanner')?.textContent.includes('Lecture Identity ok'));
      const text = String(await page.locator('#identityRuntimeSummary').textContent() || '');
      assert.equal(text.includes(expectedChip), true, `${expectedChip} must render on /identity`);
      assert.equal(text.includes('buffer_status=ok'), false, 'active staging cannot render as ok');
      assertDialogicContext(text, '/identity');
    });

    await openBrowserPage({ pathSuffix: '/hermeneutic-admin.html', mockScript }, async (page) => {
      await page.waitForFunction(() =>
        document.querySelector('#hermeneuticAdminStatusBanner')?.textContent.includes('Lecture hermeneutique ok'));
      const text = String(await page.locator('#hermeneuticIdentityReadModel').textContent() || '');
      assert.equal(text.includes(expectedChip), true, `${expectedChip} must render on /hermeneutic-admin`);
      assert.equal(text.includes('buffer_status=ok'), false, 'active staging cannot render as ok');
      assertDialogicContext(text, '/hermeneutic-admin');
    });
  }
});
