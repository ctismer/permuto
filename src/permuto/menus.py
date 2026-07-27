"""What the menus are: which key does what, and how the line reads.

``polytop.mod`` wrote its menu line with ``IO.WrStr`` and then read the key in
a ``CASE`` a hundred lines further down, so the line and the keys were two
unrelated pieces of text that happened to agree.  The port had inherited that:
the wording lived in :mod:`permuto.session`, the behaviour in an ``elif`` chain
in the widget, and nothing tied them together.  Here they are one table.

The tables are UI-free on purpose -- they name keys, not Qt key codes, so the
frontend's whole job is to turn an event into a character or a :class:`Key` and
ask which action that is.  A later web frontend inherits the menus instead of
retyping them.

Two menu lines are literal 1995 strings (:data:`FILE_MENU`,
:data:`PROGRAM_MENU`, :data:`IRIDIUM_MENU`) because their wording does not
decompose into one phrase per key -- "Kill/Repair (N)ode / (L)ine" covers two.
The main line is built from the table, because it interpolates state.  Either
way :func:`Menu.unadvertised` names the keys that work without being offered,
and a test holds the two halves together.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class Key(Enum):
    """A key that types no character, named once so a table can mention it.

    The frontend maps its own key codes onto these; nothing below this line
    knows what Qt calls them.
    """

    ESCAPE = "escape"
    ENTER = "enter"
    SPACE = "space"
    BACKSPACE = "backspace"
    UP = "up"
    DOWN = "down"
    HOME = "home"
    END = "end"


# ---------------------------------------------------------------- actions

class MainAction(Enum):
    """The main menu -- ``polytop.mod``'s outermost ``CASE``."""

    ALGORITHM = "algorithm"        # (A)lgo: the next relaxation algorithm
    CALCULATING = "calculating"
    RUNNING = "running"
    HURRY = "hurry"
    SPINNING = "spinning"
    NAME_MODE = "name mode"        # (N)ame: what is written in the balls
    FILE_MENU = "file menu"
    PROGRAM_MENU = "program menu"
    EDIT = "edit"                  # only in permutograph mode
    QUIT = "quit"                  # ESC, and it asks first
    STEP = "step"                  # what every other key does: one iteration


class FileAction(Enum):
    """The (F)ile submenu."""

    QUIT = "quit"
    POSTSCRIPT = "postscript"
    LOAD = "load"
    SAVE = "save"


class ProgramAction(Enum):
    """The (P)rogram submenu, and what a node number typed into it is for.

    Five entries ask for a node number first (``UserIO.ReadInt``) and carry
    what to ask and what the answer will be used for; two of those five then
    want a second node, picked from the first one's neighbours
    (``UserIO.SelectCard``), and carry that wording too.  The rest act at once.

    Keeping all of it here rather than in the widget means the prompts are
    testable without a display, and that this enum is the whole answer to
    "what can the program menu do" -- it used to be split between an ``elif``
    chain and a second enum listing the same five actions again.
    """

    KILL = ("kill", "Node=", "kill/repair", "")
    BREAK = ("break", "Node 1=", "break/repair a line",
             "select the other end")
    COLLAPSE = ("collapse", "Collapse node=", "collapse",
                "select the node to collapse onto")
    UNCOLLAPSE = ("uncollapse", "Uncollapse node=", "uncollapse", "")
    SPA = ("spa", "StartNode=", "run SPA from", "")
    SPTA = ("spta", "", "", "")
    PARSUM = ("parsum", "", "", "")
    LEAVE = ("leave", "", "", "")            # ESC: back to the main menu

    # _value_ must be set here, not in __init__: the by-value lookup map is
    # filled from what was assigned, so ProgramAction("kill") would otherwise
    # raise (the same trap core.layout.Algorithm documents).
    def __new__(cls, value: str, prompt: str, purpose: str, second: str):
        self = object.__new__(cls)
        self._value_ = value
        self.prompt = prompt        # what the node prompt says, e.g. "Node 1="
        self.purpose = purpose      # what the number will be used for
        self.second = second        # how to ask for the second node, if any
        return self

    @property
    def asks_for_a_node(self) -> bool:
        return bool(self.prompt)

    @property
    def asks_for_a_second_node(self) -> bool:
        return bool(self.second)


class IridiumAction(Enum):
    """The ``/I`` mode's keys -- SIMONE had one menu and no submenus.

    Two of them collect numbers first and carry the fields they ask for;
    ``TRANSMIT`` wants three, which is the whole reason a prompt has to tell
    "this field is done" from "the prompt is done".
    """

    KILL = ("kill", ("Node",))
    TRANSMIT = ("transmit", ("Node1", "Node2", "Repeat"))
    STEP = ("step", ())
    REPEAT = ("repeat", ())
    CLEAR = ("clear", ())
    QUIT = ("quit", ())

    def __new__(cls, value: str, fields: tuple[str, ...]):
        self = object.__new__(cls)
        self._value_ = value
        self.fields = fields
        return self

    @property
    def asks_for_numbers(self) -> bool:
        return bool(self.fields)


# ---------------------------------------------------------------- the table

@dataclass(frozen=True)
class Binding:
    """One key of one menu.

    *label* is how the menu line names it; an empty label means the key works
    but is not offered, which the original did in two places -- then *note*
    says why, with the line of ``polytop.mod`` that proves it was deliberate.
    *flag* names the attribute whose T/F follows the label.  *when* limits the
    entry to a mode ("permuto"), as ``(E)dit`` was.
    """

    key: str | Key
    action: Enum
    label: str = ""
    flag: str = ""
    when: str = ""
    note: str = ""

    @property
    def advertised(self) -> bool:
        return bool(self.label)


class Menu:
    """A set of bindings that both answers keys and writes its own line."""

    def __init__(self, name: str, bindings: Sequence[Binding],
                 text: str = ""):
        self.name = name
        self.bindings: tuple[Binding, ...] = tuple(bindings)
        self.text = text                    # the 1995 line, where it is literal
        self._by_char: dict[str, Binding] = {
            b.key.lower(): b for b in self.bindings if isinstance(b.key, str)}
        self._by_key: dict[Key, Binding] = {
            b.key: b for b in self.bindings if isinstance(b.key, Key)}

    # -- looking a key up ------------------------------------------
    def binding(self, char: str = "", key: Key | None = None,
                *, permuto: bool = True) -> Binding | None:
        """The binding for a keystroke, or None if this menu ignores it."""
        found = self._by_key.get(key) if key is not None else None
        if found is None and char:
            found = self._by_char.get(char.lower())
        if found is not None and found.when == "permuto" and not permuto:
            return None                     # (E)dit does not exist in polytop
        return found

    def action(self, char: str = "", key: Key | None = None,
               *, permuto: bool = True) -> Enum | None:
        found = self.binding(char, key, permuto=permuto)
        return found.action if found is not None else None

    # -- writing itself out ----------------------------------------
    def line(self, state=None, *, permuto: bool = True) -> str:
        """The menu line, exactly as the original printed it.

        Where the wording was one phrase across several keys it is kept
        literally; otherwise it is built from the labels, so a key added to the
        table shows up on screen without anyone editing a string.
        """
        if self.text:
            return self.text
        parts = []
        for b in self.bindings:
            if not b.advertised or (b.when == "permuto" and not permuto):
                continue
            flag = ""
            if b.flag:
                flag = " T" if getattr(state, b.flag) else " F"
            parts.append(b.label + flag)
        return "  ".join(parts)

    def unadvertised(self) -> tuple[Binding, ...]:
        """The keys that work without being offered -- each with its reason."""
        return tuple(b for b in self.bindings if not b.advertised)


# ---------------------------------------------------------------- the menus

#: polytop.mod:372-392 -- built, because the flags come from the session
MAIN_MENU = Menu("main", [
    Binding("a", MainAction.ALGORITHM, "(A)lgo"),
    Binding("c", MainAction.CALCULATING, "(C)alc", flag="calculating"),
    Binding("r", MainAction.RUNNING, "(R)un", flag="running"),
    Binding("h", MainAction.HURRY, "(H)urry", flag="hurry_up"),
    Binding("f", MainAction.FILE_MENU, "(F)ile"),
    Binding("s", MainAction.SPINNING, "(S)pin", flag="spinning"),
    Binding("n", MainAction.NAME_MODE, "(N)ame"),
    Binding("p", MainAction.PROGRAM_MENU, "(P)rog"),
    # the trailing space is the original's, and the line ends on it
    Binding("e", MainAction.EDIT, "(E)dit ", when="permuto"),
    Binding(Key.ESCAPE, MainAction.QUIT,
            note="ESC asks the exit question; the line never said so "
                 "(polytop.mod:466)"),
])

#: polytop.mod:439
FILE_MENU = Menu("file", [
    Binding("q", FileAction.QUIT, "(Q)uit"),
    Binding("o", FileAction.POSTSCRIPT, "(O)utput"),
    Binding("l", FileAction.LOAD, "(L)oad"),
    Binding("s", FileAction.SAVE, "(S)ave"),
    Binding(Key.ESCAPE, FileAction.QUIT,
            note="ESC leaves the file menu the way (Q)uit does -- both ask"),
], text="(Q)uit  (O)utput  (L)oad  (S)ave")

#: polytop.mod:467 -- and :498/:508, which is where (C)ollapse and
#: (U)ncollapse are handled although the line above never offers them
PROGRAM_MENU = Menu("program", [
    Binding("n", ProgramAction.KILL, "Kill/Repair (N)ode"),
    Binding("l", ProgramAction.BREAK, "(L)ine"),
    Binding("c", ProgramAction.COLLAPSE,
            note="the 1995 menu line did not offer it either (polytop.mod:498)"),
    Binding("u", ProgramAction.UNCOLLAPSE,
            note="likewise unoffered and working (polytop.mod:508)"),
    Binding("s", ProgramAction.SPA, "run (S)PA"),
    Binding("t", ProgramAction.SPTA, "SP(T)A"),
    Binding("p", ProgramAction.PARSUM, "(P)ARSUM"),
    Binding(Key.ESCAPE, ProgramAction.LEAVE,
            note="ESC goes back to the main menu"),
], text="Kill/Repair (N)ode / (L)ine   run (S)PA  SP(T)A  (P)ARSUM")

#: polytop.mod:749
IRIDIUM_MENU = Menu("iridium", [
    Binding("k", IridiumAction.KILL, "Kill"),
    Binding("t", IridiumAction.TRANSMIT, "Transmit"),
    Binding("s", IridiumAction.STEP, "Step"),
    Binding("r", IridiumAction.REPEAT, "Repeat"),
    Binding("c", IridiumAction.CLEAR, "Clear"),
    Binding("q", IridiumAction.QUIT, "Quit"),
    Binding(" ", IridiumAction.STEP,
            note="space steps as well as S -- held down, it queues steps"),
    Binding(Key.SPACE, IridiumAction.STEP,
            note="and so does the space key by code, for keyboards that send "
                 "no character"),
    Binding(Key.ESCAPE, IridiumAction.QUIT,
            note="ESC asks the exit question, as (Q)uit does"),
], text="Kill  Transmit  Step  Repeat  Clear      Quit")
