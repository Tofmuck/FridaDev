# FridaDev — intégrité et continuité de la mémoire dialogique

Date de cadrage : 2 septembre 2026.

**Statut : roadmap ouverte ; I1, I2, M1, M2, O1 et B1 fermés et livrés ; B2
techniquement corrigé et livré, preuve produit encore en attente ; Z non
commencé.**

## 1. But et décision de périmètre

Préserver ce qui s'est réellement dit, ce qui a été corrigé et ce qui a été
effectivement conservé, afin que Frida puisse poursuivre un dialogue sans
prendre une panne pour une absence, une réponse interrompue pour une position
achevée ou une ancienne formulation pour la correction qui la remplace.

Tof a demandé cette roadmap dans `app/docs/todo-todo/refactors/`, et non dans
`product/`. C'est une consolidation de capacités existantes, pas un programme
d'ajout de features. Frida reste un système personnel de recherche sur le
langage, la mémoire et le dialogue, pas un système industriel multi-utilisateur.

Le présent GO autorise la création et la livraison Git de cette documentation,
pas l'exécution des corrections. Chaque lot ci-dessous sera confié séparément,
avec son périmètre et sa livraison explicites. Un lot ne lance pas le suivant.

**Source :** [audit de recherche du 2 septembre](../audits/fridadev-research-feature-audit-2026-09-02.md),
commit `49ed4b3cb1e8b7e2e03c1ac59db0e7dd3572d881`.
Les identifiants Fxx renvoient exclusivement à cet audit.

**Architecture retenue :** réparer les frontières des lecteurs, écritures,
sélections et projections existants ; réutiliser leurs orchestrateurs,
validateurs, tests et surfaces. Aucun nouveau pipeline, agent, écran, mécanisme
générique de reprise ou framework de campagne.

**Socle :** Python, stockage PostgreSQL existant, streaming SSE amont et terminal
Frida, read-models et renderers JavaScript existants. Les doubles de stockage
et transport restent des preuves hermétiques, jamais des preuves PostgreSQL live.

## 2. État de preuve au cadrage

Le contre-audit Codex a lu le rapport intégralement et vérifié les priorités
dans le HEAD indiqué. Il n'a pas réalisé un second audit exhaustif du dépôt.

| Finding | Preuve indépendante au cadrage | Limite |
| --- | --- | --- |
| F01 | Vrai lecteur SSE et coordinateur : erreur provider → terminal done, réponse non vide sauvegardée, six callbacks post-save factices ; exception réseau témoin → error, zéro callback | Aucun appel provider réel |
| F02 | Vrai reader et applicateur mutable : lecture en panne puis écriture disponible → ancien contenu absent du résultat écrit | Store de test ; aucune perte opérateur constatée |
| F03 | Vrai summarizer : échec save_summary → True et deux messages marqués summarized_by | Génération et stockage simulés ; originaux non supprimés |
| F04 | Vrai panier pré-arbitre : mardi puis jeudi → une ancienne formulation, jeudi absent du prompt | Un contre-exemple prouvé, pas une fréquence d'occurrence |
| F07 | Reader evidence avec subject=dialogue → total zéro avant toute connexion SQL | Ne prouve pas une absence d'injection des hints |
| F06 | Coupe, projection de section et rendu relus dans le code | Sonde agent-first du rapport non rejouée par Codex |
| F11 | Mécanisme et chemins documentés par l'auditeur initial | Reproduction indépendante exigée à l'ouverture de B2 |

Baseline documentaire : `main` propre, HEAD/upstream/distant alignés sur
`49ed4b3cb1e8b7e2e03c1ac59db0e7dd3572d881`, divergence `0/0`.
Image observée : `sha256:b059c08a8edecd5fffaa63d767c766f94bbcb8ba0e8b9c3c719b8a6216b66307` ;
StartedAt `2026-09-02T07:54:22.681500409Z`, healthy, restart 0, OOM false.
Ce sont des repères datés, pas des hashes que tous les lots futurs doivent
retrouver après les commits et livraisons précédents.

## 3. Ordre de travail et cases de suivi

La priorité fonctionnelle est Memory. I1 et I2 en protègent d'abord les entrées
et le canon ; M1/M2 traitent ensuite résumés et corrections. O1 porte uniquement
le compteur dialogique indépendant. Biblio vient après, en deux lots distincts.
L'observabilité d'un défaut corrigé dans I1/M1/B1 est corrigée dans ce même lot,
sans attendre O1.

| Ordre | Lot | Résultat attendu | Finding | Réflexion conseillée | Statut |
| --- | --- | --- | --- | --- | --- |
| 1 | I1 | Une erreur de streaming reste une interruption | F01 | xhigh | fermé et livré |
| 2 | I2 | Une lecture Identity en panne ne permet aucun remplacement | F02 | xhigh | fermé et livré |
| 3 | M1 | Un résumé n'est acquis qu'après stockage confirmé | F03 | xhigh | fermé et livré |
| 4 | M2 | La déduplication ne retire pas une formulation distincte avant jugement | F04 | xhigh | fermé et livré |
| 5 | O1 | Les hints dialogiques sont comptés par leur vrai reader | F07 | high | fermé et livré |
| 6 | B1 | Un extrait tronqué n'est jamais annoncé complet | F06 | xhigh | fermé et livré |
| 7 | B2 | Une reprise appartient au document réellement ouvert | F11 | high | corrigé/livré, preuve produit en attente |
| 8 | Z | Vérification finale limitée aux raccords modifiés | ci-dessus | high | non commencé |

- [x] Cadrage documentaire et limites de preuve consignés.
- [x] I1 fermé avec preuves et livraison convenues.
- [x] I2 fermé avec preuves et livraison convenues.
- [x] M1 fermé avec preuves et livraison convenues.
- [x] M2 fermé avec preuves et livraison convenues.
- [x] O1 fermé avec preuves et livraison convenues.
- [x] B1 fermé avec preuve agentique requise.
- [ ] B2 fermé avec preuve agentique requise.
- [ ] Z fermé ; roadmap archivée et liens actualisés.

## 4. Règles communes d'exécution

- Dans VS Code, utiliser directement le workspace exposé par l'IDE ; confirmer
  `pwd`, le toplevel Git et lire son `AGENTS.md`. Aucun SSH vers cette même
  machine et aucune dépendance aux fichiers du poste Codex Desktop.
- Lire seulement le lot, ses contrats vivants et ses chemins utiles. Revalider
  son finding dans le HEAD courant ; une correction déjà livrée est attestée,
  pas refaite. Une commande devenue obsolète s'adapte à périmètre équivalent.
- Avant patch, chercher le plan plus simple et ses effets de bord. Décider
  localement des détails d'implémentation compatibles ; demander une décision
  seulement si le comportement autorisé ou la frontière produit change.
- Reproduction rouge ciblée, correctif minimal, preuve verte au point réel de
  réception/écriture, puis voisins concernés. Ne pas compter seulement les
  appels, inventer un état final dans une fixture ou recopier l'algorithme testé.
- Réutiliser les tests existants. Pas de nouvelle cathédrale de goldens, de
  corpus ou de mutations : une sensibilité utile par invariant central suffit,
  complétée par les contre-cas légitimes. Aucun test n'est affaibli pour fermer.
- Tests hermétiques : checkout read-only, réseau désactivé, sans credentials,
  provider ni DB opérateur. Ne pas installer de dépendances pour cette roadmap.
  Les modules de test listés dans chaque lot se lancent via le runner unittest
  hermétique existant ; ils ne sont pas une commande de découverte globale.
- Faire évoluer ensemble événement, reader, API et renderer seulement lorsqu'un
  champ ou un état rendu change. Conserver les inspections privées intentionnelles
  identity/memory ; ne pas leur appliquer une suppression content-free générique.
  Retours, artefacts publics et surfaces content-free restent sans contenu brut
  ni secret, conformément à leurs contrats.
- Aucun changement de modèle, prompt, reasoning, provider, limite de tokens,
  seuil sémantique, budget produit ou schéma DB n'est présumé nécessaire.
  Toute nécessité démontrée hors périmètre est soumise à décision, pas ajoutée.
- Ne pas modifier les données opérateur, réparer rétroactivement les conversations,
  rejouer les fenêtres Identity ou lancer un backfill à la faveur d'un correctif.
- Chaque lot autorisé inclut sa documentation affectée, son auto-audit,
  `git diff --check`, commit et push sur la branche courante ; vérifier ensuite
  worktree propre, HEAD/upstream/distant égaux et divergence `0/0`.
- Le prompt d'exécution précise la livraison applicative. Un correctif runtime
  n'est dit live qu'après livraison ciblée et empreintes/health vérifiés. Un lot
  docs/tests-only ne provoque jamais de rebuild ou restart. Aucun service voisin.
- Retour à Tof : mécanisme corrigé, exemple synthétique compréhensible, preuves,
  limites et état live. Une suite verte ne prouve pas une qualité sémantique globale.

Stimmung reste constitutive ; `keep_current_v2.3`, Presence, les hard guards,
les final locks, les transports stricts et l'autorité des validateurs locaux
sont conservés. La précédente roadmap de consolidation reste archivée et fermée.

## 5. I1 — Ne pas canoniser une erreur SSE

**Objectif :** une réponse interrompue n'est ni une parole achevée ni une source
de dérivations Memory/Identity.

**Entrées et fichiers :** `app/core/chat_llm_provider_exchange.py`,
`app/core/chat_llm_flow.py`, `app/core/chat_assistant_finalization.py`,
`app/core/chat_stream_control.py` ; contrat
[streaming](../../states/specs/streaming-protocol.md).
Tests/support à réutiliser : `app/tests/support/server_chat_pipeline.py`,
`app/tests/unit/chat/test_chat_llm_flow.py`,
`app/tests/unit/chat/test_chat_llm_flow_boundaries.py`,
`app/tests/unit/chat/test_chat_stream_control.py`.

- [x] Reproduire une trame top-level error / finish_reason=error sous HTTP 200,
  avant tout texte puis après un fragment, avec le vrai reader et le coordinateur.
- [x] Raccorder l'erreur provider au chemin d'interruption existant ; ne pas créer
  une seconde machine de finalisation ni persister le détail brut du provider.
- [x] Prouver terminal error unique, aucun assistant partiel canonisé et aucune
  dérivation post-save ; message utilisateur et diagnostic borné conservés.
- [x] Préserver succès nominal, trames d'usage sans contenu, exception réseau,
  JSON non-stream et final locks. Vérifier le terminal reçu par le navigateur
  avec les tests frontend existants si son contrat est effectivement touché.
- [x] Mettre à jour uniquement les contrats/mentions devenus faux et livrer I1.

**Fermeture :** la trame provider en erreur ne peut plus produire done ni les
effets de succès ; le retour à l'ancien reader fait échouer la preuve.
Les autres fins non nominales rencontrées dans cette même frontière sont
qualifiées explicitement, sans réécrire tout le protocole.

### Preuves I1 avant livraison — 2 septembre 2026

- Reproduction rouge dans le vrai reader et le vrai coordinateur, via le support
  existant : erreur top-level avant contenu, `finish_reason="error"` après un
  fragment et forme unifiée après fragment produisaient toutes `done`.
- Correctif minimal : le reader lève la `RequestException` bornée déjà traitée
  par le coordinateur ; aucun payload ou message provider brut ne franchit le
  terminal, le marqueur persistant ou l'observabilité.
- L'auto-audit unique a reproduit deux fins voisines encore fail-open :
  `choices: []` levait hors du chemin d'interruption, tandis qu'un EOF sans
  `[DONE]` ou un événement `data:` non JSON pouvait encore valider un fragment.
  Les trois cas rejoignent désormais le même chemin borné ; `choices: []`
  reste nominal pour les trames metadata/usage valides.
- Preuve verte ciblée : 34 tests `unittest` couvrent le flux, ses frontières,
  le contrôle terminal et la normalisation assistant. Sont notamment conservés
  le succès avec trames metadata/usage à `choices` vide, l'exception réseau, le
  JSON non-stream, Presence/final locks, les échecs de sauvegarde et finalisation.
- Sensibilité : le retrait temporaire de la reconnaissance des deux marqueurs
  provider remet la preuve centrale en échec même lorsque `[DONE]` suit la
  trame fautive ; sa restauration la remet au vert.
- Qualification bornée : seul un objet `error` top-level ou
  `finish_reason="error"` rejoint `upstream_error`. Une trame vide, de metadata,
  d'usage ou portant une fin non-error n'est pas reclassée par I1. Un événement
  `data:` non JSON ou un EOF sans `[DONE]` rejoint aussi l'interruption, faute de
  preuve d'achèvement provider. Aucun contrat navigateur n'a changé ; aucune
  batterie frontend n'est donc requise.
- Environnement : image locale existante, conteneur jetable, checkout monté
  read-only, `--network none`, `/tmp` en tmpfs, sans provider, secret, DB
  opérateur ni donnée live. Aucun tour de dialogue réel n'a été lancé.

### Livraison I1 effective — 2 septembre 2026

- Commit applicatif `178dba1b39ca4f500645cc954a677d148e1e1741` poussé sur
  `main`, puis rebuild sans pull depuis la sous-stack applicative et recréation
  du seul service `fridadev` avec `--no-deps --force-recreate`.
- Nouvelle image `sha256:f7f0ec6c74e2671b8ec9c30021fa3bdfa25470b394fd0d2b6930b8611f4b919a` ;
  conteneur `platform-fridadev` démarré à
  `2026-09-02T16:57:12.19563561Z`, `running`, `healthy`, restart `0`, OOM `false`.
- Healthcheck autoritatif confirmé sur la route déclarée `/`, port interne
  `8089` : HTTP `200`. Aucun `/health` supposé, aucun appel modèle ou tour réel.
- Les SHA-256 des six fichiers I1 modifiés sont identiques entre checkout et
  conteneur. Les identifiants, images et statuts de tous les conteneurs voisins
  sont inchangés ; PostgreSQL, Caddy et les autres services n'ont pas été
  recréés ni redémarrés.

## 6. I2 — Distinguer canon absent et canon illisible

**Objectif :** préserver l'identité mutable existante quand sa lecture échoue.

**Entrées et fichiers :** `app/memory/memory_identity_mutables.py`,
`app/memory/mutable_identity_apply.py`, leurs façades dans `app/memory/memory_store.py`
et appelants mutateurs ; [contrat du juge mutable](../../states/specs/mutable-identity-judge-contract.md).
Tests : `app/tests/unit/memory/test_mutable_identity_apply.py`,
`app/tests/test_identity_mutables_phase1b.py`,
`app/tests/unit/memory/test_identity_liveness_lot1.py`,
`app/tests/unit/memory/test_identity_staging_lot2.py`.

- [x] Reproduire canon existant + lecture indisponible + écriture disponible,
  avec proposition admise par le véritable validateur add-only.
- [x] Fermer la frontière mutante : l'erreur de lecture n'est plus assimilée à
  une absence établie. Adapter ses consommateurs nécessaires, sans étendre une
  exception nouvelle à toutes les lectures admin supposées tolérantes.
- [x] Prouver zéro remplacement et zéro faux succès en cas de lecture en panne ;
  conserver la politique bornée d'échec/reprise et les fences existantes.
- [x] Prouver les contre-cas : absence réellement lue → création légitime ; canon
  présent → ajout conservant l'ancien ; no_change → aucune écriture ; erreur
  d'écriture → résultat non réussi. Préserver les éditions administrateur.
- [x] Vérifier audit et projection du résultat sans inventer une lecture réussie ;
  documenter et livrer I2.

**Fermeture :** panne de lecture démontrée et impossibilité de l'écrasement
consécutif. Aucun replay manuel du staging, migration ni nouveau protocole de
transaction distribuée. Le stockage factice n'est pas présenté comme une panne
PostgreSQL réelle.

### Preuves I2 avant livraison — 2 septembre 2026

- Les hypothèses I2/1 et I2/2 sont valides au HEAD I1 : le reader tolérant
  retournait `None` après une exception, puis l'applicateur préparait un batch
  depuis un faux canon vide.
  La reproduction traverse le cursor SQL factice, `memory_store`, le validateur
  add-only et l'applicateur ; lecture indisponible puis writer disponible
  produisaient `status=ok` et remplaçaient le canon synthétique antérieur.
- L'hypothèse I2/3 est valide : `get_mutable_identity(..., strict=True)` reste
  un opt-in local à l'applicateur. Les lecteurs admin/read-models conservent le
  défaut tolérant et les éditions administrateur `set/clear` gardent leurs
  writers actuels.
- L'hypothèse I2/4 est valide : `mutable_store_unavailable` appartenait déjà à
  `write_recovery`. L'application retourne désormais `skipped`,
  `writes_applied=false` et `failed_count=1` avant toute planification. Le
  coordinateur conserve la première fenêtre sous `write_recovery_pending`, puis
  la consomme sans écriture au second échec et conserve la paire courante comme
  début de la fenêtre suivante.
- Rouge observé : les deux preuves centrales recevaient `ok`; le store SQL
  factice remplaçait le canon `user` et pouvait créer le canon `llm` du même
  batch. Après correctif : ancien canon inchangé, aucun `INSERT`, aucun audit et
  aucune écriture sur l'autre sujet.
- Une mutation contrôlée remplaçant l'appel strict par le mode tolérant remet la
  preuve SQL centrale en échec avec `ok`; la protection restaurée la remet au
  vert.
- Batterie hermétique : 120 tests ciblés et voisins, `OK`, checkout read-only,
  réseau désactivé, sans secret, provider ni DB opérateur. Elle couvre absence,
  canon présent avec append exact, `no_change`, échec d'écriture, fences,
  concurrence, vivacité, projections, lectures tolérantes et éditions admin.
- Limite : le stockage factice prouve le chemin applicatif sous panne injectée ;
  aucune panne PostgreSQL live, donnée Identity opérateur ou perte historique
  n'a été recherchée ni constatée.

### Livraison I2 effective — 2 septembre 2026

- Commit code/tests/contrat `7e2b56b328db2d899c29c92947b6c969570fc214`
  poussé sur `main`, puis rebuild sans pull et recréation du seul service
  `fridadev` avec `--no-deps`.
- Image livrée :
  `sha256:e35334d13fc30824c47f397e6e60f48162024c715676eaae0c982bbcb72a0ed6` ;
  conteneur `ab48d39f34aa10c3b3d8883baf5a9f4ac96a4aac2efc85cd1848bbb193e52da3`,
  `StartedAt=2026-09-02T18:41:02.20706282Z`, running, healthy, restart `0`,
  OOM `false`.
- Le healthcheck déclaré sur `http://127.0.0.1:8089/` retourne `200` depuis le
  conteneur. Ce Compose ne publie pas ce port sur l'hôte ; aucune route
  `/health` n'a été inventée.
- Les SHA-256 de `memory_identity_mutables.py`, `memory_store.py` et
  `mutable_identity_apply.py` sont identiques entre checkout et conteneur. Les
  120 tests ciblés sont aussi verts directement dans l'image livrée, sans
  montage du checkout ni réseau.
- Les 31 conteneurs voisins conservent exactement leurs IDs, images et
  `StartedAt`; PostgreSQL, Caddy et les autres services n'ont pas été recréés.
- Le contre-audit indépendant ciblé ne rapporte aucun finding Critical,
  Important ou Minor. M1 et les lots suivants restent non commencés.

## 7. M1 — Acquérir un résumé seulement après stockage

**Objectif :** ne pas retirer des messages du prochain travail de résumé au nom
d'un résumé qui n'a pas été conservé.

**Entrées et fichiers :** `app/memory/memory_trace_summary_store.py`,
`app/memory/summarizer.py`, `app/memory/memory_store.py`,
`app/core/chat_service.py`, `app/core/conversations_prompt_window.py` ;
[contrat Summary](../../states/specs/memory-rag-summaries-lane-contract.md).
Tests : `app/tests/unit/memory/test_summarizer_phase4.py`,
`app/tests/unit/memory/test_memory_trace_summary_store_boundary.py` et support
chat/persistance existant.

- [x] Reproduire échec du stockage texte au vrai niveau qui absorbe actuellement
  l'erreur, puis suivre le booléen, les marques et l'événement côté coordinateur.
- [x] Faire remonter une issue de stockage non ambiguë ; conditionner l'acquisition
  et les marques à la conservation effective du résumé. Garder la génération,
  la persistance et le rattachement des traces comme opérations distinctes.
- [x] Sur échec texte, prouver absence de nouvelles marques/cutoff acquis et de
  summary_generated trompeur ; les messages restent disponibles au tour suivant.
- [x] Sur texte stocké mais embedding indisponible, conserver le résumé texte
  légitime. Sur échec du rattachement des traces, préserver le texte déjà stocké,
  qualifier honnêtement l'état et vérifier la cohérence du prochain tour sans
  rollback aveugle ni boucle de retries nouvellement ajoutée.
- [x] Prouver le chemin nominal après sauvegarde/réhydratation et préserver le
  diagnostic privé existant. Corriger le test qui exige True après échec sans
  retirer son assertion utile sur le diagnostic ; documenter et livrer M1.

**Fermeture :** les indicateurs d'acquisition correspondent au stockage effectif ;
aucune perte de disponibilité des messages du fait d'une écriture manquée. Le
lot ne crée ni résumé hiérarchique, ni nouvelle politique de sélection temporelle.

### Preuves M1 avant livraison — 2 septembre 2026

- F1, F2, F4 et F5 sont valides au HEAD I2. F3 est partielle : les marques
  excluent bien les messages du prochain travail, mais un premier échec texte
  ne crée pas à lui seul de cutoff SQL; ce cutoff vient d'un résumé actif
  effectivement relu.
- Rouge observé sur la vraie chaîne writer SQL factice → façade
  `memory_traces_summaries` → façade `memory_store` → résumeur : l'erreur
  absorbée laissait le chemin poursuivre sans diagnostic d'échec au résumeur.
- Le writer texte retourne désormais un booléen après commit; les deux façades
  le transmettent. `False` et `None` arrêtent rattachement, marques,
  `summarize_done`, sauvegarde conversationnelle de phase summary,
  `summary_generated` et état d'acquisition.
- Les variantes sans et avec résumé antérieur gardent toutes leurs marques
  initiales et ne produisent aucune ligne summary sous panne. Au passage
  suivant disponible, les messages sont encore éligibles et un stockage
  confirmé permet leur acquisition.
- Une panne d'embedding conserve le texte avec embedding nul; le vrai reader de
  résumé actif et le vrai builder de prompt relisent ce texte, remplacent la
  fenêtre couverte et gardent les tours récents. Une panne du rattachement des
  traces garde le texte et son diagnostic distinct, sans seconde génération au
  tour suivant.
- Une mutation contrôlée neutralisant la garde sur le résultat du writer remet
  en échec la preuve centrale, avec et sans résumé antérieur; la restauration
  la remet au vert.
- Batterie hermétique : 74 tests ciblés et voisins, `OK`, checkout read-only,
  réseau désactivé, sans secret, provider ni DB opérateur. Elle couvre aussi
  seuil non atteint, prompt absent, panne provider, persistance/réhydratation
  des marques, cutoff, injection et observabilité summary.
- Le contre-audit indépendant ciblé, après correction de ses deux retours sur
  les doubles `None` et la comparaison du conflit idempotent, ne rapporte plus
  aucun finding Critical, Important ou Minor.
- Limite : le double de connexion/SQL prouve le chemin applicatif sous panne
  injectée et écriture ensuite disponible; aucune panne PostgreSQL live, donnée
  opérateur, perte historique ou qualité sémantique globale n'a été recherchée
  ni constatée.

### Livraison M1 effective — 2 septembre 2026

- Commit code/tests/contrat
  `7ec484e0ebd4eb989ab34e03ae91ab224e420f5a` poussé sur `main`, puis
  rebuild sans pull et recréation du seul service `fridadev` avec
  `--no-deps --force-recreate`.
- Image livrée :
  `sha256:c489455303fd234866de25ea473d1e197b27dcea8b96135cf89d1c8010a79734` ;
  conteneur `b609192c45f3d3cfbd4831f42d1bf20efc04e1e6dee22a40e065e74edd441aff`,
  `StartedAt=2026-09-02T19:30:58.05151292Z`, running, healthy, restart `0`,
  OOM `false`.
- Le healthcheck déclaré sur `http://127.0.0.1:8089/` retourne `200` depuis
  le conteneur; aucune route `/health` ni appel modèle n'a été utilisé.
- Les SHA-256 des quatre fichiers runtime M1 modifiés sont identiques entre
  checkout et conteneur. Les 74 tests ciblés sont verts dans l'image livrée,
  sans montage du checkout ni réseau.
- Les 31 conteneurs voisins conservent exactement leurs IDs, images et
  `StartedAt`; PostgreSQL, Caddy et les autres services n'ont pas été recréés.
- L'image précédente
  `sha256:e35334d13fc30824c47f397e6e60f48162024c715676eaae0c982bbcb72a0ed6`
  est restée disponible comme référence de retour applicatif ciblé. M2 et les
  lots suivants restent non commencés.

## 8. M2 — Préserver les variantes avant le jugement Memory

**Objectif :** le jugement reçoit les différences de formulation utiles au
dialogue ; le prétraitement ne décide pas à sa place qu'elles sont équivalentes.

**Entrées et fichiers :** `app/memory/memory_pre_arbiter_basket.py`,
`app/core/chat_memory_flow.py`, leurs constructeurs d'inputs et appelants arbitre ;
[contrat du panier](../../states/specs/memory-rag-pre-arbiter-basket-contract.md).
Test principal : `app/tests/unit/memory/test_memory_pre_arbiter_basket_phase7b.py`.

- [x] Reproduire mardi/jeudi : ancienne trace mieux classée, nouvelle plus récente ;
  observer le contenu transmis à l'arbitre, pas seulement les IDs fusionnés.
- [x] Retirer ou restreindre la fusion lexicale qui efface un texte distinct.
  Préférer la conservation des formulations à un détecteur de correction ; les
  égalités réellement sûres gardent leur déduplication et leur provenance.
- [x] Prouver que date, quantité et négation différentes restent distinctes dans
  des candidats admis sous le budget, et que deux contenus strictement identiques
  ne sont pas inutilement dupliqués. Tester les vrais constructeurs jusqu'au prompt.
- [x] Maintenir les plafonds de candidats/tokens et le classement existants ; une
  éviction par budget reste une sélection bornée, jamais une fausse équivalence.
- [x] Vérifier compteurs/raisons de déduplication réellement affectés, documenter
  et livrer M2 sans modifier modèle, prompt arbitre, embeddings ou reranker.

**Fermeture :** la variation n'est plus détruite par la déduplication avant le
jugement. Ne pas prétendre que le modèle choisira toujours la bonne correction :
ce lot prouve l'accès à la matière, pas son efficacité sémantique universelle.
Aucune regex sémantique, nouvelle taxonomie ou campagne de modèles.

### Preuves M2 avant livraison — 3 septembre 2026

- F1, F2 et F4 sont valides. F3 est valide pour l'égalité issue d'une
  normalisation destructive, `same_conversation_same_idea`,
  `lexical_near_duplicate` et leurs regroupements transitifs. F5 est partielle:
  davantage de formulations peuvent entrer dans le classement, mais la coupe
  existante à huit reste inchangée et ne garantit aucun rappel universel.
- Le rouge canonique construit `memory_retrieved`, le vrai panier et appelle
  `filter_traces_with_diagnostics()` avec un transport factice. Avec l'ancienne
  fusion, le message arbitre ne contenait que la trace mieux classée « mardi »;
  le texte « jeudi », son ID et son repère temporel avaient disparu.
- La déduplication textuelle compare désormais le `content` strict. Les deux
  heuristiques sémantiques locales sont retirées; date/jour, quantité, négation,
  ponctuation et extension textuelle restent séparés sous budget. `dedup_key`
  garde un slug lisible mais son digest dépend du texte strict.
- Les contenus strictement identiques gardent un représentant choisi par
  `_representative_rank`, tous leurs `source_candidate_ids` et leur liaison aux
  décisions/injections. La relation structurelle trace/summary, sa couverture,
  `parent_summary`, les modes shadow/enforced et la sélection après décision
  restent inchangés.
- La limite reste huit après déduplication/fusion structurelle et le classement
  reste identique. Un candidat hors limite n'est ni absorbé dans une provenance
  ni déclaré doublon.
- Une mutation contrôlée réintroduisant le rapprochement lexical remet la
  preuve du message mardi/jeudi en échec; sa restauration la remet au vert.
- Batterie hermétique ciblée : 61 tests, `OK`, checkout read-only, réseau
  désactivé, temporaires isolés, sans secret, provider ni DB opérateur. Le
  transport HTTP arbitre est remplacé au bord exact où ses messages sont
  capturés; aucun POST externe n'est émis.
- Le contre-audit local ne trouve ni seconde fusion textuelle pré-arbitre, ni
  perte de provenance, ni contournement de limite, ni ancien helper empilé. La
  similarité lexicale aval contre le contexte récent s'exécute après le jugement
  et ne recrée pas F04. La projection admin n'annonce plus les deux raisons de
  fusion retirées comme contrat actif; les artefacts historiques restent lisibles.
- Limite : le retrieval, le classement et la coupe à huit peuvent encore ne pas
  sélectionner une formulation. M2 prouve que les formulations admises peuvent
  être lues et jugées séparément, pas que l'arbitre choisira toujours la bonne.

### Livraison M2 effective — 3 septembre 2026

- Commit code/tests/contrats
  `6dd346c0614e5ca78dd09cff57c78440cc65405e` poussé sur `main`, puis
  rebuild sans pull et recréation du seul service `fridadev` avec
  `--no-deps --force-recreate`.
- Image livrée :
  `sha256:847d05eb84c3d544bcd13e15327ddd2c51e505ebdc160e6a36cc6f82aa9ae67b` ;
  conteneur `4ae0300f1bf978bdeb095d068208af095c5ac94d7557eebf35c87ff5a4859b5a`,
  `StartedAt=2026-09-03T09:33:43.004995607Z`, running, healthy, restart `0`,
  OOM `false`.
- Le healthcheck déclaré sur `http://127.0.0.1:8089/` retourne `200` depuis
  le conteneur; aucune route `/health` ni appel modèle n'a été utilisé.
- Les SHA-256 des deux fichiers runtime M2 modifiés sont identiques entre
  checkout et conteneur. Les 61 tests ciblés sont aussi verts depuis l'image
  livrée, sans montage du checkout ni réseau.
- Les 31 conteneurs voisins conservent exactement leurs IDs, images et
  `StartedAt`; PostgreSQL, Caddy et les autres services n'ont pas été recréés.
- L'image précédente
  `sha256:c489455303fd234866de25ea473d1e197b27dcea8b96135cf89d1c8010a79734`
  reste disponible comme référence de retour applicatif ciblé. O1 et les lots
  suivants restent non commencés.

## 9. O1 — Rendre le compteur des hints dialogiques fidèle

**Objectif :** les repères du dialogue ne sont pas affichés absents parce que le
reader administratif refuse leur catégorie.

**Entrées et fichiers :** `app/memory/memory_identity_write.py`,
`app/memory/memory_identity_read_model.py`,
`app/admin/admin_identity_read_model_service.py`,
`app/admin/admin_identity_runtime_representations_service.py`,
`app/admin/admin_identity_read_model_projection.py` ;
[contrat Identity read-model](../../states/specs/identity-read-model-contract.md).
Tests : `app/tests/unit/memory/test_identity_read_model_phase2.py`,
`app/tests/test_server_admin_identity_read_model_phase2.py`,
`app/tests/unit/identity/test_identity_read_model_projection_boundary.py`.

- [x] Reproduire dialogue → zéro avant SQL, puis composer le vrai writer,
  reader et read-model avec un stockage factice de lignes.
- [x] Admettre dialogue uniquement dans le reader d'evidence concerné ; ne pas
  élargir l'allowlist commune des identities, conflits ou canons user/llm.
- [x] Prouver N evidences dialogue → N réellement stockées dans la projection,
  absence légitime → zéro, historique user/llm conservé, filtres/limites inchangés.
- [x] Suivre cette donnée jusqu'aux renderers existants ; ne pas confondre compteur
  stocké, sélection pour injection et dernière activité. Modifier l'UI seulement
  si nécessaire à la fidélité du contrat, sans écran ni collecte supplémentaire.
- [x] Documenter et livrer O1 ; aucun retrait ni changement sémantique des hints.

**Fermeture :** le compteur rend la catégorie réellement écrite et n'affirme pas
une absence d'injection depuis un simple zéro administratif.

### Preuves O1 avant livraison — 3 septembre 2026

- F1, F2, F3 et F4 sont valides. Le writer et les deux services admin utilisent
  bien `dialogue`; seul le reader d'evidence refusait ce sujet. La garde commune
  reste inchangée pour les fragments et conflits. Les projections/renderers
  consommaient déjà `total_count`; les anciennes fixtures injectaient directement
  un snapshot correct et ne pouvaient donc pas détecter la rupture writer-reader.
- La reproduction initiale avec connexion sentinelle rendait
  `total_count=0` sans ouvrir la connexion. La preuve composée fait passer trois
  hints synthétiques par le vrai writer, les façades `memory_store`, le vrai
  reader et les deux services admin sur un stockage factice qui conserve les
  paramètres des `INSERT` puis calcule ses lectures par sujet.
- Avec `limit=2`, le read-model rend `total_count=3`, deux items minimisés et
  `stored=true`; la représentation runtime rend le même total avec sa limite
  existante de 20. Une evidence `user` et une `llm` restent lisibles chacune et
  ne rejoignent pas le total `dialogue`.
- Un sujet evidence invalide, ainsi que fragments et conflits `dialogue`, sont
  toujours refusés avant SQL. Une table dialogue vide rend légitimement zéro.
  Les requêtes paramétrées, l'ordre, les limites et la minimisation restent
  inchangés; aucun contenu brut synthétique ne traverse les projections.
- La fixture issue du vrai builder sépare `stockes=3`, activité
  `persistes=2` et sélection `max_items=2`. Le test Chromium ciblé confirme ce
  rendu sur `/identity` et `/hermeneutic-admin`, sans modification frontend.
- Une mutation remettant le refus commun dans le reader fait échouer la preuve
  composée avec `0 != 3`; le correctif restauré la remet au vert.
- Batterie hermétique ciblée : 37 tests Python et un test Chromium, tous verts,
  checkout read-only, réseau désactivé, temporaires isolés, sans installation,
  provider, secret ni DB opérateur.
- Le contre-audit local ne trouve ni admission de `dialogue` dans le canon, les
  fragments ou les conflits, ni total dérivé de la page limitée, ni renderer
  raccordé au mauvais compteur, ni second reader empilé.
- Limite : ce stockage factice n'est pas une preuve PostgreSQL live. Le compteur
  stocké ne garantit ni la sélection future d'un hint, ni son injection, et la
  gestion générale des erreurs de lecture reste inchangée.

### Livraison O1 effective — 3 septembre 2026

- Commit code/tests/contrats
  `035c286cc5f9abe531747f5e35e50efb9cf8fb69` poussé sur `main`, puis rebuild
  sans pull et recréation du seul service `fridadev` avec
  `--no-deps --force-recreate`.
- Image livrée :
  `sha256:82605c7ed2c4806024f6e489a6dd1b7749a76725108a54f6f7d34a78fc620f8b` ;
  conteneur `5c3f897ae4c6455732c9fd4f0d79abba9c080eff17abb1fa142535283fc4a97c`,
  `StartedAt=2026-09-03T10:04:06.672384901Z`, running, healthy, restart `0`,
  OOM `false`.
- Le healthcheck déclaré sur `http://127.0.0.1:8089/` et le GET interne
  retournent `200`. Le SHA-256 du reader modifié est identique entre checkout
  et conteneur.
- Les 37 tests Python ciblés sont verts depuis l'image livrée, sans montage du
  checkout ni réseau. Le smoke Chromium ciblé avait vérifié les deux renderers
  hermétiquement avant le build; aucun appel modèle ou donnée opérateur n'a été
  utilisé.
- Les 31 conteneurs voisins conservent exactement leurs IDs, images et
  `StartedAt`; PostgreSQL, Caddy et les autres services n'ont pas été recréés.
- L'image précédente
  `sha256:847d05eb84c3d544bcd13e15327ddd2c51e505ebdc160e6a36cc6f82aa9ae67b`
  reste disponible comme référence de retour applicatif ciblé. B1 et les lots
  suivants restent non commencés.

## 10. B1 — Distinguer section complète et fragment borné

**Objectif :** une lecture partielle ne devient pas une preuve d'intégralité.

**Entrées et fichiers :** `app/biblio/librarian_tools.py`,
`app/biblio/answer_extraction.py`, `app/biblio/answer_surface.py`, raccords de
reprise et final lock ; [contrat Biblio native](../../states/specs/frida-biblio-native-catalogue-contract.md)
et [contrat bibliothécaire](../../states/specs/frida-biblio-librarian-agent-contract.md).
Tests : `app/tests/unit/biblio/test_librarian_tools.py`,
`app/tests/unit/biblio/test_librarian_agent_first.py`,
`app/tests/unit/biblio/test_librarian_method_boundaries.py`.

- [x] Rejouer la section d'une page dont le texte dépasse la borne actuelle,
  par le vrai chemin agent-first avec client Catalogue factice.
- [x] Propager l'incomplétude dans l'objet-réponse, le rendu et les conditions de
  lock ; un hash de fragment n'est pas une preuve de section complète.
- [x] Conserver une reprise honnête sur la matière non lue, avec les mécanismes
  existants ; ne pas avancer au-delà de la coupe ni inventer une nouvelle ancre.
- [x] Préserver page courte complète, sections multi-pages et extraction canonique
  segmentée déjà correcte. Ne pas relever globalement les plafonds.
- [x] Livrer la correction puis la preuve agentique bornée convenue ci-dessous,
  mettre à jour contrat/observabilité affectés et fermer B1 seulement avec celle-ci.

**Fermeture :** aucun « complet » trompeur ; le reste non lu reste identifiable.
Le bibliothécaire LLM est conservé, pas remplacé par des règles de lecture.

### Preuves B1 avant livraison — 3 septembre 2026

- Hypothèses: H1 à H5 sont valides. `_page_text()` coupe après normalisation à
  2 500 caractères; l'ancienne comparaison avec le texte décoré manquait une
  petite coupe et confondait retrait d'espaces et troncature; le booléen était
  perdu avant l'objet-réponse; la projection assimilait couverture des pages et
  réception intégrale; rendu, lock et reprise ne partageaient donc pas la même
  vérité structurée.
- Reproduction rouge par le vrai builder agent-first et un Catalogue factice:
  une section d'une page contenant 4 000 caractères était bornée mais projetée
  `section_complete`, rendue « Section complete. » et mémorisée sans reste.
- Correctif minimal: la décision de coupe est capturée avant ajout du marqueur,
  propagée comme `page_truncated`/`incomplete_pages`, puis projetée en segment
  exact. Le rendu annonce la réception partielle et le final lock reste autorisé
  pour l'extrait exact reçu.
- L'outil page n'expose aucun offset. Une coupe intra-page porte donc
  `incomplete_page_no` sans fausse ancre suivante; une reprise qui sauterait à
  la page suivante est refusée avant GET et rejoint la clarification existante.
  Un segment dû au seul budget de pages conserve, lui, son vrai `next_page_no`.
- Tests hermétiques ciblés: `354` tests verts avec réseau coupé, checkout en
  lecture seule et `/tmp` isolé. Ils couvrent 2 500 caractères, dépassement d'un
  caractère, espaces terminaux, pages courtes et multi-pages complètes, coupe
  multi-page, budget de pages, sérialisation/réhydratation, véritable prochain
  GET, extraction canonique et observabilité content-free.
- Sensibilité: remettre temporairement la projection de page coupée dans le
  chemin de complétude fait échouer la preuve centrale sur `section_complete`;
  le code a été immédiatement restauré et la preuve est redevenue verte.
- Contre-audit local unique: deux chemins de saut voisins ont été trouvés et
  fermés. « Page suivante » rejoint la clarification lorsqu'une page reste
  incomplète, et le planner interrompt aussi les `page_read` déjà fournis par le
  plan agent après la première coupe; le compléteur ne les reprend pas ensuite.
  Les ranges canoniques restent distincts. Le runner live expose seulement les
  statuts, bornes, compteurs, hashes et décision de lock nécessaires; aucun
  texte, prompt ou payload provider n'est sérialisé.

À cette étape pré-livraison, B1 restait ouvert: la livraison ciblée et la preuve
agentique live content-free autorisée ci-dessous devaient encore être acquises.

### Livraison B1 et preuve agentique bornée — 3 septembre 2026

- Le commit code/tests/contrats `2a063d27e3641eb4c1f78443761ed18f3c240b6a`
  est poussé sur `main`. FridaDev seul a été rebuild sans pull ni dépendances,
  puis recréé avec `--no-deps --force-recreate`.
- Image live `sha256:c2457063ba88e74d3ff42f8f47fe8d2d594af25c2daefe8b7e9e677fc6200d07`,
  `StartedAt=2026-09-03T11:52:14.178230702Z`, health déclaré `healthy`, GET
  interne `/` sur 8089 = `200`, restart `0`, OOM `false`; les 10 empreintes
  runtime concordent et l'unique conteneur voisin observé n'a pas été recréé.
  L'image O1 `sha256:82605c7ed2c4806024f6e489a6dd1b7749a76725108a54f6f7d34a78fc620f8b`
  reste disponible pour un retour applicatif ciblé.
- Les mêmes `354` tests ciblés sont verts depuis l'image livrée, sans montage du
  checkout et sans réseau.
- Préflight agent: `openai/gpt-5.2`, reasoning `high`, 16 000 tokens de sortie,
  5 outils et 1 appel modèle par tour, sans fallback. Au tarif public contrôlé
  de 1,75 USD/M tokens d'entrée et 14 USD/M tokens de sortie, le maximum
  pessimiste des deux tentatives effectuées est 1,848 USD; le coût réellement
  facturé n'est pas exposé par le runner.
- L'exploration et les deux canaris ont consommé 25 GET Catalogue, 2 tours et
  2 tentatives provider. Le premier plan agentique de section complète est
  resté ambigu sur le document. Le second a résolu le document public Kant et
  la section 399, avec `section_complete_extraction`, mais n'a atteint aucun
  `page_read`: le Catalogue décrit ses bornes 1818–1820 en unités `sections`,
  que le runtime refuse à juste titre de convertir en pages.
- Une unité interne de 17 469 caractères a bien été repérée, mais la coupure n'a
  donc pas traversé le vrai chemin d'extraction agentique. Le troisième tour
  autorisé n'a pas été appelé pour remplir le rapport: ni ce modèle ni un retry
  ne pouvait créer la coordonnée absente. Artefact content-free:
  `app/docs/states/baselines/biblio-smokes/b1-section-truncation-live-20260903T115903Z.jsonl`.

Statut honnête: **correctif technique prouvé et livré, preuve produit en
attente**. B1 reste ouvert et sa dernière case reste décochée. Le reste d'une
page coupée est signalé comme non reçu et aucun saut n'est exécuté; il n'est pas
accessible avec le `page_read` actuel dépourvu d'offset. B2 n'est pas commencé.

### Finalisation de la preuve produit B1 — 3 septembre 2026

- La cible a été établie avant tout nouvel appel modèle par `29` GET Catalogue:
  document public déjà employé par BIB-23 (`88ab236b`), section n° 12 résolue
  sans ambiguïté, bornes réelles `pages 10–10`. Son texte nettoyé compte
  `4 654` caractères; le vrai `page_read` retourne le préfixe borné avec
  `page_truncated=true`.
- Le checker existant classe désormais explicitement `section_integrity` et
  `section_integrity_continue`. Il exige le plan agentique, le `page_read`
  réellement exécuté, la vérité segment/incomplétude, le rendu, le lock et
  l'état; la reprise n'est verte que si le reste persiste et qu'aucun GET ou
  ancre suivante ne saute la coupe. Les attentes P01–P18 ne changent pas.
- Preuve live content-free:
  `app/docs/states/baselines/biblio-smokes/b1-section-truncation-live-20260903T123527Z.jsonl`.
  Le premier tour a exercé `section_complete_extraction` en `agent_first`, puis
  lu et coupé la page 10: `section_segment`, `range_complete=false`, page 10
  incomplète, annonce partielle, extrait exact rendu et final lock autorisé.
- Le second tour « Continue. » a bien appelé le bibliothécaire. Son plan
  `passage_continue_next_segment` proposait `page_read`, mais le garde-fou
  déterministe l'a refusé avant Catalogue: `0` GET, clarification explicite,
  page 10 toujours incomplète et aucune ancre page 11 inventée. Cette
  clarification n'est pas présentée comme une décision sémantique du modèle.
- Cette passe a consommé `33/60` GET, `2/3` tours et `2/3` tentatives provider,
  sans fallback. Au tarif contrôlé de 1,75 USD/M tokens d'entrée et 14 USD/M
  tokens de sortie, la borne pessimiste des deux appels est `1,848 USD`; le
  coût facturé n'est pas exposé par le runner. Le troisième témoin court n'a
  pas été rappelé, les contre-cas hermétiques le couvrant déjà.

B1 est fermé. Sa garantie reste bornée: une coupe intra-page n'est plus annoncée
complète et son reste n'est pas sauté, mais `page_read` sans offset ne rend pas
ce reste progressivement accessible. B2 n'est pas commencé.

## 11. B2 — Garder les coordonnées dans leur document

**Objectif :** « poursuivre » ne combine pas le nouveau document et l'ancienne page.

**Entrées et fichiers :** `app/biblio/conversation_state.py`,
`app/biblio/librarian_runtime_projection.py`,
`app/biblio/librarian_method_runtime.py`,
`app/biblio/librarian_dialogue_navigation.py`,
`app/biblio/librarian_dialogue_runtime.py` ;
[contrat Biblio native](../../states/specs/frida-biblio-native-catalogue-contract.md)
et [contrat bibliothécaire](../../states/specs/frida-biblio-librarian-agent-contract.md).
Tests : `app/tests/unit/biblio/test_conversation_state.py`,
`app/tests/unit/biblio/test_librarian_navigation_runtime.py`,
`app/tests/unit/biblio/test_librarian_agent_first.py`.

- [x] Confirmer ou invalider F11 : document A page 12, ouverture B sans nouvelle
  coordonnée, puis reprise ; inspecter l'état et la requête réellement construite.
- [x] Si confirmé, invalider les coordonnées/hash attachés à A lors du changement
  de document ; accepter les nouvelles coordonnées seulement avec leur provenance B.
- [x] Prouver conservation de la reprise dans A inchangé, absence de coordonnées
  inventées dans B, acceptation d'une ancre valide B et reset explicite préservé.
- [x] Vérifier après sérialisation/réhydratation, projection et navigation réelles ;
  documenter et livrer B2 avec la preuve agentique convenue.

**Fermeture :** aucune ancre mixte A/B. Si le finding est déjà faux au HEAD,
consigner l'invalidation prouvée sans fabriquer un patch ; pas de refonte d'état.

### Correction et livraison B2 — 3 septembre 2026

- F11 est reproduit au raccord réel projection d'outil -> état ->
  sérialisation/réhydratation -> navigation: après A page 12 puis une ancre B
  sans position, l'ancien code exécutait `page_read(B, 13)`. La mutation qui
  retire la correction reproduit exactement cette requête puis le code est
  restauré vert.
- `update_state_from_runtime()` invalide désormais `page_no`, `para_no`,
  `paragraph_id` et `last_passage_hash` lorsqu'une nouvelle ancre porte un
  `document_id` canonique différent. Les coordonnées présentes dans la nouvelle
  ancre B sont ensuite appliquées normalement; une mise à jour partielle du même
  document conserve son ancre. `last_result` et son intervalle étaient déjà
  remplacés et ne nécessitent aucun second chemin.
- `93` tests hermétiques ciblés sont verts avant livraison, réseau coupé et
  checkout en lecture seule; ils couvrent état, sérialisation, vraie exécution
  navigation, B1, planificateur et checker live. Après livraison, les `43` tests
  état/checker embarqués sont verts.
- Correctif/contrats/checker poussé au commit
  `39acfa28797db949351a98750389c47730c866a1`. FridaDev seul a été rebuild sans
  pull puis recréé avec `--no-deps`. Image live
  `sha256:48d846c3242de498ade21eb2eb0942892261ad34b041e2627b699a644fbd8d58`,
  `StartedAt=2026-09-03T13:16:00.461466831Z`, health déclaré `healthy`, GET
  interne `/` sur 8089 = `200`, restart `0`, OOM `false`; les empreintes runtime
  concernées concordent et les conteneurs voisins observés n'ont pas été
  recréés. L'image B1 `sha256:c2457063ba88e74d3ff42f8f47fe8d2d594af25c2daefe8b7e9e677fc6200d07`
  reste la référence de retour ciblé.
- La preuve agentique partielle est conservée dans
  `app/docs/states/baselines/biblio-smokes/b2-document-coordinate-provenance-live-20260903T131927Z.jsonl`.
  A (`d1f49f74`) et B (`62db0e10`) sont deux documents publics distincts déjà
  éprouvés par P04/P16 et vérifiés en metadata. Le tour A a établi une ancre
  page/paragraphe/hash. Au tour B, le bibliothécaire a planifié
  `search_document` puis `document_open_summary`, mais la résolution a rendu
  `not_found`: B n'a pas été ouvert et l'état est légitimement resté sur A. Le
  tour « Continue. » a donc continué A par `passage_context`; il ne constitue
  pas la précondition B2 et le checker reste rouge.
- La passe a consommé `13/40` GET Catalogue, `3/4` tours et `3/4` tentatives
  provider, sans fallback. Au tarif contrôlé de 1,75 USD/M tokens d'entrée et
  14 USD/M tokens de sortie, la borne pessimiste des trois appels est
  `2,772 USD`; le coût facturé n'est pas exposé. La dernière tentative n'est pas
  utilisée isolément: elle ne peut pas réétablir honnêtement toute la séquence
  successive A -> B -> reprise.
- Le checker strict B2 est finalisé et poussé au commit
  `8d53207b496e7dbf81df50ad493309befdf5fce9`, sans modification du produit ni
  de B1. Il accepte séparément la clarification directe du modèle et la
  continuation refusée par le garde, vérifie les identifiants canoniques complets
  et impose les préconditions successives A -> B -> reprise. Les `53` tests
  état/smoke/B1 directement concernés sont verts, réseau coupé et checkout en
  lecture seule; la mutation qui rétablit l'exigence exclusive de `page_read`
  remet le témoin de clarification au rouge.
- La nouvelle preuve bornée est conservée dans
  `app/docs/states/baselines/biblio-smokes/b2-document-coordinate-provenance-live-20260903T145621Z.jsonl`.
  Les metadata exactes confirment A (`d1f49f74`) et B (`62db0e10`), leur
  distinction, le repère A exploitable et l'identifiant canonique complet de B
  visible dans la demande. Au premier tour, le modèle a été appelé et a choisi
  `passage_extract_canonical_range`, mais l'outil exécuté a terminé
  `document_not_found`: aucun état ni ancre A n'a été produit. La porte stricte
  a donc empêché l'appel des tours B et reprise, chacun avec `0` GET et sans
  modèle; B n'a pas été silencieusement remplacé ni une continuation inventée.
- Cette passe finale a consommé au total `10/20` GET Catalogue, `3/3` tours
  synthétiques et `1/3` tentative provider, sans fallback. La borne pessimiste
  de l'appel effectif est `0,924 USD` sur un plafond préflight de `2,772 USD`
  pour trois appels; le coût facturé n'est pas exposé. Conformément au mandat,
  les deux tentatives restantes ne sont pas utilisées en retry.

Statut honnête: **correctif technique prouvé et livré, preuve produit en
attente**. B2 reste ouvert: la nouvelle preuve n'a pas établi l'ancre A, donc
n'a pu ni ouvrir réellement B ni atteindre la reprise depuis l'état B. Z n'est
pas commencé.

### Finalisation B2 — 3 septembre 2026

- Le scénario final retire les recherches par titre sans rapport avec F11. Il
  donne au bibliothécaire les deux identifiants canoniques publics et une page A
  préalablement vérifiée: A est lu par `page_read` à la page 131, puis B est
  ouvert par `document_open_summary` sans lecture de page.
- Le checker accepte désormais une ancre B2 exacte issue d'une page même si le
  runtime ne fabrique pas d'objet `passage`: document A, position A, lane
  injectée et GET `page` suffisent. Cette correction ne relâche ni l'identité
  canonique ni l'exigence d'une position réelle.
- La preuve live content-free
  `app/docs/states/baselines/biblio-smokes/b2-document-coordinate-provenance-live-20260903T184059Z.jsonl`
  établit successivement A (`d1f49f74`, page 131), l'ouverture de B (`62db0e10`)
  et l'invalidation complète des coordonnées A. Le tour « Continue. » conserve B,
  n'envoie aucun GET Catalogue, n'invente aucune coordonnée et rend la
  clarification bornée existante.
- Le plan agent du troisième tour reste explicitement invalide avec
  `biblio_librarian_agent_product_method_tool_mismatch`. Le checker conserve cet
  échec sur l'axe agent mais ne le confond plus avec l'intégrité produit B2:
  l'appel modèle a eu lieu, son plan n'a exécuté aucun outil et le garde
  déterministe a protégé l'état. Aucun succès agent n'est fabriqué.
- La campagne finale a utilisé `3/3` appels GPT-5.2 high, sans retry ni fallback,
  et `4/20` GET Catalogue dont deux de reconnaissance. La borne pessimiste est
  `2,772 USD`; aucun texte, prompt, paramètre d'outil ou contenu provider n'est
  conservé. Les `92` tests ciblés état/navigation/agent/checker sont verts.

B2 est fermé. Z reste non commencé.

### Preuve live Biblio : autorité et proportion

Le prompt d'exécution de B1/B2 doit inclure dans le même GO les appels bornés,
le corpus existant/public autorisé, le budget et le service concerné, pour ne
pas multiplier les retours administratifs. Réutiliser
`app/biblio/smoke_librarian_agent_live.py` et les artefacts existants.

Sans cette autorisation, préparer les preuves hermétiques mais ne pas provoquer
d'appel : le statut est « correctif technique prouvé, preuve produit en attente »,
pas « fermé ». Une clôture produit Biblio exige le bibliothécaire agentique réel
et un JSONL daté content-free, selon AGENTS.md. Aucun nouveau banc d'essai,
comparatif de modèles ou catalogue artificiel. Un cas valide n'est pas rappelé
uniquement pour obtenir un second rapport.

## 12. Z — Fermeture bornée, sans nouvel audit général

- [ ] Vérifier les sept sorties I1/I2/M1/M2/O1/B1/B2, leurs contrats, preuves et
  états de livraison ; conserver explicitement toute réserve réelle.
- [ ] Exécuter une seule découverte Python hermétique de clôture, après les lots,
  et les validations frontend des surfaces effectivement modifiées. Ne pas la
  refaire mécaniquement à chaque micro-correction.
- [ ] Vérifier les frontières directement voisines : sauvegarde du tour,
  dérivations, état résumé, staging mutable, payload de l'arbitre, rendu Biblio.
  Réutiliser les preuves acquises ; aucune campagne générale provider.
- [ ] Vérifier Git propre/aligné, empreintes et health utiles, puis synchroniser
  le statut global et le hub documentaire. Ne pas prétendre mesurer la latence
  courante ni la qualité sémantique globale de Frida.
- [ ] Quand les lots sont clos ou explicitement requalifiés avec preuve/décision,
  archiver cette roadmap dans `todo-done/refactors/` et arrêter le chantier.

Un finding hors périmètre découvert en Z est conservé dans l'audit avec sa
preuve, pas transformé automatiquement en nouveau lot bloquant. Un défaut qui
invalide directement une sortie de cette roadmap empêche en revanche sa fausse
fermeture. Aucune boucle indéfinie de contre-audits.

## 13. Réserves hors périmètre, conservées dans l'audit

F05, F08–F10 et F12–F24 ne sont ni corrigés, ni invalidés, ni tacitement acceptés
par cette roadmap. Ils restent dans le rapport source jusqu'à leur décision
propre : code rendu, Nextcloud, snapshots concurrents, sélection UI, Agenda,
OCR/atelier, Web, analytics, outils historiques et documentation publique.

En particulier, F23 concerne le démarrage local d'un clone et sa publication
de port ; ce n'est pas une preuve d'exposition non authentifiée de l'OVH. Sa
mention documentaire peut faire l'objet d'un travail séparé, sans toucher à la
plateforme au titre de cette roadmap. Aucune réécriture générale du README.

La clôture de cette roadmap ne ferme pas l'audit entier et ne rouvre pas les
décisions de l'ancienne consolidation, notamment Stimmung et la latence Lot 7.
