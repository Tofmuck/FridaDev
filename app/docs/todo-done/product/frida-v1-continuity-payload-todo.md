# Frida V1 - Continuity Payload TODO

Statut: archive de chantier cloture
Date: 2026-06-22
Cloture Lot Z: 2026-06-23
Classement final: `app/docs/todo-done/product/`
Branche de travail initiale: `FridaV1-Continuity-Payload-Audit`

## Objet du chantier

Frida V1 a deja des briques fortes: identity stable et mutable, memoire,
resumes, lanes Documents/Notes/Biblio/Agenda/Web, runtime settings et
observabilite content-free.

Le probleme produit restant est plus precis: la continuite de ton, methode,
relation et presence entre conversations reste emergente. Une conversation
longue reconstruit beaucoup par son dialogue recent; une nouvelle conversation
recupere surtout le prompt statique, l'identite, et de la memoire si le
retrieval tombe juste.

Le but de ce chantier est de rendre cette continuite:

- specifiable, sans la confondre avec identity, memory ou summary;
- prouvable, sans capturer de prompt brut ni de payload provider;
- eventuellement injectable, mais seulement apres preuve content-free du
  payload final.

Regle dure: aucun runtime de capsule de continuite ne doit partir avant
livraison et test de `main_payload_manifest_v1`.

## Sources de verite

- Audit principal:
  `app/docs/todo-done/audits/frida-v1-continuity-payload-audit-2026-06-22.md`
- Contre-audit:
  `app/docs/todo-done/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`
- Contrat source-of-truth Continuity Payload:
  `app/docs/states/specs/frida-v1-continuity-payload-contract.md`
- Doctrine voix, identite et reprise apres ecart:
  `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Contrat source-of-truth mutable judge:
  `app/docs/states/specs/mutable-identity-judge-contract.md`
- Plan doctrinal `static` / `mutable`:
  `app/docs/states/policies/identity-new-contract-plan.md`
- Archive operatoire identity:
  `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Contrat observabilite agentique:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`
- Roadmap finale produit:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Findings vivants

Chaque finding demarre ouvert. Il ne peut pas etre considere clos sans preuve
content-free relue, testee ou explicitement reportee post-V1.

| Statut | Finding | Lot cible | Critere de cloture court |
| --- | --- | --- | --- |
| - [x] | P1-CONT-01 | Lot 6 puis Lot 7 | Capsule distincte d'identity/memory/summary specifiee, tests artificiels passes; surface runtime bornee, desactivable, rollbackable et observable content-free livree en Lot 7. |
| - [x] | P1-PAYLOAD-01 | Lot 1 puis Lot 2 | `main_payload_manifest_v1` livre et teste sur le payload final apres injections tardives, sans contenu brut. |
| - [x] | P2-SUMMARY-01 | Lot 4 puis Lot 6 | Lot 4 expose le summary comme fenetre content-free; Lot 6 prouve par fixture artificielle que summary seul peut aplatir la nuance et qu'une capsule candidate distincte peut restaurer les traits minimaux sans runtime. |
| - [x] | P2-LANES-01 | Lot 5 | Biblio/Agenda/renderers couverts par la doctrine de voix ou explicitement bornes. |
| - [x] | P2-MEMORY-01 | Lot 4 | Difference arbiter observe vs memoire reellement injectee prouvee dans le manifeste ou les traces. |
| - [x] | P2-WINDOWS-01 | Lot 4 | Fenetres memory, hermeneutic node, Biblio, Agenda et prompt final cartographiees par tailles/compteurs content-free. |
| - [x] | P2-IDENTITY-STAGING-01 | Lot 4 | Staging mutable conversation-scoped documente comme non disponible en nouvelle conversation avant canonisation. |
| - [x] | P2-LANE-PROVENANCE-01 | Lot 2 puis Lot 2.1 | Role provider et role logique distingues par provenance structuree, sans classification souveraine par contenu textuel. |
| - [x] | P2-FINAL-LOCK-POLICY-01 | Lot 5 | Politique de priorite Agenda/Biblio final-lock documentee et testee. |
| - [x] | P2-NOTES-UI-01 | Lot 5 | Statut Notes UI tranche: hors chemin chat courant documente, ou branchement explicite teste. |
| - [x] | P2-OBS-WRITER-01 | Lot 3 puis Lots 3.1/3.2/3.3/4.1 | Guard writer-side schema-first/default-deny strict livre contre cles/payloads dangereux, texte libre sous cles neutres et suffixes textuels inconnus, avec schemas content-free existants preserves et sentinelles anti-fuite. |
| - [x] | P3-SOFT-LIMIT-01 | Lot 4 | Soft limit explique: depassement visible, politique de non-troncation observee, compteurs d'exclusion/troncation a zero. |
| - [x] | P3-NOOP-LANES-01 | Lot 5 | Non-selection Documents/Notes observable ou absence justifiee sans confusion avec lane non instrumentee. |
| - [x] | P3-DOC-01 | Lot 1 puis Lot Z | Docs historiques requalifiees ou indexees avec statuts actifs/archive/stale; index actifs pointent vers le contrat et cette archive. |
| - [x] | P3-TEST-01 | Lot 6 | Tests nouvelle conversation vs longue conversation sur fixtures artificielles, sans contenu utilisateur reel. |
| - [x] | P3-OBS-01 | Lot 6 | Preuve qualitative content-free definie: presence jugee par fixtures artificielles et signaux bornes. |
| - [x] | P3-OFFLINE-PAYLOAD-EXPORT-01 | Lot 2 puis Lot Z | Export local historique non retenu comme preuve de cloture; remplace pour ce chantier par `main_payload_manifest_v1` et artefact Lot Z content-free. |

## Lots

### Lot 0 - Cadrage TODO actif

- [x] Creer cette TODO active produit, rattachee aux audits et sans patch runtime.

Criteres de cloture Lot 0:

- fichier cree dans `app/docs/todo-todo/product/`;
- tous les findings consolides sont presents;
- chaque finding a un lot cible;
- le gate `main_payload_manifest_v1` avant capsule runtime est explicite;
- index/roadmap mis a jour quand ils servent de portes d'entree actives;
- aucun code runtime, test executable, provider live, DB, migration ou reset.

### Lot 1 - Spec source-of-truth Continuity Payload

Docs-only.

- [x] Specifier `main_payload_manifest_v1`: structure, champs autorises,
  champs interdits, roles provider, roles logiques, origine des lanes,
  injections tardives, final locks, budgets, exclusions, hashes courts et
  compteurs.
- [x] Specifier la Continuity Capsule ou nom equivalent: objet, taille,
  version, non-souverainete, contestabilite, rollback et non-objectifs.
- [x] Distinguer strictement capsule, identity stable, identity mutable,
  memoire, resume, observabilite et lanes documentaires.
- [x] Reprendre la doctrine de non-souverainete: la capsule guide la presence,
  elle ne remplace ni le tour courant ni les preuves visibles.
- [x] Graver le no-go runtime: la capsule peut etre specifiee, mais pas
  injectee tant que `main_payload_manifest_v1` n'est pas livre et teste.
- [x] Requalifier les docs historiques utiles sans rouvrir les archives
  identitaires ou observabilite.

Statut 2026-06-22: Lot 1 livre par
`app/docs/states/specs/frida-v1-continuity-payload-contract.md`. Aucun finding
n'est clos par ce lot docs-only; Lot 2+ et Lot Z restent non coches.

### Lot 2 - Manifest payload content-free runtime/fake

Objectif: implementer et tester `main_payload_manifest_v1`, sans contenu brut.

- [x] Prouver l'ordre final du payload apres toutes les injections tardives.
- [x] Exposer la sequence des roles provider et des roles logiques.
- [x] Exposer l'origine des lanes: human user, system context, memory,
  summary, document, note, biblio, agenda, web, adobe ou autre origine
  allowlistee.
- [x] Exposer final locks et assistant override sans recopier la reponse.
- [x] Exposer budgets, exclusions, tailles, compteurs et empreintes seulement
  selon la politique de hachage du contrat: pas de hash stable naif sur contenu
  textuel sensible.
- [x] Poser des flags explicites: `raw_prompt_included=false`,
  `raw_message_included=false`, `raw_lane_content_included=false`,
  `raw_provider_payload_included=false`, `raw_content_included=false`,
  `raw_secret_included=false`.
- [x] Verifier `app/scripts/export_main_prompt_payload.py`: lu en Lot 2,
  non retenu comme preuve content-free car il exporte encore un prompt redacted
  riche; remplace pour ce chantier par `main_payload_manifest_v1`.
- [x] Couvrir au minimum nouvelle conversation, conversation longue, resume,
  lanes activees/desactivees et final response lock.

Findings principalement traites: `P1-PAYLOAD-01`,
`P2-LANE-PROVENANCE-01`, `P3-OFFLINE-PAYLOAD-EXPORT-01`.

Statut 2026-06-22: Lot 2 livre par
`app/observability/main_payload_manifest.py`, branche au dernier point de
`app/core/chat_service.py` avant `run_llm_exchange`, projection admin
content-free dans `app/observability/admin_log_projection.py`, et tests
`app/tests/unit/logs/test_main_payload_manifest.py` plus preuve d'integration
dans `app/tests/unit/chat/test_chat_workspace_folder_notes_prompt.py`.

Findings clos par ce lot: `P1-PAYLOAD-01`, `P2-LANE-PROVENANCE-01`.

Correctif Lot 2.1 livre le 2026-06-22:

- [x] Remplacer la provenance de lanes Notes, Documents, Biblio et Adobe par
  des sources structurees capturees autour des injections reelles.
- [x] Prouver que de fausses balises dans un message utilisateur restent
  `user_turn`.
- [x] Aligner les roles `identity_stable` et `identity_mutable` du premier
  message systeme sur les statuts identity reellement selectionnes.
- [x] Extraire le manifeste et la projection admin en modules de responsabilite
  claire, sans `utils.py` ni `helpers.py`.

Decision Lot Z sur `P3-OFFLINE-PAYLOAD-EXPORT-01`: le script offline historique
est non-runtime et n'a pas ete appele pour la cloture. Il reste trop riche pour
servir de preuve content-free de continuite; le manifeste runtime
`main_payload_manifest_v1` et l'artefact Lot Z le remplacent pour ce chantier.
Un nettoyage post-V1 pourra le deprecier ou le rendre conforme, sans bloquer la
cloture Continuity Payload.

### Lot 3 - Garde writer-side observability

Objectif: eviter qu'une future instrumentation payload introduise du contenu
brut dans l'observabilite.

- [x] Durcir `chat_turn_logger` ou l'equivalent writer-side par schema,
  allowlist ou rejet explicite des cles dangereuses.
- [x] Couvrir les cles de risque: messages, prompt, content, payload,
  provider payload, raw, base64/data URL et secrets.
- [x] Ajouter des sentinelles anti-fuite sur les chemins writer et projections
  admin pertinentes.
- [x] Preserver les vraies pannes visibles: un rejet de payload dangereux ne
  doit pas devenir un faux succes.

Finding traite: `P2-OBS-WRITER-01`.

Statut 2026-06-22: Lot 3 livre par
`app/observability/observability_payload_guard.py`, branche dans
`app/observability/chat_turn_logger.py` avant l'ecriture via `log_store`.
Comportement retenu: un payload dangereux est remplace avant stockage par un
evenement de garde content-free avec `reason_code=observability_payload_rejected`;
un statut demande `ok` devient `refused`, et un statut deja non-OK reste visible.
Le manifeste `main_payload_manifest_v1` reste accepte seulement s'il respecte
son contrat content-free.

Correctif Lot 3.1 livre le 2026-06-22:

- [x] Passer la garde writer-side en politique schema-first/default-deny.
- [x] Refuser une chaine libre sous cle neutre ou inconnue.
- [x] Refuser les sous-mappings manifestes inattendus dans `budgets`,
  `windows` et `runtime_settings`.
- [x] Garder le manifeste reel produit par `build_main_payload_manifest()`
  accepte quand il respecte le schema content-free.
- [x] Prouver qu'un `status=ok` avec payload refuse devient `refused` avant
  stockage.

Correctif Lot 3.2 livre le 2026-06-22:

- [x] Preserver les payloads content-free existants `context_build`.
- [x] Preserver `web_search` skipped avec `query_preview=""` sans autoriser de
  preview non vide.
- [x] Preserver les erreurs avec `error_code` et `error_class` content-free,
  sans stocker `message_short` brut.
- [x] Convertir les anciens champs Web sensibles ou correlables en compteurs et
  flags: pas d'URL brute, pas de hash stable de requete/prompt/message dans
  l'evenement writer-side.
- [x] Prouver que les rejets de garde ne deviennent pas du bruit sur les
  evenements normaux.

Correctif Lot 3.3 livre le 2026-06-22:

- [x] Supprimer l'acceptation par suffixe textuel generique pour les cles
  inconnues.
- [x] Refuser les probes `private_requested`, `private_code`,
  `private_reason`, `private_status`, `private_mode` et toute cle inconnue de
  string safe-code.
- [x] Conserver les payloads legitimes Lot 3.2: `context_build`,
  `web_search`, `emit_error` et `main_payload_manifest_v1`.

Tests de reference Lot 3:

- `app/tests/unit/logs/test_observability_payload_guard.py`
- `app/tests/unit/logs/test_chat_turn_logger_core_contract.py`
- `app/tests/unit/logs/test_chat_turn_logger_web_search.py`

Finding clos par ce lot apres Lot 3.3: `P2-OBS-WRITER-01`.

### Lot 4 - Fenetres, summary, memory, staging

Objectif: cadrer et prouver ce que chaque sous-systeme voit.

- [x] Cartographier les fenetres recent dialogue du prompt principal, memory,
  hermeneutic node, Biblio et Agenda.
- [x] Prouver dans le manifeste ou l'observabilite les tailles, periodes,
  roles et compteurs content-free de ces fenetres, sans empreinte stable de
  contenu sensible.
- [x] Documenter le mode memory `shadow`: decisions arbiter observees vs
  contenu effectivement injecte.
- [x] Qualifier l'effet du summary sur la continuite de voix et les rituels
  de travail: le manifeste expose le summary et declare la nuance de voix
  `not_available` / `summary_style_not_scored`.
- [x] Documenter la mutable identity staging comme conversation-scoped avant
  canonisation.
- [x] Traiter le soft token limit: politique assumee, preuve de signal, ou
  durcissement borne.

Findings traites: `P2-SUMMARY-01`, `P2-MEMORY-01`, `P2-WINDOWS-01`,
`P2-IDENTITY-STAGING-01`, `P3-SOFT-LIMIT-01`.

Statut 2026-06-22: Lot 4 livre par enrichissement de
`main_payload_manifest_v1` dans `app/observability/main_payload_manifest.py`
et `app/observability/main_payload_manifest_windows.py`, avec schema writer
guard et projection admin alignes. Les fenetres `prompt_final`, `conversation`,
`recent_context`, `recent_window`, `summary`, `memory`, `hermeneutic_node`,
`identity_staging`, `biblio_recent_dialogue` et `agenda_recent_dialogue`
exposent statuts, origines, compteurs, selection, flags raw a false et reason
codes content-free.

Preuves principales:

- `memory` distingue `retrieved_count`, `arbiter_observed_count`,
  `prompt_injected_count`, `injection_source` et `arbiter_controls_injection`;
- `identity_staging` est declare `not_available` avant reponse, avec
  `staging_scope=conversation_scoped` et `canonization_stage=post_response`;
- `summary` expose presence, periode et taille, mais garde
  `voice_continuity_status=not_available`;
- `budgets.prompt` expose `prompt_soft_token_limit`,
  `prompt_soft_limit_exceeded`, `dialogue_messages_truncated=false`,
  `excluded_count=0` et `soft_limit_policy=observability_only_no_prompt_exclusion`.

Findings clos par ce lot: `P2-MEMORY-01`, `P2-WINDOWS-01`,
`P2-IDENTITY-STAGING-01`, `P3-SOFT-LIMIT-01`.

Etat apres Lot 4: `P2-SUMMARY-01` restait volontairement ouvert. Lot 4 prouvait
que le resume etait visible et que la nuance de voix n'etait pas mesuree; la
cloture a ensuite ete faite en Lot 6 par fixtures artificielles post-resume.

Correctif Lot 4.1 livre le 2026-06-22:

- [x] Preserver les payloads content-free legitimes introduits ou exposes par
  Lot 4: `prompt_prepared`, `hermeneutic_node_insertion`,
  `validation_agent`, `stimmung_agent`, Biblio, Agenda, summaries et `llm_call`
  ne doivent plus devenir des `observability_payload_rejected` quand leur
  schema est borne.
- [x] Garder la garde writer-side schema-first/default-deny: aucune cle
  inconnue, string libre, URL brute, cause brute, prompt/message/content ou
  payload provider brut n'est autorise.
- [x] Remplacer dans les payloads compacts Web et validation les champs bruts
  restants par presence, longueur, domaine, compteurs et flags
  `*_included=false`.
- [x] Reduire l'estimation tokens du manifeste a une estimation globale du
  prompt final, reutilisee par `messages`, `windows.prompt_final` et
  `budgets.prompt`, au lieu de multiplier les appels au compteur.

Findings Lot 4.1: le finding P2 de bruit writer-side sur payloads legitimes est
traite par schemas explicites; le finding P3 de multiplication du compteur de
tokens est traite par estimation prompt-level unique. Aucun Lot 5+ n'est ouvert.

Correctif Lot 4.2 livre le 2026-06-22:

- [x] Supprimer `sha256_12` de `hermeneutic_prompt_injection`: le bloc
  hermeneutique est un texte injecte dans le prompt et ne doit pas recevoir de
  hash stable court.
- [x] Remplacer cette empreinte par des flags content-free:
  `fingerprint_present=false`, `fingerprint_included=false`,
  `prompt_block_hash_included=false`, `raw_content_included=false`.
- [x] Durcir la garde writer-side pour refuser une valeur renseignee sous la
  cle generique `sha256_12`, tout en conservant hors scope les placeholders
  vides et les cles qualifiees existantes deja justifiees par d'autres
  observabilites.
- [x] Prouver que le bloc brut et son hash ne sont pas exposes.

Finding Lot 4.2: le P2 residuel de hash stable sur bloc de prompt
hermeneutique est traite. Aucun Lot 5+ n'est ouvert.

### Lot 5 - Lanes et conflits

Objectif: rendre les lanes compatibles avec la continuite de voix.

- [x] Declarer la politique de conflit Agenda/Biblio final-lock.
- [x] Tester la priorite ou l'arbitrage final-lock retenu.
- [x] Couvrir les renderers/agents de lane par bornage content-free; doctrine
  qualitative de voix renvoyee Lot 6.
- [x] Trancher le statut Notes UI: non branche chat courant documente ou
  branchement explicite.
- [x] Ajouter ou justifier les no-op Documents/Notes quand rien n'est
  selectionne.
- [x] Verifier que les lanes ne masquent pas l'origine logique du contexte.

Findings traites: `P2-LANES-01`, `P2-FINAL-LOCK-POLICY-01`,
`P2-NOTES-UI-01`, `P3-NOOP-LANES-01`.

Statut 2026-06-22: Lot 5 livre par enrichissement de
`main_payload_manifest_v1`:

- `lane_conflicts` expose `priority_policy=agenda_over_biblio`, candidats
  Agenda/Biblio, source selectionnee, source supprimee par priorite,
  `message_lane_status_mismatch_count` et `implicit_injection_detected=false`.
- `lane_statuses.agenda_lane` et `lane_statuses.biblio_lane` indiquent si un
  final lock est present, selectionne ou supprime par priorite.
- Tests fakes couvrent Agenda lock seul, Biblio lock seul et conflit
  Agenda+Biblio avec Agenda prioritaire.
- Correctif Lot 5.1: la branche defensive Agenda+Biblio avec source
  selectionnee non-Agenda est maintenant `status=failed` avec
  `reason_code=final_lock_priority_unexpected`; elle ne peut plus etre lue
  comme un conflit nominal `ok`.
- Documents/Notes/Exports/Images restent visibles comme no-op
  `not_selected` ou `not_applicable` quand aucune selection n'existe.
- Notes UI est tranche content-free: le backend chat supporte
  `workspace_note_id(s)`, mais le frontend courant `app/web/app.js` ne les
  envoie pas; aucune injection Notes implicite n'est donc vendue.
- La continuite qualitative de voix des renderers reste hors Lot 5 et sera
  prouvee en Lot 6 sur fixtures artificielles.

### Lot 6 - Spec/tests de Continuity Capsule

Avant runtime reel, prouver la continuite sur donnees artificielles.

- [x] Ecrire des fixtures sans contenu utilisateur reel.
- [x] Tester nouvelle conversation vs conversation longue.
- [x] Tester une conversation apres resume.
- [x] Tester une conversation sans memoire ou avec lanes non selectionnees.
- [x] Prouver que la capsule reste distincte d'identity, memory et summary.
- [x] Prouver que la presence qualitative peut etre jugee sans provider live
  obligatoire.
- [x] Prouver que les logs et artefacts restent content-free.

Findings traites par Lot 6: `P1-CONT-01` partiel, `P2-SUMMARY-01`,
`P3-TEST-01`, `P3-OBS-01`.

Statut 2026-06-23: Lot 6 livre par fixtures unitaires artificielles dans
`app/tests/unit/continuity/test_continuity_payload_fixtures.py`.

Preuves:

- conversation longue: les traits qualitatifs peuvent etre portes par le
  dialogue recent sans capsule candidate;
- nouvelle conversation sans memoire et lanes non selectionnees: identity seule
  ne suffit pas a recuperer presence, methode, proactivite bornee et cadrage
  relationnel;
- conversation apres resume: le summary conserve un trait de methode et un fait
  de tache, mais aplatit relation, refus, humour/sobriete et reprise; le test
  detecte cet aplatissement;
- capsule candidate: objet test-only distinct de identity, memory et summary,
  porteur de traits qualitatifs seulement, sans fait identitaire, fait memoire
  ou contenu de summary;
- observation qualitative: payload content-free accepte par la garde
  writer-side, avec `model_called=false`, `capsule_runtime_injected=false` et
  flags raw a false.

Findings clos par ce lot: `P2-SUMMARY-01`, `P3-TEST-01`, `P3-OBS-01`.

Etat apres Lot 6: `P1-CONT-01` restait volontairement ouvert. Lot 6 prouvait la
forme et la testabilite d'une capsule candidate, mais ne creait pas encore de
surface runtime durable. La cloture intervient ensuite en Lot 7.

### Lot 7 - Runtime capsule borne

Seulement si Lots 1-6 OK.

- [x] Injecter eventuellement une capsule courte, versionnee et bornee.
- [x] Rendre l'injection desactivable par flag ou settings clairement
  rollbackables.
- [x] Observer la capsule content-free: version, presence, longueur,
  `fingerprint_included=false`, provenance structuree, raw flags a false.
- [x] Garder la capsule non souveraine: le tour courant, les preuves injectees
  et les guards produit priment.
- [x] Ne jamais melanger capsule et identity mutable sans decision doctrinale
  explicite.
- [x] Tester rollback simple et absence de fuite.

Statut 2026-06-23: Lot 7 livre par `app/core/continuity_capsule.py`, branche
dans `app/core/chat_service.py` apres les lanes tardives et apres le choix
Agenda/Biblio du final lock, juste avant `main_payload_manifest_v1` et
`run_llm_exchange`.

Regle runtime:

- config rollbackable sans DB ni migration: `CONTINUITY_CAPSULE_ENABLED`,
  `CONTINUITY_CAPSULE_TEXT`, `CONTINUITY_CAPSULE_VERSION`,
  `CONTINUITY_CAPSULE_MAX_CHARS`, avec fallback env
  `FRIDA_CONTINUITY_CAPSULE_*`;
- defaut: disabled, aucune injection;
- enabled + texte valide et borne: injection d'un message systeme tardif
  `logical_roles=["continuity_capsule"]`, provenance `core.continuity_capsule`,
  stage `late_continuity_capsule`;
- texte absent: `not_configured`, aucune injection;
- texte trop long: `refused`, aucune troncation silencieuse;
- texte contenant URL, credentials/token-like, data URL/base64 evident,
  XML/DAV/WebDAV/CALDAV, chemin absolu/prive ou bloc de cle privee:
  `refused`, `reason_code=continuity_capsule_unsafe_content`, aucune
  injection provider;
- final response lock Agenda/Biblio: `not_selected` avec
  `reason_code=continuity_capsule_final_lock_bypass`, aucune injection et
  `main_model_called=false` coherent.

Observabilite:

- `main_payload_manifest_v1.continuity_capsule` expose presence, enabled,
  version, status, reason_code, `content_chars`, `max_chars`,
  `injected_count`, `raw_capsule_content_included=false`,
  `raw_prompt_included=false`, `raw_content_included=false` et
  `fingerprint_included=false`;
- `lane_statuses.continuity_capsule` expose le meme statut sous forme de lane
  de suivi, sans assimiler la capsule a identity, memory ou summary;
- la projection admin et la garde writer-side acceptent seulement le schema
  content-free; un faux champ `content` sous `continuity_capsule` est refuse.

Preuves principales:

- `app/tests/unit/continuity/test_runtime_continuity_capsule.py` couvre
  disabled, valide, absent, trop long, final-lock bypass et config sans DB;
- `app/tests/unit/logs/test_main_payload_manifest.py` couvre message injecte,
  provenance structuree, final-lock sans injection, projection admin et garde;
- `app/tests/unit/logs/test_observability_payload_guard.py` couvre le rejet
  d'une capsule brute forgee;
- `app/tests/unit/chat/test_chat_workspace_folder_notes_prompt.py` prouve le
  wiring `chat_service` avec capsule activee sans fuite dans states/events.

Finding clos par ce lot: `P1-CONT-01`.

Correctif Lot 7.1:

- [x] Refuser avant provider les textes de capsule contenant des marqueurs
  dangereux evidents: URL, `Bearer`/`Authorization`/cookie, `token=`/
  `api_key=`/`password=`/`secret=`, data URL/base64, XML/DAV/WebDAV/CALDAV,
  chemin absolu/prive ou bloc de cle privee.
- [x] Exposer seulement un statut content-free
  `reason_code=continuity_capsule_unsafe_content`, sans texte refuse dans
  manifeste, projection, garde writer-side ou tests.
- [x] Clarifier la non-souverainete du role provider `system`: le role est
  conserve car il suit le modele courant des lanes de contexte, mais la
  non-souverainete reste une contrainte produit portee par le texte de priorite,
  le defaut disabled, le bypass sous final lock, la taille bornee, l'absence
  d'ecriture identity/memory/summary, la projection content-free et les tests de
  rollback.
- [x] Figer par tests que la capsule reste
  `logical_roles=["continuity_capsule"]` et ne devient jamais
  `identity_stable`, `identity_mutable`, `memory` ou `summary`.

Correctif Lot 7.2:

- [x] Refuser les variantes credential-like avec separateur `:` ou `=`,
  notamment `token:`, `secret:`, `password:`, `api_key:`, `api-key:`,
  `x-api-key:`, `authorization:`, `cookie:` et `set-cookie:`.
- [x] Refuser les URL-like `www.` meme au milieu d'une phrase.
- [x] Refuser les chemins prives/absolus evidents meme au milieu d'une phrase,
  notamment `/Users/...`, `/home/...`, `/root/...`, `/opt/...`, `/var/...`,
  `/etc/...`, `/tmp/...`, `~/...` et chemins Windows absolus.
- [x] Prouver que la capsule normale courte reste acceptee, que le final lock
  bypass reste inchange et que le texte refuse ne sort pas dans
  `as_content_free_dict()`, manifeste, projection admin ou garde writer-side.

### Lot Z - Cloture

- [x] Relire audits, spec, TODO, code et tests.
- [x] Verifier que tous les findings sont clos ou explicitement reportes
  post-V1 avec raison.
- [x] Verifier qu'aucune case ouverte ne reste dans l'archive finale.
- [x] Rejouer scans anti-fuite sur docs, artefacts, diff et logs bornes.
- [x] Verifier que les preuves content-free existent et sont retrouvables.
- [x] Verifier que les tests structuraux et qualitatifs artificiels passent.
- [x] Mettre a jour docs/spec/index avant archivage.
- [x] Archiver cette TODO seulement quand tout est clos ou reporte
  explicitement.

Statut Lot Z 2026-06-23: cloture `met`.

Artefact de cloture:
`app/docs/states/baselines/continuity-payload-smokes/frida-v1-continuity-payload-lotz-closure-20260623T100649Z.jsonl`

Preuves de cloture:

- probe capsule Lot Z conforme: disabled sans injection, normale `ok` avec
  role `system`, final lock `not_selected` sans injection, variantes unsafe
  `refused`;
- tests hote: fixtures qualitatives, capsule runtime, manifeste, garde
  writer-side et `chat_llm_flow` passent;
- tests conteneur: fixtures qualitatives, capsule runtime, manifeste, garde
  writer-side, `chat_llm_flow` et wiring Notes/Capsule passent;
- scans anti-fuite du diff et de l'artefact: pas de prompt brut, dialogue brut,
  capsule brute, payload provider, secret, bytes, base64 ou data URL;
- aucune modification DB, migration, reset, purge, backfill, provider live ou
  plateforme.

Limites post-V1 assumees:

- `app/scripts/export_main_prompt_payload.py` reste un outil offline
  historique trop riche pour servir de preuve content-free; ne pas l'utiliser
  comme substitut a `main_payload_manifest_v1` sans lot separe;
- le role provider `system` de la capsule reste une decision de compatibilite
  avec les lanes de contexte; la non-souverainete est une contrainte produit
  testee et documentee, pas une garantie mecanique du provider;
- une relecture produit post-V1 pourra affiner le texte de capsule et ses
  marqueurs unsafe, sans rouvrir ce chantier de payload.

## No-go globaux

- Pas de capsule runtime avant `main_payload_manifest_v1`.
- Pas de prompt brut.
- Pas de dialogue brut.
- Pas de document, note, passage Biblio, export, image, bytes, base64 ou data
  URL brut.
- Pas de secret, token, cookie, valeur d'en-tete d'autorisation, mot de passe
  applicatif ou URL DAV sensible.
- Pas de provider live pour "voir" le payload.
- Pas de capture ou commit de payload provider.
- Pas de backfill historique implicite.
- Pas de reset, purge, migration ou modification DB dans ce chantier sans lot
  separe et GO explicite.
- Pas de melange identity mutable / continuity capsule sans decision
  doctrinale.
- Pas de test qualitatif fonde sur contenu utilisateur reel.
- Pas de correction opportuniste de Biblio, Agenda, Notes ou Web hors lot
  dedie.

## Critères de clôture Lot Z

Lot Z ne peut cloturer que si:

- tous les findings ont un statut clos ou explicitement reporte post-V1;
- aucune case ouverte ne reste dans l'archive finale;
- les preuves content-free du payload final existent;
- les tests structuraux et qualitatifs artificiels passent;
- les docs, specs, index et roadmap sont coherents;
- le no-go capsule avant manifeste a ete respecte pendant tout le chantier;
- aucune fuite de contenu brut ou secret n'a ete introduite;
- les limites restantes sont ecrites en francais simple et visibles depuis les
  index actifs.

## Traçabilité Lot 0

Patch Lot 0 attendu:

- creation de ce fichier;
- mise a jour des index actifs si necessaire;
- aucune modification runtime;
- aucun test executable lourd;
- aucun provider live;
- aucune capture de payload brut.

Apres ce patch, les lots suivants doivent repartir de cette TODO et ne pas
rouvrir directement les audits comme checklist de travail.

Patch Lot 1 livre:

- contrat source-of-truth cree dans
  `app/docs/states/specs/frida-v1-continuity-payload-contract.md`;
- `main_payload_manifest_v1` defini avant Continuity Capsule;
- no-go runtime capsule avant manifeste livre et teste grave;
- aucun finding marque clos;
- aucune modification runtime.
