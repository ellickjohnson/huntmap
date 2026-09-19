#!/usr/bin/env python3
"""Compute per-GMU habitat-weighted elk density score.
For each GMU: intersect elk summer range + concentration areas with the GMU polygon,
weight by layer importance, normalize -> habitat_score 0-100.
Also record habitat area breakdown in table elk_habitat."""
import json
import sqlite3
from shapely.geometry import shape
from shapely.ops import unary_union

DB = "/opt/data/.scratch/huntdata/hunt.db"
HD = "/opt/data/.scratch/huntdata"

# Layer weights for a hunting-desirability score (fall rifle seasons: elk at
# summer/fall transition, but resident population + summer conc are the reliable signals)
WEIGHTS = {
    "elk_resident_population": 3.0,
    "elk_summer_concentration": 3.0,
    "elk_production": 2.0,
    "elk_summer_range": 1.5,
    "elk_winter_concentration": 0.5,
    "elk_winter_range": 0.25,
    "elk_overall_range": 0.1,
    "elk_migration_corridors": 0.25,
    "elk_migration_patterns": 0.5,
}

gmus = json.load(open(f"{HD}/gmus.geojson"))

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("DROP TABLE IF EXISTS elk_habitat")
cur.execute("""CREATE TABLE elk_habitat (
    gmuid INTEGER, layer TEXT, overlap_pct REAL, weight REAL,
    PRIMARY KEY (gmuid, layer))""")
cur.execute("ALTER TABLE gmus ADD COLUMN habitat_score REAL")
cur.execute("ALTER TABLE gmus ADD COLUMN harvest_score REAL")

gmu_shapes = {}
for feat in gmus["features"]:
    uid = int(feat["properties"]["GMUID"])
    gmu_shapes[uid] = shape(feat["geometry"])

for layer, weight in WEIGHTS.items():
    gj = json.load(open(f"{HD}/{layer}.geojson"))
    feats = gj["features"]
    if not feats:
        continue
    union = unary_union([shape(f["geometry"]) for f in feats if f.get("geometry")])
    print(f"{layer}: {len(feats)} feats, area {union.area:.2f}")
    for uid, g in gmu_shapes.items():
        if g.is_empty or g.area <= 0:
            continue
        inter = g.intersection(union)
        pct = inter.area / g.area * 100.0
        if pct > 0.05:
            cur.execute("INSERT OR REPLACE INTO elk_habitat VALUES (?,?,?,?)",
                        (uid, layer, round(pct, 2), weight))

# weighted habitat score: sum(weight * overlap)/sum(weight of layers present) capped 100
cur.execute("""SELECT gmuid, SUM(overlap_pct*weight)/SUM(weight) FROM elk_habitat GROUP BY gmuid""")
for uid, raw in cur.fetchall():
    # raw is average weighted overlap %, normalize against realistic max (~90)
    cur.execute("UPDATE gmus SET habitat_score=? WHERE gmuid=?", (round(min(raw / 0.9, 100.0), 1), uid))

con.commit()
for row in cur.execute("""SELECT g.gmuid, g.county, g.habitat_score, g.public_pct
                          FROM gmus g WHERE g.gmuid IN (14,16,161,17,171,6,201,214,191,2,5)
                          ORDER BY g.habitat_score DESC"""):
    print(row)
con.close()