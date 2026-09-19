"""HuntMap server: static + units API + full auth system.
Users: signup (email verify link w/ code), login, admin (user mgmt + SMTP settings).
Stdlib only."""
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from email.mime.text import MIMEText
from email.utils import formataddr
from http import cookies as http_cookies
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get('HUNTMAP_DB', os.path.join(ROOT, 'db', 'hunt.db'))
AUTHDB = os.environ.get('HUNTMAP_AUTHDB', os.path.join(ROOT, 'db', 'auth.db'))
WEB = os.path.join(ROOT, 'web')
PORT = int(os.environ.get('HUNTMAP_PORT', '8086'))
BASE_URL = os.environ.get('HUNTMAP_BASE_URL', 'https://huntmap.ellickjohnson.net')

# Session + token lifetimes (seconds)
SESSION_TTL = 14 * 86400
VERIFY_TTL = 24 * 3600
RESET_TTL = 3600

SALT_ROUNDS = 100_000


def hash_pw(pw: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), SALT_ROUNDS).hex()
    return f'{salt}${h}'


def check_pw(pw: str, stored: str) -> bool:
    try:
        salt, _ = stored.split('$', 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_pw(pw, salt), stored)


EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')


# ---------- auth DB ----------

def init_authdb():
    con = sqlite3.connect(AUTHDB)
    con.executescript('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        verified INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,          -- verify | reset
        expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        sid TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );''')
    # bootstrap admin from env
    admin_email = os.environ.get('HUNTMAP_ADMIN_EMAIL')
    admin_pw = os.environ.get('HUNTMAP_ADMIN_PASSWORD')
    if admin_email and admin_pw:
        have = con.execute('SELECT 1 FROM users WHERE email=?', (admin_email,)).fetchone()
        if not have:
            con.execute('INSERT INTO users (email,name,password,role,verified,created_at) VALUES (?,?,?,?,1,?)',
                        (admin_email, 'Admin', hash_pw(admin_pw), 'admin', int(time.time())))
    con.commit()
    con.close()


def get_setting(key, default=''):
    con = sqlite3.connect(AUTHDB)
    row = con.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    con.close()
    return row[0] if row else default


def set_setting(key, value):
    con = sqlite3.connect(AUTHDB)
    con.execute('INSERT INTO settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
    con.commit()
    con.close()


SMTP_FIELDS = ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'smtp_tls', 'from_address')


def smtp_config():
    cfg = {k: get_setting(k, '') for k in SMTP_FIELDS}
    if not cfg['smtp_host']:
        # fall back to env
        cfg.update({k: os.environ.get('HUNTMAP_' + k.upper(), '') for k in SMTP_FIELDS})
    return cfg


def send_mail(to, subject, html):
    cfg = smtp_config()
    if not cfg['smtp_host'] or not cfg['from_address']:
        raise RuntimeError('SMTP not configured - set it in admin settings')
    msg = MIMEText(html, 'html')
    msg['Subject'] = subject
    msg['From'] = formataddr(('HuntMap', cfg['from_address']))
    msg['To'] = to
    port = int(cfg['smtp_port'] or '587')
    tls = (cfg['smtp_tls'] or 'starttls').lower()
    if tls == 'ssl':
        s = smtplib.SMTP_SSL(cfg['smtp_host'], port, timeout=20)
    else:
        s = smtplib.SMTP(cfg['smtp_host'], port, timeout=20)
        s.ehlo()
        if tls == 'starttls':
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s.starttls(context=ctx)
            s.ehlo()
    if cfg['smtp_user']:
        s.login(cfg['smtp_user'], cfg['smtp_password'])
    s.sendmail(cfg['from_address'], [to], msg.as_string())
    s.quit()


def create_token(user_id, kind, ttl=VERIFY_TTL):
    tok = secrets.token_urlsafe(32)
    con = sqlite3.connect(AUTHDB)
    con.execute('INSERT INTO tokens (token,user_id,kind,expires_at) VALUES (?,?,?,?)',
                (hashlib.sha256(tok.encode()).hexdigest(), user_id, kind, int(time.time()) + ttl)) if False else con.execute(
        'INSERT INTO tokens (token,user_id,kind,expires_at) VALUES (?,?,?,?)',
        (hashlib.sha256(tok.encode()).hexdigest(), user_id, kind, int(time.time()) + ttl))
    con.commit()
    con.close()
    return tok


def consume_token(tok, kind):
    h = hashlib.sha256(tok.encode()).hexdigest()
    con = sqlite3.connect(AUTHDB)
    row = con.execute('SELECT user_id, expires_at FROM tokens WHERE token=? AND kind=?', (h, kind)).fetchone()
    if row and row[1] > time.time():
        con.execute('DELETE FROM tokens WHERE token=?', (h,))
        con.commit()
        con.close()
        return row[0]
    con.close()
    return None


def session_user(cookie_sid):
    if not cookie_sid:
        return None
    con = sqlite3.connect(AUTHDB)
    con.row_factory = sqlite3.Row
    row = con.execute('''SELECT u.id, u.email, u.name, u.role FROM sessions s
                         JOIN users u ON u.id = s.user_id
                         WHERE s.sid=? AND s.expires_at > ?''', (cookie_sid, int(time.time()))).fetchone()
    con.close()
    return dict(row) if row else None


def make_session(user_id):
    sid = secrets.token_urlsafe(32)
    con = sqlite3.connect(AUTHDB)
    con.execute('INSERT INTO sessions (sid,user_id,expires_at) VALUES (?,?,?)',
                (sid, user_id, int(time.time()) + SESSION_TTL))
    con.commit()
    con.close()
    return sid


VERIFY_EMAIL_TMPL = '''<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="color:#0f766e">Welcome to HuntMap, {name}!</h2>
  <p>Confirm your email to activate your account:</p>
  <p style="margin:24px 0">
    <a href="{base}/verify?code={code}"
       style="background:#0f766e;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none">
       Verify my email</a>
  </p>
  <p style="color:#64748b;font-size:13px">Or paste this code into the verify page:<br>
     <code style="background:#f1f5f9;padding:4px 8px;border-radius:4px">{code}</code></p>
  <p style="color:#94a3b8;font-size:12px">This link expires in 24 hours. If you didn't sign up, ignore this email.</p>
</div>'''


# ---------- HTTP ----------

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, fmt, *args):
        pass

    # helpers -------------------------------------------------------------
    def cookie(self, name):
        c = http_cookies.SimpleCookie(self.headers.get('Cookie', ''))
        return c[name].value if name in c else None

    def json_body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        try:
            return json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            return {}

    def send_json(self, obj, status=200, set_cookie=None):
        payload = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        if set_cookie:
            self.send_header('Set-Cookie', set_cookie) if False else self.send_header('Set-Cookie', set_cookie)
        self.end_headers()
        self.wfile.write(payload)

    def me(self):
        return session_user(self.cookie('huntmap_session'))

    def require_auth(self, admin=False):
        u = self.me()
        if not u:
            self.send_json({'error': 'Not signed in'}, 401)
            return None
        if admin and u['role'] != 'admin':
            self.send_json({'error': 'Admin only'}, 403)
            return None
        return u

    # routing -------------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith('/api/'):
            return self.route_api(u.path, u.query, None)
        if u.path.startswith('/verify'):
            qs = parse_qs(u.query)
            code = (qs.get('code') or [''])[0]
            return self.do_verify(code)
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path.startswith('/api/'):
            return self.route_api(u.path, u.query, self.json_body())
        self.send_json({'error': 'Not found'}, 404)

    def route_api(self, path, query, body):
        body = body if body is not None else self.json_body()
        m = {
            '/api/units.json': lambda: self.serve_units(),
            '/api/signup': lambda: self.api_signup(body),
            '/api/login': lambda: self.api_login(body),
            '/api/logout': lambda: self.api_logout(),
            '/api/me': lambda: self.api_me(),
            '/api/verify': lambda: self.api_verify(body),
            '/api/users': lambda: self.api_users(body),
            '/api/users/delete': lambda: self.api_user_delete(body),
            '/api/users/update': lambda: self.api_user_update(body),
            '/api/admin/settings': lambda: self.api_admin_settings(body),
        }
        fn = m.get(path)
        if fn:
            return fn()
        self.send_json({'error': 'Not found'}, 404)

    # endpoints ------------------------------------------------------------
    def serve_units(self):
        rows = []
        try:
            con = sqlite3.connect(DB)
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute(
                '''SELECT g.gmuid, g.county, g.elk_dau, g.sq_miles, g.center_lat, g.center_lon,
                          g.public_pct, g.habitat_score, g.harvest_score,
                          h.total_harvest, h.hunters, h.success_pct, h.rec_days
                   FROM gmus g LEFT JOIN harvest h
                     ON h.unit = g.gmuid AND h.section LIKE '%All Manners% '
                   ORDER BY g.gmuid''')]
            con.close()
            payload = json.dumps(rows).encode()
        except Exception as e:
            payload = json.dumps({'error': str(e)}).encode()
        self.send_response(200 if rows else 500)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def api_signup(self, body):
        email = (body.get('email') or '').strip().lower()
        name = (body.get('name') or '').strip()
        pw = body.get('password') or ''
        if not EMAIL_RE.match(email):
            return self.send_json({'error': 'Enter a valid email address'}, 400)
        if len(name) < 2:
            return self.send_json({'error': 'Enter your name'}, 400)
        if len(pw) < 8:
            return self.send_json({'error': 'Password must be at least 8 characters'}, 400)
        con = sqlite3.connect(AUTHDB)
        if con.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
            con.close()
            return self.send_json({'error': 'An account with that email already exists'}, 409)
        con.close()
        con = sqlite3.connect(AUTHDB)
        cur = con.execute('INSERT INTO users (email,name,password,role,verified,created_at) VALUES (?,?,?,?,0,?)',
                          (email, name, hash_pw(pw), 'user', int(time.time())))
        uid = cur.lastrowid
        con.commit()
        con.close()
        tok = create_token(uid, 'verify')
        link = f"{BASE_URL}/verify?code={tok}"
        try:
            send_mail(email, 'Verify your HuntMap account', VERIFY_EMAIL_TMPL.format(name=name, base=BASE_URL, code=tok))
            mailed = True
        except Exception as e:
            mailed = False
            print(f'signup mail failed: {e}')
        self.send_json({'ok': True, 'mailed': mailed,
                        'message': 'Account created! Check your email to verify before logging in.'})

    def api_login(self, body):
        email = (body.get('email') or '').strip().lower()
        pw = body.get('password') or ''
        con = sqlite3.connect(AUTHDB)
        con.row_factory = sqlite3.Row
        row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        con.close()
        if not row or not check_pw(pw, row['password']):
            return self.send_json({'error': 'Invalid email or password'}, 401)
        if not row['verified']:
            return self.send_json({'error': 'Verify your email first - check your inbox for the link'}, 403)
        sid = make_session(row['id'])
        self.send_json({'ok': True, 'user': {'email': row['email'], 'name': row['name'], 'role': row['role']}},
                       set_cookie=f'huntmap_session={sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}')

    def api_logout(self):
        sid = self.cookie('huntmap_session')
        if sid:
            con = sqlite3.connect(AUTHDB)
            con.execute('DELETE FROM sessions WHERE sid=?', (sid,))
            con.commit()
            con.close()
        self.send_json({'ok': True}, set_cookie='huntmap_session=; Path=/; HttpOnly; Max-Age=0')

    def api_me(self):
        u = self.me()
        self.send_json({'user': u} if u else {'user': None})

    def do_verify(self, code):
        """GET /verify?code=... -> mark verified, redirect to app with result banner."""
        if not code:
            return self._verify_page('Missing verification code', ok=False)
        uid = consume_token(code, 'verify')
        if not uid:
            return self._verify_page('Invalid or expired verification link - request a new one from the signup page', ok=False)
        con = sqlite3.connect(AUTHDB)
        con.execute('UPDATE users SET verified=1 WHERE id=?', (uid,))
        con.commit()
        con.close()
        return self._verify_page('Email verified! You can now log in.', ok=True)

    def _verify_page(self, msg, ok):
        color = '#0f766e' if ok else '#b91c1c'
        icon = '✅' if ok else '⚠️'
        cta = ('<a href="/" style="background:#0f766e;color:#fff;padding:12px 24px;'
               'border-radius:8px;text-decoration:none">Go to login</a>' if ok else '')
        page = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HuntMap — Email verification</title><style>
body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#1e293b;padding:40px;border-radius:16px;text-align:center;max-width:420px}}
h1{{color:{color};font-size:20px}} p{{line-height:1.5}}
</style></head><body><div class="card"><h1>{icon} {msg}</h1>{cta}</div></body></html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(page)))
        self.end_headers()
        self.wfile.write(page.encode())

    def api_verify(self, body):
        code = (body.get('code') or '').strip()
        if not code:
            return self.send_json({'error': 'Missing verification code'}, 400)
        uid = consume_token(code, 'verify')
        if not uid:
            return self.send_json({'error': 'Invalid or expired verification link'}, 400)
        con = sqlite3.connect(AUTHDB)
        con.execute('UPDATE users SET verified=1 WHERE id=?', (uid,))
        con.commit()
        con.close()
        self.send_json({'ok': True, 'message': 'Email verified! You can now log in.'})

    def api_users(self, body):
        u = self.require_auth(admin=True)
        if not u:
            return
        con = sqlite3.connect(AUTHDB)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            'SELECT id, email, name, role, verified, created_at FROM users ORDER BY created_at')]
        con.close()
        self.send_json({'users': rows})

    def api_user_delete(self, body):
        u = self.require_auth(admin=True)
        if not u:
            return
        uid = body.get('id')
        if uid == u['id']:
            return self.send_json({'error': "You can't delete your own account"}, 400)
        con = sqlite3.connect(AUTHDB)
        con.execute('DELETE FROM users WHERE id=?', (uid,))
        con.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
        con.execute('DELETE FROM tokens WHERE user_id=?', (uid,))
        con.commit()
        con.close()
        self.send_json({'ok': True})

    def api_user_update(self, body):
        u = self.require_auth(admin=True)
        if not u:
            return
        uid = body.get('id')
        name = (body.get('name') or '').strip()
        role = body.get('role')
        verified = body.get('verified')
        pw = body.get('password') or ''
        sets, vals = [], []
        if name:
            sets.append('name=?'); vals.append(name)
        if role in ('admin', 'user'):
            sets.append('role=?'); vals.append(role)
        if verified is not None:
            sets.append('verified=?'); vals.append(1 if verified else 0)
        if pw:
            if len(pw) < 8:
                return self.send_json({'error': 'Password must be at least 8 characters'}, 400)
            sets.append('password=?'); vals.append(hash_pw(pw))
        if not sets:
            return self.send_json({'error': 'Nothing to update'}, 400)
        vals.append(uid)
        con = sqlite3.connect(AUTHDB)
        con.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)
        con.commit()
        con.close()
        self.send_json({'ok': True})

    def api_admin_settings(self, body):
        u = self.require_auth(admin=True)
        if not u:
            return
        if body is not None and body:
            for k in SMTP_FIELDS:
                if k in body and body[k] is not None:
                    set_setting(k, str(body[k]).strip())
        cfg = smtp_config()
        cfg['smtp_password'] = '********' if cfg['smtp_password'] else ''
        self.send_json({'settings': cfg, 'test_sent': bool(body and body.get('send_test'))})
        if body and body.get('send_test'):
            try:
                send_mail(body.get('test_to') or u['email'], 'HuntMap SMTP test',
                          '<p>SMTP settings are working. 🦌</p>')
            except Exception as e:
                self.send_json({'error': f'Test send failed: {e}'}, 500)


if __name__ == '__main__':
    init_authdb()
    print(f'HuntMap serving {WEB} on :{PORT}')
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()