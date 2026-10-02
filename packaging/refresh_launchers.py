"""Refresh Windows virtual-environment launchers after moving the project."""

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from pip._vendor.distlib.scripts import ScriptMaker


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    for name in (".venv", ".build-venv"):
        scripts = root / name / "Scripts"
        for executable in scripts.glob("*.exe"):
            try:
                with ZipFile(executable) as archive:
                    script = archive.read("__main__.py")
            except (BadZipFile, KeyError):
                continue  # The Python interpreter itself is not a script launcher.
            maker = ScriptMaker(None, str(scripts))
            maker.executable = str(scripts / "python.exe")
            maker.clobber = True
            maker._write_script(
                [executable.stem], maker._get_shebang("utf-8"), script, [], "py"
            )
            print(f"Refreshed {executable.relative_to(root)}")


if __name__ == "__main__":
    main()
