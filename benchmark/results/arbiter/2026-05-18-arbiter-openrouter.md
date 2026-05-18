# Benchmark arbiter - 2026-05-18-arbiter-openrouter

- Created UTC: `2026-05-18T13:33:54Z`
- Dry run: `False`
- Prompt: `app/prompts/arbiter.txt` (`06f4a8f719d5`)
- Fixtures: `benchmark/suites/arbiter/fixtures/arbiter_memory_cases.json` (`9818cdf088d3`)
- Fixed parameters: `temperature=0`, `top_p=1.0`, `max_tokens=600`

## What this campaign measures

- Whether each model returns valid arbiter JSON for the production arbiter prompt.
- Whether each model keeps or drops the expected memory candidates on diagnostic fixtures.
- False positives, false negatives, latency, provider errors and estimated cost when available.

## What this campaign does not prove

- It is not a general model benchmark.
- It does not prove behavior on the full live memory distribution.
- It does not change production runtime settings or choose the final decoupled arbiter slot by itself.

## Summary

| Model | Score | JSON valid | Schema valid | FP | FN | Avg latency | Cost est. | Provider errors | Verdict | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `openai/gpt-5.4-mini` | 100.0 | 100% | 100% | 0 | 0 | 1814 ms | $0.007481 | 0% | garder | ok on diagnostic fixtures |
| `google/gemini-3.1-flash-lite` | 100.0 | 100% | 100% | 0 | 0 | 1505 ms | $0.003462 | 0% | garder | ok on diagnostic fixtures |
| `qwen/qwen3.6-flash` | 100.0 | 100% | 100% | 0 | 0 | 3654 ms | $0.006757 | 0% | garder | ok on diagnostic fixtures |
| `mistralai/mistral-small-2603` | 100.0 | 100% | 100% | 0 | 0 | 2299 ms | $0.001534 | 0% | garder | ok on diagnostic fixtures |

## Campaign verdict

- Verdict: `garder`
- Summary: 4 model(s) are viable on the diagnostic arbiter fixtures; fastest kept model: google/gemini-3.1-flash-lite. Cheapest estimated kept model: mistralai/mistral-small-2603.
- Next step: Keep production unchanged until the bounded arbiter decoupling lot chooses the caller-local slot.

## Fixture limits

- The fixture set is intentionally small and diagnostic.
- It emphasizes French memory arbitration, redundancy, weak circumstantial memories and temporal claims.
- A production switch still needs caller-by-caller review and a bounded decoupling lot.
