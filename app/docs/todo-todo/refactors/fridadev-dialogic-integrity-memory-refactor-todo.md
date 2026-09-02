# FridaDev — intégrité et continuité de la mémoire dialogique

Date de cadrage : 2 septembre 2026.

**Statut : roadmap ouverte ; I1 corrigé et validé hermétiquement, livraison applicative en attente ; I2 et les lots suivants non commencés.**

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
| 1 | I1 | Une erreur de streaming reste une interruption | F01 | xhigh | correctif validé, livraison en attente |
| 2 | I2 | Une lecture Identity en panne ne permet aucun remplacement | F02 | xhigh | non commencé |
| 3 | M1 | Un résumé n'est acquis qu'après stockage confirmé | F03 | xhigh | non commencé |
| 4 | M2 | La déduplication ne retire pas une formulation distincte avant jugement | F04 | xhigh | non commencé |
| 5 | O1 | Les hints dialogiques sont comptés par leur vrai reader | F07 | high | non commencé |
| 6 | B1 | Un extrait tronqué n'est jamais annoncé complet | F06 | xhigh | non commencé |
| 7 | B2 | Une reprise appartient au document réellement ouvert | F11 | high | non commencé |
| 8 | Z | Vérification finale limitée aux raccords modifiés | ci-dessus | high | non commencé |

- [x] Cadrage documentaire et limites de preuve consignés.
- [ ] I1 fermé avec preuves et livraison convenues.
- [ ] I2 fermé avec preuves et livraison convenues.
- [ ] M1 fermé avec preuves et livraison convenues.
- [ ] M2 fermé avec preuves et livraison convenues.
- [ ] O1 fermé avec preuves et livraison convenues.
- [ ] B1 fermé avec preuve agentique requise.
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
- [ ] Mettre à jour uniquement les contrats/mentions devenus faux et livrer I1.

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
  opérateur ni donnée live. La livraison runtime n'est pas encore revendiquée.

## 6. I2 — Distinguer canon absent et canon illisible

**Objectif :** préserver l'identité mutable existante quand sa lecture échoue.

**Entrées et fichiers :** `app/memory/memory_identity_mutables.py`,
`app/memory/mutable_identity_apply.py`, leurs façades dans `app/memory/memory_store.py`
et appelants mutateurs ; [contrat du juge mutable](../../states/specs/mutable-identity-judge-contract.md).
Tests : `app/tests/unit/memory/test_mutable_identity_apply.py`,
`app/tests/test_identity_mutables_phase1b.py`,
`app/tests/unit/memory/test_identity_liveness_lot1.py`,
`app/tests/unit/memory/test_identity_staging_lot2.py`.

- [ ] Reproduire canon existant + lecture indisponible + écriture disponible,
  avec proposition admise par le véritable validateur add-only.
- [ ] Fermer la frontière mutante : l'erreur de lecture n'est plus assimilée à
  une absence établie. Adapter ses consommateurs nécessaires, sans étendre une
  exception nouvelle à toutes les lectures admin supposées tolérantes.
- [ ] Prouver zéro remplacement et zéro faux succès en cas de lecture en panne ;
  conserver la politique bornée d'échec/reprise et les fences existantes.
- [ ] Prouver les contre-cas : absence réellement lue → création légitime ; canon
  présent → ajout conservant l'ancien ; no_change → aucune écriture ; erreur
  d'écriture → résultat non réussi. Préserver les éditions administrateur.
- [ ] Vérifier audit et projection du résultat sans inventer une lecture réussie ;
  documenter et livrer I2.

**Fermeture :** panne de lecture démontrée et impossibilité de l'écrasement
consécutif. Aucun replay manuel du staging, migration ni nouveau protocole de
transaction distribuée. Le stockage factice n'est pas présenté comme une panne
PostgreSQL réelle.

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

- [ ] Reproduire échec du stockage texte au vrai niveau qui absorbe actuellement
  l'erreur, puis suivre le booléen, les marques et l'événement côté coordinateur.
- [ ] Faire remonter une issue de stockage non ambiguë ; conditionner l'acquisition
  et les marques à la conservation effective du résumé. Garder la génération,
  la persistance et le rattachement des traces comme opérations distinctes.
- [ ] Sur échec texte, prouver absence de nouvelles marques/cutoff acquis et de
  summary_generated trompeur ; les messages restent disponibles au tour suivant.
- [ ] Sur texte stocké mais embedding indisponible, conserver le résumé texte
  légitime. Sur échec du rattachement des traces, préserver le texte déjà stocké,
  qualifier honnêtement l'état et vérifier la cohérence du prochain tour sans
  rollback aveugle ni boucle de retries nouvellement ajoutée.
- [ ] Prouver le chemin nominal après sauvegarde/réhydratation et préserver le
  diagnostic privé existant. Corriger le test qui exige True après échec sans
  retirer son assertion utile sur le diagnostic ; documenter et livrer M1.

**Fermeture :** les indicateurs d'acquisition correspondent au stockage effectif ;
aucune perte de disponibilité des messages du fait d'une écriture manquée. Le
lot ne crée ni résumé hiérarchique, ni nouvelle politique de sélection temporelle.

## 8. M2 — Préserver les variantes avant le jugement Memory

**Objectif :** le jugement reçoit les différences de formulation utiles au
dialogue ; le prétraitement ne décide pas à sa place qu'elles sont équivalentes.

**Entrées et fichiers :** `app/memory/memory_pre_arbiter_basket.py`,
`app/core/chat_memory_flow.py`, leurs constructeurs d'inputs et appelants arbitre ;
[contrat du panier](../../states/specs/memory-rag-pre-arbiter-basket-contract.md).
Test principal : `app/tests/unit/memory/test_memory_pre_arbiter_basket_phase7b.py`.

- [ ] Reproduire mardi/jeudi : ancienne trace mieux classée, nouvelle plus récente ;
  observer le contenu transmis à l'arbitre, pas seulement les IDs fusionnés.
- [ ] Retirer ou restreindre la fusion lexicale qui efface un texte distinct.
  Préférer la conservation des formulations à un détecteur de correction ; les
  égalités réellement sûres gardent leur déduplication et leur provenance.
- [ ] Prouver que date, quantité et négation différentes restent distinctes dans
  des candidats admis sous le budget, et que deux contenus strictement identiques
  ne sont pas inutilement dupliqués. Tester les vrais constructeurs jusqu'au prompt.
- [ ] Maintenir les plafonds de candidats/tokens et le classement existants ; une
  éviction par budget reste une sélection bornée, jamais une fausse équivalence.
- [ ] Vérifier compteurs/raisons de déduplication réellement affectés, documenter
  et livrer M2 sans modifier modèle, prompt arbitre, embeddings ou reranker.

**Fermeture :** la variation n'est plus détruite par la déduplication avant le
jugement. Ne pas prétendre que le modèle choisira toujours la bonne correction :
ce lot prouve l'accès à la matière, pas son efficacité sémantique universelle.
Aucune regex sémantique, nouvelle taxonomie ou campagne de modèles.

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

- [ ] Reproduire dialogue → zéro avant SQL, puis composer le vrai writer,
  reader et read-model avec un stockage factice de lignes.
- [ ] Admettre dialogue uniquement dans le reader d'evidence concerné ; ne pas
  élargir l'allowlist commune des identities, conflits ou canons user/llm.
- [ ] Prouver N evidences dialogue → N réellement stockées dans la projection,
  absence légitime → zéro, historique user/llm conservé, filtres/limites inchangés.
- [ ] Suivre cette donnée jusqu'aux renderers existants ; ne pas confondre compteur
  stocké, sélection pour injection et dernière activité. Modifier l'UI seulement
  si nécessaire à la fidélité du contrat, sans écran ni collecte supplémentaire.
- [ ] Documenter et livrer O1 ; aucun retrait ni changement sémantique des hints.

**Fermeture :** le compteur rend la catégorie réellement écrite et n'affirme pas
une absence d'injection depuis un simple zéro administratif.

## 10. B1 — Distinguer section complète et fragment borné

**Objectif :** une lecture partielle ne devient pas une preuve d'intégralité.

**Entrées et fichiers :** `app/biblio/librarian_tools.py`,
`app/biblio/answer_extraction.py`, `app/biblio/answer_surface.py`, raccords de
reprise et final lock ; [contrat Biblio native](../../states/specs/frida-biblio-native-catalogue-contract.md)
et [contrat bibliothécaire](../../states/specs/frida-biblio-librarian-agent-contract.md).
Tests : `app/tests/unit/biblio/test_librarian_tools.py`,
`app/tests/unit/biblio/test_librarian_agent_first.py`,
`app/tests/unit/biblio/test_librarian_method_boundaries.py`.

- [ ] Rejouer la section d'une page dont le texte dépasse la borne actuelle,
  par le vrai chemin agent-first avec client Catalogue factice.
- [ ] Propager l'incomplétude dans l'objet-réponse, le rendu et les conditions de
  lock ; un hash de fragment n'est pas une preuve de section complète.
- [ ] Conserver une reprise honnête sur la matière non lue, avec les mécanismes
  existants ; ne pas avancer au-delà de la coupe ni inventer une nouvelle ancre.
- [ ] Préserver page courte complète, sections multi-pages et extraction canonique
  segmentée déjà correcte. Ne pas relever globalement les plafonds.
- [ ] Livrer la correction puis la preuve agentique bornée convenue ci-dessous,
  mettre à jour contrat/observabilité affectés et fermer B1 seulement avec celle-ci.

**Fermeture :** aucun « complet » trompeur ; le reste non lu reste identifiable.
Le bibliothécaire LLM est conservé, pas remplacé par des règles de lecture.

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

- [ ] Confirmer ou invalider F11 : document A page 12, ouverture B sans nouvelle
  coordonnée, puis reprise ; inspecter l'état et la requête réellement construite.
- [ ] Si confirmé, invalider les coordonnées/hash attachés à A lors du changement
  de document ; accepter les nouvelles coordonnées seulement avec leur provenance B.
- [ ] Prouver conservation de la reprise dans A inchangé, absence de coordonnées
  inventées dans B, acceptation d'une ancre valide B et reset explicite préservé.
- [ ] Vérifier après sérialisation/réhydratation, projection et navigation réelles ;
  documenter et livrer B2 avec la preuve agentique convenue.

**Fermeture :** aucune ancre mixte A/B. Si le finding est déjà faux au HEAD,
consigner l'invalidation prouvée sans fabriquer un patch ; pas de refonte d'état.

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
