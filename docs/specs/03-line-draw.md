# Spec 03 — Line draw + distance + elevation profile (onX parity item #3)

Goal: click-to-draw measuring lines on the map with live segment + total distance
readouts and an elevation profile chart, matching onX Hunt's Line Distance tool
(points are "as the crow flies", segment lengths shown per segment, units follow
the existing hm-units setting). Client-side only: NO API changes, no new deps,
no build step, no persistence.

Repo facts this builds on (verified @ abed22d):
- `UNITS_FMT.dist` (web/index.html:2284) already formats m → mi/km per hm-units.
- `map.queryTerrainElevation` already used in the marker save path (:2150, :2164);
  terrain is OPT-IN via ⛰️ 3D Terrain chip → elevation must not depend on it.
- Spec 02's terrarium pipeline (hillshade source, `addProtocol('slope', …)`,
  OffscreenCanvas decode, abort wiring, LRU discipline) is the proven pattern.

## Design decisions (the three forks, pinned)

1. **Draw UX: hand-rolled.** No mapbox-gl-draw/terra-draw — repo ethos is
   single-lib (maplibre CDN only) and onX's tool is plain click-to-drop. Enter /
   dblclick / ✅ button finish; Esc / ✕ cancel. Undo = Backspace pops last vertex.
   No vertex dragging, no mid-line insert, no polygon mode (later items).
2. **Elevation source: dual, terrain-first.** Distance (haversine, no DEM) is the
   primary readout and never depends on elevation. Elevation samples use
   `queryTerrainElevation` when 3D terrain is on and the SDK returns a number;
   otherwise fetch terrarium PNGs directly (same tile URL family as spec 02's
   `hillshade` source) and bilinear-sample the enclosing tile. Rationale: profile
   must work with terrain off (default state), while reusing the already-loaded
   tiles when terrain is on avoids duplicate traffic.
3. **Persistence: none.** No backend change at all. The `markers` table is
   scalar-only (`lat/lon REAL`, api/server.py:88-89) — there are no line-string
   markers to reuse; adding geometry columns + CRUD is a later item.

## Implementation — `web/index.html` only

### Draw flow

- Chip `📏 Measure` (`measureChip`) sibling of the slope/terrain chips (~line 455),
  same styling; toggles draw mode. State persists in `localStorage['hm-measure']`
  ('0' default — draw mode itself is not a session-crossing feature).
- While mode is on: map clicks (`map.on('click')`) push `[lng, lat]` vertices.
  Double-click and Enter finish; Esc cancels; Backspace removes last vertex;
  ✕ clears. Draw-mode clicks must not fire marker popups (guard the existing
  markers-dots click handler with the mode flag).
- Live rendering: one GeoJSON source `measure-src` + two layers, re-`setData` on
  every vertex:
  - `measure-line`, type `line`, dashed (`line-dasharray:[2,1.5]`), width 2,
    color `var(--accent2)` (#3edbc7);
  - `measure-verts`, type `circle`, radius 4, same color, stroke panel-bg.
  Re-add after basemap `setStyle` swaps (same `style.load` re-ensure hook the
  slope layer uses — basemap swap wipes sources/layers). While actively drawing,
  suppress the hover-rebuild path so the layers persist.
- Segment labels: `symbol` layer on the line source, `text-field` = per-segment
  distance (haversine, `UNITS_FMT.dist`), `symbol-placement: 'line'`,
  11px, halo. Grand total lives in a small fixed readout pill above the profile
  area (not a popup).

### Elevation profile

- On Finish: sample min 40, max 100 points along the line (vertex angles
  preserved — sample every vertex, subdivided to ≤ sample spacing so peaks
  can't be skipped between sparse vertices).
- Profile data: for each sample, elevation via the dual source above. Sample
  count capped at 100 → worst case ~100 tile fetches, mostly cache hits (adjacent
  samples share tiles at draw zooms).
- Chart: hand-rolled SVG area/line chart (`<svg>` + `<path>`), no chart lib —
  filled path in `--accent2` at low opacity, 1px stroke, min/max elevation
  labels, ground-distance x-axis in hm-units. Sized to existing panel
  dimensions, glass-token styling. Elevation readout via `UNITS_FMT.elev`.
- Gain/loss: sum of positive/negative deltas between consecutive samples,
  shown as `↑ gain / ↓ loss` in the readout pill next to the total distance;
  `—` when elevation source unavailable.
- Panel placement: opens as the existing bottom-sheet panel pattern (same
  behavior as the weather panel) with Close; reuses panel CSS vars.

### Elevation fallback fetch (shared discipline with spec 02)

- `longitudes-for-latitude`-style tile selection: for sample (lng, lat, z) use
  the tile containing the point at the current map zoom clamped to [11, 15]
  (terrarium maxzoom). Fetch with the same 8 s AbortSignal timeout pattern;
  decode via OffscreenCanvas; `elev_m = R*256 + G + B/256 - 32768`; bilinear
  interpolation between the 4 enclosing pixels.
- Reuse spec 02's cache discipline: one shared in-module LRU (keyed `z/x/y` →
  decoded elevation grid or tile bytes, cap 200, oldest evicted) instead of a
  second parallel cache. Concurrent duplicate fetches for the same tile must
  coalesce (inflight map).
- Failure mode: tile fetch/decode error → that sample is `null` (chart shows a
  gap in the affected x-range, gain/loss computed from available samples only);
  all-samples-null → profile area shows "Elevation unavailable" inline and the
  distance readout stays live. Never throw into the draw loop.

## Perf guardrails

- Profile samples are sequential batches of ~10 concurrent fetches (not 100
  parallel); abort inflight work if the user clears/cancels before completion.
- `setData` on vertex add is O(n) on a 2-digit-scale feature — fine; no debouncing
  beyond rAF batching of rapid clicks.
- No per-frame work: chart is built once per finished line.

## Out of scope (later items)

Saving measured lines (markers-table geometry), vertex drag/mid-insert editing,
polygon draw + area (onX Area Shape, separately ranked), snapping routes to
trails/roads, slope-value-at-profile-cursor overlay.

## Acceptance (Hermes_One, independent on prod)

1. Toggle 📏 Measure → click 2+ points → dashed line + per-segment labels render
   immediately; distances cross-checked against independent haversine math on
   the clicked coords (not the bundle's own numbers).
2. Finish → profile panel opens; x-axis totals match the drawn distance; spot
   terrain check: sample elevation at a known feature within tile-resolution
   tolerance (compare against an independent terrarium fetch, not the page's).
3. Terrain OFF (fresh profile, chip not lit) → profile still renders (fallback
   source worked); terrain ON → second profile renders, no console errors.
4. Esc cancels (no artifacts); Backspace removes last vertex; ✕ clears line +
   panel; basemap switch while line drawn on → layers re-added after swap
   (same re-ensure hook as slope).
5. Units toggle imperial↔metric → live labels + readouts + axis relabel without
   redraw of geometry.
6. Offline/tile-failure simulation (block elevation tiles) → distance stays,
   profile shows inline unavailable state, zero console exceptions.
7. Diff vs main touches ONLY `web/index.html` + `docs/specs/03-line-draw.md`;
   no API changes, no new deps, no external JS libs.
8. GHA build green; app-bot: digest bump + stack reload + live verify; then
   Hermes_One runs this list fresh on prod.