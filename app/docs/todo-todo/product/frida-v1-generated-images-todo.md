# Frida V1 - Images generees - TODO

Statut: TODO actif detaille; Lots 0, 1, 2, 3 et 4 coches; read-model local,
creation Nextcloud-first et liste/lookup metadata-only livres; Lot 5+ ouverts.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Spec source-of-truth Lot 1:
`app/docs/states/specs/frida-v1-generated-images-contract.md`
Audit Lot 0:
`app/docs/states/audits/frida-v1-generated-images-lot0-audit-2026-06-19.md`

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
- Spec Images generees V1:
  `app/docs/states/specs/frida-v1-generated-images-contract.md`
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

## Decisions produit fermees par la spec Lot 1

La spec source-of-truth Images V1 ferme les decisions ci-dessous. Aucun lot
applicatif Images V1 ne doit les reouvrir silencieusement. Si une contradiction
reelle apparait pendant un lot runtime, le lot s'arrete avant patch, commit et
coche de lot, puis ouvre un micro-lot documentaire.

### Prompt de generation

Decision Lot 1:

- le prompt brut peut exister en memoire UI et serveur pendant l'appel provider;
- aucun prompt brut, resume de prompt ou hash reversible/deductible du prompt
  n'est persiste comme metadata durable Images V1;
- les seuls signaux durables autorises sont `prompt_present`, bucket de longueur
  bornee, generateur, format et reason codes content-free;
- les buckets de longueur sont les enums non ambigus `chars_001_to_250`,
  `chars_251_to_500`, `chars_501_to_1000`, `chars_1001_to_1500` et
  `chars_1501_to_2000`;
- prompt brut interdit dans logs, JSONL, observabilite technique, proofs,
  reason codes, target name et projection technique.

### Formats image V1

Decision Lot 1:

- PNG, JPEG et WebP sont les seuls formats durables Images V1;
- SVG, GIF et tout format inconnu sont refuses en V1 durable;
- pas de transcodage automatique V1;
- le format provider est conserve seulement s'il appartient a l'allowlist V1.

### Miniature

Decision Lot 1:

- pas de miniature persistante en V1;
- pas de cache thumbnail;
- pas de transformation image dediee a une miniature;
- l'UI peut s'appuyer sur open/download explicites ou route image bornee.

### Limites taille/dimensions

Decision Lot 1:

- prompt `2000` caracteres maximum;
- timeout provider `180` secondes;
- data URL provider transitoire `22_000_000` caracteres maximum;
- image stockee `15 MiB` maximum;
- dimensions minimales `32 x 32`;
- cote maximal `16000`;
- surface maximale `100_000_000` pixels;
- complet ou refus, aucune troncature silencieuse.

### Nommage et titre utilisateur

Decision Lot 1:

- nom cible serveur-owned et neutre: `generated-image-<image_id>.<format>`;
- `image_id` serveur-owned, jamais impose par le client;
- display name utilisateur facultatif, fourni explicitement ou genere de facon
  neutre;
- nom cible brut interdit en observabilite technique;
- collision = refus content-free, pas d'overwrite, pas de renommage silencieux.

### Reutilisation comme source

Decision Lot 1:

- reuse-as-source hors V1;
- une image generee ne devient pas source d'une nouvelle generation en V1;
- une image generee ne devient pas image active de conversation en V1;
- pas d'injection chat automatique.

### Suppression et retention

Decision Lot 1:

- suppression utilisateur V1 autorisee seulement par action explicite sous
  route namespaced;
- suppression distante exacte d'abord;
- tombstone local seulement apres succes distant;
- fail-closed si la suppression distante echoue;
- cleanup synthetique autorise sur cible exacte pour smokes.

### Observabilite technique autorisee

Decision Lot 1:

- refs autorisees: `image_ref`, `folder_ref`, hash court de contenu,
  `mime_type`, `byte_size`, `width`, `height`, `generator_key`,
  `provider_model`, `aspect_ratio`, `image_size`, bucket de longueur prompt,
  `prompt_present`, statuts et reason codes;
- interdits: prompt brut, image brute, base64, data URL, target brut, ETag brut,
  URL DAV, chemin DAV, XML, payload provider, payload WebDAV, secret.

### Lot Z

Decision Lot 1:

- Lot Z doit inclure au moins un smoke provider live synthetique avec prompt non
  sensible et cout borne quand le secret/runtime est disponible;
- si le provider live est indisponible, la cloture ne revendique pas de preuve
  provider live;
- PNG/JPEG/WebP doivent etre prouves par combinaison de live synthetique et
  tests fake deterministes quand le provider ne force pas chaque format;
- scan logs applicatifs borne reel attendu, ou limite documentee explicitement
  comme non bloquante dans le verdict;
- cleanup distant/local exact des images synthetiques obligatoire.

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
- `nextcloud_sync_state` doit etre fail-closed par defaut:
  `DEFAULT 'sync_error'`.
- `linked` ne peut etre ecrit qu'apres preuve distante exacte puis persistance
  locale reussie.
- La cible distante exacte `target_name_internal` est obligatoire et ne doit
  jamais etre reconstruite depuis display name, prompt, hash ou projection
  technique.
- Aucun fallback navigateur durable ne doit etre vendu comme succes V1.
- Pas de mutation Documents, Notes ou Exports par opportunisme.
- Pas d'injection chat automatique.
- Pas de Memory/RAG/Identity/Summary.

## Lots proposes

Lots 0 et 1 sont coches par audit puis spec read-only/docs-only. Les Lots 2+
restent ouverts et doivent appliquer
`app/docs/states/specs/frida-v1-generated-images-contract.md`.

### Lot 0 - Audit existant read-only/docs-only

- [x] Relire `app/tools/image_generation.py`.
- [x] Relire `POST /api/tools/image-generation` dans `app/server.py`.
- [x] Relire `app/web/chat_image_generation.js`, `app/web/index.html` et les
  styles `image-generation-*`.
- [x] Relire les tests image generation backend, serveur, frontend et browser.
- [x] Relire les surfaces images actives / Documents visuels sans les confondre
  avec Images generees.
- [x] Identifier les patterns reutilisables: validation, generateurs, logs,
  extraction data URL, download navigateur, tests.
- [x] Identifier les patterns a eviter: route outil globale, data URL comme
  stockage, absence de dossier, absence de read-model, prompt brut.
- [x] Inventorier les champs actuellement exposes au frontend et aux logs.
- [x] Produire un audit content-free sous `app/docs/states/audits/`:
  `app/docs/states/audits/frida-v1-generated-images-lot0-audit-2026-06-19.md`.
- [x] Ne livrer aucun runtime, aucune migration, aucun acces Nextcloud, aucune
  generation live.

### Lot 1 - Spec source-of-truth Images V1

- [x] Creer `app/docs/states/specs/frida-v1-generated-images-contract.md`.
- [x] Fermer toutes les decisions produit ci-dessus avant runtime.
- [x] Definir le modele produit Image generee V1.
- [x] Graver le rattachement obligatoire de toute image persistante a
  `workspace_folders.id`.
- [x] Definir la cible normative `/Frida/<dossier>/Images`.
- [x] Definir la politique de prompt: non-stockage durable du prompt brut, du
  resume et des hash deductibles.
- [x] Definir les formats V1 autorises.
- [x] Definir les limites de prompt, data URL, bytes, dimensions et timeout.
- [x] Fixer le nom du modele local/read-model Images V1 dedie obligatoire.
- [x] Definir les routes/API autorisees sous namespace dossier.
- [x] Definir la politique de nommage, collision, versioning et suppression.
- [x] Definir les projections utilisateur et technique content-free.
- [x] Definir le catalogue initial de reason codes.
- [x] Definir les criteres Lot Z.
- [x] Ne livrer aucun runtime.

### Lot 2 - Modele local / read-model images

- [x] Livrer le read-model Images V1 dedie obligatoire decide par la spec Lot
  1.
- [x] Garder ce read-model distinct de `workspace_files`,
  `workspace_folder_exports`, Notes, Documents et Exports.
- [x] Rattacher strictement chaque image a `workspace_folders.id`.
- [x] Representer statut local, statut Nextcloud, format, MIME, dimensions,
  tailles, generateur, provider model, refs/hashs et reason codes.
- [x] Definir `target_name_internal` comme cible distante exacte, interne,
  serveur-owned et obligatoire.
- [x] Definir `target_ref` comme ref/hash content-free separee pour projections
  techniques.
- [x] Interdire toute reconstruction de cible distante depuis display name,
  prompt, hash ou projection technique.
- [x] Declarer `nextcloud_sync_state DEFAULT 'sync_error'` ou un equivalent
  fail-closed explicitement teste.
- [x] Ne passer `nextcloud_sync_state` a `linked` qu'apres preuve distante
  exacte et persistance locale reussie.
- [x] Appliquer la politique prompt decidee par Lot 1, sans prompt brut par
  defaut.
- [x] Ne pas stocker les bytes image en DB applicative.
- [x] Ne pas stocker de data URL/base64.
- [x] Produire projections utilisateur et technique content-free.
- [x] Fail-closed si le store images est indisponible.
- [x] Tester statut, projections, anti-fuite, prompt policy et deleted.
- [x] Ne pas contacter Nextcloud/WebDAV live.

Preuve Lot 2:

- modules livres: `app/core/workspace_folder_generated_images.py`,
  `app/core/workspace_folder_generated_images_store.py`,
  `app/core/workspace_folder_generated_images_schema.py`,
  `app/core/workspace_folder_generated_image_projection.py` et
  `app/core/workspace_folder_generated_image_reason_codes.py`;
- suite dediee:
  `app/tests/unit/core/test_workspace_folder_generated_images.py`;
- backup DB applicative avant migration:
  `/opt/platform/_codex_reports/frida-v1-generated-images-lot2-db-backup-20260619T202702Z.dump`;
- Lot 2 ne livre aucune route, aucune UI, aucune generation provider et aucun
  acces Nextcloud/WebDAV live.

Correctif Lot 2.1:

- `target_ref` technique est strictement limite a
  `generated-image-target:<hash12>`;
- si un `target_ref` stocke est invalide, il est recompute depuis
  `target_name_internal` seulement si cette cible interne est valide;
- une cible interne et une ref invalides ne peuvent jamais ressortir brutes en
  projection technique;
- `tombstone_generated_image()` leve une erreur content-free dediee en cas de
  panne DB au lieu de retourner `None` silencieusement;
- le schema impose le format serveur-owned de `target_name_internal` et la forme
  structuree de `target_ref`;
- Lot 2.1 ne livre aucune route, aucune UI, aucune generation provider et aucun
  acces Nextcloud/WebDAV live.

### Lot 3 - Stockage Nextcloud-first sous Images

- [x] Adapter le moteur de generation existant ou extraire une capacite provider
  reusable sans passer par un contrat `image_data_url` navigateur comme stockage.
- [x] Exiger `workspace_folder` existant et `linked`.
- [x] Refuser `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted`.
- [x] Verifier `Images` par `PROPFIND Depth: 0` et confirmation collection.
- [x] Generer ou recevoir l'image selon la spec Lot 1.
- [x] Decoder/valider l'image selon les formats et limites V1 avant ecriture.
- [x] Ecrire dans Nextcloud avec strategie anti-ecrasement.
- [x] Accepter uniquement une creation sure.
- [x] Traiter les statuts update-like comme conflit/refus, jamais comme succes.
- [x] Persister le read-model local seulement apres succes distant.
- [x] Considerer le succes produit seulement si generation provider, validation
  image, ecriture Nextcloud-first et persistance read-model reussissent toutes.
- [x] Si le provider reussit mais que le stockage durable echoue, refuser
  content-free: aucun read-model `linked`, aucun fallback navigateur durable
  vendu comme succes V1, aucune data URL persistee.
- [x] Si ecriture distante reussit puis persistance locale echoue, tenter une
  compensation distante strictement bornee a la cible creee.
- [x] Ne jamais exposer prompt brut, bytes, data URL, base64, cible DAV, URL DAV,
  XML, ETag brut ou payload provider/WebDAV dans logs/projections/preuves.
- [x] Produire une preuve live synthetique content-free avec cleanup exact:
  `app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lot3-nextcloud-first-20260620T083741Z.jsonl`.

Livraison Lot 3:

- route namespaced livree: `POST /api/workspace-folders/<folder_id>/generated-images`;
- modules dedies livres pour provider V1, validation V1, client WebDAV Images,
  runtime Nextcloud-first et service HTTP;
- provider live synthetique prouve, sans prompt brut ni data URL dans
  l'artefact;
- cleanup distant exact + tombstone local prouves;
- cas update-like, stockage KO apres provider OK et rollback distant couverts
  par tests unitaires fake.

Correctif Lot 3.1:

- les projections/API ne sortent plus le `content_hash` complet interne;
- seul `content_hash_short` reste exposable dans les projections content-free
  prevues;
- l'acceptation JPEG/WebP est prouvee par tests de validation et runtime fake:
  JPEG produit `image_format=jpeg` et cible `.jpg`, WebP produit
  `image_format=webp` et cible `.webp`;
- aucun nouveau smoke live provider ou Nextcloud n'est ajoute.

### Lot 4 - Liste / lookup / projection utilisateur

- [x] Ajouter la liste des images generees d'un dossier depuis le read-model
  local uniquement.
- [x] Ajouter lookup par UUID exact.
- [x] Exiger dossier valide et `linked`.
- [x] Refuser dossier supprime, non eligible ou panne store.
- [x] Exclure les images `deleted` par defaut.
- [x] Verifier que l'image appartient strictement au dossier du path.
- [x] Ne pas appeler WebDAV/Nextcloud.
- [x] Ne pas lire de bytes image.
- [x] Exposer cote utilisateur titre/nom si autorise, format, taille,
  dimensions, dates, statut et actions disponibles.
- [x] Garder la projection technique sans prompt brut, target brut, ETag brut,
  URL DAV, chemin DAV, XML, bytes, base64 ou data URL.
- [x] Tester liste vide, liste multi-formats, deleted exclu, lookup OK, absent,
  cross-folder, panne store et anti-fuite.

Livraison Lot 4:

- routes namespaced livrees:
  `GET /api/workspace-folders/<folder_id>/generated-images` et
  `GET /api/workspace-folders/<folder_id>/generated-images/<image_id>`;
- liste et lookup lisent uniquement le read-model local
  `workspace_folder_generated_images`;
- aucune lecture provider, Nextcloud, WebDAV, bytes, base64 ou data URL;
- lookup UUID exact uniquement; invalid UUID, absent, cross-folder et deleted
  sont refuses content-free;
- pannes folder store et image store fail-closed, sans fausse liste vide;
- les actions `can_open`, `can_download` et `can_delete` restent `false` avec
  `folder_generated_image_access_not_prepared` tant que Lot 5 n'est pas livre.

### Lot 5 - Open/download/delete image

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
- [ ] Ajouter suppression utilisateur explicite sous namespace dossier.
- [ ] Supprimer distant exact avant tombstone local.
- [ ] Fail-closed si suppression distante echoue.
- [ ] Ne jamais supprimer large ou recursive.
- [ ] Tester absent, deleted, cross-folder, non linked, taille trop grande,
  panne store, panne Nextcloud, headers, suppression et anti-fuite.

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

- [ ] Consolider les projections/events techniques content-free quand le lot
  livre une surface qui les consomme.
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
- [ ] Archiver cette TODO seulement si le verdict final est conforme au contrat
  Lot 1.
- [ ] Ne pas vendre une preuve plus large que ce qui est reellement execute.

## Reason codes initiaux a stabiliser

Catalogue stabilise par la spec Lot 1:

- `folder_generated_image_folder_invalid`;
- `folder_generated_image_folder_deleted`;
- `folder_generated_image_folder_not_linked`;
- `folder_generated_image_folder_not_eligible`;
- `folder_generated_image_images_target_missing`;
- `folder_generated_image_images_target_not_collection`;
- `folder_generated_image_images_target_unavailable`;
- `folder_generated_image_client_image_id_forbidden`;
- `folder_generated_image_client_workspace_folder_id_forbidden`;
- `folder_generated_image_prompt_missing`;
- `folder_generated_image_prompt_too_large`;
- `folder_generated_image_generator_unsupported`;
- `folder_generated_image_aspect_ratio_unsupported`;
- `folder_generated_image_size_unsupported`;
- `folder_generated_image_provider_timeout`;
- `folder_generated_image_provider_error_redacted`;
- `folder_generated_image_provider_no_image`;
- `folder_generated_image_provider_payload_invalid`;
- `folder_generated_image_data_url_invalid`;
- `folder_generated_image_data_url_too_large`;
- `folder_generated_image_format_unsupported`;
- `folder_generated_image_mime_invalid`;
- `folder_generated_image_too_large`;
- `folder_generated_image_dimensions_invalid`;
- `folder_generated_image_name_invalid`;
- `folder_generated_image_name_conflict`;
- `folder_generated_image_create_ok`;
- `folder_generated_image_store_ok`;
- `folder_generated_image_store_failed_redacted`;
- `folder_generated_image_local_persistence_failed`;
- `folder_generated_image_remote_compensation_ok`;
- `folder_generated_image_remote_compensation_failed`;
- `folder_generated_image_list_ok`;
- `folder_generated_image_lookup_ok`;
- `folder_generated_image_lookup_failed`;
- `folder_generated_image_not_found`;
- `folder_generated_image_deleted`;
- `folder_generated_image_not_linked`;
- `folder_generated_image_access_not_prepared`;
- `folder_generated_image_download_ok`;
- `folder_generated_image_open_ok`;
- `folder_generated_image_delete_ok`;
- `folder_generated_image_delete_failed_redacted`;
- `folder_generated_image_nextcloud_error_redacted`.

Interdits:

- reason code contenant un prompt brut;
- reason code contenant un nom cible brut;
- reason code contenant une URL, un chemin, XML, ETag brut, payload, secret ou
  contenu image.

## Preuves attendues

- Audit Lot 0 content-free sous `app/docs/states/audits/`.
- Spec Lot 1 source-of-truth:
  `app/docs/states/specs/frida-v1-generated-images-contract.md`.
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
- Reutilisation comme source.
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

Executer Lot 4 Images V1: liste / lookup / projection utilisateur depuis le
read-model local, sans lecture Nextcloud/WebDAV et sans bytes image.
