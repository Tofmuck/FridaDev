# M9-A — diagnostic du rejet d'enveloppe et garanties OpenRouter

11 octobre 2026. Celebrimbor. **Diagnostic sans correctif ; règle historique
exacte inconnue. OBS-M9A-PREP-01 et M9-A restent ouverts.**

## Mandat, base et attribution

Travail direct dans `/opt/platform/fridadev`, `pwd` et racine Git concordants.
Branche `FridaV1-Document-Workshop-M9-A`, upstream
`origin/FridaV1-Document-Workshop-M9-A`. Départ propre ; HEAD, upstream et
`git ls-remote origin refs/heads/FridaV1-Document-Workshop-M9-A` donnent
`a0970c02fd80723c15db326d5f47d82cb064d2a6`. Aucune autre branche utilisée.
Seule la roadmap diffère depuis le code runtime
`8088571296a81f5182ce60448ed366ee49450524`.

Image active relue :
`sha256:5d28d36f50006d37710a51022e6166e24a179973ec451af3808df958aaa52d06`,
conteneur applicatif running/healthy. Comparaison SHA-256 runtime/commit/checkout :
15 fichiers identiques, aucun écart. Propriétaires : `server.py`,
`chat_transport_routes.py`, puis dans `core/` : `conversations_prompt_window`,
`chat_service`, `llm_client`, `main_llm_reasoning`, `document_canonical` et
`document_workshop_{provider,envelope,http_transport,turn,progress,actions,admission,contract}`.

Le **contre-audit runtime favorable de duplicate_stop** et l'unique nouvelle
préparation Safari sont attribués à **Codex, transmis par Tof** dans le mandat.
Le rapport local Codex n'est pas présenté comme lu. Aucun nouvel envoi après
l'échec, aucun job/worker Writer selon ce constat Codex ; aucun job déclenché ici.
Les deux premiers échecs restent ceux des
[relevés précédents](../baselines/document-workshop/frida-v1-document-workshop-obs-m9a-duplicate-stop-20261011.json),
sans attribution rétroactive du nouveau rejet.

Corrélation fournie par Codex et relue en SQL `READ ONLY` :

| Identité / observation | Résultat |
| --- | --- |
| Conversation | `db03bc08-faa1-44ae-8eea-90e526528fe4` |
| Répertoire canari | `fb9b4690-eacf-4ef8-b974-f2c6b0ae0792` |
| Contexte | `e5e02c23-a2c8-49d2-979d-04b190e71421` |
| Action | `bdb3bc4c-0dd2-4e62-b9a9-784359e9ad8b` |
| Tour | `turn-f3ff770b-0669-4154-9623-420c7d2ce10d` |
| Création / échec, UTC | `15:44:26.787` / `15:44:46.993963` ; soit 17:44 à Paris |
| Action / contenu compté | `failed/failed`, `document_envelope_invalid`, 1 510 points de code |
| Claim | `failed`, outcome `interrupted`, génération 3, terminé à `15:44:46.995479Z` |
| Tour journalisé | 20 370 ms ; 27 événements ; aucun champ `sse_rejection` |
| Révision / confirmation | ID de révision, tour/date de confirmation nuls |
| Effets durables | 0 reçu, snapshot et journal d'exécution pour l'action ; 0 révision et fichier dans le répertoire |

Safari interrompu/échoué et absence de fichier distant : observations Codex.
La vérification locale du nombre de fichiers porte sur l'inventaire SQL,
**sans lecture DAV**. Le message assistant associé est uniquement le message
fixe d'échec du code, pas les 1 510 caractères du modèle.
La demande synthétique rapportée par Codex visait un create DOCX avec titre,
paragraphe gras/italique, liste et tableau ; aucun contenu de réponse n'est
reconstruit à partir de cette demande.

## Localisation certaine et limite historique

Le seul émetteur de `document_envelope_invalid` est
[`document_workshop_envelope.py`, l.27–28](../../../core/document_workshop_envelope.py#L27).
La chaîne réelle est la suivante :

| Frontière | Propriétaire et effet vérifiés |
| --- | --- |
| Instructions / assemblage | [`document_workshop_turn.py`, l.178–247](../../../core/document_workshop_turn.py#L178) : dialogue/facultés existants, instruction documentaire, contexte/capacités serveur, éventuelles sources, reçus, capsule. Puis instruction d'enveloppe ajoutée par l'admission. Aucun ancien schéma canonical racine ajouté à ce chemin. |
| Builder réellement câblé | [`server.py`, l.25, 550–614](../../../server.py#L550) et [`chat_transport_routes.py`, l.55–70](../../../chat_transport_routes.py#L55) : proxy vers `core.llm_client`, émission de métadonnées puis retour du même payload, sans ajout de format de sortie. |
| Gel / admission | [`document_workshop_admission.py`, l.79–127](../../../core/document_workshop_admission.py#L79) : builder, contrôles modèle/sortie/reasoning, ajout local `provider`, sérialisation compacte en bytes, mesure et gel ; aucun texte ajouté ensuite au corps. |
| HTTP | [`document_workshop_http_transport.py`, l.81–143](../../../core/document_workshop_http_transport.py#L81) : POST, Content-Length calculé sur ces bytes ; `write(prepared.body)` sans reconstruction, une connexion, aucun retry. |
| SSE | [`document_workshop_provider.py`, l.193–284](../../../core/document_workshop_provider.py#L193) : framing puis parsing des **trames provider**, contrôle modèle/usages/refus/outils/terminaison, accumulation intacte des chaînes `delta.content`. |
| Enveloppe / canonical | [`provider`, l.151–162](../../../core/document_workshop_provider.py#L151) puis [`envelope`, l.123–160](../../../core/document_workshop_envelope.py#L123) : à DONE, stop/modèle/contenu requis ; parsing strict du texte complet, structure et gardes d'enveloppe, chemin, sources, limitations, enfin canonical. |
| Échec durable | [`turn`, l.283–297](../../../core/document_workshop_turn.py#L283), [`actions`, l.225–235](../../../core/document_workshop_actions.py#L225) : raison conservée, message fixe et claim terminé. La création de révision dans `actions.finalize` n'est pas atteinte. |

Avec ce wiring `stream=True`, l'atteinte du validateur implique stop et DONE
**par déduction du code**, pas par capture des trames. Aucun second stop n'est
prouvé pour ce nouvel essai. L'absence de `sse_rejection` est cohérente : son
émission est réservée à `document_provider_incomplete`.

Les classes de rejet ne sont pas interchangeables :

- **Parsing** : JSON tronqué/invalide, fences/prose, constantes non finies et
  clés dupliquées à toute profondeur sont refusés par
  [`strict_json_loads`, l.19–34](../../../core/document_canonical.py#L19), puis
  requalifiés en `document_envelope_invalid`. Un doublon à l'intérieur du
  canonical entre donc encore dans cette classe d'enveloppe.
- **Structure d'enveloppe** : objet racine et proposition à clés exactement
  requises, types stricts, version, status/opération/format, proposition nulle
  pour clarify/refuse : même code. Du JSON syntaxiquement valide peut échouer.
- **Gardes locales d'enveloppe** : surface vide, contrôles Unicode, JSON de
  protocole dans la surface, UUID invalides/équivalents dupliqués, copie sans
  source, limitations inconnues ou répétées : même code (l.37–95, 155–157).
- **Autres contrats** : chemin refusé → `document_path_*` ; forme du canonical
  après parsing → `document_canonical_invalid` ; volumes → codes dédiés.
  Capacité, fraîcheur, ownership et cible sont ensuite revalidés côté serveur.
  Ces codes ne sont pas rabattus sur le rejet observé. Un tableau mal formé
  après parsing strict n'est donc pas, à lui seul, une explication de ce code.

La réponse exacte n'a été trouvée ni dans les événements du tour (aucun champ
de contenu/réponse brute), ni dans les messages de conversation associés,
ni dans les logs consultés. Fenêtre Docker `15:44:25Z–15:44:49Z` : 66 lignes,
36 corrélées, aucun marqueur `surface_text`, `response_format`, `finish_reason`,
DONE, duplicate_stop, génération provider ou traceback. Les 15 fichiers de
logs montés n'ont aucune ligne avec l'action ou le tour. Aucun contenu brut
exporté ; pas de recherche dans un compte provider, dump mémoire ou nouvelle
capture. Cette absence est bornée aux stores et traces examinés.

**La première règle rejetée reste inconnue.** Les traces des facultés du même
tour ne sont pas des réponses du principal documentaire. Les champs provider
du manifeste désignent OpenRouter, pas le fournisseur sous-jacent.

## Requête réellement construite, sans messages privés

Sources : [`llm_client.py`, l.117–120, 234–235, 441–473](../../../core/llm_client.py#L454),
[`main_llm_reasoning.py`, l.42–79](../../../core/main_llm_reasoning.py#L42),
[`chat_service.py`, l.591–595](../../../core/chat_service.py#L591), admission ci-dessus.

| Champ | Chemin courant reconstitué | Preuve historique disponible |
| --- | --- | --- |
| Endpoint | `https://openrouter.ai/api/v1/chat/completions`, base du réglage serveur + suffixe | Base actuelle égale à l'URL publique standard ; pas de capture HTTP historique |
| Modèle | réglage `openai/gpt-5.1`, vérifié par admission | `prompt_prepared` et manifeste concordants |
| Streaming | `stream:true`, `stream_options.include_usage:true` | manifeste `stream_requested:true` ; options exactes déduites du builder |
| Format contraint | **aucun `response_format`, aucun JSON Schema, aucun `strict`** | absence établie dans le builder/proxy actifs, pas par corps historique capturé |
| Provider | `{"allow_fallbacks":false}` ; ni `require_parameters`, ni `order`, ni `only` | ajout de l'admission avant gel ; fournisseur historique inconnu |
| Reasoning | `{"effort":"high","exclude":true}` | effort high et hidden=true dans `prompt_prepared` ; réglage courant concordant |
| Sampling / stop | `temperature:0.7`, `top_p:1.0`, `stop:["<\u007cendoftext\u007c>","<\u007creturn\u007c>","<\u007ccall\u007c>"]` (séparateurs échappés ici pour le tableau Markdown) | manifeste atteste leur présence pour sampling, pas leurs valeurs ; valeurs actuelles et code relus |
| Budget | `max_tokens:24000`, contrat contexte 400 000 | max_tokens=24 000 dans le manifeste ; calcul et décisions de budget non rouverts |
| Autres | `messages`, `metadata`, `trace` ; pas de tools, plugins, retry ou réparation | attribution statique ; aucun message/header privé reproduit |

Réglages SQL actuels non secrets : modèle/base/reasoning/température d'origine
`admin_ui`, top_p d'origine `db_seed` ; date de ligne antérieure au canari.
Cela soutient la reconstitution, sans transformer le réglage actuel en capture
historique. Le manifeste conserve 16 messages, sans leurs contenus.

La [limite M4](../specs/frida-v1-document-workshop-m4-contract.md#tour-facultés-et-admission)
reste exactement celle documentée : `response_format`, **si fourni par un builder
synthétique**, est conservé dans le corps et représenté par une ligne auxiliaire
d'estimation, absente des messages HTTP. Cette capacité/fixture ne prouve aucune
présence dans l'appel produit. Ici le builder ne le produit pas ; cette limite
ne peut donc pas être affirmée causale. Le proxy ne l'ajoute pas non plus.

Confrontation des instructions statiques au validateur : les quatre clés racine,
six clés de proposition, enums M9-A, codes de limitations, spans fermés,
structures de liste/tableau et absence de fence sont bien décrits
(`envelope`, l.165–208 ; `turn`, l.19–36). Aucune contradiction exigeant un format
que le validateur refuse n'est établie. La description emploie des formes
abrégées, pas un JSON Schema exécutable : leur respect n'est pas garanti.
Elle ne détaille pas toutes les gardes Unicode, la non-vacuité des tableaux
de spans hors cellules, ni l'exigence globale d'un texte non blanc dans le
canonical. Ce sont des omissions vérifiables de précision, **pas la cause du
canari** ; les deux dernières relèvent d'ailleurs de `document_canonical_invalid`.
Les tests de surface avec prose/JSON ordinaire et refus de protocole ne
montrent pas de garde incorrecte. Sans réponse exacte, une mauvaise sortie,
une interprétation des formes abrégées ou un faux positif sur cette sortie
restent des hypothèses ; le dialogue privé complet n'a pas été reconstitué.

## Prescriptions officielles confrontées au code

Pages consultées le **11 octobre 2026** ; dates de consultation, pas versions
du routage historique. Sources primaires seulement. OpenRouter Chat Completions
reste la référence ; aucun SDK/API/modèle/provider alternatif préconisé.

| Prescription, URL et section (consultation 11/10/2026) | Code / lignes | Conformité, écart ou inconnue → conséquence |
| --- | --- | --- |
| [Parameters — Response Format](https://openrouter.ai/docs/api_reference/parameters#response-format) : `json_object` demande du JSON valide, accompagné d'une consigne JSON | `llm_client.py` 454–473 ; `envelope.py` 165–208 | Consigne textuelle seule ; aucune garantie JSON demandée à l'API. JSON valide ne suffirait pas aux clés/types/relations locales. |
| [Structured Outputs — Using / Best Practices](https://openrouter.ai/docs/guides/features/structured-outputs#using-structured-outputs) : `response_format.type=json_schema`, schéma et `strict:true` ; contrainte exacte sur endpoints à strict natif, application variable ailleurs | `admission.py` 19–22, 80–102 ; `envelope.py` 136–158 | Schéma absent. La promesse est celle du schéma envoyé et du support effectif, jamais de toute la validité métier. |
| [Provider Routing — Requiring Providers / Default parameter preferences](https://openrouter.ai/docs/guides/routing/provider-selection#requiring-providers-to-support-all-parameters) : `require_parameters:true` filtre les routes ; défaut false, paramètres inconnus ignorables | `admission.py` 91–94 | `allow_fallbacks:false` seulement : empêche le secours, pas la sélection initiale ni l'ignorance d'un paramètre. La préférence souple pour response_format ne vaut pas ce filtre. |
| [GPT‑5.1 — FAQ support/providers](https://openrouter.ai/openai/gpt-5.1) et [catalogue public des endpoints](https://openrouter.ai/api/v1/models/openai/gpt-5.1/endpoints) | `llm_client.py` 441–473 ; `provider.py` 73–79 | Modèle annoncé compatible ; endpoint historique inconnu. Le préfixe `openai/` identifie le modèle, pas son hébergeur. |
| [OpenAI — Supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) ; [Azure — JSON Schema support and limitations](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs#json-schema-support-and-limitations) | `envelope.py` 136–158 ; `canonical.py` 122–180 | Objets fermés, requis/nullables et unions imbriquées nécessaires ; restrictions différentes, voir ci-dessous. Aucun schéma effectivement soumis à qualifier ici. |
| [Structured Outputs — Streaming](https://openrouter.ai/docs/guides/features/structured-outputs#streaming-with-structured-outputs) ; [Streaming — final usage chunk / errors](https://openrouter.ai/docs/api_reference/streaming#the-final-usage-chunk-chat-completions) | `provider.py` 151–162, 225–284 | Streaming compatible ; accumulation puis validation complète au terminal. SSE terminé ≠ JSON valide ≠ schéma conforme ≠ action autorisée. Le correctif de comptage est indépendant de ce nouveau rejet. |
| [Response Healing — How it works / Limitations](https://openrouter.ai/docs/guides/features/plugins/response-healing#how-it-works) : réparation opt-in, json_object/json_schema, non-streaming seulement, pas toute troncature réparable | `admission.py` 19–22 ; `provider.py` 294–338 ; contrat M4 | Aucun plugin. Réparation changerait les données acceptées ; retry/fallback ajouterait un échange contraire au contrat. Aucun activé. |

Le GET public sans Authorization du catalogue, à `16:00:20Z` (18:00:20 Paris),
HTTP 200, annonce cinq endpoints : `openai/flex`, `azure`, `openai`,
`azure/swedencentral`, `openai/fast`. Tous listent `response_format` et
`structured_outputs`. Les trois OpenAI listent `max_tokens`, les deux Azure
`max_completion_tokens`. Aucun ne liste `temperature`, `top_p` ou `stop`.
Ce sont des **capacités déclarées actuelles**, pas une trace d'ignorance ni de
traduction lors du canari. L'ajout aveugle de `require_parameters` à notre corps
entier n'est donc pas une correction démontrée ; son admissibilité doit être
qualifiée. Aucune clé du compte utilisée, aucune génération.

`require_parameters` ne fabrique pas un schéma absent et ne garantit pas une
implémentation native : OpenRouter indique que certains providers traduisent
le schéma ou le traitent comme une indication forte. Par défaut, une préférence
pour `response_format` choisit les endpoints compatibles lorsqu'ils existent ;
si aucun ne le supporte, le modèle peut rester candidat et le paramètre être
ignoré. Les réglages de compte/routage passé ne sont pas connus ici.

### Schéma, canonical et divergences utiles

Les documentations OpenAI/Azure sont pertinentes parce que ces fournisseurs
sont annoncés au catalogue, sans être attribués au canari. Azure précise
explicitement que ses limites concernent Chat Completions **et** Responses.
Les exemples Responses (`text.format`, événements `response.*`) ne sont pas
transposés à notre corps OpenRouter `response_format` ni à son SSE.

Un schéma de la forme actuelle aurait une racine objet fermée, chaque champ
requis ; `proposal` resterait objet ou null, `link` chaîne ou null. Les variantes
de blocs demanderaient des unions `anyOf` **imbriquées**, pas un `anyOf` racine.
La relation status/proposal reste à contrôler localement si elle n'est pas
exprimable dans le sous-ensemble admis ; rendre tous les champs de toutes les
variantes présents avec null contredirait nos blocs fermés.

Divergences publiées : OpenAI annonce 5 000 propriétés/10 niveaux ; Azure
100 propriétés/5 niveaux. Azure exclut notamment min/maxLength, pattern/format,
minimum/maximum, min/maxItems et uniqueItems ; OpenAI présente certaines de
ces exclusions seulement pour modèles fine-tunés, mais exclut notamment
`allOf`, `not`, `if/then/else`. Ne pas amalgamer ces listes. Notre canonical
est fini : racine → proposition → canonical → bloc → span représente cinq
objets imbriqués ; en comptant les arrays de tableau, le trajet comporte neuf
conteneurs. La convention de profondeur et l'acceptation d'un schéma concret
sur chaque endpoint restent à qualifier, pas à déclarer incompatibles sans
schéma ni appel. Elles ne peuvent expliquer un rejet de schéma historique
puisqu'aucun schéma n'est envoyé.

Autre écart précis : [JSON Schema — integer](https://json-schema.org/understanding-json-schema/reference/numeric#integer)
considère `1.0` comme entier ; nos tests Python de type exact (`envelope` l.137,
`canonical` l.124, 139) le refuseraient après `json.loads`. C'est une analyse
statique d'une cause possible, pas une observation du canari ni une raison
d'assouplir la garde. La forme du schéma ne remplace donc pas ces contrôles.

Restent locaux : doublons au parsing, Unicode autorisé, surface sans fuite de
protocole, UUID normalisés uniques et sélection autorisée, codes uniques,
chemins sûrs, table rectangulaire, contenu non blanc, volumes agrégés, droits,
fraîcheur et confirmation ; pagination Writer seulement après confirmation.
La vérité et l'adéquation du document à la demande ne sont pas une garantie
de schéma. Refus, filtre, limite de génération, coupure et erreurs HTTP/SSE
restent possibles ; le lecteur doit refuser toute sortie incomplète avant
persistance, même avec structured outputs.

La page OpenRouter Structured Outputs formule d'abord une garantie générale,
puis la restreint dans Best Practices selon l'endpoint : retenir cette réserve.
Sa section Healing cite json_schema ; la page dédiée précise aussi json_object
(différence de portée, pas preuve d'exclusivité). Aucun de ces écarts
documentaires n'établit la cause passée.

## Preuves exécutées et commandes

Une seule sélection des runners existants, aucune fixture historique modifiée,
aucune suite générale, aucune répétition jusqu'au vert. Image de preuve déjà
présente : `fridadev-audit-py:latest`, ID
`sha256:486a8afeb2f62c7906194d3e1fee839387e55753bcad365120d18306502fafdc`.

```bash
docker run --rm --pull=never --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro \
  -w /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest \
  -i PATH=/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/workspace/app:/workspace EMBED_BASE_URL=https://embed.invalid \
  CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid \
  python -m unittest tests.unit.core.test_document_workshop_envelope \
  tests.unit.core.test_document_workshop_canonical_paths \
  tests.unit.core.test_document_workshop_admission \
  tests.unit.core.test_document_workshop_provider_progress \
  tests.unit.core.test_document_workshop_http_transport \
  tests.unit.core.test_document_workshop_final_usage
```

**115/115, 9,792 s, exit 0, aucun skip.** Les vrais validateurs distinguent
nominal, JSON syntaxiquement invalide, JSON valide à clés/types/limitations
incorrects et canonical invalide. Admission testée avec le vrai builder et
réglages synthétiques ; variante response_format explicitement injectée dans
son test. Transport HTTP loopback réel : corps figé, terminaux, fermeture et
refus ; nominal et variante usage finale. Ces résultats ne reproduisent
**pas** le canari. Aucun besoin de sonde supplémentaire : ces variantes
existantes départagent déjà l'hypothèse « ce code prouve une syntaxe invalide ».

Lectures serveur via `docker exec -i -e PYTHONDONTWRITEBYTECODE=1
platform-fridadev python -`, connexion existante
`core.document_workshop_execution_store._db_conn`. Chaque bloc SQL débute par
`SET TRANSACTION READ ONLY` et contrôle `SHOW transaction_read_only` → `on`.
Requêtes paramétrées, projections uniquement :

```sql
SELECT id, context_id, conversation_id, state, phase, reason_code,
       received_content_codepoints, revision_id, confirmation_turn_id,
       confirmed_at, created_at, updated_at
FROM document_actions WHERE id=%s::uuid AND conversation_id=%s::uuid;
SELECT turn_id, kind, state, outcome, reason_code, generation, created_at, finished_at
FROM conversation_turn_claims WHERE turn_id=%s::uuid AND conversation_id=%s::uuid;
SELECT ts, stage, status, duration_ms, payload_json
FROM observability.chat_log_events WHERE conversation_id=%s AND turn_id=%s
ORDER BY ts,event_id;
SELECT role,content,meta FROM conversation_messages
WHERE conversation_id=%s::uuid AND meta->>'client_turn_id'=%s ORDER BY seq;
SELECT updated_at,payload->'model',payload->'base_url',payload->'reasoning_effort',
       payload->'temperature',payload->'top_p'
FROM runtime_settings WHERE section='main_model';
```

Les valeurs de contenu restent en mémoire du processus de lecture : seuls
types, tailles, égalité au message fixe, présence de champs et métadonnées
autorisées sont imprimés. Counts ciblés sur `action_id` pour receipts/journal/
snapshots ; jointure revisions/artifacts et workspace_files sur le répertoire.
Schémas découverts par `information_schema.columns`, pas de SELECT de secrets.
La base URL est projetée uniquement par égalité à la base publique standard.
Logs Docker lus avec `subprocess.run(..., capture_output=True)` sur la fenêtre
ci-dessus, filtrés en mémoire par identités, seuls comptes/marqueurs imprimés.
Hashes de fichiers lus par `Path.read_bytes` dans le conteneur et comparés au
`git show 80885712…:<chemin>` et au checkout, sans import applicatif pour ce contrôle.

Recherche Web : `open` des six URL imposées puis sections pertinentes ; GET
public du catalogue via `urllib.request` sans Authorization ; sources primaires
OpenAI/Azure/JSON Schema limitées aux restrictions ci-dessus. Incident de lecture :
la variante `.md` du guide OpenAI renvoie une erreur interne de l'outil ; guide
HTML et sections lus avec succès. Quelques recherches exploratoires de noms de
fichiers inexistants ont été remplacées par les propriétaires réels ; sorties
de lectures trop longues tronquées, sections utiles relues. Aucun incident de
test/SQL, aucun écart de baseline, aucun résultat manquant utilisé comme preuve.

## Recommandation minimale et arrêt

**Avons-nous identifié la règle exacte rejetée ? Non.** Le validateur est
localisé, mais son reason_code fusionne plusieurs règles ; aucun artefact
existant consulté ne permet d'en choisir une honnêtement.

**Notre requête demande-t-elle réellement la garantie exigée ? Non.** Elle
décrit la structure en texte, sans garantie API JSON/schema. C'est un écart
établi du mécanisme de production face au validateur, pas une preuve que son
absence explique cet incident ni qu'un schéma supprimerait les refus métier.

**Prochaine action justifiée : un micro-lot distinct de diagnostic borné**, à
autoriser avant toute reprise. Le seul discriminant supplémentaire nécessaire
est **l'identifiant fermé de la première règle locale qui rejette l'enveloppe,
parsing inclus, corrélé au tour/action**. Ni exception libre, clé inconnue,
valeur, extrait ni réponse brute. Un booléen JSON valide serait insuffisant.
Il permettrait de distinguer syntaxe, clés/types et gardes sans modifier le
résultat du validateur. Non implémenté ici, aucun canari autorisé par ce relevé.
Il ne récupérera pas rétroactivement cette règle : pour ce tour passé, il
faudrait la réponse exacte de provenance prouvée, qui manque dans les traces
consultées. À défaut, conserver explicitement l'inconnue historique.

Un éventuel lot de correction du **contrat de sortie** devra ensuite qualifier
le sous-ensemble schéma réellement supporté et l'admissibilité des paramètres
sur OpenRouter, avant d'envisager json_schema/strict/require_parameters ; garder
toutes les validations locales et l'échange unique. Ne pas commencer par
json_object seul, réparation automatique, retry/fallback, changement de modèle,
provider/API/SDK ou budgets. Aucun correctif prescrit comme remède causal certain.

Auto-audit : aucun produit, prompt, paramètre, schéma, garde, test historique,
fixture commune ou instrumentation persistante modifié ; aucun secret, message
privé ou document brut dans l'artefact ; aucune preuve inventée. Zéro appel
modèle/DAV, écriture SQL opérateur, confirmation, job Writer, migration,
installation, rebuild/restart ou déploiement. Historiques conservés. Livraison
Git documentaire seule, arrêt pour contre-audit Codex ; M9-B/M10 hors périmètre.

Contrôle documentaire avant commit : quatre fichiers autorisés (ce relevé,
contrat M9-A, roadmap et entrée existante du hub), 52 liens locaux ajoutés ou
portés par les lignes modifiées et 15 ancres de lignes vérifiés. Six relevés
historiques M9-A inchangés par SHA-256 ; références locales et distantes
inchangées avant commit ; `git diff --check` vert. Alignement après push et
nettoyage des seuls temporaires de comparaison à vérifier dans le retour Git.
