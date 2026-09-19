#!/usr/bin/env python3
"""Final scoring: composite hunt_score per GMU -> units_web.json export."""
import json
import sqlite3

DB = "/opt/data/.scratch/huntdata/hunt.db"
OUT = "/opt/data/.scratch/huntdata/units_web.json"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("SELECT * FROM gmus")
gmus = {r["gmuid"]: dict(r) for r in cur.fetchall()}
cur.execute("""SELECT unit, total_harvest, hunters, success_pct, rec_days, bulls, cows, calves
               FROM harvest WHERE section LIKE '%All Manners%'""")
h = {r["unit"]: dict(r) for r in cur.fetchall()}


def norm(vals, invert=False):
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [0.5] * len(vals)
    out = [(v - lo) / (hi - lo) for v in vals]
    if invert:
        out = [1 - o for o in out]
    return out


uids = sorted(gmus.keys())
success = [h.get(u, {}).get("success_pct") or 0 for u in uids]
habitat = [gmus[u].get("habitat_score") or 0 for u in uids]
public = [gmus[u].get("public_pct") or 0 for u in uids]
density = [(h.get(u, {}).get("total_harvest") or 0) / (gmus[u]["sq_miles"] or 1) for u in uids]

s_n = norm(success)
h_n = [x / 100 for x in habitat]
p_n = [x / 100 for x in public]
d_n = norm(density)

for i, uid in enumerate(uids):
    composite = 100 * (0.35 * s_n[i] + 0.30 * h_n[i] + 0.15 * p_n[i] + 0.20 * d_n[i])
    gmus[uid]["harvest_score"] = round(100 * s_n[i], 1)
    gmus[uid]["hunt_score"] = round(composite, 1)
    gmus[uid]["harvest_density"] = round(density[i], 3)
    if uid in h:
        gmus[uid]["harvest"] = h[uid]

con.commit()

out = []
for uid, g in gmus.items():
    hv = g.get("harvest", {})
    out.append({
        "gmuid": uid, "county": g["county"], "elk_dau": g["elk_dau"],
        "sq_miles": g["sq_miles"], "center": [g["center_lon"], g["center_lat"]],
        "public_pct": g["public_pct"], "habitat_score": g["habitat_score"],
        "harvest_score": g["harvest_score"], "hunt_score": g["hunt_score"],
        "harvest_density": g["harvest_density"],
        "harvest_2024": {k: hv[k] for k in
                         ("total_harvest", "hunters", "success_pct", "rec_days", "bulls", "cows", "calves")
                         if hv},
    })
json.dump(out, open(OUT, "w"))
print("exported", len(out), "units ->", OUT)
top = sorted(out, key=lambda x: -x["hunt_score"])[:10]
print("top 10 by hunt_score:")
for t in top:
    hv = t["harvest_2024"]
    print(f"  GMU {t['gmuid']:>3} score {t['hunt_score']:>5} | success {hv['success_pct']:>4}% | habitat {t['habitat_score']} | public {t['public_pct']}%")
con.close()