# Atelier documentaire agentique Frida V1 — spécification validée et roadmap

Date : 2026-09-29. Mise à jour M0 : 2026-10-04.

Statut : **spécification et choix architecturaux validés par Tof ; M0 fermé sur
composants et preuves internes, contre-audit corrigé sur `FridaV1-Document-Workshop-M0` ;
M1–M10 et Z non commencés ; aucun raccord produit, déploiement ou renderer livré**.

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

Les observations techniques ci-dessous sont rattachées au HEAD
`a2483bf1aa6f5e93ba7ec2800b8ff053cc0af2c6`, branche `main`, checkout
`/opt/platform/fridadev`. Elles doivent être revalidées de façon ciblée avant
l'exécution des lots concernés, sans recommencer une reconnaissance générale.

## Lecture des cases et portes d'autorisation

Une case cochée dans les décisions signifie « décidé par Tof », pas « livré ».
Une case ouverte dans les critères ou les lots signifie « à implémenter ou prouver ».
Les inconnues factuelles sont isolées en section 11. Seules les preuves datées
dans M0 décrivent des tests exécutés ; les autres lots restent des preuves futures.

- [x] Reconnaissance et proposition de design produites dans le dialogue.
- [x] Création de cette TODO autorisée par Tof.
- [x] Spécification et choix architecturaux ci-dessous validés par Tof le 2026-09-29.
- [x] Exception produit bornée du 29 septembre 2026 inscrite dans le
  [AGENTS.md racine](../../../../AGENTS.md) pour les lots M0–M10 et Z.
- [x] M0 explicitement autorisé le 2026-10-04 sur la branche dédiée ; les GO des
  autres lots restent requis séparément.
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

**Existant :** inventaire local ; sélection lisant principalement la copie locale.

**Architecture validée :** navigation paresseuse Depth: 1 de la collection explicitement
ouverte sous Documents ; réponse/entrées bornées. Adoption après sélection,
vérification identité/ETag, récupération admissible et commit fichier/lien.
Fraîcheur vérifiée avant mobilisation documentaire ultérieure.

**Preuve à livrer :** propriétés DAV, taille des réponses, téléchargement conditionnel.

- [ ] Distinguer déjà lié, adoptable, collision locale et cible incompatible.
- [ ] Ne pas injecter automatiquement le contenu d'une ressource adoptée.
- [ ] Signaler déplacement/disparition sans recherche globale.

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

Ces interfaces sont validées dans la spécification et restent non livrées.

| Interface | Responsabilité |
| --- | --- |
| POST /api/document-workshop/contexts | Contexte borné conversation/répertoire/cible. |
| GET /api/workspace-folders/{id}/documents/remote | Collection explicitement ouverte sous Documents. |
| POST /api/workspace-folders/{id}/documents/adopt | Adoption sélectionnée ; aucune écriture distante. |
| GET /api/document-workshop/contexts/{id} | Réhydratation contexte/capacités et progression effective content-free. |
| POST /api/chat avec document_context_id | Préparation conversationnelle unique. |
| GET /api/document-workshop/actions/{id} | État public de l'action. |
| POST /api/document-workshop/actions/{id}/confirm | Claim et exécution confirmée. |
| POST /api/document-workshop/actions/{id}/cancel | Annulation de préparation ou pending ; neutralisation des résultats tardifs. |

| Cas distant | Traitement |
| --- | --- |
| Déjà lié | Retourner l'ID existant et actualiser l'observation ciblée. |
| Nouveau adoptable | Vérifier identité/ETag/taille/type/extraction, puis commit fichier/lien. |
| Collision locale | Refuser association/remplacement silencieux. |
| Incompatible | Raison précise : hors racine, collection, format, version indéterminée, autre garde. |
| Déplacé/disparu | Signaler l'écart et permettre sélection explicite, sans recherche globale. |

- [ ] Navigation Depth: 1, paresseuse et bornée ; aucun href/URL frontend directement
  exécuté comme cible DAV.
- [ ] Références opaques vérifiées côté serveur et scope Documents effectif.
- [ ] Pas de pseudo-pagination dissimulant un scan complet : DAV n'est pas supposé
  fournir une pagination universelle.
- [ ] Limite honnête si collection trop volumineuse.
- [ ] Adoption sans injection automatique ; mobilisation ultérieure explicite.

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
M1–M10 et Z restent ouverts et non commencés. Spécification et décisions amont
sont validées et l'exception produit est inscrite.
Le GO de chaque lot applicatif/plateforme reste préalable à son exécution ;
le GO M0 ne vaut pour aucun lot suivant ni déploiement.
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
claim, pending, reçu, client d'écriture ou renderer. M1 est le prochain lot,
non commencé ; les transactions/contexte appartiennent à M1–M7, la pagination
et les binaires effectivement rendus à M8–M10. Code publiable sur branche dédiée
seulement : aucun merge main, déploiement ou activation produit.

### M1 — Menu Fichier et contexte explicite

**Objectif :** entrée commune dès le début, upload préservé.
**Dépendances :** M0 pour les interfaces d'admission et de progression.
**Fichiers :** app.js, index.html, chat_active_documents.js, contrôleur atelier,
routes/contexte documentaire.
**Interface :** contexte serveur editing et menu à deux choix.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : ajout ouvre une fois le picker/upload ; atelier n'appelle ni
  modèle ni écriture DAV.
- [ ] Tests ciblés et voisins : DOM menu, active-documents, soumission canonique,
  desktop/mobile ; prouver binding réel change, pas uniquement callback isolé.
- [ ] Projeter phases/progression/annulation depuis l'état réel, sans aperçu,
  animation probante inventée ou perte du garde canonique de soumission.
- [ ] Faux verts : picker callback isolé sans listener change réel, bureau seul
  testé, ancienne action upload masquée par le menu ou second binding mobile.
- [ ] Interdire deuxième input, listener mobile concurrent, perte drag-and-drop et
  autorité d'écriture via checkbox de lecture.
- [ ] Synchroniser UX/atelier ; parcours synthétiques, aucun upload live nécessaire.
- [ ] Activation atelier différée ; aucun déploiement requis pour fermer les tests.
- [ ] Fermer lorsque les deux entrées utilisent leurs bonnes autorités et que
  l'upload conserve toutes ses capacités.

### M2 — Adoption et lecture distante ciblées

**Objectif :** intégrer un dépôt direct dans l'inventaire commun.
**Dépendances :** M0–M1, notamment gardes chemin et admission des sources.
**Fichiers :** liens Nextcloud, workspace_files_store, readers, client DAV,
service d'adoption et navigateur UI.
**Interface :** routes remote/adopt et lien identité/chemin/ETag.
**Propriétaire :** Celebrimbor ; Sauron seulement si contrat DAV manquant.

- [ ] Rouge causal : même identité → même ID ; collision → refus ; adoption → zéro
  PUT/MKCOL/DELETE.
- [ ] Tests ingestion/sélection/projections voisins ; changement listing/GET,
  identité différente avec même nom, réponse excessive et atomicité locale.
- [ ] Prouver qu'une source >20 pages n'est pas rejetée par la borne du produit ;
  appliquer le budget d'entrée complet sans troncature silencieuse.
- [ ] Faux verts : ne tester que noms identiques, ignorer ETag ou mocker un listing
  toujours petit/complet.
- [ ] Interdire scan récursif caché, polling, URL frontend exécutée et origine Frida
  attribuée à une adoption.
- [ ] Synchroniser Documents/fraîcheur ; preuve live de lecture ciblée seulement si
  autorisée, sans noms privés dans l'artefact.
- [ ] Rebuild applicatif requis pour livraison ; fermer les quatre catégories
  d'adoption et la publication locale atomique.

### M3 — Réservation durable et concurrence

**Objectif :** empêcher double génération et commit tardif.
**Dépendances :** M0–M2 ; suivi de progression de M0 et contexte de M1–M2.
**Fichiers :** claims, transport chat, finalisation et primitive transactionnelle
de snapshot.
**Interface :** turn_id, réservation propriétaire, lease technique renouvelable
et jeton de génération ; aucun TTL temporel du pending.
**Propriétaire :** Celebrimbor ; Sauron conditionnel pour environnement SQL isolé.

- [ ] Rouge causal : même tour soumis deux fois → un démarrage ; concurrent normal
  → conflit contrôlé ; ancien jeton → aucun commit.
- [ ] Tests ciblés SQL concurrents isolés ; voisins sauvegarde/erreurs/streaming.
- [ ] Faux vert : store dictionnaire verrouillé présenté comme preuve PostgreSQL.
- [ ] Interdire transaction DB durant réseau, replay automatique et modification
  du contenu des réponses normales.
- [ ] Synchroniser concurrence/états interrompus ; aucun provider live.
- [ ] Distinguer lease perdu, inactivité de préparation, annulation et invalidation
  pending ; progression continue sans expiration murale, aucun retry automatique.
- [ ] Rebuild requis à livraison ; fermer courses SQL, lease/fencing et invalidation,
  y compris pending ancien encore valide.

### M4 — Préparation Markdown dans un tour canonique

**Objectif :** vraie parole, appel documentaire unique, réponse/pending réhydratables.
**Dépendances :** M0–M3.
**Fichiers :** service de tour, agent/contrat, revisions/actions, branche chat_service,
finalisation et UI.
**Interface :** prepared/clarify/refuse et commit de fin de tour commun.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : un appel documentaire/zéro échange normal ; échec de commit
  pending → aucun succès ; refresh → même action.
- [ ] Tests final lock/persistance/stream/provenance voisins ; panne à chaque
  écriture, sortie tronquée valide et refus du fallthrough normal.
- [ ] Tests de progression et annulation réelles, attente initiale sans événement,
  données tardives après échec fermé et pending non expirant avec le temps.
- [ ] Faux verts : absence d'assertion sur appels normaux, stores finalisés séparément
  mais toujours disponibles, generator jamais réellement consommé.
- [ ] Interdire canonical dans transcript, aperçu, retry et contamination des facultés.
- [ ] Synchroniser tour/ingestion/observabilité ; modèle live sous GO distinct.
- [ ] Écriture inactive ; activation complète interdite avant M6.
- [ ] Fermer sauvegarde utilisateur initiale et transaction finale atomiques.

### M5 — Confirmation et exécution hermétiquement protégées

**Objectif :** démontrer les protections d'exécution avant raccord réel d'écriture.
**Dépendances :** M4.
**Fichiers :** executor, paths, clients DAV bornés, journal et confirmation.
**Interface :** claim confirmé et résultat typé ; services réels avec clients simulés.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : double confirmation → un PUT ; collision/chemin hostile → zéro
  mutation ; publication locale échouée → compensation conditionnelle.
- [ ] Tests compensation/ETag/upload/dossiers voisins ; headers réellement envoyés,
  collections existantes, ETag absent/changé et résultat réseau inconnu.
- [ ] Revérifier fraîcheur, ETag, scope et claim au clic, même sur un pending ancien ;
  refuser uniquement les invalidations/préconditions décidées, pas un âge limite.
- [ ] Faux verts : tester seulement le validator, omettre les headers ou toujours
  simuler succès distant/rollback réussi.
- [ ] Interdire DELETE sans propriété, rollback récursif, retry PUT incertain et
  écriture hors Documents.
- [ ] Réserver la frontière binaire : renderer fake après confirmation/claim,
  validation complète avant MKCOL/PUT ; panne/21e page/cleanup douteux → zéro mutation.
- [ ] Synchroniser matrice de panne/compensation ; aucun canari.
- [ ] Raccord client d'écriture réel interdit avant fermeture.
- [ ] Fermer toutes les frontières de panne et le retrait synchrone du bouton.

### M6 — Markdown create/copy, reçu et continuité

**Objectif :** premier parcours complet de création confirmée.
**Dépendances :** M5.
**Fichiers :** raccord Nextcloud, publication fichier/lien/révision/reçu, UI et lane.
**Interface :** action exécutée, lien produit, inventaire commun et reçu suivant.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : succès distant/échec local → aucun faux succès ; autre conversation
  → inventaire sans contenu ; confirmation répétée → aucune seconde mutation.
- [ ] Tests HTTP complet, inventaire/réhydratation/manifeste/projections voisins.
- [ ] Faux verts : tester l'executor seul, confondre ID conversation de départ et
  thread courant, vérifier présence du reçu sans vérifier sa lane.
- [ ] Interdire copie implicite, renommage après clic, reçu assistant/tool.
- [ ] Synchroniser atelier/Documents/dossiers/observabilité.
- [ ] Premier canari synthétique après fermeture hermétique et GO distinct seulement.
- [ ] Rebuild requis ; fermer concordance lien/inventaire/reçu/tour suivant.

### M7 — Update Markdown, ID stable et conflit

**Objectif :** modifier la cible explicite sans écrasement concurrent.
**Dépendances :** M6.
**Fichiers :** content service frais, executor update, liens/révisions.
**Interface :** If-Match de version préparée et même workspace_file_id.
**Propriétaire :** Celebrimbor ; Sauron conditionnel pour preuve Versions.

- [ ] Rouge causal : changement avant clic → conflit ; succès → même nom/ID.
- [ ] Tests Notes ETag/sélections voisins ; changement après prélecture, 412,
  panne DB après PUT réussi et réconciliation sans seconde écriture.
- [ ] Faux verts : ETag toujours identique ou If-Match seulement présent dans un
  objet intermédiaire, jamais dans la requête finale.
- [ ] Interdire restauration automatique, fusion, renommage ou copie de secours.
- [ ] Synchroniser update/Versions ; canari update sous GO distinct.
- [ ] Rebuild requis ; fermer identité stable, conflits et réconciliation sans PUT.

### M8-C — Contrat Writer fermé et raccord simulé

**Objectif :** rendre le service isolé implémentable et le raccord testable sans moteur live.
**Dépendances :** M0–M7 ; exception inscrite, GO de lot distinct.
**Frontières :** document_renderer_contract.py, document_canonical.py,
document_rendering.py, execution/actions et tests de contrat ; aucun fichier plateforme.
**Interface :** render_request_v1 / render_result_v1, méthodes et bornes de section 9 ;
canonical/révision/profil figés, source temporaire optionnelle, résultat fermé sans cible DAV.
**Propriétaire :** Celebrimbor ; contrat remis à Sauron sans patch de sa racine.

- [ ] Rouge causal : appel avant confirmation, canonical/hash discordants, profil inconnu,
  source/format inadmissible, pages absentes/21, partie manquante ou résultat brut → refus.
- [ ] Livrer schémas versionnés, client fake, validate_result et garde zéro mutation ;
  conserver Markdown direct et refuser les formats binaires tant que M9/M10 sont inactifs.
- [ ] Tests ciblés de contrat/action/executor, voisins M5–M7/Exports/readers ; assert
  ordre claim→render→validate→DAV et nombre d'appels, pas seulement statut HTTP.
- [ ] Faux verts : fake toujours complet, hash déclaré sans recalcul, canonical muté
  pour correspondre au résultat, résultat PDF présenté comme compte DOCX.
- [ ] Interdire provider/live renderer/Nextcloud, dépendance moteur dans FridaDev,
  socket Docker, shell libre, fallback ou modification Exports.
- [ ] Synchroniser contrat commun/profil/bornes/erreurs avec cette roadmap ; aucun
  déploiement requis pour fermer le contrat hermétique, rebuild futur du code livré.
- [ ] Fermer sur contrat consommable par M8-S et fake rejetant les contre-cas ;
  aucune installation ou preuve de disponibilité déclarée accomplie.

### M8-S — Service Writer/UNO isolé et preuve plateforme

**Objectif :** livrer un renderer privé disponible, confiné et capable de produire
la paire DOCX/PDF sous le profil décidé, sans accès au stockage.
**Dépendances :** M8-C fermé ; GO Sauron distinct pour installation/livraison et rendu synthétique.
**Frontières :** Sauron gère la sous-stack réelle `/opt/platform/fridadev-app`,
image/wrapper UNO/profil/font/socket/exploitation ; aucun patch du checkout FridaDev.
**Interface :** HTTP sur socket Unix ; UNO en pipe interne ; manifestes de capacités
et résultats selon section 9 ; aucun service existant présenté comme renderer livré.
**Propriétaire :** Sauron. Celebrimbor vérifie seulement la conformité du contrat remis.

- [ ] Rouge causal : image sans filtre/font, appelant hors permissions, second job,
  macro/lien distant, sortie partielle, 21 pages ou LibreOffice bloqué → échec fermé.
- [ ] Épingler image/digest, version LibreOffice/UNO, filtres DOCX/PDF, fichiers et
  empreintes/licences des polices, locale et profil ; aucun pin hérité implicitement de Stirling.
- [ ] Livrer utilisateur non privilégié, rootfs read-only et seules zones tmpfs/socket
  nécessaires, network_mode none, caps retirées/no-new-privileges et ressources bornées.
- [ ] Prouver socket Unix avec permissions dédiées, aucun port/routage public/UNO réseau,
  aucun secret Nextcloud/DB/provider, aucune donnée opérateur montée, aucun Docker socket.
- [ ] Une tâche active, zéro file d'attente ; saturation rejetée. Profil UNO temporaire
  distinct, processus suivi/destructible et nettoyage succès/erreur/annulation/crash.
- [ ] Tests synthétiques réels : Unicode, chaque style, tables multipages, sauts,
  A4/12 points/1,5/2,5 cm ; rechargement DOCX et export PDF du même état Writer.
- [ ] Prouver nombre de pages Writer stabilisé et concordance PDF, filtres réellement
  présents, refus 21e page, aucune macro/update distant/extension ou dialogue bloquant.
- [ ] Tests adverses de transport/archive/ressources/kill et seconde requête ; voisins
  FridaDev/Nextcloud/Stirling uniquement status-only, pas de document privé.
- [ ] Faux verts : binaire présent, headless sans layout évalué, DOCX ouvrable, font de
  l'hôte, keepalive pris pour progrès, rootfs ro sans preuve du profil writable.
- [ ] Interdire Caddy/Authelia/UI, cloud/payante, accès Nextcloud, fallback Stirling,
  nouveau moteur, données réelles ou canari d'écriture.
- [ ] Synchroniser runbook plateforme et preuve datée content-free ; rebuild du seul
  service renderer autorisé dans ce futur lot, aucun restart voisin automatique.
- [ ] Fermer sur capacités réelles, sécurité/ressources/cleanup et artefact synthétique
  accepté par le contrat M8-C ; ne pas attendre M9 pour prouver le moteur.

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

### 9.2. Forme minimale compatible avec le serveur observé

Service séparé à livrer par Sauron dans la sous-stack réelle FridaDev-app, avec
image/worker distincts de `platform-fridadev`. Nom de service, chemin de socket et
UID/GID seront des identifiants de livraison, pas des services prétendument présents.
Un répertoire de socket dédié, accessible aux seuls comptes FridaDev/renderer,
est monté dans les deux conteneurs ; aucun document, state/, secret, DB, volume
Nextcloud ou socket Docker n'est partagé. FridaDev utilise un client HTTP AF_UNIX
étroit de bibliothèque standard ; aucune dépendance bureautique dans son image.

Le wrapper écoute seulement sur ce socket Unix et pilote UNO sur un pipe local
au conteneur. Renderer en `network_mode: none` : aucune route entrante publique,
aucun port publié, Caddy/Authelia/UI, DNS ou réseau Nextcloud. Les réseaux partagés
observés ne sont pas réutilisés pour ce service. Les permissions du socket et
l'isolement effectif sont prouvés en M8-S ; aucune hypothèse de sécurité fondée
sur le seul mot « interne ». HTTP réseau privé ajouterait une frontière réseau
inutile sur ce même hôte ; CLI/SSH/Docker exec depuis FridaDev donneraient des
capacités d'exécution/plateforme disproportionnées. Aucun de ces chemins n'est livré.

Sauron réalise les fichiers image/wrapper/runtime dans sa racine uniquement.
Celebrimbor réalise protocole/adaptateur/orchestration dans le checkout uniquement.
Aucune modification de stack dans ce correctif ; la future connexion du socket
peut imposer une recréation ciblée FridaDev gérée par Sauron, pas un restart global.

### 9.3. Protocole fermé et bornes techniques

Schémas fermés versionnés, champs inconnus refusés. Interfaces internes seulement :

| Méthode | Effet |
| --- | --- |
| GET /v1/capabilities | Version du contrat/image/Writer/UNO, filtres, profil/polices et limites ; aucun contenu ni secret. |
| POST /v1/jobs | render_request_v1 : job_id, revision_id/hash, profil épinglé, format DOCX ou PDF, canonical validé, source_kind et octets/hash optionnels. Claim Frida confirmé requis côté orchestrateur. |
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
ni pulse, poll, CPU consommé, animation ni lease ne réarment ce compteur. Frida
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

Même job_id et même hash : lecture de l'état/résultat, aucune seconde exécution ;
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
d'ONLYOFFICE, cloud, second moteur et fallback sont exclus. Les contraintes suivantes sont
prescrites, non encore implémentées :

- [ ] Créer un modèle Writer contrôlé via UNO depuis le canonical : titres,
  paragraphes, gras/italique, listes, citations, liens passifs, tableaux simples
  et sauts de page ; aucune image ni contenu actif.
- [ ] Épingler image/digest/version LibreOffice/UNO et disponibilité des filtres
  `Office Open XML Text` pour DOCX et `writer_pdf_Export` pour PDF. Aucun filtre
  commandé par le modèle ou document ; pas de conversion CLI nominale seule.
- [ ] Épingler fichiers/polices normales/gras/italiques, licences, empreintes, locale,
  profil A4/12 points/interligne 1,5/marges 2,5 cm ; absence de glyphes/font → refus.
- [ ] Enregistrer DOCX, le recharger dans le même Writer sans mutation de son contenu
  ou profil, forcer/stabiliser le layout et relever ses pages. Exporter le PDF
  depuis ce même état rechargé ; vérifier compte PDF final et concordance Writer.
  Une paire de validation interne ne crée pas deux fichiers produit : seul le
  format confirmé est publié dans Nextcloud.
- [ ] Prouver l'API de layout effectivement opérante en headless (p. ex. curseur de
  pages UNO après layout), pas un champ docProps ou un compteur de sauts déclaré.
  Export partiel, désaccord de pages, plus de 20 pages ou layout non établi : refus.
- [ ] Le nombre de pages contractuel est celui de ce Writer épinglé, avec ces polices ;
  aucune identité mathématique universelle avec Microsoft Word n'est revendiquée.
- [ ] Canonical Frida seule source structurée durable ; DOCX/PDF liés à sa révision
  et au manifeste de rendu. ODT éventuel strictement temporaire dans le job, jamais
  adopté, inventorié ou promu en deuxième vérité.
- [ ] Tests synthétiques Unicode français/styles/tableaux/sauts/pagination, stabilité
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

### 9.6. Confinement et exploitation à prouver

- [ ] Utilisateur non privilégié, rootfs read-only compatible ; tmpfs writable
  uniquement pour travail/tmp/profil, répertoire de socket séparé ; aucune
  lecture arbitraire du filesystem, mount opérateur ou capability de commande.
- [ ] Démarrage fixed argv headless/norestore avec UserInstallation éphémère par
  exécution ; UNO acceptor en pipe interne ; aucune option fournie par l'appelant.
- [ ] Macros `NEVER_EXECUTE`, liens `NO_UPDATE`, interaction handler refusant demandes
  de chargement/mot de passe/réparation, extensions non nécessaires absentes ;
  network none et tests de non-chargement remote, pas confiance dans Hidden seul.
- [ ] Profil utilisateur séparé pour chaque job, fermeture/dispose document, destruction
  processus bloqué et nettoyage enfin garanti, y compris crash/OOM/redémarrage.
- [ ] Tests source hostile et extraction ZIP bornée, traversée interne/symlink,
  chargements locaux externes, pertes de contenu, concurrence et saturation.
- [ ] Aucun contenu brut, nom privé, source binaire, URL sensible ou exception brute
  dans logs/health/rapports ; seules versions, tailles, phases et reason codes.
- [ ] Health/capabilities sans ouverture de document ; preuve synthétique de rendu
  séparée et autorisée. Disponibilité du service et qualité de layout sont deux preuves.

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
- [Curseur de pages Writer](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1text_1_1XPageCursor.html) : API de pages, dont l'utilisation effective headless reste à prouver.
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
- document_renderer_contract.py : schémas fermés du service privé et capacités.
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

- [ ] M8-S : service Writer/UNO isolé, image/filtres/polices/profil/ressources/socket,
  sécurité/cleanup/health et preuve synthétique ; voir section 8, aucune livraison ici.
- [ ] Prouver identité DAV, préconditions, ETags et Versions si les preuves
  applicatives ne suffisent pas.
- [ ] Fournir une preuve transactionnelle isolée si environnement SQL absent.

M8-S est une vraie frontière plateforme, sans accès Nextcloud et sans surface
publique. Permissions DAV ou environnement SQL partagé relèvent de besoins
Sauron conditionnels distincts. Pins/bibliothèques/polices sont dans l'image du
renderer, pas dans FridaDev. Sauron ne modifie pas ce checkout ; Celebrimbor ne
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
contre-audit corrigé sur sa branche dédiée ; sa livraison Git est obligatoire,
à constater dans le retour de lot. M1 reste non commencé.
Elle complète les contrats vivants pour la nouvelle capacité bornée autorisée
dans AGENTS.md ; l'invariant de consolidation reste applicable hors de cette
exception. Les seuls composants applicatifs livrables par M0 sont les frontières
internes inactives et leurs preuves. Aucune dépendance, service ou preuve live
n'est livré. Commit/push requis exclusivement sur `FridaV1-Document-Workshop-M0` ;
aucun merge vers main, rebuild, restart ou déploiement n'est autorisé.
