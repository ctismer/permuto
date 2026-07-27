# Handover — permuto (Modula-2 → Python port)

Read this first, then `CLAUDE.md`, `docs/ARCHITECTURE.md` and
`git log --oneline`. Last updated 2026-07-27, in the second session of phase 3
— the refactor lives on the branch `phase3-refactor`, see below.

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

## Phase 3 — the refactor, on `phase3-refactor`

**On `origin`, and read by nobody but its author.** Tests green at every
commit; `python -m pytest --cov=permuto` reports 93%. `git log --oneline
main..phase3-refactor` is the whole story in twenty-odd lines.

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
  `disconnect`, plus `Node.remove_link`, which keeps every per-link array
  shifting together). They sat in `pm.py` under a comment saying they needed no
  PM state. `connect`/`collapse`/`uncollapse` stayed on `PM`: `connect` asks
  `which_operator` to label the new edge, so they genuinely need the table.
* **The CLI is argparse** with a subparser per command; `--pg` and `--iridium`
  for the two modes. The DOS spellings `/PG` and `/I` are gone.

### Seven defects found — each has its own test, each was red first

| What went wrong | Test that pins it |
|---|---|
| The operator digits ignored the name mode, so cycling `N` to "write nothing" still wrote numbers on the links; and they were hidden during SPA/ParSum, which the original showed. `pmdisp.mod:94` guards both with the same `names>0`; the port asked "is a program running" instead | `test_no_names_means_no_operator_numbers_on_the_edges` |
| `(C)ollapse` / `(U)ncollapse` on a `.nod` graph reached through a `pm` that is `None` and threw `AttributeError` out of the key handler. The program menu offers them for any graph, as it did in 1995 | `test_the_table_only_actions_refuse_politely_on_a_plain_graph` |
| A three-field prompt (Iridium `T`) closed after the first Enter — `"more"` was treated as an ending. **Introduced by this refactor**, caught by the key tests written in the same commit | `test_a_three_field_prompt_stays_open_until_the_last_field` |
| `PM.Disconnect` shifts `links`/`opno` but leaves `state.lines`/`broken` at their old indices, although they address the same link numbers — the 1995 bug, already fixed in the port, now recorded with its source lines in PORT-GAPS §0 | `test_broken_marks_follow_their_edge_through_a_disconnect` |
| A typed extension was honoured or not depending on where the file was: `./alle6.nod` was displaced by its `.pgd` sibling, the same name among the samples was not. Same keystrokes, two different graphs and two different modes | `test_a_typed_extension_is_honoured_wherever_the_file_lives` |
| `permuto build knot …` writes `knot.pg/.nod/.pgd` here, and `permuto show knot` said "nothing found": bare names were only ever looked for in the sample directory. The two commands did not compose | `test_a_graph_just_built_is_found_by_its_bare_name` |
| `show mine 3` built a nonsense permutograph out of the file name instead of resuming `mine.pms` with a seed. The CLI asked "is this a file?" of the graph loader alone, which knows nothing about sessions | `test_a_seed_behind_a_session_file_still_resumes_the_session` |

Four of those seven turned up by accident — one from a user question, three
while moving code or writing the tests that were meant to *cover* it. Nobody
went looking for any of them. The three loader ones came out of what the list
below called a coverage hole: writing the tests as asked would have frozen all
three as expected behaviour.

### Measured

```
src     main 5071 -> 6038
tests   main 2519 -> 3835   (+1316)
coverage  92% -> 93%,  menus.py and scene.py 100%, loader.py 84% -> 100%
Qt-bound (files under ui/ that import PySide6)  main 1229 -> 992  = 24% -> 16%
ui/viewer.py  829 -> 53    (+ permutograph_view 394, iridium_view 189,
                              base_view 85, keys 70)
ui/render.py  444 -> 201   (+ scene.py 346, UI-free)
```

The refactor did **not** make the code shorter. What moved is where the logic
lives and whether a mistake is caught. The Qt-bound part is down by a fifth and
is now six named files instead of two; what a second frontend would have to
rewrite is `ui/keys.py` and five drawing loops, because `menus.py`, `scene.py`,
`session.py`, `editor.py` and `loader.py` are all frontend-neutral.

### What to do next, in this order

1. **`formats/pmsfile.py` (88%) — the refusals.** The open lines are the
   `FileFormatError` branches. "Reject with a reason instead of swallowing it"
   is the port's stated advantage over the original; nobody checks the reasons
   arrive.
2. **Have someone else read the branch diff** before it lands on `main` — see
   the reading guide below.

Done since: the loader rules (three defects, see the table above) and
`ui/render.py`, which turned into `scene.py` + five drawing loops — the
direction discs, the hollow dead ball and the white ring now have tests on both
sides, what the scene says and what reaches the pixels.

### Reading this branch (for a reviewer)

Thirty commits, but six arcs. `git log --oneline main..phase3-refactor` reads
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

**What was not touched**: `core/` (`pm`, `graph`, `spa`, `iri`, `layout`,
`intvector`), the generators, and the file formats other than where the loader
calls them. The golden tests against `legacy/modula/nod/*` and the eight 1995
`.ply` files are unchanged and green — if a reviewer only checks one thing,
check that no golden expectation was edited to make something pass.

Useful while reading:

```bash
python -m pytest -q                       # 311 tests
python -m pytest --cov=permuto            # 94%
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
That was withdrawn by the author (2026-07-27): the reference implementation on
`main` and the golden tests are the safety net, so anything may be taken apart
as long as the suite stays green. If a change makes you uneasy, pin the
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
  `Session.advance_frame` runs a whole checkpoint per timer tick.
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
