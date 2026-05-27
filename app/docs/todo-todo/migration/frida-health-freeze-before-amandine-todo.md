# Freeze sante Frida avant duplication Amandine

Statut: actif sur `migration`
Portee: audit applicatif FridaDev avant creation d'une instance Amandine separee
But: prouver que Frida est assez saine pour servir de base produit, avec DB neuve et `state/` propre, sans lancer la duplication dans ce chantier.

## Principe

Ce freeze ne cree pas Amandine. Il fige une decision: est-ce que l'instance Frida courante est une base saine pour dupliquer le produit, ou faut-il corriger des points bloquants avant de partir.

La duplication cible est:

```text
repository FridaDev sain
+ DB neuve
+ state propre
+ runtime settings reinitialises/seedes
-> instance Amandine separee
```

Le freeze doit distinguer:

- **Bloquant duplication**: empeche de lancer Amandine proprement.
- **A corriger avant duplication**: non bloquant immediat, mais risquerait de produire une instance confuse ou fragile.
- **Acceptable apres duplication**: P3 connu, documente, sans impact sur la base produit.

## Statut

- [ ] Actif sur `migration`.
- [ ] Aucun changement de plateforme effectue.
- [ ] Aucune purge DB / `state/` effectuee.
- [ ] Aucun secret, DSN complet, token, cookie ou `.env` affiche dans les preuves.
- [ ] Decision finale de freeze non encore prise.

## Hors-scope

- [ ] Ne pas creer la stack Amandine.
- [ ] Ne pas modifier Caddy, Authelia, Docker global, reseaux, secrets ou hostnames.
- [ ] Ne pas purger, copier ou migrer la DB live.
- [ ] Ne pas nettoyer `state/` live.
- [ ] Ne pas changer le modele runtime sans lot separe.
- [ ] Ne pas refactorer le code hors correction bloquante.
- [ ] Ne pas transformer le freeze en audit infini: tout finding doit etre classe P0/P1/P2/P3 et rattache a la duplication.

## Convention d'execution des tests

Chaque preuve doit dire explicitement quel environnement elle teste:

- [ ] **Working copy montee**: utiliser cette forme avant rebuild, pour tester exactement `/opt/platform/fridadev/app`:
  - `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest <suite>`
- [ ] **Conteneur live**: utiliser cette forme apres rebuild, pour tester l'image effectivement servie:
  - `docker exec platform-fridadev python -m unittest <suite>`
- [ ] Un test `docker exec platform-fridadev ...` n'est autoritatif sur un patch recent que si l'app a ete rebuildee depuis ce patch.
- [ ] Pour un patch docs-only, ne pas rebuild; les preuves sont alors `git diff --check`, greps, liens et relecture.

## Lot 0 - Inventaire et cartographie du freeze

- [x] Verifier branche, dernier commit, et clean worktree:
  - `git status --short --branch`
  - `git log --oneline -10`
- [x] Cartographier les surfaces runtime a valider:
  - chat principal;
  - prompt augmente;
  - identity static / mutable;
  - juge mutable v2 add-only;
  - memory / RAG;
  - summaries;
  - web search;
  - active documents;
  - admin;
  - logs / observabilite;
  - runtime settings;
  - backup / restore minimal.
- [x] Lister les specs source-of-truth a relire avant test:
  - `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`;
  - `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`;
  - `app/docs/states/specs/mutable-identity-judge-contract.md`;
  - `app/docs/states/specs/identity-read-model-contract.md`;
  - `app/docs/states/specs/admin-runtime-settings-schema.md`;
  - `app/docs/states/specs/active-conversation-documents-contract.md`;
  - `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md`;
  - `app/docs/states/specs/memory-admin-surface-contract.md`.
- [x] Definir le format de preuve content-free:
  - statuts;
  - counts;
  - model ids;
  - routes;
  - timestamps;
  - hashes courts si necessaire;
  - aucune conversation brute;
  - aucune mutable brute hors fixture synthetique.
- [x] Produire un tableau de findings avec colonnes:
  - id;
  - surface;
  - severite P0/P1/P2/P3;
  - duplication impact;
  - correction requise;
  - statut;
  - lien preuve.

### Tests/preuves Lot 0

- [x] `git status --short --branch`
- [x] `find app/docs/todo-todo app/docs/todo-done app/docs/states -maxdepth 3 -type f | sort`
- [x] `grep -RIn "TODO actif\\|chantier actif\\|migration\\|Amandine" app/docs README.md AGENTS.md || true`

### Critere de sortie Lot 0

- [x] Les surfaces a tester sont listees.
- [x] Les preuves attendues sont content-free.
- [x] Les severites P0/P1/P2/P3 sont definies.
- [x] Aucun test destructif n'est prevu.

### Photo operatoire Lot 0 - 2026-05-27

Etat git au demarrage du lot:

- branche: `migration`;
- upstream: `origin/migration`;
- dernier commit avant patch Lot 0: `d274d5a docs: clarify health freeze execution checks`;
- worktree: clean avant patch Lot 0.

Surfaces runtime a tester dans les lots suivants:

| Surface | Lots | Preuve attendue | Destructif |
| --- | --- | --- | --- |
| Chat principal / streaming / prompt augmente | Lot 1 | statuts routes, tests chat, smoke synthetique content-free | non |
| Identity static / mutable / juge mutable v2 add-only | Lot 2 | model id, module, contrat, counts, hashes courts, tests add-only | non |
| Memory / RAG / resumes | Lots 1-2 | counts, routes, status, tests existants, aucun contenu brut | non |
| Web search / documents actifs | Lot 1 | status, source regime, reason codes, non-contamination | non |
| Admin / read-model / runtime settings | Lots 1, 2, 4 | champs operateur, model ids, prompts, contrats | non |
| Logs / observabilite | Lots 1, 4 | events content-free, erreurs classees, aucun secret | non |
| DB / state / backup-restore minimal | Lot 3 | inventaire tables/fichiers, classification neuf/seed/legacy | lecture seule au freeze |
| Code / docs / TODO actifs | Lot 5 | greps classes, tests stale detectes, correction seulement si bloquante | non |

Specs source-of-truth relues ou verifiees:

| Spec | Statut Lot 0 |
| --- | --- |
| `app/docs/states/architecture/fridadev-current-runtime-pipeline.md` | presente |
| `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md` | presente |
| `app/docs/states/specs/mutable-identity-judge-contract.md` | presente |
| `app/docs/states/specs/identity-read-model-contract.md` | presente |
| `app/docs/states/specs/admin-runtime-settings-schema.md` | presente |
| `app/docs/states/specs/active-conversation-documents-contract.md` | presente |
| `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md` | presente |
| `app/docs/states/specs/memory-admin-surface-contract.md` | presente |

Format de preuve content-free retenu:

- autorise: statuts, counts, model ids, caller/module/contrat, routes, timestamps, reason codes, longueurs, hashes courts, exit codes;
- interdit: conversations brutes, mutables reelles brutes, prompts complets, documents utilisateur complets, secrets, cookies, DSN complets, `.env`;
- fixtures synthetiques autorisees si elles sont explicitement marquees comme telles et ne touchent pas la DB live.

Severites utilisables:

| Severite | Definition freeze |
| --- | --- |
| P0 | risque perte de donnees, fuite secret, corruption DB/state, ou duplication impossible immediatement |
| P1 | pipeline principal casse ou verite operateur fausse sur un mecanisme central avant duplication |
| P2 | incoherence serieuse a corriger avant duplication pour eviter une instance Amandine confuse ou fragile |
| P3 | confort, documentation, dette ou nettoyage acceptable apres duplication si explicitement accepte |

Findings Lot 0:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT0-NONE | Inventaire documentaire | none | aucun bloquant detecte au Lot 0 | aucune correction runtime | clos | specs presentes; grep actif/migration classe comme bruit documentaire attendu |

Risques evidents a surveiller dans les lots suivants:

- ne pas confondre working copy montee et conteneur live non rebuilde;
- ne jamais copier DB/state Frida/Tof vers Amandine par accident;
- verifier explicitement les docs actives qui parlent encore d'Amandine ou de chantiers produit ouverts;
- garder `identity_periodic_model` comme nom de compatibilite seulement, sans raconter l'ancien agent comme actif;
- ne pas convertir le freeze en refactor general: seuls les P0/P1/P2 bloquants doivent etre corriges avant decision.

Aucune action destructive prevue ou executee au Lot 0:

- pas de tests runtime;
- pas de smoke live;
- pas de rebuild;
- pas de lecture ou modification de secrets;
- pas de purge, copie, migration ou ecriture DB/state;
- pas d'action Caddy, Authelia, Docker global, reseaux ou hostnames.

## Lot 1 - Freeze fonctionnel runtime/live

- [ ] Verifier que l'app live est healthy:
  - `docker ps --filter name=platform-fridadev --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"`;
  - `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | grep -vi '^set-cookie:' | sed -n '1,12p'`.
- [ ] Verifier que les routes principales repondent selon leur contrat:
  - `/`;
  - `/admin`;
  - `/dashboard`;
  - `/log`;
  - `/memory-admin`;
  - `/hermeneutic-admin`;
  - `/identity`.
- [ ] Executer les tests runtime essentiels dans le conteneur:
  - tests chat flow;
  - tests admin settings read contract;
  - tests identity read-model;
  - tests mutable judge/apply;
  - tests active documents;
  - tests web search si disponibles sans provider externe.
- [ ] Smoke chat principal avec conversation synthetique non sensible:
  - verifier reponse streaming;
  - verifier absence d'erreur serveur;
  - verifier prompt augmente actif par observabilite content-free;
  - verifier absence de fuite `reasoning_details`.
- [ ] Smoke prompt augmente:
  - presence reference temporelle;
  - identity_input injecte quand attendu;
  - memory/RAG injecte seulement selon contrat;
  - active documents injectes seulement si attaches.
- [ ] Smoke summaries:
  - verifier qu'un resume existant est lu sans erreur;
  - verifier qu'aucun resume ne promet une memoire durable inexistante.
- [ ] Smoke web search:
  - web off => aucun appel externe;
  - URL explicite => lecture locale/controlee;
  - recherche ouverte => provider configure, observabilite content-free.
- [ ] Smoke active documents:
  - document texte synthetique;
  - image/PDF seulement si deja couvert par les tests;
  - verifier non-contamination Memory/RAG/Identity/Summary.
- [ ] Verifier absence d'erreurs runtime recentes bloquantes:
  - logs conteneur filtres par `ERROR|CRITICAL|Traceback`;
  - events applicatifs recents content-free;
  - ne pas afficher prompt complet, conversations, secrets.

### Tests/preuves Lot 1

- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_minimal_validation_phase4`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_minimal_validation_phase4`
- [ ] Smoke live note avec status, routes, model ids et absence d'erreurs.

### Critere de sortie Lot 1

- [ ] App live healthy.
- [ ] Chat principal OK.
- [ ] Admin OK.
- [ ] Web/documents/summaries ne presentent aucun P0/P1/P2.
- [ ] Les erreurs recentes sont classees ou absentes.

## Lot 2 - Freeze identity / memoire / mutable

- [ ] Verifier `identity_input` compile:
  - static user present si attendu;
  - static llm present si attendu;
  - mutable user present si attendu;
  - mutable llm present si attendu;
  - pas de legacy `identities` comme source active.
- [ ] Verifier la surface `/identity`:
  - elle raconte static + mutable comme canon actif;
  - elle distingue staging et canon;
  - elle ne promet pas une memoire durable au-dela du mecanisme existant.
- [ ] Verifier `/hermeneutic-admin` identity/read-model:
  - `mutable_judge_runtime.model = openai/gpt-5.2`;
  - `module = mutable_identity_judge_v2_add_only`;
  - `contract = mutable_judge_v2`;
  - `verdicts = add/no_change`;
  - `window_target_pairs = 5`.
- [ ] Verifier l'admin settings:
  - `identity_periodic_model.model = openai/gpt-5.2`;
  - `active_module = mutable_identity_judge_v2_add_only`;
  - prompt actif `prompts/identity_mutable_judge_v2.txt`;
  - l'ancien benchmark Haiku est visible seulement comme legacy.
- [ ] Smoke mutable add-only avec donnees synthetiques:
  - 5 paires completes;
  - au moins un add `llm`;
  - au moins un add `user`;
  - bruit ignore;
  - pas de `tighten`, `merge`, `clear_obsolete`, `target_ref`, `target_refs`;
  - audit content-free.
- [ ] Verifier que la 6e paire repart sur un buffer 1/5 si le test pipeline est rejoue.
- [ ] Verifier absence de score-first actif:
  - aucun appel actif `score_operation`;
  - aucun writer `apply_periodic_agent_contract`;
  - aucun scoring comme critere d'admission mutable.
- [ ] Verifier absence d'ecriture static automatique:
  - pas de promotion mutable -> static;
  - pas d'appel runtime a `write_static_identity_content`.
- [ ] Verifier Memory/RAG:
  - retrieval fonctionne;
  - admin memory raconte les sources et counts;
  - pas de confusion entre souvenirs, resume, identity, active documents.
- [ ] Verifier promesses de memoire dans les prompts/UI:
  - pas de promesse de memorisation si aucun mecanisme ne porte l'inscription;
  - mention claire des couches static/mutable/memory quand elles sont exposees.

### Tests/preuves Lot 2

- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.chat.test_mutable_identity_judge_final_validation`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.chat.test_mutable_identity_judge_final_validation`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_identity_phase4`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_identity_phase4`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Grep non-concurrence:
  - `grep -RIn "score_operation\\|apply_periodic_agent_contract\\|mutable_judge_v1\\|target_ref\\|target_refs\\|clear_obsolete\\|mutable_tightening\\|mutable_merge" app/core app/memory app/admin app/tests app/docs/states app/docs/todo-todo || true`

### Critere de sortie Lot 2

- [ ] Identity injectee coherente.
- [ ] Mutable add-only actif et visible.
- [ ] Aucun ancien regime mutable actif.
- [ ] Aucun P0/P1/P2 identity/memory ouvert.

## Lot 3 - Freeze DB / state / logs et preparation purge future

- [ ] Inventorier les tables DB contenant des donnees utilisateur ou etat runtime:
  - conversations;
  - messages;
  - memories;
  - summaries;
  - identity_mutables;
  - identity_mutable_audit;
  - identity_mutable_staging;
  - runtime_settings;
  - logs/events;
  - active documents;
  - documents uploades;
  - caches eventuels.
- [ ] Pour chaque table, classer pour Amandine:
  - seed propre requis;
  - vide au depart;
  - valeur runtime a reseeder;
  - archive Frida a ne pas copier;
  - backup obligatoire avant action.
- [ ] Inventorier `state/` sans afficher contenu sensible:
  - chemins;
  - tailles;
  - counts;
  - extensions;
  - timestamps;
  - pas de dump de fichiers.
- [ ] Identifier les fichiers `state/` a rendre neufs pour Amandine:
  - conversations;
  - logs;
  - uploads;
  - active documents;
  - identity state;
  - caches.
- [ ] Identifier les fichiers de config/code a conserver depuis le repo:
  - prompts;
  - specs;
  - assets;
  - migrations SQL;
  - seeds non secrets.
- [ ] Preparer la future checklist backup/purge, sans l'executer:
  - backup DB Frida;
  - backup `state/`;
  - preuve de restauration minimale;
  - commande de creation DB neuve;
  - commande de seed runtime settings;
  - verification post-purge.
- [ ] Verifier que les logs recents ne contiennent pas de secret ou contenu brut evident:
  - grep content-free sur noms de variables sensibles;
  - pas d'affichage des valeurs.

### Tests/preuves Lot 3

- [ ] Inventaire DB content-free via requetes `count(*)`, tailles et noms de table seulement.
- [ ] Inventaire `state/` par `find`, `du`, counts, extensions.
- [ ] Grep secret-safe:
  - noms de patterns seulement;
  - aucun affichage de valeur secrete.

### Critere de sortie Lot 3

- [ ] Liste DB/state a neuver pour Amandine complete.
- [ ] Plan backup/purge futur ecrit, non execute.
- [ ] Aucun secret expose.
- [ ] Aucun nettoyage live effectue.

## Lot 4 - Freeze admin / observabilite / verite operateur

- [ ] Verifier `/admin`:
  - modules modeles lisibles;
  - `identity_periodic_model` explique la compatibilite de nom;
  - modele juge mutable `openai/gpt-5.2` visible;
  - prompt/contract/caller visibles;
  - secrets masques.
- [ ] Verifier `/dashboard`:
  - pas de statut mensonger;
  - erreurs et activites recentes comprehensibles;
  - pas de contenu brut sensible hors surfaces prevues.
- [ ] Verifier `/log`:
  - filtres fonctionnels;
  - events `mutable_identity_judge` / `mutable_identity_judge_apply`;
  - pas de fenetre brute;
  - pas de prompt complet.
- [ ] Verifier `/memory-admin`:
  - counts et sources;
  - pas de confusion Memory/RAG/Identity;
  - pas de scoring legacy comme verite active.
- [ ] Verifier `/identity` et `/hermeneutic-admin`:
  - `mutable_judge_v2_add_only` raconte le regime actif;
  - `identity_mutable_staging` raconte la fenetre, pas le canon;
  - read-model ne montre pas `15` comme cible active si un ancien staging existe.
- [ ] Verifier runtime settings:
  - secrets read-only masques;
  - source/source_reason coherents;
  - bootstrap DB externe documente sans DSN.
- [ ] Verifier docs source-of-truth:
  - `app/docs/README.md`;
  - `AGENTS.md`;
  - specs actives;
  - catalogue modeles.

### Tests/preuves Lot 4

- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_settings_read_contract`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [ ] Greps operateur:
  - `grep -RIn "Haiku\\|identity_periodic_agent\\|score-first\\|promotion_to_static_enabled.*true" app/admin app/web app/docs/states app/docs/todo-todo || true`

### Critere de sortie Lot 4

- [ ] Admin raconte le systeme reel.
- [ ] Observabilite utile sans contenu brut.
- [ ] Aucun ancien regime presente comme actif.
- [ ] Secrets masques.

## Lot 5 - Cleanup cible uniquement si bloquant

- [ ] A partir des Lots 0-4, lister uniquement les cleanups qui menacent la duplication.
- [ ] Classer chaque cleanup:
  - bloquant duplication;
  - a corriger avant duplication;
  - peut attendre apres duplication.
- [ ] Chercher code mort dangereux:
  - anciens writers mutables;
  - appels legacy encore actifs;
  - tests stale qui valident un ancien contrat actif;
  - chemins hardcodes Frida/Tof/hostname;
  - dependances implicites a `/opt/platform/fridadev` ou au hostname public.
- [ ] Chercher TODO actifs contradictoires:
  - `app/docs/todo-todo/`;
  - mentions "actif" dans `todo-done/`;
  - doublons de source-of-truth.
- [ ] Verifier modules trop gros/ambigus seulement si cela menace la duplication:
  - pas de refactor esthetique;
  - pas de renommage global;
  - correction minimale et testee si bloquant.
- [ ] Ne corriger dans ce lot que les P0/P1/P2 confirmes.

### Tests/preuves Lot 5

- [ ] Grep hostnames publics:
  - `grep -RIn "fridadev.frida-system.fr\\|fridadev-db.frida-system.fr" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Grep chemins OVH / working copy:
  - `grep -RIn "/opt/platform/fridadev\\|/opt/platform/fridadev-app\\|/opt/platform/fridadev-db" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Grep traces utilisateur/personnelles hors fixtures attendues:
  - `grep -RIn "Tof\\|Amandine" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Inspection manuelle ciblee des identites/statics/prompts:
  - verifier `state/data/identity/`, `app/data/identity/` si present, `app/prompts/` et les docs source-of-truth sans lancer de grep global sur `Frida`;
  - garder `Frida` seulement pour des recherches ciblees par fichier ou section, car c'est le nom normal du produit.
- [ ] Grep legacy actif:
  - `grep -RIn "identity_periodic_agent\\|score_operation\\|apply_periodic_agent_contract\\|target_ref\\|clear_obsolete" app/core app/memory app/admin app/web app/tests || true`
- [ ] Tests cibles selon fichiers corriges.

### Critere de sortie Lot 5

- [ ] Aucun cleanup bloquant duplication ouvert.
- [ ] Les P3 acceptes sont listes.
- [ ] Aucun refactor opportuniste n'a ete lance.

## Lot 6 - Decision de freeze et note finale

- [ ] Rediger une note de validation finale dans `app/docs/todo-done/migrations/`.
- [ ] Inclure:
  - date;
  - branche;
  - commit;
  - tests executes;
  - smokes live;
  - inventaire DB/state;
  - P0/P1/P2 restants;
  - P3 acceptes;
  - decision GO / NO-GO.
- [ ] Si GO:
  - archiver cette TODO dans `app/docs/todo-done/migrations/`;
  - mettre a jour `app/docs/README.md`;
  - ouvrir le prochain plan Amandine uniquement apres decision explicite.
- [ ] Si NO-GO:
  - laisser cette TODO active;
  - ouvrir des micro-lots correctifs classes par severite;
  - ne pas commencer la duplication.

### Tests/preuves Lot 6

- [ ] `git status --short --branch`
- [ ] `git diff --check`
- [ ] Liens docs valides par grep.
- [ ] Note finale relue.

### Critere de sortie Lot 6

- [ ] Decision GO/NO-GO explicite.
- [ ] Preuves centralisees.
- [ ] Aucun P0/P1/P2 ouvert si GO.
- [ ] P3 restants acceptes explicitement.

## Criteres de sortie globaux

Frida est assez saine pour lancer la duplication Amandine si et seulement si:

- [ ] tests essentiels OK;
- [ ] live healthy;
- [ ] admin coherent;
- [ ] smoke chat OK;
- [ ] smoke identity mutable OK;
- [ ] smoke memory/RAG OK;
- [ ] smoke web/documents OK si la duplication Amandine doit utiliser ces capacites des le depart;
- [ ] runtime settings lisibles et secrets masques;
- [ ] modele juge mutable visible: `openai/gpt-5.2`;
- [ ] pipeline mutable actif visible: `mutable_identity_judge_v2_add_only`;
- [ ] aucun ancien regime mutable actif;
- [ ] aucune promotion mutable -> static automatique;
- [ ] inventaire DB/state pret;
- [ ] plan backup/purge futur pret, non execute;
- [ ] aucun P0/P1/P2 ouvert sur pipeline principal;
- [ ] P3 restants listes et acceptes.

## Risques

- Confondre freeze sante et duplication reelle.
- Nettoyer trop tot des donnees live sans backup.
- Copier des donnees Frida/Tof vers Amandine par accident.
- Laisser `identity_periodic_model` etre lu comme ancien agent periodic au lieu de slot de compatibilite du juge mutable.
- Rendre la surface admin rassurante alors que les smokes runtime n'ont pas ete faits.
- Exposer un secret dans une preuve trop bavarde.
- Transformer le freeze en refactor general et perdre le critere produit: base saine pour duplication.

## Definition de fini

- [ ] Les lots 0 a 6 sont coches ou explicitement classes non applicables.
- [ ] La note finale GO/NO-GO existe dans `app/docs/todo-done/migrations/`.
- [ ] Les index docs pointent vers la note finale ou vers cette TODO si elle reste ouverte.
- [ ] La duplication Amandine n'a pas commence dans ce chantier.
- [ ] La prochaine action est claire: corriger les bloquants, ou ouvrir le plan de duplication Amandine.
