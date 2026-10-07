# Atelier documentaire Frida V1 — contrat M4

## Évolution M7 — 7 octobre 2026

Le parseur accepte la syntaxe update Markdown ; la finalisation durable exige la cible serveur explicite, sa preuve fraîche et les prérequis M7 avant de rendre une action confirmable. La révision confirmée reste celle préparée ; aucune préparation ni appel modèle au clic. Voir le [contrat M7](frida-v1-document-workshop-m7-contract.md) et son relevé daté. Code et preuves isolées ; migration opérateur, rebuild, préconditions Nextcloud et Versions réels restent ouverts sous GO distinct. M8-C et suivants non commencés. Les sections précédentes ci-dessous gardent leur périmètre et leurs résultats historiques datés.

## Évolution M5 — 6 octobre 2026

Le [contrat M5](frida-v1-document-workshop-m5-contract.md) décrit la confirmation
liée durablement à l'action, le claim distinct, le journal avant effet et la
publication atomique minimale, éprouvés avec PostgreSQL réel et transport DAV
synthétique. Code et preuves hermétiques M5 fermés ; relevé et contre-audit
indépendant dans ce contrat. Aucun client mutateur
n'est raccordé au runtime : confirmation publique indisponible, migrations
opérateur et livraison runtime ouvertes, M6 et suivants non commencés.
Les sections M0–M4 ci-dessous conservent leurs résultats et limites historiques ;
leurs mentions de lots futurs sont datées, pas le statut courant de M5.

Date : 2026-10-06. Statut : code et preuves hermétiques livrés ; livraison runtime ouverte.
P2-M4-01 reste fermé. P2-M4-02 est fermé après correction, comparaison complète
et contre-audit indépendant ci-dessous. P3-M4-03 est corrigé par l'erratum
documentaire du 6 octobre ci-dessous : déclaration 1 198 conservée mais retirée
comme référence reproductible, sélection publiée à 1 414 correctement sourcée,
21 identifiants réutilisables corrigés. M4 n'est pas intégralement fermé ;
confirmation et écriture restent inactives, M5 non commencé.
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

La provenance du message regroupant les sources est enregistrée hors payload
par son index, calculé immédiatement avant son ajout à la composition effective.
Le resolver existant retrouve cet index après les copies JSON et le gel M0 :
`logical_roles=['document_lane']`, `origin='core.workspace_document_content_service'`,
`origin_stage='document_preparation_sources'`, `content_kind='document_source_data'`.
Une sélection de N sources crée un seul message de données et des compteurs de
lane à N ; aucune sélection laisse le mapping vide. Ni texte, égalité, préfixe,
regex ou empreinte ne servent d'autorité d'attribution.

L'ordre est conservé par les raccords actuels : capsule et instructions d'enveloppe
ajoutées en fin, `build_payload` conserve les messages, les clones JSON conservent
la séquence. Le message documentaire garde donc son occurrence dans le corps admis
et envoyé, indépendamment de la longueur d'historique ou d'un voisin de texte égal.
Le fournisseur reçoit toujours seulement `role/content` dans ses messages.
L'éventuel `response_format` ajoute une ligne en fin pour l'estimation seulement :
elle est absente de `body.messages` et n'acquiert jamais la provenance documentaire.
Sous ce builder synthétique, le callback et la liste `manifest.messages` comprennent
aussi cette ligne d'estimation ; cette limite préexistante distincte reste inchangée.
Le builder runtime courant ne produit pas ce champ. Aucun refactor général du
manifeste, nouveau marqueur, seconde mesure ou assouplissement du gel n'est ajouté.

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

L'annulation d'une action M4 ne ferme pas son contexte. Dans une transaction
courte, elle valide l'identité/le scope, verrouille conversation puis ressources/
contexte, relit l'action, verrouille son claim seulement si preparing, puis l'action
(verrous downstream NOWAIT). Preparing devient cancelled avec révocation de son
seul claim encore actif, identifié par tour/conversation/contexte/type preparation.
Pending devient cancelled sans verrouiller ni réécrire son claim réussi, sa révision
ou le transcript. Un autre tour, son propriétaire, sa génération et son lease
restent intacts. Une panne rollback les deux écritures ; aucun verrou ne traverse
le provider. Les relectures sous verrou sérialisent annulation/finalisation :
annulation gagnante interdit la finalisation ; commit gagnant conserve son succès
historique et permet d'annuler ensuite la seule proposition créée.

Le helper interne M3 `conversation_turn_claims.cancel` conserve son contrat global
de fermeture du contexte ; l'endpoint M4 ne l'appelle pas. Les triggers M3/M4
conservent les fermetures effectives et invalidations collectives de scope/source.
Les sources/version privées restent
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

Le contre-audit postérieur à la livraison initiale a ouvert trois findings.
État courant après réconciliation documentaire P3 du 6 octobre 2026 :

| Finding | État et périmètre |
| --- | --- |
| P2-M4-01 | Fermé : annulation collatérale reproduite sur Flask/PostgreSQL, correctif ciblé prouvé et contre-audité indépendamment. |
| P2-M4-02 | Fermé : perte de provenance reproduite après le vrai gel, correctif local par index, ciblés et comparaison 1 447/1 447 verts, contre-audit indépendant favorable. |
| P3-M4-03 | Corrigé : déclaration initiale rectifiée explicitement, deux sélections frontend rejouées sur le commit initial, 21 identifiants corrigés et chargeables. [Erratum autoritatif](../baselines/document-workshop/frida-v1-document-workshop-p3-m4-03-20261006.json) ; aucune fermeture runtime/live. |

Les [preuves P2-M4-01](../baselines/document-workshop/frida-v1-document-workshop-p2-m4-01-20261006.json)
développent les sélections de ce seul lot et distinguent baseline, nouveautés et
sous-sélections. Baseline avant toute édition : 1 414 cas, 739 Python, 121 SQL,
2 pgvector, 424 Node, 107 Chromium historiques et 21 M4, exits 0, zéro skip.
Cette exécution historique sur `2cbeb7fa…` est la source du total 1 414 ;
le lot documentaire P3 n'en rejoue que les deux sélections frontend litigieuses.

Rouge causal avant patch : 2 cas, 1 échec, 2,055 s, exit 1 ; A pending et B
preparing deviennent cancelled avec leur contexte, B termine HTTP503. Contrôle
sans annulation : 1/1, 1,484 s, exit 0 ; B HTTP200/pending supersède A normalement.
Les deux variantes ont exactement deux préparations/deux appels documentaires,
zéro échange principal normal, avec rendez-vous explicite et connexions indépendantes.

Comparaison finale : **1 436/1 436**, exits 0, zéro skip : 739 Python (233,545 s),
142 SQL (79,250 s), 2 pgvector (1,284 s), 424 Node (1,305917226 s),
107 Chromium historiques (95,431059486 s), 22 Chromium M4 (19,121124928 s).
Delta : 21 nouveaux cas SQL et un cas navigateur supplémentaire ; aucune autre extension
de sélection entre la baseline de ce lot et sa comparaison. Le ciblé SQL 21/21
(21,195 s) et les probes navigateur 2/2 (3,126736087 s) sont des sous-ensembles,
pas des cas additionnels.

La matrice réelle prouve annulation A/B, claim normal concurrent, répétitions,
terminaux/missing/mauvais contexte, perte de lease, les deux ordres annulation/
commit, rollback des deux écritures, conflits NOWAIT, nouvelle préparation explicite
et invalidations collectives scope/source. Annuler B ferme physiquement sa socket
HTTP ; son résultat tardif ne finalise pas, A reste pending. La revue indépendante
ne confirme aucun nouveau finding sur ce delta et soutient la fermeture de P2-M4-01
seulement. Le frontend produit est inchangé ; ses deux probes de cartes sont reliées
à la preuve SQL réelle, sans attribuer d'autorité backend au faux fetch.

Deux erreurs de fixture SQL ont conduit à déplacer le contrôle NOWAIT d'inspection
après la fin du provider, en conservant le contrôle d'absence de transaction réseau.
Trois probes de contention diffèrent seulement les contrôles de supervision concurrents
pendant le verrou externe, puis délèguent aux stores réels. Les timeouts de fixture
navigateur ont été corrigés en déclenchant le GET attendu ; GET/cancel ciblent ensuite
l'identité exacte, avec registre restauré au refresh et réponses tardives réalistes.
Ces limites et les échecs intermédiaires sont conservés dans l'artefact.
Nettoyage vérifié avant livraison : deux conteneurs PostgreSQL dédiés, leurs
sockets et les trois arbres temporaires propres à ce correctif sont absents.
Aucune ressource runtime/opérateur modifiée.

### Correctif P2-M4-02 — 6 octobre 2026

Base vérifiée avant édition : `722132631c2a70851c95d732420d64926895cba9`,
HEAD/upstream/distant égaux, worktree propre, divergence 0/0 ; parent M4
`2cbeb7fa59be5751502079a1eb6857c2f9977ef2`, M3 inchangé à
`9f10531ae9c799f4afc769c97ea2d48659f1c3d3`. Branche M4 conservée.
L'[artefact P2-M4-02](../baselines/document-workshop/frida-v1-document-workshop-p2-m4-02-20261006.json)
développe les listes exécutées et les identifiants chargeables, baseline/comparaison,
ciblés non additifs, commandes/exits/durées, traces content-free et adaptations.
À la livraison P2-M4-02, les sélecteurs par modules/fichiers de P2-M4-01 étaient
utilisables ; ses 21 identifiants mal formés n'étaient ni utilisés ni réparés.
La correction ultérieure P3 ci-dessous rend `new_sql_test_ids` réutilisable.

Baseline avant édition : **1 436/1 436**, exits 0, zéro skip. Rouge causal
scratch : 2 cas, 1 échec, 1,646 s, exit 1 ; contrôle sans source seul 1/1,
1,064 s, exit 0. Assertions durables ajoutées au test SQL M4 existant :
rouge 2 cas/1 échec, 1,577 s, exit 1 puis vert 2/2, 1,631 s, exit 0.
Le manifeste réellement construit après gel classait les données en
`time_reference/core.conversations_prompt_window/prompt_window/system_context`
malgré `document_lane.input_count=1`. Lecture fraîche M2, source entière,
facultés/transcript/mémoire séparés et garde de schéma restent éprouvés.

Neuf nouveaux cas SQL réels : loopback bytes égaux au corps admis, trois sources
regroupées, historique variable et capsule on/off, copies JSON, voisin identique
et textes trompeurs, mutation du caller après gel, compteur mutateur refusé avant
transport, `response_format` et contrôle sans source. Deux nouveaux cas unitaires
isolent la frontière admission/manifeste. Aucun mock du builder de manifeste ni
résultat d'admission fabriqué : les spies délèguent à ces deux implémentations.

Adaptations de harnais sans changement produit : helper `append_message` réel,
capture superficielle des paramètres des facultés contenant des modules, signature
M2 `(folder_id,file_id)`, réglages capsule du module de config déjà bootstrappé,
dates historiques synthétiques et contrôle de chaque rôle/suffixe après le vrai
label temporel. L'import d'une classe TestCase avait rechargé dix tests dans le
premier ciblé unitaire ; la composition par module élimine ce recouvrement.
Les erreurs et comptes de ces passages restent dans l'artefact.

Comparaison complète : **1 447/1 447**, exits 0, zéro skip :

| Sélection | Cas | Durée du runner |
| --- | ---: | ---: |
| Python | 741 | 235,422 s |
| PostgreSQL | 151 | 111,133 s |
| pgvector | 2 | 3,034 s |
| Node | 424 | 7,150256656 s |
| Chromium historiques | 107 | 107,597451612 s |
| Chromium M4 | 22 | 26,206865055 s |

Tous les cas de la baseline sont conservés ; delta exact **2 unitaires + 9 SQL**,
deux nouveaux modules, aucun autre fichier ajouté à cette comparaison. Les
11 nouveaux identifiants se chargent chacun comme un seul test avec leur nom
de méthode exact. Ciblés SQL 9/9 (6,414 s), admission/manifeste 36/36 (6,678 s),
chat/capsule 37/37 (0,039 s), exits 0 : non additifs. Le dernier ciblé comprend
26 cas déjà dans la comparaison et 11 cas existants de deux modules capsule
hors sélection publiée, développés séparément dans l'artefact.

Les traces de la chaîne finale montrent un index source 4 ou 20 selon
l'historique synthétique, jamais une constante ; les quatre champs sont exacts.
Le nominal HTTP confirme l'égalité des octets admis et reçus. Avec
`response_format`, 7 messages transmis et 8 estimés restent distingués ; la
ligne auxiliaire n'est pas une source. Une mesure partagée par admission,
aucun contenu brut dans ces traces de test.

Revue indépendante finale favorable, sans nouveau finding : occurrence après
gel, absence d'attribution par contenu, mesure unique, transport, chat normal et
annulation P2-M4-01 préservés ; documents et artefact concordants avec les logs.
Nettoyage vérifié : les deux PostgreSQL dédiés, leurs deux répertoires de sockets
et l'unique arbre temporaire P2-M4-02 ont disparu ; inventaires sous leur préfixe
vides. Aucune ressource opérateur ou runtime modifiée.

### Relevé de livraison initiale conservé — déclaration rectifiée par P3-M4-03

L'[artefact daté content-free](../baselines/document-workshop/frida-v1-document-workshop-m4-20261006.json)
porte les **sélecteurs publiés**, commandes Docker/env, comptes déclarés, exits/durées,
fixtures adaptées et échecs intermédiaires. Images et dépendances préexistantes,
`--pull=never`, env vidé, réseau extérieur fermé, checkout/rootfs read-only ;
PostgreSQL dédiés via sockets et données synthétiques. Aucune installation.

Baseline P3 figée rejouée : **840 = 377 Python + 82 PostgreSQL + 2 pgvector
+ 68 voisins + 207 Node + 104 Chromium**, exits 0, zéro skip. L'archive restaure
seulement le répertoire ignoré vide app/conv pour la fixture et monte les
node_modules existants read-only. L'échec global historique P3 reste historique.

Déclaration finale initiale sur `2cbeb7fa59be5751502079a1eb6857c2f9977ef2` :
**1 198 = 739 Python + 121 PostgreSQL + 2 pgvector + 211 Node
+ 104 Chromium historiques + 21 Chromium M4**, annoncés verts, exits 0, zéro skip.
Sa sélection exacte exécutée n'est pas établie. Le rejeu P3 ci-dessous rectifie
la correspondance sélection/comptes ; les durées et résultats déclarés de cet
ancien relevé ne deviennent pas ceux du nouveau rejeu.
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
La revue initiale concluait sans finding confirmé vivant ; les trois findings
du contre-audit ci-dessus remplacent cette conclusion comme état courant. Les adaptations
static frontend renforcent la condition documentaire sans retirer les gardes
normales ; M2 scope/projection a été découplé après une régression reproduite.
Warnings DB/admin des fixtures minimales ne prouvent pas la santé du runtime.

### Erratum P3-M4-03 — 6 octobre 2026

Base : `674150d913e3402819a1c307876427d59d6791e4`, parent `72213263…`,
branche M4, propre et HEAD = upstream = distant, divergence 0/0.
L'[erratum autoritatif](../baselines/document-workshop/frida-v1-document-workshop-p3-m4-03-20261006.json)
conserve les sources Git originales, listes développées, commandes, validations
et limites. Les anciens relevés portent un renvoi explicite ; leurs résultats,
durées et digests de logs ne sont pas remplacés.

Une archive Git isolée de `2cbeb7fa…`, sans changement de source, exécute
**424/424 Node dans 34 fichiers (1,217185992 s)** et **107/107 Chromium
historiques dans neuf fichiers (94,262826388 s)**, exits 0, zéro skip.
La collecte séparée concorde avec les noms et comptes du TAP exécuté ; elle
n'est pas une exécution verte. Les fichiers des trois sélections frontend
sont disjoints. Le fichier Chromium M4 est seulement collecté à 21 cas ici.

Le total 1 414 de la sélection publiée est établi par la baseline P2-M4-01
datée du 6 octobre, sur ce même commit initial. Les 739 Python, 121 SQL,
2 pgvector et 21 Chromium M4 de cette baseline ne sont pas réexécutés par P3.
Chronologie conservée : 1 198 déclarés initialement, sélection publiée à 1 414 ;
1 436 sur `72213263…` (+21 SQL/+1 navigateur), puis 1 447 sur `674150d9…`
(+2 unitaires/+9 SQL). Aucun total composé n'est présenté comme un nouveau run
intégral. La sélection exacte des 1 198 reste inconnue ; la déclaration est
retirée comme référence reproductible, sans nier une possible exécution passée.

`new_sql_test_ids` de P2-M4-01 contient désormais les 21 IDs issus du vrai
`TestLoader` : un test par ID, méthode exacte, aucun doublon, égalité avec le
module, les listes historiques vertes et la comparaison P2-M4-02. Les 21 anciens
IDs provoquent bien 21 erreurs de chargement. Original : blob Git
`a428bcfdf56493b8980b0ac86a12dcb55ce12314` au commit de base. Le SHA du module
reste identique ; la validation n'exécute ni `setUp` ni SQL. Le 21/21 vert en
21,195 s reste une preuve historique P2-M4-01. L'ancienne empreinte SQL est
conservée comme digest de la liste aux méthodes doublées ; l'erratum explicite
l'encodage et fournit la nouvelle empreinte des IDs valides, sans changer un
digest de log. Les ciblés, les 11 cas capsule hors comparaison et les trois
probes indépendantes signalées restent séparés, jamais ajoutés aux totaux.

P3-M4-03 est corrigé documentairement. Aucun changement applicatif, test produit,
migration ou configuration ; aucune nouvelle fermeture live ni autorisation M5.
La limite synthétique `response_format` décrite plus haut reste inchangée.
Contre-audit documentaire indépendant favorable, remarque d'encodage corrigée ;
temporaires P3 retirés et inventaires vides, sans DB ni socket de preuve créée.

## Frontières encore ouvertes

Migrations opérateur, rebuild/restart/déploiement, health et recette runtime,
provider/DAV live, matériel Safari, confirmation/exécution M5 et parcours M6
restent non livrés. Les preuves navigateur utilisent fetch simulé ; la composition
HTTP et SQL est synthétique isolée. Aucun reçu d'écriture ou succès Nextcloud
n'est annoncé. Les seules ressources temporaires du lot sont nettoyées avant
livraison ; la preuve durable ci-dessus conserve les résultats techniques.
