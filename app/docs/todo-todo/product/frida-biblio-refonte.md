# Frida Biblio refonte

Date: 2026-06-02
Statut: TODO active
Classement: `app/docs/todo-todo/product/`
Sources:

- `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/audits/frida-biblio-stephanus-library-audit-2026-06-02.md`
- `app/docs/states/baselines/biblio-smokes/agent-first-full-post-truth-fix-20260601T185215Z.jsonl`

Portee: document canonique de pilotage produit pour la refonte Biblio. Ce
document ne remplace ni la spec agent, ni la spec Catalogue. Il fixe
l'invariant produit, la grammaire des 18 cas, la couche "methode produit",
les verites actuelles, les faux verts et l'ordre reel des lots.

## 1. Invariant produit canonique

Invariant durable:

- il existe 18 cas Biblio de reference;
- ces 18 cas forment la grammaire produit;
- le bibliothecaire recoit:
  - la demande utilisateur;
  - les 5 derniers echanges utiles;
  - l'etat Biblio;
- le bibliothecaire reconnait le cas applicable;
- le bibliothecaire declenche la methode produit explicite correspondante;
- la methode produit orchestre un ou plusieurs outils/scripts techniques bornes;
- la methode renvoie un resultat structure;
- Frida repond a partir de ce resultat structure.

Doctrine:

- le bibliothecaire est souverain pour reconnaitre le cas;
- le deterministe tient les murs:
  - garde-fous;
  - refus propres;
  - validation;
  - fallback;
  - bornes techniques;
- un parseur local ne doit plus decider le cas a la place du bibliothecaire;
- un agent ne doit pas improviser le produit sans cas ni methode explicites.

Regle de structure:

- `1 cas != 1 outil`;
- `1 cas = 1 methode produit explicite`;
- `1 methode produit` peut encapsuler:
  - 1 outil;
  - plusieurs outils;
  - plusieurs scripts;
  - une validation;
  - une clarification;
  - une mise a jour d'etat.

## 2. Couches a separer explicitement

### A. Cas produit

Le cas produit est la forme grammaticale stable que le produit promet de
reconnaitre. Exemples: "catalogue complet", "ouvrir un ouvrage", "sortir une
plage canonique", "autour de ce passage", "origine du passage".

### B. Methode produit

La methode produit est l'unite de pilotage du runtime. Elle porte:

- l'intention produit;
- les preconditions;
- les outils/scripts autorises;
- le type de resultat structure attendu;
- le niveau de verite produit de sortie:
  - exact;
  - plausible;
  - contextuel;
- le statut d'execution de sortie:
  - success;
  - clarification;
  - not_found;
  - error.

### C. Outils / scripts techniques

Les outils/scripts sont les briques bornes:

- `catalog_list`
- `catalog_search`
- `document_open_summary`
- `document_toc`
- `page_read`
- `locate`
- `passage_context`

Ces briques ne sont pas la grammaire produit. Elles sont l'infrastructure
technique des methodes.

### D. Payload structure attendu

Chaque methode doit renvoyer un payload structure qui peut etre lu par Frida
sans reenqueter sur le cas. Ce payload doit porter au minimum:

- `case_id`
- `product_method`
- `execution_status`
- `reason_code`
- `truth_level`
- `state_update`
- `result_summary`
- `anchors` utiles
- `tool_trace` content-free

Doctrine de transition Lot B:

- Lot B garantit la couche `product_method`;
- `case_id` peut rester vide pendant la transition si la methode produit est
  reconnue proprement mais que le cas exact n'est pas tranchable honnetement;
- une reparation legacy peut inferer `product_method`, mais elle ne doit pas
  inventer un `case_id` plus precis que ce qu'elle sait reellement.

Mise a jour Lot C minimal 2026-06-02:

- l'execution agent-first complete maintenant les plans selon `product_method`;
- le deterministe peut encore fournir des bornes ou des indices de requete,
  mais seulement a l'interieur de la methode deja declaree;
- une completion runtime ne doit plus changer silencieusement de methode parce
  qu'une autre intention deterministe passait par la.
- le suivi d'origine/provenance d'un passage reste une methode distincte
  (`passage_origin_check`), meme lorsqu'il reutilise le meme outil borne de
  contexte que `passage_explain_current`.

Le payload ne doit pas porter:

- prompt brut;
- query brute;
- payload Catalogue brut;
- passage brut hors lane produit;
- titre brut, auteur brut, locator brut dans l'observabilite ordinaire.

### E. Dependances DB / indexation / representation

Ce document doit dire explicitement si un cas bloque:

- cote FridaDev seulement;
- cote Catalogue / DB / indexation;
- ou en mixte.

## 3. Regle de statut produit

Statuts utilises dans cette TODO:

- `vert net`: le cas est reconnu proprement, execute par la bonne methode, sans
  reparation silencieuse et sans derive produit.
- `partiel`: le cas fonctionne sur une partie saine du besoin, mais il manque
  une verite produit, une preuve de source, une borne ou une partie du contrat.
- `faux vert`: le cas peut sembler vert dans les smokes, mais la logique
  produit actuelle ne correspond pas encore a la methode attendue.
- `absent`: le cas n'a pas de methode produit reelle ou depend d'une
  primitive/documentation inexistante.

Regle dure:

- un cas `fallback_repaired` n'est jamais `vert net`;
- un cas "outils executes mais methode non explicite" n'est jamais `vert net`;
- un cas qui depend d'un bricolage `search -> context` au lieu de la bonne
  methode reste `partiel` ou `faux vert`;
- un cas qui n'a pas d'objet d'intervalle, de source ou de navigation reel ne
  doit pas etre promu artificiellement en `livre`.

## 4. Matrice canonique des 18 cas

### A. Catalogue

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | Catalogue complet | Lister le fonds disponible | `catalog_list_full` | `catalog_list` | vert net | Le cas est deja lisible comme consultation bornee du catalogue | FridaDev | Conserver cette methode et la declarer explicitement dans le futur registre |
| P02 | Catalogue complet borne a 100 | Dire combien il y a d'ouvrages et lister les 100 premiers / tous si <= 100 | `catalog_list_bounded` | `catalog_list` | vert net | La borne produit actuelle tient la route tant qu'elle reste explicite | FridaDev | Formaliser la continuation au-dela de 100 dans la methode, pas dans un fallback implicite |

### B. Ouvrage / ouverture / TOC

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P03 | Trouver l'ouvrage | Retrouver l'ouvrage ou la bonne cible documentaire | `work_lookup` | `catalog_search`, `document_open_summary`, `document_toc` si utile | vert net | Le cas est maintenant reconnu agentiquement comme `work_lookup`, execute les outils documentaires bornes attendus et conserve une sortie structuree exploitable sans fallback deterministe | FridaDev | Conserver le contrat `work_lookup` et surveiller seulement les regressions d'agent-first |
| P09 | Table des matieres d'un ouvrage | Montrer la TOC de l'ouvrage cible | `document_toc_show` | `document_toc`, resolution prealable eventuelle | vert net | La TOC est maintenant reconnue agentiquement comme `document_toc_show`, resolve une cible documentaire bornee puis appelle `document_toc`/`chapters` sans reparation silencieuse maquillee en succes | FridaDev | Conserver la TOC comme consultation bornee; la navigation plus riche autour de cette TOC reste un sujet distinct |

### C. Passage canonique explicite

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P04 | Plage canonique explicite | Extraire un passage borne demande par locator/range | `passage_extract_canonical_range` | resolution documentaire, `locate`, `passage_context`, `page_read` borne si la plage traverse plusieurs pages | vert net | La methode explicite est maintenant reconnue agentiquement, assemble une plage canonique bornee exploitable et publie un `interval_hint` reutilisable, sans promettre un objet canonique general d'intervalle | FridaDev | Conserver la frontiere claire entre range borne resolue et support general d'intervalle canonique |
| P10 | Passage courant de reference | Faire de ce passage exact le point de depart de la suite Biblio | `passage_set_current_reference` | meme chaine que P04 + `state_update` | vert net | Le tour d'extraction exacte publie maintenant explicitement la mise en reference courante comme resultat produit `P10`, avec ancre technique persistee pour la suite, sans demander a l'agent de feindre une difference linguistique avec `P04` | FridaDev | Conserver cette couture explicite entre extraction exacte et reference courante |

### D. Recherche thematique dans une oeuvre

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P05 | Theme dans une oeuvre | Trouver un passage thematique dans l'oeuvre cible | `passage_search_in_work` | resolution documentaire, `catalog_search`, `passage_context`, selection | vert net | La methode explicite est maintenant reconnue agentiquement, consulte l'oeuvre resolue puis un contexte borne, et restitue un passage thematique utile sans le sur-vendre comme certitude textuelle plus forte que ce que le runtime tient | FridaDev | Conserver la distinction entre passage plausible/contextuel et preuve textuelle forte |
| P06 | Theme dans une oeuvre sans accents | Meme cas que P05, avec variantes de forme | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | vert net | La variante sans accents/translitteree est maintenant reconnue par l'agent comme le bon cas de famille, sans rebasculer la reconnaissance vers une reparation deterministe phrase par phrase | FridaDev | Conserver cette distinction du cote agentique et ne pas la redescendre dans le parseur local |
| P07 | Theme lexical voisin | Meme cas que P05 avec reformulation ("sage-femme") | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | vert net | La reformulation lexicale voisine est maintenant reconnue comme le bon cas de famille et reste bornee a l'oeuvre resolue avant consultation de contexte, sans fabriquer une source hors document courant | FridaDev | Conserver la verification oeuvre/document comme borne de la methode |
| P08 | Theme paraphrase | Meme cas que P05 avec reformulation plus libre | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | vert net | La paraphrase libre est maintenant reconnue comme le bon cas de famille et reste honnetement bornee a un candidat documentaire utile, sans etre maquillee en resolution forte | FridaDev | Conserver la distinction entre paraphrase, candidat plausible et passage exact |

### E. Suivi de passage / multi-tour

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P11 | Expliquer ce passage | Expliquer le dernier passage ancre | `passage_explain_current` | lecture du `last_result`, `passage_context` si necessaire | vert net | Le follow-up explicatif repart maintenant de l'ancre courante en agent-first nominal, avec `case_id=P11`, `product_method=passage_explain_current` et un seul `passage_context` borne, sans fallback deterministe | FridaDev | Conserver cette borne agentique: expliquer le passage courant sans refaire la reconnaissance du cas dans le parseur local |
| P12 | Autour de ce passage | Montrer le voisinage documentaire du passage courant | `passage_show_around_current` | `passage_context` | vert net | Le follow-up de voisinage courant est maintenant tenu en agent-first nominal: `case_id=P12`, `product_method=passage_show_around_current` et `passage_context` borne autour de l'ancre courante, avec reparation d'execution limitee au meme product_method si le tool call initial est trop fragile | FridaDev | Conserver cette reparation agentique bornee sans redonner la reconnaissance du cas au parseur local |
| P13 | Plus haut | Remonter avant le passage courant | `passage_move_previous_segment` | `passage_context` sur le segment precedent, sinon repli page borne | vert net | Le cas est maintenant tenu comme vraie methode documentaire: si l'ancre courante porte `page_no/para_no`, Frida remonte d'abord vers le segment precedent sur la meme page via `passage_context`; si cette finesse manque, le repli reste page-granulaire et borne | FridaDev | Conserver cette priorite documentaire: segment precedent si l'ancre le permet, page precedente seulement en repli explicite |
| P14 | Continue | Continuer apres le passage courant | `passage_continue_next_segment` | `passage_context` si une fin precise est connue, sinon `page_read` borne | vert net | Le cas est maintenant tenu comme vraie methode documentaire agent-first: la continuation reste ancree sur l'etat courant et peut s'executer soit via `passage_context`, soit via `page_read`, tant que l'execution reste dans la meme methode produit et sous bornes explicites | FridaDev | Conserver cette verite produit: continuation documentaire explicite, avec repli borne assume quand l'ancre disponible est plus page-granulaire |
| P15 | D'ou vient ce passage ? | Verifier l'origine documentaire du passage visible | `passage_origin_check` | `document_open_summary`, `document_toc`, `passage_context`, ancre technique | vert net | La provenance du passage courant est maintenant tenue comme methode agent-first explicite: l'agent reconnait `P15`, garde l'ancre courante et peut verifier l'origine soit via `document_open_summary`, soit via `passage_context`, tant que l'execution reste dans la meme methode produit et rend une origine documentaire exploitable | FridaDev | Conserver cette verite de provenance: ancre courante obligatoire, verification documentaire bornee, pas de requalification locale du cas |

### F. Recherche thematique hors oeuvre courante

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P16 | Theme externe 1 | Trouver un passage thematique dans une autre oeuvre/corpus | `passage_search_external_work` | `catalog_search`, `passage_context`, selection | vert net | La recherche thematique hors oeuvre courante est maintenant tenue comme vraie methode bibliothecaire canonique: l'agent reconnait explicitement `P16`, borne la cible documentaire externe, puis atteint un `passage_context` utile sans fallback deterministe ni requalification locale du cas | FridaDev | Conserver cette methode externe comme cas produit unique, sans re-decouper ses reformulations en mini-parseur opportuniste |
| P17 | Theme externe 2 | Meme methode que P16, autre reformulation | `passage_search_external_work` | `catalog_search`, `passage_context`, selection | partiel | Meme faiblesse: pas encore une vraie methode bibliothecaire canonique | mixte | Mutualiser la methode au lieu de traiter ces cas comme des variantes opportunistes |
| P18 | Theme externe 3 | Meme methode que P16, autre reformulation | `passage_search_external_work` | `catalog_search`, `passage_context`, selection | partiel | Le cas est utile, mais reste un assemblage d'outils plus qu'une methode produit | mixte | Fermer la methode externe avec verite produit et clarifications propres |

## 5. Registre cible des methodes produit

Le chantier doit converger vers un registre explicite de methodes produit. Ce
registre n'est pas encore une spec de schema; il est la cible de pilotage.

Methodes canoniques minimales:

- `catalog_list_full`
- `catalog_list_bounded`
- `work_lookup`
- `document_toc_show`
- `passage_extract_canonical_range`
- `passage_set_current_reference`
- `passage_search_in_work`
- `passage_explain_current`
- `passage_show_around_current`
- `passage_move_previous_segment`
- `passage_continue_next_segment`
- `passage_origin_check`
- `passage_search_external_work`

Regles:

- plusieurs cas peuvent reutiliser la meme methode;
- une methode ne doit pas etre une simple copie du nom d'un outil;
- le contrat agent futur doit evoluer vers une sortie qui nomme la methode
  produit, pas seulement des `tool_calls`;
- le runtime doit executer la methode, pas "deviner" la methode apres coup
  depuis une liste d'outils.

## 6. Nettoyage `app/biblio/` rattache a l'invariant

Le cleanup n'est pas cosmetique. Il est necessaire parce que le meme cas est
encore decide ou repare a plusieurs endroits.

### A. Nettoyage immediat a rattacher au chantier fonctionnel

| Zone | Fichiers principaux | Probleme | Pourquoi ce n'est pas cosmetique |
| --- | --- | --- | --- |
| Reconnaissance de cas distribuee | `query_planner.py`, `librarian_dialogue_intents.py`, `librarian_dialogue_navigation.py`, `conversation_followup.py`, `librarian_dialogue_planner.py` | Plusieurs parseurs locaux continuent a reconnaitre le cas ou a le tordre | Tant que plusieurs couches decident le cas, le bibliothecaire n'est pas souverain |
| Orchestration runtime trop concentree | `chat_runtime.py`, `library_runtime.py`, `librarian_agent_first.py` | Le runtime choisit, repare, reroute et post-traite trop de choses | Cela empeche de brancher proprement une couche "methode produit" |
| Methode et outils confondus | `librarian_tools.py`, `librarian_planner.py`, `librarian_agent_contract.py` | Les outils sont exposes clairement, mais la methode produit ne l'est pas | Le systeme parle en `tool_calls`, pas en cas produit explicites |
| Verite produit eparpillee | `prompt_lane.py`, `observability.py`, `chat_runtime.py` | Le niveau exact/plausible/contextuel n'est pas encore porte par une methode source unique | Le produit peut devenir vrai en observabilite et faux dans sa logique d'execution |

### B. Nettoyage a faire apres stabilisation fonctionnelle

| Zone | Fichiers principaux | Pourquoi attendre |
| --- | --- | --- |
| Moteurs bas niveau passage | `passage_candidate_search.py`, `passage_context_search.py`, `passage_selection.py`, `passage_extractor.py` | Ces briques sont plus stables que la couche de pilotage; il vaut mieux d'abord figer les methodes produit |
| Resolveurs documentaires | `document_resolver.py`, `work_resolver.py`, `table_of_contents_runtime.py` | Leur bon decoupage dependra du futur registre de methodes |
| Client Catalogue et observabilite large | `catalogue_client.py`, `observability.py` | Le vrai nettoyage dependra des primitives retenues et des payloads de methode |

### C. Regle de cleanup

- ne pas commencer par "refactoriser le bazar";
- commencer par fixer:
  - qui reconnait le cas;
  - quelle methode porte ce cas;
  - quel payload structure revient;
- extraire ensuite les responsabilites par couche, pas par confort local.

## 7. Ce qui releve de FridaDev vs Catalogue / DB / indexation

### A. Releve de FridaDev

- registre de methodes produit;
- reconnaissance du cas par le bibliothecaire;
- fallback deterministe comme garde-fou, pas comme souverainete produit;
- orchestration runtime par methode;
- verite produit de sortie;
- etat Biblio multi-tour;
- lanes produit;
- observabilite content-free;
- clarifications propres.

### B. Releve de Catalogue / DB / indexation

- representation forte d'une oeuvre interne si le produit la promet;
- signal exploitable primaire/commentaire/notice/introduction;
- objet ou mapping d'intervalle canonique general;
- primitives documentaires supplementaires si `page_read` et `passage_context`
  ne suffisent pas;
- indexation utile de TOC si la TOC doit devenir searchable comme support
  d'oeuvre interne.

### C. Releve mixte

- `work_lookup`
- verification de provenance;
- priorite texte primaire > commentaire;
- recherche thematique dans une oeuvre;
- continuation documentaire forte.

## 8. Ordre reel des lots

### Lot A - Cadrage canonique cas -> methode

- [x] Geler la grammaire des 18 cas.
- [x] Geler le registre initial des methodes produit.
- [x] Geler la regle de statut `vert net / partiel / faux vert / absent`.

### Lot B - Contrat methode produit

- [x] Faire evoluer la spec agent vers une sortie qui nomme la methode produit.
- [x] Definir le payload structure minimal commun a toutes les methodes.
- [x] Definir les preconditions et la verite produit de chaque methode.

### Lot C - Execution runtime par methode

- [x] Brancher le runtime sur les methodes produit, pas sur des intentions
      heuristiques eparpillees.
- [x] Arreter les reparations silencieuses qui changent de methode sans le dire.
- [x] Laisser le deterministe tenir les murs sans redevenir le plan produit.

### Lot D - Cleanup `app/biblio/` par responsabilites

- [x] Recentrer `chat_runtime.py` sur l'orchestration.
- [x] Sortir la reconnaissance de cas locale la ou elle est dupliquee.
- [x] Separer clairement:
      - reconnaissance de cas;
      - registre de methodes;
      - execution de methode;
      - outils techniques;
      - observabilite.

### Lot E - Chantiers Catalogue / DB / indexation necessaires

- [ ] Lot E reste ouvert tant qu'un `case_id` encore `partiel` ou `faux vert`
      de la matrice canonique n'est pas referme comme vraie methode produit.
- [ ] Regle de fermeture de Lot E: aucune case ci-dessous ne peut etre cochee
      sans au moins un test live avec le bibliothecaire agentique, conserve
      dans un artefact JSONL date, prouvant noir sur blanc:
      - `case_id` reconnu;
      - bonne methode/categorie de cas;
      - bons outils proposes ou executes;
      - statuts runtime/agent/produit exploitables;
      - resultat produit conforme au besoin.
- [x] `P03 work_lookup`: trouve l'ouvrage comme vraie methode produit
      explicite, agentique et structuree.
- [x] `P04 passage_extract_canonical_range`: ferme l'extraction canonique comme
      methode produit explicite, sans vendre un objet general d'intervalle tant
      qu'il n'existe pas.
- [x] `P05 passage_search_in_work`: ferme la recherche thematique dans une
      oeuvre avec une methode agentique explicite et une borne documentaire
      honnete.
- [x] `P06 passage_search_in_work` variante sans accents: ferme le cas sans
      rebasculer la reconnaissance vers des reparations locales phrase par
      phrase.
- [x] `P07 passage_search_in_work` variante lexicale voisine: ferme le cas
      avec verification oeuvre/source exploitable.
- [x] `P08 passage_search_in_work` paraphrase libre: ferme le cas en separant
      clairement paraphrase, candidat plausible et passage exact.
- [x] `P09 document_toc_show`: ferme la TOC comme vraie methode rattachee a une
      cible resolue, sans elargir le parseur local.
- [x] `P10 passage_set_current_reference`: ferme la mise en reference courante
      comme methode explicite, pas comme effet de bord du runtime.
- [x] `P11 passage_explain_current`: fermer l'explication du passage courant
      comme vraie methode multi-tour explicite.
- [x] `P12 passage_show_around_current`: fermer le voisinage documentaire du
      passage courant comme vraie methode explicite.
- [x] `P13 passage_move_previous_segment`: fermer `plus haut` comme vraie
      methode documentaire, pas comme reparation de contexte.
- [x] `P14 passage_continue_next_segment`: fermer `continue` comme vraie methode
      documentaire explicite, pas comme smoke vert ambigu.
- [x] `P15 passage_origin_check`: fermer la provenance du passage comme verite
      documentaire exploitable.
- [x] `P16 passage_search_external_work`: fermer la recherche thematique hors
      oeuvre courante comme vraie methode bibliothecaire canonique.
- [ ] `P17 passage_search_external_work` reformulation soeur: fermer le cas dans
      la meme methode canonique, sans variante opportuniste locale.
- [ ] `P18 passage_search_external_work` reformulation soeur: fermer le cas dans
      la meme methode canonique, avec meme niveau de preuve live.
- [ ] Les sous-crans techniques deja livres ci-dessous ne doivent plus etre lus
      comme "Lot E coche", mais comme pieces de support deja acquises pour
      fermer ensuite les cas produit restants.
- [x] Reutiliser la TOC/chapters legere existante comme hint d'oeuvre interne
      quand un document physique unique est deja resolu, avant de retomber sur
      la recherche plein texte de paragraphes.
- [x] Rendre la TOC searchable a l'echelle du catalogue via une route GET
      legere de recherche de chapitres, puis l'utiliser dans `work_lookup`
      avant de retomber sur `/search` de paragraphes quand aucun document
      physique unique n'est encore resolu.
- [x] Exploiter les ancres `locate` deja resolues avec `GET /doc/{id}/page/{page_no}`
      pour sortir de la limite artificielle "meme page seulement" sur les
      ranges canoniques bornes, sans pretendre avoir encore un objet
      d'intervalle canonique general.
- [x] Exposer depuis Catalogue un signal faible `document_role_signal` sur les
      hits `/search`, derive des titres de chapitre ou de document, puis
      l'utiliser seulement comme indice faible negatif de demotion
      `commentary/notice/introduction` cote FridaDev, sans emettre de faux
      signal positif par defaut ni le maquiller en verite primaire forte.
- [x] Propager ce signal faible negatif aux hits `GET /search/chapters`, puis
      l'utiliser seulement pour refuser qu'un chapitre de type
      `introduction/notice/commentary` engage a lui seul `work_lookup` comme
      resolution d'oeuvre interne.
- [x] Propager ce meme signal faible negatif aux lignes `GET /doc/{id}/chapters`
      et l'utiliser pareillement seulement comme garde-fou negatif quand
      `work_lookup` travaille deja dans un document physique unique.
- [x] Faire remonter depuis `GET /doc/{id}/page/{page_no}` et
      `GET /doc/{id}/context` un repere TOC borne (chapitre courant /
      chapitre suivant) quand la structure documentaire l'autorise deja, puis
      l'afficher cote navigation sans le maquiller en resolution bibliographique
      forte.

## 9. Criteres de sortie de cette refonte

- [ ] Les 18 cas existent comme matrice produit explicite, pas seulement comme
      smokes.
- [ ] Chaque cas renvoie a une methode produit explicite.
- [ ] Chaque methode annonce ses outils/scripts techniques et son payload
      structure.
- [ ] Les faux verts sont explicitement nommes et refuses comme validation
      finale.
- [ ] La separation FridaDev / Catalogue / DB / indexation est documentee sans
      flou.
- [ ] Le cleanup `app/biblio/` est rattache a l'invariant produit, pas a un
      geste de style.

## 10. Regles de pilotage

- [ ] Aucun lot futur ne peut se declarer "termine" sur un simple smoke vert si
      le cas reste `partiel` ou `faux vert`.
- [ ] Aucun lot futur ne doit confondre outil technique et methode produit.
- [ ] Toute validation future doit dire si l'ecart restant releve:
      - de FridaDev;
      - de Catalogue / DB / indexation;
      - ou d'un mixte.
- [ ] Aucune reouverture de micro-lot runtime ne doit court-circuiter cette
      matrice canonique.
