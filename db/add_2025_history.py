#!/usr/bin/env python3
"""Add 2025 data (per-GMU hunt-code aggregation) to web/data/harvest_history.json.

NOTE: 2025 came from CPW's new hunt-code-only report format; the 000 statewide
OTC pools can't be attributed to individual units, so 2025 hunter counts are
LOWER-bound (draw-code hunters) vs prior years' All-Manners counts. Success% is
still valid per unit (harvest/hunters within attributed codes) but user-facing
charts get a caveat flag. See DATA.md.
"""
import json

HIST = "/opt/data/huntmap-repo/web/data/harvest_history.json"
GMU25 = "/opt/data/.scratch/huntdata/gmu_2025.json"

hist = json.load(open(HIST))
gmu25 = json.load(open(GMU25))

added = 0
for u, rows in gmu25.items():
    if not rows.get("hunters"):
        continue
    hist.setdefault(u, {})["2025"] = {
        "total": rows["total"],
        "hunters": rows["hunters"],
        "success": rows["success_pct"],
        "days": rows["days"],
        "bulls": rows.get("bulls") or 0,
        "cows": rows.get("cows") or 0,
        "calves": rows.get("calves") or 0,
        "partial": True,  # hunt-code-format caveat, see DATA.md
    }
    added += 1

json.dump(hist, open(HIST, "w"), indent=1)
print(f"added 2025 to {added} units; years now:",
      sorted({int(y) for u in hist for y in hist[u]}))
u = hist.get("2", {}).get("2025")
print("sample GMU 2/2025:", u)
missing = [u for u in hist if "2025" not in hist[u]]
print(f"units without 2025 ({len(missing)}):", missing[:20])