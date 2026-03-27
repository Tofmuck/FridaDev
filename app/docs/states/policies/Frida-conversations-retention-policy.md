# Politique de retention et de purge - Conversations Frida

Objet: definir la politique cible pour `conversations` et `conversation_messages` dans `FridaDev`, en coherente avec la regle deja posee:

- la base PostgreSQL est la seule source de verite ;
- la suppression demandee depuis l'UI ne doit pas detruire immediatement la conversation ;
- les messages suivent le cycle de vie de leur conversation parente.

## Perimetre

Cette politique couvre :

- `conversations`
- `conversation_messages`

Elle ne couvre pas encore en detail :

- `traces`
- `summaries`
- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

Ces familles de donnees feront l'objet des sous-points suivants.

## Etats de vie retenus

Une conversation peut exister dans trois etats logiques.

### 1. Active

Etat normal.

- visible dans l'UI standard ;
- relue par `/api/conversations` sans `include_deleted` ;
- messages visibles via `/api/conversations/<id>/messages`.

### 2. Masquee

Etat obtenu lors d'une suppression demandee depuis l'UI.

- la conversation reste en base ;
- `deleted_at` est renseigne dans `conversations` ;
- elle disparait des listes standardes ;
- elle peut encore etre relue par les outils techniques/admin qui demandent explicitement `include_deleted`.

Important :

- une suppression UI signifie "masquer", pas "detruire".

### 3. Purgee

Etat final et destructif.

- la conversation est supprimee physiquement de la base ;
- ses `conversation_messages` sont supprimes avec elle ;
- et, dans l'implementation actuelle, les donnees liees a cette conversation sont purgees aussi (`traces`, `summaries`, `identity_evidence`, `arbiter_decisions`, identites rattachees et conflits correspondants).

## Regles de retention

### Conversations actives

Retention par defaut :

- conservation sans limite de duree tant que la conversation reste active.

Justification :

- `Frida` est un outil de travail et de recherche ;
- la perte automatique d'une conversation active serait plus nocive qu'utile ;
- la conservation locale en base ne pose pas ici de contrainte produit immediate.

Donc :

- aucune purge automatique ne doit viser les conversations actives par defaut.

### Conversations masquees

Retention par defaut :

- conservation sans limite de duree en base.

Effet attendu :

- la conversation reste recuperable techniquement ;
- elle n'apparait plus dans l'UI standard ;
- elle demeure dans la base comme source brute du systeme.

Justification :

- dans `Frida`, la suppression UI est un masquage de presentation ;
- la source brute ne doit pas sortir de la base par defaut ;
- le moteur peut continuer a s'appuyer sur ce corpus meme si l'UI standard le masque.

## Regles de suppression

### Suppression par conversation depuis l'UI

Action attendue :

- appel de `soft_delete_conversation()`
- mise a jour de `deleted_at`
- aucun hard delete

Effet attendu :

- disparition de l'UI standard ;
- conversation toujours presente en base.

### Purge manuelle d'une conversation

Action attendue :

- action admin distincte ;
- jamais confondue avec le bouton standard de suppression UI ;
- implementation technique appuyee sur `delete_conversation()`.

Effet attendu :

- suppression physique de la conversation ;
- suppression physique des `conversation_messages` associes ;
- purge des `traces`, `summaries` et `arbiter_decisions` directement rattaches a cette conversation ;
- pour la couche identitaire, ne pas forcer une lecture "tout ou rien" : si des divergences apparaissent dans le temps, elles doivent etre preservees ou synthetisees comme tensions temporelles plutot qu'ecrasees en fausse coherence.

### Purge globale

Deux niveaux doivent etre distingues.

#### 1. Purge globale prudente

Action attendue :

- operation manuelle et explicite ;
- reservee a un besoin exceptionnel de nettoyage produit, technique ou legal.

Elle ne doit pas etre automatique par defaut.

#### 2. Purge globale totale

Action attendue :

- operation exceptionnelle, explicite, admin uniquement ;
- reservee a un reset volontaire de l'instance.

Cette action ne doit jamais etre declenchee automatiquement.

## Politique de purge automatique

Regle cible :

- aucune purge automatique des conversations par defaut.

Execution conseillee si un jour elle devient configurable :

- toujours desactivee par defaut ;
- clairement annoncee dans l'admin ;
- journalisee ;
- et separee d'une vraie purge manuelle volontaire.

## Politique d'export

Avant toute purge forte, l'export doit etre pense comme suit :

- export par conversation, depuis la base uniquement ;
- export incluant la conversation et ses messages, avec leurs timestamps ;
- export declenchable avant purge manuelle ou purge globale prudente.

Point de vigilance :

- il n'existe pas encore de route produit dediee a l'export des conversations ;
- cette politique pose la regle fonctionnelle, pas encore toute l'implementation UI/admin.

## Contraintes techniques a respecter

### Source de verite

- `conversations` et `conversation_messages` restent `DB-only`.

### Horodatage

Les decisions de retention et purge doivent s'appuyer sur :

- `created_at`
- `updated_at`
- `deleted_at`

Et non sur des heuristiques fichiers ou des JSON legacy.

### Couplage parent/enfant

- `conversation_messages` n'ont pas de cycle de vie autonome ;
- ils suivent la conversation parente ;
- masquer une conversation ne supprime pas ses messages ;
- purger une conversation purge aussi ses messages.

## Etat actuel du code

Le code actuel est deja aligne avec une partie importante de cette politique :

- l'UI delete passe par `soft_delete_conversation()` ;
- `deleted_at` sert deja a masquer une conversation ;
- `delete_conversation()` fait deja une purge forte en base.

Ce qui reste a exposer plus tard :

- une action admin explicite de purge forte par conversation ;
- un export de conversation avant purge.

Point de vigilance important :

- l'implementation actuelle de `delete_conversation()` est plus destructive que la politique cible sur la couche identitaire ;
- aujourd'hui, elle supprime aussi `identity_evidence`, `identities` et `identity_conflicts` lies a la conversation ;
- avant d'exposer une vraie purge forte dans l'admin, ce point devra etre aligne avec la gouvernance cible de la memoire.

## Decision retenue

La politique retenue pour `FridaDev` est donc :

- conservation sans limite des conversations actives ;
- suppression UI = masquage uniquement ;
- conservation sans limite en base des conversations masquees, sauf purge exceptionnelle volontaire ;
- purge forte reservee a une action admin distincte ;
- aucune purge automatique des conversations par defaut ;
- export a penser depuis la base avant toute purge destructive.
