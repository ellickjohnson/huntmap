#!/usr/bin/env python3
"""Aggregate 2025 draw recap per GMU -> residency split of LIMITED elk licenses.

Output: web/data/residency.json per unit:
  limited_quota, nr_quota_pct (observed from drawn), res_drawn, nr_drawn,
  draw_pressure (apps/quota), nr_share_pct
Also computes policy-impact adjustment factors for predictions.
"""
import pymupdf
import re
import json

per = json.load(open('/tmp/recap_parsed.json'))

units = {}
for code, v in per.items():
    u = v['unit']
    d = units.setdefault(u, dict(limited_quota=0, res_drawn=0, nr_drawn=0, codes=0,
                                 nr_caps=[], apps_ch1=0))
    d['limited_quota'] += v['total_quota']
    d['codes'] += 1
    dr = v.get('drawn_final') or []
    # cells: AdultRes, AdultNonRes, YouthRes, YouthNonRes, LPPunres, LPPrestr
    for idx, cell in enumerate(dr):
        m = re.match(r'(\d+) of (\d+)', cell)
        if not m:
            continue
        drawn, quota = int(m.group(1)), int(m.group(2))
        if idx in (0, 2):
            d['res_drawn'] += drawn
        elif idx in (1, 3):
            d['nr_drawn'] += drawn
    if v.get('nr_cap_pct'):
        d['nr_caps'].append(v['nr_cap_pct'])

out = {}
for u, d in sorted(units.items(), key=lambda kv: int(kv[0])):
    tot = d['res_drawn'] + d['nr_drawn']
    out[u] = {
        'limited_codes': d['codes'],
        'limited_quota': d['limited_quota'],
        'res_drawn': d['res_drawn'],
        'nr_drawn': d['nr_drawn'],
        'nr_share_pct': round(100 * d['nr_drawn'] / tot, 1) if tot else None,
        'nr_cap_typical': sorted(d['nr_caps'])[len(d['nr_caps'])//2] if d['nr_caps'] else None,
    }
res = sorted(out.items(), key=lambda kv: -(kv[1]['limited_quota'] or 0))[:10]
for u, v in res:
    print(f"GMU {u}: quota {v['limited_quota']:>5} | drawn R {v['res_drawn']:>5} vs NR {v['nr_drawn']:>5} | NR share {v['nr_share_pct']}%")
json.dump(out, open('/opt/data/huntmap-repo/web/data/residency.json', 'w'), indent=1)
print("wrote residency.json", len(out), "units")