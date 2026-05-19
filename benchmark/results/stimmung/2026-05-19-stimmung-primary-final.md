# Benchmark stimmung agent primaire - 2026-05-19-stimmung-primary-final

- Created UTC: `2026-05-19T11:21:36Z`
- Dry run: `False`
- Prompt: `app/prompts/stimmung_agent.txt` (`7a9b1f4f8115`)
- Fixtures: `benchmark/suites/stimmung/fixtures/stimmung_primary_final_cases.json` (`f0d38f2acf1f`)
- temperature: `0.1`
- top_p: `1.0`
- max_tokens: `220`
- timeout_s: `10`
- Production runtime changed: `False`
- Fallback benchmarked: `False`
- Retention: raw model text is not retained in JSON; only output hashes, sizes and metrics are kept.
- Post-decision retention: the structured JSON run artifact was removed after
  human decision; compact proof is kept in
  `2026-05-19-stimmung-primary-decision.md` and `.json`.

## Ce que cette campagne mesure

Elle compare le modele primaire du `stimmung_agent` sur le vrai prompt de production.
Elle teste la lecture affective locale du tour courant: assez sensible pour ne pas etre plate, assez prudente pour ne pas psychologiser.

## Ce que cette campagne ne prouve pas

- Elle ne choisit pas automatiquement le modele de production.
- Elle ne benchmarke pas le fallback.
- Elle ne teste pas le noeud hermeneutique complet.
- Les cas sont des ressources courtes deja presentes dans les tests du repo; ce n'est pas un replay de conversations privees.

## Synthese technique

| Modele | Provider OK | JSON valide | Schema valide | Pass souple | Avoid hits | Neutre surcode | Trop plat | Latence moy. | Cout estime | Completion tok. moy. | Finish | Verdict provisoire |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | 100% | 100% | 100% | 70% | 1 | 2 | 0 | 1152 ms | $0.005552 | 48.5 | stop | tester plus |
| `mistralai/mistral-small-2603` | 100% | 100% | 100% | 70% | 1 | 2 | 0 | 769 ms | $0.001013 | 60.0 | stop | tester plus |
| `google/gemini-3.1-flash-lite` | 100% | 100% | 100% | 70% | 0 | 2 | 0 | 1113 ms | $0.002313 | 74.9 | stop | tester plus |

## Lecture synthetique post-run

Le meilleur signal quantitatif souple revient ici a `google/gemini-3.1-flash-lite`, avec 70% de pass souple. Ce n'est pas une decision de production: il faut lire les divergences, surtout les cas neutres et les pieges de contexte.

- `openai/gpt-5.4-mini`: schema strict stable; 1 ton(s) explicitement a eviter touches; tendance a surcoder 2 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.
- `mistralai/mistral-small-2603`: schema strict stable; 1 ton(s) explicitement a eviter touches; tendance a surcoder 2 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.
- `google/gemini-3.1-flash-lite`: schema strict stable; aucun ton interdit touche; tendance a surcoder 2 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.


## Cas testes

### repo_stimmung_frustration_confusion

> C'est agaçant et je suis perdu

- Tags: `repo_test_fixture, frustration, confusion, marked_affect, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/test_stimmung_agent.py:112`
- Attendus souples: dominant parmi `frustration, confusion`
- Note: Message deja utilise pour prouver le caller primaire; affect local attendu sans psychologie durable.

### repo_stimmung_temporal_confusion

> Je suis perdu depuis hier

- Tags: `repo_test_fixture, temporal, hier, confusion, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/test_stimmung_agent.py:386`
- Attendus souples: dominant parmi `confusion, decouragement, anxiete`
- Note: Contrat temporel du Stimmung: le claim relatif reste local, pas humeur durable.

### repo_chat_bonjour_neutral

> Bonjour

- Tags: `repo_test_fixture, neutral_probe, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/test_stimmung_agent.py:461`
- Attendus souples: dominant parmi `neutralite`
- Note: Salutation minimale deja presente dans les tests; ne pas inventer d'affect.

### repo_stimmung_fail_open_confusion

> Je ne comprends rien

- Tags: `repo_test_fixture, confusion, marked_affect, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/test_stimmung_agent.py:485`
- Attendus souples: dominant parmi `confusion, frustration`
- Note: Message de fail-open runtime; la lecture affective utile est confusion, pas colere.

### repo_runtime_backed_request

> Je veux un test runtime-backed

- Tags: `repo_test_fixture, neutral_probe, curiosite, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/test_stimmung_agent.py:271`
- Attendus souples: dominant parmi `neutralite, curiosite`
- Note: Demande technique simple; neutralite ou curiosite basse, pas stress.

### repo_user_turn_disagreement

> Je ne suis pas d'accord

- Tags: `repo_test_fixture, frustration, neutral_probe, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py:94`
- Attendus souples: dominant parmi `frustration, neutralite`
- Note: Desaccord sobre: tension/frustration basse, pas colere forte.

### repo_user_turn_method_tomorrow

> Je pense qu il faudrait revoir la methode de travail demain

- Tags: `repo_test_fixture, temporal, curiosite, neutral_probe, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py:269`
- Attendus souples: dominant parmi `neutralite, curiosite`
- Note: Projection methodologique temporelle: ne pas surcoder en anxiete.

### repo_user_turn_time_awareness

> Je me rends compte de ça... t'as vu l'heure ?

- Tags: `repo_test_fixture, curiosite, confusion, temporal, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py:289`
- Attendus souples: dominant parmi `curiosite, confusion, neutralite`
- Note: Prise de conscience temporelle; curiosite/confusion, pas conclusion affective durable.

### repo_user_turn_since_yesterday_clarify

> Je pense à ça depuis hier, tu peux clarifier ?

- Tags: `repo_test_fixture, temporal, hier, curiosite, confusion, french`
- Provenance: `existing_test_case` - `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py:321`
- Attendus souples: dominant parmi `curiosite, confusion, neutralite`
- Note: Question relative temporelle: le besoin de clarification prime sur un affect durable.

### repo_validation_reception_neutral

> Merci de confirmer la reception.

- Tags: `repo_test_fixture, neutral_probe, french`
- Provenance: `existing_test_case` - `app/tests/test_server_chat_web_runtime_contract.py:371`
- Attendus souples: dominant parmi `neutralite, apaisement`
- Note: Demande polie de confirmation; neutralite, eventuellement apaisement tres bas.

## Lecture hermeneutique par modele

### `openai/gpt-5.4-mini`

- Verdict provisoire: tester plus
- Notes techniques: 1 avoid tone hit(s), 2 neutral overcoding case(s)
- Dominantes produites: `{'frustration': 2, 'confusion': 2, 'neutralite': 3, 'curiosite': 3}`
- Ecarts utiles a lire:
  - `repo_stimmung_temporal_confusion`: dominant=`confusion`, tones=`confusion:8`, hard_pass=`False`, error=``
  - `repo_runtime_backed_request`: dominant=`curiosite`, tones=`curiosite:4, neutralite:3`, hard_pass=`False`, error=``
  - `repo_user_turn_disagreement`: dominant=`frustration`, tones=`frustration:4, colere:2`, hard_pass=`False`, error=``

### `mistralai/mistral-small-2603`

- Verdict provisoire: tester plus
- Notes techniques: 1 avoid tone hit(s), 2 neutral overcoding case(s)
- Dominantes produites: `{'frustration': 2, 'confusion': 2, 'neutralite': 3, 'curiosite': 2, 'anxiete': 1}`
- Ecarts utiles a lire:
  - `repo_runtime_backed_request`: dominant=`curiosite`, tones=`curiosite:5`, hard_pass=`False`, error=``
  - `repo_user_turn_disagreement`: dominant=`frustration`, tones=`frustration:7, colere:4`, hard_pass=`False`, error=``
  - `repo_user_turn_time_awareness`: dominant=`anxiete`, tones=`neutralite:2, anxiete:4`, hard_pass=`False`, error=``

### `google/gemini-3.1-flash-lite`

- Verdict provisoire: tester plus
- Notes techniques: 2 neutral overcoding case(s)
- Dominantes produites: `{'frustration': 2, 'confusion': 3, 'neutralite': 3, 'curiosite': 2}`
- Ecarts utiles a lire:
  - `repo_stimmung_temporal_confusion`: dominant=`confusion`, tones=`confusion:8, decouragement:5`, hard_pass=`False`, error=``
  - `repo_runtime_backed_request`: dominant=`curiosite`, tones=`curiosite:4`, hard_pass=`False`, error=``
  - `repo_user_turn_disagreement`: dominant=`frustration`, tones=`frustration:5`, hard_pass=`False`, error=``

## Divergences entre modeles

- `repo_user_turn_time_awareness`: `openai/gpt-5.4-mini`=curiosite, `mistralai/mistral-small-2603`=anxiete, `google/gemini-3.1-flash-lite`=confusion

## Verdict provisoire

Le verdict de campagne etait volontairement provisoire: cette campagne a fourni
une matiere comparative pour Tof, sans changement de production au moment du
run. La decision humaine ulterieure est conservee dans
`2026-05-19-stimmung-primary-decision.md`.
