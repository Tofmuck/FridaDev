'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS,
  compactDocumentMeta,
  formatBytes,
  uploadErrorLabel,
} = require('../../../web/chat_active_documents.js');

test('active document module keeps the supported upload vocabulary narrow', () => {
  assert.deepEqual(ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS, ['.pdf', '.docx', '.odt', '.md', '.txt']);
});

test('active document metadata stays compact and content-free', () => {
  const meta = compactDocumentMeta({
    filename: 'note.md',
    source_extension: '.md',
    byte_size: 2048,
    text_chars: 42,
    last_excluded_reason_code: '',
    text_content: 'RAW SHOULD NOT RENDER',
  });

  assert.equal(meta, 'MD · 2 ko · 42 caractères · actif');
  assert.equal(meta.includes('RAW SHOULD NOT RENDER'), false);
});

test('active document warning states use human labels rather than raw reason codes', () => {
  const meta = compactDocumentMeta({
    source_extension: '.pdf',
    byte_size: 1024,
    text_chars: 0,
    last_excluded_reason_code: 'document_too_large_for_turn',
  });

  assert.equal(meta, 'PDF · 1 ko · Trop gros pour ce tour.');
  assert.equal(meta.includes('document_too_large_for_turn'), false);
  assert.equal(uploadErrorLabel('document_ocr_required'), 'PDF scanné: OCR requis.');
  assert.equal(formatBytes(1536), '2 ko');
});
