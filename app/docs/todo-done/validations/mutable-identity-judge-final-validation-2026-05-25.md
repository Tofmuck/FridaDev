# Mutable identity judge-first - final validation - 2026-05-25

Statut: validation historique Lot 7, mise a jour apres le cutover add-only
ontologique `mutable_judge_v2` et le smoke reel Lot D.

Branche validee: `feature/mutable-refonte`

## Conclusion

La refonte mutable judge-first est maintenant validee comme pipeline actif
add-only ontologique:

```text
5 paires completes user/assistant
-> mutable_identity_judge_v2
-> mutable_judge_v2
-> mutable_identity_judge_apply append-only
-> identity_mutables
-> identity_mutable_audit content-free
-> reinjection static + mutable
```

L'ancien writer mutable score-first n'est plus un systeme actif. Les modules `memory_identity_periodic_apply.py` et `memory_identity_periodic_scoring.py` ont ete retires. `arbiter.run_identity_periodic_agent()` reste une entree de compatibilite desactivee et ne fait pas d'appel provider.

Les sections historiques ci-dessous qui parlent de `mutable_judge_v1`,
`persist`, `tighten`, `merge`, `clear_obsolete`, `target_ref` ou `target_refs`
documentent les etapes pre-Lot B. Le contrat actif automatique depuis Lot B est
`mutable_judge_v2`: verdicts `add` / `no_change` uniquement, sans operation ni
maintenance automatique du canon existant.

## Smoke Reel Lot D Add-Only v2 - 2026-05-26

Le smoke reel Lot D a ete adapte pour appeler le vrai juge `mutable_judge_v2`
sans applicateur et sans ecriture DB live.

Script:

- `app/scripts/smoke_mutable_identity_judge_llm.py`

Commande:

```bash
docker exec -i -w /app platform-fridadev python scripts/smoke_mutable_identity_judge_llm.py
```

Scenario synthetique:

- 5 paires completes envoyees au juge, une 6e paire gardee hors fenetre;
- formulation ontologique explicite cote Frida;
- formulation ontologique explicite cote Tof;
- bruit local: reformulation, fatigue du jour, meteo, demande de liste;
- idees deja couvertes par `static` ou `mutable_current`;
- aucun appel applicateur, aucune persistence, aucune modification de
  `identity_mutables` ou `identity_mutable_staging`.

Resultat observe, content-free:

- modele demande: `anthropic/claude-haiku-4.5`;
- modele provider observe: `anthropic/claude-4.5-haiku-20251001`;
- slot runtime: `identity_periodic_model`;
- prompt actif: `prompts/identity_mutable_judge_v2.txt` via
  `IDENTITY_MUTABLE_JUDGE_PROMPT_PATH`;
- structured output: `response_format.type=json_schema`,
  `json_schema.name=mutable_judge_v2`, `strict=true`;
- `provider.require_parameters=true`;
- `provider.order=["anthropic"]`;
- appel provider reel effectue;
- tokens provider observes apres rebuild: `prompt=3459`, `completion=316`, `total=3775`;
- `status=skipped`;
- `reason_code=invalid_verdict`;
- `validation_reason=invalid_verdict`;
- `verdict_counts={}` faute de contrat complet;
- `live_db_write=false`;
- `applicator_called=false`;
- aucun contenu brut de fenetre, prompt complet, secret ou cookie affiche.

Decision modele:

- Haiku n'est pas valide comme suffisant pour ce role dans la configuration
  actuelle: il repond au smoke synthetique borne, mais la sortie structuree est
  rejetee par le validateur metier `mutable_judge_v2`.
- Lot D ne change pas le modele runtime.
- Prochain micro-lot recommande: comparer un modele plus fort pour
  `mutable_judge_v2` ou ajuster explicitement le timeout du slot juge, puis
  rejouer le meme smoke sans ecriture DB.

## Smoke Reel Lot D Bis - Candidat GPT 5.4 Mini - 2026-05-26

Le smoke a ete etendu avec un override modele temporaire:

```bash
docker exec -i -w /app platform-fridadev sh -c 'python scripts/smoke_mutable_identity_judge_llm.py --model openai/gpt-5.4-mini; printf "\nexit_code=%s\n" "$?"'
```

Garanties:

- l'override ne modifie pas les runtime settings persistants;
- `runtime_model_persisted_changed=false`;
- aucun applicateur n'est appele;
- aucune ecriture DB live;
- meme prompt `prompts/identity_mutable_judge_v2.txt`;
- meme schema strict `mutable_judge_v2`;
- meme scenario synthetique que Lot D;
- `provider.require_parameters=true`;
- `provider.order=["anthropic"]` est retire pour ce candidat non-Anthropic afin
  de ne pas forcer le provider Anthropic.

Resultat content-free:

- modele runtime persistant: `anthropic/claude-haiku-4.5`;
- modele demande pour le smoke: `openai/gpt-5.4-mini`;
- provider effectif: `openai/gpt-5.4-mini-20260317`;
- structured output: oui, `json_schema`, `strict=true`;
- `temperature` et `top_p` omis pour ce modele afin de rester compatible avec
  `provider.require_parameters=true`;
- status: `ok`;
- reason_code: `judge_complete`;
- verdict_counts: `{"add": 2}`;
- add `llm`: oui;
- add `user`: oui;
- bruit ajoute: non;
- propositions synthetiques acceptees: `Frida tient une voix propre sans se
  confondre avec Tof.` et `Tof traite la frontière entre sa pensée et la voix
  de Frida comme un objet central.`;
- tokens provider observes: `prompt=2273`, `completion=168`, `total=2441`;
- `live_db_write=false`;
- `applicator_called=false`;
- exit code: `0`.

Decision:

- Le 404 precedent ne venait pas d'un modele absent, mais d'un payload non
  routable avec `provider.require_parameters=true` et des parametres non
  supportes (`temperature` / `top_p`).
- Le premier smoke compatible a prouve que `openai/gpt-5.4-mini` pouvait
  produire un contrat valide, mais il a aussi expose une instabilite de contrat
  sur les sorties `no_change`.
- Ne pas changer le modele actif.
- Le schema `mutable_judge_v2` a ensuite ete durci pour discriminer
  structurellement `add` et `no_change`.

### Durcissement no_change - 2026-05-26

Le schema v2 impose maintenant:

- `add`: proposition non vide, `source_refs` non vide, reason code add,
  `continuity_kind` different de `none`;
- `no_change`: `proposition=""`, `source_refs=[]`, `guard_notes=[]`,
  reason code no_change, `continuity_kind="none"`.

Le prompt ajoute:

- `For no_change, proposition MUST be empty, source_refs MUST be empty,
  guard_notes MUST be empty, continuity_kind MUST be "none".`
- `Never explain a no_change verdict inside proposition or guard_notes.`
- exactement un verdict pour `user` et exactement un verdict pour `llm`.

Smoke 3 runs apres durcissement:

```bash
docker exec -i -w /app platform-fridadev sh -c 'python scripts/smoke_mutable_identity_judge_llm.py --model openai/gpt-5.4-mini --runs 3; printf "\nexit_code=%s\n" "$?"'
```

Resultat content-free:

- provider effectif: `openai/gpt-5.4-mini-20260317`;
- structured output: oui, schema strict discriminant;
- run 1: `status=ok`, `verdict_counts={"no_change": 2}`, add llm non, add user non;
- run 2: `status=ok`, `verdict_counts={"no_change": 2}`, add llm non, add user non;
- run 3: `status=ok`, `verdict_counts={"add": 1, "no_change": 1}`, add llm oui, add user non;
- `noise_add_count=0` sur les trois runs;
- `source_refs_count=0` et `guard_notes_count=0` sur les no_change;
- `live_db_write=false`;
- `applicator_called=false`;
- aggregate: `runs_ok=0/3`, `exit_code=5`.

Conclusion:

- Le verrou structurel `no_change` fonctionne: plus de proposition, refs ou
  guard notes dans les `no_change`.
- `openai/gpt-5.4-mini` n'est pas encore valide pour une bascule runtime: il
  rate les adds attendus sur le smoke 3 runs.

## Smoke Reel Modele Frontiere - GPT 5.5 - 2026-05-26

Verification OpenRouter pre-smoke:

- `openai/gpt-5.2`: disponible, `response_format` et `structured_outputs`
  annonces par l'API modeles/endpoints;
- `openai/gpt-5.1`: disponible, `response_format` et `structured_outputs`
  annonces par l'API modeles/endpoints;
- `openai/gpt-5.5`: disponible, `response_format` et `structured_outputs`
  annonces par l'API modeles/endpoints.

Smoke retenu:

```bash
docker exec -i -w /app platform-fridadev sh -c 'python scripts/smoke_mutable_identity_judge_llm.py --model openai/gpt-5.5 --runs 3; printf "\nexit_code=%s\n" "$?"'
```

Resultat content-free:

- modele demande: `openai/gpt-5.5`;
- provider effectif: `openai/gpt-5.5-20260423`;
- structured output: oui, `json_schema`, `strict=true`;
- run 1: `status=ok`, `verdict_counts={"add": 2}`, add llm oui, add user oui;
- run 2: `status=ok`, `verdict_counts={"add": 2}`, add llm oui, add user oui;
- run 3: `status=ok`, `verdict_counts={"add": 2}`, add llm oui, add user oui;
- `noise_add_count=0` sur les trois runs;
- aucun champ v1;
- `live_db_write=false`;
- `applicator_called=false`;
- aggregate: `runs_ok=3/3`, `exit_code=0`.

Decision:

- `openai/gpt-5.5` est le premier candidat valide observe pour le juge mutable
  `mutable_judge_v2` sur le smoke synthetique strict.
- Le runtime persistant n'est pas modifie; une bascule du slot
  `identity_periodic_model` doit rester un micro-lot separe avec GO explicite.

## Bascule Modele Runtime - GPT 5.2 - 2026-05-26

Decision operateur:

- conserver le nom de slot de compatibilite `identity_periodic_model`;
- basculer uniquement `identity_periodic_model.model` vers `openai/gpt-5.2`;
- ne pas changer le contrat `mutable_judge_v2`, le prompt, le schema,
  l'applicateur add-only ou les mutables live.

Preuve pre-bascule:

- ancien modele effectif du slot: `anthropic/claude-haiku-4.5`;
- `openai/gpt-5.2` passe le smoke strict 3/3 avec le meme prompt et le meme
  schema.

Commande de bascule:

```python
runtime_settings.update_runtime_section(
    'identity_periodic_model',
    {'model': {'value': 'openai/gpt-5.2'}},
    updated_by='celebrimbor_mutable_judge_model_cutover',
)
```

Resultat:

- nouveau modele effectif du slot: `openai/gpt-5.2`;
- DB runtime modifiee: oui, uniquement le champ non secret
  `identity_periodic_model.model`;
- aucun secret affiche;
- aucun write static;
- aucune mutation de contrat ou de prompt.

## Crash Test Conversationnel

Test ajoute:

- `tests.unit.chat.test_mutable_identity_judge_final_validation.MutableIdentityJudgeFinalValidationTests.test_conversation_crash_test_runs_judge_first_pipeline_without_live_db_pollution`

Le test simule 6 paires completes `user` / `assistant` en memoire:

- les 5 premieres paires declenchent exactement une fenetre jugee;
- la 6e paire prouve que le buffer a ete vide puis relance a `1/5`;
- le test passe par `record_identity_entries_for_mode(...)`, `memory_identity_periodic_agent.stage_identity_turn_pair(...)`, `mutable_identity_runtime.run_mutable_identity_window(...)`, `mutable_identity_judge` fake deterministe, puis `mutable_identity_apply`;
- aucun appel modele live et aucune DB live ne sont utilises.

La fenetre jugee contient:

- des formulations mutables explicites cote `llm`;
- des formulations mutables explicites cote `user`;
- du bruit non identitaire: tache locale, reformulation, meteo, etat temporaire.

Preuves du test:

- le juge recoit les 5 paires completes, dans l'ordre, avec roles et contenu integral;
- le bruit reste visible au juge et n'est pas prefiltre par Python;
- les mutables `llm` et `user` sont ecrites dans le meme pipeline;
- la 6e paire ne declenche pas de deuxieme jugement ni de deuxieme ecriture;
- aucun champ legacy `strength`, `frequency_norm`, `recency_norm`, `threshold_verdict`, `strength_below_threshold` n'apparait dans l'entree juge ou les observabilites actives;
- aucun statique n'est ecrit;
- l'acteur d'ecriture est `mutable_identity_judge_apply`;
- les stages actifs sont `mutable_identity_judge` et `mutable_identity_judge_apply`;
- l'observabilite collectee reste content-free: pas de fenetre brute, pas de proposition brute, pas de texte conversationnel sensible;
- `identity_input` et le bloc prompt relisent bien `static + mutable`.

## Smoke Reel Juge LLM

Correction finale du 2026-05-25:

- le crash test pipeline reste deterministe et in-memory;
- un smoke manuel borne appelle maintenant le vrai `mutable_identity_judge` avec le modele runtime du slot `identity_periodic_model`;
- la persistence reste desactivee: aucun write DB live, aucun `identity_mutables` de production modifie;
- le smoke utilise une fenetre synthetique de 5 paires envoyees au juge et conserve une 6e paire hors fenetre pour prouver que la preuve n'exige pas de rejouer le pipeline live.

Bug trouve par le smoke et corrige:

- le modele peut renvoyer un JSON valide entoure d'un fence Markdown complet;
- le runner accepte maintenant ce cas strictement borne, sans accepter de texte libre autour;
- le prompt actif precise que le modele doit rendre un objet JSON brut, inclure au moins un verdict `user` et un verdict `llm`, et garder `guard_notes` sous forme de codes courts content-free.

Commande de smoke executee:

```bash
docker exec -i -w /app platform-fridadev python - < app/scripts/smoke_mutable_identity_judge_llm.py
```

Resultat content-free:

- modele: `anthropic/claude-haiku-4.5`;
- slot: `identity_periodic_model`;
- prompt kind: `mutable_identity_judge`;
- status: `ok`;
- reason_code: `judge_complete`;
- schema: `mutable_judge_v1`;
- verdict_counts: `{"persist": 2}`;
- subjects_touched: `["llm", "user"]`;
- operation_kinds: `["add"]`;
- source_refs valides: oui, bornes a `pair_01..pair_05`;
- bruit persiste: `0`;
- all_no_change: `false`;
- persistence live: `false`;
- fingerprints propositions: hashes courts et longueurs seulement, sans texte brut.

## Durcissement Structured Output - 2026-05-26

Apres le blocage live `empty_proposition`, le juge mutable a ete durci sans
relacher le validateur metier:

- le payload OpenRouter du caller `mutable_identity_judge` contient maintenant
  `response_format.type=json_schema`, `response_format.json_schema.name=mutable_judge_v1`,
  `response_format.json_schema.strict=true`, `provider.require_parameters=true`
  et `provider.order=["anthropic"]`;
- le premier essai strict via routage OpenRouter par defaut a expose deux
  contraintes provider content-free: Bedrock refuse `minItems=2` sur un array,
  puis depasse le timeout runtime de 10s; le schema utilise donc `minItems=1`
  et le routage privilegie Anthropic direct sans desactiver les fallbacks;
- le prompt interdit explicitement un `persist` incomplet: `add`, `tighten` et
  `merge` doivent porter une `proposition` non vide, tandis que
  `clear_obsolete` reste le seul cas normal de `proposition=""` avec `target`
  non vide;
- les invalidations du validateur exposent un diagnostic content-free
  (`validation_reason`, verdict/operation/reason code, longueurs et compteurs)
  sans proposition, target, fenetre, prompt ou reponse brute;
- le validateur FridaDev reste souverain apres structured output;
- la fenetre bloquee reste preservee en cas d'invalidation. La suspension
  operateur apres N echecs identiques reste un durcissement futur possible, pas
  une action automatique de ce correctif.

Smoke reel apres patch:

- commande: `docker exec -i -w /app platform-fridadev python - < app/scripts/smoke_mutable_identity_judge_llm.py`;
- modele slot: `anthropic/claude-haiku-4.5`;
- modele provider observe: compatible avec le schema strict via routage
  `provider.order=["anthropic"]`;
- status: `ok`;
- reason_code: `judge_complete`;
- `structured_output.response_format_type`: `json_schema`;
- `structured_output.json_schema_strict`: `true`;
- `provider_require_parameters`: `true`;
- `verdict_counts`: `{"persist": 2}`;
- sujets persistants: `["llm", "user"]`;
- bruit persiste: `0`;
- persistence live: `false`;
- contenu affiche: uniquement compteurs, statuts, longueurs et hashes courts.

## Correction Ciblage Mutable - 2026-05-26

Apres le passage du juge en structured output, le blocage live suivant a ete
observe content-free:

- `judge_status=ok`, `judge_reason_code=judge_complete`;
- `apply_status=skipped`, `apply_reason_code=impossible_mutation`;
- `operation_kinds=["add", "tighten"]`;
- outcome fautif: `operation=tighten`, `reason_code=invalid_target`;
- aucun write partiel grace au batch all-or-nothing.

Cause confirmee: le juge demandait un `tighten`, mais l'ancien contrat exigeait
que `target` recopie exactement une proposition mutable courante. Une
reformulation, une cible issue d'un canon avant rewrite manuel ou une phrase
proche suffisait donc a bloquer toute la fenetre.

Correction:

- le payload juge expose maintenant `current_mutables.<subject>.propositions[]`
  avec des refs reconstruites `llm_01`, `user_01`, etc.;
- le contrat `mutable_judge_v1` ajoute `target_ref` et `target_refs`;
- l'applicateur resout `tighten`, `merge` et `clear_obsolete` par ref stable
  quand elle est fournie;
- le fallback texte exact `target` / `targets` reste disponible pour
  compatibilite;
- aucun matching approximatif ou scoring identitaire n'est introduit;
- les echecs sont distingues en `target_ref_invalid`, `target_not_found` ou
  `target_ambiguous` lorsque possible;
- l'observabilite reste content-free: refs, compteurs, longueurs, hashes, jamais
  le texte brut des mutables ou de la fenetre.

Micro-correction batch du 2026-05-26:

- les refs `llm_01`, `user_02`, etc. sont resolues contre le snapshot mutable
  initial envoye au juge pour toute la duree du batch;
- l'applicateur garde une table d'origines separee de la liste courante mutee,
  afin qu'une suppression anterieure ne decale pas la cible d'un `tighten` ou
  d'un `merge` suivant;
- si une ref vise une proposition initiale deja supprimee ou fusionnee dans le
  meme contrat, l'operation echoue content-free (`target_already_mutated` ou
  `impossible_mutation`) et le batch atomique n'ecrit rien;
- aucun matching approximatif, score identitaire ou writer legacy n'est ajoute.

## Preparation Dormante Add-Only Ontologique - 2026-05-26

Un contrat `mutable_judge_v2` dormant a ete ajoute en Lot A pour preparer le
recadrage add-only ontologique sans bascule runtime.

Etat:

- le runtime actif reste `mutable_judge_v1`;
- `mutable_judge_v2` n'est pas appele par le flow chat;
- le prompt dormant est `app/prompts/identity_mutable_judge_v2.txt`;
- le schema v2 accepte seulement les verdicts `add` et `no_change`;
- le schema v2 ne contient pas `operation`, `target`, `targets`, `target_ref`
  ou `target_refs`;
- le structured output v2 reste strict et conserve
  `provider.require_parameters=true` avec `provider.order=["anthropic"]`;
- le cutover reel est reserve au Lot B, en meme temps que l'applicateur
  add-only.

## Non-Concurrence Legacy

Preuves attendues et verifiees:

- aucun import actif de `memory_identity_periodic_apply.py`;
- aucun import actif de `memory_identity_periodic_scoring.py`;
- aucun appel actif a `apply_periodic_agent_contract`;
- aucun appel actif a `score_operation`;
- `identity_periodic_agent.txt` est legacy disabled;
- `identity_periodic_model` reste seulement un nom de slot de compatibilite pour le juge mutable;
- `identity_mutable_staging` reste un support technique de fenetre, pas un canon ni un writer concurrent;
- `promotion_to_static_enabled=false` reste le regime admin/read-model;
- aucune promotion automatique `mutable -> static` n'est active.

## Commandes De Preuve

Commandes executees pendant le lot:

```bash
python3 -m py_compile \
  app/core/chat_memory_flow.py \
  app/memory/memory_identity_periodic_agent.py \
  app/memory/mutable_identity_runtime.py \
  app/memory/mutable_identity_judge.py \
  app/memory/mutable_identity_apply.py \
  app/tests/unit/chat/test_mutable_identity_judge_final_validation.py

docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest \
  tests.unit.memory.test_mutable_identity_judge \
  tests.unit.memory.test_mutable_identity_apply \
  tests.unit.memory.test_identity_periodic_agent_phase1 \
  tests.unit.chat.test_mutable_identity_judge_final_validation \
  tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline \
  tests.test_server_admin_identity_read_model_phase2

docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest \
  tests.unit.logs.test_chat_turn_logger_phase2 \
  tests.unit.admin.test_identity_read_model_lot3 \
  tests.unit.admin.test_identity_governance_service_phase5 \
  tests.test_server_admin_settings_read_contract

git grep -n "memory_identity_periodic_apply\|memory_identity_periodic_scoring\|apply_periodic_agent_contract\|score_operation\|threshold_verdict\|frequency_norm\|recency_norm\|strength_below_threshold" \
  app/core app/memory app/admin app/tests app/docs/states app/docs/todo-todo app/docs/todo-done/refactors

docker exec -i -w /app platform-fridadev python - < app/scripts/smoke_mutable_identity_judge_llm.py
```

Les hits restants du grep sont des tests d'absence, des docs historiques, ou des references explicites de non-concurrence.

## Limites Volontaires

- Pas de pollution de la DB live avec de fausses identites de test.
- Pas de renommage global de `identity_periodic_model`.
- Pas de migration ni purge de `identity_mutable_staging`.
- Pas de benchmark modele live.
- Pas de Lot 7 UI supplementaire.

`Frida_from_herself.md` reste suspendu et non concurrent; l'intuition est absorbee par la lecture de fenetre complete du juge mutable jusqu'a reevaluation separee.
