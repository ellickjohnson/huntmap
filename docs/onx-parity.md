# onX Hunt parity plan

Inventory of onX Hunt features (from onxmaps.com docs, Oct 2026) vs Huntmap current state.
Sources: onxmaps.com/hunt/app/features (+29 feature pages), webapp crawl; huntmap `web/index.html`,
`api/server.py`, `db/`.

## Status legend
HAVE = exists today | PART = partial | GAP = missing | SKIP = app-only, out of scope for a web map

## Core map
| Feature | onX | Huntmap | Action |
|---|---|---|---|
| Satellite/Topo/Hybrid basemaps | yes | yes (gmaps imagery/opentopo/cartocdn) | done |
| 3D terrain + exaggeration | yes | yes (DEM, exaggeration slider) | done |
| Lidar / bare-earth view | yes | GAP | USGS 3DEP 1m WMS toggle (CO coverage is good) |
| Recent imagery | yes | SKIP (imagery already current via gmaps) | — |
| Offline maps | mobile app | PART (web) | PWA service worker: cache tiles + /data JSON |
| Desktop web map | yes | yes (native, this IS web) | done |

## Land & layers
| Feature | onX | Huntmap | Action |
|---|---|---|---|
| Private parcels + owner/acreage | 161M parcels | PART (CO public parcels, viewport-fetched) | verify owner-name popup coverage |
| Public land (BLM/USFS/state) | yes | yes (BLM layer) | done; consideradd USFS/state |
| GMU/hunt units | nationwide | CO only (186 units, by design) | done |
| Habitat/species layers | state layers | yes (elk summer/winter/resident/migration) | done |
| Burns/wildfire | yes | yes (MTBS 1984-2024) | done |
| Trails | yes | yes (COTREX) | done |
| Crop/soil/timber-cut layers | yes | GAP | CDSS/CropScape WMS if wanted (low priority for elk) |
| Slope angle (color-coded) | yes | GAP | **build**: hillshade DEM -> per-cell slope classes (onX palette: grd 5-15, yel 15-22, org 22-30, red 30-40, pur 40-45, blu 45+) |
| CWD distribution | yes | GAP | CPW CWD prevalence ArcGIS layer |
| Roadless/wilderness | yes | PART via BLM | CPW/Conservation Biology Institute wilderness layer |

## Markups
| Feature | onX | Huntmap | Action |
|---|---|---|---|
| Waypoints w/ icons+colors | ~100 icons, 10 colors | PART (few fixed types) | icon/color picker on marker create/edit |
| Waypoint notes/photos | yes | PART (notes via marker update) | photo upload (api + object storage in stack) |
| Lines + distance | yes | GAP | **build**: MapLibre draw-line, haversine len readout |
| Area shapes + acreage | yes | GAP | **build**: polygon draw, geodesic area readout |
| Elevation profile | via line tool | GAP | sample raster-dem along line, profile chart |
| Tracker (record track) | mobile GPS | SKIP (desktop web; mobile could get geolocation watchPosition later) | defer |
| Folders / shares w/ partners | yes | GAP | per-user marker ownership exists; add share tokens or trip folders (needs product call) |
| GPX export | yes | yes | done |

## Weather / conditions
| Feature | onX | Huntmap | Action |
|---|---|---|---|
| Point weather forecast | 100k stations | GAP | **build**: Open-Meteo (free, no key) point forecast panel: temp/precip/pressure |
| Hourly wind speed+dir (8d) | yes | GAP | **build**: same Open-Meteo hourly call, wind arrow readout |
| Wind calendar on waypoints | yes | GAP | store per-marker wind heading; "favored/not" badge from forecast |
| Optimal wind direction | yes | GAP | marker field: optimal dir; compare vs forecast dir |
| Wind comparisons (multi-point) | yes | GAP | table of saved markers' wind at picked day/hour |
| Sunrise/sunset/moon | yes | GAP | computed (sunrise-sunset formula + moon phase table) in weather panel |

## Unit intel (Huntmap ALREADY LEADS here)
Hunt score, 5-yr harvest trends, draw odds + pool allocation, crossover units, NR 2028 rule
impact, DAU herd info, AI chat assistant, admin user mgmt, themes, mobile responsive rail.
onX has none of this per-unit analysis. Keep, don't duplicate effort.

## onX features deliberately skipped
SOS, trail cameras, connected optics, CarPlay/Android Auto, offline device-to-device sharing,
compass mode (mobile sensor), rut calendar/deer forecast (deer-specific; elk movement forecast
could be a moon+weather index later — stretch goal), social feeds.

## Live walkthrough (webmap.onxmaps.com, signed in via Google, Oct 27)
Layers panel (real UI): top toggle trio **Gov Lands / Private Land / Possible Access**
(on=green; Possible Access = walk-in/easement access programs, OFF by default).
Categories: Colorado (2 of 3 layers on) · Current Conditions (0) · Land & Access (15) ·
Roads, Trails & Rec (5) · Trees, Crops & Soil (11) · Wildlife Layers (9). Recent strip:
Trail Mileages, CO Species Activity, CO Walk In Access, Possible Access, Private Land,
Sections. State gate: Colorado ON / Alaska OFF — multi-state + several categories are
ELITE-paywalled. Huntmap's CO-only scope matches the free/premium tier here.
Right toolbar: line, shape, waypoint, tracker, photo, note, measure ruler, wind icon
(red "B" beta badge) + insights bar-graph icon. Bottom-right: compass, weather cloud,
zoom, basemap chip "Hyb 2D", locate-me.

Parity takeaways beyond the doc tables above:
- **Possible Access** (CPW Walk-In Access + similar programs) is a distinct toggle from
  private land onX treats as first-class — public CO data exists; good Huntmap layer #7b.
- Wind/weather is live on WEB (beta) — confirms gap #1/#6 design (per-point wind,
  calendar, optimal-wind).
- Basemap chip is a single cycling control (Hyb/2D/3D) — Huntmap's 4-basemap menu is fine.
- "Sections" (PLSS township/section grid) is a recent-used layer: cheap to add (public
  BLM PLSS GeoJSON) and hunters do use it.

## Build order (impact-per-effort, elk/CO use case)
1. Weather+wind panel (Open-Meteo) + sunrise/moon      — 1 session, no data engineering
2. Slope angle layer from existing raster-dem          — 1 session
3. Line draw + distance + elevation profile            — 1-2 sessions
4. Area shape + acreage                                — same session as 3
5. Marker icon/color picker + photos                    — 1-2 sessions (api storage)
6. Wind calendar + optimal wind + comparisons           — 1 session (depends on 1)
7. 3DEP lidar toggle, USFS/state land layers           — 1 session
8. CWD layer (CPW source), print/PDF view              — 1 session each
9. Offline PWA caching                                  — 1 session
10. Folders/sharing                                     — product decision first