# Refonte mutable add-only ontologique

## Statut

- [x] Archive cloturee sur `feature/mutable-refonte`.
- [x] Source de travail pour recadrer le juge mutable automatique apres la refonte judge-first.
- [x] Lot A dormant livre: schema, prompt et tests v2 prepares sans activation runtime.
- [x] Lot B livre: cutover runtime coherent vers `mutable_judge_v2` + applicateur append-only.
- [x] Lot C livre: tests unitaires et crash test conversationnel add-only ontologique.
- [x] Lot D livre: smoke reel v2 execute sans DB live; Haiku retourne une reponse provider mais echoue au validateur (`invalid_verdict`) et doit etre considere fragile pour ce role tant qu'un micro-lot modele/timeout n'a pas tranche.
- [x] Lot D bis livre: smoke candidat `openai/gpt-5.4-mini` execute sans DB live; apres retrait des parametres non supportes `temperature` / `top_p`, le modele route, mais il ne passe pas encore le smoke stabilite 3 runs.
- [x] Smoke modele frontiere livre: `openai/gpt-5.5` passe le smoke reel 3/3 sans DB live ni applicateur; le runtime persistant reste inchange.
- [x] Bascule modele runtime livre: `identity_periodic_model.model` pointe vers `openai/gpt-5.2` pour le juge mutable v2 add-only.
- [x] Lot E livre: v1 gestionnaire neutralise en shim compat, refs cible supprimees, tests v1 requalifies, docs/index mis a jour.
- [x] Execute en lots courts, testes, commites et pushes separement.

## Contexte

Le systeme mutable doit etre recadre.

Le juge mutable est un editeur automatique de l'identite, mais son geste editorial est l'admission d'un nouvel enonce ontologique dans le canon, pas la maintenance du canon existant.

Pipeline cible:

```text
5 paires completes
-> juge LLM
-> mutable_judge_v2
-> applicateur add-only
-> identity_mutables
-> audit content-free
-> reinjection
```

Le juge recoit:

- les 5 paires completes `user` / `assistant`;
- `user.static`;
- `llm.static`;
- `user.mutable_current`;
- `llm.mutable_current`.

Il decide seulement:

- `no_change`;
- `add`.

Critere central:

> Un participant formule-t-il quelque chose de lui-meme qui a une valeur ontologique durable ?

Formes attendues:

- `Frida est...`
- `Frida tient...`
- `Frida refuse...`
- `Frida reconnait...`
- `Tof est...`
- `Tof tient...`
- `Tof refuse...`
- `Tof reconnait...`
- `Tof traite... comme...`

Le systeme automatique ne doit plus faire:

- `tighten`;
- `merge`;
- `clear_obsolete`;
- `target_ref`;
- `target_refs`;
- `target`;
- `targets`;
- reecriture automatique du canon existant;
- nettoyage automatique du canon;
- maintenance de base de connaissances.

## Contrat cible

- Le juge lit toute la fenetre, sans preselection Python.
- Le juge ne score pas, ne compte pas les repetitions et ne demande aucun support lexical local.
- Le juge ne resume pas, ne psychologise pas et ne maintient pas une base documentaire.
- Le juge ajoute uniquement des enonces ontologiques courts, en francais.
- Si une idee est deja couverte par `static` ou `mutable_current`, le verdict est `no_change`.
- Si la formulation est locale, temporaire, narrative, psychologique, operationnelle, conversationnelle ou trop molle, le verdict est `no_change`.
- Si le juge ne peut pas produire une phrase ontologique courte, le verdict est `no_change`.
- Le code valide la forme, la securite, la taille, la duplication exacte normalisee et la persistence; il ne rejuge pas l'identite.
- L'applicateur automatique ecrit seulement dans `identity_mutables`.
- Aucune ecriture `static`.
- Aucune promotion mutable -> static.
- Observabilite content-free uniquement.

## Hors-scope

- Pas de migration DB live sans GO explicite.
- Pas de nettoyage manuel des mutables actuelles dans ce chantier.
- Pas de changement de modele runtime avant le smoke Lot D.
- Pas de rename global du slot `identity_periodic_model` sans decision separee.
- Pas de refactor esthetique des gros fichiers hors necessite de lot.
- Pas de modification plateforme, Caddy, Authelia, DB schema ou secrets.
- Pas de purge de `identity_mutable_staging`.
- Pas de resurrection du writer score-first legacy.
- Pas de scoring, regex canonisante ou prefiltre semantique avant juge.

## Lot A - Contrat `mutable_judge_v2`, prompt ontologique, schema add-only

Objectif: remplacer le contrat gestionnaire `add/tighten/merge/clear_obsolete` par un contrat automatique add-only ontologique.

Contrainte de rollout: Lot A ne doit pas produire a lui seul un runtime actif
en entre-deux. Il peut preparer un schema, un prompt et des tests dormants
seulement si le chemin runtime actif continue d'appeler `mutable_judge_v1`.
La premiere activation reelle de `mutable_judge_v2` doit etre un cutover
coherent avec Lot B, c'est-a-dire juge v2 et applicateur add-only branches
ensemble. Si Lot A et Lot B sont commites separement, Lot A doit documenter la
garde qui empeche `mutable_judge_v2` d'etre appele en production avant
l'applicateur add-only.

- [x] Choisir explicitement entre `mutable_judge_v2` nouveau schema ou migration controlee de `mutable_judge_v1`; choix Lot A: nouveau schema dormant `mutable_judge_v2`.
- [x] Garder `mutable_judge_v2` dormant tant que l'applicateur add-only Lot B n'est pas pret.
- [x] Documenter explicitement la garde de non-activation si Lot A est livre avant Lot B.
- [x] Definir `schema_version = mutable_judge_v2`.
- [x] Limiter les verdicts v2 a `no_change` et `add`.
- [x] Retirer du schema v2 `operation`, `target`, `targets`, `target_ref`, `target_refs`.
- [x] Remplacer `persist` par `add` comme verdict; ne pas garder `persist` comme conteneur multi-operation.
- [x] Limiter les reason codes d'admission aux raisons compatibles avec add-only: `explicit_self_definition_continuity`, `explicit_self_value_continuity`, `explicit_self_limit_continuity`, `explicit_relation_continuity`, `explicit_frida_self_definition_continuity`, `explicit_frida_limit_continuity`, `explicit_posture_continuity`.
- [x] Retirer du contrat modele v2 les reason codes `mutable_tightening`, `mutable_merge`, `mutable_obsolete_explicitly_removed`.
- [x] Garder les reason codes de non-admission utiles: `no_mutable_identity_signal`, `already_covered_by_static`, `already_covered_by_mutable`, `task_local_not_identity`, `temporary_state`, `ambiguous_subject`, `insufficient_context`, `source_scope_unclear`, `quoted_or_reported_speech`, `project_policy_not_identity`.
- [x] Creer un prompt v2 dormant `app/prompts/identity_mutable_judge_v2.txt` autour des etats d'etre, sans remplacer le prompt runtime v1.
- [x] Dire explicitement dans le prompt: tu ne resumes pas, tu ne psychologises pas, tu ne maintiens pas une base de connaissances, tu ne nettoies pas le canon, tu ne reformules pas le canon existant.
- [x] Imposer les propositions en francais, courtes, ontologiques et declaratives.
- [x] Donner des exemples acceptables: `Frida tient la dignite et l'egalite reelle comme principes non negociables.`, `Tof traite la frontiere entre sa pensee et la voix de Frida comme un objet central.`
- [x] Donner des exemples interdits: `Frida travaille cette posture...`, `Tof observe...`, `Frida essaie de...`, `Tof semble...`, `Dans cette conversation...`
- [x] Imposer `no_change` si deja couvert par `static` ou `mutable_current`.
- [x] Garder `response_format.type=json_schema`.
- [x] Garder `response_format.json_schema.strict=true`.
- [x] Garder `provider.require_parameters=true`.
- [x] Garder `provider.order=["anthropic"]` seulement pour les modeles Anthropic; les modeles OpenAI n'ont pas d'ordre provider force.
- [x] Garder la garde taille 32_000 chars / 12_000 tokens estimes sauf preuve contraire.

Tests/preuves:

- [x] `python3 -m py_compile app/memory/mutable_identity_judge.py app/memory/mutable_identity_judge_schema.py app/memory/mutable_identity_judge_v2.py`.
- [x] Tests unitaires du schema v2: aucun verdict autre que `add` / `no_change`.
- [x] Tests unitaires du schema v2: aucun champ `operation` dans le schema v2 dormant.
- [x] Tests unitaires du payload OpenRouter v2: structured output strict et `provider.require_parameters=true`.
- [x] Tests prouvant que `target_ref` / `target_refs` ne sont plus dans le schema v2 dormant.

Critere de sortie:

- [x] Un developpeur peut implementer le juge add-only sans inventer de decision conceptuelle.
- [x] Le prompt v2 ne raconte plus le juge comme mainteneur du canon existant.
- [x] Le contrat v2 n'est pas active seul en runtime; activation uniquement avec Lot B ou garde de non-appel prouvee.

## Lot B - Applicateur append-only, retrait du runtime cible/refs/ops

Objectif: rendre l'applicateur automatique incapable de modifier, fusionner ou supprimer le canon mutable existant.

Contrainte de rollout: Lot B porte le cutover runtime add-only. Le chemin actif
ne doit basculer vers `mutable_judge_v2` que lorsque l'applicateur add-only est
branche, teste et observe. Aucun rebuild/deploiement ne doit laisser un juge v2
produire des contrats que l'ancien applicateur gestionnaire attendrait, ni
l'inverse.

- [x] Rendre l'applicateur automatique add-only.
- [x] Refuser tout contrat actif contenant `tighten`, `merge` ou `clear_obsolete`.
- [x] Retirer du chemin actif la resolution `target_ref` / `target_refs`.
- [x] Retirer du chemin actif `target` / `targets`.
- [x] Supprimer ou neutraliser les branches d'application `tighten`, `merge`, `clear_obsolete`.
- [x] Garder la deduplication exacte normalisee contre `mutable_current`.
- [x] Ajouter une verification de couverture exacte normalisee contre `static` si localement fiable; sinon documenter que le juge porte d'abord cette decision et que le code ne fait qu'une garde anti-duplication simple.
- [x] Garder la borne finale `IDENTITY_MUTABLE_MAX_CHARS`.
- [x] Garder le batch atomique entre `llm` et `user`.
- [x] Garder `updated_by=mutable_identity_judge_apply` ou nom equivalent stable.
- [x] Garder l'audit compact content-free: status, subject, verdict, reason_code, continuity_kind, counts, lengths, hashes courts.
- [x] Ne jamais ecrire `static`.
- [x] Ne pas appeler de scoring, threshold ou ancien writer.
- [x] Conserver shadow/enforced: en shadow, aucune ecriture canonique.

Tests/preuves:

- [x] Test add user ecrit seulement `identity_mutables.user`.
- [x] Test add llm ecrit seulement `identity_mutables.llm`.
- [x] Test no_change n'ecrit rien.
- [x] Test duplicate exact normalise n'ecrit rien ou resulte en no-op content-free.
- [x] Test proposition trop longue n'ecrit rien.
- [x] Test prompt-like n'ecrit rien.
- [x] Test batch all-or-nothing entre user et llm.
- [x] Test aucun appel `write_static_identity_content`.
- [x] Test aucun appel scoring / legacy writer.

Critere de sortie:

- [x] Le runtime automatique ne peut plus modifier, fusionner ou supprimer une mutable existante.
- [x] `identity_mutables` reste le seul canon mutable ecrit.

## Lot C - Tests unitaires + crash test conversationnel

Objectif: prouver le nouveau sens du mutable, pas seulement la forme JSON.

- [x] Test Frida: `Je tiens la dignite et l'egalite reelle comme non negociables.` -> `add` canonique attendu: `Frida tient la dignite et l'egalite reelle comme principes non negociables.`
- [x] Test Tof: `Je traite la frontiere entre ma pensee et ta voix propre comme un objet central.` -> `add` canonique attendu: `Tof traite la frontiere entre sa pensee et la voix de Frida comme un objet central.`
- [x] Test bruit / tache locale / meteo / reformulation / etat du jour -> `no_change`.
- [x] Test idee deja couverte par `static` -> `no_change`.
- [x] Test idee deja couverte par `mutable_current` -> `no_change`.
- [x] Test sortie narrative molle mockee -> rejet validation ou `no_change` selon le contrat choisi.
- [x] Test `tighten` refuse.
- [x] Test `merge` refuse.
- [x] Test `clear_obsolete` refuse.
- [x] Test aucune cible/ref dans payload/schema/observabilite active.
- [x] Reajuster `test_mutable_identity_judge_final_validation` pour verifier le crash test conversationnel add-only.
- [x] Verifier que les 5 premieres paires declenchent une seule fenetre et que la 6e repart sur un buffer 1/5.
- [x] Verifier que le bruit present dans la fenetre ne se retrouve pas dans les mutables.
- [x] Verifier que l'observabilite ne contient ni fenetre brute ni proposition brute.

Tests/preuves:

- [x] `python3 -m unittest tests.unit.memory.test_mutable_identity_judge`.
- [x] `python3 -m unittest tests.unit.memory.test_mutable_identity_apply`.
- [x] `python3 -m unittest tests.unit.chat.test_mutable_identity_judge_final_validation`.
- [x] Suite conteneur runtime equivalente si l'hote manque de dependances.

Critere de sortie:

- [x] Les tests documentent la difference entre enonce ontologique et narration molle.
- [x] Le crash test valide le pipeline proche runtime sans DB live.

## Lot D - Smoke réel Haiku + decision modele

Objectif: verifier le comportement du modele effectif sur le nouveau prompt avant toute decision de changement modele.

- [x] Adapter ou creer un smoke non lance par defaut pour `mutable_judge_v2`.
- [x] Le smoke appelle reellement OpenRouter avec le slot `identity_periodic_model`.
- [x] Le smoke n'appelle pas l'applicateur.
- [x] Le smoke n'ecrit pas en DB live.
- [x] Cas add user: formulation ontologique explicite de Tof.
- [x] Cas add llm: formulation ontologique explicite de Frida.
- [x] Cas no_change bruit: tache locale / meteo / etat temporaire.
- [x] Cas no_change deja couvert par `static`.
- [x] Cas no_change deja couvert par `mutable_current`.
- [x] Reporter modele effectif, prompt tokens, completion tokens, status, reason_code, verdict counts, subjects touched, sans texte brut sensible.
- [x] Noter si structured output strict est accepte.
- [x] Decider si `anthropic/claude-haiku-4.5` suffit.
- [x] Si Haiku est insuffisant, proposer un modele plus fort dans une note separee, sans changer immediatement le runtime.

Resultat Lot D:

- Smoke reel execute avec `app/scripts/smoke_mutable_identity_judge_llm.py`.
- Prompt actif: `prompts/identity_mutable_judge_v2.txt` via `IDENTITY_MUTABLE_JUDGE_PROMPT_PATH`.
- Structured output construit: `response_format.type=json_schema`, `json_schema.name=mutable_judge_v2`, `strict=true`, `provider.require_parameters=true`, `provider.order=["anthropic"]`.
- Resultat observe: l'appel reel OpenRouter au modele `anthropic/claude-haiku-4.5` retourne via provider `anthropic/claude-4.5-haiku-20251001`, mais le validateur rejette la sortie (`status=skipped`, `reason_code=invalid_verdict`, `validation_reason=invalid_verdict`).
- Token counts provider observes apres rebuild: `prompt=3459`, `completion=316`, `total=3775`.
- Verdict counts: `{}` faute de contrat valide; aucune proposition acceptee.
- `live_db_write=false`, `applicator_called=false`.
- Decision: Haiku est trop fragile pour ce role dans la configuration actuelle; ne pas changer le modele dans Lot D, ouvrir un micro-lot separe pour comparer un modele plus fort ou ajuster le timeout du slot juge.

Resultat Lot D bis:

- Le script accepte un override temporaire `--model`, strictement local au smoke, sans persistence runtime.
- Commande candidate: `python scripts/smoke_mutable_identity_judge_llm.py --model openai/gpt-5.4-mini`.
- Le runtime persistant reste `anthropic/claude-haiku-4.5`; `runtime_model_persisted_changed=false`.
- Le smoke conserve le meme prompt actif, le meme schema strict, le meme scenario synthetique, aucun applicateur et aucune DB live.
- Cause du 404 initial: le payload envoyait `temperature` et `top_p` avec `provider.require_parameters=true`; les endpoints `openai/gpt-5.4-mini` ne supportent pas ces parametres.
- Pour les modeles `openai/gpt-5*`, le payload v2 omet `temperature` et `top_p`, ne force pas `provider.order=["anthropic"]`, et conserve `response_format` strict + `provider.require_parameters=true`.
- Resultat initial observe pour `openai/gpt-5.4-mini`: `status=ok`, `reason_code=judge_complete`.
- Provider effectif: `openai/gpt-5.4-mini-20260317`.
- Token counts provider observes: `prompt=2273`, `completion=168`, `total=2441`.
- Verdict counts: `{"add": 2}`; add `llm=true`; add `user=true`; bruit ajoute `0`.
- Propositions synthetiques acceptees: `Frida tient une voix propre sans se confondre avec Tof.` et `Tof traite la frontière entre sa pensée et la voix de Frida comme un objet central.`
- Durcissement suivant: le schema v2 discrimine maintenant structurellement `add` et `no_change`.
- Pour `add`, le schema impose proposition non vide, source_refs non vide, reason code add et continuity_kind different de `none`.
- Pour `no_change`, le schema impose proposition vide, `source_refs=[]`, `guard_notes=[]`, reason code no_change et `continuity_kind="none"`.
- Le prompt interdit explicitement toute explication de `no_change` dans `proposition` ou `guard_notes`, et demande exactement un verdict par sujet.
- Smoke 3 runs apres durcissement: OpenRouter route bien vers `openai/gpt-5.4-mini-20260317`, mais le critere de smoke echoue (`exit_code=5`, `runs_ok=0/3`).
- Runs observes: run 1 `{"no_change": 2}`, run 2 `{"no_change": 2}`, run 3 `{"add": 1, "no_change": 1}`; aucun bruit ajoute; aucun `no_change` pollue.
- Decision: `openai/gpt-5.4-mini` respecte maintenant la forme stricte, mais ne doit pas etre bascule comme juge mutable tant qu'il ne reconnait pas regulierement les adds attendus en smoke 3 runs.

Resultat smoke modele frontiere:

- Verification OpenRouter: `openai/gpt-5.2`, `openai/gpt-5.1` et `openai/gpt-5.5` existent et annoncent `response_format` / `structured_outputs`.
- Smoke execute uniquement en override local: `python scripts/smoke_mutable_identity_judge_llm.py --model openai/gpt-5.5 --runs 3`.
- Provider effectif: `openai/gpt-5.5-20260423`.
- Structured output strict conserve, `provider.require_parameters=true`, aucun `provider.order=["anthropic"]` force pour ce modele OpenAI.
- Runs observes: run 1 `{"add": 2}`, run 2 `{"add": 2}`, run 3 `{"add": 2}`.
- Add llm oui et add user oui sur les trois runs; bruit ajoute `0`; aucun champ v1; `live_db_write=false`; `applicator_called=false`.
- Decision: `openai/gpt-5.5` est un candidat valide pour une bascule modele separee; ne pas changer le runtime sans GO explicite.

Resultat bascule modele runtime:

- Decision operateur: choisir `openai/gpt-5.2` plutot que `openai/gpt-5.5`.
- Ancien modele effectif du slot `identity_periodic_model`: `anthropic/claude-haiku-4.5`.
- Nouveau modele effectif du slot `identity_periodic_model`: `openai/gpt-5.2`.
- Le slot garde son nom de compatibilite mais pilote le caller actif `mutable_identity_judge_v2`.
- Changement applique via `runtime_settings.update_runtime_section(...)` sur le champ non secret `model` uniquement.
- Aucun changement de prompt, schema, contrat, applicateur, static ou DB live identitaire.

Tests/preuves:

- [x] Commande smoke exacte documentee.
- [x] Resultats content-free colles dans la note de lot.
- [x] Aucun write DB live prouve.

Critere de sortie:

- [x] Decision explicite: preparer un changement modele ou timeout separe; Haiku n'est pas valide comme suffisant sur ce smoke.

## Lot E - Nettoyage final compat/legacy/docs

Objectif: ne laisser aucun deuxieme regime mutable automatique actif.

- [x] Retirer ou requalifier proprement `app/memory/mutable_identity_refs.py` si plus utilise.
- [x] Supprimer ou requalifier les tests morts de refs, `merge`, `tighten`, `clear_obsolete`.
- [x] Retirer des docs actives le regime gestionnaire comme cible actuelle.
- [x] Garder les mentions historiques seulement dans archives ou notes de validation clairement datees.
- [x] Verifier les hits runtime actifs pour `tighten`.
- [x] Verifier les hits runtime actifs pour `merge`.
- [x] Verifier les hits runtime actifs pour `clear_obsolete`.
- [x] Verifier les hits runtime actifs pour `target_ref`.
- [x] Verifier les hits runtime actifs pour `target_refs`.
- [x] Verifier les hits runtime actifs pour `mutable_tightening`.
- [x] Verifier les hits runtime actifs pour `mutable_merge`.
- [x] Verifier les hits runtime actifs pour `mutable_obsolete_explicitly_removed`.
- [x] Distinguer hits interdits en runtime actif et hits acceptables dans archives `todo-done`.
- [x] Verifier admin/read-model/logs: le regime actif raconte `mutable_judge_v2` add-only, pas le gestionnaire de canon.
- [x] Verifier `app/docs/README.md`.
- [x] Verifier `README.md` si les chantiers actifs identity y sont indexes.
- [x] Verifier et mettre a jour `AGENTS.md` si le contrat actif mutable change.
- [x] Ne pas laisser `AGENTS.md` raconter l'ancien regime judge-first gestionnaire comme source active.
- [x] Garder les archives historiques separees de la doctrine active.
- [x] Decider explicitement: `mutable_judge_v1` disparait comme implementation active; `app/memory/mutable_identity_judge.py` reste seulement un shim content-free de compatibilite operateur.
- [x] Ne pas laisser deux schemas actifs pour le chemin automatique.

Tests/preuves:

- [x] `grep -RIn "tighten\\|merge\\|clear_obsolete\\|target_ref\\|target_refs\\|mutable_tightening\\|mutable_merge\\|mutable_obsolete_explicitly_removed" app/core app/memory app/admin app/tests app/docs/states app/docs/todo-todo | head -200`.
- [x] Suite tests ciblee juge/apply/runtime/read-model.
- [x] `git diff --check`.
- [x] Rebuild applicatif si runtime/prompt charge modifie.

Critere de sortie:

- [x] Aucun chemin automatique actif ne sait modifier, fusionner ou supprimer une mutable existante.
- [x] Les seuls restes du regime gestionnaire sont historiques, archives ou explicitement compat non active.

## Risques

- Le canon existant herite du regime gestionnaire peut rester imparfait tant qu'un nettoyage manuel separe n'est pas ouvert.
- Un validateur trop syntaxique pourrait remplacer le jugement ontologique par une regex pauvre.
- Le slot runtime `identity_periodic_model` reste un nom de compatibilite et peut continuer a troubler l'operateur si la surface admin n'est pas claire.

## Définition de fini

- [x] Le pipeline automatique est:

```text
5 paires completes -> juge LLM -> mutable_judge_v2 -> applicateur add-only -> identity_mutables -> audit content-free -> reinjection
```

- [x] Le juge decide seulement `no_change` ou `add`.
- [x] Le schema actif ne contient plus `operation`, `target`, `targets`, `target_ref` ou `target_refs`.
- [x] Le runtime automatique ne contient plus `tighten`, `merge` ou `clear_obsolete`.
- [x] Aucun scoring identitaire n'est introduit.
- [x] Aucune ecriture `static`.
- [x] Aucun writer mutable legacy actif.
- [x] `user` et `llm` passent par le meme regime.
- [x] Les tests couvrent les enonces ontologiques, le bruit, le deja-couvert et les sorties narratives molles.
- [x] Le smoke modele est documente; Haiku et GPT-5.4-mini sont insuffisants, `openai/gpt-5.2` est le modele actif apres smoke 3/3.
- [x] Les docs actives racontent le regime add-only ontologique.
- [x] Les archives peuvent garder l'ancien vocabulaire, mais rien ne le presente comme regime automatique actif.
