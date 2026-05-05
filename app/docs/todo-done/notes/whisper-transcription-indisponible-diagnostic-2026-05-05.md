# Diagnostic "transcription indisponible" - 2026-05-05

## Resume

- statut: cause confirmee cote FridaDev
- symptome utilisateur: bouton micro visible, message rouge `transcription indisponible`
- impact: la dictee vocale ne peut pas produire de transcript exploitable
- lien avec Claude/main_model: aucun lien observe
- correctif applique: aucun, diagnostic read-only

## Cause confirmee

`/api/chat/transcribe` fonctionne et appelle bien le service aval `platform-whisper-api`, mais le service aval renvoie:

```text
HTTP 500 {"detail":"transcription failed: exit code -9"}
```

FridaDev convertit ce 500 upstream en:

```text
HTTP 502 {"error":"transcription indisponible","ok":false}
```

Le conteneur `platform-whisper-api` est joignable et son `/health` repond `200`, mais son endpoint de transcription echoue pendant l'execution du backend `whisper-cli`.

Preuve complementaire plateforme, sans secret affiche:

```text
platform-whisper-api memory_limit_bytes=536870912
platform-whisper-api oom_killed=true
```

Conclusion: la panne n'est pas un probleme de frontend dictation, permission micro, CORS, endpoint absent, cle Whisper absente, ou bascule Claude. La panne est dans le service de transcription aval `platform-whisper-api`, avec un echec de processus `exit code -9` compatible avec une contrainte memoire/kill du backend Whisper.

## Chemin runtime

1. `app/web/index.html` charge `whisper/whisper_dictation.js`.
2. `app/web/app.js` branche le bouton micro sur `/api/chat/transcribe`.
3. `app/web/whisper/whisper_dictation.js` capture l'audio via `MediaRecorder`, poste un `FormData(file)` et affiche l'erreur JSON renvoyee par le backend.
4. `app/server.py` expose `POST /api/chat/transcribe`.
5. `app/core/whisper_transcription_service.py` poste vers `WHISPER_API_URL/v1/audio/transcriptions`.
6. `app/config.py` pointe par defaut vers `http://platform-whisper-api:9001`.

## Exclusions verifiees

- Endpoint Frida absent: faux, `POST /api/chat/transcribe` existe.
- Navigateur non compatible: non indique par ce message; le frontend afficherait `Dictee vocale indisponible sur ce navigateur`.
- Permission micro refusee: non indique par ce message; le frontend afficherait `Acces au micro refuse`.
- Micro absent ou indisponible: non indique par ce message; le frontend afficherait `Aucun micro disponible` ou `Micro indisponible`.
- Cle Whisper absente: faux dans l'environnement verifie; la cle est presente/redacted.
- Reseau Docker Frida -> Whisper casse: faux, socket OK et `/health` OK.
- Bascule Claude/main_model: aucun lien de code avec ce chemin de transcription.

## Commandes de preuve executees

```bash
git fetch origin main
git pull --ff-only origin main
git status --short

docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" | grep -Ei 'whisper|fridadev|transcri|audio' || true

docker exec -i platform-fridadev python - <<'PY'
import config
print('WHISPER_API_URL=' + repr(getattr(config, 'WHISPER_API_URL', None)))
print('WHISPER_API_TIMEOUT_S=' + repr(getattr(config, 'WHISPER_API_TIMEOUT_S', None)))
print('WHISPER_API_KEY=' + ('present/redacted' if getattr(config, 'WHISPER_API_KEY', '') else 'absent'))
PY

docker exec -i platform-fridadev python - <<'PY'
from urllib.parse import urlparse
import socket, config
url = getattr(config, 'WHISPER_API_URL', '')
parsed = urlparse(url)
host = parsed.hostname
port = parsed.port or (443 if parsed.scheme == 'https' else 80)
with socket.create_connection((host, port), timeout=5):
    print('socket_connect=ok')
PY

docker exec -i platform-fridadev python - <<'PY'
import requests
r = requests.get('http://platform-whisper-api:9001/health', timeout=5)
print('status=' + str(r.status_code))
print(r.text[:200])
PY
```

Reproduction avec audio synthetique non prive:

```bash
docker exec -i platform-fridadev python - <<'PY'
import io
import wave
import requests

buf = io.BytesIO()
with wave.open(buf, 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b'\x00\x00' * 16000)
buf.seek(0)

files = {'file': ('diagnostic-silence.wav', buf.getvalue(), 'audio/wav')}
resp = requests.post('http://127.0.0.1:8089/api/chat/transcribe', files=files, timeout=140)
print('frida_status=' + str(resp.status_code))
print('frida_body=' + resp.text[:400])
PY
```

Resultat:

```text
frida_status=502
frida_body={"error":"transcription indisponible","ok":false}
```

Appel direct upstream authentifie, sans afficher la cle:

```bash
docker exec -i platform-fridadev python - <<'PY'
import io
import wave
import requests
import config

buf = io.BytesIO()
with wave.open(buf, 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b'\x00\x00' * 16000)
buf.seek(0)

headers = {}
if getattr(config, 'WHISPER_API_KEY', ''):
    headers['Authorization'] = 'Bearer ' + config.WHISPER_API_KEY
files = {'file': ('diagnostic-silence.wav', buf.getvalue(), 'audio/wav')}
data = {'model': 'whisper-1', 'response_format': 'json'}
resp = requests.post('http://platform-whisper-api:9001/v1/audio/transcriptions', headers=headers, files=files, data=data, timeout=140)
print('upstream_status=' + str(resp.status_code))
print('upstream_body=' + resp.text[:400])
PY
```

Resultat:

```text
upstream_status=500
upstream_body={"detail":"transcription failed: exit code -9"}
```

## Tests de non-regression executes

```bash
docker exec platform-fridadev python tests/integration/frontend_chat/test_frontend_chat_contract.py
docker exec platform-fridadev python tests/integration/frontend_chat/test_frontend_whisper_contract.py
docker exec platform-fridadev python tests/integration/chat/test_chat_transcription_route.py
node --test app/tests/unit/frontend_chat/test_whisper_dictation_module.js app/tests/unit/frontend_chat/test_stream_control_parser_module.js app/tests/unit/frontend_chat/test_streaming_ui_state_module.js app/tests/unit/frontend_chat/test_threads_sidebar_module.js
npm run test:frontend-browser
```

Tous les tests ont passe pendant le diagnostic.

## Correctif minimal propose

Le correctif n'est pas un patch FridaDev applicatif. Il doit etre cadre cote plateforme avec Sauron:

- verifier les limites memoire et swap de `platform-whisper-api`;
- augmenter les ressources du conteneur ou reduire le cout runtime du backend `whisper-cli`;
- verifier le modele Whisper charge, les threads et la consommation memoire lors d'une transcription reelle;
- relancer ensuite une preuve `POST /api/chat/transcribe` avec audio synthetique, puis une preuve navigateur.

Tant que `platform-whisper-api` renvoie `500 transcription failed: exit code -9`, FridaDev affichera correctement `transcription indisponible`.

## Limites

- Pas de modification Caddy, Authelia, Docker, secrets ou runtime settings.
- Pas de lecture de `.env`, token, cookie, DSN complet ou cle.
- Pas de test navigateur micro reel execute depuis l'agent; la cause backend est deja reproduite sans dependance au navigateur.
