# FridaDev — consolidation résiduelle du grand audit de recherche

Date de cadrage : 4 septembre 2026.

**Statut : roadmap ouverte ; L1 à L6 et L7.1-L7.7 fermés ; Z non refermable au
7 septembre 2026. Les quatre incompatibilités tests/support de la découverte à
3079 tests sont corrigées sans changement produit. La sélection commune passe
141/141, mais l'unique nouvelle découverte complète exécute 3088 tests en
613,603 s et sort 1 avec 2 échecs, 0 erreur et 0 skip. Les deux échecs sont
reproduits comme un défaut de commande hermétique : trois URL de services
support validées syntaxiquement avaient été vidées avec les credentials ; elles
passent 2/2 avec des URL `.invalid`, réseau toujours coupé et tokens vides. Z
reste ouvert, la réserve Biblio conserve sa limite de preuve et la roadmap
n'est pas archivée.**

## 1. But, source et règle de vérité

Cette roadmap traite les réserves encore ouvertes du grand audit de recherche
FridaDev, dans l'ordre décidé par Tof : frontière publique du clone, intégrité
du dialogue, compensations Nextcloud, projection analytics, écritures Workspace,
justesse produit, puis observabilité et outillage historique.

Elle ne remplace pas le rapport source :
[audit de recherche du 2 septembre 2026](../audits/fridadev-research-feature-audit-2026-09-02.md),
commit initial `49ed4b3cb1e8b7e2e03c1ac59db0e7dd3572d881`.
Les identifiants Fxx renvoient exclusivement à ce rapport. Le texte historique
des findings reste conservé ; cette roadmap enregistre leur revalidation, leur
correction, leur invalidation ou leur maintien explicite.

La précédente roadmap
[intégrité et continuité de la mémoire dialogique](../../todo-done/refactors/fridadev-dialogic-integrity-memory-refactor-todo.md)
a fermé F01, F02, F03, F04, F06, F07 et F11. Elle n'a ni corrigé, ni invalidé,
ni accepté tacitement F05, F08–F10 et F12–F24.

Baseline documentaire de ce cadrage : branche `main`, HEAD/upstream/distant
`cc5c593ee9d4fbcf63d85716c2b7900472664505`, divergence `0/0`, worktree propre.
Ce commit est un repère daté, pas une version que les lots futurs doivent
retrouver après leurs propres livraisons.

FridaDev reste un système personnel de recherche sur le langage, la mémoire et
le dialogue. Cette roadmap est une consolidation stricte de capacités existantes,
sans ajout de feature, agent, modèle, provider, vue, route, table, collecte ou
workflow.

## 2. Doctrine d'exécution proportionnée

- Un lot ne commence qu'après un GO distinct. Il n'enchaîne jamais le suivant.
- Chaque finding est revalidé au HEAD courant avant patch. Une hypothèse
  invalidée par preuve est documentée puis fermée sans correctif de convenance.
- Un micro-lot corrige une seule frontière causale. Les sous-lots d'une même
  feature ne sont regroupés que si le même correctif et les mêmes preuves les
  ferment réellement.
- Reproduction ciblée, plus petit correctif cohérent, test au point réel de
  lecture/écriture/rendu, voisins directement concernés, puis contre-audit.
- Pas de cathédrale de tests : pas de nouvelle campagne, corpus ou framework ;
  une preuve centrale et ses contre-cas légitimes suffisent. La découverte
  Python complète est réservée à Z, sauf modification réellement transversale
  qui la rend indispensable et doit alors être justifiée.
- JavaScript et Chromium ne sont lancés que si le lot touche un contrôleur,
  renderer ou contrat frontend. Aucun navigateur général pour un lot backend.
- Aucun provider réel, donnée opérateur, DB live, dialogue réel ou mutation
  externe sans autorisation séparée. Les stores et transports factices prouvent
  le comportement applicatif, pas la fréquence live.
- Une correction runtime autorisée inclut livraison ciblée et preuve de santé.
  Un lot tests/docs-only ne provoque ni rebuild ni restart.
- Chaque lot met à jour cette roadmap et les seuls contrats vivants devenus
  faux, relit son diff, exécute `git diff --check`, commit et push, puis prouve
  worktree propre, HEAD/upstream/distant égaux et divergence `0/0`.
- Aucun finding vivant ne disparaît : à la clôture il est `corrigé`, `invalidé`,
  `différé avec condition explicite` ou `toujours ouvert`.

Stimmung reste constitutive et `keep_current_v2.3` reste inchangée. Presence,
hard guards, final locks, transports stricts, validation métier locale et logs
privés Memory/Identity ne sont pas rouverts par cette roadmap.

## 3. Ordre de travail

| Ordre | Lot | Objet | Findings | Réflexion conseillée | Statut |
| --- | --- | --- | --- | --- | --- |
| 1 | L1 | Frontière réseau du clone public | F23 | high | fermé — F23 corrigé |
| 2 | L2 | Intégrité du canon conversationnel | F09 | xhigh | fermé — F09 corrigé |
| 3 | L3 | Compensation Nextcloud possédée | F08 | xhigh | fermé — F08 corrigé |
| 4 | L4 | Conservation de la projection analytics | F21 | high | fermé — F21 corrigé |
| 5 | L5 | Atomicité des écritures Workspace | F13b, F14a, F19b | xhigh par sous-lot | fermé — F13b, F14a et F19b corrigés |
| 6 | L6 | Justesse produit directement perceptible | F05, F10, F12, F13a, F14b, F15, F19a | high/xhigh par sous-lot | fermé — F05, F10, F12a-F12c, F13a, F14b, F15a-F15b et F19a corrigés |
| 7 | L7 | Vérité d'API, observabilité et outils historiques | F16–F18, F20, F22, F24 et dette documentaire | high | fermé — L7.1-L7.7 fermés |
| 8 | Z | Réconciliation finale avec le grand audit | tous les Fxx et réserves non numérotées | xhigh | ouvert — quatre familles tests/support corrigées, sélection commune 141/141, découverte finale rouge sur deux URL de services support neutralisées à tort |

- [x] Source, périmètre, ordre et règles de preuve consignés.
- [x] L1 fermé.
- [x] L2 fermé.
- [x] L3 fermé.
- [x] L4 fermé.
- [x] L5.1 fermé.
- [x] L5.2 et L5.3 fermés.
- [x] L6.1 fermé ; F05 corrigé et cas terminal vide corrigé après reproduction.
- [x] L6.2 fermé ; F10 corrigé sur les quatre familles frontend confirmées.
- [x] L6.3 fermé ; F12a et F12b corrigés sans commencer F12c/L6.4.
- [x] L6.4 fermé ; F12c corrigé sans commencer L6.5.
- [x] L6.5 fermé ; F15a et F15b corrigés sans commencer L6.6.
- [x] L6.6 fermé ; F19a corrigé sans commencer L6.7.
- [x] L6 fermé ; L6.7/F13a-F14b corrigés sans commencer L7.
- [x] L7.6 fermé ; F24 corrigé sans commencer L7.7.
- [x] L7.7 et L7 fermés ; dette documentaire D1-D8 réconciliée sans commencer Z.
- [x] Z réconcilie les 24 findings, leurs 34 lignes atomiques et les quatre réserves Biblio.
- [x] Le micro-lot Biblio borné corrige techniquement le libellé visible et
  verrouille 25 retenus / 20 détaillés / 5 masqués sans changer les totaux
  durables.
- [x] La réserve Biblio est corrigée par la preuve composée décidée par Tof :
  12/12 sur le chemin agentique réel et 25/20/5 sur le même renderer
  hermétique. La cardinalité live actuelle de 12 rend la borne supérieure à 20
  non franchissable ; elle constitue une limite de preuve et un déclencheur de
  revalidation lorsque le corpus live dépassera 20, pas un bug produit ouvert.
- [x] La passe distincte réaligne les deux fixtures Chromium F17 et le témoin
  Python Compose F23, puis récupère durablement la sortie de l'unique découverte.
- [x] Le micro-lot final corrige les quatre familles tests/support sans rouvrir
  Agenda, F09, F24, Stimmung, Biblio ni les F01-F24 ; la sélection commune
  passe 141/141.
- [ ] L'unique nouvelle découverte complète reste rouge : 3088 tests en
  613,603 s, 2 échecs, 0 erreur, 0 skip, exit 1. Aucun second run complet n'est
  autorisé dans ce lot ; l'archivage reste refusé jusqu'à une preuve distincte
  avec URL de services support synthétiques valides et credentials neutralisés.

## 4. L1 — Restreindre le Compose du clone public

**Finding : F23.**

**Objectif :** le chemin annoncé comme local ne publie pas implicitement
FridaDev sur toutes les interfaces de l'hôte.

**Hypothèses à revalider :**

- `docker-compose.yml` publie toujours `8093:8089` sans IP hôte ;
- le README présente toujours l'accès comme loopback ;
- ce Compose n'embarque pas la protection publique OVH.

**Correction bornée envisagée :** lier explicitement le port de développement
à `127.0.0.1`, synchroniser le README et vérifier la configuration Compose.
Ne pas modifier la sous-stack OVH, Caddy, Authelia, Docker hôte ou les gardes
admin applicatives. Ne pas réintroduire `FRIDA_ADMIN_TOKEN`.

**Revalidation au HEAD `2a15190889e297d9068fa2d3d00fc17d36094ba7` :**

- H1 confirmée avant correction : `docker-compose.yml` publiait
  `8093:8089` sans IP hôte ;
- H2 confirmée : le rendu Compose omettait `host_ip` et la
  [spécification Docker Compose](https://docs.docker.com/reference/compose-file/services/#ports)
  lie dans ce cas le port à toutes les interfaces (`0.0.0.0`) ;
- H3 confirmée : le README et `stack.sh` annonçaient déjà
  `http://127.0.0.1:8093/` ;
- H4 confirmée : ce Compose ne définit que le service `fridadev`, sans service
  proxy ni authentification Caddy/Authelia ;
- H5 confirmée : ajouter l'IP hôte à l'unique mapping suffit à obtenir
  `host_ip=127.0.0.1`, `published=8093` et `target=8089`, sans changement
  applicatif.

**Décision et correctif :** aucun plan plus simple ou plus sûr n'offre moins
d'effets de bord. Le mapping devient `127.0.0.1:8093:8089` et le README rend
explicites la liaison au loopback IPv4 hôte, l'absence de l'authentification
publique OVH et l'interdiction d'une publication réseau sans protection
adaptée. Aucun token, proxy, garde ou mécanisme générique n'est ajouté.

**Preuves de fermeture :** la CLI Compose est disponible, mais le clone ne
contient volontairement pas `app/.env`. Pour ne créer ni lire de secret, les
commandes `config --quiet` et `config --format json` ont donc reçu sur stdin un
override limité remplaçant seulement `env_file` par `/dev/null`. Le fichier
Compose exact reste parsé ; la projection JSON est consommée directement par
`jq` sans afficher la configuration. Les verdicts prouvent l'unique mapping
`host_ip=127.0.0.1`, `published=8093`, `target=8089`, ainsi que l'écoute
conteneur `0.0.0.0:8089` et le healthcheck interne
`http://127.0.0.1:8089/` inchangés. Le README conserve l'URL locale correcte et
porte les trois avertissements attendus. `git diff --check` et la preuve Git de
livraison complètent le lot avant push.

**Fermeture :** F23 est corrigé dans le Compose du clone public ; configuration
rendue et documentation concordent. Aucun audit réseau de l'OVH, déploiement,
rebuild ou restart n'est revendiqué. L2 n'était pas commencé lors de cette
fermeture.

## 5. L2 — Empêcher un snapshot ancien d'écraser un dialogue récent

**Finding : F09.**

**Objectif :** préserver l'ordre canonique des tours lorsqu'une sauvegarde,
une réponse ou un renommage se recouvrent.

**Hypothèses à revalider :**

- la sauvegarde remplace encore les messages à partir d'un snapshot complet ;
- un second submit peut encore recouvrir le premier côté navigateur ;
- le renommage réécrit encore inutilement les messages avant le titre.

**Périmètre :** store et service de conversations, orchestration de sauvegarde,
submit chat et renommage existants. Aucun verrou distribué, worker, versionnage
générique, système multi-utilisateur ou nouvelle API.

**Preuve attendue :** une écriture plus ancienne ne retire jamais un tour déjà
committé ; le renommage ne réécrit pas le dialogue ; l'ordre légitime et les
erreurs de sauvegarde restent visibles.

**Revalidation au HEAD `fe7cfe74e11de52e0c1de99035c7f3ae957c4df3` :**

- F1 confirmée : le writer atomique supprimait toutes les lignes puis
  réinsérait le snapshot reçu ;
- F2 confirmée : `GREATEST(updated_at, ...)` protégeait seulement la date du
  catalogue, pas le suffixe de messages ;
- F3 confirmée : un snapshot ancien et une branche divergente de même taille
  étaient tous deux acceptés et remplaçaient le canon ;
- F4 et F5 confirmées : le renommage chargeait résumé et messages, appelait la
  sauvegarde complète, puis exécutait tout de même son `UPDATE` de titre ;
- F6 confirmée : `chatRequestInFlight` existait, mais aucun garde ne précédait
  la lecture, l'effacement du brouillon et l'appel réseau ;
- F7 confirmée : la réinsertion naïve pouvait perdre ou ressusciter
  `summarized_by`, `embedded` et `meta`.

**Décision et architecture :** il existe un plan plus simple et plus sûr que
du versionnage ou une fusion de branches : conserver la transaction existante
et lui ajouter une précondition canonique. L'upsert du catalogue sérialise la
conversation par le verrou de ligne transactionnel, puis le writer lit les
messages par `seq` sous verrou et n'accepte que le même ordre exact ou une
extension dont le canon est un préfixe prouvé. Rôle, contenu et timestamp sont
comparés à chaque position dialogique ; aucun ordre n'est inféré des timestamps
ou du seul compteur. Les marqueurs monotones sont conservés ou enrichis :
`summarized_by` ne peut pas changer d'identité, `embedded` ne revient pas à
`false`, et `meta` accepte seulement des ajouts récursifs non conflictuels. Un
snapshot plus court, divergent ou porteur d'une metadata incompatible provoque
le rollback du catalogue et est refusé avec le reason code fermé
`conversation_snapshot_conflict`. L'écriture catalog/messages reste atomique :
aucune mutation du catalogue n'est committée quand les messages sont refusés.
Le contenu du premier message `system` est une projection volatile : lorsque le
canon et le snapshot portent tous deux ce rôle à l'index `0`, le writer accepte
son actualisation tout en maintenant l'égalité stricte de son rôle et de son
timestamp. Tous les messages suivants, y compris un éventuel autre `system`,
restent comparés strictement par rôle, contenu et timestamp.

Le renommage conserve uniquement son `UPDATE conversations SET title` : aucun
chargement ou writer de messages, et les dates de création, soft delete,
dossier workspace et autres metadata restent ceux de la ligne. Le submit
navigateur refuse immédiatement un second événement pendant le premier flux,
avant de lire ou vider le brouillon ; le `finally` existant libère le garde sur
succès comme sur erreur.

**Preuves rouges puis vertes :** une DB factice transactionnelle conserve les
lignes réellement committées et prouve R1 (snapshot ancien), R2 (branches de
même longueur), R3 (renommage ciblé) et les contre-cas metadata. Les parcours
Chromium prouvent R4 sur terminal nominal et terminal d'erreur : un seul appel
réseau, second brouillon intact, aucune bulle fantôme, reprise possible après
libération du garde. Avant correction, les quatre familles échouaient pour les
causes attendues. Après correction passent les `16` tests du store, `50` tests
chat/session/routes ciblés et `25` tests navigateur/dictée ciblés. Une mutation
de sensibilité rétablissant temporairement le remplacement destructif remet R1
en échec ; le fichier restauré retrouve exactement son empreinte préalable.

**Limites :** aucune fusion de branches divergentes n'est inventée ; le client
reçoit l'erreur de persistance publique existante et le reason code précis
reste observable côté serveur. Aucun schéma, migration, verrou distribué,
queue, nouvelle API ou mécanisme multi-utilisateur n'est ajouté. Les preuves
sont hermétiques, sans provider, DB opérateur ni dialogue réel. F10, F17 et les
findings suivants restent hors lot.

**Fermeture initiale :** F09 est corrigé et prouvé. À cet instant, L3 n'avait
pas commencé.

**Réouverture corrective bornée du 4 septembre 2026, HEAD de départ
`8b5137625c675cb6ae51bfe1314f4bacdf72524d` :**

- C1 confirmée : `resolve_chat_session()` crée puis sauvegarde la conversation
  avec le prompt système de base ; le tour ajoute ensuite le message utilisateur,
  construit le système augmenté et `apply_augmented_system()` remplace le contenu
  du premier message avant la sauvegarde finale ;
- C2 confirmée : `build_augmented_system()` incorpore le bloc temporel construit
  depuis le `now_iso` du tour et le bloc renvoyé par l'Identity courante ; ces deux
  entrées peuvent donc changer entre deux tours ;
- C3 confirmée et reproduite rouge : la précondition L2 comparait strictement le
  contenu du système stocké au système augmenté et refusait le premier tour avec
  `conversation_snapshot_conflict` avant toute réécriture ;
- C4 confirmée : les preuves transactionnelles L2 utilisaient toutes le contenu
  système constant `SYSTEM` et ne traversaient ni `build_augmented_system()` ni
  `apply_augmented_system()` ;
- C5 confirmée : longueur, rôle, contenu, timestamp, ordre et métadonnées des
  messages dialogiques doivent rester protégés dans la transaction existante ;
- C6 confirmée : le renommage reste un `UPDATE` catalogue ciblé et la garde
  `chatRequestInFlight` précède toujours toute lecture ou suppression du brouillon,
  avec libération dans `finally`. Aucun de ces chemins n'est modifié.

Le correctif minimal traite uniquement le contenu de l'index `0` lorsque les
deux rôles sont `system`. Il ne crée ni seconde persistance, ni normalisation
parallèle du prompt, ni version de snapshot. La preuve produit réutilise la DB
factice transactionnelle et les vraies fonctions de création, de construction
et d'application du système : prompt de base, premier tour augmenté, second
`NOW` et Identity différents, conservation du dialogue et des métadonnées,
refus atomique d'un snapshot court, refus d'une ancienne parole modifiée et
absence d'exemption pour un `system` ultérieur. Les 85 tests ciblés passent.
Une mutation rétablissant temporairement l'égalité stricte du contenu système
remet la preuve centrale en échec ; le fichier restauré retrouve exactement son
empreinte. F09 est de nouveau corrigé et prouvé ; L3 a été traité séparément.

## 6. L3 — Ne compenser que la version Nextcloud encore possédée

**Finding : F08.**

**Objectif :** une compensation après échec local ne supprime jamais une
version distante modifiée depuis sa création par Frida.

**Sous-périmètres à traiter dans le même contrat, sans gros patch aveugle :**
Documents, Notes créées, Exports et Images. Le cas MKCOL doit être décidé
séparément si l'intégrité d'une collection et de ses descendants ne peut pas
être prouvée par le même mécanisme.

**Preuve attendue :** création V1, modification distante V2 simulée, échec DB :
V2 est conservée et le reliquat est signalé honnêtement. La compensation
nominale de la version encore possédée reste fonctionnelle.

**Hors périmètre :** synchronisation générale Nextcloud, audit de récupération,
nouveau journal distribué ou mutation d'un espace opérateur réel.

**Revalidation et fermeture du 4 septembre 2026 :**

- F1 à F4 confirmés : Documents, Notes créées, Exports et Images générées
  utilisaient une création anti-écrasement suivie, en cas d'échec local, d'un
  DELETE compensatoire sans précondition de version ; le chemin de copie des
  Documents existants possédait le même défaut ;
- F5 et F6 confirmés : Notes, Exports et Images transportaient déjà l'ETag du
  PUT ; Documents le perdait à la frontière client. Sa propagation en mémoire
  et un DELETE `If-Match` réutilisent le contrat de concurrence déjà établi par
  l'append Notes, sans nouveau stockage durable ;
- F7 confirmée : la compensation distingue désormais `deleted`, `missing`,
  `precondition_failed`, `ownership_unverified` et `failed`. Un `412` qualifie
  uniquement le refus de précondition, sans attribuer de cause à la divergence ;
- F8 confirmée : les validations, la création nominale et les suppressions
  utilisateur explicites restent inchangées ;
- F9 confirmée : ni la réponse MKCOL ni un PROPFIND Depth 0 ne prouvent
  l'intégrité des descendants. Les créations et réconciliations de collections
  conservent donc prudemment le parent et signalent
  `workspace_folder_nextcloud_rollback_ownership_unverified` au lieu d'un
  DELETE récursif ;
- F10 confirmée : aucune migration, queue, retry, listing, GET de preuve,
  journal externe ou synchronisation générale n'est nécessaire.

Les fakes stateful traversent les runtimes réels et conservent la représentation
distante : version créée encore courante supprimée conditionnellement, version
différente préservée, ETag absent ou hors borne sans DELETE, `404` distingué,
transport ambigu sans faux succès, chemin Documents existants protégé et
collections MKCOL conservées. Les 191 tests ciblés et contrats serveur passent,
dont l'append Notes voisin et les suppressions utilisateur. Une mutation
remplaçant temporairement le DELETE conditionnel Documents par l'ancien DELETE
générique remet la preuve V2 en échec ; la restauration exacte la rend de
nouveau verte.

**Correction résiduelle du 4 septembre 2026 :** la garde initiale bornait la
valeur à 512 caractères sans valider la grammaire de l'entity-tag. Elle laissait
donc `*`, un ETag faible, une liste ou une valeur non citée atteindre
`If-Match`, ce qui ne prouvait pas la propriété de la version créée. Les quatre
clients exigent désormais positivement un unique ETag fort : guillemets doubles
exacts, seuls caractères `etagc` HTTP autorisés, longueur totale maximale 512,
valeur conservée octet pour octet. Toute autre forme devient
`ownership_unverified` avant transport, sans fallback vers le DELETE générique.
Les classifications `404`, `412` et transport, ainsi que les suppressions
utilisateur séparées, restent inchangées. La matrice dédiée traverse les quatre
clients réels avec transport synthétique ; une mutation permissive laissant
passer `*` remet la preuve de refus en échec et la restauration exacte la rend
verte.

**Fermeture :** F08 est corrigé et prouvé. L4 est fermé. L5 n'est pas commencé.

## 7. L4 — Conserver les analytics dérivées si leur source est illisible

**Finding : F21, reproduit hermétiquement dans l'audit source.**

**Objectif :** un échec de lecture des événements sources produit un statut
d'erreur, mais ne remplace pas une projection analytics précédemment disponible
par des faits vides.

**Preuve attendue :** faits dans et hors fenêtre, lecture source en échec :
aucun DELETE ni remplacement des faits/buckets ; statut d'échec conservé.
Lecture suivante saine : reconstruction nominale possible. Aucun événement
source, métrique ou surface supplémentaire.

**Revalidation et fermeture du 4 septembre 2026 :**

- F1 à F5 confirmés : la lecture de `chat_log_events` précède et reste distincte
  des lectures de facts persistés ; son exception construisait trois listes
  vides puis appelait le writer nominal, qui supprimait le fact dans la fenêtre,
  sa synthèse et les buckets affectés avant de committer un statut `error`, alors
  que le fact hors fenêtre survivait ;
- F6 confirmée : l'upsert déjà présent de
  `dashboard_materialization_status` est extrait une seule fois et réutilisé
  dans une transaction status-only, sans nouvelle table ni second pipeline ;
- F7 confirmée : runtime et read-models conservent leur contrat ; le runtime ne
  consomme que le statut retourné et les surfaces lisent facts, summaries et
  buckets persistés séparément ;
- F8 confirmée : la lecture saine suivante réutilise le writer nominal, remplace
  la fenêtre et restaure un statut sain sans migration ni rattrapage spécial.

La fake relationnelle suit désormais l'état committé des facts, summaries,
buckets et du statut. Elle prouve sur échec source l'absence de tout SQL mutateur
sur les trois tables analytics, la préservation des états dans et hors fenêtre,
et l'upsert content-free du seul statut. Elle couvre aussi l'échec de cet upsert
sans faux succès ni mutation analytics, la reprise saine, et la lecture saine à
zéro ligne qui conserve le remplacement nominal. Une mutation rétablissant
temporairement le passage de l'objet vide au writer destructif remet la preuve
centrale en échec ; la restauration exacte la rend verte.

**Fermeture :** F21 est corrigé et prouvé. L5 n'est pas commencé.

## 8. L5 — Atomicité des écritures Workspace

L5 est une famille de trois micro-lots successifs. Ils partagent la notion de
cohérence entre état local, fichier distant et metadata, mais ne doivent pas
être corrigés dans un seul patch.

### L5.1 — OCR : fichier, hash et ligne SQL cohérents

**Finding : F13b.** Une sauvegarde concurrente ne doit pas laisser les bytes,
le hash DB et le dérivé en désaccord. Revalider l'ordre fichier/SQL, le temporaire
commun par PID et le rollback. Correction attendue : sérialisation par cible,
temporaire unique et compensation conditionnelle ; aucun verrou global.

**Revalidation et fermeture du 4 septembre 2026 :**

- F1 à F5 confirmés : le store fermait sa première transaction après lecture de
  la cible, remplaçait le fichier avant l'UPDATE SQL, puis restaurait V0 sans
  condition si cette seconde transaction échouait. Deux sauvegardes recouvrantes
  pouvaient donc laisser la ligne et son hash sur V2 tout en remettant V0 sur
  disque ;
- F6 confirmée : le re-OCR d'un dérivé existant et la correction humaine passent
  tous deux par `update_workspace_text_file()` ; la création initiale conserve
  son chemin distinct à identifiant neuf ;
- F7 confirmée : un `SELECT ... FOR UPDATE` sur la ligne `workspace_files`
  sérialise la cible exacte avant lecture de V0 et reste dans l'unique transaction
  jusqu'au commit ou à la fin de la compensation. La suppression de ce même
  fichier prend le même verrou avant l'effacement. Deux lignes distinctes restent
  indépendantes ; aucun verrou global ni registre process-local n'est ajouté ;
- F8 confirmée : chaque écriture utilise un temporaire unique créé dans le
  répertoire de la cible, puis un remplacement atomique et un nettoyage
  systématique ;
- F9 confirmée : après échec SQL, V0 n'est restaurée que si les octets courants
  égalent encore exactement la candidate écrite par l'opération fautive. Une V0
  absente ou illisible arrête la sauvegarde avant remplacement ; une compensation
  impossible ne produit jamais de faux succès ;
- F10 confirmée : aucune migration, table, route, vue, queue, retry, journal,
  version persistante ou capacité OCR supplémentaire n'est nécessaire.

La fake SQL transactionnelle et le stockage temporaire hermétique orchestrent
sans `sleep` A en attente d'échec, B sur la même cible, deux cibles distinctes,
un writer déjà committé, une suppression concurrente et les branches de panne.
Ils inspectent les octets finaux ainsi que taille, SHA-256 complet/court et
metadata SQL. Une mutation retirant `FOR UPDATE` remet la preuve centrale en
échec parce que B n'attend plus A ; sa restauration exacte la rend verte.

Cette cohérence applicative n'est pas une transaction distribuée entre le
filesystem et PostgreSQL : un arrêt brutal du processus, du conteneur ou de
l'hôte entre le remplacement du fichier et le commit/rollback SQL peut encore
laisser un état à réconcilier. L5.1 n'ajoute volontairement ni journal durable ni
versionnage pour couvrir ce cas de crash.

**Fermeture :** F13b est corrigé et prouvé. L5.1 est fermé. L5.2 et L5.3 ne sont
pas commencés.

### L5.2 — Renommage de dossier : commit local et MOVE distant cohérents

**Finding : F14a.** Distinguer échec du commit et échec de relecture/projection.
Après commit local B, une erreur de GET ne doit pas remettre le distant en A et
laisser les deux autorités divergentes.

**Décision et clôture L5.2 :** la mutation locale est devenue auto-suffisante.
Le `UPDATE ... RETURNING` est encapsulé dans une CTE qui joint la liaison
Nextcloud dans la même transaction. La projection complète est sérialisée et
validée avant `commit()` ; après retour normal du commit, elle est retournée
directement, sans second GET.

- F1 confirmée : le `RETURNING` fournissait déjà la ligne dossier mutée avant
  commit ;
- F2 confirmée : l'ancien chemin committait avant d'ouvrir une seconde connexion
  de relecture ;
- F3 confirmée : une panne de ce GET retournait le même `None` qu'un échec
  antérieur au commit ;
- F4 confirmée : le runtime de renommage interprétait ce `None` comme un échec
  local et exécutait le MOVE inverse puis la restauration de la liaison ;
- F5 confirmée et reproduite : la ligne dossier restait en B alors que la
  liaison et la cible distante revenaient en A ;
- F6 confirmée : la CTE transactionnelle fournit la ligne dossier et sa liaison
  à la sérialisation avant commit ;
- F7 confirmée : les updates locaux d'icône, description et ordre conservent la
  liaison persistante complète et ne fabriquent pas un état `local_only` ;
- F8 confirmée : échec d'UPDATE, projection absente/invalide ou échec de commit
  ne produisent aucun succès et conservent la compensation distante existante ;
- F9 confirmée : aucun schéma, migration, route, écran, retry, journal, queue ou
  accès Nextcloud réel n'est ajouté.

La preuve relationnelle hermétique traverse le store et l'orchestrateur réels
avec un client distant stateful. Sous l'ancien code, elle observe après le
commit B le triplet incohérent ligne B / liaison A / distant A. Le correctif
conserve ligne B / liaison B / distant B et n'exécute aucun MOVE inverse. Les
contre-cas couvrent les échecs d'UPDATE et de commit avant confirmation, le MOVE
initial, l'upsert de liaison, les updates locaux liés, la projection invalide et
le dossier supprimé. Une mutation réintroduisant le GET post-commit remet
exactement la preuve centrale en échec ; la restauration du correctif la rend
verte.

Ce correctif ne constitue pas une transaction distribuée avec Nextcloud. Une
perte de connexion pendant `COMMIT` laisse une ambiguïté incompressible entre
commit refusé et commit accepté dont l'accusé de réception est perdu. La lever
exigerait un état durable ou un protocole explicitement hors du périmètre L5.2.

**Fermeture :** F14a est corrigé et prouvé. L5.2 est fermé. L5.3 n'est pas
commencé.

### L5.3 — Image supprimée : terminer le tombstone après DELETE réussi

**Finding : F19b.** Après DELETE distant confirmé puis échec DB, un retry doit
pouvoir terminer le tombstone lorsque l'absence de la cible enregistrée est
confirmée. Ne pas confondre 404 prouvé, panne de transport et cible différente.

**Revalidation initiale et correction du 4 septembre 2026 :**

- F1 et F2 confirmés : le chemin nominal supprimait d'abord la cible distante,
  puis tentait le tombstone ; un 2xx suivi d'un échec SQL laissait la ligne
  locale active alors que la cible était absente ;
- F3 confirmée : au retry, le service relisait la même cible durable mais
  imposait `missing_ok=False`, de sorte que le 404 interrompait le flux avant
  toute nouvelle tentative de tombstone ;
- F4 confirmée : le client conserve le statut HTTP exact du DELETE et distingue
  cette réponse d'une panne transport sans requête supplémentaire ;
- F5 confirmée : l'identifiant, le dossier, la cible interne et `target_ref`
  proviennent de la ligne durable et passent les validateurs Generated Images ;
- F6 confirmée : l'ancien `UPDATE` ne portait que l'identifiant de l'image ;
- F7 partiellement confirmée par le premier correctif : le tombstone vérifiait
  l'image, le dossier, la cible interne, `target_ref`, l'absence de tombstone et
  les états encore `available` / `linked`, mais pas encore la coordonnée
  distante durable du dossier parent ;
- F8 confirmée : le chemin 2xx conserve l'état `deleted` et le reason code
  nominal, tandis que le 404 exact produit l'état
  `remote_already_missing` et le reason code fermé
  `folder_generated_image_remote_already_missing`, puis emprunte le même
  tombstone conditionnel ;
- F9 confirmée : aucun schéma, migration, route, vue, GET/PROPFIND, listing,
  retry automatique, journal, queue ou accès Nextcloud réel n'est ajouté.

La preuve stateful hermétique traverse le service, le client DELETE réel et le
store SQL avec une fake relationnelle. Elle observe successivement le 204, la
panne du premier tombstone, le 404 au retry, puis la ligne locale `deleted`.
Elle vérifie aussi qu'une cible changée entre le 404 et l'UPDATE retourne zéro
ligne et aucun succès, et qu'un troisième appel sur la ligne tombstonee ne
relance pas WebDAV. Une mutation rétablissant temporairement
`missing_ok=False` remet le retry central en échec 502 ; sa restauration exacte
rend de nouveau la preuve verte.

**Contre-audit résiduel et refermeture du 4 septembre 2026 :**

- C1 à C4 confirmées : le DELETE combine la cible du dossier parent et celle de
  l'image ; le premier `WHERE` ignorait le lien parent et un MOVE pouvait déjà
  avoir déplacé l'image alors que l'ancienne liaison restait `linked` ;
- C5 et C6 confirmées : l'état existant `sync_pending` sert de barrière durable
  avant MOVE ; son acquisition est conditionnée au lien encore `linked` et aux
  ref/hash observés. Le tombstone exige dans la même transaction un lien parent
  encore `linked` avec les mêmes `nextcloud_folder_ref` et
  `nextcloud_name_hash`, sans verrou SQL pendant WebDAV ;
- C7 confirmée : sans renommage, le retry `204`, échec SQL, puis `404` conserve
  le tombstone légitime ;
- le MOVE n'est lancé qu'après commit de la barrière. Une réponse HTTP certaine
  du MOVE initial tente seulement le CAS de la même identité `sync_pending` vers
  `sync_error`; si cette transition locale échoue, `sync_pending` reste la
  position sûre. Une panne transport d'issue ambiguë conserve elle aussi
  honnêtement `sync_pending`. Aucun de ces chemins ne réaffirme l'ancienne
  coordonnée `linked` sans preuve positive ;
- seule la réussite effective du MOVE inverse autorise la restauration
  `linked`, elle-même conditionnée à l'état, à la ref et au hash encore attendus,
  afin de ne pas écraser une liaison concurrente ;
- les fenêtres « renommage déjà durable en B » et « MOVE effectué avant liaison
  finale B » retournent toutes deux un échec borné, sans tombstone ni succès.

La preuve relationnelle stateful interprète réellement le `EXISTS` parent du
SQL et conserve séparément la cible distante. La mutation qui retire seulement
cette précondition rétablit le faux HTTP 200 sur la course centrale ; la
restauration exacte du `WHERE` rend la preuve verte. La preuve résiduelle de
renommage place déjà la cible sous B, reçoit 404 sur le MOVE A vers B, puis
vérifie que A n'est jamais réinscrit `linked` et que l'image sous B ne peut pas
être tombstonée via A. Réintroduire l'ancien upsert de restauration rend cette
preuve rouge.

Le 404 prouve uniquement l'absence de la coordonnée distante complète au moment
du DELETE, pas la date ni l'auteur de cette absence. Cette séquence ne constitue
pas une transaction distribuée : un crash brutal entre DELETE et tombstone peut
encore laisser une divergence, refermable par le retry borné si les identités
durables de l'image et du parent n'ont pas changé.

**Fermeture de L5 :** F19b, y compris sa coordonnée distante parent, est corrigé
et prouvé. L5.3 est refermé et L5 reste fermé. Chaque sous-lot possède sa preuve
rouge/verte, sa livraison et son statut. Aucun protocole générique de transaction
externe n'est ajouté. L6 n'est pas commencé.

## 9. L6 — Justesse produit directement perceptible

L6 se traite feature par feature. Un sous-lot ne donne jamais implicitement le
GO au suivant.

### L6.1 — Sortie assistant et code autorisé — F05

Préserver exactement le corps des fences autorisées (`_`, `*` et autres
caractères légitimes) sans relâcher la doctrine générale de forme. Vérifier
séparément le cas secondaire du terminal serveur vide et du fallback UI
`reply || assistantText` ; ne le corriger que s'il est reproduit.

**Statut : fermé — F05 corrigé et raccord frontend secondaire corrigé après
reproduction.** Le plan de référence est resté le plus simple et le plus sûr :
suivre l'entrée et la sortie de fence avec la longueur de son délimiteur, rendre
opaques les seules lignes de corps lorsque `allow_code=True`, et conserver les
traitements existants sur les fences et la prose extérieure. Aucun changement
de doctrine, prompt, modèle, provider, schéma, route, store ou protocole n'a été
nécessaire.

**Revalidation H1–H7.** H1 est confirmé : chaque ligne du corps autorisé passait
dans `_strip_inline_markdown()` et perdait notamment `_`, `*` et `__name__`.
H2 est confirmé : le seul témoin autorisé `print("hello")` ne sollicitait aucun
caractère destructible, aucune indentation ni prose mixte. H3 est confirmé : la
frontière correcte est le corps entre délimitations, tandis que titres,
blockquote, règle, gras et italique extérieurs conservent leur normalisation.
H4 est confirmé et préservé : sans autorisation, délimitations et corps restent
retirés, y compris blocs vides, multiples et non fermés ; le stream structuré
emprunte lui aussi cette normalisation finale. Détection de demande et garde
système sont inchangées. H5 est confirmé comme exigence, avec un écart stream
additionnel revalidé : `allow_code=True` désactivait le buffer existant et
contournait ainsi la normalisation finale de la prose. Tous les streams texte
brut sont désormais bufferisés par le mécanisme existant ; JSON, texte terminal,
message persistant et dérivation post-save partagent le même canon. H6 est
confirmé en Chromium : le parser et `sendToServer()` respectaient bien
`final_text: ""`, puis le submit rétablissait le brouillon avec `reply ||
assistantText`. Le submit consomme maintenant la chaîne retournée telle quelle,
affiche `"(vide)"` sans fabriquer de canon et, comme le serveur réel, ne met
aucun message assistant vide en cache. H7 est confirmé.

**Rouge, correction et mutation.** Avant patch, le témoin central produisait
`foobarbaz = a  b  c` et `return name, ...`; la traversée route échouait en JSON
sur ce canon altéré et en stream sur la prose Markdown non normalisée. Le
scénario navigateur `brouillon non vide -> done(final_text="")` conservait
`Brouillon visible`. La correction conserve les lignes de code et leurs lignes
vides, exige une fermeture au moins aussi longue que l'ouverture, limite la
compression des blancs à la prose, et préserve la normalisation CRLF existante
par retrait des `\r`. Une mutation contrôlée réappliquant temporairement
`_strip_inline_markdown()` au corps autorisé a remis le témoin central au rouge ;
sa restauration exacte l'a remis au vert.

**Preuves.** Les tests ciblés couvrent le corps Python demandé, indentation,
prose avant/après, CRLF, fences vides/non fermées/multiples, imbriquées ou
indentées, fausses fermetures contenant du texte, retrait strict des blocs
interdits même en stream structuré, segmentation de chunks, routes JSON et
stream, terminal, persistance et dérivations. Le voisinage passe avec `68`
tests Python, `15` tests Node du
parser/état streaming et `17` scénarios Chromium, sans provider, DB opérateur ni
réseau. Presence, final lock, interruptions et échecs de persistance restent
verts. Limite honnête : ces preuves synthétiques établissent
le contrat applicatif et non la fréquence de sorties concernées chez un
provider réel. Lors de cette fermeture, L6 restait ouvert et L6.2 n'était pas
commencé.

### L6.2 — Réponses asynchrones rattachées à leur sélection — F10

Après un `await`, revalider l'identité ou l'époque de la requête avant d'appliquer
la réponse. Couvrir chat threads, documents actifs, dashboard et logs avec le
plus petit helper déjà compatible ; aucun nouveau store frontend.

**Statut : définitivement refermé — F10 corrigé sur les quatre familles
confirmées, y compris la fenêtre résiduelle Logs.** Aucun plan plus simple et
plus sûr ne fournit la même garantie : chaque contrôleur conserve un compteur
monotone local par famille indépendante et refuse succès et erreur si une
requête plus récente ou une autre sélection l'a remplacée. Pour les trois
loaders Logs dépendant des filtres visibles, cette identité est désormais la
signature normalisée exacte de conversation, tour, stage, statut, limite et
offset. Les requêtes ne sont pas annulées et aucun store, helper transversal,
`AbortController`, endpoint, payload ou état produit n'est ajouté.

**Revalidation F1–F7.** F1 est confirmée : une hydratation lente du fil A
rendait ses messages après le fil B. F2 est confirmée avec sa nuance : le cache
indexé par conversation peut recevoir A, mais seul le fil encore sélectionné
peut rendre ou changer son statut. F3 est confirmée : un `refresh()` tardif de
documents actifs remplaçait ou vidait la liste de B. F4 est confirmée pour les
trois étages dashboard : période, conversation et inspection de tour. F5 est
confirmée pour les familles indépendantes metadata, métriques, tours et
événements des logs. F6 est confirmée : les `catch` tardifs pouvaient effacer
une vue valide ou afficher un faux échec. F7 est confirmée : des gardes locales
suffisent, sans backend, API, schéma ni persistance.

**Rouge et correction.** Des promesses différées contrôlées ont imposé, sans
temporisation arbitraire, la séquence A démarré, B sélectionné et résolu, puis A
résolu ou rejeté. Avant correctif, le chat rendait successivement `message-b`
puis `message-a` et l'erreur A remplaçait le statut de B ; les documents de A
remplaçaient ceux de B ou une erreur A vidait B ; le dashboard ancien vidait la
période courante ; les logs anciens remplaçaient statut et données visibles.
Les gardes sont présentes après chaque attente qui précède une mutation, dans
les branches de succès et d'erreur. Le chat combine époque et conversation
courante ; les documents combinent époque et endpoint dérivé de la conversation
courante ; le dashboard sépare chargement global, conversation et inspection ;
les logs séparent metadata, métriques, tours et événements afin qu'une famille
n'invalide pas les autres.

**Preuves et limites.** Les tests réels des contrôleurs couvrent succès et erreur
périmés, erreur courante, deux chargements normaux successifs d'une même
sélection et cache de fil indexé par conversation. Les scénarios Chromium
couvrent période/conversation/tour du dashboard, filtres/metadata/données des
logs, pagination nominale, chat nominal et documents actifs rendus. Une mutation
contrôlée neutralisant la garde du fil remet les deux scénarios A/B au rouge ;
la restauration exacte les remet au vert. Les suites ciblées passent avec `24`
tests Node et `6` scénarios Chromium, plus `node --check` sur chaque JavaScript
modifié. La preuve est synthétique et déterministe ; elle n'évalue pas la
fréquence des courses en usage réel. L6 reste ouvert et L6.3 n'est pas commencé.

**Réouverture et preuve résiduelle au HEAD
`5896de156fb516f66973a1df93be1f60458d837e`.** La première fermeture laissait
une fenêtre confirmée dans les logs : après sélection de B, le handler attendait
`loadMetadata(B)` avant de démarrer les loaders B ; pendant cette attente,
l'epoch des requêtes A restait courant et leur réponse pouvait encore modifier
la vue. Une reproduction Chromium sans temporisation arbitraire maintient la
metadata B en attente, puis résout ou rejette A avant tout chargement B. Avant
correction, le succès A remplaçait le statut et les événements visibles.

Le correctif local combine désormais epoch de famille et signature des filtres
ayant produit la requête dans `loadLogs()`, `loadCockpitMetrics()` et
`loadTurnPipeline()`, après chaque attente et dans chaque `catch`. La preuve
compare DOM, statut et compteurs avant/après les succès et erreurs A, puis
vérifie B, le rafraîchissement et la pagination avant/arrière. Le test Node
prouve que les six champs participent à une signature stable. Une mutation
retirant seulement la signature de `loadLogs()` remet la preuve centrale au
rouge ; sa restauration exacte la remet au vert. Aucun autre contrôleur, contrat
ou statut global ne change. L6.3 reste non commencé.

### L6.3 — Agenda : preuve de lecture et erreurs bornées — F12a/F12b

Exiger la lecture requise par la méthode avant de rendre une absence d'événements.
Normaliser timeouts, erreurs requests et XML invalide à la frontière Agenda
existante afin qu'une panne de lane ne devienne pas un échec global du chat.
Ne pas masquer une absence de REPORT et ne pas ajouter de regex d'intention.

**Revalidation au HEAD `28bb7b7afb1c000c727123c061f63822e7808f73`.**
F12a est confirmé : la validation exigeait seulement un outil allowlisté ; un
plan de fenêtre limité à `calendar_list` pouvait donc finir avec `status=ok`,
`events=()` et produire une réponse d'absence sans `REPORT`. Une résolution de
calendriers vide suivait le même chemin trompeur. F12b est confirmé :
`requests.exceptions.Timeout`, les autres `RequestException` et
`ElementTree.ParseError` sortaient du transport/client, au-delà des exceptions
bornées par l'exécuteur Agenda, et pouvaient faire échouer le chat entier.

**Décision et correctif.** Le plan le plus simple et le plus sûr reste dans les
frontières existantes : déclarer les outils requis avec la méthode produit,
les contrôler dans la validation et l'exécution, puis autoriser un résultat
vide seulement si une observation de lecture réussie correspond exactement au
`time_scope` normalisé et porte au moins un calendrier résolu. L'absence de
calendrier devient `agenda_readonly_no_calendar_resolved`; une preuve manquante
reste une erreur bornée. Le transport normalise timeout et erreur `requests` et
le client normalise le XML invalide avec des reason codes fermés et
content-free. Le raccord et les final locks Agenda existants restent l'unique
pipeline. `KeyboardInterrupt` et `SystemExit` ne sont pas capturés.

**Preuves et limites.** Le rouge initial reproduit l'acceptation
`calendar_list` seule, la fausse absence sans calendrier et la fuite des trois
familles d'exception. Les tests ciblés prouvent le refus avant client, le
contre-cas `REPORT` vide honnête, les trois erreurs au vrai transport/client et
au raccord `/api/chat`, la survie HTTP du chat, le final lock d'erreur, le
succès nominal, les final locks voisins, l'absence de mutation et
l'observabilité content-free. Deux mutations contrôlées, sur la garde centrale
d'absence puis sur la normalisation transport, remettent les preuves au rouge;
leur restauration exacte les remet au vert. Les preuves restent synthétiques
et hermétiques : aucun provider, CalDAV réel, DB opérateur, JavaScript ou
Chromium n'a été sollicité. F12c et L6.4 ne sont pas commencés.

### L6.4 — Agenda : récurrences extrêmes — F12c, diagnostic préalable

Reproduire ou invalider le dépassement YEARLY/INTERVAL avant tout patch. Si le
mécanisme est confirmé, borner l'expansion par COUNT et fenêtre demandée sans
ajouter de famille de récurrence. Si aucun contre-exemple contractuel n'existe,
fermer comme invalidé avec la preuve.

**Statut : fermé — F12c corrigé.**

**Revalidation au HEAD `3cccab294f665e5cb7beaa8899cde8f537936f2a`.**
F1 est confirmée : `_period_starts()` matérialisait entièrement une liste avant
que sa boucle appelante ne voie une période. F2 est confirmée : `COUNT=1`,
`UNTIL` limité à la première occurrence et une fenêtre d'un jour provoquaient
chacun la préparation préalable. F3 est confirmée :
`FREQ=YEARLY;COUNT=1;INTERVAL=2`, à partir de 2026, atteignait l'année 10000 et
levait une `ValueError` avant de rendre l'occurrence initiale. F4 est confirmée
par le chemin `CalDavReadClient -> parse_event_report() -> parse_ics_events()
-> expand_recurrence_starts()` réellement exécuté par `event_query_range`.
F5 est confirmée : rendre `_period_starts()` paresseux suffit, sans modifier le
parseur ni les familles RRULE. F6 est confirmée : `COUNT` doit continuer de
compter les candidats conformes après filtres, y compris lorsque des périodes
n'en produisent aucun ou en produisent plusieurs. F7 est confirmée : la limite
de 512 occurrences reste la garde contre une fenêtre produisant trop de
résultats, distincte de la borne interne de périodes.

**Décision et correctif.** Le plus petit correctif conserve la frontière et la
borne existantes : `_period_starts()` devient un itérateur, avance seulement
lorsque le consommateur demande une période suivante, et traduit une sortie du
domaine `datetime` en `IcsRecurrenceUnsupportedError` content-free. La boucle
existante arrête alors l'itération dès que `COUNT`, `UNTIL`, la fin de fenêtre
ou le plafond d'occurrences le permet. `read_execution` classe l'erreur fermée
dans le reason code existant `agenda_readonly_tool_error`; aucun nouveau statut,
outil, pipeline, cache, dépendance ou support RRULE n'est ajouté.

**Preuves et limites.** La reproduction hermétique comptait 3 987 avancées
avant la `ValueError` du cas YEARLY extrême, et 6 144 avancées pour chacun des
contre-cas sûrs `COUNT`, `UNTIL`, fenêtre courte et `COUNT` épuisé avant la
fenêtre. Après correction, le premier cas rend l'occurrence initiale sans
avancement ; `UNTIL` s'arrête sans avancement, la fenêtre quotidienne après un
avancement et `COUNT=2` épuisé avant la fenêtre après un avancement avec `[]`.
Les tests couvrent aussi les filtres `BY*`, les périodes vides du 29 février,
les candidats multiples, les overrides ICS, le plafond de 512 et la
classification d'erreur Agenda. Une mutation contrôlée rematérialisant les
périodes remet la preuve YEARLY centrale au rouge ; l'empreinte identique avant
et après restauration prouve le retour exact au correctif. Les preuves restent
synthétiques et sans provider, CalDAV réel, DB opérateur, JavaScript ou
Chromium. L6.5 n'avait pas été commencé par ce sous-lot.

### L6.5 — Web : requête pertinente et source réellement officielle — F15a/F15b

Retirer ou dériver du sujet réel le gabarit AI Act hors sujet. Comparer les
sources à partir du host/path parsé plutôt que d'une sous-chaîne de l'URL
complète. Conserver budgets, profils et reranking existants.

**Statut : fermé — F15a et F15b corrigés.**

**Revalidation au HEAD `3b0bfcfb637cb69f1bc052ca1ae7a888840cfb5d`.**
F1 et F2 sont confirmés : les marqueurs larges `europe`, `ia` ou `regulation`
activaient un gabarit fixe AI Act ; « actualités du football en Europe »
produisait donc `AI Act intelligence artificielle Europe 2026
site:ec.europa.eu`. F3 est confirmé : les deux secondaires peuvent être
dérivées du `primary_query`; une demande AI Act le conserve naturellement
dans chacune. F4 et F5 sont confirmés : source-first et profile policy
acceptaient une occurrence attendue dans l'URL complète, y compris query,
fragment, chemin tiers ou suffixe de chemin sans frontière. F6 est confirmé :
les signaux docs-like et le bonus documentaire lisaient eux aussi l'URL brute.
F7 est confirmé : `hostname` et `path` parsés préservent domaines exacts,
sous-domaines, `.gouv.fr`, `.europa.eu`, `.edu` et `ac-*.fr`, avec une frontière
de segment pour les chemins. F8 est confirmé : budgets, profils, ordre souple,
reason codes et champs d'observabilité n'ont pas besoin de changer.

**Décision et correctif.** `_actualite_queries()` ne contient plus d'entité
fixe et compose ses deux candidats depuis le sujet primaire, sans nouvelle
heuristique sémantique. La comparaison URL est mutualisée dans la seule policy
existante : schéma HTTP(S), `hostname` normalisé en casse, sans `www.` ni point
terminal, et `path` borné par segment. Query, fragment, userinfo et
`source_domain` ne participent plus à l'identité de classement ; une URL
absente ou invalide reste neutre. Le reranker réutilise cette comparaison pour
source-first et ne nourrit plus ses signaux textuels ou documentaires avec
l'URL brute. Aucun chemin permissif concurrent n'est conservé.

**Preuves et limites.** Les reproductions rouges couvraient football/Europe,
le contre-cas AI Act, un domaine officiel caché dans query, fragment, userinfo
ou chemin tiers, `openrouter.ai.evil.test`, `/docs-evil`, un hostname officiel
réel et un `source_domain` contradictoire. Après correction, les quatre suites
ciblées query plan, source-first, profile policy et reranking passent `63/63` ;
deux tests de composition Web existants portent la preuve totale à `65/65`.
Une mutation rétablissant le gabarit fixe remet le cas football au rouge ; une
mutation rétablissant la recherche de sous-chaîne remet le faux domaine
officiel au rouge. Les preuves sont hermétiques, sans provider, SearXNG,
Crawl4AI, réseau, DB opérateur, JavaScript ou Chromium. L6.6 n'est pas commencé.

**Contre-audit résiduel au HEAD
`77141c31d6d0de39462be3debff45bd5dda25dda`.** Une divergence restait possible
avant `urlparse()` : un antislash ou un caractère ASCII C0/DEL pouvait être
interprété différemment par le client HTTP et par l'identité de classement,
jusqu'à faire passer un hôte tiers pour `openrouter.ai/docs`. Le prédicat
lexical déjà porté par la garde d'URL publique est désormais mutualisé et
appliqué à la valeur brute avant toute suppression ou parsing. Ces URL n'ont
plus d'identité de classement, restent neutres malgré `source_domain`, titre ou
contenu flatteurs, et ne reçoivent aucun bonus source-first, officiel ou
documentaire. Les URL HTTP(S) légitimes gardent leur identité ; la garde de
crawl et le classement rejettent les mêmes formes ambiguës. Cette correction
reste un défaut de classement F15b, sans nouveau finding SSRF, politique,
dépendance ou normalisation réparatrice. Les suites ciblées query plan,
source-first, profile policy, reranking, garde d'URL publique et deux tests de
composition passent `77/77`, sans réseau. L6.6 reste non commencé.

### L6.6 — ODT : préserver les séparateurs textuels — F19a

Interpréter dans l'extracteur existant les éléments ODT d'espace, tabulation et
saut de ligne afin de ne pas concaténer des mots. Ne pas prétendre garantir la
fidélité universelle de tout ODT.

**Statut : fermé — F19a corrigé.**

**Revalidation au HEAD `5162f539b9e6f73b4079d23c2bc5446810c25551`.**
F1 est confirmé et reproduit : `Element.itertext()` ignore les éléments vides
`text:s`, `text:tab` et `text:line-break`, et concaténait donc le texte qui les
précède avec leur `child.tail`.
F2 est confirmé : l'upload de document actif accepte le résultat `complete` et
active ce texte ; l'ingestion workspace en conserve taille/hash, puis la
sélection explicite relit le même extracteur avant injection. F3 est confirmé :
un parcours récursif local `node.text`, enfants, `child.tail` conserve l'ordre
des spans/liens imbriqués sans parseur ODT général. F4 est confirmé par
OpenDocument 1.3 : `text:s` vaut un espace sans `text:c`, dont le type est
`nonNegativeInteger`; les valeurs malformées ou l'expansion explicite
déraisonnable doivent échouer fermées. F5 est confirmé : le dispatch des
formats, la normalisation finale, les statuts et les métadonnées sont communs
après le parseur et n'ont pas besoin de changer.

**Décision et correctif.** Aucun plan plus simple et plus sûr n'offre moins
d'effets de bord. `_extract_odt_text()` remplace son unique `itertext()` par un
parcours ordonné borné aux paragraphes/headings existants. Seuls les trois tags
du namespace texte ODF exact sont interprétés : espace répété selon `text:c`,
tabulation et saut de ligne. Le compteur accepte la forme XML Schema
non négative, compare sa valeur avant conversion/multiplication et partage sur
tout le document un budget maximal de `40 MiB` d'espaces explicites. Une valeur
malformée ou un dépassement lève une erreur interne traduite par la frontière
existante en `parse_error`, texte vide et métadonnées complètes absentes.

**Preuves et limites.** Les tests rouges couvraient les trois séparateurs seuls
et combinés, `text:c` absent/valide/zéro/malformé/excessif, tails, span et lien
imbriqués, heading, plusieurs paragraphes, namespace étranger, ODT historique,
entrée invalide et traversée réelle de l'upload actif. Après correction, les
quatre suites ciblées extracteur, upload/OCR voisin, ingestion et sélection
passent `67/67` dans le runner hermétique, checkout read-only, réseau coupé et
`/tmp` en tmpfs. Une mutation rétablissant `itertext()` remet les quatre
sous-cas centraux au rouge ; la restauration retrouve exactement l'empreinte
du correctif. Le contre-audit confirme que ce `itertext()` était unique dans
la frontière Documents, que DOCX/PDF/TXT/MD, normalisation, statut `complete`,
taille/hash/tokens, logs et projections gardent leur wiring. Le lot ne promet
ni fidélité ODT universelle ni validation complète du schéma, et n'ajoute
aucune dépendance, route, télémétrie, format ou capacité produit. L6.7 n'est pas
commencé.

### L6.7 — Décisions conditionnelles — F13a et F14b

- **F13a :** établir d'abord si ré-OCR doit contractuellement remplacer un
  dérivé humain. Si oui, corriger uniquement le libellé création/mise à jour et
  l'avertissement nécessaire ; sinon cadrer séparément le changement produit.
- **F14b :** distinguer état courant et historique seulement si une surface ou
  une API affirme encore à tort qu'un document exclu est actuellement prêt ou
  injecté. Conserver l'historique utile.

**Statut : fermé — F13a et F14b corrigés ; L6 fermé ; L7 non commencé.**

**Revalidation au HEAD `1c6b88d720092e998f79f03e8757750a99232843`.**
L'hypothèse 1 est confirmée : le premier OCR crée le dérivé et retourne `201`,
tandis que la ré-OCR retrouve le même `source_file_id`, appelle
`update_workspace_text_file()` et retourne `200`. L'hypothèse 2 est confirmée :
l'édition humaine appelle elle aussi cette frontière de mise à jour ; la ré-OCR
suivante remplace donc réellement les corrections du même Markdown.
L'hypothèse 3 et l'hypothèse 4 sont confirmées : le frontend annonçait toujours
« créé », sans avertissement, alors que `Response.status` et les métadonnées
déjà listées `source_kind=ocr_derived`
et `source_file_id` suffisent sans modifier l'API. L'hypothèse 5 est confirmée :
une injection efface l'exclusion précédente ; une exclusion conserve l'ancien
`last_injected_turn_id` et renseigne les deux champs d'exclusion. L'hypothèse 6 est
confirmée : `build_usage_projection()` donnait priorité à cet identifiant
historique et fabriquait `readable/ready` malgré la décision d'exclusion
courante. L'hypothèse 7 est confirmée : aucun nouvel état durable, endpoint,
écran, champ, événement, table ou workflow n'est nécessaire.

**Décision et correctif.** Aucun plan plus simple et plus sûr n'offre moins
d'effets de bord. Avant une ré-OCR, le contrôleur recherche dans la liste déjà
chargée le dérivé actif de la même source et utilise la confirmation native
existante pour annoncer que le Markdown OCR actuel, corrections manuelles
comprises, sera remplacé. Une annulation s'arrête avant le POST. Un verrou
process-local par cible neutralise un double clic pendant la requête. Le client
conserve désormais le statut HTTP réel avec le fichier retourné ; le succès
affiche « créé » pour `201`, « mis à jour » pour `200`, et aucun autre statut ne
fabrique un succès. Côté projection, l'existence de l'exclusion est désormais
décidée depuis ses marqueurs durables avant normalisation du motif et prime sur
l'ancien ID d'injection pour `usage_status`, `readiness` et `reason_code`. Un
motif reconnu conserve son mapping ; un motif vide, malformé ou sûr mais non
mappé produit `not_injected/blocked/folder_document_content_redacted`. Les
trois champs historiques restent exposés selon leur normalisation content-free.
L'injection suivante réutilise le contrat store existant qui efface l'exclusion
et restaure `readable/ready`.

**Preuves et limites.** Les reproductions rouges ont établi l'absence de
confirmation, la perte de `Response.status` et la projection fautive
`readable/ready`. Les suites ciblées passent `42/42` côté Node et `48/48` côté
Python hermétique, sans réseau, provider, Stirling, Nextcloud ni DB opérateur.
Elles couvrent premier OCR, ré-OCR après correction humaine, annulation sans
POST, confirmation et double clic bornés à un POST, libellés `201/200`, erreur
sans faux succès, conservation de l'ID injecté historique, reprise après
injection, image/PDF visuel et sélection/désélection. Le scénario Chromium
Workspace ciblé passe `1/1` avec création, avertissement, annulation, mise à
jour et sélection/désélection réelles dans le DOM. Deux mutations contrôlées —
neutralisation de l'avertissement OCR puis subordination de l'exclusion à
l'absence d'injection historique — remettent leurs preuves centrales au rouge ;
leur restauration exacte retrouve les empreintes du correctif. La décision
pré-POST repose volontairement sur le read-model déjà chargé : une autre
surface concurrente peut le rendre caduc entre lecture et POST, mais le statut
serveur final reste la vérité du libellé. Aucun algorithme OCR, stockage,
versionnage, télémétrie ou capacité produit n'est ajouté. L7 n'est pas commencé.

**Correctif résiduel F14b au HEAD
`306c97d3901c017f3a7c3f9f81ed78e03b23c8bb`.** La revalidation a montré que
le premier correctif utilisait le motif déjà normalisé comme preuve d'existence
de l'exclusion : un motif vide ou malformé redevenait donc `readable/ready`, et
un motif syntaxiquement sûr mais non mappé conservait à tort `selected`. Les
reproductions ciblées ont échoué exactement sur ces états. La projection sépare
maintenant l'existence, déterminée par les deux marqueurs bruts durables, du
mapping du motif normalisé. Les tests de projection et de chaîne
sélection/exclusion/injection couvrent aussi l'absence réelle d'exclusion, un
motif valide et la reprise après injection. Aucun champ, helper, état, route,
API ou capacité n'est ajouté ; L7 reste non commencé.

## 10. L7 — Vérité d'API, observabilité et outils historiques

### L7.1 — Agenda pending observable — F16

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`3253a1bd07c4fbd19423cf615ad0b396162a9e43` a confirmé F16 et un second maillon
du même chemin causal : le writer pending émet au top-level `pending_status`,
`pending_confirmation_level` et `pending_risk_flags`, puis dans
`pending_execution` `pending_status`, `confirmation_level` et `risk_flags`,
alors que la projection privilégiait les anciens noms. En outre, la garde
centrale refusait les conteneurs content-free `final_response` et
`pending_execution`; le logger remplaçait donc le payload avant son stockage et
rendait le raccord de projection seul insuffisant.

Le correctif minimal aligne la projection sur les clés writer et conserve les
aliases historiques `pending_action_status`, `confirmation_level` et
`risk_flags`. La garde admet uniquement, pour le schéma exact
`frida_agenda_lot6_pending_v1`, les chemins et types content-free effectivement
produits sous `final_response`, `pending_execution` et
`pending_execution.draft_summary`; `pending_execution.write_execution` doit
rester un mapping vide dans ce payload pending. Il n'existe aucune exemption
générale pour ces conteneurs, les mappings, listes ou clés DAV. Les clés
inconnues, types faux et valeurs sensibles restent refusés, notamment contenu,
draft, titre, lieu, description, UID, ETag, URL/path DAV, ICS/XML, headers et
credentials, y compris imbriqués.

La preuve ciblée traverse un vrai résultat de
`build_lot6_observability_payload()` depuis le writer pending, la garde, le log
store simulé, la projection, `build_admin_observability()` et la route admin
existante. Elle vérifie aussi absence vide, neutralisation des valeurs
invalides, mutations sensibles négatives et absence de contenu brut. Les 62
tests Agenda observabilité/garde/route et voisins immédiats passent dans le
conteneur hermétique existant (`--network none`, checkout monté read-only).
Aucun pending store, comportement de confirmation, product method, accès
CalDAV, frontend, route, schéma DB, champ producteur ou télémétrie n'a changé.
L7.2 n'est pas commencé.

### L7.2 — Conversations : succès, erreur et limite de liste — F17

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`16b86349d935ef4350d2173bfda8c37c92a9a9d7` confirme les trois branches de
F17. `create_conversation()` ignorait le `ConversationSaveResult`, puis son
résumé de repli transformait encore une sauvegarde refusée en réponse `201`.
`conversations_store.list_conversations()` transformait toute exception SQL en
`items=[]`, `total=0`; le service et la route ajoutaient ensuite `ok=true` et
un statut `200`. Enfin, le sidebar demandait une seule page de 200 et jetait
les champs `limit`, `offset` et `total` déjà exposés par l'API.

Le correctif reste sur les contrats existants. Une création ne consulte son
résumé et ne répond `201` qu'après un `ConversationSaveResult.ok=true`; sinon
elle répond `503 conversation_save_failed`, sans conversation synthétique. Le
store de liste distingue maintenant explicitement succès et échec; une panne
SQL remonte jusqu'à `503 conversation_list_failed`, tandis qu'un vide sain
reste `200`, `ok=true`, `items=[]`, `total=0`. Le sidebar accumule les pages de
200 selon `limit/offset/total`, préserve leur ordre et refuse doublon, identifiant
absent, total instable, offset incohérent ou page courte avant le total. Sa
progression doit être strictement monotone et son état n'est remplacé qu'après
chargement complet; toute page défaillante conserve liste, sélection et cache
précédents.

Les reproductions rouges ont observé `201 != 503`, `200 != 503`, une panne SQL
rendue comme vide, seulement 200 conversations sur 205, la publication de la
première page malgré l'échec de la suivante et l'acceptation d'une page courte.
Les deux mutations causales demandées réintroduisent séparément le faux `201`
en réignorant `ConversationSaveResult`, puis la limite à 200 en retournant la
première page; chacune fait échouer son témoin avant restauration exacte. Les
tests ciblés store/service/routes et les voisins Workspace passent `46/46`; les
tests Node du sidebar, du renderer, du folder binding et des frontières
Workspace passent `33/33`. Aucun schéma DB, route, écran, télémétrie, queue,
retry, framework de pagination ou accès à la DB opérateur n'est ajouté. L7.3
n'est pas commencé.

### L7.3 — Portée des compteurs — F20 — fermé

Traiter séparément les cinq mécanismes :

1. sources Web et blocs injectés ne sont pas la même unité — **L7.3.1 fermé** ;
2. fenêtre durable et compteurs process-local doivent être nommés sans ambiguïté — **L7.3.2 fermé** ;
3. `failed` doit suivre le compteur canonique du pipeline — **L7.3.3 fermé** ;
4. buckets et conversations doivent employer la même borne temporelle — **L7.3.4 fermé** ;
5. réception du callback de log ne doit pas devenir `audit.stored=true` si
   l'écriture fichier a échoué — **L7.3.5 fermé**.

Un même micro-lot peut regrouper deux points uniquement s'ils partagent le même
read-model et le même correctif. Aucune collecte ou dashboard supplémentaire.

#### L7.3.1 — Sources Web du manifeste principal

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`3e364b9242a80997a4600a6f817382b8b49bc642` confirme que `results_count`
compte les sources retenues, tandis que `context_block` est un bloc unique qui
peut les regrouper. Le manifeste soustrayait pourtant `1` bloc au nombre de
sources et pouvait donc produire `5/1/4`. Il prenait aussi la constitution du
bloc, via `context_injected` ou sa présence brute, pour une preuve de son
insertion dans le dernier message utilisateur.

Le correctif conserve le schéma et les champs existants. La préparation du
payload transmet au manifeste le résultat enrichi de l'injecteur; seule sa
preuve `main_prompt_context_injected` gouverne l'attribution du rôle logique
`web_lane` et les compteurs. Les trois compteurs sont désormais exprimés en
sources: `N/N/0` après insertion réelle et `N/0/N` sinon. Le booléen
`context_injected` continue seulement d'indiquer qu'un bloc Web a été
constitué. Aucun prompt, résultat, classement, budget, modèle ou nombre de
sources n'est modifié, et aucune requête, URL, source ou contenu brut n'est
projeté.

La reproduction rouge observe `5/1/4` pour cinq sources injectées et un faux
rôle `web_lane` quand le bloc existe sans insertion. Le chemin réel
`prepare_main_payload -> main_payload_manifest_v1 -> projection admin` est
couvert, ainsi que `5/0/5`, `0/0/0`, `1/1/0`, final lock, erreur Web et absence
de contenu brut. La mutation demandée rétablit le calcul par bloc, fait
réapparaître `5/1/4`, puis le correctif exact est restauré. L7.3 reste ouvert;
L7.3.2 est fermé.

#### L7.3.2 — Portée des compteurs herméneutiques

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`012664a915397b495066b2225e0ba9e2f24a46df` confirme trois populations
distinctes dans le dashboard herméneutique : les KPI persistés de
`get_hermeneutic_kpis()` sont bornés par `window_days`; les compteurs de
`arbiter.get_runtime_metrics()` vivent uniquement dans le processus courant et
sont remis à zéro au redémarrage; les latences sont calculées sur au plus
`log_limit` entrées du seul fichier de log courant. L'ancien
`max(durable_fallback_rate, runtime_fallback_rate)` mélangeait deux populations
sans portée statistique cohérente, et le renderer parlait à tort d'une unique
« fenêtre courante ».

L'API groupe désormais les faits existants sous `measurement_scopes` :
`durable_window` porte `window_days`, ses compteurs et son taux de fallback;
`process_runtime` porte les compteurs, taux et métriques du processus, avec
`started_at=null` puisque ce timestamp n'est pas collecté; `current_log_sample`
porte `log_limit` et les latences du fichier courant. Les taux de fallback et
leurs alertes restent séparés, avec des reason codes qui nomment mesure et
portée. Les anciens agrégats top-level ambigus sont retirés et le frontend rend
trois cartes explicites. Aucune collecte, route, page, télémétrie, donnée brute
ou capacité produit n'est ajoutée.

Les reproductions rouges traversent la route et le service réels pour les deux
ordres durable/runtime, puis un redémarrage simulé; le renderer réel prouve les
trois libellés, le début process inconnu et la borne `log_limit`. Le témoin
causal réintroduit brièvement « fenêtre courante », fait échouer le test Node,
puis le correctif exact est restauré. Les tests ciblés passent : 17 tests
Python service/routes, 6 tests Node renderer et voisin immédiat, puis un unique
scénario Chromium herméneutique ciblé. L7.3 reste ouvert.

#### L7.3.3 — Compteur canonique des problèmes

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`d474a6cadfc0ee5536b8224791a90ce54decb3d6` confirme que le pipeline distingue
déjà `error_count`, `failed_count` et `fallback_count`, puis expose leur
`problem_count` canonique dans les items de tour et les résumés de conversation.
Le dashboard recalculait pourtant trois fois `error_count + fallback_count` :
pour l'état de conversation, sa colonne « problèmes » et le détail d'un tour.
Un échec `failed` seul pouvait ainsi être affiché à zéro et laisser la
conversation « Stable ».

Le renderer utilise désormais une règle locale unique. La présence explicite
de `problem_count` prévaut, y compris lorsqu'il vaut zéro; seul un payload
historique qui ne porte pas ce champ déclenche le repli exact
`error_count + failed_count + fallback_count`. Les statuts sans problème ne
sont pas ajoutés, et ni la taxonomie, ni le pipeline, ni le read-model, ni
l'API ou la collecte ne changent.

La reproduction Chromium ciblée traverse le vrai dashboard avec un échec seul,
un zéro canonique contredisant ses composants, un payload legacy, et les cas
`error`/`fallback` existants, au niveau conversation comme au niveau tour. Elle
échoue sur l'ancien calcul, passe après raccord, puis redevient rouge pendant
la mutation contrôlée qui réintroduit `error_count + fallback_count`; le
correctif exact est ensuite restauré. Les voisins Python confirment le compteur
canonique et la projection content-free. L7.3 reste ouvert.

#### L7.3.4 — Bornes temporelles communes du dashboard

**Définitivement refermé le 6 septembre 2026.** La revalidation au HEAD initial
`e2db300f9b36f1b82b6678e814abee83413588ad` confirme que les conversations,
tours, inspections et content gates filtraient les facts par
`latest_ts >= start AND latest_ts < end`, tandis que l'overview sélectionnait
les buckets par `bucket_start >= start AND bucket_start < end`. Pour une
fenêtre commençant à `12:30`, un tour à `12:45` apparaissait donc dans sa
conversation alors que son bucket `12:00` était absent. Inclure le bucket
chevauchant aurait inversement ajouté ses faits antérieurs à `12:30`.

`resolve_dashboard_window()` reste l'autorité unique et publie maintenant la
sémantique machine-lisible `timestamp_field=latest_ts` et
`interval=[start,end)`. La fermeture initiale a été rouverte après reproduction
dans l'image livrée d'une custom alignée historique : les buckets horaires ne
sont garantis que sur les 30 derniers jours, donc l'alignement géométrique ne
prouve pas leur existence. Toute fenêtre `custom`, alignée ou non, réduit
désormais les mêmes turn facts persistés, filtrés exactement sur cet intervalle,
avec des buckets de bord bornés à `start` et `end`. Seules les fenêtres
prédéfinies alignées conservent la lecture des buckets persistés; aucun événement
extérieur n'est ainsi absorbé. Le frontend résout d'abord l'overview, puis
réutilise ses timestamps exacts pour les conversations, tours, inspections et
ouvertures du content gate. Il ne publie toujours aucun état partiel si la
lecture des conversations échoue.

La fake relationnelle prouve la fenêtre glissante `12:30`, une custom
historique à fin non alignée, puis la réouverture avec la custom alignée
`[2026-07-20T12:00Z,13:00Z)` et son fact à `12:30`: overview et conversations
comptent tous deux un tour malgré l'absence du bucket horaire historique. Elle
prouve aussi l'inclusion exacte de `start`, l'exclusion exacte de `end`,
l'absence de fuite par bucket chevauchant et les cinq surfaces avec la même
fenêtre. Le chemin préagrégé reste verrouillé pour une fenêtre prédéfinie
alignée. La mutation contrôlée rétablit `aligné => buckets`, remet la custom
historique au rouge, puis le correctif exact est restauré. Les tests ciblés
couvrent en outre couverture, pagination, erreurs, content gate,
matérialisation, rendu et absence de contenu brut. Aucune table, collecte,
route, métrique source ou granularité n'est ajoutée. Lors de cette clôture
initiale, L7.3 restait ouvert et L7.3.5 n'était pas commencé.

#### L7.3.5 — Preuve de stockage de l'audit du content gate

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`a8ad0844733afc11a277de61f27b5f83ba50abb4` confirme que
`admin_logs.log_event()` absorbait une exception d'écriture sans retourner de
preuve, tandis que le callback de la route content gate retournait toujours
`True`. Le read-model pouvait donc publier `audit.attempted=true` et
`audit.stored=true` sans qu'aucune ligne d'audit existe.

Le writer retourne désormais `True` uniquement après l'écriture complète de la
ligne JSONL sanitizée et `False` après exception. Le callback transmet ce
résultat sans le remplacer. L'ouverture volontaire du contenu reste disponible
en cas d'échec d'audit, mais sa réponse porte honnêtement
`attempted=true/stored=false`; le frontend conserve son libellé existant
« stockage non confirmé ». Les appelants historiques peuvent continuer à
ignorer le retour. Rotation, destination, sanitisation et absence de contenu ou
d'exception brute restent inchangées.

Les reproductions rouges traversent le vrai writer, le callback de route et le
read-model d'audit : le writer retournait `None` après succès comme après
échec, puis un chemin sans ligne écrite devenait `stored=true`. Les preuves
finales couvrent succès avec ligne présente, échec hermétique sans ligne,
ouverture préservée, statuts d'audit exacts et absence de contenu brut. La
mutation contrôlée rétablit le `True` inconditionnel, remet le témoin d'échec au
rouge, puis le correctif exact est restauré. Aucune queue, retry, destination,
base, route, métrique, vue ou capacité n'est ajoutée. L7.3 est fermé.

### L7.4 — Réglages Identity historiques — F18

**Fermé le 6 septembre 2026.** F18 restait partiellement vivant: six seuils
du writer fragmentaire historique etaient encore classes comme sous-pipeline
actif et editables, alors que le chemin chat courant passe par
`memory_identity_periodic_agent -> mutable_identity_runtime ->
mutable_identity_judge_v2 / mutable_identity_apply` sans les lire.

La gouvernance separe maintenant les dix cles dont la valeur reste lue depuis
`runtime_settings.identity_governance` des quatre cles reellement modifiables
par son API. Les six seuils historiques restent donc visibles avec leur valeur
persistee mais sont readonly. Les quatre `CONTEXT_HINTS_*` restent des
auxiliaires actifs editables; `identity_extractor_max_tokens` est un auxiliaire
actif readonly sur cette surface; les budgets `3000/3300` sont les deux seuls
items directement raccordes au juge V2; `IDENTITY_DECAY_FACTOR` est une
compatibilite encore executee a la creation d'une conversation, bornee a la
decroissance de `identities.weight`; `IDENTITY_TOP_N` et
`IDENTITY_MAX_TOKENS` restent legacy inactifs.

Le read-model, ses compteurs, les labels et l'aide frontend racontent cette
meme taxonomie. La route dediee refuse les six seuils historiques avec
`governance_key_readonly`, et aucune route generique `/api/admin/settings/*`
n'expose `identity_governance` en mutation. Les tests ciblent la matrice
autoritative, la conservation des valeurs runtime-backed, l'allowlist d'edition,
le rendu Node et un scenario Chromium unique. La mutation controlee de la
classification centrale remet le test de matrice au rouge puis le correctif
exact est restaure. Aucun seuil, jugement, injection, writer ou contenu
Identity n'est modifie. L7.5 n'est pas commence.

### L7.5 — Bancs Identity obsolètes — F22

**Fermé le 6 septembre 2026.** La revalidation au HEAD initial
`68eee3464a90c06a98a3a747f55fd82f1ec3bc91` confirme F22. Le banc
`identity_extractor` chargeait le prompt courant `dialogic_context_hint_v1`,
limité au sujet `dialogue`, tandis que sa fixture, son payload et son scorer
attendaient encore des entrées `user` / `llm`. Le banc `identity_periodic`
importait `memory_identity_periodic_apply`, applicateur retiré du dépôt, alors
que le runtime actif passe par `memory_identity_periodic_agent ->
mutable_identity_runtime -> mutable_identity_judge_v2 ->
mutable_identity_apply`.

Le runner général ne propose, n'importe et ne branche plus ces deux suites et
ne porte plus leurs modèles par défaut. Les deux formes de sélection, option
`--suite` et positionnelle, sont refusées par `argparse` avant résolution des
credentials, construction du client, appel provider ou création du répertoire
de résultat. Les tests positifs des campagnes historiques ont été remplacés
par ces invariants négatifs sur la vraie CLI et par l'import du runner actif
sans chargement des modules Identity historiques ni de l'applicateur retiré.

Les sources, fixtures et résultats suivis restent inchangés comme preuves de
provenance. `benchmark/README.md` les étiquette désormais comme historiques,
inactifs et non comparables au HEAD. Il nomme le pipeline V2 courant et le
smoke distinct `app/scripts/smoke_mutable_identity_judge_llm.py` sans prétendre
qu'il a été exécuté ni en faire un banc de remplacement. La reproduction rouge
a montré les deux noms dans `--help`, quatre tentatives atteignant encore la
résolution de `OPENROUTER_API_KEY`, l'import actif du vieux banc extractor et
l'échec de découverte du test périodique sur l'applicateur absent. Après le
correctif, les 17 tests benchmark ciblés passent dans le conteneur hermétique
existant, checkout read-only et `--network none`.

Aucun corpus, scorer, prompt, modèle, juge, applicateur, canon, runtime ou
artefact historique n'est modifié. Aucun provider, campagne modèle réelle,
canari, DB, dialogue réel, JavaScript ou Chromium n'est lancé. L7.6 n'est pas
commencé.

### L7.6 — Banc historique Stimmung — F24, garde avant réutilisation

**Fermé initialement le 6 septembre 2026.** La revalidation au HEAD initial
`78cfe1350fb57f2515aa5ce7de71e2858a6711e7` confirme les hypothèses 1 à 6 de
F24 et invalide la septième sur le chemin antérieur. `validate_mapping()` liait
mapping et packet par leurs empreintes, mais ne recroisait ni séquence ni
variante avec le calendrier et le ledger. Une
permutation synthétique des deux seules variantes d'une paire, à empreintes de
sorties inchangées, franchissait cette validation et modifiait les deux comptes
d'amélioration attribués au candidat. Le ledger et le calendrier portaient déjà
toutes les identités nécessaires ; le finalizer v2.5 réutilisait bien le même
scorer v2.4, sans disposer d'une bijection causale commune.

La frontière publique v2.4 exige désormais la racine et le commit gelé ; son
ancien appel sans contexte historique échoue avec le reason code fermé
`historical_attribution_guard_required`. Une garde de finalisation unique
reconstruit le protocole historique depuis le manifeste v2.4 ou le profil v2.5,
réinjecte seulement ses empreintes gelées de provenance, puis vérifie le
manifeste exact et l'empreinte du calendrier de 24 appels. Cette reconstruction
n'autorise ni reprise ni campagne. Après validation complète des ratings et de
la ratification éventuelle, et seulement alors, elle lit le mapping et impose
la bijection exacte des 24 séquences. Chaque lien recroise cas, répétition, type
de comparaison, slot aveugle, empreinte des messages, variante autoritative et
empreinte de sortie entre calendrier, ledger, mapping et packet. Les doublons,
absences, séquences étrangères et incohérences utilisent uniquement des reason
codes fermés et content-free.

Le finalizer GPT-5.2 v2.5 délègue à cette même garde sous son profil historique ;
aucun second protocole n'est copié. Toute incohérence s'arrête avant scorer,
écriture durable, `unlink` ou `rmdir`, en conservant packet, ratings, mapping,
ledger et sorties privées. Le scorer consomme le snapshot validé, et une
nouvelle empreinte des sources juste avant scoring puis commit ferme la fenêtre
de relecture TOCTOU. Les ratings incomplets et l'absence de ratification restent
refusés avant reconstruction du calendrier et lecture du mapping. Les chemins
nominaux v2.4 et v2.5 conservent l'écriture atomique, le readback, les
permissions et la séparation privé/review. Avant le commit durable, les deux
répertoires de preuves sont renommés sans lecture ni copie vers des noms privés
content-free ; tout échec pré-commit restaure leurs noms et contenus. La purge
post-commit est bornée à ces répertoires isolés et ne transforme jamais un
résultat durable validé en refus destructeur. La publication durable est
atomique, sans écrasement ; une destination existante ou située dans les
répertoires actifs ou de staging est refusée sans mutation.

La reproduction, les contre-cas et les chemins nominaux traversent les vrais
finalizers dans 16 tests hermétiques, sans réseau ni provider. La mutation
contrôlée retirant le contrôle de variante atteint de nouveau le scorer et remet
le témoin de permutation au rouge ; la restauration exacte le remet au vert.
La fonction de scoring sémantique, les seuils, corpus, prompts, modèles,
manifestes, résultats et artefacts gelés restent inchangés. `keep_current_v2.3`
reste actif et inchangé. Aucun canari, campagne, runtime, DB, dialogue réel,
JavaScript, Chromium, rebuild, restart ou déploiement n'est lancé. L7.7 n'est
pas commencé.

**Correctif de réouverture puis fermeture définitive du 6 septembre 2026.** Au
HEAD initial `6b3fd405c5fc4ef5820d55fb49f9ad01c70f43d8`, la garde F24 avait modifié
le module de notation après les gels v2.4/v2.5. Le manifeste v2.4 conservait
l'empreinte historique `b2154ec3...`, tandis que la source courante valait
`6a4fb3f7...`. `build_protocol()` refusait donc correctement la dérive avec
`freeze_manifest_mismatch`, mais trois `setUpClass` et sept tests v2.5
continuaient à reconstruire les campagnes comme si leurs runners décrivaient
le HEAD. La commande hermétique commune lançait 26 tests et produisait 10
erreurs ; la preuve initiale L7.6 était trop étroite.

Les preuves distinguent désormais trois contrats. Premièrement, les manifestes
v2.1/v2.4/v2.5 et les résultats v2.4/v2.5 sont authentifiés byte-for-byte selon
leur provenance gelée, sans substituer les hashes courants. La garde partagée
ancre explicitement les SHA-256 exacts des manifestes v2.4/v2.5 avant toute
réinjection de `frozen_inputs`, ce qui refuse aussi une auto-réécriture cohérente
d'un champ historique. Deuxièmement, les entrées publiques runner et dry-run
v2.4/v2.5 prouvent leur non-comparabilité au HEAD : elles échouent avant
credentials, client, provider, progression ou création de fichier. Les anciens
tests positifs de campagne ont été reclassés test par test en intégrité
d'archive, helpers purs encore valides ou refus public ; aucun runner n'est
réactivé. Troisièmement, les vrais finalizers offline v2.4/v2.5 continuent seuls
à réutiliser la bijection F24, avec ratification, refus des permutations avant
scorer/purge, destination no-clobber et restauration ou purge conforme au
contrat.

La preuve différentielle finale exécute les quatre modules v2.1/v2.4/v2.5/L7.6
dans une même commande, en conteneur read-only, `/tmp` éphémère et réseau
coupé : `50/50` tests verts, sans erreur de `setUpClass`, skip, expected failure
ou xfail. Les manifestes, corpus, scorers, résultats, prompts, modèles, seuils
et artefacts historiques restent byte-for-byte inchangés ; seul le loader de
finalisation authentifie plus strictement leurs deux manifestes. Le runtime
Stimmung et `keep_current_v2.3` restent inchangés. Aucun provider, canari,
campagne, DB, dialogue réel, JavaScript, Chromium, rebuild, restart ou
déploiement n'est lancé. L7.6 est définitivement refermé ; L7.7 n'est pas
commencé.

### L7.7 — Passe documentaire bornée

Synchroniser seulement les affirmations encore fausses : vérifier la cohérence
finale de l'exposition du Compose traitée en L1, preuve admin loopback/proxy,
sections historiques Web, aide OCR, activation
Biblio, pré-appel Stimmung présenté comme réception, mélange des temps dans les
contrats herméneutiques et vocabulaire Identity legacy. Le grand audit reste
conservé comme source datée ; aucune réécriture générale du README.

**Fermé le 7 septembre 2026.** La revalidation phrase par phrase au HEAD
initial `eb8870740e8b7d39504f5e64a9361d397d9babe5` classe les huit groupes sans
modifier le grand audit historique:

| Groupe | Classement | Revalidation et correction bornée |
| --- | --- | --- |
| D1 — Compose local | `déjà exact` | L1 avait déjà livré `127.0.0.1:8093:8089`; Compose et README distinguent usage local et absence de Caddy/Authelia. Aucun patch. |
| D2 — Admin loopback/proxy | `encore faux puis corrigé` | Le guide appelait le port Docker depuis l'hôte comme preuve admin. La preuve technique part désormais du loopback conteneur; le Compose local n'offre pas de voie humaine admin authentifiée, tandis que l'OVH passe par Caddy/Authelia + `Remote-User`, sans token admin. |
| D3 — Web historique | `encore faux puis corrigé` | Le guide mélangeait l'ancien auto-Web et un chantier dit ouvert dans `todo-done`. Seul le déclenchement lexical automatique est historique; SearXNG reste une dépendance actuelle de la recherche Web explicite. Les passages renvoient au pipeline courant et conservent `/api/chat`. |
| D4 — OCR et lecture visuelle | `encore faux puis corrigé` | L'aide d'upload et des passages du contrat Workspace présentaient encore l'OCR comme futur ou implicitement attendu. Ils distinguent maintenant admission visuelle bornée, OCR explicite de l'atelier et absence d'OCR obligatoire pour tout PDF scanné. |
| D5 — Biblio active | `encore faux puis corrigé` | Les deux exemples de configuration décrivaient encore un smoke futur. Ils nomment le bibliothécaire LLM actif selon le réglage et les murs déterministes. Aucun flag ni modèle ne change. |
| D6 — Stimmung pré-appel | `encore faux puis corrigé` | Le contrat attribuait une réception provider à `stimmung_prompt_prepared`. Il borne désormais la preuve à la préparation/émission content-free avant frontière provider, sans inférence de réception, succès ou effet final. |
| D7 — Temps herméneutiques | `encore faux puis corrigé` | Les contrats minimaux et leurs voisins conservaient des présents préparatoires. Les paragraphes sont marqués historiques et l'état courant nomme Validation arbitre final borné puis `validated_output` projeté dans `[JUGEMENT HERMENEUTIQUE]`. |
| D8 — Identity et aides admin | `encore faux puis corrigé` | La taxonomie L7.4 était déjà exacte (`juge V2`, auxiliaires, compatibilité legacy, legacy inactif). L'aide Admin ne présente plus ses formulaires/logs comme futurs et le contrat readonly Validation inclut le régime `presence` déjà livré. |

Aucun écart produit hors L7.7 n'a été reproduit. Les corrections portent sur
des Markdown vivants, commentaires/exemples, aides statiques et assertions
ciblées. Elles n'ajoutent ni capacité, route, API, schéma, seuil, éditabilité,
provider, modèle ou workflow. Le runtime Stimmung et `keep_current_v2.3`, les
benchmarks et Z restent inchangés. Le grand audit n'est pas modifié.

Contre-audit documentaire du 7 septembre 2026: la première rédaction
sur-historicisait SearXNG et n'explicitait pas l'absence de voie humaine Admin
dans le Compose local sans proxy. Le guide distingue maintenant ces deux
frontières sans changement de code ni de comportement produit.

## 11. Z — Réconciliation finale avec le grand audit

Z n'est pas un nouvel audit indéfini. La passe du 7 septembre 2026 a vérifié les
findings et réserves recensés par le rapport du 2 septembre au HEAD initial
`844d2e1ed2fc83202643b6a7cd24d7ffafcc2095`. La baseline attendue était exacte :
branche `main`, HEAD/upstream/distant égaux, divergence `0/0`, worktree propre.

### 11.1 Décompte et décision

- **Identifiants historiques : 24/24 classés.** Les 24 sont `corrigé`; zéro
  `invalidé`, zéro `différé avec condition`, zéro `ouvert`.
- **Lignes atomiques : 34/34 classées.** Les divisions F12 (3), F13 (2), F14
  (2), F15 (2), F19 (2) et F20 (5) ajoutent dix lignes aux 24 identifiants :
  les 34 sont `corrigé`; zéro `invalidé`, zéro `différé avec condition`, zéro
  `ouvert`.
- **Réserves non numérotées : la réserve de rendu Biblio est corrigée avec une
  limite de preuve documentée.** Le chemin agentique réel
  `catalog_list -> objet-réponse -> renderer` a retenu et rendu 12/12 ouvrages.
  Le même renderer est traversé hermétiquement à 1/1, 20/20/0 et 25/20/5 ; un
  cas où `total_count=40` et `document_count=25` maintient distincts total
  répertorié, retenu, affiché et masqué. Au-delà de 20, aucune branche LLM ou
  provider supplémentaire ne s'active : seule la tranche déterministe change.
  Le corpus live courant ne contenant que 12 ouvrages, P01 est requalifié comme
  frontière live non franchissable avec cette cardinalité, pas comme échec
  produit. La revalidation devient obligatoire lorsque le corpus live dépassera
  20. Les trois autres réserves demeurent des limites ou mécanismes sans bug
  produit reproduit.
- Les trois témoins explicitement autorisés ont été reproduits rouges avant
  patch puis réalignés. Le Compose échouait seul sur l'ancien littéral et passe
  désormais `1/1` sur `127.0.0.1:8093:8089`. Les deux scénarios Chromium
  expiraient avant leur frontière métier ; leurs fixtures renvoient maintenant
  `items`, `total`, `limit` et `offset` cohérents avec la requête. Le scénario
  terminal vide passe `1/1` en 606,928 ms et le scénario Workspace passe `1/1`
  en 1 626,753 ms, sans timeout, skip du scénario ciblé ni faux succès.
- Les quatre familles de la découverte précédente sont corrigées. Agenda passe
  dans les deux ordres, seul et avec l'import sans lecture de secret ; les 22
  anciens tests Stimmung passent dans la même session que les 50 témoins F24 ;
  les neuf témoins causaux de la fake conversationnelle et leur voisin passent
  avec la vraie précondition F09 ; l'assertion L7.7 vérifie désormais le contrat Web
  courant. La sélection commune passe **141/141 en 315,281 s**.
- L'unique découverte Python complète de ce micro-lot a exécuté **3088 tests en
  613,603 s**, avec **2 échecs, 0 erreur, 0 skip, exit code 1**. Le total
  augmente de neuf : huit méthodes auparavant masquées par les erreurs de
  `setUpClass` Stimmung redeviennent exécutables et un contre-cas F09 est ajouté.
  Les deux seuls échecs concernent la validation de patches de secrets
  `embedding` et `services` : la commande avait vidé `EMBED_BASE_URL`,
  `CRAWL4AI_URL` et `SEARXNG_URL`, qui sont des champs de configuration soumis
  à validation d'URL, pas des credentials. La reproduction ciblée échoue 2/2
  avec ces champs vides puis passe 2/2 en 0,001 s avec des URL synthétiques
  `.invalid`, `--network none` et tokens vides. Aucun défaut produit nouveau
  n'est établi.

La décision honnête est donc : **Z reste ouvert et cette roadmap reste active.**
Le registre ci-dessous réconcilie les Fxx livrés, les quatre incompatibilités
initiales sont éliminées et la réserve Biblio n'est plus un bug produit ouvert,
mais la consolidation entière ne peut pas être archivée sur une découverte
finale rouge. Aucun code produit n'a changé et aucune seconde découverte
complète n'a été lancée dans ce micro-lot.

### 11.2 Matrice exhaustive F01–F24

Chaque ligne nomme le test témoin courant et la frontière qu'il traverse. Les
contrats vivants correspondants sont ceux cités par le lot indiqué, complétés
par [le pipeline runtime courant](../../states/architecture/fridadev-current-runtime-pipeline.md).
Le recroisement a relu `streaming-protocol.md` pour F01/F05,
`mutable-identity-judge-contract.md`, `memory-rag-summaries-lane-contract.md`,
`memory-rag-pre-arbiter-basket-contract.md` et `identity-read-model-contract.md`
pour F02–F04/F07, les deux contrats Biblio pour F06/F11, les contrats Agenda,
Workspace/Documents et Web pour F08/F12–F16/F19, puis
`dashboard-long-term-observability-contract.md`, `identity-governance-contract.md`,
`benchmark/README.md`, le Compose/README et les baselines Stimmung pour
F17–F24. Les commits cités existent tous dans l'ascendance du HEAD Z et les
fichiers runtime/tests/contrats annoncés par leurs diffs sont encore présents.

| ID | État, cause historique et correction actuelle | Commit autoritatif et preuve actuelle | Runtime, limite, réouverture et effet quotidien |
| --- | --- | --- | --- |
| F01 | **corrigé — I1.** Une erreur structurée ou une fin SSE non prouvée pouvait devenir `done`; le reader classe désormais erreurs, EOF, JSON invalide et `choices=[]` nu comme interruption, tout en conservant les trames metadata/usage légitimes. | Chaîne autoritative `178dba1b39ca4f500645cc954a677d148e1e1741` puis correctif final `cdfa3f91ea1a8d979ac63ca078698eb730b822e0`; `test_chat_llm_flow.py::test_provider_stream_error_frames_remain_interrupted_without_success_effects` traverse reader, coordinateur, terminal, canon et dérivations. | Livré : aucune parole assistant ni dérivation de succès après erreur. Limite : transport provider synthétique. Réouvrir si une fin non prouvée produit `done`, un canon assistant ou un effet post-save. **Effet : direct.** |
| F02 | **corrigé — I2.** Une panne de lecture mutable ressemblait à une absence et autorisait un remplacement; l'applicateur exige maintenant une lecture stricte avant toute planification ou écriture. | `7e2b56b328db2d899c29c92947b6c969570fc214`; `test_identity_periodic_agent_phase1.py::test_mutable_read_failure_uses_bounded_write_recovery_without_partial_write` traverse reader strict, façade, applicateur et reprise bornée. | Livré : le canon existant survit à une lecture en panne. Limite : SQL factice, aucune panne PostgreSQL réelle. Réouvrir si une erreur de lecture peut atteindre `INSERT`, audit ou succès. **Effet : direct.** |
| F03 | **corrigé — M1.** Le résumeur marquait des paroles acquises malgré l'échec du stockage texte; le writer remonte désormais un booléen et `False`/`None` bloque marques, rattachement et succès. | `7ec484e0ebd4eb989ab34e03ae91ab224e420f5a`; `test_summarizer_phase4.py::test_writer_persistence_failure_does_not_acquire_summary_through_real_facades` traverse writer, façades, résumeur et éligibilité suivante. | Livré : une parole n'est retirée du prochain résumé qu'après commit du résumé. Limite : panne injectée, pas de mesure de qualité sémantique. Réouvrir si un stockage non confirmé produit `summarize_done`, `summary_generated` ou des marques. **Effet : direct.** |
| F04 | **corrigé — M2.** La déduplication lexicale pouvait fusionner « mardi » et sa correction « jeudi » avant l'arbitre; seules l'identité textuelle stricte et la relation trace/résumé fusionnent encore. | `6dd346c0614e5ca78dd09cff57c78440cc65405e`; `test_memory_pre_arbiter_basket_phase7b.py::test_distinct_weekday_corrections_reach_the_real_arbiter_messages` traverse retrieval synthétique, panier et payload arbitre. | Livré : les formulations distinctes admises sous budget arrivent séparément au jugement. Limite : panier toujours borné à huit, arbitre non évalué sémantiquement. Réouvrir si deux textes distincts sont de nouveau fusionnés avant l'arbitre. **Effet : direct.** |
| F05 | **corrigé — L6.1.** La normalisation retirait du code clôturé pourtant autorisé et le raccord secondaire pouvait ressusciter un brouillon quand le terminal final était vide; la policy préserve le code autorisé et la présence explicite de `final_text` prime sur le brouillon, même vide. | `3479eb1a19d3b75202cf3506702d0bf8736d3a56`; `test_chat_llm_flow.py::test_run_llm_exchange_stream_preserves_structure_for_explicit_plan_requests` traverse la finalisation, `test_stream_control_parser_module.js::resolveStreamedAssistantText honors present empty final_text over streamed draft` le parser client, et le Chromium terminal-vide traverse désormais la preuve DOM complète. | Livré : code demandé intact et aucun assistant fantôme pour un terminal vide. La fixture F17 courante porte sa pagination complète et le scénario ciblé passe sans timeout. Réouvrir si le code autorisé est altéré ou si un terminal vide conserve un brouillon. **Effet : direct.** |
| F06 | **corrigé — B1.** Une section coupée pouvait être annoncée complète; projection, rendu, final lock et état portent maintenant explicitement l'incomplétude et interdisent le saut du reste. | Code `2a063d27e3641eb4c1f78443761ed18f3c240b6a`, checker `28ee5f28299f05183ee915454d649e08ea717668`, preuve live `b1-section-truncation-live-20260903T123527Z.jsonl`; `test_librarian_agent_first.py::test_section_complete_extraction_keeps_truncated_single_page_partial` traverse outil, réponse et rendu. | Livré : un extrait tronqué reste partiel. Limite : pas d'offset de reprise intra-page, donc le reste est signalé mais pas progressivement accessible. Réouvrir si `range_complete=true`, une annonce complète ou une ancre suivante apparaît après coupe. **Effet : direct.** |
| F07 | **corrigé — O1.** Le reader admin rejetait le sujet `dialogue` réellement écrit et affichait zéro; seul le reader d'evidence admet maintenant ce sujet et compte avant pagination. | `035c286cc5f9abe531747f5e35e50efb9cf8fb69`; `test_identity_read_model_phase2.py::test_dialogue_hints_flow_through_real_store_facades_and_both_admin_responses` traverse writer, store, reader et deux projections. | Livré : le total stocké est fidèle, sans élargir canon/fragments/conflits. Limite : store factice et compteur distinct de l'injection effective. Réouvrir si `dialogue` est refusé, admis dans les mauvaises familles ou si le total vient de la page limitée. **Effet : observabilité/outillage seulement.** |
| F08 | **corrigé — L3.** Une compensation Nextcloud pouvait supprimer une version modifiée après la création de Frida; les DELETE compensatoires exigent l'ETag fort exact de la version créée et conservent les collections non prouvées. | Chaîne autoritative `bc4e88911b03989568bd0e314bfbe49653648680` puis correctif final `4f182c630bf0a2287deaea45af42d34feab5689f`; `test_workspace_nextcloud_compensation_etag.py::test_non_owning_etags_are_rejected_before_transport` traverse les quatre clients et le transport simulé. | Livré : version étrangère ou propriété non vérifiée conservée, statut résiduel honnête. Limite : DAV synthétique, aucune panne Nextcloud réelle. Réouvrir si une compensation sans ETag fort courant atteint un DELETE ou si `412` devient succès. **Effet : indirect.** |
| F09 | **corrigé — L2.** Un snapshot ancien/divergent pouvait remplacer le canon; le writer sérialise la conversation et n'accepte que le même ordre ou une extension de préfixe, avec exception bornée pour le système dynamique initial. | Chaîne autoritative `8b5137625c675cb6ae51bfe1314f4bacdf72524d` puis correctif final `57b525f7fa684855298c1bd0da7672f5e9c2aa91`; `test_conversations_store_save_result.py::test_atomic_save_accepts_dynamic_first_system_without_weakening_dialogue_canon` et `::test_atomic_save_rejects_stale_prefix_without_removing_committed_suffix` traversent la transaction factice. | Livré : suffixe, ordre et metadata monotones préservés; rename ne réécrit plus les messages. Limite : pas de fusion distribuée des branches. Réouvrir si un snapshot court/divergent committe ou si un changement légitime du système initial est refusé. **Effet : direct.** |
| F10 | **corrigé — L6.2.** Des réponses tardives conversations, documents, logs ou dashboard pouvaient modifier la sélection courante; chaque famille compare désormais epoch et identité complète de la requête, y compris les filtres logs. | Correctifs `963d530eb90b842f8fdcc2bbefb6157aa27a35f1` puis `28bb7b7afb1c000c727123c061f63822e7808f73`; `test_threads_sidebar_module.js::thread loading keeps a late conversation response out of the current conversation view` et `test_frontend_browser_smoke.js::logs keep the latest filters, metadata and visible data after stale success or error` traversent contrôleurs et DOM. | Livré : succès/erreur A ne remplace plus B. Limite : courses synthétiques, fréquence live inconnue. Réouvrir si une réponse portant une ancienne sélection, période ou signature modifie DOM, statut ou compteurs courants. **Effet : direct.** |
| F11 | **corrigé — B2.** Une nouvelle ancre document B sans position conservait les coordonnées A et pouvait lire B à la page A+1; le changement de document efface position et hash avant réhydratation/navigation. | Code `39acfa28797db949351a98750389c47730c866a1`, preuve finale `ecd2c8d209d02b8b6ccf486a8501af63b44d3ea4` et JSONL `b2-document-coordinate-provenance-live-20260903T184059Z.jsonl`; `test_conversation_state.py::test_document_change_drops_old_position_before_serialized_navigation` traverse état et navigation. | Livré : aucune ancre A/B mixte; le garde clarifie sans inventer une position. Limite : le plan agent du troisième tour live était invalide, mais le garde produit a protégé l'état. Réouvrir si un changement de document conserve page/paragraphe/hash antérieurs. **Effet : direct.** |
| F12a | **corrigé — L6.3.** Un plan Agenda pouvait conclure à l'absence après `calendar_list` seul; la méthode exige désormais une lecture `REPORT` réussie, sur la fenêtre exacte et avec calendrier résolu. | `3cccab294f665e5cb7beaa8899cde8f537936f2a`; `test_chat_runtime.py::test_window_read_rejects_calendar_list_only_before_rendering_false_absence` traverse validation, exécution, rendu et final lock. | Livré : « aucun événement » exige sa preuve de lecture. Limite : client CalDAV factice. Réouvrir si une absence est rendue sans observation `REPORT` cohérente. **Effet : direct.** |
| F12b | **corrigé — L6.3.** Timeouts, erreurs `requests` et XML invalide pouvaient sortir de la lane et faire échouer le chat; transport et client les normalisent en erreurs Agenda bornées et content-free. | `3cccab294f665e5cb7beaa8899cde8f537936f2a`; `test_chat_runtime.py::test_live_transport_failures_become_bounded_agenda_errors` traverse transport/client, runtime Agenda et verrou de réponse. | Livré : la panne Agenda reste une réponse Agenda bornée, sans masquer `KeyboardInterrupt`/`SystemExit`. Limite : erreurs injectées, pas de CalDAV réel. Réouvrir si une exception ordinaire échappe au raccord chat ou expose le corps brut. **Effet : direct.** |
| F12c | **corrigé — L6.4.** L'expansion RRULE matérialisait des milliers de périodes avant de voir `COUNT`, `UNTIL` ou la fenêtre et pouvait dépasser `datetime`; l'itération est paresseuse et l'épuisement du domaine devient une erreur fermée. | `3b0bfcfb637cb69f1bc052ca1ae7a888840cfb5d`; `test_rrule_expander.py::test_extreme_yearly_count_returns_first_occurrence_without_advancing_period` traverse l'expandeur; `::test_agenda_read_execution_classifies_calendar_domain_exhaustion` traverse sa classification Agenda. | Livré : les arrêts bornés précèdent l'avancement inutile; plafond de 512 conservé. Limite : calendrier synthétique. Réouvrir si un petit `COUNT`/`UNTIL` scanne jusqu'à l'an 10000 ou laisse une `ValueError` brute. **Effet : indirect.** |
| F13a | **corrigé — L6.7.** La ré-OCR remplaçait réellement le Markdown corrigé tout en annonçant toujours une création sans avertissement; le contrôleur confirme le remplacement, conserve le statut HTTP et distingue `201`/`200`. | `306c97d3901c017f3a7c3f9f81ed78e03b23c8bb`; `test_workspace_folder_sidebar_boundaries.js::cancelled workspace re-OCR warns about manual corrections and sends no POST` et `::confirmed workspace re-OCR sends one POST and reports the HTTP 200 update` traversent le contrôleur et le client; le Chromium Workspace traverse de nouveau le DOM complet. | Livré : annulation avant POST, avertissement et libellé juste. La fixture F17 courante porte sa pagination complète et le scénario ciblé passe sans timeout. La concurrence entre lecture et POST reste possible. Réouvrir si ré-OCR part sans confirmation ou fabrique un succès/création. **Effet : direct.** |
| F13b | **corrigé — L5.1.** Deux écritures OCR recouvrantes pouvaient désaligner bytes, hash et SQL; un verrou de ligne couvre lecture, remplacement et commit, avec temporaire unique et compensation conditionnelle. | `7ea2e4acf6e9dbf61c7a761b00b14f2d11cad5d9`; `test_workspace_file_ocr_store.py::test_same_target_writer_waits_for_failed_writer_then_commits_consistently` traverse fake SQL transactionnelle et fichiers temporaires réels. | Livré : une seule version cohérente par cible, writers distincts indépendants. Limite : crash processus/hôte entre filesystem et commit non couvert. Réouvrir si un recouvrement laisse bytes/hash/ligne divergents ou un temporaire partagé. **Effet : indirect.** |
| F14a | **corrigé — L5.2.** Après commit local d'un renommage, une panne de relecture/projection pouvait remettre le distant sous l'ancien nom; succès de mutation et projection post-commit sont maintenant séparés. | `8b7b1d09b58cfd249fddd72acd53dbe4cc2603dd`; `test_workspace_folder_rename_commit_projection.py::test_committed_rename_does_not_rollback_when_a_later_projection_read_would_fail` traverse store, MOVE simulé, commit et projection. | Livré : un commit local réussi n'est plus compensé par un GET ultérieur. Limite : DAV/SQL synthétiques. Réouvrir si une panne post-commit déclenche un MOVE inverse ou laisse deux autorités nommées. **Effet : indirect.** |
| F14b | **corrigé — L6.7.** Un ancien `last_injected_turn_id` primait sur une exclusion courante et fabriquait `readable/ready`; l'existence brute de l'exclusion prime désormais, séparément de la normalisation de son motif. | Chaîne autoritative `306c97d3901c017f3a7c3f9f81ed78e03b23c8bb` puis correctif final `3253a1bd07c4fbd19423cf615ad0b396162a9e43`; `test_workspace_folder_documents.py::test_usage_projection_blocks_current_exclusion_with_missing_or_malformed_reason` traverse le read-model courant et ses marqueurs durables. | Livré : exclu courant reste `not_injected/blocked`; injection suivante lève l'exclusion. Limite : projection synthétique, pas de contenu opérateur. Réouvrir si une exclusion présente redevient prête à cause d'un ID historique ou d'un motif invalide. **Effet : indirect.** |
| F15a | **corrigé — L6.5.** Des sous-chaînes larges comme « Europe » injectaient un gabarit AI Act hors sujet; les requêtes secondaires dérivent maintenant du sujet primaire sans entité fixe. | `77141c31d6d0de39462be3debff45bd5dda25dda`; `test_web_search_query_plan.py::test_actualite_football_europe_does_not_inject_ai_act_topic` traverse le vrai planificateur de requêtes. | Livré : une actualité football/Europe reste sur son sujet. Limite : pas de provider ni mesure de pertinence globale. Réouvrir si un marqueur large réintroduit une entité fixe absente de la demande. **Effet : direct.** |
| F15b | **corrigé — L6.5.** Le classement reconnaissait un domaine officiel par sous-chaîne dans URL, query, fragment, userinfo ou forme ambiguë; une identité URL HTTP(S) stricte sur hostname/path est maintenant partagée avec la garde de crawl. | Chaîne autoritative `77141c31d6d0de39462be3debff45bd5dda25dda` puis correctif final `5162f539b9e6f73b4079d23c2bc5446810c25551`; `test_web_search_rerank.py::test_source_first_ignores_official_domain_in_query_fragment_or_userinfo` et `test_web_search_ssrf_guard.py::test_crawl_guard_and_ranking_identity_reject_same_ambiguous_urls` traversent policy, reranking et garde. | Livré : seules les vraies autorités reçoivent les bonus. Limite : URLs synthétiques, aucune recherche live. Réouvrir si query/fragment/userinfo/C0/antislash suffit à obtenir un classement officiel. **Effet : direct.** |
| F16 | **corrigé — L7.1.** Les clés pending écrites ne correspondaient pas aux clés lues et la garde rejetait leur conteneur, rendant l'action invisible; projection et garde acceptent maintenant uniquement le schéma content-free exact. | `16b86349d935ef4350d2173bfda8c37c92a9a9d7`; `test_observability_read_model.py::test_real_pending_writer_payload_projects_pending_fields` traverse writer, garde, store simulé, read-model et API admin. | Livré : statut, niveau de confirmation et risques pending sont inspectables sans draft brut. Limite : aucune mutation Agenda ni frontend. Réouvrir si un payload writer valide disparaît, ou si une clé sensible traverse la garde. **Effet : observabilité/outillage seulement.** |
| F17 | **corrigé — L7.2.** Création et liste pouvaient transformer un échec store en succès, tandis que le sidebar ne lisait que 200 fils; service/routes propagent `503` et le client parcourt toutes les pages avec invariants stricts. | `3e364b9242a80997a4600a6f817382b8b49bc642`; `test_server_phase13.py::test_api_create_conversation_never_returns_created_when_save_is_refused`, `::test_api_list_conversations_propagates_store_failure` et `test_threads_sidebar_module.js::threads sidebar loads every conversation page once and preserves server order` traversent store, service, HTTP et pagination client. | Livré : aucun faux `201/200`, liste complète ou état précédent conservé en erreur. Limite : DB et fetch factices; les deux mocks Chromium historiques sont réalignés sur `items/total/limit/offset`. Réouvrir si échec devient vide/succès ou si une page valide reste ignorée. **Effet : direct.** |
| F18 | **corrigé — L7.4.** Six seuils du writer Identity historique étaient présentés actifs et éditables; la gouvernance les expose désormais readonly, séparés des quatre auxiliaires actifs éditables, de l'auxiliaire actif readonly `identity_extractor_max_tokens` et des budgets du juge V2. | `d8b1e8e91a70bea0c747cebb0ea99e100c53ef60`; `test_identity_governance_service_phase5.py::test_inventory_response_exposes_authoritative_runtime_classification_matrix`, la route dédiée et le Chromium Identity traversent service, API et rendu. | Livré : l'admin n'offre plus de mutation trompeuse des knobs historiques. Limite : aucune sémantique Identity ni valeur opérateur modifiée. Réouvrir si une clé historique redevient éditable ou étiquetée comme pipeline actif. **Effet : observabilité/outillage seulement.** |
| F19a | **corrigé — L6.6.** `itertext()` perdait les éléments ODT espace, tabulation et saut de ligne et concaténait des mots; un parcours ODF ordonné et borné restitue ces séparateurs. | `1c6b88d720092e998f79f03e8757750a99232843`; `test_active_document_text_extraction.py::test_odt_preserves_explicit_separators_alone_and_combined_in_document_order` traverse parseur, normalisation et statut; les tests upload/Workspace traversent les deux usages. | Livré : séparateurs standards préservés, expansions déraisonnables fermées en `parse_error`. Limite : pas de fidélité ODT universelle. Réouvrir si un séparateur ODF reconnu concatène encore du texte ou contourne la borne. **Effet : direct.** |
| F19b | **corrigé — L5.3.** Après DELETE distant réussi puis échec du tombstone, un retry `404` ne terminait pas toujours et une course de renommage pouvait viser l'ancienne coordonnée; tombstone et retry exigent maintenant identité image et parent exactes. | Chaîne autoritative `2f493c5948771f6c10b5dc04c267620e55343e1b`, `c9272ff1ba46b66a12bc807b895077f010c43717`, puis correctif final `a04f1d2bc7ada60603e6bf8c06d746ace112d99f`; `test_workspace_folder_generated_image_delete_retry.py::test_retry_after_remote_delete_and_failed_tombstone_finishes_on_exact_404` et `::test_durable_parent_rename_before_tombstone_refuses_stale_delete_coordinate` traversent DELETE, parent et store. | Livré : retry exact peut finir; identité/parent changés refusent le faux succès. Limite : courses DAV/DB simulées. Réouvrir si un `404` tombstone une autre identité ou si le parent courant n'entre pas dans la précondition. **Effet : indirect.** |
| F20.1 — sources Web/bloc injecté | **corrigé — L7.3.1.** Le manifeste soustrayait un bloc au nombre de sources et confondait bloc construit et insertion réelle; les compteurs sont maintenant tous en unités sources et gouvernés par la preuve d'injection. | `012664a915397b495066b2225e0ba9e2f24a46df`; `test_main_payload_manifest.py::test_prepare_main_payload_projects_real_web_insertion_source_counts` traverse préparation, injecteur, manifeste et projection admin. | Livré : `N/N/0` si injecté, `N/0/N` sinon. Limite : compteurs, pas qualité des sources. Réouvrir si un bloc unique redevient l'unité ou si sa seule présence prouve l'injection. **Effet : observabilité/outillage seulement.** |
| F20.2 — portées herméneutiques | **corrigé — L7.3.2.** Une fenêtre durable, des compteurs process-local et l'échantillon du log courant étaient mélangés sous un taux global; API et UI rendent désormais trois `measurement_scopes` distincts. | `d474a6cadfc0ee5536b8224791a90ce54decb3d6`; `test_server_admin_hermeneutics_phase4.py::test_dashboard_separates_durable_runtime_and_current_log_sample_scopes` et `test_hermeneutic_admin_render_scopes.js::hermeneutic overview renders three scopes without a global current window` traversent service, route et rendu. | Livré : aucune « fenêtre courante » globale inventée; `started_at` process reste `null`. Limite : aucune collecte nouvelle. Réouvrir si les populations sont recombinées ou si leur portée disparaît des labels. **Effet : observabilité/outillage seulement.** |
| F20.3 — compteur de problèmes | **corrigé — L7.3.3.** Le dashboard omettait `failed_count` et pouvait rendre un échec « Stable »; le renderer préfère `problem_count` canonique et son fallback historique somme error+failed+fallback. | `e2db300f9b36f1b82b6678e814abee83413588ad`; `test_dashboard_analytics_lot2.py::test_dashboard_status_taxonomy_distinguishes_legacy_noops_and_true_failures` traverse événements, facts, résumé conversation et buckets, puis `test_frontend_browser_smoke.js::dashboard overview renders pulse and conversations from aggregate endpoints` traverse endpoints agrégés, renderer et DOM. | Livré : un `failed` isolé compte comme problème, un zéro canonique reste zéro. Limite : données synthétiques. Réouvrir si `failed` disparaît ou si les composants écrasent un `problem_count` explicite. **Effet : observabilité/outillage seulement.** |
| F20.4 — bornes temporelles | **corrigé — L7.3.4.** Overview par buckets et conversations par facts pouvaient couvrir des intervalles différents; les customs réduisent désormais les facts exacts `[start,end)` et seules les fenêtres prédéfinies alignées utilisent les buckets. | Chaîne autoritative `8cf166c468465db03ed9f0fb9a5785d016238741` puis correctif final `a8ad0844733afc11a277de61f27b5f83ba50abb4`; `test_dashboard_time_window_consistency.py::test_old_aligned_custom_window_uses_exact_facts` traverse fake relationnelle, overview et cinq surfaces avec les mêmes bornes. | Livré : pas de tour inclus d'un côté et exclu de l'autre par géométrie de bucket. Limite : pas d'événements opérateur live. Réouvrir si une custom alignée relit des buckets historiques absents ou si une surface recalcule ses bornes. **Effet : observabilité/outillage seulement.** |
| F20.5 — audit du content gate | **corrigé — L7.3.5.** Le callback retournait `stored=true` même après échec d'écriture; le writer retourne maintenant la vérité du write et la route la transmet sans bloquer l'ouverture volontaire. | `76e06ef8ce5c6c2220303ba27d15e66e22cce433`; `test_admin_logs_write_result.py::test_log_event_returns_false_when_no_line_can_be_written` puis `test_server_admin_dashboard_contract.py::test_dashboard_turn_content_route_keeps_content_open_when_audit_write_fails` traversent writer, callback et read-model. | Livré : `attempted=true/stored=false` sans ligne; ouverture inchangée. Limite : OSError injectée, pas de panne filesystem live. Réouvrir si acceptation du callback redevient preuve de stockage. **Effet : observabilité/outillage seulement.** |
| F21 | **corrigé — L4.** Une panne de lecture des événements appelait le writer nominal avec des listes vides et effaçait les analytics; l'échec ne met plus à jour que le statut content-free. | `44924b0cf0acefcb5e834c979e2d564a0c7275bc`; `test_dashboard_analytics_lot2.py::test_source_read_failure_preserves_all_persisted_analytics_and_only_upserts_status` traverse fake relationnelle, transaction et reprise saine. | Livré : facts, summaries et buckets antérieurs survivent à la panne source. Limite : SQL factice, pas de panne PostgreSQL réelle. Réouvrir si une erreur source émet un DELETE/remplacement analytics. **Effet : observabilité/outillage seulement.** |
| F22 | **corrigé — L7.5.** Deux suites Identity obsolètes semblaient actuelles, dont une importait un applicateur supprimé; le runner général les retire et refuse leurs noms avant credentials, client ou sortie. | `78cfe1350fb57f2515aa5ce7de71e2858a6711e7`; `test_model_benchmark.py::test_retired_suites_are_rejected_before_credentials_or_output` traverse la vraie CLI et `::test_importing_active_runner_does_not_load_retired_identity_suites` sa frontière d'import. | Livré : artefacts historiques conservés mais non exécutables comme benchmark HEAD. Limite : aucune campagne ou comparaison modèle. Réouvrir si les suites réapparaissent dans `--help` ou atteignent credentials/provider. **Effet : observabilité/outillage seulement.** |
| F23 | **corrigé — L1.** Le Compose local publiait implicitement sur toutes les interfaces tout en étant présenté loopback; l'unique mapping est maintenant `127.0.0.1:8093:8089`. | `fe7cfe74e11de52e0c1de99035c7f3ae957c4df3`; au HEAD Z, `docker compose -f docker-compose.yml -f - config` alimenté par l'override `services.fridadev.env_file: !reset []` prouve `host_ip=127.0.0.1`, `published=8093`, `target=8089`, et le healthcheck interne loopback; le témoin Python réaligné passe `1/1`. | Livré pour le clone local; runtime OVH et Caddy/Authelia explicitement inchangés. Limite : pas d'audit réseau hôte. Réouvrir si le mapping perd son IP ou si la documentation le présente comme exposition publique protégée. **Effet : aucun effet produit.** |
| F24 | **corrigé — L7.6.** Le finalizer historique pouvait accepter une permutation de variantes et attribuer le score au mauvais candidat; une garde commune authentifie manifeste, calendrier, ledger, mapping et packet avant scorer/purge, puis les tests historiques ont été requalifiés selon leur vraie provenance gelée. | Chaîne autoritative `6b3fd405c5fc4ef5820d55fb49f9ad01c70f43d8` puis requalification finale `eb8870740e8b7d39504f5e64a9361d397d9babe5`; `test_l7_6_stimmung_finalization_integrity.py::test_variant_swap_is_rejected_before_scorer_or_purge` et `::test_v25_nominal_finalizer_reuses_the_shared_guard` traversent les vrais finalizers offline. | Livré uniquement à l'outillage historique; runtime Stimmung et `keep_current_v2.3` inchangés. Limite : aucun provider, canari ni gain sémantique actuel mesuré. Réouvrir avant toute réutilisation si provenance/variants ne sont plus recroisés. **Effet : observabilité/outillage seulement.** |

### 11.3 Réserves Biblio non numérotées

Ces quatre réserves ne deviennent pas de nouveaux findings. Après le correctif
borné, les `95` tests actuels de `test_answer_object`,
`test_librarian_planner` et `test_librarian_tools` passent au HEAD, sans réseau.

| Réserve | Limite exacte | Bug reproduit et effet concret | Condition de réouverture |
| --- | --- | --- | --- |
| Budgets d'outils | Le planner initial contrôle `max_steps`, `max_tool_calls` et `max_total_duration_ms` entre ses appels. Les continuations déterministes de `librarian_method_runtime.py` passent toutefois par `append_get_tool_call`, qui ne contrôle que le reliquat `max_tool_calls`; elles ne recomptent ni `max_steps` ni la durée, reconduisent le `duration_ms` initial et ne peuvent interrompre un appel HTTP bloqué. Ces budgets ne sont donc ni tous globaux aux continuations, ni une deadline murale. | Mécanisme confirmé par code et sonde content-free : avec `max_steps=0`, `max_total_duration_ms=0` et `duration_ms=999`, une continuation ajoute encore un appel. **Bug produit non établi** : `max_tool_calls` reste borné, aucun contrat courant ne promet une deadline murale et aucune gêne live n'a été mesurée. | Réouvrir si un contrat présente ces trois budgets comme globaux à toute la méthode, si une continuation dépasse une limite produit requise, ou si une gêne de latence réelle est observée. |
| Introduction produite avant le résultat | `surface_intro` est générée avec le plan, avant l'exécution, puis conservée autour du résultat verrouillé. | Mécanisme confirmé, **bug non reproduit** : aucune introduction actuelle contredisant un échec ultérieur n'a été produite et aucune fréquence live n'est connue. | Réouvrir sur un témoin déterministe ou content-free montrant une introduction formulée après coup ou comme un succès, mais incompatible avec le statut finalement rendu. |
| Inventaire plus large que les lignes | `document_count` continue de compter les documents dédupliqués retenus, jusqu'à 100; le renderer détaille au plus les 20 premiers. | **Correctif et preuve composée fermés le 7 septembre 2026.** Le chemin agentique réel `catalog_list -> objet-réponse -> renderer` rend 12/12. Le même renderer hermétique prouve 1/1, 20/20/0 et 25/20/5; avec `total_count=40` et `document_count=25`, total répertorié, retenu, affiché et masqué restent distincts. Aucun plafond, outil, appel ni branche provider n'est ajouté. La cardinalité live de 12 est une limite de preuve, pas un bug produit ouvert. | Revalider lorsque le corpus live dépassera 20, ou plus tôt si un écart apparaît entre total, retenu, lignes annoncées/rendues et reliquat masqué. |
| Scoped search après top-N global | `catalog_search(query, limit)` obtient d'abord le top-N global, puis filtre sur `document_id`; un passage pertinent du document peut donc rester hors du top-N. | Mécanisme confirmé, **bug non reproduit** : le rendu dit qu'aucun *candidat restant* n'existe dans le scope, pas qu'aucun passage n'existe dans le document; aucun faux « absent du livre » n'a été observé. | Réouvrir si la surface transforme ce résultat borné en absence exhaustive, ou si un cas produit établi montre une affirmation contraire au contenu accessible. |

### 11.4 Ce que la réconciliation change dans le dialogue

Les corrections directes empêchent maintenant qu'une erreur provider devienne
une parole achevée, qu'une sauvegarde ancienne retire un tour récent, qu'une
panne Identity efface le canon, qu'un résumé non stocké retire des paroles du
travail futur, ou qu'une correction Memory soit fusionnée avant jugement. Elles
rendent également les réponses Biblio, Agenda, Web, ODT et OCR plus fidèles à
ce qui a réellement été lu, demandé ou remplacé.

Les corrections indirectes protègent surtout les effets périphériques du
dialogue : versions Nextcloud, cohérence fichier/SQL, renommages, exclusions
courantes et tombstones. Les corrections F07, F16, F18, F20, F21, F22 et F24
améliorent la vérité de l'inspection et des outils; elles ne changent pas à elles
seules ce que Frida comprend ou dit. F23 ne change pas le produit : il ferme la
publication réseau implicite du clone local.

Cette matrice ne permet toujours pas d'affirmer que Frida retrouve toujours le
meilleur souvenir, interprète correctement Tof, choisit la correction juste,
lit exhaustivement un document, ou produit globalement un meilleur dialogue.
Le correctif Biblio rend le nombre « affiché » quantitativement égal aux lignes
détaillées dans le témoin 25/20/5, sans transformer ce rendu borné en inventaire
exhaustif. Le corpus live actuel de 12 ouvrages ne permet pas de franchir la
borne de 20 ; cette limite de preuve déclenche une revalidation lorsque le
corpus la dépassera et ne maintient pas P01 en échec produit.
Le panier Memory reste borné à huit. B1 ne fournit pas d'offset intra-page.
Stimmung reste constitutive, `keep_current_v2.3` reste la décision active, et Z
n'en déduit aucune amélioration sémantique globale. La latence actuelle n'est
pas mesurée; conformément à la décision opérateur du Lot 7, 7C ne devient pas
requis sans gêne réelle observée. Aucune panne réelle PostgreSQL, Nextcloud ou
CalDAV, ni fréquence live des défauts historiques, n'a été observée.

### 11.5 Passe finale tests/preuve/docs du 7 septembre 2026

Avant patch, les trois témoins autorisés ont été reproduits isolément :

- Compose : `1/1` échoué sur l'attente pré-F23 `8093:8089` face au mapping
  courant `127.0.0.1:8093:8089` ;
- Chromium terminal vide : timeout de 30 s sur `#threads li.active`, avant les
  assertions de canon vide ;
- Chromium Workspace : timeout de 30 s sur `.workspace-folder-row`, avant les
  assertions dossier, drag-and-drop et OCR.

Après le patch strictement tests-only :

- `test_answer_object` passe **46/46** et couvre explicitement 1/1, 20/20/0,
  25/20/5 et le cas distinct `total_count=40`, `document_count=25`, 20 lignes
  visibles et 5 masquées ;
- le témoin Compose exact passe **1/1** ;
- les contrôleurs Node F17/F05/F13a passent **38/38**, sans échec, skip ou todo ;
- Chromium terminal vide passe **1/1** en `606,928 ms` et atteint les
  assertions `final_text=""`, absence d'assistant canonique et export sans
  brouillon fantôme ; les 18 autres scénarios du fichier sont filtrés par le
  nom exact, pas le scénario prouvé ;
- Chromium Workspace passe **1/1** en `1 626,753 ms`, sans filtre ni skip, et
  atteint les assertions de repli/dépli, navigation, sélection, OCR et
  drag-and-drop ;
- `node --check` passe sur les deux fichiers Chromium modifiés et
  `git diff --check` ne relève aucun écart.

La découverte Python complète a ensuite été lancée **exactement une fois** avec
la commande demandée `python -m unittest discover -s tests -p 'test_*.py'`.
Elle a tourné dans le conteneur nommé et détaché
`fridadev-z-final-python-discovery-20260907`, réseau désactivé, filesystem
read-only, checkout readonly, `/tmp` isolé et variables provider neutralisées.
Stdout/stderr et code de sortie ont été écrits sur un montage hôte temporaire,
lus après la fin du conteneur, puis supprimés avec celui-ci après consignation.

Résumé autoritatif récupéré : **3079 tests, 580,007 s, 11 échecs, 7 erreurs,
0 skip, exit code 1**. Aucune seconde découverte complète n'a été lancée.

Classification ciblée des 18 anomalies :

1. **Agenda, 1 erreur d'isolation de modules.** Le test
   `test_agenda_read_execution_classifies_calendar_domain_exhaustion` passe
   seul `1/1` et son module passe `9/9`. La sélection ordonnée
   `test_caldav_read_tools` puis `test_rrule_expander` reproduit l'erreur sur
   `36` tests : le premier module recharge `agenda.rrule_expander`, créant une
   nouvelle classe `IcsRecurrenceUnsupportedError`, tandis que
   `read_execution` conserve l'ancienne classe importée. Aucun défaut Agenda
   produit n'est établi, mais la suite complète reste non hermétique entre
   modules.
2. **Stimmung historique, 6 erreurs de gels supersédés.** Trois anciens modules
   tentent encore de reconstruire positivement les protocoles v2/v2.3 et
   rencontrent correctement `freeze_manifest_mismatch` après F24. Leur
   sélection ciblée reproduit 6 erreurs. Les quatre modules F24 autoritatifs,
   qui authentifient les archives et refusent la réutilisation des runners,
   passent **50/50** en `263,679 s`. Ces anciens témoins sont incompatibles
   avec la décision F24 déjà livrée ; ils ne rouvrent pas Stimmung, mais restent
   des erreurs actives de découverte.
3. **Fake de conversation Stimmung, 10 échecs.** Neuf tests du module causal et
   un voisin final-wording s'arrêtent sur `synthetic Stimmung store seed
   failed`. Leur fake de curseur traite encore tout premier curseur comme un
   simple `INSERT ... RETURNING` et ne sait pas exécuter le `SELECT ... FOR
   UPDATE`/`fetchall()` ajouté par la précondition canonique F09. Le module
   courant du store conversationnel passe **18/18**. Aucun défaut du store ou
   de Stimmung n'est établi, mais ces dix preuves historiques restent
   incompatibles avec le contrat F09.
4. **Témoin documentaire, 1 échec.** Le test
   `test_identity_archive_and_hermeneutic_suspension_todo_are_aligned` échoue
   seul `1/1` parce qu'il exige encore la phrase
   `web search manuelle et auto-bornee degradees`, retirée volontairement lors
   de L7.7 au profit du contrat courant de recherche Web explicite. Le document
   vivant est cohérent avec L7.7 ; l'assertion reste périmée.

### 11.6 Décision d'archivage

La réserve Biblio reste fermée selon la preuve composée décidée. Son chemin
agentique live 12/12, son renderer 25/20/5 et son déclencheur de revalidation
au premier corpus live supérieur à 20 restent inchangés. Aucun F01-F24, choix
Biblio, Agenda, Stimmung ou F09 n'est rouvert.

Le micro-lot final part de `main` au HEAD/upstream/distant
`b29b7527b5738bff257384ad2d7e9039e4eb51d2`, divergence `0/0` et worktree
propre. Les reproductions rouges distinguent les quatre causes attendues :

1. Agenda : ordre `test_caldav_read_tools` puis `test_rrule_expander`, 36 tests,
   1 erreur d'identité de `IcsRecurrenceUnsupportedError` après reload ;
2. anciens témoins Stimmung : 14 tests exécutés, 6 erreurs
   `freeze_manifest_mismatch` et 1 échec voisin de fake F09 ;
3. fake conversationnelle : 14 tests, 10 échecs
   `synthetic Stimmung store seed failed` ;
4. assertion L7.7 : 1/1 rouge sur la phrase historique retirée.

Les corrections restent dans tests/support. L'import Agenda est déplacé dans
un sous-processus et l'identité des modules parents est vérifiée inchangée. Les
anciens témoins authentifient les manifestes selon leurs SHA historiques,
réutilisent seulement le finalizer offline F24 et prouvent que runner, dry-run,
credentials, provider, progression et fichiers restent inatteignables au HEAD.
La fake Stimmung suit désormais `INSERT ... RETURNING`, la lecture canonique
ordonnée `SELECT ... FOR UPDATE` avec `fetchall()`, la réconciliation F09,
`DELETE`, `executemany()` et commit transactionnel ; un snapshot périmé échoue
sans commit ni mutation du canon. L7.7 vérifie précisément la dégradation de la
recherche Web explicite sans SearXNG, le caractère historique et retiré de
l'auto-Web lexical, et la référence au pipeline courant.

Les preuves après patch passent : Agenda dans l'ordre initial, l'ordre inverse,
le module seul et l'import sans lecture de secret ; anciens témoins et sélection
F24 dans la même session **72/72 en 311,281 s**, dont les **50/50** autoritatifs ;
fake causale et voisin **15/15 en 5,762 s** ; L7.7 **1/1** ; store courant
**18/18** ; sélection commune **141/141 en 315,281 s**. Le contre-audit ne
trouve aucun test supprimé, skip, xfail, expected failure, retry, timeout
d'exécution augmenté, runner réactivé, succès préprogrammé, modification de gel
Stimmung ou changement de code produit/runtime.

L'unique découverte complète de ce micro-lot, lancée avec la commande demandée
dans un conteneur nommé, read-only, checkout read-only, `/tmp` isolé et réseau
coupé, termine cependant à **3088 tests en 613,603 s, 2 échecs, 0 erreur,
0 skip, exit 1**. Son harnais avait neutralisé non seulement les credentials,
mais aussi les trois URL de configuration `EMBED_BASE_URL`, `CRAWL4AI_URL` et
`SEARXNG_URL`. Les deux tests de validation de secrets candidats refusent alors
correctement les sections globalement invalides. Une reproduction ciblée avec
les mêmes champs vides échoue 2/2 ; le contre-cas avec des URL synthétiques
`https://embed.invalid`, `https://crawl.invalid` et `https://search.invalid`,
réseau toujours coupé et tokens vides, passe 2/2 en 0,001 s. Il s'agit d'un
écart de commande, pas d'une baseline produit ni d'un cinquième finding.

Z ne peut néanmoins pas être fermé sur cette sortie rouge et la découverte ne
doit pas être relancée dans ce lot. Le prochain micro-lot est strictement
preuve/docs-only : une unique découverte complète explicitement autorisée,
avec credentials provider et tokens neutralisés mais URL de services support
synthétiques `.invalid` valides, puis archivage seulement si elle est verte.
La roadmap et le grand audit restent dans `todo-todo`; aucun déplacement vers
`todo-done` ni lien d'archive concurrent n'est créé.

## 12. Risques permanents et non-objectifs

- Cette roadmap ne mesure pas la fréquence live des défauts historiques ni le
  bénéfice dialogique global.
- Elle ne prouve pas PostgreSQL, Nextcloud ou CalDAV sous panne réelle ; les
  preuves applicatives hermétiques restent explicitement bornées.
- Elle ne traite ni sauvegardes plateforme, restauration après sinistre,
  performance actuelle, prix/disponibilité des modèles, ni sécurité générale
  de l'OVH.
- Elle ne crée pas de résolution générale des contradictions, de vérité
  temporelle, de mémoire parfaite ou de lecture exhaustive de tout document.
- Elle ne rouvre pas les décisions fermées des roadmaps précédentes.
