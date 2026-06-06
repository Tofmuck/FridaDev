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

- **Nettoyage dur (L5)**: auditer les responsabilites, identifier le code
  mort probable et supprimer progressivement, par preuves, ce qui ne sert plus
  a tenir BIB-01 -> BIB-33.
- **Validation produit live (L6)**: rejouer une validation conversationnelle
  controlee apres L5 pour prouver que le cleanup n'a casse aucune famille
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

### Contraintes Lot 5

Ces contraintes s'appliquent a Lot 5A et a chaque micro-lot Lot 5B+. Elles
doivent etre reprises explicitement dans les prompts, puis cochees ou invalidees
dans le retour de livraison.

- [ ] Pas de changement de sens documentaire.
- [ ] Pas de reduction de surface visible.
- [ ] Pas de perte de meta observable.
- [ ] Pas de perte de provenance, d'ancre ou d'etat Biblio conversationnel.
- [ ] Pas de nouveau parseur utilisateur.
- [ ] Pas de mutation cote doc-pipeline, DB ou plateforme.
- [ ] Pas de suppression de garde-fou deterministe sans remplacement explicite.
- [ ] Pas de changement de statut BIB sans vraie preuve live JSONL.
- [ ] Pas de redefinition du produit: BIB-01 -> BIB-33 reste la reference.
- [ ] Pas de refactor cosmetique: chaque changement doit supprimer, migrer ou
  isoler une responsabilite prouvee.

### Lot 5A - Audit docs-only

- [ ] Inventorier tous les modules `app/biblio/`.
- [ ] Identifier les entrees publiques reellement appelees.
- [ ] Identifier les methodes produit encore vivantes.
- [ ] Relier chaque methode produit aux BIB qu'elle sert.
- [ ] Identifier les chemins legacy encore necessaires.
- [ ] Identifier les chemins legacy probablement morts.
- [ ] Identifier les doublons de responsabilite.
- [ ] Identifier les modules ou fonctions trop gros ou trop mixtes.
- [ ] Identifier les zones dangereuses a ne pas toucher.
- [ ] Identifier les tests qui protegent des comportements morts.
- [ ] Produire une matrice module -> responsabilite -> BIB -> tests.
- [ ] Produire un plan de suppression par micro-lots.
- [ ] Confirmer qu'aucune suppression runtime n'est faite dans Lot 5A.
- [ ] Verifier que l'audit ne change aucun statut BIB.
- [ ] Commit/push l'audit docs-only separement.

### Lot 5B+ - Suppressions reversibles par micro-lots

Pour chaque micro-lot de suppression ou migration:

- [ ] Formuler l'hypothese de code mort ou de doublon.
- [ ] Prouver statiquement les appels ou non-appels.
- [ ] Verifier les tests associes.
- [ ] Relier la zone touchee aux BIB, methodes produit, metas et surfaces concernees.
- [ ] Decider explicitement: supprimer, migrer ou garder.
- [ ] Supprimer le minimum.
- [ ] Lancer les tests cibles.
- [ ] Lancer la suite Biblio/chat si un chemin commun est touche.
- [ ] Lancer un live regression si une BIB ou surface utilisateur est touchee.
- [ ] Verifier absence de changement de sens documentaire.
- [ ] Verifier absence de reduction de surface visible.
- [ ] Verifier absence de perte de meta/provenance/observabilite.
- [ ] Verifier absence de perte d'etat Biblio conversationnel.
- [ ] Verifier absence de nouveau parseur utilisateur.
- [ ] Verifier que doc-pipeline/DB/plateforme ne sont pas touches.
- [ ] Verifier qu'aucun garde-fou n'est supprime sans remplacement explicite.
- [ ] Verifier qu'un chemin legacy encore utile a une BIB est garde ou migre explicitement.
- [ ] Mettre a jour TODO/spec seulement si une limite ou un contrat change.
- [ ] Auto-auditer le micro-lot.
- [ ] Commit/push separement.

### Interdits Lot 5

- [ ] Ne pas changer le produit defini par BIB-01 -> BIB-33.
- [ ] Ne pas supprimer un garde-fou parce qu'il semble laid.
- [ ] Ne pas supprimer un chemin legacy encore utile sans migration explicite.
- [ ] Ne pas refactorer au-dela du micro-lot.
- [ ] Ne pas creer de nouveau `utils.py` ou `helpers.py`.

## Lot 6 - Validation produit live

But: validation produit live complete post-L5. Lot 6 prouve que le nettoyage Lot
5 n'a pas casse les capacites BIB fermees. La checklist doit rester 33/33.

- [ ] Preparer un panel live representatif BIB-01 -> BIB-33.
- [ ] Couvrir inventaire / metadonnees.
- [ ] Couvrir resolution documentaire.
- [ ] Couvrir structure documentaire.
- [ ] Couvrir recherche scoped.
- [ ] Couvrir extraction exacte.
- [ ] Couvrir section complete / segmentee.
- [ ] Couvrir plage canonique courte.
- [ ] Couvrir plage canonique longue segmentee.
- [ ] Couvrir navigation lecteur.
- [ ] Couvrir chapitre suivant BIB-29.
- [ ] Couvrir provenance / ancre courante.
- [ ] Couvrir memoire de lecture BIB-31/BIB-32.
- [ ] Couvrir roles documentaires sans faux `primary_text`.
- [ ] Couvrir echecs propres BIB-33.
- [ ] Produire un JSONL live date.
- [ ] Verifier vraie conversation Frida.
- [ ] Verifier agent Biblio live appele.
- [ ] Verifier messages assistant sauvegardes.
- [ ] Verifier surfaces visibles propres.
- [ ] Verifier metas/provenance conservees.
- [ ] Verifier Memory observee sur les chemins multi-tour.
- [ ] Verifier aucun faux exact.
- [ ] Verifier aucun snippet rendu comme exact.
- [ ] Verifier aucun faux `primary_text`.
- [ ] Verifier aucune regression BIB-29.
- [ ] Verifier aucune regression BIB-31/BIB-32.
- [ ] Verifier checklist BIB reste 33/33.
- [ ] Documenter les limites restantes.
- [ ] Commit/push.

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
