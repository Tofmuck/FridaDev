# Dialogue VAD vendored runtime

This directory contains the complete, same-origin runtime selected for Lot D3.
It is intentionally not an npm installation and must not acquire assets from a
CDN at runtime.

## Pinned packages

- `@ricky0123/vad-web@0.0.30`
  - upstream tag: `@ricky0123/vad-web/v0.0.30`
  - npm integrity:
    `sha512-cJyYrh4YeeUBJcbR9Bic/bFDyB9qBkAepvpuWM3vLxnAi7bC3VHzf51UeNdT+OtY4D7MLAgV8iJMc4z41ZnaWg==`
  - license: ISC; the vendored Silero model is MIT
- `onnxruntime-web@1.22.0`
  - upstream tag: `v1.22.0`
  - npm integrity:
    `sha512-Ud/+EBo6mhuaQWt/OjaOk0iNWjXqJoeeMFr6xQEERZdIZH2OWpGzuujz7lfuOBjUa6TEE/sc4nb7Da5dNL34fg==`
  - license: MIT

The explicitly selected model is `v5`, corrected by D6.2b on 10 September 2026.
The previous claim linking legacy to the validated Safari calibration was false.
The official demonstrator source selects V5 with positive and negative speech
probability thresholds both at 0.4. Tof reports the distinct Safari iPhone
material validation; this correction does not claim a new hardware test.
Only the WASM execution path is included; JSEP, WebGPU, source maps,
development builds, archives, and the unused legacy model are absent.

V5 is extracted unchanged from `package/dist/silero_vad_v5.onnx` in the npm
0.0.30 distribution after verification of the package integrity above:
2,327,524 bytes. Bundle and worklet retain their exact pinned bytes.
The runtime keeps AudioWorklet, `startOnLoad: false`, and the millisecond
options 800 / 1400 / 400 (pre-speech / redemption / minimum speech).
V5 frames contain 512 samples at 16 kHz (32 ms): the pinned segmenter floors
these options to 25 / 43 / 12 frames. No obsolete frame-count input options,
volume filter or alternative model path is added.

Sources: [algorithm](https://github.com/ricky0123/vad/blob/master/docs/user-guide/algorithm.md),
[official demo source](https://github.com/ricky0123/vad/blob/8941bbf9116234748934d6b563c1751ce4d43c35/test-site/src/script-tags-example/index.html),
[pinned npm metadata](https://registry.npmjs.org/@ricky0123/vad-web/0.0.30).

## SHA-256

```text
2f07c72751aed99790b8a4869cf2311df85a860b22ded05fa22803587a48922c  LICENSE-ONNXRUNTIME.txt
239ebca4207803d3507124517c0dd6324c0d5cf73e1c486ade16bac1788f4a79  LICENSE-VAD.txt
e9e90971a8e75a9a8ac0c6412e29c1202d079998389915aa485f46c816c3b4cc  ThirdPartyNotices-ONNXRUNTIME.txt
206cf2ca0bacee64f115eba1769e33ce68bd979c9b53be31e6e0ec0edbab9ff8  bundle.min.js
85d829adcdee0fe0a5caa95c238f9e4d49758f2b222944171f5d2e8f926e01b4  bundle.min.js.LICENSE.txt
30dd851d9c00622940500f71ddd2ff8820c5cb65270816080175b958705385a8  ort-wasm-simd-threaded.mjs
71aef04959c5c1b6de461b6538e2058e306610034a85aad2742d0c7fd4533fe4  ort-wasm-simd-threaded.wasm
65e09376df69107e881b5c34d2d37aed333a366b6d941073ec518168e269b87d  ort.wasm.min.js
2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f  silero_vad_v5.onnx
8a48fdc7429948a2fde3d29a84bb1a64c1f67b4ba578ccaa7548b7f989f06a74  vad.worklet.bundle.min.js
```

`MANIFEST.md` is excluded from its own checksum list. Verify the retained
artifacts with:

```bash
sha256sum LICENSE-ONNXRUNTIME.txt LICENSE-VAD.txt \
  ThirdPartyNotices-ONNXRUNTIME.txt bundle.min.js \
  bundle.min.js.LICENSE.txt ort-wasm-simd-threaded.mjs \
  ort-wasm-simd-threaded.wasm ort.wasm.min.js \
  silero_vad_v5.onnx vad.worklet.bundle.min.js
```

The upstream MJS contains one whitespace-only line. The repository-level
`.gitattributes` disables whitespace diagnostics for that exact immutable file
only, so `git diff --check` can remain strict without changing its pinned bytes.
