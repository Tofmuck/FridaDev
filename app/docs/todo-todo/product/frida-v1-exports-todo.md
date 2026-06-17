# Frida V1 - Exports / creation documentaire - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Permettre a Frida de produire, ranger, retrouver et reutiliser des exports
Markdown, TXT, DOCX et PDF.

## Scope

- Export Markdown.
- Export TXT.
- Export DOCX.
- Export PDF.
- Rangement automatique dans le sous-dossier Nextcloud standard
  `/Frida/<dossier>/Exports`.
- Reutilisation d'un export deja produit.

## Alignement Nextcloud folders Lot 12

Source normative:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

Regle cible:

```text
Exports Markdown / TXT / DOCX / PDF -> /Frida/<dossier>/Exports
```

- Le lot Exports devra travailler uniquement sur des dossiers Frida `linked`.
- Un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque toute ecriture ou reutilisation Nextcloud d'export.
- Le sous-dossier standard `Exports` est une constante produit autorisee dans
  les docs et preuves; les noms de fichiers, contenus exportes, chemins DAV,
  XML brut, payload Nextcloud brut et secrets restent interdits dans
  l'observabilite.
- Les collisions de nom, le versioning et la reutilisation d'un export existant
  doivent etre traites dans le lot Exports.

## A livrer plus tard

- Generation Markdown.
- Generation TXT.
- Generation DOCX.
- Generation PDF.
- Rangement automatique dans `Exports`.
- Recherche/reutilisation d'un export deja produit.
- Politique de nommage, collision et versioning.

## Hors-scope

- Mise en page avancee.
- Signature ou validation juridique.
- Publication externe.
- Mail.
- Notes Markdown runtime.
- Images generees.
- Documents ingestion.
- Migration d'exports historiques sans lot dedie.
- Listing de contenu Nextcloud comme preuve.

## Preuves attendues

- Tests par format.
- Smoke de rangement content-free si stockage live active.
- Verification du lien dossier/export/conversation.
- Messages utilisateur clairs en cas d'echec.
- Verification que le dossier cible est `linked`.
- Verification que les etats `local_only`, `sync_pending`, `sync_error`,
  `conflict` et `deleted` bloquent l'ecriture Nextcloud.
- Preuve de non-fuite: aucun contenu exporte, nom de fichier sensible, chemin
  DAV, XML brut, token, cookie, app-password ou secret.

## Conflits a gerer

- Dossier Frida non `linked`.
- Sous-dossier `Exports` absent, non-collection ou inaccessible.
- Nom d'export invalide, deja utilise ou collision apres sanitisation.
- Version existante a reutiliser ou nouvelle version a creer.
- Echec transport Nextcloud redacted.

## Limites V1

- Pas de publication externe.
- Pas de validation juridique.
- Pas de contenu exporte dans logs, JSONL, dashboard ou preuves.
- Pas de suppression automatique d'exports existants.

## A detailler dans un lot separe

Moteur de generation, formats exacts, nommage, collisions et stockage.
