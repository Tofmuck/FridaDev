from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


def _resolve_app_dir() -> Path:
    cwd = Path.cwd()
    if (cwd / "server.py").exists() and (cwd / "memory").exists():
        return cwd
    for parent in Path(__file__).resolve().parents:
        if (parent / "server.py").exists() and (parent / "memory").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import mutable_identity_judge  # noqa: E402


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _window_pairs() -> list[list[dict[str, str]]]:
    return [
        [
            {
                "role": "user",
                "content": "Je suis quelqu'un qui veut que les systemes disent clairement ce qu'ils peuvent reellement tenir.",
            },
            {
                "role": "assistant",
                "content": "Je suis une voix qui prefere eclairer plutot que contester par reflexe.",
            },
        ],
        [
            {"role": "user", "content": "Peux-tu reformuler ce paragraphe localement ?"},
            {"role": "assistant", "content": "Oui, je peux le reformuler sans en faire une identite."},
        ],
        [
            {"role": "user", "content": "Aujourd'hui je suis fatigue, donc allons doucement."},
            {
                "role": "assistant",
                "content": "Je le traite comme un etat du jour, pas comme une continuite durable.",
            },
        ],
        [
            {"role": "user", "content": "Quelle est la meteo abstraite de ce test ?"},
            {"role": "assistant", "content": "C'est seulement un bruit contextuel dans la conversation."},
        ],
        [
            {
                "role": "user",
                "content": "Je veux que tu distingues toujours ce que tu peux tenir de ce que tu supposes.",
            },
            {
                "role": "assistant",
                "content": "Je ne dois pas promettre une memoire durable sans mecanisme qui la porte.",
            },
        ],
        [
            {"role": "user", "content": "Sixieme tour: fais juste une liste courte de deux points."},
            {"role": "assistant", "content": "Premier point, puis second point. Rien de canonique ici."},
        ],
    ]


def _content_free_contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    verdicts = [_mapping(item) for item in _list(contract.get("verdicts"))]
    allowed_refs = {f"pair_{index:02d}" for index in range(1, mutable_identity_judge.WINDOW_PAIRS_COUNT + 1)}
    noise_terms = ("fatigue", "meteo", "reformuler", "sixieme")
    persist_subjects = sorted(
        {
            str(item.get("subject") or "")
            for item in verdicts
            if str(item.get("verdict") or "") == "persist"
        }
    )
    proposition_fingerprints = [
        {
            "subject": str(item.get("subject") or ""),
            "operation": str(item.get("operation") or ""),
            "chars": len(str(item.get("proposition") or "")),
            "sha256_12": _short_hash(str(item.get("proposition") or "")),
        }
        for item in verdicts
        if str(item.get("verdict") or "") == "persist"
    ]
    return {
        "verdict_count": len(verdicts),
        "all_no_change": bool(verdicts) and all(str(item.get("verdict") or "") == "no_change" for item in verdicts),
        "persist_subjects": persist_subjects,
        "llm_persist": "llm" in persist_subjects,
        "user_persist": "user" in persist_subjects,
        "source_refs_valid": all(
            ref in allowed_refs
            for item in verdicts
            for ref in _list(item.get("source_refs"))
        ),
        "noise_persisted_count": sum(
            1
            for item in verdicts
            if str(item.get("verdict") or "") == "persist"
            and any(term in str(item.get("proposition") or "").lower() for term in noise_terms)
        ),
        "proposition_fingerprints": proposition_fingerprints,
    }


def main() -> int:
    synthetic_pairs = _window_pairs()
    judge_input = mutable_identity_judge.build_judge_input(
        window_pairs=synthetic_pairs[: mutable_identity_judge.WINDOW_PAIRS_COUNT],
        identities={
            "llm": {
                "static": "Frida est une assistante de developpement attentive aux limites reelles du systeme.",
                "mutable_current": "",
            },
            "user": {
                "static": "Utilisateur synthetique de validation Lot 7.",
                "mutable_current": "",
            },
        },
        mutable_budget={"target_chars": 1200, "max_chars": 3300},
        source_annotations={
            "smoke": {
                "kind": "synthetic_lot7_real_llm",
                "live_db_write": False,
                "persistence": "disabled",
                "held_back_pairs_count": len(synthetic_pairs) - mutable_identity_judge.WINDOW_PAIRS_COUNT,
            }
        },
    )
    settings = mutable_identity_judge.runtime_model_settings()
    result = mutable_identity_judge.run_mutable_identity_judge(judge_input)
    contract = _mapping(result.get("contract"))
    summary = {
        "smoke": "mutable_identity_judge_real_llm",
        "model": settings.get("model"),
        "slot": mutable_identity_judge.MODEL_SLOT,
        "prompt_kind": mutable_identity_judge.PROMPT_KIND,
        "status": result.get("status"),
        "reason_code": result.get("reason_code"),
        "live_db_write": False,
        "window_pairs_sent": mutable_identity_judge.WINDOW_PAIRS_COUNT,
        "held_back_pairs_count": len(synthetic_pairs) - mutable_identity_judge.WINDOW_PAIRS_COUNT,
        "observability": result.get("observability"),
        "contract": _content_free_contract_summary(contract),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if result.get("status") != "ok":
        return 2
    contract_summary = summary["contract"]
    if contract_summary["all_no_change"]:
        return 3
    if not contract_summary["llm_persist"] or not contract_summary["user_persist"]:
        return 4
    if not contract_summary["source_refs_valid"]:
        return 5
    if contract_summary["noise_persisted_count"]:
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
