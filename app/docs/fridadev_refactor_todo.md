# FridaDev Refactor TODO

## 1. Principes de pilotage
- Les sources historiques de type `todo` sont **explicitement exclues** du fond du plan: `app/docs/admin-todo.md`, `app/docs/todo-done/**`, `app/docs/todo-todo/**`.
- Source de vérité principale de ce plan: `app/docs/fridadev_repo_audit.md`.
- Chaque changement devra être **minimal, vérifiable, réversible** (pas de big-bang transversal).
- On traite d’abord les **contradictions de contrat** (interfaces et comportements), puis les refactos structurels.
- Un chantier = un objectif clair, une phase = un périmètre fermé.

## 2. Vue d’ensemble des phases
- **Phase 1 — Corriger les contradictions de contrat à faible risque**: stabiliser les contrats startup, API chat, provenance du modèle arbitre.
- **Phase 2 — Extraire le bootstrap runtime partagé**: supprimer la duplication du bootstrap DB/runtime.
- **Phase 3 — Scinder `runtime_settings.py`**: découper le module admin runtime en sous-modules cohérents.
- **Phase 4 — Extraire les services applicatifs de `server.py`**: réduire le monolithe HTTP/orchestration.
- **Phase 4 bis — Démonolithiser `chat_service.py`**: réduire le hotspot post-extraction sans changer le contrat HTTP.
- **Phase 5 — Découper `admin.js`**: isoler état/API/rendu/forms par section sans changer l’UI.
- **Phase 6 — Traiter les reliquats JSON / legacy / code mort**: purger les reliquats confirmés et gérer les zones incertaines.
- **Phase 7 — Reclasser les tests**: passer d’une nomenclature “phase historique” à une nomenclature métier.
- **Phase 8 — Harmoniser les conventions minimales**: converger sur des conventions légères et stables.
- **Phase 9 — Audit de clôture**: vérifier que chaque point majeur de l’audit initial est soldé, arbitré ou explicitement reporté.

## 3. Phases détaillées

### Phase 1 — Corriger les contradictions de contrat à faible risque
**Why**
- Éviter de refactorer sur une base contractuelle ambiguë.

**Scope**
- Contrat de démarrage runtime (`Dockerfile`, `run.sh`, `server.py`, `docker-compose.yml`).
- Contrat payload `/api/chat` (`history` frontend vs backend).
- Contrat de provenance du modèle arbitre persisté.

**Out of scope**
- Découpage modulaire large de `server.py`.
- Changement d’architecture frontend/admin.

**Risks**
- Régression de startup local/container.
- Régression d’observabilité si le champ `model` d’audit change de sémantique.

**Fichiers / zones concernés**
- `app/Dockerfile`
- `app/run.sh`
- `app/server.py`
- `docker-compose.yml`
- `app/web/app.js`
- `app/memory/memory_store.py`
- tests serveur/chat/admin associés

**Cases à cocher**
- [x] Valider et documenter le **contrat canonique de démarrage** (qui porte `host/port`, qui est source d’autorité).
- [x] Aligner le runtime sur ce contrat (sans changer le comportement fonctionnel externe).
- [x] Décider le contrat `history` de `/api/chat`: `supprimé` du frontend ou `consommé` côté backend.
- [x] Implémenter l’alignement `history` et ajouter tests de non-régression API.
- [x] Aligner la persistance `arbiter_decisions.model` avec la source runtime effective.
- [x] Ajouter/adapter tests ciblés sur ces 3 contrats.

**Definition of Done**
- Contrats startup/chat/arbiter explicités et cohérents dans le code.
- Aucun changement d’endpoint public.
- Tests ciblés + smoke passent.

---

### Phase 2 — Extraire le bootstrap runtime partagé
**Why**
- Supprimer la duplication de logique bootstrap DB/runtime, réduire les divergences futures.

**Scope**
- Extraction d’un module partagé pour:
  - résolution backend runtime DB,
  - fallback contrôlé,
  - bootstrap DSN.

**Out of scope**
- Refonte du modèle runtime settings.
- Refacto de l’UI/admin.

**Risks**
- Régression silencieuse sur fallback runtime.
- Couplage involontaire avec la logique de validation admin.

**Fichiers / zones concernés**
- `app/core/conv_store.py`
- `app/memory/memory_store.py`
- `app/minimal_validation.py`
- nouveau module partagé (à définir pendant exécution)
- tests unitaires de bootstrap

**Cases à cocher**
- [x] Créer un module partagé de bootstrap runtime DB (API minimale et testable).
- [x] Migrer `conv_store` vers ce module sans changer son API publique.
- [x] Migrer `memory_store` vers ce module sans changer son API publique.
- [x] Migrer `minimal_validation` vers ce module.
- [x] Ajouter tests unitaires du module partagé + tests de non-régression des trois appelants.

**Definition of Done**
- Une seule implémentation bootstrap runtime DB est utilisée par les 3 modules.
- Aucun changement de comportement observé sur fallback/erreurs attendues.

---

### Phase 3 — Scinder `runtime_settings.py`
**Why**
- Réduire le “god module” admin runtime (spec + DB + secrets + validation + readonly UI).

**Scope**
- Découpage interne en sous-modules, en conservant un point d’entrée stable.

**Out of scope**
- Changement de schéma SQL V1.
- Évolution fonctionnelle du périmètre admin.

**Risks**
- Rupture d’imports existants.
- Régressions sur seed/backfill/chiffrement.

**Fichiers / zones concernés**
- `app/admin/runtime_settings.py`
- `app/admin/runtime_secrets.py`
- `app/admin/sql/runtime_settings_v1.sql`
- `app/server.py`
- `app/tests/test_runtime_settings*.py`
- `app/tests/test_server_admin_settings_phase5.py`

**Cases à cocher**
- [x] Définir le plan de découpage interne: `spec/schema`, `repo DB`, `service runtime`, `validation`, `api_view`.
- [x] Extraire les `dataclass` et `SectionSpec/FieldSpec` dans un module dédié.
- [x] Extraire la couche accès DB/seed/backfill dans un module repository.
- [x] Extraire la validation runtime sectionnelle dans un module dédié.
- [x] Garder un point d’entrée compatibilité (`runtime_settings`) pendant transition.
- [x] Adapter les imports appelants + tests de non-régression.

**Definition of Done**
- `runtime_settings` n’est plus un module monolithique.
- API publique conservée ou migration explicitement documentée.
- Tests runtime settings/admin passent sans régression.

---

### Phase 4 — Extraire les services applicatifs de `server.py`
**Why**
- Réduire le couplage HTTP/métier et la complexité centrale de `server.py`.

**Scope**
- Extraction progressive des flux applicatifs:
  - chat orchestration,
  - conversations,
  - admin settings,
  - admin herméneutique.

**Out of scope**
- Changement du contrat HTTP externe.
- Changement UI.

**Risks**
- Régression de routes (codes HTTP, payloads, headers).
- Effets de bord sur logs et métriques.

**Fichiers / zones concernés**
- `app/server.py`
- nouveaux modules services/routes (à définir)
- `app/admin/*.py`, `app/core/*.py`, `app/memory/*.py`, `app/identity/identity.py`
- tests server phase/admin/chat

**Cases à cocher**
- [x] Extraire un service `chat` (pipeline complet) appelé par route Flask.
- [x] Extraire un service `conversations` (list/create/read/rename/delete soft).
- [x] Extraire un service `admin_settings` (GET/PATCH/VALIDATE).
- [x] Extraire un service `admin_hermeneutics` (dashboard, candidates, decisions, overrides).
- [x] Réduire `server.py` aux routes + composition + garde admin.
- [x] Vérifier strictement la stabilité des payloads/headers/codes via tests.

**Definition of Done**
- `server.py` n’est plus le lieu de l’orchestration métier complète.
- Comportement HTTP inchangé (contrats conservés).

---

### Phase 4 bis — Démonolithiser `chat_service.py`
**Why**
- Réduire le risque de recréer un nouveau monolithe métier après extraction hors `server.py`.
- Améliorer la maintenabilité pour un contributeur humain sur le pipeline chat.

**Scope**
- Découpage interne progressif de `app/core/chat_service.py` en sous-flux cohérents.
- Conservation d’une façade d’orchestration `chat_service.py` lisible et stable.
- Renforcement ciblé des tests service/HTTP autour des flux extraits.

**Out of scope**
- Refonte de design globale ou architecture “big-bang”.
- Refacto interne large de `memory_store`, `conv_store`, `arbiter`, `runtime_settings`, `llm`.
- Changement de contrat HTTP externe (`/api/chat`, payloads, headers, codes, erreurs).

**Risks**
- Faux refacto: déplacer du code sans réduire réellement la charge cognitive.
- Fragmentation artificielle en pseudo sous-modules fourre-tout.
- Régression subtile sur sync/stream, logs métier, ou persistance conversation.

**Fichiers / zones concernés**
- `app/core/chat_service.py`
- sous-modules adjacents éventuels sous `app/core/` (strictement si extraction utile et ciblée)
- `app/server.py` (façade route uniquement, ajustements minimaux)
- tests chat/service dans `app/tests/`

**Cases à cocher**
- [x] Cartographier explicitement les responsabilités internes de `chat_service.py`.
- [x] Extraire le flux conversation/session dans un sous-module ciblé.
- [x] Extraire le flux contexte/prompt (system + hermeneutical + temporalité + identité).
- [x] Extraire le flux mémoire/arbitrage (retrieve/filter/record/hints).
- [x] Extraire le flux appel LLM sync/stream (payload, erreurs, persistance, headers).
- [x] Garder `chat_service.py` comme façade d’orchestration lisible (point d’entrée stable).
- [x] Ajouter/adapter tests unitaires service + non-régression HTTP ciblés.

**Definition of Done**
- `chat_service.py` n’est plus un hotspot monolithique difficile à maintenir.
- Les sous-flux sont séparés sans créer de nouveaux fourre-tout.
- Contrat HTTP et comportement métier restent strictement inchangés, prouvés par tests.

---

### Phase 5 — Découper `admin.js`
**Why**
- Réduire la duplication et la surface de régression du frontend admin.

**Scope**
- Découpage modulaire sans changer le rendu ni les endpoints.

**Out of scope**
- Refonte UX/UI ou design system.
- Changement de modèle de données admin.

**Risks**
- Régression de wiring DOM/handlers.
- Régression de validation locale par section.

**Fichiers / zones concernés**
- `app/web/admin.js`
- `app/web/admin.html` (seulement pour le câblage de modules si nécessaire)
- `app/web/admin.css` (hors redesign)
- tests UI assets/minimal validation

**Cases à cocher**
- [x] Isoler un module `state` (draft/baseline/dirty/status).
- [x] Isoler un module `api` (fetch admin + token + gestion erreurs standard).
- [x] Isoler un module `ui_common` (render checks, readonly cards, field errors).
- [x] Isoler les formulaires de section (`main_model`, `arbiter`, `summary`, `embedding`, `database`, `services`, `resources`).
- [x] Centraliser la logique de mapping erreurs backend/locales.
- [x] Vérifier que le DOM final et les endpoints consommés restent inchangés.

**Definition of Done**
- `admin.js` est scindé en modules cohérents.
- Même UI, mêmes flux, mêmes routes.

---

### Phase 6 — Traiter les reliquats JSON / legacy / code mort
**Why**
- Réduire le bruit structurel et le risque de confusion entre strates.

**Scope**
- Traitement des éléments classés `certain/probable/à vérifier` dans l’audit.

**Out of scope**
- Suppression aveugle de fonctions potentiellement opératoires.
- Changement de politique de rétention sans décision explicite.

**Risks**
- Suppression d’un outil encore utilisé hors CI.
- Régression de migration/maintenance terrain.

**Fichiers / zones concernés**
- `app/core/conv_store.py`
- `app/web/app.js`
- `app/memory/summarizer.py`
- `app/tools/web_search.py`
- `app/run.sh`
- tests conv_store/chat/minimal validation

**Cases à cocher**
- [x] Supprimer les éléments `certain` sans valeur (`panel`, `MAX_CONTEXT_MESSAGES`, fonctions mortes confirmées).
- [x] Traiter `history` après arbitrage Phase 1.
- [x] Faire un inventaire d’usage réel des fonctions sync JSON avant suppression.
- [x] Statut final acté du sous-ensemble sync JSON: conservation documentée comme outillage opératoire explicite.
- [x] Décider le statut final de `run.sh` (conservé comme wrapper opératoire documenté).
- [x] Ajouter tests/guardrails pour éviter réintroduction de reliquats.

Arbitrage 2026-03-26: conserver le sous-ensemble sync JSON de `conv_store` comme outillage opératoire explicite (hors runtime principal), suppression non retenue à ce stade.
Arbitrage 2026-03-26: conserver `run.sh` comme wrapper opératoire local explicite, avec `server.py` comme entrée canonique runtime container.

**Definition of Done**
- Reliquats confirmés supprimés ou explicitement justifiés/documentés.
- Pas de suppression d’outils incertains sans preuve d’inutilité.

---

### Phase 7 — Reclasser les tests
**Why**
- Passer d’une logique “phase historique” à une logique métier lisible.

**Scope**
- Reclassement progressif des tests en domaines fonctionnels.

**Out of scope**
- Réécriture complète de tous les tests.
- Changement de framework de test.

**Risks**
- Perte de traçabilité historique des phases.
- Casse de découverte tests (paths/scripts CI).

**Fichiers / zones concernés**
- `app/tests/*`
- éventuelle structure `app/tests/unit|integration|smoke`
- `app/minimal_validation.py` (conservé comme smoke global)

**Cases à cocher**
- [ ] Définir la taxonomie cible: `unit`, `integration`, `smoke` + domaines (`chat`, `admin_settings`, `memory`, etc.).
- [ ] Migrer les tests par lots (sans big-bang), en conservant la couverture.
- [ ] Maintenir temporairement des wrappers/aliases si nécessaire pour compat exécution.
- [ ] Revoir les noms de tests les plus critiques pour exprimer le comportement métier.
- [ ] Conserver `app/minimal_validation.py` comme couche smoke globale.

**Definition of Done**
- Les tests critiques sont retrouvables par domaine.
- La chaîne d’exécution tests reste stable pendant la transition.

---

### Phase 8 — Harmoniser les conventions minimales
**Why**
- Réduire la friction de lecture/maintenance sans lancer un refacto esthétique.

**Scope**
- Conventions minimales partagées:
  - namespace logging,
  - style de typage,
  - nomenclature ciblée.

**Out of scope**
- Refonte stylistique massive.
- Guerre de préférences non structurantes.

**Risks**
- Diff volumineux sans gain métier si mal borné.
- Instabilité de blame git sur des fichiers sensibles.

**Fichiers / zones concernés**
- `app/server.py`, `app/core/*`, `app/memory/*`, `app/admin/*`, `app/tools/*`, `app/identity/*`
- tests impactés par renommage de conventions

**Cases à cocher**
- [ ] Valider un mini-guide de conventions (1 page max) appliqué au repo.
- [ ] Harmoniser progressivement les namespaces logger (`frida.*` vs `kiki.*`) selon décision d’arbitrage.
- [ ] Harmoniser le style de typage sur les modules touchés par les phases 1–7.
- [ ] Appliquer uniquement lors de modifications utiles (pas de commit “format global”).
- [ ] Ajouter une vérification légère (lint ou checklist PR) pour éviter la dérive.

**Definition of Done**
- Conventions minimales explicitement définies et appliquées sur les zones refactorées.
- Pas de patch massif hors périmètre fonctionnel.

---

### Phase 9 — Audit de clôture
**Why**
- Vérifier que les problèmes identifiés dans l’audit initial sont réellement soldés ou explicitement arbitrés.

**Scope**
- Relecture croisée entre le document d’audit initial et l’état final du repo après exécution des phases 1–8.
- Vérification de convergence entre architecture réelle et architecture cible annoncée.
- Vérification qu’aucun nouveau monolithe critique ou couplage majeur n’a été introduit pendant le refacto.

**Out of scope**
- Nouveau refacto structurel large.
- Reprise complète des phases précédentes.

**Risks**
- Déclarer le chantier “terminé” alors que certains points sont seulement déplacés.
- Oublier des questions ouvertes restées sans arbitrage.
- Conclure sur une cible théorique au lieu de l’état réel du repo.

**Fichiers / zones concernés**
- `app/docs/fridadev_repo_audit.md`
- `app/docs/fridadev_refactor_todo.md`
- éventuellement nouveau document de clôture: `app/docs/fridadev_refactor_closure.md`

**Cases à cocher**
- [ ] Vérifier que chaque point important de `fridadev_repo_audit.md` est soit corrigé, soit documenté, soit explicitement rejeté.
- [ ] Vérifier que toutes les questions ouvertes / points incertains ont reçu une décision explicite.
- [ ] Vérifier que les contradictions de contrat signalées dans l’audit sont fermées.
- [ ] Vérifier que les monolithes identifiés ont été réellement réduits ou requalifiés.
- [ ] Vérifier que les reliquats legacy / code mort signalés ont été traités ou justifiés.
- [ ] Vérifier que les dépendances inter-couches ont diminué et n’ont pas empiré.
- [ ] Vérifier qu’aucun nouveau “god module” n’a été créé pendant le refacto.
- [ ] Vérifier que l’architecture réelle converge suffisamment vers la cible annoncée en section 9 de `app/docs/fridadev_repo_audit.md`.
- [ ] Produire un document de clôture `app/docs/fridadev_refactor_closure.md` résumant les points soldés, les points arbitrés, les points restant ouverts et les écarts résiduels.
- [ ] Valider explicitement si l’audit initial peut être considéré comme “traité” ou seulement “traité partiellement”.

**Definition of Done**
- Une clôture écrite existe dans `docs/`.
- Le statut de chaque grand point de l’audit est explicite.
- Le chantier de refacto peut être déclaré terminé ou prolongé sur des résidus clairement nommés.

## 4. Dépendances entre phases

| Phase | Prérequis | Peut être menée en parallèle | Ne pas commencer trop tôt |
| --- | --- | --- | --- |
| Phase 1 | Aucun | Non (prioritaire) | Ne pas lancer Phases 3–6 avant clarification des contrats |
| Phase 2 | Phase 1 | Partiellement avec début Phase 5 | Ne pas lancer Phase 4 complète sans bootstrap partagé stable |
| Phase 3 | Phases 1–2 | Non | Ne pas re-scinder `runtime_settings` avant stabilisation bootstrap |
| Phase 4 | Phases 1–3 | Partiellement avec Phase 5 | Ne pas extraire massivement `server.py` avant contrats + runtime settings stables |
| Phase 4 bis | Phase 4 | Partiellement avec Phase 5 (write scopes distincts) | Ne pas découper `chat_service.py` avant fermeture de l’extraction hors `server.py` |
| Phase 5 | Phase 1 (minimum) | Oui avec Phase 4 (write scopes distincts) | Ne pas mélanger avec redesign UI |
| Phase 6 | Phases 1–4 | Partiellement avec Phase 7 | Ne pas supprimer legacy incertain avant inventaire d’usage |
| Phase 7 | Phases 1–6 (recommandé) | Oui avec fin Phase 8 | Ne pas déplacer massivement les tests avant stabilisation des modules |
| Phase 8 | Phase 1 (minimum) | Oui en continu, par petites touches | Ne pas faire une passe cosmétique globale en amont |
| Phase 9 | Phases 1–8 | Non (phase terminale) | Ne pas déclarer la convergence avant arbitrage explicite des points ouverts |

## 5. Ordre d’exécution recommandé
1. Stabiliser les contrats contradictoires (Phase 1).
2. Extraire la brique bootstrap runtime partagée (Phase 2).
3. Scinder `runtime_settings.py` sans changer le périmètre fonctionnel (Phase 3).
4. Extraire les services applicatifs hors `server.py` (Phase 4).
5. Démonolithiser `chat_service.py` sans changer le contrat HTTP (Phase 4 bis).
6. Découper `admin.js` en modules (Phase 5).
7. Nettoyer les reliquats legacy/code mort confirmés (Phase 6).
8. Reclasser les tests par domaine et niveau (Phase 7).
9. Finaliser l’harmonisation minimale des conventions (Phase 8).
10. Exécuter l’audit de clôture et publier le statut final de traitement de l’audit initial (Phase 9).

## 6. Points à arbitrer avant exécution
- Décision startup canonique: `run.sh` vs démarrage direct Docker/Flask (source d’autorité unique).
- Statut du champ `history` sur `/api/chat`: suppression ou consommation backend.
- Source canonique du modèle arbitre persisté (runtime DB vs config env).
- Sort des fonctions sync JSON dans `conv_store`: retrait complet vs maintien en outillage opératoire explicite.
- Politique cible de namespace logging (`frida.*` vs `kiki.*`).
- Politique `.gitignore` sur `app/docs/states/*` (conserver whitelist stricte ou ouvrir les états pérennes).
