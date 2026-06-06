# Frida Biblio Last Chance

Date: 2026-06-06
Statut: TODO active de pilotage apres fermeture BIB 33/33
Classement: `app/docs/todo-todo/product/`

Archive courte du nettoyage:
`app/docs/todo-done/product/frida-biblio-last-chance-historical-cleanup-2026-06-06.md`.

Historique detaille: consulter le commit pre-nettoyage `645f108` et les
artefacts JSONL listes ci-dessous. La TODO active ne doit plus redevenir une
chronique des lots intermediaires.

## Decision courte / etat courant

La checklist canonique Biblio utilisateur BIB-01 -> BIB-33 est fermee live:
33 items, 33 `ferme_live`, 0 ouvert.

Le chantier actif n'est plus de fermer des capacites BIB. Les prochains travaux
serieux sont:

- **Lot 5 - Nettoyage dur**: auditer les responsabilites, identifier le code
  mort probable et supprimer progressivement, par preuves, ce qui ne sert plus
  a tenir BIB-01 -> BIB-33.
- **Lot 6 - Validation produit live**: rejouer une validation conversationnelle
  controlee apres Lot 5 pour prouver que le cleanup n'a casse aucune famille
  BIB.

Source normative principale:
`app/docs/states/specs/frida-biblio-native-catalogue-contract.md`.

## Invariants non negociables

- Le bibliothecaire LLM reste souverain sur le sens documentaire: il comprend,
  choisit la methode, clarifie et compare.
- Le deterministe tient seulement les murs techniques: outils GET-only, budgets,
  coherence `document_id`, scopes, ancres, bornes, extraction mecanique,
  final lock, surface visible et observabilite.
- Pas de regex utilisateur comme pseudo-bibliothecaire.
- Pas de jugement semantique code.
- Pas de choix silencieux entre documents, oeuvres, sections ou passages.
- Pas de faux exact: snippet, recherche, TOC et contexte approximatif ne
  deviennent jamais un extrait exact.
- Pas de faux `primary_text`: un role inconnu ou faible reste inconnu/faible.
- Exact text seulement depuis extraction mecanique autorisee:
  `page_read`, `passage_context`, `canonical_range_extract` ou brique future
  explicitement contractee.
- JSONL live obligatoire pour fermer une capacite produit; les artefacts restent
  content-free: pas de secret, prompt brut, dialogue brut, payload Catalogue
  brut, titre/auteur brut, snippet brut ni texte d'ouvrage.
- La surface visible Biblio est lisible pour l'utilisateur. Les ids techniques,
  reason codes, render modes, compteurs internes, `document_id`, `unit_start`,
  `unit_end`, `boundary_state`, statuts machine et details de plomberie restent
  en meta/observabilite/JSONL, pas dans le message assistant normal.

## Checklist canonique Biblio utilisateur (BIB-01 -> BIB-33)

Regle: `[x]` signifie `ferme_live` par vraie conversation Frida ou preuve live
agentique conservee en JSONL content-free.

- [x] BIB-01 - Dire quels ouvrages la bibliotheque contient.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-02 - Dire combien d'ouvrages la bibliotheque contient.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-03 - Donner les metadonnees connues d'un ouvrage: titre, auteur, langue, nombre de pages, statut connu/inconnu.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-04 - Trouver un ouvrage demande par l'utilisateur.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-05 - Distinguer plusieurs ouvrages possibles quand la demande est ambigue.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib05-document-ambiguity-real-conversation-20260605T133539Z.jsonl`
- [x] BIB-06 - Trouver une oeuvre a l'interieur d'un volume.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib06-internal-work-real-conversation-20260606T091906Z.jsonl`
- [x] BIB-07 - Distinguer texte principal, commentaire, preface, notice, notes ou appareil critique.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib07-documentary-roles-real-conversation-20260606T093550Z.jsonl`
- [x] BIB-08 - Donner la table des matieres d'un ouvrage.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-09 - Dire ou commence un chapitre.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-10 - Dire ou finit un chapitre.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-11 - Dire ou commence une section interne.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib11-bib12-bib14-pdf-outline-real-conversation-20260605T183634Z.jsonl`
- [x] BIB-12 - Dire ou finit une section interne.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib11-bib12-bib14-pdf-outline-real-conversation-20260605T183634Z.jsonl`
- [x] BIB-13 - Chercher un theme ou motif dans un ouvrage.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl`
- [x] BIB-14 - Chercher un theme ou motif dans une section precise.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib11-bib12-bib14-pdf-outline-real-conversation-20260605T183634Z.jsonl`
- [x] BIB-15 - Presenter plusieurs passages candidats sans les transformer en extrait exact.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib15-bib17-live-20260604T190851Z.jsonl`
- [x] BIB-16 - Choisir explicitement un candidat parmi plusieurs quand le bibliothecaire a assez d'elements, sans choix deterministe semantique.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib16-bib18-real-conversation-20260604T192312Z.jsonl`
- [x] BIB-17 - Demander une clarification quand plusieurs passages restent possibles.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib15-bib17-live-20260604T190851Z.jsonl`
- [x] BIB-18 - Porter l'ancre d'un candidat choisi ou clarifie vers la suite du dialogue.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib16-bib18-real-conversation-20260604T192312Z.jsonl`
- [x] BIB-19 - Sortir exactement une page demandee.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-document-anchor-20260604T154046Z.jsonl`
- [x] BIB-20 - Sortir exactement deux ou trois pages demandees.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-document-anchor-20260604T154046Z.jsonl`
- [x] BIB-21 - Sortir le debut d'une section quand les bornes sont connues.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib21-real-conversation-20260605T082358Z.jsonl`
- [x] BIB-22 - Sortir un passage autour d'une occurrence trouvee.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib21-bib23-real-conversation-20260605T072804Z.jsonl`
- [x] BIB-23 - Sortir une section complete, avec decoupage si elle est longue.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib23-section-complete-real-conversation-20260605T210700Z.jsonl`
- [x] BIB-24 - Sortir une plage canonique, par exemple un repere Stephanus.
  - Statut: `ferme_live`
  - Preuves: `app/docs/states/baselines/biblio-smokes/bib24-canonical-range-closed-real-conversation-20260605T114227Z.jsonl`; `app/docs/states/baselines/biblio-smokes/bib24-long-canonical-range-real-conversation-20260605T121503Z.jsonl`
- [x] BIB-25 - Dire d'ou vient un passage: ouvrage, page, section, ancre.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib25-bib26-real-conversation-20260604T195551Z.jsonl`
- [x] BIB-26 - Garder l'ancre du passage courant.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib25-bib26-real-conversation-20260604T195551Z.jsonl`
- [x] BIB-27 - Continuer a partir du passage qu'on vient de lire.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib27-bib30-real-conversation-20260604T210551Z.jsonl`
- [x] BIB-28 - Aller a la page suivante ou precedente.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib27-bib30-real-conversation-20260604T210551Z.jsonl`
- [x] BIB-29 - Aller au chapitre suivant.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib29-next-chapter-real-conversation-20260606T120102Z.jsonl`
- [x] BIB-30 - Revenir avant un passage.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib27-bib30-real-conversation-20260604T210551Z.jsonl`
- [x] BIB-31 - Comparer deux passages deja lus.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib31-bib32-read-passages-real-conversation-20260606T082548Z.jsonl`
- [x] BIB-32 - Reprendre un extrait lu plus tot dans la conversation.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib31-bib32-read-passages-real-conversation-20260606T082548Z.jsonl`
- [x] BIB-33 - Dire clairement quand elle ne sait pas, quand c'est ambigu, ou quand la structure manque.
  - Statut: `ferme_live`
  - Preuve: `app/docs/states/baselines/biblio-smokes/bib33-clean-failures-real-conversation-20260606T101042Z.jsonl`

## Journal de preuve live BIB compact

Chaque entree ci-dessous indexe un artefact conserve. Les outils sont donnes en
noms seulement. Les details content-free complets restent dans les JSONL.

| Date | Artefact | BIB | Verdict | Outils principaux |
| --- | --- | --- | --- | --- |
| 2026-06-04 | `app/docs/states/baselines/biblio-smokes/bib15-bib17-live-20260604T190851Z.jsonl` | BIB-15, BIB-17 | `met` | `catalog_search` |
| 2026-06-04 | `app/docs/states/baselines/biblio-smokes/bib16-bib18-real-conversation-20260604T192312Z.jsonl` | BIB-16, BIB-18 | `met` | `catalog_search`, `passage_context` |
| 2026-06-04 | `app/docs/states/baselines/biblio-smokes/bib25-bib26-real-conversation-20260604T195551Z.jsonl` | BIB-25, BIB-26 | `met` | `document_open_summary`, `page_read` |
| 2026-06-04 | `app/docs/states/baselines/biblio-smokes/bib27-bib30-real-conversation-20260604T210551Z.jsonl` | BIB-27, BIB-28, BIB-30 | `met` | `page_read` |
| 2026-06-04 | `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-document-anchor-20260604T154046Z.jsonl` | BIB-19, BIB-20 | `met` | `page_read` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib01-bib14-simple-capabilities-real-conversation-20260605T125932Z.jsonl` | BIB-01, BIB-02, BIB-03, BIB-04, BIB-08, BIB-09, BIB-10, BIB-13 | `met` | `catalog_list`, `search_document`, `document_open_summary`, `document_toc`, `section_bounds`, `catalog_search` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib05-document-ambiguity-real-conversation-20260605T133539Z.jsonl` | BIB-05 | `met` | `search_document` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib11-bib12-bib14-pdf-outline-real-conversation-20260605T183634Z.jsonl` | BIB-11, BIB-12, BIB-14 | `met` | `search_document`, `search_chapters`, `section_bounds`, `catalog_search` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib21-real-conversation-20260605T082358Z.jsonl` | BIB-21 | `met` | `resolve_section`, `section_bounds`, `page_read` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib21-bib23-real-conversation-20260605T072804Z.jsonl` | BIB-22 | `met` | `resolve_work`, `catalog_search`, `passage_context` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib23-section-complete-real-conversation-20260605T210700Z.jsonl` | BIB-23 | `met` | `resolve_work`, `resolve_section`, `section_bounds`, `page_read` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib24-canonical-range-closed-real-conversation-20260605T114227Z.jsonl` | BIB-24 | `met` court complet | `resolve_work`, `canonical_range_extract` |
| 2026-06-05 | `app/docs/states/baselines/biblio-smokes/bib24-long-canonical-range-real-conversation-20260605T121503Z.jsonl` | BIB-24 | `met` long segmente + continuation | `canonical_range_extract` |
| 2026-06-06 | `app/docs/states/baselines/biblio-smokes/bib06-internal-work-real-conversation-20260606T091906Z.jsonl` | BIB-06 | `met` | `resolve_work`, `document_open_summary` |
| 2026-06-06 | `app/docs/states/baselines/biblio-smokes/bib07-documentary-roles-real-conversation-20260606T093550Z.jsonl` | BIB-07 | `met` | `search_chapters` |
| 2026-06-06 | `app/docs/states/baselines/biblio-smokes/bib31-bib32-read-passages-real-conversation-20260606T082548Z.jsonl` | BIB-31, BIB-32 | `met` | `page_read`, passages deja lus via conversation |
| 2026-06-06 | `app/docs/states/baselines/biblio-smokes/bib33-clean-failures-real-conversation-20260606T101042Z.jsonl` | BIB-33 | `met` | familles d'echec Biblio |
| 2026-06-06 | `app/docs/states/baselines/biblio-smokes/bib29-next-chapter-real-conversation-20260606T120102Z.jsonl` | BIB-29 | `met` | `section_bounds`, `page_read` |

## Lot 5 - Nettoyage dur

But: audit de responsabilites + chasse au code mort + suppressions progressives
prouvees dans `app/biblio/`, sans changer le produit.

Le produit est desormais defini par BIB-01 -> BIB-33. Lot 5 n'a pas le droit de
le redefinir, de reduire les capacites utilisateur, ni de remplacer le
bibliothecaire par du determinisme local. Lot 5 a seulement le droit d'enlever,
de deplacer ou de simplifier ce qui ne sert plus a tenir ces capacites.

Contraintes:

- petits pas reversibles;
- pas de changement de sens documentaire;
- pas de reduction de surface visible;
- pas de perte de meta observable;
- pas de perte de provenance;
- pas de perte d'etat Biblio conversationnel;
- pas de perte d'observabilite content-free ni de JSONL;
- pas de nouveaux parseurs utilisateur;
- pas de mutation Catalogue/doc-pipeline/DB/plateforme.
- pas de suppression de garde-fous parce qu'ils semblent moches;
- pas de suppression sans preuve d'appel ou de non-appel;
- chaque suppression doit etre reliee a des tests;
- si un chemin legacy est encore utile a une BIB, on le garde ou on le migre
  explicitement avant suppression.

### Lot 5A - Audit de responsabilites et code mort

Nature: docs-only, aucun patch runtime.

Objectif:

- cartographier `app/biblio/`;
- lister les modules vivants;
- lister les entrees publiques reellement appelees;
- lister les chemins legacy encore necessaires;
- lister le code mort probable;
- lister les doublons;
- lister les zones dangereuses a ne pas toucher;
- relier chaque zone aux BIB, methodes produit, outils et tests qui la
  protegent.

Livrable:

- audit ecrit dans `app/docs/todo-todo/` ou `app/docs/states/audits/` selon son
  statut;
- aucun fichier runtime modifie;
- plan de suppression par micro-lots, avec ordre, risque, preuve statique,
  tests et besoin eventuel de live regression.

### Lot 5B+ - Suppressions reversibles par micro-lots

Chaque micro-lot doit rester petit, reversible et commit/push separe.

Structure obligatoire:

1. Hypothese de code mort ou de doublon.
2. Preuve statique: appels entrants, imports, tests, observabilite, chemins BIB
   concernes.
3. Decision: supprimer, migrer explicitement ou garder.
4. Suppression minimale si et seulement si la preuve tient.
5. Tests unitaires et checks docs.
6. Live regression si une surface, un renderer, une meta, une provenance, un
   etat conversationnel ou un chemin BIB peut etre touche.
7. Auto-audit: pas de changement produit, pas de faux exact, pas de perte de
   meta/provenance/etat, pas de parser utilisateur ajoute.

Sortie attendue de Lot 5:

- `app/biblio/` plus lisible par responsabilite;
- suppressions justifiees et testees;
- aucune BIB requalifiee sans preuve live;
- TODO/spec mises a jour seulement si une limite ou un contrat bouge.

## Lot 6 - Validation produit live

But: validation produit live complete post-L5.

Lot 6 n'est pas une validation vague. C'est un rejeu live controle qui prouve
que le nettoyage Lot 5 n'a pas casse les capacites BIB fermees. La checklist
doit rester 33/33.

Echantillon minimal recommande:

- inventaire;
- resolution;
- structure;
- recherche;
- extraction;
- navigation;
- provenance;
- memoire de lecture;
- echecs propres.

Panel BIB a couvrir:

- inventaire/metadonnees/resolution: BIB-01 -> BIB-05;
- oeuvres internes/roles: BIB-06 -> BIB-07;
- structure/sections/recherche scoped: BIB-08 -> BIB-14;
- candidats/clarification/ancre: BIB-15 -> BIB-18;
- extraction/navigation/provenance: BIB-19 -> BIB-30;
- passages deja lus/memoire/echecs propres: BIB-31 -> BIB-33.

Preuve attendue:

- JSONL live obligatoire;
- vraie conversation Frida;
- agent Biblio live appele;
- messages assistant sauvegardes;
- meta Biblio presente;
- provenance conservee;
- Memory observee sur les chemins multi-tour;
- surface visible propre;
- aucun faux exact;
- aucun snippet exact;
- aucun faux `primary_text`;
- aucune regression BIB-29;
- aucune regression BIB-31/BIB-32;
- checklist BIB-01 -> BIB-33 toujours 33/33;
- artefact content-free conserve dans `app/docs/states/baselines/biblio-smokes/`;
- aucune BIB cochee ou decochee sans preuve.

## Preuves de fermeture minimales

Pour toute regression ou revalidation:

- `git status --short --branch`
- `git diff --check`
- si code Python touche:
  `python3 -m py_compile app/biblio/*.py app/biblio/structure/*.py app/core/chat_service.py app/core/chat_llm_flow.py app/server.py`
- si code Biblio/chat touche:
  `PYTHONPATH=app python3 -m unittest discover app/tests/unit/biblio`
  et `PYTHONPATH=app python3 -m unittest app.tests.unit.chat.test_chat_llm_flow`
- si runtime touche: rebuild cible `fridadev`, `docker ps`, puis verification
  HTTP admin via Authelia.

## Risques restants utiles pour L5/L6

- BIB-29 et les navigations structurelles dependent d'une hierarchie Catalogue
  exploitable; sans ancre de section/chapitre, la bonne reponse reste la
  clarification.
- BIB-23 et BIB-24 prouvent des segments budgetes et continuables, pas un
  export illimite de livre ou de section longue.
- BIB-07 prouve une distinction positive faible et honnete; ne jamais l'etendre
  en `primary_text` sans signal structurel fiable.
- Les artefacts JSONL sont content-free; ne pas les remplacer par des logs bruts
  ou par des captures de dialogue.
- La TODO active doit rester courte. Toute nouvelle strate historique doit aller
  en `todo-done/` ou dans un artefact date, pas dans ce fichier.

## Ce qui a ete retire de la TODO active

Nettoyage 2026-06-06:

- anciens plans Lot 0 -> Lot 4 detailles;
- diagnostics intermediaires et faux verts deja absorbes par les BIB;
- matrices anciennes requalifiees par la checklist canonique;
- longues listes de fichiers et modules historiques;
- redondances de journal de preuve.

La trace historique reste consultable par Git autour du commit `645f108` et par
la note:
`app/docs/todo-done/product/frida-biblio-last-chance-historical-cleanup-2026-06-06.md`.
