# Frida V1 mega-audit - remise au vert avant Lot 9B TODO

Statut: actif, tests et documentation uniquement a la creation.

Roadmap parente:
`app/docs/todo-todo/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`

## Objet

Retablir une suite complete lisible avant tout refactor du Lot 9B. Le dernier
audit independant du 25 juillet 2026 a observe `2549` tests, `22` echecs et
`16` erreurs. Les memes `38` identifiants existaient au parent du correctif de
continuite Web: ils ne sont pas une regression de ce correctif, mais ils
masquent de futures regressions et interdisent une baseline defendable pour le
coeur du chat.

Ce chantier ne consiste pas a faire passer les tests par affaiblissement. Il
doit etablir, pour chaque cas rouge, si le comportement courant ou l'attente du
test est la source du desalignement, puis corriger uniquement la source
prouvee.

## Gate avant 9B

- Aucun sous-lot 9B.0-9B.6 ne commence avant la fermeture de cette TODO.
- Le correctif de continuite de provenance Web est techniquement valide et a
  ete valide en dialogue live par Tof le 14 aout 2026. Son P2 doit etre ferme
  dans la documentation vivante sans modifier le code.
- Le travail de remise au vert part d'une branche dediee creee depuis le HEAD
  applicatif effectivement deploye et audite.
- Une nouvelle panne produit decouverte pendant le triage arrete la famille
  concernee et ouvre un lot correctif separe. Elle n'est pas masquee dans un
  patch tests-only.

## Baseline obligatoire

Avant toute correction:

- [x] Capturer branche, HEAD, parent, upstream et worktree propre.
- [x] Verifier que checkout et code FridaDev execute correspondent.
- [x] Executer la decouverte complete dans le runner hermetique autoritatif,
  sans reseau ni secret reel.
- [x] Capturer le nombre de tests, echecs, erreurs, skips et expected failures.
- [x] Conserver une liste content-free des identifiants `FAIL` et `ERROR`, avec
  une empreinte deterministe.
- [x] Rejouer chaque cas rouge de facon ciblee avant de le classer.
- [x] Ne pas imposer `2549 / 22 / 16` si le HEAD courant differe: toute
  variation doit etre expliquee par le code, les tests ou le runner reels.

Baseline revalidee le 16 aout 2026 au HEAD
`b21239284ed1bca864ddd828a01ef946ad84080a`, parent `4020d5b8`, branche
`FridaV1-Before-9B-Test-Remediation`, upstream `0/0` et worktree propre avant
execution. Le commit courant ne differe du code deploye que par trois fichiers
documentaires. Les sept fichiers runtime critiques controles sont identiques
entre checkout et conteneur; FridaDev est healthy, restart `0`, OOM false.

Runner autoritatif:

```bash
sudo docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --mount type=bind,src=/opt/platform/fridadev/app,dst=/workspace/app,readonly \
  -w /workspace/app -e PYTHONDONTWRITEBYTECODE=1 \
  platform-fridadev-app:local \
  python -m unittest discover
```

Resultat complet: `2549` tests en `8.666 s`, `22` echecs, `16` erreurs,
`0` skip et `0` expected failure signales. Les `34` tests uniques nommes ont
ensuite ete rejoues explicitement dans le meme runner; leurs sous-tests ont
reproduit les memes `38` en-tetes. Empreinte SHA-256 de la liste triee:

`f8e9ac4941fc5d35e0ae11db15eccd64705b484d4a6cdd2ac2769b4e7efa586f`

Identifiants executables exacts:

```text
tests.integration.frontend_admin.test_frontend_hermeneutic_admin_phase6.FrontendHermeneuticAdminPhase6Tests.test_page_scripts_live_in_dedicated_directory_and_use_only_allowed_endpoints
tests.test_llm_client.LlmClientRuntimeSettingsTests.test_or_headers_keeps_internal_caller_marker_local
tests.test_logging_conventions_phase8.LoggingConventionsPhase8Tests.test_repo_has_no_legacy_logger_token
tests.test_memory_store_phase4.MemoryStorePhase4EmbeddingTests.test_record_arbiter_decisions_persists_effective_model_even_if_runtime_changes_before_insert
tests.test_minimal_validation_phase11.MinimalValidationPhase11Tests.test_assert_no_env_fallback_for_persisted_non_secret_fields_accepts_db_seed
tests.test_minimal_validation_phase9.MinimalValidationPhase9Tests.test_assert_masked_secret_fields_accepts_redacted_secret_payloads
tests.test_minimal_validation_phase9.MinimalValidationPhase9Tests.test_check_api_smoke_calls_admin_endpoints_without_admin_token_header
tests.test_minimal_validation_phase9.MinimalValidationPhase9Tests.test_check_api_smoke_verifies_admin_route_and_admin_old_absence
tests.test_minimal_validation_phase9.MinimalValidationPhase9Tests.test_check_ui_assets_requires_new_admin_assets_and_rejects_legacy_assets
tests.test_phase4_transversal.Phase4TransversalTests.test_run_and_compose_runtime_binding_contract_is_unchanged
tests.test_server_chat_active_image_documents_contract.ServerChatActiveImageDocumentsContractTests.test_stream_chat_excludes_active_image_over_provider_payload_cap
tests.test_server_chat_active_image_documents_contract.ServerChatActiveImageDocumentsContractTests.test_stream_chat_injects_active_image_as_multimodal_provider_payload_only
tests.test_server_chat_compact_observability_contract.ServerChatCompactObservabilityContractTests.test_api_chat_emits_hermeneutic_node_insertion_observability_payload
tests.test_server_chat_synthetic_logs_contract.ServerChatSyntheticLogsContractTests.test_api_chat_emits_hard_guard_name_effect_and_final_posture_in_validation_logs
tests.test_server_chat_synthetic_logs_contract.ServerChatSyntheticLogsContractTests.test_api_chat_emits_primary_node_and_validation_agent_synthetic_log_events
tests.test_server_chat_synthetic_logs_contract.ServerChatSyntheticLogsContractTests.test_api_chat_emits_validation_agent_error_stage_without_raw_payload_dump
tests.test_server_chat_synthetic_logs_contract.ServerChatSyntheticLogsContractTests.test_api_chat_persist_response_reports_error_when_messages_are_not_saved
tests.test_server_chat_web_runtime_contract.ServerChatWebRuntimeContractTests.test_api_chat_does_not_auto_activate_web_for_conversational_confirmations_without_manual_flag
tests.test_server_chat_web_runtime_contract.ServerChatWebRuntimeContractTests.test_api_chat_does_not_auto_activate_web_for_pure_verification_request_without_manual_flag
tests.test_server_chat_web_runtime_contract.ServerChatWebRuntimeContractTests.test_api_chat_does_not_auto_activate_web_for_source_link_or_reference_requests_without_manual_flag
tests.test_server_chat_web_runtime_contract.ServerChatWebRuntimeContractTests.test_api_chat_exposes_canonical_web_input_and_reuses_single_web_pass
tests.test_server_chat_web_runtime_contract.ServerChatWebRuntimeContractTests.test_api_chat_passes_web_input_read_state_to_identity_write_callback
tests.test_server_logs_phase3.ServerLogsPhase3Tests.test_prompt_prepared_exposes_effective_memory_prompt_injection_summary
tests.test_server_logs_phase3.ServerLogsPhase3Tests.test_prompt_prepared_exposes_hermeneutic_prompt_injection_without_raw_block
tests.test_server_logs_phase3.ServerLogsPhase3Tests.test_requests_proxy_non_stream_web_reformulation_uses_dedicated_provider_identity
tests.test_server_logs_phase4.ServerLogsPhase4Tests.test_admin_chat_logs_delete_route_rejects_all_logs_scope
tests.test_server_logs_phase4.ServerLogsPhase4Tests.test_admin_chat_logs_delete_route_rejects_turn_without_conversation
tests.test_server_logs_phase6.ServerLogsPhase6Tests.test_admin_chat_logs_export_markdown_rejects_missing_conversation
tests.unit.core.test_temporal_model_truth_closure.TemporalModelTruthClosureTests.test_identity_and_stimmung_cannot_create_temporal_day_claims
tests.unit.logs.test_chat_turn_logger_identity_write.ChatTurnLoggerIdentityWriteTests.test_persist_identity_entries_emits_legacy_diagnostic_identity_write_for_both_sides
tests.unit.logs.test_chat_turn_logger_identity_write.ChatTurnLoggerIdentityWriteTests.test_persist_identity_entries_emits_per_side_legacy_diagnostic_visibility_when_one_side_has_no_data
tests.unit.logs.test_chat_turn_logger_identity_write.ChatTurnLoggerIdentityWriteTests.test_persist_identity_entries_tracks_persisted_count_for_rejected_entries_in_legacy_diagnostic_pipeline
tests.unit.logs.test_log_store_phase3.LogStorePhase3Tests.test_build_turn_pipeline_item_complete_turn_uses_memory_chain_snapshot_content_free
tests.unit.memory.test_hermeneutical_post_stabilization_contract.HermeneuticalPostStabilizationContractTests.test_l2_active_identity_staging_does_not_canonize_role_play_or_irony_window
```

Les tests `conversational_confirmations` et `source_link_or_reference_requests`
produisent chacun trois sous-tests. Ils comptent donc pour six en-tetes dans
la baseline, soit quatre de plus que les `34` identifiants executables uniques.

## Registre de triage

Construire dans ce fichier, avant patch, une ligne par identifiant rouge:

| identifiant | famille | reproduction ciblee | contrat autoritatif | cause prouvee | action | preuve finale | statut |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ERROR minimal_validation_phase9.masked_secret_fields` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR minimal_validation_phase11.non_secret_fields_db_seed` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR log_store_phase3.memory_chain_snapshot` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR minimal_validation_phase9.api_smoke_without_admin_token` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR minimal_validation_phase9.admin_route_and_old_absence` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR minimal_validation_phase9.ui_assets` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR temporal_model_truth_closure.identity_stimmung_day_claims` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR llm_client.internal_caller_marker_local` | F1 | oui | isolation locale des headers internes | `RUNNER_OU_FIXTURE` | secret et vue runtime synthetiques dans le test | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `ERROR identity_write.legacy_diagnostic_both_sides` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR identity_write.legacy_visibility_one_side_empty` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR identity_write.rejected_entries_persisted_count` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR memory_store_phase4.arbiter_effective_model` | F1 | oui | modele effectif fige avant persistance | `RUNNER_OU_FIXTURE` | transport et headers synthetiques locaux | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `ERROR logging_conventions.no_legacy_logger_token` | F1 | oui | absence du token logger legacy | `RUNNER_OU_FIXTURE` | scan Python standard-library avec exclusions conservees | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `ERROR server_logs_phase3.web_reformulation_provider_identity` | F1 | oui | identite provider de reformulation Web | `RUNNER_OU_FIXTURE` | headers provider synthetiques explicites | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `ERROR active_image_documents.over_provider_payload_cap` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `ERROR active_image_documents.multimodal_provider_payload_only` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL server_logs_phase4.delete_rejects_all_logs_scope` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL server_logs_phase4.delete_rejects_turn_without_conversation` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL server_logs_phase6.export_rejects_missing_conversation` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL web_runtime.no_auto_web_confirmation_1` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_confirmation_2` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_confirmation_3` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_pure_verification` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_source_request_1` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_source_request_2` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.no_auto_web_source_request_3` | F2 | oui | Web non demande et capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL synthetic_logs.hard_guard_final_posture` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL compact_observability.hermeneutic_node_insertion` | F1 | oui | summary input absent canonique | `RUNNER_OU_FIXTURE` | summary input synthetique sans DB | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `FAIL synthetic_logs.primary_and_validation_events` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL synthetic_logs.validation_error_without_raw_payload` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL web_runtime.canonical_web_input_single_pass` | F2 | oui | injection Web unique puis capsule terminale | `TEST_OBSOLETE` | assertion structurelle capsule + prefixe Web exact | cible `8/8`; complet `11/12`, aucun ajout | ferme |
| `FAIL web_runtime.identity_callback_read_state` | F1 | oui | callback Identity en mode enforced_all | `RUNNER_OU_FIXTURE` | mode hermeneutique explicite dans la fixture cible | cible `7/7`; complet `19/12`, aucun ajout | ferme |
| `FAIL synthetic_logs.persist_response_save_error` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL identity_staging.role_play_irony_window` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL frontend_hermeneutic_admin.allowed_endpoints` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL server_logs_phase3.memory_prompt_injection_summary` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL server_logs_phase3.hermeneutic_prompt_injection` | a revalider | oui | a etablir | `INCONNU` | aucune | baseline `f8e9ac49` | reproduit |
| `FAIL phase4_transversal.runtime_binding_contract` | F1 | oui | image productible avec `WORKDIR /app` | `RUNNER_OU_FIXTURE` | verifier le Dockerfile, pas le point de montage du runner | cible `7/7`; complet `19/12`, aucun ajout | ferme |

Valeurs admises pour `cause prouvee`:

- `BUG_PRODUIT`;
- `TEST_OBSOLETE`;
- `RUNNER_OU_FIXTURE`;
- `CONTRAT_DOCUMENTAIRE_INCOHERENT`;
- `INCONNU`.

Aucune ligne `INCONNU` ne peut etre fermee ou retiree de la baseline.

## Familles historiques a revalider

Le classement ci-dessous est un point de depart issu de l'audit du 25 juillet,
pas une autorisation de corriger en bloc:

### F1 - Runner et environnement, 7 cas historiques

Hypotheses a revalider: secrets runtime absents, outil `rg` absent de l'image,
chemin `/app` fige alors que le runner monte `/workspace/app`, DB absente, mode
Identity different entre runner hermetique et runtime.

- [x] Rendre les tests hermetiques avec fakes et valeurs synthetiques quand le
  contrat est unitaire.
- [x] Rendre les chemins independants du point de montage.
- [x] Ne jamais injecter un secret reel pour faire passer un test.
- [x] Ne pas transformer silencieusement un test runtime en test unitaire.
- [x] Ne pas ajouter de skip general pour cacher une dependance non preparee.

F1 fermee le 16 aout 2026. Les sept cas ont d'abord ete reproduits dans le
runner hermetique, puis compares au service actif pour distinguer les
dependances de fixture des contrats produit. Le classement exact est:

- trois tests appelaient une resolution de secret ou de headers runtime sans
  preparer de valeurs synthetiques;
- un test dependait de `rg`, absent de l'image de test;
- un test confondait le `WORKDIR /app` de l'image avec le point de montage
  `/workspace/app` du runner;
- un test dependait d'un summary input DB non prepare;
- un test dependait du mode Identity actif au lieu de fixer `enforced_all`.

Les sept tests cibles passent `7/7` sans reseau ni secret reel. La decouverte
complete passe de `2549 / 22 echecs / 16 erreurs / 38 en-tetes` a
`2549 / 19 echecs / 12 erreurs / 31 en-tetes`. Les sept en-tetes F1 sont les
seuls retires et aucun nouvel identifiant n'apparait. `rg` n'a ete installe ni
sur l'hote ni dans l'image: le scan de convention utilise desormais
`pathlib`, ce qui supprime une dependance outil non necessaire sans modifier
le produit.

### F2 - Attentes Web anterieures a la capsule, 8 cas historiques

Hypothese a revalider: les tests prouvent encore l'absence d'auto-Web, mais
comparent le prompt complet sans accepter la capsule de continuite deja
contractuelle.

- [x] Preserver les assertions qui prouvent qu'aucune recherche Web n'est
  lancee.
- [x] Tester la presence et la position de la capsule sans snapshoter du
  contenu utilisateur brut.
- [x] Ne pas retirer la capsule du runtime pour satisfaire une attente ancienne.
- [x] Verifier les cas Web off, contexte vide, injection effective et legacy.

F2 fermee le 16 aout 2026. Les huit en-tetes provenaient de quatre methodes
dont deux produisent trois sous-tests. Toutes comparaient le payload final a
la seule fenetre conversationnelle, alors que le contrat vivant exige une
Continuity Capsule `system` V1 unique, injectee en derniere position avant
l'appel du modele principal.

Le correctif reste tests-only. Il conserve l'egalite exacte de tous les
messages precedant la capsule et les gardes qui font echouer le test si une
recherche Web non demandee est lancee. Il exige separement une seule capsule,
terminale, de role `system` et de version `continuity_capsule_v1`, sans
snapshoter son texte complet. Les chemins Web off, tour conceptuel propre,
recherche manuelle sans contexte, injection Web effective et absence d'appel
au builder legacy sont couverts.

Preuves hermetiques sans reseau ni provider: huit reproductions historiques
vertes, module Web `8/8`, et six mutants de l'assertion capsule rejetes sur
six. La decouverte complete passe de
`2549 / 19 echecs / 12 erreurs / 31 en-tetes` a
`2549 / 11 echecs / 12 erreurs / 23 en-tetes`. Les huit seuls en-tetes retires
sont ceux de F2; aucun nouvel identifiant n'apparait. Aucun code runtime,
prompt, contrat produit ou configuration n'est modifie.

### F3 - Contrats d'observabilite, 12 cas historiques

Hypothese a revalider: les attentes exigent des champs supprimes, renommes ou
rediges par les contrats content-free et default-deny courants.

- [ ] Identifier pour chaque champ le sink et le schema vivant autoritatifs.
- [ ] Corriger le test si le champ est legitimement interdit ou renomme.
- [ ] Corriger le code seulement si le contrat vivant exige encore le champ.
- [ ] Ne reintroduire aucun contenu, prompt, query, URL, exception brute ou
  identifiant sensible dans une surface content-free.
- [ ] Conserver la politique distincte des logs serveur prives Identity/Memory.

### F4 - Validation minimale, 5 cas historiques

Hypotheses a revalider: attentes anciennes sur secret Agenda, referer de
reformulation Web, matrice de settings, marqueur UI et champ du modele
principal.

- [ ] Comparer chaque attente au schema runtime courant et au contrat vivant.
- [ ] Distinguer validation offline, image de test et configuration runtime.
- [ ] Ne pas retablir une compatibilite obsolete uniquement pour le test.
- [ ] Conserver une sortie content-free et des reason codes stables.

### F5 - Erreurs admin anciennes, 3 cas historiques

Hypothese a revalider: les tests attendent des messages detailles anterieurs
aux erreurs generiques content-free.

- [ ] Verifier statut HTTP, reason code et schema public courant.
- [ ] Ne pas reexposer de texte d'exception ou de detail prive.
- [ ] Mettre a jour les attentes seulement apres preuve du contrat actif.

### F6 - Contrats isoles, 3 cas historiques

Hypotheses a revalider: helper temporel retire, statut Identity requalifie et
marqueur frontend obsolete.

- [ ] Verifier qu'aucun appel runtime vivant ne depend du helper retire.
- [ ] Verifier le statut Identity contre le mode et les guards courants.
- [ ] Verifier le marqueur frontend contre le DOM et le contrat actifs.
- [ ] Ne pas recreer une API morte ou un texte UI obsolete pour satisfaire le
  test.

## Regles de correction

- Une famille a la fois, avec reproduction rouge ciblee puis preuve verte.
- Lire code, appelants, tests, contrat vivant et documentation avant le patch.
- Preferer une fixture partagee explicite a des valeurs copiees dans plusieurs
  tests.
- Ne jamais supprimer un test sans prouver que sa responsabilite est couverte
  ailleurs avec une sensibilite equivalente ou superieure.
- Interdiction de masquer une panne par `skip`, `expectedFailure`, `xfail`,
  broad `except`, timeout augmente, assertion retiree ou comparaison rendue
  triviale.
- Aucun acces Internet, provider reel, secret reel ou donnee operateur.
- Aucun changement produit, prompt, route, provider, DB, Caddy, Docker global,
  Memory, Identity, Agenda ou Biblio dans un correctif tests-only.
- Tout changement runtime necessaire revele un lot correctif distinct, borne et
  valide avant de reprendre cette TODO.
- Apres chaque famille: suites ciblees, suites voisines, decouverte complete,
  comparaison de la liste content-free et `git diff --check`.
- Un commit ne melange pas plusieurs causes sans lien.

## Auto-audit obligatoire par famille

- [ ] Le test echouait bien avant la correction.
- [ ] Le comportement attendu vient d'une source de verite courante.
- [ ] Le test corrige echouerait encore si le bug protege etait reintroduit.
- [ ] Aucun test voisin n'a ete affaibli, supprime ou ignore.
- [ ] Aucun nombre, chemin, ordre ou texte interne instable n'est fige sans
  raison contractuelle.
- [ ] Aucun contenu sensible n'entre dans fixture, snapshot, diff ou rapport.
- [ ] Le patch ne commence aucun refactor 9B.

## Condition de sortie

La TODO ne peut etre fermee que si:

- [ ] Le registre contient tous les identifiants de la baseline et aucun
  `INCONNU`.
- [ ] Chaque ancienne panne est reproduite, expliquee et corrigee a sa source.
- [ ] La decouverte complete termine avec `0` echec et `0` erreur.
- [ ] Le nombre de skips et expected failures n'augmente pas.
- [ ] Le nombre total de tests et toute variation sont expliques.
- [ ] Les suites critiques chat, Web, observabilite, admin, validation minimale,
  Identity et frontend sont vertes separement.
- [ ] La route map et les golden tests du Lot 9 restent verts.
- [ ] Le P2 de continuite Web est documente ferme par audit technique et
  validation live utilisateur.
- [ ] La roadmap Lot 9 pointe vers la preuve finale et degele explicitement
  9B.0.
- [ ] Le worktree final est propre et la branche est alignee avec son upstream
  apres livraison autorisee.

Statut de sortie attendu:

`SUITE COMPLETE VERTE - PREREQUIS AVANT 9B FERME`
