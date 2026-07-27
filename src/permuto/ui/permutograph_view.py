"""The main viewer -- ``polytop.mod`` as a Qt widget.

The interaction model lives in :mod:`permuto.session` (UI-free and tested) and
the menus in :mod:`permuto.menus` (likewise); this widget draws them and feeds
them keystrokes.  What is left here is genuinely Qt: pixels, and the mode the
keyboard is in.

Which key does what is not written down here -- ask the menu tables.  The
program menu's node prompts are on :class:`permuto.menus.ProgramAction`, the
file menu's on :class:`permuto.session.PromptKind`, and everything the tables
name is dispatched through the three ``_..._ACTIONS`` dicts at the foot of this
module.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ..editor import OperatorEditor
from ..errors import PermutoError
from ..formats import save_ps
from ..loader import make_session, session_from_file, write_session
from ..menus import (FILE_MENU, MAIN_MENU, PROGRAM_MENU, FileAction, Key,
                     MainAction, ProgramAction)
from ..session import PromptKind, Selection, UiMode
from . import keys, render
from .base_view import ViewBase
from .keys import exit_confirmed, feed_prompt
from .prompt import FieldPrompt, PromptResult


def load_note(warnings) -> str:
    """The status line for a load that had to be salvaged.

    A truncated session can produce one warning per node, so the line shows the
    first two and counts the rest.
    """
    if not warnings:
        return ""
    note = "; ".join(warnings[:2])
    if len(warnings) > 2:
        note += f" (+{len(warnings) - 2} more)"
    return f"loaded (truncated): {note}"


class PermutographView(ViewBase):
    """The main viewer: the graph, the operator panel and the two menu lines."""

    def __init__(self, name_or_path, seed: int = 1, operators=None):
        ops = list(operators) if operators is not None else None
        session = make_session(name_or_path, seed=seed, operators=ops)
        super().__init__(1000, 860)
        self.spec_name = str(name_or_path)
        self.operators = ops
        self.seed = seed
        self.session = session

        # UI chrome state
        self.ui_mode = UiMode.MAIN
        # a load note (e.g. a truncated session) shows in the status line
        self.message = load_note(session.load_warnings)
        # the ProgramAction waiting for the node number being typed
        self.pending: ProgramAction | None = None
        # an OperatorEditor while UiMode.EDIT, otherwise None
        self.editor: OperatorEditor | None = None
        # which prompt is open, while UiMode.PROMPT
        self.prompt_kind: PromptKind | None = None
        # SelectCard state, while a neighbour is being picked
        self.select: Selection | None = None

        title = self.spec_name if ops is None \
            else f"{self.spec_name} {' '.join(ops)}"
        self.setWindowTitle(f"permuto - {title}")

    @property
    def g(self):
        return self.session.graph

    def _shows_operators(self) -> bool:
        return self.session.permuto and self.session.pm is not None

    def picture_width(self) -> int:
        """How much of the window the graph gets.

        The rest is the operator table, which takes the room its text needs and
        no more -- it used to reserve a flat 260 px whether it was a four-place
        base or empty.  Public because it is what "where is node 5 on screen"
        depends on, and every caller used to re-derive it from that 260.
        """
        if not self._shows_operators():
            return self.width()
        return self.width() - int(
            render.operator_panel_width(self.session.pm, self.height()))

    # -- the clock -------------------------------------------------
    def _on_timer(self):
        # only relax freely while running; single-step waits for a key
        if self.ui_mode is UiMode.MAIN and self.session.running:
            self.session.advance_frame()
        elif self.session.program_mode:
            self.session.tick()      # a running program advances on its own
        self.update()

    # ================= painting ==================================
    def _paint(self, p):
        pic_w = self.picture_width()
        render.paint(self.g, p, pic_w, self.height(),
                     op_colors=True,      # the viewer always colours by operator
                     program=self.session.program_mode,
                     name_mode=self.session.label_mode(self.ui_mode,
                                                       self.prompt_kind))
        if self._shows_operators():
            render.paint_operator_panel(
                self.session.pm, p, pic_w, 60, self.height(),
                active_field=self.editor.field if self.editor else None,
                buffer_text=self.editor.buffer if self.editor else None)
        self._paint_chrome(p)

    def _paint_chrome(self, p):
        self._set_chrome_font(p)

        # top: the menu line for the current UI mode
        p.setPen(QColor(200, 205, 225))
        p.drawText(12, 22, self.session.top_line(self.ui_mode, self.prompt_kind))

        # bottom: the status line, plus the live prompt / message
        p.setPen(QColor(150, 155, 175))
        p.drawText(12, self.height() - 32, self.session.status_line())
        p.setPen(QColor(255, 230, 140))
        if self.ui_mode is UiMode.PROMPT and self.prompt:
            p.drawText(12, self.height() - 14,
                       self.prompt.display()
                       + (f"    {self.message}" if self.message else ""))
        elif self.ui_mode is UiMode.SELECT and self.select:
            p.drawText(12, self.height() - 14,
                       f" neighbour: node {self.select.current}   "
                       f"(space = next, Enter = pick, Esc = cancel)")
        elif self.message:
            p.setPen(QColor(255, 210, 140))
            p.drawText(12, self.height() - 14, self.message)

    # ================= input =====================================
    def keyPressEvent(self, ev):
        self.message = ""
        # every mode must name its handler: an unlisted one is a KeyError here,
        # not a key that silently lands in the main menu
        {UiMode.MAIN: self._main_key,
         UiMode.FILE: self._file_key,
         UiMode.PROGRAM: self._program_key,
         UiMode.EDIT: self._edit_key,
         UiMode.PROMPT: self._prompt_key,
         UiMode.SELECT: self._select_key,
         UiMode.CONFIRM: self._confirm_key}[self.ui_mode](ev)
        self.update()

    def _enter(self, mode: UiMode) -> None:
        """Hand the keyboard to another menu."""
        self.ui_mode = mode

    def _confirm_key(self, ev):
        """Yes closes, anything else goes back to the main menu."""
        if exit_confirmed(ev):
            self.close()
        else:
            self._enter(UiMode.MAIN)

    # -- main menu -------------------------------------------------
    def _main_key(self, ev):
        binding = MAIN_MENU.binding(keys.char(ev), keys.named(ev),
                                    permuto=self.session.permuto)
        if binding is not None and binding.flag:
            # (C)alc (R)un (H)urry (S)pin: the table already names the attribute
            # whose T/F the menu line shows, and the key flips exactly that one
            setattr(self.session, binding.flag,
                    not getattr(self.session, binding.flag))
            return
        action = binding.action if binding is not None else MainAction.STEP
        _MAIN_ACTIONS[action](self)

    def _step(self):
        """What every key the menu does not claim does: one iteration -- but
        only while not running, as the original had it."""
        if not self.session.running:
            self.session.tick()

    # -- file menu -------------------------------------------------
    def _file_key(self, ev):
        action = FILE_MENU.action(keys.char(ev), keys.named(ev))
        if action is not None:
            _FILE_ACTIONS[action](self)

    # -- program menu ----------------------------------------------
    def _program_key(self, ev):
        action = PROGRAM_MENU.action(keys.char(ev), keys.named(ev))
        if action is None:
            return
        if action.asks_for_a_node:
            self._ask_node(action)
        else:
            _PROGRAM_ACTIONS[action](self)

    def _ask_node(self, action: ProgramAction):
        """Ask for a node the original way -- type its number and Enter
        (``UserIO.ReadInt``).  The DOS program had no mouse."""
        self.pending = action
        self._begin_prompt(PromptKind.NODE, action.prompt)
        self.message = f"type a node number and Enter to {action.purpose}"

    def _start_spta(self):
        self._guard(self.session.start_spta)
        self._enter(UiMode.MAIN)     # SPTA only ever says it does not exist

    def _start_par_sum(self):
        if self._guard(self.session.start_par_sum):
            self._enter(UiMode.MAIN)     # a refusal keeps the menu open

    # -- operator editor -------------------------------------------
    def _enter_edit(self):
        self.ui_mode = UiMode.EDIT
        self.editor = OperatorEditor(self.session.pm)

    def _edit_key(self, ev):
        ed = self.editor
        if ev.text().isdigit():
            ed.type_digit(ev.text())
            return
        key = keys.named(ev)
        if key is Key.BACKSPACE:
            ed.backspace()
            return
        where = keys.EDIT_MOVES.get(key)
        leaving = key in (Key.ENTER, Key.ESCAPE)
        if where is None and not leaving:
            return
        error = ed.commit()          # any move or exit commits the field first
        if error:
            self.message = error     # blocking validation: cannot leave
            return
        if leaving:
            self._leave_edit()
        else:
            ed.move(where)

    def _leave_edit(self):
        try:
            self.session.rebuild_permutograph(
                base_changed=self.editor.base_changed)
        except PermutoError as exc:
            self.message = str(exc)
        self._enter(UiMode.MAIN)
        self.editor = None

    # -- text prompt (filenames, node numbers) ---------------------
    def _begin_prompt(self, kind: PromptKind, label: str = ""):
        """Open the prompt *kind* asks for; its own wording unless a caller
        has a better one (a node prompt says what the number is for)."""
        self.ui_mode = UiMode.PROMPT
        self.prompt_kind = kind
        text = (label or kind.label).strip()
        self.prompt = FieldPrompt(text, [(text, kind is PromptKind.NODE)])

    def _prompt_key(self, ev):
        match feed_prompt(self.prompt, ev):
            case PromptResult.CANCEL:
                self.pending = None
                self._enter(UiMode.MAIN)
            case PromptResult.SUBMIT:
                self._run_prompt()
            # TYPING and MORE: keep the prompt open and go on collecting

    def _run_prompt(self):
        text = self.prompt.text()
        if not text:
            return
        if self.prompt_kind is PromptKind.NODE:
            if not text.isdigit() or int(text) not in self.g.nodes:
                self.message = f"no node {text} (1..{self.g.nnodes})"
                self._enter(UiMode.MAIN)
                self.pending = None
                return
            self._apply_pending(int(text))
            return
        try:
            _PROMPT_ACTIONS[self.prompt_kind](self, text)
        except (PermutoError, OSError) as exc:
            self.message = str(exc)
        self._enter(UiMode.MAIN)

    def _write_ps(self, path):
        save_ps(self.g, path)
        self.message = f"wrote {path}"

    def _save_session(self, path):
        return write_session(self.session, path)

    def _report_save(self, path):
        self.message = f"saved {self._save_session(path)}"

    def _load_session(self, path):
        self.session = session_from_file(path)
        self.message = load_note(self.session.load_warnings) \
            or f"loaded {path}"

    # (no mouse: the DOS original was keyboard-only; node picking by click
    #  is deferred to the refactor/extend phase.)

    def _apply_pending(self, node):
        """Act on a node number just entered (``ReadInt`` returned)."""
        action = self.pending
        if action.asks_for_a_second_node:
            self._begin_select(node, action, action.second)
            return
        self._guard(lambda: _NODE_ACTIONS[action](self.session, node))
        self._done_pending()

    def _begin_select(self, node, action, what):
        """Enter SelectCard: cycle *node*'s neighbours with space, Enter picks.

        This is the original's second step for line-break and collapse --
        ``UserIO.SelectCard`` over the node's link list.
        """
        neighbours = self.g.nodes[node].neighbours
        if not neighbours:
            self.message = f"node {node} has no neighbours"
            self._done_pending()
            return
        self.select = Selection(node=node, action=action, items=neighbours)
        self.ui_mode = UiMode.SELECT
        self.message = f"{what}: space = next, Enter = pick, Esc = cancel"

    def _select_key(self, ev):
        sel = self.select
        match keys.named(ev):
            case Key.ESCAPE:
                self._end_select()
            case Key.SPACE:
                sel.advance()
            case Key.ENTER:
                self._guard(lambda: _SECOND_NODE[sel.action](
                    self.session, sel.node, sel.current))
                self._end_select()

    def _end_select(self):
        self.select = None
        self._done_pending()

    def _done_pending(self):
        self.pending = None
        self._enter(UiMode.MAIN)

    # -- helpers ---------------------------------------------------
    def _guard(self, fn) -> bool:
        """Run a core action, showing any PermutoError instead of crashing."""
        try:
            fn()
            return True
        except PermutoError as exc:
            self.message = str(exc)
            return False


# -- what each menu entry does ---------------------------------------------
# One entry per action the tables in permuto.menus can produce; a missing one
# is a KeyError the first time that key is pressed, not a key that does nothing.

_MAIN_ACTIONS = {
    MainAction.ALGORITHM: lambda v: v.session.next_algorithm(),
    MainAction.NAME_MODE: lambda v: v.session.cycle_name_mode(),
    MainAction.FILE_MENU: lambda v: v._enter(UiMode.FILE),
    # node numbers are forced on while the program menu is up
    MainAction.PROGRAM_MENU: lambda v: v._enter(UiMode.PROGRAM),
    MainAction.EDIT: PermutographView._enter_edit,
    MainAction.QUIT: lambda v: v._enter(UiMode.CONFIRM),
    MainAction.STEP: PermutographView._step,
}

_FILE_ACTIONS = {
    # (Q)uit means quit the program, and so does ESC here -- both ask first,
    # and a "no" drops back to the main menu.
    FileAction.QUIT: lambda v: v._enter(UiMode.CONFIRM),
    FileAction.POSTSCRIPT: lambda v: v._begin_prompt(PromptKind.PS),
    FileAction.LOAD: lambda v: v._begin_prompt(PromptKind.LOAD),
    FileAction.SAVE: lambda v: v._begin_prompt(PromptKind.SAVE),
}

#: the program-menu entries that do not ask for a node first
_PROGRAM_ACTIONS = {
    ProgramAction.SPTA: PermutographView._start_spta,
    ProgramAction.PARSUM: PermutographView._start_par_sum,
    ProgramAction.LEAVE: lambda v: v._enter(UiMode.MAIN),
}

#: what a single node number is for, once ReadInt has returned
_NODE_ACTIONS = {
    ProgramAction.KILL: lambda s, n: s.kill_node(n),
    ProgramAction.UNCOLLAPSE: lambda s, n: s.uncollapse(n),
    ProgramAction.SPA: lambda s, n: s.start_spa(n),
}

#: and what the second node picked with SelectCard is for
_SECOND_NODE = {
    ProgramAction.BREAK: lambda s, a, b: s.toggle_line(a, b),
    ProgramAction.COLLAPSE: lambda s, a, b: s.collapse(a, b),
}

_PROMPT_ACTIONS = {
    PromptKind.PS: PermutographView._write_ps,
    PromptKind.SAVE: PermutographView._report_save,
    PromptKind.LOAD: PermutographView._load_session,   # sets its own message
}
