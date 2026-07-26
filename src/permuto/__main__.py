"""CLI mirroring the original DOS pipeline.

    python -m permuto                               # just start (permutograph mode)
    python -m permuto pg    <base> <op...>          # -> .pg  on stdout
    python -m permuto gen   <base> <op...>          # -> .nod on stdout
    python -m permuto build <name> <base> <op...>   # write <name>.pg/.nod/.pgd
    python -m permuto show  <name-or-file.nod>      # interactive PySide6 viewer
    python -m permuto show  <session.pms|.ply>      # resume a saved session
    python -m permuto show  <base> <op...>          # build + view on the fly
    python -m permuto iridium                       # the /I satellite simulation
    python -m permuto convert <in.ply> [out.pms]    # migrate a binary session
    python -m permuto render <name.nod> [out.png] [steps]   # offscreen PNG
    python -m permuto export <name> [out.ps] [steps]        # PostScript (SavePicture)
    python -m permuto kugel [out.png] [size] [--floyd]      # the 1991 colour study

Example:
    python -m permuto gen 123 12 + 23
    python -m permuto show ikosa2
    python -m permuto show 1234 12 + 23 + 34
"""

from __future__ import annotations

import sys
from pathlib import Path

from .gen import build


def _as_spec(rest, resolves):
    """Split viewer args into (name, operators, seed).

    ``show 1234 12 + 23`` builds a permutograph from base + operators;
    ``show ikosa2`` / ``show ikosa2 3`` loads a file with an optional seed.
    They are told apart by whether the first argument resolves to a file:
    if it does, a lone trailing integer is a seed; if it does not, the tail
    must be an operator list to build from.
    """
    name = rest[0]
    tail = rest[1:]
    if not tail:
        return name, None, 1
    if resolves(name):
        if len(tail) == 1 and tail[0].lstrip("-").isdigit():
            return name, None, int(tail[0])     # name + seed
        return name, None, 1                     # a file ignores trailing junk
    return name, tail, 1                          # base + operators


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if not argv:
        # no arguments: just start, in permutograph mode with the default
        # graph (base 1234, operators 12/23/34), as /PG did
        from .ui.viewer import run
        return run("1234", operators=["12", "+", "23", "+", "34"])
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
        from .ui.viewer import _resolve_file, run

        name, operators, seed = _as_spec(
            rest, resolves=lambda n: _resolve_file(n) is not None)
        return run(name, seed=seed, operators=operators)

    if cmd in ("iridium", "iri", "/i", "/I"):
        from .ui.viewer import run_iridium
        return run_iridium()

    if cmd == "convert":
        from .formats.sessionio import convert_ply_to_pms

        src = rest[0]
        dst = rest[1] if len(rest) > 1 else Path(src).with_suffix(".pms")
        convert_ply_to_pms(src, dst)
        print(f"converted {src} -> {dst}")
        return 0

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

    if cmd == "kugel":
        from .studies.kugel import PALETTE, render_sphere
        from .ui.render import indexed_image

        pos = [a for a in rest if not a.startswith("--")]
        flags = {a for a in rest if a.startswith("--")}
        out = pos[0] if pos else "kugel.png"
        size = int(pos[1]) if len(pos) > 1 else 640
        floyd = "--floyd" in flags
        indices = render_sphere(size * 200 // 640,     # the original's proportions
                                size, size * 3 // 4, floyd=floyd)
        indexed_image(indices, PALETTE).save(out, "PNG")
        print(f"kugel ({'Floyd-Steinberg' if floyd else 'ordered dither'}, "
              f"{len(PALETTE) - 2} colours) -> {out}")
        return 0

    print(f"unknown command: {cmd!r}\n{__doc__}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
