'use strict';

function createDialogueAudioClient({ fetchFn = (...args) => fetch(...args) } = {}) {
  const transcribe = async (blob, { signal } = {}) => {
    if (!(blob instanceof Blob) || blob.type !== 'audio/wav'
        || blob.size <= 0 || blob.size > 24_000_000) {
      throw new Error('dialogue_stt_invalid_audio');
    }
    try {
      if (signal?.aborted) throw new Error();
      const body = new FormData();
      body.append('audio', blob, 'dialogue.wav');
      const response = await fetchFn('/api/chat/dialogue/transcribe', {
        method: 'POST', body, signal,
      });
      if (!response.ok || response.headers.get('content-type')?.split(';')[0].trim().toLowerCase()
          !== 'application/json') throw new Error();
      const data = await response.json();
      if (signal?.aborted || data?.ok !== true || typeof data.text !== 'string') throw new Error();
      return data.text;
    } catch (_error) {
      // Never project transport exceptions or provider response content.
      throw new Error('dialogue_stt_unavailable');
    }
  };
  const synthesize = async (text, { signal } = {}) => {
    if (typeof text !== 'string' || text === '' || Array.from(text).length > 16_000
        || (/^\s*$/u.test(text) && !text.includes('\ufeff'))) {
      throw new Error('dialogue_tts_invalid_text');
    }
    try {
      if (signal?.aborted) throw new Error();
      const response = await fetchFn('/api/chat/dialogue/speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal,
      });
      if (response.status !== 200
          || response.headers.get('content-type')?.split(';')[0].trim().toLowerCase()
          !== 'audio/mpeg') throw new Error();
      const blob = await response.blob();
      if (signal?.aborted || !(blob instanceof Blob)
          || blob.size <= 0 || blob.size > 16 * 1024 * 1024) throw new Error();
      return blob;
    } catch (_error) {
      // Never project transport exceptions or provider response content.
      throw new Error('dialogue_tts_unavailable');
    }
  };
  return Object.freeze({ transcribe, synthesize });
}

const FridaDialogueAudioClient = Object.freeze({ createDialogueAudioClient });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDialogueAudioClient;
if (typeof window !== 'undefined') window.FridaDialogueAudioClient = FridaDialogueAudioClient;
