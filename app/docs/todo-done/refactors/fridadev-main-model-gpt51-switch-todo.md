# TODO - bascule du modele principal vers GPT-5.1

Statut: chantier actif.

Branche: `feature/main-model-gpt51`.

Date: 2026-05-20.

## Objectif

Basculer le modele principal quotidien de FridaDev vers:

```text
openai/gpt-5.1
```

La bascule vise le flux `FridaDev / Main Chat` seulement. Les petits agents restent sur leurs slots existants.

## Pourquoi

Claude Sonnet 4.6 donne de bons resultats, y compris sur les images actives testees en reel par Tof, mais son cout devient trop eleve en gros contexte.

Un tour observe autour de `42641` tokens d'entree et `330` tokens de sortie coutait environ `0.13` USD sur le main chat Claude. GPT-5.1 est nettement moins cher sur le meme profil de tour, tout en annoncant cote OpenRouter une compatibilite `text+image+file->text` et une fenetre de contexte `400000`.

## Decision operateur

- Pas de grande matrice de benchmark conversationnel avant la bascule.
- Tof testera la qualite de voix, de presence et de longueur en usage reel.
- Les tests de ce chantier sont techniques: runtime settings, streaming, documents actifs, images actives et non-contamination.
- La bascule est reversible par runtime settings.

## Contraintes

- Garder les parametres actuels du `main_model` autant que compatible:
  - `base_url` inchange;
  - `api_key` inchange et jamais affiche;
  - `temperature=0.7`;
  - `top_p=1.0`;
  - `response_max_tokens=8192`;
  - `referer_llm` et `title_llm` inchanges.
- Ne pas toucher aux slots:
  - `memory_arbiter_model`;
  - `summary_model`;
  - `identity_extractor_model`;
  - `identity_periodic_model`;
  - `web_reformulation_model`;
  - `stimmung_agent_model`;
  - `validation_agent_model`.
- Ne pas toucher a l'outil lateral de generation d'images.
- Conserver le meme token/projet OpenRouter.
- Conserver l'attribution OpenRouter `FridaDev / Main Chat`.

## Travaux

### 1. Integrer les images actives dans `main`

- [x] Fast-forward `feature/active-image-documents` vers `main`.
- [x] Pousser `main`.
- [x] Repartir de `main` propre.

### 2. Brancher le chantier GPT-5.1

- [x] Creer `feature/main-model-gpt51` depuis `main`.
- [x] Pousser la branche.

### 3. Compatibilite images actives

- [x] Ajouter `openai/gpt-5.1` a l'allowlist V0 des modeles principaux compatibles image.
- [x] Garder `anthropic/claude-sonnet-4.6` compatible pour rollback.
- [x] Prouver que GPT-5.1 injecte une image active sous plafond provider.
- [x] Prouver que les modeles non compatibles restent exclus avec `image_model_unsupported`.
- [x] Prouver que le payload reste `text` puis `image_url`.
- [x] Prouver que `imageUrl` n'apparait pas.
- [x] Prouver que le base64 reste limite a `image_url.url` dans le payload provider.

### 4. Bascule runtime settings

- [x] Verifier le snapshot non secret de `main_model`.
- [x] Modifier uniquement `main_model.model` vers `openai/gpt-5.1`.
- [x] Verifier que `base_url`, `api_key` present, `temperature`, `top_p`, `response_max_tokens`, `referer_llm` et `title_llm` restent inchanges.
- [x] Verifier que les petits agents ne changent pas.

### 5. Smoke live

- [x] Rebuild/restart uniquement `fridadev`.
- [x] Verifier `/admin` via Authelia.
- [x] Verifier que `main_model.model` live vaut `openai/gpt-5.1`.
- [x] Verifier que l'allowlist images actives contient `openai/gpt-5.1`.
- [x] Verifier qu'aucun secret n'est affiche.

Execution OVH du 2026-05-20:

- `main_model.model` live: `openai/gpt-5.1`;
- `base_url`, `api_key` present, `temperature=0.7`, `top_p=1.0`, `response_max_tokens=8192`, `referer_llm` et `title_llm` conserves;
- petits agents inchanges;
- `/admin` repond `302` vers Authelia;
- conteneur `platform-fridadev` healthy apres rebuild.

## Valeur runtime cible

Changement unique attendu:

```text
main_model.model = openai/gpt-5.1
```

Rollback:

```text
main_model.model = anthropic/claude-sonnet-4.6
```

Le rollback passe par la meme section runtime settings `main_model`; aucun rebuild n'est attendu si la modification passe par l'API/admin runtime settings.

## Preuves attendues

Commandes techniques:

```bash
git status --short
git diff --check
git diff --cached --check

python3 -m py_compile \
  app/core/active_document_prompt_lane.py \
  app/core/llm_client.py \
  app/core/chat_service.py \
  app/core/chat_llm_flow.py \
  app/admin/runtime_settings.py \
  app/admin/runtime_settings_spec.py \
  app/admin/runtime_settings_validation.py

python3 -m unittest app.tests.unit.core.test_active_document_prompt_lane
python3 -m unittest app.tests.test_server_chat_active_image_documents_contract
python3 -m unittest app.tests.test_server_admin_settings_read_contract
python3 -m unittest app.tests.test_server_admin_settings_patch_contract
python3 -m unittest app.tests.test_server_admin_settings_validate_contract
```

Si l'hote ne possede pas les dependances, relancer dans `platform-fridadev`.

Smoke OVH:

```bash
cd /opt/platform/fridadev-app
docker compose up -d --build fridadev
docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'
```

## Hors scope

- Pas de benchmark conversationnel lourd.
- Pas de changement de prompt.
- Pas de changement des petits agents.
- Pas de changement de token OpenRouter.
- Pas de changement de l'outil lateral de generation d'images.
- Pas de migration DB.
- Pas de test image privee dans ce chantier.

## Cloture

Cloture du 2026-05-20:

- Bascule runtime effectuee: `main_model.model = openai/gpt-5.1`.
- Parametres conserves autant que possible: `temperature=0.7`, `top_p=1.0`, `response_max_tokens=8192`, base URL, token et projet OpenRouter inchanges.
- `openai/gpt-5.1` ajoute a l'allowlist des images actives V0.
- L'audit tokens a conclu a une difference de tokenizer/reporting provider, sans nouveau resume conversationnel et sans reduction reelle de contexte.
- Les investigations de cout sont arretees.
- Retour arriere possible via runtime settings vers `anthropic/claude-sonnet-4.6` si besoin, hors scope maintenant.
