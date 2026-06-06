# Biblio librarian agent - OpenRouter GPT-5.2 compatibility validation

Date: 2026-06-02
Classement: `app/docs/states/baselines/`
Roadmap: `app/docs/todo-done/product/frida-biblio-librarian-agent-todo-archive-2026-06-06.md`
Spec: `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
Scope: verification documentaire + runtime de la bascule Biblio agentique
`deepseek/deepseek-v4-pro` -> `openai/gpt-5.2`, sans refonte prompt ni
architecture.

## URLs consultees

- `https://openrouter.ai/docs/guides/features/structured-outputs`
- `https://openrouter.ai/docs/api/reference/overview`
- `https://openrouter.ai/openai/gpt-5.2`
- `https://openrouter.ai/openai/gpt-5.2/api`

## Constats verifies

- `openai/gpt-5.2` est publie par OpenRouter comme modele disponible.
- OpenRouter documente `response_format.type=json_schema` avec
  `json_schema.strict=true` comme chemin normal de structured outputs.
- OpenRouter recommande `provider.require_parameters=true` pour forcer un
  modele qui supporte effectivement les parametres requis.
- La page modele `openai/gpt-5.2` annonce `reasoning`, `response_format`,
  `max_tokens`, `tools` et `tool_choice` comme parametres supportes.
- La page modele ne confirme pas `temperature` / `top_p` sur ce chemin; la
  bascule prudente consiste donc a garder ces valeurs en runtime settings mais
  a les omettre du payload bibliothecaire pour les modeles `openai/gpt-5*`.
- Preuve live OpenRouter reelle du 2026-06-02:
  - `oneOf` est refuse dans `tool_calls.items` pour ce caller;
  - les objets stricts doivent declarer toutes leurs proprietes dans
    `required`;
  - un schema compatible pour `tool_calls` consiste ici a utiliser un
    `call_id` nullable et un objet `params` ferme avec un superset nullable des
    cles Biblio, puis a laisser le validateur metier FridaDev filtrer les
    `null` / vides et revalider l'executabilite par outil.

## Decision de bascule

- Bascule runtime ciblee du slot `biblio_librarian_agent.primary_model` vers
  `openai/gpt-5.2`.
- Conservation du contrat JSON existant:
  - `response_format.type=json_schema`
  - `response_format.json_schema.name=biblio_librarian_agent_v1`
  - `response_format.json_schema.strict=true`
  - `provider.require_parameters=true`
- Conservation du prompt agentique existant.
- Conservation de `reasoning={"effort":"high","exclude":true}`.
- Conservation des budgets et timeouts courants:
  - `max_tokens=16000`
  - `timeout_s=240`
  - `max_tool_calls=5`
  - `max_model_calls=1`
- Ajustement strictement necessaire:
  - omettre `temperature` et `top_p` du payload pour `openai/gpt-5*` sur ce
    caller, afin de rester coherent avec le support parametre annonce par
    OpenRouter sous `require_parameters=true`.
  - remplacer le schema discriminant `oneOf` des `tool_calls` par une forme
    OpenRouter-compatible: `call_id` nullable requis et `params` objet ferme a
    superset nullable des cles permises, normalise localement avant validation
    metier.

## Preuve live ciblee

- artefact vert:
  `app/docs/states/baselines/biblio-smokes/agent-gpt52-live-20260602T121652Z.jsonl`
- resultat content-free:
  - `agent_status=active_ready`
  - `model_effective=openai/gpt-5.2-20251211`
  - `validation_status=validated`
  - `tool_names=["catalog_search"]`
  - `raw_marker_leaks=false`

## Ce qui n'a pas besoin de changer

- prompt systeme bibliothecaire;
- contrat metier `biblio_librarian_agent_v1`;
- transport OpenRouter partage via `main_model`;
- logique de fallback deterministe;
- outils GET-only Biblio.
