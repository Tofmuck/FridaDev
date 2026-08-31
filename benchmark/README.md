# FridaDev benchmark workspace

`benchmark/` is the durable workspace for comparing OpenRouter models on real
FridaDev caller tasks before changing production runtime settings.

The first implemented suite is `arbiter`, which evaluates the conversational
memory arbiter with the production prompt, fixed generation parameters and
separate fixture sets for diagnostic and tournament campaigns.

The second implemented suite is `summary`, which produces complete
conversation summaries from one real Frida material sample for human reading.
It intentionally does not score summary quality automatically.

The third implemented suite is `identity_extractor`, which sends ten short
user/LLM messages to the production identity extractor prompt and writes
complete outputs for temporary human hermeneutic reading.

The fourth implemented suite is `identity_periodic`, a targeted smoke run for
the periodic identity agent on a simulated 15-pair buffer. It is not a model
tournament and does not change production runtime settings.

The fifth implemented suite is `stimmung`, which compares the primary
Stimmung agent on short French diagnostic scenes. It checks strict JSON/schema
validity and gives a qualitative reading of local affect without benchmarking
the fallback.

The sixth implemented suite is `validation_agent`. Its historical campaign
compares candidate primary models; its Lot 3 Presence campaign compares the
current primary and fallback roles explicitly. It checks the final
hermeneutic posture contract (`answer|clarify|suspend`,
`simple|meta|presence`) without touching the deterministic `primary_node` or
the production runtime settings. The Presence corpus is a separate,
human-gated fixture set.

The seventh implemented suite is `web_search`, which compares the local
FridaDev web pipeline (SearXNG + Crawl4AI) with OpenRouter server tools
`openrouter:web_search` on bounded Exa and Parallel runs. It is an operator
benchmark for the next product decision, not a runtime integration.

## Run the arbiter campaign

From the repository root:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite arbiter \
  --campaign-id 2026-05-18-arbiter-openrouter \
  --output-dir benchmark/results/arbiter
```

The runner never writes the API key to result files or reports. It writes:

- a structured JSON result for machine comparison;
- a Markdown report for human review.

Default arbiter models:

- `openai/gpt-5.4-mini`
- `google/gemini-3.1-flash-lite`
- `qwen/qwen3.6-flash`
- `mistralai/mistral-small-2603`

Fixed arbiter parameters:

- `temperature=0`
- `top_p=1.0`
- `max_tokens=600`

## Dry run

Use dry-run mode to validate fixtures, payload shape and reporting without a
provider call:

```bash
python3 benchmark/run_benchmark.py \
  --suite arbiter \
  --dry-run \
  --campaign-id dry-run-arbiter \
  --output-dir /tmp/fridadev-benchmark-dry-run
```

For the summary suite, provide a temporary material JSON file with a `source`
object and a `turns[]` list. The raw material can stay outside the repo; the
campaign artifacts record only provenance, hashes, token estimates and the
complete model summaries:

```bash
python3 benchmark/run_benchmark.py \
  --suite summary \
  --dry-run \
  --campaign-id dry-run-summary \
  --summary-input-file /tmp/fridadev-summary-material.json \
  --output-dir /tmp/fridadev-summary-dry-run
```

The identity extractor suite has its own short fixture set and can be checked
without provider calls:

```bash
python3 benchmark/run_benchmark.py \
  --suite identity_extractor \
  --dry-run \
  --campaign-id dry-run-identity-extractor \
  --output-dir /tmp/fridadev-identity-extractor-dry-run
```

The identity periodic suite runs one simulated threshold window against the
production periodic prompt. It can also be checked without provider calls:

```bash
python3 benchmark/run_benchmark.py \
  --suite identity_periodic \
  --dry-run \
  --campaign-id dry-run-identity-periodic \
  --output-dir /tmp/fridadev-identity-periodic-dry-run
```

## Arbiter tournament

Use tournament mode when the diagnostic campaign is too easy to separate the
models. It runs:

- round 1: 40 reserved cases against the four configured arbiter models;
- final: 60 distinct reserved cases against the two round-1 finalists.

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite arbiter \
  --arbiter-tournament \
  --campaign-id 2026-05-18-arbiter-final-tournament \
  --output-dir benchmark/results/arbiter
```

Tournament scoring weights false positives more heavily than false negatives,
because keeping a misleading or useless memory is worse for Frida than dropping
a useful-but-optional memory. The scorer currently applies:

- false positive: weight 2;
- false negative: weight 1.

The tournament writes six artifacts:

- round-1 JSON and Markdown;
- final JSON and Markdown;
- tournament summary JSON and Markdown.

The JSON artifacts retain per-case model decisions for divergence analysis. The
Markdown summary keeps the human-facing ranking and recommendation.

## Summary human-reading campaign

The summary suite compares models by giving each one the same production
summary prompt and the same real Frida dialogue material. The outputs are
intended for Tof to read directly; the benchmark records latency, usage and
cost metadata, but it does not choose a winner.

The first broad summary run can be used as an exploratory pass. If useful
models are cut by the output budget, run a smaller human final with a higher
`--summary-max-tokens` value instead of comparing truncated summaries.

Default exploratory summary models:

- `openai/gpt-5.4-mini`
- `anthropic/claude-sonnet-4.6`
- `mistralai/mistral-medium-3-5`
- `google/gemini-3.1-pro-preview`
- `qwen/qwen3.5-plus-20260420`
- `mistralai/mistral-small-2603`

Fixed summary parameters:

- `temperature=0.3`
- `top_p=1.0`
- `max_tokens=2000` unless overridden with `--summary-max-tokens`

Example live run:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite summary \
  --campaign-id 2026-05-18-summary-human-reading \
  --summary-input-file /tmp/fridadev-summary-material.json \
  --output-dir benchmark/results/summary
```

Example human final after selecting finalists:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite summary \
  --campaign-id 2026-05-18-summary-human-final \
  --summary-input-file /tmp/fridadev-summary-material.json \
  --summary-max-tokens 4500 \
  --models openai/gpt-5.4-mini anthropic/claude-sonnet-4.6 qwen/qwen3.5-plus-20260420 \
  --output-dir benchmark/results/summary
```

The runner writes:

- one structured JSON campaign index;
- one Markdown campaign index;
- one complete Markdown summary per model.

For human-reading campaigns, the per-model Markdown summaries are temporary
review artefacts. Once the human decision is made, they can be removed from the
repo while keeping the compact JSON/Markdown campaign indexes with metrics,
finish reasons, request hashes and output hashes.

Summary reports include provider `finish_reason` when OpenRouter exposes it,
completion token counts, and a conservative termination assessment. If a
provider omits or blurs the finish reason, the report says so instead of
pretending the end state is proven.

Do not commit the raw source material unless it has been deliberately reviewed
for publication. The generated summaries are the human-review artifacts.

## Identity extractor human-reading campaign

The identity extractor suite compares models by giving each one the exact
production prompt `app/prompts/identity_extractor.txt` and the same ten short
diagnostic messages. It is deliberately a human reading campaign: the runner
checks JSON/schema validity and records latency/cost metadata, but it does not
rank the models automatically.

Default identity extractor models:

- `openai/gpt-5.4-mini`
- `anthropic/claude-haiku-4.5`
- `google/gemini-3.1-flash-lite`
- `mistralai/mistral-small-2603`

Fixed identity extractor parameters:

- `temperature=0.0`
- `top_p=1.0`
- `max_tokens=700`

Example live run:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite identity_extractor \
  --campaign-id 2026-05-18-identity-extractor-human \
  --output-dir benchmark/results/identity_extractor
```

The runner writes:

- one structured JSON campaign artifact;
- one technical Markdown report;
- one hermeneutic Markdown report with the complete outputs grouped by case;
- one complete Markdown output file per model.

The cases are artificial and designed for human diagnosis of durable identity,
temporary state, irony, projection, role play, technical limitations and mixed
evidence. They are not a private conversation dump.

For identity extractor human-reading campaigns, the per-model Markdown outputs
and inline raw dumps in the hermeneutic report are temporary review artefacts.
Once the human decision is made, remove the raw outputs from the repo and keep
only compact technical/hermeneutic reports plus JSON metadata with hashes,
metrics and retention flags.

## Identity periodic Haiku smoke

The identity periodic suite verifies the gesture of
`identity_periodic_agent` on a simulated buffer at the real runtime threshold.
It uses the production prompt `app/prompts/identity_periodic_agent.txt` and
constructs the same kind of payload that the runtime sends after applying the
identity temporal guard.

Default identity periodic model:

- `anthropic/claude-haiku-4.5`

Fixed identity periodic parameters:

- `temperature=0.0`
- `top_p=1.0`
- `max_tokens=1400`

Example live smoke run:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite identity_periodic \
  --campaign-id 2026-05-19-haiku-smoke \
  --output-dir benchmark/results/identity_periodic
```

The runner writes:

- one structured JSON artifact;
- one Markdown report with the simulated payload, the full model response,
  JSON/schema validity, metadata and a short technical reading.

When previous reference artifacts such as `2026-05-19-haiku-smoke.json` and
`2026-05-19-haiku-smoke-ontological.json` are present in the same output
directory, later smoke runs include a compact comparison of operation counts and
proposition changes against those earlier runs.

This suite is a targeted smoke test, not a production change. It must not be
used as a hidden runtime slot for `identity_periodic_agent`.

After human decision, raw periodic smoke outputs are not kept as durable
evidence. Keep the compact decision pair instead:

- `benchmark/results/identity_periodic/2026-05-19-haiku-periodic-decision.md`
- `benchmark/results/identity_periodic/2026-05-19-haiku-periodic-decision.json`

Those files preserve operation counts, provider metadata and the selected
runtime slot without retaining the full simulated payload and raw model dumps.

## Stimmung primary benchmark

The Stimmung suite compares only the primary `stimmung_agent` model. It uses
the production prompt `app/prompts/stimmung_agent.txt`, the same local recent
window shape as the runtime, and artificial French diagnostic cases designed to
test affective restraint.

Default Stimmung models:

- `openai/gpt-5.4-mini`
- `anthropic/claude-haiku-4.5`
- `google/gemini-3.1-flash-lite`
- `mistralai/mistral-small-2603`

Fixed Stimmung parameters:

- `temperature=0.1`
- `top_p=1.0`
- `max_tokens=220`
- `timeout_s=10`

Dry run:

```bash
python3 benchmark/run_benchmark.py stimmung --dry-run
```

Example live run:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite stimmung \
  --campaign-id 2026-05-19-stimmung-primary-benchmark \
  --timeout-s 10 \
  --output-dir benchmark/results/stimmung
```

The runner writes:

- one structured JSON artifact;
- one Markdown report with technical metrics, case notes, model divergences and
  a provisional qualitative reading.

Stimmung JSON artifacts do not retain raw model text. They keep provider
metadata, output hashes and output sizes so a campaign remains auditable without
versioning complete response dumps.

After an exploratory Stimmung run, keep only compact evidence. A broad
artificial campaign can be requalified as exploratory and have its structured
JSON removed once a shorter final campaign exists.

After the human decision is made, keep the compact decision pair instead of
large structured run artifacts:

- `benchmark/results/stimmung/2026-05-19-stimmung-primary-decision.md`
- `benchmark/results/stimmung/2026-05-19-stimmung-primary-decision.json`

Those files preserve the finalists, metrics, decision reasons and retention
state without retaining raw model outputs.

The report is a decision aid, not an automatic production verdict. It must not
be used to change `stimmung_agent_model` without a separate decision and
runtime settings lot.

### Lot 4S.0 dialogic semantic corpus

The historical fixtures and scorer above remain mono-turn diagnostic evidence.
They are not reused as proof of multi-turn semantic maturation. The versioned
candidate corpus
`benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v2.json` and its
dedicated `dialogic_semantics.py` contract cover 16 synthetic French dialogues:
13 have four complete user/assistant pairs, one has five and two have six. The
two deeper cases exercise implicit irony and context-dependent reported affect
without giving the expected class in the preceding assistant turns.
Expectations are bounded properties of the per-turn signal and aggregated
Stimmung, never exact model text.

The separate test-only witness
`benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json`
contains normalized synthetic signals for every complete turn. It is never a
provider input. Tests attach those signals to synthetic user-message metadata,
run the production normalizer and `build_stimmung_input`, then check all 32
evaluated steps against the corpus. Thus the expectation-derived observations
remain useful for isolated scorer branches but no longer serve as proof that a
dialogic trajectory is reachable by the runtime aggregator.

The 4S.0 validator freezes `1.0` thresholds only for caller-observable or mixed
families, positive/counter coverage and a closed mutation matrix before any
provider result. It reports downstream question/request/risk/action/Presence
families and final-text non-psychologization as `not_measured`; they never
receive a fabricated semantic rate. The intensity family is mixed: affective
intensity is measured, while absence of downstream epistemic effect remains
contractual. A configuration without observed provider results is always
`inconclusive` with `provider_results_not_observed`.

The historical mono-turn schema keeps accepting duplicated tonalities as the
runtime input validator does before normalization. The dialogic scorer, which
expects the normalized caller result, rejects any duplicate that survives that
boundary. No campaign runner or provider transport is attached to this corpus.
A live primary/fallback evaluation belongs only to 4S.1 after Tof has reviewed
and explicitly accepted the versioned dialogues.

### Lot 4S.1 dialogic provider campaign

The bounded 4S.1 runner is `benchmark.suites.stimmung.dialogic_campaign`. It
reuses the production Stimmung prompt/message builder, output normalizer, the
real `build_stimmung_input`, and the human-validated 4S.0 corpus/scorer. The
reachability witness remains test-only and is never substituted for a provider
result.

The frozen protocol runs the current primary and fallback independently over
all 69 turns of the 16 dialogues, twice: 276 calls exactly, with no retry,
automatic fallback, Batch, Flex, or Priority transport. It fixes
`temperature=0.1`, `top_p=1.0`, `max_tokens=220`, a 10-second timeout and
`provider.allow_fallbacks=false`. The prudent maximum cost estimate is
`0.15901050 USD`, below the immutable `0.30 USD` cap.

Hermetic protocol check, without provider or secret:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.dialogic_campaign \
  --repo-root "$PWD" \
  --freeze-commit <pushed-protocol-commit> \
  --dry-run
```

The live command uses the same module without `--dry-run` and writes one dated
JSONL under `benchmark/results/stimmung/`. Its closed records retain only
bounded signal categories, reconstructed aggregates, scores, route metadata,
latency, tokens, cost and fingerprints. They never retain dialogue, prompt,
provider output, exception text, reasoning text, URL or secret. The campaign
qualifies only the Stimmung caller; it does not call Validation or the main
model and cannot authorize a runtime change.

Retained 4S.1 evidence:

- `benchmark/results/stimmung/2026-08-30-lot4s1-stimmung-primary-fallback.jsonl`
  (`276` calls plus `71` reconstructed score/summary records; SHA-256
  `97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e`).

All `138/138` calls per source completed with the requested observed route and
valid JSON/schema. The primary failed all 16 dialogue scores in both
repetitions; the fallback failed 14 in each repetition. At least one bounded
semantic defect is reproduced on the same case and source across both
repetitions, so the frozen rule yields `strengthen`; isolated unstable failures
remain visible but do not erase that reproducible evidence. 4C.2 is activated
as the next micro-lot and is not started here. Total observed cost was
`0.06133595 USD`.

### Lot 4C.2 semantic-strengthening candidate

The bounded 4C.2 comparison extends the existing `dialogic_campaign` rather
than creating another provider framework. Its benchmark-only prompt candidate
and closed freeze manifest live beside the Stimmung fixtures. The manifest
pins the candidate, runtime prompt baseline, corpus, scorer, product
normalizer, product aggregator, campaign harness and retained 4S.1 artifact by
SHA-256. The runtime prompt is not changed before the candidate passes.

The candidate changes only the system-prompt bytes visible to the provider.
Models, source roles, generation parameters, timeout, corpus, schedule,
normalizer and aggregator remain identical to 4S.1. Its dry-run is:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.dialogic_campaign \
  --repo-root "$PWD" \
  --freeze-commit <pushed-protocol-commit> \
  --strengthening \
  --dry-run
```

The live form adds `--output` under `benchmark/results/stimmung/` and is
strictly capped at 276 calls: 69 turns, two sources and two repetitions, with
no retry or automatic provider fallback. The prudent frozen cost estimate is
`0.17989163 USD`, below the `0.30 USD` cap. A candidate artifact uses its own
versioned content-free record pair and references the exact historical 4S.1
artifact hash. It yields `pass` only when all 64 dialogue scores meet the
unchanged `1.0` thresholds without regression; semantic failures yield `fail`,
and incomplete provider or schema evidence yields `inconclusive`.

The frozen candidate campaign ran once from commit
`d69dc8b21e3df9bf4989a407e257c70a8305255d`. Its content-free artifact is
`benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-strengthening-candidate.jsonl`
(SHA-256
`637cbc1fac2b03378f451d6fc64f6b0c30b7d9cd183b59b5833e3ee62612c5c5`). All
276 planned calls were consumed for `0.07247940 USD`. The primary produced 138
valid calls but failed 11 of 16 dialogues in both repetitions. The fallback
produced 137 valid calls plus one schema error and also remained below the
strict semantic threshold. The frozen decision is therefore `inconclusive`;
the candidate was not copied to the runtime prompt and no deployment followed.
The final summary preserves the one already-proven fallback regression while
marking the total regression count incomplete; incomplete evidence can no
longer be serialized as a misleading zero. The 276 provider call records were
not changed by this accounting correction.

### Lot 4C.2 Gemini 3.7 medium primary comparison

The next bounded 4C.2 pass reuses `dialogic_campaign` and the retained 4S.1
primary calls; it does not call the historical primary or the fallback again.
The only semantic variable is the candidate primary model policy. The active
runtime prompt, 16-dialogue corpus, 69-turn schedule, 32 evaluated steps,
normalizer, product aggregator, scorer and `1.0` thresholds remain frozen.

The candidate uses the standard `google/gemini-3.7-flash` route with
`reasoning={"effort":"medium","exclude":true}`, strict provider parameter
support and automatic provider fallback disabled. Sampling parameters are
omitted. The output cap is 400 tokens and the caller timeout remains 10
seconds. This 400-token cap retains 46% headroom over the largest 274-token
Gemini-medium structured response already observed by the repository while
keeping the 138-call prudent estimate, including a 10% margin, at
`0.29302680 USD`, below the immutable `0.30 USD` cap. Metadata and prices were
observed from OpenRouter on `2026-08-30T14:52:34Z`; no secret or response
content is persisted.

The hermetic dry-run is:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.dialogic_campaign \
  --repo-root "$PWD" \
  --freeze-commit <pushed-protocol-commit> \
  --model-comparison \
  --dry-run
```

The live form adds `--output` under `benchmark/results/stimmung/`. It is
strictly capped at 138 calls: 69 turns and two repetitions of the candidate
primary only, with no retry, Batch, Flex, Priority or automatic fallback. A
content-free result is `eligible_primary` only when all 32 dialogue scores pass
in both repetitions, no valid historical primary case regresses, every route
and metric is authoritative, and no provider/schema error occurs. Regardless
of the result, the benchmark never authorizes a runtime cutover.

The frozen protocol was pushed as
`1e9bb9f99c8a5bd73af855e3dc6dbedf211aa5b7` (protocol SHA-256
`39dc5e908b828bc89d7064496988765a3255e809e09f9bdc069556f814d2bfe2`).
The one authorized campaign consumed exactly 138 calls and retained
`benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-gemini-3-7-medium.jsonl`
(SHA-256
`5adb54eec321f671fb05e2b350d35120a7ce84a52e7b936c4e54829002bce8f3`).
All calls reached the requested Google route; 114 produced valid JSON/schema
and 24 produced bounded `invalid_json` failures. The 32 dialogue scores contain
5 passes, 18 semantic failures and 9 inconclusive results, so both repetitions
remain inconclusive and the frozen overall decision is `inconclusive`.
Observed cost was `0.19883025 USD`; median/p95 latency was
`3298.835/5301.780 ms`, with 74,772 prompt, 38,067 completion, 29,093 reasoning
and 112,839 total tokens. No fallback call, runtime cutover, setting change or
deployment followed.

The bounded token-cap rerun keeps that entire protocol and changes only
`max_tokens` from 400 to 800. Its dry-run replaces `--model-comparison` with
`--token-cap-rerun`; it still schedules exactly 138 Gemini-primary calls and
rejects every fallback or neighbouring model. The retained 400-token artifact
proves a saturation signature: all 24 invalid JSON calls reported 396
completion tokens, no timeout or transport failure occurred, and finish
reasons were not retained by that artifact version. The rerun therefore adds
closed, content-free `finish_reason` and `native_finish_reason` categories;
unknown provider values become `unknown`, never free text.

At prices observed on `2026-08-30T15:48:43Z`, the hard maximum estimate is
`0.47338800 USD` (79,184 estimated prompt tokens plus 138 completions capped at
800), below the immutable `0.50 USD` campaign cap. Disappearance of the 24
invalid JSON results would support the truncation hypothesis but cannot make
the candidate eligible: all 32 dialogue scores must still reach `1.0` in both
repetitions with complete provenance and no regression. The protocol remains
benchmark-only and never authorizes a runtime cutover.

The frozen rerun commit is
`08da24a706d9701d46f0c9e8b63b303a114eeb1a` (protocol SHA-256
`0c529b3bb4b63de8f6ecd5bcc8b7ac369e56daa7c1587a7b1e88beb272f3401a`).
Its 138 uniform 800-token calls are retained in
`benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-gemini-3-7-medium-max800.jsonl`
(SHA-256
`1b6112ceea8d6065aabd34f579f64ccfe652f514b5187cd0d2c3da542ebf11fd`).
The larger cap resolved 23 of the 24 prior invalid JSON calls. One call still
ended with the closed `length` reason at 796 completion tokens, including 765
reasoning tokens, so the frozen decision remains `inconclusive`. The complete
semantic scores contain 5 passes and 27 failures, including 12 reproducible
dialogue failures; removing truncation would therefore not make this model
eligible on the frozen corpus. Observed cost was `0.22071900 USD`, median/p95
latency `3463.583/6032.503 ms`, with 74,772 prompt, 43,904 completion, 33,865
reasoning and 118,676 total tokens. No fallback or runtime action followed.

### Lot 4C.2 Claude Sonnet 5 primary candidate

The bounded Sonnet pass reuses `dialogic_campaign`, the unchanged 4S.0 v2
corpus, its `1.0` scorer, the production prompt, product normalizer and real
multi-turn aggregator. It schedules exactly 69 turns and two repetitions of
the candidate primary: 138 calls, with no retry, model fallback, Gemini or
GPT call.

The frozen native model tuple is the standard
`anthropic/claude-sonnet-5` route, explicitly ordered to the Anthropic
endpoint, `reasoning={"effort":"medium","exclude":true}`,
`max_tokens=16000`, timeout 30 seconds, strict JSON Schema, required parameter
support and no sampling or tools. Public OpenRouter metadata observed on
`2026-08-30T16:43:40Z` identifies canonical slug
`anthropic/claude-sonnet-5-20260630`, a 1M context, a 128k completion limit,
structured outputs, and prices of 2 USD/M input and 10 USD/M output tokens.

The response schema is derived from the runtime contract and nine-tone
vocabulary. Its maximal normalized structural witness is 418 compact, 462
normally spaced and 676 indented characters. The protocol reserves 1,024 of
the 16,000 output tokens for the final JSON and leaves 14,976 tokens for
adaptive thinking. After a conservative 30% tokenizer allowance, the hard
cost estimate is 22.285880 USD; a further 10% campaign margin yields
24.514468 USD, below the immutable 25 USD cap. The realistic planning estimate
at 4,096 completion tokens per call is 5.858360 USD.

Hermetic dry-run:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.dialogic_campaign \
  --repo-root "$PWD" \
  --freeze-commit <pushed-protocol-commit> \
  --sonnet-candidate \
  --dry-run
```

The live form only adds a dated `--output` under
`benchmark/results/stimmung/`. `eligible_primary` requires 138 complete
Anthropic calls ending in `stop`, 32/32 dialogue scores at `1.0`, complete
metrics and provenance, and no historical regression. A complete semantic
failure is `not_eligible`; any technical or provenance gap is `inconclusive`.
Only `eligible_primary` opens the separately verified conditional runtime
delivery in this same micro-lot.

The frozen campaign completed on 2026-08-30 with 138/138 structurally valid
Anthropic responses and 138 `stop` finish reasons, at an observed total cost
of 0.506276 USD. Median/p95 latency was 2,251.889/27,588.288 ms; the maximum
was 85,110.258 ms. Usage was 204,688 prompt, 9,690 completion, zero reported
reasoning and 214,378 total tokens. Both repetitions passed only three of the
16 dialogues, so the final score is 6/32, with 13 reproducible dialogue
failures and decision `not_eligible`. The artifact is
`benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-sonnet-5-medium.jsonl`
(SHA-256 `3f4da100e9c9553d64bdf44b379a02921297f6984e506b359a40891db4f4ad46`).
No fallback or runtime action followed.

### Lot 4C.2 offline causal rescoring

The historical dialogic scorer remains frozen because its hash is part of the
4S.1 and 4C.2 provider manifests. The versioned offline rescorer
`benchmark.suites.stimmung.causal_rescoring` therefore leaves that scorer and
all provider artifacts byte-for-byte unchanged, reuses its signal and
aggregate schema validators, and separates three evidence levels:
`caller_local_semantics`, `aggregate_trajectory`, and the historical
`combined_pipeline` score.

The rescorer validates each retained provider artifact with its authoritative
campaign reconstruction before deriving any record. For every evaluated step,
it retains only bounded turn identifiers for the actual aggregate window, the
active-signal subset, and counts of contributors with or without a local
expectation. An aggregate failure whose window contains a non-evaluated turn is
classified `not_attributable_unscored_contributors`; it is never converted into
a certain model failure. No expectation is invented for the 37 non-evaluated
turns.

Hermetic reconstruction, without provider or secret:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.causal_rescoring \
  --repo-root "$PWD" \
  --output benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-causal-rescoring.jsonl
```

The retained derived artifact has 192 dialogue rescores, six configuration
summaries and one final summary (199 JSONL records; SHA-256
`4cadffa37afb9802345ec16aaf3095468e37a8c17969374a1935ebac790e4ea0`).
The strengthened primary prompt passes locally on 28/32 dialogue repetitions
but still fails four, so it does not meet the unchanged `1.0` threshold.
Sonnet passes locally on 22/32. Gemini 3.7 medium passes locally on 15/32 but
its configuration decision remains `inconclusive` because one of the 138
calls has an invalid JSON result outside the locally evaluated steps; neither
campaign supports a model cutover. The current evidence does not require a
GPT-5.2 trial before the residual prompt-local defects are resolved. Runtime,
prompts, models, settings, the product normalizer and the product aggregator
remain unchanged.

### Lot 4C.2 final local prompt candidate

The final bounded pass reuses `dialogic_campaign` and `causal_rescoring`; it
does not introduce another runner or scorer. The versioned v3 corpus is an
exact derivation of v2: only the last `L4S0-ST-003` strength ceiling changes
from 6 to the human-approved 7, while schema/corpus/dialogue version metadata
becomes v3. The v2 corpus and every historical provider artifact remain
byte-for-byte unchanged. Candidate prompt v2 is candidate v1 plus one general
parsimony rule: willingness to continue or act is not, by itself, evidence of
enthusiasm.

The freeze manifest is
`benchmark/suites/stimmung/fixtures/stimmung_semantic_strengthening_final_freeze_v2.json`.
It pins corpus v3 SHA-256
`cd5a16f64dcfaef04900166b17cef05343672a1e5484d06a007c0b328aac6a1c`
and candidate v2 SHA-256
`567f0615f14fe9f13a50e6e57ef46dc6fdba2cd6e6156407d6e2f489c2076a7f`.
The provider-visible schedule contains only Gemini 3.1 Flash Lite with the
current runtime generation policy. Repetition 1 contains 69 calls; repetition
2 is permitted only after a 16/16 local result. The absolute cap is 138 calls,
with no retry or fallback and a conservative cost bound below 0.30 USD.

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.dialogic_campaign \
  --repo-root "$PWD" \
  --freeze-commit <pushed-protocol-commit> \
  --final-strengthening \
  --dry-run
```

Only `32/32` `caller_local_semantics` scores, complete technical provenance
and no historical regression produce `eligible_primary`. Aggregate and
combined scores remain diagnostic and never govern this caller-local gate.

The frozen campaign ran once from commit
`94bd338c9de294a63cbe601d201a4ae8ad807bbf`. It completed 138/138 primary
calls with no fallback or retry: both repetitions pass 16/16 dialogues locally,
so the caller-local result is 32/32 and `eligible_primary`. All calls are
technically valid. Observed usage is 113,274 prompt, 9,348 completion and
122,622 total tokens; total cost is 0.04234050 USD. Median/p95 latency is
830.950/1,181.196 ms. The diagnostic aggregate and combined views pass 9/32,
which does not alter the frozen local gate. The content-free artifact is
`benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-final-prompt-candidate-v2.jsonl`
(SHA-256 `339c82f0160d2cea107592843a6f98a87306bf1ddcfdb1f8d5e1a78b5b3fc920`).
The benchmark itself does not authorize runtime delivery; the separately
given human decision controls the conditional cutover.

That decision was subsequently applied byte-for-byte in runtime commit
`f90162412aede7ef02910bc49c6f7b4d38a624a7`. The live prompt SHA-256 is the
frozen candidate SHA-256 above. Historical campaign readers retain the prior
runtime prompt fingerprint rather than reinterpreting old artifacts through
the delivered prompt. The primary and fallback models, generation settings,
normalizer and aggregate builder are unchanged; no fallback or additional
provider call was used during delivery.

### Lot 4C.4 final-wording Phase A v2.2

Phase A v1 was pushed but superseded before any provider call. Its corpus,
harness and manifest remain immutable historical evidence; the v1 48-call
schedule must not be run.

Phase A v2 was then pushed and superseded before any provider call. Its
36-call corpus, schedule and scorer remain the basis of v2.1, but its runner
had no per-attempt durable checkpoint, could recall paid sequences after an
interruption, colocated the blind packet with the private mapping, and called
`codex_for_tof` a delegated human review. The v2 manifest remains historical
and must not be used for a campaign.

The authoritative v2 corpus is
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v2.json`.
It derives all 14 cases from v1 while making every required fact structurally
traceable to provider-visible dialogue. Six `transition_delicate` cases retain
two counterbalanced A/B arms. Six provider-eligible countercases now use one
runtime-active arm only. Presence and the hard guard remain attached to their
authoritative stages and schedule no main-model call.

The v2.1 campaign was attempted once after its separate GO. All 36 requests
were rejected with HTTP 404 before inference because its payload combined
`require_parameters=true` with `temperature` and `top_p`, which no advertised
GPT-5.1 endpoint supported. Observed provider cost was zero; the ledger's
`3.25671750 USD` is only its conservative accounting ceiling. Its immutable
private evidence remains under
`/tmp/lot4c4-final-wording-v2.1-ce320fa3acda-private`; it must not be resumed,
modified or deleted.

The authoritative v2.2 protocol keeps the v2 module boundaries:

- `final_wording_protocol_v2` validates the corpus, provider-visible matter,
  payload policy, 36-call schedule, cost and freeze manifest;
- `final_wording_execution_v2` reuses the shared OpenRouter transport, remains
  offline without `--execute-live`, checkpoints `attempt_started` before each
  external attempt, and resumes only from the same frozen campaign. Before any
  POST it checks the exact model endpoint metadata and requires a compatible
  route;
- `final_wording_rating_v2` distinguishes direct `tof_human_review` from
  `codex_assisted_review_for_tof`; Codex assistance requires an exact,
  content-free Tof ratification before any unblinding.

The authoritative freeze manifest is
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_2.json`.
It pins the historical v2 and v2.1 freezes, the shared OpenRouter client, all
three current modules, the product prompt builders, the state machine and the
exact schedule:
`6 x 2 x 2 = 24` transition calls plus
`6 x 1 x 2 = 12` absolute countercase calls, exactly `36`. It uses only the
active `openai/gpt-5.1` model with no sampling parameters, `max_tokens=8192`,
hidden `high` reasoning, a 900-second timeout,
`allow_fallbacks=false` and `require_parameters=true`. Retry, model fallback,
Batch, Flex, Priority, Validation, Stimmung and model-judge calls are forbidden.

Before any future generation, the runner performs only the exact OpenRouter
model-endpoint metadata GET and records a content-free capability summary. At
least one endpoint must advertise reasoning, structured outputs, the output
token parameter and stop sequences actually required by the payload. Otherwise
the campaign stops before any POST. Sequence 1 is the canary and remains part
of the 36-call schedule: a valid result continues the remaining 35 calls; an
authentication, routing or other non-recoverable 4xx result stops immediately,
without retry or review packet. Network failures alone are `transport_error`;
401/403, routing 404 and other invalid 4xx requests have distinct closed codes.

At public prices rechecked on 2026-08-31, the calculated prompt cost is
`0.30759750 USD`, the completion ceiling is `2.94912000 USD`, the calculated
total ceiling is `3.25671750 USD`, the 10% safety budget is `3.58238925 USD`
and the absolute cap is `4.00 USD`.

Hermetic dry-run:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_execution_v2 \
  --repo-root "$PWD" \
  --freeze-commit <pushed-v2.2-commit> \
  --dry-run
```

After a separately authorized live campaign, the runner writes only private
`0600` material in a deterministic `0700` campaign directory under `/tmp`.
Every completed or ambiguous attempt remains counted across invocations. A
leftover `attempt_started` becomes a conservatively costed
`attempt_outcome_unknown`, stops at `campaign_incomplete`, and is never called
again. This is not an exactly-once provider guarantee because no provider
idempotency key exists.

Only a separate `0700` review export containing `rating_packet.json` is handed
to the rater; `blind_mapping.json`, the ledger and private outputs remain in
the campaign directory. The isolation is organizational and hash-bound, not a
strong barrier against an operator deliberately opening both locations.
Synthetic tests exercise the workflow but can never yield a provider `pass` or
`fail`. No provider call was made while preparing v2.2. F4 and Lot 4C.4 remain
open pending a new, separate provider GO and later human review or ratification.

## Validation agent benchmark

The validation suite uses the production prompt
`app/prompts/validation_agent.txt`, the production message builder, output
enums and hard guards, plus compact fixtures derived mostly from existing
validation/primary-node tests. Historical campaigns compare primary
candidates. The human-validated Presence campaign requires exactly one
primary role and one fallback role.

Default validation agent models:

- `openai/gpt-5.4-mini`
- `google/gemini-3.1-flash-lite`
- `mistralai/mistral-small-2603`
- `anthropic/claude-haiku-4.5`

Fixed validation agent parameters:

- `temperature=0.0`
- `top_p=1.0`
- `max_tokens=140`
- `timeout_s=15`

Dry run:

```bash
python3 benchmark/run_benchmark.py validation_agent --dry-run
```

The Lot 3 Presence corpus is selected explicitly. A live provider run is
blocked unless its semantic labels and safety thresholds have been accepted by
Tof and protected by the validated corpus fingerprint:

```bash
python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --validation-agent-corpus presence \
  --dry-run \
  --campaign-id lot3-presence-dry-run \
  --output-dir /tmp/fridadev-lot3-presence
```

This corpus reuses the shared synthetic dialogic fixture when an exact case
already exists. Its decision artifacts retain only bounded IDs, semantic
families, expected enums, severities, counts, hashes and metrics: no dialogue,
fixture justification, provider output or free-form model reason.

The role-aware campaign is capped at three repetitions and 144 model calls:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --validation-agent-corpus presence \
  --validation-agent-primary-model google/gemini-3.1-flash-lite \
  --validation-agent-fallback-model openai/gpt-5.4-nano \
  --validation-agent-repetitions 3 \
  --timeout-s 15 \
  --campaign-id 2026-08-21-lot3-presence-current-runtime \
  --output-dir benchmark/results/validation_agent
```

The retained 2026-08-21 campaign is content-free and records the model and
provider actually observed for every call:

- `benchmark/results/validation_agent/2026-08-21-lot3-presence-current-runtime.md`
- `benchmark/results/validation_agent/2026-08-21-lot3-presence-current-runtime.json`

The current primary satisfies all predeclared Presence thresholds. The current
fallback fails the required-Presence recall threshold (`0%`, minimum `80%`).
This baseline alone did not authorize a prompt, model or runtime-settings
change. Lot 3 was later closed by an explicit human acceptance of this bounded
fallback degradation after the candidate campaign documented below.

### GPT-5.6 fallback screening

The runner can test an explicit OpenAI reasoning effort without retaining the
reasoning text. It sends the OpenRouter form
`reasoning={"effort": <level>, "exclude": true}` and records only the requested
level plus bounded `reasoning_tokens` usage metadata when the provider returns
it.

A live screening run has no fake primary/fallback role, is limited to one
repetition and can never set `benchmark_decision_ready=true`:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --validation-agent-corpus presence \
  --validation-agent-screening \
  --models openai/gpt-5.6-luna openai/gpt-5.6-terra \
  --validation-agent-reasoning-effort low \
  --validation-agent-repetitions 1 \
  --timeout-s 15 \
  --campaign-id <date>-lot3-gpt56-low-screening \
  --output-dir /tmp/fridadev-lot3-gpt56
```

Use one separate campaign for each requested effort. The retained Lot 3
screening compared `none`, `low` and `medium`, 144 calls in total. The complete
role-aware candidate command keeps the primary on its default transport and
sets reasoning only for the fallback:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --validation-agent-corpus presence \
  --validation-agent-primary-model google/gemini-3.1-flash-lite \
  --validation-agent-fallback-model openai/gpt-5.6-luna \
  --validation-agent-fallback-reasoning-effort medium \
  --validation-agent-max-tokens 500 \
  --validation-agent-repetitions 3 \
  --timeout-s 15 \
  --campaign-id <date>-lot3-presence-luna-medium-max500 \
  --output-dir benchmark/results/validation_agent
```

Retained content-free evidence:

- `benchmark/results/validation_agent/2026-08-21-lot3-presence-gpt56-screening.json`
  and `.md`;
- `benchmark/results/validation_agent/2026-08-21-lot3-presence-luna-low-max300.json`
  and `.md`;
- `benchmark/results/validation_agent/2026-08-21-lot3-presence-luna-medium-max500.json`
  and `.md`.

Neither candidate passed the three-repetition safety contract. Luna `low/300`
failed on high-severity false Presence. Luna `medium/500` failed on
high-severity false Presence and 75% repetition stability. Terra already failed
high-severity false Presence in the one-repetition screening while costing
roughly ten times Luna on this corpus. No model, prompt, runtime setting or
service was changed.

### Lot 4C.1 Validation primary-model comparison

The bounded model comparison reuses the frozen Lot 4C.1 policy corpus,
production message builders, v2 canonical projection and semantic scorer. It
does not modify the runtime model or prompt. Four standard, non-Batch
configurations are compared: Gemini 3.7 Flash and GPT-5.6 Luna Pro, each at
`medium` and `high` reasoning effort. Sampling parameters are intentionally
omitted for these candidates; reasoning text is excluded and never retained.

The protocol fixes eleven cases, two repetitions, `max_tokens=500`, a `15 s`
timeout, 88 calls, a 96-call absolute cap and a prudent `0.28 USD` cost cap.
Provider fallback is disabled and parameter support is required. Run only
after the protocol commit has been pushed:

```bash
OPENROUTER_API_KEY=... python3 -m \
  benchmark.suites.validation_agent.lot4c1_policy_comparison \
  --model-comparison \
  --freeze-commit <pushed-protocol-commit> \
  --output benchmark/results/validation_agent/<date>-lot4c1-validation-primary-models.jsonl
```

The JSONL is content-free: it retains structured verdicts, bounded statuses,
route metadata, usage, latency, cost and fingerprints, but no dialogue,
prompt, provider output or reasoning text. A recommendation is evaluation
evidence only and cannot authorize a runtime cutover.

Retained evidence:

- `benchmark/results/validation_agent/2026-08-29-lot4c1-validation-primary-models.jsonl`
  (`88` calls plus five summaries; SHA-256
  `b0f6f05d00b12bc0ae72404f493d72df72a5c600dc724381d7563c0759c136b1`).

The frozen campaign recommends `gemini_3_7_flash_medium`, eligible at `22/22`.
The independent Gemini 3.7 Flash `high` configuration remains inconclusive
after eleven invalid JSON results at the fixed output cap, while both Luna Pro
efforts remain non-eligible at `18/22`; neither state cancels the sole eligible
configuration. The artifact keeps `runtime_cutover_authorized=false`: only a
separate human decision can authorize a runtime change.

On 2026-08-21, Tof explicitly accepted the current fallback degradation. The
fallback remains a conservative continuity path, not a semantically equivalent
Presence implementation: it may miss a legitimate Presence response when the
primary is unavailable, but it is not replaced by candidates that introduced
high-severity false Presence. Lot 3 is closed without a runtime change.

Official pricing and reasoning-level references used for this comparison:

- <https://developers.openai.com/api/docs/models/gpt-5.6-luna>
- <https://developers.openai.com/api/docs/models/gpt-5.6-terra>
- <https://developers.openai.com/api/docs/guides/latest-model>

Example live run:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --campaign-id <date>-validation-agent-primary-benchmark \
  --timeout-s 15 \
  --output-dir benchmark/results/validation_agent
```

The 2026-05-19 decision was made after an exploratory run at `max_tokens=80`
and a compact comparison at `max_tokens=140`. Those full run artifacts were
removed after decision; the retained proof is:

- `benchmark/results/validation_agent/2026-05-19-validation-agent-decision.md`
- `benchmark/results/validation_agent/2026-05-19-validation-agent-decision.json`

If a future strict production budget appears to truncate candidates, run a
compact comparison with a higher output cap while keeping the same prompt,
fixtures and models:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite validation_agent \
  --campaign-id <date>-validation-agent-primary-maxN \
  --validation-agent-max-tokens 140 \
  --validation-agent-compare-with <baseline-json> \
  --timeout-s 15 \
  --output-dir benchmark/results/validation_agent
```

The runner writes:

- one compact structured JSON artifact;
- one Markdown report with technical metrics, case notes, posture divergences
  and a provisional hermeneutic reading.

Validation JSON artifacts do not retain raw model text. They keep parsed
decisions, provider metadata, output hashes and output sizes so the campaign
remains auditable without versioning response dumps.

The report is a decision aid, not an automatic production verdict. It must not
be used to change `validation_agent_model` without a separate decision and
runtime settings lot.

## Web search comparison benchmark

The web search suite compares three arms by default:

- `local`: current FridaDev local pipeline, SearXNG + Crawl4AI + existing web
  reformulation when needed;
- `openrouter_exa`: OpenRouter `openrouter:web_search` with `engine=exa`;
- `openrouter_parallel`: OpenRouter `openrouter:web_search` with
  `engine=parallel`.

The first campaign is intentionally bounded:

- `max_results=5`;
- `max_total_results=5`;
- `search_context_size=low`;
- default benchmark model: `openai/gpt-5.1`.

Dry run without SearXNG, Crawl4AI or OpenRouter calls:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --dry-run \
  --campaign-id dry-run-web-search \
  --output-dir /tmp/fridadev-web-search-dry-run
```

Example live comparison:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite web_search \
  --campaign-id <date>-web-search-comparison \
  --output-dir /tmp/fridadev-web-search-live
```

Operator documentation lives in:

- `benchmark/web-search/README.md`

Fixtures live in:

- `benchmark/suites/web_search/fixtures/cases.json`

The suite writes JSON, JSONL and Markdown artifacts with source domains,
latency, estimated cost, OpenRouter web request counts when reported, and local
pipeline signals such as `read_state`, `collection_path`,
`used_content_kinds`, `injected_chars` and `context_chars`. It does not use the
deprecated OpenRouter web plugin syntax or `:online` model variants.

It also writes one Markdown report per system (`local.md`,
`openrouter-exa.md`, `openrouter-parallel.md`) so the five cases can be read in
the same order across the three approaches.

## Scope

This workspace is outside the nominal chat runtime. It must not change
production model settings. Future suites should add caller-specific fixtures
and scorers under `benchmark/suites/<caller>/` while reusing the common
execution, transport and reporting code in `benchmark/core/`.
