"""Tests for Buildben's release checks."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from buildben_dev.packaging import release_notes
from buildben_dev.packaging.install_smoke import (
    REQUIRED_RESOURCES,
    InstallSnapshot,
    validate_install_snapshot,
)


def sample_changelog(
    *,
    version: str = "1.2.3",
    unreleased_entry: str = "",
    release_entry: str = "- Add a tested release workflow.",
    toc_entry: bool = True,
) -> str:
    """Return a compact changelog accepted by the release-note parser.

    :param version: Released version heading and link value.
    :param unreleased_entry: Optional unprepared release entry.
    :param release_entry: Content placed in the released section.
    :param toc_entry: Whether to include the released version in the ToC.
    :return: Changelog fixture text.
    """
    anchor = f"#{version.replace('.', '')}---2026-08-31"
    version_toc = f"3. [\\[{version}\\] - 2026-08-31]({anchor})\n" if toc_entry else ""
    return f"""# Changelog

## Table Of Contents

1. [Changelog](#changelog)
2. [\\[Unreleased\\]](#unreleased)
{version_toc}

# [Unreleased]

### 💥 Breaking Change Summary

### ➕ Added

{unreleased_entry}

### 💔 Changed

### ⚠️ Deprecated

### 🗑️ Removed

### 🔨 Fixed

# [{version}] - 2026-08-31

### ➕ Added

{release_entry}

# [1.2.2] - 2026-08-30
"""


def test_release_notes_extract_a_prepared_release() -> None:
    """Release notes should preserve entries and promote category headings."""
    assert release_notes.build_release_notes(sample_changelog(), "1.2.3") == (
        "## ➕ Added\n\n- Add a tested release workflow.\n"
    )


def test_release_notes_reject_unprepared_entries() -> None:
    """A tag must not release entries still left under ``[Unreleased]``."""
    with pytest.raises(ValueError, match="still contains release entries"):
        release_notes.build_release_notes(
            sample_changelog(unreleased_entry="- Not released."), "1.2.3"
        )


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "1.2.3.4", "01.2.3"])
def test_release_notes_reject_malformed_versions(version: str) -> None:
    """Release versions must use three non-zero-padded numeric components."""
    with pytest.raises(ValueError, match="Invalid release version"):
        release_notes.build_release_notes(sample_changelog(), version)


def test_release_notes_reject_missing_or_duplicate_release() -> None:
    """A requested release heading must be unique."""
    with pytest.raises(ValueError, match="exactly one release heading"):
        release_notes.build_release_notes(sample_changelog(), "1.2.4")

    duplicate = sample_changelog().replace(
        "# [1.2.2] - 2026-08-30", "# [1.2.3] - 2026-08-31"
    )
    with pytest.raises(ValueError, match="found 2"):
        release_notes.build_release_notes(duplicate, "1.2.3")


def test_release_notes_reject_empty_release_or_missing_toc() -> None:
    """A release needs entries and a matching table-of-contents link."""
    with pytest.raises(ValueError, match="has no changelog entries"):
        release_notes.build_release_notes(sample_changelog(release_entry=""), "1.2.3")
    with pytest.raises(ValueError, match="table of contents"):
        release_notes.build_release_notes(sample_changelog(toc_entry=False), "1.2.3")


def test_release_notes_require_matching_tag_and_version() -> None:
    """The tag must identify the version in package metadata."""
    release_notes.validate_tag_version("v1.2.3", "1.2.3")
    with pytest.raises(ValueError, match="does not match project version"):
        release_notes.validate_tag_version("v1.2.4", "1.2.3")


def test_release_notes_validate_release_order_and_cli_arguments(tmp_path: Path) -> None:
    """The release helper should reject stale versions and partial tag checks."""
    assert release_notes.latest_release_version(sample_changelog()) == "1.2.3"
    release_notes.validate_next_version("1.2.3", "1.2.4")
    with pytest.raises(ValueError, match="must be newer"):
        release_notes.validate_next_version("1.2.3", "1.2.3")
    with pytest.raises(ValueError, match="must be provided together"):
        release_notes.main(
            [
                "1.2.3",
                "--changelog",
                str(tmp_path / "CHANGELOG.md"),
                "--output",
                str(tmp_path / "notes.md"),
                "--tag",
                "v1.2.3",
            ]
        )


def valid_snapshot() -> InstallSnapshot:
    """Return a snapshot satisfying the installed-package contract.

    :return: Complete installation snapshot.
    """
    return InstallSnapshot(
        version="1.2.3",
        module_file="/site-packages/buildben/__init__.py",
        resources=REQUIRED_RESOURCES,
        console_path="/bin/bube",
        help_returncode=0,
        help_output="usage: buildben [-h]",
    )


def test_install_smoke_contract_rejects_missing_console_script() -> None:
    """A distribution without the public command must fail the smoke check."""
    with pytest.raises(AssertionError):
        validate_install_snapshot(
            replace(valid_snapshot(), console_path=None), expected_version="1.2.3"
        )


def test_install_smoke_contract_accepts_complete_installation() -> None:
    """A complete installed package should satisfy the smoke contract."""
    validate_install_snapshot(valid_snapshot(), expected_version="1.2.3")


@pytest.mark.parametrize(
    "field,value",
    [
        ("module_file", None),
        ("resources", ()),
        ("console_path", None),
        ("help_returncode", 1),
        ("help_output", ""),
    ],
)
def test_install_smoke_contract_rejects_incomplete_installation(
    field: str, value: object
) -> None:
    """Missing public package or CLI behavior must fail the smoke check."""
    with pytest.raises(AssertionError):
        validate_install_snapshot(
            replace(valid_snapshot(), **{field: value}), expected_version="1.2.3"
        )
