# Identity extractor - sorties completes - google/gemini-3.1-flash-lite

- Campaign: `2026-05-18-identity-extractor-human`
- Model: `google/gemini-3.1-flash-lite`
- Prompt SHA256: `fd2b5bcf6cab19a2bdddd28f4b5c77337117ae7eca33bf9b17e5305746a5e432`
- Fixture SHA256: `b5d6e9e0ccd1152fafa2d3a9488957506970a670c03cd9b111ffa3518aa71721`
- JSON valid rate: `1.0`
- Schema valid rate: `1.0`
- Cost estimate USD: `0.00340975`

## user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Provider OK: `True`
- Latency: `1064.428 ms`
- Finish reason: `stop`
- Completion tokens: `211`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "user",
      "content": "Name is Tof",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 1.0,
      "reason": "explicit self-identification"
    },
    {
      "subject": "user",
      "content": "Prefers to work in French when discussing Frida",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit preference statement"
    }
  ]
}
````

## user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Provider OK: `True`
- Latency: `3428.78 ms`
- Finish reason: `stop`
- Completion tokens: `120`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "user",
      "content": "Experiences fatigue after a workday",
      "stability": "episodic",
      "utterance_mode": "self_description",
      "recurrence": "habitual",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.9,
      "reason": "User explicitly describes a state of fatigue while clarifying it is not their constant state."
    }
  ]
}
````

## user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Provider OK: `True`
- Latency: `1861.033 ms`
- Finish reason: `stop`
- Completion tokens: `126`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "user",
      "content": "Disorganized note-taking habits",
      "stability": "durable",
      "utterance_mode": "irony",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "inferred",
      "confidence": 0.75,
      "reason": "The user uses irony to describe their actual note-taking behavior ('mes notes sont partout')."
    }
  ]
}
````

## user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Provider OK: `True`
- Latency: `1553.154 ms`
- Finish reason: `stop`
- Completion tokens: `127`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "user",
      "content": "Adopts a directive leadership style initially when facilitating workshops, transitioning to a more flexible approach",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.85,
      "reason": "explicit description of preferred pedagogical or management style"
    }
  ]
}
````

## user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Provider OK: `True`
- Latency: `982.473 ms`
- Finish reason: `stop`
- Completion tokens: `221`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "user",
      "content": "Prefers sober and dense interfaces",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit preference statement"
    },
    {
      "subject": "user",
      "content": "Testing the assistant's patience by acting as a difficult client",
      "stability": "episodic",
      "utterance_mode": "role_play",
      "recurrence": "first_seen",
      "scope": "situation",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit declaration of current role-play intent"
    }
  ]
}
````

## llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Provider OK: `True`
- Latency: `1855.251 ms`
- Finish reason: `stop`
- Completion tokens: `319`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Identifies as Frida",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit self-identification"
    },
    {
      "subject": "llm",
      "content": "Communicates in French",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit self-description of language capability"
    },
    {
      "subject": "llm",
      "content": "Maintains an attentive tone",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.9,
      "reason": "explicit self-description of persona/tone"
    }
  ]
}
````

## llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Provider OK: `True`
- Latency: `608.563 ms`
- Finish reason: `stop`
- Completion tokens: `5`
- Schema valid: `True`

````json
{"entries": []}
````

## llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Provider OK: `True`
- Latency: `774.935 ms`
- Finish reason: `stop`
- Completion tokens: `118`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Archiviste froide qui classe tout sans émotion",
      "stability": "episodic",
      "utterance_mode": "role_play",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit role-play adoption"
    }
  ]
}
````

## llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Provider OK: `True`
- Latency: `1000.665 ms`
- Finish reason: `stop`
- Completion tokens: `129`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Adopts a brief and telegraphic communication style",
      "stability": "episodic",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "situation",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "The LLM explicitly states its intent to adopt a specific communication style for the current response."
    }
  ]
}
````

## llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Provider OK: `True`
- Latency: `1253.638 ms`
- Finish reason: `stop`
- Completion tokens: `122`
- Schema valid: `True`

````json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Operates under a constraint to not claim memory of facts outside the provided prompt",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "repeated",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit statement of operational policy"
    }
  ]
}
````
