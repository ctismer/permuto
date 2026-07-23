"""PostScript export (NodeMgr.SavePicture port) structure."""

from permuto.core.graph import Graph
from permuto.formats import save_ps


def test_ps_structure(tmp_path):
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    out = tmp_path / "out.ps"
    save_ps(g, out)
    text = out.read_text()
    assert "SetDimension" in text
    assert text.count("def DefNode") == g.nnodes          # one node line each
    assert text.count("] DefAttributes") == g.nnodes      # (avoid header comment)
    assert "DefEdgeOp" in text                             # built with operators
    assert text.rstrip().endswith("Finish")
