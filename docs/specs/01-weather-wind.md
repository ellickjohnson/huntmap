# Spec 01 — Weather + hourly wind panel (onX parity item #1)

Goal: clicking a marker popup shows a weather/wind section for that exact spot, matching
onX's point-forecast concept (current + hourly wind + sunrise/sunset + pressure trend).

## Backend — `api/server.py` (stdlib only, no new deps)

New route: `GET /api/weather?lat=&lon=`

- Auth: same session gate as `/api/markers` (401 when signed out).
- Upstream: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..`
  with params: `current=temperature_2m,apparent_temperature,precipitation,weather_code,
  wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl`
  `hourly=temperature_2m,precipitation_probability,weather_code,wind_speed_10m,
  wind_direction_10m,wind_gusts_10m,pressure_msl` `daily=sunrise,sunset`
  `temperature_unit=fahrenheit`
  `wind_speed_unit=mph` `precipitation_unit=inch` `forecast_days=8` `timezone=auto`.
  (Erratum, 2026-10-28: original string used `wind_speed_10m_ms` together with
  `wind_speed_unit=mph`; `_ms` is a self-contained m/s variant and the combination 400s
  upstream — reproduced by app-bot; wind_speed_10m + unit param -> 200, units report
  mp/h. Hermes_One approved the fold-in without an independent re-run.)
- Wind direction conversion: degrees -> 16-point compass (N, NNE, NE, ...).
- Pressure = mean sea level (`pressure_msl`), shown in inHg (hPa × 0.02953). Use MSL, not
  surface: surface pressure at Colorado elevations reads ~21-23 inHg, accurate but alien;
  MSL lands in the familiar ~29-30 inHg band hunters know, and the rising/falling/steady
  trend is identical either way. Trend: last 6h of hourly `pressure_msl`,
  trend = sign of (now+3h mean − now−3h mean) -> "rising" / "falling" / "steady".
- Cache: in-memory dict keyed by rounded lat/lon (0.01°), TTL 10 min, max 200 entries.
  Stdlib `urllib.request` with `timeout=10`; upstream failure -> 502 `{"error":"upstream"}`.
- Response shape (trim to what the UI needs; do not proxy the raw blob):
  `{ current: {temp_f, feels_f, precip, code, wind_mph, wind_dir_txt, wind_dir_deg,
     gust_mph, pressure_inhg, pressure_trend}, hourly: [{ts, temp_f, precip_prob,
     code, wind_mph, wind_dir_txt, wind_dir_deg, gust_mph}...48],
    daily: [{sunrise_iso, sunset_iso}...8], tz: <string> }`
- Pressure readout must show MSL-corrected inHg (~29-30), not absolute surface hPa.

## Frontend — `web/index.html`

Both marker-popup builders (`markers-dots` click at ~line 1774 and `gotoMarker` at ~1822)
add a weather section:

- Section renders async: placeholder row "wind & weather ⋯" -> fill on
  `/api/weather` response; cache per popup open.
- Collapsed by default: one summary row
  `🌡 52°F · 💨 12mph WNW · ⬇︎ pressure · 🌅 6:42a / 🌇 6:10p`.
- "Expand" -> hourly table (24 rows from next hour): day/hour, temp, precip%, wind
  arrow (SVG rotated `wind_dir_deg` — direction wind COMES FROM, arrow points down-wind),
  speed, gust.
- Style: match existing popup styling vars (`var(--panel2)`, `var(--line)`, 11-12px).
- No wind-direction "favorable" coloring yet — that is item #6 (needs marker
  `optimal_dir` field). Keep this spec lean.

## Acceptance (verified by Hermes_One)

1. Signed-out: `GET /api/weather` -> 401. Signed-in: 200 with `current`, 48-hourly,
   8 daily sunrise/sunset entries.
2. Marker popup shows summary row, expand shows wind table with rotated arrows.
3. No API keys, no external JS libs added; only `api.open-meteo.com` called server-side.
4. Repeated opens within 10 min hit the cache (server log / response timing shows it).
5. GHA build green; app-bot: digest bump + live verify.

## Out of scope (later items)
Wind calendar on list, optimal-wind directions, multi-point comparison (#6).