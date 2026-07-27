"""PM: permutograph construction from base + operator table, and the runtime
graph surgery behind the original's program menu."""

import pytest

from permuto import InvalidBase, InvalidCycle
from permuto.core import Graph
from permuto.core.graph import MAX_LINKS
from permuto.core.pm import DEFAULT_OPS, MAX_CYC, MAX_OPS, PM
from permuto.errors import LimitExceeded


def make_pm(base, ops):
    """A PM with exactly the given operators (each a list of cycles)."""
    pm = PM(base=base)
    pm.optable = [["" for _ in range(MAX_CYC)] for _ in range(MAX_OPS)]
    for i, row in enumerate(ops):
        for j, cyc in enumerate(row):
            pm.set_cycle(i + 1, j + 1, cyc)
    return pm


def degrees(g):
    return sorted({nd.nlink for nd in g.nodes.values()})


def is_connected(g):
    seen, stack = {1}, [1]
    while stack:
        for y in g.nodes[stack.pop()].neighbours:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return len(seen) == g.nnodes


# The configurations actually stored in the surviving legacy/**/*.ply headers.
# They are the real proof that multiset bases and multi-cycle operators work:
# repeated characters are what keeps the node count down to a solid, and the
# expected degrees identify the solid the file is named after.
PLY_CASES = [
    # name,      base,        operators,                       nodes, degree
    ("cube",     "11111112",  [["1234"], ["5678"], ["18", "27"], ["36", "45"]], 8, 3),
    ("ikosa",    "1123",      [["123"], ["234"], ["12", "34"]],                12, 5),
    ("kubokt",   "1123",      [["123"], ["234"]],                              12, 4),
    ("okt1",     "123",       [["123"], ["12"], ["23"]],                        6, 4),
    ("okt2",     "1122",      [["12"], ["13"], ["14"], ["23"], ["24"], ["34"]], 6, 4),
    ("okt3",     "111112",    [["123456"], ["136425"]],                         6, 4),
    ("pg24",     "1234",      [["12"], ["23"], ["34"]],                        24, 3),
]


@pytest.mark.parametrize("name,base,ops,nodes,degree", PLY_CASES,
                         ids=[c[0] for c in PLY_CASES])
def test_legacy_ply_configurations_rebuild_their_solid(name, base, ops, nodes, degree):
    g = make_pm(base, ops).new_permutograph()
    assert (g.nnodes, degrees(g)) == (nodes, [degree])
    assert is_connected(g)


def test_operator_table_agrees_with_the_golden_generation_path():
    """PM's table form must build the same graph as the .pgd operator form.

    Graph.build is verified byte-for-byte against the 1990s .pg/.nod files, so
    agreeing with it is the strongest check available for the table path.
    """
    got = make_pm("123", [["12"], ["23"]]).new_permutograph()
    want = Graph.build("123", ["12", "+", "23"], init=False)
    assert got.nnodes == want.nnodes
    for num in sorted(want.nodes):
        a, b = got.nodes[num], want.nodes[num]
        assert (a.perm, {lk.to: lk.op for lk in a.links}) == \
               (b.perm, {lk.to: lk.op for lk in b.links})


def test_grouping_cycles_shares_one_operator_number_across_edges():
    """What MaxCyc=3 buys: cube.ply stores 18+27 as *one* operator and 36+45 as
    another.  The cycles are disjoint, so the topology is the same either way --
    the point is that edges of one type share a number (hence a colour), and
    that four slots suffice where six would otherwise be spent.
    """
    grouped = make_pm("11111112", [["1234"], ["5678"], ["18", "27"], ["36", "45"]])
    apart = make_pm("11111112", [["1234"], ["5678"], ["18"], ["27"], ["36"], ["45"]])
    gg, ga = grouped.new_permutograph(), apart.new_permutograph()

    def edges(g):
        return {tuple(sorted((n, j)))
                for n in g.nodes for j in g.nodes[n].neighbours}

    assert edges(gg) == edges(ga)                    # same solid
    assert gg.n_operators == 4 and ga.n_operators == 6
    assert max(lk.op for nd in gg.nodes.values() for lk in nd.links) == 4

    # and the composition itself is a single move, not two hops
    assert grouped.apply_operator("11111112", 3) == "21111111"


# --- base validation: where the original let nonsense through ----------

@pytest.mark.parametrize("base,reason", [
    ("", "empty"),
    ("123456789", "at most 8"),          # 9 places, MAXDIMEN is 8
])
def test_unusable_bases_are_rejected_with_a_reason(base, reason):
    """PermBasisValid used the global Order, which is 0 on the first edit, so
    NextPerm aborted at once and it returned TRUE unseen."""
    with pytest.raises(InvalidBase) as exc:
        PM(base=base)
    assert reason in str(exc.value)


def test_the_longest_base_the_dimensions_allow_is_not_refused_for_size():
    """MAXDIMEN caps the base at eight places, so a node count that refused
    eight places was a second limit for the same thing.  40320 nodes are slow
    -- about a second a frame, which is what HurryUp is for -- but they are the
    program working, not the program saying no."""
    pm = PM(base="12345678")
    assert len(pm._perms) == 40320


def test_a_caller_can_still_tighten_the_bound_and_hear_why():
    """The limit stayed as something to set, and the refusal says what to do
    about it."""
    with pytest.raises(InvalidBase) as exc:
        PM(base="1234", max_nodes=10)
    assert "24 permutations" in str(exc.value)
    assert "--max-nodes" in str(exc.value)


def test_cycle_outside_the_base_is_rejected():
    with pytest.raises(InvalidCycle) as exc:
        PM(base="123").set_cycle(1, 1, "14")
    assert "1..3" in str(exc.value)


def test_shortening_the_base_drops_the_operators_that_no_longer_fit():
    pm = PM(base="1234")                      # starts with 12, 23, 34
    pm.set_base("12")
    assert pm.drop_invalid_cycles() == 2      # 23 and 34 go, 12 survives
    assert [row[0] for row in pm.optable[:3]] == ["12", "", ""]
    assert pm.drop_invalid_cycles() == 0


# --- rebuilding --------------------------------------------------------

def test_rebuild_with_the_same_base_keeps_the_picture():
    """"this makes a nice move from one contexture to another" -- positions
    survive an operator change, only perturbed by links[i] MOD 43."""
    pm = PM(base="1234")
    g = pm.new_permutograph()
    before = {n: list(nd.pos) for n, nd in g.nodes.items()}

    pm.set_cycle(4, 1, "14")
    assert pm.new_permutograph(g, reset=False) is g

    for n, nd in g.nodes.items():
        shift = [a - b for a, b in zip(nd.pos, before[n])]
        assert shift == [nd.links[i].to % 43 if i < nd.nlink else 0
                         for i in range(len(shift))]
    assert any(nd.nlink == 4 for nd in g.nodes.values())    # the new operator landed


def test_reset_seeds_from_topology_so_rebuilds_are_reproducible():
    """Unlike the .nod path there is no RandomVector here: coordinates come
    from the link numbers, so the same table always gives the same start."""
    pm = make_pm("123", [["12"], ["23"]])
    a, b = pm.new_permutograph(), pm.new_permutograph()
    assert [nd.pos for nd in a.ordered()] == [nd.pos for nd in b.ordered()]
    assert any(any(nd.pos) for nd in a.ordered())     # and not simply all zero


# --- runtime editing ---------------------------------------------------

def test_connect_recovers_the_operator_number_after_a_disconnect():
    pm = PM(base="1234")
    g = pm.new_permutograph()
    op = {lk.to: lk.op for lk in g.nodes[1].links}[2]
    g.disconnect(1, 2)
    assert pm.connect(g, 1, 2)
    assert {lk.to: lk.op for lk in g.nodes[1].links}[2] == op


def test_connect_refuses_a_full_node_instead_of_swallowing_the_edge():
    """The original's Connect returned nothing, so a full node silently ate
    the edge and Collapse could lose edges without a word.

    A five-place base, because filling a node to MAX_LINKS needs more
    neighbours than the 24 nodes of base 1234 can offer."""
    pm = PM(base="12345")
    g = pm.new_permutograph()
    free = [n for n in sorted(g.nodes) if n != 1 and not g.is_linked(1, n)]
    while g.nodes[1].nlink < MAX_LINKS:
        assert pm.connect(g, 1, free.pop(0))
    assert g.nodes[1].nlink == MAX_LINKS
    assert pm.connect(g, 1, free.pop(0)) is False


def test_collapse_moves_the_neighbours_and_reports_what_was_lost():
    pm = PM(base="1234")
    g = pm.new_permutograph()
    n1 = 1
    n2 = g.nodes[n1].links[0].to
    others = [j for j in g.nodes[n1].neighbours if j != n2]
    assert pm.collapse(g, n1, n2) == 0
    assert g.nodes[n1].nlink == 0                 # left isolated, not deleted
    assert all(g.is_linked(j, n2) for j in others)


def test_uncollapse_restores_exactly_the_canonical_edges():
    pm = PM(base="1234")
    g = pm.new_permutograph()
    before = sorted(g.nodes[1].neighbours)
    pm.collapse(g, 1, g.nodes[1].links[0].to)
    assert g.nodes[1].nlink == 0
    pm.uncollapse(g, 1)
    assert sorted(g.nodes[1].neighbours) == before


def test_broken_marks_follow_their_edge_through_a_disconnect():
    """The original shifted links and opno but left state.broken indexing the
    old positions, so removing one edge silently re-targeted the mark.

    The port fixed that by hand, and then removed the shape that allowed it:
    the mark lives on the edge, so there is no index left to go stale.  The
    test stays because the property is what matters, not how it is achieved.
    """
    pm = PM(base="1234")
    g = pm.new_permutograph()
    nd = g.nodes[1]
    marked = nd.links[2]
    marked.broken = True
    g.disconnect(1, nd.links[0].to)
    assert [lk for lk in nd.links if lk.broken] == [marked]


# -- the six-operator ceiling ------------------------------------------------

def test_the_table_grows_past_the_six_rows_the_1995_screen_had():
    """`MaxOps = 6` was `MaxLinks / 2` (pm.def:56) and MaxLinks was 12 because
    the links lived in a fixed array.  They are lists now, so the ceiling moved
    -- and with a six-place base there are fifteen transpositions to choose
    from, of which six was an arbitrary few."""
    pm = PM(base="123456")
    assert pm.n_ops == DEFAULT_OPS == 6, "a fresh table is what the screen had"
    for i, cyc in enumerate(["12", "23", "34", "45", "56", "16", "13", "46"],
                            start=1):
        pm.set_cycle(i, 1, cyc)
    assert pm.n_ops == 8, "typing into row 7 has to make room for it"

    g = pm.new_permutograph()
    assert g.nnodes == 720
    assert {nd.nlink for nd in g.nodes.values()} == {8}, \
        "every node gets one edge per operator"
    assert max(lk.op for nd in g.nodes.values() for lk in nd.links) == 8


def test_the_operator_ceiling_is_the_link_ceiling_halved():
    """The original said so in a comment and then hard-coded both numbers.  It
    is the arithmetic itself now, so the two cannot drift apart."""
    assert MAX_OPS == MAX_LINKS // 2


def test_an_operator_past_the_ceiling_is_refused_with_its_limits():
    pm = PM(base="1234")
    with pytest.raises(LimitExceeded) as exc:
        pm.set_cycle(MAX_OPS + 1, 1, "12")
    assert str(MAX_OPS) in str(exc.value)
    assert pm.n_ops == DEFAULT_OPS, "a refused operator may not grow the table"
