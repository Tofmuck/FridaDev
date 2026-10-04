# Atelier documentaire Frida V1 — contrat M2

Date : 2026-10-04. Statut : code et 536 preuves fermés, contre-revue finale du delta
Approved ; livraison runtime ouverte. Le retour final porte la livraison Git dédiée.
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
scope et opération gardent aussi la publication tardive dans le cache partagé.
Une adoption en vol reste unique après sortie ; aucun POST rejoué. Les seuls
IDs de répertoires à réconcilier survivent aux sorties/changements de contexte
pendant la vie du contrôleur ; une lecture explicite courante réussie les efface.
Erreur/incertitude → motif fixe utile ; aucune adoption rejouée automatiquement.
Les nouvelles tentatives et réconciliations restent des actions explicites.

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
Approved, sans finding Critical/Important/Minor ouvert ; commandes, dispositions
et limites figurent dans la roadmap.
