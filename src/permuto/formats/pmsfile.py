"""The ``.pms`` text session format -- the modern replacement for binary ``.ply``.

A permuto session is really just a graph plus how it was made, and its essence
is the **coordinates**: the relaxed positions that take hundreds of iterations
to settle and that the (source-less) random seed cannot reproduce.  Everything
else is either regenerable (base + operators rebuild the topology) or trimming.

``.ply`` stored all this as a raw 16-bit memory dump -- no validation, DOS junk
in the padding, undiffable, and a hard coordinate ceiling.  ``.pms`` keeps the
same information as line-oriented text, in the family of ``.nod`` / ``.pgd`` /
``.pg`` (which are all text too): a small ``key value`` header, then one line
per node.  It is diffable, hand-repairable, greppable, needs no library, takes
``%`` comments, and -- because every coordinate is already an integer
(fixed-point, ``NORM = 4096`` is "1.0") -- text loses nothing that binary kept,
while dropping the 16-bit limit entirely.

Format (version 1)::

    permuto session 1
    % any % line is a comment
    mode permuto            ; permuto | polytop | iridium
    base 1234               ; omitted in polytop/iridium mode
    op 1 12                 ; operator i, its cycles space-separated
    op 3 18 27              ; several cycles = a product (the cube's operators)
    lastedit 4
    dim 3
    nodes 24
    node 1 perm=1234 color=1 pos=-744,-1247,3810 links=7:1,3:2,2:3
    node 2 perm=2134 color=1 pos=... old=... state=display:2 iri=avail:10000

Node fields, all optional except ``pos``:

* ``perm`` / ``color`` -- label and DOS colour index
* ``pos`` / ``old`` -- the ``dim`` coordinates (``old`` = previous iteration)
* ``links`` -- ``neighbour:operator`` pairs (operator ``0`` if unknown)
* ``state`` -- SPA/ParSum fields, written only when set
  (``dead active display:N step:N sum:N broken:i|j lines:a,b,c``)
* ``iri`` -- the Iridium satellite state, written only when present

The whole session state is writable, deliberately: flexibility costs nothing
here and it is an extension anyway.  The original could not even save in ``/I``
mode; ``.pms`` can.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..errors import FileFormatError
from ..core import intvector as iv
from ..core.graph import Graph, IriState, Node, NodeState
from ..core.pm import MAX_CYC, MAX_OPS, PM
from .plyfile import PlySession

MAGIC = "permuto session"
VERSION = 1


# --- writing -----------------------------------------------------------

def _ints(values) -> str:
    return ",".join(str(v) for v in values)


def _node_line(nd: Node, dim: int) -> str:
    parts = [f"node {nd.num}"]
    if nd.perm:
        parts.append(f"perm={nd.perm}")
    parts.append(f"color={nd.color}")
    parts.append(f"pos={_ints(nd.pos[:dim])}")
    if any(nd.old[:dim]):
        parts.append(f"old={_ints(nd.old[:dim])}")
    if nd.links:
        if any(nd.opno):     # permuto edges carry an operator number
            opno = list(nd.opno) + [0] * (len(nd.links) - len(nd.opno))
            parts.append("links=" + ",".join(f"{j}:{op}"
                                              for j, op in zip(nd.links, opno)))
        else:                # iridium / .nod edges have none -- write bare
            parts.append("links=" + _ints(nd.links))
    state = _state_field(nd.state, nd.nlink)
    if state:
        parts.append("state=" + state)
    iri = _iri_field(nd.iri)
    if iri:
        parts.append("iri=" + iri)
    return " ".join(parts)


def _state_field(st: NodeState, nlink: int) -> str:
    items = []
    if st.dead:
        items.append("dead")
    if st.active:
        items.append("active")
    for name, value in (("display", st.display), ("step", st.step),
                        ("sum", st.sum)):
        if value:
            items.append(f"{name}:{value}")
    if st.broken:
        items.append("broken:" + "|".join(str(b) for b in sorted(st.broken)))
    if any(st.lines[:nlink]):
        items.append("lines:" + _ints(st.lines[:nlink]))
    return ",".join(items)


def _iri_field(iri: IriState) -> str:
    fields = [("avail", iri.avail), ("avbak", iri.avbak),
              ("target", iri.target), ("tarbak", iri.tarbak),
              ("msg", iri.message_num), ("msgcolor", iri.message_color),
              ("srepeat", iri.sender_repeat), ("starget", iri.sender_target),
              ("scolor", iri.sender_color)]
    items = [f"{name}:{value}" for name, value in fields if value]
    return ",".join(items)


def write_pms(path, session: PlySession) -> None:
    g = session.graph
    dim = g.dimensions
    out = [f"{MAGIC} {VERSION}",
           f"mode {session.mode}"]
    if session.mode == "permuto" and session.base:
        out.append(f"base {session.base}")
        for i in range(MAX_OPS):
            row = session.optable[i] if i < len(session.optable) else []
            cycles = [c for c in row if c]
            if cycles:
                out.append(f"op {i + 1} " + " ".join(cycles))
        out.append(f"lastedit {session.last_edit_line}")
    out.append(f"dim {dim}")
    out.append(f"nodes {g.nnodes}")
    for nd in g.ordered():
        out.append(_node_line(nd, dim))
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


# --- reading -----------------------------------------------------------

def _parse_int_list(path, lineno, text) -> List[int]:
    try:
        return [int(v) for v in text.split(",") if v != ""]
    except ValueError:
        raise FileFormatError(path, f"expected integers, got {text!r}",
                              where=f"line {lineno}")


def _parse_node(path, lineno, tokens, dim) -> Node:
    num = int(tokens[0])
    nd = Node(num=num)
    for tok in tokens[1:]:
        if "=" not in tok:
            raise FileFormatError(path, f"expected key=value, got {tok!r}",
                                  where=f"line {lineno}")
        key, val = tok.split("=", 1)
        if key == "perm":
            nd.perm = val
        elif key == "color":
            nd.color = int(val)
        elif key == "pos":
            coords = _parse_int_list(path, lineno, val)
            nd.pos = (coords + [0] * iv.MAXDIMEN)[:iv.MAXDIMEN]
        elif key == "old":
            coords = _parse_int_list(path, lineno, val)
            nd.old = (coords + [0] * iv.MAXDIMEN)[:iv.MAXDIMEN]
        elif key == "links":
            for pair in val.split(","):
                if not pair:
                    continue
                j, sep, op = pair.partition(":")
                nd.links.append(int(j))
                if sep:      # only carry opno when the edge actually names one
                    nd.opno.append(int(op))
        elif key == "state":
            _parse_state(nd.state, val)
        elif key == "iri":
            _parse_iri(nd.iri, val)
        else:
            raise FileFormatError(path, f"unknown node field {key!r}",
                                  where=f"line {lineno}")
    nd.nlink = len(nd.links)
    return nd


def _parse_state(st: NodeState, val) -> None:
    for item in val.split(","):
        if not item:
            continue
        key, _, num = item.partition(":")
        if key == "dead":
            st.dead = True
        elif key == "active":
            st.active = True
        elif key == "display":
            st.display = int(num)
        elif key == "step":
            st.step = int(num)
        elif key == "sum":
            st.sum = int(num)
        elif key == "broken":
            st.broken = {int(b) for b in num.split("|") if b}
        elif key == "lines":
            st.lines = [int(x) for x in num.split(",") if x]


_IRI_KEYS = {
    "avail": "avail", "avbak": "avbak", "target": "target", "tarbak": "tarbak",
    "msg": "message_num", "msgcolor": "message_color",
    "srepeat": "sender_repeat", "starget": "sender_target", "scolor": "sender_color",
}


def _parse_iri(iri: IriState, val) -> None:
    for item in val.split(","):
        if not item:
            continue
        key, _, num = item.partition(":")
        attr = _IRI_KEYS.get(key)
        if attr:
            setattr(iri, attr, int(num))


def read_pms(path) -> PlySession:
    text = Path(path).read_text(encoding="utf-8")
    mode = "permuto"
    base = ""
    optable = [["" for _ in range(MAX_CYC)] for _ in range(MAX_OPS)]
    last_edit_line = 0
    dim = 3
    declared_nodes = None
    g = Graph()
    seen_magic = False

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        head, _, rest = line.partition(" ")
        rest = rest.strip()
        if not seen_magic:
            if line.startswith(MAGIC):
                seen_magic = True
                continue
            raise FileFormatError(path, f"not a {MAGIC!r} file (line 1 is {line!r})",
                                  where="line 1")
        if head == "mode":
            mode = rest
        elif head == "base":
            base = rest
        elif head == "op":
            idx, _, cycles = rest.partition(" ")
            i = int(idx)
            for j, cyc in enumerate(cycles.split()):
                if 1 <= i <= MAX_OPS and j < MAX_CYC:
                    optable[i - 1][j] = cyc
        elif head == "lastedit":
            last_edit_line = int(rest)
        elif head == "dim":
            dim = int(rest)
        elif head == "nodes":
            declared_nodes = int(rest)
        elif head == "node":
            nd = _parse_node(path, lineno, rest.split(), dim)
            g.nodes[nd.num] = nd
        else:
            raise FileFormatError(path, f"unknown key {head!r}",
                                  where=f"line {lineno}")

    if not seen_magic:
        raise FileFormatError(path, "empty file", where="line 1")
    g.nnodes = len(g.nodes)
    if declared_nodes is not None and declared_nodes != g.nnodes:
        raise FileFormatError(
            path, f"header says {declared_nodes} nodes but {g.nnodes} were read")
    if not 1 <= dim <= iv.MAXDIMEN:
        raise FileFormatError(path, f"dim {dim} is outside 1..{iv.MAXDIMEN}")
    g.dimensions = dim
    g.n_operators = sum(1 for row in optable if any(row))
    _check_links(path, g)

    pm = None
    if base:
        from ..errors import InvalidBase, InvalidCycle
        try:
            pm = PM(base=base, optable=[list(r) for r in optable])
        except (InvalidBase, InvalidCycle):
            pm = None

    return PlySession(graph=g, permuto=(mode == "permuto"), base=base,
                      optable=optable, last_edit_line=last_edit_line, pm=pm,
                      mode=mode)


def _check_links(path, g: Graph) -> None:
    for nd in g.nodes.values():
        for j in nd.links:
            if j not in g.nodes:
                raise FileFormatError(
                    path, f"node {nd.num} links to {j}, which does not exist")
