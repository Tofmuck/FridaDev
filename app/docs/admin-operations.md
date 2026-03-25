# Admin Operations Guide

## Objet

Ce document fige l'etat d'exploitation et de migration du nouvel admin V1 de FridaDev apres la fermeture des phases 0 a 9 du chantier.

Il complete :

- `app/docs/admin-implementation-spec.md` pour les decisions de design
- `app/docs/admin-runtime-settings-schema.md` pour le schema runtime
- `app/docs/admin-todo.md` pour l'historique de realisation

## Entree canonique

- UI canonique : `/admin`
- Prefixe API canonique : `/api/admin/settings`
- `admin.html` reste un acces technique statique tant que les assets sont exposes, mais l'entree documentee et reliee depuis le front principal est `/admin`

## Authentification admin

- Quand `FRIDA_ADMIN_TOKEN` est vide, l'acces admin suit uniquement les autres gardes actifs
- Quand `FRIDA_ADMIN_TOKEN` est defini :
  - le frontend admin demande le token a l'ouverture
  - le token est conserve en `sessionStorage`
  - le frontend l'envoie via `X-Admin-Token` sur les requetes `/api/admin/*`
- Les checks de validation minimale reutilisent aussi `X-Admin-Token` quand il est requis

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

## Ce qui reste hors perimetre

Restent explicitement hors V1 :

- l'UI logs/restart legacy
- un nouvel ecran logs
- les routes hermeneutiques dans l'UI admin
- `max_tokens`
- `SYSTEM_PROMPT`
- les seuils hermeneutiques et autres invariants conceptuels

Les endpoints suivants restent disponibles cote backend, sans UI dediee dans ce chantier :

- `GET /api/admin/logs`
- `POST /api/admin/restart`

## Regles de bootstrap

- La source de verite cible des variables V1 est la base
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB externe minimal
- Le bloc `database` de l'admin V1 est visible et editable cote admin, mais `database.dsn` ne remplace pas encore le bootstrap externe minimal

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
2. fournir le token admin si demande
3. rafraichir l'etat runtime
4. verifier la source affichee pour la section a modifier
5. lancer `Verifier`
6. corriger si la validation backend remonte une erreur
7. lancer `Enregistrer`

Pour un secret :

1. laisser le champ vide si aucun remplacement n'est voulu
2. saisir une nouvelle valeur uniquement dans le champ de remplacement
3. enregistrer
4. controler que le secret reste affiche comme masque et marque `is_set`

## Migration effective atteinte

Etat atteint a la fin des phases 0 a 9 :

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

## Verification minimale recommandee apres deploiement

Checks courts a refaire apres deploiement :

1. `GET /admin`
2. `GET /api/admin/settings`
3. `PATCH` valide sur `resources`
4. `PATCH` invalide sur `resources`
5. controle qu'aucun secret ne ressort en clair via les `GET`
6. `GET /api/admin/logs`
7. `POST /api/admin/restart` seulement dans une fenetre de maintenance adaptee
8. `POST /api/chat` pour verifier que le chat principal reste operationnel

## Point de vigilance

- `POST /api/admin/restart` provoque un auto-exit du runtime
- le runtime local temporaire utilise pour les verifications manuelles tombe bien apres cet appel
- les logs/restart resteront backend-only jusqu'au chantier dedie
- le prochain chantier naturel apres cet admin V1 est justement le chantier logs
