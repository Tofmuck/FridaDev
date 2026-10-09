# Atelier documentaire — contrat Writer M8-C v1

Date : 7 octobre 2026. Base M7 exacte : `750180fa8595b53c7e188017c9c62be1ae9943fc`,
parent M6 `b00eb95001755295dcc301232272a8070d26cd78`. Branche
`FridaV1-Document-Workshop-M8-C`, créée avant édition. Autorité : mandat M8-C de
Tof et [roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md),
§§3.9–3.17, M8-C et section 9. Ce document est la remise commune à Sauron.
Statut courant : P2-M8C-AUD-01 corrigé sur la structure DOCX ;
**P2-M8C-AUD-02 corrigé sur la décision temporelle finale ; clôture globale M8-C à contre-auditer**.
Le relevé initial ci-dessous conserve ses résultats historiques ; le
[relevé dédié AUD-01](../baselines/document-workshop/frida-v1-document-workshop-p2-m8c-aud-01-20261007.json)
porte ses exécutions historiques et sa portée. Le
[relevé AUD-02 du 9 octobre](../baselines/document-workshop/frida-v1-document-workshop-p2-m8c-aud-02-20261009.json)
porte la correction temporelle et la comparaison actuelle, distinctes des
déclarations historiques et du contre-audit indépendant du 7 octobre.
Aucun service Writer ni transport AF_UNIX n'est livré. DOCX/PDF restent inactifs.

## Plan et frontières

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » La convergence de la frontière synthétique M5 vers un seul contrat
fermé évite deux validateurs concurrents. Aucun changement de canonical produit,
Exports, migration, route publique, UI ou moteur. Les choix ordinaires sont
couverts par le mandat ; aucune nouvelle approbation intermédiaire n'est requise.

1. Rejouer les 1 604 IDs M7, collecter leurs identités et séparer les 70 voisins.
2. Établir les rouges de protocole/source/paire et de lifecycle simulé.
3. Livrer contrat et framing, inspections bornées, validation et snapshots.
4. Remplacer M5, éprouver confirmation et fencing sur PostgreSQL isolé ; conserver
   le refus produit même après validation interne et libération acquittée.
5. Livrer schémas et vecteurs autonomes, comparer les mêmes IDs avec les nouveaux,
   faire la contre-lecture indépendante, conserver les preuves puis nettoyer.
6. Commit/push dédiés et vérification des références ; arrêt avant M8-S/M8-A.

| Responsabilité | Frontière |
| --- | --- |
| Canonical/volume | M0 `document_canonical`, sérialisation déterministe M4/M5 |
| Protocole/identité/framing/snapshots | `document_renderer_contract` |
| Type réel/archives/pages PDF | `document_renderer_artifacts`, primitives readers existantes |
| Ordre/temps/récupération/libération | `document_rendering`, interface injectable |
| Confirmation/claim/scope/révision | M3/M5 `document_workshop_execution_store` |
| Worker fake/corpus | `tests/support`, exclusivement synthétiques |
| HTTP AF_UNIX réel | M8-A ; aucun socket de production consommé en M8-C |
| Image/wrapper/UNO/layout/confinement | Sauron M8-S dans sa racine |

## Invariants et unités

Profil `frida_document_v1` inchangé : A4 210 × 297 mm, corps 12 pt, interligne
1,5, marges 25 mm ; canonical M0 complet, 10 000 mots/75 000 points de code
Unicode, 20 pages Writer finales. Aucun style réduit pour tenir, image, contenu
actif, format supplémentaire ou troncature. Markdown sérialisé directement.

Toutes les tailles suivantes sont des **octets**, framing inclus dans les totaux :

| Objet | Maximum inclusif |
| --- | ---: |
| JSON UTF-8 de chaque enveloppe, canonical inclus | 1 048 576 |
| Source unique | 41 943 040 |
| Corps complet de requête multipart | 44 040 192 |
| Chaque artefact DOCX/PDF | 16 777 216 |
| Corps complet de résultat multipart | 34 603 008 |
| Expansion ZIP/XML cumulée par archive | 67 108 864 |
| Entrées d'archive | 4 096 |
| Tâches occupant un espace worker | 1 |
| File d'attente | 0 |

Pas de base64 : source et artefacts sont des parties binaires exactes. Le plafond
JSON comprend les deux canonical si une source Frida doit être liée. Un document
admissible en volume peut être refusé par une borne structurelle/technique ;
aucune réduction implicite. Le plafond d'expansion porte sur tous les membres,
y compris XML/métadonnées, avec comptage des octets effectivement décompressés,
CRC et refus des noms dupliqués, traversal, symlinks, chiffrement et DTD/entities.

À appliquer et prouver par M8-S : 1 vCPU, mémoire 1 073 741 824 octets, tmpfs
268 435 456 octets, processus/descripteurs 64/256, utilisateur non privilégié,
rootfs read-only, network none, socket dédié autorisé seulement aux deux comptes.
Ni image, nom de service, socket, UID/GID, pins Writer/UNO ni polices réelles
ne sont inventés dans M8-C. Les valeurs `synthetic-*` du corpus sont des fixtures.

## Encodage fermé v1

JSON UTF-8 strict, sans BOM, NaN/Infinity, clé répétée ni champ inconnu à aucun
niveau. Types stricts : booléen n'est jamais entier ; flottant n'est jamais
compte. Champs obligatoires même quand leur valeur est `null`. UUID techniques
minuscules en forme canonique, SHA-256 hexadécimal minuscule de 64 caractères.
Sérialisation de hash : `json.dumps(..., ensure_ascii=False, sort_keys=True,
separators=(',', ':'), allow_nan=False).encode('utf-8')`, sans normalisation
Unicode. Même sérialisation du canonical M4/M5, reprenant la validation M0.
Hash canonical recalculé avant gel ; jamais modifié pour satisfaire un résultat.
Hash de requête : SHA-256 de toute l'enveloppe déterministe **sans** son champ
`request_sha256`. Inclut job/révision/format/profil/pin attendu/canonical/source
complète et leurs tailles/empreintes. Aucun timestamp/chemin privé n'y entre.

Le corps requête/résultat est `multipart/form-data; boundary=<token>` ; token
ASCII `[A-Za-z0-9_-]{8,64}`. Chaque partie utilise exactement, dans cet ordre :

```text
--<boundary>\r\n
Content-Disposition: form-data; name="<technical-name>"\r\n
Content-Type: <exact-media-type>\r\n
Content-Length: <decimal-octets>\r\n
\r\n
<exactly Content-Length octets>\r\n
```

La dernière partie est suivie de `--<boundary>--\r\n`, puis EOF exact.
Pas de préambule/épilogue, filename, header supplémentaire, doublon, transfert
encodé, partie hors manifeste, séparateur tronqué ou Content-Length discordant.
Le décodeur utilise les longueurs ; un encodeur doit éviter toute collision de
boundary dans les parties. `request` JSON puis éventuellement `source` MIME exact.
Résultat `manifest` JSON puis `docx` puis `pdf` pour ready ; pour un terminal
négatif, seulement `manifest`. Tous les totaux incluent headers et délimiteurs.
Le futur transport HTTP/1.1 impose Content-Length total exact, pas de chunking,
compression, redirects/retry ; fin prématurée, body supplémentaire ou statut
inattendu échouent fermés. M8-C simule ces messages ; M8-A prouvera le transport.

## Requête, source et attentes indépendantes

`render_request_v1` contient schema/version, job_id, revision_id, canonical_sha256,
request_sha256, profile, format confirmé docx/pdf, expected_engine_sha256,
canonical validé et source nullable. Le job suit le turn-id de confirmation M3.
Le format protocolaire n'active jamais le format produit.

Une source comporte kind docx/pdf, origin frida/external, byte_size, sha256,
source_revision_id, canonical et canonical_sha256. Externe : DOCX seulement,
les trois derniers champs `null`. Frida : les trois obligatoires non nuls,
canonical source validé avec son hash recalculé. Ce canonical peut différer du
candidat : une nouvelle révision ne se fait pas passer pour la précédente.
Si source_revision_id = revision_id, les deux hash canonical doivent être
identiques ; même UUID avec deux canonical différents est refusé.
Les octets source doivent correspondre à la longueur/hash. PDF externe, sources
multiples, import ODT/format arbitraire : refus. PDF Frida est uniquement contrôle
de correspondance ; aucun import éditable Writer/Draw.

La provenance Frida n'est pas créée par une déclaration du worker : l'appelant
M9/M10 doit établir **avant construction de la requête** la correspondance du
reçu/manifeste durable source avec révision/canonical/octets fraîchement lus.
L'enveloppe transporte ces preuves déjà établies ; un hash ne démontre pas
à lui seul que le texte d'un binaire correspond au canonical. M8-C ne livre
aucun consommateur produit de ces modes source. Les fixtures les simulent.

Seules données documentaires admissibles et IDs techniques : aucun nom privé,
chemin hôte/DAV, URL de téléchargement, secret, commande, template externe,
filtre libre ou instruction UNO. Le texte reste du texte ; les liens http/https
admis par M0 restent passifs, conservés, sans fetch autorisé.
DOCX externe : inspection bornée de l'ensemble du package et de ses XML,
puis inspection UNO sans réparation par le futur service,
inventaire complet et représentabilité/losslessness attestés. Champs dynamiques,
macros, révisions suivies, sections/styles complexes, objets/images ou contenu
non représentable sont refusés sans suppression. M9-B annoncera la remise en
forme V1 et ses limites avant clic. Aucune fidélité arbitraire promise ; ODT
éventuel strictement temporaire, détruit avec le job.

`engine` comporte renderer_version, image_id/digest OCI, writer_version,
uno_version, profile, locale, filtres exacts `Office Open XML Text` et
`writer_pdf_Export`, quatre rôles de police regular/bold/italic/bold_italic,
file_id technique, sha256 et license_id pour chacun. M8-S fournit les valeurs
réelles/fichiers/notices/glyphes. Frida compare à un snapshot explicitement
fourni par l'appelant ; capabilities et résultats non vérifiés ne choisissent
jamais leurs propres attentes. `expected_engine_sha256` lie cette attente à
la requête entière. Aucun pin Stirling n'est réutilisé.

## Paire, pagination et validation

`render_result_v1` lie job/révision/canonical/hash de requête/source, engine,
status/reason_code, artifacts et page_evidence/source_evidence.
Ready exige les deux artefacts complets, MIME fermé, longueur/SHA recalculés
sur les octets reçus, inspection du package DOCX et PDF analysable entier. Archives
inspectées sans extraction vers filesystem. PDF chiffré/actif/partiel refusé,
actions des signets incluses ; liens passifs et destinations locales conservés.
Inspection binaire dans un sous-processus fixe, sans shell/réseau : mémoire
512 MiB, CPU 20 secondes, graphe PDF limité à 65 536 conteneurs atteignables.
Ces gardes d'inspection applicative ne sont pas les ressources du futur Writer.

### Squelette DOCX — correctif P2-M8C-AUD-01

La garde renderer de `word/document.xml` compare les **noms qualifiés**,
indépendamment des préfixes : racine WordprocessingML `document`, puis
`background` facultatif et `body` facultatif, chacun au plus une fois, dans cet
ordre. Ces trois éléments n'apparaissent pas ailleurs dans cette partie.
`background` admet zéro ou un enfant VML `background` ; celui-ci est un autre
nom qualifié. Racine/background/body sont à contenu élément-seul : seul le
blanc XML U+0020/U+0009/U+000D/U+000A est admis entre leurs enfants.

Les enfants directs du body appartiennent aux noms CT_Body du modèle SDK :
blocs `p`, `tbl`, `customXml`, métadonnées proofErr/permissions/bookmarks/comment
ranges et marqueurs de révision, y compris les noms `w14` déclarés par ce
modèle. `sectPr` direct est facultatif, unique et terminal. Un `sectPr` de
paragraphe sous `pPr` reste admis. Les gardes de profil existantes continuent
de refuser, entre autres, altChunk, sdt, champs dynamiques et révisions suivies,
même lorsqu'un nom figure dans CT_Body. L'allowlist structurelle ne donne
aucune permission supplémentaire au profil V1.

Provenance vérifiée le 7 octobre 2026 : modèle primaire
[Open XML SDK, schéma WordprocessingML](https://github.com/dotnet/Open-XML-SDK/blob/431ab05cf160248cc3885a4a766026d4f8243792/data/schemas/schemas_openxmlformats_org_wordprocessingml_2006_main.json),
commit `431ab05cf160248cc3885a4a766026d4f8243792`, SHA-256 du fichier
`b29e60a07afc3e0a4695eecca6c2a7a35070eb81f53a2f11033c6df6f946212b`.
Types `w:CT_Document/w:document` (index 487), `w:CT_Background/w:background`
(645), `w:CT_Body/w:body` (654) : séquences/choix et occurrences ; body 0..1,
pas exactement un. Voir aussi la
[classe Document Microsoft](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.document?view=openxml-3.0.1).

Document vide, body vide et background seul sont acceptés **structurellement**.
Cela n'établit aucune correspondance au canonical ni fidélité du rendu.
Préfixes équivalents, namespaces/attributs supplémentaires et métadonnées
admissibles ne sont pas bannis globalement. Les intérieurs de paragraphe,
tableau, sectPr ou VML, les attributs et toutes les particules imbriquées ne
sont pas validés comme par un XSD universel. Le correctif ne livre ni moteur
de compatibilité XML, ni réparation de document, ni preuve Writer.

Même garde pour l'artefact reçu et l'admission source DOCX Frida/externe ;
lecteur partagé M2 inchangé. Refus dans le vocabulaire existant
`renderer_source_unsupported`, traduit en `document_render_invalid` au raccord
applicatif. Aucun changement de protocole/version, profil, budgets, horloge
ou libération. Les
[fixtures adverses et positives](../../../tests/support/document_renderer_structure_fixtures.py)
et [sondes de structure](../../../tests/unit/core/test_document_renderer_structure.py)
reproduisent les ZIP et manifestes cohérents, avec les vrais inspecteurs en
sous-processus. Aucun XML n'est réparé et aucun canonical n'est réécrit.

Le manifeste exige la séquence : docx_saved → docx_reloaded → layout_stable →
writer_pages_measured → pdf_exported → pdf_pages_measured. Le DOCX enregistré
est rechargé dans le même moteur/profil, layout stabilisé, pages relevées, puis
PDF exporté depuis ce même état. `page_evidence.method=writer_reload_layout_v1`
lie révision/hash canonical et SHA des deux artefacts à writer_pages/pdf_pages.
Les deux métadonnées artefacts portent writer_pages ; PDF porte aussi pdf_pages.
Tous sont entiers stricts 1..20, concordants avec le compteur réel du PDF final.
Un nombre docProps, sauts/blocs ou PDF seul ne constitue pas une preuve DOCX.
M8-C vérifie les **liens et assertions contractuels**, pas l'exécution Writer :
pagination/layout/glyphes/fidélité restent à prouver avec M8-S/M9/M10.

## États, HTTP, progression et espace worker

Interfaces du futur renderer privé, aucune route Flask ajoutée :

| Appel | Succès | Refus/erreur fermé |
| --- | --- | --- |
| GET /v1/capabilities | 200 render_capabilities_v1 | 503 indisponible, aucun document ouvert |
| POST /v1/jobs | 202 rendering ; 200 job identique existant | 409 conflit, 503 busy ; 422 entrée/source/profil refusé |
| GET /v1/jobs/{id} | 200 render_status_v1 | 409 identité incompatible ; 404/410 job perdu |
| GET /v1/jobs/{id}/result | 200 terminal multipart | 409 rendering ou identité incompatible ; 404/410 perdu |
| DELETE /v1/jobs/{id} | 200 render_release_v1 | 409 identité incompatible ; 503 cleanup failed ; 404/410 lost |

États worker fermés : rendering/ready/refused/failed/cancelled. `lost` est une
qualification Frida pour absence/perte, jamais succès. Codes : renderer_ready,
renderer_busy, renderer_input_invalid, renderer_source_unsupported,
renderer_profile_mismatch, renderer_page_limit, renderer_incomplete,
renderer_inactivity, renderer_resource_limit, renderer_cancelled,
renderer_job_conflict, renderer_job_lost, renderer_cleanup_failed. État
inconnu = renderer_job_lost (`lost` côté Frida) ; code inconnu = renderer_incomplete, aucun texte d'exception transmis.
Refus POST 422 : entrée/source/profil/pages refusés. Erreur de framing/JSON sans
identité fiable : HTTP 400 ; dépassement de corps : HTTP 413. Corps vide pour
400/413, capabilities indisponible 503 et job absent/détruit 404/410. Aucun texte
diagnostic privé. GET conflit renvoie un render_status_v1 refused/job_conflict ;
GET result encore rendering renvoie render_status_v1 (pas un faux résultat).

Pour les GET job/result et DELETE, l'adaptateur M8-A transmettra le header
`X-Frida-Request-SHA256`, exactement 64 hex minuscules ; le wrapper doit comparer
ce hash au job **avant** lecture ou destruction. POST lie le hash dans l'enveloppe.
DELETE reçoit render_delete_v1 JSON avec intent cancel/release et même job/hash.
Pas de paramètres de requête, chemin documentaire ou téléchargement par URL.

Terminal négatif : artifacts vide et page_evidence/source_evidence null.

Idempotence pendant la vie worker : même job/requête figée retrouve l'état et
le résultat, une seule exécution ; autre requête sous même job = conflit. Un
job ready occupe encore l'espace jusqu'à libération ; zéro queue. Après
libération un tombstone technique interdit la réexécution pendant cette vie.
Redémarrage/perte = lost, pas de retry ou nouvel ID automatique. Le claim et
journal Frida restent l'autorité durable ; aucune garantie exactly-once distribuée.

Progression vérifiable : source_inspected puis chaque bloc canonical appliqué,
puis étapes finies save/reload/layout/mesure/export/mesure PDF. units_total =
N blocs + 7, units_completed dérivé de phase et blocks_completed. Valeurs
monotones, compte strict borné, ready seulement à totalité. L'appelant mesure
120 secondes d'inactivité avec horloge monotone locale, depuis submit ; seuls
nouveaux blocs/étapes réarment. Poll/keepalive/CPU/lease ne le font pas. Aucun
plafond mural tant que du progrès utile arrive avant chaque échéance ; à 120
exact l'opération échoue. M8-S prouvera un superviseur indépendant d'UNO bloqué.

Correctif **P2-M8C-AUD-02**, 9 octobre 2026 : cette même horloge reste
l'autorité jusqu'à la décision finale de succès, après validation stricte de
l'acquittement et recontrôle d'autorité, avant création/mémorisation de
`ReleasedRender`. Result, validation, libération et acquittement ne réarment
pas le dernier progrès utile. À 120 s exactes ou au-delà, `renderer_inactivity`
refuse le bundle ; `collected` peut conserver le snapshot validé sans prouver
un succès. Aucune seconde annulation/libération après la tentative de libération,
même si le refus applicatif est tardif : il ne révoque pas le nettoyage acquitté.
Une répétition de la session refusée donne `renderer_job_lost` sans nouvel
échange, rendu ni mutation. Autorité/lease/inactivité restent distinctes ;
aucune interruption d'appel réellement bloqué n'est ajoutée (M8-S/M8-A).

Dérivation exacte des compteurs (N = nombre de blocs top-level canonical) :
accepted : 0/blocks 0 ; source_inspected : 1/blocks 0, même sans source ;
canonical_applied : 1+B/blocks B, 0 ≤ B ≤ N ; puis blocks=N et
units_completed=N+2, N+3, N+4, N+5, N+6, N+7 respectivement pour
save/reload/layout/mesure Writer/export PDF/mesure PDF. Une phase régressant
avec le même compteur est aussi refusée. Les compteurs sont contractuels :
M8-S doit prouver qu'ils correspondent au travail réellement achevé.

Artefacts prêts ≠ nettoyage acquitté. Frida collecte **tout**, valide, garde un
snapshot local des octets/manifeste avant DELETE. DELETE distingue abandon
(annulation/destruction) et libération après collecte dans son body fermé.
L'acquittement lie job/hash requête, state released/cancelled/failed/lost,
reason_code et workspace_removed. Seuls released/renderer_ready/true après
collecte, sous HTTP 200 strict, permettent de rendre le bundle interne.
HTTP 409 exige failed/renderer_job_conflict/false et préserve le job légitime ;
HTTP 503 exige failed/renderer_cleanup_failed/false. Aucun HTTP d'erreur portant
un body released/cancelled ne devient un acquittement positif. Pas de cleanup_complete dans
le résultat. Échec/annulation tente DELETE une fois, sans masquer l'erreur
initiale ; une réponse submit perdue/corrompue après envoi conduit aussi à une
tentative d'abandon liée au hash. Un refus explicite validé 409/422/503 ne détruit
aucun job. Pas de retry submit ; lost ne prouve aucun nettoyage. M8-S doit kill le groupe processus,
dispose UNO et nettoyer après crash/OOM/reprise ; M8-A prouvera les acquittements
et la conservation locale effective sous transport. Reaper futur borné sur
jobs effectivement soumis ; jamais TTL d'un pending sans job.

## Raccord applicatif et livraison future

Ordre : confirmation exacte → claim actif → snapshot → submit simulé → status →
result → validate_result → octets/manifeste locaux figés → DELETE acquitté →
recontrôle autorité → frontière format produit. Gardes SQL scope/lease/owner/
génération/révision avant et après chaque échange/attente et avant tout effet.
Aucune transaction SQL tenue pendant le renderer ; il ne reçoit ni DB ni DAV.
Résultat tardif ne restaure jamais une autorité. Invalidité/perte/nettoyage non
acquitté : zéro PUT/MKCOL/reçu de succès. Même paire valide : format binaire
produit refusé. Markdown create/copy/update, conflits, journal, identité stable,
réconciliation sans replay, reçus/inventaire/continuité gardent les chemins M5–M7.

M8-S nécessite un GO Sauron distinct, pins réels et corpus conforme, réseau et
chargements externes réellement bloqués, layout/font/filtres/cancel/kill/cleanup
prouvés. M8-A livrera AF_UNIX/configuration/raccord au service seulement après
M8-S. M9-A/M9-B et M10 activeront leurs formats sous autorisations séparées.
Rebuild futur du seul code applicatif à documenter après ces GO ; aucun rebuild,
restart, installation, migration opérateur, Writer live, provider ou Nextcloud
opérateur n'est exécuté en M8-C.

## Schémas et corpus autonomes remis à Sauron

Les [six schémas Draft 2020-12](../../../tests/fixtures/document_renderer_v1/render_request_v1.schema.json)
et [32 vecteurs synthétiques](../../../tests/fixtures/document_renderer_v1/vectors.json)
sont versionnés dans `app/tests/fixtures/document_renderer_v1`. Fichiers :
render_request_v1, render_result_v1, render_capabilities_v1, render_status_v1,
render_delete_v1 et render_release_v1, chacun avec `.schema.json`. `$id` utilise
`urn:frida:writer:<schema>` ; `$defs` contient canonical/source/engine/pages.
Chaque champ de properties est obligatoire ; aucune extension implicite.
`null` est admis uniquement par les branches nullable explicites. Ready exige
artifacts docx/pdf et page_evidence ; échec exige artifacts `{}` et preuves null.
Avec source, ready exige source_evidence complet correspondant à son origine.

Les schémas structurels s'accompagnent des validateurs exécutables : JSON strict
avant validation (clés répétées, entiers lexicaux stricts), validation M0 du
canonical et des liens, volume Unicode, hash croisés, parties/octets/types réels,
concordance source/révision, pins indépendants, progression et lifecycle. Un
validateur JSON Schema seul ne suffit pas, notamment pour distinguer `1.0` de `1`.
Le générateur structurel est `tests/support/document_renderer_schema.py` ; le
corpus statique reste utilisable sans serveur Frida, SQL ni secrets.

```bash
PYTHONPATH=app python -m tests.support.document_renderer_conformance
```

Ce runner exige seulement Python et le reader pypdf déjà présent dans le runner
de preuve. Aucun import Flask, DB ou configuration opérateur. Dans les vecteurs,
base64 représente les octets **hors ligne seulement**, jamais l'encodage HTTP.
13 cas acceptés et 19 refusés ; empreintes moteur/polices `synthetic-*` non livrées.
Le corpus prouve les décisions du protocole, aucune pagination/layout réelle.

## Preuves et limites de livraison M8-C

Le [relevé initial du 7 octobre](../baselines/document-workshop/frida-v1-document-workshop-m8c-20261007.json), conservé sans modification,
porte sélecteurs développés, IDs chargeables, commandes/versions/durées/exits,
rouges/verts/contrôles causaux, corrections du contre-audit et nettoyage. Même
référence M7 : 1 604 IDs avant/après ; 60 nouveaux puis un positif PDF passif,
soit 61 nouveaux distincts, 1 665 au total. Les 70 voisins historiques et les
26 voisins Exports/readers restent séparés, sans double compte. Aucun skip.
Les six noms M4 TAP `\#` sont normalisés en `#` sans changer leur identité.
Les deux probes historiques du contre-audit M7 et les sondes indépendantes M8-C
restent hors sélection du dépôt. PostgreSQL réel prouve confirmation/claims ;
le fake prouve le contrat ; les parcours HTTP M6/M7 sont rejoués en isolation.
HTTP Unix, service Writer, pages DOCX effectives, glyphes/fidélité et confinement
plateforme restent non exécutés. Les preuves live laissées ouvertes par M7 ne
sont pas des prérequis de ce lot hermétique.

La frontière M5 BinaryRenderEvidence/_validated_binary est retirée ; son ID de
test et ses onze refus historiques sont conservés avec paire/manifeste fermés.
`render_confirmed` traduit les erreurs du contrat vers les codes applicatifs
M5 existants document_render_invalid/document_page_limit, sans migration.
Aucun wiring produit du renderer injectable, aucun format activé. Rebuild du
service applicatif nécessaire lors d'une livraison runtime ultérieure autorisée,
à effectuer dans ce lot ultérieur seulement ; aucun rebuild exécuté ici.

Lors de la livraison initiale `fc911ed3`, contre-lecture indépendante du delta et du relevé effectuée : avis favorable
à la fermeture contrat/simulation, aucun finding vivant identifié après
correction et reprojection des preuves. Sept conteneurs de preuve possédés,
sockets, caches et répertoire temporaire supprimés avec absence vérifiée.
Le cache navigateur partagé et les services opérateur sont préservés.
Ces constats sont historiques : les findings AUD-01/AUD-02 du contre-audit
ultérieur sont distincts des findings internes alors corrigés. AUD-01 est
traité dans son relevé dédié ; AUD-02 était alors ouvert et hors correction.
Les verts historiques ou leur rejouage seuls ne le fermaient pas ; son correctif
et ses preuves du 9 octobre sont consignés séparément ci-dessous.
Les preuves et contrôles Git de la correction sont consignés séparément.

Correction AUD-01 : baseline ciblée 62/62 avant patch ; reproduction autonome
4 sondes dont deux refus rouges, puis 4/4 verts. Douze nouveaux IDs donnent
27 assertions rouges avant la garde, puis 12/12 verts ; ciblés avec historique
M5 : 74/74. Comparaison finale des mêmes **1 665 IDs historiques + 12 nouveaux
= 1 677 distincts**, 70 + 26 voisins séparés, aucun skip. Les cinq parcours
HTTP natifs M6, les treize M7 et les dix M6 à fetch simulé restent verts.
La collecte vérifie les IDs Python individuellement chargeables, les identités
frontend fichier/nom/index et la normalisation des six noms M4 TAP inchangés.

Sous confirmation et claim SQL réels, les deux variantes invalides atteignent
la validation réelle et sont refusées **avant** la garde finale de format :
zéro mutation DAV, journal et reçu de succès, sans bundle local ni libération
positive. Le mutant de test neutralise seulement la garde structurelle dans
le vrai enfant ; il est détecté, les paires deviennent acceptables sous ce
mutant, mais le XML tronqué reste refusé. Aucun mutant livré.

L'échec intermédiaire Chromium M4 (21/22, brouillon vide pour le contrôle image)
est conservé ; sélecteur exact rejoué 22/22 sans patch ni attente allongée,
frontend/harnais identiques à la base. Cause non établie, hors attribution à
AUD-01. L'erreur initiale de chemin de reproduction et deux noms de modules
voisins erronés restent également qualifiés ; les sélections finales exactes
les remplacent comme preuves, sans effacer leurs échecs.

Seconde lecture indépendante du delta code/tests/docs et du relevé : favorable
à AUD-01 seul, sans nouveau finding bloquant ; revue statique et vérification
des artefacts, aucun test/SQL/probe supplémentaire revendiqué. La livraison
Git AUD-01 s’arrêtait pour contre-audit Codex ; aucun avis de fermeture d’AUD-02 dans ce lot historique.

### Correctif P2-M8C-AUD-02 — 9 octobre 2026

Base AUD-01 `1732a1266d4b573734ea0ea72baa72dea5e563ca`, même branche M8-C.
Reproduction autonome avec vrais validateurs/inspecteurs : acquittement valide
reçu à 120 s accepté et mémorisé avant patch, refusé après patch. Nominal et
119,999 s admis ; retard de result à 120 s déjà refusé. Le correctif ajoute
une seule décision temporelle dans la session existante, sans nouveau mécanisme.
Les nouveaux tests observent snapshot, événements, absence de cache/replay,
nettoyage unique, erreur initiale conservée et autorité. La composition sous
confirmation/claim PostgreSQL distingue le refus renderer traduit en
`document_render_invalid` du contrôle légitime `document_format_unavailable` ;
aucune mutation DAV, publication ni reçu de succès. Le contrôle négatif retire
uniquement la garde finale en mémoire dans le processus de test ; aucun mutant
produit ni modification du transport.

La déclaration AUD-01 « 1 677 verts » reste historique. Provenance distincte :
contre-audit indépendant du 7 octobre communiqué par Tof dans le mandat AUD-02,
**1 674 succès / 1 677**, plus 96 voisins verts. OBS-M7-CONC-01 : après deux
confirmations, GET observait encore `executing` (groupe 28/29 deux fois).
OBS-M7-UI-01 : les cas natifs `phone light` et `phone dark` échouaient au clic
`#btnSidebarClose`, hors viewport/intercepté par topbar (11/13). Causes non
établies : aucune qualification de bug produit, de régression AUD ou de simple
instabilité ; aucune correction M7 ici. L'incident historique M4 21/22 puis
22/22 de cause initiale inconnue reste consigné. Les exécutions du 9 octobre,
leurs résultats exacts et incidents de harnais sont dans le relevé dédié AUD-02 ;
un rejeu vert ne résout pas une cause inconnue. Clôture globale M8-C à
contre-auditer ; M8-S/M8-A non commencés, formats publics inactifs, aucune
preuve Writer, AF_UNIX ou Nextcloud live ni livraison runtime.


Exécutions AUD-02 du 9 octobre : baseline ciblée 73/73 ; nouveaux rouges
unitaires 11 IDs/5 échecs et SQL 2 IDs/3 sous-cas échoués ; autonome 3/4 puis
4/4. Ciblés séquencés 86/86 ; négatif limité à la nouvelle garde : 2 IDs,
4 échecs attendus, zéro erreur. Comparaison finale : **1 677 identités
historiques exactes + 13 nouveaux = 1 690 succès**, sans skip ; 70 + 26 voisins
verts séparés. M6 natif 5/5, M7 natif 13/13, M6 à fetch simulé 10/10 ; M7 SQL
29/29 dans le groupe Python 34/34, M4 Chromium 22/22. Ces verts actuels
n'expliquent ni ne ferment les observations M7/M4 historiques.

Incidents de preuve conservés : le premier ciblé et le premier négatif SQL
ont chevauché le même schéma `public` détruit/recréé par les fixtures ; le
premier groupe historique SQL 151/152 a également chevauché la fin du ciblé
de 1,752 s (`exact=None` au premier test M1). Contamination plausible,
causalité précise de la ligne absente non établie. Ces runs sont exclus de
la preuve finale, puis rejoués une seule fois en séquence, sans patch produit
ni assertion affaiblie : 86/86, négatif causal attendu, groupe SQL 152/152.
Commandes/IDs/exits/durées et incidents restent dans le relevé ; aucun double
compte, aucune répétition ajoutée au total. Seconde lecture indépendante et
nettoyage sont consignés dans ce même relevé ; arrêt après livraison Git pour
contre-audit Codex.
