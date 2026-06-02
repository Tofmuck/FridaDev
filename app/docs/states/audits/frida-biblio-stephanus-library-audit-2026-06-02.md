# Frida Biblio Stephanus / logique bibliotheque audit — 2026-06-02

Statut: audit serre content-free
Classement: `app/docs/states/audits/`
Roadmap active: `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`

## Portee

Audit du Lot 11 centre sur:

- la logique metier bibliotheque;
- le chemin agent-first;
- le couple `locate -> passage_context`;
- les references Stephanus simples;
- les intervalles Stephanus;
- la confusion possible texte primaire / commentaire / notice.

Cet audit ne modifie pas Catalogue ni son schema. Il distingue ce qui est
corrigeable immediatement cote FridaDev de ce qui demande un futur chantier
Catalogue / index / mapping.

## Sources lues

- `AGENTS.md`
- `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/baselines/biblio-smokes/stephanus-locate-diagnostic-20260601T195136Z.md`
- `app/docs/states/baselines/biblio-smokes/agent-live-primary-text-stephanus-20260601T200249Z.jsonl`
- `app/biblio/chat_runtime.py`
- `app/biblio/librarian_agent_openrouter.py`
- `app/biblio/librarian_agent_contract.py`
- `app/biblio/librarian_agent_first.py`
- `app/biblio/librarian_planner.py`
- `app/biblio/librarian_tools.py`
- `app/biblio/catalogue_client.py`
- `app/biblio/library_runtime.py`
- `app/biblio/document_resolver.py`
- `app/biblio/table_of_contents_runtime.py`
- `/opt/platform/doc-pipeline/query_api.py`
- `/opt/platform/doc-pipeline/db_store.py`

Artefacts content-free associes:

- `app/docs/states/baselines/biblio-smokes/stephanus-live-check-20260602T061059Z.jsonl`
- `app/docs/states/baselines/biblio-smokes/stephanus-range-diagnostic-20260602T062819Z.md`

## Reponses pre-patch

### 1. Existe-t-il un meilleur plan ?

Oui: ne pas essayer de "forcer" l'agent-first a approximer les demandes
canoniques explicites. Le meilleur plan qui conserve strictement la logique
produit est:

1. garder l'agent-first pour le travail bibliothecaire exploratoire;
2. garder l'agent en comparaison/observabilite sur les requetes canoniques;
3. laisser le deterministe controller la reponse produit quand un locator
   canonique explicite est deja present et que le chemin deterministe sait
   faire plus vrai que `catalog_search -> passage_context`.

Cela respecte la doctrine:

> Le bibliothecaire LLM fait le travail de bibliotheque.
> Le deterministe tient les murs.

### 2. D'ou vient le probleme Stephanus ?

Reponse par couche:

- prompt: **partiel**. Le prompt aide a privilegier le texte primaire et a
  planifier `locate`, mais il n'explique pas a lui seul l'echec des plages.
- contrat JSON agent: **non bloquant pour les labels simples**, mais il peut
  rejeter des plans insuffisants ou non executables.
- validateur: **non cause racine des labels simples**; il refuse a juste titre
  un plan sans `document_id` explicite pour `locate`.
- planner agent-first: **oui, cause immediate d'un ecart produit**. Il degrade
  encore des requetes canoniques explicites vers `catalog_search` puis
  `passage_context`, au lieu de laisser le chemin exact controller.
- `librarian_tools.locate`: **non**. L'outil est borne, GET-only et appelle
  correctement `CatalogueClient.locate`.
- `CatalogueClient.locate`: **non**. Le client appelle correctement la route
  `/doc/{id}/locate`.
- route Catalogue: **partiellement**. La route sait traiter un label simple,
  pas une plage brute.
- absence de donnees/mapping/index Stephanus: **oui pour les plages brutes**.
  Le Catalogue indexe des labels ponctuels, pas un objet "148e-151d" exploitable
  directement.
- confusion texte primaire/commentaire: **oui comme risque metier de ranking**.
  Le systeme n'a pas encore de signal fort "texte primaire > commentaire" dans
  la continuation agent-first ou le ranking de candidats.

### 3. Qu'est-ce qui est corrigeable immediatement cote FridaDev ?

- garder le controle produit deterministe pour les requetes explicites
  `extract_passage` / `extract_range` avec locator present;
- continuer a observer/comparer l'agent-first sans lui laisser remplacer un
  chemin canonique plus vrai;
- documenter explicitement la frontiere "label simple" vs "plage brute";
- ajouter des tests de non-regression pour empecher un retour a
  `catalog_search -> passage_context` sur les demandes canoniques explicites.

### 4. Qu'est-ce qui demande un futur chantier Catalogue / index / mapping ?

- support natif d'une plage Stephanus brute comme objet localisable;
- mapping canonique debut/fin -> sequence stable de paragraphes/pages;
- eventuelle route ou outil dedie de type `canonical_range`;
- signaux plus nets cote Catalogue pour distinguer texte primaire, notice,
  introduction et commentaire si le produit veut garantir cette priorite.

## Audit logique metier bibliotheque

### Texte primaire vs commentaire / notice

Constat:

- le prompt bibliothecaire rappelle bien de chercher d'abord le texte primaire;
- mais `librarian_agent_first.py` continue a completer certaines demandes par
  `catalog_search` puis premier `passage_context` exploitable;
- `_first_context_params()` prend la premiere position exploitable issue des
  resultats de recherche, sans distinction metier explicite entre texte
  primaire, commentaire, introduction ou notice.

Conclusion:

- la priorite "texte primaire avant commentaire" n'est pas encore garantie par
  la seule logique de continuation agent-first;
- elle depend encore trop du hit de recherche renvoye en tete par Catalogue et
  du guidage prompt.

## Audit Stephanus simple

### Probes directes content-free

Constats verifies:

- recherche accent-sensible: la forme accentuee de l'oeuvre trouve des
  candidats pertinents; la forme non accentuee peut echouer selon le terme;
- `librarian_tools.locate` appelle bien `CatalogueClient.locate`;
- `CatalogueClient.locate` appelle bien `GET /doc/{id}/locate`;
- la route Catalogue renvoie des positions exploitables pour des labels simples
  (`page_no`, `para_no`, `paragraph_id`, `order_index`) sur certains documents;
- ces positions sont bien reutilisables par `passage_context`.

Resume des probes directes:

- recherche oeuvre accentuee: `result_count=10`, docs courts observes:
  `d1f49f74`, `7d025103`, `dabfe4a7`;
- sur `d1f49f74`, labels simples `148e`, `151d`, `126b`, `128a` localisables;
- sur `dabfe4a7`, `126b` et `128a` localisables;
- `passage_context` repond ensuite `200` sur les ancres simples testees.

Conclusion:

- Stephanus simple n'est pas casse par le client FridaDev ni par l'outil
  `locate`;
- il est deja exploitable quand le `document_id` et le label simple sont bons.

## Audit Stephanus intervalle

### Probes directes content-free

Constats verifies:

- la route `/doc/{id}/locate` fait un matching exact sur `milestones.label`;
- les chaines brutes `148e-151d` et `126b-128a` ne sont pas localisables
  directement comme labels uniques;
- le couple `debut + fin` peut etre localise separement quand les labels
  existent;
- le runtime deterministe sait extraire certaines plages bornees lorsque les
  ancres resolues restent compatibles avec ses bornes techniques;
- il ne peut pas extraire toutes les plages canoniques si elles traversent trop
  de paragraphes ou trop de pages.

Conclusion:

- une plage brute n'est pas aujourd'hui un objet Catalogue natif;
- le probleme de `148e-151d` n'est pas seulement un probleme de prompt: il
  manque un support d'index/mapping/outil pour une plage canonique generale.

## Audit agent-first

### Ce qui masque le probleme

Constat:

- en mode agent-first, des cas Stephanus explicites peuvent finir en
  `fallback_repaired` ou en lane utile, tout en restant semantiquement moins
  exacts qu'une extraction canonique;
- `chat_runtime._agent_first_fallback_plan()` replie encore
  `extract_passage` / `extract_range` vers `catalog_search`;
- `librarian_agent_first._complete_agent_loop_if_needed()` poursuit ensuite vers
  `passage_context`, sans passer par `locate`;
- le produit peut donc sembler "vert" avec une consultation approximative alors
  que la demande appelait une resolution canonique explicite.

### Decision

Pour les requetes canoniques explicites avec locator present, l'agent-first ne
doit pas controller la reponse produit tant qu'il ne depasse pas clairement le
chemin exact existant.

## Donnees Catalogue / index

Constats content-free:

- les tables et routes actuelles exposent bien des milestones ponctuels;
- il existe des positions utilisables par `context`;
- l'index actuel ne materialise pas une plage brute Stephanus comme entree
  directement localisable;
- aucun element lu ne prouve aujourd'hui l'existence d'un mapping Catalogue
  natif "148e-151d -> sequence paragraphes/pages" general.

## Correctif applicatif borne retenu

Decision:

- conserver l'agent en comparaison/observabilite;
- conserver l'agent-first pour les recherches thematiques / bibliotheque;
- redonner au deterministe le controle produit des requetes explicites
  `extract_passage` / `extract_range` avec `locator` present.

Effet vise:

- plus de faux vert par `catalog_search -> passage_context` sur une demande
  canonique explicite;
- pas de regression sur les demandes thematiques ou exploratoires;
- aucune modification de Catalogue, de la DB ou du schema d'outils.

## NO-GO / GO par type de chantier

- GO immediat FridaDev:
  - controle deterministe des locators explicites;
  - tests de non-regression;
  - observabilite content-free associee.
- NO-GO immediat sans chantier separe:
  - patch plateforme Catalogue;
  - migration DB;
  - nouveau mapping Stephanus;
  - outil `canonical_range`;
  - garantie forte primaire/commentaire par metadata Catalogue.

## Conclusion

Le probleme Stephanus n'a pas une cause unique. La situation reelle est:

1. les labels simples fonctionnent deja si le `document_id` est bon;
2. les plages brutes ne sont pas un objet Catalogue natif;
3. le chemin agent-first actuel peut encore degrader une demande canonique
   explicite en recherche/context approximatif;
4. le correctif immediat raisonnable cote FridaDev est donc de laisser le
   deterministe controller ces demandes explicites, tout en gardant l'agent
   bibliothecaire pour le reste du travail produit.
