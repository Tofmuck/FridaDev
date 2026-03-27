# Memory System — Plan d'implémentation

---

## Phase 1 — Delta-T + Identités figées

### 1.1 Delta-T dans les prompts

- [x] Injecter la date/heure courante (`now`) dans le system prompt à chaque requête
- [x] Définir le format de référence temporelle : `YYYY-MM-DD HH:MM UTC`
- [x] Annoter chaque message du payload avec son timestamp relatif à `now`
  - [x] Format lisible : `« il y a 3 jours »`, `« aujourd'hui à 14h »`, `« hier à 21h »` (heure locale FRIDA_TIMEZONE)
  - [x] Créer une fonction `delta_t_label(ts_msg, ts_now) -> str` dans `conv_store.py`
- [x] Modifier `build_prompt_messages()` pour inclure le Delta-T dans chaque entrée
  - [x] Format final : `[user — il y a 2 jours] contenu du message`
  - [x] Ne pas annoter le system prompt lui-même
- [x] Ajouter une règle dans le system prompt : le modèle **ne mentionne jamais** `now` spontanément
- [x] Ajouter `FRIDA_TIMEZONE` dans `config.py` (défaut : `Europe/Paris`) pour l'affichage local
- [x] Vérifier que le Delta-T ne pollue pas les tokens inutilement (annotations courtes)

### 1.2 Identité LLM (figée)

- [x] Créer le fichier `data/identity/llm_identity.txt` contenant le texte d'identité du modèle
  - [x] Champs minimaux : nom, rôle, traits de caractère, règles de comportement
  - [x] Format : texte libre structuré, injectable dans le system prompt
- [x] Créer une fonction `load_llm_identity() -> str` dans un nouveau module `identity.py`
- [x] Injecter l'identité LLM en tête du system prompt dans `api_chat()`
- [x] S'assurer que l'identité figée ne remplace pas le system prompt existant mais le **précède**
- [x] Ajouter `FRIDA_LLM_IDENTITY_PATH` dans `config.py`

### 1.3 Identité utilisateur (figée)

- [x] Créer le fichier `data/identity/user_identity.txt` contenant le profil utilisateur
  - [x] Champs minimaux : prénom, âge, centres d'intérêt, style de communication préféré
  - [x] Format : texte libre structuré
- [x] Créer une fonction `load_user_identity() -> str` dans `identity.py`
- [x] Injecter l'identité utilisateur dans le system prompt après l'identité LLM
- [x] Ajouter `FRIDA_USER_IDENTITY_PATH` dans `config.py`

### 1.4 Validation Phase 1

- [x] Vérifier dans les logs que les timestamps apparaissent bien dans les messages
- [x] Vérifier que le modèle utilise le Delta-T dans ses réponses quand pertinent
- [x] Vérifier que le modèle ne dit jamais "nous sommes le X" spontanément
- [x] Vérifier que les identités sont correctement injectées dans le payload LLM

---

## Phase 2 — Résumés périodiques

### 2.1 Détection du seuil

- [x] Définir `SUMMARY_THRESHOLD_TOKENS` dans `config.py` (défaut : 35 000)
- [x] Définir `SUMMARY_TARGET_TOKENS` dans `config.py` (défaut : 2 000)
- [x] Définir `SUMMARY_KEEP_TURNS` dans `config.py` (défaut : 5 derniers échanges)
- [x] Dans `build_prompt_messages()`, détecter quand le total tokens dépasse le seuil
- [x] Distinguer les messages bruts (dialogue) des messages déjà résumés (ne jamais résumer un résumé)

### 2.2 Génération du résumé

- [x] Créer une fonction `summarize_conversation(turns, model) -> str` dans un nouveau module `summarizer.py`
  - [x] Appel LLM léger via OpenRouter (modèle cheap configurable)
  - [x] Prompt dédié : résumer uniquement le dialogue, conserver les faits clés, les préférences exprimées, les décisions prises
  - [x] Le résumé inclut son propre Delta-T : `start_ts` et `end_ts` de la période couverte
- [x] Ajouter `SUMMARY_MODEL` dans `config.py` (défaut : modèle cheap type `minimax/minimax-m2.5`)

### 2.3 Stockage du résumé

- [x] Persister chaque résumé généré dans la table `summaries` PostgreSQL via `memory_store.save_summary()`
  - [x] Embedding du contenu du résumé pour RAG futur sur les résumés
  - [x] Appelé depuis `summarizer.maybe_summarize()` juste après l'ajout au JSON
- [x] Créer la structure de données d'un résumé :
  ```json
  {
    "id": "uuid",
    "start_ts": "ISO",
    "end_ts": "ISO",
    "content": "texte du résumé",
    "turn_count": 42
  }
  ```
- [x] Stocker le résumé dans la conversation JSON : champ `summaries: []`
- [x] Associer chaque message couvert à un résumé (champ `summarized_by: uuid` optionnel)

### 2.4 Injection dans le payload

- [x] Modifier `build_prompt_messages()` pour injecter le résumé actif en slot `from_resumé`
  - [x] Position : après le system prompt, avant les messages récents
  - [x] Format : `[Résumé de la période du X au Y] contenu`
- [x] Conserver uniquement les `SUMMARY_KEEP_TURNS` derniers échanges après le résumé
- [x] Au prochain dépassement de seuil, générer un résumé 2 à partir du **dialogue brut** uniquement (jamais du résumé 1)
- [x] Archiver le résumé 1 (le conserver en base pour le RAG futur), remplacer par le résumé 2 dans le payload actif

### 2.5 Validation Phase 2

- [x] Tester un déclenchement artificiel (baisser le seuil temporairement)
- [x] Vérifier que le résumé couvre bien le dialogue et pas les métadonnées
- [x] Vérifier que le modèle s'appuie sur le résumé dans sa réponse
- [x] Vérifier que les 5 derniers échanges sont bien préservés après résumé

---

## Phase 3 — Vector Store + RAG basique

### 3.1 Setup du vector store — PostgreSQL + pgvector (mutualisé docker-stacks)

- [x] Choisir le backend : **PostgreSQL + pgvector** (DB mutualisée pour tout le stack)
- [x] Déployer le container `pgvector/pgvector:pg17` + Adminer sur le stack `database/`
- [x] Tuile Adminer ajoutée dans le tableau de bord Tof (Homarr, port 8181)
- [x] Extension `vector` activée dans la DB `frida` (pgvector 0.8.2)
- [x] Créer un module `memory_store.py` avec les opérations CRUD de base
- [x] Ajouter `FRIDA_MEMORY_DB_DSN` dans `config.py` (connexion PostgreSQL)
- [x] Ajouter `psycopg[binary]` aux dépendances Python (`requirements.txt`)

### 3.2 Schéma de la base

- [x] Table `traces` :
  - `id` UUID, `conversation_id`, `role` (user/assistant), `content`, `timestamp`
  - `embedding` vector(384), `summary_id` (optionnel, FK vers résumé associé)
- [x] Table `summaries` :
  - `id` UUID, `conversation_id`, `start_ts`, `end_ts`, `content`, `embedding`
- [x] Table `identities` *(préparation Phase 5)* : structure vide pour l'instant

### 3.3 Embedding des messages

- [x] Choisir le modèle d'embedding : service OVH externe (intfloat/multilingual-e5-small, dim=384)
- [x] Créer une fonction `embed(text, mode) -> list[float]` dans `memory_store.py`
- [x] Appeler `embed()` à chaque `save_conversation()` pour les nouveaux messages
- [x] Gérer les erreurs d'embedding sans bloquer la sauvegarde principale

### 3.4 Retrieval

- [x] Créer une fonction `retrieve(query, top_k=5) -> list[dict]` dans `memory_store.py`
  - [x] Embed la query (préfixe "query: " pour E5)
  - [x] Recherche cosine similarity via pgvector (opérateur <=>)
  - [x] Retourner les `top_k` traces avec leur `timestamp` et `summary_id`
- [x] Ajouter `MEMORY_TOP_K` dans `config.py` (défaut : 5)

### 3.5 Injection dans le payload

- [x] Dans `api_chat()`, appeler `retrieve(user_msg)` avant la construction du prompt
- [x] Injecter les traces retournées en slot `[Mémoire — souvenirs pertinents]` avec leur Delta-T
- [x] Positionner l'injection : après le résumé actif, avant les messages récents

### 3.6 Validation Phase 3

- [x] Vérifier que les embeddings sont bien créés et stockés
- [x] Tester un recall sur une conversation passée (score > 0.8 sur requête sémantique)
- [x] Vérifier que le modèle utilise les traces mémoire dans ses réponses
- [ ] Monitorer le surcoût en tokens et en latence

---

## Phase 6 — Contexte résumé des traces mémoire

### 6.1 Résumé parent d'une trace

- [x] Dans `memory_store.py`, créer une fonction `get_summary_for_trace(trace) -> dict | None`
  - [x] Si la trace a un `summary_id`, récupérer le résumé correspondant en DB
  - [x] Sinon, chercher le résumé dont `start_ts <= trace.timestamp <= end_ts` pour la même `conversation_id`
  - [x] Retourner `None` si aucun résumé ne couvre la trace

### 6.2 Enrichissement après arbitrage

- [x] Dans `server.py`, après `arbiter.filter_traces()`, appeler `enrich_traces_with_summaries(traces)`
  - [x] Pour chaque trace retenue, appeler `get_summary_for_trace()` (avec cache)
  - [x] Dédupliquer les résumés (plusieurs traces peuvent partager le même résumé)
  - [x] Retourner les traces enrichies avec un champ `parent_summary` (dict ou None)

### 6.3 Injection dans le payload

- [x] Dans `conv_store.build_prompt_messages()`, modifier le slot mémoire :
  - [x] Si des traces ont un `parent_summary`, injecter d'abord le bloc résumé contextuel :
    `[Contexte du souvenir — résumé du X au Y] contenu du résumé`
  - [x] Puis injecter les traces comme aujourd'hui
  - [x] Si aucune trace n'a de résumé parent, le slot contexte reste absent (pas de bruit)

### 6.4 Règle dans le system prompt

- [x] Ajouter une règle expliquant au modèle que le bloc `[Contexte du souvenir]` fournit
  le contexte de la période dans laquelle s'inscrit le souvenir retenu

### 6.5 Validation Phase 6

- [x] Vérifier qu'une trace couverte par un résumé injecte bien le résumé parent dans le prompt
- [x] Vérifier que deux traces du même résumé n'injectent le résumé qu'une seule fois
- [x] Vérifier que l'absence de traces ne génère pas de slot vide parasite
- [ ] Vérifier que le modèle utilise le contexte résumé dans ses réponses (test en conditions réelles)

---

## Phase 4 — Arbitre LLM

### 4.1 Prompt de l'arbitre

- [x] Créer le prompt arbitre dans `data/prompts/arbiter.txt`
  - [x] Critères : pertinence sémantique ET contextuelle (herméneutique)
  - [x] Input : proposition mémoire (top-k) + 5 derniers tours de conversation
  - [x] Output : liste des IDs de traces à retenir (format JSON strict)
- [x] Ajouter `ARBITER_MODEL` dans `config.py` (modèle : openai/gpt-5.4-mini)

### 4.2 Intégration dans le pipeline

- [x] Remplacer l'injection directe du top-k par un appel à `arbiter.filter_traces()`
- [x] Logger les décisions de l'arbitre (quelles traces retenues / rejetées)
- [x] Gérer le cas où l'arbitre retourne une liste vide (pas d'injection mémoire)
- [x] Timeout strict sur l'appel arbitre pour ne pas bloquer la réponse principale

### 4.3 Validation Phase 4

- [x] Vérifier que l'arbitre réduit bien le bruit (3 candidates → 1 retenue sur test café/Blade Runner)
- [ ] Comparer qualité des réponses avec/sans arbitre sur des questions test en conditions réelles
- [ ] Mesurer le surcoût en latence de l'appel arbitre

---

## Phase 5 — Identités évolutives

### 5.1 Structure des entrées identitaires

- [x] Définir le schéma d'une entrée identitaire :
  ```json
  {
    "id": "uuid",
    "subject": "llm|user",
    "content": "texte court décrivant un trait ou fait",
    "weight": 1.0,
    "created_ts": "ISO",
    "last_seen_ts": "ISO",
    "source_trace_id": "uuid"
  }
  ```
- [x] Créer la table `identities` dans PostgreSQL (créée en Phase 3 dans `init_db()`)
- [x] Créer les fonctions CRUD dans `memory_store.py`

### 5.2 Mise à jour automatique

- [x] Étendre l'arbitre pour détecter les nouvelles informations identitaires dans la conversation
  - [x] LLM identity : le modèle a-t-il exprimé une opinion, un positionnement, une valeur ?
  - [x] User identity : l'utilisateur a-t-il révélé une préférence, un fait sur lui-même ?
- [x] Si oui, créer une nouvelle entrée avec `weight = 1.0`
- [x] Implémenter la décroissance de poids : `weight *= decay_factor` à chaque session sans réactivation
- [x] Ajouter `IDENTITY_DECAY_FACTOR` dans `config.py` (défaut : 0.95)
- [x] Implémenter la réactivation : si une entrée est rappelée et confirmée, `weight = min(weight * 1.1, 2.0)`

### 5.3 Injection dans le payload

- [x] Remplacer les fichiers statiques `llm_identity.txt` / `user_identity.txt` par une construction dynamique
- [x] Sélectionner les entrées identitaires par poids décroissant (top-N)
- [x] Construire le bloc identité LLM et identité user pour le system prompt
- [x] Ajouter `IDENTITY_TOP_N` dans `config.py` (défaut : 10 entrées par identité)
- [x] Conserver les fichiers statiques comme **seed permanent** (toujours injectés, les entrées DB sont additives)

### 5.4 Validation Phase 5

- [x] Vérifier que les nouvelles entrées sont créées après une conversation révélatrice
- [x] Vérifier que la décroissance fonctionne sur les entrées inactives (0.95 validé)
- [x] Vérifier la cohérence de l'identité construite dynamiquement vs identité figée initiale

---

## Transversal — À faire à chaque phase

- [x] Mettre à jour `requirements.txt` avec les nouvelles dépendances
- [x] Documenter les nouveaux modules dans ce fichier
- [x] Ne pas modifier la logique de `api_chat()` au-delà des points d'injection définis
- [x] Tout nouveau paramètre va dans `config.py` avec une valeur par défaut sensée
- [x] Tester le rebuild Docker après chaque phase avant de passer à la suivante

---

## Architecture des modules

```
app/
├── server.py                  — Point d'entrée Flask, pipeline principal (chat, stream, admin)
├── config.py                  — Toutes les variables de configuration (env + défauts)
│
├── core/
│   ├── conv_store.py          — CRUD conversations JSON, build_prompt_messages(), delta-T
│   ├── llm_client.py          — Appel OpenRouter (sync + stream), headers, sanitize encoding
│   ├── token_counter.py       — Compteur de tokens heuristique (stdlib, sans dépendance)
│   └── token_utils.py         — Wrapper count_tokens() appelé depuis conv_store et server
│
├── memory/
│   ├── summarizer.py          — Détection seuil, génération résumé LLM, maybe_summarize()
│   ├── memory_store.py        — PostgreSQL+pgvector : init_db, embed, save_new_traces, save_summary,
│   │                            update_traces_summary_id, retrieve, get_summary_for_trace,
│   │                            enrich_traces_with_summaries, get/add/decay/reactivate identities
│   └── arbiter.py             — filter_traces() (pertinence RAG), extract_identities() (Phase 5)
│
├── identity/
│   └── identity.py            — build_identity_block() -> (str, list[id]) : fichiers statiques + entrées DB (top-15)
│
├── budget/
│   ├── budget_manager.py      — Suivi des dépenses tokens par conversation
│   ├── budget_limits.py       — Définition des limites par modèle
│   └── budget_index.py        — Index global des budgets
│
├── admin/
│   ├── admin_logs.py          — Lecture et filtrage des logs applicatifs
│   └── admin_actions.py       — Actions d'administration (reset, purge, etc.)
│
└── tools/
    ├── web_search.py          — Recherche SearXNG + crawl Crawl4AI
    └── weather.py             — Météo Open-Meteo
```

### `requirements.txt` (dépendances tierces)

| Package | Usage |
|---------|-------|
| `Flask==3.0.3` | Serveur web |
| `requests==2.32.3` | Appels HTTP (OpenRouter, embedding, tools) |
| `python-dotenv==1.0.1` | Chargement `.env` |
| `psycopg[binary]>=3.1.0` | PostgreSQL + pgvector (Phase 3+) |
