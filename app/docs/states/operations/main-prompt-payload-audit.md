# Export du prompt effectif du modèle principal

Ce document cartographie ce qui agit réellement comme prompt du modèle principal FridaDev au moment d'un appel `/api/chat`.

Il distingue trois niveaux:

- **prompts sources**: fichiers texte et doctrines de base;
- **blocs runtime dérivés**: temps, identité, mémoire, web, jugement herméneutique, guards;
- **payload effectif**: `messages[]` et paramètres envoyés à OpenRouter pour `FridaDev / Main Chat`.

Le prompt effectif n'est donc pas seulement `app/prompts/*.txt`: c'est le résultat ordonné du pipeline de chat, des sélections documentaires et des garde-fous injectés au tour.

## Ordre du pipeline effectif

| Ordre | Source | Responsable | Condition | Forme finale OpenRouter | Contenu / persistance |
| --- | --- | --- | --- | --- | --- |
| 1 | Requête utilisateur et conversation courante | `app/core/chat_service.py::chat_response` | Toujours | Le message utilisateur est ajouté à la conversation avant construction du prompt | Contient le texte utilisateur; persisté comme message de conversation après le tour |
| 2 | Prompts sources | `app/core/chat_prompt_context.py::resolve_backend_prompts`, `app/prompts/main_system.txt`, `app/prompts/main_hermeneutical.txt` | Toujours | Premier message `role=system` après augmentation | Source stable du dépôt; pas du contenu utilisateur |
| 3 | Bloc temps `NOW` / timezone | `app/core/chat_prompt_context.py::build_augmented_system`, `app/core/hermeneutic_node/inputs/time_input.py` | Toujours | Ajouté au message `system` principal | Runtime content-free; Frida reçoit une référence temporelle, elle ne "sent" pas le temps |
| 4 | Identité | `app/core/chat_prompt_context.py::build_augmented_system`, module `identity` injecté par `chat_service` | Toujours si bloc identité disponible | Ajoutée au message `system` principal | Contient identité statique/mutable sélectionnée; issue du stockage identité, pas du tour brut |
| 5 | Résumé conversationnel potentiel | `app/memory/summarizer.py::maybe_summarize`, puis `app/core/conversations_prompt_window.py::build_prompt_messages` | Si un résumé actif existe après éventuelle mise à jour | Message séparé `role=system` | Contient résumé conversationnel persisté; le prompt n'inclut que le résumé actif utile |
| 6 | Mémoire et context hints | `app/core/chat_memory_flow.py::prepare_memory_context`, puis `conversations_prompt_window` | Selon mode mémoire et arbitrage | Messages `role=system`: indices, résumés parents, souvenirs retenus | Contient traces mémoire sélectionnées; les traces rejetées ne sont pas injectées |
| 7 | Inputs du tour pour le noeud herméneutique | `app/core/chat_turn_runtime_inputs.py`, `app/core/stimmung_agent.py`, `app/core/hermeneutic_node/*` | Toujours, avec données disponibles | Pas injectés directement sauf verdict final validé | Stimmung et inputs servent au cadrage local du tour; ce ne sont pas une psychologie durable |
| 8 | Jugement herméneutique final | `app/core/chat_service.py::_run_hermeneutic_node_insertion_point`, `app/core/chat_prompt_context.py::build_hermeneutic_judgment_block` | Si le noeud produit des directives validées | Ajouté au message `system` principal | Content-free ou quasi content-free; cadre la posture, ne rédige pas la réponse |
| 9 | Guards runtime | `app/core/chat_prompt_context.py` | Conditionnels sauf guard texte selon contrat | Ajoutés au message `system` principal | Voice transcription, révélation identitaire directe, web read-state, réponse texte simple |
| 10 | Fenêtre conversationnelle | `app/core/conversations_prompt_window.py::build_prompt_messages` | Toujours | Messages `role=user`, `role=assistant`, parfois `role=system` pour silences | Contient l'historique retenu après résumé actif; labels Delta-T et silences sont ajoutés runtime |
| 11 | Contexte web | `app/core/chat_prompt_context.py::inject_web_context` | Web manuel/auto avec `context_block` | Préfixé dans le dernier message `role=user` | Contient extraits web sélectionnés; runtime du tour, pas mémoire par défaut |
| 12 | Documents actifs de conversation | `app/core/active_conversation_documents.py`, `app/core/active_document_prompt_lane.py` | Documents actifs présents et lisibles | Lane insérée avant le premier message de dialogue: `system` de contrat puis `user` documentaire | Peut contenir texte documentaire complet; non persisté dans l'historique comme nouveau message utilisateur |
| 13 | Fichiers workspace sélectionnés | `app/core/workspace_file_selection_prompt.py`, `active_document_prompt_lane.py` | Fichier explicitement coché dans la conversation | Même lane que les documents actifs | Conversation-scoped; texte/image/PDF seulement si sélectionné; pas Biblio, pas mémoire, pas RAG |
| 14 | Images et PDF multimodaux | `active_document_prompt_lane.py::_multimodal_content` | Modèle compatible, bytes disponibles, plafond provider respecté | Message `role=user` avec `content[]`: `text` puis `image_url` ou `file` | Les bytes sont envoyés au provider comme data URL dans le payload; logs/export doivent les expurger |
| 15 | Paramètres OpenRouter | `app/core/llm_client.py::build_payload`, `app/core/llm_client.py::with_provider_attribution` | Toujours | Champs `model`, `temperature`, `top_p`, `max_tokens`, `stop`, `stream`, `metadata`, `trace` | Pas des messages de prompt, mais ils influencent l'appel et l'observabilité OpenRouter |

## Ce qui n'est pas directement injecté

Ces éléments peuvent influencer le pipeline, mais ne deviennent pas automatiquement du texte vu par le modèle principal:

- le prompt interne du `stimmung_agent`;
- les sorties brutes du primary hermeneutic node et du `validation_agent`, sauf le jugement final synthétisé;
- les traces mémoire candidates rejetées;
- les prompts du summarizer, de l'identity extractor et de l'identity periodic agent;
- les prompts/outils de recherche web avant synthèse du `context_block`;
- les fichiers workspace non cochés;
- les documents exclus pour taille, type, modèle incompatible, disque absent ou OCR requis;
- les descriptions de répertoire de travail, qui restent UI-only;
- la Biblio/RAG, sauf chantier séparé explicitement branché.

## Outil local d'export synthétique

Le script `app/scripts/export_main_prompt_payload.py` sait produire deux types d'artefacts:

- un export synthétique non sensible;
- un export local d'une conversation réelle, expurgé, non committé.

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
