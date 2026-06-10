# Frida V1 - Documents sources / ingestion / lecture / PDF fallback - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Permettre a Frida de reperer, preparer et lire des documents sources rattaches
a un dossier, avec fallback visuel pour les PDF sans texte.

## Scope

- Depot de documents dans un dossier Nextcloud.
- Liste des documents disponibles.
- Lien document, dossier, conversation et usage.
- Lecture ou preparation de lecture.
- PDF sans texte traites comme images, depuis dossier ou ajout direct au chat.
- Memes limites et messages utilisateur pour les deux chemins PDF.

## Hors-scope

- Biblio persistante.
- Indexation RAG globale.
- Export documentaire.
- Mail.

## Preuves attendues

- Tests sur document texte, PDF texte et PDF image.
- Smoke content-free si lecture serveur active.
- Absence de contenu brut dans traces et dashboard.
- Documentation des limites de taille et pages.

## A detailler dans un lot separe

Contrat de stockage, detection PDF texte/image, fallback visuel, limites et
surface utilisateur.
