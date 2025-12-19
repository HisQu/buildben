"""Utilities for resolving package paths, both for the installed
site-package and local user data."""

# %%
# --- Standard Lib ---------------------
import os
from pathlib import Path
from importlib.machinery import ModuleSpec

from types import ModuleType

try:
    from holylog import LOG
except ImportError:
    import logging

    LOG = logging.getLogger(__name__)


# %%
def package_root_dir(mod: ModuleType) -> Path:
    """Return the filesystem directory for a regular (non-namespace) package.

    Requires an ``__init__.py`` on disk (i.e., rejects PEP 420 namespace packages).
    Intentionally fails for non-filesystem imports (frozen/zip/etc.).

    This prefers :attr:`module.__spec__.origin` (PEP 451)
    and falls back to :attr:`module.__file__` when needed.

    :param mod: Imported package module.
    :returns: Package directory on disk.
    :raises RuntimeError: If no usable directory can be determined.
    """
    # -- Prefer __spec__.origin ---------------------------------------
    # > e.g.: opa.rag.__spec__.origin = "./OPA/src/opa/rag/__init__.py"
    spec: ModuleSpec | None = getattr(mod, "__spec__", None)
    origin: str | None = getattr(spec, "origin", None) or None
    if origin and isinstance(origin, str):
        p = Path(origin)
        if p.name == "__init__.py" and p.is_file():
            return p.resolve().parent  # !! Early exit
    # -- Fallback to __file__ -----------------------------------------
    file_ = getattr(mod, "__file__", None)
    if file_:
        p = Path(file_).resolve()
        if p.name == "__init__.py" and p.is_file():
            return p.parent
    raise RuntimeError(
        f"Cannot determine package directory for {mod.__name__!r}. "
        "Expected a regular package with an __init__.py on disk."
    )


def require_env(var_name: str) -> str:
    """Return a required environment variable or raise.

    :param var_name: Environment variable name.
    :raises RuntimeError: If the variable is not set or empty.
    """
    value = os.getenv(var_name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable: {var_name}\n"
            f"Set it in your shell or .env, e.g.\n"
            f"  {var_name}=/absolute/path/to/opa_rag"
        )
    return value


def get_local_dir_from_env(env_var: str) -> Path:
    """Return the local root directory for user-writable resources.

    Enforced via environment variable to keep behavior deterministic.

    :param env_var: Name of the env var holding the root path.
    """
    root = Path(require_env(env_var)).expanduser().resolve()
    LOG.info(f"Using '{env_var}' from environment: '{root}'.")
    return root


# ---------------------------------------------------------------------
# -- Hugging Face hook (Explicit call)


def sync_hf_repo_into(
    local_root: Path,
    repo_id: str,
    revision: str | None = None,
    allow_patterns: list[str] | str | None = None,
    ignore_patterns: list[str] | str | None = None,
) -> Path:
    """Pull a Hugging Face repo snapshot into a specific local folder.

    Uses `snapshot_download(..., local_dir=...)` which is designed for repeatedly
    pulling updates into a chosen folder and maintains a `.cache/huggingface/`
    metadata directory under `local_dir`. :contentReference[oaicite:3]{index=3}

    Authentication can be provided via HF_TOKEN / HF_HOME configuration.

    :param local_root: Target folder (your OPA_RAG_ROOT).
    :param repo_id: Hub repo id, e.g. "Org/name".
    :param revision: Branch, tag, or commit hash.
    :param allow_patterns: Optional glob(s) to limit what gets pulled.
    :param ignore_patterns: Optional glob(s) to exclude files.
    :returns: The local_root (for convenience).
    """
    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        raise RuntimeError(
            "huggingface_hub is required for Hugging Face sync. "
            "Install it (e.g. add an extra) to use this feature."
        ) from e

    local_root.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=str(local_root),
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )
    return local_root


def sync_hf_if_configured(local_root: Path) -> None:
    """Sync from Hugging Face if OPA_RAG_HF_REPO is set."""
    repo_id = os.getenv("OPA_RAG_HF_REPO")
    if not repo_id:
        return

    revision = os.getenv("OPA_RAG_HF_REVISION") or None

    LOG.info(f"Syncing Hugging Face repo '{repo_id}' into '{local_root}'...")
    sync_hf_repo_into(
        local_root=local_root,
        repo_id=repo_id,
        revision=revision,
        # > Example: allow_patterns=["rag_workdir/**"] if you only want the workdir.
    )
