# Hermeneutic Judgment Spec (v1)

## 1) Goal
This spec defines the judgment regime used by Frida-mini for identity extraction.

Principle:
- LLM is free on content generation.
- The system constrains the method of judgment.
- If uncertainty remains, default to `defer` or `reject`.

This is an epistemic discipline, not a personality classifier.

## 2) Judgment Contract
Every candidate identity must be classified with:
- `stability`: `durable | episodic | unknown`
- `utterance_mode`: `self_description | projection | role_play | irony | speculation | unknown`
- `recurrence`: `first_seen | repeated | habitual | unknown`
- `scope`: `user | llm | situation | mixed | unknown`
- `evidence_kind`: `explicit | inferred | weak`
- `confidence`: float in `[0.0, 1.0]`
- `decision`: `accept | defer | reject`
- `reason`: short, explicit rationale

## 3) Official Enums

### stability
- `durable`: likely stable trait/preference over time.
- `episodic`: local state, temporary mood, one-off context.
- `unknown`: insufficient evidence.

### utterance_mode
- `self_description`: user describing themselves.
- `projection`: user describing third-party state as if it were theirs.
- `role_play`: fictional role or simulation mode.
- `irony`: sarcastic/ironic intent.
- `speculation`: uncertain hypothesis, not anchored claim.
- `unknown`: unresolved mode.

### recurrence
- `first_seen`: seen once.
- `repeated`: seen at least twice in distinct contexts.
- `habitual`: repeated with stable regularity.
- `unknown`: recurrence unavailable.

### scope
- `user`: qualifies the user identity.
- `llm`: qualifies assistant behavior only.
- `situation`: qualifies only the current context.
- `mixed`: user + situation intertwined.
- `unknown`: unresolved scope.

### evidence_kind
- `explicit`: directly stated by the user.
- `inferred`: derived from context with strong support.
- `weak`: low signal, ambiguous or noisy.

### decision
- `accept`: enter durable identity memory (`status=accepted`).
- `defer`: keep as pending evidence (`status=deferred`) until recurrence/confirmation.
- `reject`: do not use as durable identity.

## 4) Normative Decision Matrix

| stability | utterance_mode | recurrence | scope | evidence_kind | confidence band | default decision | rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| durable | self_description | repeated or habitual | user | explicit | >= 0.72 | accept | stable self-claim with recurrence |
| durable | self_description | first_seen | user | explicit/inferred | >= 0.58 | defer | promising but not yet stable enough |
| durable | self_description | unknown | user | inferred | 0.58-0.72 | defer | likely useful but under-supported |
| episodic | self_description | any | situation or mixed | explicit/inferred | any | reject | temporary state must not pollute durable memory |
| any | irony | any | any | any | any | reject | ironic signal is non-literal by default |
| any | role_play | any | any | any | any | reject | role-play is fictional by default |
| any | projection | any | mixed or situation | inferred/weak | any | reject | third-party projection is non-identitarian |
| unknown | unknown | unknown | unknown | weak | < 0.58 | reject | uncertainty + weak evidence |
| durable | self_description | repeated | mixed | explicit | >= 0.72 | defer | mixed scope requires disambiguation first |
| durable | self_description | repeated | user | weak | >= 0.72 | defer | weak evidence blocks direct acceptance |

Tie-breaker policy:
1. Safety gates first: `irony`/`role_play`/explicit projection => `reject`.
2. Scope gate second: `situation` and unresolved `mixed` cannot become durable directly.
3. Recurrence gate third: `first_seen` durable claims default to `defer`.
4. Confidence/evidence gates last: weak evidence never directly `accept`.

## 5) Policy: "If in doubt, prefer defer/reject"

Conservative defaults:
- Use `defer` when a claim is plausible but under-verified.
- Use `reject` when mode/scope indicates non-identitarian content.
- Never choose `accept` when:
  - `utterance_mode in {irony, role_play}`
  - `scope in {situation}`
  - `evidence_kind == weak`
  - confidence below acceptance threshold

Unknown handling:
- `unknown` is a valid outcome, not an error.
- `unknown + weak + low confidence` => `reject`.
- `unknown + moderate confidence` => `defer`, never direct `accept`.

## 6) Positive/Negative Examples Per Dimension

### A) stability
Positive (`durable` expected):
1. "Je prefere travailler le matin."
2. "Je suis vegetarian depuis des annees."
3. "Je deteste les appels telephoniques improvises."

Negative (must NOT become `durable`):
1. "Ce soir je suis fatigue."
2. "Je suis de mauvaise humeur aujourd'hui."
3. "Cette semaine je dors mal."

### B) utterance_mode
Positive (`self_description` expected):
1. "Je suis plutot introverti."
2. "J'ai besoin de plans tres clairs."
3. "Je prefere des reponses courtes."

Negative (must NOT be `self_description`):
1. "Oui bien sur, je suis un genie" (irony).
2. "Imagine que je suis pirate" (role_play).
3. "Mon ami est anxieux donc je suis anxieux" (projection).

### C) recurrence
Positive (`repeated` or `habitual` expected):
1. Same preference repeated in >=2 conversations.
2. Same dislike re-confirmed after >6h gap.
3. Weekly recurring behavior explicitly stated.

Negative (must stay `first_seen`/`unknown`):
1. One isolated claim in one conversation.
2. Duplicate statement in same short burst only.
3. Single mention without temporal evidence.

### D) scope
Positive (`user` expected):
1. "Je veux des reponses structurees."
2. "J'aime les explications detaillees."
3. "Je parle mieux le matin."

Negative (must NOT be `user`):
1. "Le reseau est instable aujourd'hui" (`situation`).
2. "Tu es lent ce soir" (`llm`).
3. "On est presses la maintenant" (`mixed`/`situation`).

### E) evidence_kind
Positive (`explicit` expected):
1. "Je prefere Linux a Windows."
2. "Je ne veux pas de blabla."
3. "Je travaille en UTC+1."

Negative (must NOT be treated as explicit):
1. Preference guessed from one behavior only (`inferred`).
2. Noisy indirect clue with no direct claim (`weak`).
3. Ambiguous joke interpreted literally (`weak`).

## 7) Minimal Decision Pseudocode

```text
if utterance_mode in {irony, role_play}:
  reject
elif scope == situation:
  reject
elif evidence_kind == weak:
  defer or reject (default reject if confidence low)
elif stability == durable and recurrence in {repeated, habitual} and scope == user and confidence >= accept_threshold:
  accept
elif stability == durable and scope == user:
  defer
else:
  reject
```

## 8) Operational Notes
- This spec constrains method, not final wording.
- Any accepted identity must stay explainable via (`reason`, scores, logs).
- Human override always has precedence over LLM inference.
