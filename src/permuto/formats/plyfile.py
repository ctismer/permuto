"""The ``.ply`` binary session format (``NodeMgr.LoadPoly`` / ``SavePoly``).

Unlike ``.nod``, which is only a topology, this is the *whole session*: the
mode flag, the base permutation, the operator table, the editor's cursor line,
the current dimension count and every node record including its position, its
program state and its Iridium fields.  Dated ``(19.09.95)`` in the original --
the last thing added to the program before it was abandoned.

Layout, verified byte-for-byte against all eight surviving files (``cube``,
``ikosa1``, ``ikosa2``, ``kubokt``, ``okt1``, ``okt2``, ``okt3``, ``pg24``)::

    header, 178 bytes
      0    Permuto        BOOLEAN     1
      1    BasePerm       PermStr     9   (NUL-terminated, trailing junk)
      10   OpTable        6 x 3 x 9   162
      172  LastEditLine   CARDINAL    2
      174  Dimensions     CARDINAL    2
      176  nnodes         INTEGER     2

    node record, 123 bytes, little-endian, no padding
      0    pos[1..8]      INTEGER     16
      16   old[1..8]      INTEGER     16
      32   color          CARDINAL    2
      34   num            CARDINAL    2
      36   nlink          CARDINAL    2
      38   links[1..12]   CARDINAL    24
      62   opno[1..12]    SHORTCARD   12
      74   state.dead     BOOLEAN     1
      75   state.active   BOOLEAN     1
      76   state.display  INTEGER     2
      78   state.step     INTEGER     2
      80   state.sum      CARDINAL    2
      82   state.lines    12 x enum   12
      94   state.broken   BITSET      2
      96   iri.avail/avbak/target/tarbak   8
      104  iri.message.num/.color          4
      108  iri.sender.repeat/.target/.color 6
      114  perm           PermStr     9

``LoadPoly`` read this with no validation whatsoever -- no magic number, no
length check -- so any wrong file produced garbage nodes rather than an error.
Since there is no magic number to add without breaking compatibility, we check
what the structure itself implies: the size must be exactly ``178 + n*123``,
and the header fields must be within their declared ranges.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..errors import FileFormatError, InvalidBase, InvalidCycle
from ..core import intvector as iv
from ..core.graph import Graph, IriState, Node, NodeState
from ..core.pm import MAX_CYC, MAX_LINKS, MAX_OPS, PM

HEADER_SIZE = 178
RECORD_SIZE = 123
PERMSTR_SIZE = 9

_MAX_NNODES = 2000  # NodeMgr.MaxNodesTot


def _read_permstr(raw: bytes) -> str:
    """A ``PermStr`` is NUL-terminated; whatever follows is uninitialised."""
    return raw.split(b"\x00", 1)[0].decode("latin-1")


def _write_permstr(s: str) -> bytes:
    raw = s.encode("latin-1")
    if len(raw) >= PERMSTR_SIZE:
        raise FileFormatError("<save>", f"{s!r} does not fit a PermStr")
    return raw + b"\x00" * (PERMSTR_SIZE - len(raw))


@dataclass
class PlySession:
    """Everything a ``.ply`` holds: the graph plus how it was made."""

    graph: Graph
    permuto: bool = True
    base: str = ""
    optable: List[List[str]] = field(default_factory=list)
    last_edit_line: int = 0
    pm: Optional[PM] = None
    """The reconstructed PM, or None when the base/operators are unusable
    (a Polytop-mode session carries a leftover table that need not be valid)."""


# --- reading -----------------------------------------------------------

def read_ply(path) -> PlySession:
    data = Path(path).read_bytes()
    if len(data) < HEADER_SIZE:
        raise FileFormatError(
            path, f"file is {len(data)} bytes, shorter than the {HEADER_SIZE}-byte header"
        )
    body = len(data) - HEADER_SIZE
    if body % RECORD_SIZE:
        raise FileFormatError(
            path,
            f"{body} bytes of node data is not a whole number of "
            f"{RECORD_SIZE}-byte records",
        )
    by_size = body // RECORD_SIZE

    permuto = data[0] != 0
    base = _read_permstr(data[1:10])
    optable = [
        [_read_permstr(data[10 + (i * MAX_CYC + j) * PERMSTR_SIZE:][:PERMSTR_SIZE])
         for j in range(MAX_CYC)]
        for i in range(MAX_OPS)
    ]
    last_edit_line, dimensions, nnodes = struct.unpack_from("<HHh", data, 172)

    if nnodes != by_size:
        raise FileFormatError(
            path,
            f"header says {nnodes} nodes but the file holds {by_size}",
            where=f"offset 176",
        )
    if not 0 <= nnodes <= _MAX_NNODES:
        raise FileFormatError(path, f"implausible node count {nnodes}", where="offset 176")
    if not 1 <= dimensions <= iv.MAXDIMEN:
        raise FileFormatError(
            path, f"dimensions is {dimensions}, outside 1..{iv.MAXDIMEN}",
            where="offset 174",
        )

    g = Graph()
    g.nnodes = nnodes
    g.dimensions = dimensions
    for i in range(nnodes):
        nd = _read_record(path, data, HEADER_SIZE + i * RECORD_SIZE, nnodes)
        g.nodes[nd.num if nd.num else i + 1] = nd
    g.set_dimensions(dimensions)
    g.n_operators = sum(1 for row in optable if any(row))

    # LoadPoly rebuilds the graph from base + operators before overwriting it
    # with the records, which is what leaves PM.Order and the perm cache
    # consistent.  We do the same, but keep going when the table is unusable.
    pm = None
    try:
        pm = PM(base=base, optable=[list(row) for row in optable])
    except (InvalidBase, InvalidCycle):
        pm = None

    return PlySession(graph=g, permuto=permuto, base=base, optable=optable,
                      last_edit_line=last_edit_line, pm=pm)


def _read_record(path, data: bytes, off: int, nnodes: int) -> Node:
    pos = list(struct.unpack_from("<8h", data, off))
    old = list(struct.unpack_from("<8h", data, off + 16))
    color, num, nlink = struct.unpack_from("<HHH", data, off + 32)
    links = list(struct.unpack_from("<12H", data, off + 38))
    opno = list(struct.unpack_from("<12B", data, off + 62))
    dead, active = data[off + 74] != 0, data[off + 75] != 0
    display, step, ssum = struct.unpack_from("<hhH", data, off + 76)
    lines = list(struct.unpack_from("<12B", data, off + 82))
    broken_bits, = struct.unpack_from("<H", data, off + 94)
    avail, avbak, target, tarbak = struct.unpack_from("<4H", data, off + 96)
    msg_num, msg_color = struct.unpack_from("<2H", data, off + 104)
    snd_repeat, snd_target, snd_color = struct.unpack_from("<3H", data, off + 108)
    perm = _read_permstr(data[off + 114:off + 114 + PERMSTR_SIZE])

    if nlink > MAX_LINKS:
        raise FileFormatError(
            path, f"node {num} claims {nlink} links, the maximum is {MAX_LINKS}",
            where=f"offset {off + 36}",
        )
    for j in links[:nlink]:
        if not 1 <= j <= nnodes:
            raise FileFormatError(
                path, f"node {num} links to {j}, outside 1..{nnodes}",
                where=f"offset {off + 38}",
            )

    state = NodeState(
        step=step, active=active, dead=dead, sum=ssum, display=display,
        # BITSET over 1-based link indices; bit 0 is unused
        broken={j for j in range(1, MAX_LINKS + 1) if broken_bits & (1 << j)},
        lines=lines[:nlink],
    )
    iri = IriState(avail=avail, avbak=avbak, target=target, tarbak=tarbak,
                   message_num=msg_num, message_color=msg_color,
                   sender_repeat=snd_repeat, sender_target=snd_target,
                   sender_color=snd_color)
    return Node(num=num, pos=pos, old=old, color=color, nlink=nlink,
                links=links[:nlink], opno=opno[:nlink], perm=perm,
                state=state, iri=iri)


# --- writing -----------------------------------------------------------

def write_ply(path, session: PlySession) -> None:
    g = session.graph
    optable = session.optable or [["" for _ in range(MAX_CYC)] for _ in range(MAX_OPS)]

    out = bytearray()
    out += b"\x01" if session.permuto else b"\x00"
    out += _write_permstr(session.base)
    for i in range(MAX_OPS):
        for j in range(MAX_CYC):
            out += _write_permstr(optable[i][j] if i < len(optable) else "")
    out += struct.pack("<HHh", session.last_edit_line, g.dimensions, g.nnodes)
    assert len(out) == HEADER_SIZE

    for nd in g.ordered():
        out += _write_record(nd)
    Path(path).write_bytes(bytes(out))


_I16_MIN, _I16_MAX = -0x8000, 0x7FFF


def _write_record(nd: Node) -> bytes:
    def padded(seq, size, fill=0):
        return list(seq)[:size] + [fill] * max(0, size - len(seq))

    def coords(seq, what):
        """The file format is 16-bit even though the port computes in 32.

        Normalize keeps coordinates within +-NORM, so this only bites for
        un-relaxed seed layouts -- worth a clear message rather than a
        struct.error from six frames down.
        """
        out = padded(seq, 8)
        for value in out:
            if not _I16_MIN <= value <= _I16_MAX:
                raise FileFormatError(
                    "<save>",
                    f"{what} {value} of node {nd.num} does not fit the format's "
                    f"16-bit INTEGER; relax the graph before saving",
                )
        return out

    st, iri = nd.state, nd.iri
    broken_bits = 0
    for b in st.broken:
        if 0 <= b <= 15:
            broken_bits |= 1 << b

    rec = bytearray()
    rec += struct.pack("<8h", *coords(nd.pos, "coordinate"))
    rec += struct.pack("<8h", *coords(nd.old, "previous coordinate"))
    rec += struct.pack("<HHH", nd.color, nd.num, nd.nlink)
    rec += struct.pack("<12H", *padded(nd.links, MAX_LINKS))
    rec += struct.pack("<12B", *padded(nd.opno, MAX_LINKS))
    rec += bytes((1 if st.dead else 0, 1 if st.active else 0))
    rec += struct.pack("<hhH", st.display, st.step, st.sum)
    rec += struct.pack("<12B", *padded(st.lines, MAX_LINKS))
    rec += struct.pack("<H", broken_bits)
    rec += struct.pack("<4H", iri.avail, iri.avbak, iri.target, iri.tarbak)
    rec += struct.pack("<2H", iri.message_num, iri.message_color)
    rec += struct.pack("<3H", iri.sender_repeat, iri.sender_target, iri.sender_color)
    rec += _write_permstr(nd.perm)
    assert len(rec) == RECORD_SIZE
    return bytes(rec)
