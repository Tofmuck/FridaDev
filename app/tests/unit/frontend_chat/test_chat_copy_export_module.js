'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildConversationMarkdown,
  buildMarkdownFilename,
  copyTextToClipboard,
  exportableMessages,
} = require('../../../web/chat_copy_export.js');

test('buildConversationMarkdown exports a readable conversation without technical metadata', () => {
  const markdown = buildConversationMarkdown({
    exportedAt: new Date('2026-05-17T10:42:00Z'),
    messages: [
      {
        role: 'system',
        content: 'TECHNICAL SYSTEM PROMPT SHOULD NOT EXPORT',
        timestamp: '2026-05-16T21:53:00Z',
        id: 'system-id',
      },
      {
        role: 'user',
        content: 'Bonsoir Frida.',
        timestamp: '2026-05-16T21:54:00Z',
        conversation_id: 'conv-secret-id',
      },
      {
        role: 'assistant',
        content: 'Bonsoir Tof.\n\n# Markdown gardé comme texte du message',
        timestamp: '2026-05-16T21:54:30Z',
        meta: { hash: 'abc123' },
      },
    ],
  });

  assert.match(markdown, /^# Conversation avec Frida\n\nExportée le /);
  assert.match(markdown, /## Tof — .*21:54/);
  assert.match(markdown, /## Frida — .*21:54/);
  assert.match(markdown, /Bonsoir Frida\./);
  assert.match(markdown, /# Markdown gardé comme texte du message/);
  assert.equal(markdown.includes('TECHNICAL SYSTEM PROMPT SHOULD NOT EXPORT'), false);
  assert.equal(markdown.includes('conversation_id'), false);
  assert.equal(markdown.includes('conv-secret-id'), false);
  assert.equal(markdown.includes('hash'), false);
  assert.equal(markdown.includes('abc123'), false);
});

test('exportableMessages keeps only user and assistant text', () => {
  assert.deepEqual(
    exportableMessages([
      { role: 'system', content: 'hidden' },
      { role: 'user', content: 'hello', timestamp: '2026-05-17T10:00:00Z' },
      { role: 'assistant', content: 'hi' },
      { role: 'tool', content: 'payload' },
    ]),
    [
      { role: 'user', content: 'hello', timestamp: '2026-05-17T10:00:00Z' },
      { role: 'assistant', content: 'hi', timestamp: null },
    ],
  );
});

test('copyTextToClipboard copies only the provided bubble text', async () => {
  const writes = [];
  const copied = await copyTextToClipboard('Texte de la bulle', {
    navigatorObj: {
      clipboard: {
        writeText: async (text) => writes.push(text),
      },
    },
  });

  assert.equal(copied, true);
  assert.deepEqual(writes, ['Texte de la bulle']);
});

test('buildMarkdownFilename uses a stable markdown extension', () => {
  assert.equal(buildMarkdownFilename(new Date('2026-05-17T10:42:00Z')), 'frida-conversation-2026-05-17-10-42.md');
});
