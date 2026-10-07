#!/usr/bin/env python3
"""Rebuild ALL harvest history from official CPW PDFs (2019-2025), normalized.

Source PDFs: spl.cde.state.co.us mirrors (2019-2023) + Widen DAM (2024, 2025).
- 2019-2024: per-GMU "All Manners of Take" tables (GMU = 3-digit code at line start)
- 2025: hunt-code rows (GMU at chars 3-5 of code) + 4 statewide OTC pool codes (000)
  -> pool allocated per-unit by that unit's 2019-2023 avg share (flagged estimated)
Output: hunt.db.harvest_years (replaced) + web/data/harvest_history.json (rebuilt).

Statewide validation targets (All Manners / All Seasons basis):
 2019: ~219,295 hunters / 37,095 harvest | 2020: ~212,667/39,014 | 2021: ~215,305/35,230
 2022: ~206,498/40,418 | 2023: ~184,261/29,344 | 2024: ~178,011/36,308
 2025: 161,580 hunters (attributed 110,128 + pool 51,452) / 32,120 harvest ✓
"""
import re
import json
import sqlite3
import pymupdf

VENV_PDF = None  # run with /opt/data/.venv-pdf/bin/python

DB = '/opt/data/.scratch/huntdata/hunt.db'
HIST = '/opt/data/huntmap-repo/web/data/harvest_history.json'
PDFS = {
    2019: '/opt/data/.scratch/huntdata/harvest_pdfs/2019.pdf',
    2020: '/opt/data/.scratch/huntdata/harvest_pdfs/2020.pdf',
    2021: '/opt/data/.scratch/huntdata/harvest_pdfs/2021.pdf',
    2022: '/opt/data/.scratch/huntdata/harvest_pdfs/2022.pdf',
    2023: '/opt/data/.scratch/huntdata/harvest_pdfs/2023.pdf',
    2024: '/opt/data/.scratch/huntdata/2024-elk.pdf',
    2025: '/opt/data/cache/web/2025-elk-statewide-harvest.pdf',
}


def parse_allmanners(path, year):
    """Parse per-GMU All Manners tables. Unit codes are 1-3 digits (no leading
    zeros in 2019-2023 reports, 3-digit zero-padded in 2024). Rows: unit line
    followed by bulls, cows, calves, total, hunters, success%, rec-days."""
    d = pymupdf.open(path)
    units = {}
    for pi in range(d.page_count):
        txt = d[pi].get_text()
        if 'All Manners of Take' not in txt:
            continue
        lines = [l.strip() for l in txt.split('\n') if l.strip()]
        i = 0
        while i < len(lines):
            if re.fullmatch(r'\d{1,3}', lines[i]) and i + 7 <= len(lines):
                try:
                    vals = [int(lines[i+j].replace(',', '')) for j in range(1, 6)]
                    pct = float(lines[i+6].replace('%', '').replace(',', ''))
                    days = int(lines[i+7].replace(',', ''))
                    u = str(int(lines[i]))
                    if u not in units:
                        units[u] = dict(bulls=vals[0], cows=vals[1], calves=vals[2],
                                        total=vals[3], hunters=vals[4], success=pct, days=days)
                    i += 8
                    continue
                except (ValueError, IndexError):
                    pass
            i += 1
    return units


def parse_2025(path):
    """Parse hunt-code rows; return (attributed per-unit, pool codes).
    Code format: [A-Z]{2}{unit:3d}[A-Z0-9]{1,3} optionally ' *' (e.g. EM000U2R,
    EF161E1R*). Unit 000 = statewide OTC pool (not attributable per-unit)."""
    d = pymupdf.open(path)
    codes = []
    code_re = re.compile(r'^[A-Z]{2}(\d{3})[A-Z0-9]{1,3}\*?$')

    def num(x):
        x = str(x).replace(',', '')
        try:
            return int(x)
        except ValueError:
            return None

    for pi in range(d.page_count):
        lines = [l.strip() for l in d[pi].get_text().split('\n') if l.strip()]
        i = 0
        while i < len(lines):
            m = code_re.match(lines[i])
            if not m:
                i += 1
                continue
            code = lines[i].rstrip('*')
            vals = [num(lines[i + 1 + k]) if i + 1 + k < len(lines) else None for k in range(5)]
            succ_s = lines[i + 6] if i + 6 < len(lines) else ''
            succ = float(succ_s.rstrip('%')) if succ_s.endswith('%') else None
            days = num(lines[i + 7]) if i + 7 < len(lines) else None
            codes.append(dict(code=code, bulls=vals[0] or 0, cows=vals[1] or 0,
                              calves=vals[2] or 0, total=vals[3] or 0,
                              hunters=vals[4] or 0, success=succ or 0, days=days or 0))
            i += 8
    # dedupe (page overlap)
    seen, out = set(), []
    for c in codes:
        if c['code'] not in seen:
            seen.add(c['code'])
            out.append(c)
    attributed = {}
    pool = []
    for c in out:
        m = code_re.match(c['code'] + 'X')  # re-match against stripped code: pad to pass
        m2 = re.match(r'^[A-Z]{2}(\d{3})', c['code'])
        u = str(int(m2.group(1))) if m2 else None
        if u == '0':
            pool.append(c)
        elif u:
            a = attributed.setdefault(u, dict(hunters=0, total=0, bulls=0, cows=0, calves=0, days=0, codes=0))
            a['hunters'] += c['hunters']; a['total'] += c['total']
            a['bulls'] += c['bulls']; a['cows'] += c['cows']; a['calves'] += c['calves']
            a['days'] += c['days']; a['codes'] += 1
    for u in attributed:
        attributed[u]['success'] = round(attributed[u]['total'] / max(1, attributed[u]['hunters']) * 100, 1)
    return attributed, pool


def norm2025_pool(attributed, pool, hist):
    """Allocate OTC pool harvest/hunters per unit by 2019-2023 historic avg share."""
    tot_pool_h = sum(c['hunters'] for c in pool)
    tot_pool_t = sum(c['total'] for c in pool)
    tot_pool_b = sum(c['bulls'] for c in pool)
    tot_pool_cw = sum(c['cows'] for c in pool)
    tot_pool_cv = sum(c['calves'] for c in pool)
    share = {}
    for u in hist:
        vals = [hist[u][y]['hunters'] for y in ('2019', '2020', '2021', '2022', '2023') if y in hist[u]]
        if vals and u != '0':
            share[u] = sum(vals) / len(vals)
    s = sum(share.values())
    for u in sorted(set(list(attributed.keys()) + list(share.keys()))):
        a = attributed.setdefault(u, dict(hunters=0, total=0, bulls=0, cows=0, calves=0, days=0, codes=0))
        w = share.get(u, 0) / s if s else 0
        a['hunters'] += round(tot_pool_h * w)
        a['total'] += round(tot_pool_t * w)
        a['bulls'] += round(tot_pool_b * w)
        a['cows'] += round(tot_pool_cw * w)
        a['calves'] += round(tot_pool_cv * w)
        a['pool_alloc'] = True
        a['success'] = round(a['total'] / max(1, a['hunters']) * 100, 1)
    return attributed


def main():
    hist = {}
    for year, path in PDFS.items():
        if year == 2025:
            attributed, pool = parse_2025(path)
            attributed = norm2025_pool(attributed, pool, hist)
            for u, a in attributed.items():
                hist.setdefault(u, {})[str(year)] = dict(
                    total=a['total'], hunters=a['hunters'], success=a['success'],
                    days=a['days'], bulls=a['bulls'], cows=a['cows'], calves=a['calves'])
        else:
            units = parse_allmanners(path, year)
            for u, a in units.items():
                hist.setdefault(u, {})[str(year)] = a
        print(f"{year}: {sum(1 for u in hist.values() if str(year) in u)} units — "
              f"{sum(h[str(year)]['hunters'] for h in hist.values() if str(year) in h):,} hunters, "
              f"{sum(h[str(year)]['total'] for h in hist.values() if str(year) in h):,} harvest")

    # WRITE: harvest_years table (replace all) + harvest_history.json
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS harvest_years_v2")
    cur.execute("""CREATE TABLE harvest_years_v2 (
        year INTEGER, unit TEXT, bulls INTEGER, cows INTEGER, calves INTEGER,
        total_harvest INTEGER, hunters INTEGER, success_pct REAL, rec_days INTEGER,
        partial INTEGER DEFAULT 0, PRIMARY KEY (year, unit))""")
    rows = []
    for u, yrs in hist.items():
        for y, a in yrs.items():
            rows.append((int(y), u, a.get('bulls', 0), a.get('cows', 0), a.get('calves', 0),
                         a.get('total', 0), a.get('hunters', 0), a.get('success', 0),
                         a.get('days', 0), 1 if a.get('pool_alloc') else 0))
    cur.executemany("INSERT OR REPLACE INTO harvest_years_v2 VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    json.dump(hist, open(HIST, 'w'), indent=1)
    print(f"wrote harvest_years_v2 ({len(rows)} rows) + {HIST} ({len(hist)} units)")


if __name__ == '__main__':
    main()