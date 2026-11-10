from __future__ import annotations

from app.services.extraction import extract_claims, split_claims
from app.services.text import (
    extract_dates,
    extract_entities,
    extract_numbers,
    number_mentions,
    overlap_score,
    split_sentences,
)


def test_splits_multi_predicate_sentence():
    claims = split_claims(
        "Company X was founded in 2010, has 5,000 employees, and operates in 20 countries."
    )
    texts = [claim["text"] for claim in claims]
    assert len(texts) == 3
    assert all(text.startswith("Company X") for text in texts)
    assert any("founded in 2010" in text for text in texts)
    assert any("5,000 employees" in text for text in texts)
    assert any("20 countries" in text for text in texts)


def test_does_not_split_apposition():
    claims = split_claims("Paris, the capital of France, has 2.1 million people.")
    assert len(claims) == 1
    assert "capital of France" in claims[0]["text"]


def test_splits_sentences_and_semicolons():
    claims = split_claims(
        "The bridge opened in 1937. It spans 1,280 metres; it carries six lanes."
    )
    assert len(claims) == 3


def test_preserves_original_span_and_deduplicates():
    text = "The tower is 330 metres tall. The tower is 330 metres tall."
    claims = split_claims(text)
    assert len(claims) == 1
    assert claims[0]["original_span"]


def test_numbers_dates_entities():
    text = "Acme Corp reported revenue of 12,500 million dollars in 2023."
    assert 12500 in extract_numbers(text)
    assert "2023" in extract_dates(text)
    assert "Acme Corp" in extract_entities(text)


def test_bare_years_are_not_treated_as_quantities():
    assert extract_numbers("The company was founded in 2010.") == []


def test_number_context_requires_comparable_metric():
    mentions = number_mentions("The tower is 330 metres tall and 120 years old.")
    assert len(mentions) == 2
    assert "metres" in mentions[0]["context"]


def test_sentence_split_handles_abbreviation():
    sentences = split_sentences("Dr. Smith works at Acme. The company is based in London.")
    assert len(sentences) == 2


def test_overlap_score_ignores_stopwords():
    score, shared = overlap_score(
        "The Eiffel Tower is 330 metres tall.",
        "The Eiffel Tower measures 330 metres.",
    )
    assert score >= 0.7
    assert "eiffel" in shared


def test_claim_cap():
    text = " ".join(f"Object {i} has {i + 10} units." for i in range(20))
    claims, engine = extract_claims(text)
    assert engine in {"deterministic", "gemini"}
    assert len(claims) <= 8
