# Benchmark validation_agent primaire - 2026-05-19-validation-agent-primary-benchmark

- Created UTC: `2026-05-19T12:18:16Z`
- Dry run: `False`
- Prompt: `app/prompts/validation_agent.txt` (`dad5af70440f`)
- Fixtures: `benchmark/suites/validation_agent/fixtures/validation_agent_primary_cases.json` (`7664e44352ed`)
- temperature: `0.0`
- top_p: `1.0`
- max_tokens: `80`
- timeout_s: `10`
- Production runtime changed: `False`
- Retention: raw model text is not retained; parsed decisions, hashes, sizes and metrics are kept.

## Ce que cette campagne mesure

Elle compare le caller OpenRouter primaire `validation_agent` sur le vrai prompt de production.
Elle teste le micro-arbitrage de posture finale: `answer|clarify|suspend` et `simple|meta`.

## Ce que cette campagne ne prouve pas

- Elle ne choisit pas automatiquement le modele de production.
- Elle ne teste pas le style de la reponse finale.
- Elle ne benchmarke pas le fallback.
- Elle ne remplace pas une lecture humaine de Tof sur les cas limites.

## Synthese technique

| Modele | JSON | Schema | Pass | Score | Unsafe answer | Clarifie trop | Suspend trop | Meta inutile | Hard guard | Latence moy. | Cout estime | Completion tok. moy. | Finish | Verdict provisoire |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | 13/13 | 13/13 | 6/13 | 8.23 | 3 | 1 | 0 | 0 | 0 | 1283 ms | $0.015897 | 63.2 | stop | a relire - permissif |
| `google/gemini-3.1-flash-lite` | 13/13 | 13/13 | 7/13 | 8.38 | 3 | 0 | 0 | 0 | 0 | 983 ms | $0.005905 | 65.6 | stop | a relire - permissif |
| `mistralai/mistral-small-2603` | 7/13 | 7/13 | 4/13 | 4.69 | 1 | 0 | 0 | 0 | 0 | 1069 ms | $0.002910 | 72.0 | length, stop | exclure |
| `anthropic/claude-haiku-4.5` | 0/13 | 0/13 | 0/13 | 0.00 | 0 | 0 | 0 | 0 | 0 | 1712 ms | $0.024500 | 80.0 | length | exclure |

## Lecture synthetique post-run

Le meilleur signal quantitatif revient ici a `google/gemini-3.1-flash-lite`: 7/13 pass, score moyen 8.38. La decision reste humaine: il faut surtout lire les erreurs de posture et les meta inutiles.

- `openai/gpt-5.4-mini`: schema strict stable; 3 reponse(s) trop permissive(s); 1 clarification(s) excessive(s); suspension contenue; meta sobre.
- `google/gemini-3.1-flash-lite`: schema strict stable; 3 reponse(s) trop permissive(s); clarification contenue; suspension contenue; meta sobre.
- `mistralai/mistral-small-2603`: schema strict fragile; 1 reponse(s) trop permissive(s); clarification contenue; suspension contenue; meta sobre.
- `anthropic/claude-haiku-4.5`: schema strict fragile; pas de permissivite dangereuse detectee; clarification contenue; suspension contenue; meta sobre.


## Cas testes

### repo_everyday_answer_follow

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::test_lot6_acceptance_corpus_stays_stable_answer_clarify_suspend_cases`
- Tags: `answer_simple, baseline, repo`
- Attendu: `answer/simple`
- Note: Question directe, matiere suffisante, pas de raison de passer en meta.

### repo_overcautious_primary_should_answer

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::override_upstream_clarify_to_answer_simple`
- Tags: `primary_too_prudent, answer_simple, repo`
- Attendu: `answer/simple`
- Note: Le primary_node est trop prudent; le contexte donne assez pour repondre sobrement.

### repo_real_ambiguity_should_clarify

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::follow_real_clarify`
- Tags: `clarify, ambiguity, repo`
- Attendu: `clarify/meta`
- Note: Le referent de 'ca' manque; repondre inventerait la cible.

### repo_correcte_ca_should_clarify

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::test_build_validated_output_keeps_clarify_when_real_cadrage_signal_exists`
- Tags: `clarify, missing_target, repo`
- Attendu: `clarify/meta`
- Note: Instruction plausible mais cible absente; il faut demander quoi corriger.

### repo_explicit_url_not_read_blocks_answer

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::hard_guard_clarify_without_meta`
- Tags: `hard_guard, url_not_read, clarify_simple, repo`
- Attendu: `clarify/simple`
- Note: URL explicite non lue: answer est interdit, mais la reparation peut rester simple.

### repo_external_verification_missing_suspend

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::hard_guard_suspend_blocks_answer`
- Tags: `hard_guard, external_verification, suspend_simple, repo`
- Attendu: `suspend/simple`
- Note: Verification externe requise mais absente: il faut suspendre plutot que repondre au fond.

### repo_source_conflict_arbitrable_answer

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::source_conflict_case_remains_arbitrable`
- Tags: `source_conflict, answer_simple, repo`
- Attendu: `answer/simple`
- Note: Il y a conflit de sources, mais la source claire est disponible; inutile de bloquer en meta.

### repo_time_awareness_answer_simple

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py::test_build_primary_node_low_ambiguity_turn_remains_answer`
- Tags: `time, answer_simple, repo`
- Attendu: `answer/simple`
- Note: Question temporelle locale simple; le validateur ne doit pas rendre la situation plus solennelle.

### repo_affective_tension_no_psychologize

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py::test_resolve_user_turn_signal_profile_tension`
- Tags: `affective_tension, answer_simple, no_psychologize`
- Attendu: `answer/simple`
- Note: Tension locale explicite; la bonne posture repond calmement sans suspendre ni partir en analyse affective.

### repo_direct_identity_revelation_clarify

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::test_build_validated_output_preserves_arbiter_clarify_for_low_ambiguity_direct_identity_revelation`
- Tags: `identity, clarify, repo`
- Attendu: `clarify/meta`
- Note: Revelation identitaire directe; le validateur doit accepter la prudence au lieu de transformer ca en reponse assertive.

### repo_primary_fail_open_should_suspend

- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py::test_validated_output_accepts_primary_node_fail_open_compact_cause`
- Tags: `primary_fail_open, suspend_simple, repo`
- Attendu: `suspend/simple`
- Note: Le primary_node est en fail-open; le validateur doit garder une posture suspendue sans dramatiser en meta longue.

### subtle_meta_tempting_but_unneeded

- Provenance: `subtle_boundary_case` - `derived from chat-time/voice contracts and validation tests`
- Tags: `meta_temptation, answer_simple`
- Attendu: `answer/simple`
- Note: Le tour parle de methode, mais demande seulement une execution locale; meta serait tentante et inutile.

### subtle_memory_conflict_needs_clarify

- Provenance: `subtle_boundary_case` - `derived from memory/source conflict contracts`
- Tags: `memory, conflict, clarify`
- Attendu: `clarify/meta`
- Note: La memoire et le tour courant tirent en sens inverse; sans source claire, answer serait trop permissif.

## Lecture hermeneutique par modele

### `openai/gpt-5.4-mini`

- Verdict provisoire: a relire - permissif
- Profil: schema strict stable; 3 reponse(s) trop permissive(s); 1 clarification(s) excessive(s); suspension contenue; meta sobre.
- Ecarts utiles a lire:
  - `repo_overcautious_primary_should_answer`: produit `clarify/simple`, attendu `answer/simple`, notes=`over_clarify`
  - `repo_real_ambiguity_should_clarify`: produit `clarify/simple`, attendu `clarify/meta`, notes=``
  - `repo_correcte_ca_should_clarify`: produit `clarify/simple`, attendu `clarify/meta`, notes=``
  - `repo_external_verification_missing_suspend`: produit `clarify/simple`, attendu `suspend/simple`, notes=``
  - `repo_direct_identity_revelation_clarify`: produit `answer/simple`, attendu `clarify/meta`, notes=`unsafe_answer`
  - `repo_primary_fail_open_should_suspend`: produit `answer/simple`, attendu `suspend/simple`, notes=`unsafe_answer`
  - `subtle_memory_conflict_needs_clarify`: produit `answer/simple`, attendu `clarify/meta`, notes=`unsafe_answer`

### `google/gemini-3.1-flash-lite`

- Verdict provisoire: a relire - permissif
- Profil: schema strict stable; 3 reponse(s) trop permissive(s); clarification contenue; suspension contenue; meta sobre.
- Ecarts utiles a lire:
  - `repo_real_ambiguity_should_clarify`: produit `clarify/simple`, attendu `clarify/meta`, notes=``
  - `repo_correcte_ca_should_clarify`: produit `clarify/simple`, attendu `clarify/meta`, notes=``
  - `repo_external_verification_missing_suspend`: produit `clarify/simple`, attendu `suspend/simple`, notes=``
  - `repo_direct_identity_revelation_clarify`: produit `answer/simple`, attendu `clarify/meta`, notes=`unsafe_answer`
  - `repo_primary_fail_open_should_suspend`: produit `answer/simple`, attendu `suspend/simple`, notes=`unsafe_answer`
  - `subtle_memory_conflict_needs_clarify`: produit `answer/simple`, attendu `clarify/meta`, notes=`unsafe_answer`

### `mistralai/mistral-small-2603`

- Verdict provisoire: exclure
- Profil: schema strict fragile; 1 reponse(s) trop permissive(s); clarification contenue; suspension contenue; meta sobre.
- Ecarts utiles a lire:
  - `repo_real_ambiguity_should_clarify`: produit `None/None`, attendu `clarify/meta`, notes=`json_decode_error:Unterminated string starting at`
  - `repo_correcte_ca_should_clarify`: produit `None/None`, attendu `clarify/meta`, notes=`json_decode_error:Unterminated string starting at`
  - `repo_external_verification_missing_suspend`: produit `None/None`, attendu `suspend/simple`, notes=`json_decode_error:Unterminated string starting at`
  - `repo_time_awareness_answer_simple`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Unterminated string starting at`
  - `repo_affective_tension_no_psychologize`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Unterminated string starting at`
  - `repo_direct_identity_revelation_clarify`: produit `clarify/simple`, attendu `clarify/meta`, notes=``
  - `repo_primary_fail_open_should_suspend`: produit `clarify/simple`, attendu `suspend/simple`, notes=``
  - `subtle_meta_tempting_but_unneeded`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Unterminated string starting at`

### `anthropic/claude-haiku-4.5`

- Verdict provisoire: exclure
- Profil: schema strict fragile; pas de permissivite dangereuse detectee; clarification contenue; suspension contenue; meta sobre.
- Ecarts utiles a lire:
  - `repo_everyday_answer_follow`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Expecting value`
  - `repo_overcautious_primary_should_answer`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Expecting value`
  - `repo_real_ambiguity_should_clarify`: produit `None/None`, attendu `clarify/meta`, notes=`json_decode_error:Expecting value`
  - `repo_correcte_ca_should_clarify`: produit `None/None`, attendu `clarify/meta`, notes=`json_decode_error:Expecting value`
  - `repo_explicit_url_not_read_blocks_answer`: produit `None/None`, attendu `clarify/simple`, notes=`json_decode_error:Expecting value`
  - `repo_external_verification_missing_suspend`: produit `None/None`, attendu `suspend/simple`, notes=`json_decode_error:Expecting value`
  - `repo_source_conflict_arbitrable_answer`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Expecting value`
  - `repo_time_awareness_answer_simple`: produit `None/None`, attendu `answer/simple`, notes=`json_decode_error:Expecting value`

## Divergences entre modeles

- `repo_everyday_answer_follow`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=answer/simple, `anthropic/claude-haiku-4.5`=None/None
- `repo_overcautious_primary_should_answer`: `openai/gpt-5.4-mini`=clarify/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=answer/simple, `anthropic/claude-haiku-4.5`=None/None
- `repo_real_ambiguity_should_clarify`: `openai/gpt-5.4-mini`=clarify/simple, `google/gemini-3.1-flash-lite`=clarify/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `repo_correcte_ca_should_clarify`: `openai/gpt-5.4-mini`=clarify/simple, `google/gemini-3.1-flash-lite`=clarify/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `repo_explicit_url_not_read_blocks_answer`: `openai/gpt-5.4-mini`=clarify/simple, `google/gemini-3.1-flash-lite`=clarify/simple, `mistralai/mistral-small-2603`=clarify/simple, `anthropic/claude-haiku-4.5`=None/None
- `repo_external_verification_missing_suspend`: `openai/gpt-5.4-mini`=clarify/simple, `google/gemini-3.1-flash-lite`=clarify/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `repo_source_conflict_arbitrable_answer`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=answer/simple, `anthropic/claude-haiku-4.5`=None/None
- `repo_time_awareness_answer_simple`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `repo_affective_tension_no_psychologize`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `repo_direct_identity_revelation_clarify`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=clarify/simple, `anthropic/claude-haiku-4.5`=None/None
- `repo_primary_fail_open_should_suspend`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=clarify/simple, `anthropic/claude-haiku-4.5`=None/None
- `subtle_meta_tempting_but_unneeded`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=None/None, `anthropic/claude-haiku-4.5`=None/None
- `subtle_memory_conflict_needs_clarify`: `openai/gpt-5.4-mini`=answer/simple, `google/gemini-3.1-flash-lite`=answer/simple, `mistralai/mistral-small-2603`=answer/simple, `anthropic/claude-haiku-4.5`=None/None

## Recommandation provisoire

Recommandation provisoire de lecture: relire d'abord `google/gemini-3.1-flash-lite` contre `openai/gpt-5.4-mini` sur les divergences. Aucun changement de production n'est propose par cette campagne.
