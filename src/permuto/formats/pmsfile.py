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
    out.append(f"iter {session.iteration}")
    out.append(f"dim {dim}")
    out.append(f"nodes {g.nnodes}")
    for nd in g.ordered():
        out.append(_node_line(nd, dim))
    out.append("end")   # a trailer, so any truncation is detectable on read
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


# --- reading -----------------------------------------------------------

def _parse_int_list(path, lineno, text) -> List[int]:
    try:
        return [int(v) for v in text.split(",") if v != ""]
    except ValueError:
        raise FileFormatError(path, f"expected integers, got {text!r}",
                              where=f"line {lineno}")


def _parse_node(path, lineno, tokens, dim, warn, salvage) -> Node:
    """Parse one node line.

    Strict by default: any malformed field is a :class:`FileFormatError`.  Only
    when *salvage* is set -- the final line of a file that was cut off before its
    ``end`` marker -- is the line treated as a truncated tail: fields lost off
    the end default to zero and are noted via *warn* instead of rejected, since
    the coordinates re-derive from the relaxation.
    """
    nd = Node(num=int(tokens[0]))
    have_pos = False
    for tok in tokens[1:]:
        if "=" not in tok:
            if not salvage:
                raise FileFormatError(path, f"expected key=value, got {tok!r}",
                                      where=f"line {lineno}")
            warn(f"line {lineno}: node {nd.num} cut at {tok!r}")
            break
        key, val = tok.split("=", 1)
        if key == "perm":
            nd.perm = val
        elif key == "color":
            nd.color = int(val)
        elif key == "pos":
            nd.pos = _coords(path, lineno, "pos", val, dim, nd.num, warn, salvage)
            have_pos = True
        elif key == "old":
            nd.old = _coords(path, lineno, "old", val, dim, nd.num, warn, salvage)
        elif key == "links":
            for pair in val.split(","):
                if not pair:
                    continue
                j, sep, op = pair.partition(":")
                if not j.lstrip("-").isdigit() or (sep and not op.isdigit()):
                    if not salvage:
                        raise FileFormatError(path, f"bad link {pair!r}",
                                              where=f"line {lineno}")
                    warn(f"line {lineno}: node {nd.num} link cut at {pair!r}")
                    break
                nd.links.append(int(j))
                if sep:
                    nd.opno.append(int(op))
        elif key == "state":
            _parse_state(nd.state, val)
        elif key == "iri":
            _parse_iri(nd.iri, val)
        else:
            raise FileFormatError(path, f"unknown node field {key!r}",
                                  where=f"line {lineno}")
    if not have_pos:
        if not salvage:
            raise FileFormatError(path, f"node {nd.num} has no pos",
                                  where=f"line {lineno}")
        warn(f"line {lineno}: node {nd.num} has no pos, set to 0")
    nd.nlink = len(nd.links)
    return nd


def _coords(path, lineno, field, text, dim, num, warn, salvage) -> List[int]:
    """Exactly *dim* coordinates; a short count is a truncation only in the
    salvage tail, otherwise a hard error."""
    coords = [int(v) for v in text.split(",") if v.lstrip("-").isdigit()]
    if len(coords) != dim:
        if not salvage:
            raise FileFormatError(
                path, f"{field} has {len(coords)} coordinates, expected dim={dim}",
                where=f"line {lineno}")
        warn(f"line {lineno}: node {num} {field} has {len(coords)} of {dim} "
             f"coordinates, zero-filled")
    return (coords + [0] * iv.MAXDIMEN)[:iv.MAXDIMEN]


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
    """Read a ``.pms`` session, salvaging a truncated file rather than rejecting.

    A cut file loses lines and fields off the end.  We load everything readable,
    zero-fill what is missing (coordinates re-derive from the relaxation anyway)
    and return the problems as ``PlySession.warnings`` for the UI to show.  Only
    two things are fatal: it is not a ``.pms`` at all, or its dimension is
    unusable.
    """
    text = Path(path).read_text(encoding="utf-8")
    warnings: List[str] = []
    mode = "permuto"
    base = ""
    optable = [["" for _ in range(MAX_CYC)] for _ in range(MAX_OPS)]
    last_edit_line = 0
    iteration = 0
    dim = 3
    declared_nodes = None
    g = Graph()

    # meaningful (non-blank, non-comment) lines with their 1-based numbers
    body = [(i, ln.strip()) for i, ln in enumerate(text.splitlines(), start=1)
            if ln.strip() and not ln.strip().startswith("%")]
    if not body or not body[0][1].startswith(MAGIC):
        raise FileFormatError(path, f"not a {MAGIC!r} file", where="line 1")

    # A well-terminated file ends with the 'end' marker.  If it does not, it was
    # cut off, and *only* its final line may be an incomplete tail -- everything
    # before it must still be perfectly valid, and everything else is an error.
    truncated = body[-1][1].split(" ", 1)[0] != "end"
    if truncated:
        warnings.append("no 'end' marker: the file was cut off; "
                        "loaded what was readable")

    for idx, (lineno, line) in enumerate(body[1:], start=1):
        head, _, rest = line.partition(" ")
        rest = rest.strip()
        salvage = truncated and idx == len(body) - 1   # only the final line
        try:
            if head == "mode":
                mode = rest
            elif head == "base":
                base = rest
            elif head == "op":
                i = int(rest.split(" ", 1)[0])
                for j, cyc in enumerate(rest.split()[1:]):
                    if 1 <= i <= MAX_OPS and j < MAX_CYC:
                        optable[i - 1][j] = cyc
            elif head == "lastedit":
                last_edit_line = int(rest)
            elif head == "iter":
                iteration = int(rest)
            elif head == "dim":
                dim = int(rest)
            elif head == "nodes":
                declared_nodes = int(rest)
            elif head == "node":
                nd = _parse_node(path, lineno, rest.split(), dim,
                                 warnings.append, salvage)
                g.nodes[nd.num] = nd
            elif head == "end":
                pass
            else:
                raise FileFormatError(path, f"unknown key {head!r}",
                                      where=f"line {lineno}")
        except (ValueError, FileFormatError) as exc:
            if not salvage:
                if isinstance(exc, FileFormatError):
                    raise
                raise FileFormatError(path, f"could not parse: {exc}",
                                      where=f"line {lineno}") from exc
            warnings.append(f"line {lineno}: cut short, stopped here")

    if not 1 <= dim <= iv.MAXDIMEN:
        raise FileFormatError(path, f"dim {dim} is outside 1..{iv.MAXDIMEN}")
    g.nnodes = len(g.nodes)
    g.dimensions = dim
    g.n_operators = sum(1 for row in optable if any(row))

    # count and link consistency: a warning when truncated (nodes were lost off
    # the end), a hard error in a file that claims to be complete.
    if declared_nodes is not None and declared_nodes != g.nnodes:
        msg = f"expected {declared_nodes} nodes, recovered {g.nnodes}"
        if truncated:
            warnings.append(msg)
        else:
            raise FileFormatError(path, f"header says {declared_nodes} nodes "
                                  f"but {g.nnodes} were read")
    _resolve_links(path, g, warnings, truncated)

    pm = None
    if base:
        from ..errors import InvalidBase, InvalidCycle
        try:
            pm = PM(base=base, optable=[list(r) for r in optable])
        except (InvalidBase, InvalidCycle) as exc:
            if not truncated:
                raise FileFormatError(path, f"unusable operators: {exc}")
            warnings.append(f"operators unusable, editor disabled: {exc}")

    return PlySession(graph=g, permuto=(mode == "permuto"), base=base,
                      optable=optable, last_edit_line=last_edit_line,
                      iteration=iteration, pm=pm, mode=mode, warnings=warnings)


def _resolve_links(path, g: Graph, warnings: List[str], truncated: bool) -> None:
    """Links to a missing node are a truncation artefact (its line was cut away)
    -- dropped with a warning; in a complete file they are corruption -- fatal."""
    for nd in g.nodes.values():
        opno = list(nd.opno) + [0] * (len(nd.links) - len(nd.opno))
        kept = [(j, op) for j, op in zip(nd.links, opno) if j in g.nodes]
        if len(kept) != len(nd.links):
            if not truncated:
                bad = next(j for j in nd.links if j not in g.nodes)
                raise FileFormatError(
                    path, f"node {nd.num} links to {bad}, which does not exist")
            warnings.append(f"node {nd.num}: dropped {len(nd.links) - len(kept)} "
                            f"link(s) to missing node(s)")
            nd.links = [j for j, _ in kept]
            nd.opno = [op for _, op in kept] if nd.opno else []
        nd.nlink = len(nd.links)
