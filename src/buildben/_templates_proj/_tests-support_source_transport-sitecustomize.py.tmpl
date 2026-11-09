"""Route exact GitHub fixture URLs to the existing loopback server in subprocesses."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


_mapping_path = os.environ.get("INSTALLER_SMOKE_URL_MAP")
if _mapping_path:
    _url_mapping = json.loads(Path(_mapping_path).read_text(encoding="utf-8"))
    if not isinstance(_url_mapping, dict) or not all(
        isinstance(source, str) and isinstance(target, str)
        for source, target in _url_mapping.items()
    ):
        raise RuntimeError("Installer smoke URL mapping is malformed.")
    _urlopen = urllib.request.urlopen

    def _fixture_urlopen(url, *args, **kwargs):
        original = (
            url.full_url if isinstance(url, urllib.request.Request) else url
        )
        if not isinstance(original, str):
            return _urlopen(url, *args, **kwargs)
        parsed = urllib.parse.urlsplit(original)
        if parsed.hostname in {
            "api.github.com",
            "raw.githubusercontent.com",
            "github.com",
        }:
            target = _url_mapping.get(original)
            if target is None:
                raise urllib.error.URLError(
                    f"No loopback fixture was configured for GitHub URL: {original}"
                )
            if isinstance(url, urllib.request.Request):
                url = urllib.request.Request(
                    target,
                    data=url.data,
                    headers=dict(url.header_items()),
                    origin_req_host=url.origin_req_host,
                    unverifiable=url.unverifiable,
                    method=url.get_method(),
                )
            else:
                url = target
        return _urlopen(url, *args, **kwargs)

    urllib.request.urlopen = _fixture_urlopen
