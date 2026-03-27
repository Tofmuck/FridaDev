# Phase 0 - Baseline technique

Date UTC: 2026-03-22 14:50:28
Conversations exportees (anonymisees): 24

## Cas limites detectes
- Ironie: 2
- Role-play: 0
- Humeur: 4
- Contradiction: 1

## Baseline latence (ms)
- retrieve: count=20, p50=97.307, p95=126.504
- arbiter: count=20, p50=1502.593, p95=2361.564
- identity_extractor: count=20, p50=807.884, p95=1449.002

## Baseline bruit identitaire
- Taux entrees identitaires ensuite supprimees manuellement: 0.0 (0/5)
- Taux entrees scope situation injectees comme traits durables: 0.0 (0/0)

## Artefacts generes
- tests/fixtures/phase0/regression_conversations_anonymized.json
- tests/fixtures/phase0/edge_cases_anonymized.json
- tests/fixtures/phase0/baseline_metrics.json

## Notes
- Les donnees sont pseudonymisees (UUID/IP/email/host/noms/numeros).
- Les mesures latence/bruit sont executees dans le conteneur frida-mini-docker.
