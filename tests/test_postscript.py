"""PostScript export (NodeMgr.SavePicture port), checked against the 1995
golden plot `legacy/modula/plots/x.ps` where an oracle exists."""

import re

from conftest import modula_dir

from permuto.core.graph import Graph
from permuto.formats import save_ps

# x.ps is preamble + the SavePicture body for pgl4 (base 1234, ops 12/23/34).
PGL4 = ("1234", ["12", "+", "23", "+", "34"])


def _edge_ops(text):
    """The (from, to, operator) triples emitted as `/Na /Nb  k DefEdgeOp`."""
    return set(re.findall(r"/N(\d+) /N(\d+)\s+(\d+) DefEdgeOp", text))


def test_edge_operators_match_the_1995_golden_plot(tmp_path):
    """The exported edge list -- node numbering, the each-edge-once rule, and
    the operator number per edge -- must equal the body of the original's own
    PostScript output.  Coordinates are not compared (the relaxation seed is
    lost), but the topology and operator identity are fully deterministic.
    """
    golden = (modula_dir() / "plots" / "x.ps").read_bytes().decode("latin-1")
    gold_edges = _edge_ops(golden)
    assert len(gold_edges) == 36, "sanity: pgl4 has 36 edges in the golden file"

    g = Graph.build(*PGL4, init=False)
    out = tmp_path / "pgl4.ps"
    save_ps(g, out)
    assert _edge_ops(out.read_text()) == gold_edges


def test_structure_and_node_lines(tmp_path):
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    out = tmp_path / "out.ps"
    save_ps(g, out)
    text = out.read_text()
    assert f"{g.dimensions} SetDimension" in text
    assert text.count("def DefNode") == g.nnodes
    assert text.count("] DefAttributes") == g.nnodes
    assert text.rstrip().endswith("Finish")
