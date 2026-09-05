# FridaDev — consolidation résiduelle du grand audit de recherche

Date de cadrage : 4 septembre 2026.

**Statut : roadmap ouverte ; L1 à L5, L6.1 et L6.2 fermés ; L6 en cours ;
L6.3, L7 et Z non commencés.**

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
| 6 | L6 | Justesse produit directement perceptible | F05, F10, F12, F13a, F14b, F15, F19a | high/xhigh par sous-lot | en cours — L6.1/F05 et L6.2/F10 corrigés ; L6.3 non commencé |
| 7 | L7 | Vérité d'API, observabilité et outils historiques | F16–F18, F20, F22, F24 et dette documentaire | high | non commencé |
| 8 | Z | Réconciliation finale avec le grand audit | tous les Fxx et réserves non numérotées | xhigh | non commencé |

- [x] Source, périmètre, ordre et règles de preuve consignés.
- [x] L1 fermé.
- [x] L2 fermé.
- [x] L3 fermé.
- [x] L4 fermé.
- [x] L5.1 fermé.
- [x] L5.2 et L5.3 fermés.
- [x] L6.1 fermé ; F05 corrigé et cas terminal vide corrigé après reproduction.
- [x] L6.2 fermé ; F10 corrigé sur les quatre familles frontend confirmées.
- [ ] L6 et ses décisions conditionnelles fermés.
- [ ] L7 et ses décisions conditionnelles fermés.
- [ ] Z réconcilie chaque finding et archive la roadmap.

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

### L6.4 — Agenda : récurrences extrêmes — F12c, diagnostic préalable

Reproduire ou invalider le dépassement YEARLY/INTERVAL avant tout patch. Si le
mécanisme est confirmé, borner l'expansion par COUNT et fenêtre demandée sans
ajouter de famille de récurrence. Si aucun contre-exemple contractuel n'existe,
fermer comme invalidé avec la preuve.

### L6.5 — Web : requête pertinente et source réellement officielle — F15a/F15b

Retirer ou dériver du sujet réel le gabarit AI Act hors sujet. Comparer les
sources à partir du host/path parsé plutôt que d'une sous-chaîne de l'URL
complète. Conserver budgets, profils et reranking existants.

### L6.6 — ODT : préserver les séparateurs textuels — F19a

Interpréter dans l'extracteur existant les éléments ODT d'espace, tabulation et
saut de ligne afin de ne pas concaténer des mots. Ne pas prétendre garantir la
fidélité universelle de tout ODT.

### L6.7 — Décisions conditionnelles — F13a et F14b

- **F13a :** établir d'abord si ré-OCR doit contractuellement remplacer un
  dérivé humain. Si oui, corriger uniquement le libellé création/mise à jour et
  l'avertissement nécessaire ; sinon cadrer séparément le changement produit.
- **F14b :** distinguer état courant et historique seulement si une surface ou
  une API affirme encore à tort qu'un document exclu est actuellement prêt ou
  injecté. Conserver l'historique utile.

## 10. L7 — Vérité d'API, observabilité et outils historiques

### L7.1 — Agenda pending observable — F16

Aligner les clés réellement émises et celles lues pour statut, niveau de
confirmation et risques. Tester writer → projection → read-model/API ; aucune
nouvelle surface.

### L7.2 — Conversations : succès, erreur et limite de liste — F17

Respecter `SaveResult` à la création, distinguer erreur SQL et liste vide, puis
décider la limite de 200 au regard du système mono-utilisateur. Ne pas ajouter
une pagination générique si aucun parcours existant ne peut la consommer.

### L7.3 — Portée des compteurs — F20

Traiter séparément les cinq mécanismes :

1. sources Web et blocs injectés ne sont pas la même unité ;
2. fenêtre durable et compteurs process-local doivent être nommés sans ambiguïté ;
3. `failed` doit suivre le compteur canonique du pipeline ;
4. buckets et conversations doivent employer la même borne temporelle ;
5. réception du callback de log ne doit pas devenir `audit.stored=true` si
   l'écriture fichier a échoué.

Un même micro-lot peut regrouper deux points uniquement s'ils partagent le même
read-model et le même correctif. Aucune collecte ou dashboard supplémentaire.

### L7.4 — Réglages Identity historiques — F18

Corriger classification et aide des knobs legacy sans les réactiver. Prouver
la politique réellement lue par le juge courant.

### L7.5 — Bancs Identity obsolètes — F22

Étiqueter ou retirer du parcours courant les suites qui ne mesurent plus leur
responsabilité annoncée. Ne pas lancer de campagne modèle et ne pas adapter un
scorer pour fabriquer une comparabilité au HEAD.

### L7.6 — Banc historique Stimmung — F24, garde avant réutilisation

Ne corriger que si ce banc doit être réutilisé. Avant calcul ou purge, recroiser
variant et sequence avec calendrier, mapping et ledger déjà disponibles. Aucune
nouvelle campagne et aucun changement de `keep_current_v2.3`.

### L7.7 — Passe documentaire bornée

Synchroniser seulement les affirmations encore fausses : vérifier la cohérence
finale de l'exposition du Compose traitée en L1, preuve admin loopback/proxy,
sections historiques Web, aide OCR, activation
Biblio, pré-appel Stimmung présenté comme réception, mélange des temps dans les
contrats herméneutiques et vocabulaire Identity legacy. Le grand audit reste
conservé comme source datée ; aucune réécriture générale du README.

## 11. Z — Réconciliation finale avec le grand audit

Z n'est pas un nouvel audit indéfini. Il vérifie uniquement les findings et
réserves recensés par le rapport du 2 septembre, dans le code alors courant.

### Matrice obligatoire

Pour chacun de F05, F08, F09, F10, F12a–c, F13a–b, F14a–b, F15a–b, F16,
F17, F19a–b, les cinq sous-cas F20, F21, F22, F23 et F24, consigner :

- état final : `corrigé`, `invalidé`, `différé avec condition` ou `ouvert` ;
- commit et preuve autoritative ;
- comportement runtime livré ou explicitement inchangé ;
- limite de preuve et déclencheur de réouverture.

Les réserves Biblio non numérotées sont relues séparément : budgets qui ne
sont pas des deadlines, introduction antérieure au résultat, inventaire compté
plus large que le rendu et scoped search après top-N global. Elles ne deviennent
des bugs que si leur affirmation produit trompeuse est reproduite.

### Tests finaux proportionnés

- tests ciblés de chaque frontière modifiée déjà acquis dans les lots ;
- JavaScript/Chromium seulement pour les surfaces effectivement changées ;
- une unique découverte Python hermétique complète au HEAD final ;
- contrôle des liens, `git diff --check`, temporaires, secrets et contenu brut ;
- aucun provider, benchmark live, DB opérateur ou dialogue réel ajouté pour Z.

### Bilan et archivage

Z ajoute au grand audit un court lien de suivi daté sans réécrire ses findings,
complète la matrice de cette roadmap, synchronise le hub, puis déplace la
roadmap dans `app/docs/todo-done/refactors/` seulement si aucun finding non
classé ne subsiste. Un finding explicitement différé avec condition n'empêche
pas l'archivage ; un finding oublié ou maquillé en acceptation l'empêche.

La clôture doit répondre en langage simple : ce qui a été réellement réparé,
ce qui a été prouvé faux, ce qui reste conditionnel, et ce que ces corrections
changent — ou ne changent pas — pour le dialogue quotidien avec Frida.

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
