# Identity Control Surface TODO

Statut: actif
Classement: `app/docs/todo-todo/product/`
Origine: audit identity read-only revalide le `2026-04-05`

## Objectif

Ouvrir un chantier unique pour rendre le systeme identity lisible, controlable et gouvernable par l'operateur, sans lancer encore l'implementation runtime.

Ce TODO doit piloter deux besoins a la fois:
- retablir d'abord la verite runtime de l'identity statique;
- puis sequencer la requalification doctrinale des identities mutables;
- puis ouvrir une vraie surface `Identity` capable de montrer ce qui est charge, stocke, injecte, modifiable et limite.

## Pilotage

- [x] Lot 1 - Retablir la verite runtime de l'identity statique
- [ ] Lot 1B - Requalifier la doctrine identity mutable avant la surface `Identity`
- [ ] Lot 2 - Construire un mode de lecture identity unifie et honnete
- [ ] Lot 3 - Ouvrir une edition controlee du dynamique
- [ ] Lot 4 - Ouvrir une edition controlee du statique
- [ ] Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables
- [ ] Lot 6 - Assembler la surface `Identity` et sa navigation globale

## Structure reelle revalidee

- Le modele actuel n'est pas "deux identity par personne".
- Par sujet `llm` et `user`, le systeme combine aujourd'hui:
  - une source statique texte;
  - des identities dynamiques durables;
  - des evidences;
  - des conflits;
  - des statuts `accepted|deferred|rejected`;
  - des overrides.
- Le prompt runtime ne consomme pas tout ce qui est stocke:
  - il lit un statique;
  - il selectionne ensuite un sous-ensemble dynamique accepte, filtre et budgete;
  - il repasse ensuite les `identity_ids` effectivement injectes dans le flux de reactivation.
- Les surfaces admin actuelles ne donnent qu'une lecture partielle:
  - `GET /api/admin/hermeneutics/identity-candidates`
  - `POST /api/admin/hermeneutics/identity/force-accept`
  - `POST /api/admin/hermeneutics/identity/force-reject`
  - `POST /api/admin/hermeneutics/identity/relabel`
- Il n'existe pas encore de vraie surface `Identity`, ni de bouton `Identity` global.

## Etat revalide qui fixe l'ordre des lots

### Ce qui existe deja

- extraction identity via `app/memory/arbiter.py` et `app/prompts/identity_extractor.txt`;
- stockage durable via `identities`, `identity_evidence`, `identity_conflicts`;
- lecture/injection du bloc identity via `app/identity/identity.py`;
- payload canonique identity pour le noeud hermeneutique via `build_identity_input()`;
- mini-surface admin read-only cote `hermeneutic-admin`;
- quelques mutateurs de correction cote backend admin.

### Ce qui manque encore

- une verite runtime honnete du statique;
- une vue unifiee statique + dynamique + evidences + conflits + caps;
- la lisibilite de ce qui est injecte vs seulement stocke;
- l'edition directe du contenu dynamique;
- l'edition directe du contenu statique;
- la gouvernance operateur des caps et seuils;
- une navigation `Identity` coherente depuis les surfaces utiles.

### Point critique prioritaire

- Dans le runtime audite, `app/identity/identity.py` resout actuellement `llm_identity_path` et `user_identity_path` vers `data/identity/...`.
- Dans le meme audit, les fichiers statiques reels vus localement se trouvent sous `state/data/identity/...`.
- Resultat revalide:
  - le dynamique continue d'alimenter `build_identity_block()`;
  - le statique n'atteint pas effectivement le prompt/payload runtime dans l'etat courant audite.
- Tant que ce point reste ouvert, une future surface `Identity` resterait trompeuse pour l'operateur.

## Ordre retenu

- Le Lot 1 est prioritaire et bloque la suite.
- Le Lot 1B est maintenant prioritaire avant le Lot 2.
- Les Lots 2 a 6 ne doivent pas masquer ou contourner le Lot 1B.
- La future page `Identity` doit arriver apres retablissement de la verite runtime et apres requalification doctrinale des mutables, pas avant.

## Lot 1 - Retablir la verite runtime de l'identity statique

Priorite: bloqueur avant la grande surface `Identity`

But:
- faire en sorte que l'identity statique `llm` et `user` atteigne reellement:
  - le bloc prompt injecte;
  - le payload canonique `identity_input`;
  - les preuves de lecture operateur associees.

- [x] Trancher la source de verite effective des chemins `llm_identity_path` / `user_identity_path`
- [x] Fermer l'ecart entre chemins runtime, resolution relative et emplacement reel des fichiers
- [x] Verifier la semantique attendue pour chemins relatifs vs absolus
- [x] Confirmer que le contenu statique charge est bien celui expose a l'operateur
- [x] Ajouter la preuve de non-regression minimale sur `load_llm_identity()` / `load_user_identity()`, `build_identity_block()` et `build_identity_input()`

Sortie attendue:
- le statique est present dans la verite runtime du prompt et du payload, sans ambiguite de chemin;
- la source de verite documentaire du statique est explicite et stable;
- le chantier peut ensuite ouvrir une surface `Identity` sans raconter une contre-verite.

Cloture du lot:
- le contrat visible reste `data/identity/...`;
- hors conteneur, la resolution host-side retrouve le mirror `state/data/identity/...` sans changer le path expose a l'operateur;
- le payload canonique garde le statique complet et sa source;
- le bloc prompt reintegre bien le statique, mais reste soumis au budget `IDENTITY_MAX_TOKENS` deja en place.

Hors scope du lot:
- nouvelle page `Identity`;
- edition du contenu static depuis l'admin;
- refonte des endpoints identity.

## Lot 1B - Requalifier la doctrine identity mutable avant la surface `Identity`

Priorite: bloqueur avant le Lot 2

But:
- faire apparaitre clairement les 4 identities de travail:
  - `llm` statique;
  - `llm` mutable;
  - `user` statique;
  - `user` mutable;
- preparer une verite canonique ou chaque mutable devient un texte narratif unique par sujet, stocke puis injecte;
- documenter que la discipline de taille ne concerne que les mutables:
  - cible `1500` caracteres;
  - plafond dur `1650` caracteres;
  - aucune troncature runtime;
  - aucun plafond doctrinal equivalent sur les statiques.

Etat revalide avant implementation:
- l'extracteur reste encore fragmentaire avec une sortie `entries[]`;
- le payload canonique reste encore `dynamic[]`;
- l'injection active reste encore pilotee par ranking, `IDENTITY_TOP_N`, `IDENTITY_MAX_TOKENS` et troncature;
- la persistance durable et l'admin legacy restent encore centres sur `accepted|deferred|rejected`, `force_accept`, `force_reject` et `relabel`;
- l'observabilite identity transporte encore des previews textuelles.

- [ ] `1B-A` Introduire une source de verite canonique durable, une mutable narrative par sujet, distincte des evidences et du legacy fragmentaire
- [ ] `1B-B` Requalifier l'extracteur et son contrat pour relire contexte recent + mutable courante et produire `no_change` ou une reecriture narrative validee dans le budget mutable `1500/1650`
- [ ] `1B-C` Basculer l'injection active et `identity_input` vers `static + mutable narrative`, sans ranking, sans `IDENTITY_TOP_N`, sans `IDENTITY_MAX_TOKENS` et sans troncature runtime sur la partie mutable
- [ ] `1B-D` Reclasser ou neutraliser honnetement le legacy (`accepted|deferred|rejected`, `force_accept`, `force_reject`, `relabel`, controles admin) pour qu'il ne raconte plus la verite d'injection active
- [ ] `1B-E` Refaire l'observabilite identity en mode compact, sans previews de contenu brut, avec seulement longueurs, presence/absence, flags d'update et validation budget/shape

Sortie attendue:
- une doctrine mutable narrative sequencee sans pretendre qu'elle est deja fermee;
- une suite de sous-lots qui permet de basculer sans laisser deux verites concurrentes;
- une base honnete avant l'ouverture de la future surface `Identity`.

## Lot 2 - Construire un mode de lecture identity unifie et honnete

But:
- donner a l'operateur une lecture unique de la structure reelle du systeme identity.

- [ ] Separer clairement statique, dynamique durable, evidences, conflits, accepte / differe / rejete et stocke vs effectivement injecte
- [ ] Definir un contrat read-only compact et stable pour la future surface `Identity`
- [ ] Montrer les sources, dates, ids et etats sans reconstitutions manuelles dispersees

Sortie attendue:
- une vue read-only qui explique le modele reel sans retomber dans la formule "deux identity par personne";
- une base lisible pour les lots d'edition.

## Lot 3 - Ouvrir une edition controlee du dynamique

But:
- permettre a l'operateur de corriger les identities dynamiques sans toucher encore au statique.

- [ ] Etendre le perimetre au-dela de `force_accept`, `force_reject` et `relabel`
- [ ] Trancher ce qui est vraiment editable en direct: contenu, statut, override, champs de qualification, gestion de conflits et reactivation ou operations voisines si elles doivent etre exposees
- [ ] Expliciter les bornes de securite et d'audit des actions operateur

Sortie attendue:
- une edition dynamique utile, comprehensible et journalisee;
- aucune confusion entre correction operateur et simple lecture.

## Lot 4 - Ouvrir une edition controlee du statique

But:
- permettre l'edition du contenu static lui-meme, pas seulement de ses chemins.

- [ ] Trancher la source de verite durable du contenu statique apres Lot 1
- [ ] Definir comment l'operateur lit, modifie, valide et sauvegarde `llm` / `user` statiques
- [ ] Expliciter la place des fichiers statiques dans le produit: ressource repo, ressource state ou ressource runtime referencee
- [ ] Garder une separation claire entre edition static et dynamique

Sortie attendue:
- une edition statique explicite et non ambigue;
- aucune illusion de controle limitee a un changement de path.

## Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables

But:
- rendre visibles les limites reelles du systeme identity et trancher ce qui doit devenir gouvernable.

- [ ] Inventorier proprement et exposer `IDENTITY_TOP_N`, `IDENTITY_MAX_TOKENS`, `IDENTITY_MIN_CONFIDENCE`, `IDENTITY_DEFER_MIN_CONFIDENCE`, les seuils de recurrence et de promotion, le budget d'extraction identity distinct et les autres caps reels du pipeline
- [ ] Distinguer ce qui est visible, editable, code en dur, en config/env et en runtime settings/admin
- [ ] Dire explicitement s'il n'existe toujours pas de cap caracteres identity distinct

Sortie attendue:
- une gouvernance operateur honnete des limites;
- une distinction claire entre stockage, extraction et injection.

## Lot 6 - Assembler la surface `Identity` et sa navigation globale

But:
- finir le chantier par une surface `Identity` vraiment utile, accessible depuis les surfaces clefs.

- [ ] Ajouter une page dediee `Identity`
- [ ] Lier cette page depuis toutes les pages admin utiles et depuis la surface principale LLM
- [ ] Garder un ordre de lecture qui aide l'operateur a tout comprendre: structure reelle, etat courant, injection effective, edition, caps et seuils, observabilite

Sortie attendue:
- un point d'entree unique `Identity`;
- une navigation coherente a l'echelle du produit.

## Observabilite attendue a travers les lots

- [ ] Conserver et clarifier les coutures deja presentes sur `identities_read`, `identity_write` et `hermeneutic_node_insertion`
- [ ] Faire apparaitre pour l'operateur la presence du statique, les identities effectivement injectees, l'ecart entre stockage et injection, les actions operateur identity et l'etat des conflits ouverts

## Preuves attendues futures

- [ ] Tests cibles sur le chargement static et l'injection runtime
- [ ] Preuves backend sur les contrats read-only et editables exposes
- [ ] Preuves frontend/admin sur la lisibilite de la future surface `Identity`
- [ ] Verification live minimale de ce que voit vraiment l'operateur
- [ ] Verification documentaire de la source de verite retenue

## Hors scope global

- implementation immediate de la page `Identity`;
- refonte large du systeme identity en une seule passe;
- mutation opportuniste d'autres surfaces admin sans lien direct;
- changements runtime hors besoin direct du chantier identity;
- relecture speculative de toute l'architecture hermeneutique hors perimetre identity.
