# Atelier documentaire agentique Frida V1 — spécification validée et roadmap

Date : 2026-09-29.

Statut : **spécification et choix architecturaux validés par Tof ; M0 est le
prochain lot, non commencé ; aucun lot applicatif livré**.

Provenance : reconnaissance architecturale puis design consolidé dans le même
dialogue avec Tof. Création documentaire committée dans `d6b63fd1`, puis validation
explicite de la spécification et des six décisions amont par Tof le 2026-09-29.
Ce correctif docs-only inscrit cette validation ; il ne démarre aucun lot applicatif.

Les observations techniques ci-dessous sont rattachées au HEAD
`a2483bf1aa6f5e93ba7ec2800b8ff053cc0af2c6`, branche `main`, checkout
`/opt/platform/fridadev`. Elles doivent être revalidées de façon ciblée avant
l'exécution des lots concernés, sans recommencer une reconnaissance générale.

## Lecture des cases et portes d'autorisation

Une case cochée dans les décisions signifie « décidé par Tof », pas « livré ».
Une case ouverte dans les critères ou les lots signifie « à implémenter ou prouver ».
Les inconnues factuelles sont isolées en section 11. Les tests décrits sont des
preuves futures, pas des tests déjà exécutés pour cet atelier.

- [x] Reconnaissance et proposition de design produites dans le dialogue.
- [x] Création de cette TODO autorisée par Tof.
- [x] Spécification et choix architecturaux ci-dessous validés par Tof le 2026-09-29.
- [ ] Exception documentaire bornée inscrite dans le [AGENTS.md racine](../../../../AGENTS.md)
  dans un lot explicitement autorisé, avant tout patch applicatif.
- [ ] Lot d'implémentation concerné explicitement autorisé.
- [ ] GO distinct obtenu avant tout appel modèle réel de preuve.
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
- [x] Modèle initial principal `openai/gpt-5.1`, prompt documentaire distinct, un
  appel documentaire par préparation, aucun fallback ni nouveau réglage Admin.
- [x] Plafond documentaire dédié de 24 000 tokens de sortie ; chat normal inchangé
  à 8 192 tokens ; fenêtre officielle 400 000 et sortie officielle 128 000 tokens.
- [x] Admission mesurée avant appel, avec réservation de 24 000 tokens et marge
  explicite d'enveloppe/raisonnement selon le transport réel.
- [x] Document produit : A4, corps 12 points, interligne 1,5, marges 2,5 cm ;
  canonical au plus 10 000 mots et 75 000 caractères Unicode, premier plafond atteint.
- [x] DOCX/PDF rendus au plus 20 pages ; Markdown borné par mots/caractères,
  sans pagination stable ; aucune sauvegarde partielle en cas de dépassement.
- [x] Source de plus de 20 pages admise si elle tient intégralement dans l'entrée
  avec dialogue, prompt, autres sources et réserve ; sinon réduction/sélection ou refus.
- [x] Préparation sans deadline murale si progression effective projetée ; absence
  de progression pendant 120 secondes : échec fermé ; annulation explicite possible.
- [x] Pending sans expiration temporelle ; invalidation seulement par annulation,
  remplacement, changement de répertoire/cible ou perte de fraîcheur/précondition.
- [x] Chemins : Documents, au plus 8 niveaux, 180 caractères Unicode et 255 octets
  UTF-8 par segment/nom de fichier, 1 024 octets UTF-8 pour le chemin relatif complet.
- [x] Rendu local déterministe : Markdown depuis canonical, DOCX python-docx,
  PDF ReportLab Platypus avec police Unicode embarquée/épinglée ; aucun rendu distant.
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
Elles ne prouvent pas les capacités futures décrites ici. La présence historique
de Stirling/LibreOffice et doc-pipeline ne les place pas dans la composition
nominale : le renderer décidé est exclusivement applicatif et local. python-docx,
ReportLab et la police épinglée ne sont pas encore livrés dans l'image actuelle.

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
avec plafond dédié de 24 000 tokens ; chat normal conservé à 8 192 tokens. Aucun
fallback, continuation, chunking, réparation par second appel ou réglage Admin nouveau.

**Existant :** modèle et budget résolus depuis les réglages runtime ; lecteur
non streaming centré sur le texte extrait.

**Architecture validée :** entrées typées : demande/tour, contexte dialogique partagé,
répertoire autorisé, références explicites, sources et versions, capacités/budgets.
Sortie stricte prepared, clarify ou refuse. Prepared contient réponse courte,
opération, cible, canonical et limites ; les deux autres n'ont aucune action
exécutable. Le modèle ne possède aucun client d'écriture.

**Preuve à livrer :** admission complète dans 400 000 tokens en réservant 24 000
tokens et la marge explicite du transport/raisonnement ; limites de sortie de la
section 7. Les chiffres sont décidés, leur application reste à implémenter.

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
| document_revisions | Canonical immutable, schéma, empreinte, rendu figé, empreinte/version renderer et correspondance distante. |
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

**Preuve à livrer :** Versions et préconditions effectives sur la chaîne déployée.

- [ ] Aucun update sans version établie.
- [ ] Aucune fusion, copie, renommage ou nouvelle préparation automatique.
- [ ] Préserver le même workspace_file_id après succès.

### 3.12. Canonical et rendus

**Décision :** profil fixé sans images, DOCX/PDF Frida issus de la même révision
canonical. Pile locale déterministe : Markdown direct, DOCX python-docx, PDF
ReportLab Platypus et police Unicode embarquée/épinglée. Aucun service distant de
rendu ou moteur de secours. A4, corps 12 points, interligne 1,5, marges 2,5 cm ;
canonical au plus 10 000 mots et 75 000 caractères Unicode ; DOCX/PDF au plus 20 pages.

**Existant :** renderer Exports minimal, profil complet non couvert.

**Architecture validée :** titres, paragraphes, spans, listes, citations, liens, tableaux
simples et sauts de page ; refus images, HTML actif, macros et références
exécutables. Rendu préparé/figé avant action confirmable ; le clic écrit ces octets.
Pagination/marges pour DOCX/PDF ; marqueur documenté pour sauts de page Markdown,
dont la pagination dépend du lecteur.

**Preuve à livrer :** pile décidée et pagination finale, section 9. Versions,
licences, police et empreinte épinglées dans le lot applicatif ; aucune dépendance
n'est encore livrée par ce correctif documentaire.

- [ ] Même révision pour canonical, rendu, empreintes et version renderer.
- [ ] Update Frida DOCX/PDF seulement si leur correspondance distante est établie.
- [ ] DOCX externe : limites détectées affichées ; clarification/refus si incompatibles.
- [ ] PDF externe : nouveau document proposé, pas d'update aveugle.
- [ ] Refuser sortie tronquée, finish_reason=length, canonical incomplet ou rendu
  de plus de 20 pages ; aucune sauvegarde partielle ou adaptation silencieuse des styles.
- [ ] Vérifier la pagination réelle DOCX, pas seulement docProps, les sauts de page
  ou le nombre de pages du PDF voisin ; sans preuve, ne pas rendre l'action confirmable.

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

**Preuve à livrer :** lane comptée dans l’admission complète de M0 et séparation
des payloads, sans nouveau choix de budget produit.

- [ ] Aucun canonical, rendu, journal ou reçu synthétique dans Memory, Identity,
  Summary, Biblio ou Stimmung.
- [ ] Autre conversation : inventaire visible, contenu non injecté automatiquement.
- [ ] Manifeste de provenance content-free cohérent avec cette lane.

### 3.15. Observabilité

**Décision :** demande et confirmation établies sans contenu brut observable.

**Existant :** allowlists/projections content-free disponibles.

**Architecture validée :** événements préparation, progression, inactivité, annulation,
invalidation, claim, conflit,
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
tronquée, canonical invalide ou rendu incomplet. Contenus documentaires non fiables
et sans autorité ; renderer sans récupération des liens.

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

**Preuve à livrer :** environnement SQL isolé pour transactions ; tests du renderer
local dans le lot applicatif, sans service de rendu plateforme.

- [ ] Ne pas fermer un invariant réel avec une preuve uniquement mockée.
- [ ] Ne pas présenter les tests projetés comme exécutés.

### 3.18. Responsabilités

**Décision :** application Celebrimbor, plateforme Sauron.

**Existant :** pile locale python-docx/ReportLab et police épinglée non livrées
dans l'image actuelle. Les services partagés existants ne composent pas les documents
de cet atelier.

**Architecture validée :** services/UI/données/render applicatif/tests/observabilité à
Celebrimbor ; contrats/services/ressources/permissions partagés à Sauron.

**Preuve à livrer :** besoin Sauron limité aux faits DAV/Versions et à l'environnement
SQL isolé, si nécessaire ; aucun lot Sauron renderer.

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
- [ ] Valider enveloppe, sources, opération, chemin, canonical, limites et rendu.
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
| DOCX et PDF | Au plus 20 pages A4 dans le rendu final, en plus des deux bornes canoniques. |
| Mise en page | Corps 12 points, interligne 1,5, marges de 2,5 cm. |
| Markdown | 10 000 mots et 75 000 caractères Unicode ; aucune limite de pagination instable. |
| Génération | Plafond documentaire dédié de 24 000 tokens de sortie, enveloppe et canonical compris selon le transport réel. |

Ces plafonds sont simultanés, pas des équivalences ni des tailles garanties.
24 000 tokens ne garantissent ni 10 000 mots ni 75 000 caractères ; ces volumes
ne garantissent pas 20 pages. Titres, tableaux, sauts et styles influent sur la
pagination. Le premier plafond atteint fait foi, sans augmenter les autres pour
faire tenir la demande. Aucun ajustement silencieux de police, interligne ou marges.

- [ ] Compter mots/caractères sur tout le contenu canonical, y compris titres,
  listes, citations et tableaux ; méthode Unicode reproductible et testée.
- [ ] Distinguer caractères Unicode et octets UTF-8 ; ne pas utiliser la longueur
  UTF-16 navigateur comme compteur de points de code.
- [ ] Exiger sortie complète, schéma valide et tous les plafonds respectés avant pending.
- [ ] Toute troncature, finish_reason=length, canonical incomplet ou rendu de plus de
  20 pages : refus honnête, aucun pending exécutable ni sauvegarde partielle.
- [ ] Ne jamais rogner un document ou diminuer la mise en page pour contourner un refus.

### 7.2. Source longue

La limite de 20 pages concerne uniquement le document produit. Une source peut
dépasser 20 pages si son contenu admissible tient réellement dans l'entrée du
modèle, avec dialogue, prompt, autres sources et réserves. Le nombre de pages
d'une source n'est pas un critère de refus de volume produit.

- [ ] Admettre une source de plus de 20 pages lorsque l'ensemble tient dans la fenêtre.
- [ ] Ne jamais tronquer, résumer ou échantillonner une source silencieusement.
- [ ] Si elle ne tient pas, demander de réduire/sélectionner la source ou refuser
  avant l'appel documentaire ; aucune réduction automatique de la fenêtre dialogique.

### 7.3. Modèle et budget dédiés

Modèle initial : `openai/gpt-5.1`, modèle principal courant décidé par Tof.
Fenêtre officielle : 400 000 tokens ; sortie maximale officielle : 128 000 tokens.
Le plafond local documentaire de 24 000 est volontaire. Le plafond du chat normal
reste inchangé à 8 192 tokens.

Références primaires conservées et vérifiées sur leurs pages publiques, sans appel modèle :

- [OpenAI — GPT-5.1](https://developers.openai.com/api/docs/models/gpt-5.1).
- [OpenRouter — openai/gpt-5.1](https://openrouter.ai/openai/gpt-5.1).

Avec I = tokens de l'entrée complète, M_transport = marge explicite d'enveloppe
et de raisonnement selon le transport réel, l'admission impose :

```text
T_document = 24 000
T_chat_normal = 8 192
W_modele = 400 000
I + T_document + M_transport <= W_modele
```

I comprend prompt documentaire, dialogue, sources complètes et métadonnées
injectées. Le calcul de M_transport doit être explicité et mesuré dans M0, en
comptant correctement le raisonnement et l'enveloppe selon leur inclusion dans
les tokens du transport. Masquer le raisonnement ne le rend pas gratuit. Cette
preuve d'admission n'autorise aucune modification de T_document ou du volume produit.
Les limites officielles ne constituent pas une mesure de runtime réalisée ici.

Le compteur heuristique actuel ne suffit pas à garantir l'admission. M0 livre un
décompte ou une borne conservatrice prouvée pour ce modèle et le payload complet,
et refuse avant appel lorsque la place nécessaire ne peut être établie.

- [ ] Séparer le plafond documentaire du réglage du chat normal ; payload documentaire
  à 24 000 et payload normal à 8 192, sans nouveau réglage Admin ni changement runtime normal.
- [ ] Vérifier admission avant appel et conserver finish_reason/métadonnées utiles.
- [ ] Borner l'enveloppe technique selon les plafonds décidés et le schéma, sans
  introduire de plafond produit caché ou de troncature.
- [ ] Un seul appel documentaire ; aucun fallback, continuation, chunking ou second
  appel de réparation.
- [ ] Un modèle hors contrat initial ne devient pas silencieusement une alternative.
- [ ] Progression réelle projetée, 120 secondes d'inactivité puis échec fermé ;
  aucune deadline murale supplémentaire tant que la progression continue.

## 8. Roadmap par micro-lots

Tous les lots restent ouverts et non commencés. Spécification et décisions amont
sont validées ; M0 est le prochain lot. Les portes d'autorisation applicative de
début de fichier restent préalables à l'exécution ; ce correctif n'en réalise aucune.
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
| M8 | M0–M7 ; pile locale décidée et preuve de pagination, aucune sélection de moteur. |
| M9 | M7–M8 ; raccord DOCX et preuve du fichier final. |
| M10 | M9 et pile M8 ; raccord PDF et sa politique de source. |
| Z | M0–M10 ; clôture finie et preuves des voisins. |

L'ordre M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → Z
est conservé, sans cycle. M0 établit le contrat des 20 pages ; M8–M10 en livrent
les preuves de rendu final. Cette répartition ne reporte aucun choix de volume.
Le canari d'écriture reste après M5 et sous GO distinct ; aucun lot renderer Sauron.

### M0 — Implémentation et preuve des bornes décidées

**Objectif :** rendre applicables les bornes de volume, admission, chemin et
inactivité déjà fixées ; aucune nouvelle décision de taille ou budget.
**Dépendances :** spécification validée ; exception AGENTS.md et GO applicatif encore
à obtenir/livrer. Préalable de M1 et des lots suivants.
**Frontières :** contrat documentaire, adapter modèle, compteur/admission, gardes
canoniques et de chemin, suivi de progression ; chat normal préservé.
**Interface :** gpt-5.1, sortie documentaire 24 000, chat 8 192, fenêtre 400 000,
réserve explicite ; canonical 10 000 mots/75 000 caractères ; profil A4/20 pages
déclaré, compteur final fourni par le renderer M8–M10 ; watchdog 120 secondes.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : refus à 10 001 mots ou 75 001 caractères, JSON complet mais
  finish_reason=length, entrée qui tient sans réserve mais dépasse avec elle ;
  payload documentaire héritant par erreur de 8 192 ou payload normal porté à 24 000.
- [ ] Prouver les limites exactes de chemin, y compris nom de fichier, octets/Unicode,
  et refus sans normalisation destructive ; source >20 pages admise si elle tient.
- [ ] Implémenter mesure d'entrée et marge explicite du transport/raisonnement,
  validation de sortie et contrat de page_count ; aucune pagination binaire livrée
  artificiellement avant son renderer.
- [ ] Implémenter le suivi d'inactivité : progrès continu au-delà de 120 secondes
  accepté, 120 secondes sans progrès refusées, keepalive seul non probant.
- [ ] Tests ciblés synthétiques et transport fake ; voisins réglages/raisonnement/
  parser/compteur/path validation, sans fournisseur ni DB opérateur.
- [ ] Faux verts : heuristique présentée comme exacte, payload partiel mesuré,
  raisonnement omis, mots/UTF-16 confondus, timer relancé par animation ou heartbeat.
- [ ] Interdire provider réel, fallback, deadline murale pendant progrès, nouvelle
  taille produit et modification du plafond normal de 8 192.
- [ ] Synchroniser contrats bornes/transport/progression ; appel réel éventuel
  sous GO distinct, jamais nécessaire pour décider les chiffres.
- [ ] Aucun déploiement produit ; rebuild seulement lors de livraison applicative
  explicitement autorisée. Fermer sur gardes et mesures hermétiquement prouvés,
  en laissant pagination/rendus binaires aux lots M8–M10.

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

**Objectif :** démontrer le moteur avant raccord réel d'écriture.
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

### M8 — Implémentation et preuve de la pile locale décidée

**Objectif :** livrer la pile locale déterministe et ses preuves de rendu, sans
comparaison de moteurs ni nouvelle décision de dépendance.
**Dépendances :** M0–M7 fermés ; canonical stable de M4, invariants de publication
et update de M5–M7. Markdown est livré avant les formats binaires.
**Frontières :** document_rendering/canonical, exigences de dépendances/image
applicative et assets de police ; compatibilité Exports préservée.
**Interface :** canonical + profil/version → rendered_revision + empreinte et
preuve de pagination ; Markdown direct, DOCX python-docx, PDF ReportLab Platypus.
**Propriétaire :** Celebrimbor exclusivement ; aucun lot Sauron renderer.

- [ ] Épingler versions python-docx/ReportLab et dépendances nécessaires, licences,
  police Unicode embarquée, empreinte et versions du profil de rendu.
- [ ] Implémenter depuis la même révision canonical : titres, paragraphes, gras/
  italique, listes, citations, liens, tableaux simples et sauts de page, sans images.
- [ ] Appliquer A4, corps 12 points, interligne 1,5, marges 2,5 cm et limite finale
  de 20 pages ; refuser plutôt que changer silencieusement la mise en page.
- [ ] Rouge causal : Unicode perdu, style/tableau mal rendu, 21e page, canonical
  ou empreinte discordants et bytes non déterministes doivent être détectés.
- [ ] Tests corpus synthétique et voisins génération/extraction Exports ; structure
  OOXML, fonts, rendu PDF, pagination et absence de récupération réseau.
- [ ] Faux verts : texte extrait seul, DOCX simplement ouvrable, fonts de l'hôte,
  docProps ou sauts déclarés présentés comme pagination réelle ; PDF voisin utilisé
  comme preuve automatique du DOCX.
- [ ] Interdire service distant nominal, fallback, benchmark comparatif, images,
  changement d'ownership Exports et toute modification de plateforme.
- [ ] Synchroniser pile locale/profil/déterminisme/licences et preuves de la section 9.
- [ ] Rebuild applicatif requis pour livrer bibliothèques/police, uniquement dans
  ce futur lot autorisé ; aucun raccord nominal aux formats avant M9/M10.
- [ ] Fermer sur pile locale, isolation, déterminisme et compteurs de pages prouvés ;
  aucune dépendance n'est déclarée livrée par la validation documentaire.

### M9 — DOCX Frida et retravail externe

**Objectif :** create/update DOCX et retravail externe honnête.
**Dépendances :** M7–M8.
**Fichiers :** python-docx via renderer local M8, reader DOCX, révisions et projection des limites.
**Interface :** rendu lié au canonical et update à identité stable.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : mismatch canonical/rendu → refus ; externe complexe → limite
  ou refus ; update → même ID.
- [ ] Tests OOXML/styles/listes/tableaux/liens/pages et voisins extraction/Exports ;
  archives excessives, relations externes et pertes détectables.
- [ ] Prouver le DOCX rendu <=20 pages avec le profil décidé ; si la pagination réelle
  n'est pas établie, aucune action confirmable, sans autre moteur de secours.
- [ ] Faux vert : valider uniquement le texte extrait ou l'ouverture du ZIP.
- [ ] Interdire fidélité arbitraire promise, images incorporées et ownership Exports.
- [ ] Synchroniser formats/fidélité ; preuve synthétique live sous autorisation.
- [ ] Rebuild requis ; fermer profil DOCX et correspondance canonique.

### M10 — PDF Frida et PDF externe comme source

**Objectif :** rendu PDF ; update uniquement si canonical correspondant établi.
**Dépendances :** M9.
**Fichiers :** ReportLab Platypus via renderer local M8, reader PDF, politique de cible
et mapping des révisions.
**Interface :** PDF Frida lié ; PDF externe vers proposition de nouveau document.
**Propriétaire :** Celebrimbor.

- [ ] Rouge causal : externe à modifier → nouveau document ; Frida désynchronisé
  → aucun update aveugle.
- [ ] Tests Unicode/visuel/fonts/pagination/tableaux/liens, PDF chiffré/scanné,
  canonical absent et octets distants changés ; voisins readers/Exports.
- [ ] Vérifier <=20 pages A4, corps 12 points, interligne 1,5 et marges 2,5 cm
  dans le PDF final ; 21e page ou source canonique excessive → refus sans partie sauvegardée.
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
- [ ] Fermer chaque critère par une preuve et les limites/refus du contrat testés,
  sans finding vivant caché ; ne pas ouvrir une nouvelle capacité pour prolonger la clôture.

## 9. Pile locale de rendu décidée et preuves à livrer

Le chemin architectural est arrêté : pile locale applicative déterministe, sans
service distant de composition, fallback ou comparaison de moteurs. Les dépendances
n'existent pas encore dans l'image actuelle ; leur livraison appartient à M8,
pas à ce correctif documentaire.

| Format | Implémentation décidée | Preuve requise |
| --- | --- | --- |
| Markdown | Sérialisation directe du canonical. | Structure, liens et sauts documentés ; 10 000 mots/75 000 caractères, sans pagination stable. |
| DOCX | python-docx. | Profil A4/12 points/interligne 1,5/marges 2,5 cm et pagination finale <=20 pages. |
| PDF | ReportLab Platypus avec police Unicode embarquée et épinglée. | Même révision/profil, Unicode français et compte final <=20 pages. |

DOCX/PDF sont issus de la même révision canonical. Le renderer fournit la version
du profil, l'empreinte de ses entrées et celle des octets figés ; il ne choisit pas
de chemin Nextcloud et ne publie pas le fichier. Dates de provenance et métadonnées
volatiles ne doivent pas rendre les mêmes entrées non déterministes.

- [ ] Épingler versions des bibliothèques/dépendances, licences, police, empreinte
  et profil dans le lot applicatif ; pas d'utilisation de fonts implicites de l'hôte.
- [ ] Corpus synthétique : accents/ligatures/espaces insécables, titres/paragraphes,
  gras/italique/listes/citations/liens/tableaux simples/sauts et marges/pagination.
- [ ] Tester A4, corps 12 points, interligne 1,5 et marges 2,5 cm ; aucun ajustement
  silencieux pour faire entrer une 21e page.
- [ ] Prouver le nombre réel de pages du DOCX final : python-docx écrit l'OOXML mais
  ne fournit pas à lui seul une preuve de pagination rendue. Ni docProps, ni les
  sauts déclarés, ni le PDF voisin ne suffisent. Sans preuve, refus avant pending.
- [ ] Vérifier le nombre de pages du PDF final et refuser dépassement/incomplétude.
- [ ] Prouver déterminisme, isolation, tailles/ressources/nettoyage et absence
  d'accès réseau de composition sur contenu synthétique, sans provider réel.
- [ ] Même canonical et empreintes concordantes ; aucun moteur de secours ou image.
- [ ] Aucune composition nominale via Stirling/LibreOffice ou doc-pipeline ; leurs
  responsabilités existantes hors composition restent préservées.

## 10. Matrice réutiliser / extraire / créer et propriétaires

| Traitement | Frontières |
| --- | --- |
| Réutiliser | Inventaire workspace_files, sélections, extracteurs, liens produit, protocole terminal, clients DAV et éléments de compensation ETag. |
| Extraire pour une responsabilité réelle | Primitive de snapshot transactionnelle ; interfaces de rendu partageables seulement à invariants Exports préservés, sans changement de moteur décidé. |
| Modifier | Transport/service/finalisation chat, projections, liens/store workspace, clients DAV bornés, manifestes/guards, binding Fichier et réhydratation. |
| Créer | Services atelier/canonical/actions/reçus/claims/adoption/fraîcheur et contrôleur UI dédiés ; renderer python-docx/ReportLab, profil et police épinglés. |

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
- [ ] Fournir une preuve transactionnelle isolée si environnement SQL absent.

Permissions DAV, réseau ou environnement SQL partagé relèvent de lots Sauron
distincts si les faits les imposent. Les bibliothèques et la police du renderer
sont embarquées dans l'application par Celebrimbor ; aucun lot Sauron renderer,
font partagée ou service de conversion n'est prévu.

## 11. Faits externes restant à prouver

Toutes les décisions produit et architecturales amont sont fermées. Budgets,
volume, source longue, progression/pending, chemins et moteur ne sont plus des
inconnues ou des comparaisons. Leur implémentation et leurs tests restent ouverts.

- [ ] M2/M5/M7 : comportement DAV effectif, identité distante, préconditions/ETags
  et Versions disponibles sur la chaîne déployée.
- [ ] M3 : environnement SQL concurrent isolé de preuve si non établi par le HEAD.

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
- [ ] Canonical/rendu figés et correspondance distante vérifiée.
- [ ] Reçu séparé des paroles et des tool results ; réhydratation durable.
- [ ] Inventaire unique workspace_files, ID stable en update.
- [ ] ETag frais et If-Match réellement envoyés ; aucun écrasement implicite.
- [ ] Journal et remote_uncertain sans promesse d'exactly-once distribué.
- [ ] Aucun DELETE sans propriété ni rollback récursif de collections.
- [ ] DOCX externe et PDF externe traités avec fidélité honnête.
- [ ] Pile locale décidée livrée/épinglée/prouvée, aucune dépendance plateforme de rendu.
- [ ] Document produit <=10 000 mots et <=75 000 caractères Unicode ; DOCX/PDF
  rendus <=20 pages A4, corps 12 points/interligne 1,5/marges 2,5 cm.
- [ ] Markdown sans pagination stable ; aucun plafond de 20 pages appliqué aux sources.
- [ ] Source longue admise si entrée complète admissible ; sinon réduction/sélection
  ou refus avant appel, aucune troncature/résumé/échantillonnage silencieux.
- [ ] Un appel documentaire gpt-5.1, plafond dédié 24 000, chat inchangé 8 192,
  entrée mesurée avec réserve complète dans 400 000 ; aucune promesse d'équivalence
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

## 13. Statut de publication documentaire

Cette TODO conserve la spécification et les décisions validées par Tof sous forme
de cases à cocher. M0 est le prochain lot et reste non commencé.
Elle ne remplace pas les contrats vivants et ne lève pas l'invariant applicatif de
consolidation. Aucune fonctionnalité, dépendance ou preuve live n'est déclarée
livrée par ce correctif docs-only. Commit/push sont explicitement autorisés pour
la roadmap et son entrée de hub ; aucun changement runtime n'est autorisé.
