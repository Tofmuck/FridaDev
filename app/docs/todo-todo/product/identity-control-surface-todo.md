# Identity Control Surface TODO

Statut: actif
Classement: `app/docs/todo-todo/product/`
Origine: audit identity read-only revalide le `2026-04-05`

## Objectif

Ouvrir un chantier unique pour rendre le systeme identity lisible, controlable et gouvernable par l'operateur, sans lancer encore l'implementation runtime.

Ce TODO doit piloter deux besoins a la fois:
- retablir d'abord la verite runtime de l'identity statique;
- puis sequencer une vraie surface `Identity` capable de montrer ce qui est charge, stocke, injecte, modifiable et limite.

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
- Les Lots 2 a 6 ne doivent pas masquer ou contourner le Lot 1.
- La future page `Identity` doit arriver apres retablissement de la verite runtime, pas avant.

## Lot 1 - Retablir la verite runtime de l'identity statique

But:
- faire en sorte que l'identity statique `llm` et `user` atteigne reellement:
  - le bloc prompt injecte;
  - le payload canonique `identity_input`;
  - les preuves de lecture operateur associees.

Travail attendu:
- trancher la source de verite effective des chemins `llm_identity_path` / `user_identity_path`;
- fermer l'ecart entre chemins runtime, resolution relative et emplacement reel des fichiers;
- verifier la semantique attendue pour chemins relatifs vs absolus;
- confirmer que le contenu statique charge est bien celui expose a l'operateur;
- ajouter la preuve de non-regression minimale sur:
  - `load_llm_identity()` / `load_user_identity()`;
  - `build_identity_block()`;
  - `build_identity_input()`.

Sortie attendue:
- le statique est present dans la verite runtime du prompt et du payload, sans ambiguite de chemin;
- la source de verite documentaire du statique est explicite et stable;
- le chantier peut ensuite ouvrir une surface `Identity` sans raconter une contre-verite.

Hors scope du lot:
- nouvelle page `Identity`;
- edition du contenu static depuis l'admin;
- refonte des endpoints identity.

## Lot 2 - Construire un mode de lecture identity unifie et honnete

But:
- donner a l'operateur une lecture unique de la structure reelle du systeme identity.

Travail attendu:
- separer clairement:
  - statique;
  - dynamique durable;
  - evidences;
  - conflits;
  - accepte / differe / rejete;
  - stocke vs effectivement injecte;
- definir un contrat read-only compact et stable pour la future surface `Identity`;
- montrer les sources, dates, ids et etats sans reconstitutions manuelles disperses.

Sortie attendue:
- une vue read-only qui explique le modele reel sans retomber dans la formule "deux identity par personne";
- une base lisible pour les lots d'edition.

## Lot 3 - Ouvrir une edition controlee du dynamique

But:
- permettre a l'operateur de corriger les identities dynamiques sans toucher encore au statique.

Travail attendu:
- etendre le perimetre au-dela de `force_accept`, `force_reject` et `relabel`;
- trancher ce qui est vraiment editable en direct:
  - contenu;
  - statut;
  - override;
  - champs de qualification;
  - gestion de conflits;
  - reactivation ou operations voisines si elles doivent etre exposees;
- expliciter les bornes de securite et d'audit des actions operateur.

Sortie attendue:
- une edition dynamique utile, comprehensible et journalisee;
- aucune confusion entre correction operateur et simple lecture.

## Lot 4 - Ouvrir une edition controlee du statique

But:
- permettre l'edition du contenu static lui-meme, pas seulement de ses chemins.

Travail attendu:
- trancher la source de verite durable du contenu statique apres Lot 1;
- definir comment l'operateur lit, modifie, valide et sauvegarde `llm` / `user` statiques;
- expliciter la place des fichiers statiques dans le produit:
  - ressource repo;
  - ressource state;
  - ressource runtime referencee;
- garder une separation claire entre edition static et dynamique.

Sortie attendue:
- une edition statique explicite et non ambigue;
- aucune illusion de controle limitee a un changement de path.

## Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables

But:
- rendre visibles les limites reelles du systeme identity et trancher ce qui doit devenir gouvernable.

Travail attendu:
- inventorier proprement et exposer:
  - `IDENTITY_TOP_N`;
  - `IDENTITY_MAX_TOKENS`;
  - `IDENTITY_MIN_CONFIDENCE`;
  - `IDENTITY_DEFER_MIN_CONFIDENCE`;
  - seuils de recurrence et de promotion;
  - budget d'extraction identity distinct;
  - autres caps reels du pipeline;
- distinguer:
  - visible;
  - editable;
  - code en dur;
  - config/env;
  - runtime settings/admin;
- dire explicitement s'il n'existe toujours pas de cap caracteres identity distinct.

Sortie attendue:
- une gouvernance operateur honnete des limites;
- une distinction claire entre stockage, extraction et injection.

## Lot 6 - Assembler la surface `Identity` et sa navigation globale

But:
- finir le chantier par une surface `Identity` vraiment utile, accessible depuis les surfaces clefs.

Travail attendu:
- ajouter une page dediee `Identity`;
- lier cette page:
  - depuis toutes les pages admin utiles;
  - depuis la surface principale LLM;
- garder un ordre de lecture qui aide l'operateur a tout comprendre:
  - structure reelle;
  - etat courant;
  - injection effective;
  - edition;
  - caps et seuils;
  - observabilite.

Sortie attendue:
- un point d'entree unique `Identity`;
- une navigation coherente a l'echelle du produit.

## Observabilite attendue a travers les lots

- Conserver et clarifier les coutures deja presentes sur `identities_read`, `identity_write` et `hermeneutic_node_insertion`.
- Faire apparaitre ce qui manque encore pour l'operateur:
  - presence du statique;
  - identities effectivement injectees;
  - ecart entre stockage et injection;
  - actions operateur identity;
  - etat des conflits ouverts.

## Preuves attendues futures

- tests cibles sur le chargement static et l'injection runtime;
- preuves backend sur les contrats read-only et editables exposes;
- preuves frontend/admin sur la lisibilite de la future surface `Identity`;
- verification live minimale de ce que voit vraiment l'operateur;
- verification documentaire de la source de verite retenue.

## Hors scope global

- implementation immediate de la page `Identity`;
- refonte large du systeme identity en une seule passe;
- mutation opportuniste d'autres surfaces admin sans lien direct;
- changements runtime hors besoin direct du chantier identity;
- relecture speculative de toute l'architecture hermeneutique hors perimetre identity.
