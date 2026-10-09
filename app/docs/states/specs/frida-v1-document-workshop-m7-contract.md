# Atelier documentaire Frida V1 — contrat M7

Date : 7 octobre 2026. Autorité : mandat M7 explicite de Tof et
[roadmap active](../../todo-todo/product/frida-v1-document-workshop-todo.md#m7--update-markdown-id-stable-et-conflit).
Base exacte M6 : `b00eb95001755295dcc301232272a8070d26cd78`, parent
`47a85218e02aa749372e524ec9bc4d72ae9a1c10`. Branche nouvelle
`FridaV1-Document-Workshop-M7`, créée avant toute édition, sans merge/rebase.
M0–M6/main sont préservés. Le
[relevé M7](../baselines/document-workshop/frida-v1-document-workshop-m7-20261007.json)
porte les commandes, identités, résultats intermédiaires et limites de preuve.

Code/preuves isolées fermés après contre-lecture indépendante : 1 557 références
conservées + 47 nouveaux = 1 604 distincts verts, 70 voisins supplémentaires
séparés, exits 0 et zéro skip/annulation. Les 47 nouveaux comprennent 29 cas
SQL/Flask/DAV, cinq clients HTTP et 13 parcours natifs navigateur/Flask/SQL/DAV.
Les cinq natifs M6 et dix tests à transport simulé restent distincts. Les échecs
intermédiaires et deux évolutions d’assertions historiques restent qualifiés dans
le relevé, sans double comptage des ciblés.

M7 couvre update Markdown à identité stable, conflits et réconciliation ciblée
sans nouvelle écriture distante. Livraison runtime, migration opérateur, rebuild,
canari Nextcloud/Versions et appel OpenRouter réel ne sont pas autorisés par ce
mandat. M8-C, Writer, DOCX/PDF et suivants restent non commencés.

## Plan, propriétaires et observations de base

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d’effets de
bord ? » Le chemin minimal étend l’action, le journal et l’inventaire existants.
Il conserve M2 pour lire, M3 pour confirmer et clôturer les détenteurs, M4 pour
préparer, M5 pour journaliser et M6 pour présenter/reprendre les métadonnées.
Aucun second inventaire, journal concurrent, job, scanner ni framework de reprise.

Les observations de cadrage sont confirmées dans le M6 exact : enveloppe et
contraintes create/copy, INSERT allouant un nouveau fichier lors de publication,
auteur de création Frida, preuve comparant la révision au fichier courant,
téléchargement choisissant un reçu sans pointeur de révision courante et triggers
invalidant les contextes/actions lorsque leurs cibles/sources changent. Ce sont
les frontières historiques attendues de M6, sans requalification en bugs M6.
M7 adapte ces frontières ensemble, sans modifier les archives de preuves.

| Étape | Autorité et propriétaire | Panne / limite |
| --- | --- | --- |
| Préparation | `document_workshop_turn`, lecteur frais M2, `document_workshop_update_target`, action/révision M4 | Version forte ou identité indéterminée : aucune action update confirmable |
| Confirmation | service HTTP commun, `execution_store.begin`, claim M3 distinct | Identités d’action/context/conversation/répertoire/révision exactes ; aucune autorité depuis DOM/source/reçu |
| Contrôle frais | mêmes services M2, garde locale de cible figée | Disparition/substitution/version/empreinte différentes : aucun PUT |
| Intention + effet | journal existant, client DAV de production | Un seul PUT conditionnel ; aucune transaction SQL pendant DAV |
| Publication | `document_workshop_update_publication`, mêmes tables/cache | Transaction SQL commune ; fenêtre distante/locale explicitement non atomique |
| Observation / réparation | GET action existant, `document_workshop_update_reconciliation`, nouveau claim M3 | SQL seul sous preuves complètes ; absence de preuve : résultat inconnu |
| Présentation | contrôleur atelier, propriétaire d’inventaire M2, reçus/lane M6 | GET/navigation/rafraîchissement ne rejouent jamais le PUT |

## Cible et révision figées

La cible vient exclusivement du contexte documentaire serveur explicitement
sélectionné. Les références de lecture ne deviennent pas des cibles. Le dernier
reçu et le fichier affiché dans le DOM ne donnent aucune autorité d’écriture.
La compréhension de la demande reste agentique : aucun routage lexical ajouté.

La préparation mobilise les octets frais de la cible Markdown et conserve dans
`document_actions.target_version` : ID local/répertoire, chemin, identité distante
scope+file-id, ETag fort exact, SHA-256, taille/date d’observation, document-ref,
origine/auteur de création, source-kind, nom, date de création, MIME et noms/preuves
du lien, ainsi que la révision de base de l’artefact. L’ETag, l’identité, le chemin
et l’empreinte sont des preuves distinctes. La révision proposée est immuable.
Un modèle proposant un autre chemin est refusé, sans correction silencieuse.
Si la cible est également une source explicite, l’observation est partagée et
sa progression n’est signalée qu’une fois. Les autres formats ne sont pas lus
automatiquement comme cibles d’update.

Le clic consomme l’action préparée et crée son propre claim M3 avec l’ETag figé.
Il n’appelle pas le modèle et ne renouvelle pas les préconditions. Les gardes sont
les mêmes pour les requêtes HTTP construites hors UI. Annulation ciblée,
génération, lease et fencing restent souverains.

## PUT et conflits

Immédiatement avant l’écriture, M2 relit la cible à son chemin exact et compare
identité/répertoire/chemin/version/empreinte/taille avec la préparation. Aucun
scan global ni recherche d’une cible déplacée. Une version absente/faible,
identité incompatible, disparition ou remplacement ferme l’action sans PUT.

`NextcloudDocumentMutationClient.update_document` transmet réellement
`If-Match: <ETag fort préparé exact>` et les octets de la révision préparée dans
l’unique PUT. Il accepte un succès update 200/204 avec ETag fort de sortie et
observe de nouveau identité/taille/octet exacts. HTTP 412 est un conflit ; un
transport interrompu ou un succès dont la preuve postérieure manque reste
inconnu. L’ETag n’est jamais rafraîchi pour retenter.

Update ne crée ni collection ni ressource de remplacement, et n’utilise pas
`If-None-Match`. Aucun retry, fusion, renommage, copie de secours, DELETE ou
réécriture compensatoire. Create/copy gardent leur création et leur compensation
M5 séparées. Nextcloud Versions reste l’autorité de récupération, sans restauration
automatique ni restauration locale supposée équivalente.

Deux confirmations dans deux conversations peuvent atteindre DAV avec la même
ancienne version ; une seule précondition distante peut réussir. La contention
réelle des gardes SQL `NOWAIT` peut ensuite refuser l’observation/publication du
gagnant : aucun reçu de succès n’est promis dans cette fenêtre. La fin de requête
tente de clôturer son seul claim M3 puis observe l’état sans replay ; si SQL reste
indisponible ou occupé, l’expiration de lease reste l’autorité avant le prochain GET. Le résultat reste
inconnu si aucune preuve acquittée/publiante suffisante n’est durable. Ce refus
fermé est distinct du succès nominal et du 412, tous deux éprouvés séparément.

Diagnostic **OBS-M7-CONC-01**, 9 octobre 2026 : un entrelacement contrôlé
éprouve cette fenêtre jusqu'au premier GET `executing/confirmed`, claim SQL
encore vivant après arrêt des superviseurs, puis `remote_uncertain` après
expiration artificielle de sa lease dans la base de preuve. Le contrôle sans
chevauchement publie un reçu ; deux PUT produisent un seul effet dans les deux
cas. L'attente de terminalité immédiate du test de concurrence est donc trop
forte pour cette branche contractuelle. Aucun correctif produit/test dans le
commit diagnostique `970ccb37` ;
l'ordonnancement exact des rouges historiques reste inconnu. Voir le
[rapport et sa proposition de suite bornée](../audits/frida-v1-document-workshop-obs-m7-conc-01-20261009.md)
et le [relevé daté](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-20261009.json).

Correctif de preuves distinct du même jour, base `970ccb37` : l'ID historique
couvre désormais le nominal avec deux PUT en vol, puis commit/retour du perdant
avant observation du gagnant, reçu vérifié unique et conflit sans reçu. Un
nouveau test maintient le vrai verrou du perdant jusqu'aux trois refus `55P03`
du gagnant et à son retour HTTP. Il joint les vrais superviseurs puis observe,
par connexion distincte, claim actif/lease future et action `executing/confirmed`
sans reçu ; le premier GET ne change aucun champ durable. Après expiration
artificielle de ce seul claim en DB jetable, GET `remote_uncertain`, claim `lost`,
sans preuve de succès ni réparation de métadonnées, nouveau claim ou appel DAV.
Ce contrôle n'est pas une mesure d'expiration naturelle et ne modifie ni les
durées/constantes produit de lease, ni le renouvellement, ni le contrat. Les
snapshots comparent toutes les colonnes des tables concernées, journal compris ; `lease_live` est une projection temporelle
vérifiée séparément. Répétitions sans mutation ni replay dans les deux cas.
Voir le [rapport du correctif](../audits/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.md)
et le [relevé daté](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.json).
La cause exacte des rouges historiques demeure inconnue ; le défaut d'attente
immédiate est corrigé dans les preuves, sans patch produit.

## Publication et historique

L’intention durable précède tout effet distant. Après un succès distant établi,
la transaction SQL ajoute le rendu et le reçu immuables, change le pointeur de
révision de l’artefact, clôture le claim et l’action, puis UPDATE le fichier et
son lien existants. Elle conserve ID, nom, chemin, identité distante, origine,
auteur de création, date et MIME de création. Elle ne fait aucun INSERT de copie
dans `workspace_files`. Le nouvel auteur de révision est Frida, y compris pour
un original externe adopté.

L’ordre de clôture avant UPDATE fichier/lien évite l’auto-invalidation de la
publication autorisée. Les vrais triggers restent actifs : ils invalident les
autres préparations/contextes périmés, notamment entre deux conversations du
même répertoire. Un rollback annule ensemble reçu/rendu/pointeur/fichier/lien
et clôture de succès. Aucun verrou SQL ne couvre l’attente DAV.

`document_workshop_publication_proof` vérifie séparément le bundle historique
immuable et le bundle de la révision courante pointée par l’artefact. Les octets
anciens restent liés à leurs anciennes empreintes. Un update ultérieur légitime
ne dégrade pas les anciens reçus. Le lien folder/file télécharge la révision
courante complète, jamais arbitrairement le premier reçu. Cache, scope, auteurs,
MIME, identité, noms, claims, intentions/outcomes et rendu restent contrôlés ;
une corruption ne produit pas une projection de succès ni un téléchargement
autorisé. La lane tardive lit seulement les métadonnées durables du dernier
reçu : lire ce reçu ne mobilise pas le contenu.

## Résultats inconnus et réparation ciblée

| Observation durable | Résultat autorisé |
| --- | --- |
| Refus avant effet / 412 | Échec ou conflit, sans publication et sans compensation update |
| PUT connu réussi, publication SQL rollback | Résultat inconnu initial ; réparation SQL ciblée possible sous les preuves ci-dessous |
| Réponse DAV perdue | Inconnu, même si les octets frais ressemblent à la révision proposée : cela ne prouve pas l’auteur de l’effet |
| Réponse de commit perdue | Une connexion indépendante établit le succès seulement si tout le bundle publié est relu et vérifié |
| Interruption / lease perdue | Ancien détenteur refusé ; jamais réarmé et jamais autorisé à réécrire |
| Changement distant supplémentaire | Préservé ; aucun succès attribué aux octets plus récents |

Le GET existant peut effectuer une seule tentative bornée de réparation des
métadonnées d’une action update `remote_uncertain`. Il exige l’outcome de succès
200/204 acquitté et durable de l’unique PUT, ses identités/empreintes, le claim
original inactif, la cible locale encore exactement à sa base et le contexte
encore valide. Une nouvelle confirmation M3 interne, avec nouveau turn-id,
owner/génération, fingerprint `sha256('metadata:'+action_id)` et ETag préparé,
porte sa propre intention `metadata_reconciliation`. L’ancien token ne reprend
aucune autorité.

L’observation fraîche exige le scope/chemin/file-id préparés, l’ETag de sortie
acquitté et les octets exacts de la révision. La publication SQL seule utilise
la nouvelle autorité et journalise `metadata_published`. La preuve historique
exige les deux événements liés, leur serializer fixe, fingerprints, ETags,
claims et bundles complets. Un commit de réparation dont la réponse est perdue
peut également être établi par une connexion indépendante, sans retry.

Une tentative déjà journalisée mais échouée/expirée reste inconnue et nécessite
une intervention contrôlée ; les GET suivants n’insistent pas. Une disparition,
scope invalidé, base locale changée, outcome absent/incertain ou observation
distante plus récente interdit la réparation. Aucun second PUT, DELETE, POST de
reprise, scanner ni retour à pending. La simulation n’atteste aucun mécanisme de
récupération Versions réel. Une nouvelle demande après conflit suit une nouvelle
préparation et sa propre confirmation.

## UI, continuité et budgets

La carte indique modification, cible exacte, identité conservée et absence de
restauration automatique. « Modifier le fichier » utilise la confirmation commune
et disparaît synchroniquement au clic, y compris pour un bouton détaché/double
clic. Succès durable, conflit, échec et inconnu sont distingués. Aucun bouton de
force/fusion/secours. Navigation, réponses tardives et annulation restent liées
aux identités d’origine ; l’inventaire partagé actualise la même entrée et ne
sélectionne rien dans une autre conversation. Une panne de rafraîchissement
préserve la publication sans rejouer l’écriture.
Le succès SQL précède le GET asynchrone d’inventaire. Si un nouveau contexte
editing du même scope est ouvert pendant ce GET, sa liste de cibles est
reprojetée depuis le propriétaire partagé à réception, en conservant seulement
la cible de ce contexte. Le reçu ne sélectionne jamais son fichier. La preuve
native retient puis libère réellement ce GET ; le seed du harnais attend aussi
la publication DOM du propriétaire, distincte de la carte succeeded.
Après succès d’un update, la carte reste historique mais son contexte cible est
fermé par les triggers. L’UI refuse une nouvelle soumission sur cette autorité,
conserve le brouillon et demande une réouverture ou un choix de cible explicite ;
elle ne recrée pas silencieusement de contexte.

Les deux compositions normale et documentaire reçoivent la lane M6 tardive de
métadonnées avec auteurs/opération/révision. Les sources/canonical/reçus
synthétiques restent absents des entrées Memory, Identity, Summary, Biblio et
Stimmung ; la provenance du payload gelé est préservée.
`token_utils.estimate_tokens` compte le payload complet réellement transmis,
`E + 24 000 ≤ 400 000`, sans marge ni deuxième réserve. OpenRouter, modèle,
budgets et défaut normal 8 192/overrides existants sont inchangés.

## Migration et suite opérateur — à ne pas exécuter dans M7

Migration explicite : `app/core/sql/document_workshop_update_m7.sql`, après les
pré requis existants M1 contexte, M2 adoption, M3 claims, M4 actions et M5 exécution,
avec le schéma fichiers/liens/conversations existant. Elle étend opérations/états,
auteurs et événements, ajoute la preuve de cible figée et l’unicité d’artefact par
fichier, et borne l’unique transition terminale de réparation. Les historiques
ne sont ni migrés en nouveaux fichiers ni supprimés. Idempotence et ordre sont
éprouvés uniquement sur PostgreSQL isolé. Aucune migration à l’import/bootstrap
ou durant GET/POST produit.

La disponibilité runtime vérifie les colonnes/contraintes M7 effectives, index,
fonction de fermeture et trigger, plus les prérequis M2–M5 existants. Sans M7,
create/copy restent possibles selon M6 ; update est annoncé indisponible et
refusé avant consommation/effet. Une restauration partielle de CHECK historique
sous le même nom ne suffit pas à annoncer update.

Pour un futur GO distinct : vérifier d’abord la chaîne de migrations sur une
copie isolée des données et les prérequis du cache, appliquer les migrations
applicatives dans cet ordre selon procédure opérateur validée, puis rebuild du
seul service FridaDev, health et surfaces concernées. Préparer un canari update
sur un document jetable avec identité/ETag avant-après, concurrence réelle 412
et récupération Versions contrôlée par l’opérateur. Les besoins réseau/image/
exploitation/Versions plateforme reviennent à Sauron dans un lot séparé.

Retour arrière : ne pas appliquer un down destructif supprimant révisions/reçus
update ou restaurant les CHECK create/copy sur des données M7. Garder schéma et
historiques compatibles ; un binaire M6 seul ne sait pas projeter ces reçus ni
suivre leurs révisions courantes. Un rollback runtime après données M7 exige
donc une version applicative compatible avec ces données, à valider séparément,
sans remettre les anciens octets à la place des versions courantes. Aucun de
ces gestes opérateur n’a été exécuté ici.
