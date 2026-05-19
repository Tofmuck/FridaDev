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

The report is a decision aid, not an automatic production verdict. It must not
be used to change `stimmung_agent_model` without a separate decision and
runtime settings lot.

## Scope

This workspace is outside the nominal chat runtime. It must not change
production model settings. Future suites should add caller-specific fixtures
and scorers under `benchmark/suites/<caller>/` while reusing the common
execution, transport and reporting code in `benchmark/core/`.
