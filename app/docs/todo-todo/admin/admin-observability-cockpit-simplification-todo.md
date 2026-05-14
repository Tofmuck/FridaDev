# Admin observability cockpit simplification - TODO

Statut: ouvert, actif
Source: audit read-only frontend/admin observabilite du 2026-05-14
Classement: `app/docs/todo-todo/admin/`
Portee: simplification des surfaces admin/frontend d'observabilite et consolidation cockpit operateur
Hors-scope: patch runtime dans ce commit, nouveau dashboard immediat, migration DB, backfill, redesign graphique global, modification plateforme OVH, exposition de secrets ou contenu brut

## 1. Intention

Ce TODO transforme l'audit read-only des surfaces frontend/admin d'observabilite en feuille de route executable.

Le probleme a traiter n'est pas un manque general d'observabilite: FridaDev possede deja des logs, read-models, snapshots et surfaces admin riches.

Le probleme est leur lisibilite operateur:

- `/log`, `/memory-admin`, `/hermeneutic-admin`, `/identity` et `/admin` racontent des morceaux du meme tour;
- les signaux de sante les plus utiles sont parfois enfouis dans des timelines, payloads generiques ou sections longues;
- certains details debug apparaissent trop tot;
- quelques projections admin content-free restent a durcir avant de construire un cockpit;
- les metriques backend les plus propres ne sont pas encore exposees comme lecture par conversation et par tour.

Objectif produit:

- transformer l'observabilite actuelle, riche mais eclatee, en un cockpit operateur simple, fiable, content-free, aligne avec le runtime et lisible d'un coup d'oeil;
- consolider l'existant au lieu de creer une cinquieme surface opaque;
- reduire le scroll inutile et les doublons de lecture;
- garder le langage visuel admin actuel autant que possible.

## 2. Emplacement retenu

Emplacement choisi: `app/docs/todo-todo/admin/admin-observability-cockpit-simplification-todo.md`.

Raison:

- le chantier n'est plus un audit mais une execution admin/frontend;
- les corrections touchent d'abord les surfaces admin, leurs read-models et leur lisibilite;
- `app/docs/todo-todo/audits/` resterait adapte a un plan de remediation issu d'un audit transversal non encore transforme en chantier produit;
- ici, l'objectif est deja nomme: simplifier et consolider les surfaces admin d'observabilite.

## 3. Sources de verite a relire avant patch

- `app/docs/states/specs/log-module-contract.md`
- `app/docs/states/specs/memory-admin-surface-contract.md`
- `app/docs/states/specs/identity-surface-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- `app/docs/todo-done/audits/full-turn-metrics-observability-todo.md`
- `app/docs/todo-done/memory/memory-rag-observability-remediation-todo.md`
- `app/docs/todo-done/audits/identity-observability-remediation-todo.md`
- `app/docs/todo-done/audits/hermeneutic-node-observability-remediation-todo.md`
- `app/web/log.html`
- `app/web/log/log.js`
- `app/web/memory-admin.html`
- `app/web/memory_admin/`
- `app/web/hermeneutic-admin.html`
- `app/web/hermeneutic_admin/`
- `app/web/identity.html`
- `app/web/identity/`
- `app/admin/`
- `app/observability/`
- `app/memory/memory_identity_read_model.py`

## 4. Principes de simplification

- Ne pas creer une cinquieme surface opaque.
- Ne pas dupliquer l'audit existant.
- Reutiliser les read-models, endpoints et snapshots existants avant d'en creer.
- Garder le design CSS actuel autant que possible.
- Augmenter la densite utile, pas la decoration.
- Ne pas afficher de contenu brut par defaut.
- Les details debug doivent etre replies ou explicitement demandes.
- Les courbes doivent etre construites seulement sur des metriques fiables et documentees.
- Le cockpit doit etre lisible par conversation et par tour.
- Le but est de reduire le scroll, pas d'ajouter des kilometres de panels.
- Les lots doivent rester petits, testables et reversibles.
- Les surfaces existantes ne doivent pas etre supprimees sans lot dedie et decision explicite.

## 5. Regles content-free

Autorise dans les vues de synthese:

- counts;
- statuts;
- booleens;
- durees;
- dimensions;
- timestamps;
- source kinds;
- provider callers;
- reason codes;
- error codes;
- error classes sanitisees;
- longueurs;
- hashes courts;
- IDs techniques seulement si deja non sensibles ou haches.

Interdit par defaut:

- contenu brut de conversation;
- prompt;
- messages;
- memory trace brute;
- summary brute;
- identity brute dans les couches legacy/diagnostic;
- query web brute;
- result snippet;
- canonical input dump;
- DSN;
- token;
- cle;
- traceback brut.

Exception bornee:

- les surfaces d'edition canonique identity peuvent continuer a afficher le contenu explicite qu'elles doivent editer;
- cette exception ne doit pas contaminer le cockpit, les couches legacy, les timelines ou les projections de synthese.

## 6. Condition de non-prolongation

Le chantier doit s'arreter des que ces conditions sont atteintes:

- les P1 content-free sont fermes;
- une lecture compacte par conversation/tour existe ou est exposee depuis les read-models actuels;
- `/log` donne une synthese cockpit minimale sans masquer la timeline brute;
- Memory Admin et Hermeneutic/Identity reduisent le scroll inutile et replient les details debug;
- les courbes retenues reposent uniquement sur des metriques fiables;
- aucun nouveau stockage, dashboard parallele ou redesign global n'a ete introduit sans decision separee.

Ne pas prolonger ce chantier pour:

- refaire tout `app/web/`;
- renommer les surfaces admin existantes;
- redessiner le systeme visuel;
- migrer les donnees;
- backfiller l'historique;
- reparer des bugs metier hors observabilite;
- transformer le cockpit en outil BI general.

## 7. Ordre de lots recommande

1. Lot 1: durcir content-free avant tout cockpit.
2. Lot 2: exposer ou consolider le read-model pipeline par tour.
3. Lot 3: enrichir `/log` avec une synthese cockpit compacte.
4. Lot 4: simplifier Memory Admin.
5. Lot 5: alleger Hermeneutic / Identity.
6. Lot 6: ajouter seulement les courbes utiles apres stabilisation.

Cet ordre est volontaire:

- commencer par la redaction evite de construire le cockpit sur des projections qui fuient du contenu;
- consolider le backend par tour evite de dupliquer la logique dans les renderers;
- enrichir `/log` avant de multiplier les pages garde la timeline brute comme source de debug;
- simplifier Memory puis Hermeneutic/Identity reduit le bruit domaine par domaine;
- les courbes arrivent seulement quand les signaux sont stables.

## Lot 1 - Durcir content-free avant tout cockpit

Objectif: fermer les deux P1 avant toute consolidation UI.

Findings couverts:

- Memory Admin expose encore `content_excerpt` dans les doublons notables.
- Identity read-model expose encore du legacy brut: `content`, `content_norm`, raisons brutes, conflits bruts.

Fichiers probablement touches:

- `app/admin/admin_memory_durable_dashboard.py`
- `app/web/memory_admin/render_overview.js`
- `app/memory/memory_identity_read_model.py`
- `app/admin/admin_identity_read_model_service.py`
- `app/web/identity/render_identity_runtime_representations.js`
- `app/web/hermeneutic_admin/render_identity_read_model.js`
- tests admin Memory / Identity si disponibles.

Hors-scope:

- ne pas supprimer les donnees durables existantes;
- ne pas modifier la doctrine identity;
- ne pas casser les surfaces d'edition canonique qui ont besoin de contenu explicite;
- ne pas ajouter une route de detail brut par commodite.

Cases de correction:

- [x] Remplacer `content_excerpt` dans les doublons Memory Admin par une projection compacte: role, occurrences, longueur, hash court, source, statut eventuel.
- [x] Verifier que `/api/admin/memory/dashboard` ne sert plus d'extrait de trace dans les vues chargees par defaut.
- [x] Remplacer les champs legacy identity bruts par longueurs, hashes courts, statuts, reason codes et counts.
- [x] Distinguer explicitement `legacy_diagnostic` / `evidence_only` des couches canoniques editables.
- [x] Garder les surfaces d'edition `static` / `mutable` intactes si elles ont besoin de contenu.
- [x] Renforcer les renderers frontend par projections allowlistees lorsque la source est une couche legacy.

Tests attendus:

- [x] Test API Memory Admin: absence de `content_excerpt` ou equivalent brut dans la reponse par defaut.
- [x] Test API Identity read-model: absence de `content`, `content_norm`, raisons libres et conflits bruts dans les couches legacy par defaut.
- [x] Test de presence des substituts compacts: longueur, hash court, statut, reason code, count.
- [x] Test frontend cible si les champs rendus changent.

Preuves runtime attendues:

- [x] lecture compacte des cles retournees, sans imprimer de valeurs brutes;
- [x] preuve que les vues restent exploitables avec seulement counts, statuts, longueurs et hashes courts.

Condition de cloture:

- [x] Le cockpit peut consommer Memory Admin et Identity legacy sans risque d'afficher du contenu brut par defaut.

## Lot 2 - Read-model pipeline par tour

Objectif: fournir une lecture backend compacte par conversation/tour, sans nouveau stockage si les logs suffisent.

Sources a reutiliser:

- `turn_observability_checklist`
- `full_turn_metrics_snapshot`
- `chat_log_events`
- `memory_chain_snapshot`

Fichiers probablement touches:

- `app/observability/log_store.py`
- `app/observability/turn_observability_checklist.py`
- `app/observability/full_turn_metrics_snapshot.py`
- `app/observability/memory_chain_snapshot.py`
- `app/server.py` ou routes admin dediees si une route est ajoutee;
- tests logs / observability / admin endpoint.

Hors-scope:

- pas de nouveau stockage si `observability.chat_log_events` suffit;
- pas de backfill;
- pas de migration DB;
- pas de duplication des snapshots existants;
- pas de logique UI complexe dans le backend.

Cases de correction:

- [x] Definir le JSON minimal d'un tour: statut global, conversation_id, turn_id, checklist, provider principal, providers secondaires, persistence assistant finale, RAG, Identity, Hermeneutic, Web, latences, erreurs/fallbacks.
- [x] Reutiliser `read_turn_observability_checklist()` plutot que recalculer en frontend.
- [x] Reutiliser `full_turn_metrics_snapshot` pour les agregats globaux.
- [x] Reutiliser `memory_chain_snapshot` pour la chaine `retrieved -> basket -> kept -> injected`.
- [x] Marquer explicitement `complete`, `degraded`, `partial`, `legacy_incomplete` ou vocabulaire local deja stabilise.
- [x] Exposer les truncations et limites de lecture.

Tests attendus:

- [x] Test read-model sur tour complet.
- [x] Test tour degrade ou legacy avec raison compacte.
- [x] Test content-free: pas de prompt, message, memory, identity ou web query brute.
- [x] Test sans `memory_chain_snapshot` pour compatibilite legacy.

Preuves runtime attendues:

- un appel local en lecture seule qui affiche seulement schema, counts, statuts et presence/absence des blocs.

Condition de cloture:

- [x] Un frontend peut afficher une ligne cockpit par tour sans relire ni interpreter toute la timeline brute.

## Lot 3 - Enrichir /log

Objectif: ajouter a `/log` un bandeau cockpit compact et une table de tours, en gardant la timeline brute comme detail repliable.

Fichiers probablement touches:

- `app/web/log.html`
- `app/web/log/log.js`
- `app/web/admin.css`
- endpoint/read-model du Lot 2 si cree;
- `/api/admin/logs/chat/metrics`;
- tests frontend/admin si disponibles.

Hors-scope:

- ne pas supprimer la timeline brute;
- ne pas redesigner `/log`;
- ne pas creer un nouveau dashboard separe;
- ne pas afficher les payloads complets en synthese.

Cases de correction:

- [x] Consommer `/api/admin/logs/chat/metrics` pour un bandeau compact.
- [x] Afficher la repartition `complete / degraded / partial / legacy`.
- [x] Afficher provider principal et providers secondaires sans les fusionner.
- [x] Afficher persistence assistant finale, interruptions et echecs de persistence.
- [x] Afficher erreurs/fallbacks par stage sous forme compacte.
- [x] Afficher les statuts RAG, Identity, Hermeneutic et Web par conversation/tour.
- [x] Ajouter une table de tours recents avec tri/filtre minimal.
- [x] Garder la timeline brute repliee ou secondaire, avec acces debug explicite.
- [ ] Remplacer les filtres stage statiques si possible par une liste derivee ou documenter leur limite.

Note: le filtre `stage` reste statique dans ce lot pour eviter d'ajouter une lecture metadata supplementaire; a reprendre seulement si un endpoint de stages derives est ajoute sans parser la timeline brute cote frontend.

Tests attendus:

- [x] Test JS ou rendu cible sur payload metrics minimal.
- [x] Test empty/error state.
- [x] Test qu'aucun payload brut n'est affiche dans le bandeau.
- [x] Test de non-regression de lecture timeline.

Preuves runtime attendues:

- capture compacte de `/log` ou appel local prouvant que le bandeau lit les metriques existantes;
- aucune preuve avec contenu brut.

Condition de cloture:

- [x] Depuis `/log`, un operateur sait en moins d'un ecran si les tours recents sont complets, degrades, partiels ou legacy, et peut ouvrir la timeline seulement si necessaire.

## Lot 4 - Simplifier Memory Admin

Objectif: garder Memory Admin comme surface domaine Memory/RAG, mais reduire le scroll et rendre les indicateurs de sante compacts.

Fichiers probablement touches:

- `app/web/memory-admin.html`
- `app/web/memory_admin/main.js`
- `app/web/memory_admin/render_overview.js`
- `app/web/memory_admin/render_turns.js`
- `app/admin/admin_memory_service.py`
- `app/admin/admin_memory_history_dashboard.py`
- `app/admin/admin_memory_durable_dashboard.py`
- `app/docs/states/specs/memory-admin-surface-contract.md` si le contrat change.

Hors-scope:

- ne pas changer retrieval, scoring, top-k ou arbitre;
- ne pas supprimer les logs;
- ne pas fusionner Memory Admin dans `/log`;
- ne pas ajouter de detail brut.

Cases de correction:

- [ ] Ajouter `memory_chain_snapshot` a l'inspection par tour.
- [ ] Afficher une sante embeddings compacte: count, dimension, couverture, erreurs, latest update, drift ou mismatch si disponible.
- [ ] Masquer par defaut les stages absents et sections vides.
- [ ] Deplacer les details debug en accordion.
- [ ] Reduire les panneaux longs sans perdre les counters utiles.
- [ ] Distinguer clairement `retrieved`, `basket`, `kept`, `rejected`, `injected`.
- [ ] Conserver les provenances `durable_persistence`, `calculated_aggregate`, `runtime_process_local`, `historical_logs`.

Tests attendus:

- [ ] Test renderer avec stage absent.
- [ ] Test renderer avec `memory_chain_snapshot`.
- [ ] Test API ou aggregation embeddings health si des champs backend sont ajoutes.
- [ ] Test content-free sur les nouveaux champs.

Preuves runtime attendues:

- lecture compacte d'un tour Memory/RAG avec chaine visible;
- preuve que les embeddings sont lisibles en indicateurs de sante sans dumps.

Condition de cloture:

- [ ] Memory Admin explique un tour RAG sans scroller dans des murs de payloads ni exposer le contenu des traces.

## Lot 5 - Alleger Hermeneutic / Identity

Objectif: separer ce qui releve du cockpit, du diagnostic detaille et de l'edition identity.

Fichiers probablement touches:

- `app/web/hermeneutic-admin.html`
- `app/web/hermeneutic_admin/main.js`
- `app/web/hermeneutic_admin/render.js`
- `app/web/hermeneutic_admin/render_identity_read_model.js`
- `app/web/identity.html`
- `app/web/identity/main.js`
- `app/web/identity/render_identity_runtime_representations.js`
- `app/admin/admin_identity_read_model_service.py`
- `app/admin/admin_identity_runtime_representations_service.py`
- `app/docs/states/specs/identity-surface-contract.md` si la repartition cockpit/diagnostic change.

Hors-scope:

- ne pas changer la doctrine identity;
- ne pas retirer l'edition canonique;
- ne pas masquer les etats critiques;
- ne pas transformer `/hermeneutic-admin` en simple clone de `/log`.

Cases de correction:

- [ ] Replier les details runtime longs par defaut.
- [ ] Eviter `refreshAll()` trop large lors d'une simple selection de tour.
- [ ] Ne pas recharger identity, governance, candidates ou corrections a chaque changement de tour si ces blocs ne dependent pas du tour selectionne.
- [ ] Renforcer la garde frontend content-free pour les payloads de stage.
- [ ] Clarifier les zones: cockpit, diagnostic, edition.
- [ ] Garder `/identity` comme pilotage compact et `/hermeneutic-admin` comme diagnostic detaille.
- [ ] Eviter les sections vides visibles par defaut.

Tests attendus:

- [ ] Test ou preuve JS que changement de tour ne recharge que les donnees necessaires.
- [ ] Test renderer de payload stage avec cles sensibles ou inconnues.
- [ ] Test empty/debug accordion.
- [ ] Test non-regression des formulaires d'edition canonique identity.

Preuves runtime attendues:

- appels reseau ou logs frontend compacts montrant un rechargement cible;
- aucune valeur identity brute dans les preuves.

Condition de cloture:

- [ ] Hermeneutic/Identity restent puissants pour diagnostiquer, mais ne noient plus le cockpit dans des details runtime permanents.

## Lot 6 - Courbes utiles uniquement apres stabilisation

Objectif: ajouter uniquement des courbes construites sur des metriques fiables et documentees.

Precondition:

- Lots 1 a 5 fermes ou explicitement declares non bloquants;
- metriques source documentees;
- signaux legacy ambigus exclus ou etiquetes.

Courbes autorisees:

- taux `complete / degraded / partial / legacy`;
- latences p50/p95 par stage/provider;
- RAG `retrieved -> basket -> kept -> injected`;
- web `requested / success / injected`;
- providers principal/secondaires;
- erreurs/skips par stage;
- embeddings health;
- persistence assistant finale.

Courbes interdites:

- signaux legacy ambigus non etiquetes;
- payload counts generiques sans semantique;
- heuristiques frontend non documentees;
- contenu brut ou labels derives de texte libre;
- graphes decoratifs sans decision operateur associee.

Fichiers probablement touches:

- `app/web/log.html`
- `app/web/log/log.js`
- `app/web/admin.css`
- read-model pipeline du Lot 2;
- docs de spec si une metrique devient contractuelle.

Cases de correction:

- [ ] Pour chaque courbe, nommer la source exacte.
- [ ] Pour chaque courbe, documenter la fenetre, le mode de troncature et la semantique.
- [ ] Preferer mini-courbes compactes ou tableaux tendances a des grands panneaux decoratifs.
- [ ] Garder une alternative tabulaire pour les counts importants.
- [ ] Ne pas ajouter de bibliotheque graphique lourde sans besoin confirme.

Tests attendus:

- [ ] Test transformation metriques -> serie.
- [ ] Test empty/truncated state.
- [ ] Test que les courbes ne rendent pas de labels issus de contenu brut.

Preuves runtime attendues:

- lecture compacte de series numeriques;
- capture ou preuve visuelle si un rendu frontend est ajoute.

Condition de cloture:

- [ ] Les courbes aident a decider quoi ouvrir/debugger; elles ne deviennent pas une nouvelle couche de bruit.

## 8. Hors-scope global du TODO

- Pas de patch runtime dans le commit de creation de ce TODO.
- Pas de nouveau dashboard maintenant.
- Pas de migration DB.
- Pas de backfill.
- Pas de redesign graphique global.
- Pas de modification plateforme OVH.
- Pas de secrets ni contenu brut.
- Pas de suppression de surfaces existantes.
- Pas de refactor opportuniste de `app/web/`.
- Pas de modification des prompts, providers, seuils Memory/RAG ou doctrine Identity.

## 9. Checks docs-only de creation

Pour le commit de creation de ce fichier:

```bash
git status --short
git diff --check
test -f app/docs/todo-todo/admin/admin-observability-cockpit-simplification-todo.md
grep -n "Lot 1" app/docs/todo-todo/admin/admin-observability-cockpit-simplification-todo.md
grep -n "Condition de non-prolongation" app/docs/todo-todo/admin/admin-observability-cockpit-simplification-todo.md
git diff --cached --check
```

Pas de rebuild runtime pour ce commit docs-only.

## 10. Criteres de cloture du chantier complet

- [ ] Les deux P1 content-free sont corriges et prouves.
- [ ] Le pipeline par tour est lisible par conversation/tour sans relecture manuelle de toute la timeline.
- [ ] `/log` affiche une synthese cockpit minimale.
- [ ] Memory Admin est plus compacte et couvre `memory_chain_snapshot`.
- [ ] Hermeneutic/Identity distinguent cockpit, diagnostic et edition.
- [ ] Les courbes ajoutees sont limitees aux signaux fiables.
- [ ] Les specs vivantes sont mises a jour seulement si un contrat runtime ou operateur change.
- [ ] Le chantier est archive dans `app/docs/todo-done/` avec preuves compactes.
