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
  return Object.freeze({ transcribe });
}

const FridaDialogueAudioClient = Object.freeze({ createDialogueAudioClient });
if (typeof module !== 'undefined' && module.exports) module.exports = FridaDialogueAudioClient;
if (typeof window !== 'undefined') window.FridaDialogueAudioClient = FridaDialogueAudioClient;
