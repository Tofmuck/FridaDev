# Token Counter OpenRouter

Statut: chantier clos comme prerequis utile avant la decision finale `full + observability`.

Plan retenu et ferme dans le code:
- `post-call` reel via `usage` provider/OpenRouter
- `pre-call` estimateur honnete pour budgeting/prompt window
- `single shared token` maintenant, `caller` / `X-Title` distincts par composant maintenant

Constat revalide dans le code:
- `app/core/token_counter.py` et `app/core/token_utils.py` restent heuristiques et model-agnostic
- ces estimations pilotent deja du runtime (`server.py`, `chat_service.py`, `conversations_prompt_window.py`, `identity.py`, `summarizer.py`)
- les appels OpenRouter reels capturent maintenant les vrais `usage` / `id` / `model` post-call
- la couche OpenRouter reste aujourd'hui sur un token / une API key partagee; les noms provider par `caller` / `X-Title` sont maintenant normalises par composant, et l'observability locale distingue maintenant les estimations heuristiques `estimated_*` de la verite provider `provider_*`
- les appelants LLM reels couverts sont: LLM principal, reformulation web, arbiter, identity extractor, summarizer, `stimmung_agent`, `validation_agent`

- [x] Capturer sur chaque appel LLM OpenRouter les metadonnees provider post-call utiles (`usage`, `id`/generation id, `model`) et normaliser le couple `caller` / `X-Title` par composant, en gardant pour l'instant un token / une API key partagee pour le LLM principal, la reformulation web, l'arbiter, l'identity extractor si distinct du runtime arbiter, le summarizer, `stimmung_agent` et `validation_agent`.
- [x] Garder un estimateur pre-call pour la fenetre de prompt, les budgets et les garde-fous runtime, mais le requalifier explicitement en `estimated_*` et ne plus le presenter comme un compteur exact.
- [x] Etendre l'observability/logging pour distinguer noir sur blanc `estimated_*` et `provider_*`, et rendre lisibles les noms OpenRouter par `caller` / `X-Title`, sans melanger estimation locale et verite provider.
- [x] Fermer ce chantier avant la decision finale de bascule `full + observability`, car le comptage provider utile a cette bascule est maintenant en place.

Note de cloture:
- les champs provider necessaires a un pricing/cost OpenRouter futur sont deja conserves
- aucun chantier pricing n'est garde ouvert ici
- si le sujet cout/API key split devient utile plus tard, il devra etre rouvert explicitement dans un document distinct
