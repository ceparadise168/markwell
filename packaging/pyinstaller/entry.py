"""PyInstaller frozen-app entry point for Markwell desktop.

PyInstaller executes its entry script as a top-level ``__main__`` module with no
parent package. A package module that uses relative imports (such as
``markwell/desktop.py`` with ``from .gui.server import ...``) therefore crashes at
startup with ``ImportError: attempted relative import with no known parent
package``.

This bootstrap lives outside the package and uses an absolute import, then hands
off to the real launcher. Keep it thin: it is build glue, not app code. The
PyInstaller spec must point at this file, never at a package submodule.
"""
from markwell.desktop import main

if __name__ == "__main__":
    main()
