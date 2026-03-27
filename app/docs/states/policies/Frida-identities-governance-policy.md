# Politique d'anonymisation, d'export et de suppression - Identites Frida

Objet: definir la politique cible pour :

- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

Cette politique suit le principe systeme retenu pour `Frida` :

- le front peut masquer ;
- la base conserve par defaut ;
- la suppression physique est une operation distincte, rare et explicite.

## 1. Nature de chaque famille

### Identities

`identities` represente la memoire consolidee du systeme.

Ce n'est pas un simple cache temporaire :

- ce sont les connaissances stables ou semi-stables que `Frida` reutilise ;
- elles peuvent evoluer, etre requalifiees, forcees ou rejetees ;
- elles doivent survivre au masquage UI des conversations sources.

### Identity evidence

`identity_evidence` represente les observations et justifications accumulees par le moteur.

Ce n'est pas seulement du debug :

- c'est la trace d'apprentissage qui permet d'expliquer pourquoi une identite existe ;
- elle peut rester en base meme si la conversation source est masquee dans le front.

### Identity conflicts

`identity_conflicts` represente aujourd'hui, techniquement, l'historique des contradictions detectees entre identites.

Cette table fait partie du fonctionnement hermeneutique :

- elle ne doit pas etre pensee comme un simple bruit jetable ;
- elle documente les tensions de memoire du systeme ;
- elle peut rester utile meme si les conversations sources sont masquees.

Sur le plan produit, elle doit etre lue de plus en plus comme une table de tensions temporelles, pas seulement comme une table d'incoherences brutes.

### Arbiter decisions

`arbiter_decisions` represente la telemetry brute du moteur d'arbitrage.

Cette famille est differente :

- elle sert au pilotage, au diagnostic et a la visualisation ;
- elle n'est pas la memoire durable du produit ;
- elle doit donc avoir une duree de vie courte.

## 2. Regles de retention

## 2.a Regle d'interpretation - Tension temporelle

Comme les conversations, evidences et messages sont horodates, une divergence ne doit pas etre lue trop vite comme une simple incoherence logique.

La regle retenue est la suivante :

- si l'utilisateur a affirme `A`, puis plus tard `B`, on ne doit pas ecraser cette evolution ;
- si `Frida` a soutenu `A`, puis plus tard `B`, on doit aussi pouvoir relire cette evolution ;
- quand deux etats se contredisent ou se deplacent dans le temps, le systeme doit les traiter comme une tension temporelle et non comme un pur "bug de coherence".

Une tension temporelle doit idealement pouvoir exprimer :

- le sujet concerne (`user` ou `llm`) ;
- l'etat anterieur ;
- l'etat plus recent ;
- la fenetre temporelle ou les timestamps connus ;
- un niveau de confiance ou de tension ;
- un resume synthétique de l'evolution.

Le nom de table `identity_conflicts` peut donc rester technique pour l'instant, mais la semantique cible doit tendre vers :

- contradiction detectee ;
- ou tension temporelle synthetisee.

### Identities

Retention par defaut :

- conservation sans limite de duree en base.

Justification :

- `identities` fait partie du coeur memoire de `Frida` ;
- le systeme doit pouvoir garder ce qu'il a appris ;
- le masquage du front ne doit pas effacer cette couche consolidee.

La regulation se fait donc prioritairement par :

- `status` (`accepted`, `deferred`, `rejected`) ;
- `weight` ;
- `override_state` ;
- `relabel`.

### Identity evidence

Retention par defaut :

- conservation sans limite de duree en base.

Justification :

- tant que l'on ne supprime pas la source brute de la base, l'evidence peut rester ;
- elle contribue a l'auditabilite et a l'interpretabilite du systeme ;
- elle est utile pour l'analyse, la recherche et les corrections futures.

### Identity conflicts

Retention par defaut :

- conservation sans limite de duree en base.

Justification :

- l'historique des conflits fait partie de la memoire de gouvernance du systeme ;
- il ne doit pas etre perdu juste parce que le front masque certaines conversations.

### Arbiter decisions

Retention par defaut :

- conservation des decisions brutes pendant 30 jours ;
- purge automatique au-dela.

Justification :

- `arbiter_decisions` releve de la telemetrie moteur ;
- il faut assez de recul pour diagnostiquer et produire des graphes ;
- mais pas assez pour laisser la base grossir indefiniment avec du brut peu durable.

## 3. Regles de suppression

### Masquage UI

Le masquage UI :

- ne supprime pas `identities` ;
- ne supprime pas `identity_evidence` ;
- ne supprime pas `identity_conflicts` ;
- ne supprime pas `arbiter_decisions`.

Il ne change que la presentation des conversations dans l'interface standard.

### Suppression metier recommandee

Pour `identities`, la suppression physique ne doit pas etre l'outil normal.

L'outil normal doit etre :

- `force_accept`
- `force_reject`
- `relabel`
- ajustement du poids ou du statut

Autrement dit :

- on prefere corriger et gouverner une memoire ;
- on ne la detruit pas par defaut.

### Suppression physique exceptionnelle

Une suppression physique peut exister plus tard, mais seulement comme action admin distincte et exceptionnelle.

Cas legitimes :

- nettoyage de test ;
- exigence legale ;
- reset volontaire de l'instance ;
- correction d'une pollution manifeste de la base.

Par defaut :

- aucune purge automatique pour `identities`, `identity_evidence` et `identity_conflicts`.

Si une source conversationnelle est exceptionnellement purgee physiquement :

- on ne doit pas reinterpretrer artificiellement l'histoire comme parfaitement coherente ;
- si une memoire consolidee subsiste, les divergences connues doivent pouvoir rester lisibles comme tensions temporelles ;
- la suppression de la source brute ne doit pas, a elle seule, imposer l'effacement conceptuel de l'evolution memoire.

### Arbiter decisions

Pour `arbiter_decisions`, la suppression automatique est admise et voulue :

- purge des lignes brutes de plus de 30 jours ;
- journalisation de la purge ;
- execution idempotente.

## 4. Politique d'export

Deux niveaux d'export doivent etre distingues.

### Export standard

But :

- fournir une vue lisible de la memoire produit.

Contenu recommande :

- `identities`
- resume synthétique de l'evidence associee
- etat des overrides et relabels pertinents

Contenu a exclure par defaut :

- UUID internes ;
- bruit technique ;
- decisions brutes d'arbitrage ;
- details de debug non utiles a l'usage courant.

### Export technique / admin

But :

- audit, recherche, diagnostic, reproductibilite.

Contenu recommande :

- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions` dans la fenetre de retention
- timestamps complets
- statuts, raisons, overrides, acteurs techniques si necessaire

L'endpoint actuel `corrections-export` ne couvre qu'une partie du besoin.
Il exporte deja les corrections admin journalisees, mais pas encore l'ensemble du modele memoire.

Pour les tensions temporelles, l'export technique devra idealement permettre de restituer :

- l'avant ;
- l'apres ;
- les timestamps ;
- la nature de la tension ;
- et, si disponible, une synthese interpretable.

## 5. Politique d'anonymisation

Le principe retenu est le suivant :

- l'instance locale peut conserver la donnee brute en base ;
- l'export partageable ou publiable doit etre pseudonymise ou nettoye selon son niveau.

### Anonymisation de l'export standard

Par defaut :

- pas d'UUID internes ;
- pas d'acteurs techniques bruts si non necessaires ;
- pas de noms de tables ni de champs internes ;
- presentation par objets metier lisibles.

### Anonymisation de l'export technique publiable

Si l'export sort du perimetre local :

- pseudonymiser les identifiants de conversation ;
- retirer les secrets, tokens, noms d'acteurs infra et details inutiles ;
- garder uniquement les champs necessaires a la recherche ou a l'analyse.

## 6. Decision retenue

La politique retenue pour `FridaDev` est donc :

- `identities` : conservation durable en base, sans purge automatique par defaut ;
- `identity_evidence` : conservation durable en base, sans purge automatique par defaut ;
- `identity_conflicts` : conservation durable en base, sans purge automatique par defaut, avec une lecture produit orientee tensions temporelles ;
- `arbiter_decisions` : retention brute de 30 jours, puis purge automatique ;
- masquage UI : aucun effet destructif sur ces tables ;
- export : distinction claire entre export standard et export technique ;
- anonymisation : surtout au niveau des exports sortants, pas au niveau du stockage local par defaut.

## 7. Ecart actuel de mise en oeuvre

Le code actuel n'est pas encore totalement aligne avec cette cible lors d'une purge forte de conversation :

- `delete_conversation()` supprime aujourd'hui les `identities`, `identity_evidence` et `identity_conflicts` lies a la conversation ;
- la politique cible, elle, demande une lecture plus conservatrice de la memoire consolidee et des tensions temporelles.

Conclusion :

- la politique est maintenant posee ;
- l'alignement complet du code devra etre traite avant d'exposer une purge forte comme fonctionnalite produit normale.
