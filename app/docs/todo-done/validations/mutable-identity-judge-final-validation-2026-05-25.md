# Mutable identity judge-first - final validation - 2026-05-25

Statut: validation finale Lot 7, corrigee par smoke reel LLM du juge mutable.

Branche validee: `feature/mutable-refonte`

## Conclusion

La refonte mutable judge-first est validee comme pipeline actif:

```text
5 paires completes user/assistant
-> mutable_identity_judge
-> mutable_judge_v1
-> mutable_identity_judge_apply
-> identity_mutables
-> identity_mutable_audit content-free
-> reinjection static + mutable
```

L'ancien writer mutable score-first n'est plus un systeme actif. Les modules `memory_identity_periodic_apply.py` et `memory_identity_periodic_scoring.py` ont ete retires. `arbiter.run_identity_periodic_agent()` reste une entree de compatibilite desactivee et ne fait pas d'appel provider.

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
