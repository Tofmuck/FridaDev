# Validation DB-only - FridaDev

Date d'execution: `2026-03-23`

Objet: valider sur une fixture reelle que `FridaDev` fonctionne bien en mode `DB-only` pour le state metier, sans reimport JSON legacy, avec conservation correcte apres redemarrage, masquage UI non destructif et purge forte explicite.

## Fixture de validation

Conversation de test creee:

- titre: `DB ONLY VALIDATION 2026-03-23`
- `conversation_id`: `f1156282-11b2-4e1d-831e-e46086ff45f6`

JSON legacy injecte volontairement:

- `legacy_id`: `3b695642-1019-4056-8802-eb0ca3802598`

Contenu prepare dans la fixture:

- `4` messages metier (`user` / `assistant`)
- `4` traces
- `1` resume SQL
- `1` identity
- `1` identity_evidence
- `1` arbiter_decision

## Etape 1 - Creation et coherence immediate

Resultats observes juste apres creation:

- `conversation_messages=5`
  - `1` system
  - `4` messages metier
- `traces=4`
- `summaries=1`
- `identities=1`
- `identity_evidence=1`
- `arbiter_decisions=1`

Verifications metier:

- le bloc resume est bien injecte dans le prompt reconstruit ;
- les messages couverts par le resume ne reapparaissent pas dans la fenetre active ;
- un message plus recent reste bien present ;
- le JSON legacy a bien ete cree comme appat de test.

Verdict:

- creation OK ;
- reconstruction contexte/resume OK ;
- ecriture primaire bien en base.

## Etape 2 - Redemarrage du conteneur

Action:

- redemarrage de `FridaDev`

Resultats observes:

- conteneur revenu `healthy`
- racine HTTP: `200`
- `GET /api/conversations/f1156282-11b2-4e1d-831e-e46086ff45f6/messages`: `200`
- `GET /api/conversations/3b695642-1019-4056-8802-eb0ca3802598/messages`: `404`

Interpretation:

- la conversation valide survit bien au redemarrage via la base ;
- le faux JSON legacy n'est pas reimporte ;
- le runtime ne ressuscite donc plus de conversation depuis `state/conv/*.json`.

Verdict:

- reprise apres redemarrage OK ;
- absence de reimport JSON OK.

## Etape 3 - Export technique DB-only

Validation realisee:

- export technique reconstruit directement depuis PostgreSQL

Contenu exporte avec succes:

- `conversation_present=true`
- `messages=5`
- `traces=4`
- `summaries=1`
- `identities=1`
- `identity_evidence=1`
- `arbiter_decisions=1`

Interpretation:

- la base contient bien assez d'information pour reconstruire un export technique coherent sans dependre d'un JSON de conversation.

Verdict:

- export technique DB-only OK.

## Etape 4 - Suppression UI / masquage

Validation realisee:

- suppression via l'endpoint UI standard

Resultats observes:

- `DELETE /api/conversations/<id>` deja execute avec succes dans le scenario
- `GET /api/conversations/<id>/messages` apres masquage: `200`
- conversation absente de la liste standard
- conversation presente dans `include_deleted=1`
- `deleted_flag=true` en base

Etat des donnees apres masquage:

- `conversation_messages=5`
- `traces=4`
- `summaries=1`
- `identities=1`
- `identity_evidence=1`
- `arbiter_decisions=1`

Interpretation:

- le masquage UI est bien non destructif ;
- la conversation sort du front standard ;
- toute la memoire associee reste en base.

Verdict:

- suppression UI = masquage uniquement: OK.

## Etape 5 - Purge forte explicite

Action:

- purge forte via `conv_store.delete_conversation()`

Resultats observes:

- `purge_ok=true`
- `legacy_file_removed=true`
- `GET /api/conversations/<id>/messages` apres purge: `404`
- `GET /api/conversations/<legacy_id>/messages` apres purge: `404`
- conversation absente meme de `include_deleted=1`

Etat des donnees apres purge:

- `conversations=0`
- `conversation_messages=0`
- `traces=0`
- `summaries=0`
- `identities=0`
- `identity_evidence=0`
- `arbiter_decisions=0`

Interpretation:

- la purge forte actuelle est pleinement destructive sur tous les objets lies a la conversation ;
- elle nettoie bien la conversation, ses messages, ses traces, son resume, sa couche identitaire liee et la telemetrie associee.

Verdict:

- purge forte technique actuelle: OK du point de vue implementation ;
- mais voir le gap ci-dessous vis-a-vis de la politique cible.

## Gap connu

Le scenario valide un point important:

- le code actuel de purge forte est plus destructif que la politique cible retenue pour la memoire consolidee.

Concretement :

- `delete_conversation()` supprime aujourd'hui aussi `identities` et `identity_evidence` lies a la conversation ;
- cela contredit la cible produit plus recente, qui veut une lecture des divergences en tensions temporelles et une memoire consolidee plus conservatrice.

Conclusion sur ce gap:

- tant que la purge forte reste une operation technique exceptionnelle et non exposee comme geste produit normal, le systeme reste exploitable ;
- avant d'exposer une vraie purge forte dans l'admin produit, ce comportement devra etre aligne.

## Verdict global

Le scenario `DB-only` est valide sur les points suivants:

- creation de conversation en base
- persistance des messages
- persistance des traces
- persistance du resume SQL
- persistance des identites et evidences
- persistance d'une decision d'arbitrage
- reprise apres redemarrage
- absence de reimport JSON legacy
- export technique coherent depuis la base
- masquage UI non destructif
- purge forte explicite fonctionnelle

Le seul ecart notable restant n'est pas un echec du scenario, mais un ecart entre :

- le comportement actuel de la purge forte
- et la politique cible de memoire consolidee / tensions temporelles

En l'etat, le chantier `DB-only` peut etre considere comme valide techniquement, avec ce `known gap` explicitement documente.
