"""Tests for GET /api/weather — server-side Open-Meteo proxy (build item #1).

Contract: docs/specs/01-weather-wind.md @ 96814c0 (incl. erratum: wind_speed_10m +
wind_speed_unit=mph; pressure_msl readout; 10-min cache; trimmed response shape).

Harness: real Handler in a thread on 127.0.0.1:random, temp SQLite DBs, and a
local stub HTTP server standing in for Open-Meteo (injected via
HUNTMAP_OPEN_METEO_URL so prod default stays api.open-meteo.com).
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer, HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen

REPO = '/opt/data/.scratch/huntmap'
sys.path.insert(0, os.path.join(REPO, 'api'))

TMP = tempfile.mkdtemp(prefix='weather_test_')
os.environ['HUNTMAP_DB'] = os.path.join(TMP, 'hunt.db')
os.environ['HUNTMAP_AUTHDB'] = os.path.join(TMP, 'auth.db')
os.environ['HUNTMAP_WEATHER_TIMEOUT'] = '3'

import server as srv  # noqa: E402  (env first)


# ---- stub Open-Meteo (speaks the spec's upstream request; returns imperial units) ----
STUB_STATE = {'last_query': None, 'mode': 'ok', 'hits': 0, 'pressure_slope': 0.2}


def _canned():
    """Full single-day canned upstream response in imperial units (spec's unit params)."""
    slope = STUB_STATE['pressure_slope']
    n = 24
    base = 1015.0
    pressures = [round(base + slope * (i - 12), 2) for i in range(n)]  # slope > 0 -> rising
    return {
        'latitude': 38.925, 'longitude': -107.125,
        'timezone': 'America/Denver', 'timezone_abbreviation': 'MDT', 'utc_offset_seconds': -21600,
        'current': {'time': '2026-10-28T12:00', 'temperature_2m': 52, 'apparent_temperature': 47,
                    'precipitation': 0.0, 'weather_code': 3, 'wind_speed_10m': 8,
                    'wind_direction_10m': 225, 'wind_gusts_10m': 16, 'pressure_msl': pressures[12]},
        'hourly': {
            'time': [f'2026-10-28T{h:02d}:00' for h in range(n)],
            'temperature_2m': [50 + (h % 5) for h in range(n)],
            'precipitation_probability': [10 * (h % 4) for h in range(n)],
            'weather_code': [3] * n,
            'wind_speed_10m': [8 + h * 0.1 for h in range(n)],
            'wind_direction_10m': [225 + h for h in range(n)],
            'wind_gusts_10m': [16 + h * 0.2 for h in range(n)],
            'pressure_msl': pressures,
        },
        'daily': {'time': [f'2026-10-{d}' for d in range(28, 31)] + [f'2026-11-{d:02d}' for d in range(1, 6)],
                  'sunrise': [f'2026-10-{d}T07:31' for d in range(28, 31)] + [f'2026-11-{d:02d}T07:32' for d in range(1, 6)],
                  'sunset': [f'2026-10-{d}T18:12' for d in range(28, 31)] + [f'2026-11-{d:02d}T18:11' for d in range(1, 6)]},
    }


class StubOpenMeteo(BaseHTTPRequestHandler):
    def do_GET(self):
        STUB_STATE['hits'] += 1
        STUB_STATE['last_query'] = self.path
        mode = STUB_STATE['mode']
        if mode == 'ok':
            body = json.dumps(_canned()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
        elif mode == 'upstream_bad_request':
            body = json.dumps({'error': True, 'reason': 'Latitude out of range'}).encode()
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
        elif mode == 'non_json':
            body = b'<html>gateway error</html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
        elif mode == 'hang':
            body = b'{}'
            import time as _t
            _t.sleep(5)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
        else:
            body = b'{}'
            self.send_response(500)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass  # client (HuntMap proxy) already timed out — fine

    def log_message(self, fmt, *args):
        pass


def boot_stub():
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), StubOpenMeteo)
    port = httpd.server_address[1]
    os.environ['HUNTMAP_OPEN_METEO_URL'] = f'http://127.0.0.1:{port}/forecast'
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


# ---- boot the real HuntMap handler -------------------------------------------
def boot_huntmap():
    srv.init_authdb()
    import sqlite3
    con = sqlite3.connect(os.environ['HUNTMAP_AUTHDB'])
    con.execute("INSERT INTO users (email,name,password,role,verified,created_at) VALUES (?,?,?,?,1,?)",
                ('hunter@test.local', 'Test Hunter', srv.hash_pw('pw-hunter-123'), 'user', 0))
    uid = con.execute("SELECT id FROM users WHERE email='hunter@test.local'").fetchone()[0]
    con.commit()
    con.close()
    sid = srv.make_session(uid)

    httpd = HTTPServer(('127.0.0.1', 0), srv.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port, sid


def get(path, sid=None):
    req = Request(f'http://127.0.0.1:{_ctx["port"]}{path}')
    if sid:
        req.add_header('Cookie', f'huntmap_session={sid}')
    try:
        resp = urlopen(req, timeout=10)
        with resp:
            return resp.status, json.loads(resp.read().decode())
    except Exception as e:
        from urllib.error import HTTPError
        if isinstance(e, HTTPError):
            with e:
                raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw
        raise


_ctx = {}


class WeatherAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _ctx['stub'] = boot_stub()
        _ctx['httpd'], _ctx['port'], _ctx['sid'] = boot_huntmap()

    @classmethod
    def tearDownClass(cls):
        _ctx['httpd'].shutdown()
        _ctx['stub'].shutdown()

    def setUp(self):
        srv.weather_cache_clear()
        STUB_STATE['mode'] = 'ok'
        STUB_STATE['pressure_slope'] = 0.2
        STUB_STATE['hits'] = 0

    def test_signed_in_proxy_matches_spec_shape_and_request(self):
        status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status, 200, data)
        # exact response shape per spec (trimmed; do not proxy the raw blob)
        self.assertEqual(sorted(data.keys()), ['current', 'daily', 'hourly', 'tz'])
        self.assertEqual(data['tz'], 'America/Denver')
        cur = data['current']
        self.assertEqual(sorted(cur.keys()), ['code', 'feels_f', 'gust_mph', 'precip', 'pressure_inhg',
                                              'pressure_trend', 'temp_f', 'wind_dir_deg', 'wind_dir_txt', 'wind_mph'])
        self.assertEqual(cur['temp_f'], 52)
        self.assertEqual(cur['wind_mph'], 8)
        self.assertEqual(cur['wind_dir_txt'], 'SW')      # 225° -> 16-point compass, server-side
        self.assertEqual(cur['wind_dir_deg'], 225)
        self.assertAlmostEqual(cur['pressure_inhg'], 29.97, places=2)  # 1015.0 hPa × 0.02953
        self.assertEqual(cur['pressure_trend'], 'rising')  # slope +0.2 hPa/h around now
        # hourly: array of objects, from next hour, wind+temp+precip%+code, max 48
        self.assertIsInstance(data['hourly'], list)
        self.assertEqual(len(data['hourly']), 11)  # 24 canned rows, now = 12:00, start 13:00
        row = data['hourly'][0]
        self.assertEqual(sorted(row.keys()), ['code', 'gust_mph', 'precip_prob', 'temp_f',
                                              'ts', 'wind_dir_deg', 'wind_dir_txt', 'wind_mph'])
        self.assertEqual(row['ts'], '2026-10-28T13:00')
        self.assertEqual(row['wind_dir_txt'], 'WSW')   # 225°+13 = 238° -> grid index 11 = 247.5°
        # daily: 8 sunrise/sunset objects
        self.assertEqual(len(data['daily']), 8)
        self.assertEqual(sorted(data['daily'][0].keys()), ['sunrise_iso', 'sunset_iso'])
        self.assertEqual(data['daily'][0]['sunrise_iso'], '2026-10-28T07:31')
        # upstream saw the spec's exact unit params + field lists
        q = STUB_STATE['last_query']
        self.assertIn('forecast_days=8', q)
        self.assertIn('timezone=auto', q)
        self.assertIn('temperature_unit=fahrenheit', q)
        self.assertIn('wind_speed_unit=mph', q)
        self.assertIn('precipitation_unit=inch', q)
        self.assertIn('latitude=38.9', q)
        self.assertIn('longitude=-107.1', q)
        self.assertIn('hourly=temperature_2m%2Cprecipitation_probability%2Cweather_code%2C'
                      'wind_speed_10m%2Cwind_direction_10m%2Cwind_gusts_10m%2Cpressure_msl', q)
        self.assertIn('current=temperature_2m%2Capparent_temperature%2Cprecipitation%2Cweather_code%2C'
                      'wind_speed_10m%2Cwind_direction_10m%2Cwind_gusts_10m%2Cpressure_msl', q)
        self.assertIn('daily=sunrise%2Csunset', q)

    # ---- contract pins (route shipped in one slice; these pin each branch) ----

    def test_unauthenticated_request_is_401(self):
        # regression pin: the auth gate must fire BEFORE the route (spec: same gate as /api/markers)
        status, _ = get('/api/weather?lat=38.9&lon=-107.1')
        self.assertEqual(status, 401)
        self.assertEqual(STUB_STATE['hits'], 0)   # never reached upstream

    def test_bad_coords_are_rejected_server_side_without_hitting_upstream(self):
        for q in ('lat=95&lon=-107', 'lon=-107', 'lat=abc&lon=-107', 'lat=&lon=-107', ''):
            status, data = get('/api/weather?' + q, _ctx['sid'])
            self.assertEqual(status, 400, (q, data))
            self.assertIn('error', data)
        self.assertEqual(STUB_STATE['hits'], 0)   # never reached upstream

    def test_out_of_range_longitude_is_rejected(self):
        status, data = get('/api/weather?lat=38.9&lon=200', _ctx['sid'])
        self.assertEqual(status, 400)
        self.assertIn('error', data)

    def test_upstream_failures_map_to_502_upstream(self):
        # spec: upstream failure -> 502 {"error":"upstream"} (upstream 400, non-JSON, timeout)
        for mode in ('upstream_bad_request', 'non_json', 'hang'):
            with self.subTest(mode=mode):
                srv.weather_cache_clear()
                STUB_STATE['mode'] = mode
                status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
                self.assertEqual(status, 502, (mode, data))
                self.assertEqual(data.get('error'), 'upstream')
        STUB_STATE['mode'] = 'ok'

    def test_pressure_trends(self):
        for slope, expected in ((+0.2, 'rising'), (-0.2, 'falling'), (0.0, 'steady')):
            with self.subTest(slope=slope):
                srv.weather_cache_clear()
                STUB_STATE['pressure_slope'] = slope
                status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
                self.assertEqual(status, 200)
                self.assertEqual(data['current']['pressure_trend'], expected)

    def test_cache_hit_within_ttl_avoids_upstream(self):
        # acceptance #4: repeated opens within 10 min hit the in-memory cache
        status1, data1 = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status1, 200)
        hits_after_first = STUB_STATE['hits']
        status2, data2 = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status2, 200)
        self.assertEqual(data2, data1)
        self.assertEqual(STUB_STATE['hits'], hits_after_first)  # second call did NOT hit upstream

    def test_cache_key_rounds_to_the_grid(self):
        # different coords within the same 0.01° cell -> one upstream hit
        status1, _ = get('/api/weather?lat=38.9032&lon=-107.1049', _ctx['sid'])
        status2, _ = get('/api/weather?lat=38.9000&lon=-107.1000', _ctx['sid'])
        self.assertEqual((status1, status2), (200, 200))
        self.assertEqual(STUB_STATE['hits'], 1)