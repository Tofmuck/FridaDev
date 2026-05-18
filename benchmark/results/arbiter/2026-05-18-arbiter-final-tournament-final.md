# Benchmark arbiter - 2026-05-18-arbiter-final-tournament-final

- Created UTC: `2026-05-18T14:08:41Z`
- Dry run: `False`
- Prompt: `app/prompts/arbiter.txt` (`06f4a8f719d5`)
- Fixtures: `benchmark/suites/arbiter/fixtures/arbiter_tournament_final.jsonl` (`a167c0e49534`)
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

| Model | Weighted score | Hard score | JSON valid | Schema valid | FP | FN | Avg latency | Cost est. | Provider errors | Verdict | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `mistralai/mistral-small-2603` | 98.9 | 98.7 | 100% | 100% | 1 | 0 | 1037 ms | $0.007838 | 0% | garder | 1 FP |
| `google/gemini-3.1-flash-lite` | 95.7 | 94.8 | 100% | 100% | 4 | 0 | 1305 ms | $0.033561 | 0% | tester plus | 4 FP |

## Campaign verdict

- Verdict: `garder`
- Summary: 1 model(s) are viable on the diagnostic arbiter fixtures; fastest kept model: mistralai/mistral-small-2603. Cheapest estimated kept model: mistralai/mistral-small-2603.
- Next step: Keep production unchanged until the bounded arbiter decoupling lot chooses the caller-local slot.

## Fixture limits

- The fixture set is intentionally small and diagnostic.
- It emphasizes French memory arbitration, redundancy, weak circumstantial memories and temporal claims.
- A production switch still needs caller-by-caller review and a bounded decoupling lot.
