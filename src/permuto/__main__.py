"""CLI mirroring the original DOS pipeline.

    python -m permuto pg    <base> <op...>          # -> .pg  on stdout
    python -m permuto gen   <base> <op...>          # -> .nod on stdout
    python -m permuto build <name> <base> <op...>   # write <name>.pg/.nod/.pgd

Example:
    python -m permuto gen 123 12 + 23
"""

from __future__ import annotations

import sys
from pathlib import Path

from .gen import build


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]

    if cmd in ("gen", "pg"):
        base, ops = rest[0], rest[1:]
        g = build(base, ops)
        lines = g.nod if cmd == "gen" else g.pg
        sys.stdout.write("\n".join(lines) + "\n")
        return 0

    if cmd == "build":
        name, base, ops = rest[0], rest[1], rest[2:]
        g = build(base, ops)
        Path(f"{name}.pg").write_text("\n".join(g.pg) + "\n")
        Path(f"{name}.nod").write_text("\n".join(g.nod) + "\n")
        Path(f"{name}.pgd").write_text(f"permuto {name} {base} {' '.join(ops)}\n")
        print(f"wrote {name}.pg {name}.nod {name}.pgd  ({len(g.nod)} nodes)")
        return 0

    print(f"unknown command: {cmd!r}\n{__doc__}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
