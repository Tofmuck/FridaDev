# Admin Todo

## Contexte initial

Ce document est un livrable d'audit et de planification, pas une implementation.

Objectif du chantier prepare ici : introduire un nouvel admin centre sur les variables contingentes de deploiement, stockees en base, lues par le code depuis la base, sans melanger le chantier logs/restart dans cette V1.

Ce document se base sur l'etat reel du depot observe dans le code au 24/03/2026.

## Decisions deja prises

- L'admin V1 porte sur les variables contingentes de deploiement.
- Ces variables doivent vivre en base de donnees.
- Le code doit lire ces variables depuis la base.
- Le nouvel admin est cree from scratch.
- Le nouvel admin reprend le style du front existant, avec priorite a la reutilisation de `app/web/styles.css` si cela reste propre.
- Les logs constituent un chantier distinct et ulterieur.
- L'UI admin actuelle orientee logs/restart n'est pas conservee comme UI legacy ; le chantier logs sera refait from scratch apres le nouvel admin de configuration.
- Le present todo couvre l'ensemble du chantier jusqu'a l'implementation finale.
- L'execution reelle ne se fera pas en big bang : elle se fera tranche minimale par tranche minimale.
- Chaque tranche reelle devra etre validee, puis committee et poussee avant d'ouvrir la suivante.
- Pour `main_model`, `arbiter_model` et `summary_model`, les parametres effectivement paramétrables doivent entrer dans le perimetre V1, avec une priorite immediate donnee a `main_model.response_max_tokens`.
- `temperature` et `top_p` font donc partie de la logique de configuration globale des modeles et ne sont plus des points ouverts.
- Les prompts systeme et prompts internes envoyes aux modeles doivent etre visibles dans l'admin en lecture seule, pour comprehension, meme s'ils ne deviennent pas editables dans cette phase.
- Dans l'immediat, le seul budget de generation a rendre editable est `main_model.response_max_tokens` ; les autres budgets de generation peuvent d'abord rester visibles en lecture seule.
- Le routage cible est deja fixe :
  - `/admin` = nouvel admin
  - aucune UI legacy `/admin-old` n'est retenue
- Le lien depuis le front devra etre adapte vers le nouvel admin ; ce n'est plus un point a rouvrir.

## Methode d'execution

- Ce document est une feuille de route complete A -> Z, pas un lot de travail a executer d'un seul bloc.
- Son usage normal est le suivant :
  - prendre une tranche minimale ;
  - l'executer sans elargir le perimetre ;
  - verifier la tranche ;
  - commit + push ;
  - reprendre ensuite la tranche suivante.
- Les cases ci-dessous doivent donc rester suffisamment fines pour permettre une execution pas a pas.
- Une phase peut s'etaler sur plusieurs commits ; l'important est de garder des increments petits, testables et refermables.
- Les arbitrages deja fixes par le cadrage ne doivent plus revenir comme faux choix dans les premieres etapes.

## Contrainte structurelle de bootstrap DB

- La base est la source de verite cible des variables V1.
- Tant que la bascule complete n'est pas terminee, l'acces initial a cette base exige encore un bootstrap minimal externe.
- Ce bootstrap minimal externe est une contrainte structurelle de transition, pas une objection bloquante au schema cible.
- Le chantier doit donc organiser proprement la coexistence transitoire suivante :
  - bootstrap externe minimal pour atteindre la base ;
  - lecture des variables V1 depuis la base une fois l'acces etabli ;
  - reduction progressive du bootstrap externe au strict minimum necessaire.
- Le bloc `database` du nouvel admin V1 decrit donc la configuration stockee en base et relue depuis la base une fois l'acces etabli ; il ne rouvre pas le besoin transitoire de bootstrap externe minimal.

## Constats depuis le code

### Surface admin reelle aujourd'hui

- L'application Flask est montee en statique pure via `app = Flask(__name__, static_folder="web", static_url_path="")` dans `app/server.py` : il n'y a ni repertoire `templates/`, ni rendu Jinja, ni blueprint dedie a l'admin.
- Le garde admin actuel est implemente dans `app/server.py` via `@app.before_request`, mais il ne protege que les routes commencant par `/api/admin/`.
- La page `/admin` sert actuellement `app/web/admin.html` via `send_from_directory(...)` dans `app/server.py`.
- La page HTML admin elle-meme n'est donc pas protegee par le garde admin ; seules les requetes API admin le sont.
- Les routes admin actives constatees dans `app/server.py` sont :
  - `GET /api/admin/logs`
  - `POST /api/admin/restart`
  - `GET /api/admin/hermeneutics/identity-candidates`
  - `GET /api/admin/hermeneutics/arbiter-decisions`
  - `POST /api/admin/hermeneutics/identity/force-accept`
  - `POST /api/admin/hermeneutics/identity/force-reject`
  - `POST /api/admin/hermeneutics/identity/relabel`
  - `GET /api/admin/hermeneutics/dashboard`
  - `GET /api/admin/hermeneutics/corrections-export`
- Aucune route de lecture/ecriture d'une configuration runtime stockee en base n'existe aujourd'hui.

### Etat reel du front admin actuel

- `app/web/admin.html` est une page intitulee `Admin - Logs techniques` et charge `app/web/admin.js`.
- `app/web/admin.html` embarque son propre bloc `<style>` inline ; il ne reutilise pas `app/web/styles.css`.
- `app/web/admin.js` ne consomme aujourd'hui que deux endpoints : `/api/admin/logs` et `/api/admin/restart`.
- Aucun code frontend dans `app/web/admin.js` ne consomme aujourd'hui les endpoints hermeneutiques exposes cote backend.
- `app/web/admin.js` n'envoie jamais le header `X-Admin-Token` pourtant accepte par le backend ; si `FRIDA_ADMIN_TOKEN` est renseigne, la page charge mais les appels API admin echouent en `401`.
- L'admin actuel est donc bien principalement un admin de logs/restart, meme si le backend expose deja d'autres routes admin non branchees dans cette UI.

### Couplage du front principal avec l'admin actuel

- `app/web/index.html` expose un bouton `Parametres` (`#btnSettings`).
- `app/web/app.js` redirige ce bouton vers `admin.html`, pas vers `/admin`.
- Le front principal conserve en `localStorage` une cle `frida.settings` qui stocke `temperature`, `top_p` et `max_tokens`.
- `app/web/app.js` envoie encore ces valeurs a `/api/chat` a chaque requete.
- `app/web/app.js` envoie egalement `system` a `/api/chat`, alimente par une constante `SYSTEM_PROMPT` definie cote client.
- Il existe donc deja un chevauchement entre futurs reglages globaux de modele et reglages locaux de session chat.
- Le chantier devra supprimer ce chevauchement en faisant passer `temperature` et `top_p` sous la logique globale des modeles, tout en laissant `max_tokens` hors du perimetre V1.

### Ou vit aujourd'hui la configuration

- La configuration applicative vit d'abord dans `app/config.py`.
- `app/config.py` charge `app/.env` au demarrage, puis materialise des constantes module-level lues ensuite partout dans le code.
- `docker-compose.yml` injecte `./app/.env` dans le conteneur via `env_file`, puis ajoute aussi `FRIDA_WEB_PORT` et `FRIDA_WEB_HOST` via `environment:`.
- `app/run.sh` lit directement `FRIDA_WEB_HOST` et `FRIDA_WEB_PORT` pour lancer le serveur.
- `app/admin/admin_logs.py` contourne `app/config.py` et lit directement l'environnement pour `FRIDA_ADMIN_LOG_PATH`, `FRIDA_ADMIN_LOG_MAX_BYTES` et `FRIDA_ADMIN_LOG_MAX_FILES`.
- Il n'existe aujourd'hui aucune couche intermediaire `runtime_config` / `settings_store` / equivalent entre le code metier et l'environnement.
- Toute modification effective de configuration suppose donc aujourd'hui un changement d'environnement suivi d'un redemarrage du processus.

### Variables contingentes constatees qui devront migrer vers la base

- Bloc modele principal / provider principal aujourd'hui en env via `app/config.py` :
  - `OPENROUTER_BASE`
  - `OPENROUTER_MODEL`
  - `OPENROUTER_REFERER`
  - `OPENROUTER_APP_NAME`
  - `OPENROUTER_TITLE_LLM`
  - `OPENROUTER_TITLE_ARBITER`
  - `OPENROUTER_TITLE_RESUMER`
  - secret associe : `OPENROUTER_API_KEY`
- Bloc modele arbitre aujourd'hui en env via `app/config.py` :
  - `ARBITER_MODEL`
  - `ARBITER_TIMEOUT_S`
- Bloc modele resumeur aujourd'hui en env via `app/config.py` :
  - `SUMMARY_MODEL`
- Bloc embeddings aujourd'hui en env via `app/config.py` :
  - `EMBED_BASE_URL`
  - `EMBED_DIM`
  - `MEMORY_TOP_K`
  - secret associe : `EMBED_TOKEN`
  - point important : aucun champ `EMBED_MODEL` n'existe aujourd'hui dans le code ; il faudra l'ajouter si le futur admin doit parametrer un modele d'embedding explicite.
- Bloc base de donnees aujourd'hui en env via `app/config.py` :
  - `FRIDA_MEMORY_DB_DSN`
- Bloc services externes aujourd'hui en env via `app/config.py` :
  - `SEARXNG_URL`
  - `SEARXNG_RESULTS`
  - `CRAWL4AI_URL`
  - `CRAWL4AI_TOP_N`
  - `CRAWL4AI_MAX_CHARS`
  - secret associe : `CRAWL4AI_TOKEN`
- Bloc chemins / ressources externes aujourd'hui en env via `app/config.py` :
  - `FRIDA_LLM_IDENTITY_PATH`
  - `FRIDA_USER_IDENTITY_PATH`
- Les chemins identite par defaut pointent vers `data/identity/...` et, sous Docker, ces ressources vivent en pratique dans le volume `./state/data:/app/data`.

### Variables presentes mais a ne pas melanger au premier admin de configuration

- `HERMENEUTIC_MODE` et les seuils hermeneutiques (`ARBITER_MIN_*`, `IDENTITY_MIN_*`, `CONTEXT_HINTS_*`, etc.) sont bien configures aujourd'hui par l'env, mais ils relevent d'invariants conceptuels et ne doivent pas etre absorbes sans arbitrage explicite dans le premier nouvel admin.
- Les chemins de prompts internes au depot (`ARBITER_PROMPT_PATH`, `IDENTITY_EXTRACTOR_PROMPT_PATH`) ne relevent pas du meme bloc que les ressources runtime externes.
- Les variables de logs admin (`FRIDA_ADMIN_LOG_*`) existent mais les logs ne sont pas la priorite de ce chantier.
- Les variables de binding processus / conteneur (`FRIDA_WEB_HOST`, `FRIDA_WEB_PORT`) existent mais touchent au runtime d'execution et au Compose ; elles ne doivent pas etre melangees sans decision explicite.
- `max_tokens` de reponse est deja pilote cote chat et est explicitement hors perimetre du nouvel admin V1.

### Points d'ancrage backend deja en place

- `app/core/llm_client.py` construit les headers OpenRouter et le payload du modele principal a partir de `app/config.py`.
- `app/server.py` lit directement `OR_MODEL`, `OR_BASE`, `OR_KEY`, `TIMEOUT_S`, `FRIDA_TIMEZONE` et les parametres admin/security.
- `app/tools/web_search.py` lit `OR_MODEL`, `OR_BASE`, `SEARXNG_*` et `CRAWL4AI_*`.
- `app/memory/arbiter.py` lit `ARBITER_MODEL`, `ARBITER_TIMEOUT_S`, `OR_BASE` et les seuils hermeneutiques.
- `app/memory/summarizer.py` lit `SUMMARY_MODEL`, `SUMMARY_TARGET_TOKENS`, `SUMMARY_THRESHOLD_TOKENS`, `SUMMARY_KEEP_TURNS` et `OR_BASE`.
- `app/memory/memory_store.py` lit `FRIDA_MEMORY_DB_DSN`, `EMBED_BASE_URL`, `EMBED_TOKEN`, `EMBED_DIM`, `MEMORY_TOP_K` et plusieurs seuils identitaires.
- `app/core/conv_store.py` lit `FRIDA_MEMORY_DB_DSN`, `FRIDA_TIMEZONE`, `MAX_TOKENS` et plusieurs seuils de hints.
- `app/identity/identity.py` lit `FRIDA_LLM_IDENTITY_PATH`, `FRIDA_USER_IDENTITY_PATH`, `OR_MODEL`, `IDENTITY_TOP_N` et `IDENTITY_MAX_TOKENS`.
- Aucun de ces modules ne lit aujourd'hui une configuration deployee depuis la base ; tous lisent soit `config.py`, soit directement `os.environ`.

### Etat reel de la base existante

- L'initialisation SQL est deja faite au demarrage via `memory_store.init_db()`, `conv_store.init_catalog_db()` et `conv_store.init_messages_db()` appelees dans `app/server.py`.
- Les tables deja creees pour le state metier sont :
  - `conversations`
  - `conversation_messages`
  - `traces`
  - `summaries`
  - `identities`
  - `identity_evidence`
  - `arbiter_decisions`
  - `identity_conflicts`
- Aucune table de configuration runtime n'existe aujourd'hui.
- `memory_store.init_db()` active deja `pgcrypto` en plus de `pgvector` ; `pgcrypto` constitue un point d'ancrage utile si des secrets doivent etre stockes chiffrablement en base.

### Tables cibles pour le chantier

- Le chantier doit introduire une table primaire `runtime_settings`.
- Le chantier doit introduire une table d'historique `runtime_settings_history`.
- Le chantier doit introduire une structure explicite de gestion des secrets (`value_encrypted`, `is_secret`, `is_set`, redaction de sortie).
- `pgcrypto`, deja active dans la base, constitue l'ancrage retenu pour la gestion des secrets.

### Routes backend cibles pour le chantier

- Le prefixe de configuration du nouvel admin est `/api/admin/settings`.
- Les routes sectionnelles cibles du chantier sont :
  - `GET/PATCH /api/admin/settings/main-model`
  - `GET/PATCH /api/admin/settings/arbiter-model`
  - `GET/PATCH /api/admin/settings/summary-model`
  - `GET/PATCH /api/admin/settings/embedding`
  - `GET/PATCH /api/admin/settings/database`
  - `GET/PATCH /api/admin/settings/services`
  - `GET/PATCH /api/admin/settings/resources`
- Le chantier doit aussi exposer :
  - `GET /api/admin/settings`
  - une route de statut bootstrap/fallback env-vers-DB ;
  - une route de validation / smoke test par section si une verification technique active est necessaire avant sauvegarde finale.

### Impacts front minimaux deja visibles

- Le bouton `Parametres` du front devra changer de cible, car il pointe aujourd'hui vers `admin.html` legacy direct.
- Le nouvel admin devra etre cree from scratch dans `app/web/admin.html` et `app/web/admin.js` ; l'UI logs/restart actuelle ne sera pas preservee sous `admin-old.*`.
- Le style devra idealement reutiliser `app/web/styles.css`, ce qui n'est pas le cas de l'admin actuel.
- Le front devra traiter la question des secrets masques, des erreurs de validation et de l'eventuel token admin.
- Le front devra traiter explicitement la coexistence entre reglage global admin et reglage local `frida.settings` deja stocke en `localStorage`.

### Validation et couplages existants a ne pas oublier

- `app/minimal_validation.py` verifie aujourd'hui l'existence de `admin.html` et `admin.js`, ainsi que des marqueurs lies a `/api/admin/logs` et `/api/admin/restart`.
- La liberation de `admin.html` et `admin.js` pour le nouvel admin exigera donc une mise a jour explicite de la validation minimale.
- `app/minimal_validation.py` est aligne sur `fridalogo.png`, qui constitue la reference UI canonique du front courant.

## Invariants a respecter

- Ne pas implementer le nouvel admin dans cette phase preparatoire.
- Ne pas modifier le runtime, les routes actives, le schema SQL ou les comportements applicatifs dans cette phase preparatoire.
- Ne pas conserver l'UI admin actuelle comme legacy `admin-old.*`.
- Ne pas introduire de route UI `/admin-old` dans ce chantier.
- Planifier explicitement la creation d'un nouveau `admin.html` from scratch.
- Planifier explicitement la liberation de `admin.js` pour le nouvel admin from scratch.
- Planifier explicitement l'adaptation du lien depuis le front vers le nouvel admin.
- Limiter le premier nouvel admin aux variables contingentes de deploiement, pas aux invariants conceptuels du systeme.
- Faire de la base la source de verite cible pour ces variables contingentes.
- Garder les logs comme chantier distinct et non prioritaire.
- Reutiliser `app/web/styles.css` si cela reste propre ; sinon limiter la derivation CSS au strict necessaire et la justifier.
- Ne jamais renvoyer les secrets en clair au frontend par simple lecture des settings.
- Ne pas oublier la contrainte de transition bootstrap DB : l'application a besoin d'un bootstrap externe minimal pour atteindre la base avant de pouvoir lire la configuration V1 stockee en base.
- Maintenir un chemin de compatibilite/fallback env tant que la bascule complete n'est pas terminee.
- Garder les routes hermeneutiques existantes hors du premier admin de configuration.

## Todo detaille et cochable

Chaque case ci-dessous doit pouvoir correspondre a une action locale, verifiable et committable.

### Phase 0 - Verrouillage operatoire du cadrage

- [x] Reporter les decisions deja prises en tete du document dans la spec technique d'implementation du chantier.
- [x] Geler dans le chantier la cible `/admin` pour le nouvel admin.
- [x] Geler dans le chantier l'absence de route UI `/admin-old`.
- [x] Geler dans le chantier le principe de non-conservation de l'UI admin actuelle comme legacy `admin-old.*`.
- [x] Geler dans le chantier le principe de creation du nouvel admin from scratch dans `admin.html` / `admin.js`.
- [x] Geler dans le chantier le principe d'adaptation du lien depuis le front vers le nouvel admin.
- [x] Geler dans le chantier le principe de priorite a la reutilisation de `app/web/styles.css`.
- [x] Geler dans le chantier l'exclusion du bloc logs hors du premier admin V1.
- [x] Formaliser dans la spec d'implementation que le todo est complet A -> Z mais que l'execution reelle se fera par micro-etapes successives.
- [x] Formaliser dans la spec d'implementation qu'une tranche minimale = implementation ciblee + validation + commit + push.
- [x] Documenter que l'entree canonique du nouvel admin est `/admin` et que `admin.html` reste un acces technique transitoire pendant la migration.
- [x] Documenter qu'aucune entree UI `/admin-old` n'est retenue et que l'UI logs/restart actuelle n'est pas preservee comme legacy.
- [x] Documenter la politique UX appliquee quand `FRIDA_ADMIN_TOKEN` est actif : saisie a l'ouverture, stockage en `sessionStorage`, envoi via `X-Admin-Token` sur les requetes `/api/admin/*`.

### Phase 1 - Conception du modele de donnees de configuration

- [x] Creer le module backend de lecture/ecriture de configuration runtime dans `app/admin/runtime_settings.py`.
- [x] Poser `runtime_settings` comme table primaire des settings runtime.
- [x] Poser une granularite `une ligne par section JSONB` dans `runtime_settings`.
- [x] Poser les sections minimales du schema : `main_model`, `arbiter_model`, `summary_model`, `embedding`, `database`, `services`, `resources`.
- [x] Lister pour `main_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [x] Lister pour `arbiter_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [x] Lister pour `summary_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [x] Lister pour `embedding` les champs exacts a stocker en base.
- [x] Lister pour `database` les champs exacts a stocker en base pour la configuration V1 relue depuis la base.
- [x] Documenter dans le schema la distinction entre bootstrap DB minimal externe et configuration `database` stockee en base.
- [x] Lister pour `services` les champs exacts a stocker en base.
- [x] Lister pour `resources` les champs exacts a stocker en base.
- [x] Marquer, champ par champ, lesquels sont des secrets et lesquels ne le sont pas.
- [x] Ajouter dans le design un champ `updated_at`.
- [x] Ajouter dans le design un champ `updated_by`.
- [x] Ajouter dans le design un champ `source` / `origin` pour distinguer seed env et valeur editee.
- [x] Ajouter dans le design un champ minimal de version de schema.
- [x] Integrer `runtime_settings_history` des la V1.
- [x] Utiliser `pgcrypto` pour la politique de secret retenue.
- [x] Exposer au front un secret present sous forme masquee avec un indicateur `is_set`, sans jamais renvoyer sa valeur en clair.
- [x] Ajouter `EMBED_MODEL` au schema V1 et au code de consommation associe.
- [x] Integrer `OPENROUTER_BASE`, `OPENROUTER_REFERER`, `OPENROUTER_APP_NAME` et `OPENROUTER_TITLE_*` au perimetre V1 du bloc modele principal / provider.
- [x] Integrer `ARBITER_TIMEOUT_S` au perimetre V1 du bloc arbitre.
- [x] Integrer `SEARXNG_RESULTS`, `CRAWL4AI_TOP_N` et `CRAWL4AI_MAX_CHARS` au perimetre V1 du bloc services.
- [x] Documenter explicitement que `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB minimal externe tant que la transition n'est pas achevee.

### Phase 2 - Schema SQL et seed initial

- [x] Creer la migration SQL de la table principale des settings runtime.
- [x] Ajouter la contrainte d'unicite necessaire sur la cle ou sur le couple section/cle.
- [x] Ajouter les index necessaires a la lecture par section.
- [x] Ajouter la structure necessaire au stockage des secrets selon la politique retenue.
- [x] Ajouter le champ/indicateur permettant de savoir si une valeur secrete est presente.
- [x] Creer la table d'historique/revision `runtime_settings_history`.
- [x] Prevoir une migration idempotente executable sans casser un environnement deja initialise.
- [x] Ecrire la logique de seed des valeurs non secretes depuis l'environnement courant.
- [x] Ecrire la logique de seed initial des valeurs secretes depuis l'environnement courant, sans re-exposition en clair.
- [x] Implementer la regle "ne pas ecraser une valeur deja presente en DB lors d'un reseed".
- [x] Prevoir un moyen explicite de reconnaitre qu'une section n'a jamais encore ete seedee.
- [x] Documenter dans la migration qu'aucune extension PostgreSQL supplementaire n'est requise a priori au-dela de `pgcrypto` deja active.
- [x] Documenter dans la migration la separation entre bootstrap DB minimal externe et sections V1 stockees dans `runtime_settings`.
- [x] Exclure explicitement `FRIDA_MEMORY_DB_DSN` du seed de `runtime_settings` tant que la transition n'est pas achevee.
- [x] Prevoir un commit isole pour la migration SQL et le seed initial, sans branchement frontend.

### Phase 3 - Couche backend de lecture de configuration

- [x] Creer le module dedie a la lecture des settings runtime depuis la DB.
- [x] Ajouter un fallback env explicite tant que la table ou la valeur n'existe pas.
- [x] Ajouter un point d'entree backend pour lire la section `main_model`.
- [x] Ajouter un point d'entree backend pour lire la section `arbiter_model`.
- [x] Ajouter un point d'entree backend pour lire la section `summary_model`.
- [x] Ajouter un point d'entree backend pour lire la section `embedding`.
- [x] Ajouter un point d'entree backend pour lire la section `database`.
- [x] Ajouter un point d'entree backend pour lire la section `services`.
- [x] Ajouter un point d'entree backend pour lire la section `resources`.
- [x] Ajouter une redaction automatique des secrets dans tous les objets renvoyables au frontend.
- [x] Ajouter une validation backend par champ avant toute ecriture.
- [x] Implementer une lecture centralisee via un cache explicitement invalide apres ecriture.
- [x] Implementer le comportement `table de settings vide = fallback env transitoire + statut visible`.
- [x] Implementer le comportement `DB indisponible = fallback env transitoire quand il existe, sinon erreur de configuration explicite`.
- [x] Implementer le comportement `secret requis absent = erreur de configuration explicite, sans fuite de valeur`.
- [x] Laisser explicitement `app/admin/admin_logs.py` hors de cette bascule V1.
- [x] Laisser explicitement `FRIDA_WEB_HOST` et `FRIDA_WEB_PORT` hors de cette bascule V1.
- [x] Laisser explicitement `FRIDA_MEMORY_DB_DSN` dans le bootstrap DB minimal externe tant que la transition n'est pas achevee.
- [x] Prevoir un commit isole pour la couche backend de lecture avant remplacement des usages.

### Phase 4 - Remplacement progressif des lectures actuelles dans le code

- [x] Remplacer la lecture du modele principal dans `app/core/llm_client.py` par la nouvelle couche runtime config.
- [x] Remplacer la lecture du modele principal dans `app/server.py` par la nouvelle couche runtime config.
- [x] Remplacer la lecture du modele principal utilisee par `app/tools/web_search.py`.
- [x] Remplacer la lecture du modele principal utilisee pour le comptage de tokens dans `app/server.py`.
- [x] Remplacer la lecture du modele principal utilisee pour le comptage de tokens dans `app/identity/identity.py`.
- [x] Remplacer la lecture du modele arbitre dans `app/memory/arbiter.py`.
- [x] Remplacer la lecture du modele resumeur dans `app/memory/summarizer.py`.
- [x] Remplacer la lecture du bloc embeddings dans `app/memory/memory_store.py`.
- [x] Remplacer la lecture du bloc services externes dans `app/tools/web_search.py`.
- [x] Remplacer la lecture des chemins / ressources externes dans `app/identity/identity.py`.
- [x] Remplacer la lecture des memes chemins / ressources externes dans `app/minimal_validation.py`.
- [x] Remplacer la lecture du bloc `database` dans `app/core/conv_store.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [x] Remplacer la lecture du bloc `database` dans `app/memory/memory_store.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [x] Remplacer la lecture du bloc `database` dans `app/minimal_validation.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [x] Verifier que `app/config.py` reste utilisable comme fallback transitoire tant que la bascule n'est pas complete.
- [x] Verifier que `app/admin/admin_logs.py` continue a fonctionner sans regression apres introduction de la nouvelle couche.
- [x] Verifier que `app/run.sh` et `docker-compose.yml` ne sont pas touches par inadvertance pendant cette phase.
- [x] Prevoir un commit isole pour chaque bloc remplace (`main_model`, `arbiter_model`, `summary_model`, `embedding`, `services`, `resources`, puis `database`).

### Phase 5 - API backend du nouvel admin

- [x] Ouvrir le prefixe `/api/admin/settings` pour la configuration du nouvel admin.
- [x] Ajouter une route de lecture agregee de l'ensemble des sections du nouvel admin.
- [x] Ajouter une route `GET` de lecture pour la section `main_model`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `main_model`.
- [x] Ajouter une route `GET` de lecture pour la section `arbiter_model`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `arbiter_model`.
- [x] Ajouter une route `GET` de lecture pour la section `summary_model`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `summary_model`.
- [x] Ajouter une route `GET` de lecture pour la section `embedding`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `embedding`.
- [x] Ajouter une route `GET` de lecture pour la section `database`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `database`.
- [x] Ajouter une route `GET` de lecture pour la section `services`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `services`.
- [x] Ajouter une route `GET` de lecture pour la section `resources`.
- [x] Ajouter une route `PATCH` de mise a jour pour la section `resources`.
- [x] Ajouter une route de statut bootstrap/fallback pour rendre visible la source effective de configuration.
- [x] Ajouter une route de validation/smoke test par section pour les verifications techniques avant sauvegarde finale.
- [x] Brancher toutes ces routes sous le garde admin existant.
- [x] Verifier que les reponses `GET` masquent tous les secrets.
- [x] Verifier que les reponses `PATCH` ne logguent jamais les secrets en clair.
- [x] Conserver inchangées `GET /api/admin/logs` et `POST /api/admin/restart`.
- [x] Ne pas melanger les endpoints hermeneutiques existants avec les endpoints de configuration V1.
- [x] Prevoir un commit isole pour l'ouverture des routes API de configuration.

### Phase 5 bis - Secrets runtime chiffres en base

- [x] Documenter que les secrets runtime V1 sont stockes chiffres en base via `pgcrypto`, jamais en clair.
- [x] Introduire une cle externe minimale dediee au chiffrement/dechiffrement des settings runtime sous `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`.
- [x] Documenter que `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` reste externe a la base, au meme titre que le bootstrap DB minimal.
- [x] Documenter que `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` ne transite jamais vers le frontend, les logs applicatifs, ni les reponses d'erreur.
- [x] Documenter que `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB externe minimal meme si `database.dsn` devient stockable chiffre en base.
- [x] Geler la liste des secrets V1 couverts par cette phase : `main_model.api_key`, `embedding.token`, `services.crawl4ai_token`, `database.dsn`.
- [x] Creer le module dedie `app/admin/runtime_secrets.py`.
- [x] Ajouter dans ce module un helper de chiffrement applicatif vers `value_encrypted` via `pgp_sym_encrypt`.
- [x] Ajouter dans ce module un helper de dechiffrement applicatif depuis `value_encrypted` via `pgp_sym_decrypt`.
- [x] Ajouter dans ce module un helper de verification de presence de `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`.
- [x] Implementer le comportement `cle crypto absente = ecriture de secret refusee avec erreur explicite`.
- [x] Implementer le comportement `secret chiffre present mais indechiffrable = erreur de configuration explicite`.
- [x] Implementer le comportement `is_set=true sans valeur dechiffrable exploitable = erreur de configuration explicite`.
- [x] Fixer le format de remplacement d'un secret en `PATCH` a `payload.<field>.replace_value`.
- [x] Refuser tout `PATCH` secret sans `replace_value`.
- [x] Refuser tout melange ambigu entre `value`, `replace_value` et `value_encrypted` dans les payloads d'update secret.
- [x] Normaliser `replace_value` sans jamais le reinjecter en clair dans `runtime_settings`.
- [x] Normaliser `replace_value` sans jamais le reinjecter en clair dans `runtime_settings_history`.
- [x] Normaliser `replace_value` sans jamais le reinjecter en clair dans les logs, traces d'erreur ou retours d'API.
- [x] Ouvrir l'ecriture chiffree de `main_model.api_key`.
- [x] Ouvrir l'ecriture chiffree de `embedding.token`.
- [x] Ouvrir l'ecriture chiffree de `services.crawl4ai_token`.
- [x] Ouvrir l'ecriture chiffree de `database.dsn`.
- [x] Ajouter la lecture runtime dechiffree de `main_model.api_key`.
- [x] Remplacer le fallback `OPENROUTER_API_KEY` par le secret DB dechiffre quand il est disponible.
- [x] Ajouter la lecture runtime dechiffree de `embedding.token`.
- [x] Remplacer le fallback `EMBED_TOKEN` par le secret DB dechiffre quand il est disponible.
- [x] Ajouter la lecture runtime dechiffree de `services.crawl4ai_token`.
- [x] Remplacer le fallback `CRAWL4AI_TOKEN` par le secret DB dechiffre quand il est disponible.
- [x] Garder `database.dsn` stockable et lisible en mode masque dans l'admin sans le substituer au bootstrap externe minimal tant que la transition DB n'est pas explicitement refermee.
- [x] Ajouter dans l'API admin un indicateur de source effective du secret (`db_encrypted` vs `env_fallback`) sans jamais exposer la valeur.
- [x] Ajouter un backfill initial des secrets deja presents en env vers `value_encrypted`, sans re-exposition en clair.
- [x] Garantir qu'un reseed secret n'ecrase jamais une valeur deja chiffree en base.
- [x] Ajouter des tests unitaires sur le chiffrement et le dechiffrement des secrets runtime.
- [x] Ajouter des tests backend sur un `PATCH` secret valide pour `main_model`.
- [x] Ajouter des tests backend sur un `PATCH` secret valide pour `embedding`.
- [x] Ajouter des tests backend sur un `PATCH` secret valide pour `services`.
- [x] Ajouter des tests backend sur un `PATCH` secret valide pour `database`.
- [x] Ajouter des tests backend sur le cas `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` absent.
- [x] Ajouter des tests backend sur le cas `value_encrypted` indechiffrable.
- [x] Ajouter des tests backend garantissant qu'aucun secret ne fuit en clair via `GET`, `PATCH`, logs, erreurs, historique ou validation.
- [x] Prevoir un commit isole pour la couche crypto.
- [x] Prevoir un commit isole pour l'ouverture des `PATCH` secrets.
- [x] Prevoir un commit isole pour la lecture runtime dechiffree des secrets.
- [x] Prevoir un commit isole pour le backfill initial des secrets existants.

### Phase 6 - Liberation de `admin.html` / `admin.js` pour le nouvel admin

- [x] Reserver `app/web/admin.html` au futur nouvel admin.
- [x] Reserver `app/web/admin.js` au futur nouvel admin.
- [x] Retirer de `app/web/admin.html` tout contenu UI logs/restart legacy au moment de la bascule vers le nouvel admin.
- [x] Retirer de `app/web/admin.js` toute logique UI logs/restart legacy au moment de la bascule vers le nouvel admin.
- [x] Ne pas creer `app/web/admin-old.html`.
- [x] Ne pas creer `app/web/admin-old.js`.
- [x] Ne pas ajouter de route Flask `/admin-old`.
- [x] Ne pas maintenir d'acces technique direct `/admin-old.html`.
- [x] Documenter explicitement que `GET /api/admin/logs` et `POST /api/admin/restart` restent disponibles sans UI legacy dediee jusqu'au futur chantier logs.
- [x] Documenter explicitement dans le code ou la doc que les routes hermeneutiques backend existent mais ne sont pas branchees dans l'UI admin V1.
- [x] Prevoir un commit isole uniquement pour la liberation de `admin.html` / `admin.js` sans `admin-old.*`.

### Phase 7 - Nouveau frontend admin from scratch

- [x] Creer le nouveau `app/web/admin.html` from scratch.
- [x] Creer le nouveau `app/web/admin.js` from scratch.
- [x] Verifier d'abord si `app/web/styles.css` peut etre reutilise tel quel sans casser le front principal.
- [x] Si la reutilisation directe n'est pas propre, creer une derivation CSS minimale et justifiee au lieu d'un nouveau bloc inline massif.
- [x] Construire une section UI dediee au modele principal.
- [x] Construire une section UI dediee au modele arbitre.
- [x] Construire une section UI dediee au modele resumeur.
- [x] Construire une section UI dediee au bloc embeddings.
- [x] Construire une section UI dediee au bloc base de donnees.
- [x] Construire une section UI dediee au bloc services externes.
- [x] Construire une section UI dediee au bloc chemins / ressources externes.
- [x] Ajouter un affichage masque des secrets deja presents.
- [x] Ajouter un mecanisme explicite de remplacement des secrets sans re-affichage en clair.
- [x] Ajouter un etat de chargement par section.
- [x] Ajouter un etat d'erreur par section.
- [x] Ajouter un etat "modifications non sauvegardees" par section.
- [x] Ajouter un bouton d'enregistrement par section.
- [x] Ajouter un retour de validation lisible par champ en cas d'erreur backend.
- [x] Ajouter un indicateur visible de source de valeur (`env fallback` vs `db`).
- [x] Ne pas ajouter de lien vers une UI admin legacy logs/restart.
- [x] Verifier que le nouveau `admin.js` n'embarque pas de logique logs/restart par reflexe.
- [x] Prevoir un commit isole pour le nouveau frontend admin.

### Phase 8 - Integration minimale avec le front principal

- [x] Modifier `app/web/app.js` pour que le bouton `Parametres` vise le nouvel admin et non plus `admin.html` legacy direct.
- [x] Pointer le bouton `Parametres` du front principal vers `/admin`.
- [x] Aligner cette cible avec la route Flask et avec les assets statiques reellement exposes.
- [x] Retirer `temperature` et `top_p` de `frida.settings` dans `localStorage`.
- [x] Brancher `temperature` et `top_p` sur la logique globale de configuration des modeles.
- [x] Retirer l'envoi direct de `temperature` et `top_p` depuis le front vers `/api/chat`.
- [x] Limiter `frida.settings` aux reglages de session restant hors admin V1.
- [x] Requalifier clairement `max_tokens` comme reglage de session hors admin V1 tant qu'il reste hors perimetre.
- [x] Maintenir `max_tokens` hors du nouvel admin V1.
- [x] Maintenir `SYSTEM_PROMPT` hors du nouvel admin V1.
- [x] Verifier que la navigation du front principal n'expose plus d'entree UI legacy logs/restart.
- [x] Prevoir un commit isole pour l'integration minimale du front principal.

### Phase 9 - Validation automatique et non-regression

- [x] Mettre a jour `app/minimal_validation.py` pour couvrir le nouvel admin.
- [x] Mettre a jour `app/minimal_validation.py` pour ne plus attendre l'UI legacy logs/restart dans `admin.html` / `admin.js`.
- [x] Ajouter un test de presence des nouveaux assets `admin.html` et `admin.js`.
- [x] Ajouter un test garantissant que les assets `admin-old.html` et `admin-old.js` ne sont pas introduits.
- [x] Ajouter un smoke test `GET /admin`.
- [x] Ajouter un smoke test garantissant que `/admin-old` n'est pas expose.
- [x] Ajouter un smoke test de lecture agregee de la configuration admin.
- [x] Ajouter un smoke test d'update valide sur une section non secrete.
- [x] Ajouter un smoke test d'update invalide pour verifier la validation backend.
- [x] Ajouter un smoke test garantissant qu'un secret ne ressort jamais en clair via un `GET`.
- [x] Verifier manuellement que `GET /api/admin/logs` et `POST /api/admin/restart` continuent a fonctionner sans UI legacy dediee.
- [x] Verifier manuellement que les routes hermeneutiques existantes repondent encore apres l'ajout du nouvel admin.
- [x] Verifier manuellement que le chat principal fonctionne encore apres bascule des lectures runtime vers la DB.
- [x] Prevoir un commit isole pour la couche de validation et de non-regression.

### Phase 10 - Sequence de commits recommandee

- [x] Commit 1 : migration SQL + seed initial + design documentaire du bootstrap DB.
- [x] Commit 2 : couche backend de lecture runtime config avec fallback env, sans front.
- [x] Commit 3 : remplacement progressif des lectures code sur un premier bloc isole (`main_model` ou `services`).
- [x] Commit 4 : ouverture des routes API de configuration.
- [x] Commit 5 : chiffrement, ecriture, lecture et backfill initial des secrets runtime en base.
- [x] Commit 6 : liberation de `admin.html` / `admin.js` sans `admin-old.*`.
- [x] Commit 7 : creation du nouveau frontend admin.
- [x] Commit 8 : adaptation du bouton `Parametres` dans le front principal.
- [x] Commit 9 : validation minimale, smoke tests et non-regression.
- [x] Commit 10 : documentation finale d'exploitation/migration du nouvel admin.

### Phase 11 - Activation effective de la configuration runtime en base

- [x] Acter explicitement qu'apres cette phase, toutes les variables V1 non invariantes doivent exister en base, pas seulement les secrets.
- [x] Geler explicitement la liste residuelle des invariants/bootstrap restant hors DB, au minimum `FRIDA_MEMORY_DB_DSN`, `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`, `FRIDA_WEB_HOST` et `FRIDA_WEB_PORT`.
- [x] Considerer l'absence de `runtime_settings` et `runtime_settings_history` comme une anomalie de deploiement a corriger, plus comme un fallback normal.
- [x] Ne plus traiter `UndefinedTable` comme un simple etat `empty_table` silencieux une fois cette phase activee.
- [x] Ajouter une etape explicite d'application de `app/admin/sql/runtime_settings_v1.sql` sur la vraie DB cible avant exposition du nouvel admin.
- [x] Ajouter une verification automatique de presence des tables `runtime_settings` et `runtime_settings_history` au demarrage ou au deploy.
- [x] Ajouter un bootstrap idempotent qui cree en DB toutes les sections V1 manquantes a partir de la config effective courante.
- [x] Ecrire en base les valeurs non secretes de `main_model`.
- [x] Ecrire en base les valeurs non secretes de `arbiter_model`.
- [x] Ecrire en base les valeurs non secretes de `summary_model`.
- [x] Ecrire en base les valeurs non secretes de `embedding`.
- [x] Ecrire en base `database.backend`.
- [x] Ecrire en base les valeurs non secretes de `services`.
- [x] Ecrire en base les valeurs non secretes de `resources`.
- [x] Fusionner ce bootstrap non secret avec le backfill des secrets deja chiffres pour obtenir une baseline DB complete et idempotente.
- [x] Introduire un origin persiste explicite pour les valeurs importees en base (`db_seed` ou equivalent), distinct du fallback env.
- [x] Reserver le libelle `env fallback` au seul cas ou une valeur est encore synthesee depuis l'env faute de row DB exploitable.
- [x] Verifier qu'apres bootstrap complet, toutes les sections V1 apparaissent avec `source=db` dans `/api/admin/settings/status`.
- [x] Verifier qu'apres bootstrap complet, les champs non secrets n'affichent plus `env fallback` dans l'UI lorsqu'ils sont deja persistes en base.
- [x] Verifier qu'apres bootstrap complet, les secrets V1 affichent `db_encrypted` des qu'ils sont chiffres en base, hors cas special `database.dsn`.
- [x] Maintenir `database.dsn` stockable et masque en base sans remplacer le bootstrap externe tant que `FRIDA_MEMORY_DB_DSN` reste l'invariant.
- [x] Ajouter des tests backend sur le bootstrap DB complet des sections manquantes.
- [x] Ajouter des tests backend sur la taxonomie d'origine (`db_seed` / `admin_ui` vs `env_fallback`).
- [x] Ajouter un smoke test de deploiement qui echoue si `runtime_settings` n'existe pas.
- [x] Verifier manuellement sur le conteneur cible que l'admin affiche majoritairement `db` apres activation effective de la baseline.
- [x] Prevoir un commit isole pour l'activation reelle de la configuration runtime en base.

### Phase 12 - Prompts visibles et `response_max_tokens` principal editable

- [x] Acter explicitement que tous les prompts systeme / prompts internes envoyes aux modeles doivent etre visibles dans l'admin en lecture seule, sans obliger a ouvrir le code.
- [x] Acter explicitement que, dans cette phase, le seul budget de generation editable est `main_model.response_max_tokens`.
- [x] Maintenir les autres budgets de generation en lecture seule tant qu'ils ne sont pas explicitement ouverts a l'edition.
- [x] Ajouter au schema runtime un champ editable `main_model.response_max_tokens`.
- [x] Seed en base `main_model.response_max_tokens = 1500`, valeur actuellement envoyee a `/api/chat` par defaut.
- [x] Remplacer la lecture du budget de generation principal actuellement envoye a `/api/chat` pour qu'il vienne de `main_model.response_max_tokens` quand aucune surcharge locale de session n'est fournie.
- [x] Exposer en lecture seule, dans la section `main_model`, un bloc informationnel pour :
  - le budget de contexte `FRIDA_MAX_TOKENS`
  - le `SYSTEM_PROMPT` de base actuellement injecte par le front principal
- [x] Exposer en lecture seule, dans la section `arbiter_model`, un bloc informationnel pour :
  - `max_tokens=600` du flux de decision memoire
  - `max_tokens=700` du flux `identity_extractor`
  - `ARBITER_PROMPT_PATH`
  - `IDENTITY_EXTRACTOR_PROMPT_PATH`
  - le contenu actuel des deux prompts
- [x] Exposer en lecture seule, dans la section `summary_model`, un bloc informationnel pour :
  - `SUMMARY_TARGET_TOKENS`
  - `SUMMARY_THRESHOLD_TOKENS`
  - `SUMMARY_KEEP_TURNS`
  - le prompt systeme inline actuellement utilise par le resumeur
- [x] Exposer en lecture seule, dans la section `services`, un bloc informationnel pour :
  - `max_tokens=40` du flux de reformulation web
  - le prompt systeme inline de reformulation web
- [x] Ajouter dans les `GET` admin concernes :
  - `main_model.response_max_tokens` dans le `payload` editable
  - un bloc `readonly_info` distinct pour les prompts et budgets non editables
- [x] Refuser ou ignorer explicitement tout `PATCH` tentant d'ecrire `readonly_info`.
- [x] Ajouter des tests backend sur la presence des informations read-only.
- [x] Ajouter des tests backend sur l'edition de `main_model.response_max_tokens`.
- [x] Ajouter des tests backend garantissant la non-editabilite des prompts et des budgets restant purement informationnels.
- [x] Ajouter dans le frontend admin un champ editable pour `main_model.response_max_tokens`.
- [x] Ajouter dans le frontend admin des cartes read-only naturelles pour tous les prompts systeme exposes par cette phase.
- [x] Ajouter un rendu lisible des prompts longs (bloc scrollable / pre-wrap / textarea readonly) sans introduire de mode edition.
- [x] Maintenir les prompts internes hors edition dans cette phase, sans les rebaptiser en invariants.
- [x] Prevoir un commit isole pour cette extension.

### Phase 13 - Audit d'interpretabilite du pipeline principal

- [ ] Cadrer explicitement que cet audit porte sur le pipeline du modele principal hors details internes de l'arbitre.
- [ ] Produire dans l'admin un audit `clair / ambigu / absent` centre sur ce que le modele principal voit reellement et sur ce qu'il sait explicitement interpreter.
- [ ] Classer comme `clair` dans cet audit :
  - le `SYSTEM_PROMPT` de base
  - la reference temporelle globale (`Nous sommes le...`)
  - les labels Delta-T ajoutes aux messages (`[il y a ...]`)
  - les marqueurs de silence (`[— silence de X —]`)
  - le resume actif (`[Resume de la periode ...]`)
  - les souvenirs pertinents (`[Memoire — souvenirs pertinents]`)
  - le contexte du souvenir (`[Contexte du souvenir — resume ...]`)
  - le contexte web injecte avant la question finale
- [ ] Classer comme `ambigu` dans cet audit :
  - le bloc identites (`[IDENTITE DU MODELE]`, `[IDENTITE DE L'UTILISATEUR]`)
  - les identites dynamiques avec `stability`, `recurrence` et `confidence`
  - les `Indices contextuels recents`
  - la signification operative du score `confidence` a l'interieur de ces indices
- [ ] Classer comme `absent` dans cet audit :
  - une hierarchie explicite entre resume actif, souvenirs pertinents, contexte web et question courante
  - une hierarchie explicite entre identite statique et identite dynamique
  - une regle explicite indiquant comment ponderer `confidence`
  - une provenance explicite des blocs injectes et de leur niveau de fiabilite
- [ ] Exposer dans l'admin, pour `main_model`, un bloc `Pipeline effectif vu par le modele` listant l'ordre exact des briques injectees.
- [ ] Exposer dans ce bloc l'ordre exact de construction du prompt final, au minimum :
  - `SYSTEM_PROMPT` de base
  - augmentation temporelle
  - bloc identites
  - resume actif si present
  - indices contextuels recents si presents
  - contexte du souvenir si present
  - souvenirs pertinents si presents
  - contexte web si present
  - message utilisateur final
- [ ] Exposer pour chaque brique les colonnes minimales suivantes :
  - `visible par le modele`
  - `interpretation explicite par le modele`
  - `statut audit` (`clair`, `ambigu`, `absent`)
  - `source technique`
  - `condition d'apparition`
- [ ] Exposer pour chaque brique sa source technique concrete, sans imposer d'ouvrir le code, par exemple :
  - `web/app.js`
  - `server.py`
  - `core/conv_store.py`
  - `identity/identity.py`
  - `tools/web_search.py`
- [ ] Exposer distinctement ce qui est toujours present, ce qui est conditionnel, et ce qui n'est jamais visible par le modele principal.
- [ ] Exposer dans l'admin la liste des informations aujourd'hui non visibles par le modele principal mais souvent supposees a tort comme presentes.
- [ ] Y inclure explicitement :
  - les decisions d'arbitre brutes
  - les scores internes de l'arbitre
  - les sorties brutes de l'identity extractor
- [ ] Exposer un apercu read-only du `prompt final compose` du modele principal, decoupe par blocs, sans ouvrir de mode edition.
- [ ] Exposer dans cet apercu les marqueurs reels utilises en runtime (`[Memoire — souvenirs pertinents]`, `[Contexte du souvenir — resume ...]`, `[Indices contextuels recents]`, etc.).
- [ ] Exposer les budgets et limites qui structurent ce pipeline, au minimum :
  - `FRIDA_MAX_TOKENS`
  - `IDENTITY_MAX_TOKENS`
  - `CONTEXT_HINTS_MAX_ITEMS`
  - `CONTEXT_HINTS_MAX_TOKENS`
  - `SUMMARY_TARGET_TOKENS`
  - `SUMMARY_THRESHOLD_TOKENS`
  - `SUMMARY_KEEP_TURNS`
- [ ] Exposer les conditions runtime qui changent concretement le prompt final, au minimum :
  - presence ou non d'un resume actif
  - presence ou non de souvenirs pertinents
  - presence ou non d'indices contextuels recents
  - activation ou non de la recherche web
- [ ] Ajouter des tests backend sur la surface d'audit et sur la presence du bloc `Pipeline effectif vu par le modele`.
- [ ] Ajouter des tests frontend sur l'affichage `clair / ambigu / absent` et sur l'apercu read-only du prompt final.
- [ ] Prevoir un commit isole pour cette phase d'audit et de transparence runtime.
