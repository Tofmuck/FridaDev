# Frida Biblio Last Chance

> **ARCHIVE - 2026-06-06**
>
> Statut: clos / obsolete; ne pilote plus le travail actif.
>
> Raison: la checklist canonique BIB-01 -> BIB-33 est fermee live et conservee
> ci-dessous avec ses artefacts JSONL content-free. Les sections Lot 5 / Lot 6
> ouvertes dans l'ancienne TODO active ont ete neutralisees: elles ne doivent
> plus etre lues comme travail a faire.
>
> Verite courante: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
> pour le contrat vivant; artefacts de preuve dans
> `app/docs/states/baselines/biblio-smokes/`.
>
> Ne pas rouvrir sans decision explicite.

Date: 2026-06-06
Statut historique: checklist BIB fermee live, desormais archivee.
Classement: `app/docs/todo-done/product/`

Archive courte du nettoyage:
`app/docs/todo-done/product/frida-biblio-last-chance-historical-cleanup-2026-06-06.md`.

Historique detaille: consulter le commit pre-nettoyage `645f108` et les
artefacts JSONL listes ci-dessous. La TODO active ne doit plus redevenir une
chronique des lots intermediaires.

## Decision courte / etat courant

La checklist canonique Biblio utilisateur BIB-01 -> BIB-33 est fermee live:
33 items, 33 `ferme_live`, 0 ouvert.

Le chantier actif n'est plus de fermer des capacites BIB. Le faux prolongement
Lot 5 / Lot 6 a ete abandonne: la branche `Biblio-lot-5` a ete supprimee sans
merge le 2026-06-06, apres verification qu'elle ne contenait que des reflexions
docs-only. Aucun nettoyage runtime n'a ete integre.

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

## Note de cloture Lot 5 / Lot 6

Les sections ouvertes Lot 5 et Lot 6 de l'ancienne TODO active ont ete retirees
de cette archive pour eviter toute ambiguite de pilotage.

- Lot 5 a ete abandonne en no-op runtime: la branche `Biblio-lot-5`, qui ne
  contenait que des reflexions docs-only, a ete supprimee sans merge le
  2026-06-06.
- Aucun nettoyage runtime Biblio n'a ete integre.
- Lot 6 n'est pas lance par cette archive et ne constitue plus une TODO active.
- Les preuves utiles restent la checklist BIB-01 -> BIB-33 et le journal JSONL
  ci-dessus.

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
