# Frida Biblio librarian agent TODO

Date: 2026-05-31
Statut: TODO active canonique
Classement: `app/docs/todo-todo/product/`
Audit source: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
Contrat source Biblio native: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Contrat source agent Lot 2: `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
Baseline Lot 0: `app/docs/states/baselines/frida-biblio-librarian-agent-lot0-baseline-2026-05-31.md`
Scope: plan produit/runtime pour agent bibliothecaire Frida, lots docs et runtime bornes.

## Objectif produit

Frida doit pouvoir utiliser la bibliotheque comme une vraie bibliotheque, pas seulement comme un parser de requetes ciblees. Elle doit pouvoir comprendre une demande explicite ou implicite, construire ses propres requetes Catalogue, explorer, desambiguiser, consulter des passages, tenir un etat conversationnel Biblio et restituer a l'utilisateur des donnees comme si l'ouvrage etait devant elle, sans inventer une certitude documentaire.

Ce chantier ne livre pas encore l'agent. Il cadre les lots qui devront le livrer.

## Sources lues

- `AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
- `app/docs/todo-done/validations/frida-biblio-real-library-passage-search-validation-2026-05-30.md`
- `app/docs/todo-done/product/frida-biblio-real-library-product-gap-todo.md`
- `app/biblio/`
- `app/core/chat_service.py`
- `app/core/chat_llm_flow.py`
- `app/config.py`
- `app/config.example.py`
- `app/web/`

## Etat courant resume

- Le frontend transmet `biblio_enabled` via `app/web/chat_biblio_mode.js`.
- `app/core/chat_service.py` appelle `run_biblio_chat_turn(data, user_msg=user_msg, ...)`.
- Le runtime Biblio actuel planifie a partir du dernier message utilisateur et exploite maintenant un etat conversationnel Biblio content-free Lot 1 / Lot 1 bis via `message.meta.biblio_state`.
- `CatalogueClient` est GET-only et expose notamment `catalog`, `document`, `metadata`, `chapters`, `locate`, `context`, `search`.
- Le client n'expose pas encore `page` ni `export/chunk`.
- `query_planner.py` reste deterministe et porte deja des intents `list_catalog`, `open_document`, `show_table_of_contents`, `search_catalog`, `extract_passage`, `extract_range`.
- Plusieurs modules Biblio depassent ou frolent 500-600 lignes; les lots doivent eviter d'empiler des regex dans `query_planner.py`.

## Invariants non negociables

- FridaDev reste GET-only cote Catalogue.
- L'agent ne fait aucune ecriture Catalogue.
- L'agent ne fait aucune suppression Catalogue.
- L'agent n'appelle aucune route destructive et n'expose aucune route destructive.
- L'agent ne declenche aucun OCR, re-OCR ou job doc-pipeline.
- L'agent ne modifie pas `/opt/platform/doc-pipeline`.
- L'agent reste separe de Memory/RAG, documents actifs, workspace, Web search, Identity, Summary, Hermeneutic et AnythingLLM.
- Biblio ne devient pas `active_document`.
- Aucun payload brut Catalogue en observabilite.
- Aucun prompt complet en logs.
- Aucun passage brut, texte OCR, titre brut, auteur brut, requete brute utilisateur, secret, token, DSN, cookie ou `.env` dans admin/dashboard/logs/read-model/smokes.
- Les passages et titres peuvent apparaitre seulement dans la lane produit destinee a Frida quand l'utilisateur demande une consultation.
- Aucun `latest/page` ou `latest/context` sans `document_id` explicite resolu.
- Aucun modele agent hardcode.
- Toute configuration modele doit etre observable sans exposer de secret.
- Le critere de verite n'est pas "le modele semble bon", mais "il reussit les cas bibliotheque".
- L'agent bibliothecaire doit rester desactivable par feature flag runtime ou mode parallele jusqu'aux smokes produit valides.
- Le toggle Biblio existant ne doit pas devenir un appel agent obligatoire tant que le lot de branchement n'est pas valide.
- Le chemin Biblio deterministe actuel doit rester disponible ou etre remplace seulement avec preuve de non-regression.
- Le rollback runtime doit etre documente avant toute activation produit de l'agent.

## Modele agent / runtime settings

Invariant cible:

- le modele de l'agent bibliothecaire est configurable via runtime settings;
- le candidat produit par defaut est DeepSeek V4 Pro, si disponible et adapte cote OpenRouter;
- ne pas deviner le slug OpenRouter exact dans le code ou la doc d'implementation;
- verifier le slug, la disponibilite, les capacites JSON/outils, les couts et la latence au moment du lot runtime;
- prevoir un fallback runtime vers un modele plus robuste si DeepSeek V4 Pro est indisponible, trop lent, invalide son JSON ou echoue aux smokes;
- exposer en observabilite content-free le modele effectif, la source de configuration, le fallback eventuel, le timeout, le nombre de retries et le reason code, jamais la cle API.

Implication probable:

- ajouter une section runtime settings dediee, par exemple `biblio_librarian_agent_model`, plutot que reutiliser `main_model`;
- cette section devra avoir `primary_model`, `fallback_model`, `timeout_s`, `temperature`, `top_p`, `max_tokens`, `max_tool_calls`, `json_contract_enabled` ou equivalents;
- les secrets restent ceux du provider OpenRouter deja gere, sans nouveau secret si ce n'est pas necessaire;
- tout ajout de section runtime settings exige tests spec/validation/API/admin.

## OpenRouter / JSON contracts

Invariant dur:

- si l'agent bibliothecaire utilise un contrat JSON, structured output, tool schema, JSON mode ou equivalent, Celebrimbor doit verifier la documentation OpenRouter actuelle avant implementation.

Regles:

- ne pas inventer le format JSON attendu par le provider;
- ne pas supposer qu'un modele respecte strictement un schema sans test;
- tester JSON absent, invalide, tronque, hors contrat, timeout, refus, reponse texte libre et reponse partiellement valide;
- en cas d'echec JSON, pas de fail suspend;
- Frida doit continuer le dialogue par clarification, reponse degradee ou erreur propre;
- les erreurs de contrat doivent etre observables par reason code content-free;
- les schemas internes doivent etre versionnes et testes avec fixtures.

Artefact obligatoire de verification avant implementation:

- [ ] noter la date de verification OpenRouter;
- [ ] lister les URLs OpenRouter consultees;
- [ ] noter le modele/slug observe pour DeepSeek V4 Pro ou le candidat retenu;
- [ ] confirmer ou infirmer les capacites JSON, structured output, tool schema ou JSON mode;
- [ ] ecrire la decision dans cette TODO ou dans une spec source-of-truth;
- [ ] associer les tests JSON/provider a cette decision;
- [ ] definir le fallback si la capacite provider n'est pas confirmee.

## Cas produit obligatoires

Chaque cas ci-dessous doit prouver: outil(s) appele(s), etat Biblio mis a jour ou preserve, passage injecte ou clarification, observabilite content-free, absence de fuite brute hors lane produit.

| Cas | Preuve attendue |
| --- | --- |
| `Montre-moi le catalogue complet.` | `catalog` appele avec limite produit, total/displayed/truncated corrects, lane consultation, aucun payload brut en observabilite. |
| `Il y a 100 ouvrages ? Liste-les tous.` | pagination explicite jusqu'a 100, continuation claire si total > 100, pas de fausse totalite. |
| `Ouvre les oeuvres completes de Platon.` | resolution document/ouvrage, etat `current_document` mis a jour, ambiguite si plusieurs volumes. |
| `Donne-moi la table des matieres du Platon.` | reprise du document courant ou resolution explicite, `chapters` appele, TOC bornee ou pagination, etat conserve. |
| `Trouve le passage du Theetete ou Socrate parle de la maieutique.` | recherche multi-variante, filtre document/oeuvre, contextes consultes, selection ou clarification. |
| `Cherche dans le Theetete le passage sur la sage-femme.` | reformulation theme, recherche dans le meme ouvrage, pas de certitude forcee. |
| `Donne-moi 126b a 128a dans le Theetete.` | `locate` puis `context`, range valide, passage lane, positions et hashes en observabilite. |
| `Continue apres ce passage.` | reprise `last_result`, lecture contexte/page suivante bornee, etat mis a jour. |
| `Montre-moi la page precedente.` | reprise `page_no` et `document_id`, outil page si livre, jamais `latest/page`, borne de chars. |
| `Cherche un autre passage proche.` | exclure ou declasser dernier resultat, relancer recherche/contextes, exposer ambiguite si besoin. |
| `Est-ce que ce passage vient bien du Theetete ?` | verification par etat + Catalogue, reponse prudente, clarification si le passage visible n'a pas d'ancre technique. |

## Lot 0 — Baseline et repros produit

### Objectif

Fixer l'etat de depart avant patch runtime: comportements actuels, limites produit, smokes stricts, cas obligatoires et logs content-free.

### Risque produit traité

Risque de construire l'agent sur une perception floue de l'existant ou de confondre une regression future avec une limite deja connue.

### Plan

- [x] Relire l'audit du 2026-05-31 et cette TODO.
- [x] Executer le smoke strict existant.
- [x] Construire une matrice de repros live content-free pour les cas obligatoires.
- [x] Construire une matrice Catalogue/API/plateforme live content-free:
  - [x] routes disponibles;
  - [x] routes lourdes;
  - [x] routes interdites;
  - [x] `chapters`;
  - [x] `context`;
  - [x] route `page` eventuelle;
  - [x] sante `doc-pipeline-api`;
  - [x] counts DB content-free;
  - [x] endpoint kinds utilises par les smokes.
- [x] Capturer les statuts, reason codes, endpoint kinds, counts, ids courts et hashes seulement.
- [x] Noter les cas qui echouent parce que l'etat conversationnel n'existe pas encore.

### Patch attendu

- [x] Aucun patch runtime.
- [x] Eventuellement une note de baseline sous `app/docs/states/baselines/` si les resultats live divergent de l'audit.
- [x] Pas de modification plateforme.

### Tests / preuves

- [x] `docker exec -w /app platform-fridadev python -m biblio.smoke_live --jsonl`
- [x] repros manuels ou script content-free des cas obligatoires;
- [x] preuve `doc-pipeline-api` health content-free;
- [x] inventaire routes disponibles/lourdes/interdites;
- [x] preuve counts DB content-free sans contenu d'ouvrage;
- [x] preuve endpoint kinds observes dans les smokes;
- [x] `git diff --check` si une note est produite;
- [x] verification que les sorties ne contiennent pas de passage brut hors lane produit.

### Réduction du risque attendue

- [x] Risque reduit par une baseline reproductible et content-free avant changement.

### Critères de sortie

- [x] Matrice des cas obligatoires remplie avec statut courant.
- [x] Matrice Catalogue/API/plateforme remplie avec routes, health, counts DB et endpoint kinds.
- [x] Liste des gaps confirmes.
- [x] Aucun patch runtime.

### Photo operatoire Lot 0 - 2026-05-31

Baseline source: `app/docs/states/baselines/frida-biblio-librarian-agent-lot0-baseline-2026-05-31.md`.

Decision: Lot 0 valide, GO Lot 1 sous conditions.

Resume content-free:

- smoke strict exit code `0`;
- endpoint kinds observes: `catalog`, `search`, `context`, `chapters`;
- matrice produit P01-P11 remplie sans requete brute ni passage brut;
- `state_present=false` pour tous les cas produit;
- gaps P1 confirmes: etat Biblio absent, planning deterministe fragile, navigation/verification impossibles sans ancre technique;
- matrice API: `GET /health` HTTP `200`, OpenAPI `33` routes GET et `6` routes mutantes;
- counts DB: `documents=10`, `document_chapters=973`, `pages=4837`, `paragraphs=101421`, `raw_units=378034`, `catalogue_human_metadata=10`;
- routes dangereuses confirmees: `/doc/{id}` lourd, `latest/page` et `latest/context` interdits par invariant et non utilisables comme base agentique;
- aucun patch runtime, aucun patch plateforme, aucun rebuild.

### Hors-scope

- Agent LLM.
- Nouvel etat conversationnel.
- Nouvelles routes Catalogue.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / GO-NO-GO Lot 1`.

## Lot 1 — Etat Biblio conversationnel explicite

### Objectif

Creer un etat Biblio interne par conversation qui porte les references techniques necessaires a la reprise.

Lot 1 est un lot d'etat conversationnel explicite. Il doit preparer les ancres techniques et les clarifications propres, pas resoudre tout le planner, pas ajouter l'outil page et pas livrer l'agent complet.

### Risque produit traité

Risque que Frida reponde a "continue", "ce passage", "la page precedente" ou "dans ce meme ouvrage" avec une memoire floue issue du dialogue visible.

### Plan

- [x] Definir `BiblioConversationState` avec `schema_version`.
- [x] Porter au minimum `current_document`, `current_work`, `page_no`, `para_no`, `paragraph_id`, dernier passage hash, dernier resultat exploitable, derniers candidats, derniere ambiguite, dernier intent.
- [x] Trancher explicitement la frontiere de persistance: memoire process seule, etat attache a la conversation, persistance content-free, survie reload navigateur, survie reprise de conversation et survie rebuild/restart.
- [x] Garantir au minimum que "continue", "page precedente" et "ce passage" survivent au reload/reprise de conversation si le produit promet cette reprise.
- [x] Si la survie reload/reprise/rebuild n'est pas livree dans ce lot, forcer une clarification propre plutot qu'une reprise inventee.
- [x] Lire l'etat avant planning Biblio.
- [x] Mettre a jour l'etat apres resolution, TOC, extraction, recherche, navigation ou clarification.
- [x] Garder l'etat interne non content-rich: ids, positions, hashes, counts, reason codes.
- [x] Ne pas deduire `document_id`, `page_no`, `para_no` ou `paragraph_id` seulement du dialogue recent.
- [x] Traiter P08 et P11 comme criteres centraux du lot: reprise depuis `last_result` et verification par ancre technique.
- [x] Garder P03 et P09 comme cas de regression a surveiller: P03 depend aussi du planner/intention, P09 depend aussi d'un outil page non expose par `CatalogueClient`.
- [x] Clarifier proprement si l'etat, le planner ou l'outillage manque, sans promettre une correction complete de P03/P09 dans ce lot.

### Frontiere de persistance minimale

- [x] documenter la decision de persistance dans le patch du lot: process-only, conversation-attached ou persiste content-free;
- [x] si reprise produit promise: faire survivre `document_id`, `page_no`, `para_no`, `paragraph_id`, dernier passage hash et dernier resultat exploitable apres sauvegarde normale reussie;
- [x] si reprise produit promise: faire survivre ces references a la reprise de conversation apres sauvegarde normale reussie;
- [x] si l'etat n'a pas encore ete sauvegarde ou manque apres redemarrage: produire une clarification propre au lieu d'inventer une position;
- [x] tester le chemin store fake save/load de `message.meta.biblio_state`;
- [x] ne jamais persister de passage brut, prompt complet, payload Catalogue, titre brut, auteur brut ou requete brute;
- [x] ne jamais exposer ces champs bruts en observabilite.

Decision livree Lot 1, corrigee Lot 1 bis:

- mode: etat persiste content-free dans `message.meta.biblio_state` du dernier message utilisateur;
- attachement: un etat ancien reste dans l'historique sauvegarde, mais n'est pas recopie sur chaque nouveau message utilisateur;
- toggle Biblio off: aucune consultation, aucune mise a jour d'etat, aucun nouveau tamponnage Biblio du message courant;
- attachement nouveau: seulement si le tour courant porte une transition Biblio utile, par consultation, extraction, TOC, ambiguite ou clarification explicite;
- portee: etat rattache a la conversation par les messages existants, sans nouvelle table ni schema DB;
- survie reload/reprise/rebuild: garantie seulement apres sauvegarde normale reussie de la conversation;
- observabilite: `state_transition.persistence_status=pending_normal_conversation_save` au moment de l'event Biblio;
- avant sauvegarde ou si l'etat manque: clarification propre, jamais reprise inventee;
- aucune ecriture Catalogue, aucun OCR, aucune route mutante, aucun `latest/page` ou `latest/context`.

### Patch attendu

- [x] Nouveau module dedie, par exemple `app/biblio/conversation_state.py`.
- [x] Integration dans `chat_service.py` ou `chat_runtime.py` sans grossir les fichiers au-dela du raisonnable.
- [x] Tests unitaires de read/update/clear.
- [x] Event content-free `biblio_state_*`.

### Tests / preuves

- [x] Tests unitaires sur serialisation content-free.
- [x] Test multi-tour: ouvrir Platon -> demander TOC sans renommer Platon.
- [x] Test multi-tour: extraire Theetete 126b -> "continue apres ce passage".
- [x] Test multi-tour: passage trouve -> "page precedente".
- [x] Test fake-store: sauvegarde normale puis relecture des messages DB preserve `meta.biblio_state`.
- [x] Tests reprise "continue", "page precedente" et "page suivante" par clarification propre si l'outil page manque.
- [x] Tests toggle off / tour non utilise: ancien etat conserve dans l'historique, pas de recopie sur le message courant.
- [x] Verification absence de passage brut dans l'etat observe.

### Réduction du risque attendue

- [x] Risque reduit par une source technique explicite de reprise; risque rendu observable par reason codes quand l'etat manque.

### Critères de sortie

- [x] Les references techniques ne dependent pas du dialogue visible.
- [x] La frontiere de persistance est explicite et prouvee ou limitee par clarification propre.
- [x] Reload/reprise sont testes si le produit promet la reprise.
- [x] Les cas de navigation savent echouer proprement si l'etat est absent.
- [x] Aucun contenu brut durable hors lane produit.
- [x] Lot 1 ne modifie pas le planner/intention hors adaptation minimale necessaire a lire/ecrire l'etat.
- [x] Lot 1 n'ajoute pas l'outil page et ne livre pas la navigation complete.

Photo operatoire Lot 1 - 2026-05-31:

- `app/biblio/conversation_state.py` porte `BiblioConversationState`, `BiblioStateTransition`, serialisation, lecture/ecriture et mise a jour content-free;
- `app/biblio/conversation_followup.py` porte la detection bornee de follow-up et la clarification content-free;
- `app/biblio/chat_runtime.py` lit l'etat avant le plan, l'applique seulement au cas TOC sans cible quand un `document_id` courant existe, met a jour l'etat apres consultation et clarifie les reprises sans ancre/outillage;
- `app/core/chat_service.py` lit l'etat depuis la conversation et rattache l'etat produit au dernier message utilisateur seulement si le tour courant produit une transition Biblio;
- `app/biblio/observability.py` expose `state` et `state_transition` sans payload brut, avec persistance marquee pending jusqu'a sauvegarde normale;
- `app/biblio/conversation_state.py` depasse temporairement 500 lignes mais reste borne a la responsabilite etat/projection; Lot 2 ne doit pas l'alourdir sans extraction dediee;
- P03 et P09 restent des surveillances de regression, pas des promesses de correction complete du Lot 1;
- aucun agent LLM, aucun OpenRouter, aucun outil page, aucune route Catalogue mutante, aucun `latest/page` ou `latest/context`.

### Hors-scope

- Planner LLM.
- Refonte du planner deterministe ou de la detection d'intention.
- Ajout de l'outil page dans `CatalogueClient`.
- Navigation page precedente/suivante complete.
- Nouvelle route Catalogue.
- Agent bibliothecaire complet.
- Persistance long terme riche.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / GO-NO-GO Lot 2`.

## Lot 2 — Contrat agent bibliothecaire

### Objectif

Definir le contrat d'entree/sortie de l'agent, ses actions, limites, budgets, timeouts, modele runtime-configurable et fallback.

### Risque produit traité

Risque d'introduire un agent non testable, non observable ou lie a un modele hardcode.

### Plan

- [x] Specifier les entrees: message courant, dialogue recent borne, etat Biblio, catalogue tool registry, budgets.
- [x] Specifier les sorties: action plan, tool calls demandes, reponse structuree, mise a jour d'etat, lane candidate, clarification.
- [x] Versionner le schema interne cible.
- [x] Ajouter un contrat OpenRouter/JSON comme gate obligatoire avant implementation runtime.
- [x] Rendre obligatoire l'artefact date OpenRouter/JSON avant tout appel agent: date, URLs, modele/slug observe, capacites confirmees ou non, decision, tests et fallback.
- [x] Prevoir fallback modele et fallback deterministe.
- [x] Interdire toute action non allowlistee.

### Patch attendu

- [x] Spec contractuelle dediee avant runtime complet: `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`.
- [x] Contrat runtime settings pour modele agent: primary/fallback/timeouts/budgets, sans implementation runtime dans ce lot.
- [x] Tests de validation de configuration specifies comme gates avant runtime.
- [x] Observabilite modele effective sans secret specifiee comme contrat.

### Tests / preuves

- [x] Tests de schema valide/invalide listes comme exigences avant runtime.
- [x] Tests JSON absent, invalide, tronque, hors contrat, refus, texte libre listes comme exigences avant runtime.
- [x] Test lie a l'artefact OpenRouter specifie: slug observe, capacites declarees, format payload attendu et fallback si non confirme.
- [x] Test fallback modele specifie.
- [x] Test aucun fail suspend specifie: Frida obtient clarification ou erreur propre.
- [x] Preuves docs-only Lot 2: `git diff --check`, `git diff --cached --check`, grep contractuel et relecture du diff utile.

### Réduction du risque attendue

- [x] Risque reduit par contrat versionne et par degradation exigee; risque rendu observable par status et reason codes.

### Critères de sortie

- [x] Aucun modele hardcode dans le contrat.
- [x] DeepSeek V4 Pro est seulement candidat runtime a verifier, pas slug invente.
- [x] Artefact OpenRouter date et source rendu obligatoire avant implementation runtime.
- [x] JSON/tool contract documente comme gate a verifier selon OpenRouter actuel avant implementation.
- [x] Fallback modele et fallback deterministe specifies; preuve runtime obligatoire avant activation agent.

Photo operatoire Lot 2 - 2026-05-31:

- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md` livre le contrat normatif agent bibliothecaire;
- le futur agent reste `off` par defaut et pilote par feature flag/mode runtime;
- le toggle `biblio_enabled` autorise Biblio mais ne force pas le futur agent;
- le modele agent est runtime-configurable, jamais hardcode;
- DeepSeek V4 Pro reste candidat a verifier, sans slug invente;
- l'artefact OpenRouter/JSON date est un gate bloquant avant tout appel modele agent;
- le schema conceptuel `biblio_librarian_agent_v1` est defini;
- les outils futurs sont limites a un registre GET-only explicite;
- `latest/page`, `latest/context`, routes mutantes et `GET /doc/{id}` automatique/non borne restent interdits;
- l'observabilite agent doit rester content-free;
- aucun runtime agent, aucun appel OpenRouter, aucun outil page, aucun rebuild.

### Hors-scope

- Boucle outil complete.
- Ranking final.
- UI admin avancee.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / OPENROUTER DOC CHECK / GO-NO-GO Lot 3`.

## Lot 3 — Outils Catalogue GET-only pour agent

### Objectif

Exposer a l'agent un registre d'outils Catalogue strictement GET-only, borne et observable.

### Risque produit traité

Risque qu'un agent LLM appelle une route lourde, destructive, non bornee ou non observee.

### Plan

- [ ] Transformer les capacites existantes en outils: `catalog`, `metadata`, `chapters`, `locate`, `search`, `context`.
- [ ] Ajouter seulement si necessaire `page` avec `document_id` explicite, bornes de chars et interdiction `latest/page`.
- [ ] Ajouter seulement si necessaire `export/chunk` borne et explicite, jamais automatique.
- [ ] Refuser toute methode non GET.
- [ ] Refuser `PUT`, `POST`, `DELETE`, `settings`, `progress clear`, routes destructive UI et path hors allowlist.
- [ ] Ajouter timeouts par outil.

### Patch attendu

- [ ] Nouveau module outil dedie, par exemple `app/biblio/librarian_tools.py`.
- [ ] Event observations compactes par appel.
- [ ] Tests d'allowlist.
- [ ] Pas de patch `/opt/platform/doc-pipeline` sauf lot Sauron separe.

### Tests / preuves

- [ ] Tests outils nominal: catalog/search/chapters/locate/context.
- [ ] Tests interdiction routes mutatrices.
- [ ] Tests interdiction `latest/page` et `latest/context`.
- [ ] Tests parametres bornes.
- [ ] Test timeout content-free.

### Réduction du risque attendue

- [ ] Risque bloque par allowlist et method guard; risque rendu observable par endpoint kind/status/duration/counts.

### Critères de sortie

- [ ] L'agent ne peut appeler que des outils GET definis.
- [ ] Chaque outil retourne contenu interne ou lane candidate sans payload brut en observabilite.
- [ ] Les routes lourdes sont explicitement bornees ou refusees.

### Hors-scope

- Choix autonome de sequence.
- Edition Catalogue.
- OCR.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / GET-ONLY PROOF / GO-NO-GO Lot 4`.

## Lot 4 — Planner agentique / boucle bibliothecaire

### Objectif

Permettre a l'agent de choisir plusieurs requetes successives: chercher, ouvrir, comparer, desambiguiser, demander plus de contexte.

### Risque produit traité

Risque que Frida reste bloquee sur une seule regex ou une seule recherche lexicale ratee.

### Plan

- [ ] Introduire une boucle bornee: planifier -> appeler outil -> observer -> decider suite -> finaliser.
- [ ] Garder l'agent off par defaut ou en mode parallele tant que les smokes produit ne sont pas valides.
- [ ] Garantir que le toggle Biblio existant ne force pas l'appel agent tant que le branchement produit n'est pas valide.
- [ ] Comparer le chemin agentique au chemin deterministe actuel avant remplacement.
- [ ] Budget nominal: nombre max d'appels, variantes, contextes, duree totale.
- [ ] Requetes alternatives pour accents, paraphrases, auteur/oeuvre/theme.
- [ ] Stop sur certitude insuffisante.
- [ ] Sortie clarification quand plusieurs chemins restent plausibles.
- [ ] Fallback deterministe si agent indisponible.

### Patch attendu

- [ ] Module agent runtime dedie, par exemple `app/biblio/librarian_agent.py`.
- [ ] Adaptateur OpenRouter ou reuse d'un caller existant si frontieres claires.
- [ ] Tests avec faux Catalogue et faux modele.
- [ ] Feature flag runtime ou mode parallele.
- [ ] Rollback runtime documente avant activation produit.

### Tests / preuves

- [ ] `Sapere aude` dans Kant: separation document/expression.
- [ ] Theetete/maieutique: variantes et contextes.
- [ ] Sage-femme: reformulation.
- [ ] JSON invalide puis fallback/clarification.
- [ ] Budget depasse -> erreur propre.
- [ ] Smokes comparatifs avant/apres: catalogue, TOC, passage exact, recherche thematique.
- [ ] Test agent desactive: chemin deterministe encore disponible ou remplacement prouve sans regression.

### Réduction du risque attendue

- [ ] Risque reduit par iteration bornee; risque accepte si Catalogue ne contient pas le passage et que l'agent le signale proprement.

### Critères de sortie

- [ ] L'agent execute plusieurs etapes sans fuite.
- [ ] L'agent peut rester desactive ou parallele.
- [ ] Le chemin deterministe actuel reste disponible ou son remplacement est prouve par smokes comparatifs.
- [ ] Les reason codes distinguent not_found, ambiguous, budget_exhausted, model_failed, catalogue_failed.
- [ ] Aucun blocage technique visible comme consigne systeme.

### Hors-scope

- Persistance longue des passages bruts.
- Recherche semantique vectorielle globale.
- Modification Catalogue.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / BUDGETS / GO-NO-GO Lot 5`.

## Lot 5 — Comprehension implicite et dialogue

### Objectif

Faire cooperer dialogue recent et etat Biblio explicite pour comprendre les demandes implicites.

### Risque produit traité

Risque que l'agent interprete "le passage", "dans ce meme ouvrage" ou "c'est tout ?" sans ancre technique fiable.

### Plan

- [ ] Injecter a l'agent une synthese content-free de l'etat Biblio.
- [ ] Fournir un dialogue recent borne pour interpretation linguistique.
- [ ] Declarer que l'etat technique prime sur la memoire conversationnelle floue.
- [ ] Gerer les references anaphoriques: ce passage, ce livre, meme ouvrage, plus haut, apres.
- [ ] Demander clarification si l'etat est absent ou contradictoire.

### Patch attendu

- [ ] Extension du contrat agent et de l'etat.
- [ ] Tests multi-tour.
- [ ] Reason codes pour anaphore resolue ou impossible.

### Tests / preuves

- [ ] Ouvrir Platon -> "donne-moi la table des matieres".
- [ ] Passage Theetete -> "continue".
- [ ] Ambiguite -> "le deuxieme".
- [ ] Etat absent -> clarification propre.

### Réduction du risque attendue

- [ ] Risque reduit par priorite donnee aux references techniques; risque rendu observable quand l'anaphore ne peut pas etre resolue.

### Critères de sortie

- [ ] Les demandes implicites principales passent ou clarifient.
- [ ] Aucune reference technique n'est inventee depuis le dialogue.

### Hors-scope

- Memoire longue hors conversation.
- Resume automatique des ouvrages.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / MULTI-TURN PROOF / GO-NO-GO Lot 6`.

## Lot 6 — Navigation bibliotheque

### Objectif

Gerer les commandes de navigation: continue, avant, apres, autour de ce passage, dans ce meme ouvrage, autre passage, table des matieres, liste tout le catalogue.

### Risque produit traité

Risque que Frida ne sache pas se deplacer dans un ouvrage deja consulte.

### Plan

- [ ] Ajouter intents de navigation structures.
- [ ] Utiliser `last_result` et `current_document`.
- [ ] Lire page/contexte voisin avec bornes.
- [ ] Paginer catalogue et TOC.
- [ ] Ne jamais utiliser `latest/page` ou `latest/context`.
- [ ] Clarifier si l'etat ne suffit pas.

### Patch attendu

- [ ] Outils page/contexte voisins si route client sure.
- [ ] Mise a jour etat apres navigation.
- [ ] Tests de pagination catalogue/TOC.

### Tests / preuves

- [ ] "Continue apres ce passage."
- [ ] "Montre-moi la page precedente."
- [ ] "Remonte un peu."
- [ ] "Cherche un autre passage proche."
- [ ] "Il y a 100 ouvrages ? Liste-les tous."

### Réduction du risque attendue

- [ ] Risque reduit par navigation explicite et bornee; risque bloque par garde `document_id` obligatoire.

### Critères de sortie

- [ ] Navigation fonctionne sur etat valide.
- [ ] Navigation clarifie sur etat absent.
- [ ] Observabilite expose positions/hashes/counts seulement.

### Hors-scope

- Chargement illimite d'ouvrage.
- Export complet automatique.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / NAVIGATION MATRIX / GO-NO-GO Lot 7`.

## Lot 7 — Selection / ranking / prudence

### Objectif

Selectionner sans forcer une certitude quand plusieurs ouvrages, chapitres ou passages sont plausibles.

### Risque produit traité

Risque de citation faussement certaine ou d'attribution incorrecte.

### Plan

- [ ] Reutiliser et etendre `passage_selection.py`.
- [ ] Definir seuils explicites de selection et d'ambiguite.
- [ ] Tenir compte du document cible, de la proximite theme, de positions, de scores Catalogue et de preuves contextuelles.
- [ ] Presenter candidats ou demander clarification quand l'ecart est insuffisant.
- [ ] Ne pas transformer un candidat en passage certain sans preuve.

### Patch attendu

- [ ] Selection agentique content-free.
- [ ] Tests de score gap et ambiguite.
- [ ] Lane produit qui distingue candidat, passage retenu et clarification.

### Tests / preuves

- [ ] Theetete maieutique ambigu.
- [ ] Sage-femme avec plusieurs candidats.
- [ ] Verification "vient bien du Theetete ?".
- [ ] Cas meilleur candidat faible -> clarification.

### Réduction du risque attendue

- [ ] Risque reduit par seuils et par clarification; risque accepte si Catalogue/OCR ne permet pas de trancher.

### Critères de sortie

- [ ] Les cas ambigus ne sont pas presentes comme certains.
- [ ] Les candidats plausibles peuvent etre montres a Frida pour reponse naturelle prudente.

### Hors-scope

- Annotation humaine Catalogue.
- Correction OCR.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / SELECTION PROOF / GO-NO-GO Lot 8`.

## Lot 8 — Injection lane et reponse Frida

### Objectif

Donner a Frida les passages consultes, les limites et les ambiguities dans une lane claire, pour une reponse naturelle et prudente.

### Risque produit traité

Risque que la reponse finale efface les incertitudes de l'agent ou pretende avoir lu plus que la lane.

### Plan

- [ ] Versionner la lane agent bibliothecaire.
- [ ] Inclure statut, document, positions, passages bornes, candidats, limites.
- [ ] Indiquer explicitement ambiguite ou not_found.
- [ ] Ne pas injecter tout ouvrage.
- [ ] Garder la lane avant le dernier message utilisateur, comme Biblio actuel, sauf preuve contraire.

### Patch attendu

- [ ] Adaptation de `prompt_lane.py` ou nouveau builder dedie.
- [ ] Tests d'injection et de neutralisation marqueurs.
- [ ] Tests que `BiblioPromptLane.message` ou equivalent ne sort pas en observabilite.

### Tests / preuves

- [ ] Passage exact injecte.
- [ ] Ambiguite injectee comme ambiguite.
- [ ] Catalogue complet injecte comme consultation bornee.
- [ ] Prompt/log/admin sans lane complete.

### Réduction du risque attendue

- [ ] Risque reduit par un contrat de lane explicite; risque rendu observable par counts/chars/hashes.

### Critères de sortie

- [ ] Frida peut repondre naturellement avec prudence.
- [ ] La lane ne fuit pas dans les surfaces techniques.

### Hors-scope

- Changement du contrat principal de sortie assistant.
- Streaming UI.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / LANE PROOF / GO-NO-GO Lot 9`.

## Lot 9 — Observabilite content-free

### Objectif

Rendre le chemin bibliothecaire lisible par l'operateur sans exposer le contenu des ouvrages.

### Risque produit traité

Risque de debug impossible ou de fuite de contenu/prompt/payload.

### Plan

- [ ] Definir events agent: start, tool_call, selection, state_update, fallback, final.
- [ ] Exposer endpoint kinds, durees, status, counts, ids courts, positions, hashes, model source, budgets.
- [ ] Interdire passages, pages, titres bruts, auteurs bruts, requetes utilisateur brutes, payloads et prompts complets.
- [ ] Etendre admin/dashboard/read-model seulement avec projections compactes.

### Patch attendu

- [ ] Projection observability dediee.
- [ ] Tests anti-fuite.
- [ ] Read-model/dashboard si besoin.

### Tests / preuves

- [ ] Unitaires anti-fuite.
- [ ] Smoke strict agent.
- [ ] Dashboard/read-model sans contenu brut.
- [ ] Modele effectif observable sans secret.

### Réduction du risque attendue

- [ ] Risque reduit par projections compactes; risque bloque par tests anti-fuite.

### Critères de sortie

- [ ] Chaque tour agentique est audit-able content-free.
- [ ] Aucune surface technique ordinaire ne montre contenu d'ouvrage.

### Hors-scope

- Vue lecteur affichant passages complets.
- Export d'audit content-rich.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / OBSERVABILITY PROOF / GO-NO-GO Lot 10`.

## Lot 10 — Smokes produit philosophiques

### Objectif

Creer une suite de smokes produit live couvrant les cas bibliotheque centraux.

### Risque produit traité

Risque de livrer un agent qui passe les unitaires mais echoue les demandes philosophiques reelles.

### Plan

- [ ] Etendre `app/biblio/smoke_live.py` ou creer un runner agent dedie.
- [ ] Couvrir catalogue complet, 100 ouvrages, Platon, Theetete, maieutique, sage-femme, 126b-128a, navigation, verification et ambiguite.
- [ ] Sorties strictement content-free.
- [ ] Exit code non zero si fuite ou violation de statut attendu.

### Patch attendu

- [ ] Runner smoke agent.
- [ ] Fixtures attendues content-free.
- [ ] Documentation des cas et resultats.

### Tests / preuves

- [ ] `docker exec -w /app platform-fridadev python -m biblio.smoke_librarian_agent_live --jsonl`
- [ ] Verification `raw_marker_leaks=false`.
- [ ] Verification `payload_objects_retained=0`.
- [ ] Verification des endpoint kinds et state updates attendus.

### Réduction du risque attendue

- [ ] Risque reduit par validation produit live; risque rendu observable par matrice de cas.

### Critères de sortie

- [ ] Tous les cas obligatoires passent ou produisent une clarification explicitement acceptee.
- [ ] Aucune fuite brute.

### Hors-scope

- Benchmark exhaustif du fonds.
- Mesure qualite philosophique humaine complete.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / SMOKE MATRIX / GO-NO-GO Lot 11`.

## Lot 11 — Timeouts, retries, degradation

### Objectif

Definir budgets, retries, fallback modele, fallback deterministe, clarification utilisateur et absence de suspension.

### Risque produit traité

Risque que l'agent se bloque, coute trop cher, attende trop longtemps ou expose une erreur technique brute.

### Plan

- [ ] Budgets par tour: appels outils, appels modele, duree totale, contextes, variantes, chars lane.
- [ ] Timeouts par outil Catalogue et par appel modele.
- [ ] Retries bornes sur timeout/transient.
- [ ] Fallback modele si modele principal indisponible ou invalide JSON.
- [ ] Fallback deterministe si agent indisponible.
- [ ] Degradation: clarification, reponse bornee, erreur propre.

### Patch attendu

- [ ] Configuration runtime budgets/timeouts.
- [ ] Tests timeout modele, timeout Catalogue, JSON invalide, budget depasse.
- [ ] Observabilite reason codes.

### Tests / preuves

- [ ] Faux modele timeout.
- [ ] Faux Catalogue timeout.
- [ ] JSON tronque.
- [ ] Outil trop lent.
- [ ] Aucune fail suspend.

### Réduction du risque attendue

- [ ] Risque reduit par budgets et fallback; risque accepte temporairement si le fallback deterministe couvre moins de cas mais reste propre.

### Critères de sortie

- [ ] Tous les echecs techniques aboutissent a clarification/reponse degradee/erreur propre.
- [ ] Les budgets sont visibles content-free.

### Hors-scope

- Optimisation cout fine.
- Choix definitif permanent du modele.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / DEGRADATION PROOF / GO-NO-GO Lot 12`.

## Lot 12 — Validation finale et archivage

### Objectif

Decider GO/NO-GO produit, mettre a jour les docs vivantes et archiver la TODO si le chantier est livre.

### Risque produit traité

Risque de declarer trop vite que Frida a une bibliotheque produit devant elle.

### Plan

- [ ] Rejouer tous les smokes stricts.
- [ ] Rejouer les cas obligatoires en live.
- [ ] Verifier GET-only et anti-fuite.
- [ ] Verifier rollback feature flag.
- [ ] Verifier agent off / mode parallele avant activation produit.
- [ ] Rejouer les smokes comparatifs avant/apres: catalogue, TOC, passage exact, recherche thematique.
- [ ] Documenter limites restantes.
- [ ] Mettre a jour README, `app/docs/README.md`, `AGENTS.md` si la TODO est archivee.

### Patch attendu

- [ ] Note de validation finale sous `app/docs/todo-done/validations/`.
- [ ] TODO deplacee sous `app/docs/todo-done/product/` seulement si tous les criteres sont atteints.
- [ ] Docs d'index mises a jour.

### Tests / preuves

- [ ] Unitaires agent.
- [ ] Contrats chat/admin/dashboard/read-model.
- [ ] Smokes live agent.
- [ ] Smokes comparatifs agent vs deterministe.
- [ ] Test rollback runtime.
- [ ] Test toggle Biblio avec agent off.
- [ ] `git diff --check`.
- [ ] Status final propre.

### Réduction du risque attendue

- [ ] Risque reduit par validation live et archivage conditionnel; risque restant documente s'il ne bloque pas le GO.

### Critères de sortie

- [ ] GO produit seulement si les cas bibliotheque passent ou clarifient proprement.
- [ ] NO-GO si etat multi-tour, GET-only, anti-fuite ou fallback echoue.
- [ ] NO-GO si agent off/rollback n'est pas prouve.
- [ ] NO-GO si les smokes comparatifs regressent catalogue, TOC, passage exact ou recherche thematique.
- [ ] Aucun rebuild plateforme implicite.

### Hors-scope

- Nouveaux chantiers Catalogue.
- OCR ou correction du fonds.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / FINAL GO-NO-GO / COMMIT-PUSH`.

## Risques documentes mais non corriges par cette TODO

- Pas encore d'agent bibliothecaire runtime.
- Contrat agent bibliothecaire Lot 2 livre, mais pas encore implemente.
- Etat Biblio conversationnel Lot 1/Lot 1 bis livre et exploite, mais borne a un etat content-free, un attachement conditionnel, des clarifications et une persistance seulement apres sauvegarde normale reussie.
- Pas encore d'outil page cote FridaDev; P09 reste une surveillance, pas une promesse de navigation complete.
- P03 reste une surveillance planner/intention, pas une promesse de correction complete par l'etat Lot 1.
- Pas encore de navigation precedente/suivante complete cote FridaDev.
- Pas encore de verification OpenRouter actuelle pour JSON/structured outputs; l'artefact date reste gate obligatoire avant implementation runtime.
- Pas encore de section runtime settings implementee pour le modele agent.
- Pas encore de preuve runtime fallback modele/fallback deterministe agent.

## Risques que la future architecture devra reduire

- Mauvaise attribution ouvrage/passage.
- Recherches lexicales rates a cause des accents ou paraphrases.
- Ambiguite forcee en certitude.
- Routes lourdes ou timeouts.
- Fuite de contenu dans logs/admin/dashboard.
- Blocage technique sur JSON invalide ou modele indisponible.

## Risques acceptes temporairement

- L'agent runtime n'est pas encore livre; la TODO a commence docs-only, puis Lot 1/Lot 1 bis ont livre l'etat conversationnel applicatif.
- DeepSeek V4 Pro reste candidat, pas engagement de slug ou de disponibilite.
- Les routes Catalogue manquantes ou lourdes restent hors scope FridaDev jusqu'a lot dedie.
- Les corrections OCR/metadata restent hors scope agent.

## GO / NO-GO courant

Lot 0 valide.

Lot 1 et correction Lot 1 bis livres.

Lot 2 contrat/spec agent bibliothecaire livre.

NO-GO pour declarer l'agent bibliothecaire produit livre.

GO conditionnel pour ouvrir le Lot 3 comme lot registre d'outils Catalogue GET-only, sans modele agent, sans boucle agentique, sans outil page et sans activation runtime.

NO-GO pour coder directement l'agent.

NO-GO pour faire deborder Lot 3 vers outil page, navigation complete, OpenRouter non verifie ou agent bibliothecaire complet.

Risques restants reels: agent absent, outil page absent, OpenRouter/JSON non verifie, modele agent non configure, fallback agent non prouve.
