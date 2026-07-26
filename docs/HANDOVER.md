# Handover — permuto (Modula-2 → Python port)

Read this first, then `docs/ARCHITECTURE.md` and `git log --oneline`.

## Where we are

**Parity is reached — phase 2 is done.** Every mode, menu, program, drawing
detail, format and generator of the 1995 original exists in the port.
`docs/PORT-GAPS.md` is no longer a work plan; it is the record of what the
original did and where the port decided otherwise.

- `main` is the port; `recovered-original` holds the pristine 1995 import.
- **Remote**: `origin = git@github.com:ctismer/permuto.git` (public, MIT).
  Christian pushes; check `git status` for unpushed commits.
- `python -m pytest` — 217 tests.
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
memory dump (§3), dimmed back edges instead of the `colour + 8` palette trick
(§6), and no `InputStr` overwrite typing — a DOS-terminal habit, not a feature
(§9). Everything else follows the original.

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
permuto                          # /PG mode, base 1234 -- no arguments needed
permuto show pgl4                # keys: a c r h s n f p e · ESC quits
permuto iridium                  # /I mode (SIMONE)
python -m permuto render pgl5 out.png 700
python -m permuto export pgl4 out.ps 600
```

## Next — phase 3 = pythonic refactor
Parity was the floor and it is reached, so improvements are now allowed — the
strict-1:1 rule has done its job and no longer binds. What does still bind: the
core stays **UI-free**, and the golden tests against `legacy/modula/nod/*` and
the 1995 `.ply` files must stay green through any refactor. They are what makes
it safe.

Afterwards: optionally TypeScript/browser on the cleaned core.

## Gotchas
- **Coordinates always need a scale.** `NORM = 2**24`, and anything much
  smaller projects to a single dot. `layout.frame()` is called by every
  producer of coordinates — `Graph.random_init`, `PM.new_permutograph` for a
  fresh graph, `Session` for whatever a session file brought along. Do not
  re-add `normalize()` calls at the use sites; add them at the producer.
- `HurryUp` is "compute fast, look seldom" — it suppresses the spin *while
  calculating* (`polytop.mod:299`), so it must earn that back in iterations.
  The viewer's `_run_a_frame` runs a whole checkpoint per timer tick.
- The sizes `TrueDisc`/`TrueCircle` were called with are **radii**, not
  diameters — the ball is sized around the label that goes inside it. See
  PORT-GAPS §6; `Graph`'s source is lost, so this was read off the call sites.
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
