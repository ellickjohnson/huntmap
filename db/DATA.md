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

## API key note
TypeSafe AI key lives in Vaultwarden item "typesafeai" (visible only to machine
accounts on .145 — NOT readable from this drawer; use ssh docker exec crypto-bot
+ vw-fetch.py with OAEP-SHA1→SHA256 org key unwrap).