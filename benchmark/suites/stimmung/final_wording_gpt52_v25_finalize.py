from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from benchmark.suites.stimmung import final_wording_gpt52_v25 as campaign_v25
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("v25_call_ledger_invalid")
    return value


def finalize_campaign(
    *,
    repo_root: Path,
    freeze_commit: str,
    campaign_dir: Path,
    rating_packet_path: Path,
    ratings_path: Path,
    durable_output: Path,
    ratification_path: Path | None = None,
) -> dict[str, Any]:
    """Finalize v2.5 offline without altering its frozen provider runner."""

    protocol = campaign_v25.build_protocol(repo_root, freeze_commit=freeze_commit)
    expected_private, expected_review = campaign_v25.expected_live_campaign_paths(
        protocol
    )
    if (
        campaign_dir.resolve() != expected_private.resolve()
        or rating_packet_path.resolve()
        != (expected_review / "rating_packet.json").resolve()
        or ratings_path.resolve() != (expected_review / "ratings.json").resolve()
    ):
        raise ValueError("v25_finalization_paths_invalid")

    ledger_path = campaign_dir.resolve() / "call_ledger.json"
    if not ledger_path.is_file():
        raise ValueError("v25_call_ledger_missing")
    ledger = _load_object(ledger_path)
    expected_provenance: Mapping[str, Any] = {
        "freeze_commit": freeze_commit,
        "protocol_sha256": protocol_v2.protocol_sha256(protocol),
        "schedule_sha256": protocol["schedule_sha256"],
        "campaign_status": "human_rating_required",
        "terminal_reason_code": None,
        "attempted_call_count": campaign_v25.EXPECTED_CALLS,
        "completed_call_count": campaign_v25.EXPECTED_CALLS,
        "unknown_outcome_count": 0,
        "outputs_complete": True,
        "status_counts": {"valid": campaign_v25.EXPECTED_CALLS},
        "finish_reason_counts": {"stop": campaign_v25.EXPECTED_CALLS},
        "observed_model_counts": {
            campaign_v25.TARGET_MODEL: campaign_v25.EXPECTED_CALLS
        },
    }
    if any(ledger.get(key) != value for key, value in expected_provenance.items()):
        raise ValueError("v25_call_ledger_provenance_invalid")
    campaign_v25._normalize_v25_ledger(ledger, require_complete=True)

    with campaign_v25._campaign_profile():
        artifact = rating_v2.finalize_campaign(
            campaign_dir=campaign_dir,
            rating_packet_path=rating_packet_path,
            ratings_path=ratings_path,
            ratification_path=ratification_path,
            durable_output=durable_output,
        )

    if artifact.get("decision") is None:
        return artifact
    if (
        artifact.get("call_count") != campaign_v25.EXPECTED_CALLS
        or artifact.get("outputs_complete") is not True
        or artifact.get("route_counts", {}).get("models")
        != {campaign_v25.TARGET_MODEL: campaign_v25.EXPECTED_CALLS}
        or artifact.get("observed_cost_usd") != ledger.get("observed_cost_usd")
    ):
        raise ValueError("v25_durable_evidence_mismatch")
    rating_v2.validate_durable_artifact(artifact)
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lot 4C.4 v2.5 offline human-rating finalizer"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--rating-packet", type=Path, required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    parser.add_argument("--tof-ratification", type=Path)
    parser.add_argument("--durable-output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = finalize_campaign(
        repo_root=args.repo_root,
        freeze_commit=args.freeze_commit,
        campaign_dir=args.campaign_dir,
        rating_packet_path=args.rating_packet,
        ratings_path=args.ratings,
        ratification_path=args.tof_ratification,
        durable_output=args.durable_output,
    )
    print(
        _compact_json(
            {
                "status": artifact.get("status", "finalized"),
                "decision": artifact.get("decision"),
                "call_count": artifact.get("call_count"),
                "rating_count": artifact.get("rating_count"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
