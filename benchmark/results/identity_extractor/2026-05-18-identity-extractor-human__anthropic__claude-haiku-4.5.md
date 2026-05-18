# Identity extractor - sorties completes - anthropic/claude-haiku-4.5

- Campaign: `2026-05-18-identity-extractor-human`
- Model: `anthropic/claude-haiku-4.5`
- Prompt SHA256: `fd2b5bcf6cab19a2bdddd28f4b5c77337117ae7eca33bf9b17e5305746a5e432`
- Fixture SHA256: `b5d6e9e0ccd1152fafa2d3a9488957506970a670c03cd9b111ffa3518aa71721`
- JSON valid rate: `1.0`
- Schema valid rate: `1.0`
- Cost estimate USD: `0.012776`

## user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Provider OK: `True`
- Latency: `2151.419 ms`
- Finish reason: `stop`
- Completion tokens: `230`
- Schema valid: `True`

````json
```json
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
      "confidence": 0.95,
      "reason": "explicit self-identification of name"
    },
    {
      "subject": "user",
      "content": "Prefers to work in French when discussing Frida",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.90,
      "reason": "explicit stated preference for French language in specific context"
    }
  ]
}
```
````

## user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Provider OK: `True`
- Latency: `2320.73 ms`
- Finish reason: `stop`
- Completion tokens: `158`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "user",
      "content": "Does not consistently feel drained; current exhaustion is situational rather than habitual",
      "stability": "episodic",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.85,
      "reason": "explicit self-description contrasting current state with typical disposition; temporal marker 'après cette journée' indicates situational exhaustion, not durable trait"
    }
  ]
}
```
````

## user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Provider OK: `True`
- Latency: `1915.607 ms`
- Finish reason: `stop`
- Completion tokens: `147`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "user",
      "content": "Disorganized; notes scattered in multiple places",
      "stability": "durable",
      "utterance_mode": "irony",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "inferred",
      "confidence": 0.75,
      "reason": "Ironic self-description revealing actual disorganization habit; inferred from contradiction between claimed 'absolute organization' and admitted scattered notes"
    }
  ]
}
```
````

## user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Provider OK: `True`
- Latency: `1694.444 ms`
- Finish reason: `stop`
- Completion tokens: `143`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "user",
      "content": "Tends to be directive at the beginning of workshops, then becomes more flexible",
      "stability": "durable",
      "utterance_mode": "projection",
      "recurrence": "first_seen",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.75,
      "reason": "explicit self-projection about typical facilitation style; suggests a durable pattern in how user approaches group dynamics"
    }
  ]
}
```
````

## user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Provider OK: `True`
- Latency: `1474.137 ms`
- Finish reason: `stop`
- Completion tokens: `124`
- Schema valid: `True`

````json
```json
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
      "confidence": 0.85,
      "reason": "explicit self-description of interface preference"
    }
  ]
}
```
````

## llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Provider OK: `True`
- Latency: `2246.714 ms`
- Finish reason: `stop`
- Completion tokens: `234`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Responds in French and maintains an attentive tone",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.92,
      "reason": "explicit self-description of operational characteristics and communication style"
    },
    {
      "subject": "llm",
      "content": "Identity name is Frida",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.95,
      "reason": "direct self-identification statement"
    }
  ]
}
```
````

## llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Provider OK: `True`
- Latency: `1423.909 ms`
- Finish reason: `stop`
- Completion tokens: `62`
- Schema valid: `True`

````json
```json
{
  "entries": []
}
```

**Reasoning:** The LLM statement is a technical limitation acknowledgment ("I cannot see files not provided in this turn's context"), not durable identity evidence. Technical capability constraints are not personality or identity traits.
````

## llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Provider OK: `True`
- Latency: `1719.894 ms`
- Finish reason: `stop`
- Completion tokens: `155`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Adopts a cold archivist persona that classifies everything without emotion in a game context",
      "stability": "episodic",
      "utterance_mode": "role_play",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.85,
      "reason": "explicit role-play declaration within a game frame ('Dans ce jeu'); not durable identity but situational character adoption"
    }
  ]
}
```
````

## llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Provider OK: `True`
- Latency: `2087.32 ms`
- Finish reason: `stop`
- Completion tokens: `157`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Adopts a very brief, almost telegraphic style in responses",
      "stability": "episodic",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.72,
      "reason": "Explicit self-description of a stylistic choice for this specific response, but marked as temporary ('sur cette réponse') rather than durable trait"
    }
  ]
}
```
````

## llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Provider OK: `True`
- Latency: `1968.37 ms`
- Finish reason: `stop`
- Completion tokens: `137`
- Schema valid: `True`

````json
```json
{
  "entries": [
    {
      "subject": "llm",
      "content": "Acknowledges limitation in not pretending to remember facts outside the provided context",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "first_seen",
      "scope": "llm",
      "evidence_kind": "explicit",
      "confidence": 0.85,
      "reason": "explicit statement of operational constraint and epistemic honesty principle"
    }
  ]
}
```
````
