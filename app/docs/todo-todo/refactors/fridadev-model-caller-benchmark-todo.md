# FridaDev - benchmark et organisation progressive des callers modeles - TODO

Statut: actif.

Source de verite de depart:
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`
- `app/docs/states/specs/admin-runtime-settings-schema.md`
- `app/memory/arbiter.py`
- `app/prompts/arbiter.txt`

## Decision de methode

- [x] Ne pas ouvrir un gros chantier global de refonte des modeles d'un seul bloc.
- [x] Ne pas remplacer un modele auxiliaire a l'intuition.
- [x] Avancer caller par caller, avec la sequence: benchmark -> decision -> decouplage si necessaire.
- [x] Garder la possibilite de partager le meme token et le meme projet OpenRouter, meme quand les callers gagnent leur propre modele ou leurs propres parametres.
- [x] Consigner l'horizon global ici, sans creer un deuxieme TODO de decouplage general.

## Horizon global

- [ ] Organiser progressivement les appels OpenRouter de Frida, caller par caller, a partir de benchmarks concrets.
- [ ] Donner a chaque caller important un contrat runtime explicite: modele, parametres et responsabilite propres.
- [ ] Repercuter les resultats des campagnes dans les settings runtime ou dans la documentation de contrat, caller par caller.
- [ ] Conserver un atelier de benchmark durable dans le repo, reutilisable au lieu de scripts jetables.

## Deja traite hors de ce TODO

- [x] LLM principal revu separement.
- [x] Reformulation web decouplee du modele principal et passee a `openai/gpt-5.4-mini`.

## Callers OpenRouter a traiter progressivement

- [ ] Arbitre memoire.
- [ ] Resume conversationnel.
- [ ] Extracteur identity.
- [ ] Agent periodic identity.
- [ ] Stimmung agent primaire.
- [ ] Validation agent primaire.
- [ ] Fallback stimmung: hors priorite pour l'instant.

## Ordre de progression

- [ ] Benchmark arbitre memoire.
- [ ] Decision arbitre memoire: garder, tester plus, exclure ou decoupler.
- [ ] Decouplage eventuel ou necessaire de son slot runtime propre.
- [ ] Benchmark resume conversationnel.
- [ ] Decision resume conversationnel puis decouplage eventuel.
- [ ] Benchmark extracteur identity.
- [ ] Decision extracteur identity puis decouplage eventuel.
- [ ] Benchmark periodic identity.
- [ ] Decision periodic identity puis decouplage eventuel.
- [ ] Benchmark stimmung agent primaire.
- [ ] Decision stimmung agent primaire puis decouplage eventuel.
- [ ] Benchmark validation agent primaire.
- [ ] Decision validation agent primaire puis decouplage eventuel.

On ne benchmarke pas tout d'abord pour decoupler tout plus tard: on avance benchmark -> decision -> decouplage caller par caller.

## Lot 1 - atelier durable + premiere campagne arbitre memoire

- [ ] Creer un repertoire durable `benchmark/` dans le repo.
- [ ] Concevoir `benchmark/` comme un atelier reutilisable pour les callers OpenRouter de Frida, pas comme un script jetable pour l'arbitre memoire.
- [ ] Prevoir un moteur commun d'execution.
- [ ] Prevoir des suites par caller.
- [ ] Prevoir des fixtures propres a chaque caller.
- [ ] Prevoir des scorers propres a chaque caller.
- [ ] Prevoir des sorties comparables communes.
- [ ] Prevoir la conservation des resultats et rapports de campagne.
- [ ] Ne changer aucun modele de production tant que la premiere campagne n'a pas produit son verdict.

## Premiere campagne - arbitre memoire seulement

- [ ] Caller cible: `app/memory/arbiter.py`.
- [ ] Prompt cible: `app/prompts/arbiter.txt`.
- [ ] Comparer exactement `openai/gpt-5.4-mini`, baseline actuelle.
- [ ] Comparer exactement `google/gemini-3.1-flash-lite`.
- [ ] Comparer exactement `qwen/qwen3.6-flash`.
- [ ] Comparer exactement `mistralai/mistral-small-2603`.
- [ ] Ne pas inclure `openai/gpt-5.4-nano` dans cette premiere campagne.
- [ ] Utiliser le meme prompt arbitre pour tous les modeles.
- [ ] Utiliser le meme jeu de fixtures pour tous les modeles.
- [ ] Utiliser `temperature=0`.
- [ ] Utiliser `top_p=1.0`.
- [ ] Utiliser `max_tokens=600`.
- [ ] Utiliser le meme token et le meme projet OpenRouter.
- [ ] Ne faire varier que le modele.

## Fixtures attendues pour l'arbitre memoire

- [ ] Traces clairement utiles.
- [ ] Traces clairement inutiles.
- [ ] Traces ambigues.
- [ ] Bruit conversationnel.
- [ ] Redondance forte avec contexte recent.
- [ ] Souvenirs affectivement proches mais peu utiles.
- [ ] Identite utilisateur.
- [ ] Faux souvenirs.
- [ ] Souvenirs circonstanciels ou temporels: aujourd'hui, hier, ce soir, depuis hier.
- [ ] Cas en francais.

## Mesures minimales

- [ ] JSON valide ou non.
- [ ] Respect du schema.
- [ ] Keep/drop attendu.
- [ ] Faux positifs memoire.
- [ ] Faux negatifs memoire.
- [ ] Latence.
- [ ] Cout estime.
- [ ] Taux d'erreur provider.
- [ ] Remarques qualitatives.
- [ ] Verdict de campagne: garder, tester plus ou exclure.

## Sorties attendues

- [ ] Produire un tableau Markdown lisible pour chaque campagne.
- [ ] Inclure au minimum dans le tableau: modele, score, validite JSON, cout, latence, remarques qualitatives, verdict.
- [ ] Conserver un resultat structure exploitable pour comparer plusieurs campagnes.
- [ ] Documenter le verdict sans masquer les limites du jeu de fixtures.

## Hors scope du cadrage documentaire actuel

- [x] Pas de code benchmark cree dans ce lot documentaire.
- [x] Pas de changement de modele en production.
- [x] Pas de changement aux runtime settings.
- [x] Pas de separation immediate des slots `identity_extractor` / `identity_periodic`.
- [x] Pas de rotation de token.
- [x] Pas de changement de projet OpenRouter.
- [x] Pas de benchmark du resume conversationnel ou des autres callers dans ce lot documentaire.
- [x] Pas de nouveau grand TODO separe pour le decouplage global.

## Definition de fin du Lot 1

- [ ] `benchmark/` existe avec une architecture reutilisable.
- [ ] La suite arbitre memoire est isolee dans l'atelier.
- [ ] Les fixtures arbitre memoire couvrent les familles de cas attendues.
- [ ] Les scorers arbitre memoire mesurent schema, keep/drop, faux positifs, faux negatifs, latence et cout.
- [ ] Les quatre modeles de la premiere campagne ont ete executes avec les memes parametres.
- [ ] Un rapport Markdown de campagne existe.
- [ ] Un verdict caller est documente.
- [ ] Si le verdict l'exige, un lot suivant borne decouple ou ajuste le slot runtime de l'arbitre memoire.

## Definition de fin globale

- [ ] Le chantier global d'organisation des modeles ne pourra pas etre considere comme acheve tant que les resultats des benchmarks n'auront pas ete repercutes caller par caller et que chaque appel modele concerne n'aura pas son propre contrat runtime explicite - modele, parametres et responsabilite propres - tout en pouvant continuer a partager le meme token / projet OpenRouter.
