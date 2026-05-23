# FridaDev - contrat du reasoning du LLM principal

Statut: actif
Date: 2026-05-22
Portee: LLM principal OpenRouter `openai/gpt-5.1`, runtime settings, payload provider, controle chat, observabilite

## Contrat produit

Le niveau de reasoning du LLM principal est un reglage global de runtime settings:

- section: `main_model`;
- champ: `reasoning_effort`;
- valeurs autorisees: `none`, `low`, `medium`, `high`;
- defaut FridaDev: `high`;
- source de verite: runtime settings / DB, avec seed/backfill compatible pour installations existantes.

Le controle visible pres de la zone de chat est un raccourci ergonomique vers ce reglage global. Un changement applique la nouvelle valeur comme defaut global des prochains tours. Les overrides par conversation, session ou tour sont hors scope de ce contrat.

## Sources provider

OpenAI documente pour GPT-5.1 `reasoning.effort` avec `none`, `low`, `medium`, `high`.
OpenRouter accepte l'objet `reasoning` sur Chat Completions et permet `exclude=true` pour ne pas renvoyer les tokens de raisonnement. OpenRouter expose aussi des niveaux generiques plus larges pour d'autres modeles; FridaDev ne les reprend pas pour GPT-5.1.

## Payload envoye

Pour le modele principal compatible GPT-5.1, FridaDev ajoute au payload Chat Completions:

```json
"reasoning": {
  "effort": "high",
  "exclude": true
}
```

La valeur de `effort` suit `main_model.reasoning_effort`. Le champ n'est pas envoye si le modele principal courant n'est pas reconnu comme compatible GPT-5.1.

FridaDev ne definit pas `include_reasoning`.

## Non-exposition du raisonnement interne

Le niveau selectionne peut etre affiche et journalise de facon content-free. Le contenu interne du raisonnement ne doit jamais etre:

- affiche;
- streame;
- persiste;
- exporte;
- injecte dans Memory, Identity, Summary, Biblio/RAG ou documents actifs;
- expose dans les logs, read-models ou observabilite.

Les champs provider `reasoning`, `reasoning_details` ou equivalents, s'ils apparaissent dans des reponses OpenRouter, sont filtres par les chemins de lecture et ignores par le streaming utilisateur. Le streaming visible ne lit que `delta.content`.

Validation live du 2026-05-22: OpenRouter accepte `reasoning.effort=high`, `none` et `medium` avec les `temperature` / `top_p` historiques du LLM principal. Le provider peut toutefois renvoyer une cle `reasoning_details` dans le message pour `high` / `medium` malgre `exclude=true`; FridaDev filtre donc explicitement les champs `reasoning` et `reasoning_details` des payloads de reponse lus par `llm_client.read_openrouter_response_payload()`.

## Observabilite

Les surfaces content-free peuvent exposer:

- `main_llm_reasoning_effort_requested`;
- `main_llm_reasoning_effort_effective`;
- `main_llm_reasoning_policy_kind`;
- `main_llm_reasoning_hidden`;
- `main_llm_reasoning_reason_code`.

Ces champs decrivent le parametre demande/envoye, jamais un contenu de raisonnement.

## Limites

La valeur `high` augmente potentiellement cout et latence. La calibration fine pourra etre ajustee apres observation, mais sans ouvrir de stockage ou affichage du raisonnement interne.
