#!/usr/bin/env python3
"""Per-GMU public-land % via area-weighted overlay using shapely.
Intersection of each GMU polygon with each of the 9 agency parcels -> area ratio.
Run inside /opt/data/.venv-hunt (shapely)."""
import json
import sqlite3
from shapely.geometry import shape, Point
from shapely.ops import unary_union

DB = "/opt/data/.scratch/huntdata/hunt.db"

gj = json.load(open("/opt/data/.scratch/huntdata/gmus.geojson"))
land = json.load(open("/opt/data/.scratch/huntdata/landown_nwco.geojson"))

# Preload land parcels as shapely geoms keyed by agency class
PUBLIC = {"BLM", "USFS", "NPS", "FWS", "ST", "LG", "OTHFE", "USBR"}
parcels = []
for f in land["features"]:
    code = f["properties"]["ADMIN_AGENCY_CODE"]
    parcels.append((code, shape(f["geometry"]))) if False else None
parcels = [(f["properties"]["ADMIN_AGENCY_CODE"], shape(f["geometry"])) for f in land["features"]]

# Union public parcels for fast containment (may be heavy but 9 polys is fine)
public_geoms = [g for c, g in parcels if c in PUBLIC]
private_geoms = [g for c, g in parcels if c not in PUBLIC]
public_u = unary_union(public_geoms)
print("public union done")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("ALTER TABLE gmus ADD COLUMN public_pct REAL")

for feat in gj["features"]:
    uid = int(feat["properties"]["GMUID"])
    geom = shape(feat["geometry"])
    if geom.is_empty:
        continue
    area_total = geom.area
    if area_total <= 0:
        continue
    inter = geom.intersection(public_u)
    pct = inter.area / area_total * 100.0
    cur.execute("UPDATE gmus SET public_pct=? WHERE gmuid=?", (round(pct, 1), uid))

con.commit()
# report on the E-6 units
for row in cur.execute("""SELECT gmuid, county, public_pct, acres FROM gmus
                          WHERE gmuid IN (14,16,161,17,171,6,201,214,191,5,2) ORDER BY gmuid"""):
    print(row)
con.close()