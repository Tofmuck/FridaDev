# Atelier documentaire — M10, publication PDF Writer

13 octobre 2026. Base exacte `dcbd3e7540fbc6414defad9bf913c2470a3f6d38`,
branche `FridaV1-Document-Workshop-M10`. M9-A/M9-B restent fermés.
Mandat : [M10 et §9.5 de la roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md#m10--pdf-writer-source-externe-et-intégration-finale-des-formats).
Code et preuves isolées soumis au contre-audit ; livraison runtime et clôture
M10 ouvertes. Z non commencé.

## Plan et propriétaires

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » Le snapshot M8-A contient déjà la paire validée. Sélectionner son PDF
selon le format confirmé conserve la session, les validations et la publication
uniques ; aucun nouveau moteur, validateur, route, workflow ou dépendance.

1. Petite baseline des enveloppes, capacités SQL, Markdown et sources de copie.
2. Étendre les enums, capacités et contraintes effectives ; choisir les octets
   du snapshot selon le format confirmé, avant publication/reçu/téléchargement.
3. Étendre la preuve de révision Writer et les gardes de contexte/claim au PDF ;
   refuser l'externe en update et conserver la clarification et la copie explicites.
4. Réutiliser les harnais M9 sur PostgreSQL/DAV/modèle synthétiques et Writer
   qualifié éphémère ; navigateur HTTP natif, auto-audit du delta, documentation.
5. Nettoyer les ressources possédées, commit/push M10, arrêt pour contre-audit.

Le schéma structuré reste incorporé avant gel et mesure par l'admission
existante. Modèle, compteur partagé, budgets, canonical et facultés inchangés.
Les gardes de format sont étendues dans leurs propriétaires, y compris contexte,
claim et adoption sous cible sélectionnée. Aucun chemin concurrent conservé.

## PDF publié et PDF Frida

`document_renderer_store.content` vérifie toujours identité, révision/canonical,
manifeste et SHA/taille des **deux** artefacts. Il retourne le format demandé.
L'exécuteur utilise la même session M8-A : validation de paire, profil/pins,
pages, gel durable puis libération acquittée avant journal et mutation.
Les métadonnées sont extraites une fois sur les octets figés **avant PUT**.
Seul le PDF confirmé est écrit ; le DOCX compagnon reste interne.
MIME `application/pdf`, extension `.pdf`, empreinte, taille, cache, reçu et
réponse de téléchargement portent tous ce même PDF.

L'update PDF reprend la preuve durable existante : action réussie, révision
courante, canonical, paire, journal, reçu, cache et lien distant concordants.
Elle lie les octets fraîchement lus à la révision source distincte du candidat,
puis utilise `source.kind=pdf, origin=frida` déjà qualifié côté Writer. Aucun
import PDF éditable. Nom/ID/format inchangés, relecture finale et If-Match exact.
Preuve cassée ou source périmée : refus, sans fallback externe, copie de secours,
restauration, second PUT ou nouvelle préparation automatique.

## PDF externe et intention

Le reader M2 complet reste l'autorité : PDF texte sélectionné explicitement,
sans OCR implicite ; source scannée, chiffrée, partielle ou inexploitable refusée.
La limite de 20 pages ne s'applique pas aux sources de lecture.

Une cible PDF sans révision Frida prouvée peut servir de donnée au tour de
clarification. Le booléen serveur `target_pdf_has_frida_revision` vient du même
propriétaire de provenance ; une preuve cassée ne devient pas `false` permissif.
Un update externe est refusé par la finalisation et le raccord renderer.
Les consignes exigent un **nouveau document, un nouveau nom et une sélection de
lecture explicitement acceptés**. Sinon, `clarify` sans proposition. La copie
reste soumise aux références sélectionnées existantes et au no-clobber ; aucune
transformation automatique de l'update. Les réponses modèle des preuves sont
synthétiques : elles prouvent le raccord, pas l'obéissance future d'un modèle live.

## Migration et remise Sauron

Migration explicite additive :
[`document_workshop_pdf_m10.sql`](../../../core/sql/document_workshop_pdf_m10.sql),
après M9-A. Quatre contraintes existantes étendues au PDF, sans modification des
migrations précédentes. Aucune application au startup, GET ou DB opérateur.
Elle est incluse explicitement à Git malgré l'ignore `*.sql`.

La capacité PDF exige son schéma effectif et la session munie des pins locaux.
Schéma PDF absent : Markdown/DOCX conservés. Pins/session absents : Markdown
conservé. Le renderer incompatible refuse avant submit selon M8-A.
Aucun changement d'image, code renderer, pins, socket ou ressources durables.

La liste exhaustive des fichiers runtime et la migration à remettre à Sauron,
les commandes/IDs/exits et les incidents sont dans le
[relevé M10](../baselines/document-workshop/frida-v1-document-workshop-m10-20261013.json).
Aucun déploiement, rebuild, installation, migration opérateur, modèle/DAV live,
canari ou démarrage Z. Les confirmations, reconnexion sans POST automatique,
claims/fencing, reçus et continuité restent les parcours existants.

## Attribution et limites de preuve

Baseline **24/24**, puis **58 IDs distincts verts par union** : 52 Python,
4 schéma et 2 navigateur. Le run Python initial est à 50/52 : deux tests
vérifiaient un numéro de ligne source déplacé par le raccord. Leur oracle porte
désormais sur la fonction et l'instruction de refus ; ils passent dans le dernier
rejeu **4/4**, qui confirme aussi la restauration des deux contrôles causaux.
Les rouges, répétitions et preuves héritées ne sont pas ajoutés aux 58 IDs.
Commandes, durées disponibles, exits et identifiants exacts figurent au relevé.

Le profil A4/12 points/interligne 1,5/marges 2,5 cm est celui des pins Writer
qualifiés. Le nominal PDF vérifie le manifeste, l'identité de la paire et les
pages, en plus du contenu demandé et du lien passif. Les preuves physiques
20/21 pages et fonts/layout de M9-A/M8-S sont **héritées**, pas une nouvelle
campagne moteur ; leurs références exactes figurent au relevé. Les refus M10
sur manifeste altéré prouvent la frontière applicative, pas un export réellement
partiel ou divergent du renderer qualifié.

La réparation SQL héritée de M7/M9-A conserve sa réextraction de métadonnées
après un succès distant connu. Elle n'est pas la première validation du PDF :
l'extraction initiale précède le PUT. Sa preuve M10 injecte un rollback SQL,
puis vérifie une réparation sur GET sous nouvelle autorité, sans second PUT,
DELETE ou nouveau rendu. Aucun changement de ce mécanisme dans M10.

**Limite Chromium observée :** avec le nom Unicode `Étude-…pdf`, les octets et
l'en-tête serveur sont exacts, mais le navigateur du harnais propose `download`.
Un petit pair HTTP synthétique reproduit ce résultat avec le même en-tête pour
`application/pdf` et `application/octet-stream`, tandis qu'un nom ASCII est
conservé. L'en-tête est produit par le `send_file` préexistant inchangé : ce
comportement est requalifié hors delta PDF, cause navigateur précise inconnue.
La tentative d'attribut `download` sans effet a été retirée. La preuve navigateur
M10 porte donc sur un nom ASCII et un contenu accentué ; nom Unicode côté
serveur/identité prouvé, nom Unicode téléchargé et Safari matériel non validés.
Ce constat reste visible pour le contre-audit ; aucune fidélité navigateur
universelle revendiquée, aucun correctif opportuniste de téléchargement commun.
