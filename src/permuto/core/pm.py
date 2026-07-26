"""Port of ``PM`` (pm.def / pm.mod) -- permutograph construction and editing.

This is the model behind the operator editor: a **base permutation** plus a
table of up to ``MAX_OPS`` operators, each a product of up to ``MAX_CYC``
position cycles.  Three cycles per operator is what makes products of disjoint
transpositions expressible -- ``cube.ply`` uses ``1234``, ``5678``, ``18``,
``27``, ``36``, ``45``.

The editing operations (:func:`connect`, :func:`disconnect`, :meth:`PM.collapse`,
:meth:`PM.uncollapse`) are the runtime graph surgery reachable from the original's
program menu.

Deviations from the original, all deliberate (``docs/PORT-GAPS.md`` §0):

* ``PermBasisValid`` validated the base using the *global* ``Order``, which is 0
  until ``NewPermutograph`` has run.  On the very first edit ``NextPerm``
  therefore aborted at once and the check returned ``TRUE`` unseen, letting
  invalid bases through.  Here the length is taken from the string itself, and
  an unusable base raises :class:`~permuto.errors.InvalidBase`.
* ``PermBisect`` searched with ``hi := p-1``, which can step over a match; and
  ``PermName`` read its ``Name`` variable uninitialised when the cache belonged
  to a different base.  The lookup is an index dict here -- same meaning, no
  reliance on the cache happening to be sorted.
* ``Connect`` failed silently when a node had no free link slot, and
  ``Collapse`` could therefore drop edges without a word.  Both now report.

Kept faithfully, because the behaviour is visible:

* the base is normalised to its lexicographically smallest form (``FindBase``);
* rebuilding with an unchanged base keeps the existing node positions -- "this
  makes a nice move from one contexture to another";
* new dimensions are seeded from the link numbers (``pos[i] := links[i]``) and
  existing ones perturbed by ``links[i] MOD 43`` ("primes are good here"), so
  a collapsed structure gets shuffled apart rather than staying degenerate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..errors import InvalidBase, InvalidCycle, LimitExceeded, limit_check
from ..gen.operate import apply_cycle
from ..perms import next_perm
from . import intvector as iv
from .graph import MAX_LINKS, Graph, Node, NodeState

MAX_OPS = 6      # PM.MaxOps -- "should be MaxLinks / 2, each op has max 2 arms"
MAX_CYC = 3      # PM.MaxCyc
MAX_NODES_TOT = 2000  # NodeMgr.MaxNodesTot ("aber weniger koennte allokiert werden")

DEFAULT_BASE = "1234"
DEFAULT_OPERATORS = ("12", "23", "34")  # PM's module init


# --- pure helpers ------------------------------------------------------

def find_base(perm: str) -> str:
    """``PM.FindBase`` -- the lexicographically smallest representation.

    The original sorts in place with a bubble sort and the note "straight
    sorting appropriate here".
    """
    return "".join(sorted(perm))


def valid_cycle(order: int, cycle: str) -> bool:
    """``PM.ValidCycle`` -- every character must address a position ``1..order``.

    The empty cycle is valid and means "unused slot".
    """
    return all("1" <= c <= chr(ord("0") + order) for c in cycle)


def cyclic_operate(perm: str, cycle: str) -> str:
    """``PM.CyclicOperate`` -- apply one position cycle.

    Identical to :func:`permuto.gen.operate.apply_cycle`, which the generation
    pipeline already uses: both compute ``perm[to] = old[from]`` over the pairs
    of the rotated cycle, reading sources from the pre-cycle state.
    """
    if not cycle or not perm:
        return perm
    return apply_cycle(perm, cycle)


def all_perms_from(base: str) -> List[str]:
    """Every permutation of *base*, in ``NextPerm`` order starting at *base*.

    With a sorted base this is plain lexicographic order, and it handles
    repeated characters correctly -- ``11223`` yields 5!/(2!·2!) = 30, not 120.
    """
    out: List[str] = []
    cur = list(base)
    while True:
        out.append("".join(cur))
        if next_perm(cur):
            break
    return out


# --- the PM state ------------------------------------------------------

@dataclass
class PM:
    """Base permutation + operator table, and the graph built from them."""

    base: str = DEFAULT_BASE
    optable: List[List[str]] = field(default_factory=lambda: _default_optable())
    last_edit_line: int = 0        # PM.LastEditLine, persisted in .ply
    max_nodes: int = MAX_NODES_TOT

    _perms: List[str] = field(default_factory=list, repr=False)
    _index: Dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.set_base(self.base)

    # -- base and operators --------------------------------------------
    @property
    def order(self) -> int:
        """``PM.Order`` -- the length of the base permutation."""
        return len(self.base)

    def set_base(self, base: str) -> None:
        """Validate, normalise and adopt a new base; rebuild the perm cache.

        Raises :class:`InvalidBase` where the original would have accepted the
        string and produced nonsense (see the module docstring).
        """
        if not base:
            raise InvalidBase("the base permutation is empty")
        if len(base) > iv.MAXDIMEN:
            raise InvalidBase(
                f"base {base!r} has {len(base)} places, at most "
                f"{iv.MAXDIMEN} are supported"
            )
        normalised = find_base(base)
        perms = all_perms_from(normalised)
        if len(perms) > self.max_nodes:
            raise InvalidBase(
                f"base {base!r} generates {len(perms)} permutations, "
                f"the limit is {self.max_nodes}"
            )
        self.base = normalised
        self._perms = perms
        self._index = {p: i + 1 for i, p in enumerate(perms)}

    def set_cycle(self, op: int, cyc: int, value: str) -> None:
        """Set one cycle of one operator (both 1-based), validating it.

        The editor cannot leave a field holding an invalid cycle, so this is
        where that rule lives.
        """
        limit_check("operator number", op, 1, MAX_OPS)
        limit_check("cycle number", cyc, 1, MAX_CYC)
        if not valid_cycle(self.order, value):
            raise InvalidCycle(
                f"cycle {value!r} addresses positions outside 1..{self.order} "
                f"of base {self.base!r}"
            )
        self.optable[op - 1][cyc - 1] = value

    def drop_invalid_cycles(self) -> int:
        """Clear cycles that no longer fit the base; return how many went.

        ``EdPermuto`` does this after editing, because shortening the base can
        leave operators addressing positions that no longer exist.
        """
        dropped = 0
        for row in self.optable:
            for k, cyc in enumerate(row):
                if cyc and not valid_cycle(self.order, cyc):
                    row[k] = ""
                    dropped += 1
        return dropped

    def apply_operator(self, perm: str, op: int) -> str:
        """Apply all cycles of operator *op* (1-based) to *perm*."""
        for cyc in self.optable[op - 1]:
            if cyc and valid_cycle(len(perm), cyc):
                perm = cyclic_operate(perm, cyc)
        return perm

    # -- naming ---------------------------------------------------------
    @property
    def permutations(self) -> List[str]:
        """All node permutations, in node-number order (node 1 = base)."""
        return list(self._perms)

    def perm_name(self, perm: str) -> int:
        """``PM.PermName`` -- 1-based node number of *perm*, 0 if unknown."""
        return self._index.get(perm, 0)

    # -- construction ---------------------------------------------------
    def new_permutograph(self, g: Optional[Graph] = None, *,
                         reset: bool = True) -> Graph:
        """``PM.NewPermutograph`` -- (re)build the graph from base + operators.

        With ``reset`` the nodes are created from scratch; without it only the
        links are recomputed and the existing positions are kept, which is what
        makes changing an operator look like a move rather than a jump.

        Fresh nodes are seeded from the link numbers -- tens of units, which at
        the current ``NORM`` would project to a single dot -- so a rebuilt
        graph is framed before it is handed back.  Kept positions are already
        at scale and are left exactly as they were, perturbation and all.
        """
        from . import layout

        fresh = reset or g is None
        if reset or g is None:
            g = Graph()
            g.nnodes = len(self._perms)
            for i, p in enumerate(self._perms, start=1):
                nd = Node(num=i, perm=p)
                # colour is the position of the node's first character in the base
                nd.color = self.base.index(p[0]) + 1 if p else 7
                g.nodes[i] = nd
            last_dimension = 0
        else:
            for nd in g.nodes.values():
                nd.nlink = 0
                nd.links.clear()
                nd.opno.clear()
                nd.state = NodeState()
            last_dimension = g.dimensions

        g.n_operators = sum(1 for row in self.optable if any(row))
        g.set_dimensions(iv.MAXDIMEN)

        self._link_nodes(g)
        self._seed_positions(g, last_dimension)
        g.pack_nodes()
        if fresh:
            layout.frame(g)
        return g

    def _link_nodes(self, g: Graph) -> None:
        """Run every operator on every node and link the results, undirected.

        A node pair is linked once; the operator number recorded is the first
        one that produced it, exactly as in the original.
        """
        for frm in sorted(g.nodes):
            nd = g.nodes[frm]
            for op in range(1, MAX_OPS + 1):
                if not any(self.optable[op - 1]):
                    continue
                to = self.perm_name(self.apply_operator(nd.perm, op))
                if to == 0 or to == frm:
                    continue
                for a, b in ((frm, to), (to, frm)):
                    node = g.nodes[a]
                    if b in node.links:
                        continue
                    if node.nlink >= MAX_LINKS:
                        raise LimitExceeded(
                            f"links of node {a}", node.nlink + 1, 0, MAX_LINKS
                        )
                    node.links.append(b)
                    node.opno.append(op)
                    node.nlink = len(node.links)

    def _seed_positions(self, g: Graph, last_dimension: int) -> None:
        """Seed coordinates from the link numbers (``NewPermutograph``'s tail).

        Note there is no randomness here: in permutograph mode the starting
        layout is derived from the topology, unlike the ``.nod`` path which
        seeds with ``RandomVector``.
        """
        for nd in g.ordered():
            def link(k: int) -> int:      # links[k], 1-based, 0 past the end
                return nd.links[k - 1] if k <= nd.nlink else 0
            for i in range(last_dimension):
                nd.pos[i] += link(i + 1) % 43       # "primes are good here"
            for i in range(last_dimension, iv.MAXDIMEN):
                nd.pos[i] = link(i + 1)

    # -- runtime editing ------------------------------------------------
    def exec_operator(self, g: Graph, n1: int, op: int) -> int:
        """``PM.ExecOperator`` -- node reached from *n1* by operator *op*.

        Returns *n1* itself when the operator does not apply -- notably for
        graphs loaded from ``.nod``, which carry no permutation strings.
        """
        if op == 0:
            return n1
        perm = g.nodes[n1].perm
        if not perm:
            return n1
        return self.perm_name(self.apply_operator(perm, op)) or n1

    def which_operator(self, g: Graph, n1: int, n2: int) -> int:
        """``PM.WhichOperator`` -- reconstruct which operator joins two nodes."""
        for op in range(1, MAX_OPS + 1):
            if self.exec_operator(g, n1, op) == n2 or \
               self.exec_operator(g, n2, op) == n1:
                return op
        return 0

    def connect(self, g: Graph, n1: int, n2: int) -> bool:
        """``PM.Connect`` -- add an undirected edge. False if it did not happen.

        The original returned nothing, so a full node silently swallowed the
        edge; callers here can tell and report it.
        """
        if n1 <= 0 or n2 <= 0 or g.is_linked(n1, n2):
            return False
        if not g.links_avail(n1, n2):
            return False
        op = self.which_operator(g, n1, n2)
        for a, b in ((n1, n2), (n2, n1)):
            nd = g.nodes[a]
            nd.links.append(b)
            nd.opno.append(op)
            nd.nlink = len(nd.links)
        return True

    def collapse(self, g: Graph, n1: int, n2: int) -> int:
        """``PM.Collapse`` -- merge *n1* onto *n2*; returns edges lost.

        Every remaining neighbour of *n1* is re-attached to *n2*.  A neighbour
        that cannot be re-attached (because *n2* is full, or it is already
        there) is counted, so the caller can say so instead of the original's
        silent loss.  *n1* is left isolated, not removed -- "for future: kill
        all the unlinked nodes".
        """
        if not g.is_linked(n1, n2) or n1 == n2:
            return 0
        g.disconnect(n1, n2)
        lost = 0
        nd = g.nodes[n1]
        for _ in range(nd.nlink):
            node = nd.links[0]        # disconnect shifts, so index 0 is fine
            g.disconnect(n1, node)
            if not self.connect(g, node, n2):
                lost += 1
        return lost

    def uncollapse(self, g: Graph, n1: int) -> None:
        """``PM.Uncollapse`` -- drop all edges of *n1* and restore canonical ones."""
        for other in list(g.nodes[n1].links):
            g.disconnect(n1, other)
        for op in range(1, MAX_OPS + 1):
            node = self.exec_operator(g, n1, op)
            if node != n1:
                self.connect(g, n1, node)


def _default_optable() -> List[List[str]]:
    """PM's module initialisation: base ``1234`` with operators 12, 23, 34."""
    table = [["" for _ in range(MAX_CYC)] for _ in range(MAX_OPS)]
    for i, cyc in enumerate(DEFAULT_OPERATORS):
        table[i][0] = cyc
    return table
