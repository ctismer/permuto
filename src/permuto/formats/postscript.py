"""Port of ``NodeMgr.SavePicture``: write the graph as a PostScript program.

The output uses the same abstract operators as the original (`SetDimension`,
`DefNode`, `DefAttributes`, `DefEdge` / `DefEdgeOp`, `Finish`) and expects a
matching prelude (see ``legacy/modula/plots/poly.pre``). Node positions are the
full N-dimensional integer vectors; `DefEdgeOp` carries the operator number.
"""

from __future__ import annotations

from pathlib import Path


def save_ps(g, path):
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
        for idx, j in enumerate(nd.links):
            if nd.num < g.nodes[j].num:  # each undirected edge once
                op = nd.opno[idx] if idx < len(nd.opno) else 0
                if op == 0:
                    w(f" /N{nd.num} /N{g.nodes[j].num} DefEdge")
                else:
                    w(f" /N{nd.num} /N{g.nodes[j].num}  {op} DefEdgeOp")
    w("")
    w("% Generate the Picture:")
    w("Finish")
    Path(path).write_text("\n".join(out) + "\n")
    return path
