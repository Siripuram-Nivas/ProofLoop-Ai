from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from ..config import settings
from .text import (
    content_tokens,
    extract_dates,
    extract_entities,
    extract_numbers,
    split_sentences,
    tokenize,
)

VERBS = {
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "do", "does", "did",
    "will", "would", "can", "could", "may", "might", "must", "shall", "should", "operates", "operate",
    "employs", "employ", "includes", "include", "owns", "own", "produces", "produce", "launched",
    "launch", "contains", "contain", "covers", "cover", "spans", "span", "sits", "sit", "lies",
    "stand", "stands", "ranks", "rank", "serves", "serve", "provides", "provide", "makes", "make",
    "sells", "sell", "recorded", "record", "generated", "generate", "won", "win", "holds", "hold",
    "grew", "grow", "increased", "increase", "decreased", "decrease", "reached", "reach", "started",
    "start", "began", "begin", "founded", "found", "became", "become", "remains", "remain", "reported",
    "report", "announced", "announce", "released", "release", "completed", "complete", "built",
    "build", "created", "create", "located", "locate", "measures", "measure", "weighs", "weigh",
    "costs", "cost", "earned", "earn", "produced", "acquired", "acquire", "merged", "merge",
    "supports", "support", "contradicts", "lists", "list", "estimated", "estimate", "has",
}
PRONOUNS = {"it", "they", "he", "she"}
CLAIM_CAP = 8


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _find_verb_index(words: list[str]) -> Optional[int]:
    for index, word in enumerate(words):
        cleaned = word.strip(".,;:!?").lower()
        if cleaned in VERBS:
            return index
    return None


def _subject_of(sentence: str) -> str:
    words = sentence.split()
    index = _find_verb_index(words)
    if index is None or index == 0:
        return ""
    subject = " ".join(words[:index]).strip(" ,;")
    if len(subject) < 2 or re.fullmatch(r"[\d.,%\s]+", subject):
        return ""
    return subject


def _clean_part(part: str) -> str:
    part = part.strip()
    part = re.sub(r"^(and|but|while|whereas)\s+", "", part, flags=re.IGNORECASE)
    return part.strip(" ,;")


def split_claims(text: str) -> list[dict]:
    """Split prose into atomic, independently checkable claims.

    The splitter is intentionally conservative: it only splits on commas/semicolons when the
    first clause already contains a finite verb, so appositions ("Paris, the capital of France")
    are never broken into fragments.
    """
    claims: list[dict] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        if not sentence:
            continue
        parts = [_clean_part(part) for part in re.split(r";\s*|,\s+(?:and\s+)?", sentence)]
        parts = [part for part in parts if part]
        split_ok = (
            len(parts) > 1
            and _find_verb_index(parts[0].split()) is not None
            and all(
                _find_verb_index(part.split()) is not None
                or part.split()[0].lower().strip(".,") in PRONOUNS
                for part in parts[1:]
            )
        )
        if not split_ok:
            parts = [sentence]
        subject = _subject_of(sentence)
        for index, part in enumerate(parts):
            candidate = part
            if split_ok and index > 0:
                first = candidate.split()[0].lower().strip(".,")
                if first in PRONOUNS:
                    candidate = " ".join(candidate.split()[1:])
                if subject:
                    candidate = f"{subject} {candidate}"
            candidate = candidate.strip(" ,;")
            if not candidate:
                continue
            if not candidate.endswith((".", "!", "?")):
                candidate += "."
            key = _normalise(candidate)
            if len(key) < 12 or key in seen:
                continue
            seen.add(key)
            claims.append(
                {
                    "text": candidate,
                    "original_span": part.strip(" ,;"),
                    "category": _categorise(candidate),
                    "entities": extract_entities(candidate),
                    "numbers": extract_numbers(candidate),
                    "dates": extract_dates(candidate),
                    "confidence": _extraction_confidence(candidate, split_ok),
                }
            )
            if len(claims) >= CLAIM_CAP:
                return claims
    if not claims and text.strip():
        sentence = re.sub(r"\s+", " ", text).strip()
        if len(sentence) >= 12:
            claims.append(
                {
                    "text": sentence if sentence.endswith((".", "!", "?")) else sentence + ".",
                    "original_span": sentence,
                    "category": "general",
                    "entities": extract_entities(sentence),
                    "numbers": extract_numbers(sentence),
                    "dates": extract_dates(sentence),
                    "confidence": 0.4,
                }
            )
    return claims


def _categorise(text: str) -> str:
    if extract_dates(text):
        return "date"
    if extract_numbers(text):
        return "quantity"
    if re.search(r"\b(according to|reported|announced|stated|claimed|said)\b", text, re.I):
        return "attribution"
    if re.search(r"\b(is|are|was|were)\b", text, re.I):
        return "identity"
    return "general"


def _extraction_confidence(text: str, split: bool) -> float:
    score = 0.55
    if extract_numbers(text):
        score += 0.12
    if extract_dates(text):
        score += 0.1
    if extract_entities(text):
        score += 0.08
    if split:
        score += 0.05
    if len(text) > 260:
        score -= 0.15
    return round(min(score, 0.95), 2)


def _gemini_claims(text: str) -> Optional[list[str]]:
    """Optional LLM-assisted extraction. Proposals must appear in the source text."""
    if not settings.gemini_api_key:
        return None
    prompt = (
        "Split the user's text into atomic, independently verifiable factual claims. "
        "Preserve names, numbers, dates and meaning exactly. One claim per array item. "
        "Do not add facts that are not in the text. Return JSON only: {\"claims\": [\"...\"]}.\n\n"
        f"TEXT:\n{text[:12000]}"
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    try:
        with httpx.Client(timeout=25) as client:
            response = client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
                },
            )
            response.raise_for_status()
            payload = response.json()
        raw = payload["candidates"][0]["content"]["parts"][0]["text"]
        proposed = json.loads(raw).get("claims", [])
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        return None
    source_norm = _normalise(text)
    valid: list[str] = []
    for claim in proposed:
        if not isinstance(claim, str):
            continue
        claim = claim.strip()
        norm = _normalise(claim)
        if len(norm) >= 12 and norm in source_norm and norm not in {_normalise(v) for v in valid}:
            valid.append(claim)
    return valid[:CLAIM_CAP] or None


def extract_claims(text: str) -> tuple[list[dict], str]:
    llm_claims = _gemini_claims(text)
    if llm_claims:
        claims = []
        for index, claim in enumerate(llm_claims):
            if not claim.endswith((".", "!", "?")):
                claim += "."
            claims.append(
                {
                    "text": claim,
                    "original_span": claim.rstrip("."),
                    "category": _categorise(claim),
                    "entities": extract_entities(claim),
                    "numbers": extract_numbers(claim),
                    "dates": extract_dates(claim),
                    "confidence": 0.85,
                }
            )
        if claims:
            return claims, "gemini"
    return split_claims(text), "deterministic"


def search_query(claim: str) -> str:
    tokens = tokenize(claim)
    return " ".join(tokens[:12])
