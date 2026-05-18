# Arbiter tournament - 2026-05-18-arbiter-final-tournament

## Round 1

| Model | Weighted score | Hard score | FP | FN | Provider errors | Cost est. | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mistralai/mistral-small-2603` | 95.2 | 94.0 | 1 | 2 | 0% | $0.007131 | 2033 ms |
| `google/gemini-3.1-flash-lite` | 93.5 | 92.0 | 4 | 0 | 0% | $0.022613 | 1362 ms |
| `openai/gpt-5.4-mini` | 93.5 | 92.0 | 4 | 0 | 0% | $0.048800 | 1836 ms |
| `qwen/qwen3.6-flash` | 0.0 | 0.0 | 0 | 36 | 100% | n/a | 308 ms |

Finalists: `mistralai/mistral-small-2603`, `google/gemini-3.1-flash-lite`

## Final

| Model | Weighted score | Hard score | FP | FN | Provider errors | Cost est. | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mistralai/mistral-small-2603` | 98.9 | 98.7 | 1 | 0 | 0% | $0.007838 | 1037 ms |
| `google/gemini-3.1-flash-lite` | 95.7 | 94.8 | 4 | 0 | 0% | $0.033561 | 1305 ms |

## Recommendation

- Pure relevance winner: `mistralai/mistral-small-2603`
- Relevance/cost/latency winner: `mistralai/mistral-small-2603`
- Baseline comparison: Baseline openai/gpt-5.4-mini did not reach the final.
- Recommendation: Basculer vers mistralai/mistral-small-2603 devient defendable au prochain lot de decouplage.

## Divergences

- Showing 20 of 43 divergent cases.
- `round1` / `r1_real_01_admin_authelia` expected `['r1_real_01_admin_authelia_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_01_admin_authelia_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_01_admin_authelia_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_01_admin_authelia_keep']`
- `round1` / `r1_real_02_delta_t_temporel` expected `['r1_real_02_delta_t_temporel_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_02_delta_t_temporel_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_02_delta_t_temporel_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_02_delta_t_temporel_keep']`
- `round1` / `r1_real_03_resume_date_locale` expected `['r1_real_03_resume_date_locale_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_03_resume_date_locale_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_03_resume_date_locale_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_03_resume_date_locale_keep']`
- `round1` / `r1_real_04_lane_web_locale` expected `['r1_real_04_lane_web_locale_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_04_lane_web_locale_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_04_lane_web_locale_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_04_lane_web_locale_keep']`
- `round1` / `r1_real_05_validation_agent` expected `['r1_real_05_validation_agent_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_05_validation_agent_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_05_validation_agent_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `[]`
- `round1` / `r1_real_06_arbitre_memoire_temporel` expected `['r1_real_06_arbitre_memoire_temporel_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_06_arbitre_memoire_temporel_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_06_arbitre_memoire_temporel_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_06_arbitre_memoire_temporel_keep']`
- `round1` / `r1_real_07_identity_temporelle_faible` expected `['r1_real_07_identity_temporelle_faible_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_07_identity_temporelle_faible_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_07_identity_temporelle_faible_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_07_identity_temporelle_faible_keep']`
- `round1` / `r1_real_08_stimmung_sans_gaps` expected `['r1_real_08_stimmung_sans_gaps_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_08_stimmung_sans_gaps_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_08_stimmung_sans_gaps_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_08_stimmung_sans_gaps_keep']`
- `round1` / `r1_real_09_timestamp_invalide` expected `['r1_real_09_timestamp_invalide_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_09_timestamp_invalide_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_09_timestamp_invalide_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_09_timestamp_invalide_keep']`
- `round1` / `r1_real_10_timezone_invalide` expected `['r1_real_10_timezone_invalide_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_10_timezone_invalide_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_10_timezone_invalide_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_10_timezone_invalide_keep']`
- `round1` / `r1_real_11_contrat_prompt_temporel` expected `['r1_real_11_contrat_prompt_temporel_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_11_contrat_prompt_temporel_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_11_contrat_prompt_temporel_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_11_contrat_prompt_temporel_keep']`
- `round1` / `r1_real_12_documents_actifs` expected `['r1_real_12_documents_actifs_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_12_documents_actifs_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_12_documents_actifs_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_12_documents_actifs_keep']`
- `round1` / `r1_real_13_ocr_bornee` expected `['r1_real_13_ocr_bornee_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_13_ocr_bornee_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_13_ocr_bornee_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_13_ocr_bornee_keep']`
- `round1` / `r1_real_14_frontiere_biblio` expected `['r1_real_14_frontiere_biblio_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_14_frontiere_biblio_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_14_frontiere_biblio_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_14_frontiere_biblio_keep']`
- `round1` / `r1_real_15_runtime_settings_effectifs` expected `['r1_real_15_runtime_settings_effectifs_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_15_runtime_settings_effectifs_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_15_runtime_settings_effectifs_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_15_runtime_settings_effectifs_keep']`
- `round1` / `r1_real_16_token_openrouter_partage` expected `['r1_real_16_token_openrouter_partage_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_16_token_openrouter_partage_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_16_token_openrouter_partage_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_16_token_openrouter_partage_keep']`
- `round1` / `r1_real_17_catalogue_modeles` expected `['r1_real_17_catalogue_modeles_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_17_catalogue_modeles_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_17_catalogue_modeles_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_17_catalogue_modeles_keep']`
- `round1` / `r1_real_18_atelier_benchmark` expected `['r1_real_18_atelier_benchmark_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_18_atelier_benchmark_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_18_atelier_benchmark_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_18_atelier_benchmark_keep']`
- `round1` / `r1_real_19_prompt_arbitre` expected `['r1_real_19_prompt_arbitre_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_19_prompt_arbitre_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_19_prompt_arbitre_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_19_prompt_arbitre_keep']`
- `round1` / `r1_real_20_arbitre_de_reponse` expected `['r1_real_20_arbitre_de_reponse_keep']`: `openai/gpt-5.4-mini` -> `['r1_real_20_arbitre_de_reponse_keep']`, `google/gemini-3.1-flash-lite` -> `['r1_real_20_arbitre_de_reponse_keep']`, `qwen/qwen3.6-flash` -> `[]`, `mistralai/mistral-small-2603` -> `['r1_real_20_arbitre_de_reponse_keep']`

## Limits

- Real cases are anonymized or reformulated from FridaDev work patterns.
- Gold labels are human development labels, not previous arbiter decisions.
- No production model or runtime setting is changed by this tournament.
