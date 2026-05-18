# FridaDev benchmark workspace

`benchmark/` is the durable workspace for comparing OpenRouter models on real
FridaDev caller tasks before changing production runtime settings.

The first implemented suite is `arbiter`, which evaluates the conversational
memory arbiter with the production prompt, fixed generation parameters and a
small diagnostic fixture set.

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

## Scope

This workspace is outside the nominal chat runtime. It must not change
production model settings. Future suites should add caller-specific fixtures
and scorers under `benchmark/suites/<caller>/` while reusing the common
execution, transport and reporting code in `benchmark/core/`.
