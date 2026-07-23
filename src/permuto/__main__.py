"""CLI mirroring the original DOS pipeline.

    python -m permuto pg    <base> <op...>          # -> .pg  on stdout
    python -m permuto gen   <base> <op...>          # -> .nod on stdout
    python -m permuto build <name> <base> <op...>   # write <name>.pg/.nod/.pgd
    python -m permuto show  <name-or-file.nod>      # interactive PySide6 viewer
    python -m permuto render <name.nod> [out.png] [steps]   # offscreen PNG
    python -m permuto export <name> [out.ps] [steps]        # PostScript (SavePicture)

Example:
    python -m permuto gen 123 12 + 23
    python -m permuto show ikosa2
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

    if cmd == "show":
        from .ui.viewer import run
        return run(rest[0], seed=int(rest[1]) if len(rest) > 1 else 1)

    if cmd == "render":
        from .core import layout
        from .ui import render as rndr
        from .ui.viewer import load_graph

        pos = [a for a in rest if not a.startswith("--")]
        flags = {a for a in rest if a.startswith("--")}
        name = pos[0]
        out = pos[1] if len(pos) > 1 else "permuto.png"
        steps = int(pos[2]) if len(pos) > 2 else 500
        g = load_graph(name, seed=1)
        for _ in range(steps):
            layout.relax_step(g, alg="rubber")
        rndr.save_png(g, out, labels="--labels" in flags,
                      op_colors="--no-op" not in flags)
        print(f"rendered {name} ({g.nnodes} nodes, {g.dimensions}-D) -> {out}")
        return 0

    if cmd == "export":
        from .core import layout
        from .formats import save_ps
        from .ui.viewer import load_graph

        pos = [a for a in rest if not a.startswith("--")]
        name = pos[0]
        out = pos[1] if len(pos) > 1 else "permuto.ps"
        steps = int(pos[2]) if len(pos) > 2 else 500
        g = load_graph(name, seed=1)
        for _ in range(steps):
            layout.relax_step(g, alg="rubber")
        save_ps(g, out)
        print(f"exported {name} ({g.nnodes} nodes, {g.dimensions}-D) -> {out}")
        return 0

    print(f"unknown command: {cmd!r}\n{__doc__}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
