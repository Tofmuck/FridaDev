# Hermeneutic Node Source Conflict Contract

Statut: draft normatif ouvert
Portee: contrat doctrinal minimal pour `source_conflicts`

## 1. Purpose

Cette spec fixe le socle doctrinal minimal du Lot 7.

Elle tranche:

- la nature exacte de `source_conflicts`
- la taxonomie minimale des conflits inter-sources residuels
- le seuil strict de detection
- l'issue doctrinale minimale retenue
- le lien explicite avec Lot 6, Lot 4 et Lot 5
- le format compact de sortie

Elle ne code rien.
Elle ferme le contrat doctrinal qui devra preceder `app/core/hermeneutic_node/doctrine/source_conflicts.py`.

## 2. Repo Grounding

Le repo a deja stabilise:

- les entrees canoniques du noeud sous `app/core/hermeneutic_node/inputs/`
- un contrat doctrinal pour `source_priority`
- un contrat doctrinal pour `epistemic_regime`
- un contrat doctrinal pour `judgment_posture`

Notamment:

- `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- `app/docs/states/specs/hermeneutic-node-epistemic-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-judgment-posture-contract.md`

Le Lot 7 reste dans le meme cadre:

- `inputs/` = matieres canoniques recues par le noeud
- `doctrine/` = logique doctrinale elaboree par le noeud

La cible code de ce lot reste donc:

- `app/core/hermeneutic_node/doctrine/source_conflicts.py`

Et non:

- `app/core/hermeneutic_node/inputs/source_conflicts_input.py`

## 3. Inputs / Doctrine Boundary

`source_conflicts` est une sortie doctrinale du noeud.

Il:

- consomme des entrees canoniques deja structurees
- ne constitue pas une nouvelle entree canonique
- ne duplique pas `source_priority`
- ne duplique pas `epistemic_regime`
- ne constitue pas encore un moteur complet de resolution
- detecte et explicite des conflits residuels entre sources encore recevables

`source_conflicts` n'est pas l'endroit ou l'on refait la priorisation normale du Lot 6.

Il n'est pas non plus l'endroit ou l'on transforme toute divergence en contradiction epistemique.

## 4. Nature Exacte De `source_conflicts`

Un conflit inter-sources du Lot 7 n'est pas toute divergence.

Il faut distinguer:

- divergence ordinaire
- priorisation normale
- cohabitation normale
- conflit residuel explicite

Regle doctrinale minimale:

- si le Lot 6 suffit a departager un ecart, il n'y a pas de conflit Lot 7
- si `temps` suffit a requalifier une source comme stale ou non pertinente, il n'y a pas de conflit Lot 7
- si deux sources cohabitent legitimement sans porter sur le meme point, il n'y a pas de conflit Lot 7

Le Lot 7 ne traite donc que le residu non absorbe par:

- `source_priority`
- `temps`
- la cohabitation doctrinale normale

## 5. Minimal Taxonomy

La taxonomie minimale retenue est:

- `conflit_factuel`
- `conflit_de_continuite_dialogique`
- `conflit_d_ancrage_de_source`
- `conflit_de_validite_temporelle`

Cette taxonomie est retenue telle quelle car elle reste:

- courte
- directement codable
- suffisamment differenciee pour le runtime futur
- plus stable qu'une liste trop fine de micro-sous-types

Definitions minimales:

- `conflit_factuel`
  - au moins deux sources encore recevables soutiennent des contenus incompatibles sur le meme point factuel
- `conflit_de_continuite_dialogique`
  - plusieurs sources recevables portent une incompatibilite sur ce qui a ete etabli, prefere ou decide dans le fil du dialogue
- `conflit_d_ancrage_de_source`
  - plusieurs sources recevables imposent des ancrages de source incompatibles sur le meme point
- `conflit_de_validite_temporelle`
  - plusieurs sources recevables soutiennent des lectures incompatibles parce qu'elles ne valent pas au meme regime de validite temporelle et que `temps` ne suffit pas a absorber l'ecart

## 6. Strict Detection Threshold

Le seuil de detection doit rester strict.

Il y a conflit Lot 7 seulement si:

1. au moins deux sources parlent du meme point
2. elles portent une incompatibilite reelle
3. elles restent toutes deux recevables apres application normale du Lot 6
4. l'ecart n'est pas deja absorbe par `source_priority`, `temps` ou la cohabitation normale

Discipline minimale:

- une simple divergence de nuance ne suffit pas
- une simple dissymetrie de rang ne suffit pas
- une simple absence de support dans une source ne suffit pas
- une simple disponibilite d'une source non retenue ne suffit pas
- une simple tension entre sources heterogenes sans meme these commune ne suffit pas

## 7. Minimal Issue

Dans cette premiere version normative, l'issue minimale d'un conflit inter-source residuel est:

- `clarify`

`prioriser` est explicitement ecarte comme issue du Lot 7, car la priorisation normale appartient deja au Lot 6.

`suspend` est explicitement ecarte comme issue normale du Lot 7, car la suspension appartient au blocage epistemique ou probatoire du jugement.

Important:

- un conflit inter-source residuel peut nourrir `judgment_posture = clarify`
- il ne doit pas, a lui seul, pousser automatiquement vers `judgment_posture = suspend`
- si un cas plus dur conduit un jour a `suspend`, cela devra venir d'un blocage doctrinal additionnel, pas du seul fait qu'un conflit residuel existe

## 8. Link With Lot 6

Le Lot 6 precede logiquement le Lot 7.

`source_priority` traite:

- l'ordre par defaut
- les renversements minimaux
- les cohabitations normales

`source_conflicts` ne traite que le residu non absorbe apres cette lecture.

Regles minimales:

- une divergence ordinaire absorbee par le Lot 6 n'est pas un conflit Lot 7
- le Lot 7 ne reouvre pas `prioriser` comme issue
- l'egalite de rang du Lot 6 n'est pas encore, a elle seule, un conflit Lot 7

## 9. Link With Lot 4

`source_conflicts` ne se confond pas avec `epistemic_regime = contradictoire`.

Difference minimale:

- `source_conflicts`
  - detecte un conflit residuel entre sources encore recevables
  - vise prioritairement une clarification
- `contradictoire`
  - designe un etat epistemique plus dur, plus rare et plus bloquant
  - peut impliquer `arbitrage_requis` et `bloquante`

Regle minimale:

- un conflit Lot 7 peut exister sans imposer `contradictoire`
- un conflit Lot 7 ne doit pas automatiquement pousser vers `a_verifier` ou `suspendu`

## 10. Link With Lot 5

Le lien doctrinal minimal avec Lot 5 est le suivant:

- un conflit inter-source residuel appelle une clarification explicite
- cette clarification reste un regime de parole
- elle n'est ni une non-reponse, ni un abort de tour, ni une formule vide

`source_conflicts` doit donc pouvoir nourrir:

- `judgment_posture = clarify`

Sans confusion avec:

- `judgment_posture = suspend`

## 11. Minimal Output Shape

La forme minimale attendue est:

```python
{
    "source_conflicts": [
        {
            "conflict_type": "conflit_factuel",
            "sources": ["memoire", "web"],
            "issue": "clarify",
        }
    ]
}
```

Invariants minimaux:

- `source_conflicts` est une liste
- chaque conflit porte un `conflict_type` compact
- chaque conflit nomme explicitement les `sources` en cause
- chaque conflit porte une `issue` explicite
- aucune prose longue n'est attendue dans le payload minimal

En l'absence de conflit residuel detecte, la forme minimale attendue est:

```python
{
    "source_conflicts": []
}
```

## 12. Non-goals

Cette spec n'ouvre pas encore:

- le runtime de `source_conflicts.py`
- le moteur complet de resolution des conflits
- une narration longue des conflits source par source
- le retour de `prioriser` comme issue du Lot 7
- le retour de `suspend` comme issue normale du Lot 7
- une theorie generale de toute divergence entre sources
