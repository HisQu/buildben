"""Verify the public surface of an installed Buildben distribution."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import importlib.resources
import shutil
import subprocess
from dataclasses import dataclass

REQUIRED_RESOURCES = (
    "_templates_proj/_justfile",
    "_templates_proj/_github-ci.yml",
    "_templates_proj/_github-release.yml",
)


@dataclass(frozen=True, slots=True)
class InstallSnapshot:
    """Record the installed package state needed by the smoke test.

    :param version: Installed Buildben distribution version.
    :param module_file: Location of the imported package.
    :param resources: Required package resources found in the distribution.
    :param console_path: Installed ``bube`` console script path.
    :param help_returncode: Exit code returned by ``bube --help``.
    :param help_output: Combined standard output and error from the help call.
    """

    version: str
    module_file: str | None
    resources: tuple[str, ...]
    console_path: str | None
    help_returncode: int
    help_output: str


def capture_install_snapshot() -> InstallSnapshot:
    """Inspect the installed package, templates, and ``bube`` entry point.

    :return: Installed module, metadata, resource, and CLI state.
    """
    import buildben

    package_files = importlib.resources.files("buildben")
    resources = tuple(
        resource
        for resource in REQUIRED_RESOURCES
        if package_files.joinpath(*resource.split("/")).is_file()
    )
    console_path = shutil.which("bube")
    if console_path is None:
        return InstallSnapshot(
            version=metadata.version("buildben"),
            module_file=buildben.__file__,
            resources=resources,
            console_path=None,
            help_returncode=127,
            help_output="The bube console script is not on PATH.",
        )
    help_result = subprocess.run(
        [console_path, "--help"], capture_output=True, check=False, text=True
    )
    return InstallSnapshot(
        version=metadata.version("buildben"),
        module_file=buildben.__file__,
        resources=resources,
        console_path=console_path,
        help_returncode=help_result.returncode,
        help_output=f"{help_result.stdout}\n{help_result.stderr}",
    )


def validate_install_snapshot(
    snapshot: InstallSnapshot, expected_version: str | None = None
) -> None:
    """Reject an installed package that violates Buildben's base contract.

    :param snapshot: Installed state captured after importing the package.
    :param expected_version: Optional artifact version to compare with metadata.
    :return: None.
    """
    if expected_version is not None:
        assert snapshot.version == expected_version
    assert snapshot.module_file
    assert set(REQUIRED_RESOURCES).issubset(snapshot.resources)
    assert snapshot.console_path
    assert snapshot.help_returncode == 0
    assert "usage: buildben" in snapshot.help_output.lower()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse install-smoke command arguments.

    :param argv: Optional argument vector used by tests.
    :return: Parsed command namespace.
    """
    parser = argparse.ArgumentParser(
        description="Smoke-test an installed Buildben distribution."
    )
    parser.add_argument("--expected-version", help="Optional version to require.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the installed-distribution smoke test.

    :param argv: Optional argument vector used by tests.
    :return: Process exit code.
    """
    args = parse_args(argv)
    validate_install_snapshot(
        capture_install_snapshot(), expected_version=args.expected_version
    )
    print("Buildben install smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
