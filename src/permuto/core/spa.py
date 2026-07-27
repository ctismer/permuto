"""Faithful port of ``PmProgs`` (pmprogs.def / pmprogs.mod) — the permutographic
programs that run *on* the graph. Christian's "child".

* ``ShortestPath`` — a parallel breadth-first wave; distances = ``step - 1``.
* ``ParSum`` — walks the SPA paths backwards, summing path counts.

Each step also updates the per-edge :data:`LineStatus` (input / output /
locked), so the programs can be watched, exactly as in the original.
"""

from __future__ import annotations


from .graph import (Graph, L_FREE, L_INPUT, L_LOCKED, L_OUTPUT)


def reset_machine(g: Graph) -> None:
    for nd in g.nodes.values():
        nd.state.step = 0
        nd.state.active = False
        for link in nd.links:
            link.status = L_FREE


def update_linestates(g: Graph) -> None:
    """Port of ``_update_linestates``: edge state from the two step values."""
    for nd in g.ordered():
        st = nd.state
        for link in nd.links:
            ot = g.nodes[link.to].state
            if st.dead or ot.dead:
                link.status = L_LOCKED
            elif link.broken:
                link.status = L_FREE
            elif st.step == 0 or ot.step == 0:
                link.status = L_FREE
            elif st.step < ot.step:
                link.status = L_OUTPUT
            elif st.step == ot.step:
                link.status = L_LOCKED
            else:  # st.step > ot.step
                link.status = L_INPUT


def activate_maxstep(g: Graph) -> int:
    """Port of ``_activate_maxstep``: find the max step, activate those."""
    mx = 0
    for nd in g.nodes.values():
        if not nd.state.dead and nd.state.step > mx:
            mx = nd.state.step
    if mx == 0:
        return 0
    for nd in g.nodes.values():
        if not nd.state.dead and nd.state.step == mx:
            nd.state.active = True
            nd.state.display = nd.state.sum
    return mx


def init_spa(g: Graph, start: int) -> None:
    reset_machine(g)
    g.nodes[start].state.active = True
    g.nodes[start].state.step = 1
    for nd in g.nodes.values():
        nd.state.display = nd.num
    g.nodes[start].state.display = g.nodes[start].state.step - 1


def shortest_path(g: Graph) -> bool:
    """One parallel BFS step. Returns False when no active node remains."""
    act = set()
    found = 0
    for i in sorted(g.nodes):
        s = g.nodes[i].state
        if s.active:
            s.active = False
            if not s.dead:
                act.add(i)
                found += 1
    if found == 0:
        return False
    for i in sorted(g.nodes):
        if i not in act:
            continue
        nd = g.nodes[i]
        phase = nd.state.step
        for link in nd.links:
            if link.broken or g.nodes[link.to].state.dead:
                continue
            js = g.nodes[link.to].state
            if js.step == 0:
                js.step = phase + 1
                js.active = True
                js.display = js.step - 1
    update_linestates(g)
    return True


def init_par_sum(g: Graph) -> bool:
    """Port of ``InitParSum``: seed every node's sum with 1, activate the
    sinks (largest SPA step). Requires SPA to have run first."""
    for nd in g.nodes.values():
        nd.state.sum = 1
    ok = activate_maxstep(g) > 0
    for nd in g.nodes.values():
        if nd.state.active:
            nd.state.display = nd.state.sum
    return ok


def par_sum(g: Graph) -> bool:
    """One ParSum step: active nodes push their sums back along input lines."""
    act = set()
    found = 0
    for i in sorted(g.nodes):
        s = g.nodes[i].state
        if s.active:
            s.active = False
            if not s.dead:
                act.add(i)
                found += 1
    if found == 0:
        return False
    for i in sorted(g.nodes):
        if i not in act:
            continue
        nd = g.nodes[i]
        nd.state.step = -nd.state.step  # clear, so it will not reactivate
        for link in nd.links:
            if link.broken or g.nodes[link.to].state.dead:
                continue
            other = g.nodes[link.to].state
            if other.sum != 0:
                message = nd.state.sum
                nd.state.sum = 0
                nd.state.display = nd.state.sum
                other.sum += message
                other.display = other.sum
    update_linestates(g)
    return activate_maxstep(g) > 0


def distances(g: Graph, start: int) -> dict[int, int]:
    """Shortest-path distances from ``start`` (unreached -> -1)."""
    init_spa(g, start)
    while shortest_path(g):
        pass
    return {i: (g.nodes[i].state.step - 1 if g.nodes[i].state.step else -1)
            for i in g.nodes}
