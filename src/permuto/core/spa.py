"""Faithful port of ``PmProgs`` (pmprogs.def / pmprogs.mod): the SPA.

``ShortestPath`` is a *parallel* breadth-first wave: each call advances every
active node's frontier by one step, so distances = ``step - 1`` from the start
node.  This is Christian's "child".  ``distances`` runs it to completion.
"""

from __future__ import annotations

from typing import Dict

from .graph import Graph


def reset_machine(g: Graph) -> None:
    for nd in g.nodes.values():
        nd.state.step = 0
        nd.state.active = False


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
        for link, j in enumerate(nd.links, start=1):
            if link in nd.state.broken or g.nodes[j].state.dead:
                continue
            js = g.nodes[j].state
            if js.step == 0:  # empty node receives the wave
                js.step = phase + 1
                js.active = True
                js.display = js.step - 1
    return True


def distances(g: Graph, start: int) -> Dict[int, int]:
    """Shortest-path distances from ``start`` (unreached -> -1)."""
    init_spa(g, start)
    while shortest_path(g):
        pass
    return {i: (g.nodes[i].state.step - 1 if g.nodes[i].state.step else -1)
            for i in g.nodes}
