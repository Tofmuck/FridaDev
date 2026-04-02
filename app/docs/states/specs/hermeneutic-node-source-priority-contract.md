# Hermeneutic Node Source Priority Contract

Statut: draft normatif ouvert
Portee: contrat doctrinal minimal pour `source_priority`

## 1. Purpose

Cette spec fixe le socle doctrinal minimal du Lot 6.

Elle tranche:

- la nature exacte de `source_priority`
- l'ordre par defaut retenu entre les familles de sources
- le statut particulier de `tour_utilisateur` et `temps`
- la regle interne `static > dynamic` pour `identity`
- les renversements minimaux de priorite
- les cas minimaux de cohabitation sans fusion abusive
- le format compact de sortie

Elle ne code rien.
Elle ferme le contrat doctrinal qui devra preceder `app/core/hermeneutic_node/doctrine/source_priority.py`.

## 2. Repo Grounding

Le repo a deja stabilise plusieurs entrees canoniques du noeud sous:

- `app/core/hermeneutic_node/inputs/`

Notamment:

- `time_input.py`
- `memory_retrieved_input.py`
- `memory_arbitration_input.py`
- `summary_input.py`
- `identity_input.py`
- `recent_context_input.py`
- `user_turn_input.py`
- `stimmung_input.py`
- `web_input.py`

Le Lot 6 reste dans le meme cadre que les Lots 4 et 5:

- `inputs/` = matieres canoniques recues par le noeud
- `doctrine/` = logique doctrinale elaboree par le noeud

La cible code de ce lot reste donc:

- `app/core/hermeneutic_node/doctrine/source_priority.py`

Et non:

- `app/core/hermeneutic_node/inputs/source_priority_input.py`

## 3. Inputs / Doctrine Boundary

`source_priority` est une sortie doctrinale du noeud.

Elle:

- consomme des entrees canoniques deja structurees
- ne constitue pas une nouvelle entree canonique
- ne duplique ni `epistemic_regime`, ni `proof_regime`, ni `judgment_posture`
- ne constitue pas encore le moteur complet de resolution des conflits inter-sources
- fixe une regle explicite de priorite et de cohabitation entre determinants

Elle peut s'appuyer notamment sur:

- `time_input`
- `memory_retrieved` et `memory_arbitration`
- `summary_input`
- `identity_input`
- `recent_context_input`
- `user_turn_input`
- `user_turn_signals`
- `stimmung_input`
- `web_input`

Elle ne doit pas s'appuyer directement sur:

- le prompt final
- la reponse deja redigee
- les logs d'observabilite
- un moteur implicite de fusion totale des sources

## 4. Default Priority Order

La formulation retenue est:

- une liste ordonnee de rangs avec egalites explicites

Cette forme est retenue car elle reste:

- compacte
- directement codable
- compatible avec des egalites explicites
- suffisante pour le Lot 6 sans ouvrir deja le moteur de conflits du Lot 7

Ordre par defaut retenu:

1. `tour_utilisateur`
2. `temps`
3. `memoire`, `contexte_recent`, `identity`
4. `resume`
5. `web`
6. `stimmung`

Important:

- `tour_utilisateur` et `temps` ne sont pas des preuves du monde au meme sens que `memoire` ou `web`;
- ils occupent pourtant les deux premiers rangs car ils cadrent doctrinalement ce qu'il est legitime de privilegier;
- l'ordre par defaut vaut en l'absence de raison explicite de renversement;
- une egalite de rang n'autorise pas une fusion silencieuse des sources.

Forme minimale attendue:

```python
{
    "source_priority": [
        ["tour_utilisateur"],
        ["temps"],
        ["memoire", "contexte_recent", "identity"],
        ["resume"],
        ["web"],
        ["stimmung"],
    ]
}
```

## 5. Internal Rule For `identity`

`identity` reste une seule famille de source au niveau top-level.

Elle ne doit pas etre separee en deux sources doctrinales distinctes du type:

- `identite_stable`
- `identite_dynamique`

Regle interne minimale retenue:

- `static > dynamic`

Cette regle vaut pour les deux cotes deja exposes par `identity_input.py`:

- `frida`
- `user`

Effets minimaux:

- une constante `static` prime sur une entree `dynamic` si les deux divergent
- une entree `dynamic` peut nuancer, contextualiser ou actualiser
- une entree `dynamic` ne doit pas a elle seule renverser une constante `static` sans autre appui

## 6. Minimal Conditional Reversals

Le Lot 6 ne fixe pas encore un moteur complet de conflits.
Il fixe seulement des renversements minimaux de priorite.

### 6.1 `web`

`web` reste de faible priorite par defaut.

Il remonte fortement lorsque le tour porte sur:

- un contenu instable ou date
- une actualite, un prix, une disponibilite, une norme, un chiffre
- une verification identifiable
- un besoin explicite de source externe
- un regime probatoire qui appelle une preuve `scientifique` ou `factuelle` de provenance externe explicite

Un simple fait que `web` soit disponible n'en fait pas une source souveraine par defaut.

### 6.2 `memoire`

`memoire` remonte lorsque le tour porte sur:

- une reprise conversationnelle
- un souvenir partage
- une preference deja etablie dans le dialogue
- une continuite dialogique longue qui ne peut pas etre tenue par le seul contexte recent

### 6.3 `contexte_recent`

`contexte_recent` remonte lorsque le point decisif se joue:

- dans les tous derniers tours
- dans une correction locale
- dans une regulation immediate
- dans ce qui vient d'etre dit ou decide a l'instant

### 6.4 `identity`

`identity` remonte lorsque la question porte surtout sur:

- la forme de parole
- le registre relationnel
- les preferences stables
- les contraintes de structure ou de ton

`identity` ne remonte pas comme autorite factuelle sur le monde.

### 6.5 `resume`

`resume` peut remonter comme secours de continuite lorsque:

- les traces recentes utiles manquent
- une continuite longue doit etre tenue
- une memoire plus fine n'est pas disponible a ce tour

`resume` ne devient pas pour autant une source souveraine.

### 6.6 `stimmung`

`stimmung` peut remonter pour l'enonciation:

- regime de parole
- cout d'une transition
- niveau de retenue ou de douceur

Elle ne remonte jamais comme autorite factuelle devant `memoire`, `web` ou `temps`.

## 7. Link With `tour_utilisateur`

`tour_utilisateur` a une priorite doctrinale speciale de cadrage.

Il ne vaut pas comme preuve du monde.
Il dit plutot quel arbitrage de sources devient legitime.

Regles minimales:

- `geste_dialogique_dominant` oriente la lecture du bon type d'appui, sans prouver a lui seul le contenu
- `regime_probatoire.types_de_preuve_attendus` peut faire remonter `web`, `memoire` ou `resume` selon le type de preuve attendu
- `regime_probatoire.provenances` peut faire remonter la famille correspondante:
  - `dialogue_trace` -> `memoire`
  - `dialogue_resume` -> `resume`
  - `web` -> `web`
- `qualification_temporelle` peut faire remonter `temps` et, conditionnellement, `web`
- un signal `ancrage_de_source` pousse a expliciter la bonne source au lieu de melanger silencieusement plusieurs appuis

Discipline minimale:

- `tour_utilisateur` peut renverser l'ordre par defaut
- `tour_utilisateur` ne transforme pas une source faible en preuve suffisante

## 8. Link With `temps`

`temps` ne prime pas comme contenu.
Il prime comme condition de validite, de recence et de formulation.

Il sert notamment a:

- qualifier si un contenu est stable ou instable
- qualifier si une trace memoire est encore recevable telle quelle
- qualifier si `web` doit remonter pour verifier un point actuel ou date
- cadrer le relatif et l'absolu dans la reprise du tour

Regle minimale:

- `temps` peut faire descendre une source de contenu qui serait trop stale sur un point instable
- `temps` ne devient pas une source factuelle autonome

## 9. Minimal Cohabitation Rules

Le Lot 6 doit permettre plusieurs cohabitations minimales sans pseudo-source composite.

Cas minimaux a retenir:

- `memoire` + `contexte_recent`
  - la memoire porte la continuite longitudinale, le contexte recent porte l'immediat local
- `memoire` + `identity`
  - la memoire rappelle, `identity` contraint la relation ou la preference stable
- `web` + `temps`
  - `web` apporte la matiere externe, `temps` qualifie sa recence et sa validite
- `resume`
  - support de continuite et de secours, sans absorber les autres sources
- `stimmung`
  - modulation de parole, jamais fusionnee comme source de verite

Regles minimales:

- la cohabitation ne vaut pas fusion
- l'egalite de rang ne vaut pas resolution du conflit
- un conflit explicite entre sources reste du ressort du Lot 7

## 10. Minimal Output Invariants

Le payload minimal attendu doit respecter:

- un seul champ `source_priority`
- une liste ordonnee de rangs
- des egalites explicites a l'interieur d'un meme rang
- des familles de source nommees explicitement
- aucune prose libre
- aucune tentative d'encoder deja tout le moteur de conflits

## 11. Non-goals

Cette spec n'ouvre pas encore:

- le runtime de `source_priority.py`
- le moteur complet de resolution des conflits
- une hierarchie ponderee fine source par source
- une scission top-level de `identity` en deux sources distinctes
- un regime `web-first` par defaut
- une souverainete epistemique de `stimmung`
- la formulation finale de la reponse utilisateur
