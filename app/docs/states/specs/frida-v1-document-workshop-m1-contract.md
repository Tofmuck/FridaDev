# Atelier documentaire Frida V1 — contrat M1

Date : 2026-10-04. Statut : code et preuves hermétiques M1 ; activation différée.
La [roadmap autoritative](../../todo-todo/product/frida-v1-document-workshop-todo.md)
reste l'unique spécification du chantier. Le [contrat M0](frida-v1-document-workshop-m0-contract.md)
reste inchangé : aucun nouveau compte, budget, modèle ou transport de préparation.

## Entrée et compositeur

Le même bouton **Fichier**, menu et input servent le bureau et le téléphone :
**Ajouter un fichier existant** et **Créer ou modifier un document**, exactement.
Le menu ferme à la sélection, Échap, Tab ou clic extérieur ; flèches/Home/End
parcourent ses choix. `aria-haspopup`, `aria-controls`, `aria-expanded` et le
retour de focus suivent l'ouverture. Sur téléphone, son ouverture ferme le
panneau des autres outils ; aucune copie mobile ni second binding.

`chat_document_workshop.js` possède le clic Fichier. `chat_active_documents.js`
possède toujours l'unique listener `change` et le drag-and-drop, l'upload
séquentiel, les erreurs/statuts et le retrait. Son bouton reste fourni à
`render`, notamment pour le désarmer pendant upload. Input `multiple`, extensions
et MIME acceptés restent identiques. Ouvrir le menu ou l'édition n'ouvre pas le
picker ; Ajouter l'ouvre une fois. L'upload ne rejoint aucune route atelier.

Le panneau d'édition appartient au compositeur courant et ne contient aucun
éditeur complet ni aperçu. Répertoire, cible optionnelle et brouillon utilisent
le contexte courant ; les sélections de lecture existantes restent des sources.
Elles ne désignent jamais implicitement une cible. Les thèmes sont conservés ;
le téléphone utilise sa présentation sombre existante même avec préférence claire.

Seul **`editing` reçu du serveur** est projeté. `busy` est une attente locale
d'ouverture/relecture, sans phase `preparing`, pourcentage, heartbeat probant,
`pending` ou annulation de job. « Retour au chat » ferme l'édition locale, sans
requête d'annulation ni suppression du contexte SQL. Aucune expiration d'édition
ou de pending ; le watchdog M0 concerne la préparation future.

## Autorité et routes

`document_workshop_routes.py` compose des routes fines ;
`document_workshop_context_service.py` valide le scope et les réponses.

- `POST /api/document-workshop/contexts` accepte uniquement
  `conversation_id`, `workspace_folder_id`, `target_file_id` optionnel/null.
  Identités UUID vérifiées ; champs état, chemin, nom ou URL client refusés.
  Succès `201`, contexte avec identité propre, liens et état `editing`.
- `GET /api/document-workshop/contexts/{id}` relit le contexte puis réévalue
  conversation active, association au même répertoire actif et cible éventuelle.
  Succès `200` ; aucun effet externe ou tour conversationnel.

La réponse contient `id`, `conversation_id`, `workspace_folder_id`,
`target_file_id`, `target_relative_path`, `state`, `created_at` et
`capabilities: {prepare: false}`. La référence distante interne n'est pas exposée.
Réponses de refus fixes/content-free : requête invalide `400`, ressource absente
`404`, scope modifié/incohérent `409`, cible impropre/chemin invalide `422`,
stockage/lecture indisponible `503`. Les exceptions ne sont pas recopiées.

M1 accepte sans cible un répertoire existant associé côté serveur, y compris
local-only : cela ne prouve aucune disponibilité DAV. Une cible est un fichier
inventorié actif de ce même répertoire, document texte `.md` ou `.docx`, lié
Nextcloud `linked`. Un PDF existant ne possède pas encore la provenance/canonical
Frida exigée pour update ; sa lecture ou copie distante reste M2, sa production
M8–M10. TXT/ODT/images restent des sources possibles par les parcours existants,
pas de nouveaux formats de cible produit.

Le nom distant vient du lien serveur. L'option ciblée
`get_nextcloud_link(..., fail_closed=True, preserve_target_identity=True)`
conserve exactement nom, référence et état persistés ; le défaut de lecture
historique et ses projections restent inchangés. M1 ne réutilise pas la sanitation
historique comme resolver. La cible est validée par **l'unique garde M0** sur
`Documents/<nom exact>` ; aucune troncature/basename/normalisation de son identité.
Nom et référence sont figés dans le contexte. Leur changement, une suppression,
un déplacement ou un lien impropre invalident sa relecture.

Aucune conversation : `newThread` reste le mécanisme de création ; il retourne
l'identité réellement obtenue ou null. Son option locale `activateIf` refuse une
sélection tardive avant ses effets UI. M1 vérifie résultat et identité courante
avant tout POST de contexte. Aucun répertoire associé : choix explicite parmi les
répertoires existants puis **Associer ce répertoire à la conversation** réutilise
le PATCH existant. Aucune réaffectation silencieuse à l'ouverture, aucun MKCOL.
Création échouée : association désarmée et refusée aussi par son callback.

Génération locale et signature conversation/répertoire neutralisent réponses
POST/GET/association/création tardives. Double entrée pendant ouverture n'émet
pas un second POST. Navigation ferme le panneau ; un déplacement courant notifie
le scope immédiatement après le PATCH, avant les inventaires asynchrones.
Changer la cible crée une nouvelle identité de contexte ; l'ancien contexte
n'est pas réutilisé. Les anciens enregistrements ne deviennent pas des actions.

## Persistance limitée

`document_workshop_contexts.py` utilise PostgreSQL et la résolution de connexion
serveur existante. La migration idempotente
`app/core/sql/document_workshop_contexts.sql` crée seulement
`document_workshop_contexts` : identité, conversation, répertoire, cible
optionnelle, chemin/référence serveur figés, état fermé `editing`, date.
Aucun contenu, faux message, artifact, revision, receipt, claim ou journal futur.
FK avec suppression en cascade sur suppression physique des ressources ; les
soft deletes et déplacements sont réévalués par le service.

L'INSERT revalide et verrouille les lignes conversation/répertoire et cible/lien
avec `FOR SHARE`, dans sa transaction. Une modification entre validation service
et insertion refuse le contexte. Cela ne remplace ni les claims ni le fencing M3.

La migration et `init_db()` sont livrés **sans application automatique à
l'import/startup**. Une livraison runtime distinctement autorisée devra appliquer
cette migration avant usage ; une table absente produit un refus contrôlé.
Dans ce lot, seule la base PostgreSQL éphémère de preuve a été initialisée.
Preuve démontrée : migration répétable, INSERT committé, relecture par une
connexion indépendante, FK/état fermé, revalidation SQL, identité Unicode intacte.
Pas de preuve de crash/reprise ni d'application à la DB opérateur.

## Préparation encore indisponible

`submitCanonicalChatMessage` garde le mode documentaire immédiatement après le
garde commun `chatRequestInFlight`, avant transcript/cache, effacement du
brouillon et `/api/chat`. Clavier, Whisper et Dialogue passent par cette même
fonction. Refus `document_preparation_unavailable`, brouillon conservé ; sortie
explicite rétablit le parcours normal. Aucun second transcript ni faux tour.

Côté serveur, la présence de `document_context_id` dans `/api/chat`, y compris
faux/null/vide, retourne `409 document_preparation_unavailable` **avant**
`begin_turn`, résolution de conversation, proxies, service chat et persistance.
Le message ordinaire sans ce champ conserve son chemin, paramètres, streaming,
locks finaux et persistance. Aucun protocole de claims/tours clients livré ici.

L'ouverture/relecture n'appelle aucun modèle, préparation simulée produit,
extracteur, renderer ou client DAV. Ni préparation ni confirmation exécutable.
M4 raccordera la préparation ; M3 gèrera réservation/concurrence ; M2 doit encore
livrer navigateur distant, adoption ciblée et lecture fraîche.

## Preuves et réserves

L'[exécution M1 de la roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md#m1--menu-fichier-et-contexte-explicite)
donne runners, commandes, nombres, durées et contre-audit. Suites :
`test_server_document_workshop_contexts_contract.py` (routes montées, effets à
zéro), `test_context_store_postgresql.py` (SQL réel isolé),
`test_frontend_browser_document_workshop.js` (menu/picker/change réels,
multisélection séquentielle, erreurs/drop/retrait, bureau/mobile, navigation,
création/GET/PATCH différés), garde canonique trois provenances et voisins.

Le runner SQL exige explicitement `M1_PROOF_PG_SOCKET` et une base synthétique
`m1proof` isolée ; il réinitialise son seul schéma de preuve. Il est ignoré en
suite ordinaire sans ce harnais, jamais présenté comme preuve SQL dans ce cas.
Les cinq cas ont été exécutés réellement avec ce socket, zéro skip.
Aucun fournisseur, DAV, base opérateur, téléchargement, installation, restart,
build, déploiement ou merge. Les transports navigateur sont simulés ; aucune
conclusion live ne s'en déduit.
