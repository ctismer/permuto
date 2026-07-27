"""Port of ``Iri`` (iri.def / iri.mod) -- the Iridium satellite simulation.

The program's intro calls it **SIMONE V1.4**; per the author it stands for
*SIMulation ONE*, after someone he had reason to like in 1992.  It is not a
permutograph: nodes are 55 satellites on a triangular grid, labelled ``"abc"``
with ``a + b + c = Freq = 9``, each linked to its (up to six) hexagonal
neighbours.

What makes it worth having is the **adaptive routing**.  Every satellite has an
*availability*, recomputed each step as a diffusion filter -- 65 % of its own
value, 30 % of the neighbourhood mean, plus a constant recharge, with 10000 as
the fixed point.  Shooting a satellite down (``avail = 0``) drags its
neighbours down too, so a dent forms in the availability field.  A packet picks
its next hop by ``quality x availability``, where quality is 5 towards the
target, 3 sideways and **2 backwards** -- backwards being reachable is exactly
what lets traffic detour around the damage.

Faithful details that matter:

* ``Movements`` runs ascending over the nodes and reads ``target`` *live* while
  availability comes from the ``avbak`` snapshot, so low-numbered nodes win
  conflicts.  Reproduced as-is; changing it changes the simulation.
* Only one packet fits in a node.  The original knew this was provisional:
  "Repeat function temporarily does two steps before inserting the new node.
  This is for the lack of packet storage in the nodes."
* The initial coordinates are seeded by repeatedly multiplying by 4/3, which
  grows exponentially and eventually overflows.  The port is 32-bit throughout
  (see ``intvector``), so the wrap happens later than on the 16-bit original;
  either way the seed layout is degenerate on purpose and the relaxation pulls
  it apart.

Deviations, all deliberate:

* Module state (``namestr``, ``toright``, ``MessageNumber``, ``ActColor``) lives
  on the instance.  The original could not rebuild a network without restarting
  the program -- nothing ever reset ``namestr``, so a second build began in the
  wrong place.
* Unknown labels raise :class:`~permuto.errors.NodeNotFound` instead of being
  silently ignored.  ``ReadInt(1,900)`` happily accepted labels whose digits do
  not sum to ``Freq``; ``SeekNode`` then returned 0 and the command did nothing
  at all, with no way to tell a typo from a refusal.

Known defects of the original, reproduced but not hidden -- see
:meth:`Iridium.stuck_senders` and :meth:`Iridium.orphaned_packets`.
"""

from __future__ import annotations


from ..errors import NodeNotFound, ProgramStateError
from . import intvector as iv
from .graph import Graph, IriState, Link, Node

FREQ = 9
LIMIT = (FREQ + 1) * (FREQ + 2) // 2      # 55 satellites
FULL = 10000                              # availability fixed point ("1.0")

# Weights of the availability filter; they sum to 0.95, so FULL is the fixed
# point: 0.05 * 10000 == the 500 recharge.
OWN_WEIGHT = 6500
NEIGHBOUR_WEIGHT = 3000
RECHARGE = 500
DISCHARGE = 8000                          # kept when a node forwards a packet

# Routing qualities, "a level of intention" in the author's words
QUAL_AWAY, QUAL_SIDEWAYS, QUAL_TOWARDS = 2, 3, 5

# DOS palette entries the simulation uses
BLACK, BLUE, RED, YELLOW = 0, 1, 4, 14
_RESERVED_COLORS = frozenset({BLUE, YELLOW, BLACK})

# The six neighbour operations: one coordinate up, one down, sum preserved.
_OPERATIONS = ((1, 2), (0, 2), (0, 1), (2, 1), (2, 0), (1, 0))

_MAX_DIGIT = str(FREQ)


def valid_label(label: str) -> bool:
    """A label is three digits summing to ``FREQ`` -- a point of the grid."""
    return (len(label) == 3 and label.isdigit()
            and sum(int(c) for c in label) == FREQ)


class Iridium:
    """The satellite network: builds its own grid, then routes packets on it."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        self.message_number = 0
        self._act_color = RED - 1
        self.restart_build()

    # -- building the grid ---------------------------------------------
    def restart_build(self) -> None:
        """Rewind the label sweep.  The original had no way to do this."""
        self._namestr = "0" + _MAX_DIGIT + "0"
        self._toright = True

    @property
    def built(self) -> bool:
        return self.graph.nnodes >= LIMIT

    def _sweep(self) -> str:
        """``Sweep`` -- the boustrophedon walk that names the nodes in order.

        Rows are traversed alternately left and right ("090", then "081" "180",
        then "270" "171" "072", ...), which is what makes the incremental build
        look like a growing sheet rather than scattered points.
        """
        r = [int(c) for c in self._namestr]
        if self._toright and r[0] == 0:
            r[1] -= 1
            r[2] += 1
            self._toright = False
        elif not self._toright and r[2] == 0:
            r[1] -= 1
            r[0] += 1
            self._toright = True
        elif self._toright:
            r[0] -= 1
            r[2] += 1
        else:
            r[0] += 1
            r[2] -= 1
        return "".join(str(d) for d in r)

    @staticmethod
    def operate(label: str, op: int) -> str:
        """``Operate`` -- move to the neighbour in direction *op* (1..6).

        One coordinate goes up and another down, so the digits keep summing to
        ``FREQ``.  At the rim the move is impossible and the label comes back
        unchanged, which is how the builder recognises "no edge here".
        """
        if not 1 <= op <= len(_OPERATIONS):
            return label
        p1, p2 = _OPERATIONS[op - 1]
        r = [int(c) for c in label]
        if r[p1] < FREQ and r[p2] > 0:
            r[p1] += 1
            r[p2] -= 1
        return "".join(str(d) for d in r)

    def seek_node(self, label: str) -> int:
        """``SeekNode`` -- node number for a label, 0 if it does not exist."""
        for num in sorted(self.graph.nodes):
            if self.graph.nodes[num].perm == label:
                return num
        return 0

    def _require(self, label: str) -> int:
        num = self.seek_node(label)
        if num == 0:
            hint = "" if valid_label(label) else \
                f" (a label is three digits summing to {FREQ})"
            raise NodeNotFound(f"no satellite {label!r} in the network{hint}")
        return num

    def new_node(self) -> Node | None:
        """``NewNode`` -- add the next satellite and link it to its neighbours.

        Only nodes that already exist get linked; later ones attach themselves
        when their turn comes.
        """
        g = self.graph
        node = None
        if not self.built:
            num = g.nnodes + 1
            g.nnodes = num
            node = Node(num=num, perm=self._namestr, color=YELLOW)
            node.iri = IriState(avail=FULL, avbak=FULL)
            node.pos[0], node.pos[1] = self._seed_position(num)
            g.nodes[num] = node

            for op in range(1, len(_OPERATIONS) + 1):
                name = self.operate(self._namestr, op)
                if name == self._namestr:
                    continue
                other = self.seek_node(name)
                if other == 0:
                    continue
                node.links.append(Link(to=other))
                g.nodes[other].links.append(Link(to=num))

        # advanced even when the network is full, exactly as in the original
        self._namestr = self._sweep()
        return node

    def _seed_position(self, num: int) -> tuple:
        """The starting coordinates, straight from ``NewNode``.

        Nodes 1 and 2 deliberately coincide; only the relaxation separates
        them.  Everything after node 3 inherits ``pos * 4 / 3`` from its
        predecessor, so the second coordinate stays 0 and the first grows
        exponentially until it wraps -- the layout is degenerate on purpose and
        gets pulled apart by ``PCalc.Contract`` with the ``New`` algorithm.
        """
        if num in (1, 2):
            return 0, iv.NORM
        if num == 3:
            return iv.NORM, 0
        prev = self.graph.nodes[num - 1]
        return (iv.int32(prev.pos[0] * 4 // 3),
                iv.int32(prev.pos[1] * 4 // 3))

    def build(self) -> Graph:
        """Build the whole grid at once (the viewer does it node by node)."""
        while not self.built:
            self.new_node()
        return self.graph

    # -- damage and traffic --------------------------------------------
    def kill_node(self, label: str) -> bool:
        """``KillNode`` -- toggle a satellite between dead and fully charged.

        Returns True if it is now dead.  Note "repair" restores a *full*
        battery rather than the value before the hit; that is the original's
        behaviour and it is visible on screen, so it stays.
        """
        state = self.graph.nodes[self._require(label)].iri
        state.avail = 0 if state.avail else FULL
        return state.avail == 0

    def _next_color(self) -> int:
        """``NextColor`` -- rotate, skipping the colours with a fixed meaning."""
        while True:
            self._act_color = (self._act_color + 1) % 16
            if self._act_color not in _RESERVED_COLORS:
                return self._act_color

    def transmit(self, frm: str, to: str, repeat: int = 0) -> int:
        """``Transmit`` -- inject a packet; returns its message number.

        With ``repeat`` the sender keeps the job and re-injects one packet per
        :meth:`repeat_all`, in a colour of its own so several streams stay
        distinguishable.

        The 1992 note "don't allow for target to be a broken node" is enforced
        here as an error rather than as silence.
        """
        n1, n2 = self._require(frm), self._require(to)
        nodes = self.graph.nodes
        for num, what in ((n1, "sender"), (n2, "target")):
            if nodes[num].iri.avail == 0:
                raise ProgramStateError(
                    f"satellite {nodes[num].perm} is dead and cannot be the {what}"
                )

        src, dst = nodes[n1], nodes[n2]
        src.iri.target = n2
        self.message_number = (self.message_number % 100) + 1
        src.iri.message_num = self.message_number
        src.iri.message_color = RED
        dst.color = BLUE
        dst.iri.message_num = self.message_number
        if repeat:
            src.iri.sender_target = n2
            src.iri.sender_repeat = repeat
            src.iri.sender_color = self._next_color()
        if src.iri.sender_repeat:
            src.iri.message_color = src.iri.sender_color
        src.color = src.iri.message_color
        return self.message_number

    def repeat_all(self) -> int:
        """``Repeat`` -- every idle sender with a stored job injects one more."""
        sent = 0
        nodes = self.graph.nodes
        for num in sorted(nodes):
            nd = nodes[num]
            if nd.iri.avail == 0 or nd.iri.target != 0 or not nd.iri.sender_repeat:
                continue
            target = nodes[nd.iri.sender_target]
            if target.iri.avail == 0:
                continue          # see stuck_senders(): no timeout in the original
            self.transmit(nd.perm, target.perm, 0)
            nd.iri.sender_repeat -= 1
            sent += 1
        return sent

    def reset(self) -> None:
        """``Reset`` -- clear the network.

        ``MessageNumber`` deliberately survives, as it did originally, so
        numbers keep counting across a clear.
        """
        for nd in self.graph.nodes.values():
            nd.color = YELLOW
            nd.iri = IriState(avail=FULL, avbak=FULL)
        self._act_color = RED - 1

    # -- one simulation step -------------------------------------------
    def step(self) -> None:
        """``Step`` -- recompute availability, then move the packets."""
        nodes = self.graph.nodes
        order = sorted(nodes)

        for num in order:
            st = nodes[num].iri
            st.avbak, st.tarbak = st.avail, st.target

        for num in order:
            nd = nodes[num]
            if nd.iri.avail == 0 or nd.nlink == 0:
                continue
            neighbourhood = sum(nodes[link.to].iri.avbak
                                for link in nd.links) // nd.nlink
            nd.iri.avail = (iv.scale(nd.iri.avail, OWN_WEIGHT, FULL)
                            + iv.scale(neighbourhood, NEIGHBOUR_WEIGHT, FULL)
                            + iv.scale(FULL, RECHARGE, FULL))

        self._movements()

    def _distance(self, a: str, b: str) -> int:
        """``Distance`` -- L1 over the three digits (twice the graph distance)."""
        return sum(abs(int(x) - int(y)) for x, y in zip(a, b))

    def _best_move(self, num: int) -> int:
        """``BestMove`` -- pick the next hop, or *num* itself if none is free.

        Availability is read from the snapshot but occupancy (``target``) is
        read live -- a mix that is almost certainly unintentional and definitely
        behaviour-relevant, so it is kept.
        """
        nodes = self.graph.nodes
        nd = nodes[num]
        target_label = nodes[nd.iri.tarbak].perm
        here = self._distance(nd.perm, target_label)

        qual, avail = [], []
        for link in nd.links:
            there = self._distance(nodes[link.to].perm, target_label)
            qual.append(QUAL_AWAY if here < there else
                        QUAL_SIDEWAYS if here == there else QUAL_TOWARDS)
            avail.append(nodes[link.to].iri.avbak)

        # the original scans backwards for a first candidate, so ties resolve
        # to the lowest link index
        best = -1
        for i in range(nd.nlink - 1, -1, -1):
            if avail[i] != 0 and nodes[nd.links[i].to].iri.target == 0:
                best = i
        if best < 0:
            return num

        for i in range(nd.nlink):
            if (nodes[nd.links[i].to].iri.target == 0
                    and iv.scale(qual[i], avail[i], 5)
                    > iv.scale(qual[best], avail[best], 5)):
                best = i
        return nd.links[best].to

    def _movements(self) -> None:
        """``Movements`` -- one hop per packet, then repaint.

        Selection uses the ``tarbak`` snapshot, so a packet handed on during
        this pass is not moved twice; and ``BestMove`` avoids occupied
        neighbours, which is the whole collision handling.
        """
        nodes = self.graph.nodes
        for num in sorted(nodes):
            nd = nodes[num]
            if nd.iri.avail == 0 or nd.iri.tarbak == 0:
                continue
            target = nd.iri.tarbak
            to = self._best_move(num)
            msg, col = nd.iri.message_num, nd.iri.message_color
            nd.iri.target = 0
            nd.iri.message_num = 0
            nd.iri.avail = iv.scale(nd.iri.avail, DISCHARGE, FULL)
            if target != num:
                nodes[to].iri.target = target
                nodes[to].iri.message_num = msg
                nodes[to].iri.message_color = col
            nd.color = YELLOW

        # "hidden message numbers must be revived, if they were hidden in
        # multiple targets" -- and the destination is marked blue
        for num in sorted(nodes):
            nd = nodes[num]
            if nd.iri.avail == 0 or nd.iri.target == 0:
                continue
            nd.color = nd.iri.message_color
            dst = nodes[nd.iri.target]
            if dst.iri.target == 0:
                dst.iri.message_num = nd.iri.message_num
                dst.iri.message_color = nd.iri.message_color
                dst.color = BLUE

    # -- reporting the original's known defects -------------------------
    def stuck_senders(self) -> list[int]:
        """Senders whose stored job can never complete: the target is dead.

        ``Repeat`` skips them without decrementing the counter and there is no
        timeout, so they wait forever.  The original gave no sign of this.
        """
        nodes = self.graph.nodes
        return [n for n in sorted(nodes)
                if nodes[n].iri.sender_repeat
                and nodes[nodes[n].iri.sender_target].iri.avail == 0]

    def orphaned_packets(self) -> list[int]:
        """Dead nodes still holding a packet.

        Killing a carrier loses its packet silently, and because ``target``
        stays set the node keeps blocking the collision check in ``BestMove``
        for good.
        """
        nodes = self.graph.nodes
        return [n for n in sorted(nodes)
                if nodes[n].iri.avail == 0 and nodes[n].iri.target != 0]

    # -- convenience ----------------------------------------------------
    @staticmethod
    def num_to_label(num: int) -> str:
        """``NumToLabel`` -- the decimal digits of *num* as a three-char label.

        This is how the interactive commands take their input: what the user
        types is the label shown on screen, not a node index.
        """
        return f"{num % 1000:03d}"

    def availability(self) -> dict[int, int]:
        """Current availability per node -- the field the display draws."""
        return {n: nd.iri.avail for n, nd in sorted(self.graph.nodes.items())}
