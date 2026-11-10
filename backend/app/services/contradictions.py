from __future__ import annotations

from ..db import new_id


def detect_contradictions(claims: list[dict]) -> list[dict]:
    contradictions: list[dict] = []
    seen: set[tuple] = set()

    for claim in claims:
        evidence = claim.get("evidence", [])
        for item in evidence:
            if item["relationship"] != "contradicts":
                continue
            key = (claim["id"], item["id"], item["match_kind"])
            if key in seen:
                continue
            seen.add(key)
            if item["match_kind"] == "numeric_mismatch":
                kind = "numeric_mismatch"
                severity = "high"
            elif item["match_kind"] == "date_mismatch":
                kind = "date_mismatch"
                severity = "high"
            else:
                kind = "source_disagreement"
                severity = "medium"
            contradictions.append(
                {
                    "id": new_id("con"),
                    "claim_id": claim["id"],
                    "claim_text": claim["text"],
                    "kind": kind,
                    "severity": severity,
                    "summary": item["explanation"],
                    "evidence_ids": [item["id"]],
                }
            )

        # Two supporting sources that report materially different values for the same metric.
        supporting = [
            item
            for item in evidence
            if item["relationship"] == "supports" and item.get("numbers")
        ]
        reported: list[tuple[float, dict]] = []
        for item in supporting:
            for pair in item["numbers"]:
                if pair["kind"] in ("match", "near"):
                    reported.append((pair["evidence_value"], item))
        for index, (value_a, item_a) in enumerate(reported):
            for value_b, item_b in reported[index + 1:]:
                if item_a["id"] == item_b["id"]:
                    continue
                larger = max(abs(value_a), abs(value_b), 1)
                if abs(value_a - value_b) / larger <= 0.05:
                    continue
                key = (claim["id"], "disagreement", item_a["id"], item_b["id"])
                if key in seen:
                    continue
                seen.add(key)
                contradictions.append(
                    {
                        "id": new_id("con"),
                        "claim_id": claim["id"],
                        "claim_text": claim["text"],
                        "kind": "source_disagreement",
                        "severity": "medium",
                        "summary": (
                            f"Two sources report different values ({value_a:,.4g} vs {value_b:,.4g}). "
                            "They are not reconciled automatically; check their reporting dates and definitions."
                        ),
                        "evidence_ids": [item_a["id"], item_b["id"]],
                    }
                )
    return contradictions
