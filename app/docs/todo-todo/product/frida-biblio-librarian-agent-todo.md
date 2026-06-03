# Frida Biblio librarian agent TODO

Date: 2026-05-31
Statut: TODO active canonique
Classement: `app/docs/todo-todo/product/`
Audit source: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
Contrat source Biblio native: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Contrat source agent Lot 2: `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
Matrice d'action produit complementaire: `app/docs/todo-todo/product/frida-biblio-refonte.md`
Baseline Lot 0: `app/docs/states/baselines/frida-biblio-librarian-agent-lot0-baseline-2026-05-31.md`
Verification OpenRouter courante: `app/docs/states/baselines/frida-biblio-librarian-agent-openrouter-gpt52-2026-06-02.md`
Scope: plan produit/runtime pour agent bibliothecaire Frida, lots docs et runtime bornes.

## Objectif produit

Frida doit pouvoir utiliser la bibliotheque comme une vraie bibliotheque, pas seulement comme un parser de requetes ciblees. Elle doit pouvoir comprendre une demande explicite ou implicite, construire ses propres requetes Catalogue, explorer, desambiguiser, consulter des passages, tenir un etat conversationnel Biblio et restituer a l'utilisateur des donnees comme si l'ouvrage etait devant elle, sans inventer une certitude documentaire.

Ce chantier livre progressivement l'agent. Le Lot 7 livre seulement le socle
agentique borne, non active par defaut et compare au deterministe; il ne livre
pas encore le remplacement produit du chemin Biblio actuel.

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
- `CatalogueClient` est GET-only et expose notamment `catalog`, `document`, `metadata`, `chapters`, `page`, `locate`, `context`, `search`.
- Le client n'expose toujours pas `export/chunk`.
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
- le candidat produit courant par defaut est `openai/gpt-5.2`;
- ne pas deviner le slug OpenRouter exact hors verification documentaire et preuve live ciblee;
- verifier le slug, la disponibilite, les capacites JSON/outils, les couts et la latence au moment du lot runtime;
- prevoir un fallback runtime vers un autre modele robuste si `openai/gpt-5.2` devient indisponible, trop lent, invalide son JSON ou echoue aux smokes;
- exposer en observabilite content-free le modele effectif, la source de configuration, le fallback eventuel, le timeout, le nombre de retries et le reason code, jamais la cle API.

Implication livree partiellement:

- section runtime settings dediee `biblio_librarian_agent`;
- cette section a `mode`, `primary_model`, `fallback_model`, `timeout_s`,
  `temperature`, `top_p`, `max_tokens`, `max_tool_calls`, `max_model_calls`,
  `max_recent_turns` et `reasoning_effort`;
- le contrat JSON est obligatoire dans le Lot 7; aucun knob operateur ne doit permettre de le desactiver sans lot separe;
- les secrets restent ceux du provider OpenRouter deja gere via
  `main_model.api_key`; aucune cle dediee Biblio;
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
- [ ] noter le modele/slug observe pour le candidat retenu;
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

- [x] Transformer les capacites existantes en outils agent contractuels:
  `catalog_list`, `catalog_search`, `document_open_summary`, `document_toc`,
  `locate`, `passage_context`.
- [x] Distinguer explicitement noms d'outils agent et routes internes:
  `catalog_list` / `catalog_search` peuvent s'appuyer sur `GET /catalog` ou
  `GET /search`, `document_open_summary` sur `GET /catalog` et
  `GET /doc/{id}/metadata`, `document_toc` sur `GET /doc/{id}/chapters`,
  `locate` sur `GET /doc/{id}/locate`, `passage_context` sur
  `GET /doc/{id}/context`.
- [x] Garder `page_read` hors Lot 3: futur outil explicite seulement, avec GO
  separe, route/client sure, `document_id` explicite, bornes, tests et
  interdiction `latest/page`.
- [x] Garder `export/chunk` hors Lot 3: futur lot optionnel seulement avec GO
  explicite, jamais automatique ni opportuniste.
- [x] Refuser toute methode non GET.
- [x] Refuser `PUT`, `POST`, `DELETE`, `settings`, `progress clear`, routes destructive UI et path hors allowlist.
- [x] Appliquer le timeout Catalogue existant a chaque appel outil; aucun
  timeout agent/model additionnel tant que l'agent runtime est absent.

### Patch attendu

- [x] Nouveau module outil dedie: `app/biblio/librarian_tools.py`.
- [x] Event observations compactes par appel.
- [x] Tests d'allowlist.
- [x] Pas de patch `/opt/platform/doc-pipeline`.

### Tests / preuves

- [x] Tests outils nominaux: `catalog_list`, `catalog_search`,
  `document_open_summary`, `document_toc`, `locate`, `passage_context`.
- [x] Tests interdiction routes mutatrices par absence d'API outil mutatrice et
  reutilisation exclusive des methodes publiques GET du `CatalogueClient`.
- [x] Tests interdiction `latest/page` et `latest/context`.
- [x] Tests interdiction `page_read` dans le scope Lot 3.
- [x] Tests interdiction `export/chunk` automatique ou opportuniste dans le scope Lot 3.
- [x] Tests parametres bornes.
- [x] Test timeout content-free.
- [x] Tests `passage_context` refusant un payload sans `document_id`
  coherent avec la demande.
- [x] Tests anti-fuite `repr(result)` pour passage, titre, auteur, chapitre
  et requete brute.

### Réduction du risque attendue

- [x] Risque bloque par allowlist et method guard; risque rendu observable par endpoint kind/status/duration/counts.

### Critères de sortie

- [x] L'agent futur ne peut recevoir que les outils GET definis par le registre.
- [x] Chaque outil retourne un resultat interne compact sans payload brut retenu
  et une observabilite content-free.
- [x] `passage_context` exige un `document_id` Catalogue present et coherent
  avant de conserver un contexte interne.
- [x] Les champs content-rich des resultats outils sont exclus de `repr(result)`.
- [x] Les routes lourdes sont explicitement bornees ou refusees:
  `GET /doc/{id}` n'est pas utilise par `document_open_summary`.
- [x] `page_read` et `export/chunk` restent hors Lot 3 et requierent un GO separe.

### Hors-scope

- Choix autonome de sequence.
- Edition Catalogue.
- OCR.
- Outil page / `page_read`.
- Navigation complete.
- Export/chunk.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / GET-ONLY PROOF / GO-NO-GO Lot 4`.

## Lot 4 — Planner agentique / boucle bibliothecaire

### Objectif

Permettre a l'agent de choisir plusieurs requetes successives: chercher, ouvrir, comparer, desambiguiser, demander plus de contexte.

### Risque produit traité

Risque que Frida reste bloquee sur une seule regex ou une seule recherche lexicale ratee.

### Plan

- [x] Introduire une boucle bornee: planifier -> appeler outil -> observer -> finaliser.
- [x] Garder la boucle non branchee au produit tant que les smokes produit ne sont pas valides.
- [x] Garantir que le toggle Biblio existant ne force pas l'appel agent: aucun branchement chat/runtime produit dans ce lot.
- [ ] Comparer le chemin agentique au chemin deterministe actuel avant remplacement.
- [x] Budget nominal: nombre max d'etapes, appels outils, contextes, duree totale logique.
- [ ] Requetes alternatives pour accents, paraphrases, auteur/oeuvre/theme.
- [x] Stop propre sur plan invalide, outil refuse, outil echoue ou budget depasse.
- [x] Sortie clarification/fallback quand aucun plan utile n'est fourni.
- [x] Fallback deterministe explicite si aucune boucle n'est executable.

### Patch attendu

- [x] Module planner/boucle dedie: `app/biblio/librarian_planner.py`.
- [x] Aucun adaptateur OpenRouter dans ce lot; gate OpenRouter/JSON reste separe.
- [x] Tests avec faux Catalogue et sorties structurees fake.
- [x] Aucun branchement produit, donc aucune activation par defaut.
- [ ] Feature flag runtime et rollback restent requis avant activation produit.

### Tests / preuves

- [x] Plan simple `catalog_list`.
- [x] Sequence bornee `catalog_search` -> `passage_context`.
- [x] Rejet outil inconnu avant appel outil.
- [x] Rejet `page_read`, `export/chunk`, `latest/page`, `latest/context`.
- [x] Rejet methode non GET et nom de route mutatrice.
- [x] Rejet `passage_context` sans document ou sans position.
- [x] Budget `max_tool_calls` depasse -> `budget_exhausted`.
- [x] Timeout outil -> `tool_failed` content-free.
- [x] Sortie structuree fake invalide -> `tool_rejected`, pas de fail suspend.
- [x] Observabilite et `repr(result)` / `repr(step)` sans requete, passage, titre, auteur ou chapitre brut.
- [x] Test absence import OpenRouter/chat/model/LLM.
- [ ] Smokes comparatifs agent vs deterministe restent hors Lot 4 preparatoire.

### Réduction du risque attendue

- [x] Risque reduit par iteration bornee; risque accepte car la boucle n'est pas encore branchee au produit.

### Critères de sortie

- [x] La boucle execute plusieurs etapes sans fuite.
- [x] La boucle reste non branchee au produit.
- [ ] Le chemin deterministe actuel reste disponible ou son remplacement est prouve par smokes comparatifs.
- [x] Les reason codes distinguent `not_found`, `ambiguous`, `budget_exhausted`, `tool_rejected`, `tool_failed` et `fallback_deterministic`.
- [x] Aucun blocage technique visible comme consigne systeme.

Photo operatoire Lot 4 - 2026-05-31:

- `app/biblio/librarian_planner.py` livre `BiblioLibrarianPlan`,
  `BiblioLibrarianToolCall`, `BiblioLibrarianLoopRequest`,
  `BiblioLibrarianStep`, `BiblioLibrarianLoopResult` et
  `BiblioLibrarianPlanner`;
- la boucle consomme seulement des appels outils structures fake/deterministes,
  pas de modele externe reel;
- la boucle valide les tool calls contre le registre Lot 3 et execute via
  `BiblioLibrarianToolRegistry`;
- budgets livres: `max_steps`, `max_tool_calls`, `max_total_duration_ms`,
  `max_clarifications`, `max_context_chars`;
- correctif post-audit Lot 4: `max_clarifications` est applique uniquement
  quand le plan demande explicitement une clarification; sinon un plan vide
  reste un fallback deterministe;
- correctif post-audit Lot 4: `passage_context.window_chars` est borne ou
  refuse avant l'appel outil si le budget `max_context_chars` restant ne
  permet plus une fenetre Catalogue minimale;
- correctif post-audit Lot 4: `max_steps` est strict; quand aucun slot de
  step ne reste, le resultat peut porter `budget_exhausted` sans ajouter de
  step diagnostique supplementaire;
- micro-refactor post-audit Lot 4: les helpers de budget/contexte vivent dans
  `app/biblio/librarian_planner_budget.py`, les helpers d'observabilite
  content-free vivent dans `app/biblio/librarian_planner_observability.py`,
  et `librarian_planner.py` reste centre sur les dataclasses publiques et la
  boucle `BiblioLibrarianPlanner`;
- statuts livres: `tool_executed`, `needs_clarification`, `not_found`,
  `ambiguous`, `budget_exhausted`, `tool_rejected`, `tool_failed`,
  `fallback_deterministic`;
- `librarian_tools.py` n'a pas ete modifie ni regonfle dans ce lot;
- aucun branchement chat, aucun OpenRouter, aucun modele, aucun outil page,
  aucun `export/chunk`, aucune navigation complete et aucune activation
  runtime produit.

### Hors-scope

- Persistance longue des passages bruts.
- Recherche semantique vectorielle globale.
- Modification Catalogue.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / BUDGETS / GO-NO-GO Lot 5`.

## Lot 5 — Comprehension implicite et dialogue

### Objectif

Preparer la cooperation future entre dialogue recent et etat Biblio explicite
pour comprendre les demandes implicites. Lot 5 bis confirme que le dialogue
recent est seulement borne/observable pour l'instant, pas encore un signal de
decision.

### Risque produit traité

Risque que l'agent interprete "le passage", "dans ce meme ouvrage" ou "c'est tout ?" sans ancre technique fiable.

### Plan

- [x] Preparer une synthese content-free de l'etat Biblio pour le futur agent.
- [x] Recevoir un dialogue recent borne comme entree content-free; Lot 5 ne
  l'utilise pas encore comme signal decisionnel et ne le livre pas a un modele.
- [x] Declarer que l'etat technique prime sur la memoire conversationnelle floue.
- [x] Gerer les references anaphoriques: ce passage, ce livre, meme ouvrage,
  plus haut, apres.
- [x] Demander clarification si l'etat est absent ou contradictoire.

### Patch attendu

- [x] Module dedie: `app/biblio/librarian_dialogue_planner.py`.
- [x] Tests multi-tour/content-free dans
  `app/tests/unit/biblio/test_librarian_dialogue_planner.py`.
- [x] Reason codes pour anaphore resolue, etat absent, candidats absents ou
  outil de navigation manquant.

### Tests / preuves

- [x] Ouvrir Platon -> "donne-moi la table des matieres".
- [x] Passage Theetete -> "continue" clarifie ou signale l'outil de navigation
  manquant, sans inventer de page.
- [x] Ambiguite -> comparaison planifiee seulement si deux candidats
  content-free positionnes existent.
- [x] Etat absent -> clarification propre.

### Réduction du risque attendue

- [x] Risque reduit par priorite donnee aux references techniques; risque rendu
  observable quand l'anaphore ne peut pas etre resolue.

### Critères de sortie

- [x] Les demandes implicites principales passent ou clarifient.
- [x] Aucune reference technique n'est inventee depuis le dialogue.

Photo operatoire Lot 5 - 2026-05-31:

- `BiblioDialoguePlanner` transforme une demande utilisateur interne + un etat
  Biblio content-free en `BiblioLibrarianPlan` ou clarification;
- statut livre: `planned`, `needs_clarification`,
  `unsupported_missing_tool`, `fallback_deterministic`;
- intentions livrees: liste Catalogue, recherche thematique, recherche avec
  ancre document courant mais recherche Catalogue globale explicite, table des
  matieres deictique du document courant, reprise d'un dernier passage positionne,
  comparaison de candidats precedents et navigation refusee proprement;
- correction post-audit Lot 5 bis: `ce passage` / `reprends ce passage`
  reouvrent seulement un contexte borne si `last_result` porte une position;
  sinon clarification;
- correction post-audit Lot 5 ter: `le passage` / `reprends le passage` /
  `resume le passage` / `relis le passage` suivent la meme regle de contexte
  borne que `ce passage`;
- correction post-audit Lot 5 bis: `plus haut`, `avant`, `apres`, `continue`
  signalent l'outil de navigation manquant si l'etat existe, ou clarifient si
  l'etat manque;
- correction post-audit Lot 5 ter: `avant` n'est plus traite comme navigation
  quand il est discursif (`avant tout`, `avant de chercher`) ou thematique
  (`avant Socrate, cherche ...`);
- correction post-audit Lot 5 ter: une table des matieres avec titre explicite
  non resolu, y compris les formes prefixees (`Theetete sommaire`, `du
  Theetete, donne la table...`) et suffixees (`table des matieres Theetete`,
  `sommaire Theetete`, `sommaire complet Theetete`), ne reutilise pas
  silencieusement `current_document`;
  les formes deictiques (`ce livre`, `celui-la`) et les qualificatifs de TOC
  seuls (`complete`, `detaillee`, `complet`, `general`) restent autorises;
- correction post-audit Lot 5 bis: `recent_dialogue` est borne et observable,
  mais pas encore utilise comme signal decisionnel;
- limite assumee Lot 5 ter: la recherche `dans ce livre` reste une recherche
  Catalogue globale avec ancre documentaire observable, pas une recherche
  strictement bornee au contenu du livre;
- aucun appel reseau, aucun OpenRouter, aucun modele reel, aucun branchement
  chat/runtime produit;
- aucun outil page, aucun `export/chunk`, aucun `latest/page`, aucun
  `latest/context`;
- `librarian_planner.py`, `librarian_tools.py` et
  `librarian_planner_observability.py` ne portent pas la comprehension
  dialogue.

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

- [x] Ajouter intents de navigation structures.
- [x] Utiliser `last_result` et `current_document`.
- [x] Lire le contexte autour d'un passage avec bornes quand une ancre
  exploitable existe.
- [ ] Lire page/contexte voisin: bloque tant qu'aucune route page/voisin sure
  n'existe.
- [ ] Paginer catalogue et TOC.
- [x] Ne jamais utiliser `latest/page` ou `latest/context`.
- [x] Clarifier si l'etat ne suffit pas.

### Patch attendu

- [x] Planification `passage_context` bornee pour `autour de ce passage`.
- [ ] Outils page/contexte voisins si route client sure.
- [ ] Mise a jour etat apres navigation.
- [ ] Tests de pagination catalogue/TOC.

### Tests / preuves

- [x] "Continue apres ce passage." -> outil de navigation manquant.
- [x] "Montre-moi la page precedente." -> outil de navigation manquant.
- [x] "Remonte un peu." -> outil de navigation manquant.
- [x] "Autour de ce passage." -> `passage_context` borne si ancre presente.
- [x] "Cherche un autre passage proche." -> outil de navigation manquant.
- [ ] "Il y a 100 ouvrages ? Liste-les tous."

### Réduction du risque attendue

- [ ] Risque reduit par navigation explicite et bornee; risque bloque par garde `document_id` obligatoire.

### Critères de sortie

- [x] Navigation autour d'un passage fonctionne sur etat valide.
- [x] Navigation non supportee signale l'outil manquant sur etat valide.
- [x] Navigation clarifie sur etat absent.
- [x] Observabilite expose positions/hashes/counts seulement.

Photo operatoire Lot 6 - 2026-05-31:

- `librarian_dialogue_navigation.py` classe les demandes de navigation en
  `continue`, `page_previous`, `page_next`, `up`, `down`, `around_passage`,
  `nearby_passage` ou `generic`;
- seul `around_passage` est planifie en outil Catalogue existant:
  `passage_context` GET-only avec `document_id` explicite, position issue de
  `last_result` et `window_chars` borne;
- `continue`, page precedente/suivante, plus haut/bas et passage proche ne sont
  pas simules: ils retournent `unsupported_missing_tool` si l'etat existe ou
  `needs_clarification` si l'etat manque;
- correction post-audit Lot 6: une navigation avec ouvrage explicite non
  resolu (`dans le Theetete`, `dans Platon`, `chez Platon`,
  `dans l'Apologie`, `de l Apologie`, `d'Apologie`) clarifie et ne reutilise
  jamais silencieusement le document courant;
- correction post-audit Lot 6: `passage proche` reste navigation seulement
  pour les reprises anaphoriques (`un autre passage proche`, `passage voisin`);
  avec un verbe de recherche et un theme/ouvrage explicite, la demande reste
  une recherche thematique;
- correction d'ouverture P3: les politesses apres qualificatifs de TOC (`stp`,
  `merci`, `maintenant`, `s il te plait`) ne sont pas des titres; les formes
  `qualificatif + titre` clarifient toujours;
- aucun outil page dans le Lot 6 historique, aucun `latest/page`, aucun
  `latest/context`, aucun `export/chunk`, aucun OpenRouter et aucun
  branchement runtime produit.

### Mise a jour Lot R1 - 2026-06-02

- `page_read` est maintenant livre comme primitive GET-only bornee sur
  `GET /doc/{id}/page/{page_no}`;
- le runtime Biblio sait maintenant resoudre un document/volume explicitement
  nomme dans une demande de navigation page, puis composer cette resolution
  sur `page_read`;
- le planner dialogue Biblio planifie `page_read` pour:
  - `page suivante / page precedente`;
  - `page 28 a page 32` avec garde `<= 5` pages;
  - `continue apres ce passage` quand l'etat porte deja `document_id` et
    `page_no`;
- `autour de ce passage` reste sur `passage_context`, ce qui preserve la
  distinction entre lecture de page et contexte autour d'une ancre;
- une oeuvre interne non mappee proprement a des pages documentaires
  (exemple: `Theetete` comme oeuvre dans `Platon`) ne doit pas etre
  requalifiee en navigation page supportee sans preuve de mapping reel;
- `deux pages apres 147c` reste hors contrat: aucun lien general locator ->
  page/offset n'est encore promis;
- `latest/page` et `latest/context` restent interdits.

### Hors-scope

- Chargement illimite d'ouvrage.
- Export complet automatique.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / NAVIGATION MATRIX / GO-NO-GO Lot 7`.

## Lot 7 — Socle agentique OpenRouter / JSON, off-shadow

### Objectif

Livrer la premiere fondation reelle du bibliothecaire agentique sans activation
produit sauvage: entree bornee, appel OpenRouter optionnel par mode, JSON strict,
validation du plan, rejet des outils interdits, fallback deterministe et
observabilite content-free.

### Risque produit traité

Risque de continuer a empiler des regex locales au lieu de donner a Frida un
bibliothecaire capable de planifier une consultation multi-tour. Risque inverse:
appeler un modele non borne qui remplacerait le chemin deterministe ou fuirait
du contenu brut.

### Plan

- [x] Verifier la documentation OpenRouter actuelle pour `response_format`
  JSON Schema strict, tool calling et support modele.
- [x] Creer un artefact date:
  `app/docs/states/baselines/frida-biblio-librarian-agent-openrouter-json-2026-06-01.md`.
- [x] Ajouter un contrat agent versionne:
  `app/biblio/librarian_agent_contract.py`.
- [x] Ajouter un adaptateur OpenRouter:
  `app/biblio/librarian_agent_openrouter.py`.
- [x] Ajouter l'orchestrateur non actif:
  `app/biblio/librarian_agent.py`.
- [x] Ajouter les modes `off`, `shadow`, `candidate`, `active`.
- [x] Garder `off` par defaut et ne pas utiliser `active` comme chemin
  produit dans ce lot.
- [x] Valider strictement le JSON avant tout plan executable.
- [x] Rejeter JSON absent, invalide, tronque, texte libre, schema inconnu,
  outil interdit, outil inconnu, methode non GET et budget depasse.
- [x] Rejeter localement les payloads hors schema: champs racine en trop,
  champs requis absents, `risk_flags` invalides, params inconnus et bornes de
  params depassees.
- [x] Rejeter `params` non objet (`null`, liste, string, nombre, booleen) sans
  le normaliser en `{}`; `{}` reste valide seulement pour les outils qui
  l'acceptent reellement.
- [x] Aligner la validation locale sur les contraintes executables de
  `librarian_tools.py`: query obligatoire pour `catalog_search`, document_id
  obligatoire pour TOC/locate/context, position obligatoire pour
  `passage_context`, limites par outil et offset de recherche borne.
- [x] Refuser `active` avant appel modele dans le Lot 7.
- [x] Implementer le fallback modele configure seulement si
  `max_model_calls >= 2`.
- [x] Ne conserver aucun prompt complet ni raw JSON modele dans le resultat
  agent observe.
- [x] Garder le chemin deterministe comme controleur en `shadow` et
  `candidate`.

### Patch attendu

- [x] Section runtime settings non secrete `biblio_librarian_agent`:
  `BIBLIO_LIBRARIAN_AGENT_MODE`, `BIBLIO_LIBRARIAN_AGENT_MODEL`,
  `BIBLIO_LIBRARIAN_AGENT_FALLBACK_MODEL`, timeout, sampling, max tokens,
  max tool/model calls, max recent turns et reasoning restent des seeds/env
  bootstrap, pas la source runtime principale quand la DB est disponible.
- [x] Contrat JSON obligatoire: pas de knob operateur permettant de le
  desactiver dans ce lot; `provider.require_parameters=true` est invariant.
- [x] Referer/title OpenRouter dedies:
  `OPENROUTER_REFERER_BIBLIO_LIBRARIAN`,
  `OPENROUTER_TITLE_BIBLIO_LIBRARIAN`.
- [x] Aucune cle API dediee nouvelle: reutilisation du secret runtime
  `main_model.api_key` via `llm_client`; `OPENROUTER_API_KEY` ne sert plus
  d'autorite directe pour l'appel Biblio.
- [x] Aucun branchement chat/runtime produit.
- [x] Aucun appel Catalogue nouveau.

### Tests / preuves

- [x] mode `off`: aucun appel modele.
- [x] mode `shadow`: appel possible, plan valide non utilise pour la reponse.
- [x] mode `candidate`: plan candidat conserve mais deterministe controle.
- [x] mode `active` Lot 7 historique: non active, fallback deterministe.
- [x] mode `active` Lot 7 historique: aucun appel modele, aucun cout/latence
  provider. Supersede post-Lot 10: le smoke nominal `active` appelle le modele
  mais reste non souverain (`used_for_response=false`, outils non executes).
- [x] JSON valide: plan `BiblioLibrarianPlan` produit.
- [x] JSON invalide, texte libre, tronque: fallback deterministe.
- [x] JSON hors schema local: rejet, meme si le provider devait deja faire du
  strict schema.
- [x] outil interdit / inconnu / methode mutable: rejet avant execution.
- [x] budget modele et budget tool calls: rejet propre.
- [x] timeout / erreur provider primaire: tentative du fallback modele si
  configure et budget `max_model_calls >= 2`, sinon fallback deterministe.
- [x] modele absent ou cle provider absente: aucun appel provider et
  `model_called=false`.
- [x] timeout provider simule: tentative provider observee,
  `attempt_count=1` et `model_called=true`.
- [x] plans JSON valides mais non executables par les outils GET-only rejetes
  avant toute execution.
- [x] dialogue recent borne a `max_recent_turns`.
- [x] fixtures produit anaphoriques transmises au modele avec message courant,
  dialogue recent borne, etat Biblio et outils disponibles; cela ne prouve pas
  encore la comprehension reelle du modele.
- [x] `to_observability()` et `repr(result)` restent content-free.

### Réduction du risque attendue

- [x] Risque reduit par un contrat agentique testable avant activation:
  l'agent peut proposer un plan, mais il ne devient pas souverain.

### Critères de sortie

- [x] `BIBLIO_LIBRARIAN_AGENT_MODE=off` ne construit aucun appel modele.
- [x] `shadow` et `candidate` ne remplacent pas le chemin deterministe.
- [x] OpenRouter / JSON documente avec URLs et limites.
- [x] Aucun modele n'est hardcode comme choix actif; DeepSeek V4 Pro est
  documente comme slug observe, pas comme default runtime.
- [x] Aucun outil hors allowlist ne passe la validation.
- [x] Aucune fuite brute dans l'observabilite ou `repr`.

### Hors-scope

- Activation produit de l'agent.
- Remplacement du chemin deterministe.
- Execution de la boucle d'outils depuis le plan agent en chat runtime.
- Runtime settings admin/DB.
- Nouveau Catalogue, outil page, navigation complete ou route plateforme.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / AGENT CONTRACT / GO-NO-GO Lot 8`.

## Lot 8 — Integration comparative agentique non souveraine

### Objectif

Brancher le socle agentique dans le runtime Biblio comme comparateur
observable, sans donner le controle produit a l'agent.

### Risque produit traité

Risque de passer d'un socle agentique teste en isolation a une activation
produit trop rapide. Risque inverse: garder l'agent hors runtime et ne jamais
observer sa comparaison avec le deterministe.

### Plan

- [x] Construire une `BiblioLibrarianAgentRequest` bornee depuis le message
  courant, le dialogue recent, l'etat Biblio content-free, la baseline
  deterministe et les settings runtime.
- [x] Appeler l'agent uniquement si Biblio est activee et si le mode agent
  n'est pas `off`.
- [x] Garder le deterministe comme controleur unique de la reponse produit.
- [x] En `shadow` et `candidate`, observer le plan agent sans modifier la
  reponse ni le prompt produit.
- [x] En `active`, refuser encore l'activation produit et ne pas appeler le
  provider.
- [x] Ajouter une comparaison content-free dans l'evenement Biblio:
  mode, model_called, candidate_plan_present, used_for_response=false,
  deterministic_controller=true, product_response_changed=false.
- [x] Proteger le fallback deterministe si le comparateur agent echoue.

### Patch attendu

- [x] Nouveau module dedie `app/biblio/librarian_agent_runtime.py`.
- [x] Wiring minimal dans `app/biblio/chat_runtime.py` apres baseline
  deterministe.
- [x] Passage du dialogue recent borne depuis `app/core/chat_service.py`.
- [x] Extension passive de `app/biblio/observability.py` pour la projection
  agent.

### Tests / preuves

- [x] Mode agent `off`: aucun appel modele.
- [x] Biblio toggle off: aucun appel agent.
- [x] `shadow`: modele fake appele, reponse deterministe inchangee.
- [x] `candidate`: plan candidat observable, reponse deterministe inchangee.
- [x] `active`: non active produit, aucun remplacement souverain.
- [x] JSON invalide, outil interdit, timeout provider et exception runtime
  agent: fallback deterministe.
- [x] Observabilite agent sans message brut, dialogue brut, prompt, raw JSON,
  passage, titre, auteur, locator ou payload Catalogue.
- [x] Correction post-audit Lot 8: l'observation de requete est exposee sous
  `request_observation`, pas sous la cle globale redigee `request`, afin de
  conserver les longueurs/hashes content-free du message courant et du dialogue
  recent dans l'evenement final.

### Réduction du risque attendue

- [x] Risque reduit par comparaison runtime observable avant activation:
  l'agent peut etre evalue en conditions Biblio sans controler la reponse.

### Critères de sortie

- [x] L'agent ne peut pas influencer la reponse produit.
- [x] L'agent n'est pas appele en mode `off`.
- [x] Biblio off ne declenche pas d'agent.
- [x] Le fallback deterministe reste intact.
- [x] Les projections restent content-free.

### Hors-scope

- Injection lane/reponse Frida pilotee par le plan agent.
- Execution des outils proposes par le modele pour produire la reponse finale.
- Activation produit `active`.
- Changement du contrat principal de sortie assistant.
- Streaming UI.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / COMPARISON PROOF / GO-NO-GO Lot 9`.

## Lot 9 — Observabilite content-free

### Objectif

Rendre le chemin bibliothecaire lisible par l'operateur sans exposer le contenu des ouvrages.

### Risque produit traité

Risque de debug impossible ou de fuite de contenu/prompt/payload.

### Plan

- [x] Ne pas inventer d'events agentiques absents: aucun `tool_call`,
  `selection`, `state_update` ou `final` agentique n'est declare execute dans
  le runtime comparatif.
- [x] Exposer le statut reel du comparateur: mode, skipped/off,
  `request_observation`, appel modele, validation JSON, plan candidat,
  fallback, reason codes, budgets, modele effectif expurge et resultat de
  comparaison.
- [x] Exposer explicitement `tool_execution_status=not_executed` et les
  compteurs d'evenements agentiques executes a `0`.
- [x] Exposer les metriques compactes disponibles: durees, counts, hashes,
  longueurs, tool names allowlistes, status/reason codes et model source
  expurgee.
- [x] Interdire passages, pages, titres bruts, auteurs bruts, requetes
  utilisateur brutes, payloads, prompts complets, raw JSON modele et params
  d'outils bruts.
- [x] Etendre read-model/dashboard uniquement avec projections compactes
  persistees dans `biblio_json`.

### Patch attendu

- [x] Projection `librarian_agent` enrichie dans l'evenement Biblio.
- [x] Sanitizer Biblio ajuste pour conserver les tokens/hashes agentiques
  lisibles sans brut.
- [x] Read-model dashboard: resume compact `biblio.librarian_agent`.
- [x] Aggregats dashboard Biblio pour mode, statut, appels modele, controle
  deterministe normal, validation JSON et absence d'execution d'outils
  agentiques.
- [x] Metriques agent declarees dans le module observable Biblio, sans compteur
  `fallback` ambigu.
- [x] Read-model agent defensif: les chaines `"false"` / `"0"` ne deviennent
  pas des booleens vrais.
- [x] Tests anti-fuite Biblio + dashboard/read-model.

### Tests / preuves

- [x] Unitaires anti-fuite.
- [x] Smoke strict existant conserve vert.
- [x] Dashboard/read-model sans contenu brut.
- [x] Modele effectif observable sans secret.

### Réduction du risque attendue

- [x] Risque reduit par projections compactes; risque bloque par tests
  anti-fuite et par compteurs explicites `not_executed`.

### Critères de sortie

- [x] Chaque tour comparatif agentique est audit-able content-free.
- [x] Aucune surface technique ordinaire ne montre contenu d'ouvrage.
- [x] L'agent reste non souverain: `used_for_response=false`,
  `product_response_changed=false`, `deterministic_controller=true`.

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

- [x] Creer un runner agent dedie: `python -m biblio.smoke_librarian_agent_live --jsonl`.
- [x] Couvrir catalogue complet, 100 ouvrages, Platon, Theetete, maieutique, sage-femme, 126b-128a, navigation, verification et ambiguite.
- [x] Sorties strictement content-free.
- [x] Exit code non zero si fuite, payload retenu, endpoint lourd interdit, effet agent produit, agent attendu non appele, statut produit `failed` ou `partial_required_attention`.

### Patch attendu

- [x] Runner smoke agent, agent mode nominal `active`; `off` reste explicite pour test negatif.
- [x] `shadow` et `candidate` restent des modes compat/dev et ne comptent pas
  comme preuve produit nominale.
- [x] `active` appelle le modele et valide le JSON; il ne modifie pas encore la
  reponse produit (`used_for_response=false`, outils non executes).
- [x] `--no-product-strict` ne masque plus un echec agent; seul
  `--no-agent-strict` permet une inspection debug non bloquante.
- [x] Mini-lot configuration active post-Lot 10: defaults applicatifs non
  secrets `active`, `openai/gpt-5.2`, temperature `0`, `top_p=1`,
  `max_tokens=16000`, `max_recent_turns=5`, timeout `240s` et
  `reasoning_effort=high`.
- [x] Correctif post-audit: payload OpenRouter Biblio aligne sur
  `reasoning={"effort":"high","exclude":true}` et smoke segmentable par
  `--case-id` / `--max-cases`; le full smoke reste le gate global.
- [x] Compat GPT-5.2 prouvee sans refonte prompt: le caller omet
  `temperature` / `top_p` pour `openai/gpt-5*`, evite `oneOf` dans
  `tool_calls.items`, et normalise localement les `null` / vides d'un schema
  `params` strict OpenRouter-compatible.
- [x] Fixtures attendues content-free avec statuts separes: `runtime_expectation_status`, `agent_expectation_status`, `product_expectation_status`.
- [x] Un plan dialogue local seul ne peut pas rendre un cas `met`.
- [x] Documentation des cas et resultats.

### Tests / preuves

- [ ] `docker exec -w /app platform-fridadev python -m biblio.smoke_librarian_agent_live --jsonl`
  complet, strict, termine.
- [x] Smoke segmente content-free utilisable pour debug:
  `python -m biblio.smoke_librarian_agent_live --jsonl --case-id P01`.
- [x] Verification `raw_marker_leaks=false`.
- [x] Verification `payload_objects_retained=0`.
- [x] Verification des endpoint kinds, lanes et state updates attendus.

### Réduction du risque attendue

- [x] Risque reduit par validation produit live; risque rendu observable par matrice de cas.

### Critères de sortie

- [x] Tous les cas obligatoires passent ou produisent une clarification explicitement acceptee.
- [x] Aucune fuite brute.

### Hors-scope

- Benchmark exhaustif du fonds.
- Mesure qualite philosophique humaine complete.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / SMOKE MATRIX / GO-NO-GO Lot 11`.

## Lot 11 — Test utilisateur live et stabilisation produit

### Objectif

Permettre a Tof de tester Frida en usage reel avec l'agent-first Biblio deja
actif comme controleur bibliothecaire. Collecter les echecs produit, reponses
pauvres, lenteurs, mauvaises citations, ambiguities mal gerees,
incomprehensions et cas ou Frida manipule mal le fonds, puis stabiliser sans
rouvrir l'activation agent-first.

### Risque produit traité

Risque de confondre une matrice de smokes verte avec une bibliotheque vraiment
utilisable en conversation. Le prochain signal produit vient des tests live
utilisateur, pas d'un nouveau GO technique d'activation.

### Plan

- [ ] Organiser une session de test live utilisateur avec Biblio activee.
- [ ] Capturer les cas reels qui echouent ou degradent l'experience:
  - [ ] faux "je n'ai pas acces";
  - [ ] catalogue incomplet ou presente comme exhaustif a tort;
  - [ ] TOC/chapitres mal consultes;
  - [ ] mauvaise oeuvre interne ou mauvais volume;
  - [ ] citation ou passage mal borne;
  - [ ] ambiguite non annoncee ou certitude forcee;
  - [ ] reponse trop pauvre alors que la lane contient assez d'elements;
  - [ ] lenteur, timeout, cout ou instabilite OpenRouter;
  - [ ] JSON modele invalide, plan inexecutable ou fallback trop frequent.
- [ ] Pour chaque cas, conserver une preuve content-free: `case_id` local,
  status/reason, endpoints, outils executes, lane presente ou non, longueurs,
  hashes courts, latence si disponible, jamais le texte d'ouvrage.
- [ ] Classer les retours P0/P1/P2/P3 selon impact produit.
- [ ] Corriger seulement les ecarts confirmes et bornes; ne pas ajouter page,
  `export/chunk`, route Catalogue ou refactor large sans lot separe.
- [ ] Verifier apres chaque correction que le smoke strict P01-P18 reste vert.

### Patch attendu

- [ ] Notes de test live content-free sous `app/docs/states/baselines/` ou
  `app/docs/states/audits/` selon la forme retenue.
- [ ] Micro-correctifs produit si les tests live revelent un ecart local.
- [ ] Tests unitaires/regression pour chaque correctif.
- [ ] Eventuels ajustements de prompt/lane seulement si le probleme est prouve
  par usage live et garde les murs content-free hors lane produit.
- [x] Stabilisation immediate post-retour live: timeout bibliothecaire porte a
  `240s`, prompt renforce pour chercher le texte primaire avant commentaire ou
  notice, et diagnostic Stephanus content-free date sous
  `app/docs/states/baselines/biblio-smokes/`.
- [x] Correctif borne Stephanus / logique produit: les requetes canoniques
  explicites `extract_passage` / `extract_range` avec locator present restent
  sous controle deterministe; l'agent-first reste compare/observable mais ne
  degrade plus ces cas en `catalog_search -> passage_context` approximatif.
- [x] Correctif borne verite produit / resolution documentaire: la lane Biblio
  distingue maintenant `exact_passage`, `plausible_candidate` et
  `contextual_approximation`; `resolve_work` n'essaie plus d'extraire un
  passage sans locator et conserve `work_title` distinct de `document_title`
  pour des cas du type `Theetete de Platon`.

### Tests / preuves

- [ ] `python -m biblio.smoke_librarian_agent_live --jsonl` en conteneur live.
- [ ] Repros live utilisateur ciblees, content-free.
- [x] Diagnostic content-free Stephanus: labels simples localisables selon le
  document; plage brute non directement localisable, sans patch plateforme ni
  affichage OCR.
- [x] Audit date sous `app/docs/states/audits/frida-biblio-stephanus-library-audit-2026-06-02.md`
  et baseline associee `stephanus-range-diagnostic-20260602T062819Z.md`.
- [ ] Unitaires Biblio impactes par chaque stabilisation.
- [ ] Verification anti-fuite: pas de passage brut, prompt, payload, titre,
  auteur, locator, requete brute ou secret dans les preuves techniques.
- [ ] Verification que les fallbacks reparateurs restent distingues par
  `fallback_repaired` et ne deviennent pas un succes pur du plan modele.

### Réduction du risque attendue

- [ ] Risque reduit par confrontation aux usages reels au lieu d'une validation
  seulement smoke-driven.
- [ ] Risques conserves et suivis: taille des modules, dependance OpenRouter
  live, latence/cout, qualite JSON, absence de navigation canonique
  locator -> page/offset et absence `export/chunk`.

### Critères de sortie

- [ ] Les retours live utilisateur sont inventories et classes.
- [ ] Les P0/P1/P2 confirmes sont corriges ou explicitement bloques avec
  justification produit.
- [ ] Le smoke strict reste vert apres stabilisation.
- [ ] Aucune regression GET-only, content-free, rollback/off ou separation
  Biblio / Memory-RAG / Web / documents actifs.

### Hors-scope

- Nouvelle activation produit: l'agent-first est deja actif comme controleur
  Biblio.
- Refonte agentique large.
- Outil page, `export/chunk`, nouvelle route Catalogue ou patch plateforme.
- Benchmark exhaustif du fonds.
- Optimisation fine cout/latence hors regression bloquante.

### Format de retour attendu

`PLAN / PATCH / TEST LIVE / STABILISATIONS / RISKS / GO-NO-GO Lot 12`.

## Lot 12 — Consolidation et clôture agent bibliothécaire

### Objectif

Integrer les retours du Lot 11, corriger les derniers ecarts acceptes dans le
scope, documenter l'etat final, les limites et les dettes acceptees, puis
archiver la roadmap seulement si le test utilisateur live confirme que Frida se
comporte comme une bibliotheque utilisable.

### Risque produit traité

Risque de cloturer administrativement le chantier alors que l'usage reel reste
fragile. Le GO final ne peut pas preceder les tests live utilisateur et leur
triage.

### Plan

- [ ] Relire les retours Lot 11 et fermer chaque P0/P1/P2 confirme.
- [ ] Rejouer les smokes stricts agent-first.
- [ ] Rejouer les cas live utilisateur qui avaient echoue.
- [ ] Verifier GET-only et anti-fuite.
- [ ] Verifier rollback feature flag.
- [ ] Verifier mode `off` et absence d'appel modele quand Biblio/agent sont
  desactives.
- [ ] Documenter les limites restantes:
  - [ ] modules gros et dette de separation;
  - [ ] dependance OpenRouter live;
  - [ ] latence/cout;
  - [ ] qualite JSON modele;
  - [ ] absence page;
  - [ ] absence `export/chunk`;
  - [ ] fonds Catalogue et metadata non corriges par FridaDev.
- [ ] Confirmer la doctrine finale: le bibliothecaire LLM fait le travail
  bibliothecaire; le deterministe tient les murs GET-only, budgets, validation
  JSON, fallback et observabilite content-free.
- [ ] Mettre a jour README, `app/docs/README.md`, `AGENTS.md` si la TODO est archivee.

### Patch attendu

- [ ] Note de validation finale sous `app/docs/todo-done/validations/`.
- [ ] TODO deplacee sous `app/docs/todo-done/product/` seulement si tous les criteres sont atteints.
- [ ] Docs d'index mises a jour.
- [ ] Dettes acceptees documentees explicitement, sans les masquer comme GO
  parfait.

### Tests / preuves

- [ ] Unitaires agent.
- [ ] Contrats chat/admin/dashboard/read-model.
- [ ] Smokes live agent.
- [ ] Repros Lot 11 fermees ou requalifiees.
- [ ] Test rollback runtime.
- [ ] Test toggle Biblio avec agent off.
- [ ] `git diff --check`.
- [ ] Status final propre.

### Réduction du risque attendue

- [ ] Risque reduit par validation live et archivage conditionnel; risque restant documente s'il ne bloque pas le GO.

### Critères de sortie

- [ ] GO final seulement si les tests live utilisateur confirment que les cas
  bibliotheque passent, extraient, listent, consultent ou clarifient proprement.
- [ ] NO-GO si etat multi-tour, GET-only, anti-fuite ou fallback echoue.
- [ ] NO-GO si agent off/rollback n'est pas prouve.
- [ ] NO-GO si catalogue, TOC, passage exact, recherche thematique ou reprise
  conversationnelle regressent.
- [ ] Aucun rebuild plateforme implicite.

### Hors-scope

- Nouveaux chantiers Catalogue.
- OCR ou correction du fonds.

### Format de retour attendu

`PLAN / PATCH / TEST / RISKS / FINAL GO-NO-GO / COMMIT-PUSH`.

## Risques documentes mais non corriges par cette TODO

- Branchement chat produit agent-first livre pour la matrice P01-P18.
- Le smoke nominal `active` peut echouer honnetement si le modele ou la cle
  provider ne sont pas configures; ce n'est plus remplace par `candidate`.
- Activation agent-first livree sous murs GET-only, avec fallback borne si le
  JSON actif est invalide, vide ou inexecutable.
- Section runtime settings admin/DB dediee livree; smoke complet actif P01-P18
  valide comme gate global le 2026-06-01.
- L'outil page borne existe cote FridaDev, mais P09 reste une surveillance
  tant que la navigation canonique locator -> page/offset n'est pas livree.
- P03 etait un cas de regression historique; il est maintenant prouve comme
  `work_lookup` agent-first nominal et ne doit plus etre gere comme exception
  produit.
- La navigation precedente/suivante borne existe cote FridaDev; la navigation
  canonique ou intra-page reste partielle.
- Risques stale retires: verification OpenRouter/JSON datee, contrat agent,
  config env, fallback modele configure, fallback deterministe, validation
  d'outils interdits et validation locale des plans non executables.

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

Lot 3 registre d'outils Catalogue GET-only livre; correction post-Lot 3
appliquee sur coherence `passage_context` et anti-fuite `repr(result)`.

Lot 4 boucle/planner bibliothecaire borne livre comme module non branche
produit, sans modele externe reel.

Lot 5 comprehension implicite/dialogue livre.

Lot 6 navigation bornee livre.

Lot 7 socle OpenRouter/JSON livre, avec validation stricte et
`provider.require_parameters=true` invariant. Le correctif post-Lot 10 branche
la source runtime settings DB `biblio_librarian_agent`, la cle partagee
`main_model.api_key` et le payload `reasoning` officiel.

Lot 8 integration comparative runtime livre: l'agent peut etre appele en
`shadow`/`candidate` quand Biblio est activee, mais le deterministe reste le
controleur et `used_for_response=false`.

Tranche verticale post-Lot 10 generalisee livree: l'exception P03-only est
remplacee par une architecture agent-first Biblio. Quand Biblio est activee,
l'agent `active` est appele comme controleur bibliothecaire principal. Un plan
JSON valide peut executer les outils GET-only allowlistes (`catalog_list`,
`catalog_search`, `document_open_summary`, `document_toc`, `locate`,
`passage_context`) par `librarian_tools.py` sous budgets stricts. Si le modele
rend un JSON invalide, un plan vide ou un outil inexecutable, un fallback borne
peut synthetiser un plan depuis les signaux deterministes/dialogue deja
content-free, toujours sous `execution_scope=agent_first` et murs GET-only.
Une lane de consultation bornee contient les donnees produit utiles, tandis que
l'observabilite dit explicitement `execution_scope=agent_first`,
`tool_execution_status=executed`, `used_for_response=true` et
`product_response_changed=true`. Route lourde, route `latest/*`, route mutante,
nouvel outil, frontend, plateforme ou payload brut restent interdits.

Correction verite operateur post-tranche agent-first: l'artefact
`app/docs/states/baselines/biblio-smokes/agent-first-full-20260601T181903Z.jsonl`
reste une preuve produit P01-P18, mais il etait trop genereux cote agent:
les cas repares par fallback borne ne doivent plus etre comptes comme succes
pur du plan modele. Le smoke expose maintenant les outils reellement executes
via `agent_executed_tool_names`; `agent_expectation_status=met` signifie plan
modele valide/executable, tandis que `fallback_repaired` signifie reponse
produit verte par fallback agent-first borne et observable.
Preuve post-correctif:
`app/docs/states/baselines/biblio-smokes/agent-first-full-post-truth-fix-20260601T185215Z.jsonl`,
18/18 records avec `runtime_expectation_status=met`,
`product_expectation_status=met`, `raw_marker_leaks=false`,
`payload_objects_retained=0`, et statuts agent separes `met` /
`fallback_repaired`.

Dette structurelle post-agent-first: `librarian_agent_first.py`,
`chat_runtime.py`, `librarian_agent_contract.py` et `librarian_tools.py`
depassent ou frolent la zone 500-700 lignes. Aucun refactor dans cette
micro-correction; un futur nettoyage doit separer par responsabilite reelle
avant d'empiler de nouvelles capacites agentiques.

NO-GO pour executer un outil non allowliste, ajouter un outil page non borne,
`export/chunk`, navigation complete, modele hardcode, route plateforme, ou
marquer un smoke produit vert sur simple plan agent observe sans donnees reelles
injectees dans la lane.

Risques restants reels: le smoke nominal `active` depend de la disponibilite
OpenRouter live et de la qualite JSON du modele, la navigation canonique
locator -> page/offset reste absente, `export/chunk` reste absent, et les
fallbacks bornes doivent rester limites aux signaux deja valides par les murs
deterministes/dialogue.
