# Export du prompt effectif du modèle principal

Ce document cartographie ce qui agit réellement comme prompt du modèle principal FridaDev au moment d'un appel `/api/chat`.

Il distingue trois niveaux:

- **prompts sources**: fichiers texte et doctrines de base;
- **blocs runtime dérivés**: temps, identité, mémoire, web, jugement herméneutique, guards;
- **payload effectif**: `messages[]` et paramètres envoyés à OpenRouter pour `FridaDev / Main Chat`.

Le prompt effectif n'est donc pas seulement `app/prompts/*.txt`: c'est le résultat ordonné du pipeline de chat, des sélections documentaires et des garde-fous injectés au tour.

## Disponibilité et criticité des prompts

`app/core/prompt_loader.py` classe une lecture comme `available`,
`unavailable`, `undecodable` ou `empty`. Le lecteur historique utilisé par les
surfaces admin reste souple et retourne un texte vide lorsque le fichier n'est
pas utilisable. La criticité est appliquée au consommateur, pas au démarrage
global de FridaDev.

| Prompt | Consommateur runtime actif | Criticité | Comportement si absent, illisible ou vide | Provider appelé |
| --- | --- | --- | --- | --- |
| `main_system` | `/api/chat`; création `/api/conversations` | Constitutif du chat | `503 critical_prompt_unavailable` avant résolution ou création de conversation; identifiant stable `main_system` | Non |
| `main_hermeneutical` | `/api/chat` | Constitutif du chat | Même refus avant résolution de session; non requis par la simple création de conversation | Non |
| `summary_system` | `summarizer.maybe_summarize()` | Requis pour le résumé seulement | Résumé ignoré avec `False`; aucun faux résumé ni marquage de messages | Non |
| `web_reformulation` | `web_search.reformulate()` | Requis pour la reformulation seulement | Requête utilisateur originale conservée à l'identique; la recherche peut poursuivre son repli local | Non |
| `identity_mutable_judge_v2` | juge Identity mutable | Requis pour le juge seulement | Résultat technique local `runtime_safety_violation`; aucune écriture Identity | Non |
| `stimmung_agent` | agent Stimmung | Secondaire fail-open local | Résultat local `prompt_missing`; le chat continue | Non |
| `validation_agent` | agent Validation | Secondaire fail-open local | Validation fail-open `prompt_missing`; le chat continue | Non |
| `arbiter` | arbitre Memory | Secondaire fail-open local | Sélection déterministe `prompt_missing` | Non |
| `identity_extractor` (chemin de compatibilite) | `dialogic_context_hint_extractor` | Secondaire fail-open local | `dialogic_context_prompt_missing`; aucun hint ni ecriture Identity | Non |
| `identity_periodic_agent` | Aucun consommateur de prompt actif | Legacy pré-refactor | Aucun blocage import, validation offline ou chat | Non |
| `identity_mutable_rewriter` | Aucun consommateur de prompt actif; rewriter retiré | Legacy | Aucun blocage import, validation offline ou chat | Non |
| `identity_mutable_judge` v1 | Aucun consommateur actif | Legacy | Aucun blocage import, validation offline ou chat | Non |

Aucun consommateur modèle actif n'accepte donc légitimement un prompt fichier
vide. Les trois artefacts legacy ne sont pas réactivés et ne sont pas des
conditions de disponibilité.

## Ordre du pipeline effectif

| Ordre | Source | Responsable | Condition | Forme finale OpenRouter | Contenu / persistance |
| --- | --- | --- | --- | --- | --- |
| 1 | Prompts sources constitutifs | `app/core/chat_service.py::chat_response`, `app/core/chat_prompt_context.py::resolve_backend_prompts` | Les deux fichiers doivent être utilisables | Refus `503` avant `resolve_chat_session()` sinon; premier message `role=system` après augmentation sur le chemin nominal | Source stable du dépôt; aucune mutation de conversation avant la preuve de disponibilité |
| 2 | Requête utilisateur et conversation courante | `app/core/chat_session_flow.py`, puis `chat_service` | Après validation des prompts constitutifs | Le message utilisateur est ajouté à la conversation avant construction du payload | Contient le texte utilisateur; persisté comme message de conversation après le tour |
| 3 | Bloc temps `NOW` / timezone | `app/core/chat_prompt_context.py::build_augmented_system`, `app/core/hermeneutic_node/inputs/time_input.py` | Toujours | Ajouté au message `system` principal | Runtime content-free; Frida reçoit une référence temporelle, elle ne "sent" pas le temps |
| 4 | Identité | `app/core/chat_prompt_context.py::build_augmented_system`, module `identity` injecté par `chat_service` | Toujours si bloc identité disponible | Ajoutée au message `system` principal | Contient identité statique/mutable sélectionnée; issue du stockage identité, pas du tour brut |
| 5 | Résumé conversationnel potentiel | `app/memory/summarizer.py::maybe_summarize`, puis `app/core/conversations_prompt_window.py::build_prompt_messages` | Si un résumé actif existe après éventuelle mise à jour | Message séparé `role=system` | Contient résumé conversationnel persisté; le prompt n'inclut que le résumé actif utile |
| 6 | Mémoire et context hints | `app/core/chat_memory_flow.py::prepare_memory_context`, puis `conversations_prompt_window` | Selon mode mémoire et arbitrage | Messages `role=system`: indices, résumés parents, souvenirs retenus | Contient traces mémoire sélectionnées; les traces rejetées ne sont pas injectées |
| 7 | Inputs du tour pour le noeud herméneutique | `app/core/chat_turn_runtime_inputs.py`, `app/core/stimmung_agent.py`, `app/core/hermeneutic_node/*` | Toujours, avec données disponibles | Pas injectés directement sauf verdict final validé | Stimmung et inputs servent au cadrage local du tour; ce ne sont pas une psychologie durable. `validation_agent` lit d'abord la fenêtre dialogique, présume le sens sans inventer et traite les signaux structurés comme secondaires |
| 8 | Jugement herméneutique final | `app/core/chat_service.py::_run_hermeneutic_node_insertion_point`, `app/core/chat_prompt_context.py::build_hermeneutic_judgment_block` | Si le noeud produit des directives validées | Ajouté au message `system` principal | Content-free ou quasi content-free; cadre la posture et le régime final. `answer/presence` projette `regime_presence`, distinct de `suspend` |
| 9 | Guards runtime | `app/core/chat_prompt_context.py` | Conditionnels sauf guard texte selon contrat | Ajoutés au message `system` principal | Voice transcription, révélation identitaire directe, web read-state, réponse texte simple |
| 10 | Fenêtre conversationnelle | `app/core/conversations_prompt_window.py::build_prompt_messages` | Toujours | Messages `role=user`, `role=assistant`, parfois `role=system` pour silences et provenance assistant | Contient l'historique retenu après résumé actif; labels Delta-T et silences sont ajoutés runtime. Après un assistant portant une méta V1 valide, un marqueur `system` court projette seulement `response_origin` et l'injection Web effective au modèle principal |
| 11 | Contexte web | `app/core/chat_prompt_context.py::inject_web_context` | Web manuel/auto avec `context_block` | Préfixé dans le dernier message `role=user` | Contient extraits web sélectionnés; runtime du tour, pas mémoire par défaut |
| 12 | Documents actifs de conversation | `app/core/active_conversation_documents.py`, `app/core/active_document_prompt_lane.py` | Documents actifs présents et lisibles | Lane insérée avant le premier message de dialogue: `system` de contrat puis `user` documentaire | Peut contenir texte documentaire complet; non persisté dans l'historique comme nouveau message utilisateur |
| 13 | Fichiers workspace sélectionnés | `app/core/workspace_file_selection_prompt.py`, `active_document_prompt_lane.py` | Fichier explicitement coché dans la conversation | Même lane que les documents actifs | Conversation-scoped; texte/image/PDF seulement si sélectionné; pas Biblio, pas mémoire, pas RAG |
| 14 | Images et PDF multimodaux | `active_document_prompt_lane.py::_multimodal_content` | Modèle compatible, bytes disponibles, plafond provider respecté | Message `role=user` avec `content[]`: `text` puis `image_url` ou `file` | Les bytes sont envoyés au provider comme data URL dans le payload; logs/export doivent les expurger |
| 15 | Paramètres OpenRouter | `app/core/llm_client.py::build_payload`, `app/core/llm_client.py::with_provider_attribution` | Sauf override final déjà autorisé | Champs `model`, `temperature`, `top_p`, `max_tokens`, `stop`, `stream`, `metadata`, `trace` | Pas des messages de prompt, mais ils influencent l'appel et l'observabilité OpenRouter. Pour `answer/presence`, l'override exact `...` court-circuite aussi la résolution du secret, de l'URL et l'appel principal |

La provenance trans-tour ne persiste ni requête, ni source, ni extrait Web.
Seule la méta assistant content-free `assistant_runtime_provenance` est durable.
Elle distingue `main_model` de `final_lock` et indique si un contexte Web
utilisable a effectivement atteint le modèle principal. L'absence de cette
méta sur un message legacy reste une provenance inconnue. La reconstruction ne
relance aucune recherche et le marqueur n'est ni ajouté au contenu durable, ni
rendu dans l'UI.

## Ce qui n'est pas directement injecté

Ces éléments peuvent influencer le pipeline, mais ne deviennent pas automatiquement du texte vu par le modèle principal:

- le prompt interne du `stimmung_agent`;
- les sorties brutes du primary hermeneutic node et du `validation_agent`, sauf le jugement final synthétisé;
- les traces mémoire candidates rejetées;
- les prompts du summarizer, de l'extracteur de contexte dialogique et de l'identity periodic agent legacy;
- les prompts/outils de recherche web avant synthèse du `context_block`;
- les fichiers workspace non cochés;
- les documents exclus pour taille, type, modèle incompatible, disque absent ou OCR requis;
- les descriptions de répertoire de travail, qui restent UI-only;
- la Biblio/RAG, sauf chantier séparé explicitement branché.

## Regime local `presence`

`validation_agent` est le seul point de decision semantique du micro-lot. Il
peut valider `final_judgment_posture=answer` avec
`final_output_regime=presence` apres lecture de la fenetre dialogique locale.
Cette valeur est rejetee avec `clarify` ou `suspend`, et aucun fail-open ne la
synthetise.

`chat_service` transforme seulement ce verdict positif en
`AssistantResponseOverride(content="...")`. La precedence Agenda puis Biblio
reste intacte. `chat_llm_flow` reutilise ensuite sa frontiere existante:

- aucun appel au provider principal;
- meme succes JSON ou terminal `done` stream;
- un seul append assistant et une seule sauvegarde finale;
- texte visible et persiste exactement `...`;
- pas d'extraction Identity ni de trace Memory depuis cette sortie;
- message toujours present dans l'historique conversationnel canonique;
- aucune ecriture `node_state`, afin que `presence` reste locale au tour.

## Outil local d'export synthétique

Le script `app/scripts/export_main_prompt_payload.py` sait produire trois types d'artefacts:

- un export synthétique non sensible;
- un export local d'une conversation réelle, expurgé, non committé.
- un export court du `posture pack`, qui isole seulement les blocs normatifs et posturaux du modèle principal.

Le mode synthétique reconstruit un payload non sensible avec les mêmes briques que le pipeline principal:

- prompts sources réels;
- bloc temps;
- bloc identité synthétique;
- jugement herméneutique synthétique;
- guards runtime;
- résumé, mémoire et context hints synthétiques;
- contexte web synthétique;
- documents actifs synthétiques;
- fichier workspace sélectionné synthétique;
- image et PDF multimodaux synthétiques, expurgés à l'écriture.

Il n'appelle pas OpenRouter, ne lit pas la DB runtime, ne lit pas `.env` et n'affiche pas de secret.

Exemple Markdown:

```bash
python3 app/scripts/export_main_prompt_payload.py synthetic \
  --output /tmp/fridadev-main-prompt-audit.md
```

Exemple JSON:

```bash
python3 app/scripts/export_main_prompt_payload.py synthetic \
  --format json \
  --output /tmp/fridadev-main-prompt-audit.json
```

L'artefact généré peut être relu localement. Il ne doit pas être committé.

## Export court du posture pack

Le mode `posture` ne reconstruit pas toute la conversation et ne dump pas le payload complet. Il extrait les blocs qui disent au modèle principal comment répondre:

- voix, style et contrat de forme;
- hiérarchie des sources et prudence herméneutique;
- ontologie de la trace;
- référence temporelle;
- identité, sous forme synthétique non privée;
- guards runtime conditionnels;
- jugement herméneutique final, sous forme synthétique;
- contrat postural des documents actifs, images et fichiers workspace sélectionnés.

Exemple:

```bash
python3 app/scripts/export_main_prompt_payload.py posture \
  --output /tmp/fridadev-posture-pack.md
```

Ce mode produit un Markdown court avec une table des blocs posturaux, le texte exact des blocs sources ou générés, une section "Ce qui n'est pas postural" et une lecture courte. Les blocs conditionnels sont rendus avec des exemples synthétiques content-free: ils montrent la forme exacte quand ils sont actifs, sans inclure de conversation privée, de document réel, de web réel ou de data URL.

## Export local d'une conversation réelle

Le mode `conversation` charge une conversation réelle depuis le store runtime, garde les messages jusqu'au dernier tour utilisateur, reconstruit le payload principal sans appeler OpenRouter, puis écrit un Markdown ou JSON expurgé.

Exemple par identifiant explicite:

```bash
python3 app/scripts/export_main_prompt_payload.py conversation \
  --conversation-id <conversation-id> \
  --output /tmp/fridadev-real-main-prompt.md
```

Exemple JSON:

```bash
python3 app/scripts/export_main_prompt_payload.py conversation \
  --conversation-id <conversation-id> \
  --format json \
  --output /tmp/fridadev-real-main-prompt.json
```

Le mode `latest` choisit la conversation non supprimée la plus récemment mise à jour:

```bash
python3 app/scripts/export_main_prompt_payload.py latest \
  --output /tmp/fridadev-real-main-prompt.md
```

Sur OVH, l'hôte peut ne pas avoir les dépendances Python runtime (`psycopg`, accès DB). Dans ce cas, lancer le script dans le conteneur applicatif ou copier le script comme outil temporaire avec `FRIDA_APP_DIR=/app`.

Limite importante: le prompt historique exact n'est pas stocké en clair. Le mode réel reconstruit le chemin actuel depuis la DB et le code courant. Il ne rejoue pas les appels provider secondaires: Stimmung fraîche, `validation_agent` frais et contexte web live ne sont pas reproduits sans nouvel appel externe. La section `Limites de reconstruction` de l'export le rappelle explicitement.

Par défaut, le mode réel ne rejoue pas la retrieval mémoire pour éviter un appel embedding/provider. L'option `--include-current-memory` peut reconstruire les traces depuis l'état mémoire courant, mais elle peut appeler le provider d'embeddings configuré et ne garantit pas l'identité parfaite avec le tour historique.

## Sécurité d'export

Règles opératoires:

- ne jamais committer un export de conversation réelle;
- ne jamais committer une data URL image/PDF réelle;
- ne jamais afficher `Authorization`, token OpenRouter, `.env`, `api_key` ou secret runtime;
- les data URLs doivent être expurgées sous une forme du type `[redacted data URL: mime=image/png, chars=..., sha256_12=...]`;
- l'export synthétique actuel est destiné à comprendre la structure du prompt effectif, pas à auditer le contenu privé d'un tour.

## Lecture rapide

Pour relire ce que le modèle principal voit, partir du JSON `messages[]` généré et lire dans cet ordre:

1. le premier `system`: doctrine, temps, identité, jugement herméneutique, guards;
2. les `system` suivants: résumé, mémoire, indices contextuels;
3. la lane documentaire: contrat, documents injectés, exclusions;
4. les messages historiques user/assistant avec labels temporels;
5. le dernier `user`, éventuellement augmenté par le web;
6. les parties multimodales `image_url` / `file`, expurgées dans l'export mais présentes dans le payload réel quand autorisées.
