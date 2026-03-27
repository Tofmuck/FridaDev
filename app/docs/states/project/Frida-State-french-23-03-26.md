# Frida State — 23/03/2026

## Objet du document

Ce document fixe un **état lisible et structuré du code** à la date du **23 mars 2026**.  
Il a vocation à être **réécrit régulièrement** au fil des changements, en gardant la même logique :

- décrire le périmètre réel du dépôt ;
- rendre visibles les invariants techniques du moment ;
- signaler les zones propres, les dettes encore ouvertes et les risques à surveiller ;
- servir de base de comparaison pour les audits suivants.

Ce document ne remplace pas la documentation conceptuelle du projet. Il décrit **l'état du code et de l'architecture effective** du dépôt `FridaDev` à l'instant T.

## 1. Résumé exécutif

À la date du 23/03/2026, le dépôt `FridaDev` est une base applicative autonome pour **Frida**, organisée autour :

- d'une stack Docker dédiée ;
- d'une application Flask unique ;
- d'une mémoire métier portée principalement par PostgreSQL + `pgvector` ;
- d'une interface web minimaliste ;
- d'une couche herméneutique reposant sur traces, résumés, identités et arbitrage ;
- d'un outillage d'administration et d'une validation minimale.

Le chantier a nettement avancé sur un point central : **le state métier conversationnel est désormais DB-first, et en pratique presque DB-only** pour le flux normal.

Les conversations, messages, résumés, traces, identités, évidences, conflits et décisions d'arbitrage vivent désormais en base. Les prompts statiques, les assets web et les logs techniques restent en fichiers, ce qui est cohérent avec la direction actuelle.

Le dépôt est déjà exploitable, mais il n'est pas encore totalement prêt pour un premier push public propre sans sélection :

- la sécurité admin par défaut reste trop ouverte pour un dépôt partagé ;
- la purge forte reste plus destructive que la politique documentaire visée ;
- le bootstrap d'un clone vierge demande encore une préparation runtime explicite pour `state/data`.

## 2. Périmètre et conventions

### 2.1 Identité projet

- **Nom du dépôt / stack** : `FridaDev`
- **Nom de l'IA dans le produit** : `Frida`
- **Site** : <https://frida-ai.fr>
- **Contact** : <tofmuck@frida-ai.fr>

### 2.2 Structure documentaire

L'arborescence documentaire actuelle est la suivante :

- `app/docs/states/` : états structurés, baselines, specs et documents de situation ;
- `app/docs/todo-done/` : documents de travail internes, déjà traités ;
- `app/docs/todo-todo/` : feuilles de route internes encore ouvertes.

À partir de ce state :

- `todo-done/` et `todo-todo/` doivent être considérés comme **internes à l'équipe** ;
- ils sont exclus du premier push par défaut ;
- `states/` devient le lieu des audits réguliers et des documents pérennes.

## 3. État du dépôt

### 3.1 Racine

Le dépôt versionne à sa racine :

- `README.md`
- `docker-compose.yml`
- `stack.sh`
- `.gitignore`
- `app/`

### 3.2 Ce que le dépôt versionne réellement

Le dépôt versionne actuellement :

- le code Flask ;
- les modules mémoire, identité, admin et outils ;
- les prompts statiques ;
- l'interface web ;
- les scripts d'exploitation ;
- les exemples de configuration ;
- les documents de référence situés dans `app/docs/states/`.

### 3.3 Ce que le dépôt ne versionne pas

Le dépôt n'a pas vocation à versionner :

- `app/.env`
- `state/`
- `app/conv/`
- `app/logs/`
- `app/data/`
- les sauvegardes, `.bak`, fichiers temporaires et fichiers système macOS
- les documents internes `app/docs/todo-done/`
- les documents internes `app/docs/todo-todo/`

### 3.4 Conséquence pratique

Le dépôt décrit donc **le code et l'architecture**, mais pas un runtime complet autosuffisant.  
Un clone neuf demande encore :

- un `app/.env` réel ;
- un stockage runtime `state/` ;
- les fichiers d'identité runtime dans `state/data/identity/`.

## 4. Stack et exécution

### 4.1 Docker / orchestration

Le fichier `docker-compose.yml` définit une stack simple :

- projet Compose : `fridadev`
- service : `fridadev`
- conteneur : `FridaDev`
- image locale : `fridadev-app:local`
- port publié : `8093 -> 8089`

Volumes montés :

- `./state/conv:/app/conv`
- `./state/logs:/app/logs`
- `./state/data:/app/data`

### 4.2 Script opérateur

`stack.sh` fournit les commandes :

- `up`
- `down`
- `restart`
- `logs`
- `ps`
- `config`
- `health`

La logique est simple et lisible.  
Le `restart` actuel est un `docker compose up -d --build`, ce qui correspond bien au mode de travail courant sur le front et le backend.

### 4.3 Santé applicative

Le healthcheck Docker interroge `/` via Python.  
La stack est donc pilotée par un signal très simple : l'interface doit répondre en HTTP sur le port interne `8089`.

## 5. Configuration et dépendances externes

### 5.1 Configuration centrale

La configuration applicative est centralisée dans `app/config.py`.  
On y trouve les familles de paramètres suivantes :

- provider LLM (`OpenRouter`) ;
- recherche web (`SearXNG`) ;
- crawl (`Crawl4AI`) ;
- service d'embeddings ;
- stockage mémoire PostgreSQL ;
- paramètres de résumés ;
- paramètres herméneutiques ;
- sécurité admin.

### 5.2 Dépendances externes actuellement assumées

Le code suppose la présence ou l'accès aux services suivants :

- `OpenRouter` pour le LLM principal, l'arbitre et le résumeur ;
- `SearXNG` pour la recherche web ;
- `Crawl4AI` pour l'extraction de contenu ;
- un service d'embeddings ;
- PostgreSQL avec extensions `pgvector` et `pgcrypto`.

### 5.3 Point positif

Ticketmaster et météo ont été retirés du produit actif.  
La surface externe est donc plus cohérente avec la direction de Frida comme outil de travail et de recherche.

### 5.4 Point de vigilance

La configuration d'infrastructure reste **principalement pilotée par `.env`**.  
La future page `Infrastructure` n'est pas encore implémentée. À ce jour :

- les providers sont configurés côté runtime ;
- ils ne sont pas encore pilotables depuis l'admin ;
- les changements exigent encore une action opérateur.

## 6. Surface HTTP et API

### 6.1 Interface publique

Routes principales :

- `POST /api/chat`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/<conversation_id>/messages`
- `PATCH /api/conversations/<conversation_id>`
- `DELETE /api/conversations/<conversation_id>`
- `GET /`
- `GET /admin`

### 6.2 Interface admin

Routes admin observées :

- `GET /api/admin/logs`
- `POST /api/admin/restart`
- `GET /api/admin/hermeneutics/identity-candidates`
- `GET /api/admin/hermeneutics/arbiter-decisions`
- `POST /api/admin/hermeneutics/identity/force-accept`
- `POST /api/admin/hermeneutics/identity/force-reject`
- `POST /api/admin/hermeneutics/identity/relabel`
- `GET /api/admin/hermeneutics/dashboard`
- `GET /api/admin/hermeneutics/corrections-export`

### 6.3 Politique actuelle de sécurité admin

Le garde admin existe bien dans `server.py`, mais son activation dépend encore des paramètres :

- `FRIDA_ADMIN_LAN_ONLY`
- `FRIDA_ADMIN_TOKEN`

Dans les exemples de config actuels, le token est vide et le mode LAN-only est désactivé.  
Conclusion : **le code sait protéger l'admin, mais les défauts de configuration ne sont pas encore sécurisés par défaut**.

## 7. Conversations : persistance et cycle de vie

### 7.1 État réel

Le flux conversationnel actif est désormais stocké en base via deux tables :

- `conversations`
- `conversation_messages`

Les messages persistés embarquent notamment :

- `role`
- `content`
- `timestamp`
- `summarized_by`
- `embedded`
- `meta`

### 7.2 Ce qui a changé structurellement

Le bootstrap JSON au démarrage a été désactivé.  
`save_conversation()`, `load_conversation()` et `read_conversation()` sont désormais alignés sur PostgreSQL pour le flux normal.

Le dossier `app/conv/` existe encore dans le code et dans la stack pour compatibilité opératoire, mais il n'est plus la source primaire du state métier.

### 7.3 Suppression logique

La suppression exposée côté UI repose sur `deleted_at` :

- une conversation peut sortir du front ;
- elle reste en base ;
- le catalogue standard filtre `deleted_at IS NULL`.

Cette logique est cohérente avec la politique actuellement visée :

- disparition de l'UI ;
- conservation de la matière en base ;
- pas de destruction silencieuse.

### 7.4 Purge forte

Une fonction de suppression forte existe encore (`delete_conversation`), mais elle est plus destructive que la politique documentaire la plus récente :

- elle purge la conversation ;
- elle purge aussi messages, traces, résumés, décisions, évidences, identités et conflits liés.

Conclusion : **la logique de purge forte existe encore comme outil technique**, mais elle n'est pas encore alignée avec l'ambition de mémoire consolidée à long terme.

## 8. Mémoire, résumés et identité

### 8.1 Tables métier

Le module `memory_store.py` initialise les tables suivantes :

- `traces`
- `summaries`
- `identities`
- `identity_evidence`
- `arbiter_decisions`
- `identity_conflicts`

Des index sont posés sur les accès fréquents, y compris les index utiles à `pgvector`.

### 8.2 Traces

Les traces sont stockées en base avec embeddings.  
La récupération mémoire s'appuie sur la similarité vectorielle, avec un `top_k` configurable.

Le mécanisme `save_new_traces()` a été rendu idempotent :

- une trace déjà présente n'est pas réinsérée ;
- le flag `embedded` est persisté côté message ;
- le système évite les doublons après redémarrage.

### 8.3 Résumés

Les résumés conversationnels sont stockés en SQL.  
Le résumé actif est choisi à partir des timestamps (`start_ts`, `end_ts`) et non plus à partir d'un simple état volatil.

`build_prompt_messages()` reconstruit le contexte à partir :

- du résumé actif ;
- des messages postérieurs au cutoff ;
- des traces mémoire ;
- des hints identitaires récents.

### 8.4 Identités

La couche identité combine :

- des identités statiques en fichiers ;
- des identités dynamiques persistées en base.

Le bloc d'identité injecté dans le prompt final est donc hybride par conception :

- statique pour les fichiers de référence ;
- dynamique pour la mémoire identitaire consolidée.

### 8.5 Conflits et arbitrage

Le système dispose d'une mémoire explicite des tensions identitaires :

- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

Cette couche donne à Frida une base de travail plus interprétative qu'un simple chat conversationnel linéaire.

## 9. Herméneutique et arbitrage

### 9.1 Position actuelle

L'architecture herméneutique est bien installée dans le code :

- mode `off`
- mode `shadow`
- mode `enforced_identities`
- mode `enforced_all`

### 9.2 Invariants visibles

On retrouve déjà dans le code plusieurs invariants alignés avec la philosophie du projet :

- séparation partielle entre génération et validation ;
- hiérarchisation des traces ;
- possibilité de filtrer la mémoire retenue ;
- gestion de l'incertitude par l'arbitre ;
- extraction et consolidation d'identités ;
- correction manuelle possible via l'admin.

### 9.3 Limite actuelle

La couche herméneutique est présente et sérieuse, mais elle reste encore très liée à des seuils de configuration et à des choix d'implémentation internes.  
Elle n'est pas encore exposée comme un système pleinement documenté et administrable de bout en bout.

## 10. Admin, logs et observabilité

### 10.1 Admin

L'admin a deux fonctions principales aujourd'hui :

- observer ;
- intervenir sur la couche herméneutique.

Le redémarrage admin ne pilote plus un ancien service externe : il provoque l'auto-sortie du runtime, ce qui laisse Docker relancer le conteneur.

### 10.2 Logs admin

Les logs admin sont écrits en JSONL, avec :

- rotation ;
- redaction de certains champs sensibles ;
- migration d'un ancien chemin legacy si nécessaire.

La solution est simple, robuste et adaptée à l'état actuel du projet.

### 10.3 Point de vigilance

Des noms de logger legacy subsistaient encore dans plusieurs modules :

- `core/conv_store.py`
- `memory/memory_store.py`
- `memory/arbiter.py`
- `identity/identity.py`
- `tools/web_search.py`
- `admin/admin_logs.py`

Ce n'est pas bloquant techniquement, mais c'est un résidu de dérivation à nettoyer pour un dépôt public propre.

## 11. Frontend

### 11.1 Direction actuelle

L'interface web a été simplifiée autour d'un design plus sobre et plus adulte :

- branding réduit à `Frida` + logo ;
- interface de chat allégée ;
- séparation claire avec l'admin.

### 11.2 Comportements déjà en place

Le front courant prend déjà en charge :

- affichage des conversations ;
- renommage ;
- suppression logique ;
- recherche web activable ;
- redirection du bouton paramètres vers `admin.html` ;
- affichage des timestamps de messages ;
- bylines `Vous` / `Frida`.

### 11.3 Point de vigilance

Le front est déjà cohérent, mais reste un chantier vivant :

- l'ergonomie conversationnelle continue d'évoluer ;
- le design system n'est pas encore figé ;
- l'UI ne reflète pas encore toute l'ambition architecturale du backend.

## 12. Validation et qualité

### 12.1 Validation minimale

Le script `app/minimal_validation.py` vérifie déjà plusieurs invariants utiles :

- import et boot du serveur ;
- présence et structure des tables SQL attendues ;
- présence des prompts/fichiers nécessaires ;
- présence des assets UI ;
- smoke tests HTTP/API ;
- garde contre la résurrection de vieux JSON legacy.

### 12.2 Lecture de l'état qualité

Cette validation minimale constitue un bon filet de sécurité pour continuer à faire bouger le produit sans revenir à un fonctionnement hybride ancien.

Elle n'est pas encore une suite de tests exhaustive, mais elle est déjà suffisante pour :

- vérifier le socle ;
- rejouer les invariants les plus critiques ;
- sécuriser les prochains chantiers front et infra.

## 13. Points solides à la date du 23/03/2026

- séparation Docker dédiée et simple à exploiter ;
- mémoire métier fortement recentrée sur PostgreSQL ;
- conversation store désormais cohérent avec la stratégie DB-first ;
- identités, évidences, conflits et arbitrage déjà présents en base ;
- retrait des intégrations parasites (météo, Ticketmaster) ;
- admin herméneutique déjà utile ;
- validation minimale déjà opérationnelle ;
- identité produit clarifiée autour de `Frida`.

## 14. Écarts et risques connus

### 14.1 Sécurité admin par défaut

Le plus gros écart immédiat avant publication reste la sécurité admin par défaut :

- token vide dans les exemples ;
- accès LAN-only désactivé par défaut ;
- protection présente dans le code, mais non durcie par défaut.

### 14.2 Bootstrap d'un clone neuf

Le dépôt n'est pas encore entièrement plug-and-play :

- `state/` est ignoré, ce qui est normal ;
- mais `state/data/identity/*` reste nécessaire au runtime ;
- un bootstrap documenté ou un mécanisme d'initialisation manque encore.

### 14.3 Purge forte non alignée

La suppression forte existe encore selon une logique trop destructrice par rapport à la doctrine actuelle de conservation mémoire.

### 14.4 Noms legacy

Il restait des reliquats de namespace logger legacy dans les logs et dans certains résidus documentaires.

### 14.5 Documentation de dépôt

La documentation est désormais mieux structurée, mais `states/` contient encore plusieurs documents historiques qui ne sont pas tous homogènes entre eux.  
Un travail de curation progressive reste utile.

## 15. Recommandations pour les prochains states

À chaque nouvel audit `Frida-State-*`, il faudra vérifier explicitement :

- la sécurité admin effective ;
- le degré réel de `DB-only` ;
- la cohérence entre politique documentaire et logique de purge ;
- le statut de la future page `Infrastructure` ;
- l'état des loggers legacy ;
- la capacité d'un clone neuf à démarrer proprement ;
- la qualité du front après les prochaines itérations.

## 16. Conclusion

Au 23 mars 2026, `FridaDev` n'est plus un simple clone dérivé : c'est déjà une base logicielle cohérente pour **Frida**, avec :

- une identité clarifiée ;
- une mémoire structurée ;
- une architecture herméneutique réelle ;
- un front redevenu exploitable ;
- une documentation en train de se stabiliser.

Le chantier n'est pas fini, mais il est désormais **lisible**.  
Le prochain enjeu n'est plus de savoir si le système tient debout : il s'agit surtout de **durcir, clarifier et publier proprement** sans perdre l'exigence philosophique et technique du projet.
