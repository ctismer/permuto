"""The menus as tables: what is offered, what is bound, and what happens.

`polytop.mod` printed its menu line in one place and read the key in a `CASE`
a hundred lines further down, and the port had inherited the split -- the
wording in session.py, the behaviour in an elif chain in the widget.  Nothing
could check that they agreed, and by 2026 they no longer entirely did.

Now one table answers both, so these become questions a test can ask: does
every offered key do something, does every key that does something say so, and
does every action the tables can produce have a handler.
"""

import pytest

from permuto import menus
from permuto.menus import (FILE_MENU, IRIDIUM_MENU, MAIN_MENU, PROGRAM_MENU,
                           FileAction, IridiumAction, Key, MainAction,
                           ProgramAction)
from permuto.session import new_permutograph_session

ALL_MENUS = [MAIN_MENU, FILE_MENU, PROGRAM_MENU, IRIDIUM_MENU]
MENU_IDS = [m.name for m in ALL_MENUS]


def _offered_keys(line: str) -> set:
    """The keys a menu line advertises: every letter inside brackets."""
    return {line[i + 1].lower()
            for i, ch in enumerate(line)
            if ch == "(" and i + 2 < len(line) and line[i + 2] == ")"}


# -- the line and the keys are one thing -----------------------------------

@pytest.mark.parametrize("menu", ALL_MENUS, ids=MENU_IDS)
def test_every_key_a_menu_offers_is_a_key_it_answers(menu):
    """The failure this makes impossible: a line that promises (X) while no
    branch handles it, which is what a hand-written string invites."""
    session = new_permutograph_session()
    for key in _offered_keys(menu.line(session)):
        assert menu.action(key) is not None, \
            f"{menu.name} offers ({key.upper()}) and does nothing with it"


@pytest.mark.parametrize("menu", ALL_MENUS, ids=MENU_IDS)
def test_a_key_that_works_without_being_offered_has_to_say_why(menu):
    """The other direction, and the one that actually bit: the program menu
    has handled (C)ollapse and (U)ncollapse since 1995 without ever offering
    them.  That stays -- but as a note in the table, not as a surprise."""
    for binding in menu.unadvertised():
        assert binding.note, \
            f"{menu.name}: {binding.key} works unannounced and gives no reason"


def test_the_1995_menu_lines_are_reproduced_exactly():
    """polytop.mod:372-392 built the top line piece by piece; :439 and :467
    wrote theirs in one go.  Generated or literal, the text on screen is the
    text the original printed -- the flags included."""
    s = new_permutograph_session()
    s.calculating, s.running, s.hurry_up, s.spinning = True, False, False, True
    assert MAIN_MENU.line(s) == ("(A)lgo  (C)alc T  (R)un F  (H)urry F"
                                 "  (F)ile  (S)pin T  (N)ame  (P)rog"
                                 "  (E)dit ")
    s.calculating, s.spinning = False, False
    s.running, s.hurry_up = True, True
    assert MAIN_MENU.line(s) == ("(A)lgo  (C)alc F  (R)un T  (H)urry T"
                                 "  (F)ile  (S)pin F  (N)ame  (P)rog"
                                 "  (E)dit ")
    assert FILE_MENU.line() == "(Q)uit  (O)utput  (L)oad  (S)ave"
    assert PROGRAM_MENU.line() == ("Kill/Repair (N)ode / (L)ine"
                                   "   run (S)PA  SP(T)A  (P)ARSUM")
    assert IRIDIUM_MENU.line() == "Kill  Transmit  Step  Repeat  Clear      Quit"


def test_edit_is_offered_only_where_it_exists():
    """`IF Permuto THEN IO.WrStr("  (E)dit ")` -- and in polytop mode the key
    falls through to a single step, as any unbound key does."""
    s = new_permutograph_session()
    assert "(E)dit" in MAIN_MENU.line(s, permuto=True)
    assert "(E)dit" not in MAIN_MENU.line(s, permuto=False)
    assert MAIN_MENU.action("e", permuto=True) is MainAction.EDIT
    assert MAIN_MENU.action("e", permuto=False) is None


def test_the_program_menu_hides_exactly_the_two_keys_it_always_did():
    """Named on purpose: a third hidden key should have to be added here."""
    hidden = {b.key for b in PROGRAM_MENU.unadvertised()}
    assert hidden == {"c", "u", Key.ESCAPE}


# -- looking a key up -------------------------------------------------------

def test_keys_are_answered_by_character_or_by_name():
    """A frontend hands over what it has: a character for a letter, a Key for
    ESC.  Nothing below permuto.ui knows what Qt calls either."""
    assert MAIN_MENU.action("a") is MainAction.ALGORITHM
    assert MAIN_MENU.action("A") is MainAction.ALGORITHM      # case-blind
    assert MAIN_MENU.action(key=Key.ESCAPE) is MainAction.QUIT
    assert MAIN_MENU.action("z") is None                      # single-steps
    assert FILE_MENU.action(key=Key.ESCAPE) is FileAction.QUIT
    assert PROGRAM_MENU.action(key=Key.ESCAPE) is ProgramAction.LEAVE
    assert IRIDIUM_MENU.action(" ") is IridiumAction.STEP


# -- what an action carries -------------------------------------------------

def test_the_node_prompts_live_with_the_action_that_asks():
    """"Node 1=" and "select the other end" are one flow, so they are one
    enum member -- the widget used to spell both out at the call site."""
    asking = {a for a in ProgramAction if a.asks_for_a_node}
    assert asking == {ProgramAction.KILL, ProgramAction.BREAK,
                      ProgramAction.COLLAPSE, ProgramAction.UNCOLLAPSE,
                      ProgramAction.SPA}
    second = {a for a in ProgramAction if a.asks_for_a_second_node}
    assert second == {ProgramAction.BREAK, ProgramAction.COLLAPSE}
    assert second < asking, "a second node is only ever asked after a first"
    assert ProgramAction.BREAK.prompt == "Node 1="
    assert all(a.purpose for a in asking), "and each says what it is for"


def test_the_iridium_prompts_carry_their_fields():
    """(T)ransmit asks for three, which is why a prompt has to tell "field
    done" from "prompt done" at all."""
    assert IridiumAction.TRANSMIT.fields == ("Node1", "Node2", "Repeat")
    assert IridiumAction.KILL.fields == ("Node",)
    assert not IridiumAction.STEP.asks_for_numbers


def test_a_data_carrying_enum_can_still_be_looked_up_by_value():
    """The trap core.layout.Algorithm documents: with __init__ instead of
    __new__ the by-value map is filled from the tuple, and this raises."""
    assert ProgramAction("kill") is ProgramAction.KILL
    assert IridiumAction("transmit") is IridiumAction.TRANSMIT


# -- every action has a handler ---------------------------------------------
# These reach into the view modules on purpose: the tables there are the other
# half of the tables here, and an action nobody handles is a key that quietly
# does nothing.

def test_every_action_the_menus_can_produce_is_handled():
    pytest.importorskip("PySide6")
    from permuto.ui import iridium_view as iv
    from permuto.ui import permutograph_view as pv

    # the four toggles need no handler: the binding already names the session
    # attribute whose T/F the line shows, and the key flips exactly that one
    toggles = {b.action for b in MAIN_MENU.bindings if b.flag}
    assert set(pv._MAIN_ACTIONS) | toggles == set(MainAction)
    assert not set(pv._MAIN_ACTIONS) & toggles
    assert set(pv._FILE_ACTIONS) == set(FileAction)

    asks = {a for a in ProgramAction if a.asks_for_a_node}
    assert set(pv._PROGRAM_ACTIONS) | asks == set(ProgramAction)
    assert set(pv._NODE_ACTIONS) | set(pv._SECOND_NODE) == asks
    assert set(pv._SECOND_NODE) == {a for a in ProgramAction
                                    if a.asks_for_a_second_node}

    assert set(iv._IRIDIUM_ACTIONS) | set(iv._IRIDIUM_PROMPTS) \
        == set(IridiumAction)
    assert set(iv._IRIDIUM_PROMPTS) == {a for a in IridiumAction
                                        if a.asks_for_numbers}


def test_every_binding_points_at_an_action_of_its_own_menus_kind():
    """One menu, one action type -- so a handler table can be checked for
    completeness against the enum, as the test above does."""
    for menu, kind in ((MAIN_MENU, MainAction), (FILE_MENU, FileAction),
                       (PROGRAM_MENU, ProgramAction),
                       (IRIDIUM_MENU, IridiumAction)):
        for binding in menu.bindings:
            assert isinstance(binding.action, kind), \
                f"{menu.name}: {binding.key} -> {binding.action!r}"


def test_the_menus_stay_ui_free():
    """A web frontend is meant to inherit these tables, so importing them must
    not drag in Qt.  Asked in a fresh interpreter, because this one has long
    since imported PySide6 for the widget tests."""
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src"
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; import permuto.menus;"
         " print('PySide6' in sys.modules or"
         " any(m.startswith('permuto.ui') for m in sys.modules))"],
        capture_output=True, text=True, env={"PYTHONPATH": str(src),
                                             "PATH": ""})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False", "permuto.menus reached into the UI"
