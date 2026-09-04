# Frida V1 - Generated Images contract

Statut: spec source-of-truth Images generees V1 cloturee pour Frida 1.0; Lots
0/1 docs-only, Lot 2 read-model, Lot 3 creation Nextcloud-first, Lot 4
liste/lookup metadata-only, Lot 5 open/download/delete, Lot 6 UI dossier, Lot
7 observabilite/smokes content-free et Lot Z cloture livres.
Date: 2026-06-20
Archive livraison: `app/docs/todo-done/product/frida-v1-generated-images-todo.md`
Audit Lot 0: `app/docs/states/audits/frida-v1-generated-images-lot0-audit-2026-06-19.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat Documents source: `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
Contrat Notes source: `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
Contrat Exports source: `app/docs/states/specs/frida-v1-exports-contract.md`

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non. Les decisions produit bloquantes sont maintenant fermees dans ce contrat.
Le Lot 1 reste docs-only: aucun runtime, aucune route, aucune migration DB,
aucun acces Nextcloud/WebDAV, aucune generation provider live et aucun rebuild.

Tout lot runtime Images V1 doit appliquer ce contrat. S'il rencontre une
contradiction reelle avec le depot ou une nouvelle decision produit, il doit
s'arreter avant patch, commit et coche de lot, puis ouvrir un micro-lot de
recalage documentaire.

## 2. Modele produit Images V1

Une image generee V1 est un artefact image produit par Frida, rattache a un
dossier Frida produit et range durablement sous le sous-dossier standard
`Images`.

Regle centrale:

```text
workspace_folder linked -> image generee V1 -> /Frida/<dossier>/Images
```

Images V1 ne cree pas une deuxieme notion de dossier, ne depend pas de la DB
Nextcloud et ne remplace pas Documents, Notes, Exports, Biblio, Agenda, Mail,
Memory/RAG, Identity ou Summary.

Une image generee V1 n'est pas:

- un document utilisateur Documents;
- une image active de conversation;
- un export;
- une note;
- un prompt brut;
- une entree Biblio ou Catalogue.

## 3. Frontiere V0 outil lateral / V1 durable

La route V0 suivante reste un outil lateral non persistant:

```text
POST /api/tools/image-generation
```

Elle peut continuer a afficher une image dans le navigateur et permettre un
telechargement local navigateur. Elle ne livre pas Images V1, car elle n'exige
pas de `workspace_folder`, n'ecrit pas sous `Images`, ne verifie pas Nextcloud et
ne persiste aucun read-model Images.

Images V1 doit utiliser uniquement des routes produit namespaced sous dossier.
La route V0 peut inspirer l'appel provider, la validation generateur et les
erreurs, mais le succes V1 n'est jamais defini par `image_data_url` affichee
dans le navigateur.

## 4. Modele local obligatoire

Images V1 exige un read-model applicatif dedie:

```text
workspace_folder_generated_images
```

Cette table est obligatoire, strictement rattachee a `workspace_folders.id` et
distincte de:

- `workspace_files`;
- `workspace_folder_exports`;
- `workspace_folder_notes`;
- Documents;
- Notes;
- Exports;
- `active_conversation_documents`.

Absence de ce read-model = no-go pour create, list, lookup, open, download ou
delete Images V1.

Champs attendus, sans figer la migration exacte:

- `id` UUID serveur-owned;
- `workspace_folder_id`;
- `display_name` user-facing facultatif ou neutre;
- refs/hashes courts du display name pour projections techniques;
- `target_name_internal` obligatoire, exact, serveur-owned et interne;
- `target_ref` content-free obligatoire pour projections techniques;
- `mime_type`;
- format canonique `png`, `jpeg` ou `webp`;
- `byte_size`;
- `width`, `height`;
- hash de contenu interne et hash court expose;
- `generator_key`;
- `provider_model` si disponible;
- `aspect_ratio`, `image_size`;
- signaux prompt content-free definis en section 8;
- `local_state`;
- `nextcloud_sync_state` avec default schema fail-closed
  `DEFAULT 'sync_error'`;
- `deleted_at`;
- `created_at`, `updated_at`;
- `last_reason_code`;
- ETag interne uniquement si utile au transport, avec ref technique separee.

`target_name_internal` est la seule cible distante utilisable pour GET, DELETE,
rollback et compensation. Cette cible exacte ne doit jamais etre reconstruite
depuis `display_name`, prompt, hash, `target_ref` ou projection technique.

Implementation Lot 2:

- le schema applicatif est porte par
  `app/core/workspace_folder_generated_images_schema.py`;
- le store local est porte par
  `app/core/workspace_folder_generated_images_store.py`;
- le read-model est cree par `conversations_maintenance.init_catalog_db()` via
  `ensure_schema(cur)`;
- `nextcloud_sync_state` reste `sync_error` par defaut et le store ne conserve
  `linked` que si l'appelant fournit explicitement une preuve distante
  (`remote_proof=true`);
- les projections techniques sont portees par
  `app/core/workspace_folder_generated_image_projection.py` et ne contiennent
  pas `display_name`, cible distante brute, ETag brut, prompt, bytes, base64,
  data URL, payload, DAV/XML/path/URL ou secret.

Durcissement Lot 2.1:

- `target_ref` technique accepte uniquement la forme structuree
  `generated-image-target:<hash12>`;
- une `target_ref` stockee invalide est recomputee depuis
  `target_name_internal` seulement si cette cible interne est valide;
- si la cible interne et la ref stockee sont invalides, la projection technique
  expose une ref vide/redacted et jamais la valeur brute;
- `tombstone_generated_image()` ne masque pas les pannes DB: il leve une erreur
  content-free dediee, sans cause brute chainee;
- la suppression conditionne le tombstone a l'identite durable encore active
  de l'image, du dossier, de la cible interne et de sa `target_ref`; une
  precondition non satisfaite ne produit ni tombstone ni succes;
- le schema applicatif impose le format serveur-owned
  `generated-image-<uuid>.(png|jpg|webp)` pour `target_name_internal` et la
  forme `generated-image-target:<hash12>` pour `target_ref`.

Interdits dans ce read-model:

- prompt brut;
- resume de prompt;
- hash reversible, deductible ou attaquable du prompt;
- bytes image;
- base64;
- data URL;
- payload provider;
- payload WebDAV;
- chemin DAV;
- URL DAV;
- XML brut;
- ETag brut dans les projections;
- secret, token, cookie, app-password ou Authorization.

Etats locaux initiaux:

- `available`;
- `sync_error`;
- `conflict`;
- `deleted`;
- `unavailable`.

Etats Nextcloud initiaux:

- `linked`;
- `sync_error`;
- `conflict`;
- `deleted`;
- `unavailable`.

Default obligatoire du schema Lot 2:

```sql
nextcloud_sync_state TEXT NOT NULL DEFAULT 'sync_error'
```

`linked` ne peut etre ecrit qu'apres preuve distante exacte, creation ou
verification Nextcloud reussie selon le flux concerne, puis persistance locale
reussie. Aucune ligne creee sans preuve distante ne doit sortir comme `linked`.

## 5. Frontiere Nextcloud

La cible normative est:

```text
/Frida/<dossier>/Images/<nom_serveur>.<format>
```

Invariants:

- seul un dossier `linked` peut recevoir une image generee durable;
- les dossiers `local_only`, `sync_pending`, `sync_error`, `conflict` et
  `deleted` sont refuses;
- le sous-dossier `Images` doit exister et etre une collection WebDAV valide;
- `PROPFIND Depth: 0` est obligatoire sur `Images` avant ecriture;
- un statut `207` seul ne prouve rien;
- la reponse XML est parsee en memoire uniquement et jamais exposee;
- aucun listing large Nextcloud;
- aucune DB Nextcloud directe;
- aucun chemin ou URL DAV brut dans logs, docs, JSONL ou projections
  techniques.

## 6. API produit autorisee

Routes autorisees, sous reserve des lots qui les livrent:

```text
POST   /api/workspace-folders/<folder_id>/generated-images
GET    /api/workspace-folders/<folder_id>/generated-images
GET    /api/workspace-folders/<folder_id>/generated-images/<image_id>
GET    /api/workspace-folders/<folder_id>/generated-images/<image_id>/download
GET    /api/workspace-folders/<folder_id>/generated-images/<image_id>/open
DELETE /api/workspace-folders/<folder_id>/generated-images/<image_id>
```

Etat de livraison:

- Lot 3 livre uniquement `POST /api/workspace-folders/<folder_id>/generated-images`;
- Lot 4 livre `GET /api/workspace-folders/<folder_id>/generated-images` et
  `GET /api/workspace-folders/<folder_id>/generated-images/<image_id>`;
- Lot 5 livre `GET .../<image_id>/download`, `GET .../<image_id>/open` et
  `DELETE .../<image_id>`.
- Lot 6 livre une UI dossier qui consomme uniquement ces routes namespaced, sans
  nouvelle route serveur ni reutilisation durable de l'outil V0.

Regles communes:

- `folder_id` du path est l'autorite;
- aucun `workspace_folder_id` du payload ne peut elargir le scope;
- aucun `image_id` client n'est accepte en creation;
- aucune route globale `/api/generated-images*`, `/api/images*` ou
  `/api/tools/*` ne devient route produit Images V1;
- le serveur reste l'autorite sur eligibilite, format, cible et persistance.

## 7. Formats V1

Formats persistables V1:

- PNG: `image/png`, extension `.png`;
- JPEG: `image/jpeg`, extension `.jpg`;
- WebP: `image/webp`, extension `.webp`.

Formats refuses en V1 durable:

- SVG;
- GIF;
- tout MIME `image/*` non allowliste;
- tout format inconnu.

Pas de transcodage automatique V1. Le format retourne par le provider est
conserve seulement s'il appartient a l'allowlist V1. Sinon l'image est refusee.

## 8. Prompt policy V1

Le prompt brut peut exister uniquement:

- dans le navigateur pendant la saisie;
- en memoire serveur pendant la validation et l'appel provider.

Le prompt brut ne doit pas etre persiste comme metadata durable Images V1.
Images V1 ne persiste pas non plus de resume de prompt, ni de hash reversible,
deductible ou exploitable du prompt.

Signaux techniques autorises:

- `prompt_present=true`;
- bucket de longueur: `chars_001_to_250`, `chars_251_to_500`,
  `chars_501_to_1000`, `chars_1001_to_1500`, `chars_1501_to_2000`;
- refus `folder_generated_image_prompt_missing`;
- refus `folder_generated_image_prompt_too_large`.

Interdits:

- prompt brut en DB, logs, JSONL, observabilite, dashboard technique ou reason
  code;
- prompt brut dans projection technique;
- prompt brut dans nom cible;
- prompt brut dans hash durable.

## 9. Limites V1

Limites initiales obligatoires:

- prompt: `2000` caracteres maximum;
- timeout provider: `180` secondes;
- data URL provider transitoire: `22_000_000` caracteres maximum;
- image stockee: `15 MiB` maximum;
- largeur minimale: `32`;
- hauteur minimale: `32`;
- largeur ou hauteur maximale: `16000`;
- surface maximale: `100_000_000` pixels;
- operation complete ou refus;
- aucune troncature silencieuse.

La limite data URL n'est pas un format de stockage. Elle ne sert qu'a refuser
une reponse provider inline trop grande avant decodage et validation.

## 10. Nommage et collision

Le nom cible distant est serveur-owned, neutre et non derive du prompt brut.
Pattern cible:

```text
generated-image-<image_id>.<format>
```

`image_id` est un UUID serveur-owned. Le display name utilisateur est facultatif:
il peut etre explicitement fourni par l'utilisateur ou genere neutrement par le
serveur, par exemple avec une date et un compteur non sensible. Il ne devient
pas une preuve technique.

Collision cible:

- refus content-free;
- pas d'overwrite;
- pas de renommage automatique silencieux;
- pas de versioning implicite.

## 11. Creation et stockage Nextcloud-first

Succes Images V1 = toute la chaine suivante reussit:

1. provider OK;
2. extraction de l'image OK;
3. validation format/MIME/taille/dimensions OK;
4. verification `Images` collection OK;
5. creation distante Nextcloud sure OK;
6. persistance read-model OK.

Si le provider retourne une image mais que le stockage durable echoue, le verdict
produit est un echec/refus content-free:

- aucun read-model `linked`;
- aucune data URL persistee;
- aucun fallback navigateur durable vendu comme succes V1.

Ecriture distante:

- PUT exact vers la cible serveur-owned;
- strategie anti-ecrasement obligatoire;
- creation sure uniquement;
- tout statut update-like ou cible existante = conflit/refus;
- pas de listing Nextcloud.

Si l'ecriture distante reussit puis la persistance locale echoue:

- tenter la suppression exacte uniquement sous `If-Match` avec l'unique ETag
  fort, syntaxiquement valide et conserve exactement, renvoye par cette
  creation;
- wildcard `*`, ETag faible, liste, valeur non citee, malformee ou hors borne
  valent propriete non prouvee sans DELETE; sans ETag, sur refus de precondition
  ou resultat ambigu, conserver la cible et signaler le reliquat content-free;
- ne jamais supprimer large ni retenter par un DELETE inconditionnel;
- si compensation distante reussit, retourner un echec content-free explicite;
- si compensation distante echoue, retourner un echec partiel content-free;
- ne jamais masquer une divergence local/distant.

Implementation Lot 3:

- modules dedies: provider V1, validation V1, client WebDAV Images, runtime
  Nextcloud-first et service HTTP;
- preuve live:
  `app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lot3-nextcloud-first-20260620T083741Z.jsonl`;
- cas update-like, provider OK mais stockage KO et rollback distant couverts par
  tests unitaires fake;
- aucune route globale `/api/images*` ou `/api/generated-images*` livree.

Correctif Lot 3.1:

- `content_hash` complet reste un champ interne read-model uniquement et ne doit
  jamais sortir dans les projections/API;
- `content_hash_short` est la seule reference de contenu exposable lorsque la
  projection content-free en a besoin;
- l'acceptation PNG/JPEG/WebP est prouvee par tests de validation V1; le runtime
  fake prouve aussi que JPEG produit une cible `.jpg` et WebP une cible `.webp`;
- cette preuve ne remplace pas un smoke live provider supplementaire.

## 12. Liste et lookup

Liste:

- depuis `workspace_folder_generated_images` uniquement;
- dossier valide et `linked`;
- images `deleted` exclues par defaut;
- aucun appel Nextcloud/WebDAV;
- aucun byte image lu.
- panne store = fail-closed, pas liste vide mensongere.

Lookup:

- par UUID exact;
- verifier l'appartenance stricte au dossier du path;
- refuser absent, deleted, cross-folder ou dossier non eligible;
- panne store = fail-closed, pas liste vide.

Lookup par titre/critere reste hors V1.

Implementation Lot 4:

- liste et lookup metadata-only sont livres via les routes namespaced dossier;
- invalid UUID est refuse avec `folder_generated_image_id_invalid`;
- absence, cross-folder et deleted sont distingues sans exposer d'entrailles
  techniques;
- les projections utilisateur exposent nom, format, taille, dimensions, dates,
  statuts et actions;
- les projections techniques restent sans prompt brut, target brut, ETag brut,
  URL DAV, chemin DAV, XML, bytes, base64, data URL, `content_hash` complet ou
  secret;
- `can_open`, `can_download` et `can_delete` valent `true` uniquement pour une
  image active, non deleted, `nextcloud_sync_state=linked`, rattachee au dossier
  du path, avec cible interne exacte et format V1 valide;
- les images non linked, deleted, cible invalide ou dossier non linked gardent
  les actions `false` avec reason code content-free;
- aucun provider, Nextcloud ou WebDAV n'est appele par liste/lookup.

## 13. Open/download

Download et open exigent:

- action explicite;
- dossier `linked`;
- image active, non deleted, meme dossier;
- `nextcloud_sync_state=linked`;
- cible distante exacte issue du read-model interne;
- GET WebDAV exact;
- aucun listing Nextcloud;
- limite `15 MiB`, complet ou refus;
- pas de troncature silencieuse;
- revalidation des bytes distants comme PNG/JPEG/WebP avant service;
- refus si le MIME/format distant ne correspond pas au read-model local.

Headers HTTP:

- `X-Content-Type-Options: nosniff`;
- `Cache-Control: private, no-store`;
- `Content-Type` allowliste;
- `Content-Disposition` sobre.

Le nom utilisateur peut etre utilise dans `Content-Disposition` si la surface
utilisateur l'autorise. Les headers ne contiennent jamais prompt brut, cible
distante brute, URL DAV, ETag brut ou secret.

Lot 5 livre `Content-Disposition: inline` pour open et
`Content-Disposition: attachment` pour download, avec nom de fichier
user-facing safe et sans reconstruire ni exposer `target_name_internal`.
Preuve live Lot 5:
`app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lot5-content-access-20260620T114646Z.jsonl`.

## 14. Suppression V1

La suppression utilisateur V1 est autorisee uniquement comme action explicite
sous route namespaced.

Ordre obligatoire:

1. verifier dossier, image, appartenance, etat actif et `linked`;
2. DELETE distant exact de `target_name_internal`;
3. tombstone local conditionnel seulement apres reponse distante 2xx ou 404
   de ce DELETE exact.

Regles:

- pas de suppression large;
- pas de suppression recursive;
- pas de listing Nextcloud;
- echec distant = fail-closed, pas de tombstone local mensonger;
- un 2xx signifie que la suppression distante a ete effectuee;
- un 404 provenant du meme DELETE exact signifie seulement que cette cible est
  deja absente; il permet de terminer le tombstone, sans pretendre a une
  nouvelle suppression distante;
- timeout, panne transport, 401, 403, 5xx ou statut ambigu n'autorisent jamais
  le tombstone;
- le tombstone verifie atomiquement l'image, le dossier, la cible interne,
  `target_ref`, `deleted_at IS NULL`, l'etat local `available` et l'etat distant
  `linked`; zero ligne retournee est un echec content-free;
- succes distant puis echec tombstone local = divergence explicite
  content-free;
- cleanup synthetique de smokes autorise avec cible exacte.

Lot 5 livre la suppression remote-first sous
`DELETE /api/workspace-folders/<folder_id>/generated-images/<image_id>`:
aucun prefix delete, aucun listing Nextcloud et aucune suppression hors cible
exacte persistée.

Durcissement L5.3 du 4 septembre 2026:

- le retry apres un DELETE 2xx suivi d'un echec SQL accepte uniquement le 404
  du DELETE exact reconstruit depuis la ligne durable encore active;
- `folder_generated_image_delete_ok` decrit le chemin 2xx et
  `folder_generated_image_remote_already_missing` le chemin 404 deja absent;
- la ligne deja tombstonee est refusee avant WebDAV et ne declenche aucun
  DELETE supplementaire;
- aucun GET, PROPFIND, listing, retry automatique, verrou SQL pendant le reseau
  ou nouvelle persistance n'est ajoute.

Cette sequence n'est pas une transaction distribuee entre Nextcloud et SQL.
Un arret brutal entre le DELETE et le tombstone peut laisser la ligne active;
le retry exact referme cette fenetre lorsque l'absence distante est prouvee,
sans supprimer logiquement une identite locale devenue differente.

## 15. Reuse, chat et thumbnail

Thumbnail:

- aucune miniature persistante en V1;
- pas de cache thumbnail;
- l'UI peut afficher l'image via open/download explicite ou URL routee, pas via
  une miniature durable.

Reuse-as-source:

- hors V1;
- une image generee ne devient pas source d'une nouvelle generation en V1;
- une image generee ne devient pas document actif en V1;
- aucune injection chat automatique.

Open/download restent les seuls acces contenu Images V1.

UI dossier Lot 6:

- la section Images generees V1 est visible dans le contexte d'un
  `workspace_folder`;
- creation active uniquement pour un dossier `linked`;
- le payload UI de creation contient le prompt courant et options autorisees,
  mais jamais `workspace_folder_id`, `image_id`, bytes, base64, data URL, cible
  distante ou payload technique;
- le module V0 `chat_image_generation.js` doit etre charge avant le panneau
  Images V1 afin que la normalisation `generator_key`, `aspect_ratio` et
  `image_size` soit disponible dans le navigateur reel;
- open/download/delete utilisent les routes namespaced Lot 5 et les flags
  serveur `can_open`, `can_download` et `can_delete`;
- delete exige une confirmation humaine et ne fait pas de suppression optimiste;
- l'UI n'affiche pas prompt brut apres creation, bytes, base64, data URL, cible
  interne, `target_ref`, DAV/path/URL, ETag, `content_hash` complet ou payload
  provider;
- l'outil lateral V0 `/api/tools/image-generation` reste separe et ne devient
  pas surface durable Images V1.

## 16. Projections

Projection utilisateur autorisee:

- `id`;
- display name utilisateur ou neutre;
- format;
- MIME;
- taille;
- dimensions;
- generateur libelle;
- date de creation;
- statut utilisateur;
- actions `can_open`, `can_download`, `can_delete`;
- reason label utilisateur sobre.

Projection technique autorisee:

- `image_ref`;
- `folder_ref`;
- `target_ref`;
- format;
- MIME;
- taille;
- dimensions;
- hash court de contenu;
- `generator_key`;
- `provider_model` si non sensible;
- `aspect_ratio`, `image_size`;
- bucket de longueur prompt;
- `prompt_present`;
- statuts;
- reason code;
- classes HTTP abstraites.

Interdits dans projection technique, logs, JSONL, docs de preuve et dashboard
technique:

- prompt brut;
- image brute;
- bytes image;
- base64;
- data URL;
- target brut;
- chemin DAV;
- URL DAV;
- XML;
- ETag brut;
- payload provider;
- payload WebDAV;
- secret, token, cookie, app-password, Authorization.

## 17. Reason codes finaux

Catalogue V1:

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
- `folder_generated_image_remote_compensation_missing`;
- `folder_generated_image_remote_already_missing`;
- `folder_generated_image_remote_compensation_precondition_failed`;
- `folder_generated_image_remote_compensation_ownership_unverified`;
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

Un reason code ne contient jamais prompt, titre, cible, chemin, URL, XML, ETag,
payload, contenu image ou secret.

## 18. Observabilite content-free

Les events Images V1 doivent etre utiles sans fuite:

- operation;
- image_ref;
- folder_ref;
- generator_key;
- format;
- MIME;
- taille;
- dimensions;
- prompt_present;
- prompt_length_bucket;
- statut local;
- statut Nextcloud;
- reason code;
- classe HTTP distante;
- latence;
- verdict de compensation.

Les logs applicatifs doivent refuser ou redacter toute cause brute provider ou
transport qui contient contenu, prompt, cible distante, payload ou secret.

Implementation Lot 7:

- preuve live synthetique:
  `app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lot7-observability-smokes-20260620T123855Z.jsonl`;
- le smoke prouve provider live, validation PNG reelle, stockage
  Nextcloud-first, read-model linked, liste, lookup UUID, open, download,
  delete remote-first, tombstone local et absence distante status-only;
- JPEG/WebP sont prouves par tests unitaires/fake du Lot 3.1, car le provider
  live ne force pas proprement chaque format;
- conflit/no-overwrite et refus dossier non `linked` sont prouves par tests
  lorsque le live ne peut pas les reproduire sans mutation artificielle;
- scans anti-fuite Lot 7 executes sur artefact, docs, diff staged et logs
  applicatifs bornes, sans recopier ni conserver de logs bruts.

## 19. Lot Z

Lot Z cloture Images V1 avec l'artefact content-free:

```text
app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lotz-closure-20260620T130636Z.jsonl
```

Verdict final: `met`.

Portee de preuve:

- provider live synthetique prouve avec format observe PNG;
- JPEG/WebP couverts par tests/fakes Lot 3.1, sans les presenter comme formats
  live forces;
- create provider -> validation -> Nextcloud-first -> read-model linked;
- liste, lookup UUID, open, download, suppression remote-first, tombstone local
  et cleanup exact;
- no-overwrite/conflit et refus dossier non `linked` couverts par tests sans
  mutation DB artificielle;
- UI dossier Images couverte par tests frontend directs;
- scan artefact/docs/diff et scan logs applicatifs borne reel, sans raw logs
  recopies, commites ou conserves.

Les criteres de cloture appliques etaient:

- create provider -> validation -> Nextcloud-first -> read-model;
- au moins un smoke provider live synthetique avec prompt non sensible et cout
  borne quand le secret/runtime est disponible;
- si le provider live est indisponible, la cloture ne revendique pas de preuve
  provider live;
- formats V1 PNG/JPEG/WebP, par combinaison de live synthetique et tests fake
  deterministes si le provider ne permet pas de forcer chaque format;
- no-overwrite / conflit nom;
- liste et lookup UUID;
- open/download;
- suppression exacte et tombstone local si la suppression V1 est livree;
- refus SVG/GIF;
- refus dossier non `linked`;
- refus provider OK mais stockage durable KO;
- cleanup distant/local exact des images synthetiques;
- UI dossier Images si livree;
- scan artefacts/docs/diff;
- scan logs applicatifs borne reel, sauf limite explicitement documentee et
  non bloquante dans le verdict;
- aucun contenu utilisateur reel.

Le JSONL de preuve reste sous:

```text
app/docs/states/baselines/generated-images-smokes/
```

## 20. Hors-scope V1

- edition d'image;
- galerie avancee;
- batch multi-image;
- video;
- publication externe;
- moderation avancee hors provider;
- prompt rewriting automatique;
- prompt brut durable;
- stockage local de bytes image en DB;
- miniature persistante;
- OCR ou description automatique persistante;
- reuse-as-source;
- injection chat automatique;
- Documents ingestion;
- Notes Markdown;
- Exports;
- Biblio / Catalogue;
- Agenda;
- Mail;
- Memory/RAG/Identity/Summary;
- migration d'images historiques;
- listing large Nextcloud;
- DB Nextcloud directe.
