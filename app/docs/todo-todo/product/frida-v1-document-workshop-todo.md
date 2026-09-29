# Atelier documentaire agentique Frida V1 — spécification proposée et roadmap

Date : 2026-09-29.

Statut : **proposition à valider par Tof ; aucun lot applicatif commencé**.

Provenance : reconnaissance architecturale puis design consolidé dans le même
dialogue avec Tof. La création de ce fichier TODO est explicitement autorisée ;
elle ne vaut pas validation de la spécification ni GO d'implémentation.

Les observations techniques ci-dessous sont rattachées au HEAD
`a2483bf1aa6f5e93ba7ec2800b8ff053cc0af2c6`, branche `main`, checkout
`/opt/platform/fridadev`. Elles doivent être revalidées de façon ciblée avant
l'exécution des lots concernés, sans recommencer une reconnaissance générale.

## Lecture des cases et portes d'autorisation

Une case cochée dans les décisions signifie « décidé par Tof », pas « livré ».
Une case ouverte dans les critères ou les lots signifie « à valider, qualifier
ou implémenter ». Les tests décrits sont des preuves futures, pas des tests déjà
exécutés pour cet atelier.

- [x] Reconnaissance et proposition de design produites dans le dialogue.
- [x] Création de cette TODO autorisée par Tof.
- [ ] Spécification et choix architecturaux ci-dessous validés par Tof.
- [ ] Exception documentaire bornée inscrite dans le [AGENTS.md racine](../../../../AGENTS.md)
  dans un lot explicitement autorisé, avant tout patch applicatif.
- [ ] Lot d'implémentation concerné explicitement autorisé.
- [ ] GO distinct obtenu avant tout appel modèle réel de qualification.
- [ ] GO distinct obtenu avant tout canari d'écriture Nextcloud.

Le présent lot est docs-only. Il ne modifie ni application, ni tests, ni schéma,
ni AGENTS.md, ni runtime. Aucun provider, accès à des contenus privés, mutation
DB/WebDAV, installation, build ou déploiement n'est nécessaire à sa création.

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
- [x] Modèle principal actuellement configuré, prompt documentaire distinct, un
  appel documentaire par préparation, aucun fallback ni nouveau réglage Admin.
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
« modèle/stratégie agentique » sont fermés par ce design. Les propositions
techniques ci-dessous restent à valider avec la spécification.

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
Elles ne prouvent pas les capacités futures décrites ici. La disponibilité
observée de Stirling/LibreOffice ne prouve pas son contrat de conversion ;
doc-pipeline n'est pas une API de composition documentaire qualifiée.

## 3. Spécification proposée

Chaque rubrique distingue décision, existant, proposition et qualification.
Les cases ouvertes sont des critères futurs ; aucun n'est déclaré livré.

### 3.1. Finalité et non-objectifs

**Décision :** préparer puis créer/modifier des documents dans Documents et
poursuivre ce travail dans la conversation.

**Existant :** Documents, Notes, Exports et Images ont des responsabilités propres.

**Proposition :** l'atelier possède préparation et exécution ; Notes conserve
l'append, Exports les snapshots. Pas de synchronisation globale, fusion concurrente,
images incorporées, continuation automatique ou tools principaux au premier palier.

**Qualification :** aucune inconnue de finalité produit.

- [ ] Préserver les responsabilités voisines dans les parcours et tests.

### 3.2. Vocabulaire

**Décision :** document distinct de la réponse, provenance durable.

**Existant :** workspace_file représente un fichier inventorié, pas son brouillon
ou sa confirmation.

**Proposition :**

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

**Qualification :** aucune.

- [ ] Utiliser ce vocabulaire dans schémas, projections et contrats.

### 3.3. UX et autorités

**Décision :** menu Fichier à deux choix ; lecture distincte de l'autorité d'écriture.

**Existant :** bouton relié directement au picker et sélections persistantes.

**Proposition :** un seul listener Fichier ; contexte serveur lié à conversation,
répertoire et cible éventuelle. Le contexte autorise la préparation ; seul le clic
de confirmation autorise la mutation.

**Qualification :** aucune nouvelle autorité produit.

- [ ] Conserver même DOM, contrôleur et callbacks sur desktop/mobile.
- [ ] Garder une sélection de source distincte d'une cible d'update.

### 3.4. Préparation conversationnelle

**Décision :** vraie parole utilisateur, réponse courte et pending durable.

**Existant :** soumission canonique et sauvegarde des messages/meta, sans transaction
commune avec une action documentaire.

**Proposition :** /api/chat unique, branche explicite, réservation avant appel,
sauvegarde utilisateur initiale, commit réponse/pending commun. Séquence en section 4.

**Qualification :** preuve de concurrence SQL réelle isolée.

- [ ] Garantir zéro échange principal normal après sélection de la branche atelier.
- [ ] Réhydrater un tour échoué sans inventer une réponse ou un succès.

### 3.5. Agent documentaire

**Décision :** modèle principal configuré, prompt distinct, un appel documentaire,
aucun fallback et aucun réglage Admin nouveau.

**Existant :** modèle et budget résolus depuis les réglages runtime ; lecteur
non streaming centré sur le texte extrait.

**Proposition :** entrées typées : demande/tour, contexte dialogique partagé,
répertoire autorisé, références explicites, sources et versions, capacités/budgets.
Sortie stricte prepared, clarify ou refuse. Prepared contient réponse courte,
opération, cible, canonical et limites ; les deux autres n'ont aucune action
exécutable. Le modèle ne possède aucun client d'écriture.

**Qualification :** limites du modèle, raisonnement, fin de génération et transport.

- [ ] Valider l'enveloppe sans routage linguistique déterministe.
- [ ] Ne jamais relancer le modèle pour réparer automatiquement une sortie invalide.

### 3.6. Données et migrations

**Décision :** inventaire commun, canonical, confirmation unique et reçu durable.

**Existant :** message.meta existe ; identité DB des messages par conversation/seq ;
liens Nextcloud sans contrat complet de chemin relatif/ETag.

**Proposition :**

| Ensemble | Responsabilité proposée |
| --- | --- |
| workspace_files | Inventaire unique ; auteur/source typés ; ID stable en update. |
| workspace_file_nextcloud_links | Extension du lien : chemin relatif complet, identité, ETag, observation/fraîcheur. |
| document_artifacts | Identité documentaire, fichier lié après exécution et révision courante validée. |
| document_revisions | Canonical immutable, schéma, empreinte, rendu figé, empreinte/version renderer et correspondance distante. |
| document_actions | Contexte, proposition, sources/tour, expiration, confirmation, état et journal. |
| document_receipts | Résultat immutable, demande/confirmation, version et lien produit. |
| conversation_turn_claims | Réservation durable d'un tour ou d'une confirmation, propriétaire et jeton de génération. |

**Qualification :** identité DAV et environnement SQL de preuve.

- [ ] Unicité des tours clients et d'une réservation active par conversation.
- [ ] Au plus un reçu de succès par action et une identité distante par répertoire.
- [ ] Révisions immutables ; drafts absents de l'inventaire public.
- [ ] Migration ciblée des anciens liens seulement lorsque leur chemin est prouvé.
- [ ] Référencer le tour utilisateur stable dans meta, sans dépendre du seul seq.

### 3.7. Confirmation, expiration et idempotence

**Décision :** bouton éphémère, aucune double écriture.

**Existant :** Agenda fournit des concepts mais pas le claim documentaire durable
et atomique requis.

**Proposition :** editing → preparing → pending → executing → succeeded ; sorties
expired, cancelled, superseded, failed ou remote_uncertain. Expiration proposée de
30 minutes, fondée sur le précédent Agenda, à valider avec la spécification.
Le claim compare état, expiration, propriétaire, conversation, répertoire, jeton
et préconditions. Une répétition retourne l'état sans relancer modèle ou PUT.

**Qualification :** exclusion SQL et crashs DB/WebDAV.

- [ ] Ne jamais rendre automatiquement pending une exécution incertaine.
- [ ] Refuser résultats tardifs et ancienne génération.
- [ ] Invalider les contextes/pending lors d'un changement de répertoire pertinent.

### 3.8. Chemins et collections

**Décision :** créations et collections exclusivement sous Documents ; segments
manquants affichés confirmés avec le fichier.

**Existant :** sanitizers de noms insuffisants pour valider un chemin complet.

**Proposition :** resolver serveur segment par segment ; refus chemins absolus,
traversées, séparateurs déguisés, contrôles, normalisation ambiguë et sortie de
racine. Bornes proposées : huit sous-répertoires, 180 points de code et 255 octets
UTF-8 par segment, 1024 octets pour le chemin relatif complet. Chemin affiché,
normalisation et clés de collision sont figés avant confirmation.

**Qualification :** compatibilité de ces bornes avec la cible WebDAV.

- [ ] Vérifier no-clobber local et distant ; ne jamais corriger le chemin au clic.
- [ ] Créer seulement les collections bornées prévues, vérifier les collections
  existantes et signaler celles laissées vides après échec.
- [ ] Ne jamais supprimer récursivement les collections.

### 3.9. Nextcloud-first et compensations

**Décision :** mutation distante avant publication locale ; collections vides
possibles et signalées.

**Existant :** upload Nextcloud-first et compensation ETag, mais plusieurs
transactions locales.

**Proposition :** journaliser l'intention avant mutation ; après succès distant,
publier fichier/lien, révision, reçu et état final dans une transaction commune.
Compensation create uniquement avec propriété et ETag fort identique. Aucune
réécriture compensatoire automatique pour update ; Versions reste l'autorité.

**Qualification :** fenêtres de panne ; aucune atomicité distribuée supposée.

- [ ] Journal durable avant PUT/MKCOL ; pas de publication locale prématurée.
- [ ] Sans preuve de propriété, ne pas supprimer et conserver un état honnête.
- [ ] Réconcilier les métadonnées sans rejouer un PUT incertain.

### 3.10. Lecture, adoption et fraîcheur

**Décision :** adoption ciblée obligatoire, aucun scan global.

**Existant :** inventaire local ; sélection lisant principalement la copie locale.

**Proposition :** navigation paresseuse Depth: 1 de la collection explicitement
ouverte sous Documents ; réponse/entrées bornées. Adoption après sélection,
vérification identité/ETag, récupération admissible et commit fichier/lien.
Fraîcheur vérifiée avant mobilisation documentaire ultérieure.

**Qualification :** propriétés DAV, taille des réponses, téléchargement conditionnel.

- [ ] Distinguer déjà lié, adoptable, collision locale et cible incompatible.
- [ ] Ne pas injecter automatiquement le contenu d'une ressource adoptée.
- [ ] Signaler déplacement/disparition sans recherche globale.

### 3.11. Update, ETag et Versions

**Décision :** même cible/nom/ID ; conflit sans écrasement ; Versions fait autorité.

**Existant :** Notes utilise GET frais/If-Match ; cela ne remplace pas la comparaison
avec la version préparée.

**Proposition :** ETag/empreinte figés à la préparation ; lecture fraîche et identité
vérifiées juste avant PUT If-Match exact. Différence ou 412 termine en conflit.

**Qualification :** Versions et préconditions effectives sur la chaîne déployée.

- [ ] Aucun update sans version établie.
- [ ] Aucune fusion, copie, renommage ou nouvelle préparation automatique.
- [ ] Préserver le même workspace_file_id après succès.

### 3.12. Canonical et rendus

**Décision :** profil fixé, aucune image, DOCX/PDF Frida issus du canonical.

**Existant :** renderer Exports minimal, profil complet non couvert.

**Proposition :** titres, paragraphes, spans, listes, citations, liens, tableaux
simples et sauts de page ; refus images, HTML actif, macros et références
exécutables. Rendu préparé/figé avant action confirmable ; le clic écrit ces octets.
Pagination/marges pour DOCX/PDF ; marqueur documenté pour sauts de page Markdown,
dont la pagination dépend du lecteur.

**Qualification :** un seul moteur retenu après comparaison, section 9.

- [ ] Même révision pour canonical, rendu, empreintes et version renderer.
- [ ] Update Frida DOCX/PDF seulement si leur correspondance distante est établie.
- [ ] DOCX externe : limites détectées affichées ; clarification/refus si incompatibles.
- [ ] PDF externe : nouveau document proposé, pas d'update aveugle.

### 3.13. Provenance et réhydratation

**Décision :** reçu durable, demande réelle et confirmation humaine établies.

**Existant :** meta réhydratable ; aucun reçu documentaire typé.

**Proposition :** reçu avec action/artefact/fichier/révision, conversation/répertoire,
nom/format/chemin, auteur de création et de révision, référence stable de demande,
confirmation, date, ETag/version, empreintes et lien produit. Un adopté garde son
origine externe même après révision Frida.

**Qualification :** aucune inconnue produit.

- [ ] Réhydratation après réouverture et lien produit fonctionnel.
- [ ] Référence de demande indépendante du seul seq.
- [ ] Reçu de succès uniquement après publication locale complète.

### 3.14. Injection et non-contamination

**Décision :** métadonnées au tour suivant ; contenu par référence explicite.

**Existant :** facultés et fenêtre dialogique consomment les vraies paroles ; lanes
tardives et manifeste du payload principal disponibles.

**Proposition :** lane de reçus produite à la volée après construction des entrées
des facultés ; jamais enregistrée comme message. Dernier reçu pertinent présent
au tour suivant, historique supplémentaire borné. La vraie demande et la réponse
courte restent dans le dialogue légitime.

**Qualification :** budget de lane et preuves de séparation des payloads.

- [ ] Aucun canonical, rendu, journal ou reçu synthétique dans Memory, Identity,
  Summary, Biblio ou Stimmung.
- [ ] Autre conversation : inventaire visible, contenu non injecté automatiquement.
- [ ] Manifeste de provenance content-free cohérent avec cette lane.

### 3.15. Observabilité

**Décision :** demande et confirmation établies sans contenu brut observable.

**Existant :** allowlists/projections content-free disponibles.

**Proposition :** événements préparation, rejet, claim, expiration, conflit,
écriture, compensation, incertitude et reçu ; seulement IDs, états, codes, tailles,
comptes, durées, empreintes et versions techniques. Projection produit autorisée
distincte pour nom et chemin.

**Qualification :** tous les sinks, manifestes et projections admin.

- [ ] Aucun texte utilisateur/canonical, nom privé, chemin brut, URL distante ou
  exception de transport brute dans logs, JSONL et projections content-free.

### 3.16. Sécurité et refus

**Décision :** pas de mutation ambiguë ou de fidélité dissimulée.

**Existant :** lecteurs textuels avec limites ; copies locales potentiellement périmées.

**Proposition :** refus avant pending exécutable pour cible hors scope, version
indéterminée, archive inadmissible, extraction incomplète, dépassement, sortie
tronquée, canonical invalide ou rendu incomplet. Contenus documentaires non fiables
et sans autorité ; renderer sans récupération des liens.

**Qualification :** expansion d'archives, tailles, deadlines et corpus de refus.

- [ ] Gardes appliqués avant mutation, même contre requête HTTP construite hors UI.
- [ ] Aucun appel OCR implicite ou perte de contenu silencieuse ajoutée par l'atelier.

### 3.17. Tests et preuves live

**Décision :** aucun canari d'écriture avant gardes, claim et compensations.

**Existant :** preuves de briques acquises ; workflow futur non prouvé.

**Proposition :** TDD causal par capacité, voisins et injections de panne ; preuve
SQL isolée pour concurrence ; corpus synthétiques pour rendus. Appel modèle réel
et canari Nextcloud chacun sous GO distinct, preuves datées/content-free.

**Qualification :** environnement isolé pour transactions et rendus.

- [ ] Ne pas fermer un invariant réel avec une preuve uniquement mockée.
- [ ] Ne pas présenter les tests projetés comme exécutés.

### 3.18. Responsabilités

**Décision :** application Celebrimbor, plateforme Sauron.

**Existant :** Stirling/LibreOffice disponible sans contrat requis qualifié ;
doc-pipeline sans capacité de composition qualifiée.

**Proposition :** services/UI/données/render applicatif/tests/observabilité à
Celebrimbor ; contrats/services/ressources/permissions partagés à Sauron.

**Qualification :** besoin Sauron selon preuves DAV et choix renderer.

- [ ] Aucun changement de plateforme par proximité ou contournement applicatif.

### 3.19. Achèvement et non-prolongation

**Décision :** atelier spécialisé et fondation tool-ready.

**Existant :** aucune boucle tools principale à étendre.

**Proposition :** clôture sur create/adoption/read/copy/update, trois formats,
confirmation, conflits, continuité et voisins préservés. Appel de service sans DOM
pour prouver tool-ready, sans implémenter de tool principal. Images, continuation
de documents longs et édition enrichie nécessiteraient d'autres projets.

**Qualification :** aucune extension indispensable à la fermeture.

- [ ] Fermer par les critères du lot Z ; ne pas convertir les suites hors scope en
  condition permanente de clôture.

## 4. Raccordement conversationnel exact — L1

### Choix recommandé

| Raccord réaliste | Évaluation |
| --- | --- |
| Chat normal puis préparation | Écarté : double génération principale et réponse normale sans rôle clair. |
| Route et transcript documentaires indépendants | Écarté : duplication de sauvegarde/finalisation et risque de contourner les facultés. |
| /api/chat unique avec branche documentaire explicite | Retenu comme proposition : transport/transcript réutilisés, échange principal normal remplacé. |

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
- [ ] Valider enveloppe, sources, opération, chemin, canonical, limites et rendu.
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
garde peut utiliser final_lock. Commit documentaire avant ouverture du flux.

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
| Préparation | Garde de soumission, aucune confirmation disponible. |
| Pending | Carte compacte sans aperçu complet. |
| Confirmation engagée | Bouton retiré synchroniquement, état bref. |
| Résultat | Lien, conflit, expiration ou erreur honnête. |

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

## 6. Adoption et routes proposées — L3

Ces routes ne sont pas livrées ; leurs noms restent des interfaces proposées.

| Interface | Responsabilité |
| --- | --- |
| POST /api/document-workshop/contexts | Contexte borné conversation/répertoire/cible. |
| GET /api/workspace-folders/{id}/documents/remote | Collection explicitement ouverte sous Documents. |
| POST /api/workspace-folders/{id}/documents/adopt | Adoption sélectionnée ; aucune écriture distante. |
| GET /api/document-workshop/contexts/{id} | Réhydratation contexte/capacités. |
| POST /api/chat avec document_context_id | Préparation conversationnelle unique. |
| GET /api/document-workshop/actions/{id} | État public de l'action. |
| POST /api/document-workshop/actions/{id}/confirm | Claim et exécution confirmée. |
| POST /api/document-workshop/actions/{id}/cancel | Annulation encore pending. |

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

## 7. Bornes rectifiées — L4

La combinaison « 16000 tokens / 120000 caractères générés » est retirée.

Faits : défaut response_max_tokens = 8192 ; FRIDA_MAX_TOKENS = 35000 est une
estimation souple ; compteur heuristique sans rapport garanti tokens/caractères.
Ces défauts ne prouvent pas les valeurs runtime actuelles ou les limites du modèle.

### Contrat d'admission proposé

Avec T = plafond de sortie documentaire, W = fenêtre qualifiée, I = entrée complète,
M = réserve qualifiée, Cmax = caractères canoniques et Bmax = octets de l'enveloppe :

```text
T = min(response_max_tokens runtime, 8192, plafond de sortie qualifié du modèle)
I + T + M <= W
```

Le cap initial 8192 est une restriction proposée fondée sur le défaut existant.
I comprend prompt, dialogue, sources et enveloppes. La qualification établit la
place du raisonnement dans ces limites.

Aucune égalité C = k × T n'est promise. Le canonical et son enveloppe partagent la
sortie. Acceptation simultanée : génération complète, schéma valide, Cmax/Bmax
respectés et limites du contrat token qualifié.

- [ ] Fixer Cmax, Bmax, M et plafond d'entrée en M0 sur modèle effectif, tokenisation
  et corpus synthétiques ; aucune valeur numérique inventée ici.
- [ ] Conserver finish_reason et métadonnées utiles dans l'adapter documentaire.
- [ ] Refuser finish_reason=length ou enveloppe incohérente même si JSON valide.
- [ ] Refuser canonical excessif sans troncature.
- [ ] Refuser source trop longue avant appel, sans extrait silencieux.
- [ ] Refuser admission documentaire trop longue sans raccourcir arbitrairement la
  fenêtre du dialogue normal.
- [ ] Modèle nouveau non qualifié : atelier indisponible, aucun fallback.
- [ ] Aucun chunking, continuation ou réparation par second appel caché.

## 8. Roadmap par micro-lots

Tous les lots restent ouverts. La séquence est proposée ; la validation et les
portes d'autorisation de début de fichier sont préalables à son exécution.
UI construite tôt, contrats DOM/HTTP hermétiques ; aucun parcours d'écriture exposé
comme fonctionnel avant livraison des protections et de la tranche complète.

### M0 — Contrat autorisé et budgets qualifiés

**Objectif :** profil d'admission exploitable avant tout appel documentaire.
**Dépendances :** validation et autorisation préalables ; prerequisite des autres lots.
**Frontières :** réglages principaux, llm_client, compteur, contrat documentaire.
**Interface :** profil interne lié au modèle, sans nouveau réglage Admin.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : entrée excessive, modèle non qualifié, fin tronquée avec JSON
  syntaxiquement valide doivent être refusés.
- [ ] Tests ciblés : corpus synthétiques et contrat d'admission ; voisins réglages/
  raisonnement/parser existants.
- [ ] Faux verts : confondre défaut et valeur effective, heuristique et tokenizer,
  tokens visibles et raisonnement.
- [ ] Interdire provider réel, fallback et changements de plafonds du chat normal.
- [ ] Documenter valeurs, méthode et refus ; appel réel éventuel sous GO distinct.
- [ ] Aucun déploiement produit ; fermer avec budgets et transport borné vérifiables.

### M1 — Menu Fichier et contexte explicite

**Objectif :** entrée commune dès le début, upload préservé.
**Dépendances :** M0 pour le contrat.
**Fichiers :** app.js, index.html, chat_active_documents.js, contrôleur atelier,
routes/contexte documentaire.
**Interface :** contexte serveur editing et menu à deux choix.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : ajout ouvre une fois le picker/upload ; atelier n'appelle ni
  modèle ni écriture DAV.
- [ ] Tests ciblés et voisins : DOM menu, active-documents, soumission canonique,
  desktop/mobile ; prouver binding réel change, pas uniquement callback isolé.
- [ ] Interdire deuxième input, listener mobile concurrent, perte drag-and-drop et
  autorité d'écriture via checkbox de lecture.
- [ ] Synchroniser UX/atelier ; parcours synthétiques, aucun upload live nécessaire.
- [ ] Activation atelier différée ; aucun déploiement requis pour fermer les tests.
- [ ] Fermer lorsque les deux entrées utilisent leurs bonnes autorités et que
  l'upload conserve toutes ses capacités.

### M2 — Adoption et lecture distante ciblées

**Objectif :** intégrer un dépôt direct dans l'inventaire commun.
**Dépendances :** M1.
**Fichiers :** liens Nextcloud, workspace_files_store, readers, client DAV,
service d'adoption et navigateur UI.
**Interface :** routes remote/adopt et lien identité/chemin/ETag.
**Propriétaire :** Celebrimbor ; Sauron seulement si contrat DAV manquant.

- [ ] Rouge causal : même identité → même ID ; collision → refus ; adoption → zéro
  PUT/MKCOL/DELETE.
- [ ] Tests ingestion/sélection/projections voisins ; changement listing/GET,
  identité différente avec même nom, réponse excessive et atomicité locale.
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
**Dépendances :** M1–M2.
**Fichiers :** claims, transport chat, finalisation et primitive transactionnelle
de snapshot.
**Interface :** turn_id, réservation propriétaire et jeton de génération.
**Propriétaire :** Celebrimbor ; Sauron conditionnel pour environnement SQL isolé.

- [ ] Rouge causal : même tour soumis deux fois → un démarrage ; concurrent normal
  → conflit contrôlé ; ancien jeton → aucun commit.
- [ ] Tests ciblés SQL concurrents isolés ; voisins sauvegarde/erreurs/streaming.
- [ ] Faux vert : store dictionnaire verrouillé présenté comme preuve PostgreSQL.
- [ ] Interdire transaction DB durant réseau, replay automatique et modification
  du contenu des réponses normales.
- [ ] Synchroniser concurrence/états interrompus ; aucun provider live.
- [ ] Rebuild requis à livraison ; fermer courses SQL, expiration et invalidation.

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
- [ ] Faux verts : absence d'assertion sur appels normaux, stores finalisés séparément
  mais toujours disponibles, generator jamais réellement consommé.
- [ ] Interdire canonical dans transcript, aperçu, retry et contamination des facultés.
- [ ] Synchroniser tour/ingestion/observabilité ; modèle live sous GO distinct.
- [ ] Écriture inactive ; activation complète interdite avant M6.
- [ ] Fermer sauvegarde utilisateur initiale et transaction finale atomiques.

### M5 — Confirmation et exécution hermétiquement protégées

**Objectif :** démontrer le moteur avant raccord réel d'écriture.
**Dépendances :** M4.
**Fichiers :** executor, paths, clients DAV bornés, journal et confirmation.
**Interface :** claim confirmé et résultat typé ; services réels avec clients simulés.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : double confirmation → un PUT ; collision/chemin hostile → zéro
  mutation ; publication locale échouée → compensation conditionnelle.
- [ ] Tests compensation/ETag/upload/dossiers voisins ; headers réellement envoyés,
  collections existantes, ETag absent/changé et résultat réseau inconnu.
- [ ] Faux verts : tester seulement le validator, omettre les headers ou toujours
  simuler succès distant/rollback réussi.
- [ ] Interdire DELETE sans propriété, rollback récursif, retry PUT incertain et
  écriture hors Documents.
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

### M8 — Qualification bornée du renderer

**Objectif :** choisir un seul chemin couvrant le profil fixé.
**Dépendances :** canonical stable de M4 ; séquencé après le premier parcours Markdown.
**Frontières :** renderer Exports, canonical, candidate dédiée, capacité plateforme.
**Interface :** canonical → rendered_revision.
**Propriétaire :** Celebrimbor ; Sauron pour candidate plateforme.

- [ ] Rouge causal : renderer actuel insuffisant au profil ; corpus Unicode/styles/
  tableaux multipages/isolation.
- [ ] Tests génération Exports voisins ; contrôler structure et rendu, pas seulement
  texte extrait, ouverture DOCX ou apparence sur une machine avec fonts implicites.
- [ ] Interdire choix/dépendance avant preuve, provider, plateforme sans contrat,
  second moteur de secours et changement du domaine Exports.
- [ ] Synchroniser rapport synthétique et décision technique ; critères section 9.
- [ ] Aucun déploiement produit ; fermer sur un seul chemin, limites et coûts établis.

### M9 — DOCX Frida et retravail externe

**Objectif :** create/update DOCX et retravail externe honnête.
**Dépendances :** M7–M8.
**Fichiers :** moteur retenu, reader DOCX, révisions et projection des limites.
**Interface :** rendu lié au canonical et update à identité stable.
**Propriétaire :** Celebrimbor ; Sauron conditionnel.

- [ ] Rouge causal : mismatch canonical/rendu → refus ; externe complexe → limite
  ou refus ; update → même ID.
- [ ] Tests OOXML/styles/listes/tableaux/liens/pages et voisins extraction/Exports ;
  archives excessives, relations externes et pertes détectables.
- [ ] Faux vert : valider uniquement le texte extrait ou l'ouverture du ZIP.
- [ ] Interdire fidélité arbitraire promise, images incorporées et ownership Exports.
- [ ] Synchroniser formats/fidélité ; preuve synthétique live sous autorisation.
- [ ] Rebuild requis ; fermer profil DOCX et correspondance canonique.

### M10 — PDF Frida et PDF externe comme source

**Objectif :** rendu PDF ; update uniquement si canonical correspondant établi.
**Dépendances :** M9.
**Fichiers :** renderer PDF, reader, politique de cible et mapping des révisions.
**Interface :** PDF Frida lié ; PDF externe vers proposition de nouveau document.
**Propriétaire :** Celebrimbor ; Sauron conditionnel.

- [ ] Rouge causal : externe à modifier → nouveau document ; Frida désynchronisé
  → aucun update aveugle.
- [ ] Tests Unicode/visuel/fonts/pagination/tableaux/liens, PDF chiffré/scanné,
  canonical absent et octets distants changés ; voisins readers/Exports.
- [ ] Faux vert : texte présent sans pagination correcte, canonical retrouvé mais
  correspondant à une ancienne version.
- [ ] Interdire édition arbitraire d'externe, OCR caché et pertes dissimulées.
- [ ] Synchroniser politique PDF/limites ; canari sous GO distinct.
- [ ] Rebuild requis ; fermer les deux politiques PDF et le profil complet.

### Z — Clôture bornée

**Objectif :** fermer le premier palier sans chantier permanent.
**Dépendances :** M0–M10.
**Frontières :** parcours complets, preuves et contrats vivants.
**Interface :** services appelables sans DOM ; aucun tool principal.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : pending rejouable après refresh, cache obsolète, reçu perdu ou
  canonical contaminant une faculté doivent être détectés.
- [ ] Matrice finale ciblée desktop/mobile/conversations croisées/crashs/formats ;
  voisins upload/Notes/Exports/Images/Agenda/Biblio/pipeline.
- [ ] Faux vert : smoke nominal seul ou régression voisine non exercée.
- [ ] Interdire nouvelle dépendance, extension d'édition, benchmark général et tools
  du modèle principal.
- [ ] Rassembler preuves autorisées et limites ; retirer états transitoires remplacés.
- [ ] Rebuild seulement pour correction effectivement livrée.
- [ ] Fermer chaque critère prouvé ou explicitement qualifié, sans finding vivant
  caché ; ne pas ouvrir une nouvelle capacité pour prolonger la clôture.

## 9. Qualification comparative du renderer

Profil décidé ; moteur non sélectionné. Aucun package/service choisi ou installé
par la création de cette TODO.

| Stratégie | Preuves requises | Coût/propriétaire |
| --- | --- | --- |
| Extraire/améliorer le local | Fonts Unicode PDF, structure DOCX, styles, tableaux, pagination, ressources et déterminisme. | Pas de service partagé ; charge réelle de composition. Celebrimbor. |
| Dépendance applicative dédiée | Deux formats réellement couverts, licences, fonts embarquées, versions fixes, isolation et aucune récupération externe. | Maintenance packages/image. Celebrimbor. |
| Adapter Stirling/LibreOffice | Endpoint/options, limites, auth serveur, timeout, isolation, cleanup et reproductibilité. | Disponibilité/réseau partagés ; contrat Sauron, adapter Celebrimbor. |

- [ ] Corpus synthétique : accents, ligatures, espaces insécables, titres,
  emphases/listes/citations/liens, tableaux multipages, sauts de page et marges.
- [ ] Prouver fidélité du contenu et du rendu, reproductibilité de composition,
  stabilité binaire ou normalisation des métadonnées volatiles.
- [ ] Conserver empreinte des octets effectivement figés pour l'exécution.
- [ ] Mesurer isolation/ressources/nettoyage et sécurité sans contenu privé/provider.
- [ ] Un seul chemin sélectionné ; aucun fallback renderer.
- [ ] Renderer sans choix de chemin Nextcloud ni publication de fichier.
- [ ] Ne pas traiter doc-pipeline comme capacité de rendu sans contrat correspondant.

## 10. Matrice réutiliser / extraire / créer et propriétaires

| Traitement | Frontières |
| --- | --- |
| Réutiliser | Inventaire workspace_files, sélections, extracteurs, liens produit, protocole terminal, clients DAV et éléments de compensation ETag. |
| Extraire pour une responsabilité réelle | Primitive de snapshot transactionnelle ; renderer seulement si le chemin local gagne la qualification. |
| Modifier | Transport/service/finalisation chat, projections, liens/store workspace, clients DAV bornés, manifestes/guards, binding Fichier et réhydratation. |
| Créer | Services atelier/canonical/actions/reçus/claims/adoption/fraîcheur et contrôleur UI dédiés. |

Modules probables, noms proposés et non fichiers déjà livrés :

- document_workshop_contract.py : entrées/sorties/capacités.
- document_workshop_agent.py : appel unique et validation.
- document_workshop_turn_service.py : raccord conversationnel.
- document_workshop_store.py : artefacts/révisions/actions/reçus et transactions.
- document_workshop_execution.py : confirmation/journal/exécution.
- document_workshop_routes.py : frontières HTTP.
- document_canonical.py et document_rendering.py : modèle/rendu.
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

### Lots Sauron conditionnels

- [ ] Prouver identité DAV, préconditions, ETags et Versions si les preuves
  applicatives ne suffisent pas.
- [ ] Prouver le contrat borné Stirling/LibreOffice si cette candidate est étudiée.
- [ ] Fournir une preuve transactionnelle isolée si environnement SQL absent.

Permissions, fonts partagées, ressources, réseau et modifications de service sont
des lots Sauron distincts. Si le local satisfait le profil, aucun chantier de
plateforme de rendu n'est nécessaire.

## 11. Inconnues techniques restantes

Aucun ancien arbitrage produit ne reste OPEN.

- [ ] M0 : fenêtre/sortie/tokenisation/raisonnement/transport du modèle effectif.
- [ ] M8 : moteur satisfaisant le profil DOCX/PDF.
- [ ] M2/M7 : identité DAV, préconditions et Versions effectivement disponibles.
- [ ] M3 : environnement SQL concurrent isolé de preuve.

Expiration et bornes de chemins sont des recommandations à valider avec la
spécification, pas des décisions utilisateur déjà acquises.

## 12. Contre-audit et critères de clôture

- [ ] Distinguer décisions utilisateur, faits du HEAD, recommandations et qualifications.
- [ ] Ne conserver aucun ancien OPEN fermé par le design consolidé.
- [ ] Une soumission, une vraie parole utilisateur, un échange documentaire.
- [ ] Upload/picker/change/drag-and-drop conservés, sans duplication mobile.
- [ ] Navigation/adoption ciblées ; aucun synchroniseur global.
- [ ] Aucune mutation distante avant confirmation et claim valides.
- [ ] Canonical/rendu figés et correspondance distante vérifiée.
- [ ] Reçu séparé des paroles et des tool results ; réhydratation durable.
- [ ] Inventaire unique workspace_files, ID stable en update.
- [ ] ETag frais et If-Match réellement envoyés ; aucun écrasement implicite.
- [ ] Journal et remote_uncertain sans promesse d'exactly-once distribué.
- [ ] Aucun DELETE sans propriété ni rollback récursif de collections.
- [ ] DOCX externe et PDF externe traités avec fidélité honnête.
- [ ] Moteur choisi sur preuves, sans dépendance plateforme supposée.
- [ ] Appel documentaire unique, budgets qualifiés, aucun retry/fallback caché.
- [ ] Memory/Identity/Summary/Biblio/Stimmung préservés et non contaminés.
- [ ] Service tool-ready appelable sans DOM, aucun tool principal implémenté.
- [ ] Tous les parcours create/read/adopt/update/copy et les trois formats prouvés.
- [ ] Preuves live éventuelles explicitement autorisées et content-free.
- [ ] Docs/limites/statuts synchronisés ; aucun finding vivant caché.
- [ ] Lot Z fermé ; suites images/continuations/édition enrichie hors ce chantier.

## 13. Statut de publication documentaire

Cette TODO conserve la proposition issue du dialogue sous forme de cases à cocher.
Elle ne remplace pas les contrats vivants et ne lève pas l'invariant applicatif de
consolidation. Aucune fonctionnalité, qualification ou preuve live n'est déclarée
livrée par sa création. Aucun commit/push ni changement runtime n'est autorisé
implicitement par son enregistrement.
