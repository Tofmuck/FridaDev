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
- la verite produit de sortie:
  - exact;
  - plausible;
  - contextuel;
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
- `status`
- `reason_code`
- `truth_level`
- `state_update`
- `result_summary`
- `anchors` utiles
- `tool_trace` content-free

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
| P03 | Trouver l'ouvrage | Retrouver l'ouvrage ou la bonne cible documentaire | `work_lookup` | `catalog_search`, `document_open_summary`, `document_toc` si utile | faux vert | Le smoke vert connu repose surtout sur `catalog_search`; ce n'est pas encore une vraie methode d'ouverture documentaire | mixte | Definir `work_lookup` comme methode produit explicite avec sortie structuree ouvrage/document/ambiguite |
| P09 | Table des matieres d'un ouvrage | Montrer la TOC de l'ouvrage cible | `document_toc_show` | `document_toc`, resolution prealable eventuelle | faux vert | Le chemin peut finir par appeler `chapters`, mais il reste repare depuis un cas initialement non resolu | FridaDev | Rattacher la TOC a une vraie methode `document_toc_show`, sans reparation silencieuse |

### C. Passage canonique explicite

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P04 | Plage canonique explicite | Extraire un passage borne demande par locator/range | `passage_extract_canonical_range` | resolution documentaire, `locate`, `passage_context` | partiel | Le chemin exact existe sur certains cas forts, mais la methode n'est pas encore la brique canonique du systeme | mixte | Declarer la methode produit et documenter clairement la frontiere label simple vs plage canonique generale |
| P10 | Amorcage d'etat sur passage explicite | Initialiser l'etat Biblio a partir d'un passage exact | `passage_seed_from_exact_result` | meme chaine que P04 + `state_update` | partiel | L'amorcage existe, mais comme consequence du runtime, pas comme methode explicite | FridaDev | Rendre le seed d'etat explicite dans le contrat de methode |

### D. Recherche thematique dans une oeuvre

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P05 | Theme dans une oeuvre | Trouver un passage thematique dans l'oeuvre cible | `passage_search_in_work` | resolution documentaire, `catalog_search`, `passage_context`, selection | partiel | Le systeme sait produire des candidats/contextes, pas encore une verite bibliothecaire forte | mixte | Stabiliser la methode produit et la sortie `exact/plausible/contextuel/clarification` |
| P06 | Theme dans une oeuvre sans accents | Meme cas que P05, avec variantes de forme | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | partiel | Le cas passe encore avec reparation/fallback sur certaines variantes | FridaDev | Sortir les variantes de la logique de reparation et les rattacher a la methode produit |
| P07 | Theme lexical voisin | Meme cas que P05 avec reformulation ("sage-femme") | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | partiel | La recherche marche parfois, mais sans garantie de source ni de niveau documentaire | mixte | Integrer la verification oeuvre/source dans la methode |
| P08 | Theme paraphrase | Meme cas que P05 avec reformulation plus libre | `passage_search_in_work` | variantes + `catalog_search` + `passage_context` | partiel | Le cas reste un `search -> context` utile, pas une resolution forte | mixte | Mieux separer paraphrase, candidat plausible et passage exact |

### E. Suivi de passage / multi-tour

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P11 | Expliquer ce passage | Expliquer le dernier passage ancre | `passage_explain_current` | lecture du `last_result`, `passage_context` si necessaire | partiel | L'etat aide deja, mais la methode n'est pas encore une unite produit explicite | FridaDev | Definir la methode `passage_explain_current` avec preconditions et sortie structuree |
| P12 | Autour de ce passage | Montrer le voisinage documentaire du passage courant | `passage_show_around_current` | `passage_context` | partiel | Cas utile et relativement sain, mais encore trop confondu avec simple contexte local | FridaDev | Fixer la verite produit: vrai voisinage borne vs simple contexte |
| P13 | Plus haut | Remonter avant le passage courant | `passage_move_previous_segment` | `page_read` ou primitive de voisinage plus fine | faux vert | Le cas est encore maquille par des reparations de contexte, pas par une vraie methode documentaire | mixte | Declarer le cas comme non stabilise tant qu'une primitive documentaire propre n'existe pas |
| P14 | Continue | Continuer apres le passage courant | `passage_continue_next_segment` | `page_read` ou primitive sequentielle dediee | faux vert | Le smoke vert connu ne prouve pas une vraie continuation documentaire | mixte | Arreter de considerer ce cas comme "vert" tant que la methode n'est pas explicite et ancree |
| P15 | D'ou vient ce passage ? | Verifier l'origine documentaire du passage visible | `passage_origin_check` | `document_open_summary`, `document_toc`, `passage_context`, ancre technique | partiel | La provenance est partiellement visible, mais pas encore garantie comme verite forte | mixte | Ajouter un vrai statut de provenance et une verification de source exploitable |

### F. Recherche thematique hors oeuvre courante

| case_id | Nom du cas | Intention produit | Methode produit attendue | Outils / scripts techniques | Etat actuel | Verite produit actuelle | Dependance | Action necessaire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P16 | Theme externe 1 | Trouver un passage thematique dans une autre oeuvre/corpus | `passage_search_external_work` | `catalog_search`, `passage_context`, selection | partiel | Le cas peut marcher, mais encore avec reparation/fallback selon la forme de demande | mixte | Definir explicitement le scope corpus/oeuvre et le statut de resultat |
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
- `passage_seed_from_exact_result`
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

- [ ] Geler la grammaire des 18 cas.
- [ ] Geler le registre initial des methodes produit.
- [ ] Geler la regle de statut `vert net / partiel / faux vert / absent`.

### Lot B - Contrat methode produit

- [ ] Faire evoluer la spec agent vers une sortie qui nomme la methode produit.
- [ ] Definir le payload structure minimal commun a toutes les methodes.
- [ ] Definir les preconditions et la verite produit de chaque methode.

### Lot C - Execution runtime par methode

- [ ] Brancher le runtime sur les methodes produit, pas sur des intentions
      heuristiques eparpillees.
- [ ] Arreter les reparations silencieuses qui changent de methode sans le dire.
- [ ] Laisser le deterministe tenir les murs sans redevenir le plan produit.

### Lot D - Cleanup `app/biblio/` par responsabilites

- [ ] Recentrer `chat_runtime.py` sur l'orchestration.
- [ ] Sortir la reconnaissance de cas locale la ou elle est dupliquee.
- [ ] Separer clairement:
      - reconnaissance de cas;
      - registre de methodes;
      - execution de methode;
      - outils techniques;
      - observabilite.

### Lot E - Chantiers Catalogue / DB / indexation necessaires

- [ ] Ouvrir seulement les lots structurels encore necessaires:
      - intervalle canonique;
      - signal primaire/commentaire;
      - oeuvre interne;
      - navigation documentaire plus riche si prouvee necessaire.

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
