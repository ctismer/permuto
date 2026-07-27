"""The .ply binary session format, checked against the files the original
program actually wrote in 1995."""

import struct

import pytest

from conftest import ply_files
from permuto import FileFormatError
from permuto.core.graph import Graph, Link, Node
from permuto.formats import PlySession, read_ply, write_ply
from permuto.formats.plyfile import HEADER_SIZE, RECORD_SIZE

PLY = ply_files()
PLY_IDS = [p.stem for p in PLY]

pytestmark = pytest.mark.skipif(not PLY, reason="no .ply files found")


@pytest.mark.parametrize("path", PLY, ids=PLY_IDS)
def test_stored_graph_matches_what_pm_recomputes(path):
    """The strongest check available: every .ply carries both the generating
    parameters and the resulting graph, so the 1995 program's own output is the
    oracle for our PM port -- permutations, edges and operator numbers alike.
    """
    session = read_ply(path)
    stored, built = session.graph, session.pm.new_permutograph()

    assert [nd.perm for nd in stored.ordered()] == [nd.perm for nd in built.ordered()]

    def edges(g):
        return {tuple(sorted((n, j)))
                for n in g.nodes for j in g.nodes[n].neighbours}

    def ops(g):
        return {(n, lk.to): lk.op for n in g.nodes
                for lk in g.nodes[n].links}

    assert edges(stored) == edges(built)
    assert ops(stored) == ops(built)


@pytest.mark.parametrize("path", PLY, ids=PLY_IDS)
def test_roundtrip_preserves_every_meaningful_byte(path):
    """Reading and writing back reproduces the file exactly, except where the
    original wrote uninitialised memory: PermStr is NUL-terminated and DOS left
    whatever happened to be in the padding (only pg24.ply still has such junk).
    """
    original = path.read_bytes()
    written = _rewrite(path)
    assert len(written) == len(original)

    for i, (a, b) in enumerate(zip(original, written)):
        if a == b:
            continue
        assert _is_permstr_padding(i, original), \
            f"{path.name}: byte {i} differs outside string padding ({a} != {b})"


@pytest.mark.parametrize("path", PLY, ids=PLY_IDS)
def test_relaxed_positions_and_dimension_survive_the_load(path):
    """A .ply is a session, not a topology: the coordinates are the ones the
    1995 relaxation had settled on, and every saved object had already fallen
    from 8-D to 3-D."""
    g = read_ply(path).graph
    assert g.dimensions == 3
    assert any(any(nd.pos[:3]) for nd in g.ordered())
    # 'old' is the previous iteration's copy, so it must be populated too
    assert any(any(nd.old[:3]) for nd in g.ordered())


def test_session_roundtrip_keeps_program_and_iridium_state(tmp_path):
    """State the original stored but our loader could easily drop: SPA/ParSum
    fields, broken-link bitset, and the Iridium record."""
    g = Graph()
    g.nnodes = 2
    g.dimensions = 3
    for n in (1, 2):
        nd = Node(num=n, perm=f"12{n}", color=n + 1,
                  links=[Link(to=3 - n, op=2, status=2, broken=True)],
                  pos=[n, -n, 7, 0, 0, 0, 0, 0], old=[1, 2, 3, 0, 0, 0, 0, 0])
        nd.state.dead = n == 2
        nd.state.active = n == 1
        nd.state.display, nd.state.step, nd.state.sum = -5, 3, 9
        nd.iri.avail, nd.iri.target = 10000, 3 - n
        nd.iri.message_num, nd.iri.sender_repeat = 42, 7
        g.nodes[n] = nd

    path = tmp_path / "session.ply"
    write_ply(path, PlySession(graph=g, permuto=True, base="1234",
                               optable=[["12", "", ""]] + [["", "", ""]] * 5,
                               last_edit_line=4))
    back = read_ply(path)

    assert (back.permuto, back.base, back.last_edit_line) == (True, "1234", 4)
    assert back.optable[0][0] == "12"
    for n in (1, 2):
        a, b = g.nodes[n], back.graph.nodes[n]
        assert (a.pos, a.old, a.color, a.perm) == (b.pos, b.old, b.color, b.perm)
        assert a.links == b.links
        assert a.state == b.state
        assert a.iri == b.iri


def test_negative_coordinates_survive():
    """pos is INTEGER, not CARDINAL -- reading it unsigned would wrap the half
    of every relaxed object that sits left of or below the centre."""
    g = read_ply(PLY[0]).graph
    assert any(c < 0 for nd in g.ordered() for c in nd.pos[:3])


# --- validation: LoadPoly checked nothing at all -----------------------

def _valid_bytes():
    return read_ply(PLY[0]).graph, PLY[0].read_bytes()


@pytest.mark.parametrize("mangle,expect", [
    (lambda d: d[:100], "shorter than"),
    (lambda d: d + b"\x00" * 40, "not a whole number"),
    (lambda d: d[:176] + struct.pack("<h", 99) + d[178:], "header says 99"),
    (lambda d: d[:174] + struct.pack("<H", 0) + d[176:], "outside 1..8"),
    (lambda d: d[:174] + struct.pack("<H", 9) + d[176:], "outside 1..8"),
    (lambda d: d[:HEADER_SIZE + 36] + struct.pack("<H", 13)
               + d[HEADER_SIZE + 38:], "maximum is 12"),
])
def test_damaged_files_are_reported_not_silently_accepted(tmp_path, mangle, expect):
    path = tmp_path / "damaged.ply"
    path.write_bytes(mangle(PLY[0].read_bytes()))
    with pytest.raises(FileFormatError) as exc:
        read_ply(path)
    assert expect in str(exc.value)


def test_link_pointing_outside_the_graph_is_reported(tmp_path):
    data = bytearray(PLY[0].read_bytes())
    nnodes = struct.unpack_from("<h", data, 176)[0]
    struct.pack_into("<H", data, HEADER_SIZE + 38, nnodes + 5)   # links[1]
    path = tmp_path / "badlink.ply"
    path.write_bytes(bytes(data))
    with pytest.raises(FileFormatError) as exc:
        read_ply(path)
    assert f"outside 1..{nnodes}" in str(exc.value)


# --- helpers -----------------------------------------------------------

def _rewrite(path) -> bytes:
    import tempfile
    from pathlib import Path

    out = Path(tempfile.mkdtemp()) / "out.ply"
    write_ply(out, read_ply(path))
    return out.read_bytes()


def _is_permstr_padding(offset: int, data: bytes) -> bool:
    """True if *offset* lies after the NUL of one of the file's PermStr fields.

    PermStr is ARRAY[0..8] OF CHAR; the original never cleared the tail.
    """
    if offset < HEADER_SIZE:
        starts = [1] + [10 + i * 9 for i in range(18)]     # base + 6x3 optable
        if offset >= 172:
            return False
    else:
        rec = HEADER_SIZE + (offset - HEADER_SIZE) // RECORD_SIZE * RECORD_SIZE
        starts = [rec + 114]                               # perm
    for s in starts:
        if s <= offset < s + 9:
            return b"\x00" in data[s:offset + 1]
    return False
