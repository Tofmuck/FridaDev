# Atelier documentaire Frida V1 — contrat M5

## Évolution M8-C — 7 octobre 2026

La frontière synthétique historique `BinaryRenderEvidence` / `_validated_binary`
est retirée au profit du [contrat Writer v1 fermé](frida-v1-document-workshop-m8c-contract.md),
de `validate_result` et de la session injectable. L’ID M5 et ses onze sous-cas
sont conservés avec paire/manifeste et libération séparée ; leur nouveau run
est consigné dans le relevé M8-C. Aucun chemin permissif parallèle. Ce constat
ne requalifie pas la frontière M5 en bug historique. Markdown direct et gardes
M3/M5 restent inchangés ; DOCX/PDF publics restent indisponibles, Writer et
transport Unix non livrés. Les sections M5 ci-dessous sont des preuves datées,
pas le protocole Writer courant. M8-S/M8-A/M9/M10 restent non commencés.

## Évolution M7 — 7 octobre 2026

Create/copy conservent leur création If-None-Match et leur compensation conditionnelle. Update conserve fichier/lien, écrit avec If-Match préparé et interdit toute compensation DELETE/restauration. La migration M7 explicite étend les contraintes sans désactiver les triggers. Voir le [contrat M7](frida-v1-document-workshop-m7-contract.md) et son relevé daté. Code et preuves isolées ; migration opérateur, rebuild, préconditions Nextcloud et Versions réels restent ouverts sous GO distinct. M8-C est désormais fermé en contrat/simulation (voir évolution ci-dessus) ; M8-S/M8-A et formats binaires restent non commencés. Les sections précédentes ci-dessous gardent leur périmètre et leurs résultats historiques datés.

## Raccord M6 — 7 octobre 2026

Le périmètre historique M5 ci-dessous reste la confirmation/exécution injectée.
M6 fournit désormais au serveur une factory réelle paresseuse, les consommateurs
du reçu/lien/inventaire et la lane de continuité, sans modifier l'autorité ni les
compensations M5. Voir le [contrat M6](frida-v1-document-workshop-m6-contract.md).
Cette évolution est prouvée en isolation ; aucune migration opérateur, livraison
runtime ou mutation Nextcloud opérateur n'est attestée.

Date : 2026-10-06. Statut : code et preuves hermétiques fermés ;
aucune livraison runtime. Autorité :
[roadmap active](../../todo-todo/product/frida-v1-document-workshop-todo.md#m5--confirmation-et-exécution-hermétiquement-protégées)
et mandat explicite M5 du 6 octobre 2026. Base exacte :
`cc72aa963366660a6a135b66d206e39671556e8b`, parent
`674150d913e3402819a1c307876427d59d6791e4`, vérifiés avant création de
`FridaV1-Document-Workshop-M5`, sans merge ni rebase. Les résultats historiques
M0–M4, dont P2-M4-01/02 et l'erratum P3-M4-03, sont conservés.

## Plan et propriétaires

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » Le plan retenu réutilise les chemins et le Markdown figés M0, les
lectures fraîches et l'inventaire commun M2, les réservations et le fencing M3,
et l'action/révision M4. La confirmation est une transaction courte distincte
de la préparation. Les seuls composants ajoutés portent l'autorité SQL,
l'exécution bornée et les requêtes conditionnelles nécessaires à M5.

| Responsabilité | Propriétaire |
| --- | --- |
| Canonical, sérialisation et chemin exact | M0 : `document_canonical`, `document_markdown`, `workspace_document_paths` |
| Sources, identité/version, inventaire unique | M2 : services de contenu/adoption, stores fichier/lien |
| Exclusion chat/préparation/confirmation, lease et génération | M3 : `conversation_turn_claims`, superviseur `ChatReservation` |
| Consommation durable, journal, publication SQL | `document_workshop_execution_store` |
| Séquence hors transaction, validation et arrêt | `document_workshop_executor` |
| Requêtes DAV, preuve de création et compensation | `workspace_document_nextcloud_mutation_client` |
| Autorité HTTP et projection fermée | `document_workshop_execution_service`, registrar documentaire |
| Clic et toutes les représentations de l'action | Contrôleur commun `chat_document_workshop.js` |

L'upload historique conserve son client, son sanitizer et ses transactions.
Son DELETE non conditionnel n'est jamais utilisé par M5. Il n'existe ni second
inventaire, ni framework de jobs/retry, ni client mutateur raccordé par défaut.

## Confirmation et autorité durable

`POST /api/document-workshop/actions/{id}/confirm` est l'unique entrée de
confirmation. Son objet JSON fermé contient cinq UUID : `context_id`,
`conversation_id`, `workspace_folder_id`, `revision_id`, `request_id`.
Le navigateur ne transmet ni contenu, ni chemin, ni ETag faisant autorité.
Aucune phrase, lecture GET ou marqueur navigateur ne constitue une confirmation.
Cette entrée ne soumet rien à `/api/chat` et n'ajoute aucun transcript.

Le registrar reçoit un fournisseur d'exécuteur optionnel explicitement injecté
par les tests. Le wiring serveur existant ne lui en fournit aucun : la capacité
publique de confirmation reste fausse et le POST construit hors UI reçoit
`503 document_execution_unavailable` avant accès mutateur. Pas de réglage
Admin, de faux succès runtime ou de mode de démonstration. Markdown create/copy
sont les seules opérations confirmables dans le harnais ; update et DOCX/PDF
restent indisponibles au produit.

Le store relit action, contexte, conversation, répertoire, liens, sources et
révision. Il vérifie les identités du corps, l'opération, le chemin M0, les
empreintes du canonical/Markdown et les collisions de l'inventaire. Sous le
verrou de conversation, il crée le claim M3 `confirmation`, lie son identité
à l'action et passe `pending` à `executing` dans la même transaction.
L'action et son claim de préparation réussi restent historiques, inchangés.

Une action consommée ne crée plus de claim, même avec un autre `request_id`.
Une réutilisation incompatible d'identité est refusée. Une répétition
compatible relit l'état : ni modèle, ni renderer, ni PUT supplémentaire. Aucun
TTL du pending : l'ancienneté seule ne l'invalide pas. Les sources mobilisées
sont relues intégralement via la frontière M2 avant toute mutation ; changement
de scope, identité, ETag ou empreinte refuse l'exécution sans nouvelle
préparation automatique.

Les transactions verrouillent conversation, ressources, contexte/claim, puis
action ; les verrous aval sont `NOWAIT`. Propriétaire, génération, lease et
scope sont vérifiés dans les transactions d'écriture et avant chaque effet.
La supervision M3 reste active. Aucun verrou ou transaction SQL ne traverse
un appel DAV ou renderer. Une annulation d'action est ciblée : agir sur A ne
ferme pas le claim de préparation de B. Un détenteur perdu ne publie pas un
résultat tardif, ne journalise pas une observation et ne compense pas.

## Cible et transport

Le chemin affiché, confirmé et envoyé est le même snapshot M0 : sous-arbre
`Documents` du répertoire sélectionné, huit niveaux maximum, 180 points de
code et 255 octets UTF-8 par segment, 1 024 octets UTF-8 pour le chemin complet.
La validation refuse traversées, séparateurs déguisés et encodages ambigus.
Aucun raccourcissement, renommage ou normalisation destructive au clic.

Les ancêtres possibles sous `Documents` sont dérivés du chemin figé et
présentés avec la proposition. La préparation M4 ne conservait pas de listing
DAV des collections manquantes : cette projection ne prétend pas qu'ils sont
absents. L'exécution vérifie chaque segment existant et ne peut créer que les
ancêtres de cette liste. La racine `Documents` doit déjà être une collection
distante identifiée ; M5 ne la crée pas. Une erreur de lecture n'est pas une
absence. Les collisions locales/distantes utilisent les clés M0 ; la cible
apparue après prélecture reste protégée par la précondition HTTP.

Le client injecté envoie les octets figés à la cible encodée exacte, avec
`If-None-Match: *`. Il n'effectue aucun retry, fallback PUT ou redirection.
Un succès de création exige une réponse 201, un ETag fort unique et une
relecture conditionnelle vérifiant identité, taille, version et octets.
Une coupure après réception du PUT, un ETag absent/faible ou une relecture
incompatible constitue un résultat inconnu, jamais une absence certaine.
Une redirection 3xx après PUT ou MKCOL est également inconnue : refuser de la
suivre empêche une seconde requête, sans prouver l'absence d'effet de la
première. Le statut reçu est conservé, sans retry ni compensation supposée.

## Journal, pannes et publication

Un journal d'intention durable précède le premier MKCOL/PUT. Chaque requête
mutatrice doit ensuite obtenir une autorisation explicite qui vérifie le
claim/scope et commite son intention exacte. Échec du journal ou du contrôle :
zéro requête mutatrice à cette frontière. Il reste une fenêtre entre le commit
SQL et l'effet distant : ce contrat ne suppose aucune atomicité distribuée ni
« exactly once ». La confirmation unique locale et le PUT conditionnel
empêchent le replay applicatif ; les effets inconnus restent inconnus.

| Étape | Préconditions | Effet possible | Panne | État durable / reprise |
| --- | --- | --- | --- | --- |
| Confirmation | Pending, identités/scope/révision valides, exclusion M3 | Claim lié et `executing` | Rollback SQL | Pending non consommé ; seule une nouvelle action humaine peut confirmer |
| Fraîcheur/rendu | Claim vivant, sources identiques, résultat complet | Lecture ou rendu synthétique seulement | Refus/panne avant journal | `failed`/`invalidated`, aucune mutation ; aucun retour à pending |
| Intention | Claim vivant, cible exacte, collision absente | Journal commité | Journal refusé | Aucun MKCOL/PUT ; exécution fermée ou détenteur perdu |
| MKCOL | Ancêtre confirmé, parent existant, intention propre | Collection de cette action | Réponse perdue/arrêt | Incertitude conservatrice ; aucune suppression de collection ni retry |
| PUT | Cible exacte, octets figés, intention propre | Objet nouveau sous précondition | 412/rejet/coupure | Conflit/refus ou `remote_uncertain` ; aucune seconde écriture |
| Validation distante | 201 + identité/version forte + readback | Création prouvée | Version/ETag/readback douteux | `remote_uncertain`, pas de publication ni DELETE aveugle |
| Publication | Création prouvée et détenteur vivant | Bundle SQL atomique | Rollback/commit incertain | Pas de succès partiel ; compensation seulement si rollback certain et propriété prouvée |
| Compensation | Même création, cible, ETag fort d'origine, claim vivant | DELETE `If-Match` exact | 412/ETag changé/réponse perdue | Objet préservé ou résultat inconnu ; aucun DELETE non conditionnel |
| Annulation/lease perdu | Autorité fermée | Plus aucun effet autorisé | Réponse tardive | Sans intention : échec/annulation ; avec intention : incertitude, lecture seulement |

La publication transactionnelle minimale écrit fichier, lien Nextcloud,
rendu de révision, association de l'artifact, reçu structuré, succès de
l'action et clôture du claim sur une seule connexion. Le cache local est
préparé hors transaction ; il ne constitue pas un inventaire publié. Un
rollback réel de chaque écriture annule tout le bundle SQL. Un commit à réponse
perdue exige une nouvelle connexion et la preuve de tout le bundle, identité
et version distantes, cache et octets inclus, avant reconnaissance du succès.

La compensation n'accepte que la preuve de création détenue par la même
instance du client pour la cible exacte et l'ETag fort obtenu lors de cette
création. Une lecture ultérieure vérifie encore cet ETag ; elle ne remplace
jamais l'ETag d'origine par celui d'une modification concurrente. Propriété
inconnue, ETag faible/absent/changé ou DELETE incertain : aucun effacement
aveugle. Les collections préexistantes ou créées ne sont jamais supprimées ;
le nombre de créations observées est projeté et une panne peut laisser des collections vides
ou un objet distant. Un crash entre effet et observation conserve l'intention,
sans inventer un nombre exact ni une absence.

Les nombres projetés comptent les créations de collection observées, pas un
inventaire actuel. Zéro création observée ne prouve pas l'absence d'une
collection après une réponse MKCOL perdue. L'UI avertit aussi dans ce cas et
quand le nombre est inconnu ; elle ne fabrique aucun total.

Une relecture GET et une répétition de confirmation vérifient à leur tour le
bundle historique, le reçu/rendu/journal immuables, l'observation de succès
distante d'origine, le propriétaire/génération et les octets du cache. Si cette
preuve est indisponible, la projection est `remote_uncertain` avec
`document_publication_unknown`, même si le commit SQL historique est
`succeeded`. Ce fait durable n'est ni rouvert ni réécrit par un détenteur clos.
Retrouver la preuve complète permet de projeter le succès historique, sans PUT
et sans prétendre effectuer une nouvelle lecture de fraîcheur DAV.

Le journal ne contient ni texte documentaire, ni nom privé, ni chemin brut,
ni exception de transport brute : identités, empreintes, états, codes, statut
HTTP et ETag validé seulement. Aucune nouvelle famille de logs n'est ajoutée.
Les projections produit autorisées gardent le nom/chemin de la proposition ;
les contrats privés historiques ne changent pas.

## Contrôleur commun et frontière binaire

Le clic retire synchroniquement la confirmation de toutes les cartes de cette
action, avant le premier `await`. Le marqueur local contient seulement les
identités et `attempted/unknown/observed` ; il ne confère aucun droit serveur.
Une erreur de stockage empêche l'envoi. Bouton détaché, double clic, clavier,
ancienne réponse et re-render ne réarment pas la confirmation. Refresh et
perte réseau font uniquement des GET, jamais un POST automatique. Si le clic
n'a pas atteint le serveur, l'action reste pending côté serveur et l'UI expose
une confirmation non établie : elle n'invente pas une exécution globale.
Les générations isolent conversation/répertoire et réponses tardives ; une
carte historique A ne neutralise pas le polling de préparation de B.

La frontière binaire est interne : un fake renderer est appelé seulement
après confirmation/claim, avec vérification du claim avant/après. Son résultat
doit être complet, correctement lié à la révision/canonical, avec octets et
empreinte concordants, cleanup confirmé et pagination observée de 1 à 20.
Panne, pages absentes/incohérentes, 21e page ou cleanup douteux : aucun
MKCOL/PUT. Les pages du canonical et les metadata DOCX ne font pas preuve.
Ce mécanisme ne livre ni Writer/UNO, ni client live, ni protocole M8-C.

## Migration explicite

`app/core/sql/document_workshop_execution_m5.sql` étend les états/actions,
ajoute le lien de confirmation, les associations et les tables de rendu,
reçu et journal. Il étend les invalidations M4 aux exécutions et conserve
l'immuabilité des identités/révisions et la fermeture des états consommés.
Son application est explicite, testée sur PostgreSQL isolé depuis M4 avec
actions existantes et en réapplication. Aucun import, démarrage ou requête
n'applique ce schéma. Il est livré mais non appliqué à la base opérateur.

## Preuves et contre-audit

Le [relevé daté M5](../baselines/document-workshop/frida-v1-document-workshop-m5-20261006.json)
conserve les sélections et fichiers développés, IDs chargeables, commandes,
sorties de résultats, empreintes des logs complets, durées, codes, skips,
images et versions réellement consommées. Avant toute édition, la sélection
`final.selections` corrigée P2-M4-02, qualifiée par P3-M4-03, a été rejouée :
1 447/1 447 réussis, zéro skip. P3 n'a changé aucun test ni code.

| Groupe | Baseline avant patch | Comparaison finale V2 | Durée finale du runner |
| --- | ---: | ---: | ---: |
| Python historique | 741 | 741 | 233,690 s |
| PostgreSQL historique | 151 | 151 | 106,097 s |
| pgvector historique | 2 | 2 | 1,718 s |
| Node historique | 424 | 424 | 4,338 s |
| Chromium historique | 107 | 107 | 99,591 s |
| Chromium M4 | 22 | 22 | 19,007 s |
| Python M5 : routes / DAV loopback | — | 3 / 28 | 1,219 s |
| PostgreSQL M5 | — | 28 | 30,173 s |
| Chromium M5 | — | 17 | 14,234 s |

La version finale exécutée comprend **1 447 historiques + 76 nouveaux =
1 523/1 523**, neuf groupes à exit 0 et zéro skip. Les mêmes IDs historiques
sont préservés ; les comptes et IDs nouveaux concordent avec la collecte.
Les 128 empreintes collectées, dont le delta code/tests M5 et la migration,
restent stables pendant le rejeu. Les 953 IDs Python distincts chargent chacun
un seul cas ; les 570 registrations frontend sont identifiées par fichier,
rang et nom, puis comparées au TAP exécuté. Le titre seul n'est pas unique
pour onze titres historiques Node. La collecte n'exécute pas les callbacks.
La première comparaison à 1 523 verts précède la correction des 3xx : elle
reste une preuve intermédiaire conservée, pas la preuve de la version finale.

Les voisins DAV/compensation/upload/dossiers comptent 74 cas, tous déjà dans
la baseline. Les voisins Exports/Images/Notes ajoutent 70 cas distincts hors
comparaison, tous verts : leurs 144 exécutions ne gonflent ni la baseline ni
les 76 nouveautés. Le rejeu ciblé final des 3xx et des 74 voisins est vert
à 102/102. Les ciblés et probes restent séparés des totaux uniques.

Les rouges causaux et contrôles nominaux traversent les vrais services/stores :
deux processus et connexions indépendants pour la confirmation unique ;
exclusion chat/préparation, lease/génération, annulation A/B et résultat tardif ;
rollback SQL du journal et de chacune des sept écritures de publication ;
route Flask et HTTP DAV loopback pour les headers, octets, cible, conflits,
réponse PUT perdue, ETag et DELETE conditionnel ; contrôleur monté pour le
retrait immédiat, refresh sans POST, navigation et réponse tardive ; fake
renderer refusé avant toute mutation. Le pending daté ancien reste admissible
avec ses préconditions intactes.

Auto-audit et contre-lecture indépendante du delta ont corrigé : fencing des
observations tardives (`M5-A1`), preuve complète identité/cache/claim (`M5-A2`),
polling de B lors de la confirmation de A (`M5-A3`), GET tardif après annulation
(`P2-M5-UI-01`), vérification du bundle sur GET/reconfirmation (`M5-R2`),
refus d'un résultat binaire même valide à la frontière Markdown (`M5-R3`),
signalement des collections observées ou possibles (`M5-A4`) et classification
des réponses 3xx PUT/MKCOL comme inconnues (`P2-M5-DAV-01`). Chaque finding
code introduit possède son rouge, son correctif et son rejeu final dans le relevé.
Le contrôle indépendant final des preuves et documents est inscrit dans son
champ `review`. Aucun finding code vivant ni anomalie étrangère confirmée.

Les adaptations sont explicites : import de fixture SQL sans redécouvrir
24 cas M2, IDs Python sans suffixe dupliqué, fixture UI utilisant un vrai refresh
pour relire les cartes, et sélecteurs réellement existants. Une commande Node
avec deux fichiers absents avait exécuté seulement 13 cas M5 ; elle est
conservée avec ce périmètre, puis remplacée par les voisins vérifiés.
Une commande Python avec trois modules absents a échoué malgré ses 28 cas M5
verts ; un driver détaché n'a enregistré aucun résultat. Aucun de ces essais
n'est présenté comme une preuve verte ; les exécutions attendues les remplacent.
Les assertions historiques M0–M4 ne sont pas affaiblies ; seul le golden exact
des routes passe de 130 à 131 pour la confirmation autorisée.

Les preuves distinguent mocks de services, HTTP loopback réellement consommé,
PostgreSQL réel et navigateur monté avec fetch synthétique. Les tests séparés
frontend/backend ne constituent pas un parcours navigateur→Flask exécuté.
Images et runners préexistants, `--pull=never`, réseau extérieur coupé,
rootfs/checkout en lecture seule, environnement vidé, bytecode désactivé,
sources synthétiques et sockets/bases séparés de l'opérateur. Les adaptations
de fixtures et de collecte sont consignées sans affaiblir les assertions M0–M4.

Contre-lecture finale indépendante favorable, en lecture seule : 66 logs et
leurs empreintes, comptes/IDs, 128 empreintes courantes et diagnostics causaux
contrôlés ; aucun test concurrent relancé par le reviewer. Les deux conteneurs
de preuve, les sockets et les deux racines temporaires possédées sont supprimés,
avec inventaires finaux vides. Les permissions des sockets héritées des UID
PostgreSQL ont nécessité un runner de nettoyage existant, sans réseau,
rootfs en lecture seule et unique bind writable sur la racine temporaire du lot.
L'échec initial de nettoyage et cette résolution sont conservés dans le relevé.
Un conteneur anonyme resté `Created`, jamais démarré, a également été identifié
par sa commande exacte comme appartenant au driver interrompu, puis supprimé.
L'ancien contrôle limité aux conteneurs en cours d'exécution est requalifié ;
l'inventaire final inclut les conteneurs arrêtés/créés et est vide (`M5-P2`).

## Frontières ouvertes

M6 reste non commencé : aucun raccord réel de mutation, parcours complet,
lien produit, rafraîchissement d'inventaire ou lane conversationnelle du reçu.
M7 update, M8-C/M8-S/M8-A renderer et formats binaires restent non commencés.
Aucun provider/DAV live, migration opérateur, rebuild, restart, canari ou
changement plateforme n'est autorisé/livré. Les simulations ne prouvent ni
le comportement d'un Nextcloud déployé ni un rendu Writer ni Safari matériel.
La livraison Git M5 s'arrête après commit/push et vérification des refs.
