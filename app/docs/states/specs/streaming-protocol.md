# Streaming Protocol

Statut: reference normative active
Classement: `app/docs/states/specs/`
Portee: contrat public du streaming de `/api/chat` quand `stream=true`
Roadmap archivee liee: `app/docs/todo-done/product/frida-response-streaming-todo.md`

## 1. Objet et perimetre

Cette spec decrit le protocole streaming reel de Frida tel qu'il est implemente aujourd'hui.

Elle couvre explicitement:
- le transport physique public actuel entre le serveur Frida et le navigateur;
- la grammaire logique minimale du flux;
- les invariants imposes par le wrapper serveur;
- les obligations minimales du frontend navigateur;
- la taxonomie minimale d'erreurs observable;
- la regle canonique de persistance des tours interrompus.

Elle ne couvre pas:
- le protocole amont du provider LLM;
- une cible SSE/WebSocket non implementee;
- une UX ideale future;
- les reponses JSON non-streaming, sauf quand elles partagent une metadata equivalente.

Point de frontiere important:
- le transport public Frida est `text/plain; charset=utf-8`;
- le flux SSE-like lu par `chat_llm_flow.py` chez le provider est un detail interne d'implementation, pas le protocole public documente ici.

## 2. Transport physique actuel

Le protocole public streaming de Frida repose aujourd'hui sur:
- une reponse HTTP `200`;
- un `Content-Type: text/plain; charset=utf-8`;
- un corps UTF-8 diffuse en chunks;
- un unique terminal de controle inline en fin de flux.

Headers pre-body actuels:
- `X-Conversation-Id`
- `X-Conversation-Created-At`

Header volontairement absent sur le chemin streaming public:
- `X-Conversation-Updated-At`

La date `updated_at` post-stream n'est donc pas un header pre-body dans le contrat streaming courant; elle est portee par la metadata terminale quand elle est connue.

Le terminal de controle utilise le format physique exact suivant:
- prefixe reserve `RS` (`0x1e`, `\x1e`);
- payload JSON UTF-8;
- suffixe `\n`.

Exemple nominal:

```text
Bonjour\x1e{"kind":"frida-stream-control","event":"done","updated_at":"2026-04-16T12:00:00Z"}\n
```

Exemple d'erreur:

```text
Segment partiel.\x1e{"kind":"frida-stream-control","event":"error","error_code":"upstream_error","updated_at":"2026-04-16T12:00:10Z"}\n
```

## 3. Grammaire logique minimale

### 3.1 Grammaire on-wire

```text
stream = *content terminal

content = chunk UTF-8 visible rendu a l'utilisateur

terminal = done-terminal / error-terminal

done-terminal = control-frame(event="done")
error-terminal = control-frame(event="error", error_code=...)

control-frame = RS json-object LF
json-object.kind = "frida-stream-control"
```

### 3.2 Evenement logique hors wire

Le protocole logique de l'experience streaming inclut aussi:
- `network_error`: interruption inferee cote frontend quand `fetch()`, `ReadableStream` ou le parseur local echoue avant la lecture d'un terminal valide.

`network_error` n'est pas un evenement backend emis dans le flux.

## 4. Terminal de controle

Le terminal de controle DOIT etre un JSON objet avec:
- `kind`: requis, valeur fixe `frida-stream-control`;
- `event`: requis, `done` ou `error`.

Champs optionnels:
- `error_code`: optionnel; utile seulement quand `event="error"`;
- `updated_at`: optionnel; timestamp ISO du tour persiste quand il est connu.

Contraintes:
- `done` et `error` sont mutuellement exclusifs;
- un `error_code` absent sur un terminal `error` reste defensivement acceptable cote parseur, mais le backend Frida courant vise un `error_code` explicite pour les terminaux d'erreur qu'il emet;
- `updated_at` appartient au terminal; il ne doit pas etre suppose disponible ailleurs dans le corps du stream.

## 5. Invariants

Les invariants suivants sont normatifs:
- le flux DOIT contenir au plus un terminal valide;
- aucun contenu visible ne DOIT suivre un terminal valide;
- le terminal valide DOIT etre le dernier element logique du flux;
- le controle ne DOIT jamais entrer dans la prose rendue a l'utilisateur;
- l'absence de terminal valide DOIT etre traitee comme une erreur protocolaire;
- `done` et `error` sont mutuellement exclusifs pour un meme flux;
- `updated_at` est une metadata terminale post-stream, pas un signal inline pre-body;
- le frontend ne DOIT pas inventer une cause plus precise que celle observable localement.

## 6. Taxonomie minimale d'erreurs

Codes emis ou propages canoniquement dans le flux/backend:
- `upstream_error`
  - sens: echec du provider LLM pendant la requete ou la lecture du stream amont;
  - famille frontend: `upstream_error`.
- `stream_finalize_error`
  - sens: echec local de finalisation apres reception du flux amont, ou exception locale du stream avant terminal cote wrapper serveur;
  - famille frontend: `server_error`.
- `stream_protocol_error`
  - sens: violation du contrat de terminal unique / terminal final / terminal present;
  - famille frontend: `server_error`.

Classifications defensives utiles, sans en faire de nouveaux statuts produit:
- `missing_stream_terminal`
  - cas: le flux se termine sans terminal valide;
  - emission publique actuelle: le wrapper serveur synthesize un terminal `error` avec `error_code="stream_protocol_error"`;
  - classification locale/logique: `missing_stream_terminal`.
- `multiple_stream_terminal`
  - cas: un second terminal valide apparait;
  - emission publique actuelle: famille `stream_protocol_error`;
  - classification locale/logique: `multiple_stream_terminal`.
- `content_after_stream_terminal`
  - cas: du contenu visible apparait apres un terminal valide;
  - emission publique actuelle: famille `stream_protocol_error`;
  - classification locale/logique: `content_after_stream_terminal`.
- `stream_terminal_error`
  - sens: classification defensive du wrapper/logs quand un terminal `error` a ete recu;
  - ce n'est pas le code canonique d'erreur metier a persister dans la conversation.

Inference frontend seulement:
- `network_error`
  - source: `fetch()`, `AbortError`, `TypeError`, rupture de lecture navigateur, etc.;
  - ce n'est pas un `error_code` backend emis dans le flux.

## 7. Comportement du wrapper serveur

Le wrapper serveur dans `app/server.py` a quatre obligations normatives:

### 7.1 Exposer le flux public Frida

Il DOIT:
- retourner une `Response` Flask `text/plain; charset=utf-8`;
- transmettre les headers de conversation streaming;
- relayer les chunks visibles;
- reconnaitre les terminaux via `parse_terminal_chunk()`.

### 7.2 Garantir les invariants de terminal

Il DOIT:
- refuser un second terminal valide;
- refuser du contenu apres terminal;
- synthétiser un terminal `error` si le flux s'arrete sans terminal;
- synthétiser un terminal `error` si le generateur leve avant terminal.

Syntheses publiques actuelles:
- fin sans terminal -> terminal `error` avec `error_code="stream_protocol_error"`;
- exception locale avant terminal -> terminal `error` avec `error_code="stream_finalize_error"` si aucun code plus precis n'est deja connu.

### 7.3 Porter l'observabilite de stream

Il DOIT renseigner l'observabilite de tour avec:
- `mode: "stream"`;
- `response_chars`;
- `stream_chunks`;
- `stream_terminal` quand un terminal a ete vu;
- `error_class` et `error_code` en cas d'erreur.

### 7.4 Ne pas redefinir la persistance canonique

Le wrapper serveur n'invente pas a lui seul la persistance du tour assistant.
La persistance canonique se fait en amont dans `chat_llm_flow.py`, puis le wrapper garantit seulement la sortie publique et les erreurs protocolaires de dernier mile.

## 8. Obligations frontend

Le frontend navigateur DOIT:
- appeler `/api/chat` avec `stream: true`;
- lire la reponse `text/plain` comme un `ReadableStream` UTF-8;
- parser le terminal via `createStreamControlParser()`;
- rendre les chunks `content` sans jamais afficher le terminal de controle;
- traiter `done` et `error` comme terminaux exclusifs;
- traiter l'absence de terminal, les terminaux multiples ou le contenu apres terminal comme erreurs protocolaires locales;
- utiliser `terminal.updated_at` quand il est present pour horodater le message assistant et le thread;
- forcer une rehydratation serveur si `updated_at` manque.

Interpretation frontend minimale actuelle:
- `request_started` -> etat `preparing`;
- `response_opened` -> etat `waiting_visible_content`;
- `visible_content` -> etat `streaming`;
- `terminal_done` -> etat `done`;
- `terminal_error` ou `network_error` -> etat `interrupted`.

Le frontend DOIT distinguer au moins:
- `upstream_error`;
- `server_error`;
- `network_error`.

Il ne DOIT PAS documenter ni afficher `network_error` comme si le backend l'avait emis.

Rehydratation:
- si un message persiste porte `meta.assistant_turn.status="interrupted"`, le frontend DOIT le rerendre comme une interruption visible;
- il ne DOIT PAS rerendre ce message comme une reponse assistant normale vide.

## 9. Metadata terminales et headers

Metadata terminales actuelles utiles:
- `event`
- `error_code`
- `updated_at`

Semantique de `updated_at`:
- sur `done`, il represente le timestamp canonique du tour assistant persiste;
- sur `error` emis par `chat_llm_flow.py`, il represente le timestamp du marqueur assistant interrompu persiste;
- sur les erreurs protocolaires synthétisees par le wrapper serveur, il peut legitiment manquer.

Relation headers / terminal:
- `X-Conversation-Id` et `X-Conversation-Created-At` sont disponibles avant le corps;
- `updated_at` pertinent pour la fin du stream vit dans le terminal;
- le frontend privilegie donc `terminal.updated_at` avant toute rehydratation forcee.

## 10. Regle de persistance

La regle canonique de persistance est la suivante:

### 10.1 `done`

Si le stream se termine en `done`:
- un vrai message assistant canonique est persiste avec le texte final normalise;
- ce message porte le timestamp `updated_at` du terminal;
- la conversation est sauvegardee avec ce meme `updated_at`;
- `save_new_traces()` peut ensuite persister ce contenu comme trace assistant.

### 10.2 `error`

Si le stream se termine en `error`:
- aucun fragment texte assistant n'est persiste comme reponse canonique complete;
- un message assistant marqueur est persiste avec:
  - `content=""`;
  - `meta.assistant_turn.status="interrupted"`;
  - `meta.assistant_turn.error_code=<code canonique>`;
  - `timestamp=updated_at` si connu.

### 10.3 Echec de finalisation

Si la finalisation locale casse apres un append assistant temporaire:
- le texte assistant appendu est rollbacke;
- le code canonique devient `stream_finalize_error`;
- le message persiste est le marqueur `assistant_turn` interrompu, jamais le fragment texte rollbacke.

### 10.4 Prompt et memoire

Les marqueurs `assistant_turn.status="interrupted"`:
- sont exclus de `build_prompt_messages()`;
- ne doivent pas etre relus comme reponse assistant canonique;
- ne sont jamais eligibles a `save_new_traces()`;
- ne doivent pas polluer la memoire derivee, meme lors d'un tour ulterieur.

## 11. Cas nominaux et cas d'erreur

### 11.1 Flux nominal

Sequence attendue:
1. contenu visible zero ou plusieurs fois;
2. terminal `done`;
3. persistance du message assistant complet;
4. `updated_at` exploitable cote frontend.

### 11.2 Erreur upstream mid-stream

Sequence attendue:
1. contenu visible eventuel deja recu;
2. terminal `error` avec `error_code="upstream_error"` et `updated_at` si la persistance du marqueur a reussi;
3. persistance d'un marqueur assistant interrompu sans texte partiel.

### 11.3 Erreur locale de finalisation

Sequence attendue:
1. contenu visible eventuel deja affiche au navigateur selon le mode de buffering;
2. aucun texte partiel n'est canonise en DB;
3. terminal `error` avec `error_code="stream_finalize_error"`;
4. persistance d'un marqueur assistant interrompu;
5. aucune trace memoire du fragment rollbacke.

### 11.4 Fin sans terminal

Sequence attendue:
1. le wrapper detecte l'absence de terminal;
2. il synthétise un terminal `error` avec `error_code="stream_protocol_error"`;
3. l'observabilite retient `error_class="missing_stream_terminal"`.

### 11.5 Coupure reseau navigateur

Sequence attendue:
1. le navigateur perd `fetch()` ou la lecture du `ReadableStream` avant terminal valide;
2. le frontend infere `network_error`;
3. aucun terminal backend supplementaire n'est invente localement;
4. la persistance canonique ne peut etre deduite du seul navigateur et doit, si necessaire, etre rehydratee depuis le serveur.

## 12. References code et tests

Code source-of-truth relu:
- `app/core/chat_stream_control.py`
- `app/core/chat_llm_flow.py`
- `app/server.py`
- `app/web/app.js`
- `app/core/assistant_turn_state.py`
- `app/core/conversations_prompt_window.py`
- `app/memory/memory_traces_summaries.py`

Tests de contrat relus:
- `app/tests/unit/chat/test_chat_stream_control.py`
- `app/tests/unit/chat/test_chat_llm_flow.py`
- `app/tests/test_server_phase14.py`
- `app/tests/test_server_logs_phase3.py`
- `app/tests/test_server_phase13.py`
- `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`
- `app/tests/unit/frontend_chat/test_stream_control_parser_module.js`
- `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`
- `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py`

## 13. Resume normatif court

Le protocole streaming public de Frida est aujourd'hui:
- un flux HTTP `text/plain`;
- du texte visible en clair;
- un terminal unique reserve `RS + JSON + LF`;
- `done` ou `error` comme seuls terminaux emis;
- `network_error` comme inference frontend, jamais comme terminal backend;
- `done` -> message assistant canonique complet;
- `error` -> marqueur `assistant_turn.status="interrupted"` sans texte partiel;
- aucun marqueur interrompu dans le prompt ni dans les traces memoire.
