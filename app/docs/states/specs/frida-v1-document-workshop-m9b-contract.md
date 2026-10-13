# Atelier documentaire — M9-B, DOCX externe simple

**État courant au 13 octobre 2026 :** M9-A/M9-B/M10 restent fermés ; Z est clos
documentairement selon le [bilan archivé](../../todo-done/product/frida-v1-document-workshop-todo.md#bilan-de-clôture-z--13-octobre-2026).
Les remises et clôtures successives ci-dessous conservent leur chronologie et
leurs limites ; aucun nouveau test ni canari dans Z.

13 octobre 2026. Base exacte `0781f0014e291d84562bfd36cefc1418575f6318`,
branche `FridaV1-Document-Workshop-M9-B`. M9-A reste fermé.
**M9-B fermé le 13 octobre 2026**, après contre-audits Codex favorables du code
et du runtime livré ; clôture autorisée par Tof sur preuves acquises, sans nouveau test ni canari.
[Mandat et critères](../../todo-done/product/frida-v1-document-workshop-todo.md#m9-b--retravail-docx-externe-avec-fidélité-honnête),
[commandes, IDs exacts et exits](../baselines/document-workshop/frida-v1-document-workshop-m9b-20261013.json).

## Raccord minimal

Le propriétaire `document_workshop_update_target` distingue une origine de
création et une révision courante. Un DOCX adopté externe sans révision courante
est admis au mode M8-C existant `source.origin=external`, avec
`source_revision_id`, `canonical`, `canonical_sha256` nuls. Aucun reçu ni
canonical d'origine n'est inventé. Les octets frais M2 et leurs preuves
ID/chemin/ETag/taille/SHA sont transmis sans retrait d'élément.

Un document déclaré Frida exige toujours sa preuve historique complète. Un
externe déjà révisé par Frida suit également cette preuve et le mode renderer
`frida` pour sa révision courante ; son origine de création reste externe.
Une preuve absente ou incohérente ne donne aucun fallback externe. Un artefact
préparatoire sans révision courante n'invente pas d'origine Frida.

L'update de cible seule reste autorisé sans sélection de lecture. La copie garde
ses références explicitement sélectionnées et ne devient jamais un secours.
Aucun changement de protocole M8-C, de renderer, d'exécuteur, de publication,
de reçu, de route ou de workflow. Aucune migration nouvelle : les contraintes
M7 et M9-A acceptent déjà cette combinaison update/DOCX/origine externe.

## Avant confirmation et avant écriture

`document_workshop_actions.finalize` ajoute systématiquement
`external_docx_v1_reformat` aux limitations immuables d'un update DOCX d'origine
externe, même si le modèle retourne `limitations=[]`. La carte existante affiche
avant son bouton : remise en forme dans le profil Writer V1, absence de garantie
de conservation d'une mise en page arbitraire, refus du contenu non représentable
ou d'un import incomplet. Les consignes du tour et de l'enveloppe sont alignées ;
la garantie d'affichage appartient à l'application.

Le préflight complet, l'inventaire OOXML/UNO et les validations de paire restent
ceux du renderer qualifié. Macros/code actif, champs, images/objets, révisions,
styles/sections non représentables et preuves d'import réparé/incomplet/perte
restent des refus. Aucun validateur parallèle ni suppression silencieuse ajouté.

Confirmation, claim/fencing, snapshot avant libération Writer, métadonnées avant
PUT, relecture fraîche finale et If-Match préparé restent les autorités
existantes. Publication sur le même fichier/nom/ID distant ; un seul PUT/reçu
par confirmation, aucune copie, suppression, fusion ou restauration automatique.
Le reçu conserve `creation_author=external`, `revision_author=frida` ; la nouvelle
révision est liée au même artefact et demeure modifiable par le chemin normal.

## Preuves et limites

Le harnais PostgreSQL/DAV HTTP M9-A est étendu, pas remplacé. Le nominal part
d'OOXML synthétique écrit indépendamment de Frida/Writer : titre, paragraphe
avec gras/italique, liste décimale et tableau 2×2, sans reçu ni révision source.
Import/rendu réels, contenu attendu et structures de sortie, paire et seconde
révision sont contrôlés. Les preuves négatives vérifient zéro PUT/reçu de succès.
Les cas `inventory_complete=false`, `repair_used=true`, `loss_detected=true`
altèrent uniquement le manifest retourné par le renderer réel : ils prouvent
le refus applicatif, pas la production effective d'un import réparé par Writer.

Le navigateur HTTP natif vérifie l'adoption explicite, l'update cible seule,
l'avertissement visible avant clic et la fraîcheur. Playwright existant utilisé :
plugin Browser absent. Les voisins rejoués restent DOCX Frida M9-A,
copie explicitement sourcée et Markdown indépendant de Writer.

Renderer éphémère : image
`sha256:7a61bd805ca0e371873184f9b050ad47945ee32562c952437b65c793a6f4da10`,
pins SHA-256 `a788e48f649a84eed24af05ab340c1f2f080fe1f14c1827a86cf95d2a2900021`.
Socket/pins propres, réseau absent, aucun montage opérateur ni socket durable.
Les sorties modèle synthétiques prouvent le raccord, pas l'obéissance future
d'OpenRouter. Aucun canari, DAV live, document privé, déploiement ou rebuild.

Remise runtime à Sauron après contre-audit :
`app/core/document_workshop_update_target.py`, `document_workshop_actions.py`,
`document_workshop_turn.py`, `document_workshop_envelope.py` (tous sous
`app/core/`) et `app/web/chat_document_workshop.js`. Aucun fichier renderer,
image, pin durable ni migration opérateur à modifier dans ce lot.

## Clôture documentaire du 13 octobre 2026

Les preuves et la remise ci-dessus décrivent la livraison applicative initiale.
Le runtime a depuis été livré par Sauron puis contre-audité par Codex : image
`f31d02e67af2…`, code `df6b6afbd321f2dbd8772b1fb271067abc6c96ac`, renderer inchangé.
Les 36 tests Codex antérieurs, deux SQL Sauron et seul navigateur de reprise
conservent leur attribution, sans rejeu dans cette clôture.
[Clôture, provenance et limites](../../todo-done/product/frida-v1-document-workshop-todo.md#clôture-m9-b-sur-preuves-acquises--13-octobre-2026).
Aucune recette externe live ni fidélité Word universelle revendiquée.
**M9-B fermé ; M10 et Z non commencés.**
