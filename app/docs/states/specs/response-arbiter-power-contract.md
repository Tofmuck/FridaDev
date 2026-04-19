# Response Arbiter Power Contract

Statut: spec vivante
Portee: lot 1 normatif pour la chaine de pouvoir cible de l'arbitrage de reponse
Nature: source de verite normative du lot 1 pour le pouvoir institutionnel et le minimum d'observabilite

Note runtime:
- le lot 2 runtime applique maintenant cette chaine de pouvoir;
- `validation_agent` emet directement le verdict final arbitral;
- `validation_decision` peut subsister comme trace legacy de compatibilite, mais sans souverainete.
- le lot 4 runtime explicite maintenant l'amont comme `upstream_advisory` structuree, lue comme recommendation non souveraine.

## 1. Purpose

Cette spec ferme le lot 1 documentaire du chantier `LLM-dominant response arbiter`.

Elle tranche noir sur blanc:

- la chaine de pouvoir actuelle et sa limite institutionnelle;
- la chaine de pouvoir cible;
- la distinction normative entre garde-fous durs, analyse amont conseillere et arbitre LLM dominant;
- la souverainete cible du `validation_agent`;
- la priorite de lecture locale et le statut exceptionnel de `meta`;
- la matiere principale de l'arbitre;
- le contrat minimal d'observabilite requis pour ouvrir les lots 2+.

Elle ne code rien.
Elle ne requalifie pas encore le runtime.
Elle n'ouvre pas une refonte generale de l'observabilite.

## 2. Repo Grounding

Cette spec est ancree notamment dans:

- `app/docs/todo-todo/memory/llm-dominant-response-arbiter-todo.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-user-demand-contract.md`
- `app/prompts/validation_agent.txt`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/tests/unit/logs/test_chat_turn_logger_phase2.py`
- `app/tests/test_server_phase14.py`

Le TODO actif reste la roadmap du chantier.
Cette spec devient la source de verite normative du lot 1.

Depuis le lot 2 runtime:

- `validation_agent` produit directement `final_judgment_posture`, `final_output_regime` et `arbiter_reason`;
- `[JUGEMENT HERMENEUTIQUE]` est projete depuis ce verdict final arbitral;
- le seam compact `validation_agent` rend visible le suivi vs override, le verdict final et le verdict projete.

## 3. Chaine De Pouvoir Actuelle

Aujourd'hui, le pouvoir est trop precontraint en amont:

1. les couches deterministes amont produisent deja une posture et un regime fortement structurants;
2. `validation_agent` intervient tard, avec un contrat encore borne autour de `validation_decision`;
3. le verdict final projete reste derive d'un couloir deja ferme en amont.

Dans cet etat:

- l'amont ne conseille pas seulement, il ferme trop souvent le couloir de sortie;
- `validation_agent` n'est pas encore l'arbitre souverain de la posture finale;
- `meta` peut etre active trop facilement comme consequence pratique d'une difficulte ordinaire.

## 4. Chaine De Pouvoir Cible

La chaine de pouvoir cible est la suivante:

1. des garde-fous durs, rares et non cassables, bornent seulement les cas extremes;
2. l'analyse amont conserve une autorite reelle mais non souveraine;
3. le `validation_agent` reinstitue devient l'arbitre LLM dominant de la posture finale de reponse.

Regle forte:

- le `validation_agent` a le dernier mot sur la posture finale de reponse;
- l'amont pese, alerte et recommande, mais ne tranche pas a sa place;
- seuls les garde-fous durs peuvent interdire `answer`.

## 5. Pouvoir Des Trois Etages

### 5.1 Garde-fous durs non cassables

Les garde-fous durs:

- sont rares;
- restent deterministes;
- peuvent interdire `answer`;
- ne forcent pas a eux seuls un regime `meta`;
- ne retirent pas a l'arbitre le choix entre `clarify` et `suspend`.

Leur role est de borner le couloir autorise, pas d'ecrire eux-memes la reponse.

Liste runtime retenue au lot 5:

- `explicit_url_not_read`
  - une URL explicite est ciblee mais `web_input.read_state` dit que la page n'a pas ete lue directement;
  - effet: `answer` interdit.
- `external_verification_missing`
  - `primary_verdict.proof_regime = verification_externe_requise` et aucune preuve externe admissible n'est effectivement disponible dans `web_input`;
  - effet: `answer` interdit.

Familles explicitement non retenues comme garde-fous durs au lot 5:

- les `source_conflicts` generiques restent amont-conseillers tant qu'aucun signal runtime distinct de contradiction materielle haute n'est stabilise;
- payload arbitral invalide ou contexte insuffisant relevent du fail-open de validation, pas d'un garde-fou laissant le choix entre `clarify` et `suspend`.

### 5.2 Analyse amont a autorite non souveraine

L'amont conserve une autorite reelle.
Il peut:

- structurer le tour;
- signaler des alertes;
- proposer une posture;
- proposer un regime;
- remonter des conflits ou des contraintes.

Mais cette autorite est non souveraine:

- elle n'a pas le dernier mot;
- elle ne ferme pas seule le couloir final hors garde-fous durs;
- elle est lue comme recommendation structuree, pas comme verdict final.

Forme runtime minimale livree au lot 4:

- `primary_verdict` transporte un bloc `upstream_advisory`;
- ce bloc porte au minimum la posture recommandee, le regime propose, les familles de signaux actives et un indicateur simple de contrainte amont;
- la validation et les logs compacts lisent ce bloc comme source de verite de la recommendation amont;
- les champs doctrinaux top-level du `primary_verdict` peuvent subsister transitoirement pour compatibilite, mais ils ne requalifient pas l'amont en couche souveraine.

Nettoyage runtime livre au lot 5:

- `a_verifier` et `verification_externe_requise` ne suspendent plus a eux seuls l'amont;
- `source_conflicts.issue` reste neutre (`review_required`) au lieu d'encoder une posture;
- `pipeline_directives_provisional` ne requalifie plus un `source_conflict` en pseudo-verrou `clarify`.

### 5.3 Arbitre LLM dominant

Le `validation_agent` reinstitue est l'institution cible de l'arbitrage final.

Il doit:

- lire d'abord la matiere dialogique locale;
- lire ensuite les recommandations amont comme indices secondaires;
- choisir `final_judgment_posture`;
- choisir `final_output_regime`;
- pouvoir suivre ou casser l'amont;
- rester borne par les garde-fous durs.

## 6. Priorite De Lecture Et Statut De `meta`

Par defaut, l'arbitre doit privilegier:

- la lecture la plus naturelle du tour;
- la continuite dialogique locale;
- la reponse simple.

Il ne monte vers `clarify`, `suspend` ou `meta` que si cette lecture echoue reellement.

Regle normative:

- `meta` devient exceptionnel;
- `meta` n'est plus une consequence mecanique de `clarify`;
- `meta` n'est plus un regime ordinaire de gestion des difficultes locales.

## 7. Matiere Principale Et Contextes Secondaires

La matiere principale de l'arbitre est une fenetre dialogique locale canonisee de 5 messages `user` / `assistant` maximum.

Priorites normatives:

- priorite absolue au tour utilisateur courant;
- priorite absolue au dernier message assistant;
- priorite forte aux tours immediatement precedents;
- perte du plus ancien avant perte du plus local en cas de troncature.

Contrat runtime minimal du lot 3:

- seuls des messages `user` / `assistant` canoniques entrent dans `validation_dialogue_context`;
- le tour utilisateur courant doit etre retenu chaque fois qu'il existe;
- le dernier message assistant doit etre retenu chaque fois qu'il existe;
- les messages immediatement precedents completent la fenetre jusqu'a 5;
- si plus de 5 messages sont disponibles, la troncature elimine d'abord le plus ancien hors priorites absolues;
- si aucun dernier assistant n'existe, aucun faux assistant n'est invente.

Le reste du contexte est secondaire et indiciaire, notamment:

- signaux amont;
- posture proposee;
- regime propose;
- `source_conflicts`;
- `identity`;
- `memory`;
- `summary`;
- `web`;
- `time`.

Ces matieres secondaires peuvent peser.
Elles ne doivent pas ecraser le bon sens dialogique local.

## 8. Expression Vernaculaire Des Limites

Quand une contrainte borne la reponse, la forme discursive doit rester libre dans le couloir autorise.

Regles normatives:

- un garde-fou dur peut interdire `answer`;
- il ne force pas a lui seul une sortie meta-systemique;
- l'arbitre peut exprimer la limite de facon vernaculaire, dialogique et locale;
- la contrainte borne la reponse, elle ne dicte pas a elle seule un discours bureaucratique.

## 9. Projection Finale

Le verdict projete dans `[JUGEMENT HERMENEUTIQUE]` doit etre le verdict final de l'arbitre.

Regles normatives:

- si l'arbitre suit l'amont, le bloc projete reflete ce verdict final;
- si l'arbitre casse l'amont, c'est le verdict final de l'arbitre qui est projete;
- aucune recommendation amont ne doit redevenir souveraine au moment de la projection finale.

## 10. Contrat Minimal De Sortie Cible

Le futur arbitre final doit produire directement au minimum:

- `final_judgment_posture`
- `final_output_regime`
- `applied_hard_guards`
- `hard_guard_effect`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `arbiter_reason`

Champ de transition accepte en lot 2:

- `validation_decision`
  - peut subsister comme trace legacy derivee du verdict final et des recommandations amont;
  - ne porte plus l'autorite normative du couloir final.

Ce contrat de sortie reste volontairement minimal au lot 1.
Il fixe la matiere obligatoire.
Il ne fige pas encore le schema runtime detaille ni le transport technique final.

## 11. Contrat Minimal D'Observabilite

Le chantier ne repart pas de zero.
Il reutilise d'abord:

- `chat_turn_logger` comme seam canonique de logs de tour;
- `hermeneutic_node_logger` comme seam compact de pipeline;
- `test_chat_turn_logger_phase2.py` et `test_server_phase14.py` comme seams de preuve existants.

Le minimum obligatoire pour ouvrir les lots 2+ est un contrat compact, testable, proche de l'existant.

### 11.1 Champs minimaux requis

Les traces minimales doivent rendre visibles au moins:

- `upstream_recommendation_posture`
- `upstream_output_regime_proposed`
- `upstream_active_signal_families`
- `upstream_constraint_present`
- `dialogue_messages_count`
- `dialogue_truncated`
- `current_user_retained`
- `last_assistant_retained`
- `final_judgment_posture`
- `final_output_regime`
- `arbiter_followed_upstream`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `applied_hard_guards`
- `hard_guard_effect`
- `arbiter_reason`
- `projected_judgment_posture`

### 11.2 Lecture attendue

Ce contrat minimal doit permettre de voir sans replay implicite:

- combien de messages dialogiques ont ete retenus;
- si une troncature de la fenetre locale a eu lieu;
- si le tour utilisateur courant a bien ete retenu;
- si le dernier message assistant a bien ete retenu;
- si l'arbitre a suivi l'amont;
- si l'arbitre a casse l'amont;
- quel garde-fou dur a borne la decision, si present;
- quel verdict final a ete retenu;
- quel verdict a ete effectivement projete;
- quelle raison lisible accompagne la decision.

### 11.3 Niveau obligatoire des lots 1 et 2

Des le lot 1:

- les champs minimaux requis doivent etre fixes noir sur blanc;
- les seams existants a reutiliser doivent etre nommes noir sur blanc;
- la preuve minimale doit etre `logs compacts + tests`.

Des le lot 2:

- la sortie arbitralement finale doit rendre visible le suivi vs override de l'amont;
- les garde-fous appliques doivent etre observables;
- le verdict final projete doit etre observable;
- une raison lisible doit accompagner la decision.

Ce contrat n'impose pas encore:

- une nouvelle surface admin;
- une nouvelle infrastructure de logs;
- une taxonomie exhaustive de tous les `reason_code`;
- un schema runtime detaille final au-dela du minimum requis.

## 12. Ce Que Le Lot 1 Fige Et Ce Qu'il Laisse Ouvert

Le lot 1 fige:

- la chaine de pouvoir cible;
- la souverainete du `validation_agent` comme institution cible;
- le statut non souverain de l'amont;
- le role rare et non cassable des garde-fous durs;
- le statut exceptionnel de `meta`;
- la fenetre locale de 5 tours comme matiere principale;
- l'expression vernaculaire des limites;
- le minimum d'observabilite requis pour ouvrir les lots 2+.

Le lot 1 ne tranche pas encore:

- le schema technique final exact du payload arbitral;
- le detail exhaustif des garde-fous durs;
- la forme finale de tous les champs de logs;
- une surface admin dediee;
- le naming final du module si un renommage devient un jour utile.
