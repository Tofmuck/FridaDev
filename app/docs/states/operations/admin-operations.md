# Admin Operations Guide

## Objet

Ce document fige l'etat d'exploitation et de migration du nouvel admin V1 de FridaDev apres la fermeture des phases 0 a 11 du chantier.

Il complete :

- `app/docs/states/specs/admin-implementation-spec.md` pour les decisions de design
- `app/docs/states/specs/admin-runtime-settings-schema.md` pour le schema runtime
- `app/docs/todo-done/refactors/admin-todo.md` pour l'historique de realisation

## Entree canonique

- UI canonique : `/admin`
- Prefixe API canonique : `/api/admin/settings`
- `admin.html` reste un acces technique statique tant que les assets sont exposes, mais l'entree documentee et reliee depuis le front principal est `/admin`

## Authentification admin

- Les surfaces `/admin`, `/log`, `/identity`, `/hermeneutic-admin`, `/memory-admin` et `/api/admin/*` ne demandent plus de token admin applicatif.
- La protection publique attendue est Authelia au niveau du hostname.
- Les routes `/api/admin/*` ne doivent plus etre accessibles lateralement depuis les conteneurs pairs du reseau Docker.
- Le runtime n'accepte ces routes qu'en loopback local ou via le chemin Caddy/Authelia, avec header proxy `Remote-User`.
- Sur OVH, `FRIDA_ADMIN_LAN_ONLY` ne doit pas etre reactive sans decision explicite.

## Perimetre V1 reellement exploitable

Le nouvel admin V1 couvre les sections runtime suivantes :

- `main_model`
- `arbiter_model`
- `summary_model`
- `embedding`
- `database`
- `services`
- `resources`

Le frontend V1 permet :

- lecture sectionnelle et agregee
- validation backend avant sauvegarde
- ecriture des champs non secrets
- remplacement explicite des secrets sans re-affichage en clair
- visualisation de la source de valeur (`env` ou `db`)

## Surface read-only complementaire

`Memory Admin` complete le paysage admin sans devenir une extension confuse de `/admin`.

- UI read-only dediee : `/memory-admin`
- API read-only dediee : `GET /api/admin/memory/dashboard`
- role :
  - regrouper l observabilite memoire / RAG
  - distinguer persistance durable, agregat calcule, runtime process-local et historique logs
  - eviter de naviguer durablement entre plusieurs surfaces pour comprendre retrieval, panier, arbitre et injection

Cette surface ne remplace pas :

- `/log` pour la timeline brute et les operations sur logs
- `/hermeneutic-admin` pour le detail identity / pipeline hermeneutique
- `/admin` pour le pilotage runtime settings

## Ce qui reste hors perimetre

Restent explicitement hors V1 :

- l'UI logs/restart legacy
- un nouvel ecran logs
- les routes hermeneutiques dans l'UI admin
- les surcharges explicites `max_tokens` au niveau requete `/api/chat` pour des clients externes
- `SYSTEM_PROMPT`
- les seuils hermeneutiques et autres invariants conceptuels

Les endpoints suivants restent disponibles cote backend, sans UI dediee dans ce chantier :

- `GET /api/admin/logs`
- `POST /api/admin/restart`

## Regles de bootstrap

- La source de verite cible des variables V1 est la base
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB externe minimal
- Le bloc `database` de l'admin V1 est visible et editable cote admin, mais `database.dsn` ne remplace pas encore le bootstrap externe minimal

## Regle de perimetre V1 apres phase 11

- Toutes les variables V1 non invariantes doivent desormais exister en base, pas seulement les secrets.
- Cela couvre les sections runtime V1 suivantes :
  - `main_model`
  - `arbiter_model`
  - `summary_model`
  - `embedding`
  - `database.backend`
  - `services`
  - `resources`
- Le libelle `env fallback` ne doit plus decrire qu'un vrai fallback temporaire :
  - table absente
  - DB indisponible
  - section manquante
  - invariant externe encore assume comme tel

## Invariants et bootstrap restant hors DB

Restent explicitement hors DB a ce stade :

- `FRIDA_MEMORY_DB_DSN`
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`
- `FRIDA_WEB_HOST`
- `FRIDA_WEB_PORT`

Regle d'exploitation associee :

- ces quatre variables ne sont pas des champs admin V1
- elles restent des invariants/process bootstrap
- elles ne doivent pas etre relabelisees comme configuration runtime contingente modifiable depuis la DB

## Regles de secrets

Secrets V1 couverts :

- `main_model.api_key`
- `embedding.token`
- `services.crawl4ai_token`
- `database.dsn`

Regles appliquees :

- les secrets runtime V1 sont stockes chiffres en base via `pgcrypto`
- ils ne sont jamais exposes en clair par les `GET`
- l'API n'accepte leur remplacement que via `payload.<field>.replace_value`
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` reste externe a la base
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` ne transite ni vers le frontend, ni vers les logs, ni vers les erreurs applicatives

## Usage operatoire courant

Sequence nominale :

1. ouvrir `/admin`
2. rafraichir l'etat runtime
3. verifier la source affichee pour la section a modifier
4. lancer `Verifier`
5. corriger si la validation backend remonte une erreur
6. lancer `Enregistrer`

Regle d'exploitation associee au chat principal :

- la surface first-party `/` n'envoie plus de `max_tokens` dans ses requetes `/api/chat`
- pour cette surface, `main_model.response_max_tokens` est la source de verite operative du budget de reponse

Pour un secret :

1. laisser le champ vide si aucun remplacement n'est voulu
2. saisir une nouvelle valeur uniquement dans le champ de remplacement
3. enregistrer
4. controler que le secret reste affiche comme masque et marque `is_set`

## Migration effective atteinte

Etat atteint a la fin des phases 0 a 11 :

- schema runtime V1 defini
- migration SQL et seed initial en place
- couche backend de lecture/ecriture runtime en place
- lectures runtime du code basculees sur la DB avec fallback transitoire
- API admin V1 ouverte et protegee
- secrets V1 chiffres en base et lus dechiffres la ou le runtime en a besoin
- nouvel admin frontend from scratch disponible
- front principal repointe vers `/admin`
- `temperature` et `top_p` ne sont plus pilotes par le front principal
- couche de validation minimale et de non-regression fermee
- tables `runtime_settings` / `runtime_settings_history` presentes sur la DB cible
- sections V1 non secretes bootstrappees en base avec `db_seed`
- secrets V1 chiffres en base et identifies comme `db_encrypted` hors cas special `database.dsn`

## Verification minimale recommandee apres deploiement

Checks courts a refaire apres deploiement :

1. `GET /admin`
2. `GET /memory-admin`
3. `GET /api/admin/settings`
4. `GET /api/admin/memory/dashboard`
5. `PATCH` valide sur `resources`
6. `PATCH` invalide sur `resources`
7. controle qu'aucun secret ne ressort en clair via les `GET`
8. `GET /api/admin/logs`
9. `POST /api/admin/restart` seulement dans une fenetre de maintenance adaptee
10. `POST /api/chat` pour verifier que le chat principal reste operationnel

## Lecture operatoire des embeddings dans `/log`

Un meme tour peut emettre plusieurs evenements `embedding` pour des usages differents. C'est normal si les `source_kind` restent lisibles et si le volume reste coherent avec le pipeline :

- `query` : embedding de la requete de retrieval memoire
- `trace_user` : persistance de trace pour le message user
- `trace_assistant` : persistance de trace pour le message assistant
- `summary` : persistance d'un resume
- `identity_conflict_current` : embedding du texte courant examine pendant un scan de conflits d'identite
- `identity_conflict_candidate` : embedding d'un candidat compare pendant ce meme scan

Le scan de conflits d'identite emet aussi un evenement `identity_conflict_scan` qui resume la passe :

- nombre de candidats vus et compares
- conflits detectes
- nombre d'embeddings courant/candidats
- indicateur `current_embedding_reused`

Contrat operatoire actuel :

- les embeddings de conflit d'identite ne doivent plus remonter en `source_kind=unknown`
- le vecteur du texte courant est calcule une seule fois par passe de conflit, puis reutilise dans la boucle
- pour `N` candidats, le cout cible du scan est donc `1 + N` embeddings, et non plus `2 * N`

## Point de vigilance

- `POST /api/admin/restart` provoque un auto-exit du runtime
- le runtime local temporaire utilise pour les verifications manuelles tombe bien apres cet appel
- les logs/restart resteront backend-only jusqu'au chantier dedie
- le prochain chantier naturel apres cet admin V1 est justement le chantier logs
