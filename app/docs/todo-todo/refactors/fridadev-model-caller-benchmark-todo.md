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
- [x] Avancer caller par caller, avec la sequence: benchmark -> decision -> decouplage propre du caller.
- [x] Garder la possibilite de partager le meme token et le meme projet OpenRouter, meme quand les callers gagnent leur propre modele ou leurs propres parametres.
- [x] Consigner l'horizon global ici, sans creer un deuxieme TODO de decouplage general.

## Horizon global

- [ ] Organiser progressivement les appels OpenRouter de Frida, caller par caller, a partir de benchmarks concrets.
- [ ] Individualiser chaque caller important avec son propre point d'appel ou module, son modele, ses parametres et son contrat runtime.
- [ ] Repercuter les resultats des campagnes dans les settings runtime ou dans la documentation de contrat, caller par caller.
- [x] Conserver un atelier de benchmark durable dans le repo, reutilisable au lieu de scripts jetables.

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

- [x] Benchmark arbitre memoire.
- [x] Campagne finale bornee arbitre memoire avant decouplage.
- [x] Decision arbitre memoire: garder, tester plus, exclure ou decoupler.
- [ ] Decouplage propre de l'arbitre memoire: point d'appel, modele et parametres locaux.
- [ ] Benchmark resume conversationnel.
- [ ] Decision resume conversationnel.
- [ ] Decouplage propre du resume conversationnel.
- [ ] Benchmark extracteur identity.
- [ ] Decision extracteur identity.
- [ ] Decouplage propre de l'extracteur identity.
- [ ] Benchmark periodic identity.
- [ ] Decision periodic identity.
- [ ] Decouplage propre de periodic identity.
- [ ] Benchmark stimmung agent primaire.
- [ ] Decision stimmung agent primaire.
- [ ] Decouplage propre du stimmung agent primaire.
- [ ] Benchmark validation agent primaire.
- [ ] Decision validation agent primaire.
- [ ] Decouplage propre du validation agent primaire.

On ne benchmarke pas tout d'abord pour decoupler tout plus tard: on avance benchmark -> decision -> decouplage caller par caller, puis caller suivant.

## Lot 1 - atelier durable + premiere campagne arbitre memoire

- [x] Creer un repertoire durable `benchmark/` dans le repo.
- [x] Concevoir `benchmark/` comme un atelier reutilisable pour les callers OpenRouter de Frida, pas comme un script jetable pour l'arbitre memoire.
- [x] Prevoir un moteur commun d'execution.
- [x] Prevoir des suites par caller.
- [x] Prevoir des fixtures propres a chaque caller.
- [x] Prevoir des scorers propres a chaque caller.
- [x] Prevoir des sorties comparables communes.
- [x] Prevoir la conservation des resultats et rapports de campagne.
- [x] Ne changer aucun modele de production tant que la premiere campagne n'a pas produit son verdict.

## Premiere campagne - arbitre memoire seulement

- [x] Caller cible: `app/memory/arbiter.py`.
- [x] Prompt cible: `app/prompts/arbiter.txt`.
- [x] Comparer exactement `openai/gpt-5.4-mini`, baseline actuelle.
- [x] Comparer exactement `google/gemini-3.1-flash-lite`.
- [x] Comparer exactement `qwen/qwen3.6-flash`.
- [x] Comparer exactement `mistralai/mistral-small-2603`.
- [x] Ne pas inclure `openai/gpt-5.4-nano` dans cette premiere campagne.
- [x] Utiliser le meme prompt arbitre pour tous les modeles.
- [x] Utiliser le meme jeu de fixtures pour tous les modeles.
- [x] Utiliser `temperature=0`.
- [x] Utiliser `top_p=1.0`.
- [x] Utiliser `max_tokens=600`.
- [x] Utiliser le meme token et le meme projet OpenRouter.
- [x] Ne faire varier que le modele.

## Constat apres campagne diagnostique arbitre memoire

- [x] Requalifier la premiere campagne comme examen de passage initial.
- [x] Constater qu'elle ne suffit pas comme examen final: 8 cas, 12 candidats, quatre modeles a 100%.
- [x] Ne pas decider le decouplage arbitre sur cette seule campagne trop facile.

## Campagne finale bornee - arbitre memoire

- [x] Manche 1: 40 cas distincts, quatre modeles, 160 appels maximum.
- [x] Manche 1: 24 cas reels anonymises ou reformules.
- [x] Manche 1: 16 cas artificiels durs.
- [x] Finale: 60 cas reserves distincts de la manche 1.
- [x] Finale: deux finalistes seulement, 120 appels maximum.
- [x] Finale: 40 cas reels anonymises ou reformules.
- [x] Finale: 20 cas artificiels durs.
- [x] Garder le meme prompt, les memes fixtures par manche et les memes parametres: `temperature=0`, `top_p=1.0`, `max_tokens=600`.
- [x] Donner plus de poids aux faux positifs memoire qu'aux faux negatifs: faux positif poids 2, faux negatif poids 1.
- [x] Produire un classement de pertinence pure.
- [x] Produire un classement rapport pertinence / cout / latence.
- [x] Produire une analyse des divergences entre modeles.
- [x] Produire une recommandation documentee sans changer la production.
- [x] Resultat de campagne: `mistralai/mistral-small-2603` gagne la finale en pertinence pure et en rapport pertinence / cout / latence.
- [x] Comparaison baseline: `openai/gpt-5.4-mini` ne passe pas en finale.
- [x] Recommandation: basculer vers `mistralai/mistral-small-2603` devient defendable au prochain lot de decouplage, sans changement prod dans ce lot.

## Fixtures attendues pour l'arbitre memoire

- [x] Traces clairement utiles.
- [x] Traces clairement inutiles.
- [x] Traces ambigues.
- [x] Bruit conversationnel.
- [x] Redondance forte avec contexte recent.
- [x] Souvenirs affectivement proches mais peu utiles.
- [x] Identite utilisateur.
- [x] Faux souvenirs.
- [x] Souvenirs circonstanciels ou temporels: aujourd'hui, hier, ce soir, depuis hier.
- [x] Cas en francais.

## Mesures minimales

- [x] JSON valide ou non.
- [x] Respect du schema.
- [x] Keep/drop attendu.
- [x] Faux positifs memoire.
- [x] Faux negatifs memoire.
- [x] Latence.
- [x] Cout estime.
- [x] Taux d'erreur provider.
- [x] Remarques qualitatives.
- [x] Verdict de campagne: garder, tester plus ou exclure.

## Sorties attendues

- [x] Produire un tableau Markdown lisible pour chaque campagne.
- [x] Inclure au minimum dans le tableau: modele, score, validite JSON, cout, latence, remarques qualitatives, verdict.
- [x] Conserver un resultat structure exploitable pour comparer plusieurs campagnes.
- [x] Documenter le verdict sans masquer les limites du jeu de fixtures.

## Hors scope respecte dans le Lot 1

- [x] Pas de changement de modele en production.
- [x] Pas de changement aux runtime settings.
- [x] Pas de separation immediate des slots `identity_extractor` / `identity_periodic`.
- [x] Pas de rotation de token.
- [x] Pas de changement de projet OpenRouter.
- [x] Pas de benchmark du resume conversationnel ou des autres callers dans le Lot 1.
- [x] Pas de nouveau grand TODO separe pour le decouplage global.

## Definition de fin du Lot 1

- [x] `benchmark/` existe avec une architecture reutilisable.
- [x] La suite arbitre memoire est isolee dans l'atelier.
- [x] Les fixtures arbitre memoire couvrent les familles de cas attendues.
- [x] Les scorers arbitre memoire mesurent schema, keep/drop, faux positifs, faux negatifs, latence et cout.
- [x] Les quatre modeles de la premiere campagne ont ete executes avec les memes parametres.
- [x] Un rapport Markdown de campagne existe.
- [x] La campagne finale de departage a ete executee: manche 1 `40 x 4`, finale `60 x 2`.
- [x] Un verdict caller est documente avec classement de pertinence, classement valeur, divergences et recommandation.
- [ ] Le lot suivant borne individualise l'arbitre memoire avant de passer au resume conversationnel: point d'appel clair, modele propre, parametres propres et contrat runtime propre.

## Definition de fin globale

- [ ] Le chantier global d'organisation des modeles ne pourra pas etre considere comme acheve tant que les resultats des benchmarks n'auront pas ete repercutes caller par caller et que chaque appel modele important n'aura pas ete individualise avec son propre point d'appel ou module, son modele propre, ses parametres propres et son contrat runtime propre - tout en pouvant continuer a partager le meme token / projet OpenRouter.
