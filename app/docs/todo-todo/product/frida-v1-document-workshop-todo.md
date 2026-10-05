# Atelier documentaire agentique Frida V1 — spécification validée et roadmap

Date : 2026-09-29. Mise à jour M0–M2 : 2026-10-05.

Statut : **spécification et choix architecturaux validés par Tof ; M0 fermé sur
composants et preuves internes, contre-audit corrigé sur `FridaV1-Document-Workshop-M0` ;
M1 fermé sur menu, contexte `editing` et gardes, branche `FridaV1-Document-Workshop-M1` ;
M2 : succès historique 536/536 et revue G-R1–G-R4 Approved conservés ;
P2-M2-01 corrigé, comparaison 567/567 ; deux findings frontend hérités distincts
P2-M2-02/P2-M2-03 ouverts hors correctif ; livraison runtime ouverte ;
M3–M10 et Z non commencés ; préparation inactive, aucun déploiement ou renderer livré**.

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
dans M0, M1 et M2 décrivent des tests exécutés ; M3 et suivants restent des preuves futures.
Une clôture code/preuves M2 ne ferme pas migration opérateur, rebuild ou preuve DAV déployée.

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

Les contextes POST/GET sont implémentés en M1, sans progression de préparation.
Les routes remote/adopt sont implémentées et prouvées hermétiquement en M2 ;
leur livraison runtime reste ouverte. `/api/chat` avec `document_context_id`
refuse encore la préparation ; les routes d’actions restent futures.

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
Le correctif indépendant P2-M2-01 du 5 octobre passe 567/567 ; P2-M2-02/P2-M2-03
hérités restent ouverts hors de ce lot. Migration opérateur, rebuild et lecture DAV déployée
restent ouverts. M3–M10 et Z ne sont pas commencés. Spécification et
décisions amont sont validées et l'exception produit est inscrite.
Le GO de chaque lot applicatif/plateforme reste préalable à son exécution ;
les GO M0–M2 ne valent pour aucun lot suivant ni déploiement.
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

**Statut : P2-M2-01 corrigé sur code/preuves (567/567), après le succès historique
536/536 et G-R1–G-R4 Approved ; deux findings hérités P2-M2-02/P2-M2-03 ouverts
hors correctif ; livraison runtime ouverte.**
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

Deux findings hérités **restent ouverts**, sans être absorbés dans ce patch :

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
contre-audit corrigé et livré sur sa branche dédiée (`3eb2e34a`). M1 est fermé sur
menu/contexte `editing` et gardes inactifs sur sa branche issue de M0 ; livraison
Git M1 corrigée par P3 `c6f648ba`, constatée avant création de M2. M2 dispose du
succès historique 536/536 après G-R1–G-R4, dont la contre-revue du delta est
Approved ; les 528 premiers restent historiques. Le 5 octobre, P2-M2-01 est
corrigé et la comparaison passe 567/567 ; P2-M2-02/P2-M2-03 hérités restent
ouverts hors correctif. Le retour final porte la livraison Git et ses alignements. M3 et suivants restent
non commencés.
Elle complète les contrats vivants pour la nouvelle capacité bornée autorisée
dans AGENTS.md ; l'invariant de consolidation reste applicable hors de cette
exception. Les seuls composants applicatifs livrables par M0 sont les frontières
internes inactives et leurs preuves. M1 ajoute seulement entrée et contexte
`editing`, avec préparation indisponible. M2 ajoute exclusivement lecture/adoption ciblées et inventaire commun, avec
préparation toujours indisponible. Aucune dépendance nouvelle, service
plateforme ou preuve live n'est livré. La correction P3 M1 est séparée ; la
livraison M2 reste limitée à `FridaV1-Document-Workshop-M2`. Aucun merge vers main,
rebuild, restart, migration opérateur ou déploiement n'est autorisé par ces lots.
