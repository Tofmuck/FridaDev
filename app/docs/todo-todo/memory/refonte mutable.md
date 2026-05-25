# Refonte mutable identity - TODO operatoire

Statut: chantier actif.

Spec source-of-truth Lot 0: `app/docs/states/specs/mutable-identity-judge-contract.md`.

Decision source-of-truth du 2026-05-25: le nouveau pipeline mutable ne doit plus scorer l'identite, ne doit plus selectionner des formulations avant le juge et ne doit plus promouvoir implicitement du mutable vers le statique. Le juge LLM lit une fenetre complete de dialogue et decide lui-meme ce qui engage une continuite mutable.

Pipeline cible:

```text
5 paires completes user/assistant
-> juge LLM mutable
-> verdicts
-> applicateur technique
-> identity_mutables
-> audit content-free
-> reinjection static + mutable
```

## Checklist globale

- [ ] Remplacer le contrat actif par `5 paires completes -> juge LLM -> mutable`.
- [ ] Supprimer toute cible de preselection semantique avant le juge.
- [ ] Supprimer le scoring identitaire comme critere d'admission mutable.
- [ ] Garantir un pipeline commun pour `user` et `llm`.
- [ ] Garantir que le juge recoit toute la fenetre de 5 paires, pas seulement des extraits.
- [ ] Garantir que le nouveau juge recoit `user.static`, `user.mutable_current`, `llm.static` et `llm.mutable_current`.
- [ ] Garantir que la refonte mutable n'ecrit que dans `identity_mutables`.
- [ ] Interdire toute ecriture automatique de `static` dans ce chantier.
- [ ] Conserver le canon mutable existant comme canon herite initial, sans migration automatique.
- [x] Retirer le writer mutable score-first du runtime actif.
- [x] Remplacer les surfaces admin/read-model/logs qui presentent le staging long, les scores et les promotions comme regime actif.
- [ ] Prouver que l'observabilite finale reste content-free.
- [ ] Prouver que `Frida_from_herself.md` n'est pas un chantier concurrent actif.
- [ ] Mettre a jour docs/tests/specs pour qu'il ne reste pas de couche morte.

## Existe-t-il un meilleur plan ?

Oui: le meilleur plan est de retirer toute porte algorithmique avant le juge. Une fenetre complete de 5 paires user/assistant devient l'unite minimale de lecture; le juge LLM lit cette fenetre en entier avec le canon courant, puis produit des verdicts. Le code ne choisit pas ce qui merite d'etre lu et ne transforme pas l'identite en force locale mesurable. Il valide seulement la forme, la securite, la taille et l'applicabilite technique.

Ce plan remplace donc toute architecture de type `extraction intelligente de traces -> juge`. Le seul mecanisme avant le juge est la capture technique de paires completes.

## Findings valides avant chantier

- [x] Finding 1 valide: le module de formulation/preselection etait encore trop ingenierie; il doit disparaitre comme etape cible.
- [x] Finding 2 valide: le seuil cible est 5 paires completes, pas une fenetre longue.
- [x] Finding 3 valide: le statique ne doit pas etre modifie par defaut.
- [x] Finding 4 valide: le contenu actuel de `identity_mutables` est un canon herite initial, pas une preuve a remigrer.
- [x] Finding 5 valide: `Frida_from_herself.md` doit etre suspendu jusqu'a la fin de cette refonte.
- [x] Finding 6 valide: ce document doit etre une TODO a cases, avec lots, preuves et criteres de sortie.

## Etat actuel reel a remplacer

Modules actifs constates:

- `app/core/chat_memory_flow.py`
  - `record_identity_entries_for_mode(...)` extrait encore des fragments legacy via `arbiter.extract_identities(turn_pair)`.
  - En mode enforced, il persiste les diagnostics legacy hors canon mutable puis appelle `_run_periodic_identity_agent(...)` comme wrapper de runtime judge-first.
  - `_run_periodic_identity_agent(...)` appelle `memory_identity_periodic_agent.stage_identity_turn_pair(...)` avec `enforce_writes=True` et journalise `mutable_identity_judge_apply`.
  - En mode shadow, il peut observer le juge mais passe `enforce_writes=False`; aucune ecriture canonique mutable n'est autorisee.
- `app/memory/memory_identity_periodic_agent.py`
  - Avant Lot 1, `BUFFER_TARGET_PAIRS = 15`; depuis Lot 1, la cible runtime est `5`.
  - Accumule un buffer dans `identity_mutable_staging`.
  - Depuis Lot 4, appelle `mutable_identity_runtime.run_mutable_identity_window(...)` quand le buffer atteint la cible.
  - Ne depend plus de `memory_identity_periodic_apply.py` et n'appelle plus `apply_periodic_agent_contract(...)` dans le chemin actif.
  - Nettoie le buffer apres retour techniquement termine et valide; preserve le buffer en cas d'erreur transport, JSON/contrat invalide ou fenetre trop grosse.
- `app/memory/mutable_identity_runtime.py`
  - Orchestre `5 paires -> mutable_identity_judge -> mutable_identity_apply`.
  - Construit l'input juge avec les 5 paires completes, les canons static/mutable courants et le budget mutable.
  - En `shadow`, appelle le juge mais ne lance pas l'applicateur.
  - En `enforced`, applique seulement un contrat juge valide; preserve le buffer si le juge ou l'applicateur echoue.
- `app/memory/arbiter.py`
  - `run_mutable_identity_judge(...)` charge `app/prompts/identity_mutable_judge.txt` pour le chemin actif Lot 4.
  - `run_identity_periodic_agent(...)` et `app/prompts/identity_periodic_agent.txt` restent legacy pre-refonte jusqu'au nettoyage Lot 6.
  - Modele et parametres viennent de `identity_periodic_model`: `temperature=0.0`, `top_p=1.0`, `max_tokens=1400`, timeout court, sauf override runtime.
  - Le temporal guard annote les signaux relatifs faibles dans la fenetre, mais ne retire plus le texte avant lecture du modele.
  - Ajoute une garde content-free de taille: si la fenetre depasse les limites configurees, pas d'appel modele, pas d'ecriture mutable, buffer preserve.
- `app/prompts/identity_periodic_agent.txt`
  - Prompt legacy pre-refonte, hors chemin actif Lot 4.
  - Demande des operations locales par sujet.
  - Demande explicitement une grande prudence.
  - Rappelle que Python calcule ensuite des champs de force locale.
  - Exemple meta encore cale sur l'ancienne fenetre longue.
- `app/prompts/identity_mutable_judge.txt`
  - Prompt actif du juge mutable.
  - Declare les verdicts, operations, continuity kinds et reason codes du contrat `mutable_judge_v1`.
- `app/memory/memory_identity_periodic_scoring.py`
  - Calcule une force locale a partir du support lexical, de la recurrence et de la distance dans la fenetre.
  - Donne un verdict deterministe utilise avant application.
- `app/memory/memory_identity_periodic_apply.py`
  - Valide le JSON de l'agent.
  - Recalcule un score par operation.
  - Rejette ou reporte selon verdict local.
  - Peut planifier une promotion du mutable vers le statique.
  - Ecrit `identity_mutables` et peut aussi ecrire le statique avec rollback.
- `app/memory/memory_identity_staging.py`
  - Stocke une fenetre conversationnelle par `conversation_id` dans `identity_mutable_staging`.
  - Fige la fenetre quand la cible est atteinte.
  - Nettoie le buffer apres completion.
- `app/memory/memory_identity_mutables.py`
  - Lit/ecrit le canon mutable actif dans `identity_mutables`.
  - Ecrit l'audit compact dans `identity_mutable_audit`.
- `app/identity/active_identity_projection.py` et `app/identity/identity.py`
  - Reinjection runtime: `static + mutable`.
  - Les mutables sont relues depuis `identity_mutables`.
- `app/identity/identity_governance.py`
  - Depuis micro-correctif Lot 4, expose la fenetre judge-first comme active et requalifie scoring / promotion static comme legacy pre-refonte inactive.
- `app/admin/admin_identity_read_model_service.py`
  - Avant correction Lot 1, exposait encore `promotion_to_static_enabled=true` comme si le writer score-first pouvait promouvoir le mutable vers le statique.
  - Depuis correction pre-Lot 2, expose `promotion_to_static_enabled=false`, `score_first_writer_enabled=false` et des statuts legacy neutralises.
  - Depuis Lot 4, expose `mutable_writer_pipeline=mutable_identity_judge_first`, `mutable_judge_writer_enabled=true`, `promotion_to_static_enabled=false`, `score_first_writer_enabled=false` et les dernieres activites `mutable_identity_judge` compactes.

Tables / structures persistantes:

- `identity_mutables`: canon mutable actif, une ligne par sujet `llm` / `user`.
- `identity_mutable_audit`: audit compact des mutations, sans contenu brut.
- `identity_mutable_staging`: buffer actuel des paires de dialogue et statut du dernier run.
- `identities`, `identity_evidence`, `identity_conflicts`: legacy diagnostic, hors canon actif.
- `state/data/identity/*_identity.txt`: statiques file-backed.

Tests et docs actuels a requalifier:

- `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`
- `app/tests/unit/memory/test_identity_periodic_apply_phase2.py`
- `app/tests/unit/memory/test_identity_periodic_scoring_phase2.py`
- `app/tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`
- `app/tests/test_server_admin_identity_read_model_phase2.py`
- `app/tests/unit/logs/test_chat_turn_logger_phase2.py`
- `app/docs/states/specs/identity-read-model-contract.md`
- `app/docs/states/specs/identity-surface-contract.md`
- `app/docs/states/specs/identity-governance-contract.md`
- `app/docs/states/policies/identity-new-contract-plan.md`
- `app/docs/todo-done/refactors/identity-new-contract-todo.md` comme archive, a ne pas rouvrir mais a ne plus lire comme cible active.

## Critique du modele ancien

- L'ancien regime laisse une operation LLM etre ensuite jugee par un score local.
- L'ancien regime peut bloquer une proposition parce qu'elle n'est pas assez repetee ou pas assez lexicalement supportee.
- L'ancien regime mele extraction legacy, buffer, appel LLM, scoring, applicateur, promotion et persistence.
- L'ancien regime peut faire croire que l'identite devient plus vraie parce qu'une phrase revient dans la fenetre.
- L'ancien regime conserve une promotion mutable -> static comme effet automatique implicite.
- L'ancien regime fait coexister plusieurs vocabulaires: evidence legacy, staging, agent periodic, scoring, promotion, read-model.
- L'ancien regime est observable, mais l'observabilite raconte encore le mauvais modele conceptuel.

Ce qui doit disparaitre a la fin:

- [ ] Scoring local comme juge d'admission mutable.
- [ ] Fenetre longue comme contrat cible.
- [ ] Writer score-first actif.
- [ ] Promotion automatique vers `static`.
- [ ] Labels admin/read-model qui presentent scores et seuils comme regime actif.
- [ ] Tests qui prouvent l'ancien scoring comme comportement attendu.
- [ ] Prompt periodic presente comme source de verite active si son contrat n'est pas remplace.

## Architecture cible

Le juge LLM mutable recoit toujours:

- les 5 paires completes user/assistant;
- `llm.static`;
- `llm.mutable_current`;
- `user.static`;
- `user.mutable_current`;
- le budget mutable;
- les regles de jugement;
- des metadonnees de source ou de garde temporelle si elles existent deja, mais sans retirer la matiere dialogique avant lecture.

Le juge lit lui-meme la matiere dialogique et decide si une phrase engage:

- l'identite;
- la relation;
- une valeur;
- une limite;
- une posture;
- une tension non canonisable;
- rien de mutable.

Le juge produit uniquement ces verdicts:

- `no_change`: la fenetre ne demande aucune mutation.
- `reject`: le juge a lu la fenetre et refuse la canonisation.
- `defer`: le juge a lu la fenetre mais juge le statut trop ambigu.
- `raise_tension`: le juge signale une tension non injectee.
- `persist`: le juge autorise une mutation mutable.

Operations autorisees uniquement quand `verdict = persist`:

- `add`;
- `tighten`;
- `merge`;
- `clear_obsolete`, seulement quand une mutable existante est explicitement retiree ou devenue fausse.

Regle dure: `raise_tension` n'est pas une operation de persistence. Ce verdict peut produire une trace content-free, un reason code ou une future surface operateur, mais il ne cree pas, ne modifie pas et ne supprime pas de mutable canonique dans `identity_mutables`.

Le code peut refuser seulement:

- JSON invalide;
- sujet invalide;
- operation invalide;
- contenu vide;
- contenu trop long;
- contenu prompt-like;
- contenu non declaratif;
- mutation impossible;
- violation de securite ou de runtime.

Le code ne peut pas refuser parce que:

- la phrase n'est pas repetee;
- la force locale est jugee trop faible;
- le support lexical est insuffisant;
- la recence est basse;
- le juge a lu une formulation singuliere plutot qu'une recurrence.

Schema JSON cible:

```json
{
  "schema_version": "mutable_judge_v1",
  "meta": {
    "execution_status": "complete",
    "window_pairs_count": 5,
    "window_complete": true
  },
  "verdicts": [
    {
      "subject": "user",
      "verdict": "persist",
      "operation": "add",
      "proposition": "Proposition canonique compacte.",
      "target": "",
      "targets": [],
      "reason_code": "explicit_self_limit_continuity",
      "continuity_kind": "limit",
      "source_refs": ["pair_03"],
      "guard_notes": ["not_task_local", "not_prompt_policy"]
    },
    {
      "subject": "llm",
      "verdict": "no_change",
      "operation": "",
      "proposition": "",
      "target": "",
      "targets": [],
      "reason_code": "no_mutable_identity_signal",
      "continuity_kind": "none",
      "source_refs": [],
      "guard_notes": []
    }
  ]
}
```

Reason codes canoniques definis par la spec Lot 0:

- source-of-truth: `app/docs/states/specs/mutable-identity-judge-contract.md`;
- familles: persistence, non-persistence, technique;
- les lots code ne doivent pas recreer une liste locale divergente dans cette TODO.

## Frontiere entre capture et jugement

La capture technique sert seulement a fournir au juge une fenetre complete de dialogue.

Elle doit:

- [ ] conserver les 5 paires completes user/assistant;
- [ ] conserver l'ordre et les roles;
- [ ] inclure les timestamps si deja disponibles;
- [ ] s'arreter a 5 paires completes;
- [ ] declencher le juge quand la cinquieme paire complete est disponible;
- [ ] garder la meme fenetre pour retry si le juge timeout ou renvoie une forme invalide;
- [ ] vider la fenetre seulement apres un run techniquement termine;
- [ ] ne pas extraire de fragments;
- [ ] ne pas classifier la matiere;
- [ ] ne pas mesurer la force de la matiere;
- [ ] ne pas retirer des passages pour raison semantique.

Decision de fenetre: la premiere implementation cible une fenetre consommee apres run termine. Ce choix evite de rejuger sans cesse les memes 5 paires et evite un gros staging historique. En cas de timeout, JSON invalide ou erreur transport, la fenetre reste en place pour retry; elle n'est pas remplacee par les tours suivants tant que le run n'est pas resolu.

## Transition du canon existant

- [ ] Conserver `identity_mutables` actuel comme canon herite initial.
- [ ] Ne pas migrer automatiquement `identity_mutable_staging` vers le nouveau canon.
- [ ] Ne pas revalider silencieusement les mutables existantes avec le nouveau juge.
- [ ] Ne pas migrer `identities`, `identity_evidence` ou `identity_conflicts` vers `identity_mutables`.
- [x] Ne pas transformer les anciens buffers en fenetres jugees.
- [ ] Les prochaines mutations viennent uniquement du nouveau juge mutable.
- [ ] Toute purge ou revue humaine du canon herite doit etre un chantier separe explicite.

## Regle dure sur le statique

- [x] Le nouveau juge mutable ne produit aucune ecriture `static`.
- [x] L'applicateur mutable n'appelle pas `write_static_identity_content`.
- [x] Le code ne planifie aucune promotion mutable -> static.
- [x] Le read-model n'affiche pas la promotion vers `static` comme capacite active du nouveau regime.
- [ ] Toute future promotion mutable -> static sera un chantier separe, avec spec, tests et validation humaine ou regle explicite.

## Lots

### Lot 0 - Contrat source-of-truth

Objectif: figer le contrat exact du nouveau mutable avant code.

Cases:

- [x] Specifier le contrat `5 paires completes -> juge LLM -> mutable`.
- [x] Retirer du plan toute cible de preselection semantique.
- [x] Definir le schema JSON `mutable_judge_v1`.
- [x] Definir les reason codes canoniques.
- [x] Verrouiller `pas d'ecriture static`.
- [x] Verrouiller `pas de scoring identitaire`.
- [x] Decrire les refus techniques autorises.
- [x] Decrire les refus techniques interdits.
- [x] Requalifier le temporal guard comme annotation ou garde technique, jamais comme tri identitaire avant lecture.
- [x] Mettre a jour docs/specs source-of-truth si necessaire.

Tests / preuves attendus:

- [x] Grep docs: aucune cible active ne decrit un pipeline de preselection avant juge.
- [x] Grep docs: les anciens scores ne sont decrits que comme legacy a supprimer.
- [x] Relecture manuelle du schema JSON.

Critere de sortie:

- [x] Un implementateur peut coder le pipeline sans inventer de decision conceptuelle.

Risque principal:

- Reintroduire une couche de tri sous un nom plus propre.

### Lot 1 - Fenetre de 5 paires

Objectif: remplacer le staging ancien par une fenetre courte complete.

Cases:

- [x] Remplacer la cible de buffer par 5 paires completes.
- [x] Garantir que chaque paire contient exactement un message user et un message assistant.
- [x] Garantir que la fenetre envoyee au juge contient tout le texte utile des 5 paires.
- [x] Ne pas faire de preselection semantique.
- [x] Neutraliser les ecritures canoniques score-first pendant la transition Lot 1.
- [x] Ajouter une garde taille content-free sans tronquer silencieusement la fenetre.
- [x] Documenter la fenetre comme consommee apres run termine.
- [x] Preserver la fenetre en cas de timeout, JSON invalide ou erreur transport.
- [x] Eviter un gros staging historique ou multi-run.
- [x] Renommer les events/payloads actifs pour raconter `mutable_identity_judge`; les noms de fonctions legacy restants sont reserves au nettoyage Lot 6.

Tests / preuves attendus:

- [x] Fenetre incomplete: pas d'appel juge.
- [x] Cinquieme paire complete: appel juge avec les 5 paires entieres.
- [x] Run termine: fenetre videe.
- [x] Timeout ou JSON invalide: fenetre conservee pour retry.
- [x] Fenetre trop grosse: pas d'appel modele, pas d'ecriture mutable, fenetre conservee.
- [x] Le payload juge ne contient aucun champ de score.

Critere de sortie:

- [x] Le juge recoit toujours une fenetre complete de 5 paires ou rien.

Risque principal:

- Transformer la nouvelle fenetre en ancien staging long sous un autre nom.

### Lot 2 - Juge LLM mutable

Objectif: creer le juge comme autorite centrale de decision.

Cases:

- [x] Creer le prompt `identity_mutable_judge`.
- [x] Creer le caller/service juge isole dans `app/memory/mutable_identity_judge.py`.
- [x] Envoyer au juge les 5 paires completes.
- [x] Envoyer au juge les quatre canons courants: `llm.static`, `llm.mutable_current`, `user.static`, `user.mutable_current`.
- [x] Envoyer le budget mutable.
- [x] Envoyer les regles de jugement.
- [x] Couvrir les deux sujets dans le meme appel.
- [x] Demander les verdicts `no_change`, `reject`, `defer`, `raise_tension`, `persist`.
- [x] Fail-closed sur timeout, parse error ou JSON invalide.
- [x] Ne pas demander au juge de retourner un score.
- [x] Exposer au juge les `continuity_kind` et reason codes canoniques.
- [x] Refuser les reason codes techniques comme sortie de jugement LLM.
- [x] Refuser les operations persistantes incompatibles pour un meme sujet.
- [x] Garder une garde taille locale dans le runner juge: `32_000` chars de fenetre, `12_000` tokens estimes.
- [x] Ne pas brancher encore l'applicateur canonique judge-first.
- [x] Documenter que `target` / `targets` referencent les formulations exactes du canon courant tant que le store n'a pas d'IDs par proposition.

Tests / preuves attendus:

- [x] Mock `persist`.
- [x] Mock `reject`.
- [x] Mock `defer`.
- [x] Mock `raise_tension`.
- [x] Mock `no_change`.
- [x] Mock JSON invalide.
- [x] Mock timeout.
- [x] Test que `user` et `llm` passent par le meme schema.
- [x] Test que l'observabilite compacte ne contient pas les propositions brutes.
- [x] Test que `window_too_large` ne fait pas d'appel provider.
- [x] Test que `raise_tension` ne peut toujours pas porter d'operation persistante.
- [x] Test que les conflicts `tighten` / `clear_obsolete` / `merge` sont refuses.

Critere de sortie:

- [x] Le module du LLM juge, isole du writer legacy, porte seul la decision mutable ontologique; l'application canonique reste pour Lot 3.

Risque principal:

- Rendre le prompt tellement conservateur qu'il recree le chomage technique, ou tellement permissif qu'il transforme le mutable en resume.

### Lot 3 - Applicateur judge-first

Objectif: appliquer seulement les verdicts `persist`, sans recalcul identitaire local.

Cases:

- [x] Creer l'applicateur dans un module separe de `app/memory/mutable_identity_judge.py`.
- [x] Valider le schema JSON.
- [x] Valider `subject in {llm,user}`.
- [x] Valider les operations autorisees.
- [x] Refuser contenu vide pour une persistence.
- [x] Refuser contenu trop long.
- [x] Refuser un contenu canonique final au-dela de `IDENTITY_MUTABLE_MAX_CHARS`, meme si chaque operation prise seule est sous la limite.
- [x] Refuser contenu prompt-like.
- [x] Refuser contenu non declaratif.
- [x] Refuser mutation impossible.
- [x] Refuser les couples operation/reason code incompatibles.
- [x] Appliquer uniquement les verdicts `persist`.
- [x] Ecrire seulement `identity_mutables`.
- [x] Ecrire `identity_mutable_audit` content-free via le store existant.
- [x] Persister les changements `llm` / `user` en batch all-or-nothing, sans ecriture canonique partielle entre sujets.
- [x] Utiliser les formulations exactes du canon courant comme `target` / `targets`, sans creer de nouveau modele DB.
- [x] Ne jamais appeler l'ancien scoring.
- [x] Ne jamais appeler le writer static.
- [x] Ne jamais transformer `reject`, `defer` ou `raise_tension` en canon injecte.

Tests / preuves attendus:

- [x] `persist/add` ecrit le mutable.
- [x] `persist/tighten` modifie seulement le mutable vise.
- [x] `persist/merge` modifie seulement le mutable vise.
- [x] `persist/clear_obsolete` efface ou retire seulement la mutable visee.
- [x] `reject`, `defer`, `raise_tension`, `no_change` n'ecrivent pas le canon.
- [x] JSON invalide n'ecrit rien.
- [x] Contenu prompt-like n'ecrit rien.
- [x] Proposition trop longue n'ecrit rien.
- [x] Contenu final trop long apres plusieurs operations n'ecrit rien.
- [x] Contenu final trop long apres `tighten` n'ecrit rien.
- [x] Reason code incompatible avec operation n'ecrit rien.
- [x] Echec d'ecriture d'un second sujet ne laisse aucune ecriture partielle observable.
- [x] `source_refs=["pair_99"]` est refuse, seules `pair_01` a `pair_05` sont valides.
- [x] Une proposition singuliere acceptee par le juge n'est pas rejetee par manque de recurrence.
- [x] Aucune ecriture static n'est observee.
- [x] Aucun appel a l'ancien scoring.
- [x] Aucun texte brut dans le summary/audit content-free.
- [x] Meme pipeline pour `user` et `llm`.

Critere de sortie:

- [x] L'applicateur execute le juge; il ne rejuge pas l'identite.

Risque principal:

- Garder un reliquat de veto score-first dans un helper.

### Lot 4 - Bascule runtime

Objectif: brancher le nouveau pipeline et retirer l'ancien writer actif.

Cases:

- [x] Brancher le nouveau pipeline dans `record_identity_entries_for_mode(...)`.
- [x] Garder les diagnostics legacy seulement s'ils restent explicitement hors canon.
- [x] Retirer le writer score-first automatique du chemin actif.
- [ ] Remplacer ou renommer completement `arbiter.run_identity_periodic_agent` legacy.
- [x] Remplacer le prompt periodic actif par le prompt judge-first.
- [x] Ne pas laisser deux writers mutables actifs.
- [x] Garantir que shadow/enforced modes gardent une semantique claire.
- [x] Garder l'observabilite content-free existante.

Tests / preuves attendus:

- [x] En mode enforced, le nouveau juge est appele apres 5 paires completes.
- [x] En mode shadow, aucune ecriture canonique n'est faite.
- [x] L'ancien writer n'est plus appele.
- [x] Les logs disent `mutable_judge` ou un nom equivalent, pas l'ancien regime comme verite active.
- [x] Les evenements ne contiennent pas de texte brut de fenetre.

Critere de sortie:

- [x] Un seul writer mutable canonique reste actif.

Risque principal:

- Laisser l'ancien agent actif en parallele pendant que le nouveau juge ecrit aussi.

### Lot 5 - Admin, read-model et logs

Objectif: aligner les surfaces d'observabilite sur le nouveau regime.

Cases:

- [x] Remplacer les labels de staging/scoring actifs minimaux du chemin Lot 4.
- [x] Exposer une activite `mutable_judge` content-free.
- [ ] Exposer count, status, reason code, hashes courts, longueurs, timestamps.
- [ ] Ne pas afficher la fenetre brute.
- [ ] Ne pas afficher les formulations sensibles.
- [x] Ne plus presenter la promotion static comme active.
- [x] Ne plus presenter les anciens seuils numeriques comme regime actif.
- [ ] Garder `identity_mutables` et `identity_mutable_audit` comprehensibles.
- [ ] Mettre a jour le frontend admin si ses labels racontent encore l'ancien regime.

Tests / preuves attendus:

- [ ] Test read-model: regime affiche `window_target_pairs=5`.
- [ ] Test read-model: pas de score local dans le regime actif.
- [ ] Test read-model: `promotion_to_static_enabled=false` ou champ retire.
- [ ] Test logs: aucun contenu de fenetre brute.
- [ ] Test admin: les anciens termes ne sont plus presentes comme actifs.

Critere de sortie:

- [ ] L'admin permet de comprendre le nouveau juge sans exposer de contenu sensible.

Risque principal:

- Ajouter de la telemetrie exploratoire au lieu de remplacer proprement les surfaces existantes.

### Lot 6 - Nettoyage legacy

Objectif: retirer la couche morte et les tests qui valident l'ancien modele.

Cases:

- [ ] Supprimer ou archiver `app/memory/memory_identity_periodic_scoring.py`.
- [ ] Supprimer ou requalifier les tests de scoring.
- [ ] Retirer `identity_mutable_staging` du runtime actif si le nouveau stockage de fenetre n'en a plus besoin.
- [ ] Supprimer les index inutiles lies au staging ancien apres decision migration.
- [ ] Requalifier ou supprimer `identity_periodic_agent.txt`.
- [ ] Retirer les imports morts.
- [ ] Retirer les reason codes legacy du chemin actif.
- [ ] Nettoyer docs/specs/README qui presentent l'ancien modele comme vivant.
- [ ] Garder les archives dans `todo-done/` comme archives, pas comme specs actives.

Tests / preuves attendus:

- [ ] Grep code: aucun appel actif a l'ancien scoring.
- [ ] Grep code: aucun writer mutable ancien dans le chemin enforced.
- [ ] Grep docs actives: l'ancien modele est seulement legacy.
- [ ] Suite identity/memory adaptee.

Critere de sortie:

- [ ] Il ne reste pas deux systemes mutables concurrents.

Risque principal:

- Garder des shims actifs "juste au cas ou" qui deviennent le vrai runtime par accident.

### Lot 7 - Validation finale

Objectif: prouver que la refonte est terminee, pas seulement ajoutee.

Cases:

- [ ] Prouver qu'il n'existe plus de writer mutable score-first actif.
- [ ] Prouver que `user` et `llm` passent par le meme pipeline.
- [ ] Prouver que le juge recoit toute la fenetre de 5 paires.
- [ ] Prouver que le statique n'est pas modifie.
- [ ] Prouver que `identity_mutables` reste le canon mutable relu.
- [ ] Prouver que les mutables sont reinjectees via `static + mutable`.
- [ ] Prouver l'absence de fuite de texte sensible dans logs/admin.
- [ ] Prouver que `Frida_from_herself.md` reste suspendu ou a ete absorbe.
- [ ] Prouver que docs et tests racontent le meme runtime.
- [ ] Prouver que les anciennes tables/buffers ne pilotent plus le canon.

Tests / preuves attendus:

- [ ] Tests unitaires cible complets.
- [ ] Tests admin/read-model/logs.
- [ ] Greps de non-regression.
- [ ] Relecture docs.
- [ ] Smoke applicatif si un lot runtime le justifie.

Critere de sortie:

- [ ] Plus d'ancien systeme mutable actif.
- [ ] Plus de scoring deterministe comme critere central.
- [ ] Mutable humain et mutable Frida fonctionnent selon le meme principe.
- [ ] Le LLM juge est l'autorite de decision.
- [ ] Observabilite, docs et tests sont alignes.
- [ ] Repo propre, pas de couche morte.

Risque principal:

- Clore le chantier alors qu'une surface admin, un test ou un helper continue de raconter l'ancien regime.

## Garde-fous du juge

Le juge doit tenir ensemble ouverture hermeneutique et discipline de canon.

Il doit lire sans prefiltre, mais il peut juger:

- qu'une phrase est ironique;
- qu'une phrase est citee;
- qu'une phrase est roleplay;
- qu'une phrase est un etat passager;
- qu'une phrase appartient au projet courant;
- qu'une phrase est une preference de format;
- qu'une phrase est une politique operateur;
- qu'une phrase est une consigne de prompt;
- qu'une phrase ouvre une tension plutot qu'une mutation.

Il ne doit pas transformer automatiquement en mutable:

- une humeur;
- une politesse;
- une consigne locale;
- une simple preference d'interface;
- une speculation psychologique;
- une promesse non supportee par une write-path reelle;
- une formule de confort conversationnel.

Mais il doit pouvoir persister une formulation singuliere si elle engage clairement une continuite de soi, de relation, de valeur, de limite ou de posture.

## Observabilite finale

S'en tenir aux surfaces existantes, en les requalifiant.

Autorise:

- status;
- reason code;
- sujet;
- operation;
- verdict;
- compteurs;
- longueurs;
- hashes courts;
- ids courts;
- timestamps;
- timeout / parse error / apply error;
- `window_pairs_count`.

Interdit:

- texte brut de la fenetre;
- extrait sensible de formulation;
- prompt complet du juge dans les logs de tour;
- decisions internes non stabilisees;
- telemetry exploratoire creee seulement pour regarder "ce que ca donne".

## Feed her from herself

L'intuition `feed her from herself` est suspendue pendant cette refonte. Les auto-formulations de Frida doivent d'abord etre lues par le meme juge mutable, dans la meme fenetre complete, avec le meme canon courant et les memes garde-fous que les formulations utilisateur.

Apres la refonte, il faudra seulement reevaluer s'il reste un artefact reflexif separe utile. Aucun systeme parallele ne doit etre ouvert maintenant.

## Definition de fini

- [ ] Les mutables courantes restent relues depuis `identity_mutables`.
- [ ] Les nouvelles mutations viennent uniquement du juge LLM mutable.
- [ ] La fenetre de 5 paires completes est l'unite de lecture.
- [ ] Il n'existe aucun tri semantique avant lecture par le juge.
- [ ] Le code ne score pas l'identite.
- [ ] Le code ne refuse pas par manque de recurrence ou de support lexical.
- [ ] Le code n'ecrit pas `static`.
- [ ] Les anciens buffers et evidence stores ne migrent pas automatiquement.
- [ ] L'admin ne presente plus les anciens scores comme regime actif.
- [ ] Les logs restent content-free.
- [ ] Les tests couvrent `user` et `llm`.
- [ ] Les docs actives ne contredisent pas ce contrat.
