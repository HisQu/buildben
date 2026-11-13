"""Small maintained helpers for generated native-release consumer proofs."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path


def sdk_authoring_environment(root: Path) -> tuple[dict[str, str], str, str]:
    """Select the generated project's SDK pin, optionally from a local repository.

    :param root: Generated project whose declared SDK references are authoritative.
    :return: Authoring environment, full immutable revision, and SDK version.
    """
    settings = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = settings["project"]
    declarations = [
        *project.get("dependencies", []),
        *(
            dependency
            for group in project.get("optional-dependencies", {}).values()
            for dependency in group
        ),
        *(
            dependency
            for group in settings.get("dependency-groups", {}).values()
            for dependency in group
            if isinstance(dependency, str)
        ),
    ]
    references = {
        match.groups()
        for declaration in declarations
        if isinstance(declaration, str)
        for match in re.finditer(
            r"git\+(https://github\.com/HisQu/apprc(?:\.git)?)@([^#;\s]+)",
            declaration,
        )
    }
    assert references, "Generated project declares no AppRC Git references."
    revisions = {revision for _, revision in references}
    override = os.environ.get("APPRC_TEST_SDK_REVISION")
    if override is None:
        assert len(revisions) == 1, "Generated SDK references must share one full ref."
        revision = next(iter(revisions))
    else:
        revision = override
    assert re.fullmatch(r"[0-9a-f]{40}", revision), "Supply a full SDK commit hash."
    environment = os.environ.copy()
    source = environment.get("APPRC_TEST_SDK_SOURCE")
    if source is None:
        return environment, revision, importlib.metadata.version("apprc-core")

    repository = Path(source).resolve()
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", f"{revision}^{{commit}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == revision
    metadata = subprocess.run(
        ["git", "-C", str(repository), "show", f"{revision}:pyproject.toml"],
        capture_output=True,
        text=True,
        check=True,
    )
    version = tomllib.loads(metadata.stdout)["project"]["version"]
    object_store = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    count = int(environment.get("GIT_CONFIG_COUNT", "0"))
    # > Lock exports may omit the repository URL's optional .git suffix.
    canonical_urls = {
        url.removesuffix(".git") + suffix
        for url, _ in references
        for suffix in ("", ".git")
    }
    for canonical in sorted(canonical_urls):
        environment[f"GIT_CONFIG_KEY_{count}"] = (
            f"url.{Path(object_store).as_uri()}.insteadOf"
        )
        environment[f"GIT_CONFIG_VALUE_{count}"] = canonical
        count += 1
    environment["GIT_CONFIG_COUNT"] = str(count)
    return environment, revision, version


def pin_fixture_sdk(root: Path, revision: str) -> None:
    """Change only generated fixture dependencies, never canonical SDK pins.

    :param root: Fresh generated consumer root.
    :param revision: Verified immutable SDK object.
    """
    project = root / "pyproject.toml"
    original = project.read_text(encoding="utf-8")
    content, replacements = re.subn(
        r"(git\+https://github\.com/HisQu/apprc\.git@)[0-9a-f]{40}",
        lambda match: match[1] + revision,
        original,
    )
    assert replacements == 4, (
        "Generated core/terminal/GUI/authoring SDK declarations changed."
    )
    project.write_text(content, encoding="utf-8")


def disk_bytes(root: Path) -> int:
    """Count regular owned bytes without following links into shared storage.

    :param root: One bounded fixture checkpoint directory.
    :return: Regular file sizes, counting no symlink targets.
    """
    if not root.exists():
        return 0
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def assert_installed_runtime(package: str, sdk_version: str) -> None:
    """Exercise installed dependencies and initialize declared managed config.

    This entry runs with the installed interpreter under ``-I`` so authoring
    imports and the generated checkout cannot satisfy runtime requirements.

    :param package: Installed generated application import/distribution name.
    :param sdk_version: Version read from the immutable SDK snapshot.
    """
    from importlib.resources import files

    from apprc.user_files.app_home.ownership import inspect_ownership
    from apprc.user_files.env_files.secrets import secret_companion_path
    from packaging.requirements import Requirement

    prefix = Path(sys.prefix).resolve()
    for module in (package, "apprc", "apprc.cli", "apprc_gui", "gradio"):
        imported = importlib.import_module(module)
        module_file = imported.__file__
        assert module_file is not None, f"{module} has no installed module file."
        assert Path(module_file).resolve().is_relative_to(prefix)
    for distribution in ("apprc-core", "apprc", "apprc-gui"):
        assert importlib.metadata.version(distribution) == sdk_version
    assert importlib.metadata.version(package) == "0.1.0"
    assert files(package).joinpath("config/apprc.defaults.env").is_file()
    visited: set[tuple[str, str]] = set()
    pending = [(package, "gui")]
    while pending:
        distribution, extra = pending.pop()
        identity = (distribution.casefold().replace("_", "-"), extra)
        if identity in visited:
            continue
        visited.add(identity)
        environment = {"extra": extra}
        for value in importlib.metadata.requires(distribution) or ():
            requirement = Requirement(value)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            observed = importlib.metadata.version(requirement.name)
            assert not requirement.specifier or requirement.specifier.contains(observed)
            pending.extend(
                (requirement.name, requested) for requested in ("", *requirement.extras)
            )
    assert {"apprc-core", "apprc", "apprc-gui", "gradio"} <= {
        name for name, _ in visited
    }
    app_rc = importlib.import_module(f"{package}.config.bundle").APP_RC
    setup = app_rc.manage().setup()
    assert inspect_ownership(setup.config_dir, package, "config") == "owned"
    assert setup.user_dotenv is not None and setup.user_dotenv.is_file()
    secrets = secret_companion_path(setup.user_dotenv)
    assert secrets.is_file()
    print(
        json.dumps(
            {
                "prefix": str(prefix),
                "sdk_version": sdk_version,
                "checked_requirements": len(visited),
                "managed_config": str(setup.user_dotenv),
                "managed_secrets": str(secrets),
            }
        )
    )


if __name__ == "__main__":
    assert_installed_runtime(sys.argv[1], sys.argv[2])
