# Frida V1 - Documents sources / ingestion / lecture / PDF fallback - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Permettre a Frida de reperer, preparer et lire des documents sources rattaches
a un dossier, avec fallback visuel pour les PDF sans texte.

## Scope

- Depot futur de documents dans le sous-dossier Nextcloud standard
  `/Frida/<dossier>/Documents`.
- Liste des documents disponibles.
- Lien document, dossier, conversation et usage.
- Lecture ou preparation de lecture.
- PDF sans texte traites comme images, depuis dossier ou ajout direct au chat.
- Memes limites et messages utilisateur pour les deux chemins PDF.

## Alignement Nextcloud folders Lot 12

Source normative:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

Regle cible:

```text
Documents sources et fichiers persistants -> /Frida/<dossier>/Documents
```

- Le lot Documents devra travailler uniquement sur des dossiers Frida `linked`.
- Un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque tout depot ou rangement Nextcloud.
- Le sous-dossier standard `Documents` est une constante produit autorisee dans
  les docs et preuves; les noms de fichiers, contenus, chemins DAV, XML brut,
  `storage_key`, payload Nextcloud brut et secrets restent interdits.
- Les fichiers workspace existants ne sont pas migres automatiquement par le
  socle Nextcloud folders; une migration/copie eventuelle est un lot separe,
  borne, avec preuve content-free et rollback.
- PDF texte vs PDF image / OCR fallback devront etre cadres dans le lot
  Documents sans rouvrir les notes, exports ou images.

## A livrer plus tard

- Depot de nouveaux documents dans `Documents`.
- Lecture/preparation de lecture depuis un dossier `linked`.
- Detection PDF texte vs PDF image.
- Fallback OCR/visuel borne pour PDF image, avec limites de taille/pages.
- Read-model document/dossier/conversation content-free.
- Politique de migration/copie des fichiers existants, si ouverte par lot
  separe.

## Hors-scope

- Biblio persistante.
- Indexation RAG globale.
- Export documentaire.
- Mail.
- Notes Markdown.
- Images generees.
- Migration automatique des fichiers existants.
- Suppression source silencieuse apres copie.
- Listing de contenu Nextcloud comme preuve.

## Preuves attendues

- Tests sur document texte, PDF texte et PDF image.
- Smoke content-free si lecture serveur active.
- Absence de contenu brut dans traces et dashboard.
- Documentation des limites de taille et pages.
- Verification que le dossier cible est `linked`.
- Verification que les etats `local_only`, `sync_pending`, `sync_error`,
  `conflict` et `deleted` bloquent l'ecriture Nextcloud.
- Preuve de non-fuite: aucun contenu, nom de fichier sensible, chemin DAV, XML
  brut, `storage_key`, token, cookie, app-password ou secret.

## Conflits a gerer

- Dossier Frida non `linked`.
- Sous-dossier `Documents` absent, non-collection ou inaccessible.
- Nom de fichier invalide, deja existant ou collision apres sanitisation.
- PDF image depassant les limites OCR.
- Echec transport Nextcloud redacted.

## Limites V1

- Pas de migration automatique des fichiers historiques.
- Pas d'indexation RAG globale.
- Pas de suppression de source sans decision explicite.
- Pas de contenu brut dans les preuves ou l'observabilite.

## A detailler dans un lot separe

Contrat de stockage, detection PDF texte/image, fallback visuel, limites et
surface utilisateur.
