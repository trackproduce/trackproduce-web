"""The Vercel Blob file store: what it puts on the wire, and what it makes of the answer.

Uploads only happen in the deployed environment, where a mistake surfaces as a broken
"cambiar imagen" and nothing else, so the request itself is worth pinning down here.
No network: every test swaps in a fake ``urlopen`` and reads the request it was handed.
"""
from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest
from sitecopy.media import MediaKind

from app.media_store import VercelBlobStore

PNG = MediaKind("image", ".png", "image/png")
MP4 = MediaKind("video", ".mp4", "video/mp4")


class _Response(io.BytesIO):
    """Just enough of an HTTP response for ``json.load`` inside a ``with``."""

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Capture the requests the store makes, answering each with a plausible URL."""
    captured: list[Any] = []

    def fake_urlopen(request: Any, timeout: int | None = None) -> _Response:
        captured.append(request)
        return _Response(
            json.dumps({"url": "https://store.public.blob.vercel-storage.com/x.png"}).encode()
        )

    monkeypatch.setattr("app.media_store.urllib.request.urlopen", fake_urlopen)
    return captured


def test_the_upload_is_a_put_of_the_bytes_under_a_content_addressed_name(sent: list[Any]) -> None:
    store = VercelBlobStore("tok_123")

    store.save(b"the bytes", PNG)

    request = sent[0]
    assert request.method == "PUT"
    assert request.data == b"the bytes"
    # sha1("the bytes")[:16] — the name says nothing about who uploaded it or what they
    # called their file.
    assert request.full_url == (
        "https://blob.vercel-storage.com/?pathname=uploads/7be32645e0437bfb.png"
    )


def test_the_headers_carry_the_token_the_type_and_the_year_long_cache(sent: list[Any]) -> None:
    store = VercelBlobStore("tok_123")

    store.save(b"clip", MP4)

    # urllib lowercases header names it is given.
    headers = sent[0].headers
    assert headers["Authorization"] == "Bearer tok_123"
    assert headers["X-content-type"] == "video/mp4"
    assert headers["X-cache-control-max-age"] == "31536000"
    assert headers["Access"] == "public"
    # Re-uploading a file the editor already has must not be an error: same bytes, same
    # name, same URL.
    assert headers["X-allow-overwrite"] == "1"


def test_the_same_bytes_always_land_on_the_same_url(sent: list[Any]) -> None:
    store = VercelBlobStore("tok_123")

    store.save(b"same", PNG)
    store.save(b"same", PNG)

    assert sent[0].full_url == sent[1].full_url


def test_a_prefix_scopes_the_uploads_inside_the_store(sent: list[Any]) -> None:
    store = VercelBlobStore("tok_123", prefix="media/")

    store.save(b"x", PNG)

    assert "pathname=media/" in sent[0].full_url


def test_the_store_is_disabled_without_a_token() -> None:
    assert VercelBlobStore("").enabled is False
    assert VercelBlobStore("tok_123").enabled is True


def test_a_refusal_from_the_api_says_what_the_api_said(monkeypatch: pytest.MonkeyPatch) -> None:
    """The body explains it (stale api version, revoked token, quota) — keep it."""

    def fake_urlopen(request: Any, timeout: int | None = None) -> None:
        raise urllib.error.HTTPError(
            request.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"error":"invalid token"}')
        )

    monkeypatch.setattr("app.media_store.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="invalid token"):
        VercelBlobStore("tok_123").save(b"x", PNG)


def test_an_answer_without_a_url_is_an_error_rather_than_a_broken_picture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Any, timeout: int | None = None) -> _Response:
        return _Response(json.dumps({"pathname": "uploads/x.png"}).encode())

    monkeypatch.setattr("app.media_store.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="no URL"):
        VercelBlobStore("tok_123").save(b"x", PNG)


def test_the_store_is_chosen_by_whether_a_blob_token_is_around(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one switch between the deployed site and a laptop, so worth pinning down."""
    from sitecopy import LocalFileStore

    from app.factory import file_store

    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    assert isinstance(file_store("/tmp/uploads"), LocalFileStore)

    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "tok_123")
    assert isinstance(file_store("/tmp/uploads"), VercelBlobStore)
