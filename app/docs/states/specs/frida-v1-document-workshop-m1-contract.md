# Atelier documentaire Frida V1 — contrat M1

## Évolution M4 — 6 octobre 2026

L’entrée et le contexte M1 sont conservés. Les capacités publiques annoncent la préparation Markdown create/copy ; `confirm` et `update` restent faux. GET contexte projette la dernière préparation durable. La validation de scope interne M2 reste indépendante de cette projection HTTP.
Voir le [contrat M4](frida-v1-document-workshop-m4-contract.md) pour les preuves
hermétiques et les limites ; migrations opérateur, runtime, modèle/DAV live et M5 restent ouverts.


Date : 2026-10-04. Statut : code et preuves hermétiques M1 ; activation différée.
La [roadmap autoritative](../../todo-todo/product/frida-v1-document-workshop-todo.md)
reste l'unique spécification du chantier. Le [contrat M0](frida-v1-document-workshop-m0-contract.md)
conserve ses comptes, budgets, modèle et transport de préparation. Le
[contrat M2](frida-v1-document-workshop-m2-contract.md) précise désormais les
chemins sources/collections partagés et la lecture/adoption ciblées.

## Évolution M3 — 6 octobre 2026

Le présent document conserve les preuves et frontières historiques M1. Le
[contrat M3](frida-v1-document-workshop-m3-contract.md) complète l'autorité des
contextes : identité immuable, fermeture durable `cancelled`/`invalidated`,
invalidation irréversible du scope et réservation commune au chat. Les prises de
ressources de création refusent un verrou concurrent pour éviter une attente
cyclique avec les mutations existantes. Le menu/protocole M1 et la préparation
publique inactive sont conservés. Migrations uniquement prouvées en isolation ;
application opérateur et rebuild restent ouverts.

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
Frida exigée pour update ; sa lecture/adoption appartient à M2, sa copie et sa
production restent aux lots ultérieurs. TXT/ODT/images restent des sources possibles par les parcours existants,
pas de nouveaux formats de cible produit.

Le nom distant vient du lien serveur. L'option ciblée
`get_nextcloud_link(..., fail_closed=True, preserve_target_identity=True)`
conserve exactement nom, référence et état persistés ; le défaut de lecture
historique et ses projections restent inchangés. M1 ne réutilise pas la sanitation
historique comme resolver. Depuis M2, la cible est validée par **l'unique garde
produit M0** sur le chemin complet `nextcloud_relative_path`, sous-répertoires
compris ; pour un lien historique non enrichi, `Documents/<nom exact>` reste
la représentation. Aucune troncature/basename/normalisation de son identité.
Chemin, référence et identité distante optionnelle `scope_key:file_id` sont
figés dans le contexte. Leur changement, une suppression, un déplacement ou
un lien impropre invalident la relecture GET. Cette identité interne n'est pas
exposée au navigateur ; l'option du getter conserve aussi les champs M2 présents.

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
L'extension idempotente M2 ajoute `target_remote_identity` nullable ; la
migration M2 porte également cette extension pour une installation M1 existante.
Aucun contenu, faux message, artifact, revision, receipt, claim ou journal futur.
FK avec suppression en cascade sur suppression physique des ressources ; les
soft deletes et déplacements sont réévalués par le service.

L'INSERT revalide et verrouille les lignes conversation/répertoire et cible/lien
avec `FOR SHARE`, dans sa transaction. Une modification entre validation service
et insertion refuse le contexte. Depuis M2, ce contrôle couvre aussi chemin
complet et identité distante enrichis, avec résolution `to_jsonb` des colonnes
optionnelles du lien historique. Cela ne remplace ni les claims ni le fencing M3.

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
M4 raccordera la préparation ; M3 gèrera réservation/concurrence. M2 ajoute
navigateur distant, adoption ciblée et lecture fraîche seulement sur action
explicite ; l'ouverture/relecture du contexte seule reste sans DAV ni extraction.

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
