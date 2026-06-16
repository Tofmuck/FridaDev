# Frida V1 - Nextcloud folders contract

Statut: spec vivante Lot 1
Date: 2026-06-16
Classement: `app/docs/states/specs/`
TODO source: `app/docs/todo-todo/product/frida-v1-nextcloud-folders-todo.md`
Audit source: `app/docs/states/audits/frida-v1-nextcloud-folders-lot0-audit-2026-06-16.md`
Contrat existant relu: `app/docs/states/specs/workspace-folders-contract.md`

## 1. Perimetre

Ce contrat est docs-only. Il ne modifie pas le runtime, ne cree pas de route, ne
change pas la DB, ne contacte pas Nextcloud, ne provisionne aucun compte et ne
modifie pas la plateforme.

Il fixe le contrat produit minimal du socle Frida 1.0:

```text
un dossier frontend Frida = un sous-dossier Nextcloud sous la racine logique Frida
```

Les lots documents, notes Markdown, exports, images generees, mail, Agenda et
Biblio restent separes.

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

- le contrat de suppression actuel peut supprimer des fichiers workspace locaux;
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
- le provisionnement du compte Frida, de la racine, des droits et du partage
  appartient a Sauron dans un lot ulterieur;
- FridaDev ne doit pas acceder directement a la DB Nextcloud;
- FridaDev ne doit pas exposer de chemin brut serveur;
- les logs, JSONL, dashboards et rapports utilisent un alias logique redacted ou
  une reference courte, jamais une URL DAV ni un chemin serveur;
- Lot 1 ne lit ni n'ecrit Nextcloud.

Le nom Nextcloud cible n'est pas seulement le `display_name` brut. Les lots
runtime devront definir une normalisation reproductible, au minimum:

- suppression des espaces superflus;
- longueur bornee;
- refus des caracteres incompatibles avec le stockage cible;
- cle de comparaison casefolded pour detecter les collisions;
- conservation du `display_name` utilisateur pour l'affichage.

Renommage:

- renommer un `workspace_folder` renomme le dossier Frida cote produit;
- si le dossier est deja lie a Nextcloud dans un lot futur, le renommage doit
  prevoir le renommage du sous-dossier Nextcloud cible ou une erreur explicite;
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
- toute suppression reelle Nextcloud est reservee a un lot live ulterieur, avec
  confirmation humaine et cible synthetique bornee.

## 4. Modele produit minimal

Le choix exact DB/runtime viendra en Lot 3. Ce Lot 1 definit seulement les
logiques attendues.

Logiques deja portees ou candidates dans `workspace_folders`:

- identifiant stable applicatif: `workspace_folders.id`;
- nom affiche: `display_name`;
- description UI-only: `description`, non injectee au modele;
- icone allowlistee: `icon_key`;
- ordre UI: `sort_order`;
- timestamps locaux: `created_at`, `updated_at`, `deleted_at`;
- statut local derive: `active`, `deleted` ou `tombstone`.

Logiques Nextcloud attendues, a implementer plus tard:

- nom ou slug sanitise pour le sous-dossier cible;
- etat de synchronisation Nextcloud:
  - `unknown`: pas encore verifie ou non configure;
  - `pending`: operation locale acceptee, lien Nextcloud pas encore confirme;
  - `linked`: sous-dossier Nextcloud associe;
  - `conflict`: collision ou cible ambigue;
  - `error`: erreur redacted;
  - `deleted`: dossier local supprime ou lien retire;
- reference logique Nextcloud redacted, par exemple alias court ou hash court;
- etat de partage avec `tof`:
  - `unknown`: partage non verifie;
  - `expected`: partage attendu par contrat;
  - `confirmed`: partage confirme par preuve Sauron ou smoke borne futur;
  - `error`: partage attendu mais non confirme;
- timestamps d'observation ou de transition si necessaires;
- reason code content-free pour toute erreur ou attente.

Contraintes:

- ne pas stocker de secret dans FridaDev;
- ne pas stocker de chemin brut serveur dans une surface affichee ou logguee;
- ne pas exposer `storage_key`, chemin disque, URL DAV, contenu fichier ou
  extrait utilisateur;
- ne pas confondre etat local du dossier et etat de synchronisation Nextcloud.

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
- en fake/local, le dossier peut etre cree sans Nextcloud live;
- en live futur, la creation devra correspondre a un sous-dossier
  `/Frida/<display_name_sanitise>`;
- la reponse utilisateur ne doit pas afficher de chemin serveur.

Listing:

- la liste active vient du modele applicatif `workspace_folders`;
- les dossiers supprimes ne sont pas listes par defaut;
- l'etat Nextcloud peut etre affiche comme statut produit, mais sans detail
  sensible;
- un etat `unknown` est acceptable avant decision Sauron/live.

Renommage:

- le renommage doit repasser par la validation et detection de conflit;
- si le dossier est lie a Nextcloud plus tard, le lien ne peut pas etre suppose
  valide tant que le renommage cible n'est pas confirme;
- en cas de conflit, l'ancien nom reste actif.

Suppression:

- la suppression locale peut tombstoner le `workspace_folder`;
- les conversations restent conservees et sorties du dossier selon le contrat
  existant;
- aucune suppression reelle Nextcloud ne doit se produire sans lot live explicite
  et confirmation humaine;
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

Lot 3:

- implementation fake/local du modele applicatif;
- tests automatises sur creation, listing, renommage, suppression, conflits et
  etats;
- aucun secret;
- aucun appel Nextcloud live;
- logs et fixtures content-free.

Lot 5:

- ouverture live seulement apres Lots 0 a 4 et decision Sauron;
- preuve Sauron read-only avant toute ecriture;
- smoke live borne sur dossier synthetique;
- creation, renommage, suppression uniquement de ce dossier synthetique;
- rollback documente;
- aucun contenu utilisateur lu, deplace, supprime ou loggue.

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

Evenements minimaux futurs:

- `workspace_folder_create_requested`;
- `workspace_folder_created`;
- `workspace_folder_rename_requested`;
- `workspace_folder_renamed`;
- `workspace_folder_delete_requested`;
- `workspace_folder_deleted`;
- `workspace_folder_name_conflict`;
- `workspace_folder_sync_state_changed`;
- `workspace_folder_share_state_changed`;
- `workspace_folder_error`.

Champs autorises:

- id applicatif court ou hash court;
- operation;
- statut;
- sync state;
- share state;
- reason code;
- compteur borne si necessaire;
- latence ou duree;
- type d'erreur redacted.

Champs interdits:

- contenu de fichier;
- extrait utilisateur;
- chemin brut serveur;
- URL DAV;
- chemin disque;
- `storage_key`;
- secret;
- nom sensible si le contexte peut l'etre;
- payload brut Nextcloud;
- detail serveur sensible.

Les preuves JSONL ou rapports doivent rester content-free et passer un scan
anti-fuite avant commit.

## 9. Limites V1 et hors-scope

Ce contrat ne livre pas:

- ingestion documents;
- notes Markdown;
- exports;
- images generees;
- rattachement mail;
- Agenda;
- Biblio;
- refonte Nextcloud;
- migration massive;
- routes/API nouvelles;
- UI nouvelle;
- migration DB;
- live Nextcloud;
- creation de compte;
- modification droits/partage live;
- Docker/rebuild.

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

Etat de cette spec: ces conditions sont remplies pour ouvrir Lot 3 fake/local
dans un prompt separe, sans ouvrir Lot 2, Lot 5 ou un patch runtime.

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
- une migration serait prematuree avant decision Sauron et avant Lot 5 live.

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

## 12. Decisions techniques restantes avant Lot 4/5

- choisir la forme exacte d'exposition UI Lot 4 des nouveaux etats fake/local;
- definir si Lot 4 doit afficher le mapping logique ou seulement un statut
  redacted;
- obtenir plus tard la decision Sauron sur compte Frida, racine, droits,
  partage et secrets runtime avant tout Lot 5;
- definir le module d'observabilite dedie ou l'extension des conventions
  existantes en Lot 6;
- decider en Lot 5 si un etat `linked` peut devenir une preuve live, et sous
  quelle preuve content-free.
