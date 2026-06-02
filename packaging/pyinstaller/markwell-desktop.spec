# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Markwell desktop launcher.

Build from the repository root:

    pyinstaller packaging/pyinstaller/markwell-desktop.spec --clean --noconfirm

The entry point is the thin `entry.py` bootstrap in this directory, which imports
`markwell.desktop` (absolute) and starts the existing localhost GUI in desktop
lifecycle mode. PyInstaller runs its entry as a parentless `__main__` script, so
it must not be a package module that uses relative imports. The spec intentionally
collects only package GUI assets, never local user data from the repository root.
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


ROOT = Path(SPECPATH).parents[1]
# PyInstaller runs the entry as a top-level __main__ script with no parent
# package, so it must be the thin bootstrap rather than markwell/desktop.py,
# which uses relative imports. See entry.py.
ENTRYPOINT = Path(SPECPATH) / "entry.py"

FORBIDDEN_ARTIFACT_INPUTS = (
    ".kobo/*",
    "output/*",
    "backups/*",
    "*.sqlite",
    "*.sqlite-shm",
    "*.sqlite-wal",
    ".playwright-mcp/*",
    ".pytest_cache/*",
    "__pycache__/*",
)


def allowed_data(item):
    src, _dest = item
    try:
        rel = Path(src).resolve().relative_to(ROOT)
    except ValueError:
        return True
    rel_posix = rel.as_posix()
    return not any(fnmatch.fnmatch(rel_posix, pat) for pat in FORBIDDEN_ARTIFACT_INPUTS)


datas = [
    item for item in collect_data_files("markwell.gui", includes=["assets/*"])
    if allowed_data(item)
]

block_cipher = None

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Markwell",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Markwell",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Markwell.app",
        icon=None,
        bundle_identifier="io.github.ceparadise168.markwell",
        info_plist={
            "CFBundleName": "Markwell",
            "CFBundleDisplayName": "Markwell",
            "NSHighResolutionCapable": "True",
        },
    )
