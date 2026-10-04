# Atelier documentaire Frida V1 — contrat interne M0

Date : 2026-10-04. Spécification autoritative :
[roadmap active](../../todo-todo/product/frida-v1-document-workshop-todo.md).
Ce contrat décrit les composants internes inactifs de M0. Il ne livre aucune
route, UI, transaction, écriture Nextcloud ou capacité de rendu.

## Responsabilités et appels

| Module dans `app/core/` | Frontière appelable |
| --- | --- |
| `document_workshop_contract.py` | Constantes, erreur content-free et `validate_writer_page_count`. |
| `document_canonical.py` | `validate_canonical`, `read_canonical_json` et snapshot immuable. |
| `document_workshop_admission.py` | `prepare_document_call`, corps provider figé et admission estimée. |
| `document_workshop_provider.py` | `prepare_and_read_document`, lecteur JSON/SSE et résultat typé. |
| `document_workshop_progress.py` | `DocumentPreparation`, annulation et surveillance monotone indépendante. |
| `workspace_document_paths.py` | `validate_document_path`, nom affiché, clé de collision et projection DAV pure. |

Les futurs lots consomment ces frontières. Aucun caller du chat normal, upload,
Exports, OCR ou des facultés n'est modifié. Aucun algorithme de comptage des
tokens ni transport HTTP concurrent n'est créé.

## Admission estimée et payload figé

Le recadrage explicite de Tof du 4 octobre 2026 remplace l'ancienne obligation
de décompte exact ou de borne fournisseur démontrée :

```text
E = core.token_utils.estimate_tokens(messages_finaux_et_adaptateur, modele)
estimated_input_tokens = E
estimated_total_tokens = E + 24_000
admission : estimated_total_tokens <= 400_000
```

Le callable partagé est injecté comme dans les composants de payload existants.
Il passe par `token_counter.estimate_message_tokens` et `estimate_text_tokens`.
Cette heuristique utilise actuellement des coefficients linguistiques, des
surcharges et une marge textuelle de 10 %, puis quatre unités par message et
deux au total. Le paramètre modèle n'influence pas son calcul. M0 ne copie ni
ne modifie cet algorithme, n'ajoute aucun tokenizer, coefficient ou marge de
framing et ne prétend pas mesurer exactement le contexte fournisseur.

Le caller fournit les messages finaux contenant prompt spécialisé, dialogue,
sources entières, contexte et métadonnées documentaires réellement injectées.
M0 n'en sélectionne ni n'en réduit aucune partie. Ses instructions de schéma
fermé sont ajoutées avant estimation. Le constructeur `llm_client.build_payload`
résout le modèle et le raisonnement par les frontières serveur actuelles.
Le modèle résolu doit être exactement `openai/gpt-5.1` via OpenRouter ; aucun
remplacement silencieux. Le corps JSON UTF-8 est figé avant estimation et
transport. Le compteur reçoit une copie ; sa mutation est refusée et les
mutations ultérieures du caller ne changent pas les octets admis.

Le champ modèle `response_format`, s'il est envoyé, est représenté par sa
sérialisation JSON dans un message système d'estimation seulement, avec le même
callable. Les autres champs inconnus, outils et contenus multimodaux sont
refusés. `metadata`/`trace` d'attribution existants, contrôles d'échantillonnage,
headers et secrets HTTP ne sont pas du texte de prompt ; les métadonnées
documentaires destinées au modèle doivent figurer dans les messages.

`max_tokens=24_000` couvre raisonnement et texte visible selon le contrat
OpenRouter Chat Completions ; `reasoning.exclude=true` masque le raisonnement
sans le rendre gratuit. L'effort résolu reste inchangé. Aucune seconde réserve
de raisonnement, aucun budget supplémentaire. Les 24 000 ne garantissent ni
24 000 tokens visibles ni les volumes maximaux du canonical. Le défaut normal
8 192 et les overrides normaux légitimes restent intacts.

Le compteur absent, en erreur, mutateur, ou retournant autre chose qu'un entier
strictement positif échoue fermé (`document_estimation_unavailable` ou
`document_estimation_input_mutated`). Le dépassement donne
`document_estimated_context_limit`, avant toute émission. Un refus local fait
zéro appel ; une admission autorise un seul `send`, sans retry, continuation,
réparation, boucle tools ou retour vers le chat normal. Le payload documentaire
porte `provider.allow_fallbacks=false`, sans changement du payload normal.
Un refus de contexte provider simulé termine en échec, sans document partiel.

Références primaires publiques, consultées sans API authentifiée :
[paramètres OpenRouter](https://openrouter.ai/docs/api_reference/parameters),
[raisonnement et max_tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens#reasoning-tokens-and-max_tokens),
[désactivation du fallback provider](https://openrouter.ai/docs/guides/routing/provider-selection).
Leur contrat documenté ne constitue pas une mesure live.

## Canonical, Unicode et pages

Racine fermée : `schema_version` entier 1, `profile="frida_document_v1"`,
`blocks` non vide. Blocs : `paragraph`/`quote` avec `spans`, `heading` avec
`level` entier 1–6 et `spans`, `list` avec `ordered` booléen et `items`, `table`
rectangulaire avec `rows`, `page_break` seul. Un span possède exactement
`text`, `bold`, `italic`, `link` ; texte non vide, styles booléens, lien nul ou
HTTP(S) absolu passif, sans credentials. Les cellules peuvent être vides.
Au moins un texte non blanc est requis. Aucun champ image, HTML actif, macro,
commande ou référence exécutable. Le texte reste une donnée, jamais du code.
Clés inconnues, doublons JSON, nombres non finis et schéma incorrect sont refusés.
Les branches prepared/clarify/refuse et leur action restent M4.

Les caractères sont les **points de code Unicode** comptés par `len(str)` Python,
sans normalisation. Un caractère hors BMP compte un point de code, deux unités
UTF-16 et quatre octets UTF-8 ; un accent combiné compte séparément de sa base,
même s'ils forment un seul graphème affiché. Les octets sont comptés par
`len(text.encode("utf-8"))`. Surrogates et contrôles sauf CR/LF/tab sont refusés.

Méthode de mots reproductible : suites des catégories Unicode lettres `L` et
nombres `N`, marques `M` attachées ; apostrophe ASCII ou courbe et tiret ASCII
internes joignent le mot si suivis d'une lettre ou d'un nombre. Espaces et autres
ponctuations séparent ; symboles/emoji et marques seules ne sont pas des mots.
Les spans adjacents d'un même titre/paragraphe/citation/élément/cellule sont
concaténés avant ce décompte. Chaque unité textuelle et chaque cible de lien est
comptée une fois ; aucun séparateur artificiel n'ajoute des caractères entre
blocs. Titres, listes, citations, tableaux, styles et liens n'échappent pas au
compte. Les tables ne fusionnent pas les mots de cellules distinctes.

Les deux plafonds simultanés sont 10 000 mots et 75 000 points de code ; tout
dépassement refuse sans réécrire, normaliser ou tronquer l'entrée. Le résultat
admissible contient un snapshot JSON immuable ; sa projection renvoie une copie.
La borne technique d'enveloppe canonical JSON UTF-8 est 1 048 576 octets,
déjà décidée en §9.3 de la roadmap : elle limite aussi la structure/sérialisation,
ne constitue ni une équivalence de volume ni une troncature.

Le profil est A4, corps 12 pt, interligne 1,5, marges 2,5 cm. Formats produit :
Markdown, DOCX et PDF. `validate_writer_page_count` exige un entier strict,
non booléen, de 1 à 20 lorsqu'une preuve binaire finale est demandée ; absent,
chaîne, flottant, booléen, compte nul/négatif ou >20 sont refusés. Ce garde ne
calcule pas les pages et ne certifie pas la provenance : M8–M10 fourniront
l'observation Writer finale liée aux octets/révision. Aucun docProps, saut déclaré
ou ratio mots/pages n'est une preuve. Markdown n'a pas de pagination stable.
Une source de plus de 20 pages est admise entière si l'estimation d'entrée tient.

## Lecture, progression et transport injecté

`DocumentProviderResult` ne contient que canonical validé, état `complete`,
`finish_reason`, modèle et `ProviderUsage` rapporté, facultatif. Les compteurs
prompt/completion/total réutilisent l'extraction existante de `llm_client` ;
`reasoning_tokens` est un compteur, jamais le raisonnement brut. Un compteur
absent reste absent, sans reconstruction depuis l'estimation. Types invalides,
usage de sortie >24 000 ou contexte rapporté/déductible >400 000 sont refusés.
Prompt seul, prompt + completion disponibles et total sont contrôlés même
si le total manque ou est incohérent. Reasoning étant inclus dans completion,
le maximum des deux compteurs est une borne partielle, jamais leur somme.
Cette vérification n'invente pas de `total_tokens` rapporté absent et ne rend
pas l'admission rétroactivement exacte.

JSON non streamé : une seule réponse, un choix, texte canonical intégral,
`finish_reason=stop` et modèle compatibles requis. SSE : lignes réellement
consommées, données multi-lignes jointes selon SSE, contenu accumulé dans la
borne technique ; une fin `stop`, puis `[DONE]`, est requise. `[DONE]` seul,
fin manquante, longueur dépassée même avec JSON complet, contenu après fin,
erreur/refus, outils, JSON/canonical invalides et contenu vide sont refusés.
Les champs de raisonnement sont retirés avant usage ; aucun log ou persistence
de contenu n'est ajouté, aucun traitement de bulle chat ne répare le canonical.

`DocumentPreparation` commence à sa construction, avant fabrication du payload.
L'horloge est monotone et injectable. Étapes finies, ordonnées et non répétables :
payload figé, admission achevée, terminaison provider prouvée, canonical validé.
Seul contenu provider non vide accepté par le lecteur, ou étape réellement
achevée, réarme l'inactivité. Les contrôles SSE, keepalives, chunks vides et
raisonnement brut ne le font pas. Les snapshots sont content-free.

À **120 secondes** depuis le dernier progrès, état d'échec irréversible. Une
tâche de surveillance indépendante du `send`/read agit pendant leurs attentes
bloquées ; la consommation SSE cède aussi au superviseur même sous flot continu
de contrôles. Les étapes synchrones sont contrôlées avant/après. Aucune deadline
de durée totale : le progrès utile peut maintenir la préparation au-delà de
120 secondes. L'annulation interne réveille le superviseur. Un résultat tardif
est neutralisé par l'état terminal, y compris si la lecture ignore sa cancellation.

Le transport **injecté**, possédé par un appel, expose `send` async,
`read_json` async, `iter_lines` async et `close` synchrone prompt/non bloquant,
qui doit interrompre une attente en cours. Il envoie le corps figé verbatim,
sans retry. Il est fermé sur succès, refus, erreur ou annulation ; le succès
n'est publié qu'après libération et contrôle de l'état. Aucun adaptateur HTTP
réel n'est livré par M0 ; M4 devra prouver ces obligations sur son adaptateur.
Les fixtures M0 simulent réellement la consommation, les attentes et la fermeture.
Ce composant n'est ni un pending, ni un TTL, une lease ou un claim durable.

## Cible et représentation relative

La représentation validée, comptée et affichée est exactement
`Documents/<sous-répertoires>/<nom.extension>`, séparateurs `/` inclus, relative
au répertoire Frida sélectionné. Maximum huit niveaux sous Documents ; chaque
segment, nom complet et extension compris : 180 points de code **et** 255 octets
UTF-8. Le chemin entier, préfixe `Documents/` inclus, est limité à 1 024 octets.

Refus par segment : vide, `.`/`..`, absolu, contrôle/catégorie Unicode `C`,
séparateurs Unicode `Zl`/`Zp`, séparateur direct/déguisé (dont U+2216 et U+29F9),
séquence `%HH` encodée, caractères réservés,
espaces de bord, point final et ambiguïté de compatibilité Unicode
(`NFKC(segment) != NFC(segment)`). Les accents français composés ou décomposés
restent admis et inchangés. Aucun basename, trim, raccourcissement ou renommage.
Clé de collision explicite : `NFC(chemin_relatif).casefold()` ; elle n'est jamais
le nom affiché ni une preuve de collision distante.

La projection encode séparément les segments originaux avec `quote(..., safe="")`.
`dav_segments` préfixe uniquement le mapping de dossier fourni par le serveur ;
racine DAV et utilisateur restent à la frontière du client Nextcloud existant.
Aucun préfixe Documents n'est retiré pour faire passer la borne. Cette projection
pure ne contacte pas DAV et n'accorde aucune autorité d'écriture. Le
[contrat M2](frida-v1-document-workshop-m2-contract.md) raccorde la lecture DAV
conditionnelle et les collisions d'adoption ; créations/écritures restent M5/M7.

Depuis M2, `validate_document_collection_path` et `validate_document_source_path`
partagent ces mêmes gardes : une collection `Documents[/sous-répertoire]` n'exige
aucune extension fictive ; une source accepte TXT/MD/MARKDOWN/DOCX/ODT/PDF.
`validate_document_path` reste limité aux formats produit Markdown/DOCX/PDF.
Ces extractions ne changent ni les comptes, ni les bornes, ni l'admission M0.

## Preuves et portée

Les commandes, comptes RED/GREEN, baseline et contre-audit sont dans la section
M0 de la même roadmap. Les tests sont hermétiques : image existante, réseau
coupé, checkout/rootfs read-only, environnement vide avec valeurs synthétiques,
temporaires en tmpfs et aucun bytecode. Aucun téléchargement ou dépendance ajoutée.
Les tests simulés ne prouvent aucun comportement fournisseur, DAV ou Writer live.
