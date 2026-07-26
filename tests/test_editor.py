"""The operator editor's two rules that the keyboard alone does not show:
a cell that will not validate keeps the cursor, and Ctrl-End goes to the last
cell anyone filled in.  No Qt here -- that is the point of the class.
"""

from permuto.core.pm import PM
from permuto.editor import Move, OperatorEditor, OpField


def _pm():
    """A 4-place base with two operators filled in, four rows left blank."""
    return PM(base="1234",
              optable=[["12", "", ""], ["23", "", ""]] +
                      [["", "", ""] for _ in range(4)])


def test_an_invalid_cycle_keeps_the_cursor():
    pm = _pm()
    ed = OperatorEditor(pm)
    ed.move(Move.DOWN)                      # Op 1, cycle 1
    ed.buffer = "15"                     # a 4-place base has no position 5
    assert ed.commit(), "an invalid cycle must report, not pass silently"
    assert ed.field == OpField(1, 1), "the cursor may not leave a bad cell"
    assert pm.optable[0][0] == "12", "and nothing may be written"


def test_last_goes_to_the_last_filled_cell_not_the_last_cell():
    ed = OperatorEditor(_pm())
    ed.move(Move.LAST)
    assert ed.field == OpField(2, 1)
    assert ed.buffer == "23"
