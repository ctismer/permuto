"""Port of ``NodeMgr.SavePicture``: write the graph as a PostScript program.

The output uses the same abstract operators as the original (`SetDimension`,
`DefNode`, `DefAttributes`, `DefEdge` / `DefEdgeOp`, `Finish`), which are
defined by a hand-written PostScript preamble -- itself a little rendering
engine that projects the N-dimensional coordinates, auto-scales the picture
(`CalcMinMax` / `CalcScale`), draws hollow node circles and the operator
digits.  The original program emitted only the *body*; the preamble
(`poly.pre`, dated 19.09.95, "(C) YCHI") lived beside it and had to be
prepended by hand (``x.ps = poly.pre + <name>.p``).

We ship ``poly.pre`` with the package and, by default, prepend it so the export
is a complete, runnable document.  Pass ``preamble=False`` for just the body
(the original's raw ``SavePicture`` output).
"""

from __future__ import annotations

from pathlib import Path

_PREAMBLE = Path(__file__).with_name("poly.pre")


def preamble_text() -> str:
    """The bundled PostScript preamble (CP437 source, kept byte-for-byte)."""
    return _PREAMBLE.read_bytes().decode("latin-1")


def body_lines(g):
    """The ``SavePicture`` body: the stream of DefNode/DefEdge/... calls."""
    out = []
    w = out.append
    w("% Postscript-Output from POLYTOP")
    w("% needs a prelude with the functions ")
    w("% SetDimension, DefNode, DefEdge, DefEdgeOp,")
    w("% DefAttributes and Finish.")
    w("% DefEdgeOp is used for /PG-Mode (Operators used).")
    w("")
    w(f"{g.dimensions} SetDimension")
    w("")
    w("% Node Positions:")
    for nd in g.ordered():
        coords = "".join(f"{nd.pos[k]} " for k in range(g.dimensions))
        w(f"/N{nd.num} dup [{coords} ] def DefNode")
    w("")
    w("% Node Attributes:")
    for nd in g.ordered():
        w(f"[ /N{nd.num} ({nd.num}) ({nd.perm}) {nd.color} ] DefAttributes")
    w("")
    w("% List of Links:")
    for nd in g.ordered():
        for link in nd.links:
            if nd.num < g.nodes[link.to].num:  # each undirected edge once
                if link.op == 0:
                    w(f" /N{nd.num} /N{g.nodes[link.to].num} DefEdge")
                else:
                    w(f" /N{nd.num} /N{g.nodes[link.to].num}  {link.op} DefEdgeOp")
    w("")
    w("% Generate the Picture:")
    w("Finish")
    return out


def save_ps(g, path, *, preamble: bool = True):
    """Write *g* to *path* as PostScript.

    With ``preamble`` (the default) the bundled ``poly.pre`` is prepended, so
    the file is a complete document that a PostScript viewer can render.  The
    original only ever wrote the body; that is ``preamble=False``.
    """
    body = "\n".join(body_lines(g)) + "\n"
    text = (preamble_text() + body) if preamble else body
    Path(path).write_text(text, encoding="latin-1")
    return path
