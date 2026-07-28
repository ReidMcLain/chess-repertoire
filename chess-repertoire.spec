# -*- mode: python ; coding: utf-8 -*-

import os
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


project_root = Path(SPECPATH).resolve()
version_text = os.environ.get("CRM_BUILD_VERSION", "1.0").removeprefix("v")
version_parts = [int(part) for part in re.findall(r"\d+", version_text)[:4]]
version_parts.extend([0] * (4 - len(version_parts)))
version_tuple = tuple(version_parts)
windows_version = ".".join(str(part) for part in version_tuple)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version_tuple,
        prodvers=version_tuple,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Reid McLain"),
                        StringStruct("FileDescription", "Chess Repertoire Memorizer"),
                        StringStruct("FileVersion", windows_version),
                        StringStruct("InternalName", "Chess Repertoire Memorizer"),
                        StringStruct("LegalCopyright", "Copyright (c) 2026 Reid McLain"),
                        StringStruct("OriginalFilename", "Chess Repertoire Memorizer.exe"),
                        StringStruct("ProductName", "Chess Repertoire Memorizer"),
                        StringStruct("ProductVersion", windows_version),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)
version_info_path = project_root / "build" / "windows-version-info.txt"
version_info_path.parent.mkdir(parents=True, exist_ok=True)
version_info_path.write_text(str(version_info), encoding="utf-8")

version_resource = Path(
    os.environ.get("CRM_VERSION_RESOURCE", str(project_root / "VERSION"))
).resolve()
if not version_resource.is_file():
    raise FileNotFoundError(f"Version resource not found: {version_resource}")

analysis = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=copy_metadata("chess")
    + [
        (str(project_root / "assets"), "assets"),
        (str(project_root / "data" / "openings"), "data/openings"),
        (str(version_resource), "."),
    ],
    hiddenimports=collect_submodules("chess"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Chess Repertoire Memorizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=os.environ.get("CRM_BUILD_CONSOLE") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_info_path),
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Chess Repertoire Memorizer",
)
