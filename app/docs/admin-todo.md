# Admin Todo

## Contexte initial

Ce document est un livrable d'audit et de planification, pas une implementation.

Objectif du chantier prepare ici : introduire un nouvel admin centre sur les variables contingentes de deploiement, stockees en base, lues par le code depuis la base, sans supprimer brutalement l'admin actuel oriente logs.

Ce document se base sur l'etat reel du depot observe dans le code au 24/03/2026.

## Decisions deja prises

- L'admin V1 porte sur les variables contingentes de deploiement.
- Ces variables doivent vivre en base de donnees.
- Le code doit lire ces variables depuis la base.
- L'admin actuel est conserve comme ancien admin sous `admin-old.*`.
- Le nouvel admin est cree from scratch.
- Le nouvel admin reprend le style du front existant, avec priorite a la reutilisation de `app/web/styles.css` si cela reste propre.
- Les logs constituent un chantier distinct et ulterieur.
- Le present todo couvre l'ensemble du chantier jusqu'a l'implementation finale.
- L'execution reelle ne se fera pas en big bang : elle se fera tranche minimale par tranche minimale.
- Chaque tranche reelle devra etre validee, puis committee et poussee avant d'ouvrir la suivante.
- Pour `main_model`, `arbiter_model` et `summary_model`, tous les parametres effectivement paramétrables doivent entrer dans le perimetre V1, a l'exception explicite de `max_tokens` de reponse.
- `temperature` et `top_p` font donc partie de la logique de configuration globale des modeles et ne sont plus des points ouverts.
- Le routage cible est deja fixe :
  - `/admin` = nouvel admin
  - `/admin-old` = ancien admin
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
- Bloc modele resumieur aujourd'hui en env via `app/config.py` :
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
- Le nouvel admin devra etre cree from scratch dans `app/web/admin.html` et `app/web/admin.js`, tandis que l'ancien admin sera conserve comme `admin-old.*`.
- Le style devra idealement reutiliser `app/web/styles.css`, ce qui n'est pas le cas de l'admin actuel.
- Le front devra traiter la question des secrets masques, des erreurs de validation et de l'eventuel token admin.
- Le front devra traiter explicitement la coexistence entre reglage global admin et reglage local `frida.settings` deja stocke en `localStorage`.

### Validation et couplages existants a ne pas oublier

- `app/minimal_validation.py` verifie aujourd'hui l'existence de `admin.html` et `admin.js`, ainsi que des marqueurs lies a `/api/admin/logs` et `/api/admin/restart`.
- Toute future conservation de l'ancien admin par renommage exigera donc une mise a jour explicite de la validation minimale.
- `app/minimal_validation.py` est aligne sur `fridalogo.png`, qui constitue la reference UI canonique du front courant.

## Invariants a respecter

- Ne pas implementer le nouvel admin dans cette phase preparatoire.
- Ne pas modifier le runtime, les routes actives, le schema SQL ou les comportements applicatifs dans cette phase preparatoire.
- Conserver l'admin actuel comme ancien admin ; ne pas le supprimer brutalement.
- Planifier explicitement le futur renommage `admin.html -> admin-old.html`.
- Planifier explicitement le futur renommage `admin.js -> admin-old.js`.
- Planifier explicitement la creation d'un nouveau `admin.html` from scratch.
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
- [x] Geler dans le chantier la cible `/admin-old` pour l'ancien admin.
- [x] Geler dans le chantier le principe de conservation de l'admin actuel sous `admin-old.*`.
- [x] Geler dans le chantier le principe de creation du nouvel admin from scratch dans `admin.html` / `admin.js`.
- [x] Geler dans le chantier le principe d'adaptation du lien depuis le front vers le nouvel admin.
- [x] Geler dans le chantier le principe de priorite a la reutilisation de `app/web/styles.css`.
- [x] Geler dans le chantier l'exclusion du bloc logs hors du premier admin V1.
- [x] Formaliser dans la spec d'implementation que le todo est complet A -> Z mais que l'execution reelle se fera par micro-etapes successives.
- [x] Formaliser dans la spec d'implementation qu'une tranche minimale = implementation ciblee + validation + commit + push.
- [x] Documenter que l'entree canonique du nouvel admin est `/admin` et que `admin.html` reste un acces technique transitoire pendant la migration.
- [x] Documenter que l'entree canonique de l'ancien admin est `/admin-old` et que `admin-old.html` reste un acces technique transitoire pendant la migration.
- [x] Documenter la politique UX appliquee quand `FRIDA_ADMIN_TOKEN` est actif : saisie a l'ouverture, stockage en `sessionStorage`, envoi via `X-Admin-Token` sur les requetes `/api/admin/*`.

### Phase 1 - Conception du modele de donnees de configuration

- [ ] Creer le module backend de lecture/ecriture de configuration runtime dans `app/admin/runtime_settings.py`.
- [ ] Poser `runtime_settings` comme table primaire des settings runtime.
- [ ] Poser une granularite `une ligne par section JSONB` dans `runtime_settings`.
- [ ] Poser les sections minimales du schema : `main_model`, `arbiter_model`, `summary_model`, `embedding`, `database`, `services`, `resources`.
- [ ] Lister pour `main_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [ ] Lister pour `arbiter_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [ ] Lister pour `summary_model` tous les champs effectivement paramétrables a stocker en base, y compris `temperature` et `top_p`, hors `max_tokens` de reponse.
- [ ] Lister pour `embedding` les champs exacts a stocker en base.
- [ ] Lister pour `database` les champs exacts a stocker en base pour la configuration V1 relue depuis la base.
- [ ] Documenter dans le schema la distinction entre bootstrap DB minimal externe et configuration `database` stockee en base.
- [ ] Lister pour `services` les champs exacts a stocker en base.
- [ ] Lister pour `resources` les champs exacts a stocker en base.
- [ ] Marquer, champ par champ, lesquels sont des secrets et lesquels ne le sont pas.
- [ ] Ajouter dans le design un champ `updated_at`.
- [ ] Ajouter dans le design un champ `updated_by`.
- [ ] Ajouter dans le design un champ `source` / `origin` pour distinguer seed env et valeur editee.
- [ ] Ajouter dans le design un champ minimal de version de schema.
- [ ] Integrer `runtime_settings_history` des la V1.
- [ ] Utiliser `pgcrypto` pour la politique de secret retenue.
- [ ] Exposer au front un secret present sous forme masquee avec un indicateur `is_set`, sans jamais renvoyer sa valeur en clair.
- [ ] Ajouter `EMBED_MODEL` au schema V1 et au code de consommation associe.
- [ ] Integrer `OPENROUTER_BASE`, `OPENROUTER_REFERER`, `OPENROUTER_APP_NAME` et `OPENROUTER_TITLE_*` au perimetre V1 du bloc modele principal / provider.
- [ ] Integrer `ARBITER_TIMEOUT_S` au perimetre V1 du bloc arbitre.
- [ ] Integrer `SEARXNG_RESULTS`, `CRAWL4AI_TOP_N` et `CRAWL4AI_MAX_CHARS` au perimetre V1 du bloc services.
- [ ] Documenter explicitement que `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB minimal externe tant que la transition n'est pas achevee.

### Phase 2 - Schema SQL et seed initial

- [ ] Creer la migration SQL de la table principale des settings runtime.
- [ ] Ajouter la contrainte d'unicite necessaire sur la cle ou sur le couple section/cle.
- [ ] Ajouter les index necessaires a la lecture par section.
- [ ] Ajouter la structure necessaire au stockage des secrets selon la politique retenue.
- [ ] Ajouter le champ/indicateur permettant de savoir si une valeur secrete est presente.
- [ ] Creer la table d'historique/revision `runtime_settings_history`.
- [ ] Prevoir une migration idempotente executable sans casser un environnement deja initialise.
- [ ] Ecrire la logique de seed des valeurs non secretes depuis l'environnement courant.
- [ ] Ecrire la logique de seed initial des valeurs secretes depuis l'environnement courant, sans re-exposition en clair.
- [ ] Implementer la regle "ne pas ecraser une valeur deja presente en DB lors d'un reseed".
- [ ] Prevoir un moyen explicite de reconnaitre qu'une section n'a jamais encore ete seedee.
- [ ] Documenter dans la migration qu'aucune extension PostgreSQL supplementaire n'est requise a priori au-dela de `pgcrypto` deja active.
- [ ] Documenter dans la migration la separation entre bootstrap DB minimal externe et sections V1 stockees dans `runtime_settings`.
- [ ] Exclure explicitement `FRIDA_MEMORY_DB_DSN` du seed de `runtime_settings` tant que la transition n'est pas achevee.
- [ ] Prevoir un commit isole pour la migration SQL et le seed initial, sans branchement frontend.

### Phase 3 - Couche backend de lecture de configuration

- [ ] Creer le module dedie a la lecture des settings runtime depuis la DB.
- [ ] Ajouter un fallback env explicite tant que la table ou la valeur n'existe pas.
- [ ] Ajouter un point d'entree backend pour lire la section `main_model`.
- [ ] Ajouter un point d'entree backend pour lire la section `arbiter_model`.
- [ ] Ajouter un point d'entree backend pour lire la section `summary_model`.
- [ ] Ajouter un point d'entree backend pour lire la section `embedding`.
- [ ] Ajouter un point d'entree backend pour lire la section `database`.
- [ ] Ajouter un point d'entree backend pour lire la section `services`.
- [ ] Ajouter un point d'entree backend pour lire la section `resources`.
- [ ] Ajouter une redaction automatique des secrets dans tous les objets renvoyables au frontend.
- [ ] Ajouter une validation backend par champ avant toute ecriture.
- [ ] Implementer une lecture centralisee via un cache explicitement invalide apres ecriture.
- [ ] Implementer le comportement `table de settings vide = fallback env transitoire + statut visible`.
- [ ] Implementer le comportement `DB indisponible = fallback env transitoire quand il existe, sinon erreur de configuration explicite`.
- [ ] Implementer le comportement `secret requis absent = erreur de configuration explicite, sans fuite de valeur`.
- [ ] Laisser explicitement `app/admin/admin_logs.py` hors de cette bascule V1.
- [ ] Laisser explicitement `FRIDA_WEB_HOST` et `FRIDA_WEB_PORT` hors de cette bascule V1.
- [ ] Laisser explicitement `FRIDA_MEMORY_DB_DSN` dans le bootstrap DB minimal externe tant que la transition n'est pas achevee.
- [ ] Prevoir un commit isole pour la couche backend de lecture avant remplacement des usages.

### Phase 4 - Remplacement progressif des lectures actuelles dans le code

- [ ] Remplacer la lecture du modele principal dans `app/core/llm_client.py` par la nouvelle couche runtime config.
- [ ] Remplacer la lecture du modele principal dans `app/server.py` par la nouvelle couche runtime config.
- [ ] Remplacer la lecture du modele principal utilisee par `app/tools/web_search.py`.
- [ ] Remplacer la lecture du modele principal utilisee pour le comptage de tokens dans `app/server.py`.
- [ ] Remplacer la lecture du modele principal utilisee pour le comptage de tokens dans `app/identity/identity.py`.
- [ ] Remplacer la lecture du modele arbitre dans `app/memory/arbiter.py`.
- [ ] Remplacer la lecture du modele resumieur dans `app/memory/summarizer.py`.
- [ ] Remplacer la lecture du bloc embeddings dans `app/memory/memory_store.py`.
- [ ] Remplacer la lecture du bloc services externes dans `app/tools/web_search.py`.
- [ ] Remplacer la lecture des chemins / ressources externes dans `app/identity/identity.py`.
- [ ] Remplacer la lecture des memes chemins / ressources externes dans `app/minimal_validation.py`.
- [ ] Remplacer la lecture du bloc `database` dans `app/core/conv_store.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [ ] Remplacer la lecture du bloc `database` dans `app/memory/memory_store.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [ ] Remplacer la lecture du bloc `database` dans `app/minimal_validation.py` une fois la separation bootstrap externe / config V1 effectivement branchee.
- [ ] Verifier que `app/config.py` reste utilisable comme fallback transitoire tant que la bascule n'est pas complete.
- [ ] Verifier que `app/admin/admin_logs.py` continue a fonctionner sans regression apres introduction de la nouvelle couche.
- [ ] Verifier que `app/run.sh` et `docker-compose.yml` ne sont pas touches par inadvertance pendant cette phase.
- [ ] Prevoir un commit isole pour chaque bloc remplace (`main_model`, `arbiter_model`, `summary_model`, `embedding`, `services`, `resources`, puis `database`).

### Phase 5 - API backend du nouvel admin

- [ ] Ouvrir le prefixe `/api/admin/settings` pour la configuration du nouvel admin.
- [ ] Ajouter une route de lecture agregee de l'ensemble des sections du nouvel admin.
- [ ] Ajouter une route `GET` de lecture pour la section `main_model`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `main_model`.
- [ ] Ajouter une route `GET` de lecture pour la section `arbiter_model`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `arbiter_model`.
- [ ] Ajouter une route `GET` de lecture pour la section `summary_model`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `summary_model`.
- [ ] Ajouter une route `GET` de lecture pour la section `embedding`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `embedding`.
- [ ] Ajouter une route `GET` de lecture pour la section `database`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `database`.
- [ ] Ajouter une route `GET` de lecture pour la section `services`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `services`.
- [ ] Ajouter une route `GET` de lecture pour la section `resources`.
- [ ] Ajouter une route `PATCH` de mise a jour pour la section `resources`.
- [ ] Ajouter une route de statut bootstrap/fallback pour rendre visible la source effective de configuration.
- [ ] Ajouter une route de validation/smoke test par section pour les verifications techniques avant sauvegarde finale.
- [ ] Brancher toutes ces routes sous le garde admin existant.
- [ ] Verifier que les reponses `GET` masquent tous les secrets.
- [ ] Verifier que les reponses `PATCH` ne logguent jamais les secrets en clair.
- [ ] Conserver inchangées `GET /api/admin/logs` et `POST /api/admin/restart`.
- [ ] Ne pas melanger les endpoints hermeneutiques existants avec les endpoints de configuration V1.
- [ ] Prevoir un commit isole pour l'ouverture des routes API de configuration.

### Phase 6 - Conservation explicite de l'ancien admin

- [ ] Copier `app/web/admin.html` vers `app/web/admin-old.html`.
- [ ] Copier `app/web/admin.js` vers `app/web/admin-old.js`.
- [ ] Mettre a jour `app/web/admin-old.html` pour charger `admin-old.js`.
- [ ] Ajouter une route Flask `/admin-old` qui serve `admin-old.html`.
- [ ] Maintenir l'acces technique direct `/admin-old.html` pendant la transition en plus de `/admin-old`.
- [ ] Reserver `app/web/admin.html` au futur nouvel admin.
- [ ] Reserver `app/web/admin.js` au futur nouvel admin.
- [ ] Verifier que `admin-old.js` continue a parler a `/api/admin/logs` et `/api/admin/restart` sans changement de comportement.
- [ ] Verifier que l'ancien admin conserve son usage actuel de logs/restart sans refactor opportuniste.
- [ ] Documenter explicitement dans le code ou la doc que les routes hermeneutiques backend existent mais ne sont pas branchees dans l'ancien admin UI.
- [ ] Ajouter un lien visible du nouvel admin vers l'ancien admin une fois le nouvel admin en place.
- [ ] Prevoir un commit isole uniquement pour la preservation/renommage de l'admin legacy.

### Phase 7 - Nouveau frontend admin from scratch

- [ ] Creer le nouveau `app/web/admin.html` from scratch.
- [ ] Creer le nouveau `app/web/admin.js` from scratch.
- [ ] Verifier d'abord si `app/web/styles.css` peut etre reutilise tel quel sans casser le front principal.
- [ ] Si la reutilisation directe est propre, brancher `styles.css` dans le nouvel admin.
- [ ] Si la reutilisation directe n'est pas propre, creer une derivation CSS minimale et justifiee au lieu d'un nouveau bloc inline massif.
- [ ] Construire une section UI dediee au modele principal.
- [ ] Construire une section UI dediee au modele arbitre.
- [ ] Construire une section UI dediee au modele resumieur.
- [ ] Construire une section UI dediee au bloc embeddings.
- [ ] Construire une section UI dediee au bloc base de donnees.
- [ ] Construire une section UI dediee au bloc services externes.
- [ ] Construire une section UI dediee au bloc chemins / ressources externes.
- [ ] Ajouter un affichage masque des secrets deja presents.
- [ ] Ajouter un mecanisme explicite de remplacement des secrets sans re-affichage en clair.
- [ ] Ajouter un etat de chargement par section.
- [ ] Ajouter un etat d'erreur par section.
- [ ] Ajouter un etat "modifications non sauvegardees" par section.
- [ ] Ajouter un bouton d'enregistrement par section.
- [ ] Ajouter un retour de validation lisible par champ en cas d'erreur backend.
- [ ] Ajouter un indicateur visible de source de valeur (`env fallback` vs `db`).
- [ ] Ajouter un lien visible vers l'ancien admin.
- [ ] Verifier que le nouveau `admin.js` n'embarque pas de logique logs/restart par reflexe.
- [ ] Prevoir un commit isole pour le nouveau frontend admin.

### Phase 8 - Integration minimale avec le front principal

- [ ] Modifier `app/web/app.js` pour que le bouton `Parametres` vise le nouvel admin et non plus `admin.html` legacy direct.
- [ ] Pointer le bouton `Parametres` du front principal vers `/admin`.
- [ ] Aligner cette cible avec la route Flask et avec les assets statiques reellement exposes.
- [ ] Retirer `temperature` et `top_p` de `frida.settings` dans `localStorage`.
- [ ] Brancher `temperature` et `top_p` sur la logique globale de configuration des modeles.
- [ ] Retirer l'envoi direct de `temperature` et `top_p` depuis le front vers `/api/chat`.
- [ ] Limiter `frida.settings` aux reglages de session restant hors admin V1.
- [ ] Requalifier clairement `max_tokens` comme reglage de session hors admin V1 tant qu'il reste hors perimetre.
- [ ] Maintenir `max_tokens` hors du nouvel admin V1.
- [ ] Maintenir `SYSTEM_PROMPT` hors du nouvel admin V1.
- [ ] Verifier que la navigation vers l'ancien admin reste possible apres changement du bouton principal.
- [ ] Prevoir un commit isole pour l'integration minimale du front principal.

### Phase 9 - Validation automatique et non-regression

- [ ] Mettre a jour `app/minimal_validation.py` pour couvrir le nouvel admin.
- [ ] Mettre a jour `app/minimal_validation.py` pour conserver un smoke test de l'ancien admin.
- [ ] Ajouter un test de presence des nouveaux assets `admin.html` et `admin.js`.
- [ ] Ajouter un test de presence des assets legacy `admin-old.html` et `admin-old.js`.
- [ ] Ajouter un smoke test `GET /admin`.
- [ ] Ajouter un smoke test `GET /admin-old`.
- [ ] Ajouter un smoke test de lecture agregee de la configuration admin.
- [ ] Ajouter un smoke test d'update valide sur une section non secrete.
- [ ] Ajouter un smoke test d'update invalide pour verifier la validation backend.
- [ ] Ajouter un smoke test garantissant qu'un secret ne ressort jamais en clair via un `GET`.
- [ ] Verifier manuellement que l'ancien admin logs/restart continue a fonctionner.
- [ ] Verifier manuellement que les routes hermeneutiques existantes repondent encore apres l'ajout du nouvel admin.
- [ ] Verifier manuellement que le chat principal fonctionne encore apres bascule des lectures runtime vers la DB.
- [ ] Prevoir un commit isole pour la couche de validation et de non-regression.

### Phase 10 - Sequence de commits recommandee

- [ ] Commit 1 : migration SQL + seed initial + design documentaire du bootstrap DB.
- [ ] Commit 2 : couche backend de lecture runtime config avec fallback env, sans front.
- [ ] Commit 3 : remplacement progressif des lectures code sur un premier bloc isole (`main_model` ou `services`).
- [ ] Commit 4 : ouverture des routes API de configuration.
- [ ] Commit 5 : preservation/renommage de l'ancien admin en `admin-old.*`.
- [ ] Commit 6 : creation du nouveau frontend admin.
- [ ] Commit 7 : adaptation du bouton `Parametres` dans le front principal.
- [ ] Commit 8 : validation minimale, smoke tests et non-regression.
- [ ] Commit 9 : documentation finale d'exploitation/migration du nouvel admin.
