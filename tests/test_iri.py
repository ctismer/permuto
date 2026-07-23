"""Iridium / SIMONE: the satellite grid and its adaptive routing."""

import pytest

from permuto import NodeNotFound, ProgramStateError
from permuto.core.iri import (
    BLUE,
    FREQ,
    FULL,
    LIMIT,
    RED,
    YELLOW,
    Iridium,
    valid_label,
)


@pytest.fixture
def net():
    net = Iridium()
    net.build()
    return net


# --- the grid ----------------------------------------------------------

def test_the_grid_is_the_triangle_of_labels_summing_to_freq(net):
    """55 satellites, one per point of the triangular grid."""
    assert net.graph.nnodes == LIMIT == 55
    labels = {nd.perm for nd in net.graph.nodes.values()}
    assert len(labels) == 55
    assert all(valid_label(lab) for lab in labels)
    # exactly the multiset of all digit triples summing to FREQ
    expected = {f"{a}{b}{c}" for a in range(FREQ + 1) for b in range(FREQ + 1)
                for c in range(FREQ + 1) if a + b + c == FREQ}
    assert labels == {f"{int(l[0])}{int(l[1])}{int(l[2])}" for l in expected}


def test_the_sweep_visits_rows_alternately(net):
    """"090", then "081" "180", then "270" "171" "072" -- a boustrophedon, so
    the incremental build looks like a growing sheet."""
    order = [net.graph.nodes[n].perm for n in sorted(net.graph.nodes)]
    assert order[:6] == ["090", "081", "180", "270", "171", "072"]


def test_neighbours_differ_by_one_step_in_two_coordinates(net):
    """Every edge moves one unit from one coordinate to another, so the digit
    sum -- the grid -- is preserved."""
    for nd in net.graph.nodes.values():
        for j in nd.links:
            other = net.graph.nodes[j].perm
            deltas = [int(a) - int(b) for a, b in zip(nd.perm, other)]
            assert sorted(deltas) == [-1, 0, 1]


def test_the_grid_has_corners_a_rim_and_a_hexagonal_interior(net):
    by_degree = {}
    for nd in net.graph.nodes.values():
        by_degree.setdefault(nd.nlink, []).append(nd.perm)
    assert {d: len(v) for d, v in sorted(by_degree.items())} == {2: 3, 4: 24, 6: 28}
    assert sorted(by_degree[2]) == ["009", "090", "900"]   # the triangle's corners
    # rim nodes are exactly those with a zero coordinate
    assert all("0" in lab for lab in by_degree[4])
    assert not any("0" in lab for lab in by_degree[6])


def test_rebuilding_needs_no_fresh_process():
    """The original never reset namestr, so a second build started in the
    wrong place and there was no way to fix it short of restarting."""
    a = Iridium()
    a.build()
    b = Iridium()
    b.build()
    assert [n.perm for n in a.graph.ordered()] == [n.perm for n in b.graph.ordered()]


# --- availability ------------------------------------------------------

def test_a_healthy_network_stays_at_full_charge(net):
    """The filter's weights sum to 0.95 and the recharge supplies the rest, so
    FULL is the fixed point -- an undamaged network must not drift."""
    for _ in range(20):
        net.step()
    assert set(net.availability().values()) == {FULL}


def test_damage_spreads_a_dent_into_the_neighbourhood(net):
    victim = net.seek_node("450")
    net.kill_node("450")
    for _ in range(5):
        net.step()

    avail = net.availability()
    assert avail[victim] == 0
    neighbours = net.graph.nodes[victim].links
    assert all(avail[j] < FULL for j in neighbours), "neighbours must sag"
    # and the dent is local: something far away is untouched
    far = net.seek_node("009")
    assert far not in neighbours and avail[far] == FULL


def test_repair_restores_a_full_battery(net):
    assert net.kill_node("450") is True
    assert net.availability()[net.seek_node("450")] == 0
    assert net.kill_node("450") is False
    assert net.availability()[net.seek_node("450")] == FULL


# --- routing -----------------------------------------------------------

def _carrier(net):
    """Where the single packet currently sits, if anywhere."""
    return next((n for n, nd in net.graph.nodes.items() if nd.iri.target), None)


def test_a_packet_walks_to_its_destination_and_is_consumed(net):
    src, dst = "900", "009"
    net.transmit(src, dst)
    target = net.seek_node(dst)

    seen = []
    for _ in range(40):
        net.step()
        here = _carrier(net)
        if here is None:
            break
        seen.append(here)
    else:
        pytest.fail("packet never arrived")

    assert seen, "packet should have moved at least once"
    assert net.graph.nodes[seen[-1]].iri.tarbak == target or seen[-1] == target
    assert all(nd.iri.target == 0 for nd in net.graph.nodes.values())


def test_the_packet_gets_closer_on_the_undamaged_grid(net):
    net.transmit("900", "009")
    dst_label = "009"

    def distance_now():
        n = _carrier(net)
        return None if n is None else \
            sum(abs(int(a) - int(b)) for a, b in zip(net.graph.nodes[n].perm, dst_label))

    start = distance_now()
    net.step()
    assert distance_now() < start


def test_routing_detours_around_dead_satellites(net):
    """The whole point of the exercise: because "sideways" and even
    "backwards" carry a non-zero quality, a packet routes around damage
    instead of stalling in front of it.

    Sender "333" sits in the interior with six neighbours, of which exactly
    "234" and "324" lead towards "009".  Killing both leaves no step that gets
    closer, so arriving at all proves the detour.
    """
    blocked = ("234", "324")
    for label in blocked:
        net.kill_node(label)
    net.transmit("333", "009")

    visited = []
    for _ in range(80):
        net.step()
        here = _carrier(net)
        if here is None:
            break
        visited.append(net.graph.nodes[here].perm)
    else:
        pytest.fail("packet never arrived despite an available detour")

    assert not set(visited) & set(blocked)
    assert visited, "packet should have moved"


def test_only_one_packet_per_node(net):
    """BestMove avoids neighbours that already hold something, which is the
    entire collision handling -- the original had no packet storage."""
    net.transmit("900", "009")
    net.step()
    net.transmit("090", "009")
    for _ in range(20):
        net.step()
        holders = [n for n, nd in net.graph.nodes.items() if nd.iri.target]
        assert len(holders) <= 2
        for n in holders:
            assert net.graph.nodes[n].iri.message_num != 0


def test_destination_is_marked_blue_and_carrier_takes_the_message_colour(net):
    net.transmit("900", "009")
    assert net.graph.nodes[net.seek_node("009")].color == BLUE
    assert net.graph.nodes[net.seek_node("900")].color == RED
    net.step()
    carrier = _carrier(net)
    assert net.graph.nodes[carrier].color == RED


def test_forwarding_discharges_the_node(net):
    net.transmit("900", "009")
    net.step()
    carrier = _carrier(net)
    # the sender forwarded, so it paid the 80% discharge
    assert net.availability()[net.seek_node("900")] < FULL
    assert carrier != net.seek_node("900")


# --- repeated senders --------------------------------------------------

def test_a_repeating_sender_keeps_its_own_colour(net):
    net.transmit("900", "009", repeat=3)
    src = net.graph.nodes[net.seek_node("900")]
    assert src.iri.sender_repeat == 3
    assert src.iri.sender_color not in (BLUE, YELLOW, 0)
    assert src.color == src.iri.sender_color


def test_repeat_injects_one_packet_per_call_until_exhausted(net):
    net.transmit("900", "009", repeat=2)
    src = net.graph.nodes[net.seek_node("900")]
    for _ in range(30):
        net.step()
        if src.iri.target == 0:
            break
    assert net.repeat_all() == 1
    assert src.iri.sender_repeat == 1


def test_message_numbers_cycle_and_survive_a_reset(net):
    """Reset clears the network but deliberately not the message counter."""
    assert net.transmit("900", "009") == 1
    net.reset()
    assert net.transmit("900", "009") == 2
    net.message_number = 100
    net.reset()
    assert net.transmit("900", "009") == 1


def test_reset_clears_traffic_and_damage(net):
    net.kill_node("450")
    net.transmit("900", "009", repeat=2)
    net.reset()
    assert set(net.availability().values()) == {FULL}
    assert all(nd.iri.target == 0 and nd.iri.sender_repeat == 0
               for nd in net.graph.nodes.values())
    assert all(nd.color == YELLOW for nd in net.graph.nodes.values())


# --- the original's defects, reported rather than hidden ---------------

def test_a_sender_whose_target_died_is_reported_as_stuck(net):
    """Repeat skips such a sender without decrementing, and there is no
    timeout -- so it waits forever, silently, in the original."""
    net.transmit("900", "009", repeat=5)
    for _ in range(30):
        net.step()
        if net.graph.nodes[net.seek_node("900")].iri.target == 0:
            break
    net.kill_node("009")
    assert net.repeat_all() == 0
    assert net.seek_node("900") in net.stuck_senders()


def test_killing_a_carrier_orphans_its_packet(net):
    """The packet is lost and target stays set, so the node blocks the
    collision check for good."""
    net.transmit("900", "009")
    net.step()
    carrier = _carrier(net)
    net.kill_node(net.graph.nodes[carrier].perm)
    net.step()
    assert carrier in net.orphaned_packets()


# --- input handling ----------------------------------------------------

def test_unknown_labels_are_refused_with_an_explanation(net):
    with pytest.raises(NodeNotFound) as exc:
        net.kill_node("123")            # digits sum to 6, not 9
    assert "three digits summing to 9" in str(exc.value)
    with pytest.raises(NodeNotFound):
        net.transmit("900", "123")


def test_a_dead_satellite_cannot_send_or_receive(net):
    """"11.07.92 : don't allow for target to be a broken node" -- enforced as
    an error instead of as silence."""
    net.kill_node("009")
    with pytest.raises(ProgramStateError) as exc:
        net.transmit("900", "009")
    assert "target" in str(exc.value)
    with pytest.raises(ProgramStateError) as exc:
        net.transmit("009", "900")
    assert "sender" in str(exc.value)


def test_typed_numbers_are_labels_not_indices():
    """The interactive commands read what is written on screen."""
    assert Iridium.num_to_label(270) == "270"
    assert Iridium.num_to_label(9) == "009"
