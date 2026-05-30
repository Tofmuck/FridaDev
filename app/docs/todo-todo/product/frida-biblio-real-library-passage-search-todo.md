# Frida Biblio vraie bibliotheque / recherche de passages - TODO P1

Statut: actif
Date de creation: 2026-05-30
Classement: `app/docs/todo-todo/product/`
Spec source-of-truth: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Chantier Biblio archive: `app/docs/todo-done/product/frida-biblio-native-catalogue-todo.md`
Validation archivee: `app/docs/todo-done/validations/frida-biblio-native-catalogue-validation-2026-05-29.md`
Commit declencheur: `b5e1df2 Add Biblio librarian runtime`
Priorite: P1 produit

## 1. Probleme

Le correctif `b5e1df2` a transforme Biblio en bibliothecaire minimal:

- le toggle Biblio arrive au backend;
- le Catalogue est consulte en GET-only;
- les premiers ouvrages peuvent etre listes;
- une demande bien cadree par oeuvre + auteur + locator/range peut extraire un passage borne;
- les events et surfaces admin restent content-free.

Ce n'est pas encore une vraie bibliotheque produit.

Cas cible non satisfait:

```text
Peux-tu me trouver dans le Theetete le passage ou Socrate parle de la maieutique ?
```

Attendu produit:

- Biblio activee;
- consultation Catalogue reelle;
- oeuvre interne `Theetete` traitee comme dialogue possible dans un volume physique;
- recherche thematique sur le passage demande;
- candidats de paragraphes/passages;
- ranking borne;
- extraction via `/context`;
- injection d'un ou plusieurs passages dans `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`;
- reponse Frida avec le passage, ou ambiguite honnete si le choix n'est pas sur.

Etat actuel observe:

- la phrase cible est detectee comme `search_catalog`, pas comme `no_signal` dans l'etat post-`b5e1df2`;
- la branche `search_catalog` peut construire une lane de consultation ou des candidats, mais elle ne va pas jusqu'a extraire un passage;
- les chemins d'extraction restent principalement `locator` / `range`;
- les formulations naturelles sans locator, par theme, mot, expression ou paraphrase restent insuffisamment prises en charge;
- des formulations dictees, approximatives ou sans accents doivent etre mieux normalisees avant planification;
- le systeme ne doit pas se refugier dans `locator_required_for_passage` quand l'utilisateur demande clairement un passage thematique.

Conclusion: le finding principal est valide. Le bug n'est pas "Catalogue inaccessible"; c'est une lacune de bibliothecaire entre recherche conceptuelle et extraction bornee.

## 2. Objectif produit

Biblio doit fonctionner comme une bibliotheque consultable:

- lister les ouvrages;
- chercher un ouvrage, un auteur, un corpus ou une oeuvre interne;
- comprendre les alias raisonnables d'oeuvres et variantes sans accents;
- chercher des passages par theme, mot, expression ou formulation naturelle;
- selectionner des candidats de passage avec ranking explicable;
- extraire un ou plusieurs passages bornes;
- injecter seulement les passages retenus dans la lane Biblio;
- permettre a Frida de repondre dans le chat avec le texte du passage demande.

Biblio ne doit pas devenir:

- RAG documentaire global;
- recherche semantique large non bornee;
- Memory/RAG;
- documents actifs;
- workspace;
- Web;
- Summary;
- Identity;
- Hermeneutic;
- AnythingLLM;
- OCR general.

## 3. Invariants durs

### FridaDev reste GET-only cote Catalogue

Autorise depuis FridaDev:

- `GET /health`;
- `GET /catalog`;
- `GET /doc/{id}`;
- `GET /doc/{id}/metadata`;
- `GET /doc/{id}/locate`;
- `GET /doc/{id}/context`;
- `GET /search`;
- nouveaux GET si un lot futur demontre qu'ils sont necessaires.

Interdit depuis FridaDev:

- `DELETE`;
- `PUT`;
- `POST` mutateur;
- ecriture DB Catalogue;
- suppression fichier ou DB;
- backfill;
- OCR;
- re-OCR.

### Observabilite content-free

Interdit dans logs, admin, dashboard, read-model et retour technique:

- passage brut;
- texte OCR brut;
- payload Catalogue brut;
- prompt complet;
- `BiblioPromptLane.message`;
- titre brut;
- auteur brut;
- locator brut;
- requete utilisateur brute;
- secret, token, cookie, DSN, `.env`.

Autorise en observabilite:

- status;
- reason codes;
- counts;
- doc ids courts;
- hashes courts;
- longueurs;
- positions non textuelles;
- endpoint kinds;
- durees;
- bornes appliquees;
- flags d'ambiguite.

Important: l'interdiction de contenu brut concerne les surfaces techniques. Le produit final doit bien pouvoir afficher le passage dans le chat quand l'utilisateur le demande et que Biblio l'a extrait.

## 4. Lots proposes

### Lot 0 - Audit actuel et repro live content-free

- [ ] Reproduire les cas live sans afficher de contenu d'ouvrage brut.
- [ ] Confirmer pour chaque cas: `query_kind`, `status`, `reason_code`, `client_count`, `candidate_count`, `passage_count`, `lane_injected`.
- [ ] Auditer le shape content-free de `/search` et `/context`: champs disponibles, presence ou absence de `paragraph_id`, page, paragraphe, titre document, score/rank.
- [ ] Mesurer si `/search` retourne assez de positions pour appeler `/context` sans nouvelle API.
- [ ] Identifier les limites exactes de `library_runtime._search_catalog()`: candidats injectes, absence d'extraction.
- [ ] Lister les cas qui tombent encore en `no_signal`, `locator_required_for_passage`, `not_found` ou `ambiguous`.
- [ ] Verifier que toggle off ne construit toujours aucun client Catalogue.

Preuves attendues, content-free:

- pas de passage brut dans les sorties;
- pas de titre/auteur/requete brute dans observabilite;
- counts, ids courts, hashes, longueurs et positions seulement.

### Lot 1 - Normalisation requete / accents / dictee / alias d'oeuvres

- [ ] Centraliser une normalisation partagee: accents, apostrophes, ligatures, ponctuation dictee, variantes `bibliotheque` / `biblio`.
- [ ] Gerer `Theetete`, `Theaitetos`, `Theaetetus`, `Théétète` comme alias candidats sans inventer une correspondance certaine.
- [ ] Separer proprement:
  - oeuvre interne;
  - corpus / auteur;
  - theme recherche;
  - locator eventuel;
  - demande de liste.
- [ ] Ne jamais promouvoir les fragments `le`, `la`, `l`, `bibliotheque`, `catalogue`, `ouvrage`, `livre` en titre utilisable.
- [ ] Couvrir les formulations dictees sans accents: `maieutique`, `Theetete`, `ou Socrate parle de`.
- [ ] Garder une strategie conservatrice: si la demande est vraiment vague, clarifier au lieu de chercher toute la bibliotheque.

Tests minimum:

- `Trouve dans le Theetete le passage ou Socrate parle de la maieutique`;
- `trouve dans le Théétète le passage où Socrate parle de la maïeutique`;
- `cherche maieutique dans la bibliotheque`;
- `cherche un livre sympa` reste non bibliographique ou clarification explicite, sans appel Catalogue large.

### Lot 2 - Planner documentaire de recherche de passage

- [ ] Etendre le planner au-dela de `search_catalog` / `extract_locator`.
- [ ] Ajouter une intention explicite, par exemple `search_passage` ou `extract_conceptual_passage`.
- [ ] Produire un plan structure separe:
  - `work_title`;
  - `corpus_or_author`;
  - `theme_query`;
  - `quoted_expression`;
  - `locator_start`;
  - `locator_end`;
  - `needs_clarification`.
- [ ] Evaluer si le deterministe suffit.
- [ ] Si le deterministe devient fragile, specifier un planner LLM structure avant le LLM principal:
  - entree: message utilisateur + `biblio_enabled`;
  - sortie JSON stricte;
  - schema borne;
  - pas de passage brut dans logs;
  - fallback deterministe si JSON invalide;
  - aucun appel Catalogue si le planner conclut `not_bibliographic`.
- [ ] Documenter le contrat de planification et les reason codes.

Sorties attendues:

- demande thematique claire -> plan de recherche de passage;
- demande de liste -> `list_catalog`;
- demande locator -> `extract_passage` / `extract_range`;
- demande vague -> `clarify_ambiguous`.

### Lot 3 - Moteur `search -> candidats -> context`

- [ ] Creer ou etendre un module dedie sans gonfler `chat_runtime.py`.
- [ ] Pour une recherche thematique:
  - chercher oeuvre/corpus via `/catalog` et/ou `/search`;
  - filtrer les resultats par document candidat quand possible;
  - convertir les resultats `/search` en cibles `/context`;
  - appeler `/context` uniquement sur un petit nombre de candidats bornes;
  - ne jamais injecter tout le document.
- [ ] Preferer les positions non textuelles (`paragraph_id`, `page_no`, `para_no`) aux payloads bruts.
- [ ] Si `/search` ne fournit pas de `paragraph_id`, verifier le couple `page_no` / `para_no`.
- [ ] Refuser les contextes incoherents (`document_id` absent ou divergent).
- [ ] Definir bornes:
  - max resultats `/search`;
  - max contextes appeles;
  - max chars par passage;
  - max chars total lane;
  - timeout et comportement degrade.

Statuts attendus:

- `searched`;
- `candidate_selected`;
- `extracted`;
- `ambiguous`;
- `not_found`;
- `too_long`;
- `catalogue_unavailable`;
- `invalid_request`.

### Lot 4 - Ranking et selection bornee de passages

- [ ] Definir un ranking explicable content-free:
  - match document / oeuvre;
  - match theme ou expression;
  - proximite des mots cles;
  - score Catalogue si disponible;
  - diversite des candidats;
  - longueur acceptable.
- [ ] Ajouter une strategie d'ambiguite:
  - plusieurs passages plausibles -> injecter top N avec statut clair, ou demander clarification;
  - candidats dans plusieurs documents -> candidats documentaires, pas extraction forcee;
  - score insuffisant -> `not_found` ou clarification.
- [ ] Ne pas inventer une certitude sur un passage seulement parce qu'un mot apparait.
- [ ] Prevoir un mode multi-passage borne pour themes disperses.
- [ ] Tester que les passages non retenus ne sont pas exposes en observabilite.

### Lot 5 - Injection lane Biblio avec passages multiples possibles

- [ ] Reutiliser `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` pour les passages extraits.
- [ ] Injecter un a trois passages retenus, selon bornes.
- [ ] Conserver le contrat d'interpretation: passages consultes, pas lecture totale.
- [ ] Ne pas fusionner avec `active_document`.
- [ ] Ne pas injecter les lanes de consultation candidates a la place d'un passage si un passage a ete extrait.
- [ ] Ajouter une observabilite lane:
  - `passage_count`;
  - `candidate_count`;
  - `selected_count`;
  - `skipped_count`;
  - chars;
  - hashes courts;
  - doc ids courts;
  - positions non textuelles.
- [ ] Garantir que `BiblioPromptLane.message` et les passages restent absents des logs/admin/dashboard.

### Lot 6 - Smokes live philosophiques

- [ ] Ajouter un script ou protocole smoke content-free reutilisable.
- [ ] Verifier les cas obligatoires:
  - `Tu peux chercher et voir les premiers ouvrages ?`;
  - `Extrait du Theetete de Platon 126b a 128a`;
  - `Trouve dans le Theetete le passage ou Socrate parle de la maieutique`;
  - `Cherche maieutique dans la bibliotheque`;
  - formulation dictee approximative sans accents.
- [ ] Pour chaque smoke, reporter seulement:
  - status;
  - reason code;
  - query kind;
  - client count;
  - candidate count;
  - selected count;
  - passage count;
  - lane injected;
  - doc ids courts;
  - hashes courts;
  - longueurs.
- [ ] Ne jamais afficher le texte d'ouvrage dans le retour technique.

### Lot 7 - Observabilite/admin content-free

- [ ] Etendre `build_biblio_event_payload()` si besoin pour les recherches thematiques.
- [ ] Ajouter les projections content-free:
  - `theme_query` longueur/hash;
  - `work_query` longueur/hash;
  - `search_candidate_count`;
  - `context_fetch_count`;
  - `selected_passage_count`;
  - `selection_reason_codes`;
  - `ranking_available`.
- [ ] Verifier dashboard/read-model si de nouvelles cles sont materialisees.
- [ ] Tester que les titres, auteurs, locators bruts, requetes brutes et passages ne fuitent pas.
- [ ] Ne pas ajouter de dashboard brut de passages.

### Lot 8 - Validation finale GO/NO-GO

- [ ] Repasser les invariants GET-only.
- [ ] Repasser toggle off / toggle on sans signal.
- [ ] Repasser separation active documents / Biblio / Memory/RAG / Web / Identity / Summary.
- [ ] Executer suites Biblio, chat et admin pertinentes.
- [ ] Executer smokes live content-free.
- [ ] Mettre a jour la spec Biblio et cette TODO.
- [ ] Si tout est clos, archiver cette TODO dans `app/docs/todo-done/product/` avec une note de validation.

GO si:

- la demande thematique cible extrait un passage ou produit une ambiguite honnete apres consultation reelle;
- les passages extraits peuvent etre affiches par Frida dans le chat;
- aucune fuite de contenu brut n'existe dans les surfaces techniques;
- le Catalogue reste GET-only cote FridaDev.

NO-GO si:

- la branche thematique s'arrete aux candidats sans extraction;
- une demande bibliographique claire redevient `no_signal`;
- Frida dit a tort qu'elle n'a pas acces a la bibliotheque alors que Biblio est activee et Catalogue joignable;
- observabilite/admin/dashboard exposent un passage, une requete brute ou un prompt complet.

## 5. Tests cibles

Suites existantes a etendre:

- `tests.unit.biblio.test_query_planner`;
- `tests.unit.biblio.test_work_resolver`;
- `tests.unit.biblio.test_chat_runtime`;
- `tests.unit.biblio.test_passage_extractor`;
- `tests.unit.biblio.test_prompt_lane`;
- `tests.unit.biblio.test_observability`;
- `tests.test_server_chat_biblio_contract`;
- `tests.test_server_admin_chat_logs_contract`.

Nouvelles suites probables:

- `tests.unit.biblio.test_passage_search_runtime`;
- `tests.unit.biblio.test_passage_ranking`;
- `tests.unit.biblio.test_biblio_query_normalization`;
- `tests.unit.biblio.test_biblio_planner_llm_contract` si planner LLM retenu.

Cas obligatoires:

- toggle off: aucun client Catalogue construit;
- toggle on sans signal clair: aucun client Catalogue construit;
- liste premiers ouvrages: consultation Catalogue, pas de passage brut dans observabilite;
- locator/range Theetete: extraction existante non regresse;
- recherche thematique Theetete/maieutique: candidats puis extraction ou ambiguite explicite;
- recherche simple `maieutique dans la bibliotheque`: candidats puis extraction ou ambiguite;
- phrase sans accents/dictee: meme intention que phrase accentuee;
- aucune confusion avec documents actifs;
- aucune fuite dans observabilite.

## 6. Smokes live obligatoires

Les smokes live doivent etre lances apres rebuild seulement quand du runtime est touche.

Cas:

```text
Tu peux chercher et voir les premiers ouvrages ?
Extrait du Theetete de Platon 126b a 128a
Trouve dans le Theetete le passage ou Socrate parle de la maieutique
Cherche maieutique dans la bibliotheque
Trouve dans l Theetete le passage ou Socrate parle maieutique
```

Retour technique autorise:

- `status`;
- `reason_code`;
- `query_kind`;
- `client_count`;
- `candidate_count`;
- `selected_count`;
- `passage_count`;
- `lane_injected`;
- `doc_id_shorts`;
- `hashes`;
- `chars`;
- `raw_term_leaks=false`;
- `prompt_message_in_observability=false`.

Retour technique interdit:

- texte du passage;
- extrait OCR;
- payload Catalogue;
- prompt complet;
- titre/auteur/requete/locator brut;
- secret ou configuration sensible.

## 7. Hors-scope

- Patch `/opt/platform/doc-pipeline` avant preuve qu'une route GET manque.
- Modification API Catalogue.
- Route API Biblio metier dans FridaDev.
- Ecriture DB Biblio metier.
- OCR ou re-OCR.
- RAG documentaire global.
- Memory/RAG, Identity, Summary, Web, Hermeneutic ou documents actifs.
- UI Catalogue dans FridaDev.
- Recherche automatique quand `biblio_enabled=false`.

## 8. Notes de mise en oeuvre

- Ne pas transformer `chat_runtime.py` en fourre-tout.
- Preferer un module de passage search dedie si le Lot 3 grossit.
- Ne pas faire confiance au texte de `/search` comme passage final: extraire via `/context` avec document id coherent.
- Si un planner LLM est retenu, il doit produire du JSON strict et etre appele avant le LLM principal, sans exposer de passage brut dans les logs.
- La reponse produit peut citer le passage uniquement parce que la lane prompt le contient explicitement.
- Les preuves techniques doivent rester content-free, meme quand le passage est correctement extrait.
