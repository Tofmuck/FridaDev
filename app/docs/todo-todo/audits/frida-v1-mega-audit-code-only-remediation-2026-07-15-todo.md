# Frida V1 - Mega-audit code-only 2026-07-15 - TODO de remediation

Statut: actif, docs-only a la creation.
Agent cible: Celebrimbor, racine `/opt/platform/fridadev`.
Branche de reference au moment de l'audit: `FridaV1-Mega-Audit-Code-Stack`.
HEAD audite: `afdf19fa54c6a1602232e54e40bb23a6ba33787d`.

## Sources de verite

- Audit source:
  `app/docs/states/audits/frida-v1-mega-audit-code-only-2026-07-15.md`.
- Registre canonique:
  `app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-todo.md`.
- Refactors structurels existants:
  `app/docs/todo-todo/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`.
- Contrat observabilite:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`.

## Regles de conduite

- Lire `AGENTS.md`, les sources ci-dessus et l'etat Git courant avant chaque
  lot. Le HEAD de l'audit est un point de depart, jamais une preuve actuelle.
- Avant patch, revalider le finding dans le code courant et repondre
  explicitement: `Existe-t-il un meilleur plan ?`.
- Un lot ne vaut pas autorisation pour le suivant. Un lot = un sujet, une
  responsabilite, un commit et un retour de preuve distincts.
- Cette TODO applique la doctrine de consolidation: corriger, simplifier et
  tester l'existant sans nouvelle feature, route, vue, provider, workflow,
  collecte de contenu ni mecanisme generique "pour plus tard".
- Hors perimetre: Docker, Caddy, Authelia, secrets, reseaux, DB/stack OVH,
  reactivation Agenda, Mail runtime, migrations non imposees par un bug et
  refactor opportuniste.
- Ne jamais afficher contenu utilisateur, prompt, URL sensible complete, log
  brut, token, mot de passe, DSN ou secret.
- Apres chaque lot: `git status --short`, `git diff --check`, relecture du
  diff utile, tests adaptes, commit/push selon `AGENTS.md`, puis retour au
  demandeur. Aucun enchainement automatique.

## Decision produit - logs prives identity/memory

Le 16 juillet 2026, l'utilisateur a explicite le contexte produit courant:
FridaDev est mono-utilisateur et Tof en est aussi l'unique operateur. La
visibilite du contenu identity/memory deja journalise dans les logs prives du
serveur OVH est intentionnelle et preservee comme outil d'inspection du
systeme. L'hypothese normative historique
`P2-CEL-IDENTITY-RAW-LOG-01` est donc requalifiee en **non-finding dans le
contexte produit courant, par decision explicite de l'utilisateur**. Elle ne
constitue ni une correction, ni une dette acceptee, ni un lot de remediation.

Cette decision n'autorise aucun nouveau log, aucune augmentation de contenu,
collecte, telemetrie, projection admin, export ou surface produit. JSONL,
projections admin, exports, telemetrie externe et retours d'agent restent
content-free. Les secrets restent interdits; les textes d'exceptions brutes du
Lot 10F restent un sujet distinct a classifier et ne sont pas autorises
globalement.

## Ordre de traitement

1. Lot 10A - garde SSRF HTML/Crawl4AI.
2. Lot 10B - plafonds uploads/documents/transcription.
3. Lot 10C - frontiere post-persistence du chat.
4. Lot 10D - URL runtime du LLM principal.
5. Lot 10E - prompts critiques fail-closed.
6. Lot 10F - requalification contractuelle des exceptions brutes en logs.
7. Lot 10G - raccord de complexite au Lot 9, sans extraction anticipee.

L'audit historique a initialement rapporte cinq P2 et trois P3. Apres la
decision produit ci-dessus, la remediation courante contient quatre P2 et trois
P3: les Lots 10A a 10D sont P2 et les Lots 10E a 10G sont P3. Aucun P0/P1
n'est confirme par l'audit code-only.

## Lot 10A - Garde URL publique partagee pour HTML/Crawl4AI

Finding cible: `P2-CEL-WEB-HTML-SSRF-GUARD-01`.

Faits revalides et clotures:

- au HEAD historique `fbbb056e`, `app/tools/web_search.py` envoyait les URL
  HTML explicites et les resultats de recherche vers Crawl4AI sans garde URL
  equivalente au lecteur PDF;
- le commit Celebrimbor `e616616c` a introduit la politique partagee amont
  FridaDev avant le payload `/md`, et conserve la garde PDF avant chaque
  requete et redirection controlee par FridaDev;
- la preuve Sauron independante du 2026-07-16 couvre maintenant aussi les
  navigations et redirections effectuees en aval par Crawl4AI.

Perimetre strict:

- `app/tools/web_search.py`, `app/tools/web_pdf_reader.py` et leurs tests;
- extraction partagee seulement si elle diminue vraiment la duplication et
  garde une responsabilite URL nette;
- aucun changement de provider, de reseau, de Docker, de Crawl4AI ni d'UI.

Checklist:

- [x] Reproduire par test controle que l'URL HTML explicite atteint ou peut
  atteindre le payload crawl sans garde locale.
- [x] Identifier la politique PDF reutilisable et verifier ses dependances de
  resolution DNS et de redirection.
- [x] Definir une unique frontiere de validation avant tout appel Crawl4AI.
- [x] Prouver le traitement des redirections sous controle de FridaDev, puis
  la barriere aval Crawl4AI verifiee independamment par Sauron au 2026-07-16.
- [x] Couvrir par fakes: IPv4 privee/loopback/link-local/reservee, IPv6
  loopback/link-local/unique-local, DNS vers IP non globale, noms internes,
  URL publique, redirection publique puis interne.
- [x] Prouver que l'URL rejetee ne produit ni requete crawl ni payload externe,
  avec reason code stable et content-free.

Critere de sortie atteint:
la politique URL publique FridaDev borne les voies PDF et HTML avant le crawler,
et la barriere Crawl4AI reelle borne chaque navigation et redirection aval. Les
preuves applicatives et plateforme sont content-free et ne necessitent aucune
nouvelle action runtime dans ce lot documentaire.

### Validation et cloture Lot 10A - 2026-07-16

Statut: **clos; `P2-CEL-WEB-HTML-SSRF-GUARD-01` ferme**.

Revalidation au HEAD de depart
`fbbb056eba5c8ca0b18466f203fe051b277b8228`:

- `app/tools/web_search.py` construisait le payload `/md`, puis appelait
  Crawl4AI sans garde URL/DNS locale; les voies URL explicite HTML et resultat
  SearXNG rejoignaient toutes deux cette primitive;
- `app/tools/web_pdf_reader.py` validait l'URL initiale et chaque redirection
  HTTP qu'il suivait lui-meme, mais portait seul cette politique;
- une URL PDF explicite rejetee avant detection pouvait en outre retomber vers
  Crawl4AI parce que le resultat bloque etait marque `detected=False`.

Correction bornee:

- `app/tools/web_public_url_policy.py` porte maintenant l'unique politique
  HTTP(S) publique: noms internes, URL ambigues, IP IPv4/IPv6 non globales et
  toutes les adresses issues de la resolution DNS sont refusees fail-closed;
- `app/tools/web_pdf_reader.py` reutilise cette politique avant chaque requete
  et redirection qu'il controle, sans relacher le reason code PDF historique;
- `app/tools/web_search.py::_crawl_markdown_with_status()` applique la meme
  politique avant resolution du token, construction du payload et appel `/md`.
  Cette frontiere couvre donc URL explicite, resultat SearXNG et fallbacks de
  filtre Crawl4AI;
- une URL PDF explicite bloquee reste desormais sur la voie PDF et ne retombe
  plus vers Crawl4AI.

Preuves amont FridaDev au commit `e616616c`:

- 162 tests unitaires web executes en environnement isole sans reseau reel;
- fakes couvrant le rejet IPv4/IPv6/interne, DNS mixte public/non global,
  resolution en echec, URL publique, resultat SearXNG et absence de payload ou
  appel Crawl4AI pour les refus;
- test PDF couvrant la redirection publique vers loopback effectivement
  observable par FridaDev.

Barriere aval Crawl4AI, preuve Sauron independante du 2026-07-16:

- image active derivee du digest Crawl4AI 0.8.5 epingle;
- garde URL initiale, interception Playwright et wrapper Chromium imposant le
  proxy SOCKS sur la navigation concernee;
- proxy resolvant chaque destination lors de la connexion, refusant les IP non
  globales puis se connectant a l'IP validee sans seconde resolution DNS;
- preuves ciblees couvrant loopback, noms internes, IPv4/IPv6 non globales,
  redirections Chromium et DNS rebinding;
- `/md` actif refusant une cible loopback avec erreur et reason code
  content-free; conteneurs Crawl4AI et FridaDev healthy pendant la verification.

Conclusion de cloture:

- la garde amont FridaDev limite les URL qui atteignent le transport Crawl4AI;
- la barriere aval Crawl4AI controle la destination effectivement naviguee,
  y compris les redirections et la resolution au moment de la connexion;
- la cloture vaut pour l'usage Crawl4AI de FridaDev vise par ce finding. Elle
  ne pretend pas etablir un firewall kernel generique pour du code arbitraire.

P3 distinct, non bloquant, non confirme, hors cloture P2:

- `P3-SAU-CRAWL4AI-CHROMIUM-FAKE-PROXY-SOCKET-01`: le
  `ConnectionResetError` observe historiquement n'a pas ete reproduit dans
  13 executions isolees du test Chromium, toutes sorties code 0 et `stderr`
  vide, sans patch;
- cette non-reproduction borne une hypothese de course dans l'environnement de
  test actuel. Elle ne qualifie pas le P3 de `stale`, corrige ou clos, et ne
  permet pas d'affirmer que la course est impossible;
- le P3 reste non bloquant et distinct de
  `P2-CEL-WEB-HTML-SSRF-GUARD-01`, qui demeure ferme. Il ne justifie ni la
  reouverture du Lot 10A ni une correction speculative;
- seul declencheur de reouverture: traceback, exception asynchrone ou `stderr`
  anormal reproduit par ce test.

## Lot 10B - Plafonds coherents des uploads, documents et transcription

Finding cible: `P2-CEL-UPLOAD-LIMITS-01`.

Faits revalides au HEAD de depart du sous-lot:

- aucun plafond Flask global n'est configure;
- workspace et documents actifs font confiance a `Content-Length` avant de
  lire `request.files`; documents actifs acceptent une taille absente/invalide
  comme zero puis lisent integralement le fichier;
- workspace possede deja un second controle post-lecture, contrairement aux
  documents actifs;
- transcription lisait et dupliquait le blob audio sans plafond.

### Tranche transcription Whisper - fermee le 2026-07-16

Statut borne:

- [x] `SOUS-LOT PLATEFORME WHISPER FERME`: Whisper lit par blocs, accepte
  exactement `16 Mio` (`16 777 216` octets), refuse au-dessus, borne les
  durees d'entree et normalisee a `305 s`; Caddy borne le corps de
  `POST /api/chat/transcribe` a `17 Mio` (`17 825 792` octets). La preuve
  plateforme inclut un rejet HTTP 413 a `17 Mio + 1 octet` et un WAV silence
  synthetique de `300 s` / `9 600 044` octets transcrit en environ `37,5 s`;
- [x] regression WebM plateforme fermee sur preuve produit reelle: la premiere
  livraison avait valide un WebM Chromium court dont la duree de conteneur
  etait lisible, puis un vrai WebM utilisateur court a revele un rejet HTTP 422
  `audio_duration_unknown` avant normalisation. La correction traite desormais
  cette duree inconnue comme un etat provisoire autorisant seulement une
  normalisation bornee a `306 s`; le WAV normalise doit rester connu et
  inferieur ou egal a `305 s` avant `whisper-cli`, sans fallback brut si cette
  normalisation echoue. La suite plateforme `19/19` hors reseau couvre
  notamment un vrai WebM decodable sans `format.duration`; les probes
  synthetiques WebM et WAV `300 s` ont reussi. Enfin, la preuve utilisateur du
  16 juillet 2026 a rejoue le vrai WebM navigateur qui avait echoue
  (`171 527` octets): normalisation a `6,4075 s`, HTTP 200 et transcription
  terminee, sans restart ni OOM;
- [x] `SOUS-LOT APPLICATION WHISPER FERME`: la route FridaDev refuse un
  `Content-Length` valide strictement superieur a `17 Mio` avant tout acces a
  `request.files` ou `request.form`, avec
  `reason_code=audio_request_too_large`; le service lit par blocs au plus
  jusqu'a `16 Mio + 1 octet`, accepte exactement `16 Mio` et refuse au-dessus
  avant tout appel Whisper avec `reason_code=audio_file_too_large`;
- [x] le frontend s'arrete a `300000 ms`, conserve les valeurs configurees
  plus basses, plafonne les valeurs superieures, garde
  `MediaRecorder.start()` sans `timeslice`, un blob, un upload et une
  transcription, et refuse `16 Mio + 1 octet` avant `FormData` et `fetch`;
- [x] seuls `audio_file_too_large`, `audio_duration_unknown` et
  `audio_duration_too_long` sont propages depuis les reponses Whisper 413/422
  avec statut, message francais stable et `reason_code`; toute autre structure
  reste une 502 generique sans detail amont;
- [x] preuves sans reseau: suites ciblees `9` tests Node et `24` tests Python;
  suites elargies `120` tests frontend Node, `113` unitaires chat, `16`
  integrations chat et `25` contrats frontend Python, toutes vertes;
- [x] `LOT 10B GLOBAL FERME LE 2026-07-22`: les voies documents actifs et
  workspace sont maintenant bornees avant et apres parsing; la tranche Whisper
  precedente reste inchangee et revalidee.

Perimetre strict:

- `app/server.py`, les services workspace/documents actifs/transcription et
  leurs tests de contrat;
- aucune nouvelle option runtime generique sans besoin demontre;
- ne pas modifier formats produits, OCR, provider Whisper ou workflow UI.

Checklist:

- [x] Inventorier les routes multipart et leurs limites existantes; conserver
  les valeurs produit deja decidees ou justifier toute borne avec contrat et
  effets de bord.
- [x] Poser une premiere barriere Flask coherente avec les plafonds metier et
  une erreur HTTP stable, sans masquer les erreurs de validation propres a une
  route.
- [x] Conserver ou ajouter un controle de taille apres lecture pour chaque voie
  qui materialise encore le contenu en memoire; ne jamais accepter une taille
  inconnue comme zero par defaut.
- [x] Ajouter un plafond explicite a la transcription avant lecture complete et
  avant duplication multipart. Fait pour la seule tranche Whisper par lecture
  bornee en blocs, sans chunking, streaming ni seconde voie; les autres uploads
  du Lot 10B sont maintenant fermes par la meme exigence, sans raccorder
  Whisper a leur primitive.
- [x] Tester, par route: `Content-Length` absent, invalide, mensonger, limite
  exacte, limite moins un, limite plus un et fichier effectivement trop grand.
- [x] Prouver qu'aucun test ne contacte Whisper, OCR ou un service externe.

### Validation et cloture Lot 10B - 2026-07-22

Statut: **clos; `P2-CEL-UPLOAD-LIMITS-01` ferme**.

Revalidation au HEAD de depart
`804ff5fb907b600c0c5d4a8c399034d8b6fb8503`:

- les trois seules voies `request.files` / `request.form` de `app/server.py`
  etaient Whisper, workspace et documents actifs;
- Flask `3.0.3` / Werkzeug `3.1.8` etaient executes avec
  `MAX_CONTENT_LENGTH=None` avant correction;
- sans longueur fiable et avec `wsgi.input_terminated`, la vraie frontiere
  WSGI materialisait un multipart au-dela du plafond simule sur documents
  actifs et workspace;
- les deux services documentaires appelaient `file_obj.read()` sans borne;
- le runtime conservait `ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS=0`; cette valeur
  n'a pas ete modifiee.

Correction bornee:

- `app/server.py` pose `MAX_CONTENT_LENGTH=41943040` (`40 MiB`) sans nouvelle
  option runtime; Werkzeug borne ainsi les flux termines sans longueur fiable,
  tandis que son safe fallback ne consomme rien sans longueur ni signal WSGI;
- le handler 413 conserve les reason codes de chaque route identifiable:
  `active_document_upload_too_large`, `folder_document_too_large` et
  `audio_request_too_large`;
- `app/core/document_upload_reader.py` lit seulement les uploads documents
  actifs/workspace, par blocs, jusqu'a la limite pertinente plus un octet;
  Whisper reste sur sa lecture bornee historique et n'est pas modifie;
- les deux services acceptent la limite exacte, refusent `limite + 1`, ne
  retournent jamais le prefixe observe et n'appellent aucun effet aval apres
  refus;
- le controle workspace post-materialisation devenu mort est supprime.

Integrite preservee:

- les octets acceptes atteignent sans alteration l'extracteur ou le stockage;
- l'extracteur textuel `complete` conserve les sentinelles synthetiques de
  debut, milieu et fin;
- les lanes active-document et workspace injectent les trois sentinelles dans
  le payload modele fake quand le document est admissible;
- en exclusion, aucun fragment sentinelle n'atteint le modele, l'appel modele
  continue, le signal compact est present et Frida peut repondre honnetement
  qu'elle ne dispose pas du document;
- aucune troncature, chunking, resume automatique ou echec global du chat n'est
  introduit.

Preuves sans reseau:

- reproduction pre-correctif a la frontiere WSGI: longueur absente, invalide et
  negative consommaient le multipart complet au-dela du plafond simule;
- controle Flask/Werkzeug apres configuration: les memes cas s'arretent au
  plafond et rendent HTTP 413; une longueur mensongere plus petite ne permet
  pas de lire au-dela de la longueur exposee par WSGI;
- suite ciblee nouvelle: `12/12` tests;
- suites obligatoires routes/services/extracteur/lanes: `121/121` tests;
- revalidation Whisper inchange: `24/24` tests;
- suite documentaire elargie: `54/56` tests; les deux erreurs
  d'observabilite image active sont reproduites a l'identique au HEAD initial
  et ne traversent ni l'upload corrige ni les lanes textuelles;
- decouverte Python complete comparee: HEAD initial `2465` tests, patch `2477`
  tests, avec exactement les memes `22` echecs et `16` erreurs hors Lot 10B;
  les `12` tests ajoutes expliquent seuls l'augmentation et sont tous verts;
- streams instrumentes: au plus `limite + 1` octet lu et reste du flux non
  consomme apres refus;
- aucun reseau externe, aucun contenu utilisateur et aucune donnee persistante
  operateur utilises.

Critere de sortie:
aucune voie d'upload auditee ne consomme sans borne le corps effectif; les
erreurs sont stables et les limites sont testees sur la taille reelle, pas
seulement sur l'en-tete client.

## Lot 10C - Frontiere de succes apres persistence du chat

Finding cible: `P2-CEL-CHAT-POST-PERSIST-AUX-01`.

Faits a revalider:

- les voies non-stream et final-lock persistent la reponse assistant puis
  executent traces, identity et reactivation sans frontiere fail-open commune;
- une exception tardive peut retourner HTTP 500 apres persistence reussie;
- le streaming possede deja des wrappers post-persistence explicites.

Perimetre strict:

- `app/core/chat_llm_flow.py`, dependances auxiliaires immediates et tests
  chat non-stream/stream/override;
- ne pas changer prompts, modele, persistence primaire, routes, schema DB ou
  decisions Biblio/Agenda;
- ne pas attraper une panne de persistence primaire sous couvert de fail-open.

Checklist:

- [ ] Tracer les trois voies jusqu'au point de persistence et nommer la
  frontiere exacte entre succes produit et effets auxiliaires.
- [ ] Comparer les wrappers stream aux voies non-stream/final-lock sans copier
  aveuglement une abstraction de taille excessive.
- [ ] Rendre fail-open apres commit uniquement traces, identity, reactivation
  et observabilite auxiliaire; conserver une trace content-free de la panne.
- [ ] Injecter une panne dans chaque effet auxiliaire apres persistence pour
  non-stream et final-lock/override.
- [ ] Prouver HTTP/terminal de succes, reponse assistant unique et durable,
  absence de second save semantique et absence de duplication au retry.
- [ ] Rejouer les contrats stream pour prouver que les garanties existantes ne
  regressent pas.

Critere de sortie:
apres persistence reussie de la reponse assistant, une panne auxiliaire ne
change plus le succes utilisateur. Une panne avant persistence reste une vraie
erreur et n'est pas masquee.

## Lot 10D - URL runtime commune du LLM principal

Finding cible: `P2-CEL-MAIN-LLM-BASE-URL-01`.

Faits a revalider:

- `app/core/llm_client.py` expose `or_chat_completions_url()` a partir des
  settings runtime;
- `app/core/chat_llm_flow.py` construit encore une URL depuis
  `config_module.OR_BASE` pour le chat principal;
- stream et non-stream reutilisent cette divergence.

Perimetre strict:

- `app/core/llm_client.py`, `app/core/chat_llm_flow.py` et tests chat;
- aucun changement de modele, provider, settings UI, secret ou fallback
  produit; `OR_BASE` reste le default compatible s'il est encore requis.

Checklist:

- [ ] Revalider les appelants stream et non-stream ainsi que le point
  d'injection runtime.
- [ ] Faire converger le chat principal vers l'abstraction URL partagee, sans
  dupliquer la logique de normalisation.
- [ ] Tester avec `config_module.OR_BASE` et `main_model.base_url` dirigeant
  volontairement vers deux hotes synthetiques distincts.
- [ ] Prouver, avec transport fake, que stream et non-stream choisissent la
  valeur runtime et ne contactent aucun provider reel.
- [ ] Verifier les sous-agents voisins pour eviter une nouvelle divergence de
  configuration, sans les refactorer hors besoin prouve.

Critere de sortie:
le chat principal suit la meme source runtime que le client LLM partage dans
les deux modes de transport, par tests differenciants.

## Lot 10E - Prompts critiques fail-closed

Finding cible: `P3-CEL-PROMPT-FAIL-OPEN-01`.

Faits a revalider:

- `app/core/prompt_loader.py` retourne une chaine vide sur `OSError`;
- le contexte chat omet silencieusement les prompts vides;
- `minimal_validation.py` connait deja des controles non branches au demarrage
  produit.

Perimetre strict:

- chargeur de prompt, contexte chat, validation existante et tests;
- ne pas transformer tous les prompts en configuration runtime ni modifier leur
  texte/metier;
- ne pas faire echouer un prompt facultatif sans classification explicite.

Checklist:

- [ ] Inventorier les prompts effectivement critiques et facultatifs dans le
  chemin chat courant, avec sources de verite documentaires.
- [ ] Choisir le plus petit point de refus fiable: demarrage seulement si la
  criticite est globale, sinon avant appel modele.
- [ ] Produire un reason code stable, content-free et actionnable pour un
  prompt critique absent, illisible ou vide.
- [ ] Tester prompts critiques absents/vides/illisibles, prompt facultatif
  absent, et chemin nominal.
- [ ] Prouver qu'aucun appel modele ne part apres le refus d'un prompt critique.

Critere de sortie:
une installation incompletement packagee ne peut plus lancer un chat sans son
contexte critique, tandis que les absences explicitement facultatives restent
traitees selon leur contrat.

## Lot 10F - Requalification contractuelle des exceptions brutes en logs

Finding cible: `P3-CEL-RAW-EXCEPTION-LOGS-01`.

Conflit a resoudre avant tout patch:

- l'audit du 2026-07-15 trouve 81 interpolations d'exception brute dans les
  loggers standards et cite le contrat content-free;
- le Lot 6J precedent a classe une partie des logs DB/stores/memoire comme
  internes/non publics, donc hors correction alors attendue.

La decision historique ne suffit pas a ecarter un contrat normatif plus large.
Elle doit etre revalidee par le code courant et le texte exact du contrat.

Perimetre strict:

- inventaire et classification des familles de log, puis seulement les familles
  confirmees non conformes;
- ne pas remplacer mecaniquement chaque `err=%s` et ne pas supprimer les
  diagnostics utiles;
- la decision produit sur les logs prives identity/memory ne requalifie pas les
  textes d'exceptions brutes; ce lot reste distinct et doit les classifier sans
  les autoriser globalement.

Checklist:

- [ ] Reexecuter le scan sur le HEAD courant et produire un inventaire
  content-free par famille, fichier, surface, type d'exception et potentiel de
  contenu/secret/URL/chemin/payload.
- [ ] Lire les clauses pertinentes du contrat et decider, par preuve, si les
  logs standards internes sont dans son champ normatif ou une limite explicite.
- [ ] Revalider les decisions Lot 6J, sans les traiter comme intouchables.
- [ ] Si une famille est non conforme, la convertir vers `err_class` et reason
  code en conservant une panne actionnable; ajouter une sentinelle synthetique.
- [ ] Si une famille est hors champ, documenter la requalification `stale` ou
  `accepted` avec fichiers, appelants et raison precise dans cette TODO.
- [ ] Ne fermer le finding qu'apres classification complete des hits actuels,
  pas sur le nombre 81 historique.

Critere de sortie:
le champ du contrat et le statut de chaque famille sont explicites. Les logs
couverts par le contrat ne peuvent plus interpoler un texte d'exception
susceptible de contenir du contenu, et aucun remplacement global aveugle n'est
introduit.

## Lot 10G - Raccord de la complexite au Lot 9

Finding cible: `P3-CEL-COMPLEXITY-HOTSPOTS-01`.

Faits a revalider:

- les hotspots principaux sont `minimal_validation._check_ui_assets`,
  `runtime_settings_validation.validate_runtime_section`,
  `chat_llm_flow.run_llm_exchange`, `chat_service.chat_response`, les flows
  web search, `server.py` et plusieurs read-models;
- ce finding supersede l'ancien simple signalement de gros fichiers;
- une TODO Lot 9 existe deja et impose des golden tests avant toute extraction.

Perimetre strict:

- documentation et priorisation seulement dans ce Lot 10G;
- aucune extraction, aucun renommage, aucun deplacement runtime;
- le travail de code reste exclusivement dans les sous-lots 9.0 puis 9A-9H.

Checklist:

- [ ] Comparer les hotspots de l'audit au decoupage 9A-9H existant.
- [ ] Marquer les recouvrements et les absences, sans creer de deuxieme
  roadmap de refactor concurrente.
- [ ] Definir le premier candidat seulement apres Lot 9.0, selon criticite,
  couverture golden et reduction de responsabilite demontrable.
- [ ] Si un bug P2 apparait pendant un refactor futur, stopper et ouvrir un lot
  correctif autonome.

Critere de sortie:
la dette structurelle nouvellement mesuree est absorbee par le Lot 9 existant,
sans faux refactor ni multiplication de roadmaps.

## Cloture de cette TODO

- [ ] Revalider chaque finding avant son lot.
- [ ] Fermer, requalifier `stale` ou accepter explicitement chaque P2/P3 avec
  preuves datees.
- [ ] Mettre a jour le registre canonique du mega-audit apres chaque lot.
- [ ] Archiver cette TODO sous `app/docs/todo-done/audits/` seulement quand les
  Lots 10A-10G sont tous resolus ou requalifies avec preuve.

## Preuve minimale par lot

Retour Celebrimbor attendu: plan alternatif evalue, finding valide/invalide,
perimetre reel, fichiers touches, tests executes et leurs resultats, effets de
bord cherches, statut `git diff --check`, statut Git, hash de commit et push.
Les artefacts et sorties restent content-free.
