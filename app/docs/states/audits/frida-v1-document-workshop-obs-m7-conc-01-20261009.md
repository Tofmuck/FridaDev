# OBS-M7-CONC-01 — diagnostic causal borné du 9 octobre 2026

Base `c1654c25b14bde72439d2b892f9014362749f1e6`, parent
`1732a1266d4b573734ea0ea72baa72dea5e563ca`, branche
`FridaV1-Document-Workshop-M8-C`. Mandat : diagnostic, preuves et documentation
seulement, puis livraison Git et arrêt pour contre-audit Codex.

**Qualification : attente de terminalité immédiate du test contredite par un
entrelacement autorisé et reproduit.** Une cause suffisante est établie sous
barrières ; l'ordonnancement exact des échecs indépendants initiaux reste inconnu.
Aucun défaut produit, blocage permanent, double effet ou corruption n'est démontré.
OBS-M7-CONC-01 est diagnostiqué dans cette portée, sans correctif appliqué ni
requalification des observations historiques en invalides.

Le [relevé daté](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-20261009.json)
porte commandes complètes, IDs, versions, exits, durées, empreintes, provenance,
incidents de sonde et nettoyage. Les [traces synthétiques corrélées](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-20261009.jsonl)
conservent chaque run instrumenté, distingué par son label ; seules les deux
exécutions `delivered-control` et `delivered-overlap` prouvent la sonde livrée.

## Autorités et limite de l'assertion

Le [contrat M7](../specs/frida-v1-document-workshop-m7-contract.md#put-et-conflits)
prévoit explicitement le refus SQL NOWAIT après succès DAV, une tentative de
clôture du seul claim, puis l'autorité de l'expiration de lease si SQL reste
occupé. Le [contrat M3](../specs/frida-v1-document-workshop-m3-contract.md#lease-flux-et-états)
fixe la lease à 90 secondes et le renouvellement à 15 secondes, selon
`clock_timestamp()` PostgreSQL. Cette borne part de l'admission ou du dernier
renouvellement ; elle n'ajoute pas 90 secondes après la réponse HTTP.

Le test exact est
`tests.integration.document_workshop.test_update_m7_postgresql.UpdateM7PostgresqlTests.test_two_inflight_conversations_same_version_at_most_one_publication`.
Après deux futures HTTP, il exige immédiatement `succeeded`, `conflict` ou
`remote_uncertain`, puis zéro claim actif. La fin des futures ne prouve pas une
clôture SQL réussie ni une lease expirée. Le contre-exemple éprouve aussi la
transition prévue après expiration ; la clause contractuelle n'est pas utilisée
pour justifier arbitrairement toute action `executing`.

## Chronologie causale éprouvée

Les rôles gagnant/perdant viennent des vrais résultats DAV 204/412, pas d'un
ordre supposé des threads A/B. Les IDs, owners, générations, leases, PID et
transactions figurent dans les traces monotones.

1. Deux préparations et deux confirmations réelles, dans deux conversations,
   prennent leurs claims M3 distincts. Deux PUT avec le même `If-Match: "v1"`
   arrivent au serveur DAV synthétique. Comme dans le test historique, aucun
   verrou SQL ne couvre l'attente DAV. La libération produit exactement un
   effet distant : version 2, un résultat 204 validé et un résultat 412.
2. Le perdant 412 entre dans la vraie transaction `execution_store.observe`.
   Après le vrai `_resources`, il détient notamment le verrou de ligne
   `workspace_folders FOR UPDATE NOWAIT`. La barrière conserve cette transaction
   jusqu'au retour HTTP du gagnant. Une connexion indépendante relève son PID,
   son XID et `idle in transaction`. `pg_locks` expose ses verrous de relation et
   de transaction ; il n'expose pas nécessairement chaque verrou de tuple.
3. Le gagnant 204 tente réellement `observe` : `_guard/_resources` refuse le
   verrou du répertoire avec `LockNotAvailable / 55P03`, puis rollback. Son
   outcome de succès n'est pas durable ; `publish` n'est jamais atteint.
4. Le gestionnaire d'exception trouve `put_intent` et tente `finish` en
   `remote_uncertain`. Le même verrou provoque `55P03` et rollback.
5. `ChatReservation.close` arrête réellement son superviseur et tente
   `claims.finish`. Le `FOR SHARE NOWAIT` de `_scope` rencontre le même verrou :
   rollback brut `55P03`, traduit en `ClaimError/conversation_turn_conflict`.
   L'erreur de clôture reste absorbée par la branche existante. Le claim SQL
   conserve `active`, une lease future et aucun outcome.
6. Les réconciliations de fin de requête relisent ce claim encore actif et
   conservent l'action `executing/confirmed`. La confirmation du gagnant répond
   HTTP 200 avec cette projection et sans reçu. Cela n'est pas un succès publié.
   La barrière libère ensuite le perdant : son observation commit, puis son
   action devient `conflict` et sa confirmation répond 409.
7. Après les deux réponses et la sortie effective des deux superviseurs, un
   SELECT indépendant, en transaction de lecture seule, précède chaque GET.
   Le premier GET du gagnant conserve exactement le snapshot SQL :
   `executing/confirmed`, claim actif avec lease future, aucun reçu.
   L'assertion historique `assertIn` est réellement exécutée et capturée rouge.
8. Après arrêt et join des superviseurs, la sonde place **artificiellement** la
   seule lease du gagnant dans le passé, dans la base jetable. Avant le GET,
   l'action est toujours `executing`, le claim encore `active` mais expiré.
   Le GET réel appelle `actions.get_action → execution_store.reconcile →
   claims.read`, constate `lost`, puis passe l'action à
   `remote_uncertain/interrupted`. La réconciliation de métadonnées ne publie
   rien : aucun `remote_outcome` du gagnant n'est durable. Aucun nouveau PUT.

Le contrôle appelle les mêmes méthodes et relève les mêmes mesures. Son seul
facteur causal différent est la libération du perdant : le gagnant attend le
retour HTTP du perdant, donc la fin de ses transactions, avant `observe`.
Observation et publication du gagnant réussissent alors : `succeeded`, un reçu,
un rendu ; le perdant reste `conflict`. L'assertion historique est verte.
Un échec de `close` peut aussi survenir dans ce contrôle, après clôture déjà
réussie du claim ou invalidation du contexte ; cette exception seule ne prouve
pas un claim SQL resté actif. Les snapshots distinguent ces situations.

## Invariants observés au-delà de l'assertion rouge

| Mesure | Contrôle | Chevauchement imposé |
| --- | --- | --- |
| PUT reçus / effets distants | 2 / 1 | 2 / 1 |
| Identité distante / version | file-id 42 / 2 | file-id 42 / 2 |
| Fichiers locaux / liens | 1 / 1 | 1 / 1 |
| Reçus / rendus publiés | 1 / 1 | 0 / 0 |
| Premier GET du gagnant | `succeeded`, reçu | `executing/confirmed`, aucun reçu |
| Claim du gagnant après réponses | `succeeded` | `active`, lease future |
| Après expiration artificielle + un GET | Sans objet | `lost` / `remote_uncertain` |
| Claims confirmation actifs à la fin | 0 | 0 |
| DELETE / MKCOL / compensation update | 0 | 0 |
| Replay des deux confirmations | Aucun DAV, aucun nouvel état SQL | Aucun DAV, aucun nouvel état SQL |

La répétition compare les snapshots, le journal, le nombre total de claims,
les fichiers/liens/reçus/rendus et l'absence de tout nouvel appel DAV. Elle
n'autorise aucune nouvelle soumission ou attribution de succès au gagnant inconnu.

## Exécutions et comparabilité

Aucune instrumentation lors des trois premières sélections, séquencées sur une
unique base dédiée, sans autre runner sur ce socket : SQL seul **29/29**,
cas exact **1/1**, SQL + client **34/34**. Aucun skip, échec ou erreur.
Le ciblé et le SQL du groupe combiné réutilisent les mêmes identités : aucun
cumul de ces runs en une nouvelle comparaison produit.

Même sélection combinée, images, options, ordre de modules, environnement vidé,
répertoire et variables de preuve que le relevé AUD-02 vert. Seuls les noms
possédés de conteneur/socket changent. Le module client est chargé avant
l'exécution des tests par unittest ; sa lecture et une sonde d'import confirment
qu'il ne remplace ni les méthodes des stores/client ni les constantes de lease.
Aucune cause runner, import ou charge n'est prouvée par la différence de verts.

Runners existants : `fridadev-audit-py:latest`, Python 3.11.15, Flask 3.0.3,
Requests 2.32.3, psycopg 3.3.4 ; `postgres:16-alpine`, PostgreSQL 16.12.
Le relevé porte les IDs d'images et la comparaison avec les versions AUD-02.
Checkout `/workspace:ro`, travail `/workspace/app`, rootfs read-only,
`--pull=never --network none`, `/tmp` en tmpfs, environnement `env -i`, bytecode
inactif, endpoints auxiliaires `.invalid`, socket dédié `/proof/sock:ro`.
Le serveur HTTP DAV est synthétique et interne au namespace sans réseau extérieur.

Commande applicative de la sonde autonome, sous ce même runner décrit intégralement
par `records[*].argv` :

```bash
python -m tests.support.probe_obs_m7_conc_01 --scenario control
python -m tests.support.probe_obs_m7_conc_01 --scenario overlap
```

La [sonde](../../../tests/support/probe_obs_m7_conc_01.py) exige explicitement un
socket jetable : la fixture historique recrée le schéma public. Elle ne crée ni
socket, ni thread, ni import applicatif à l'import ; contrôle dédié avec ces
effets interdits réussi. Aucun test volontairement rouge n'est ajouté à la
découverte ordinaire. Le rouge contrôlé est capturé comme résultat diagnostique.

## Provenances historiques conservées

- Contre-audit indépendant du 7 octobre, HEAD `1732a126`, transmis par Tof :
  deux groupes SQL inchangés **28/29**, même assertion ; **1 674/1 677**, plus
  96 voisins verts séparés. Les assertions postérieures au premier GET rouge
  n'avaient pas été atteintes ; aucun état ultérieur n'avait été observé.
- Contre-audit indépendant du 9 octobre, HEAD `c1654c25`, transmis dans ce mandat :
  SQL **28/29**, même assertion ; comparaison **1 689/1 690**, 96 voisins verts
  séparés. Les cinq tests client passent séparément après arrêt SQL. Bases et
  sockets distincts, groupes partageant une base séquencés : aucune attribution
  à un chevauchement de schémas d'autres runs.
- Relevé Celebrimbor AUD-02 du 9 octobre : groupe combiné **34/34** et
  comparaison **1 690/1 690**, voisins **70 + 26** séparés. Ces verts restent
  distincts et ne réfutent aucun rouge indépendant. Les incidents de fixtures
  de ce relevé ont leur propre provenance ; ils n'expliquent pas OBS-M7-CONC-01.
- OBS-M7-UI-01 (`phone light` / `phone dark`, clic sidebar, 11/13 le 7 octobre)
  et M4 historique 21/22 puis rejeux 22/22 restent séparés, causes initiales
  inconnues. Aucun diagnostic ou correctif de ces sujets ici.

Selon le mandat de Tof du 9 octobre, AUD-01 et AUD-02 sont fermés après
contre-audits indépendants. Leurs corrections renderer ne sont pas exercées par
ce parcours Markdown. Aucun nouveau run intégral de 1 690 cas ni des 96 voisins
n'est revendiqué dans ce diagnostic ; aucun lot suivant ne démarre.

## Auto-audit, contre-lecture et suite proposée

Les wrappers appellent les vraies méthodes et préservent valeurs, connexions,
transactions, exceptions et contrôles de scope/owner/génération/lease. Ils
tracent des codes d'erreur, jamais des exceptions brutes ou du contenu documentaire.
Les mesures indépendantes utilisent SELECT en lecture seule, sans verrou de ligne
mutateur. L'assertion SQL historique avant libération DAV est conservée telle
quelle ; elle précède la fenêtre causale. La barrière prolonge volontairement
un verrou réel déjà acquis ; elle impose un entrelacement, elle ne prétend pas
observer passivement la course initiale. Les mêmes mesures existent au contrôle.

Aucun renouvellement n'est suspendu ou remplacé. Le join suit la clôture réelle
et l'arrêt produit ; la lease n'est modifiée qu'ensuite dans la base possédée.
La preuve n'attend pas naturellement 90 secondes : elle démontre la frontière
SQL d'expiration et la convergence au GET, sans affirmer avoir mesuré sa durée
naturelle. Aucun GET réparateur n'est confondu avec le SELECT préalable.

La seconde lecture indépendante a confirmé la chaîne et la qualification,
puis fait corriger la corrélation des événements d'expiration artificielle et
d'assertion vers l'observateur et l'action concernée. Les deux scénarios ont été
rejoués après cette correction de trace. Le premier lancement de sonde avait
échoué dans sa préparation manuelle de la seconde conversation ; le vrai helper
`conv_store.new_conversation/save_conversation` du test a été rétabli. Cet échec
de harnais, ses commandes et durées restent dans le relevé, sans attribution produit.

**Proposition de micro-lot ultérieur, non exécutée :** corriger uniquement la
preuve de concurrence M7. Séparer explicitement le contrôle publication nominale
et le chevauchement NOWAIT démontré, avec barrières sur les méthodes réelles.
Dans la branche de clôture refusée, vérifier d'abord `executing/confirmed` sans
reçu et claim SQL vivant, après sortie effective des superviseurs ; puis éprouver
la frontière d'expiration dans la DB de test et conserver l'assertion terminale
après un unique GET. Garder les bornes de publication, les deux PUT/un seul effet,
zéro compensation et les contrôles anti-replay. Ne pas ajouter `executing` à la
liste terminale, remplacer la preuve par un sommeil/polling, ni changer le produit,
les leases ou les gardes. Ce micro-lot nécessite son mandat distinct.

Produit, migrations, tests historiques et fixtures communes restent inchangés,
vérifiés par diff et empreintes. Seuls sonde, rapport, traces/relevé et notices
vivantes sont livrés. Nettoyage des seuls conteneur/socket/temporaires possédés,
avec vérification de disparition dans le relevé. Aucun runtime opérateur, secret,
Writer, AF_UNIX renderer, DAV/Nextcloud live, OpenRouter, installation ou déploiement.
