# Frida - Politique de donnees

Objectif: fixer la cible de stockage durable pour `Frida` avant la migration "DB only" du state metier.

## 1. Principe directeur

La base PostgreSQL locale est la source de verite de `Frida` pour tout le state metier.

Cela signifie:

- aucune conversation metier ne doit dependre d'un fichier JSON comme stockage primaire;
- aucun resume, aucune trace, aucune identite, aucune evidence ni aucun conflit ne doit dependre d'un fichier de state pour survivre a un redemarrage;
- les lectures et ecritures metier doivent converger vers la base;
- les fichiers restants ne doivent servir qu'aux prompts statiques, aux assets et aux logs techniques.

## 2. Ce qui doit vivre en base de donnees

Le state metier cible est le suivant:

- `conversations`
- `conversation_messages`
- `summaries`
- `traces`
- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

En pratique, cela couvre:

- les conversations et leur catalogue;
- les messages utilisateur/assistant/systeme et leurs meta;
- les resumes generes;
- les traces memorisees;
- les identites deduites;
- les evidences associees aux identites;
- les conflits d'identite;
- les decisions d'arbitrage memoire.

## 3. Ce qui reste en fichiers a ce stade

Les fichiers suivants restent volontaires et hors du chantier "DB only" du state metier:

- prompts statiques:
  - `app/prompts/arbiter.txt`
  - `app/prompts/identity_extractor.txt`
- identites statiques de base chargees par configuration:
  - fichiers runtime operateur `state/data/identity/llm_identity.txt` et `state/data/identity/user_identity.txt`
  - ces fichiers locaux constituent la source canonique retenue quand le runtime resout `data/identity/...`
  - ils sont volontairement ignores par Git; le repo ne versionne ici que `*.example.txt` et `README.md`
  - sur OVH, le conteneur consomme cette meme arborescence via le bind mount `/opt/platform/fridadev/state/data -> /app/data`
- assets et front:
  - `app/web/*`
- logs techniques:
  - `state/logs/*.jsonl`

Ces fichiers ne sont pas consideres comme du state conversationnel ou memoire.

## 4. Regles de stockage retenues

- la base de donnees devient la seule source de verite pour le state metier;
- aucun mecanisme de bootstrap ne doit reimporter automatiquement `state/conv/*.json` au demarrage;
- aucun fallback de lecture ne doit retourner vers des JSON si la base ne contient pas une conversation;
- aucune duplication durable du state metier ne doit subsister entre DB et fichiers;
- les marqueurs metier necessaires au fonctionnement des resumes, embeddings et reprises doivent etre persistes explicitement.

## 5. Regles de gouvernance a respecter

Chaque famille de donnees metier doit ensuite avoir des regles explicites pour:

- retention;
- purge;
- anonymisation;
- export;
- suppression ciblee;
- suppression globale si necessaire.

Ces regles seront detaillees dans les sous-cases suivantes de la todo de migration.

## 6. Etat actuel du code

La cible ci-dessus n'est pas encore atteinte.

Le point principal a traiter ensuite est le stockage hybride encore present dans `app/core/conv_store.py`, avec des lectures, ecritures et resynchronisations JSON qui doivent etre retirees pour atteindre un fonctionnement "DB only".
