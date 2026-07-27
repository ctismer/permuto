"""A single text-input prompt, shared by every viewer that reads a value.

This exists so there is exactly one prompt implementation.  Both the
permutograph viewer (file names, node numbers) and the Iridium view (kill /
transmit) drive it; the earlier code had two divergent copies, and the second
one forgot to show the digits as they were typed.

It is deliberately Qt-free -- the view maps key events onto :meth:`type_char`,
:meth:`backspace` and :meth:`enter`, so the whole input behaviour is unit
tested without a display.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum


class PromptResult(Enum):
    """What a keystroke did to a prompt.

    ``MORE`` is the one that bites: a prompt with several fields (Iridium's
    (T)ransmit asks for three) is not finished by the first Enter, and reading
    that as an ending closes it a third of the way through.
    """

    TYPING = "typing"
    MORE = "more"          # field committed, the next one is now live
    SUBMIT = "submit"      # the last field is in
    CANCEL = "cancel"      # ESC


class FieldPrompt:
    """One or more labelled fields filled in turn.

    ``fields`` is a sequence of ``(label, numeric)`` pairs; a numeric field
    accepts only digits.  A single-field prompt (a file name, one node number)
    is just the common case of this.
    """

    def __init__(self, title: str, fields: Sequence[tuple[str, bool]]):
        self.title = title
        self.fields: list[tuple[str, bool]] = list(fields)
        self.values: list[str] = []
        self.buffer = ""

    @property
    def _index(self) -> int:
        return len(self.values)

    @property
    def _numeric(self) -> bool:
        return self.fields[self._index][1]

    def type_char(self, ch: str) -> None:
        if not ch or not ch.isprintable():
            return
        if self._numeric and not ch.isdigit():
            return
        self.buffer += ch

    def backspace(self) -> None:
        self.buffer = self.buffer[:-1]

    def enter(self) -> PromptResult:
        """Commit the current field: ``SUBMIT`` when the last one is done,
        else ``MORE``."""
        self.values.append(self.buffer)
        self.buffer = ""
        return (PromptResult.SUBMIT if len(self.values) == len(self.fields)
                else PromptResult.MORE)

    def display(self) -> str:
        """The prompt line, with a cursor on the field being typed.

        A single field is shown as just ``label<value>`` (its label already
        carries any ``=`` the caller wants); several fields are shown as
        ``title:  Label=v   Label=v`` with the cursor on the live one.
        """
        def shown(i, label):
            if i < len(self.values):
                return self.values[i]
            if i == self._index:
                return f"{self.buffer}_"
            return ""

        if len(self.fields) == 1:
            label = self.fields[0][0]
            return f" {label}{shown(0, label)}"
        parts = [f"{label}={shown(i, label)}"
                 for i, (label, _) in enumerate(self.fields)]
        return f" {self.title}:  " + "   ".join(parts)

    def ints(self) -> list[int]:
        """The entered values as integers (empty field -> 0)."""
        return [int(v) if v else 0 for v in self.values]

    def text(self) -> str:
        """The single-field text value (for file-name prompts)."""
        return self.values[0].strip() if self.values else ""


def single(title: str, numeric: bool = True) -> FieldPrompt:
    """A one-field prompt -- the usual case."""
    return FieldPrompt(title, [(title, numeric)])
