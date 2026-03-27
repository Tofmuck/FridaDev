# Kiki-mini — rendre le LLM plus intelligent (ordre de nécessité)

## Liste d'actions (ordre de nécessité)
- [x] Choisir un modèle plus capable et l'utiliser partout (même modèle, même source).
- [x] Simplifier le prompt système en règles courtes et claires.
- [ ] Ajouter un résumé court du fil et l'envoyer à chaque message.
- [ ] Ajouter un petit profil local d'Olive (prénom, âge, goûts) et l'envoyer à chaque message.
- [x] Baisser la température par défaut pour plus de cohérence (ex. 0.4).
- [ ] Nettoyer l'historique avant envoi (messages vides, doublons, rôles invalides).
- [ ] Ajouter 1 ou 2 exemples courts dans le prompt pour cadrer le style.
- [ ] Limiter la longueur envoyée par message pour éviter le bruit.
- [ ] Prévoir un champ "sources" vide dans les échanges (préparation à la recherche).
- [ ] Ranger des documents simples dans un dossier dédié (ex. `data/docs`).
- [ ] Noter les règles pour la future recherche dans les documents (RAG) : formats, taille, mise à jour.


---

## Politique de stockage et réinjection des conversations (serveur)

### Objectif
- [x] Stocker toutes les conversations côté serveur dans `/home/tof/apps/kiki-mini/conv/`
- [x] Une conversation = un fichier JSON
- [x] Réinjecter l’historique pertinent dans chaque requête LLM
- [x] Budget maximal : **25 000 tokens** (fenêtre glissante)

### Structure de stockage
- [x] Créer le répertoire `/home/tof/apps/kiki-mini/conv/` (permissions user `tof`)
- [x] Définir un `conversation_id` stable (UUID v4 recommandé)
- [x] Un fichier par conversation : `{conversation_id}.json`
- [x] Schéma JSON minimal :
  - [x] `id`
  - [x] `created_at` (timestamp conversation)
  - [x] `updated_at`
  - [x] `messages[]` = `{role, content, timestamp}`

### Cycle de vie d’une conversation
- [x] Nouvelle conversation :
  - [x] Générer `conversation_id`
  - [x] Créer le fichier JSON avec le message `system`
- [x] Message utilisateur :
  - [x] Charger le JSON correspondant
  - [x] Ajouter le message `user`
  - [x] Calculer la fenêtre de messages à réinjecter (cf. tokens)
  - [x] Appeler le LLM
  - [x] Ajouter la réponse `assistant`
  - [x] Sauvegarder le JSON (écriture atomique)
  - [x] Suppression d’une conversation :
  - [x] Action UI : suppression explicite par l’utilisateur
  - [x] Back-end : suppression du fichier `{conversation_id}.json`
  - [x] Vérifier l’inexistence du fichier après suppression

### Fenêtre glissante & tokens
- [x] Définir `MAX_TOKENS = 25000`
- [x] Toujours inclure le message `system`
- [x] Ajouter les messages les plus récents en remontant le fil
- [x] Stopper l’ajout avant dépassement du budget tokens
- [x] Renvoyer les messages dans l’ordre chronologique

### Comptage des tokens
- [x] Intégrer le **tokencounter Frida** dès qu’il est fourni
- [x] API attendue : `count_tokens(messages, model)`
- [ ] Fallback temporaire si absent (approximation simple, clairement marquée)
- [x] Logguer : `conversation_id`, tokens envoyés, nombre de messages inclus

### Robustesse & sécurité
- [x] Écriture atomique des fichiers (tmp + replace)
- [x] Protection contre JSON corrompu (backup + recréation)
- [x] Pas de données personnelles hors contenu conversationnel

### Contraintes UI — timestamps
- [x] Chaque conversation possède un timestamp de création (serveur)
- [x] Le timestamp n’est jamais injecté dans le prompt LLM
- [x] Le modèle ne doit jamais renvoyer ou commenter les timestamps
- [x] Affichage UI : timestamp discret sous chaque carte de conversation
- [x] Format lisible humain (ex. `2025-12-20 14:32`)

### Tests manuels minimaux
- [ ] Création d’une conversation → fichier JSON créé
- [ ] Reprise après redémarrage serveur → continuité OK
- [ ] Conversation longue → respect du plafond 25k tokens
- [ ] Vérification que les messages anciens sont correctement exclus


## Budget mensuel via OpenRouter (usage réel — 6 $ / mois — point)

### Objectif
- [x] Mettre un **budget mensuel unique** pour Olive : **6,00 $/mois** (aucun budget journalier, aucun carry-over)
- [x] Utiliser les **tokens réels** renvoyés par OpenRouter (`usage.*`) pour calculer le **coût réel**
- [x] Afficher dans l’UI un **budget restant / total** en dollars (discret, non infantilisant)
- [x] Bloquer côté serveur quand le budget mensuel est atteint (règle simple, lisible)

### Paramètres (config)
- [x] `MONTHLY_USD_LIMIT = 6.00`
- [x] Tarifs modèle (USD) :
  - [x] `PRICE_INPUT_PER_M = 1.25`   # $ / 1 000 000 tokens input
  - [x] `PRICE_OUTPUT_PER_M = 10.0`  # $ / 1 000 000 tokens output
- [x] Définir le **mois courant** à partir du timestamp serveur (ex. `YYYY-MM`)

### Collecte des tokens réels (OpenRouter)
- [x] Sur chaque réponse modèle, lire :
  - [x] `usage.prompt_tokens`
  - [x] `usage.completion_tokens`
  - [x] `usage.total_tokens`
- [x] Associer le `model` effectivement utilisé à la réponse (ex. `openai/gpt-5.1`)
- [x] Stocker ces infos **hors-prompt** (jamais injectées au LLM) dans le JSON conversation, par message assistant :
  - [x] `meta.usage.prompt_tokens`
  - [x] `meta.usage.completion_tokens`
  - [x] `meta.usage.total_tokens`
  - [x] `meta.usage.model`
  - [x] `meta.usage.timestamp` (serveur)
- [x] Logs (sans contenu sensible) : `conversation_id`, `model`, `total_tokens`, `cost_usd`, `month_key`

### Conversion tokens → coût (USD)
- [x] Calculer le coût par réponse :
  - [x] `cost_usd_in  = (prompt_tokens     / 1_000_000) * PRICE_INPUT_PER_M`
  - [x] `cost_usd_out = (completion_tokens / 1_000_000) * PRICE_OUTPUT_PER_M`
  - [x] `cost_usd = cost_usd_in + cost_usd_out`
- [x] Stocker le coût dans le message assistant :
  - [x] `meta.usage.cost_usd`

### Agrégation mensuelle (serveur)
- [x] Agréger la consommation **par mois** (clé `YYYY-MM` basée sur timestamps serveur)
- [x] Stocker un index agrégé (éviter de rescanner toutes les conversations à chaque requête), ex :
  - [x] `/home/tof/apps/kiki-mini/conv/budget-index.json`
  - [x] structure : `{ "YYYY-MM": { "cost_usd": ..., "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ... } }`
- [x] Mettre à jour l’agrégat à chaque réponse modèle (écriture atomique)

### Enforcement (blocage côté serveur)
- [x] Avant chaque appel au modèle, calculer `monthly_cost_usd` (à partir de l’index agrégé)
- [x] Si `monthly_cost_usd >= MONTHLY_USD_LIMIT` :
  - [x] Refuser l’appel modèle
  - [x] Retourner un message UI clair : **budget mensuel épuisé**
  - [x] Logger l’évènement : mois, limite, coût atteint
- [x] Ne jamais exposer tokens, coûts détaillés, ni timestamps au modèle

### UI (discret)
- [x] Afficher très discrètement : **Budget du mois : restant / 6,00 $**
- [x] Pas d’affichage journalier
- [ ] Option debug (désactivée par défaut) : afficher tokens + coût par message

### Tests manuels minimaux (plus tard)
- [ ] Vérifier que `usage.*` est bien récupéré et stocké sur chaque réponse
- [ ] Vérifier que `cost_usd` est correct (input + output)
- [ ] Vérifier que l’agrégat mensuel est mis à jour et persistant
- [ ] Vérifier que le blocage intervient exactement à 6,00 $


## Admin / Logs techniques (LAN)

### Accès & affichage
- [x] Page `/admin` accessible sur le LAN
- [x] Afficher les logs techniques sans jamais montrer les messages
- [x] Rafraîchissement automatique de la liste des logs

### API & stockage
- [x] Endpoint logs : `/api/admin/logs`
- [x] Stockage JSONL : `/home/tof/apps/kiki-mini/logs/admin.log.jsonl`
- [x] Redaction stricte des contenus sensibles (messages, prompts)

### Budget (admin)
- [x] Afficher en haut : tokens utilisés / restants
- [x] Afficher en haut : dollars utilisés / restants
- [x] Bouton pour ajouter 1 $ au budget mensuel

### Service
- [x] Bouton pour redémarrer `frida-mini.service`

