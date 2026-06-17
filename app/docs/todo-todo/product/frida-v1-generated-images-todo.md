# Frida V1 - Images generees - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Stabiliser le stockage et le rattachement des images generees par Frida.

## Scope

- Audit du stockage actuel.
- Choix stockage serveur et/ou sous-dossier Nextcloud standard
  `/Frida/<dossier>/Images`.
- Rattachement de chaque image a un dossier.
- Metadonnees sobres.
- Absence de prompt brut ou contenu sensible dans les traces.

## Alignement Nextcloud folders Lot 12

Source normative:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

Regle cible:

```text
Images generees -> /Frida/<dossier>/Images
```

- Le lot Images devra travailler uniquement sur des dossiers Frida `linked`.
- Un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque tout stockage Nextcloud d'image generee.
- Le sous-dossier standard `Images` est une constante produit autorisee dans
  les docs et preuves; les noms de fichiers, contenus image, prompts bruts,
  chemins DAV, XML brut, payload Nextcloud brut et secrets restent interdits
  dans l'observabilite.
- L'audit du stockage actuel reste a faire dans le lot Images; Lot 12 ne genere
  et ne stocke aucune image.

## A livrer plus tard

- Audit du stockage actuel des images generees.
- Choix du stockage cible serveur et/ou Nextcloud.
- Rattachement de chaque image a un dossier Frida `linked`.
- Stockage futur dans `Images` si Nextcloud est retenu.
- Metadonnees sobres: ids, refs, formats, dimensions ou hash courts si utiles,
  sans prompt brut.

## Hors-scope

- Nouvelle generation d'images.
- Galerie avancee.
- Edition d'image.
- Publication externe.
- Documents ingestion.
- Notes Markdown.
- Exports.
- Migration d'images existantes sans lot dedie.
- Listing de contenu Nextcloud comme preuve.

## Preuves attendues

- Audit court du stockage actuel.
- Tests ou smoke de rattachement dossier/image.
- Read-model content-free.
- Documentation des metadonnees conservees.
- Verification que le dossier cible est `linked`.
- Verification que les etats `local_only`, `sync_pending`, `sync_error`,
  `conflict` et `deleted` bloquent l'ecriture Nextcloud.
- Preuve de non-fuite: aucun prompt brut, contenu image, nom de fichier
  sensible, chemin DAV, XML brut, token, cookie, app-password ou secret.

## Conflits a gerer

- Dossier Frida non `linked`.
- Sous-dossier `Images` absent, non-collection ou inaccessible.
- Nom ou ref image invalide, deja utilise ou collision apres sanitisation.
- Stockage actuel divergent ou non rattache.
- Echec transport Nextcloud redacted.

## Limites V1

- Pas de generation d'image dans ce lot.
- Pas de galerie avancee.
- Pas d'edition d'image.
- Pas de prompt brut dans logs, JSONL, dashboard ou preuves.

## A detailler dans un lot separe

Modele de stockage, migration eventuelle des images existantes, UI et politique
de retention.
