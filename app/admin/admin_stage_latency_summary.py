from __future__ import annotations

from math import ceil, floor
from typing import Any, Dict, List


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    rank = max(0.0, min(1.0, p)) * (len(vals) - 1)
    lo = int(floor(rank))
    hi = int(ceil(rank))
    if lo == hi:
        return float(vals[lo])
    weight = rank - lo
    return float(vals[lo] * (1.0 - weight) + vals[hi] * weight)


def compute_stage_latencies(log_entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, List[float]] = {
        'retrieve': [],
        'arbiter': [],
        'identity_extractor': [],
    }
    for entry in log_entries:
        if entry.get('event') != 'stage_latency':
            continue
        stage = str(entry.get('stage') or '').strip()
        if stage not in buckets:
            continue
        try:
            duration = float(entry.get('duration_ms') or 0.0)
        except (TypeError, ValueError):
            continue
        if duration < 0:
            continue
        buckets[stage].append(duration)

    out: Dict[str, Dict[str, float]] = {}
    for stage, values in buckets.items():
        out[stage] = {
            'count': int(len(values)),
            'p50_ms': round(_percentile(values, 0.50), 3),
            'p95_ms': round(_percentile(values, 0.95), 3),
        }
    return out
