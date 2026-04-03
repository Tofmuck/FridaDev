# Token Counter OpenRouter TODO

But: fermer le chantier tokens avant la decision finale `full + observability`, avec le plan unique retenu:
- `post-call` reel via `usage` provider/OpenRouter
- `pre-call` estimateur honnete pour budgeting/prompt window
- `single shared token` maintenant, `caller` / `X-Title` distincts par composant maintenant

Constat revalide dans le code:
- `app/core/token_counter.py` et `app/core/token_utils.py` restent heuristiques et model-agnostic
- ces estimations pilotent deja du runtime (`server.py`, `chat_service.py`, `conversations_prompt_window.py`, `identity.py`, `summarizer.py`)
- les appels OpenRouter reels ne capturent pas encore les vrais `usage`
- la couche OpenRouter reste aujourd'hui sur un token / une API key partagee; la lisibilite provider par `caller` / `X-Title` n'est pas encore normalisee pour tous les appelants LLM reels
- les appelants LLM reels a couvrir sont: LLM principal, arbiter, identity extractor, summarizer, `stimmung_agent`, `validation_agent`

- [ ] Capturer sur chaque appel LLM OpenRouter les metadonnees provider post-call utiles (`usage`, `id`/generation id, `model`) et normaliser le couple `caller` / `X-Title` par composant, en gardant pour l'instant un token / une API key partagee pour le LLM principal, l'arbiter, l'identity extractor si distinct du runtime arbiter, le summarizer, `stimmung_agent` et `validation_agent`.
- [ ] Garder un estimateur pre-call pour la fenetre de prompt, les budgets et les garde-fous runtime, mais le requalifier explicitement en `estimated_*` et ne plus le presenter comme un compteur exact.
- [ ] Etendre l'observability/logging pour distinguer noir sur blanc `estimated_*` et `provider_*`, et rendre lisibles les noms OpenRouter par `caller` / `X-Title`, sans melanger estimation locale et verite provider.
- [ ] Preparer la suite cout/pricing OpenRouter en conservant les champs provider necessaires, sans faire du billing detaille un blocage de cette premiere fermeture tokens ni ouvrir tout de suite une separation par token / API key.
- [ ] Fermer ce chantier avant la decision finale de bascule `full + observability`, car sans comptage provider fiable la consommation runtime reste insuffisamment lisible pour un passage full propre.
