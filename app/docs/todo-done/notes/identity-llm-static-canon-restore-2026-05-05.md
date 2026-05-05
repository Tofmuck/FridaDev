# Restauration `llm.static` canonique - 2026-05-05

## Resume

- statut: restauration runtime effectuee
- sujet: `llm.static`
- cause: clear admin accidentel/operateur le 2026-05-03T09:12:16Z
- evenement source: `identity_static_admin_edit`, `subject=llm`, `action=clear`, `old_len=1236`, `new_len=0`, `stored_after=false`
- mecanisme de restauration: route officielle `POST /api/admin/identity/static`
- contenu complet: non reproduit dans cette note

## Source restauree

- source: `state/data/identity/llm_identity.example.txt`
- provenance repo: commit `e92b446038cc84ff0d3a4d1a7399e2b885cde76a` (`Add four fridian voice stances to static identity`)
- date commit: 2026-04-20T15:15:56Z
- taille source: 1293 bytes / 1236 caracteres bruts / 1235 caracteres normalises
- sha256 source: `6a68770bab0912030bcd43c20ee994e994c52d114ad5656e190a198d899b328b`

## Preuves de concordance

- le clear admin du 2026-05-03 a mesure `old_len=1236` sur le fichier runtime brut avant effacement;
- les logs `identities_read` montrent `llm.static` statique a `total_chars=1235` entre 2026-04-20T18:36:57Z et 2026-05-01T16:01:46Z;
- la source restauree a `1236` caracteres bruts et `1235` caracteres normalises;
- aucune autre source exploree dans `/opt/platform/fridadev`, `/opt/platform/fridadev-app`, `/opt/platform/_codex_backups`, `/opt/platform/backups`, `/home/tof`, `/mnt`, `/media` ou `/srv` ne fournissait une candidate `llm.static` de longueur 1236.

## Resultat

- premiere restauration appliquee le 2026-05-05T09:14:57Z via `POST /api/admin/identity/static`;
- la suite de tests identity a ensuite produit un clear live a 2026-05-05T09:15:54Z (`old_len=1236`, `new_len=0`);
- restauration finale reappliquee le 2026-05-05T09:18:20Z via `POST /api/admin/identity/static`;
- reponse route finale: `ok=true`, `reason_code=set_applied`, `old_len=0`, `new_len=1236`, `stored_after=true`;
- une relance avec les tests stale du conteneur a reproduit un clear live a 2026-05-05T09:28:26Z;
- restauration finale effective reappliquee le 2026-05-05T09:29:02Z via `POST /api/admin/identity/static`;
- fichier runtime: `/app/data/identity/llm_identity.txt`, 1293 bytes, sha256 `6a68770bab0912030bcd43c20ee994e994c52d114ad5656e190a198d899b328b`;
- read-model apres restauration: `llm.static stored=true loaded=true injected=true`;
- runtime representations apres restauration: bloc compile present, marqueur `[IDENTITÉ DU MODÈLE]` present, marqueur `[IDENTITÉ DE L'UTILISATEUR]` present.

## Correctif safety tests

- cause test confirmee: `test_server_admin_identity_static_edit_phase4.py::test_identity_static_edit_route_is_available_without_admin_token` appelait `/api/admin/identity/static` avec `subject=llm`, `action=clear` sans isoler `llm_identity_path`;
- correctif: le test d'auth statique utilise maintenant des fichiers temporaires et un `get_resources_settings` de test;
- durcissement adjacent: les tests d'auth `mutable` et `governance` mockent aussi leurs effets metier pour ne pas toucher les sources runtime OVH;
- particularite OVH: `/app/tests` n'est pas bind-monte depuis le repo hote; les trois fichiers de tests patchés ont ete copies dans le conteneur courant avant la relance de preuve;
- preuve apres relance de la suite identity patchée: `/app/data/identity/llm_identity.txt` conserve 1293 bytes et sha256 `6a68770bab0912030bcd43c20ee994e994c52d114ad5656e190a198d899b328b`.

## Limites

- `llm.mutable` n'a pas ete restaure: aucune modulation modele mutable fiable n'a ete selectionnee.
- La note ne contient pas le texte identitaire complet par hygiene de confidentialite.
