"""Stage and publish validated Buildben release assets through GitHub."""
# > Run this CLI from the checked project root so prepare reads its pyproject.toml.

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from .release_notes import validate_tag_version

SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
RELEASES_PER_PAGE = 100


class ReleaseError(RuntimeError):
    """Raised when release identity, payload, or remote state is invalid."""


class _ReleaseNotFound(ReleaseError):
    """Raised when a successful release listing contains no matching tag."""


class Api(Protocol):
    """Minimal GitHub API boundary used by the publisher and stateful tests."""

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        data: bytes | None = None,
        headers: tuple[str, ...] = (),
    ) -> bytes: ...
    def watch_ci(self, repository: str, run_id: int) -> int: ...


@dataclass(frozen=True, slots=True)
class Identity:
    """Immutable tag identity required by every mutating operation."""

    repository: str
    tag: str
    commit: str


class GitHubApi:
    """Run authenticated GitHub requests through the user's ``gh`` client."""

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        data: bytes | None = None,
        headers: tuple[str, ...] = (),
    ) -> bytes:
        command = ["gh", "api", "--method", method.upper()]
        for header in headers:
            command.extend(("--header", header))
        if data is not None:
            command.extend(("--input", "-"))
        command.append(endpoint)
        result = subprocess.run(
            command,
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise ReleaseError(f"GitHub API request failed: {detail}")
        return result.stdout

    def watch_ci(self, repository: str, run_id: int) -> int:
        result = subprocess.run(
            ["gh", "run", "watch", str(run_id), "--exit-status", "--repo", repository],
            check=False,
        )
        return result.returncode


def _json(
    api: Api, method: str, endpoint: str, payload: object | None = None
) -> object:
    body = (
        None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    )
    raw = api.request(method, endpoint, data=body)
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"GitHub returned invalid JSON for {endpoint}") from exc


def _repository(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ReleaseError("Repository must be OWNER/REPO.")
    return value


def _tag(value: str) -> str:
    if not re.fullmatch(
        r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value
    ):
        raise ReleaseError("Tag must be vMAJOR.MINOR.PATCH.")
    return value


def _sha(value: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise ReleaseError("Commit must be a full immutable Git commit SHA.")
    return value


def _endpoint(repository: str, suffix: str) -> str:
    return f"/repos/{_repository(repository)}/{suffix.lstrip('/')}"


def _tag_commit(api: Api, identity: Identity) -> str:
    """Resolve the exact remote tag ref and peel annotated tags to a commit."""
    ref = _json(
        api, "GET", _endpoint(identity.repository, f"git/ref/tags/{identity.tag}")
    )
    if not isinstance(ref, dict) or not isinstance(ref.get("object"), dict):
        raise ReleaseError(f"Remote tag {identity.tag} has no Git object.")
    obj = ref["object"]
    object_type, object_sha = obj.get("type"), obj.get("sha")
    if not isinstance(object_sha, str) or not SHA_RE.fullmatch(object_sha):
        raise ReleaseError(f"Remote tag {identity.tag} has an invalid object SHA.")
    if object_type == "tag":
        annotated = _json(
            api, "GET", _endpoint(identity.repository, f"git/tags/{object_sha}")
        )
        if not isinstance(annotated, dict) or not isinstance(
            annotated.get("object"), dict
        ):
            raise ReleaseError(f"Annotated tag {identity.tag} cannot be peeled.")
        peeled = annotated["object"]
        if peeled.get("type") != "commit":
            raise ReleaseError(
                f"Remote tag {identity.tag} does not peel directly to a commit."
            )
        commit = peeled.get("sha")
    elif object_type == "commit":
        commit = object_sha
    else:
        raise ReleaseError(f"Remote tag {identity.tag} does not identify a commit.")
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit):
        raise ReleaseError(
            f"Remote tag {identity.tag} has an invalid peeled commit SHA."
        )
    if commit != identity.commit:
        raise ReleaseError(
            f"Remote tag {identity.tag} points to {commit}, not {identity.commit}."
        )
    return commit


def _release(api: Api, identity: Identity) -> dict[str, object]:
    page = 1
    seen_ids: set[int] = set()
    match: dict[str, object] | None = None
    while True:
        endpoint = _endpoint(
            identity.repository,
            f"releases?per_page={RELEASES_PER_PAGE}&page={page}",
        )
        result = _json(api, "GET", endpoint)
        if not isinstance(result, list) or len(result) > RELEASES_PER_PAGE:
            raise ReleaseError("GitHub release listing page is malformed.")
        for item in result:
            if not isinstance(item, dict):
                raise ReleaseError(
                    "GitHub release listing contains a malformed release."
                )
            tag_name = item.get("tag_name")
            if not isinstance(tag_name, str):
                raise ReleaseError(
                    "GitHub release listing contains a malformed release."
                )
            release_id = item.get("id")
            if (
                not isinstance(release_id, int)
                or isinstance(release_id, bool)
                or release_id <= 0
            ):
                raise ReleaseError(
                    "GitHub release listing contains an invalid identifier."
                )
            if release_id in seen_ids:
                raise ReleaseError("GitHub release listing repeats an identifier.")
            seen_ids.add(release_id)
            if tag_name == identity.tag:
                if match is not None:
                    raise ReleaseError(
                        f"GitHub release listing ambiguously identifies tag "
                        f"{identity.tag}."
                    )
                match = item
        if len(result) < RELEASES_PER_PAGE:
            break
        page += 1
    if match is None:
        raise _ReleaseNotFound(f"No GitHub release exists for tag {identity.tag}.")
    if match.get("tag_name") != identity.tag:
        raise ReleaseError(
            f"GitHub release does not identify exact tag {identity.tag}."
        )
    if match.get("draft") is not True:
        raise ReleaseError(
            f"Release {identity.tag} is published; refusing to mutate it."
        )
    if match.get("target_commitish") != identity.commit:
        raise ReleaseError(f"Draft {identity.tag} has an inconsistent target commit.")
    if match.get("prerelease") is not False:
        raise ReleaseError(f"Draft {identity.tag} is marked as a prerelease.")
    return match


def _release_id(release: dict[str, object]) -> int:
    value = release.get("id")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReleaseError("Draft release has an invalid identifier.")
    return value


def _assets(release: dict[str, object]) -> dict[str, dict[str, object]]:
    value = release.get("assets")
    if not isinstance(value, list):
        raise ReleaseError("Draft release has a malformed asset list.")
    result: dict[str, dict[str, object]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ReleaseError("Draft release contains a malformed asset.")
        name = item["name"]
        if name in result:
            raise ReleaseError(f"Draft contains duplicate asset {name}.")
        result[name] = item
    return result


def _normalize(value: str) -> str:
    return re.sub(r"[-_.]+", "_", value).lower()


def _project() -> tuple[str, str]:
    try:
        with Path("pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)["project"]
        name, version = project["name"], project["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError(
            "Cannot read project name and version from pyproject.toml."
        ) from exc
    if not isinstance(name, str) or not isinstance(version, str):
        raise ReleaseError("Project name and version must be strings.")
    return name, version


def _safe_member(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or re.match(r"^[A-Za-z]:", value)
    ):
        raise ReleaseError(f"Unsafe archive member: {value!r}.")
    return path


def _basename(value: str, label: str) -> str:
    if (
        not value
        or value in (".", "..")
        or Path(value).name != value
        or "/" in value
        or "\\" in value
    ):
        raise ReleaseError(f"{label} must be a safe basename.")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata_matches(data: bytes, name: str, version: str, filename: str) -> None:
    from email.parser import BytesParser

    metadata = BytesParser().parsebytes(data)
    if (
        _normalize(metadata.get("Name", "")) != _normalize(name)
        or metadata.get("Version") != version
    ):
        raise ReleaseError(
            f"Package metadata in {filename} does not match {name} {version}."
        )


def _validate_package(path: Path, name: str, version: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ReleaseError(
            f"Release asset {path.name} is missing or not a regular file."
        )
    data = path.read_bytes()
    if path.name.endswith(".whl"):
        try:
            with zipfile.ZipFile(path) as archive:
                names = set()
                for item in archive.infolist():
                    _safe_member(item.filename.rstrip("/"))
                    mode = item.external_attr >> 16
                    if mode & 0o170000 == 0o120000:
                        raise ReleaseError(
                            f"Wheel {path.name} contains a symbolic link."
                        )
                    if item.filename in names:
                        raise ReleaseError(f"Wheel {path.name} has duplicate members.")
                    names.add(item.filename)
                metadata_names = [
                    item for item in names if item.endswith(".dist-info/METADATA")
                ]
                if len(metadata_names) != 1:
                    raise ReleaseError(
                        f"Wheel {path.name} must contain one METADATA file."
                    )
                _metadata_matches(
                    archive.read(metadata_names[0]), name, version, path.name
                )
        except (OSError, zipfile.BadZipFile) as exc:
            raise ReleaseError(f"Invalid wheel {path.name}.") from exc
        normalized = _normalize(path.name[:-4])
        if not normalized.startswith(f"{_normalize(name)}_{_normalize(version)}_"):
            raise ReleaseError(
                f"Wheel filename {path.name} does not match project/version."
            )
    else:
        import io
        import tarfile

        stem = path.name.removesuffix(".tar.gz")
        if not stem.endswith("-" + version) or _normalize(
            stem[: -(len(version) + 1)]
        ) != _normalize(name):
            raise ReleaseError(
                f"Source archive filename {path.name} does not match project/version."
            )
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
                roots: set[str] = set()
                metadata = []
                for member in archive.getmembers():
                    safe = _safe_member(member.name)
                    roots.add(safe.parts[0])
                    if (
                        member.issym()
                        or member.islnk()
                        or not (member.isfile() or member.isdir())
                    ):
                        raise ReleaseError(
                            f"Source archive {path.name} contains a link or special file."
                        )
                    if len(safe.parts) == 2 and safe.parts[1] == "PKG-INFO":
                        stream = archive.extractfile(member)
                        if stream is None:
                            raise ReleaseError(
                                f"Cannot read PKG-INFO from {path.name}."
                            )
                        metadata.append(stream.read())
                if len(roots) != 1 or len(metadata) != 1:
                    raise ReleaseError(
                        f"Source archive {path.name} must have one root and one PKG-INFO."
                    )
                _metadata_matches(metadata[0], name, version, path.name)
        except (OSError, tarfile.TarError) as exc:
            raise ReleaseError(f"Invalid source archive {path.name}.") from exc
    return data


def _validate_local_files(
    directory: Path, names: list[str], identity: Identity
) -> dict[str, bytes]:
    if len(names) != 2 or len(names) != len(set(names)):
        raise ReleaseError("Upload exactly one wheel and one source archive.")
    for filename in names:
        _basename(filename, "Upload filename")
    name, version = _project()
    if identity.tag != f"v{version}":
        raise ReleaseError("Project version does not match the release tag.")
    normalized = _normalize(name)
    wheels = [item for item in names if item.endswith(".whl")]
    sdists = [item for item in names if item.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseError("Upload exactly one wheel and one source archive.")
    if _normalize(sdists[0][:-7].removesuffix("-" + version)) != normalized:
        raise ReleaseError("Source archive filename does not match project/version.")
    return {item: _validate_package(directory / item, name, version) for item in names}


def _asset_bytes(api: Api, identity: Identity, asset: dict[str, object]) -> bytes:
    asset_id = asset.get("id")
    if not isinstance(asset_id, int) or isinstance(asset_id, bool):
        raise ReleaseError("GitHub asset has an invalid identifier.")
    return api.request(
        "GET",
        _endpoint(identity.repository, f"releases/assets/{asset_id}"),
        headers=("Accept: application/octet-stream",),
    )


def _delete_asset(api: Api, identity: Identity, asset_id: int) -> None:
    _tag_commit(api, identity)
    api.request("DELETE", _endpoint(identity.repository, f"releases/assets/{asset_id}"))


def _upload(
    api: Api, identity: Identity, release_id: int, name: str, data: bytes
) -> None:
    _tag_commit(api, identity)
    encoded = __import__("urllib.parse", fromlist=["quote"]).quote(name, safe="")
    api.request(
        "POST",
        f"https://uploads.github.com/repos/{identity.repository}/releases/{release_id}/assets?name={encoded}",
        data=data,
        headers=(
            "Content-Type: application/octet-stream",
            f"Content-Length: {len(data)}",
        ),
    )


def _sync_asset(
    api: Api, identity: Identity, release: dict[str, object], name: str, data: bytes
) -> None:
    assets = _assets(release)
    existing = assets.get(name)
    if existing is not None:
        digest = existing.get("digest")
        if (
            isinstance(digest, str)
            and digest.startswith("sha256:")
            and digest[7:] == _sha256(data)
        ):
            return
        remote = _asset_bytes(api, identity, existing)
        if remote == data:
            return
        _delete_asset(api, identity, _asset_id(existing))
    _upload(api, identity, _release_id(release), name, data)
    updated = _release(api, identity)
    uploaded = _assets(updated).get(name)
    if uploaded is None:
        raise ReleaseError(f"GitHub did not retain uploaded asset {name}.")
    digest = uploaded.get("digest")
    expected_digest = _sha256(data)
    if isinstance(digest, str) and digest.startswith("sha256:"):
        if digest[7:] != expected_digest:
            raise ReleaseError(
                f"GitHub stored an incorrect digest for uploaded asset {name}."
            )
    elif _asset_bytes(api, identity, uploaded) != data:
        raise ReleaseError(f"GitHub stored different bytes for uploaded asset {name}.")


def _asset_id(asset: dict[str, object]) -> int:
    value = asset.get("id")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReleaseError("GitHub asset has an invalid identifier.")
    return value


def prepare(
    api: Api, repository: str, tag: str, commit: str, notes: Path
) -> dict[str, object]:
    """Validate checked metadata and create or reuse only its draft release."""
    identity = Identity(_repository(repository), _tag(tag), _sha(commit))
    if not notes.is_file() or notes.is_symlink():
        raise ReleaseError("Release notes must be a regular file.")
    distribution, current_version = _project()
    version = identity.tag[1:]
    validate_tag_version(identity.tag, current_version)
    _tag_commit(api, identity)
    try:
        release = _release(api, identity)
    except _ReleaseNotFound:
        _tag_commit(api, identity)
        release = _json(
            api,
            "POST",
            _endpoint(identity.repository, "releases"),
            {
                "tag_name": identity.tag,
                "target_commitish": identity.commit,
                "name": f"{distribution} {version}",
                "body": notes.read_text(encoding="utf-8"),
                "draft": True,
                "prerelease": False,
            },
        )
        if not isinstance(release, dict):
            raise ReleaseError("GitHub did not return the created draft release.")
    if release.get("draft") is not True or release.get("tag_name") != identity.tag:
        raise ReleaseError("Prepared release is not the requested tag's draft.")
    if release.get("target_commitish") != identity.commit:
        raise ReleaseError("Draft release has an inconsistent target commit.")
    return release


def upload(
    api: Api, repository: str, tag: str, commit: str, directory: Path, names: list[str]
) -> None:
    identity = Identity(_repository(repository), _tag(tag), _sha(commit))
    _tag_commit(api, identity)
    files = _validate_local_files(directory, names, identity)
    release = _release(api, identity)
    existing = _assets(release)
    if set(existing) - set(files):
        raise ReleaseError(
            "Draft contains unexpected assets; refusing to replace or delete them."
        )
    for name, data in files.items():
        _sync_asset(api, identity, release, name, data)
        release = _release(api, identity)


def finalize(api: Api, repository: str, tag: str, commit: str) -> None:
    """Validate exactly one wheel and sdist, then publish the checked draft."""
    identity = Identity(_repository(repository), _tag(tag), _sha(commit))
    _tag_commit(api, identity)
    release = _release(api, identity)
    assets = _assets(release)
    names = set(assets)
    if (
        len(names) != 2
        or sum(name.endswith(".whl") for name in names) != 1
        or sum(name.endswith(".tar.gz") for name in names) != 1
    ):
        raise ReleaseError(
            "Draft must contain exactly one wheel and one source archive."
        )
    with tempfile.TemporaryDirectory(prefix="buildben-release-finalize-") as temp:
        directory = Path(temp)
        for name, asset in assets.items():
            _basename(name, "GitHub asset name")
            (directory / name).write_bytes(_asset_bytes(api, identity, asset))
        files = _validate_local_files(directory, sorted(names), identity)
        if set(files) != names:
            raise ReleaseError("Draft asset set changed during finalization.")
    _tag_commit(api, identity)
    api.request(
        "PATCH",
        _endpoint(identity.repository, f"releases/{_release_id(release)}"),
        data=json.dumps(
            {"draft": False, "prerelease": False}, separators=(",", ":")
        ).encode(),
    )


def wait_ci(
    api: Api,
    repository: str,
    tag: str,
    commit: str,
    *,
    timeout: float = 120.0,
    interval: float = 5.0,
    clock=time.monotonic,
    sleep=time.sleep,
) -> int:
    """Wait for the exact successful main-push or tag-dispatch CI run."""
    identity = Identity(_repository(repository), _tag(tag), _sha(commit))
    deadline = clock() + timeout
    run_id: int | None = None
    while clock() < deadline:
        endpoint = _endpoint(
            identity.repository,
            f"actions/workflows/ci.yml/runs?head_sha={identity.commit}&per_page=100",
        )
        data = _json(api, "GET", endpoint)
        if not isinstance(data, dict) or not isinstance(
            data.get("workflow_runs"), list
        ):
            raise ReleaseError("GitHub returned malformed CI workflow runs.")
        candidates: list[dict[str, object]] = []
        for run in data["workflow_runs"]:
            run_repository = run.get("repository") if isinstance(run, dict) else None
            head_repository = (
                run.get("head_repository") if isinstance(run, dict) else None
            )
            if (
                not isinstance(run, dict)
                or run.get("head_sha") != identity.commit
                or run.get("path") != ".github/workflows/ci.yml"
            ):
                continue
            if (
                not isinstance(run_repository, dict)
                or run_repository.get("full_name") != identity.repository
                or not isinstance(head_repository, dict)
                or head_repository.get("full_name") != identity.repository
            ):
                continue
            allowed_push = (
                run.get("event") == "push" and run.get("head_branch") == "main"
            )
            allowed_dispatch = (
                run.get("event") == "workflow_dispatch"
                and run.get("head_branch") == identity.tag
            )
            if allowed_push or allowed_dispatch:
                candidates.append(run)
        if candidates:
            candidates.sort(
                key=lambda run: (
                    str(run.get("created_at", "")),
                    run.get("run_number", 0)
                    if isinstance(run.get("run_number"), int)
                    else 0,
                ),
                reverse=True,
            )
            value = candidates[0].get("id")
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                run_id = value
                break
        sleep(min(interval, max(0.0, deadline - clock())))
    if run_id is None:
        raise ReleaseError(
            f"No matching ci.yml run for {identity.commit} was found within "
            f"{timeout:g}s. Dispatch ci.yml for immutable tag {identity.tag}, "
            "then rerun the release gate."
        )
    status = api.watch_ci(identity.repository, run_id)
    if status:
        raise ReleaseError(
            f"Matching CI run {run_id} failed, was cancelled, or timed out "
            f"(gh run watch exit {status})."
        )
    return run_id


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and publish validated GitHub release assets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--repository", required=True)
    prepare_parser.add_argument("--tag", required=True)
    prepare_parser.add_argument("--commit", required=True)
    prepare_parser.add_argument("--notes", type=Path, required=True)
    item = subparsers.add_parser("upload")
    item.add_argument("--repository", required=True)
    item.add_argument("--tag", required=True)
    item.add_argument("--commit", required=True)
    item.add_argument("--directory", type=Path, required=True)
    item.add_argument("--files", nargs="+", required=True)
    for verb in ("finalize", "wait-ci"):
        item = subparsers.add_parser(verb)
        item.add_argument("--repository", required=True)
        item.add_argument("--tag", required=True)
        item.add_argument("--commit", required=True)
    return parser


def main(argv: list[str] | None = None, *, api: Api | None = None) -> int:
    args = _parser().parse_args(argv)
    client = api or GitHubApi()
    try:
        if args.command == "prepare":
            release = prepare(
                client, args.repository, args.tag, args.commit, args.notes
            )
            print(f"Prepared draft release {args.tag} (id {_release_id(release)}).")
        elif args.command == "upload":
            upload(
                client,
                args.repository,
                args.tag,
                args.commit,
                args.directory,
                args.files,
            )
        elif args.command == "finalize":
            finalize(client, args.repository, args.tag, args.commit)
        else:
            run_id = wait_ci(client, args.repository, args.tag, args.commit)
            print(f"Required CI run {run_id} passed.")
    except (ReleaseError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"release-assets: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
