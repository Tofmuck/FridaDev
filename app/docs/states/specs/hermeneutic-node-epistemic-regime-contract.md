# Hermeneutic Node Epistemic Regime Contract

Statut: draft normatif ouvert
Portee: contrat doctrinal minimal pour `epistemic_regime`, `proof_regime` et `uncertainty_posture`

## 1. Purpose

Cette spec fixe le socle doctrinal minimal du Lot 4.

Elle tranche:

- la taxonomie minimale de `epistemic_regime`
- la definition minimale de `proof_regime`
- la definition minimale de `uncertainty_posture`
- les conditions minimales de passage entre classes

Elle ne code rien.
Elle ferme le contrat doctrinal qui devra preceder `app/core/hermeneutic_node/doctrine/epistemic_regime.py`.

## 2. Repo Grounding

Le repo a deja stabilise plusieurs entrees canoniques du noeud sous:

- `app/core/hermeneutic_node/inputs/`

Notamment:

- `time_input.py`
- `recent_window_input.py`
- `user_turn_input.py`
- `stimmung_input.py`

Le Lot 4 change de nature:

- `inputs/` = matieres canoniques que le noeud recoit
- `doctrine/` = logique doctrinale que le noeud elabore

La cible code de ce lot reste donc:

- `app/core/hermeneutic_node/doctrine/epistemic_regime.py`

Et non:

- `app/core/hermeneutic_node/inputs/epistemic_regime_input.py`

## 3. Inputs / Doctrine Boundary

`epistemic_regime`, `proof_regime` et `uncertainty_posture` sont des sorties doctrinales du noeud.

Ils:

- consomment des entrees canoniques deja structurees
- ne constituent pas eux-memes de nouvelles entrees canoniques
- appartiennent au verdict primaire du noeud
- ne sont ni le texte final utilisateur, ni la posture finale aval

Leur calcul peut s'appuyer notamment sur:

- `temps`
- `memory_retrieved`
- `memory_arbitration`
- `resume`
- `identite`
- `contexte_recent`
- `web`
- `tour_utilisateur`
- `stimmung`

Il ne doit pas s'appuyer directement sur:

- le prompt final
- un texte brut deja redige pour l'utilisateur
- une logique aval de validation finale

## 4. Minimal Epistemic Taxonomy

La taxonomie minimale retenue reste:

- `certain`
- `probable`
- `incertain`
- `suspendu`
- `contradictoire`
- `a_verifier`

Cet ensemble est conserve tel quel car il reste:

- deja aligne avec l'architecture de reference
- court
- suffisamment distinctif pour le futur code
- plus robuste qu'une reduction qui fusionnerait des cas differents

Distinctions minimales:

- `certain`
  - convergence forte, stable et suffisante des determinants
  - pas de verification manquante ni de conflit actif
- `probable`
  - lecture dominante defendable, mais encore prudente ou partielle
- `incertain`
  - appui faible, incomplet ou sous-determine, sans conflit frontal explicite
- `a_verifier`
  - le point depend d'une verification identifiable non encore faite
  - typiquement un fait externe, instable, date, norme, chiffre, source a confirmer
- `contradictoire`
  - au moins deux determinants utiles soutiennent des lectures incompatibles sur le meme point
- `suspendu`
  - le noeud ne peut pas stabiliser de lecture responsable a ce tour
  - l'absence de base exploitable ou le blocage restant l'emporte

Raisons de non-fusion:

- `a_verifier` ne se reduit pas a `incertain`, car il indique une voie de verification identifiable
- `contradictoire` ne se reduit pas a `suspendu`, car le conflit lui-meme est un resultat doctrinal utile

## 5. Minimal `proof_regime`

`proof_regime` ne duplique pas `epistemic_regime`.
Il dit quel type d'appui est requis ou suffisant pour tenir la lecture du tour.

Taxonomie minimale retenue:

- `suffisant_en_l_etat`
- `source_explicite_requise`
- `verification_externe_requise`
- `arbitrage_requis`

Definitions minimales:

- `suffisant_en_l_etat`
  - les determinants deja presents suffisent pour soutenir la lecture retenue
- `source_explicite_requise`
  - la lecture peut tenir, mais doit rester ancree dans une source ou un appui nommable
- `verification_externe_requise`
  - la lecture depend d'une verification additionnelle avant assertivite forte
- `arbitrage_requis`
  - un conflit ou une tension de sources doit etre arbitre avant de tenir la lecture

## 6. Minimal `uncertainty_posture`

`uncertainty_posture` dit comment l'incertitude doit etre traitee par le noeud.
Ce n'est pas un simple synonyme du doute.

Taxonomie minimale retenue:

- `discrete`
- `prudente`
- `explicite`
- `bloquante`

Definitions minimales:

- `discrete`
  - l'incertitude residuelle n'a pas besoin d'etre mise au premier plan
- `prudente`
  - la lecture peut tenir, mais avec retenue ou qualification
- `explicite`
  - l'incertitude doit etre dite noir sur blanc dans la suite du traitement
- `bloquante`
  - l'incertitude empeche une tenue substantielle propre du tour

Utilite future minimale:

- preparer Lot 5 sans le pre-decider
- distinguer un doute mineur d'un blocage reel
- permettre au noeud de nuancer sans tout suspendre

## 7. Minimal Decision Rules

### 7.1 Default Discipline

Le noeud ne doit jamais partir de `certain` par defaut.

Discipline minimale:

- base prudente par defaut
- promotion seulement par convergence suffisante
- degradation immediate des qu'un blocage doctrinal apparait

### 7.2 Priority Order Of Blocking Cases

Ordre minimal de lecture:

1. `contradictoire` si un conflit materiel explicite est deja present
2. `a_verifier` si la lecture depend d'une verification identifiable non encore faite
3. `certain` si la convergence est forte, stable et sans blocage
4. `probable` si une lecture domine sans etre encore ferme
5. `incertain` si une lecture existe mais reste trop faible ou trop pauvre
6. `suspendu` si aucune lecture responsable ne peut etre tenue a ce tour

Cet ordre n'est pas une machine a etats exhaustive.
Il fixe seulement les priorites minimales qui empechent un futur code arbitraire.

### 7.3 Minimal Passage Rules

Passages minimaux a retenir:

- `incertain -> probable`
  - si une lecture dominante apparait et qu'aucun conflit materiel n'est actif
- `probable -> certain`
  - seulement si l'appui devient stable, convergent et suffisant en l'etat
- `certain|probable|incertain -> a_verifier`
  - des qu'une verification externe devient necessaire pour tenir la lecture
- `certain|probable|incertain -> contradictoire`
  - des qu'un conflit materiel explicite apparait
- `incertain|a_verifier|contradictoire -> suspendu`
  - si le tour ne permet toujours pas de tenir une lecture responsable dans l'etat

### 7.4 Compatibility Constraints

Contraintes minimales:

- `certain` n'est pas compatible avec `verification_externe_requise`
- `certain` n'est pas compatible avec `arbitrage_requis`
- `certain` n'est pas compatible avec `bloquante`
- `contradictoire` implique `arbitrage_requis`
- `contradictoire` implique `bloquante`
- `a_verifier` implique `verification_externe_requise`
- `a_verifier` implique une posture au moins `explicite`
- `suspendu` n'est pas compatible avec `suffisant_en_l_etat`

## 8. Minimal Output Shape

La forme minimale attendue du bloc doctrinal correspondant est:

```python
{
    "epistemic_regime": "probable",
    "proof_regime": "source_explicite_requise",
    "uncertainty_posture": "prudente",
}
```

Invariants minimaux:

- une valeur unique pour chacun des trois champs
- pas de champ decoratif doctrinal supplementaire a ce stade
- pas de prose libre
- pas de justification longue integree au payload minimal

## 9. Node Usage Boundary

Ces sorties servent a:

- cadrer la tenue epistemique du noeud
- preparer `judgment_posture`
- preparer la hierarchie des sources
- preparer le traitement futur des conflits inter-sources

Elles ne servent pas a:

- rediger la reponse finale utilisateur
- se substituer a `source_priority`
- se substituer a `judgment_posture`
- produire seules des directives finales aval

## 10. Non-goals

Cette spec n'ouvre pas encore:

- la runtime de `epistemic_regime.py`
- la posture de jugement finale
- la hierarchie complete des sources
- le moteur complet de conflits inter-sources
- une machine a etats exhaustive
- la redaction finale de la reponse utilisateur
