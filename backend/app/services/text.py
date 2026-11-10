from __future__ import annotations

import re

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "that", "this", "these", "those",
    "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did", "has", "have",
    "had", "having", "will", "would", "can", "could", "should", "may", "might", "must", "shall",
    "of", "in", "on", "at", "to", "for", "from", "by", "with", "about", "as", "into", "over",
    "after", "before", "between", "under", "during", "without", "within", "across", "per",
    "it", "its", "they", "their", "them", "he", "she", "his", "her", "we", "our", "you", "your",
    "i", "my", "me", "us", "which", "who", "whom", "whose", "what", "when", "where", "why", "how",
    "not", "no", "nor", "so", "also", "very", "more", "most", "less", "least", "such", "both",
    "each", "other", "some", "any", "all", "one", "two", "three", "according", "reported",
    "reports", "said", "says", "stated", "approximately", "around", "about", "roughly", "nearly",
    "just", "only", "still", "yet", "now", "currently", "today", "there", "here", "up", "down",
    "out", "off", "again", "further", "once", "same", "too", "own", "through", "against",
}

ABBREVIATIONS = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|Inc|Ltd|Co|Corp|U\.S|U\.K|U\.N|e\.g|i\.e|No|Vol|Fig)\.(?=\s)",
    re.IGNORECASE,
)

_NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
_YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2}|2100)\b")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
_DATE_TEXT = re.compile(rf"\b(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b")
_CAPITALISED = re.compile(r"\b(?:[A-Z][A-Za-z0-9&.'-]+|[A-Z]{2,})(?:\s+(?:of|the|and|for|de|van|von)\s+[A-Z][A-Za-z0-9&.'-]+|\s+(?:[A-Z][A-Za-z0-9&.'-]+|[A-Z]{2,}))*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    text = re.sub(r"\r", " ", text)
    protected = []
    for index, match in enumerate(ABBREVIATIONS.finditer(text)):
        token = f"§{index}§"
        protected.append((token, match.group(0)))
    for token, original in protected:
        text = text.replace(original, token)
    raw = _SENTENCE_END.split(text)
    result = []
    for sentence in raw:
        for token, original in protected:
            sentence = sentence.replace(token, original)
        sentence = sentence.strip(" ,;")
        if sentence:
            result.append(sentence)
    return result


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)*", text.lower())
    return [word for word in words if word not in STOPWORDS and len(word) > 1]


def content_tokens(text: str) -> set[str]:
    return set(tokenize(text))


def overlap_score(claim: str, excerpt: str) -> tuple[float, list[str]]:
    claim_tokens = content_tokens(claim)
    if not claim_tokens:
        return 0.0, []
    excerpt_tokens = content_tokens(excerpt)
    shared = sorted(claim_tokens & excerpt_tokens)
    return len(shared) / len(claim_tokens), shared


def extract_numbers(text: str) -> list[float]:
    values = []
    for match in _NUMBER.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        if value.is_integer() and 1000 <= value <= 2100 and "," not in match.group(1):
            continue  # treat bare 4-digit values as years
        values.append(value)
    return values


def extract_years(text: str) -> list[int]:
    years = [int(match.group(1)) for match in _YEAR.finditer(text)]
    for match in _DATE_TEXT.finditer(text):
        years.extend(int(y) for y in re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", match.group(0)))
    return sorted(set(years))


def number_mentions(text: str) -> list[dict]:
    """Numbers with a small context window so we only compare the same metric."""
    mentions = []
    for match in _NUMBER.finditer(text):
        raw = match.group(1)
        value = float(raw.replace(",", ""))
        if value.is_integer() and 1000 <= value <= 2100 and "," not in raw:
            continue
        window = text[max(0, match.start() - 42): min(len(text), match.end() + 42)]
        mentions.append(
            {
                "value": value,
                "raw": raw,
                "context": content_tokens(window) - {raw.replace(",", "")},
            }
        )
    return mentions


def year_mentions(text: str) -> list[dict]:
    mentions = []
    for match in _YEAR.finditer(text):
        window = text[max(0, match.start() - 42): min(len(text), match.end() + 42)]
        mentions.append({"value": int(match.group(1)), "context": content_tokens(window)})
    return mentions


def extract_entities(text: str) -> list[str]:
    found: list[str] = []
    for match in _CAPITALISED.finditer(text):
        value = match.group(0).strip(" .,'\"")
        if len(value) < 2:
            continue
        if value.lower() in {"the", "a", "an", "this", "that", "these", "those"}:
            continue
        if value not in found:
            found.append(value)
    return found[:8]


def extract_dates(text: str) -> list[str]:
    dates = [match.group(0) for match in _DATE_TEXT.finditer(text)]
    dates.extend(match.group(0) for match in _YEAR.finditer(text))
    seen: list[str] = []
    for value in dates:
        if value not in seen:
            seen.append(value)
    return seen[:8]
