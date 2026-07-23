# Port gaps — what the Python port still owes the Modula-2 original

Status: **the port is not feature-complete.** Phase 1 delivered the viewer
core (generation, relaxation, projection, SPA/ParSum, PostScript). This
document lists, verified against `legacy/modula/`, everything the original
can do that the port cannot yet.

Rule for this phase: **reach parity first.** Improvements beyond the original
are welcome afterwards — with the single exception of error handling, where
the original's behaviour is not portable (see §0).

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
| Label whose digits don't sum to `Freq` → `SeekNode` returns 0 → silent no-op | Iridium `k`/`t` commands | reject with a message |

Design: a `PermutoError` hierarchy (`InvalidBase`, `InvalidCycle`,
`FileFormatError`, `LimitExceeded`, …) in the UI-free core. Core raises, the
PySide6 layer catches and displays. Never terminate the process.

---

## 1. Operating modes

The original is one program with three modes; the port only has the first.

| Mode | Start | Port |
|---|---|---|
| Polytop | `polytop <file.nod>` — load a finished graph | **done** |
| Permutograph | `polytop /PG` — build permutographs interactively, default base `1234`, ops `12 23 34` | **missing** |
| Iridium | `polytop /I` | **missing** |

Also missing: `Running = FALSE` is the **start state** — every iteration
blocks on a keypress, so any unbound key single-steps the relaxation.

## 2. Main menu, keys and status lines (`polytop.mod`)

Top line: `(A)lgo  (C)alc T|F  (R)un T|F  (H)urry T|F  (F)ile  (S)pin T|F  (N)ame  (P)rog[  (E)dit ]`
Bottom line: `iter=<n> dim=<d> nodes=<n>  A=<algorithm>`

| Key | Action | Port |
|---|---|---|
| `A` | cycle algorithm (Rubber, Rubber2, Ribbon, Mean, New) | done |
| `C` | calculating on/off | done |
| `R` | running (continuous) on/off | **missing** (no single-step mode) |
| `S` | spinning on/off | done |
| `H` | HurryUp — draw seldom, suppress spin while calculating | **missing** |
| `N` | NameMode 0..3 cycle (none / node# / perm / display); mode 2 skipped unless Permuto | partly |
| `F` | file submenu | **missing** |
| `P` | program submenu | partly |
| `E` | operator editor (Permuto only) | **missing** |
| `M` | collapse mask (`EdCollapseMask` is commented out in the original — resets `Iteration` only) | n/a |
| `ESC` | `UserWantsToExit()` — accepts `y/Y`, `j/J`, `o/O`, Enter | **missing** |

## 3. File submenu `(Q)uit (O)utput (L)oad (S)ave` — all missing

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
- **PostScript preamble.** Our `.p` output is not runnable on its own; it
  needs `legacy/modula/plots/poly.pre` (auto-scaling to 14 cm, Helvetica 8pt,
  hollow circles, `DefEdgeOp` draws the operator digit on the edge midpoint).
  Ship or embed it. `plots/namestr.pre` selects `LabelPos 1` (node number)
  instead of the default `2` (permutation string).

## 4. Program submenu — partly missing

Menu line: `Kill/Repair (N)ode / (L)ine   run (S)PA  SP(T)A  (P)ARSUM`
(`(C)ollapse` and `(U)ncollapse` exist but are not advertised.)

| Key | Action | Port |
|---|---|---|
| `N` | toggle `state.dead` on a node | **missing** |
| `L` | toggle `state.broken` on an edge — node 1 typed, neighbour picked with `SelectCard` | **missing** |
| `C` | `PM.Collapse(n1, n2)` — merge n1 onto n2 | **missing** |
| `U` | `PM.Uncollapse(n1)` — restore canonical edges via `ExecOperator` | **missing** |
| `S` | SPA from a start node | done |
| `T` | SPTA — the original itself says "sorry, SPTA not yet available" | n/a |
| `P` | ParSum (requires a prior SPA run) | done |

Before the menu appears the original draws node numbers on **both** video
pages so the user can read the number to type.

## 5. Operator editor (`pm.mod`) — missing entirely

Permanently visible right of the picture (row 4, column 64); `E` enters edit
mode. One base line + 6 operators × 3 cycles = 19 fields (`MaxOps=6`,
`MaxCyc=3`).

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

## 6. Drawing (`PmDisp`) — missing details

- Operator digit at each edge midpoint, on a `BackColor` rectangle punched out
  of the edge (suppressed in Iridium mode).
- Direction discs (`Graph.TrueDisc`, r=3) at 1/6 of the edge for
  `L_input`/`L_output` — near own node for input, near neighbour for output.
- Broken edges drawn black; `L_input`/`L_output` green, `L_locked` red.
- Depth cue `colour + 8` when `Dimensions >= 3` and `z + zz > 0`.
- Node diameter by NameMode: `0→5`, `1→9`, `2→12`, `3→9`.
- Dead nodes hollow (background disc + black circle); active nodes get an
  extra white circle at `diam+1`; labels always black, centred in the ball.

### Everything above is in EGA pixels — scale it

All the numbers in this section (font cell, node diameters, disc radius 3, the
8×10 punch-out rectangle, line widths) are absolute pixels on a 640×350 EGA
screen, where the drawing area `_pic` was **479×320** (`pmdisp.def`). They must
be scaled to today's drawing area, or they shrink to illegibility in a large
window. Take the *apparent* size of the original as the target:

| Original | Fraction of `_pic` | At a 900 px drawing area |
|---|---|---|
| font cell 6×8 | 1.25 % w × 2.5 % h | ≈ 11 × 22 px |
| node diameter 12 (perm labels) | 3.75 % h | ≈ 34 px |
| node diameter 9 / 5 | 2.8 % / 1.6 % h | ≈ 25 / 14 px |
| direction disc r = 3 | 0.94 % h | ≈ 8 px |

`minifont.mod` is **lost** (only `minifont.obj` survives), so the glyphs cannot
be reproduced byte-exact. What mattered about it was that it was a
**fixed-width 6×8 cell** — so the replacement must be a monospace Qt font,
sized so that a character occupies the same fraction of the picture as it did
on EGA. Not "a small font": a proportionally large one.

## 7. Iridium / `Iri` — missing entirely

Own module (`core/iri.py`), independent of the permutograph generator.

The intro calls it **SIMONE V1.4**. Per the author (2026-07-24): "damals war ich
in Simone etwas verknallt. ich habe mein programm deshalb SIMulation ONE
genannt" — a backronym for a name he had reason to like at the time. Keep the
name in the port; it is part of the program's history, like the `Poly.cry`
provenance.

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

## 8. Generators

`makeikos.awk` — geodesic icosahedra, frequency 1..12 (`10f²+2` nodes) — is
**not ported**. `nod/ikosa1..12.nod` are frozen outputs of it; `ikosa2` is used
by `tests/test_layout.py` and the demo. Without the generator, arbitrary
frequencies are impossible. ~80 lines, no dependencies. (`makeiko.awk`,
`makeiko1.awk`, `makeiko2.awk` are its predecessors — redundant.)

## 9. Input layer (`UserIO`) — no equivalent yet

`InputStr(S, allowed, exit)` (character filter, Home/End/←/→/Del/Backspace,
Ins toggle, overwrite by default), `ReadInt/ReadLong/ReadReal(min, max, prec)`
(range handling — see §0), `SelectCard(a, len)` (cycle a list with space,
1-based result), `UserWantsToExit()`. Functionality matters, not the DOS
look — Qt validators and an input line in the viewer are the equivalent.

---

## Out of scope (verified: standalone experiments, not viewer features)

`ham1.mod` (Hamiltonian circle search, 4 algorithms, imports no project
module), `h.mod` (one-off count — "85477800 Wege der Länge 17 gibt es ab
Knoten 1", result is in the comment), `kugel.mod` (Floyd-Steinberg dithered
sphere, unrelated), `pm5.mod`/`pm5_221.mod` (brute-force variant; differs only
in the start permutation), `pmtest.mod` (ranking experiment with a documented
failure), `inzidenz.m` (Mathematica helper), `lj`/`ljtest.pas` (PCL printer
test), `num.awk` (superseded by `num2.awk`).
