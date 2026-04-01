# Hermeneutic Node Stimmung Input Contract

Statut: draft normatif ouvert
Portee: contrat d'entree utile pour `FridaDev`, sans importation de la machine `M6` complete

## 1. Purpose

Cette spec fixe le contrat minimal de deux artefacts distincts:

- `affective_turn_signal`
- `stimmung`

Le premier est un signal affectif brut par tour.
Le second est une `stimmung` stabilisee sur plusieurs tours, exposee au noeud comme determinant d'entree pour le regime d'enonciation.

## 2. Repo Grounding

Le repo suit deja une separation stricte entre:

- composants amont de service sous `app/core/`
- inputs canoniques du noeud sous `app/core/hermeneutic_node/inputs/`

Le cadrage retenu pour `stimmung` suit cette separation:

- `app/core/stimmung_agent.py`
  - petit agent LLM amont
  - produit un `affective_turn_signal` par tour
  - ne calcule pas la `stimmung` stabilisee
  - n'est ni la gouvernance affective, ni la sortie finale du noeud
- `app/core/hermeneutic_node/inputs/stimmung_input.py`
  - agrege plusieurs `affective_turn_signal`
  - calcule une `stimmung` dominante / stabilisee

Le noeud hermeneutique recoit `stimmung`.
Il ne recoit ni la machine `M6` complete, ni une gouvernance affective complete importee, ni des directives finales aval.

## 3. Separation Of Responsibility

### 3.1 `affective_turn_signal`

`affective_turn_signal` est un artefact brut par tour.

Il sert a:

- decrire la tonalite affective locale du tour
- laisser coexister plusieurs tonalites
- fournir un materiau simple a stabiliser ensuite

Il ne sert pas a:

- calculer la `stimmung` stabilisee
- appliquer `thresholds`, `delta` ou `hysteresis`
- gouverner le noeud
- produire des directives finales

### 3.2 `stimmung`

`stimmung` est l'input canonique stabilise du noeud.

Il sert a:

- agreger plusieurs `affective_turn_signal`
- retenir une `dominant_tone`
- exposer une stabilite lisible
- signaler un `shift_state`
- fournir au noeud un determinant affectif compact pour le regime d'enonciation

Il ne sert pas a:

- remplacer la hierarchie des sources
- produire a lui seul la posture finale
- importer la souverainete `M6`

## 4. Large Affective Taxonomy

La taxonomie retenue a ce stade est large, englobante et volontairement compacte:

- `apaisement`
- `enthousiasme`
- `curiosite`
- `confusion`
- `frustration`
- `colere`
- `anxiete`
- `decouragement`
- `neutralite`

Regles:

- un `affective_turn_signal` peut contenir plusieurs `tones`
- la taxonomie reste a grands groupes
- pas de micro-taxonomie psychologisante a ce stade

## 5. Minimal Contract For `affective_turn_signal`

Forme minimale attendue:

```python
affective_turn_signal = {
    "schema_version": "v1",
    "present": True,
    "tones": [
        {"tone": "frustration", "strength": 7},
        {"tone": "confusion", "strength": 4},
    ],
    "dominant_tone": "frustration",
    "confidence": 0.82,
}
```

Champs minimaux:

- `schema_version`
  - version du contrat
- `present`
  - signale que le signal a bien ete produit pour le tour
- `tones`
  - liste de tonalites actives
- `tones[].tone`
  - une tonalite de la taxonomie large retenue
- `tones[].strength`
  - intensite simple de `1` a `10`
- `dominant_tone`
  - tonalite dominante du tour si le signal n'est pas vide
- `confidence`
  - confiance compacte du petit agent amont

Invariants:

- `dominant_tone` doit appartenir a `tones` quand `present = True`
- `tones` peut contenir plusieurs `tone`
- `strength` reste un score simple par tour, pas une stabilisation

## 6. Minimal Contract For `stimmung`

Forme minimale attendue:

```python
stimmung = {
    "schema_version": "v1",
    "present": True,
    "dominant_tone": "frustration",
    "active_tones": [
        {"tone": "frustration", "strength": 6},
        {"tone": "confusion", "strength": 3},
    ],
    "stability": "stable",
    "shift_state": "steady",
    "turns_considered": 4,
}
```

Champs minimaux:

- `schema_version`
  - version du contrat
- `present`
  - signale que l'input canonique a bien ete calcule
- `dominant_tone`
  - tonalite dominante retenue apres stabilisation
- `active_tones`
  - tonalites encore actives apres agregation compacte
- `active_tones[].tone`
  - tonalite retenue
- `active_tones[].strength`
  - force compacte issue de la stabilisation, sur la meme echelle simple `1` a `10` que `tones[].strength`
- `stability`
  - statut compact de stabilite
  - forme minimale attendue: `emerging | stable | volatile`
- `shift_state`
  - statut compact de bascule
  - forme minimale attendue: `steady | candidate_shift | shifted`
- `turns_considered`
  - nombre de `affective_turn_signal` recents utilises

Invariants:

- `stimmung` reste compacte et lisible
- `active_tones` n'est pas l'historique complet
- `active_tones[].strength` reste sur une echelle fermee `1` a `10`
- le noeud recoit `stimmung`, pas les signaux bruts complets

## 7. Stabilization Boundary

Les mecanismes suivants appartiennent a `stimmung_input.py`, pas a `stimmung_agent.py`:

- `thresholds`
- `delta`
- `hysteresis`
- choix de `turns_considered`
- calcul de `stability`
- calcul de `shift_state`

Regle structurelle:

- `affective_turn_signal` = signal brut par tour
- `stimmung` = resultat stabilise sur plusieurs tours

La frontiere ne doit pas etre brouillee:

- le petit agent amont ne calcule pas la stabilite
- l'input canonique du noeud ne redevient pas un dump brut des signaux par tour

## 8. Node Usage Boundary

Le noeud peut prendre `stimmung` en consideration pour:

- le regime d'enonciation
- la prudence de transition
- la tonalite generale de reprise

Le noeud ne doit pas traiter `stimmung` comme:

- un souverain unique
- une posture finale
- une sortie aval
- la machine `M6` complete

## 9. Non-goals

Cette spec n'ouvre pas encore:

- une gouvernance affective complete
- une doctrine complete de souverainete ou de priorite
- une importation brute de `M6`
- la runtime complete de `stimmung_agent.py`
- la runtime complete de `stimmung_input.py`
