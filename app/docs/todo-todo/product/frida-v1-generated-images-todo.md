# Frida V1 - Images generees - TODO

Statut: TODO actif detaille; aucun lot Images V1 n'est encore coche.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Intention

Stabiliser les images generees par Frida comme artefacts produit rattaches a un
dossier Frida, sans confondre cette capacite avec les documents utilisateur, les
images actives de conversation, les exports, les notes, la Biblio ou le prompt
brut.

Regle cible pour toute image persistante Images V1:

```text
workspace_folder linked -> image generee -> /Frida/<dossier>/Images
```

Ce document est une roadmap de livraison. Il ne livre aucun runtime, aucune
route, aucune migration, aucune generation d'image et aucun acces Nextcloud.

## Sources de verite

- Roadmap finale Frida 1.0:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- Socle dossiers Nextcloud V1 clos:
  `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- Archive socle dossiers Nextcloud V1:
  `app/docs/todo-done/product/frida-v1-nextcloud-folders-todo.md`
- Documents V1 clos:
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- Archive Documents V1:
  `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
- Notes Markdown V1 closes:
  `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- Archive Notes Markdown V1:
  `app/docs/todo-done/product/frida-v1-folder-markdown-notes-todo.md`
- Exports V1 clos:
  `app/docs/states/specs/frida-v1-exports-contract.md`
- Archive Exports V1:
  `app/docs/todo-done/product/frida-v1-exports-todo.md`
- Archive generation d'images OpenRouter V0:
  `app/docs/todo-done/product/fridadev-image-generation-openrouter-todo.md`
- Archive lecture d'images comme documents actifs:
  `app/docs/todo-done/product/fridadev-active-image-documents-todo.md`
- Vue pipeline runtime:
  `app/docs/states/architecture/fridadev-full-pipeline-overview-2026-05-19.md`

## Surfaces existantes a auditer sans les confondre avec Images V1

### Outil lateral de generation d'images

Surfaces actuelles:

- backend: `app/tools/image_generation.py`;
- route: `POST /api/tools/image-generation`;
- frontend: `app/web/chat_image_generation.js`;
- UI: panneau `#imageGenerationPanel` dans `app/web/index.html`;
- styles: bloc `image-generation-*` dans `app/web/styles.css`;
- tests: `app/tests/unit/tools/test_image_generation.py`,
  `app/tests/test_server_image_generation.py`,
  `app/tests/unit/frontend_chat/test_image_generation_module.js`,
  `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`.

Comportement observe:

- l'utilisateur saisit un prompt dans un outil lateral;
- le backend appelle OpenRouter via une allowlist de generateurs;
- le resultat revient au navigateur sous forme `image_data_url`;
- l'image peut etre affichee et telechargee localement;
- aucune image n'est persistee cote serveur;
- aucun `workspace_folder_id` n'est exige;
- aucune cible `/Frida/<dossier>/Images` n'est ecrite;
- aucun read-model d'image generee n'existe;
- l'outil ne poste pas dans `/api/chat` et n'injecte pas l'image dans le
  dialogue, Memory, Identity, Summary, Biblio ou Documents actifs.

Classification pour Images V1: adapter avec prudence.

Patterns reutilisables:

- allowlist de generateurs;
- validation `generator_key`, prompt, ratio et taille;
- attribution OpenRouter par generateur;
- timeout dedie;
- extraction d'une data URL image;
- logs content-free sans prompt brut ni base64.

Patterns a ne pas copier aveuglement:

- retour direct `image_data_url` comme contrat produit final;
- telechargement navigateur comme preuve de stockage;
- absence de dossier;
- absence de read-model;
- absence de cible Nextcloud;
- duplication durable de la table generateurs frontend/backend sans audit.

### Images actives et Documents visuels

Surfaces existantes:

- `app/core/active_document_image_validation.py`;
- `app/core/active_document_prompt_lane.py`;
- `app/core/active_conversation_documents.py`;
- `app/core/active_document_upload_service.py`;
- `app/core/workspace_file_selection_prompt.py`;
- `app/core/workspace_folder_documents.py`;
- `app/web/chat_active_documents.js`;
- tests actifs image et Documents visuels sous `app/tests/`.

Comportement observe:

- les images actives sont des pieces de conversation ou de dossier selectionnees
  pour un tour utile;
- les bytes peuvent etre envoyes au modele comme payload multimodal;
- le chemin construit des data URLs au dernier moment pour le provider;
- les logs, read-models et preuves restent sans image brute, base64 ou data URL;
- les images utilisateur et PDF visuels relevent du chantier Documents /
  active documents, pas du chantier Images generees.

Classification pour Images V1: adapter pour les validateurs et garde-fous,
eviter pour le modele produit.

A eviter:

- transformer une image generee en `active_document` par defaut;
- ranger une image generee dans `Documents`;
- reutiliser `workspace_files` comme read-model produit Images;
- presenter une image generee comme document utilisateur ou OCR source.

### Sous-dossiers standards Nextcloud

Surface existante:

- `app/core/workspace_folder_standard_subfolders.py`

Comportement observe:

- les sous-dossiers standards `Documents`, `Notes`, `Exports` et `Images` sont
  deja definis au niveau du socle folders;
- les futurs lots d'artefacts doivent verifier le sous-dossier cible par
  `PROPFIND Depth: 0` et confirmation collection;
- `207` seul ne suffit jamais;
- pas de listing de contenu Nextcloud comme preuve.

Classification pour Images V1: reutiliser comme prerequis de cible standard,
sans elargir le scope Nextcloud.

## Objectif produit Images V1

Permettre a Frida de produire et ranger durablement une image generee comme
artefact produit d'un dossier Frida.

Capacites V1 visees, sous reserve de decisions Lot 1:

- creer une image generee depuis une action utilisateur explicite;
- rattacher l'image a un `workspace_folder`;
- ranger l'image sous le sous-dossier standard `Images`;
- persister un read-model local metadata-only;
- lister et retrouver les images generees d'un dossier;
- ouvrir ou telecharger explicitement une image generee;
- afficher ces capacites dans l'UI dossier;
- prouver le flux avec smokes synthetiques content-free.

Images V1 ne doit pas pretendre livrer edition d'image, galerie avancee,
Memory/RAG, Biblio, Documents, Notes ou Exports.

Un succes produit Images V1 exige toute la chaine:

- generation provider OK;
- validation image OK;
- ecriture Nextcloud-first OK sous `/Frida/<dossier>/Images`;
- persistance du read-model Images OK.

Si le provider retourne une image mais que le stockage durable echoue, timeout,
rencontre un conflit, une cible `Images` indisponible ou une persistance locale
impossible, le verdict produit reste un echec/refus content-free. FridaDev ne
doit alors creer aucun read-model `linked`, ne doit persister aucune data URL et
ne doit pas vendre un fallback navigateur non durable comme succes Images V1. Un
eventuel choix produit "afficher quand meme l'image non durable" serait un lot
separe hors V1, a ne pas inventer pendant le runtime.

## Frontieres produit

### Images generees vs Documents

- Documents V1 gere les fichiers utilisateur persistants sous
  `/Frida/<dossier>/Documents`.
- Une image generee par Frida est un artefact produit par Frida, pas un document
  source utilisateur.
- Images V1 ne doit pas reutiliser `workspace_files` comme read-model produit
  des images generees.
- Une image generee ne devient pas automatiquement selectionnee, preparee,
  OCRisee ou injectee dans le chat comme document.

### Images generees vs images actives

- Une image active est une piece de conversation ou de dossier envoyee au
  modele multimodal sur action explicite.
- Une image generee est un resultat d'outil/image generator.
- Le fait de produire une image ne l'injecte pas automatiquement dans le tour de
  chat.
- Toute reutilisation conversationnelle d'une image generee comme source visuelle
  est hors V1 tant qu'un contrat dedie ne l'autorise pas.

### Images generees vs Exports

- Exports V1 produit Markdown, TXT, DOCX et PDF sous
  `/Frida/<dossier>/Exports`.
- Images V1 produit des fichiers image sous `/Frida/<dossier>/Images`.
- Un PDF exporte contenant une image ne livre pas Images V1.
- Images V1 ne doit pas utiliser `workspace_folder_exports` comme read-model.

### Images generees vs Notes

- Notes V1 gere des fichiers Markdown vivants sous
  `/Frida/<dossier>/Notes`.
- Une reference Markdown vers une image n'est pas une livraison Images V1.
- Images V1 ne modifie pas les notes et ne stocke pas d'image dans `Notes`.

### Images generees vs Biblio / Agenda / Mail / Memory

Images V1 ne livre pas:

- Biblio ou Catalogue;
- Agenda;
- Mail;
- Memory/RAG;
- Identity;
- Summary;
- indexation visuelle;
- embedding d'image;
- agent vision autonome.

### Images generees vs prompt brut

Le prompt utilisateur d'une generation peut contenir informations privees,
secrets, noms, descriptions sensibles ou instructions. Il n'est pas une
metadonnee technique anodine.

Images V1 ne doit jamais exposer le prompt brut dans logs, JSONL, observabilite
technique, dashboard technique, reason codes ou preuves. La decision de le
stocker ou non en DB applicative est ouverte et bloquante avant runtime.

## Decisions produit deja prises

- Images generees V1 vient apres la cloture de Nextcloud folders V1, Documents
  V1, Notes Markdown V1 et Exports V1.
- Le sous-dossier standard cible est `Images`.
- La cible logique attendue est `/Frida/<dossier>/Images`.
- Les constantes produit `Images`, `Documents`, `Notes` et `Exports` peuvent
  apparaitre dans les docs, reason codes et preuves.
- Toute image persistante Images V1 est obligatoirement rattachee a un
  `workspace_folder`.
- Seuls les dossiers Frida `linked` peuvent recevoir une ecriture Nextcloud
  d'artefact.
- Les etats `local_only`, `sync_pending`, `sync_error`, `conflict` et `deleted`
  bloquent toute ecriture Nextcloud d'image generee.
- `Images` doit exister et etre une collection WebDAV valide avant ecriture.
- FridaDev ne doit jamais acceder directement a la DB Nextcloud.
- Pas de listing large Nextcloud.
- Pas d'overwrite silencieux.
- Pas de renommage automatique silencieux.
- Un modele local/read-model Images V1 dedie est obligatoire, distinct de
  `workspace_files`, `workspace_folder_exports`, Notes, Documents et Exports.
- Les preuves techniques doivent rester content-free: compteurs, statuts,
  refs/hashs courts, tailles, dimensions, formats, reason codes.
- Les bytes image, base64, data URL, chemins DAV, URL DAV, XML brut, payload
  WebDAV, prompt brut, secret, token, cookie et app-password sont interdits dans
  les preuves et l'observabilite technique.
- Le chantier Images ne rouvre pas Documents, Notes, Exports, Biblio, Agenda,
  Mail, Memory/RAG, Identity ou Summary.
- L'outil V0 actuel peut rester lateral/local/non persistant tant qu'il ne
  pretend pas livrer Images V1.

## Decisions ouvertes avant runtime

Aucun lot applicatif Images V1 ne doit demarrer tant que ces decisions ne sont
pas fermees dans la spec Lot 1. Si une decision nouvelle apparait pendant un lot
runtime, le lot s'arrete avant patch, avant spec additionnelle opportuniste,
avant commit et avant de cocher le lot.

### Prompt de generation

Decision manquante:

- stocker le prompt brut en DB applicative;
- stocker un resume utilisateur;
- stocker seulement un hash/ref;
- ne rien stocker;
- stocker une version redigee/redacted sous controle explicite.

Contraintes deja fermees:

- prompt brut interdit dans logs, JSONL, observabilite technique et preuves;
- prompt brut interdit dans reason codes;
- prompt brut interdit dans refs techniques;
- si le prompt est visible cote utilisateur, la surface doit etre explicitement
  decidee et testee.

No-go: aucun read-model Images ne doit etre livre tant que la politique prompt
n'est pas tranchee.

### Formats image V1

Decision manquante:

- formats persistables V1: PNG, JPEG, WebP, SVG, GIF, autre;
- faut-il conserver le format fournisseur ou normaliser;
- faut-il refuser SVG pour eviter scripts/actifs ou l'autoriser comme fichier;
- faut-il refuser GIF anime.

Constats actuels:

- l'outil image V0 accepte toute data URL `image/*` valide cote backend;
- les images actives Documents utilisent surtout PNG/JPEG/WebP et refusent GIF
  en V0;
- les smokes historiques de generation ont observe PNG, WEBP et SVG selon les
  tests/mocks.

No-go: pas de stockage durable tant que l'allowlist format V1 n'est pas fermee.

### Miniature

Decision manquante:

- pas de miniature V1;
- miniature generee cote backend;
- miniature fournie par Nextcloud;
- miniature seulement dans un lot UI post-V1.

No-go: ne pas ajouter de pipeline thumbnail, cache ou transformation sans
decision produit et tests anti-fuite.

### Limites taille/dimensions

Decision manquante:

- taille maximale de l'image generee stockee;
- taille maximale de la data URL fournisseur avant decodage;
- dimensions maximales;
- politique si dimensions inconnues;
- limite de duree generation + stockage.

Points de comparaison:

- generation V0: prompt `2000` caracteres, timeout `180` secondes,
  data URL max `6_000_000` caracteres;
- Documents visuels et Exports utilisent des limites `25 MiB` sur certains flux;
- images actives source acceptent des limites differentes qui ne doivent pas
  etre reprises sans decision.

No-go: pas de creation runtime Images sans limites completes ou refus fail-closed.

### Nommage et titre utilisateur

Decision manquante:

- titre utilisateur obligatoire ou optionnel;
- nom derive du prompt, du generateur ou d'un timestamp;
- visibilite utilisateur du titre;
- presence ou absence d'un nom provider;
- politique de collision et versioning.

Contraintes:

- le nom cible sanitise interne ne doit pas apparaitre en observabilite
  technique;
- collision = refus content-free, sauf decision future de versioning explicite.

### Reutilisation comme source

Decision manquante:

- Images V1 permet-elle de reutiliser une image generee comme source d'une
  nouvelle generation;
- permet-elle de l'envoyer comme image active;
- permet-elle de l'utiliser dans un export;
- ou bien toute reutilisation est-elle post-V1.

Position prudente recommandee: V1 liste, lookup, open/download et UI de dossier;
la reutilisation comme source reste post-V1 sauf decision produit explicite en
Lot 1.

### Suppression et retention

Decision manquante:

- suppression distante Nextcloud reelle avant tombstone local;
- tombstone local seulement, en conservant l'image distante;
- suppression utilisateur interdite en V1;
- cleanup strict seulement pour smokes synthetiques.

No-go: ne pas supprimer d'image utilisateur distante sans decision produit et
contrat de compensation.

### Observabilite technique autorisee

Decision a stabiliser:

- refs autorisees: `image_ref`, `folder_ref`, `prompt_hash` si applicable,
  `content_hash`, `mime_type`, `byte_size`, `width`, `height`, `generator_key`,
  `provider_model`, `aspect_ratio`, `image_size`, statuts et reason codes;
- interdits: prompt brut, image brute, base64, data URL, target brut, ETag brut,
  URL DAV, chemin DAV, XML, payload provider, payload WebDAV, secret.

Lot 1 doit transformer cette liste en projection technique allowlistee.

### Lot Z

Decision a fermer:

- faut-il prouver live une generation provider reelle ou seulement un fake
  provider plus stockage Nextcloud;
- quels formats exacts doivent etre prouves live;
- faut-il scanner les logs applicatifs comme Exports Lot Z;
- quels cas non applicables peuvent etre couverts par tests sans mutation DB.

## Garde-fous runtime graves a graver en Lot 1

- Dossier non `linked` = refus content-free.
- Dossier `deleted` = refus content-free.
- Dossier `local_only`, `sync_pending`, `sync_error` ou `conflict` = refus
  d'ecriture.
- Sous-dossier `Images` absent, non-collection ou inaccessible = refus
  content-free.
- `PROPFIND 207` seul ne suffit pas.
- Pas de DB Nextcloud directe.
- Pas de listing large Nextcloud.
- Pas d'overwrite.
- Pas de renommage automatique non decide.
- Pas de stockage local de bytes image dans une projection technique.
- Pas de prompt brut dans les surfaces techniques.
- Pas de data URL/base64 dans logs, JSONL, docs de preuve ou dashboard.
- Provider OK sans stockage durable complet reste un echec/refus content-free,
  pas un succes Images V1.
- Aucun read-model `linked` ne doit etre persiste si l'ecriture Nextcloud ou la
  persistance locale echoue.
- Aucun fallback navigateur durable ne doit etre vendu comme succes V1.
- Pas de mutation Documents, Notes ou Exports par opportunisme.
- Pas d'injection chat automatique.
- Pas de Memory/RAG/Identity/Summary.

## Lots proposes

Les lots ci-dessous sont tous ouverts. Cette re-ecriture de TODO ne coche aucun
lot Images V1.

### Lot 0 - Audit existant read-only/docs-only

- [ ] Relire `app/tools/image_generation.py`.
- [ ] Relire `POST /api/tools/image-generation` dans `app/server.py`.
- [ ] Relire `app/web/chat_image_generation.js`, `app/web/index.html` et les
  styles `image-generation-*`.
- [ ] Relire les tests image generation backend, serveur, frontend et browser.
- [ ] Relire les surfaces images actives / Documents visuels sans les confondre
  avec Images generees.
- [ ] Identifier les patterns reutilisables: validation, generateurs, logs,
  extraction data URL, download navigateur, tests.
- [ ] Identifier les patterns a eviter: route outil globale, data URL comme
  stockage, absence de dossier, absence de read-model, prompt brut.
- [ ] Inventorier les champs actuellement exposes au frontend et aux logs.
- [ ] Produire un audit content-free sous `app/docs/states/audits/`.
- [ ] Ne livrer aucun runtime, aucune migration, aucun acces Nextcloud, aucune
  generation live.

### Lot 1 - Spec source-of-truth Images V1

- [ ] Creer `app/docs/states/specs/frida-v1-generated-images-contract.md`.
- [ ] Fermer toutes les decisions ouvertes ci-dessus avant runtime.
- [ ] Definir le modele produit Image generee V1.
- [ ] Graver le rattachement obligatoire de toute image persistante a
  `workspace_folders.id`.
- [ ] Definir la cible normative `/Frida/<dossier>/Images`.
- [ ] Definir la politique de prompt: brut, resume, hash ou non-stockage.
- [ ] Definir les formats V1 autorises.
- [ ] Definir les limites de prompt, data URL, bytes, dimensions et timeout.
- [ ] Fixer le nom du modele local/read-model Images V1 dedie obligatoire.
- [ ] Definir les routes/API autorisees sous namespace dossier.
- [ ] Definir la politique de nommage, collision, versioning et suppression.
- [ ] Definir les projections utilisateur et technique content-free.
- [ ] Definir le catalogue initial de reason codes.
- [ ] Definir les criteres Lot Z.
- [ ] Si une decision produit manque, s'arreter avant de committer la spec et
  demander explicitement.
- [ ] Ne livrer aucun runtime.

### Lot 2 - Modele local / read-model images

- [ ] Livrer le read-model Images V1 dedie obligatoire decide par la spec Lot
  1.
- [ ] Garder ce read-model distinct de `workspace_files`,
  `workspace_folder_exports`, Notes, Documents et Exports.
- [ ] Rattacher strictement chaque image a `workspace_folders.id`.
- [ ] Representer statut local, statut Nextcloud, format, MIME, dimensions,
  tailles, generateur, provider model, refs/hashs et reason codes.
- [ ] Appliquer la politique prompt decidee par Lot 1, sans prompt brut par
  defaut.
- [ ] Ne pas stocker les bytes image en DB applicative.
- [ ] Ne pas stocker de data URL/base64.
- [ ] Produire projections utilisateur et technique content-free.
- [ ] Fail-closed si le store images est indisponible.
- [ ] Tester statut, projections, anti-fuite, prompt policy et deleted.
- [ ] Ne pas contacter Nextcloud/WebDAV live.

### Lot 3 - Stockage Nextcloud-first sous Images

- [ ] Adapter le moteur de generation existant ou extraire une capacite provider
  reusable sans passer par un contrat `image_data_url` navigateur comme stockage.
- [ ] Exiger `workspace_folder` existant et `linked`.
- [ ] Refuser `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted`.
- [ ] Verifier `Images` par `PROPFIND Depth: 0` et confirmation collection.
- [ ] Generer ou recevoir l'image selon la spec Lot 1.
- [ ] Decoder/valider l'image selon les formats et limites V1 avant ecriture.
- [ ] Ecrire dans Nextcloud avec strategie anti-ecrasement.
- [ ] Accepter uniquement une creation sure.
- [ ] Traiter les statuts update-like comme conflit/refus, jamais comme succes.
- [ ] Persister le read-model local seulement apres succes distant.
- [ ] Considerer le succes produit seulement si generation provider, validation
  image, ecriture Nextcloud-first et persistance read-model reussissent toutes.
- [ ] Si le provider reussit mais que le stockage durable echoue, refuser
  content-free: aucun read-model `linked`, aucun fallback navigateur durable
  vendu comme succes V1, aucune data URL persistee.
- [ ] Si ecriture distante reussit puis persistance locale echoue, tenter une
  compensation distante strictement bornee a la cible creee.
- [ ] Ne jamais exposer prompt brut, bytes, data URL, base64, cible DAV, URL DAV,
  XML, ETag brut ou payload provider/WebDAV dans logs/projections/preuves.
- [ ] Produire une preuve live synthetique content-free avec cleanup exact.

### Lot 4 - Liste / lookup / projection utilisateur

- [ ] Ajouter la liste des images generees d'un dossier depuis le read-model
  local uniquement.
- [ ] Ajouter lookup par UUID exact.
- [ ] Exiger dossier valide et `linked`.
- [ ] Refuser dossier supprime, non eligible ou panne store.
- [ ] Exclure les images `deleted` par defaut.
- [ ] Verifier que l'image appartient strictement au dossier du path.
- [ ] Ne pas appeler WebDAV/Nextcloud.
- [ ] Ne pas lire de bytes image.
- [ ] Exposer cote utilisateur titre/nom si autorise, format, taille,
  dimensions, dates, statut et actions disponibles.
- [ ] Garder la projection technique sans prompt brut, target brut, ETag brut,
  URL DAV, chemin DAV, XML, bytes, base64 ou data URL.
- [ ] Tester liste vide, liste multi-formats, deleted exclu, lookup OK, absent,
  cross-folder, panne store et anti-fuite.

### Lot 5 - Open/download image

- [ ] Ajouter une action explicite de telechargement sous namespace dossier.
- [ ] Ajouter une action explicite d'ouverture inline seulement si la spec Lot 1
  l'autorise.
- [ ] Exiger dossier `linked`.
- [ ] Exiger image active, non deleted, rattachee au dossier du path et
  `nextcloud_sync_state=linked`.
- [ ] Lire uniquement la cible distante exacte persistee dans le read-model.
- [ ] Ne faire aucun listing Nextcloud.
- [ ] Appliquer la limite de taille decidee par Lot 1, complet ou refus.
- [ ] Ne pas tronquer silencieusement.
- [ ] Ajouter headers sobres: `X-Content-Type-Options: nosniff` et
  `Cache-Control: private, no-store`.
- [ ] Ne jamais exposer prompt brut ou chemin distant dans les headers.
- [ ] Tester absent, deleted, cross-folder, non linked, taille trop grande,
  panne store, panne Nextcloud, headers et anti-fuite.

### Lot 6 - UI dossier Images

- [ ] Ajouter une surface Images dans le contexte du dossier Frida courant.
- [ ] Charger la liste seulement pour un dossier `linked`.
- [ ] Afficher les images generees sans prompt brut si la politique Lot 1 ne
  l'autorise pas.
- [ ] Permettre la creation seulement par action explicite et payload conforme a
  la spec Lot 1.
- [ ] Ne jamais envoyer `messages`, contenu image brut existant, data URL ou
  bytes depuis l'UI comme preuve de source non decidee.
- [ ] Ne jamais envoyer un ID serveur client-owned pour contourner le create.
- [ ] Ouvrir/telecharger uniquement quand les flags serveur l'autorisent.
- [ ] Ne pas exposer Documents, Notes, Exports, Biblio, Agenda, Mail,
  Memory/RAG/Identity/Summary comme sources.
- [ ] Afficher les erreurs utilisateur sobrement.
- [ ] Tester payloads, routes namespaced, actions disabled/enabled, absence de
  route globale, absence de prompt brut dans surfaces techniques et responsive.

### Lot 7 - Observabilite / smokes content-free

- [ ] Consolider les projections/events techniques content-free si necessaire.
- [ ] Produire un JSONL live synthetique sous
  `app/docs/states/baselines/generated-images-smokes/`.
- [ ] Prouver create/store Nextcloud-first pour les formats V1 livres.
- [ ] Prouver liste, lookup, open/download si livres.
- [ ] Prouver conflit sans overwrite.
- [ ] Prouver refus dossier non `linked` par live propre ou tests si aucun
  dossier non `linked` naturel n'existe.
- [ ] Prouver cleanup distant exact et tombstone local des images synthetiques.
- [ ] Scanner artefact, docs, diff staged et, si decide, logs applicatifs bornes.
- [ ] Ne toucher aucun contenu utilisateur reel.
- [ ] Ne conserver aucun prompt brut, bytes image, data URL, base64, chemin DAV,
  URL DAV, XML, ETag brut, payload ou secret.

### Lot Z - Cloture Images V1

- [ ] Rejouer ou relire les smokes transverses Images V1.
- [ ] Verifier create/generate/store Nextcloud-first.
- [ ] Verifier formats V1 reellement livres.
- [ ] Verifier no-overwrite / conflit nom.
- [ ] Verifier list / lookup UUID.
- [ ] Verifier open/download si livres.
- [ ] Verifier UI dossier Images si livree.
- [ ] Verifier refus prompt/source/format/taille selon spec Lot 1.
- [ ] Verifier cleanup distant/local des images synthetiques.
- [ ] Verifier absence de confusion Documents / Notes / Exports / Images.
- [ ] Executer les scans anti-fuite exiges par la spec Lot 1.
- [ ] Archiver cette TODO seulement si le verdict final est suffisant.
- [ ] Ne pas vendre une preuve plus large que ce qui est reellement execute.

## Reason codes initiaux a stabiliser

Catalogue candidat, a fermer en spec Lot 1:

- `folder_image_folder_invalid`;
- `folder_image_folder_deleted`;
- `folder_image_folder_not_linked`;
- `folder_image_images_target_missing`;
- `folder_image_images_target_not_collection`;
- `folder_image_images_target_unavailable`;
- `folder_image_prompt_policy_unresolved`;
- `folder_image_prompt_missing`;
- `folder_image_prompt_too_large`;
- `folder_image_generator_unsupported`;
- `folder_image_aspect_ratio_unsupported`;
- `folder_image_size_unsupported`;
- `folder_image_format_unsupported`;
- `folder_image_mime_invalid`;
- `folder_image_data_url_invalid`;
- `folder_image_too_large`;
- `folder_image_dimensions_invalid`;
- `folder_image_name_invalid`;
- `folder_image_name_conflict`;
- `folder_image_not_found`;
- `folder_image_deleted`;
- `folder_image_not_linked`;
- `folder_image_lookup_failed`;
- `folder_image_access_not_prepared`;
- `folder_image_generation_failed_redacted`;
- `folder_image_provider_timeout`;
- `folder_image_provider_error_redacted`;
- `folder_image_create_ok`;
- `folder_image_store_ok`;
- `folder_image_store_failed_redacted`;
- `folder_image_list_ok`;
- `folder_image_lookup_ok`;
- `folder_image_download_ok`;
- `folder_image_open_ok`;
- `folder_image_local_persistence_failed`;
- `folder_image_remote_compensation_ok`;
- `folder_image_remote_compensation_failed`;
- `folder_image_nextcloud_error_redacted`.

Interdits:

- reason code contenant un prompt brut;
- reason code contenant un nom cible brut;
- reason code contenant une URL, un chemin, XML, ETag brut, payload, secret ou
  contenu image.

## Preuves attendues

- Audit Lot 0 content-free sous `app/docs/states/audits/`.
- Spec Lot 1 source-of-truth avant runtime.
- Tests unitaires pour validation prompt policy, format, MIME, dimensions,
  taille, noms, projections et reason codes.
- Tests fake provider pour generation sans OpenRouter live.
- Tests fake transport Nextcloud pour anti-overwrite, rollback et compensation.
- Tests serveur pour routes namespaced si ajoutees.
- Tests frontend si UI modifiee.
- Smokes live uniquement sur images synthetiques et non sensibles.
- JSONL content-free sous `app/docs/states/baselines/generated-images-smokes/`.
- Cleanup distant/local des images synthetiques.
- Scans anti-fuite sur diff, JSONL, docs et preuves; logs seulement si scan
  borne explicite execute et documente.

## Interdits dans preuves techniques

- prompt brut;
- image brute;
- bytes image;
- base64;
- data URL;
- nom utilisateur sensible;
- nom cible brut;
- chemin DAV;
- URL DAV;
- XML;
- ETag brut;
- payload provider brut;
- payload WebDAV brut;
- secret;
- token;
- cookie;
- app-password;
- Authorization;
- contenu utilisateur reel.

## Hors-scope V1

- Edition d'image.
- Galerie avancee.
- Multi-image batch.
- Video.
- Publication externe.
- Moderation avancee hors provider et hors decision dediee.
- Prompt rewriting automatique par Frida.
- Stockage local de bytes image en DB.
- OCR automatique des images generees.
- Description automatique persistante.
- Injection chat automatique.
- Reutilisation comme source sans contrat Lot 1 explicite.
- Documents ingestion.
- Notes Markdown.
- Exports.
- Biblio / Catalogue.
- Agenda.
- Mail.
- Memory/RAG/Identity/Summary.
- Migration d'images historiques sans lot dedie.
- Listing large de contenu Nextcloud comme preuve.
- DB Nextcloud directe.

## Points faibles a surveiller

- Faire passer une data URL navigateur pour un stockage durable.
- Vendre une image provider OK mais non stockee durablement comme succes Images
  V1.
- Stocker le prompt brut par commodite.
- Reutiliser `workspace_files` et brouiller Documents/Images.
- Ouvrir une route globale `/api/images*` ou reutiliser `/api/tools` comme route
  produit dossier.
- Accepter un `200`/`204` WebDAV update-like comme creation sure.
- Oublier rollback si la persistance locale echoue apres creation distante.
- Logger le payload provider ou la data URL.
- Afficher une miniature comme preuve technique en JSONL.
- Presenter une image generee comme lue par Frida sans action explicite.
- Cocher Lot Z avec des preuves seulement frontend/local download.

## Prochain pas

Executer Lot 0 Images V1: audit read-only/docs-only des surfaces de generation
d'images, images actives, Documents visuels, UI et tests existants. Lot 0 doit
produire un audit content-free sous `app/docs/states/audits/` et ne doit livrer
aucun runtime.
