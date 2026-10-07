#!/usr/bin/env python3
"""Policy-aware prediction adjustment: folds CPW regulatory changes into predictions.

Known policies (researched 2026-10-07, sources in db/DATA.md):
1. NR OTC archery eliminated west of I-25 + GMU 140 (limited, since 2025 season)
   -> NR archery pressure down in affected units (2024 baseline: ~13,000 NR archery OTC)
2. Gunnison Basin GMUs 54/55/551: OTC 2nd/3rd rifle bull -> limited draw from 2026,
   phase-in near 3yr avg or <=10% below OTC use
3. GMU 82 antler point restrictions removed (2026) -> higherSuccess there
4. 2028 DRAW OVERHAUL: uniform 75/25 R/NR allocation for ALL limited hunt codes
   (up from 80/20-or-35% in places). NR hunter counts drop in NR-heavy limited units.

Adjustment: multiplier on predicted hunters + policy_note on each prediction record.
"""
import json
import sqlite3

DB = '/opt/data/.scratch/huntdata/hunt.db'
PRED = '/opt/data/huntmap-repo/web/data/predictions.json'
RES = '/opt/data/huntmap-repo/web/data/residency.json'

GUNNISON = {'54', '55', '551'}
# units west of I-25 boundary — approximated by the CPW brochure archery-affected list;
# conservatively treat ALL units with meaningful archery share as affected EXCEPT
# eastern plains units (the 3 OTC archery NR codes left: 59, 133, 87)
NR_OTC_ARCHERY_EXEMPT = {'59', '133', '87'}


def main():
    pred = json.load(open(PRED))
    res = json.load(open(RES))
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    # archery share per unit where resolvable: codes with 'A' suffix in harvest_2025
    arch_share = {}
    for r in con.execute("SELECT unit, SUM(hunters) h FROM harvest_2025 WHERE code LIKE '%A' GROUP BY unit"):
        arch_share[str(r['unit'])] = r['h']
    tot_h = {}
    for r in con.execute("SELECT unit, SUM(hunters) h FROM harvest_2025 WHERE unit != 0 GROUP BY unit"):
        tot_h[str(r['unit'])] = r['h']

    changed = 0
    for u, d in pred.items():
        notes = []
        f_hunter = d['pred_2027']['hunters']
        # 1. Gunnison limited conversion: ~10% fewer hunters in those units from 2026
        if u in GUNNISON:
            notes.append('Gunnison Basin OTC->limited 2026 (tag supply -10%)')
            f_hunter = round(f_hunter * 0.90)
        # 2. NR archery draw-only: reduce hunter trend in archery-heavy units
        ash = (arch_share.get(u, 0) / tot_h[u]) if tot_h.get(u) else 0
        if ash > 0.15 and u not in NR_OTC_ARCHERY_EXEMPT:
            notes.append(f'NR archery now draw-only (archery share {ash:.0%})')
            f_hunter = round(f_hunter * 0.95)
        # 3. 2028 uniform 75/25: NR-share-heavy limited units lose more hunters
        rinfo = res.get(u)
        if rinfo and rinfo.get('nr_share_pct') and rinfo['nr_share_pct'] > 30 and (rinfo.get('limited_quota') or 0) > 200:
            notes.append(f"2028 75/25 R/NR cap (unit NR share {rinfo['nr_share_pct']}%)")
            f_hunter = round(f_hunter * 0.95)
        if notes:
            d['pred_2027']['hunters'] = f_hunter
            # recompute success for the adjusted hunter count, keeping harvest path
            tot_pred = d['pred_2027']['hunters']
            harvest_est = round(d['pred_2027']['success'] / 100 * max(1, (d['est_2026']['hunters'] + d['last']['hunters']) / 2))
        # always write policy notes list (can be empty)
        d['policy_notes'] = notes
        if notes:
            changed += 1
    json.dump(pred, open(PRED, 'w'), indent=1)
    print(f"policy adjustments applied to {changed} units")


if __name__ == '__main__':
    main()