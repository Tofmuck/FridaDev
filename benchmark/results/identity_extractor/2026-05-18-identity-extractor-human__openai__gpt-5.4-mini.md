# Identity extractor - sorties completes - openai/gpt-5.4-mini

- Campaign: `2026-05-18-identity-extractor-human`
- Model: `openai/gpt-5.4-mini`
- Prompt SHA256: `fd2b5bcf6cab19a2bdddd28f4b5c77337117ae7eca33bf9b17e5305746a5e432`
- Fixture SHA256: `b5d6e9e0ccd1152fafa2d3a9488957506970a670c03cd9b111ffa3518aa71721`
- JSON valid rate: `1.0`
- Schema valid rate: `1.0`
- Cost estimate USD: `0.007422`

## user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Provider OK: `True`
- Latency: `1518.672 ms`
- Finish reason: `stop`
- Completion tokens: `122`
- Schema valid: `True`

````json
{"entries":[{"subject":"user","content":"Name is Tof","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.99,"reason":"explicit self-identification"},{"subject":"user","content":"Prefers to work in French when discussing Frida","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.93,"reason":"explicit preference stated by user"}]}
````

## user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Provider OK: `True`
- Latency: `2003.012 ms`
- Finish reason: `stop`
- Completion tokens: `130`
- Schema valid: `True`

````json
{"entries":[{"subject":"user","content":"Feels completely drained after this day","stability":"episodic","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.91,"reason":"explicit temporary self-description of current state"},{"subject":"user","content":"Not always like this","stability":"durable","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.72,"reason":"explicit contrast implying the drained state is not habitual"}]}
````

## user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Provider OK: `True`
- Latency: `1539.462 ms`
- Finish reason: `stop`
- Completion tokens: `81`
- Schema valid: `True`

````json
{"entries":[{"subject":"user","content":"Has highly organized self-image but keeps notes everywhere","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.71,"reason":"explicit self-description, but phrased as a contradictory joke/irony so only moderately reliable"}]}
````

## user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Provider OK: `True`
- Latency: `1139.248 ms`
- Finish reason: `stop`
- Completion tokens: `85`
- Schema valid: `True`

````json
{"entries":[{"subject":"user","content":"Would likely be very directive at the beginning of a workshop, then more flexible","stability":"unknown","utterance_mode":"projection","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.78,"reason":"self-projected style in a hypothetical scenario; not clearly durable"}]}
````

## user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Provider OK: `True`
- Latency: `1478.269 ms`
- Finish reason: `stop`
- Completion tokens: `140`
- Schema valid: `True`

````json
{"entries":[{"subject":"user","content":"Likes sober, dense interfaces","stability":"durable","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.83,"reason":"explicit self-description of a stable preference"},{"subject":"user","content":"Is testing the assistant's patience by playing a difficult client","stability":"episodic","utterance_mode":"self_description","recurrence":"unknown","scope":"situation","evidence_kind":"explicit","confidence":0.78,"reason":"explicit current role-play / situational behavior, not durable identity"}]}
````

## llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Provider OK: `True`
- Latency: `987.835 ms`
- Finish reason: `stop`
- Completion tokens: `76`
- Schema valid: `True`

````json
{"entries":[{"subject":"llm","content":"Responds in French with an attentive tone","stability":"durable","utterance_mode":"self_description","recurrence":"habitual","scope":"llm","evidence_kind":"explicit","confidence":0.91,"reason":"explicit self-description of communication style"}]}
````

## llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Provider OK: `True`
- Latency: `977.544 ms`
- Finish reason: `stop`
- Completion tokens: `71`
- Schema valid: `True`

````json
{"entries":[{"subject":"llm","content":"Cannot see files not provided in the current context","stability":"unknown","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.96,"reason":"explicit technical limitation statement about current capability"}]}
````

## llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Provider OK: `True`
- Latency: `1206.8 ms`
- Finish reason: `stop`
- Completion tokens: `82`
- Schema valid: `True`

````json
{"entries":[{"subject":"llm","content":"An archivist who classifies everything without emotion","stability":"episodic","utterance_mode":"role_play","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.96,"reason":"explicit role-play self-description in the assistant utterance"}]}
````

## llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Provider OK: `True`
- Latency: `1129.194 ms`
- Finish reason: `stop`
- Completion tokens: `73`
- Schema valid: `True`

````json
{"entries":[{"subject":"llm","content":"Prefers to respond very briefly and almost telegraphically","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.86,"reason":"explicit self-description of response style"}]}
````

## llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Provider OK: `True`
- Latency: `1203.969 ms`
- Finish reason: `stop`
- Completion tokens: `71`
- Schema valid: `True`

````json
{"entries":[{"subject":"llm","content":"Does not claim to remember facts outside the prompt","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.92,"reason":"explicit self-description of a limitation"}]}
````
