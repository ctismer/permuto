# permuto

A modern **PySide6** reincarnation of Christian Tismer's 1990–95 Modula-2
**Polytop / Permutograph** viewer — recovered in 2026 from a 1997 e-mail
attachment and being ported to Python (see `docs/ARCHITECTURE.md`).

A *permutograph* has permutations as nodes and *operators* (products of
position cycles) as edges; the viewer embeds it in N‑dimensional space,
relaxes it into shape, and shows a rotating 2‑D projection. Rotating 4‑D+
objects this way looks glorious.

## Status

* **Generation pipeline ported and verified** — `genperm → operate → num2`
  regenerates 11 of the original graphs byte-for-byte (golden tests).
* Core (graph model, SPA, fixed-point layout/rotation) and the PySide6 viewer
  are next.

## Use

```bash
python -m permuto gen 123 12 + 23     # -> .nod on stdout  (= genperm|operate|num2)
python -m permuto pg  123 12 + 23     # -> .pg  on stdout
python -m permuto build myname 1234 12 + 23 + 34   # write myname.pg/.nod/.pgd
```

## Test

```bash
python -m pytest        # regenerates originals in legacy/modula/nod and compares
```

## Layout

* `src/permuto/` — the Python port (`gen/`, `formats/`, `core/`, `ui/`)
* `legacy/` — the recovered Modula-2 original (kept until the port is complete)
* `docs/ARCHITECTURE.md` — reverse-engineering notes & the port plan
