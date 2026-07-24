"""The main loop and menu state of polytop.mod, without a UI attached."""

import pytest

from permuto import ProgramStateError
from permuto.core import layout
from permuto.core.pm import PM
from permuto.session import (
    Mode,
    NameMode,
    Program,
    Session,
    new_permutograph_session,
)


@pytest.fixture
def polytop():
    """A .nod-style session: a finished graph, no permutation strings."""
    from permuto.core import Graph
    return Session(graph=Graph.build("1234", ["12", "+", "23", "+", "34"],
                                     seed=1))


@pytest.fixture
def permuto():
    return new_permutograph_session()


# --- startup state -----------------------------------------------------

def test_the_program_starts_in_single_step(polytop):
    """Running is False at startup, so every iteration waits for a key and any
    unbound key advances one step.  Getting this wrong makes the port feel
    completely different from the original."""
    assert polytop.single_stepping
    assert (polytop.calculating, polytop.spinning, polytop.hurry_up) == \
        (True, True, False)
    assert polytop.algorithm == "rubber"
    assert polytop.name_mode == NameMode.NONE


# --- the label modes ---------------------------------------------------

def test_perm_labels_are_skipped_without_permutation_strings(polytop):
    """"have no perm strings" -- outside permutograph mode mode 2 is useless
    and the original cycles straight past it."""
    seen = [polytop.cycle_name_mode() for _ in range(6)]
    assert NameMode.PERM not in seen
    assert seen[:3] == [NameMode.NUMBER, NameMode.DISPLAY, NameMode.NONE]


def test_perm_labels_are_offered_in_permutograph_mode(permuto):
    seen = [permuto.cycle_name_mode() for _ in range(4)]
    assert seen == [NameMode.NUMBER, NameMode.PERM, NameMode.DISPLAY,
                    NameMode.NONE]


# --- the status lines --------------------------------------------------

def test_menu_line_shows_the_toggles_and_hides_edit_outside_permuto(polytop):
    assert polytop.menu_line() == (
        "(A)lgo  (C)alc T  (R)un F  (H)urry F  (F)ile  (S)pin T"
        "  (N)ame  (P)rog")
    polytop.calculating = False
    polytop.running = True
    assert "(C)alc F" in polytop.menu_line()
    assert "(R)un T" in polytop.menu_line()


def test_edit_appears_only_with_an_operator_table(permuto, polytop):
    assert "(E)dit" in permuto.menu_line()
    assert "(E)dit" not in polytop.menu_line()


def test_status_line_reports_iteration_dimension_and_algorithm(polytop):
    assert polytop.status_line().startswith(" iter=0 dim=8 nodes=24  A=Rubber")
    polytop.next_algorithm()
    assert "A=Rubber2" in polytop.status_line()


# --- the loop's subtleties --------------------------------------------

def test_hurry_up_suppresses_spinning_only_while_calculating(polytop, monkeypatch):
    """"IF Spinning AND (NOT HurryUp OR NOT Calculating)" -- HurryUp is a
    "compute fast, look seldom" switch, so it stops the decorative rotation
    only when there is computing to get on with."""
    spins = []
    monkeypatch.setattr(layout, "spin", lambda g: spins.append(1))

    polytop.hurry_up = True
    polytop.calculating = True
    polytop.tick()
    assert spins == [], "should not spin while hurrying and calculating"

    polytop.calculating = False
    polytop.tick()
    assert spins == [1], "with nothing to compute, it spins again"


def test_hurry_up_limits_redraws_to_the_checkpoints(polytop):
    """Without HurryUp every iteration redraws; with it, only the every-25th
    checkpoints do."""
    assert all(polytop.tick() for _ in range(5))

    polytop.hurry_up = True
    polytop.iteration = 1
    redraws = [polytop.tick() for _ in range(30)]
    assert sum(redraws) < 5, "hurrying must not redraw every frame"
    assert any(redraws), "but it must still redraw at the checkpoints"


def test_dimensions_are_only_reconsidered_at_the_checkpoints(polytop):
    """The shrink test runs behind `Changed`, which is set every 25th
    iteration -- so a graph cannot shed two dimensions in consecutive ticks."""
    polytop.hurry_up = True
    polytop.iteration = 1
    before = polytop.graph.dimensions
    polytop.tick()
    assert polytop.graph.dimensions == before


def test_a_geodesic_dome_still_falls_from_8d_to_3d():
    """The cadence must not break the actual behaviour.  A frequency-2 dome is
    a genuinely 3-D object, and relaxing it from 8-D through the session loop
    must still let it "fall" all the way down.

    Note this exercises three ported pieces at once: our own geodesic
    generator, PCalc, and the main loop's shrink checkpoints.
    """
    from permuto.gen import geodesic

    g = geodesic(2)
    g.set_dimensions(8)
    g.random_init(1)
    session = Session(graph=g)
    for _ in range(900):
        session.tick()
    assert g.dimensions == 3


# --- programs ----------------------------------------------------------

def test_parsum_refuses_to_run_before_spa(polytop):
    """The original printed "Must run SPA before PARSUM" and waited for a key;
    we raise it so the UI can say the same thing."""
    with pytest.raises(ProgramStateError) as exc:
        polytop.start_par_sum()
    assert "Must run SPA before PARSUM" in str(exc.value)


def test_spa_runs_to_completion_and_then_idles(polytop):
    polytop.start_spa(1)
    assert polytop.program is Program.SPA
    assert polytop.name_mode == NameMode.DISPLAY
    for _ in range(200):
        polytop.tick()
        if not polytop.program_mode:
            break
    else:
        pytest.fail("SPA never finished")
    assert polytop.program is Program.IDLE
    assert polytop.start_par_sum() is None      # now it is allowed


def test_spa_from_a_nonexistent_node_is_refused(polytop):
    with pytest.raises(ProgramStateError):
        polytop.start_spa(999)


def test_spta_reports_what_the_original_said(polytop):
    with pytest.raises(ProgramStateError) as exc:
        polytop.start_spta()
    assert "not yet available" in str(exc.value)


# --- editing -----------------------------------------------------------

def test_rebuilding_with_the_same_base_keeps_the_picture(permuto):
    """EdPermuto: same base -> incremental, "a nice move from one contexture
    to another"; the iteration counter restarts either way."""
    for _ in range(10):
        permuto.tick()
    before = {n: list(nd.pos) for n, nd in permuto.graph.nodes.items()}
    old_graph = permuto.graph

    permuto.pm.set_cycle(4, 1, "14")
    permuto.rebuild_permutograph(base_changed=False)

    assert permuto.graph is old_graph
    assert permuto.iteration == 0
    assert all(permuto.graph.nodes[n].pos != [0] * 8 for n in before)


def test_rebuilding_with_a_new_base_starts_over(permuto):
    permuto.pm.set_base("123")
    permuto.rebuild_permutograph(base_changed=True)
    assert permuto.graph.nnodes == 6
    assert permuto.iteration == 0


def test_editing_needs_an_operator_table(polytop):
    with pytest.raises(ProgramStateError):
        polytop.rebuild_permutograph(base_changed=False)


def test_permutograph_mode_starts_from_pms_own_defaults(permuto):
    """"/PG" starts with base 1234 and operators 12/23/34 -- the 24-node pgl4."""
    assert permuto.mode is Mode.PERMUTO
    assert permuto.pm.base == "1234"
    assert permuto.graph.nnodes == 24
