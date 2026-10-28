"""Tests for GET /api/weather — server-side Open-Meteo proxy (build item #1).

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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'api'))

TMP = tempfile.mkdtemp(prefix='weather_test_')
os.environ['HUNTMAP_DB'] = os.path.join(TMP, 'hunt.db')
os.environ['HUNTMAP_AUTHDB'] = os.path.join(TMP, 'auth.db')
os.environ['HUNTMAP_WEATHER_TIMEOUT'] = '3'

import server as srv  # noqa: E402  (env first)


# ---- stub Open-Meteo ---------------------------------------------------------
STUB_STATE = {'last_query': None, 'mode': 'ok'}


CANNED_FORECAST = {
    'latitude': 38.9, 'longitude': -107.125,
    'timezone': 'America/Denver', 'timezone_abbreviation': 'MDT', 'utc_offset_seconds': -21600,
    'current': {'time': '2026-10-28T12:00', 'temperature_2m': 4.0, 'apparent_temperature': 1.0,
                'weather_code': 3, 'wind_speed_10m': 12.5, 'wind_direction_10m': 225.0, 'wind_gusts_10m': 28.0},
    'hourly': {'time': ['2026-10-28T00:00', '2026-10-28T01:00'],
               'wind_speed_10m': [10.0, 11.0], 'wind_direction_10m': [210.0, 220.0],
               'wind_gusts_10m': [20.0, 22.0]},
    'daily': {'time': ['2026-10-28', '2026-10-29'], 'weather_code': [3, 61],
              'temperature_2m_max': [8.0, 6.0], 'temperature_2m_min': [-2.0, -1.0],
              'precipitation_sum': [0.0, 4.5],
              'sunrise': ['2026-10-28T07:31', '2026-10-29T07:32'],
              'sunset': ['2026-10-28T18:12', '2026-10-29T18:11']},
}


class StubOpenMeteo(BaseHTTPRequestHandler):
    def do_GET(self):
        STUB_STATE['last_query'] = self.path
        mode = STUB_STATE['mode']
        if mode == 'ok':
            body = json.dumps(CANNED_FORECAST).encode()
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
    from http.server import ThreadingHTTPServer
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

    def test_signed_in_weather_proxy_returns_trimmed_forecast(self):
        STUB_STATE['mode'] = 'ok'
        STUB_STATE['last_query'] = None
        status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status, 200, data)
        # shape: current + hourly (wind fields only) + daily with sun times
        self.assertIn('current', data)
        cur = data['current']
        for k in ('temperature_2m', 'apparent_temperature', 'weather_code',
                  'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m'):
            self.assertIn(k, cur)
        self.assertIn('hourly', data)
        self.assertEqual(sorted(data['hourly'].keys()),
                         ['time', 'wind_direction_10m', 'wind_gusts_10m', 'wind_speed_10m'])
        self.assertIn('daily', data)
        for k in ('weather_code', 'temperature_2m_max', 'temperature_2m_min',
                  'precipitation_sum', 'sunrise', 'sunset'):
            self.assertIn(k, data['daily'])
        # upstream saw an 8-day, tz-aware request for wind fields only
        q = STUB_STATE['last_query']
        self.assertIn('forecast_days=8', q)
        self.assertIn('timezone=auto', q)
        self.assertIn('hourly=wind_speed_10m%2Cwind_direction_10m%2Cwind_gusts_10m', q)
        self.assertIn('latitude=38.9', q)
        self.assertIn('longitude=-107.1', q)

    # ---- contract pins (route shipped in one slice; these pin each branch) ----

    def test_unauthenticated_request_is_401(self):
        # regression pin: the auth gate must fire BEFORE the route (spec: no new auth code)
        STUB_STATE['last_query'] = None
        status, _ = get('/api/weather?lat=38.9&lon=-107.1')
        self.assertEqual(status, 401)
        self.assertIsNone(STUB_STATE['last_query'])   # never reached upstream

    def test_bad_coords_are_rejected_server_side_without_hitting_upstream(self):
        STUB_STATE['last_query'] = None
        for q in ('lat=95&lon=-107', 'lon=-107', 'lat=abc&lon=-107', 'lat=&lon=-107', ''):
            status, data = get('/api/weather?' + q, _ctx['sid'])
            self.assertEqual(status, 400, (q, data))
            self.assertIn('error', data)
        self.assertIsNone(STUB_STATE['last_query'])   # never reached upstream

    def test_out_of_range_longitude_is_rejected(self):
        status, data = get('/api/weather?lat=38.9&lon=200', _ctx['sid'])
        self.assertEqual(status, 400)
        self.assertIn('error', data)

    def test_upstream_400_is_translated_to_502(self):
        STUB_STATE['mode'] = 'upstream_bad_request'
        status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status, 502)
        self.assertIn('error', data)
        self.assertIn('Latitude out of range', data['error'])

    def test_upstream_non_json_is_translated_to_502(self):
        STUB_STATE['mode'] = 'non_json'
        status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status, 502)
        self.assertIn('error', data)

    def test_upstream_timeout_is_translated_to_502(self):
        STUB_STATE['mode'] = 'hang'
        status, data = get('/api/weather?lat=38.9&lon=-107.1', _ctx['sid'])
        self.assertEqual(status, 502)
        self.assertIn('Weather service unavailable', data['error'])