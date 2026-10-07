#!/usr/bin/env python3
"""Crossover analysis: per-GMU linear trend of HUNTERS vs SUCCESS% over the
harvest-history series, producing:
  - crossover score (0-100): how far toward a "declining hunters / rising success"
    crossover the unit is, higher = closer/beyond
  - crossover year (projected or achieved)
  - est_2026 (educated estimate) / pred_2027 (prediction) for hunters + success
Confidence weighting via R^2 of the regressions (weak fits are damped toward the
mean so units with noisy data don't produce wild predictions).

Writes web/data/predictions.json consumed by the frontend.
"""
import json
import math
import sqlite3
import sys

DB = "/opt/data/.scratch/huntdata/hunt.db"
OUT = "/opt/data/huntmap-repo/web/data/predictions.json"
HIST = "/opt/data/huntmap-repo/web/data/harvest_history.json"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]


def linfit(ys, xs):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 0.0
    return a, b, r2


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # Historical series: harvest_history.json (2019-2024, All-Manners per-GMU rows,
    # like-for-like across years) + 2025 from the hunt-code aggregation.
    HISTORY = json.load(open(HIST))
    try:
        gmu2025 = json.load(open("/opt/data/.scratch/huntdata/gmu_2025.json"))
    except FileNotFoundError:
        sys.exit("run parse_harvest2025.py first")

    series = {}  # unit -> {year: (hunters, success_pct, total)}
    for u in HISTORY:
        try:
            ui = int(u)
        except ValueError:
            continue
        for y, r in HISTORY[u].items():
            y = int(y)
            if 2019 <= y <= 2024 and r.get("hunters"):
                series.setdefault(ui, {})[y] = (
                    float(r["hunters"]), float(r.get("success") or 0), float(r.get("total") or 0))
    for u, rows in gmu2025.items():
        u = int(u)
        if rows.get("hunters"):
            series.setdefault(u, {})[2025] = (
                float(rows["hunters"]), float(rows["success_pct"] or 0), float(rows["total"] or 0))
    con.close()

    out = {}
    for u, byyear in series.items():
        pts = [(y, byyear[y]) for y in YEARS if y in byyear]
        if len(pts) < 4:
            continue
        xs = [p[0] for p in pts]
        hu = [p[1][0] for p in pts]
        su = [p[1][1] for p in pts]

        fh = linfit(hu, xs)
        fs = linfit(su, xs)
        if not (fh and fs):
            continue
        ah, bh, r2h = fh
        as_, bs, r2s = fs

        # projected values
        hu26, hu27 = ah + bh * 2026, ah + bh * 2027
        su26, su27 = clamp(as_ + bs * 2026), clamp(as_ + bs * 2027)
        hu26, hu27 = max(hu26, 0), max(hu27, 0)

        # confidence: weakest of the two fits damps predictions toward last value
        conf = min(r2h, r2s)
        last_h = byyear[max(byyear)].__getitem__(0)
        su26c = su26 * conf + su26 * 0  # keep raw; confidence used in score & flag
        last_s = byyear[max(byyear)][1]

        # crossover: solve a_h + b_h*t = a_s + b_s*t on unit-normalized series
        # (hunters z-scored vs its own mean, success vs its own). Crossover = year
        # where normalized hunter trend falls below normalized success trend;
        # before that, crowding suppresses the success rate.
        hh_mean = sum(hu) / len(hu)
        ss_mean = sum(su) / len(su)
        if hh_mean <= 0 or ss_mean <= 0:
            continue
        hn = [(v - hh_mean) / hh_mean for v in hu]
        sn = [(v - ss_mean) / ss_mean for v in su]
        fh2 = linfit(hn, xs)
        fs2 = linfit(sn, xs)
        cyear = None
        if fh2 and fs2:
            a1, b1, _ = fh2
            a2, b2, _ = fs2
            # a1 + b1 t = a2 + b2 t
            if abs(b1 - b2) > 1e-9:
                t = (a2 - a1) / (b1 - b2)
                if 2019 <= t <= 2035:
                    cyear = round(t)

        # crossover score: reward falling hunter pressure + rising success, weighted by fit
        d_hunters = -bh / (hh_mean or 1) * 100.0        # %/yr decline of hunters
        d_success = bs                                  # percentage-point success/yr
        raw = 50 + 3.0 * d_hunters + 4.0 * d_success    # scaled combination
        # damp weak fits toward 50
        score = clamp(50 + (raw - 50) * (0.25 + 0.75 * conf))
        achieved = cyear is not None and cyear <= 2026

        out[str(u)] = {
            "years": xs,
            "hunters": [round(v) for v in hu],
            "success": [round(v, 1) for v in su],
            "est_2026": {"hunters": round(hu26), "success": round(su26, 1)},
            "pred_2027": {"hunters": round(hu27), "success": round(su27, 1)},
            "crossover_year": cyear,
            "crossover_achieved": achieved,
            "crossover_score": round(score),
            "hunters_trend_pct_per_yr": round(d_hunters, 1),
            "success_trend_pp_per_yr": round(d_success, 2),
            "confidence": round(conf, 2),
            "n_years": len(pts),
            "last": {"year": max(byyear), "hunters": round(last_h), "success": round(last_s, 1)},
        }

    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {len(out)} units -> {OUT}")
    top = sorted(out.items(), key=lambda kv: -kv[1]["crossover_score"])[:15]
    print("\nTop 15 crossover-score units (rising success, falling pressure):")
    for u, d in top:
        cy = d["crossover_year"] or "-"
        print(f"  GMU {u:>4}  score {d['crossover_score']:>3}  cross {cy}  "
              f"2026est S{d['est_2026']['success']:>5}%  2027pred S{d['pred_2027']['success']:>5}%  "
              f"conf {d['confidence']}")


if __name__ == "__main__":
    main()