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

from typing import List

from . import intvector as iv

ALGORITHMS = ("rubber", "rubber2", "ribbon", "mean", "new")


def backup(g) -> None:
    """Copy ``pos`` into ``old`` (so Contract reads a stable snapshot)."""
    for nd in g.nodes.values():
        nd.old = list(nd.pos)


def contract(g, alg: str = "rubber") -> None:
    iv.set_dimensions(g.dimensions)
    NORM = iv.NORM

    mean = 0
    if alg == "new":
        lsum = lcount = 0
        for nd in g.ordered():
            for j in nd.links:
                tmp = list(g.nodes[j].old)
                iv.sub_vector(tmp, nd.pos)
                lsum += iv.vector_length(tmp)
                lcount += 1
        if lcount:
            mean = lsum // lcount

    for nd in g.ordered():
        nlink = nd.nlink
        if nlink == 0:
            iv.zero_vector(nd.pos)
            continue
        vec = iv.new_vector()

        if alg == "rubber":
            for j in nd.links:
                tmp = list(g.nodes[j].old)
                iv.sub_vector(tmp, nd.pos)
                iv.add_vector(vec, tmp)
            iv.scale_vector(vec, 1, 3 * nlink)
            iv.add_vector(nd.pos, vec)

        elif alg == "rubber2":
            for j in nd.links:
                tmp = list(g.nodes[j].old)
                iv.sub_vector(tmp, nd.pos)
                length = iv.vector_length(tmp)
                iv.scale_vector(tmp, length, nlink * NORM)
                iv.add_vector(vec, tmp)
            iv.scale_vector(vec, 1, 3 * nlink)
            iv.add_vector(nd.pos, vec)

        elif alg == "ribbon":
            mx, mn = 1, 1 << 30
            for j in nd.links:
                cmp = list(g.nodes[j].old)
                iv.sub_vector(cmp, nd.pos)
                length = iv.vector_length(cmp)
                if length > mx:
                    mx = length
                    vec = list(cmp)
                if length < mn:
                    mn = length
            iv.scale_vector(vec, (mx - mn) // 100, mx)
            iv.add_vector(nd.pos, vec)

        elif alg == "mean":
            for j in nd.links:
                iv.add_vector(nd.pos, g.nodes[j].old)

        elif alg == "new":
            for j in nd.links:
                iv.add_vector(vec, g.nodes[j].old)
            iv.scale_vector(vec, 1, 20 * nlink)
            iv.add_vector(nd.pos, vec)
            for _ in range(2):  # "nochmal!" -- contract long edges twice
                for j in nd.links:
                    tmp = list(g.nodes[j].old)
                    iv.sub_vector(tmp, nd.pos)
                    length = iv.vector_length(tmp)
                    if length > mean:
                        iv.scale_vector(tmp, (length - mean) // nlink, 2 * length)
                        iv.add_vector(nd.pos, tmp)
        else:
            raise ValueError(f"unknown algorithm {alg!r}")


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
    """Rotate the (1,3) plane by a small fixed angle (integer fixed-point)."""
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


def relax_step(g, alg: str = "rubber", calculating: bool = True,
               spinning: bool = True) -> int:
    """One iteration of the main loop. Returns how many dimensions were shed."""
    backup(g)
    if calculating:
        contract(g, alg)
        squeeze(g)
        if alg == "rubber":
            punish(g)
    if spinning and g.dimensions >= 3:
        spin(g)
    normalize(g)
    dropped = 0
    while g.dimensions > 1 and can_shrink(g):
        g.set_dimensions(g.dimensions - 1)
        dropped += 1
    return dropped
