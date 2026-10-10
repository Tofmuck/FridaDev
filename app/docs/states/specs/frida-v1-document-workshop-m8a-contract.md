# Atelier documentaire — adaptateur Writer M8-A

Date : 10 octobre 2026. Base exacte `6827cb50b5d1633875b9864513b30e5c99c94a5b`,
branche `FridaV1-Document-Workshop-M8-A`. Autorité : mandat de Tof, M8-A et §9
de la [roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md),
[protocole M8-C](frida-v1-document-workshop-m8c-contract.md). Lot interne ;
clôture globale et raccord runtime non revendiqués.

## Plan d'exécution borné

1. Baselines comparables : session/contrat/structure/Markdown/confirmation,
   puis confirmation/exécution/compensation/update sur PostgreSQL isolé.
2. Serveur synthétique HTTP Unix, rouges puis client standard AF_UNIX ;
   mêmes identités, framing M8-C et contrôles d'autorité pendant toute I/O.
3. Gel transactionnel interne lié à action/révision/claim, avant libération,
   sans changer le stockage des publications Markdown ni leurs gardes.
4. Entrelacements déterministes SQL/transport ; rendu compact avec liste par
   le client livré sur une instance isolée de l'image qualifiée, sans DAV/modèle.
5. Auto-audit, preuves compactes, remise Sauron, livraison Git puis arrêt pour
   contre-audit Codex. Aucun M9/M10, montage permanent ou redémarrage FridaDev.

## Frontières et configuration

`document_renderer_client.DocumentRendererClient(socket_path=...)` reçoit
exclusivement un chemin absolu de configuration de confiance.
`RenderingSession(client=..., expected_engine=...)` fige séparément les pins
attendus avant capabilities. Aucun pin appris du serveur, URL utilisateur,
TCP, redirection, retry, second moteur ou second validateur.

La session conserve l'identité du claim de confirmation et le hash complet de
requête. Une réponse POST perdue/tronquée autorise uniquement GET de cette
identité ; jamais un autre POST. État non prouvé/perdu : refus. Les contrôles
M3 et l'horloge monotone M8-C supervisent chaque attente d'I/O non bloquante.
120 secondes inclusives sans étape/bloc supplémentaire restent la borne
jusqu'après l'acquittement final ; polls, octets réseau et cleanup ne réarment
pas cette horloge. Aucune deadline murale tant que le progrès est utile.

La validation existante M8-C recalcule tailles/SHA, inspecte réellement DOCX/PDF
et contrôle identités/pages/profil/moteur/polices. La paire immutable et son
manifeste sont figés puis persistés sous autorité avant DELETE release. Un
snapshot durable n'est ni reçu ni preuve de libération ou publication. Seul
l'acquittement conforme suivi du dernier contrôle autorise `ReleasedRender`.
Échec avant tentative release : une seule annulation de meilleur effort,
bornée à une seconde réelle ; elle préserve l'erreur initiale. Après tentative
release : aucun second nettoyage. Chaque socket est fermé dans son propriétaire.

## Persistance interne

L'existant `document_revision_renders` est réservé à Markdown, avec une seule
entrée par révision et sans manifeste de paire. Il ne peut satisfaire cette
obligation sans modifier le contrat de publication M5/M7. La migration explicite
`document_renderer_m8a.sql` ajoute donc seulement un snapshot immutable interne
par action, lié à révision et confirmation, contenant les octets exacts de la
paire et du manifeste (BYTEA bornés). Le commit précède la libération ; aucun
fichier auxiliaire à compenser et aucune transaction pendant l'attente réseau.
Elle reste non appliquée à la DB opérateur. Aucune consommation publique ni
reprise/replay automatique depuis ce snapshot.

`render_confirmed` reste le seul raccord applicatif interne : vrai
`ConfirmedExecution`, garde M3/M5, session unique, persistance sous la même
autorité. La projection ne porte que la phase validée d'un progrès utile dans
le champ existant de l'action. Les erreurs renderer sont traduites dans les
codes applicatifs existants ; aucun contenu documentaire/exception transport
brute n'est ajouté aux projections ou logs.

## Remise à Sauron et limites

Socket durable futur hôte :
`/opt/platform/fridadev-app/writer-renderer/socket/renderer.sock`.
Chemin proposé côté application : `/run/writer/renderer.sock`, répertoire
socket partagé seulement ; pins complets opérateur montés en lecture seule,
par exemple `/run/writer-pins.json`, puis explicitement transmis à la session.
Aucun document partagé avec Writer. Sauron seul décide/livre montage et identité
runtime : accès au GID numérique 20000, socket 0660/répertoire 2770 ; la preuve
isolée emploie UID 20001/GID 20000 sans groupe supplémentaire. Ne pas élargir
les permissions du service durable ni contourner un refus du compte courant.

Image qualifiée, **config ID Docker** :
`sha256:f3067a8fa6787e72a81cd72f94eb276c3887adf2e7907331a79aec98ca1c1487`.
Le champ contractuel `engine.image_digest` désigne le **manifeste OCI local** :
`sha256:8737155ab4794d06077d796ec5d3406521790f289b87b4204490735907449bf3`.
Pins complets : runbook Sauron `/opt/platform/fridadev-app/writer-renderer/pins.json`,
lus seulement ; Writer 25.2.3.2/PyUNO 25.2.3.2, filtres et quatre Liberation
Serif/OFL-1.1. Aucune équivalence supposée entre ces deux identités d'image.

Le mandat présent n'autorise ni montage permanent, migration opérateur,
rebuild/restart FridaDev, ni activation DOCX/PDF. La preuve interne réelle
isolée est autorisée ; le raccord runtime permanent reste dépendant de Sauron.

## Preuves exécutées et auto-audit

Le [relevé compact](../baselines/document-workshop/frida-v1-document-workshop-m8a-20261010.json)
porte commandes, exits, durées, identifiants comparables et incidents. Baseline
91 unitaires/69 SQL ; 25 nouveaux IDs finalement verts (14 Unix/11 SQL),
80 voisins HTTP/provider/enveloppe/observabilité distincts. La comparaison SQL
initiale 79/80 est conservée : le détecteur causal M8-C supposait qu'enlever le
premier garde suffirait à traverser tout le rendu. Les nouveaux gardes SQL le
refusent plus tard. Le détecteur vérifie maintenant le submit prématuré en
gardant ces gardes actifs ; huit M8-C rejoués après cette adaptation, verts.
Les 185 IDs distincts comparés sont une **union de sélections**, aucun run
unique de 185 ni campagne intégrale revendiqué. Les 25 nouveaux sont également
rejoués ensemble après drainage déterministe des threads serveur.

Incidents de harnais conservés : première injection SQL bloquée par le trigger
immutable de révision (corruption ensuite injectée uniquement dans la fixture
isolée), attente erronée d'un HTTP non-200 sur fencing, et première invocation
du probe Writer privée de `-m` (exit 2, aucun contact renderer). Ces corrections
n'affaiblissent ni les invariants produit ni les assertions de non-mutation.
Le retour M5 `executing` d'un claim encore actif malgré une génération périmée
est un comportement hérité observé, distinct d'un succès : aucun bundle rendu,
journal ou reçu. Terminalité immédiate non promise, aucune correction M3/M5 ici.

La preuve réelle interne, depuis `probe_document_renderer_m8a`, passe en
6,129 s de commande (5,204 s internes) : liste ordonnée, une page, DOCX 8 313
octets/PDF 14 951 octets, paire durable identique et libération acquittée.
Confirmation et claim SQL réels ; aucun modèle ni DAV. L'image n'a pas été
reconstruite ; aucun document n'a été soumis au renderer durable. Après rendu,
répertoire jobs vide et aucun processus UNO/soffice ; les seules caches
fontconfig éphémères sont détruites avec l'instance de preuve.

| Point d'auto-audit | Preuve et limite |
| --- | --- |
| Transport consommé | Cinq endpoints sur vrai HTTP Unix, header de hash imposé par serveur, EOF exact. |
| Faux ready | Autre job/révision/hash, longueurs, pages, moteur/fonts, paire incomplète refusés avant gel/DAV. |
| Autorité tardive | Cancel/scope/lease/génération/révision pendant result bloqué ; fencing après DELETE avant ack, aucun retour de succès. |
| Ressources | Peer EOF après interruption, fermeture de chaque socket, drainage des threads ; cleanup borné unique et jamais répété après tentative release. |
| Tests permissifs | Garde initiale retirée dans le seul contrôle causal : submit interdit détecté ; nouveaux gardes SQL restent actifs. |
| Markdown | Succès avec table M8-A supprimée et renderer rendu inappelable ; ancien exécuteur et publication inchangés. |
| Mutation prématurée | Snapshots vérifiés depuis connexion indépendante avant ack ; tous les refus gardent PUT/MKCOL/journal/reçu à zéro. |

Restent hors preuve : montage/permissions dans le conteneur FridaDev durable,
migration opérateur, livraison runtime et contre-audit Codex M8-A. La paire
interne n'active aucun format ni reçu public. Streaming/upload/Exports/OCR et
frontend non modifiés ne sont pas rejoués ; aucun total historique réannoncé
comme nouvelle exécution. Une release perdue/refusée laisse honnêtement la
libération non prouvée ; le client ne recommence pas le DELETE.
