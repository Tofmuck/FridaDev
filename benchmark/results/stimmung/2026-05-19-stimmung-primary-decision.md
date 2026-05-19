# Decision stimmung agent primaire - 2026-05-19

## Decision

Le modele primaire du `stimmung_agent` passe a:

`google/gemini-3.1-flash-lite`

Le fallback reste:

`openai/gpt-5.4-nano`

Ce choix ne modifie ni le prompt `app/prompts/stimmung_agent.txt`, ni le
fallback, ni le token/projet OpenRouter partage via `main_model`.

## Campagne de reference

- Rapport final: `benchmark/results/stimmung/2026-05-19-stimmung-primary-final.md`
- Suite: `benchmark/suites/stimmung/`
- Prompt: `app/prompts/stimmung_agent.txt`
- Fixtures finales: `benchmark/suites/stimmung/fixtures/stimmung_primary_final_cases.json`
- temperature: `0.1`
- top_p: `1.0`
- max_tokens: `220`
- timeout_s: `10`
- Fallback benchmarke: non

## Finalistes

| Modele | Pass souple | Avoid hits | Neutre surcode | Latence moyenne | Cout estime | Completion tokens moyens | Finish |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `openai/gpt-5.4-mini` | 7/10 | 1 | 2 | 1152 ms | $0.005552 | 48.5 | stop |
| `mistralai/mistral-small-2603` | 7/10 | 1 | 2 | 769 ms | $0.001013 | 60.0 | stop |
| `google/gemini-3.1-flash-lite` | 7/10 | 0 | 2 | 1113 ms | $0.002313 | 74.9 | stop |

## Raison de decision

La finale courte donne une egalite quantitative a 7/10 entre OpenAI, Mistral et
Gemini. Tof retient `google/gemini-3.1-flash-lite` parce que:

- Gemini est le seul finaliste avec 0 `avoid_hits`;
- il parait moins nerveux que Mistral sur les cas de desaccord, d'heure et de
  tension;
- il est moins cher que `openai/gpt-5.4-mini`;
- Mistral reste interessant, mais semble un peu trop reactif pour un capteur
  affectif amont.

## Retention

Les sorties brutes modele ne sont pas conservees comme preuve durable. Le gros
JSON structure de la finale a ete retire apres decision. Cette paire
`decision.md` / `decision.json` conserve seulement les metriques, raisons de
decision, chemins de provenance et etat de retention.
