# Mutable Identity Judge Contract

Statut: spec normative active
Date: 2026-05-25
Portee: contrat source-of-truth de la refonte mutable `user` et `llm`
Hors-scope de cette spec: migration DB lourde, test modele live, benchmark modele, promotion mutable -> static

## Decision

Le nouveau systeme mutable est judge-first.

Pipeline normatif:

```text
5 paires completes user/assistant
-> juge LLM mutable
-> verdicts du juge
-> validation technique minimale
-> identity_mutables si et seulement si verdict=persist et operation valide
-> audit content-free
-> reinjection static + mutable
```

Le code ne pre-juge pas ce qui est identitaire.

Interdits comme criteres d'admission mutable:

- scoring identitaire;
- preselection semantique;
- extraction de candidats par Python avant lecture du juge;
- recurrence comme condition d'entree;
- support lexical comme condition d'entree;
- seuil de force locale;
- tri temporel qui empeche le juge de lire la fenetre complete.

Le juge LLM lit la fenetre complete et juge lui-meme ce qui releve de l'identite mutable, pour `user` comme pour `llm`.

## Unites Et Cadence

Unite de lecture:

- exactement 5 paires completes `user` / `assistant`;
- une paire complete contient un message `user` puis le message `assistant` correspondant;
- le texte complet des 5 paires est transmis au juge;
- l'ordre, les roles et les timestamps disponibles sont conserves;
- aucune formulation n'est extraite, resumee ou classee avant le juge.

Cadence:

- le juge s'active quand la cinquieme paire complete est disponible;
- si la fenetre est incomplete, il n'y a pas d'appel juge;
- apres un run techniquement termine, la fenetre est consommee;
- en cas de timeout, JSON invalide, erreur transport ou schema invalide, la meme fenetre reste disponible pour retry;
- les tours suivants ne remplacent pas silencieusement une fenetre bloquee.

Cette fenetre est une capture technique, pas un staging semantique.

## Branchement Runtime Actif

Depuis le Lot 4, le chemin actif est:

```text
record_identity_entries_for_mode(...)
-> memory_identity_periodic_agent.stage_identity_turn_pair(...)
-> mutable_identity_runtime.run_mutable_identity_window(...)
-> run_mutable_identity_judge(...)
-> apply_mutable_judge_contract(...) seulement en mode enforced
```

Regles runtime:

- le nom historique `memory_identity_periodic_agent` ne designe plus un writer score-first actif; il sert de wrapper de fenetre jusqu'au nettoyage legacy;
- `arbiter.run_identity_periodic_agent(...)` et `app/prompts/identity_periodic_agent.txt` restent legacy pre-refonte et ne sont plus le chemin actif;
- en `shadow`, le juge peut etre appele et observe, mais l'applicateur n'est pas lance et `identity_mutables` ne change pas;
- en `enforced`, un contrat `mutable_judge_v1` valide peut etre applique dans `identity_mutables`;
- si le juge echoue, timeout, renvoie JSON/schema invalide ou `window_too_large`, la fenetre est preservee;
- si l'applicateur echoue, la fenetre est preservee;
- si le run se termine proprement par `no_change`, `reject`, `defer`, `raise_tension` ou par persistence appliquee, la fenetre est consommee;
- aucun chemin actif n'appelle `memory_identity_periodic_apply.apply_periodic_agent_contract(...)` ni `memory_identity_periodic_scoring.score_operation(...)`;
- aucun chemin actif n'ecrit `static`.

## Entrees Du Juge

Le juge recoit:

- `window_pairs`: les 5 paires completes;
- `llm.static`;
- `llm.mutable_current`;
- `user.static`;
- `user.mutable_current`;
- `mutable_budget.target_chars`;
- `mutable_budget.max_chars`;
- `judgment_rules`;
- `source_annotations` si elles existent deja.

Le juge ne recoit pas comme entree obligatoire:

- memories RAG;
- summaries longues;
- observations hermeneutiques completes;
- evidence legacy;
- read-model admin complet;
- fragments preselectionnes;
- candidats produits par regex;
- score local.

Ces couches peuvent rester disponibles pour d'autres pipelines, mais elles ne font pas partie du contrat source du juge mutable.

## Temporal Guard Et Source Guard

Un temporal guard peut annoter la fenetre.

Il peut fournir:

- presence de marqueurs temporels faibles;
- contexte de citation;
- role source;
- timestamps;
- indications de source ou de provenance;
- flags techniques de securite.

Il ne peut pas:

- retirer une phrase parce qu'elle parait non identitaire;
- remplacer une formulation par un trou avant lecture du juge;
- transformer une phrase en candidat;
- decider qu'une formulation est trop faible;
- refuser une mutation par recurrence basse;
- servir de scoring.

Exception: une redaction obligatoire pour securite runtime ou secret suit la politique de securite generale. Elle doit etre auditee comme garde technique, jamais comme jugement identitaire.

## Schema JSON Canonique

Nom de schema: `mutable_judge_v1`

Forme top-level:

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

Regles de schema:

- `schema_version` vaut exactement `mutable_judge_v1`.
- `meta.execution_status` vaut `complete`.
- `meta.window_pairs_count` vaut `5`.
- `meta.window_complete` vaut `true`.
- `verdicts` est une liste non vide.
- Chaque item de `verdicts` porte exactement un sujet: `user` ou `llm`.
- Chaque run porte au moins un verdict pour `user` et au moins un verdict pour `llm`.
- Si un sujet ne demande aucune persistence, tension, rejection ou deferral, il porte un verdict explicite `no_change`.
- Un sujet peut avoir plusieurs verdicts seulement si les operations persistantes restent compatibles entre elles.
- `no_change` ne coexiste pas avec un autre verdict du meme sujet dans le meme run.
- `source_refs` reference uniquement la fenetre courante: `pair_01`, `pair_02`, `pair_03`, `pair_04`, `pair_05`. Toute autre reference, dont `pair_99`, est invalide.
- `guard_notes` contient des codes courts, jamais une justification longue.
- `continuity_kind` vaut `identity`, `relation`, `value`, `limit`, `posture`, `tension` ou `none`.

## Verdicts Canoniques

Verdicts autorises:

- `no_change`: le juge a lu la fenetre et ne voit aucune mutation utile.
- `reject`: le juge refuse la canonisation.
- `defer`: le juge voit une matiere possible mais pas assez resolue pour canoniser.
- `raise_tension`: le juge signale une tension identitaire ou relationnelle non canonisee.
- `persist`: le juge demande une mutation mutable.

`raise_tension` n'est pas une operation de persistence. Il peut produire une trace content-free, un reason code, un compteur ou une future surface operateur, mais il ne cree pas, ne modifie pas et ne supprime pas de mutable canonique.

## Operations Persistantes

Operations autorisees uniquement quand `verdict = persist`:

- `add`: ajouter une proposition mutable nouvelle.
- `tighten`: remplacer une proposition mutable existante par une formulation plus precise.
- `merge`: fusionner plusieurs propositions existantes en une formulation plus nette.
- `clear_obsolete`: retirer une proposition mutable explicitement devenue fausse, retiree ou obsolete.

Quand `verdict != persist`:

- `operation` doit etre vide;
- `proposition` doit etre vide;
- `target` doit etre vide;
- `targets` doit etre vide.

Quand `operation = add`:

- `proposition` est obligatoire;
- `target` est vide;
- `targets` est vide.

Quand `operation = tighten`:

- `target` reference exactement une proposition mutable courante;
- `proposition` est la nouvelle formulation;
- `targets` est vide.

Quand `operation = merge`:

- `targets` reference au moins deux propositions mutables courantes;
- `proposition` est la formulation fusionnee;
- `target` est vide.

Quand `operation = clear_obsolete`:

- `target` reference exactement une proposition mutable courante;
- `proposition` est vide;
- `targets` est vide.

Tant que `identity_mutables` stocke un contenu canonique par sujet sans
identifiants stables par proposition, `target` et `targets` referencent les
formulations exactes presentes dans le canon mutable courant du meme sujet.
L'applicateur ne cree pas de nouveau modele DB pour ce lot.

## Reason Codes Canoniques

Les reason codes sont content-free, stables et courts.

Le juge LLM ne retourne que les codes de persistence ou de non-persistence.
Les codes techniques sont reserves au runner, au validateur et au futur
applicateur; ils ne sont jamais une raison ontologique produite par le modele.

Codes de persistence:

- `explicit_self_definition_continuity`
- `explicit_self_value_continuity`
- `explicit_self_limit_continuity`
- `explicit_relation_continuity`
- `explicit_frida_self_definition_continuity`
- `explicit_frida_limit_continuity`
- `explicit_posture_continuity`
- `mutable_tightening`
- `mutable_merge`
- `mutable_obsolete_explicitly_removed`

Codes de non-persistence:

- `no_mutable_identity_signal`
- `already_covered_by_static`
- `already_covered_by_mutable`
- `task_local_not_identity`
- `format_or_operator_policy_not_identity`
- `memory_summary_not_identity`
- `irony_roleplay_or_quote`
- `temporary_state`
- `ambiguous_subject`
- `insufficient_context`
- `source_scope_unclear`
- `contradiction_open`
- `relation_tension_open`
- `quoted_or_reported_speech`
- `project_policy_not_identity`

Compatibilite verdict / reason code de sortie modele:

- `persist`: codes de persistence uniquement.
- `persist/add`: codes `explicit_*_continuity` uniquement; `mutable_tightening`,
  `mutable_merge` et `mutable_obsolete_explicitly_removed` sont interdits.
- `persist/tighten`: `mutable_tightening`.
- `persist/merge`: `mutable_merge`.
- `persist/clear_obsolete`: `mutable_obsolete_explicitly_removed`.
- `no_change`: `no_mutable_identity_signal`, `already_covered_by_static`,
  `already_covered_by_mutable`.
- `reject`: `task_local_not_identity`,
  `format_or_operator_policy_not_identity`, `memory_summary_not_identity`,
  `irony_roleplay_or_quote`, `temporary_state`, `ambiguous_subject`,
  `quoted_or_reported_speech`, `project_policy_not_identity`,
  `already_covered_by_static`, `already_covered_by_mutable`.
- `defer`: `ambiguous_subject`, `insufficient_context`,
  `source_scope_unclear`, `contradiction_open`, `relation_tension_open`.
- `raise_tension`: `contradiction_open`, `relation_tension_open`.

Codes techniques:

- `window_too_large`
- `judge_timeout`
- `judge_transport_error`
- `judge_invalid_json`
- `schema_invalid`
- `invalid_subject`
- `invalid_verdict`
- `invalid_operation`
- `invalid_target`
- `empty_proposition`
- `proposition_too_long`
- `prompt_like_content`
- `non_declarative_content`
- `impossible_mutation`
- `mutable_content_too_long`
- `runtime_safety_violation`
- `mutable_store_unavailable`
- `canonical_write_failed`

## Validation Technique Autorisee

Le code peut refuser seulement pour:

- JSON invalide;
- schema invalide;
- `subject` invalide;
- verdict invalide;
- operation invalide;
- cible inexistante ou ambigue;
- taille excessive;
- contenu canonique final au-dela de `IDENTITY_MUTABLE_MAX_CHARS`;
- contenu vide quand une proposition est obligatoire;
- contenu dangereux, prompt-like ou non declaratif;
- mutation impossible a appliquer;
- violation de contrat;
- violation de securite runtime;
- store mutable indisponible;
- echec de persistence.

Le refus technique ne remplace pas le jugement ontologique. Il protege seulement le runtime et la coherence du stockage.

## Validation Technique Interdite

Le code ne peut pas refuser parce que:

- une formulation n'est pas assez repetee;
- un support lexical est insuffisant;
- une occurrence est trop ancienne dans la fenetre;
- un score local est faible;
- Python ne reconnait pas une categorie identitaire;
- la proposition est rare mais jugee persistable par le LLM;
- la formulation n'a pas ete extraite par une regex;
- la fenetre contient de l'indetermine.

## Persistence

Seul `verdict = persist` avec operation valide peut modifier `identity_mutables`.

Le nouveau pipeline:

- ecrit seulement le canon mutable dans `identity_mutables`;
- borne le contenu canonique final de chaque sujet a `IDENTITY_MUTABLE_MAX_CHARS`, apres composition de toutes les operations du run;
- persiste les mutations `llm` / `user` d'un meme contrat en transaction batch all-or-nothing: si un sujet echoue, aucun sujet n'est ecrit;
- ecrit un audit compact content-free dans `identity_mutable_audit` ou dans la surface d'audit finale retenue;
- ne stocke pas la fenetre brute dans l'audit;
- ne reinjecte pas `reject`, `defer` ou `raise_tension`;
- ne migre pas automatiquement les donnees legacy;
- ne revalide pas silencieusement le canon mutable herite.

Interdits:

- ecriture automatique de `static`;
- promotion automatique mutable -> static;
- persistence dans `identities`, `identity_evidence` ou `identity_conflicts` comme canon actif;
- migration automatique depuis l'ancien staging;
- double writer mutable actif.

## Regime Commun User Et LLM

Le meme pipeline traite:

- `user.mutable`;
- `llm.mutable`.

Le sujet change, pas le regime.

Le juge doit savoir:

- qui parle;
- de qui on parle;
- si la formulation est auto-formulation, projection, citation, roleplay ou tension;
- si la mutation vise `user` ou `llm`.

Il ne doit pas exister de pipeline mutable Frida separe ni de writer utilisateur distinct.

## Observabilite

L'observabilite finale reste content-free.

Autorise:

- status;
- verdict;
- reason code;
- subject;
- operation;
- counts;
- longueurs;
- hashes courts;
- ids courts;
- timestamps;
- `window_pairs_count`;
- `window_complete`;
- timeout / parse error / apply error.
- stages actifs `mutable_identity_judge` et `mutable_identity_judge_apply`.

Interdit:

- texte brut de la fenetre;
- extrait sensible;
- proposition source brute dans les logs;
- prompt complet du juge dans un event de tour;
- score identitaire;
- justification longue du juge dans l'observabilite compacte.
- presenter `identity_periodic_agent` ou ses seuils score-first comme writer mutable actif.

## Contrat De Sortie Du Lot 0

Un developpeur doit pouvoir coder le Lot 1 sans inventer de decision conceptuelle:

- la cadence est fixee;
- les entrees juge sont fixees;
- le schema JSON est fixe;
- les verdicts sont fixes;
- les operations persistantes sont fixees;
- les reason codes initiaux sont fixes;
- les refus techniques autorises et interdits sont fixes;
- le temporal guard est requalifie comme annotation/garde technique;
- la persistence est bornee a `identity_mutables`;
- le statique est hors ecriture.
