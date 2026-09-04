# FridaDev — pipeline runtime courant

Statut : **référence d'architecture active**

Dernière revalidation structurelle : **4 septembre 2026**

Portée : pipeline chat, composition du payload principal, final locks,
persistance canonique et surfaces qui en dépendent.

> **English scope.** This document maps the current FridaDev chat/runtime
> pipeline after the Lot 9 refactors. It records stable responsibilities,
> observable lane order, final-response arbitration, canonical persistence,
> and operator projections. Code and executable tests remain authoritative.

## Rôle du document

Cette cartographie répond à quatre questions :

1. où entre un tour et quelles gardes s'appliquent avant toute mutation ;
2. dans quel ordre les contextes et agents sont exécutés ou injectés ;
3. quand le modèle principal est appelé ou court-circuité ;
4. à quelle condition une réponse devient canonique et produit des dérivations.

Elle décrit les frontières actuelles, pas l'historique des refactors. Les
contrats normatifs restent dans `app/docs/states/specs/`; les preuves historiques
et roadmaps fermées restent dans `app/docs/todo-done/`.

## Schéma one-glance

```text
[Navigateur / app/web]
  |- message texte
  |- dictée optionnelle -> /api/chat/transcribe
  |- toggles explicites Web, Biblio, Agenda, Adobe
  |- documents actifs et images actives conversation-scoped
  |- répertoires, fichiers sélectionnés, Notes, Exports, Images durables
  v
[chat_transport_routes / POST /api/chat]
  |- begin_turn et enveloppe de transport
  |- classification finale ok / refused / error
  v
[Garde des prompts constitutifs]
  |- main_system et main_hermeneutical lisibles, décodables, non vides
  |- échec -> 503 critical_prompt_unavailable
  |- avant résolution de session, mutation, secret ou provider
  v
[chat_session_flow]
  |- validation message, conversation_id, input_mode, stream
  |- création ou rechargement de la conversation
  v
[Tour utilisateur]
  |- append utilisateur unique
  |- résumé éventuel du seul dialogue user/assistant
  |- ancrage temporel, identité et fenêtre récente
  v
[chat_memory_flow]
  |- retrieval Memory/RAG
  |- résumés parents et context hints
  |- pré-panier puis arbitrage
  |- traces finalement retenues
  |- lecture des context hints temporaires: nouvelles evidences subject=dialogue
     + anciennes evidences user compatibles jusqu'a expiration
  v
[Entrées runtime et agents]
  |- stimmung
  |- Web, ou no-op Web si Adobe est actif
  |- contexte Adobe HelpX si demandé
  |- Biblio + état conversationnel
  |- Agenda si activé, sinon résultat disabled observable
  |- nœud herméneutique primary -> validation
  v
[Base du prompt et gardes]
  |- système + contrat herméneutique + NOW + identité
  |- résumé actif + fenêtre récente + Memory/RAG
  |- jugement herméneutique validé
  |- gardes voix, identité directe, lecture/preuve Web et texte brut
  v
[Lectures explicites]
  |- documents actifs conversation-scoped
  |- fichiers workspace sélectionnés pour la conversation
  |- fusion dans une seule lecture documentaire
  |- Notes workspace demandées pour ce tour
  v
[chat_main_payload]
  |- construction de la base conversationnelle
  |- injection Web éventuelle
  |- lane Notes
  |- lane Documents (actifs + workspace sélectionnés)
  |- lane Biblio
  |- arbitrage final lock : Agenda > Biblio > présence
  |- lane Adobe
  |- Continuity Capsule unique et terminale si autorisée
  |- construction + émission de main_payload_manifest_v1 content-free
  v
[chat_llm_flow]
  |- final lock valide -> override local, aucun appel modèle principal
  |- sinon chat_llm_provider_exchange -> llm_client -> provider principal
  |- réponse non-stream ou stream text/plain
  v
[chat_assistant_finalization]
  |- sauvegarde assistant canonique unique sur succès
  |- marqueur interrompu sur erreur quand sa sauvegarde est prouvée
  |- aucun faux updated_at, aucun second save de compensation
  |- dérivations seulement après preuve positive de sauvegarde
  v
[Transport final et projections]
  |- JSON, ou chunks visibles + terminal RS/JSON/LF unique
  |- réhydratation de la conversation
  |- dashboard, log, Memory Admin, Hermeneutic Admin, Identity, Admin
```

## 1. Transport et gardes initiales

`app/server.py` compose l'application Flask et injecte ses dépendances dans les
routes extraites. `app/chat_transport_routes.py` porte `/api/chat`; il ouvre et
ferme le tour observable, délègue le travail à `core.chat_service.chat_response`
et adapte le résultat interne en réponse Flask.

Avant la résolution de la conversation, `chat_service` exige les deux prompts
constitutifs `main_system` et `main_hermeneutical`. Leur absence, leur encodage
invalide ou leur contenu vide produit `503 critical_prompt_unavailable`. Cette
barrière interdit toute création de conversation, mutation, résolution de
secret ou tentative provider.

`chat_session_flow` valide ensuite le message, l'identifiant de conversation,
le mode d'entrée et la demande de streaming. Il crée ou recharge la conversation
et expose les paramètres normalisés au coordinateur.

## 2. Tour utilisateur, résumé et contexte historique

Le message utilisateur est ajouté une fois à la conversation avec son mode
d'entrée éventuel. `maybe_summarize()` ne compte que les messages dialogiques
`user` et `assistant` éligibles : prompts, identité, Memory, Web, documents,
Notes, Biblio, Agenda et lanes système ne participent pas à son seuil.

Le coordinateur prépare ensuite :

- l'ancrage temporel du tour ;
- le bloc d'identité ;
- le résumé actif et la fenêtre récente ;
- les entrées structurées destinées au nœud herméneutique ;
- Memory/RAG via `chat_memory_flow`, avec retrieval, enrichissement, pré-panier,
  arbitrage, traces retenues et `context_hints`.

Un save intermédiaire peut matérialiser un résumé. Il ne crée pas de message
assistant et ne change pas la règle de canonisation finale.

Apres la sauvegarde assistant, deux chemins sans autorite partagee s'executent:

- la paire user/assistant complete traverse `dialogic_context_hint_extractor`
  (`openai/gpt-5.4-mini`, slot de compatibilite `identity_extractor_model`),
  puis les hints strictement valides `subject=dialogue` sont stockes comme
  evidences temporaires et bornes par age, confiance, nombre et budget tokens;
- la paire projetee pour Identity alimente le staging cinq paires, puis
  `mutable_identity_judge_v2_add_only` peut seul ecrire le canon mutable.

Le premier chemin n'appelle ni `add_identity`, ni la detection de conflits, ni
les politiques de promotion/defer legacy. Les donnees `identities`, evidences
`user/llm` et conflits anterieurs restent consultables comme historique.

## 3. Web, Adobe, Biblio, Agenda et herméneutique

L'ordre d'exécution courant dans `chat_service` est observable :

1. résolution de la demande Adobe ;
2. préparation Memory/RAG et Stimmung ;
3. résolution Web ; lorsque le mode Adobe est actif, la recherche Web générale
   est explicitement remplacée par un résultat `skipped_by_adobe` ;
4. lecture HelpX Adobe éventuelle ;
5. exécution Biblio et rattachement de son état conversationnel ;
6. exécution Agenda si activé, sinon émission d'un état disabled borné ;
7. nœud herméneutique `primary -> validation` avec les entrées du tour et la
   provenance Web structurée ; le primaire sépare le régime épistémique fondé
   sur les preuves de la directive d'énonciation dérivée de Stimmung ;
8. injection du jugement herméneutique et des gardes système ; une transition
   affective peut adapter la délicatesse ou le rythme, sans modifier la
   certitude, le régime de preuve ou la posture d'incertitude.

La décision produit ratifiée par 4C.4 est `keep_current_v2.3` : le bloc courant
de `chat_prompt_context.py` est conservé.
La candidate benchmark `surface_only_v1` a été rejetée sur GPT-5.1 et GPT-5.2,
reste inactive et n'est raccordée à aucun chemin runtime ou frontend.

Le contre-audit 4O.Z confirme aussi que `contradictoire` reste un vocabulaire
contractuel accepté sans producteur canonique actif dans le primaire courant.
Les seuls `source_conflicts` effectivement produits portent
`issue=review_required` : ils restent inspectables et peuvent accompagner une
clarification issue des signaux canoniques, sans imposer automatiquement
`contradictoire`, `arbitrage_requis`, `bloquante` ou `suspend`.

Biblio et Agenda conservent leurs propres contrats, outils et états. Ils ne sont
ni Memory, ni Summary, ni Identity, ni Web. Agenda conserve les confirmations
humaines requises pour toute mutation externe significative.

Le régime `presence` n'est autorisé que par un verdict herméneutique positif
`answer/presence`. Il produit exactement `...`, avec une méta serveur dédiée ;
il n'est jamais inféré par regex, fail-open ou simple absence de réponse.

## 4. Lectures documentaires

Après les gardes du prompt, le coordinateur lit séparément :

- les `active_document` temporaires de la conversation ;
- les `workspace_file` persistants explicitement sélectionnés pour cette
  conversation ;
- les Notes explicitement demandées pour le tour.

Documents actifs et fichiers workspace sont fusionnés dans une lecture commune,
puis admis ou exclus par la même lane documentaire. Un document est injecté
entier ou absent avec un reason code borné ; il n'est pas silencieusement
tronqué. Cette sélection ne le promeut pas en Memory, Identity, Summary ou
Biblio.

Les images actives suivent le même principe de rattachement conversationnel,
avec validation et limites multimodales propres. L'OCR des PDF scannés reste
synchrone et bornée selon le contrat des documents actifs ou du workspace ; ce
n'est ni une OCR générale ni un pipeline documentaire parallèle.

## 5. Composition du payload principal

`chat_main_payload.prepare_main_payload()` est l'unique frontière de composition
finale. À partir de la base créée par `conversations_prompt_window`, il applique
l'ordre tardif suivant :

1. contexte Web, seulement pour les activations `manual` ou `auto` effectives ;
2. lane Notes ;
3. lane Documents ;
4. lane Biblio ;
5. résolution des candidats de réponse finale ;
6. lane Adobe ;
7. Continuity Capsule.

Une lane inactive ou vide est un no-op : elle n'ajoute aucun message factice et
ne déplace pas les autres sources. Les ajouts sont suivis par références de
messages, puis décrits par rôle logique, origine, étape et nature de contenu.

### Final locks

Les seuls candidats actuels sont résolus dans cet ordre strict :

1. final lock Agenda ;
2. final lock Biblio ;
3. override de présence herméneutique.

Un lock n'est accepté que s'il est autorisé, déclaré `ok` et contient une
réponse non vide. Un candidat invalide ou non autorisé est ignoré sans devenir
un faux lock. Le candidat sélectionné conserve sa source, son reason code, sa
méta assistant et sa provenance observable.

Lorsqu'un final lock valide existe :

- la Continuity Capsule est contractuellement bypassée ;
- le modèle principal n'est pas appelé ;
- son secret, son URL finale et son transport ne sont pas résolus inutilement ;
- la réponse suit néanmoins la voie canonique ordinaire de persistance.

### Continuity Capsule et manifeste

Sans final lock, la Continuity Capsule est résolue depuis la configuration. Si
elle est activée et valide, elle est injectée une fois comme dernier message du
payload principal. Sa duplication, son déplacement ou son absence injustifiée
violent le contrat.

`main_payload_manifest_v1` est construit après les lanes et avant l'échange
LLM. Il décrit structurellement : sources logiques, statuts, compteurs, fenêtres,
mémoire, lanes, final lock, Capsule et paramètres bornés. Il reste content-free :
aucun prompt, query, URL sensible, document, note, secret, contenu Capsule,
réponse provider ou exception brute.

## 6. Échange LLM et identité stream/non-stream

`chat_llm_flow` reçoit un payload déjà préparé et un éventuel override.

- Avec override, il compose la réponse locale sans passer par le provider
  principal.
- Sans override, `chat_llm_provider_exchange` isole l'appel au modèle et
  `llm_client` résout la configuration runtime finale.

Le provider amont peut parler un flux de type SSE, mais le protocole public
Frida n'est pas du SSE navigateur. Le streaming public est `text/plain` : chunks
visibles, puis un seul terminal `RS + JSON + LF` portant `done` ou `error`.

Le transport non-stream renvoie une réponse JSON. Les deux transports partagent
les mêmes règles de final lock, de persistance, de provenance et d'effets
post-save. Aucun mode ne doit transformer une erreur en faux succès ni produire
deux terminaux.

## 7. Persistance canonique et effets dérivés

`chat_assistant_finalization` centralise la frontière de sauvegarde :

- le message utilisateur n'est ajouté qu'une fois ;
- un succès sauvegarde un seul message assistant complet ;
- un final lock est sauvegardé comme un assistant normal, avec sa méta ;
- un échec provider avant résultat ne crée pas de faux assistant réussi ;
- un stream partiel interrompu n'est pas canonisé comme réponse complète ;
- l'état assistant interrompu n'existe que si sa sauvegarde est prouvée ;
- un échec de persistance finale produit `conversation_persist_failed` sans
  faux `updated_at`, retry caché ou second assistant.

Dans la transaction du writer, l'upsert catalogue sérialise la conversation
par son verrou de ligne, puis les messages canoniques sont relus par `seq` sous
verrou. Un snapshot est accepté seulement si le canon est son préfixe exact par
rôle, contenu et timestamp. La seule exception de contenu est la projection
volatile placée au premier message : quand le canon et le snapshot portent tous
deux le rôle `system` à l'index `0`, son contenu augmenté (`NOW`, identité et
gardes du tour) peut être remplacé, tandis que son rôle, son timestamp et ses
métadonnées restent contrôlés selon leurs règles propres. Aucun autre message
`system` n'est exempté. Les
enrichissements monotones de `summarized_by`, `embedded` et `meta` sont
conservés ; une suppression, une divergence de contenu/ordre ou une metadata
incompatible déclenche le rollback du catalogue avec
`conversation_snapshot_conflict`. Aucune mutation catalog/messages n'est alors
committée. Le writer ne fusionne jamais deux branches dont l'ordre relatif
n'est pas prouvé.

Le renommage d'une conversation est une mutation ciblée du catalogue : il ne
charge ni ne réécrit les messages.

La sauvegarde canonique positive est la barrière commune aux dérivations : log
`AssistantText`, traces Memory, écritures Identity, réactivations et projections.
Chaque effet est tenté une fois et isolé. Sa panne après sauvegarde ne révoque
pas le succès canonique ; avant sauvegarde, aucun de ces effets finaux ne part.

Les messages interrompus sont exclus de la fenêtre de prompt et des dérivations
substantives. La présence dialogique sauvegardée reste dans l'histoire visible,
mais sa méta l'exclut des traces Memory et la projette comme non substantive aux
frontières Identity.

## 8. Réhydratation et observabilité

Le frontend n'infère la persistance que depuis un `updated_at` terminal prouvé.
En son absence, il réhydrate la conversation au lieu de prétendre qu'un texte
partiel est canonique. Les documents actifs et artefacts workspace sont relus
depuis leurs états serveur propres.

Le navigateur n'autorise qu'une soumission chat en vol. Un second submit est
ignoré avant lecture ou effacement du brouillon ; la fin nominale ou en erreur
libère le garde pour une nouvelle soumission.

Les surfaces opérateur lisent le runtime et ses dérivations ; elles ne forment
pas des pipelines concurrents :

- `/dashboard` : métriques longues, conversations et inspection traduite ;
- `/log` : timeline technique ;
- `/memory-admin` : read-model Memory/RAG ;
- `/hermeneutic-admin` : nœud herméneutique et projections associées ;
- `/identity` : identité canonique et gouvernance ;
- `/admin` : réglages runtime ;
- endpoints admin Biblio/Agenda : projections content-free dédiées.

Les manifestes, JSONL, dashboards et artefacts de preuve restent content-free
selon leurs contrats. Les logs privés identity/memory conservent la visibilité
explicitement décidée par l'opérateur, sans jamais autoriser un secret.

Les stages `primary_node` et `validation_agent`, le read-model de tour et les
deux surfaces `/log` et `/hermeneutic-admin` exposent la même séparation
content-free: effet, source et reason code épistémiques d'une part; effet,
source et reason code d'énonciation d'autre part. Les événements historiques
incomplets restent `unknown`; un fail-open n'est jamais requalifié en succès.

## 9. Pipelines adjacents

### Dictée

`chat_transcription_routes` reçoit un unique upload. Le navigateur ne découpe
pas l'audio : `MediaRecorder` produit un blob et une demande. Le corps HTTP, le
fichier, la normalisation et l'appel Whisper possèdent des bornes distinctes ;
une durée WebM inconnue impose une normalisation bornée, jamais un fallback brut
non vérifié.

### Atelier documentaire

Les routes `workspace_folder_*_routes.py` exposent les opérations sur dossiers,
fichiers, Notes, Exports et Images générées. Les services correspondants vivent
dans `core/`, utilisent des stores/read-models locaux et délèguent à Nextcloud
par des clients bornés. Une sélection de fichier ou de Note reste explicite et
conversation-scoped ; la simple présence d'un artefact dans un dossier ne
l'injecte pas dans le chat.

### Administration

Les routes admin sont enregistrées depuis `server.py` mais leurs décisions et
projections vivent dans `admin/` et `observability/`. Authelia et Caddy protègent
le hostname public hors de ce dépôt ; leur configuration appartient à la
plateforme.

## 10. Carte des responsabilités

| Frontière | Responsabilité actuelle |
| --- | --- |
| `app/server.py` | Composition Flask, bootstrap des stores, wiring des routes |
| `app/chat_*_routes.py` | Transport chat et transcription |
| `app/workspace_folder_*_routes.py` | Transport des artefacts workspace |
| `app/core/chat_service.py` | Coordination applicative du tour |
| `app/core/chat_session_flow.py` | Validation et résolution session/conversation |
| `app/core/chat_memory_flow.py` | Retrieval et arbitrage Memory/RAG |
| `app/core/chat_prompt_context.py` | Base système, jugement et gardes |
| `app/core/chat_document_prompt_reads.py` | Lecture et fusion documentaires |
| `app/core/chat_agent_lane_orchestration.py` | Observabilité agents et priorité des final locks |
| `app/core/chat_main_payload.py` | Lanes tardives, Capsule et manifeste |
| `app/core/chat_llm_flow.py` | Orchestration réponse, streaming, override et erreurs |
| `app/core/chat_llm_provider_exchange.py` | Échange avec le provider principal |
| `app/core/chat_assistant_finalization.py` | Persistance canonique et effets post-save |
| `app/agenda/`, `app/biblio/` | Domaines agentiques séparés |
| `app/memory/`, `app/identity/` | Mémoire et identité |
| `app/observability/` | Manifestes, événements et read-models |
| `app/admin/` | Services et routes opérateur applicatifs |
| `app/web/` | Chat et interfaces opérateur |

## Références vivantes

- `app/core/chat_service.py`
- `app/core/chat_main_payload.py`
- `app/core/chat_agent_lane_orchestration.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_llm_provider_exchange.py`
- `app/core/chat_assistant_finalization.py`
- `app/chat_transport_routes.py`
- `app/observability/main_payload_manifest.py`
- `app/docs/states/specs/frida-v1-continuity-payload-contract.md`
- `app/docs/states/specs/streaming-protocol.md`
- `app/docs/states/specs/active-conversation-documents-contract.md`
- `app/docs/states/specs/workspace-folders-contract.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-agenda-agent-contract.md`

Tests transversaux principaux :

- `app/tests/unit/golden/test_lot9_golden_harness.py`
- fixtures partagées sous `app/tests/support/`
- suites chat, streaming, persistance, Capsule/manifeste, Web, Documents, Notes,
  Agenda et Biblio sous `app/tests/`.

Toute modification future de l'ordre des lanes, de la priorité des final locks,
du contrat Capsule/manifeste, de la barrière de persistance ou de l'identité
stream/non-stream doit mettre à jour ce document dans le même lot.
