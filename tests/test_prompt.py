"""The shared input prompt -- one implementation, Qt-free and unit tested,
so the "typed digits do not show" bug cannot come back in a second copy."""

from permuto.ui.prompt import FieldPrompt, single


def type_str(prompt, s):
    for ch in s:
        prompt.type_char(ch)


def test_single_numeric_field_collects_and_shows_the_buffer():
    p = single("StartNode=")
    type_str(p, "12")
    # the buffer is visible while typing -- the actual regression that hit
    assert "StartNode=12_" in p.display()
    assert p.enter() == "submit"
    assert p.ints() == [12]


def test_numeric_field_rejects_non_digits():
    p = single("Node")
    type_str(p, "1a2.b3")
    assert p.buffer == "123"


def test_text_field_accepts_letters_for_filenames():
    p = single("Save = ", numeric=False)
    type_str(p, "out.ply")
    assert "Save = out.ply_" in p.display()     # visible while typing
    assert p.enter() == "submit"
    assert p.text() == "out.ply"


def test_backspace_edits_the_current_field():
    p = single("Node")
    type_str(p, "159")
    p.backspace()
    assert p.buffer == "15"


def test_multi_field_advances_and_shows_a_cursor_on_the_live_field():
    p = FieldPrompt("transmit",
                    [("Node1", True), ("Node2", True), ("Repeat", True)])
    type_str(p, "900")
    assert p.enter() == "more"
    type_str(p, "9")
    # first committed, second is live with the cursor, third still empty
    shown = p.display()
    assert "Node1=900" in shown
    assert "Node2=9_" in shown
    assert "Repeat=" in shown and "Repeat=9" not in shown
    assert p.enter() == "more"
    type_str(p, "3")
    assert p.enter() == "submit"
    assert p.ints() == [900, 9, 3]


def test_empty_field_becomes_zero():
    p = single("Repeat")
    assert p.enter() == "submit"
    assert p.ints() == [0]
