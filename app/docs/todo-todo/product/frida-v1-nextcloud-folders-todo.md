# Frida V1 - Socle Nextcloud / dossiers / droits - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Faire correspondre chaque dossier frontend Frida a un repertoire Nextcloud,
avec creation, renommage, suppression, conflits de noms, droits et traces
content-free.

## Scope

- Repertoires Nextcloud associes aux dossiers Frida.
- Creation, renommage et suppression de dossiers.
- Conflits de noms et messages utilisateur.
- Utilisateur Nextcloud propre pour Frida et partage avec Tof.
- Droits, chemins internes et erreurs sans fuite de contenu.

## Hors-scope

- Ingestion documentaire detaillee.
- Notes Markdown.
- Exports.
- Mail.

## Preuves attendues

- Tests unitaires/fake.
- Smoke serveur borne si runtime livre.
- Trace content-free des erreurs et conflits.
- Documentation operateur minimale.

## A detailler dans un lot separe

Decoupage technique, droits exacts, modele de chemins, migrations eventuelles et
UI frontend.
