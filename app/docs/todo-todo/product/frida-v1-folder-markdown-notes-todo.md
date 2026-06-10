# Frida V1 - Notes Markdown par dossier - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Permettre a Frida de creer, completer, retrouver et lister des notes Markdown
rattachees a un dossier Nextcloud.

## Scope

- Creation de note Markdown.
- Ajout ou completion controlee.
- Recherche et liste des notes d'un dossier.
- Stockage dans le repertoire Nextcloud associe.
- Messages utilisateur sobres en cas de conflit.

## Hors-scope

- Editeur Markdown complet.
- Collaboration multi-utilisateur.
- Export DOCX/PDF.
- Rappels ou taches.

## Preuves attendues

- Tests unitaires/fake sur creation, ajout, recherche et liste.
- Smoke content-free si stockage live active.
- Verification que les traces ne contiennent pas le corps brut des notes.

## A detailler dans un lot separe

Format de nommage, politique de conflit, surface frontend et frontiere avec les
exports.
