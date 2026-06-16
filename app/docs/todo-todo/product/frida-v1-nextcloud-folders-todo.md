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

## 2. Lots proposes

Ne pas cocher ces lots dans ce cycle de redaction. Ils servent de plan
operatoire pour les prochains prompts.

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

- [ ] Definir le modele produit minimal d'un dossier Frida: identifiant stable,
  nom affiche, statut, chemin logique Nextcloud, droits attendus et timestamps.
- [ ] Definir les operations V1: creer, lister, renommer, supprimer un dossier
  synthetique Frida.
- [ ] Definir le contrat de conflit de nom: detection explicite, message
  utilisateur clair, reason code content-free, aucune correction silencieuse.
- [ ] Definir ce qui reste local/fake avant live et ce qui depend d'une
  decision Sauron.
- [ ] Documenter les limites V1 avant toute implementation runtime.

### Lot 2 - Decision Sauron compte Frida / droits / partage

- [ ] Demander explicitement a Sauron de trancher/provisionner le compte
  Nextcloud Frida si le lot live est ouvert.
- [ ] Demander explicitement a Sauron de definir le repertoire racine Frida, le
  partage avec Tof et les droits exacts.
- [ ] Demander explicitement a Sauron de gerer secrets, app-passwords, backups
  si necessaire et verification serveur.
- [ ] Obtenir une preuve read-only content-free avant toute ecriture Nextcloud.
- [ ] Ne stocker dans FridaDev que des indicateurs redacted et des chemins
  logiques non sensibles.

### Lot 3 - Modele backend FridaDev fake/local

- [ ] Implementer le modele applicatif de dossiers sans appel Nextcloud live.
- [ ] Ajouter un client fake/local pour creer, lister, renommer et supprimer des
  dossiers synthetiques.
- [ ] Couvrir conflits de noms, erreurs, suppression refusee et etats
  incoherents par tests automatises.
- [ ] Garder les logs, erreurs et fixtures content-free.
- [ ] Ne pas brancher de secret ni de chemin serveur reel dans ce lot.

### Lot 4 - Routes/API frontend/backend pour dossiers

- [ ] Ajouter les routes applicatives minimales pour lister, creer, renommer et
  supprimer un dossier Frida via le backend fake/local.
- [ ] Ajouter la surface frontend minimale correspondante si le backend Lot 3
  est stable.
- [ ] Afficher les conflits et erreurs sans fuite de chemin brut, contenu,
  secret ou detail serveur sensible.
- [ ] Exiger une confirmation humaine avant toute suppression reelle ou future
  suppression live.
- [ ] Prouver la compatibilite avec les dossiers/conversations existants sans
  deplacement massif.

### Lot 5 - Preuve live Nextcloud bornee

- [ ] Ouvrir ce lot seulement apres validation Lots 0 a 4 et decision Sauron.
- [ ] Verifier en read-only les droits Frida/Tof et le repertoire cible.
- [ ] Executer un smoke live borne sur un dossier synthetique dedie.
- [ ] Creer, renommer puis supprimer uniquement ce dossier synthetique.
- [ ] Documenter le rollback et verifier qu'aucun contenu utilisateur n'a ete
  lu, deplace, supprime ou loggue.

### Lot 6 - Observabilite content-free et erreurs

- [ ] Definir les reason codes dossiers: succes, conflit de nom, droits
  insuffisants, cible absente, cible deja existante, suppression refusee,
  erreur Nextcloud redacted.
- [ ] Exposer seulement des compteurs, statuts, ids courts, hashes courts si
  necessaire et categories d'erreurs.
- [ ] Interdire contenu de fichier, nom sensible, chemin brut serveur, URL DAV,
  token, cookie, Authorization et app-password.
- [ ] Ajouter un scan anti-fuite adapte aux artefacts JSONL ou rapports.
- [ ] Relier cette observabilite au chantier global
  `frida-v1-agentic-observability-todo.md` sans le rouvrir ici.

### Lot Z - Cloture / no-go / limites V1

- [ ] Verifier que le point de sortie V1 est atteint ou declarer un no-go
  explicite.
- [ ] Documenter les limites V1 et les operations non livrees.
- [ ] Archiver les preuves content-free.
- [ ] Mettre a jour la roadmap generale si le statut du lot change.
- [ ] Ne pas basculer documents, notes, exports, images ou mail dans ce lot.

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

- creer un dossier Frida synthetique;
- lister les dossiers Frida;
- renommer le dossier synthetique;
- supprimer le dossier synthetique avec confirmation et rollback documente;
- associer clairement un dossier frontend Frida a un repertoire Nextcloud;
- gerer un conflit de nom sans fuite de contenu;
- tracer les operations en content-free;
- documenter les limites V1.

Ce point de sortie ne traite pas:

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
- Rebuild Docker.
- Modification Sauron ou plateforme.
