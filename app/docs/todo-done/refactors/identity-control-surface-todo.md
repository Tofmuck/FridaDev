# Identity Control Surface TODO

Statut: ferme
Classement: `app/docs/todo-done/refactors/`
Origine: audit identity read-only revalide le `2026-04-05`

Note de requalification `2026-04-18`:
- cette archive fige la phase precedente ou la doctrine mutable etait encore racontee autour d'une `mutable narrative` administree via des coutures legacy de reecriture;
- les passages ci-dessous qui parlent de `reecriture narrative`, de `no_change` ou du lot `1B-B` doivent etre lus comme des jalons historiques de cette phase, pas comme la verite runtime active;
- la verite active actuelle reste: projection `static + mutable narrative` pour l'injection, mais maintien du canon mutable par staging periodique et applicateur deterministe, hors reecriture globale par tour.

## Objectif

Ouvrir un chantier unique pour rendre le systeme identity lisible, controlable et gouvernable par l'operateur, maintenant que la requalification runtime doctrinale est fermee.

Ce TODO a deja ferme deux besoins structurants:
- retablir la verite runtime de l'identity statique;
- requalifier la doctrine des identities mutables autour de `static + mutable narrative`;
- il doit maintenant ouvrir une vraie surface `Identity` capable de montrer ce qui est charge, stocke, injecte, modifiable et limite.

## Pilotage

- [x] Lot 1 - Retablir la verite runtime de l'identity statique
- [x] Lot 1B - Requalifier la doctrine identity mutable avant la surface `Identity`
- [x] Lot 2 - Construire un mode de lecture identity unifie et honnete
- [x] Lot 3 - Ouvrir une edition controlee du dynamique
- [x] Lot 4 - Ouvrir une edition controlee du statique
- [x] Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables
- [x] Lot 6 - Assembler la surface `Identity` et sa navigation globale

## Structure reelle revalidee

- Le modele actuel n'est pas "deux identity par personne".
- Par sujet `llm` et `user`, le systeme combine aujourd'hui:
  - une source statique texte;
  - des identities dynamiques durables;
  - des evidences;
  - des conflits;
  - des statuts `accepted|deferred|rejected`;
  - des overrides.
- Depuis `1B-C`, le prompt runtime actif repose sur:
  - `static + mutable narrative` pour `llm` et `user`;
  - un canon `identity_input` `v2` en `static + mutable`;
  - des `used_identity_ids` honnetement vides dans le flux de reactivation.
- Le legacy fragmentaire reste present dans le repo:
  - evidences, conflits, statuts `accepted|deferred|rejected` et overrides existent encore;
  - mais ils ne pilotent plus l'injection active du prompt runtime.
- Les surfaces admin actuelles ne donnent qu'une lecture partielle:
- `GET /api/admin/hermeneutics/identity-candidates`
- `POST /api/admin/hermeneutics/identity/force-accept`
- `POST /api/admin/hermeneutics/identity/force-reject`
- `POST /api/admin/hermeneutics/identity/relabel`
- `POST /api/admin/identity/mutable`
- Une vraie surface `Identity` existe maintenant, avec navigation dediee depuis les surfaces clefs.

## Etat revalide qui fixe l'ordre des lots

### Ce qui existe deja

- extraction identity via `app/memory/arbiter.py` et `app/prompts/identity_extractor.txt`;
- stockage durable via `identities`, `identity_evidence`, `identity_conflicts`;
- lecture/injection du bloc identity via `app/identity/identity.py`;
- payload canonique identity pour le noeud hermeneutique via `build_identity_input()`;
- mini-surface admin read-only cote `hermeneutic-admin`;
- quelques mutateurs de correction cote backend admin.

### Ce qui manque encore

- aucun lot identity ouvert dans ce chantier; la surface `Identity` et sa navigation globale existent maintenant.

### Point critique prioritaire

- Le Lot 1, le Lot 1B, le Lot 2, le Lot 3, le Lot 4, le Lot 5 et le Lot 6 sont maintenant fermes.
- La surface `Identity` existe maintenant comme point d'entree dedie, aligne sur les contrats read-only, edition et gouvernance deja stabilises.
- Le chantier est ferme sans ressusciter le legacy comme verite active.

## Ordre retenu

- Le Lot 1, le Lot 1B, le Lot 2, le Lot 3, le Lot 4, le Lot 5 et le Lot 6 sont maintenant fermes.
- La page `Identity` arrive bien apres lecture unifiee, editions controlees et gouvernance lisible, sans requalifier les lots precedents.
- Le chantier est maintenant ferme.

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
- le bloc prompt reintegre bien le statique; depuis `1B-C`, le chemin actif repose sur `static + mutable narrative` sans budget runtime legacy.

Hors scope du lot:
- nouvelle page `Identity`;
- edition du contenu static depuis l'admin;
- refonte des endpoints identity.

## Lot 1B - Requalifier la doctrine identity mutable avant la surface `Identity`

Statut: ferme; ancien bloqueur doctrinal avant le Lot 2

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
- le payload canonique actif est maintenant `static + mutable` en `v2`;
- l'injection active repose maintenant sur `static + mutable narrative`; le legacy fragmentaire reste dans le repo mais ne gouverne plus le chemin actif;
- la persistance legacy reste visible via `accepted|deferred|rejected`, mais l'admin identity la presente maintenant comme legacy/evidence-only hors injection active;
- les controles `force_accept`, `force_reject` et `relabel` sont maintenant neutralises cote admin legacy;
- l'observabilite identity est maintenant compacte: longueurs, presence/absence, counts, flags d'update et validation budget/shape, sans previews textuelles ni excerpts bruts.

- [x] `1B-A` Introduire une source de verite canonique durable, une mutable narrative par sujet, distincte des evidences et du legacy fragmentaire
- [x] `1B-B` Requalifier l'extracteur et son contrat pour relire contexte recent + mutable courante et produire `no_change` ou une reecriture narrative validee dans le budget mutable `1500/1650`
- [x] `1B-C` Basculer l'injection active et `identity_input` vers `static + mutable narrative`, sans ranking, sans `IDENTITY_TOP_N`, sans `IDENTITY_MAX_TOKENS` et sans troncature runtime sur la partie mutable
- [x] `1B-D` Reclasser ou neutraliser honnetement le legacy (`accepted|deferred|rejected`, `force_accept`, `force_reject`, `relabel`, controles admin) pour qu'il ne raconte plus la verite d'injection active
- [x] `1B-E` Refaire l'observabilite identity en mode compact, sans previews de contenu brut, avec seulement longueurs, presence/absence, flags d'update et validation budget/shape

Sortie attendue:
- une table canonique `identity_mutables` existe, une ligne par sujet mutable, distincte du legacy `identities` / `identity_evidence` / `identity_conflicts`;
- une doctrine mutable narrative maintenant fermee autour de `static + mutable narrative`;
- des sous-lots `1B-A` a `1B-E` fermes sans laisser deux verites concurrentes;
- une base honnete avant l'ouverture de la future surface `Identity`.

## Lot 2 - Construire un mode de lecture identity unifie et honnete

Statut: ferme; base read-only stable avant les lots d'edition

But:
- donner a l'operateur une lecture unique de la structure reelle du systeme identity.

- [x] Separer clairement `static`, `mutable`, `legacy_fragments`, `evidence`, `conflicts` et `stored` vs effectivement injecte
- [x] Definir un contrat read-only compact et stable pour la future surface `Identity`
- [x] Montrer les sources, dates, ids et etats sans reconstitutions manuelles dispersees
- [x] Exposer une lecture operator-facing minimale dans `/hermeneutic-admin` sans lancer encore la page `Identity`

Sortie attendue:
- une vue read-only qui explique le modele reel sans retomber dans la formule "deux identity par personne";
- une base lisible pour les lots d'edition.

## Lot 3 - Ouvrir une edition controlee du dynamique

Statut: ferme; edition mutable canonique bornee avant l'edition du statique

But:
- permettre a l'operateur de corriger la mutable canonique active sans toucher encore au statique.

- [x] Trancher que `dynamique` = mutable canonique narrative dans `identity_mutables`, et non plus le legacy fragmentaire
- [x] Ouvrir une edition operateur explicite `set` / `clear` de la mutable canonique `llm` / `user`
- [x] Garder le statique, le legacy, les evidences et les conflits en lecture seule
- [x] Appliquer la validation doctrinale `1500 / 1650` sans troncature et journaliser l'audit admin en mode compact
- [x] Exposer cette edition minimale dans `Vue unifiee identity` sans lancer encore la page `Identity`

Sortie attendue:
- une edition de la mutable canonique utile, comprehensible et journalisee;
- aucune confusion entre correction operateur, lecture read-only et legacy fragmentaire.

## Lot 4 - Ouvrir une edition controlee du statique

Statut: ferme; statique canonique file-backed editable via ressource runtime referencee

But:
- permettre l'edition du contenu static lui-meme, pas seulement de ses chemins.

- [x] Trancher la source de verite durable du contenu statique apres Lot 1
- [x] Definir comment l'operateur lit, modifie, valide et sauvegarde `llm` / `user` statiques
- [x] Expliciter la place des fichiers statiques dans le produit: ressource repo, ressource state ou ressource runtime referencee
- [x] Garder une separation claire entre edition static et dynamique

Sortie attendue:
- une edition statique explicite et non ambigue;
- aucune illusion de controle limitee a un changement de path.

## Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables

Statut: ferme; gouvernance identity minimale stabilisee avant la page `Identity`

But:
- rendre visibles les limites reelles du systeme identity et trancher ce qui doit devenir gouvernable.

- [x] Inventorier proprement et exposer `IDENTITY_TOP_N`, `IDENTITY_MAX_TOKENS`, `IDENTITY_MIN_CONFIDENCE`, `IDENTITY_DEFER_MIN_CONFIDENCE`, les seuils de recurrence et de promotion, le budget d'extraction identity distinct et les autres caps reels du pipeline
- [x] Distinguer ce qui est visible, editable, code en dur, en config/env et en runtime settings/admin
- [x] Dire explicitement s'il n'existe toujours pas de cap caracteres identity distinct

Sortie attendue:
- une gouvernance operateur honnete des limites;
- une distinction claire entre stockage, extraction et injection.

## Lot 6 - Assembler la surface `Identity` et sa navigation globale

Statut: ferme; surface `Identity` dediee et navigation globale ajoutees

But:
- finir le chantier par une surface `Identity` vraiment utile, accessible depuis les surfaces clefs.

- [x] Ajouter une page dediee `Identity`
- [x] Lier cette page depuis toutes les pages admin utiles et depuis la surface principale LLM
- [x] Garder un ordre de lecture qui aide l'operateur a tout comprendre: structure reelle, etat courant, injection effective, edition, caps et seuils, observabilite

Sortie attendue:
- un point d'entree unique `Identity`;
- une navigation coherente a l'echelle du produit.

Cloture du lot:
- `GET /identity` sert une page dediee alignee sur `admin.css`;
- la page explique clairement la difference entre la fiche structuree pour le jugement et le texte identity injecte au modele;
- la navigation `Identity` existe depuis `/`, `/admin`, `/log` et `/hermeneutic-admin`;
- les contrats Lots 2 a 5 sont reemployes sans rouvrir la doctrine `static + mutable narrative`.

## Observabilite de cloture

- [x] Conserver et clarifier les coutures deja presentes sur `identities_read`, `identity_write` et `hermeneutic_node_insertion`
- [x] Faire apparaitre pour l'operateur la presence du statique, les identities effectivement injectees, l'ecart entre stockage et injection, les actions operateur identity et l'etat des conflits ouverts

## Preuves de cloture

- [x] Tests cibles sur le chargement static et l'injection runtime
- [x] Preuves backend sur les contrats read-only et editables exposes
- [x] Preuves frontend/admin sur la lisibilite de la surface `Identity`
- [x] Verification live minimale de ce que voit vraiment l'operateur
- [x] Verification documentaire de la source de verite retenue

## Hors scope global

- refonte large du systeme identity en une seule passe;
- mutation opportuniste d'autres surfaces admin sans lien direct;
- changements runtime hors besoin direct du chantier identity;
- relecture speculative de toute l'architecture hermeneutique hors perimetre identity.
