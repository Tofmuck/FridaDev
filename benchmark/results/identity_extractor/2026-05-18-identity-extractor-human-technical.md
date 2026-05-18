# Benchmark identity extractor - 2026-05-18-identity-extractor-human - technique

- Created UTC: `2026-05-18T19:06:27Z`
- Dry run: `False`
- Prompt: `app/prompts/identity_extractor.txt` (`fd2b5bcf6cab`)
- Fixtures: `benchmark/suites/identity_extractor/fixtures/identity_extractor_human_cases.json` (`b5d6e9e0ccd1`)
- temperature: `0.0`
- top_p: `1.0`
- max_tokens: `700`
- Production runtime changed: `False`

## Synthese technique

| Modele | Provider OK | JSON valide | Schema valide | Entrees | Taille sortie | Latence moyenne | Cout estime | Finish reason(s) | Sorties completes | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| `openai/gpt-5.4-mini` | 100% | 100% | 100% | 13 | 3866 chars | 1318 ms | $0.007422 | stop | `benchmark/results/identity_extractor/2026-05-18-identity-extractor-human__openai__gpt-5.4-mini.md` | 13 extracted entrie(s) |
| `anthropic/claude-haiku-4.5` | 100% | 100% | 100% | 11 | 5188 chars | 1900 ms | $0.012776 | stop | `benchmark/results/identity_extractor/2026-05-18-identity-extractor-human__anthropic__claude-haiku-4.5.md` | 11 extracted entrie(s) |
| `google/gemini-3.1-flash-lite` | 100% | 100% | 100% | 13 | 4942 chars | 1438 ms | $0.003410 | stop | `benchmark/results/identity_extractor/2026-05-18-identity-extractor-human__google__gemini-3.1-flash-lite.md` | 13 extracted entrie(s) |
| `mistralai/mistral-small-2603` | 100% | 100% | 100% | 2 | 977 chars | 632 ms | $0.000635 | stop | `benchmark/results/identity_extractor/2026-05-18-identity-extractor-human__mistralai__mistral-small-2603.md` | 2 extracted entrie(s) |

## Ce que cette campagne mesure

- La capacite de chaque modele a respecter le prompt de production `identity_extractor`.
- La validite JSON, le respect du schema, la latence, le cout et les erreurs provider.
- La matiere complete necessaire a une lecture humaine de discernement identitaire.

## Ce que cette campagne ne prouve pas

- Aucun score automatique ne choisit le modele de production.
- Les dix cas sont courts et diagnostiques; ils ne remplacent pas une validation longue sur trafic reel.
- Aucun slot runtime `identity_extractor_model` n'est cree ou modifie dans ce lot.
