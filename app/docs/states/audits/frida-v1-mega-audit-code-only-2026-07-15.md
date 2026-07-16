# Audit code FridaDev - seconde passe autocritique - 2026-07-15

Origine: seconde passe demandee par l'utilisateur apres l'audit cartographique initial, exclusivement centree sur le code.
Rapport de travail local: `/Users/tof/codex-fridadev/audits/fridadev-initial-code-audit-2026-07-15.md`.
Rapport durable du depot: `app/docs/states/audits/frida-v1-mega-audit-code-only-2026-07-15.md`.
Mode: lecture seule sur l'OVH et FridaDev. Aucun patch distant, test mutable, commit, pull, rebuild, redemarrage ou ecriture DB.

Cette version remplace le rapport precedent. Les constats Docker, Caddy, Authelia,
conteneurs, endpoints publics et runtime live du premier passage ne sont pas
revalides ici et ne servent pas de preuve a cette seconde passe. Les specs et
les tests sont lus uniquement comme contrats a confronter au code.

Version auditee:

- depot: `/opt/platform/fridadev`;
- branche: `FridaV1-Mega-Audit-Code-Stack`;
- HEAD: `afdf19fa54c6a1602232e54e40bb23a6ba33787d`;
- ecart upstream observe: `0 0`;
- worktree distant propre aux controles initial et final;
- `git diff --check` vide.

## DIAGNOSTIC COURT

Aucun P0 ou P1 n'est confirme par le code seul. Cinq findings P2 et trois P3
restent vivants.

La seconde passe invalide surtout l'impression de surete trop large du premier
rapport sur trois surfaces. Le code accepte une URL HTML explicite sans le garde
SSRF applique aux PDF; les uploads ne disposent pas d'une limite applicative
coherente, notamment aucune pour la transcription; et une ecriture d'identite
journalise directement les 60 premiers caracteres du contenu.

Deux defauts de coherence du chemin chat sont aussi confirmes. Le chat principal
ignore toujours `main_model.base_url` runtime. En outre, les chemins non-stream
et final-lock effectuent des travaux auxiliaires non proteges apres avoir
persiste la reponse assistant: une panne tardive peut donc retourner une erreur
alors que la reponse est deja durablement enregistree. Le streaming contient au
contraire des wrappers fail-open dedies.

Le premier rapport sous-estimait enfin la dette de complexite. Le probleme ne se
resume pas au nombre de lignes de `server.py`: plusieurs fonctions uniques font
200 a 957 lignes et concentrent de 50 a 129 noeuds de branchement statiques. Le
code est fortement teste, mais cette densite rend possibles des tests verts qui
figent une incoherence, comme les tests du chat principal qui mockent
`config_module.OR_BASE` au lieu d'exiger l'URL runtime partagee.

## FINDINGS

### P2-CEL-WEB-HTML-SSRF-GUARD-01 - les URL HTML explicites contournent le garde SSRF du lecteur PDF

Faits verifies:

- `app/tools/web_search.py:163-173` extrait toute URL utilisateur `http` ou
  `https` dotee d'un `netloc`.
- `app/tools/web_search.py:197-211` copie cette URL telle quelle dans le payload
  Crawl4AI.
- `app/tools/web_search.py:214-242` envoie ce payload au service `/md` sans
  validation de l'hote, resolution DNS ou rejet des IP non globales.
- `app/tools/web_search.py:2108-2123` dirige les PDF vers le lecteur borne, mais
  toutes les autres URL vers `_crawl_explicit_url_primary_with_status()`.
- a l'inverse, `app/tools/web_pdf_reader.py:445-471` revalide chaque URL avant
  chaque requete et chaque redirection;
  `app/tools/web_pdf_reader.py:491-544` bloque localhost, suffixes internes,
  adresses privees, loopback, link-local, multicast, reservees et non globales.
- les tests `app/tests/unit/web_search/test_web_pdf_reader.py` couvrent le
  blocage interne PDF; aucun test equivalent n'existe pour la voie HTML/Crawl4AI.

Impact:

- une URL explicite controlee par l'utilisateur peut demander au crawler de
  joindre une cible interne;
- la voie de resultats de recherche reutilise aussi le meme primitive de crawl;
- la portee exploitable depend des defenses et du reseau propres a Crawl4AI,
  non audites dans ce passage code-only. C'est la raison du classement P2 et non
  P1.

Condition de sortie d'un futur lot: une politique URL publique partagee par PDF
et HTML, appliquee avant l'appel au crawler et a chaque redirection sous controle
de FridaDev, avec tests IPv4, IPv6, DNS, redirection et noms internes.

### P2-CEL-UPLOAD-LIMITS-01 - les limites d'upload sont absentes ou contournables au niveau applicatif

Faits verifies:

- aucune configuration Flask `MAX_CONTENT_LENGTH` n'existe dans `app/server.py`.
- les routes workspace et documents actifs ne regardent que
  `request.content_length` avant d'acceder a `request.files`:
  `app/server.py:1426-1439` et `:1818-1831`.
- `app/core/active_document_upload_service.py:27-46` considere une taille
  absente ou invalide comme `0`, donc acceptable.
- `app/core/active_document_upload_service.py:87-118` lit ensuite tout le
  fichier en memoire, sans second controle `len(content)` contre la limite de
  40 Mio avant extraction/OCR/activation.
- `app/core/workspace_files_service.py:103-140` lit aussi tout en memoire, mais
  possede au moins un second controle post-lecture.
- `/api/chat/transcribe` n'a aucun garde de taille dans `app/server.py:762-775`.
- `app/core/whisper_transcription_service.py:163-199` lit integralement le blob
  audio sans plafond, puis `:220-234` le duplique dans une requete multipart
  amont.
- le test documents actifs `app/tests/test_server_active_documents_contract.py:320-349`
  couvre seulement un `CONTENT_LENGTH` explicitement trop grand. Aucun test ne
  couvre l'absence ou le mensonge de cet en-tete; aucun test de plafond audio
  n'a ete trouve.

Impact:

- consommation memoire non bornee avant rejet pour le workspace;
- consommation et traitement non bornes pour les documents actifs;
- consommation puis duplication non bornees pour la transcription;
- risque de degradation ou d'indisponibilite du processus applicatif.

Condition de sortie: plafond global Flask, plafonds metier post-lecture ou
lecture bornee/streaming, erreurs stables et tests sans `Content-Length`, avec
taille mensongere et juste au-dessus/au-dessous de chaque borne.

### P2-CEL-IDENTITY-RAW-LOG-01 - une identite brute est ecrite dans les logs applicatifs

Faits verifies:

- `app/server.py:169-171` configure le logging standard au niveau INFO.
- `app/memory/memory_store.py:660-692` transmet son logger a
  `memory_identity_write.add_identity()`.
- apres commit, `app/memory/memory_identity_write.py:352` journalise
  `content=%.60s`, soit les 60 premiers caracteres de l'identite user ou LLM.
- ce contenu provient des entrees d'identite persistees, donc peut porter une
  information personnelle ou contextuelle.
- le contrat transversal `app/docs/states/specs/frida-v1-agentic-observability-contract.md:312-331`
  autorise classes d'erreur redacted, compteurs et hashes, pas le contenu brut.
- aucun test ne reference `identity_saved` ni n'impose l'absence de contenu dans
  ce log.

Impact: fuite certaine de contenu vers la sortie de logging a chaque identite
effectivement ajoutee. La retention et les lecteurs effectifs des logs sont hors
perimetre de cette passe; la violation existe deja dans le code.

Condition de sortie: remplacer le contenu par des metadonnees content-free et
ajouter une sentinelle anti-fuite sur les logs standard, pas seulement sur les
projections admin.

### P2-CEL-CHAT-POST-PERSIST-AUX-01 - une panne auxiliaire tardive peut transformer une reponse persistee en erreur utilisateur

Faits verifies:

- dans le chemin non-stream principal,
  `app/core/chat_llm_flow.py:400-408` ajoute et persiste la reponse assistant.
- les traces, l'extraction/ecriture d'identite et la reactivation sont executees
  ensuite sans wrapper local a `:409-428`.
- `save_new_traces()` et plusieurs stores internes attrapent leurs pannes, mais
  toute la chaine n'est pas garantie `never raises`: par exemple
  `app/memory/arbiter.py:677-680` resout les settings et charge le prompt avant
  son `try` transport a `:710`.
- si une exception remonte, le `except Exception` global de
  `app/core/chat_llm_flow.py:862-883` sauvegarde de nouveau la conversation puis
  retourne HTTP 500. La reponse assistant reste donc dans l'etat sauvegarde.
- le chemin de final-lock/override presente la meme sequence non protegee dans
  `app/core/chat_llm_flow.py:190-226`.
- le streaming possede au contraire trois wrappers fail-open explicites a
  `app/core/chat_llm_flow.py:536-589`, appeles apres persistance a `:814-816`.
- les tests couvrent les sequences heureuses et le fail-open interne du periodic
  agent, pas une exception remontant apres persistance dans les chemins
  non-stream ou override.

Impact:

- l'utilisateur recoit une erreur alors que la reponse est durablement visible
  dans la conversation;
- un retry peut produire un tour supplementaire ou une duplication semantique;
- comportement divergent entre non-stream, override et stream.

Condition de sortie: definir une frontiere de commit unique; apres persistance
reussie, tous les effets auxiliaires doivent etre fail-open et observables sans
changer le succes HTTP/terminal. Ajouter des tests d'injection de panne pour
traces, identite, reactivation et logs.

### P2-CEL-MAIN-LLM-BASE-URL-01 - le chat principal ignore `main_model.base_url` runtime

Finding initial revalide sans changement de severite.

Faits verifies:

- `app/core/llm_client.py:108-112` lit la base URL runtime;
- `app/core/llm_client.py:225-226` expose `or_chat_completions_url()`;
- `app/core/chat_llm_flow.py:335-345` construit pourtant
  `f'{config_module.OR_BASE}/chat/completions'`;
- les chemins non-stream et stream reutilisent cette URL a `:374` et `:592-598`;
- les sous-agents principaux utilisent l'abstraction partagee;
- `app/tests/unit/chat/test_chat_llm_flow.py` fournit repetitivement un
  `config_module.OR_BASE` et ne prouve pas l'appel a
  `llm_module.or_chat_completions_url()`.

Impact: divergence entre le transport principal et les transports lateraux des
que la base runtime differe de la constante de configuration. Aucun etat runtime
n'est invoque ici pour minorer ou majorer ce bug.

Condition de sortie: URL partagee injectee par `llm_module`, test non-stream et
stream ou `config.OR_BASE` et runtime pointent volontairement vers deux hotes
differents.

### P3-CEL-PROMPT-FAIL-OPEN-01 - les prompts critiques manquants deviennent silencieusement vides

Finding initial revalide et precise.

Faits verifies:

- `app/core/prompt_loader.py:15-19` retourne `''` sur `OSError`;
- `app/core/chat_prompt_context.py:68-90` ne valide pas les prompts et omet les
  parties vides;
- le chemin chat applique ce systeme partiel dans
  `app/core/chat_service.py:781-845`;
- `app/minimal_validation.py:365-447` sait controler les prompts, mais il s'agit
  d'un validateur operatoire separe; `server.py` ne l'invoque pas au demarrage;
- les tests valident les prompts presents ou le validateur, pas le refus produit
  d'un prompt backend critique absent.

Impact: une erreur de chemin ou de packaging peut demarrer un Frida partiellement
desystemise sans signal produit ferme.

Condition de sortie: classifier prompts critiques/facultatifs et bloquer au
demarrage ou avant l'appel modele avec reason code stable.

### P3-CEL-RAW-EXCEPTION-LOGS-01 - le contrat content-free reste incomplet hors du paquet observabilite

Faits verifies:

- le scan du code de production trouve 81 appels de logging interpolant encore
  une exception brute sous une forme `err=%s` ou equivalente hors tests;
- ils couvrent notamment stores conversations/workspace, memory/identity,
  bootstrap et arbiter;
- `app/memory/arbiter.py:478` et `:737` loggent directement des exceptions de
  transport/parsing;
- `app/memory/memory_traces_summaries.py:720-744` et plusieurs stores loggent
  les exceptions DB/embedding brutes;
- le contrat `app/docs/states/specs/frida-v1-agentic-observability-contract.md:328-331`
  exige `err_class` quand le texte peut contenir contenu, prompt, URL, chemin,
  payload ou secret;
- le lot 5C documente et teste surtout `app/observability`, pas ces familles.

Interpretation bornee: le scan prouve le risque contractuel, pas que chacune des
81 exceptions contient effectivement une donnee sensible a chaque execution.
Le finding P2 precedent est, lui, une fuite certaine et distincte.

Condition de sortie: inventaire raisonne par famille, conversion vers
`err_class`/reason code, tests sentinelles sur les logs standard. Pas de
remplacement mecanique global sans conserver les pannes actionnables.

### P3-CEL-COMPLEXITY-HOTSPOTS-01 - la complexite est concentree dans des fonctions et modules critiques

Ce finding supersede `P3-CEL-LARGE-FILES-HOTSPOTS-01` et requalifie la partie
code de `P2-CEL-DOC-CLOSURE-DRIFT-SERVER-01`. La divergence documentaire de
`server.py` n'a pas ete reauditee dans ce passage code-only; le fait code reste
vivant et est classe P3 architectural.

Modules les plus volumineux:

- `app/tools/web_search.py`: 2655 lignes;
- `app/server.py`: 1884;
- `app/observability/dashboard_read_model.py`: 1688;
- `app/observability/turn_pipeline_read_model.py`: 1391;
- `app/observability/dashboard_observable_modules.py`: 1268;
- `app/core/chat_service.py`: 1255;
- `app/biblio/librarian_tools.py`: 1187;
- `app/biblio/librarian_method_runtime.py`: 1176;
- `app/core/hermeneutic_node/validation/validation_agent.py`: 1128.

Fonctions les plus significatives par taille/branches statiques:

- `minimal_validation._check_ui_assets`: 957 lignes, 53 noeuds;
- `runtime_settings_validation.validate_runtime_section`: 638 lignes, 127 noeuds;
- `chat_llm_flow.run_llm_exchange`: 619 lignes, 72 noeuds;
- `chat_service.chat_response`: 507 lignes;
- `chat_llm_flow.event_stream`: 380 lignes, 61 noeuds;
- `web_search.build_context_payload`: 228 lignes, 129 noeuds;
- `web_search._emit_web_search_runtime_event`: 273 lignes, 103 noeuds;
- `server.api_chat`: 199 lignes, 41 noeuds.

Impact: multiplication des chemins implicites, divergences stream/non-stream,
tests qui figent le mauvais point d'injection et audit ponctuel moins fiable.
Ce n'est pas une demande de refactor global. Toute extraction doit etre bornee
par comportement et precedee de tests d'or.

## REVALIDATION DES FINDINGS DU PREMIER PASSAGE

| Finding initial | Statut seconde passe |
|---|---|
| `P2-CEL-MAIN-LLM-BASE-URL-01` | confirme P2, preuves code renforcees |
| `P2-CEL-DOC-CLOSURE-DRIFT-SERVER-01` | partie documentaire hors seconde passe; fait code requalifie dans `P3-CEL-COMPLEXITY-HOTSPOTS-01` |
| `P3-CEL-PROMPT-FAIL-OPEN-01` | confirme P3; validateur existant mais non branche au demarrage produit |
| `P3-CEL-LARGE-FILES-HOTSPOTS-01` | confirme et supersede par analyse fonctions/branches |

Aucun finding initial ne disparait silencieusement.

## MATRICE DE COUVERTURE CODE

| Zone | Couverture | Controles principaux | Resultat |
|---|---:|---|---|
| Git/source | complete cartographique | HEAD, branche, upstream, status, diff check | propre au controle initial |
| Python global | complete statique | 587 fichiers parses par AST: 326 production, 261 tests | 0 erreur syntaxique |
| Imports locaux | complete statique | 463 aretes; imports `app.*` resolus; SCC calculees | 0 import local non resolu; 4 petits cycles de facade/store |
| JavaScript | complete syntaxique | 72 fichiers web/tests avec `node --check` | 0 erreur |
| Shell applicatif | syntaxique | `bash -n app/run.sh` | 0 erreur |
| Chat/orchestration | profond | `chat_service`, `chat_llm_flow`, sessions, prompt, stream, persistence | 3 findings actifs |
| LLM/settings | profond | client partage, settings runtime, appelants lateraux, tests | base URL principale incoherente |
| Web/URL/PDF | profond | extraction URL, SearxNG, Crawl4AI, PDF, redirections, timeouts | garde SSRF HTML manquant |
| Uploads/documents/audio | profond | routes, tailles, extraction, OCR, transcription, chemins stockage | limites incoherentes |
| Persistence conversations | profond | save atomique catalogue/messages, resultats, rollback logique | atomicite DB coherente; erreur post-commit auxiliaire |
| Memory/identity | profond cible | retrieval, arbiter, traces, evidence, mutables, reactivation, logs | fuite log + risque exceptions brutes |
| Observabilite/admin read models | structurel + scans | projecteurs, guards, dashboard, log sinks | projections defensives; logs standard incomplets |
| Agenda | profond cible | agent, validation, pending state, proposal/write execution | chemin chat fixe `live_write_caldav=False`; confirmations et client requis |
| Biblio | profond cible | agent-first, outils, catalogue client, final locks | client catalogue GET-only et parametres bornes |
| Workspace/Nextcloud code | structurel + points profonds | folders, files, notes, exports, images, compensation | chemins/UUID bornes; pas de SQL injection trouvee |
| SQL | scan global + revue dynamique | execute dynamiques, fragments, parametres | pas d'entree utilisateur injectee dans SQL trouvee |
| Frontend | structurel + sinks | DOM sinks, liens, rendu messages, syntaxe | messages rendus via `textContent`; SVG de dossier issu d'une allowlist |
| Tests | inventaire statique | 261 fichiers Python, 2694 fonctions/methodes `test_*`; tests JS presents | suite non executee |
| Scripts/validation | structurel | minimal validator, exports/smokes, effets possibles | non executes en lecture seule |

## CARTOGRAPHIE CODE

Production Python:

- 326 fichiers, dont 317 modules hors `__init__.py`;
- `core`: 117 fichiers;
- `biblio`: 52;
- `admin`: 33;
- `observability`: 33;
- `agenda`: 31;
- `memory`: 27;
- `tools`: 20;
- `identity`: 7;
- racine/config/scripts: 6.

Topologie logique suivie:

1. `server.py`: transport Flask, guards et delegation;
2. `core/chat_service.py`: composition du tour et des lanes;
3. `core/chat_llm_flow.py`: appel modele, streaming, finalisation et persistence;
4. `core/llm_client.py`: transport/configuration partagee;
5. Biblio, Agenda, Web, Adobe, documents actifs, workspace notes/files comme
   lanes laterales;
6. Hermeneutic Node et validation avant sortie;
7. conversations, traces, identity et observabilite comme persistences/projections.

Cycles d'import detectes:

- exports projection / exports facade / store;
- generated images projection / facade / store;
- `biblio.librarian_library_tools` / `biblio.librarian_tools`;
- workspace folder notes facade / store.

Ils reposent sur des imports locaux tardifs et ressemblent a des cycles de
facade deliberes. Aucun n'est classe bug; ils augmentent seulement le couplage.

## PARCOURS CRITIQUES REVALIDES

### Chat

Le parcours composer vers reponse a ete suivi de `server.api_chat()` a
`chat_service.chat_response()`, puis aux final locks ou a
`chat_llm_flow.run_llm_exchange()`. Les deux voies stream/non-stream, la
persistence atomique et les erreurs finales ont ete relues. Les divergences
base URL et post-persistence sont les deux findings fonctionnels principaux.

### Biblio

Le code maintient la frontiere voulue: le LLM bibliothecaire choisit une methode
et des outils, tandis que les outils deterministes bornent l'acces. Le client
catalogue refuse toute methode autre que GET dans
`app/biblio/catalogue_client.py:489-506`. Les outils ont allowlist, budgets et
validation de parametres. Aucun finding nouveau confirme dans cette passe.

Cette conclusion est code-only: aucun cas produit live ni artefact Biblio n'a
ete rejoue.

### Agenda et mutations externes

Le chemin chat appelle `execute_pending_plan()` avec
`live_write_caldav=False` dans `app/agenda/chat_runtime.py:381-390`.
`app/agenda/write_execution.py:88-143` exige methode de mutation, pending action
correspondante, draft prive valide, confirmation renforcee pour les cas
sensibles et client d'ecriture. Aucun envoi mail n'existe dans le code inventorie.

Conclusion: pas de mutation utilisateur CalDAV implicite trouvee. Aucun write
live n'a ete tente.

### Persistence et chemins fichiers

La sauvegarde conversations catalogue/messages est atomique dans une seule
transaction (`app/core/conversations_store.py:548-646`). Les fragments SQL
dynamiques observes reposent sur booleens internes, listes de colonnes
allowlistees ou DDL constants. Les IDs workspace sont normalises en UUID et les
storage keys rejettent chemins absolus et `..`.

La faiblesse de persistence trouvee n'est donc pas une transaction partielle:
c'est la semantique HTTP apres commit dans le chemin chat.

### Frontend

Les messages utilisateur et assistant sont rendus avec `textContent`, pas comme
HTML. Les principaux `innerHTML` contiennent des icones constantes ou vident des
conteneurs. `folder.icon_svg` est le seul sink alimente par une structure, mais
`icon_key` est valide par allowlist serveur et le SVG est projete depuis cette
allowlist. Aucun XSS confirme.

## SCANS TRANSVERSAUX

Resultats statiques:

- 342 `except Exception` dans le code de production: beaucoup implementent un
  fail-open explicite, mais ils imposent une lecture de frontiere et non une
  confiance globale;
- aucun argument par defaut mutable detecte;
- aucun `eval`, `exec`, `subprocess` ou `os.system` dans la production;
- tous les appels reseau directs identifies ont un timeout;
- le lecteur PDF borne taille, pages, caracteres, redirections et IP;
- aucun import local non resolu;
- aucun appel SQL dynamique controle par une valeur utilisateur trouve;
- un seul log transmet explicitement une variable nommee `content`:
  `memory_identity_write.py:352`;
- 81 interpolations d'exception brute restent a traiter par analyse de risque.

Heuristique de tests:

- 224 des 317 modules hors `__init__.py` sont importes directement par au moins
  un test Python;
- 93 ne le sont pas directement, souvent parce qu'ils passent par une facade,
  une route serveur ou un script;
- cette mesure ne vaut ni couverture de ligne ni preuve comportementale.

## TESTS ET PREUVES

Execute pendant cette seconde passe:

- parse AST de 587 fichiers Python: succes;
- `node --check` sur 72 fichiers JavaScript web/tests: succes;
- `bash -n app/run.sh`: succes;
- scans imports, cycles, SQL, appels reseau, logs, complexite et sinks DOM;
- `git diff --check`: succes.

Non execute:

- `pytest` et `node --test`;
- smokes Biblio/Agenda/modeles;
- `minimal_validation.py`;
- navigateur/Playwright;
- appels modele ou services live.

Raison: plusieurs suites et validateurs importent `server.py`, initialisent des
stores, ecrivent caches/fichiers temporaires, appellent des endpoints ou peuvent
muter DB/runtime. L'exigence de lecture seule interdit de supposer qu'un
`--collect-only` ou un validateur est sans effet. Les checks syntaxiques ont ete
choisis parce qu'ils ne chargent pas l'application.

## ANGLES MORTS

- aucune preuve comportementale live n'est produite dans cette passe code-only;
- aucune couverture dynamique de branches ou concurrence;
- aucune validation du reseau ou des protections internes de Crawl4AI;
- aucune mesure memoire reelle des uploads;
- aucune introspection DB ni verification de migrations appliquees;
- aucune inspection de logs reels, pour eviter tout contenu personnel;
- aucun rendu navigateur;
- les 326 fichiers ont ete inventories et parses, mais pas tous relus ligne par
  ligne avec la meme profondeur;
- les specs ont servi de contrats cibles, pas d'objet d'audit documentaire
  exhaustif.

## PROGRAMME DE LOTS A CADRER

Ordre rationnel, sans execution automatique:

1. garde URL publique partagee Web/PDF, avec preuve SSRF et redirections;
2. plafonds uploads globaux et metier, en commencant par transcription et
   documents actifs;
3. suppression du contenu identitaire et traitement des logs d'exception par
   familles;
4. frontiere post-persistence commune aux trois voies chat;
5. base URL runtime du chat principal;
6. fail-closed des prompts critiques;
7. seulement ensuite, extractions structurelles bornees des fonctions les plus
   complexes, protegees par tests d'or.

Chaque lot de correction devra etre discute et transmis a Celebrimbor. Aucun de
ces lots n'a ete lance dans cet audit.

## VERIFY

- instructions locales relues: `AGENTS.md`, `memory.md`, prompt `001`;
- instructions Celebrimbor relues: `/opt/platform/fridadev/AGENTS.md`;
- source distante uniquement lue sous `/opt/platform/fridadev`;
- HEAD audite: `afdf19fa54c6a1602232e54e40bb23a6ba33787d`;
- worktree distant propre aux controles initial et final, meme HEAD et ecart upstream `0 0`;
- aucun fichier distant cree ou modifie;
- aucun test mutable, write DB, commit, pull, push, restart ou rebuild;
- seul le rapport local durable a ete ecrit pendant l'audit; ce transfert dans
  le depot est posterieur, documentaire et sans modification de code/runtime.

## RISKS

Le risque principal restant est l'absence d'execution comportementale: les
findings sont prouves par controle de flux et contrats, mais leur manifestation
reelle depend parfois d'une exception, d'un upload mal borne ou du reseau du
crawler.

Le risque inverse est la fausse assurance par densite de tests. Les 2694
fonctions/methodes `test_*` prouvent un investissement important, pas que les
bons invariants sont testes. La base URL principale et la dissymetrie des gardes
URL montrent precisement comment un grand corpus peut laisser passer, voire
figer, une incoherence d'architecture.

Verdict code-only: architecture riche et largement contractualisee, mais pas
encore suffisamment homogene aux frontieres de securite, de commit et de
configuration pour etre qualifiee de robuste sans reserve.
