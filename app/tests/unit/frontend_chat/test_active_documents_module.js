'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS,
  compactDocumentMeta,
  formatBytes,
  uploadInProgressLabel,
  uploadErrorLabel,
} = require('../../../web/chat_active_documents.js');

test('active document module keeps the supported upload vocabulary narrow', () => {
  assert.deepEqual(ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS, ['.pdf', '.docx', '.odt', '.md', '.txt', '.png', '.jpg', '.jpeg', '.webp']);
  assert.equal(ACTIVE_DOCUMENT_ACCEPTED_EXTENSIONS.includes('.gif'), false);
});

test('active document file input exposes V0 image types without GIF', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../../../web/index.html'), 'utf8');
  const inputMatch = indexHtml.match(/id="activeDocumentFileInput"[\s\S]*?accept="([^"]+)"/);
  assert.ok(inputMatch, 'active document file input should declare accepted types');
  const accept = inputMatch[1];

  for (const expected of ['.png', '.jpg', '.jpeg', '.webp', 'image/png', 'image/jpeg', 'image/webp']) {
    assert.ok(accept.includes(expected), `${expected} should be accepted`);
  }
  assert.equal(accept.includes('.gif'), false);
  assert.equal(accept.includes('image/gif'), false);
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

test('active image metadata renders dimensions without raw image content', () => {
  const meta = compactDocumentMeta({
    filename: 'capture.png',
    source_extension: '.png',
    media_kind: 'image',
    byte_size: 4096,
    text_chars: 0,
    image_width: 80,
    image_height: 64,
    content_sha256_12: '123456abcdef',
    binary_content: 'RAW SHOULD NOT RENDER',
  });

  assert.equal(meta, 'PNG · 4 ko · 80 x 64 px · Image active');
  assert.equal(meta.includes('RAW SHOULD NOT RENDER'), false);
  assert.equal(meta.includes('123456abcdef'), false);
});

test('active image exclusion metadata is explicit and content-free', () => {
  const meta = compactDocumentMeta({
    filename: 'capture.webp',
    source_extension: '.webp',
    media_kind: 'image',
    byte_size: 9 * 1024 * 1024,
    text_chars: 0,
    image_width: 2400,
    image_height: 1600,
    content_sha256_12: 'abcdef123456',
    last_excluded_reason_code: 'image_too_large_for_provider_payload',
    binary_content: 'RAW SHOULD NOT RENDER',
  });

  assert.equal(meta, 'WEBP · 9.0 Mo · 2400 x 1600 px · Image non injectée: Trop lourde pour ce tour.');
  assert.equal(meta.includes('RAW SHOULD NOT RENDER'), false);
  assert.equal(meta.includes('abcdef123456'), false);
  assert.equal(meta.includes('image_too_large_for_provider_payload'), false);
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
  assert.equal(uploadInProgressLabel([{ name: 'capture.png' }]), "Activation de l'image active…");
  assert.equal(uploadInProgressLabel([{ name: 'scan.pdf' }]).includes('%'), false);
  assert.equal(uploadErrorLabel('document_ocr_failed'), 'OCR impossible.');
  assert.equal(uploadErrorLabel('document_ocr_timeout'), 'OCR trop long.');
  assert.equal(uploadErrorLabel('document_ocr_empty'), 'OCR sans texte lisible.');
  assert.equal(uploadErrorLabel('document_ocr_too_large'), "PDF trop volumineux pour l'OCR de conversation.");
  assert.equal(uploadErrorLabel('document_ocr_too_many_pages'), "PDF trop long pour l'OCR de conversation.");
  assert.equal(uploadErrorLabel('active_document_upload_too_large'), 'Upload trop volumineux.');
  assert.equal(uploadErrorLabel('image_gif_unsupported_v0'), 'GIF hors V0 pour les images actives.');
  assert.equal(uploadErrorLabel('image_too_small_for_provider'), 'Image trop petite.');
  assert.equal(uploadErrorLabel('image_model_unsupported'), 'Modèle actuel sans lecture image.');
  assert.equal(uploadErrorLabel('image_bytes_missing'), 'Image indisponible.');
  assert.equal(uploadErrorLabel('image_too_large_for_provider_payload'), 'Trop lourde pour ce tour.');
  assert.equal(uploadErrorLabel('document_ocr_timeout').includes('document_ocr_timeout'), false);
});
