"""The main loop and menu state of ``polytop.mod``, without any UI.

This is the layer between the domain core and a frontend: it owns the modes,
the toggles and the iteration cadence, and it produces the two status lines as
text.  Keeping it Qt-free means the whole interaction model is testable, and a
later web frontend inherits it rather than reimplementing it.

The original's cadence, reproduced here::

    Backup -> Contract(alg) -> Squeeze -> [Punish if Rubber]
           -> [Spin if spinning and dim>=3 and (not hurry or not calculating)]
           -> Normalize -> [every 25 iterations: while CanShrink: dim -= 1]

Two details that are easy to miss and change the feel:

* ``Running`` starts **False**, so the program single-steps: every iteration
  waits for a keypress, and any unbound key advances it by one.
* ``HurryUp`` suppresses spinning only while calculating, and limits redraws to
  the every-25th-iteration checkpoints -- it is a "compute fast, look seldom"
  switch, not a speed multiplier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .core import layout, spa
from .core.graph import Graph
from .core.pm import PM
from .errors import ProgramStateError
from .menus import (FILE_MENU, MAIN_MENU, PROGRAM_MENU, Menu,
                    ProgramAction)

DIMENSION_CHECK_INTERVAL = 25   # "IF Iteration MOD 25 = 0 THEN Changed := TRUE"

EXIT_QUESTION = "Do You want to exit? (Y/N)"   # UserIO, capital You and all


def confirms_exit(text: str = "", *, enter: bool = False) -> bool:
    """``UserIO.UserWantsToExit`` -- anything else keeps the program running.

    The original accepted three languages' yes (and the author's own habit of
    just hitting Enter), which is worth keeping: it is the only place the
    program ever asked the user anything twice.
    """
    return enter or text[:1].lower() in ("y", "j", "o")   # English, Deutsch, France


class Mode(Enum):
    """How the program was started -- one parameter, three worlds."""

    POLYTOP = "polytop"      # a finished graph from a .nod file
    PERMUTO = "permuto"      # /PG: build permutographs interactively
    IRIDIUM = "iridium"      # /I: the satellite simulation


class NameMode:
    """What to write inside the node balls: ``0=none 1=node# 2=perm 3=display``."""

    NONE, NUMBER, PERM, DISPLAY = 0, 1, 2, 3
    COUNT = 4


class Program(Enum):
    """``PmProgs`` selector."""

    IDLE = "idle"
    SPA = "spa"
    PARSUM = "parsum"
    SPTA = "spta"            # Gerhard's algorithm; the spec never arrived, so
                             # the original only ever said "not yet available"


class UiMode(Enum):
    """Which menu the keyboard is talking to.

    The original needed no such state: DOS read its keys inside whichever menu
    loop was running, so the menu *was* the call stack.  An event-driven
    frontend has to remember it instead, and both status lines and the forced
    node numbers read it back -- which is why it lives here and not in the
    widget.
    """

    MAIN = "main"
    FILE = "file"
    PROGRAM = "program"
    EDIT = "edit"
    PROMPT = "prompt"        # typing a file name or a node number
    SELECT = "select"        # SelectCard: picking a neighbour
    CONFIRM = "confirm"      # the exit question


class PromptKind(Enum):
    """What the text prompt is collecting, which menu asked for it, and what it
    says while it asks.

    The menu matters because a prompt keeps its parent's line on screen: you
    typed a file name under ``(Q)uit (O)utput (L)oad (S)ave``, and that is what
    you go on seeing while you type.  ``NODE`` has no wording of its own -- the
    :class:`~permuto.menus.ProgramAction` that asked supplies it, because
    "Node 1=" and "Uncollapse node=" are the same kind of prompt.
    """

    menu: UiMode         # the menu whose line stays on screen while typing
    label: str           # what the prompt says, if it has wording of its own

    PS = ("ps", UiMode.FILE, "PostScript out = ")
    SAVE = ("save", UiMode.FILE, "Save .pms = ")
    LOAD = ("load", UiMode.FILE, "Load (.pms/.ply) = ")
    NODE = ("node", UiMode.PROGRAM, "")     # a node number (``UserIO.ReadInt``)

    def __new__(cls, value: str, menu: UiMode, label: str):
        self = object.__new__(cls)
        self._value_ = value
        self.menu = menu
        self.label = label
        return self


EDIT_MENU_LINE = ("editing operators: digits, arrows move, "
                  "Ctrl-Home base, Ctrl-End last, Enter/Esc leave")


#: which menu each keyboard mode is talking to; anything else gets the main one
#: Menus of different action types, so what is common to them is a Menu of
#: *some* action -- all this map is asked for is the line to print.
MENU_FOR_MODE: dict[UiMode, Menu[Any]] = {
    UiMode.MAIN: MAIN_MENU,
    UiMode.FILE: FILE_MENU,
    UiMode.PROGRAM: PROGRAM_MENU,
    UiMode.SELECT: PROGRAM_MENU}               # picking the second node


@dataclass
class Selection:
    """``UserIO.SelectCard``: cycling a node's neighbours to pick one.

    The DOS program had no mouse, so the second node of a line-break or a
    collapse is chosen by walking the link list.
    """

    node: int
    action: ProgramAction
    items: list[int] = field(default_factory=list)
    pos: int = 0

    @property
    def current(self) -> int:
        return self.items[self.pos]

    def advance(self) -> None:
        self.pos = (self.pos + 1) % len(self.items)


@dataclass
class Session:
    """The running program: a graph, how it is being computed, and what is shown."""

    graph: Graph
    mode: Mode = Mode.POLYTOP
    pm: PM | None = None

    # PCalc / main loop state, with the original's startup values
    algorithm_index: int = 0
    calculating: bool = True
    running: bool = False          # !!! single-step is the start state
    spinning: bool = True
    hurry_up: bool = False
    name_mode: int = NameMode.NONE

    program_mode: bool = False
    program: Program = Program.IDLE
    start_node: int = 1

    iteration: int = 0
    changed: bool = True
    _spa_has_run: bool = False

    load_warnings: list[str] = field(default_factory=list)
    """Non-fatal notes from loading this session (e.g. a truncated file), for
    the viewer to show in its status line instead of printing to the console."""

    def __post_init__(self) -> None:
        # A session always starts with a picture that fills the view: a graph
        # read back from a file carries whatever fixed-point scale it was saved
        # at (a .ply from 1995 used NORM = 4096), which would otherwise show up
        # microscopic until the relaxation has renormalized it.
        layout.frame(self.graph)

    # -- derived ---------------------------------------------------------
    @property
    def algorithm(self) -> "layout.Algorithm":
        return layout.ALGORITHMS[self.algorithm_index]

    @property
    def permuto(self) -> bool:
        """Whether the permutograph-specific commands are available."""
        return self.mode is Mode.PERMUTO

    @property
    def single_stepping(self) -> bool:
        """True while every iteration waits for a keypress."""
        return not self.running

    # -- the main loop ---------------------------------------------------
    def tick(self) -> bool:
        """Advance one iteration; returns whether the picture should be redrawn.

        Mirrors the body of ``polytop.mod``'s loop, including the order of the
        program step: after the display, before the menu, "to show the initial
        state before starting".
        """
        g = self.graph
        layout.backup(g)
        if self.calculating:
            layout.contract(g, self.algorithm)
            layout.squeeze(g)
            if self.algorithm is layout.Algorithm.RUBBER:
                layout.punish(g)

        if self.spinning and g.dimensions >= 3 \
                and (not self.hurry_up or not self.calculating):
            layout.spin(g)

        layout.normalize(g)
        if self.iteration == 0:
            layout.backup(g)        # first time round, old := the cleaned pos

        if self.iteration % DIMENSION_CHECK_INTERVAL == 0:
            self.changed = True

        redraw = self.changed or not self.hurry_up

        if self.changed:
            self.changed = False
            while g.dimensions > 1 and layout.can_shrink(g):
                g.set_dimensions(g.dimensions - 1)
                self.changed = True

        self.iteration += 1
        self._advance_program()
        return redraw

    def advance_frame(self) -> None:
        """One frame's worth of relaxation, as the frontend's clock asks for it.

        Normally one iteration per frame.  With HurryUp the original traded
        looking for computing -- it drew only at the 25-iteration checkpoints
        and skipped the spin while calculating (``polytop.mod:299``) -- so here
        it keeps iterating until :meth:`tick` asks for a redraw.  Without this
        the switch only costs the rotation and buys nothing.
        """
        if not self.hurry_up:
            self.tick()
            return
        for _ in range(DIMENSION_CHECK_INTERVAL):   # at most one checkpoint
            if self.tick():
                break

    def _advance_program(self) -> None:
        if not self.program_mode:
            return
        if self.program is Program.SPA:
            self.program_mode = spa.shortest_path(self.graph)
        elif self.program is Program.PARSUM:
            self.program_mode = spa.par_sum(self.graph)
        if not self.program_mode:
            self.program = Program.IDLE

    # -- toggles ---------------------------------------------------------
    def next_algorithm(self) -> "layout.Algorithm":
        self.algorithm_index = (self.algorithm_index + 1) % len(layout.ALGORITHMS)
        self.changed = True
        return self.algorithm

    def cycle_name_mode(self) -> int:
        """Next label mode, skipping the ones that have nothing to show.

        ``REPEAT NameMode := (NameMode+1) MOD 4 UNTIL Permuto OR (NameMode # 2)``
        -- outside permutograph mode the nodes "have no perm strings".  The
        port applies the same idea to the display mode, which is `state.display`
        and therefore all zeroes until SPA or ParSum has filled it in.
        """
        while True:
            self.name_mode = (self.name_mode + 1) % NameMode.COUNT
            if self.name_mode == NameMode.PERM and not self.permuto:
                continue
            if self.name_mode == NameMode.DISPLAY and not self._spa_has_run:
                continue
            break
        self.changed = True
        return self.name_mode

    # -- programs --------------------------------------------------------
    def start_spa(self, node: int) -> None:
        """Run the shortest-path wave from *node*."""
        if node not in self.graph.nodes:
            raise ProgramStateError(
                f"node {node} does not exist (1..{self.graph.nnodes})")
        self.start_node = node
        spa.init_spa(self.graph, node)
        self.program_mode = True
        self.program = Program.SPA
        self.name_mode = NameMode.DISPLAY
        self._spa_has_run = True
        self.changed = True

    def start_par_sum(self) -> None:
        """Run ParSum, which needs the distances a previous SPA left behind."""
        if not spa.init_par_sum(self.graph):
            raise ProgramStateError("Must run SPA before PARSUM")
        self.program_mode = True
        self.program = Program.PARSUM
        self.name_mode = NameMode.DISPLAY
        self.changed = True

    def start_spta(self) -> None:
        """The original never finished this one."""
        raise ProgramStateError("sorry, SPTA not yet available")

    def stop_program(self) -> None:
        self.program_mode = False
        self.program = Program.IDLE
        self.changed = True

    # -- the program menu's edits on the graph ---------------------------
    def kill_node(self, node: int) -> bool:
        """``Kill/Repair (N)ode`` -- toggle a node dead; True if it is now."""
        state = self.graph.nodes[node].state
        state.dead = not state.dead
        return state.dead

    def toggle_line(self, n1: int, n2: int) -> None:
        """``Kill/Repair (L)ine`` -- mark the edge broken, or mend it.

        Both ends carry their own mark, indexed by their own link number, so
        the edge has to be found from each side.
        """
        for a, b in ((n1, n2), (n2, n1)):
            k = self.graph.find_link(a, b)
            if k:
                link = self.graph.nodes[a].links[k - 1]
                link.broken = not link.broken

    def _table(self) -> PM:
        """The operator table, or a refusal: a ``.nod`` graph has none, and the
        program menu offers its actions all the same."""
        if self.pm is None:
            raise ProgramStateError(
                "this graph has no operator table -- collapsing needs "
                "permutograph mode, where the edges can be rebuilt")
        return self.pm

    def collapse(self, n1: int, n2: int) -> int:
        """``(C)ollapse`` -- merge *n1* onto *n2*; returns the edges lost."""
        return self._table().collapse(self.graph, n1, n2)

    def uncollapse(self, node: int) -> None:
        """``(U)ncollapse`` -- drop a node's edges and restore the canonical ones."""
        self._table().uncollapse(self.graph, node)

    # -- the two status lines --------------------------------------------
    def menu_line(self) -> str:
        """The top line, built from the menu table (``menus.MAIN_MENU``) so
        that what is offered and what a key does cannot drift apart."""
        return MAIN_MENU.line(self, permuto=self.permuto)

    def status_line(self) -> str:
        """The bottom line: ``iter=N dim=D nodes=N  A=Alg``.

        polytop.mod:354 wrote it as ``" iter="``, one column right of the menu
        line above it (:371, same column 1).  That was the original being
        careless, not deliberate, so the port lines them up.
        """
        return (f"iter={self.iteration} dim={self.graph.dimensions}"
                f" nodes={self.graph.nnodes}"
                f"  A={self.algorithm.label}")

    def file_menu_line(self) -> str:
        return FILE_MENU.line(self)

    def program_menu_line(self) -> str:
        return PROGRAM_MENU.line(self)

    def top_line(self, ui_mode: "UiMode",
                 prompt_kind: "PromptKind | None" = None) -> str:
        """The line above the picture: the menu the keyboard is in.

        A prompt shows the menu it was opened from, so typing a file name still
        reads ``(Q)uit (O)utput (L)oad (S)ave``.
        """
        if ui_mode is UiMode.PROMPT and prompt_kind is not None:
            ui_mode = prompt_kind.menu
        if ui_mode is UiMode.EDIT:
            return EDIT_MENU_LINE          # cursor keys, not a key menu
        if ui_mode is UiMode.CONFIRM:
            return EXIT_QUESTION
        return MENU_FOR_MODE.get(ui_mode, MAIN_MENU).line(
            self, permuto=self.permuto)

    def label_mode(self, ui_mode: "UiMode",
                   prompt_kind: "PromptKind | None" = None) -> int:
        """What to write in the balls right now.

        Node numbers are forced on while a node is being chosen, so there is
        always something to read -- the original drew them before the program
        menu regardless of the current name mode.
        """
        picking = ui_mode in (UiMode.PROGRAM, UiMode.SELECT) or \
            (ui_mode is UiMode.PROMPT and prompt_kind is PromptKind.NODE)
        return NameMode.NUMBER if picking else self.name_mode

    # -- editing entry point ---------------------------------------------
    def rebuild_permutograph(self, *, base_changed: bool) -> None:
        """``EdPermuto``'s tail: rebuild after the operator table changed.

        With an unchanged base the positions are kept, "this makes a nice move
        from one contexture to another"; otherwise everything starts over.
        Either way the iteration counter restarts.
        """
        if self.pm is None:
            raise ProgramStateError("no operator table: not in permutograph mode")
        self.pm.drop_invalid_cycles()
        reset = base_changed or self.graph.nnodes == 0
        self.graph = self.pm.new_permutograph(
            None if reset else self.graph, reset=reset)
        self.iteration = 0
        self.changed = True
        self.stop_program()


def new_permutograph_session(base: str = "1234",
                             operators: list[str] | None = None) -> Session:
    """Start in ``/PG`` mode.

    ``operators`` uses the generation-pipeline syntax: cycle tokens with ``+``
    separating one operator from the next, so an operator may be several cycles
    (``12 + 23`` is two operators of one cycle; ``18 27 + 36 45`` is two
    operators of two cycles).  With no operators, PM's own defaults apply --
    base 1234, operators 12/23/34.
    """
    from .gen import operator_groups

    pm = PM(base=base)
    if operators is not None:
        for row in pm.optable:
            for j in range(len(row)):
                row[j] = ""
        for i, group in enumerate(operator_groups(operators)):
            for j, cyc in enumerate(group):
                pm.set_cycle(i + 1, j + 1, cyc)
    return Session(graph=pm.new_permutograph(), mode=Mode.PERMUTO, pm=pm)
