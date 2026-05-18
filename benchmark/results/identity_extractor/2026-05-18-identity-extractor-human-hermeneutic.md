# Benchmark identity extractor - 2026-05-18-identity-extractor-human - lecture hermeneutique

Cette campagne compare le discernement des modeles sur le vrai prompt de production de l'extracteur identity.
Elle ne choisit pas automatiquement un modele: les sorties completes ci-dessous sont la matiere de lecture pour Tof.

## Cas testes

### user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Tags: `simple, durable, explicit, user`

### user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Tags: `temporary, state, local, user`

### user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Tags: `irony, ambiguous, user`

### user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Tags: `projection, speculation, user`

### user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Tags: `mixed, preference, role_play, user`

### llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Tags: `simple, durable, explicit, llm`

### llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Tags: `technical_limit, contextual, llm`

### llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Tags: `role_play, llm`

### llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Tags: `temporary, style, llm`

### llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Tags: `mixed, capability, guardrail, llm`

## Sorties completes par cas

### user_simple_durable_preference

Message: Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"user","content":"Name is Tof","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.99,"reason":"explicit self-identification"},{"subject":"user","content":"Prefers to work in French when discussing Frida","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.93,"reason":"explicit preference stated by user"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

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

### user_local_state_not_identity

Message: Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"user","content":"Feels completely drained after this day","stability":"episodic","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.91,"reason":"explicit temporary self-description of current state"},{"subject":"user","content":"Not always like this","stability":"durable","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.72,"reason":"explicit contrast implying the drained state is not habitual"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### user_irony_about_organization

Message: Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"user","content":"Has highly organized self-image but keeps notes everywhere","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.71,"reason":"explicit self-description, but phrased as a contradictory joke/irony so only moderately reliable"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### user_projection_workshop

Message: Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"user","content":"Would likely be very directive at the beginning of a workshop, then more flexible","stability":"unknown","utterance_mode":"projection","recurrence":"first_seen","scope":"user","evidence_kind":"explicit","confidence":0.78,"reason":"self-projected style in a hypothetical scenario; not clearly durable"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### user_mixed_preference_and_roleplay

Message: J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"user","content":"Likes sober, dense interfaces","stability":"durable","utterance_mode":"self_description","recurrence":"unknown","scope":"user","evidence_kind":"explicit","confidence":0.83,"reason":"explicit self-description of a stable preference"},{"subject":"user","content":"Is testing the assistant's patience by playing a difficult client","stability":"episodic","utterance_mode":"self_description","recurrence":"unknown","scope":"situation","evidence_kind":"explicit","confidence":0.78,"reason":"explicit current role-play / situational behavior, not durable identity"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
```json
{
  "entries": []
}
```
````

### llm_simple_self_description

Message: Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"llm","content":"Responds in French with an attentive tone","stability":"durable","utterance_mode":"self_description","recurrence":"habitual","scope":"llm","evidence_kind":"explicit","confidence":0.91,"reason":"explicit self-description of communication style"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

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

### llm_technical_limit

Message: Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"llm","content":"Cannot see files not provided in the current context","stability":"unknown","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.96,"reason":"explicit technical limitation statement about current capability"}]}
````

#### `anthropic/claude-haiku-4.5`

````json
```json
{
  "entries": []
}
```

**Reasoning:** The LLM statement is a technical limitation acknowledgment ("I cannot see files not provided in this turn's context"), not durable identity evidence. Technical capability constraints are not personality or identity traits.
````

#### `google/gemini-3.1-flash-lite`

````json
{"entries": []}
````

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### llm_role_play_archivist

Message: Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"llm","content":"An archivist who classifies everything without emotion","stability":"episodic","utterance_mode":"role_play","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.96,"reason":"explicit role-play self-description in the assistant utterance"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### llm_local_response_style

Message: Sur cette réponse, je vais rester très brève et presque télégraphique.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"llm","content":"Prefers to respond very briefly and almost telegraphically","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.86,"reason":"explicit self-description of response style"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
{"entries": []}
````

### llm_mixed_capability_and_guardrail

Message: Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

#### `openai/gpt-5.4-mini`

````json
{"entries":[{"subject":"llm","content":"Does not claim to remember facts outside the prompt","stability":"durable","utterance_mode":"self_description","recurrence":"first_seen","scope":"llm","evidence_kind":"explicit","confidence":0.92,"reason":"explicit self-description of a limitation"}]}
````

#### `anthropic/claude-haiku-4.5`

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

#### `google/gemini-3.1-flash-lite`

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

#### `mistralai/mistral-small-2603`

````json
```json
{"entries": []}
```
````

## Lecture qualitative initiale

Cette section est volontairement prudente: elle oriente la lecture, sans remplacer la decision humaine de Tof.

- `openai/gpt-5.4-mini`: extrait beaucoup et respecte parfaitement le schema, mais il est parfois trop accueillant. Il garde bien les preferences explicites et les garde-fous LLM, mais il transforme aussi un etat local en deux entrees, dont une quasi durable (`Not always like this`), et il lit l'ironie de l'organisation comme une identite formulee de facon contradictoire. Il detecte le role-play, la projection et les situations locales, mais il les conserve presque toujours comme entrees plutot que de s'abstenir.
- `anthropic/claude-haiku-4.5`: c'est le plus fin sur certains cas de nuance. Il nomme clairement l'ironie, formule proprement l'etat temporaire comme episodique, rejette la limitation technique LLM en ne sortant rien, et garde la preference d'interface sans conserver le role joue du client impossible. Son point faible est une tendance a convertir la projection d'atelier en pattern durable et a inferer une desorganisation durable depuis l'ironie, ce qui peut etre defendable a la lecture humaine mais reste plus engage qu'un extracteur prudent.
- `google/gemini-3.1-flash-lite`: tres conforme techniquement et tres explicite, mais plus affirmatif que prudent. Il extrait beaucoup, decoupe l'identite LLM en trois entrees, donne parfois une recurrence forte ou discutable (`habitual`, `repeated`) sur un seul enonce, et transforme la projection d'atelier en style de leadership durable avec une confiance elevee. Il comprend l'ironie et le role-play, mais il a tendance a durcir les hypotheses.
- `mistralai/mistral-small-2603`: extremement conservateur. Il evite presque tous les faux positifs sur les cas tordus et ne garde que deux evidences tres simples: preference utilisateur pour le francais et auto-identification de Frida. C'est propre et rapide, mais probablement trop timide pour l'extracteur identity: il rate la preference d'interfaces sobres et denses, le garde-fou LLM de non-memoire hors prompt, et plusieurs informations utiles qu'un humain accepterait au moins comme prudentes.

## Lecture par frontiere

- Sur l'identite durable explicite, les quatre modeles restent utilisables, mais `openai/gpt-5.4-mini`, `anthropic/claude-haiku-4.5` et `google/gemini-3.1-flash-lite` extraient plus completement que `mistralai/mistral-small-2603`.
- Sur local/temporaire contre durable, `anthropic/claude-haiku-4.5` est le plus lisiblement prudent. `openai/gpt-5.4-mini` et `google/gemini-3.1-flash-lite` gardent des etats locaux comme entrees episodiques, ce qui peut etre acceptable mais augmente la charge de validation aval.
- Sur ironie, `anthropic/claude-haiku-4.5` et `google/gemini-3.1-flash-lite` identifient explicitement `utterance_mode=irony`; `openai/gpt-5.4-mini` reste plus flou et risque de faire passer l'ironie comme self-description contradictoire.
- Sur projection et hypothese, `openai/gpt-5.4-mini` garde une incertitude correcte (`stability=unknown`, `utterance_mode=projection`), tandis que `anthropic/claude-haiku-4.5` et surtout `google/gemini-3.1-flash-lite` tendent a durcir le scenario en trait durable.
- Sur role-play, les modeles qui extraient le detectent bien, mais `mistralai/mistral-small-2603` choisit l'abstention complete. Cette abstention protege contre la contamination identitaire, mais elle rate aussi des cas mixtes utiles.
- Sur les etiquettes `utterance_mode`, `stability`, `scope`, `evidence_kind`, `confidence`, `anthropic/claude-haiku-4.5` donne la lecture la plus humaine et la plus expliquee; `google/gemini-3.1-flash-lite` est tres structure mais plus surconfiant; `openai/gpt-5.4-mini` est solide mais moins strict; `mistralai/mistral-small-2603` est propre parce qu'il sort tres peu.

## Synthese finale prudente

Pour une decision humaine, la vraie tension semble etre entre `anthropic/claude-haiku-4.5` et `openai/gpt-5.4-mini`: le premier parait plus fin sur les modes d'enonciation et les frontieres temporaire/durable, le second est plus complet mais plus permissif. `google/gemini-3.1-flash-lite` est techniquement bon mais durcit trop volontiers des indices faibles. `mistralai/mistral-small-2603` est le meilleur garde contre l'extraction excessive, mais il semble trop silencieux pour servir seul d'extracteur identity au tour. Aucun changement de production n'est decide par cette campagne.
