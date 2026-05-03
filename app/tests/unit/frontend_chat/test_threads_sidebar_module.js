const test = require("node:test");
const assert = require("node:assert/strict");

const {
  THREADS_PAGE_SIZE,
  MAX_TITLE_LENGTH,
  clampThreadTitle,
  normalizeThreadItem,
} = require("../../../web/chat_threads_sidebar.js");

test("threads sidebar module exposes the conversations page size contract", () => {
  assert.equal(THREADS_PAGE_SIZE, 200);
});

test("clampThreadTitle normalizes whitespace and preserves the fallback contract", () => {
  assert.equal(clampThreadTitle("  Mon   fil   "), "Mon fil");
  assert.equal(clampThreadTitle("   "), "Nouvelle conversation");
  assert.equal(clampThreadTitle("   ", ""), "");
});

test("clampThreadTitle truncates long labels without changing the max length", () => {
  const longTitle = "x".repeat(MAX_TITLE_LENGTH + 10);
  const clamped = clampThreadTitle(longTitle);

  assert.equal(clamped.length, MAX_TITLE_LENGTH + 1);
  assert.equal(clamped.endsWith("…"), true);
});

test("normalizeThreadItem keeps the stable sidebar shape and cached messages", () => {
  const cachedMessages = [{ role: "user", content: "bonjour", timestamp: null }];

  assert.deepEqual(
    normalizeThreadItem(
      {
        conversation_id: "conv-1",
        title: "  Titre ",
        created_at: "2026-05-03T10:00:00Z",
        message_count: "2",
        last_message_preview: "hello",
      },
      cachedMessages,
    ),
    {
      id: "conv-1",
      conversation_id: "conv-1",
      title: "Titre",
      messages: cachedMessages,
      created_at: "2026-05-03T10:00:00Z",
      updated_at: "2026-05-03T10:00:00Z",
      message_count: 2,
      last_message_preview: "hello",
      deleted_at: null,
    },
  );
});

test("normalizeThreadItem rejects malformed conversation identifiers", () => {
  assert.equal(normalizeThreadItem({ title: "sans id" }), null);
});
