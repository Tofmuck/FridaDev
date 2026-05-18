# Benchmark summary - 2026-05-18-summary-human-reading

- Created UTC: `2026-05-18T15:56:30Z`
- Dry run: `False`
- Prompt: `app/prompts/summary_system.txt` (`c15fc217b6b8`)
- Goal: produire six résumés complets du même matériau réel pour lecture humaine.
- Verdict: non attribué automatiquement; décision humaine de Tof requise.
- Production runtime changed: `False`

## Matériau

- Source kind: `live_conversation`
- Conversation id: `a2bebfd3-96d3-4088-b622-6495461f534a`
- Window: `2026-04-04T20:16:49Z` -> `2026-04-21T10:15:09Z`
- Turns: `106`
- Approx tokens: `38993`
- User content chars: `140500`
- User content SHA256: `6994324235593da3bc347e026615cae0fa1a24c775af6bcb1338a48f07551d67`
- Raw material written: `False`

## Paramètres communs

- Models: `6`
- temperature: `0.3`
- top_p: `1.0`
- max_tokens: `2000`
- timeout_s: `240`

## Sorties à lire

| Modèle | Provider OK | Latence | Prompt tokens | Completion tokens | Coût estimé | Note | Résumé complet |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | True | 20680 ms | 34486 | 2000 | $0.034864 | Budget de completion atteint; verifier une possible troncature a la lecture. | `benchmark/results/summary/2026-05-18-summary-human-reading__openai__gpt-5.4-mini.md` |
| `anthropic/claude-sonnet-4.6` | True | 55145 ms | 43756 | 2000 | $0.161268 | Budget de completion atteint; verifier une possible troncature a la lecture. | `benchmark/results/summary/2026-05-18-summary-human-reading__anthropic__claude-sonnet-4.6.md` |
| `mistralai/mistral-medium-3-5` | True | 9103 ms | 35126 | 482 | $0.056304 | Sortie brute a lire humainement; aucun score automatique. | `benchmark/results/summary/2026-05-18-summary-human-reading__mistralai__mistral-medium-3-5.md` |
| `google/gemini-3.1-pro-preview` | True | 42321 ms | 36654 | 1996 | $0.097260 | Budget de completion atteint; verifier une possible troncature a la lecture. | `benchmark/results/summary/2026-05-18-summary-human-reading__google__gemini-3.1-pro-preview.md` |
| `qwen/qwen3.5-plus-20260420` | True | 64061 ms | 36238 | 3415 | $0.017018 | Budget de completion atteint; verifier une possible troncature a la lecture. | `benchmark/results/summary/2026-05-18-summary-human-reading__qwen__qwen3.5-plus-20260420.md` |
| `mistralai/mistral-small-2603` | True | 21125 ms | 35126 | 2000 | $0.006469 | Budget de completion atteint; verifier une possible troncature a la lecture. | `benchmark/results/summary/2026-05-18-summary-human-reading__mistralai__mistral-small-2603.md` |

## Ce que cette campagne mesure

- La qualité lisible du résumé conversationnel produit à prompt et matériau identiques.
- La capacité du modèle à tenir un gros dialogue réel Frida et à rester utile pour la suite.

## Ce que cette campagne ne prouve pas

- Aucun score automatique ne départage les modèles.
- Aucun changement de modèle de production n'est effectué.
- La décision de découplage du résumé reste ouverte jusqu'à lecture humaine.
