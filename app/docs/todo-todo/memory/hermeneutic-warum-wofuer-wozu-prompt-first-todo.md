# Hermeneutic - Warum / Wofür / Wozu prompt-first - mini TODO

Statut: mini-chantier executable livre
Classement: `app/docs/todo-todo/memory/`
Portee: premier pas prompt-first pour inscrire la triade `Warum / Wofür / Wozu` comme discipline de lecture du `validation_agent`
Source doctrinale: `app/docs/todo-todo/memory/hermeneutic-warum-wofuer-wozu-triad-todo.md`
Etat runtime vise: prompt / tests uniquement, sans nouvelle architecture

Note d'execution 2026-05-17:

- V1 livree dans le prompt du `validation_agent` et dans un rappel runtime compact de la tache provider;
- schema de sortie inchange;
- aucune projection directe vers le modele principal, les logs, les read-models ou le dashboard;
- la qualite hermeneutique effective reste a observer en dialogues reels, hors mini-lot.

## 1. Question prealable

> Existe-t-il un meilleur plan qu'ouvrir une grosse roadmap executable pour cette idee ?

Oui.

Le meilleur plan est un mini-chantier en un seul lot:

- inscrire la discipline triadique dans le `validation_agent`;
- garder l'architecture existante;
- ne pas produire de nouvel objet;
- ne pas ouvrir de chantier d'evaluation complet avant d'avoir une V1 sobre a observer en conversation.

## 2. Doctrine reprise

La triade `Warum / Wofür / Wozu` doit agir comme discipline de lecture du texte.

Elle porte sur:

- le dernier enonce;
- le dialogue comme texte total en cours.

Elle doit:

- tenir ensemble les trois questions;
- empecher `Warum` de psychologiser l'utilisateur ou de reconstruire un auteur-totalite;
- empecher `Wofür` de rabattre le texte sur l'utilite ou la consommation;
- empecher `Wozu` de devenir une finalite abstraite souveraine;
- aider le `validation_agent` a mieux relire `validation_dialogue_context`.

Elle ne doit pas:

- creer un nouvel agent;
- creer une nouvelle memoire;
- creer un nouveau JSON;
- ajouter un champ de sortie;
- ouvrir un dashboard;
- lancer une evaluation hermeneutique apres coup;
- projeter directement `Warum / Wofür / Wozu` vers le modele principal en V1.

## 3. Lot unique - prompt-first validation_agent

Statut: [x]

Objectif:

- modifier le contrat prompt du `validation_agent` pour integrer la discipline triadique;
- renforcer tres sobrement la tache runtime construite par `validation_agent._build_messages()` si necessaire;
- garder le schema de sortie strictement inchange.

### 3.1 Patch attendu

Fichiers probables:

- `app/prompts/validation_agent.txt`
- `app/core/hermeneutic_node/validation/validation_agent.py`, seulement si le rappel dans la tache runtime est necessaire
- tests du `validation_agent`

A faire:

- ajouter une consigne breve indiquant que le `validation_agent` lit le `validation_dialogue_context` selon la tension `Warum / Wofür / Wozu`;
- preciser que cette triade porte sur le texte et le dialogue comme texte, pas sur la psychologie de l'utilisateur;
- preciser que les trois questions doivent etre tenues ensemble;
- preciser que `Wozu` ne devient pas un principe souverain;
- conserver la priorite actuelle: `validation_dialogue_context` reste la matiere hermeneutique principale;
- conserver la sortie JSON stricte actuelle.

A ne pas faire:

- ne pas modifier `main_hermeneutical.txt` en V1;
- ne pas ajouter `interpretive_center`;
- ne pas ajouter `warum`, `wofuer`, `wozu` au payload de sortie;
- ne pas modifier `[JUGEMENT HERMENEUTIQUE]`;
- ne pas exposer la triade dans les logs comme nouveau champ;
- ne pas changer la chaine de pouvoir du `validation_agent`.

### 3.2 Schema de sortie inchange

Le lot doit prouver que le modele secondaire continue a ne renvoyer que:

```json
{
  "schema_version": "v1",
  "final_judgment_posture": "answer|clarify|suspend",
  "final_output_regime": "simple|meta",
  "arbiter_reason": "raison_courte_lisible"
}
```

Interdits de sortie:

- `warum`
- `wofuer`
- `wozu`
- `interpretive_center`
- `triad`
- `validation_decision`
- `pipeline_directives_final`

### 3.3 Tests attendus

Ajouter ou adapter des tests pour prouver:

- la discipline triadique est presente dans le contrat du `validation_agent`;
- le prompt rappelle que la triade porte sur le texte, pas sur la psychologie de l'utilisateur;
- le prompt rappelle que les trois questions sont tenues ensemble;
- le prompt ne donne pas de souverainete speciale au seul `Wozu`;
- `_ALLOWED_MODEL_PAYLOAD_KEYS` ou son equivalent continue de refuser tout champ de sortie supplementaire;
- `[JUGEMENT HERMENEUTIQUE]` reste compact et ne projette pas directement `Warum / Wofür / Wozu`;
- les logs/read-models ordinaires ne gagnent aucune fuite de contenu ni aucun dump de triade.

Suites cibles probables:

```bash
docker exec -i -w /app platform-fridadev python -m unittest \
  tests.test_prompt_loader_phase13 \
  tests.unit.core.hermeneutic_node.validation.test_validation_agent \
  tests.test_server_chat_hermeneutic_insertion_contract \
  tests.test_server_chat_compact_observability_contract
```

Adapter la commande si le patch touche moins ou plus de surfaces.

## 4. Condition de non-prolongation

Le mini-chantier se ferme des que:

- la discipline triadique est inscrite proprement dans le `validation_agent`;
- le schema de sortie reste inchange;
- les tests de contrat passent;
- `[JUGEMENT HERMENEUTIQUE]` reste compact;
- aucune nouvelle surface runtime, memoire, dashboard ou observabilite n'a ete ouverte;
- une base propre existe pour observer ensuite la qualite reelle des dialogues.

Ne pas prolonger ce mini-chantier vers:

- un corpus d'evaluation complet;
- une refonte du systeme hermeneutique;
- une trace structuree triadique;
- un dashboard;
- un chantier de reception hermeneutique apres coup;
- Biblio;
- une nouvelle doctrine memoire.

## 5. Ce qui restera a tester en conversation reelle

Les tests unitaires prouveront le contrat, pas encore la qualite hermeneutique effective.

Apres fermeture du mini-lot, il faudra observer en dialogue reel:

- si Frida rate moins souvent le coeur textuel du tour;
- si elle evite mieux les reponses formellement correctes mais localement a cote;
- si elle ne verbalise pas la triade dans ses reponses;
- si elle ne psychologise pas davantage l'utilisateur;
- si le `validation_agent` reste sobre et stable en latence / cout.

Ces observations ne font pas partie du mini-chantier.
