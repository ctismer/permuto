"""CLI mirroring the original DOS pipeline.

    python -m permuto                               # just start (permutograph mode)
    python -m permuto pg    <base> <op...>          # -> .pg  on stdout
    python -m permuto gen   <base> <op...>          # -> .nod on stdout
    python -m permuto build <name> <base> <op...>   # write <name>.pg/.nod/.pgd
    python -m permuto show  <name-or-file.nod>      # interactive PySide6 viewer
    python -m permuto show  <session.pms|.ply>      # resume a saved session
    python -m permuto show  <base> <op...>          # build + view on the fly
    python -m permuto iridium                       # the SIMONE satellite simulation
    python -m permuto convert <in.ply> [out.pms]    # migrate a binary session
    python -m permuto render <name.nod> [out.png] [steps]   # offscreen PNG
    python -m permuto export <name> [out.ps] [steps]        # PostScript (SavePicture)
    python -m permuto kugel [out.png] [size] [--floyd]      # the 1991 colour study

The original's two modes are flags here: ``--pg`` starts the permutograph mode
(which is what no arguments does too) and ``--iridium`` starts SIMONE.  Their
1995 spellings ``/PG`` and ``/I`` are gone -- DOS switch syntax, and nothing
else on this command line looks like that.

Example:
    python -m permuto gen 123 12 + 23
    python -m permuto show ikosa2
    python -m permuto show 1234 12 + 23 + 34
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .gen import build

#: what ``polytop /PG`` started with, and so does ``permuto`` on its own
DEFAULT_BASE = "1234"
DEFAULT_OPERATORS = ["12", "+", "23", "+", "34"]


def _as_spec(rest, resolves):
    """Split viewer args into (name, operators, seed).

    ``show 1234 12 + 23`` builds a permutograph from base + operators;
    ``show ikosa2`` / ``show ikosa2 3`` loads a file with an optional seed.
    They are told apart by whether the first argument resolves to a file:
    if it does, a lone trailing integer is a seed; if it does not, the tail
    must be an operator list to build from.  No argument parser can make that
    call, which is why this one is hand-written.
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


# -- what each command does --------------------------------------------
# The heavy imports stay inside these: `permuto gen` must not load Qt.

def _cmd_generate(args) -> int:
    g = build(args.base, args.operators)
    sys.stdout.write("\n".join(g.nod if args.kind == "nod" else g.pg) + "\n")
    return 0


def _cmd_build(args) -> int:
    g = build(args.base, args.operators)
    Path(f"{args.name}.pg").write_text("\n".join(g.pg) + "\n")
    Path(f"{args.name}.nod").write_text("\n".join(g.nod) + "\n")
    Path(f"{args.name}.pgd").write_text(
        f"permuto {args.name} {args.base} {' '.join(args.operators)}\n")
    print(f"wrote {args.name}.pg {args.name}.nod {args.name}.pgd "
          f"({len(g.nod)} nodes)")
    return 0


def _cmd_show(args) -> int:
    from .loader import can_open
    from .ui.viewer import run

    name, operators, seed = _as_spec(args.spec, resolves=can_open)
    return run(name, seed=seed, operators=operators)


def _cmd_start(args=None) -> int:
    """``--pg``, and what no arguments does: the permutograph mode with the
    default base and operators, as ``polytop /PG`` came up in 1995."""
    from .ui.viewer import run

    return run(DEFAULT_BASE, operators=list(DEFAULT_OPERATORS))


def _cmd_iridium(args) -> int:
    from .ui.viewer import run_iridium

    return run_iridium()


def _cmd_convert(args) -> int:
    from .formats.sessionio import convert_ply_to_pms

    dst = args.dst or Path(args.src).with_suffix(".pms")
    convert_ply_to_pms(args.src, dst)
    print(f"converted {args.src} -> {dst}")
    return 0


def _relaxed(name: str, steps: int):
    """The graph both offscreen writers start from."""
    from .core import layout
    from .loader import load_graph

    g = load_graph(name, seed=1)
    for _ in range(steps):
        layout.relax_step(g, alg=layout.Algorithm.RUBBER)
    return g


def _cmd_render(args) -> int:
    from .ui import render as rndr

    g = _relaxed(args.name, args.steps)
    rndr.save_png(g, args.out, labels=args.labels, op_colors=not args.no_op)
    print(f"rendered {args.name} ({g.nnodes} nodes, {g.dimensions}-D) "
          f"-> {args.out}")
    return 0


def _cmd_export(args) -> int:
    from .formats import save_ps

    g = _relaxed(args.name, args.steps)
    save_ps(g, args.out)
    print(f"exported {args.name} ({g.nnodes} nodes, {g.dimensions}-D) "
          f"-> {args.out}")
    return 0


def _cmd_kugel(args) -> int:
    from .studies.kugel import PALETTE, render_sphere
    from .ui.render import indexed_image

    indices = render_sphere(args.size * 200 // 640,   # the original's proportions
                            args.size, args.size * 3 // 4, floyd=args.floyd)
    indexed_image(indices, PALETTE).save(args.out, "PNG")
    print(f"kugel ({'Floyd-Steinberg' if args.floyd else 'ordered dither'}, "
          f"{len(PALETTE) - 2} colours) -> {args.out}")
    return 0


# -- the parser ---------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="permuto", epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", metavar="command")

    for name, kind, what in (("gen", "nod", "write the .nod graph to stdout"),
                             ("pg", "pg", "write the .pg edge list to stdout")):
        c = sub.add_parser(name, help=what)
        c.add_argument("base")
        c.add_argument("operators", nargs="*")
        c.set_defaults(run=_cmd_generate, kind=kind)

    c = sub.add_parser("build", help="write <name>.pg, .nod and .pgd")
    c.add_argument("name")
    c.add_argument("base")
    c.add_argument("operators", nargs="*")
    c.set_defaults(run=_cmd_build)

    c = sub.add_parser("show",
                       help="open a graph, a session, or a base + operators")
    c.add_argument("spec", nargs="+",
                   help="a name, a file, a session, or a base and its operators")
    c.set_defaults(run=_cmd_show)

    c = sub.add_parser("iridium", aliases=["iri"],
                       help="the SIMONE satellite simulation")
    c.set_defaults(run=_cmd_iridium)

    c = sub.add_parser("convert", help="migrate a binary .ply session to .pms")
    c.add_argument("src")
    c.add_argument("dst", nargs="?")
    c.set_defaults(run=_cmd_convert)

    c = sub.add_parser("render", help="relax and write a PNG, without a window")
    c.add_argument("name")
    c.add_argument("out", nargs="?", default="permuto.png")
    c.add_argument("steps", nargs="?", type=int, default=500)
    c.add_argument("--labels", action="store_true", help="write the permutations")
    c.add_argument("--no-op", action="store_true", help="one colour for all edges")
    c.set_defaults(run=_cmd_render)

    c = sub.add_parser("export", help="relax and write PostScript (SavePicture)")
    c.add_argument("name")
    c.add_argument("out", nargs="?", default="permuto.ps")
    c.add_argument("steps", nargs="?", type=int, default=500)
    c.set_defaults(run=_cmd_export)

    c = sub.add_parser("kugel", help="the 1991 colour study")
    c.add_argument("out", nargs="?", default="kugel.png")
    c.add_argument("size", nargs="?", type=int, default=640)
    c.add_argument("--floyd", action="store_true",
                   help="Floyd-Steinberg instead of the ordered dither")
    c.set_defaults(run=_cmd_kugel)

    return p


#: ``polytop``'s two modes as flags -- what ``/PG`` and ``/I`` used to be
_MODE_SWITCHES = {"--iridium": ["iridium"], "--pg": []}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in _MODE_SWITCHES:
        argv = _MODE_SWITCHES[argv[0]] + argv[1:]
    if not argv:
        return _cmd_start()
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:   # --help, or a refusal argparse has printed
        return int(exc.code or 0)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
