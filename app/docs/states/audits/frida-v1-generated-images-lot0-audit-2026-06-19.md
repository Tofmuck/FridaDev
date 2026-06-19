# Frida V1 - Generated Images Lot 0 audit - 2026-06-19

Statut: audit read-only/docs-only Lot 0.
Classement: `app/docs/states/audits/`
TODO source: `app/docs/todo-todo/product/frida-v1-generated-images-todo.md`

## Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan pour Lot 0 est un audit content-free de l'existant, sans
runtime, sans route, sans UI, sans migration DB, sans acces Nextcloud/WebDAV,
sans generation provider live, sans smoke et sans rebuild. Les lots runtime
Images V1 doivent attendre la spec source-of-truth Lot 1 et ses decisions
produit fermees.

Verdict Lot 0:

- audit existant realise;
- aucune image utilisateur lue ou copiee;
- aucun prompt brut repris;
- aucun contenu image brut conserve;
- aucune generation live;
- aucune decision produit fermee par opportunisme.

## Sources relues

Docs et contrats:

- `AGENTS.md`;
- `app/docs/todo-todo/product/frida-v1-generated-images-todo.md`;
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`;
- `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`;
- `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`;
- `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`;
- `app/docs/states/specs/frida-v1-exports-contract.md`;
- `app/docs/todo-done/product/frida-v1-exports-todo.md`;
- `app/docs/todo-done/product/fridadev-image-generation-openrouter-todo.md`;
- `app/docs/todo-done/product/fridadev-active-image-documents-todo.md`;
- `app/docs/states/architecture/fridadev-full-pipeline-overview-2026-05-19.md`.

Code runtime et UI:

- `app/tools/image_generation.py`;
- `app/server.py`;
- `app/web/chat_image_generation.js`;
- `app/web/index.html`;
- `app/web/styles.css`;
- `app/web/app.js`;
- `app/core/active_document_image_validation.py`;
- `app/core/active_document_prompt_lane.py`;
- `app/core/active_conversation_documents.py`;
- `app/core/active_document_upload_service.py`;
- `app/core/workspace_file_selection_prompt.py`;
- `app/core/workspace_folder_documents.py`;
- `app/core/workspace_folder_standard_subfolders.py`;
- `app/observability/active_documents_observability.py`.

Tests relus ou inventories:

- `app/tests/unit/tools/test_image_generation.py`;
- `app/tests/test_server_image_generation.py`;
- `app/tests/unit/frontend_chat/test_image_generation_module.js`;
- `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`;
- `app/tests/test_server_active_documents_contract.py`;
- `app/tests/test_server_chat_active_image_documents_contract.py`;
- `app/tests/unit/core/test_active_document_prompt_lane.py`;
- `app/tests/unit/core/test_active_document_non_contamination_lot5.py`;
- `app/tests/unit/logs/test_active_documents_observability_lot7.py`;
- inventaire des tests actifs image / Documents visuels via recherche `rg`.

Recherches executees:

- generation image: `image_generation`, `image-generation`, `image_data_url`,
  `generated_image`, `generated image`;
- prompt/image/storage: `prompt.*image`, `image.*prompt`, `base64`, `data URL`,
  `data_url`, `blob`, `storage_key`, `thumbnail`, `mime_type`, `width`,
  `height`;
- sous-dossier et docs: `Images`.

## Surfaces runtime existantes

### Outil lateral V0 image generation

Surface:

- backend: `app/tools/image_generation.py`;
- route: `POST /api/tools/image-generation`;
- garde serveur: route presente dans `_GUARDED_TOOLS_PATHS`, avec appel couteux
  refuse avant provider pour un pair non fiable ou un proxy sans identite;
- transport provider: OpenRouter Chat Completions via le transport LLM partage;
- frontend: `app/web/chat_image_generation.js`;
- UI: panneau `#imageGenerationPanel`;
- styles: bloc `image-generation-*`.

Contrat observe:

- payload entrant: `generator_key`, prompt utilisateur, `aspect_ratio`,
  `image_size`;
- allowlist backend: quatre generateurs V0, aucun `openrouter/auto`;
- allowlist frontend: table miroir avec les memes quatre generateurs;
- limites backend: prompt non vide, `2000` caracteres maximum, timeout `180`
  secondes, plafond de reponse inline `6_000_000` caracteres;
- formats backend: accepte tout MIME `image/*` retourne par le provider si la
  reponse inline passe la regex et la limite; les tests V0 couvrent au moins
  PNG et un rejet non-image;
- contrat succes: retourne `ok`, generateur, modele, libelle de prix, format
  demande, champ `image_data_url`, MIME, modele provider et usage/cout si
  disponible;
- erreurs normalisees: generateur invalide, prompt invalide, ratio invalide,
  taille invalide, erreur provider, absence d'image, image inline invalide,
  timeout;
- logs: evenements demande/succes/echec avec generateur, modele, ratio, taille,
  statut, code erreur, latence, statut provider, modele provider, usage/cout,
  MIME et taille de la reponse inline;
- absence de persistance serveur;
- absence de `workspace_folder_id`;
- absence de read-model image;
- absence de cible `/Frida/<dossier>/Images`;
- absence de Nextcloud/WebDAV.

Conclusion V0:

- reutilisable comme moteur/facade provider sous reserve d'extraction hors
  contrat navigateur;
- insuffisant comme Images V1 durable;
- dangereux si le champ `image_data_url` reste la definition du succes produit.

### Route serveur

`POST /api/tools/image-generation` delegue directement a
`generate_image_response()`. La route ne recoit pas de `folder_id` dans le path,
ne verifie pas un `workspace_folder`, ne connait pas l'etat `linked`, ne verifie
pas le sous-dossier `Images`, ne fait aucun rollback et ne persiste rien.

Pour Images V1, cette route doit rester une surface outil V0. Les futures routes
produit Images V1 doivent etre namespaced sous le dossier Frida, selon la spec
Lot 1.

## UI actuelle

Surfaces:

- bouton outil dans le composer;
- panneau lateral natif avec textarea prompt, select modele, select ratio,
  select taille, statut, pricing, resultat, preview et bouton de telechargement;
- integration dans `app/web/app.js` via `createImageGenerationController()`.

Comportement observe:

- le frontend envoie uniquement `generator_key`, prompt, ratio et taille a
  `/api/tools/image-generation`;
- aucun `workspace_folder_id` n'est envoye;
- aucune conversation ou dossier actif n'est requis;
- le resultat est affiche depuis `image_data_url`;
- le telechargement est un telechargement navigateur local;
- le nom de fichier de telechargement est derive cote frontend depuis le MIME et
  un timestamp local;
- le panneau ne poste pas dans `/api/chat`;
- les tests browser prouvent que l'outil image n'ajoute pas de message au fil
  de chat pendant ce flux.

Points UI utiles:

- patterns de panneau sobre, etats loading/error/success, preview contrainte,
  bouton de telechargement;
- tests frontend unitaires pour table generateurs, fallback de selection,
  pricing prudent et metadonnees compactes.

Points UI a eviter pour Images V1:

- l'absence de contexte dossier;
- la duplication non source-of-truth des tables generateurs frontend/backend;
- le telechargement local comme preuve de durabilite;
- l'affichage direct d'une image non durable comme succes produit V1.

## Tests existants

Tests V0 image generation:

- unit backend: allowlist, rejet generateur invalide, prompt requis/limite,
  ratio/taille par generateur, payload provider, headers/attribution, image
  absente, reponse non-image, logs sans prompt ni contenu image brut;
- serveur: delegation de route, garde d'acces, refus avant provider, erreur
  normalisee sans secret;
- frontend unit: table generateurs, absence de taille non exposee pour le
  generateur prudent, fallback ratio/taille, nom de telechargement, pricing
  prudent, metadonnees compactes;
- browser smoke: panneau image, POST outil, preview, telechargement local,
  absence de POST `/api/chat`, etats erreur, responsive desktop/mobile.

Tests actifs image / Documents visuels:

- upload PNG/JPEG/WebP actif;
- refus GIF V0;
- refus extension trompeuse;
- refus image trop petite, trop lourde ou dimensions invalides;
- retrait avec effacement des bytes image actifs;
- injection multimodale uniquement au tour provider;
- exclusion si modele incompatible, bytes absents ou payload trop lourd;
- preuves anti-contamination: pas de payload image dans conversation
  persistante, Memory, Identity, Summary, traces ou observabilite;
- observabilite active-documents sans contenu brut.

Limite de ces tests pour Images V1:

- ils prouvent des surfaces V0 ou conversationnelles;
- ils ne prouvent pas de stockage durable sous `Images`;
- ils ne prouvent pas de read-model Images V1;
- ils ne prouvent pas de Nextcloud-first, no-overwrite ni rollback Images V1.

## Logs / observabilite actuelle

Outil V0:

- logger dedie `frida.image_generation`;
- log demande, succes et echec;
- champs utiles: generateur, modele, ratio, taille, statut, reason/error code,
  latence, statut provider, modele provider, usage/cout, MIME et taille de la
  reponse inline;
- le prompt n'est pas logge par le module;
- le contenu image brut n'est pas logge par le module;
- le payload provider brut n'est pas logge;
- le secret provider n'est pas logge.

Points a corriger/adapter pour Images V1:

- la taille de reponse inline V0 est un signal utile mais ne suffit pas comme
  preuve de bytes stockes durablement;
- l'usage/cout provider doit rester optionnel et redacted si la forme provider
  evolue;
- les logs Images V1 devront ajouter des refs content-free de dossier/image,
  statut de stockage, hash court, MIME, dimensions et reason code, sans titre
  cible brut ni chemin distant.

Images actives:

- observabilite `active_documents` deja content-free pour decisions de prompt;
- l'observabilite peut inclure MIME, extension, taille, dimensions, hash court,
  statut, reason code, modele provider et ordre de payload;
- elle ne doit pas etre reutilisee comme preuve Images V1 durable, car elle
  decrit des pieces actives de conversation.

## Images actives / Documents visuels

Validation active image:

- formats V0 acceptes comme images actives: PNG, JPEG, WebP;
- GIF reconnu mais refuse en V0;
- SVG n'est pas pris en charge par le sniff actif actuel;
- taille source maximale active: `32 MiB`;
- body multipart maximal avant parsing: `40 MiB`;
- dimensions minimales: `32 x 32`;
- dimension maximale par cote: `16000`;
- surface maximale: `100 megapixels`;
- hash court disponible;
- sniff conteneur/dimensions sans decodage complet provider.

Prompt lane:

- data inline provider construite seulement au moment du payload multimodal;
- ordre multimodal text puis image;
- modele compatible allowliste;
- plafond provider pour images actives: `25 MiB`;
- exclusion entiere si modele non compatible, bytes absents ou payload trop
  lourd;
- aucune troncature silencieuse.

Documents visuels / workspace files:

- les fichiers workspace images relus comme selection de dossier restent des
  documents/fichiers selectionnes, pas des images generees;
- `workspace_files` porte stockage et selection Documents, pas le read-model
  Images V1;
- la projection Documents sait produire une projection technique content-free,
  mais elle doit inspirer Images V1 sans absorber son modele.

Conclusion:

- reutiliser les validateurs de format/dimensions avec prudence;
- ne pas reutiliser `active_conversation_documents` comme stockage durable;
- ne pas reutiliser `workspace_files` comme read-model Images V1.

## Sous-dossier standard Images

Le socle folders definit deja:

```text
Documents, Notes, Exports, Images
```

`workspace_folder_standard_subfolders.py` fournit le pattern:

- `Images` est un sous-dossier standard au meme niveau que `Documents`, `Notes`
  et `Exports`;
- verification status-only par sous-dossier;
- une reponse `207` seule ne suffit pas;
- la ressource doit etre confirmee comme collection;
- aucun listing large Nextcloud;
- pas de DB Nextcloud directe;
- observations et preuves avec refs/hashs et reason codes content-free.

Patterns applicables a Images V1:

- verifier `Images` avant ecriture;
- ecrire en Nextcloud-first;
- accepter uniquement une creation sure;
- persister localement apres succes distant;
- rollback/compensation stricte si la persistance locale echoue apres creation
  distante;
- si provider OK mais stockage durable KO, refuser le succes produit.

## Patterns reutilisables

- Allowlist de generateurs V0 et validation `generator_key`;
- limites prompt/timeout et erreurs normalisees;
- attribution OpenRouter par generateur;
- extraction de la premiere image provider;
- validation MIME image et limites de reponse inline comme premiere garde;
- logs V0 sans prompt brut ni contenu image brut;
- UI panneau, etats, preview et telechargement comme experience de base;
- sniff PNG/JPEG/WebP et dimensions depuis `active_document_image_validation`;
- hash court, tailles, dimensions et reason codes comme projection technique;
- tests anti-fuite avec sentinelles synthetiques;
- pattern Nextcloud folders/Notes/Exports: collection obligatoire, no overwrite,
  read-model apres succes distant, compensation stricte.

## Patterns a adapter

- `image_data_url` doit devenir un objet transitoire interne ou une entree de
  validation, pas le contrat final Images V1;
- la table generateurs doit avoir une source-of-truth unique ou un mecanisme de
  synchronisation teste entre backend et frontend;
- les formats V0 provider et les formats actifs ne sont pas identiques: Lot 1
  doit trancher PNG/JPEG/WebP/SVG/GIF;
- les limites V0 (`2000` chars prompt, timeout `180` s, reponse inline
  `6_000_000` chars) doivent etre redecidees pour un flux durable;
- l'usage/cout provider peut etre conserve cote utilisateur, mais seulement
  selon une projection content-free decidee;
- l'UI actuelle peut inspirer la creation, mais doit devenir folder-scoped et
  server-authoritative;
- les headers/download devront suivre les patterns Exports/Documents, pas le
  simple clic navigateur V0.

## Patterns a eviter

- route globale `/api/tools/image-generation` comme route produit Images V1;
- succes V1 base sur preview ou telechargement navigateur;
- stockage durable sous forme inline/base64/data URL;
- prompt brut en DB, logs, JSONL ou projection technique;
- read-model `workspace_files`, `workspace_folder_exports` ou Notes;
- image generee automatiquement transformee en document actif;
- injection chat automatique apres generation;
- listing large Nextcloud;
- DB Nextcloud directe;
- overwrite silencieux ou renommage automatique non decide;
- propagation du payload provider brut dans logs/preuves/docs.

## Risques produit avant Lot 1

- Format ambiguity: V0 provider peut retourner plus large que les formats
  validates pour images actives.
- Prompt policy: aucune politique de stockage prompt n'est encore fermee.
- Success ambiguity: l'outil V0 affiche une image non durable; Images V1 doit
  refuser tout succes sans stockage durable et read-model.
- Model table drift: backend et frontend portent deux tables V0 proches mais
  separees.
- Observability drift: les logs V0 parlent de reponse inline, pas de cible
  distante ni d'etat durable.
- Product confusion: active images, Documents visuels et generated images ont
  des parcours proches mais des contrats differents.

## No-go avant Lot 1

- Pas de runtime Images V1 sans spec source-of-truth;
- pas de stockage durable sans politique prompt fermee;
- pas de stockage durable sans allowlist formats fermee;
- pas de read-model sans table dediee nommee;
- pas de create si le dossier n'est pas `linked`;
- pas de succes si provider OK mais stockage durable KO;
- pas de route produit globale;
- pas de Nextcloud write sans verification `Images` collection;
- pas de prompt brut, contenu image brut, payload provider brut, secret ou
  chemin distant dans preuves techniques.

## Inputs pour Lot 1

Lot 1 doit fermer explicitement:

- politique prompt: brut, resume, hash, redaction ou non-stockage;
- formats persistables V1: PNG/JPEG/WebP/SVG/GIF/autre;
- traitement SVG et GIF;
- limites: prompt, reponse provider inline, bytes stockes, dimensions, timeout;
- nom du read-model/table Images V1 dedie;
- etats locaux et Nextcloud;
- routes namespaced sous dossier;
- politique de nommage et collision;
- suppression/retention;
- presence ou absence de miniature V1;
- open/download et headers;
- projection utilisateur vs projection technique;
- reason codes finaux;
- criteres Lot Z et portee des smokes/log scans.

## Anti-fuite Lot 0

Cet audit ne conserve pas:

- prompt brut;
- image brute;
- bytes image;
- payload provider brut;
- secret, token, cookie, app-password ou Authorization;
- chemin DAV, URL DAV ou XML brut;
- contenu utilisateur reel.

Les termes techniques `image_data_url`, MIME, dimensions, tailles, hashes courts
et reason codes sont cites comme noms de contrat ou categories; aucune valeur
inline brute n'est conservee.
