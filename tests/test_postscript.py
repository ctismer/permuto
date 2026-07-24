"""PostScript export (NodeMgr.SavePicture port), checked against the 1995
golden plot `legacy/modula/plots/x.ps` where an oracle exists."""

import re


def _read(path):
    """PostScript here is CP437 (umlauts in the preamble comments)."""
    return path.read_bytes().decode("latin-1")

from conftest import modula_dir

from permuto.core.graph import Graph
from permuto.formats import save_ps
from permuto.formats.postscript import preamble_text

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
    assert _edge_ops(_read(out)) == gold_edges


def test_bundled_preamble_is_byte_identical_to_the_original():
    """The export is only runnable because we ship the 1995 preamble; it must
    match the legacy file exactly, or the operators it defines drift from what
    the body calls."""
    shipped = preamble_text().encode("latin-1")
    golden = (modula_dir() / "plots" / "poly.pre").read_bytes()
    assert shipped == golden


def test_full_export_is_a_self_contained_document(tmp_path):
    """poly.pre + body: the preamble defines every operator the body uses, so
    the file needs nothing external to render."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    out = tmp_path / "full.ps"
    save_ps(g, out)                       # preamble on by default
    text = _read(out)
    assert text.startswith(preamble_text())
    for op in ("SetDimension", "DefNode", "DefAttributes", "DefEdge",
               "DefEdgeOp", "Finish"):
        assert re.search(rf"/{op}\s*{{", text), f"preamble does not define {op}"
    assert f"{g.dimensions} SetDimension" in text
    assert text.count("def DefNode") == g.nnodes
    assert text.rstrip().endswith("Finish")


def test_body_only_option_matches_the_originals_raw_output(tmp_path):
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    out = tmp_path / "body.ps"
    save_ps(g, out, preamble=False)
    text = out.read_text()
    assert not text.startswith("%!") and "/DefNode {" not in text  # no preamble
    assert text.startswith("% Postscript-Output from POLYTOP")
    assert text.rstrip().endswith("Finish")
