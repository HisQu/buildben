"""Tests for Buildben's release checks."""

from __future__ import annotations

from dataclasses import replace

import pytest

from buildben_dev.packaging import release_notes
from buildben_dev.packaging.install_smoke import (
    REQUIRED_RESOURCES,
    InstallSnapshot,
    validate_install_snapshot,
)


def sample_changelog(unreleased_entry: str = "") -> str:
    """Return a compact changelog accepted by the release-note parser.

    :param unreleased_entry: Optional unprepared release entry.
    :return: Changelog fixture text.
    """
    return f"""# Changelog

## Table Of Contents

1. [Changelog](#changelog)
2. [\\[Unreleased\\]](#unreleased)
3. [\\[1.2.3\\] - 2026-08-31](#123---2026-08-31)

# [Unreleased]

### 💥 Breaking Change Summary

### ➕ Added

{unreleased_entry}

### 💔 Changed

### ⚠️ Deprecated

### 🗑️ Removed

### 🔨 Fixed

# [1.2.3] - 2026-08-31

### ➕ Added

- Add a tested release workflow.
"""


def test_release_notes_extract_a_prepared_release() -> None:
    """Release notes should preserve entries and promote category headings."""
    assert release_notes.build_release_notes(sample_changelog(), "1.2.3") == (
        "## ➕ Added\n\n- Add a tested release workflow.\n"
    )


def test_release_notes_reject_unprepared_entries() -> None:
    """A tag must not release entries still left under ``[Unreleased]``."""
    with pytest.raises(ValueError, match="still contains release entries"):
        release_notes.build_release_notes(sample_changelog("- Not released."), "1.2.3")


def test_release_notes_require_matching_tag_and_version() -> None:
    """The tag must identify the version in package metadata."""
    release_notes.validate_tag_version("v1.2.3", "1.2.3")
    with pytest.raises(ValueError, match="does not match project version"):
        release_notes.validate_tag_version("v1.2.4", "1.2.3")


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
