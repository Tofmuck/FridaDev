'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS,
  compactDocumentMeta,
  formatBytes,
  uploadInProgressLabel,
  uploadErrorLabel,
} = require('../../../web/chat_active_documents.js');

test('active document module keeps the supported upload vocabulary narrow', () => {
  assert.deepEqual(ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS, ['.pdf', '.docx', '.odt', '.md', '.txt']);
});

test('active document metadata stays compact and content-free', () => {
  const meta = compactDocumentMeta({
    filename: 'scan.pdf',
    source_extension: '.pdf',
    byte_size: 2048,
    text_chars: 42,
    ocr_applied: true,
    last_excluded_reason_code: '',
    text_content: 'RAW SHOULD NOT RENDER',
  });

  assert.equal(meta, 'PDF · 2 ko · 42 caractères · OCRisé · actif');
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

test('OCR upload states use human labels without fake progress', () => {
  assert.equal(uploadInProgressLabel([{ name: 'scan.pdf' }]), 'Analyse du PDF, OCR si nécessaire…');
  assert.equal(uploadInProgressLabel([{ name: 'note.txt' }]), 'Activation du document actif…');
  assert.equal(uploadInProgressLabel([{ name: 'scan.pdf' }]).includes('%'), false);
  assert.equal(uploadErrorLabel('document_ocr_failed'), 'OCR impossible.');
  assert.equal(uploadErrorLabel('document_ocr_timeout'), 'OCR trop long.');
  assert.equal(uploadErrorLabel('document_ocr_empty'), 'OCR sans texte lisible.');
  assert.equal(uploadErrorLabel('document_ocr_too_large'), "PDF trop volumineux pour l'OCR de conversation.");
  assert.equal(uploadErrorLabel('document_ocr_too_many_pages'), "PDF trop long pour l'OCR de conversation.");
  assert.equal(uploadErrorLabel('document_ocr_timeout').includes('document_ocr_timeout'), false);
});
