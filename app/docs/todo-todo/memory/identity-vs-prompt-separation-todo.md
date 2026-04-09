# Identity vs Prompt Separation TODO

Statut: actif
Classement: `app/docs/todo-todo/memory/`
Surface conceptuelle: identite canonique, prompt systeme, prompt hermeneutique, rewriter de mutable, representations runtime injectees
Origine: clarification doctrinale apres fixation de la surface `/identity` et constat d'un melange conceptuel entre personnalite, instructions et formes compilees d'injection.

## Objectif

Fixer un contrat simple et normatif qui separe explicitement:

- ce qui releve de `identity`
- ce qui releve de `prompt`
- ce qui releve du prompt du rewriter de mutable
- ce qui releve des representations runtime injectees

Ce document ne code rien.
Il sert de base au prochain chantier de separation comportementale et UI.

## Decisions produit deja acquises

- `identity` et `prompt` ne sont pas la meme chose.
- `identity` designe la personnalite du LLM ou de l'utilisateur, pas une consigne de travail.
- `llm` vide n'est pas un etat nominal du produit.
- `llm.mutable` ne doit pas devenir un pseudo-system-prompt.
- une representation runtime injectee n'est pas une source canonique; c'est une forme compilee d'application.

## Repo grounding

Points actifs a prendre comme base reelle:

- `app/identity/active_identity_projection.py`
  - compose aujourd'hui un bloc `[IDENTITE DU MODELE]` / `[IDENTITE DE L'UTILISATEUR]`
  - agrege `static` et `mutable` dans une meme projection textuelle
- `app/core/chat_prompt_context.py`
  - concatene `system_prompt`, prompt hermeneutique, repere temporel et bloc identite dans le prompt systeme augmente
- `app/core/hermeneutic_node/inputs/identity_input.py`
  - expose deja une forme structuree canonique distincte: `identity_input` schema `v2`
- `app/memory/memory_identity_mutable_rewriter.py`
  - construit un payload de reecriture avec `recent_turns`, `static`, `mutable_current` et `mutable_budget`
- `app/prompts/identity_mutable_rewriter.txt`
  - demande aujourd'hui une reecriture narrative de la mutable, mais ne ferme pas encore assez explicitement la frontiere entre personnalite et instruction
- `app/prompts/main_system.txt`
  - porte deja des consignes de conduite, de forme et de methode qui relevent du prompt, pas de l'identite
- `app/prompts/main_hermeneutical.txt`
  - traite deja le bloc identite comme une brique de coherence relationnelle, non souveraine sur la question courante

## Diagnostic

Le melange actuel ne vient pas d'un seul endroit. Il vient de la superposition de quatre faits reels:

- la source canonique `identity` existe bien comme couche semantique propre
- cette couche est ensuite compilee dans le prompt systeme augmente
- le rewriter mutable voit a la fois le statique, la mutable courante et les derniers tours
- l'UI `/identity` montre ensemble source canonique, projection runtime et diagnostics

Consequence:

- l'operateur peut croire qu'une identite est juste "du prompt en plus"
- le rewriter mutable peut etre tente d'absorber des instructions de tache, des contraintes runtime ou des heuristiques de pipeline
- la mutable `llm` risque de devenir une zone grise entre personnalite mouvante et consignes operatoires

Le probleme a corriger n'est donc pas seulement un probleme de rangement UI.
C'est un probleme de doctrine des couches.

## Distinction cible: prompt vs identity

### `identity`

`identity` designe qui parle et comment cette voix se tient dans la duree.

Cela couvre notamment:

- la posture relationnelle
- la coloration de voix
- le style de presence
- la continuite narrative ou biographique minimale
- les preferences durables qui relevent du sujet lui-meme

`identity` n'est pas:

- une checklist de comportements techniques
- un paquet de consignes de tache
- une politique de formatting
- une couche de garde runtime
- une description du pipeline

### `prompt`

`prompt` designe les instructions qui pilotent l'action du systeme.

Cela couvre notamment:

- la methode de travail
- les priorites d'interpretation
- les interdictions et obligations operatoires
- les regles de forme de reponse
- les consignes de prudence, verification, suspension ou cadrage
- les contraintes runtime explicites

Le prompt peut cadrer la parole, mais il n'est pas l'identite.

## Contrat canonique par couche

### `llm.static`

`llm.static` = noyau identitaire stable du modele.

Il porte:

- la base de personnalite durable
- la couleur relationnelle de reference
- les traits de continuites qui ne doivent pas varier d'un tour a l'autre

Il ne doit pas porter:

- des instructions de tache
- des consignes de formatting
- des contraintes de navigation web
- des regles d'usage d'outils
- des heuristiques de reecriture
- des details de pipeline ou de runtime

### `llm.mutable`

`llm.mutable` = etat identitaire mouvant autorise du modele.

Il porte:

- une modulation narrative durable ou semi-durable de la personnalite
- une actualisation de ton, de positionnement ou de continuite personnelle
- une evolution interpretable comme identitaire, pas comme consigne de travail

Il ne doit pas porter:

- des instructions operatoires pour repondre au tour courant
- des contraintes runtime
- des obligations de format
- des consignes de methode
- des rappels meta du pipeline
- des heuristiques de reecriture ou de budget

Regle simple:

- `llm.mutable` peut modifier la facon d'etre du modele
- `llm.mutable` ne doit pas modifier la politique de conduite du systeme

### `user.static`

`user.static` = base stable connue du cote utilisateur.

Il porte:

- les informations durables de presentation
- les preferences profondes ou biographiques deja stabilisees
- les repaires utiles a la coherence relationnelle de long terme

### `user.mutable`

`user.mutable` = etat mouvant autorise du cote utilisateur.

Il porte:

- des preferences ou inflexions relationnelles qui ont gagne une certaine duree
- des evolutions de posture ou de priorite qui relevent encore de l'identite, pas du simple contexte de la journee

Il ne doit pas devenir:

- un resume de situation circonstancielle
- un cache des taches en cours
- un substitut aux indices contextuels recents

### `system prompt` et prompt hermeneutique

Ces prompts portent:

- les consignes de travail
- la methode d'interpretation
- les priorites entre sources
- les obligations de forme
- les gardes et contraintes runtime

Ils ne sont pas la source canonique de l'identite.

### Prompt du `identity_mutable_rewriter`

Le prompt du rewriter ne definit pas l'identite profonde.
Il definit seulement comment maintenir ou reecrire `llm.mutable` et `user.mutable`.

Il doit donc porter:

- les criteres de durabilite
- la discipline de reecriture
- les interdits meta
- le contrat JSON de sortie

Il ne doit pas porter:

- une nouvelle personnalite de reference
- des instructions de reponse pour le modele principal
- des contraintes runtime a recopier dans la mutable
- des formulations qui poussent a verser dans la mutable des directives de prompt

### Representations runtime injectees

Les representations runtime injectees sont des vues compilees.

Elles servent a:

- l'injection dans le prompt final
- le jugement hermeneutique
- la lecture operateur du runtime

Elles ne doivent pas etre traitees comme:

- la source canonique de l'identite
- l'endroit ou l'on edite les regles de pilotage
- le lieu doctrinal ou l'on decide ce qui releve de `identity` ou de `prompt`

## Regles normatives de separation

### Interdit dans `identity`

Ne doivent pas apparaitre dans `llm.static`, `llm.mutable`, `user.static` ou `user.mutable`:

- instructions de tache
- priorites de raisonnement
- interdictions de style purement operatoires
- regles markdown ou formatting
- politiques d'usage d'outils
- contraintes de lecture web
- mentions du budget tokens ou caracteres
- descriptions du pipeline
- consignes sur quand clarifier, suspendre, verifier ou citer
- formulations du type `tu dois`, `il faut repondre`, `ne jamais`, quand elles relevent d'une politique operatoire

### Interdit dans `llm.mutable`

Ne doivent pas y entrer:

- humeur ponctuelle
- situation de la journee
- tache en cours
- contrainte runtime locale
- auto-description technique du type `je n'ai pas acces a ...` quand elle releve d'une limite de prompt ou d'outil
- rappel des heuristiques du rewriter

### Autorise et encourage dans `llm.mutable`

Peuvent y entrer si le signal est assez durable:

- inflexion de ton
- maniere de se positionner face a l'utilisateur
- continuite narrative de la voix
- nuances relationnelles ou stylistiques qui restent identitaires
- auto-comprehension durable du role conversationnel, tant qu'elle ne devient pas une consigne de methode

### Interdit dans le prompt du rewriter

Le prompt du rewriter ne doit pas encourager:

- la fusion entre personnalite et instructions
- la recopie de contraintes runtime dans la mutable
- l'injection de regles systeme dans un texte identitaire
- la reecriture de `llm.mutable` comme pseudo-politique de comportement

## Contrat de lecture operateur

L'operateur doit pouvoir comprendre simplement:

- `identity` = qui est la voix
- `prompt` = comment le systeme doit travailler
- `runtime injection` = forme compilee actuellement utilisee

Consequence UI a preparer pour les lots suivants:

- `/identity` doit exposer la personnalite canonique, pas un patchwork d'instructions
- les vues runtime doivent etre lues comme compilees, pas comme source de verite
- la mutable `llm` doit etre presentee comme `personnalite mouvante` ou equivalent, pas comme zone de consignes

## Lots suivants

### Lot 1 - Doctrine et vocabulaire

- fermer les termes officiels `identity`, `prompt`, `mutable`, `representation runtime`
- aligner les labels operateur sur cette doctrine

### Lot 2 - Audit des prompts et du rewriter mutable

- relire `main_system`, `main_hermeneutical` et `identity_mutable_rewriter`
- identifier ce qui pousse encore a melanger personnalite, prompt et runtime
- relever les contenus deja stockes qui ressemblent a du pseudo-prompt

### Lot 3 - Contrat de reecriture mutable

- durcir le prompt du rewriter
- durcir la validation des sorties `llm.mutable` / `user.mutable`
- interdire explicitement les contenus prompt-like dans la mutable

### Lot 4 - Separation runtime / source canonique

- clarifier dans l'admin et les specs que les representations injectees sont compilees
- montrer plus nettement la difference entre source canonique et projection runtime

### Lot 5 - Surface operateur `/identity`

- exposer distinctement la personnalite canonique et les couches prompt/runtime
- rendre visible ce qui releve de l'identite et ce qui releve du pilotage systeme

## Definition de done du futur chantier

Le chantier sera considere comme boucle quand:

- la doctrine `identity != prompt` est visible dans les docs et dans l'admin
- `llm.mutable` ne peut plus servir de pseudo-prompt de tache
- le prompt du rewriter ne contamine plus la personnalite qu'il maintient
- les representations runtime injectees sont clairement presentees comme des formes compilees
- l'operateur peut distinguer en quelques secondes identite, prompt et injection runtime

## Hors scope

- patch code backend ou frontend dans ce document
- redesign complet de l'admin
- arbitrage `arbiter model drift`
- changement immediat du contrat de runtime en production
