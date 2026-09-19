#!/usr/bin/env python3
"""Build the web data bundle: merge unit metrics + geometry into compact JSON
served by the app. Splits GMU polygons per unit so the client can render only
what it needs."""
import json
import os

HD = "/opt/data/.scratch/huntdata"
OUT = "/opt/data/.scratch/huntmap/web/data"
os.makedirs(OUT, exist_ok=True)

units = {u["gmuid"]: u for u in json.load(open(f"{HD}/units_web.json"))}
gj = json.load(open(f"{HD}/gmus.geojson"))

# simplify polygons lightly? Keep as-is for accuracy; file ~28MB shape -> geojson maybe 15MB.
# Round coords to 5 decimals to shrink
def round_coords(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [round_coords(c) for c in coords]

out_feats = []
for f in gj["features"]:
    uid = int(f["properties"]["GMUID"])
    u = units.get(uid, {})
    geom = {"type": f["geometry"]["type"],
            "coordinates": round_coords(f["geometry"]["coordinates"])}
    out_feats.append({
        "type": "Feature",
        "id": uid,
        "properties": {
            "gmuid": uid,
            "county": u.get("county"),
            "elk_dau": u.get("elk_dau"),
            "hunt_score": u.get("hunt_score"),
            "habitat_score": u.get("habitat_score"),
            "harvest_score": u.get("harvest_score"),
            "public_pct": u.get("public_pct"),
            "success_pct": (u.get("harvest_2024") or {}).get("success_pct"),
            "hunters": (u.get("harvest_2024") or {}).get("hunters"),
            "total_harvest": (u.get("harvest_2024") or {}).get("total_harvest"),
            "harvest_density": u.get("harvest_density"),
            "sq_miles": u.get("sq_miles"),
        },
        "geometry": geom,
    })

with open(f"{OUT}/units.geojson", "w") as fh:
    json.dump({"type": "FeatureCollection", "features": out_feats}, fh, separators=(",", ":"))
print(f"units.geojson: {len(out_feats)} features, "
      f"{os.path.getsize(f'{OUT}/units.geojson')//1024} KB")