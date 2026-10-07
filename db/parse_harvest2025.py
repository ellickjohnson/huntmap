#!/usr/bin/env python3
"""Parse CPW 2025 elk harvest report (hunt-code format) -> SQLite, aggregated per GMU.

The 2025 report published by CPW dropped the per-section tables and publishes by
HUNT CODE only (e.g. EM161E1R -> antlered elk, GMU 161, rifle). The GMU digits are
chars 3-5 of the code (leading zeros). Codes with unit 000 are statewide OTC pools
(archery either-sex, rifle bulls) that span every OTC unit - they have no single GMU,
so they cannot be attributed per-unit (documented in DATA.md).

Also updates the harvest_history.json source series (2019-2025) from the mirrored
statewide PDFs so the frontend history charts and predictions use like-for-like data.
"""
import json
import re
import sqlite3
import sys
import urllib.parse

PDF = "/opt/data/cache/web/2025-elk-statewide-harvest.pdf"
DB = "/opt/data/.scratch/huntdata/hunt.db"

try:
    import pymupdf
except ImportError:
    sys.exit("pymupdf required (pip install pymupdf)")

CODE_RE = re.compile(r"^[A-Z]{2}(\d{3})[A-Z0-9]{1,3}\*?$")


def num(x):
    x = str(x).replace(",", "").rstrip("%")
    try:
        return int(x)
    except ValueError:
        return None


def parse_2025():
    d = pymupdf.open(PDF)
    rows = []
    for pi in range(3, d.page_count):  # pages 4..27 are hunt-code tables
        lines = [l.strip() for l in d[pi].get_text().split("\n") if l.strip()]
        i = 0
        while i < len(lines):
            m = CODE_RE.match(lines[i])
            if not m:
                i += 1
                continue
            code = lines[i]
            star = code.endswith("*")
            vals = [num(lines[i + 1 + k]) if i + 1 + k < len(lines) else None for k in range(5)]
            succ_s = lines[i + 6] if i + 6 < len(lines) else ""
            succ = float(succ_s.rstrip("%")) if succ_s.endswith("%") else None
            days = num(lines[i + 7]) if i + 7 < len(lines) else None
            rows.append(dict(code=code.rstrip("*"), star=star, unit=int(m.group(1)),
                             bulls=vals[0], cows=vals[1], calves=vals[2],
                             total=vals[3], hunters=vals[4], success=succ, days=days))
            i += 8
    return rows


def main():
    rows = parse_2025()
    print(f"parsed {len(rows)} hunt codes from 2025 PDF")
    statewide_h = sum(r["hunters"] or 0 for r in rows)
    statewide_t = sum(r["total"] or 0 for r in rows)
    print(f"statewide sums (codes incl. 000 pools): hunters={statewide_h:,} harvest={statewide_t:,}")
    assert statewide_t == 32120, f"statewide harvest mismatch: {statewide_t}"

    # update DB with 2025 hunt-code rows (year=2025)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS harvest_2025")
    cur.execute("""CREATE TABLE harvest_2025 (
        code TEXT PRIMARY KEY, unit INTEGER, star INTEGER,
        bulls INTEGER, cows INTEGER, calves INTEGER,
        total_harvest INTEGER, hunters INTEGER, success_pct REAL, rec_days INTEGER)""")
    for r in rows:
        cur.execute("INSERT OR REPLACE INTO harvest_2025 VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (r["code"], r["unit"], int(r["star"]), r["bulls"], r["cows"], r["calves"],
                     r["total"], r["hunters"], r["success"], r["days"]))
    con.commit()

    # per-GMU aggregation (excluding 000 statewide pools)
    agg = {}
    for r in rows:
        if r["unit"] == 0:
            continue
        a = agg.setdefault(r["unit"], {"hunters": 0, "total": 0, "bulls": 0, "cows": 0,
                                       "calves": 0, "days": 0})
        for k in ("hunters", "total", "bulls", "cows", "calves", "days"):
            if r[k]:
                a[k] += r[k]
    for u, a in sorted(agg.items()):
        a["success_pct"] = round(100 * a["total"] / a["hunters"], 1) if a["hunters"] else None
    json.dump({str(k): v for k, v in sorted(agg.items())},
              open("/opt/data/.scratch/huntdata/gmu_2025.json", "w"), indent=1)
    print(f"wrote {len(agg)} GMUs -> gmu_2025.json")
    for u in (2, 10, 161, 61, 201):
        print(" GMU", u, agg.get(u))
    con.close()


if __name__ == "__main__":
    main()