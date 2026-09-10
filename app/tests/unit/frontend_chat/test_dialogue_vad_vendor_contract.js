'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const WEB_DIR = path.resolve(__dirname, '../../../web');
const VENDOR_DIR = path.join(WEB_DIR, 'vendor/dialogue-vad');
const EXPECTED_HASHES = Object.freeze({
  'LICENSE-ONNXRUNTIME.txt': '2f07c72751aed99790b8a4869cf2311df85a860b22ded05fa22803587a48922c',
  'LICENSE-VAD.txt': '239ebca4207803d3507124517c0dd6324c0d5cf73e1c486ade16bac1788f4a79',
  'ThirdPartyNotices-ONNXRUNTIME.txt': 'e9e90971a8e75a9a8ac0c6412e29c1202d079998389915aa485f46c816c3b4cc',
  'bundle.min.js': '206cf2ca0bacee64f115eba1769e33ce68bd979c9b53be31e6e0ec0edbab9ff8',
  'bundle.min.js.LICENSE.txt': '85d829adcdee0fe0a5caa95c238f9e4d49758f2b222944171f5d2e8f926e01b4',
  'ort-wasm-simd-threaded.mjs': '30dd851d9c00622940500f71ddd2ff8820c5cb65270816080175b958705385a8',
  'ort-wasm-simd-threaded.wasm': '71aef04959c5c1b6de461b6538e2058e306610034a85aad2742d0c7fd4533fe4',
  'ort.wasm.min.js': '65e09376df69107e881b5c34d2d37aed333a366b6d941073ec518168e269b87d',
  'silero_vad_v5.onnx': '2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f',
  'vad.worklet.bundle.min.js': '8a48fdc7429948a2fde3d29a84bb1a64c1f67b4ba578ccaa7548b7f989f06a74',
});

test('D3 vendor directory contains only the pinned local runtime and licenses', () => {
  const files = fs.readdirSync(VENDOR_DIR).sort();
  assert.deepEqual(files, [...Object.keys(EXPECTED_HASHES), 'MANIFEST.md'].sort());

  for (const [fileName, expectedHash] of Object.entries(EXPECTED_HASHES)) {
    const body = fs.readFileSync(path.join(VENDOR_DIR, fileName));
    const actualHash = crypto.createHash('sha256').update(body).digest('hex');
    assert.equal(actualHash, expectedHash, fileName);
  }

  const manifest = fs.readFileSync(path.join(VENDOR_DIR, 'MANIFEST.md'), 'utf8');
  assert.match(manifest, /@ricky0123\/vad-web@0\.0\.30/);
  assert.match(manifest, /onnxruntime-web@1\.22\.0/);
  assert.match(manifest, /The explicitly selected model is `v5`/);
  assert.doesNotMatch(manifest, /@latest|node_modules|\.tgz/);
});

test('D6.2b local V5 model has the pinned size and checksum', () => {
  const file = path.join(VENDOR_DIR, 'silero_vad_v5.onnx');
  assert.equal(fs.existsSync(file), true, 'the selected V5 model must exist locally');
  const bytes = fs.readFileSync(file);
  assert.equal(bytes.length, 2327524);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), EXPECTED_HASHES['silero_vad_v5.onnx']);
});

test('D6.2b manifest corrects the false legacy Safari calibration claim', () => {
  const manifest = fs.readFileSync(path.join(VENDOR_DIR, 'MANIFEST.md'), 'utf8');
  assert.doesNotMatch(manifest, /avoids silently changing the calibration used by the existing\s+Safari proof/);
  assert.match(manifest, /previous claim[^\n]*legacy[^\n]*Safari[^\n]*false/i);
  assert.match(manifest, /The explicitly selected model is `v5`/);
});

test('normal bootstrap has no VAD assets or required VAD global and product stays disabled', () => {
  const index = fs.readFileSync(path.join(WEB_DIR, 'index.html'), 'utf8');
  const scriptPaths = [
    'chat_dialogue_mode.js',
    'app.js',
  ];
  let previousIndex = -1;
  for (const scriptPath of scriptPaths) {
    const scriptIndex = index.indexOf(`<script src="${scriptPath}"></script>`);
    assert.ok(scriptIndex > previousIndex, `${scriptPath} must load in order`);
    previousIndex = scriptIndex;
  }
  assert.match(index, /id="btnDialogueMode"[^>]*disabled/);
  assert.doesNotMatch(index, /<script[^>]+(?:vendor\/dialogue-vad\/|dialogue\/dialogue_vad_)/);
  assert.doesNotMatch(index, /https?:\/\/[^"']*dialogue-vad/i);
});
