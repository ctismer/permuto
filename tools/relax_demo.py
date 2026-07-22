"""Headless demo of the layout engine: load a permutograph, embed it in 8-D,
relax it, and watch the dimensions "fall" — no GUI, pure integer core.

    python tools/relax_demo.py wuerfel
    python tools/relax_demo.py dodekaed 800
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from permuto.core import intvector as iv  # noqa: E402
from permuto.core import layout  # noqa: E402
from permuto.core.graph import Graph  # noqa: E402


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "wuerfel"
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(root, "legacy", "modula", "nod", f"{name}.nod")

    g = Graph.load_nod(path, dimensions=iv.MAXDIMEN, seed=1)
    print(f"{name}: {g.nnodes} nodes, starting in {g.dimensions}-D")
    last = g.dimensions
    for it in range(1, steps + 1):
        layout.relax_step(g, alg="rubber")
        if g.dimensions != last:
            print(f"  iter {it:4d}: dimension fell {last} -> {g.dimensions}")
            last = g.dimensions
    print(f"final dimension after {steps} iters: {g.dimensions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
