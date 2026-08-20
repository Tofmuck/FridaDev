# Mutable Identity Judge Contract

Statut: spec normative active
Date: 2026-05-25
Portee: contrat source-of-truth de la refonte mutable `user` et `llm`
Hors-scope de cette spec: migration DB lourde, test modele live, benchmark modele, promotion mutable -> static

Mise a jour 2026-05-26: le caller OpenRouter du juge envoie un
`response_format` JSON Schema strict pour le contrat actif et
`provider.require_parameters=true`. `provider.order` n'est force que pour les
modeles Anthropic; le modele actif `openai/gpt-5.2` ne force pas de provider
Anthropic et omet les parametres d'echantillonnage non supportes par OpenRouter
avec `require_parameters=true`. Ce verrou amont ne remplace pas le validateur
metier FridaDev: la validation locale reste souveraine pour les contraintes
conditionnelles, les tailles, la securite et la persistence.

Mise a jour 2026-05-26, Lot B add-only ontologique: le runtime actif utilise
`mutable_judge_v2`. Le regime automatique admet seulement de nouveaux enonces
ontologiques courts via `add` ou conclut `no_change`. Il ne maintient plus le
canon existant: pas de `persist`, pas d'`operation`, pas de `tighten`, pas de
`merge`, pas de `clear_obsolete`, pas de `target_ref` / `target_refs`.

Convention de lecture apres Lot B: les sections qui decrivent `mutable_judge_v1`,
`persist`, `operation`, `tighten`, `merge`, `clear_obsolete`, `target_ref` ou
`target_refs` sont des traces legacy pre-Lot-B / compatibilite historique. Elles
ne constituent plus le regime runtime actif.

Mise a jour 2026-05-26, Lot E cleanup: l'implementation v1 gestionnaire a ete
retiree du chemin de code actif. `app/memory/mutable_identity_judge.py` reste un
shim de compatibilite operateur content-free; les helpers communs utilises par
v2 vivent dans `mutable_identity_judge_common.py`. Les refs cible
`mutable_identity_refs.py` ont ete supprimees.

## Decision

Le systeme mutable est judge-first et add-only ontologique. Depuis le cutover
Lot B, le runtime actif est `mutable_judge_v2`.

Pipeline runtime actif (`mutable_judge_v2`):

```text
5 paires completes user/assistant
-> juge LLM mutable
-> verdict add/no_change
-> validation technique minimale
-> identity_mutables si et seulement si verdict=add valide
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
- timeout, erreur transport, JSON/schema ou verdict invalide conservent la meme
  fenetre pour une seconde et derniere tentative;
- `runtime_safety_violation`, qui peut couvrir un echec technique local ou de
  chargement, conserve la fenetre pour une seconde et derniere tentative;
- `window_too_large` consomme immediatement la fenetre sans ecriture canonique;
- apres la seconde tentative en echec, la fenetre est consommee sans ecriture
  canonique et garde son reason code d'echec;
- une paire arrivee pendant le traitement est promue atomiquement, exactement
  une fois, comme premiere paire de la fenetre suivante.

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

- le nom historique `memory_identity_periodic_agent` ne designe plus un writer score-first actif; il sert de wrapper de fenetre tant que le stockage technique reste `identity_mutable_staging`;
- `arbiter.run_identity_periodic_agent(...)` est une entree de compatibilite desactivee depuis Lot 6: pas d'appel provider, pas d'ecriture canonique, retour content-free `legacy_identity_periodic_agent_disabled`;
- `app/prompts/identity_periodic_agent.txt` est un artefact legacy desactive, conserve pour compatibilite documentaire/admin, pas un prompt runtime actif;
- en `shadow`, le juge peut etre appele et observe, mais l'applicateur n'est pas lance et `identity_mutables` ne change pas;
- en `enforced`, un contrat `mutable_judge_v2` valide peut ajouter dans `identity_mutables`;
- timeout, erreur transport et echec de contrat conservent la fenetre pour une
  unique reprise; un second echec la consomme sans ecriture;
- `runtime_safety_violation` est un echec technique transitoire borne, preserve
  une fois puis consomme sans ecriture s'il se repete;
- `window_too_large` reste l'echec d'input deterministe terminal, consomme sans
  appel provider ni ecriture canonique;
- si l'applicateur echoue, la fenetre est preservee pour une reprise
  idempotente; un second echec la consomme sans etre renomme succes;
- si le run se termine proprement par `no_change` ou par `add` applique, la fenetre est consommee;
- aucun chemin actif n'appelle `memory_identity_periodic_apply.apply_periodic_agent_contract(...)` ni `memory_identity_periodic_scoring.score_operation(...)`; les modules legacy correspondants ont ete retires en Lot 6;
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

## Schema JSON Legacy Pre-Lot-B (`mutable_judge_v1`)

Le schema `mutable_judge_v1` est conserve dans cette spec comme reference
historique. Son implementation runtime a ete retiree en Lot E; il n'est plus le
contrat runtime actif et n'a plus de builder schema actif.

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
      "target_ref": "",
      "target_refs": [],
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
      "target_ref": "",
      "target_refs": [],
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
- Les formulations identitaires humaines non vides (`proposition`, `target`, `targets[]`) sont redigees en francais.
- Les cles JSON, enums, `reason_code`, `continuity_kind`, `source_refs` et `guard_notes` restent en forme canonique code.
- `continuity_kind` vaut `identity`, `relation`, `value`, `limit`, `posture`, `tension` ou `none`.
- `current_mutables.<subject>.propositions[]` fournit au juge des refs stables
  content-free du type `llm_01` / `user_01` associees aux formulations
  courantes; ces refs sont reconstruites depuis le canon courant a chaque run.

## Contrat Actif Add-Only `mutable_judge_v2`

Statut: actif depuis Lot B.

Le contrat v2 recadre le juge automatique comme admission d'un nouvel enonce
ontologique, pas comme maintenance du canon existant. Il conserve la fenetre de
5 paires, le meme regime pour `user` et `llm`, le structured output OpenRouter,
`provider.require_parameters=true`, la validation locale stricte et
l'observabilite content-free. Le modele runtime actif est `openai/gpt-5.2`;
`provider.order=["anthropic"]` reste seulement une preference conditionnelle
pour les modeles Anthropic.

Activation:

- le runtime actif appelle `mutable_judge_v2`;
- l'applicateur automatique actif est append-only;
- tout contrat contenant un champ gestionnaire v1 est invalide dans le chemin
  actif.

Schema v2:

```json
{
  "schema_version": "mutable_judge_v2",
  "meta": {
    "execution_status": "complete",
    "window_pairs_count": 5,
    "window_complete": true
  },
  "verdicts": [
    {
      "subject": "user",
      "verdict": "add",
      "proposition": "Tof traite la frontiere entre sa pensee et la voix de Frida comme un objet central.",
      "reason_code": "explicit_relation_continuity",
      "continuity_kind": "relation",
      "source_refs": ["pair_03"],
      "guard_notes": ["not_task_local"]
    },
    {
      "subject": "llm",
      "verdict": "no_change",
      "proposition": "",
      "reason_code": "no_mutable_identity_signal",
      "continuity_kind": "none",
      "source_refs": [],
      "guard_notes": []
    }
  ]
}
```

Regles v2:

- verdicts autorises: `no_change`, `add`;
- champs interdits: `operation`, `target`, `targets`, `target_ref`,
  `target_refs`;
- operations automatiques retirees du contrat cible: `tighten`, `merge`,
  `clear_obsolete`;
- `persist` disparait comme conteneur multi-operation;
- `add` exige une `proposition` francaise, courte, ontologique et declarative;
- la validation locale du contrat borne la forme canonique de sortie, sans lire
  ni filtrer la fenetre: une `proposition` ajoutee doit commencer par le nom
  actif du sujet. Pour `llm`, le nom actif est `Frida`. Pour `user`, le nom est
  derive de l'identite active (`user.static` / `user.mutable_current`), par
  exemple `Tof` sur Frida courante ou `Amandine` sur un clone seede ainsi. Une
  simple mention relationnelle ou historique d'un nom tiers ne suffit pas a le
  rendre actif. Le fallback UI generique `Utilisateur` n'est pas un nom canonique mutable;
  la proposition doit employer une forme du type `est`, `tient`, `refuse`,
  `reconnait`, `traite`, `exige`, se terminer par un point, et `traite` doit
  porter un `comme`;
- `no_change` exige une `proposition=""`;
- si l'idee est deja couverte par `static` ou `mutable_current`, le verdict est
  `no_change`;
- si la matiere est locale, temporaire, narrative, psychologique,
  operationnelle, conversationnelle, citee, rapportee ou trop molle, le verdict
  est `no_change`;
- si le juge ne peut pas produire une phrase ontologique courte, le verdict est
  `no_change`.

Reason codes d'admission v2:

- `explicit_self_definition_continuity`;
- `explicit_self_value_continuity`;
- `explicit_self_limit_continuity`;
- `explicit_relation_continuity`;
- `explicit_frida_self_definition_continuity`;
- `explicit_frida_limit_continuity`;
- `explicit_posture_continuity`.

Reason codes de non-admission v2:

- `no_mutable_identity_signal`;
- `already_covered_by_static`;
- `already_covered_by_mutable`;
- `task_local_not_identity`;
- `temporary_state`;
- `ambiguous_subject`;
- `insufficient_context`;
- `source_scope_unclear`;
- `quoted_or_reported_speech`;
- `project_policy_not_identity`.

Le prompt runtime actif est `app/prompts/identity_mutable_judge_v2.txt`.

## Verdicts Legacy Pre-Lot-B (`mutable_judge_v1`)

Cette section decrit le regime gestionnaire retire du chemin actif en Lot B.
Elle reste utile pour comprendre l'historique, pas pour coder le runtime actuel.

Verdicts autorises:

- `no_change`: le juge a lu la fenetre et ne voit aucune mutation utile.
- `reject`: le juge refuse la canonisation.
- `defer`: le juge voit une matiere possible mais pas assez resolue pour canoniser.
- `raise_tension`: le juge signale une tension identitaire ou relationnelle non canonisee.
- `persist`: le juge demande une mutation mutable.

`raise_tension` n'est pas une operation de persistence. Il peut produire une trace content-free, un reason code, un compteur ou une future surface operateur, mais il ne cree pas, ne modifie pas et ne supprime pas de mutable canonique.

## Operations Persistantes v1 Actives Pre-Lot B

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
- `target_ref` doit etre vide;
- `target_refs` doit etre vide.

Quand `operation = add`:

- `proposition` est obligatoire;
- `target` est vide;
- `targets` est vide.
- `target_ref` est vide;
- `target_refs` est vide.

Quand `operation = tighten`:

- `target_ref` reference une proposition mutable courante du meme sujet, par
  exemple `llm_01` ou `user_02`;
- `target` reste un chemin de compatibilite texte exact si aucune ref n'est
  disponible;
- `proposition` est la nouvelle formulation;
- `targets` est vide.
- `target_refs` est vide.

Quand `operation = merge`:

- `target_refs` reference au moins deux propositions mutables courantes du
  meme sujet;
- `targets` reste un chemin de compatibilite texte exact si aucune ref n'est
  disponible;
- `proposition` est la formulation fusionnee;
- `target` est vide.
- `target_ref` est vide.

Quand `operation = clear_obsolete`:

- `target_ref` reference une proposition mutable courante du meme sujet;
- `target` reste un chemin de compatibilite texte exact si aucune ref n'est
  disponible;
- `proposition` est vide;
- `targets` est vide.
- `target_refs` est vide.

Le juge ne doit jamais produire un `persist` incomplet. Si `add`, `tighten` ou
`merge` ne peuvent pas fournir de `proposition` non vide, le verdict attendu
est `no_change`, `reject` ou `defer` avec un reason code de non-persistence
compatible, par exemple `already_covered_by_mutable`, `already_covered_by_static`,
`insufficient_context` ou `source_scope_unclear`. `clear_obsolete` est le seul
cas ou `proposition` vide est normal, et seulement avec `target_ref` ou
`target` non vide.

Tant que `identity_mutables` stocke un contenu canonique par sujet sans
identifiants persistants par proposition, `target_ref` / `target_refs` sont des
refs techniques reconstruites depuis l'ordre courant des propositions du canon
mutable. Elles ne sont pas stockees comme IDs DB durables. `target` et
`targets` restent seulement une compatibilite texte exact; l'applicateur ne
fait pas de matching approximatif.

Dans un meme contrat applique en batch, ces refs sont stables par rapport au
snapshot initial envoye au juge, pas par rapport a la liste courante deja
modifiee par les operations precedentes. L'applicateur conserve une table
d'origines pour que `user_02` continue a viser la deuxieme proposition initiale
meme si `user_01` a ete retiree plus tot dans le batch. Si une proposition
initiale visee par ref a deja ete supprimee ou fusionnee par une operation
precedente du meme contrat, l'operation suivante est refusee avec
`target_already_mutated` ou `impossible_mutation`; le batch reste all-or-nothing.

## Structured Output OpenRouter v1 Actif Pre-Lot B

Le payload OpenRouter du caller `mutable_identity_judge` contient:

- `response_format.type = json_schema`;
- `response_format.json_schema.name = mutable_judge_v1`;
- `response_format.json_schema.strict = true`;
- `response_format.json_schema.schema.additionalProperties = false`;
- enums de forme pour `subject`, `verdict`, `operation`, `reason_code`,
  `continuity_kind` et `source_refs`;
- champs de ciblage stables `target_ref` et `target_refs`, en plus des champs
  de compatibilite texte `target` et `targets`;
- `provider.require_parameters = true`, afin d'eviter un routage vers un
  provider qui ignorerait `response_format`.
- `provider.order = ["anthropic"]`, afin de privilegier le provider Anthropic
  direct observe compatible et plus rapide que le routage Bedrock pour ce
  schema, sans mettre `allow_fallbacks=false`.

Le JSON Schema couvre la forme structurelle. Il ne porte pas toute la logique
conditionnelle metier: compatibilite verdict/reason code, obligation de
`proposition` pour `add`/`tighten`/`merge`, `clear_obsolete` sans proposition,
operations incompatibles et bornes applicatives restent validees par
`validate_mutable_judge_contract(...)`.

## Reason Codes Canoniques v1 Actifs Pre-Lot B

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
- `target_not_found`
- `target_ambiguous`
- `target_ref_invalid`
- `target_already_mutated`
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

## Persistence Active Lot B (`mutable_judge_v2`)

Seul `verdict = add` valide peut ajouter dans `identity_mutables`.

Le nouveau pipeline:

- ecrit seulement le canon mutable dans `identity_mutables`;
- borne le contenu canonique final de chaque sujet a `IDENTITY_MUTABLE_MAX_CHARS`, apres append des propositions admises du run;
- persiste les mutations `llm` / `user` d'un meme contrat en transaction batch all-or-nothing: si un sujet echoue, aucun sujet n'est ecrit;
- ecrit un audit compact content-free dans `identity_mutable_audit` ou dans la surface d'audit finale retenue;
- ne stocke pas la fenetre brute dans l'audit;
- ignore `no_change` sans ecriture;
- ne modifie, ne fusionne et ne supprime jamais le canon existant automatiquement;
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
- empreinte SHA-256 tronquee a 12 caracteres de la fenetre, stable seulement
  pour reconnaitre un retry et jamais accompagnee du contenu source;
- ids courts;
- timestamps;
- `window_pairs_count`;
- `window_complete`;
- timeout / parse error / apply error.
- stage de tour actif `mutable_identity_judge`; l'etat apply reste projete dans
  ses champs compacts et ne cree pas un nouveau stage de tour opportuniste;
- `failure_class`, `recovery_action`, `processing_state`, `attempt_current`,
  `attempt_limit`, `window_fingerprint`, `next_window_progress` et
  `next_buffer_pairs_count`;
- `window_chars`, `payload_chars`, `estimated_prompt_tokens`,
  `max_window_chars` et `max_estimated_prompt_tokens`;
- diagnostics d'invalidation content-free: `validation_reason`,
  `invalid_verdict_index`, `invalid_subject`, `invalid_verdict`,
  `invalid_operation`, `invalid_reason_code`, `invalid_proposition_chars`,
  `invalid_target_chars`, `invalid_targets_count`, `invalid_source_refs_count`,
  `invalid_guard_notes_count`.

Interdit:

- texte brut de la fenetre;
- extrait sensible;
- proposition source brute dans les logs;
- prompt complet du juge dans un event de tour;
- score identitaire;
- justification longue du juge dans l'observabilite compacte.
- presenter `identity_periodic_agent` ou ses seuils score-first comme writer mutable actif.

Une invalidation `empty_proposition` conserve la fenetre pour une unique reprise
et expose le verdict/operation fautif sous forme de compteurs et codes seulement.
Si la seconde tentative echoue, la fenetre est consommee sans ecriture et sans
faux `no_change`.

## Politique De Vivacite Lot 1

La borne est `attempt_limit = 2`. Elle ne depend d'aucun compteur global en
memoire. Une fenetre complete seulement persistee, encore `buffering` et sans
run enregistre, commence a `attempt_current=1`. `running` signifie seulement
qu'un owner content-free a acquis la fenetre; un crash apres ce claim et avant
l'appel du juge ne consomme aucune tentative. La tentative devient persistante
au CAS `judge_attempt_started`. Sa reprise prudente devient la tentative
suivante; `retry_pending` et `write_recovery_pending` portent de meme la preuve
d'une tentative precedente. `terminal_discard_failed` ne rend jamais la main au
juge: il reprend exclusivement le CAS de consommation/finalisation.

- `transient`: `judge_timeout`, transport sans statut, HTTP
  `408/409/425/429`, `5xx` et `runtime_safety_violation`; reprise preservee,
  puis consommation terminale sans ecriture si elle echoue encore;
- `deterministic_input`: `window_too_large`; consommation terminale immediate
  sans ecriture;
- `deterministic_contract`: autres refus techniques, HTTP `4xx` non
  recuperables, JSON/schema/verdict et refus metier invalides; une reprise
  preservee puis consommation terminale;
- `write_recovery`: `canonical_write_failed`, `mutable_store_unavailable`,
  `staging_finalize_failed`; reprise idempotente, puis consommation terminale
  sans faux succes si la preuve canonique reste impossible.

Les gardes locales sont `40000` caracteres de fenetre et `16000` tokens de
prompt estimes. Elles ne tronquent rien: au-dela, la fenetre entiere est refusee
comme `window_too_large`. La cadence reste exactement cinq paires completes.

La transition terminale ou reussie remplace atomiquement l'ancien buffer par
zero paire ou par la paire courante comme premiere paire de la fenetre suivante.
Si l'ecriture canonique a reussi mais que la finalisation du staging echoue, le
staging porte un statut de reprise de finalisation; la reprise ne rappelle ni le
juge ni l'applicateur.

Une seule execution peut posseder une fenetre donnee. Le wrapper tient pendant
juge, application et finalisation un verrou consultatif PostgreSQL de session
derive de `conversation_id + window_fingerprint`; la fermeture de connexion le
libere aussi apres crash. Sous ce verrou, l'acquisition persistante est un CAS
sur la liste JSON complete, le statut et le reason attendus. Le reason
`processing_claim` contient seulement tentative, empreinte courte et owner
aleatoire content-free. Le CAS `judge_attempt_started`, execute juste avant
l'appel effectif du juge, distingue donc acquisition et tentative.

Tout changement de statut et tout clear apres acquisition reutilisent la meme
precondition de fenetre, statut et owner/reason. Un clear tardif devient un
no-op explicite: il ne peut effacer ni la premiere paire suivante ni une
nouvelle fenetre. Un appel concurrent attend le verrou; apres la finalisation,
sa paire est reappendue avec deduplication exacte ou reconnue comme deja
presente, exactement une fois.

Pour une fenetre active, l'applicateur ecrit le canon, l'audit et le verrou
`canonical_write_committed` du staging dans une seule transaction. Ce fence
compare aussi la fenetre JSON, `judge_attempt_started` et son owner/reason; un
verdict concurrent ou tardif perdant provoque donc le rollback de ses ecritures
et audits. Le reason
persistant contient `canonical_write_recovery_pending` et l'empreinte courte de
la fenetre. Un retour d'application incoherent apres commit est donc reconnu
avant tout nouveau jugement: le verdict suivant, identique, different ou
`no_change`, n'est jamais consulte. La finalisation expose
`writes_previously_applied=true`; aucune seconde ecriture ni aucun second audit
n'est possible pour cette empreinte. Le fallback historique
`already_covered_by_mutable` reste seulement une verification des etats
anterieurs au verrou transactionnel.

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
