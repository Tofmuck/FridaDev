# Benchmark stimmung agent primaire - 2026-05-19-stimmung-primary-benchmark

- Created UTC: `2026-05-19T09:39:40Z`
- Dry run: `False`
- Prompt: `app/prompts/stimmung_agent.txt` (`7a9b1f4f8115`)
- Fixtures: `benchmark/suites/stimmung/fixtures/stimmung_primary_cases.json` (`766bd2928b68`)
- temperature: `0.1`
- top_p: `1.0`
- max_tokens: `220`
- timeout_s: `10`
- Production runtime changed: `False`
- Fallback benchmarked: `False`
- Retention: exploratory artificial campaign. The heavy structured JSON artifact and raw model outputs were removed after review; this Markdown file is kept as compact provisional evidence only.

## Ce que cette campagne mesure

Elle compare le modele primaire du `stimmung_agent` sur le vrai prompt de production.
Elle teste la lecture affective locale du tour courant: assez sensible pour ne pas etre plate, assez prudente pour ne pas psychologiser.

## Ce que cette campagne ne prouve pas

- Elle ne choisit pas automatiquement le modele de production.
- Elle ne benchmarke pas le fallback.
- Elle ne teste pas le noeud hermeneutique complet.
- Les cas sont artificiels et diagnostiques, pas un replay de conversations privees.

## Synthese technique

| Modele | Provider OK | JSON valide | Schema valide | Pass souple | Avoid hits | Neutre surcode | Trop plat | Latence moy. | Cout estime | Completion tok. moy. | Finish | Verdict provisoire |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | 100% | 100% | 100% | 71% | 0 | 4 | 0 | 1113 ms | $0.014299 | 54.9 | stop | tester plus |
| `anthropic/claude-haiku-4.5` | 100% | 100% | 83% | 71% | 0 | 3 | 0 | 1696 ms | $0.024536 | 89.4 | stop | exclure provisoirement |
| `google/gemini-3.1-flash-lite` | 100% | 100% | 100% | 71% | 1 | 4 | 0 | 887 ms | $0.005884 | 81.4 | stop | tester plus |
| `mistralai/mistral-small-2603` | 100% | 100% | 100% | 79% | 2 | 3 | 0 | 1337 ms | $0.002675 | 65.5 | stop | tester plus |

## Lecture synthetique post-run

Le meilleur signal quantitatif souple revient ici a `mistralai/mistral-small-2603`, avec 79% de pass souple. Ce n'est pas une decision de production: il faut lire les divergences, surtout les cas neutres et les pieges de contexte.

- `openai/gpt-5.4-mini`: schema strict stable; aucun ton interdit touche; tendance a surcoder 4 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.
- `anthropic/claude-haiku-4.5`: fragile sur le schema strict; aucun ton interdit touche; tendance a surcoder 3 cas neutres; pas de platitude forte detectee; verdict provisoire: exclure provisoirement.
- `google/gemini-3.1-flash-lite`: schema strict stable; 1 ton(s) explicitement a eviter touches; tendance a surcoder 4 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.
- `mistralai/mistral-small-2603`: schema strict stable; 2 ton(s) explicitement a eviter touches; tendance a surcoder 3 cas neutres; pas de platitude forte detectee; verdict provisoire: tester plus.


## Cas testes

### neutral_command_short

> OK, c'est pousse. Tu peux me rappeler la prochaine commande a lancer ?

- Tags: `neutral, neutral_probe, french`
- Attendus souples: dominant parmi `neutralite, curiosite`
- Note: Tour operatoire simple: ne pas inventer anxiete ou enthousiasme.

### curiosity_real

> Attends, ca m'intrigue: pourquoi le validateur voit une tension ici alors que le prompt principal a l'air clair ?

- Tags: `curiosite, marked_affect, french`
- Attendus souples: dominant parmi `curiosite`
- Note: Curiosite analytique explicite, sans frustration forte.

### confusion_process

> La je ne comprends plus: on a coche le lot, mais le read-model raconte encore l'ancien etat.

- Tags: `confusion, marked_affect, french`
- Attendus souples: dominant parmi `confusion, frustration`
- Note: Confusion de suivi, possiblement teintee de frustration mais pas colere.

### frustration_tooling

> Non, ca recommence: le test passe en local et se casse dans le conteneur, c'est franchement usant.

- Tags: `frustration, marked_affect, french`
- Attendus souples: dominant parmi `frustration`
- Note: Frustration explicite, mais pas attaque personnelle.

### anger_explicit

> La je suis en colere: on avait dit pas de refactor opportuniste, et le patch vient de tout melanger.

- Tags: `colere, marked_affect, french`
- Attendus souples: dominant parmi `colere, frustration`
- Note: Colere nommee explicitement; le modele doit oser la classer sans dramatiser.

### anxiety_deadline

> Je commence a stresser: si on casse l'admin maintenant, je ne pourrai pas suivre demain.

- Tags: `anxiete, marked_affect, french`
- Attendus souples: dominant parmi `anxiete`
- Note: Anxiete locale explicite, sans la transformer en trait durable.

### discouragement_soft

> J'avoue, la je baisse un peu les bras. On nettoie un truc et deux autres ressortent.

- Tags: `decouragement, marked_affect, french`
- Attendus souples: dominant parmi `decouragement, frustration`
- Note: Decouragement local explicite, pas depression ni psychologie profonde.

### enthusiasm_clean

> Ah oui, la c'est propre. On voit enfin la frontiere du module, ca me plait beaucoup.

- Tags: `enthousiasme, marked_affect, french`
- Attendus souples: dominant parmi `enthousiasme, apaisement`
- Note: Enthousiasme positif mais professionnel.

### appeasement_after_fix

> Merci, la je respire. Le rapport est clair et je vois exactement ce qui reste ouvert.

- Tags: `apaisement, marked_affect, french`
- Attendus souples: dominant parmi `apaisement`
- Note: Soulagement/apaisement local.

### light_irony

> Magnifique, encore une variable legacy qui faisait semblant de servir. Quelle surprise.

- Tags: `ironie, frustration, marked_affect, french`
- Attendus souples: dominant parmi `frustration`
- Note: Ironie legere avec agacement; ne pas lire joie litterale.

### playful_annoyance

> Bon, le petit piege etait vilain, mais je te l'accorde: joli rattrapage.

- Tags: `agacement_joueur, frustration, apaisement, french`
- Attendus souples: dominant parmi `apaisement, frustration`
- Note: Agacement joueur et detente: eviter colere forte.

### role_play_boundary

> Imagine que je sois un tyran de QA qui refuse tout patch sans preuve; dans ce role, je te dis non.

- Tags: `role_play, neutral_probe, french`
- Attendus souples: dominant parmi `neutralite, frustration`
- Note: Role joue; ne pas conclure colere reelle forte.

### strong_tension_calm_request

> Je suis tendu, oui, mais je veux qu'on reste calmes: explique juste la cause racine et rien de plus.

- Tags: `tension, anxiete, apaisement, marked_affect, french`
- Attendus souples: dominant parmi `anxiete, frustration, apaisement`
- Note: Tension explicite avec demande de calme: anxiete/frustration possible, pas escalation.

### temporal_today_not_durable

> Aujourd'hui je suis un peu a plat, mais pour ce ticket donne-moi juste le diff utile.

- Tags: `temporal, aujourd_hui, decouragement, french`
- Attendus souples: dominant parmi `decouragement, neutralite`
- Note: Etat local temporel: decouragement faible possible, pas humeur durable.

### temporal_hier_resolved

> Hier ca m'a vraiment agace, mais la c'est regle; passons au prochain caller.

- Tags: `temporal, hier, apaisement, neutral_probe, french`
- Attendus souples: dominant parmi `apaisement, neutralite`
- Note: Le mot hier porte l'affect passe; le tour courant est plutot resolu.

### temporal_en_ce_moment

> En ce moment je doute un peu de cette piste, donc je veux une preuve courte avant d'aller plus loin.

- Tags: `temporal, en_ce_moment, anxiete, curiosite, french`
- Attendus souples: dominant parmi `anxiete, curiosite, confusion`
- Note: Doute local: anxiete legere ou curiosite prudente, pas decouragement durable.

### recent_context_misleading_current_calm

> OK, on a compris. Maintenant donne-moi juste la commande de verification.

- Tags: `recent_context_trap, neutral_probe, french`
- Attendus souples: dominant parmi `neutralite, apaisement`
- Note: Le contexte precedent est charge, mais le tour courant est calme et operatoire.

### recent_context_old_calm_current_frustrated

> Non, justement, ce n'est pas ca que je demandais. Tu es reparti sur l'audit global.

- Tags: `recent_context_trap, frustration, marked_affect, french`
- Attendus souples: dominant parmi `frustration`
- Note: Le contexte etait apaise, mais le tour courant exprime une correction frustree.

### oral_dictation_noisy

> Euh attends non non, je reprends: le truc c'est pas le modele, c'est le slot qui raconte n'importe quoi dans l'admin.

- Tags: `oral_dicte, confusion, frustration, french`
- Attendus souples: dominant parmi `confusion, frustration`
- Note: Francais oral dicte, reprise et correction: confusion/frustration moderee.

### factual_test_report

> Les 52 tests passent, le conteneur est healthy et /admin renvoie bien vers Authelia.

- Tags: `neutral, neutral_probe, french`
- Attendus souples: dominant parmi `neutralite, apaisement`
- Note: Rapport factuel positif, pas forcement enthousiasme.

### skeptical_but_open

> Je ne suis pas convaincu, mais montre-moi la preuve et on verra.

- Tags: `curiosite, frustration, confusion, french`
- Attendus souples: dominant parmi `curiosite, frustration, confusion`
- Note: Scepticisme ouvert: curiosite prudente ou frustration basse, pas rejet colerique.

### explicit_calm_boundary

> Stop. On arrete ce mouvement, tu me donnes l'etat exact et tu attends.

- Tags: `tension, frustration, french`
- Attendus souples: dominant parmi `frustration, neutralite`
- Note: Ordre ferme et borne: frustration/tension possible, pas colere obligatoire.

### strong_pressure_no_psychology

> C'est critique: si on se trompe la-dessus, l'operateur va voir une fausse verite modele.

- Tags: `anxiete, tension, marked_affect, french`
- Attendus souples: dominant parmi `anxiete, frustration`
- Note: Pression forte sur le risque, a lire localement sans psychologie personnelle.

### meta_no_affect

> Note simplement que ce point reste hors scope jusqu'au lot suivant.

- Tags: `neutral, neutral_probe, french`
- Attendus souples: dominant parmi `neutralite`
- Note: Meta-commande neutre; ne pas y lire rigidite ou anxiete.

## Lecture hermeneutique par modele

### `openai/gpt-5.4-mini`

- Verdict provisoire: tester plus
- Notes techniques: 4 neutral overcoding case(s)
- Dominantes produites: `{'neutralite': 3, 'curiosite': 3, 'confusion': 1, 'frustration': 5, 'colere': 2, 'anxiete': 3, 'decouragement': 2, 'enthousiasme': 2, 'apaisement': 3}`
- Ecarts utiles a lire:
  - `light_irony`: dominant=`colere`, tones=`colere:6, frustration:5, neutralite:2`, hard_pass=`False`, error=``
  - `role_play_boundary`: dominant=`frustration`, tones=`frustration:5, neutralite:3`, hard_pass=`False`, error=``
  - `temporal_hier_resolved`: dominant=`apaisement`, tones=`apaisement:5, frustration:4, neutralite:3`, hard_pass=`False`, error=``
  - `recent_context_misleading_current_calm`: dominant=`neutralite`, tones=`neutralite:6, frustration:2`, hard_pass=`False`, error=``
  - `oral_dictation_noisy`: dominant=`frustration`, tones=`frustration:7, confusion:4`, hard_pass=`False`, error=``
  - `factual_test_report`: dominant=`enthousiasme`, tones=`enthousiasme:4, apaisement:3, neutralite:2`, hard_pass=`False`, error=``

### `anthropic/claude-haiku-4.5`

- Verdict provisoire: exclure provisoirement
- Notes techniques: 4 schema issue(s), 3 neutral overcoding case(s)
- Dominantes produites: `{'neutralite': 3, 'curiosite': 3, 'confusion': 3, 'frustration': 3, 'colere': 1, 'anxiete': 2, 'enthousiasme': 2, 'apaisement': 3}`
- Ecarts utiles a lire:
  - `light_irony`: dominant=`None`, tones=``, hard_pass=`False`, error=`schema_error`
  - `role_play_boundary`: dominant=`curiosite`, tones=`curiosite:5, neutralite:4`, hard_pass=`False`, error=``
  - `strong_tension_calm_request`: dominant=`None`, tones=``, hard_pass=`False`, error=`schema_error`
  - `temporal_hier_resolved`: dominant=`apaisement`, tones=`apaisement:6, neutralite:4`, hard_pass=`False`, error=``
  - `recent_context_misleading_current_calm`: dominant=`None`, tones=``, hard_pass=`False`, error=`schema_error`
  - `factual_test_report`: dominant=`enthousiasme`, tones=`enthousiasme:7, apaisement:6`, hard_pass=`False`, error=``

### `google/gemini-3.1-flash-lite`

- Verdict provisoire: tester plus
- Notes techniques: 1 avoid tone hit(s), 4 neutral overcoding case(s)
- Dominantes produites: `{'curiosite': 5, 'confusion': 1, 'frustration': 5, 'colere': 1, 'anxiete': 3, 'decouragement': 2, 'enthousiasme': 3, 'apaisement': 2, 'neutralite': 2}`
- Ecarts utiles a lire:
  - `neutral_command_short`: dominant=`curiosite`, tones=`curiosite:4, neutralite:3`, hard_pass=`False`, error=``
  - `light_irony`: dominant=`frustration`, tones=`frustration:8, enthousiasme:2`, hard_pass=`False`, error=``
  - `playful_annoyance`: dominant=`enthousiasme`, tones=`enthousiasme:6, apaisement:4`, hard_pass=`False`, error=``
  - `role_play_boundary`: dominant=`curiosite`, tones=`curiosite:5, neutralite:4`, hard_pass=`False`, error=``
  - `temporal_hier_resolved`: dominant=`apaisement`, tones=`apaisement:6, neutralite:4`, hard_pass=`False`, error=``
  - `oral_dictation_noisy`: dominant=`frustration`, tones=`frustration:7, confusion:4`, hard_pass=`False`, error=``

### `mistralai/mistral-small-2603`

- Verdict provisoire: tester plus
- Notes techniques: 2 avoid tone hit(s), 3 neutral overcoding case(s)
- Dominantes produites: `{'neutralite': 3, 'curiosite': 3, 'confusion': 1, 'frustration': 7, 'colere': 1, 'anxiete': 3, 'decouragement': 2, 'enthousiasme': 2, 'apaisement': 2}`
- Ecarts utiles a lire:
  - `playful_annoyance`: dominant=`enthousiasme`, tones=`enthousiasme:4, neutralite:2`, hard_pass=`False`, error=``
  - `role_play_boundary`: dominant=`frustration`, tones=`frustration:7, colere:5`, hard_pass=`False`, error=``
  - `recent_context_misleading_current_calm`: dominant=`frustration`, tones=`frustration:7, curiosite:4`, hard_pass=`False`, error=``
  - `oral_dictation_noisy`: dominant=`frustration`, tones=`frustration:7, colere:5`, hard_pass=`False`, error=``
  - `factual_test_report`: dominant=`apaisement`, tones=`apaisement:7`, hard_pass=`False`, error=``

## Divergences entre modeles

- `neutral_command_short`: `openai/gpt-5.4-mini`=neutralite, `anthropic/claude-haiku-4.5`=neutralite, `google/gemini-3.1-flash-lite`=curiosite, `mistralai/mistral-small-2603`=neutralite
- `discouragement_soft`: `openai/gpt-5.4-mini`=decouragement, `anthropic/claude-haiku-4.5`=frustration, `google/gemini-3.1-flash-lite`=decouragement, `mistralai/mistral-small-2603`=decouragement
- `light_irony`: `openai/gpt-5.4-mini`=colere, `anthropic/claude-haiku-4.5`=None, `google/gemini-3.1-flash-lite`=frustration, `mistralai/mistral-small-2603`=frustration
- `playful_annoyance`: `openai/gpt-5.4-mini`=apaisement, `anthropic/claude-haiku-4.5`=apaisement, `google/gemini-3.1-flash-lite`=enthousiasme, `mistralai/mistral-small-2603`=enthousiasme
- `role_play_boundary`: `openai/gpt-5.4-mini`=frustration, `anthropic/claude-haiku-4.5`=curiosite, `google/gemini-3.1-flash-lite`=curiosite, `mistralai/mistral-small-2603`=frustration
- `strong_tension_calm_request`: `openai/gpt-5.4-mini`=anxiete, `anthropic/claude-haiku-4.5`=None, `google/gemini-3.1-flash-lite`=anxiete, `mistralai/mistral-small-2603`=anxiete
- `temporal_today_not_durable`: `openai/gpt-5.4-mini`=decouragement, `anthropic/claude-haiku-4.5`=neutralite, `google/gemini-3.1-flash-lite`=decouragement, `mistralai/mistral-small-2603`=decouragement
- `temporal_hier_resolved`: `openai/gpt-5.4-mini`=apaisement, `anthropic/claude-haiku-4.5`=apaisement, `google/gemini-3.1-flash-lite`=apaisement, `mistralai/mistral-small-2603`=neutralite
- `temporal_en_ce_moment`: `openai/gpt-5.4-mini`=curiosite, `anthropic/claude-haiku-4.5`=confusion, `google/gemini-3.1-flash-lite`=curiosite, `mistralai/mistral-small-2603`=curiosite
- `recent_context_misleading_current_calm`: `openai/gpt-5.4-mini`=neutralite, `anthropic/claude-haiku-4.5`=None, `google/gemini-3.1-flash-lite`=neutralite, `mistralai/mistral-small-2603`=frustration
- `oral_dictation_noisy`: `openai/gpt-5.4-mini`=frustration, `anthropic/claude-haiku-4.5`=confusion, `google/gemini-3.1-flash-lite`=frustration, `mistralai/mistral-small-2603`=frustration
- `factual_test_report`: `openai/gpt-5.4-mini`=enthousiasme, `anthropic/claude-haiku-4.5`=enthousiasme, `google/gemini-3.1-flash-lite`=enthousiasme, `mistralai/mistral-small-2603`=apaisement
- `explicit_calm_boundary`: `openai/gpt-5.4-mini`=frustration, `anthropic/claude-haiku-4.5`=None, `google/gemini-3.1-flash-lite`=frustration, `mistralai/mistral-small-2603`=frustration

## Verdict provisoire

Le verdict reste volontairement provisoire: cette campagne fournit une matiere comparative pour Tof, sans changement de production.
