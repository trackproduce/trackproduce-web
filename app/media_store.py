"""Uploaded media in production: a ``FileStore`` backed by Vercel Blob.

A Vercel Function runs on a read-only filesystem, so the ``LocalFileStore`` the site
uses in development has nowhere to write once deployed. Blob is the object store Vercel
offers for that, and it serves its files from its own CDN domain — so a picture the
content editor uploads is read back without ever invoking the function.

Vercel ships no Python SDK for Blob, only a JavaScript one, so this speaks the same REST
API that SDK speaks: one PUT, one JSON response, over stdlib ``urllib`` rather than a
new dependency.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from sitecopy import FileStore
from sitecopy.media import MediaKind

API_URL = "https://blob.vercel-storage.com"
# The API refuses a version it does not know, so this number tracks Vercel's SDK rather
# than this site: if uploads start failing with a 4xx after a Blob release, bump it.
API_VERSION = "10"
# A year. Safe because the stored name is the hash of the bytes, so a given URL can
# never come to mean different bytes.
CACHE_MAX_AGE = "31536000"
UPLOAD_TIMEOUT = 30  # seconds


class VercelBlobStore(FileStore):
    """Store uploads in a Vercel Blob store, under the hash of their bytes.

    The name is ``sha1(bytes)[:16] + ext``, exactly as ``LocalFileStore`` names a file:
    re-uploading the same picture resolves to the same URL instead of filling the version
    history with duplicates, and a client-supplied filename — the classic path-traversal
    vector — never reaches the store.
    """

    def __init__(self, token: str, prefix: str = "uploads") -> None:
        self._token = token
        self._prefix = prefix.strip("/")

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    def save(self, data: bytes, kind: MediaKind) -> str:
        name = hashlib.sha1(data).hexdigest()[:16] + kind.ext
        pathname = f"{self._prefix}/{name}" if self._prefix else name
        # ``quote`` leaves "/" alone, which is what Blob wants: a pathname's slashes are
        # the folders a file is filed under, not characters to escape.
        request = urllib.request.Request(
            f"{API_URL}/?pathname={urllib.parse.quote(pathname)}",
            data=data,
            method="PUT",
            headers={
                "access": "public",
                "authorization": f"Bearer {self._token}",
                "x-api-version": API_VERSION,
                "x-content-type": kind.content_type,
                "x-cache-control-max-age": CACHE_MAX_AGE,
                # The name is the content hash, so a pathname that already exists holds
                # these very bytes and overwriting it changes nothing. Without this the
                # API rejects the second upload of a file the editor already has.
                "x-allow-overwrite": "1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            # The body carries the reason (a stale x-api-version, a revoked token, a
            # store over quota). Losing it would leave nothing but "500" in the log.
            detail = error.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"Vercel Blob refused the upload ({error.code}): {detail}"
            ) from error
        url = payload.get("url")
        if not url:
            raise RuntimeError(f"Vercel Blob returned no URL for {pathname}: {payload}")
        return url
