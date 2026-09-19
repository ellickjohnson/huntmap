#!/usr/bin/env python3
"""HuntMap static+API server. Serves web/ and exposes /api/units.json from SQLite
for live data without rebuilding geojson. stdlib only."""
import json
import os
import sqlite3
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "db", "hunt.db")
WEB = os.path.join(ROOT, "web")
PORT = int(os.environ.get("HUNTMAP_PORT", "8086"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, fmt, *args):  # quiet
        pass

    def do_GET(self):
        if self.path.startswith("/api/units.json"):
            self.serve_units()
        else:
            super().do_GET()

    def serve_units(self):
        rows = []
        try:
            con = sqlite3.connect(DB)
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute(
                """SELECT g.gmuid, g.county, g.elk_dau, g.sq_miles, g.center_lat, g.center_lon,
                          g.public_pct, g.habitat_score, g.harvest_score,
                          h.total_harvest, h.hunters, h.success_pct, h.rec_days
                   FROM gmus g LEFT JOIN harvest h
                     ON h.unit = g.gmuid AND h.section LIKE '%All Manners% '
                   ORDER BY g.gmuid""")]
            con.close()
            payload = json.dumps(rows).encode()
        except Exception as e:
            payload = json.dumps({"error": str(e)}).encode()
        self.send_response(200 if rows else 500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    print(f"HuntMap serving {WEB} on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()