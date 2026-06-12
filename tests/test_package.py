import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PYINSTALLER_ENTRY = _REPO / "packaging" / "pyinstaller" / "entry.py"


def test_package_imports_with_version():
    import markwell
    assert markwell.__version__ == "0.2.0"


def test_desktop_entrypoint_imports():
    from markwell import desktop
    assert callable(desktop.main)


def test_pyinstaller_entry_runs_as_toplevel_script():
    """PyInstaller runs its entry as a parentless ``__main__`` script, so the
    entry must not rely on relative imports. A module-level import test cannot
    catch that. Running the entry directly with --help must import cleanly and
    exit 0 via argparse — the same import path the frozen app takes at launch."""
    result = subprocess.run(
        [sys.executable, str(_PYINSTALLER_ENTRY), "--help"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONPATH": str(_REPO)},
    )
    assert result.returncode == 0, result.stderr
