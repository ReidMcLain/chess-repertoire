from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_RESOURCES = {
    "VERSION",
    "assets/check_success.json",
    "data/openings/COPYING-lichess-chess-openings.txt",
    "data/openings/README.md",
    "data/openings/metadata.json",
    "data/openings/openings.tsv",
    *{
        f"assets/pieces/{color}{piece}.png"
        for color in ("w", "b")
        for piece in ("K", "Q", "R", "B", "N", "P")
    },
}

FORBIDDEN_FRAGMENTS = {
    ".pgn",
    "chess_com_2026-07-17-opening-report.md",
    "repertoire/archive",
    "repertoire/reid-s-repertoire",
    "tests/",
    "__pycache__",
}


def validate_distribution(distribution: Path) -> list[str]:
    if not distribution.is_dir():
        return [f"Distribution directory does not exist: {distribution}"]
    executable = distribution / "Chess Repertoire Memorizer.exe"
    resource_root = distribution / "_internal"
    if not resource_root.is_dir():
        resource_root = distribution

    missing = sorted(
        name for name in REQUIRED_RESOURCES if not (resource_root / name).is_file()
    )
    names = {
        path.relative_to(distribution).as_posix()
        for path in distribution.rglob("*")
        if path.is_file()
    }
    forbidden = sorted(
        name
        for name in names
        if any(fragment.casefold() in name.casefold() for fragment in FORBIDDEN_FRAGMENTS)
    )
    errors = [] if executable.is_file() else [f"Executable does not exist: {executable}"]
    errors.extend(f"Missing resource in distribution: {name}" for name in missing)
    if not list(resource_root.glob("chess-*.dist-info/licenses/LICENSE.txt")):
        errors.append("The bundled python-chess license text is missing")
    errors.extend(f"Private/development file was packaged: {name}" for name in forbidden)
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python packaging/inspect_build.py <distribution-directory>")
        return 2
    distribution = Path(sys.argv[1]).resolve()
    errors = validate_distribution(distribution)
    if errors:
        print("\n".join(errors))
        return 1
    print(
        f"Validated {distribution.name}: all required resources are present and "
        "personal/development files are absent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
