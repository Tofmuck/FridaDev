# Politique de retention et de purge - Traces et resumes Frida

Objet: definir la politique cible pour `traces` et `summaries`, en tenant compte du comportement actuel du moteur de memoire et de leur lien avec les conversations.

## Perimetre

Cette politique couvre :

- `traces`
- `summaries`

Elle ne couvre pas encore :

- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

## Nature de ces donnees

`traces` et `summaries` ne sont pas la source primaire du dialogue.

La source primaire reste :

- `conversations`
- `conversation_messages`

`traces` et `summaries` sont des donnees derivees de la conversation :

- `traces` = souvenirs semantiques elementaires, au niveau message ;
- `summaries` = condensations temporelles de portions de conversation.

En consequence :

- leur cycle de vie doit suivre celui de la conversation parente ;
- ils ne doivent pas survivre indefiniment si la conversation source est explicitement purgee.

## Granularite retenue

### Traces

Granularite :

- une trace par message `user` ou `assistant` juge persistant ;
- rattachement a `conversation_id` ;
- horodatage au niveau du message ;
- lien optionnel `summary_id` vers un resume couvrant cette periode.

### Resumes

Granularite :

- un resume pour un intervalle temporel d'une conversation ;
- rattachement a `conversation_id` ;
- bornes temporelles `start_ts` / `end_ts`.

## Regles de retention

### 1. Conversation active

Tant que la conversation parente est active :

- conserver ses `traces` ;
- conserver ses `summaries`.

Justification :

- la recuperation memoire actuelle est principalement `trace-first` ;
- purger des traces actives par anciennete casserait la capacite de rappel semantique ;
- les resumes enrichissent et contextualisent les traces, mais ne remplacent pas encore seuls la recuperation.

Conclusion :

- aucune purge automatique basee uniquement sur l'age ne doit viser les `traces` et `summaries` d'une conversation active dans l'etat actuel du produit.

### 2. Conversation masquee

Si la conversation parente est masquee via `deleted_at` :

- conserver ses `traces` ;
- conserver ses `summaries` ;
- les laisser disponibles comme memoire du systeme tant qu'aucune purge forte n'est demandee.

Justification :

- dans `Frida`, masquer une conversation ne signifie pas supprimer la source brute ;
- le corpus reste en base ;
- la memoire derivee peut donc continuer a vivre et a servir le systeme.

### 3. Conversation purgee

Si la conversation parente est purgee definitivement :

- purger immediatement ses `traces` ;
- purger immediatement ses `summaries`.

Le code actuel est deja aligne avec cette regle dans `delete_conversation()`.

## Regles de purge

### Purge selective par conversation

Autorisee.

Effet attendu :

- suppression des `traces` et `summaries` d'une conversation cible ;
- operation coherente avec la purge forte de la conversation parente.

### Purge selective par etat du parent

Autorisee.

Cas cible principal :

- purger les `traces` et `summaries` d'une conversation explicitement purgee par une action admin distincte.

### Purge selective par anciennete seule

Non recommandee dans l'etat actuel.

Justification :

- la recuperation semantique depend encore directement de `traces` ;
- une purge "tout ce qui a plus de X jours" sur des conversations actives reduirait la memoire utile de maniere difficile a expliquer.

Cette regle pourra etre reconsideree plus tard si :

- la recuperation devient hybride `traces + summaries` ;
- ou si un mode de retention configurable par instance est introduit.

### Purge globale

Deux niveaux doivent etre distingues.

#### 1. Purge globale prudente

- operation manuelle et explicite ;
- reservee a un besoin exceptionnel de nettoyage produit, technique ou legal.

#### 2. Purge globale totale

- reset complet de l'instance ;
- operation exceptionnelle, manuelle, admin uniquement.

## Politique de recuperation

Regle retenue :

- tant qu'une conversation reste en base, ses `traces` et `summaries` peuvent continuer a participer a la memoire du systeme ;
- le masquage UI ne retire pas cette conversation du corpus memoire ;
- seule une purge forte explicite retire ces objets du moteur.

## Reindexation et maintenance

Apres purge selective ou purge globale prudente :

- executer un `VACUUM ANALYZE` sur `traces` et `summaries`.

Apres purge massive ou si la qualite/performance de recherche se degrade :

- reindexer ou reconstruire les index vectoriels associes a `traces` et `summaries`.

Regle pratique :

- maintenance legere apres petite purge ;
- reindexation/rebuild apres purge importante ou suspicion de fragmentation.

## Decision retenue

La politique retenue pour `FridaDev` est donc :

- conservation des `traces` et `summaries` tant que la conversation parente reste en base ;
- aucune purge automatique par anciennete seule par defaut ;
- le masquage UI d'une conversation ne retire pas ses `traces` et `summaries` du systeme memoire ;
- si une conversation est purgee explicitement, ses `traces` et `summaries` sont purges aussi ;
- toute purge globale reste exceptionnelle et manuelle ;
- apres purge, une maintenance de base et des index doit etre prevue.
