# Atelier documentaire Frida V1 — contrat M4

Date : 2026-10-06. Statut : code et preuves hermétiques fermés ; livraison runtime ouverte.
Base exacte : correctif P3 `9f10531ae9c799f4afc769c97ea2d48659f1c3d3`, poussé
sur M3 et vérifié propre, HEAD = upstream = distant, divergence `0/0`, avant
création de `FridaV1-Document-Workshop-M4`. Le hash M4 et les contrôles du push
sont rapportés après livraison dans le retour final ; aucune fusion vers main.
Autorité : [roadmap](../../todo-todo/product/frida-v1-document-workshop-todo.md),
§§3.3–3.7, 3.10–3.16, 4–7 et M4 ; [M0](frida-v1-document-workshop-m0-contract.md),
[M1](frida-v1-document-workshop-m1-contract.md), [M2](frida-v1-document-workshop-m2-contract.md)
et [M3](frida-v1-document-workshop-m3-contract.md).

## Plan retenu et propriétaires

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de bord ? »
La préparation conserve le tour canonique et ses facultés. Elle remplace seulement
l'échange principal par un propriétaire documentaire distinct. M3 possède
l'exclusion/fencing et le snapshot, M2 la lecture fraîche, M0 le canonical,
l'admission et le lecteur provider. Le succès documentaire ne passe pas par le
final lock à sauvegarde paresseuse. Aucun second transcript ou framework de jobs.

Les étapes T1 enveloppe/Markdown, T2 HTTP, T3 autorité SQL/tour, T4 UI et T5
comparaison/revue ont été exécutées. Trois sous-lots indépendants ont traité
l'enveloppe, le transport et l'UI ; leurs auteurs ont relu les autres périmètres.
Les extractions répondent à ces responsabilités : `document_workshop_turn.py`,
`document_workshop_actions.py`, `document_workshop_http_transport.py`,
`document_workshop_envelope.py`, `document_markdown.py`. Le contrôleur navigateur
commun desktop/mobile et clair/sombre est conservé. Les fichiers historiques
longs restent propriétaires de leurs raccords ; aucun refactor cosmétique ajouté.

## Tour, facultés et admission

`submitCanonicalChatMessage` et `/api/chat` restent l'entrée unique, avec
`client_turn_id`, `document_context_id` et `document_source_file_ids` explicites.
Le serveur contrôle les identités, le contexte, la conversation/répertoire,
les sources et les modes. Clavier et dictée sont compatibles ; Dialogue est
bloqué dans l'atelier. Web, Agenda, Biblio, Notes, Adobe et images sont refusés,
sans retombée vers le chat normal ni nouvelle capacité vocale.

Le vrai user est sauvegardé une fois avec ses références avant l'appel.
Summary, Identity, Memory, Stimmung et herméneutique suivent les raccords du
tour existant. Les sources complètes M2 sont lues ensuite, uniquement sur IDs
mobilisés ; leurs textes sont données sans autorité dans le payload local.
L'adoption seule n'injecte rien. Aucun canonical, rendu ou JSON d'action n'entre
dans la conversation ou les facultés. Les effets après persistance reçoivent
seulement la vraie demande et la réponse courte.

Le nominal synthétique compte séparément **1 échange principal documentaire,
0 principal normal et 2 échanges constitutifs de validation** ; ce dernier
nombre décrit la fixture, pas un plafond universel d'agents. Aucun DAV mutateur.
Les étapes finies summary/identity/memory/Stimmung/herméneutique, sources et M0
renouvellent le progrès réel. GET/polling/keepalive/animation/lease ne le font pas.
L'inactivité est exactement 120 secondes, sans deadline totale ni TTL du pending.

OpenRouter conserve `openai/gpt-5.1`, sortie 24 000 et politiques reasoning
existantes. L'entrée complète, instructions d'enveloppe et capsule comprises,
est mesurée une fois par `token_utils.estimate_tokens` : E + 24 000 <= 400 000.
Aucun texte n'est ajouté ensuite ; le corps HTTP admis est transmis verbatim.
Échec/absence/type invalide du compteur : refus avant provider. Le budget normal
8 192 et ses overrides restent inchangés. Aucune réduction cachée d'une source.

## Enveloppe, transport et Markdown

Un seul schéma fermé remplace le canonical seul dans le builder et le lecteur M0.
`prepared` porte surface courte, create/copy Markdown, chemin Documents validé,
références autorisées, limites et canonical immuable. `clarify/refuse` portent
surface courte et proposal null : aucune révision ou proposition confirmable.
Toute sortie invalide échoue, sans réparation, second appel ou document partiel.

Le canonical reste borné à 10 000 mots/75 000 points de code et 1 048 576 octets
JSON. L'enveloppe vaut au plus 1 114 112 octets, la frame provider 6 750 208 octets,
la lecture HTTP cumulée 32 Mio et les headers 64 Kio. Ces plafonds techniques
laissent les bornes produit indépendantes. Le lecteur conserve stop/DONE,
modèle/usages/outils/troncature et refuse `length`, une fin manquante ou ambiguë.

Le transport asyncio/stdlib possède une connexion, TLS vérifié et framing
Content-Length/chunked/EOF. Aucun retry, redirect, fallback ou décompression.
L'annulation/inactivité abortent la socket réelle. La boucle du tour se ferme
sans attendre le DNS système bloqué ; sa reprise ne peut ouvrir de socket tardive.
Le DNS OS lui-même reste non interruptible. Les preuves distinctes JSON/SSE et
la composition `/api/chat` ont observé les octets reçus et EOF/reset effectifs.

Markdown est sérialisé directement depuis le canonical validé, avec échappements,
liens passifs, table à en-tête vide et `<!-- frida-page-break -->` pour le saut
logique. Pagination et certaines adjacences de styles dépendent du lecteur.
DOCX/PDF, Writer et update sont indisponibles. La surface refuse les objets JSON
canonical/envelope connus, même imbriqués, préfixés ou fenced, sans réécriture.
Ce garde structural ne prouve pas la conformité sémantique d'une prose arbitraire
produite par un modèle réel ; l'interdiction d'écho reste aussi portée par le prompt.

## Transactions et autorité durable

Migration explicite : `app/core/sql/document_workshop_actions.sql`, versionnée
malgré l'ignore général des SQL. Elle a été exécutée seulement en DB de preuve.
`document_artifacts`, `document_revisions`, `document_actions` restent séparés
de `workspace_files`. La révision et ses métadonnées sont immuables ; le SHA
canonical trie les clés JSON, stable après roundtrip JSONB, sans modifier les
chaînes ni l'ordre des blocs. Le SHA Markdown et le serializer sont figés.

L'identité d'action est celle du tour. Transaction initiale : contrôle claim/scope,
références, snapshot M3 du vrai user et action preparing. Échec : zéro provider.
La transaction finale contrôle propriétaire/génération/lease/scope/versions,
puis artefact/révision, supersession de l'ancien pending du contexte, snapshot
court, action et clôture du claim. Tout réussit ou rollback ensemble. Pour
clarify/refuse, réponse et clôture sont communes, sans artefact/révision artificiels.
Le pending libère la conversation ; aucun verrou DB n'est conservé pendant le réseau.

Commit précède le premier octet de réponse et l'unique done daté. La provenance
est `main_model` avec références, sans détour par final_lock. Une panne persiste
une courte interruption lorsque l'autorité et le stockage le permettent ; sinon
l'état interrompu/perdu est relisible. Répétition identique : relecture technique,
aucun replay ; réutilisation incompatible refusée, même après clôture du contexte.

Les triggers M3 et M4 synchronisent contexte/action après annulation ou mutation
locale pertinente de cible/répertoire/source. Les sources/version privées restent
figées ; les observations distantes sont celles de la lecture fraîche, pas une
surveillance permanente de Nextcloud. L'inventaire local détecte les collisions
NFC/casefold ; une image non mobilisée ne bloque pas une proposition Markdown.
Une vérification distante future appartient à l'exécution non livrée M5.

## Projection et frontend

Interfaces livrées : GET `/api/document-workshop/actions/<action_id>` et
POST `/api/document-workshop/actions/<action_id>/cancel`, corps fermé
`{"context_id":"<UUID>"}`. GET contexte projette la dernière action après validation
de scope ; le service de scope utilisé par M2 ne déclenche pas cette projection.
Le golden exact comprend **130 routes**, dont uniquement ces deux ajouts M4.
Aucune route de confirmation ou d'écriture.

Les projections publiques sont des whitelists : IDs, états, phases, mesures,
motifs, nom/chemin validé, format, opération, limites et capacités. Ni canonical,
versions privées, texte rendu ni exception. `confirm=false`, formats Markdown,
create/copy et `update=false`. Annulation idempotente vérifie le contexte SQL ;
un résultat tardif ne restaure aucune autorité. Pending sans expiration.

Cartes compactes uniques par références persistées, progression et annulation
fonctionnent dans les deux thèmes et les compositions desktop/phone. SessionStorage
conserve seulement les identités de tentative, jamais un document. Une tentative
absente/incertaine est relue sans inventer d'état SQL ni rejouer le POST. Une
relecture GET bloquée libère le garde du compositeur après le tour. Les listes,
upload, multisélection, drag-and-drop et corrections M2 restent éprouvés.
`document_preparation` a un schéma d'observabilité fermé, content-free par stage.

## Preuves et contre-audit

L'[artefact daté content-free](../baselines/document-workshop/frida-v1-document-workshop-m4-20261006.json)
porte les **sélecteurs exacts**, commandes Docker/env, comptes, exits/durées,
fixtures adaptées et échecs intermédiaires. Images et dépendances préexistantes,
`--pull=never`, env vidé, réseau extérieur fermé, checkout/rootfs read-only ;
PostgreSQL dédiés via sockets et données synthétiques. Aucune installation.

Baseline P3 figée rejouée : **840 = 377 Python + 82 PostgreSQL + 2 pgvector
+ 68 voisins + 207 Node + 104 Chromium**, exits 0, zéro skip. L'archive restaure
seulement le répertoire ignoré vide app/conv pour la fixture et monte les
node_modules existants read-only. L'échec global historique P3 reste historique.

Final unique : **1 198 = 739 Python + 121 PostgreSQL + 2 pgvector + 211 Node
+ 104 Chromium historiques + 21 Chromium M4**, tous verts, exits 0, zéro skip.
Les 121 SQL sont 82 historiques et 39 M4. Le run commun 118/118 puis le ciblé
39/39 se recouvrent : ne pas les additionner. Même règle pour 324/324, 89/89,
les 25 pannes SQL et le rejeu 8/8 des compteurs constitutifs.

Les preuves M4 couvrent prepared/clarify/refuse, user unique, source M2 complète
après facultés, sorties invalides sans fallback, rollback à chaque frontière
réellement atteinte par trigger SQL, connexions indépendantes, concurrence,
perte/scope/annulation, fin tardive, course commit, supersession atomique, relecture
sans retry, immutabilité, dates/provenance/terminal et autorité publique.
Les sockets ont été réellement consommées ; keepalives seuls ne renouvellent
pas l'horloge 120. Progression continue au-delà de 120 et frontière exacte testées.

La seconde lecture indépendante a fermé P2 DNS, P2 canonical JSON en surface,
P2 busy UI et P3 libellés techniques ; le contre-audit final a corrigé le refus
PNG non mobilisé et rétabli la propagation des interruptions de processus après
nettoyage de la réservation, sans assimiler celles-ci à une panne documentaire.
Aucun finding confirmé vivant dans ce delta. Les adaptations
static frontend renforcent la condition documentaire sans retirer les gardes
normales ; M2 scope/projection a été découplé après une régression reproduite.
Warnings DB/admin des fixtures minimales ne prouvent pas la santé du runtime.

## Frontières encore ouvertes

Migrations opérateur, rebuild/restart/déploiement, health et recette runtime,
provider/DAV live, matériel Safari, confirmation/exécution M5 et parcours M6
restent non livrés. Les preuves navigateur utilisent fetch simulé ; la composition
HTTP et SQL est synthétique isolée. Aucun reçu d'écriture ou succès Nextcloud
n'est annoncé. Les seules ressources temporaires du lot sont nettoyées avant
livraison ; la preuve durable ci-dessus conserve les résultats techniques.
