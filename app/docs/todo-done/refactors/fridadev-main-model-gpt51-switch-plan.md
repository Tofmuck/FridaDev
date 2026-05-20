# Plan de bascule du modele principal vers GPT-5.1

Statut: plan ouvert initial, maintenant complete par le TODO d'execution
`app/docs/todo-done/refactors/fridadev-main-model-gpt51-switch-todo.md`.

Date: 2026-05-20.

Modele cible: `openai/gpt-5.1`.

## Question pre-plan

Existe-t-il un meilleur plan ?

Oui: le meilleur plan n'est pas une bascule immediate. Le plan le plus sur est:

1. auditer l'etat live et les couts;
2. verifier la compatibilite GPT-5.1 sur les chemins Frida reels, surtout streaming et images actives;
3. comparer la qualite sur une petite matrice de tours humains;
4. basculer seulement la section runtime `main_model` si le GO est confirme;
5. realiser un smoke live court;
6. garder un rollback immediat vers le modele precedent.

Ce document decrit le plan initial. La decision operateur du 2026-05-20 avance vers
une bascule effective dans la branche `feature/main-model-gpt51`, avec tests
techniques cibles et sans matrice conversationnelle humaine prealable.

## Sources lues et constats principaux

Sources principales:

- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`;
- `app/docs/states/specs/admin-runtime-settings-schema.md`;
- `app/docs/states/specs/active-conversation-documents-contract.md`;
- `app/docs/states/specs/chat-time-grounding-contract.md`;
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`;
- `app/core/llm_client.py`;
- `app/core/chat_service.py`;
- `app/core/chat_llm_flow.py`;
- `app/core/chat_prompt_context.py`;
- `app/core/active_document_prompt_lane.py`;
- `app/admin/runtime_settings.py`;
- `app/admin/runtime_settings_spec.py`;
- `app/admin/runtime_settings_validation.py`;
- `app/admin/admin_settings_routes.py`;
- `app/admin/runtime_settings_write_path.py`;
- `app/server.py`;
- `app/web/admin_settings_catalog.js`.

Constats:

- Le chat principal lit le modele dans la section runtime `main_model`.
- Le modele live OVH releve avant bascule le 2026-05-20 etait `anthropic/claude-sonnet-4.6`.
- Les petits agents ne doivent pas etre touches par cette bascule: memory arbiter, identity extractor, identity periodic, summary, web reformulation, Stimmung et validation ont leurs slots propres.
- Le transport OpenRouter partage le secret applicatif `main_model.api_key`; la bascule de modele ne demande pas de nouveau secret.
- La V0 images actives utilisait une allowlist applicative stricte limitee a `anthropic/claude-sonnet-4.6`; le chantier `feature/main-model-gpt51` l'etend a `openai/gpt-5.1` tout en conservant Claude pour rollback.

## 1. Audit de l'etat actuel

Avant toute bascule, relever un snapshot content-free:

```text
Section: main_model
base_url: https://openrouter.ai/api/v1
model: anthropic/claude-sonnet-4.6
temperature: 0.7
top_p: 1.0
response_max_tokens: 8192
api_key: present, sans affichage de valeur
referer_llm: https://fridadev.frida-system.fr/openrouter/main-chat
title_llm: FridaDev / Main Chat
```

Points a verifier:

- `GET /api/admin/settings/main-model` affiche bien `main_model.model`.
- `POST /api/admin/settings/main-model/validate` valide base URL, modele non vide, sampling et secret resoluble.
- Les logs OpenRouter affichent toujours `FridaDev / Main Chat` pour le flux principal.
- Les logs applicatifs continuent de produire `llm_payload`, `llm_call`, `llm_provider_response` et `AssistantText`.
- Le provider model retourne par OpenRouter est note avant la bascule pour permettre la comparaison.

Important: ne pas modifier `main_model.api_key`, `main_model.base_url`, les referer/title ni les petits slots modeles pendant ce lot.

## 2. Compatibilite GPT-5.1

Metadonnees OpenRouter publiques revalidees le 2026-05-20 via `https://openrouter.ai/api/v1/models`, sans cle:

| Modele | Modality | Input | Output | Contexte | Prompt | Completion | Cache read |
|---|---|---|---|---:|---:|---:|---:|
| `openai/gpt-5.1` | `text+image+file->text` | `text`, `image`, `file` | `text` | 400000 | 0.00000125 | 0.00001 | 0.00000013 |
| `openai/gpt-5.2` | `text+image+file->text` | `text`, `image`, `file` | `text` | 400000 | 0.00000175 | 0.000014 | 0.000000175 |
| `anthropic/claude-sonnet-4.6` | `text+image+file->text` | `text`, `image`, `file` | `text` | 1000000 | 0.000003 | 0.000015 | 0.0000003 |

Compatibilite attendue:

- Contexte: GPT-5.1 a 400k tokens, suffisant pour les tours Frida observes autour de 40k a 50k tokens d'entree.
- Input texte: compatible avec le prompt systeme, le dialogue recent, le resume, l'identite, la memoire, le web et les documents actifs texte.
- Output texte: compatible avec `extract_openrouter_text()` et la normalisation assistant.
- Streaming: compatible attendu avec `stream=true` et `stream_options.include_usage=true`, a verifier en smoke.
- Non-stream: compatible attendu avec la forme OpenRouter `choices[0].message.content`, a verifier.
- Usage/cost: a verifier dans `llm_provider_response` et dans la console OpenRouter.
- Images actives: OpenRouter annonce `image` en input, mais FridaDev doit d'abord accepter `openai/gpt-5.1` dans la compatibilite applicative images. Le payload attendu reste un message `user` multimodal avec contenu `text` puis `image_url`.

Conclusion compatibilite: GPT-5.1 est un candidat serieux pour le chat texte et documents texte. Pour "sans casser les images actives", le chantier d'execution ajoute explicitement `openai/gpt-5.1` a l'allowlist images actives V0 et le prouve par tests techniques.

## 3. Mesure cout actuelle

Objectif: mesurer quelques vrais tours, sans benchmark artificiel lourd.

Pour chaque tour, relever dans OpenRouter et dans les logs Frida:

- modele principal demande;
- provider model retourne;
- prompt tokens;
- completion tokens;
- cout;
- streaming oui/non;
- presence de documents actifs;
- presence d'image active;
- cout des petits modules separes.

Echantillon minimal:

| Tour | Condition | Mesure principale |
|---|---|---|
| A | texte simple, sans web, sans document | cout de base main + petits agents |
| B | contexte long, conversation chargee | prompt tokens main chat |
| C | document actif texte | cout d'injection documentaire |
| D | image active | compatibilite `image_url`, cout vision, provider model |
| E | web manuel | cout web reformulation + main chat |

Exemple de comparaison sur un tour observe:

```text
Claude Sonnet 4.6:
42641 input tokens * 0.000003 = 0.127923
330 output tokens * 0.000015 = 0.004950
total main estime = 0.132873

GPT-5.1:
42641 input tokens * 0.00000125 = 0.053301
330 output tokens * 0.00001 = 0.003300
total main estime = 0.056601
```

Lecture:

- GPT-5.1 reduirait ce main call d'environ 57% par rapport a Claude Sonnet 4.6.
- GPT-5.2 est 40% plus cher que GPT-5.1 sur input et output; formule inverse, GPT-5.1 est environ 28.6% moins cher que GPT-5.2.
- Les petits agents ne sont pas le levier principal si le main chat represente plus de 90% du cout du tour.
- Le caching OpenRouter ne doit pas etre suppose garanti; le cout sans cache reste la reference conservatrice.

## 4. Test qualite

Comparer Claude Sonnet 4.6 et GPT-5.1 sur des tours humains courts, sans chercher un benchmark massif.

Matrice proposee:

| Cas | Attendu Frida | A surveiller |
|---|---|---|
| Tour simple | reponse naturelle, ni froide ni bavarde | voix, longueur, presence |
| Long contexte | reprise correcte du fil | oublis, confusion de dates |
| Memoire / identity | usage sobre des faits pertinents | surinterpretation identitaire |
| Resume conversationnel | continuite sans inventer | faux souvenirs |
| Document actif texte | lecture du document injecte | confusion document/memoire |
| Image active | lecture visuelle via `image_url` | vision moins fine, exclusion par allowlist |
| Web manuel | distinction lecture directe/snippet/echec | claims web trop forts |
| Tour sensible | prudence sans bureaucratie | dramatisation ou meta excessive |
| Tour phatique | chaleur et presence | reponse lapidaire |

Notation simple par tour:

- qualite de voix: OK / a reprendre / non;
- precision factuelle: OK / doute / erreur;
- respect garde-fous temporels: OK / non;
- respect documents/images: OK / non;
- cout et latence: chiffres OpenRouter;
- decision finale: garder GPT-5.1, revenir Claude, ou garder Claude seulement en mode qualite.

## 5. Bascule technique proposee

Chemin operateur recommande le jour du GO:

1. Ouvrir `/admin`.
2. Aller dans les runtime settings, section `main_model` / "Modele principal".
3. Verifier que `base_url`, secret applicatif, referer/title et sampling sont inchanges.
4. Valider une previsualisation de patch sur `main_model`.
5. Modifier uniquement:

```json
{
  "model": {
    "value": "openai/gpt-5.1"
  }
}
```

6. Sauvegarder via l'UI admin ou via `PATCH /api/admin/settings/main-model` depuis une session admin protegee.
7. Verifier par `GET /api/admin/settings/main-model` que `model.value` vaut `openai/gpt-5.1`.

Valeurs qui changent:

- `main_model.model`: `anthropic/claude-sonnet-4.6` -> `openai/gpt-5.1`.

Valeurs qui ne changent pas:

- `main_model.base_url`;
- `main_model.api_key`;
- `main_model.referer_llm`;
- `main_model.title_llm`;
- `main_model.temperature` au premier GO, sauf decision qualite explicite;
- `main_model.top_p`;
- `main_model.response_max_tokens`;
- tous les slots lateraux: `memory_arbiter_model`, `identity_extractor_model`, `identity_periodic_model`, `summary_model`, `web_reformulation_model`, `stimmung_agent_model`, `validation_agent_model`.

Rebuild:

- Aucun rebuild n'est attendu si la bascule passe par l'UI/API admin, car `update_runtime_section()` ecrit en DB, historise et invalide le cache runtime du process.
- Si quelqu'un modifie directement la DB hors API, le cache applicatif peut rester stale; ce chemin est deconseille pour le GO.

Precondition images actives:

- `openai/gpt-5.1` doit etre ajoute et teste dans la compatibilite applicative images avant ou dans le meme lot que le GO runtime.
- Le mini-lot attendu est borne: etendre la compatibilite image a GPT-5.1, prouver que le payload `text` puis `image_url` fonctionne, puis garder l'observabilite content-free existante.

## 6. Tests avant/apres bascule

Avant GO:

- `git status --short` pour confirmer aucun patch runtime non voulu.
- Runtime settings:
  - `app/tests/test_server_admin_settings_read_contract.py`;
  - `app/tests/test_server_admin_settings_patch_contract.py`;
  - `app/tests/test_server_admin_settings_validate_contract.py`;
  - `app/tests/unit/runtime_settings/`.
- Chat principal:
  - `app/tests/unit/chat/test_chat_llm_flow.py`;
  - `app/tests/test_server_chat_route_transport_contract.py`;
  - `app/tests/test_server_chat_conversation_id_contract.py`.
- Streaming:
  - `app/tests/unit/chat/test_chat_stream_control.py`;
  - `app/tests/unit/frontend_chat/test_stream_control_parser_module.js`;
  - `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`.
- Documents actifs:
  - `app/tests/test_server_active_documents_contract.py`;
  - `app/tests/unit/core/test_active_document_prompt_lane.py`;
  - `app/tests/unit/core/test_active_document_non_contamination_lot5.py`.
- Images actives:
  - `app/tests/test_server_chat_active_image_documents_contract.py`;
  - eventuels tests a ajouter si GPT-5.1 est allowliste.
- Memory / identity / summary:
  - `app/tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py`;
  - `app/tests/unit/memory/test_arbiter_phase4.py`;
  - `app/tests/unit/memory/test_summarizer_phase4.py`;
  - `app/tests/unit/memory/test_summarizer_phase13.py`;
  - `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`;
  - `app/tests/unit/memory/test_identity_temporal_guard.py`.

Apres GO:

- refaire un chat texte stream;
- refaire un chat texte non-stream si une route/procedure le permet;
- refaire un tour avec document actif texte;
- refaire un tour avec image active;
- refaire un tour memoire/identity naturel;
- verifier la console OpenRouter et les logs applicatifs.

## 7. Smoke live minimal

Preuves live minimales:

1. `/admin` reste protege par Authelia.
2. `GET /api/admin/settings/main-model` montre `openai/gpt-5.1`.
3. Chat texte simple en streaming:
   - reponse complete;
   - terminal stream normal;
   - `llm_provider_response` contient model/provider/tokens.
4. Chat non-stream si disponible:
   - HTTP 200;
   - message assistant persiste.
5. Document actif texte:
   - lane injectee ou exclusion expliquee;
   - aucune contamination memoire/identity/summary.
6. Image active:
   - payload `text` puis `image_url`;
   - provider model observe;
   - usage/cout OpenRouter observe;
   - absence de fuite de base64 ou bytes image dans logs, docs, read-models et UI.
7. Observabilite:
   - OpenRouter affiche `FridaDev / Main Chat`;
   - cout/prompt/completion visibles;
   - pas de secret dans logs.

## 8. Rollback / retour arriere

Rollback immediat recommande:

1. Ouvrir `/admin`.
2. Revenir dans `main_model`.
3. Modifier uniquement:

```json
{
  "model": {
    "value": "anthropic/claude-sonnet-4.6"
  }
}
```

4. Sauvegarder via l'UI admin ou via `PATCH /api/admin/settings/main-model`.
5. Verifier par `GET /api/admin/settings/main-model`.
6. Faire un smoke texte court et, si le rollback est motive par l'image, un smoke image active.

Rebuild:

- Non requis si le rollback passe par l'API admin.
- A envisager seulement si le cache a ete contourne par une modification DB manuelle ou si le process est dans un etat incoherent.

Documentation de l'operation:

- noter le GO ou rollback dans une note `todo-done/notes/` ou dans une validation datee si l'operation devient un chantier clos;
- conserver les chiffres OpenRouter: prompt tokens, completion tokens, cout, provider model, latence, streaming.

## 9. Risques

- Voix moins bonne ou plus plate: GPT-5.1 peut etre efficace mais moins "presence" que Claude sur certains tours.
- Reponses trop lapidaires: a surveiller avec les tours phatiques et sensibles.
- Differences de vision: meme si OpenRouter annonce l'image en input, la lecture visuelle peut diverger de Claude.
- Verrou applicatif images actives: si une regression retire GPT-5.1 de l'allowlist FridaDev, les images actives seront exclues avec `image_model_unsupported`.
- Respect du prompt: verifier que GPT-5.1 suit bien les garde-fous temporels, documents actifs, web et jugement hermeneutique.
- Latence: le cout baisse ne garantit pas une latence meilleure.
- Cout image: la vision peut avoir une tarification effective differente selon provider/routage; mesurer, ne pas supposer.
- Divergence provider OpenRouter: le canonical/provider model peut changer ou router differemment.
- Caching non garanti: les estimations doivent partir du tarif sans cache.
- Longue fenetre mais prompt trop lourd quand meme: 400k suffit largement aujourd'hui, mais le budget prompt complet reste a observer.
- `response_max_tokens=8192`: conserver au GO evite de melanger deux variables, mais peut produire des couts de sortie eleves si GPT-5.1 devient plus bavard.

## Decision GO / no-go

GO seulement si:

- GPT-5.1 passe le test texte stream;
- GPT-5.1 passe le test non-stream ou le chemin non-stream est explicitement juge hors usage;
- documents actifs texte restent corrects;
- images actives sont preservees, soit par compatibilite code testee, soit par decision explicite de differer la bascule;
- la voix de Frida reste acceptable;
- les logs OpenRouter montrent bien `FridaDev / Main Chat` et les usages/couts;
- le rollback a ete teste ou au moins repete operatoirement.

No-go si:

- les images actives deviennent indisponibles sans decision explicite;
- GPT-5.1 perd trop la voix ou devient trop sec;
- les garde-fous temporels ou documentaires regressent;
- l'observabilite OpenRouter ne permet plus de suivre provider/tokens/cout;
- le rollback n'est pas clair au moment du GO.

## Cloture

Cloture du 2026-05-20:

- Bascule runtime effectuee: `main_model.model = openai/gpt-5.1`.
- Parametres conserves autant que possible: `temperature=0.7`, `top_p=1.0`, `response_max_tokens=8192`, base URL, token et projet OpenRouter inchanges.
- `openai/gpt-5.1` ajoute a l'allowlist des images actives V0.
- L'audit tokens a conclu a une difference de tokenizer/reporting provider entre Claude et GPT-5.1, sans nouveau resume et sans reduction reelle du contexte envoye.
- Les investigations de cout sont arretees pour ce chantier.
- Retour arriere possible via runtime settings vers `anthropic/claude-sonnet-4.6` si besoin, hors scope de cette cloture.
