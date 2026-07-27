"""The .pms text session format: it must preserve everything the binary .ply
held -- above all the relaxed coordinates -- and reach where .ply could not
(an Iridium session)."""

import pytest

from conftest import ply_files

from permuto import FileFormatError
from permuto.core import layout
from permuto.core.graph import Graph, Link, Node
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


def _links_key(nd):
    """Everything the edges of *nd* know, in one comparable value."""
    return tuple((lk.to, lk.op, lk.status, lk.broken) for lk in nd.links)


def graphs_agree(a: Graph, b: Graph) -> bool:
    if (a.nnodes, a.dimensions) != (b.nnodes, b.dimensions):
        return False
    for n in a.nodes:
        na, nb = a.nodes[n], b.nodes[n]
        if na.perm != nb.perm or na.color != nb.color:
            return False
        if na.pos[:a.dimensions] != nb.pos[:b.dimensions]:
            return False
        if _links_key(na) != _links_key(nb):
            return False
        if na.state != nb.state:
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
    """SPA/ParSum fields and the broken edges are part of a session too.

    (This test used to mark link 3 of a node that has two -- the old `broken`
    set took any number.  A link carries its own mark now, so there is no
    number to be wrong about.)"""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    nd = g.nodes[1]
    nd.state.dead = True
    nd.state.display, nd.state.step, nd.state.sum = 5, 2, 9
    nd.links[0].broken = True
    nd.links[1].broken = True
    nd.links[0].status, nd.links[1].status = 1, 2

    out = tmp_path / "prog.pms"
    write_pms(out, PlySession(graph=g, mode="permuto", base="123"))
    back = read_pms(out).graph.nodes[1]
    assert back.state.dead and back.state.display == 5
    assert [lk.broken for lk in back.links] == [True, True]


def test_iteration_counter_round_trips(tmp_path):
    """.pms stores the relaxation step counter so a reloaded session shows where
    it was -- the binary .ply never did (the original reset it to 0 on load)."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    out = tmp_path / "s.pms"
    write_pms(out, PlySession(graph=g, mode="permuto", base="123", iteration=123))
    assert read_pms(out).iteration == 123


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
        "end\n"
    )
    s = read_pms(p)
    assert s.mode == "polytop" and s.graph.nnodes == 2
    assert s.graph.nodes[1].pos[:2] == [100, 200]


def test_save_adds_the_pms_extension_when_none_is_given(tmp_path):
    """A bare name like "xanti" must land as xanti.pms, not extensionless.
    (init=False keeps coordinates at 0 so the .ply case fits its 16-bit format.)"""
    g = Graph.build("123", ["12", "+", "23"], seed=1, init=False)
    sess = PlySession(graph=g, mode="permuto", base="123")
    assert save_session(tmp_path / "xanti", sess).name == "xanti.pms"
    assert save_session(tmp_path / "keep.pms", sess).name == "keep.pms"
    assert save_session(tmp_path / "old.ply", sess).name == "old.ply"


def test_load_session_detects_format_by_content(tmp_path):
    """load_session dispatches on what the file is, not its name: .pms text
    written into a .ply-named file must still load as .pms."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)   # relaxed coords are fine in text
    mislabelled = tmp_path / "mislabelled.ply"
    write_pms(mislabelled, PlySession(graph=g, mode="permuto", base="123"))
    loaded = load_session(mislabelled)
    assert loaded.mode == "permuto"
    assert graphs_agree(g, loaded.graph)


# A file that ends properly ('end' present) but is inconsistent is corruption,
# not truncation, and must be rejected -- leniency is for truncation alone.
@pytest.mark.parametrize("text,detail", [
    ("nothing here\n", "not a"),
    ("permuto session 1\ndim 2\nnodes 5\nnode 1 pos=0,0\nend\n", "says 5 nodes"),
    ("permuto session 1\ndim 2\nnodes 1\nnode 1 pos=0,0 links=9:0\nend\n", "does not exist"),
    ("permuto session 1\ndim 99\nnodes 0\nend\n", "outside 1..8"),
    ("permuto session 1\ndim 2\nnodes 1\nnode 1 pos=0\nend\n", "expected dim=2"),
    ("permuto session 1\ndim 2\nnodes 1\nnode 1 color=1\nend\n", "no pos"),
    ("permuto session 1\ndim 2\nnodes 0\nbogus 1\nend\n", "unknown key"),
])
def test_malformed_files_are_reported(tmp_path, text, detail):
    p = tmp_path / "bad.pms"
    p.write_text(text)
    with pytest.raises(FileFormatError) as exc:
        read_pms(p)
    assert detail in str(exc.value)


def test_truncation_is_salvaged_with_a_warning_not_rejected(tmp_path):
    """A cut file is loaded, not refused: the reader keeps what parsed,
    zero-fills the rest (coordinates re-derive from the relaxation) and reports
    it in .warnings.  A cut inside the last node line is caught too, which the
    node count alone would miss."""
    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(30):
        layout.relax_step(g, alg="rubber")
    full = tmp_path / "full.pms"
    write_pms(full, PlySession(graph=g, mode="permuto", base="1234"))
    data = full.read_text()
    lines = data.splitlines(keepends=True)

    damaged = {                                  # whole node lines lost off the end
        "half the lines": "".join(lines[:len(lines) // 2]),
        "half the bytes": data[:len(data) // 2],
    }
    for label, text in damaged.items():
        p = tmp_path / "cut.pms"
        p.write_text(text)
        s = read_pms(p)                          # loads, does not raise
        assert any("truncated" in w for w in s.warnings), f"{label}: not flagged"
        assert 1 <= s.graph.nnodes < g.nnodes

    assert not read_pms(full).warnings           # the intact file: no warnings


def test_a_file_without_the_end_marker_is_flagged_but_loaded(tmp_path):
    """The 'end' trailer is new.  A file missing it -- an older save, or one
    truncated exactly on a boundary -- cannot be proven complete, so it is
    always noted, but reassuringly ('loaded fully') when nothing looks lost and
    plainly ('truncated') when nodes are missing."""
    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(30):
        layout.relax_step(g, alg="rubber")
    full = tmp_path / "full.pms"
    write_pms(full, PlySession(graph=g, mode="permuto", base="1234"))

    no_end = full.read_text().rstrip()
    assert no_end.endswith("end")
    no_end = no_end[:-len("end")].rstrip() + "\n"     # drop just the 'end' line
    p = tmp_path / "old.pms"
    p.write_text(no_end)

    s = read_pms(p)
    assert s.graph.nnodes == g.nnodes                  # nothing actually lost
    assert len(s.warnings) == 1 and "loaded fully" in s.warnings[0]




# -- the refusals ------------------------------------------------------------
# "Reject with a reason instead of swallowing it" is the port's stated
# advantage over the original (PORT-GAPS section 0).  Nobody had checked that
# the reasons arrive -- and two of them did not.

HEAD = "permuto session 1\nmode polytop\ndim 2\nnodes 1\n"


@pytest.mark.parametrize("text,detail", [
    (HEAD + "node 1 pos=1,2,x\nend\n", "'x' where a number belongs"),
    (HEAD + "node 1 pos=1,zzz\nend\n", "'zzz' where a number belongs"),
    (HEAD + "node 1 pos=1.5,2.5\nend\n", "'1.5' where a number belongs"),
    (HEAD + "node 1 pos=0,0 rubbish\nend\n", "expected key=value"),
    (HEAD + "node 1 pos=0,0 links=x:y\nend\n", "bad link"),
    (HEAD + "node 1 pos=0,0 wobble=3\nend\n", "unknown node field 'wobble'"),
    ("permuto session 1\nmode permuto\nbase 1234\nop 99 12\ndim 2\nnodes 0\nend\n",
     "operator 99 is outside 1..12"),
    ("permuto session 1\nmode permuto\nbase 1234\nop 1 99\ndim 2\nnodes 0\nend\n",
     "outside 1..4 of base '1234'"),
])
def test_a_refusal_says_which_text_it_choked_on(tmp_path, text, detail):
    p = tmp_path / "bad.pms"
    p.write_text(text)
    with pytest.raises(FileFormatError) as exc:
        read_pms(p)
    assert detail in str(exc.value)
    assert "line" in str(exc.value), "and where"


def test_junk_among_the_right_number_of_coordinates_is_not_swallowed(tmp_path):
    """`pos=1,2,x` at dim=2 used to load as a clean node: the parser dropped
    anything that was not a number and then counted what was left, so the count
    happened to match and nothing was said."""
    p = tmp_path / "junk.pms"
    p.write_text(HEAD + "node 1 pos=1,2,x\nend\n")
    with pytest.raises(FileFormatError):
        read_pms(p)


def test_an_operator_the_base_cannot_carry_is_refused(tmp_path):
    """The reader passed the table straight to PM's constructor, which only
    validates the base -- so a cycle addressing positions the base does not
    have was loaded without a word, and the editor opened on it.  It goes
    through set_cycle now, which is where that rule lives."""
    p = tmp_path / "ops.pms"
    p.write_text("permuto session 1\nmode permuto\nbase 1234\nop 1 99\n"
                 "dim 2\nnodes 0\nend\n")
    with pytest.raises(FileFormatError) as exc:
        read_pms(p)
    assert "unusable operators" in str(exc.value)


def test_a_number_cut_in_half_is_still_a_truncation_not_corruption(tmp_path):
    """The leniency has to survive the stricter parse: a file cut mid-number
    ends with something like `pos=7,-`, which is a cut and not junk."""
    p = tmp_path / "cut.pms"
    p.write_text("permuto session 1\nmode polytop\ndim 2\nnodes 2\n"
                 "node 1 pos=5,6\nnode 2 pos=7,-\n")
    s = read_pms(p)                      # loads, does not raise
    assert s.graph.nnodes == 2
    assert any("cut at '-'" in w for w in s.warnings)
    assert any("zero-filled" in w for w in s.warnings)


def test_negative_coordinates_are_ordinary(tmp_path):
    """The stricter parse must not start refusing the minus sign."""
    p = tmp_path / "neg.pms"
    p.write_text(HEAD + "node 1 pos=-3,4\nend\n")
    assert read_pms(p).graph.nodes[1].pos[:2] == [-3, 4]
