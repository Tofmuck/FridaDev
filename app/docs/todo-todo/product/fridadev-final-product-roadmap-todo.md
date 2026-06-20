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

TODO archivee:
`app/docs/todo-done/product/frida-v1-nextcloud-folders-todo.md`

Statut 2026-06-17: socle dossiers Frida V1 / Nextcloud valide en Lot Z par
preuve empirique runtime content-free. Les chantiers Documents, Notes, Exports
et Images restent des points obligatoires separes.

Chantier Documents actif apres ce socle, maintenant cloture:
`app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`

### 2. Documents sources / ingestion / lecture / PDF fallback

Frida doit pouvoir recevoir des documents dans un dossier Nextcloud, lister ce
qui est disponible, preparer ou faire lire un document, relier document,
dossier, conversation et usage, et traiter les PDF sans texte comme images. Le
fallback visuel doit etre le meme que le PDF vienne d'un dossier ou d'un ajout
direct dans le chat: memes limites, memes messages utilisateur, memes preuves,
aucun contenu brut dans les traces.

TODO archivee:
`app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`

Contrat source:
`app/docs/states/specs/frida-v1-documents-ingestion-contract.md`

Statut 2026-06-18: Documents V1 valide en Lot Z avec verdict
`met_with_documented_limit`. La seule limite de cloture est le cas live non
`linked`, non applicable faute de dossier actif non `linked` naturel et couvert
par tests unitaires/serveur sans mutation DB artificielle.

### 3. Notes Markdown par dossier

Frida doit pouvoir creer une note, completer une note, retrouver une note,
lister les notes d'un dossier et stocker ces notes en Markdown dans Nextcloud.

TODO archivee:
`app/docs/todo-done/product/frida-v1-folder-markdown-notes-todo.md`

Contrat source:
`app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`

Statut 2026-06-18: Notes Markdown V1 valide en Lot Z avec verdict
`met_with_documented_limit`. La limite documentee est le conflit ETag/version
live, non applicable sans mutation concurrente synthetique propre et couvert
par tests fake/unit et contrat serveur. Aucun contenu utilisateur, secret,
corps Markdown brut, ETag brut, DAV/XML ou payload WebDAV brut n'est conserve
dans les preuves.

Chantier Exports cloture:
`app/docs/todo-done/product/frida-v1-exports-todo.md`

### 4. Exports / creation documentaire

Frida doit pouvoir produire des exports Markdown, TXT, DOCX et PDF, les ranger
dans le bon dossier Nextcloud, puis retrouver et reutiliser un export deja
produit.

TODO archivee:
`app/docs/todo-done/product/frida-v1-exports-todo.md`

Statut 2026-06-19: Exports V1 valide en Lot Z avec verdict `met`. La preuve
live synthetique couvre creation Nextcloud-first, Markdown/TXT/DOCX/PDF,
liste/lookup, download/open, reuse-as-source `.md` / `.txt`, no-overwrite,
refus publics, UI, cleanup distant/local, scan artefacts/docs/diff et scan logs
applicatifs borne reel.

### 5. Images generees

Auditer le stockage actuel des images generees, choisir stockage serveur et/ou
Nextcloud, rattacher chaque image a un dossier, garder des metadonnees sobres et
eviter toute fuite de prompt brut ou contenu sensible.

TODO archivee:
`app/docs/todo-done/product/frida-v1-generated-images-todo.md`

Contrat source:
`app/docs/states/specs/frida-v1-generated-images-contract.md`

Statut 2026-06-20: Images generees V1 valide en Lot Z avec verdict `met`.
La preuve live synthetique couvre provider -> validation -> stockage
Nextcloud-first -> read-model linked, liste/lookup UUID, open/download,
suppression remote-first, cleanup exact, UI dossier, scan artefact/docs/diff et
scan logs applicatifs borne reel. Le format live observe est PNG; JPEG/WebP
sont couverts par tests/fakes Lot 3.1. No-overwrite/conflit et refus dossier
non `linked` sont couverts par tests, sans mutation DB artificielle.

### 6. Observabilite globale / logs agentiques

Auditer les traces actuelles, verifier leur degradation en mode agentique,
harmoniser statuts, reason codes, traces d'outils, smokes et dashboard. Les
traces doivent rester exploitables mais content-free, avec une separation nette
entre observabilite technique, observabilite produit, preuves live et surface
utilisateur.

TODO dediee:
`app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`

Statut 2026-06-20: prochain chantier produit actif apres la cloture Images
generees V1.

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
