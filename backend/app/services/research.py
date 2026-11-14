from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from .extraction import search_query
from .text import overlap_score, split_sentences

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ProofLoopAI/1.0 (evidence verification hackathon demo; https://example.invalid)"
STALE_AFTER = timedelta(days=365 * 3)
MAX_PAGES = 3


class ResearchError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def fetch_sources(claim_text: str) -> list[dict]:
    """Return real Wikipedia pages with excerpts relevant to one claim."""
    query = search_query(claim_text)
    if not query:
        return []
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": str(MAX_PAGES),
        "prop": "extracts|info",
        "inprop": "url",
        "explaintext": "1",
        "exchars": "3500",
        "exsectionformat": "plain",
        "format": "json",
        "formatversion": "2",
        "utf8": "1",
    }
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": USER_AGENT}, follow_redirects=False) as client:
            response = client.get(WIKI_API, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ResearchError(f"Wikipedia request failed: {exc.__class__.__name__}") from exc

    pages = payload.get("query", {}).get("pages", [])
    if not isinstance(pages, list):
        return []
    results = []
    retrieved_at = _now()
    for page in pages:
        title = page.get("title", "Untitled")
        if title.endswith("(disambiguation)"):
            continue
        extract = page.get("extract") or ""
        if not extract.strip() or page.get("missing"):
            continue
        excerpt = _best_excerpt(claim_text, extract)
        if not excerpt:
            continue
        updated = page.get("touched")
        updated_at = _parse_timestamp(updated)
        stale = bool(updated_at and datetime.now(timezone.utc) - updated_at > STALE_AFTER)
        results.append(
            {
                "page_id": page.get("pageid"),
                "title": page.get("title", "Untitled"),
                "url": page.get("fullurl")
                or f"https://en.wikipedia.org/?curid={page.get('pageid', '')}",
                "excerpt": excerpt,
                "updated_at": updated,
                "retrieved_at": retrieved_at,
                "stale": stale,
                "extract_chars": len(extract),
            }
        )
    return results


def excerpt_from_url(url: str, claim_text: str) -> dict:
    """Fetch a public page safely and return the passage most relevant to the claim.

    Search snippets are never used as excerpts: only text retrieved from the page is returned.
    """
    from .ingest import IngestError, fetch_url

    try:
        text = fetch_url(url)
    except IngestError as exc:
        return {
            "excerpt": None,
            "locator": None,
            "accessible": False,
            "note": str(exc),
        }
    excerpt = _best_excerpt(claim_text, text)
    if not excerpt:
        return {
            "excerpt": None,
            "locator": "retrieved page text",
            "accessible": True,
            "note": "No passage on the retrieved page matched the claim closely enough.",
        }
    return {
        "excerpt": excerpt,
        "locator": "retrieved page text",
        "accessible": True,
        "note": None,
    }


def _best_excerpt(claim_text: str, extract: str) -> Optional[str]:
    best: Optional[tuple[float, str]] = None
    sentences = split_sentences(extract)
    for index, sentence in enumerate(sentences):
        if len(sentence) < 20:
            continue
        score, shared = overlap_score(claim_text, sentence)
        if len(shared) < 2:
            continue
        if score < 0.3:
            continue
        excerpt = sentence
        if len(sentence) < 60 and index + 1 < len(sentences):
            excerpt = f"{sentence} {sentences[index + 1]}"
        if best is None or score > best[0]:
            best = (score, excerpt.strip())
    if best is None:
        return None
    return re.sub(r"\s+", " ", best[1])[:900]
