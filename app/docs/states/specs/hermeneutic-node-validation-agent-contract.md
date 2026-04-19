# Hermeneutic Node Validation Agent Contract

Statut: spec historique partiellement supersedee
Portee: premiere pause normative du Lot 9 pour `validation_agent`, relue a la lumiere du lot 2 runtime

Note runtime 2026-04-19:

- `response-arbiter-power-contract.md` est la source normative recente sur la chaine de pouvoir;
- `validation_agent` produit maintenant directement `final_judgment_posture`, `final_output_regime` et `arbiter_reason`;
- `validation_decision` peut subsister comme trace legacy de compatibilite, mais elle n'est plus la source souveraine du verdict final.
- `validation_dialogue_context` est maintenant livre en runtime comme fenetre dialogique locale canonisee de 5 messages maximum, priorisant le user courant puis le dernier assistant.

## 1. Purpose

Cette spec ouvre la premiere pause normative du Lot 9.

Elle tranchait initialement:

- la nature exacte du `validation_agent`
- sa frontiere avec le noeud primaire, le verdict final et l'aval
- son statut d'agent borne, en une passe, sans autonomie agentique forte en V1
- son entree minimale
- la centralite du contexte dialogique recent elargi dans la relecture
- ses sorties minimales de revision
- sa frontiere minimale avec `pipeline_directives_final`
- son cadre operationnel minimal
- ses besoins minimaux d'observabilite

Le runtime lot 2 a depuis precise:

- que la sortie souveraine est un verdict arbitral final direct;
- que `validation_decision` n'est plus qu'une trace legacy derivee;
- que le wiring aval consomme ce verdict final et non une table de combinaison externe.

## 2. Repo Grounding

Le repo a deja stabilise:

- `primary_verdict`
- `node_state`
- `output_regime`
- la frontiere `primary node -> validation -> aval`
- `recent_context_input`
- `recent_window_input`

Notamment:

- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/hermeneutic_node/inputs/recent_context_input.py`
- `app/core/hermeneutic_node/inputs/recent_window_input.py`

La cible code de cette pause normative est:

- `app/core/hermeneutic_node/validation/validation_agent.py`

Cette spec ne cree ni ce fichier, ni son wiring.

## 3. Primary Node / Validation / Downstream Boundary

Le `validation_agent` intervient:

- apres `primary_node`
- avant tout branchement aval
- avant toute consommation de `pipeline_directives_final`

Il ne:

- produit pas le `primary_verdict`
- ne remplace pas le noeud primaire
- ne remplace pas les contrats doctrinaux deja fermes
- ne vaut pas sortie finale complete a lui seul

Frontiere minimale:

- `runtime/primary_node`
  - produit le `primary_verdict`
- `validation/validation_agent`
  - relit ce verdict, le juge et tranche directement le verdict final arbitral
- `aval`
  - ne consomme pas directement le `primary_verdict`

## 4. Nature Exacte Du `validation_agent`

`validation_agent` est un agent de validation hermeneutique borne.

Il est:

- un juge de revision
- une passe unique de relecture
- un agent contraint
- souverain sur la validation finale

Il n'est pas:

- un agent autonome multi-boucles
- un agent outille
- un agent qui recherche, replannifie ou se relance tout seul
- un second noeud primaire cache
- un auto-legislateur des criteres doctrinaux

Discipline minimale:

- V1 = une passe
- pas d'autonomie agentique forte
- pas de second systeme de regles cache
- pas de rederivation libre du noeud primaire

## 5. Minimal Validation Input Contract

L'entree minimale du `validation_agent` est une enveloppe structuree qui comprend:

- `primary_verdict`
- un artefact frere de `justifications`
- un `validation_dialogue_context`
- les entrees canoniques pertinentes du tour

`pipeline_directives_provisional` reste une matiere explicite de validation,
mais elle est lue dans `primary_verdict`.
Cette V1 ne duplique donc pas ce bloc dans un second transport parallele.

Forme minimale de lecture:

```python
{
    "primary_verdict": {...},
    "justifications": {...},
    "validation_dialogue_context": {...},
    "canonical_inputs": {...},
}
```

Regles minimales:

- `primary_verdict` reste l'entree canonique primaire du jugement
- `justifications` restent hors `primary_verdict`
- `validation_dialogue_context` ne vaut pas side input faible
- les entrees canoniques pertinentes restent disponibles pour relire le verdict dans son cadre

## 6. Decision Retenue Pour Le Contexte Dialogique Recent Elargi

La decision normative retenue est:

- le `validation_agent` ne doit pas juger sur le seul `primary_verdict`
- il doit recevoir un contexte dialogique recent elargi
- ce contexte est la matiere hermeneutique principale de la relecture

Support retenu en V1:

- un artefact validation-side distinct: `validation_dialogue_context`

Grounding minimal de cet artefact:

- `recent_context_input` constitue la base existante la plus propre
- `recent_window_input` peut rester une vue compacte secondaire
- `recent_window_input` ne suffit pas seul comme matiere principale de validation

Raison:

- `recent_context_input` garde une matiere dialogique recente en messages apres cutoff de resume
- `recent_window_input` compresse cette matiere en une petite fenetre utile au noeud primaire
- la validation a besoin d'une fenetre plus large et hermeneutiquement lisible

Contrat runtime livre au lot 3:

- `validation_dialogue_context` retient au maximum 5 messages `user` / `assistant`;
- le tour utilisateur courant est prioritaire;
- le dernier message assistant disponible est prioritaire;
- les messages immediatement precedents completent ensuite la fenetre;
- la troncature elimine d'abord le plus ancien hors priorites absolues;
- le payload compact expose aussi `source_message_count`, `truncated`, `current_user_retained`, `last_assistant_retained`.

Regle forte:

- le `validation_dialogue_context` peut conduire a `confirm`, `challenge`, `clarify` ou `suspend` un `primary_verdict` pourtant structurellement propre

## 7. Minimal Arbiter Verdict

Le contrat runtime minimal de l'arbitre est maintenant:

- `final_judgment_posture`
- `final_output_regime`
- `arbiter_reason`

Taxonomies minimales:

- `final_judgment_posture`
  - `answer`
  - `clarify`
  - `suspend`
- `final_output_regime`
  - `simple`
  - `meta`

Regles fortes:

- le verdict final vient directement de l'arbitre;
- `meta` n'est pas une consequence mecanique de `clarify`;
- `validation_decision` peut subsister comme trace legacy derivee, mais elle ne gouverne plus l'aval.

## 8. Boundary With `pipeline_directives_final`

Le `validation_agent`:

- recoit un `primary_verdict` qui contient `pipeline_directives_provisional`
- ne transmet pas ces directives telles quelles a l'aval
- produit un verdict arbitral final qui sert ensuite de base a `pipeline_directives_final`

Depuis le lot 2 runtime:

- la table de combinaison entre primaire et validation n'est plus souveraine;
- `pipeline_directives_final` derive du verdict final arbitral;
- le bloc `[JUGEMENT HERMENEUTIQUE]` est projete depuis cette sortie finale.

## 9. Minimal Operational Frame

Cadre minimal retenu:

- budget token explicite et borne par passe
- timeout dur par passe
- fail-open explicite et auditable
- circuit breaker explicite si echecs ou cout/latence se repetent
- cible de cout/latence compatible avec un usage conversationnel interactif

Discipline minimale:

- pas de seconde passe implicite
- pas de boucle auto-relancee
- le fail-open de validation ne doit pas se maquiller en `confirm`
- cette spec ne fixe pas encore de seuils chiffres

Modele cible de reference en V1:

- `GPT-5.4`

## 10. Minimal Observability

Les signaux minimaux a journaliser sont maintenant au moins:

- `dialogue_messages_count`
- `dialogue_truncated`
- `current_user_retained`
- `last_assistant_retained`
- `primary_judgment_posture`
- `primary_output_regime_proposed`
- `final_judgment_posture`
- `final_output_regime`
- `arbiter_followed_upstream`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `applied_hard_guards`
- `arbiter_reason`
- `projected_judgment_posture`
- `decision_source`
- `reason_code` si present

Ne doivent jamais etre journalises brutement:

- le `validation_dialogue_context` complet
- le dump brut du contexte dialogique recent elargi
- les `justifications` longues
- les entrees canoniques completes comme seconde memoire de logs

Regle forte:

- l'observabilite de validation ne doit pas creer un dispositif parallele de stockage brut du dialogue recent

## 11. Non-goals

Cette pause normative ne ferme pas encore:

- `validation_agent.py`
- le contrat complet du verdict final post-validation
- la table complete de combinaison normative
- le wiring aval
- l'observabilite complete du dispositif final
- la shadow globale
