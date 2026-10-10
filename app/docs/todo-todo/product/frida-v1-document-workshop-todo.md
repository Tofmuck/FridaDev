# Atelier documentaire agentique Frida V1 — spécification validée et roadmap

Date : 2026-09-29. Mise à jour M0–M2 : 2026-10-05 ; M3/M4/M5 : 2026-10-06 ; M6 : 2026-10-07 ; M8-S plateforme et correctif P2-M8S-AUD-01 : 2026-10-10.

Statut : **spécification et choix architecturaux validés par Tof ; M0 fermé sur
composants et preuves internes, contre-audit corrigé sur `FridaV1-Document-Workshop-M0` ;
M1 fermé sur menu, contexte `editing` et gardes, branche `FridaV1-Document-Workshop-M1` ;
M2 : succès historique 536/536 et revue G-R1–G-R4 Approved conservés ;
P2-M2-01 corrigé, comparaison historique 567/567 ; P2-M2-03 corrigé séparément
sur sa frontière frontend (594/594 historiques) ; P2-M2-02 corrigé séparément
sur Exports/Images/Notes,
P2-M2-04 backend corrigé séparément, comparaison historique 713/713 ;
P2-M2-05 corrigé séparément sur le résumé de réconciliation, comparaison
716/716 ; livraison runtime ouverte ;
M3 fermé sur code/preuves hermétiques et contre-audit, branche `FridaV1-Document-Workshop-M3`, livraison runtime ouverte ;
P3-M3-baseline-route-golden corrigé séparément le 2026-10-06 (tests/docs-only) ;
M4 livré sur code, P2-M4-01 et P2-M4-02 fermés après contre-audits indépendants ;
P3-M4-03 corrigé par erratum documentaire (1 198 déclarés conservés et rectifiés,
sélection publiée à 1 414, 21 identifiants réutilisables validés) ;
M4 non intégralement fermé ;
M5 fermé sur code/preuves hermétiques et contre-audit ; M6 implémenté sur code et preuves isolées, livraison runtime ouverte ; M7 fermé sur code/preuves isolées et contre-audit, livraison runtime ouverte ; M8-C fermé après contre-audits indépendants AUD-01/AUD-02 ; M8-S livré et qualifié sur la plateforme, correctif P2-M8S-AUD-01 livré, clôture soumise au contre-audit Codex ; M8-A, M9/M10 et Z non commencés. Seul le renderer isolé est démarré, aucun déploiement FridaDev ou format public activé**.

Provenance : reconnaissance architecturale puis design consolidé dans le même
dialogue avec Tof. Création documentaire committée dans `d6b63fd1`, puis validation
explicite de la spécification et des six décisions amont par Tof le 2026-09-29.
Le commit `9f728998` a inscrit ces décisions. La réconciliation autoritative du
29 septembre 2026 remplace le moteur par LibreOffice Writer headless/UNO isolé,
ferme l'exception AGENTS.md et ne démarre aucun lot applicatif ou plateforme.
Tof autorise M0 le 4 octobre 2026, puis recadre explicitement l'admission sur
le compteur partagé existant et impose une branche dédiée avant toute édition.
Ce recadrage est inscrit en §7.3 ; le premier arrêt avant patch sur l'exigence
ancienne de framing ne reste pas un blocage du lot autorisé.

Les observations de reconnaissance architecturale des sections 1–3 sont rattachées au HEAD
`a2483bf1aa6f5e93ba7ec2800b8ff053cc0af2c6`, branche `main`, checkout
`/opt/platform/fridadev`. Elles doivent être revalidées de façon ciblée avant
l'exécution des lots concernés, sans recommencer une reconnaissance générale.

## Lecture des cases et portes d'autorisation

Une case cochée dans les décisions signifie « décidé par Tof », pas « livré ».
Une case ouverte dans les critères ou les lots signifie « à implémenter ou prouver ».
Les inconnues factuelles sont isolées en section 11. Seules les preuves datées
dans M0–M4 décrivent des tests exécutés ou des déclarations historiques explicitement
qualifiées ; M5 dispose de son relevé daté hermétique, M6 dispose de son relevé isolé du 7 octobre ; M7 et suivants restent des preuves futures. L'erratum P3-M4-03
ci-dessous distingue les nouveaux rejeux des résultats antérieurs.
Une clôture code/preuves ne ferme pas migration opérateur, rebuild ou preuve DAV déployée.

- [x] Reconnaissance et proposition de design produites dans le dialogue.
- [x] Création de cette TODO autorisée par Tof.
- [x] Spécification et choix architecturaux ci-dessous validés par Tof le 2026-09-29.
- [x] Exception produit bornée du 29 septembre 2026 inscrite dans le
  [AGENTS.md racine](../../../../AGENTS.md) pour les lots M0–M10 et Z.
- [x] M0 explicitement autorisé le 2026-10-04 sur la branche dédiée ; les GO des
  autres lots restent requis séparément.
- [x] M1 explicitement autorisé le 2026-10-04, sur une nouvelle branche issue de M0 audité.
- [x] M2 explicitement autorisé le 2026-10-04, sur une branche issue de M1 corrigé ;
  preuves hermétiques seulement, sans autorisation runtime ou canari implicite.
- [x] M3 explicitement autorisé le 2026-10-06, depuis le M2 exact validé, pour code,
  migrations isolées, preuves, contre-audit et livraison Git ; aucune livraison runtime.
- [x] M4 explicitement autorisé le 2026-10-06 après livraison séparée du P3 M3,
  pour code, migrations isolées, preuves, contre-audit, documentation et commit/push.
  Aucun GO runtime, provider/DAV live ou M5.
- [x] P3-M4-03 explicitement autorisé le 2026-10-06 sur M4 : rectification
  documentaire, vérifications isolées, contre-audit et commit/push seulement.
- [x] M5 explicitement autorisé le 2026-10-06 depuis M4 exact `cc72aa963366660a6a135b66d206e39671556e8b`,
  pour confirmation, exécution injectée, migrations isolées, preuves, contre-audit,
  documentation et commit/push sur `FridaV1-Document-Workshop-M5` seulement.
  Aucun démarrage M6, raccord réel de mutation, runtime ou canari.
- [x] M6 explicitement autorisé le 2026-10-07 depuis M5 exact `6ea19f93bab0c1fb14fd4465ddc449f60f1531e4`,
  sur la nouvelle branche `FridaV1-Document-Workshop-M6` : raccord applicatif create/copy,
  reçu/lien/inventaire/continuité, preuves isolées, contre-audit et commit/push.
  Aucun runtime opérateur, modèle réel, canari DAV ou démarrage M7.
- [ ] GO distinct obtenu avant tout appel modèle réel de preuve.
- [ ] GO distinct obtenu avant tout canari d'écriture Nextcloud.

Le lot de réconciliation du 29 septembre était docs-only : roadmap, exception
AGENTS.md et résumé du hub. M0 ajoute uniquement les composants internes, tests
et contrats décrits ci-dessous ; aucun provider réel, contenu privé, mutation
DB/WebDAV, installation, build ou déploiement n'est autorisé par son mandat.

## 1. Décisions produit intégrées

- [x] Le bouton Fichier ouvre exactement deux choix : `Ajouter un fichier existant`
  et `Créer ou modifier un document`.
- [x] L'ajout existant conserve son comportement intégral.
- [x] Une cible existante peut ouvrir l'atelier par une sélection explicite ; une
  sélection de lecture ne donne jamais une autorisation d'écriture.
- [x] L'autorité d'entrée vient du geste explicite, puis la compréhension est
  agentique ; aucun routeur de formulations, regex ou catalogue de phrases.
- [x] Atelier spécialisé, avec fondation tool-ready ; aucune boucle tools générale
  ajoutée au modèle principal au premier palier.
- [x] Modèle initial principal `openai/gpt-5.1`, prompt documentaire distinct, un
  appel documentaire par préparation, aucun fallback ni nouveau réglage Admin.
- [x] Plafond documentaire dédié de 24 000 tokens de sortie ; défaut normal
  inchangé à 8 192 avec ses overrides légitimes ; fenêtre officielle 400 000
  et sortie officielle 128 000 tokens.
- [x] Recadrage Tof du 2026-10-04 : admission estimée par le compteur partagé,
  entrée complète plus 24 000 <=400 000 ; pas de seconde réserve de raisonnement
  ni de marge de framing inventée. Ce n'est pas une mesure exacte fournisseur.
- [x] Document produit : A4, corps 12 points, interligne 1,5, marges 2,5 cm ;
  canonical au plus 10 000 mots et 75 000 caractères Unicode, premier plafond atteint.
- [x] DOCX/PDF rendus au plus 20 pages Writer épinglé ; Markdown borné par mots/caractères,
  sans pagination stable ; aucune sauvegarde partielle en cas de dépassement.
- [x] Source de plus de 20 pages admise si elle tient intégralement dans l'entrée
  avec dialogue, prompt, autres sources et réserve ; sinon réduction/sélection ou refus.
- [x] Préparation sans deadline murale si progression effective projetée ; absence
  de progression pendant 120 secondes : échec fermé ; annulation explicite possible.
- [x] Pending sans expiration temporelle ; invalidation seulement par annulation,
  remplacement, changement de répertoire/cible ou perte de fraîcheur/précondition.
- [x] Chemins : Documents, au plus 8 niveaux, 180 caractères Unicode et 255 octets
  UTF-8 par segment/nom de fichier, 1 024 octets UTF-8 pour le chemin relatif complet.
- [x] Markdown sérialisé directement depuis le canonical ; DOCX enregistré et PDF
  exporté par le même moteur LibreOffice Writer headless piloté par UNO, depuis
  la même révision canonical. Service libre, auto-hébergé et isolé sur le même serveur.
- [x] La véritable demande reste une parole utilisateur canonique ; préparation
  d'une courte réponse Frida et d'une action pending sans double échange principal.
- [x] Le document est distinct de la réponse ; la dernière bulle n'est jamais
  enregistrée mécaniquement.
- [x] Confirmation compacte : nom, format, chemin relatif, conflit ou limite utile,
  et bouton `Créer le fichier` ou `Modifier le fichier` ; aucun aperçu complet.
- [x] Le bouton disparaît synchroniquement au clic ; exécution unique, état bref,
  puis lien ou erreur honnête.
- [x] Le même clic confirme les segments manquants affichés puis le fichier.
- [x] Des collections vides peuvent rester après un échec et sont signalées ; aucun
  rollback récursif ou suppression risquée de collections.
- [x] Toute création vit sous `<répertoire Frida sélectionné>/Documents/...`.
- [x] Adoption distante obligatoire : action `Parcourir les documents Nextcloud`,
  navigation bornée sous Documents, sélection, enregistrement dans workspace_files.
- [x] Aucun synchroniseur global, polling ou scan en arrière-plan.
- [x] `create` crée un nouveau fichier ; `update` conserve fichier, nom et
  workspace_file_id ; `copy` exige une demande explicite.
- [x] Update avec relecture fraîche et `If-Match` sur l'ETag attendu ; conflit sans
  fusion ni écrasement automatique ; Versions Nextcloud fait autorité de récupération.
- [x] Création Markdown, DOCX et PDF ; Markdown directement modifiable.
- [x] Canonical structuré persistant pour les documents Frida, rendus liés par
  version et empreinte.
- [x] DOCX externe lisible et retravaillable sans fidélité arbitraire promise.
- [x] PDF externe utilisé comme source ; modification vers un nouveau document,
  sauf PDF Frida dont le canonical correspondant est encore établi.
- [x] Profil : Unicode français, titres, paragraphes, gras/italique, listes,
  citations, liens, tableaux simples, sauts de page, marges et pagination cohérentes.
- [x] Aucune image incorporée au premier palier.
- [x] Reçu typé durable, réhydratable et injecté en métadonnées au tour suivant.
- [x] Inventaire commun au répertoire, sans injection automatique dans les autres
  conversations ni canonical dans Memory, Identity, Summary, Biblio ou Stimmung.

Les anciens OPEN « sous-répertoires », « adoption », « profil de rendu » et
« modèle/stratégie agentique » sont fermés par ce design. Volume, source longue,
budget, progression/pending, chemins et pile de rendu sont également décidés.
Les futurs lots implémentent ces décisions et en apportent les preuves ; ils ne
choisissent plus la taille du produit ou le moteur.

## 2. Sources et faits de la reconnaissance

### Contrats vivants

- [Répertoires de travail](../../states/specs/workspace-folders-contract.md).
- [Dossiers Nextcloud Frida V1](../../states/specs/frida-v1-nextcloud-folders-contract.md).
- [Ingestion Documents](../../states/specs/frida-v1-documents-ingestion-contract.md).
- [Documents actifs](../../states/specs/active-conversation-documents-contract.md).
- [Notes Markdown](../../states/specs/frida-v1-folder-markdown-notes-contract.md).
- [Exports](../../states/specs/frida-v1-exports-contract.md).
- [Images générées](../../states/specs/frida-v1-generated-images-contract.md).
- [Agenda](../../states/specs/frida-agenda-agent-contract.md).
- [Agent bibliothécaire](../../states/specs/frida-biblio-librarian-agent-contract.md).
- [Surface agentique](../../states/specs/agentic-response-surface-contract.md).
- [Streaming](../../states/specs/streaming-protocol.md).
- [Continuity Payload](../../states/specs/frida-v1-continuity-payload-contract.md).
- [Observabilité agentique](../../states/specs/frida-v1-agentic-observability-contract.md).

### Interfaces déjà identifiées

| Frontière actuelle | Fait observé et limite de réutilisation |
| --- | --- |
| [chat_service.py](../../../core/chat_service.py) | Orchestration réelle du tour et facultés dialogiques ; pas de branche documentaire livrée. |
| [chat_main_payload.py](../../../core/chat_main_payload.py) | Construction du payload principal, lanes tardives et manifeste ; aucune boucle tools générale. |
| [llm_client.py](../../../core/llm_client.py) | Modèle runtime et payload principal sans tools ; réglages à réutiliser, contrat documentaire distinct. |
| [chat_llm_provider_exchange.py](../../../core/chat_llm_provider_exchange.py) | Échange principal ; le lecteur non streaming retourne le texte, insuffisant seul pour contrôler la troncature documentaire. |
| [chat_llm_flow.py](../../../core/chat_llm_flow.py) | Override avant provider ; son succès impose final_lock et sa sauvegarde streaming est différée dans le générateur. |
| [chat_assistant_finalization.py](../../../core/chat_assistant_finalization.py) | Persistance assistant et effets post-persistance ; pas de transaction commune avec un pending documentaire. |
| [conversations_store.py](../../../core/conversations_store.py) | Snapshot atomique, réconciliation et meta JSONB ; pas de réservation avant appel provider. |
| [app.js](../../../web/app.js) | submitCanonicalChatMessage et garde navigateur ; transport unique /api/chat. |
| [chat_threads_sidebar.js](../../../web/chat_threads_sidebar.js) | Réhydratation des messages/meta et gardes de génération frontend. |
| [chat_active_documents.js](../../../web/chat_active_documents.js) | Picker, upload et drag-and-drop ; binding bouton/input à préserver lors du menu. |
| [workspace_files_service.py](../../../core/workspace_files_service.py) | Inventaire/ingestion existants ; meilleur catalogue public du fichier exécuté. |
| [workspace_document_nextcloud_runtime.py](../../../core/workspace_document_nextcloud_runtime.py) | Upload Nextcloud-first et compensation ETag ; publication locale répartie sur plusieurs transactions. |
| [workspace_file_nextcloud_links_store.py](../../../core/workspace_file_nextcloud_links_store.py) | Lien existant ; chemin complet, identité distante et ETag à compléter. |
| [active_document_text_extraction.py](../../../core/active_document_text_extraction.py) | Lecture textuelle MD/DOCX/PDF avec limites ; extraction ne prouve pas fidélité de mise en page. |
| [workspace_folder_export_docx_pdf.py](../../../core/workspace_folder_export_docx_pdf.py) | Renderer minimal : DOCX surtout paragraphes, PDF Helvetica/WinAnsi ; profil complet non couvert. |
| [runtime_settings_spec.py](../../../admin/runtime_settings_spec.py) | Défaut response_max_tokens de 8192 ; pas une preuve de la valeur runtime actuelle. |
| [token_counter.py](../../../core/token_counter.py) | Estimation heuristique, sans garantie de tokenisation du modèle. |

Les preuves hermétiques déjà obtenues pendant la reconnaissance sont conservées.
Elles ne prouvent pas les capacités futures décrites ici. Exports reste propriétaire
de ses snapshots et de son renderer minimal actuel : sa migration n'appartient
pas à cet atelier. Aucun renderer concurrent ni fallback n'est ajouté à l'atelier.

### Topologie revalidée en lecture seule au HEAD 9f728998

| Source réelle | Fait et portée de la preuve |
| --- | --- |
| `/opt/platform/fridadev-app/docker-compose.yml`, métadonnées Docker | Sous-stack `fridadev-app`, conteneur `platform-fridadev`, image `platform-fridadev-app:local` ; build applicatif distinct du checkout. Réseaux actuels `platform_platform_net`, `platform_fridadev_db_net`, `platform_browsing_net`, `platform_crawl_net`. |
| `/opt/platform/fridadev-db/docker-compose.yml` | PostgreSQL dans la sous-stack distincte `fridadev-db` ; aucune DB renderer à créer. |
| `/opt/platform/docker-compose.yml` | Nextcloud et Stirling-PDF appartiennent à la stack plateforme ; leurs conteneurs sont présents. Le réseau partagé `platform_platform_net` n'est pas `internal` : le rejoindre ne prouverait pas l'isolation du renderer. |
| [Dockerfile applicatif](../../../Dockerfile), [dépendances](../../../requirements.txt), recherche de binaires dans l'image active | Ni installation LibreOffice dans le Dockerfile ni `soffice`/`libreoffice` dans le PATH actif de FridaDev. Aucun lancement Writer effectué. |
| Image active `platform-stirling-pdf`, interrogation de package seule | `soffice` présent, paquet Writer `4:26.2.0-1~bpo13+1` ; cela ne livre ni wrapper UNO ni contrat renderer Frida. Ce n'est pas le pin du futur service. |
| `/opt/platform/homepage/services.yaml` | Entrée humaine Stirling PDF présente, décrite comme outils de fusion/découpe/conversion. Aucun outil UI n'est retiré ; aucune opération PDF exécutée pour valider cette liste. |
| [client OCR](../../../core/active_document_ocr_client.py), [upload actif](../../../core/active_document_upload_service.py), [OCR workspace](../../../core/workspace_file_ocr_service.py) | Stirling sert aussi l'OCR existant, dont conversion image→PDF. Ce flux explicite est préservé ; aucune chaîne Writer→Stirling pour générer les documents. |
| [client DAV](../../../core/workspace_document_nextcloud_client.py), contrats Folders/Documents | FridaDev résout ses capacités Nextcloud et assure le stockage conditionnel. Le renderer ne les reçoit pas. |
| Conteneurs recensés et vérification des seuls emplacements standard d'apps | Aucun conteneur Collabora ni app `richdocuments`/`richdocumentscode` aux emplacements testés. Activation effective de l'éditeur humain non établie ; aucune configuration privée interrogée. Cela n'autorise pas son installation dans ce chantier. |

Les lectures d'infrastructure ont porté sur champs structurels, métadonnées,
présence de binaires/package et entrée UI ; aucun secret, log privé, contenu
documentaire, appel DAV ou canari. Aucun nom de nouvelle stack/réseau n'est
présenté comme existant.

### Findings H1–H8 et décision de réconciliation

| Hypothèse | Verdict et preuve |
| --- | --- |
| H1 | Confirmée sur la version `9f728998`, sections 1, 3.12, 9 et 10 : ancienne pile prescrite et exclusion nominale de LibreOffice. Ces prescriptions sont remplacées intégralement ici. |
| H2 | Confirmée sur cette version, M8/M9/M10 et graphe de section 8 : dépendances et pagination supposent cette pile. Nouveau graphe ci-dessous. |
| H3 | Confirmée sur cette version, M8 et section 10 : propriété exclusivement applicative et négation du lot Sauron renderer. Frontière corrigée. |
| H4 | Confirmée par les AGENTS applicatif/plateforme et les sous-stacks observées : service isolé sous responsabilité Sauron, contrat/adaptateur métier sous Celebrimbor. |
| H5 | Confirmée pour les rôles : stockage Nextcloud, édition humaine Collabora, utilitaire Stirling et OCR existant sont distincts. Disponibilité Collabora non prouvée ; aucune composition agentique confiée à ces surfaces humaines. |
| H6 | Confirmée avec simplification : HTTP fermé sur socket Unix, UNO en pipe local dans le worker. Le même hôte permet `network_mode: none` sans réseau partagé ni nouveau port ; permissions/socket à prouver en M8-S. CLI distante, Docker exec depuis FridaDev et UNO brut sont écartés. |
| H7 | Confirmée par le reader DOCX textuel et les limites Exports : création depuis canonical et import externe n'ont pas la même garantie. M9-A/M9-B séparent leurs preuves et leurs refus. |
| H8 | Confirmée : docs officielles headless/UNO/filtres ci-dessous ; présence actuelle dans Stirling insuffisante. M8-S doit prouver les filtres/polices/layout de son image réellement livrée, sans API publique ni stockage direct. |

## 3. Spécification validée

Chaque rubrique distingue décision utilisateur, existant du HEAD et architecture
validée à implémenter. Les preuves à livrer ne sont pas des choix produit ouverts.
Les cases ouvertes sont des critères futurs ; aucun n'est déclaré livré.

### 3.1. Finalité et non-objectifs

**Décision :** préparer puis créer/modifier des documents dans Documents et
poursuivre ce travail dans la conversation.

**Existant :** Documents, Notes, Exports et Images ont des responsabilités propres.

**Architecture validée :** l'atelier possède préparation et exécution ; Notes conserve
l'append, Exports les snapshots. Pas de synchronisation globale, fusion concurrente,
images incorporées, continuation automatique ou tools principaux au premier palier.

**Preuve à livrer :** aucune inconnue de finalité produit.

- [ ] Préserver les responsabilités voisines dans les parcours et tests.

### 3.2. Vocabulaire

**Décision :** document distinct de la réponse, provenance durable.

**Existant :** workspace_file représente un fichier inventorié, pas son brouillon
ou sa confirmation.

**Architecture validée :**

| Terme | Sens |
| --- | --- |
| Canonical | Contenu structuré immutable d'une révision préparée. |
| Artefact | Identité documentaire reliant révisions Frida et fichier inventorié. |
| Action | Proposition figée create/update/copy et préconditions. |
| Reçu | Résultat typé lié à la conversation. |
| Adoption | Enregistrement explicite d'une ressource distante, sans écriture distante. |
| create | Nouveau fichier. |
| update | Même cible, nom et workspace_file_id. |
| copy | Nouveau fichier explicitement demandé à partir d'une source. |

**Preuve à livrer :** aucune.

- [ ] Utiliser ce vocabulaire dans schémas, projections et contrats.

### 3.3. UX et autorités

**Décision :** menu Fichier à deux choix ; lecture distincte de l'autorité d'écriture.

**Existant :** bouton relié directement au picker et sélections persistantes.

**Architecture validée :** un seul listener Fichier ; contexte serveur lié à conversation,
répertoire et cible éventuelle. Le contexte autorise la préparation ; seul le clic
de confirmation autorise la mutation.

**Preuve à livrer :** aucune nouvelle autorité produit.

- [ ] Conserver même DOM, contrôleur et callbacks sur desktop/mobile.
- [ ] Garder une sélection de source distincte d'une cible d'update.

### 3.4. Préparation conversationnelle

**Décision :** vraie parole utilisateur, réponse courte et pending durable.

**Existant :** soumission canonique et sauvegarde des messages/meta, sans transaction
commune avec une action documentaire.

**Architecture validée :** /api/chat unique, branche explicite, réservation avant appel,
sauvegarde utilisateur initiale, commit réponse/pending commun. Séquence en section 4.

**Preuve à livrer :** preuve de concurrence SQL réelle isolée.

- [ ] Garantir zéro échange principal normal après sélection de la branche atelier.
- [ ] Réhydrater un tour échoué sans inventer une réponse ou un succès.

### 3.5. Agent documentaire

**Décision :** modèle initial `openai/gpt-5.1`, prompt distinct, un appel documentaire
avec plafond dédié de 24 000 tokens ; défaut normal 8 192 et overrides conservés. Aucun
fallback, continuation, chunking, réparation par second appel ou réglage Admin nouveau.

**Existant :** modèle et budget résolus depuis les réglages runtime ; lecteur
non streaming centré sur le texte extrait.

**Architecture validée :** entrées typées : demande/tour, contexte dialogique partagé,
répertoire autorisé, références explicites, sources et versions, capacités/budgets.
Sortie stricte prepared, clarify ou refuse. Prepared contient réponse courte,
opération, cible, canonical et limites ; les deux autres n'ont aucune action
exécutable. Le modèle ne possède aucun client d'écriture.

**Preuve M0 :** admission estimée de l'entrée complète, par le compteur partagé,
avec réserve de génération 24 000 dans 400 000 (§7.3) ; limites canoniques et
terminaison du lecteur interne. Enveloppe prepared/clarify/refuse, réponse courte
et transaction produit restent M4 ; aucun raccord au chat n'est livré par M0.

- [ ] Valider l'enveloppe sans routage linguistique déterministe.
- [ ] Ne jamais relancer le modèle pour réparer automatiquement une sortie invalide.

### 3.6. Données et migrations

**Décision :** inventaire commun, canonical, confirmation unique et reçu durable.

**Existant :** message.meta existe ; identité DB des messages par conversation/seq ;
liens Nextcloud sans contrat complet de chemin relatif/ETag.

**Architecture validée :**

| Ensemble | Responsabilité validée à implémenter |
| --- | --- |
| workspace_files | Inventaire unique ; auteur/source typés ; ID stable en update. |
| workspace_file_nextcloud_links | Extension du lien : chemin relatif complet, identité, ETag, observation/fraîcheur. |
| document_artifacts | Identité documentaire, fichier lié après exécution et révision courante validée. |
| document_revisions | Canonical immutable, schéma et empreinte ; manifeste de rendu immutable lié après confirmation, avec octets figés, empreintes/version Writer/profil/polices/pages et correspondance distante. Aucun ODT durable. |
| document_actions | Contexte, proposition, sources/tour, progression de préparation, motifs d'invalidation, confirmation, état et journal ; aucun expires_at temporel de pending. |
| document_receipts | Résultat immutable, demande/confirmation, version et lien produit. |
| conversation_turn_claims | Réservation durable d'un tour ou d'une confirmation, propriétaire, lease technique renouvelable et jeton de génération. |

**Preuve à livrer :** identité DAV et environnement SQL de preuve.

- [ ] Unicité des tours clients et d'une réservation active par conversation.
- [ ] Au plus un reçu de succès par action et une identité distante par répertoire.
- [ ] Révisions immutables ; drafts absents de l'inventaire public.
- [ ] Migration ciblée des anciens liens seulement lorsque leur chemin est prouvé.
- [ ] Référencer le tour utilisateur stable dans meta, sans dépendre du seul seq.

### 3.7. Progression, invalidation, claim et idempotence

**Décision :** bouton éphémère, aucune double écriture ; préparation active tant
qu'une progression effective est observée et honnêtement projetée. Sans progression
pendant 120 secondes : échec fermé. Annulation explicite possible. Aucune deadline
murale supplémentaire tant que la progression continue. Pending sans expiration temporelle.

**Existant :** Agenda fournit des concepts mais pas le claim documentaire durable
et atomique requis.

**Architecture validée :** editing → preparing → pending → executing → succeeded ;
sorties cancelled, superseded, invalidated, failed ou remote_uncertain. Le pending
devient invalide uniquement par annulation, remplacement/supersession, changement
de répertoire ou cible, ou fraîcheur source/ETag/précondition différente de celle
de préparation. La confirmation revérifie fraîcheur, ETag, scope et claim avant
mutation. Une répétition retourne l'état sans relancer modèle ou PUT.

| Mécanisme | Effet et frontière |
| --- | --- |
| Inactivité de préparation | 120 secondes depuis la dernière progression effective, puis échec fermé ; aucune limite sur la durée totale si progression continue. |
| Annulation utilisateur | Arrête/neutralise la préparation ou annule le pending ; aucun résultat tardif exécutable. |
| Invalidation du pending | Liée aux seuls changements/événements décidés, jamais à son âge. |
| Lease technique du claim | Exclusion et détection du détenteur perdu, renouvelable ; ne constitue ni TTL du pending ni deadline murale de préparation. |

Une progression est un avancement vérifiable : nouvelle donnée utile reçue du
provider, étape réellement terminée ou avancement de rendu. Un keepalive, polling
d'état, animation, renouvellement de lease ou pourcentage inventé ne suffit pas.
L'interface projette phase/avancement content-free sans aperçu du document.
La perte d'un lease invalide le détenteur via son jeton ; elle ne relance pas
automatiquement modèle ou écriture et ne supprime pas un pending valide.

**Preuve à livrer :** exclusion SQL et crashs DB/WebDAV.

- [ ] Ne jamais rendre automatiquement pending une exécution incertaine.
- [ ] Refuser résultats tardifs et ancienne génération.
- [ ] Invalider les contextes/pending lors d'un changement de répertoire pertinent.
- [ ] Tester une progression réelle au-delà de 120 secondes de durée totale,
  puis 120 secondes sans progression et les keepalives non probants.
- [ ] Tester un pending ancien toujours confirmable si toutes ses préconditions
  restent valides ; lease, annulation et invalidation ont des états distincts.

### 3.8. Chemins et collections

**Décision :** créations et collections exclusivement sous Documents ; segments
manquants affichés confirmés avec le fichier. Au plus 8 niveaux de sous-répertoires
sous Documents, 180 caractères Unicode et 255 octets UTF-8 par segment, 1 024 octets
UTF-8 pour le chemin relatif complet ; le nom de fichier suit les limites de segment.

**Existant :** sanitizers de noms insuffisants pour valider un chemin complet.

**Architecture validée :** resolver serveur segment par segment ; refus segment
vide, . ou .., chemin absolu, séparateur déguisé, contrôle, ambiguïté Unicode et
sortie de racine. Aucun raccourcissement, renommage ou normalisation destructive
silencieuse : clarification/refus avant action confirmable. Chemin affiché et clés
de collision sont figés avant confirmation.

**Preuve à livrer :** application des valeurs décidées aux frontières locales et
DAV ; leur compatibilité doit être prouvée, sans en refaire un choix produit.

- [ ] Vérifier no-clobber local et distant ; ne jamais corriger le chemin au clic.
- [ ] Créer seulement les collections bornées prévues, vérifier les collections
  existantes et signaler celles laissées vides après échec.
- [ ] Ne jamais supprimer récursivement les collections.

### 3.9. Nextcloud-first et compensations

**Décision :** mutation distante avant publication locale ; collections vides
possibles et signalées.

**Existant :** upload Nextcloud-first et compensation ETag, mais plusieurs
transactions locales.

**Architecture validée :** journaliser l'intention avant mutation ; après succès distant,
publier fichier/lien, révision, reçu et état final dans une transaction commune.
Pour DOCX/PDF, confirmation/claim → canonical figé → renderer → validations Frida
→ journal de mutation → MKCOL bornés/PUT conditionnel → publication locale/reçu.
Un refus de rendu précède toute collection ou écriture distante. Le renderer ne
participe jamais à la transaction de stockage ni à sa compensation.
Compensation create uniquement avec propriété et ETag fort identique. Aucune
réécriture compensatoire automatique pour update ; Versions reste l'autorité.

**Preuve à livrer :** fenêtres de panne ; aucune atomicité distribuée supposée.

- [ ] Journal durable avant PUT/MKCOL ; pas de publication locale prématurée.
- [ ] Sans preuve de propriété, ne pas supprimer et conserver un état honnête.
- [ ] Réconcilier les métadonnées sans rejouer un PUT incertain.

### 3.10. Lecture, adoption et fraîcheur

**Décision :** adoption ciblée obligatoire, aucun scan global. La limite de 20 pages
porte seulement sur le document produit ; une source plus longue reste admissible
si elle tient intégralement dans l'entrée selon la section 7.

**Existant :** inventaire local ; sélection du chat normal lisant la copie locale.
M2 ajoute une lecture fraîche dédiée à l’atelier, sans modifier ce parcours normal.

**Architecture validée :** navigation paresseuse Depth: 1 de la collection explicitement
ouverte sous Documents ; réponse/entrées bornées. Adoption après sélection,
vérification identité/ETag, récupération admissible et commit fichier/lien.
Fraîcheur vérifiée avant mobilisation documentaire ultérieure.

**Preuves M2 acquises :** HTTP réel sur serveur synthétique, propriétés/taille/
préconditions et publication SQL isolée ; comportement DAV déployé encore à prouver.
Le [contrat M2](../../states/specs/frida-v1-document-workshop-m2-contract.md) fixe
interfaces, bornes, identité, cache et limites ; l’exécution ci-dessous porte les résultats.

- [x] Distinguer déjà lié, adoptable, collision locale et cible incompatible.
- [x] Ne pas injecter automatiquement le contenu d'une ressource adoptée.
- [x] Signaler déplacement/disparition sans recherche globale.

### 3.11. Update, ETag et Versions

**Décision :** même cible/nom/ID ; conflit sans écrasement ; Versions fait autorité.

**Existant :** Notes utilise GET frais/If-Match ; cela ne remplace pas la comparaison
avec la version préparée.

**Architecture validée :** ETag/empreinte figés à la préparation ; lecture fraîche et identité
vérifiées juste avant PUT If-Match exact. Différence ou 412 termine en conflit.
FridaDev récupère la cible au clic avec l'identité et l'ETag préparés, puis donne
seulement ses octets temporaires au renderer si le format le nécessite. Après
le rendu, FridaDev revérifie identité/fraîcheur et envoie If-Match de cette même
version : une modification pendant Writer reste un conflit. Aucun accès DAV du
renderer et aucune conservation de la source dans son espace éphémère.

**Preuve à livrer :** Versions et préconditions effectives sur la chaîne déployée.

- [ ] Aucun update sans version établie.
- [ ] Aucune fusion, copie, renommage ou nouvelle préparation automatique.
- [ ] Préserver le même workspace_file_id après succès.

### 3.12. Canonical et rendus

**Décision :** profil fixé sans images, DOCX/PDF Frida issus de la même révision
canonical et du même moteur Writer épinglé. Markdown direct ; DOCX enregistré,
PDF exporté par LibreOffice Writer headless via UNO dans un service privé isolé
sur le même serveur. Solution libre/auto-hébergée sans licence payante, cloud,
filigrane ou moteur de secours. A4, corps 12 points, interligne 1,5, marges 2,5 cm ;
canonical au plus 10 000 mots/75 000 caractères Unicode ; DOCX/PDF au plus 20 pages Writer.

**Existant :** renderer Exports minimal, profil complet non couvert.

**Architecture validée :** titres, paragraphes, spans, listes, citations, liens, tableaux
simples et sauts de page ; refus images, HTML actif, macros et références
exécutables. Canonical, cible, préconditions et profil renderer figés avant pending.
Markdown peut être sérialisé à ce stade ; pour les binaires, le clic confirme
l'exécution, puis le renderer produit des octets qui sont validés/figés avant PUT.
La carte annonce la limite utile de 20 pages Writer et ne prétend pas que le
rendu a déjà réussi. Échec de rendu après clic : erreur honnête, zéro écriture,
aucune sauvegarde partielle. Aucun second appel modèle ou nouveau bouton rejouable.
Marqueur documenté pour sauts de page Markdown, dont la pagination dépend du lecteur.

**Preuve à livrer :** contrat applicatif M8-C, service et pins M8-S, adaptateur M8-A,
pagination/fidélité finales M9/M10, section 9. Aucun renderer encore livré.

- [ ] Même révision pour canonical, rendu, empreintes et version renderer.
- [ ] Update Frida DOCX/PDF seulement si leur correspondance distante est établie.
- [ ] DOCX externe : limites détectées affichées ; clarification/refus si incompatibles.
- [ ] PDF externe : nouveau document proposé, pas d'update aveugle.
- [ ] Refuser sortie tronquée, finish_reason=length, canonical incomplet ou rendu
  de plus de 20 pages ; aucune sauvegarde partielle ou adaptation silencieuse des styles.
- [ ] Recharger le DOCX final dans le même Writer épinglé et obtenir son layout
  final ; exporter le PDF depuis ce même état, vérifier les comptes concordants.
  Ni docProps ni sauts déclarés ne prouvent les pages ; sans preuve, zéro PUT.
- [ ] Ne promettre aucune pagination identique à Microsoft Word sur toute machine.
- [ ] Canonical seule source Frida durable ; tout ODT interne reste temporaire et nettoyé.

### 3.13. Provenance et réhydratation

**Décision :** reçu durable, demande réelle et confirmation humaine établies.

**Existant :** meta réhydratable ; aucun reçu documentaire typé.

**Architecture validée :** reçu avec action/artefact/fichier/révision, conversation/répertoire,
nom/format/chemin, auteur de création et de révision, référence stable de demande,
confirmation, date, ETag/version, empreintes et lien produit. Un adopté garde son
origine externe même après révision Frida.

**Preuve à livrer :** aucune inconnue produit.

- [ ] Réhydratation après réouverture et lien produit fonctionnel.
- [ ] Référence de demande indépendante du seul seq.
- [ ] Reçu de succès uniquement après publication locale complète.

### 3.14. Injection et non-contamination

**Décision :** métadonnées au tour suivant ; contenu par référence explicite.

**Existant :** facultés et fenêtre dialogique consomment les vraies paroles ; lanes
tardives et manifeste du payload principal disponibles.

**Architecture validée :** lane de reçus produite à la volée après construction des entrées
des facultés ; jamais enregistrée comme message. Dernier reçu pertinent présent
au tour suivant, historique supplémentaire borné. La vraie demande et la réponse
courte restent dans le dialogue légitime.

**Preuve à livrer :** lane incluse dans l’estimation complète via M0 et séparation
des payloads, sans nouveau choix de budget produit.

- [ ] Aucun canonical, rendu, journal ou reçu synthétique dans Memory, Identity,
  Summary, Biblio ou Stimmung.
- [ ] Autre conversation : inventaire visible, contenu non injecté automatiquement.
- [ ] Manifeste de provenance content-free cohérent avec cette lane.

### 3.15. Observabilité

**Décision :** demande et confirmation établies sans contenu brut observable.

**Existant :** allowlists/projections content-free disponibles.

**Architecture validée :** événements préparation, progression, inactivité, annulation,
invalidation, claim, render job, refus/saturation/kill/cleanup renderer, conflit,
écriture, compensation, incertitude et reçu ; seulement IDs, états, codes, tailles,
comptes, durées, empreintes et versions techniques. Projection produit autorisée
distincte pour nom et chemin.

**Preuve à livrer :** tous les sinks, manifestes et projections admin.

- [ ] Aucun texte utilisateur/canonical, nom privé, chemin brut, URL distante ou
  exception de transport brute dans logs, JSONL et projections content-free.

### 3.16. Sécurité et refus

**Décision :** pas de mutation ambiguë ou de fidélité dissimulée.

**Existant :** lecteurs textuels avec limites ; copies locales potentiellement périmées.

**Architecture validée :** refus avant pending exécutable pour cible hors scope, version
indéterminée, archive inadmissible, extraction incomplète, dépassement, sortie
tronquée ou canonical invalide. Après confirmation binaire, rendu incomplet,
pagination excessive/non établie ou fidélité inadmissible : refus avant MKCOL/PUT.
Contenus documentaires non fiables et sans autorité ; renderer sans récupération
des liens, macros, code ou commandes contrôlés par le contenu.

**Preuve à livrer :** expansion d'archives, tailles, inactivité de préparation et
corpus de refus ; aucune deadline murale malgré une progression effective.

- [ ] Gardes appliqués avant mutation, même contre requête HTTP construite hors UI.
- [ ] Aucun appel OCR implicite ou perte de contenu silencieuse ajoutée par l'atelier.

### 3.17. Tests et preuves live

**Décision :** aucun canari d'écriture avant gardes, claim et compensations.

**Existant :** preuves de briques acquises ; workflow futur non prouvé.

**Architecture validée :** TDD causal par capacité, voisins et injections de panne ; preuve
SQL isolée pour concurrence ; corpus synthétiques pour rendus. Appel modèle réel
et canari Nextcloud chacun sous GO distinct, preuves datées/content-free.

**Preuve à livrer :** environnement SQL isolé pour transactions ; tests fake du
contrat puis preuves synthétiques du service privé effectivement livré par Sauron.
Rendu live, appel modèle et écriture Nextcloud sont trois autorisations distinctes ;
ce lot n'en exécute aucune. Une présence binaire ne ferme pas une preuve UNO/layout.

- [ ] Ne pas fermer un invariant réel avec une preuve uniquement mockée.
- [ ] Ne pas présenter les tests projetés comme exécutés.

### 3.18. Responsabilités

**Décision :** application Celebrimbor, plateforme Sauron.

**Existant :** LibreOffice absent du PATH FridaDev ; présent dans Stirling mais
sans wrapper dédié prouvé. Aucun renderer Writer de cet atelier livré.

**Architecture validée :** Celebrimbor : canonical, contrat/adaptateur, UI, claims,
orchestration, DAV, validations, persistance, reçus, tests applicatifs/observabilité.
Sauron : image isolée, wrapper de processus UNO, ressources, pins Writer/filtres/
polices, socket/permissions, confinement, health et exploitation. Contrat commun,
preuves séparées ; aucun patch de la racine de l'autre.

**Preuve à livrer :** M8-S obligatoire, M8-A raccord applicatif ; Sauron conditionnel
pour DAV/Versions et environnement SQL seulement si leurs faits l'imposent.

- [ ] Aucun changement de plateforme par proximité ou contournement applicatif.

### 3.19. Achèvement et non-prolongation

**Décision :** atelier spécialisé et fondation tool-ready.

**Existant :** aucune boucle tools principale à étendre.

**Architecture validée :** clôture sur create/adoption/read/copy/update, trois formats,
confirmation, conflits, continuité et voisins préservés. Appel de service sans DOM
pour prouver tool-ready, sans implémenter de tool principal. Images, continuation
de documents longs et édition enrichie nécessiteraient d'autres projets.

**Preuve à livrer :** aucune extension indispensable à la fermeture.

- [ ] Fermer par les critères du lot Z ; ne pas convertir les suites hors scope en
  condition permanente de clôture.
- [ ] Aucun moteur secondaire, suite bureautique supplémentaire ou pipeline PDF
  parallèle sans nouvelle décision produit explicite ; Z ne les ouvre pas.

## 4. Raccordement conversationnel exact — L1

### Raccord validé

| Raccord réaliste | Évaluation |
| --- | --- |
| Chat normal puis préparation | Écarté : double génération principale et réponse normale sans rôle clair. |
| Route et transcript documentaires indépendants | Écarté : duplication de sauvegarde/finalisation et risque de contourner les facultés. |
| /api/chat unique avec branche documentaire explicite | Validé : transport/transcript réutilisés, échange principal normal remplacé. |

### Séquence à livrer

- [ ] Ouvrir un contexte serveur lié à conversation existante et répertoire courant.
  Pour un nouveau thread, réutiliser la création conversationnelle avant le contexte.
- [ ] Garder submitCanonicalChatMessage ; transmettre client_turn_id et
  document_context_id ; conserver les input_mode actuels.
- [ ] Valider contexte, scope et modes compatibles ; réserver durablement avant appel.
- [ ] Sauvegarder le vrai role=user, texte canonique et références dans une transaction
  initiale. Si elle échoue, aucun appel documentaire.
- [ ] Préserver le raccord dialogique constitutif à la vraie parole ; apporter les
  sources documentaires ensuite au payload documentaire. Atelier sans activation
  Web/Agenda/Biblio/append Notes.
- [ ] Appeler une fois le modèle principal avec prompt documentaire ; jamais passer
  ensuite dans l'échange principal normal, même en cas d'erreur ou sortie vide.
- [ ] Valider enveloppe, sources, opération, chemin, canonical, limites et profil
  renderer attendu ; serializer Markdown direct, sans lancer Writer avant le clic.
- [ ] Suivre la progression effective pendant toute la préparation et la projeter
  sans contenu ; watchdog d'inactivité de 120 secondes, sans deadline murale.
- [ ] Permettre l'annulation explicite et neutraliser les résultats tardifs.
- [ ] Commit commun réponse courte assistant, révision, pending et clôture du claim ;
  vérifier encore génération et répertoire ; remplacer explicitement l'ancien pending
  de ce contexte.
- [ ] Après commit, émettre la réponse courte et un terminal done unique avec updated_at.
  Aucun canonical dans le flux visible.
- [ ] Réhydrater la projection associée au tour ; meta contient des références seules.

La sauvegarde actuelle doit être extraite seulement pour partager la primitive
de snapshot dans une transaction fournie. Ne pas reconstruire le transcript par
INSERT indépendants ni créer un second store de messages.

L'override actuel ne sert pas tel quel au succès documentaire : provenance
final_lock et commit streaming paresseux. La réponse du modèle documentaire garde
une provenance main_model avec référence documentaire ; un refus imposé par un
garde peut utiliser final_lock. Commit documentaire avant émission de la réponse
courte et du terminal de succès. Pendant la préparation, le contexte expose
phase/avancement et annulation ; leur projection ne contient pas le canonical.
La lecture ciblée de cet état d'opération n'est pas une synchronisation de fichiers
Nextcloud et ne déclenche aucun scan distant.

- [ ] En panne après sauvegarde utilisateur, ne jamais annoncer un succès sans commit.
- [ ] Persister une courte explication si possible ; sinon projeter un tour
  interrompu/incertain identifiable sans réponse inventée.
- [ ] Ne pas reprendre automatiquement le modèle avec le même ID de tour.
- [ ] Faire participer le chat normal à la réservation minimale pour exclure une
  course avec préparation/confirmation ; refuser les anciens jetons.
- [ ] Ne pas tenir une transaction DB ouverte pendant le réseau.

Le compteur de production documentaire est un appel au modèle principal et zéro
échange principal normal. Le pipeline comporte déjà des appels constitutifs,
notamment Stimmung/herméneutique : ils restent préservés, visibles et comptés
séparément. Il n'est pas promis un seul appel HTTP tous agents confondus.

## 5. UX Fichier — L2

| État | Comportement |
| --- | --- |
| Normal | Compositeur existant. |
| Menu ouvert | Deux choix exacts ; fermeture par sélection, Échap ou clic extérieur. |
| Ajout existant | Input, callback change, upload et drag-and-drop actuels. |
| Atelier ouvert | Répertoire, cible éventuelle, sources et demande dans le compositeur courant. |
| Préparation | Garde de soumission, progression réelle content-free et annulation ; aucune confirmation disponible. |
| Pending | Carte compacte sans aperçu complet. |
| Confirmation engagée | Bouton retiré synchroniquement, état bref. |
| Rendu binaire confirmé | Claim actif, progression effective du worker ; validation des artefacts avant toute mutation distante. |
| Résultat | Lien, conflit, invalidation, annulation ou erreur d'inactivité honnête. |

- [ ] Déplacer seulement le listener Fichier ; ne pas perdre le callback change
  actuellement conditionné avec buttonEl/inputEl dans chat_active_documents.bind.
- [ ] Conserver input multiple, formats admis et drag-and-drop.
- [ ] Un DOM/contrôleur commun desktop/mobile ; présentation seulement adaptée.
- [ ] Placer Parcourir les documents Nextcloud dans l'atelier/sélecteur de cible,
  sans troisième choix du menu.
- [ ] Conserver localement uniquement ID/état de tentative pour éviter de réarmer le
  bouton après refresh ; ce marqueur n'accorde aucun droit serveur.
- [ ] Après perte réseau, lire l'état, sans répétition automatique du POST.

Un clic qui n'a jamais atteint le serveur ne peut être connu globalement. L'UI
ne doit pas prétendre le contraire ; l'unicité d'exécution est garantie au serveur.

## 6. Adoption et routes à livrer — L3

Les contextes POST/GET sont implémentés en M1, historiquement sans progression de préparation.
Les routes remote/adopt sont implémentées et prouvées hermétiquement en M2 ;
leur livraison runtime reste ouverte. `/api/chat` avec `document_context_id`
raccorde depuis M4 la préparation Markdown, avec GET/cancel des actions durables.
M5 ajoute la confirmation à exécuteur injecté pour ses preuves hermétiques ;
M6 raccorde la factory réelle au registrar existant : capacité annoncée seulement
si les prérequis sont disponibles. Ce code est prouvé en isolation, sans livraison
runtime opérateur ni canari. Voir le [contrat M6](../../states/specs/frida-v1-document-workshop-m6-contract.md).

| Interface | Responsabilité |
| --- | --- |
| POST /api/document-workshop/contexts | Contexte borné conversation/répertoire/cible. |
| GET /api/workspace-folders/{id}/documents/remote | Collection explicitement ouverte sous Documents. |
| POST /api/workspace-folders/{id}/documents/adopt | Adoption sélectionnée ; aucune écriture distante. |
| GET /api/document-workshop/contexts/{id} | Réhydratation contexte/capacités et progression effective content-free. |
| POST /api/chat avec document_context_id | Préparation conversationnelle unique. |
| GET /api/document-workshop/actions/{id} | État public de l'action. |
| POST /api/document-workshop/actions/{id}/confirm | Claim et exécution confirmée. |
| POST /api/document-workshop/actions/{id}/cancel | Annulation ciblée de préparation, pending ou exécution ; avec intention, résultat distant incertain et neutralisation des résultats tardifs. |

| Cas distant | Traitement |
| --- | --- |
| Déjà lié | Retourner l'ID existant et actualiser l'observation ciblée. |
| Nouveau adoptable | Vérifier identité/ETag/taille/type/extraction, puis commit fichier/lien. |
| Collision locale | Refuser association/remplacement silencieux. |
| Incompatible | Raison précise : hors racine, collection, format, version indéterminée, autre garde. |
| Déplacé/disparu | Signaler l'écart et permettre sélection explicite, sans recherche globale. |

- [x] Navigation Depth: 1, paresseuse et bornée ; aucun href/URL frontend directement
  exécuté comme cible DAV.
- [x] Références opaques vérifiées côté serveur et scope Documents effectif.
- [x] Pas de pseudo-pagination dissimulant un scan complet : DAV n'est pas supposé
  fournir une pagination universelle.
- [x] Limite honnête si collection trop volumineuse.
- [x] Adoption sans injection automatique ; mobilisation ultérieure explicite.

## 7. Bornes décidées et admission — L4

Les valeurs suivantes sont des décisions définitives. M0 les implémente et les
prouve ; il ne choisit aucun volume produit ou budget de sortie.

### 7.1. Document produit

| Borne | Valeur décidée et application |
| --- | --- |
| Canonical | Au plus 10 000 mots et 75 000 caractères Unicode ; premier plafond atteint. |
| DOCX et PDF | Au plus 20 pages A4 calculées par le Writer effectivement épinglé, en plus des deux bornes canoniques. |
| Mise en page | Corps 12 points, interligne 1,5, marges de 2,5 cm. |
| Markdown | 10 000 mots et 75 000 caractères Unicode ; aucune limite de pagination instable. |
| Génération | Plafond documentaire dédié de 24 000 tokens de sortie, enveloppe et canonical compris selon le transport réel. |

Ces plafonds sont simultanés, pas des équivalences ni des tailles garanties.
24 000 tokens ne garantissent ni 10 000 mots ni 75 000 caractères ; ces volumes
ne garantissent pas 20 pages. Titres, tableaux, sauts et styles influent sur la
pagination. Le premier plafond atteint fait foi, sans augmenter les autres pour
faire tenir la demande. Aucun ajustement silencieux de police, interligne ou marges.

- [x] M0 : compter mots/caractères sur tout le contenu canonical, y compris titres,
  listes, citations et tableaux ; méthode Unicode reproductible et testée.
- [x] M0 : distinguer caractères Unicode et octets UTF-8 ; ne pas utiliser la longueur
  UTF-16 navigateur comme compteur de points de code.
- [ ] Exiger sortie modèle complète, schéma valide et plafonds canoniques avant pending ;
  contrôler le plafond final Writer après confirmation et avant toute mutation distante.
- [ ] Toute troncature, finish_reason=length, canonical incomplet ou rendu de plus de
  20 pages : refus honnête, aucune sauvegarde partielle. Erreur modèle/canonical
  bloque le pending ; erreur de rendu confirmé termine l'action sans mutation.
- [ ] Ne jamais rogner un document ou diminuer la mise en page pour contourner un refus.

### 7.2. Source longue

La limite de 20 pages concerne uniquement le document produit. Une source peut
dépasser 20 pages si son contenu entier passe l'admission estimée de l'entrée du
modèle, avec dialogue, prompt, autres sources et réserve de génération. Le nombre de pages
d'une source n'est pas un critère de refus de volume produit.

- [x] M0 : admettre une source de plus de 20 pages si l'entrée entière passe la garde estimée.
- [x] M0 : aucune troncature, résumé ou échantillonnage silencieux d'une source.
- [ ] Si elle ne tient pas, demander de réduire/sélectionner la source ou refuser
  avant l'appel documentaire ; aucune réduction automatique de la fenêtre dialogique.

### 7.3. Modèle et budget dédiés

Modèle initial : `openai/gpt-5.1`, modèle principal courant décidé par Tof.
Fenêtre officielle : 400 000 tokens ; sortie maximale officielle : 128 000 tokens.
Le plafond local documentaire de 24 000 est volontaire. Le défaut normal reste
8 192 tokens, ainsi que les réglages et overrides normaux légitimes actuels.

Références primaires conservées et vérifiées sur leurs pages publiques, sans appel modèle :

- [OpenAI — GPT-5.1](https://developers.openai.com/api/docs/models/gpt-5.1).
- [OpenRouter — openai/gpt-5.1](https://openrouter.ai/openai/gpt-5.1).

**Recadrage explicite de Tof du 4 octobre 2026 :** réutiliser la structure de
comptage du système. La décision initiale demandait un décompte exact ou une
borne conservatrice avec marge de framing ; la première tentative s'est arrêtée
avant patch faute de preuve de ce framing. Tof remplace cette exigence par
l'estimation partagée, sans modifier modèle, volumes, budget, transport ou timeout :

```text
E = token_utils.estimate_tokens(entree_documentaire_complete, modele)
estimated_input_tokens = E
estimated_total_tokens = E + 24 000
admission_estimee : estimated_total_tokens <= 400 000
```

E utilise le callable injecté existant `core.token_utils.estimate_tokens` →
`token_counter.estimate_message_tokens` → `estimate_text_tokens`, sans copie
ni changement d'algorithme. Il reste heuristique et indépendant de l'identité
du modèle dans son implémentation actuelle : aucune exactitude fournisseur ou
borne mathématique complète n'est revendiquée. Aucun tokenizer ou coefficient
documentaire supplémentaire, aucune recherche de marge de framing nécessaire.

Le payload final est figé avant estimation : prompt spécialisé, dialogue,
sources complètes, contexte, métadonnées injectées et instructions de schéma.
Un `response_format` hors messages est représenté par un adaptateur explicite
d'estimation avec le même callable. Headers/secrets et attribution HTTP ne sont
pas du texte de prompt. Rien n'est ajouté au texte envoyé après admission.
Une estimation absente, invalide ou en erreur refuse avant transport ; jamais zéro
de secours, troncature, résumé ou réduction cachée de la fenêtre dialogique.

Le raisonnement masqué consomme encore la génération : sur le transport
OpenRouter Chat Completions choisi, il partage `max_tokens=24 000` avec le texte
visible. Aucune seconde réserve n'est ajoutée. Effort et masquage restent résolus
par les primitives serveur existantes. Les usages prompt/completion/total
rapportés réutilisent l'extraction actuelle et restent distincts de E ; leur
absence n'autorise aucune invention. Refus de contexte provider → échec sans
document partiel, deuxième appel ou retour vers le chat normal. Les limites
publiques et ces tests simulés ne constituent pas une mesure live.
Le [contrat interne M0](../../states/specs/frida-v1-document-workshop-m0-contract.md)
fixe les représentations, codes et frontières consommables par les prochains lots.

- [x] M0 : séparer le plafond documentaire du réglage du chat normal ; payload documentaire
  à 24 000, défaut normal à 8 192 et overrides préservés, sans réglage Admin nouveau.
- [x] M0 : vérifier l'admission estimée avant appel et conserver finish_reason/usages utiles.
- [x] M0 : borner l'enveloppe technique selon les plafonds décidés et le schéma, sans
  introduire de plafond produit caché ou de troncature.
- [x] M0 : un seul appel documentaire ; aucun fallback, continuation, chunking ou second
  appel de réparation.
- [x] M0 : un modèle hors contrat initial ne devient pas silencieusement une alternative.
- [x] M0 : états internes de progression effective, 120 secondes d'inactivité puis
  échec fermé ; aucune deadline murale pendant progrès. Projection UI future M4.

## 8. Roadmap par micro-lots

M0 est fermé sur composants et preuves internes, contre-audit corrigé sur sa branche dédiée.
M1 est fermé sur menu/contexte `editing` et gardes inactifs, sur sa branche issue de M0.
M2 conserve la contre-revue historique G-R1–G-R4 Approved et le succès 536/536.
Le correctif indépendant P2-M2-01 du 5 octobre passe historiquement 567/567.
P2-M2-03 est corrigé dans un lot frontend distinct (594/594 historiques) ;
P2-M2-02 est ensuite corrigé sur les trois familles ci-dessous, puis P2-M2-04
sur le contrat backend de listing (713/713 historiques). P2-M2-05 est corrigé
dans le lot de résumé ci-dessous (716/716). Migration opérateur, rebuild et lecture DAV déployée
restent ouverts. M3 est fermé sur code/preuves et contre-audit ci-dessous ;
M4 est livré sur code/preuves hermétiques, P2-M4-01 et P2-M4-02 fermés après
contre-audits indépendants, P3-M4-03 corrigé documentairement ; livraison runtime
ouverte. M5 est fermé sur code/preuves injectées ; M6 raccorde le parcours réel
avec preuves isolées, sans déploiement. M7 est fermé sur code/preuves isolées et contre-audit, livraison runtime ouverte ; AUD-01 et AUD-02 fermés après contre-audits indépendants.
**M8-C fermé sur contrat, code et preuves isolées ; M8-S et correctif P2-M8S-AUD-01 livrés/qualifiés, clôture soumise au contre-audit Codex.**
M8-A, M9/M10 et Z restent non commencés. Spécification et
décisions amont sont validées et l'exception produit est inscrite.
Le GO de chaque lot applicatif/plateforme reste préalable à son exécution ;
les GO M0–M4 et P3-M4-03 ne valent pour aucun lot suivant ni déploiement.
UI construite tôt, contrats DOM/HTTP hermétiques ; aucun parcours d'écriture exposé
comme fonctionnel avant livraison des protections et de la tranche complète.

### Dépendances contrôlées

| Lot | Dépendances et frontière de fermeture |
| --- | --- |
| M0 | Décisions validées et autorisation applicative ; gardes/admission/progression, sans prétendre livrer les rendus binaires. |
| M1 | M0 ; entrée UI et upload préservé dès ce premier lot UI. |
| M2 | M0–M1 ; adoption ciblée et fraîcheur des sources. |
| M3 | M0–M2 ; réservation, lease technique et preuve SQL isolée. |
| M4 | M0–M3 ; préparation Markdown et pending persistant. |
| M5 | M4 et gardes M0/M3 ; confirmation/compensations hermétiques. |
| M6 | M5 ; parcours Markdown complet, premier canari seulement avec GO distinct. |
| M7 | M6 ; update Markdown, ETag et Versions. |
| M8-C | M0–M7 ; contrat fermé canonical/Writer et client fake, Celebrimbor. |
| M8-S | M8-C ; image/service Writer isolé, sécurité et preuves synthétiques, Sauron. |
| M8-A | M8-S et M8-C ; adaptateur FridaDev, validation/cleanup et preuve interne, Celebrimbor. |
| M9-A | M8-A et M7 ; DOCX Frida create/copy/update avec pagination Writer. |
| M9-B | M9-A ; retravail DOCX externe et refus de fidélité séparés. |
| M10 | M9-B ; PDF du même état Writer et PDF externe comme source. |
| Z | M0–M7, tous les sous-lots M8/M9 et M10 ; clôture finie et voisins préservés. |

Ordre : M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8-C → M8-S → M8-A
→ M9-A → M9-B → M10 → Z, sans cycle. Les sous-lots restent dans M8/M9, pas
de nouveau projet ni seconde roadmap. M0 établit le contrat des 20 pages Writer ;
M8-S prouve le moteur et M9/M10 prouvent les fichiers effectivement publiés.
Markdown précède les binaires ; canari après M5, tranche hermétique fermée et GO
distinct. M8-S n'exige ni modèle réel ni Nextcloud et ne dépend pas de M9/M10.

### M0 — Implémentation et preuve des bornes décidées

**Objectif :** rendre applicables les bornes de volume, admission, chemin et
inactivité déjà fixées ; aucune nouvelle décision de taille ou budget.
**Dépendances :** spécification validée, exception AGENTS.md et GO M0 du
2026-10-04 avec recadrage compteur partagé et branche dédiée. Préalable de M1.
**Frontières :** contrat documentaire, adapter modèle, compteur/admission, gardes
canoniques et de chemin, suivi de progression ; chat normal préservé.
**Interface :** gpt-5.1, sortie documentaire 24 000, chat 8 192, fenêtre 400 000,
estimation partagée E + réserve 24 000 ; canonical 10 000 mots/75 000 points de code ; profil A4/20 pages
déclaré, compteur final fourni par Writer M8-S puis validé en M8-A/M9/M10 ;
watchdog d'inactivité 120 secondes, aucune installation renderer en M0.
**Propriétaire :** Celebrimbor.
**Statut M0 :** critères internes prouvés et contre-audit corrigé le 2026-10-04 ;
livraison Git sur branche dédiée requise, preuve d'alignement dans le retour de lot.

- [x] Rouge causal : refus à 10 001 mots ou 75 001 caractères, JSON complet mais
  finish_reason=length, entrée qui tient sans réserve mais dépasse avec elle ;
  payload documentaire héritant par erreur de 8 192 ou payload normal porté à 24 000.
- [x] Prouver les limites exactes de chemin, y compris nom de fichier, octets/Unicode,
  et refus sans normalisation destructive ; source >20 pages admise si elle tient.
- [x] Implémenter estimation d'entrée par le compteur partagé sans marge ajoutée,
  validation de sortie et contrat de page_count ; aucune pagination binaire livrée
  artificiellement avant son renderer.
- [x] Implémenter le suivi d'inactivité : progrès continu au-delà de 120 secondes
  accepté, 120 secondes sans progrès refusées, keepalive seul non probant.
- [x] Tests ciblés synthétiques et transport fake ; voisins réglages/raisonnement/
  parser/compteur/path validation, sans fournisseur ni DB opérateur.
- [x] Faux verts contrôlés : heuristique présentée comme exacte, payload partiel mesuré,
  raisonnement omis, mots/UTF-16 confondus, timer relancé par animation ou heartbeat.
- [x] Interdire provider réel, fallback, deadline murale pendant progrès, nouvelle
  taille produit et modification du défaut normal 8 192 ou des overrides légitimes.
- [x] Synchroniser contrats bornes/transport/progression ; appel réel éventuel
  sous GO distinct, jamais nécessaire pour décider les chiffres.
- [x] Aucun déploiement produit ; rebuild seulement lors de livraison applicative
  explicitement autorisée. Fermer sur gardes et mesures hermétiquement prouvés,
  en laissant pagination/rendus binaires aux lots M8–M10.

#### Exécution M0 du 4 octobre 2026

Base revalidée : checkout `/opt/platform/fridadev`, `main` propre,
HEAD = upstream `origin/main` = branche distante
`e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb`, divergence `0/0`, constat distant
par `git ls-remote` sans lecture de credentials. Le nom de branche était libre
localement et sur origin. `git switch -c FridaV1-Document-Workshop-M0` exécuté
avant toute édition ; HEAD restait à la base, worktree propre. Aucun pull,
second checkout, worktree, merge ou édition de main.

Plan minimal retenu : isoler les six responsabilités internes suivantes ;
ne toucher aucun coordinateur/caller existant et ne pas installer de dépendance.
Le [contrat M0](../../states/specs/frida-v1-document-workshop-m0-contract.md)
documente précisément formes, comptage Unicode, clés et codes de refus.

| Fichier `app/core/` | Preuve effective |
| --- | --- |
| `document_workshop_contract.py` | Bornes fixes ; preuve page_count strictement entière 1–20 ; A4/12 pt/1,5/2,5 cm. Aucun rendu. |
| `document_canonical.py` | Schéma fermé, titres/spans/listes/citations/cellules/liens comptés ; points de code et mots Unicode sans réécriture ; snapshot JSON. |
| `document_workshop_admission.py` | Constructeur partagé à 24 000, modèle exact, effort inchangé/masqué, corps figé ; compteur partagé injecté et garde E + 24 000 <=400 000. |
| `document_workshop_provider.py` | Un send simulé au plus, vrais lecteurs JSON/SSE conservant stop/modèle/usages ; aucun retour vers le chat, retry ou réparation. |
| `document_workshop_progress.py` | Horloge monotone, surveillance indépendante des lectures/ouvertures bloquées, inactivité et annulation irréversibles. |
| `workspace_document_paths.py` | Chemin original Documents-préfixé, bornes exactes, collision NFC/casefold séparée et encodage DAV segmentaire purement local. |

La méthode de mots utilise lettres/nombres Unicode, marques attachées et
apostrophes/tiret internes ; les spans d'une unité sont joints avant compte.
Chaque unité et cible de lien contribue une fois, sans caractères séparateurs
inventés. `len(str)` compte les points de code, distincts des graphèmes/UTF-16/
UTF-8. Refus sans modification de l'entrée à 10 001 mots ou 75 001 points de code.
Le plafond technique de JSON canonical 1 Mio est celui déjà décidé en §9.3,
distinct des volumes produit ; il refuse la structure trop volumineuse sans
troncature. Ni page_count fourni par le modèle, ni sauts, ni docProps ne prouvent
la pagination finale : M8–M10 doivent fournir cette preuve Writer liée au rendu.

Les callers futurs fournissent prompt, dialogue, contexte, sources intégrales
et métadonnées documentaires en messages. Instructions de schéma ajoutées avant
estimation ; schéma `response_format` hors messages via adaptateur d'estimation
local avec le même callable. Attribution HTTP/headers/secrets hors texte modèle.
La garde accepte E=376 000 et refuse 376 001 ; les 24 000 partagent génération
visible et raisonnement, sans seconde réserve. Aucun compteur documentaire,
framing supplémentaire, changement des réglages ou promesse d'exactitude.

L'URL, secret, attribution et raisonnement sont résolus par `llm_client` existant,
avec fixtures synthétiques et sans DB/runtime. Le payload normal réellement
construit garde le défaut de seed 8 192 et un override synthétique 12 345.
Le payload documentaire transmis au fake porte 24 000 et
`provider.allow_fallbacks=false`, applicable au contrat public OpenRouter
Chat Completions. Les lecteurs normaux restent inchangés : le non-streaming
réduit au texte et le streaming chat ne fournissent pas ce résultat documentaire
typé. Le sanitizer upload reste inchangé et n'est pas appelé pour une cible
confirmable. Aucun ancien chemin documentaire produit à remplacer n'existait.

La préparation démarre à construction de `DocumentPreparation`, avant le
payload. Étapes finies non répétables et contenu provider accepté seuls réarment
120 secondes. Première attente, send bloqué, read bloqué et contrôles SSE sont
couverts par un superviseur async indépendant ; les étapes synchrones sont
contrôlées avant/après. Le transport injecté doit fermer/abandonner promptement
toute attente et envoyer les octets figés sans retry ; son adaptateur HTTP
effectif et son raccord restent M4. Aucune deadline totale, TTL ou lease inventée.

#### Commandes et résultats hermétiques

Runner disponible et inspecté, sans pull : `fridadev-audit-py:latest`, image
`sha256:486a8afeb2f62c7906194d3e1fee839387e55753bcad365120d18306502fafdc`.
Les dépendances requises étaient déjà disponibles. Commande de la comparaison
ciblée ; baseline avec les onze premiers sélecteurs, final avec les quatorze :

```bash
docker run --rm --pull never --network none --read-only \
  --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
  --tmpfs /tmp:rw,nosuid,nodev --workdir /workspace/app \
  --entrypoint /usr/bin/env fridadev-audit-py:latest \
  -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
  EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid \
  SEARXNG_URL=https://search.invalid python -m unittest \
  tests.test_llm_client \
  tests.unit.chat.test_main_llm_reasoning \
  tests.unit.chat.test_chat_llm_flow \
  tests.unit.chat.test_chat_llm_flow_boundaries \
  tests.unit.runtime_settings.test_runtime_settings \
  tests.unit.runtime_settings.test_runtime_settings_validation \
  tests.unit.runtime_settings.test_runtime_settings_validation_boundaries \
  tests.unit.runtime_settings.test_runtime_settings_seed_bundles_and_plans \
  tests.unit.core.test_workspace_documents_ingestion \
  tests.unit.core.test_workspace_folder_documents \
  tests.unit.core.test_workspace_folders_contract \
  tests.unit.core.test_document_workshop_canonical_paths \
  tests.unit.core.test_document_workshop_admission \
  tests.unit.core.test_document_workshop_provider_progress
```

Sorties redirigées dans un répertoire temporaire de preuve hors checkout ; aucun
contenu brut ou secret n'est repris ici. Les runs M0 seuls utilisent les trois
derniers sélecteurs et n'ont pas besoin des trois URL synthétiques de voisins.

| Exécution réellement observée | Résultat et qualification |
| --- | --- |
| Baseline avant patch, onze modules | 234/234, 0,185 s, exit 0. |
| RED canonical/paths avant interfaces | 15 échecs, exit 1 : rouge du contrat M0 absent, aucune régression produit existante. |
| GREEN canonical/paths | 15/15, 0,145 s, exit 0. |
| RED admission avant interface | 9 échecs, exit 1 : interface absente. |
| GREEN admission | 9/9, 6,199 s, exit 0. |
| RED lecteur/progression avant interface | 22 échecs, exit 1 : interface absente. |
| GREEN lecteur/progression | 22/22, 0,385 s, exit 0. |
| Contre-cas adverses ajoutés | 51 tests, trois erreurs de type sur champs non hashables ; garde de type corrigée sans affaiblir les tests. |
| GREEN M0 + mêmes voisins | 285/285 = 51 M0 + 234 voisins, 6,821 s, exit 0. |
| Revue indépendante, M0 avant corrections | 51/51, 6,912 s, exit 0 ; probes supplémentaires découvrant deux findings importants. |
| RED des findings de revue | Trois tests, dix échecs en sous-cas, 0,065 s, exit 1 : usages partiels/incohérents et séparateurs Unicode. |
| GREEN de ces trois tests | 3/3, 0,061 s, exit 0. |
| Final après corrections, mêmes voisins | 288/288 = 54 M0 + 234 voisins, 7,288 s, exit 0. Aucun échec, erreur ou skip. |

Contre-cas exercés : 10 000/10 001 mots ; 75 000/75 001 points de code indépendants,
français décomposé et hors BMP ; totalité titres/cellules/spans/liens ; schéma et
JSON fermés, données intactes ; source synthétique >20 pages entière ; mêmes
estimations que token_utils sur espaces/ponctuation/Unicode ; ajout réel de
sources/métadonnées et adaptateur de schéma ; compteur absent/erroné/mutateur ;
mutation caller après mesure ; JSON complet mais length, stop/DONE manquants,
vide/refus/erreur/contexte/usages invalides, contrôle ou raisonnement seuls ;
progrès utiles pendant 357 secondes virtuelles, inactivité exacte à 120,
keepalives continus, lecture/ouverture bloquées, annulation, résultat tardif et
fermeture ; chemins 8/9 niveaux, 180/181 points de code, 255/256 octets,
1 024/1 025 octets préfixe inclus, extension et français préservés,
traversées/encodages/confusables refusés ; pages 1/20/21 et preuves invalides.

Les six modules sont nouveaux, inactifs et consommés seulement par leurs tests :
aucune primitive commune ou route du chat modifiée. Clôture proportionnée par
M0 et les mêmes 234 voisins avant/après ; aucune découverte générale ni
comparaison différentielle complète supplémentaire nécessaire. Les tests ne
dépendent ni d'un secret, de DB opérateur, de réseau ni d'un téléchargement et
ne déduisent aucun comportement live de fournisseur, DAV ou Writer.

#### Contre-audit et frontière de livraison

Contre-audit indépendant effectué en lecture seule sur tout le lot, avec
rejeu M0 et probes hermétiques. Deux findings importants reproduits et corrigés
dans une passe causale ; aucun Critical ni Minor distinct, aucun finding M0
vivant laissé ouvert :

| Finding | Correction et preuve |
| --- | --- |
| Dépassement connu accepté sans total_tokens ou avec total incohérent | Contrôle du total et de la borne déductible prompt + max(completion, reasoning), sans double compte ni invention du total absent ; RED/GREEN via lecteur non-stream et usages SSE répartis. Seuil exact 400 000 accepté. |
| U+2216/U+29F9 et U+2028/U+2029 admis dans un nom confirmable | Refus ciblé de ces séparateurs et catégories Zl/Zp ; RED/GREEN, témoins français admissibles et octets originaux conservés. |

Registre de contre-audit : enveloppe technique 1 Mio décidée explicitement,
aucune borne produit cachée ; messages/schema figés inclus dans l'estimation ;
callable partagé, aucune fausse exactitude ni réserve de raisonnement doublée ;
sanitizer upload absent du resolver ; superviseur bloqué/keepalives/résultat
tardif éprouvé ; aucun test supprimé, affaibli ou désactivé ; aucun ancien
chemin documentaire actif, pas de duplication du comptage/renderer ; voisins
préservés et graphes de callers isolés ; aucun contenu/secret/log ajouté ;
roadmap/contrat/hub synchronisés ; aucune capacité hors M0.

Comportements examinés puis laissés aux lots décidés, sans être des findings M0
omis : transport HTTP réel, interruption des sockets et plafonds réseau (M4) ;
assemblage/fraîcheur des sources produit et transactions/concurrence durable
(M1–M7) ; collisions et préconditions/mutations DAV (M2/M5/M7) ; pagination,
rendu et fidélité Writer (M8–M10). L'exactitude fournisseur de l'estimation et
le comportement OpenRouter live sont exclus par le recadrage ; aucune garantie
n'en est déduite. Le mandat autorise le commit/push de la branche, pas un merge
ou un déploiement ; alignement distant final à constater après push.

M0 ne raccorde pas `/api/chat` ou UI, ne crée ni contexte produit, table/migration,
claim, pending, reçu, client d'écriture ou renderer. À la clôture M0, M1 restait
non commencé ; son exécution est décrite ci-dessous. Les transactions/contexte
appartiennent à M1–M7, la pagination
et les binaires effectivement rendus à M8–M10. Code publiable sur branche dédiée
seulement : aucun merge main, déploiement ou activation produit.

### M1 — Menu Fichier et contexte explicite

**Objectif :** entrée commune dès le début, upload préservé.
**Dépendances :** M0 pour les interfaces d'admission et de progression.
**Fichiers :** app.js, index.html, chat_active_documents.js, contrôleur atelier,
routes/contexte documentaire.
**Interface :** contexte serveur editing et menu à deux choix.
**Propriétaire :** Celebrimbor.

- [x] Rouge causal : ajout ouvre une fois le picker/upload ; atelier n'appelle ni
  modèle ni écriture DAV.
- [x] Tests ciblés et voisins : DOM menu, active-documents, soumission canonique,
  desktop/mobile ; prouver binding réel change, pas uniquement callback isolé.
- [x] Projeter `editing` et les capacités réelles ; préparation indisponible, sans
  aperçu, progression ou annulation de job inventées, garde canonique conservé.
- [x] Faux verts : picker callback isolé sans listener change réel, bureau seul
  testé, ancienne action upload masquée par le menu ou second binding mobile.
- [x] Interdire deuxième input, listener mobile concurrent, perte drag-and-drop et
  autorité d'écriture via checkbox de lecture.
- [x] Synchroniser UX/atelier ; parcours synthétiques, aucun upload live nécessaire.
- [x] Activation atelier différée ; aucun déploiement requis pour fermer les tests.
- [x] Fermer lorsque les deux entrées utilisent leurs bonnes autorités et que
  l'upload conserve toutes ses capacités.

#### Exécution M1 du 4 octobre 2026

Mandat distinct : menu et contexte explicite `editing`, tests/docs/contre-audit,
commit/push M1 uniquement. Racine revalidée `/opt/platform/fridadev`. Départ propre :
M0 HEAD = upstream = distant `3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a`,
parent/main/origin-main/distant `e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb`,
divergence `0/0`. M1 absent localement et distant. Avant toute édition :

```bash
git switch -c FridaV1-Document-Workshop-M1 3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a
git branch --show-current
git rev-parse HEAD
git status --short --branch
```

Branche M1 constatée, HEAD à M0, worktree propre. Aucun pull/stash/reset,
checkout supplémentaire, worktree, merge ou modification de M0/main.

Plan minimal : contrôleur menu/édition isolé, input conservé dans active-documents,
création/association existantes réutilisées, routes fines/service de scope/store
SQL limité. [Contrat M1](../../states/specs/frida-v1-document-workshop-m1-contract.md)
pour les formes, refus, garanties et frontières. Aucun besoin de nouveau calcul
de tokens ni de dépendance ; les six primitives M0 restent inchangées.

Composants livrés : `chat_document_workshop.js`, wiring `app.js`/`index.html`,
styles ciblés et ordre de scripts vérifié ; `document_workshop_routes.py`,
`document_workshop_context_service.py`, `document_workshop_contexts.py` et migration
`core/sql/document_workshop_contexts.sql`. Cette migration, exclue par le motif
historique `*.sql`, est ajoutée explicitement au lot, sans changer le gitignore.
Aucun bootstrap automatique de table à l'import/startup ; aucune DB opérateur
initialisée. Son application runtime exige une livraison ultérieure autorisée.

Un seul menu à deux choix, input multiple/change et drag-and-drop conservés.
L'ancien clic direct picker est retiré du contrôleur d'upload, son render conserve
le bouton. `newThread` expose réussite/identité et une garde d'activation tardive ;
création sans répertoire suivie d'un choix et d'une association **explicites**,
sans MKCOL ni réaffectation à l'ouverture. Cibles inventoriées `.md`/`.docx`
actives et liées, distinctes des sources cochées. Lecture exacte du lien via option
locale, défaut historique inchangé ; validation du chemin par M0, pas de copie.

POST/GET valident conversation/répertoire/cible côté serveur ; création SQL
revalide/verrouille ces ressources et fixe chemin/référence. GET refuse scope,
suppression ou identité distante changés. Les routes Flask et le service sont
éprouvés avec inventaires et store de contexte simulés. Une suite PostgreSQL
isolée vérifie séparément la migration, le store réel, le commit et la relecture
par une connexion indépendante ; un scénario y compose également le service
avec ce store. Ces preuves ne sont pas présentées comme un parcours
Flask–PostgreSQL de bout en bout.
État réel `editing`, `prepare=false`, pas de préparation, aperçu, progression,
`pending`, reçu, claim ou annulation fictive. Gardes frontend canonique et serveur
`document_context_id` placés avant les effets du tour ; sortie locale explicite.

**Runners revalidés et commandes reproductibles.** Host Node `20.19.2`, package
Playwright existant `1.59.1`, Chromium cache `chromium-1217`. Preuves dans l'image
existante `mcr.microsoft.com/playwright:v1.54.0-jammy`, Node `22.17.0`, ID
`sha256:55dfaaa282c98d5f4d328676e36eca5203b6494b97d9ef3ba0608d9e939e9523`,
avec package/cache du checkout déjà disponibles. Python :
`fridadev-audit-py:latest`, ID
`sha256:486a8afeb2f62c7906194d3e1fee839387e55753bcad365120d18306502fafdc`.
Pas de téléchargement/installation ; mounts checkout et cache en lecture seule,
rootfs readonly, temporaires tmpfs, environnement vidé, réseau Docker `none`.
Le serveur statique Playwright reste en loopback **dans** le conteneur isolé.
L'unshare réseau hôte était indisponible ; ce runner Docker conserve l'isolation.

Invocations utilisées (stdout/stderr conservés seulement sous
`/tmp/fridadev-m1-proof`, jamais copiés en documentation) :

```bash
m1_node() {
  docker run --rm --pull never --network none --read-only \
    --tmpfs /tmp:rw,nosuid,nodev \
    --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
    --mount type=bind,src=/home/tof/.cache/ms-playwright,dst=/proof/browsers,readonly \
    --workdir /workspace --entrypoint /usr/bin/env \
    mcr.microsoft.com/playwright:v1.54.0-jammy \
    -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp \
    PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node --test "$@"
}
m1_python() {
  docker run --rm --pull never --network none --read-only \
    --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
    --tmpfs /tmp:rw,nosuid,nodev --workdir /workspace/app \
    --entrypoint /usr/bin/env fridadev-audit-py:latest \
    -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
    EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid \
    SEARXNG_URL=https://search.invalid python -m unittest "$@"
}
m1_node_neighbors=(
  app/tests/unit/frontend_chat/test_active_documents_module.js
  app/tests/unit/frontend_chat/test_canonical_chat_submission.js
  app/tests/unit/frontend_chat/test_lot9_load_order_golden.js
  app/tests/unit/frontend_chat/test_threads_folder_binding_module.js
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js
  app/tests/unit/frontend_chat/test_workspace_folders_module.js
  app/tests/unit/frontend_chat/test_threads_list_renderer_module.js
)
m1_browser_neighbors=(
  app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
)
m1_python_neighbors=(
  tests.test_server_active_documents_contract
  tests.test_server_workspace_folders_contract
  tests.test_server_chat_route_transport_contract
  tests.test_server_chat_conversation_id_contract
  tests.test_server_chat_document_integrity_contract
  tests.integration.frontend_chat.test_frontend_chat_contract
  tests.unit.core.test_workspace_folders_contract
  tests.unit.chat.test_chat_llm_flow
  tests.unit.chat.test_chat_llm_flow_boundaries
  tests.unit.chat.test_chat_stream_control
  tests.unit.core.test_document_workshop_canonical_paths
  tests.unit.core.test_document_workshop_admission
  tests.unit.core.test_document_workshop_provider_progress
  tests.unit.core.test_workspace_documents_ingestion
)
m1_node "${m1_node_neighbors[@]}"
m1_node "${m1_browser_neighbors[@]}" \
  app/tests/integration/frontend_browser/test_frontend_browser_document_workshop.js
m1_python "${m1_python_neighbors[@]}" \
  tests.test_server_document_workshop_contexts_contract
```

**Comparaison avant/après complète sur ces arbres utiles.** Avant patch : Node
66/66 (`0,175 s`), navigateur 45/45 (`31,963 s`), Python 195/195 (`13,675 s`)
sans ingestion. La lecture exacte touche ensuite le getter partagé : ajout des
29 voisins ingestion, baseline élargie 224/224 (`15,495 s`, code 0).
Pour cette extension, les seuls fichiers de frontière modifiés sont projetés depuis
`git show 3eb2e34a:<fichier>` dans le même checkout readonly du conteneur ; aucun
second checkout ni changement de branche. Même runner, fixtures et sélecteurs.
Après : Node 69/69 (`0,158 s`), navigateur 56/56 (`36,230 s`), Python 232/232 (`15,688 s`),
codes 0, zéro skip. Les 54 preuves M0 sont incluses et vertes. Pas de suite générale
répétée : les voisins sélectionnés exercent transport, streaming, final locks,
persistance, intégrité documentaire, conversation/folder/upload et sérialisation
historique réellement partagés ; les paramètres du chat normal ne changent pas.

**SQL réel isolé**, image locale `postgres:16-alpine`, PostgreSQL `16.12`, ID
`sha256:87e04d274d186c7331d0e13c7c90c8b9f63b0d7ae94476c98a229a94d62c9745`.
Base/utilisateur synthétiques `m1proof`, aucun DSN opérateur. Exemple exact de
préparation retenue, après adaptation de l'essai initial de socket personnalisé
incompatible avec l'entrypoint de cette image :

```bash
mkdir -p /tmp/fridadev-m1-proof/pg-socket
chmod 777 /tmp/fridadev-m1-proof/pg-socket
docker run -d --name fridadev-m1-proof-pg --pull never --network none --read-only \
  --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev --tmpfs /tmp:rw,nosuid,nodev \
  --mount type=bind,src=/tmp/fridadev-m1-proof/pg-socket,dst=/var/run/postgresql \
  -e POSTGRES_USER=m1proof -e POSTGRES_DB=m1proof \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16-alpine -c listen_addresses=
docker exec fridadev-m1-proof-pg pg_isready -h /var/run/postgresql -U m1proof -d m1proof
docker run --rm --pull never --network none --read-only \
  --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
  --mount type=bind,src=/tmp/fridadev-m1-proof/pg-socket,dst=/proof/sock,readonly \
  --tmpfs /tmp:rw,nosuid,nodev --workdir /workspace/app \
  --entrypoint /usr/bin/env fridadev-audit-py:latest \
  -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
  M1_PROOF_PG_SOCKET=/proof/sock \
  python -m unittest tests.integration.document_workshop.test_context_store_postgresql
docker stop fridadev-m1-proof-pg
docker rm fridadev-m1-proof-pg
```

5/5 (`0,527 s`), code 0, zéro skip : migration idempotente, commit/relecture par
connexion indépendante, FK et état fermé, recheck après modification SQL,
identité française/doubles espaces préservés sans changer le getter historique,
traversée du lien refusée. Données uniquement éphémères ; aucune installation ou
mutation plateforme/production. L'absence de socket en suite ordinaire entraîne
un skip explicite et ne vaut jamais preuve SQL.

**Rouges et faux verts.** Routes nouvelles absentes (POST 405), store absent
(import refusé), garde documentaire absent (trois provenances produisant déjà un
message/transport), menu monté absent (0 choix au lieu de 2), codes 1 sur baseline.
Le RED canonique final vérifie les effets immédiatement, sans promise pendante
utilisée comme preuve. Le premier essai browser attendait un thread sous un
répertoire replié : erreur de sélecteur requalifiée, remplacée par attente bootstrap
et parcours réel du répertoire. Le RED menu est ensuite reproduit avec les fichiers
M0 readonly. Le vrai clic a aussi détecté un ancien binding picker encore actif ;
retiré avant clôture. Une attente UI interceptée par le contrôle raisonnement a
fait corriger le placement du panneau, sans forcer les clics ni affaiblir le test.

**Contre-audit indépendant et corrections dans M1.** P2 : déplacement courant
changeait le scope mais n'invalidait l'atelier qu'après les inventaires ; PATCH
réussi/inventaire volontairement bloqué reproduit le panneau résiduel (`5,892 s`,
code 1). Notification immédiate avant refresh, puis GREEN. P3 : association
proposée après échec de création ; controls attendus disabled reproduits rouges
(`1,390 s`, code 1), garde UI et callback ajoutés, puis GREEN. Revalidation
indépendante des deux scénarios 2/2, code 0 ; suite M1 navigateur complète 11/11.
Aucun finding vivant retenu par ce contre-audit. Relance finale M1 11/11
(`9,757 s`, code 0, zéro skip) avec comptage des vrais bindings input/button
et vérification du focus/flèches/Home/Échap, sans modification du code produit.

Vérifications causales finales : unique picker/change, deux uploads ordonnés avant
libération du premier, erreur conservée puis drop/retrait ; bureaux clair/sombre
et téléphone avec les deux préférences, contrôles mobiles préservés, zéro erreur
JavaScript ; source cochée ≠ cible ; création échouée ≠ contexte ; double clic,
POST/GET/création et changement de répertoire différés ≠ rattachement tardif ;
modèle/DAV/client d'écriture à zéro dans les routes montées ; IDs/états/URL client
refusés ; brouillon/transcript/normal chat gardés ; SQL durable démontré hors mocks.
Aucune capacité préparation/confirmation/progression/annulation annoncée à tort.

Documentation synchronisée dans le contrat M1, active-documents, workspace-folders,
Documents ingestion et hub ; lien informatif dans Nextcloud folders. M0 reste
inchangé. Limites : aucune expérience live déduite des mocks, aucune activation,
migration opérateur, préparation M4 ou job d'annulation. À la clôture M1, M2 et
les suivants n’étaient pas commencés ; l’exécution M2 ci-dessous actualise ce statut.
M1 ferme menu/entrée et autorité du contexte `editing` avec gardes inactifs ; M2
reste responsable du navigateur distant, de l'adoption et de la lecture fraîche.

**Correction documentaire P3 du 4 octobre 2026 :** la description précédente
du harnais Flask omettait le store de contexte simulé (`Mock` et `self.saved`).
La distinction avec les cinq preuves PostgreSQL séparées est rétablie ci-dessus,
sans changement de code, de tests ou des résultats historiques. Livrée séparément
sur M1 par `c6f648badba96a60f1474db8d3f7404f97a2dda7`, parent
`8fb383b9aeb5cdb6f7f32338f60a57acdfa24ec5` ; branche, upstream et remote égaux,
worktree propre, avance/retard 0/0 vérifiés avant création de M2.

### M2 — Adoption et lecture distante ciblées

**Statut : P2-M2-01 corrigé sur code/preuves (comparaison historique 567/567),
après le succès historique 536/536 et G-R1–G-R4 Approved ; P2-M2-03 corrigé
séparément en frontend (594/594 historiques) ; P2-M2-02 corrigé séparément
sur les trois familles (679/679 historiques) ; P2-M2-04 corrigé sur le backend
(713/713 historiques), P2-M2-05 corrigé séparément sur le résumé (716/716) ;
livraison runtime ouverte.**
**Objectif :** intégrer un dépôt direct dans l'inventaire commun.
**Dépendances :** M0–M1, notamment gardes chemin et admission des sources.
**Fichiers :** liens Nextcloud, workspace_files_store, readers, client DAV,
service d'adoption et navigateur UI.
**Interface :** routes remote/adopt et lien identité/chemin/ETag.
**Propriétaire :** Celebrimbor ; Sauron seulement si contrat DAV manquant.

- [x] Rouge causal : même identité → même ID ; collision → refus ; adoption → zéro
  PUT/MKCOL/DELETE.
- [x] Tests ingestion/sélection/projections voisins ; changement listing/GET,
  identité différente avec même nom, réponse excessive et visibilité locale atomique.
- [x] Source >20 pages acceptée entière ; budget d'entrée complet appliqué sans
  troncature, y compris refus d'un fichier admissible seul dans un payload trop grand.
- [x] Faux verts exclus : vraies préconditions HTTP synthétiques, changements
  d'identité/ETag, listing 256/257 enfants et PostgreSQL réel.
- [x] Aucun scan récursif, polling, URL frontend exécutée ni origine Frida inventée.
- [x] Documents/fraîcheur et contrats vivants synchronisés ; quatre catégories
  d'adoption et publication SQL fichier/lien sur une seule transaction prouvées.
- [ ] Appliquer les migrations opérateur M1/M2, puis rebuild du seul service
  applicatif lors d'une livraison distinctement autorisée ; health/surface à prouver.
- [ ] Lecture DAV déployée ciblée sous GO distinct, artefact content-free ; aucune
  preuve live inférée des fixtures. M3–M10 et Z restent non commencés.

#### Exécution M2 du 4 octobre 2026

Checkout `/opt/platform/fridadev`, branche `FridaV1-Document-Workshop-M2`, créée
avant toute édition depuis M1 corrigé `c6f648badba96a60f1474db8d3f7404f97a2dda7`.
M0 `3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a` et main
`e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb` n'ont pas été modifiés.
La correction P3 M1 reste un commit distinct. Le contre-audit global a identifié
G-R1–G-R4, corrigés dans une vague bornée puis fermés par la contre-revue du
seul delta Approved. Le retour final porte le commit/push M2 et ses alignements.

Le [contrat M2](../../states/specs/frida-v1-document-workshop-m2-contract.md)
décrit les responsabilités livrées : lecteur DAV, extraction complète isolée,
service d'adoption, store transactionnel, lecture fraîche interne et contrôleur
UI existant. La roadmap reste l'unique spécification du chantier.

Navigation `PROPFIND Depth: 1` limitée à une collection explicitement ouverte,
XML 1 Mio plus détection, 256 enfants et self, source 40 Mio ; timeout réseau
local de 12 secondes par requête. Un GET `If-Match` entre deux observations
conditionnelles vérifie identité/version/taille/ETag et octets consommés.
`oc:fileid` canonique et scope serveur sont distincts du chemin, de l'ETag et du
SHA-256 observé. Références UUID opaques : FIFO 4 096, local au processus, sans
TTL ni promesse durable. Aucun href/URL client exécuté, redirect, scan ou retry.

Les gardes M0 partagés conservent Documents, 8 niveaux, 180 points de code et
255 octets UTF-8 par segment, 1 024 octets pour le chemin ; collection sans
extension fictive, sources TXT/MD/MARKDOWN/DOCX/ODT/PDF, formats produit inchangés.
Extraction binaire : Python `-I -B`, environnement nettoyé, 512 Mio mémoire,
20 secondes CPU, core dumps interdits, stderr jeté ; ZIP 64 Mio réellement
développés/4 096 membres, texte UTF-8 complet 40 Mio. Ces bornes ne changent ni
le watchdog M0 ni les durées editing/pending. Compatibilité conservatrice :
contenu DOCX/ODT/PDF non couvert ou omis de façon détectable → refus, aucun OCR.
Texte brut exact ; espaces binaires selon extracteurs historiques, sans fidélité
universelle de mise en page. Après G-R2/G-R3, répétitions textuelles ODT non
représentées et DOCX `mc:AlternateContent` sont refusés entièrement ; cellules
ordinaires/unaires et répétitions ODT vides restent admises. Aucun moteur
ODF/OOXML ajouté. Liens PDF passifs conservés comme données sans fetch.

Migration explicite `workspace_document_adoption.sql`, jamais au startup :
colonnes nullable chemin/collision/fileid/scope/ETag/observation/SHA-256/origine,
unicité identité incluant tombstones, unicité chemin des liens liés et contrainte
d'identité canonique ; `target_remote_identity` enrichit les contextes M1.
Même identité → même ID, collision → refus ; ancien lien enrichi seulement après
preuve du chemin et égalité des octets complets. Nouveau fichier externe, jamais
Frida par déduction. GET service et INSERT M1 gardent chemin complet/identité.
Le DELETE historique refuse les liens enrichis avant son writer par basename.

Cache préparé sous UUID immuable avant publication SQL ; fichier/lien committés
sur une transaction avec revalidation/verrous du scope. Pas d'atomicité distribuée
filesystem/SQL. Échec certain : tentative de retrait du seul nouveau cache possédé
(un échec filesystem peut laisser un orphelin). Commit incertain : cache conservé,
`document_adoption_commit_unknown`, aucune répétition automatique. Anciennes
révisions conservées, sans purge automatique ; aucune compensation DAV.

La lecture fraîche exige la version persistée, refuse son ETag invalide avant
transport, compare identité/taille/SHA-256 puis revalide le scope local. Elle ne
cherche pas une source déplacée et ne remplace pas la lecture cache du chat
normal. Une nouvelle version exige une adoption explicite. La preuve composée
adopte/lit un PDF synthétique réel de 21 pages puis utilise le garde M0 inchangé
et `token_utils.estimate_tokens` sur prompt, dialogue, toutes sources/métadonnées
et instructions/schema canonical envoyés. `E + 24 000 <= 400 000`, réserve unique
raisonnement compris ; un fichier admissible seul est refusé avec le reste du
payload trop grand. Aucun nouvel appel, compteur, modèle, paramètre ou transport M4.

UI paresseuse dans le même DOM et menu Fichier : quatre catégories distinctes,
collections via références opaques, inventaire commun et aucune source/cible
choisie automatiquement. Cible antérieure conservée après GET serveur valide.
Les gardes de génération/scope M2 empêchaient ses propres publications tardives,
mais ne coordonnaient pas les lecteurs historiques ; P2-M2-01 corrige cette course
chez le propriétaire de l’inventaire, comme décrit ci-dessous.
L'obligation de réconcilier les seuls IDs de répertoires affectés survit aux sorties
locales, jusqu'à une lecture courante explicitement demandée et réussie ; aucun
second inventaire/cache, polling ou replay POST. `editing`/`prepare:false` et
soumission canonique interdite dans l'atelier restent inchangés. G-R1 ajoute les
raisons fermées `document_remote_identity_invalid`, `document_remote_version_invalid`
et `document_remote_size_invalid` (422), propagées dans le listing et le refus
d'adoption. La table UI fixe distingue également format, limite, OCR, extraction,
changement/disparition et commit incertain, dans lignes/navigation/adoption.
Aucune raison brute, clé héritée ou HTML serveur rendu ; les inconnus gardent un
fallback fixe. Une incompatibilité permanente n'invite plus à actualiser en vain.
Les conditions d'admission, générations, sélections et interdiction du retry restent inchangées.

#### Preuves finales différentielles et portée

Baseline utile depuis `c6f648ba` : Python 290/290 en 15,648 s, plus voisin OCR
5/5 en 0,001 s ; Node 69/69 en 0,304835 s plus frontières sidebar 10/10 en
0,083262 s ; navigateur 56/56 en 35,242050701 s ; SQL M1 5/5 en 0,523 s.
Tous exit 0, sans skip. Le voisin OCR a été identifié après les edits des deux
getters/serializers : leurs seuls blobs immuables `c6f648ba` ont été montés en
lecture seule aux chemins originaux, mêmes tests/image/runner, sans autre checkout.
Les anciens comptes 362/M0 98 ne sont pas la baseline M2.

La première comparaison après les trois gates initiaux a réellement passé
**528/528** : Python 340/340 en 18,371 s ; SQL 27/27 en 17,787 s ; Node 80/80
en 0,315777548 s ; navigateur 81/81 en 40,963524759 s, chaque exit 0 sans skip.
Elle reste une preuve historique antérieure aux faux succès G-R2/G-R3 et aux
lacunes G-R1/G-R4 ; elle ne ferme pas ces cas nouvellement établis. Leur
correction justifie une unique reprise finale des mêmes familles utiles, avec
le module navigateur de raisons ajouté ; aucune découverte générale répétée.

| Suite finale après contre-audit | Résultat | Durée | Composition |
| --- | --- | --- | --- |
| Python | 344/344 | 35,973 s | 20 modules de baseline, voisin OCR et 3 modules M2 ; +49 cas M2. |
| PostgreSQL réel isolé | 27/27 | 17,138 s | 22 M2 et 5 M1 ; mêmes sélecteurs, migration, commits, concurrence, rollback et lecture indépendante. |
| Node | 80/80 | 0,506575391 s | 7 modules initiaux et frontières sidebar ; +1 cas de normalisation. |
| Chromium monté | 85/85 | 46,271549201 s | 4 modules initiaux, adoption et raisons M2 ; +29 cas M2. |

Total final **536/536**, baseline utile **435**, soit **101** nouvelles preuves ;
chaque commande exit 0, aucun échec, skip ou annulation. Aucun code ni fixture
modifié après cette comparaison. Le manifeste du lot passe de 44 à 45 fichiers
par l'ajout du module navigateur des raisons. Seule cette documentation est
ensuite réconciliée avant contre-revue finale du delta.
Les diagnostics préexistants restent visibles : baseline/final conservent les
mêmes familles/comptes `ERROR frida.log_store` 264, `WARNING frida.conv` 17,
`ERROR frida.server` 3 ; INFO bootstrap attendus également conservés. Cela ne
signifie pas des logs vides ou sans Warning/Error, ni un nouveau logging produit.

Runners temporaires réellement exécutés : images existantes `--pull never`,
`--network none`, rootfs et checkout read-only, `/tmp` tmpfs, entrée `/usr/bin/env -i`,
HOME temporaire et aucun bytecode. Python : `fridadev-audit-py:latest`
(image `486a8afeb2f6`) ; Node/Chromium :
`mcr.microsoft.com/playwright:v1.54.0-jammy` (image `55dfaaa282c9`, cache navigateur
existant read-only) ; PostgreSQL 16 Alpine (image `87e04d274d18`) sur socket Unix
isolé, seules variables de socket de preuve, aucun DSN opérateur. Pas d'installation,
download ou `.env` lu. L'absence de `app/.env` (fichier et symlink) a été vérifiée
sans lecture de contenu pendant cette session. C'est une **précondition de
reproduction** : `env -i` ne masque pas un fichier dotenv dans le checkout monté.
Si cette précondition échoue, arrêter la preuve sans charger de configuration
opérateur. Les images et le cache navigateur doivent déjà être disponibles et
correspondre aux versions ci-dessus ; aucune installation ou récupération implicite.

Les trois wrappers scratch utilisés sont retranscrits ci-dessous en fonctions
Bash avec les mêmes options, arguments et environnement. Le sous-shell de chaque
fonction conserve l'effet de `set -euo pipefail` du script d'origine. Python et
SQL refusent explicitement un dotenv présent ou symlink avant Docker ; la
précondition ne dépend plus d'un `test` isolé au niveau du shell appelant. Après
cleanup du scratch, définir ces fonctions dans le shell de preuve suffit pour
les invocations qui suivent ; aucun fichier runner permanent n'est nécessaire.

```bash
m2_python() (
  set -euo pipefail
  if test -e /opt/platform/fridadev/app/.env || test -L /opt/platform/fridadev/app/.env; then
    printf "%s\n" "Precondition failed: checkout dotenv present." >&2
    exit 1
  fi
  docker run --rm --pull never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly --workdir /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid python -m unittest "$@"
)
m2_node() (
  set -euo pipefail
  docker run --rm --pull never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly --mount type=bind,src=/home/tof/.cache/ms-playwright,dst=/proof/browsers,readonly --workdir /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node --test "$@"
)
m2_sql() (
  set -euo pipefail
  if test -e /opt/platform/fridadev/app/.env || test -L /opt/platform/fridadev/app/.env; then
    printf "%s\n" "Precondition failed: checkout dotenv present." >&2
    exit 1
  fi
  docker run --rm --pull never --network none --read-only --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly --mount type=bind,src=/tmp/fridadev-m2-proof/pg-socket,dst=/proof/sock,readonly --tmpfs /tmp:rw,nosuid,nodev --workdir /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 M1_PROOF_PG_SOCKET=/proof/sock M2_PROOF_PG_SOCKET=/proof/sock EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid python -m unittest "$@"
)
```

Pour PostgreSQL, reprendre la préparation isolée M1 avec les seuls noms de
conteneur/socket M2 ci-dessous. Base/utilisateur restent synthétiques `m1proof` ;
le runner M2 expose **les deux** variables `M1_PROOF_PG_SOCKET` et
`M2_PROOF_PG_SOCKET`, vers le même socket isolé. Le chemin socket doit être absent
et le nom de conteneur libre avant préparation ; ne pas réutiliser une DB ou un
socket existant. Le bloc unique refuse explicitement dotenv/socket présents,
conteneur existant ou impossibilité d'établir son absence, avant mkdir, démarrage
Docker et readiness. Seule la requête de liste de conteneur nécessaire à cette
preuve précède ces mutations ; aucun arrêt ne repose uniquement sur `errexit`.
Ces commandes documentent la reproduction ; la passe
documentaire n'a démarré aucun conteneur ni relancé de test.

```bash
(
  set -euo pipefail
  if test -e /opt/platform/fridadev/app/.env || test -L /opt/platform/fridadev/app/.env; then
    printf '%s\n' 'Precondition failed: checkout dotenv present.' >&2
    exit 1
  fi
  if test -e /tmp/fridadev-m2-proof/pg-socket || test -L /tmp/fridadev-m2-proof/pg-socket; then
    printf '%s\n' 'Precondition failed: proof socket path already exists.' >&2
    exit 1
  fi
  if ! m2_existing_containers="$(docker container ls -a --filter 'name=^/fridadev-m2-proof-pg$' --format '{{.Names}}')"; then
    printf '%s\n' 'Precondition failed: proof container absence is unverified.' >&2
    exit 1
  fi
  if test -n "$m2_existing_containers"; then
    printf '%s\n' 'Precondition failed: proof container already exists.' >&2
    exit 1
  fi
  mkdir -p /tmp/fridadev-m2-proof/pg-socket || exit 1
  chmod 777 /tmp/fridadev-m2-proof/pg-socket || exit 1
  docker run -d --name fridadev-m2-proof-pg --pull never --network none --read-only \
    --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev --tmpfs /tmp:rw,nosuid,nodev \
    --mount type=bind,src=/tmp/fridadev-m2-proof/pg-socket,dst=/var/run/postgresql \
    -e POSTGRES_USER=m1proof -e POSTGRES_DB=m1proof \
    -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16-alpine -c listen_addresses= || exit 1
  docker exec fridadev-m2-proof-pg pg_isready -h /var/run/postgresql -U m1proof -d m1proof || exit 1
)
```

Attendre le succès de `pg_isready` avant la commande SQL, puis exécuter les deux
modules SQL en série dans cette invocation unique : ils réinitialisent le même
schéma de preuve. Ne jamais les lancer en parallèle. Les invocations suivantes
correspondent à la comparaison finale après G-R1–G-R3, par les wrappers scratch
équivalents ; elles conservent tous les voisins de la première comparaison et
ajoutent le module de raisons navigateur. La passe documentaire ne les relance pas.

```sh
m2_python \
  tests.test_server_active_documents_contract \
  tests.test_server_workspace_folders_contract \
  tests.test_server_chat_route_transport_contract \
  tests.test_server_chat_conversation_id_contract \
  tests.test_server_chat_document_integrity_contract \
  tests.integration.frontend_chat.test_frontend_chat_contract \
  tests.unit.core.test_workspace_folders_contract \
  tests.unit.chat.test_chat_llm_flow \
  tests.unit.chat.test_chat_llm_flow_boundaries \
  tests.unit.chat.test_chat_stream_control \
  tests.unit.core.test_document_workshop_canonical_paths \
  tests.unit.core.test_document_workshop_admission \
  tests.unit.core.test_document_workshop_provider_progress \
  tests.unit.core.test_workspace_documents_ingestion \
  tests.test_server_document_workshop_contexts_contract \
  tests.unit.core.test_workspace_folder_documents \
  tests.unit.core.test_workspace_file_selection_prompt \
  tests.unit.core.test_active_document_text_extraction \
  tests.unit.core.test_document_upload_limits \
  tests.unit.core.test_workspace_nextcloud_compensation_etag \
  tests.unit.core.test_workspace_file_ocr_service \
  tests.unit.core.test_workspace_document_read_client_m2 \
  tests.unit.core.test_workspace_document_source_extraction_m2 \
  tests.unit.core.test_workspace_document_adoption_m2
```

```sh
m2_node \
  app/tests/unit/frontend_chat/test_active_documents_module.js \
  app/tests/unit/frontend_chat/test_canonical_chat_submission.js \
  app/tests/unit/frontend_chat/test_lot9_load_order_golden.js \
  app/tests/unit/frontend_chat/test_threads_folder_binding_module.js \
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js \
  app/tests/unit/frontend_chat/test_workspace_folders_module.js \
  app/tests/unit/frontend_chat/test_threads_list_renderer_module.js \
  app/tests/unit/frontend_chat/test_workspace_folder_sidebar_boundaries.js
```

```sh
m2_node \
  app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_workshop.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption_reasons.js
```

```sh
m2_sql tests.integration.document_workshop.test_adoption_postgresql tests.integration.document_workshop.test_context_store_postgresql
```

Après les preuves SQL, retirer uniquement le conteneur et le socket de preuve
possédés ; les données PG sont sur tmpfs. Le reste du scratch se retire après
lecture et conservation des faits dans la documentation.

```bash
docker container stop --time 10 fridadev-m2-proof-pg
docker container rm fridadev-m2-proof-pg
rmdir /tmp/fridadev-m2-proof/pg-socket
```

Portée des preuves, sans confusion entre couches :

- M1 Flask historique : inventaires **et** store contexte `Mock`/`self.saved` ;
  cinq preuves PostgreSQL séparées, comme rétabli par P3.
- M2 transport : vrai urllib/HTTP vers loopback synthétique dans le conteneur
  sans réseau externe ; méthodes, Depth, If-Match et octets effectivement vérifiés.
- M2 SQL : schéma de preuve minimal, migrations réelles répétées, stores réels ;
  `_db_conn` de contexts/workspace_files/workspace_folders/adoption raccordé à
  PostgreSQL isolé, stockage temporaire. Résumé conversation substitué par une
  fonction du test qui lit réellement sa ligne SQL.
- Cas Flask M2 composé : `load_server_module_for_tests` neutralise le bootstrap
  DB/settings/secrets ; modules serveur remplacés par ces modules réels raccordés ;
  factory `from_env` remplacée par le vrai lecteur configuré vers le serveur
  synthétique. `app.test_client()` exerce GET remote, POST adopt et GET files,
  avec publication fichier/lien SQL réelle. Aucun startup ni E2E production prouvé.
- Navigateur : vrai index/app/DOM/Chromium avec `fetch` simulé ; clics, menu,
  upload, sélection, concurrence et gardes inspectés. Géométries 1280×900 et
  390×844, captures desktop clair et téléphone ; deux thèmes et deux compositions
  exercés. Aucune recette matérielle Safari/iPhone, paysage/clavier ou DAV live.

#### Dispositions du contre-audit et limites

Les trois gates d'implémentation initiaux ont reçu un re-review **Approved**.
Le contre-audit global suivant a conclu **Needs fixes** : 0 Critical, 3 Important
(G-R1–G-R3), 1 Minor (G-R4). Une seule vague bornée a corrigé ces quatre findings ;
la contre-revue finale du delta G-R1–G-R4 a conclu historiquement **Approved** :
0 Critical, 0 Important, 0 Minor ouverts dans cette revue. Les findings
indépendants du 5 octobre sont consignés dans la section P2-M2-01 ci-dessous
et ne sont pas couverts par cette décision historique. Elle a vérifié les 12 fichiers du delta, les 45 empreintes du
lot et les 36 empreintes du code/tests exécutés, sans seconde revue générale.
Les rouges causaux précèdent
leurs corrections ; les erreurs initiales de fixtures ne sont pas présentées
comme régressions produit. Les résultats finaux incluent les corrections code/UI,
sans masquer les diagnostics ni prétendre que 528/528 fermait les nouveaux cas.

| Finding | Disposition et preuve retenue |
| --- | --- |
| T1 contrôles locaux avant revue | Corrigés : href IPv6 malformé, racine/texte DOCX non couverts, images PDF inline/XObject et XML auxiliaire vide. RED 28 tests / 3 assertions et 1 erreur, 6,590 s, puis deux probes 1/1 rouges en 0,215/0,529 s ; GREEN voisin 98/98, 6,892 s avant le round indépendant, puis final ci-dessus. |
| T1 R1 DOCX, R2 ODT, R3 PDF, R4 href | Corrigés : éléments DOCX omis, texte ODT hors corps, actions PDF actives, query/fragment/userinfo vides. RED 35 tests / 28 sous-cas en échec, 9,370 s, exit 1 ; complément ODT 1/1 rouge, 0,403 s ; GREEN 35/35, 9,269 s, exit 0. R4 Minor explicitement fermé. |
| T2 collision ordre/statut OCR | Corrigés, RED 7 tests / 2 assertions, 0,682 s, exit 1 ; inclus dans SQL et Python finaux. |
| T2 fallback DELETE TypeError | Corrigé par retrait du retry sans métadonnées ; RED 1 test / 2 sous-cas, 0,001 s, exit 1 ; GREEN voisin 109/109, 0,496 s, puis final ci-dessus. |
| T2 R1 ETag enregistré | Corrigé avant configuration/transport ; RED 2 tests / 10 sous-cas, 0,189 s, exit 1 ; GREEN 10/10, 0,874 s et SQL ciblé 4/4, 11,324 s, exit 0. |
| T2 R2 Minor INFO bootstrap | Requalifié et accepté comme diagnostic hérité attendu, non supprimé ; aucune extension de collecte ni suppression de logs. |
| W-BYTECODE | Hypothèse invalidée : snapshot initial déjà `-I -B`, probe des vrais flags positif ; probe `-I` seul ne représentait pas le code exécuté. |
| Nettoyage cache sur échec certain | Formulation absolue requalifiée après lecture de `_discard` : `OSError` d'unlink est ignorée, donc résidu orphelin possible sans fichier SQL visible. Risque local explicite accepté dans la documentation ; aucune garantie de purge, aucun GC ajouté. |
| T3 REREAD / INVENTORY / SIBLINGS | Corrigés : refus de cible visible, réconciliation explicite et frères conservés ; rouges chacun 1/1, respectivement 1,082/1,104/0,961 s, exit 1 ; inclus dans GREEN navigateur final. |
| T3 R1 perte de réconciliation tardive, R2 fixture racine | Corrigés, y compris le Minor : RED 4/4 assertions, 3,661 s, exit 1 ; GREEN 25/25, 20,904 s, exit 0. Obligation conservée après sortie et références racine/parent fidèles. |
| G-R1 — motifs API/UI perdus | Corrigé : identité/version/taille en codes fermés, explications fixes dans lignes/navigation/adoption et fallback sûr. Backend RED 3 tests / 26 sous-cas, 0,853 s, exit 1 → GREEN 11/11, 0,914 s ; UI RED 4/4 assertions, 2,674 s, exit 1 → GREEN 29/29, 21,828 s ; raffinement des seuls statuts HTTP de fixture puis 4/4, 9,293 s, exits 0. Les 536 finaux incluent cette dernière fixture. Contre-revue du delta Approved. |
| G-R2 — occurrences ODT répétées perdues | Corrigé : refus entier des cellules/lignes textuelles répétées non représentées ; voisins ordinaires/unaires/vides préservés. RED commun G-R2/G-R3 : 3 tests / 3 assertions, 0,424 s, exit 1 → GREEN ciblé 7/7, 0,891 s, exit 0. Aucun développement ODF ajouté. Contre-revue du delta Approved. |
| G-R3 — alternatives DOCX concaténées | Corrigé : refus de `mc:AlternateContent` avant extraction, sans sélection de branche ni changement du lecteur historique ; mêmes preuves causales ci-dessus, puis comparaison finale 536. Contre-revue du delta Approved. |
| G-R4 — préconditions Bash non bloquantes | Corrigé dans les fonctions Python/SQL et le bloc PG unique : refus explicites dotenv/socket/conteneur avant mutation, y compris symlinks et échec de vérification. Probes mécaniques isolées décrites ci-dessous ; aucune suite/DB relancée. Minor explicitement fermé par la contre-revue du delta Approved. |


Les premiers rouges d'interfaces absentes (lecteur 19/19 assertions, service 5/5,
SQL 9/9) établissent les nouvelles capacités autorisées, pas une régression
préexistante. Les refus nouveaux conservateurs de formats sont documentés au
contrat M2. Aucun finding de ces gates n'est laissé sans correction, invalidation
ou requalification. Les quatre findings globaux ont une correction et des preuves
explicites ; leur contre-revue limitée au delta les ferme tous, sans nouvelle
revue générale ni extension du lot.

Preuve G-R4 distincte des 536 tests applicatifs : le probe de revue du bloc
initial terminait exit 0 malgré un premier `test` faux, donc sa précondition
n'était pas effective. Après correction, les trois corps de fonctions concordent
exactement avec les wrappers utilisés, dont Python/SQL renforcés ; `bash -n`
valide les sept blocs de commande sans les exécuter.

Une sonde mécanique lit ces blocs puis remplace en mémoire les seuls chemins
dotenv/socket par des sentinelles possédées sous un temporaire de preuve ;
Docker, mkdir et chmod sont des stubs qui enregistrent les appels. **14/14 cas,
0,046450 s, commande exit 0** : 11 refus attendus sortent 1 (fichier ou symlink
dotenv, socket fichier/répertoire/symlink, nom de conteneur existant, échec de
vérification de son absence) ; trois témoins sans obstacle sortent 0 et atteignent
les seules commandes simulées attendues. Aucun démarrage/mkdir/chmod après refus ;
les deux cas de vérification de conteneur n'effectuent que la liste simulée.
Zéro Docker réel, test applicatif ou PG, aucun `.env` opérateur créé/lu ;
sentinelles supprimées. Les six probes séparés des wrappers scratch par le parent
sont également verts ; ces vérifications ne sont pas ajoutées au total 536.

Après la première comparaison, puis de nouveau après les 27 preuves SQL finales
post-correction, le PostgreSQL possédé a réellement été arrêté (`stop --time 10`)
puis supprimé ; sa recréation intermédiaire utilisait les gardes explicites
dotenv/socket/nom, jamais une DB existante. À la fin de chaque exécution :
répertoire socket vérifié vide et retiré, aucun conteneur de ce nom restant.
Données PG en tmpfs détruites ; autres runners `--rm`. Après contre-revue
Approved et conservation des faits, le parent a retiré le scratch possédé
`/tmp/fridadev-m2-proof` (234 fichiers) et ses deux auxiliaires P3. Absence du
conteneur et du socket vérifiée avant ce retrait ; aucun temporaire de preuve
restant ni ressource de production nettoyée.

Limites ouvertes : migration DB opérateur, rebuild/health, comportement DAV
réel et canari de lecture ciblée. Caches anciens/incertains retenus ; références
et marqueurs de réconciliation locaux au processus ; aucune promesse de fidélité
bureautique universelle ni de transaction distribuée. M3–M10/Z non commencés,
préparation toujours indisponible. Aucune activation runtime, installation,
mutation distante, renderer ou appel modèle réel effectué dans M2.

#### Correction indépendante P2-M2-01 — 5 octobre 2026

**Disposition : corrigé ; lot borné arrêté après livraison Git dédiée.** Le parent
exact du correctif est M2 `24233ce86d2c02a4648b8b901258a533dce2f375`, initialement
HEAD = upstream = M2 distant, worktree propre et divergence `0/0`. `pwd` et
`git rev-parse --show-toplevel` confirment `/opt/platform/fridadev`. M1 `c6f648ba`,
M0 `3eb2e34a` et main `e3e0d19` sont revalidés par `git ls-remote --heads`.
Le retour final porte le nouveau hash, le push et l’alignement après livraison ;
aucun merge, changement de branche ou démarrage M3. La preuve du 4 octobre
536/536 et la revue G-R1–G-R4 demeurent historiques, sans prétendre couvrir ce P2.

**Cause et revalidation.** `chat_threads_sidebar.js` publiait les fichiers et
statuts depuis la lecture individuelle, et depuis deux setters remplaçant les
Maps après collecte globale. Le garde `isCurrent` M2 ne coordonnait pas les
requêtes historiques (upload, suppression, OCR et `syncAndRender`). Une réponse
capturée avant adoption pouvait ainsi restaurer l’ancien inventaire après sa
publication réussie. Les quatre probes de l’annexe, intégrés dans
`test_frontend_browser_document_inventory_publication.js`, reproduisent les deux
chemins réels : contrôles livrés avant adoption verts, réponses livrées après
adoption rouges. Deux contrôles conservent le fichier et une cible ; les deux
rouges observent fichier absent, zéro cible à la réouverture et **un seul POST**
d’adoption. La capture JSON précède l’attente ; aucune reconstruction du payload
après adoption, aucun sommeil arbitraire ni global d’audit livré au produit.

**Coordination retenue.** Le propriétaire garde ses seules Maps Files existantes.
Un token de requête opaque par répertoire coordonne tous leurs écrivains ;
`readWorkspaceFiles` est l’unique publication fichiers/statut, sans `await` entre
les deux. Le global réserve tous ses tokens avant les lectures séquentielles et
publie chaque résultat par cette même fonction. Les deux setters de remplacement
complet sont retirés : A déjà lu ne peut plus être réécrit par un batch retardé
par B, ni disparaître indirectement d’une Map reconstruite. Une lecture B ne
supersède pas A ; un B déjà supersédé avant son tour global ne fait aucun I/O.
Un epoch des rafraîchissements globaux refuse les anciennes listes de répertoires
avant publication et arrête leurs étapes tardives. `saveWorkspaceFolders` retire
fichiers, statut et token pour les seuls IDs absents : une réponse de l’ancienne
existence ne peut ressusciter un répertoire supprimé, même réintroduit ensuite.

Le token **et** le garde d’autorité de l’appelant sont requis avant lecture et
publication. Un appel déjà sans autorité ne supersède aucune requête valide.
Le retour individuel est un tableau, même vide, pour une publication effective,
`null` pour une lecture ignorée/refusée, et un rejet pour l’erreur courante après
publication de `[]`/`error`. Les erreurs périmées ne publient ni fichiers ni
statut, et ne rejettent pas. Les erreurs courantes restent visibles ; le global
continue son traitement historique des erreurs Files après publication du statut.
`app.js` transmet ce retour. Les deux lecteurs M2 (adoption et réconciliation)
conservent le marqueur et l’invitation à actualiser si le retour est `null` ; ils
n’annoncent pas « Inventaire actualisé » et n’effacent pas le besoin de reprise.
Même une publication concurrente plus récente réussie ne suffit pas à acquitter
la lecture M2 ignorée : une reprise explicite reste nécessaire et prouvée.
Fermeture, conversation/répertoire/contexte, navigation et générations M2
conservent leurs gardes ; aucun retry ni second POST implicite.

Fichiers du correctif : `app/web/chat_threads_sidebar.js`,
`app/web/chat_document_workshop.js`, raccord `app/web/app.js`, tests sidebar
existants et nouveau module navigateur ci-dessus, cette roadmap, contrat M2 et
entrée du hub (sa mention de clôture globale était affectée). Aucun changement
backend, SQL, DAV, admission, modèle, renderer, route ou dépendance. Les Maps
Exports/Images/Notes ne sont pas étendues par ce correctif.

**Résultats réels et commandes.** Les wrappers `m2_python`, `m2_node`, `m2_sql`
et leurs préconditions ci-dessus restent ceux exécutés : mêmes trois images et
empreintes, `--pull never`, réseau `none`, rootfs/checkout/cache navigateur en
lecture seule, `/tmp` tmpfs, `/usr/bin/env -i`, HOME temporaire et bytecode interdit.
Aucun dotenv présent ou symlink, aucune installation/pull. Le socket SQL seul
est adapté au scratch possédé `/tmp/fridadev-p2-m2-01-wfq8m36z/pg-socket`, et le
conteneur à `fridadev-p2-m2-01-proof-pg`, tous deux initialement absents. Le bind
couvre `/var/run/postgresql` dès l’initialisation ; readiness `pg_isready` positive
avant tout runner dépendant. Les deux modules SQL sont exécutés **en série** dans
l’unique invocation `m2_sql` documentée. Les sorties ci-dessous sont celles des
runners isolés ; les essais hôte du reviewer sont exclus des preuves autoritatives.

| Passe | Résultat | Durée | Exit |
| --- | --- | --- | --- |
| Baseline HEAD M2, 8 sélecteurs Node | 80/80 | 0,342314123 s | 0 |
| Baseline HEAD M2, 6 sélecteurs Chromium | 85/85 | 44,821106461 s | 0 |
| Annexe seule avant patch (`--test-name-pattern='response released'`) | 4 : 2 verts / 2 rouges causaux | 3,523457069 s | 1 |
| Frontières Node avant patch (`--test-name-pattern='P2-M2-01'`) | 19 : 2 verts / 17 rouges | 0,110041567 s | 1 |
| Annexe et frontières navigateur avant patch | 8 : 2 verts / 6 rouges | 6,525287437 s | 1 |
| Complément batch A/B, sources produit initiales montées read-only | 2 : 2 rouges | 0,187000390 s | 1 |
| Complément sortie M2, mêmes sources initiales read-only | 2 : 2 rouges | 4,047852997 s | 1 |
| Ciblé Node après correction | 21/21 | 0,112226368 s | 0 |
| Ciblé Chromium après correction | 10/10 | 9,745947258 s | 0 |
| Comparaison Python, 24 modules inchangés | 344/344 | 39,250 s | 0 |
| Comparaison Node, 8 fichiers inchangés + 21 cas | 101/101 | 0,443754923 s | 0 |
| Première comparaison Chromium, 7 modules | 94/95 ; garde chat temporisé en échec | 58,573066379 s | 1 |
| Même garde chat isolé, code courant / sources initiales | 1/1 puis 1/1 | 1,002837133 / 1,015734117 s | 0 / 0 |
| Comparaison Chromium reprise avec modules en série, avant raffinement final du harnais | 95/95 | 84,726869380 s | 0 |
| Erreurs tardives, réponse construite et capturée avant attente, sources initiales read-only | 2 : 2 rouges | 2,251983309 s | 1 |
| Même harnais final, ciblé Chromium | 10/10 | 9,807948247 s | 0 |
| Comparaison Chromium finale après raffinement du seul harnais | 95/95 | 84,424016836 s | 0 |
| Comparaison PostgreSQL réel, 2 modules inchangés en série | 27/27 | 39,131 s | 0 |

Zéro skip, annulation ou erreur de runner dans ces passes causales/finales.
Un premier essai de harnais Node était mal ordonné (17 cas, deux verts, dix
échecs et cinq annulations) : l’attente d’un appel déjà sans autorité bloquait
la libération de sa réponse. Le harnais a été corrigé avant la passe causale
19 cas ; aucune modification produit n’a servi à masquer cette erreur.
Les 19 cas verts intermédiaires passent en 0,102686620 s, exit 0 ; les huit
navigateurs intermédiaires en 7,724056135 s, exit 0. Les compléments montent les
**trois blobs produit exacts de `24233ce8`**, sans revert ni autre checkout.

La dernière relecture a resserré le seul harnais des erreurs tardives : leur
réponse fixe est désormais construite **et capturée avant l’attente**, comme les
succès ; aucun payload n’est fabriqué après libération. Les deux erreurs restent
rouges sur les blobs initiaux (`--test-name-pattern='late .* error'`), puis les dix
cas passent sur le correctif. Seule la comparaison navigateur est renouvelée
après cette modification de harnais ; code produit, Python, Node et SQL restent
identiques à leurs preuves finales ci-dessus.

La première comparaison Chromium n’est pas omise :
`test_frontend_browser_smoke.js`, cas `chat submit keeps the second draft while
one request is in flight and accepts it after completion`, compte deux requêtes
à une assertion qui en attend une. Sa fixture diffère le premier résultat de
120 ms puis attend encore 30 ms après des actions navigateur, sans verrouiller
l’état « en vol ». Le cas repasse isolément sur les deux codes. Cette dépendance
aux durées permet un faux diagnostic si le premier tour s’achève entre les
actions ; la cause temporelle exacte de cette exécution n’a pas été tracée.
La reprise ne modifie **ni fixture ni assertion**, mais utilise
`--test-concurrency=1` pour les sept modules ; l’herméticité et les sélecteurs
sont conservés. La fragilité de cette temporisation reste une limite de preuve,
pas une régression chat déclarée ni une correction opportuniste dans ce lot.

Comparaison finale : **344 + 101 + 95 + 27 = 567/567**, soit les **40 sélecteurs
historiques et un fichier navigateur ajouté**, 31 nouveaux cas, chaque exit 0.
Diagnostics Python hérités conservés : 264 `ERROR:frida.log_store`, 17
`WARNING:frida.conv`, trois `ERROR:frida.server`, mêmes familles/comptes que
la passe historique ; aucun nouveau logging produit.
Les 24 modules Python, huit fichiers Node et deux modules SQL sont exactement
ceux des commandes du 4 octobre ci-dessus. Les sélecteurs ciblés sont :

```sh
m2_node --test-name-pattern='P2-M2-01' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
```

Les rouges complémentaires emploient `m2_node_original`, même wrapper Node avec
les trois blobs initiaux `git show 24233ce86d2c02a4648b8b901258a533dce2f375:app/web/{chat_threads_sidebar.js,chat_document_workshop.js,app.js}`
montés en lecture seule par-dessus leurs chemins `/workspace/app/web/` :

```sh
m2_node_original --test-name-pattern='global batch waiting' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node_original --test-name-pattern='exit during M2' app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
```

La commande finale navigateur, seule adaptation d’ordonnancement après l’échec :

```sh
m2_node --test-concurrency=1 \
  app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_workshop.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption_reasons.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
```

Les 21 cas Node verrouillent aussi erreur/succès plus récent, inventaire vide,
indépendance A/B, résultats A déjà consommés avant attente B, suppression et
réintroduction, anciennes listes de répertoires et autorité invalide. Les dix
cas navigateur prouvent projection commune, cible proposée à la réouverture,
aucune sélection automatique, POST unique, réponses capturées avant adoption,
erreurs tardives et maintien/effacement justifié du marqueur de réconciliation.
Les 85 cas historiques sont conservés : upload multisélection/drag-and-drop,
brouillon, cibles/sources explicites, chat et préparation inactive, thèmes et
compositions desktop/mobile. Ce n’est ni un parcours upload intégral des probes,
ni une perte SQL démontrée, ni une preuve DAV/produit live.

**Contre-audit et findings distincts.** Inventaire des écrivains via `rg` :
Maps Files et Status déclarées chez le propriétaire, suppression dans
`saveWorkspaceFolders`, publications `ok`/`error` exclusivement dans
`readWorkspaceFiles`, appels global/individuel communs ; aucun setter complet
résiduel. Statut obsolète, omission indirecte de A, faux accusé M2, erreur courante
masquée, autorité du contexte, upload/chat, duplication et élargissement ont été
inspectés et couverts par les preuves adaptées. La revue indépendante du delta
ne relève aucun finding introduit dans Files. Les contradictions courantes de
clôture sont réconciliées, la provenance G-R1–G-R4 reste inchangée.

À la livraison P2-M2-01, deux findings hérités **restaient ouverts**, sans être
absorbés dans ce patch. Ce registre conserve cette provenance ; P2-M2-03 est
ensuite corrigé dans son lot séparé ; P2-M2-02 est corrigé ultérieurement
dans le lot dédié ci-dessous. Registre historique à la livraison P2-M2-01 :

| Finding distinct | Preuve et disposition |
| --- | --- |
| P2-M2-02 — publications Exports/Images/Notes | Global conserve les anciens résultats avant remplacement de Maps ; refresh individuel de ces familles sans token. Probe isolé Exports : ancien A collecté, attente B, refresh A publie un nouvel export, fin B restaure l’ancien A. Reproduit au code initial et au correctif ; Images/Notes ont le même chemin statique, sans reproduction propre de ces deux familles. Appelants : `chat_workspace_folder_exports_panel.js` et `chat_workspace_folder_notes_panel.js`. Ouvert, correction séparément autorisée requise. |
| P2-M2-03 — erreur du listing des répertoires acceptée comme vide | `listWorkspaceFoldersFromServer().catch(... return [])` puis sauvegarde/retour `true` : erreur 503 simulée retire les deux répertoires et est acceptée comme succès. Même comportement au code initial et au correctif. Ouvert, correction séparée ; aucune suppression SQL ou DAV inférée. |

Ces deux probes scratch supplémentaires utilisent le même runner Node isolé et
le vrai contrôleur, HTTP simulé : **2/2 rouges en 0,143056453 s sur les blobs
initiaux, 2/2 rouges en 0,108830140 s après correction, exits 1, zéro skip**.
Ils sont distincts de la comparaison 567 et prouvent leur antériorité ; leurs
assertions attendent la conservation du nouvel export et le refus du faux succès
de listing. Aucun correctif ni fixture produit ne leur est associé dans ce lot.

**Nettoyage et limites.** Après SQL, arrêt/suppression du seul conteneur possédé,
socket vérifié vide puis retiré ; données PG tmpfs détruites. Tous les autres
runners sont `--rm`. Les deux scratches possédés (runners, logs synthétiques, probes et
blobs initiaux) sont retirés après conservation des faits et contre-audit ; absence
vérifiée avant commit. Aucun artefact d’autrui ou ressource opérateur supprimé.
La coordination est locale à l’instance frontend : elle ne garantit pas une
fraîcheur serveur universelle, ne coordonne pas d’autres onglets et ne prouve
pas l’état DAV. Migrations opérateur M1/M2, livraison runtime/rebuild/health et
preuve DAV live restent ouverts. M3–M10/Z non commencés, préparation inactive ;
aucun déploiement, provider, renderer ou appel modèle réel.

#### Correction indépendante P2-M2-03 — 5 octobre 2026

**Disposition : corrigé sur la frontière frontend ; livraison Git dédiée puis
arrêt du lot.** Base revérifiée : `/opt/platform/fridadev`, branche
`FridaV1-Document-Workshop-M2`, HEAD = upstream = M2 distant
`c8275d7d39672560e84bd89ea66c6daae8ba8cb3`, parent exact
`24233ce86d2c02a4648b8b901258a533dce2f375`, worktree propre, divergence `0/0`.
`git ls-remote --heads` revalide M1 `c6f648badba96a60f1474db8d3f7404f97a2dda7`,
M0 `3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a` et main
`e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb`. Le retour final porte SHA/parent,
push et alignement ; aucun merge, changement de branche ou livraison runtime.
Le succès historique 536/536, G-R1–G-R4 Approved et la correction P2-M2-01
567/567 restent conservés avec leur provenance. **P2-M2-02 est explicitement
exclu et restait ouvert à cette livraison ; sa correction dédiée ultérieure
figure ci-dessous. M3 reste non commencé.**

**Cause et rouge.** Le global interceptait l'erreur de
`listWorkspaceFoldersFromServer`, la transformait en `[]`, sauvegardait cette
fausse appartenance, reconstruisait les autres inventaires puis retournait
`true`. Sur cette base, l'annexe établit deux répertoires et un fichier de A par
un premier chargement valide. Le second 503 retourne `true`, répertoires `0`,
fichiers de A `0` : rouge causal. Le contrôle `200 {ok:true,items:[]}` est vert,
avec ces mêmes zéros légitimes. Aucune suppression SQL/DAV inférée.

**Correctif minimal.** Le propriétaire attend ses deux listings avant toute
publication, sans convertir l'erreur du listing des répertoires en vide. Son
catch existant renvoie `false` et affiche « Mode hors ligne. » ; l'epoch ignore
les erreurs anciennes sans toucher le succès récent. Avant normalisation, cette
seule frontière exige `ok:true`, un tableau `items`, des champs `id` et
`display_name` chaînes non blanches, puis aucune ligne perdue. Le contrat réel
est vérifié dans la route, le service et `serialize_workspace_folder_row` ;
parseur et normalizers partagés inchangés. Des objets coercibles ne peuvent plus
inventer une appartenance. Toute liste invalide est refusée intégralement.

Une erreur laisse le dernier état connu des répertoires, conversations,
sélections, Files/Exports/Images/Notes et de leurs statuts. Elle ne lance pas leurs
lectures ni n'invalide les tokens Files individuels en vol. Le garde
`workspaceFoldersLoaded` porte seulement la connaissance de la liste : un premier
échec n'annonce pas « Aucun répertoire ». Le bootstrap `loaded=false` existant
ne crée aucune conversation ni répertoire. Une liste réellement vide conserve
la publication et la suppression des seuls IDs absents ; les tokens Files de
P2-M2-01 restent invalidés, sans résurrection tardive. L'ancienne liste globale
est refusée après une suppression confirmée plus récente.

Les appelants sont inspectés via `rg` : `syncAndRender` et déplacement rendent
le dernier état sans effacer le statut ; bootstrap s'arrête sur `false`.
Après chat et suppression de conversation confirmés, les trois rechargements
passent `preserveStatus` à `loadThread` si le refresh a échoué ou été ignoré.
Ils rendent toujours les messages légitimes, sans fausse synchronisation,
rollback du succès serveur ou replay de mutation. Une actualisation ultérieure
réussie reprend normalement ; aucun retry, polling, second cache ou route.
La coordination Files/Status, ses tokens, son tableau/null/rejet, les gardes M2
et la réconciliation explicite sont inchangés. **Aucune coordination nouvelle
des publications Exports/Images/Notes** n'est ajoutée.

Fichiers du lot : `app/web/chat_threads_sidebar.js`, raccord `app/web/app.js`,
`app/tests/unit/frontend_chat/test_threads_sidebar_module.js`, navigateur
`test_frontend_browser_document_inventory_publication.js`, deux fixtures
nominales dans `test_frontend_browser_active_documents.js` et
`test_frontend_browser_smoke.js`, cette roadmap, contrat M2 et hub (son affirmation
sur les P2 ouverts était affectée). Aucun backend, SQL/DAV, admission/tokens,
modèle, renderer, dépendance ou DOM produit ajouté.

**Preuves réelles.** Mêmes images/runners et empreintes documentés plus haut,
revalidés avant exécution ; aucune installation ou pull. Réseau `none`, rootfs,
checkout et cache navigateur read-only, `/tmp` tmpfs, `/usr/bin/env -i`, HOME
scratch et bytecode Python interdit. Absence de dotenv et symlink vérifiée sans
lecture. Scratch possédé `/tmp/fridadev-p2-m2-03-vlhaexy1` ; PostgreSQL dédié
`fridadev-p2-m2-03-proof-pg`, chemin socket et nom initialement absents.
Bind du socket sur `/var/run/postgresql` dès l'initialisation, `pg_isready` exit 0
après 1,787 s avant SQL ; deux modules SQL **en série**, aucun accès DB opérateur.

| Passe | Résultat | Durée | Exit |
| --- | --- | --- | --- |
| Baseline Node, 8 fichiers | 101/101 | 0,336609683 s | 0 |
| Baseline Chromium, 7 fichiers en série | 95/95 | 84,814360234 s | 0 |
| Annexe avant patch, `P2-M2-03 distinguishes` | 1 contrôle vert / 1 rouge 503 | 0,086841903 s | 1 |
| Frontières Node initiales, `P2-M2-03` | 19 : 4 verts / 15 rouges | 0,115242922 s | 1 |
| Suppression confirmée avant patch, `P2-M2-03 confirmed conversation deletion` | 1 rouge, statut effacé | 0,305417237 s | 1 |
| Premier harnais navigateur, `P2-M2-03` | 3 rouges produit / 1 timeout de harnais | 7,863537457 s | 1 |
| Harnais chat corrigé avant patch, `P2-M2-03 confirmed chat result` | 1 rouge, statut vide | 0,830085960 s | 1 |
| Complément premier échec, `P2-M2-03 first load failure`, avant garde connaissance | 1 rouge, faux libellé vide | 0,075184198 s | 1 |
| Complément `P2-M2-03 object folder`, avant validation des types | 2 rouges | 0,109757766 s | 1 |
| Ciblé intermédiaire Node / navigateur, avant garde connaissance | 41/41 / 14/14 | 0,330119819 / 12,477527803 s | 0 / 0 |
| Ciblé intermédiaire après garde connaissance | 41/41 / 14/14 | 0,323399066 / 12,547268590 s | 0 / 0 |
| Ciblé final Node, `P2-M2-0[13]` | 44/44, dont 23 nouveaux | 0,342456045 s | 0 |
| Ciblé final Chromium : publication, documents actifs, chat nominal | 16/16, dont les 10 P2-M2-01 et 4 nouveaux | 14,959756687 s | 0 |
| Comparaison Python, 24 modules | 344/344 | 18,867 s | 0 |
| Comparaison Node avant derniers types | 121/121 | 0,460533920 s | 0 |
| Première comparaison Chromium, avant complétude des deux mocks de listing | 85/99 ; 14 échecs | 240,023095224 s | 1 |
| Comparaison finale Node, 8 fichiers | 124/124 | 0,415412187 s | 0 |
| Comparaison finale Chromium, 7 fichiers en série | 99/99 | 87,716477599 s | 0 |
| PostgreSQL isolé, 2 modules en série | 27/27 | 18,090 s | 0 |

Comparaison finale **344 + 124 + 99 + 27 = 594/594** : les **567 historiques
conservés**, plus **23 Node et 4 Chromium** dans les modules existants, mêmes
**41 sélecteurs**, chaque exit 0, zéro skip ou annulation. Les quatre probes
originaux P2-M2-01 et leurs six frontières restent verts. Les 23 nouveaux cas
Node couvrent 503/réseau, JSON/enveloppe/lignes invalides, conservation de toutes
les familles et statuts, sélections/conversation, premier échec, reprise,
lecture Files indépendante, suppression partielle et anciennes générations.
Les quatre navigateurs prouvent panne visible, inventaire et fichier adopté
conservés, réouverture avec cible proposée mais non choisie, brouillon/sélection,
reprise explicite, POST d'adoption unique et statut conservé après chat confirmé.
Aucune instrumentation d'audit n'est livrée au produit.

Les essais imparfaits ne sont pas des rouges causaux : le premier harnais chat
attendait un sélecteur inexistant et ne simulait pas les messages persistés
après sa réponse. Il a été corrigé **avant patch**, puis donne le rouge d'assertion
ci-dessus. La première comparaison Chromium révèle que deux fixtures historiques
ne simulaient pas du tout `GET /api/workspace-folders` et levaient `Unexpected
fetch` ; l'ancien fallback masquait cette erreur. Les deux seuls ajouts de mock
sont maintenant `200 {ok:true,items:[]}`, conforme au serveur et à leur scénario
nominal sans répertoire. Ni timer ni assertion ne change, notamment dans le cas
chat temporisé ; les modes 503/réseau des nouveaux tests restent réellement en
erreur. La fragilité et le résultat historique **94/95** de P2-M2-01 sont conservés.
Seuls Node/Chromium sont repris après derniers types/fixtures ; Python et SQL,
non affectés, ne sont pas répétés. Diagnostics Python hérités : 264
`ERROR:frida.log_store`, 17 `WARNING:frida.conv`, trois `ERROR:frida.server`,
mêmes familles/comptes ; aucune nouvelle collecte produit.

Commandes ciblées exactes, avec les wrappers/préconditions ci-dessus :

```sh
m2_node --test-name-pattern='P2-M2-03 distinguishes' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-03' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-03 confirmed conversation deletion' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-03 first load failure' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-03 object folder' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-03' app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
m2_node --test-name-pattern='P2-M2-03 confirmed chat result' app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
m2_node --test-name-pattern='P2-M2-0[13]' app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-concurrency=1 --test-name-pattern='P2-M2-0[13]|active conversation documents upload|chat stream nominal' app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
```

Les 41 sélecteurs exacts de comparaison sont ceux retranscrits dans M2 :
les **24 modules `m2_python`**, les **huit fichiers `m2_node`** et l'invocation
unique **`m2_sql tests.integration.document_workshop.test_adoption_postgresql
tests.integration.document_workshop.test_context_store_postgresql`**, inchangés ;
les **sept fichiers Chromium** sont ceux de la commande P2-M2-01 avec
`--test-concurrency=1`, inchangés. Aucun fichier ou cas supprimé pour atteindre
un total ; les nouveaux cas sont dans les deux modules existants. Les preuves
frontend utilisent le vrai propriétaire et Chromium avec fetch simulé ; Python
inclut le transport HTTP loopback synthétique historique ; PostgreSQL est réel
mais isolé. Aucune preuve DAV, modèle ou produit live déduite.

**Contre-audit final.** Tous les appels listing/refresh et écrivains Files sont
recensés ; pas de fallback en liste vide, publication avant succès ou remplacement
Files destructeur réintroduit. Statut de l'échec conservé chez les trois
rechargements concernés ; mutation confirmée non rejouée. Vrai vide accepté,
seuls absents invalidés ; erreur périmée non publiée ; tokens/contexte, bootstrap,
chat/upload, brouillon, gardes M2, thèmes et DOM desktop/mobile conservés.
Pas de normalizer commun modifié, second cache, nouvelle collecte, duplication
ou extension de P2-M2-02/M3. Le skill `requesting-code-review` a fourni une
contre-revue statique indépendante : types corrigés après deux rouges, puis
aucun nouveau finding dans le delta final ; aucun test hôte ou runner exécuté
par le reviewer. Les contradictions courantes de statut sont réconciliées sans
réécriture des revues historiques.

**Findings hors lot à la livraison P2-M2-03.** P2-M2-02 restait ouvert et exclu
(il est corrigé dans le lot dédié ultérieur ci-dessous) : son rouge causal
Exports et l'inspection Images/Notes consignés dans P2-M2-01 restent inchangés,
séparés de la comparaison. Aucun de ces rouges n'est caché ou réparé ici.
**P2-M2-04 — erreur backend de listing convertie en succès vide**, nouveau finding
indépendant ouvert à cette livraison, corrigé ensuite dans son lot ci-dessous :
`workspace_folders_store.py` intercepte exception
DB/sérialisation et retourne `[]` ; `workspace_folders_service.py` ajoute
`ok:true`, route HTTP 200 par inspection. Un probe scratch appelle les vrais
store/service avec une fonction de connexion synthétique qui lève : warning
appelé une fois, `items:[]`, `ok:true`, **1/1 rouge attendu, 0,001 s, exit 1**
(0,508 s murales Docker). Assertion attendue : l'erreur ne doit pas être un succès.
Le probe est séparé des 594 et ne prouve ni DB réelle défaillante ni perte SQL/DAV.
Cette erreur déjà masquée côté serveur est indiscernable d'un vrai vide côté UI ;
aucun correctif backend n'est absorbé. Une première invocation exploratoire du
probe avec un sélecteur Python inexistant avait été refusée (exit 1), exclue de
cette preuve ; la bonne invocation isolée charge le script scratch read-only par
`python -c`/`runpy`, mêmes préconditions et environnement que `m2_python`.

**Nettoyage et limites.** Conteneur PostgreSQL possédé arrêté/supprimé après
succès SQL, socket vide retiré et absence vérifiée ; données tmpfs détruites.
Autres runners `--rm`. Scratch possédé retiré après conservation des faits,
aucun artefact d'autrui supprimé. La cohérence reste locale à l'instance frontend,
sans coordination inter-onglets ni preuve universelle de fraîcheur serveur.
Migrations opérateur, livraison runtime/rebuild/health et DAV live restent
ouverts. M3–M10/Z non commencés ; arrêt après vérification du commit/push,
aucun enchaînement vers P2-M2-02, aucun merge ni livraison runtime.

#### Correction indépendante P2-M2-02 — 5 octobre 2026

**Disposition : corrigé séparément pour Exports, Images générées et Notes.**
Base revalidée : `pwd` et `git rev-parse --show-toplevel` donnent
`/opt/platform/fridadev` ; branche `FridaV1-Document-Workshop-M2`, propre,
divergence `0/0`, HEAD = upstream = M2 distant
`c057d286b0e7a35d2ce8e0f3c43eaf8200edd131`, parent `c8275d7d`.
`git ls-remote --heads` confirme M1 `c6f648ba`, M0 `3eb2e34a`, main `e3e0d19`.
Le commit de ce lot a pour parent exact `c057d286` ; son SHA, push et alignement
sont fournis dans le retour final. Pas de merge, changement de branche ou runtime.
Les succès historiques 536/567/594, revues G-R1–G-R4 et échecs intermédiaires
restent conservés avec leur provenance. P2-M2-01/03 restent fermés dans leur
périmètre ; **à cette livraison, P2-M2-04 backend restait ouvert et exclu ;
sa correction séparée figure ensuite. M3–M10/Z non commencés**.

**Cause et preuves distinctes.** Chez le propriétaire, les lecteurs individuels
publiaient directement données/statut sans coordination. Le global collectait
A, attendait B puis remplaçait six Maps entières : anciens résultats et omissions
pouvaient écraser une publication récente. Exports est reproduit à nouveau ;
Images et Notes sont maintenant reproduits séparément, avec les vraies enveloppes
`exports`, `generated_images` et `items`. Pour chaque famille, le contrôle
(global terminé avant lecture individuelle) est vert et la livraison globale
après publication individuelle est rouge. Les trois tests Chromium montés
capturent A ancien avant l'attente de B, utilisent les vrais boutons, contrôleurs
et normalizers, puis observent `old-folder-a` à la place de `new-a`, statut `ok`
périmé, avec **un seul POST de création confirmé par cas**. Aucun mock de cache,
payload reconstruit après l'attente, sommeil arbitraire ou instrumentation produit.

**Choix minimal.** La question préalable « Existe-t-il un meilleur plan, plus
simple, plus sûr et avec moins d'effets de bord ? » conduit à reprendre la
coordination locale Files éprouvée, séparément pour chaque famille et répertoire.
Les seules Maps existantes restent chez le propriétaire. Trois Maps de tokens
opaques et trois lecteurs communs global/individuel contrôlent autorité avant I/O,
après réponse et avant erreur. Chaque publication données/statut est synchrone.
Les six setters de remplacement complet sont retirés : ignorer A ne peut pas
l'effacer indirectement. Ancien succès/erreur, erreur récente, vide réel et
`not_applicable` gardent leur traitement honnête ; pas de sérialisation générale,
verrou UI, cache parallèle, retry/polling, dépendance ou mécanisme futur générique.

L'epoch global est acquis à l'entrée. Les tokens d'inventaire sont réservés
**après les deux listings réussis et l'epoch validé**, pour tous les répertoires
et les quatre familles, sans attente avant le premier I/O Files. Ils ne sont
jamais réacquis à la reprise des phases Exports/Images/Notes. Une requête plus
récente de A conserve donc son autorité pendant l'attente de B ou d'une autre
famille ; les phases supersédées ne lancent pas d'I/O. Les générations globales
refusent les phases et listings anciens. La suppression confirmée d'un ID retire
données/statut/token de chaque famille ; réintroduire cet ID ne rend pas son
autorité à une ancienne réponse. Une erreur de listing P2-M2-03 ne réserve ni
n'invalide ces tokens et conserve le dernier état connu.

Retour individuel : tableau, même vide, pour publication effective ; `null`
pour absence/autorité perdue/supersession, y compris erreur périmée ; rejet après
publication `[]`/`error` pour erreur courante. Les trois panneaux vérifient ce
retour pour création/réutilisation d'export, création/suppression d'image et
création de note. Un rechargement ignoré/échoué après mutation confirmée affiche
la confirmation puis « Inventaire non actualisé. » sur le statut existant et
rend l'inventaire/statut courant. Il n'invite pas à rejouer la mutation. La note
créée explicitement reste sélectionnée. Erreurs de mutation et actions
ouverture/téléchargement/préparation restent inchangées. Le global conserve son
retour historique de parcours : `true` ne garantit pas tous les statuts `ok`.
Files P2-M2-01 et sa réconciliation explicite M2 ne sont pas refondus ; le listing
et le bootstrap/chat P2-M2-03 sont conservés.

Fichiers : `app/web/chat_threads_sidebar.js`, les trois panneaux
`chat_workspace_folder_exports_panel.js`, `chat_workspace_folder_generated_images_panel.js`,
`chat_workspace_folder_notes_panel.js`, les deux tests sidebar/navigateur existants,
cette roadmap, le contrat M2 et l'affirmation courante du hub. Aucun backend,
SQL/DAV, admission/tokens, provider, renderer, DOM ou nouvelle capacité produit.

**Preuves et exécution.** Images existantes et empreintes revalidées, mêmes
wrappers `m2_python`, `m2_node`, `m2_sql` ci-dessus : `--pull never`, réseau `none`,
rootfs/checkout/cache navigateur read-only, scratch possédé,
`/usr/bin/env -i`, HOME temporaire et bytecode Python interdit. Aucun dotenv
présent, y compris symlink. Scratch `/tmp/fridadev-p2-m2-02-drbbnotl`, socket
`pg-socket` et conteneur `fridadev-p2-m2-02-proof-pg` initialement absents,
préconditions vérifiées avant création. Socket bindé sur `/var/run/postgresql`
dès initialisation, readiness `pg_isready` exit 0 en 1,317 s, puis les deux modules
SQL en série, jamais la DB opérateur. Aucune installation/pull ou preuve hôte.

| Passage | Résultat réel | Durée runner | Exit |
| --- | --- | --- | --- |
| Baseline huit fichiers Node | 124/124 | 0,462676001 s | 0 |
| Baseline sept fichiers Chromium, concurrence 1 | 99/99 | 86,917549054 s | 0 |
| Contrôles/rouges principaux Node, trois familles | 6 : 3 verts / 3 rouges | 0,094872622 s | 1 |
| Matrice causale Node avant patch, harnais corrigé | 72 : 15 verts / 57 rouges | 0,185072351 s | 1 |
| Appelants confirmés avant patch | 10/10 rouges | 0,105339582 s | 1 |
| Courses montées Chromium avant patch, capture A prouvée | 3/3 rouges | 2,657898017 s | 1 |
| Ciblé Node après correction | 82/82 | 0,167578514 s | 0 |
| Ciblé Node après assertion du rendu d'erreur et adaptation des panneaux | 82/82 | 0,189718859 s | 0 |
| Ciblé Chromium après correction | 3/3 | 3,106376756 s | 0 |
| Comparaison Python, 24 modules | 344/344 | 24,350 s | 0 |
| Comparaison Node, huit fichiers | 206/206 | 0,525733652 s | 0 |
| Comparaison Chromium, sept fichiers, concurrence 1 | 102/102 | 89,822881720 s | 0 |
| Comparaison PostgreSQL isolé, deux modules en série | 27/27 | 23,670 s | 0 |

Les passages de preuve retenus n'ont aucun skip/cancel. **Comparaison finale :
344 + 206 + 102 + 27 = 679/679**, soit les **594 historiques conservés + 82 Node
et 3 Chromium nouveaux**. Diagnostics Python hérités inchangés : 264 ERROR
`frida.log_store`, 17 WARNING `frida.conv`, 3 ERROR `frida.server` issus des
scénarios négatifs, sans nouvelle journalisation. Les quatre scénarios originaux
P2-M2-01 restent verts, ainsi que les gardes M2 et P2-M2-03, upload/chat,
multisélection, drag-and-drop, sélection explicite et compositions/themes.

Échecs intermédiaires conservés, exclus des preuves causales retenues : premier
harnais Node 72 cas, 4 verts/19 échecs/49 cancel (0,179013896 s, exit 1), car son
cas d'autorité attendait une lecture bloquée avant de libérer sa promesse ;
libération avant assertion corrige le harnais, sans modifier l'attendu. Le test
`not_applicable` doit aussi fournir le même état non lié au listing global.
Premier Chromium : trois timeouts sur un champ de brouillon inexistant
(17,235830333 s, exit 1), remplacé par le vrai compositeur `#message`.
Puis trois verts non causaux (3,164862373 s, exit 0) : le tri « Autre »/« Recherche »
faisait lire B avant A. Une assertion de capture A révèle trois erreurs de harnais
(2,363254890 s, exit 1). Les seuls libellés synthétiques A/B imposent ensuite
l'ordre attendu et l'assertion de capture est conservée : trois vrais rouges.
Aucun timer ou assertion historique n'est affaibli. Deux commandes d'édition
ont été refusées (`python` absent, exit 127) ; reprises par `python3` stdlib,
sans imports applicatifs hôte. Le ciblé lancé sur cette édition partielle donne
10 échecs/72 cancel (0,148344214 s, exit 1), exclu ; après édition complète les
82 passent. Les anciens 94/95 et 85/99 restent consignés dans leurs lots.

Commandes ciblées exactes (même module, jamais suppression d'un cas) :

```sh
m2_node --test-name-pattern='P2-M2-02.*collected A' \
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-02 confirmed' \
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-name-pattern='P2-M2-02' \
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js
m2_node --test-concurrency=1 --test-name-pattern='P2-M2-02 mounted' \
  app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
```

Les **41 sélecteurs exacts de comparaison** restent ceux retranscrits dans M2
et P2-M2-01/03 : les 24 modules de `m2_python`, les huit fichiers de `m2_node`,
les sept fichiers de `m2_node --test-concurrency=1`, et
`m2_sql tests.integration.document_workshop.test_adoption_postgresql
 tests.integration.document_workshop.test_context_store_postgresql` (une
invocation séquentielle). Aucun sélecteur supprimé/ajouté : les cas nouveaux
sont dans les deux modules existants. Wrappers inchangés, seuls chemin socket
et nom PostgreSQL adaptés mécaniquement à ce scratch. Aucun passage vert répété
sans changement ou incertitude nouvelle. Node/Chromium sont à fetch simulé,
Python inclut les preuves HTTP loopback historiques, PostgreSQL est réel isolé ;
aucun de ces niveaux ne constitue une preuve DAV ou produit live.

**Contre-audit.** `rg` recense tous les écrivains, setters, lecteurs et appelants
réels : aucune publication ancienne restante, six remplacements complets retirés,
données/statut atomiques, pas d'omission destructrice ni collision de famille.
Suppression/réintroduction, ancien succès/erreur, erreur récente, vrai vide,
`not_applicable`, reprise, A/B indépendants, phases différées Files et famille
précédente, globaux concurrents et erreur de listing sont couverts par le vrai
propriétaire. Les dix cas d'appelants observent les POST/DELETE réels simulés,
le retour réel, le statut visible et le rendu d'erreur, sans replay ; les trois
cas montés observent aussi brouillon, sélection de fichier et note créée.
La contre-revue indépendante via `requesting-code-review` ne relève aucun
nouveau finding dans le code/tests ni dans la revue documentaire complémentaire ;
57 références documentaires locales et leurs ancres sont vérifiées (exit 0).
La revue est statique, aucun test hôte ou
runner exécuté par le reviewer. Pas de second cache, nouvelle collecte,
secret/contenu ajouté, abstraction future, backend ou élargissement M3.
Documents courants réconciliés, provenance historique conservée.

**Finding vivant à la livraison P2-M2-02 et limites.** P2-M2-04 restait ouvert
(il est corrigé dans le lot séparé ci-dessous), son rouge historique
séparé n'est ni rejoué ni corrigé dans ce lot : une erreur DB déjà transformée
en `200 {ok:true,items:[]}` est indiscernable d'un vrai vide côté UI. Aucun
résultat 679/679 ne ferme ce finding. Cohérence locale au contrôleur, sans
coordination inter-onglets ni garantie de fraîcheur serveur/DAV. Migration
opérateur, livraison runtime/rebuild/health et DAV live restent ouverts ;
M3–M10/Z non commencés. Arrêt après vérification de livraison Git, sans
enchaînement P2-M2-04 ou M3.

**Nettoyage.** Le seul PostgreSQL possédé est arrêté puis supprimé après SQL ;
socket vide retiré et absence vérifiée, données tmpfs détruites. Autres runners
`--rm`. Scratch possédé retiré après conservation des faits et revue finale ;
aucun artefact d'autrui ou runtime opérateur supprimé.

#### Correction indépendante P2-M2-04 — 5 octobre 2026

**Disposition : corrigé sur code et preuves, livraison runtime ouverte.**
Base revalidée : `/opt/platform/fridadev`, branche
`FridaV1-Document-Workshop-M2`, propre, divergence `0/0`, HEAD/upstream/M2 distant
`0a5b4b553a20e0230991be34fd7b23354885395e`, parent
`c057d286b0e7a35d2ce8e0f3c43eaf8200edd131`. `git ls-remote --heads`
confirme M1 `c6f648badba96a60f1474db8d3f7404f97a2dda7`, M0
`3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a`, main
`e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb`. Aucun changement de branche,
pull/reset/stash, merge, installation ou déploiement. Les historiques
536/567/594/679 et G-R1–G-R4 Approved restent des preuves de leurs lots,
pas une fermeture rétroactive de P2-M2-04.

**Cause et preuve avant patch.** Le store interceptait toute exception de
connexion, SQL, lecture ou sérialisation et renvoyait `[]` ; wrapper inchangé,
service `ok:true`, GET HTTP 200 et observation `workspace_folder_list_ok`.
La reproduction Flask utilise la vraie route enregistrée par `server.py`,
le vrai service, wrapper et store ; seule la connexion DB est remplacée.
Lecture réussie sans ligne : `200,ok:true,items:[]`, contrôle vert.
Connexion synthétique refusée : même réponse, rouge `200 != 503`, exit 1.
Aucune panne opérateur ni suppression SQL/DAV n'est déduite de cette injection.
La sérialisation est aussi exercée après une première ligne valide ; aucun
inventaire partiel n'est admis dans les assertions.

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets
de bord ? » Le pas retenu est une exception dédiée de listing chez le store,
traduite aux frontières existantes, sans nouveau cache ou retry. `503` suit
la convention de lecture de stockage indisponible des services documentaires ;
il ne promet pas une panne transitoire ni une reprise automatique. `500`
reste le résultat historique de persistance partielle après mutation distante.

**Contrat et appelants.** `WorkspaceFolderListError` porte la raison fixe
`workspace_folder_list_failed`. Le listing renvoie seulement un tableau
entièrement lu/sérialisé, ou lève cette exception. Tri, filtre `include_deleted`,
projections, icônes et vraie liste vide restent inchangés. Le warning privé
existant est conservé sans collecte supplémentaire ; cause technique chaînée
en interne, jamais exposée par HTTP ou les projections d'observabilité.
Le service renvoie maintenant `(payload,status)` comme ses autres opérations ;
le registrar GET transmet le statut. Échec : JSON `ok:false`, raison stable,
message fixe « lecture des repertoires indisponible », observation `error/5xx`,
aucun `items` ni `folder_count` inventé, aucun succès de listing.

Recensement `rg` du nom de méthode, y compris le consommateur dynamique
`getattr`, puis inspection de ses appels :

| Frontière affectée | Traitement de la lecture impossible |
| --- | --- |
| `workspace_folders.py` : wrapper et validation de nom | Propagation de l'exception dédiée ; service create/patch refuse en JSON 503 avant mutation. |
| `workspace_folders_store.py` : create et update avec nom | Refus `None` selon leur contrat de mutation existant, sans SQL d'écriture. Ce retour laisse les compensations Nextcloud-first s'exécuter si DAV a déjà eu lieu. Aucun `catch → []` déplacé. |
| `workspace_folder_nextcloud_runtime.py` : inventaire initial create/rename | Refus explicite 503 avant mutation SQL/DAV. Relecture après MKCOL/MOVE : branches de persistance partielle et compensation existantes conservées, sans replay ni nouvelle suppression distante. |
| `workspace_folder_nextcloud_reconcile.py` : inventaire initial et deux lectures finales | `ok:false`, record existant `failed` initial ou `partial` final, raison stable, classe `5xx`. Compteurs inconnus et exemples finaux inconnus valent `None`, pas zéro. Les records d'actions déjà accomplies sont conservés. |
| `workspace_folder_standard_subfolders.py` : inventaire initial | Échec explicite, `folder_counts:None`, pas `not_applicable` sur la panne. Sa synthèse nominale utilise déjà le snapshot initial ; aucune nouvelle relecture finale ajoutée. |
| `workspace_document_existing_inventory.py` → `workspace_document_existing_files.py` | Catch existant adapté : erreur d'inventaire `folder_document_existing_inventory_failed`, verdict failed avant DAV ; aucun changement produit nécessaire. Le test historique utilise désormais le vrai wrapper/store avec panne de connexion. |

Les getters indépendants et leurs fallbacks ne sont pas modifiés. Le seul
appelant du service de listing est le registrar GET ; un ancien test direct
adapte son unpacking et affirme HTTP 200, sans supprimer ses assertions.
Les compensations vérifiées conservent leurs limites existantes : après MKCOL,
le dossier distant reste présent faute de preuve d'ownership pour le supprimer ;
après MOVE, rollback réussi ou échoué reste explicitement représenté.

**Préconditions et séparation des preuves.** Images existantes, sans pull :
`fridadev-audit-py:latest`, `mcr.microsoft.com/playwright:v1.54.0-jammy`,
`postgres:16-alpine`, empreintes vérifiées. Checkout et rootfs read-only,
réseau `none`, environnement vidé par `/usr/bin/env -i`, bytecode désactivé,
valeurs de providers `.invalid`, scratch possédé
`/tmp/fridadev-p2-m2-04-i8udp379`. Absence de `app/.env` et de son symlink
vérifiée sans lecture ; présence du cache navigateurs vérifiée.
Wrappers `m2_python`, `m2_node`, `m2_sql` ci-dessus conservés ; seul le chemin
SQL du socket est adapté à ce scratch. PostgreSQL dédié
`fridadev-p2-m2-04-proof-pg`, conteneur/socket initialement absents,
`/var/run/postgresql` monté dès initialisation, données tmpfs, aucun TCP,
readiness `pg_isready` exit 0 en 1,631 s ; les deux modules SQL sont exécutés
en série et ne touchent jamais la DB opérateur.

Le nouveau test PostgreSQL renomme temporairement une colonne dans le seul
schéma synthétique de preuve : le vrai SELECT lève `UndefinedColumn`, puis le
GET réel renvoie le JSON 503. Rétablissement explicite du schéma et GET suivant
réussis, sans retry. Le test voisin confirme ordre, projection et filtre supprimé
avec et sans `include_deleted`. Les DAV des autres tests sont simulés ou HTTP
loopback dans le runner, sans accès DAV live.

La composition frontend réutilise une capture JSON du vrai Flask/store,
`tests/support/workspace_folder_listing_responses.json`, produite avec :

```sh
docker run --rm --pull never --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev \
  --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
  --workdir /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest \
  -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
  EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid \
  SEARXNG_URL=https://search.invalid \
  python -m tests.support.workspace_folder_listing_fixture
```

Exit 0, 1,698 s murales. Le test Python
`test_p2_m2_04_browser_fixture_matches_actual_backend_responses` compare à
chaque passe les deux réponses réelles à cette capture intégrale. Les deux cas
Chromium lisent cette fixture du dépôt : aucune env supplémentaire obligatoire,
aucun store simulant le correctif. Seul le transport est simulé. Échec : retour
frontend false, statut « Mode hors ligne. » visible, quatre inventaires non
vides et leurs statuts conservés, répertoires/sélection/contexte/brouillon
préservés ; reprise explicite réussie, cible adoptée encore proposée sans
sélection automatique, un seul POST d'adoption. Vrai vide : succès et
invalidation des quatre familles selon P2-M2-01/02/03, puis reprise explicite.
Cette composition relie le backend corrigé à P2-M2-03 ; elle ne constitue pas
un test HTTP bout en bout navigateur→Flask ni une preuve runtime déployé.

**Résultats réels, sans skip.** Durées internes des runners, sauf mention murale :

| Passe | Résultat | Exit | Durée |
| --- | --- | --- | --- |
| Baseline Python, quatre modules concernés/voisins au parent | 82/82 | 0 | 0,392 s |
| Rouge causal GET réel + contrôle vide avant patch | 1 vert, 1 rouge sur 2 | 1 | 0,722 s |
| Premiers huit cas store avant patch | 2 méthodes vertes, 6 échouées ; 11 assertions/subtests rouges | 1 | 0,007 s |
| Matrice étendue avant patch, 17 méthodes | 3 méthodes vertes, 14 échouées ; 23 assertions/subtests rouges | 1 | 0,844 s |
| Même matrice après patch | 17/17 | 0 | 0,731 s |
| Ciblé avec module voisin renommage | 29/29 | 0 | 1,239 s |
| PostgreSQL ciblé nominal/erreur réelle/reprise | 2/2 | 0 | 1,600 s |
| Chromium ciblé capture backend | 2/2 | 0 | 2,723529681 s |
| Comparaison initiale Python | 373/373 | 0 | 25,688 s |
| Comparaison Node finale | 206/206 | 0 | 0,548504314 s |
| Comparaison Chromium initiale | 104/104 | 0 | 92,434611003 s |
| Comparaison PostgreSQL finale | 29/29 | 0 | 25,467 s |
| Test capture réelle ↔ fixture conservée | 1/1 | 0 | 0,774 s |
| Comparaison Python après ajout de ce contrat | 374/374 | 0 | 24,814 s |
| Comparaison Python finale, test Documents renforcé | 374/374 | 0 | 23,667 s |
| Comparaison Chromium finale, fixture du dépôt | 104/104 | 0 | 91,758688560 s |

L'intermédiaire vert **712/712** utilisait une capture scratch injectée par env
dans les deux nouveaux cas navigateur. Le contre-audit a détecté que la commande
publique navigateur n'avait pas cette précondition : le harnais est corrigé par
la fixture du dépôt et son test Python de provenance, sans affaiblir les
assertions ni modifier le produit. Seuls Python/Chromium modifiés sont renouvelés ;
Node/SQL verts ne le sont pas. Une dernière passe Python suit le renforcement du
cas Documents existant pour exercer le vrai store, pas un faux listing qui lève.
Aucun échec après patch ; tous les échecs causaux avant patch sont conservés.

Comparaison finale : **374 + 206 + 104 + 29 = 713/713**, soit les **679 historiques
conservés**, 22 nouveaux cas (18 Python, deux Chromium, deux SQL), plus les
12 cas existants du module voisin renommage ajouté à la commande. Les
**41 sélecteurs historiques + deux modules Python = 43 sélecteurs** sont :

```sh
m2_python \
  tests.test_server_active_documents_contract \
  tests.test_server_workspace_folders_contract \
  tests.test_server_chat_route_transport_contract \
  tests.test_server_chat_conversation_id_contract \
  tests.test_server_chat_document_integrity_contract \
  tests.integration.frontend_chat.test_frontend_chat_contract \
  tests.unit.core.test_workspace_folders_contract \
  tests.unit.chat.test_chat_llm_flow \
  tests.unit.chat.test_chat_llm_flow_boundaries \
  tests.unit.chat.test_chat_stream_control \
  tests.unit.core.test_document_workshop_canonical_paths \
  tests.unit.core.test_document_workshop_admission \
  tests.unit.core.test_document_workshop_provider_progress \
  tests.unit.core.test_workspace_documents_ingestion \
  tests.test_server_document_workshop_contexts_contract \
  tests.unit.core.test_workspace_folder_documents \
  tests.unit.core.test_workspace_file_selection_prompt \
  tests.unit.core.test_active_document_text_extraction \
  tests.unit.core.test_document_upload_limits \
  tests.unit.core.test_workspace_nextcloud_compensation_etag \
  tests.unit.core.test_workspace_file_ocr_service \
  tests.unit.core.test_workspace_document_read_client_m2 \
  tests.unit.core.test_workspace_document_source_extraction_m2 \
  tests.unit.core.test_workspace_document_adoption_m2 \
  tests.unit.core.test_workspace_folders_listing_failure \
  tests.unit.core.test_workspace_folder_rename_commit_projection

m2_node \
  app/tests/unit/frontend_chat/test_active_documents_module.js \
  app/tests/unit/frontend_chat/test_canonical_chat_submission.js \
  app/tests/unit/frontend_chat/test_lot9_load_order_golden.js \
  app/tests/unit/frontend_chat/test_threads_folder_binding_module.js \
  app/tests/unit/frontend_chat/test_threads_sidebar_module.js \
  app/tests/unit/frontend_chat/test_workspace_folders_module.js \
  app/tests/unit/frontend_chat/test_threads_list_renderer_module.js \
  app/tests/unit/frontend_chat/test_workspace_folder_sidebar_boundaries.js

m2_node --test-concurrency=1 \
  app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_workshop.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_adoption_reasons.js \
  app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js

m2_sql tests.integration.document_workshop.test_adoption_postgresql tests.integration.document_workshop.test_context_store_postgresql

```

Commandes ciblées/baseline effectivement exécutées avec les mêmes wrappers :

```sh
m2_python tests.unit.core.test_workspace_folders_contract \
  tests.test_server_workspace_folders_contract \
  tests.unit.core.test_workspace_folder_rename_commit_projection \
  tests.unit.core.test_workspace_nextcloud_compensation_etag
m2_python \
  tests.test_server_workspace_folders_contract.ServerWorkspaceFoldersListingFailureTests.test_p2_m2_04_control_successful_empty_listing_is_200 \
  tests.test_server_workspace_folders_contract.ServerWorkspaceFoldersListingFailureTests.test_p2_m2_04_db_failure_is_explicit_json_through_real_chain
m2_python tests.unit.core.test_workspace_folders_listing_failure
m2_python tests.unit.core.test_workspace_folders_listing_failure \
  tests.test_server_workspace_folders_contract.ServerWorkspaceFoldersListingFailureTests
m2_python tests.unit.core.test_workspace_folders_listing_failure \
  tests.test_server_workspace_folders_contract.ServerWorkspaceFoldersListingFailureTests \
  tests.unit.core.test_workspace_folder_rename_commit_projection
m2_sql \
  tests.integration.document_workshop.test_adoption_postgresql.AdoptionPostgresqlTests.test_folder_listing_keeps_order_projection_and_deleted_filter \
  tests.integration.document_workshop.test_adoption_postgresql.AdoptionPostgresqlTests.test_real_sql_listing_error_is_explicit_and_recovers_without_retry
m2_node --test-concurrency=1 --test-name-pattern='P2-M2-04' \
  app/tests/integration/frontend_browser/test_frontend_browser_document_inventory_publication.js
m2_python \
  tests.test_server_workspace_folders_contract.ServerWorkspaceFoldersListingFailureTests.test_p2_m2_04_browser_fixture_matches_actual_backend_responses
```

**Contre-audit.** Aucun écrivain/frontend modifié, aucun autre getter corrigé.
Les appels de listing directs et dynamiques sont recensés. Erreur absorbée en
vide, publication partielle, compteur/succès faux, exception non traitée,
validation de conflit permissive, compensation interrompue, replay et détail
HTTP ont été inspectés et couverts aux frontières correspondantes. Les gardes
P2-M2-01/02/03 et leurs probes navigateur restent dans la comparaison, avec chat,
upload, thème et DOM. Revue indépendante statique par le skill
`requesting-code-review` : aucun nouveau finding dans le delta final ; le reviewer
n'a exécuté aucun runner ni modifié le checkout.

**Finding indépendant P2-M2-05, ouvert hors lot à la livraison P2-M2-04.**
Sa reproduction et correction séparées figurent ensuite ci-dessous. Inspection du parent
`0a5b4b55` et du delta : `_summary` de la réconciliation utilise déjà
`_example_status(after or before)`. Si une lecture finale réussit réellement
avec `[]` après un snapshot initial contenant un exemple, `counts_after.active`
vaut zéro mais `examples` peut conserver `present_reconciled`/`present_pending`
issus de l'ancien snapshot. Ce point concerne un succès vide réel, pas la lecture
impossible P2-M2-04 désormais représentée par `None`. Constat statique, aucune
reproduction dynamique exécutée ; pas de perte SQL/DAV inférée. Correction et
preuve causale demandent un lot distinct ; il n'est ni réparé ni clos ici.

**Nettoyage et livraison.** PostgreSQL possédé arrêté/supprimé après les suites
SQL (exits 0, 0,173 s murales), socket vide retiré et absence vérifiée, données
tmpfs détruites. Autres runners `--rm`, scratch possédé retiré après consignation
des preuves (31 fichiers), absence vérifiée. Aucun artefact d'autrui supprimé.
Diff et périmètre vérifiés, 58 liens locaux valides, `git diff --check` exit 0
avant commit ; le retour final atteste SHA/parent, push, worktree propre,
HEAD/upstream/M2 distant égaux, divergence `0/0` et M1/M0/main inchangés.
Aucun déploiement, migration opérateur, rebuild/restart, modèle ou DAV live.
Livraison runtime/health et DAV live restent ouverts ; M3–M10/Z non commencés.
Arrêt après vérification Git, sans enchaînement P2-M2-05 ou M3.

#### Correction indépendante P2-M2-05 — 5 octobre 2026

**Disposition : corrigé sur code et preuves ; livraison runtime ouverte.**
Base revalidée dans l'IDE : `pwd` et toplevel `/opt/platform/fridadev`, branche
`FridaV1-Document-Workshop-M2`, worktree propre, divergence `0/0`, HEAD/upstream/
M2 distant `6b891eb39b39069116302f9fdfba047f445fbf16`, parent
`0a5b4b553a20e0230991be34fd7b23354885395e`. M1/M0/main correspondent aux SHA
consignés dans le lot précédent ; aucune modification de ces branches.
Les historiques 536/567/594/679/713 et G-R1–G-R4 restent conservés. À la livraison
P2-M2-04, ce finding était seulement statique et ouvert : cette provenance n'est
pas remplacée par la preuve dynamique du présent lot.

**Cause, rouge et contrôle.** L'expression
`_example_status(after or before or [])` réutilisait l'inventaire initial lorsque
la liste finale était connue mais vide. La reproduction passe par la vraie
entrée `reconcile_existing_workspace_folders`, le vrai store et ses deux SELECT,
avec `ListingDatabase` et le client DAV synthétique existant. L'état initial
contient l'exemple synthétique « Philosophie » lié ; la racine et ses quatre
sous-répertoires ont des réponses distantes simulées valides. Pendant
`folder_status`, le harnais vide les lignes destinées à la relecture SQL finale.
Avant patch : `counts_after.active=0`, record final `expected_example_absent`,
mais résumé `present_reconciled` ; un rouge d'assertion sur l'accord des deux.
Contrôle identique où les lignes restent présentes : vert. Aucun sommeil,
remplacement du résumé ou mutation de données opérateur.

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets
de bord ? » Le correctif retient une seule expression :
`_example_status(after) if after is not None else None`. Le snapshot final connu,
vide ou non vide, fait exclusivement autorité pour les exemples du résumé.
Après échec de lecture, exemples et compteurs finaux restent `None`, avec verdicts
et raison de P2-M2-04 inchangés. Compteurs initiaux, records historiques, record
final, catégories d'exemples et calcul de `ok` sont conservés. Aucune lecture,
mutation, compensation, reprise ou action de réconciliation ajoutée.

**Fichiers et preuves ciblées.** Produit :
`app/core/workspace_folder_nextcloud_reconcile.py`, une ligne. Trois nouveaux
cas dans `app/tests/unit/core/test_workspace_folders_listing_failure.py` : vide
final causal, contrôle présent et état final non vide différent (sous-cas linked,
local_only, conflict, error). Ils affirment résumé = record final, historique
initial conservé, exactement deux connexions/deux SELECT, aucune écriture SQL,
une observation racine et quatre observations des sous-répertoires, zéro
MKCOL/MOVE/DELETE. Le contrôle vide initial existant de
`app/tests/unit/core/test_workspace_folders_contract.py` utilise désormais le
vrai store, conserve ses anciennes assertions et vérifie une seule lecture,
zéro DAV/mutation et cohérence du record final. Les deux erreurs finales connues
P2-M2-04 sont réutilisées, sans nouvelle assertion permissive ni nouveau cache.
Documentation : même roadmap, contrat M2 et affirmation courante du hub.

**Runners et résultats.** Les fonctions `m2_python`, `m2_node`, `m2_sql` et les
quatre invocations exactes des **43 sélecteurs** de la
[comparaison P2-M2-04](#correction-indépendante-p2-m2-04--5-octobre-2026)
sont exécutées sans changement de sélection. Seul le chemin du socket SQL est
adapté au scratch possédé `/tmp/fridadev-p2-m2-05-dhgjv91v`. Images existantes
vérifiées (`fridadev-audit-py:latest`, Playwright v1.54.0-jammy, postgres:16-alpine),
sans pull/installation, réseau coupé, rootfs/checkout read-only, env vidée,
bytecode Python désactivé, cache navigateur existant, dotenv/symlink absents.
PostgreSQL dédié `fridadev-p2-m2-05-proof-pg`, socket/conteneur initialement absents,
mount `/var/run/postgresql` dès initialisation, tmpfs et aucun TCP ; readiness
`pg_isready` exit 0 en 1,380 s murales avant runner SQL. Les deux modules SQL
s'exécutent en série sur ce seul schéma synthétique.

| Passe | Résultat | Exit | Durée interne |
| --- | --- | --- | --- |
| Baseline Python ciblée au parent | 63/63 | 0 | 0,039 s |
| Contrôle présent + causal vide avant patch | 1 vert, 1 rouge sur 2 | 1 | 0,598 s |
| Ciblé après patch, mêmes cas et frontières | 6/6 | 0 | 0,004 s |
| Cinq modules voisins | 103/103 | 0 | 0,471 s |
| Comparaison Python | 377/377 | 0 | 25,770 s |
| Comparaison Node | 206/206 | 0 | 0,575470003 s |
| Comparaison Chromium, concurrence 1 | 104/104 | 0 | 91,944391365 s |
| Comparaison PostgreSQL isolé, modules en série | 29/29 | 0 | 25,230 s |

Comparaison finale : **377 + 206 + 104 + 29 = 716/716**, zéro skip. Les **713 cas
historiques sont conservés**, avec leurs 12 cas préexistants du voisin renommage ;
**trois cas Python seulement sont ajoutés**, aucun nouveau sélecteur. Le test vide
initial est renforcé, pas remplacé par un faux résultat attendu. Aucun échec
intermédiaire autre que le rouge causal avant patch ; aucune relance de suite
verte, exclusion ou modification frontend/harness navigateur.

Commandes ciblées exactes avec les mêmes wrappers :

```sh
m2_python tests.unit.core.test_workspace_folders_contract \
  tests.unit.core.test_workspace_folders_listing_failure
m2_python \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_p2_m2_05_present_final_inventory_control \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_p2_m2_05_final_empty_does_not_reuse_initial_examples
m2_python \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_p2_m2_05_present_final_inventory_control \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_p2_m2_05_final_empty_does_not_reuse_initial_examples \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_p2_m2_05_different_nonempty_final_inventory_is_authoritative \
  tests.unit.core.test_workspace_folders_contract.WorkspaceFoldersContractTests.test_nextcloud_reconcile_inventory_marks_expected_examples_absent \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_final_reconciliation_failure_keeps_completed_actions_and_unknown_final_counts \
  tests.unit.core.test_workspace_folders_listing_failure.WorkspaceFoldersListingFailureTests.test_final_reconciliation_listing_failure_after_client_failure_is_also_unknown
m2_python tests.unit.core.test_workspace_folders_contract \
  tests.unit.core.test_workspace_folders_listing_failure \
  tests.test_server_workspace_folders_contract \
  tests.unit.core.test_workspace_folder_rename_commit_projection \
  tests.unit.core.test_workspace_nextcloud_compensation_etag
```

**Contre-audit et limites.** Tous les appels de `_summary` sont inspectés : vide
initial, état final connu des deux branches de relecture et `_listing_failure`
avec `None`. Aucun repli vers les données anciennes, historique réécrit,
régression des erreurs P2-M2-04, I/O/action ajouté, duplication de chemin produit
ou extension du lot. Revue statique indépendante via `requesting-code-review` :
aucun nouveau finding dans le delta ; reviewer sans exécution de runner ni édition.
La réconciliation réelle est exercée avec DB/DAV synthétiques ; la comparaison
SQL utilise PostgreSQL réel isolé et les tests DAV loopback existants. Les cas
Chromium restent à transport simulé ; aucune preuve runtime opérateur,
DAV live, perte SQL/DAV ou parcours HTTP navigateur→Flask n'est déduite.

**Nettoyage et livraison.** Seul PostgreSQL possédé arrêté/supprimé après SQL
(exits 0, 0,174 s murales), socket vide retiré et absence vérifiée, données tmpfs
détruites ; autres runners `--rm`. Scratch possédé retiré après consignation des
preuves (18 fichiers), absence vérifiée, aucun artefact d'autrui supprimé.
Diff/périmètre vérifiés, 60 liens locaux valides, `git diff --check` exit 0 avant
commit. Le retour final porte commit/parent, push et alignement propre `0/0`,
HEAD/upstream/M2 distant égaux, M1/M0/main inchangés. Aucun merge, nouveau lot,
migration opérateur, rebuild/restart, installation, modèle/DAV live ou déploiement.
Migrations opérateur, livraison runtime/health et DAV live restent ouverts.
M3–M10/Z non commencés ; arrêt après vérification Git.

### M3 — Réservation durable et concurrence

**Statut au 6 octobre 2026 :** code/preuves hermétiques et contre-audit fermés sur
`FridaV1-Document-Workshop-M3`. Migration opérateur, rebuild/restart, health et
smoke runtime restent ouverts et hors autorisation. À la clôture M3, M4 était
non commencé ; son exécution autorisée du 6 octobre est consignée ci-dessous.
[Contrat M3](../../states/specs/frida-v1-document-workshop-m3-contract.md).

**Objectif :** empêcher double génération et commit tardif.
**Dépendances :** M0–M2 ; progression M0 et contexte M1–M2.
**Fichiers :** claims SQL, enveloppes chat/transport/finalisation, primitive
transactionnelle de snapshot, écritures pré-finales résumé/état herméneutique,
ordre des verrous M2, identité depuis l'unique soumission frontend.
**Interface :** identité tour/confirmation interne, propriétaire, génération et
lease technique ; aucun TTL du pending, carte/action/révision/exécution M4/M5.
**Propriétaire :** Celebrimbor. Aucun besoin plateforme installé.

- [x] Rouge causal : même tour soumis deux fois, tours concurrents normaux et
  scope A→B→A reproduits au M2 exact ; un démarrage principal après correction.
- [x] Tests SQL concurrents isolés avec connexions/processus indépendants ; voisins
  de sauvegarde/erreurs/streaming, providers synthétiques comptés et vrai transport.
- [x] Faux vert exclu : les doubles mémoire des anciens tests ne sont pas une
  preuve PostgreSQL ; autorité SQL réelle dans tous les nouveaux tests décisifs.
- [x] Aucune transaction maintenue pendant provider bloqué ; snapshots et fences
  atomiques, pas de replay automatique ni modification du contenu normal.
- [x] Succès JSON/flux, final locks, résumé intermédiaire, erreurs et secours
  raccordés ; perte, résultats tardifs et fermeture réelle du flux couverts.
- [x] Lease, inactivité documentaire M0, annulation et invalidation distingués ;
  préparation utile au-delà de 120 secondes ; confirmation interne ancienne valide.
- [x] Contre-audit indépendant et corrections causales fermés ; aucune route,
  préparation publique, M4, fournisseur live, DAV live ou runtime opérateur activé.
- [ ] **Rebuild requis à livraison runtime**, après migration opérateur coordonnée.
  Les courses SQL/lease/fencing/invalidation sont prouvées en isolation seulement.

#### Base et plan revalidés avant édition

`pwd` et toplevel : `/opt/platform/fridadev`. M2 propre ; fetch explicite sans pull ;
HEAD = upstream = M2 distant `6e8c61f5059350d8d15ded4b41b68f2e0d9acac3`,
parent `6b891eb39b39069116302f9fdfba047f445fbf16`, divergence `0/0`.
M3 absent local/distant, créé depuis ce commit exact avant toute édition.
M1 `c6f648badba96a60f1474db8d3f7404f97a2dda7`,
M0 `3eb2e34aa0622112ebb4a8700dbe0eec02e4a27a`,
main `e3e0d19290cb7ac275b3fd4b19c4b01dbc89f2cb` conservés.

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de bord ? »
Oui : partager seulement la primitive existante de snapshot sur connexion fournie,
plutôt que créer un autre store de messages. Le snapshot M2 était déjà atomique,
mais ouvrait/commitait sa propre connexion ; M1 n'avait ni claim ni génération.
Le chat pouvait démarrer deux providers et le scope A→B→A redevenait admissible.
L'acquisition est maintenant avant le travail protégé/providers, avec sauvegarde
utilisateur initiale et relecture du transcript après admission.

Le claim est détenu pendant le traitement effectif et la consommation du flux.
Snapshot + contrôle propriétaire/génération/scope + résultat sont une seule courte
transaction. La clôture durable reste avant succès JSON/terminal `done` ; une
clôture refusée ne devient pas un succès. Les erreurs ne contournent pas le fence.
Résumé et état herméneutique pré-final disposent également du fence sur leur
connexion d'écriture. Aucun appel réseau sous transaction.

Compatibilité sans `client_turn_id` : UUID serveur par requête, même exclusion,
aucune déduplication promise sans identité commune. Clavier/dictée/Dialogue passent
par la même soumission UUID. Répétition identifiée : relecture technique `409`, sans
nouveau provider/utilisateur ni reprise d'un tour interrompu. Demande incompatible refusée.

Lease **90 s**, renouvellement **15 s**, autorité PostgreSQL `clock_timestamp()` ;
`statement_timeout` local SQL **5 s**. Le superviseur de requête renouvelle pendant
le travail et cesse entre chunks/avant consommation ; close fonctionne même sans
premier `next()`. Ces paramètres ne changent ni le timeout fournisseur (défaut
source principal 900 s), ni les budgets/réglages, ni M0. Cadence accélérée à 0,02 s
uniquement dans le test de renouvellement, via le même code et le vrai SQL.
Le pending n'expire pas par âge ; preuve de confirmation interne avec contexte
créé en 2000 et ETag actuel, sans livraison pending produit.

#### Environnement de preuve et commandes

Aucune installation/pull. Images locales :

- `fridadev-audit-py:latest` : `sha256:486a8afeb2f62c7906194d3e1fee839387e55753bcad365120d18306502fafdc`.
- `mcr.microsoft.com/playwright:v1.54.0-jammy` : `sha256:55dfaaa282c98d5f4d328676e36eca5203b6494b97d9ef3ba0608d9e939e9523`.
- `postgres:16-alpine` : `sha256:87e04d274d186c7331d0e13c7c90c8b9f63b0d7ae94476c98a229a94d62c9745`, PostgreSQL **16.12**.
- `pgvector/pgvector:pg17` : `sha256:e34a81641384711daf8aedaed03223011d0274005b5afa0fa3c11917f9b745ae`, PostgreSQL **17.9**, vector **0.8.2**.

Deux conteneurs propres à M3 : `fridadev-m3-proof-pg-20261006` et
`fridadev-m3-summary-proof-pg-20261006`, données/tmp en tmpfs, rootfs readonly,
`--network none`, aucun port TCP (`-c listen_addresses=`), trust/db/user synthétiques
`m1proof`. Sockets dans `/tmp/fridadev-m3-proof-20261006/{pg-socket,vector-socket}`,
montés `/var/run/postgresql` dans PostgreSQL et readonly `/proof/sock` dans runners.
Le checkout est toujours readonly ; `.env` absent et non symlink vérifié avant Python.
DAV synthétique utilise uniquement le loopback du runner sans réseau externe.

Commandes exécutées, mêmes images/options que M1/M2 :

```sh
proof_root=/tmp/fridadev-m3-proof-20261006
mkdir -p "$proof_root/pg-socket" "$proof_root/vector-socket"
chmod 777 "$proof_root/pg-socket" "$proof_root/vector-socket"
docker run -d --name fridadev-m3-proof-pg-20261006 --pull never --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev \
  --mount type=bind,src="$proof_root/pg-socket",dst=/var/run/postgresql \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=m1proof -e POSTGRES_DB=m1proof \
  postgres:16-alpine -c listen_addresses=
docker run -d --name fridadev-m3-summary-proof-pg-20261006 --pull never --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev \
  --mount type=bind,src="$proof_root/vector-socket",dst=/var/run/postgresql \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=m1proof -e POSTGRES_DB=m1proof \
  pgvector/pgvector:pg17 -c listen_addresses=
```

Readiness positive au démarrage par `pg_isready` sur les sockets isolées.
Les extraits ci-dessous tracent les commandes exécutées dans le wrapper
`set -euo pipefail` ; ils ne sont pas des runners autonomes à copier isolément.
Une reproduction conserve les préconditions M2 complètes : aucun conteneur,
répertoire/socket de preuve préexistant, absence de `.env` et readiness ; ne
jamais écraser une ressource existante. Les fonctions de preuve `m3_python`, `m3_node`, `m3_sql`, `m3_vector` sont les
wrappers M2 conservés plus haut, renommés avec les sockets M3 ci-dessus. Invocation
Python effective commune :

```sh
test ! -e /opt/platform/fridadev/app/.env && test ! -L /opt/platform/fridadev/app/.env
docker run --rm --pull never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev \
  --mount type=bind,src=/opt/platform/fridadev,dst=/workspace,readonly \
  --workdir /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest \
  -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/workspace EMBED_BASE_URL=https://embed.invalid \
  CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid \
  python -m unittest <sélecteurs>
```

SQL ajoute le bind readonly de la socket choisie vers `/proof/sock` et les variables
`M1_PROOF_PG_SOCKET=/proof/sock`, `M2_PROOF_PG_SOCKET=/proof/sock`,
`M3_PROOF_PG_SOCKET=/proof/sock` ; pgvector ajoute `M3_VECTOR_PROOF_PG_SOCKET=/proof/sock`.
Node reprend l'image Playwright et le bind readonly `/home/tof/.cache/ms-playwright`
vers `/proof/browsers`, workdir `/workspace`, env vide plus PATH/HOME et
`PLAYWRIGHT_BROWSERS_PATH=/proof/browsers`, `node --test` ; Chromium
`--test-concurrency=1`. `PYTHONPATH=/workspace` est ajouté pour la découverte élargie
qui importe le package `benchmark` versionné à la racine ; aucune dépendance installée.
Les premières baseline/ciblés n'en avaient pas besoin.

Comparaison : les **43 sélecteurs M2 explicités ci-dessus**, identiques, fonctions
renommées `m3_*`. Le nouveau test Node canonique ajoute un cas aux 206 historiques.
Voisins supplémentaires, dix sélecteurs :

```sh
m3_python \
  tests.unit.core.test_conversations_store_save_result \
  tests.test_conv_store_phase4_database tests.unit.chat.test_chat_session_flow \
  tests.test_server_chat_synthetic_logs_contract tests.integration.chat.test_chat_input_mode_route \
  tests.unit.memory.test_summarizer_phase4 tests.unit.memory.test_summarizer_phase13 \
  tests.unit.memory.test_memory_trace_summary_store_boundary \
  tests.unit.memory.test_hermeneutic_node_state tests.unit.core.test_chat_hermeneutic_node_state
m3_sql \
  tests.integration.document_workshop.test_turn_claims_postgresql \
  tests.integration.document_workshop.test_claim_transport_postgresql \
  tests.integration.document_workshop.test_claim_adoption_postgresql
m3_vector tests.integration.document_workshop.test_claim_summary_postgresql
m3_python \
  tests.test_server_chat_hermeneutic_insertion_contract tests.test_server_chat_web_runtime_contract \
  tests.test_server_phase4 tests.test_server_phase8 \
  tests.unit.chat.test_chat_workspace_folder_notes_prompt tests.unit.core.test_chat_main_payload_boundary \
  tests.unit.golden.test_lot0_identity_goldens tests.unit.golden.test_lot4_stimmung_causal_goldens \
  tests.unit.golden.test_lot9_golden_harness tests.unit.golden.test_l7_6_stimmung_finalization_integrity
m3_python discover
```

La baseline de ces voisins a été mesurée au M2 avant leur modification : 41 tests
persistance/transport, 18 mémoire, neuf voisins d'état herméneutique, puis 84 goldens
sur une archive Git du M2 exact readonly (app et benchmark). Ce sont des extensions
de sélection, distinctes des nouveaux tests M3.

#### Rouges causaux et contre-audit

Le probe gelé du transport, conservé dans
`app/tests/support/m3_baseline_causal_probe.py` (exclu de discovery), est rejoué
sur archive du M2 exact : deux requêtes
simultanées atteignent **deux fois le modèle principal**, pour même ID et IDs
concurrents ; A→B→A rendait le contexte `200`. Trois vrais failures en **5,287 s**,
exit 1. Un premier probe comptait aussi la validation constitutive ; la reprise
compte exclusivement `openrouter/runtime-main-model`, sans supprimer ces appels.
Aucune reproduction n'est fondée sur un import absent. Le probe conservé exige
`M3_BASELINE_PROBE_SOCKET=/proof/pg-socket` ; rejeu après conservation : trois
failures en **5,124 s**, exit 1, deux appels principaux dans chaque concurrence.
Reproduction du rejeu dans le runner Python M2 readonly : checkout bind remplacé
par l'archive obtenue avec `git archive 6e8c61f5059350d8d15ded4b41b68f2e0d9acac3 app benchmark`,
probe readonly monté `/proof/m3_probe.py`, socket isolée readonly `/proof/pg-socket`,
env `PYTHONPATH=/workspace:/workspace/app` et `M3_BASELINE_PROBE_SOCKET=/proof/pg-socket`,
commande `python /proof/m3_probe.py`. Le probe est uniquement M2, jamais un test
SQL vert M3 ni un composant produit.

| Défaut reproduit | Rouge, exit 1 | Correction/proof réelle |
| --- | --- | --- |
| Transport M2 double démarrage et scope restauré | 3 failures, 5,287 s | Un seul détenteur/provider/utilisateur ; relecture sans replay. |
| Résumé tardif sauvegardé après lease perdu | 1 failure, 0,844 s | Vrai MemoryStore/pgvector fence la connexion d'écriture. |
| Annulation laissant le contexte editing | 1 failure, 1,050 s (plus erreur de nouvelle signature non causale) | Contexte et claim cancelled atomiquement. |
| Jeton transplanté vers une autre conversation de même génération | 1 failure, 1,091 s | Conversation/contexte de la ligne liés au jeton, vert 0,901 s. |
| Lien de répertoire A→B→A / contexte mutable | 2 failures, 1,018 s | Triggers irréversibles et identité immuable. |
| Suppression réelle répertoire contre claim | 1 failure, 1,866 s | Ressources downstream NOWAIT, mutation légitime aboutit. |
| Adoption/suppression fichier et rotation cache identique | 2 failures, 1,911 s ; DeadlockDetected explicite | Mêmes verrous M2 réordonnés ; champs de scope positifs. |
| Delta provider assimilé à done avant snapshot | 1 failure, 0,963 s | Done exige résultat SQL réussi ; flux vide légitime conservé. |
| Échange nominal JSON sans résultat canonique (défaut injecté à la frontière existante) | 1 failure, 0,919 s | Succès JSON exige aussi outcome SQL succeeded. |
| Renommage répertoire aller-retour | 1 failure, 0,950 s | Invalidation durable au changement de nom. |

Le rouge adoption recompose uniquement l'ancien ordre M2 et le prédicat initial
M3 trop large dans des mounts scratch readonly. Il reproduit une régression du
patch intermédiaire, pas un finding prétendument présent avant les triggers M3.
Le probe terminal utilise un vrai delta synthétique dans une fence de code ouverte,
le normalizer réel et le transport réellement consommé. Le probe simple sans
fence avait sauvegardé une réponse : il n'est pas retenu comme rouge causal.

Contre-audit indépendant `m3_counteraudit` en lecture seule (compétence
`superpowers:requesting-code-review`) : trois P2 (verrous, cache, faux done),
régression vide prévenue, corrections relues ; approbation finale après preuves
53/53 SQL, 2/2 pgvector et 59/59 voisins sur les derniers deltas.
Les deux P3 documentaires (statut §8 et portée des fragments de commandes)
sont corrigés et relus. Aucun autre finding M3 confirmé restant.
La roadmap/hub sont vérifiés séparément après rédaction.

#### Résultats et limites des preuves

| Sélection exécutée | Résultat | Exit | Durée suite |
| --- | --- | --- | --- |
| Baseline M2 Python / Node / Chromium / SQL, avant édition | 377 + 206 + 104 + 29 = **716/716**, aucun skip | 0 / 0 / 0 / 0 | 18,611 / 0,4774418 / 91,14398262 / 17,670 s |
| Extension baseline persistance / mémoire / état herméneutique | 41 + 18 + 9 = **68/68** | 0 / 0 / 0 | 1,086 / 0,061 / 0,002 s |
| Première comparaison historique M3 | **716/716**, aucun skip | 0 / 0 / 0 / 0 | 19,486 / 0,479271569 / 91,257983855 / 17,692 s |
| Comparaison finale 43 sélecteurs + un nouveau cas Node | 377 + 207 + 104 + 29 = **717/717**, aucun skip | 0 / 0 / 0 / 0 | 19,867 / 0,44542203 / 91,33331557 / 17,993 s |
| Voisins finaux (dix sélecteurs) | **68/68**, aucun skip | 0 | 0,890 s |
| Nouvelle matrice M3 SQL finale | **53/53**, aucun skip | 0 | 15,052 s |
| Résumé réel pgvector M3 final | **2/2**, aucun skip | 0 | 1,144 s |
| Extension dix sélecteurs goldens M2 / M3 | 84 exécutés de chaque côté ; 83 succès et un failure préexistant | 1 / 1 | 187,139 / 190,669 s |
| Découverte Python élargie finale, sélection chargée avant les derniers deltas | 3369 tests, un failure préexistant, 83 skips SQL sans socket | 1 | 659,873 s |

Soit **772/772** sur la comparaison et les nouveaux tests (717 + 55), plus les
68 voisins existants. Les 83 goldens supplémentaires réussis sont séparés du
golden de routes préexistant défaillant, sans le masquer ni l'absorber.

La découverte élargie initiale : **3339 tests, 502,321 s, exit 1**, 26 failures,
un import `benchmark` absent du PYTHONPATH, 70 skips (dont SQL sans socket dans
cette commande ordinaire). Les défauts de fixtures introduits par le contrat M3
sont corrigés sans retirer les assertions historiques : sauvegarde initiale
exposée séparément de la vue historique final/summary, doubles claims explicites
sur services directs, nouveau kwarg summarizer, inspect source incluant le helper
réservé, proxy requests sous-jacent toujours inspecté et réservation vérifiée.
Les callbacks voix/Dialogue, Stimmung, cardinalités Identity et budgets restent testés.
Les doubles ne constituent aucun bypass en production ; les suites SQL raccordées
utilisent les vrais claims et snapshots.

La découverte finale exécute **3369 tests en 659,873 s, exit 1**, avec le seul
failure de routes préexistant et 83 skips SQL faute de socket dans cette commande.
Elle avait chargé sa sélection avant le dernier garde JSON et la préservation
des champs de diagnostic snapshot : ces deltas ont ensuite été vérifiés par
les **55/55 SQL** et **59/59 voisins**, sans prétendre à une nouvelle découverte
globale du dernier état. Le dernier nouveau cas SQL est ainsi exécuté explicitement,
pas compté dans cette découverte.

**P3-M3-baseline-route-golden, historique hors patch M3 initial :** le golden des routes attend 123 alors
que M2 expose déjà 128 routes. Reproduit au commit M2 exact : 84 tests en 187,139 s,
83 succès et ce seul failure ; après adaptation M3 : mêmes 84 tests en 190,669 s,
83 succès et le même failure. Requalifié défaut préexistant de fixture, non absorbé
par M3 ; aucune route ajoutée et aucune assertion historique changée. La découverte
globale n'est pas déclarée entièrement verte.

**Correctif distinct P3, 2026-10-06 :** revalidé sur M3
`c9275847d81c2fedd9147bbacd5798b44eacca2a`, propre et aligné avec origin (`0/0`).
Le rouge ciblé reproduit `128 != 123` : un test, 0,787 s, exit 1. La différence
détaillée est exactement les cinq routes speech, création/lecture de contexte,
adoption et listing distant. Méthodes/endpoints contrôlés dans les déclarations ;
gardes contrôlées dans les deux `before_request` serveur. Les contextes rejoignent
la famille de test `conversations_documents_workspace`. L'attendu reste un
inventaire explicite avec égalité exacte ; le nombre seul n'est pas la preuve.
Aucun handler, route produit, garde ou classement applicatif modifié.

Preuves exécutées avec checkout readonly, environnement vidé, réseau `none`,
aucune installation/pull ni DB opérateur. Rouge dans l'image existante
`platform-fridadev-app:local` ; vert dans `fridadev-audit-py:latest`, wrapper
Python M3 ci-dessus, sans bind SQL. Commandes (noms complets) :

```sh
python -m unittest tests.unit.golden.test_lot9_golden_harness.Lot9GoldenHarnessTests.test_route_map_is_exact_by_family_method_endpoint_and_guard
python -m unittest tests.unit.golden.test_lot9_golden_harness.Lot9GoldenHarnessTests.test_route_map_is_exact_by_family_method_endpoint_and_guard tests.unit.golden.test_lot9_golden_harness.Lot9GoldenHarnessTests.test_route_map_validator_rejects_controlled_mutations
python -m unittest tests.unit.golden.test_lot9_golden_harness tests.test_server_chat_route_transport_contract tests.test_server_document_workshop_contexts_contract tests.test_server_admin_non_settings_contracts tests.integration.chat.test_chat_dialogue_audio_routes
```

Vert ciblé : **2/2**, 0,700 s, exit 0. Module golden et voisins : **59/59**,
1,705 s, exit 0, aucun skip. Sensibilités conservées : route absente,
supplémentaire, méthode/famille/garde altérées ; endpoint altéré ajouté.
Diff contre-audité, `git diff --check` et périmètre tests/docs vérifiés.
Les échecs historiques M2/M3 et discovery ci-dessus restent historiques : aucune
nouvelle découverte globale n'est revendiquée. Le hash complet du correctif et
son alignement distant sont relevés avant la création de M4 et dans son contrat.
Migration/runtime et fournisseurs live restent hors de cette livraison P3.

Échecs intermédiaires conservés : mauvais mount socket (3 errors, 0,763 s),
indentation extraction initiale (import, pas rouge causal), fixture SQL ancienne
sans migration/wiring (12 tests, 23,172 s, trois failures), fixtures chat ciblant
involontairement l'initial au lieu du final (21 tests : 6 failures/1,454 s, puis
1/1,410 s, corrigés 21/21 en 1,594 s), provider count incluant validation (24 tests,
6 failures/6,425 s), observation d'une autre transaction courte confondue avec un
provider sous transaction (28 tests, 1 failure/7,547 s), attente HTTP 503 contre
le refus correct 409 de perte (32/37 tests, 1 failure/8,594 et 9,748 s), imports de
fixture de scope (2 errors/0,962 s), ancien contexte daté via UPDATE incompatible
avec immutabilité (44 tests, 2 errors/12,397 s ; INSERT synthétique daté corrigé),
fixture suppression fichier sans table selections (3 tests, 1 failure/1,814 s).
Aucun de ces écarts de harnais n'est présenté comme une faille produit ni un rouge
causal. Intermédiaires verts : snapshot27/0,008 s, SQL9/2,716 puis2,728 s,
39/11,563 s, 48/13,488 s, 51/15,461 s, mémoire27/0,047 s,
Nodecanonique13/0,11479011 s, résumé1/0,893 s puis2/1,345 s.
Après préservation des champs privés historiques id normalisé/stage/err_class
dans l'extraction : 22 voisins snapshot en0,010 s, puis 59 voisins
snapshot/transport/flux en1,171 s, exits0. Matrice intermédiaire52/16,742 s et
résumé2/1,166 s conservés avant le dernier garde JSON.

Les rendez-vous SQL et providers bloqués démontrent la causalité ; les attentes
maximales de 10 s bornent seulement les tests. Les pertes de lease sont forcées
par horloge SQL de fixture, puis une nouvelle acquisition génère le successeur.
Migration rejouée avec relecture indépendante ; aucun tableau actions/révisions/
reçus/artefacts créé. Préparation publique inactive, aucune règle documentaire
appliquée au chat normal, aucun pending/confirmation produit livré.

Nettoyage des seuls conteneurs/sockets/temporaires M3 après preuves, absence vérifiée.
Le retrait initial du scratch a rencontré les sockets résiduelles dans les
répertoires sticky possédés par PostgreSQL ; un runner `postgres:16-alpine`
existant, `--rm --pull never --network none --read-only --user 0`, avec le seul
scratch M3 bind writable, a retiré les quatre fichiers socket/lock explicitement.
Exit 0, puis retrait complet du scratch ; aucune permission d'hôte modifiée.
Liens touchés,
`git diff --check`, diff utile et périmètre contrôlés avant commit. Le retour final
porte commit/push/upstream, alignement propre `0/0`, ascendance M2 et références
M2/M1/M0/main inchangées. Aucun merge/rebase/reset/force-push, migration opérateur,
rebuild/restart, modèle/DAV live, canari, renderer ou démarrage M4.

### M4 — Préparation Markdown dans un tour canonique

**Objectif :** vraie parole, appel documentaire unique, réponse/pending réhydratables.
**Dépendances :** M0–M3.
**Fichiers :** service de tour, agent/contrat, revisions/actions, branche chat_service,
finalisation et UI.
**Interface :** prepared/clarify/refuse et commit de fin de tour commun.
**Propriétaire :** Celebrimbor.

- [x] Rouge causal : un appel documentaire/zéro échange normal ; échec de commit
  pending → aucun succès ; refresh → même action.
- [x] Tests final lock/persistance/stream/provenance voisins ; panne à chaque
  écriture, sortie tronquée valide et refus du fallthrough normal.
- [x] Tests de progression et annulation réelles, attente initiale sans événement,
  données tardives après échec fermé et pending non expirant avec le temps.
- [x] Faux verts : absence d'assertion sur appels normaux, stores finalisés séparément
  mais toujours disponibles, generator jamais réellement consommé.
- [x] Interdire canonical dans transcript, aperçu, retry et contamination des facultés.
- [x] Synchroniser tour/ingestion/observabilité ; modèle live sous GO distinct.
- [x] Écriture inactive ; activation complète interdite avant M6.
- [x] Fermer sauvegarde utilisateur initiale et transaction finale atomiques.

#### Exécution M4 du 6 octobre 2026

Relevé historique de la livraison initiale conservé, déclaration de comptes
rectifiée par l'[erratum P3-M4-03](#erratum-documentaire-p3-m4-03--6-octobre-2026)
ci-dessous. Il ne décrit pas une nouvelle exécution ni l'état courant des findings.
Base exacte : correctif P3
`9f10531ae9c799f4afc769c97ea2d48659f1c3d3`, poussé/vérifié propre sur M3 avant
création de `FridaV1-Document-Workshop-M4`. Les deux livraisons ont des commits
séparés ; le hash M4 et les contrôles distants sont fournis au retour final.

Le [contrat M4](../../states/specs/frida-v1-document-workshop-m4-contract.md)
décrit les frontières du tour, de la persistance, du transport et de l'UI ;
l'[artefact daté content-free](../../states/baselines/document-workshop/frida-v1-document-workshop-m4-20261006.json)
porte les commandes/sélecteurs publiés, comptes déclarés, durées/exits et écarts
intermédiaires ; son renvoi P3 retire le total contesté comme référence reproductible.

- Baseline P3 archivée et rejouée : **840/840**, zéro skip, soit 377 Python,
  82 PostgreSQL, 2 pgvector, 68 voisins, 207 Node et 104 Chromium.
- Déclaration finale initiale sur `2cbeb7fa…` : **1 198/1 198**, annoncés verts,
  zéro skip, exits 0 : 739 Python
  (197,370 s), 82 PostgreSQL historiques (32,171 s) + 39 M4 (20,277 s),
  2 pgvector (1,671 s), 211 Node (0,541363126 s), 104 Chromium historiques
  (91,290776034 s) et 21 M4 (16,708937178 s).
  La sélection exacte du run annoncé reste inconnue. Les sélecteurs frontend
  publiés exécutent 424 Node et 107 Chromium historiques dans le rejeu P3 ;
  les durées ci-dessus restent celles de la déclaration originale.
- Runs de sous-sélections non additifs : 324/324 enveloppe/voisins (8,492 s),
  89/89 transport/M0 (9,449 s), 25/25 pannes SQL (13,169 s), 8/8 compteurs
  du tour (3,916 s). Le run commun SQL 118/118 (52,031 s) est repris dans ces
  82 + 39, jamais additionné une seconde fois.
- Nominal réel `/api/chat` : vrai user unique, 1 principal documentaire,
  0 principal normal, 2 constitutifs synthétiques comptés séparément. Prepared,
  clarify/refuse, réhydratation, provenance main_model et done daté éprouvés.
- Connexions SQL indépendantes et rendez-vous : rollback initial et chaque
  écriture finale, triggers atteints même après rollback, exclusion/fencing,
  lease/scope, annulation/résultat tardif/course commit, supersession et SHA
  stable après JSONB. Pas de transaction conservée pendant le réseau.
- HTTP physique synthétique : corps admis exact, JSON/SSE, framing/TLS,
  attente bloquée, EOF/reset réel, keepalives seuls, horloge exacte 120 et
  reprise DNS incapable d'ouvrir une socket tardive. Aucun provider réel.
- Chromium monté à fetch simulé : thèmes/compositions, cartes compactes,
  preparing/pending, cancel/refus/late/refresh, calls comptés et aucun canonical
  public. La déclaration de 104 historiques est rectifiée ci-dessous ; le rejeu
  des neuf fichiers historiques exécute 107 cas.

Rouges et adaptations : 409 M3 au lieu de préparation ; deux assertions static
frontend devenues étroites et un couplage scope M2/projection M4, corrigés sans
relâchement ; signatures/identités/provenance de fixtures explicitées ; absence
du répertoire ignoré vide app/conv et des node_modules dans l'archive corrigée
uniquement dans le runner, sans installation. Aucun rouge d'import absent ne
constitue la preuve causale. Les détails de chaque run restent dans l'artefact.

Revue indépendante et contre-audit : P2 DNS retenait la requête malgré transport
annulé ; P2 surface acceptait JSON canonical pur/préfixé ; P2 GET suspendu
retenait le garde chat ; P3 libellés exposaient des codes internes. Tous corrigés
et revalidés indépendamment. Le dernier contre-audit a corrigé le refus d'une
préparation Markdown par un PNG non mobilisé, tout en conservant NFC/casefold.
Il a aussi rétabli la propagation des interruptions de processus après nettoyage
de la réservation : rouge causal KeyboardInterrupt, puis 39/39 SQL verts.
La revue initiale concluait sans finding confirmé vivant ; le contre-audit
postérieur ci-dessous remplace cette conclusion comme état courant. La conformité sémantique d'une
prose arbitraire reste une obligation du prompt, sans preuve fournisseur live.

Migration M4 versionnée et testée uniquement dans PostgreSQL dédiés isolés.
Deux seules routes M4 (GET action et POST cancel), golden exact **130** ; aucune
confirmation active, mutation Nextcloud, route chat parallèle, reçu ou renderer.
Le service de scope M2 reste indépendant de la projection HTTP des actions.
Les contrats vivants tour/ingestion/continuité/observabilité et M0–M3 sont
synchronisés, leurs preuves historiques préservées. Ressources temporaires
créées par ce lot nettoyées avant livraison ; résultat technique durable conservé.

- [ ] Migration opérateur, rebuild/restart/déploiement, health et recette runtime.
- [ ] Provider/DAV live sous GO distinct et recette matérielle Safari.
- [ ] Confirmation/exécution M5, parcours complet Markdown/reçu M6.

#### Contre-audit M4 — correctif borné P2-M4-01 du 6 octobre 2026

Base vérifiée : `2cbeb7fa59be5751502079a1eb6857c2f9977ef2`, HEAD/upstream/distant
égaux, worktree propre et divergence 0/0 ; parent et M3 distant exacts
`9f10531ae9c799f4afc769c97ea2d48659f1c3d3`. Correction sur la même branche M4.

| Finding | État à la livraison P2-M4-01, conservé |
| --- | --- |
| P2-M4-01 | Fermé : cancel A pending annulait aussi B preparing ; correctif ciblé prouvé sur Flask/PostgreSQL et contre-audité indépendamment. |
| P2-M4-02 | Ouvert : provenance perdue lors du gel du payload ; aucune modification de provenance, modèle, compteur ou budgets dans ce lot. |
| P3-M4-03 | Ouvert : sélecteurs/comptes historiques non concordants ; ancien relevé et artefact conservés, sans les prétendre corrigés. |

Ce tableau conserve l'état P2-M4-01 ; l'[erratum P3](#erratum-documentaire-p3-m4-03--6-octobre-2026)
porte la rectification ultérieure et l'état courant.

Ordre utilisateur avant M5 : P2-M4-01 puis contre-audit ; P2-M4-02 puis contre-audit ;
P3-M4-03 puis contrôle documentaire. Seul P2-M4-01 était autorisé dans ce lot daté.
Le [contrat M4](../../states/specs/frida-v1-document-workshop-m4-contract.md)
distingue l'annulation d'action de la fermeture globale du contexte M3.
L'[artefact P2-M4-01](../../states/baselines/document-workshop/frida-v1-document-workshop-p2-m4-01-20261006.json)
porte les listes exactes, comptes réellement exécutés, commandes/exits/durées,
adaptations de fixtures, sous-ensembles non additifs et nettoyage.

Baseline avant toute édition du dépôt : **1 414/1 414**, zéro skip, exits 0 :
739 Python (235,979 s), 121 SQL (56,311 s), 2 pgvector (1,536 s),
424 Node (1,467138683 s), 107 Chromium historiques (93,664197308 s),
21 Chromium M4 (16,756157819 s). Les listes sont développées, sans wildcard
ni recouvrement de sélecteurs ; ce relevé propre au lot ne ferme pas P3-M4-03.

Rouge causal avant patch : 2 cas, 1 échec (2,055 s, exit 1) ; contexte/A/B/claim B
cancelled, B HTTP503, exactement deux préparations/deux appels documentaires,
zéro échange principal normal. Contrôle seul sans cancel : 1/1 (1,484 s, exit 0),
B HTTP200/pending, A superseded. Requêtes Flask/stores réels, connexions SQL
indépendantes et rendez-vous explicite du provider, sans temporisation seule.

Le correctif modifie uniquement `document_workshop_actions.cancel` : transaction
courte, ordre conversation → ressources/contexte → claim ciblé si preparing → action,
relectures après verrouillage, révocation ciblée puis annulation de la seule action.
Pending n'a aucune écriture/verrou sur son claim historique. Contexte, successeur,
révision et transcript restent intacts. Helpers M3 et triggers globaux inchangés,
aucune migration nouvelle ni route, retry ou tour automatique ajouté.

Comparaison complète finale : **1 436/1 436**, zéro skip, exits 0 :

| Sélection exacte développée dans l'artefact | Cas | Durée | Exit |
| --- | ---: | ---: | ---: |
| Python, 57 modules | 739 | 233,545 s | 0 |
| PostgreSQL dédié, 9 modules | 142 | 79,250 s | 0 |
| pgvector dédié, 1 module | 2 | 1,284 s | 0 |
| Node, 34 fichiers | 424 | 1,305917226 s | 0 |
| Chromium historique, 9 fichiers | 107 | 95,431059486 s | 0 |
| Chromium M4, 1 fichier | 22 | 19,121124928 s | 0 |

La baseline de ce lot et la comparaison ont les mêmes sélections, sauf le nouveau
module SQL de 21 cas ; le fichier navigateur M4 gagne un cas net. Delta total :
**21 SQL + 1 navigateur**, sans autre extension de sélection. Le ciblé SQL 21/21
(21,195 s, exit 0) et les deux probes navigateur (3,126736087 s, exit 0) se
recouvrent avec la comparaison : aucun ajout aux 1 436.

Matrice SQL/HTTP : A pending + B preparing, contrôle nominal, annulation de B
avec fermeture physique HTTP et résultat tardif neutralisé, chat normal concurrent,
répétitions, états terminaux/absence/mauvais contexte, lease perdu, les deux ordres
annulation/commit, panne sur chacune des deux écritures et rollback, verrous NOWAIT,
scope/source collectifs conservés, nouvelle préparation explicite sans replay.
Le frontend produit n'a pas changé : le harnais conserve la carte et les identités
de B quand A est annulée, puis progression/pending/refresh ; annuler B préserve A
et refuse les réponses tardives. Les probes sont liées aux scénarios SQL réels,
sans présenter le faux fetch comme preuve de l'autorité backend.

Adaptations de fixtures documentées : deux erreurs de sonde SQL sous concurrence
de supervision, contrôle NOWAIT d'inspection déplacé après la fin du provider,
contrôle d'absence de transaction pendant le réseau conservé. Trois tests de verrou
externe diffèrent seulement la supervision concurrente jusqu'au rendez-vous puis
délèguent au store réel. Deux timeouts navigateur attendaient un GET non déclenché ;
le test déclenche maintenant le reload explicitement. Le faux backend utilise
ensuite GET/cancel par identité exacte, registre complet au refresh, révisions
distinctes et erreur 503/phase conformes à la chaîne réelle. Les échecs de harnais
restent distincts du rouge causal du produit.

Revue indépendante finale favorable à la fermeture de **P2-M4-01 seulement**,
sans nouveau finding confirmé sur ce delta : annulation collatérale, claim
historique/courant, ordre des verrous, panne entre écritures, course commit,
lease/successeur, invalidations collectives et projections navigateur vérifiés.
Nettoyage vérifié : les deux conteneurs SQL dédiés, leurs sockets et les trois
arbres temporaires du correctif ont disparu ; aucun reste sous leur préfixe.
À cette livraison P2-M4-01, M4 demeurait ouvert sur P2-M4-02/P3-M4-03.
M5 non commencé ; écriture/confirmation,
DB opérateur, provider/DAV live et runtime hors de ce correctif.

#### Contre-audit M4 — correctif borné P2-M4-02 du 6 octobre 2026

Base vérifiée avant édition : `722132631c2a70851c95d732420d64926895cba9`,
HEAD/upstream/distant alignés, worktree propre et divergence 0/0 ; parent
`2cbeb7fa59be5751502079a1eb6857c2f9977ef2`, M3 distant inchangé à
`9f10531ae9c799f4afc769c97ea2d48659f1c3d3`. Même branche M4, sans merge,
rebase, M5 ou intervention runtime. Les branches M0–M3 et main sont préservées.

| Finding | État à la livraison P2-M4-02, conservé |
| --- | --- |
| P2-M4-01 | Fermé après revue indépendante ; matrice d'annulation conservée dans la comparaison de ce lot. |
| P2-M4-02 | Fermé : reproduit après gel réel, correctif local, ciblés et comparaison 1 447/1 447 verts ; contre-audit indépendant favorable. |
| P3-M4-03 | Ouvert sur les comptes historiques 1 198/1 414 et les 21 noms de méthode doublés dans `new_sql_test_ids` de l'artefact P2-M4-01. Aucun ancien artefact réparé ici. |

Ce tableau est historique ; la [rectification P3 ultérieure](#erratum-documentaire-p3-m4-03--6-octobre-2026)
préserve ses résultats et corrige les métadonnées réutilisables.

L'[artefact P2-M4-02](../../states/baselines/document-workshop/frida-v1-document-workshop-p2-m4-02-20261006.json)
porte les listes exactes, identifiants chargeables, commandes, résultats/exits/durées,
traces sans contenu, différences de sélection, sous-ensembles et erreurs de harnais.
Le [contrat M4](../../states/specs/frida-v1-document-workshop-m4-contract.md)
fixe l'attribution stable sans modifier admission, estimation ou schéma du manifeste.

Baseline avant édition : **1 436/1 436**, exits 0, zéro skip :
739 Python (231,955 s), 142 SQL (104,923 s), 2 pgvector (2,800 s),
424 Node (7,166231765 s), 107 Chromium historiques (106,177801850 s),
22 Chromium M4 (26,221945543 s). Sélecteurs finaux publiés P2-M4-01 revalidés
par modules/fichiers ; les 21 identifiants hérités mal formés n'ont pas été utilisés.
Ces anomalies restaient P3-M4-03 à la livraison P2-M4-02, sans réécriture des relevés historiques.

Rouge causal avant patch : 2 cas, 1 échec (1,646 s, exit 1), contrôle sans source
vert ; contrôle seul 1/1 (1,064 s, exit 0). Flask/stores SQL/M2/admission/manifeste
réels, transport de preuve recevant le corps figé. La source complète est envoyée
mais classée `time_reference`, origine `core.conversations_prompt_window`, stage
`prompt_window`, kind `system_context`, avec lane input_count 1. Son index observé
appartient à la fixture, pas au produit. Les assertions ajoutées au test SQL
existant reproduisent séparément rouge 2 cas/1 échec (1,577 s, exit 1), puis vert
2/2 (1,631 s, exit 0), sans retirer contenu intégral, non-contamination et garde.

Le seul delta produit remplace la clé d'identité Python par la position calculée
immédiatement avant l'append du message source. Capsule/enveloppe/adaptateur
`response_format` ajoutent en fin ; le builder actuel et les clones JSON gardent
l'ordre. Le resolver existant accepte cette clé. Un message regroupe toutes les
sources sélectionnées et porte les quatre champs documentaires explicites ;
aucune sélection laisse le mapping vide. Aucune attribution par texte/égalité/
regex/empreinte, métadonnée fournisseur, marqueur, mesure ou budget ajouté.

Matrice ciblée SQL **9/9, 6,414 s, exit 0** : nominal avec octets reçus en loopback
égaux aux octets admis, trois sources regroupées, historique de longueurs différentes,
capsule active/inactive, copies JSON, voisin de texte identique et canaris trompeurs,
caller modifié après gel sans altération du corps, compteur mutateur refusé avant
transport, `response_format` et absence de source. Un seul appel documentaire,
zéro fallback normal. Ciblé admission/manifeste **36/36, 6,678 s** ; voisins
chat/capsule **37/37, 0,039 s**, exits 0, zéro skip. Ces sous-sélections ne
s'ajoutent pas au total de comparaison ; les deux modules capsule supplémentaires
sont un ciblé distinct de la sélection publiée, pas une extension cachée de sa baseline.

Les adaptations ne changent aucune assertion produit : nom/signature des helpers
réels, capture des paramètres contenant des modules sans deepcopy, config capsule
résolue au bootstrap plutôt qu'environnement tardif, dates synthétiques et contrôle
des suffixes/rôles après le label temporel existant. Le premier ciblé unitaire
chargeait dix tests importés en doublon ; import du module et composition corrigent
ce seul harnais. Tous les passages intermédiaires sont consignés avec leurs exits.

Sous builder synthétique `response_format`, la liste du manifeste conserve aussi
la ligne d'estimation, distincte de `body.messages`. Cette limite préexistante est
consignée séparément : elle n'est jamais une source documentaire, et sa refonte
n'est pas absorbée par ce correctif. Le builder runtime actuel ne produit pas ce champ.

Comparaison finale **1 447/1 447**, exits 0, zéro skip :

| Sélection | Cas | Durée du runner |
| --- | ---: | ---: |
| Python | 741 | 235,422 s |
| PostgreSQL | 151 | 111,133 s |
| pgvector | 2 | 3,034 s |
| Node | 424 | 7,150256656 s |
| Chromium historiques | 107 | 107,597451612 s |
| Chromium M4 | 22 | 26,206865055 s |

Tous les cas baseline sont conservés. Le delta ajoute exactement deux tests
unitaires et neuf SQL dans deux nouveaux modules ; aucune extension des autres
fichiers de comparaison. Les onze identifiants nouveaux se chargent chacun
comme un seul test, sans nom de méthode doublé. Les ciblés et contrôles ne
s'ajoutent pas à 1 447 : le ciblé chat/capsule de 37 cas contient 26 cas en
recouvrement et 11 cas existants hors comparaison, développés séparément.

Traces finales de la chaîne réelle : index source 4 ou 20 selon l'historique,
quatre champs de provenance exacts, source entière et compte cohérent. Le nominal
HTTP relie les octets admis aux octets effectivement reçus ; `response_format`
distingue les 7 messages transmis des 8 estimés sans attribuer la source à
l'auxiliaire. Une mesure partagée par admission ; zéro nouveau log produit.

Revue indépendante finale favorable à la fermeture de **P2-M4-02 seulement**,
sans nouveau finding confirmé : delta, logs bruts, traces et documentation
concordent. Les garanties P2-M4-01 restent vertes. Nettoyage vérifié : deux
PostgreSQL dédiés, deux répertoires de sockets et l'unique arbre temporaire de ce
lot supprimés ; inventaires sous leur préfixe vides, aucune ressource voisine modifiée.
À cette livraison P2-M4-02, P3-M4-03 restait ouvert. M4 reste non intégralement
fermé et M5 non commencé. Aucun appel
OpenRouter/DAV live, migration opérateur, confirmation, écriture ou déploiement.

#### Erratum documentaire P3-M4-03 — 6 octobre 2026

Lot documentaire uniquement, base `674150d913e3402819a1c307876427d59d6791e4`,
parent `722132631c2a70851c95d732420d64926895cba9`, même branche M4 ;
HEAD/upstream/distant alignés, worktree propre et divergence 0/0 avant édition.
M0–M3 et main inchangés. Aucun code, test produit, configuration ou migration
modifié ; commit/push M4 autorisés, aucun déploiement ni démarrage M5.

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de bord ? »
Plan minimal retenu : un [artefact autoritatif P3](../../states/baselines/document-workshop/frida-v1-document-workshop-p3-m4-03-20261006.json),
renvois depuis les trois anciens artefacts, correction de la seule liste
réutilisable `new_sql_test_ids`, synchronisation de cette roadmap, du contrat M4
et du hub. Les anciens champs de résultats, durées et digests de logs restent
inchangés ; les statuts des anciens tableaux sont explicitement datés.

**Comptes.** Sur une archive Git temporaire isolée du commit initial
`2cbeb7fa59be5751502079a1eb6857c2f9977ef2`, les deux sélections publiées
litigieuses ont été exécutées, et pas seulement collectées :

| Nouveau rejeu P3 sur le commit initial | Fichiers | Cas exécutés verts | Durée TAP | Exit / skips |
| --- | ---: | ---: | ---: | --- |
| `app/tests/unit/frontend_chat/test_*.js`, liste développée | 34 | 424/424 | 1,217185992 s | 0 / 0 |
| Neuf fichiers Chromium historiques publiés, en série | 9 | 107/107 | 94,262826388 s | 0 / 0 |

L'artefact développe les fichiers, commandes et empreintes des sources et des
nouveaux TAP. Une collecte distincte des registrations, sans appeler les
callbacks, concorde avec les noms/comptes exécutés. Le fichier Chromium M4 est
seulement collecté à 21 cas dans P3, jamais présenté comme un nouveau vert.
Les trois ensembles de fichiers frontend sont disjoints ; les sélecteurs
Python/SQL/pgvector initiaux sont également uniques et disjoints par module.
Les 11 noms Node répétés ne sont pas des identifiants ; l'identité de collecte
associe fichier, rang de registration et nom, sans supprimer de cas exécuté.

| Relevé historique du 6 octobre, version testée | Compte et statut |
| --- | --- |
| M4 initial `2cbeb7fa…` | 1 198 annoncés = 739 Python + 121 SQL + 2 pgvector + 211 Node + 104 Chromium historiques + 21 M4 ; sélection exacte du run annoncé inconnue. |
| Sélection publiée sur ce même commit, baseline P2-M4-01 | 1 414 exécutés historiquement = 739 + 121 + 2 + 424 + 107 + 21, exits 0, zéro skip. P3 ne rejoue que les deux lignes frontend ci-dessus. |
| P2-M4-01 `72213263…` | 1 436 exécutés, delta +21 SQL/+1 navigateur, contre-audit indépendant favorable. |
| P2-M4-02 `674150d9…` | 1 447 exécutés, delta +2 unitaires/+9 SQL, contre-audit indépendant favorable. |

Source précise des sous-comptes initiaux non rejoués ici :
[`P2-M4-01.baseline`](../../states/baselines/document-workshop/frida-v1-document-workshop-p2-m4-01-20261006.json),
datée du 6 octobre, base `2cbeb7fa…` : Python 739/739 (235,979 s), SQL
121/121 (56,311 s), pgvector 2/2 (1,536 s), Chromium M4 21/21
(16,756157819 s), exits 0, zéro skip. Leurs pointeurs, sélecteurs et blobs
originaux sont développés dans l'erratum. Ce sont des résultats historiques,
pas un nouveau run intégral ou des durées du rejeu P3.

La non-concordance sélection/comptes est prouvée ; elle ne prouve pas qu'un run
de 1 198 n'a jamais existé. Sa sélection exacte n'est pas récupérable dans
l'artefact conservé ni l'historique documentaire pertinent inspecté. La
déclaration reste accessible mais son statut de référence reproductible est
retiré. Aucun log manquant, durée ou succès n'est inventé. Un digest seul ne
prouve pas un run. Les ciblés qui se recouvrent ne s'additionnent pas ; les
11 cas capsule hors comparaison et les trois probes indépendantes signalées
par le mandat restent séparés. Ce mandat ne fournit pas leurs IDs/logs/résultats ;
P3 ne leur attribue aucun nouveau succès ni compte additionnel.

**Identifiants.** La collecte réelle du module d'annulation au HEAD `674150d9…`
fournit 21 cas. Chaque ID corrigé résout exactement un test, sans erreur,
en conservant son nom de méthode ; liste égale aux 21 attendus, sans doublon,
et aux listes historiques vertes du ciblé P2-M4-01 et de P2-M4-02.
Les 21 valeurs originales reproduisent 21 erreurs de chargement. Original
retrouvable au blob `a428bcfdf56493b8980b0ac86a12dcb55ce12314`, dans
`674150d9:app/docs/states/baselines/document-workshop/frida-v1-document-workshop-p2-m4-01-20261006.json`.
Le module n'a pas changé depuis `72213263…`, SHA inchangé. Le contrôle des
IDs ne lance ni `setUp` ni SQL ; le vert 21/21 en 21,195 s est conservé comme
résultat historique de `targeted_sql.runs[4]`, sans nouveau run DB.
L'empreinte historique SQL de 142 IDs encode les méthodes doublées : elle est
conservée avec cette qualification. L'erratum valide cet encodage, l'égalité
avec les 142 IDs corrects de la baseline P2-M4-02 et leurs empreintes nouvelles
explicitement encodées, sans remplacer aucun digest de log.

Images/runners préexistants et figés, `--pull=never`, réseau extérieur fermé,
env vidé, sources/rootfs/dépendances read-only, `/tmp` tmpfs, bytecode désactivé ;
aucune DB opérateur ni socket DB montée. Adaptation d'archive : seul point de
montage vide `node_modules`, dépendances/cache navigateur existants read-only.
Le premier collecteur Python lancé comme fichier scratch n'avait pas le cwd
applicatif sur `sys.path` ; `python -c/runpy` le rétablit comme `python -m unittest`,
sans changer les sources. Une assertion de noms frontend uniques a été corrigée
dans le résumé de collecte, en conservant les 424 registrations et leurs noms.
Les programmes, exits et observations intermédiaires sont dans l'artefact.

Contre-audit documentaire indépendant favorable : sources, TAP, IDs, empreintes,
liens, chronologie et périmètre vérifiés. Une précision sur l'encodage des trois
digests de registrations a été ajoutée puis revalidée ; aucun finding vivant.
L'unique arbre temporaire P3, ses archives/programmes et les deux nouveaux TAP
ont été retirés ; inventaires du préfixe temporaire et des conteneurs P3 vides.
Aucune DB de preuve ni socket DB créée dans ce lot.

État à la clôture documentaire P3-M4-03, avant le mandat M5 : **P2-M4-01 et P2-M4-02 fermés après contre-audits indépendants ;
P3-M4-03 corrigé documentairement ; livraison runtime ouverte ; confirmation
et écriture inactives ; M5 non commencé**. La limite `response_format` sous
builder synthétique reste inchangée, le builder courant n'émettant pas ce champ.
Migrations opérateur, déploiement/health, OpenRouter/DAV live et Safari matériel
restent des obligations distinctes. Ce lot ne vaut pas autorisation de M5.

### M5 — Confirmation et exécution hermétiquement protégées

**Statut au 6 octobre 2026 :** code et preuves hermétiques fermés.
Le [contrat M5](../../states/specs/frida-v1-document-workshop-m5-contract.md)
porte les propriétaires, la matrice de panne, l'autorité durable et les limites.
La confirmation reste indisponible dans le parcours public ; seul le harnais
injecte l'exécuteur et le transport synthétique à cette date. Le raccord M6 du
7 octobre est décrit dans la section suivante, sans livraison runtime.

**Objectif :** démontrer les protections d'exécution avant raccord réel d'écriture.
**Dépendances :** M4.
**Fichiers :** executor, paths, clients DAV bornés, journal et confirmation.
**Interface :** claim confirmé et résultat typé ; services réels avec clients simulés.
**Propriétaire :** Celebrimbor.

- [x] Rouge causal : double confirmation → un PUT ; collision/chemin hostile → zéro
  mutation ; publication locale échouée → compensation conditionnelle.
- [x] Tests compensation/ETag/upload/dossiers voisins ; headers réellement envoyés,
  collections existantes, ETag absent/changé et résultat réseau inconnu.
- [x] Revérifier fraîcheur, ETag, scope et claim au clic, même sur un pending ancien ;
  refuser uniquement les invalidations/préconditions décidées, pas un âge limite.
- [x] Faux verts : tester seulement le validator, omettre les headers ou toujours
  simuler succès distant/rollback réussi.
- [x] Interdire DELETE sans propriété, rollback récursif, retry PUT incertain et
  écriture hors Documents.
- [x] Réserver la frontière binaire : renderer fake après confirmation/claim,
  validation complète avant MKCOL/PUT ; panne/21e page/cleanup douteux → zéro mutation.
- [x] Synchroniser matrice de panne/compensation ; aucun canari.
- [x] Raccord client d'écriture réel interdit avant fermeture.
- [x] Fermer toutes les frontières de panne et le retrait synchrone du bouton.

**Preuves exécutées le 6 octobre 2026 :**
[relevé M5](../../states/baselines/document-workshop/frida-v1-document-workshop-m5-20261006.json).
Baseline avant patch : 1 447/1 447 selon `final.selections` P2-M4-02 ;
comparaison finale V2 : mêmes 1 447 + 76 nouveaux = **1 523/1 523**,
exits 0, zéro skip, mêmes IDs historiques, collecte nouvelle concordante et
128 empreintes stables. Nouveautés : 31 Python (3 route, 28 DAV loopback),
28 PostgreSQL réels et 17 Chromium montés à fetch simulé. Les 74 voisins
DAV/upload/dossiers recoupent la baseline ; les 70 voisins Exports/Images/Notes
hors comparaison sont verts et séparés des totaux. Les 953 IDs Python chargent
un cas chacun ; les 570 registrations frontend sont distinctes par fichier/rang/nom.
La première comparaison verte, antérieure à la correction des 3xx, reste intermédiaire.

Confirmation liée une fois à l'action, claim M3 distinct, journal avant effets,
PUT `If-None-Match: *`, publication minimale atomique et DELETE conditionnel
seulement avec preuve de création/ETag fort d'origine. Pannes, perte de lease,
commit incertain et absence de preuve ne réarment jamais l'action. Les findings
introduits d'autorité, compensation/classification distante et UI sont corrigés
avec rouges causaux et contre-lecture indépendante, détaillés dans le contrat.
La migration M5 est versionnée et testée deux fois depuis M4 avec actions
existantes, **non appliquée à l'opérateur**. Aucun client mutateur par défaut :
POST public 503 avant mutation. Cette fermeture n'autorise pas le raccord réel
réservé à M6 ; aucune preuve de rendu, de DAV live ou de déploiement.

### M6 — Markdown create/copy, reçu et continuité

**Objectif :** premier parcours complet de création confirmée.
**Dépendances :** M5.
**Fichiers :** raccord Nextcloud, publication fichier/lien/révision/reçu, UI et lane.
**Interface :** action exécutée, lien produit, inventaire commun et reçu suivant.
**Propriétaire :** Celebrimbor.

- [x] Rouge causal : succès distant/échec local → aucun faux succès ; autre conversation
  → inventaire sans contenu ; confirmation répétée → aucune seconde mutation.
- [x] Tests HTTP complet, inventaire/réhydratation/manifeste/projections voisins.
- [x] Faux verts : tester l'executor seul, confondre ID conversation de départ et
  thread courant, vérifier présence du reçu sans vérifier sa lane.
- [x] Interdire copie implicite, renommage après clic, reçu assistant/tool.
- [x] Synchroniser atelier/Documents/dossiers/observabilité.
- [ ] Premier canari synthétique après fermeture hermétique et GO distinct seulement.
- [ ] Rebuild requis ; fermer concordance lien/inventaire/reçu/tour suivant.

Code et preuves isolées : [contrat M6](../../states/specs/frida-v1-document-workshop-m6-contract.md),
[relevé daté](../../states/baselines/document-workshop/frida-v1-document-workshop-m6-20261007.json).
Baseline M5 exacte rejouée avant patch et comparée après patch ; nouveautés et
70 voisins supplémentaires séparés. Contre-lecture indépendante effectuée,
findings M6 corrigés et revalidés avant livraison Git. Aucune nouvelle migration
M6 ; prérequis M1–M5 et recette future
détaillés dans le contrat. Les deux portes live ci-dessus restent ouvertes.

Correctif **P3-M6-AUD-01/02**, 7 octobre 2026, sur la même branche M6 :
[preuves séparées](../../states/baselines/document-workshop/frida-v1-document-workshop-p3-m6-aud-20261007.json).
Les harnais SQL/NOWAIT et Chromium/concurrence étaient déjà identiques sur M5.
Sonde de transactions ciblée au thread de requête et réponses navigateur bloquées
explicitement remplacent leurs hypothèses temporelles, avec contrôles négatifs,
supervision réelle et assertions produit conservées. Tests/preuves/docs seulement.
Le run élargi de 87 cas a révélé **P3-M6-AUD-03**, course indépendante du harnais
d'annulation inchangé (contrôle déjà entré avant pause), reproduite avec les deux
helpers et laissée ouverte hors mandat. Aucun finding produit établi ; le premier
échec spontané n'est pas réattribué au détenteur imposé par le diagnostic causal.
Comparaison finale : **1 552 historiques conservés + 3 contrôles négatifs = 1 555
distincts**, exits 0, zéro skip/annulation ; **70 voisins séparés**. Les cinq
parcours HTTP natifs et les dix à fetch simulé M6 sont conservés. Le passage final
au vert ne ferme pas P3-M6-AUD-03 ; son échec intermédiaire reste dans le relevé.
À cette livraison historique M6, le runtime restait ouvert et M7 non commencé.

Correctif dédié **P3-M6-AUD-03**, 7 octobre 2026, depuis `47a85218` :
[relevé séparé](../../states/baselines/document-workshop/frida-v1-document-workshop-p3-m6-aud-03-20261007.json).
Le finding laissé ouvert ci-dessus est corrigé dans la seule fixture : admission
fermée et drainage des vrais appels/transactions avant le verrou externe, puis
reprise réelle après libération. La preuve observe un watchdog déjà entré, son
retour et sa transaction fermée, son prochain contrôle différé et son store repris.
Un négatif retire uniquement le drainage : la même sonde rejette avant l'effet SQL.
Les trois scénarios et leurs 17 assertions sont conservés ; P3-01/02 restent
inchangés et rejoués. Aucun code produit ou prérequis runtime modifié.
Le diagnostic rouge avant patch, le rendez-vous intermédiaire 4/5 et la correction
du nettoyage détectée en contre-lecture restent consignés ; aucun rouge historique
86/87 n'est réécrit, son ordonnancement spontané reste inconnu.
Comparaison exacte : **1 555 historiques + 2 nouveaux = 1 557 distincts**, exits 0,
zéro skip/annulation ; **70 voisins séparés**. Les cinq parcours HTTP natifs et dix
à fetch simulé restent distincts ; ciblés/diagnostics ne sont pas recomptés.
À cette livraison historique P3-M6-AUD-03, runtime et canari restaient ouverts ; **M7 non commencé**.

### M7 — Update Markdown, ID stable et conflit

**Objectif :** modifier la cible explicite sans écrasement concurrent.
**Dépendances :** M6.
**Fichiers :** content service frais, executor update, liens/révisions.
**Interface :** If-Match de version préparée et même workspace_file_id.
**Propriétaire :** Celebrimbor ; Sauron conditionnel pour preuve Versions.

- [x] Rouge causal : changement avant clic → conflit et zéro PUT ; succès → même nom/chemin/ID local et distant.
- [x] Voisins Notes ETag/sélections, create/copy/compensations M5, annulation/provenance M4 et inventaires M2 préservés ; 412 après prélecture, rollback PostgreSQL réel et réconciliation SQL sous nouveau claim sans seconde écriture.
- [x] Requête DAV de production observée avec ETag préparé exact ; négatifs retirant/remplaçant le header final détectent l'écrasement concurrent réel du peer synthétique.
- [x] Aucune restauration automatique, fusion, renommage, copie de secours, DELETE ou compensation d'update ; Nextcloud Versions reste l'autorité de récupération.
- [x] Identité stable, historiques/révisions et réparation ciblée sans PUT fermés sur code/preuves isolées après contre-lecture indépendante.
- [ ] Migration opérateur et rebuild du seul service applicatif sous GO distinct ; contrôles déployés et canari update/Versions restent ouverts.

[Contrat M7](../../states/specs/frida-v1-document-workshop-m7-contract.md) et
[relevé daté M7](../../states/baselines/document-workshop/frida-v1-document-workshop-m7-20261007.json).
Depuis M6 exact `b00eb95001755295dcc301232272a8070d26cd78`, branche nouvelle
`FridaV1-Document-Workshop-M7`, sans merge/rebase. **1 557 identités de référence
rejouées avant édition puis conservées + 47 nouveaux cas = 1 604 distincts verts**,
exits 0, zéro skip/annulation ; **70 voisins distincts supplémentaires séparés**.
Les 47 nouveaux sont 29 SQL/Flask/DAV, cinq tests HTTP du client de production et
13 parcours navigateur monté → vrai Flask HTTP → PostgreSQL isolé → client DAV
de production → serveur DAV HTTP synthétique à versions/préconditions effectives.
Les cinq parcours HTTP natifs et dix à transport simulé M6 restent distingués.
Les deux assertions historiques interdisant update au parseur évoluent avec le
contrat M7 sous les mêmes IDs ; autorité cible et refus voisins restent prouvés.
Les rouges, pannes de harnais et résultats intermédiaires restent qualifiés dans
le relevé, y compris la fenêtre succès SQL/GET inventaire, fermée par une preuve
Event de reprojection sans sélection implicite. Ciblés inclus non recomptés.
Migration M7 explicite après M1–M5, éprouvée sur PostgreSQL isolé seulement ;
aucune DB opérateur, livraison runtime, canari Nextcloud/Versions ou OpenRouter
réel. Lors de cette fermeture M7, M8-C et lots suivants n’étaient pas commencés ;
le statut courant M8-C est consigné ci-dessous, après le diagnostic M7.

#### OBS-M7-CONC-01 — Diagnostic causal, 9 octobre 2026

[Rapport borné](../../states/audits/frida-v1-document-workshop-obs-m7-conc-01-20261009.md),
[relevé](../../states/baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-20261009.json)
et traces synthétiques corrélées : un verrou réel détenu par le perdant DAV 412
refuse l'observation, la fermeture d'action et celle du claim du gagnant 204.
Après arrêt des superviseurs, claim encore vivant et GET `executing/confirmed`
sans reçu ; après expiration artificielle de lease dans la DB jetable, un GET
converge vers `remote_uncertain`, sans second PUT. Contrôle sans chevauchement :
un reçu publié. Deux PUT/un seul effet, fichier/lien uniques, zéro compensation
et répétitions sans DAV ni nouvel état SQL dans les deux scénarios.

L'attente de terminalité immédiate du test est trop forte pour cette branche
permise par le contrat M7. Cause suffisante éprouvée ; ordonnancement exact des
rouges initiaux inconnu, aucun défaut produit démontré. Diagnostic livré sans
correctif produit, migration, test historique ou fixture commune dans le commit
diagnostique `970ccb37`. Le correctif de preuves autorisé ensuite est consigné
ci-dessous ; il conserve cette branche contractuelle sans changer le produit.

Provenances conservées : contre-audit indépendant du 7 octobre sur `1732a126`,
SQL 28/29 deux fois, total 1 674/1 677 ; celui du 9 octobre sur `c1654c25`,
SQL 28/29, total 1 689/1 690 et cinq clients verts séparément après SQL.
96 voisins verts séparés dans chacun de ces contre-audits. Le 9 octobre,
Celebrimbor AUD-02 : combiné 34/34 et total 1 690/1 690, distincts de ces rouges.
Dans ce diagnostic seulement : SQL 29/29, ciblé 1/1, combiné 34/34, séquencés ;
deux scénarios finaux autonomes verts, assertion historique rouge capturée dans
le chevauchement. Aucun cumul de répétitions ni comparaison intégrale relancée.
Les bases/sockets de Codex étaient isolés et les groupes SQL séquencés : aucun
rattachement aux chevauchements de fixtures du relevé AUD-02. OBS-M7-UI-01 et
M4 restent séparés, de causes initiales inconnues. AUD-01 et AUD-02 sont fermés
après contre-audits indépendants selon le mandat de Tof ; aucun runtime
ou lot suivant ne démarre lors de ce diagnostic. Arrêt historique après
Git pour contre-audit Codex.

#### OBS-M7-CONC-01 — Correctif des preuves de concurrence, 9 octobre 2026

Mandat distinct tests/helpers/preuves/docs, base `970ccb37750af1aa7f53486afcef00774d269c84`,
parent `c1654c25`. Produit, configuration, migrations et frontend identiques.
[Rapport du correctif](../../states/audits/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.md) et
[relevé exact](../../states/baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.json),
avec inventaires avant/après, commandes, exits, durées et traces JSONL.

L'ID historique est conservé pour le nominal : deux PUT réellement en vol avec
`If-Match: "v1"`, puis fin de requête du perdant avant observation du gagnant.
Un reçu vérifié pour le gagnant, conflit sans reçu pour le perdant. Un nouvel ID
éprouve séparément les trois refus NOWAIT, le claim vivant après jonction des
superviseurs, le premier GET sans mutation SQL, puis l'expiration artificielle
du seul claim identifié dans la DB jetable et le GET `remote_uncertain`/`lost`.
Aucune attente de terminalité avant expiration ; `executing` reste transitoire.
Dans les deux cas : fichier/lien uniques, deux PUT/un effet, zéro compensation,
aucun nouveau claim ni DAV/journal/état modifié lors des répétitions. Tous les
champs durables sont comparés ; `lease_live` est vérifié séparément.

L'ancienne assertion est rouge causalement dans le chevauchement ; le contrôle
nominal est vert. Les scénarios corrigés et le négatif de convergence sont
éprouvés sur SQL/Flask réels ; les injections restent en mémoire. Le nettoyage
est éprouvé sur échec du harnais après deux PUT et sur erreur d'observation de
supervision, sans masquer l'erreur initiale ni interrompre les autres joins.
Baseline 1 690/1 690 ; comparaison finale : **1 690 IDs historiques conservés +
1 nouveau = 1 691/1 691**, zéro skip. 70 + 26 voisins verts séparés ; groupe M7
35/35 et ciblés 2/2 distincts, non ajoutés au total. M6 HTTP natif 5/5, M7 natif
13/13, M6 à transport simulé 10/10, avant et après. Aucun échec fonctionnel
intermédiaire inattendu ; rouge causal et incidents de commande conservés.

Preuves transmises par Tof, distinctes de ces exécutions : contre-audit Codex du
diagnostic, sélection 34/34 et deux scénarios verts. Variante d'expiration
naturelle en mémoire : 92,681 s, dont environ 89,054 s résiduelles, échéance
inchangée et GET convergent sans replay. Un premier essai auxiliaire de 92,902 s
a échoué après le GET conforme sur l'égalité autour du replay ; différence non
capturée, cause inconnue. Le second ajoutait une capture d'erreur sans changer
les assertions. La séparation des projections temporelles dans ce correctif
ne permet pas d'attribuer une cause à ce premier essai.

Ce lot corrige l'attente et la reproductibilité de la preuve ; il n'identifie
pas rétrospectivement chaque rouge historique et ne démontre aucun bug produit.
Les comptes indépendants 1 674/1 677 et 1 689/1 690 restent conservés ci-dessus.
AUD-01/AUD-02 fermés ; UI M7/M4, runtime et clôture globale M8-C restent séparés.
Livraison à contre-auditer par Codex ; aucun démarrage M8-S/M8-A ni lot suivant.

#### OBS-M7-UI-01 — Diagnostic borné du menu téléphone, 9 octobre 2026

[Rapport et suite proposée](../../states/audits/frida-v1-document-workshop-obs-m7-ui-01-20261009.md),
[relevé reproductible](../../states/baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-20261009.json).
Base `360521bd`, même branche M8-C. **Défaut d'attente du harnais démontré sur la
base du diagnostic** : sélection native fermant le menu après `loadThread`, puis
clic redondant du helper pendant/après cette fermeture. Baseline intacte
13/13 en 265,955 s ; sonde riche quatre variantes 3/4, rouge phone dark avant
reload. Témoin GET réel retenu puis continué : 2/2, parcours/assertions complets.
Ordre après fin réelle de transition : deux timeouts au clic natif 10 000 ms,
reproduits avec observateur réduit. Retrait de classe seul : gestes armés
réussis, rouge ultérieur non armé après reload conservé. Tentative de filtre
transition ciblé : deux rouges avant armement, contrôle non atteint et rejeté
comme preuve causale. Aucun cumul de ces ciblés avec les treize cas natifs.

Produit, CSS, tests/helpers historiques et fixtures communs inchangés ;
1 041 empreintes historiques comparées. Diagnostic/probes/preuves/docs seulement,
sans nouvelle confirmation ou mutation DAV par instrumentation, sans runtime.
L'ordre exact des deux rouges du 7 octobre reste inconnu ; aucun lien causal
renderer/SQL établi. **Correctif du harnais alors encore ouvert**, proposé pour un
mandat distinct, sans l'appliquer dans ce diagnostic. Les branches après le point d'échec ne
sont pas validées par les rouges. M4 reste ouvert séparément. AUD-01/AUD-02 et
OBS-M7-CONC-01 restent validés ; clôture globale M8-C hors mandat, aucun M8-S/M8-A
ou lot suivant. Nettoyage et contre-lecture dans le relevé, arrêt après Git
pour contre-audit Codex.

#### OBS-M7-UI-01 — Correctif du harnais de navigation, 9 octobre 2026

[Rapport du correctif](../../states/audits/frida-v1-document-workshop-obs-m7-ui-01-fix-20261009.md),
[relevé et commandes](../../states/baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-fix-20261009.json).
Base exacte `be9e3a8a0bdbc246659ccde4f286a2a91e2cbab3`, même branche M8-C.
**Défaut d'attente corrigé ; produit inchangé.** `choose` retire son clic
redondant et attend la sélection exacte puis la fermeture native complète sous
l'autorité téléphone existante : classes, ARIA, backdrop, transition transform
et géométrie. Fermeture déjà achevée reconnue ; vrai GET retenu démontrant que
l'attente ne se termine pas pendant `loadThread`. Bureau clair/sombre préservé,
helper partagé et geste explicite de fermeture toujours exercés.

Baseline avant édition 13/13 ; premier ciblé rouge conservé : dark causal
atteint, light avant armement et non causal. Six positifs complets (quatre
variantes `completed`, dont deux téléphones déjà fermés, et deux téléphones
en cours de sélection) ; négatifs attente supprimée
2/2 rouges attendus et ancien clic 2/2 timeouts attendus, barrières exigées.
Archive isolée sur la base : deux incidents de montage conservés, puis deux
rouges causaux atteints avec les anciens programmes inchangés. Les branches
après un rouge restent non validées par ce rouge. Assertions métier conservées.

M7 natif **13/13**, M6 HTTP natif **5/5**, M6 simulé **10/10**, groupes séparés.
Comparaison finale **1 691 identités historiques exactes / 1 691**, aucun nouvel
ID normal ; six positifs et quatre mutants de preuve hors de ce total.
**70 + 26 voisins distincts** sans double compte. 1 043 sources historiques app
hors docs : 1 042 inchangées, seul le test M7 modifié avec autorisation. Produit,
CSS, handlers et fixtures communs inchangés. Traces, incidents, inventaires,
nettoyage et portée de contre-lecture dans le relevé.

Seul le défaut d'attente est corrigé, validé par le contre-audit indépendant transmis par Tof.
L'ordre exact des incidents du 7 octobre reste inconnu ; aucun défaut produit
ni lien renderer/SQL établi. AUD-01/AUD-02 et OBS-M7-CONC-01 restent fermés ;
M4, clôture globale M8-C, runtime et Writer restent séparés. Aucun M8-S/M8-A,
restart/rebuild/déploiement ou lot suivant ; arrêt après livraison Git.

#### P3-M7-UI-FIX-01 — Racines du lanceur, 10 octobre 2026

**Fermé sur ce seul P3.** [Rapport et erratum](../../states/audits/frida-v1-document-workshop-p3-m7-ui-fix-01-20261010.md),
[relevé durable dédié](../../states/baselines/document-workshop/frida-v1-document-workshop-p3-m7-ui-fix-01-20261010.json).
Base exacte `2fd60c48a5a01669425fded6a648304fdede45e0`, même branche M8-C.
Premier rouge avant édition conservé : ancien exemple avec suffixe neuf,
exit 1 en 0,046 s, deux copies et aucun browser record ; échec de lancement,
pas rouge causal. Contrat unique `/tmp/fridadev-obs-m7-ui-01-fix-…` avant tout
effet et dans la copie interne, namespace/collisions/nettoyage inchangés.
Runner et artefacts diagnostiques, attente M7, sondes et assertions intacts.

36 rejets instrumentés, six refus réels sans répertoire/copie/ressource ;
`completed` 4/4, `pending` 2/2, `no-wait` deux rejets causaux, `old-click` deux
timeouts causaux ; archive exacte readonly avec deux barrières atteintes.
M7 natif 13/13 ; `neighbors` : 13/5/10 séparés. Les six modes sont exécutés et
inspectés. Une seule comparaison complète du 10 octobre : **1 691/1 691**
identités exactes, **70 + 26** voisins distincts ; mode `compare-neighbors`
éprouvé séparément sans ajout au total. Nouveaux résultats Celebrimbor, distincts
du 9 octobre et de la portée du contrôle Codex transmis. Erratum daté des
commandes, preuves, relecture indépendante et nettoyage dans le relevé P3.

OBS-M7-UI-01 fonctionnel reste validé ; AUD-01/AUD-02 et concurrence M7 restent
fermés. M4, runtime, Writer et clôture globale M8-C restent distincts ; aucune
installation, livraison runtime, M8-S/M8-A ou suite automatique. Commit/push
sur M8-C uniquement, puis arrêt pour contre-audit Codex de ce micro-lot.

Réserve distincte transmise par Tof le 10 octobre après le dernier contre-audit
Codex : archive M7 ancienne, une des deux barrières atteinte ; téléphone clair
arrêté pendant choose initial, sombre armé. Les deux barrières Celebrimbor restent
un record distinct. Préfixe du lanceur validé, P3 fermé ; aucun diagnostic ni
correctif d'archive dans le lot M4 ci-dessous.

#### M4-Chromium-intermediate-draft-failure — Diagnostic borné, 10 octobre

**Cause suffisante actuelle prouvée ; attribution historique exacte inconnue.**
[Rapport](../../states/audits/frida-v1-document-workshop-obs-m4-draft-image-20261010.md),
[relevé dédié](../../states/baselines/document-workshop/frida-v1-document-workshop-obs-m4-draft-image-20261010.json).
Base `d3e1f685af88777e363d075fc7f5207f9008c031`, même M8-C propre/synchronisée avant édition.
Lors du diagnostic, test/fixtures/produit inchangés. Baseline M4 22/22, ciblé exact image 1/1 (21
exclus, zéro ignoré), observation V1 verte ; aucun cumul de sélections recouvrantes.

Le vrai callback différé de focus image libéré entre la sélection du compositeur
et l'insertion réelle Playwright dirige les 16 caractères vers le prompt image,
sans vider un brouillon existant. Témoin callback avant fill : draft16/prompt0 ;
adverse et réduit sans hooks détaillés : draft0/prompt16, assertion exacte rouge
après barrières atteintes. Contexte réellement editing, garde incompatible
préservée ; zéro effet optimiste et zéro préparation/chat normal/image.

Mécanisme suffisant de synchronisation du harnais, aucun défaut produit ou runner
établi. Le premier 21/22 AUD-01 (20,774 s) reste conservé avec raw absent ; aucun
vert ultérieur ni ordre imposé ne donne son attribution exacte ou sa fréquence.
Le diagnostic proposait d'attendre le vrai focus image avant send dans ce seul
cas ; sa seconde lecture indépendante n'exécutait aucun test/Docker.
**Correctif minimal du harnais appliqué le 10 octobre**, base `500b442b` :
[relevé compact](../../states/baselines/document-workshop/frida-v1-document-workshop-m4-image-focus-fix-20261010.json).
Cinq lignes, send/autres modes/assertions/délais conservés ; callback déjà établi
et retenu verts, saisie bloquée jusqu'à sa libération indépendante. Copie privée
retirant uniquement l'attente : assertion originale rouge après barrières.
M4 22/22 une fois (19,498 s), fetch simulé ; incident de montage exit125 conservé.
Produit/fixtures/helpers et preuves historiques intacts, attribution historique
toujours inconnue. Aucun correctif produit ni comparaison générale.
AUD-01/AUD-02, concurrence M7, attente UI et P3 restent fermés dans leurs portées.
Aucune clôture globale M8-C, runtime, Writer ou suite M8-S/M8-A ; arrêt après
commit/push pour contre-audit Codex, sans correctif automatique.

### M8-C — Contrat Writer fermé et raccord simulé

**Objectif :** rendre le service isolé implémentable et le raccord testable sans moteur live.
**Dépendances :** M0–M7 ; exception inscrite, GO de lot distinct.
**Frontières :** document_renderer_contract.py, document_canonical.py,
document_rendering.py, execution/actions et tests de contrat ; aucun fichier plateforme.
**Interface :** render_request_v1 / render_result_v1, méthodes et bornes de section 9 ;
canonical/révision/profil figés, source temporaire optionnelle, résultat fermé sans cible DAV.
**Propriétaire :** Celebrimbor ; contrat remis à Sauron sans patch de sa racine.

- [x] Rouge causal : appel avant confirmation, canonical/hash discordants, profil inconnu,
  source/format inadmissible, pages absentes/21, partie manquante ou résultat brut → refus.
- [x] Livrer schémas versionnés, client fake, validate_result et garde zéro mutation ;
  conserver Markdown direct et refuser les formats binaires tant que M9/M10 sont inactifs.
- [x] Tests ciblés de contrat/action/executor, voisins M5–M7/Exports/readers ; assert
  ordre claim→render→validate→DAV et nombre d'appels, pas seulement statut HTTP.
- [x] Faux verts : fake toujours complet, hash déclaré sans recalcul, canonical muté
  pour correspondre au résultat, résultat PDF présenté comme compte DOCX.
- [x] Interdire provider/live renderer/Nextcloud, dépendance moteur dans FridaDev,
  socket Docker, shell libre, fallback ou modification Exports.
- [x] Synchroniser contrat commun/profil/bornes/erreurs avec cette roadmap ; aucun
  déploiement requis pour fermer le contrat hermétique, rebuild futur du code livré.
- [x] Fermer sur contrat consommable par M8-S et fake rejetant les contre-cas ;
  AUD-01 et AUD-02 fermés après contre-audits indépendants ; clôture documentaire du 10 octobre ;
  aucune installation ou preuve de disponibilité déclarée accomplie.

**M8-C fermé sur contrat, code et preuves isolées ; M8-S et correctif P2-M8S-AUD-01 livrés/qualifiés, clôture soumise au contre-audit Codex.**
La [note de clôture du contrat commun](../../states/specs/frida-v1-document-workshop-m8c-contract.md#clôture-documentaire--10-octobre-2026)
relie les critères aux preuves existantes et distingue le compte rendu Codex
transmis par Tof de toute nouvelle exécution. Réserve d'archive M7 maintenue :
une seule des deux barrières au dernier contre-audit, record Celebrimbor à deux
barrières séparé ; aucun défaut actuel démontré. Les attributions historiques
restent inconnues. Contrat remis à Sauron ; disponibilité du service, pins et confinement prouvés
par M8-S ci-dessous sous GO distinct. Contre-audit M8-S attendu ; aucun lot suivant démarré.

**Livraison initiale M8-C — 7 octobre 2026 (`fc911ed3`).** Résultats historiques
conservés ; la clôture totale est retirée après le contre-audit AUD-01/AUD-02. Base M7 exacte
`750180fa8595b53c7e188017c9c62be1ae9943fc`, branche
`FridaV1-Document-Workshop-M8-C`, créée avant édition. Voir le
[contrat commun remis à Sauron](../../states/specs/frida-v1-document-workshop-m8c-contract.md)
et le [relevé durable](../../states/baselines/document-workshop/frida-v1-document-workshop-m8c-20261007.json).
Six schémas fermés, multipart brut borné, hash canonical et identité complète
recalculés, sources Frida/externe distinguées, paire DOCX/PDF et assertions de
pages liées aux octets. Snapshots locaux puis DELETE/acquittement HTTP lié au
job/hash ; conflit préserve le job, submit incertain tente abandon sans retry.
Progression utile monotone N+7, 120 s d’inactivité exacte, aucun plafond mural.

La frontière synthétique BinaryRenderEvidence/_validated_binary M5 est remplacée,
son test et ses onze sous-cas conservés sous le nouveau contrat. Confirmation,
claim et fences prouvés sur PostgreSQL isolé ; faux verts hash/partie/armement
calibrés. Comparaison : 1 604 références M7 + 61 nouveaux = 1 665 distincts ;
70 voisins historiques et 26 Exports/readers séparés ; 32 vecteurs autonomes
(13 acceptés/19 refusés). Les findings introduits du contre-audit sont corrigés
et les preuves rouges/vertes conservées dans le relevé. Aucun format binaire
public disponible, aucun Writer, transport HTTP Unix, rendu/layout/glyphe réel,
service ou pin réel livré. M8-S/M8-A/M9-A/M9-B/M10/Z non commencés ; GO distincts
requis. Aucun rebuild/restart ; rebuild futur du code applicatif à effectuer
seulement lors d’une livraison runtime autorisée.

### P2-M8C-AUD-01 — Squelette de la partie principale DOCX

**Statut :** correctif borné sur la base `fc911ed3d42d253424becae399422dc992bc0b9c` ;
AUD-02, horloge/libération, restait ouvert dans ce lot historique.
Son correctif séparé du 9 octobre suit ci-dessous ; M8-C reste à contre-auditer.
Ces identifiants AUD sont distincts des findings internes de la livraison initiale.
Voir le [relevé dédié](../../states/baselines/document-workshop/frida-v1-document-workshop-p2-m8c-aud-01-20261007.json)
et le [contrat structurel/provenance SDK](../../states/specs/frida-v1-document-workshop-m8c-contract.md#squelette-docx--correctif-p2-m8c-aud-01).

L'inspecteur renderer ferme les QNames et le placement du squelette
`document → background? → body?`, cardinalité/ordre et blanc XML exact ;
background admet VML background facultatif. Body : enfants CT_Body admis,
sectPr direct facultatif/unique/terminal ; sectPr de paragraphe préservé.
Body optionnel selon le modèle SDK : absence de body n'est pas un refus de
structure. Aucun validateur XSD universel, preuve de fidélité ou rendu Writer.
La même garde s'applique aux sources DOCX Frida/externe ; M2/Exports inchangés.

Rouges avant patch : reproduction autonome, 4 sondes dont deux refus attendus
rouges ; 12 nouveaux cas, 27 assertions rouges, dont les deux variantes sous
confirmation/claim PostgreSQL. Verts ciblés : 74/74 et reproduction 4/4.
Instrumentations : result → refus réel → abandon lié au job/hash, aucun
bundle figé/libération positive ; refus avant la garde finale de format,
zéro DAV/journal/reçu de succès. Mutant temporaire dans le vrai sous-processus
neutralisant seulement la garde détecté ; XML tronqué toujours refusé.

Le relevé initial et ses 1 665 IDs restent historiques. Rejouage final :
**1 665 références exactes + 12 nouveaux = 1 677 distincts verts**, aucun skip ;
70 + 26 voisins séparés, cinq HTTP natifs M6, treize M7 et dix M6 à fetch simulé
préservés. Commandes/durées/exits et contre-lecture du delta sont consignés dans
le relevé dédié. Un échec intermédiaire Chromium M4 (21/22) est conservé :
sélecteur exact rejoué 22/22 sans patch, cause non établie. Les six sondes
Codex fournies (trois contrôles verts/trois refus attendus rouges, dont un
AUD-02) restent des preuves distinctes, jamais ajoutées à la sélection.
Lors de la livraison AUD-01 : aucune correction AUD-02, modification de transport/profil/budget/claim,
route/UI/capacité publique ou installation/rebuild/restart. DOCX/PDF publics
restent inactifs ; Markdown direct ; M8-S/M8-A/M9/M10 non commencés.

Seconde lecture indépendante code/tests/docs/relevé favorable à AUD-01 seul ;
vérification statique des artefacts, aucun test supplémentaire revendiqué.
Cette livraison AUD-01 s’arrêtait après Git pour contre-audit Codex, sans correction AUD-02.

### P2-M8C-AUD-02 — Inactivité au dernier acquittement de libération

Correctif borné du 9 octobre 2026, base AUD-01 `1732a126`, branche M8-C conservée.
[Relevé dédié](../../states/baselines/document-workshop/frida-v1-document-workshop-p2-m8c-aud-02-20261009.json)
et [contrat temporel](../../states/specs/frida-v1-document-workshop-m8c-contract.md#états-http-progression-et-espace-worker).
Un acquittement valide reçu à exactement 120 s sans progrès était accepté ;
le rouge autonome et le rouge sous confirmation/claim SQL le reproduisent.
La session contrôle désormais l'âge du dernier progrès utile après acquittement
validé et autorité, avant mémorisation de `ReleasedRender`. Aucun compteur
réarmé, deadline totale ou superviseur ajouté. `collected` reste un snapshot,
pas une preuve de succès ; un refus ne réexécute rien et ne relibère pas un job.

Les preuves ciblées couvrent 119,999/120/au-delà, âge consommé avant libération,
validation et contrôle d'autorité, cache/replay, erreurs et nettoyage unique.
Le contrôle négatif neutralise uniquement la nouvelle garde en mémoire de test.
Sous PostgreSQL réel, le refus temporel précède le contrôle de format public,
avec erreur applicative fermée et zéro DAV/journal de mutation/reçu de succès.

La déclaration AUD-01 de 1 677 verts est historique, pas la référence de santé
actuelle : contre-audit indépendant du 7 octobre transmis par Tof = **1 674 /
1 677**, plus 70 + 26 voisins verts. OBS-M7-CONC-01 : GET encore `executing`
après deux confirmations, 28/29 deux fois ; OBS-M7-UI-01 : `phone light`/`phone
dark`, clic `#btnSidebarClose` hors viewport/intercepté par topbar, 11/13.
Causes non établies ; ni bug produit confirmé, ni régression AUD démontrée,
ni simple instabilité qualifiée. Ces observations restent séparées et ouvertes,
sans patch M7. M4 historique 21/22 puis 22/22 reste de cause initiale inconnue.
Le relevé AUD-02 porte chaque exécution actuelle sans double compte ni effacement
des incidents. AUD-01 reste fermé ; clôture globale M8-C soumise au contre-audit
Codex après livraison Git, sans démarrer M8-S/M8-A ni déployer.

Comparaison finale du 9 octobre : **1 677 identités historiques exactes +
13 nouveaux = 1 690 succès**, zéro skip ; 70 + 26 voisins verts séparés.
Ciblés séquencés 86/86 ; négatif de la seule nouvelle garde : 2 IDs et 4 échecs
attendus, zéro erreur. M6 natif 5/5, M7 natif 13/13, M6 à fetch simulé 10/10 ;
M7 SQL 29/29, M4 Chromium 22/22. Observations M7/M4 historiques non résolues
par ces verts. Premiers ciblé/négatif contaminés par chevauchement des fixtures
SQL conservés ; premier groupe SQL 151/152 chevauché de 1,752 s, `exact=None`
au premier cas M1, cause précise non établie. Un rejeu séquencé exact donne
152/152 sans patch ni affaiblissement ; incidents exclus de la sélection finale,
conservés dans le relevé avec commandes/IDs/exits/durées, sans double compte.

### M8-S — Service Writer/UNO isolé et preuve plateforme

**Objectif :** livrer un renderer privé disponible, confiné et capable de produire
la paire DOCX/PDF sous le profil décidé, sans accès au stockage.
**Dépendances :** M8-C fermé ; GO Sauron distinct pour installation/livraison et rendu synthétique.
**Frontières :** Sauron gère la sous-stack réelle `/opt/platform/fridadev-app`,
image/wrapper UNO/profil/font/socket/exploitation ; exception documentaire explicite limitée à cette roadmap, aucun patch applicatif.
**Interface :** HTTP sur socket Unix ; UNO en pipe interne ; manifestes de capacités
et résultats selon section 9 ; aucun service existant présenté comme renderer livré.
**Propriétaire :** Sauron. Celebrimbor vérifie seulement la conformité du contrat remis.

- [x] Rouge causal : image sans filtre/font, appelant hors permissions, second job,
  macro/lien distant, sortie partielle, 21 pages ou LibreOffice bloqué → échec fermé.
- [x] Épingler image/digest, version LibreOffice/UNO, filtres DOCX/PDF, fichiers et
  empreintes/licences des polices, locale et profil ; aucun pin hérité implicitement de Stirling.
- [x] Livrer utilisateur non privilégié, rootfs read-only et seules zones tmpfs/socket
  nécessaires, network_mode none, caps retirées/no-new-privileges et ressources bornées.
- [x] Prouver socket Unix avec permissions dédiées, aucun port/routage public/UNO réseau,
  aucun secret Nextcloud/DB/provider, aucune donnée opérateur montée, aucun Docker socket.
- [x] Une tâche active, zéro file d'attente ; saturation rejetée. Profil UNO temporaire
  distinct, processus suivi/destructible et nettoyage succès/erreur/annulation/crash.
- [x] Tests synthétiques réels : Unicode, chaque style, tables multipages, sauts,
  A4/12 points/1,5/2,5 cm ; rechargement DOCX et export PDF du même état Writer.
- [x] Prouver nombre de pages Writer stabilisé et concordance PDF, filtres réellement
  présents, refus 21e page, aucune macro/update distant/extension ou dialogue bloquant.
- [x] Tests adverses de transport/archive/ressources/kill et seconde requête ; voisins
  FridaDev/Nextcloud/Stirling uniquement status-only, pas de document privé.
- [x] Faux verts : binaire présent, headless sans layout évalué, DOCX ouvrable, font de
  l'hôte, keepalive pris pour progrès, rootfs ro sans preuve du profil writable.
- [x] Interdire Caddy/Authelia/UI, cloud/payante, accès Nextcloud, fallback Stirling,
  nouveau moteur, données réelles ou canari d'écriture.
- [x] Synchroniser runbook plateforme et preuve datée content-free ; rebuild du seul
  service renderer réalisé dans ce lot, aucun restart voisin automatique.
- [x] Établir capacités réelles, sécurité/ressources/cleanup et artefact synthétique
  accepté par le contrat M8-C ; preuve moteur réalisée sans attendre M9, clôture après contre-audit.

**Livraison initiale plateforme — 10 octobre 2026, historique conservé.**
Douze critères exécutés, sans clôture forcée ni raccord applicatif. Rapport
Sauron : `/Users/tof/Saurons/sauron-frida-system/reports/2026-10-10-writer-m8s.md`,
commit `726a1ff30d545961b512d6fa03a37347e5c23d8a` sur `FridaV1-Document-Workshop-M8-S` (local, sans push).
Sources/runbook : `services/writer-renderer/` dans ce même commit. Image Docker
`sha256:419e953c98a149741c724c6b4515420966adc7523d6f4cdb2d527c071db18185`,
manifest OCI local `sha256:c1e292e3d4a8ae453817eb5abfad0fd777cc946f1ee69aac9d36e17e879f220d` ;
Writer/PyUNO 25.2.3.2, filtres DOCX/PDF et quatre Liberation Serif/OFL-1.1 épinglés.
Service `writer-renderer`, conteneur `platform-frida-writer`, socket
`/opt/platform/fridadev-app/writer-renderer/socket/renderer.sock` 0660,
répertoire 2770, UID/GID 20000:20000 ; client de preuve 20001:20000.
Protocole fermé et corpus 32/32, rendus riches 5 pages, 20 acceptées/21 refusées,
sources/refus hostiles, saturation, ressources, annulation, crash, sortie partielle,
UNO réellement bloqué 120 s malgré polls et travail utile >120 s vérifiés.
Trois défauts de revue interne reproduits puis corrigés/requalifiés : staging
ENOSPC, acquittement cleanup négatif et inventaire des libellés de liste ;
échecs intermédiaires conservés au rapport. Les 32 voisins gardent leurs IDs,
état actif et démarrages antérieurs au lot ; aucun restart/rebuild voisin.
Le Compose préexistant reste identique. Backup/rollback ciblé au rapport.
Aucun document privé, modèle, Nextcloud, Caddy/Authelia ou format public ;
M8-A et suivants non commencés. Cette revue interne ne vaut pas contre-audit.

**Correctif P2-M8S-AUD-01 livré — 10 octobre 2026 ; clôture M8-S soumise au contre-audit Codex.**
Finding confirmé sur l'image initiale : le PDF exact d'une liste est refusé
`renderer_source_unsupported`, tandis que le témoin sans liste passe. Le worker
reconstruit désormais le texte attendu depuis la structure canonical et les
libellés du Writer épinglé : décimal depuis 1/reset par bloc et puce U+2022.
Égalité intégrale conservée ; aucun effacement de nombres/puces, sous-chaîne ou
réécriture canonical. DOCX, protocole, six modules M8-C, profil/fonts/bornes et
lifecycle inchangés.
Rapport Sauron : `/Users/tof/Saurons/sauron-frida-system/reports/2026-10-10-writer-m8s-aud01.md` ;
sources/preuves/runbook commit `41d8f0322be95f7e226a216a69f9d5034396205c`
sur la branche M8-S locale, sans remote ni push.
Image courante `sha256:f3067a8fa6787e72a81cd72f94eb276c3887adf2e7907331a79aec98ca1c1487`,
manifest OCI `sha256:8737155ab4794d06077d796ec5d3406521790f289b87b4204490735907449bf3` ;
six couches initiales conservées + seule couche worker, socle/polices inchangés.
Qualification isolée sur vrai socket : sans liste, listes ordonnées 9→10/reset,
puces, reprise PDF exact et DOCX voisine ; 14 jobs, 11 ready validés M8-C et
3 discordances refusées (nombre littéral, puce littérale, reset différent).
Canonical et UUID source viennent des paires produites ; libérations acquittées,
job suivant possible. Corpus 32/32 rejoué une fois. Seul renderer recréé,
healthy/restart 0 ; smoke durable liste→PDF exact→libération en 4,436/4,200 s.
Workspace vide, aucun UNO résiduel, essais/temporaires possédés retirés ;
32 voisins strictement inchangés (ID/démarrage/restart/état/health), Compose
préexistant identique. Backup distinct et images initiale/corrigée conservées,
rollback limité au renderer. Aucun raccord FridaDev, document privé, modèle,
Nextcloud, Caddy/Authelia ou format public ; M8-A et suivants non commencés.

- [x] Corriger et livrer uniquement P2-M8S-AUD-01 après rouge causal et qualification ciblée.
- [ ] Contre-audit Codex du correctif et clôture M8-S ; aucun lot suivant démarré.

### M8-A — Adaptateur FridaDev, validations et nettoyage

**Objectif :** orchestrer le service livré sans capacité de stockage déléguée.
**Dépendances :** M8-C et M8-S fermés ; configuration du socket livrée par Sauron.
**Frontières :** document_renderer_client.py, document_rendering.py, execution,
révisions/actions/observabilité ; pas de LibreOffice dans app/Dockerfile.
**Interface :** submit/status/result/cancel-release, job ID et hash figés ; validation
locale des types, bytes, pages Writer, version/profile/fonts et résultat terminal.
**Propriétaire :** Celebrimbor ; Sauron seul raccorde le montage runtime de socket
et ses permissions dans sa racine, avec livraison FridaDev coordonnée si nécessaire.

- [ ] Rouge causal : résultat d'un autre job/révision, résultat tardif, transport perdu,
  timeout sans progrès, cleanup non acquitté ou mismatch pages/hash → zéro PUT/MKCOL.
- [ ] Tests serveur HTTP Unix fake et vraie consommation du transport ; voisins
  claims/confirmation/compensation/projections/streaming/upload/Exports/OCR.
- [ ] Transférer seulement canonical et octets admissibles ; persister le manifeste
  de rendu immutable et les octets figés avant journal/écriture conditionnelle.
- [ ] Tester confirmation doublée → un job et au plus un PUT ; perte de connexion
  → lecture d'état, aucun nouvel ID/retry automatique ; perte de worker → échec fermé.
- [ ] Projeter seulement progression réelle, 120 s d'inactivité puis annulation/kill ;
  ne pas inventer de deadline murale pendant progrès ni de TTL pending.
- [ ] Faux verts : client mocké hors transport, hashes non recalculés, résultat récupéré
  mais jamais libéré, event tardif non exercé, statut ready sans tous les artefacts.
- [ ] Interdire adresse/URL fournie par utilisateur, mount partagé de documents,
  secrets envoyés, mutation avant validation et activation prématurée DOCX/PDF.
- [ ] Synchroniser adapter/erreurs/observabilité ; preuve interne synthétique réelle
  sous GO distinct, sans modèle ni Nextcloud. Rebuild FridaDev à livraison autorisée.
- [ ] Fermer avec contrat M8-S réellement consommé, cleanup confirmé et invariants
  M5 préservés ; aucune API renderer publique ni sortie partielle publiée.

### M9-A — DOCX Frida create/copy/update et pagination Writer

**Objectif :** publier le DOCX validé et préserver son identité/canonical lors d'un update.
**Dépendances :** M7 et M8-A ; moteur/profil/filtres épinglés disponibles.
**Frontières :** adapter Writer, révisions/manifeste, policy DOCX, content service frais,
executor et projection de carte ; aucune logique UNO dans le pipeline principal.
**Interface :** canonical Frida → DOCX final rechargé/paginé Writer ; source distante
Frida récupérée/validée temporairement, update If-Match sur même ID/nom.
**Propriétaire :** Celebrimbor ; Sauron traite seulement une non-conformité plateforme prouvée.

- [ ] Rouge causal : canonical/source/empreinte non correspondants, 21e page, version
  renderer différente ou ETag changé durant rendu → refus sans écriture.
- [ ] Tests structure/styles/listes/tableaux/liens/pages, réponse/action/reçu/inventaire ;
  voisins DOCX reader/Exports/Notes ETag ; succès → même workspace_file_id.
- [ ] Prouver Writer rechargé sur les octets DOCX finaux, page_count stabilisé et
  PDF de contrôle issu du même état, sans le publier si seul DOCX est demandé.
- [ ] Faux verts : docProps ou PDF voisin seul, ancien canonical retrouvé, If-Match
  absent de la requête finale, test de création présenté comme preuve d'update.
- [ ] Interdire renommage/copie implicites, image, fidélité Word universelle et
  écriture après échec de rendu ; conserver MD indépendant d'une panne Writer.
- [ ] Synchroniser formats/pagination/continuité ; rendu synthétique et canari DOCX
  ont chacun leur GO, canari uniquement après gardes/compensations hermétiques.
- [ ] Rebuild applicatif à livraison ; fermer create/copy/update, conflits réels,
  correspondance canonical/rendu et reçu au tour suivant.

### M9-B — Retravail DOCX externe avec fidélité honnête

**Objectif :** retravailler une cible externe explicitement mobilisée, sans promettre
une conservation parfaite d'une mise en page arbitraire ou supprimer du contenu caché.
**Dépendances :** M9-A ; garde d'adoption/fraîcheur M2, policy externe de section 9.5.
**Frontières :** préflight OOXML, readers, canonical, mode source_docx du wrapper,
validation source/résultat, carte de limites et executor stable-ID.
**Interface :** octets source récupérés par FridaDev + hash/ETag préparés + canonical
candidat ; import temporaire UNO, classification de fidélité puis rendu du profil V1.
**Propriétaire :** Celebrimbor pour policy/tests ; Sauron livre dans son wrapper
le mode fermé dans M8-S selon M8-C ; M9-B consomme ce mode déjà prouvé, sans
nouvelle livraison plateforme requise. Toute correction reste dans sa racine,
sans patch applicatif.

- [ ] Rouge causal : macro, champ dynamique, contenu image/objet, révision suivie,
  style/section non représentables, texte incomplet ou import réparé → refus honnête.
- [ ] Tester sources simples admissibles et conversion/round-trip avec tables/styles ;
  limites annoncées sur la carte avant clic, changement source avant/durant rendu.
- [ ] Comparer inventaire de contenu admissible/source textuelle et sortie canonical ;
  aucune perte détectée cachée, aucune copie automatique ; update même nom/ID/If-Match.
- [ ] Faux verts : même texte mais champs/images effacés, extraction ZIP sans inventaire,
  échantillon exclusivement créé par Frida présenté comme DOCX externe, limites non visibles.
- [ ] Interdire fidélité complexe garantie, code actif, images ajoutées ou supprimées
  silencieusement, import de n'importe quel format et ODT durable concurrent.
- [ ] Synchroniser politique de fidélité/refus ; corpus externe exclusivement synthétique,
  rendu réel et canari update sous GO séparés ; rebuild applicatif à livraison.
- [ ] Fermer sur cas simple utile et cas complexes refusés causalement, avec provenance
  externe conservée et révision Frida liée au même fichier après succès.

### M10 — PDF Writer, source externe et intégration finale des formats

**Objectif :** publier le PDF du même moteur/révision ; préserver la politique des PDF sources.
**Dépendances :** M9-B, donc tous les sous-lots M8/M9 fermés ; zéro pipeline PDF parallèle.
**Frontières :** export Writer via adapter, reader PDF existant, policy de cible,
manifeste de rendus, confirmation/reçus et UI des trois formats.
**Interface :** export writer_pdf_Export du même état Writer que le DOCX validé ;
PDF Frida lié au canonical, PDF externe source vers nouveau document demandé.
**Propriétaire :** Celebrimbor ; Sauron seulement pour non-conformité du service livré.

- [ ] Rouge causal : externe pris comme cible update, PDF Frida désynchronisé,
  export partiel/21 pages ou divergence de pages Writer/PDF → zéro mutation.
- [ ] Tests Unicode/fonts/pagination/tableaux/liens, PDF chiffré/scanné, canonical
  absent/octets modifiés ; voisins readers/Exports/OCR et read/copy/update inter-formats.
- [ ] Vérifier <=20 pages Writer, A4/12 points/1,5/2,5 cm et le PDF final ; aucune
  sauvegarde partielle, ODT caché, page réduite ou appel Stirling de composition.
- [ ] Faux verts : texte présent sans layout, PDF compagnon d'une autre révision,
  timestamp/hashes ignorés, PDF externe chargé dans Draw comme édition fidèle.
- [ ] Interdire PDF externe édité en place, OCR implicite, image, fallback ou
  désynchronisation canonical/rendus ; seul le format demandé est écrit.
- [ ] Synchroniser politique PDF/provenance/refus ; preuve interne synthétique et
  canari sous GO distincts ; rebuild FridaDev à livraison autorisée.
- [ ] Fermer les trois formats et les deux politiques PDF, sécurité/cleanup et
  continuité end-to-end ; moteur inchangé, aucun service bureautique supplémentaire.

### Z — Clôture bornée

**Objectif :** fermer le premier palier sans chantier permanent.
**Dépendances :** M0–M7, M8-C/M8-S/M8-A, M9-A/M9-B et M10.
**Frontières :** parcours complets, preuves et contrats vivants.
**Interface :** services appelables sans DOM ; aucun tool principal.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : pending rejouable après refresh, cache obsolète, reçu perdu ou
  canonical contaminant une faculté doivent être détectés.
- [ ] Matrice finale ciblée desktop/mobile/conversations croisées/crashs/formats ;
  voisins upload/Notes/Exports/Images/Agenda/Biblio/pipeline/OCR et entrée Stirling.
- [ ] Inclure M8-C/M8-S/M8-A/M9-A/M9-B/M10 : sécurité réseau/secrets, filtres/fonts,
  layout livré, saturation/kill/cleanup et paire Writer cohérente.
- [ ] Faux vert : smoke nominal seul ou régression voisine non exercée.
- [ ] Interdire nouvelle dépendance, extension d'édition, benchmark général et tools
  du modèle principal.
- [ ] Rassembler preuves autorisées et limites ; retirer états transitoires remplacés.
- [ ] Synchroniser contrats vivants/statuts/preuves avec le comportement livré,
  puis archiver cette même TODO à fermeture ; aucune roadmap concurrente.
- [ ] Rebuild seulement pour correction effectivement livrée.
- [ ] Fermer chaque critère par une preuve et les limites/refus du contrat testés,
  sans finding vivant caché ; ne pas ouvrir une nouvelle capacité pour prolonger la clôture.
- [ ] Aucun moteur secondaire, suite bureautique supplémentaire ou pipeline PDF
  parallèle sans décision produit explicite ; aucun lot ajouté pour prolonger Z.

## 9. Architecture serveur Writer/UNO et preuves à livrer

### 9.1. Quatre rôles et autorité

```text
Utilisateur : geste documentaire explicite → demande canonique → confirmation humaine
                                      |
FridaDev (orchestrateur, canonical, claim, validation, seuls secrets/capacités DAV)
  | HTTP privé sur socket Unix ; canonical + octets temporaires, IDs techniques
  v
Renderer isolé sur le même serveur : wrapper fermé → UNO en pipe local → Writer
  | DOCX enregistré + PDF exporté + métadonnées ; aucun accès au stockage
  v
FridaDev : vérifications → écritures conditionnelles → transaction locale → reçu
  | seul chemin de mutation de l'atelier
  v
Nextcloud : Documents du répertoire choisi + identité/ETag + historique Versions
  ↔ Collabora/Nextcloud : éditeur humain des fichiers enregistrés

Stirling-PDF : utilitaire humain séparé pour PDF existants ; entrée Homepage conservée
             + OCR explicite existant de Frida préservé ; hors génération Writer
```

La flèche Collabora représente un rôle humain, pas une disponibilité démontrée
par cette inspection. Ce chantier ne livre pas Collabora, n'installe pas Writer
« dans Nextcloud » et ne remplace pas une UI Nextcloud. Stirling n'est ni supprimé
ni chaîné derrière Writer. Fusion/découpe/conversion sont décrites par l'entrée
humaine observée ; rotation/compression et autres fonctions ne sont pas déclarées
prouvées sans recette. OCR existant : contrats actuels inchangés.

### 9.2. Forme minimale livrée et raccord restant

M8-S livre dans `/opt/platform/fridadev-app` le service `writer-renderer`,
conteneur `platform-frida-writer`, image/worker distincts de `platform-fridadev`.
Socket `/opt/platform/fridadev-app/writer-renderer/socket/renderer.sock` :
UID/GID 20000:20000, mode 0660, répertoire 2770. Il est monté dans le seul
renderer ; client synthétique hôte 20001:20000. Le montage et l'identité du
client FridaDev restent M8-A, sans modification du conteneur FridaDev ici.
Aucun document, state/, secret, DB, volume Nextcloud ou socket Docker partagé.
Le futur client applicatif est HTTP AF_UNIX de bibliothèque standard,
sans dépendance bureautique dans son image.

Le wrapper écoute seulement sur ce socket Unix et pilote UNO sur un pipe local.
`network_mode: none`, aucun listener TCP ni port publié ; Caddy/Authelia/UI,
DNS et réseaux partagés inchangés. Confinement et permissions effectivement
vérifiés par M8-S ; aucun shell/SSH/Docker exec offert à FridaDev.

Sauron conserve image/wrapper/runtime et preuves dans son dépôt, avec cette
seule roadmap modifiée par exception explicite de Tof. Celebrimbor réalise
adaptateur/orchestration dans le checkout. La future connexion du socket
peut imposer une recréation ciblée FridaDev gérée par Sauron sous mandat M8-A.
Aucune recréation FridaDev ni restart global dans M8-S.

### 9.3. Protocole fermé et bornes techniques

Schémas fermés versionnés, champs inconnus et clés dupliquées refusés. Le
[contrat M8-C v1](../../states/specs/frida-v1-document-workshop-m8c-contract.md)
fixe champs obligatoires/nullables, encodage, unités exactes, HTTP/erreurs et
corpus autonome. Cette section conserve les invariants communs. Interfaces internes seulement :

| Méthode | Effet |
| --- | --- |
| GET /v1/capabilities | Version du contrat/image/Writer/UNO, filtres, profil/polices et limites ; aucun contenu ni secret. |
| POST /v1/jobs | render_request_v1 : job_id, revision_id/hash, profil épinglé, format DOCX ou PDF, canonical validé, source fermée nullable et partie octets/hash optionnelle. Claim Frida confirmé requis côté orchestrateur. |
| GET /v1/jobs/{id} | État et progression vérifiable, jamais canonical ou aperçu. |
| GET /v1/jobs/{id}/result | Résultat terminal multipart borné : manifeste JSON et artefacts nommés techniquement par le wrapper, sans chemin opérateur. |
| DELETE /v1/jobs/{id} | Annulation/destruction ou acquittement/libération d'espace éphémère ; ne touche jamais Nextcloud. |

La source optionnelle est fermée : aucune, DOCX mobilisé, ou PDF Frida dont le
canonical correspondant est établi. PDF Frida : octets pour contrôle de source,
jamais import Writer/Draw destiné à éditer le PDF. Aucune URL/href comme adresse
de source à télécharger, destination DAV, ETag secret, nom privé, instruction UNO
libre, filtre libre, chemin absolu, commande, macro, template externe ou fetch
arbitraire dans le protocole. Les liens hypertextes admissibles du canonical
restent des données passives validées ; ils ne sont jamais chargés par le renderer.

Profil technique initial de l'architecture proposée, distinct des plafonds
produit de Tof : une tâche active, **zéro file** (busy → refus contrôlé), une source
binaire au plus, 1 MiB pour le JSON canonical/enveloppe, source au plus 40 MiB
(plafond upload actuel ; admission réelle/extraction peuvent être plus strictes),
requête totale au plus 42 MiB, 16 MiB par artefact DOCX/PDF et 33 MiB pour le
résultat complet. Expansion ZIP/XML cumulée au plus 64 MiB et au plus 4 096 entrées ;
structures bornées par le schéma/admission M8-C. Aucun plafond n'autorise une
troncature ; dépassement technique → refus explicite, jamais taille produit choisie.

Sauron épingle à la livraison le profil d'exploitation : quota 1 vCPU, mémoire
1 GiB, tmpfs de travail 256 MiB maximum, limite de processus et descripteurs
explicites (64/256), aucun disque persistant documentaire. Ces gardes techniques
sont à appliquer/prouver, pas des capacités mesurées de l'hôte ici. Si ce profil
ne soutient pas un cas admissible, le lot rapporte l'écart avant sa fermeture ;
il ne change pas les 20 pages/10 000 mots/75 000 caractères ni le moteur.

Le temps est borné par **120 secondes sans progression effective** ; aucun
watchdog absolu supplémentaire tant que la progression continue. Avancement :
blocs réellement appliqués, import/layout/export achevés ou étape utile vérifiable ;
ni pulse, poll, CPU consommé, animation ni lease ne réarment ce compteur. La
même borne inclusive vaut jusqu'à la décision finale après libération acquittée :
ni collecte, validation, début de libération ni acquittement ne réarment le temps.
Un snapshot local peut exister sans bundle livrable ; un refus tardif ne répète
pas le nettoyage déjà tenté/acquitté. Frida
projette cet état après clic. Un UNO bloqué est neutralisé par un superviseur
hors de son appel bloquant : destruction du groupe de processus, nettoyage du
profil/espace de travail, erreur terminale. Perte du worker/OOM : échec fermé
et suppression de son espace éphémère à la reprise, aucun replay de mutation.

render_result_v1 exige status, reason_code allowlisté, job/révision/hash d'entrée,
version renderer/image/Writer/UNO/profil/filtres/polices, source hash si présente,
et pour chaque artefact type, longueur, SHA-256, compte de pages Writer ; PDF
également vérifié par son compteur final. ready seulement si tous les artefacts
attendus sont complets ; sinon aucun artefact partiel consommable comme succès.
Frida recalcule tailles/empreintes/types et vérifie les versions/pages avant PUT.

États worker fermés : rendering, ready, refused, failed, cancelled ; inconnu/perdu
est projeté lost par Frida et ne vaut jamais succès. Codes minimaux du contrat :
renderer_ready, renderer_busy, renderer_input_invalid, renderer_source_unsupported,
renderer_profile_mismatch, renderer_page_limit, renderer_incomplete,
renderer_inactivity, renderer_resource_limit, renderer_cancelled,
renderer_job_conflict, renderer_job_lost et renderer_cleanup_failed. Toute raison
non reconnue est une erreur de protocole, sans exception brute. Les phases et
comptes d'avancement sont monotones et bornés par les étapes/blocs réellement attendus.

Même job_id et même empreinte de requête complète (distincte du hash canonical,
liant aussi révision/format/profil/source/pins) : lecture de l'état/résultat, aucune seconde exécution ;
job_id réutilisé avec autre hash : conflit. Dédoublonnage à durée de vie du worker,
pas promesse exactly-once distribuée. Claim/journal durable Frida font autorité ;
worker redémarré/job perdu → erreur honnête, aucun retry caché. Après récupération
validée et persistance locale des octets/manifeste, Frida acquitte la libération.
Profil, sources et ODT éventuel sont détruits sur tous les états ; reaper borné
nettoie les résultats orphelins sans faire expirer un pending qui n'a pas encore
lancé de job. Aucun store de fichiers concurrent dans le renderer.

### 9.4. Composition, filtres et pagination Writer

Writer est l'unique moteur nominal DOCX/PDF de cet atelier. Markdown reste
sérialisé directement depuis canonical. Aspose, éditions payantes/filigranées
d'ONLYOFFICE, cloud, second moteur et fallback sont exclus. Les cases cochées ci-dessous sont prouvées côté renderer par M8-S ;
la publication Nextcloud et la persistance applicative restent M8-A et suivants :

- [x] Créer un modèle Writer contrôlé via UNO depuis le canonical : titres,
  paragraphes, gras/italique, listes, citations, liens passifs, tableaux simples
  et sauts de page ; aucune image ni contenu actif.
- [x] Épingler image/digest/version LibreOffice/UNO et disponibilité des filtres
  `Office Open XML Text` pour DOCX et `writer_pdf_Export` pour PDF. Aucun filtre
  commandé par le modèle ou document ; pas de conversion CLI nominale seule.
- [x] Épingler fichiers/polices normales/gras/italiques, licences, empreintes, locale,
  profil A4/12 points/interligne 1,5/marges 2,5 cm ; absence de glyphes/font → refus.
- [x] Enregistrer DOCX, le recharger dans le même Writer sans mutation de son contenu
  ou profil, forcer/stabiliser le layout et relever ses pages. Exporter le PDF
  depuis ce même état rechargé ; vérifier compte PDF final et concordance Writer.
  Une paire de validation interne ne crée pas deux fichiers produit : seul le
  format confirmé est publié dans Nextcloud.
- [x] Prouver l'API de layout effectivement opérante en headless (p. ex. curseur de
  pages UNO après layout), pas un champ docProps ou un compteur de sauts déclaré.
  Export partiel, désaccord de pages, plus de 20 pages ou layout non établi : refus.
- [x] Le nombre de pages contractuel est celui de ce Writer épinglé, avec ces polices ;
  aucune identité mathématique universelle avec Microsoft Word n'est revendiquée.
- [ ] Canonical Frida seule source structurée durable ; DOCX/PDF liés à sa révision
  et au manifeste de rendu. ODT éventuel strictement temporaire dans le job, jamais
  adopté, inventorié ou promu en deuxième vérité.
- [x] Tests synthétiques Unicode français/styles/tableaux/sauts/pagination, stabilité
  de layout/contenu sur répétition. Métadonnées volatiles fixées ou précisément
  déclarées ; aucune promesse de SHA binaire universel si le moteur ne la tient pas.
  L'exécution utilise toujours les octets effectivement figés et leur empreinte.

### 9.5. Cibles existantes et garanties distinctes

| Cas | Contrat de traitement |
| --- | --- |
| Création Frida DOCX/PDF | Canonical complet, profil contrôlé, paire Writer validée ; Frida choisit la cible Documents confirmée et fait PUT no-clobber. |
| Update DOCX Frida | Frida récupère la cible/identité/ETag ; source temporaire remise au worker et correspondance canonical/hash prouvée ; révision candidate rendue, même ID/nom, If-Match de version préparée. |
| Update PDF Frida | Même garde de correspondance source/canonical ; récupération temporaire, rendu depuis canonical via Writer, aucun import PDF éditable. If-Match exact et même ID/nom. |
| DOCX externe | Frida récupère/inspecte complètement la source, la remet temporairement à UNO. Sous-ensemble V1 représentable seulement ; conversion/retravail et remise en forme du profil V1 annoncés avant clic. Aucun héritage universel de mise en page. |
| PDF externe | Lecture avec les readers existants, jamais édition UNO en place ; demande de modification vers un nouveau document explicite. Aucun OCR implicite ou copie automatique de secours. |

Correspondance PDF Frida côté renderer : égalité intégrale du texte extrait avec
le canonical et les seuls libellés de liste du profil Writer épinglé (décimal
depuis 1, redémarrage par bloc, puce U+2022). Nombres et puces littéraux restent
significatifs ; aucune suppression générale ni comparaison par sous-chaîne.
P2-M8S-AUD-01 corrigé et prouvé ci-dessus ; provenance/ETag/reçu applicatifs restent M9/M10.

DOCX externe : préflight OOXML puis inspection UNO concordante, import sans
réparation automatique. L'action préparée lie la source/ETag et les limites utiles
avant confirmation. Contenu simple admissible : textes, styles V1, listes et
tableaux simples ; transformations fondées sur le canonical candidat, inventaire
source complet et contrôle du résultat. Style arbitraire, champs dynamiques,
révisions suivies, sections complexes, cadres/objets/images ou contenu non
représentable : clarification/refus, jamais suppression silencieuse. Aucun champ
externe mis à jour ni code exécuté. Liens hypertextes passifs conservables ne sont
pas des autorisations de chargement distant. La fidélité de création contrôlée
et celle d'import externe ont des corpus et critères de clôture séparés M9-A/M9-B.

Juste avant mutation, Frida revérifie toutes les préconditions après le temps
passé dans Writer. Conflit → aucune fusion/écriture aveugle. Sauron ne reçoit
ni cible DAV ni secret ; Nextcloud reste autorité de Versions. Le reçu relie
résultat, identité stable, format, cible et révision, sans injecter le contenu.

### 9.6. Confinement et exploitation prouvés côté renderer M8-S

- [x] Utilisateur non privilégié, rootfs read-only compatible ; tmpfs writable
  uniquement pour travail/tmp/profil, répertoire de socket séparé ; aucune
  lecture arbitraire du filesystem, mount opérateur ou capability de commande.
- [x] Démarrage fixed argv headless/norestore avec UserInstallation éphémère par
  exécution ; UNO acceptor en pipe interne ; aucune option fournie par l'appelant.
- [x] Macros `NEVER_EXECUTE`, liens `NO_UPDATE`, interaction handler refusant demandes
  de chargement/mot de passe/réparation, extensions non nécessaires absentes ;
  network none et tests de non-chargement remote, pas confiance dans Hidden seul.
- [x] Profil utilisateur séparé pour chaque job, fermeture/dispose document, destruction
  processus bloqué et nettoyage enfin garanti, y compris crash/OOM/redémarrage.
- [x] Tests source hostile et extraction ZIP bornée, traversée interne/symlink,
  chargements locaux externes, pertes de contenu, concurrence et saturation.
- [x] Aucun contenu brut, nom privé, source binaire, URL sensible ou exception brute
  dans logs/health/rapports ; seules versions, tailles, phases et reason codes.
- [x] Health/capabilities sans ouverture de document ; preuve synthétique de rendu
  séparée et autorisée. Disponibilité du service et qualité de layout sont deux preuves.

Preuves limitées au renderer isolé et aux sources synthétiques ; un défaut de
nettoyage injecté donne cleanup_failed sans acquittement positif, puis réparation
explicite de la probe. Aucun retry caché, aucune promesse de suppression malgré
une erreur filesystem ; admission suivante seulement après libération validée.

### 9.7. Références primaires LibreOffice revalidées

Liens officiels consultés en lecture publique seulement ; aucun document exécuté.
La documentation `latest` décrit les API, pas un pin de livraison de notre service :
M8-S fournit les pins et preuves correspondant à sa version réelle.

- [Licence LibreOffice](https://www.libreoffice.org/licenses/) : logiciel libre,
  MPL 2.0 avec composants sous autres licences ouvertes ; notices de l'image/polices à conserver.
- [Démarrage headless, accept UNO et UserInstallation](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html).
- [Filtres Writer DOCX et PDF](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html).
- [API UNO XStorable](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1frame_1_1XStorable.html) : storeAsURL pour enregistrement, storeToURL pour export.
- [Paramètres d'export PDF](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html).
- [Curseur de pages Writer](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1text_1_1XPageCursor.html) : API de pages effectivement exercée en headless par M8-S.
- [MediaDescriptor UNO](https://api.libreoffice.org/docs/idl/ref/servicecom_1_1sun_1_1star_1_1document_1_1MediaDescriptor.html) : chargement/contrôle de macros, liens et interactions.
- [Macros NEVER_EXECUTE](https://api.libreoffice.org/docs/idl/ref/namespacecom_1_1sun_1_1star_1_1document_1_1MacroExecMode.html).
- [Liens NO_UPDATE](https://api.libreoffice.org/docs/idl/ref/namespacecom_1_1sun_1_1star_1_1document_1_1UpdateDocMode.html).

## 10. Matrice réutiliser / extraire / créer et propriétaires

| Traitement | Frontières |
| --- | --- |
| Réutiliser | Inventaire workspace_files, sélections, extracteurs, liens produit, protocole terminal, clients DAV et éléments de compensation ETag. |
| Extraire pour une responsabilité réelle | Primitive de snapshot transactionnelle ; concepts de formats/validation sans extraire un second moteur ni modifier le renderer Exports livré. |
| Modifier | Transport/service/finalisation chat, projections, liens/store workspace, clients DAV bornés, manifestes/guards, binding Fichier et réhydratation. |
| Créer côté application | Services atelier/canonical/actions/reçus/claims/adoption/fraîcheur, contrôleur UI et contrat/adaptateur Writer ; aucun moteur bureautique embarqué. |
| Livrer côté plateforme | Service Writer/UNO isolé, wrapper fermé, image/filtres/profil/polices épinglés et exploitation par Sauron. |

Modules probables, noms proposés et non fichiers déjà livrés :

- document_workshop_contract.py : entrées/sorties/capacités.
- document_workshop_agent.py : appel unique et validation.
- document_workshop_turn_service.py : raccord conversationnel.
- document_workshop_store.py : artefacts/révisions/actions/reçus et transactions.
- document_workshop_execution.py : confirmation/journal/exécution.
- document_workshop_routes.py : frontières HTTP.
- document_canonical.py : modèle structuré ; document_rendering.py : orchestration
  du rendu et validation, sérialisation Markdown directe, aucun UNO embarqué.
- document_renderer_contract.py : schémas fermés, identités/snapshots et capacités ;
  document_renderer_wire.py : framing strict ; document_renderer_artifacts.py :
  inspections de type/archives/PDF bornées, aucune exécution Writer.
- document_renderer_client.py : HTTP Unix borné, suivi/résultat/annulation/libération.
- workspace_document_paths.py : racine/segments.
- workspace_document_content_service.py : fraîcheur/lecture.
- workspace_document_adoption_service.py : navigation/adoption.
- document_receipt_prompt_lane.py : métadonnées du tour suivant.
- conversation_turn_claims.py et store associé : réservation/fencing.
- chat_document_workshop.js : contrôleur frontend.

Fichiers à protéger d'un allongement : workspace_files_service.py (516 lignes),
workspace_folder_documents.py (487), workspace_document_nextcloud_runtime.py (463).
Déjà plus grands : chat_service.py, conversations_store.py, chat_llm_flow.py,
active_document_prompt_lane.py, app.js et chat_threads_sidebar.js. Ces comptes sont
ceux du HEAD de reconnaissance ; aucun refactor cosmétique n'est proposé.

### Lot Sauron obligatoire et besoins conditionnels

- [x] M8-S : service Writer/UNO isolé, image/filtres/polices/profil/ressources/socket,
  sécurité/cleanup/health et preuve synthétique livrés, correctif P2-M8S-AUD-01 inclus ; voir section 8, clôture à contre-auditer.
- [ ] Prouver identité DAV, préconditions, ETags et Versions si les preuves
  applicatives ne suffisent pas.
- [ ] Fournir une preuve transactionnelle isolée si environnement SQL absent.

M8-S est une vraie frontière plateforme, sans accès Nextcloud et sans surface
publique. Permissions DAV ou environnement SQL partagé relèvent de besoins
Sauron conditionnels distincts. Pins/bibliothèques/polices sont dans l'image du
renderer, pas dans FridaDev. Sauron modifie seulement cette roadmap par exception explicite ; Celebrimbor ne
modifie aucune stack, réseau, secret ou fichier sous sa racine plateforme.

## 11. Faits externes restant à prouver

Toutes les décisions produit et architecturales amont sont fermées. Budgets,
volume, source longue, progression/pending, chemins et moteur ne sont plus des
inconnues ou des comparaisons. M0 ferme leurs gardes internes ; raccordements,
transactions, pagination et parcours produit restent aux lots concernés.

- [ ] M2/M5/M7 : comportement DAV effectif, identité distante, préconditions/ETags
  et Versions disponibles sur la chaîne déployée.
- [ ] M3 : environnement SQL concurrent isolé de preuve si non établi par le HEAD.
- [ ] M8-S/M8-A : disponibilité effective du service isolé, permissions de socket,
  capacités/filtres/polices/layout du pin livré, ressources/confinement/cleanup.
  Partie M8-S prouvée ci-dessus ; raccord M8-A non commencé.
  Ce sont des preuves de livraison, aucun choix de moteur repoussé.
- [ ] M9-A/M9-B/M10 : stabilité Writer réelle, import/round-trip externe admissible
  et limites détectées du corpus synthétique ; aucune promesse Word universelle.

Collabora n'est pas prouvé actif par la lecture non sensible de ce lot. Son rôle
d'éditeur humain est conservé ; sa disponibilité n'est pas une dépendance de
l'atelier et son installation ne devient pas un lot implicite de cette roadmap.

Ces faits ne justifient pas de changer les décisions : précondition non prouvée
→ refus fermé ; besoin de plateforme → lot Sauron ciblé et autorisé. Le calcul
d'admission, la progression et la pagination sont des obligations d'implémentation
et de preuve de M0/M4/M8–M10, pas des arbitrages repoussés.

## 12. Contre-audit et critères de clôture

- [ ] Distinguer décisions validées, faits du HEAD, implémentation future et preuves.
- [ ] Ne conserver aucun ancien OPEN fermé par le design consolidé.
- [ ] Une soumission, une vraie parole utilisateur, un échange documentaire.
- [ ] Upload/picker/change/drag-and-drop conservés, sans duplication mobile.
- [ ] Navigation/adoption ciblées ; aucun synchroniseur global.
- [ ] Aucune mutation distante avant confirmation et claim valides.
- [ ] Canonical/profil/cible figés avant confirmation ; octets binaires/manifeste
  figés et validés après claim, avant MKCOL/PUT ; correspondance distante vérifiée.
- [ ] Reçu séparé des paroles et des tool results ; réhydratation durable.
- [ ] Inventaire unique workspace_files, ID stable en update.
- [ ] ETag frais et If-Match réellement envoyés ; aucun écrasement implicite.
- [ ] Journal et remote_uncertain sans promesse d'exactly-once distribué.
- [ ] Aucun DELETE sans propriété ni rollback récursif de collections.
- [ ] DOCX externe et PDF externe traités avec fidélité honnête.
- [ ] Writer/UNO isolé livré/épinglé/prouvé par M8-S, adaptateur M8-A ; aucun moteur
  concurrent, cloud/payante, fallback ou LibreOffice dans le conteneur FridaDev.
  M8-S et correctif P2-M8S-AUD-01 livrés, clôture à contre-auditer ; case globale laissée ouverte pour M8-A.
- [ ] Nextcloud/Collabora/Stirling distincts ; entrée humaine et OCR Stirling préservés.
- [ ] Aucun secret/capacité DAV dans le renderer, aucun UNO brut ni API publique,
  socket restreint/network none et fichiers éphémères nettoyés, ODT jamais vérité durable.
- [ ] Pagination réelle du DOCX final rechargé dans Writer et PDF du même état,
  sans docProps fictif ou équivalence Word universelle.
- [ ] Graphe M8-C→M8-S→M8-A→M9-A→M9-B→M10 sans dépendance circulaire.
- [ ] Document produit <=10 000 mots et <=75 000 caractères Unicode ; DOCX/PDF
  rendus <=20 pages Writer A4, corps 12 points/interligne 1,5/marges 2,5 cm.
- [ ] Markdown sans pagination stable ; aucun plafond de 20 pages appliqué aux sources.
- [ ] Source longue admise si entrée complète admissible ; sinon réduction/sélection
  ou refus avant appel, aucune troncature/résumé/échantillonnage silencieux.
- [ ] Un appel documentaire gpt-5.1, plafond dédié 24 000, chat inchangé 8 192,
  entrée estimée par le compteur partagé plus 24 000 <=400 000 ; aucune promesse d'équivalence
  tokens/mots/caractères/pages.
- [ ] Refus sur finish_reason=length, canonical incomplet ou dépassement ; aucune
  sauvegarde partielle, réparation, continuation ou fallback.
- [ ] Progression réelle honnêtement projetée ; 120 secondes sans progrès → échec
  fermé ; aucune deadline murale tant que la progression continue.
- [ ] Annulation utilisateur, invalidation pending et lease technique distingués ;
  pending sans expiration temporelle et confirmation avec fraîcheur/ETag/scope/claim.
- [ ] Bornes de chemin décidées appliquées localement/DAV et au nom de fichier,
  sans raccourcissement/renommage/normalisation destructive silencieuse.
- [ ] Memory/Identity/Summary/Biblio/Stimmung préservés et non contaminés.
- [ ] Service tool-ready appelable sans DOM, aucun tool principal implémenté.
- [ ] Tous les parcours create/read/adopt/update/copy et les trois formats prouvés.
- [ ] Preuves live éventuelles explicitement autorisées et content-free.
- [ ] Docs/limites/statuts synchronisés ; aucun finding vivant caché.
- [ ] Lot Z fermé ; suites images/continuations/édition enrichie hors ce chantier.
- [ ] Aucun moteur secondaire, suite bureautique supplémentaire ou pipeline PDF
  parallèle sans nouvelle décision produit ; aucune extension opportuniste.

## 13. Statut de publication documentaire

Cette TODO conserve la spécification et les décisions validées par Tof sous forme
de cases à cocher. M0 ferme les composants internes avec tests hermétiques et
contre-audit corrigé et livré sur sa branche dédiée (`3eb2e34a`). M1 est fermé sur
menu/contexte `editing` et gardes inactifs sur sa branche issue de M0 ; livraison
Git M1 corrigée par P3 `c6f648ba`, constatée avant création de M2. M2 dispose du
succès historique 536/536 après G-R1–G-R4, dont la contre-revue du delta est
Approved ; les 528 premiers restent historiques. Le 5 octobre, P2-M2-01 est
corrigé et la comparaison historique passe 567/567. P2-M2-03 est ensuite
corrigé séparément en frontend (594/594 historiques) ; P2-M2-02 est ensuite
corrigé séparément sur Exports/Images/Notes,
P2-M2-04 backend est corrigé séparément (713/713 historiques). P2-M2-05 est
ensuite corrigé sur le résumé de réconciliation (716/716). Le retour final porte la livraison Git et ses
alignements. M3 est fermé sur code/preuves/Git ; son P3 golden a été corrigé
séparément avant M4. La livraison initiale M4 est conservée comme déclaration
historique explicitement rectifiée par P3-M4-03 ; les identifiants réutilisables
sont corrigés. P2-M4-01 et P2-M4-02 sont fermés après leurs contre-audits
indépendants, avec leurs résultats conservés ci-dessus ; P3-M4-03 est corrigé
documentairement, sans fermer la livraison runtime de M4 ;
M5 est fermé sur code/preuves hermétiques et contre-audit ; M6 est réalisé sur
code/preuves isolées et contre-audit. M7 est fermé sur code/preuves isolées et contre-audit, livraison runtime ouverte ; AUD-01 et AUD-02 fermés après contre-audits indépendants.
**M8-C fermé sur contrat, code et preuves isolées ; M8-S et correctif P2-M8S-AUD-01 livrés/qualifiés, clôture soumise au contre-audit Codex.**
M8-A, M9/M10/Z restent non commencés et les
obligations runtime restent ouvertes.
Elle complète les contrats vivants pour la nouvelle capacité bornée autorisée
dans AGENTS.md ; l'invariant de consolidation reste applicable hors de cette
exception. Les seuls composants applicatifs livrables par M0 sont les frontières
internes inactives et leurs preuves. M1 ajoute seulement entrée et contexte
`editing`, avec préparation indisponible. M2 ajoute exclusivement lecture/adoption ciblées et inventaire commun, avec
préparation historiquement indisponible. M3 ajoute l’autorité commune ; M4
raccorde uniquement la préparation Markdown sans écriture. Ces lots applicatifs ne livraient aucune dépendance ou service plateforme.
M8-S livre désormais le seul renderer isolé, son correctif P2-M8S-AUD-01 et ses preuves synthétiques sous
mandat distinct ; cette exception documentaire ne raccorde aucun consommateur. La correction P3 M1 est séparée ; la
livraison M2 reste limitée à `FridaV1-Document-Workshop-M2`. Aucun merge vers main,
rebuild, restart, migration opérateur ou déploiement n'est autorisé par ces lots.
