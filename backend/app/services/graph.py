from __future__ import annotations


EDGE_LABEL = {
    "supports": "supports",
    "contradicts": "contradicts",
    "insufficient": "insufficient evidence",
}


def build_graph(job: dict) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    source_ids: set[str] = set()
    evidence_ids: set[str] = set()

    for claim in job.get("claims", []):
        nodes.append(
            {
                "id": claim["id"],
                "kind": "claim",
                "label": claim["text"],
                "verdict": claim.get("verdict"),
                "category": claim.get("category"),
                "evidenceCount": len(claim.get("evidence", [])),
            }
        )
        for item in claim.get("evidence", []):
            if item["id"] not in evidence_ids:
                evidence_ids.add(item["id"])
                nodes.append(
                    {
                        "id": item["id"],
                        "kind": "evidence",
                        "label": item["excerpt"],
                        "relationship": item["relationship"],
                        "sourceTitle": item["source_title"],
                        "sourceUrl": item["source_url"],
                        "matchKind": item.get("match_kind"),
                        "stale": item.get("stale", False),
                    }
                )
            edges.append(
                {
                    "id": f"{claim['id']}-{item['id']}",
                    "source": claim["id"],
                    "target": item["id"],
                    "label": EDGE_LABEL.get(item["relationship"], item["relationship"]),
                    "kind": item["relationship"],
                }
            )
            if item["source_id"] not in source_ids:
                source_ids.add(item["source_id"])
                nodes.append(
                    {
                        "id": item["source_id"],
                        "kind": "source",
                        "label": item["source_title"],
                        "url": item["source_url"],
                        "sourceType": item.get("source_type"),
                        "quality": item.get("quality"),
                        "retrievedAt": item.get("retrieved_at"),
                    }
                )
            edges.append(
                {
                    "id": f"{item['id']}-{item['source_id']}",
                    "source": item["id"],
                    "target": item["source_id"],
                    "label": "derived from",
                    "kind": "derived_from",
                }
            )

    return {"nodes": nodes, "edges": edges}
