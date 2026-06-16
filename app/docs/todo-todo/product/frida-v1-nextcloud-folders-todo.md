# Frida V1 - Socle Nextcloud / dossiers / droits - TODO

Statut: TODO actif
Date: 2026-06-16
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## 1. Decision V1

Le dossier est l'unite de travail Frida 1.0.

Regle produit:

- un dossier frontend Frida correspond a un repertoire Nextcloud;
- ce socle est obligatoire pour Frida 1.0;
- ce lot ne livre pas l'ingestion de documents, les notes Markdown, les exports,
  les images generees ni le mail;
- ce lot cadre seulement le modele dossier, les droits, les chemins, les
  operations de base et l'observabilite;
- un compte Nextcloud Frida est a prevoir pour les fichiers/dossiers, distinct
  de la decision Agenda V1 qui utilise le compte humain `tof`;
- le repertoire Frida doit etre partage avec Tof selon une decision plateforme
  explicite;
- FridaDev ne doit jamais acceder directement a la DB Nextcloud;
- aucun secret Nextcloud ne doit apparaitre dans les docs, logs, JSONL,
  prompts, sorties terminal ou reponses;
- toute observabilite liee aux dossiers doit rester content-free.

Ce socle doit ensuite permettre, dans des lots separes:

- documents sources;
- notes Markdown;
- exports;
- images generees;
- rattachement eventuel de mails;
- observabilite content-free transversale.

Recalage produit post Lot 6:

- les Lots 0 a 6 sont des fondations: audit, contrat, compte/droits Sauron,
  projection fake/local, API/UI fake-local, smoke live synthetique et
  observabilite content-free;
- ils ne cloturent pas le besoin produit Frida 1.0;
- la V1 produit n'est pas livree tant que la creation UI d'un dossier Frida ne
  cree pas reellement le sous-dossier Nextcloud `/Frida/<nom_sanitise>`;
- la V1 doit relier les dossiers UI Frida existants et futurs a des dossiers
  Nextcloud reels;
- les dossiers existants doivent etre reconcilies dans un lot dedie, sans
  deplacement ni suppression implicite de fichiers.

## 2. Lots proposes

Les Lots 0 a 6 sont livres comme fondations. Les Lots 7 et suivants cadrent le
runtime permanent et les dependances produit restantes; ne cocher que les lots
effectivement prouves.

### Lot 0 - Audit read-only existant Nextcloud / FridaDev

Audit Lot 0:
`app/docs/states/audits/frida-v1-nextcloud-folders-lot0-audit-2026-06-16.md`

- [x] Inventorier les surfaces FridaDev deja liees aux dossiers de travail,
  fichiers persistants, documents actifs, exports et observabilite.
- [x] Relire les decisions Nextcloud/Agenda pertinentes sans acceder au live.
- [x] Confirmer les invariants: pas de DB directe Nextcloud, pas de secret en
  docs/logs, preuves content-free.
- [x] Identifier les points de reutilisation possibles cote FridaDev sans
  rouvrir les chantiers archives.
- [x] Produire un constat court: reuse possible, manques, risques, no-go avant
  code.

### Lot 1 - Contrat produit dossier Frida

Spec Lot 1:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

- [x] Trancher explicitement: extension de `workspace_folders` ou nouveau
  modele `frida_folder` / dossier Nextcloud dedie, avec justification et effets
  de bord.
- [x] Definir le modele produit minimal d'un dossier Frida: identifiant stable,
  nom affiche, statut, chemin logique Nextcloud, droits attendus et timestamps.
- [x] Definir les operations V1: creer, lister, renommer, supprimer un dossier
  synthetique Frida.
- [x] Definir le contrat de conflit de nom: detection explicite, message
  utilisateur clair, reason code content-free, aucune correction silencieuse.
- [x] Definir ce qui reste local/fake avant live et ce qui depend d'une
  decision Sauron.
- [x] Documenter les limites V1 avant toute implementation runtime.

### Lot 2 - Decision Sauron compte Frida / droits / partage

- [x] Demander explicitement a Sauron de trancher/provisionner le compte
  Nextcloud Frida si le lot live est ouvert.
- [x] Demander explicitement a Sauron de definir le repertoire racine Frida, le
  partage avec Tof et les droits exacts.
- [x] Demander explicitement a Sauron de gerer secrets, app-passwords, backups
  si necessaire et verification serveur.
- [x] Obtenir une preuve read-only content-free avant toute ecriture Nextcloud.
- [x] Ne stocker dans FridaDev que des indicateurs redacted et des chemins
  logiques non sensibles.

Note Lot 2 Sauron livre le 2026-06-16:
`/opt/platform/_codex_reports/frida-v1-nextcloud-folders-lot2-sauron-20260616T151803Z.md`

- compte Nextcloud `frida` cree;
- dossier `Frida` cree dans l'espace du compte `frida`;
- partage utilisateur vers `tof` cree avec permissions `15`: lecture,
  ecriture/update, creation, suppression, sans reshare;
- aucun lien public;
- secret compte et app-password dediee stockes cote plateforme, valeurs jamais
  affichees ni copiees dans FridaDev;
- preuve read-only content-free OK: DAV status-only `207`, aucun contenu
  utilisateur affiche, aucun fichier utilisateur deplace ou supprime;
- limite: partage prouve par `occ`/OCS, pas par login DAV du compte `tof`.

### Lot 3 - Modele backend FridaDev fake/local

- [x] Implementer le modele applicatif de dossiers sans appel Nextcloud live.
- [x] Ajouter une projection/service fake-local derive depuis
  `workspace_folders` pour creer, lister, renommer et supprimer des dossiers
  synthetiques.
- [x] Couvrir conflits de noms, erreurs, suppression refusee et etats
  incoherents par tests automatises.
- [x] Garder les logs, erreurs et fixtures content-free.
- [x] Ne pas brancher de secret ni de chemin serveur reel dans ce lot.

Note post-Lot 4: la projection Nextcloud fake/local a ete extraite dans
`app/core/workspace_folder_nextcloud_projection.py`; le store revient sous le
seuil de 500 lignes. Ne pas creer de `utils.py` ni de `helpers.py`.

### Lot 4 - Routes/API frontend/backend pour dossiers

- [x] Ajouter les routes applicatives minimales pour lister, creer, renommer et
  supprimer un dossier Frida via le backend fake/local.
- [x] Ajouter la surface frontend minimale correspondante si le backend Lot 3
  est stable.
- [x] Afficher les conflits et erreurs sans fuite de chemin brut, contenu,
  secret ou detail serveur sensible.
- [x] Exiger une confirmation humaine avant toute suppression reelle ou future
  suppression live.
- [x] Prouver la compatibilite avec les dossiers/conversations existants sans
  deplacement massif.

Lot 4 livre les routes existantes `/api/workspace-folders*` sans surface
parallele. La suppression V1 tombstone le dossier et sort les conversations du
dossier selon le comportement existant; elle ne supprime pas les fichiers,
documents workspace, notes, exports ou contenus. L'UI garde un statut fake/local
discret (`Local`, `En attente Nextcloud`, `Conflit`, `Erreur`) sans chemin
serveur, URL DAV, secret, `storage_key` ni contenu utilisateur.

### Lot 5 - Preuve live Nextcloud bornee

- [x] Ouvrir ce lot seulement apres validation Lots 0 a 4 et decision Sauron.
- [x] Verifier en read-only les droits Frida/Tof et le repertoire cible.
- [x] Executer un smoke live borne sur un dossier synthetique dedie.
- [x] Creer, renommer puis supprimer uniquement ce dossier synthetique.
- [x] Documenter le rollback et verifier qu'aucun contenu utilisateur n'a ete
  lu, deplace, supprime ou loggue.

Preuve Lot 5 live bornee:
`app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lot5-live-20260616T154117Z.jsonl`

- cible synthetique creee: `frida-v1-smoke-20260616T154117Z`;
- cible synthetique renommee: `frida-v1-smoke-20260616T154117Z-renamed`;
- operations prouvees content-free: readonly droits/racine, creation,
  renommage, suppression, verification finale d'absence;
- cleanup final: `done`;
- aucun contenu utilisateur lu, liste, deplace, supprime ou loggue;
- aucun fichier/document workspace touche;
- aucun lien public cree;
- aucun secret ni app-password copie dans FridaDev;
- limite: preuve DAV/OCS interne status-only; pas de branchement runtime
  permanent ni d'operation UI live dans ce lot.

### Lot 6 - Observabilite content-free et erreurs

- [x] Definir les reason codes dossiers: succes, conflit de nom, droits
  insuffisants, cible absente, cible deja existante, suppression refusee,
  erreur Nextcloud redacted.
- [x] Exposer seulement des compteurs, statuts, ids courts, hashes courts si
  necessaire et categories d'erreurs.
- [x] Interdire contenu de fichier, nom sensible, chemin brut serveur, URL DAV,
  token, cookie, Authorization et app-password.
- [x] Ajouter un scan anti-fuite adapte aux artefacts JSONL ou rapports.
- [x] Relier cette observabilite au chantier global
  `frida-v1-agentic-observability-todo.md` sans le rouvrir ici.

Lot 6 livre une projection d'observabilite content-free pour les routes
existantes `/api/workspace-folders*`, sans route parallele ni route admin. Le
read-model expose operation, statut, classe HTTP, reason code, compteurs, etats
fake/local, hash courts et compteurs de suppression; il n'expose pas de
`display_name`, chemin serveur, URL DAV, `storage_key`, secret, contenu fichier
ou payload Nextcloud brut. Le service journalise le meme resume content-free.
Le frontend normalise uniquement les champs allowlistes si cette projection est
presente. Cette brique est referencee comme preuve locale du chantier global
`frida-v1-agentic-observability-todo.md`, sans ouvrir la refonte globale.

Micro-correctif post Lot 6: l'observabilite fail-closed les reason codes
inconnus vers `workspace_folder_nextcloud_error_redacted`, n'expose
`nextcloud_name_hash` que si le format de hash court est strictement conforme,
et le frontend parse les booleens de projection sans transformer `"false"` en
`true`.

### Lot 7 - Design d'etat runtime local/Nextcloud

- [x] Inscrire que Lots 0 a 6 sont des fondations et pas la fin produit V1.
- [x] Inscrire les decisions produit runtime: creation Nextcloud d'abord,
  renommage Nextcloud d'abord, suppression locale tombstone sans suppression
  recursive Nextcloud reelle.
- [x] Definir les etats cibles `local_only`, `linked`, `sync_pending`,
  `sync_error`, `conflict` et `deleted`.
- [x] Definir les champs candidats: `nextcloud_sync_state`,
  `nextcloud_folder_ref`, `nextcloud_name_hash`, `last_sync_at`,
  `last_sync_reason_code`.
- [x] Cadrer les lots runtime restants sans migration DB ni code live dans ce
  patch.

Note Lot 7: ce lot est docs/design only. Il prepare le runtime permanent, mais
ne branche pas encore FridaDev sur Nextcloud en continu, ne lit pas de secret et
n'effectue aucun acces live.

### Lot 8 - Runtime permanent creation/renommage Nextcloud

- [ ] Verifier l'injection runtime sure des credentials plateforme prepares par
  Sauron, sans valeur dans FridaDev.
- [ ] Sur creation UI, creer d'abord `/Frida/<nom_sanitise>` dans Nextcloud,
  puis creer le dossier local seulement si Nextcloud reussit.
- [ ] Si la creation Nextcloud echoue, refuser la creation locale, afficher une
  erreur simple et tracer un reason code content-free.
- [ ] Sur renommage UI, renommer d'abord le dossier Nextcloud, puis renommer le
  dossier local seulement si Nextcloud reussit.
- [ ] Si le renommage Nextcloud echoue, conserver l'ancien nom local, afficher
  une erreur simple et tracer un reason code content-free.
- [ ] Separer les conflits locaux des conflits Nextcloud et ne jamais corriger
  silencieusement un nom.
- [ ] Prouver le chemin applicatif sur dossier synthetique uniquement, sans
  contenu utilisateur ni secret.

### Lot 9 - Reconciliation des dossiers existants

- [ ] Inventorier les dossiers UI Frida existants de facon content-free.
- [ ] Traiter explicitement les exemples attendus comme `Philosophie` et
  `Conflit lycee` s'ils existent cote UI Frida.
- [ ] Verifier s'ils existent deja cote Nextcloud par preuve status-only, sans
  lister de contenu utilisateur.
- [ ] Proposer la creation des dossiers manquants sans deplacer leurs fichiers
  existants.
- [ ] Ne pas ecraser un dossier Nextcloud existant et ne pas resoudre un
  conflit sans decision humaine.

### Lot 10 - Politique fichiers existants et futurs par dossier

- [ ] Decider comment les fichiers deja rattaches aux dossiers Frida seront
  representes ou migres vers Nextcloud.
- [ ] Decider comment les futurs fichiers associes a un dossier Frida seront
  ranges sous le dossier Nextcloud correspondant.
- [ ] Garantir qu'aucun fichier/document workspace n'est deplace, lu ou supprime
  sans lot dedie et preuve content-free.
- [ ] Documenter l'interaction avec les documents actifs et uploads sans rouvrir
  l'ingestion documentaire.

### Lot 11 - Sous-dossiers standards par dossier

- [ ] Definir les sous-dossiers standards cibles par dossier Frida, par exemple
  `Documents`, `Notes`, `Exports` et `Images`.
- [ ] Decider s'ils sont crees a la creation du dossier ou a la premiere
  utilisation.
- [ ] Definir les conflits et erreurs si un sous-dossier standard existe deja.
- [ ] Ne pas creer ces sous-dossiers avant preuve et decision du lot.

### Lot 12 - Preparation Notes / Exports / Images

- [ ] Aligner les futurs lots Notes Markdown sur le dossier Nextcloud du dossier
  Frida.
- [ ] Aligner les futurs exports sur un sous-dossier dedie, par exemple
  `/Frida/<dossier>/Exports`, ou variante documentee.
- [ ] Aligner les images generees sur un sous-dossier dedie, sans livrer la
  generation ni le stockage image dans ce lot.
- [ ] Garder documents, notes, exports, images et mail comme chantiers separes.

### Lot Z - Cloture V1 reelle

- [ ] Verifier que la creation UI cree reellement le dossier Nextcloud avant de
  creer le dossier local.
- [ ] Verifier que le renommage UI renomme Nextcloud avant de renommer le local.
- [ ] Verifier que la suppression V1 tombstone localement sans suppression
  recursive Nextcloud reelle.
- [ ] Verifier que les dossiers existants sont reconcilies ou declares no-go.
- [ ] Verifier que la politique fichiers et les sous-dossiers standards sont
  documentes.
- [ ] Documenter les limites V1 et les operations non livrees.
- [ ] Archiver les preuves content-free.
- [ ] Mettre a jour la roadmap generale si le statut du lot change.
- [ ] Ne pas cloturer documents, notes, exports, images ou mail par confusion
  avec ce socle.

## 3. Frontieres Sauron / Celebrimbor

Sauron est responsable de la plateforme OVH et Nextcloud:

- compte Nextcloud Frida;
- droits, groupes, partages et repertoire racine;
- secrets, app-passwords, rotation et stockage runtime;
- verification serveur Nextcloud;
- backups ou rollback plateforme si besoin;
- toute modification de configuration Nextcloud, Docker, Caddy, Authelia ou
  plateforme.

Celebrimbor est responsable du depot applicatif FridaDev:

- code FridaDev;
- modele de dossiers;
- API backend et UI frontend applicatives;
- tests fake/local et smokes applicatifs bornes;
- observabilite applicative content-free;
- documentation applicative dans `app/docs/`.

Regle de frontiere:

- aucun agent ne touche a la partie de l'autre sans prompt explicite;
- Celebrimbor ne cree pas de compte Nextcloud et ne modifie pas la plateforme;
- Sauron ne modifie pas le code FridaDev sans demande explicite;
- toute modification plateforme exige backup, documentation et verification
  adaptee par Sauron.

## 4. Garde-fous

- Pas de suppression reelle sans confirmation humaine explicite.
- Pas de suppression recursive large.
- Pas de deplacement massif de dossiers ou fichiers utilisateur.
- Pas de chemin brut sensible dans les logs, JSONL, dashboard ou reponses.
- Pas de contenu de fichiers dans les logs, JSONL, dashboard ou reponses.
- Pas de secret Nextcloud dans le repo, les docs, les logs, les prompts ou les
  sorties terminal.
- Pas de DB directe Nextcloud.
- Pas de scraping de l'UI Nextcloud.
- Les erreurs doivent etre content-free et actionnables par reason code.
- Le conflit de nom doit etre traite explicitement, jamais masque par un
  renommage silencieux.
- Toute operation live doit viser un dossier synthetique dedie au smoke.
- Toute modification plateforme future doit inclure rollback/documentation et
  rester dans le perimetre Sauron.

## 5. Preuves attendues

- Tests fake/local avant tout live.
- Preuve Sauron read-only avant toute ecriture Nextcloud.
- Smoke live borne sur dossier synthetique dedie.
- Creation, renommage et suppression du dossier synthetique avec rollback
  documente.
- Verification des droits Tof/Frida par preuve content-free.
- JSONL ou rapport content-free avec statuts, reason codes, ids courts et
  aucun contenu utilisateur.
- Scan anti-fuite sur artefacts et diff: pas de token, password, app-password,
  Authorization, Cookie, private key, secret ou `value_encrypted` reel.
- Documentation des limites et no-go avant cloture.

## 6. Point de sortie V1

Le lot est fermable quand FridaDev peut, dans le perimetre explicitement ouvert:

- creer un dossier Frida depuis l'UI en creant d'abord le sous-dossier
  Nextcloud reel `/Frida/<nom_sanitise>`, puis en creant le dossier local
  seulement si Nextcloud reussit;
- lister les dossiers Frida;
- renommer un dossier Frida en renommant d'abord le dossier Nextcloud, puis le
  local seulement si Nextcloud reussit;
- refuser creation ou renommage local si Nextcloud echoue, avec erreur
  utilisateur simple et reason code content-free;
- supprimer cote UI par tombstone local / retrait Frida sans suppression
  recursive automatique du dossier Nextcloud reel;
- associer clairement un dossier frontend Frida a un repertoire Nextcloud reel;
- reconcilier les dossiers UI existants avec Nextcloud sans ecraser, lire,
  deplacer ou supprimer de contenu utilisateur;
- documenter la politique des fichiers existants et futurs par dossier;
- gerer un conflit de nom sans fuite de contenu;
- tracer les operations en content-free;
- documenter les limites V1.

Ce point de sortie ne traite pas directement:

- ingestion documentaire;
- notes Markdown;
- exports;
- images;
- mail.

## 7. Hors-scope

- Ingestion de documents.
- Notes Markdown.
- Exports Markdown, TXT, DOCX ou PDF.
- Images generees.
- Mail, y compris rattachement automatique de mails.
- Agenda.
- Biblio.
- Refonte Nextcloud.
- Migration massive de dossiers ou fichiers.
- Suppression ou deplacement massif de contenu utilisateur.
- TTS.
- SMS.
- Pas de rebuild Docker plateforme/global. Un rebuild applicatif cible
  `fridadev` reste autorise pour un patch runtime FridaDev.
- Modification Sauron ou plateforme.
