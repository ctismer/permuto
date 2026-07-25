"""The .pms text session format: it must preserve everything the binary .ply
held -- above all the relaxed coordinates -- and reach where .ply could not
(an Iridium session)."""

import pytest

from conftest import ply_files

from permuto import FileFormatError
from permuto.core import layout
from permuto.core.graph import Graph, Node
from permuto.core.iri import Iridium
from permuto.formats import (
    PlySession,
    load_session,
    read_ply,
    read_pms,
    save_session,
    write_pms,
)

PLY = ply_files()
PLY_IDS = [p.stem for p in PLY]


def _state_key(st, nlink):
    # normalise line states to length nlink, so [] and [0]*nlink -- both meaning
    # "no line states" -- compare equal regardless of how the node was created
    lines = tuple((list(st.lines) + [0] * nlink)[:nlink])
    return (st.dead, st.active, st.display, st.step, st.sum,
            frozenset(st.broken), lines)


def graphs_agree(a: Graph, b: Graph) -> bool:
    if (a.nnodes, a.dimensions) != (b.nnodes, b.dimensions):
        return False
    for n in a.nodes:
        na, nb = a.nodes[n], b.nodes[n]
        if na.perm != nb.perm or na.color != nb.color:
            return False
        if na.pos[:a.dimensions] != nb.pos[:b.dimensions]:
            return False
        if na.links != nb.links or list(na.opno) != list(nb.opno):
            return False
        if _state_key(na.state, na.nlink) != _state_key(nb.state, nb.nlink):
            return False
        if na.iri != nb.iri:
            return False
    return True


@pytest.mark.skipif(not PLY, reason="no .ply files")
@pytest.mark.parametrize("path", PLY, ids=PLY_IDS)
def test_every_1995_ply_survives_the_trip_through_text(path, tmp_path):
    """Load the binary session, write it as text, read it back -- the graph,
    the coordinates, the topology and the program/Iridium state must all be
    identical.  This is the acceptance test for the format."""
    original = read_ply(path)
    out = tmp_path / (path.stem + ".pms")
    write_pms(out, original)
    assert graphs_agree(original.graph, read_pms(out).graph)


@pytest.mark.skipif(not PLY, reason="no .ply files")
def test_text_is_smaller_than_the_binary_dump(tmp_path):
    """No padding, no zero fields -- the readable format is also the smaller one."""
    p = next(x for x in PLY if x.stem == "pg24")
    out = tmp_path / "pg24.pms"
    write_pms(out, read_ply(p))
    assert out.stat().st_size < p.stat().st_size


def test_coordinates_are_the_point_and_are_kept_exactly(tmp_path):
    """The essence of a session is the relaxed integer coordinates; a text
    format keeps them exactly because they are already integers."""
    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(200):
        layout.relax_step(g, alg="rubber")
    before = {n: list(nd.pos[:g.dimensions]) for n, nd in g.nodes.items()}

    out = tmp_path / "s.pms"
    write_pms(out, PlySession(graph=g, mode="permuto", base="1234"))
    back = read_pms(out).graph
    assert all(back.nodes[n].pos[:back.dimensions] == before[n] for n in before)


def test_an_iridium_session_round_trips_which_ply_could_not(tmp_path):
    """The original could not save in /I mode at all; .pms can, because it
    stores the graph explicitly instead of regenerating it."""
    g = Graph()
    g.set_dimensions(2)
    iri = Iridium(g)
    while not iri.built:
        iri.new_node()
        for _ in range(5):
            layout.backup(g)
            layout.contract(g, "new")
            layout.normalize(g)
    iri.transmit("900", "009")
    iri.step()
    live = [n for n, nd in g.nodes.items() if nd.iri.target or nd.iri.avail != 10000]

    out = tmp_path / "sim.pms"
    write_pms(out, PlySession(graph=g, mode="iridium"))
    back = read_pms(out)

    assert back.mode == "iridium"
    assert back.graph.nnodes == 55
    assert graphs_agree(g, back.graph)
    assert live and all(back.graph.nodes[n].iri == g.nodes[n].iri for n in live)


def test_program_state_survives(tmp_path):
    """SPA/ParSum fields and the broken-edge set are part of a session too."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    nd = g.nodes[1]
    nd.state.dead = True
    nd.state.display, nd.state.step, nd.state.sum = 5, 2, 9
    nd.state.broken = {1, 3}
    nd.state.lines = [1, 0, 2]

    out = tmp_path / "prog.pms"
    write_pms(out, PlySession(graph=g, mode="permuto", base="123"))
    back = read_pms(out).graph.nodes[1]
    assert back.state.dead and back.state.display == 5
    assert back.state.broken == {1, 3}


def test_comments_and_blank_lines_are_ignored(tmp_path):
    p = tmp_path / "c.pms"
    p.write_text(
        "permuto session 1\n"
        "% this is a comment\n"
        "\n"
        "mode polytop\n"
        "dim 2\n"
        "nodes 2\n"
        "% node lines follow\n"
        "node 1 color=1 pos=100,200 links=2:0\n"
        "node 2 color=1 pos=-100,-200 links=1:0\n"
    )
    s = read_pms(p)
    assert s.mode == "polytop" and s.graph.nnodes == 2
    assert s.graph.nodes[1].pos[:2] == [100, 200]


def test_save_adds_the_pms_extension_when_none_is_given(tmp_path):
    """A bare name like "xanti" must land as xanti.pms, not extensionless."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    sess = PlySession(graph=g, mode="permuto", base="123")
    assert save_session(tmp_path / "xanti", sess).name == "xanti.pms"
    assert save_session(tmp_path / "keep.pms", sess).name == "keep.pms"
    assert save_session(tmp_path / "old.ply", sess).name == "old.ply"


def test_load_session_detects_format_by_content(tmp_path):
    """load_session dispatches on what the file is, not its name."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    pms = tmp_path / "mislabelled.ply"     # .ply name, .pms content
    save_session(pms, PlySession(graph=g, mode="permuto", base="123"))
    loaded = load_session(pms)
    assert loaded.mode == "permuto"
    assert graphs_agree(g, loaded.graph)


@pytest.mark.parametrize("text,detail", [
    ("nothing here\n", "not a"),
    ("permuto session 1\ndim 2\nnodes 5\nnode 1 pos=0,0\n", "says 5 nodes"),
    ("permuto session 1\ndim 2\nnodes 1\nnode 1 pos=0,0 links=9:0\n", "does not exist"),
    ("permuto session 1\ndim 99\nnodes 0\n", "outside 1..8"),
])
def test_malformed_files_are_reported(tmp_path, text, detail):
    p = tmp_path / "bad.pms"
    p.write_text(text)
    with pytest.raises(FileFormatError) as exc:
        read_pms(p)
    assert detail in str(exc.value)
