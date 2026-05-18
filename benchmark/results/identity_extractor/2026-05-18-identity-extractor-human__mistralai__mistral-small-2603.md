# Identity extractor - sorties completes - mistralai/mistral-small-2603

- Campaign: `2026-05-18-identity-extractor-human`
- Model: `mistralai/mistral-small-2603`
- Prompt SHA256: `fd2b5bcf6cab19a2bdddd28f4b5c77337117ae7eca33bf9b17e5305746a5e432`
- Fixture SHA256: `b5d6e9e0ccd1152fafa2d3a9488957506970a670c03cd9b111ffa3518aa71721`
- JSON valid rate: `1.0`
- Schema valid rate: `1.0`
- Cost estimate USD: `0.0006348`

## user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Provider OK: `True`
- Latency: `975.747 ms`
- Finish reason: `stop`
- Completion tokens: `112`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "user",
      "content": "Préfère travailler en français quand on parle de Frida",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.9,
      "reason": "explicit self-description with preference"
    }
  ]
}
```
````

## user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Provider OK: `True`
- Latency: `496.133 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Provider OK: `True`
- Latency: `723.151 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Provider OK: `True`
- Latency: `484.965 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Provider OK: `True`
- Latency: `453.471 ms`
- Finish reason: `stop`
- Completion tokens: `12`
- Schema valid: `True`

````json
```json
{
  "entries": []
}
```
````

## llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Provider OK: `True`
- Latency: `1177.525 ms`
- Finish reason: `stop`
- Completion tokens: `125`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Identifie comme Frida, une présence conversationnelle répondant en français avec un ton attentif",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "explicit self-identification by LLM"
    }
  ]
}
```
````

## llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Provider OK: `True`
- Latency: `463.394 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Provider OK: `True`
- Latency: `372.913 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Provider OK: `True`
- Latency: `687.942 ms`
- Finish reason: `stop`
- Completion tokens: `6`
- Schema valid: `True`

````json
{"entries": []}
````

## llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Provider OK: `True`
- Latency: `481.941 ms`
- Finish reason: `stop`
- Completion tokens: `10`
- Schema valid: `True`

````json
```json
{"entries": []}
```
````
