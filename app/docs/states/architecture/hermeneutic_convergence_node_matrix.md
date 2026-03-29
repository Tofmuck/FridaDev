# Noeud de convergence hermeneutique - matrice des briques

Date: 2026-03-29
Statut: cadrage architectural operatoire
Document parent: `app/docs/states/architecture/hermeneutic_convergence_node.md`

## 1. Regle de lecture

Cette matrice fige la lecture suivante:

- les briques existantes continuent a renseigner directement le LLM principal;
- en parallele, ces briques deviennent des entrees canoniques du dispositif cible;
- le dispositif cible est en 2 etages:
  - noeud primaire de convergence;
  - agent hermeneutique de validation (juge de revision);
- la chaine cible est: `determinants -> noeud primaire -> validation -> aval`;
- l'agent de validation est souverain sur la validation finale du verdict;
- les criteres restent fixes par les contrats normatifs (pas d'auto-legislation runtime);
- la sortie aval cible inclut des `pipeline_directives_final` (pas des directives provisoires brutes);
- modele cible de reference pour la validation: `GPT-5.4`.

## 2. Tableau principal - briques deja la / a venir

| Brique | Statut actuel dans `FridaDev` | Alimente deja le LLM principal ? | Role cible | Famille code cible | Travail requis |
| --- | --- | --- | --- | --- | --- |
| Temps / grounding temporel | Deja la (`NOW`, `TIMEZONE`, `delta_t_label`, `_silence_label`) | Oui | Entree canonique | `inputs/` | Canoniser l'objet `temps` sans casser l'injection directe |
| Memoire RAG (traces recuperees) | Deja la (`retrieve`) | Oui | Entree canonique | `inputs/` | Stabiliser `memoire_retrieved` |
| Arbitrage memoire (decisions) | Deja la (`filter_traces_with_diagnostics`) | Oui (indirect) | Entree canonique distincte | `inputs/` | Stabiliser `memory_arbitration` distinct de la memoire recuperee |
| Resume actif | Deja la | Oui | Entree canonique | `inputs/` | Canoniser portee et autorite |
| Identite statique + dynamique | Deja la | Oui | Entree canonique | `inputs/` | Stabiliser autorite relative |
| Contexte recent | Deja la | Oui | Entree canonique | `inputs/` | Stabiliser statut de source faible |
| Web | Deja la | Oui | Entree canonique | `inputs/` | Canoniser fraicheur, autorite, conflit potentiel |
| Fenetre recente conversationnelle | Deja la mais diffuse | Oui | Entree canonique | `inputs/` | Extraire format propre |
| Demande utilisateur / intention | Pas encore canonique | Oui (texte brut) | Entree canonique | `inputs/` | Creer qualification minimale |
| Stimmung / M6 | Externe a `FridaDev` | Non | Determinant d'entree (non souverain) | `inputs/` + `doctrine/` | Distinguer explicitement contrat d'entree (`inputs/stimmung.py`) et gouvernance (`doctrine/stimmung_governance.py`) |
| Regime epistemique | Manquant | Non | Sortie primaire doctrinale | `doctrine/` | Creer module doctrinal |
| Posture de jugement | Manquant | Non | Sortie primaire doctrinale | `doctrine/` | Creer module doctrinal `answer|clarify|suspend` |
| Hierarchie des sources | Manquante | Non | Sortie primaire doctrinale | `doctrine/` | Creer module doctrinal |
| Conflits inter-sources | Manquants | Non | Sortie primaire doctrinale | `doctrine/` | Creer module doctrinal |
| Regime discursif + resituation + mode temporel | Manquants | Non | Sortie primaire doctrinale | `doctrine/` | Creer module doctrinal de sortie incluant `time_reference_mode` |
| Etat persistant du noeud | Manquant | Non | Runtime primaire | `runtime/` | Creer store et inertie |
| Noeud primaire de convergence | Manquant | Non | Produit verdict premier + directives provisoires | `runtime/` | Creer orchestration primaire + contrat fail-open primaire |
| Agent hermeneutique de validation | Manquant | Non | Revision finale (`confirm|challenge|clarify|suspend`) | `validation/` | Creer agent final + table de combinaison normative + format `pipeline_directives_final` + cadre budget/timeout/fail-open/circuit breaker |
| Branchement aval sur verdict valide | Manquant | Non | Consommation aval du verdict revise | `runtime/` | Interdire la consommation directe d'un verdict primaire brut et imposer `pipeline_directives_final` |
| Observabilite dispositif complet | Partielle (locale) | Non | Traçabilite primaire + validation | `runtime/` + `validation/` | Etendre observabilite sans inflation |

## 3. Tableau operationnel - nature du travail

| Nature de travail | Briques concernees | Resultat attendu |
| --- | --- | --- |
| A canoniser depuis l'existant | Temps, memoire recuperee, arbitrage memoire, resume, identite, contexte, web | Contrats d'entree stables et lisibles |
| A extraire depuis l'existant | Fenetre recente, demande utilisateur brute, signaux d'ambiguite | Objets d'entree autonomes pour le noeud primaire |
| A integrer depuis l'autre systeme | Stimmung / M6 | Determinant encadre en 2 artefacts: contrat d'entree (`inputs`) + gouvernance (`doctrine`) |
| A creer from scratch | Regimes doctrinaux, hierarchie, conflits, noeud primaire, etat runtime, validation agent | Dispositif complet `primaire + validation` |
| A brancher apres creation | Branchement aval et observabilite complete | Aval consomme une sortie revisee uniquement |

## 4. Structure code cible (documentaire)

Structure cible (non creee dans cette tranche):

- `app/core/hermeneutic_node/inputs/`
  - contrats d'entree canoniques et traduction runtime.
- `app/core/hermeneutic_node/doctrine/`
  - modules doctrinaux issus des specs normatives.
- `app/core/hermeneutic_node/runtime/`
  - noeud primaire, etat persistant, wiring technique, branchement aval.
- `app/core/hermeneutic_node/validation/`
  - agent hermeneutique de validation et sorties de revision.

## 5. Priorite logique de construction

Ordre recommande:

1. Canoniser les entrees deja presentes.
2. Extraire `fenetre_recente` et `demande_utilisateur`.
3. Integrer `Stimmung` comme determinant non souverain (entree `inputs` + gouvernance `doctrine`).
4. Construire la doctrine primaire (`epistemic`, `judgment`, `source_priority`, `source_conflicts`, `discursive`, `resituation`).
5. Construire le runtime du noeud primaire (verdict premier + directives provisoires + fail-open).
6. Construire l'etat persistant du noeud primaire.
7. Construire l'agent hermeneutique de validation (`GPT-5.4` cible) avec table de combinaison normative et cadre operationnel.
8. Brancher l'aval sur verdict revise uniquement (`pipeline_directives_final`).
9. Finaliser l'observabilite du dispositif complet.
10. Envisager ensuite une shadow globale du pipeline.

## 6. Consequence architecturale immediate

Le chantier ne vise plus un seul bloc "noeud".
Il vise un dispositif explicite:

- converger d'abord vers un noeud primaire lisible et testable;
- puis imposer une validation de revision avant la consommation aval;
- et transformer explicitement `pipeline_directives_provisional` en `pipeline_directives_final`;
- sans laisser l'agent de validation redefinir librement les criteres doctrinaux.
