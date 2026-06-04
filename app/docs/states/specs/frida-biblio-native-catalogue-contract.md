# Frida Biblio native / Frida Catalogue contract

Statut: spec vivante
Date: 2026-05-28
Mise a jour Lot 5: 2026-05-29
Correctif post-audit Lot 5: 2026-05-29
Mise a jour Lot 6: 2026-05-29
Correctif post-audit Lot 6: 2026-05-29
Mise a jour Lot 7: 2026-05-29
Correctif post-audit Lot 7: 2026-05-29
Validation finale Lot 8: 2026-05-29
Correctif bibliothecaire Biblio reelle: 2026-05-30
Mise a jour recherche passages Lot 5: 2026-05-30
Mise a jour recherche passages Lot 6: 2026-05-30
Mise a jour recherche passages Lot 7: 2026-05-30
Validation finale recherche passages Lot 8: 2026-05-30
Reouverture produit vraie bibliotheque: 2026-05-30
Route legere table des matieres Catalogue: 2026-05-30
Etat conversationnel agent bibliothecaire Lot 1: 2026-05-31
Socle agent bibliothecaire Lot 7: 2026-06-01
Navigation documentaire R1: 2026-06-02
Signal faible role documentaire Lot E: 2026-06-02
Manifeste documentaire minimal Last Chance Lot 1: 2026-06-03
API/outils minimaux Last Chance Lot 2: 2026-06-04
Cadrage enrichissement structurel Last Chance Lot 2 bis: 2026-06-04
Premier cran aliases structurels Last Chance Lot 2 bis: 2026-06-04
Premier cran answer object Last Chance Lot 3: 2026-06-04
Verrou final assistant Last Chance L3A1: 2026-06-04
Memoire conversationnelle des lectures Last Chance Lot 3 bis: 2026-06-04
Premiere methode canonique Last Chance Lot 4A: 2026-06-04
Resolution documentaire canonique Last Chance Lot 4B: 2026-06-04
Structure/TOC canonique Last Chance Lot 4C: 2026-06-04
Recherche scoped canonique Last Chance Lot 4D: 2026-06-04
Classement: `app/docs/states/specs/`
Roadmap archivee: `app/docs/todo-done/product/frida-biblio-native-catalogue-todo.md`
Validation finale: `app/docs/todo-done/validations/frida-biblio-native-catalogue-validation-2026-05-29.md`
Preuve role signal: `app/docs/states/baselines/frida-biblio-role-signal-proof-2026-06-02.md`
Trace navigation chapter hint: `app/docs/states/baselines/frida-biblio-navigation-chapter-hint-trace-2026-06-03.md`
Roadmap vraie bibliotheque archivee: `app/docs/todo-done/product/frida-biblio-real-library-passage-search-todo.md`
Validation vraie bibliotheque requalifiee: `app/docs/todo-done/validations/frida-biblio-real-library-passage-search-validation-2026-05-30.md`
Remediation vraie bibliotheque archivee: `app/docs/todo-done/product/frida-biblio-real-library-product-gap-todo.md`
Audit Lot 0 Catalogue: `app/docs/states/audits/frida-catalogue-human-metadata-editing-audit-2026-05-28.md`
Specs voisines: `app/docs/states/specs/active-conversation-documents-contract.md`, `app/docs/states/specs/workspace-folders-contract.md`
Portee: contrat produit, frontieres, client futur GET-only, resolver, extraction bornee, lane prompt, observabilite et surface admin content-free de Biblio native.

## 1. Statut et portee

Biblio native est une capacite documentaire persistante separee. Elle permet a FridaDev de consulter une bibliotheque durable connue de Frida Catalogue / doc-pipeline, lister ou chercher des ouvrages, puis resoudre un document, une oeuvre interne et un passage documentaire borne a la demande.

Source nominale:

- API Catalogue / doc-pipeline;
- DB Catalogue geree par la stack Catalogue;
- metadonnees humaines Lot 0 quand elles existent;
- metadonnees d'ingestion comme trace source, jamais comme titre canonique si une correction humaine existe.

Le premier client FridaDev doit etre strictement read-only / GET-only.

Le Lot 1 historique du chantier Biblio native 2026-05-28 ne livrait aucun code runtime:

- pas de route FridaDev;
- pas de client Catalogue;
- pas de toggle frontend;
- pas de lane prompt effective;
- pas de branchement chat;
- pas de DB;
- pas de modification de `/opt/platform/doc-pipeline`;
- pas de modification de `/opt/platform/doc-library`.

## 2. Vocabulaire stabilise

`library_document`: document persistant d'une bibliotheque native. Terme generique cote FridaDev.

`catalogue_document`: `library_document` dont la source de verite est Frida Catalogue / doc-pipeline. Il possede un identifiant Catalogue, des metadonnees source et, si disponibles, des metadonnees humaines.

`passage documentaire`: extrait borne issu d'un `library_document` ou `catalogue_document`, consulte a la demande pour un tour. Il n'est pas un document actif et ne devient pas automatiquement durable dans FridaDev.

`locator`: repere documentaire demande ou resolu. Exemples: page, chapitre, paragraphe, milestone Stephanus, intervalle `126b -> 126e`, citation structuree ou autre repere supporte par Catalogue.

`resolver documentaire`: service futur FridaDev qui transforme une demande utilisateur en resultat structure:

- document cible;
- locator demande;
- locator resolu;
- statut;
- confiance;
- raisons compactes;
- preuve content-free.

`resolved`: document et locator suffisamment determines pour permettre une extraction bornee sans presenter l'incertitude comme certaine.

`ambiguous`: plusieurs documents, editions, dialogues, locators ou passages restent plausibles. Le modele doit voir l'ambiguite.

`not_found`: aucun document ou locator compatible n'a ete trouve.

`error`: la consultation Catalogue a echoue pour raison technique ou contractuelle.

`confidence`: signal borne, non souverain, qui indique la qualite de resolution. Il peut etre qualitatif ou numerique dans un lot futur, mais ne doit jamais masquer `ambiguous`, `not_found` ou `error`.

`source metadata`: metadonnees d'ingestion ou d'OCR portees par Catalogue: titre auto, nom de fichier source, hash, langue detectee, type source, compteurs, qualite JSON, TOC et champs apparentes.

`human metadata`: metadonnees bibliographiques corrigees humainement par Lot 0 Catalogue: titre canonique, titre original, auteur(s), traducteur(s), editeur scientifique, editeur, collection, annee, langue override, type, notes operateur, statut.

`DocumentManifest`: projection structurelle FridaDev, versionnee, validable et
content-free, derivee du fonds Catalogue existant et obligatoire pour les
imports nominaux futurs. Elle porte `LibraryDocument`, `Work`, `SectionNode`,
`TextUnit`, `Anchor`, `Interval`, `CanonicalReference`, `ContentRole`, signal de
langue exploitable et validation de forme, avec etats `known`, `unknown`,
`derived` ou `ambiguous`. Le manifeste ne contient ni texte long d'ouvrage, ni
payload Catalogue brut, ni titre/auteur brut; il porte des ids, compteurs,
ancres, roles, limites, raisons content-free et hashes courts.

Livraison Last Chance Lot 1:

- module: `app/biblio/structure/`;
- runner de preuve: `app/biblio/document_manifest_baseline.py`;
- artefact:
  `app/docs/states/baselines/biblio-manifests/frida-biblio-document-manifest-lot1-20260603T173615Z.json`;
- artefact correctif rejouable:
  `app/docs/states/baselines/biblio-manifests/frida-biblio-document-manifest-lot1-correctif-20260603T183445Z.json`;
- couverture: 10 documents vus, 10 manifestes produits, 0 echec;
- validation: 10 manifestes `valid_with_warnings`, 0 reason code invalidant;
- verrou baseline: `valid` et `valid_with_warnings` passent; `invalid` devient
  une failure `manifest_validation_failed` avec `validation_reason_codes` et
  fait sortir le runner non-zero;
- usine d'entree doc-pipeline: le worker nominal controle le payload normalise
  avant DB et les tables reellement ecrites avant commit. `accepted` couvre
  `valid` / `valid_with_warnings`; `invalid` bloque l'import avec reason codes
  content-free, notamment si pages, paragraphes, unites ou `raw_units` manquent;
- preuve d'entree reelle 2026-06-03: un EPUB UQAM fourni a ete importe par le
  worker nominal avec `quality_gate=accepted`, `validation=valid_with_warnings`,
  0 reason code invalidant; la baseline courante apres import voit 11 documents,
  11 manifestes, 0 failure;
- normalisation: EPUB, PDF et origines inconnues futures doivent converger vers
  ce meme modele de sortie;
- contrat d'import: un nouvel ouvrage ajoute par le chemin nominal doit etre
  projetable/validable comme `DocumentManifest`; si les champs minimaux
  manquent, la preuve doit produire un echec content-free explicite;
- limite volontaire: ce correctif ne modifie ni DB schema, ni API Catalogue, ni
  chat runtime; le worker d'import doc-pipeline a ete modifie de facon ciblee
  pour porter le gate d'entree.

Livraison Last Chance Lot 2:

- module haut niveau: `app/biblio/librarian_library_tools.py`;
- registry exposee: `search_document`, `search_work`, `search_section`,
  `resolve_work`, `resolve_section`, `section_bounds`;
- routes Catalogue consommees: GET-only via `/catalog`, `/doc/{id}/metadata`
  et `/doc/{id}/chapters`; aucune route mutatrice, export ou payload lourd n'est
  introduit;
- `search_document` cherche des documents/ouvrages dans le catalogue; il ne
  doit pas etre confondu avec une recherche plein texte de passage;
- `search_section`, `resolve_section` et `section_bounds` sont scopees par
  `document_id` et derivees de la TOC/manifeste du document cible; elles ne
  presentent pas une recherche globale de chapitres comme resolution scoped;
- les resolutions strictes retournent `resolved`, `ambiguous` ou `not_found`;
  ces statuts sont content-free et visibles par le planner;
- `section_bounds` renvoie des ancres debut/fin derivees du manifeste lorsque
  la section est unique; les bornes derivees restent signalees comme telles;
- le schema agent OpenRouter et les methodes produit acceptent ces outils
  comme primitives documentaires GET-only.

Cadrage Last Chance Lot 2 bis:

- Lot 2 donne au bibliothecaire des outils minimaux, mais ne garantit pas a lui
  seul la richesse documentaire necessaire aux questions canoniques;
- la couche documentaire doit porter aliases, titres alternatifs,
  transliterations, titres courts, oeuvres internes, titres de sections,
  hierarchies de sections, roles de contenu et bornes plus fiables quand ces
  signaux sont disponibles ou derivables honnetement;
- le contrat ne doit pas transformer des regressions severes comme Kant,
  Foucault ou Stephanus en regex locales ni en cas canoniques substitues aux
  questions de bibliotheque;
- les 18 cas historiques restent une matrice de regression, pas 18 outils ni
  le canon principal du chantier;
- le bibliothecaire LLM reste souverain pour explorer, comparer et proposer les
  ancres; le deterministe reste limite a GET-only, budgets, validation de
  forme, refus de routes dangereuses, observabilite content-free et extraction
  mecanique quand les ancres sont donnees;
- si la structure ne suffit pas, les outils doivent exposer des statuts ou
  reason codes content-free (`ambiguous`, `not_found`,
  `work_alias_missing`, `internal_work_unresolved`,
  `section_alias_missing`, `primary_text_role_unknown` ou equivalents)
  plutot que fabriquer une certitude bibliographique.

Premier cran Lot 2 bis livre:

- `DocumentManifest` porte `AliasSignal` sur `Work` et `SectionNode`;
- les aliases sont derives seulement depuis les signaux deja fournis par
  Catalogue/metadonnees/TOC (`title`, `chapter_title`, `label`, `short_title`,
  `aliases`, `title_aliases`, `alternative_titles`) et par transliteration
  accent-stripped d'un alias existant;
- la serialisation manifeste reste content-free: count, state, source et
  hashes courts, jamais labels bruts;
- `search_section`, `resolve_section`, `section_bounds` et les candidats
  `section_scope` de `search_work` utilisent ces aliases dans le scope du
  document cible, sans presenter `search_chapters` global comme resolution
  scoped;
- les resultats outils n'exposent que `alias_count`, `alias_state` et
  `alias_source`; les aliases bruts ne doivent pas apparaitre dans
  l'observabilite;
- `section_alias_missing`, `internal_work_unresolved` et `work_alias_missing`
  rendent les insuffisances structurelles explicites;
- restent ouverts: oeuvres internes fiables, hierarchie profonde, roles
  primaires/commentaires forts, mapping section -> paragraphe/raw unit et
  bornes d'oeuvre interne.

Premier cran Last Chance Lot 3 livre:

- module: `app/biblio/answer_object.py`;
- `BiblioAnswerObject` devient le guichet de verite de sortie entre la lane
  Biblio interne, le resultat structure et le rendu produit minimal;
- statuts minimaux: `ready`, `ambiguous`, `not_found`,
  `needs_clarification`, `error`;
- champs minimaux: `product_method`, `case_id`, `document_id`, `work_id`,
  `section_id`, `anchors`, `interval`, `content_role`, `provenance`,
  `limits`, `reason_codes`, `truth_level`, `source_tool_names` et
  `render_mode`;
- render modes minimaux: `structured_status`, `exact_excerpt`,
  `blocked_exact`;
- le renderer ne produit un extrait exact que si le texte est deja
  mecaniquement present dans un resultat borne (`context_text` ou
  `page_text`);
- `ambiguous`, `not_found`, `section_alias_missing`,
  `internal_work_unresolved`, `work_alias_missing` et autres manques
  structurels ne doivent pas devenir des sorties pseudo-exactes;
- l'observabilite reste content-free: ids courts, statuts, reason codes,
  compteurs et hashes, jamais prompt brut, payload Catalogue brut ni texte long;
- la voie agent-first construit ce premier objet depuis le tool loop et insere
  le rendu minimal dans la consultation Biblio.

Limite volontaire: Lot 3 commence alors que Lot 2 bis reste ouvert. Le renderer
ne choisit pas une oeuvre, une section, un role ou une ancre ambiguë a la place
du bibliothecaire; il rend la structure disponible ou expose la limite. La
surface finale utilisateur et l'extraction mecanique complete restent a
renforcer dans les lots suivants.

Verrou final Last Chance L3A1 livre:

- invariant: le determinisme ne juge jamais la pertinence semantique d'une
  reponse Biblio; seul le bibliothecaire LLM decide documentairement;
- le determinisme verifie seulement le contrat technique de restitution:
  statut connu, statut/mode coherents, ancre ou position presente pour un
  rendu exact, texte mecanique present quand un extrait exact est rendu,
  hash/longueur concordants, absence de faux extrait, observabilite
  content-free;
- `BiblioFinalResponseLock` autorise ou bloque la surface finale sans lire la
  demande utilisateur ni choisir entre candidats bibliographiques;
- `BiblioChatResult` transporte `BiblioAnswerObject`, `BiblioRenderedAnswer` et
  `BiblioFinalResponseLock`;
- `AssistantResponseOverride` permet au chat de persister et retourner le rendu
  Biblio autorise comme message assistant final, sans appel OpenRouter final;
- la persistance conversationnelle, Memory, Identity et `AssistantText` restent
  executees sur ce message final rendu;
- la separation observable devient: lane Biblio interne, objet resultat
  structure, rendu produit, verrou final, message assistant final;
- si le verrou est bloque ou absent, le chemin LLM ordinaire reste le fallback;
  ce fallback ne doit pas etre raconte comme preuve produit de restitution
  exacte.

Limite volontaire: L3A1 ne corrige pas les erreurs d'ancrage ou de pertinence
documentaire. Il empeche seulement qu'un rendu Biblio deja produit soit ignore,
reformule ou contredit par le LLM final quand le contrat technique est
coherent.

Memoire conversationnelle Last Chance Lot 3 bis livree:

- un extrait Biblio effectivement rendu dans le message assistant final est du
  contenu conversationnel ordinaire;
- Memory ne doit pas l'exclure parce qu'il vient de Biblio;
- les ancres, provenance, statut, mode de rendu, hashes courts et compteurs
  portes par `message.meta` enrichissent cette memoire, mais ne remplacent pas le
  texte rendu;
- `AssistantResponseOverride` persiste le message assistant final en mode
  synchrone et streaming, puis appelle `memory_store.save_new_traces()` sur la
  conversation contenant ce message;
- `memory_traces_summaries._message_is_trace_eligible()` ne filtre pas
  `source=biblio_rendered_answer`: les messages `assistant` non vides, non deja
  `embedded`, et non interrompus restent eligibles;
- la lane Biblio interne, le payload Catalogue et l'observabilite content-free ne
  sont pas promus automatiquement en Memory. Seul le contenu effectivement rendu
  dans le fil suit la politique generale de memoire conversationnelle;
- la rehydratation ulterieure par ancres depuis la bibliotheque est un complement
  de verification/recuperation, pas un substitut obligatoire au texte memorise
  quand la conversation est memorisee.

Premiere methode canonique Last Chance Lot 4A livree:

- famille canonique: `inventory_metadata`;
- methode produit: `product_method=inventory_metadata`, `case_id=""`;
- outils autorises: `catalog_list`, `search_document`, `document_open_summary`;
- anciens P01/P02 restent des regressions historiques et des compatibilites de
  liste catalogue, pas le canon principal de validation;
- le bibliothecaire LLM choisit la methode. Le deterministe ne reconnait pas les
  phrases utilisateur a sa place et ne juge pas la pertinence documentaire;
- le deterministe valide seulement: methode connue, famille canonique,
  allowlist GET-only, params bornes, budgets et observabilite content-free;
- `BiblioAnswerObject.inventory_metadata` porte le resultat structure
  inventaire/metadonnees: documents, total observe, langue, pages et statut
  metadata quand disponibles;
- le renderer produit une surface structuree sans extrait exact; le verrou final
  L3A1 peut l'autoriser parce que le contrat technique est coherent, sans faire
  de jugement semantique;
- l'observabilite expose uniquement compteurs, hashes courts, statuts, ids courts
  et flags de borne. Les titres/auteurs bruts peuvent etre rendus a l'utilisateur
  quand ils sont le resultat produit, mais ne doivent pas fuiter dans les
  artefacts ou logs content-free;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Resolution documentaire canonique Last Chance Lot 4B livree:

- famille canonique: `document_resolution`;
- methode produit: `product_method=document_resolution`, `case_id=""`;
- outils autorises: `search_document`, `search_work`, `resolve_work`,
  `document_open_summary`;
- ancien `work_lookup` / P03 reste une regression historique et une compatibilite
  de transition, pas le canon principal de validation Lot 4;
- `resolve_section`, `section_bounds` et les bornes fines de section restent
  hors Lot 4B et relevent du cran structure/TOC;
- le bibliothecaire LLM choisit la methode. Le deterministe ne reconnait pas les
  phrases utilisateur a sa place et ne juge pas la pertinence bibliographique;
- le deterministe valide seulement: methode connue, famille canonique,
  allowlist GET-only, params bornes, statut technique, non-selection du premier
  candidat ambigu et observabilite content-free;
- `app/biblio/answer_resolution.py` porte la projection/rendu de resolution
  documentaire pour eviter d'empiler toutes les familles dans
  `answer_object.py`;
- `BiblioAnswerObject.document_resolution` porte les statuts `resolved`,
  `ambiguous`, `not_found`, `needs_clarification` ou `error`;
- plusieurs candidats restent ambigus et aucun candidat n'est choisi par le
  renderer. Zero candidat reste `not_found`;
- un candidat de section seulement signale comme travail interne non confirme ne
  devient pas une oeuvre interne resolue; il reste en clarification structurelle;
- le renderer produit une surface structuree sans extrait exact; le verrou final
  L3A1 peut l'autoriser si le contrat technique est coherent;
- l'observabilite expose uniquement compteurs, hashes courts, ids courts, types
  de candidats, statuts et reason codes. Les titres/auteurs bruts peuvent etre
  rendus a l'utilisateur comme resultat produit, mais ne doivent pas fuiter dans
  les artefacts ou logs content-free;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Structure/TOC canonique Last Chance Lot 4C livree:

- famille canonique: `document_structure`;
- methode produit: `product_method=document_structure`, `case_id=""`;
- outils autorises: `search_document`, `resolve_work`, `document_open_summary`,
  `document_toc`, `search_section`, `resolve_section`, `section_bounds`;
- ancien `document_toc_show` / P09 reste une regression historique et une
  compatibilite de transition, pas le canon principal de validation Lot 4;
- `catalog_search` reste hors de la methode canonique structure/TOC. Le chemin
  canonique s'appuie sur les outils documentaires bornes et sur un document ou
  une section resolu/e, pas sur une recherche globale opportuniste;
- le bibliothecaire LLM choisit la methode. Le deterministe ne reconnait pas les
  phrases utilisateur a sa place et ne juge pas la pertinence semantique ou
  bibliographique;
- le deterministe valide seulement: methode connue, famille canonique,
  allowlist GET-only, params bornes, statut technique, non-selection du premier
  candidat ambigu et observabilite content-free;
- `app/biblio/answer_structure.py` porte la projection/rendu structure/TOC pour
  eviter d'empiler toutes les familles dans `answer_object.py`;
- `BiblioAnswerObject.document_structure` porte les statuts `resolved`,
  `ambiguous`, `not_found`, `needs_clarification` ou `error`;
- une TOC, un chapitre ou une section structurelle ne sont pas des extraits
  exacts. La famille `document_structure` rend un `structured_status` et ne
  transforme pas un `context_text` eventuel en `exact_excerpt`;
- plusieurs candidats restent ambigus et aucun candidat n'est choisi par le
  renderer. Zero structure reste `not_found`;
- le renderer produit une surface structuree sans extrait exact; le verrou final
  L3A1 peut l'autoriser si le contrat technique est coherent;
- l'observabilite expose uniquement compteurs, hashes courts, ids courts, roles
  de contenu, statuts de bornes, reason codes et flags de borne. Les titres de
  chapitres/sections peuvent etre rendus a l'utilisateur comme resultat produit,
  mais ne doivent pas fuiter dans les artefacts ou logs content-free;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Recherche scoped canonique Last Chance Lot 4D livree:

- famille canonique: `scoped_search`;
- methode produit: `product_method=scoped_search`, `case_id=""`;
- outils autorises: `search_document`, `search_work`, `search_section`,
  `resolve_work`, `resolve_section`, `section_bounds`, `catalog_search`;
- anciens P05-P08/P16-P18 restent des regressions historiques et des
  compatibilites de transition `passage_search_in_work` /
  `passage_search_external_work`, pas le canon principal de validation Lot 4D;
- `catalog_search` reste une recherche plein texte globale cote API Catalogue.
  Elle ne devient recherche scoped que si un `document_id` est explicite ou
  porte depuis une resolution documentaire unique. Le runtime bloque une
  recherche scoped sans scope unique et filtre techniquement les hits par
  `document_id`;
- le bibliothecaire LLM choisit le sens, le theme et le scope documentaire. Le
  deterministe ne juge jamais la pertinence intellectuelle d'un hit; il valide
  seulement la methode, l'allowlist GET-only, les params bornes, le scope unique,
  le filtrage technique et l'observabilite content-free;
- `app/biblio/answer_search.py` porte la projection/rendu recherche scoped pour
  eviter d'empiler toutes les familles dans `answer_object.py`;
- `BiblioAnswerObject.scoped_search` porte les statuts `resolved`, `ambiguous`,
  `not_found`, `needs_clarification` ou `error`, ainsi que scope, compteurs,
  candidats bornes, hits filtres hors scope et reason codes;
- quand `catalog_search` a ete tente dans un scope documentaire unique et
  qu'aucun candidat ne reste dans ce scope, le statut mecanique est `not_found`
  avec `scoped_search_no_hits_in_scope`, pas `needs_clarification`;
- le renderer expose le reason code produit effectif du bloc canonique actif:
  un `not_found` scoped ne doit pas etre rendu avec `Reason: ok`;
- recherche scoped canonique n'est pas extraction exacte. La methode
  `product_method=scoped_search` rend un `structured_status`; elle ne transforme
  pas `context_text`, `page_text` ou un hit de recherche en `exact_excerpt`. Les
  anciens P05-P08/P16-P18 peuvent encore produire un contexte borne comme
  compatibilite legacy jusqu'a leur migration extraction;
- plusieurs documents possibles avant recherche restent ambigus ou demandent
  clarification. Plusieurs hits dans un scope resolu restent des candidats de
  recherche et ne sont pas presentes comme le passage exact;
- `passage_context`, `page_read` et `locate` restent hors Lot 4D canonique et
  relevent de l'extraction, de la navigation ou des references canoniques;
- l'observabilite expose uniquement compteurs, hashes courts, ids courts,
  statuts, reason codes et flags de borne. Les snippets bornes peuvent etre
  rendus a l'utilisateur comme surface de recherche scoped, mais pas fuiter dans
  les artefacts/logs content-free;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Extraction mecanique canonique Last Chance Lot 4E livree:

- famille canonique: `extraction`;
- methode produit: `product_method=extraction`, `case_id=""`;
- outils autorises: `search_document`, `search_work`, `search_section`,
  `resolve_work`, `resolve_section`, `section_bounds`, `catalog_search`,
  `locate`, `page_read`, `passage_context`;
- P04 `passage_extract_canonical_range` reste legacy/regression historique pour
  les plages canoniques; il n'est plus le canon principal de validation Lot 4E;
- `catalog_search` peut preparer un candidat ancre dans un scope documentaire,
  mais ses snippets restent hors extraction exacte. Une recherche produit des
  candidats; elle ne produit pas le texte exact;
- exact text = texte mecanique fourni par `page_read` ou `passage_context`,
  avec `document_id` et ancre technique minimale (`page_no` ou `paragraph_id`).
  Sans texte mecanique ou sans ancre, le rendu exact est bloque avec un reason
  code content-free (`extraction_mechanical_text_missing`,
  `extraction_anchor_missing` ou `extraction_source_tool_unsupported`);
- `app/biblio/answer_extraction.py` porte la projection/rendu extraction pour
  eviter d'empiler toutes les familles dans `answer_object.py`;
- `BiblioAnswerObject.extraction` porte statut, outil source, document court,
  type de texte, ancre, compteurs/hash du texte exact, reason codes et limites;
- le bibliothecaire LLM choisit le sens, le document, la reference, la page ou
  les ancres candidates. Le deterministe ne juge jamais la pertinence
  semantique du passage: il valide seulement la methode, l'outil GET-only, les
  params bornes, la coherence document/ancre, la presence du texte mecanique et
  l'observabilite content-free;
- le runtime peut completer mecaniquement une position deja portee vers
  `passage_context`, mais il ne lance pas de recherche globale opportuniste pour
  fabriquer une extraction canonique;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Extraction mecanique bornee Last Chance Lot 4E.1 livree:

- la methode canonique reste `product_method=extraction`, `case_id=""`;
- page unique: `page_read(document_id, page_no)` peut rendre exact si le texte,
  le document et l'ancre page sont coherents;
- intervalle court: 2 ou 3 appels `page_read` peuvent etre assembles
  mecaniquement, en ordre documentaire, si les pages sont consecutives et dans
  le meme document;
- une resolution documentaire unique (`search_document`, `resolve_work` ou
  equivalent autorise) peut porter le `document_id` vers `page_read` quand le
  bibliothecaire demande une page ou une courte plage explicite. Si un
  `page_read` subsequent contient un `document_id` contradictoire alors qu'une
  ancre documentaire unique est deja portee, le planner utilise l'ancre portee
  pour maintenir la coherence technique; il ne choisit pas un document
  semantiquement, il applique le scope deja resolu;
- budget actuel: 1 a 3 pages, 8 000 caracteres exacts assembles. Les warnings
  ou refus sont content-free;
- reason codes bloquants:
  `extraction_page_range_too_long`, `extraction_page_range_incomplete`,
  `extraction_document_mismatch`, `extraction_mixed_block_types_unsupported`,
  `budget_or_limit_exceeded`;
- un intervalle non lu n'est pas un extrait. Le systeme ne fabrique pas une page
  manquante et ne transforme pas une recherche, un snippet, une TOC ou un titre
  de chapitre en texte exact;
- `BiblioAnswerObject.extraction` expose les blocs mecaniques sans texte brut:
  `block_count`, `page_start`, `page_end`, `page_count`, `missing_pages`, hashes
  courts, compteur de caracteres, outil source, statut et reason codes;
- `BiblioAnswerObject.anchors` expose une ancre globale par bloc rendu pour les
  extractions resolues, au minimum `document_id` + `page_no` pour les pages. Les
  cas bloques ne doivent pas presenter une couverture globale partielle comme
  valide;
- le bibliothecaire LLM decide les bornes documentaires. Le deterministe assemble
  seulement les blocs effectivement lus et verifies; il ne devine pas une borne
  ambigue et ne juge jamais la pertinence semantique;
- continuation: pas de navigation lecteur globale dans ce lot. Une continuation
  est seulement un nouvel appel `page_read` explicite par le bibliothecaire, ou
  relevera d'un futur etat/ancrage fiable;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Extraction depuis bornes de section Last Chance Lot 4E.2 livree:

- la methode canonique reste `product_method=extraction`, `case_id=""`;
- `section_bounds` peut servir de pont vers une extraction exacte seulement
  quand le bibliothecaire a explicitement choisi un `answer_mode` compact de
  debut de section, par exemple `section_start_page_block_2`;
- `section_bounds` seul est une preuve de structure/bornes, pas une lecture:
  il ne rend jamais de texte exact sans `page_read` effectivement execute;
- si les bornes de section portent une page de debut exploitable, le runtime
  peut lire mecaniquement deux pages de debut, ou moins si la borne de fin connue
  indique une section plus courte;
- le rendu exact reste soumis au contrat Lot 4E.1: blocs effectivement lus,
  meme `document_id`, intervalle contigu, budget 1 a 3 pages / 8 000 caracteres,
  ancres globales couvrantes et hash/longueur coherents;
- ambiguite, absence de document, absence de page exploitable ou bornes non-page
  bloquent/clarifient. Le deterministe ne choisit pas une section, n'invente pas
  une borne et ne juge jamais la pertinence semantique;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Extraction depuis candidat de recherche ancre Last Chance Lot 4E.3 livree:

- la methode canonique reste `product_method=extraction`, `case_id=""`;
- `catalog_search` est accepte comme outil precurseur uniquement pour localiser
  un candidat ancre dans un scope documentaire explicite ou porte;
- le runtime peut appeler `passage_context` seulement si le resultat de
  recherche est document-scoped, contient exactement un seul hit scoped total
  apres filtrage, et que ce hit unique porte `paragraph_id` ou `page_no` +
  `para_no`;
- plusieurs candidats scoped, zero candidat, candidat unique sans ancre,
  candidat sans `document_id`, recherche globale non scopee ou document
  incoherent bloquent l'extraction exacte. Aucun premier hit n'est choisi
  silencieusement, meme si un seul des candidats scoped est ancre;
- le texte exact rendu vient uniquement du `context_text` retourne par
  `passage_context`. Le snippet de `catalog_search` ne devient jamais
  `exact_excerpt`;
- `scoped_search` reste une surface de recherche structuree et ne declenche pas
  automatiquement une extraction;
- le deterministe ne juge pas le sens du hit: il verifie seulement scope,
  unicite, ancre, outil GET-only, coherence technique et observabilite
  content-free;
- preuve actuelle: unitaires contractuels seulement, pas smoke live agentique.

Correction transition agentique live 4E:

- les familles canoniques live doivent etre exposees au bibliothecaire comme
  `product_method=scoped_search` ou `product_method=extraction`, avec
  `case_id=""`;
- P05-P08/P16-P18 restent legacy/regression et ne doivent pas absorber les
  demandes canoniques de recherche scoped ou d'extraction;
- une extraction de page ou plage courte peut porter le `document_id` depuis une
  resolution documentaire unique vers `page_read`; les bornes numeriques
  explicites restent limitees par budget;
- un plan legacy avec `answer_mode=scoped_search` ne complete pas vers
  `passage_context`: il reste une surface structuree de recherche, pas un
  extrait exact.

## 3. Frontieres non negociables

Biblio n'est pas `active_document`.

- Un `active_document` est temporaire, conversation-scoped, fourni ou selectionne par l'utilisateur, puis injecte entier ou exclu entier par tour.
- Un `catalogue_document` est durable, hors conversation, consulte ponctuellement.
- Un `passage documentaire` extrait depuis Catalogue ne devient pas automatiquement `active_document`.

Biblio n'est pas workspace.

- Le workspace organise des fichiers persistants a portee de main.
- Biblio designe un fonds/catalogue durable consulte via l'API Catalogue.
- Un `workspace_file` selectionne peut suivre la lane `active_document`; il ne devient pas `catalogue_document`.

Biblio n'est pas Memory/RAG.

- Biblio ne cree pas d'embedding FridaDev par defaut.
- Biblio ne promeut pas les passages dans Memory/RAG.
- Biblio ne remplace pas les traces memoire, les summaries parents ou l'arbitre memoire.

Biblio n'est pas Summary.

- Une consultation Catalogue ne modifie pas le resume de conversation par elle-meme.
- Un passage repris dans une reponse peut ensuite appartenir au dialogue ordinaire, et seulement par ce chemin.

Biblio n'est pas Identity.

- Une consultation d'ouvrage ne cree pas d'enonce identitaire.
- Le juge mutable ne doit pas lire des passages de Biblio comme source identitaire directe.

Biblio n'est pas Web.

- Catalogue est une source locale/persistante deja ingeree.
- Web search decouvre ou lit des sources web; Biblio consulte un fonds Catalogue.

Biblio n'est pas Hermeneutic.

- Hermeneutic juge le tour et la posture.
- Biblio fournit eventuellement un passage documentaire borne dans une lane dediee.

Biblio n'est pas AnythingLLM.

- AnythingLLM n'est pas requis dans le chemin nominal.
- Les precedents OpenWebUI/AnythingLLM peuvent inspirer, mais ne deviennent pas dependance cible.

OCR des documents actifs ne cree pas de Biblio.

- L'OCR ponctuel des `active_document` via Stirling reste conversation-scoped.
- Il ne cree ni `library_document`, ni `catalogue_document`, ni `passage documentaire`.

Un passage extrait ne devient pas automatiquement durable.

- Le passage peut etre utilise dans la reponse du tour.
- Une fois repris dans la reponse, il devient seulement matiere conversationnelle ordinaire.
- Il ne devient pas memoire documentaire durable, document actif, workspace file ou entree Identity.

## 4. Toggle frontend

Le Lot 7 ajoute un bouton/toggle Biblio dans le frontend chat, au meme niveau conceptuel que les autres outils explicites.

Invariant `Biblio off`:

- aucune consultation Catalogue;
- aucun appel client Biblio;
- aucune lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`;
- aucune tentative de resolver documentaire;
- observabilite `biblio_enabled=false`, `biblio_used=false`.

Invariant `Biblio on`:

- Frida peut consulter Catalogue si la demande appelle une consultation d'ouvrage;
- le toggle autorise seulement une consultation bornee;
- le toggle n'injecte jamais toute la bibliotheque;
- le toggle ne transforme pas Catalogue en contexte permanent;
- l'observabilite indique si Biblio a ete utilisee ou non.

Implementation Lot 7 du 2026-05-29:

- bouton frontend: `btnBiblioMode`, classe `btn-biblio-mode`, icone livre, place dans la rangee des outils bas juste apres le mode Adobe;
- payload chat: `biblio_enabled: true|false`, transmis explicitement a chaque envoi;
- etat visuel: meme taille, classes `active`, `aria-pressed`, tooltip et rythme que les autres boutons de composer;
- le toggle ne cree aucun document actif, ne modifie pas Memory/RAG, Identity, Summary, workspace ou Web;
- le toggle autorise seulement le chemin Biblio minimal du tour courant.

## 5. Source de verite

La source nominale de Biblio est l'API Catalogue / doc-pipeline.

Priorite metadonnees:

1. `human metadata` validee ou corrigee humainement;
2. `source metadata` d'ingestion Catalogue;
3. `source_filename` seulement comme trace operateur ou fallback affiche, jamais comme titre canonique s'il existe mieux.

Regles:

- le titre canonique humain prime sur le titre auto;
- le titre auto reste utile comme trace d'ingestion;
- `source_filename` ne doit jamais etre presente comme titre bibliographique fiable;
- le statut metadata (`to_review`, `corrected`, `validated`) doit influencer la confiance future;
- FridaDev ne recopie pas Catalogue comme nouvelle source de verite;
- FridaDev ne backfill pas Catalogue;
- AnythingLLM n'est pas requis dans le chemin nominal.

## 6. Contrat client FridaDev futur

Le premier client Catalogue FridaDev doit etre GET-only.

Endpoints autorises au depart:

- `GET /health`;
- `GET /catalog`;
- `GET /doc/{id}`;
- `GET /doc/{id}/metadata`;
- `GET /doc/{id}/chapters`;
- `GET /search/chapters`;
- `GET /doc/{id}/page/{page_no}`;
- `GET /doc/{id}/locate`;
- `GET /doc/{id}/context`;
- `GET /search`.

Endpoints interdits au client FridaDev initial:

- `DELETE /doc/{id}`;
- `DELETE /doc/{id}/with-files`;
- `PUT /doc/{id}/metadata`;
- `PUT /settings`;
- `POST /settings/reset`;
- `POST /progress/recent/clear`.

Le client futur doit:

- avoir des timeouts explicites;
- gerer Catalogue indisponible sans faire echouer tout le chat si la demande peut etre traitee sans Biblio;
- retourner des erreurs structurees et content-free;
- journaliser seulement endpoint logique, statut, duree, doc id court/hash court, statut de resolution et reason codes;
- ne jamais afficher ni stocker secret, DSN, cookie, texte OCR brut, ouvrage brut, passage complet ou prompt complet dans les logs ordinaires;
- n'ecrire aucune donnee dans Catalogue;
- ne supprimer aucun document;
- ne lancer aucun OCR;
- ne lancer aucun backfill.

Implementation Lot 2 du 2026-05-28:

- module: `app/biblio/catalogue_client.py`;
- package domaine: `app/biblio/`;
- config non secrete: `BIBLIO_CATALOGUE_BASE_URL`, defaut `http://platform-doc-pipeline-api:8090`;
- timeout non secret: `BIBLIO_CATALOGUE_TIMEOUT_S`, defaut `8`;
- methodes publiques: `health()`, `catalog()`, `document()`, `metadata()`, `chapters()`, `search_chapters()`, `page()`, `locate()`, `context()`, `search()`;
- garde structurelle: `_request()` refuse tout verbe autre que `GET`;
- allowlist structurelle: seuls `/health`, `/catalog`, `/search`, `/search/chapters`, `/doc/{id}`, `/doc/{id}/metadata`, `/doc/{id}/chapters`, `/doc/{id}/page/{page_no}`, `/doc/{id}/locate`, `/doc/{id}/context` sont acceptes;
- routes mutatrices et exports non allowlistes sont refuses avant appel reseau;
- erreurs content-free: forbidden method, forbidden route, invalid base URL, invalid parameter, service unavailable, timeout, invalid JSON, not found, unexpected status;
- `CatalogueResponse.to_observability()` exclut le payload brut et expose seulement endpoint, status, duree, compte, id court et longueur compacte si applicable.

Correctif oeuvre interne Lot E du 2026-06-03:

- une petite demande TOC deja mappee de forme `Sommaire du Theetete de
  Platon` peut rester cote FridaDev: le planner separe `work_title` et
  `document_title`, puis la runtime TOC consulte le volume unique et renvoie
  seulement les entrees TOC correspondantes a l'oeuvre interne quand elles
  existent;
- cette focalisation reste un repere structurel dans la TOC du volume; elle
  ne doit pas etre racontee comme une table des matieres autonome et complete
  de l'oeuvre interne;
- la comprehension plus libre des formulations naturelles reste hors de portee
  du deterministe et doit revenir au bibliothecaire agentique, pas a une
  accumulation de variantes locales.

Correctif generique section interne -> deux pages du 2026-06-03:

- quand un volume/corpus est deja resolu et qu'une demande vise le debut d'une
  section interne sans locator canonique, FridaDev peut maintenant utiliser
  `GET /search/chapters` comme repere structurel de debut, puis enchainer
  `GET /doc/{id}/page/{page_no}` sur `page_start` et `page_start + 1`;
- ce chemin reste documentaire et borne: il n'invente ni nouvel objet
  canonique general, ni pseudo-resolution semantique forte;
- s'il existe ensuite une limite de restitution de surface dans le chat, elle
  doit etre traitee comme limite de surface distincte, pas comme faux
  probleme de droits.

Correctif Lot 2 du 2026-05-28:

- les parametres numeriques publics sont valides avant appel reseau;
- les erreurs de parametre utilisent `biblio_catalogue_invalid_parameter`;
- aucune valeur brute utilisateur n'est exposee dans l'erreur ou l'observabilite;
- aucune troncature silencieuse n'est autorisee: seuls les `int` Python et les chaines d'entiers decimales propres sont acceptes;
- bornes alignees sur Catalogue quand l'API les declare:
  - `catalog.limit`: `1..500`;
  - `chapters.limit`: `1..1000`;
  - `locate.limit`: `1..1000`;
  - `context.window_chars`: `80..8000`;
  - `search.limit`: `1..100`;
  - `search_chapters.limit`: `1..100`;
- bornes client conservatrices quand l'API ne declare pas de maximum:
  - `catalog.offset`: `0..100000`;
  - `chapters.offset`: `0..100000`;
  - `context.char_offset`: `0..1000000`;
  - `context.page_no`: `1..100000`;
  - `context.para_no`: `1..100000`;
  - `context.paragraph_id`: `1..2147483647`.

Le Lot 2 ne branche toujours pas:

- chat;
- frontend;
- toggle Biblio;
- lane prompt;
- route API FridaDev;
- DB FridaDev;
- Memory/RAG;
- Identity;
- Summary;
- OCR.

## 7. Resolver documentaire

Le resolver Lot 3 retourne toujours un statut:

- `resolved`;
- `ambiguous`;
- `not_found`;
- `invalid_request`;
- `catalogue_unavailable`.

Regles:

- ne jamais presenter une resolution incertaine comme certaine;
- toujours distinguer document, corpus, edition, dialogue et locator si les metadonnees l'exigent;
- exposer les raisons d'ambiguite sans texte brut long;
- utiliser `human metadata` comme signal prioritaire quand disponible;
- conserver le `source_filename` comme trace, pas comme preuve bibliographique;
- traiter les milestones Stephanus comme aide, pas comme preuve suffisante.

Implementation Lot 3 du 2026-05-28:

- module: `app/biblio/document_resolver.py`;
- classes structurantes: `BiblioResolveRequest`, `BiblioResolutionResult`, `DocumentCandidate`, `LocatorCandidate`, `BiblioDocumentResolver`;
- le resolver utilise seulement le client Catalogue GET-only;
- il peut appeler `catalog()`, `document()`, `metadata()` et `locate()`;
- il n'appelle pas `context()` et n'extrait aucun passage;
- il ne branche pas chat, prompt, frontend, toggle, DB, Memory/RAG, Identity, Summary, Web, workspace ou OCR;
- il retourne des raisons content-free comme `locator_requires_document`, `ambiguous_document`, `ambiguous_locator`, `document_not_found`, `locator_not_found`, `catalogue_unavailable`;
- `to_observability()` expose status, reason, ids courts et compteurs de candidats, jamais de payload Catalogue brut ni de texte OCR;
- les locators demandes et resolus ne sortent pas en clair dans l'observabilite: seuls presence, longueur et hash court stable sont exposes;
- `locator_kind` est expose seulement comme valeur connue (`stephanus`, `page`, `paragraph`, `chapter`, `milestone`) ou `custom`;
- titres, auteurs, titre canonique, label de locator, texte OCR, passage, payload Catalogue et requete utilisateur brute restent hors observabilite.

Cas Platon / Stephanus:

- `126b -> 126e` doit etre un cas de test;
- `126b` seul retourne `invalid_request` / `locator_requires_document`;
- `Platon 126b` peut rester `ambiguous` si plusieurs documents ou editions correspondent;
- si le dialogue cible n'est pas determine, le resultat doit etre `ambiguous`;
- si plusieurs occurrences ou editions restent plausibles, le resultat doit etre `ambiguous`;
- si aucun locator compatible n'est trouve, le resultat doit etre `not_found`;
- si Catalogue echoue, le resultat doit etre `catalogue_unavailable`.

## 8. Extraction bornee

Un passage documentaire extrait doit etre borne.

Champs minimum futurs:

- doc ref;
- doc id court ou hash court;
- titre via `human metadata` si acceptable;
- locator demande;
- locator resolu;
- statut;
- confidence;
- longueur chars;
- hash court du passage;
- reason codes;
- erreurs compactes.

Limites a fixer dans un lot futur:

- limite chars;
- limite tokens;
- comportement si passage trop long;
- politique de citation ou d'affichage utilisateur.

Regles:

- pas de texte brut dans les logs ordinaires;
- pas de contenu d'ouvrage brut dans le dashboard ordinaire;
- pas de stockage comme `active_document`;
- pas de troncature silencieuse sans reason code;
- pas de promesse que tout l'ouvrage a ete lu.

Implementation Lot 4 du 2026-05-28, completee par le correctif bibliothecaire du 2026-05-30:

- module: `app/biblio/passage_extractor.py`;
- l'extracteur utilise le resolver Lot 3 et le client Catalogue GET-only;
- il peut appeler `context()` pour un passage simple ou un range borne sur une
  meme page, et `page()` pour un range borne multi-page quand les deux ancres
  resolues portent des positions `page_no` / `para_no` coherentes;
- en sortie, l'extraction exacte peut exposer un `interval_hint` content-free
  borne (`kind`, `mode`, ancres start/end non textuelles, spans calcules) afin
  de reutiliser proprement le range dans l'etat et la navigation, sans
  pretendre a un objet canonique general d'intervalle;
- dans l'etat courant, `continue apres ce passage` peut reutiliser l'ancre de
  fin d'un `interval_hint` via `passage_context` quand `end_page_no` /
  `end_para_no` ou `end_paragraph_id` sont connus; `page suivante` reste un
  geste page-granulaire sur `page_read`;
- il refuse toute extraction si la resolution est `ambiguous`, `not_found`, `invalid_request` ou `catalogue_unavailable`;
- il exige un locator resolu avec cible contextuelle non ambigue: `paragraph_id` ou couple `page_no` / `para_no`;
- il refuse les ranges non bornes ou incoherents avec `range_extraction_not_supported`;
- il peut extraire un range borne quand le document et les deux locators sont
  resolus sans ambiguite apres ancrage, avec au plus
  `MAX_RANGE_PARAGRAPHS = 40` paragraphes, au plus `MAX_RANGE_PAGES = 12`
  pages, et une taille finale autorisee;
- il ne choisit jamais le premier passage d'un locator ambigu;
- bornes initiales:
  - `window_chars`: `80..2000`;
  - `max_passage_chars`: `80..4000` par defaut, jusqu'a `8000` pour une extraction range explicitement bornee par le runtime bibliothecaire;
  - `char_offset`: `0..1000000`;
- seuls les entiers stricts ou chaines d'entiers decimales propres sont acceptes pour les options numeriques;
- reponse Catalogue incoherente, passage vide, introuvable, trop long ou indisponibilite Catalogue produisent des statuts explicites;
- le payload `/context` doit porter un `document_id` identique au document resolu, sinon l'extraction retourne `incoherent_catalogue` sans conserver le passage;
- l'objet metier peut contenir le passage brut en interne uniquement quand `status=extracted`;
- `to_observability()` n'expose jamais passage brut, texte OCR, payload Catalogue, locator brut, titre, auteur ou requete utilisateur brute;
- l'observabilite expose seulement status, reason code, resolution content-free, ids courts, longueurs, hash court stable, bornes appliquees et positions non textuelles.

## 9. Lane prompt

Nom stable:

```text
[PASSAGES DE BIBLIOTHEQUE CONSULTES]
```

La lane doit etre distincte de:

- documents actifs;
- Memory/RAG;
- Summary;
- Identity;
- Web;
- Hermeneutic.

Instruction modele minimale:

```text
Les passages ci-dessous proviennent d'une bibliotheque persistante consultee a la demande.
Ils ne prouvent pas que tout l'ouvrage ou tout le corpus a ete lu.
Respecte le statut de resolution, les limites et les ambiguites.
Ne confonds pas ces passages avec les documents actifs, la memoire, le web, l'identite ou le resume.
```

Implementation Lot 5 du 2026-05-29:

- module: `app/biblio/prompt_lane.py`;
- entree unique: une sequence de `BiblioPassageResult` deja produits par l'extracteur Lot 4;
- aucun appel Catalogue, resolver, extracteur, chat, frontend, route API, DB, Memory/RAG, Identity, Summary, Web, workspace ou OCR;
- seuls les resultats `status=extracted` avec passage brut present peuvent produire du texte dans la lane;
- les statuts non extraits (`ambiguous`, `not_found`, `invalid_request`, `catalogue_unavailable`, `empty`, `too_long`, `incoherent_catalogue`, etc.) sont ignores par la lane texte et traces seulement par decisions content-free;
- si aucun passage extrait n'est injecte, aucun message de lane n'est produit;
- bornes initiales:
  - `DEFAULT_MAX_PASSAGES = 3`;
  - `DEFAULT_MAX_TOTAL_CHARS = 8000`, calcule sur tout le bloc lane, balises et contrat inclus;
  - `MAX_MAX_PASSAGES = 10`;
  - `MAX_MAX_TOTAL_CHARS = 50000`;
- depassement du nombre de passages: passage ignore avec `biblio_prompt_max_passages_reached`;
- depassement de taille totale: passage ignore avec `biblio_prompt_max_total_chars_reached`, sans troncature silencieuse;
- passage extrait vide: passage ignore avec `biblio_prompt_empty_passage`;
- format source: `catalogue_doc=<doc_id_short>` puis positions non textuelles disponibles (`page`, `paragraphe`, `paragraph_id`);
- pas d'invention de titre, auteur, edition, filename source ou locator textuel;
- le passage brut existe uniquement dans le `message["content"]` produit par la lane;
- les balises `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` et `[/PASSAGES DE BIBLIOTHEQUE CONSULTES]` presentes dans un passage sont neutralisees uniquement dans le texte injecte, sans modifier le `BiblioPassageResult` interne;
- `BiblioPromptLane.message` est exclu du `repr` pour reduire le risque de fuite accidentelle;
- `to_observability()` n'expose jamais passage brut, texte OCR, payload Catalogue, locator brut, titre, auteur, requete utilisateur brute ou prompt complet;
- l'observabilite ne fait pas confiance a un `passage_hash` arbitraire: si le passage brut existe, le hash court est recalcule depuis ce passage; sinon seul un hash court strictement hexadecimal de 12 caracteres peut etre repris;
- observabilite lane: presence, `passage_count`, `skipped_count`, `chars`, bornes appliquees, hashes courts, doc ids courts, positions non textuelles et decisions content-free.

Format Lot 5:

```text
[PASSAGES DE BIBLIOTHEQUE CONSULTES]
Contrat d'interpretation:
- Les passages ci-dessous proviennent d'une bibliotheque persistante consultee a la demande.
- Ils ne prouvent pas que tout l'ouvrage ou tout le corpus a ete lu.
- Respecte le statut de resolution, les limites et les ambiguites.
- Ne confonds pas ces passages avec les documents actifs, la memoire, le web, l'identite ou le resume.
Passage 1
Source: catalogue_doc=<doc_id_short>, page=<page_no>, paragraphe=<para_no>, paragraph_id=<paragraph_id>
Texte:
<passage borne>
[/PASSAGES DE BIBLIOTHEQUE CONSULTES]
```

Le Lot 5 ne branche pas encore cette lane dans le chat principal. Le modele ne la recoit que si un lot futur l'insere explicitement dans le prompt du tour.

## 10. Observabilite

Observabilite content-free par defaut:

- `biblio_enabled`;
- `biblio_used`;
- query kind;
- endpoint logique;
- document `resolved` / `ambiguous` / `not_found` / `error`;
- doc id court ou hash court;
- metadata status compact si disponible;
- locator demande sous forme presence/longueur/hash/kind seulement;
- locator resolu sous forme positions non textuelles et kind seulement;
- passage chars;
- passage hash court;
- confidence;
- reason codes;
- erreurs compactes;
- duree appel Catalogue;
- timeout ou retry si applicable.

Ne pas logguer par defaut:

- texte OCR brut;
- passage complet;
- contenu d'ouvrage brut;
- prompt complet;
- secret;
- DSN;
- cookie;
- header d'authentification;
- full document id si un id court suffit;
- source filename si le nom revele une information sensible et qu'un label compact suffit.

Le dashboard ordinaire doit rester content-free. Toute vue future affichant un passage complet devra etre une surface explicite, bornee et documentee separement.

Implementation Lot 6 du 2026-05-29:

- module: `app/biblio/observability.py`;
- surface admin read-only: `GET /api/admin/biblio/observability`;
- la route admin n'appelle pas Catalogue, ne resout aucun document, n'extrait aucun passage, ne construit aucune lane prompt et n'ecrit rien en DB;
- la route expose seulement l'etat du module, la config non secrete utile (`catalogue_base_url` expurgee de userinfo, query et fragment; timeout; GET-only), les endpoints GET autorises et les mutations interdites;
- `build_biblio_event_payload()` projette des objets deja produits par les lots 2 a 5 en event compact: `enabled`, `used`, `query_kind`, status, client, resolver, extractor, lane, counts, confidence non disponible, reason codes, frontieres et redaction;
- `emit_biblio_event()` reserve le stage compact `biblio`, mais le Lot 6 ne le branche pas au chat principal;
- l'observabilite Biblio ne serialise jamais `BiblioPromptLane.message`;
- les projections recalculent ou valident strictement les hashes de passage observables et compactent les textes inconnus en longueur/hash court au lieu de les exposer;
- les payloads bruts Catalogue, passage brut, texte OCR, prompt complet, titre, auteur, requete ou locator brut, secret, cookie, token, DSN et `.env` restent hors projection;
- le catalogue observable dashboard declare le module `biblio`, ses metriques compactes, ses raisons de degradation et sa traduction d'inspection;
- le read-model de tour reconnait des events `stage=biblio` s'ils existent deja, sans creer d'event ni declencher Catalogue;
- la Biblio reste separee des documents actifs, workspace, Memory/RAG, Identity, Summary, Web, Hermeneutic, AnythingLLM et OCR des documents actifs.

Correctif post-audit Lot 6 du 2026-05-29:

- la projection materialisee `observability.dashboard_turn_facts` porte une colonne `biblio_json JSONB NOT NULL DEFAULT '{}'::jsonb`;
- le schema runtime ajoute cette colonne par `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` pour les DB existantes;
- `dashboard_analytics_storage.py` persiste et relit `fact["biblio"]`;
- `dashboard_read_model.py` relit `biblio_json` au lieu de remettre `biblio` a `{}`;
- le contenu de `biblio_json` reste la projection compacte content-free deja expurgee; aucune donnee Biblio metier brute n'est ajoutee a la persistence dashboard.

Implementation Lot 7 du 2026-05-29:

- module runtime: `app/biblio/chat_runtime.py`;
- le chat appelle Biblio seulement si `biblio_enabled=true`;
- si le toggle est off, l'event `stage=biblio` expose `enabled=false`, `used=false`, `status=not_applicable`, sans construire de client Catalogue;
- si le toggle est on mais que le message ne contient pas de signal bibliographique clair, l'event expose `enabled=true`, `used=false`, `status=not_used`, sans construire de client Catalogue;
- la detection minimale accepte uniquement des signaux conservateurs: document/titre/id explicite, `dans la bibliotheque`, `dans le catalogue`, `cherche dans ...`, ou locator Stephanus associe a un document/titre;
- les demandes Adobe/Photoshop/Illustrator sans signal Biblio explicite sont ignorees par Biblio;
- si le signal est clair, `BiblioPassageExtractor` est appele, puis `build_biblio_prompt_lane()` formate les passages extraits;
- la lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` est injectee dans le prompt principal seulement si un passage `status=extracted` existe;
- l'event `stage=biblio` utilise uniquement `build_biblio_event_payload()` et ne serialise jamais `BiblioPromptLane.message`;
- la surface admin `GET /api/admin/biblio/observability` indique maintenant `chat_wired=true`, `frontend_wired=true`, `toggle_wired=true`, tout en conservant `automatic_catalogue_call=false` et `db_write=false`.

Correctif bibliothecaire du 2026-05-30:

- nouveaux modules applicatifs: `app/biblio/query_planner.py`, `app/biblio/work_resolver.py`, `app/biblio/library_runtime.py`;
- `chat_runtime.py` redevient une orchestration mince: toggle, plan structure, client GET-only, runtime bibliothecaire, observabilite et injection prompt;
- le planner reconnait les intentions `list_catalog`, `search_catalog`, `resolve_work`, `extract_passage`, `extract_range` et `clarify_ambiguous`;
- quand `biblio_enabled=true`, les demandes naturelles comme `voir les premiers ouvrages`, `cherche Theetete`, `extrait du Theetete de Platon`, `Theetete 126b a 128a` ne tombent plus en faux `no_signal`;
- `work_resolver.py` distingue document physique Catalogue, oeuvre interne, locator et range; quand un document physique unique est deja resolu, il consulte d'abord `GET /doc/{id}/chapters` comme hint structurel d'oeuvre interne avec un matching normalise par mots/phrase;
- `GET /doc/{id}/chapters` peut maintenant porter le meme signal faible negatif `document_role_signal` que `/search` et `/search/chapters`, derive du couple `document_title` / `title`;
- quand aucun document physique unique n'est encore resolu mais qu'une oeuvre interne est explicitement demandee, il peut maintenant consulter `GET /search/chapters` comme support structural leger a l'echelle du catalogue avant de retomber sur `/search` de paragraphes;
- `GET /search/chapters` ne remplace pas la recherche plein texte de paragraphes pour les locators/ranges: si une ancre documentaire interne reste necessaire, `/search` continue de fournir cette ancre content-free;
- `GET /search/chapters` doit rester un support structural honnete: le fallback permissif par simple sous-chaine accidentelle n'est pas autorise pour "resoudre" une oeuvre interne;
- cote FridaDev, un `document_id` unique issu de `search/chapters` n'est accepte que si le titre de chapitre matche la requete de facon defendable; sinon le resolver retombe sur le chemin suivant au lieu d'inventer une resolution;
- `GET /search/chapters` peut maintenant porter le meme signal faible negatif `document_role_signal` que `/search`, derive du couple `document_title` / `chapter_title`;
- ce signal reste faible et negatif uniquement: FridaDev peut l'utiliser pour refuser qu'un hit de type `introduction`, `notice` ou `commentary` engage a lui seul une resolution d'oeuvre interne, mais jamais pour prouver positivement qu'un hit est le texte primaire;
- la meme regle vaut maintenant pour `GET /doc/{id}/chapters`: un chapitre deja situe dans un document physique unique mais marque `introduction`, `notice` ou `commentary` ne suffit pas a lui seul a "resoudre" l'oeuvre interne;
- le resolver accepte des ancres non textuelles `locator_anchor_page` / `locator_anchor_para` pour choisir un locator parmi plusieurs candidats sans exposer le titre, l'oeuvre ou la requete en observabilite;
- le chemin document-id utilise `/metadata` plutot que le payload lourd `/doc/{id}` pour eviter de tirer inutilement l'overview complet;
- `library_runtime.py` peut produire une lane de consultation `[CONSULTATION DE BIBLIOTHEQUE]` pour liste, recherche, candidat ou statut non extrait; cette lane peut contenir des titres Catalogue dans le prompt produit, mais elle n'est jamais serialisee en observabilite;
- les passages bruts restent limites a `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` quand `BiblioPassageResult.status=extracted`;
- si Catalogue est joignable et la demande est bibliographique, le systeme doit consulter ou produire une ambiguite/statut explicite; il ne doit pas repondre comme si aucune bibliotheque n'etait accessible.
- les resultats actifs `BiblioLibraryRuntimeResult` et `BiblioWorkResolution` ne conservent pas de `CatalogueResponse.payload`; ils gardent seulement des observations endpoint compactes content-free.

Correctif recherche de candidats du 2026-05-30:

- `app/biblio/passage_candidate_search.py` transforme un `BiblioQueryPlan` en candidats de paragraphes via `GET /search` uniquement;
- `/search.rank` est un score Catalogue float, issu notamment de `ts_rank_cd(...) AS rank` ou du fallback `0::float`, et ne doit jamais etre interprete comme un rang ordinal entier;
- le ranking distingue `catalogue_rank_score` du `first_result_index` local aux resultats retournes par `/search`;
- `/search` peut maintenant exposer un signal faible `document_role_signal`,
  derive du titre du chapitre porteur ou, a defaut, du titre documentaire;
- `GET /search/chapters` peut exposer ce meme signal faible sur ses resultats
  structurels de TOC, derive directement du titre de chapitre et, a defaut, du
  titre documentaire;
- `GET /doc/{id}/chapters` peut exposer ce meme signal faible sur ses lignes de
  TOC directe, derive du titre de chapitre et, a defaut, du titre
  documentaire;
- `GET /doc/{id}/page/{page_no}` et `GET /doc/{id}/context` peuvent maintenant
  exposer un repere TOC borne sous forme d'un objet `chapter`, derive de
  `document_chapters` pour l'unite/page demandee;
- ce repere peut contenir le chapitre courant, sa plage unitaire bornee, et le
  chapitre suivant quand il existe;
- valeurs autorisees pour ce signal faible: `commentary`, `notice`,
  `introduction`;
- source autorisee: `chapter_title` ou `document_title`;
- force autorisee: `weak` uniquement a ce stade;
- ce signal ne prouve jamais qu'un hit est du texte primaire; il sert
  seulement a demoter proprement les hits `commentary`, `notice` ou
  `introduction`, et a conserver un indice explicite plutot qu'une heuristique
  cachee; l'absence de signal ne prouve rien de positif sur la nature du hit.
- le repere `chapter` enrichit seulement la navigation documentaire bornee
  cote FridaDev (`page_read`, `passage_context`); il n'autorise pas a
  sur-vendre une resolution bibliographique plus forte que la TOC elle-meme.
- un score Catalogue float fini peut contribuer au ranking et produire le reason code `high_catalogue_rank_score`;
- l'observabilite des candidats reste content-free: ids courts, pages, paragraphes, `paragraph_id`, scores, hashes de variantes, reason codes et counts seulement;
- l'objet resultat de recherche de candidats ne conserve pas les payloads Catalogue bruts de `/search`; il garde seulement des observations endpoint compactes content-free;
- cette couche ne doit pas appeler `/context`, ne doit pas extraire de passage, et ne doit pas injecter de lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`.

Moteur contextuel Lot 3 du 2026-05-30:

- `app/biblio/passage_context_search.py` consomme les candidats Lot 2 comme un ranking provisoire, pas comme une resolution finale;
- le statut `candidates_found` ne signifie jamais "passage choisi avec certitude";
- le moteur valide seulement un petit top-N borne par `GET /doc/{id}/context`, avec `DEFAULT_MAX_CONTEXT_CANDIDATES = 3`;
- `paragraph_id` est prefere quand disponible, sinon le couple non textuel `page_no` / `para_no` est utilise;
- un contexte sans `document_id`, ou avec `document_id` divergent du candidat, retourne `incoherent_catalogue`;
- un seul contexte coherent et borne peut retourner `extracted`;
- plusieurs contextes plausibles retournent `ambiguous` plutot qu'un choix silencieux;
- aucun contexte exploitable retourne `not_found`, et les erreurs transport/API retournent `catalogue_unavailable`;
- le passage brut est autorise seulement dans l'objet metier interne quand `status=extracted`; il reste interdit en observabilite, logs, dashboard, read-model et retour technique;
- les resultats contextuels ne conservent pas les payloads Catalogue bruts de `/context`; les reponses stockees sont des observations compactes content-free, et le payload brut reste une variable locale transitoire pendant la validation;
- ce lot n'ajoute pas d'injection chat supplementaire et ne modifie pas le toggle frontend.

Selection de passages Lot 4 du 2026-05-30:

- `app/biblio/passage_selection.py` applique un ranking deterministe et content-free aux contextes deja valides par `/context`;
- signaux utilises: score candidat Lot 2, `catalogue_rank_score`, `first_result_index`, reason codes de candidat (`theme_hit`, `exact_theme_variant`, `folded_theme_variant`, `multi_variant_hit`, `work_document_match`, `work_theme_proximity`) et longueur du contexte;
- un seul contexte plausible reste selectionnable;
- plusieurs contextes plausibles ne produisent `extracted` que si le meilleur domine avec `score_gap >= 8.0` et un signal fort autre que le seul rang Catalogue;
- si l'ecart est trop faible ou si le meilleur ne doit sa position qu'au score Catalogue, le statut reste `ambiguous`;
- l'observabilite expose seulement `selected_count`, `top_score`, `score_gap`, `selection_reason_codes` et les decisions content-free;
- les passages non retenus ne sont jamais inclus dans l'observabilite; pour le resultat final unique, le passage brut reste uniquement dans `BiblioPassageContextSearchResult.passage` quand `status=extracted`.

Injection thematique Lot 5 du 2026-05-30:

- le runtime chat garde `chat_runtime.py` comme orchestration mince et delegue `INTENT_SEARCH_CATALOG` a `library_runtime.py`;
- `library_runtime.py` utilise `BiblioPassageContextSearcher` pour executer `GET /search` puis des appels `GET /doc/{id}/context` bornes avant toute lane de passage thematique;
- si un seul passage est selectionne, `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` contient ce passage et le resultat runtime conserve un `BiblioPassageResult` interne;
- si plusieurs contextes plausibles restent proches, le statut runtime reste `ambiguous` et `selected_count=0`, mais une lane bornee peut contenir les passages candidats consultes pour permettre une reponse prudente du LLM principal;
- cette lane multi-passages ne transforme pas l'ambiguite en certitude: son contrat prompt indique que plusieurs passages peuvent etre des candidats plausibles;
- le runtime porte maintenant un niveau de verite produit explicite:
  - `exact_passage` pour une extraction locator/range effectivement resolue;
  - `plausible_candidate` pour une lane de passages candidats ambigus;
  - `contextual_approximation` pour un passage thematique retenu via `search -> context`;
  - `clarification_required` quand la resolution ou l'extraction ne sont pas assez fortes;
- la lane `[CONSULTATION DE BIBLIOTHEQUE]` reste le fallback pour liste, recherche sans passage extrait, erreur ou absence de contexte exploitable;
- les passages bruts issus de contextes ambigus sont autorises seulement dans les `BiblioPassageResult` internes transmis a `BiblioPromptLane.message` et dans la lane prompt produit; ils ne sont pas recopies dans `BiblioPassageContextSearchResult.passage` tant que le statut reste `ambiguous`;
- ces passages candidats restent interdits en observabilite, logs, dashboard, read-model, retour technique et payloads admin;
- les objets resultats actifs ne retiennent toujours aucun `CatalogueResponse.payload`: ils conservent seulement `CatalogueEndpointObservation`, counts, endpoint kinds, ids courts, positions, hashes courts, scores et reason codes.

Smokes live philosophiques Lot 6 du 2026-05-30:

- le protocole reutilisable est `python -m biblio.smoke_live --jsonl`;
- le mode normal est strict: le processus retourne un code non-zero si `raw_marker_leaks=true` ou si `payload_objects_retained > 0`;
- l'inspection non bloquante doit etre explicite via `--no-strict`;
- le runner execute les cas obligatoires de liste, range explicite, recherche thematique, recherche theme seul et formulation dictee approximative;
- les sorties ne contiennent pas les formulations utilisateur, titres, auteurs, locators, passages, payloads Catalogue, prompts complets, cookies, tokens ou DSN;
- chaque record est identifie seulement par `case_id` et expose `status`, `reason_code`, `query_kind`, `client_count`, `endpoint_count`, `endpoint_kinds`, `candidate_count`, `context_call_count`, `selected_count`, `passage_count`, `lane_injected`, `lane_chars`, ids courts, hashes courts, longueurs, `payload_objects_retained` et `raw_marker_leaks`;
- `raw_marker_leaks` est calcule sur les projections content-free (`observability_payload`, observation contextuelle et observation de lane) et sur le record final sanitize avant emission, jamais sur le message prompt brut;
- le nettoyage P3 post-Lot 5 supprime l'ancien chemin `library_runtime._search_catalog()` et ses constantes locales stale: `INTENT_SEARCH_CATALOG` passe uniquement par `_search_passages()` et `BiblioPassageContextSearcher`.

Observabilite/admin recherche passages Lot 7 du 2026-05-30:

- `build_biblio_event_payload()` expose une projection `passage_search` dediee aux recherches thematiques et range/search contextuels;
- cette projection est construite seulement depuis `to_observability()` et les observations endpoint compactes, jamais depuis `BiblioPromptLane.message`, `CatalogueResponse.payload`, le message utilisateur brut ou un passage OCR brut;
- champs autorises: counts (`candidate_count`, `total_candidate_count`, `context_call_count`, `plausible_context_count`, `selected_count`, `passage_result_count`, `passage_count`), flags (`ambiguous`, `lane_injected`, `ranking_available`), longueurs (`lane_chars`), endpoint counts/kinds, scores compacts (`top_score`, `score_gap`, `candidate_top_score`), `selection_reason_codes`, `candidate_query_variant_count`, ids courts, hashes courts et positions non textuelles;
- `theme_query_signal` et `work_query_signal` restent `available=false` tant que la projection ne recoit pas une longueur/hash deja expurgee; le read-model ne doit jamais recalculer ces signaux depuis la requete utilisateur brute;
- `dashboard_turn_facts.biblio_json` materialise les nouveaux champs operateur sous noms compacts (`search_candidate_count`, `context_fetch_count`, `selected_passage_count`, `ambiguous`, `endpoint_kinds`, `selection_reason_codes`, scores), sans migration schema additionnelle;
- les metriques dashboard peuvent agregger candidats, contextes, selections, ambiguite, endpoint kinds et raisons de selection;
- les surfaces admin/dashboard/read-model restent content-free: pas de passage brut, texte OCR, payload Catalogue, prompt complet, lane message, titre, auteur, locator, requete utilisateur brute, cookie, token, DSN ou `.env`.

Validation finale vraie bibliotheque Lot 8 du 2026-05-30:

- le chantier P1 `frida-biblio-real-library-passage-search-todo.md` est clos et archive;
- la validation finale est tracee dans `app/docs/todo-done/validations/frida-biblio-real-library-passage-search-validation-2026-05-30.md`;
- le smoke strict `python -m biblio.smoke_live --jsonl` couvre liste Catalogue, extraction range Theetete, recherche thematique dans Theetete, recherche theme seul et formulation dictee approximative sans accents;
- les cas thematiques valides appellent `/search` puis `/context` borne, injectent une lane de passages candidats quand des contextes plausibles existent, et gardent `ambiguous` lorsque `selected_count=0`;
- le cas range smoke extrait un passage borne et injecte `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`;
- les preuves live valident `payload_objects_retained=0` et `raw_marker_leaks=false` sur tous les smokes;
- les suites Biblio, chat, admin/dashboard et read-model passent en conteneur live;
- aucune case ouverte reelle ne reste dans la roadmap P1: toute evolution future doit rouvrir un lot explicite.

Requalification produit du 2026-05-30:

- la validation ci-dessus reste une preuve technique du chemin passage, mais elle n'est plus un GO produit final "vraie bibliotheque";
- le chantier est rouvert puis corrige et archive dans `app/docs/todo-done/product/frida-biblio-real-library-product-gap-todo.md`;
- une demande de catalogue doit lister tout le fonds disponible jusqu'a 100 ouvrages, pas une preview `limit=5`;
- si `total > displayed`, la lane produit doit dire explicitement combien d'ouvrages existent et combien sont affiches;
- les demandes `quels ouvrages`, `combien d'ouvrages`, `liste la bibliotheque` et `c'est tout ?` sont des signaux Biblio quand le toggle est actif;
- les actions bibliothecaires deterministes reconnues incluent `list_catalog`, `open_document`, `show_table_of_contents`, `search_catalog`, `extract_passage` et `extract_range`;
- les titres/auteurs peuvent etre presentes dans la lane produit de consultation lorsque l'utilisateur demande la liste ou l'ouverture du fonds, mais ils restent interdits dans observabilite/admin/dashboard/read-model;
- Catalogue expose des compteurs TOC (`chapter_count`, `toc_source`) et stocke `document_chapters`;
- une route GET Catalogue legere est maintenant requise et livree pour les gros documents: `GET /doc/{id}/chapters`;
- FridaDev doit utiliser cette route pour `show_table_of_contents` et ne plus passer par `/doc/{id}` pour lister les chapitres d'un gros document.

Route legere table des matieres du 2026-05-30:

- plateforme Catalogue: `GET /doc/{id}/chapters`;
- lecture seule: `documents` + `document_chapters`;
- bornes: `limit` par defaut 500, maximum 1000; `offset` minimum 0;
- payload autorise: `document_id`, compteurs documentaires, `total`, `limit`, `offset`, `count`, `truncated`, et une liste de chapitres `{chapter_no, title, unit_no, source}`;
- payload interdit: texte OCR, paragraphes, excerpts, page text, raw units, fichiers, prompt, secret, cookie, token ou DSN;
- FridaDev expose les titres/chapitres seulement dans la lane produit `[CONSULTATION DE BIBLIOTHEQUE]` quand l'utilisateur demande la table des matieres;
- observabilite/admin/dashboard/read-model ne gardent que endpoint kind, status, duree, counts, id court, longueurs et reason codes, jamais les titres de chapitres ni le payload Catalogue brut;
- `library_runtime.py` delegue l'ouverture document / TOC a `table_of_contents_runtime.py` pour garder la responsabilite du runtime bibliothecaire lisible.

Validation finale Lot 8 du 2026-05-29:

- le parsing naturel accepte les formulations conservatrices `126b de l Apologie`, `126b de l'Apologie`, `126b de la Republique` et `126b -> 126e dans le catalogue` sans garder d'article oral ou de fleche dans le titre;
- la limite Lot 8 "ranges non extraits" est supersedee par le correctif bibliothecaire du 2026-05-30: seuls les ranges bornes et surs peuvent etre extraits; les autres restent refuses explicitement;
- aucune case ouverte reelle ne reste dans la roadmap Biblio archivee;
- toute extension future doit ouvrir un lot explicite si elle touche ranges, UI Catalogue FridaDev, ecriture Catalogue, recherche semantique large, RAG documentaire, OCR ou changement de frontiere avec les documents actifs.

## 11. Etat conversationnel Biblio

Implementation agent bibliothecaire Lot 1 du 2026-05-31:

- module dedie: `app/biblio/conversation_state.py`;
- schema: `biblio_conversation_state_v1`;
- persistance: `message.meta.biblio_state` sur le dernier message utilisateur seulement quand le tour courant produit une transition Biblio utile;
- portee: etat attache a la conversation, persiste content-free via la persistence existante des messages apres sauvegarde normale reussie;
- ancien etat: conserve dans l'historique sauvegarde, jamais efface par toggle Biblio off;
- toggle Biblio off: aucune consultation, aucune mise a jour d'etat, aucun nouveau tamponnage Biblio du message courant;
- tour non utilise sans clarification ni consultation: pas de recopie de l'ancien etat sur le message courant;
- survie reload/reprise/rebuild: garantie seulement apres sauvegarde normale reussie de la conversation;
- observabilite avant sauvegarde: `state_transition.persistence_status=pending_normal_conversation_save`;
- absence de nouvelle table, de migration DB ou de stockage Catalogue;
- absence d'ecriture Catalogue, d'OCR, de route mutante, d'appel OpenRouter et d'agent LLM.

Champs autorises dans l'etat:

- `schema_version`;
- `conversation_id`;
- `current_document` avec `document_id` si disponible, `doc_id_short` et source compacte;
- `current_work` sous forme de presence, longueur et hash court, jamais titre brut;
- `page_no`, `para_no`, `paragraph_id`;
- `last_passage_hash`;
- `last_result`;
- `last_candidates`;
- `last_ambiguity`;
- `last_intent`;
- `updated_at`;
- `source_event`.

Champs interdits dans l'etat:

- passage brut;
- texte OCR;
- payload Catalogue;
- prompt complet;
- lane complete;
- titre brut;
- auteur brut;
- requete utilisateur brute;
- secret, token, DSN, cookie ou `.env`.

Integration runtime:

- `chat_runtime.py` reste l'orchestrateur Biblio mince: toggle, plan deterministe existant, adaptation minimale par etat, runtime bibliothecaire, observabilite et clarification;
- l'etat est lu avant consultation et mis a jour apres resolution, ouverture, TOC, extraction, recherche, ambiguite ou clarification explicite;
- `previous_page` et `next_page` sont distingues comme follow-ups, mais restent clarifies sans outil page dans ce lot;
- l'adaptation par etat est bornee au cas TOC sans cible explicite quand un `document_id` courant existe deja;
- P03 reste un cas de surveillance planner/intention, pas une promesse de correction Lot 1;
- P09 reste un cas de surveillance outillage page, pas une promesse de navigation complete Lot 1;
- si l'utilisateur demande une reprise et que l'etat, le planner ou l'outillage manque, Frida recoit une lane `[ETAT BIBLIO]` lui demandant de clarifier proprement;
- cette lane interdit explicitement `latest/page`, `latest/context` et toute reprise inventee;
- l'observabilite `stage=biblio` expose maintenant `state` et `state_transition` content-free sans pretendre que la sauvegarde finale a deja reussi;
- `conversation_state.py` depasse temporairement 500 lignes mais reste accepte comme module borne etat/projection; toute extension Lot 2 doit extraire une responsabilite avant de l'alourdir.

## 12. Socle agent bibliothecaire Lot 7

Le chantier agent bibliothecaire ajoute un socle OpenRouter / JSON non actif
par defaut au-dessus de Biblio native.

Contrat avec Biblio native:

- `BIBLIO_LIBRARIAN_AGENT_MODE=off` par defaut ne construit aucun appel modele;
- `shadow` et `candidate` peuvent produire un plan candidat, mais ne remplacent
  pas le chemin deterministe Biblio;
- `active` n'est pas un chemin produit livre dans ce lot;
- le modele agent est configurable et peut etre vide; aucun slug n'est hardcode
  comme default actif;
- les outils proposés par le modele restent bornes a l'allowlist GET-only
  Biblio: catalog, search, metadata, chapters, locate, context;
- toute methode non GET, outil inconnu, outil interdit ou budget depasse
  retombe sur le deterministe;
- l'observabilite de l'agent ne contient ni prompt, ni raw JSON modele, ni
  message utilisateur brut, ni titre/auteur/locator, ni passage, ni payload
  Catalogue;
- aucun endpoint Catalogue nouveau n'est cree et aucune route mutatrice n'est
  autorisee.

Artefact provider: `app/docs/states/baselines/frida-biblio-librarian-agent-openrouter-json-2026-06-01.md`.

## 13. Tests de regression du chantier

Suites et cas a conserver:

- client GET-only nominal;
- interdiction routes mutatrices;
- `DELETE /doc/{id}` interdit;
- `DELETE /doc/{id}/with-files` interdit;
- `PUT /doc/{id}/metadata` interdit;
- `PUT /settings` interdit;
- `POST /settings/reset` interdit;
- `POST /progress/recent/clear` interdit;
- document trouve;
- document absent;
- document ambigu;
- locator trouve;
- locator absent;
- locator ambigu;
- Stephanus `126b -> 126e`;
- passage trop long;
- lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` presente quand Biblio utilisee;
- `Biblio off` empeche toute consultation Catalogue;
- `Biblio on` autorise seulement une consultation bornee;
- anti-contamination `active_document`;
- anti-contamination workspace;
- anti-contamination Memory/RAG;
- anti-contamination Identity;
- anti-contamination Summary;
- anti-contamination Web;
- anti-contamination Hermeneutic;
- absence AnythingLLM dans le chemin nominal;
- observabilite content-free;
- absence de texte brut dans logs ordinaires;
- erreur Catalogue content-free;
- timeout Catalogue content-free.

## 14. Conditions de reouverture future

Le chantier Biblio native est clos au 2026-05-29. Son correctif P1 "vraie bibliotheque / recherche de passages" est requalifie: preuve technique close, validation produit rouverte le 2026-05-30. Une reouverture future doit rester explicite et verifier d'abord que:

- cette spec reste indexee comme source-of-truth;
- le client cible est confirme GET-only;
- les endpoints mutateurs sont explicitement exclus des tests et du code;
- la frontiere avec `active_document` et workspace est conservee;
- la decision produit accepte que FridaDev consomme Catalogue sans ecrire dans Catalogue, sauf lot separe d'edition explicitement approuve.

Tout changement futur qui veut ecrire dans Catalogue, editer les metadonnees depuis FridaDev, supprimer un document, lancer OCR, backfill, indexer ou vectoriser doit ouvrir un nouveau lot explicite avant code.
