"""Faithful port of ``PCalc`` (pcalc.def / pcalc.mod): the integer
fixed-point force-directed layout, plus ``spin`` and dimension shrinking.

All arithmetic mirrors the original (via :mod:`permuto.core.intvector`).
Component indices are translated from the Modula 1-based convention to
Python 0-based (e.g. Spin's ``pos[1]``/``pos[3]`` -> ``pos[0]``/``pos[2]``).

The main-loop cadence follows ``polytop.mod``::

    Backup -> Contract(alg) -> Squeeze -> [Punish if Rubber]
           -> [Spin if dim>=3] -> Normalize -> while CanShrink: dim -= 1
"""

from __future__ import annotations

from enum import Enum

from . import intvector as iv

class Algorithm(Enum):
    """``PCalc``'s five relaxation algorithms, in the order ``A`` cycles them.

    Each carries the name the status line prints, padded exactly as
    ``PCalc.AlgNames`` printed it -- one list instead of a tuple here and a
    lookup table in the session that had to agree with it.
    """

    label: str          # what the status line prints, padded as PCalc did

    def __new__(cls, value: str, label: str):
        # __new__, not __init__: only this way does Algorithm("rubber") find
        # the member, so a plain name still works wherever one is handier
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    RUBBER = ("rubber", "Rubber ")
    RUBBER2 = ("rubber2", "Rubber2")
    RIBBON = ("ribbon", "Ribbon ")
    MEAN = ("mean", "Mean   ")
    NEW = ("new", "New    ")


#: in cycling order, for the ``A`` key
ALGORITHMS = tuple(Algorithm)


def as_algorithm(alg: "Algorithm | str") -> Algorithm:
    """Either spelling in, an :class:`Algorithm` out; anything else raises.

    Written out rather than as ``Algorithm(alg)``, which a type checker reads
    as a call to the two-argument ``__new__`` -- and this way the refusal says
    what the choices are instead of "is not a valid Algorithm".
    """
    if isinstance(alg, Algorithm):
        return alg
    for member in Algorithm:
        if member.value == alg:
            return member
    raise ValueError(f"no such relaxation algorithm: {alg!r} "
                     f"(have {', '.join(a.value for a in Algorithm)})")


def backup(g) -> None:
    """Copy ``pos`` into ``old`` (so Contract reads a stable snapshot)."""
    for nd in g.nodes.values():
        nd.old = list(nd.pos)


def _mean_edge_length(g) -> int:
    """The average edge length, which only ``New`` needs."""
    lsum = lcount = 0
    for nd in g.ordered():
        for link in nd.links:
            tmp = list(g.nodes[link.to].old)
            iv.sub_vector(tmp, nd.pos)
            lsum += iv.vector_length(tmp)
            lcount += 1
    return lsum // lcount if lcount else 0


def _rubber(g, nd, nlink, mean) -> None:
    """Pull toward the neighbours, all edges equally."""
    vec = iv.new_vector()
    for link in nd.links:
        tmp = list(g.nodes[link.to].old)
        iv.sub_vector(tmp, nd.pos)
        iv.add_vector(vec, tmp)
    iv.scale_vector(vec, 1, 3 * nlink)
    iv.add_vector(nd.pos, vec)


def _rubber2(g, nd, nlink, mean) -> None:
    """As Rubber, but each pull weighted by its own length."""
    vec = iv.new_vector()
    for link in nd.links:
        tmp = list(g.nodes[link.to].old)
        iv.sub_vector(tmp, nd.pos)
        length = iv.vector_length(tmp)
        iv.scale_vector(tmp, length, nlink * iv.NORM)
        iv.add_vector(vec, tmp)
    iv.scale_vector(vec, 1, 3 * nlink)
    iv.add_vector(nd.pos, vec)


def _ribbon(g, nd, nlink, mean) -> None:
    """Move along the longest edge only, by how much it exceeds the shortest."""
    vec = iv.new_vector()
    mx, mn = 1, 1 << 30
    for link in nd.links:
        cmp = list(g.nodes[link.to].old)
        iv.sub_vector(cmp, nd.pos)
        length = iv.vector_length(cmp)
        if length > mx:
            mx = length
            vec = list(cmp)
        if length < mn:
            mn = length
    iv.scale_vector(vec, (mx - mn) // 100, mx)
    iv.add_vector(nd.pos, vec)


def _mean(g, nd, nlink, mean) -> None:
    """Add the neighbours outright -- Normalize scales the result back."""
    for link in nd.links:
        iv.add_vector(nd.pos, g.nodes[link.to].old)


def _new(g, nd, nlink, mean) -> None:
    """Gather gently, then contract the over-long edges -- twice."""
    vec = iv.new_vector()
    for link in nd.links:
        iv.add_vector(vec, g.nodes[link.to].old)
    iv.scale_vector(vec, 1, 20 * nlink)
    iv.add_vector(nd.pos, vec)
    for _ in range(2):  # "nochmal!" -- contract long edges twice
        for link in nd.links:
            tmp = list(g.nodes[link.to].old)
            iv.sub_vector(tmp, nd.pos)
            length = iv.vector_length(tmp)
            if length > mean:
                iv.scale_vector(tmp, (length - mean) // nlink, 2 * length)
                iv.add_vector(nd.pos, tmp)


_CONTRACTIONS = {Algorithm.RUBBER: _rubber, Algorithm.RUBBER2: _rubber2,
                 Algorithm.RIBBON: _ribbon, Algorithm.MEAN: _mean,
                 Algorithm.NEW: _new}


def contract(g, alg: Algorithm | str = Algorithm.RUBBER) -> None:
    """One contraction pass over every node, by the chosen algorithm."""
    alg = as_algorithm(alg)       # a name still works, and rejects a wrong one
    iv.set_dimensions(g.dimensions)
    step = _CONTRACTIONS[alg]
    mean = _mean_edge_length(g) if alg is Algorithm.NEW else 0
    for nd in g.ordered():
        if nd.nlink == 0:
            iv.zero_vector(nd.pos)
            continue
        step(g, nd, nd.nlink, mean)


def squeeze(g) -> None:
    """Pull each node's length toward the mean -> closer to a sphere."""
    iv.set_dimensions(g.dimensions)
    n = g.nnodes
    mean = 0
    for nd in g.nodes.values():
        mean += iv.vector_length(nd.pos) // n
    for nd in g.ordered():
        length = iv.vector_length(nd.pos) or 1
        vec = list(nd.pos)
        iv.scale_vector(vec, mean, length)
        iv.scale_vector(vec, 1, 5)
        iv.add_vector(nd.pos, vec)


def punish(g) -> None:
    """Shrink higher dimensions a little (see design note in ARCHITECTURE)."""
    iv.set_dimensions(g.dimensions)
    NORM = iv.NORM
    vec = iv.new_vector()
    for i in range(g.dimensions):
        dimnum = i + 1
        vec[i] = (NORM * NORM) // (NORM + dimnum * NORM // 400)
    for nd in g.nodes.values():
        iv.dot_product(nd.pos, vec)


def normalize(g) -> None:
    """Recentre (mean -> 0) and rescale so the max length becomes NORM."""
    iv.set_dimensions(g.dimensions)
    d, n = g.dimensions, g.nnodes
    vec = iv.new_vector()
    for dim in range(d):
        lmean = 0
        for nd in g.nodes.values():
            lmean += nd.pos[dim]
        vec[dim] = iv.idiv(lmean, n) if n else 0
    if iv.vector_length(vec) > 5:
        for nd in g.nodes.values():
            iv.sub_vector(nd.pos, vec)
    mx = 1
    for nd in g.nodes.values():
        length = iv.vector_length(nd.pos)
        if length > mx:
            mx = length
    for nd in g.nodes.values():
        iv.scale_vector(nd.pos, iv.NORM, mx)


def frame(g) -> None:
    """Make freshly established coordinates visible at the current ``NORM``.

    Seeding a graph and framing it belong together: random vectors, the
    topology-derived seed of ``NewPermutograph`` and the coordinates read back
    from a session file all live at their own scale, and anything much smaller
    than ``NORM`` projects to a single dot.  Every producer of coordinates
    calls this, so no call site can forget it.
    """
    normalize(g)


def spin(g) -> None:
    """Rotate the (1,3) plane by a small fixed angle (integer fixed-point).

    Only this one plane, and deliberately: a rotation of (3,4) here would *make*
    a fourth dimension out of the third, because turning a plane whose one axis
    is occupied and whose other is empty spreads the extent across both.  A
    genuinely three-dimensional graph would then never satisfy
    :func:`can_shrink` again and would sit at 4-D for ever (which is what
    ``test_a_geodesic_dome_still_falls_from_8d_to_3d`` caught).  Turning the
    fourth dimension into view is a matter of *looking*, and lives in
    :func:`permuto.scene.project`; the layout keeps the figure as it is.
    """
    iv.set_dimensions(g.dimensions)
    NORM = iv.NORM
    rots = NORM // 120                       # sin ~ angle (small-angle)
    rotc = iv.sqrt(iv.sqr(NORM) - iv.sqr(rots))  # cos = sqrt(1 - sin^2)
    for nd in g.ordered():
        p = nd.pos
        v = list(p)
        p[0] = iv.scale(p[0], rotc, NORM) + iv.scale(v[2], rots, NORM)
        p[2] = iv.scale(p[2], rotc, NORM) - iv.scale(v[0], rots, NORM)


def can_shrink(g) -> bool:
    """True when the top dimension's extent is <= 1% of the first's."""
    iv.set_dimensions(g.dimensions)
    d = g.dimensions
    vec = iv.new_vector()
    for nd in g.nodes.values():
        for j in range(d):
            a = abs(nd.pos[j])
            if a > vec[j]:
                vec[j] = a
    return vec[d - 1] <= vec[0] // 100


def relax_step(g, alg: Algorithm | str = Algorithm.RUBBER,
               calculating: bool = True, spinning: bool = True) -> int:
    """One iteration of the main loop. Returns how many dimensions were shed."""
    alg = as_algorithm(alg)
    backup(g)
    if calculating:
        contract(g, alg)
        squeeze(g)
        if alg is Algorithm.RUBBER:
            punish(g)
    if spinning and g.dimensions >= 3:
        spin(g)
    normalize(g)
    dropped = 0
    while g.dimensions > 1 and can_shrink(g):
        g.set_dimensions(g.dimensions - 1)
        dropped += 1
    return dropped
