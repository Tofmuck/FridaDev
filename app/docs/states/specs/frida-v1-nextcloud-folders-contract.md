# Frida V1 - Nextcloud folders contract

Statut: spec vivante Lot Z valide; socle dossiers Frida V1 / Nextcloud cloture
Date: 2026-06-17
Classement: `app/docs/states/specs/`
TODO archivee: `app/docs/todo-done/product/frida-v1-nextcloud-folders-todo.md`
Audit source: `app/docs/states/audits/frida-v1-nextcloud-folders-lot0-audit-2026-06-16.md`
Contrat existant relu: `app/docs/states/specs/workspace-folders-contract.md`
Contrats dedies clotures:
`app/docs/states/specs/frida-v1-documents-ingestion-contract.md`,
`app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`,
`app/docs/states/specs/frida-v1-exports-contract.md`,
`app/docs/states/specs/frida-v1-generated-images-contract.md`

## 1. Perimetre

Cette spec a ete ouverte en Lot 1 comme contrat docs-only: le Lot 1 n'a pas
modifie le runtime, n'a pas cree de route, n'a pas change la DB, n'a pas
contacte Nextcloud, n'a provisionne aucun compte et n'a pas modifie la
plateforme.

Depuis le commit `017195f5`, cette meme spec documente aussi la mise en oeuvre
runtime fake/local livree par le Lot 3. Le Lot 3 reste sans Nextcloud live, sans
secret, sans migration DB, sans table de liaison et sans client Nextcloud
separe: il ajoute une projection/service derive depuis `workspace_folders`.

Depuis le Lot 4, les routes existantes `/api/workspace-folders*` exposent ce
modele fake/local sans route parallele, et l'UI affiche un statut sobre. La
suppression V1 tombstone le dossier et sort les conversations du dossier, mais
ne supprime aucun fichier ou document workspace.

Depuis le Lot 2 Sauron du 2026-06-16, le socle plateforme Nextcloud est livre:
compte `frida`, dossier `Frida`, partage vers `tof` en permissions `15`, aucun
lien public et secrets stockes cote plateforme sans valeur dans FridaDev. Le
rapport source est
`/opt/platform/_codex_reports/frida-v1-nextcloud-folders-lot2-sauron-20260616T151803Z.md`.

Depuis le Lot 5 du 2026-06-16, un smoke live Nextcloud borne a prouve la
creation, le renommage, la suppression et le cleanup final d'un dossier
synthetique unique sous la racine `Frida`, sans lister ni toucher de contenu
utilisateur. L'artefact JSONL content-free est
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot5-live-20260616T154117Z.jsonl`.
Ce smoke ne branche pas encore le runtime FridaDev sur Nextcloud en permanence.

Depuis le Lot 6, les operations fake/local exposent une observabilite
content-free avec reason codes allowlistes, pseudo-hashs fail-closed et
normalisation frontend defensive. Le Lot 6 ne branche pas Nextcloud en runtime
permanent.

Depuis le Lot 8A, FridaDev possede une persistance locale de l'etat
local/Nextcloud via `workspace_folder_nextcloud_links`, table de liaison stricte
rattachee a `workspace_folders.id`. Le Lot 8A ne branche pas encore le transport
Nextcloud live: aucune creation, lecture, renommage ni suppression Nextcloud
reelle n'est effectuee par ce lot.

Depuis le Lot 8B, les routes existantes `/api/workspace-folders*` creent et
renomment les dossiers Nextcloud avant la mutation locale. Le transport WebDAV
est borne aux dossiers: `MKCOL` pour creation, `MOVE` pour renommage et
`PROPFIND` status-only. La compensation automatique d'un `MKCOL` ne fait plus
de `DELETE`, faute de preuve sur l'absence de descendants concurrents.
L'artefact live content-free est
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot8b-live-runtime-20260616T201404Z.jsonl`.
L'injection runtime du secret est documentee sans valeur dans
`/opt/platform/_codex_reports/frida-v1-nextcloud-folders-lot8b-secret-injection-20260616T200809Z.md`.

Depuis le Lot 9 du 2026-06-17, les dossiers UI actifs existants ont ete
reconcilies avec Nextcloud sans lister de contenu: inventaire content-free,
`PROPFIND` Depth 0 par cible, creation par `MKCOL` uniquement pour les cibles
manquantes, puis liaison locale `workspace_folder_nextcloud_links` en
`linked`. L'artefact live content-free est
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot9-reconcile-20260617T074733Z.jsonl`.
Le backup applicatif des liaisons avant ecriture est
`/opt/platform/_codex_reports/frida-v1-nextcloud-folders-lot9-link-backup-20260617T074720Z.jsonl`.

Depuis le Lot 10A du 2026-06-17, la politique fichiers par dossier est
documentee sans runtime fichier Nextcloud: inventaire applicatif read-only
content-free, fichiers existants conserves sans migration automatique, fichiers
de dossier alors non livres a ranger plus tard dans le dossier Nextcloud du
dossier Frida, et separation explicite entre fichiers workspace, documents
actifs, notes, exports et images. L'audit source est
`app/docs/states/audits/frida-v1-nextcloud-folders-lot10-files-policy-2026-06-17.md`.

Depuis le Lot 11 du 2026-06-17, les sous-dossiers standards par dossier Frida
sont definis et crees/verifies de maniere bornee: `Documents`, `Notes`,
`Exports` et `Images`. La creation Nextcloud-first d'un nouveau dossier cree le
dossier parent puis ces sous-dossiers avant la creation locale. Les dossiers
Frida existants `linked` peuvent etre verifies/completees par le helper dedie,
avec `PROPFIND` Depth 0 et `MKCOL` seulement, sans listing de contenu ni
operation fichier. L'artefact live content-free est
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot11-standard-subfolders-20260617T091722Z.jsonl`.
Correctif Lot 11: un `PROPFIND` `207` ne suffit pas a prouver un dossier; la
reponse XML est parse en memoire uniquement et la ressource doit porter
`collection` pour etre acceptee comme dossier parent ou sous-dossier standard.
Une ressource WebDAV non-collection est un conflit/incompatibilite
content-free, sans XML brut, URL DAV, chemin technique ni payload Nextcloud
expose.

Depuis le Lot 12 du 2026-06-17, le routage cible des artefacts de dossier est
norme sans runtime supplementaire: documents sources et fichiers persistants
dans `Documents`, notes Markdown dans `Notes`, exports Markdown/TXT/DOCX/PDF
dans `Exports`, images generees dans `Images`. Ce lot ne migrait aucun fichier
existant, ne creait aucune note, ne produisait aucun export, ne generait ni ne
stockait aucune image, et ne contactait pas Nextcloud.

Depuis le Lot Z du 2026-06-17, le socle dossiers Frida V1 / Nextcloud est
valide empiriquement par le runtime reel: creation applicative Nextcloud-first,
renommage applicatif Nextcloud-first, suppression produit en tombstone local
sans suppression recursive Nextcloud, reconciliation des dossiers existants,
sous-dossiers standards et observabilite content-free. L'artefact source est
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lotz-live-closure-20260617T104258Z.jsonl`.
Cette validation ne livrait pas, a la date du Lot Z Folders, les runtimes
Documents, Notes, Exports, Images ou mail. Depuis, Documents, Notes, Exports et
Images sont clotures par leurs contrats dedies cites en en-tete; mail reste un
chantier separe.

Recalage produit post Lot 6:

- les Lots 0 a 6 sont des fondations, pas la cloture produit Frida 1.0;
- la V1 produit n'est pas livree tant que la creation UI d'un dossier Frida ne
  cree pas reellement le sous-dossier Nextcloud `/Frida/<nom_sanitise>`;
- la V1 doit relier les dossiers UI Frida aux dossiers Nextcloud reels;
- les dossiers existants doivent etre reconcilies dans un lot separe;
- les fichiers, documents, notes, exports et images doivent rester compatibles
  avec ce modele; Documents, Notes, Exports et Images sont maintenant portes par
  des contrats dedies clotures.

Il fixe le contrat produit minimal du socle Frida 1.0:

```text
un dossier frontend Frida = un sous-dossier Nextcloud sous la racine logique Frida
```

Le socle Folders reste source-of-truth pour `workspace_folders`, le mapping
logique `/Frida/<dossier>`, les sous-dossiers standards et les gardes
Nextcloud-first. Les runtimes Documents, Notes Markdown, Exports et Images
generees sont sources-of-truth dans leurs contrats dedies clotures. Mail,
Agenda et Biblio restent separes.

Clarification Lot 2A du 2026-06-23:

- les formulations historiques du type "futur", "a livrer" ou "reste a livrer"
  dans les sections de lots Folders decrivent l'etat du socle au 2026-06-17;
- elles ne rouvrent pas Documents, Notes, Exports ou Images pour la cloture
  Frida V1;
- le statut courant de ces quatre chantiers est donne par les contrats dedies
  cites en en-tete et par leurs TODO archivees.

## 2. Decision modele

Decision Lot 1:

- `workspace_folders` devient le modele produit des dossiers Frida V1;
- les dossiers visibles dans l'interface actuelle deviennent les dossiers Frida
  V1 relies a Nextcloud;
- Frida V1 ne cree pas de nouvelle notion produit separee `frida_folder`;
- la relation conversation -> dossier continue de passer par
  `conversations.workspace_folder_id`;
- les fichiers workspace, selections et OCR restent des surfaces distinctes et
  ne sont pas ouvertes par ce contrat.

Consequence:

- si des champs techniques Nextcloud sont necessaires, ils doivent etendre
  `workspace_folders` ou vivre dans une table de liaison strictement rattachee a
  `workspace_folders.id`;
- cette table de liaison eventuelle ne doit pas creer une deuxieme notion
  utilisateur de dossier;
- l'UI ne doit pas afficher deux familles de dossiers;
- les endpoints existants `/api/workspace-folders*` sont les surfaces
  applicatives candidates pour les lots runtime futurs, mais aucune route n'est
  modifiee par ce Lot 1.

Justification:

- l'utilisateur a deja une surface dossiers dans la sidebar;
- `workspace_folders.id` est un identifiant stable non derive du nom humain;
- les conversations sont deja rattachees a zero ou un dossier;
- creer un modele produit parallele augmenterait le risque de divergence UI,
  conflits de nom, suppression incoherente et confusion conversation/dossier.

Effets de bord a traiter plus tard:

- risque historique corrige: l'ancien contrat de suppression dossier pouvait
  tenter de supprimer des fichiers workspace locaux;
- contrat courant: `DELETE /api/workspace-folders/<id>` tombstone le dossier,
  sort les conversations du dossier, preserve les fichiers/documents workspace
  et retourne `workspace_folder_files_preserved`;
- le futur branchement Nextcloud ne doit pas reprendre une suppression live
  recursive sans confirmation humaine et borne synthetique;
- les champs Nextcloud devront etre ajoutes sans exposer chemin brut, URL DAV ou
  information sensible en UI/logs;
- les tests Lot 3 devront prouver que le comportement existant des conversations
  reste stable.

## 3. Mapping Nextcloud logique

Racine logique cible:

```text
/Frida
```

Mapping produit:

```text
workspace_folder.display_name -> /Frida/<display_name_sanitise>
```

Regles:

- quand l'utilisateur cree un nouveau dossier Frida dans l'interface, cela
  correspond, a terme, a un nouveau sous-dossier Nextcloud sous `/Frida`;
- le dossier racine logique `/Frida` et ses sous-dossiers doivent etre partages
  avec l'utilisateur Nextcloud `tof`;
- le provisionnement du compte Frida, de la racine, des droits, du partage et
  des secrets plateforme a ete livre par Sauron en Lot 2;
- le rapport Lot 2 confirme le partage `tof` avec permissions `15`, sans lien
  public, et une preuve DAV status-only `207`;
- limite Lot 2: le partage est prouve par `occ`/OCS, pas par login DAV du
  compte `tof`;
- FridaDev ne doit pas acceder directement a la DB Nextcloud;
- FridaDev ne doit pas exposer de chemin brut serveur;
- les logs, JSONL, dashboards et rapports utilisent un alias logique redacted ou
  une reference courte, jamais une URL DAV ni un chemin serveur;
- Lot 1 ne lit ni n'ecrit Nextcloud.

Contrat runtime cible:

- creation UI: FridaDev cree d'abord le sous-dossier Nextcloud
  `/Frida/<display_name_sanitise>`, puis cree le dossier local seulement si
  Nextcloud reussit;
- si la creation Nextcloud echoue, FridaDev refuse la creation locale, affiche
  une erreur simple et trace un reason code content-free;
- renommage UI: FridaDev renomme d'abord le sous-dossier Nextcloud, puis
  renomme le dossier local seulement si Nextcloud reussit;
- si le renommage Nextcloud echoue, l'ancien nom local reste conserve, sans
  divergence silencieuse local/Nextcloud;
- suppression UI V1: FridaDev tombstone ou retire le dossier localement, sans
  suppression recursive automatique du dossier Nextcloud reel;
- suppression Nextcloud autorisee seulement pour un dossier synthetique, vide
  prouve ou smoke controle, jamais pour un vrai dossier potentiellement charge
  en fichiers utilisateur.

Le nom Nextcloud cible n'est pas seulement le `display_name` brut. Le Lot 3 a
defini une normalisation fake/local reproductible, detaillee en section 11. Les
lots live futurs devront conserver au minimum:

- suppression des espaces superflus;
- longueur bornee;
- refus des caracteres incompatibles avec le stockage cible;
- cle de comparaison casefolded pour detecter les collisions;
- conservation du `display_name` utilisateur pour l'affichage.

Renommage:

- renommer un `workspace_folder` renomme le dossier Frida cote produit;
- en runtime permanent, le sous-dossier Nextcloud cible est renomme avant le
  nom local Frida;
- si Nextcloud refuse ou echoue, le nom local ne change pas;
- aucun renommage silencieux ne doit corriger un conflit;
- l'ancien alias logique ne doit pas rester affiche comme cible active apres un
  renommage reussi;
- les logs de renommage restent content-free.

Suppression/tombstone:

- `workspace_folders.deleted_at` reste le signal local de suppression;
- un dossier supprime ne doit plus etre liste comme dossier actif;
- les conversations ne sont pas supprimees automatiquement;
- une reference Nextcloud future devra passer a l'etat `deleted` ou
  equivalent, sans conserver de chemin brut;
- la suppression V1 conserve le dossier Nextcloud reel;
- toute suppression reelle Nextcloud est reservee aux smokes controles ou aux
  dossiers synthetiques/vides prouves.

## 4. Modele produit minimal

Le Lot 1 definit les logiques attendues. Le choix fake/local livre en Lot 3 est
un calcul derive depuis `workspace_folders`, sans migration DB et sans table de
liaison. Le choix live eventuel reste reserve aux lots ulterieurs.

Logiques deja portees ou candidates dans `workspace_folders`:

- identifiant stable applicatif: `workspace_folders.id`;
- nom affiche: `display_name`;
- description UI-only: `description`, non injectee au modele;
- icone allowlistee: `icon_key`;
- ordre UI: `sort_order`;
- timestamps locaux: `created_at`, `updated_at`, `deleted_at`;
- statut local derive: `active`, `deleted` ou `tombstone`.

Modele d'etat runtime cible Lot 7:

- `local_only`:
  - signification: dossier local existant sans lien Nextcloud confirme;
  - apparition: dossiers historiques avant reconciliation, fallback de lecture
    ou absence de liaison persistante;
  - UI: libelle sobre du type `Local a relier`;
  - renommage: autorise seulement comme operation de reconciliation ou tant que
    le runtime permanent n'est pas actif;
  - suppression: tombstone local autorise, sans suppression Nextcloud;
  - artefacts Documents/Notes/Exports/Images: non autorises comme cible
    Nextcloud tant que l'etat n'est pas `linked`.
- `sync_pending`:
  - signification: operation Nextcloud en cours ou reservee, resultat non
    confirme;
  - apparition: fenetre transactionnelle runtime ou retry controle;
  - UI: `Synchronisation en cours`;
  - renommage: bloque ou desactive jusqu'a resolution;
  - suppression: a refuser ou differer sauf rollback explicite;
  - artefacts Documents/Notes/Exports/Images: non autorises.
- `linked`:
  - signification: dossier local et sous-dossier Nextcloud cible associes;
  - apparition: creation runtime reussie, renommage reussi ou reconciliation
    confirmee;
  - UI: statut discret `Synchronise` ou pas de badge si l'etat normal suffit;
  - renommage: autorise via renommage Nextcloud d'abord, puis local;
  - suppression: tombstone local autorise, dossier Nextcloud reel conserve;
  - artefacts Documents/Notes/Exports/Images: autorises sous reserve des
    contrats dedies.
- `sync_error`:
  - signification: derniere operation Nextcloud echouee avec erreur redacted;
  - apparition: echec transport, droits, cible absente ou conflit live;
  - UI: `Erreur Nextcloud` avec message simple;
  - renommage: bloque sauf action de reparation/retry explicite;
  - suppression: tombstone local possible si cela ne masque pas une operation
    live partielle;
  - artefacts Documents/Notes/Exports/Images: non autorises tant que l'erreur n'est pas
    resolue.
- `conflict`:
  - signification: conflit local, conflit Nextcloud, collision apres
    sanitisation ou collision casefold;
  - apparition: validation creation/renommage ou reconciliation;
  - UI: `Conflit`, avec invitation a choisir un autre nom ou arbitrer;
  - renommage: autorise vers un nom non conflictuel;
  - suppression: tombstone local possible sans suppression Nextcloud;
  - artefacts Documents/Notes/Exports/Images: non autorises.
- `deleted`:
  - signification: dossier local tombstone ou retire de l'UI active;
  - apparition: suppression UI Frida;
  - UI: masque par defaut;
  - renommage: interdit;
  - suppression: aucune suppression Nextcloud automatique;
  - artefacts Documents/Notes/Exports/Images: interdits.

Champs techniques candidats pour le runtime permanent:

- `nextcloud_sync_state`: un des etats cibles ci-dessus;
- `nextcloud_folder_ref`: reference logique redacted stable, jamais URL DAV ni
  chemin serveur;
- `nextcloud_name_hash`: hash court du nom cible sanitise;
- `last_sync_at`: timestamp de derniere transition ou observation;
- `last_sync_reason_code`: reason code content-free de la derniere transition;
- `last_sync_operation`: operation source si necessaire (`create`, `rename`,
  `delete`, `reconcile`);
- `nextcloud_share_state`: `unknown`, `expected`, `confirmed` ou `error`.

Le Lot 7 n'imposait pas de migration DB. Le runtime permanent live etait bloque
tant que la persistance d'etat local/Nextcloud n'etait pas tranchee. Le Lot 8A
tranche explicitement ou persister ou deriver:

- `nextcloud_sync_state`, dont `linked`, `sync_error`, `conflict` et `deleted`;
- `nextcloud_folder_ref`;
- `nextcloud_name_hash`;
- `last_sync_at`;
- `last_sync_reason_code`;
- `last_sync_operation`.

Decision Lot 8A:

- choix retenu: table de liaison stricte
  `workspace_folder_nextcloud_links`;
- rattachement: `workspace_folder_id` est cle primaire et reference
  `workspace_folders(id)` en `ON DELETE CASCADE`;
- la table ne cree pas de deuxieme notion utilisateur de dossier;
- elle isole les etats de transport/synchronisation sans gonfler
  `workspace_folders`;
- l'absence de ligne de liaison reste compatible avec les dossiers historiques:
  la projection expose `local_only`;
- la ligne de liaison permet de memoriser `linked`, `sync_error`, `conflict`,
  `deleted`, `nextcloud_folder_ref`, `nextcloud_name_hash`, `last_sync_at`,
  `last_sync_reason_code`, `last_sync_operation`, `nextcloud_share_state`,
  `created_at` et `updated_at`.

Le Lot 8A resout la decision de persistance locale, mais il ne prouve pas encore
le transport live. Le Lot 8B devra utiliser cette persistence pour faire passer
creation et renommage en Nextcloud-first.

Invariant post-correctif Lot 8A: toute reponse d'update local d'un
`workspace_folder` doit reappliquer la projection persistante
`workspace_folder_nextcloud_links` si elle existe. Apres un futur succes
Nextcloud Lot 8B, un echec de persistance locale de cette liaison doit etre
fail-closed: rollback si possible, sinon erreur explicite content-free; jamais
un succes silencieux.

Invariant post-correctif Lot 8A.2: une erreur redacted de persistance ne doit
pas chainer de cause brute exploitable par traceback. Historiquement, une
relecture post-update reconstruisait la projection persistante et refusait le
fallback `local_only` potentiellement faux.

Invariant post-correctif L5.2: cette relecture post-commit est supprimee. La
mutation locale utilise un `UPDATE ... RETURNING` dans une CTE, joint dans la
meme transaction la ligne `workspace_folder_nextcloud_links`, puis serialise
et valide la projection complete avant `commit()`. Une ligne ou projection
absente/invalide provoque le rollback local. Apres retour normal de `commit()`,
la projection deja construite est retournee sans nouveau GET: une panne de
lecture ne peut donc plus transformer le commit B en echec ni declencher le
`MOVE` inverse. Les updates locaux d'icone, description ou ordre conservent la
liaison persistante complete; l'absence reelle de liaison reste seule projetee
en `local_only`.

Invariant post-correctif residuel L5.3: un renommage qui change la cible inscrit
et committe d'abord l'ancienne identite de liaison en `sync_pending`, par un
UPDATE conditionne au lien encore `linked` et aux ref/hash observes, puis lance
le MOVE. Apres succes, la nouvelle ref/hash passe en `linked` avant la mutation
du nom local. Un consommateur d'artefact peut ainsi refuser atomiquement aussi
bien une ancienne coordonnee apres renommage qu'une coordonnee dont le MOVE est
en cours. Un echec HTTP du MOVE restaure l'ancien lien `linked`; une panne
transport sans issue certaine laisse `sync_pending` visible. Aucun verrou SQL
n'est conserve pendant WebDAV.

Compatibilite: le payload fake/local Lot 3 peut encore exposer des etats
historiques comme `pending` ou `error`. Le Lot 8B devra mapper ou migrer ces
etats vers le vocabulaire runtime cible sans casser les clients existants.

Contraintes:

- ne pas stocker de secret dans FridaDev;
- ne pas stocker de chemin brut serveur dans une surface affichee ou logguee;
- ne pas exposer `storage_key`, chemin disque, URL DAV, contenu fichier ou
  extrait utilisateur;
- ne pas confondre etat local du dossier et etat de synchronisation Nextcloud.

Decision Lot 8B:

- transport dedie: `app/core/workspace_folder_nextcloud_client.py`;
- orchestration Nextcloud-first:
  `app/core/workspace_folder_nextcloud_runtime.py`;
- creation: `MKCOL` Nextcloud puis creation locale puis liaison
  `workspace_folder_nextcloud_links` en `linked`;
- renommage: barriere durable de liaison `sync_pending`, puis `MOVE` Nextcloud,
  nouvelle liaison `linked`, puis mutation locale;
- compensation creation: si la persistance locale echoue apres `MKCOL`, le
  parent distant est conserve, car ni la reponse MKCOL ni le status Depth 0 ne
  prouvent qu'aucun descendant concurrent n'existe ; la reponse signale
  `workspace_folder_nextcloud_rollback_ownership_unverified`, et le tombstone
  local reste tente si necessaire; depuis le correctif Lot 8B.1, si ce tombstone local echoue, la
  reponse doit signaler `local_compensation_status=failed` et
  `workspace_folder_local_compensation_failed` sans pretendre que la divergence
  locale est resolue;
- compensation renommage: si la persistance locale echoue avant un commit
  confirme apres `MOVE`, rollback `MOVE` strict vers l'ancien nom et
  restauration de la liaison si possible; apres retour normal du commit local,
  aucune indisponibilite de projection ne peut lancer cette compensation;
- client/secret Nextcloud indisponible: retour runtime content-free
  `workspace_folder_nextcloud_unavailable`, sans traceback utilisateur ni chemin
  secret brut;
- suppression UI reste hors live Nextcloud: tombstone local seulement, pas de
  suppression recursive du dossier Nextcloud reel;
- `nextcloud_share_state` reste `expected` car le Lot 8B ne prouve pas le login
  DAV `tof`; le partage global a ete prouve par Sauron en Lot 2.

Limite transactionnelle L5.2: ce contrat n'est pas une transaction distribuee
avec Nextcloud. Une perte de connexion pendant `COMMIT` peut rendre son issue
indeterminable pour le client; sans journal durable ni protocole en deux phases,
le runtime ne peut pas distinguer avec certitude un commit refuse d'un commit
accepte dont l'accuse de reception a ete perdu. L5.2 n'ajoute volontairement ni
retry, ni journal, ni reconciliation automatique pour cette fenetre de crash.

Reason codes runtime Lot 8B:

- `workspace_folder_nextcloud_create_ok`;
- `workspace_folder_nextcloud_rename_ok`;
- `workspace_folder_nextcloud_conflict`;
- `workspace_folder_nextcloud_unavailable`;
- `workspace_folder_nextcloud_auth_failed`;
- `workspace_folder_nextcloud_target_missing`;
- `workspace_folder_nextcloud_rollback_ok`;
- `workspace_folder_nextcloud_rollback_failed`;
- `workspace_folder_nextcloud_rollback_ownership_unverified`;
- `workspace_folder_local_persistence_failed`;
- `workspace_folder_local_compensation_failed`;
- `workspace_folder_nextcloud_error_redacted`.

## 5. Operations V1

Les operations produit V1 sont:

- lister les dossiers Frida actifs;
- creer un dossier Frida;
- renommer un dossier Frida;
- supprimer un dossier Frida;
- detecter un conflit de nom;
- afficher une erreur comprehensible;
- tracer les operations en content-free.

Creation:

- l'utilisateur fournit un nom affiche;
- FridaDev valide et normalise le nom;
- depuis le Lot 8B runtime permanent, FridaDev cree d'abord le sous-dossier
  Nextcloud
  `/Frida/<display_name_sanitise>`;
- le dossier local `workspace_folders` est cree seulement apres succes
  Nextcloud;
- si Nextcloud echoue, la creation Frida est refusee et aucun dossier local en
  erreur n'est cree silencieusement;
- l'utilisateur voit une erreur simple et l'observabilite trace un reason code
  content-free;
- la reponse utilisateur ne doit pas afficher de chemin serveur.

Listing:

- la liste active vient du modele applicatif `workspace_folders`;
- les dossiers supprimes ne sont pas listes par defaut;
- l'etat Nextcloud peut etre affiche comme statut produit, mais sans detail
  sensible;
- un etat `local_only` reste acceptable pour les dossiers historiques avant
  reconciliation;
- un etat `linked` ne doit etre affiche que sur preuve runtime ou
  reconciliation content-free.

Renommage:

- le renommage doit repasser par la validation et detection de conflit;
- les conflits locaux sont detectes avant d'appeler Nextcloud;
- les conflits Nextcloud sont detectes ou traites separement;
- depuis le Lot 8B runtime permanent, FridaDev renomme d'abord le sous-dossier
  Nextcloud;
- le nom local est change seulement apres succes Nextcloud;
- si Nextcloud echoue, l'ancien nom local reste actif;
- en cas de conflit, l'ancien nom reste actif.

Suppression:

- la suppression locale peut tombstoner le `workspace_folder`;
- les conversations restent conservees et sorties du dossier selon le contrat
  existant;
- les fichiers et documents workspace restent conserves dans Lot 4;
- la suppression V1 d'un vrai dossier conserve le dossier Nextcloud;
- aucune suppression recursive Nextcloud automatique ne doit se produire;
- la suppression Nextcloud reste reservee aux smokes controles ou a un dossier
  synthetique/vide prouve;
- pas de suppression recursive large;
- pas de deplacement massif;
- pas de lecture, suppression ou log de contenu fichier dans ce contrat.

## 6. Conflits de noms

Le conflit doit etre explicite, actionnable et content-free. Aucun renommage
automatique silencieux n'est autorise.

Cas a cadrer:

- nom vide;
- nom invalide apres nettoyage;
- nom trop long;
- nom deja utilise localement par un dossier actif;
- nom deja existant cote Nextcloud dans un lot futur;
- collision apres sanitisation;
- collision apres comparaison majuscules/minuscules;
- dossier local supprime/tombstone portant encore une reference utile;
- cible Nextcloud inconnue ou non verifiee.

Messages utilisateur:

- simples et non techniques;
- sans chemin brut;
- sans URL DAV;
- sans identifiant serveur sensible;
- avec indication de l'action possible: choisir un autre nom, verifier droits ou
  reessayer plus tard selon le cas.

Reason codes minimaux:

- `workspace_folder_name_required`;
- `workspace_folder_name_invalid`;
- `workspace_folder_name_too_long`;
- `workspace_folder_name_conflict_local`;
- `workspace_folder_name_conflict_nextcloud`;
- `workspace_folder_name_conflict_sanitized`;
- `workspace_folder_name_conflict_case`;
- `workspace_folder_id_invalid`;
- `workspace_folder_not_found`;
- `workspace_folder_deleted`;
- `workspace_folder_sync_unknown`;
- `workspace_folder_sync_pending`;
- `workspace_folder_sync_linked`;
- `workspace_folder_sync_conflict`;
- `workspace_folder_sync_error`;
- `workspace_folder_share_unknown`;
- `workspace_folder_share_expected`;
- `workspace_folder_share_confirmed`;
- `workspace_folder_share_error`;
- `workspace_folder_delete_confirmation_required`;
- `workspace_folder_live_unavailable`;
- `workspace_folder_sauron_required`.

Les reason codes ne doivent jamais contenir de nom utilisateur brut, chemin,
contenu, secret, URL ou detail serveur sensible.

## 7. Frontiere fake/local vs live

Lot 1:

- contrat docs-only;
- aucune implementation runtime;
- aucun schema DB definitif;
- aucun acces Nextcloud.

Lot 2 Sauron:

- compte Nextcloud `frida` cree pour les fichiers/dossiers Frida V1;
- dossier `Frida` cree dans l'espace du compte `frida`;
- partage utilisateur vers `tof` cree avec permissions `15`: lecture,
  ecriture/update, creation, suppression, sans reshare;
- aucun lien public;
- secret compte et app-password dediee stockes cote plateforme, valeurs jamais
  affichees ni copiees dans FridaDev;
- preuve read-only content-free OK, dont DAV status-only `207`;
- limite: partage prouve par `occ`/OCS, pas par login DAV du compte `tof`;
- rapport:
  `/opt/platform/_codex_reports/frida-v1-nextcloud-folders-lot2-sauron-20260616T151803Z.md`.

Lot 3:

- implementation fake/local du modele applicatif;
- tests automatises sur creation, listing, renommage, suppression, conflits et
  etats;
- aucun secret;
- aucun appel Nextcloud live;
- logs et fixtures content-free.

Lot 4:

- routes existantes `/api/workspace-folders*` completees, sans route parallele;
- listing, creation, renommage et suppression exposent la projection fake/local;
- suppression V1 = tombstone dossier et conversations sorties du dossier;
- aucun fichier ou document workspace n'est supprime par la suppression du
  dossier;
- UI avec confirmation humaine et statut discret: `Local`,
  `En attente Nextcloud`, `Conflit`, `Erreur`;
- aucun chemin serveur, URL DAV, secret, `storage_key` ou contenu utilisateur.

Lot 5:

- ouverture live effectuee seulement apres Lots 0 a 4 et decision Sauron;
- preuve read-only droits/racine par DAV/OCS interne status-only;
- smoke live borne sur dossier synthetique:
  `frida-v1-smoke-20260616T154117Z`;
- renommage synthetique:
  `frida-v1-smoke-20260616T154117Z-renamed`;
- suppression du dossier synthetique renomme puis verification finale d'absence;
- cleanup final `done`;
- artefact:
  `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot5-live-20260616T154117Z.jsonl`;
- aucun contenu utilisateur lu, liste, deplace, supprime ou loggue;
- aucun fichier/document workspace touche;
- aucun lien public cree;
- aucun secret, app-password, URL DAV complete, raw XML ou chemin disque dans
  l'artefact;
- aucun branchement runtime permanent ni operation UI live dans ce lot.

Lot 6:

- observabilite content-free locale des routes `/api/workspace-folders*`;
- reason codes allowlistes et erreurs redacted;
- aucune route parallele, aucune route admin, aucun Nextcloud live permanent.

Lot 7:

- design d'etat runtime local/Nextcloud;
- decisions produit inscrites: creation Nextcloud d'abord, renommage Nextcloud
  d'abord, suppression locale sans suppression recursive Nextcloud reelle;
- aucun code runtime, aucun live, aucun secret et aucune migration DB.

Lot 8A:

- table `workspace_folder_nextcloud_links` creee dans le bootstrap DB
  applicatif;
- projection `/api/workspace-folders*` enrichie par `LEFT JOIN` si une liaison
  existe;
- absence de liaison persistante -> `local_only`;
- liaison persistante `linked`, `sync_error` ou `conflict` -> projection
  content-free correspondante;
- suppression dossier -> projection `deleted`, fichiers/documents preserves;
- aucun Nextcloud live, aucun WebDAV/OCS, aucun secret.

Sauron:

- compte Nextcloud Frida;
- racine logique ou emplacement serveur correspondant a `/Frida`;
- droits exacts;
- partage avec `tof`;
- gestion des secrets runtime;
- verification serveur et backup/rollback plateforme si necessaire.

Celebrimbor:

- contrat produit;
- code FridaDev dans les lots applicatifs futurs;
- fake/local;
- tests applicatifs;
- docs applicatives;
- observabilite content-free.

## 8. Observabilite content-free

Statut Lot 6: livre en fake/local applicatif.

Le Lot 6 ajoute une projection d'observabilite content-free dediee aux dossiers
Frida V1, branchee sur les routes existantes `/api/workspace-folders*`. Elle ne
cree pas de route parallele, ne cree pas de route admin, ne branche pas
Nextcloud en runtime permanent et ne modifie pas Sauron.

Module:

- `app/observability/workspace_folders_observability.py`;
- service appele depuis `app/core/workspace_folders_service.py`;
- normalisation frontend allowlistee dans `app/web/chat_workspace_folders.js`.

Operations observees:

- `list`;
- `create`;
- `rename`;
- `delete`;
- erreurs de validation ou conflit sur ces operations.

Reason codes consolides:

- succes:
  - `workspace_folder_list_ok`;
  - `workspace_folder_create_ok`;
  - `workspace_folder_rename_ok`;
  - `workspace_folder_delete_ok`;
- validation/conflits:
  - `workspace_folder_name_required`;
  - `workspace_folder_name_invalid`;
  - `workspace_folder_name_too_long`;
  - `workspace_folder_name_conflict_local`;
  - `workspace_folder_name_conflict_sanitized`;
  - `workspace_folder_name_conflict_case`;
- droits/cible/live futur redacted:
  - `workspace_folder_permission_denied`;
  - `workspace_folder_target_missing`;
  - `workspace_folder_target_exists`;
  - `workspace_folder_delete_refused`;
  - `workspace_folder_nextcloud_error_redacted`;
- etats et limites V1:
  - `workspace_folder_sync_pending`;
  - `workspace_folder_deleted`;
  - `workspace_folder_files_preserved`.

Champs autorises dans la projection:

- `kind`;
- `operation`;
- `status`;
- `status_class` pour la classe de statut de reponse;
- `reason_code`;
- hash court du dossier (`folder_ref`), calcule par le read-model;
- hash court du nom cible Nextcloud (`nextcloud_name_hash`) seulement si la
  valeur source ressemble strictement au hash court attendu;
- `local_status`;
- `nextcloud_sync_state`;
- `nextcloud_share_state`;
- `nextcloud_reason_code`;
- compteurs de dossiers et d'etats;
- compteurs de suppression dossier (`files_deleted`, `files_preserved`,
  `file_delete_requested`, `file_delete_failed`, `conversations_moved_out`);
- indicateurs booleens d'absence de contenu brut, chemin serveur, URL distante
  et secret.

Champs interdits dans la projection, les logs, les JSONL et les rapports:

- contenu de fichier;
- extrait utilisateur;
- `display_name` ou nom sensible non necessaire;
- chemin brut serveur;
- URL DAV;
- chemin disque;
- `storage_key`;
- secret;
- nom sensible si le contexte peut l'etre;
- payload brut Nextcloud;
- detail serveur sensible.

Les erreurs sont exploitables par `reason_code`, classe HTTP et hash court
d'erreur si necessaire. Le hash court est stable pour une meme valeur, mais ne
remplace pas un journal technique brut et ne doit jamais etre accompagne du
message original s'il contient chemin, URL, secret, nom sensible ou contenu.

Regles fail-closed post Lot 6:

- `reason_code`, `nextcloud_reason_code`, `file_reason_code` et les cles de
  `reason_code_counts` sont allowlistes par le catalogue des reason codes;
- toute raison inconnue est remplacee par
  `workspace_folder_nextcloud_error_redacted`;
- un pseudo-hash qui contient un nom, un chemin ou tout texte non conforme n'est
  pas expose comme `nextcloud_name_hash`;
- les booleens frontend de la projection sont parses strictement:
  `"false"`, `"0"`, `"no"`, `"off"`, chaine vide, `null` et `undefined`
  valent `false`.

Lien observabilite globale:

- cette brique locale est une preuve de faisabilite pour
  `app/docs/todo-done/product/frida-v1-agentic-observability-todo.md`;
- elle ne cloture pas la refonte globale observabilite;
- elle fournit un precedent: reason codes catalogues, read-model allowliste,
  tests anti-fuite et scan avant commit.

## 9. Limites des fondations Lots 0 a 7 et hors-scope courant

Restent hors-scope des fondations livrees a ce stade, meme s'ils peuvent
devenir necessaires avant cloture V1 reelle:

- ingestion documents;
- notes Markdown;
- exports;
- images generees;
- rattachement mail;
- Agenda;
- Biblio;
- refonte Nextcloud;
- migration massive;
- routes paralleles ou nouvelles hors `/api/workspace-folders*`;
- refonte UI large;
- migration DB avant decision technique dediee;
- runtime permanent Nextcloud depuis FridaDev avant Lot 8B;
- creation, rotation ou affichage de secrets depuis FridaDev;
- modification compte/droits/partage live hors intervention Sauron explicite;

Le dossier Frida V1 est une unite de travail et un mapping de rangement, pas:

- une memoire par dossier;
- un RAG par dossier;
- une Biblio;
- un prompt de projet;
- une identite;
- un resume separe;
- une lecture automatique des fichiers du dossier.

## 10. Point de sortie Lot 1

Lot 1 est fini quand:

- la decision `workspace_folders` etendu est inscrite;
- l'absence de nouveau modele produit `frida_folder` est inscrite;
- le mapping logique `/Frida/<dossier>` est inscrit;
- les champs/logiques minimaux sont listes sans schema DB definitif;
- les operations V1 sont listees;
- les conflits de nom et reason codes sont cadres;
- la frontiere fake/local, live et Sauron est claire;
- les limites V1 et hors-scope sont ecrits.

Etat de la section Lot 1: ces conditions ont ete remplies avant l'ouverture du
Lot 3 fake/local. Le Lot 3 est desormais documente ci-dessous; les Lots 2, 4, 5
et 6 restent distincts.

## 11. Mise en oeuvre Lot 3 fake/local

Lot 3 livre le 2026-06-16 le modele backend fake/local sans appel Nextcloud.

Decision technique:

- choix retenu: calcul local derive depuis `workspace_folders`;
- pas de migration DB;
- pas de table de liaison;
- pas de deuxieme notion utilisateur de dossier;
- les champs Nextcloud fake/local sont ajoutes au payload serialise des
  `workspace_folders`;
- l'unique modele produit reste `workspace_folders`.

Justification:

- le Lot 3 ne possede aucune preuve live Nextcloud a persister;
- le mapping logique `/Frida/<dossier>` est derivable depuis `display_name`;
- l'etat local est derivable depuis `deleted_at`;
- les conflits sont detectables contre les dossiers actifs existants;
- une migration reste prematuree avant Lot 5 live et avant choix explicite de
  persistence des preuves live.

Algorithme de sanitisation Nextcloud fake/local:

1. normaliser le nom utilisateur par collapse des espaces;
2. refuser le nom vide;
3. refuser un nom affiche de plus de `80` caracteres au lieu de le tronquer
   silencieusement dans les routes dossier V1;
4. appliquer une normalisation Unicode `NFKC`;
5. conserver les caracteres alphanumeriques et `.` / `_` / `-`;
6. transformer espaces, separateurs de chemin et ponctuation en `-`;
7. supprimer les caracteres de controle;
8. compacter les tirets consecutifs;
9. retirer les espaces, points, `_` et `-` en debut/fin de cible;
10. refuser la cible vide apres nettoyage.

Unicite locale:

- les dossiers `deleted_at IS NOT NULL` ne bloquent pas la reutilisation du nom;
- un nom affiche identique a un dossier actif donne
  `workspace_folder_name_conflict_local`;
- un nom affiche equivalent en `casefold()` donne
  `workspace_folder_name_conflict_case`;
- une cible sanitisee equivalente en `casefold()` donne
  `workspace_folder_name_conflict_sanitized`;
- aucun renommage silencieux n'est applique.

Payload fake/local:

- `local_status`: `active` ou `deleted`;
- `nextcloud_logical_root`: `/Frida`;
- `nextcloud_target_name`: nom cible sanitise;
- `nextcloud_logical_path`: mapping logique `/Frida/<display_name_sanitise>`;
- `nextcloud_directory_ref`: reference courte derivee content-free;
- `nextcloud_name_hash`: hash court de la cle cible;
- `nextcloud_sync_state`: `pending` pour un dossier actif valide,
  `deleted` pour une tombstone, `error` si une ligne historique est invalide;
- `nextcloud_share_state`: `expected` pour un dossier actif valide,
  `unknown` pour une tombstone ou erreur;
- `nextcloud_live_checked`: toujours `false` dans Lot 3.

Etats fake/local:

- `unknown`: etat reserve pour payloads futurs ou modules sans verification;
- `pending`: etat normal d'un dossier actif local, sans preuve live;
- `linked`: interdit comme preuve Nextcloud dans Lot 3; reservable seulement a
  une simulation explicite future;
- `conflict`: retourne par les validations de creation/renommage en cas de
  collision;
- `error`: retourne par les validations invalides ou lignes historiques
  incoherentes;
- `deleted`: derive de `workspace_folders.deleted_at`.

Etat de partage:

- `expected`: partage avec `tof` attendu par contrat, sans preuve live;
- `unknown`: tombstone, erreur ou absence de verification;
- `confirmed`: interdit hors preuve live/Sauron;
- `error`: reserve aux lots futurs.

Garde-fous livres:

- aucun appel Nextcloud, WebDAV ou CalDAV;
- aucun secret;
- aucune DB directe Nextcloud;
- aucun chemin serveur brut;
- aucune URL DAV;
- aucun `storage_key`;
- aucun contenu fichier;
- les routes existantes `/api/workspace-folders*` restent le point d'entree
  applicatif, sans creation de route Lot 4;
- les fichiers workspace, OCR, documents, exports, images, mail, Agenda et
  Biblio restent hors-scope.

Tests Lot 3:

- validation nom vide, invalide, trop long;
- collisions locales actives, collisions apres sanitisation et collisions
  case-insensitive;
- payload mapping logique `/Frida/<dossier>` sans URL DAV, chemin serveur,
  `storage_key` ni secret;
- renommage valide contre les memes regles;
- tombstone locale marquee `deleted` sans live Nextcloud;
- normalisation frontend des champs fake/local sans fuite de champs bruts.

Dette courte post-Lot 3 resolue en Lot 4:

- `app/core/workspace_folders_store.py` atteint `519` lignes apres la projection
  fake/local;
- le Lot 4 extrait la projection/sanitisation Nextcloud fake/local dans
  `app/core/workspace_folder_nextcloud_projection.py`;
- `app/core/workspace_folders_store.py` repasse sous 500 lignes et conserve la
  responsabilite persistence workspace folders;
- ne pas creer de fichier fourre-tout `utils.py` ou `helpers.py`.

## 12. Mise en oeuvre Lot 4 API/UI fake-local

Lot 4 livre le 2026-06-16 l'exposition API/UI fake-local sans Nextcloud live.

Routes/API:

- les routes existantes `/api/workspace-folders*` sont conservees;
- aucune route `/api/frida-folders` ou surface parallele n'est creee;
- `GET /api/workspace-folders` liste les dossiers actifs avec projection
  fake/local;
- `POST /api/workspace-folders` cree un dossier avec validation de nom,
  conflits et projection;
- `PATCH /api/workspace-folders/<id>` renomme avec les memes validations et met
  a jour la projection;
- `DELETE /api/workspace-folders/<id>` tombstone le dossier, sort les
  conversations du dossier, preserve les fichiers/documents workspace et
  retourne `workspace_folder_files_preserved`.

UI:

- le frontend conserve la sidebar existante;
- la confirmation de suppression dit explicitement que les fichiers et documents
  ne seront pas supprimes;
- le statut fake/local reste discret et textuel: `Local`,
  `En attente Nextcloud`, `Conflit`, `Erreur`;
- l'UI n'affiche ni chemin serveur, ni URL DAV, ni `storage_key`, ni secret, ni
  contenu utilisateur.

Dette UI bornee:

- `app/web/chat_workspace_folders_sidebar.js` reste au-dessus de 500 lignes
  comme renderer historique concentre;
- Lot 4 n'ouvre pas de refactor UI large pour eviter un deplacement hors-scope;
- si Lot 6 ou un futur lot UI rallonge encore cette surface, extraire une
  responsabilite dediee plutot que continuer a empiler dans le renderer.

Preuves Lot 4:

- tests route/API sur creation, renommage, suppression tombstone et projection;
- tests service garantissant que le module fichiers n'est pas appele par la
  suppression dossier;
- tests frontend sur normalisation content-free, libelles sobres et texte de
  confirmation;
- tests conversations/workspace files existants conserves.

Limites:

- aucun Nextcloud live;
- aucun Sauron;
- aucun secret;
- aucune DB Nextcloud;
- aucun Lot 5.

## 13. Lot 7 - Design d'etat runtime local/Nextcloud

Lot 7 recale la spec et la TODO apres les fondations Lots 0 a 6. Il ne livre
aucun runtime Nextcloud permanent.

Decisions produit integrees:

- creation: Nextcloud d'abord, local ensuite, refus complet si Nextcloud echoue;
- renommage: Nextcloud d'abord, local ensuite, ancien nom conserve si
  Nextcloud echoue;
- suppression: tombstone local / retrait Frida, pas de suppression recursive
  automatique du dossier Nextcloud reel.

Etat attendu avant Lot 8B:

- le runtime actuel reste fake/local pour les operations utilisateur;
- le smoke Lot 5 prouve seulement un chemin synthetique borne;
- le prochain lot runtime doit transformer les operations create/rename en
  operations Nextcloud-first sans creer d'etat divergent silencieux.

Etat depuis Lot 8B:

- creation et renommage produit passent par Nextcloud-first;
- les dossiers historiques `local_only` etaient a reconcilier en Lot 9;
- les fichiers/documents rattaches aux dossiers ne sont ni deplaces ni migres;
- les sous-dossiers standards restent a cadrer en Lot 11;
- la cloture V1 reste interdite avant politique fichiers et sous-dossiers
  standards.

Etat depuis Lot 9:

- les 2 dossiers UI actifs existants inventories le 2026-06-17 sont `linked`;
- les exemples attendus `Philosophie` et `Conflit lycee` / `Conflit lycée`
  etaient presents cote UI et ont ete reconcilies;
- les cibles Nextcloud manquantes ont ete creees par `MKCOL` borne, sans
  listing de contenu utilisateur;
- aucun fichier/document workspace n'a ete lu, deplace, supprime ou migre;
- Lot 10A a ensuite defini la politique des fichiers existants et des fichiers
  rattaches a un dossier sans migration ni transport fichier Nextcloud.

Etat depuis Lot 10A:

- inventaire read-only content-free: 2 dossiers actifs, 2 `linked`,
  10 fichiers workspace actifs rattaches a un dossier;
- fichiers existants: pas de migration automatique, pas de copie silencieuse,
  pas de suppression source silencieuse;
- nouveaux fichiers rattaches a un dossier Frida: cible produit = dossier
  Nextcloud du dossier Frida, mais transport fichier et migration restent des
  lots runtime separes;
- documents actifs, notes Markdown, exports et images restent des surfaces
  distinctes et ne sont pas livrees par le Lot 10A;
- Lot 11 a ensuite defini les sous-dossiers standards avant les contrats dedies
  Documents/Notes/Exports/Images.

Etat depuis Lot 11:

- sous-dossiers standards par dossier Frida: `Documents`, `Notes`, `Exports`,
  `Images`;
- creation d'un nouveau dossier Frida: dossier Nextcloud parent cree d'abord,
  puis sous-dossiers standards, puis creation locale si tout reussit;
- si un sous-dossier standard existe deja, l'etat est OK;
- si une cible standard est absente, `MKCOL` la cree;
- si une cible standard est incompatible ou bloquee, l'operation passe en
  `conflict` ou `sync_error` content-free, sans overwrite;
- preuve live: 2 dossiers `linked` inspectes et 8 sous-dossiers crees, sans
  listing de contenu ni action fichier;
- Lot 12 a ensuite confirme le routage des artefacts de dossier vers ces
  sous-dossiers, sans livrer les runtimes dedies.

Etat depuis Lot 12:

- routage documentaire cible confirme:
  `Documents`, `Notes`, `Exports`, `Images`;
- les contrats dedies Documents / Notes / Exports / Images travaillent
  seulement sur des dossiers Frida `linked`;
- un dossier non `linked`, en `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque toute ecriture Nextcloud d'artefact;
- les fichiers existants ne sont pas migres automatiquement;
- les constantes standards peuvent apparaitre dans les docs/preuves; les noms
  de fichiers, contenus, prompts bruts, chemins DAV, XML brut, `storage_key` et
  secrets restent interdits.

## 14. Lots du socle Folders avant cloture V1 reelle

Lot 8A - Persistance locale de l'etat Nextcloud:

- livre: table de liaison `workspace_folder_nextcloud_links`;
- livre: integration de cette liaison dans la projection existante des dossiers;
- livre: aucune route parallele et aucun transport live;
- livre: reason codes et etats content-free, avec redaction fail-closed des
  raisons inconnues.

Lot 8B - Runtime permanent creation/renommage Nextcloud:

- livre: injection runtime read-only du secret plateforme, sans
  valeur dans le depot;
- livre: creer le dossier Nextcloud avant la ligne locale;
- livre: renommer le dossier Nextcloud avant le nom local;
- livre: gerer les echecs par refus local ou conservation de l'ancien nom;
- livre: rollback/compensation borne create/rename;
- livre: preuve synthetique par le chemin applicatif, JSONL content-free.

Lot 9 - Reconciliation des dossiers existants:

- livre: inventaire content-free des dossiers UI actifs;
- livre: traitement explicite des exemples `Philosophie` et `Conflit lycee` /
  `Conflit lycée`;
- livre: verification Nextcloud par `PROPFIND` Depth 0 seulement, sans listing
  de contenu;
- livre: creation par `MKCOL` des cibles manquantes uniquement pour dossiers UI
  actifs existants;
- livre: liaison locale `workspace_folder_nextcloud_links` en `linked`;
- livre: aucune suppression Nextcloud reelle hors rollback strict, aucun
  rollback necessaire;
- livre: aucun fichier/document workspace lu, deplace, supprime ou migre;
- artefact:
  `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot9-reconcile-20260617T074733Z.jsonl`.

Lot 10 - Politique fichiers existants et fichiers rattaches par dossier:

- livre Lot 10A: audit read-only content-free des fichiers rattaches aux
  dossiers Frida;
- livre Lot 10A: les fichiers existants restent dans `workspace_files` et leur
  stockage applicatif courant jusqu'a un lot de copie/rangement dedie;
- livre Lot 10A: aucune migration automatique, copie silencieuse, lecture de
  contenu, deplacement ou suppression source;
- livre Lot 10A: les nouveaux fichiers associes a un dossier Frida devront etre
  ranges dans le dossier Nextcloud correspondant, mais le transport fichier
  Nextcloud reste hors de ce lot;
- livre Lot 10A: documents actifs, uploads/fichiers workspace, notes, exports et
  images sont separes;
- artefact:
  `app/docs/states/audits/frida-v1-nextcloud-folders-lot10-files-policy-2026-06-17.md`.

Lot 11 - Sous-dossiers standards par dossier:

- livre: sous-dossiers standards `Documents`, `Notes`, `Exports`, `Images`;
- livre: creation automatique lors de la creation Nextcloud-first d'un nouveau
  dossier Frida;
- livre: helper de verification/creation bornee pour dossiers Frida existants
  `linked`;
- livre: sous-dossier deja existant = OK;
- livre: cible absente = `MKCOL`;
- livre: `PROPFIND` `207` accepte seulement si la ressource WebDAV est une
  collection; le XML est parse en memoire et jamais expose;
- livre: ressource non-collection = conflit/incompatibilite content-free;
- livre: conflit/incompatibilite = `conflict` ou `sync_error` content-free, sans
  overwrite;
- livre: preuve live content-free, 2 dossiers `linked`, 8 sous-dossiers crees,
  aucun fichier touche;
- artefact:
  `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot11-standard-subfolders-20260617T091722Z.jsonl`.

Lot 12 - Preparation Notes / Exports / Images:

- livre: routage Documents sources et fichiers persistants vers
  `/Frida/<dossier>/Documents`;
- livre: routage Notes Markdown vers `/Frida/<dossier>/Notes`;
- livre: routage Exports Markdown, TXT, DOCX et PDF vers
  `/Frida/<dossier>/Exports`;
- livre: routage Images generees vers `/Frida/<dossier>/Images`;
- livre: prerequis `linked` strict avant ecriture Nextcloud d'artefact;
- livre: blocage des etats `local_only`, `sync_pending`, `sync_error`,
  `conflict` et `deleted`;
- livre: alignement des TODO dediees Documents, Notes, Exports et Images;
- ne pas livrer ces chantiers runtime dans le socle dossiers.

Lot Z - Cloture V1 reelle:

- livre: validation empirique par le runtime reel et les routes existantes
  `/api/workspace-folders*`;
- livre: creation UI d'un dossier synthetique -> creation Nextcloud reelle,
  sous-dossiers standards, puis dossier local `linked`;
- livre: conflit de creation refuse avec reason code content-free, sans second
  dossier Nextcloud;
- livre: renommage UI d'un dossier synthetique -> `MOVE` Nextcloud effectif,
  ancien target absent status-only, nouveau target `linked`;
- livre: suppression produit -> tombstone local, fichiers/documents preserves,
  aucune suppression recursive Nextcloud;
- livre: cleanup test-only strictement borne au dossier synthetique cree par le
  run de validation, avec absence finale status-only;
- livre: dossiers UI actifs existants `linked` verifies status-only, sans
  listing de contenu;
- livre: observabilite et payloads content-free, sans URL DAV brute, chemin
  serveur, XML brut, `storage_key`, secret, token, cookie, app-password, nom de
  fichier ou contenu utilisateur;
- artefact:
  `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lotz-live-closure-20260617T104258Z.jsonl`;
- trace annexe non cloturante conservee:
  `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lotz-live-closure-20260617T104124Z.jsonl`.

## 15. Politique fichiers par dossier depuis Lot 10A

### 15.1 Fichiers existants

Les fichiers workspace deja rattaches a un dossier Frida restent dans
`workspace_files` et dans le stockage applicatif courant. Le Lot 10A interdit de
les migrer automatiquement vers Nextcloud.

Un lot de migration/copie, seulement si decide explicitement, devra:

- travailler dossier par dossier, uniquement si le dossier Frida est `linked`;
- produire une preuve content-free avant et apres;
- ne jamais lister ni afficher de contenu utilisateur;
- ne jamais ecraser une cible Nextcloud existante sans decision humaine;
- conserver la source tant que la preuve et le rollback ne sont pas actees;
- ne supprimer la source qu'apres decision explicite si une suppression devient
  necessaire.

### 15.2 Nouveaux fichiers rattaches a un dossier

La cible produit des nouveaux fichiers associes a un dossier Frida est le
dossier Nextcloud reel du dossier Frida. Le comportement runtime fichier n'etait
pas livre par Lot 10A: pas de `PUT`, `GET`, `MOVE`, `DELETE` ou listing fichier
Nextcloud dans ce lot.

Les capacites Documents, Notes, Exports et Images ont ensuite ete livrees par
leurs contrats dedies lorsqu'elles rangent un artefact sous un sous-dossier
standard. La copie/rangement des fichiers workspace existants reste separee et
ne peut pas etre deduite du seul socle Folders.

### 15.3 Documents, notes, exports et images

- Les documents actifs de conversation restent scopes par conversation et ne
  deviennent pas automatiquement des fichiers de dossier Frida.
- Les fichiers workspace persistants sont traites par le contrat Documents V1
  quand ils deviennent documents persistants de dossier.
- Les notes Markdown sont portees par
  `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`.
- Les exports sont portes par
  `app/docs/states/specs/frida-v1-exports-contract.md`, avec cible
  `/Frida/<dossier>/Exports`.
- Les images generees sont portees par
  `app/docs/states/specs/frida-v1-generated-images-contract.md`.

### 15.4 Observabilite et preuves

Les lots de fichiers ou artefacts rattaches doivent rester content-free:

- aucun contenu fichier;
- aucun nom de fichier sensible dans les preuves si une reference hashée suffit;
- aucun `storage_key`, chemin disque, URL DAV, XML, token, cookie,
  `app-password` ou secret;
- aucun listing de contenu Nextcloud;
- reason codes stables et redaction fail-closed des erreurs transport.

## 16. Sous-dossiers standards depuis Lot 11

Pour chaque dossier Frida `linked`, les cibles standards sont:

- `Documents`;
- `Notes`;
- `Exports`;
- `Images`.

Ces noms sont les seuls noms humains autorises dans les preuves Lot 11, car ils
sont des constantes produit et non du contenu utilisateur.

Creation d'un nouveau dossier Frida:

- creer le dossier Nextcloud parent;
- verifier/creer les quatre sous-dossiers standards;
- creer le dossier local seulement si le parent et les sous-dossiers standards
  reussissent;
- si un sous-dossier standard echoue, conserver le parent et les descendants
  deja crees : leur propriete exclusive n'est pas prouvee et aucun DELETE
  recursif automatique n'est autorise.

Dossiers existants:

- verifier seulement les dossiers Frida `linked`;
- faire `PROPFIND` Depth 0 sur chaque sous-dossier standard;
- accepter `207` comme deja present seulement si la ressource WebDAV est une
  collection;
- parser le XML `PROPFIND` en memoire uniquement, sans jamais le logger, le
  stocker, le retourner dans une reponse API, l'inclure dans une preuve JSONL ou
  le documenter comme payload brut;
- traiter une cible `207` non-collection comme conflit/incompatibilite
  content-free;
- faire `MKCOL` si absent;
- ne jamais faire `PROPFIND` Depth 1, `GET`, `PUT`, `MOVE`, `DELETE` ou listing
  de contenu dans ce lot;
- ne jamais ecraser une cible existante.

Reason codes standards:

- `workspace_folder_standard_subfolders_ok`;
- `workspace_folder_standard_subfolder_existing_ok`;
- `workspace_folder_standard_subfolder_created_ok`;
- `workspace_folder_standard_subfolder_conflict`;
- `workspace_folder_standard_subfolders_unavailable`;
- `workspace_folder_standard_subfolders_auth_failed`.

Limite:

- Lot 11 cree seulement les conteneurs standards;
- il ne range aucun fichier dans `Documents`;
- il ne cree aucune note Markdown dans `Notes`;
- il ne genere aucun export dans `Exports`;
- il ne stocke aucune image generee dans `Images`.

Dette structurelle post-correctif Lot 11:

- `app/core/workspace_folder_nextcloud_reconcile.py` est deja au-dessus du seuil
  de 500 lignes;
- le correctif collection reste dans le client WebDAV et les tests, sans
  rallonger la reconciliation;
- le prochain lot qui ajoute du comportement de reconciliation doit extraire
  une responsabilite claire avant d'etendre ce fichier.

## 17. Routage des artefacts depuis Lot 12

Lot 12 a prepare les contrats dedies Documents / Notes / Exports / Images. Il
ne livrait aucun runtime fichier, aucune migration et aucun acces Nextcloud live.

Mapping produit normatif:

| Artefact | Sous-dossier cible |
| --- | --- |
| Documents sources et fichiers persistants | `/Frida/<dossier>/Documents` |
| Notes Markdown | `/Frida/<dossier>/Notes` |
| Exports Markdown, TXT, DOCX, PDF | `/Frida/<dossier>/Exports` |
| Images generees | `/Frida/<dossier>/Images` |

Prerequis d'ecriture:

- le dossier Frida doit etre `linked`;
- `nextcloud_folder_ref` doit referencer la cible logique redacted du dossier;
- les sous-dossiers standards doivent etre verifies comme collections WebDAV si
  le lot fait du live;
- un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou `deleted`
  bloque toute ecriture Nextcloud d'artefact;
- les conflits de nom ou de cible WebDAV sont traites par reason code
  content-free, sans correction silencieuse.

Fichiers existants:

- aucune migration automatique n'est autorisee par Lot 12;
- un lot de migration/copie, seulement si decide explicitement, devra travailler
  dossier par dossier,
  produire une preuve content-free, conserver la source tant que rollback et
  verification ne sont pas actees, et ne jamais supprimer silencieusement;
- les fichiers workspace existants restent sous le contrat courant tant qu'un
  lot dedie n'a pas livre leur copie/rangement Nextcloud.

Contraintes content-free communes:

- les constantes `Documents`, `Notes`, `Exports` et `Images` peuvent apparaitre
  dans les docs, preuves et reason codes car elles sont des constantes produit;
- les noms de fichiers, contenus, prompts bruts, chemins DAV, URL DAV, XML brut,
  `storage_key`, payload Nextcloud brut, token, cookie, app-password et secret
  restent interdits dans logs, JSONL, dashboard, erreurs et docs de preuve;
- les preuves doivent preferer compteurs, refs redacted, hash courts et classes
  de statut;
- aucune operation ne doit lister le contenu Nextcloud pour prouver ce routage.

Frontieres par chantier:

- Documents: depot, lecture/preparation, fallback visuel et fichiers
  persistants sous `Documents` sont portes par
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`;
- Notes: creation, liste, lookup, append et lecture Markdown sous `Notes` sont
  portes par
  `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`;
- Exports: Markdown, TXT, DOCX et PDF sous `Exports` sont portes par
  `app/docs/states/specs/frida-v1-exports-contract.md`;
- Images: stockage, liste, lookup, open/download/delete et UI dossier des images
  generees sous `Images` sont portes par
  `app/docs/states/specs/frida-v1-generated-images-contract.md`.

Dette architecture:

- tout futur lot qui modifie la reconciliation doit extraire une responsabilite
  avant d'etendre `app/core/workspace_folder_nextcloud_reconcile.py`;
- Lot 12 ne modifie pas ce fichier et ne change pas le comportement runtime.
