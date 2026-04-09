# Identity vs Prompt Separation TODO

Statut: actif
Classement: `app/docs/todo-todo/memory/`
Surface conceptuelle: identite canonique, prompt systeme, prompt hermeneutique, rewriter de mutable, representations runtime injectees
Origine: clarification doctrinale apres fixation de la surface `/identity` et constat d'un melange conceptuel entre personnalite, instructions et formes compilees d'injection.

## Objectif

- [x] Fixer une doctrine lisible qui separe `identity` et `prompt`.
- [x] Fixer un contrat distinct pour le prompt du rewriter de mutable.
- [x] Fixer le statut des representations runtime injectees.
- [ ] Transformer cette doctrine en chantier d'implementation suivi, sans la melanger au TODO UI `/identity`.

## Priorite absolue

- [x] Definir et figer `llm.static` comme noyau identitaire stable du modele.
- [x] Unifier repo et runtime sur une source canonique unique de `llm.static`.
- [x] Distinguer explicitement ce qui releve de la personnalite identitaire (`llm.static`) et ce qui releve du pilotage technique (`prompt systeme` / `prompt hermeneutique`).
- [x] Nettoyer le prompt du LLM pour n'y garder que la technique, l'operatoire, la methode, la securite, les priorites, les outils, le format et les contraintes runtime.
- [x] Verifier que `llm.static` est reellement charge, projete et injecte au runtime.
- [x] Ne traiter le durcissement de `llm.mutable` et du `identity_mutable_rewriter` qu'apres cette base posee et verifiee.

## Decisions acquises

- [x] `identity` et `prompt` ne sont pas la meme chose.
- [x] `identity` designe la personnalite du LLM ou de l'utilisateur, pas une consigne de travail.
- [x] `llm` vide n'est pas un etat nominal du produit.
- [x] `llm.mutable` ne doit pas devenir un pseudo-system-prompt.
- [x] Une representation runtime injectee n'est pas une source canonique; c'est une forme compilee d'application.
- [x] Le present document reste distinct du TODO UI `app/docs/todo-todo/admin/identity-surface-canonical-layout-todo.md`.
- [x] Sans `llm.static` fixe, la doctrine `identity != prompt` reste incomplete et flotte entre le prompt, la mutable et les representations runtime.

## Constats de depart a garder en tete

- [x] `app/identity/active_identity_projection.py` agrege aujourd'hui `static` et `mutable` dans une meme projection textuelle.
- [x] `app/core/chat_prompt_context.py` concatene aujourd'hui prompt systeme, prompt hermeneutique, repere temporel et bloc identite dans le prompt systeme augmente.
- [x] `app/core/hermeneutic_node/inputs/identity_input.py` expose deja une forme structuree canonique distincte (`identity_input` schema `v2`).
- [x] `app/memory/memory_identity_mutable_rewriter.py` construit aujourd'hui un payload de reecriture qui voit `recent_turns`, `static`, `mutable_current` et `mutable_budget`.
- [x] `app/prompts/identity_mutable_rewriter.txt` demande deja une reecriture narrative de la mutable, mais ne ferme pas encore assez explicitement la frontiere entre personnalite et instruction.
- [x] `app/prompts/main_system.txt` porte deja des consignes de conduite, de forme et de methode qui relevent du prompt, pas de l'identite.
- [x] `app/prompts/main_hermeneutical.txt` traite deja le bloc identite comme une brique de coherence relationnelle, non souveraine sur la question courante.
- [x] Tant que `llm.static` n'est pas clairement fixe et verifie dans le runtime, le systeme compense facilement en mettant de la personnalite un peu partout.
- [x] La source canonique unique de `llm.static` sur OVH est `state/data/identity/llm_identity.txt` dans le repo `fridadev`, montee dans le conteneur en `/app/data/identity/llm_identity.txt`.

## Diagnostic conceptuel a ne pas perdre

- [x] La source canonique `identity` existe bien comme couche semantique propre.
- [x] Cette couche est ensuite compilee dans le prompt systeme augmente.
- [x] Le rewriter mutable voit a la fois le statique, la mutable courante et les derniers tours.
- [x] L'UI `/identity` montre aujourd'hui ensemble source canonique, projection runtime et diagnostics.
- [x] Le probleme a corriger n'est pas seulement un probleme de rangement UI.
- [x] Le probleme a corriger est un probleme de doctrine des couches.
- [x] La premiere fuite a colmater n'est pas seulement dans la mutable; c'est d'abord l'absence d'un noyau identitaire stable suffisamment explicite et verifie.

## Invariants doctrinaux

### Distinction cible

- [x] `identity` = qui parle et comment cette voix se tient dans la duree.
- [x] `prompt` = instructions qui pilotent l'action du systeme.
- [x] Le prompt peut cadrer la parole, mais il n'est pas l'identite.
- [x] Les representations runtime injectees sont des vues compilees, pas une source canonique.
- [x] Dans le prompt du LLM, on ne doit garder que la technique et l'operatoire.
- [x] Tout ce qui releve de la personnalite, de la voix, de la posture relationnelle et du comportement identitaire doit vivre dans `llm.static`.

### Contrat par couche

- [x] `llm.static` = noyau identitaire stable du modele.
- [x] `llm.mutable` = etat identitaire mouvant autorise du modele.
- [x] `user.static` = base stable connue du cote utilisateur.
- [x] `user.mutable` = etat mouvant autorise du cote utilisateur.
- [x] `system prompt` et prompt hermeneutique portent les consignes de travail, la methode d'interpretation, les priorites et les gardes runtime.
- [x] Le prompt du `identity_mutable_rewriter` ne definit pas l'identite profonde; il definit seulement comment maintenir ou reecrire `llm.mutable` et `user.mutable`.

### Contrat cible de `llm.static`

- [x] `llm.static` porte la base de personnalite durable.
- [x] `llm.static` porte la couleur relationnelle de reference.
- [x] `llm.static` porte les traits de continuite qui ne doivent pas varier d'un tour a l'autre.
- [x] `llm.static` porte la voix stable du modele.
- [x] `llm.static` porte la posture relationnelle stable du modele.
- [x] `llm.static` porte le comportement identitaire durable du modele.

### Contrat cible de `llm.mutable`

- [x] `llm.mutable` porte une modulation narrative durable ou semi-durable de la personnalite.
- [x] `llm.mutable` porte une actualisation de ton, de positionnement ou de continuite personnelle.
- [x] `llm.mutable` peut modifier la facon d'etre du modele.
- [x] `llm.mutable` ne doit pas modifier la politique de conduite du systeme.

### Contrat cible cote utilisateur

- [x] `user.static` porte les informations durables de presentation, les preferences profondes et les reperes biographiques stabilises.
- [x] `user.mutable` porte des preferences ou inflexions relationnelles qui ont gagne une certaine duree.
- [x] `user.mutable` ne doit pas devenir un resume de situation circonstancielle.

## Checklist des interdits normatifs

### Interdit dans `identity`

- [x] Ne pas verser dans `identity` des instructions de tache.
- [x] Ne pas verser dans `identity` des priorites de raisonnement.
- [x] Ne pas verser dans `identity` des interdictions de style purement operatoires.
- [x] Ne pas verser dans `identity` des regles markdown ou de formatting.
- [x] Ne pas verser dans `identity` des politiques d'usage d'outils.
- [x] Ne pas verser dans `identity` des contraintes de lecture web.
- [x] Ne pas verser dans `identity` des mentions de budget tokens ou caracteres.
- [x] Ne pas verser dans `identity` des descriptions du pipeline.
- [x] Ne pas verser dans `identity` des consignes sur quand clarifier, suspendre, verifier ou citer.
- [x] Ne pas verser dans `identity` des formulations du type `tu dois`, `il faut repondre`, `ne jamais` quand elles relevent d'une politique operatoire.

### Interdit dans `llm.mutable`

- [x] Ne pas laisser entrer dans `llm.mutable` une humeur ponctuelle.
- [x] Ne pas laisser entrer dans `llm.mutable` la situation de la journee.
- [x] Ne pas laisser entrer dans `llm.mutable` la tache en cours.
- [x] Ne pas laisser entrer dans `llm.mutable` une contrainte runtime locale.
- [x] Ne pas laisser entrer dans `llm.mutable` une auto-description technique qui releve d'une limite de prompt ou d'outil.
- [x] Ne pas laisser entrer dans `llm.mutable` un rappel des heuristiques du rewriter.

### Autorise et encourage dans `llm.mutable`

- [x] Autoriser une inflexion durable de ton.
- [x] Autoriser une maniere durable de se positionner face a l'utilisateur.
- [x] Autoriser une continuite narrative de la voix.
- [x] Autoriser des nuances relationnelles ou stylistiques qui restent identitaires.
- [x] Autoriser une auto-comprehension durable du role conversationnel tant qu'elle ne devient pas une consigne de methode.

### Interdit dans le prompt du rewriter

- [x] Le prompt du rewriter ne doit pas encourager la fusion entre personnalite et instructions.
- [x] Le prompt du rewriter ne doit pas encourager la recopie de contraintes runtime dans la mutable.
- [x] Le prompt du rewriter ne doit pas encourager l'injection de regles systeme dans un texte identitaire.
- [x] Le prompt du rewriter ne doit pas encourager la reecriture de `llm.mutable` comme pseudo-politique de comportement.

## Contrat de lecture operateur

- [x] L'operateur doit pouvoir comprendre simplement que `identity` = qui est la voix.
- [x] L'operateur doit pouvoir comprendre simplement que `prompt` = comment le systeme doit travailler.
- [x] L'operateur doit pouvoir comprendre simplement que `runtime injection` = forme compilee actuellement utilisee.
- [x] `/identity` doit exposer la personnalite canonique, pas un patchwork d'instructions.
- [x] Les vues runtime doivent etre lues comme compilees, pas comme source de verite.
- [x] La mutable `llm` doit etre presentee comme une personnalite mouvante, pas comme une zone de consignes.

## Checklist de travail par lot

### Lot 1 - Doctrine et vocabulaire

- [x] Definir et figer le contenu cible de `llm.static` comme noyau identitaire stable du modele.
- [x] Unifier la source canonique effective de `llm.static` entre repo et runtime.
- [x] Aligner le montage runtime pour que `/app/data/identity/llm_identity.txt` consomme `state/data/identity/llm_identity.txt` du repo.
- [x] Fermer explicitement ce qui doit vivre dans `llm.static`: personnalite stable, voix, posture relationnelle, comportement identitaire durable.
- [x] Reperer la fuite principale active: la personnalite stable logee dans `main_system.txt` alors que `llm.static` etait vide.

### Lot 2 - Frontiere prompt technique vs identite

- [x] Relire `main_system` et `main_hermeneutical`.
- [x] Nettoyer doctrinalement la frontiere entre comportement identitaire et comportement operatoire.
- [x] Poser noir sur blanc que le prompt systeme / prompt hermeneutique ne gardent que la technique, la methode, la securite, les priorites, les outils, le format et les contraintes runtime.
- [ ] Relever les docs/specs qui parlent encore de facon melangee de personnalite et de prompt.

### Lot 3 - Verification runtime de `llm.static`

- [x] Verifier que `llm.static` est reellement charge dans le runtime.
- [x] Verifier que `llm.static` est bien projete dans `ActiveIdentityProjection`.
- [x] Verifier que `llm.static` est bien present dans `identity_input`.
- [x] Verrouiller par tests le contrat `load_llm_identity() -> build_identity_block() -> build_identity_input()` pour la vraie source active.
- [x] Verifier via le read-model admin que `llm.static` est `loaded_for_runtime` et `actively_injected`.
- [x] Verifier que `llm.static` est bien injecte dans le `augmented_system`.
- [x] Verifier que la chaine `load -> projection -> injection` est explicitement prouvee sur OVH.

### Lot 4 - Mutable et rewriter apres base posee

- [ ] Relire `identity_mutable_rewriter` seulement apres fixation de `llm.static`.
- [ ] Identifier ce qui pousse encore `llm.mutable` a absorber de la personnalite faute de noyau stable suffisamment explicite.
- [ ] Durcir le prompt du rewriter.
- [ ] Durcir la validation des sorties `llm.mutable` / `user.mutable`.
- [ ] Interdire explicitement les contenus prompt-like dans la mutable.

### Lot 5 - Clarification admin et lecture runtime

- [ ] Clarifier dans l'admin et les specs que les representations injectees sont compilees.
- [ ] Montrer plus nettement la difference entre source canonique et projection runtime.
- [ ] Exposer distinctement la personnalite canonique et les couches prompt/runtime.
- [ ] Rendre visible ce qui releve de l'identite et ce qui releve du pilotage systeme.
- [ ] Garder ce lot distinct du TODO de layout `/identity`.

## Definition of done

- [ ] La doctrine `identity != prompt` est visible dans les docs et dans l'admin.
- [ ] `llm.mutable` ne peut plus servir de pseudo-prompt de tache.
- [ ] Le prompt du rewriter ne contamine plus la personnalite qu'il maintient.
- [ ] Les representations runtime injectees sont clairement presentees comme des formes compilees.
- [ ] L'operateur peut distinguer en quelques secondes identite, prompt et injection runtime.

## Hors scope

- [x] Pas de patch code backend ou frontend dans ce document.
- [x] Pas de redesign complet de l'admin dans ce document.
- [x] Pas de traitement du finding `arbiter model drift` dans ce document.
- [x] Pas de changement immediat du contrat runtime en production dans ce document.
