#!/usr/bin/env python3
"""Parse the CPW post-draw recap PDF into per-hunt-code, per-point-level draw odds.

Each page of the recap documents one hunt code:

    # Drawn Hunt Code List
    10 EE003O1M A                     <- quota, code
    Total Quota Amount 10
    Drawn Out At 1 Pref Points ...    <- cutoff level per residency column
    Pre-Draw Applicants               <- applicants by preference points
      5 - 1 - - - -                   level, Res, NonRes, YthRes, YthNonRes, LPPunres, LPPres
      ...
      Total Choice 1 15 7 4 0 0 0
    Post-Draw Successful              <- successful applicants, same shape
      ...
    Post-Draw
    Successful # Drawn Balance Res NonRes ...

Applicants and successes at the same point level give an exact P(draw | points);
nothing needs to be modelled.

Usage:  python3 parse_draw_recap.py <pdf> <out.db> [out.json]
"""
import json
import re
import sqlite3
import sys

import pypdf

CODE_RE = re.compile(r'^(\d{1,5})\s+([A-Z]{2}\d{3}[A-Z]\d[A-Z])\s*([A-Z]?)$')
ROW_RE = re.compile(r'^(\d{1,2})\s+((?:-|\d+)(?:\s+(?:-|\d+)){5})$')
TOTAL_RE = re.compile(r'^Total Choice 1\s+((?:-|\d+)(?:\s+(?:-|\d+)){5})$')
CUTOFF_RE = re.compile(r'^Drawn Out At (.+)$')
CODE_ONLY_RE = re.compile(r'^([A-Z]{2}\d{3}[A-Z]\d[A-Z])\s*$')


def split_cols(s):
    out = []
    for tok in s.split():
        out.append(None if tok == '-' else int(tok))
    return out


def parse_block(lines, start):
    """Parse the 6 preference-point rows that follow a table header."""
    levels = {}
    for ln in lines[start:start + 14]:
        m = ROW_RE.match(ln)
        if not m:
            if levels:
                break
            continue
        levels[int(m.group(1))] = split_cols(m.group(2))
    return levels


def find(lines, needle, after=0):
    for i in range(after, len(lines)):
        if needle in lines[i]:
            return i
    return -1


def parse_page(text):
    lines = [l.strip() for l in text.split('\n')]
    code = quota = None
    for i, ln in enumerate(lines[:14]):
        m = CODE_RE.match(ln)
        if m:
            quota, code = int(m.group(1)), m.group(2)
            break
    if not code:
        # some pages put the code alone on a line after the quota block
        for ln in lines[:20]:
            m = CODE_ONLY_RE.match(ln)
            if m:
                code = m.group(1)
                break
    if not code:
        return None

    cutoff = None
    for ln in lines:
        m = CUTOFF_RE.match(ln)
        if m:
            cutoff = m.group(1)
            break

    pre_i = find(lines, 'Pre-Draw Applicants')
    post_i = find(lines, 'Post-Draw Successful', pre_i + 1 if pre_i >= 0 else 0)
    pre = parse_block(lines, pre_i + 5) if pre_i >= 0 else {}
    post = parse_block(lines, post_i + 5) if post_i >= 0 else {}

    if not pre:
        return None

    levels = {}
    for lvl in sorted(set(pre) | set(post)):
        a = pre.get(lvl) or [None] * 6
        s = post.get(lvl) or [None] * 6
        levels[lvl] = {
            'res_app': a[0], 'res_drawn': s[0],
            'nr_app': a[1], 'nr_drawn': s[1],
            'y_res_app': a[2], 'y_res_drawn': s[2],
            'y_nr_app': a[3], 'y_nr_drawn': s[3],
        }
    return {'code': code, 'quota': quota, 'cutoff': cutoff, 'levels': levels}


def main():
    pdf, db_path = sys.argv[1], sys.argv[2]
    json_path = sys.argv[3] if len(sys.argv) > 3 else None
    reader = pypdf.PdfReader(pdf)
    n = len(reader.pages)
    print(f'pages: {n}', flush=True)

    con = sqlite3.connect(db_path)
    con.execute('drop table if exists draw_odds')
    con.execute('''create table draw_odds (
        year integer, code text, unit integer, sex text, season integer, weapon text,
        quota integer, cutoff text, level integer,
        res_app integer, res_drawn integer, nr_app integer, nr_drawn integer,
        y_res_app integer, y_res_drawn integer, y_nr_app integer, y_nr_drawn integer,
        primary key (year, code, level))''')

    sex_map = {'M': 'bull', 'F': 'cow', 'E': 'either'}
    weap_map = {'A': 'archery', 'M': 'muzzleloader', 'R': 'rifle'}
    code_pat = re.compile(r'^E([MEF])(\d{3})([A-Z])(\d)([A-Z])$')

    export = {}
    ok = skipped = 0
    for i in range(n):
        try:
            text = reader.pages[i].extract_text() or ''
        except Exception:
            continue
        p = parse_page(text)
        if not p:
            skipped += 1
            continue
        m = code_pat.match(p['code'])
        unit = int(m.group(2)) if m else None
        sex = sex_map.get(m.group(1)) if m else None
        season = int(m.group(4)) if m else None
        weapon = weap_map.get(m.group(5)) if m else None
        rows = []
        for lvl, d in sorted(p['levels'].items()):
            con.execute('insert or replace into draw_odds values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (2025, p['code'], unit, sex, season, weapon, p['quota'], p['cutoff'], lvl,
                         d['res_app'], d['res_drawn'], d['nr_app'], d['nr_drawn'],
                         d['y_res_app'], d['y_res_drawn'], d['y_nr_app'], d['y_nr_drawn']))
            rows.append([lvl, d['res_app'], d['res_drawn'], d['nr_app'], d['nr_drawn']])
        export[p['code']] = {
            'unit': unit, 'sex': sex, 'season': season, 'weapon': weapon,
            'quota': p['quota'], 'cutoff': p['cutoff'],
            # [level, res applicants, res drawn, nonres applicants, nonres drawn]
            'rows': rows,
        }
        ok += 1
        if ok % 50 == 0:
            con.commit()
            print(f'  {i+1}/{n} pages, {ok} codes', flush=True)

    con.commit()
    print(f'parsed codes: {ok}, skipped pages: {skipped}', flush=True)
    print('db rows:', con.execute('select count(*) from draw_odds').fetchone()[0], flush=True)
    if json_path:
        with open(json_path, 'w') as f:
            json.dump(export, f, separators=(',', ':'))
        print('json:', json_path, len(export), 'codes', flush=True)


if __name__ == '__main__':
    main()
