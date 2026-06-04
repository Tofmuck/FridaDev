# Frida Biblio Last Chance

Date: 2026-06-03
Statut: TODO active structurante
Classement: `app/docs/todo-todo/product/`

Sources lues:

- `AGENTS.md`
- `app/docs/todo-todo/product/frida-biblio-refonte.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
- `app/biblio/chat_runtime.py`
- `app/biblio/librarian_agent_first.py`
- `app/biblio/librarian_agent_openrouter.py`
- `app/biblio/librarian_method_runtime.py`
- `app/biblio/librarian_product_methods.py`
- `app/biblio/librarian_tools.py`
- `app/biblio/librarian_planner.py`
- `app/biblio/library_runtime.py`
- `app/biblio/work_resolver.py`
- `app/biblio/passage_extractor.py`
- `app/biblio/smoke_librarian_agent_live.py`
- `app/biblio/smoke_librarian_agent_expectations.py`

Contexte runtime/API relu en lecture seule sous discipline Sauron:

- `/opt/platform/AGENTS.md`
- `/opt/platform/doc-pipeline/query_api.py`
- `/opt/platform/doc-pipeline/db_store.py`
- DB `platform-doc-pipeline-db`, sans secret affiche.

Modele: GPT-5.5 / extra-high n'etait pas selectionnable dans cette session
Codex. Ce plan a donc ete redige avec la meilleure variante disponible dans
la session courante.

## 0. Decision courte

Existe-t-il un meilleur plan que la trajectoire actuelle ?

Oui. Le meilleur plan est de recentrer Frida Biblio sur la structure d'une
bibliotheque avant de continuer a durcir l'agent ou a multiplier les reparations
runtime.

La trajectoire precedente est recuperable, mais son centre de gravite est trop
bas: elle part des 18 cas, des smokes et des outils. Cette TODO repart des
questions canoniques qu'une bibliotheque doit pouvoir traiter. Les cas Kant,
Foucault ou Stephanus ne sont pas le canon; ils sont des trous revelateurs.

Frontieres cible:

- Bibliotheque / structure documentaire: porte le fonds, les documents, les
  oeuvres internes, sections, roles de contenu, aliases, ancres et intervalles.
- API / outils: expose des questions documentaires propres, GET-only et bornees.
- Extraction mecanique: produit le texte exact a partir d'ancres resolues.
- Renderer produit: restitue le resultat structure sans demander au LLM final
  d'imprimer le texte exact.
- Bibliothecaire LLM: comprend, choisit la methode, explore, resout, propose
  des ancres et demande les outils; il ne remplace pas la structure ni
  l'extracteur.

## 0 bis. Principe de souverainete documentaire

Le bibliothecaire LLM est le documentaliste central. Il decide au maximum dans
le cadre des outils/API disponibles: comprehension de la demande, strategie de
recherche, choix des candidats, proposition d'ancres, gestion de l'ambiguite et
formulation des limites.

Les murs deterministes doivent rester ultra fins: securite, GET-only, budgets,
coherence minimale des ancres, extraction mecanique, renderer et observabilite
content-free. Ils ne doivent pas epaissir en jugement bibliographique, ni
transformer un resultat plausible en verite produit.

La validation de pertinence finale reste dialogique et humaine: le systeme
expose ses ancres, sa provenance, son niveau de confiance et ses ambiguites.
L'utilisateur peut confirmer, corriger, demander une autre piste ou
elargir/recentrer. Le code ne doit pas pretendre fermer une question
interpretative a la place de l'utilisateur.

## 0 ter. Invariant import / parsing / normalisation

La bibliotheque doit converger vers une forme documentaire homogene quelle que
soit l'origine technique des ouvrages. Un ouvrage peut venir d'un PDF scanne
avec OCR, d'un PDF texte, d'un EPUB, d'un import manuel ou d'un autre pipeline;
cette origine varie, mais la forme documentaire finale doit rejoindre le meme
modele canonique.

Il ne doit pas exister une bibliotheque speciale OCR, une bibliotheque PDF
texte, une bibliotheque EPUB ou des structures incompatibles selon le chemin
d'entree. Les differences d'origine doivent etre conservees comme provenance,
qualite, confiance, limites OCR ou limites de parsing, jamais comme schemas
produit divergents.

Regle de normalisation:

1. Auditer la bibliotheque existante telle qu'elle est deja en base.
2. Definir le modele canonique de sortie attendu pour tous les documents:
   document, oeuvre interne, sections/chapitres, pages, paragraphes/unites
   texte, ancres stables, intervalles, roles de contenu, provenance, qualite,
   confiance et limites OCR si necessaire.
3. Normaliser la bibliotheque actuelle vers ce modele canonique.
4. Contraindre le chemin nominal des futurs ouvrages a produire ce meme modele:
   tout nouvel ouvrage doit etre projetable/validable comme `DocumentManifest`,
   ou echouer avec un `reason_code` content-free indiquant les champs
   structurels manquants.

Le premier chantier concret reste la normalisation de l'existant, parce que le
fonds deja ingere est la preuve disponible. Mais cette normalisation fige aussi
le contrat de sortie des imports futurs: EPUB, PDF texte, PDF OCR, import manuel
ou origine inconnue convergent vers le meme `DocumentManifest`. Les champs
peuvent rester `unknown`, `ambiguous` ou `derived`; la forme, elle, ne doit plus
etre incompatible ni silencieuse.

## 0 quater. Invariant memoire conversationnelle des lectures

Bibliotheque = source canonique du texte exact.

Conversation = espace ou l'extrait rendu devient visible et utilisable par le
LLM.

Memoire = politique generale de memorisation de la conversation, enrichie si
possible par les ancres et la provenance Biblio.

Tout extrait rendu mecaniquement dans le fil conversationnel devient disponible
au LLM comme contexte immediat. Le LLM peut le commenter, l'expliquer, le
comparer, le reprendre ou continuer dessus dans la conversation courante.

Biblio ne cree pas une categorie de conversation moins memorisable. Un extrait
de bibliotheque rendu a l'utilisateur est un element du dialogue. A ce titre, il
suit la politique generale de memoire conversationnelle.

Si l'utilisateur colle un texte dans le fil, il fait partie de la conversation.
Si Frida rend un extrait de livre dans le fil, il fait partie de la conversation.
Si le LLM travaille sur cet extrait dans le fil, ce travail fait partie de la
conversation. La memoire ne doit donc pas creer une exception qui exclut les
extraits Biblio rendus.

Les ancres et la provenance Biblio enrichissent cette memoire, mais ne
remplacent pas l'entree du contenu rendu dans la memoire lorsque la conversation
est memorisee. La rehydratation par ancre depuis la bibliotheque est un
complement utile pour retrouver ou verifier le texte exact; elle n'est pas un
substitut obligatoire au contenu effectivement dit dans le fil.

Cette regle ne transforme pas la lane Biblio interne, les payloads Catalogue ou
les donnees d'observabilite en auto-promotion Memory. Elle s'applique au contenu
effectivement rendu dans le fil conversationnel.

Une note de lecture, une synthese ou une interpretation peut etre memorisee
comme le reste de la conversation. Elle doit rester distinguable du texte source
par ses metadonnees, ses ancres et sa provenance, mais elle n'est pas moins
memorisable parce qu'elle vient d'une lecture Biblio.

Objet cible minimal: `BiblioReadingEvent`.

- `document_id`;
- `work_id` ou titre d'oeuvre quand disponible;
- `section_id` ou section quand disponible;
- ancres debut/fin;
- pages, paragraphes ou intervalle quand disponible;
- `content_hash` ou hash court du bloc rendu;
- type de restitution: page, pages, section, intervalle, passage trouve,
  continuation;
- demande utilisateur associee sous forme content-free ou resumee;
- statut: rendu, consulte, explique, compare, repris;
- origine `biblio_extraction`;
- role de contenu;
- provenance;
- limites;
- eventuelle note/synthese memorisable;
- lien vers le message rendu ou la trace memoire si disponible;
- indicateur explicite que le contenu rendu suit la politique memoire generale
  de la conversation.

Ce `BiblioReadingEvent` relie la conversation a la bibliotheque. Il porte les
ancres/provenance qui manquent a une trace conversationnelle ordinaire, mais ne
sert pas a retirer le texte rendu du flux memoire.

Point de vigilance courant: la lane Biblio injectee dans le prompt n'est pas
elle-meme un message conversationnel rendu, et l'etat Biblio est content-free.
En revanche, la reponse finale de Frida est sauvegardee comme message assistant
ordinaire, puis les chemins de traces et de resumes Memory traitent les messages
`user`/`assistant` eligibles. Le lot runtime devra verifier qu'un extrait Biblio
effectivement rendu a l'utilisateur n'est pas perdu entre lane interne, renderer,
message final, traces, summaries et metadonnees d'ancrage.

## 1. Probleme a corriger

Le chantier actuel a de bonnes pieces:

- client Catalogue GET-only;
- outils bornes;
- etat Biblio conversationnel;
- registry de methodes produit;
- extracteur borne;
- observabilite content-free;
- separation croissante entre resolution et restitution.

Mais il reste mal centre. Trop de succes sont encore mesures comme:

```text
outil appele + lane produite + smoke vert = produit OK
```

Ce n'est pas une preuve de bibliotheque fonctionnelle. Une bibliotheque doit
savoir repondre proprement a des familles de questions, porter les structures
necessaires a ces reponses, et rendre les limites ou ambiguites explicites.

## 2. Questions canoniques

Les questions ci-dessous deviennent le socle de pilotage. Elles remplacent les
exemples isoles comme point de depart.

### A. Inventaire / metadonnees

Questions:

- Quels ouvrages as-tu ?
- Combien d'ouvrages as-tu au total ?
- Quelle est la langue d'un ouvrage ?
- Combien de pages ?
- Quel auteur, quel titre, quel volume, quelle edition ?

Structure requise:

- `library_document`;
- metadonnees humaines et source;
- auteur(s), titre canonique, titre original, langue, type, volume, edition;
- compteurs pages, paragraphes, unites, chapitres;
- statut metadata.

Etat actuel:

- bon socle Catalogue;
- 10 documents, metadata humaines validees;
- manques: edition/volume plus riche, langue override exploitee comme signal,
  statut bibliographique normalise par type d'oeuvre.

### B. Resolution documentaire

Questions:

- Trouve tel ouvrage.
- Trouve telle oeuvre dans tel volume.
- Trouve telle section dans telle oeuvre.
- Resous une demande ambigue entre plusieurs correspondances.

Structure requise:

- distinction document physique / oeuvre interne / section;
- aliases et titres alternatifs;
- roles de contenu;
- ancre de debut et ancre de fin;
- statut `resolved`, `ambiguous`, `not_found`, `error`.

Etat actuel:

- `documents` et `document_chapters` existent;
- `work_resolver.py` essaie deja de distinguer document et oeuvre;
- manque un objet natif `work` ou un manifeste de document avec sections
  hierarchiques et bornes.

### C. Structure documentaire

Questions:

- Donne la table des matieres d'un ouvrage.
- Ou commence chaque chapitre / section ?
- Ou finit chaque chapitre / section ?
- Quel est le plan interne d'une oeuvre ?
- Quels aliases / titres alternatifs / translitterations utiles ?

Structure requise:

- arbre de sections;
- niveau hierarchique;
- `unit_start`, `unit_end`, page/para start/end si disponibles;
- relation parent/enfant;
- aliases;
- source de TOC;
- confiance et role documentaire.

Etat actuel:

- `document_chapters` porte `chapter_no`, `title`, `unit_no`, `source`;
- le debut existe souvent, la fin est deduite seulement par chapitre suivant;
- pas de hierarchie native ni d'aliases;
- pas de role positif fiable `primary_text`, `commentary`, `preface`, `note`,
  `apparatus`.

### D. Recherche

Questions:

- Trouve un passage sur tel theme.
- Cherche dans toute la bibliotheque.
- Cherche dans un ouvrage.
- Cherche dans une oeuvre.
- Cherche dans une section.
- Cherche dans un intervalle deja ancre.

Structure requise:

- recherche globale;
- recherche document-scoped;
- recherche work-scoped;
- recherche section-scoped;
- index lexical normalise;
- eventuel index semantique borne;
- resultats ancres et roles.

Etat actuel:

- `/search` existe mais reste global;
- `/search/chapters` existe mais reste title-scoped et global;
- pas de filtre API natif `doc_id`, `work_id`, `section_id`;
- FridaDev filtre parfois cote client, ce qui est acceptable comme transition
  mais pas comme contrat final.

### E. Extraction

Questions:

- Sors une page.
- Sors deux pages.
- Sors un chapitre.
- Sors un intervalle de pages.
- Sors un intervalle de chapitres.
- Sors un intervalle canonique.
- Sors un passage trouve par recherche.
- Sors un bloc exact entre deux ancres.

Structure requise:

- ancres debut/fin;
- intervalle resolu;
- budget chars/pages/paragraphes;
- extraction mecanique;
- raison de troncature si borne atteinte;
- hash court content-free en observabilite.

Etat actuel:

- `/page`, `/context`, `/locate` et `BiblioPassageExtractor` sont de bonnes
  briques;
- le chemin agent-first contourne encore parfois l'extracteur et produit une
  lane de consultation;
- le LLM final peut encore devenir l'imprimante du texte exact.

### F. Navigation lecteur

Questions:

- Page suivante / precedente.
- 10 pages plus loin / plus tot.
- Chapitre suivant / precedent.
- Continue.
- Plus haut.
- Autour de ce passage.
- Elargis / resserre l'intervalle.

Structure requise:

- etat lecteur courant;
- intervalle courant;
- ancre courante;
- operations de navigation mecaniques;
- bornes et clarifications.

Etat actuel:

- l'etat Biblio existe;
- `page_read` et `passage_context` aident;
- la navigation reste partagee entre method runtime, etat, outil et lane;
- pas encore d'objet `ReaderState` manipule par des operations simples.

### G. Provenance

Questions:

- D'ou vient ce passage ?
- Quel document ?
- Quelle oeuvre ?
- Quelle section ?
- Quelles pages ?
- Quelle reference canonique ?
- Est-ce un texte primaire, un commentaire, une preface, une note, un appareil
  critique ?

Structure requise:

- provenance stable;
- roles de contenu;
- ancre exacte;
- reference canonique si disponible;
- source de la resolution.

Etat actuel:

- ids, pages, paragraphes et milestones existent;
- le role signal est surtout negatif et faible;
- la provenance produit est fragile quand le passage vient d'une lane et non
  d'un objet resultat structure.

### H. Desambiguisation

Questions:

- J'ai plusieurs correspondances: laquelle veux-tu ?
- Cette reference est ambigue.
- Ce titre renvoie a plusieurs oeuvres.
- Cette section existe a plusieurs endroits.

Structure requise:

- liste de candidats content-free pour observabilite;
- presentation utilisateur lisible;
- choix utilisateur reappliquable a l'etat;
- pas de choix silencieux du premier resultat.

Etat actuel:

- certains statuts `ambiguous` existent;
- les smokes ne punissent pas assez les mauvais choix semantiques;
- la surface de clarification reste moins centrale que la production d'une
  lane.

### I. Ancrage / etat

Questions:

- Quel est le document courant ?
- Quelle oeuvre courante ?
- Quelle section courante ?
- Quelle ancre courante ?
- Quel intervalle courant ?
- Quel debut / fin d'un passage ?

Structure requise:

- `current_document`;
- `current_work`;
- `current_section`;
- `current_anchor`;
- `current_interval`;
- `last_result`;
- provenance et role de contenu.

Etat actuel:

- l'etat conversationnel Biblio existe et doit etre garde;
- il faut le rendre manipule par les methodes produit, pas seulement par des
  reparations runtime.

## 3. Structure documentaire minimale cible

Cette structure peut etre portee soit directement dans Catalogue au moment de
l'import, soit par un manifeste documentaire derive et versionne apres import.
La cible ne doit pas attendre que l'agent compense l'absence de structure.

### Entites minimales

`LibraryDocument`

- document physique Catalogue;
- id stable;
- titre canonique;
- auteurs;
- langue;
- type source;
- compteurs;
- statut metadata;
- source d'import.

`Work`

- oeuvre interne dans un document ou volume;
- titre canonique;
- aliases;
- auteur si different;
- volume/document parent;
- role par defaut `primary_text` ou autre;
- ancre debut/fin.

`SectionNode`

- noeud hierarchique de TOC;
- parent;
- niveau;
- titre;
- aliases;
- role;
- debut;
- fin;
- source et confiance.

`TextUnit`

- unite documentaire normalisee;
- page, section EPUB, raw unit ou paragraphe selon source;
- mapping vers page/para et raw unit quand possible.

`Anchor`

- document;
- work optionnel;
- section optionnelle;
- page;
- paragraphe;
- raw unit;
- char_offset;
- reference canonique si disponible;
- source de resolution.

`Interval`

- ancre debut;
- ancre fin;
- type: page range, section range, canonical range, search result range;
- budget;
- statut;
- raison de troncature.

`CanonicalReference`

- type: Stephanus, page, chapitre, section, autre;
- label demande;
- label resolu;
- occurrences;
- ambiguite.

`ContentRole`

- valeurs minimales:
  - `primary_text`;
  - `commentary`;
  - `preface`;
  - `introduction`;
  - `notice`;
  - `note`;
  - `apparatus`;
  - `metadata`;
  - `unknown`.

`DocumentManifest`

- projection structurelle par document;
- oeuvre(s), sections, aliases, roles, bornes;
- langue exploitable via signal court (`fr`, `de`, `en`, etc.) ou signal
  derive content-free quand la metadonnee n'est pas un code court;
- source: import, metadata humaine, backfill, correction operateur;
- validation de forme: `valid`, `valid_with_warnings` ou `invalid`, avec
  `reason_codes` content-free pour les champs obligatoires manquants;
- version et date.

### A porter des l'import ou du backfill documentaire

- extraction TOC hierarchique;
- bornes debut/fin des chapitres;
- detection des oeuvres internes dans les volumes;
- aliases de titres;
- role de contenu;
- mapping section -> page/para quand possible;
- references canoniques connues;
- qualite et confiance de chaque signal.

### A ne pas porter dans le LLM

- choix du premier hit comme verite;
- reconstruction libre d'une TOC;
- invention de bornes de fin;
- impression du texte exact;
- decision de droit generique lorsque la bibliotheque locale a un extrait borne.

## 4. API / outils minimaux

Les noms ci-dessous sont conceptuels. Ils peuvent etre routes Catalogue, wrappers
FridaDev GET-only, ou outils agentiques au-dessus de routes existantes.

### Inventaire

- `catalog_list(limit, offset, q?)`
- `catalog_count()`
- `document_metadata(document_id)`

Etat actuel: largement couvert par `/catalog` et `/metadata`.

### Resolution

- `resolve_document(query)`
- `resolve_work(document_id?, query)`
- `resolve_section(document_id, work_id?, query)`
- `resolve_canonical_reference(document_id, work_id?, label, kind?)`
- `disambiguate_candidates(candidates_ref)`

Etat actuel: partiel via `catalog`, `chapters`, `search_chapters`, `locate`.

### Structure

- `document_toc(document_id, structured=true)`
- `work_toc(document_id, work_id)`
- `section_children(section_id)`
- `section_bounds(section_id)`
- `document_manifest(document_id)`

Etat actuel: `document_chapters` donne une TOC plate avec debut, pas une
structure complete.

### Recherche

- `search_library(q, filters)`
- `search_document(document_id, q)`
- `search_work(document_id, work_id, q)`
- `search_section(section_id, q)`
- `search_interval(interval, q)`
- `search_chapters(q, filters)`

Etat actuel: `/search` et `/search/chapters` existent, mais sans filtres forts.
Le premier lot peut faire du filtrage strict cote FridaDev; le lot propre doit
enrichir l'API Catalogue.

### Extraction

- `extract_page(document_id, page_no, max_chars)`
- `extract_pages(document_id, start_page, count, max_chars)`
- `extract_section(section_id, max_chars)`
- `extract_interval(interval, max_chars)`
- `extract_between_anchors(start_anchor, end_anchor, max_chars)`
- `extract_search_hit(hit_id/context_anchor, max_chars)`

Etat actuel: partiel via `/page`, `/context`, `/locate`,
`BiblioPassageExtractor`.

### Navigation

- `reader_state_get()`
- `reader_state_update(anchor|interval)`
- `navigate_next_page(state, count)`
- `navigate_previous_page(state, count)`
- `navigate_next_section(state)`
- `navigate_previous_section(state)`
- `expand_interval(state, mode)`
- `shrink_interval(state, mode)`

Etat actuel: partiel et distribue.

### Provenance

- `explain_anchor(anchor)`
- `explain_interval(interval)`
- `content_role(anchor|section)`
- `source_trace(result_id)`

Etat actuel: a renforcer autour du resultat structure.

## 5. Extraction mecanique

Regle dure:

```text
LLM -> variables structurees
API/outils -> ancres et donnees documentaires
extracteur -> texte exact
renderer -> restitution produit
```

Le LLM ne doit pas:

- produire lui-meme un extrait exact;
- recoller des bouts de texte comme s'il les avait extraits;
- decider seul qu'une demande est impossible pour raisons juridiques si une
  extraction locale bornee est disponible;
- transformer une lane de consultation en citation exacte.

L'extracteur doit:

- refuser les ancres ambigues;
- refuser les intervalles incoherents;
- appliquer des budgets explicites;
- produire un `BiblioAnswerObject`;
- porter les ancres, la provenance, les roles, les limites et les hashes courts;
- permettre au renderer d'afficher le texte sans re-generation.

Le renderer doit:

- afficher les blocs exacts bornes;
- afficher les limites;
- afficher les choix ou ambiguites;
- ne jamais dependre d'un LLM pour rendre le texte exact.

## 6. Place exacte du bibliothecaire LLM

Le bibliothecaire LLM reste aussi souverain que possible pour:

- comprendre la demande naturelle;
- choisir la methode documentaire;
- exploiter l'historique recent et l'etat Biblio;
- proposer les requetes de resolution;
- comparer les candidats;
- demander une clarification;
- choisir les outils API;
- proposer des ancres candidates.

Il ne doit plus etre souverain pour:

- inventer la structure absente;
- valider un passage exact sans extracteur;
- imprimer le texte exact;
- choisir silencieusement un hit ambigu;
- surclasser les budgets, roles, bornes ou garde-fous;
- transformer un commentaire en texte primaire parce que le titre matche.

Le deterministe doit etre limite a:

- validation schema;
- GET-only;
- budgets;
- coherence des ancres;
- extraction mecanique;
- renderer;
- observabilite;
- fallback propre;
- refus ou clarification quand la structure ne suffit pas.

## 7. Ce qu'on garde, ce qu'on requalifie

Garder:

- `catalogue_client.py` comme frontiere GET-only;
- `librarian_tools.py` comme base d'outils, a scinder plus tard;
- `librarian_planner.py` comme boucle bornee;
- `conversation_state.py` et l'etat Biblio;
- `passage_extractor.py` comme noyau d'extraction mecanique;
- observabilite content-free;
- registry de methodes produit, a restructurer autour des questions canoniques.

Requalifier:

- les 18 cas comme exemples/regressions, pas comme canon principal;
- `frida-biblio-refonte.md` comme roadmap de transition centree cas;
- les smokes existants comme preuves de plomberie;
- `passage_search_in_work` comme famille trop large a eclater;
- `final_restitution_ok` comme preuve insuffisante si aucune reponse finale
  rendue n'est verifiee.

Jeter a terme:

- reparations de cas par regex qui redeclarent une intelligence bibliothecaire;
- lanes de consultation utilisees comme resultat final exact;
- choix de premier resultat sans objet d'ambiguite;
- code mort des chemins legacy une fois les methodes migrees.

## 7 bis. Lot 0 - Gel de verite livre

Date de gel: 2026-06-03.

Portee: docs/audit/proofs uniquement. Ce lot ne ferme ni le manifeste
documentaire, ni l'API cible, ni l'extraction mecanique, ni le renderer, ni le
nettoyage `app/biblio/`.

### Definitions de validation

Preuve de plomberie:

- un agent a appele un outil;
- un endpoint Catalogue a repondu;
- une lane Biblio existe dans le prompt;
- un JSONL contient `status=agent_first_executed`;
- un smoke strict passe sur des noms d'outils, endpoint kinds ou reason codes;
- `agent_used_for_response=true` et `agent_product_response_changed=true` sont
  observes sans verifier la reponse finale rendue.

Une preuve de plomberie prouve que la tuyauterie tourne. Elle ne prouve pas que
la bibliotheque a repondu correctement.

Preuve produit:

- la question canonique visee est identifiee;
- le document, l'oeuvre, la section et le role de contenu sont corrects;
- les ancres de debut/fin ou l'intervalle courant sont corrects;
- l'extraction mecanique ou la clarification est effectivement rendue cote
  utilisateur;
- la preuve distingue lane interne, reponse finale, memoire si concernee,
  provenance et metadonnees d'ancrage;
- le statut de sortie est explicite: `resolved`, `ambiguous`, `not_found`,
  `clarification` ou `error`;
- l'artefact live est content-free: pas de secret, pas de prompt brut, pas de
  payload Catalogue brut, pas de contenu d'ouvrage long.

Faux vert:

- bons outils appeles, mauvaise ancre;
- commentaire ou appareil critique trouve a la place du texte primaire;
- page lue, mais section demandee non prouvee;
- lane interne confondue avec reponse utilisateur;
- `final_restitution_ok` projete sans verification du message final rendu;
- fallback deterministe masquant un echec agentique;
- methode produit incoherente avec le `case_id`;
- exemple Kant/Foucault/Stephanus declare "regle" alors que la structure
  canonique reste non prouvee.

Validation insuffisante:

- endpoint appele seul;
- outil appele seul;
- lane produite seule;
- smoke vert seul;
- reason code attendu seul;
- hash ou longueur de message sans verifier la semantique rendue;
- `final_restitution_ok=true` sans preuve content-free associee du message final
  et du rendu utilisateur.

### Canon prioritaire de validation

Les questions canoniques restent le canon de validation prioritaire:

- inventaire / metadonnees;
- resolution documentaire;
- structure / TOC;
- recherche scoped;
- extraction;
- navigation lecteur;
- provenance;
- desambiguisation / clarification;
- ancrage / etat;
- import / parsing / normalisation;
- memoire conversationnelle des lectures.

Les exemples Kant/Foucault/Stephanus restent des regressions severes. Ils ne
remplacent pas ces questions canoniques et ne suffisent pas a fermer un lot
structurel.

### Audit content-free des artefacts existants

Artefacts requalifies comme preuves de plomberie:

| Artefact | Cases / statut | Methode / outils | Verdict |
| --- | --- | --- | --- |
| `app/docs/states/baselines/biblio-smokes/agent-first-full-20260601T181903Z.jsonl` | P01-P18, `agent_first_executed`, `met:18` | outils/endpoints observes, lanes | Plomberie verte historique; pas de reponse finale. |
| `app/docs/states/baselines/biblio-smokes/agent-first-full-post-truth-fix-20260601T185215Z.jsonl` | P01-P18, `agent_first_executed`, `met:18` | methodes/outils mieux exposes | Plomberie avancee; contient encore des reparations/fallbacks. |
| `app/docs/states/baselines/biblio-smokes/agent-gpt52-live-20260602T121652Z.jsonl` | `GPT52-LIVE-01` | `catalog_search` | Preuve provider/outil seulement. |
| `app/docs/states/baselines/biblio-smokes/p03-agent-smoke-20260601T150723Z.jsonl` | P03, `not_used`, runtime failed | plan agent observe | Preuve agent/planner, pas preuve produit. |

Artefacts mixtes a ne plus utiliser comme preuve stricte isolee:

| Artefact | Cases / statut | Methode / outils | Verdict |
| --- | --- | --- | --- |
| `app/docs/states/baselines/biblio-smokes/lot-e-p03-p18-final-20260603T123538Z.jsonl` | P03-P18, `met:16` | methodes P03-P18, GET-only | Bonne plomberie agent-first et case/method, mais pas de reponse finale. |
| `app/docs/states/baselines/biblio-smokes/p03-agentic-20260603T110117Z.jsonl` -> `p18-agentic-20260603T122300Z.jsonl` | P03-P18 unitaires, majoritairement `met` | outils par cas | Preuves unitaires utiles; pas fermeture produit globale. |
| `app/docs/states/baselines/biblio-smokes/r1-navigation-live-20260602T082355Z.jsonl` | navigation, `navigation_executed` | `page_read`, `passage_context` | Preuve de primitives navigation, pas validation lecteur finale. |
| `app/docs/states/baselines/biblio-smokes/r2-named-document-page-navigation-20260602T112708Z.jsonl` | navigation nommee, `navigation_executed`/`needs_clarification` | `page_read` | Preuve partielle navigation document nomme. |
| `app/docs/states/baselines/biblio-smokes/r3-truth-and-document-resolution-20260602T130112Z.jsonl` | resolution/truth, `resolved`/`extracted`/`ambiguous` | `resolve_work`, `extract_range`, recherche | Preuve partielle utile sur statuts, pas renderer. |
| `app/docs/states/baselines/biblio-smokes/stephanus-live-check-20260602T061059Z.jsonl` et `stephanus-live-check-20260602T063133Z.jsonl` | P04/P05, `met` | `catalog_search`, `passage_context`, endpoints | Regression Stephanus partielle; pas preuve canonique stable. |

Artefacts faux verts ou preuves insuffisantes nommees:

| Artefact | Cases / statut | Methode / outils | Verdict |
| --- | --- | --- | --- |
| `app/docs/states/baselines/biblio-smokes/lot-e-p12-p18-readiness-20260603T100407Z.jsonl` | P12-P15 failed/partial, P16-P18 met | context/search | Gaps stateful et origine encore visibles. |
| `app/docs/states/baselines/biblio-smokes/p10-agentic-rerun-20260603T131029Z.jsonl` | P10, failed | `passage_extract_canonical_range` | Faux vert bloque par mismatch case/method. |
| `app/docs/states/baselines/biblio-smokes/p14-agentic-rerun-stateful-20260603T131342Z.jsonl` | P10 failed, P11-P14 met | stateful context/page | Mixte; P10 prouve une regression de methode. |
| `app/docs/states/baselines/biblio-smokes/p14-agentic-isolated-from-stateful-20260603T133545Z.jsonl` | P14 met isole | `passage_context` | Preuve insuffisante: follow-up sans preuve complete du fil stateful. |
| `app/docs/states/baselines/biblio-smokes/stephanus-interval-diagnostic-20260603T134500Z.jsonl` | `agent_first_executed` | methode canonical range | Diagnostic incomplet, pas preuve produit. |

Artefacts produit partiels ou solides seulement dans leur perimetre:

| Artefact | Cases / statut | Methode / outils | Verdict |
| --- | --- | --- | --- |
| `app/docs/states/baselines/biblio-smokes/kant-internal-section-two-pages-diagnostic-20260603T135200Z.jsonl` | diagnostic Kant interne | plan agent-first | Diagnostic structurel, pas preuve finale. |
| `app/docs/states/baselines/biblio-smokes/kant-internal-section-two-pages-live-final-20260603T144926Z.jsonl` | `KANT_INTERNAL_SECTION_TWO_PAGES`, `met`, `final_restitution_ok=true` | `catalog_search`, `document_open_summary`, `search_chapters`, `page_read` | Preuve partielle utile du chemin section interne -> lectures de pages; non suffisante comme preuve produit finale tant qu'aucune preuve content-free du message final rendu n'est conservee. |
| `app/docs/states/baselines/biblio-smokes/radical-audit-biblio-live-20260603T152425Z.jsonl` | Kant/Foucault/Stephanus live audit | outils et message hashes | Audit live content-free; classe des risques et regressions, pas cloture. |

### Exigences pour preuves futures

- Les smokes doivent dire s'ils valident une lane interne ou une reponse finale.
- Une extraction exacte doit prouver le renderer ou le message final rendu.
- Un cas de recherche doit prouver document/oeuvre/section/role quand ces
  dimensions comptent.
- Un follow-up doit prouver l'etat conversationnel, pas seulement une nouvelle
  lane.
- `final_restitution_ok` doit etre accompagne d'une preuve content-free de
  reponse finale rendue, ou rester une projection.
- Les artefacts live doivent rester sans secret, sans prompt brut et sans long
  contenu d'ouvrage.
- Les preuves doivent etre indexees d'abord par questions canoniques, puis par
  regressions P01-P18 ou Kant/Foucault/Stephanus.

## 8. Nettoyage ultra strict du module Biblio

Le cleanup est un critere de fermeture, pas un embellissement.

### Couches finales attendues

`app/biblio/catalogue/`

- client GET-only;
- schemas de reponses compactes;
- wrappers de recherche filtree si l'API Catalogue n'est pas encore enrichie.

`app/biblio/structure/`

- manifestes documentaires;
- anchors;
- intervals;
- roles;
- provenance.

`app/biblio/methods/`

- methodes produit executees;
- pas de regex de reconnaissance;
- chaque methode a entrees, preconditions, outils autorises, resultat.

`app/biblio/extraction/`

- extraction mecanique;
- page, pages, section, intervalle, range canonique, search hit.

`app/biblio/rendering/`

- renderer produit;
- messages de clarification;
- restitution des extraits exacts bornes.

`app/biblio/agent/`

- appel OpenRouter/JSON;
- prompt/schema agent;
- conversion plan agent -> method request.

`app/biblio/runtime/`

- orchestration de tour;
- etat;
- fallback;
- observabilite.

`app/biblio/smokes/`

- tests live content-free;
- validation produit par questions canoniques;
- pas de faux vert par simple lane.

### Fichiers a requalifier

- `chat_runtime.py`: garder orchestration, retirer projection produit et
  reparations lourdes.
- `library_runtime.py`: legacy/fallback a reduire puis supprimer si remplace.
- `librarian_method_runtime.py`: convertir en executeur de methodes ou supprimer
  les completions opportunistes.
- `librarian_product_methods.py`: passer de matrice P01-P18 a familles de
  questions canoniques.
- `librarian_tools.py`: scinder outils Catalogue, normalisation, mapping payload.
- `librarian_agent_first.py`: retirer le rendu de texte, produire un resultat
  structure ou une consultation non exacte.
- `work_resolver.py`: remplacer par resolution document/work/section appuyee
  sur manifestes.
- `passage_extractor.py`: garder mais extraire par responsabilites si la taille
  continue a grossir.
- `smoke_librarian_agent_*`: rebatir les criteres autour de bonnes ancres,
  bons roles, extraction mecanique et rendu final.

### Regles de suppression

- aucun module legacy ne reste parce qu'il est "peut-etre utile";
- chaque chemin restant doit etre appele par une methode active ou un test de
  fallback documente;
- tout parseur local de cas doit etre justifie comme garde-fou, pas comme
  bibliothecaire;
- aucun fichier Biblio ne doit devenir un grab-bag au-dela des limites de
  responsabilite.

## 9. Plan de migration

### Lot 0 - Gel de verite

- [x] Requalifier les smokes verts actuels en preuves de plomberie.
- [x] Lister les preuves produit insuffisantes sans les supprimer.
- [x] Interdire toute nouvelle validation fondee seulement sur endpoint/lane.
- [x] Fixer la matrice des questions canoniques comme entree de validation.

Critere de fermeture: aucun document de travail actif ne pretend que les 18 cas
sont une preuve finale de bibliotheque fonctionnelle. Lot 0 ferme le gel de
verite seulement; il ne ferme aucun lot structurel suivant.

### Lot 1 - Manifeste documentaire minimal

- [x] Definir `DocumentManifest`, `Work`, `SectionNode`, `Anchor`, `Interval`,
      `ContentRole`.
- [x] Auditer les chemins d'entree deja presents dans le fonds existant: PDF
      scanne/OCR, PDF texte, EPUB, import manuel ou autre pipeline detecte.
- [x] Verifier comment ces chemins remplissent aujourd'hui `documents`,
      `pages`, `paragraphs`, `raw_units`, `document_chapters` et `milestones`.
- [x] Verifier si pages, paragraphes, chapitres, TOC et ancres sont comparables
      entre origines, ou si certains imports produisent une structure plus
      pauvre, instable ou non homogene.
- [x] Identifier ce qui est obligatoire, facultatif, inconnu ou derive dans le
      manifeste canonique.
- [x] Garder l'origine technique comme provenance/qualite/confiance/limites,
      sans laisser cette origine produire des structures Biblio incompatibles.
- [x] Produire un manifeste derive pour chaque document existant, sans changer
      le runtime chat.
- [x] Marquer explicitement les roles inconnus.
- [x] Ajouter les bornes de fin de section par chapitre suivant quand possible.
- [x] Identifier les oeuvres internes dans les volumes complexes seulement si
      la TOC le permet honnetement.
- [x] Porter une langue exploitable dans le manifeste: valeur courte quand elle
      existe (`fr`, `de`, `en`, etc.), sinon signal derive content-free.
- [x] Ajouter un validateur de forme `DocumentManifest`: un document peut rester
      incomplet bibliographiquement, mais il ne peut plus sortir du format commun
      sans `reason_code`.
- [x] Rendre la baseline Lot 1 rejouable de bout en bout: le runner collecte
      lui-meme l'audit DB content-free quand `DOC_PIPELINE_DATABASE_URL`,
      `DATABASE_URL` ou `--database-url` est disponible.
- [x] Poser le contrat d'import obligatoire: un ouvrage ajoute demain par le
      chemin nominal doit produire un `DocumentManifest` valide ou
      `valid_with_warnings`, ou apparaitre comme echec content-free avec raison
      explicite.
- [x] Verrouiller la baseline: `valid` et `valid_with_warnings` passent;
      `invalid` devient une failure `manifest_validation_failed` et la commande
      sort non-zero.
- [x] Verrouiller le chemin nominal d'import doc-pipeline: le payload normalise
      et les tables reellement ecrites passent par un quality gate content-free;
      `accepted` couvre `valid` / `valid_with_warnings`, `invalid` bloque
      l'import avant succes silencieux.

Livraison Lot 1, 2026-06-03:

- code: package `app/biblio/structure/` et runner content-free
  `app/biblio/document_manifest_baseline.py`;
- test: `app/tests/test_biblio_document_manifest.py`;
- artefact:
  `app/docs/states/baselines/biblio-manifests/frida-biblio-document-manifest-lot1-20260603T173615Z.json`;
- artefact correctif rejouable:
  `app/docs/states/baselines/biblio-manifests/frida-biblio-document-manifest-lot1-correctif-20260603T183445Z.json`;
- commande OVH rejouable, sans afficher l'URL DB:
  `DB_URL=$(docker exec platform-doc-pipeline-api sh -lc 'printf %s "$DOC_PIPELINE_DATABASE_URL"') && docker run --rm --network doc-pipeline_default -v /opt/platform/fridadev:/repo -w /repo -e PYTHONPATH=app -e DOC_PIPELINE_DATABASE_URL="$DB_URL" platform-fridadev-app:local python -m biblio.document_manifest_baseline --base-url http://platform-doc-pipeline-api:8090 --output app/docs/states/baselines/biblio-manifests/frida-biblio-document-manifest-lot1-correctif-<YYYYMMDDTHHMMSSZ>.json`;
- resultat: 10 documents vus, 10 manifestes produits, 0 echec;
- fonds existant: 5 EPUB / `sections`, 5 PDF / `pages`;
- tables DB auditees: 10 `documents`, 4837 `pages`, 101421
  `paragraphs`, 378034 `raw_units`, 973 `document_chapters`, 26492
  `milestones`;
- `raw_units`: presents pour tous les documents; le runner correctif les
  collecte lui-meme par audit DB content-free quand la DB documentaire est
  joignable;
- langue: 10 documents avec signal de langue connu cote DB; 6 signaux courts
  portes directement, 4 signaux derives content-free parce que la metadonnee
  n'est pas un code court;
- TOC: 5 documents `epub_toc`, 4 `llm_fallback`, 1 `pdf_outline`;
- sections: 973 sections projetees, 973 bornes de fin derivees par chapitre
  suivant ou fin de document;
- roles: 61 signaux faibles `introduction`, 912 roles `unknown`; aucun
  `primary_text` n'est invente;
- references canoniques: milestones Stephanus dans 9 documents; 1 document sans
  milestone;
- validation: 10 manifestes `valid_with_warnings`, 0 `reason_code` invalidant;
  warnings attendus: roles incomplets, oeuvres internes inconnues, origine PDF
  encore ambigue, 1 document sans reference canonique;
- verrou final: un manifeste `invalid` n'est pas accepte comme manifeste
  produit; il est reporte dans `failures` avec `validation_reason_codes`, et le
  runner sort avec code non-zero;
- usine d'entree: `/opt/platform/doc-pipeline` porte un gate d'import minimal:
  `validate_import_payload_quality()` controle le payload normalise avant DB,
  `validate_ingested_document_quality()` controle apres ecriture SQL, avant
  commit; si le document manque pages, paragraphes, unites ou `raw_units`,
  l'import echoue avec reason codes content-free;
- runtime import: le worker `platform-doc-pipeline` a ete reconstruit/recree
  de facon ciblee pour embarquer ce gate; DB, API Catalogue, Caddy et FridaDev
  runtime chat n'ont pas ete redemarres;
- preuve d'entree reelle: un EPUB UQAM fourni le 2026-06-03 a ete importe par
  le worker nominal avec `input_kind=epub`, 2 unites, 1071 paragraphes, 3951
  `raw_units`, 28 chapitres, `quality_gate=accepted` et
  `validation=valid_with_warnings`; une fixture cassee sans unites/pages/
  paragraphes/`raw_units` retourne `invalid` avec reason codes content-free;
- baseline rejouee apres cet import reel: 11 documents vus, 11 manifestes
  produits, 0 failure, 11 `valid_with_warnings`;
- limites assumees: les PDF ne distinguent pas encore PDF texte / PDF scanne
  OCR dans `source_type`; les EPUB exposent leurs sections via la semantique
  actuelle `page_no`; les oeuvres internes complexes ne sont pas inventees.

Critere de fermeture: les documents existants ont maintenant une projection
structurelle inspectable, versionnee, validee et sans texte long expose. Cette
projection normalise le fonds actuel vers un modele canonique unique et devient
le contrat de sortie des imports futurs: si un ouvrage entre demain par le
pipeline nominal, il doit etre projetable/validable comme `DocumentManifest`.
S'il manque des champs minimaux, l'echec doit etre content-free et explicite;
il ne doit pas disparaitre dans une structure incompatible ni dans un smoke vert
de baseline. Lot 2 reste interdit si le gate d'entree n'est pas actif sur le
worker d'import nominal.

### Lot 2 - API/outils de bibliotheque minimale

- [x] Ajouter ou wrapper `search_document`.
- [x] Ajouter ou wrapper `search_work`.
- [x] Ajouter ou wrapper `search_section`.
- [x] Ajouter `resolve_work` et `resolve_section` outilles par manifeste.
- [x] Ajouter `section_bounds`.
- [x] Garder GET-only et budgets explicites.

Critere de fermeture: le bibliothecaire peut poser les questions canoniques
sans passer par une recherche globale puis tri opportuniste.

Livraison Lot 2, 2026-06-04:

- code: `app/biblio/librarian_library_tools.py` porte les primitives haut
  niveau; `app/biblio/librarian_tools.py` garde la registry et delegue les
  outils Lot 2;
- outils exposes au bibliothecaire: `search_document`, `search_work`,
  `search_section`, `resolve_work`, `resolve_section`, `section_bounds`;
- API utilisee: uniquement routes Catalogue GET deja existantes:
  `GET /catalog`, `GET /doc/{id}/metadata`, `GET /doc/{id}/chapters`;
- `search_document` reste une recherche documentaire bornee dans le catalogue,
  pas une recherche plein texte de passages;
- `search_section`, `resolve_section` et `section_bounds` exigent un
  `document_id` et consultent la TOC du document cible; elles ne passent pas par
  une recherche globale de chapitres suivie d'un filtrage opportuniste;
- `resolve_work` / `resolve_section` retournent des statuts structurels:
  `resolved`, `ambiguous` ou `not_found`, avec observabilite content-free;
- `section_bounds` renvoie les ancres debut/fin derivees par manifeste quand
  une section unique est resolue;
- contrat agent: validation JSON, schema OpenRouter et methodes produit
  acceptent ces nouveaux outils GET-only;
- preuves: `python3 -m unittest discover app/tests/unit/biblio` -> 363 tests
  OK; tests cibles sur resolution section scoped, bornes derivees, ambiguite,
  absence, et absence de recherche globale opportuniste presentee comme
  resolution scoped.

Limite volontaire: les primitives Lot 2 normalisent l'acces documentaire pour
le bibliothecaire, mais ne livrent pas encore le renderer produit ni
l'extraction mecanique exacte du Lot 3.

### Lot 2 bis - Enrichissement structurel / aliases / oeuvres internes

- [x] Enrichir `DocumentManifest` avec des aliases exploitables:
      titres alternatifs, transliterations, titres courts, titres d'oeuvres
      internes et titres de sections.
- [ ] Distinguer plus fortement document physique / volume, oeuvre interne,
      partie / livre / section / chapitre.
- [ ] Distinguer plus fortement texte primaire, commentaire, preface,
      introduction, notes, appareil critique et role inconnu.
- [ ] Porter une hierarchie de sections quand elle est disponible ou derivable
      honnetement, sans inventer une structure absente.
- [ ] Produire des bornes plus fiables: section -> page, section -> paragraphe
      ou raw unit si disponible, oeuvre interne -> debut / fin.
- [x] Ajouter des reason codes content-free pour les limites structurelles,
      par exemple `work_alias_missing`, `internal_work_unresolved`,
      `section_alias_missing`, `primary_text_role_unknown` ou noms plus justes.
- [x] Prouver content-free qu'une section interne connue peut se resoudre par
      alias quand l'alias existe dans la structure.
- [ ] Prouver content-free qu'une oeuvre interne dans un volume peut se
      resoudre sans confondre texte primaire et commentaire quand les roles le
      permettent.
- [x] Prouver qu'une requete bibliographique ambigue reste `ambiguous` ou
      demande clarification au lieu de fabriquer une certitude.
- [x] Interdire les preuves contenant texte long d'ouvrage, prompt brut, titre
      ou auteur brut non necessaire, payload brut, secret ou URL sensible.

Limite a figer: Lot 2 expose les outils minimaux (`search_document`,
`search_work`, `search_section`, `resolve_work`, `resolve_section`,
`section_bounds`), mais ces outils ne suffisent pas si la structure
documentaire reste pauvre. Des echecs severes comme une section interne connue
dans un volume Kant montrent le manque d'aliases, d'oeuvres internes, de
sections hierarchiques, de roles de contenu, de mapping section -> page/para et
de distinction texte primaire / commentaire. Ces exemples restent des
regressions severes, pas le canon conceptuel du chantier.

Invariant: le bibliothecaire LLM reste souverain dans le cadre de l'API. Il
comprend la demande, explore, compare, choisit les outils et propose les
ancres. Le deterministe reste un mur mince: GET-only, budgets, validation de
forme, refus des routes dangereuses, observabilite content-free et extraction
mecanique quand les ancres sont donnees. Lot 2 bis ne doit pas devenir un
parseur local de formulations, une pile de regex Kant/Foucault/Stephanus, ni
une confusion entre les 18 cas historiques et 18 outils. La structure doit
aider le bibliothecaire, pas le remplacer. Quand la pertinence bibliographique
reste interpretative ou ambigue, le systeme expose l'ambiguite ou demande
clarification; le code ne doit pas faire semblant d'une certitude structurelle
absente.

Critere de fermeture: le bibliothecaire dispose d'une structure documentaire
assez riche pour resoudre des aliases, oeuvres internes, sections
hierarchiques, roles de contenu et bornes sans basculer vers une recherche
globale opportuniste ni vers un jugement bibliographique deterministe. Les
preuves restent content-free et distinguent clairement structure disponible,
structure derivee, structure ambigue et structure absente.

Livraison premier cran Lot 2 bis, 2026-06-04:

- `DocumentManifest` porte maintenant `AliasSignal` sur `Work` et
  `SectionNode`;
- les aliases sont derives conservativement depuis les champs deja disponibles:
  titres Catalogue/metadonnees, titres de TOC, `chapter_title`, `label`,
  `short_title`, `aliases`, `title_aliases`, `alternative_titles`;
- une transliteration accent-stripped est ajoutee seulement a partir d'un alias
  existant; aucun dictionnaire Kant/Foucault/Stephanus ni synonyme externe
  n'est introduit;
- la projection manifeste reste content-free: `AliasSignal.to_dict()` expose
  count, state, source et hashes courts, pas les labels bruts;
- `search_section`, `resolve_section`, `section_bounds` et les candidats
  `section_scope` de `search_work` matchent les aliases quand ils existent,
  sans passer par `search_chapters` global;
- les aliases bruts ne sont pas retournes dans `result.items` ni dans
  l'observabilite; seuls `alias_count`, `alias_state` et `alias_source` sont
  visibles;
- `resolve_section` / `section_bounds` retournent `section_alias_missing`
  lorsqu'une TOC existe mais qu'aucun alias/titre scoped ne resout la requete;
- `resolve_work` retourne `internal_work_unresolved` dans un document connu et
  `work_alias_missing` hors document quand la resolution d'oeuvre echoue;
- l'ambiguite reste `ambiguous` si plusieurs sections matchent le meme alias;
- preuves: tests cibles sur alias de section, alias ambigu, alias absent,
  `section_bounds` par alias, absence de recherche globale opportuniste et
  manifeste content-free.

Limites encore ouvertes: detection forte des oeuvres internes, hierarchie
multi-niveau, roles `primary_text` / commentaire vraiment fiables, mapping
section -> paragraphe/raw unit plus fin et bornes d'oeuvre interne debut/fin.
Ces limites restent des dettes structurelles, pas des cas a reparer par regex.

### Lot 3 - Answer object et renderer

- [x] Introduire `BiblioAnswerObject`.
- [x] Porter document, oeuvre, section, ancre, intervalle, role, provenance,
      limites, truth level et status.
- [x] Brancher un renderer produit minimal pour statuts et textes deja
      mecaniquement presents.
- [x] Bloquer les faux exacts dans le renderer quand le statut structurel ne
      permet pas de rendre.

Critere de fermeture Lot 3 strict: l'objet de verite et le renderer minimal
existent. Le verrou du message assistant final est porte par L3A1.

Livraison premier cran Lot 3, 2026-06-04:

- code: `app/biblio/answer_object.py`;
- objet: `BiblioAnswerObject` avec `status`, `product_method`, `case_id`,
  `document_id`, `work_id` / `work_state`, `section_id` / `section_state`,
  `anchors`, `interval`, `content_role`, `provenance`, `limits`,
  `reason_codes`, `truth_level`, `source_tool_names` et `render_mode`;
- statuts minimaux: `ready`, `ambiguous`, `not_found`,
  `needs_clarification`, `error`;
- render modes minimaux: `structured_status`, `exact_excerpt`,
  `blocked_exact`;
- renderer: `render_biblio_answer_object()` produit un bloc mecanique
  `[RESULTAT BIBLIO STRUCTURE]` qui rend le statut, la provenance courte,
  l'intervalle et, seulement si disponible, un texte exact deja present dans
  `context_text` ou `page_text`;
- garde-fou: `ambiguous`, `not_found`, `section_alias_missing`,
  `internal_work_unresolved`, `work_alias_missing` et autres manques
  structurels ne deviennent pas des extraits exacts;
- integration: la voie agent-first construit l'objet depuis le tool loop et
  insere le rendu minimal dans la consultation Biblio; la lane interne, l'objet
  structure et le rendu sont maintenant distinguables;
- observabilite: `to_observability()` reste content-free, avec hashes/compteurs
  pour les textes exacts et sans prompt brut ni payload brut.

Important: Lot 3 commence pendant que Lot 2 bis reste ouvert. Le renderer ne
remplace pas la richesse structurelle manquante: si aliases, oeuvres internes,
roles ou bornes sont insuffisants, l'objet expose la limite et le renderer
bloque la pseudo-restitution exacte. Ce premier cran ne ferme pas encore toute
l'extraction mecanique ni, a lui seul, la surface finale utilisateur; il
installe le guichet de verite de sortie.

### Lot 3.1 / L3A1 - Verrou du message assistant final

INVARIANT L3A1: LE DETERMINISME NE JUGE JAMAIS LA PERTINENCE SEMANTIQUE D'UNE REPONSE BIBLIO. SEUL LE BIBLIOTHECAIRE LLM DECIDE DOCUMENTAIREMENT. LE DETERMINISME VERIFIE UNIQUEMENT LE CONTRAT TECHNIQUE DE RESTITUTION: ANCRE PRESENTE, TEXTE MECANIQUE PRESENT, STATUT COHERENT, ABSENCE DE FAUX EXTRAIT, BUDGETS, GET-ONLY ET OBSERVABILITE CONTENT-FREE.

- [x] Requalifier Lot 3: objet de verite + renderer minimal, pas verrou final
      complet a lui seul.
- [x] Ajouter un verrou technique de restitution finale
      `BiblioFinalResponseLock`.
- [x] Autoriser le message assistant final seulement si le rendu Biblio respecte
      son contrat technique: statut connu, statut/mode coherents, hash et
      longueur du texte exact concordants quand un texte exact est rendu.
- [x] Court-circuiter `run_llm_exchange()` quand un rendu Biblio final autorise
      existe, afin que le message assistant final corresponde au rendu Biblio
      et ne soit pas recopie ou reformule librement par le LLM final.
- [x] Conserver la persistance conversationnelle, Memory, Identity et
      `AssistantText` sur ce message final rendu.
- [x] Exposer content-free la separation lane Biblio interne /
      `BiblioAnswerObject` / `BiblioRenderedAnswer` / message assistant final.

Livraison L3A1, 2026-06-04:

- `app/biblio/answer_object.py` ajoute `BiblioFinalResponseLock`;
- `app/biblio/chat_runtime.py` transporte `answer_object`, `rendered_answer` et
  `final_response_lock` dans `BiblioChatResult`, et enrichit l'observabilite
  content-free;
- `app/core/chat_llm_flow.py` ajoute `AssistantResponseOverride`, surface
  generique de message assistant final deja autorise par un composant produit;
- `app/core/chat_service.py` convertit un `BiblioFinalResponseLock` autorise en
  override assistant final;
- l'override n'appelle pas OpenRouter, ne demande pas au LLM final de recopier
  le texte exact, et persiste le message comme assistant final normal;
- le verrou ne lit ni la demande utilisateur, ni les titres bruts, ni les
  passages pour juger de leur pertinence. Il controle seulement la coherence
  technique du rendu deja produit par Biblio.

Limite L3A1: le verrou final ne rend pas la structure documentaire plus riche,
ne resout pas les ambiguïtés et ne termine pas le Lot 4 d'extraction mecanique
complete. Si le bibliothecaire fournit une mauvaise ancre mais techniquement
coherente, le verrou ne corrige pas le sens: il expose seulement la sortie
structuree autorisee. La validation de pertinence documentaire reste
bibliothecaire puis dialogique/humaine.

### Lot 3 bis - Memoire conversationnelle des lectures

LOT 3 BIS: UN EXTRAIT BIBLIO EFFECTIVEMENT RENDU DANS LE MESSAGE ASSISTANT FINAL ENTRE DANS LA CONVERSATION COMME N'IMPORTE QUEL AUTRE CONTENU ASSISTANT. MEMORY NE DOIT PAS L'EXCLURE PARCE QU'IL VIENT DE BIBLIO. LES ANCRES ET LA PROVENANCE SONT UN COMPLEMENT, PAS UN SUBSTITUT AU TEXTE RENDU.

- [x] Documenter la frontiere entre lane Biblio interne, extrait rendu dans le
      fil et contenu effectivement memorise.
- [x] Verifier la politique reelle conversation -> traces Memory: messages `user`,
      messages `assistant`, messages interrompus, messages deja `embedded`,
      `message.meta`; summaries et retrieval restent sous politique generale
      Memory, sans exception Biblio.
- [x] Poser que toute conversation est candidate a la memoire selon les regles
      generales de Memory.
- [x] Poser que les extraits Biblio rendus dans la conversation ne sont pas
      exclus par defaut.
- [x] Poser que les citations, extraits, commentaires, explications et reprises
      Biblio entrent comme contenu conversationnel normal quand ils sont
      effectivement rendus dans le fil.
- [x] Definir `BiblioReadingEvent` comme enrichissement d'ancrage/provenance,
      pas comme substitut sans texte au contenu rendu.
- [x] Conserver en complement document_id, oeuvre, section, ancres, pages, hash,
      provenance, role de contenu, origine `biblio_extraction` et limites.
- [x] Faire de la rehydratation par ancres depuis la bibliotheque un complement
      de verification/recuperation, pas un substitut obligatoire a la memoire du
      texte effectivement dit.
- [x] Distinguer texte source rendu, note de lecture, synthese et interpretation
      par metadonnees et provenance, sans les rendre moins memorisables.
- [x] Auditer les chemins runtime concernes: lane Biblio, reponse assistant,
      `message.meta`, traces Memory, et frontiere avec resumes, retrieval et
      documents actifs de conversation.
- [x] Verifier si un extrait Biblio rendu peut etre perdu entre lane interne,
      renderer, reponse finale, persistence conversationnelle et Memory.
- [x] Definir les preuves futures qui distinguent extrait rendu dans la
      conversation, contenu effectivement memorise, metadonnees
      d'ancrage/provenance et recuperation ulterieure depuis la bibliotheque.

Livraison Lot 3 bis, 2026-06-04:

- `AssistantResponseOverride` persiste le rendu Biblio autorise comme message
  assistant final, en mode synchrone et streaming, avant d'appeler
  `memory_store.save_new_traces(conversation)`;
- `conv_store.append_message()` conserve le texte effectivement rendu dans
  `message.content`; `message.meta` porte seulement les signaux Biblio
  complementaires content-free (`source`, statut, mode de rendu, hash court,
  compteurs), sans remplacer le texte rendu;
- `memory_traces_summaries._message_is_trace_eligible()` accepte les messages
  `user` et `assistant` non vides, non deja `embedded`, et exclut seulement les
  assistants interrompus. Aucun filtre `source=biblio_rendered_answer` ne retire
  les extraits Biblio rendus;
- P3 streaming est valide comme trou de preuve historique et ferme par test:
  `test_run_llm_exchange_stream_override_persists_biblio_content_for_memory`
  prouve que le stream finalise le message assistant, garde ses metadonnees
  Biblio, appelle `save_new_traces()` avec le texte rendu, bypass OpenRouter et
  garde l'observabilite sans texte brut;
- les summaries et retrieval restent des comportements generaux de Memory: ce
  lot prouve l'entree du contenu rendu dans la conversation et dans
  `save_new_traces`, pas une politique speciale de recuperation documentaire;
- aucune memoire documentaire speciale ne remplace le texte conversationnel:
  `BiblioReadingEvent` reste un enrichissement d'ancrage/provenance et un futur
  lien possible vers traces ou ancres.

Critere de fermeture: le comportement reel conversation -> memoire est audite;
on sait precisement si les extraits rendus entrent en memoire; les
citations/extraits Biblio sont traites comme contenu conversationnel normal; les
ancres/provenance Biblio sont conservables en complement; aucun chemin ne
supprime silencieusement les extraits sous pretexte qu'ils viennent de Biblio;
les preuves distinguent lane Biblio interne, reponse finale rendue, contenu
effectivement memorise et metadonnees d'ancrage/provenance.

### Lot 4 - Methodes par questions canoniques

- [x] Lot 4A: migrer un premier cran inventaire/metadonnees.
- [x] Lot 4B: migrer un premier cran resolution documentaire.
- [x] Lot 4C: migrer un premier cran structure/TOC.
- [x] Lot 4D: migrer un premier cran recherche scoped.
- [ ] Migrer extraction.
- [ ] Migrer navigation lecteur.
- [ ] Migrer provenance.
- [ ] Migrer desambiguisation.
- [ ] Migrer etat/ancrage.

Critere de fermeture: chaque question canonique a une methode, des outils
autorises, un resultat et des tests.

Livraison Lot 4A, 2026-06-04:

- famille canonique livree: `inventory_metadata`;
- methode produit canonique ajoutee: `product_method=inventory_metadata`,
  `case_id=""`, distincte des anciens P01/P02 qui restent des regressions
  historiques et des compatibilites `catalog_list_full` / `catalog_list_bounded`;
- outils autorises explicites: `catalog_list`, `search_document`,
  `document_open_summary`;
- le bibliothecaire LLM reste souverain pour choisir cette methode. Le code ne
  reconnait pas les formulations utilisateur par regex et ne juge pas le sens de
  la demande;
- le deterministe valide seulement le contrat: methode connue, famille
  canonique, outils allowlistes GET-only, budgets, params bornes,
  observabilite content-free;
- `BiblioAnswerObject` porte un bloc `inventory_metadata` structure depuis les
  resultats d'outils: documents, total observe, langue, pages et statut metadata
  quand ces champs existent;
- le renderer produit un rendu structure sans extrait exact. `BiblioFinalResponseLock`
  peut autoriser cette surface finale parce que le contrat technique est
  coherent et qu'aucun texte exact n'est pretendu;
- l'observabilite ne contient pas les titres/auteurs bruts: seulement compteurs,
  hashes courts, statuts, ids courts et flags de borne;
- preuve actuelle: tests unitaires de validation agent, outils, answer object et
  agent-first. Ce n'est pas une preuve live agentique: aucun artefact JSONL live
  n'est produit par ce lot.

Findings Lot 4A:

- F1 valide: `passage_search_in_work` reste trop large et ne doit pas devenir la
  methode fourre-tout de Lot 4.
- F2 valide: Lot 4 ne se ferme pas en un commit; seule la premiere famille est
  migree.
- F3 valide: inventaire/metadonnees est le meilleur premier cran car il depend
  des endpoints Catalogue/metadonnees et pas de l'extraction mecanique complete.
- F4 valide: un rendu final structure doit passer par
  `BiblioAnswerObject` / renderer / `BiblioFinalResponseLock`, pas par une lane
  racontee au LLM final.
- F5 valide: les preuves de ce lot sont unitaires et contractuelles, pas une
  preuve agentique live.

Familles Lot 4 encore ouvertes apres Lot 4A: resolution documentaire, structure/TOC,
recherche scoped, extraction, navigation lecteur, provenance,
desambiguisation, etat/ancrage.

Livraison Lot 4B, 2026-06-04:

- famille canonique livree en premier cran: `document_resolution`;
- methode produit canonique ajoutee: `product_method=document_resolution`,
  `case_id=""`, distincte de l'ancien `work_lookup` / P03 qui reste une
  regression historique et une compatibilite de transition;
- outils autorises explicites: `search_document`, `search_work`,
  `resolve_work`, `document_open_summary`;
- `resolve_section` et `section_bounds` restent hors Lot 4B: la resolution fine
  de section/TOC demeure ouverte pour le cran structure/TOC;
- le bibliothecaire LLM choisit cette methode. Le code ne reconnait pas les
  formulations utilisateur par regex et ne juge pas la pertinence
  bibliographique;
- le deterministe verifie seulement: methode connue, famille canonique, outils
  allowlistes GET-only, params bornes, statut technique, absence de choix
  silencieux du premier candidat ambigu et observabilite content-free;
- `app/biblio/answer_resolution.py` porte la projection/rendu de resolution
  documentaire pour eviter d'empiler toutes les familles dans
  `answer_object.py`;
- `BiblioAnswerObject.document_resolution` expose `resolved`, `ambiguous`,
  `not_found`, `needs_clarification` ou `error` selon les tool results. Un
  candidat unique peut etre rendu comme resolution structuree; plusieurs
  candidats restent `ambiguous`; zero candidat reste `not_found`;
- un candidat de section signale comme travail interne non confirme ne devient
  pas une oeuvre interne resolue: il reste en clarification structurelle;
- `BiblioFinalResponseLock` peut autoriser le rendu structure coherent sans
  extrait exact; aucun texte exact n'est pretendu par ce cran;
- l'observabilite ne contient pas les titres/auteurs bruts: seulement compteurs,
  hashes courts, ids courts, types de candidats, statuts et reason codes;
- preuve actuelle: tests unitaires de validation agent, outils, answer object et
  agent-first. Ce n'est pas une preuve live agentique: aucun artefact JSONL live
  n'est produit par ce lot.

Findings Lot 4B:

- F1 valide: `work_lookup` est la vieille methode P03 et ne reste pas seule
  comme methode canonique de resolution documentaire.
- F2 valide: Lot 4B migre seulement document/work; la resolution fine de
  section/TOC reste ouverte.
- F3 valide: le resultat de resolution est structure et renderable via
  `BiblioAnswerObject` / renderer / `BiblioFinalResponseLock`, pas raconte comme
  lane au LLM final.
- F4 valide: `ambiguous` reste `ambiguous`; la completion metadata canonique ne
  choisit pas le premier document quand plusieurs candidats existent.
- F5 valide: les preuves de ce lot sont unitaires et contractuelles, pas une
  preuve agentique live.

Familles Lot 4 encore ouvertes apres Lot 4B: structure/TOC, recherche scoped,
extraction, navigation lecteur, provenance, desambiguisation, etat/ancrage.

Livraison Lot 4C, 2026-06-04:

- famille canonique livree en premier cran: `document_structure`;
- methode produit canonique ajoutee: `product_method=document_structure`,
  `case_id=""`, distincte de l'ancien `document_toc_show` / P09 qui reste une
  regression historique et une compatibilite de transition;
- outils autorises explicites: `search_document`, `resolve_work`,
  `document_open_summary`, `document_toc`, `search_section`,
  `resolve_section`, `section_bounds`;
- `catalog_search` reste hors de la methode canonique structure/TOC: le cran
  canonique ne doit pas redevenir une recherche globale opportuniste suivie d'un
  bricolage local. P09 garde cette compatibilite legacy;
- le bibliothecaire LLM choisit cette methode. Le deterministe ne reconnait pas
  les formulations utilisateur par regex et ne juge jamais la pertinence
  semantique ou bibliographique;
- le deterministe verifie seulement: methode connue, famille canonique, outils
  allowlistes GET-only, params bornes, statut technique, absence de choix
  silencieux d'un document/section ambigu et observabilite content-free;
- `app/biblio/answer_structure.py` porte la projection/rendu structure/TOC pour
  eviter d'empiler toutes les familles dans `answer_object.py`;
- `BiblioAnswerObject.document_structure` expose `resolved`, `ambiguous`,
  `not_found`, `needs_clarification` ou `error` selon les tool results;
- une TOC ou une section structurelle n'est pas un texte primaire ni une
  extraction exacte. Meme si un outil porte par ailleurs du texte mecanique, la
  famille `document_structure` force un rendu `structured_status`, pas
  `exact_excerpt`;
- un document unique peut ouvrir une TOC. Plusieurs candidats restent
  `ambiguous`; zero structure reste `not_found`; une structure insuffisante
  reste `needs_clarification` ou porte un reason code structurel;
- `BiblioFinalResponseLock` peut autoriser le rendu structure coherent sans
  extrait exact; aucun texte exact n'est pretendu par ce cran;
- l'observabilite ne contient pas les titres/auteurs/chapitres bruts: seulement
  compteurs, hashes courts, ids courts, roles de contenu, statuts de bornes,
  reason codes et flags de borne;
- preuve actuelle: tests unitaires de validation agent, answer object et
  agent-first. Ce n'est pas une preuve live agentique: aucun artefact JSONL live
  n'est produit par ce lot.

Findings Lot 4C:

- F1 valide: `document_toc_show` / P09 est legacy; le canon Lot 4C est
  `document_structure` avec `case_id=""`.
- F2 valide: plusieurs documents ou sections restent `ambiguous`; le cran
  canonique ne choisit pas le premier candidat.
- F3 valide: une TOC ou une section structurelle ne devient ni texte primaire ni
  extraction exacte.
- F4 valide: Kant, Foucault et Stephanus restent des regressions severes, pas
  des cas particuliers corriges par ce lot.
- F5 valide: `answer_object.py` etait deja gros; la projection/rendu structurel
  substantiel est separe dans `answer_structure.py`.

Familles Lot 4 encore ouvertes apres Lot 4C: recherche scoped, extraction,
navigation lecteur, provenance, desambiguisation, etat/ancrage.

Livraison Lot 4D, 2026-06-04:

- famille canonique livree en premier cran: `scoped_search`;
- methode produit canonique ajoutee: `product_method=scoped_search`,
  `case_id=""`, distincte des anciens P05-P08/P16-P18 qui restent des
  regressions historiques et des compatibilites de transition
  `passage_search_in_work` / `passage_search_external_work`;
- outils autorises explicites: `search_document`, `search_work`,
  `search_section`, `resolve_work`, `resolve_section`, `section_bounds`,
  `catalog_search`;
- `catalog_search` reste une recherche plein texte globale cote API Catalogue,
  mais le chemin canonique `scoped_search` ne l'accepte comme recherche scoped
  que si un `document_id` est explicite ou porte depuis un scope documentaire
  unique. Le runtime bloque une recherche globale sans scope et filtre
  techniquement les hits par `document_id`;
- le bibliothecaire LLM choisit le sens, le theme, le scope et la methode. Le
  deterministe ne juge pas quel hit est intellectuellement le bon passage: il
  verifie seulement la methode, les outils GET-only, les params bornes, le scope
  unique, le filtrage technique et l'observabilite content-free;
- `app/biblio/answer_search.py` porte la projection/rendu recherche scoped pour
  eviter d'empiler toutes les familles dans `answer_object.py`;
- `BiblioAnswerObject.scoped_search` expose `resolved`, `ambiguous`,
  `not_found`, `needs_clarification` ou `error`, avec scope, compteurs,
  candidats bornes, hits filtres hors scope et reason codes content-free;
- quand `catalog_search` a bien ete tente dans un scope documentaire unique et
  qu'aucun candidat ne reste dans ce scope, le statut mecanique est `not_found`
  avec `scoped_search_no_hits_in_scope`, pas `needs_clarification`;
- le renderer expose le reason code produit effectif du bloc canonique actif:
  un `not_found` scoped ne doit pas etre rendu avec `Reason: ok`;
- recherche scoped canonique n'est pas extraction exacte: la methode
  `product_method=scoped_search` force un rendu `structured_status` et ne
  transforme ni `context_text`, ni `page_text`, ni un hit de recherche en
  `exact_excerpt`. Les anciens P05-P08/P16-P18 peuvent encore produire un
  contexte borne comme compatibilite legacy jusqu'a leur migration extraction;
- plusieurs documents possibles avant recherche restent `ambiguous` ou
  `needs_clarification`. Plusieurs hits dans un scope resolu restent des
  candidats de recherche; le renderer ne choisit pas silencieusement le
  "meilleur" passage;
- `passage_context`, `page_read` et `locate` restent hors du cran canonique
  Lot 4D: ils relevent de l'extraction, de la navigation ou des references
  canoniques;
- l'observabilite ne contient pas de snippets/titres bruts: seulement compteurs,
  hashes courts, ids courts, statuts, reason codes et flags de borne. Les
  snippets bornes peuvent etre rendus a l'utilisateur comme surface de recherche
  scoped, mais pas dans les artefacts/logs content-free;
- preuve actuelle: tests unitaires de validation agent, answer object et
  agent-first. Ce n'est pas une preuve live agentique: aucun artefact JSONL live
  n'est produit par ce lot.

Findings Lot 4D:

- F1 valide: `passage_search_in_work` est trop large pour rester le canon Lot
  4D; il reste legacy/regression historique.
- F2 valide: `_method_allows_exact_text()` ne doit pas autoriser la methode
  canonique `product_method=scoped_search` a rendre `exact_excerpt`; Lot 4D
  retire cette possibilite sans casser les legacy P05-P08/P16-P18.
- F3 valide: `/search` / `catalog_search` est global; la recherche scoped est
  garantie par un scope documentaire explicite/porte et par un filtrage
  technique content-free cote FridaDev.
- F4 valide: plusieurs documents possibles avant recherche restent
  `ambiguous`/clarification; aucun premier candidat documentaire n'est choisi.
- F5 valide: plusieurs hits dans un document resolu forment un resultat de
  recherche, pas un passage exact.
- F6 valide: Kant, Foucault et Stephanus restent des regressions severes, pas
  des cas particuliers corriges par ce lot.

Familles Lot 4 encore ouvertes apres Lot 4D: extraction, navigation lecteur,
provenance, desambiguisation, etat/ancrage.

Livraison Lot 4E, 2026-06-04:

- famille canonique livree en premier cran: `extraction`;
- methode produit canonique ajoutee: `product_method=extraction`, `case_id=""`,
  distincte de l'ancien P04 `passage_extract_canonical_range`, qui reste une
  regression historique et une compatibilite de transition pour les plages
  canoniques;
- outils autorises explicites: `search_document`, `search_work`,
  `search_section`, `resolve_work`, `resolve_section`, `section_bounds`,
  `catalog_search`, `locate`, `page_read`, `passage_context`;
- `catalog_search` peut preparer un candidat ancre dans un scope documentaire,
  mais une recherche ou un snippet ne sont jamais un extrait exact;
- exact text signifie: texte mecanique fourni par `page_read` ou
  `passage_context`, avec `document_id` et ancre technique minimale
  (`page_no` ou `paragraph_id`) presents. Sans cette ancre, le renderer bloque
  l'exact avec `extraction_anchor_missing`;
- `app/biblio/answer_extraction.py` porte la projection/rendu extraction pour
  eviter d'empiler la famille dans `answer_object.py`;
- `BiblioAnswerObject.extraction` expose `resolved`, `ambiguous`, `not_found`,
  `needs_clarification` ou `error`, source tool, document court, type de texte,
  ancre, presence/hash/compteurs de texte exact, reason codes et limites;
- le bibliothecaire LLM choisit le sens, la methode, le document, la reference,
  la page ou les ancres candidates. Le deterministe valide seulement le contrat
  technique: outil GET-only autorise, document/ancre coherents, texte mecanique
  present, observabilite content-free et renderer final coherent;
- le runtime peut completer mecaniquement une position deja portee vers
  `passage_context`, mais il ne lance pas de recherche plein texte opportuniste
  pour fabriquer une extraction canonique;
- l'observabilite ne contient pas le texte brut: seulement compteurs, hashes
  courts, ids courts, positions, statut, reason codes et flags de borne;
- preuve actuelle: tests unitaires de validation agent, answer object et
  agent-first. Ce n'est pas une preuve live agentique: aucun artefact JSONL live
  n'est produit par ce lot.

Findings Lot 4E:

- F1 valide: l'extraction existait via P04 legacy; le canon Lot 4E est
  `extraction` avec `case_id=""`.
- F2 valide: `answer_object.py` savait rendre du texte mecanique, mais il
  manquait une projection produit extraction lisible et testee.
- F3 valide: un hit `catalog_search` ou un snippet ne devient jamais
  `exact_excerpt`.
- F4 valide: un texte exact sans document/ancre technique suffisante est bloque.
- F5 valide: aucune pertinence semantique n'est codee par ce lot.

Familles Lot 4 encore ouvertes apres Lot 4E: navigation lecteur, provenance,
desambiguisation, etat/ancrage. Extraction reste ouverte pour les sections
completes, multi-pages complexes, intervalles arbitraires et plages canoniques
completes.

Livraison Lot 4E.1, 2026-06-04:

- Lot 4E.1 reste dans la famille canonique `extraction`;
- il livre l'extraction mecanique bornee de pages et d'intervalles courts deja
  materialises par les appels outil du bibliothecaire;
- page unique: `page_read(document_id, page_no)` rend exact si la page est lue,
  ancree et coherente avec le document;
- deux ou trois pages consecutives: plusieurs appels `page_read` sont assembles
  mecaniquement en ordre documentaire, uniquement si tous les blocs existent,
  portent le meme `document_id` et forment un intervalle contigu;
- budget ferme actuel: 1 a 3 pages et 8 000 caracteres exacts assembles. Au-dela,
  le renderer bloque avec reason code content-free;
- un intervalle non lu n'est pas un extrait. Une page manquante entre deux pages
  lues bloque avec `extraction_page_range_incomplete`;
- des pages de documents differents bloquent avec `extraction_document_mismatch`;
- `catalog_search`, snippets, TOC, titres de chapitres ou resultats de structure
  restent hors extraction exacte;
- `BiblioAnswerObject.extraction` porte maintenant des blocs mecaniques
  content-free: nombre de blocs, pages debut/fin, pages manquantes, compteurs,
  hashes courts, outil source et reason codes. Le texte brut des pages ne fuit
  pas dans l'observabilite;
- les extractions multi-pages resolues exposent aussi au niveau global de
  `BiblioAnswerObject.anchors` une ancre par bloc rendu, avec au minimum
  `document_id` et `page_no`. Les extractions bloquees ne creent pas de fausse
  couverture globale partielle;
- `BiblioFinalResponseLock` autorise le rendu exact assemble seulement si le
  hash, la longueur et la couverture d'ancres tiennent;
- LOT 4E.1: LE BIBLIOTHECAIRE DECIDE LES BORNES DOCUMENTAIRES. LE CODE NE FAIT
  QU'ASSEMBLER MECANIQUEMENT LES PAGES OU CONTEXTES EFFECTIVEMENT LUS, SOUS
  BUDGET ET AVEC ANCRES. UN INTERVALLE NON LU N'EST PAS UN EXTRAIT. UNE BORNE
  AMBIGUE N'EST PAS DEVINEE.

Limites restantes Lot 4E apres 4E.1:

- pas de section complete sans bornes fiables;
- pas d'intervalle Stephanus complet ou autre plage canonique complete;
- pas de navigation lecteur globale;
- pas de continuation automatique depuis un etat implicite. La continuation
  minimale est acceptee seulement si le bibliothecaire materialise le prochain
  `page_read` ou si un futur lot expose une ancre courante explicite et fiable;
- preuve actuelle: tests unitaires et agent-first contractuels seulement, pas de
  smoke live agentique ni artefact JSONL.

Livraison Lot 4E.2, 2026-06-04:

- Lot 4E.2 reste dans la famille canonique `extraction`;
- il livre un premier pont runtime depuis des bornes de section deja resolues
  vers des lectures mecaniques `page_read` courtes;
- condition de declenchement: `product_method=extraction`, `case_id=""`,
  un `section_bounds` resolu avec `document_id` et une page de debut
  exploitable, plus un `answer_mode` compact explicite de debut de section
  (`section_start_page_block_2` ou famille equivalente deja autorisee);
- sans cet `answer_mode` explicite, `section_bounds` reste une structure/bornes:
  il ne devient pas automatiquement une extraction exacte;
- comportement livre: le runtime lit mecaniquement les deux premieres pages de
  la section, ou moins si la borne de fin connue rend la section plus courte,
  puis laisse `answer_extraction.py` assembler/verrouiller le rendu exact selon
  les regles Lot 4E.1;
- `section_bounds` seul ne rend jamais un extrait exact. Le texte exact ne vient
  que des `page_read` effectivement executes;
- ambiguite, absence de `document_id`, absence de page de debut exploitable ou
  borne non-page restent bloques/clarification; le code ne choisit pas une
  section et n'invente pas une borne;
- aucun parseur de formulation utilisateur n'est ajoute: le bibliothecaire LLM
  decide la section et le mode de restitution; le deterministe execute seulement
  le contrat technique sous budget;
- observabilite: pas de texte brut dans les preuves, seulement statuts,
  reason codes, ids courts, compteurs, hashes et ancres;
- preuve actuelle: tests unitaires et agent-first contractuels seulement, pas de
  smoke live agentique ni artefact JSONL.

Findings Lot 4E.2:

- F1 valide: Lot 4E.1 savait assembler les pages deja lues, mais pas completer
  depuis `section_bounds`.
- F2 valide: `section_bounds` porte les bornes structurelles; le runtime
  canonique `extraction` ne les transformait pas encore en lectures courtes.
- F3 valide: ambiguite, absence de document, absence de page exploitable ou
  intervalle non materialise doivent bloquer proprement.
- F4 valide: le debut/deux premieres pages de section lit seulement le petit
  bloc demande; aucune section longue n'est lue dans ce lot.
- F5 valide: la preuve runtime `resolve/section_bounds -> page_read ->
  exact_excerpt -> final lock` manquait jusque-la.

Limites restantes Lot 4E apres 4E.2:

- pas de section complete longue;
- pas d'intervalle arbitraire de section hors petit bloc de debut explicite;
- pas de plage canonique complete type Stephanus;
- pas de navigation lecteur globale ni continuation depuis etat implicite;
- pas de nouveau filtre ou enrichissement structurel Lot 2 bis.

Livraison Lot 4E.3, 2026-06-04:

- Lot 4E.3 reste dans la famille canonique `extraction`;
- il livre un premier pont depuis un candidat de recherche ancre vers une
  extraction mecanique `passage_context`;
- condition de declenchement: `product_method=extraction`, `case_id=""`, un
  `catalog_search` document-scoped par `document_id` explicite ou porte,
  exactement un seul hit scoped total apres filtrage, et ce hit unique doit
  porter une ancre technique exploitable (`paragraph_id` ou `page_no` +
  `para_no`);
- `catalog_search` est autorise comme precurseur de localisation dans
  `extraction`, mais ses snippets ne sont jamais du texte exact;
- le runtime appelle `passage_context` uniquement apres ce candidat unique
  ancre; le rendu exact vient ensuite de `context_text`, pas du snippet;
- zero candidat, plusieurs candidats scoped, candidat unique sans ancre,
  candidat sans `document_id`, recherche non scopee ou document incoherent
  restent bloques/clarification. Le code ne choisit pas le premier hit, meme si
  un seul des candidats scoped est ancre;
- `scoped_search` ne change pas de nature: il reste une methode de recherche
  structuree et ne declenche pas `passage_context`;
- aucun jugement semantique n'est code: le bibliothecaire choisit la requete,
  le scope et la methode; le deterministe verifie seulement unicite, scope,
  ancre, execution GET-only et observabilite content-free;
- preuve actuelle: tests unitaires et agent-first contractuels seulement, pas de
  smoke live agentique ni artefact JSONL.

Findings Lot 4E.3:

- F1 valide: le runtime pouvait prendre le premier candidat ancre via
  `_first_context_params()`; le chemin canonique `extraction` exige maintenant
  un unique hit scoped total, puis verifie que ce hit unique est ancre.
- F2 valide: `scoped_search` reste recherche structuree, sans `exact_excerpt`.
- F3 valide: le pont est limite a `product_method=extraction` et ne s'active
  que sur un unique hit scoped total, ancre, dans un scope documentaire.
- F4 valide: le renderer savait deja rendre `passage_context`; le manque etait
  le pont runtime strict depuis la recherche ancree.
- F5 valide: le chemin `catalog_search` unique scoped -> `passage_context` ->
  `exact_excerpt` -> final lock est maintenant prouve par tests.
- F6 valide: plusieurs hits scoped bloquent, meme si un seul est ancre; aucun
  premier hit n'est choisi.

Limites restantes Lot 4E apres 4E.3:

- pas de ranking semantique deterministe;
- pas de choix automatique entre plusieurs hits;
- pas de passage depuis `scoped_search` vers extraction sans decision
  bibliothecaire explicite;
- pas de section complete longue;
- pas de plage canonique complete type Stephanus;
- pas de navigation lecteur globale ni provenance/etat global.

Proof Gate live Lot 4E, 2026-06-04:

- artefact content-free:
  `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-20260604T144426Z.jsonl`;
- 4 cas live agentiques lances: page precise, deux pages precises, recherche
  scoped zero-hit, recherche scoped multi-hit;
- contenu brut absent de l'artefact: pas de prompt brut, pas de dialogue brut,
  pas de titre/auteur brut, pas de payload Catalogue brut, pas de passage
  d'ouvrage; seulement statuts, reason codes, noms d'outils, compteurs,
  hashes courts, ids courts et modes de rendu;
- message final Biblio verifie via `BiblioFinalResponseLock` /
  `AssistantResponseOverride`: quand le lock autorise une surface Biblio,
  l'override attendu est present et son hash correspond au lock;
- verdict global: Proof Gate non ferme. Il prouve que le verrou de rendu final
  tient, mais pas que les chemins canoniques Lot 4E sont correctement choisis
  par l'agent live.

Findings Proof Gate Lot 4E:

- `PG4E_PAGE_ONE`: partiel. Le bibliothecaire choisit bien
  `product_method=extraction`, mais n'execute que `search_document`; aucun
  `page_read` n'est materialise, donc l'extraction exacte reste bloquee.
- `PG4E_PAGE_TWO`: echec canonique. Le chemin live tombe en
  `fallback_deterministic` puis rend un `exact_excerpt` via
  `catalog_search`/`passage_context`, pas via la methode canonique
  `extraction` + `page_read` multi-page.
- `PG4E_SCOPED_ZERO`: echec canonique. La demande de recherche scoped part en
  `passage_search_in_work` legacy et execute `passage_context`; elle ne produit
  pas le statut `scoped_search/not_found` attendu.
- `PG4E_SCOPED_MULTI`: echec canonique. La demande reste sur
  `passage_search_in_work` legacy et rend un extrait exact; elle ne prouve pas
  le contrat `scoped_search` sans extraction.
- aucun snippet n'est prouve comme rendu exact dans l'artefact, mais les
  chemins legacy continuent de produire de l'exact via `passage_context`; ils
  doivent etre traites avant de clore la validation produit 4E.

Prochain micro-lot recommande apres Proof Gate:

- corriger la transition agentique live vers les methodes canoniques, sans
  parseur utilisateur local:
  - page precise / deux pages -> `product_method=extraction` avec `page_read`;
  - recherche scoped -> `product_method=scoped_search`, sans `passage_context`;
  - legacy `passage_search_in_work` ne doit plus absorber les demandes
    canoniques de recherche scoped ou d'extraction page/pages.

Correction transition agentique live 4E:

- le contrat agentique rappelle que les P-cases sont une matrice historique /
  regression, pas le canon principal des questions live;
- pour les familles canoniques `scoped_search` et `extraction`, le
  bibliothecaire doit privilegier `case_id=""` et les methodes canoniques;
- `passage_search_in_work` / P05-P08 et
  `passage_search_external_work` / P16-P18 restent legacy et ne doivent plus
  absorber une recherche scoped canonique;
- une extraction page/page-range peut enchainer resolution documentaire puis
  `page_read` avec `document_id` porte par le runtime quand la page ou plage
  courte est explicite;
- le separateur naturel `pages N et M` est accepte comme borne numerique courte,
  au meme titre que `pages N a M`;
- si un vieux plan declare `answer_mode=scoped_search`, le runtime ne complete
  pas vers `passage_context`: il rend une surface structuree de recherche, pas
  un extrait exact;
- cette correction reste un mur technique: elle ne choisit pas le bon passage,
  ne ranke pas semantiquement, ne corrige pas Kant/Foucault/Stephanus et
  n'ajoute pas de regex de cas produit. Le Proof Gate live doit etre rejoue
  pour verifier le comportement agentique reel.

Replay live apres correction:

- artefact content-free conserve:
  `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-agentic-transition-20260604T145952Z.jsonl`;
- score initial: `0 met`, `3 failed`, `1 partial`;
- score apres correction: `1 met`, `0 failed`, `3 partial`;
- amelioration observee: les cas page/petite plage basculent vers
  `product_method=extraction` avec `page_read`; les cas recherche bornee
  basculent vers `product_method=scoped_search`; aucun cas scoped ne rend
  d'extrait exact via `passage_context`;
- limite restante: les cas page restent partiels quand la resolution
  documentaire live ne porte pas encore un document unique exploitable jusqu'au
  rendu final. C'est une limite de transition agentique/resolution
  documentaire, pas un bug du renderer d'extraction;
- Lot 4E live n'est pas encore ferme: le replay valide l'amelioration de
  trajectoire, mais les pages precises doivent encore produire regulierement
  `BiblioAnswerObject` + `BiblioFinalResponseLock` exact depuis `page_read`.

Proof Gate page-render isole:

- artefact content-free conserve:
  `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-page-render-20260604T151409Z.jsonl`;
- score: `4 met`, `0 failed`, `0 partial`;
- diagnostic: quand le document est deja explicitement ancre, le troncon
  `page_read` -> `BiblioAnswerObject.extraction/resolved` -> `exact_excerpt`
  -> `BiblioFinalResponseLock/authorized` -> message assistant final conforme
  tient pour une page unique et deux pages contigues;
- requalification: les anciens `partial` des cas page ne prouvaient pas un bug
  du renderer page. Ils provenaient de `page_read` planifie mais non exploitable
  faute de `document_id` porte par la resolution live;
- limite restante: fermer le live naturel page/page-range exige encore une
  meilleure resolution/ancrage documentaire agentique avant `page_read`. Le
  renderer page-range minimal est prouve quand les pages ont effectivement ete
  lues.

Proof Gate ancrage documentaire naturel avant `page_read`:

- artefact content-free conserve:
  `app/docs/states/baselines/biblio-smokes/lot4e-proof-gate-live-after-document-anchor-20260604T154046Z.jsonl`;
- score: `3 met`, `0 failed`, `1 partial`;
- `PG4E_PAGE_ONE`: `met`. Une demande naturelle de page d'un ouvrage resolu
  passe par `search_document` puis `page_read`; l'extraction devient
  `resolved/page`, le renderer rend `exact_excerpt`, le final lock autorise et
  le message assistant correspond au lock;
- `PG4E_PAGE_TWO`: `met` apres audit du harness. Le bibliothecaire passe par
  `resolve_work` puis deux `page_read`; `resolve_work` porte un `document_id`
  unique exploitable, l'extraction devient `resolved/page_range`, deux ancres
  globales couvrent les pages et le final lock autorise. Le verdict initial du
  harness exigeait a tort `search_document`; l'artefact porte le flag
  `verdict_reclassified_after_harness_audit=true`;
- correction runtime: si un `page_read` suit une resolution documentaire unique
  et porte un `document_id` contradictoire ou hallucine, le planner utilise
  l'ancre documentaire unique deja portee. Ce mur ne choisit pas le document:
  il preserve la coherence technique du document resolu par le bibliothecaire;
- limite restante hors scope: le cas recherche scoped multi-hit reste partiel
  dans ce replay et devra etre traite dans le lot scoped_search/clarification,
  pas dans le lot page-render.

### Lot 5 - Nettoyage dur

- [ ] Supprimer ou declasser les chemins legacy non appeles.
- [ ] Scinder les gros fichiers par responsabilite reelle.
- [ ] Supprimer les reparations de cas devenues inutiles.
- [ ] Refaire les smokes autour des questions canoniques.
- [ ] Archiver ou requalifier les roadmaps obsoletes.

Critere de fermeture: `app/biblio/` ne contient plus de code mort significatif
et chaque module a une responsabilite lisible.

### Lot 6 - Validation produit live

- [ ] Valider les questions canoniques, pas seulement les exemples.
- [ ] Garder Kant/Foucault/Stephanus comme regressions severes.
- [ ] Produire des artefacts JSONL content-free.
- [ ] Verifier les reponses finales quand le renderer est concerne.
- [ ] Documenter les limites volontaires restantes.

Critere de fermeture: Frida se comporte comme une bibliotheque utilisable,
pas seulement comme un agent qui appelle des outils.

## 10. Preuves de fermeture minimales

Chaque lot doit fournir:

- commandes executees;
- statut Git;
- diff utile relu;
- tests ou preuves content-free;
- absence de secrets;
- absence de contenu d'ouvrage long;
- raison des limites acceptees.

Preuves produit minimales:

- inventaire total coherent;
- resolution document/work/section;
- recherche globale et scoped;
- extraction page/pages/section/intervalle;
- navigation depuis etat;
- provenance avec role;
- clarification d'ambiguite;
- rendu final mecanique pour extrait exact.
- extrait Biblio rendu traite comme contenu conversationnel normal par la
  politique memoire generale;
- evenement de lecture Biblio ancre en complement du contenu rendu;
- preuve distinguant lane Biblio interne, reponse finale rendue, contenu
  effectivement memorise et metadonnees d'ancrage/provenance;
- preuve de rehydratation ulterieure du texte exact depuis la bibliotheque a
  partir des ancres, comme complement de verification.

## 11. Risques si cette TODO n'est pas suivie

- accumulation de regex et de reparations locales;
- smokes verts mais produit faux;
- agent LLM utilise comme substitut a une structure documentaire absente;
- erreurs primaires/commentaires;
- refus generiques alors que la bibliotheque locale a un extrait borne;
- extraits Biblio rendus perdus entre lane interne, renderer, reponse finale et
  Memory;
- metadonnees d'ancrage/provenance absentes des traces conversationnelles;
- module Biblio trop gros et trop ambigu pour etre maintenu;
- perte de confiance utilisateur.

## 12. Regle de pilotage

Le chantier ne se ferme pas quand l'agent parait intelligent.

Il se ferme quand la bibliotheque sait repondre aux questions canoniques avec:

- structure;
- API/outils;
- extraction mecanique;
- renderer;
- bibliothecaire LLM souverain dans ce cadre;
- deterministe reduit aux murs;
- code Biblio nettoye.
