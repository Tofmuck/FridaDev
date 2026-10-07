# Atelier documentaire Frida V1 — contrat M6

Date : 2026-10-07. Périmètre : code et preuves isolées du parcours Markdown
create/copy. Livraison runtime, migrations opérateur, rebuild, canari DAV et
modèle réel restent ouverts. M7 reste non commencé.

Autorité : [roadmap active](../../todo-todo/product/frida-v1-document-workshop-todo.md#m6--markdown-createcopy-reçu-et-continuité),
mandat M6 du 7 octobre et [contrat M5](frida-v1-document-workshop-m5-contract.md).
Branche nouvelle `FridaV1-Document-Workshop-M6`, créée avant édition depuis M5
exact `6ea19f93bab0c1fb14fd4465ddc449f60f1531e4`, parent M4 exact
`cc72aa963366660a6a135b66d206e39671556e8b`. Aucun merge/rebase ; références
M0–M5/main préservées. Les preuves historiques et l'erratum M4 ne sont pas réécrits.

## Plan et propriétaires

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » Le raccord minimal conserve toute l'autorité M5 et complète ses
consommateurs. Pas de second inventaire, journal de succès, job, upload de secours
ou renderer. L'absence d'exécuteur runtime M5 et les consommateurs incomplets
étaient les frontières attendues de M6, sans finding imputé à M5.

| Responsabilité | Propriétaire effectif |
| --- | --- |
| Résolution paresseuse du client et des prérequis | `document_workshop_runtime.get_executor`, registrar serveur existant |
| Configuration Nextcloud | `NextcloudDocumentReadClient.from_env` / résolution serveur existante |
| Racine commune fichier/rendu | `workspace_files._storage_root`, aucune nouvelle racine |
| Confirmation, claim, journal, publication atomique | M5 `document_workshop_execution_store` / M3 |
| Séquence hors transaction et compensation | M5 `DocumentExecutor` / client mutateur M5 |
| Lecture fraîche explicitement mobilisée | M2 `workspace_document_content_service` |
| Reçu immuable et projection privée | SQL M5 `document_receipts`, `document_workshop_receipts` |
| Inventaire | `workspace_files` / `workspace_folder_document_list` et coordination M2 du sidebar |
| Lien | GET produit folder/file, bundle M5 vérifié, cache commun de la révision |
| Cartes/réhydratation et observation executing | contrôleur atelier existant, références durables du transcript |
| Lane tardive | même `inject_receipt_lane` dans `chat_main_payload` et `document_workshop_turn` |

Le client n'est pas un harnais : le serveur normal fournit cette factory au
registrar existant. Chaque confirmation possède un mutateur neuf et sa preuve
de création ; aucune instance mutatrice concurrente ne partage cette preuve.
La factory résout les valeurs Nextcloud existantes, vérifie la racine writable et
lit les colonnes requises et les 14 triggers d'autorité M3–M5 activés sans
créer le schéma. Configuration, cache ou schéma incomplets :
capacité `confirm=false`, POST 503 avant claim/effet. Imports et GET ne contactent
pas DAV et n'appliquent aucune migration atelier. `prepare` reste sa capacité M4
distincte ; update/binaire/Writer/UNO restent indisponibles.

## Exécution et publication

La confirmation lie action, contexte, conversation, répertoire et révision.
Son request_id et son claim distinct M3 n'appellent aucun modèle. M5 conserve
lease/fencing, sources fraîches, journal avant effet, préconditions HTTP,
`PUT If-None-Match: *`, publication SQL commune fichier/lien/rendu/révision/reçu,
compensation conditionnelle et refus du replay inconnu. Aucun SQL long autour
du DAV. Un succès DAV seul n'est jamais projeté comme succès produit.

Copy provient d'une proposition explicite avec source mobilisée et destination
distincte affichée avant clic. Une collision ne renomme pas, ne raccourcit pas
et ne devient pas une copie. Les ancêtres confirmés restent ceux de M0/M5.
Une adoption externe garde son origine sur l'identité originale ; la copie a
son propre file_id, artefact/révision et auteurs Frida. Les chemins historiques
upload, Notes, Exports, Images, dictée et Dialogue gardent leurs propriétaires.

## Reçu et lien

Le reçu SQL M5 n'est ni recréé au GET ni persisté dans un message. Sa projection
fermée porte : id, action_id, artifact_id, workspace_file_id, revision_id,
conversation_id, workspace_folder_id d'origine, operation, format, relative_path,
name dérivé sans réécriture, creation_author, revision_author, request_turn_id
stable UUID, confirmation_turn_id, confirmed_at, created_at, nextcloud_file_id,
nextcloud_etag, canonical_sha256, content_sha256, product_link et la qualification
`publication_evidence=historical`. Aucun texte de demande, canonical, Markdown,
journal, credential, scope secret ou URL modèle n'y figure.

GET `/api/workspace-folders/<folder_id>/files/<file_id>/content` est le raccord
minimal ajouté : l'ancien accès Markdown existant concernait uniquement un
dérivé OCR, pas les fichiers produits. La nouvelle surface réutilise l'identité
et le stockage communs, avec folder/file UUID exacts, répertoire actif lié,
receipt correspondant et preuve intégrale M5. Elle refuse tout paramètre query,
ne reçoit aucun chemin filesystem/DAV/URL, ne crée aucun partage public et relève
de la même protection publique Authelia/Caddy que les routes produit existantes.
Golden exact : une route GET ajoutée, 132 routes, aucune modification du guard
admin ni des frontières plateforme.

Le téléchargement renvoie les octets de la **révision publiée attestée** depuis
le cache commun vérifié, en attachment texte, `private, no-store` et `nosniff`.
Il ne prétend pas être une relecture DAV fraîche. La mobilisation ultérieure
réutilise exclusivement M2. Mauvais répertoire/identité ou absence réelle :
404 ; répertoire actif dont la liaison est indisponible, bundle/cache ou lecture
SQL indisponibles : 503 content-free. GET action
ne fournit aucun reçu/lien exécutable quand la preuve complète manque et projette
`remote_uncertain / document_publication_unknown` sans muter le résultat historique.

## Inventaire et réhydratation

Après succès prouvé, le contrôleur rafraîchit l'inventaire de son répertoire
d'origine via le propriétaire commun et ses générations M2 par famille/folder.
Même après navigation, un succès validé rafraîchit ce répertoire sans rendre de
carte dans le nouveau thread. Une réponse de listing antérieure ne peut remplacer
la publication plus récente. La présence dans une autre conversation du même
répertoire n'est ni source, ni cible, ni sélection ou contenu de prompt.

La lecture HTTP de l'inventaire propage une panne SQL en 503 sans items ; elle
ne fabrique pas `[]`. Le refresh M6 conserve le cache précédemment visible en
cas d'erreur. Le succès durable conserve son lien et affiche « Inventaire non
actualisé » si le nouveau file_id n'a pas été observé. Recharger explicitement
le contexte peut relancer uniquement ce refresh, jamais la confirmation.

Les cartes chargent leurs identités durables depuis les messages et le GET de
l'action. Après refresh/perte de réponse, une action encore executing est
observée par GET ciblé toutes les 750 ms pendant qu'une carte de cette action
est montée dans sa conversation, ou que son atelier est ouvert. Une panne de
GET conserve l'état et reprend cette consultation. La terminaison, navigation,
annulation ou disparition de la carte arrête cette observation ; aucun scanner
Nextcloud, synchroniseur de fond, nouveau claim ou POST de reprise. Les gardes
restent par action/conversation/répertoire ; annuler A ne révoque pas B.

La confirmation est retirée synchroniquement de toutes les cartes et sa tentative
reste conservée selon M5. Clavier, dictée, Dialogue, deux thèmes et présentation
téléphone utilisent le même contrôleur ; aucun chemin de confirmation concurrent.

## Continuité, facultés et manifeste

Après construction des entrées constitutives, la même fonction lit **un seul
reçu : le dernier de la conversation et du répertoire concernés**. Historique
supplémentaire = **zéro**, borne explicite sans nouveau réglage ni budget.
La lecture SQL historique n'ouvre ni canonical, ni rendu/cache, ni journal et
n'appelle aucun lecteur DAV. Le reçu ne prouve pas que Frida connaît le contenu
et ne sélectionne/recharge aucun document automatiquement.

La projection devient une lane system tardive de métadonnées non souveraines,
annoncée comme données et jamais instruction. Elle est distincte de
`document_lane` (sources) et précède la capsule à sa place contractuelle, dans
le tour normal comme dans la préparation. Les provenances par index survivent
au gel documentaire et sont celles du payload réellement estimé et envoyé.
Dans la préparation, l'ordre final reste sources → reçu → capsule → instructions
d'enveloppe M0 ; dans le tour normal, la capsule reste terminale. La capsule
documentaire reçoit ses constantes de provenance existantes par index, comme
les sources et le reçu. Ce raccord ferme un défaut hérité d'attribution générique
révélé par la preuve renforcée, sans changer aucun message envoyé.
`document_receipt_lane` a son statut/count/volume/origin content-free dans le
manifeste, et entre dans les comptes et contradictions de lanes ; aucun contenu
de reçu n'apparaît dans l'observabilité technique. Les métadonnées privées produit
autorisées ne changent pas la politique des logs privés existants.

La conversation canonique conserve uniquement la vraie demande et la courte
réponse Frida. Memory, Identity, Summary, Biblio et Stimmung, y compris les effets
différés, ne reçoivent ni cette lane synthétique ni le contenu documentaire ajouté.
Les paroles légitimes restent dans leurs entrées. Les providers bornés et les
frontières synthétiques existantes des services constitutifs capturent leurs
entrées : preuve de raccord/non-contamination, aucune conclusion sur la sémantique
d'un modèle réel ni exécution complète des facultés réelles.

Admission documentaire inchangée : `token_utils.estimate_tokens`, E + 24 000
≤ 400 000, enveloppe incluse au gel, aucune marge/réserve supplémentaire. Modèle
documentaire OpenRouter, défaut normal 8 192 et overrides existants préservés.

## Preuves et livraison future

Le [relevé daté M6](../baselines/document-workshop/frida-v1-document-workshop-m6-20261007.json)
consigne baseline exacte, nouveautés, voisins, versions, commandes, IDs chargeables,
collecte/exécution, durées/exits/skips et adaptations de fixtures. Les preuves
HTTP complètes sont séparées des Chromium à fetch simulé. Les erreurs de montage
et le run HTTP contaminé par partage de DB sont qualifiés, jamais comptés verts.
Le harnais final possède sa propre base/socket et partage uniquement son réseau
`none` avec le navigateur. Les synchronisations DAV sont des événements causaux ;
la supervision réelle des claims/préparation reste active.

Comparaison finale : **1 523 historiques + 29 nouveaux = 1 552 cas distincts**,
exits 0, zéro skip, mêmes IDs historiques et collecte concordante. Nouveautés :
11 PostgreSQL/Flask/DAV, 3 unitaires de lane, 10 Chromium à fetch simulé et
5 Chromium à HTTP natif complet. Les **70 voisins supplémentaires** sont verts
et séparés (1 622 avec eux, sans doubler les 74 voisins déjà dans la baseline).
La contre-lecture indépendante a fermé les refus de prérequis incomplets,
les classifications d'indisponibilité, le refresh d'origine tardif et
l'attribution capsule après gel ; aucun finding code confirmé ne reste ouvert.

### Correctif de harnais P3-M6-AUD-01/02 — 7 octobre 2026

Le [relevé séparé du correctif](../baselines/document-workshop/frida-v1-document-workshop-p3-m6-aud-20261007.json)
préserve la preuve M6 initiale et les rouges causaux. Les trois fichiers de tests
concernés étaient identiques sur M5 et la base M6 `d676f4fb` : leurs hypothèses
temporelles ne sont pas des régressions produit M6. Aucun code produit, contrat
métier, route, migration, dépendance ou réglage runtime ne change.

**P3-M6-AUD-01 corrigé.** Le NOWAIT historique peut rejeter la transaction courte
de supervision. Le harnais identifie désormais chaque invocation HTTP par un
`application_name` unique passé à `psycopg.connect`, restauré en `finally` sur
le seul thread de requête. Une connexion réellement taguée calibre la sonde
indépendante `pg_stat_activity` : aucune transaction de requête ouverte, active
ou idle, sans seuil d'âge. Watchdog, renouvellement et garde asynchrone exécutent
leurs vrais stores sans hériter du tag. Un rendez-vous retient un seul appel
watchdog après ses vrais verrous jusqu'à la sonde, puis deux appels réels terminés
prouvent sa continuation. Annulation HTTP 200, fermeture physique, réponse 503,
absence de révision/assistant tardif et appel fournisseur unique sont conservés.
Le contrôle négatif tient volontairement une transaction du thread de requête
pendant le SSE HTTP réel : la même sonde la rejette, puis la fermeture la libère.

**P3-M6-AUD-02 corrigé.** Les chemins nominal et erreur bloquent explicitement
la réponse de fixture. La seconde saisie/clic a lieu pendant cette attente
constatée ; un seul appel, le brouillon et la bulle utilisateur sont vérifiés
avant libération. Le retour `busy → idle` du contrôleur dictée observe le vrai
`finally` produit ; une soumission ultérieure est autorisée. Réhydratation,
transcript canonique et absence d'assistant optimiste restent prouvés. Deux
contrôles négatifs injectent un second fetch dans le harnais seul et font rejeter
la même assertion ; ils ne prétendent pas contourner la garde via l'UI produit.
Les gates sont libérées en `finally`. Aucun délai ne décide de l'ordre causal.

Un finding **indépendant P3-M6-AUD-03 reste ouvert**, hors correctif : le harnais
inchangé `cancel_with_external_lock` ne draine pas une supervision déjà entrée
avant `pause_checks`. Le run élargi de 87 cas a un échec (préparation 503 au lieu
de 200). Le diagnostic avec helper de base et helper corrigé force un contrôle
déjà admis à rencontrer le verrou réel et reproduit l'interruption, avec une
assertion plus précoce sur le claim. Les fichiers et fonctions de supervision
concernés sont hérités de M5. Cette variante causale n'établit pas l'ordonnancement
de l'échec spontané. Aucun finding produit n'est établi et ce troisième harnais
n'est pas modifié ici ; un éventuel rejeu vert ne ferme pas cette course.

Comparaison complète du correctif : **1 552 cas historiques conservés à l'identité
exacte + 3 nouveaux contrôles négatifs = 1 555 distincts**, tous verts dans la
sélection finale, zéro skip/annulation. Les 70 voisins restent séparés (1 625 avec
eux). Les cinq parcours M6 à HTTP natif et les dix à fetch simulé sont conservés
et comptés séparément. Ciblés, diagnostics et répétitions incluses dans ces
sélections ne sont pas recomptés. L'échec intermédiaire de P3-M6-AUD-03 reste
consigné ; ces résultats ne constituent pas une fermeture de cette anomalie.

M6 ne livre aucune nouvelle migration. Pour une livraison future, après GO
distinct, Celebrimbor vérifie la version et l'état des migrations atelier M1
contextes → M2 adoption/liens → M3 claims → M4 actions/révisions → M5 exécution/
rendus/reçus/journal et triggers, puis la racine commune et configuration existantes.
Les scripts versionnés correspondants, à vérifier et appliquer seulement s'ils
manquent lors du futur lot autorisé, sont dans cet ordre :

1. [document_workshop_contexts.sql](../../../core/sql/document_workshop_contexts.sql) ;
2. [workspace_document_adoption.sql](../../../core/sql/workspace_document_adoption.sql) ;
3. [conversation_turn_claims.sql](../../../core/sql/conversation_turn_claims.sql) ;
4. [document_workshop_actions.sql](../../../core/sql/document_workshop_actions.sql) ;
5. [document_workshop_execution_m5.sql](../../../core/sql/document_workshop_execution_m5.sql).

L'application ne les applique jamais par imports/GET. Le code M6 exige ce socle ;
un rollback applicatif vers M5 conserve fichiers, reçus et schéma et désactive le
consommateur runtime, sans supprimer des données ni rejouer une action.

Sauron possède image/processus/runtime/secrets/permissions/réseau et toute
modification hors checkout applicatif. Le lot futur doit coordonner ces prérequis,
appliquer seulement les migrations réellement manquantes selon leur contrat,
rebuild uniquement FridaDev, vérifier version/health, puis recette contrôlée
capacité → préparation synthétique → confirmation humaine → fichier/lien réel →
inventaire autre conversation sans sélection → réouverture/reçu → tour suivant
normal et documentaire sans source. Le premier canari Markdown synthétique borné
exige fermeture hermétique puis GO distinct **et** confirmation humaine du contrat.
Aucun de ces actes opérateur/live n'est exécuté ou autorisé par la livraison Git M6.
