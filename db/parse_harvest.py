#!/usr/bin/env python3
"""Parse CPW 2024 elk harvest report -> SQLite, keeping sections distinct."""
import json
import re
import sqlite3

SRC = "/opt/data/cache/web/spl.cde.state.co.us-8e154cfe67.md"
DB = "/opt/data/.scratch/huntdata/hunt.db"

text = open(SRC).read()
lines = text.split("\n")

section = None
rows = []
row_re = re.compile(
    r"^\|\s*(\d{2,3})\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*"
    r"\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|")
section_re = re.compile(r"^\*\*(.+)\*\*\s*$")

for line in lines:
    sm = section_re.match(line.strip())
    if sm:
        section = sm.group(1).strip()
    m = row_re.match(line.strip())
    if m and section and "2024 Elk Harvest" in section:
        unit, bulls, cows, calves, tot, hunters, succ, days = m.groups()
        try:
            vals = [int(x.replace(",", "")) for x in (unit, bulls, cows, calves, tot, hunters, days)]
        except ValueError:
            continue
        rows.append({
            "unit": vals[0], "bulls": vals[1], "cows": vals[2], "calves": vals[3],
            "total": vals[4], "hunters": vals[5], "success": float(succ), "days": vals[6],
            "section": section,
        })

# sanity: the All Manners of Take row for 161
manners = [r for r in rows if "All Manners of Take" in r["section"] and r["unit"] == 161]
print("unit 161 All Manners row:", manners)

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("DROP TABLE IF EXISTS harvest")
cur.execute("""CREATE TABLE harvest (
    year INTEGER, unit INTEGER, section TEXT,
    bulls INTEGER, cows INTEGER, calves INTEGER,
    total_harvest INTEGER, hunters INTEGER, success_pct REAL, rec_days INTEGER,
    PRIMARY KEY (year, unit, section))""")
for r in rows:
    cur.execute("INSERT OR REPLACE INTO harvest VALUES (?,?,?,?,?,?,?,?,?,?)",
                (2024, r["unit"], r["section"], r["bulls"], r["cows"], r["calves"],
                 r["total"], r["hunters"], r["success"], r["days"]))
con.commit()
print("rows inserted:", cur.execute("SELECT COUNT(*) FROM harvest").fetchone()[0])
print("sections:", cur.execute("SELECT COUNT(DISTINCT section) FROM harvest").fetchone()[0])
for row in cur.execute("""SELECT unit, total_harvest, hunters, success_pct FROM harvest
                          WHERE section LIKE '%All Manners%' AND unit IN (14,16,161,17,171,6)
                          ORDER BY unit"""):
    print(row)
con.close()