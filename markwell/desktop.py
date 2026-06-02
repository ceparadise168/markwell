"""Desktop launcher entrypoint for packaged Markwell apps."""
from __future__ import annotations

import sys

from .gui.server import main as gui_main


def main(argv=None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--desktop" not in args:
        args.insert(0, "--desktop")
    gui_main(args)


if __name__ == "__main__":
    main()
