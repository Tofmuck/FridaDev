# Benchmark summary - 2026-05-18-summary-human-final

- Created UTC: `2026-05-18T16:20:26Z`
- Dry run: `False`
- Prompt: `app/prompts/summary_system.txt` (`c15fc217b6b8`)
- Goal: produire les résumés complets du même matériau réel pour lecture humaine, puis conserver seulement une preuve compacte après décision.
- Verdict: décision humaine de Tof: garder `openai/gpt-5.4-mini`.
- Production runtime changed: `False`
- Raw per-model summaries retained: `False` (retirés après lecture humaine et décision)

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

## Métriques conservées

Les sorties brutes par modèle ont été retirées du dépôt après lecture humaine et décision. Les métriques, signatures et hashes restent dans ce rapport et dans le JSON de campagne comme preuve compacte.

| Modèle | Provider OK | Finish reason | Latence | Prompt tokens | Completion tokens | Coût estimé | Terminaison | Note |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | True | stop | 12972 ms | 34486 | 1693 | $0.033483 | provider_declares_clean_stop | Sortie brute retirée après décision; modèle retenu par lecture humaine. |
| `anthropic/claude-sonnet-4.6` | True | stop | 67151 ms | 43756 | 2588 | $0.170088 | provider_declares_clean_stop | Sortie brute retirée après décision; métriques conservées. |
| `qwen/qwen3.5-plus-20260420` | True | stop | 55431 ms | 36238 | 2945 | $0.016172 | provider_declares_clean_stop | Sortie brute retirée après décision; métriques conservées. |

## Ce que cette campagne mesure

- La qualité lisible du résumé conversationnel produit à prompt et matériau identiques.
- La capacité du modèle à tenir un gros dialogue réel Frida et à rester utile pour la suite.

## Ce que cette campagne ne prouve pas

- Aucun score automatique ne départage les modèles.
- Ce rapport ne conserve pas les textes complets des résumés après décision.
- Le changement de production et le découplage runtime ont été traités dans un lot ultérieur dédié.
