"""Exact application release assets and their non-self-referential integrity manifest."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, cast

MANIFEST_NAME = "release-manifest.json"
SCRIPT_SUPPORT = (
    "app-install.sh",
    "app-install.cmd",
    "bootstrap.ps1",
    "main-installer.py",
)
ZIPAPP_SUPPORT = (
    "app-install.sh",
    "app-install.cmd",
    "bootstrap.ps1",
    "main-installer.pyz",
    "management-requirements.txt",
)


def asset_basename(value: str, label: str = "Release asset") -> str:
    """Reject unsafe names before any staging or download write.

    :param value: Asset's single-component filename.
    :param label: Diagnostic context.
    :return: Unchanged safe basename.
    """
    if (
        not value
        or value in {".", ".."}
        or Path(value).name != value
        or any(character in value for character in "/\\\r\n\x00:")
    ):
        raise ValueError(f"{label} must be a safe basename.")
    return value


def expected_asset_names(
    names: Sequence[str],
    *,
    payload_format: Literal["script", "zipapp"] = "script",
) -> tuple[str, ...]:
    """Require exactly one package pair and the selected native support set.

    :param names: Explicit asset list, including the integrity manifest.
    :param payload_format: Script or explicitly selected zipapp contract.
    :return: Deterministically ordered exact asset names.
    """
    for name in names:
        asset_basename(name)
    if len(names) != len(set(names)):
        raise ValueError("Release contains duplicate asset names.")
    wheels = [name for name in names if name.endswith(".whl")]
    sdists = [name for name in names if name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Release requires exactly one wheel and one source archive.")
    if payload_format not in {"script", "zipapp"}:
        raise ValueError("Unsupported release payload format.")
    support = SCRIPT_SUPPORT if payload_format == "script" else ZIPAPP_SUPPORT
    expected = {wheels[0], sdists[0], MANIFEST_NAME, *support}
    if set(names) != expected:
        raise ValueError(
            "Release contains missing or unexpected installer/manifest assets."
        )
    return tuple(sorted(expected))


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate release manifest field: {key}.")
        value[key] = item
    return value


def _identity(app_id: str, distribution: str, version: str, commit: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", app_id) is None:
        raise ValueError("Release app_id must be one safe component.")
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", distribution) is None:
        raise ValueError("Release distribution must be normalized with hyphens.")
    if not version or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit) is None:
        raise ValueError("Release requires an explicit version and immutable commit.")


def manifest_bytes(
    payload: Mapping[str, bytes],
    *,
    app_id: str,
    distribution: str,
    version: str,
    commit: str,
    payload_format: Literal["script", "zipapp"] = "script",
) -> bytes:
    """Describe every final asset except the manifest itself.

    :param payload: Final package/native-entry bytes, with no manifest included.
    :param app_id: Persistent application identity.
    :param distribution: Normalized package identity, independent of app_id.
    :param version: Final package version.
    :param commit: Full release source commit.
    :param payload_format: Selected main installer format.
    :return: Deterministic UTF-8 JSON; no timestamp or digest cycle.
    """
    _identity(app_id, distribution, version, commit)
    if MANIFEST_NAME in payload:
        raise ValueError("Manifest must not include its own digest.")
    expected_asset_names((*payload, MANIFEST_NAME), payload_format=payload_format)
    value = {
        "schema_version": 1,
        "app_id": app_id,
        "distribution": distribution,
        "version": version,
        "commit": commit,
        "payload_format": payload_format,
        "assets": [
            {
                "filename": name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in sorted(payload.items())
        ],
    }
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def validate_manifest(
    payload: Mapping[str, bytes],
    *,
    app_id: str,
    distribution: str,
    version: str,
    commit: str,
) -> tuple[str, ...]:
    """Validate exact identities, asset set, sizes and SHA-256 before mutation.

    :param payload: Explicit final assets including release-manifest.json.
    :param app_id: Expected host identity, not taken from untrusted manifest bytes.
    :param distribution: Expected normalized package identity.
    :param version: Expected release/package version.
    :param commit: Expected immutable source commit.
    :return: Validated exact asset names.
    """
    _identity(app_id, distribution, version, commit)
    if MANIFEST_NAME not in payload:
        raise ValueError("Release is missing release-manifest.json.")
    try:
        value = json.loads(
            payload[MANIFEST_NAME].decode("utf-8"), object_pairs_hook=_unique_fields
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Release manifest is not valid UTF-8 JSON.") from error
    fields = {
        "schema_version",
        "app_id",
        "distribution",
        "version",
        "commit",
        "payload_format",
        "assets",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Release manifest has missing or unknown fields.")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["app_id"] != app_id
        or value["distribution"] != distribution
        or value["version"] != version
        or value["commit"] != commit
    ):
        raise ValueError(
            "Release manifest schema or app/distribution/version/commit identity does not match."
        )
    payload_format = value["payload_format"]
    if not isinstance(payload_format, str) or payload_format not in {
        "script",
        "zipapp",
    }:
        raise ValueError("Release manifest has an unsupported payload format.")
    names = expected_asset_names(
        tuple(payload), payload_format=cast(Literal["script", "zipapp"], payload_format)
    )
    assets = value["assets"]
    if not isinstance(assets, list):
        raise ValueError("Release manifest assets must be a list.")
    seen: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != {"filename", "size", "sha256"}:
            raise ValueError("Release manifest asset has missing or unknown fields.")
        name = asset["filename"]
        if not isinstance(name, str) or name == MANIFEST_NAME or name in seen:
            raise ValueError(
                "Release manifest contains duplicate or self-referential assets."
            )
        asset_basename(name)
        seen.add(name)
        if name not in payload:
            raise ValueError("Release manifest names a missing asset.")
        if type(asset["size"]) is not int or asset["size"] != len(payload[name]):
            raise ValueError(f"Release asset size does not match: {name}.")
        if (
            not isinstance(asset["sha256"], str)
            or asset["sha256"] != hashlib.sha256(payload[name]).hexdigest()
        ):
            raise ValueError(f"Release asset SHA-256 does not match: {name}.")
    if seen != set(payload) - {MANIFEST_NAME}:
        raise ValueError("Release manifest omits final assets.")
    return names
