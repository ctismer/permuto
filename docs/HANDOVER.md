# Handover — permuto (Modula-2 → Python port)

Read this first, then `CLAUDE.md`, `docs/ARCHITECTURE.md` and
`git log --oneline`. Last updated 2026-07-27, at the end of the second session
of phase 3 — which has landed on `main`, see below.

## Where we are

**Parity is reached — phase 2 is done.** Every mode, menu, program, drawing
detail, format and generator of the 1995 original exists in the port.
`docs/PORT-GAPS.md` is no longer a work plan; it is the record of what the
original did and where the port decided otherwise.

- `main` is the port; `recovered-original` holds the pristine 1995 import.
- **Remote**: `origin = git@github.com:ctismer/permuto.git` (public, MIT).
  Christian pushes himself (passphrase-protected key) — hand him the command,
  never run it. Check `git status` for unpushed commits.
- `python -m pytest` — all green. `--cov=permuto` for where the holes are.
- **Serena is set up for this project** (2026-07-26). Read the memory
  `project-conventions` first; it says which tool to use where. In short:
  semantic tools for `src/` and `tests/`, Read/Grep for `legacy/`, which is
  Modula-2 (no language server exists) and CP437.
- **This port is the reference implementation.** The 1990s program still runs
  under DOSBox, which makes it an excellent place to look up *what the original
  did* — menu layout, colours, what a key actually does — so ask for a run or a
  screenshot rather than inferring from `polytop.mod`. But it is a source, not
  an authority: where it was simply bad (no error handling, a memory dump for a
  file format, 16-bit arithmetic), the port decides for itself.

## Done (ported + tested)

- **gen/** `genperm` / `operate` / `num2` — regenerates 11 original graphs
  byte-for-byte; `geodesic` (makeikos), `factorize` (trunc), `vierdrei`.
- **core/** `intvector` (fixed point, `NORM = 2**24`, 32-bit — see its header),
  `graph` (NodeMgr model, `.nod` loader, permutograph build, `pack_nodes`),
  `layout` (PCalc), `spa` (PmProgs: SPA + ParSum + line states),
  `pm` (base + operator table, naming, build, runtime editing),
  `iri` (the Iridium/SIMONE simulation).
- **session.py** — `polytop.mod`'s modes, toggles, main-loop cadence and the two
  status lines, UI-free and tested on their own.
- **formats/** `.pg`/`.nod`/`.pgd` readers, `.ply` binary sessions (read),
  `.pms` text sessions (read + write), PostScript with its preamble.
- **errors** — a real error hierarchy where the original halted or kept quiet.
- **ui/** PySide6 viewer with the original's keys, both status lines, file and
  program submenus, the operator editor and `/I` mode; PNG renderer; PostScript
  export.
- **packaging** — `pip install`, a `permuto` console command, sample graphs
  bundled, README, MIT licence.

### Verified against the original data, not just invariants
- `PM` reproduces permutations, edges **and** operator numbers of all eight
  1995 `.ply` files; `.ply` round-trips byte-identically apart from
  uninitialised padding in `pg24.ply`.
- The geodesic generator is isomorphic to all twelve `ikosa1..12.nod`.
- `vierdrei` and the factorisation match their `.nod` edge sets exactly.

## What the port deliberately does differently
Real errors instead of `HALT` (PORT-GAPS §0), `.pms` text sessions instead of a
memory dump (§3), dimmed back *edges* instead of the `colour + 8` palette trick
— the balls do use it (§6), `N` skips the display mode until SPA has put
something in it (§2), and no `InputStr` overwrite typing — a DOS-terminal habit,
not a feature (§9). Everything else follows the original.

### Settled on screen, do not re-open
The look was gone through with the author on 2026-07-26, at the picture, not in
the abstract. These were tried and rejected; PORT-GAPS §6 has the detail:

* choosing the label ink per ball (by brightness or by contrast ratio) — reads
  as restless;
* levelling the balls into one light band so a single ink always works — washed
  out;
* dropping the ball colours altogether — the colour is information (which
  character the permutation starts with), not decoration.

What stands: palette colours on the balls, bright half for the front, **labels
always black**, centred inside. If a colour looks wrong, check `ball_color()` —
it cycles 1..7 with the bright twins 9..15 so that a graph past the palette
(`ikosa9`, 812 nodes) never lands on 0 = black = an invisible node.

Not viewer features, and not needed for parity (verified standalone
experiments): `ham1`, `h`, `pmtest`, `pm5`. `kugel` was one of them and got
ported anyway — see below.

- **studies/** `kugel` — the 1991 colour study: a lit sphere in 14 colours,
  ordered dither vs Floyd-Steinberg, seamless through octant mirroring. Qt-free
  (it returns palette indices), run it with `permuto kugel`. The only floating
  point in the whole project, deliberately kept.

## Run
```bash
pip install -e .                 # or prefix commands with PYTHONPATH=src
python -m pytest
permuto                          # permutograph mode (or --pg), base 1234
permuto show pgl4                # keys: a c r h s n f p e · ESC quits
permuto iridium                  # SIMONE (or --iridium)
permuto render --help            # every command explains itself
python -m permuto render pgl5 out.png 700
python -m permuto export pgl4 out.ps 600
```

## Phase 3 — the refactor, now on `main`

**It landed on 2026-07-27**, as a fast-forward: `main` was a direct ancestor,
so there is no merge commit and the history stays linear. `2a5af72` is where it
starts, so `git diff 2a5af72` is the whole refactor and `git log --oneline
2a5af72..` is what it did.

Tests green at every commit; `python -m pytest --cov=permuto` reports 94%.

Three rules still bind, unchanged from when phase 3 started:

1. The core stays **UI-free** (a web frontend later is just another frontend),
   and `studies/` stays free of viewer imports in both directions.
2. The golden tests against `legacy/modula/nod/*` and the 1995 `.ply` files
   must stay green — never adjust a golden expectation to make a change pass.
3. Prefer driving the widget over poking internals
   (`viewer.run(..., _drive=...)`, real keystrokes, then look at the pixels).

### What the branch did

* **The two `QWidget`s are module-level classes** over a shared `ViewBase`
  (window, frame timer, crash-proof `paintEvent`, chrome font). They used to be
  nested inside `run()` / `run_iridium()`, where no language server could see
  them — which is why this was step one.
* **Nothing in the UI is stringly typed any more.** `UiMode`, `PromptKind`,
  `Selection`, `OpField`, `IriPhase`, `PromptResult`, `editor.Move`,
  `menus.Key` and `layout.Algorithm` replace strings, a one-element tuple
  everybody indexed with `[0]`, and a four-key dict. Keys go through one
  dispatch table per view: a mode nobody handles is a `KeyError`, not a key
  that quietly lands in the main menu.
* **The menus are one table** (`menus.py`, UI-free). The line used to be an
  f-string in `session.py` while the keys were an `elif` chain in the widget,
  with nothing checking that they agreed — and they had drifted. A `Binding` is
  a key, an action, how the line names it, and where the line does *not* name
  it, why (the program menu has answered `C` and `U` unadvertised since
  `polytop.mod:467`). The main line is generated from the table; the other
  three are the 1995 strings, which do not decompose into one phrase per key.
  Keys are named UI-free (`menus.Key`), so `ui/keys.py` is the only module that
  knows a Qt key code — a second frontend replaces that one file.
* **Two enums that said the same thing twice are gone.** `NodeAction` was the
  node-asking subset of the program menu, `IriAction` the prompt-collecting
  subset of Iridium's. What survives carries its own prompt wording, so
  `"Node 1="` and `"select the other end"` sit on `ProgramAction.BREAK`
  instead of being spelled out at the call site.
* **The viewer module became five.** `base_view` (window, timer, crash-proof
  paint), `permutograph_view`, `iridium_view`, `keys` (Qt, translated once) and
  `viewer` itself, now 53 lines of entry points and re-exports. Every `elif`
  chain over keys is a table lookup; `_edit_key` and `_select_key` use `match`.
* **Logic left the widget** into UI-free modules — `editor.py` (the operator
  editor's cursor and its rules) and `loader.py` (file resolution, session save
  and load, which the widget had a second, disagreeing copy of). `Session` took
  the menu state machine (`top_line`, `label_mode`), the HurryUp cadence
  (`advance_frame`) and the program menu's edits (`kill_node`, `toggle_line`,
  `collapse`, `uncollapse`).
* **`render.paint()` became `Picture`** — one frame's state as fields, five
  layer methods, and `draw()` is the layer order in five lines.
* **`Graph` owns its edges** (`find_link`, `is_linked`, `links_avail`,
  `disconnect`, `Node.remove_link`). They sat in `pm.py` under a comment saying
  they needed no PM state. `connect`/`collapse`/`uncollapse` stayed on `PM`:
  `connect` asks `which_operator` to label the new edge, so they genuinely need
  the table.
* **An edge-end is one `Link`**, not four containers sharing an index in two
  different counting conventions. See the section on it below; it is the change
  that removed a class of bug rather than an instance.
* **What is in the picture left the painting** into `scene.py` (UI-free): the
  projection, both palettes, the size arithmetic, and which colour an edge is
  and why. `ui/render.py` is five loops over five lists.
* **The limits that were really fixed arrays are gone.** `MaxLinks` 12 → 24 and
  `MaxOps` = `MaxLinks / 2` — the original's own comment, executable instead of
  a second hard-coded 6; `MaxNodesTot` 2000 → 40320, which is what `MAXDIMEN`
  already allowed, so it stopped being a second limit on the same thing. A
  fresh operator table holds seven, because an eight-place base has seven
  adjacent transpositions.
* **A frame is bounded by time**, not by counting iterations. `advance_frame`
  ran up to a 25-iteration checkpoint in one timer slot, which cost
  milliseconds in 1995 and 13.9 seconds of dead keyboard on 40320 nodes.
* **The look answers a bigger window with room, not with zoom** — marks stop
  growing at `scene.MARK_REFERENCE` and are measured by the picture's short
  side. The operator table takes the width its text needs instead of a flat
  260 px.
* **The CLI is argparse** with a subparser per command; `--pg` and `--iridium`
  for the two modes. The DOS spellings `/PG` and `/I` are gone.
* **`mypy` runs clean** at its default strictness, from the suite where it is
  installed, with no `type: ignore` anywhere. Plus a tooling-free test that
  resolves every annotation in the package — which is what caught one naming
  something that did not exist.

### Twelve defects found — each has its own test, each was red first

| What went wrong | Test that pins it |
|---|---|
| The operator digits ignored the name mode, so cycling `N` to "write nothing" still wrote numbers on the links; and they were hidden during SPA/ParSum, which the original showed. `pmdisp.mod:94` guards both with the same `names>0`; the port asked "is a program running" instead | `test_no_names_means_no_operator_numbers_on_the_edges` |
| `(C)ollapse` / `(U)ncollapse` on a `.nod` graph reached through a `pm` that is `None` and threw `AttributeError` out of the key handler. The program menu offers them for any graph, as it did in 1995 | `test_the_table_only_actions_refuse_politely_on_a_plain_graph` |
| A three-field prompt (Iridium `T`) closed after the first Enter — `"more"` was treated as an ending. **Introduced by this refactor**, caught by the key tests written in the same commit | `test_a_three_field_prompt_stays_open_until_the_last_field` |
| `PM.Disconnect` shifts `links`/`opno` but leaves `state.lines`/`broken` at their old indices, although they address the same link numbers — the 1995 bug, already fixed in the port, now recorded with its source lines in PORT-GAPS §0 | `test_broken_marks_follow_their_edge_through_a_disconnect` |
| A typed extension was honoured or not depending on where the file was: `./alle6.nod` was displaced by its `.pgd` sibling, the same name among the samples was not. Same keystrokes, two different graphs and two different modes | `test_a_typed_extension_is_honoured_wherever_the_file_lives` |
| `permuto build knot …` writes `knot.pg/.nod/.pgd` here, and `permuto show knot` said "nothing found": bare names were only ever looked for in the sample directory. The two commands did not compose | `test_a_graph_just_built_is_found_by_its_bare_name` |
| `show mine 3` built a nonsense permutograph out of the file name instead of resuming `mine.pms` with a seed. The CLI asked "is this a file?" of the graph loader alone, which knows nothing about sessions | `test_a_seed_behind_a_session_file_still_resumes_the_session` |
| `pos=1,2,x` at `dim=2` loaded as a clean node: the `.pms` reader dropped whatever was not a number and *then* counted what was left, so the count matched and the junk went unmentioned — the one thing PORT-GAPS §0 says the port must never do | `test_junk_among_the_right_number_of_coordinates_is_not_swallowed` |
| An operator table the base cannot carry loaded silently, and the editor opened on it: the reader handed the table to `PM`'s constructor, which validates only the base, bypassing the `set_cycle` where that rule lives | `test_an_operator_the_base_cannot_carry_is_refused` |
| `perms.next_perm` was declared `s: List` after the typing sweep removed the import — the regex looked for `List[` and this one had no subscript. `from __future__ import annotations` means nothing ever evaluates it, so it survived a full green suite. **Introduced by this refactor** | `test_every_annotation_in_the_module_resolves` |
| Typing a value longer than the stored one ran it off the right edge of the window, where it was cut off: the room beside the picture was measured from the *stored* table plus one character. **Introduced by this refactor** | `test_a_value_longer_than_the_stored_one_is_not_drawn_off_the_edge` |
| `advance_frame` counted iterations, so with HurryUp it held the event loop — and the keyboard — for 13.9 s on 40320 nodes | `test_hurry_stops_at_the_budget_however_far_it_has_got` |

Most of those turned up by accident — from a user question, from moving code,
or from writing the test that was meant to *cover* the line. Nobody went looking
for any of them. The three loader ones came out of what the list below called a
coverage hole: writing the tests as asked would have frozen all three as
expected behaviour. Three were introduced by this refactor and caught by it.

### Measured

```
src     5071 -> 6354            tests   2519 -> 4202  (+1683)
coverage  92% -> 94%,  menus.py and scene.py 100%, loader.py 84% -> 100%
                       pmsfile 87% -> 94%
Qt-bound (files under ui/ that import PySide6)  1229 -> 1066  = 24% -> 17%
UI-free and frontend-neutral: menus, scene, session, editor, loader  = 1444
ui/viewer.py  829 -> 53    (+ permutograph_view 394, iridium_view 189,
                              base_view 85, keys 70)
ui/render.py  444 -> 201   (+ scene.py 346, UI-free)
```

The refactor did **not** make the code shorter. What moved is where the logic
lives and whether a mistake is caught. The Qt-bound part is down by a fifth and
is now six named files instead of two; what a second frontend would have to
rewrite is `ui/keys.py` and five drawing loops, because `menus.py`, `scene.py`,
`session.py`, `editor.py` and `loader.py` are all frontend-neutral.

### What to do next

**Have someone else read the diff** — `git diff 2a5af72`, and see the reading
guide below. It is on `main` already; the reading is still owed. Everything else
on this list has been done; what is left is deliberately left.

Done, newest first: the six-operator ceiling, the `.pms` refusals (two of which
were wrong — see the defect table), `nnodes`, one `Link` per edge-end, the
loader rules, and `ui/render.py`, which turned into `scene.py` plus five drawing
loops.

**Not done, on purpose.** `MAXDIMEN = 8` is now the *only* thing bounding the
base, and it is a real bound: the coordinate vectors are eight components wide
and both file formats store them that way, so raising it is a format change,
not a constant. (Until 2026-07-27 the node limit refused eight places first,
which made `MAXDIMEN` look like the slack one. It is not.) Qt chrome (a menu bar, a status bar, the operator table as a
dock): the menu line is a *display* of what the keys do, flags and all, and a
real `QMenuBar` would have to be clickable, which means a second input path
through a program that has been keyboard-only since 1995. The dock alone is
defensible and worth doing together with the size control, when that arrives —
`scene.UI_SCALE` and `scene.MARK_REFERENCE` are the two numbers it would turn.

### How an edge is stored, and why it stopped being four things

An edge is stored twice, once at each end. Until `b3629e3` each end lived in
**four parallel containers** sharing an index — `Node.links` (the neighbour),
`Node.opno` (the operator), `state.lines` (the LineStatus) and `state.broken`
(a set of 1-based indices) — plus `nlink`, a cached `len(links)`. Two index
conventions, `broken` counting from 1 and `lines` from 0, met in the same loop
in `spa.py`. That is the shape that produced the 1995 `Disconnect` bug: the
first pair was shifted on removal and the second was not, so the marks then
described other edges. The port fixed the symptom, and `remove_link` held the
four together by hand for as long as they existed.

Now one end is one object:

```python
@dataclass
class Link:
    to: int                 # the neighbour's number
    op: int = 0             # which operator made this edge
    status: int = L_FREE    # LineStatus while a program runs
    broken: bool = False
```

One `Link` per **edge-end**, not a shared edge object: the same edge is
`L_INPUT` where the wave enters and `L_OUTPUT` where it leaves, and the
direction discs read exactly that. `remove_link` is a `del`, `spa.py` no longer
realigns `lines` "if the length no longer matches", `pack_nodes` no longer
unzips and rezips, and `nlink` is a property.

**The formats did not change.** `.pms` and `.ply` are index-based on disk and
stay that way; the 1-based/0-based arithmetic now exists only at that boundary,
where `pmsfile._state_field` says so in as many words.

Worth knowing for the next such change:

* It cost **26 files, +10 lines** — but −16 lines of *executable* code. The
  file grew because the reasoning went in with it. An estimate that counts only
  the code will come out too optimistic; this one did, by 36 lines.
* `tools/framehash.py` caught two frames going wrong immediately, and the fault
  was **the tool**: it still set `state.broken = {1}`, which after the change
  merely creates a dead attribute, so the broken edge vanished from the picture.
  Anything that pokes the representation directly has to be swept too.
* `test_program_state_survives` had been marking link 3 of a node with two
  links. The old `broken` set accepted any number, so the test passed on a mark
  that pointed at nothing. There is no number left to be wrong about.

### Open: a big graph should be much faster than this (author, 2026-07-27)

Measured, at 40320 nodes and 141120 edges, 900x900: relaxation 698 ms a step,
building the scene 436 ms, painting it 1137 ms -- about 2.3 s a frame.

Nothing is quadratic: 9.3x the edges gives 8.7x the relaxation, 11.9x the
scene, 7.6x the painting. It is linear and there is simply a lot of it.

Where the painting time actually goes, measured rather than profiled (cProfile
attributes the time *inside* `drawLine` to `drawLine`, which reads as though the
Python->C++ crossing were the cost -- it is 0.47 of the 3.85 microseconds an
edge takes, 12 percent). The rest is Qt's rasteriser, and the biggest item in
it is antialiasing: the same edges cost 58 ms with and 20 ms without.

Done: the pens are cached (`1d7c4bd`), a seventh off the layer, picture
byte-identical.

Not tried, and this is where to look next:

* **Antialiasing off past some size.** Three times faster, and at 40320 nodes
  the balls are a few pixels wide anyway. A judgement to make at the picture.
* **Batching by pen** with `drawLines`: a further eighth, but it draws colour
  by colour and so changes which edge lies on top where two cross.
* **Not redrawing what did not change** -- the graph is repainted whole every
  frame, including while only the chrome changes.
* **A different surface**: `QOpenGLWidget`, or a `QPixmap` the picture is
  composed into once. Untouched.

Careful with one thing found on the way: `drawLine(x1, y1, x2, y2)` with floats
hits the *integer* overload and truncates the coordinates, which is a different
picture. Pass `QPointF`.

### Done: the tests run on GitHub (2026-07-28)

`.github/workflows/tests.yml`, one job, `push` and `pull_request`, Python
**3.10, 3.12, 3.13 and 3.14** -- the floor, what is developed on, and the two
current releases (3.15 is still alpha). `mypy` is not a job of its own on
purpose: `tests/test_annotations.py` shells out to it, so a plain `pytest`
covers both.

**It is green** -- run `30310008124`, 38 s and 42 s, first try, when the matrix
was still 3.10/3.12. The floor was checked locally first (fresh venv, 372
passed) rather than by pushing at CI until it worked, and so were 3.13 and 3.14
before they were added.

The test tools come from the `[test]` extra in `pyproject.toml`, which the
workflow installs as `pip install -e ".[test]"`. That list used to exist twice,
and the copy in `pyproject.toml` had no `mypy` in it -- which matters, because
the mypy test *skips* where mypy is absent instead of failing. Nothing is
version-pinned there: the suite was checked against mypy 2.3 as well as the
1.15 that happens to be installed locally.

The actions are pinned at `checkout@v5` / `setup-python@v6`; `@v4`/`@v5` still
run but are annotated as Node 20, which the runners now force onto Node 24.
`.github/dependabot.yml` watches them monthly, so the next such bump arrives as
a pull request rather than by somebody reading the annotations. The README
carries the badge.

Beyond the sketch this replaced: `fonts-dejavu-core` (the widget tests paint
chrome text and read the pixels back; a runner without a font is a different
picture), `apt-get update` before the install, `fail-fast: false` so one
version does not hide another, and no `pytest-cov` -- nothing in `addopts` asks
for coverage.

Three things that would otherwise have cost an evening, and still apply to
anyone editing that file:

* **PySide6 will not even import** on a bare ubuntu runner without `libegl1`
  (and usually `libgl1`, `libxkbcommon-x11-0`). The error names a missing `.so`
  and looks nothing like the real cause.
* **`QT_QPA_PLATFORM=offscreen`** at the job level. `conftest.py` and
  `test_render.py` set it themselves, but only once they are imported; setting
  it in the environment is what makes an early import safe.
* **The 1995 bytes survive the checkout already** -- `.gitattributes` says
  `* -text`, so no line-ending conversion anywhere. The golden tests read
  `legacy/` as CP437 and depend on that. Nobody should "fix" that line.

Worth adding at the same time: `python tools/framehash.py` as a job of its own
would notice a picture change, but only against hashes committed somewhere, and
those are machine-dependent (font rasterisation). Probably not worth it -- the
tool is for a person comparing before and after, not for CI.

### Open: reactivity still is not good -- probably a thread (author, 2026-07-27)

The frame budget took the dead keyboard from 13.9 s to 0.63 s, and 0.63 s is
still too long. It is one relaxation iteration, the smallest thing that can
happen, and the repaint after it is another second in the next turn of the
event loop. Both run in the GUI thread, so nothing else can.

What a worker thread would and would not buy, before anyone is disappointed:

* **Not speed.** The relaxation is pure Python integer arithmetic, so the GIL
  serialises it either way. What a thread buys is that the interpreter switches
  every few milliseconds, so keystrokes are handled *while* it computes.
* Only the GUI thread may paint a widget, so the split is: the worker relaxes,
  hands over, the GUI paints.
* The shared state is the graph, and the painter reads positions the worker
  would be writing. There is already a two-buffer structure to build on --
  `layout.backup()` keeps `old` beside `pos`, which is what `contract` reads
  from. Painting from `old` while the worker fills `pos` may be most of the
  answer without a lock.
* `core/` is Qt-free, which is what makes this a small change rather than a
  rewrite: nothing in the relaxation touches a widget.
* The cheaper thing to try first is `processEvents()` between iterations. It is
  a few lines, and the hazard is re-entrancy -- a keystroke can start a rebuild
  in the middle of a relaxation.

Worth doing together with the cheaper balls below: at 40320 nodes the repaint
is the larger of the two blocks.

### Wanted: smaller balls, cheaper balls, and real ones (author, 2026-07-27)

Three things about the nodes, from looking at 40320 of them. They belong
together and none of them is started.

**Smaller.** At that size the balls swamp the picture -- there has to be a way
to bring them down. `scene.UI_SCALE` and `scene.MARK_REFERENCE` are the two
numbers that decide it and they already sit in one place; what is missing is a
control (the size slider, which is also what the dock question waits for). Worth
asking whether the size should fall with the node count on its own, the way the
mark size already stops growing with the window.

**Cheaper.** `render._draw_balls` calls `drawEllipse` per node with a brush and
antialiasing, plus a second one for a dead node's rim and a third for an active
node's ring. Roughly 2.8 microseconds a ball measured at 5040 nodes, so about
113 ms at 40320. For a ball a few pixels across that is a filled antialiased
curve where a handful of pixels would do -- a small blitted image per (colour,
size), or `drawPixmap`, would be a different order.

**Real ones.** And then they could stop being discs: `studies/kugel` is the
1991 colour study of a *lit sphere*, palette-indexed and Qt-free, written for
exactly this and never wired to the viewer. It already produces the pixels; the
cheap path above wants a small image per colour anyway. The two ideas are the
same piece of work.

### Waiting: the chrome is painted, so none of it can be quoted

Both status lines, the prompt and every error message are drawn with a
`QPainter`, so there is nothing to select and nothing to copy -- an error you
cannot quote is an error you have to photograph, which is how this came up
(author, 2026-07-27).

The cheap answer is a copy gesture: a logical `menus.Key.COPY` that
`ui/keys.py` produces for Ctrl-C, and a `ViewBase.copy_chrome()` putting the
lines on the clipboard. That keeps `menus.py` Qt-free and needs no widgets.
The thorough answer is real chrome -- see "Nothing is off limits" on the dock
question, which this belongs with, and which waits for the size control.

Deferred by the author, not forgotten.

### Reading this branch (for a reviewer)

Fifty-odd commits, but ten arcs. `git log --oneline 2a5af72..main` reads
newest first; the arcs below are oldest first, which is the order they make
sense in. Each commit builds and its tests pass, so bisecting works.

| Arc | Commits | What to check |
|---|---|---|
| The widgets become visible to a language server | `57b7925`..`2568940` | pure moves |
| Types instead of strings and dicts | `550a44f`..`4ad9727`, `a05eb84` | that no enum lost a case |
| Logic leaves the widget | `cf9c60a`, `338beca`, `d9ccd0e`, `0b013c1`, `e0d6ebc`, `ec65497` | that `core/` and `session.py` stayed UI-free |
| Painting becomes layers, then a scene | `92e09fe`..`bd19861`, `39b7020` | the layer order, and that nothing draws twice |
| The menus become one table | `820748a` | **the parity claims** — see below |
| The look, on purpose | `24b18bf`, `6b1360b` | whether you agree with the judgement |
| One `Link` per edge-end | `b3629e3`, `e00c3b9` | the two serialisation modules; see above |
| Limits that were fixed arrays | `769c3c5`, `c0b1ce3`, `b0f83e5`, `c46739e` | the .ply refusals, and .pms's stricter parse |
| Types, and what they demanded | `909f023`, `b54b3d3` | that no `type: ignore` crept in |
| Responsiveness and cost | `9a56bb5`, `1d7c4bd`, `7ea7add` | the frame budget; the picture is byte-identical |

**Where the risk actually is**, honestly:

* **`820748a` (the menu table).** The main menu line is now *generated*. It is
  pinned byte-for-byte against `polytop.mod:372-392` in
  `test_menus.py::test_the_1995_menu_lines_are_reproduced_exactly`, but if the
  original prints something that table cannot express, this is where it breaks.
  Note the two deliberately unadvertised keys (`C`/`U` in the program menu) —
  `polytop.mod:467` versus `:498`/`:508` says the original hid them too.
* **`39b7020` (scene/render split).** Claimed invisible, and checked over
  thirteen frames with `tools/framehash.py`. The residual risk is a
  configuration nobody rendered. If you think of one, add it to that file.
* **`f58dd80` (name resolution).** This one **changes CLI behaviour**: a typed
  extension now wins, bare names are looked for in the working directory first,
  and a seed behind a session name resumes the session. Three defects, three
  tests; but if you relied on `show alle6.nod` giving you the `.pgd`, it no
  longer does.
* **`24b18bf` / `6b1360b` (the look).** The only intentional visual change, at
  the author's request: marks stop growing past `scene.MARK_REFERENCE`, and the
  operator table takes the width its text needs instead of a flat 260 px. The
  window the viewer opens with is bit-identical apart from the wider picture.

**What the maths did not change.** `core/` was touched -- `graph` and `spa`
for the `Link` object, `pm` for the limits, `iri` for the same parallel-list
shape, `layout` for `as_algorithm` -- but only in *how* things are held, never
in what is computed. `intvector` and the generators are untouched.

The proof of that is not a promise: the golden tests against
`legacy/modula/nod/*` and the eight 1995 `.ply` files are **unchanged** and
green, and `tools/framehash.py` says the picture is byte-identical across every
step of it. If a reviewer only checks one thing, check that no golden
expectation was edited to make something pass.

Useful while reading:

```bash
python -m pytest -q                       # 372 tests
python -m pytest --cov=permuto            # 94%, pmsfile 87% -> 94%
python tools/framehash.py                 # the picture, as thirteen hashes
permuto show pgl5                         # and then pull the window open
```

### How to read a "coverage hole" on this list

Twice now the honest answer to "these lines never run" has been "and some of
them are wrong". Before writing a test for an uncovered branch, work out what
the branch is *supposed* to do and check that it does — a test written to the
current behaviour turns a defect into a golden expectation, which is worse than
no test. The loader entry above is the worked example: three of its rules were
wrong, and all three would have been frozen.

The same goes for a test that passes on the first run: prove it can fail.
`test_the_direction_discs_actually_reach_the_picture` passed and was worthless
— a disc is the same green as the edge it sits on, so comparing the pixel under
it to the disc's colour could not tell the two apart. Switching the layer off
and watching the test still pass is what found that.

When a change has to leave the picture alone, say so in bytes: render a set of
frames before and after and compare hashes. The `scene.py` split was checked
over eleven (both window shapes, every name mode, a graph mid-SPA with a broken
edge, a dead node, an active one, a `.nod` graph, the 812-node geodesic).

### Nothing is off limits

An earlier version of this file said not to split `PermutographView` further.
That was withdrawn by the author (2026-07-27): the golden tests against the
1995 data are the safety net -- with `recovered-original` and the DOSBox build
behind them -- so anything may be taken apart as long as the suite stays green. If a change makes you uneasy, pin the
result with a test rather than leaving it undone.

Afterwards: optionally TypeScript/browser on the cleaned core — `menus.py`,
`session.py`, `editor.py` and `loader.py` are already frontend-neutral, and
`test_menus.py::test_the_menus_stay_ui_free` keeps them that way.

### Loose thread worth picking up
Christian wrote a Conway **Game of Life** around the same time as the rest, and
used the `kugel` study to design its scalable little balls — the connection to
`studies/kugel` is his own. That source is not in the recovered archive
(checked: nothing matching life/Conway in all 233 entries of
`Poly_decrypted.zip`), but he thinks he can find it. If it turns up, it belongs
in `studies/` next to `kugel`, and there is something to build from it.

## Gotchas
- **Coordinates always need a scale.** `NORM = 2**24`, and anything much
  smaller projects to a single dot. `layout.frame()` is called by every
  producer of coordinates — `Graph.random_init`, `PM.new_permutograph` for a
  fresh graph, `Session` for whatever a session file brought along. Do not
  re-add `normalize()` calls at the use sites; add them at the producer.
- `HurryUp` is "compute fast, look seldom" — it suppresses the spin *while
  calculating* (`polytop.mod:299`), so it must earn that back in iterations.
  `Session.advance_frame` iterates towards the next checkpoint but stops after
  `FRAME_BUDGET` (50 ms), because **nothing else happens while it runs** — no
  keystroke, no repaint. It used to count iterations instead, which cost
  milliseconds on a 1995-sized graph and 13.9 seconds of dead keyboard on
  40320 nodes. Bound the time; how many iterations fit is the machine's
  business.
- **A stale `.pyc` can survive a `git checkout`.** Python compares mtime *and
  size* only. An edit that keeps the size (swapping two equal-length strings)
  and a checkout in the same second leave the old bytecode in place, so the
  file on disk and the code being run disagree. If something stays red that
  cannot possibly be red, delete `__pycache__` before believing anything else.
- An `Enum` whose members carry extra data must set `_value_` in **`__new__`**,
  not `__init__`: the by-value map is filled from the tuple that was assigned,
  so with `__init__` the lookup `Algorithm("rubber")` raises `ValueError`.
  `core/layout.py` has it right and says why.
- The sizes `TrueDisc`/`TrueCircle` were called with are **radii**, not
  diameters — the ball is sized around the label that goes inside it. See
  PORT-GAPS §6; `Graph`'s source is lost, so this was read off the call sites.
- **`grep` lies about `legacy/`.** Those files are CP437, which a UTF-8 locale
  calls binary; macOS grep then prints nothing and exits 1, which reads as "not
  found". `git grep`, `rg` and `grep -a` are fine. For readable diffs:
  `git config diff.cp437.textconv "iconv -f cp437 -t utf-8"` (once per clone).
- `/rewind` restores files but does **not** touch git. If disk and HEAD
  disagree, trust the disk and re-commit.
- `Lib.RANDOM` is source-less → absolute node positions are not
  bit-reproducible; the *algorithm* is faithful and the emergent shape matches.
  This applies to the `.nod` path only: in permutograph mode the start layout
  comes from the link numbers, so those rebuilds *are* reproducible.
- The AWK generators' node numbering is likewise not reproducible (Thompson
  AWK hash order), so those are checked by isomorphism — see PORT-GAPS §8.
- Integer width is **32 bit** throughout; do not reintroduce TopSpeed's 16-bit
  wraparound. `core/intvector` explains why and offers `int32()` for the few
  places where the original's overflow is observable.
- `legacy/modula/s.exe` is PolyTop **V1.3** "now under the name SimOne", an
  older build than `polytop.exe` (V1.4) — not a source of extra features. Its
  copyright line names the second author, Gerhard G. Thomas.
