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
  `e20209c45f9e6b4c17ea6bc808acd7dfe406c543543674fd298b5dbe9a93a635`).

The frozen campaign is `inconclusive`: Gemini 3.7 Flash `medium` is eligible
at `22/22`, both Luna Pro efforts are non-eligible at `18/22`, and Gemini 3.7
Flash `high` produced eleven invalid JSON results at the fixed output cap. No
runtime cutover is authorized by this result.

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
