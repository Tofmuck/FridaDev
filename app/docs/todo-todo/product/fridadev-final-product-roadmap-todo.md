# FridaDev - Roadmap finale produit Frida 1.0

Statut: TODO actif
Date: 2026-06-10
Cible de cloture: 2026-07-02
Branche de travail courante: `FridaV1-Nextcloud-Folders`

## Intention

Cette roadmap fixe l'ordre general de cloture Frida 1.0. Elle n'est pas une
grande specification detaillee: chaque point renvoie vers une TODO dediee qui
sera detaillee dans un lot separe.

Regle de fin de cycle:

- finir les capacites indispensables a Frida 1.0;
- ne pas rouvrir les chantiers abstraits deja clos;
- traiter les bonus seulement s'il reste de la marge;
- documenter les limites et preuves sans gonfler la roadmap.

## Obligatoire pour cloturer Frida 1.0

### 1. Socle Nextcloud / dossiers / droits Frida

Un dossier frontend Frida doit correspondre a un repertoire Nextcloud: creation,
renommage, suppression, conflits de noms, utilisateur Nextcloud propre pour
Frida, repertoire partage avec Tof, droits, chemins, erreurs et traces
content-free.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-nextcloud-folders-todo.md`

### 2. Documents sources / ingestion / lecture / PDF fallback

Frida doit pouvoir recevoir des documents dans un dossier Nextcloud, lister ce
qui est disponible, preparer ou faire lire un document, relier document,
dossier, conversation et usage, et traiter les PDF sans texte comme images. Le
fallback visuel doit etre le meme que le PDF vienne d'un dossier ou d'un ajout
direct dans le chat: memes limites, memes messages utilisateur, memes preuves,
aucun contenu brut dans les traces.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-documents-ingestion-todo.md`

### 3. Notes Markdown par dossier

Frida doit pouvoir creer une note, completer une note, retrouver une note,
lister les notes d'un dossier et stocker ces notes en Markdown dans Nextcloud.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-folder-markdown-notes-todo.md`

### 4. Exports / creation documentaire

Frida doit pouvoir produire des exports Markdown, TXT, DOCX et PDF, les ranger
dans le bon dossier Nextcloud, puis retrouver et reutiliser un export deja
produit.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-exports-todo.md`

### 5. Images generees

Auditer le stockage actuel des images generees, choisir stockage serveur et/ou
Nextcloud, rattacher chaque image a un dossier, garder des metadonnees sobres et
eviter toute fuite de prompt brut ou contenu sensible.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-generated-images-todo.md`

### 6. Observabilite globale / logs agentiques

Auditer les traces actuelles, verifier leur degradation en mode agentique,
harmoniser statuts, reason codes, traces d'outils, smokes et dashboard. Les
traces doivent rester exploitables mais content-free, avec une separation nette
entre observabilite technique, observabilite produit, preuves live et surface
utilisateur.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`

### 7. Audit final general

Verifier securite et valeurs sensibles, runtime OVH, docs/specs/TODO, tests,
smokes live, coherence des agents, coherence frontend/backend, surface
utilisateur et critique produit/politique.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-final-audit-todo.md`

## Bonus non bloquant

### 8. Mail V1 bonus borne

Bonus si marge, non bloquant pour cloturer Frida 1.0. Auditer Nextcloud Mail /
IMAP / SMTP / API controlee, puis cadrer lecture, resume, tri/classement,
brouillons, envoi seulement avec confirmation humaine, archivage ou rattachement
eventuel a des dossiers Frida.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-mail-bonus-todo.md`

## Reporte hors Frida 1.0

- SMS: reporte, pas necessaire pour la cloture Frida 1.0.
- TTS: reporte / no-go pour l'instant; pas d'usage fort. Frida reste
  principalement une interface de lecture et d'ecriture.

## References utiles

- Cloture pragmatique Agenda V1:
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
- TODO Agenda V1:
  `app/docs/todo-todo/product/frida-agenda-agent.md`
- Hub documentation:
  `app/docs/README.md`

## Hors-scope de cette roadmap generale

- Pas de code runtime.
- Pas de smoke live.
- Pas d'acces Nextcloud.
- Pas de modification Docker.
- Pas de grand audit maintenant.
- Pas de reouverture Agenda abstraite.
- Pas de reouverture Biblio.
