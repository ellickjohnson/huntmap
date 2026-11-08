#!/usr/bin/env python3
"""Build the decision table: every hunt code with draw odds, success rate and a score.

Joins three sources on the hunt code:
  draw_odds.json    per-code, per-preference-level applicants and successful draws
  harvest_2025      per-code hunters and harvest (same code granularity)
  harvest_years_v2  per-unit multi-year success, used both as the shrink prior
                    and for the trend arrow
  gmus              public land percentage (access)

Success per code is one year of data, so it is shrunk toward the unit's multi-year
rate: (harvest + k * prior) / (hunters + k). A code with 4 hunters and 2 kills
must not outrank a code with 300 hunters and 60 kills.

Output: web/data/plan.json
"""
import json
import math
import os
import re
import sqlite3

K_SHRINK = 40.0          # pseudo-hunters pulling thin samples toward the unit rate

# 6th character of a CPW hunt code is the license class:
#   O = limited draw (preference points)   P = private land only
#   L = landowner preference (LPP)         V = over-the-counter (leftover/OTC)
#   E = premium either-sex                 W = winter/damage  S,K = special
# PLO tags draw by CHOICE not points and carry much higher success because the
# hunter is on private ground — ranking them against public-land tags is
# misleading, so they are flagged and hidden by default in the UI.
LICENSE_CLASS = {
    'O': ('limited', 'Preference-point draw'),
    'P': ('plo', 'Private land only'),
    'L': ('lpp', 'Landowner preference'),
    'V': ('otc', 'Over the counter'),
    'E': ('premium', 'Premium either-sex'),
    'W': ('winter', 'Winter / damage'),
    'S': ('special', 'Special'),
    'K': ('special', 'Special'),
}
OUT = 'web/data/plan.json'
HUNTDB = '/opt/data/.scratch/huntdata/hunt.db'


CUT_RE = re.compile(r'(\d+)\s*Pref\s*Points|(No\s*Apps)|(Leftover)|(Choice\s*\d+)', re.I)


def parse_cutoff(s):
    """Cutoff text -> [res, nonres, youth_res, youth_nr, lpp_u, lpp_r] levels.

    'Choice N' / 'Leftover' / 'No Apps' all mean no preference points were
    needed, so they collapse to level 0."""
    if not s:
        return [None] * 6
    vals = []
    for m in CUT_RE.finditer(s):
        if m.group(1):
            vals.append(int(m.group(1)))
        else:
            vals.append(0)
    while len(vals) < 6:
        vals.append(None)
    return vals[:6]


def wilson(p, n, z=1.0):
    """Lower confidence bound — ranks a lucky small sample below a solid big one."""
    if not n:
        return 0.0
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / den)


def main():
    odds = json.load(open('web/data/draw_odds.json'))
    con = sqlite3.connect(HUNTDB)
    con.row_factory = sqlite3.Row

    # per-code 2025 actuals
    h2025 = {r['code']: (r['hunters'] or 0, r['total_harvest'] or 0)
             for r in con.execute('select code, hunters, total_harvest from harvest_2025')}

    # per-unit multi-year prior: hunters-weighted mean success over 2022-2025
    unit_succ = {}
    for r in con.execute('''select unit, sum(hunters) h, sum(total_harvest) t
                            from harvest_years_v2 where year >= 2022 and hunters > 0
                            group by unit'''):
        if r['h'] and r['h'] > 0:
            unit_succ[r['unit']] = r['t'] / r['h']
    statewide = sum(t for _, t in h2025.values()) / max(1, sum(h for h, _ in h2025.values()))

    # trend per unit (per-hunter rate, hunters-weighted least squares)
    trend = {}
    rows = list(con.execute('''select unit, year, hunters, total_harvest from harvest_years_v2
                               where hunters > 20 order by unit, year'''))
    by_u = {}
    for r in rows:
        by_u.setdefault(r['unit'], []).append((r['year'], r['hunters'], r['total_harvest']))
    for u, pts in by_u.items():
        if len(pts) < 4:
            continue
        xs = [p[0] for p in pts]
        ys = [p[2] / p[1] for p in pts]
        w = [p[1] for p in pts]
        sw = sum(w)
        mx = sum(wi * x for wi, x in zip(w, xs)) / sw
        my = sum(wi * y for wi, y in zip(w, ys)) / sw
        num = sum(wi * (x - mx) * (y - my) for wi, x, y in zip(w, xs, ys))
        den = sum(wi * (x - mx) ** 2 for wi, x in zip(w, xs))
        if den:
            trend[u] = num / den          # percentage-points of success per year

    # access
    pub = {r['gmuid']: (r['public_pct'] or 0) for r in con.execute('select gmuid, public_pct from gmus')}

    out = []
    for code, d in odds.items():
        unit = d['unit']
        if not unit:
            continue
        hunters, harvest = h2025.get(code, (0, 0))
        prior = unit_succ.get(unit, statewide)
        succ = (harvest + K_SHRINK * prior) / (hunters + K_SHRINK)
        # Confidence bound on the SHRUNK estimate with pseudo-count sample size —
        # taking the bound of the raw rate instead can exceed the point estimate
        # (raw 26/44 = .59 vs shrunk .40), which silently inflated the ranking.
        succ_lb = wilson(succ, hunters + K_SHRINK)

        # per-level observed ratio, used only AT the cutoff level
        res = {}
        nr = {}
        for lvl, ra, rd, na, nd in d['rows']:
            if ra:
                res[lvl] = (rd or 0) / ra
            if na:
                nr[lvl] = (nd or 0) / na

        cut = parse_cutoff(d.get('cutoff'))
        cut_res, cut_nr = cut[0], cut[1]

        def odds_curve(cut_level, ratios):
            """Preference draw: above the cutoff you are guaranteed a tag, at the
            cutoff you take that level's ratio, below it you are out. Reading the
            ratio at 'my level' alone is wrong — a level with no applicants
            recorded scores 0 and makes an easy tag look impossible."""
            curve = []
            for p in range(7):
                if cut_level is None:
                    curve.append(round(ratios.get(p, 0.0), 3))
                elif p > cut_level:
                    curve.append(1.0)
                elif p == cut_level:
                    r = ratios.get(p)
                    curve.append(round(1.0 if r is None else r, 3))
                else:
                    curve.append(0.0)
            return curve

        odds_res = odds_curve(cut_res, res)
        odds_nr = odds_curve(cut_nr, nr)

        def need(curve, threshold=0.5, cap=12):
            for p, v in enumerate(curve):
                if v >= threshold:
                    return p
            return cap

        need_res = need(odds_res)
        need_nr = need(odds_nr)
        cls, cls_label = LICENSE_CLASS.get(code[5], ('other', 'Other'))
        otc = cls == 'otc' or hunters > 1.5 * max(1, d['quota'] or 1)
        out.append({
            'code': code, 'unit': unit, 'sex': d['sex'], 'season': d['season'],
            'cls': cls, 'cls_label': cls_label, 'otc': otc,
            'weapon': d['weapon'], 'quota': d['quota'],
            'hunters': hunters, 'harvest': harvest,
            'success': round(succ, 4), 'success_lb': round(succ_lb, 4),
            'trend_pp': round(trend.get(unit, 0.0), 3),
            'public_pct': pub.get(unit, 0),
            'need_res': need_res, 'need_nr': need_nr,
            # odds at 0..6 points, residents and non-residents
            'odds_res': odds_res,
            'odds_nr': odds_nr,
            'cut_res': cut_res, 'cut_nr': cut_nr,
            'cutoff': d['cutoff'],
        })

    out.sort(key=lambda r: -r['success'])
    meta = {'generated_from': 'drawrecap2025.pdf + harvest_2025 + harvest_years_v2',
            'codes': len(out), 'statewide_success': round(statewide, 4), 'k_shrink': K_SHRINK}
    with open(OUT, 'w') as f:
        json.dump({'meta': meta, 'codes': out}, f, separators=(',', ':'))
    print(f'codes: {len(out)}  statewide {statewide:.3f}  -> {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)')

    # a few sanity lines
    top = [r for r in out if r['weapon'] == 'rifle' and r['sex'] == 'bull' and not r['otc']][:6]
    print('\ntop PUBLIC bull rifle codes by success:')
    for r in top:
        print(f"  {r['code']} [{r['cls']}] u{r['unit']:>3} s{r['season']} q={r['quota']:<4} "
              f"succ={r['success']*100:4.1f}%  need(res)={r['need_res']}pt  odds@0={r['odds_res'][0]*100:3.0f}%")
    plo = [r for r in out if r['cls'] == 'plo']
    print(f"\nflagged: {len(plo)} private-land-only codes, "
          f"{sum(1 for r in out if r['otc'])} over-the-counter codes")


if __name__ == '__main__':
    main()
