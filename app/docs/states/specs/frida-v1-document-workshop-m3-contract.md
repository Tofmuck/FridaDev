# Atelier documentaire Frida V1 — contrat M3

## Évolution M4 — 6 octobre 2026

La préparation M4 réutilise les claims communs et le snapshot transactionnel M3. Sauvegarde utilisateur/action initiale, puis réponse courte/révision/pending/supersession/clôture finale sont atomiques. Le pending libère le claim et n’expire pas. Le correctif golden M3 distinct est `9f10531ae9c799f4afc769c97ea2d48659f1c3d3`, poussé et vérifié avant la branche M4.
Voir le [contrat M4](frida-v1-document-workshop-m4-contract.md) pour les preuves
hermétiques et les limites ; migrations opérateur, runtime, modèle/DAV live et M5 restent ouverts.


Date : 2026-10-06. Base : M2 `6e8c61f5059350d8d15ded4b41b68f2e0d9acac3`.
Autorité : [roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md),
§§3.4, 3.6, 3.7, 4 et M3. M4 reste non commencé.
Code et migrations livrés sur `FridaV1-Document-Workshop-M3` ; application
opérateur et rebuild requis restent ouverts. Git ne constitue pas une livraison runtime.

## Plan retenu et périmètre

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de bord ? »
Le snapshot atomique existant est conservé. Seule sa primitive acceptant une
connexion fournie est extraite ; son appelant historique conserve ses contrats.
Une table de claims commune et des enveloppes propres à la requête protègent le
chat existant. Aucun second store de messages, transcript reconstruit en parallèle,
framework de tâches, route, action/révision/reçu M4 ou workflow documentaire ajouté.

Les écritures pré-finales de résumé et d'état herméneutique utilisaient aussi des
connexions indépendantes. Elles acceptent le même jeton et le vérifient sur leur
connexion d'écriture, après tout travail réseau/embedding. Leurs contenus et les
facultés constitutives, dont Stimmung, restent inchangés. Les dérivations globales
Memory/Identity postérieures au snapshot canonique conservent leur chemin existant ;
elles ne deviennent pas une transaction globale ni un mécanisme de retry M3.

## Identité et acquisition

L'unique soumission canonique navigateur crée un UUID `client_turn_id`, après les
gardes, et le transmet pour clavier, dictée et Dialogue. Un tour accepté reçoit
une identité nouvelle, même pour un texte identique. Le serveur valide l'UUID.
Le texte et `seq` ne sont jamais l'identité. Le fingerprint canonique SHA-256 de
la demande sert seulement à refuser un identifiant réutilisé avec des entrées
incompatibles ; le choix JSON/stream est exclu de cette compatibilité.

Les appels existants sans `client_turn_id` reçoivent un UUID serveur par requête.
Ils acquièrent exactement la même exclusion SQL. Aucune déduplication entre des
requêtes sans identité commune n'est promise.

Le service refuse toujours un champ `document_context_id`, même vide, sans
fallback normal. Préparation documentaire publique indisponible. Pour le chat,
la session résout l'existence de la conversation, puis acquiert le claim et relit
le snapshot sous exclusion. Une nouvelle conversation initialise son catalogue
avant l'acquisition ; aucun message utilisateur/provider n'est démarré sans claim.
La sauvegarde utilisateur initiale protégée précède résumé et providers.

`conversation_turn_claims` porte identité de tour/confirmation interne, conversation,
propriétaire UUID, génération, kind (`chat`, `preparation`, `confirmation`), fingerprint,
contexte éventuel, précondition ETag éventuelle, lease, état et résultat canonique.
PostgreSQL impose la clé primaire globale du tour, l'unicité conversation/génération
et un index unique partiel sur la conversation en état `active`.
L'incrément de génération et l'INSERT du propriétaire appartiennent à une transaction.
Deux processus indépendants utilisent cette même autorité ; aucun mutex global.

Une répétition relit l'état durable et retourne un conflit `409` avec la seule
projection technique `turn_id`, `conversation_id`, `state`, `outcome`. Elle ne
relance pas le modèle, ne réinsère pas l'utilisateur et ne reprend pas une tentative
interrompue. Une demande incompatible est refusée ; un autre tour actif dans la
conversation reçoit un conflit. Deux conversations peuvent atteindre leurs
providers simultanément.

## Transactions et fencing

`check_in_transaction` lie le jeton à la conversation et au contexte de sa ligne,
à son propriétaire, sa génération, la génération courante et au lease SQL vivant.
Il verrouille l'autorité et le scope jusqu'à l'écriture. Snapshot, contrôle et
`outcome` participent à la même transaction courte. La primitive de snapshot ne
commit jamais ; le caller historique continue à posséder son commit.
La sauvegarde réservée préserve le répertoire courant et les tombstones ; un chat
normal en cours peut survivre à un déplacement sans remettre l'ancien répertoire.
Une suppression de conversation invalide aussi le claim normal.

Ordre des claims : conversation, ressources documentaires éventuelles, contexte,
claim. Les verrous downstream sont `NOWAIT`, y compris le pré-verrouillage avant
expiration SQL des claims actifs : une mutation existante qui possède déjà une
ressource/contexte/claim puis demande la conversation reçoit la priorité ; le
claim concurrent rollback et retourne un conflit, sans attente cyclique.
Les opérations SQL ont un `statement_timeout` local de 5 secondes après connexion.
La création M1 refuse également une ressource verrouillée. L'adoption M2 conserve
ses mêmes verrous de fichiers/liens, placés avant conversation puis contexte ;
aucun accroissement de portée. Les suppressions réelles de répertoire/fichier sont
exercées par rendez-vous SQL, pas seulement par UPDATE de fixture.

Toutes les sauvegardes du tour utilisent l'enveloppe réservée : utilisateur initial,
résumé intermédiaire, final locks, succès JSON/flux, erreur et secours. La perte
ou panne du store ne crée aucune branche de sauvegarde permissive. Les écritures
pré-finales Memory concernées vérifient aussi sur leur connexion fournie.
Un ancien jeton ne peut renouveler, écrire, clôturer ou annuler son successeur.
Un jeton transplanté vers une autre conversation de même génération est refusé.

`outcome` est enregistré atomiquement avec le snapshot final (`succeeded` ou
`interrupted`). L'état reste `active` jusqu'à la fin réelle du traitement ; la
clôture utilise ce résultat durable. Un échec de clôture peut donc laisser un
snapshot final valide avec `state=active,outcome=succeeded` ; cette incertitude
est relisible, ne devient pas un succès HTTP et finit par perdre son lease.
Un succès JSON et un `done` de flux exigent atomiquement `outcome=succeeded`, même si un delta du
provider ressemble au marqueur de contrôle. Un flux vide légitimement terminé
sauvegarde seulement l'utilisateur avec phase `empty_final` et résultat réussi.
Aucun assistant technique n'est inventé.

## Lease, flux et états

Lease fixe **90 secondes**, renouvellement **15 secondes**, horloge autoritative
`clock_timestamp()` PostgreSQL. Le superviseur appartient à la requête/session,
pas au générateur retourné. Le défaut source du timeout principal OpenRouter est
900 secondes : un traitement vivant peut dépasser plusieurs leases, sans deadline
totale nouvelle ni changement de budget/modèle/timeout fournisseur.

Aucune transaction reste ouverte pendant provider, embedding ou consommation
réseau. Pendant un `next()` effectif, le superviseur renouvelle. Entre deux chunks,
ou avant toute consommation, il cesse de renouveler ; reprise exige un renouvellement
SQL encore valide. Un abandon sans `close()` finit donc par perdre l'exclusion.
`close()` et `Response.call_on_close` ferment aussi un flux jamais consommé. Un
terminal n'est rendu qu'après clôture SQL ; perte/échec rend le terminal d'erreur
existant `conversation_persist_failed`, sans annoncer une finalisation refusée.
La fermeture anticipée ne canonise pas un fragment assistant.

| État durable | Cause |
| --- | --- |
| `active` | Propriétaire vivant, traitement non clôturé ; résultat éventuellement déjà enregistré. |
| `succeeded` | Snapshot réussi puis clôture durable validée. |
| `interrupted` | Sortie/erreur/fermeture sans résultat final réussi. |
| `lost` | Lease SQL expiré, observé à la relecture/acquisition ; aucun replay automatique. |
| `cancelled` | Annulation explicite documentaire, contexte fermé aussi. |
| `invalidated` | Scope pertinent modifié ou conversation supprimée. |
| `failed` + `document_inactivity` | Préparation interne fermée après 120 secondes sans progrès M0. |

Le lease n'est ni progrès, ni limite de durée totale, ni expiration documentaire.
M0 reste l'autorité du compteur local de préparation : avancées utiles à 119,
238 et 357 secondes ; à 476 le traitement reste valide, à 477 il atteint exactement
120 secondes sans progrès et échoue. Renouvellements, keepalives et polling ne
réarment pas ce compteur. Le chat normal refuse le motif `document_inactivity`.
Aucun préparateur public n'est activé par cette preuve interne.

## Scope documentaire et confirmation interne

Le contexte est immuable ; ses états deviennent `editing`, `cancelled`, `invalidated`.
Des triggers partagent la transaction des mutations existantes : déplacement ou
suppression de conversation, renommage/suppression du répertoire, changement pertinent du
lien Nextcloud du répertoire, cible/éligibilité/contenu du fichier, identité/chemin/
ETag/fraîcheur de son lien, ouverture d'un autre scope de contexte. Une fermeture
n'est pas réversible, même après A→B→A. Les mises à jour purement diagnostiques
ou la rotation du cache local à octets/ETag identiques ne ferment pas l'autorité.

La confirmation interne revérifie scope et ETag fourni dans sa transaction de
réservation. Un contexte/proposition synthétique créé en 2000 reste admissible
si ses préconditions sont valides. Aucun TTL n'est ajouté. Ce test ne livre
ni carte pending M4, ni exécution M5, ni une table de propositions anticipée.

## Migration, preuves et limites

Migration versionnée : `app/core/sql/conversation_turn_claims.sql`, rejouée sur
PostgreSQL isolé avec relecture indépendante et conservation des claims/générations.
`init_db()` n'est appelé ni par import ni par bootstrap serveur. Aucun SQL n'a été
appliqué sur la base opérateur. Le nouveau chat échoue fermé si le schéma manque :
la livraison runtime exige une migration opérateur coordonnée avant son rebuild.

Les commandes, sélecteurs, résultats, durées, défauts de harnais et contre-audit
sont consignés dans [M3 de la roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md#m3--réservation-durable-et-concurrence).
Le P3 préexistant de l'inventaire golden des routes est corrigé séparément le
2026-10-06, tests/docs-only : cinq entrées explicites, classification de test des
contextes, cardinalité 128 et sensibilités strictes. Rouge ciblé conservé ; vert
2/2 puis module et voisins 59/59, sans skip. Les découvertes historiques M3 ne
sont pas réécrites en succès global. Aucun code runtime modifié par ce correctif.
Providers synthétiques comptés, PostgreSQL réel avec connexions/processus distincts,
pgvector réel pour le résumé, runners réseau fermé et checkout en lecture seule.
Aucun modèle/DAV live, base opérateur, rebuild/restart, health runtime, renderer,
canari ou démarrage M4. Les preuves navigateur ne remplacent pas une recette
matérielle iPhone ; les callbacks et tests voix/Dialogue existants sont conservés.
