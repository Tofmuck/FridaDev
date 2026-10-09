# OBS-M7-CONC-01 — Correction des preuves de concurrence M7

9 octobre 2026, Celebrimbor. Mandat tests/helpers/preuves/docs de Tof.
Branche `FridaV1-Document-Workshop-M8-C`, base exacte
`970ccb37750af1aa7f53486afcef00774d269c84`, parent de cette base
`c1654c25b14bde72439d2b892f9014362749f1e6`. Worktree initial propre,
HEAD/upstream/distant égaux, divergence `0/0`. Les 18 références locales et de
suivi M0–M7/main et les neuf têtes distantes sont capturées dans le
[relevé dédié](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.json).
Le commit de ce correctif a pour parent la base `970ccb37` ; sa référence de
livraison figure dans le retour Git, sans hash autoréférentiel dans sa preuve.

## Plan et constat

« Existe-t-il un meilleur plan ? » Conserver l'identité historique pour le
nominal et ajouter un seul cas NOWAIT/expiration est le changement minimal.
Aucun changement produit, migration, configuration, UI ou politique de lease.
Les méthodes, transactions, validateurs DAV, gardes et superviseurs restent réels.
Les deux PUT sont déjà en vol avec le même ETag préparé avant toute libération.
Seule la fin de l'observation SQL du perdant est ordonnée.

Le [diagnostic historique](frida-v1-document-workshop-obs-m7-conc-01-20261009.md)
est revalidé sur cette base : le perdant DAV 412 détient, dans son vrai `observe`,
le verrou du répertoire ; le gagnant 204 rencontre trois refus `55P03` dans
`observe`, `finish` et `claims.finish`. Les superviseurs s'arrêtent, mais le
claim SQL du gagnant reste actif jusqu'à sa lease. Le premier GET peut donc
restituer `executing/confirmed` sans reçu. Après expiration, un GET le rend
`remote_uncertain`, claim `lost`, sans replay. Ce transitoire est déjà prévu au
contrat M7 original `750180fa:94–101`. L'assertion de terminalité immédiate est
trop forte ; aucun défaut produit n'est démontré. L'ordonnancement précis des
échecs historiques reste inconnu.

## Delta et correspondance des assertions

Le test historique
`tests.integration.document_workshop.test_update_m7_postgresql.UpdateM7PostgresqlTests.test_two_inflight_conversations_same_version_at_most_one_publication`
conserve son ID. Le nouveau test est
`tests.integration.document_workshop.test_update_m7_postgresql.UpdateM7PostgresqlTests.test_two_inflight_updates_nowait_keep_live_claim_until_expiry_then_uncertain`.
Le helper reste local à cette famille dans
`app/tests/support/document_workshop_m7_concurrency.py` ; la sonde diagnostique
et le serveur DAV commun restent inchangés.

| Assertion historique | Preuve corrigée |
| --- | --- |
| Au plus un HTTP 200/reçu | Nominal ordonné : exactement un gagnant 200/succeeded avec reçu vérifié et téléchargement exact ; perdant 409/conflict sans reçu. Chevauchement : aucun reçu/rendu malgré un effet DAV. |
| Si aucun reçu, refus d'observation 55P03 | Chevauchement : trois rollbacks 55P03 exacts, dans l'ordre observation/action/claim, avant retour HTTP du gagnant ; aucun garde neutralisé. |
| GET immédiatement terminal (ancienne ligne 338) | Nominal : succeeded/conflict. Chevauchement : actif/executing avant expiration, puis lost/remote_uncertain après la frontière autorisée. `executing` n'est jamais ajouté à une liste de terminaux. |
| Zéro claim actif immédiatement (ancienne ligne 340) | Nominal : zéro après publication. Chevauchement : claim identifié vivant/lease future avant et après le premier GET, puis zéro après expiration et réconciliation. |
| Deux PUT/un effet, aucune compensation | Dans les deux scénarios : exactement deux PUT avec If-Match `"v1"`, version distante 2, un fichier/lien, zéro DELETE/MKCOL, aucun appel DAV supplémentaire pendant GET ou replay. |
| Absence de transaction pendant DAV | Vraie observation SQL indépendante alors que les deux PUT sont retenus ; aucune transaction SQL ne couvre cette attente. |
| Répétitions | Deux confirmations et GET répétés ; toutes lignes/colonnes de 14 tables durables identiques, journal compris, aucun nouveau claim et aucun appel DAV. |

La transaction du perdant reste réellement ouverte dans le scénario NOWAIT.
Le nominal attend son retour HTTP complet avant l'observation du gagnant.
Dans le chevauchement, le perdant attend le retour du gagnant avant son commit.
Les barrières sont bornées ; tout timeout échoue avec trace technique. Le
`finally` libère toutes les barrières avant drainage des futures, garde les
patches actifs jusqu'à la fin des requêtes et joint tous les superviseurs.
Les erreurs de nettoyage ne masquent pas l'erreur initiale. Aucune fermeture
forcée d'un claim SQL n'est utilisée pour faire paraître le nettoyage vert.

Les snapshots SQL indépendants sont en lecture seule, cohérents sous
REPEATABLE READ. Les empreintes portent sur **toutes les colonnes**, y compris
lease_until, timestamps, propriétaires, générations et journal complet. Aucun
champ durable n'est omis. `lease_live = lease_until > clock_timestamp()` reste
une projection temporelle séparée, vérifiée aux points utiles. Les empreintes
évitent de recopier canonical/messages synthétiques dans les traces.

## RED, GREEN et contrôles négatifs

Les commandes exactes, IDs, images, versions, exits, durées et empreintes de
logs sont dans le relevé JSON ; les événements corrélés sont conservés dans
[la trace JSONL](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.jsonl).
Les programmes de preuve autonomes, dont les mutants uniquement en mémoire,
sont conservés dans `proof_programs` du relevé pour reproduction.

| Exécution distincte | Résultat | Exit | Durée murale |
| --- | --- | --- | --- |
| `before-controlled-nominal` | contrôle nominal vert | 0 | 4.811 s |
| `before-controlled-overlap-red` | ancienne assertion rouge attendue sur executing | 1 | 4.558 s |
| `targeted-final` | 2/2 | 0 | 6.059 s |
| `positive-nominal-final` | nominal + reçu vérifié | 0 | 3.707 s |
| `positive-overlap-final` | NOWAIT/expiration, zéro reçu | 0 | 3.721 s |
| `negative-convergence-final` | mutant de convergence rejeté au bon invariant | 0 | 3.632 s |
| `negative-cleanup-final` | erreur injectée propagée, nettoyage vérifié | 0 | 3.160 s |
| `negative-cleanup-supervisor-final` | erreur primaire conservée malgré erreur de nettoyage | 0 | 3.107 s |
| `m7-neighbors-final` | 35/35 | 0 | 36.889 s |
| `neighbors70-final` | 70/70, séparés | 0 | 0.623 s |
| `exports-readers26-final` | 26/26, séparés | 0 | 0.612 s |

Baseline : **1 690/1 690**, zéro skip, intervalle de comparaison 556.094 s.
Après : **1 690 IDs historiques + 1 nouveau = 1 691/1 691**, zéro skip,
intervalle 556.482 s. 70 + 26 voisins séparés avant et après.
Ces intervalles couvrent les sélections parallèles autorisées et ne somment pas
leurs durées. Ciblés/probes/négatifs/voisins ne sont jamais ajoutés aux totaux.

| Frontière frontend | Avant | Après | Exit avant/après | Durées avant/après |
| --- | --- | --- | --- | --- |
| M6 HTTP natif | 5/5 | 5/5 | 0/0 | 27.607/26.916 s |
| M7 HTTP natif | 13/13 | 13/13 | 0/0 | 266.246/264.576 s |
| M6 transport simulé | 10/10 | 10/10 | 0/0 | 11.975/11.887 s |


Le rouge causal réutilise la vraie sonde puis applique l'ancienne assertion au
premier GET : `executing` ne fait pas partie des trois états terminaux attendus.
Le contrôle nominal passe avec les mêmes méthodes réelles. Le négatif de
convergence supprime **seulement l'UPDATE terminal de reconcile en mémoire** :
le vrai claim expire en SQL, mais Flask restitue encore executing. L'assertion
remote_uncertain/interrupted échoue exactement à cette frontière ; le processus
de preuve attend cet échec et vérifie séparément le claim réel `lost`.
Aucun mutant ni code produit modifié n'est livré.

L'échec injecté du harnais survient après les deux PUT retenus et après la vraie
preuve d'absence de transaction. Le `finally` draine deux futures, joint deux
superviseurs réels, ferme les connexions ; une nouvelle connexion réacquiert
les verrous des conversations/répertoire, sans transaction idle restante.
Aucun thread créé par la preuve ne survit, serveur DAV compris. Le second
négatif observe temporairement `_stop.is_set()` faux pour le premier superviseur,
sans changer l'événement réel ou le thread. Les deux joins et le contrôle de
connexion sont exécutés ; l'erreur de nettoyage est tracée sans masquer
`injected_harness_failure_after_two_puts`.

Les incidents auxiliaires restent dans `incidents` et `records` : collecteur
sélectionnant Docker `-v` au lieu d'unittest (exit 1), collecte de version lxml
absente (exit 1), tags d'images supposés absents (exit 1 puis 125). Les commandes
ont été adaptées aux runners réellement utilisés, sans installation ni pull.
Ces incidents n'effacent pas leurs premières exécutions et ne constituent pas
des régressions fonctionnelles. Les verts intermédiaires avant renforcement
par la relecture restent séparés des preuves finales.

## Comparaison et provenances

La baseline Python et l'inventaire sont capturés avant édition. Les parcours
frontend natifs M7 et les 70 + 26 voisins ont terminé pendant la rédaction du
helper/docs : leurs entrées frontend/produit/voisins sont strictement identiques
à la base. Les bases HTTP sont distinctes de celle des probes. La comparaison
finale conserve les 1 690 IDs historiques et ajoute un seul nouvel ID ; les
sélections SQL réinitialisant le schéma ne se chevauchent jamais. Les groupes
ciblés, négatifs, voisins et répétitions ne sont pas additionnés aux totaux.
Les noms TAP sont comparés dans l'ordre file/name/index ; seule l'échappement
historique `\#` est normalisé, sans fusion d'identités.

Provenances historiques préservées : contre-audit indépendant du 7 octobre sur
`1732a126`, **1 674/1 677**, SQL 28/29 deux fois et M7 natifs 11/13 ; celui du
9 octobre sur `c1654c25`, **1 689/1 690**, SQL 28/29, 96 voisins verts et cinq
tests client M7 verts séparément après arrêt du groupe SQL. Les verts Celebrimbor AUD-02 et le
34/34 diagnostique sont des exécutions distinctes. Les observations UI M7
phone light/dark sidebar et M4 historique 21/22 puis 22/22 restent séparées,
causes initiales non établies ; un vert courant ne les résout pas.

Preuve **transmise par Tof**, non exécutée par ce correctif : contre-audit Codex
du diagnostic, sélection 34/34 et deux scénarios livrés verts. Variante en mémoire
avec expiration naturelle : succès en 92,681 s, environ 89,054 s d'attente
résiduelle, échéance inchangée, GET convergent et zéro replay. Premier essai
auxiliaire : 92,902 s, échec **après le GET conforme** sur la comparaison autour
du replay ; différence non capturée, cause inconnue. Le second essai ajoutait
une capture d'erreur sans changer les assertions. La précaution lease_live du
présent correctif n'établit pas la cause de ce premier échec.

## Auto-audit, relecture et limites

Auto-audit : deux PUT réellement concurrents, transactions/autorité/supervision
réelles, terminalité conditionnée à la lease, reçu seulement après publication
vérifiée, aucune réparation de succès non journalisé, aucune mutation/reprise
sur répétition, comparaison durable complète et nettoyage sur échec.
La seconde lecture indépendante a fait renforcer l'absence de reçu perdant,
les refus de repair/DAV/claim pendant GET et le parcours complet du nettoyage.
Avis final favorable de la seconde lecture indépendante : aucun finding
vivant restant dans ce delta. Inventaires, totaux, intervalles, hashes, liens et
statuts recalculés/vérifiés ; 73 relevés comparés aux logs avant nettoyage,
81 relevés finaux contre-lus dans l’artefact durable. Aucune réexécution SQL ou
Docker indépendante par ce relecteur. La livraison reste à contre-auditer par
Codex après Git.

Runners existants, env vidé, checkout/rootfs en lecture seule, réseau extérieur
coupé, données synthétiques, ressources SQL possédées. Aucun changement produit,
configuration, migration opérateur, UI, service partagé, installation, runtime,
rebuild/restart, déploiement ou appel OpenRouter/Nextcloud/Writer live.
Aucune preuve Writer/AF_UNIX renderer/live déduite des sockets PostgreSQL.
Nettoyage vérifié : six conteneurs possédés supprimés et absents ; racine
temporaire `/tmp/fridadev-m7-conc-fix-20261009` et sockets absents. Le premier
rmtree hôte a échoué (exit 1) sur les sockets dans les répertoires sticky détenus
par les UID PostgreSQL. Sa durée de script n’a pas été persistée avant l’erreur ;
la durée du tool et l’exception sont conservées. Un conteneur jetable existant,
root, réseau coupé/rootfs en lecture seule, montait seulement cette racine en
écriture pour en supprimer les derniers fichiers possédés (exit 0). Les preuves
durables sont conservées ; aucun cache partagé supprimé. Commandes et contrôle
de disparition figurent dans `cleanup` du relevé.

Ce lot ferme le défaut d'attente immédiate et de reproductibilité des preuves
M7 dans sa portée ; la livraison reste à contre-auditer par Codex. Il ne prétend
identifier rétrospectivement chaque rouge ni diagnostiquer un bug produit.
AUD-01/AUD-02 restent fermés ; clôture globale M8-C, UI M7/M4 et runtime restent
séparés. Aucun démarrage M8-S/M8-A ou lot suivant.
