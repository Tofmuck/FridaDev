# Atelier documentaire Frida V1 — contrat M2

Date : 2026-10-05. Statut : P2-M2-01 corrigé sur code/preuves, comparaison
historique 567/567 ; succès historique 536/536 et revue G-R1–G-R4 Approved conservés.
P2-M2-03 corrigé séparément sur la frontière frontend du listing (594/594
historiques) ; P2-M2-02 corrigé séparément sur Exports/Images/Notes,
P2-M2-04 backend corrigé séparément (713/713 historiques) ; P2-M2-05 corrigé
séparément sur le résumé de réconciliation (716/716) ;
livraison runtime ouverte. Le retour final porte la livraison Git dédiée.
La [roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md#m2--adoption-et-lecture-distante-ciblées)
reste l'unique spécification et porte les commandes, résultats et dispositions
des contre-audits. M2 part de M1 corrigé `c6f648ba`. Migration opérateur,
rebuild et lecture DAV déployée exigent une autorisation distincte. M3–M10 et Z
ne sont pas commencés ; `editing` et `capabilities.prepare=false` restent seuls
disponibles. Aucune préparation, mutation distante ou appel modèle dans M2.

## Autorité et interfaces

`document_workshop_routes.py` réutilise le registrar M1 pour deux routes :

| Route | Entrée et réponse |
| --- | --- |
| `GET /api/workspace-folders/{id}/documents/remote` | `context_id` obligatoire, `collection_ref` opaque optionnelle ; aucun paramètre inconnu ou dupliqué. Réponse `200` : `ok`, `workspace_folder_id`, `collection` (`reference`, `relative_path`, `name`), `items`, `complete:true`. |
| `POST /api/workspace-folders/{id}/documents/adopt` | Exactement `context_id` et `resource_ref`. Réponse `201 adopted` ou `200 already_linked`, identité `workspace_file_id` et projection `file` commune. |

Le service `workspace_document_adoption_service.py` revalide le contexte serveur
M1, la conversation active, son répertoire et le mapping Nextcloud `linked`.
La navigation revalide ce scope après I/O ; la publication le verrouille à
nouveau en SQL. Aucun nom, chemin, href, URL ou état fourni par le navigateur
ne fait autorité. Ouvrir le contexte M1 seul ne fait toujours aucun appel DAV.

`RemoteReferences` conserve au plus 4 096 observations UUID dans un registre
FIFO protégé par verrou, local au processus. Chaque référence est liée au
répertoire et au scope distant. Redémarrage/éviction → refus puis réouverture
explicite ; aucune durabilité ni TTL revendiqué. L'identité d'une collection
explicitement rouverte est revérifiée. La racine initiale exige une collection
dans le scope ; une référence de collection sans identité canonique est refusée.

Les fichiers sont `already_linked`, `adoptable`, `collision` ou `incompatible`.
`legacy_verification_required` reste provisoire jusqu'à la preuve des octets.
Une collection navigable porte `is_collection:true` et
`reason_code=document_collection` ; sa catégorie `incompatible` interdit son
adoption comme fichier. Les métadonnées manquantes ne sont jamais inventées.

Les erreurs exposent une raison fixe et le texte « Opération documentaire
indisponible. » : requête `400`, absent `404`, conflit/scope/référence `409`,
borne `413`, incompatibilité `422`, indisponibilité/commit incertain `503`.
Aucun XML, href DAV, exception brute, secret ou contenu source dans ces erreurs
ou dans une nouvelle collecte technique. Depuis la correction G-R1, les raisons
métadonnées sont distinctes, sans changer les conditions d'admission :

| `reason_code` | HTTP de refus | Message UI fixe |
| --- | --- | --- |
| `document_remote_identity_invalid` | 422 | Identité distante absente ou non vérifiable. Cette ressource ne peut pas être adoptée. |
| `document_remote_version_invalid` | 422 | Version distante absente ou non vérifiable. Ce fichier ne peut pas être adopté. |
| `document_remote_size_invalid` | 422 | Taille du fichier absente ou invalide. Ce fichier ne peut pas être adopté. |
| `document_type_unsupported` | 422 | Format de fichier non pris en charge. Choisissez un autre fichier. |
| `document_source_limit` | 413 | Le fichier ou son contenu extrait dépasse les limites de lecture. Choisissez une source moins volumineuse. |
| `document_ocr_required` | 422 | Ce document nécessite une reconnaissance de texte (OCR) avant son adoption. |
| `document_extraction_incomplete` | 422 | Le texte ne peut pas être extrait intégralement. Choisissez une version dont tout le texte est lisible. |
| `document_remote_changed` | 409 | Le fichier ou le répertoire a changé depuis sa lecture. Actualisez la collection, puis sélectionnez de nouveau la ressource. |
| `document_remote_missing` | 404 | La ressource a disparu ou a été déplacée. Actualisez la collection et choisissez explicitement une ressource. |
| `document_adoption_commit_unknown` | 503 | Résultat de l’adoption incertain. Aucun nouvel essai automatique. Actualiser la collection pour vérifier son état. |

Un listing réussi reste HTTP 200 ; ses items portent les motifs de classification
connus (identité/version/taille, format ou limite). Les refus d'extraction et de
publication apparaissent lors de l'adoption. Identité/scope non prouvés, ETag fort non prouvé et taille absente,
non entière ou non positive sont distingués au point de connaissance. Ils ne
prétendent pas expliquer davantage les métadonnées DAV malformées. Le refus de
l'ETag persisté avant tout transport porte `document_remote_version_invalid`.

Lignes, erreurs de navigation et d'adoption utilisent une table fermée de textes
fixes du contrôleur, seulement pour une clé propre de type chaîne (`Object.hasOwn`).
Les autres motifs connus couvrent chemin, collection, collision, référence/scope,
archive/parseur/texte absent et indisponibilité ; `document_remote_response_limit`
explique ensemble taille/nombre d'éléments, que le backend ne distingue pas.
`document_remote_incompatible` reste honnêtement générique. Inconnu, clé héritée
ou valeur non chaîne → fallback fixe de la surface ; aucune lecture du champ
serveur `error`, d'un diagnostic, contenu, HTML, href ou exception comme message.
Une incompatibilité permanente n'invite plus à une actualisation inutile ;
aucun OCR, retry, nouvelle garde ou assouplissement n'est ajouté.

Les noms et chemins relatifs sont
des données de la seule surface produit, insérées via `textContent`.

## Lecture ciblée et bornes

`workspace_document_nextcloud_read_client.py` emploie la configuration serveur
Nextcloud existante. Seuls les segments validés du mapping construisent l'URL ;
les hrefs reçus sont des preuves de scope, jamais des instructions de navigation.
Même origine/racine, ressource elle-même ou enfant direct exigés ; redirects,
proxies, userinfo même vide, query/fragment même vides, traversées et ambiguïtés
encodées sont refusés. Aucun scan récursif, polling, pagination fictive ou GET
à partir d'une URL frontend.

| Frontière | Limite effective |
| --- | --- |
| `PROPFIND Depth: 1` | Une collection explicitement ouverte, XML 1 Mio plus un octet de détection, 256 enfants et la collection elle-même ; dépassement → aucune liste partielle. |
| Requête réseau | Timeout local de 12 secondes par requête ; aucune deadline de préparation M0 ajoutée. |
| Source téléchargée | 40 Mio ; taille DAV, `Content-Length` s'il existe et octets effectivement consommés concordants. |
| Archives DOCX/ODT | 4 096 membres, expansion cumulée réellement lue ≤64 Mio, sans extraction sur disque ; refus des traversées, doublons, symlinks, chiffrement, XML invalide/entités. |
| Texte extrait complet | UTF-8 ≤40 Mio ; aucun préfixe présenté comme complet. |
| Parseur binaire | Processus fixe Python `-I -B`, environnement nettoyé, mémoire 512 Mio, CPU 20 secondes, core dumps interdits, stderr jeté ; entrée par octets et type fixe uniquement. |

Les limites CPU/mémoire bornent le parseur ; elles ne sont ni le watchdog de
préparation M0 ni une expiration d'édition/pending. Aucun chemin, URL ou commande
du document n'est exécuté. Le worker ne reçoit aucun secret runtime.

Propriétés demandées : `resourcetype`, `oc:fileid`, `getetag`,
`getcontentlength`, `getcontenttype`. L'autorité service/SQL exige un `oc:fileid`
décimal positif canonique, sans zéro initial, de 64 chiffres au plus. Il est lié
au SHA-256 du scope origine/base/utilisateur/racine/mapping. L'identité, le chemin
exact, l'ETag fort opaque et le SHA-256 des octets observés sont des preuves
distinctes. Un GET unique avec `If-Match` est encadré par deux observations
`Depth: 0` conditionnelles ; identité/version/taille et ETag du GET concordent.
Conflit ou lecture incomplète → refus, sans télécharger une nouvelle version,
retry ni réparation. Les [propriétés DAV Nextcloud](https://docs.nextcloud.com/server/latest/developer_manual/client_apis/WebDAV/basic.html)
et [préconditions If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match)
décrivent le protocole public ; leur comportement déployé n'est pas prouvé ici.

Les gardes partagés de `workspace_document_paths.py` distinguent collection,
source et cible produit. `Documents[/sous-répertoire]/fichier` reste exact :
huit niveaux sous Documents, 180 points de code et 255 octets UTF-8 par segment,
1 024 octets UTF-8 pour l'ensemble. Clé de collision `NFC(path).casefold()` ;
aucun basename, trim, raccourcissement ou normalisation du nom affiché.

Sources : TXT, MD/MARKDOWN, DOCX, ODT, PDF textuel. Formats produit inchangés :
Markdown/DOCX/PDF. `extract_complete_source` conserve les espaces du texte brut ;
les formats binaires réutilisent les règles d'extraction textuelle historiques,
sans promesse de fidélité de mise en page. Le préflight conservateur refuse
images, formulaires, macros, objets, parties textuelles non couvertes et pertes
détectables : caractères DOCX non extraits, corps ODT mal structuré, actions PDF
actives notamment. G-R2 refuse les cellules/lignes ODT textuelles portant une
répétition autre qu'une forme lexicale valide de un ; cellules ordinaires,
répétition un et cellules/lignes répétées vides restent admises. G-R3 refuse
`mc:AlternateContent` DOCX sans concaténer Choice/Fallback ni choisir une branche.
Ces refus entiers donnent `document_extraction_incomplete`, sans modifier
l'extracteur historique ni créer de moteur ODF/OOXML. Chaque page PDF doit livrer du texte. Liens PDF passifs
HTTP(S) ou destinations locales bornées restent des données, jamais chargées.
Aucun OCR, renderer, résumé ou échantillonnage de secours.

## Adoption et persistance

La migration explicite `app/core/sql/workspace_document_adoption.sql` enrichit
`workspace_file_nextcloud_links` de champs nullable : `nextcloud_relative_path`,
`nextcloud_collision_key`, `nextcloud_file_id`, `nextcloud_scope_key`,
`nextcloud_etag`, `observed_at`, `observed_sha256`, `document_origin`.
Elle ajoute aussi `target_remote_identity` aux contextes M1. Aucun backfill
supposé des liens historiques. Index unique identité par répertoire/scope/fileid,
tombstones compris ; index unique chemin de collision des liens `linked` ;
contrainte SQL de forme identité/scope. Les `init_db()` explicites ne sont
appelés ni à l'import, ni au startup, ni par le `ensure_schema` partagé.
Appliquer les migrations M1 puis M2 fait partie de la future livraison autorisée.
Un schéma absent échoue fermé ; seule la DB isolée de preuve a été migrée.

`workspace_document_adoption_store.py` publie dans l'inventaire unique
`workspace_files` et son lien, sur la même connexion/transaction. Lecture et
extraction complètes précèdent la transaction ; celle-ci verrouille le
répertoire/mapping, le contexte/conversation et les lignes fichier/lien, puis
reclasse la ressource. Même identité → même ID, y compris après sélection
explicite d'un chemin déplacé. Un chemin occupé, même par une ligne OCR,
refuse le remplacement. Un lien historique exige le chemin exact et le SHA-256
des octets complets du cache identique aux octets distants ; pointeur et version
locale sont revérifiés sous verrou. Même ETag avec d'autres octets → conflit.

Un nouveau fichier adopté porte `source_kind=nextcloud_adoption` et
`document_origin=external`. L'origine inconnue d'un ancien lien reste inconnue ;
une adoption ne crée aucune provenance Frida/canonical. Le chemin et l'identité
enrichis sont revalidés par M1 au service GET et à l'INSERT SQL, sans rabattement
au basename. PDF reste source-only pour M1.

Les octets sont écrits sous deux UUID dans le stockage workspace existant,
avant publication SQL du pointeur ; chaque révision est immuable. Il s'agit
d'une visibilité locale atomique fichier/lien, sans transaction distribuée
filesystem/SQL. Échec certain avant commit : tentative de suppression du seul
nouveau cache possédé ; un échec d'unlink peut laisser un résidu orphelin local.
Absence de fichier visible en SQL ne garantit donc pas absence de tout cache.
Accusé de commit incertain : `document_adoption_commit_unknown`, cache
potentiellement publié conservé, aucun retry automatique. Les anciens caches
publiés sont conservés ; aucun ramasse-miettes automatique en M2. Aucun PUT,
MKCOL, MOVE ou DELETE distant, même pour rollback.

La projection commune fournit `document_relative_path`, l'origine externe si
prouvée et `document_remote_delete_available=false`. Le vieux DELETE par basename
refuse tout lien enrichi avec `folder_document_remote_delete_unavailable` ; une
erreur de lookup ne retombe pas sur un getter sans métadonnées. Ce garde ne
livre aucune capacité de mutation M5/M7. Les uploads historiques gardent leurs
sanitation, writer et compensation existants.

## Fraîcheur et UI

`read_workspace_document_source` est une frontière interne pour M4, sans route
ni consommateur prompt ajouté. Elle refuse localement tout ETag persisté absent
ou invalide avant configuration/transport, fait une observation conditionnelle
initiale puis la lecture encadrée, compare identité/taille/SHA-256 enregistrés,
extrait entièrement et revalide le scope local. Déplacé/disparu → refus sans
recherche globale. Une version nouvelle exige une adoption explicitement
renouvelée ; le vieux cache seul ne prouve jamais la fraîcheur documentaire.
La sélection du chat normal conserve son chemin de cache historique.

Une source réelle synthétique de 21 pages a été adoptée/lue entière puis admise
avec le garde [M0](frida-v1-document-workshop-m0-contract.md). L'estimation
partagée `token_utils.estimate_tokens` porte sur toute l'entrée envoyée : prompt,
dialogue, toutes les sources et métadonnées, instructions/schema canonical.
`E + 24 000 <= 400 000`, réserve unique incluant le raisonnement ; le fichier seul
ne décide pas l'admission. Un autre cas tient seul mais dépasse une fois le
payload composé : refus avant transport. Aucun compteur, paramètre, modèle ou
provider nouveau, aucun adaptateur M4. La limite de 20 pages porte sur la sortie.

Le navigateur réutilise le panneau M1, le même DOM bureau/téléphone et le menu
Fichier à deux choix. Navigation/adoption uniquement après clic explicite ;
inventaire commun rafraîchi par son propriétaire existant, sans nouveau cache.
Ni checkbox source ni cible ne sont choisies automatiquement. Une cible déjà
choisie est conservée seulement après relecture du contexte serveur. Génération,
scope et opération gardent les publications du contrôleur M2. Ces gardes seuls
ne coordonnaient pas les lecteurs historiques : P2-M2-01, reproduit après le
succès historique 536/536, corrige cet ordre de publication chez le propriétaire.
Une adoption en vol reste unique après sortie ; aucun POST rejoué. Les seuls
IDs de répertoires à réconcilier survivent aux sorties/changements de contexte
pendant la vie du contrôleur ; seule une lecture explicite courante effectivement
publiée les efface. Une lecture ignorée n’acquitte pas la réconciliation, même
si un lecteur concurrent plus récent a réussi.
Erreur/incertitude → motif fixe utile ; aucune adoption rejouée automatiquement.
Les nouvelles tentatives et réconciliations restent des actions explicites.

### Cohérence des publications Files — P2-M2-01

`chat_threads_sidebar.js` conserve l’unique inventaire Files partagé. Un token
opaque de requête par répertoire lie le résultat à son autorité de publication ;
`readWorkspaceFiles` vérifie à la fois ce token et le garde `isCurrent` avant
lecture/publication. Fichiers et statut sont écrits sans attente entre les deux,
pour le succès comme pour l’erreur. Un appel déjà sans autorité ne supersède pas
une lecture valide. Une lecture de B n’invalide pas celle de A.

Le global réserve les tokens de tous les répertoires avant ses lectures
séquentielles ; chaque résultat passe par la même fonction de publication. Les
setters qui reconstruisaient les Maps Files/Status après collecte sont retirés.
A déjà lu ne peut plus écraser un A plus récent lorsque B termine, ni être omis
d’une Map reconstruite. B supersédé avant son tour n’effectue aucun I/O.
Un epoch du refresh global refuse ses anciennes listes de répertoires et ses
étapes tardives. La sauvegarde des répertoires retire fichiers/statut/token des
IDs absents ; une réponse de l’ancienne existence ne ressuscite pas un ID supprimé,
même réintroduit ensuite. P2-M2-03 corrige ensuite la conversion des erreurs
de listing observables en faux inventaire vide, sans modifier cette coordination.

Contrat de retour de `refreshWorkspaceFiles` :

| Résultat | Effet et consommateur |
| --- | --- |
| Tableau, y compris `[]` | Publication effective `ok` ; un inventaire courant vide est accepté. |
| `null` | Répertoire absent/invalide, autorité perdue ou lecture supersédée ; aucun effet sur fichiers/statut. Une erreur périmée est également ignorée. |
| Rejet | Erreur courante : inventaire `[]`, statut `error` et raison prévue publiés, puis erreur transmise. Le global conserve son affichage d’erreur Files et continue ses autres lectures. |

Le raccord `refreshFiles` d’`app.js` transmet ce retour. Les lecteurs d’adoption
et de réconciliation M2 vérifient `null` après leur garde de contexte et avant de
supprimer le marqueur. Ils conservent alors l’invitation à actualiser et ne
présentent pas cette réponse ignorée comme « Inventaire actualisé » ou comme
collection réconciliée. La prochaine lecture explicite réussie résout le marqueur ;
aucun polling, retry, replay POST, verrou global, cache documentaire concurrent
ou nouvelle dépendance. Les lecteurs historiques upload/suppression/OCR rendent
le même cache partagé ; leurs annonces portent sur leur mutation confirmée,
sans promettre une réconciliation M2.

Cette coordination est locale au contrôleur frontend, sans garantie entre
onglets ni preuve de fraîcheur DAV ou serveur universelle. Elle porte sur les
Maps Files/Status ; le lot distinct P2-M2-02 ci-dessous étend ensuite la
coordination aux familles Exports/Images/Notes sans modifier Files.

## Portée des preuves

Les routes M1 historiques utilisent inventaires et store simulés ; leurs cinq
preuves PostgreSQL sont séparées. M2 prouve le transport HTTP réel en loopback
synthétique et le store/service sur PostgreSQL isolé. La composition Flask utilise
le bootstrap de test qui neutralise DB/settings/secrets : `_db_conn` des vrais
modules contexts/workspace_files/workspace_folders/adoption pointe vers la base
isolée et `_storage_root` vers un temporaire ; le résumé conversation est
substitué par une lecture SQL du test. Le serveur reçoit ces modules raccordés,
la factory `from_env` fournit le vrai lecteur en configuration synthétique, puis
`app.test_client()` exerce remote/adopt/files. Le navigateur exécute le vrai HTML/app
dans Chromium avec `fetch` simulé. Aucune de ces preuves n'est un parcours
production E2E, un canari Nextcloud ou une recette Safari/iPhone matérielle.
La première comparaison 528/528 reste historique : elle précédait les quatre
findings G-R1–G-R4 et ne les fermait pas. Après leur vague de correction, la
comparaison utile finale passe 536/536 sans skip, contre 435 en baseline ;
diagnostics hérités conservés. La contre-revue finale limitée au delta est
Approved, sans finding Critical/Important/Minor ouvert dans cette revue historique.
Le finding indépendant P2-M2-01 du 5 octobre a ensuite été reproduit : quatre
probes Chromium, deux contrôles verts et deux rouges, sans skip, un seul POST
d’adoption par cas. Capture de la réponse avant adoption, fichier absent et zéro
cible après publication ancienne ; aucune perte SQL revendiquée. Le correctif
passe 21 cas Node et dix cas navigateur nouveaux, puis la comparaison complète
**567/567 = 344 Python + 101 Node + 95 Chromium + 27 PostgreSQL isolé**, chaque
exit 0, zéro skip. La première comparaison Chromium 94/95 (garde chat dépendant
d’une temporisation de fixture) reste documentée ; reprise des mêmes modules en
série, sans changer fixture ni assertion. Les commandes exactes, durées, codes
de sortie, contre-audit et nettoyage figurent dans la
[correction P2-M2-01](../../todo-todo/product/frida-v1-document-workshop-todo.md#correction-indépendante-p2-m2-01--5-octobre-2026).

À la livraison P2-M2-01, deux findings frontend hérités restaient ouverts
**hors de ce correctif**, avant le lot P2-M2-03 décrit ci-dessous :
P2-M2-02, publications Exports/Images/Notes encore non coordonnées (probe causal
Exports, autres familles inspectées statiquement) ; P2-M2-03, erreur courante du
listing des répertoires convertie en liste vide puis succès. Deux probes isolés
reproduisent ces défauts sur les blobs initiaux `24233ce8` comme après correction,
deux rouges à chaque passe, exits 1, sans skip. Ces preuves supplémentaires sont
séparées des 567 cas de comparaison et ne justifient aucune extension du patch.
Aucun finding vivant n’est retiré par l’annonce de fermeture de P2-M2-01.


### Listing des répertoires — P2-M2-03

Une erreur de `GET /api/workspace-folders` ne constitue plus une liste vide.
La frontière locale exige l'enveloppe de la route existante (`ok:true`, `items`
tableau), les champs de projection `id` et `display_name` chaînes non blanches,
et aucune ligne perdue par normalisation. HTTP en erreur, rejet réseau, JSON
illisible, `ok:false`, enveloppe ou lignes invalides provoquent un échec ; le
parseur et les normalizers partagés sont inchangés.

Le global attend les deux listings avant toute sauvegarde : une erreur courante
retourne `false` et affiche le statut existant « Mode hors ligne. », sans écrire
répertoires, conversations, inventaires Files/Exports/Images/Notes ou leurs statuts,
ni sélection/conversation courante. L'appartenance inconnue ne devient pas une
suppression. Un garde local indique seulement si les répertoires ont été connus :
au premier échec, aucun libellé « Aucun répertoire » ni création automatique du
bootstrap ; aucune donnée inventée ni cache documentaire supplémentaire. Le dernier état
connu, même vide, reste le dernier état connu.

Un vrai `200 {ok:true,items:[]}` reste un succès : suppressions et invalidations
Files de P2-M2-01 sont appliquées. À la livraison P2-M2-03, les autres Maps
gardaient leur traitement global historique ; P2-M2-02 les coordonne ensuite. Les epochs refusent une ancienne erreur après succès et une ancienne
liste après suppression confirmée ; une erreur de listing ne supersède pas les
tokens individuels Files en vol. Les courses internes Exports/Images/Notes ne
sont pas coordonnées par ce correctif P2-M2-03 ; leur correction relève du lot
P2-M2-02 décrit ci-dessous.

`refreshThreadsFromServer` reste booléen : `true` pour son parcours réussi,
`false` pour échec courant ou lecture globale supersédée. Son traitement des
erreurs propres aux inventaires n'est pas changé. `syncAndRender`, déplacement
et bootstrap conservent le statut sans rejouer de mutation. Les rechargements
après chat ou suppression de conversation confirmés passent `preserveStatus`
à `loadThread` lorsque le refresh a retourné `false` ; leur réussite de lecture
de conversation n'efface plus cette panne de listing et leur mutation n'est
pas requalifiée en échec. Un rafraîchissement ultérieur réussi reprend
normalement, sans retry autonome, polling ou replay. Le contrat tableau/null/rejet
Files et la réconciliation explicite M2 demeurent inchangés.

Comparaison du lot : **594/594 = 344 Python + 124 Node + 99 Chromium + 27
PostgreSQL isolé**, les 567 historiques conservés plus 23 Node/4 Chromium,
41 sélecteurs inchangés, chaque exit 0, zéro skip.
Les nouveaux tests passent par le propriétaire et le vrai navigateur monté,
avec HTTP simulé ; les deux anciennes fixtures chat/documents actifs qui ne
simulaient pas ce listing ajoutent seulement sa réponse nominale vide valide.
Le cas chat temporisé conserve timers et assertions, ainsi que le résultat
historique 94/95 dans la provenance P2-M2-01. Résultats, sélecteurs, durées,
exits et contre-audit figurent dans la
[correction P2-M2-03](../../todo-todo/product/frida-v1-document-workshop-todo.md#correction-indépendante-p2-m2-03--5-octobre-2026).

**Limite serveur constatée à la livraison P2-M2-03.** P2-M2-04 restait
ouvert : le store convertissait une exception DB/sérialisation en `[]`, puis
service/route annonçaient `200 {ok:true,items:[]}`. Le probe historique isolé
(un rouge attendu) est conservé dans la roadmap ; il ne démontrait aucune panne
opérateur ou perte SQL/DAV. Le frontend ne pouvait distinguer ce payload d'un
vrai vide. La correction backend séparée P2-M2-04 ci-dessous ferme maintenant
ce contrat d'erreur ; aucun backend n'avait été absorbé dans P2-M2-03.
Migrations opérateur, livraison runtime et DAV live restent ouverts ; M3 non commencé.


### Publications Exports, Images générées et Notes — P2-M2-02

Les trois hypothèses sont confirmées séparément au parent `c057d286` par le
vrai propriétaire : ancien résultat A collecté, attente B, publication
individuelle récente de A, fin du global qui restaurait l'ancien A. Trois
contrôles où le global termine avant l'individuel restent verts. Les payloads
suivent les routes existantes : `exports`, `generated_images`, `items` pour
Notes. Trois preuves Chromium montées exercent les vrais boutons de création,
le POST simulé unique et le rendu final ; aucune preuve Images/Notes n'est
inférée de la seule inspection Exports. Résultats et commandes sont dans la
[correction P2-M2-02](../../todo-todo/product/frida-v1-document-workshop-todo.md#correction-indépendante-p2-m2-02--5-octobre-2026).

Chaque famille conserve ses Maps de données/statut chez `chat_threads_sidebar`.
Un token opaque par famille ET répertoire coordonne le lecteur individuel et
le global. Chacun des trois `readWorkspace…` est l'unique publication de sa
famille : autorité vérifiée avant I/O, après réponse et avant erreur ; données
et statut écrits ensemble, sans attente. A et B sont indépendants, comme Files,
Exports, Images et Notes entre eux. Les six setters qui reconstruisaient les
Maps après collecte sont retirés ; aucun résultat ignoré n'omet indirectement
une publication récente. Une ancienne réussite ne masque pas une erreur récente,
et une erreur ancienne ne vide pas un inventaire récent.

Le global capture son epoch à l'entrée. Après succès des deux listings et
validation de cet epoch, il sauvegarde l'appartenance connue puis réserve,
sans attente, les tokens de TOUS les répertoires et des QUATRE familles avant
la première lecture Files. Il conserve ces tokens dans chaque phase ultérieure,
sans réacquisition après attente Files/Exports/Images ou d'un autre répertoire.
Une phase supersédée ne lance pas son I/O. Un global supersédé s'arrête et
retourne `false` ; une phase déjà publiée avant la supersession reste publiée
jusqu'à un remplacement valide ou une suppression confirmée. L'autorité de
l'inventaire global est donc acquise après le listing validé, pas avant sa
réponse ni à l'entrée d'une phase différée. Cela coordonne les publications
locales ; aucun token ne prouve la version effective des données serveur.

`saveWorkspaceFolders` retire données, statut ET tokens de toutes les familles
pour les seuls IDs confirmés absents. Une ancienne lecture ne peut ressusciter
le répertoire ni son statut, même si le même ID réapparaît. Une erreur du listing
protégée par P2-M2-03 ne sauvegarde aucune appartenance, ne réserve aucun token
et ne supersède pas une lecture individuelle légitime en vol.

Les trois lecteurs individuels utilisent le même retour que Files : tableau
(y compris `[]`) pour une publication effective ; `null` pour absence, autorité
invalide, supersession ou erreur périmée ; rejet après publication `[]`/`error`
pour une erreur courante. Un répertoire connu non lié publie `[]` et
`not_applicable`, avec sa raison historique, sans HTTP. Le garde optionnel de
contexte est vérifié avant réservation et avant publication. Vrai vide, erreur
courante et reprise explicite conservent leur sens ; aucun retry ou polling.

Les panneaux Exports (création/réutilisation), Images (création/suppression) et
Notes (création) vérifient le tableau de retour. Après mutation confirmée, un
rechargement ignoré/échoué conserve la confirmation et affiche sur le statut
existant « Inventaire non actualisé. », avec rendu du cache/statut courant.
Il n'annonce ni publication effective ni échec de la mutation, et ne rejoue
aucun POST/DELETE. La note explicitement créée reste sélectionnée. Les erreurs
de mutation gardent leur traitement antérieur ; ouvrir/télécharger/préparer
une note ne changent pas. Le global garde son booléen de parcours historique,
avec les erreurs courantes propres aux familles dans leurs statuts ; `true`
ne promet pas que tous les inventaires sont `ok`.

La coordination Files P2-M2-01, sa réconciliation M2 explicite, le listing
P2-M2-03, le chat, l'upload, les sélections/brouillons et le DOM des thèmes sont
préservés. Aucun second cache, verrou d'interface, sérialisation générale,
normalizer partagé, backend ou capacité produit ajouté. Cohérence locale au
contrôleur seulement : onglets, runtime livré, versions serveur et DAV live
restent hors preuve. À cette livraison, P2-M2-04 restait ouvert et hors lot, avec
son rouge historique séparé ; il est corrigé ensuite ci-dessous. M3–M10/Z restent
non commencés.

Comparaison dédiée finale : **679/679 = 344 Python + 206 Node + 102 Chromium +
27 PostgreSQL isolé**, les 594 historiques conservés plus 82 Node et trois
Chromium nouveaux, exits 0 sans skip. Baseline frontend 124/99 verte ; six
contrôles/rouges Node donnent trois verts et trois rouges, puis trois rouges
montés propres aux familles. Les échecs de harnais et corrections causales,
durées, sélecteurs exacts, contre-audit et nettoyage restent dans la roadmap.

### Lecture backend des répertoires — P2-M2-04

Le finding est confirmé au parent `0a5b4b55` dans Flask : vraie route/service/
wrapper/store, seule connexion DB remplacée. Lecture vide valide et connexion
en erreur produisaient le même HTTP 200, `ok:true,items:[]` et observation de
succès. Le contrôle vide passait, l'assertion de refus échouait. Les historiques
536/567/594/679 et le rouge initial P2-M2-04 conservent leur provenance.

`workspace_folders_store.list_workspace_folders` renvoie une liste complètement
lue/sérialisée ou lève `WorkspaceFolderListError`, raison stable
`workspace_folder_list_failed`. Connexion, exécution/fetch SQL et exception après
une ligne valide ne deviennent ni liste vide ni inventaire partiel. Le warning
privé existant est conservé sans collecte nouvelle ; la cause reste interne.
Tri, `include_deleted`, projections et icônes ne changent pas. Les getters
indépendants et leurs fallbacks restent hors lot.

Le service renvoie `(payload,status)` et le registrar transmet ce statut :
HTTP **503**, JSON `ok:false`, raison stable et message fixe « lecture des
repertoires indisponible ». Aucun `items`, compteur de répertoires inventé, détail
SQL/DSN ou exception brute dans la réponse. L'observation existante indique
`error/5xx` et la même raison, jamais `workspace_folder_list_ok`. Le 503 suit la
convention de lecture de stockage indisponible ; aucun retry implicite. Un vrai
vide conserve HTTP 200, `ok:true,items:[]`, icônes et observation nominale.

La validation de nom du wrapper propage l'exception ; create/patch du service et
les lectures initiales Nextcloud-first refusent avant écriture SQL/DAV. Les
relectures de nom dans create/update du store conservent leur retour de mutation
`None` : après une mutation distante déjà engagée, les branches existantes de
persistance partielle et compensation s'exécutent sans replay. MKCOL n'acquiert
pas une autorité nouvelle de suppression ; rollback MOVE réussi ou échoué garde
son résultat explicite et son statut 500 de persistance partielle.

La réconciliation signale l'échec d'inventaire initial ou final par `ok:false`,
raison stable et record existant `failed`/`partial`. `counts_before`,
`counts_after` ou exemples inconnus valent `None` ; les actions déjà réalisées
restent dans les records. Les sous-répertoires standards refusent l'échec initial,
avec `folder_counts:None`, sans faux `not_applicable` ; leur synthèse nominale
reste fondée sur le snapshot initial, sans nouvelle relecture. Le consommateur
Documents dynamique conserve sa frontière d'erreur existante
`folder_document_existing_inventory_failed`, avant DAV ; son test est renforcé
avec le vrai wrapper/store. Tous les appelants recensés sont décrits dans la
[correction P2-M2-04](../../todo-todo/product/frida-v1-document-workshop-todo.md#correction-indépendante-p2-m2-04--5-octobre-2026).

Le frontend P2-M2-03 reste inchangé. Une fixture capturée du vrai Flask/store est
comparée aux réponses réelles par le test Python puis utilisée par Chromium :
erreur backend refusée, répertoires et quatre inventaires/statuts/sélection/
contexte/brouillon conservés ; vrai vide accepté et invalidations légitimes ;
reprise explicite et un seul POST d'adoption. Pas de preuve HTTP bout en bout
navigateur→Flask, pas de DAV live. PostgreSQL dédié exerce aussi un vrai
`UndefinedColumn`, sa projection HTTP 503 et la reprise explicite, sans DB
opérateur ni mutation de plateforme.

Comparaison finale : **713/713 = 374 Python + 206 Node + 104 Chromium + 29
PostgreSQL isolé**, les 679 historiques conservés, 22 nouveaux cas et 12 cas du
voisin renommage, 43 sélecteurs (41 historiques + deux modules Python), exits 0
sans skip. Chromium reste en `--test-concurrency=1`, modules SQL en série.
Résultats intermédiaires, commandes, durées et nettoyage figurent dans la roadmap.

**À la livraison P2-M2-04, P2-M2-05 restait ouvert hors lot**, signalé seulement
sur inspection du parent et du delta :
une liste finale réellement vide peut conserver des exemples présents issus du
snapshot initial (`after or before`), malgré `counts_after.active=0`. Aucune
reproduction dynamique exécutée, aucune correction absorbée. Les erreurs de
lecture de ce lot sont explicitement inconnues et ne passent pas par ce fallback.
Migrations opérateur, livraison runtime/health et DAV live restent ouverts ;
M3–M10/Z non commencés. Arrêt après commit/push vérifié, aucun déploiement.

### Cohérence des exemples de réconciliation — P2-M2-05

Le finding hérité est confirmé dynamiquement au parent `6b891eb3` par la vraie
entrée de réconciliation et le vrai store : l'inventaire initial contient
un exemple synthétique lié, puis une observation distante simulée vide les
lignes de la relecture finale. `counts_after.active=0` et exemples du record final absents,
mais l'ancien résumé conservait `present_reconciled`. Le contrôle où le dossier
reste présent est vert. Cette restitution incohérente ne prouve aucune perte
SQL/DAV ni panne opérateur. Le constat seulement statique à la livraison
P2-M2-04 garde sa provenance historique ci-dessus.

`_summary` utilise désormais exclusivement `_example_status(after)` quand
`after is not None`. Une liste finale valide `[]` exprime l'absence des exemples ;
un état final non vide différent reflète ses propres catégories et statuts.
Une lecture finale échouée garde `examples:None`, compteurs finaux inconnus,
verdicts et raison de P2-M2-04. Compteurs initiaux, records historiques, record
final et calcul de `ok` ne changent pas. Aucun I/O, action de réconciliation,
création, compensation ou reprise ajouté, aucun frontend modifié.

Trois nouveaux cas Python verrouillent causal vide, contrôle présent et état
final différent. Le vide initial historique est renforcé avec le vrai store ;
les deux gardes existantes de lecture finale échouée sont réutilisées. Assertions
résumé/record final et historique initial, deux SELECT et cinq observations
DAV simulées sans mutation pour le scénario causal ; un SELECT et zéro DAV
pour le vide initial. Pas de mock du résumé ni de nouvelle abstraction produit.

Comparaison **716/716 = 377 Python + 206 Node + 104 Chromium + 29 PostgreSQL
isolé**, zéro skip, 43 sélecteurs inchangés : 713 historiques conservés (dont
12 cas préexistants du voisin renommage), trois cas Python ajoutés. Avant patch,
contrôle vert et rouge causal ; après patch, six cas ciblés et 103 voisins verts.
Commandes exactes, durées, résultats et nettoyage dans la
[correction P2-M2-05](../../todo-todo/product/frida-v1-document-workshop-todo.md#correction-indépendante-p2-m2-05--5-octobre-2026).

P2-M2-05 est fermé sur code/preuves ; aucun finding indépendant ajouté au lot.
Les DB/DAV du ciblé sont synthétiques, PostgreSQL de comparaison est réel et
isolé, Chromium à transport simulé. Runtime opérateur et DAV live ne sont pas
prouvés. Migrations opérateur, livraison runtime/health et DAV live restent
ouverts ; M3–M10/Z non commencés. Arrêt après livraison Git vérifiée, aucun déploiement.
