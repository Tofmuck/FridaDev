# Admin Implementation Spec

## Objet

Ce document fixe la spec technique d'implementation immediate du chantier admin V1.

Il sert d'appui d'execution pour les prochaines tranches minimales et s'aligne sur `app/docs/todo-done/refactors/admin-todo.md`, qui reste la feuille de route autoritative du chantier complet.

## Decisions deja actees

- L'admin V1 porte sur les variables contingentes de deploiement.
- Les variables V1 sont stockees en base de donnees.
- Le code lit les variables V1 depuis la base.
- Le nouvel admin est cree from scratch dans `admin.html` / `admin.js`.
- Le nouvel admin reprend le style du front existant, avec priorite a la reutilisation de `app/web/styles.css`.
- Les logs sont hors V1.
- L'UI admin actuelle orientee logs/restart n'est pas conservee comme UI legacy ; le chantier logs sera refait from scratch apres le nouvel admin de configuration.
- `/admin` = nouvel admin.
- Le lien du front principal pointe vers `/admin`.
- `temperature` et `top_p` appartiennent a la logique globale de configuration des modeles.
- Les prompts systeme / prompts internes envoyes aux modeles doivent etre visibles dans l'admin en lecture seule.
- Dans cette extension, le seul budget de generation a ouvrir a l'edition est `main_model.response_max_tokens`.
- Les autres budgets de generation peuvent rester d'abord visibles en lecture seule.
- Les prompts internes ne deviennent pas editables pour autant dans cette phase.

## Perimetre exact de V1

Les sections V1 a implementer sont :

- `main_model`
- `arbiter_model`
- `summary_model`
- `embedding`
- `database`
- `services`
- `resources`

## Exclusions explicites de V1

Sont exclus de V1 :

- les logs
- les seuils hermeneutiques
- les prompts internes en edition
- les budgets de contexte / resume / identite en edition tant qu'ils restent seulement informationnels
- les autres budgets de generation tant qu'ils ne sont pas explicitement ouverts apres `main_model.response_max_tokens`
- `FRIDA_WEB_HOST`
- `FRIDA_WEB_PORT`
- tout invariant conceptuel du systeme

## Contrainte de bootstrap DB

- La base est la source de verite cible des variables V1.
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap externe minimal tant que la transition n'est pas achevee.
- Le bloc `database` de V1 decrit la configuration stockee en base et relue depuis la base une fois l'acces etabli.
- Le bloc `database` de V1 ne rouvre pas le bootstrap externe minimal.

## Regle d'execution

- `app/docs/todo-done/refactors/admin-todo.md` couvre le chantier complet A -> Z.
- Une seule tranche minimale a la fois.
- Une tranche minimale = un changement cible, sa validation, son commit, puis son push.
- Validation obligatoire avant cloture de tranche.
- Commit puis push apres chaque tranche validee.
- Aucun refactor opportuniste hors perimetre.
- Aucune reouverture des decisions deja prises.

## Traitement transitoire de l'acces admin

- `/admin` est l'entree canonique du nouvel admin ; `admin.html` reste un acces technique transitoire tant que le statique l'expose, mais le front et la documentation pointent vers `/admin`.
- Aucune entree UI `/admin-old` n'est retenue pour cette migration ; l'UI logs/restart actuelle n'est pas preservee comme legacy.
- `GET /api/admin/logs` et `POST /api/admin/restart` restent disponibles cote backend jusqu'au futur chantier logs.
- Depuis la decision operateur du `2026-04-08`, le frontend admin ne demande plus de token admin applicatif et n'envoie plus `X-Admin-Token`; la protection publique repose sur Authelia au niveau du hostname, et le backend n'accepte `/api/admin/*` qu'en loopback local ou via le proxy Caddy transportant `Remote-User`.
- Cette tranche documente cette contrainte mais ne l'implemente pas.

## Sujets explicitement hors tranche

- le chantier logs
- l'implementation SQL
- l'implementation backend
- l'implementation frontend
