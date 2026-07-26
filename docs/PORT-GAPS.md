# Port gaps — what the Python port still owes the Modula-2 original

Status: **parity is reached, nothing is open.** Every mode, menu, program,
drawing detail and generator of the original exists in the port. This document
is no longer a work plan; it stays as the record of what the original did, with
the byte-level formats and decoded behaviour that made the port possible, all
verified against `legacy/modula/`.

Rule for this phase: **reach parity first.** Improvements beyond the original
are welcome afterwards — with the single exception of error handling, where
the original's behaviour is not portable (see §0).

## Progress

| § | Item | State |
|---|---|---|
| 0 | Error handling (`permuto/errors.py`) | **done** |
| 1 | Operating modes (Polytop / `/PG` / `/I`) | **done** |
| 2 | Menu, keys, status lines, single-step (`session.py`, `ui/viewer.py`) | **done** |
| 2 | `ESC` = `UserWantsToExit()` confirmation prompt | **done** |
| 3 | `.ply` binary session format (`formats/plyfile.py`) | **done** |
| 3 | File submenu (quit / PostScript out / load / save) | **done** |
| 3 | PostScript preamble shipped with the export (`formats/poly.pre`) | **done** |
| 4 | Program submenu (kill/break/collapse/uncollapse) — model + UI | **done** |
| 5 | `PM` model: naming, build, runtime editing (`core/pm.py`) | **done** |
| 5 | Operator editor UI | **done** |
| 6 | Drawing: operator digit, dead/active nodes, screen sizes scaled | **done** |
| 6 | Direction discs (`TrueDisc`) for `L_input`/`L_output` | **done** |
| 6 | Labels black and centred in the ball | **done** |
| 7 | Iridium / SIMONE — simulation (`core/iri.py`) | **done** |
| 7 | Iridium / SIMONE — `/I` mode UI (`run_iridium`) | **done** |
| 8 | `makeikos` geodesic generator (`gen/geodesic.py`) | **done** |
| 8 | `trunc` factorisation (`gen/factorize.py`), `vierdrei` (`gen/vierdrei.py`) | **done** |
| 9 | `UserIO` input primitives | **done** (one `FieldPrompt`) |
| 9 | `InputStr`'s overwrite typing (port appends; Ins/Del/←/→ absent) | n/a — not wanted |
| + | Text session format `.pms` (better than `.ply`) | **done** |

What is done is verified against the original data, not just against
invariants: `PM` reproduces the permutations, edges *and* operator numbers of
all eight `.ply` files; the geodesic generator is isomorphic to all twelve
`ikosa*.nod`; `vierdrei` and the factorisation match their `.nod` edge sets
exactly; `.ply` round-trips byte-for-byte apart from uninitialised padding.

Deliberate deviations, beyond §0's error handling: the depth cue dims the back
*edges* instead of the original's `colour + 8` palette trick (the balls do use
it), `N` skips the display mode until a program has filled it (the original's
own reason for skipping the perm mode, applied once more), and the viewer saves
`.pms` text rather than a memory dump.

Earlier versions of `HANDOVER.md` / `ARCHITECTURE.md` declared the interactive
layer, the operator editor and `Iri` "intentionally not ported / out of
scope". That was wrong and has been corrected.

---

## 0. Error handling — the one place we must beat the original

The original deals with bad input in three non-portable ways:

| Original behaviour | Where | Port must instead |
|---|---|---|
| `CloseGraph` + message + **HALT** (kills the session) | `NodeMgr.LimitCheck` — node numbers on `.nod` load, `MaxLinks=12` overflow | raise `LimitExceeded`, keep the graph consistent, report in the UI |
| Clips out-of-range numbers **silently** | `UserIO.ReadInt/ReadLong` | reject with a reason, or state that the value was clamped |
| Stops at the first non-numeric byte, no error | `NodeMgr.ReadNodes` (`FIO.RdCard`) — truncated files look like valid small graphs | validate; report line/position (note: some hand-made `.nod` legitimately carry a trailing German comment) |
| **No validation at all** — no magic, no length check | `NodeMgr.LoadPoly` | verify structure and size (`178 + n*123`), raise `FileFormatError` |
| Fails silently when no link slot is free | `PM.Connect` | raise / report |
| Overwrites files without asking; `SavePicture` never calls `FIO.Close` | `NodeMgr.SavePicture` / `SavePoly` | confirm overwrite; use context managers |
| Accepts an invalid base | `PM.PermBasisValid` uses global `PM.Order`, which is 0 on the first edit → `NextPerm` aborts → returns `TRUE` unseen | **real bug**: validate independently of `Order` |
| Removing a link leaves the per-link marks pointing at the wrong edges | `PM.Disconnect` (`pm.mod:479`) shifts `links` and `opno` down and decrements `nlink`, but `lines` and `broken` (`nodemgr.def:39`) are addressed by the same index and stay where they were — `pmdisp.mod:72` and `pmprogs.mod:33` then read them against the shifted list | **real bug**: `Node.remove_link` moves everything indexed by link together. Reachable through Collapse/Uncollapse, the only callers of `Disconnect`; the `L` command toggles `broken` without disconnecting, which is why it survives normal use |
| Label whose digits don't sum to `Freq` → `SeekNode` returns 0 → silent no-op | Iridium `k`/`t` commands | reject with a message |

Design: a `PermutoError` hierarchy (`InvalidBase`, `InvalidCycle`,
`FileFormatError`, `LimitExceeded`, …) in the UI-free core. Core raises, the
PySide6 layer catches and displays. Never terminate the process.

---

## 1. Operating modes

The original is one program with three modes; the port has all three.

| Mode | Start | Port |
|---|---|---|
| Polytop | `polytop <file.nod>` — load a finished graph | `permuto show <name>` |
| Permutograph | `polytop /PG` — build permutographs interactively, default base `1234`, ops `12 23 34` | `permuto` (no argument) |
| Iridium | `polytop /I` | `permuto iridium` |

`Running = FALSE` is the **start state**: every iteration blocks on a keypress,
so any unbound key single-steps the relaxation. Reproduced.

## 2. Main menu, keys and status lines (`polytop.mod`)

Top line: `(A)lgo  (C)alc T|F  (R)un T|F  (H)urry T|F  (F)ile  (S)pin T|F  (N)ame  (P)rog[  (E)dit ]`
Bottom line: `iter=<n> dim=<d> nodes=<n>  A=<algorithm>`

| Key | Action | Port |
|---|---|---|
| `A` | cycle algorithm (Rubber, Rubber2, Ribbon, Mean, New) | done |
| `C` | calculating on/off | done |
| `R` | running (continuous) on/off | done |
| `S` | spinning on/off | done |
| `H` | HurryUp — draw seldom, suppress spin while calculating | done |
| `N` | NameMode 0..3 cycle (none / node# / perm / display); mode 2 skipped unless Permuto | done; mode 3 skipped too until SPA has run |
| `F` | file submenu | done |
| `P` | program submenu | done |
| `E` | operator editor (Permuto only) | done |
| `M` | collapse mask (`EdCollapseMask` is commented out in the original — resets `Iteration` only) | n/a |
| `ESC` | `UserWantsToExit()` — accepts `y/Y`, `j/J`, `o/O`, Enter | done |

`UserWantsToExit` (`userio.mod:17`) asks `Do You want to exit? (Y/N)` and takes
yes in three languages plus a bare Enter; anything else carries on. It guards
every way out: `ESC` in the main menu (`polytop.mod:431`), `ESC`/`Q` in the file
menu (`:443`) — note that the file menu's **(Q)uit ends the program**, it is not
a way back — and `ESC`/`Q` in Iridium (`:773`). One `exit_confirmed()` in
`ui/viewer.py` serves all three.

`HurryUp` is "compute fast, look seldom", and both halves matter:
`polytop.mod:299` skips the spin while calculating, and `:315` draws only at the
25-iteration checkpoints. In a Qt timer the second half is not free — one
`tick()` per timer event would make the switch pure loss — so the viewer runs
iterations until `tick()` asks for a redraw (`_run_a_frame`).

## 3. File submenu `(Q)uit (O)utput (L)oad (S)ave` — done

The open question below has been decided: the viewer **reads** `.ply` and
**writes** `.pms`, a line-oriented text format (`formats/pmsfile.py`).

> **The question, as it stood.** `SavePoly` is a raw memory dump
> (`FIO.WrBin` of `SIZE(NodeType)`), and its purpose was to preserve the
> *relaxed* state — `.nod` holds only topology, while settling into the final
> 3-D shape takes hundreds of iterations. In 1995 a dump was the cheapest way
> there. Its faults are visible in the files themselves: no magic, no version,
> no validation, uninitialised memory written along (50 junk bytes in
> `pg24.ply`), 16-bit coordinates that now collide with the port's 32-bit
> decision, and no diffability although the files live in git. The plan is to
> keep *reading* `.ply` and make a line-oriented **text** format the default for
> saving. See the task list; decide together with the file menu.

- **`.ply` binary load/save — the whole session state.** Verified byte-exact
  against `pg24.ply` (3130 = 178 + 24·123), `cube.ply`, `okt*.ply`,
  `ikosa*.ply`, `kubokt.ply`.
  Header (178 B): `Permuto:BOOL(1)`, `BasePerm:PermStr(9)`,
  `OpTable:6×3×PermStr(162)`, `LastEditLine:CARD(2)`, `Dimensions:CARD(2)`,
  `nnodes:INT(2)`.
  Node record (123 B, little-endian, no padding): `pos[8]` i16 @0,
  `old[8]` i16 @16, `color` @32, `num` @34, `nlink` @36, `links[12]` u16 @38,
  `opno[12]` u8 @62, `dead` @74, `active` @75, `display` i16 @76, `step` i16 @78,
  `sum` u16 @80, `lines[12]` u8 @82, `broken` bitset16 @94,
  `iri.avail/avbak/target/tarbak` @96, `iri.message.num/.color` @104,
  `iri.sender.repeat/.target/.color` @108, `perm:PermStr(9)` @114.
  **Load order matters**: read header → `NewPermutograph(TRUE)` to regenerate
  the graph (this is what sets `Order` and the `PermCache`) → then overwrite
  every node record. Loading also flips the Permuto flag.
- **PostScript preamble** (done — bundled as `src/permuto/formats/poly.pre`,
  prepended by `save_ps` by default). The raw `.p` body is not runnable on its
  own; `poly.pre` is the hand-written driver (auto-scaling to 14 cm, Helvetica
  8pt, hollow circles, `DefEdgeOp` draws the operator digit on the edge
  midpoint). `plots/namestr.pre` selects `LabelPos 1` (node number) instead of
  the default `2` (permutation string).
  The `(C) YCHI` byline is the author's own pseudonym: mis-heard from The Small
  Faces' *Itchycoo Park* (1967), adopted without understanding it, then
  forgotten — recovered here in 2026.

## 4. Program submenu — done

Menu line: `Kill/Repair (N)ode / (L)ine   run (S)PA  SP(T)A  (P)ARSUM`
(`(C)ollapse` and `(U)ncollapse` exist but are not advertised.)

| Key | Action | Port |
|---|---|---|
| `N` | toggle `state.dead` on a node | done |
| `L` | toggle `state.broken` on an edge — node 1 typed, neighbour picked with `SelectCard` | done |
| `C` | `PM.Collapse(n1, n2)` — merge n1 onto n2 | done |
| `U` | `PM.Uncollapse(n1)` — restore canonical edges via `ExecOperator` | done |
| `S` | SPA from a start node | done |
| `T` | SPTA — the original itself says "sorry, SPTA not yet available" | n/a |
| `P` | ParSum (requires a prior SPA run) | done |

Before the menu appears the original draws node numbers on **both** video
pages so the user can read the number to type.

## 5. Operator editor (`pm.mod`) — done

Permanently visible right of the picture (row 4, column 64); `E` enters edit
mode. One base line + 6 operators × 3 cycles = 19 fields (`MaxOps=6`,
`MaxCyc=3`). In the port: `render.paint_operator_panel` draws it,
`viewer._edit_key` / `_leave_edit` run it, `session.rebuild_permutograph`
finishes it. The section below stays because it documents *why* the editor
behaves as it does.

**How the solids actually arise** (decoded from the surviving `.ply` headers,
all of which are `Permuto = TRUE`): through **multiset bases**. Repeated
characters cut the node count from `n!` down to the size of the solid —
`cube.ply` has base `11111112` → 8!/7! = 8 nodes, `ikosa1/2.ply` and
`kubokt.ply` have `1123` → 4!/2! = 12, `okt3.ply` has `111112` → 6. Three
different bases (`123`, `1122`, `111112`) all reach the octahedron, which is
the "Zerlegung in Subpermutographen" of `denke.txt` in practice. Any port that
assumes distinct characters gets this wrong.

Grouping cycles into one operator (`MaxCyc`) is about *identity*, not topology:
`cube.ply` stores `18`+`27` as one operator and `36`+`45` as another. Since the
cycles are disjoint the resulting edges are the same as with six separate
operators — but grouped they share one operator number, hence one colour, and
four slots suffice where six would be spent.

| file | base | operators | result |
|---|---|---|---|
| `cube.ply` | `11111112` | `1234`, `5678`, `18`+`27`, `36`+`45` | 8 nodes, degree 3 |
| `ikosa1/2.ply` | `1123` | `123`, `234`, `12`+`34` | 12 nodes, degree 5 |
| `kubokt.ply` | `1123` | `123`, `234` | 12 nodes, degree 4 |
| `okt1.ply` | `123` | `123`, `12`, `23` | 6 nodes, degree 4 |
| `okt2.ply` | `1122` | `12`, `13`, `14`, `23`, `24`, `34` | 6 nodes, degree 4 |
| `okt3.ply` | `111112` | `123456`, `136425` | 6 nodes, degree 4 |
| `pg24.ply` | `1234` | `12`, `23`, `34` | 24 nodes, degree 3 |

- Digits only; **blocking validation** — a field cannot be left while invalid,
  not even with ESC (`REPEAT … UNTIL ok`).
- Keys: ↑/↓ (skipping the blank line after the base), Ctrl-Home → base line,
  Ctrl-End → last occupied operator field, ESC/Enter → leave.
- `LastEditLine` is remembered across invocations **and persisted in `.ply`**.
- Base is normalised by `FindBase` ("take minimum representation").
- On leaving: operator cycles invalid for the (possibly new) base length are
  cleared, then `NewPermutograph(reset = base changed or nnodes = 0)`.
  Same base → **incremental rebuild, positions kept**: *"this makes a nice
  move from one contexture to another"*. Different base → full rebuild.
  Either way `Iteration := 0`.
- Node colour in Permuto mode = position of the node permutation's first
  character in the base, +1. In Polytop mode `1 + (num-1) DIV 6` resp. `DIV 24`.
- Permutations **with repeats** are valid input (cf. `pm5_221.mod`, base
  `11223`, "der kleine fürs Telefon").

Supporting `PM` procedures the port needs: `PermName` (+ `PermCache`
bisection), `PermBasisValid`, `FindBase`, `ValidCycle`, `CyclicOperate`,
`ExecOperator`, `WhichOperator`, `FindLink`, `IsLinked`, `LinksAvail`,
`Connect`, `Disconnect`, `Collapse`, `Uncollapse`, `NewPermutograph`,
`PolytopFilter` (currently a stub returning `TRUE`).

## 6. Drawing (`PmDisp`) — done

- Operator digit at each edge midpoint, on a `BackColor` rectangle punched out
  of the edge. Guarded by `IF (names>0) & (progsel # P_SPTA)` (`pmdisp.mod:94`)
  — the *same* `names` that decides the ball labels and their size, so
  "write nothing" is one look, not two switches: small circles, no labels, bare
  links. `P_SPTA` is Iridium, which `render.paint_iridium` draws separately.
- Direction discs (`Graph.TrueDisc`, 3) at 1/6 of the edge for
  `L_input`/`L_output` — near own node for input, near neighbour for output.
  Colour says *that* an edge carries the wave, the disc says *which way*.
- Broken edges drawn black; `L_input`/`L_output` green, `L_locked` red.
- Depth cue `colour + 8` when `Dimensions >= 3` and `z + zz > 0` — the port
  dims the back edges instead; there is no 16-entry DOS palette to index into.
- Node size by NameMode: `0→5`, `1→9`, `2→12`, `3→9`.
- Ball colour is the node's own `color`, with `(color+8) MOD 16` for the front
  half. `color` comes from `Str.Pos(BasePerm, perm[0]) + 1` in permutograph mode
  (`pm.mod:352`), so it groups the permutations by first character, and from
  `1 + (num-1) DIV 6`, resp. `DIV 24` past 24 nodes, for a `.nod` graph
  (`polytop.mod:218`, the author's own comment: *"awkward"*).
- Dead nodes hollow (background disc + black circle); active nodes get an
  extra white circle one pixel out; labels **always black**, centred in the
  ball (`PlotCenteredStr(px, py, str, 0)`), on the node's palette colour.

  Do not "improve" this. Choosing the ink per ball by brightness or by WCAG
  contrast, and levelling the balls into one light band, were all tried on
  screen in July 2026 and rejected: the picture is meant to look like this.

### `TrueDisc`'s third argument is a **radius**

`Graph` is a library module and its source did not survive, so the sizes above
had to be read off the calls. Two things settle it: `TrueCircle(px, py, diam+1)`
rings a ball drawn at `diam`, which is only visible if the number is a radius;
and a four-character perm string in the 6×8 font cell is 24 px wide, so it fits
inside `diam = 12` exactly when that 12 is a radius. `PlotCenteredStr` puts it
there — the ball is sized around its label. Reading the number as a diameter
gives balls at half size with labels spilling out.

### Everything above is in the original's screen pixels — scale it

All the numbers in this section (font cell, node radii, disc radius 3, the
8×10 punch-out rectangle, line widths) are absolute pixels on the original's
screen: a **VGA** card in a 640×350 16-colour mode, where the drawing area
`_pic` was **479×320** (`pmdisp.def`). `ScreenHandler`'s source is lost, but the
geometry pins the mode down: `_scanlines = 350`, and `AspectX/AspectY = 350/480`
is exactly that mode's non-square pixel ratio — which is why a picture 479 wide
and 320 high came out square on screen. (`ham1.mod` and `kugel.mod` say it
outright: *"VGA-Karte nötig"*.)

The resolution is compiled in, but the **video pages are not**: the group ran
VGA and Super-VGA cards, and `polytop.mod:671` asks
`Graph.GetVideoConfig` for `numvideopages`. With more than one page the program
double-buffers — *"screen is built hidden and then shown"* — and `PagesToPrint`
makes sure a change is redrawn onto both pages before it stops. That is the one
place the program adapts to the card, and it needs no port: Qt composites
off-screen anyway.

The sizes must be scaled to today's drawing area, or they shrink to
illegibility in a large window. Take the *apparent* size of the original as the
target:

`render._scaled()` does that mapping, and `render.UI_SCALE` is the single knob
for the whole UI's apparent size (a faithful 1.0 reads a touch large today).

| Original | Fraction of `_pic` | At a 900 px drawing area |
|---|---|---|
| font cell 6×8 | 1.25 % w × 2.5 % h | ≈ 11 × 22 px |
| node radius 12 (perm labels) | 3.75 % h | ≈ 34 px |
| node radius 9 / 5 | 2.8 % / 1.6 % h | ≈ 25 / 14 px |
| direction disc r = 3 | 0.94 % h | ≈ 8 px |

`minifont.mod` is **lost** (only `minifont.obj` survives), so the glyphs cannot
be reproduced byte-exact. What mattered about it was that it was a
**fixed-width 6×8 cell** — so the replacement must be a monospace Qt font,
sized so that a character occupies the same fraction of the picture as it did
on the 479×320 original. Not "a small font": a proportionally large one.

## 7. Iridium / `Iri` — done

Own module (`core/iri.py`), independent of the permutograph generator; the
`/I` mode is `viewer.run_iridium`.

The intro calls it **SIMONE V1.4**. Per the author (2026-07-24): "damals war ich
in Simone etwas verknallt. ich habe mein programm deshalb SIMulation ONE
genannt" — a backronym for a name he had reason to like at the time. Keep the
name in the port; it is part of the program's history, like the `Poly.cry`
provenance.

### Where it comes from: `legacy/modula/salzdemo.txt`

The design is written down, and it survived. `salzdemo.txt` is the plan for a
demo made in and for **Salzburg**, where **Prof. Bernhard Mitterauer** lived —
he was with the group now and then. Forty lines, in two parts, recovered here
2026-07-26 with the author's account of who is who.

Part b), *"Katzenminze"*, is `Iri` before it was written:

> Alle Knoten erfragen periodisch die Verfügbarkeitscodes ihrer Nachbarn.
> Zerstörte Knoten antworten dabei garnicht, was als eine Verfügbarkeit von 0
> gerechnet wird. […] Each time a link is used, its availability decreases. The
> availability also increases automatically, like the charging of a capacitor.
> […] a broken node smears its unavailability out into its neighbourhood, and
> an information packet will be refracted on its route to walk around this area.

That is, line for line, `avail = 0.65·avail + 0.30·mean(neighbours) + 500`, the
discharge to 80 % on use, and the detour around dead satellites.

**`SPTA` was never specified and never built.** `SPA` is the shortest path
algorithm; `SPTA` was Gerhard G. Thomas's, and per the author (2026-07-26) the
specification never arrived, which is why the menu entry only ever answers
"sorry, SPTA not yet available".

What it was heading towards is legible, if not settled: **locally** shortest
paths, found from the network structure alone. `polytop.mod:409` has the call
commented out as `LocalShortestPath()`, and `salzdemo.txt` assumes it as given —
*"Angenommen, wir haben den SPTA. Dieser kann aufgrund der Netzwerkstruktur
lokal kürzeste Wege finden"* — and only then adds the availability code **on
top**. The author's own verdict (same day): it was not thought through to the
end. So the routing `Iri` implements is not SPTA; it is the layer that was to
sit above it.

That layer exists because it had to: there was a demo at **Motorola in
Chicago**, and something had to be on the screen. The Iridium simulation is what
was shown. The enum value survives as the display selector — `progsel = P_SPTA`
is what `PmDisp` checks to draw in Iridium mode.

One idea from it never got built, and it is credited in the file to "Jeff" —
**Jeff Myers**, senior at Motorola, whom the group visited in the USA when they
pitched around the early Iridium project:

> Depending on the priority of a message, it will take the availability code
> into account more or less. Urgent messages will take the shortest paths
> whenever possible. Less urgent messages try to avoid areas of low
> availability. That increases the overall availability and avoids local
> overloading.

Part a) is unbuilt too: generalised operators over "Platz- und Wertkontexturen",
a first step towards the Keno operator where **two nodes are linked when a
certain string match holds between them** — rather than by applying a cycle —
plus a zoom, computing on demand, and hiding individual operators.

- **Grid**: labels `"abc"` with `a+b+c = Freq = 9`; `limit = (F+1)(F+2)/2 = 55`
  nodes. Built by a boustrophedon `Sweep` (`"090"`, `"081" "180"`,
  `"270" "171" "072"`, …), 6 neighbour `Operate`s (one coordinate +1, one −1),
  bidirectional linking against already-created nodes only.
- **Availability** per step: `avail = 0.65·avail + 0.30·mean(neighbour avbak)
  + 500` (fixed point 10000). Dead nodes (`avail = 0`) are skipped and drag
  their neighbours down.
- **Routing** (`BestMove`): quality by L1 label distance — closer 5, sideways
  3, **backwards 2** — scored as `quality × availability / 5`; neighbours
  already holding a packet are avoided (one packet per node). Backwards is
  reachable, which is exactly the adaptive detour.
- **Movement**: selection on the `tarbak` snapshot, discharge to 80 % on use,
  arrival consumes the packet; a second pass recolours carriers and marks the
  destination blue.
- `Transmit(from, to, repeat)` with message numbers cycling 1..100 and a
  per-sender colour from `NextColor` (skips Blue/Yellow/Black); `Repeat()`
  re-injects stored jobs; `KillNode` toggles 0 ↔ 10000; `Reset` clears the
  network (**but not `MessageNumber`**).
- Display: node diameter `Scale(11, avail+1500, 10000)`; yellow = idle (shows
  label), otherwise the message number; blue = destination.
- Keys: `Kill  Transmit  Step  Repeat  Clear  Quit`, own 256-key ring buffer
  batching `s`/`S`/space/`r`/`R`, any other key flushes it. Typed "node
  numbers" are **labels** via `NumToLabel`, not indices.

Known defects in the original — reproduce the behaviour, but do not
reproduce the bugs silently; document each:
1. `Repeat` never decrements `sender.repeat` if the target is dead → job stuck
   forever, no timeout.
2. Killing a carrier loses its packet silently; `target` stays set, so it
   permanently blocks the collision check in `BestMove`.
3. Order dependence in `Movements`: pass 1 runs ascending and reads `target`
   **live** while availability comes from the `avbak` snapshot — low indices
   win conflicts. Needed 1:1 for identical results.
4. `namestr`/`toright` are never reset — a second build without module
   re-init starts at the wrong place.
5. Nodes 1 and 2 get identical start positions `(0, Norm)`.
6. The neighbour sum before division can reach 60000 — fits a 16-bit CARDINAL
   only because the triangular grid has ≤ 6 links. Document, don't reproduce.

## 8. Generators and graph tools — done

All AWK, none depend on the Modula code; all three are now in `gen/`.

* **`makeikos.awk`** — geodesic icosahedra, frequency 1..12 (`10f²+2` nodes).
  `nod/ikosa1..12.nod` are frozen outputs; `ikosa2` is used by
  `tests/test_layout.py` and the demo. Without the generator, arbitrary
  frequencies are impossible. (`makeiko.awk`, `makeiko1.awk`, `makeiko2.awk`
  are its predecessors — redundant.)
* **`trunc.awk` / `trunc2.awk`** — *factorisation*: truncate every permutation
  string to its first n characters, collapsing a permutograph onto a coarser
  one ("Dadurch wird pgl6 nach pgl6-4 faktorisiert"). This is the "Zerlegung in
  Subpermutographen" of `denke.txt` made operational; `nod/pgl6-4.nod` is the
  result, and its truncated labels are still visible in the file.
* **`vierdrei.awk`** — a different graph family altogether: "Vier Werte, 3
  Plätze", 4³ = 64 nodes with 9 edges each (every value change at every place
  is an edge), plus filter modes 0–3 that drop the all-equal and/or
  all-different nodes "um Struktur sehen zu können". Output: `nod/vierdrei.nod`.

Not needed: `zyk.awk` (the predecessor of `operate.awk`, prints `u(arg) = res`),
`num.awk` (superseded by `num2.awk`), `trans.awk` (a vocabulary-drill toy,
unrelated to the project).

### A note on reproducing the AWK output byte-for-byte

Not possible, and not worth chasing. `makeikos.awk` numbers nodes in the order
they come out of `for (tr in Tri)` / `for (i in Edges)`, i.e. the hash order of
Thompson AWK's associative arrays. It is visible in the data: in `ikosa1.nod`
the first triangle's edges `(a,b), (b,c), (a,c)` are emitted as `1 2 / 3 2 /
1 3`, which is the order `(a,c), (b,c), (a,b)` — neither sorted nor insertion
order. Without TAWK's hash function the numbering cannot be reconstructed. The
*graph* is well defined, so the port checks isomorphism against the originals
instead, which is the stronger statement anyway.

## 9. Input layer (`UserIO`) — one `FieldPrompt`

`InputStr(S, allowed, exit)` (character filter, Home/End/←/→/Del/Backspace,
Ins toggle, overwrite by default), `ReadInt/ReadLong/ReadReal(min, max, prec)`
(range handling — see §0), `SelectCard(a, len)` (cycle a list with space,
1-based result), `UserWantsToExit()`. Functionality matters, not the DOS
look — `ui/prompt.py`'s `FieldPrompt` and the viewer's input line are the
equivalent, and node picking uses `SelectCard`'s space/Enter cycle.

One thing is deliberately **not** reproduced: `InputStr`'s cursor and its
overwrite-by-default typing. Editing a field is append + Backspace, so retyping
a base means clearing it first. That was a DOS-terminal habit, not a feature of
the program (decided 2026-07-26) — and with it the last open item is closed.

---

## Not viewer features (verified: standalone experiments)

None of these import a project module, so none of them is needed for parity.
That does not make them worthless — see `kugel` below.

`ham1.mod` (Hamiltonian circle search, 4 algorithms), `h.mod` (one-off count —
"85477800 Wege der Länge 17 gibt es ab Knoten 1", result is in the comment),
`pm5.mod`/`pm5_221.mod` (brute-force variant; differs only in the start
permutation), `pmtest.mod` (ranking experiment with a documented failure),
`inzidenz.m` (Mathematica helper), `lj`/`ljtest.pas` (PCL printer test),
`num.awk` (superseded by `num2.awk`).

### `kugel.mod` — ported anyway, as `studies/kugel.py`

The author's 1991 study in getting a natural-looking lit sphere out of 14
colours: a hand-mixed deep-red-to-pink-white ramp, plus two ways of hiding the
quantisation — an ordered 4×4 dither (the pattern copied off the Windows 3.0
setup screen and drawn into the source as ASCII) and Floyd-Steinberg error
diffusion with a noise "Shake". One octant is computed and mirrored eight ways,
with the loops starting two pixels early so the error buffer is charged before
the visible part begins — that is what keeps the octant boundaries seamless.

It is the only place in the 1995 source that uses floating point, and the port
keeps it that way. Two things are documented rather than reproduced: the
ordered-dither branch kept the error arrays up to date but overwrote the
accumulated value first, so those stores never reached a pixel; and `Lib.RANDOM`
is source-less, so the shake takes a `seed` — same idea, different numbers,
and reproducible.

`permuto kugel [out.png] [size] [--floyd]`. The study is Qt-free and returns
palette indices; `render.indexed_image()` turns those into pixels and knows
nothing about spheres.
