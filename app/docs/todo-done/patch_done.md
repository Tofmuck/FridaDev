# patch_done - Inventaire des modifications (hors TODO)

| Timestamp (UTC) | Scope | Modifications realisees |
|---|---|---|
| 2026-03-22T20:45:12Z | OpenRouter config | Ajout de l attribution par composant dans app/config.py et app/config.example.py: OPENROUTER_REFERER, OPENROUTER_APP_NAME (base Frida-Mini), OPENROUTER_TITLE_LLM, OPENROUTER_TITLE_ARBITER, OPENROUTER_TITLE_RESUMER, avec fallback retrocompatible sur OPENROUTER_SITE_URL. |
| 2026-03-22T20:45:12Z | Client LLM | Mise a jour de app/core/llm_client.py: or_headers(caller=...) avec mapping explicite llm, arbiter, resumer vers les X-Title dedies. |
| 2026-03-22T20:45:12Z | Points d appel | Routage des appels OpenRouter vers le bon caller: app/server.py -> llm, app/memory/arbiter.py -> arbiter, app/memory/summarizer.py -> resumer, app/tools/web_search.py -> llm. |
| 2026-03-22T20:45:12Z | Exemples env + runtime | Mise a jour de app/.env.example avec variables OpenRouter nommees Frida-Mini/*, et alignement du runtime local app/.env (non versionne) pour affichage cote OpenRouter en Frida-Mini/*. |

## Resultat attendu
Les logs OpenRouter distinguent desormais les appels sous:
- Frida-Mini/LLM
- Frida-Mini/Arbiter
- Frida-Mini/Resumer
