# Noeud de convergence hermeneutique - matrice des briques

Date: 2026-03-29
Statut: cadrage architectural operatoire
Document parent: `app/docs/states/architecture/hermeneutic_convergence_node.md`

## 1. Regle de lecture

Cette matrice fige la lecture suivante :

- les briques existantes continuent a renseigner directement le LLM principal ;
- en parallele, ces memes briques doivent devenir des entrees canoniques du futur noeud ;
- le noeud ne remplace donc pas les injections de prompt ;
- le noeud sert de registre de discours, d'arbitrage inter-sources, et de derive des regimes de reponse.

## 2. Tableau principal - briques deja la / a venir

| Brique | Statut pour le futur noeud | Materialisation actuelle dans `FridaDev` | Alimente deja le LLM principal ? | Statut d'entree pour le noeud | Travail requis |
| --- | --- | --- | --- | --- | --- |
| Temps / grounding temporel | Deja la | `NOW`, `TIMEZONE`, `delta_t_label`, `_silence_label`, bloc `[RÉFÉRENCE TEMPORELLE]` | Oui, directement dans le prompt augmente | Entree presque disponible | Canoniser l'objet d'entree temps pour le noeud sans casser l'injection directe |
| Memoire RAG | Deja la | retrieval vectoriel des traces via `memory_traces_summaries.retrieve()` | Oui, via `[Mémoire — souvenirs pertinents]` | Entree partiellement disponible | Exposer les traces retenues avec leur statut et leur autorite pour le noeud |
| Arbitrage memoire | Deja la | `arbiter.filter_traces_with_diagnostics()` + decisions logguees | Oui, indirectement, via la selection de souvenirs injectes | Entree partiellement disponible | Stabiliser une sortie canonique "decision memoire" lisible par le noeud |
| Resume actif | Deja la | `summaries` SQL + `_get_active_summary()` + `[Résumé de la période ...]` | Oui, directement | Entree disponible mais faible | Canoniser la portee et l'autorite du resume pour le noeud |
| Identite statique | Deja la | fichiers ressources identite + injection dans `build_identity_block()` | Oui, directement | Entree disponible | Faible travail : l'exposer comme source explicite pour le noeud |
| Identite dynamique | Deja la | `get_identities(...)`, `persist_identity_entries(...)`, preview/persist, conflits identitaires | Oui, directement | Entree partiellement disponible | Rendre plus nette son autorite relative face aux autres sources |
| Contexte recent | Deja la | `get_recent_context_hints(...)` + `[Indices contextuels recents]` | Oui, directement | Entree disponible mais non canonique | Stabiliser son statut de source faible non durable |
| Web | Deja la | `tools/web_search.py`, reformulation, search, crawl, bloc `[RECHERCHE WEB — ...]` | Oui, directement dans le dernier message user | Entree partiellement disponible | Canoniser fraicheur, autorite, conflit de source, degre de confiance |
| Fenetre recente conversationnelle | Deja la mais diffuse | selection des derniers tours dans `chat_memory_flow.py`, `summarizer.py`, `conv_store.py` | Oui, de fait | Entree non canonique | Extraire une vraie brique de fenetre conversationnelle lisible par le noeud |
| Demande utilisateur / intention de tour | Pas encore la comme module | texte user brut seulement | Oui, en brut | Entree manquante | Creer un module de qualification de la demande du tour |
| `Stimmung` / M6 | Pas encore la dans `FridaDev` | existe conceptuellement et techniquement dans `Frida_V4`, pas dans `FridaDev` | Non dans `FridaDev` actuel | Entree manquante | Integrer un equivalent fonctionnel de M6 comme determinant du noeud |
| Regime epistemique | Pas encore la | aucune sortie canonique `certain / probable / incertain / suspendu` | Non | Entree/sortie manquante | Creer from scratch un module ou sous-noeud d'arbitrage epistemique |
| Suspension du jugement / epoke | Pas encore la | pas de sortie canonique `answer | clarify | suspend` | Non | Sortie manquante | Creer une fonction explicite permettant `je ne sais pas` ou `peux-tu preciser ?` quand le cadre ne permet pas de conclure proprement |
| Hierarchie des sources | Pas encore la | seulement des priorites implicites et locales | Non | Fonction centrale manquante | Creer from scratch la logique d'arbitrage inter-sources |
| Conflits inter-sources | Pas encore la | seuls les conflits identitaires existent aujourd'hui | Non | Fonction manquante | Creer un module de conflit entre web/memoire/identite/resume/contexte |
| Preuves typees / `evidence_ref` | Pas encore la | motifs et journaux existent, mais pas de references typees resolubles | Non | Entree manquante | Creer from scratch une couche de preuves typees et resolubles |
| Etat persistant du noeud | Pas encore la | aucun snapshot global du cadre discursif par conversation | Non | Fonction manquante | Creer un store dedie au noeud |
| Sortie regime discursif global | Pas encore la | seulement des contraintes eparses dans prompts et policies locales | Non | Sortie manquante | Creer la sortie canonique du noeud |
| Sortie directives aval | Pas encore la comme ensemble unique | directives locales diffuses, pas de payload central | Non | Sortie manquante | Creer un objet unique de directives pour les modules aval |
| Observabilite du noeud | Pas encore la | bonne observabilite locale des sous-pipelines, mais pas du noeud global | Non | Fonction manquante | Etendre les logs et KPIs une fois le noeud defini |

## 3. Tableau operationnel - nature du travail

| Nature de travail | Briques concernees | Point de depart | Resultat attendu |
| --- | --- | --- | --- |
| Deja pret ou quasi pret | Temps, resume actif, identite statique | Existent deja sous forme exploitable et injectee | Les conserver comme entrees directes du LLM principal et les exposer proprement au noeud |
| A canoniser depuis l'existant | Memoire RAG, arbitrage memoire, identite dynamique, contexte recent, web | La logique existe deja mais la sortie n'est pas encore un objet d'entree stable du noeud | Produire pour chaque brique un contrat d'entree court, stable, lisible |
| A extraire depuis des fichiers existants | Fenetre recente conversationnelle, demande utilisateur brute, autorite relative implicite des sources | La matiere est deja dans le code, mais diffusee dans plusieurs fichiers ou usages | Isoler des modules ou objets d'entree autonomes pour le noeud |
| A integrer depuis l'autre systeme | `Stimmung` / M6 | Le cadrage existe dans `Frida_V4`, pas dans `FridaDev` | Faire de M6 un determinant du noeud, sans confondre M6 et le noeud |
| A creer from scratch | Regime epistemique, suspension du jugement, hierarchie des sources, conflits inter-sources, preuves typees, etat persistant du noeud, sortie regime global, directives aval unifiees | Rien de vraiment canonique aujourd'hui dans `FridaDev` | Construire les briques centrales qui transforment l'assemblage actuel en pipeline complet |
| A brancher seulement apres creation du noeud | Observabilite globale du noeud, shadow globale du pipeline complet | Les sous-pipelines sont bien loggues, mais pas le noeud global | Instrumenter et mesurer seulement quand le noeud existe vraiment |

## 4. Tableau "ce qui est deja la" vs "ce qui est a venir"

| Ce qui est deja la | Ce qui est a venir |
| --- | --- |
| Temps / grounding temporel | `Stimmung` / M6 dans `FridaDev` |
| Memoire RAG | Qualification de la demande utilisateur |
| Arbitrage memoire | Regime epistemique explicite |
| Resume actif | Suspension du jugement / epoke explicite |
| Identite statique | Hierarchie des sources |
| Identite dynamique | Conflits inter-sources |
| Contexte recent | Preuves typees / `evidence_ref` |
| Web | Etat persistant du noeud |
| Fenetre recente conversationnelle (matiere deja la, forme non canonique) | Sortie regime discursif globale |
| Demande utilisateur / intention de tour | Sortie `answer | clarify | suspend` |
| Autorite relative des sources (aujourd'hui implicite) | Sortie unifiee de directives aval |

## 5. Tableau "a extraire" vs "a creer from scratch"

| A extraire / canoniser depuis l'existant | A creer from scratch |
| --- | --- |
| Objet d'entree `temps` a partir du grounding actuel | Module d'arbitrage epistemique |
| Objet d'entree `demande_utilisateur` a partir du tour brut | Sortie canonique `judgment_posture` (`answer | clarify | suspend`) |
| Objet d'entree `memoire` a partir du retrieval + arbiter | Module de hierarchie des sources |
| Objet d'entree `resume` a partir du resume actif actuel | Module de conflit inter-sources |
| Objet d'entree `identite` a partir du bloc identitaire actuel | Systeme de preuves typees resolubles |
| Objet d'entree `contexte_recent` a partir des context hints | Store persistant du noeud |
| Objet d'entree `web` a partir de la recherche actuelle | Sortie canonique `discursive_regime` |
| Objet `fenetre_recente` a extraire du flux actuel | Sortie canonique `epistemic_regime` |
| Statut d'autorite implicite des sources | Sortie canonique `proof_regime` |
| Signaux d'ambiguite et de sous-determination de la demande | Payload unique de `pipeline_directives` |

## 6. Consequence architecturale immediate

La consequence immediate de cette matrice est la suivante :

- `FridaDev` n'est pas vide ;
- le futur noeud ne part pas de zero ;
- mais les briques centrales qui font de cet assemblage un systeme complet ne sont pas encore la ;
- il faut donc construire d'abord les modules manquants du noeud, pas lancer trop tot une validation globale du pipeline complet.

## 7. Priorite logique de construction

Ordre recommande a ce stade :

1. Canoniser les entrees deja presentes.
2. Extraire la fenetre recente conversationnelle et la qualification de la demande.
3. Integrer `Stimmung` comme determinant.
4. Creer l'arbitrage epistemique.
5. Creer la sortie `answer | clarify | suspend`.
6. Creer la hierarchie des sources.
7. Creer les conflits inter-sources.
8. Creer l'etat persistant du noeud.
9. Creer la sortie unique du noeud.
10. Brancher les directives aval.
11. Seulement ensuite envisager une shadow globale du pipeline complet.
