'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { openBrowserPage } = require('./helpers/browser_test_helpers.js');

const STREAM_CONTROL_PREFIX = '\x1e';

function adobeMockScript() {
  const terminal = `${STREAM_CONTROL_PREFIX}${JSON.stringify({
    kind: 'frida-stream-control',
    event: 'done',
    updated_at: '2026-05-23T12:00:00Z',
  })}\n`;
  const streamBody = `Réponse Adobe UI${terminal}`;
  return `
    (() => {
      const encoder = new TextEncoder();
      const state = {
        chatPosts: [],
        fetchCalls: [],
      };
      window.__fridaAdobeUiState = state;
      window.fetch = async (input, init = {}) => {
        const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
        const method = String(init.method || "GET").toUpperCase();
        const body = typeof init.body === "string" ? init.body : "";
        state.fetchCalls.push({ method, path: url.pathname, search: url.search, body });

        if (url.pathname === "/api/admin/settings/main-model" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            payload: { reasoning_effort: { value: "high" } },
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/workspace-folders" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations" && method === "GET") {
          return new Response(JSON.stringify({
            ok: true,
            items: [{
              id: "conv-adobe-ui",
              conversation_id: "conv-adobe-ui",
              title: "Adobe UI",
              created_at: "2026-05-23T11:00:00Z",
              updated_at: "2026-05-23T11:00:00Z",
              message_count: 0,
              last_message_preview: "",
            }],
          }), { status: 200, headers: { "Content-Type": "application/json" } });
        }

        if (url.pathname === "/api/conversations/conv-adobe-ui/messages" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, messages: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/conversations/conv-adobe-ui/active-documents" && method === "GET") {
          return new Response(JSON.stringify({ ok: true, conversation_id: "conv-adobe-ui", items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.pathname === "/api/chat" && method === "POST") {
          let payload = {};
          try {
            payload = JSON.parse(body || "{}");
          } catch {
            payload = {};
          }
          state.chatPosts.push(payload);
          return new Response(encoder.encode(${JSON.stringify(streamBody)}), {
            status: 200,
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
              "X-Conversation-Id": "conv-adobe-ui",
              "X-Conversation-Created-At": "2026-05-23T11:00:00Z",
            },
          });
        }

        throw new Error("Unexpected fetch " + method + " " + url.pathname + url.search);
      };
    })();
  `;
}

async function submitMessage(page, text, expectedCount) {
  await page.fill('#message', text);
  await page.click('#ask button[type="submit"]');
  await page.waitForFunction(
    (count) => window.__fridaAdobeUiState.chatPosts.length >= count,
    expectedCount,
  );
}

test('Adobe mode sends explicit product payloads and clears them when disabled', async () => {
  await openBrowserPage({
    mockScript: adobeMockScript(),
    afterPage: (page) => page.setViewportSize({ width: 1440, height: 900 }),
  }, async (page) => {
    await page.waitForSelector('#message:not([disabled])');

    assert.equal(await page.locator('#adobeProductChoices').isHidden(), true);
    assert.equal(await page.locator('#btnAdobeMode').getAttribute('aria-pressed'), 'false');

    await submitMessage(page, 'Message normal', 1);
    let posts = await page.evaluate(() => window.__fridaAdobeUiState.chatPosts);
    assert.equal(Object.hasOwn(posts[0], 'specialization_profile'), false);
    assert.equal(Object.hasOwn(posts[0], 'adobe_product'), false);

    await page.click('#btnWebSearch');
    assert.equal(await page.locator('#btnWebSearch').getAttribute('aria-pressed'), 'true');
    await page.click('#btnAdobeMode');
    assert.equal(await page.locator('#adobeProductChoices').isVisible(), true);
    await page.click('[data-adobe-product="photoshop"]');
    assert.equal(await page.locator('#btnAdobeMode').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#btnWebSearch').isDisabled(), true);
    assert.equal(await page.locator('#btnWebSearch').getAttribute('aria-pressed'), 'false');

    await submitMessage(page, 'Question Photoshop', 2);
    posts = await page.evaluate(() => window.__fridaAdobeUiState.chatPosts);
    assert.equal(posts[1].specialization_profile, 'adobe');
    assert.equal(posts[1].adobe_product, 'photoshop');
    assert.equal(posts[1].web_search, false);

    await page.click('[data-adobe-product="illustrator"]');
    await submitMessage(page, 'Question Illustrator', 3);
    posts = await page.evaluate(() => window.__fridaAdobeUiState.chatPosts);
    assert.equal(posts[2].specialization_profile, 'adobe');
    assert.equal(posts[2].adobe_product, 'illustrator');

    await page.click('#btnAdobeMode');
    assert.equal(await page.locator('#adobeProductChoices').isHidden(), true);
    assert.equal(await page.locator('#btnWebSearch').isDisabled(), false);
    await submitMessage(page, 'Adobe off', 4);
    posts = await page.evaluate(() => window.__fridaAdobeUiState.chatPosts);
    assert.equal(Object.hasOwn(posts[3], 'specialization_profile'), false);
    assert.equal(Object.hasOwn(posts[3], 'adobe_product'), false);
  });
});

test('Adobe composer controls stay in bounds on desktop and mobile', async () => {
  for (const viewport of [
    { width: 1440, height: 900, name: 'desktop' },
    { width: 390, height: 780, name: 'mobile' },
  ]) {
    await openBrowserPage({
      mockScript: adobeMockScript(),
      afterPage: (page) => page.setViewportSize({ width: viewport.width, height: viewport.height }),
    }, async (page) => {
      await page.waitForSelector('#message:not([disabled])');
      await page.click('#btnAdobeMode');
      await page.click('[data-adobe-product="photoshop"]');

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
        return {
          viewportWidth: window.innerWidth,
          ask: rect('#ask'),
          message: rect('#message'),
          choices: rect('#adobeProductChoices'),
          actions: rect('.composer-actions'),
          adobe: rect('#btnAdobeMode'),
          submit: rect('#ask button[type="submit"]'),
        };
      });

      assert.ok(layout.ask.left >= 0, `${viewport.name} composer should stay inside left viewport edge`);
      assert.ok(layout.ask.right <= layout.viewportWidth + 1, `${viewport.name} composer should stay inside right viewport edge`);
      assert.ok(layout.message.left >= layout.ask.left, `${viewport.name} textarea should stay inside composer`);
      assert.ok(layout.message.right <= layout.ask.right + 1, `${viewport.name} textarea should stay inside composer`);
      assert.ok(layout.message.bottom <= layout.actions.top + 1, `${viewport.name} action row should sit below textarea`);
      assert.ok(layout.choices.left >= layout.ask.left, `${viewport.name} Adobe choices should stay inside composer`);
      assert.ok(layout.choices.right <= layout.ask.right + 1, `${viewport.name} Adobe choices should stay inside composer`);
      assert.ok(layout.adobe.left >= layout.actions.left, `${viewport.name} Adobe button should stay inside action row`);
      assert.ok(layout.submit.right <= layout.actions.right + 1, `${viewport.name} submit should stay inside action row`);
    });
  }
});
