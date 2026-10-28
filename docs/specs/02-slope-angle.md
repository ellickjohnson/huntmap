# Spec 02 — Slope-angle shading layer (onX parity item #2)

Goal: toggleable slope-angle overlay that color-codes terrain steepness per cell,
matching onX Hunt's slope shading. Client-side only: NO new API routes, no new deps,
no build step. Parity doc palette (docs/onx-parity.md, "Slope angle" row):
5–15 green, 15–22 yellow, 22–30 orange, 30–40 red, 40–45 purple, 45+ blue.

## Implementation — `web/index.html` only

### DEM input (already in repo)

All three style objects (SATELLITE/TOPO/HYBRID, ~line 596+) already carry a
`raster-dem` source id `hillshade`: terrarium PNGs
`https://elevation-tiles-prod.s3.amazonaws.com/v2/terrarium/{z}/{x}/{y}.png`,
tileSize 256, `encoding: 'terrarium'`, maxzoom 15. Reuse the SAME tile URL for the
slope pipeline (independent fetches — do not couple to maplibre's internal source).
Note: this inherits the existing hillshade upstream dependency; if the dataset dies,
hillshade dies too (pre-existing risk, not a new one).

### Tile pipeline: maplibre `addProtocol('slope', ...)`

- Register ONCE at startup (global protocol, survives style swaps).
- Handler for `slope://{z}/{x}/{y}`:
  1. `fetch` the terrarium tile for the same z/x/y (8 s timeout via the
     AbortSignal maplibre passes — wire it, don't ignore it).
  2. Decode to ImageData (OffscreenCanvas or canvas, no external libs).
  3. Terrarium elevation: `elev_m = R*256 + G + B/256 - 32768`.
  4. Per-pixel slope from 1 px neighbors (clamp neighbors at tile edges; any missing
     neighbor tile → transparent pixel for that cell):
     - meters per pixel: `156543.03392 * cos(lat_center) / 2^z` where z is the TILE
       zoom and lat_center is the tile's center latitude;
     - `dz/dx`, `dz/dy` per pixel over that distance;
     - `slope_deg = atan(sqrt((dz/dx)^2 + (dz/dy)^2))`.
  5. Classify into the palette (<5° → fully transparent) and render RGBA.
  6. `canvas.toBlob` → ArrayBuffer, return `{data}` to maplibre.
- Failure mode: fetch error/timeout/undecodable → return a fully transparent tile +
  `console.warn` once per session (not per tile). Never throw into the tile loop;
  overlay just stays empty there.

### Source/layer

- `map.addSource('slope-dem', { type:'raster', tiles:['slope://{z}/{x}/{y}'],
  tileSize:256, minzoom:11, maxzoom:15 })` — maplibre overzooms z15 tiles above
  zoom 15 automatically.
- Layer `slope-classes`, type `raster`, `raster-opacity: 0.6`,
  `raster-resampling: 'nearest'` (keeps class boundaries crisp, no smoothing),
  minzoom 11. Insert ABOVE basemap raster layers, BELOW symbol/popup layers
  (use the first symbol layer id as beforeId when one exists).

### Toggle + gates

- Chip `📐 Slope` (`slopeChip`) as sibling of `#terrainChip` (~line 455), same styling.
- Slope layer visible only at map zoom >= 11 (below that onX-style classes are
  noise). On zoom crossing the threshold: add/remove `slope-classes` while toggle
  is on. Chip renders dimmed + `title` hint when below threshold.
- Toggle state persists in `localStorage['hm-slope']` ('1'/'0', default 0), same
  convention as `hm-theme`.
- BASMAP SWITCH GOTCHA (must handle): basemaps are whole-style `setStyle` swaps, so
  the slope source+layer vanish on every switch. On `style.load` after a switch, if
  toggle is on and zoom >= 11: re-add source + layer. Verify chip state stays lit.

### Legend

- Compact legend strip, bottom-left, ONLY while overlay is active: 6 swatches with
  ranges (5–15 / 15–22 / 22–30 / 30–40 / 40–45 / 45+), green→blue order, styled
  with existing panel vars (`var(--panel2)`, `var(--line)`, 11-12px). Hide when
  toggle off or below zoom gate.

### Colors (hex, translucent 0.6 handled by raster-opacity)

green `#4caf50` · yellow `#ffd24d` · orange `#ff9f1c` · red `#e63946` ·
purple `#9d4edd` · blue `#3b82f6`

## Perf guardrails

- Processed-tile cache: in-module Map keyed `z/x/y` → PNG bytes, LRU cap 200, evict
  oldest. No second cache layer beyond that + maplibre's own tile cache.
- Abort inflight tile work when maplibre aborts the request (fast pans).
- Slope math is synchronous over 256×256 — fine on main thread (~ms per tile).

## Out of scope (later items)

Click-to-query a cell's slope value; slope "favorable at marker" coloring (item #6,
needs marker `optimal_dir`); any DEM smoothing/FOV adjustments; lidar/bare-earth
sources (separate parity row).

## Acceptance (Hermes_One, independent on prod)

1. `slopeChip` toggle: overlay appears at zoom >= 11; known steep terrain
   (Maroon Bells / West Elks cliff bands) shows red/purple/blue; valley floors
   green. Classes not inverted.
2. Zoom out below 11 → overlay + legend gone, chip dimmed; zoom back in → returns.
3. Style switch (Satellite↔Topo↔Hybrid) with toggle on → layer re-added, chip stays
   lit, no console errors.
4. Legend visible only while active.
5. Diff vs main touches ONLY `web/index.html` + `docs/specs/02-slope-angle.md`;
   no API changes, no new deps, no external JS libs.
6. 30 s of panning at high zoom with overlay on → zero JS console errors.
7. GHA build green; app-bot: digest bump + stack reload + live verify; then
   Hermes_One runs this list fresh on prod.