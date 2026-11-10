from __future__ import annotations

import io
import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlsplit

import httpx
from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_PDF_PAGES = 40
FETCH_TIMEOUT = 12.0
FETCH_MAX_BYTES = 3 * 1024 * 1024


class IngestError(Exception):
    pass


def validate_url(url: str) -> str:
    url = url.strip()
    if len(url) > 2000:
        raise IngestError("URL is too long.")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise IngestError("Only http:// and https:// URLs are supported.")
    if not parts.hostname:
        raise IngestError("URL has no hostname.")
    if parts.username or parts.password:
        raise IngestError("URLs containing credentials are not allowed.")
    host = parts.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise IngestError("Private hostnames are not allowed.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not _is_public(address):
        raise IngestError("Private or reserved network addresses are not allowed.")
    return url


def _is_public(address: ipaddress._BaseAddress) -> bool:
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _resolve_public(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise IngestError("Could not resolve the URL hostname.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not _is_public(address):
            raise IngestError("The URL resolves to a private or reserved address.")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag in {"p", "br", "div", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "div", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:  # malformed HTML must not crash ingestion
        pass
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()[:MAX_TEXT_CHARS]


def fetch_url(url: str) -> str:
    validate_url(url)
    host = urlsplit(url).hostname or ""
    _resolve_public(host)
    headers = {
        "User-Agent": "ProofLoopAI/1.0 (evidence verification; contact: maintainer)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
    }
    try:
        with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=False, headers=headers) as client:
            with client.stream("GET", url) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    raise IngestError("The URL redirects. Submit the final destination URL instead.")
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not any(kind in content_type for kind in ("text/html", "text/plain", "application/xhtml")):
                    raise IngestError("The URL did not return an HTML or text document.")
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > FETCH_MAX_BYTES:
                        raise IngestError("The page is too large to process (limit 3 MB).")
                    chunks.append(chunk)
    except IngestError:
        raise
    except httpx.HTTPError as exc:
        raise IngestError(f"Could not fetch the URL ({exc.__class__.__name__}).") from exc

    encoding = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type)
    if match:
        encoding = match.group(1)
    try:
        raw = b"".join(chunks).decode(encoding, errors="replace")
    except LookupError:
        raw = b"".join(chunks).decode("utf-8", errors="replace")
    text = html_to_text(raw) if "html" in content_type else raw.strip()[:MAX_TEXT_CHARS]
    if len(text) < 40:
        raise IngestError("The page did not contain enough readable text.")
    return text


def extract_pdf(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise IngestError("PDF is larger than the 10 MB limit.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IngestError("Encrypted PDFs are not supported. Remove the password and retry.")
        pages = reader.pages[:MAX_PDF_PAGES]
        text = "\n".join((page.extract_text() or "") for page in pages)
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError("The PDF could not be parsed. It may be corrupt or scanned.") from exc
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) < 40:
        raise IngestError(
            "No readable text was found in the PDF. Scanned PDFs need OCR, which is not enabled."
        )
    return text[:MAX_TEXT_CHARS]


def clean_filename(name: str) -> str:
    name = re.split(r"[\\/]", name or "document")[-1]
    name = re.sub(r"[^\w.\- ]", "_", name).strip()
    return (name or "document")[:120]


def detect_kind(filename: str, content_type: str) -> Optional[str]:
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension == "pdf" or content_type == "application/pdf":
        return "pdf"
    if extension in {"txt", "md", "text"} or content_type.startswith("text/"):
        return "text"
    if extension in {"png", "jpg", "jpeg", "webp"} or content_type.startswith("image/"):
        return "image"
    return None
