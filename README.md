# ellickjohnson/huntmap

Colorado elk hunting unit heatmaps — harvest success, habitat quality, and public
land access for all 186 CPW Game Management Units, with an interactive 2D/3D map.

## Stack
- **Frontend**: vanilla ES modules, MapLibre GL JS v5 + deck.gl v9 (3D extrusions)
- **Data**: SQLite (units + harvest) + GeoJSON (boundaries + habitat layers)
- **API**: tiny Python HTTP server (stdlib only)
- **Deploy**: Docker image → GHCR → Portainer git-backed stack → NPM → huntmap.ellickjohnson.net

## Data sources (all public/official)
- CPW Big Game GMU boundaries (shapefile, 2026-08-27)
- CPW 2024 Elk Harvest report (per-unit, per-season estimates)
- CPWSpeciesData FeatureServer (elk summer/winter ranges, concentration areas, migration)
- BLM Surface Management Agency layer (land ownership)

## Scoring
`hunt_score = 0.35·success_norm + 0.30·habitat_norm + 0.15·public_norm + 0.20·harvest_density_norm`

See `db/DATA.md` for the full methodology and refresh procedure.

## Dev
```
cd web && python3 -m http.server 8085   # serves static map, uses /data/ JSON
```

## License
Data © Colorado Parks & Wildlife (public domain). Code MIT.