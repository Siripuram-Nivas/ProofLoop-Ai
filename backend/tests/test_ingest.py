from __future__ import annotations

import pytest

from app.services.ingest import (
    IngestError,
    clean_filename,
    detect_kind,
    html_to_text,
    validate_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://[::1]/",
        "file:///etc/passwd",
        "https://user:pass@example.com/",
        "https://example.local/",
    ],
)
def test_rejects_ssrf_targets(url):
    with pytest.raises(IngestError):
        validate_url(url)


@pytest.mark.parametrize("url", ["https://example.com/article", "http://example.org/a?b=1"])
def test_accepts_public_urls(url):
    assert validate_url(url) == url


def test_clean_filename_removes_paths():
    assert clean_filename("..\\..\\secret.pdf") == "secret.pdf"
    assert "/" not in clean_filename("a/b/c.txt")


def test_detect_kind():
    assert detect_kind("report.pdf", "application/pdf") == "pdf"
    assert detect_kind("notes.txt", "text/plain") == "text"
    assert detect_kind("shot.png", "image/png") == "image"
    assert detect_kind("evil.exe", "application/octet-stream") is None


def test_html_to_text_strips_scripts_and_markup():
    html = "<html><script>alert(1)</script><p>Hello <b>world</b>.</p></html>"
    text = html_to_text(html)
    assert "alert" not in text
    assert "Hello world" in text
