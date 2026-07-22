# Permuto — Architecture & Reverse-Engineering Notes

Modern (PySide6) reincarnation of Christian Tismer's 1990–95 Modula-2
**Polytop / Permutograph** viewer. This document records what the original
does — verified from the recovered sources — and the plan for the port.

Provenance: the original was deleted years ago and survived only as an
encrypted attachment (`Poly.cry`) in a 1997 e-mail; decrypted and recovered
in 2026. See the repository root `CLAUDE.md`.

---

## 1. What the program is

A **permutograph** is a graph whose nodes are permutations of a base string
and whose edges connect permutations that differ by an *operator* (a product
of position cycles). Nodes live as **integer vectors in N‑dimensional space**
(N up to 8); the viewer relaxes them into a symmetric shape and shows a
rotating **orthographic 2D projection**. Because the objects are genuinely
4‑D and higher, a rotating N‑D→2D projection (not 3‑D) is what reveals the
structure.

Pipeline (see `legacy/modula/permuto.bat`):

```
genperm <base> | operate <ops> > name.pg     # permutations -> edge list
num2 < name.pg                 > name.nod     # strings -> node numbers
polytop name.nod                              # relax + rotate + draw
```

---

## 2. Module map

Domain logic — **source present**, to be ported:

| Modula module | file | role |
|---|---|---|
| `GenPerm` | genperm.mod | list all permutations of the base |
| `perms` | perms.mod/.def | `NextPerm` — lexicographic next permutation |
| `NodeMgr` | nodemgr.mod/.def | node/graph data model, `.nod` load, PS/binary save |
| `PM` | pm.mod/.def | permutograph construction & editing |
| `PmProgs` | pmprogs.mod/.def | the SPA (shortest-path) program on the graph |
| `PmDisp` | pmdisp.mod/.def | projection to screen + edge drawing |
| `PCalc` | pcalc.mod/.def | layout: relaxation + spin (all integer) |
| `IntVector` | intvecto.mod/.def | integer fixed-point vector ops |
| `TextPlot` | textplot.mod/.def | bitmap text-on-graphics |
| `Iri`, `PCalc`, … | | supporting logic |
| `Polytop` | polytop.mod | main program / event loop |

Infrastructure — **source absent** (shipped as `.obj`), all trivially
replaced; **nothing algorithmic is missing**:

| module | used symbols | Python replacement |
|---|---|---|
| `MATHLIB` | Sin, Cos, ASin, ACos, Sqrt | `math` |
| `Lib` | RANDOM | `random` |
| `Storage` | ALLOCATE, DEALLOCATE, Available | n/a (GC) |
| `ScreenHandler` | GotoXY, WhereX/Y, ClrEol, SetupGraph2, CloseGraph | PySide6 |
| `MiniFont` | First, Last, PixX, PixY, PixDX | bitmap font / Qt fonts |
| `IO`,`FIO`,`Str`,`Graph`,`Window`,`BiosIO`,`KEY`,`DosUtil`,`Lib1`,`MacFns` | TopSpeed/DOS runtime | Python stdlib + PySide6 |

Dialect: **TopSpeed / JPI Modula-2** (DOS). Not directly `gm2`-buildable, but
irrelevant — we reimplement, not recompile.

---

## 3. On-disk formats

### `.pgd` — generating command (one line)
```
permuto <name> <base> <op tokens...>
```
e.g. `permuto pgl3 123 12 + 23`.

### `.pg` — edge list with permutation strings
One line per source permutation: `src nbr1 src nbr2 …`, one `(src,nbr)` pair
per operator. `genperm` emits the sources in lexicographic order.

### `.nod` — same, numbered
`num2` numbers nodes 1..k by first appearance of each line's first field
(= `genperm` order; node 1 = base) and replaces every permutation string by
its number.

**Worked example** (`pgl3`, base `123`, ops `12 + 23`):

```
.pg   line 1:  123 213 123 132     # 123 —(swap pos 1,2)→ 213 ;  123 —(swap 2,3)→ 132
.nod  line 1:  1 3 1 2             # 123=1, 213=3, 132=2
```

Note: when `NodeMgr.ReadNodes` **loads** a `.nod`, it just reads a flat stream
of integers in `(from,to)` pairs and builds an **undirected, deduped, sorted**
adjacency. The `src` repetition and the operator order are *not* recovered —
edges become plain topology (operator identity is only kept in the binary
`.poly` save format).

---

## 4. Generation semantics (ported & verified)

* **`operate`** — an *operator* is one or more cycles (digit strings) over the
  1‑based **positions** of the permutation; `+` separates operators. A cycle
  rotates places, reading source characters from the pre-cycle state. Each
  operator yields one neighbour edge per node.
* **`num2`** — pure renumbering, as above.

The Python port lives in `src/permuto/gen/` and `src/permuto/perms.py` and is
locked to the originals by golden tests (`tests/test_generation_golden.py`):
**11 recovered graphs regenerate byte-for-byte** — `alle6, knuepfli, pgl3,
pgl4, pgl5, pgl6, reflekt4, reflekt5, test, triprism, zykel`.

---

## 5. The viewer maths — all **integer fixed-point**, no float, no trig lib

`polytop.mod` deliberately uses no `REAL` (comment 17.12.91: *"absolutely no
more REAL necessary. 11k code saved"*).

**Fixed point** (`IntVector`): `Norm = 4096` is treated as `1.0`. `Scale(x,mul,div)
= x*mul DIV div` is the fixed-point multiply; `Sqr`/`Sqrt` are integer.

**Rotation** (`PCalc.Spin`): small fixed angle per step in the (1,3) plane:
```
rots = Norm DIV 120                 # sin ≈ angle (small-angle)
rotc = Sqrt(Sqr(Norm) - Sqr(rots))  # cos = √(1 − sin²), so sin²+cos² = Norm² (no length drift)
x' = Scale(x,rotc,Norm) + Scale(z,rots,Norm)
z' = Scale(z,rotc,Norm) - Scale(x,rots,Norm)
```

**Projection** (`PmDisp.DrawEdges`): orthographic — take components 1,2 as
screen x,y (y flipped), scaled by `Scale_X/Y` (~95 % of half the picture) to
the picture centre. Component 3 (`z`) is only a **depth cue**: front edges
(`z+zz > 0`) are drawn brighter.

**Layout / relaxation** (`PCalc`) — positions are **emergent**: start (random)
and relax each frame. Operators:

* `Contract(alg)` — pull each node toward its graph neighbours (read from
  `old`, so it is a Jacobi update). Five spring models: `Rubber`, `Rubber2`
  (length-weighted), `Ribbon`, `Mean`, `New` (equalize edge lengths).
* `Squeeze` — pull each node's length toward the mean → onto a common shell
  ("closer to a sphere").
* `Punish` — scale coordinate `i` by `Norm²/(Norm + i·Norm/400)`, i.e.
  gently shrink higher dimensions. **Design rationale (author):** the objects
  liked to become high-dimensional; rather than compute anything clever, the
  heuristic *punishes high dimensions a little, so it tumbles down as far as
  it must — but no further.* `CanShrink` detects when the top axis has
  collapsed → the object visibly "falls" from 4‑D into 3‑D into 2‑D.
* `Normalize` — recentre (mean → 0) and rescale so max length = `Norm`.

Main loop (in `polytop.mod`): `Backup → Contract → Squeeze → Punish →
Normalize → Spin → draw`, repeated → the graph relaxes into its symmetric
form while spinning.

---

## 6. Port plan & status

Project layout:

```
legacy/                  # the recovered Modula-2 original (delete when done)
  modula/                # *.mod/.def, nod/, plots/, *.awk, permuto.bat, …
  Poly_decrypted.zip     # pristine baseline
  Poly.cry, Crypt.pas    # provenance
  mail-fragments/        # the individually e-mailed SPA fragments (duplicates)
src/permuto/
  perms.py               # NextPerm                              [done]
  gen/                   # genperm, operate, num2, pipeline       [done, verified]
  formats/               # .pg/.nod/.pgd readers                  [done]
  core/                  # NodeMgr, PM, PmProgs, IntVector, PCalc [next]
  ui/                    # PySide6 2D-projection viewer           [next]
tests/                   # golden tests vs legacy/modula/nod/*
docs/ARCHITECTURE.md
```

**Phase 1** — strict 1:1 port, verified against the `nod/` golden files
(`IntVector`, rotation, `Scale`/`Sqrt` reproduced bit-exact; keep coordinates
`int`). *Done so far:* the whole generation pipeline.
**Phase 2** — refactor to idiomatic Python once behaviour is locked.
**Phase 3** — optional TypeScript/browser port of the (then clean) UI-free core.

The core stays **UI-free** so PySide6 and a later web viewer are just frontends.

### To confirm when porting the core
* Where `Dimensions` is set and how `pos` is seeded (looks like random init +
  relaxation; `RandomVector` + `PM`/`polytop` main — `ReadNodes` sets neither).
* Exact `Contract` algorithm chosen by default and the main-loop cadence.
* Whether initial positions ever use the permutation itself (permutohedron).
