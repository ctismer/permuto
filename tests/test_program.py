"""PmProgs: SPA sets line states, ParSum runs to completion."""

from permuto.core import spa
from permuto.core.graph import Graph, L_FREE


def test_spa_line_states_and_parsum():
    g = Graph.build("123", ["12", "+", "23"], init=False)
    spa.init_spa(g, 1)
    steps = 0
    while spa.shortest_path(g):
        steps += 1
        assert steps < 100
    dist = {i: g.nodes[i].state.step - 1 for i in g.nodes}
    assert dist[1] == 0
    assert max(dist.values()) >= 1
    # the wave marks some edges as input/output/locked
    assert any(link.status != L_FREE
               for nd in g.nodes.values() for link in nd.links)
    # ParSum: seed and run backwards to completion
    assert spa.init_par_sum(g) is True
    n = 0
    while spa.par_sum(g):
        n += 1
        assert n < 500
