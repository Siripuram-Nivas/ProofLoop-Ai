from __future__ import annotations

from app.services.contradictions import detect_contradictions
from app.services.evaluation import evaluate_claim


def _candidate(excerpt: str, stale: bool = False) -> dict:
    return {
        "excerpt": excerpt,
        "source_id": "src_1",
        "title": "Example source",
        "url": "https://example.org/source",
        "source_type": "test",
        "quality": "medium",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "stale": stale,
    }


def _claim(text: str) -> dict:
    return {"id": "clm_1", "text": text}


def test_numeric_match_supports():
    evidence, verdict, _ = evaluate_claim(
        _claim("The Eiffel Tower is 330 metres tall."),
        [_candidate("The Eiffel Tower measures 330 metres (1,082 ft) in height.")],
        research_failed=False,
    )
    assert verdict == "supported"
    assert evidence[0]["relationship"] == "supports"
    assert evidence[0]["match_kind"] == "numeric"


def test_rounding_within_tolerance_supports():
    _, verdict, _ = evaluate_claim(
        _claim("Mount Everest is 8,848 metres high."),
        [_candidate("Mount Everest is 8,848.86 metres high.")],
        research_failed=False,
    )
    assert verdict == "supported"


def test_numeric_mismatch_contradicts():
    evidence, verdict, _ = evaluate_claim(
        _claim("The Eiffel Tower is 450 metres tall."),
        [_candidate("The Eiffel Tower is 330 metres tall.")],
        research_failed=False,
    )
    assert verdict == "contradicted"
    assert evidence[0]["match_kind"] == "numeric_mismatch"
    assert "330" in evidence[0]["explanation"]


def test_year_mismatch_contradicts():
    _, verdict, _ = evaluate_claim(
        _claim("The Eiffel Tower was completed in 1879."),
        [_candidate("The Eiffel Tower was completed in 1889.")],
        research_failed=False,
    )
    assert verdict == "contradicted"


def test_mixed_evidence_preserves_both_sides():
    evidence, verdict, _ = evaluate_claim(
        _claim("The bridge is 1,200 metres long."),
        [
            _candidate("The bridge is 1,200 metres long."),
            _candidate("The bridge is 900 metres long."),
        ],
        research_failed=False,
    )
    assert verdict == "mixed"
    relationships = {item["relationship"] for item in evidence}
    assert relationships == {"supports", "contradicts"}


def test_weak_overlap_is_insufficient():
    _, verdict, _ = evaluate_claim(
        _claim("The company opened a new factory in 2020."),
        [_candidate("The company published a new factory safety policy for employees.")],
        research_failed=False,
    )
    assert verdict == "insufficient"


def test_no_evidence_is_unverified_not_false():
    _, verdict, basis = evaluate_claim(
        _claim("The company has 5,000 employees."), [], research_failed=False
    )
    assert verdict == "unverified"
    assert "not evidence that the claim is false" in basis


def test_research_failure_is_inconclusive():
    _, verdict, _ = evaluate_claim(
        _claim("The company has 5,000 employees."), [], research_failed=True
    )
    assert verdict == "inconclusive"


def test_stale_support_becomes_outdated():
    _, verdict, _ = evaluate_claim(
        _claim("The population is 8 million."),
        [_candidate("The population of the region is 8 million.", stale=True)],
        research_failed=False,
    )
    assert verdict == "outdated"


def test_contradiction_detection_groups_by_claim():
    claim = _claim("The tower is 450 metres tall.")
    evidence, verdict, _ = evaluate_claim(
        claim, [_candidate("The tower is 330 metres tall.")], research_failed=False
    )
    claim["evidence"] = evidence
    claim["verdict"] = verdict
    contradictions = detect_contradictions([claim])
    assert len(contradictions) == 1
    assert contradictions[0]["kind"] == "numeric_mismatch"
    assert contradictions[0]["evidence_ids"] == [evidence[0]["id"]]
