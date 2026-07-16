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

## Ordre de traitement

1. Lot 10A - garde SSRF HTML/Crawl4AI.
2. Lot 10B - plafonds uploads/documents/transcription.
3. Lot 10C - fuite certaine de contenu identity dans les logs.
4. Lot 10D - frontiere post-persistence du chat.
5. Lot 10E - URL runtime du LLM principal.
6. Lot 10F - prompts critiques fail-closed.
7. Lot 10G - requalification contractuelle des exceptions brutes en logs.
8. Lot 10H - raccord de complexite au Lot 9, sans extraction anticipee.

Les Lots 10A a 10E sont P2. Les Lots 10F a 10H sont P3. Aucun P0/P1 n'est
confirme par l'audit code-only.

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

Faits a revalider:

- aucun plafond Flask global n'est configure;
- workspace et documents actifs font confiance a `Content-Length` avant de
  lire `request.files`; documents actifs acceptent une taille absente/invalide
  comme zero puis lisent integralement le fichier;
- workspace possede deja un second controle post-lecture, contrairement aux
  documents actifs;
- transcription lit et duplique le blob audio sans plafond.

Perimetre strict:

- `app/server.py`, les services workspace/documents actifs/transcription et
  leurs tests de contrat;
- aucune nouvelle option runtime generique sans besoin demontre;
- ne pas modifier formats produits, OCR, provider Whisper ou workflow UI.

Checklist:

- [ ] Inventorier les routes multipart et leurs limites existantes; conserver
  les valeurs produit deja decidees ou justifier toute borne avec contrat et
  effets de bord.
- [ ] Poser une premiere barriere Flask coherente avec les plafonds metier et
  une erreur HTTP stable, sans masquer les erreurs de validation propres a une
  route.
- [ ] Conserver ou ajouter un controle de taille apres lecture pour chaque voie
  qui materialise encore le contenu en memoire; ne jamais accepter une taille
  inconnue comme zero par defaut.
- [ ] Ajouter un plafond explicite a la transcription avant lecture complete et
  avant duplication multipart; preferer lecture bornee/streaming seulement si
  c'est necessaire pour ne pas empiler une seconde voie.
- [ ] Tester, par route: `Content-Length` absent, invalide, mensonger, limite
  exacte, limite moins un, limite plus un et fichier effectivement trop grand.
- [ ] Prouver qu'aucun test ne contacte Whisper, OCR ou un service externe.

Critere de sortie:
aucune voie d'upload auditee ne consomme sans borne le corps effectif; les
erreurs sont stables et les limites sont testees sur la taille reelle, pas
seulement sur l'en-tete client.

## Lot 10C - Suppression du contenu identity brut des logs

Finding cible: `P2-CEL-IDENTITY-RAW-LOG-01`.

Faits a revalider:

- `app/memory/memory_identity_write.py` journalise `content=%.60s` apres une
  ecriture identity;
- le contrat d'observabilite interdit le contenu brut et privilegie classes,
  compteurs et hashes bornes;
- aucun test ne garantit aujourd'hui l'absence de contenu dans `identity_saved`.

Perimetre strict:

- chemin d'ecriture identity et tests de logs standards uniquement;
- ce lot traite la fuite certaine `content=%.60s`, pas les 81 exceptions du
  Lot 10G;
- aucun nouveau stockage, champ admin ou collecte d'identite.

Checklist:

- [ ] Capturer le log actuel avec une sentinelle synthetique sans contenu reel.
- [ ] Remplacer le contenu par les metadonnees minimales deja utiles au
  diagnostic, strictement content-free.
- [ ] Verifier que la valeur conservee ne reintroduit ni texte identity, ni
  hash reidentifiant, ni identifiant utilisateur sensible.
- [ ] Ajouter une sentinelle qui echoue si le log standard contient la chaine
  synthetique, une URL ou un texte identity brut.
- [ ] Conserver l'information actionnable: statut/raison/classe selon le
  contrat, sans texte libre.

Critere de sortie:
une ecriture identity reussie reste observable sans qu'aucun fragment de son
contenu soit ecrit dans le logger standard.

## Lot 10D - Frontiere de succes apres persistence du chat

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

## Lot 10E - URL runtime commune du LLM principal

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

## Lot 10F - Prompts critiques fail-closed

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

## Lot 10G - Requalification contractuelle des exceptions brutes en logs

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
- ne pas absorber la fuite certaine identity du Lot 10C, deja independante.

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

## Lot 10H - Raccord de la complexite au Lot 9

Finding cible: `P3-CEL-COMPLEXITY-HOTSPOTS-01`.

Faits a revalider:

- les hotspots principaux sont `minimal_validation._check_ui_assets`,
  `runtime_settings_validation.validate_runtime_section`,
  `chat_llm_flow.run_llm_exchange`, `chat_service.chat_response`, les flows
  web search, `server.py` et plusieurs read-models;
- ce finding supersede l'ancien simple signalement de gros fichiers;
- une TODO Lot 9 existe deja et impose des golden tests avant toute extraction.

Perimetre strict:

- documentation et priorisation seulement dans ce Lot 10H;
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
  Lots 10A-10H sont tous resolus ou requalifies avec preuve.

## Preuve minimale par lot

Retour Celebrimbor attendu: plan alternatif evalue, finding valide/invalide,
perimetre reel, fichiers touches, tests executes et leurs resultats, effets de
bord cherches, statut `git diff --check`, statut Git, hash de commit et push.
Les artefacts et sorties restent content-free.
