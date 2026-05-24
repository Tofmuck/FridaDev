# FridaDev - jobs divers produit - TODO

Statut: objets 1 et 2 livres en runtime applicatif; objet 3 dictee Whisper longue corrige cote applicatif et cloture provisoirement sous surveillance apres validation live navigateur 99 s; objet 4 repertoires de travail fermes par defaut livre; objet 5 composer actions en grille droite livre; objet 6 animation des statuts Whisper livre; objet 7 loader assistant anime livre; objet 8 memoire/intention de Frida ajoute en cadrage docs-only, non lance runtime
Date de creation: 2026-05-22
Classement: `app/docs/todo-todo/product/`
Nature: TODO source-of-truth pour jobs produit courts et bornes, docs-only au moment de creation
Portee: LLM principal OpenRouter `openai/gpt-5.1`, runtime settings, admin, controle chat, payload, observabilite, UI de streaming visuel, dictee Whisper locale longue, polish UI des repertoires de travail, ergonomie du composer de chat, retour visuel actif de la dictee Whisper, loader assistant anime, cadrage memoire/intention `feed her from herself`
Hors-scope du commit de creation: runtime, DB, migration, frontend, backend, tests applicatifs, changement de modele, rebuild

## 1. Intention

Ce TODO rassemble des jobs produit courts qui doivent rester bornes, testables et reversibles, sans perdre l'historique des objets deja livres.

Il a d'abord ouvert trois objets distincts mais proches dans l'experience de conversation:

1. ajouter un reglage avance borne du niveau de reasoning du LLM principal;
2. corriger le streaming visuel du texte assistant dans la fenetre de chat;
3. diagnostiquer et corriger la dictee Whisper locale longue, cible minimum 2 minutes.

Depuis le renommage du 2026-05-23, il sert aussi de TODO general pour petits jobs produit explicites:

4. fermer les repertoires de travail par defaut au chargement initial, sans casser l'ouverture manuelle ni l'etat actif des conversations/fichiers.
5. ranger les actions du composer en grille compacte a droite de la zone de saisie, avec le bouton envoyer prioritaire.
6. animer discretement les statuts actifs Whisper pendant l'enregistrement et la transcription.
7. animer le loader assistant avec le meme langage visuel que Whisper.
8. retenir le chantier memoire/intention `feed her from herself`: Frida ne doit pas promettre de retenir ou de vouloir durablement si aucune couche mutable/persistante/reinjectable ne porte cette promesse.

Le premier objet controle le niveau de raisonnement demande au modele principal. Le second objet rend la generation visible progressivement dans l'interface, quand le backend streame deja des chunks exploitables.
Le troisieme objet vise la capture vocale locale: la dictee ne doit pas s'interrompre prematurement au bout de 20 a 40 secondes, et doit rester fiable sur une cible produit d'au moins 2 minutes.
Le quatrieme objet est un polish UI des repertoires de travail: les dossiers doivent demarrer replies, puis rester ouvrables a la demande pendant la session.
Le cinquieme objet est un polish UI du composer: les actions ne doivent plus s'etirer en ligne horizontale sous la saisie, mais former un bloc droit compact et stable.
Le sixieme objet est un polish du retour Whisper: les statuts actifs doivent montrer une activite en cours sans bruit visuel ni changement backend.
Le septieme objet aligne le loader assistant du chat sur ce meme langage visuel, sans changer le protocole streaming.
Le huitieme objet est seulement un cadrage docs-only: il ne lance pas encore de patch runtime, mais evite de perdre le sujet des fausses promesses de memoire/intention et renvoie au TODO memoire `app/docs/todo-todo/memory/Frida_from_herself.md`.

Ces chantiers ne doivent pas etre melanges dans un patch unique de runtime. Ils partagent seulement le fait qu'ils touchent l'experience de conversation. Les objets 1 et 2 sont livres; l'objet 3 est clos provisoirement sous surveillance; l'objet 4 est livre comme petit lot UI/docs; l'objet 5 est livre comme petit lot ergonomie frontend/docs; l'objet 6 est livre comme petit lot frontend/docs; l'objet 7 est livre comme petit lot frontend/docs; l'objet 8 reste a cadrer avant toute implementation.

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
- `app/web/whisper/whisper_dictation.js`
- `app/server.py`
- `app/core/whisper_transcription_service.py`
- `app/config.py`
- `app/tests/unit/chat/test_chat_llm_flow.py`
- `app/tests/test_llm_client.py`
- `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`
- `app/tests/unit/frontend_chat/test_whisper_dictation_module.js`
- `app/tests/unit/chat/test_whisper_transcription_service.py`
- `app/tests/integration/chat/test_chat_transcription_route.py`
- `app/tests/integration/frontend_chat/test_frontend_whisper_contract.py`
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`
- `app/docs/todo-done/notes/whisper-transcription-indisponible-diagnostic-2026-05-05.md`

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
- Diagnostic Objet 3, 2026-05-22: `app/web/whisper/whisper_dictation.js` imposait `DEFAULT_MAX_RECORDING_MS = 60_000` et arretait automatiquement `MediaRecorder` via `recorder.stop()`. Ce plafond rendait la cible 2 minutes impossible.
- Correctif Objet 3, 2026-05-23: `DEFAULT_MAX_RECORDING_MS` et la borne client sont passes a `150_000`, pour couvrir une cible reelle de 120 s avec marge.
- Diagnostic Objet 3, 2026-05-22: le frontend n'utilisait pas de `timeslice` dans `recorder.start()`, donc il accumulait un blob unique jusqu'a l'arret. Le correctif initial conserve ce blob unique, mais le rend observable par duree/taille/raison/chunks sans contenu.
- Diagnostic Objet 3, 2026-05-22: aucune detection de silence, de `blur`, de changement de thread ou de busy state qui stopperait explicitement un enregistrement actif n'a ete trouvee dans le code relu.
- Diagnostic Objet 3, 2026-05-22: `/api/chat/transcribe` ne porte pas de limite de duree explicite; `whisper_transcription_service` lit le fichier complet en memoire et poste vers `WHISPER_API_URL`. Le timeout applicatif par defaut est passe de `WHISPER_API_TIMEOUT_S=120` a `180` pour laisser une marge a 2 minutes d'audio.
- Diagnostic Objet 3, 2026-05-22: l'ancien diagnostic `whisper-transcription-indisponible-diagnostic-2026-05-05.md` a observe un `exit code -9` et un conteneur Whisper aval `oom_killed=true`; les longs blobs peuvent donc reveiller une limite ressources cote service local.

## 3. Doctrine commune

- Le modele principal reste `openai/gpt-5.1` tant qu'une decision separee ne change pas le modele.
- Le reglage reasoning controle un parametre de generation, pas une autorisation d'afficher le raisonnement interne.
- Le streaming visuel affiche uniquement le texte final destine a l'utilisateur, jamais un contenu de raisonnement cache.
- La dictee Whisper locale ne doit jamais logger d'audio brut ni de transcription sensible; les diagnostics doivent rester content-free: duree, taille, raison d'arret, statut et erreur bornee.
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

- afficher le niveau selectionne, par exemple `raisonnement: aucun / faible / moyen / élevé`;
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
  - `high` -> `élevé`.
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
- [x] Archivage global differe: conserver ce TODO dans `todo-todo` tant que l'Objet 3 reste en cloture provisoire sous surveillance; archiver seulement apres decision explicite de fermeture globale.

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

## 7. Objet 3 - Dictee Whisper longue

Objectif: permettre une dictee Whisper locale fluide d'au moins 2 minutes, sans rupture prematuree, sans perte du brouillon texte existant, avec une decision explicite si le produit doit retenir temporairement l'audio pour retry, et sans log d'audio brut ou de transcription sensible.

### Diagnostic lecture seule - 2026-05-22

Symptome utilisateur: la dictee demarre, puis s'arrete seule apres environ 20, 30 ou 40 secondes. Ce comportement casse le flux de parole et bloque l'usage naturel.

Constats confirmes par lecture:

- [x] Le frontend possedait un plafond dur: `DEFAULT_MAX_RECORDING_MS = 60_000` dans `app/web/whisper/whisper_dictation.js`.
- [x] Ce plafond declenchait un arret automatique par `recorder.stop()` via `setTimeout`.
- [x] La cible produit 2 minutes etait donc impossible sans changement frontend, meme si le backend et Whisper aval fonctionnaient parfaitement.
- [x] `MediaRecorder.start()` est appele sans `timeslice`; le code accumule un blob unique dans `pendingChunks` puis l'envoie en une seule fois a `/api/chat/transcribe`.
- [x] Aucun arret automatique par silence n'a ete trouve dans le frontend.
- [x] Aucun arret automatique par `blur`, changement de thread, submit chat ou busy state n'a ete trouve pour un enregistrement deja actif.
- [x] Le bouton micro est desactive quand une requete chat est deja en cours, mais ce signal ne semble pas stopper une capture deja lancee.
- [x] `/api/chat/transcribe` delegue a `whisper_transcription_service.transcribe_http_request()` sans limite explicite de duree.
- [x] `whisper_transcription_service.prepare_upload()` lit le fichier complet en memoire.
- [x] Le timeout applicatif Whisper etait `WHISPER_API_TIMEOUT_S=120`; cela concernait surtout la transcription apres arret, pas l'arret de capture lui-meme.
- [x] L'ancien diagnostic du 2026-05-05 a deja observe `platform-whisper-api` en echec `exit code -9` avec indice OOM; cela reste une hypothese serieuse pour les longs blobs ou les transcriptions longues.

Hypotheses classees:

1. Cause certaine pour la cible 2 minutes: plafond frontend `60_000 ms`. Ce point rend 120 secondes impossibles, mais n'explique pas a lui seul un arret de capture a 20-40 secondes.
2. Risque confirme par lecture pour les longues durees: absence de `timeslice`, blob final unique, lecture complete en memoire par `prepare_upload()`, puis POST complet vers le service aval. Ce risque concerne la stabilite navigateur, l'upload et la transcription; il ne doit pas etre masque par une simple hausse du plafond.
3. Cause serieuse pour les echecs de transcription apres arret: pression ressource du service Whisper local, deja observee le 2026-05-05 via `exit code -9` et `oom_killed=true`. Cette preuve porte sur le service aval, pas sur un arret premature de `MediaRecorder`.
4. Cause possible pour un arret de capture avant 60 secondes: erreur `MediaRecorder`, piste micro terminee, comportement navigateur/device ou pression memoire client. Le code ne l'observe pas encore assez finement.
5. Cause possible mais secondaire: timeout backend `120 s` trop court pour un audio de 2 minutes selon modele, CPU et charge; il devrait produire une erreur transcription, pas stopper la capture.
6. Causes non etayees par lecture: detection de silence, arret sur blur, arret sur busy state apres demarrage, limite client explicite de taille blob.

La reproduction doit donc separer trois phenomenes au lieu de les fusionner:

- capture interrompue avant la limite attendue;
- capture complete mais upload ou transcription en echec;
- transcription reussie ou echouee mais brouillon UI perdu, remplace ou mal signale.

### Livraison Objet 3 - 2026-05-23

Statut: correctif applicatif livre; cloture provisoire sous surveillance; pas de modification Docker/ressources ni de changement modele Whisper.

- [x] Plafond client remplace par une limite bornee a `150_000 ms`.
- [x] Raisons d'arret explicites: `manual`, `auto_limit`, `recorder_error`, `track_ended`, `unknown`.
- [x] Arret volontaire conserve et distingue de l'arret par limite.
- [x] Pas d'arret ajoute sur silence, blur, busy state ou changement de thread.
- [x] Blob unique conserve pour le premier patch; `MediaRecorder.start()` reste sans `timeslice`.
- [x] Mesures content-free envoyees avec l'upload: duree approx, taille blob, nombre de chunks, raison d'arret.
- [x] Backend: logs content-free de reception upload, statut transcription, latence et erreur bornee; pas d'audio brut, pas de transcript, pas de nom de fichier utilisateur.
- [x] Observabilite incident 2026-05-23: correlation `request_id` FridaDev -> `platform-whisper-api`, `transcript_chars` cote FridaDev, durees ffprobe entree/normalisee, tailles et latences ffmpeg/whisper cote service aval, sans contenu audio ni transcript.
- [x] Timeout applicatif Whisper par defaut porte a `180 s`.
- [x] Brouillon texte existant preserve en cas d'erreur recorder, upstream ou timeout.
- [x] Tests frontend/backend ajoutes pour limite 150 s, raison d'arret, brouillon preserve, gros blob simule et logs content-free.
- [x] Validation live longue 2026-05-23 avec service Whisper aval: test navigateur reel d'environ `99,4 s`, transcription HTTP 200, pas de troncature visible cote utilisateur, aucune perte detectee cote capture/upload/normalisation/transcription/UI sur cet essai.
- [x] Observabilite conservee en surveillance: si une troncature reapparait, repartir des metadonnees content-free `recording_duration_ms`, `normalized_duration_s`, `text_chars`, `stop_reason`, taille blob et latence transcription.

### Lot 0 - Reproduction et observabilite content-free

- [x] Ajouter une preuve reproductible avec audio non sensible ou silence synthetique: 20 s, 60 s, 120 s.
- [x] Mesurer separement les etapes: capture navigateur, construction blob, upload recu par FridaDev, POST upstream Whisper, transcription retournee, reinjection UI.
- [x] Mesurer sans contenu brut: duree capturee, nombre de chunks `dataavailable`, taille blob finale, raison d'arret (`manual`, `auto_limit`, `recorder_error`, `track_ended`, `upload_error`, `transcription_error`), statut HTTP, temps d'upload, temps de transcription.
- [x] Verifier que l'erreur affichee a l'utilisateur distingue arret automatique, erreur MediaRecorder, timeout backend et service Whisper indisponible.
- [x] Reproduire avant patch l'etat courant pour ne pas confondre regression existante, plafond volontaire et panne aval.
- [x] Ne jamais logger audio brut, transcription complete sensible, token, cookie ou header d'autorisation.

### Lot 1 - Frontend: plafond de duree et arret volontaire

- [x] Porter le plafond de capture a au moins 2 minutes, ou rendre la limite explicitement configuree par constante bornee, seulement apres decision sur la strategie blob unique / chunks du lot 2.
- [x] Ne pas traiter la hausse de `60_000 ms` vers `150_000 ms` comme un correctif suffisant tant que l'upload complet, la transcription et la preservation UI ne sont pas prouves.
- [x] Tester que la dictee ne s'arrete pas avant 120 secondes en fonctionnement normal.
- [x] Tester que l'auto-stop arrive seulement a la limite attendue et qu'il est distingue d'une erreur recorder.
- [x] Conserver l'arret volontaire immediat.
- [x] Conserver la preservation du brouillon texte existant si la transcription echoue.
- [x] Afficher un etat clair pendant l'enregistrement et pendant la transcription, sans pedagogie lourde dans l'UI.

### Lot 2 - Frontend: decision chunks MediaRecorder

- [x] Decider explicitement si le correctif initial reste en blob unique jusqu'a 120 s, ou ajoute un `timeslice` a `MediaRecorder.start()` pour recevoir des `dataavailable` periodiques.
- [x] Traiter le `timeslice` comme une option d'architecture a justifier, pas comme un dogme: avec l'endpoint actuel non-streaming, il ne rend pas l'upload streaming a lui seul.
- [x] Si le blob unique est conserve, documenter la preuve que 120 s reste acceptable sur navigateur cible, taille audio attendue, memoire client, upload FridaDev et service aval.
- [x] Si le `timeslice` est ajoute plus tard, definir le gain attendu: limiter les donnees perdues en cas d'erreur tardive, observer la croissance audio, reduire la dependance au `dataavailable` final, ou preparer un futur upload segmente. Non applicable au patch clos: `timeslice` non retenu pour cette livraison.
- [x] Conserver la construction finale du fichier audio si l'endpoint reste non-streaming.
- [x] Eviter qu'un long enregistrement repose sur un unique blob tardif si le navigateur ou le device est instable.
- [x] Tester interruption, erreur recorder, permissions micro et changement d'etat.

### Lot 3 - Backend: limites et erreurs transcription

- [x] Verifier si `WHISPER_API_TIMEOUT_S=120` suffit pour 2 minutes d'audio sur OVH.
- [x] Si necessaire, proposer une valeur bornee plus sure sans toucher a la plateforme dans le meme lot applicatif.
- [x] Verifier separement les limites de taille upload applicatives et proxy sans afficher de config sensible.
- [x] Prouver que FridaDev recoit l'upload complet avant d'attribuer un echec au service Whisper aval.
- [x] Si une limite de taille ou duree est ajoutee plus tard, la rendre explicite, testee, bornee et visible par une erreur content-free. Non applicable au patch clos: aucune nouvelle limite serveur n'a ete ajoutee.
- [x] Garder les erreurs mappees proprement: 400 fichier absent/vide, 502 indisponible, 504 timeout.
- [x] Ne pas lire ni persister plus de contenu audio que necessaire.
- [x] Ne pas ajouter de log contenant audio brut, transcript, nom de fichier utilisateur sensible, cookie, token, header d'autorisation ou detail upstream verbeux.

### Lot 4 - Service Whisper local et discipline Sauron

- [x] Si les preuves pointent vers `platform-whisper-api`, ouvrir un micro-lot sous discipline Sauron pour verifier memoire, OOM, modele charge, threads et duree de transcription. Non requis par la validation 99 s: aucune perte ni OOM detectes.
- [x] Ne pas modifier Docker, ressources, modele Whisper ou plateforme depuis un lot applicatif Celebrimbor sans GO utilisateur explicite. Respecte: pas de Docker/ressources/modele; observabilite du service aval ajoutee avec GO explicite, backup et logs content-free.
- [x] Rejouer ensuite la preuve FridaDev `/api/chat/transcribe` avec audio synthetique non prive. Fait apres observabilite: audio synthetique 12 s, correlation FridaDev -> `platform-whisper-api`, duree normalisee et `text_chars` observes sans contenu.

### Lot 5 - Tests et validation live

- [x] Tests frontend: pas d'auto-stop avant 120 s, auto-stop borne si limite atteinte, arret volontaire, erreur recorder, piste terminee, brouillon texte existant preserve.
- [x] Tests endpoint/service: timeout, erreur upstream, fichier vide, upload long synthetique recu complet, fichier long synthetique transcrit si possible.
- [x] Test integration contrat frontend: bouton micro, endpoint, input_mode voice inchanges.
- [x] Validation navigateur provisoire: dictee longue reelle `99,4 s` OK, arret volontaire `manual` OK, transcription retournee sans troncature visible; cible produit 2 minutes gardee sous surveillance.
- [x] Definir et verifier l'absence de perte: le brouillon texte existant n'est jamais efface; une transcription reussie est ajoutee une seule fois; si une transcription longue echoue, l'UI explique l'echec sans inventer ni effacer de texte.
- [x] Si le produit exige de ne pas perdre l'audio dicte en cas d'echec transcription, ouvrir une decision separee sur retry local ephemere, duree de conservation, consentement utilisateur et garde-fous privacy avant tout patch.
- [x] Verifier qu'aucun audio brut ni transcription sensible ne sort dans logs, read-models, exports ou docs.

### Hors-scope Objet 3

- Ne pas changer le modele Whisper sans lot separe.
- Ne pas modifier Docker, ressources conteneur ou reseau plateforme sans discipline Sauron et GO utilisateur.
- Ne pas brancher une transcription streaming temps reel dans ce lot initial.
- Ne pas toucher au reasoning, au streaming assistant, au web search, a Memory, Identity, Summary, Biblio/RAG ou documents actifs.

### Critere de cloture provisoire Objet 3

- [x] Blocage certain des `60_000 ms` corrige par limite client bornee a `150_000 ms`.
- [x] Validation live bornee documentee: test navigateur reel `recording_duration_ms=99407`, blob recu `2728410` octets, `normalized_duration_s=99.365`, HTTP 200, latence environ `30,9 s`, texte retourne `1185` caracteres.
- [x] Capture, upload, normalisation, transcription et reinjection UI sans perte detectee sur ce test.
- [x] Arret volontaire OK sur le test live: `stop_reason=manual`.
- [x] Erreur transcription visible et non silencieuse couverte par tests automatises.
- [x] Pas de perte du brouillon texte existant; statut explicite si l'audio dicte ne peut pas etre transcrit.
- [x] Pas de log audio brut ni transcription sensible.
- [x] Observabilite content-free maintenue pour diagnostic futur: `recording_duration_ms`, `normalized_duration_s`, `text_chars`, `stop_reason`, taille blob et latence transcription.

## 8. Objet 4 - Repertoires de travail fermes par defaut

Objectif: au chargement initial du frontend, afficher les repertoires de travail replies par defaut, tout en conservant l'ouverture manuelle et sans modifier la conversation active, les fichiers du repertoire ou les selections de fichiers.

### Diagnostic lecture - 2026-05-23

- [x] La surface UI concernee est `app/web/chat_workspace_folders_sidebar.js`.
- [x] L'etat d'expansion etait uniquement local a la session: un `Set` JS initialise vide rendait les repertoires ouverts par defaut.
- [x] Aucune persistance utilisateur explicite de l'etat ouvert/replie n'a ete trouvee dans cette surface: pas de `localStorage`, pas de champ API, pas de preference serveur.
- [x] Decision produit: en absence d'etat utilisateur persiste, le defaut produit prime au chargement initial; l'ouverture/repli manuel reste conserve pendant la session courante.

### Livraison Objet 4 - 2026-05-23

- [x] Defaut UI inverse: les repertoires de travail demarrent replies au premier rendu.
- [x] L'utilisateur peut toujours ouvrir/replier un repertoire par clic sur la ligne ou le bouton de toggle.
- [x] La selection active n'est pas modifiee: le changement ne touche pas l'etat conversationnel, seulement le rendu des lignes enfant.
- [x] Les fichiers et documents actifs ne sont pas modifies: les lignes de fichiers restent simplement masquees tant que le repertoire est replie.
- [x] Test navigateur frontend adapte: premier rendu replie, ouverture manuelle, affichage des fichiers/conversations, selection de fichier, drag-and-drop et OCR de repertoire.

### Hors-scope Objet 4

- Ne pas ajouter de preference persistante sans decision produit separee.
- Ne pas refondre la sidebar, les styles ou les APIs workspace folders.
- Ne pas toucher au backend, a Memory, Identity, Summary, Biblio/RAG, documents actifs, reasoning, streaming chat ou Whisper.

## 9. Objet 5 - Composer chat: actions compactes a droite

Objectif: reorganiser les boutons du composer de chat pour eviter une rangee horizontale trop longue avec les nouveaux modes, sans changer le comportement des actions existantes.

### Diagnostic lecture - 2026-05-23

- [x] Les boutons du composer etaient rendus dans `.composer-actions` sous la zone de saisie.
- [x] Avec micro, web, envoyer, piece/document actif, image et Adobe, la rangee devenait trop longue et fragile sur petits ecrans.
- [x] Les comportements fonctionnels etaient deja portes par les ids existants: `btnMic`, `btnWebSearch`, bouton `submit`, `btnActiveDocument`, `btnImageGeneration`, `btnAdobeMode`.
- [x] Decision: conserver les memes ids/controleurs et changer seulement la structure/layout frontend.

### Livraison Objet 5 - 2026-05-23

- [x] Ajout d'une ligne de composition `textarea + actions` dans le composer.
- [x] Actions placees a droite de la zone de saisie.
- [x] Actions organisees en grille compacte `3 x 2`.
- [x] Ordre visuel retenu: micro, web, envoyer en premiere ligne; piece/document actif, image, Adobe en seconde ligne.
- [x] Priorite visuelle du bouton envoyer conservee: bouton plein, en haut a droite de la grille.
- [x] Layout desktop et mobile borne: grille compacte, textarea conservee a gauche, pas de chevauchement attendu.
- [x] Contrats fonctionnels inchanges: Whisper, document actif, image, web, Adobe et envoi gardent leurs ids, tooltips/labels et listeners.
- [x] Adobe actif continue de forcer `web_search=false` dans le payload.
- [x] Tests navigateur adaptes pour verifier le placement lateral et l'ordre de grille.

### Tests attendus Objet 5

- [x] Desktop: textarea et grille d'actions cote a cote, sans chevauchement.
- [x] Mobile: grille d'actions lisible, composer dans le viewport, textarea non masquee.
- [x] Payload normal sans Adobe inchange.
- [x] Payload Adobe Photoshop/Illustrator inchange.
- [x] Desactivation Adobe retire les champs Adobe du payload.
- [x] Web + Adobe: UI claire, web desactive et payload `web_search=false`.

### Hors-scope Objet 5

- Ne pas changer `/api/chat`.
- Ne pas changer le pipeline Adobe.
- Ne pas changer web search, Whisper backend, generation image backend, reasoning, Memory, Identity, Summary, Docker ou plateforme.
- Ne pas ajouter de nouvelle action au composer.

## 10. Objet 6 - Whisper: animation des statuts actifs

Objectif: rendre les etats actifs de dictee et de transcription plus vivants, sans changer le flux Whisper ni ajouter d'observabilite.

### Diagnostic lecture - 2026-05-23

- [x] La ligne `#dictationStatus` affichait deja les textes `Enregistrement en cours.` et `Transcription en cours.`.
- [x] Le statut etait trop statique pour un etat potentiellement long, surtout pendant la transcription.
- [x] Le flux Whisper expose deja `recording`, `transcribing`, `error`, `busy` et `idle`.
- [x] Decision: utiliser le `data-dictation-state` de la ligne de statut pour piloter une animation CSS, sans changer l'upload ni la transcription.

### Livraison Objet 6 - 2026-05-23

- [x] La ligne de statut recoit maintenant l'etat visuel reel: `recording`, `transcribing`, `busy`, `error` ou `idle`.
- [x] Animation sobre de trois points ondulants pendant `recording`.
- [x] Animation sobre de trois points ondulants pendant `transcribing`.
- [x] Aucun point anime en `idle`, `busy` ou `error`.
- [x] Texte accessible conserve via `textContent`; les points sont decoratifs en CSS.
- [x] `prefers-reduced-motion: reduce` coupe l'animation et garde trois points fixes.
- [x] Aucun changement backend, aucun log, aucun stockage supplementaire.

### Tests attendus Objet 6

- [x] Statut `recording`: texte existant conserve, etat DOM `data-dictation-state="recording"`.
- [x] Statut `transcribing`: texte existant conserve, etat DOM `data-dictation-state="transcribing"`.
- [x] Statut erreur: pas d'animation active, etat DOM `data-dictation-state="error"`.
- [x] Retour normal: etat DOM `idle` et ligne vide.
- [x] CSS contient le garde-fou `prefers-reduced-motion: reduce`.

### Hors-scope Objet 6

- Ne pas changer `/api/chat/transcribe`.
- Ne pas changer `whisper_transcription_service.py` ni les timeouts Whisper.
- Ne pas changer le pipeline chat, Adobe, web search, reasoning, Docker ou plateforme.

## 11. Objet 7 - Chat: loader assistant anime

Objectif: remplacer les points statiques de la bulle assistant d'attente par le meme langage visuel discret que l'animation Whisper.

### Diagnostic lecture - 2026-05-23

- [x] A l'envoi d'un message, `app/web/app.js` creait une bulle assistant initiale avec le texte statique `…`.
- [x] Le streaming visuel progressif etait deja pilote par `chat_streaming.js`; le loader ne devait donc pas toucher au protocole.
- [x] L'animation Whisper venait d'ajouter trois points ondulants avec garde-fou `prefers-reduced-motion`.
- [x] Decision: factoriser l'animation CSS et piloter seulement une classe de loader sur la bulle assistant jusqu'au premier texte visible.

### Livraison Objet 7 - 2026-05-23

- [x] La bulle assistant d'attente demarre vide avec la classe `assistant-loader`.
- [x] `assistant-loader` utilise les memes trois points ondulants que les statuts actifs Whisper.
- [x] La classe loader est retiree des que du texte assistant visible arrive.
- [x] La classe loader est retiree en fin de stream, reponse vide ou erreur.
- [x] `prefers-reduced-motion: reduce` coupe aussi l'animation du loader assistant.
- [x] Aucun changement du protocole streaming, du backend chat, de Memory/Identity/Summary ou des providers.

### Tests attendus Objet 7

- [x] En attente de stream: bulle assistant avec `assistant-loader` et points animes.
- [x] Debut du stream: texte assistant visible, loader retire.
- [x] Fin du stream: pas de loader residuel.
- [x] Erreur: bulle d'erreur sans loader anime.
- [x] Reduced motion: points fixes, animation coupee.

### Hors-scope Objet 7

- Ne pas changer le backend chat ni le protocole streaming.
- Ne pas changer reasoning, Whisper backend, Adobe, web search, Memory, Identity, Summary, Docker ou plateforme.

## 12. Objet 8 - Memoire/intention: `feed her from herself`

Objectif: retenir le chantier conceptuel selon lequel Frida ne doit pas produire de fausses promesses de memoire, de volonte ou d'intention durable.

Reference active:
- `app/docs/todo-todo/memory/Frida_from_herself.md`

### Diagnostic initial - 2026-05-24

- [ ] Distinguer une reconnaissance locale (`la formulation juste est...`) d'un engagement durable (`je retiens`, `je parlerai de...`).
- [ ] Refuser les formulations ou Frida pretend memoriser durablement sans write-path reel.
- [ ] Cadrer un module `feed her from herself`: certaines paroles de Frida sur sa propre conduite deviennent des candidats d'etat, et non de simples effets de surface.
- [ ] Decider si ces candidats passent d'abord par un artefact reflexif separe, un staging mutable ou une extension de l'identity pipeline.
- [ ] Definir les conditions eventuelles de promotion vers `identity_mutables`, sans confusion avec `static`.

### Hors-scope Objet 8

- Ne pas implementer dans ce TODO.
- Ne pas ecrire directement dans `static` ou `identity_mutables` sans contrat separe.
- Ne pas donner au LLM final un pouvoir direct de reecriture identitaire.
- Ne pas transformer une preference relationnelle locale en verite identitaire sans validation.
- Ne pas toucher a Docker, Caddy, Authelia, DB, web search, Whisper, Adobe ou frontend dans ce cadrage docs-only.

## 13. Decisions utilisateur a prendre avant implementation

- [x] Niveaux exacts de reasoning valides apres relecture finale des docs officielles: `none`, `low`, `medium`, `high`.
- [x] Valeur par defaut du reasoning FridaDev: `high`.
- [x] Libelles UI francais definitifs pour l'objet 1: `aucun`, `faible`, `moyen`, `élevé`.
- [x] Emplacement precis du controle dans la fenetre de chat: pres de la zone de saisie, comme raccourci global compact.
- [x] Strategie si `temperature` / `top_p` deviennent incompatibles avec certains niveaux de reasoning: smoke live 2026-05-22 OK, conserver les champs; reouvrir seulement sur erreur provider prouvee.
- [x] Comportement si le modele principal n'est plus GPT-5.1 ou ne supporte pas reasoning: ne pas envoyer le champ, exposer un signal content-free, ne pas planter.
- [x] Niveau de tests visuels attendu pour le streaming: tests unitaires parser/state, tests serveur, validation Playwright/harness et verification live app.
- [x] Comportement streaming en cas d'interruption: terminal `error` ou erreur reseau conserve le statut interrompu et ne canonise pas le fragment visible.
- [x] Cible produit dictee longue: au moins 2 minutes.
- [x] Limite exacte de capture apres correctif initial: 2 minutes strictes, marge 150 s, ou limite configurable par settings. Decision 2026-05-23: limite client bornee a `150 s`.
- [x] Strategie capture longue initiale: blob unique prouve acceptable, ou `timeslice` MediaRecorder avant/avec hausse du plafond. Decision 2026-05-23: blob unique conserve pour ce patch; `timeslice` reste option future si preuve de fragilite.
- [x] Garantie produit attendue en cas d'echec transcription longue: preservation du brouillon texte seulement, ou retry local ephemere de l'audio avec garde-fous privacy explicites. Decision 2026-05-23: preservation du brouillon texte seulement.
- [x] Niveau de diagnostic live accepte pour le service Whisper aval si la cause reste cote plateforme. Decision 2026-05-23: observabilite content-free actuelle suffisante pour surveillance provisoire; ouvrir un micro-lot Sauron seulement si `recording_duration_ms`, `normalized_duration_s`, `text_chars`, taille blob, `stop_reason` ou latence pointent de nouveau vers l'aval.

## 14. Hors-scope global

- Ne pas implementer dans le commit de creation de ce TODO.
- Ne pas modifier runtime, DB, UI ou backend sans lot dedie.
- Ne pas changer le modele principal.
- Ne pas toucher au web search.
- Ne pas ajouter de provider routing, tools, response_format, penalties, seed ou autres reglages OpenRouter non demandes.
- Ne jamais rendre visible le raisonnement interne du modele.
- Ne pas streamer, stocker, persister, exporter ou injecter de `reasoning_details`.
- Ne pas ouvrir le chantier `reasoning conversationnel conserve`: c'est un chantier futur separe.
- Ne pas injecter le raisonnement dans Memory, Identity, Summary, Biblio/RAG ou documents actifs.
- Ne pas logger d'audio brut ni de transcription sensible pour l'objet 3.
- Ne pas afficher secret, `.env`, token, DSN, cookie ou header sensible.

## 15. Criteres de cloture

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
- la dictee Whisper locale atteint la cible 2 minutes sans rupture prematuree;
- les erreurs de transcription longues sont visibles et non silencieuses;
- le brouillon texte existant n'est pas perdu en cas d'echec, et tout objectif de retry audio ephemere a ete decide explicitement avant patch;
- les tests runtime, frontend et docs sont passes;
- aucune contamination Memory / Identity / Summary / Biblio/RAG / documents actifs / exports n'est observee;
- aucun audio brut ni transcription sensible n'est loggue, exporte ou documente;
- une validation live bornee est documentee;
- les repertoires de travail sont replies par defaut au chargement initial et ouvrables manuellement;
- les actions du composer sont en grille droite compacte `3 x 2`, avec envoyer en haut a droite et sans regression des actions existantes;
- les statuts actifs Whisper affichent une animation sobre et compatible reduced motion sans toucher au backend;
- le loader assistant du chat utilise la meme animation sobre, disparait au premier contenu visible et reste compatible reduced motion;
- le chantier `feed her from herself` est soit extrait dans un TODO memoire dedie avec contrat, soit explicitement maintenu hors implementation;
- le renommage en `job-divers-todo.md` est propage aux index et roadmaps actives;
- le TODO est archive dans `app/docs/todo-done/product/`.
