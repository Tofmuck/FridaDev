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
- limites assumees: les PDF ne distinguent pas encore PDF texte / PDF scanne
  OCR dans `source_type`; les EPUB exposent leurs sections via la semantique
  actuelle `page_no`; les oeuvres internes complexes ne sont pas inventees.

Critere de fermeture: les documents existants ont maintenant une projection
structurelle inspectable, versionnee, validee et sans texte long expose. Cette
projection normalise le fonds actuel vers un modele canonique unique et devient
le contrat de sortie des imports futurs: si un ouvrage entre demain par le
pipeline nominal, il doit etre projetable/validable comme `DocumentManifest`.
S'il manque des champs minimaux, l'echec doit etre content-free et explicite;
il ne doit pas disparaitre dans une structure incompatible.

### Lot 2 - API/outils de bibliotheque minimale

- [ ] Ajouter ou wrapper `search_document`.
- [ ] Ajouter ou wrapper `search_work`.
- [ ] Ajouter ou wrapper `search_section`.
- [ ] Ajouter `resolve_work` et `resolve_section` outilles par manifeste.
- [ ] Ajouter `section_bounds`.
- [ ] Garder GET-only et budgets explicites.

Critere de fermeture: le bibliothecaire peut poser les questions canoniques
sans passer par une recherche globale puis tri opportuniste.

### Lot 3 - Answer object et renderer

- [ ] Introduire `BiblioAnswerObject`.
- [ ] Porter document, oeuvre, section, ancre, intervalle, role, provenance,
      limites, truth level et status.
- [ ] Brancher un renderer produit pour les extractions exactes.
- [ ] Empêcher le LLM final d'etre l'imprimante du texte exact.

Critere de fermeture: une extraction exacte peut etre rendue sans generation
libre du texte extrait.

### Lot 3 bis - Memoire conversationnelle des lectures

- [ ] Documenter la frontiere entre lane Biblio interne, extrait rendu dans le
      fil et contenu effectivement memorise.
- [ ] Verifier la politique reelle conversation -> memoire: messages `user`,
      messages `assistant`, messages interrompus, messages deja `embedded`,
      `message.meta`, summaries et retrieval.
- [ ] Poser que toute conversation est candidate a la memoire selon les regles
      generales de Memory.
- [ ] Poser que les extraits Biblio rendus dans la conversation ne sont pas
      exclus par defaut.
- [ ] Poser que les citations, extraits, commentaires, explications et reprises
      Biblio entrent comme contenu conversationnel normal quand ils sont
      effectivement rendus dans le fil.
- [ ] Definir `BiblioReadingEvent` comme enrichissement d'ancrage/provenance,
      pas comme substitut sans texte au contenu rendu.
- [ ] Conserver en complement document_id, oeuvre, section, ancres, pages, hash,
      provenance, role de contenu, origine `biblio_extraction` et limites.
- [ ] Faire de la rehydratation par ancres depuis la bibliotheque un complement
      de verification/recuperation, pas un substitut obligatoire a la memoire du
      texte effectivement dit.
- [ ] Distinguer texte source rendu, note de lecture, synthese et interpretation
      par metadonnees et provenance, sans les rendre moins memorisables.
- [ ] Auditer les chemins runtime concernes: lane Biblio, reponse assistant,
      `message.meta.biblio_state`, traces Memory, resumes, retrieval et
      documents actifs de conversation.
- [ ] Verifier si un extrait Biblio rendu peut etre perdu entre lane interne,
      renderer, reponse finale, persistence conversationnelle et Memory.
- [ ] Definir les preuves futures qui distinguent extrait rendu dans la
      conversation, contenu effectivement memorise, metadonnees
      d'ancrage/provenance et recuperation ulterieure depuis la bibliotheque.

Critere de fermeture: le comportement reel conversation -> memoire est audite;
on sait precisement si les extraits rendus entrent en memoire; les
citations/extraits Biblio sont traites comme contenu conversationnel normal; les
ancres/provenance Biblio sont conservables en complement; aucun chemin ne
supprime silencieusement les extraits sous pretexte qu'ils viennent de Biblio;
les preuves distinguent lane Biblio interne, reponse finale rendue, contenu
effectivement memorise et metadonnees d'ancrage/provenance.

### Lot 4 - Methodes par questions canoniques

- [ ] Migrer inventaire/metadonnees.
- [ ] Migrer resolution documentaire.
- [ ] Migrer structure/TOC.
- [ ] Migrer recherche scoped.
- [ ] Migrer extraction.
- [ ] Migrer navigation lecteur.
- [ ] Migrer provenance.
- [ ] Migrer desambiguisation.
- [ ] Migrer etat/ancrage.

Critere de fermeture: chaque question canonique a une methode, des outils
autorises, un resultat et des tests.

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
