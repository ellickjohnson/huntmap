---
name: huntmap-data
description: >
  CPW elk hunting data pipeline for huntmap.ellickjohnson.net. Sources, scoring
  method, and refresh commands. Built 2026-09-19.
---

# HuntMap Data Pipeline

## What exists
- DB: `/opt/data/.scratch/huntdata/hunt.db` (SQLite)
  - `gmus` — 186 GMU polygons (WGS84 geojson in `gmus.geojson`), public_pct, habitat_score, harvest_score, hunt_score
  - `harvest` — 2024 CPW report, 1,962 rows, 32 sections (per-season + All Manners)
  - `elk_habitat` — per-GMU overlap % for 9 elk layers
- Web export: `units_web.json` (per-unit metrics) — built by `final_scores.py`
- Habitat layers: `/opt/data/.scratch/huntdata/elk_*.geojson` (10 files, 3,747 feats)
- Land ownership: `landown_nwco.geojson` (9 statewide agency parcels)
- GMU source: official CPW shapefile (2026-08-27 vintage), NAD83 UTM13N -> WGS84 via pyproj

## Scoring method (hunt_score 0-100)
0.35 × success_pct(2024 All Manners, minmax norm) + 0.30 × habitat_score/100
+ 0.15 × public_pct/100 + 0.20 × harvest_density (harvest/sq mi, minmax norm)

habitat_score = weighted avg overlap of elk layers (resident_pop ×3, summer_conc ×3,
production ×2, summer_range ×1.5, winter layers low-weight, migration ×0.25-0.5),
normalized to /0.9.

## Refresh (each season)
1. Download new CPW harvest PDF (spl.cde.state.co.us / cpw elk statistics page)
2. Update `parse_harvest3.py` year + rerun
3. Rerun `final_scores.py`
4. Rebuild app data bundle

## 2025+ hunt-code format (added 2026-10-07)
From 2025 CPW publishes by HUNT CODE only (e.g. EM161E1R — GMU digits at chars 3-5),
dropping per-GMU "All Manners" tables. `parse_harvest2025.py` handles this:
- parses PDF → `harvest_2025` table + `gmu_2025.json` per-GMU aggregation
- `web/data/harvest_history.json` gains a `2025` key per unit (flagged `"partial": true`)
- ⚠️ 2025 hunter counts are LOWER-BOUND vs 2019-2024: codes with unit `000` are
  statewide OTC pools (all OTC GMUs, e.g. EM000U2R = 23,668 rifle bulls) and cannot
  be attributed to a single unit. Success% per attributed code is still valid.
  Trend comparisons for HUNTER counts should use 2019-2024 like-for-like; the
  crossover model in `crossover.py` damps low-confidence fits accordingly.

## Crossover predictions (added 2026-10-07)
`crossover.py` → `web/data/predictions.json` per GMU:
- linear trend of hunters + success over 2019-2025 (R²-damped)
- `crossover_year`: where normalized hunter trend crosses below success trend
- `est_2026` / `pred_2027`: projected hunters + success%
- `crossover_score` 0-100: 50 + 3×(hunters %/yr decline) + 4×(success pp/yr gain),
  damped toward 50 by fit confidence (R²)
Frontend: "Crossover" metric button, crossover panel in unit details, predictions
layer served from PUBLIC_DATA.

Direct official PDFs (Widen DAM CDN pattern discovered 2026-10-07):
`https://cpw.widen.net/content/<asset-id>/pdf` — 2025 elk = `8uno656mtu`,
2024 elk = `wkisb2j1f4`.

## API key note
TypeSafe AI key lives in Vaultwarden item "typesafeai" (visible only to machine
accounts on .145 — NOT readable from this drawer; use ssh docker exec crypto-bot
+ vw-fetch.py with OAEP-SHA1→SHA256 org key unwrap).