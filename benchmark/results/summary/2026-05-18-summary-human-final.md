# Benchmark summary - 2026-05-18-summary-human-final

- Created UTC: `2026-05-18T16:20:26Z`
- Dry run: `False`
- Prompt: `app/prompts/summary_system.txt` (`c15fc217b6b8`)
- Goal: produire les résumés complets du même matériau réel pour lecture humaine.
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

- Models: `3`
- temperature: `0.3`
- top_p: `1.0`
- max_tokens: `4500`
- timeout_s: `300`

## Sorties à lire

| Modèle | Provider OK | Finish reason | Latence | Prompt tokens | Completion tokens | Coût estimé | Terminaison | Note | Résumé complet |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `openai/gpt-5.4-mini` | True | stop | 12972 ms | 34486 | 1693 | $0.033483 | provider_declares_clean_stop | Sortie brute a lire humainement; aucun score automatique. | `benchmark/results/summary/2026-05-18-summary-human-final__openai__gpt-5.4-mini.md` |
| `anthropic/claude-sonnet-4.6` | True | stop | 67151 ms | 43756 | 2588 | $0.170088 | provider_declares_clean_stop | Sortie brute a lire humainement; aucun score automatique. | `benchmark/results/summary/2026-05-18-summary-human-final__anthropic__claude-sonnet-4.6.md` |
| `qwen/qwen3.5-plus-20260420` | True | stop | 55431 ms | 36238 | 2945 | $0.016172 | provider_declares_clean_stop | Sortie brute a lire humainement; aucun score automatique. | `benchmark/results/summary/2026-05-18-summary-human-final__qwen__qwen3.5-plus-20260420.md` |

## Ce que cette campagne mesure

- La qualité lisible du résumé conversationnel produit à prompt et matériau identiques.
- La capacité du modèle à tenir un gros dialogue réel Frida et à rester utile pour la suite.

## Ce que cette campagne ne prouve pas

- Aucun score automatique ne départage les modèles.
- Aucun changement de modèle de production n'est effectué.
- La décision de découplage du résumé reste ouverte jusqu'à lecture humaine.
