# Spec 04 — Area shape + acreage (onX parity build item #4)

Goal: click-to-draw polygon areas with live acreage readout, matching onX Hunt's
Area Shape tool. Client-side only: NO API changes, no new deps, no build step,
no persistence. Sits beside the measure-line tool (spec 03) with shared
discipline — but is a separate draw mode, per this spec.

Repo facts this builds on (verified @ main = spec-03 branch base):
- Spec 03 shipped the full hand-rolled draw framework: `measure-src` +
  `measure-line`/`measure-verts`/`measure-labels` layers, vertex loop,
  keyboard map (Enter/Esc/Backspace), style.load re-ensure hook,
  click-suppression guards on gmu-fill/burn-area/land-fill/markers-dots/placing.
- Spec 03's terrarium elevation pipeline (LRU 200, coalesce, 8s abort,
  bilinear decode) is available for area elevation stats.
- `UNITS_FMT.area` (module scope, web/index.html) formats mi²/km² per hm-units;
  acreage needs a new formatter (acre = mi² × 640; hectare = km² × 100).

## Design decisions (pinned)

1. **Mode: same chip is a mode, not a sibling tool.** The onX toolbar has
   separate line/shape buttons; Huntmap's rail is chip-based. Decision: chip
   `📐 Area` sibling of 📏 Measure. While Area mode is ON, map clicks plant
   polygon vertices; Escape/Esc key cancels; dblclick or ✓ closes the ring;
   Backspace pops last vertex; ✕ clears. Same pattern as measure-line — one
   muscle memory, fewer states.
2. **Acreage math: geodesic spherical excess.** Area of a polygon on the
   sphere via the standard spherical-excess formula (Chamberlain & Duquette,
   the same method turf.js ships): `sum over edges of (λ2−λ1)(2+sin φ1+sin
   φ2) × R²/2`, absolute value, half is not needed if formula used as
   documented. R = 6371008.8 m. Output acres = m² × 0.000247105; hectares =
   m² × 0.0001. Sanity gate: Colorado GMUs are 100k–1000k acres — the readout
   must land in plausible ranges for known shapes (unit test: a 1°×1° square
   at 39°N ≈ 5,893 mi² ≈ 3.77M acres ±1%).
3. **Rendering: reuse the measure-* source/layers family** with new ids
   `area-src` / `area-fill` (fill-opacity 0.25, `--accent2`, same beforeId
   positioning) / `area-outline` (dashed, 2px) / `area-verts` (circle) /
   `area-labels` (grand-total text at the ring center via `symbol-placement:
   'point'` on a single point feature — polygon centroids in geojson sources
   are risky at high zoom; use the average of vertices clamped inside, or the
   centroid of the largest triangle if that's cheap — decision: simple mean
   of vertex coords is fine at these zooms). Live per-edge? No — onX shows just
   total ac; edge segments remain Measure-line's job.
4. **No elevation dependency.** Acreage never requires DEM. Optional future
   item: mean elevation inside area (stretch, not this spec).
5. **Persistence: none** (same as spec 03).
6. **Click suppression: same flags as measure mode.** The `_measureActive`
   getter pattern gets a sibling flag OR — better — the guards check a shared
   `window._drawMode` that is true when either mode is on (keeps the existing
   guards 1:1, no new call sites; internal to the PR).

## Out of scope (later items)

Holes/lakes, self-intersection validation (onX doesn't either), saving shapes
(schema change, later item), area perimeter readout (cheap stretch: show
perimeter under acreage — include it, one line of code).

## Acceptance (Hermes_One, independent on prod)

1. Toggle 📐 Area → click 4+ points → translucent fill + dashed outline
   renders immediately; acreage readout live in the pill + at ring center.
2. Acreage sanity: draw a rough rectangle of known screen size, independent
   math (spherical excess, computed outside the page) matches within 1%.
3. Finish (✓/dblclick) → pill shows acreage + perimeter; Esc clears fill (no
   artifacts); Backspace pops a vertex with area updating live.
4. Units toggle → acreage ↔ hectares, mi² ↔ km² relabel live.
5. Basemap switch while shape drawn → layers re-add after swap.
6. Both modes coexist: Area active while Measure chip off; toggling one does
   not clear the other's drawn feature until its own ✕.
7. Diff vs main touches ONLY `web/index.html` (+ docs/specs/04-area.md);
   no API changes, no new deps.
8. GHA build green; deploy lane per ruling; acceptance on prod after deploy.