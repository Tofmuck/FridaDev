# Hermeneutic Node Validation Agent Contract

Statut: draft normatif ouvert
Portee: premiere pause normative du Lot 9 pour `validation_agent`

## 1. Purpose

Cette spec ouvre la premiere pause normative du Lot 9.

Elle tranche:

- la nature exacte du `validation_agent`
- sa frontiere avec le noeud primaire, le verdict final et l'aval
- son statut d'agent borne, en une passe, sans autonomie agentique forte en V1
- son entree minimale
- la centralite du contexte dialogique recent elargi dans la relecture
- ses sorties minimales `confirm|challenge|clarify|suspend`
- sa frontiere minimale avec `pipeline_directives_final`
- son cadre operationnel minimal
- ses besoins minimaux d'observabilite

Elle ne code rien.
Elle ne ferme ni `validation_agent.py`, ni le contrat complet du verdict final post-validation, ni le wiring aval.

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
  - relit ce verdict, le juge et prepare la revision finale
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

Regle forte:

- le `validation_dialogue_context` peut conduire a `confirm`, `challenge`, `clarify` ou `suspend` un `primary_verdict` pourtant structurellement propre

## 7. Minimal Review Decisions

Les sorties minimales de revision retenues sont:

- `confirm`
- `challenge`
- `clarify`
- `suspend`

Definitions minimales:

- `confirm`
  - le verdict primaire peut servir de base a la sortie revisee
- `challenge`
  - le verdict primaire est juge materiellement insuffisant ou mal oriente et doit etre corrige
- `clarify`
  - la sortie revisee doit passer par une clarification explicite
- `suspend`
  - la sortie revisee ne peut pas valider une reponse normale dans l'etat courant

Discipline minimale:

- ces decisions appartiennent a la validation finale
- elles ne redoublent pas la doctrine du noeud primaire

## 8. Boundary With `pipeline_directives_final`

Le `validation_agent`:

- recoit un `primary_verdict` qui contient `pipeline_directives_provisional`
- ne transmet pas ces directives telles quelles a l'aval
- contribue ensuite a la production de `pipeline_directives_final`

Cette pause normative ne ferme pas encore:

- le contrat exact de `pipeline_directives_final`
- la table complete de combinaison normative
- le format complet de la sortie finale revisee

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

Les signaux minimaux a journaliser plus tard sont:

- la decision de validation
- `fail_open`
- un statut synthetique de budget/timeout
- un statut synthetique de circuit breaker
- un signal synthetique de cout/latence

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
