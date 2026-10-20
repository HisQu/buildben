"""Tests for Buildben's release checks."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from buildben_dev.packaging import release_notes
from buildben_dev.packaging.install_smoke import (
    REQUIRED_RESOURCES,
    InstallSnapshot,
    validate_install_snapshot,
)


def _manual_pypi_preflight_script(workflow_path: Path) -> str:
    """Extract the manual PyPI preflight shell script from a release workflow."""
    workflow_text = workflow_path.read_text(encoding="utf-8")
    preflight = workflow_text.split("  manual_pypi_preflight:\n", 1)[1].split(
        "  publish-existing-release:\n", 1
    )[0]
    validation_step = preflight.split(
        "      - name: Validate workflow-run commit and requested tag\n", 1
    )[1]
    script_block = validation_step.split("        run: |\n", 1)[1]
    script_lines = []
    for line in script_block.splitlines():
        if line.strip() and not line.startswith("          "):
            break
        script_lines.append(line[10:] if line.startswith("          ") else "")
    return "\n".join(script_lines).rstrip() + "\n"


def _manual_publisher_scripts(workflow_path: Path) -> tuple[str, str]:
    """Extract snapshot verification and publication scripts from a workflow."""
    workflow_text = workflow_path.read_text(encoding="utf-8")
    publisher = workflow_text.split("  publish-existing-release:\n", 1)[1]
    scripts: list[str] = []
    for step_name in (
        "Verify the preflight manifest and package hashes",
        "Publish existing artifacts to PyPI",
    ):
        step = publisher.split(f"      - name: {step_name}\n", 1)[1].split(
            "\n      - name: ", 1
        )[0]
        body = step.split("        run: |\n", 1)[1]
        lines = []
        for line in body.splitlines():
            if line.strip() and not line.startswith("          "):
                break
            lines.append(line[10:] if line.startswith("          ") else "")
        scripts.append("\n".join(lines).rstrip() + "\n")
    return scripts[0], scripts[1]


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

### 💥 Breaking changes

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


@pytest.mark.parametrize(
    ("helper", "breaking_heading"),
    [
        (
            Path("src/buildben_dev/packaging/release_notes.py"),
            "### 💥 Breaking changes",
        ),
        (
            Path(
                "src/buildben/_templates_proj/_src-dev-packaging-release_notes.py.tmpl"
            ),
            "### 💥 Breaking Change Summary",
        ),
    ],
)
def test_release_note_cli_build_only_allowance_keeps_release_validation(
    tmp_path: Path, helper: Path, breaking_heading: str
) -> None:
    """Build-only extraction tolerates unreleased entries, but not bad structure."""
    repository_root = Path(__file__).resolve().parents[1]
    changelog = sample_changelog(unreleased_entry="- Work still in progress.").replace(
        "### 💥 Breaking changes", breaking_heading
    )
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(changelog, encoding="utf-8")
    output_path = tmp_path / "release-notes.md"
    command = [
        sys.executable,
        str(repository_root / helper),
        "1.2.3",
        "--changelog",
        str(changelog_path),
        "--project-version",
        "1.2.3",
        "--output",
        str(output_path),
    ]

    build_only = subprocess.run(
        [*command, "--allow-unreleased-entries"],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    assert build_only.returncode == 0, build_only.stderr
    assert output_path.read_text(encoding="utf-8") == (
        "## ➕ Added\n\n- Add a tested release workflow.\n"
    )

    strict = subprocess.run(
        command, cwd=repository_root, capture_output=True, check=False, text=True
    )
    assert strict.returncode != 0
    assert "still contains release entries" in strict.stderr

    malformed = changelog.replace(breaking_heading, "### 💥 Missing category")
    changelog_path.write_text(malformed, encoding="utf-8")
    invalid_structure = subprocess.run(
        [*command, "--allow-unreleased-entries"],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    assert invalid_structure.returncode != 0
    assert "exactly once" in invalid_structure.stderr

    changelog_path.write_text(changelog, encoding="utf-8")
    mismatched_tag = subprocess.run(
        [
            *command,
            "--allow-unreleased-entries",
            "--tag",
            "branch-name",
        ],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    assert mismatched_tag.returncode != 0
    assert "does not match project version" in mismatched_tag.stderr

    tagged_build = subprocess.run(
        [
            *command,
            "--allow-unreleased-entries",
            "--tag",
            "v1.2.3",
        ],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    assert tagged_build.returncode != 0
    assert "still contains release entries" in tagged_build.stderr


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


def test_manual_pypi_preflight_scripts_match_root_and_scaffold() -> None:
    """Generated projects must run the same preflight as Buildben itself."""
    repository_root = Path(__file__).resolve().parents[1]
    root_script = _manual_pypi_preflight_script(
        repository_root / ".github/workflows/release.yml"
    )
    scaffold_script = _manual_pypi_preflight_script(
        repository_root / "src/buildben/_templates_proj/_github-release.yml"
    )

    assert root_script == scaffold_script
    assert '"${ACTIVE_WORKFLOW_SHA}^{commit}"' in root_script
    assert '"${ACTIVE_WORKFLOW_REF}^{commit}"' not in root_script


@pytest.mark.parametrize(
    (
        "workflow_policy",
        "target_policy",
        "release_draft",
        "move_tag",
        "expected_ready",
        "invalid_asset_name",
    ),
    [
        ("false", "true", False, False, False, False),
        ("true", "false", False, False, False, False),
        ("true", "true", False, False, True, False),
        ("true", "true", True, False, False, False),
        ("true", "true", "false", False, False, False),
        ("true", "true", False, True, False, False),
        ("true", "true", False, False, False, True),
    ],
)
def test_manual_pypi_preflight_uses_workflow_run_commit(
    tmp_path: Path,
    workflow_policy: str,
    target_policy: str,
    release_draft: bool | str,
    move_tag: bool,
    expected_ready: bool,
    invalid_asset_name: bool,
) -> None:
    """Use the immutable run SHA and capture assets only when both policies pass."""
    repository_root = Path(__file__).resolve().parents[1]
    script = _manual_pypi_preflight_script(
        repository_root / ".github/workflows/release.yml"
    )
    repository = tmp_path / "workflow-repository"
    repository.mkdir()
    git_env = os.environ.copy()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            env=git_env,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    def write_policy(value: str) -> None:
        (repository / "justfile").write_text(
            f'RELEASE_PYPI := "{value}"\n', encoding="utf-8"
        )

    git("init", "--initial-branch=main")
    git("config", "user.name", "Buildben Test")
    git("config", "user.email", "test@example.com")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    write_policy(workflow_policy)
    git("add", "justfile")
    git("commit", "-m", "Record workflow-run release policy")
    workflow_sha = git("rev-parse", "HEAD")

    git("switch", "-c", "release-target")
    write_policy(target_policy)
    git("add", "justfile")
    git("commit", "--allow-empty", "-m", "Record target tag release policy")
    git("tag", "-a", "v1.2.3", "-m", "Release v1.2.3")
    git("switch", "main")
    if workflow_policy == "false":
        git("switch", "main")
        write_policy("true")
        git("add", "justfile")
        git("commit", "-m", "Advance branch with release policy enabled")
        assert git("rev-parse", "main") != workflow_sha
        assert 'RELEASE_PYPI := "true"' in git("show", "main:justfile")
    elif target_policy == "false":
        git("branch", "v1.2.3", workflow_sha)

    target_commit_sha = git("rev-parse", "refs/tags/v1.2.3^{commit}")
    target_tag_sha = git("rev-parse", "refs/tags/v1.2.3")
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        cwd=tmp_path,
        env=git_env,
        check=True,
        text=True,
        capture_output=True,
    )
    git("remote", "add", "origin", str(remote))
    git("push", "origin", "refs/tags/v1.2.3")
    replacement_tag_sha = ""
    if move_tag:
        git("tag", "-a", "replacement", "-m", "Replacement tag")
        git("push", "origin", "refs/tags/replacement")
        replacement_tag_sha = git("rev-parse", "refs/tags/replacement")
    git("tag", "-d", "v1.2.3")
    git("checkout", "--detach", workflow_sha)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$MANUAL_GH_LOG"
case "$1:$2" in
  api:*)
    endpoint="$2"
    if [[ "$endpoint" == */releases/tags/* ]]; then
      cat "$MANUAL_RELEASE_JSON"
    elif [[ "$endpoint" == "/repos/buildben/example/releases/assets/101" ]]; then
      if [[ -n "$MOVE_TAG_OID" ]]; then git --git-dir "$REMOTE_GIT_DIR" update-ref refs/tags/v1.2.3 "$MOVE_TAG_OID"; fi
      cat "$MANUAL_WHEEL"
    elif [[ "$endpoint" == "/repos/buildben/example/releases/assets/102" ]]; then
      if [[ -n "$MOVE_TAG_OID" ]]; then git --git-dir "$REMOTE_GIT_DIR" update-ref refs/tags/v1.2.3 "$MOVE_TAG_OID"; fi
      cat "$MANUAL_SDIST"
    else
      exit 90
    fi
    ;;
  *) exit 91 ;;
esac
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    fake_uvx = fake_bin / "uvx"
    fake_uvx.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$MANUAL_UVX_LOG"
exit 0
""",
        encoding="utf-8",
    )
    fake_uvx.chmod(0o755)

    release_json = tmp_path / "release.json"
    import json

    release_json.write_text(
        json.dumps(
            {
                "id": 42,
                "tag_name": "v1.2.3",
                "draft": release_draft,
                "assets": [
                    {
                        "id": 101,
                        "name": (
                            "buildben-1.2.3-unsafe/../../escape.whl"
                            if invalid_asset_name
                            else "buildben-1.2.3-py3-none-any.whl"
                        ),
                    },
                    {"id": 102, "name": "buildben-1.2.3.tar.gz"},
                ],
            }
        ),
        encoding="utf-8",
    )
    wheel = tmp_path / "buildben-1.2.3-py3-none-any.whl"
    sdist = tmp_path / "buildben-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel snapshot")
    sdist.write_bytes(b"source snapshot")
    gh_log = tmp_path / "gh.log"
    uvx_log = tmp_path / "uvx.log"
    gh_log.write_text("", encoding="utf-8")

    output_file = tmp_path / "github-output"
    env = git_env.copy()
    env.update(
        {
            "ACTIVE_WORKFLOW_REF": "refs/heads/main",
            "ACTIVE_WORKFLOW_SHA": workflow_sha,
            "GITHUB_OUTPUT": str(output_file),
            "GITHUB_REPOSITORY": "buildben/example",
            "MANUAL_GH_LOG": str(gh_log),
            "MANUAL_RELEASE_JSON": str(release_json),
            "MANUAL_SDIST": str(sdist),
            "MANUAL_UVX_LOG": str(uvx_log),
            "MANUAL_WHEEL": str(wheel),
            "MOVE_TAG_OID": replacement_tag_sha,
            "PACKAGE_NAME": "buildben",
            "PATH": os.pathsep.join([str(fake_bin), git_env.get("PATH", "")]),
            "RELEASE_TAG": "v1.2.3",
            "REMOTE_GIT_DIR": str(remote),
        }
    )
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=repository,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    if workflow_policy != "true" or target_policy != "true":
        assert result.returncode == 0, result.stderr
        assert output_file.read_text(encoding="utf-8") == "snapshot_ready=false\n"
        assert gh_log.read_text(encoding="utf-8") == ""
        assert not (repository / "manual-pypi-snapshot").exists()
        return

    if release_draft is not False:
        assert result.returncode != 0
        assert "non-draft" in result.stderr
        assert len(gh_log.read_text(encoding="utf-8").splitlines()) == 1
        assert not (repository / "manual-pypi-snapshot").exists()
        return

    if move_tag:
        assert result.returncode != 0
        assert "changed during asset capture" in result.stderr
        assert len(gh_log.read_text(encoding="utf-8").splitlines()) == 3
        assert not output_file.exists()
        return

    if invalid_asset_name:
        assert result.returncode != 0
        assert "filenames do not match tag" in result.stderr
        assert len(gh_log.read_text(encoding="utf-8").splitlines()) == 1
        assert not (repository / "manual-pypi-snapshot").exists()
        return

    assert expected_ready

    assert result.returncode == 0, result.stderr
    outputs = output_file.read_text(encoding="utf-8")
    assert "snapshot_ready=true\n" in outputs
    assert "release_id=42\n" in outputs
    assert "release_tag=v1.2.3\n" in outputs
    assert f"active_commit_sha={workflow_sha}\n" in outputs
    assert f"tag_object_sha={target_tag_sha}\n" in outputs
    assert f"target_commit_sha={target_commit_sha}\n" in outputs
    calls = gh_log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 3
    assert calls[0].startswith("api /repos/buildben/example/releases/tags/v1.2.3")
    assert calls[1] == (
        "api /repos/buildben/example/releases/assets/101 --header "
        "Accept: application/octet-stream"
    )
    assert calls[2] == (
        "api /repos/buildben/example/releases/assets/102 --header "
        "Accept: application/octet-stream"
    )
    assert all("/releases/42/assets/" not in call for call in calls)
    assert "twine check manual-pypi-snapshot/" in uvx_log.read_text(encoding="utf-8")

    import hashlib
    import json

    snapshot = repository / "manual-pypi-snapshot"
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_id"] == 42
    assert manifest["release_tag"] == "v1.2.3"
    assert manifest["workflow_run_commit_sha"] == workflow_sha
    assert manifest["tag_object_sha"] == target_tag_sha
    assert manifest["tag_commit_sha"] == target_commit_sha
    assert manifest["repository"] == "buildben/example"
    assert manifest["packages"] == [
        {
            "filename": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
        {
            "filename": sdist.name,
            "sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        },
    ]


def _write_manual_snapshot(snapshot: Path) -> tuple[str, str, str]:
    """Write a valid snapshot and return its package names and manifest hash."""
    import hashlib
    import json

    snapshot.mkdir()
    wheel_name = "buildben-1.2.3-py3-none-any.whl"
    sdist_name = "buildben-1.2.3.tar.gz"
    (snapshot / wheel_name).write_bytes(b"captured wheel")
    (snapshot / sdist_name).write_bytes(b"captured source archive")
    manifest = {
        "schema_version": 1,
        "repository": "buildben/example",
        "release_id": 42,
        "release_tag": "v1.2.3",
        "workflow_run_commit_sha": "a" * 40,
        "tag_object_sha": "b" * 40,
        "tag_commit_sha": "c" * 40,
        "packages": [
            {
                "filename": filename,
                "sha256": hashlib.sha256(
                    (snapshot / filename).read_bytes()
                ).hexdigest(),
            }
            for filename in (wheel_name, sdist_name)
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n"
    (snapshot / "manifest.json").write_bytes(manifest_bytes)
    return wheel_name, sdist_name, hashlib.sha256(manifest_bytes).hexdigest()


def _manual_publisher_env(snapshot: Path, manifest_sha256: str) -> dict[str, str]:
    """Return downstream publisher identity values for a valid snapshot."""
    return {
        "EXPECTED_REPOSITORY": "buildben/example",
        "EXPECTED_RELEASE_ID": "42",
        "EXPECTED_RELEASE_TAG": "v1.2.3",
        "EXPECTED_ACTIVE_COMMIT_SHA": "a" * 40,
        "EXPECTED_TAG_OBJECT_SHA": "b" * 40,
        "EXPECTED_TARGET_COMMIT_SHA": "c" * 40,
        "EXPECTED_MANIFEST_SHA256": manifest_sha256,
        "EXPECTED_WHEEL_NAME": "buildben-1.2.3-py3-none-any.whl",
        "EXPECTED_SDIST_NAME": "buildben-1.2.3.tar.gz",
        "WHEEL_NAME": "buildben-1.2.3-py3-none-any.whl",
        "SDIST_NAME": "buildben-1.2.3.tar.gz",
    }


def test_manual_publisher_uses_only_preflight_artifact_snapshot(tmp_path: Path) -> None:
    """Publish captured files without resolving tags or release assets again."""
    repository_root = Path(__file__).resolve().parents[1]
    verify_script, publish_script = _manual_publisher_scripts(
        repository_root / ".github/workflows/release.yml"
    )
    snapshot = tmp_path / "manual-pypi-snapshot"
    wheel_name, sdist_name, manifest_sha256 = _write_manual_snapshot(snapshot)
    # A moved tag may now identify different release assets; downstream publication
    # still has access only to the already captured artifact directory.
    replacement_assets = tmp_path / "replacement-release-assets"
    replacement_assets.mkdir()
    (replacement_assets / wheel_name).write_bytes(b"replacement wheel")
    (replacement_assets / sdist_name).write_bytes(b"replacement source archive")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    uv_log = tmp_path / "uv.log"
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "$PUBLISH_UV_LOG"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    for executable in ("gh", "git"):
        forbidden = fake_bin / executable
        forbidden.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
        forbidden.chmod(0o755)

    env = os.environ.copy()
    env.update(_manual_publisher_env(snapshot, manifest_sha256))
    env.update(
        {
            "PATH": os.pathsep.join((str(fake_bin), env.get("PATH", ""))),
            "PUBLISH_UV_LOG": str(uv_log),
        }
    )
    verified = subprocess.run(
        ["bash", "-e", "-c", verify_script],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert verified.returncode == 0, verified.stderr
    published = subprocess.run(
        ["bash", "-e", "-c", publish_script],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert published.returncode == 0, published.stderr
    assert uv_log.read_text(encoding="utf-8").splitlines() == [
        (
            "publish --trusted-publishing always --check-url https://pypi.org/simple/buildben/ "
            f"manual-pypi-snapshot/{wheel_name} manual-pypi-snapshot/{sdist_name}"
        )
    ]
    assert "gh " not in verify_script + publish_script
    assert "git " not in verify_script + publish_script


@pytest.mark.parametrize(
    "damage", ["missing_snapshot", "altered_hash", "unexpected_file"]
)
def test_manual_publisher_rejects_invalid_preflight_artifact(
    tmp_path: Path,
    damage: str,
) -> None:
    """A missing, altered, or unexpected artifact never reaches the publisher."""
    repository_root = Path(__file__).resolve().parents[1]
    verify_script, publish_script = _manual_publisher_scripts(
        repository_root / ".github/workflows/release.yml"
    )
    snapshot = tmp_path / "manual-pypi-snapshot"
    wheel_name, _sdist_name, manifest_sha256 = _write_manual_snapshot(snapshot)
    if damage == "missing_snapshot":
        (snapshot / "manifest.json").unlink()
    elif damage == "altered_hash":
        (snapshot / wheel_name).write_bytes(b"tampered wheel")
    else:
        (snapshot / "replacement.whl").write_bytes(b"unexpected")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    uv_log = tmp_path / "uv.log"
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "$PUBLISH_UV_LOG"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    env = os.environ.copy()
    env.update(_manual_publisher_env(snapshot, manifest_sha256))
    env.update(
        {
            "PATH": os.pathsep.join((str(fake_bin), env.get("PATH", ""))),
            "PUBLISH_UV_LOG": str(uv_log),
        }
    )

    verified = subprocess.run(
        ["bash", "-e", "-c", verify_script],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert verified.returncode != 0
    assert not uv_log.exists()
    assert "gh " not in verify_script + publish_script
    assert "git " not in verify_script + publish_script


def test_root_publish_policy_uses_exact_tag_ref_before_github(
    tmp_path: Path,
) -> None:
    """Reject shadow branches and absent tag refs before invoking GitHub."""
    repository_root = Path(__file__).resolve().parents[1]
    repository = tmp_path / "root-repository"
    repository.mkdir()
    git_env = os.environ.copy()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            env=git_env,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    (repository / "justfile").write_text(
        (repository_root / "justfile").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    git("init", "--initial-branch=main")
    git("config", "user.name", "Buildben Test")
    git("config", "user.email", "test@example.com")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    git("add", "justfile")
    git("commit", "-m", "Record disabled release policy")
    git("tag", "-a", "v1.2.3", "-m", "Release v1.2.3")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$ROOT_PUBLISH_GH_LOG"\n'
        'case "$1:$2" in\n'
        "  auth:status) exit 0 ;;\n"
        "  release:view)\n"
        '    if [[ "$*" == *"--json isDraft"* ]]; then printf \'false\\n\'; '
        'elif [[ "$*" == *".whl"* || "$*" == *".tar.gz"* ]]; then '
        "printf '1\\n'; else exit 90; fi ;;\n"
        "  workflow:run) exit 0 ;;\n"
        "  *) exit 91 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    gh_log = tmp_path / "root-gh.log"
    gh_log.write_text("", encoding="utf-8")
    env = git_env.copy()
    env.update(
        {
            "PATH": os.pathsep.join((str(fake_bin), env.get("PATH", ""))),
            "ROOT_PUBLISH_GH_LOG": str(gh_log),
        }
    )

    def publish() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["just", "publish-pypi", "v1.2.3"],
            cwd=repository,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )

    current_disabled = publish()
    assert current_disabled.returncode != 0
    assert "current committed justfile" in current_disabled.stderr
    assert gh_log.read_text(encoding="utf-8") == ""

    justfile = repository / "justfile"
    justfile.write_text(
        justfile.read_text(encoding="utf-8").replace(
            'RELEASE_PYPI := "false"', 'RELEASE_PYPI := "true"', 1
        ),
        encoding="utf-8",
    )
    git("add", "justfile")
    git("commit", "-m", "Enable current release policy")
    git("branch", "v1.2.3", "HEAD")

    false_tag_shadowed_by_true_branch = publish()
    assert false_tag_shadowed_by_true_branch.returncode != 0
    assert "tag v1.2.3's committed justfile" in false_tag_shadowed_by_true_branch.stderr
    assert gh_log.read_text(encoding="utf-8") == ""

    git("tag", "-d", "v1.2.3")
    missing_exact_tag_with_branch = publish()
    assert missing_exact_tag_with_branch.returncode != 0
    assert "Could not resolve exact release tag ref refs/tags/v1.2.3" in (
        missing_exact_tag_with_branch.stderr
    )
    assert gh_log.read_text(encoding="utf-8") == ""

    git("tag", "-a", "v1.2.3", "-m", "Release v1.2.3")
    enabled = publish()
    assert enabled.returncode == 0, enabled.stderr
    assert gh_log.read_text(encoding="utf-8").splitlines() == [
        "auth status",
        "release view v1.2.3 --json isDraft --jq .isDraft",
        'release view v1.2.3 --json assets --jq [.assets[].name | select(endswith(".whl"))] | length',
        'release view v1.2.3 --json assets --jq [.assets[].name | select(endswith(".tar.gz"))] | length',
        "workflow run release.yml --raw-field release_tag=v1.2.3",
    ]


def test_release_notes_validate_release_order_and_cli_arguments(tmp_path: Path) -> None:
    """The release helper should reject stale versions and partial tag checks."""
    assert release_notes.latest_release_version(sample_changelog()) == "1.2.3"
    release_notes.validate_next_version("1.2.3", "1.2.4")
    with pytest.raises(ValueError, match="must be newer"):
        release_notes.validate_next_version("1.2.3", "1.2.3")
    with pytest.raises(ValueError, match="--tag requires --project-version"):
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


@pytest.mark.parametrize(
    ("current_policy", "tag_policy", "publish_allowed"),
    [
        ("false", "false", False),
        ("false", "true", False),
        ("true", "false", False),
        ("true", "true", True),
    ],
)
def test_publish_pypi_uses_committed_policy_before_github(
    tmp_path: Path,
    current_policy: str,
    tag_policy: str,
    publish_allowed: bool,
) -> None:
    """Require committed true policy in both refs before calling GitHub."""
    source_justfile = Path(__file__).resolve().parents[1] / "justfile"
    source_text = source_justfile.read_text(encoding="utf-8")
    assert source_text.count('RELEASE_PYPI := "false"') == 1

    repo = tmp_path / "policy-repository"
    repo.mkdir()
    (repo / "justfile").write_text(
        source_text.replace(
            'RELEASE_PYPI := "false"',
            f'RELEASE_PYPI := "{current_policy}"',
            1,
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()

    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

    git("init", "--initial-branch=main")
    git("config", "user.name", "Buildben Test")
    git("config", "user.email", "test@example.com")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    git("add", "justfile")
    git("commit", "-m", "Set current release policy")

    if tag_policy != current_policy:
        git("switch", "-c", "tag-policy")
        justfile = repo / "justfile"
        justfile.write_text(
            justfile.read_text(encoding="utf-8").replace(
                f'RELEASE_PYPI := "{current_policy}"',
                f'RELEASE_PYPI := "{tag_policy}"',
                1,
            ),
            encoding="utf-8",
        )
        git("add", "justfile")
        git("commit", "-m", "Set target tag release policy")
        git("tag", "-a", "v1.2.3", "-m", "Release v1.2.3")
        git("switch", "main")
    else:
        git("tag", "-a", "v1.2.3", "-m", "Release v1.2.3")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$RELEASE_POLICY_GH_LOG"\n'
        'case "$1:$2" in\n'
        "  auth:status) exit 0 ;;\n"
        "  release:view)\n"
        '    if [[ "$*" == *"--json isDraft"* ]]; then printf \'false\\n\'; '
        'elif [[ "$*" == *"--json assets"* ]]; then printf \'1\\n\'; '
        "else exit 90; fi ;;\n"
        "  workflow:run) exit 0 ;;\n"
        "  *) exit 91 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    gh_log = tmp_path / "gh.log"
    env["PATH"] = os.pathsep.join([str(fake_bin), env.get("PATH", "")])
    env["RELEASE_POLICY_GH_LOG"] = str(gh_log)

    command = ["just"]
    if not publish_allowed:
        command.extend(["--set", "RELEASE_PYPI", "true"])
    command.extend(["publish-pypi", "v1.2.3"])
    result = subprocess.run(
        command,
        cwd=repo,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    if not publish_allowed:
        assert result.returncode != 0
        expected_ref = (
            "current committed justfile"
            if current_policy == "false"
            else "tag v1.2.3's committed justfile"
        )
        assert expected_ref in result.stderr
        assert not gh_log.exists()
        return

    assert result.returncode == 0, result.stderr
    assert gh_log.is_file()
    assert "auth status" in gh_log.read_text(encoding="utf-8")
    assert "workflow run release.yml --raw-field release_tag=v1.2.3" in (
        gh_log.read_text(encoding="utf-8")
    )
