# FridaDev - model call catalog - 2026-05-17

## Resume executif

Cet audit cartographie les appels modele et services d'inference reellement presents dans FridaDev au 2026-05-17, sur la working copy OVH `/opt/platform/fridadev` et le runtime vivant `platform-fridadev`.

Verdict court:

- FridaDev expose **11 chemins fonctionnels d'inference**, correspondant a **13 slots modele/service** si l'on compte separement les modeles primaire/fallback du `stimmung_agent` et du `validation_agent`.
- Les chemins OpenRouter partagent aujourd'hui **un seul secret applicatif**: `main_model.api_key`.
- Sur OVH, ce secret est configure et resolu via les runtime settings chiffrés (`db_encrypted`), avec origine historique `env_backfill`. Le repo ne prouve pas a lui seul la separation ou non des projets cote console OpenRouter.
- Le systeme est fonctionnel mais heterogene: certains callers utilisent `llm_client.or_chat_completions_url()` et donc `main_model.base_url` runtime; d'autres utilisent encore `config.OR_BASE`.
- Plusieurs sections runtime admin existent, mais tous leurs champs ne sont pas encore la source effective du call. Exemple important: `arbiter_model.timeout_s` vaut `60` sur OVH mais les chemins `arbiter`, `identity_extractor` et `identity_periodic_agent` utilisent encore `config.ARBITER_TIMEOUT_S` (`10`).

## Perimetre et methode

La methode retenue est audit-first, docs-only. La question prealable etait: **existe-t-il un meilleur plan ?** Pour ce lot, oui: cartographier depuis les vrais points d'appel avant toute rotation de token ou normalisation de configuration.

Sources inspectees:

- code d'appel: `app/core/llm_client.py`, `app/core/chat_llm_flow.py`, `app/core/chat_service.py`, `app/tools/web_search.py`, `app/memory/arbiter.py`, `app/memory/summarizer.py`, `app/core/stimmung_agent.py`, `app/core/hermeneutic_node/validation/validation_agent.py`, `app/memory/memory_store_infra.py`, `app/core/whisper_transcription_service.py`, `app/core/active_document_ocr_client.py`;
- configuration: `app/config.py`, `app/config.example.py`, `app/.env.example`;
- runtime settings: `app/admin/runtime_settings*.py`;
- prompts: `app/prompts/*.txt`;
- tests de contrat autour des callers principaux;
- lecture runtime OVH assainie via `docker exec platform-fridadev`, sans afficher de secret.

Ce que l'audit prouve:

- les chemins de code qui peuvent appeler un provider ou un service d'inference;
- les modeles et parametres effectifs lus dans le runtime OVH;
- la source de verite applicative des secrets;
- les contrats de sortie parses/valides cote FridaDev.

Ce que l'audit ne prouve pas:

- le projet OpenRouter exact rattache au token dans la console externe;
- les droits, quotas, budgets ou routages internes du compte OpenRouter;
- le modele interne reel de services hors FridaDev quand le service ne l'expose pas dans son contrat applicatif, par exemple le backend Whisper ou Stirling.

## Carte complete des modeles et services

### Synthese des slots actifs

La table ci-dessous liste les **slots modele/service** observables. Les **11 chemins fonctionnels** regroupent `stimmung_agent` primary/fallback en un seul chemin et `validation_agent` primary/fallback en un seul chemin: chat principal, reformulation web, arbitre memoire, resume, extracteur identity, agent periodic identity, stimmung, validation, embeddings, Whisper, OCR.

| # | Slot modele/service | Type | Caller / fichier principal | Modele ou service runtime OVH | Statut |
|---|---|---|---|---|---|
| 1 | Chat principal | OpenRouter chat completion | `app/core/chat_llm_flow.py` | `anthropic/claude-sonnet-4.6` | actif |
| 2 | Reformulation web | OpenRouter chat completion | `app/tools/web_search.py` | `openai/gpt-5.4-mini` | actif quand web active |
| 3 | Arbitre memoire | OpenRouter chat completion | `app/memory/arbiter.py` | `openai/gpt-5.4-mini` | actif |
| 4 | Resume conversationnel | OpenRouter chat completion | `app/memory/summarizer.py` | `openai/gpt-5.4-mini` | actif au seuil de summary |
| 5 | Extracteur identity | OpenRouter chat completion | `app/memory/arbiter.py` | `openai/gpt-5.4-mini` | actif apres tour assistant |
| 6 | Agent periodic identity | OpenRouter chat completion | `app/memory/arbiter.py` via `memory_identity_periodic_agent.py` | `openai/gpt-5.4-mini` | actif quand buffer atteint le seuil |
| 7 | Stimmung agent primaire | OpenRouter chat completion | `app/core/stimmung_agent.py` | `openai/gpt-5.4-mini` | actif avant noeud hermeneutique |
| 8 | Stimmung agent fallback | OpenRouter chat completion | `app/core/stimmung_agent.py` | `openai/gpt-5.4-nano` | fallback |
| 9 | Validation agent primaire | OpenRouter chat completion | `app/core/hermeneutic_node/validation/validation_agent.py` | `openai/gpt-5.4-mini` | actif dans noeud hermeneutique |
| 10 | Validation agent fallback | OpenRouter chat completion | meme fichier | `openai/gpt-5.4-nano` | fallback |
| 11 | Embeddings Memory/RAG | service embedding HTTP | `app/memory/memory_store_infra.py` | `intfloat/multilingual-e5-small`, dim `384` | actif |
| 12 | Transcription vocale | service Whisper HTTP | `app/core/whisper_transcription_service.py` | payload `model=whisper-1` | actif si dictation |
| 13 | OCR PDF active documents | service Stirling PDF HTTP | `app/core/active_document_ocr_client.py` | `platform-stirling-pdf` OCR, modele interne non expose | actif sur `document_ocr_required` |

Chemins explicitement absents ou retires:

- **Reranker Memory/RAG**: absent; decision documentaire `no-go for now` dans `app/docs/states/project/memory-rag-reranker-decision-2026-04-11.md`.
- **Identity mutable rewriter LLM**: retire; `app/memory/memory_identity_mutable_rewriter.py` et `rewrite_identity_mutables()` ne declenchent plus d'appel modele.
- **Biblio native / Catalogue**: chantier actif documentaire, aucun call modele Biblio nominal dans FridaDev.

## Tableau exhaustif principal

> `Runtime OVH` vient d'une lecture assainie des settings et constantes dans le conteneur. Les secrets sont notes `set/unset`, jamais affiches.

| Role | Caller / fichier | Prompt | Provider | Modele effectif runtime OVH | Defaut code / seed | Source config runtime | Token / auth source | Temperature | top_p | Max tokens | Timeout | Raisonnement | Stream | Output contract | Admin configurable | Observabilite |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|---|---|---|
| Chat principal | `chat_llm_flow.run_llm_exchange()` | `MAIN_SYSTEM_PROMPT_PATH`, `main_hermeneutical.txt`, prompt window runtime | OpenRouter | `anthropic/claude-sonnet-4.6` | `OPENROUTER_MODEL=openai/gpt-5.1` | `main_model.model` runtime DB | `main_model.api_key`, resolu `db_encrypted`; header caller `llm` | `0.4` | `1.0` | `8192` par defaut, override request possible | `FRIDA_TIMEOUT=900` | aucun parametre `reasoning` envoye | oui, si `stream=true` | texte libre assistant, normalise puis persiste | oui: `main_model.model`, sampling, response max, headers; base_url runtime existe mais ce call utilise encore `config.OR_BASE` | `llm_payload`, `llm_call`, `llm_provider_response`, `AssistantText`, stream events |
| Reformulation web | `web_search.reformulate()` | `prompts/web_reformulation.txt` | OpenRouter | `openai/gpt-5.4-mini` | `WEB_REFORMULATION_MODEL=openai/gpt-5.4-mini` | `web_reformulation_model.model`; base via `llm_client.or_chat_completions_url()` | `main_model.api_key`, caller `web_reformulation` | `0.2` | non envoye | `40` | `10` | aucun | non | texte court, fallback vers message utilisateur si erreur | oui: `web_reformulation_model` pour model/temp/max/timeout; transport/token partages via `main_model`; referer/title web restent config-only | `web_reformulation_prompt_prepared`, `web_search` |
| Arbitre memoire | `arbiter.filter_traces_with_diagnostics()` | `prompts/arbiter.txt` | OpenRouter | `openai/gpt-5.4-mini` | `ARBITER_MODEL=openai/gpt-5.4-mini` | `arbiter_model.model` runtime DB | `main_model.api_key`, caller `arbiter` | `0.0` fixe | `1.0` fixe | `600` fixe | `config.ARBITER_TIMEOUT_S=10` effectif; runtime admin affiche `60` mais non utilise ici | aucun | non | JSON `decisions[]`, puis post-filtrage deterministe | modele oui; temp/top_p/timeout exposes mais temp/top_p/timeout non sources effectives du payload courant | provider logs, metrics, `record_arbiter_decisions()` |
| Resume conversationnel | `summarizer.summarize_conversation()` | `prompts/summary_system.txt` | OpenRouter | `openai/gpt-5.4-mini` | `SUMMARY_MODEL=openai/gpt-5.4-mini` | `summary_model.model` runtime DB | `main_model.api_key`, caller `resumer` | `0.3` fixe | `1.0` fixe | `SUMMARY_TARGET_TOKENS=2000` | `90` fixe | aucun | non | texte libre de resume; persiste en summary actif | modele oui; temp/top_p exposes mais non sources effectives | provider metadata log; summary persistence |
| Extracteur identity | `arbiter.extract_identities()` | `prompts/identity_extractor.txt` | OpenRouter | `openai/gpt-5.4-mini` | reutilise `ARBITER_MODEL` | `arbiter_model.model` runtime DB | `main_model.api_key`, caller `identity_extractor` | `0.0` fixe | `1.0` fixe | `700` fixe | `config.ARBITER_TIMEOUT_S=10` | aucun | non | JSON `entries[]`; invalides skips; erreur => `[]` | indirect via `arbiter_model.model`; pas de section modele dediee | provider log, metrics parse/call; staging identity |
| Agent periodic identity | `arbiter.run_identity_periodic_agent()` | `prompts/identity_periodic_agent.txt` | OpenRouter | `openai/gpt-5.4-mini` | reutilise `ARBITER_MODEL` | `arbiter_model.model` runtime DB | `main_model.api_key`; caller demande `identity_periodic_agent` mais `llm_client` le normalise en `llm` | `0.0` fixe | `1.0` fixe | `1400` fixe | `config.ARBITER_TIMEOUT_S=10` | aucun | non | JSON `llm/user/meta`; validation stricte dans `memory_identity_periodic_apply.py`; erreur => `None` | indirect via `arbiter_model.model`; pas de headers/titles dedies | provider log sous event periodic mais headers/titles `llm`; events periodic agent |
| Stimmung agent primaire | `stimmung_agent.run_stimmung_agent()` | `prompts/stimmung_agent.txt` | OpenRouter | `openai/gpt-5.4-mini` | `PRIMARY_MODEL=openai/gpt-5.4-mini` | `stimmung_agent_model.primary_model` runtime DB | `main_model.api_key`, caller `stimmung_agent` | `0.1` | `1.0` | `220` | `10` | aucun | non | JSON affectif strict v1 | oui: primary/fallback/temp/top_p/max/timeout | provider log; `stimmung_agent` stage |
| Stimmung agent fallback | meme | meme | OpenRouter | `openai/gpt-5.4-nano` | `FALLBACK_MODEL=openai/gpt-5.4-nano` | `stimmung_agent_model.fallback_model` | meme | `0.1` | `1.0` | `220` | `10` | aucun | non | meme; fail-open si echec | oui | meme |
| Validation agent primaire | `validation_agent.run_validation_agent()` | `prompts/validation_agent.txt` | OpenRouter | `openai/gpt-5.4-mini` | `PRIMARY_MODEL=openai/gpt-5.4-mini` | `validation_agent_model.primary_model` runtime DB | `main_model.api_key`, caller `validation_agent` | `0.0` | `1.0` | `80`, borne | `10` | aucun | non | JSON verdict compact v1 | oui: primary/fallback/temp/top_p/max/timeout | provider log; validation stage; projection compacte dans `[JUGEMENT HERMENEUTIQUE]` |
| Validation agent fallback | meme | meme | OpenRouter | `openai/gpt-5.4-nano` | `FALLBACK_MODEL=openai/gpt-5.4-nano` | `validation_agent_model.fallback_model` | meme | `0.0` | `1.0` | `80`, borne | `10` | aucun | non | meme; fail-open controle si echec | oui | meme |
| Embeddings Memory/RAG | `memory_store_infra.embed()` | pas de prompt; prefixe `query:` ou `passage:` | Service embedding HTTP | `intfloat/multilingual-e5-small`, dim `384` | `EMBED_BASE_URL=https://embed.example.com`, `EMBED_DIM=384` | section runtime `embedding` | `embedding.token` resolu `db_encrypted`, header `X-Embed-Token` | n/a | n/a | n/a | `(5,120)` connect/read | n/a | n/a | `list[float]` depuis `response.json()[0]` | oui: endpoint/model/token/dim/top_k | memory traces, summaries, retrieval diagnostics; pas de provider OpenRouter |
| Transcription vocale | `/api/chat/transcribe` -> `whisper_transcription_service` | pas de prompt | Service Whisper HTTP | payload `model=whisper-1` | constant `whisper-1` | `WHISPER_API_URL`, `WHISPER_API_TIMEOUT_S`, `WHISPER_API_KEY` dans `config.py` | bearer optionnel `WHISPER_API_KEY`; OVH `set=True` | n/a | n/a | n/a | `120` | n/a | n/a | JSON avec `text`; Frida renvoie `{ok,text,input_mode:"voice"}` | non admin runtime | route HTTP; erreurs mappees 400/502/504 |
| OCR documents actifs | `active_document_ocr_client.ocr_pdf_with_stirling()` | pas de prompt | Stirling PDF HTTP | `platform-stirling-pdf` endpoint `/pdf/api/v1/misc/ocr-pdf` | meme defaut | `ACTIVE_DOCUMENT_OCR_*` dans `config.py` | pas d'auth cote FridaDev | n/a | n/a | n/a | `180` | n/a | n/a | PDF OCRise + meta compacte; activation seulement apres extraction finale `complete` | non admin runtime | active document events; metadata content-free |

## Payloads sortants et parametres fixes

Cette section rend explicites les champs envoyes qui ne sont pas tous visibles dans le tableau principal.

| Chemin | Payload ou formulaire sortant | Parametres fixes / additionnels | Notes |
|---|---|---|---|
| Chat principal | JSON OpenRouter construit par `llm_client.build_payload()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stop=["<\|endoftext\|>", "<\|return\|>", "<\|call\|>"]`; si streaming: `stream=true`, `stream_options={"include_usage": true}` | `max_tokens` vient du runtime `response_max_tokens` sauf override de requete; pas de `response_format`, pas de champ `reasoning` |
| Reformulation web | JSON OpenRouter dans `web_search.reformulate()` | `model` depuis `web_reformulation_model.model`, `messages` system/user, `max_tokens` depuis `web_reformulation_model.max_tokens`, `temperature` depuis `web_reformulation_model.temperature` | defauts `openai/gpt-5.4-mini`, `40`, `0.2`, timeout `10`; pas de `top_p`, pas de `stop`, pas de streaming, pas de `response_format` |
| Arbitre memoire | JSON OpenRouter dans `arbiter.filter_traces_with_diagnostics()` | `model`, `messages`, `temperature=0.0`, `top_p=1.0`, `max_tokens=600` | pas de `stop`, pas de streaming, pas de `response_format`; JSON impose par prompt |
| Extracteur identity | JSON OpenRouter dans `arbiter.extract_identities()` | `model`, `messages`, `temperature=0.0`, `top_p=1.0`, `max_tokens=700` | pas de `stop`, pas de streaming, pas de `response_format`; JSON impose par prompt |
| Agent periodic identity | JSON OpenRouter dans `arbiter.run_identity_periodic_agent()` | `model`, `messages`, `temperature=0.0`, `top_p=1.0`, `max_tokens=1400` | pas de `stop`, pas de streaming, pas de `response_format`; JSON impose par prompt |
| Resume conversationnel | JSON OpenRouter dans `summarizer.summarize_conversation()` | `model`, `messages`, `temperature=0.3`, `top_p=1.0`, `max_tokens=SUMMARY_TARGET_TOKENS` | pas de `stop`, pas de streaming, pas de `response_format`; texte libre attendu |
| Stimmung agent | JSON OpenRouter dans `stimmung_agent._call_model()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens` | primary/fallback partagent la meme forme; pas de `stop`, pas de streaming, pas de `response_format` |
| Validation agent | JSON OpenRouter dans `validation_agent._call_model()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens=_bounded_response_max_tokens(max_tokens)` | primary/fallback partagent la meme forme; pas de `stop`, pas de streaming, pas de `response_format` |
| Embeddings | JSON HTTP vers `/embed` | headers `X-Embed-Token`, `Content-Type: application/json`; body `inputs=[prefix + text]`, `model`; prefixe `query: ` ou `passage: ` | timeout `(5,120)`; sortie attendue `response.json()[0]` |
| Whisper | multipart/form-data vers `/v1/audio/transcriptions` | fichier `file`; data `model=whisper-1`, `response_format=json`; header `Authorization: Bearer ...` seulement si `WHISPER_API_KEY` est present | pas de timestamps/langue demandes par FridaDev |
| OCR Stirling | multipart/form-data vers Stirling | fichier `fileInput`; data `languages` repete pour chaque langue de `fra+eng+deu`, `ocrType=force-ocr`, `ocrRenderType=sandwich` | refus local avant appel si bytes/pages depassent les limites; pas d'auth cote FridaDev |
| SearXNG / Crawl4AI support web | hors table inference principale | SearXNG GET: `q`, `format=json`, `language=fr-FR`, `safesearch=0`; Crawl4AI `/md`: `url`, `f`, `c`, optionnel `q` | services support web, non comptes comme modeles d'inference FridaDev |

## Topologie OpenRouter et tokens

### Reponse nette

Oui, **tous les appels OpenRouter du code passent actuellement par le meme secret applicatif**: `main_model.api_key`.

Le secret est lu par `llm_client.or_headers()`, appele par:

- `chat_llm_flow.py`;
- `web_search.py`;
- `arbiter.py` pour `arbiter`, `identity_extractor`, `identity_periodic_agent`;
- `summarizer.py`;
- `stimmung_agent.py`;
- `validation_agent.py`.

Sur OVH, la lecture assainie indique:

- `main_model.api_key`: `is_set=True`, origine affichage `env_backfill`, resolution effective `db_encrypted`;
- `config.OR_KEY`: present en environnement, mais le chemin normal runtime passe par `runtime_settings.get_runtime_secret_value('main_model', 'api_key')`.

Donc la source de verite applicative actuelle est:

1. runtime settings DB chiffre (`db_encrypted`) quand disponible;
2. fallback env seulement si le champ runtime est d'origine `env_seed` et que la valeur env existe;
3. erreur si aucune source n'est resoluble.

### Tableau auth / transport

| Caller OpenRouter demande | Caller normalise par `llm_client` | Token | Base URL effective | Referer/title effectifs | `X-Frida-Caller` vers provider | Particularite |
|---|---|---|---|---|---|---|
| `llm` | `llm` | `main_model.api_key` | chat: `config.OR_BASE`; helper: runtime `main_model.base_url` | `main_model.referer_llm`, `main_model.title_llm` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy` avant l'appel externe | chat principal n'utilise pas encore le helper URL |
| `web_reformulation` | `web_reformulation` | meme | runtime `main_model.base_url` via helper | fallback config `OPENROUTER_REFERER_WEB_REFORMULATION` / `OPENROUTER_TITLE_WEB_REFORMULATION` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | modele et petits parametres dedies via `web_reformulation_model`; referer/title restent config-only |
| `arbiter` | `arbiter` | meme | `config.OR_BASE` | `main_model.referer_arbiter`, `main_model.title_arbiter` | transmis: appel direct `requests.post()` sans proxy | timeout runtime admin non utilise |
| `identity_extractor` | `identity_extractor` | meme | `config.OR_BASE` | `main_model.referer_identity_extractor`, `main_model.title_identity_extractor` | transmis: appel direct `requests.post()` sans proxy | modele partage `arbiter_model` |
| `identity_periodic_agent` | `llm` | meme | `config.OR_BASE` | `main_model.referer_llm`, `main_model.title_llm` | transmis comme `X-Frida-Caller: llm`, car caller inconnu normalise en `llm` | caller non connu par `llm_client`, donc pas distingue dans headers |
| `resumer` | `resumer` | meme | `config.OR_BASE` | `main_model.referer_resumer`, `main_model.title_resumer` | transmis: appel direct `requests.post()` sans proxy | temp/top_p runtime non utilises |
| `stimmung_agent` | `stimmung_agent` | meme | runtime `main_model.base_url` via helper | `main_model.referer_stimmung_agent`, `main_model.title_stimmung_agent` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | primary/fallback propres |
| `validation_agent` | `validation_agent` | meme | runtime `main_model.base_url` via helper | `main_model.referer_validation_agent`, `main_model.title_validation_agent` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | primary/fallback propres |

### Ce que le repo permet deja

- Un seul secret OpenRouter peut etre rote dans `main_model.api_key`.
- Les headers `HTTP-Referer`, `X-OpenRouter-Title`, `X-Title` distinguent deja la plupart des composants.
- Le header interne `X-Frida-Caller` est toujours construit par `llm_client.or_headers()` apres normalisation du caller. Sur les appels passes par `_RequestsChatLogProxy`, il sert localement a l'observabilite puis il est retire avant l'appel externe; sur les appels directs `requests.post()` de certains modules, il est transmis au provider.

### Ce qu'il faudra verifier cote console OpenRouter

Le repo ne peut pas prouver:

- si le token courant appartient a un projet unique ou a plusieurs projets cote OpenRouter;
- si les budgets, limites, analytics ou restrictions par domaine sont configures cote console;
- si OpenRouter utilise vraiment les referer/title comme separation exploitable pour l'operateur.

Pour une separation par projets OpenRouter, il faudra verifier dans l'interface externe:

- projet rattache au token actuel;
- possibilite de creer un token par projet/caller;
- politiques de budget et model allowlist par projet;
- consequences de la rotation sur les secrets runtime chiffrés et les fallbacks env.

## Contrats de sortie

| Chemin | Type sortie provider/service | Parseur / validation | Fail-open / fail-closed | Persistance / propagation |
|---|---|---|---|---|
| Chat principal | texte libre assistant | `extract_openrouter_text()`, puis `assistant_output_contract.normalize_assistant_output()` | erreur provider => erreur HTTP/stream terminal error; pas de faux texte | message assistant persiste; traces memoire et identity post-turn ensuite |
| Web reformulation | texte libre court | strip guillemets; aucun JSON | fail-open vers message utilisateur original | query utilisee pour SearXNG/Crawl4AI; observabilite hashes/chars |
| Arbitre memoire | JSON `{"decisions":[...]}` | `_safe_json_loads()`, `_validate_arbiter_output()`, completion deterministe des candidats manquants | fallback deterministe sur timeout/parse/runtime | decisions persistees dans audit arbitre; traces gardees injectees |
| Summary | texte libre resume | extraction texte provider seulement | exception remontee dans `maybe_summarize()` et log; pas de summary si echec | resume persiste, messages couverts marques `summarized_by`, embedding du summary |
| Identity extractor | JSON `{"entries":[...]}` | `_validate_identity_output()` filtre enums/champs invalides | erreur => `[]`, donc pas de staging | entrees valides stagees/appliquees dans identity pipeline |
| Identity periodic agent | JSON `{llm:{operations}, user:{operations}, meta}` | `validate_periodic_agent_contract()` exige top-level exact, operations exactes, meta complete | erreur provider => `None`; contrat invalide => skipped/error dans agent periodique | operations appliquees par `memory_identity_periodic_apply`; events periodiques |
| Stimmung agent | JSON strict v1 | validation enums, strengths, confidence, dominant tone | fail-open signal avec raison, pas de blocage | signal dans meta du tour et stage observabilite |
| Validation agent | JSON strict v1 | `_validated_model_verdict()` + hard guards | fail-open controle vers posture/regime sur echec | `validated_output`, projection compacte dans `[JUGEMENT HERMENEUTIQUE]` |
| Embeddings | `list[float]` | `response.json()[0]`; dimension attendue `384` par schema DB/settings | exceptions gerees au niveau appelant selon retrieval/save | vectors traces, summaries, identity conflicts |
| Whisper | JSON service contenant `text` | `_response_json()` exige mapping avec `text` | erreurs mappees en 400/502/504 | texte renvoye au frontend comme draft vocal, non memoire directe |
| OCR Stirling | reponse PDF + headers content-type | content-type `application/pdf`, bytes non vides; puis extracteur FridaDev doit rendre `complete` | refus content-free reason code; jamais activation partielle | document actif OCRise avec metadata compactes, sans texte brut dans UI/log ordinaire |

### Schemas JSON principaux

#### Arbitre memoire

```json
{
  "decisions": [
    {
      "candidate_id": "cand-...",
      "keep": true,
      "semantic_relevance": 0.91,
      "contextual_gain": 0.72,
      "redundant_with_recent": false,
      "reason": "short reason"
    }
  ]
}
```

Validation:

- `candidate_id` doit referencer un candidat fourni;
- `keep` et `redundant_with_recent` booleens;
- scores dans `[0,1]`;
- candidats absents de la reponse LLM sont completes en rejet avec `missing_from_llm_output`;
- post-filtrage Python applique seuils, redondance et plafond.

#### Identity extractor

```json
{
  "entries": [
    {
      "subject": "user",
      "content": "One compact identity candidate",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "repeated",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.88,
      "reason": "short reason"
    }
  ]
}
```

Enums autorises:

- `subject`: `user`, `llm`;
- `stability`: `durable`, `episodic`, `unknown`;
- `utterance_mode`: `self_description`, `projection`, `role_play`, `irony`, `speculation`, `unknown`;
- `recurrence`: `first_seen`, `repeated`, `habitual`, `unknown`;
- `scope`: `user`, `llm`, `situation`, `mixed`, `unknown`;
- `evidence_kind`: `explicit`, `inferred`, `weak`.

#### Identity periodic agent

```json
{
  "llm": {
    "operations": [
      {
        "kind": "no_change",
        "proposition": "",
        "reason": "no durable identity change"
      }
    ]
  },
  "user": {
    "operations": [
      {
        "kind": "add",
        "proposition": "One compact identity proposition.",
        "reason": "durable identity signal"
      }
    ]
  },
  "meta": {
    "execution_status": "complete",
    "buffer_pairs_count": 15,
    "window_complete": true
  }
}
```

Operations autorisees: `no_change`, `add`, `tighten`, `merge`, `raise_conflict`. Le validateur refuse les top-level keys inattendues, les shapes incorrectes, le melange `no_change` + operation et les metadonnees incoherentes.

#### Stimmung agent

```json
{
  "schema_version": "v1",
  "present": true,
  "tones": [
    {"tone": "neutralite", "strength": 3}
  ],
  "dominant_tone": "neutralite",
  "confidence": 0.72
}
```

Tones autorises: `apaisement`, `enthousiasme`, `curiosite`, `confusion`, `frustration`, `colere`, `anxiete`, `decouragement`, `neutralite`.

#### Validation agent

```json
{
  "schema_version": "v1",
  "final_judgment_posture": "answer",
  "final_output_regime": "simple",
  "arbiter_reason": "raison_courte_lisible"
}
```

Enums:

- `final_judgment_posture`: `answer`, `clarify`, `suspend`;
- `final_output_regime`: `simple`, `meta`.

La sortie brute ne doit pas contenir `validation_decision` ni `pipeline_directives_final`; ces formes sont construites/normalisees en aval par Python.

## Schema des chemins d'appel

```text
Chat user turn
  -> stimmung_agent (OpenRouter primary/fallback JSON)
  -> hermeneutic validation_agent (OpenRouter primary/fallback JSON)
  -> maybe_summarize (OpenRouter summary when dialogue-only threshold reached)
  -> Memory retrieval
       -> embedding query service
       -> arbiter OpenRouter JSON
  -> web, if enabled
       -> web reformulation OpenRouter text
       -> SearXNG / Crawl4AI support services
  -> active_document prompt lane
       -> no model call at prompt build time
       -> upload path may previously have called Stirling OCR
  -> main chat LLM OpenRouter text/stream
  -> post-turn memory
       -> embedding passage service for traces/summaries
       -> identity_extractor OpenRouter JSON
       -> identity_periodic_agent OpenRouter JSON when staged window completes

Voice dictation path
  -> /api/chat/transcribe
  -> platform-whisper-api /v1/audio/transcriptions

Active document upload path
  -> local extractor
  -> if document_ocr_required: platform-stirling-pdf OCR
  -> local extractor again
  -> active_document state only if final extraction complete
```

## Ecarts et asymetries

### Patrons propres

- `stimmung_agent` et `validation_agent` ont chacun une section runtime dediee complete: primary model, fallback model, temperature, top_p, max_tokens, timeout.
- Le contrat de sortie JSON de `validation_agent` est court et strict.
- Le contrat de sortie JSON de `stimmung_agent` est borne, fail-open et observe.
- Les embeddings ont une section runtime dediee avec endpoint/model/token/dimensions/top_k.
- Les services Whisper et OCR sont separes par responsabilite et n'exposent pas de contenu brut dans les surfaces ordinaires.

### Divergences sans raison claire documentee dans le code

- `chat_llm_flow.py`, `summarizer.py` et `arbiter.py` appellent `config.OR_BASE` au lieu de `llm_client.or_chat_completions_url()`. Les valeurs runtime OVH sont aujourd'hui coherentes (`https://openrouter.ai/api/v1`), mais une modification admin de `main_model.base_url` ne toucherait pas tous les callers.
- `web_reformulation` a maintenant une section runtime dediee pour `model`, `temperature`, `max_tokens`, `timeout_s`; ses referer/title restent encore config-only, contrairement aux autres composants OpenRouter exposes dans `main_model`.
- `identity_periodic_agent` appelle `llm_client.or_headers(caller='identity_periodic_agent')`, mais ce caller n'est pas dans `_KNOWN_PROVIDER_CALLERS`; il est donc normalise en `llm` pour headers/referer/title.
- `arbiter_model.timeout_s` est administrable et vaut `60` dans le runtime OVH, mais les trois chemins de `arbiter.py` utilisent `config.ARBITER_TIMEOUT_S=10`.
- `arbiter_model.temperature` et `top_p` existent dans les settings runtime, mais les payloads `arbiter`, `identity_extractor` et `identity_periodic_agent` sont hardcodes a `0.0/1.0`.
- `summary_model.temperature` et `top_p` existent, mais le summarizer hardcode `0.3/1.0`.
- `identity_extractor` et `identity_periodic_agent` reutilisent le modele de l'arbitre; il n'existe pas de section modele dediee pour les distinguer.

### Endroits fragiles ou implicites

- Les sorties `identity_extractor` fail-open vers `[]`, ce qui est volontaire pour ne pas casser le tour, mais rend les erreurs invisibles dans le comportement utilisateur direct.
- Le summary ne possede pas de schema JSON; c'est un texte libre. C'est normal pour une synthese, mais plus fragile a verifier automatiquement.
- `extract_openrouter_text()` suppose `choices[0].message.content`; il n'y a pas de contrat alternatif si un provider renvoie une autre forme.
- Les parametres `reasoning` / `effort` / equivalents ne sont envoyes par aucun caller. Si l'on veut les utiliser plus tard, il faudra un contrat explicite par role.
- L'admin runtime expose un statut "shared transport" pour certains composants, mais cette verite est incomplete pour les callers encore branches sur `config.OR_BASE`.

## Ce que nous pourrons raffiner ensuite

Pistes candidates, hors scope de ce lot:

1. Normaliser tous les appels OpenRouter sur `llm_client.or_chat_completions_url()` pour que `main_model.base_url` soit vraiment source de verite globale.
2. Decider si `identity_periodic_agent` doit devenir un caller OpenRouter distinct, avec referer/title dedies.
3. Decider si `identity_extractor` et `identity_periodic_agent` doivent rester sur `arbiter_model` ou recevoir leur propre section modele.
4. Aligner les champs runtime administrables sur les parametres reellement utilises: `timeout_s`, `temperature`, `top_p`, `max_tokens`.
5. Decider si les referer/title `web_reformulation` doivent rester config-only ou rejoindre une surface runtime future.
6. Preparer une rotation OpenRouter sans fuite: un plan de migration `main_model.api_key`, validation runtime, smoke calls, puis eventuelle separation par projets.
7. Ajouter un tableau operateur "model topology" dans l'admin si la rotation multi-projets devient un chantier.

## Questions restant hors preuve repo

- Le token OpenRouter actuel correspond-il a un seul projet externe ou a une cle globale?
- Les referer/title envoyes par FridaDev sont-ils exploites dans l'analytics OpenRouter actuel?
- Faut-il separer les budgets par role fonctionnel ou seulement par grandes familles (`main`, `memory`, `hermeneutic`)?
- Quels modeles sont allowlistes ou bloques cote OpenRouter externe?
- Quelle est la politique de rotation souhaitee: un secret unique remplace, ou migration progressive vers plusieurs secrets?

## Annexes - valeurs runtime OVH relevees

Lecture assainie le 2026-05-17:

| Section runtime | Champ | Valeur non secrete observee | Origine |
|---|---|---|---|
| `main_model` | `base_url` | `https://openrouter.ai/api/v1` | `admin_ui` |
| `main_model` | `model` | `anthropic/claude-sonnet-4.6` | `admin_ui` |
| `main_model` | `temperature` | `0.4` | `db_seed` |
| `main_model` | `top_p` | `1.0` | `db_seed` |
| `main_model` | `response_max_tokens` | `8192` | `admin_ui` |
| `main_model` | `api_key` | secret present, resolu `db_encrypted` | `env_backfill` / DB chiffree |
| `arbiter_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` |
| `arbiter_model` | `timeout_s` | `60` | `admin_ui` |
| `summary_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` |
| `web_reformulation_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `temperature` | `0.2` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `max_tokens` | `40` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `timeout_s` | `10` | `db_seed` apres bootstrap / env fallback |
| `stimmung_agent_model` | `primary_model` | `openai/gpt-5.4-mini` | `db_seed` |
| `stimmung_agent_model` | `fallback_model` | `openai/gpt-5.4-nano` | `db_seed` |
| `validation_agent_model` | `primary_model` | `openai/gpt-5.4-mini` | `db_seed` |
| `validation_agent_model` | `fallback_model` | `openai/gpt-5.4-nano` | `db_seed` |
| `embedding` | `endpoint` | `https://embed.frida-system.fr` | `db_seed` |
| `embedding` | `model` | `intfloat/multilingual-e5-small` | `db_seed` |
| `embedding` | `dimensions` | `384` | `db_seed` |
| `embedding` | `token` | secret present, resolu `db_encrypted` | `env_backfill` / DB chiffree |
| `services` | `searxng_url` | `http://searxng:8080` | `admin_ui` |
| `services` | `crawl4ai_url` | `http://crawl4ai:11235` | `admin_ui` |
| `services` | `crawl4ai_token` | secret present, resolu `db_encrypted` | `env_backfill` / DB chiffree |

Constantes runtime `config.py` relevees dans le conteneur:

- `OR_BASE='https://openrouter.ai/api/v1'`;
- `OR_MODEL='openai/gpt-5.1'` comme seed/env, non modele principal effectif car runtime DB le remplace;
- `WEB_REFORMULATION_MODEL='openai/gpt-5.4-mini'`;
- `WEB_REFORMULATION_TEMPERATURE=0.2`;
- `WEB_REFORMULATION_MAX_TOKENS=40`;
- `WEB_REFORMULATION_TIMEOUT_S=10`;
- `TIMEOUT_S=900`;
- `ARBITER_TIMEOUT_S=10`;
- `SUMMARY_TARGET_TOKENS=2000`;
- `WHISPER_API_URL='http://platform-whisper-api:9001'`;
- `WHISPER_API_TIMEOUT_S=120`;
- `WHISPER_API_KEY` present;
- `ACTIVE_DOCUMENT_OCR_URL='http://platform-stirling-pdf:8080/pdf/api/v1/misc/ocr-pdf'`;
- `ACTIVE_DOCUMENT_OCR_TIMEOUT_S=180`;
- `ACTIVE_DOCUMENT_OCR_LANGUAGES='fra+eng+deu'`;
- `ACTIVE_DOCUMENT_OCR_MAX_PAGES=25`;
- `ACTIVE_DOCUMENT_OCR_MAX_BYTES=26214400`;
- `EMBED_BASE_URL='https://embed.frida-system.fr'`;
- `EMBED_DIM=384`;
- `MEMORY_TOP_K=5`.
