# Admin Implementation Spec

## Objet

Ce document fixe la spec technique d'implementation immediate du chantier admin V1.

Il sert d'appui d'execution pour les prochaines tranches minimales et s'aligne sur `app/docs/admin-todo.md`, qui reste la feuille de route autoritative du chantier complet.

## Decisions deja actees

- L'admin V1 porte sur les variables contingentes de deploiement.
- Les variables V1 sont stockees en base de donnees.
- Le code lit les variables V1 depuis la base.
- L'admin actuel est conserve comme ancien admin sous `admin-old.*`.
- Le nouvel admin est cree from scratch dans `admin.html` / `admin.js`.
- Le nouvel admin reprend le style du front existant, avec priorite a la reutilisation de `app/web/styles.css`.
- Les logs sont hors V1.
- `/admin` = nouvel admin.
- `/admin-old` = ancien admin.
- `temperature` et `top_p` appartiennent a la logique globale de configuration des modeles.
- `max_tokens` de reponse est hors perimetre V1.

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
- les prompts internes
- `FRIDA_WEB_HOST`
- `FRIDA_WEB_PORT`
- `max_tokens`
- tout invariant conceptuel du systeme

## Contrainte de bootstrap DB

- La base est la source de verite cible des variables V1.
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap externe minimal tant que la transition n'est pas achevee.
- Le bloc `database` de V1 decrit la configuration stockee en base et relue depuis la base une fois l'acces etabli.
- Le bloc `database` de V1 ne rouvre pas le bootstrap externe minimal.

## Regle d'execution

- Une seule tranche minimale a la fois.
- Validation obligatoire avant cloture de tranche.
- Commit puis push apres chaque tranche validee.
- Aucun refactor opportuniste hors perimetre.
- Aucune reouverture des decisions deja prises.

## Traitement transitoire de l'acces admin

- La question de `FRIDA_ADMIN_TOKEN` doit etre documentee et traitee de maniere coherente cote frontend quand il est active.
- Le frontend admin devra disposer d'un mecanisme unique et explicite pour transmettre ce token aux routes `/api/admin/*` lorsque la protection token est active.
- Cette tranche documente cette contrainte mais ne l'implemente pas.

## Sujets explicitement hors tranche

- la divergence `frida.svg` / `fridalogo.png`
- le chantier logs
- l'implementation SQL
- l'implementation backend
- l'implementation frontend
