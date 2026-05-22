# FridaDev - raisonnement du LLM principal et streaming visuel du chat - TODO

Statut: actif
Date de creation: 2026-05-22
Classement: `app/docs/todo-todo/product/`
Nature: TODO source-of-truth A-Z, docs-only au moment de creation
Portee: LLM principal OpenRouter `openai/gpt-5.1`, runtime settings, admin, controle chat, payload, observabilite, UI de streaming visuel
Hors-scope du commit de creation: runtime, DB, migration, frontend, backend, tests applicatifs, changement de modele, rebuild

## 1. Intention

Ce TODO ouvre deux objets distincts mais proches dans l'experience de conversation:

1. ajouter un reglage avance borne du niveau de reasoning du LLM principal;
2. corriger le streaming visuel du texte assistant dans la fenetre de chat.

Le premier objet controle le niveau de raisonnement demande au modele principal. Le second objet rend la generation visible progressivement dans l'interface, quand le backend streame deja des chunks exploitables.

Ces deux chantiers ne doivent pas etre melanges dans un patch unique de runtime. Ils partagent seulement le fait qu'ils touchent l'appel principal `/api/chat` et l'experience de reponse.

## 2. Sources consultees avant creation

Docs officielles consultees:

- OpenAI GPT-5.1 model page: `https://platform.openai.com/docs/models/gpt-5.1/`
- OpenAI GPT-5.1 / GPT-5 guide retrouve via docs officielles: `https://platform.openai.com/docs/guides/gpt-5`
- OpenRouter Chat Completions: `https://openrouter.ai/docs/api-reference/chat-completion`
- OpenRouter Parameters: `https://openrouter.ai/docs/api-reference/parameters`
- OpenRouter Reasoning Tokens: `https://openrouter.ai/docs/guides/best-practices/reasoning-tokens`
- OpenRouter GPT-5.1 model API/endpoints publics: `https://openrouter.ai/api/v1/models/openai/gpt-5.1/endpoints`

Code FridaDev relu:

- `app/core/llm_client.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_service.py`
- `app/admin/runtime_settings.py`
- `app/admin/runtime_settings_spec.py`
- `app/admin/runtime_settings_validation.py`
- `app/web/app.js`
- `app/web/chat_streaming.js`
- `app/web/admin_section_main_model.js`
- `app/tests/unit/chat/test_chat_llm_flow.py`
- `app/tests/test_llm_client.py`
- `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`

Constats utiles:

- `llm_client.build_payload()` envoie aujourd'hui `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stop`, puis `metadata` / `trace`; en streaming il ajoute `stream=true` et `stream_options.include_usage=true`.
- Le LLM principal n'envoie actuellement aucun champ `reasoning`.
- OpenAI annonce pour GPT-5.1: `reasoning.effort` supporte `none` par defaut, `low`, `medium`, `high`.
- OpenRouter supporte un objet generique `reasoning`, mais sa liste generique est plus large que les niveaux GPT-5.1 officiellement annonces. Le lot d'implementation doit privilegier les niveaux modele-specifiques, pas inventer a partir d'une liste generique.
- OpenRouter documente des champs de sortie `reasoning` / `reasoning_details`; ce chantier interdit de les rendre visibles, de les persister en conversation visible ou de les injecter dans d'autres sous-systemes.
- Le frontend envoie deja `stream: true` a `/api/chat`, lit `ReadableStream`, parse un terminal de controle, et concatene des chunks dans `app/web/app.js`.
- L'archive `app/docs/todo-done/product/frida-response-streaming-todo.md` indique que certains modes plain text peuvent etre bufferises par la politique de sortie assistant; le diagnostic du nouvel objet streaming doit donc distinguer streaming technique et streaming reellement visible.

## 3. Doctrine commune

- Le modele principal reste `openai/gpt-5.1` tant qu'une decision separee ne change pas le modele.
- Le reglage reasoning controle un parametre de generation, pas une autorisation d'afficher le raisonnement interne.
- Le streaming visuel affiche uniquement le texte final destine a l'utilisateur, jamais un contenu de raisonnement cache.
- Les changements doivent rester bornes, observables, reversibles et testes.
- Les autres callers OpenRouter ne doivent pas etre contamines par le reglage du LLM principal: web discovery, web reformulation, arbiter, identity, summary, stimmung et validation gardent leurs contrats propres.

## 4. Contrainte dure - raisonnement non visible

Le reglage `reasoning` doit controler le niveau de raisonnement demande au modele, mais le raisonnement lui-meme ne doit jamais etre affiche a l'utilisateur.

Interdits:

- afficher une chaine de pensee;
- afficher des `reasoning_details`;
- streamer le raisonnement;
- stocker le raisonnement cache en conversation visible;
- injecter le raisonnement dans Memory, Identity, Summary, Biblio/RAG ou documents actifs;
- exposer le raisonnement dans les exports utilisateur;
- confondre niveau de reasoning et contenu du raisonnement.

Autorise:

- afficher le niveau selectionne, par exemple `raisonnement: aucun / faible / moyen / eleve`;
- journaliser de facon content-free le niveau utilise;
- observer cout, latence, tokens, modele, caller;
- garder une trace technique du parametre envoye, sans contenu de raisonnement.

Si OpenRouter / OpenAI renvoie des champs `reasoning`, `reasoning_details` ou equivalents, ils doivent etre ignores, ecartes ou explicitement filtres dans ce chantier, sauf decision future separee.

## 5. Objet 1 - Reglage reasoning du LLM principal

Objectif: rendre modulable le niveau de raisonnement du LLM principal GPT-5.1 via OpenRouter, de bout en bout.

### Lot 0 - Contrat et niveaux officiels

- [ ] Revalider la documentation officielle OpenAI GPT-5.1 et OpenRouter au moment du patch.
- [ ] Verifier les niveaux officiellement supportes pour `openai/gpt-5.1` via OpenRouter.
- [ ] Partir de la preuve actuelle: GPT-5.1 annonce `none`, `low`, `medium`, `high`.
- [ ] Ne pas ajouter `minimal`, `xhigh` ou tout autre niveau sauf preuve officielle GPT-5.1 via OpenRouter / OpenAI.
- [ ] Verifier la forme exacte attendue par OpenRouter Chat Completions: `reasoning: {"effort": value}` et option d'exclusion.
- [ ] Decider si le payload doit envoyer `reasoning.exclude=true` pour garantir que le raisonnement ne revient pas dans la reponse.
- [ ] Verifier la compatibilite avec `temperature` et `top_p`, notamment si GPT-5.1 impose des restrictions selon le niveau de reasoning.
- [ ] Definir le mapping UI francais:
  - `none` -> `aucun` ou `rapide`;
  - `low` -> `faible`;
  - `medium` -> `moyen`;
  - `high` -> `eleve`.
- [ ] Definir la valeur par defaut proposee pour FridaDev.
- [ ] Definir le comportement si le modele principal courant ne supporte pas reasoning: ne pas envoyer le champ, exposer un signal content-free, ne pas planter.
- [ ] Documenter que les niveaux generiques OpenRouter ne suffisent pas: le contrat actif est l'intersection modele-specifique.

### Lot 1 - DB / runtime settings

- [ ] Ajouter un champ runtime settings borne pour `main_model.reasoning_effort` ou nom equivalent.
- [ ] Choisir le type: enum stricte, pas texte libre.
- [ ] Prevoir migration / bootstrap si necessaire.
- [ ] Definir une valeur par defaut sure.
- [ ] Garantir compatibilite avec les settings existants `model`, `temperature`, `top_p`, `response_max_tokens`, headers et secrets.
- [ ] Ne pas stocker de secret.
- [ ] Ajouter validation backend: valeur absente, inconnue, modele incompatible.
- [ ] Verifier que les anciennes installations sans champ reasoning continuent a fonctionner.

### Lot 2 - Admin settings

- [ ] Exposer le champ dans les reglages avances du modele principal.
- [ ] Utiliser un controle borne: select/segmented control, pas JSON libre.
- [ ] Montrer la valeur active et sa source runtime.
- [ ] Indiquer clairement que le niveau controle l'effort demande, pas un affichage de pensee.
- [ ] Ajouter erreurs de validation lisibles si valeur inconnue.
- [ ] Conserver la gestion actuelle de `api_key` sans affichage de secret.
- [ ] Tester la sauvegarde, le reload et les erreurs.

### Lot 3 - Controle pres de la fenetre de chat

- [ ] Ajouter un controle accessible pres de la zone de saisie du chat.
- [ ] Proposer avant implementation le meilleur choix de portee:
  - global runtime;
  - conversation courante;
  - session navigateur;
  - prochain tour seulement.
- [ ] Recommandation initiale a evaluer: `prochain tour` ou `conversation courante`, pour eviter qu'un geste rapide modifie silencieusement le runtime global.
- [ ] Definir le libelle UI et les tooltips.
- [ ] Garder le controle compact et clair, par exemple `Raisonnement: moyen`.
- [ ] Afficher uniquement le niveau choisi, jamais le raisonnement interne.
- [ ] Decider la persistance UI: localStorage, meta conversation, parametre de requete ou runtime settings.
- [ ] Tester clavier, mobile, desktop et interaction avec web/manual/documents actifs.

### Lot 4 - Payload OpenRouter du LLM principal

- [ ] Brancher le reasoning dans le chemin du LLM principal uniquement.
- [ ] Revalider le meilleur emplacement exact: probablement `chat_service.py` pour resolution de valeur, puis `chat_llm_flow.py` / `llm_client.build_payload()` pour le payload.
- [ ] N'envoyer le champ `reasoning` que si la valeur est valide et applicable au modele courant.
- [ ] Envoyer une forme compatible OpenRouter, par exemple a verifier: `reasoning: {"effort": "medium", "exclude": true}`.
- [ ] Ne pas perturber `temperature`, `top_p`, `max_tokens`, `stop`, `metadata`, `trace`, `stream`, `stream_options.include_usage`.
- [ ] Si la documentation officielle confirme une incompatibilite entre certains niveaux de reasoning et `temperature` / `top_p`, ajouter une strategie explicite et testee au lieu de laisser une erreur provider opaque.
- [ ] Verifier que `reasoning_details` renvoyes en streaming ou non-streaming sont ignores / ecartes.
- [ ] Ne pas transmettre de raisonnement a Memory, Identity, Summary, Biblio/RAG, documents actifs ou exports.

### Lot 5 - Observabilite

- [ ] Journaliser content-free le niveau de reasoning demande.
- [ ] Journaliser le niveau effectivement envoye, ou `not_sent` si modele incompatible / valeur absente.
- [ ] Ajouter les champs utiles au read-model / checklist si pertinent:
  - `main_llm_reasoning_effort_requested`;
  - `main_llm_reasoning_effort_effective`;
  - `main_llm_reasoning_policy_kind`;
  - `main_llm_reasoning_hidden=true` ou equivalent.
- [ ] Ne jamais logger le contenu de raisonnement.
- [ ] Ne jamais stocker `reasoning_details`.
- [ ] Observer cout, latence, tokens, modele et caller via les surfaces deja existantes.
- [ ] Verifier que les exports utilisateur ne contiennent que le niveau selectionne, pas le raisonnement.

### Lot 6 - Tests

- [ ] Tests runtime settings: seed, migration, enum, valeur absente, valeur invalide.
- [ ] Tests admin settings: champ visible, sauvegarde, validation.
- [ ] Tests payload: aucun champ absent par defaut si contrat le decide, champ present si niveau choisi, champ absent si modele incompatible.
- [ ] Tests non-regression: `temperature`, `top_p`, `max_tokens`, `stream_options`, `metadata`, `trace` conserves.
- [ ] Tests de non-contamination: autres callers OpenRouter inchanges.
- [ ] Tests de filtrage: `reasoning`, `reasoning_details` ou equivalents provider ne sont ni affiches, ni persistes, ni injectes.
- [ ] Tests chat control si le controle pres du chat envoie un parametre de tour.
- [ ] Tests serveur runtime contract si `/api/chat` accepte une nouvelle option de tour.

### Lot 7 - Documentation / validation live

- [ ] Mettre a jour le catalogue des appels modeles.
- [ ] Mettre a jour la doc runtime/admin si comportement operateur nouveau.
- [ ] Documenter les niveaux retenus, la valeur par defaut, la portee du controle chat et les limites.
- [ ] Smoke test borne: un tour sans reasoning explicite, un tour `none`, un tour `medium` ou `high` selon cout acceptable.
- [ ] Verifier dans l'observabilite que le niveau est visible content-free.
- [ ] Verifier que le raisonnement interne n'apparait pas dans l'UI, les logs user-facing, Memory, Identity, Summary, exports ou documents actifs.
- [ ] Rebuild applicatif seulement quand le runtime/UI a ete modifie.
- [ ] Archiver le TODO quand tous les lots sont fermes.

## 6. Objet 2 - Streaming visuel du texte dans la fenetre de chat

Objectif: obtenir un affichage progressif reel du message assistant cote UI quand le backend fournit des chunks visibles.

### Lot 0 - Audit court du flux actuel

- [ ] Cartographier le chemin complet: OpenRouter stream -> `chat_llm_flow.event_stream()` -> `/api/chat` -> `fetch` -> `ReadableStream` -> parser frontend -> state thread -> rendu message.
- [ ] Distinguer streaming technique et streaming visible.
- [ ] Verifier quels modes sont bufferises par `assistant_output_contract.should_buffer_plain_text_stream()`.
- [ ] Identifier pourquoi l'utilisateur voit encore un bloc dans certains cas:
  - chunks provider eux-memes tardifs;
  - buffering backend pour plain text;
  - parser frontend;
  - store/thread hydration;
  - rendu DOM;
  - rechargement final qui remplace le message live.
- [ ] Ne pas supposer un bug frontend avant preuve.
- [ ] Relire l'archive `app/docs/todo-done/product/frida-response-streaming-todo.md` avant tout patch.

### Lot 1 - Contrat UX

- [ ] Le message assistant doit etre visible des les premiers tokens/chunks de contenu destines a l'utilisateur.
- [ ] Afficher un etat `reponse en cours` ou equivalent pendant la generation.
- [ ] Ne pas dupliquer le message final.
- [ ] Le contenu final persiste doit rester identique au texte affiche.
- [ ] En cas d'erreur ou d'interruption, conserver un statut clair et ne pas presenter un fragment comme reponse complete.
- [ ] Le comportement mobile et desktop doit rester propre.
- [ ] Les chunks de raisonnement ne doivent jamais etre rendus, meme si un futur payload reasoning les fait apparaitre cote provider.

### Lot 2 - Implementation frontend

- [ ] Adapter le store / reducer / composant message seulement apres l'audit.
- [ ] Concatener les chunks de contenu utilisateur-visible proprement.
- [ ] Eviter les reflows lourds: throttling leger si necessaire.
- [ ] Preserver byline, bouton de copie, export, thread sidebar, scroll et etats d'interruption.
- [ ] Ne pas remplacer le message live par une rehydratation qui annule l'effet progressif sauf necessite.
- [ ] Tester les cas long message, court message, erreur, interruption reseau.

### Lot 3 - Backend si necessaire

- [ ] Ne toucher au backend que si le streaming n'est pas deja exploitable par le frontend.
- [ ] Conserver les appels non-stream.
- [ ] Conserver `stream_options.include_usage` si utile.
- [ ] Conserver le protocole terminal existant ou documenter tout changement.
- [ ] Si le buffering plain text est la cause du bloc final, proposer explicitement une evolution de `assistant_output_contract` avant patch.
- [ ] Verifier que la normalisation de sortie assistant reste compatible avec le streaming visible.

### Lot 4 - Tests et validation

- [ ] Test unitaire frontend du state streaming si possible.
- [ ] Test integration frontend si l'infrastructure existante le permet.
- [ ] Test serveur streaming si le backend est modifie.
- [ ] Test manuel navigateur: long message visible progressivement.
- [ ] Test manuel navigateur: message court propre.
- [ ] Test erreur/interruption.
- [ ] Verifier l'absence de raisonnement rendu, stocke ou exporte.
- [ ] Rebuild applicatif seulement si runtime/UI modifie.

## 7. Decisions utilisateur a prendre avant implementation

- [ ] Niveaux exacts de reasoning valides apres relecture finale des docs officielles.
- [ ] Valeur par defaut du reasoning FridaDev.
- [ ] Portee du controle chat: global, conversation, session ou prochain tour.
- [ ] Libelles UI francais definitifs.
- [ ] Emplacement precis du controle dans la fenetre de chat.
- [ ] Strategie si `temperature` / `top_p` deviennent incompatibles avec certains niveaux de reasoning.
- [ ] Comportement si le modele principal n'est plus GPT-5.1 ou ne supporte pas reasoning.
- [ ] Niveau de tests visuels attendu pour le streaming.
- [ ] Comportement streaming en cas d'interruption.

## 8. Hors-scope global

- Ne pas implementer dans le commit de creation de ce TODO.
- Ne pas modifier runtime, DB, UI ou backend sans lot dedie.
- Ne pas changer le modele principal.
- Ne pas toucher au web search.
- Ne pas ajouter de provider routing, tools, response_format, penalties, seed ou autres reglages OpenRouter non demandes.
- Ne jamais rendre visible le raisonnement interne du modele.
- Ne pas streamer, stocker, persister, exporter ou injecter de `reasoning_details`.
- Ne pas ouvrir le chantier `reasoning conversationnel conserve`: c'est un chantier futur separe.
- Ne pas injecter le raisonnement dans Memory, Identity, Summary, Biblio/RAG ou documents actifs.
- Ne pas afficher secret, `.env`, token, DSN, cookie ou header sensible.

## 9. Criteres de cloture

Le chantier pourra etre clos seulement si:

- les niveaux reasoning officiellement retenus sont documentes;
- le champ runtime settings existe et est migre / seed proprement;
- l'admin expose le reglage de facon bornee;
- le controle chat existe avec une portee decidee;
- le payload OpenRouter envoie le niveau correct au LLM principal seulement;
- l'observabilite montre le niveau de reasoning sans contenu de raisonnement;
- les champs provider `reasoning` / `reasoning_details` sont ignores ou filtres;
- le streaming visuel affiche vraiment les chunks utilisateur-visibles quand ils existent;
- les erreurs/interruption restent propres;
- les tests runtime, frontend et docs sont passes;
- aucune contamination Memory / Identity / Summary / Biblio/RAG / documents actifs / exports n'est observee;
- une validation live bornee est documentee;
- le TODO est archive dans `app/docs/todo-done/product/`.
