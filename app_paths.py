from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


APPLICATION_DATA_DIRECTORY_NAME = "ChessRepertoireMemorizer"
SOURCE_DIRECTORY = Path(__file__).resolve().parent


def is_frozen() -> bool:
    """Return whether the application is running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_directory(
    *,
    frozen: bool | None = None,
    bundle_directory: Path | None = None,
    source_directory: Path | None = None,
) -> Path:
    """Return the read-only root containing bundled application resources."""
    frozen = is_frozen() if frozen is None else frozen
    if frozen:
        if bundle_directory is not None:
            return Path(bundle_directory)
        pyinstaller_directory = getattr(sys, "_MEIPASS", None)
        if pyinstaller_directory:
            return Path(pyinstaller_directory)
        return Path(sys.executable).resolve().parent
    return Path(source_directory) if source_directory is not None else SOURCE_DIRECTORY


def resource_path(
    *parts: str,
    frozen: bool | None = None,
    bundle_directory: Path | None = None,
    source_directory: Path | None = None,
) -> Path:
    """Resolve a read-only asset in source or in PyInstaller's extraction directory."""
    return resource_directory(
        frozen=frozen,
        bundle_directory=bundle_directory,
        source_directory=source_directory,
    ).joinpath(*parts)


def user_data_directory(
    *,
    frozen: bool | None = None,
    environment: Mapping[str, str] | None = None,
    source_directory: Path | None = None,
) -> Path:
    """Return and create the writable per-user data root.

    Source runs intentionally retain the existing repository-local behavior.
    Frozen Windows builds use LOCALAPPDATA and never write into the bundle.
    """
    frozen = is_frozen() if frozen is None else frozen
    if frozen:
        environment = os.environ if environment is None else environment
        local_app_data = environment.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        directory = base / APPLICATION_DATA_DIRECTORY_NAME
    else:
        directory = Path(source_directory) if source_directory is not None else SOURCE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def repertoire_directory(
    *,
    frozen: bool | None = None,
    environment: Mapping[str, str] | None = None,
    source_directory: Path | None = None,
) -> Path:
    """Return and create the writable directory that stores user PGN files."""
    directory = user_data_directory(
        frozen=frozen,
        environment=environment,
        source_directory=source_directory,
    ) / "repertoire"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
