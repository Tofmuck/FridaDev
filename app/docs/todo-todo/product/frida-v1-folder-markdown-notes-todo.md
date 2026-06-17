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
- Stockage dans le sous-dossier Nextcloud standard
  `/Frida/<dossier>/Notes`.
- Messages utilisateur sobres en cas de conflit.

## Alignement Nextcloud folders Lot 12

Source normative:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

Regle cible:

```text
Notes Markdown -> /Frida/<dossier>/Notes
```

- Le lot Notes devra travailler uniquement sur des dossiers Frida `linked`.
- Un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque toute creation, modification, recherche ou liste Nextcloud
  de note.
- Le sous-dossier standard `Notes` est une constante produit autorisee dans les
  docs et preuves; les noms de fichiers, corps Markdown, chemins DAV, XML brut,
  payload Nextcloud brut et secrets restent interdits dans l'observabilite.
- Le stockage Markdown exact, le nommage et les collisions restent a traiter
  dans le lot Notes.

## A livrer plus tard

- Creation de note Markdown dans `Notes`.
- Complement controle d'une note existante.
- Recherche et liste content-free des notes d'un dossier.
- Politique de nommage et de versioning.
- Messages utilisateur sobres sur conflit ou cible indisponible.

## Hors-scope

- Editeur Markdown complet.
- Collaboration multi-utilisateur.
- Export DOCX/PDF.
- Rappels ou taches.
- Documents sources.
- Images generees.
- Migration de notes historiques sans lot dedie.
- Listing de contenu Nextcloud comme preuve.

## Preuves attendues

- Tests unitaires/fake sur creation, ajout, recherche et liste.
- Smoke content-free si stockage live active.
- Verification que les traces ne contiennent pas le corps brut des notes.
- Verification que le dossier cible est `linked`.
- Verification que les etats `local_only`, `sync_pending`, `sync_error`,
  `conflict` et `deleted` bloquent l'ecriture Nextcloud.
- Preuve de non-fuite: aucun corps Markdown brut, nom de fichier sensible,
  chemin DAV, XML brut, token, cookie, app-password ou secret.

## Conflits a gerer

- Dossier Frida non `linked`.
- Sous-dossier `Notes` absent, non-collection ou inaccessible.
- Nom de note vide, invalide, deja utilise ou collision apres sanitisation.
- Concurrence de modification ou version obsoletes.
- Echec transport Nextcloud redacted.

## Limites V1

- Pas d'editeur complet.
- Pas de collaboration temps reel.
- Pas d'export depuis Notes dans ce lot.
- Pas de corps brut dans logs, JSONL, dashboard ou preuves.

## A detailler dans un lot separe

Format de nommage, politique de conflit, surface frontend et frontiere avec les
exports.
