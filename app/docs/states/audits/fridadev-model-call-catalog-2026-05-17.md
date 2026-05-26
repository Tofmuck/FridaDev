# FridaDev - model call catalog - 2026-05-17

## Resume executif

Cet audit cartographie les appels modele et services d'inference reellement presents dans FridaDev au 2026-05-17, sur la working copy OVH `/opt/platform/fridadev` et le runtime vivant `platform-fridadev`.

Mise a jour du 2026-05-20: le chantier `feature/main-model-gpt51` bascule le modele principal quotidien vers `openai/gpt-5.1`, en conservant les autres slots modeles et le transport OpenRouter. Les valeurs historiques Claude Sonnet 4.6 ci-dessous sont a lire comme etat pre-bascule quand elles sont explicitement marquees precedentes.

Mise a jour du 2026-05-26: le Lot B add-only ontologique bascule le chemin modele actif vers `mutable_identity_judge_v2`, avec prompt `prompts/identity_mutable_judge_v2.txt`, contrat `mutable_judge_v2`, verdicts `add` / `no_change` uniquement et slot runtime provisoire `identity_periodic_model`. L'ancien chemin **Agent periodic identity** reste legacy disabled: `arbiter.run_identity_periodic_agent()` ne fait plus d'appel provider, `prompts/identity_periodic_agent.txt` est un artefact legacy, et `memory_identity_periodic_apply.py` / `memory_identity_periodic_scoring.py` ont ete supprimes.

Mise a jour du 2026-05-26: `mutable_identity_judge` envoie maintenant `response_format={"type":"json_schema", ... strict=true}`, `provider.require_parameters=true` et `provider.order=["anthropic"]` dans son payload OpenRouter. Le routage privilegie Anthropic direct pour eviter la latence observee via Amazon Bedrock, sans desactiver les fallbacks OpenRouter. Le validateur metier FridaDev reste souverain apres structured output; les invalidations exposent uniquement un diagnostic compact content-free.

Mise a jour du 2026-05-26 Lot D: le smoke reel `mutable_judge_v2` sans applicateur ni DB live appelle bien OpenRouter via le slot `identity_periodic_model`; le provider repond avec `anthropic/claude-4.5-haiku-20251001`, mais la sortie est rejetee par le validateur FridaDev (`invalid_verdict`). Le modele n'est pas change dans ce lot; decision operatoire: Haiku est fragile pour ce role tant qu'un micro-lot modele/timeout n'a pas tranche.

Mise a jour du 2026-05-26 Lot D bis: le smoke candidat `openai/gpt-5.4-mini` est execute uniquement via override local du script, sans changer le slot runtime persistant. Le 404 initial venait du couple `provider.require_parameters=true` + parametres non supportes (`temperature` / `top_p`), pas d'un modele absent. Avec un payload compatible conservant le schema strict, OpenRouter route vers `openai/gpt-5.4-mini-20260317`. Apres durcissement du schema discriminant `add` / `no_change`, le smoke 3 runs garde les `no_change` propres mais echoue au critere modele (`runs_ok=0/3`, `exit_code=5`) parce que le modele rate des adds attendus; le modele actif reste inchange.

Mise a jour du 2026-05-26 modele frontiere: l'API OpenRouter confirme `openai/gpt-5.2`, `openai/gpt-5.1` et `openai/gpt-5.5` comme disponibles avec `response_format` / `structured_outputs`. Le smoke reel candidat `openai/gpt-5.5`, execute uniquement via override local, passe 3/3 runs (`provider=openai/gpt-5.5-20260423`, `verdict_counts={"add": 2}` a chaque run, bruit ajoute `0`, `live_db_write=false`, `applicator_called=false`). Recommandation: `openai/gpt-5.5` est le premier candidat valide pour une bascule separee du slot `identity_periodic_model`; le runtime persistant n'est pas modifie par ce smoke.

Mise a jour du 2026-05-26 bascule modele juge mutable: decision operateur de basculer le slot runtime de compatibilite `identity_periodic_model` vers `openai/gpt-5.2`, candidat valide observe en smoke 3/3 (`provider=openai/gpt-5.2-20251211`, `verdict_counts={"add": 2}` a chaque run, bruit ajoute `0`, `live_db_write=false`, `applicator_called=false`). Le nom du slot reste conserve par compatibilite, mais il pilote le caller actif `mutable_identity_judge_v2` add-only.

Verdict court:

- FridaDev expose **11 chemins fonctionnels d'inference**, correspondant a **13 slots modele/service** si l'on compte separement les modeles primaire/fallback du `stimmung_agent` et du `validation_agent`.
- Les chemins OpenRouter partagent aujourd'hui **un seul secret applicatif**: `main_model.api_key`.
- Sur OVH, ce secret est configure et resolu via les runtime settings chiffrés (`db_encrypted`), avec origine historique `env_backfill`. Le repo ne prouve pas a lui seul la separation ou non des projets cote console OpenRouter.
- Le systeme est fonctionnel mais heterogene: certains callers utilisent `llm_client.or_chat_completions_url()` et donc `main_model.base_url` runtime; d'autres utilisent encore `config.OR_BASE`.
- L'arbitre memoire, l'extracteur identity au tour et le juge mutable sont maintenant individualises: `memory_arbiter_model`, `identity_extractor_model` et `identity_periodic_model` portent leurs modeles, parametres et timeouts propres. Le slot `identity_periodic_model` garde un nom de compatibilite mais pilote le caller actif `mutable_identity_judge`. Le slot legacy `arbiter_model` ne pilote plus aucun caller actif.

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

La table ci-dessous liste les **slots modele/service** observables. Les **11 chemins fonctionnels** regroupent `stimmung_agent` primary/fallback en un seul chemin et `validation_agent` primary/fallback en un seul chemin: chat principal, reformulation web, arbitre memoire, resume, extracteur identity, juge mutable, stimmung, validation, embeddings, Whisper, OCR.

| # | Slot modele/service | Type | Caller / fichier principal | Modele ou service runtime OVH | Statut |
|---|---|---|---|---|---|
| 1 | Chat principal | OpenRouter chat completion | `app/core/chat_llm_flow.py` | `openai/gpt-5.1` depuis la bascule 2026-05-20; precedent `anthropic/claude-sonnet-4.6` | actif |
| 2 | Reformulation web | OpenRouter chat completion | `app/tools/web_search.py` | `openai/gpt-5.4-mini` | actif quand web active |
| 3 | Arbitre memoire | OpenRouter chat completion | `app/memory/arbiter.py` | `mistralai/mistral-small-2603` | actif, individualise |
| 4 | Resume conversationnel | OpenRouter chat completion | `app/memory/summarizer.py` | `openai/gpt-5.4-mini` | actif au seuil de summary |
| 5 | Extracteur identity | OpenRouter chat completion | `app/memory/arbiter.py` | `openai/gpt-5.4-mini` | actif apres tour assistant |
| 6 | Mutable identity judge | OpenRouter chat completion | `app/memory/mutable_identity_judge_v2.py` via `memory_identity_periodic_agent.py` / `mutable_identity_runtime.py` | `openai/gpt-5.2` via le slot de compatibilite `identity_periodic_model` | actif quand la fenetre mutable atteint 5 paires completes |
| 7 | Stimmung agent primaire | OpenRouter chat completion | `app/core/stimmung_agent.py` | `google/gemini-3.1-flash-lite` | actif avant noeud hermeneutique |
| 8 | Stimmung agent fallback | OpenRouter chat completion | `app/core/stimmung_agent.py` | `openai/gpt-5.4-nano` | fallback |
| 9 | Validation agent primaire | OpenRouter chat completion | `app/core/hermeneutic_node/validation/validation_agent.py` | `google/gemini-3.1-flash-lite` | actif dans noeud hermeneutique, decision 2026-05-19 |
| 10 | Validation agent fallback | OpenRouter chat completion | meme fichier | `openai/gpt-5.4-nano` | fallback |
| 11 | Embeddings Memory/RAG | service embedding HTTP | `app/memory/memory_store_infra.py` | `intfloat/multilingual-e5-small`, dim `384` | actif |
| 12 | Transcription vocale | service Whisper HTTP | `app/core/whisper_transcription_service.py` | payload `model=whisper-1` | actif si dictation |
| 13 | OCR PDF active documents | service Stirling PDF HTTP | `app/core/active_document_ocr_client.py` | `platform-stirling-pdf` OCR, modele interne non expose | actif sur `document_ocr_required` |

Chemins explicitement absents ou retires:

- **Reranker Memory/RAG**: absent; decision documentaire `no-go for now` dans `app/docs/states/project/memory-rag-reranker-decision-2026-04-11.md`.
- **Identity mutable rewriter LLM**: retire; `app/memory/memory_identity_mutable_rewriter.py` et `rewrite_identity_mutables()` ne declenchent plus d'appel modele.
- **Agent periodic identity score-first**: legacy disabled depuis le 2026-05-25; `arbiter.run_identity_periodic_agent()` retourne un resume compact sans appel provider, et le prompt `identity_periodic_agent.txt` n'est plus actif.
- **Biblio native / Catalogue**: chantier actif documentaire, aucun call modele Biblio nominal dans FridaDev.

## Tableau exhaustif principal

> `Runtime OVH` vient d'une lecture assainie des settings et constantes dans le conteneur. Les secrets sont notes `set/unset`, jamais affiches.

| Role | Caller / fichier | Prompt | Provider | Modele effectif runtime OVH | Defaut code / seed | Source config runtime | Token / auth source | Temperature | top_p | Max tokens | Timeout | Raisonnement | Stream | Output contract | Admin configurable | Observabilite |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|---|---|---|
| Chat principal | `chat_llm_flow.run_llm_exchange()` | `MAIN_SYSTEM_PROMPT_PATH`, `main_hermeneutical.txt`, prompt window runtime | OpenRouter | `openai/gpt-5.1`; precedent `anthropic/claude-sonnet-4.6` | `OPENROUTER_MODEL=openai/gpt-5.1` | `main_model.model` runtime DB | `main_model.api_key`, present origine `admin_ui`, resolu `db_encrypted`; header caller `llm` | `0.7` | `1.0` | `8192` par defaut, override request possible | `FRIDA_TIMEOUT=900` | `main_model.reasoning_effort`, defaut `high`; envoye comme `reasoning.effort` avec `exclude=true` si modele GPT-5.1 compatible | oui, si `stream=true` | texte libre assistant, normalise puis persiste; reasoning interne ignore | oui: `main_model.model`, sampling, response max, reasoning effort, headers; base_url runtime existe mais ce call utilise encore `config.OR_BASE` | `llm_payload`, `llm_call`, `llm_provider_response`, `AssistantText`, stream events, champs `main_llm_reasoning_*` content-free |
| Reformulation web | `web_search.reformulate()` | `prompts/web_reformulation.txt` | OpenRouter | `openai/gpt-5.4-mini` | `WEB_REFORMULATION_MODEL=openai/gpt-5.4-mini` | `web_reformulation_model.model`; base via `llm_client.or_chat_completions_url()` | `main_model.api_key`, caller `web_reformulation` | `0.2` | non envoye | `40` | `10` | aucun | non | texte court, fallback vers message utilisateur si erreur | oui: `web_reformulation_model` pour model/temp/max/timeout; transport/token et referer/title partages via `main_model` | `web_reformulation_prompt_prepared`, `web_search` |
| Arbitre memoire | `arbiter.filter_traces_with_diagnostics()` | `prompts/arbiter.txt` | OpenRouter | `mistralai/mistral-small-2603` | `MEMORY_ARBITER_MODEL=mistralai/mistral-small-2603` | `memory_arbiter_model` runtime DB: model/temp/top_p/max_tokens/timeout | `main_model.api_key`, caller `arbiter`, transport `llm_client.or_chat_completions_url()` | `0.0` | `1.0` | `600` | `10` | aucun | non | JSON `decisions[]`, puis post-filtrage deterministe | oui: section dediee `memory_arbiter_model`; benchmark final conserve sous `benchmark/results/arbiter/` | provider logs, metrics, `record_arbiter_decisions()` avec modele effectif |
| Resume conversationnel | `summarizer.summarize_conversation()` | `prompts/summary_system.txt` | OpenRouter | `openai/gpt-5.4-mini` | `SUMMARY_MODEL=openai/gpt-5.4-mini` | `summary_model` runtime DB: model/temp/top_p/max_tokens/timeout | `main_model.api_key`, caller `resumer`, transport `llm_client.or_chat_completions_url()` | `0.3` | `1.0` | `2000` | `90` | aucun | non | texte libre de resume; persiste en summary actif | oui: section dediee `summary_model`; decision humaine conservee sous `benchmark/results/summary/` | provider metadata log; summary persistence |
| Extracteur identity | `arbiter.extract_identities()` | `prompts/identity_extractor.txt` | OpenRouter | `openai/gpt-5.4-mini` | `IDENTITY_EXTRACTOR_MODEL=openai/gpt-5.4-mini` | `identity_extractor_model` runtime DB: model/temp/top_p/max_tokens/timeout | `main_model.api_key`, caller `identity_extractor`, transport `llm_client.or_chat_completions_url()` | `0.0` | `1.0` | `700` | `10` | aucun | non | JSON `entries[]`; invalides skips; erreur => `[]` | oui: section dediee `identity_extractor_model`; benchmark humain conserve sous `benchmark/results/identity_extractor/` | provider log, metrics parse/call; staging identity |
| Mutable identity judge | `mutable_identity_judge_v2.run_mutable_identity_judge_v2()` via `mutable_identity_runtime.run_mutable_identity_window()` | `prompts/identity_mutable_judge_v2.txt` | OpenRouter | `openai/gpt-5.2` | `IDENTITY_PERIODIC_MODEL` env reste fallback; runtime actif via DB | `identity_periodic_model` runtime DB: model/temp/top_p/max_tokens/timeout, nom conserve par compatibilite | `main_model.api_key`, caller `mutable_identity_judge`, transport `llm_client.or_chat_completions_url()` | omis pour `openai/gpt-5*` | omis pour `openai/gpt-5*` | `1400` | `10` | aucun | non | JSON `mutable_judge_v2`; `response_format` JSON Schema strict + `provider.require_parameters=true`; validation stricte dans `mutable_identity_judge_v2.py`; erreur => `skipped` content-free et fenetre preservee | oui: section dediee `identity_periodic_model`; nom conserve par compatibilite | provider log `mutable_identity_judge_provider_response`; events `mutable_identity_judge` / `mutable_identity_judge_apply` content-free |
| Stimmung agent primaire | `chat_turn_runtime_inputs.run_stimmung_agent_stage()` -> `stimmung_agent.build_affective_turn_signal()` | `prompts/stimmung_agent.txt` | OpenRouter | `google/gemini-3.1-flash-lite` | `PRIMARY_MODEL=google/gemini-3.1-flash-lite` | `stimmung_agent_model.primary_model` runtime DB | `main_model.api_key`, caller `stimmung_agent` | `0.1` | `1.0` | `220` | `10` | aucun | non | JSON affectif strict v1 | oui: primary/fallback/temp/top_p/max/timeout | provider log; `stimmung_agent` stage |
| Stimmung agent fallback | meme | meme | OpenRouter | `openai/gpt-5.4-nano` | `FALLBACK_MODEL=openai/gpt-5.4-nano` | `stimmung_agent_model.fallback_model` | meme | `0.1` | `1.0` | `220` | `10` | aucun | non | meme; fail-open si echec | oui | meme |
| Validation agent primaire | `validation_agent.run_validation_agent()` | `prompts/validation_agent.txt` | OpenRouter | `google/gemini-3.1-flash-lite` | `PRIMARY_MODEL=google/gemini-3.1-flash-lite` | `validation_agent_model.primary_model` runtime DB | `main_model.api_key`, caller `validation_agent` | `0.0` | `1.0` | `140`, borne | `10` | aucun | non | JSON verdict compact v1 | oui: primary/fallback/temp/top_p/max/timeout; decision conservee sous `benchmark/results/validation_agent/2026-05-19-validation-agent-decision.md` | provider log; validation stage; projection compacte dans `[JUGEMENT HERMENEUTIQUE]` |
| Validation agent fallback | meme | meme | OpenRouter | `openai/gpt-5.4-nano` | `FALLBACK_MODEL=openai/gpt-5.4-nano` | `validation_agent_model.fallback_model` | meme | `0.0` | `1.0` | `140`, borne | `10` | aucun | non | meme; fail-open controle si echec | oui | meme |
| Embeddings Memory/RAG | `memory_store_infra.embed()` | pas de prompt; prefixe `query:` ou `passage:` | Service embedding HTTP | `intfloat/multilingual-e5-small`, dim `384` | `EMBED_BASE_URL=https://embed.example.com`, `EMBED_DIM=384` | section runtime `embedding` | `embedding.token` resolu `db_encrypted`, header `X-Embed-Token` | n/a | n/a | n/a | `(5,120)` connect/read | n/a | n/a | `list[float]` depuis `response.json()[0]` | oui: endpoint/model/token/dim/top_k | memory traces, summaries, retrieval diagnostics; pas de provider OpenRouter |
| Transcription vocale | `/api/chat/transcribe` -> `whisper_transcription_service` | pas de prompt | Service Whisper HTTP | payload `model=whisper-1` | constant `whisper-1` | `WHISPER_API_URL`, `WHISPER_API_TIMEOUT_S`, `WHISPER_API_KEY` dans `config.py` | bearer optionnel `WHISPER_API_KEY`; header content-free `X-Frida-Request-Id`; OVH `set=True` | n/a | n/a | n/a | `180` | n/a | n/a | JSON avec `text`; Frida renvoie `{ok,text,input_mode:"voice"}` | non admin runtime | route HTTP; erreurs mappees 400/502/504; observabilite content-free request_id, taille/duree/raison/latence/transcript_chars |
| OCR documents actifs | `active_document_ocr_client.ocr_pdf_with_stirling()` | pas de prompt | Stirling PDF HTTP | `platform-stirling-pdf` endpoint `/pdf/api/v1/misc/ocr-pdf` | meme defaut | `ACTIVE_DOCUMENT_OCR_*` dans `config.py` | pas d'auth cote FridaDev | n/a | n/a | n/a | `180` | n/a | n/a | PDF OCRise + meta compacte; activation seulement apres extraction finale `complete` | non admin runtime | active document events; metadata content-free |

## Payloads sortants et parametres fixes

Cette section rend explicites les champs envoyes qui ne sont pas tous visibles dans le tableau principal.

| Chemin | Payload ou formulaire sortant | Parametres fixes / additionnels | Notes |
|---|---|---|---|
| Chat principal | JSON OpenRouter construit par `llm_client.build_payload()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stop=["<\|endoftext\|>", "<\|return\|>", "<\|call\|>"]`; si modele GPT-5.1 compatible: `reasoning={"effort": main_model.reasoning_effort, "exclude": true}`; si streaming: `stream=true`, `stream_options={"include_usage": true}` | `max_tokens` vient du runtime `response_max_tokens` sauf override de requete; pas de `response_format`, pas de `include_reasoning`; les champs `reasoning` / `reasoning_details` provider sont filtres au read path et ne sont pas rendus ni persistés |
| Reformulation web | JSON OpenRouter dans `web_search.reformulate()` | `model` depuis `web_reformulation_model.model`, `messages` system/user, `max_tokens` depuis `web_reformulation_model.max_tokens`, `temperature` depuis `web_reformulation_model.temperature` | defauts `openai/gpt-5.4-mini`, `40`, `0.2`, timeout `10`; pas de `top_p`, pas de `stop`, pas de streaming, pas de `response_format` |
| Arbitre memoire | JSON OpenRouter dans `arbiter.filter_traces_with_diagnostics()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens` depuis `memory_arbiter_model` | defaut benchmarke `mistralai/mistral-small-2603`, `0.0`, `1.0`, `600`, timeout `10`; pas de `stop`, pas de streaming, pas de `response_format`; JSON impose par prompt |
| Extracteur identity | JSON OpenRouter dans `arbiter.extract_identities()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens` depuis `identity_extractor_model` | defaut benchmarke/conserve `openai/gpt-5.4-mini`, `0.0`, `1.0`, `700`, timeout `10`; pas de `stop`, pas de streaming, pas de `response_format`; JSON impose par prompt |
| Mutable identity judge | JSON OpenRouter dans `mutable_identity_judge_v2.run_mutable_identity_judge_v2()` | `model`, `messages`, `max_tokens` depuis `identity_periodic_model`; `temperature` / `top_p` seulement si le modele les supporte; `response_format.type=json_schema`; `response_format.json_schema.name=mutable_judge_v2`; `response_format.json_schema.strict=true`; `provider.require_parameters=true`; `provider.order` seulement pour les modeles Anthropic | runtime DB `openai/gpt-5.2`, `1400`, timeout `10`; pas de `stop`, pas de streaming; JSON `mutable_judge_v2` impose par structured output puis revalide par le validateur metier FridaDev |
| Resume conversationnel | JSON OpenRouter dans `summarizer.summarize_conversation()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens` depuis `summary_model` | defaut benchmarke `openai/gpt-5.4-mini`, `0.3`, `1.0`, `2000`, timeout `90`; la fonction ne prend plus de modele en argument; pas de `stop`, pas de streaming, pas de `response_format`; texte libre attendu |
| Stimmung agent | JSON OpenRouter dans `stimmung_agent._call_model()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens` | primary/fallback partagent la meme forme; pas de `stop`, pas de streaming, pas de `response_format` |
| Validation agent | JSON OpenRouter dans `validation_agent._call_model()` | `model`, `messages`, `temperature`, `top_p`, `max_tokens=_bounded_response_max_tokens(max_tokens)` | primary/fallback partagent la meme forme; borne serveur `140` apres decision benchmark du 2026-05-19; pas de `stop`, pas de streaming, pas de `response_format` |
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

- `main_model.api_key`: `is_set=True`, origine affichage `admin_ui`, resolution effective `db_encrypted`;
- `config.OR_KEY`: present en environnement, mais le chemin normal runtime passe par `runtime_settings.get_runtime_secret_value('main_model', 'api_key')`.

Donc la source de verite applicative actuelle est:

1. runtime settings DB chiffre (`db_encrypted`) quand disponible;
2. fallback env seulement si le champ runtime est d'origine `env_seed` et que la valeur env existe;
3. erreur si aucune source n'est resoluble.

### Tableau auth / transport

| Caller OpenRouter demande | Caller normalise par `llm_client` | Token | Base URL effective | Referer/title effectifs | Attribution payload | `X-Frida-Caller` vers provider | Particularite |
|---|---|---|---|---|---|---|---|
| `llm` | `llm` | `main_model.api_key` | chat: `config.OR_BASE`; helper: runtime `main_model.base_url` | `main_model.referer_llm` = `https://fridadev.frida-system.fr/openrouter/main-chat`; `main_model.title_llm` = `FridaDev / Main Chat` | `metadata.frida_caller=main_chat`, `metadata.frida_slot=main_model`, `trace.generation_name=FridaDev / Main Chat` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy` avant l'appel externe | chat principal n'utilise pas encore le helper URL |
| `web_reformulation` | `web_reformulation` | meme | runtime `main_model.base_url` via helper | `main_model.referer_web_reformulation` = `https://fridadev.frida-system.fr/openrouter/web-reformulation`; `main_model.title_web_reformulation` = `FridaDev / Web Reformulation` | `metadata.frida_caller=web_reformulation`, `metadata.frida_slot=web_reformulation_model`, `trace.generation_name=FridaDev / Web Reformulation` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | modele et petits parametres dedies via `web_reformulation_model` |
| `arbiter` | `arbiter` | meme | runtime `main_model.base_url` via helper | `main_model.referer_arbiter` = `https://fridadev.frida-system.fr/openrouter/memory-arbiter`; `main_model.title_arbiter` = `FridaDev / Memory Arbiter` | `metadata.frida_caller=memory_arbiter`, `metadata.frida_slot=memory_arbiter_model`, `trace.generation_name=FridaDev / Memory Arbiter` | transmis: appel direct `requests.post()` sans proxy | modele et parametres dedies via `memory_arbiter_model` |
| `identity_extractor` | `identity_extractor` | meme | runtime `main_model.base_url` via helper | `main_model.referer_identity_extractor` = `https://fridadev.frida-system.fr/openrouter/identity-extractor`; `main_model.title_identity_extractor` = `FridaDev / Identity Extractor` | `metadata.frida_caller=identity_extractor`, `metadata.frida_slot=identity_extractor_model`, `trace.generation_name=FridaDev / Identity Extractor` | transmis: appel direct `requests.post()` sans proxy | modele et parametres dedies via `identity_extractor_model` |
| `identity_periodic_agent` | `identity_periodic_agent` | meme | runtime `main_model.base_url` via helper | `main_model.referer_identity_periodic` = `https://fridadev.frida-system.fr/openrouter/identity-periodic`; `main_model.title_identity_periodic` = `FridaDev / Identity Periodic` | `metadata.frida_caller=identity_periodic`, `metadata.frida_slot=identity_periodic_model`, `trace.generation_name=FridaDev / Identity Periodic` | transmis: appel direct `requests.post()` sans proxy | modele et parametres dedies via `identity_periodic_model` |
| `resumer` | `resumer` | meme | runtime `main_model.base_url` via helper | `main_model.referer_resumer` = `https://fridadev.frida-system.fr/openrouter/summary`; `main_model.title_resumer` = `FridaDev / Summary` | `metadata.frida_caller=summary`, `metadata.frida_slot=summary_model`, `trace.generation_name=FridaDev / Summary` | transmis: appel direct `requests.post()` sans proxy | modele et parametres dedies via `summary_model` |
| `stimmung_agent` | `stimmung_agent` | meme | runtime `main_model.base_url` via helper | `main_model.referer_stimmung_agent` = `https://fridadev.frida-system.fr/openrouter/stimmung`; `main_model.title_stimmung_agent` = `FridaDev / Stimmung` | `metadata.frida_caller=stimmung_agent`, `metadata.frida_slot=stimmung_agent_model`, `trace.generation_name=FridaDev / Stimmung` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | primary/fallback propres |
| `validation_agent` | `validation_agent` | meme | runtime `main_model.base_url` via helper | `main_model.referer_validation_agent` = `https://fridadev.frida-system.fr/openrouter/validation-agent`; `main_model.title_validation_agent` = `FridaDev / Validation Agent` | `metadata.frida_caller=validation_agent`, `metadata.frida_slot=validation_agent_model`, `trace.generation_name=FridaDev / Validation Agent` | chemin `/api/chat`: construit puis retire par `_RequestsChatLogProxy`; appel direct de module: transmis | primary/fallback propres |

### Ce que le repo permet deja

- Un seul secret OpenRouter peut etre rote dans `main_model.api_key`.
- Les headers `HTTP-Referer`, `X-OpenRouter-Title`, `X-Title` distinguent les callers OpenRouter principaux. `X-Title` reste conserve en compatibilite; `X-OpenRouter-Title` est la forme moderne.
- Les payloads ajoutent une attribution content-free: `metadata.frida_caller`, `metadata.frida_slot`, `trace.trace_name=FridaDev`, `trace.generation_name`. Le champ provider `user` n'est pas utilise pour nommer les callers.
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
| Mutable identity judge | JSON `mutable_judge_v2` avec `schema_version`, `verdicts[]`, `meta` | `validate_mutable_judge_contract_v2()` exige sujets `llm` et `user`, verdicts `add` / `no_change`, proposition add non vide/declarative et `source_refs` bornees a `pair_01..pair_05` | timeout/transport/JSON invalide/contrat invalide => `skipped` content-free et fenetre preservee | verdicts `add` appliques en append-only par `mutable_identity_apply`; events content-free `mutable_identity_judge` / `mutable_identity_judge_apply` |
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

#### Mutable identity judge

```json
{
  "schema_version": "mutable_judge_v2",
  "verdicts": [
    {
      "subject": "llm",
      "verdict": "no_change",
      "proposition": "",
      "reason_code": "no_mutable_identity_signal",
      "continuity_kind": "none",
      "source_refs": [],
      "guard_notes": []
    },
    {
      "subject": "user",
      "verdict": "add",
      "proposition": "Tof tient une limite identitaire stable.",
      "reason_code": "explicit_self_definition_continuity",
      "continuity_kind": "posture",
      "source_refs": ["pair_01"],
      "guard_notes": []
    }
  ],
  "meta": {
    "execution_status": "complete",
    "window_pairs_count": 5,
    "window_complete": true
  }
}
```

Verdicts autorises: `no_change`, `add`. Aucun champ `operation`, `target`, `targets`, `target_ref` ou `target_refs` n'appartient au contrat actif. Le validateur refuse les top-level keys inattendues, les shapes incorrectes, les reason codes techniques comme verdict modele, les verdicts hors contrat, les propositions non declaratives et les `source_refs` hors `pair_01..pair_05`.

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

- `chat_llm_flow.py` appelle encore `config.OR_BASE` au lieu de `llm_client.or_chat_completions_url()`. L'arbitre memoire, l'extracteur identity au tour, l'agent periodic identity et le resume conversationnel utilisent desormais le transport runtime partage.
- `arbiter_model` existe encore dans le schema runtime par compatibilite, mais ne pilote plus un caller actif. Il peut etre supprime dans un lot separe si la migration de compatibilite devient explicitement souhaitable.

### Endroits fragiles ou implicites

- Les sorties `identity_extractor` fail-open vers `[]`, ce qui est volontaire pour ne pas casser le tour, mais rend les erreurs invisibles dans le comportement utilisateur direct.
- Le summary ne possede pas de schema JSON; c'est un texte libre. C'est normal pour une synthese, mais plus fragile a verifier automatiquement.
- `extract_openrouter_text()` suppose `choices[0].message.content`; il n'y a pas de contrat alternatif si un provider renvoie une autre forme.
- Les parametres `reasoning` / `effort` / equivalents ne sont envoyes par aucun caller. Si l'on veut les utiliser plus tard, il faudra un contrat explicite par role.
- L'admin runtime expose un statut "shared transport" pour certains composants, mais cette verite est incomplete pour les callers encore branches sur `config.OR_BASE`.

## Ce que nous pourrons raffiner ensuite

Pistes candidates, hors scope de ce lot:

1. Normaliser tous les appels OpenRouter sur `llm_client.or_chat_completions_url()` pour que `main_model.base_url` soit vraiment source de verite globale.
2. Decider si `arbiter_model` doit rester un slot legacy de compatibilite ou etre retire dans une migration separee.
3. Preparer une rotation OpenRouter sans fuite: un plan de migration `main_model.api_key`, validation runtime, smoke calls, puis eventuelle separation par projets.
4. Ajouter un tableau operateur "model topology" dans l'admin si la rotation multi-projets devient un chantier.

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
| `main_model` | `model` | `openai/gpt-5.1`; precedent `anthropic/claude-sonnet-4.6` | `admin_ui` |
| `main_model` | `temperature` | `0.7` | `admin_ui` |
| `main_model` | `top_p` | `1.0` | `db_seed` |
| `main_model` | `response_max_tokens` | `8192` | `admin_ui` |
| `main_model` | `api_key` | secret present, resolu `db_encrypted` | `admin_ui` / DB chiffree |
| `arbiter_model` | `model` / `temperature` / `top_p` / `timeout_s` | legacy non effectif | section conservee par compatibilite, aucun caller modele actif ne la lit comme source effective |
| `identity_extractor_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` apres bootstrap |
| `identity_extractor_model` | `temperature` | `0.0` | `db_seed` apres bootstrap |
| `identity_extractor_model` | `top_p` | `1.0` | `db_seed` apres bootstrap |
| `identity_extractor_model` | `max_tokens` | `700` | `db_seed` apres bootstrap |
| `identity_extractor_model` | `timeout_s` | `10` | `db_seed` apres bootstrap |
| `identity_periodic_model` | `model` | `openai/gpt-5.2` | `runtime DB` |
| `identity_periodic_model` | `temperature` | `0.0` | `db_seed` apres bootstrap |
| `identity_periodic_model` | `top_p` | `1.0` | `db_seed` apres bootstrap |
| `identity_periodic_model` | `max_tokens` | `1400` | `db_seed` apres bootstrap |
| `identity_periodic_model` | `timeout_s` | `10` | `db_seed` apres bootstrap |
| `memory_arbiter_model` | `model` | `mistralai/mistral-small-2603` | `db_seed` apres bootstrap |
| `memory_arbiter_model` | `temperature` | `0.0` | `db_seed` apres bootstrap |
| `memory_arbiter_model` | `top_p` | `1.0` | `db_seed` apres bootstrap |
| `memory_arbiter_model` | `max_tokens` | `600` | `db_seed` apres bootstrap |
| `memory_arbiter_model` | `timeout_s` | `10` | `db_seed` apres bootstrap |
| `summary_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` |
| `summary_model` | `temperature` | `0.3` | `db_seed` apres bootstrap |
| `summary_model` | `top_p` | `1.0` | `db_seed` apres bootstrap |
| `summary_model` | `max_tokens` | `2000` | `db_seed` apres bootstrap |
| `summary_model` | `timeout_s` | `90` | `db_seed` apres bootstrap |
| `web_reformulation_model` | `model` | `openai/gpt-5.4-mini` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `temperature` | `0.2` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `max_tokens` | `40` | `db_seed` apres bootstrap / env fallback |
| `web_reformulation_model` | `timeout_s` | `10` | `db_seed` apres bootstrap / env fallback |
| `stimmung_agent_model` | `primary_model` | `google/gemini-3.1-flash-lite` | `db_seed`; decision humaine du 2026-05-19 |
| `stimmung_agent_model` | `fallback_model` | `openai/gpt-5.4-nano` | `db_seed` |
| `validation_agent_model` | `primary_model` | `google/gemini-3.1-flash-lite` | `db_seed`; decision humaine du 2026-05-19 |
| `validation_agent_model` | `fallback_model` | `openai/gpt-5.4-nano` | `db_seed` |
| `validation_agent_model` | `max_tokens` | `140` | `db_seed`; relance benchmark `max_tokens=140` |
| `embedding` | `endpoint` | `https://embed.frida-system.fr` | `db_seed` |
| `embedding` | `model` | `intfloat/multilingual-e5-small` | `db_seed` |
| `embedding` | `dimensions` | `384` | `db_seed` |
| `embedding` | `token` | secret present, resolu `db_encrypted` | `env_backfill` / DB chiffree |
| `services` | `searxng_url` | `http://searxng:8080` | `admin_ui` |
| `services` | `crawl4ai_url` | `http://crawl4ai:11235` | `admin_ui` |
| `services` | `crawl4ai_token` | secret present, resolu `db_encrypted` | `env_backfill` / DB chiffree |

Constantes runtime `config.py` relevees dans le conteneur:

- `OR_BASE='https://openrouter.ai/api/v1'`;
- `OR_MODEL='openai/gpt-5.1'` comme seed/env; le modele principal effectif reste lu dans `main_model.model` runtime DB;
- `WEB_REFORMULATION_MODEL='openai/gpt-5.4-mini'`;
- `WEB_REFORMULATION_TEMPERATURE=0.2`;
- `WEB_REFORMULATION_MAX_TOKENS=40`;
- `WEB_REFORMULATION_TIMEOUT_S=10`;
- `MEMORY_ARBITER_MODEL='mistralai/mistral-small-2603'`;
- `MEMORY_ARBITER_TEMPERATURE=0.0`;
- `MEMORY_ARBITER_TOP_P=1.0`;
- `MEMORY_ARBITER_MAX_TOKENS=600`;
- `MEMORY_ARBITER_TIMEOUT_S=10`;
- `TIMEOUT_S=900`;
- `ARBITER_TIMEOUT_S=10`;
- `SUMMARY_MODEL='openai/gpt-5.4-mini'`;
- `SUMMARY_TEMPERATURE=0.3`;
- `SUMMARY_TOP_P=1.0`;
- `SUMMARY_TARGET_TOKENS=2000`;
- `SUMMARY_TIMEOUT_S=90`;
- `WHISPER_API_URL='http://platform-whisper-api:9001'`;
- `WHISPER_API_TIMEOUT_S=180`;
- `WHISPER_API_KEY` present;
- `ACTIVE_DOCUMENT_OCR_URL='http://platform-stirling-pdf:8080/pdf/api/v1/misc/ocr-pdf'`;
- `ACTIVE_DOCUMENT_IMAGE_TO_PDF_URL='http://platform-stirling-pdf:8080/pdf/api/v1/convert/img/pdf'`;
- `ACTIVE_DOCUMENT_OCR_TIMEOUT_S=180`;
- `ACTIVE_DOCUMENT_OCR_LANGUAGES='fra+eng+deu'`;
- `ACTIVE_DOCUMENT_OCR_MAX_PAGES=25`;
- `ACTIVE_DOCUMENT_OCR_MAX_BYTES=26214400`;
- `EMBED_BASE_URL='https://embed.frida-system.fr'`;
- `EMBED_DIM=384`;
- `MEMORY_TOP_K=5`.
