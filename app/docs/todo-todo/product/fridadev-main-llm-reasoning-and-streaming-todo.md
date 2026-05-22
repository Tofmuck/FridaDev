# FridaDev - raisonnement du LLM principal et streaming visuel du chat - TODO

Statut: livre en runtime applicatif; archive documentaire a faire dans un lot separe si souhaite
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

Decision utilisateur post-creation:

- le niveau de reasoning du LLM principal est un reglage global runtime settings / DB;
- le controle pres de la fenetre de chat est un raccourci ergonomique vers ce reglage global;
- changer ce controle modifie le defaut global des prochains tours;
- la valeur par defaut cible doit pouvoir etre `high`, sous reserve de confirmation au lot d'implementation;
- un override par conversation ou par tour pourra etre etudie plus tard, mais il est hors scope de ce chantier.

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
- Le niveau reasoning du LLM principal est global par defaut: runtime settings / DB est la source de verite.
- Le controle chat est un raccourci ergonomique vers ce reglage global, pas un override local.

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

### Livraison Objet 1 - 2026-05-22

Statut: livre en runtime applicatif.

- [x] Niveaux GPT-5.1 revalides et bornes a `none`, `low`, `medium`, `high`.
- [x] Reglage global `main_model.reasoning_effort` ajoute aux runtime settings / DB avec defaut `high`.
- [x] Controle admin borne ajoute au modele principal.
- [x] Controle compact pres du chat ajoute comme raccourci vers le reglage global, applicable aux prochains tours.
- [x] Payload OpenRouter du LLM principal branche via `reasoning.effort` avec exclusion du raisonnement detaille.
- [x] Observabilite content-free du niveau demande/effectif ajoutee aux evenements LLM principaux.
- [x] Garde-fou documente: niveau visible, contenu interne du raisonnement jamais affiche, streame, persiste, exporte ou injecte.
- [x] Tests settings, payload, frontend contract, controle chat et observabilite ajoutes ou adaptes.
- [x] Smoke live borne OpenRouter effectue sur `high`, `none`, `medium`; pas d'incompatibilite `temperature` / `top_p` observee.
- [x] Correctif post-smoke: filtrage explicite des champs provider `reasoning` / `reasoning_details` au read path.

Les cases detaillees ci-dessous conservent le plan A-Z initial. Pour l'objet 1, le statut effectif est porte par le bloc de livraison ci-dessus et par la spec `app/docs/states/specs/fridadev-main-llm-reasoning-contract.md`.

### Lot 0 - Contrat et niveaux officiels

- [x] Revalider la documentation officielle OpenAI GPT-5.1 et OpenRouter au moment du patch.
- [x] Verifier les niveaux officiellement supportes pour `openai/gpt-5.1` via OpenRouter.
- [x] Partir de la preuve actuelle: GPT-5.1 annonce `none`, `low`, `medium`, `high`.
- [x] Ne pas ajouter `minimal`, `xhigh` ou tout autre niveau sauf preuve officielle GPT-5.1 via OpenRouter / OpenAI.
- [x] Verifier la forme exacte attendue par OpenRouter Chat Completions: `reasoning: {"effort": value}` et option d'exclusion.
- [x] Decider si le payload doit envoyer `reasoning.exclude=true`; le smoke live a montre que le provider peut encore renvoyer `reasoning_details`, donc FridaDev filtre aussi cote read path.
- [x] Verifier la compatibilite avec `temperature` et `top_p`, notamment si GPT-5.1 impose des restrictions selon le niveau de reasoning.
- [x] Definir le mapping UI francais:
  - `none` -> `aucun` ou `rapide`;
  - `low` -> `faible`;
  - `medium` -> `moyen`;
  - `high` -> `eleve`.
- [x] Confirmer la valeur par defaut cible pour FridaDev: `high`.
- [x] Definir le comportement si le modele principal courant ne supporte pas reasoning: ne pas envoyer le champ, exposer un signal content-free, ne pas planter.
- [x] Documenter que les niveaux generiques OpenRouter ne suffisent pas: le contrat actif est l'intersection modele-specifique.

### Lot 1 - DB / runtime settings

- [x] Ajouter un champ runtime settings borne pour `main_model.reasoning_effort`.
- [x] Choisir le type: texte valide par liste fermee cote serveur, pas JSON libre.
- [x] Prevoir bootstrap/backfill DB pour les installations existantes.
- [x] Definir une valeur par defaut sure: `high`.
- [x] Garantir compatibilite avec les settings existants `model`, `temperature`, `top_p`, `response_max_tokens`, headers et secrets.
- [x] Ne pas stocker de secret.
- [x] Ajouter validation backend: valeur absente, inconnue, modele incompatible.
- [x] Verifier que les anciennes installations sans champ reasoning continuent a fonctionner.

### Lot 2 - Admin settings

- [x] Exposer le champ dans les reglages avances du modele principal.
- [x] Utiliser un controle borne: select, pas JSON libre.
- [x] Montrer la valeur active et sa source runtime via le mecanisme admin existant.
- [x] Indiquer clairement que le niveau controle l'effort demande, pas un affichage de pensee.
- [x] Ajouter erreurs de validation lisibles si valeur inconnue.
- [x] Conserver la gestion actuelle de `api_key` sans affichage de secret.
- [x] Tester la sauvegarde, le reload et les erreurs via contrats admin/runtime.

### Lot 3 - Controle pres de la fenetre de chat

- [x] Ajouter un controle accessible pres de la zone de saisie du chat.
- [x] Acter la portee: le controle modifie le reglage global `main_model.reasoning_effort` en runtime settings / DB.
- [x] Traiter ce controle comme un raccourci ergonomique vers les settings globaux, pas comme un override de tour, session ou conversation.
- [x] Quand l'utilisateur change ce controle, appliquer la nouvelle valeur comme defaut global des prochains tours.
- [x] Definir le libelle UI et le titre compact.
- [x] Garder le controle compact et clair.
- [x] Afficher uniquement le niveau choisi, jamais le raisonnement interne.
- [x] Persister par runtime settings / DB, avec retour UI clair sur la valeur active.
- [x] Garder les overrides conversation ou prochain tour hors scope; ils pourront devenir un chantier futur separe si le besoin est confirme.
- [x] Tester le contrat frontend chat/admin; validation visuelle navigateur approfondie hors de ce lot.

### Lot 4 - Payload OpenRouter du LLM principal

- [x] Brancher le reasoning dans le chemin du LLM principal uniquement.
- [x] Revalider le meilleur emplacement exact: resolution dans `llm_client.build_payload()` depuis runtime settings, observabilite dans `chat_llm_flow.py` / proxy serveur.
- [x] N'envoyer le champ `reasoning` que si la valeur est valide et applicable au modele courant.
- [x] Envoyer une forme compatible OpenRouter: `reasoning: {"effort": "medium", "exclude": true}`.
- [x] Ne pas perturber `temperature`, `top_p`, `max_tokens`, `stop`, `metadata`, `trace`, `stream`, `stream_options.include_usage`.
- [x] Aucune incompatibilite officielle bloquante `temperature` / `top_p` n'a ete confirmee pour ce lot.
- [x] Verifier que `reasoning_details` renvoyes en streaming ou non-streaming sont ignores / ecartes; un smoke live a confirme la presence possible de la cle en JSON provider.
- [x] Ne pas transmettre de raisonnement a Memory, Identity, Summary, Biblio/RAG, documents actifs ou exports.

### Lot 5 - Observabilite

- [x] Journaliser content-free le niveau de reasoning demande.
- [x] Journaliser le niveau effectivement envoye, ou `not_sent` si modele incompatible / valeur absente.
- [x] Ajouter les champs utiles aux evenements LLM principaux:
  - `main_llm_reasoning_effort_requested`;
  - `main_llm_reasoning_effort_effective`;
  - `main_llm_reasoning_policy_kind`;
  - `main_llm_reasoning_hidden=true` ou equivalent.
- [x] Ne jamais logger le contenu de raisonnement.
- [x] Ne jamais stocker `reasoning_details`; filtrage explicite dans `llm_client.read_openrouter_response_payload()`.
- [x] Observer cout, latence, tokens, modele et caller via les surfaces deja existantes.
- [x] Verifier que les exports utilisateur ne contiennent que le niveau selectionne, pas le raisonnement.

### Lot 6 - Tests

- [x] Tests runtime settings: seed, bootstrap/backfill, valeur absente, valeur invalide.
- [x] Tests admin settings: champ visible, sauvegarde, validation.
- [x] Tests payload: champ present par defaut compatible, champ present si niveau choisi, champ absent si modele incompatible.
- [x] Tests non-regression: `temperature`, `top_p`, `max_tokens`, `stream_options`, `metadata`, `trace` conserves.
- [x] Tests de non-contamination: autres callers OpenRouter inchanges.
- [x] Tests de filtrage: `reasoning`, `reasoning_details` ou equivalents provider ne sont ni affiches, ni persistes, ni injectes.
- [x] Tests chat control: le controle pres du chat modifie le reglage global et n'envoie pas de parametre de tour.
- [x] Tests serveur runtime contract: `/api/chat` ne recoit pas de nouvelle option de tour.

### Lot 7 - Documentation / validation live

- [x] Mettre a jour le catalogue des appels modeles.
- [x] Mettre a jour la doc runtime/admin si comportement operateur nouveau.
- [x] Documenter les niveaux retenus, la valeur par defaut, la portee du controle chat et les limites.
- [x] Smoke test borne: `high`, `none`, `medium` avec appel OpenRouter reel; controle budget supplementaire `high` / `medium` a `max_tokens=64`.
- [x] Verifier dans l'observabilite que le niveau est visible content-free.
- [x] Verifier que le raisonnement interne n'apparait pas dans l'UI, les logs user-facing, Memory, Identity, Summary, exports ou documents actifs.
- [x] Rebuild applicatif seulement quand le runtime/UI a ete modifie.
- [ ] Archiver le TODO quand tous les lots sont fermes.

## 6. Objet 2 - Streaming visuel du texte dans la fenetre de chat

Objectif: obtenir un affichage progressif reel du message assistant cote UI quand le backend fournit des chunks visibles.

Statut 2026-05-22: livre en runtime applicatif. Le point de buffering etait le buffering plain text de `chat_llm_flow` / `assistant_output_contract`, pas le `ReadableStream` frontend. Le backend diffuse maintenant un brouillon visible normalise au fil de l'eau et le terminal `done` peut porter `final_text` quand le texte canonique final doit remplacer ce brouillon. `final_text` est du texte assistant final visible, jamais du raisonnement interne.

### Lot 0 - Audit court du flux actuel

- [x] Cartographier le chemin complet: OpenRouter stream -> `chat_llm_flow.event_stream()` -> `/api/chat` -> `fetch` -> `ReadableStream` -> parser frontend -> state thread -> rendu message.
- [x] Distinguer streaming technique et streaming visible.
- [x] Verifier quels modes sont bufferises par `assistant_output_contract.should_buffer_plain_text_stream()`.
- [x] Identifier pourquoi l'utilisateur voit encore un bloc dans certains cas:
  - chunks provider eux-memes tardifs;
  - buffering backend pour plain text;
  - parser frontend;
  - store/thread hydration;
  - rendu DOM;
  - rechargement final qui remplace le message live.
- [x] Ne pas supposer un bug frontend avant preuve.
- [x] Relire l'archive `app/docs/todo-done/product/frida-response-streaming-todo.md` avant tout patch.

### Lot 1 - Contrat UX

- [x] Le message assistant doit etre visible des les premiers tokens/chunks de contenu destines a l'utilisateur.
- [x] Afficher un etat `reponse en cours` ou equivalent pendant la generation.
- [x] Ne pas dupliquer le message final.
- [x] Le contenu final persiste doit rester identique au texte affiche.
- [x] En cas d'erreur ou d'interruption, conserver un statut clair et ne pas presenter un fragment comme reponse complete.
- [x] Le comportement mobile et desktop doit rester propre.
- [x] Les chunks de raisonnement ne doivent jamais etre rendus, meme si un futur payload reasoning les fait apparaitre cote provider.

### Lot 2 - Implementation frontend

- [x] Adapter le store / reducer / composant message seulement apres l'audit.
- [x] Concatener les chunks de contenu utilisateur-visible proprement.
- [x] Eviter les reflows lourds: pas de nouveau throttling necessaire; le scroll ne colle au bas que si l'utilisateur est deja proche du bas.
- [x] Preserver byline, bouton de copie, export, thread sidebar, scroll et etats d'interruption.
- [x] Ne pas remplacer le message live par une rehydratation qui annule l'effet progressif sauf necessite.
- [x] Tester les cas long message, court message, erreur, interruption reseau.

### Lot 3 - Backend si necessaire

- [x] Ne toucher au backend que si le streaming n'est pas deja exploitable par le frontend.
- [x] Conserver les appels non-stream.
- [x] Conserver `stream_options.include_usage` si utile.
- [x] Conserver le protocole terminal existant ou documenter tout changement.
- [x] Si le buffering plain text est la cause du bloc final, proposer explicitement une evolution de `assistant_output_contract` avant patch.
- [x] Verifier que la normalisation de sortie assistant reste compatible avec le streaming visible.

### Lot 4 - Tests et validation

- [x] Test unitaire frontend du state streaming si possible.
- [x] Test integration frontend si l'infrastructure existante le permet.
- [x] Test serveur streaming si le backend est modifie.
- [x] Test navigateur/harness: long message visible progressivement.
- [x] Test navigateur/harness: message court propre.
- [x] Test erreur/interruption.
- [x] Verifier l'absence de raisonnement rendu, stocke ou exporte.
- [x] Rebuild applicatif seulement si runtime/UI modifie.

## 7. Decisions utilisateur a prendre avant implementation

- [x] Niveaux exacts de reasoning valides apres relecture finale des docs officielles: `none`, `low`, `medium`, `high`.
- [x] Valeur par defaut du reasoning FridaDev: `high`.
- [x] Libelles UI francais definitifs pour l'objet 1: `aucun`, `faible`, `moyen`, `eleve`.
- [x] Emplacement precis du controle dans la fenetre de chat: pres de la zone de saisie, comme raccourci global compact.
- [x] Strategie si `temperature` / `top_p` deviennent incompatibles avec certains niveaux de reasoning: smoke live 2026-05-22 OK, conserver les champs; reouvrir seulement sur erreur provider prouvee.
- [x] Comportement si le modele principal n'est plus GPT-5.1 ou ne supporte pas reasoning: ne pas envoyer le champ, exposer un signal content-free, ne pas planter.
- [x] Niveau de tests visuels attendu pour le streaming: tests unitaires parser/state, tests serveur, validation Playwright/harness et verification live app.
- [x] Comportement streaming en cas d'interruption: terminal `error` ou erreur reseau conserve le statut interrompu et ne canonise pas le fragment visible.

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
