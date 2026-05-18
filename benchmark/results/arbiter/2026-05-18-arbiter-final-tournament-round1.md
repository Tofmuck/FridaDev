# Benchmark arbiter - 2026-05-18-arbiter-final-tournament-round1

- Created UTC: `2026-05-18T14:06:20Z`
- Dry run: `False`
- Prompt: `app/prompts/arbiter.txt` (`06f4a8f719d5`)
- Fixtures: `benchmark/suites/arbiter/fixtures/arbiter_tournament_round1.jsonl` (`a75917a4c1a4`)
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
| `openai/gpt-5.4-mini` | 93.5 | 92.0 | 100% | 100% | 4 | 0 | 1836 ms | $0.048800 | 0% | tester plus | 4 FP |
| `google/gemini-3.1-flash-lite` | 93.5 | 92.0 | 100% | 100% | 4 | 0 | 1362 ms | $0.022613 | 0% | tester plus | 4 FP |
| `qwen/qwen3.6-flash` | 0.0 | 0.0 | 0% | 0% | 0 | 36 | 308 ms | n/a | 100% | exclure | 40 provider error(s), schema issues, 36 FN |
| `mistralai/mistral-small-2603` | 95.2 | 94.0 | 98% | 98% | 1 | 2 | 2033 ms | $0.007131 | 0% | tester plus | schema issues, 1 FP, 2 FN |

## Campaign verdict

- Verdict: `tester plus`
- Summary: No model is ready to replace the arbiter on this diagnostic set, but at least one deserves another campaign.
- Next step: Broaden arbiter fixtures before any runtime decoupling decision.

## Fixture limits

- The fixture set is intentionally small and diagnostic.
- It emphasizes French memory arbitration, redundancy, weak circumstantial memories and temporal claims.
- A production switch still needs caller-by-caller review and a bounded decoupling lot.
