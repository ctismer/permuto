"""SPA (PmProgs) port vs an independent BFS on the recovered graphs."""

from collections import deque

import pytest
from conftest import modula_dir

from permuto.core.graph import Graph
from permuto.core.spa import distances
from permuto.formats import read_nod


def _bfs(links, start):
    dist = {start: 0}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in links.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


GRAPHS = ["pgl3", "pgl4", "pgl5", "wuerfel", "tetraede", "oktaeder", "dodekaed"]


@pytest.mark.parametrize("name", GRAPHS)
def test_spa_matches_bfs(name):
    path = modula_dir() / "nod" / f"{name}.nod"
    if not path.exists():
        pytest.skip(f"{name}.nod missing")
    g = Graph.load_nod(path, init=False)
    start = min(g.nodes)
    got = distances(g, start)
    ref = _bfs(read_nod(path).links, start)
    for node in g.nodes:
        assert got[node] == ref.get(node, -1), f"{name}: node {node}"
