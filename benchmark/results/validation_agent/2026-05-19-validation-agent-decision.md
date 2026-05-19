# Validation agent primary decision - 2026-05-19

## Decision

Tof/Codex retiennent `google/gemini-3.1-flash-lite` pour le `validation_agent` primaire.

Le slot runtime cible devient:

- `primary_model=google/gemini-3.1-flash-lite`
- `fallback_model=openai/gpt-5.4-nano`
- `temperature=0.0`
- `top_p=1.0`
- `max_tokens=140`
- `timeout_s=10`

Le fallback reste inchange. Le token et le projet OpenRouter restent partages via `main_model`.

## Campagnes remplacees

Deux campagnes compactes ont servi a la decision:

- `2026-05-19-validation-agent-primary-benchmark`: premier run a `max_tokens=80`.
- `2026-05-19-validation-agent-primary-max140`: relance comparative a `max_tokens=140`.

Les artefacts complets de run ont ete retires apres decision pour ne conserver qu'une preuve compacte: cette note et le JSON compagnon.

## Synthese technique

| Run | Modele | JSON | Schema | Pass | Unsafe answers | Latence moy. | Cout estime | Finish |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| max80 | `openai/gpt-5.4-mini` | 13/13 | 13/13 | 6/13 | 3 | 1283 ms | $0.015897 | stop |
| max80 | `google/gemini-3.1-flash-lite` | 13/13 | 13/13 | 7/13 | 3 | 983 ms | $0.0059045 | stop |
| max80 | `mistralai/mistral-small-2603` | 7/13 | 7/13 | 4/13 | 1 | 1069 ms | $0.00290985 | length/stop |
| max80 | `anthropic/claude-haiku-4.5` | 0/13 | 0/13 | 0/13 | 0 | 1712 ms | $0.0245 | length |
| max140 | `openai/gpt-5.4-mini` | 13/13 | 13/13 | 6/13 | 3 | 1163 ms | $0.0160545 | stop |
| max140 | `google/gemini-3.1-flash-lite` | 13/13 | 13/13 | 7/13 | 3 | 881 ms | $0.005908 | stop |
| max140 | `mistralai/mistral-small-2603` | 11/13 | 11/13 | 6/13 | 1 | 1533 ms | $0.00327263 | length/stop |
| max140 | `anthropic/claude-haiku-4.5` | 0/13 | 0/13 | 0/13 | 0 | 2724 ms | $0.0284 | length |

## Lecture retenue

La relance a `max_tokens=140` prouve que Mistral et Haiku etaient bien genes par le plafond initial, mais elle ne renverse pas le classement.

Gemini reste le meilleur candidat global:

- JSON et schema stables aux deux plafonds.
- Meilleur nombre de cas reussis.
- Pas de tendance supplementaire a la meta ou a la clarification excessive.
- Latence la plus basse du run final.
- Cout nettement inferieur a la baseline OpenAI.

OpenAI reste stable mais ne progresse pas. Mistral recupere une partie de la validite JSON a `140`, mais reste partiellement fragile avec des `finish_reason=length`. Haiku reste hors contrat court.

## Retention

- Sorties brutes modele non conservees.
- Artefacts complets de run retires apres decision.
- Preuve compacte conservee: `2026-05-19-validation-agent-decision.md` et `2026-05-19-validation-agent-decision.json`.
- Aucun secret OpenRouter n'est versionne.
