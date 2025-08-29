import os
try:
    os.chdir(os.path.dirname(__file__))
except Exception:
    pass
# -*- coding: utf-8 -*-
# === Divine Brain Lotto Forecast Centre Flask App =====
import os, glob, tempfile, shutil, subprocess, re, sys, json
from datetime import datetime, timedelta, timezone
from collections import Counter
from flask import request, session, Flask, request, redirect, url_for, session, flash, abort, render_template_string, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# --- LIVE PUSH (local -> PA) ---
PA_UPLOAD_URL = "https://www.divinebrainlotteryforecastcentre.org/upload_predictions"
ADMIN_TOKEN   = os.getenv("ADMIN_TOKEN", "")  # set this in your local env to match PA

def push_games_to_live(games: dict, source="local-run", verify=False):
    """
    games = {
      "National": {"numbers":[1,2,3,4,5], "message":"two-sure X", "extra": {...}},
      "Monday Special": {"numbers":[...], "message":"..."}
    }
    """
    headers = {"Content-Type":"application/json"}
    if ADMIN_TOKEN:
        headers["X-Admin-Token"] = ADMIN_TOKEN
    payload = {"games": games, "source": source}
    r = requests.post(PA_UPLOAD_URL, json=payload, headers=headers, timeout=20, verify=verify)
    r.raise_for_status()
    print("✅ push_games_to_live:", r.text[:200])
# --- /LIVE PUSH ---


# --- Mobile-User-Agent Keywords ----------------------------------------------
_mobile_keywords = (
    # Core tokens
    'iphone', 'ipod', 'ipad', 'android', 'mobile', 'mobi',
    'windows phone', 'iemobile', 'opera mini', 'opera mobi', 'blackberry',
    # Samsung
    'samsung', 'galaxy', 'sm-',
    # Huawei & Honor
    'huawei', 'honor',
    # Motorola
    'motorola', 'moto', 'xt',
    # Nokia & Lumia
    'nokia', 'lumia',
    # LG
    'lg',
    # HTC
    'htc',
    # Sony / Xperia
    'sony', 'xperia',
    # OnePlus
    'oneplus',
    # Google
    'pixel', 'nexus',
    # Xiaomi / Redmi / Poco / Mi
    'xiaomi', 'mi', 'redmi', 'poco',
    # Realme
    'realme',
    # Oppo / Reno
    'oppo', 'reno',
    # Vivo
    'vivo',
    # ZTE / Nubia
    'zte', 'nubia',
    # Asus / Zenfone
    'asus', 'zenfone',
    # Lenovo / Phab / Vibe
    'lenovo', 'phab', 'vibe',
    # Infinix
    'infinix',
    # Tecno
    'tecno',
    # Blu
    'blu',
    # Sharp
    'sharp',
    # Alcatel
    'alcatel',
    # Smaller / niche brands
    'blackview', 'doogee', 'ulefone', 'cubot', 'cat', 'caterpillar',
    'fairphone', 'panasonic'
)

def is_mobile_request():
    ua = (request.headers.get('User-Agent') or '').lower()
    return any(keyword in ua for keyword in _mobile_keywords)

# ?? Where login activity will be saved
LOG_FILE = os.path.join(os.path.dirname(__file__), 'login_logs.json')
login_logs = []

def load_logs():
    global login_logs
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                login_logs = json.load(f)
            except json.JSONDecodeError:
                login_logs = []

def save_logs():
    with open(LOG_FILE, "w") as f:
        json.dump(login_logs, f)

# Load logs when app starts
load_logs()

# ===== Helper to get cached adverts from Admin upload =====
def get_ad_files():
    import json, os
    cache_path = os.path.join(app.root_path, "ad_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except:
            return []
    return []


app = Flask(__name__)





# --- BEGIN PA_GUARD_STOPITER ---
from functools import wraps
def guard_stopiteration(fn):
    @wraps(fn)
    def _inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except StopIteration as e:
            try:
                from flask import current_app, request
                current_app.logger.warning("StopIteration guarded in %s %s: %s", fn.__name__, getattr(request,'path',''), e)
            except Exception:
                pass
            return ("", 204)
    return _inner
# --- END PA_GUARD_STOPITER ---
# --- BEGIN PA_STATIC_ADS_DIR_PATCH ---
import os as _os
try:
    # Absolute ads directory using Flask's static folder
    ADS_DIR = _os.path.join(app.static_folder, 'images.advirt')
    _os.makedirs(ADS_DIR, exist_ok=True)

    # Safely rewrite os.listdir('static/images.advirt') -> os.listdir(ADS_DIR)
    _real_listdir = _os.listdir
    def _safe_listdir(path):
        try:
            p = str(path).replace('\\','/').rstrip('/')
            if p == 'static/images.advirt' or p == 'static/images.advirt/':
                return _real_listdir(ADS_DIR)
        except Exception:
            pass
        return _real_listdir(path)
    _os.listdir = _safe_listdir
except Exception:
    # Never break the app if patching fails
    pass
# --- END PA_STATIC_ADS_DIR_PATCH ---

# --- Safe ads dir helper (absolute path, never crashes) ---
def _ads_dir():
    try:
        base = app.static_folder  # absolute path to /static
    except Exception:
        base = os.path.join(os.path.dirname(__file__), 'static')
    ads = os.path.join(base, 'images.advirt')
    os.makedirs(ads, exist_ok=True)
    return ads

def list_ad_images():
    ads = _ads_dir()
    try:
        names = os.listdir(ads)
    except FileNotFoundError:
        names = []
    # return web paths for templates: static/images.advirt/<file>
    return [f"static/images.advirt/{n}" for n in names
            if n.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp'))]
import os

# --- Robust absolute ads dir (prevents FileNotFoundError) ---
ADS_DIR = os.path.join(app.static_folder, 'images.advirt')
os.makedirs(ADS_DIR, exist_ok=True)

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me')
os.makedirs(app.instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'lotto_users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



# --- BEGIN PA_PRESENCE_PATCH ---
try:
    from flask_login import current_user
except Exception:
    class _Anon: 
        is_authenticated = False
        id = None
    current_user = _Anon()

class Presence(db.Model):
    __tablename__ = "presence"
    user_id     = db.Column(db.Integer, primary_key=True)
    last_seen   = db.Column(db.DateTime, index=True)
    last_login  = db.Column(db.DateTime)
    last_logout = db.Column(db.DateTime)
    is_online   = db.Column(db.Boolean, default=False)

class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True)
    at      = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip      = db.Column(db.String(64))
    country = db.Column(db.String(8))
    ua      = db.Column(db.String(255))
    event   = db.Column(db.String(12))  # login|logout|ping

def _client_ip_country():
    ip = (request.headers.get("CF-Connecting-IP")
          or (request.headers.get("X-Forwarded-For","").split(",")[0].strip() if request.headers.get("X-Forwarded-For") else "")
          or (request.remote_addr or ""))
    return ip, request.headers.get("CF-IPCountry","")

def _presence_row(uid):
    row = Presence.query.get(uid)
    if not row:
        row = Presence(user_id=uid, is_online=False)
        db.session.add(row)
    return row

def _current_uid():
    try:
        if getattr(current_user, "is_authenticated", False) and getattr(current_user, "id", None) is not None:
            return int(current_user.id)
    except Exception:
        pass
    for k in ("user_id","userid","uid","id"):
        v = session.get(k)
        if v is None: 
            continue
        try: 
            return int(v)
        except Exception:
            continue
    return None

def mark_login(uid):
    ip,country = _client_ip_country()
    now = datetime.utcnow()
    row = _presence_row(uid)
    row.last_login = now
    row.last_seen  = now
    row.is_online  = True
    db.session.add(LoginLog(user_id=uid, ip=ip, country=country,
                            ua=request.headers.get("User-Agent","")[:255],
                            event="login"))
    db.session.commit()

def mark_seen(uid):
    ip,country = _client_ip_country()
    row = _presence_row(uid)
    row.last_seen = datetime.utcnow()
    row.is_online = True
    db.session.add(LoginLog(user_id=uid, ip=ip, country=country,
                            ua=request.headers.get("User-Agent","")[:255],
                            event="ping"))
    db.session.commit()

@app.before_request
def _pa_presence_before_request():
    if os.environ.get("PRESENCE_OFF") == "1":
        return
    try:
        uid = _current_uid()
        if not uid:
            return
        if not session.get("_presence_logged"):
            mark_login(uid)
            session["_presence_logged"] = True
        else:
            # keep "online" fresh
            mark_seen(uid)
    except Exception:
        # never block requests
        pass

@app.get("/me/ping")
def me_ping():
    if os.environ.get("PRESENCE_OFF") == "1":
        return ("", 204)
    try:
        uid = _current_uid()
        if uid:
            mark_seen(uid)
    except Exception:
        pass
    return ("", 204)

@app.context_processor
def _pa_inject_online():
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(minutes=2)
    online = Presence.query.filter(Presence.last_seen >= cutoff).all()
    return {"online_users": online, "online_count": len(online)}
# --- END PA_PRESENCE_PATCH ---

# --- BEGIN PA_CACHE_WARMER ---
@app.cli.command('recache')
def recache():
    """Warm key routes so your code reads .txt files and refreshes any in-app caches."""
    with app.app_context():
        c = app.test_client()
        paths = ['/', '/login']   # add more paths if needed
        results = {}
        for p in paths:
            try:
                r = c.get(p, follow_redirects=True)
                results[p] = r.status_code
            except Exception as e:
                results[p] = f'ERR:{e}'
        print("recache:", results)
# --- END PA_CACHE_WARMER ---


# ======== Models ========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(18), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    login_count = db.Column(db.Integer, default=0)
    is_blocked = db.Column(db.Boolean, default=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

class MatchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_no = db.Column(db.String(12), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CachedPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), unique=True, nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    shared_json = db.Column(db.Text, nullable=False)
    topX_json = db.Column(db.Text, nullable=False)
    top2_json = db.Column(db.Text, nullable=False)
    banker = db.Column(db.Integer, nullable=True)
    history_json = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='processing')

    def shared(self): return json.loads(self.shared_json)
    def topX(self): return json.loads(self.topX_json)
    def top2(self): return json.loads(self.top2_json)
    def history(self): return json.loads(self.history_json) if self.history_json else []

class UserPredict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    event_no = db.Column(db.String(12), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='predicts')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    sender   = db.relationship('User', foreign_keys=[sender_id],   backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    filename = db.Column(db.String(120), nullable=False)
    event_no = db.Column(db.String(12), nullable=False)
    shared = db.Column(db.Text, nullable=False)
    topX = db.Column(db.Text, nullable=False)
    top2 = db.Column(db.Text, nullable=False)
    banker = db.Column(db.Integer, nullable=True)
    actual_draw = db.Column(db.Text, nullable=False)
    shared_hits = db.Column(db.Integer, nullable=False)
    topX_hits = db.Column(db.Integer, nullable=False)
    two_sure_hits = db.Column(db.Integer, nullable=False)
    banker_hit = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
from flask import request, session, jsonify

@app.route('/api/cached_files')
def api_cached_files():
    day = request.args.get('day')
    if not day:
        return jsonify([])
    files = CachedPrediction.query.filter_by(day_of_week=day.title()).order_by(CachedPrediction.last_updated.desc()).all()
    return jsonify([{'filename': cp.filename, 'last_updated': cp.last_updated.strftime('%Y-%m-%d %H:%M')} for cp in files])
@app.context_processor
def inject_online_users():
    # Provide online users to ALL templates automatically
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    online_users = User.query.filter(User.last_active >= ten_min_ago, User.is_blocked == False).all()
    return dict(online_users=online_users)

ADMIN_PHONE = '233243638607'
ADMIN_PASSWORD = 'admin1234'
EXTRA_DEPENDENCIES = {
    'GENERAL_COMBO.py': ['a.code', 'counter.txt', 'number.txt']
}
CREDITS = ["A very big thank you to our sponsors: Mr Kaspa Antonio Afriyie,  Mr Emmanuel Kwame Dua an Engineer and a building contractor at Metcam Gh limited. Mawusi P. Kpegla of Revolution Ventures, Abigail Antwi of Kesty Queens Academy, Mr Noah Adai, Samuel Odame Alema Junior of 'Odame World Films production And  ALEMA FARMS. God bless you all..."]

REGISTER_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <title>Register - Divine Brain Lotto</title>
  <meta charset="utf-8">
  <style>
    body { font-family: "Segoe UI", sans-serif; background: #001f3f; color: #fff; margin:0; }
    .wrap { max-width:380px; margin:8% auto 0; padding:2rem 2.5rem; background:rgba(2,6,22,0.97); border-radius:14px;
      box-shadow:0 0 32px #0d3db988; text-align:center;}
    .wrap img { width:90px; }
    h2 { margin-top:1.1rem; color:#ffd700; }
    form { margin-top:2rem;}
    label { display:block; margin-bottom:.7rem; font-weight:bold;}
    input[type=text], input[type=password] {
      width:100%; padding:.8rem; border-radius:7px; border:1px solid #ffd70066; font-size:1rem;
      margin-bottom:1.1rem; background:#112247; color:#fff;
    }
    button { width:100%; padding:.85rem; border:none; border-radius:8px; background:#ffd700;
      color:#222; font-weight:bold; font-size:1.12rem; letter-spacing:1px;
      margin-top:.6rem; cursor:pointer; }
    .login-link { margin-top:1.5rem; font-size:.96rem;}
    .login-link a { color:#23c6d6; text-decoration:underline;}
    .msg { color:#ff7e66; margin-bottom:1.3rem;}
  </style>
</head>
<body>
<div class="wrap">
  <img src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo">
  <h2>Register an Account</h2>
  {% if msg %}<div class="msg">{{ msg }}</div>{% endif %}
  <form method="post">
    <label for="phone">Phone Number</label>
    <input type="text" name="phone" required placeholder="Enter your phone (digits only)">
    <label for="password">Create Password</label>
    <input type="password" name="password" required placeholder="Create a password">
    <button type="submit">Register</button>
  </form>
  <div class="login-link">
    Already registered? <a href="{{ url_for('login') }}">Login here</a>
  </div>
</div>
</body>
</html>
'''
LOGIN_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Login - Divine Brain Lotto</title>
  <style>
    body { font-family: Arial, sans-serif; background:#09264f; color:#fff; margin:0; }
    .wrap { max-width: 400px; margin: 50px auto; background:#012144; padding: 20px; border-radius: 8px; }
    label { display:block; margin-top: 15px; }
    input { width:100%; padding:8px; margin-top:5px; }
    button { margin-top: 15px; padding: 10px; width:100%; background:#ffd700; border:none; font-weight:bold; cursor:pointer; }
    .login-link { margin-top: 15px; }
    #ad-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background:#000; display:flex; flex-direction:column; align-items:center; justify-content:center; z-index:9999; }
    #ad-overlay video, #ad-overlay img { max-width:100%; max-height:80%; }
    .ad-close-hint { margin-top:15px; color:#fff; background:rgba(0,0,0,0.7); padding:8px; cursor:pointer; border-radius:4px; }
  </style>
  <script>
    const adFiles = {{ ad_files|tojson }};
    let currentIndex = 0;

    function showNextAd() {
      if (currentIndex >= adFiles.length) {
        document.getElementById('ad-overlay').style.display = 'none';
        return;
      }
      const file = adFiles[currentIndex];
      const video = document.getElementById('ad-video');
      const image = document.getElementById('ad-image');

      video.style.display = 'none';
      image.style.display = 'none';
      video.src = '';
      image.src = '';

      if (file.match(/\\.mp4$|\\.webm$|\\.ogg$/i)) {
        video.src = "/static/" + file;
        video.style.display = 'block';
        video.play();
        video.onended = () => {
          currentIndex++;
          showNextAd();
        };
      } else {
        image.src = "/static/" + file;
        image.style.display = 'block';
        setTimeout(() => {
          currentIndex++;
          showNextAd();
        }, 4000); // show images for 4 seconds
      }
    }

    window.onload = () => {
      if (adFiles.length > 0) {
        document.getElementById('ad-overlay').onclick = () => {
          document.getElementById('ad-overlay').style.display = 'none';
        };
        showNextAd();
      } else {
        document.getElementById('ad-overlay').style.display = 'none';
      }
    };
  </script>
</head>
<body>
  <!-- ADVERT OVERLAY -->
  <div id="ad-overlay">
    <video id="ad-video" style="display:none;" controls autoplay playsinline></video>
    <img id="ad-image" style="display:none;" alt="Ad">
    <div class="ad-close-hint">Tap/click anywhere to close advert.</div>
  </div>

  <!-- LOGIN FORM -->
  <div class="wrap">
    <h2>Login</h2>
    {% if msg %}<div class="msg">{{ msg }}</div>{% endif %}
    <form method="post">
      <label for="phone">Phone Number</label>
      <input type="text" name="phone" required placeholder="Enter your phone (digits only)">
      <label for="password">Password</label>
      <input type="password" name="password" required placeholder="Enter your password">
      <button type="submit">Login</button>
    </form>
    <div class="login-link">
      No account? <a href="{{ url_for('register') }}">Register here</a>
    </div>
  </div>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <title>Admin Dashboard - Divine Brain Lotto</title>
  <meta charset="utf-8">
  <style>
    body { font-family:"Segoe UI",sans-serif; background:#09264f; color:#e8f1fa; margin:0;}
    .wrap { max-width:900px; margin:36px auto 0; background:rgba(4,18,38,0.98); border-radius:14px;
      box-shadow:0 0 40px #0d3db988; padding:1.5rem 2.7rem 2.3rem 2.7rem;}
    h2 { color:#ffd700; text-align:center;}
    table { width:100%; border-collapse:collapse; background:#012144;}
    th, td { padding:12px 7px; border-bottom:1px solid #244470;}
    th { background:#1a49b8; color:#fff; font-weight:bold;}
    td { text-align:center; font-size:1.03rem;}
    tr:nth-child(even) { background:#091d38; }
    .blocked { color:#fa5d41; font-weight:bold;}
    .btn { display:inline-block; padding:7px 15px; border-radius:5px; background:#ffe066; color:#191900;
      font-weight:bold; text-decoration:none; margin:0 2px;}
    .btn.block { background:#fa5d41; color:#fff;}
    .btn.unblock { background:#22cc99;}
    .btn.del { background:#1a49b8; color:#fff;}
    .btn.logout { background:#222; color:#ffd700; float:right;}
    .section { margin-top:30px;}
    .online { color:#37f74b; font-weight:bold; font-size:1.11em;}
    .notif-list { background:#133e91bb; color:#ffd700; padding:10px 15px; margin:18px 0 24px 0; border-radius:8px;}
    .app-link { display:inline-block; margin:22px auto 0 auto; text-align:center; font-size:1.19em; }
    .app-link a { color:#00ced1; background:#111e; padding:7px 15px; border-radius:6px; text-decoration:none;}
    .adm-footer { text-align:center; color:#ccc; font-size:.95rem; margin-top:48px;}
  </style>
</head>
<body>
<div class="wrap">
  <h2>Admin Dashboard</h2>
    <div class="app-link">
    <a href="{{ url_for('main') }}">?? Open Main App &rarr;</a>
    <a class="btn" href="{{ url_for('admin_predictions') }}">?? Upload Predictions</a>
    <a class="btn logout" href="{{ url_for('logout') }}">Logout</a>
    <a class="btn" href="{{ url_for('view_logins') }}">?? Login Records</a>
    <a class="btn" href="{{ url_for('admin_adverts') }}">?? Manage Adverts</a>
</div>


  <div class="section">
    <h3>Registered Users</h3>
    <table>
      <tr>
        <th>Phone</th>
        <th>Registered</th>
        <th>Login Count</th>
        <th>Status</th>
        <th>Online?</th>
        <th>Actions</th>
      </tr>
      {% for u in users %}
      <tr>
        <td>{{ u.phone }}</td>
        <td>{{ u.reg_date.strftime("%Y-%m-%d %H:%M") }}</td>
        <td>{{ u.login_count }}</td>
        <td>
          {% if u.is_blocked %}<span class="blocked">Blocked</span>
          {% elif u.is_admin %}Admin{% else %}Active{% endif %}
        </td>
        <td>{% if online_now(u) %}<span class="online">Online</span>{% else %}-{% endif %}</td>
        <td>
          {% if not u.is_admin %}
            {% if u.is_blocked %}
              <a class="btn unblock" href="{{ url_for('unblock', user_id=u.id) }}">Unblock</a>
            {% else %}
              <a class="btn block" href="{{ url_for('block', user_id=u.id) }}">Block</a>
            {% endif %}
            <a class="btn del" href="{{ url_for('delete_user', user_id=u.id) }}"
               onclick="return confirm('Delete this user?')">Delete</a>
          {% else %}
            <span style="color:#bbb;">?</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <div class="section">
    <h3>Prediction Match Notifications (Today)</h3>
    {% if matches %}
      <div class="notif-list">
        {% for m in matches %}<div>{{ m }}</div>{% endfor %}
      </div>
    {% else %}
      <div class="notif-list" style="color:#ddd;">No match notifications yet today.</div>
    {% endif %}
  </div>

  <!-- New Section: Cached Predictions by Day -->
  <div class="section">
    <h3>Cached Predictions by Day</h3>
    {% for day in days %}
      <h4 style="color:#ffd700; margin-top:20px;">{{ day }}</h4>
      {% if cp_by_day[day] %}
        <ul style="list-style:none; padding-left:0; margin-top:8px;">
        {% for cp in cp_by_day[day] %}
          <li style="margin-bottom:6px;">
            <strong>{{ cp.filename }}</strong>
            &mdash; Last updated {{ cp.last_updated.strftime("%Y-%m-%d %H:%M") }}
            <a href="{{ url_for('main') }}?file={{ cp.filename }}"
               class="btn" style="padding:4px 10px; font-size:.9em;">Preview</a>
          </li>
        {% endfor %}
        </ul>
      {% else %}
        <p style="font-style:italic; color:#ccc; margin-left:1em;">
          No files for {{ day }} yet.
        </p>
      {% endif %}
    {% endfor %}
  </div>

<div class="section">
  <h3>Recent User Runs</h3>
  <table>
    <tr><th>Phone</th><th>File</th><th>Event #</th><th>When</th></tr>
    {% for run in recent_runs %}
    <tr>
      <td>{{ run.user.phone }}</td>
      <td>{{ run.filename }}</td>
      <td>{{ run.event_no }}</td>
      <td>{{ run.timestamp.strftime("%Y-%m-%d %H:%M") }}</td>
    </tr>
    {% endfor %}
  </table>
</div>

  <div class="adm-footer">
    &copy; 2025 Divine Brain Lotto Forecast Centre
  </div>
</div>
<script>
  window.addEventListener('load', () => {
    speechSynthesis.speak(
      new SpeechSynthesisUtterance(
        "Welcome to Divine Brain Lotto Admin Dashboard"
      )
    );
  });
</script>
</body>
</html>
'''
ADMIN_PREDICTIONS_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <title>Upload Predictions - Divine Brain Lotto</title>
  <meta charset="utf-8">
  <style>
    body { font-family:"Segoe UI",sans-serif; background:#09264f; color:#e8f1fa; }
    .wrap { max-width:480px; margin:50px auto; background:rgba(4,18,38,0.98);
            padding:2rem; border-radius:10px; }
    h2 { text-align:center; color:#ffd700; }
    form { text-align:center; }
    select, input[type=file] { width:100%; padding:.5rem; margin:.8rem 0;
                               border-radius:5px; border:1px solid #244470; background:#012144; color:#e8f1fa; }
    button { padding:.6rem 1.2rem; border:none; border-radius:5px;
             background:#ffd700; color:#191900; font-weight:bold; cursor:pointer; }
    a.back { display:block; text-align:center; color:#00ced1; margin-top:1.2rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>Upload &amp; Cache Predictions</h2>
    {% if msg %}
      <div style="color:#ffe066; text-align:center; margin-bottom:1rem;">{{ msg }}</div>
    {% endif %}
    <form method="post" enctype="multipart/form-data">
      <label>Day of Week:<br>
        <select name="day_of_week" required>
          <option value="">--Select--</option>
          <option>Monday</option><option>Tuesday</option><option>Wednesday</option>
          <option>Thursday</option><option>Friday</option><option>Saturday</option>
          <option>Sunday</option>
        </select>
      </label>
      <label>Prediction .txt files:<br>
        <input type="file" name="files" accept=".txt" multiple required>
      </label>
      <button type="submit">Upload &amp; Cache</button>
    </form>
    <a class="back" href="{{ url_for('admin') }}">? Back to Admin Dashboard</a>
  </div>
</body>
</html>
'''

HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Divine Brain Lotto Forecast Centre</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
  html { box-sizing:border-box; }
  *,*:before,*:after { box-sizing:inherit; }
  body { margin:0; padding:0; min-height:100vh; overflow-x:hidden;
    font-family:"Segoe UI",sans-serif; background: url("{{ url_for('static', filename='db_lotto_hall.png') }}") center/cover no-repeat fixed;
    animation: sparkle 7s linear infinite, pulseGlow 4s ease-in-out infinite alternate; color:#eef;
  }
  @keyframes sparkle { 0%{background-position:0% 0%;} 50%{background-position:100% 100%;} 100%{background-position:0% 0%;} }
  @keyframes pulseGlow { from{filter:brightness(1) contrast(1.09);} to{filter:brightness(1.19) contrast(1.16) saturate(1.08);} }
  #splash {position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.72);
    display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:9999;
    animation: fadeOut 1.5s ease-out 2.9s forwards;}
  @keyframes fadeOut { to{opacity:0; visibility:hidden;} }
  #splash img {width:170px; animation: popIn 1s ease-out;}
  @keyframes popIn { from{transform:scale(0.1);} to{transform:scale(1);} }
  #splash .welcome-text {margin-top:1.6rem; font-size:1.6rem; color:#fff;
    animation: popIn 1s ease-out 0.7s forwards; opacity:0;}
  #main-content { display:none; }
  header { display:flex; align-items:center; justify-content:space-between;
    padding:1.3rem 2.3rem; background: rgba(0,0,0,0.61); border-bottom:1.5px solid #00335c7a;}
  header img { height:75px; }
  header h1 { font-size:2rem; margin:0 0 0 8px; color:#fff;
    text-transform:uppercase; letter-spacing:1.5px; font-weight:700;
    text-shadow: 1px 2px 8px #123e7e44;
  }
  .contact { text-align:right; font-size:0.97rem; }
  .contact a { color:#9feef7; text-decoration:none; margin-right:12px; }
  .nav-btns { display:flex; align-items:center; gap:11px;}
  .nav-btns a {
    display:inline-block; padding:8px 18px; border-radius:6px;
    background:linear-gradient(91deg,#ffd700 70%,#fa5d41 110%);
    color:#222; font-weight:bold; font-size:1.01em; margin-left:8px;
    border:none; box-shadow:0 2px 11px #ffde0081, 0 0 9px #fff4;
    text-decoration:none; transition:background .2s, color .2s;
    cursor:pointer; letter-spacing:.7px;
  }
  .nav-btns a.admin { background:linear-gradient(88deg,#00ced1 60%,#1a49b8 120%);
    color:#fff;}
  .nav-btns a:hover { background:#ffd800; color:#0a1432; }
  .nav-btns a.admin:hover { background:#1a49b8; color:#ffd800;}
  @media (max-width:600px) {
    header { flex-direction:column; align-items:stretch; gap:10px; padding:0.7rem 1.2rem;}
    header img { height:55px; }
    header h1 { font-size:1.21rem; }
    .nav-btns a { padding:8px 10px; font-size:0.96em;}
  }
  main { max-width:860px; margin:2.6rem auto; padding:2.2rem; background: rgba(0,0,0,0.56);
    border-radius:13px; box-shadow:0 0 30px rgba(0,0,0,0.88); backdrop-filter: blur(4px);}
  form { display:flex; justify-content:center; margin-bottom:2rem; flex-wrap:wrap;}
  label { margin-right:0.5rem; color:#dde; font-size:1.04em;}
  select { appearance:none; -webkit-appearance:none; background: rgba(255,255,255,0.11); color:#eef;
    font-size:1.04rem; padding:0.6rem 1.3rem; border:1.2px solid rgba(255,255,255,0.35);
    border-radius:6px; min-width:180px; cursor:pointer; transition: background .3s, border-color .3s; }
  select:hover, select:focus { background: rgba(255,255,255,0.22); border-color:#ffd700; outline:none; }
  select option { background:#233; color:#eee; }
  button { font-size:1.03rem; padding:.66rem 1.22rem; margin-left:1.15rem; border:none; border-radius:7px;
    background:#ffd700; color:#000; font-weight:bold; box-shadow:0 0 10px rgba(255,215,0,0.58);
    cursor:pointer; transition: transform .2s; }
  button:hover { transform: translateY(-2px) scale(1.04);}
  h2 { text-align:center; font-size:2rem; margin-top:2.1rem; color:#ffd700;
    text-shadow:1px 2px 4px rgba(0,0,0,0.75); }
  .info-board { text-align:center; margin-bottom:1.1rem; color:#dde; }
  .info-board span { display:inline-block; margin:0 .56rem; padding:.33rem .91rem;
    background: rgba(255,255,255,0.13); border-radius:5px; transition: background .3s; }
  .info-board span:hover { background: rgba(255,255,255,0.22); }
  .shared, .topX, .top2 { display:flex; justify-content:center; flex-wrap:wrap; margin:1.2rem 0; }
  .shared div, .topX div {
    background:#ffd700; color:#000; font-weight:bold;
    width:77px; height:77px; display:flex; justify-content:center; align-items:center;
    border-radius:8px; font-size:1.5rem; margin:.57rem;
    box-shadow:2px 2px 10px rgba(0,0,0,0.67); transition: transform .2s;
  }
  .shared div:hover, .topX div:hover { transform: scale(1.11); }
  .top2 .two-sure-anim {
    font-weight: bold;
    background:#00ced1;
    color:#000;
    width:90px; height:90px;
    display:flex; justify-content:center; align-items:center;
    border-radius:50%;
    font-size:2rem; margin:.6rem;
    box-shadow: 0 0 40px #00eaff, 0 0 12px #fff, 0 0 32px #ffd90088;
    animation: burnTwist 2s cubic-bezier(.5,1.3,.3,1.2) infinite alternate;
    text-shadow: 0 0 16px #fff, 0 0 32px #ffc80077;
  }
  .banker.banker-anim {
    font-weight: bold;
    text-align:center; font-size:2.3rem; margin-top:1rem;
    color:#ffa500;
    text-shadow:2px 2px 4px #000, 0 0 24px #fff, 0 0 60px #ff6b0088;
    box-shadow: 0 0 40px #ffa50099, 0 0 80px #fff688;
    animation: burnTwist 2.8s cubic-bezier(.5,1.3,.3,1.2) infinite alternate;
    filter: brightness(1.15) drop-shadow(0 0 24px #ff9100cc);
  }
  @keyframes burnTwist {
    0%   { transform: rotate(-12deg) scale(1.03); filter: brightness(1.10) hue-rotate(-8deg); }
    20%  { transform: rotate(8deg) scale(1.12) skewY(-3deg); filter: brightness(1.35) drop-shadow(0 0 32px #fff688);}
    35%  { transform: rotate(-2deg) scale(0.96) skewX(5deg);}
    60%  { transform: rotate(4deg) scale(1.08) skewY(4deg);}
    85%  { transform: rotate(-8deg) scale(1.15);}
    100% { transform: rotate(6deg) scale(1.03);}
  }
  .topX .top14-anim {
    animation: top14BounceIn 0.8s cubic-bezier(.5,1.5,.5,1) backwards;
    transition: transform .7s cubic-bezier(.6,.3,.7,1.7);
    will-change: transform;
  }
  @keyframes top14BounceIn {
    0%   { transform: translateY(-90px) scale(0.3); opacity:0;}
    80%  { transform: translateY(12px) scale(1.05);}
    100% { transform: translateY(0) scale(1); opacity:1;}
  }
  #historyOverlay {
    position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:5000;
    display:none; flex-direction:column; align-items:center; overflow-y:auto;
    justify-content:center;
    color:#fff;
    text-shadow: 0 0 8px #133e91, 0 0 16px #35559a66;
    padding:2rem; box-sizing:border-box;
  }
  #historyOverlay .closeHint {
    color:#ccc;font-size:.9rem;margin-top:1rem;text-align:center;
  }
  #historyOverlayBG {
    position:absolute;top:0;left:0;width:100%;height:100%;z-index:-1;object-fit:cover;
    opacity:0.34;pointer-events:none;
  }
  #historyOverlay .historyContent {
    position:relative;z-index:2;max-width:93vw;
    background:rgba(5,7,21,0.86);border-radius:18px;padding:2rem 1.2rem 1.5rem 1.2rem;
    box-shadow:0 0 32px #111a;
  }
  .historyContent h2 {
    color:#1a49b8;
    text-shadow: 0 0 8px #fff, 0 0 22px #05153999;
  }
  .historyContent .match {
    color:#1de396;
    font-weight:bold;
    font-size:1.18em;
    text-shadow: 0 0 10px #000, 0 0 12px #0e6f1a88;
  }
  .historyContent .empty {
    color:#ccc;font-style:italic;text-align:center;
  }
  #date-bar {
    text-align:center;
    margin-top:1.2rem;
    margin-bottom:-1.5rem;
    font-size:1.14rem;
    color:#0d3db9;
    font-weight:bold;
    letter-spacing:1.2px;
    text-shadow:1px 1px 5px #0d3db944;
  }
  #match-popup {
    display:none;
    position:fixed;
    left:50%; bottom:62px; transform:translateX(-50%);
    background: linear-gradient(92deg, #13a5ff 70%, #ffa500 100%);
    color:#fff;
    border: 2px solid #ffd700;
    border-radius:14px;
    box-shadow: 0 0 30px #1fc8ffcc, 0 0 11px #ffd90077;
    font-weight:bold;
    font-size:1.18rem;
    z-index:50001;
    min-width: 210px;
    max-width: 96vw;
    padding:15px 27px 13px 27px;
    animation: popupBlink 1.07s infinite alternate;
    text-align:center;
    pointer-events: all;
    cursor:pointer;
  }
  @media (max-width:600px) {
    #match-popup { font-size:1.01rem; min-width:140px; padding:10px 6vw;}
  }
  @keyframes popupBlink {
    from { filter: brightness(1.0); opacity:0.30;}
    to   { filter: brightness(1.22); opacity:1;}
  }
  #ad-overlay {
    position: fixed; left:0; top:0; width:100vw; height:100vh; background:rgba(0,0,0,0.98);
    z-index: 120000; display: none; justify-content:center; align-items:center; flex-direction:column;
    animation: fadeInAd 0.7s;
  }
  @keyframes fadeInAd { from {opacity:0;} to {opacity:1;} }
  #ad-overlay video, #ad-overlay img {
    max-width:94vw; max-height:77vh; border-radius:18px; box-shadow:0 0 48px #111c;
    background: #000;
    display: block;
    margin: 0 auto;
  }
  #ad-logo {
    position:absolute; left:16px; bottom:26px; width:79px; opacity:0.92; z-index:3;
    filter:drop-shadow(0 0 14px #ffe)
  }
  #ad-overlay .ad-close-hint {
    color:#ffe; font-size:1.07em; text-align:center; margin-top:20px; opacity:0.85;
  }
  @media (max-width:600px) {
    #ad-logo { width:44px; left:6px; bottom:7px;}
    #ad-overlay .ad-close-hint { font-size:.97em;}
  }
  #credits-bar {
    width:100vw; position:fixed; left:0; bottom:0; z-index:60000;
    height:44px; background:rgba(4,18,38,0.93);
    overflow:hidden; display:flex;align-items:center;
  }
  #credits-slide {
    display:inline-block;white-space:nowrap;
    color:#e9f3ff;font-size:1.13rem;font-family:Georgia,serif;
    font-weight:bold;
    letter-spacing:1.3px;
    text-shadow:0 0 6px #132a60bb, 0 0 20px #fff2;
  }
  footer { text-align:center; padding:1.1rem; font-size:.97rem; background: rgba(0,0,0,0.62); color:#ccc; margin-bottom:54px;}
  a { color:#abe; text-decoration:none; }
</style>
</head>
<body>
<div id="splash">
  <img src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo">
  <div class="welcome-text">Welcome to Divine Brain Lotto Forecast Centre</div>
</div>
<div id="main-content">
  <header>
    <img src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo">
    <h1>Divine Brain Lotto Forecast</h1>
    <div class="nav-btns">
  {% if is_admin %}
    <a class="admin" href="{{ url_for('admin') }}">Admin</a>
  {% endif %}
  <a href="{{ url_for('history') }}">History</a>
  <a href="{{ url_for('inbox') }}">
    Inbox{% if unread_count and unread_count > 0 %} ({{ unread_count }}){% endif %}
  </a>
  <a href="{{ url_for('logout') }}">Logout</a>
</div>

<div class="contact">
      <span>Call/WhatsApp: <a href="tel:+233243638607">+233 24 363 8607</a></span><br>
      <a href="https://www.facebook.com/dblotto" target="_blank">
        <img src="{{ url_for('static', filename='facebook.png') }}" alt="Facebook" style="height:18px;vertical-align:middle;"> Facebook
      </a>
      <a href="https://wa.me/233243638607" target="_blank">
        <img src="{{ url_for('static', filename='whatsapp.png') }}" alt="WhatsApp" style="height:18px;vertical-align:middle;"> WhatsApp
      </a>
    </div>
  </header>
 {% if is_admin %}
<!-- Online users block START -->
<div id="online-users-block" style="background:#012144; color:#00ffcc; text-align:center; padding:8px 0 7px 0; margin-bottom:16px; border-radius:8px;">
  Loading online users?
</div>
<!-- Online users block END -->
<script>
function refreshOnlineUsers() {
  fetch("/online-users")
    .then(r => r.json())
    .then(data => {
      const block = document.getElementById('online-users-block');
      const users = data.users || [];
      if (users.length === 0) {
        block.innerHTML = "No users online.";
      } else {
        block.innerHTML = "<strong>Online now:</strong> " + users.join(", ");
      }
    });
}
setInterval(refreshOnlineUsers, 10000); // refresh every 10 sec
window.addEventListener('DOMContentLoaded', refreshOnlineUsers);
</script>
{% endif %}
  <div id="date-bar"></div>
  <div id="match-popup"></div>
  <main>
    <form method="post">
   <form method="post" id="prediction-form">
  <label for="day">Select Day:</label>
  <select id="day-select" name="day" required>
    <option value="">--Select--</option>
    <option>Monday</option>
    <option>Tuesday</option>
    <option>Wednesday</option>
    <option>Thursday</option>
    <option>Friday</option>
    <option>Saturday</option>
    <option>Sunday</option>
  </select>
  <label for="file">Select Game:</label>
  <select id="file-select" name="file" required>
    <option value="">--First select a day--</option>
  </select>
  <button type="submit">Run Predictions</button>
  <button type="button" id="run-all-btn" style="margin-left:12px;">Run All Predictions For This Day</button>
</form>

<!-- Where the batch results will appear -->
<div id="batch-results"></div>

<script>
document.getElementById('day-select').addEventListener('change', function() {
  var day = this.value;
  var gameSelect = document.getElementById('file-select');
  gameSelect.innerHTML = '<option value="">Loading...</option>';
  if (!day) {
    gameSelect.innerHTML = '<option value="">--First select a day--</option>';
    return;
  }
  fetch('/api/cached_files?day=' + day)
    .then(res => res.json())
    .then(files => {
      if (files.length === 0) {
        gameSelect.innerHTML = '<option value="">No games for ' + day + '</option>';
      } else {
        gameSelect.innerHTML = '';
        files.forEach(f => {
          var opt = document.createElement('option');
          opt.value = f.filename;
          opt.textContent = f.filename + ' (updated ' + f.last_updated + ')';
          gameSelect.appendChild(opt);
        });
      }
    });
});

// Run All Predictions For This Day
document.getElementById('run-all-btn').addEventListener('click', function() {
  var day = document.getElementById('day-select').value;
  var batchDiv = document.getElementById('batch-results');
  batchDiv.innerHTML = ""; // Clear previous
  if (!day) {
    alert('Please select a day first.');
    return;
  }
  fetch('/api/cached_files?day=' + day)
    .then(res => res.json())
    .then(files => {
      if (files.length === 0) {
        batchDiv.innerHTML = '<b>No games for ' + day + '</b>';
        return;
      }
      batchDiv.innerHTML = '<b>Processing all games for ' + day + '...</b>';
      // For each file, fetch the prediction result
      Promise.all(
        files.map(f =>
          fetch('/run_prediction_api?file=' + encodeURIComponent(f.filename))
            .then(r => r.json())
            .then(pred => ({
              filename: f.filename,
              result: pred
            }))
        )
      ).then(allResults => {
        // Display results as a table
        let html = '<h3>Results for all ' + day + ' games</h3><table border="1" cellpadding="5" style="background:#fff;color:#000"><tr><th>File</th><th>Shared</th><th>TopX</th><th>Two Sure</th><th>Banker</th></tr>';
        allResults.forEach(r => {
          html += '<tr><td>' + r.filename + '</td>'
          + '<td>' + (r.result.shared ? r.result.shared.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.topX ? r.result.topX.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.top2 ? r.result.top2.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.banker !== undefined ? r.result.banker : '-') + '</td></tr>';
        });
        html += '</table>';
        batchDiv.innerHTML = html;
      });
    });
});
</script>


    {% if results %}
    {% if results %}
  <!-- ?your shared/topX/top2/banker markup? -->
  <script>
    speechSynthesis.speak(
      new SpeechSynthesisUtterance(
        "Your predictions are ready for {{ filename }}, event {{ event }}"
      )
    );
  </script>
{% endif %}

      <div class="info-board">
        <span><strong>File:</strong> {{ filename }}</span>
        <span><strong>Event:</strong> {{ event }}</span>
      </div>
      <h2>Shared Predictions</h2>
      <div class="shared">{% for n in results.shared %}<div>{{ n }}</div>{% endfor %}</div>
      <h2>{{ results.top_label }}</h2>
      <div class="topX" id="top14predictions">
        {% for n in results.topX %}
          <div class="top14-anim">{{ n }}</div>
        {% endfor %}
      </div>
      <h2>Two Sure</h2>
      <div class="top2">
        {% for n in results.top2 %}
          <div class="two-sure-anim">{{ n }}</div>
        {% endfor %}
      </div>
      <div class="banker banker-anim">?? Banker: {{ results.banker }}</div>
      <div style="text-align:center; margin-top:20px;">
        <button onclick="showHistory()">View Last 20 Historical Matches</button>
      </div>
    {% endif %}
  </main>
  {% if results %}
<script>
  // speak once your predictions are rendered:
  const runMsg = `Your predictions are ready for {{ filename }} event {{ event }}`;
  window.speechSynthesis.speak(
    new SpeechSynthesisUtterance(runMsg)
  );
</script>
{% endif %}

  <footer>
    &copy; 2025 Divine Brain Lotto Forecast Centre
  </footer>
</div>
<div id="credits-bar"><span id="credits-slide">{{ credits[0] }}</span></div>

<!-- =============== ADVERT OVERLAY ================ -->
<div id="ad-overlay">
  <video id="ad-video" src="" style="display:none;" controls autoplay playsinline></video>
  <img id="ad-image" src="" style="display:none;" alt="Ad">
  <img id="ad-logo" src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo">
  <div class="ad-close-hint">Tap/click anywhere to close advert.</div>
</div>

<!-- ============= Last 20 overlay (video/image bg handled in script) ========== -->
<div id="historyOverlay">
  <div id="historyOverlayBG"></div>
  <div class="historyContent">
    <h2>Last 20 Historical Matches</h2>
    {% if results and results.history %}
      {% for entry in results.history %}
        <div class="match" style="margin-bottom:16px;">
          <div><strong>Event {{ entry.event }}</strong></div>
          <div>Actual Draw: {{ entry.actual|join(', ') }}</div>
          <div>
            Shared Prediction: {{ entry.shared_pred|join(', ') }}<br>
            <strong>Shared Matched:</strong>
            {% if entry.shared_hits %}
              {{ entry.shared_hits|join(', ') }} ({{ entry.shared_hits|length }})
            {% else %}None{% endif %}
          </div>
          <div>
            Top Prediction: {{ entry.top_pred|join(', ') }}<br>
            <strong>Top Matched:</strong>
            {% if entry.top_hits %}
              {{ entry.top_hits|join(', ') }} ({{ entry.top_hits|length }})
            {% else %}None{% endif %}
          </div>
          <div>
            Two Sure Prediction: {{ entry.two_sure_pred|join(', ') }}<br>
            <strong>Two Sure Matched:</strong>
            {% if entry.two_sure_hits %}
              {{ entry.two_sure_hits|join(', ') }} ({{ entry.two_sure_hits|length }})
            {% else %}None{% endif %}
          </div>
          <div>
            Banker Prediction: {{ entry.banker_pred }}<br>
            <strong>Banker Matched:</strong>
            {% if entry.banker_hit %}
              {{ entry.banker_hit }}
            {% else %}None{% endif %}
          </div>
        </div>
      {% endfor %}
    {% else %}
      <div class="empty">No matches found in last 20 events.</div>
    {% endif %}
    <div class="closeHint">(overlay closes automatically or tap outside to close)</div>
  </div>
</div>

<script>
// Splash/welcome
window.addEventListener('load', () => {
  speechSynthesis.speak(new SpeechSynthesisUtterance("Welcome to Divine Brain Lotto Forecast Centre"));
  setTimeout(()=>{
    document.getElementById('splash').style.display='none';
    document.getElementById('main-content').style.display='block';
    setTimeout(showAdOverlay, 5200); // Run adverts after splash and match
  },3600);
});

// Date bar using real online time
fetch("https://worldtimeapi.org/api/ip")
  .then(r => r.json())
  .then(data => {
    let d = new Date(data.datetime);
    document.getElementById('date-bar').textContent =
      "Today is: " + d.toLocaleDateString(undefined, {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  })
  .catch(() => {
    let d = new Date();
    document.getElementById('date-bar').textContent =
      "Today is: " + d.toLocaleDateString(undefined, {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  });

// Top 14 shuffle animation every 5 seconds
function shuffleTop14() {
  const container = document.getElementById('top14predictions');
  if (!container) return;
  const children = Array.from(container.children);
  if (children.length < 2) return;
  for (let i = children.length - 1; i > 0; i--) {
    let j = Math.floor(Math.random() * (i + 1));
    [children[i], children[j]] = [children[j], children[i]];
  }
  children.forEach(child => {
    child.classList.remove('top14-anim');
    void child.offsetWidth;
    child.classList.add('top14-anim');
  });
  container.innerHTML = '';
  children.forEach(c => container.appendChild(c));
}
setInterval(shuffleTop14, 5500);

// History overlay logic
function showHistory() {
  var h = document.getElementById('historyOverlay');
  h.style.display = 'flex';
  startHistoryBg();
  setTimeout(function() {
    h.style.display = 'none';
    stopHistoryBg();
  }, 42000);
}
document.getElementById('historyOverlay').addEventListener('click', function(e){
  if (e.target === this) {
    this.style.display = 'none';
    stopHistoryBg();
  }
});

// Credits scroll: dynamically animate FULL length so nothing is cut
window.addEventListener('DOMContentLoaded', function() {
  const slide = document.getElementById('credits-slide');
  const bar = document.getElementById('credits-bar');
  if (!slide) return;
  function scrollCredits() {
    slide.style.transition = 'none';
    slide.style.transform = 'translateX(0)';
    setTimeout(function() {
      const textWidth = slide.offsetWidth;
      const barWidth = bar.offsetWidth;
      let duration = Math.max((textWidth + barWidth) / 40, 22);
      slide.style.transition = `transform ${duration}s linear`;
      slide.style.transform = `translateX(-${textWidth + 40}px)`;
      setTimeout(scrollCredits, duration*1000 + 500);
    }, 600);
  }
  scrollCredits();
});

// Popup match notification (bottom, touch to close, 10s)
{% if match_msgs %}
let popupText = `{% for m in match_msgs %}{{ m|escape }}\n{% endfor %}`.trim();
let popCount = 0, popMax = 1;
function showPopupMatch() {
  let p = document.getElementById('match-popup');
  p.textContent = popupText;
  p.style.display = 'block';
  popCount++;
  p.onclick = function(){p.style.display='none';};
  if(popCount < popMax) setTimeout(showPopupMatch, 10000);
  else setTimeout(()=>{ p.style.display='none'; },10000);
}
setTimeout(showPopupMatch, 1800);
{% endif %}

// === Adverts logic ===
const adOverlay = document.getElementById('ad-overlay');
const adVideo   = document.getElementById('ad-video');
const adImage   = document.getElementById('ad-image');
const adLogo    = document.getElementById('ad-logo');
let adImages = [], adCurrent = 0, adTimer = null, adShowed = false;

function showAdOverlay() {
  if (adShowed) return;
  adShowed = true;
  fetch("{{ url_for('static', filename='video.advirt.mp4') }}", {method:'HEAD'})
    .then(r => {
      if (r.ok) showVideoAd("{{ url_for('static', filename='video.advirt.mp4') }}");
      else fetchAdImages();
    })
    .catch(fetchAdImages);
}

function showVideoAd(src) {
  adImage.style.display = 'none';
  adVideo.style.display = 'block';
  adVideo.src = src;
  adOverlay.style.display = 'flex';
  adLogo.style.display = 'block';
  adVideo.currentTime = 0;
  adVideo.play();
  adVideo.onended = hideAdOverlay;
}

function fetchAdImages() {
  // Try to get list of images from a manifest
  fetch("{{ url_for('static', filename='images.advirt/manifest.json') }}")
    .then(r => r.json())
    .then(list => {
      adImages = list;
      if (adImages.length) showImageAd();
    })
    .catch(() => { // fallback: try some default names
      adImages = [];
      for (let i=1;i<=8;i++) adImages.push("{{ url_for('static', filename='images.advirt/') }}" + i + ".jpg");
      showImageAd();
    });
}

function showImageAd() {
  adOverlay.style.display = 'flex';
  adLogo.style.display = 'block';
  adImage.style.display = 'block';
  adVideo.style.display = 'none';
  adCurrent = 0;
  showNextAdImage();
  adTimer = setInterval(showNextAdImage, 4000);
}
function showNextAdImage() {
  if (!adImages.length) return;
  adImage.src = adImages[adCurrent % adImages.length];
  adCurrent++;
}
function hideAdOverlay() {
  adOverlay.style.display = 'none';
  adVideo.pause();
  adVideo.src = "";
  clearInterval(adTimer);
}
// Tap/click closes ad
adOverlay.onclick = hideAdOverlay;

// Show ad again after inactivity (20min = 1200000ms)
let lastActive = Date.now();
['mousemove','keydown','touchstart'].forEach(e=>{
  document.addEventListener(e,()=>{lastActive=Date.now();});
});
setInterval(()=>{
  if(Date.now()-lastActive > 1200000) {
    adShowed=false; showAdOverlay();
    lastActive = Date.now();
  }
}, 45000);

// ========== History overlay bg slideshow/video ==========
let historyBgTimer, historyBgType, histBgEl=document.getElementById('historyOverlayBG');
function startHistoryBg(){
  fetch("{{ url_for('static', filename='video.advirt.mp4') }}", {method:'HEAD'})
    .then(r=>{ if(r.ok) showHistVideo(); else showHistImages(); })
    .catch(showHistImages);
}
function showHistVideo() {
  histBgEl.innerHTML = `<video src="{{ url_for('static', filename='video.advirt.mp4') }}" autoplay loop muted playsinline style="width:100%;height:100%;object-fit:cover;border-radius:0;"></video>`;
}
function showHistImages() {
  let imgs = [];
  fetch("{{ url_for('static', filename='images.advirt/manifest.json') }}")
    .then(r => r.json())
    .then(list => { imgs=list; doHistImg(imgs); })
    .catch(()=>{for(let i=1;i<=8;i++)imgs.push("{{ url_for('static', filename='images.advirt/') }}"+i+".jpg");doHistImg(imgs);});
}
function doHistImg(imgs){
  let idx=0;
  if(!imgs.length) return;
  histBgEl.innerHTML = `<img src="${imgs[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:0;">`;
  historyBgTimer = setInterval(()=>{
    idx = (idx+1)%imgs.length;
    histBgEl.innerHTML = `<img src="${imgs[idx]}" style="width:100%;height:100%;object-fit:cover;border-radius:0;">`;
  },4200);
}
function stopHistoryBg(){
  histBgEl.innerHTML = "";
  clearInterval(historyBgTimer);
}
</script>
<script>
function showBluePopup(msg) {
  const popup = document.getElementById('match-popup');
  if (popup) {
    popup.textContent = msg;
    popup.style.display = 'block';
    popup.onclick = () => popup.style.display = 'none';
    setTimeout(() => { popup.style.display = 'none'; }, 12000);
  } else {
    alert(msg); // fallback
  }
}

window.addEventListener("DOMContentLoaded", function() {
  fetch('/notification_api')
    .then(res => res.json())
    .then(data => {
      if (data && data.matched && (
        (data.matched.shared && data.matched.shared.length) ||
        (data.matched.topX && data.matched.topX.length) ||
        (data.matched.two_sure && data.matched.two_sure.length) ||
        data.matched.banker
      )) {
        showBluePopup(data.message);
      }
    });
});
</script>
</body>
</html>
'''
HTML_TEMPLATE_MOBILE = '''
<!doctype html>
<html>
<head>
  <title>Divine Brain Lotto - Mobile</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
  <style>
    html { box-sizing:border-box; }
    *,*:before,*:after { box-sizing:inherit; }
    body {
      margin:0; padding:0; min-height:100vh;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #022139 url('{{ url_for('static', filename='db_lotto_hall.png') }}') center/cover no-repeat fixed;
      color:#fff;
    }
    .container { max-width: 100vw; padding:1.1rem .5rem 0 .5rem; }
    h1 {
      font-size:1.16em; color:#ffd700; text-align:center;
      margin: 1.3rem 0 0.6rem 0; letter-spacing:.1em;
    }
    .nav-btns {
      display: flex; justify-content: space-between; align-items: center;
      margin: .8rem 0 1.4rem 0; gap:3vw;
    }
    .nav-btns a {
      background: linear-gradient(88deg,#ffd700 70%,#fa5d41 110%);
      color: #222; font-weight: bold; border-radius: 7px;
      font-size: .99em; padding: 7px 14px;
      text-decoration: none; box-shadow:0 2px 11px #ffde0081, 0 0 7px #fff4;
    }
    .nav-btns a.admin { background:linear-gradient(88deg,#00ced1 60%,#1a49b8 120%); color:#fff;}
    .nav-btns a:hover { background:#ffd800; color:#0a1432; }
    .nav-btns a.admin:hover { background:#1a49b8; color:#ffd800;}
    .contact {
      text-align:center; font-size:0.97rem; margin-bottom:.9rem;
    }
    .contact a, .contact span { color:#ffd700; text-decoration:none; margin: 0 10px;}
    .contact img {height:18px;vertical-align:middle;}
    .whatsapp { color:#25d366;font-weight:bold;}
    .form-block {
      background:rgba(0,0,0,0.67); border-radius:10px;
      padding: 1.2rem .8rem .6rem .8rem; margin-bottom:1.2rem;
      box-shadow: 0 2px 20px #000b;
    }
    form { display:flex; flex-direction:column; align-items:center; gap:.7em;}
    label { color:#ffd700; font-size:1.02em;}
    select {
      appearance:none; -webkit-appearance:none; background: rgba(255,255,255,0.14); color:#fff;
      font-size:1.01rem; padding:.55rem 1.2rem; border:1.1px solid #ffd70099;
      border-radius:7px; min-width:180px; cursor:pointer;
      margin-bottom:.65em;
    }
    button {
      font-size:1.04rem; padding:.60rem 1.12rem; border:none; border-radius:7px;
      background:#ffd700; color:#000; font-weight:bold; box-shadow:0 0 10px rgba(255,215,0,0.41);
      cursor:pointer; transition: transform .2s; margin-top:.4rem;
    }
    button:hover { transform: scale(1.06);}
    .info-board { text-align:center; margin:1rem 0 .8rem 0; color:#dde;}
    .info-board span { display:inline-block; margin:0 .39rem; padding:.19rem .71rem;
      background: rgba(255,255,255,0.13); border-radius:5px; transition: background .3s; }
    .shared, .topX, .top2 { display:flex; justify-content:center; flex-wrap:wrap; gap:10px; }
    .shared div, .topX div {
      background:#ffd700; color:#000; font-weight:bold;
      width:54px; height:54px; display:flex; justify-content:center; align-items:center;
      border-radius:7px; font-size:1.22rem; box-shadow:2px 2px 8px #111a; transition:transform .18s;
    }
    .shared div:hover, .topX div:hover { transform: scale(1.09);}
    .top2 .two-sure-anim {
      font-weight: bold;
      background:#00ced1;
      color:#000;
      width:64px; height:64px;
      display:flex; justify-content:center; align-items:center;
      border-radius:50%;
      font-size:1.32rem; box-shadow: 0 0 16px #00eaff, 0 0 7px #fff, 0 0 12px #ffd90088;
      animation: burnTwist 2s cubic-bezier(.5,1.3,.3,1.2) infinite alternate;
      text-shadow: 0 0 8px #fff, 0 0 12px #ffc80077;
      margin:.45rem;
    }
    .banker.banker-anim {
      font-weight: bold; text-align:center; font-size:1.55rem; margin-top:.82rem;
      color:#ffa500;
      text-shadow:2px 2px 4px #000, 0 0 16px #fff, 0 0 40px #ff6b0088;
      box-shadow: 0 0 18px #ffa50099, 0 0 40px #fff688;
      animation: burnTwist 2.8s cubic-bezier(.5,1.3,.3,1.2) infinite alternate;
      filter: brightness(1.15) drop-shadow(0 0 18px #ff9100cc);
    }
    @keyframes burnTwist {
      0%   { transform: rotate(-12deg) scale(1.03); filter: brightness(1.10) hue-rotate(-8deg);}
      20%  { transform: rotate(8deg) scale(1.10) skewY(-2deg);}
      35%  { transform: rotate(-2deg) scale(0.98) skewX(4deg);}
      60%  { transform: rotate(4deg) scale(1.08) skewY(3deg);}
      85%  { transform: rotate(-8deg) scale(1.12);}
      100% { transform: rotate(6deg) scale(1.03);}
    }
    main {padding:0;}
    h2 { text-align:center; font-size:1.16rem; color:#ffd700; margin:1.4rem 0 0.5rem 0;}
    .history-btn {
      background:#03253e; color:#ffd700; border:1px solid #ffd70070; border-radius:6px;
      font-size:1.02em; margin:10px auto 0 auto; display:block; padding:7px 1.7em;
    }
    #historyOverlay {
      position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:6000;
      display:none; flex-direction:column; align-items:center; overflow-y:auto;
      justify-content:center; color:#fff; text-shadow: 0 0 6px #133e91, 0 0 14px #35559a66;
      padding:1rem; box-sizing:border-box; background:rgba(7,15,33,0.94);
    }
    #historyOverlay .closeHint {
      color:#bbb;font-size:.91rem;margin-top:1rem;text-align:center;
    }
    #historyOverlayBG {
      position:absolute;top:0;left:0;width:100%;height:100%;z-index:-1;object-fit:cover;
      opacity:0.22;pointer-events:none;
    }
    .historyContent h2 {color:#1a49b8;text-shadow: 0 0 6px #fff, 0 0 12px #05153999;}
    .historyContent .match {color:#1de396;font-weight:bold;font-size:1.07em;}
    .historyContent .empty {color:#ccc;font-style:italic;text-align:center;}
    #match-popup {
      display:none; position:fixed; left:50%; bottom:54px; transform:translateX(-50%);
      background: linear-gradient(92deg, #13a5ff 70%, #ffa500 100%);
      color:#fff; border: 2px solid #ffd700; border-radius:14px; box-shadow: 0 0 13px #1fc8ffcc;
      font-weight:bold; font-size:1.07rem; z-index:80001; min-width: 90px; max-width: 98vw;
      padding:10px 11vw 10px 11vw; animation: popupBlink 1.09s infinite alternate;
      text-align:center; pointer-events: all; cursor:pointer;
    }
    @keyframes popupBlink {
      from { filter: brightness(1.0); opacity:0.30;}
      to   { filter: brightness(1.22); opacity:1;}
    }
    #credits-bar {
      width:100vw; position:fixed; left:0; bottom:0; z-index:99999;
      height:42px; background:rgba(4,18,38,0.93);
      overflow:hidden; display:flex;align-items:center;
      box-shadow:0 0 18px #1239;
    }
    #credits-slide {
      display:inline-block;white-space:nowrap;
      color:#e9f3ff;font-size:1.13rem;font-family:Georgia,serif;
      font-weight:bold;
      letter-spacing:1.1px;
      text-shadow:0 0 6px #132a60bb, 0 0 20px #fff2;
      padding-left: 9vw;
    }
    footer { text-align:center; padding:1.01rem; font-size:.95rem; background: rgba(0,0,0,0.55); color:#ccc; margin-bottom:42px;}
    a { color:#abe; text-decoration:none;}
  </style>
</head>
<body>
  <div class="container">

    <h1>Divine Brain Lotto Forecast (Mobile)</h1>
    <div class="nav-btns">
      {% if is_admin %}
        <a class="admin" href="{{ url_for('admin') }}">Admin</a>
      {% endif %}
      <a href="{{ url_for('history') }}">History</a>
      <a href="{{ url_for('inbox') }}">
        Inbox{% if unread_count and unread_count > 0 %} ({{ unread_count }}){% endif %}
      </a>
      <a href="{{ url_for('logout') }}">Logout</a>
    </div>
    <div class="contact">
      <span>WhatsApp/Call: <a class="whatsapp" href="https://wa.me/233243638607" target="_blank">+233 24 363 8607</a></span>
    </div>
    <div class="form-block">
     <form method="post" id="prediction-form">
  <label for="day">Select Day:</label>
  <select id="day-select" name="day" required>
    <option value="">--Select--</option>
    <option>Monday</option>
    <option>Tuesday</option>
    <option>Wednesday</option>
    <option>Thursday</option>
    <option>Friday</option>
    <option>Saturday</option>
    <option>Sunday</option>
  </select>
  <label for="file">Select Game:</label>
  <select id="file-select" name="file" required>
    <option value="">--First select a day--</option>
  </select>
  <button type="submit">Run Predictions</button>
  <button type="button" id="run-all-btn" style="margin-left:12px;">Run All Predictions For This Day</button>
</form>

<!-- Where the batch results will appear -->
<div id="batch-results"></div>

<script>
document.getElementById('day-select').addEventListener('change', function() {
  var day = this.value;
  var gameSelect = document.getElementById('file-select');
  gameSelect.innerHTML = '<option value="">Loading...</option>';
  if (!day) {
    gameSelect.innerHTML = '<option value="">--First select a day--</option>';
    return;
  }
  fetch('/api/cached_files?day=' + day)
    .then(res => res.json())
    .then(files => {
      if (files.length === 0) {
        gameSelect.innerHTML = '<option value="">No games for ' + day + '</option>';
      } else {
        gameSelect.innerHTML = '';
        files.forEach(f => {
          var opt = document.createElement('option');
          opt.value = f.filename;
          opt.textContent = f.filename + ' (updated ' + f.last_updated + ')';
          gameSelect.appendChild(opt);
        });
      }
    });
});

// Run All Predictions For This Day
document.getElementById('run-all-btn').addEventListener('click', function() {
  var day = document.getElementById('day-select').value;
  var batchDiv = document.getElementById('batch-results');
  batchDiv.innerHTML = ""; // Clear previous
  if (!day) {
    alert('Please select a day first.');
    return;
  }
  fetch('/api/cached_files?day=' + day)
    .then(res => res.json())
    .then(files => {
      if (files.length === 0) {
        batchDiv.innerHTML = '<b>No games for ' + day + '</b>';
        return;
      }
      batchDiv.innerHTML = '<b>Processing all games for ' + day + '...</b>';
      // For each file, fetch the prediction result
      Promise.all(
        files.map(f =>
          fetch('/run_prediction_api?file=' + encodeURIComponent(f.filename))
            .then(r => r.json())
            .then(pred => ({
              filename: f.filename,
              result: pred
            }))
        )
      ).then(allResults => {
        // Display results as a table
        let html = '<h3>Results for all ' + day + ' games</h3><table border="1" cellpadding="5" style="background:#fff;color:#000"><tr><th>File</th><th>Shared</th><th>TopX</th><th>Two Sure</th><th>Banker</th></tr>';
        allResults.forEach(r => {
          html += '<tr><td>' + r.filename + '</td>'
          + '<td>' + (r.result.shared ? r.result.shared.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.topX ? r.result.topX.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.top2 ? r.result.top2.join(', ') : '-') + '</td>'
          + '<td>' + (r.result.banker !== undefined ? r.result.banker : '-') + '</td></tr>';
        });
        html += '</table>';
        batchDiv.innerHTML = html;
      });
    });
});
</script>

      {% if results %}
        <div class="info-board">
          <span><strong>File:</strong> {{ filename }}</span>
          <span><strong>Event:</strong> {{ event }}</span>
        </div>
        <h2>Shared Predictions</h2>
        <div class="shared">{% for n in results.shared %}<div>{{ n }}</div>{% endfor %}</div>
        <h2>{{ results.top_label }}</h2>
        <div class="topX">{% for n in results.topX %}<div>{{ n }}</div>{% endfor %}</div>
        <h2>Two Sure</h2>
        <div class="top2">{% for n in results.top2 %}<div class="two-sure-anim">{{ n }}</div>{% endfor %}</div>
        <div class="banker banker-anim">?? Banker: {{ results.banker }}</div>
        <button class="history-btn" onclick="showHistory()">View Last 20 Historical Matches</button>
      {% endif %}
    </div>
  </div>

  <div id="match-popup"></div>

  <!-- History Overlay -->
  <div id="historyOverlay">
    <div id="historyOverlayBG"></div>
    <div class="historyContent">
      <h2>Last 20 Historical Matches</h2>
      {% if results and results.history %}
        {% for entry in results.history %}
          <div class="match" style="margin-bottom:13px;">
            <div><strong>Event {{ entry.event }}</strong></div>
            <div>Actual Draw: {{ entry.actual|join(', ') }}</div>
            <div>
              Shared Prediction: {{ entry.shared_pred|join(', ') }}<br>
              <strong>Shared Matched:</strong>
              {% if entry.shared_hits %}
                {{ entry.shared_hits|join(', ') }} ({{ entry.shared_hits|length }})
              {% else %}None{% endif %}
            </div>
            <div>
              Top Prediction: {{ entry.top_pred|join(', ') }}<br>
              <strong>Top Matched:</strong>
              {% if entry.top_hits %}
                {{ entry.top_hits|join(', ') }} ({{ entry.top_hits|length }})
              {% else %}None{% endif %}
            </div>
            <div>
              Two Sure Prediction: {{ entry.two_sure_pred|join(', ') }}<br>
              <strong>Two Sure Matched:</strong>
              {% if entry.two_sure_hits %}
                {{ entry.two_sure_hits|join(', ') }} ({{ entry.two_sure_hits|length }})
              {% else %}None{% endif %}
            </div>
            <div>
              Banker Prediction: {{ entry.banker_pred }}<br>
              <strong>Banker Matched:</strong>
              {% if entry.banker_hit %}
                {{ entry.banker_hit }}
              {% else %}None{% endif %}
            </div>
          </div>
        {% endfor %}
      {% else %}
        <div class="empty">No matches found in last 20 events.</div>
      {% endif %}
      <div class="closeHint">(overlay closes automatically or tap outside to close)</div>
    </div>
  </div>

  <!-- ========== Ads Overlay ========= -->
  <div id="ad-overlay" style="display:none; position:fixed; top:0;left:0;width:100vw;height:100vh;z-index:12000;justify-content:center;align-items:center;flex-direction:column;background:rgba(0,0,0,0.99);">
    <video id="ad-video" src="" style="display:none;max-width:97vw;max-height:55vh;border-radius:10px;background:#000;" controls autoplay playsinline></video>
    <img id="ad-image" src="" style="display:none;max-width:97vw;max-height:55vh;border-radius:10px;background:#000;" alt="Ad">
    <div class="ad-close-hint" style="color:#ffe; font-size:.98em; margin-top:12px; opacity:0.92;">Tap/click anywhere to close advert.</div>
  </div>

  <!-- CREDITS BAR (ROLLS) -->
  <div id="credits-bar">
    <span id="credits-slide">{{ credits[0] }}</span>
  </div>

  <footer>
    &copy; 2025 Divine Brain Lotto Forecast Centre
  </footer>

  <!-- SCRIPTS -->
  <script>
  // Splashless: just show main content

  // Top 14 shuffle animation every 5 seconds
  function shuffleTop14() {
    const container = document.querySelector('.topX');
    if (!container) return;
    const children = Array.from(container.children);
    if (children.length < 2) return;
    for (let i = children.length - 1; i > 0; i--) {
      let j = Math.floor(Math.random() * (i + 1));
      [children[i], children[j]] = [children[j], children[i]];
    }
    children.forEach(child => {
      child.classList.remove('top14-anim');
      void child.offsetWidth;
      child.classList.add('top14-anim');
    });
    container.innerHTML = '';
    children.forEach(c => container.appendChild(c));
  }
  setInterval(shuffleTop14, 5500);

  // History overlay logic
  function showHistory() {
    var h = document.getElementById('historyOverlay');
    h.style.display = 'flex';
    startHistoryBg();
    setTimeout(function() {
      h.style.display = 'none';
      stopHistoryBg();
    }, 42000);
  }
  document.getElementById('historyOverlay').addEventListener('click', function(e){
    if (e.target === this) {
      this.style.display = 'none';
      stopHistoryBg();
    }
  });

  // Rolling credits (mobile, long message support!)
  window.addEventListener('DOMContentLoaded', function() {
    const slide = document.getElementById('credits-slide');
    const bar = document.getElementById('credits-bar');
    if (!slide) return;

    function scrollCredits() {
      setTimeout(function() {
        slide.style.transition = 'none';
        slide.style.transform = 'translateX(0)';
        setTimeout(function() {
          const textWidth = slide.scrollWidth;
          const barWidth = bar.offsetWidth;
          let duration = Math.max((textWidth + barWidth) / 40, 22);
          slide.style.transition = `transform ${duration}s linear`;
          slide.style.transform = `translateX(-${textWidth + 40}px)`;
          setTimeout(scrollCredits, duration * 1000 + 800);
        }, 600);
      }, 350);
    }

    window.addEventListener('resize', scrollCredits);

    scrollCredits();
  });

  // Ads/video logic for mobile
  const adOverlay = document.getElementById('ad-overlay');
  const adVideo   = document.getElementById('ad-video');
  const adImage   = document.getElementById('ad-image');
  let adImages = [], adCurrent = 0, adTimer = null, adShowed = false;

  function showAdOverlay() {
    if (adShowed) return;
    adShowed = true;
    fetch("{{ url_for('static', filename='video.advirt.mp4') }}", {method:'HEAD'})
      .then(r => {
        if (r.ok) showVideoAd("{{ url_for('static', filename='video.advirt.mp4') }}");
        else fetchAdImages();
      })
      .catch(fetchAdImages);
  }

  function showVideoAd(src) {
    adImage.style.display = 'none';
    adVideo.style.display = 'block';
    adVideo.src = src;
    adOverlay.style.display = 'flex';
    adVideo.currentTime = 0;
    adVideo.play();
    adVideo.onended = hideAdOverlay;
  }

  function fetchAdImages() {
    fetch("{{ url_for('static', filename='images.advirt/manifest.json') }}")
      .then(r => r.json())
      .then(list => {
        adImages = list;
        if (adImages.length) showImageAd();
      })
      .catch(() => {
        adImages = [];
        for (let i=1;i<=8;i++) adImages.push("{{ url_for('static', filename='images.advirt/') }}" + i + ".jpg");
        showImageAd();
      });
  }

  function showImageAd() {
    adOverlay.style.display = 'flex';
    adImage.style.display = 'block';
    adVideo.style.display = 'none';
    adCurrent = 0;
    showNextAdImage();
    adTimer = setInterval(showNextAdImage, 3500);
  }
  function showNextAdImage() {
    if (!adImages.length) return;
    adImage.src = adImages[adCurrent % adImages.length];
    adCurrent++;
  }
  function hideAdOverlay() {
    adOverlay.style.display = 'none';
    adVideo.pause();
    adVideo.src = "";
    clearInterval(adTimer);
  }
  adOverlay.onclick = hideAdOverlay;
  setTimeout(showAdOverlay, 1200);

  // Popup match notification
  {% if match_msgs %}
  let popupText = `{% for m in match_msgs %}{{ m|escape }}\n{% endfor %}`.trim();
  let popCount = 0, popMax = 1;
  function showPopupMatch() {
    let p = document.getElementById('match-popup');
    p.textContent = popupText;
    p.style.display = 'block';
    popCount++;
    p.onclick = function(){p.style.display='none';};
    if(popCount < popMax) setTimeout(showPopupMatch, 9000);
    else setTimeout(()=>{ p.style.display='none'; },9000);
  }
  setTimeout(showPopupMatch, 1700);
  {% endif %}

  // History overlay bg slideshow/video
  let historyBgTimer, histBgEl=document.getElementById('historyOverlayBG');
  function startHistoryBg(){
    fetch("{{ url_for('static', filename='video.advirt.mp4') }}", {method:'HEAD'})
      .then(r=>{ if(r.ok) showHistVideo(); else showHistImages(); })
      .catch(showHistImages);
  }
  function showHistVideo() {
    histBgEl.innerHTML = `<video src="{{ url_for('static', filename='video.advirt.mp4') }}" autoplay loop muted playsinline style="width:100%;height:100%;object-fit:cover;border-radius:0;"></video>`;
  }
  function showHistImages() {
    let imgs = [];
    fetch("{{ url_for('static', filename='images.advirt/manifest.json') }}")
      .then(r => r.json())
      .then(list => { imgs=list; doHistImg(imgs); })
      .catch(()=>{for(let i=1;i<=8;i++)imgs.push("{{ url_for('static', filename='images.advirt/') }}"+i+".jpg");doHistImg(imgs);});
  }
  function doHistImg(imgs){
    let idx=0;
    if(!imgs.length) return;
    histBgEl.innerHTML = `<img src="${imgs[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:0;">`;
    historyBgTimer = setInterval(()=>{
      idx = (idx+1)%imgs.length;
      histBgEl.innerHTML = `<img src="${imgs[idx]}" style="width:100%;height:100%;object-fit:cover;border-radius:0;">`;
    },3200);
  }
  function stopHistoryBg(){
    histBgEl.innerHTML = "";
    clearInterval(historyBgTimer);
  }
  </script>
<script>
function showBluePopup(msg) {
  const popup = document.getElementById('match-popup');
  if (popup) {
    popup.textContent = msg;
    popup.style.display = 'block';
    popup.onclick = () => popup.style.display = 'none';
    setTimeout(() => { popup.style.display = 'none'; }, 12000);
  } else {
    alert(msg); // fallback
  }
}

window.addEventListener("DOMContentLoaded", function() {
  fetch('/notification_api')
    .then(res => res.json())
    .then(data => {
      if (data && data.matched && (
        (data.matched.shared && data.matched.shared.length) ||
        (data.matched.topX && data.matched.topX.length) ||
        (data.matched.two_sure && data.matched.two_sure.length) ||
        data.matched.banker
      )) {
        showBluePopup(data.message);
      }
    });
});
</script>

</body>
</html>
'''


INBOX_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head><title>Inbox</title><meta charset="utf-8"></head>
<body>
  <h2>Inbox for {{ user.phone }}</h2>
  <p><a href="{{ url_for('main') }}">? Back</a></p>
  <ul>
  {% for m in messages %}
    <li>
      <strong>From:</strong> {{ m.sender.phone }} |
      <strong>At:</strong> {{ m.timestamp.strftime("%Y-%m-%d %H:%M") }}<br>
      {{ m.content }}
    </li>
  {% endfor %}
  </ul>

  {% if is_admin %}
<h3>Send Message</h3>
<form method="post" action="{{ url_for('send_message_route') }}">
  <label>To:
    <select name="to_user_id" required>
      <option value="">--Choose User--</option>
      {% for u in all_users %}
        <option value="{{ u.id }}">{{ u.phone }} (ID {{ u.id }})</option>
      {% endfor %}
    </select>
  </label><br>
  <textarea name="content" rows="3" placeholder="Type your message?"></textarea><br>
  <button type="submit">Send</button>
</form>
{% endif %}
{% if not is_admin %}
<h3>Reply to Admin</h3>
<form method="post" action="{{ url_for('send_reply_to_admin') }}">
  <textarea name="content" rows="3" placeholder="Type your message?" required></textarea><br>
  <button type="submit">Send Reply</button>
</form>
{% endif %}

</body>
</html>
'''
HISTORY_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <title>Prediction History</title>
  <meta charset="utf-8">
  <style>
    body { font-family: "Segoe UI", sans-serif; background: #112247; color: #fff; margin: 0; }
    .wrap { max-width: 850px; margin: 40px auto 0; background: rgba(4,18,38,0.97); border-radius: 14px; box-shadow: 0 0 32px #0d3db988; padding: 2.3rem; }
    h2 { color: #ffd700; text-align: center; }
    table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; background: #002144; }
    th, td { padding: 11px 7px; border-bottom: 1px solid #244470; text-align: center; }
    th { background: #1a49b8; color: #fff; }
    tr:nth-child(even) { background: #091d38; }
    .hits { color: #0f0; font-weight: bold; }
    .nohits { color: #ff6666; }
    .back-link { display: block; text-align: center; color: #00ced1; margin-top: 1.7rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>Prediction History</h2>
    <table>
      <tr>
        <th>Date</th>
        <th>File</th>
        <th>Event</th>
        <th>Shared Hits</th>
        <th>TopX Hits</th>
        <th>Two-Sure Hits</th>
        <th>Banker Hit</th>
        <th>Actual Draw</th>
      </tr>
      {% for r in records %}
      <tr>
        <td>{{ r.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
        <td>{{ r.filename }}</td>
        <td>{{ r.event_no }}</td>
        <td class="{% if r.shared_hits > 0 %}hits{% else %}nohits{% endif %}">
        {{ r.shared_hits }}
        {% if r.shared_hits > 0 %} ({{ r.shared_matches | join(', ') }}) {% endif %}
        </td>
        <td class="{% if r.topX_hits > 0 %}hits{% else %}nohits{% endif %}">{{ r.topX_hits }}</td>
        <td class="{% if r.two_sure_hits > 0 %}hits{% else %}nohits{% endif %}">
        {{ r.two_sure_hits }}
        {% if r.two_sure_matches %} ({{ r.two_sure_matches | join(', ') }}) {% endif %}
        </td>
        <td class="{% if r.banker_hit %}hits{% else %}nohits{% endif %}">
        {{ 'Yes' if r.banker_hit else 'No' }}
        {% if r.banker_match %} ({{ r.banker_match }}) {% endif %}
</td>
        <td>{{ r.actual_draw }}</td>
      </tr>
      {% endfor %}
    </table>
    <a class="back-link" href="{{ url_for('main') }}">? Back to Main</a>
  </div>
</body>
</html>
"""

# ========== DB setup ==============
@app.before_request
def create_admin_once():
    if not hasattr(app, '_admin_inited'):
        app._admin_inited = True
        db.create_all()
        if not User.query.filter_by(phone=ADMIN_PHONE).first():
            db.session.add(User(
                phone=ADMIN_PHONE,
                password=generate_password_hash(ADMIN_PASSWORD),
                is_admin=True
            ))
            db.session.commit()

# ======== Helper functions ========
def list_txt_files():
    # For demo: pick from app root
    return sorted([os.path.basename(f) for f in glob.glob('*.txt')])

def run_and_capture(script, txt_file):
    name = os.path.basename(script)
    path = os.path.abspath(script)
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(txt_file, tmp)
        if os.path.exists('number.txt'):
            shutil.copy('number.txt', tmp)
        for dep in EXTRA_DEPENDENCIES.get(name, []):
            if os.path.exists(dep):
                shutil.copy(dep, tmp)
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        p = subprocess.Popen([sys.executable, path],
                             cwd=tmp, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, errors='ignore', env=env)
        out, _ = p.communicate('1\n\n')
    return out

def extract_groups(output: str):
    groups = []
    for grp in re.findall(r'\[([^\[\]]+)\]', output):
        nums = re.findall(r'\d+', grp)
        if len(nums) >= 3:
            groups.append([int(n) for n in nums])
    for line in output.splitlines():
        nums = [int(n) for n in re.findall(r'\b\d+\b', line) if 1 <= int(n) <= 90]
        if len(nums) >= 5:
            groups.append(nums[:5])
    return groups

def extract_all_numbers(groups):
    return [n for group in groups for n in group if 1 <= n <= 90]

def merge_and_rank_numbers(*lists_of_nums):
    freq = Counter()
    for nums in lists_of_nums:
        for n in nums:
            freq[n] += 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    result = []
    last_freq = None
    for idx, (n, c) in enumerate(ranked):
        if idx < 9:
            result.append(n)
            last_freq = c
        elif c == last_freq and len(result) < 14:
            result.append(n)
        else:
            break
    return result, freq

def get_twosure_and_banker(topX):
    twosure = topX[:2]
    banker = topX[0] if topX else None
    return twosure, banker

def parse_txt_file_events(fp, start_ev=1):
    events = []
    with open(fp) as f:
        for idx, line in enumerate(f):
            parts = re.findall(r'\d+', line)
            if len(parts) >= 10:
                win = [int(x) for x in parts[:5]]
                events.append((start_ev + idx, line.rstrip('\n'), win))
    return events

def get_latest_event_number(fp, start_ev=1):
    lines = []
    with open(fp) as f:
        for idx, line in enumerate(f):
            if re.findall(r'\d+', line):
                lines.append(idx)
    if not lines:
        return "N/A"
    return str(start_ev + lines[-1])

def get_today_matches():
    today = datetime.now(timezone.utc).date()
    matches = (MatchLog.query
        .filter(MatchLog.timestamp >= datetime.combine(today, datetime.min.time()))
        .order_by(MatchLog.timestamp.desc())
        .all())
    return [f"{m.filename}: {m.details} (Event {m.event_no})" for m in matches]

def _compute_shared_and_top_for_events(past_events):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        for _, line, _ in past_events:
            tmp.write(line + "\n")
        tmp_path = tmp.name
    scripts = [
        'GENERAL_COMBO.py',
        'A master upgrade 2.py',
        'AAAAA.3.py',
        'aaaaa4.py',
        'GREAT ALEMA .py',
        'final full_combo.py'
    ]
    extracted = {}
    for s in scripts:
        if os.path.exists(s):
            try:
                out = run_and_capture(s, tmp_path)
                groups = extract_groups(out)
                extracted[s] = extract_all_numbers(groups)
            except:
                extracted[s] = []
        else:
            extracted[s] = []
    master = []
    if extracted.get('A master upgrade 2.py'):
        out = run_and_capture('A master upgrade 2.py', tmp_path)
        for l in out.splitlines():
            if 'Super Repeated' in l or 'Super Repeat' in l:
                master.extend(int(x) for x in re.findall(r'\b\d+\b', l) if 1 <= int(x) <= 90)
    master = list(dict.fromkeys(master))[:max(1, int(0.05 * 35))]
    big_three = ['GREAT ALEMA .py', 'AAAAA.3.py', 'aaaaa4.py']
    big_nums = []
    for s in big_three:
        big_nums.extend(dict.fromkeys(extracted.get(s, [])))
    big_nums = big_nums[:min(int(0.7 * 35), len(big_nums))]
    rest    = 35 - len(master) - len(big_nums)
    general = extracted.get('GENERAL_COMBO.py') or extracted.get('final full_combo.py') or []
    used    = set(master + big_nums)
    filler  = [n for n in general if n not in used][:max(0, rest)]
    shared = list(dict.fromkeys(master + big_nums + filler))[:35]
    top_cands = []
    for s in big_three:
        for n in dict.fromkeys(extracted.get(s, [])):
            if n in shared:
                top_cands.append(n)
    top_cands = list(dict.fromkeys(top_cands))
    if len(top_cands) < 15:
        extras = [n for n in shared if n not in top_cands]
        top_cands += extras[:15 - len(top_cands)]
    topX = top_cands[:15]
    os.unlink(tmp_path)
    return shared, topX

def is_logged_in():
    return 'user_id' in session

def is_admin():
    uid = session.get('user_id')
    if not uid:
        return False
    user = db.session.get(User, uid)
    return user.is_admin if user else False

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return db.session.get(User, uid)

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*a, **k):
        if not is_logged_in():
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        user = current_user()
        if user and user.is_blocked:
            session.clear()
            flash("You are blocked by admin.", "danger")
            return redirect(url_for('login'))
        user.last_active = datetime.now(timezone.utc)
        db.session.commit()
        return f(*a, **k)
    return wrapper

def send_message(sender_id, receiver_id, content):
    m = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(m)
    db.session.commit()

def save_prediction_history(user_id, filename, event_no, shared, topX, top2, banker, actual_draw):
    shared_hits = len(set(shared) & set(actual_draw))
    topX_hits = len(set(topX) & set(actual_draw))
    two_sure_hits = len(set(top2) & set(actual_draw))
    banker_hit = banker in actual_draw if banker is not None else False
    record = PredictionHistory(
        user_id=user_id,
        filename=filename,
        event_no=event_no,
        shared=json.dumps(shared),
        topX=json.dumps(topX),
        top2=json.dumps(top2),
        banker=banker,
        actual_draw=json.dumps(actual_draw),
        shared_hits=shared_hits,
        topX_hits=topX_hits,
        two_sure_hits=two_sure_hits,
        banker_hit=banker_hit,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(record)
    db.session.commit()




# ============= ROUTES =============
import os

def get_adverts():
    ad_folder = os.path.join('static', 'adverts')
    if not os.path.exists(ad_folder):
        return []
    return [
        f for f in os.listdir(ad_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg'))
    ]

@app.route('/register', methods=['GET','POST'])
def register():
    if is_logged_in():
        return redirect(url_for('main'))
    msg = ''
    if request.method == 'POST':
        phone = request.form['phone'].strip()
        pw = request.form['password']
        if not re.fullmatch(r'\d{8,}', phone):
            msg = "Phone must be numbers, at least 8 digits."
        elif User.query.filter_by(phone=phone).first():
            msg = "Phone already registered."
        else:
            db.session.add(User(
                phone=phone,
                password=generate_password_hash(pw)
            ))
            db.session.commit()
            flash("Account created! Log in below.", "success")
            return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE, msg=msg)
import os

def get_adverts():
    ad_folder = os.path.join('static', 'adverts')
    if not os.path.exists(ad_folder):
        return []
    return [
        f for f in os.listdir(ad_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg'))
    ]
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('main'))

    msg = ''
    if request.method == 'POST':
        phone = request.form['phone'].strip()
        pw = request.form['password']
        user = User.query.filter_by(phone=phone).first()
        if not user or not check_password_hash(user.password, pw):
            msg = "Invalid credentials."
        elif user.is_blocked:
            msg = "You are blocked. Contact admin."
        else:
            session['user_id'] = user.id
            user.login_count += 1
            user.last_active = datetime.now(timezone.utc)
            db.session.commit()
            if user.is_admin:
                return redirect(url_for('admin'))
            return redirect(url_for('main'))

    # ==== ADVERTS SECTION ====
    ad_folder = os.path.join(app.static_folder, 'images.advirt')
    ad_files = get_ad_files()
    if os.path.exists(ad_folder):
        ad_files = [
            f'images.advirt/{f}' for f in os.listdir(ad_folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg'))
        ]

    return render_template_string(LOGIN_TEMPLATE, msg=msg, ad_files=ad_files)


@app.route('/admin/logins')
@require_login
def view_logins():
    if not is_admin():
        abort(403)
    
    log_path = "login_logs.json"
    try:
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = json.load(f)
        else:
            logs = []
    except:
        logs = []

    return render_template_string("""
    <h2 style="text-align:center;">Recent Login Records</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="margin:auto; background:white; color:black;">
        <tr><th>Phone</th><th>IP</th><th>Time</th></tr>
        {% for log in logs|reverse %}
        <tr>
            <td>{{ log.username }}</td>
            <td>{{ log.ip }}</td>
            <td>{{ log.time }}</td>
        </tr>
        {% endfor %}
    </table>
    <div style="text-align:center; margin-top:20px;"><a href="{{ url_for('admin') }}">? Back to Admin</a></div>
    """, logs=logs)


@app.route('/logout')
@require_login
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))

@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.png'))


@app.route('/admin')
@require_login
def admin():
    if not is_admin():
        return redirect(url_for('main'))
    users   = User.query.all()
    matches = get_today_matches()
    online_now = lambda u: (
        u.last_active and
        (((datetime.now(timezone.utc) - (u.last_active.replace(tzinfo=timezone.utc) if u.last_active.tzinfo is None else u.last_active)))) < timedelta(minutes=10)
    )
    days      = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    cp_by_day = {
        day: CachedPrediction.query.filter_by(day_of_week=day).all()
        for day in days
    }
    recent_runs = (
        UserPredict.query.order_by(UserPredict.timestamp.desc()).limit(20).all()
    )
    return render_template_string(
        ADMIN_TEMPLATE,
        users       = users,
        matches     = matches,
        online_now  = online_now,
        days        = days,
        cp_by_day   = cp_by_day,
        recent_runs = recent_runs
    )

@app.route('/block/<int:user_id>')
@require_login
def block(user_id):
    if not is_admin():
        abort(403)
    u = db.session.get(User, user_id)
    if u and not u.is_admin:
        u.is_blocked = True
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/unblock/<int:user_id>')
@require_login
def unblock(user_id):
    if not is_admin():
        abort(403)
    u = db.session.get(User, user_id)
    if u and not u.is_admin:
        u.is_blocked = False
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/delete/<int:user_id>')
@require_login
def delete_user(user_id):
    if not is_admin():
        abort(403)
    u = db.session.get(User, user_id)
    if u and not u.is_admin:
        db.session.delete(u)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/predictions', methods=['GET','POST'])
@require_login
@guard_stopiteration
def admin_predictions():
    if not is_admin():
        abort(403)

    msg = ''
    if request.method == 'POST':
        day_of_week = request.form.get('day_of_week')
        uploaded    = request.files.getlist('files')
        if not day_of_week or not uploaded:
            msg = 'Please select a day and at least one .txt file.'
        else:
            for file in uploaded:
                filename = file.filename
                save_dir = 'admin_uploaded_txt'
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                file.save(save_path)

                # --- 1) Extract scripts ------------------------------------
                combo_out = ''
                try:
                    combo_out = run_and_capture('GENERAL_COMBO.py', save_path)
                except:
                    pass
                if not combo_out:
                    try:
                        combo_out = run_and_capture('final full_combo.py', save_path)
                    except:
                        combo_out = ''

                extracted = {}
                # pull the six standalones from combo_out
                for name, nums_txt in re.findall(
                    r'(?m)^\s*(sim_eq|hybrid|hausdorff|chebyshev|elijah|time_series)\s*:\s*\[([^\]]+)\]',
                    combo_out
                ):
                    extracted[f'{name}.py'] = [int(n) for n in re.findall(r'\d+', nums_txt)]

                # pull A-master, GENERAL_COMBO, final full_combo, big3
                for s in [
                    'A master upgrade 2.py',
                    'GENERAL_COMBO.py','final full_combo.py',
                    'GREAT ALEMA .py','AAAAA.3.py','aaaaa4.py'
                ]:
                    try:
                        out = run_and_capture(s, save_path)
                        extracted[s] = extract_all_numbers(extract_groups(out))
                    except:
                        extracted[s] = []

                # --- 2) Build SHARED 35 ------------------------------------
                forced = []
                for script, limit in [
                    ('sim_eq.py',    2),
                    ('hausdorff.py', 4),
                    ('hybrid.py',    4),
                    ('chebyshev.py', 4),
                ]:
                    for n in extracted.get(script, [])[:limit]:
                        if n not in forced:
                            forced.append(n)

                cnt_am = Counter(extracted.get('A master upgrade 2.py', []))
                master_repeated = [n for n,_ in cnt_am.most_common(2)]

                big3 = ['GREAT ALEMA .py','AAAAA.3.py','aaaaa4.py']
                big_nums = []
                big_broken = False
                for s in big3:
                    out = extracted.get(s, [])
                    if not out:
                        big_broken = True
                    for n in dict.fromkeys(out):
                        if n not in big_nums:
                            big_nums.append(n)

                if big_broken:
                    master_repeated = []
                    for fb in ['FINAL MAWU INPROVED 2.py','A OLIVIA.py','A A. NEW.py']:
                        try:
                            fb_out  = run_and_capture(fb, save_path)
                            fb_nums = extract_all_numbers(extract_groups(fb_out))
                        except:
                            fb_nums = []
                        for n in fb_nums:
                            if n not in big_nums:
                                big_nums.append(n)

                used = set(forced + master_repeated + big_nums)
                slot_count = 35 - len(used)
                general_source = (
                    extracted.get('GENERAL_COMBO.py')
                    or extracted.get('final full_combo.py')
                    or []
                )
                filler = [n for n in general_source if n not in used][:max(0, slot_count)]

                raw_shared = forced + master_repeated + big_nums + filler
                seen = set()
                shared = []
                for n in raw_shared:
                    if n not in seen:
                        seen.add(n)
                        shared.append(n)
                for n in general_source:
                    if len(shared) >= 35:
                        break
                    if n not in seen:
                        seen.add(n)
                        shared.append(n)

                # --- 3) Rank & pick Top15/Two-Sure/Banker ------------------
                freq = Counter()
                for nums in extracted.values():
                    freq.update(nums)
                freq.update(shared)

                top15 = shared[-15:]

                if len(shared) >= 25:
                    two_sure = [shared[22], shared[24]]
                else:
                    two_sure = top15[:2]

                banker = next(n for n,_ in freq.most_common() if n not in two_sure)

                         # 4) Build & save history array, always honest (prediction vs next result)
                history = []
                events = parse_txt_file_events(save_path, start_ev=1)
                if len(events) >= 2:
                    start = max(0, len(events) - 21)
                    for i in range(start, len(events) - 1):
                        ev_no, _, _ = events[i]
                        raw_next_win = events[i + 1][2]
                        if isinstance(raw_next_win, str):
                            next_win = [int(n) for n in re.findall(r'\d+', raw_next_win)]
                        else:
                            next_win = list(raw_next_win)
                        # Use only events[:i+1] to predict, never see the future!
                        h_shared, h_topX = _compute_shared_and_top_for_events(events[:i+1])
                        h_two_sure = h_topX[:2]
                        h_freq = Counter(h_shared)
                        h_banker = next((n for n, _ in h_freq.most_common() if n not in h_two_sure), None)
                        history.append({
                            'event':    ev_no,
                            'shared':   sorted(set(h_shared)   & set(next_win)),
                            'top':      sorted(set(h_topX)     & set(next_win)),
                            'two_sure': sorted(set(h_two_sure) & set(next_win)),
                            'banker':   [h_banker] if h_banker in next_win else []
                        })


                # 5) Cache everything to DB
                cached = CachedPrediction.query.filter_by(filename=filename).first()
                if not cached:
                    cached = CachedPrediction(filename=filename, day_of_week=day_of_week)
                    db.session.add(cached)

                cached.shared_json   = json.dumps(shared)
                cached.topX_json     = json.dumps(top15)
                cached.top2_json     = json.dumps(two_sure)
                cached.banker        = banker
                cached.history_json  = json.dumps(history)
                cached.last_updated  = datetime.now(timezone.utc)
                cached.status        = 'ready'
                db.session.commit()        # 6) Log & broadcast matches for notifications, always honest!
        if len(events) >= 2:
            ev_no, _, _ = events[-2]       # Previous event, prediction up to here
            raw_next_win = events[-1][2]
            if isinstance(raw_next_win, str):
                next_win = [int(n) for n in re.findall(r'\d+', raw_next_win)]
            else:
                next_win = list(raw_next_win)

            honest_shared, honest_topX = _compute_shared_and_top_for_events(events[:-1])
            honest_two_sure = honest_topX[:2]
            honest_freq = Counter(honest_shared)
            honest_banker = next((n for n, _ in honest_freq.most_common() if n not in honest_two_sure), None)
            admin_u = User.query.filter_by(is_admin=True).first()

            # --- Find what matched for each group ---
            matched_shared   = sorted(set(honest_shared)   & set(next_win))
            matched_topX     = sorted(set(honest_topX)     & set(next_win))
            matched_twosure  = sorted(set(honest_two_sure) & set(next_win))
            matched_banker   = [honest_banker] if honest_banker in next_win else []

            # --- Build the message exactly like history ---
            parts = []
            if matched_shared:
                parts.append(f"Shared: {matched_shared} ({len(matched_shared)})")
            if matched_topX:
                parts.append(f"Top15: {matched_topX} ({len(matched_topX)})")
            if matched_twosure:
                parts.append(f"Two-Sure: {matched_twosure} ({len(matched_twosure)})")
            if matched_banker:
                parts.append(f"Banker: {matched_banker} (1)")

            if parts:
                details = "; ".join(parts)
                # --- DEBUG PRINTS ---
                print("DEBUG details being sent in notification:", details, flush=True)
                print("DEBUG matched_shared:", matched_shared, flush=True)
                print("DEBUG matched_topX:", matched_topX, flush=True)
                print("DEBUG matched_twosure:", matched_twosure, flush=True)
                print("DEBUG matched_banker:", matched_banker, flush=True)
                # Only notify if NOT already in MatchLog (to avoid duplicate alerts)
                if not MatchLog.query.filter_by(
                    event_no=str(ev_no), filename=filename, details=details
                ).first():
                    db.session.add(MatchLog(
                        event_no=str(ev_no),
                        filename=filename,
                        details=details
                    ))
                    db.session.commit()
                for run in UserPredict.query.filter_by(filename=filename).all():
                    content = f"?? Congrats! {filename} matched next draw: {details}"
                    print("DEBUG content about to send:", content, flush=True)
                    if not Message.query.filter_by(
                        sender_id=admin_u.id,
                        receiver_id=run.user_id,
                        content=content
                    ).first():
                        send_message(admin_u.id, run.user_id, content)

            msg = f'{len(uploaded)} file(s) processed and cached under {day_of_week}.'

    return render_template_string(ADMIN_PREDICTIONS_TEMPLATE, msg=msg)

@app.route('/admin/adverts', methods=['GET', 'POST'])
@require_login
def admin_adverts():
    if not is_admin():
        abort(403)

    upload_folder = ADS_DIR
    os.makedirs(upload_folder, exist_ok=True)
    msg = ''

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(f.filename.strip() == '' for f in uploaded_files):
            msg = "Please select at least one image or video."
        else:
            allowed_exts = ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg')
            for file in uploaded_files:
                if file and file.filename.lower().endswith(allowed_exts):
                    save_path = os.path.join(upload_folder, file.filename)
                    file.save(save_path)
            msg = "Advert(s) uploaded successfully!"

    # List all existing adverts for preview
    ad_files = get_ad_files()
    for f in os.listdir(upload_folder):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg')):
            ad_files.append(f)

    return render_template_string("""
    <h2 style="text-align:center;">Upload Adverts (Images & Videos)</h2>
    <form method="post" enctype="multipart/form-data" style="text-align:center; margin-bottom:20px;">
        <input type="file" name="files" multiple required>
        <button type="submit">Upload</button>
    </form>
    <p style="text-align:center; color:lime;">{{ msg }}</p>
    <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:20px;">
    {% for f in ad_files %}
        {% if f.lower().endswith(('.mp4', '.webm', '.ogg')) %}
            <video src="{{ url_for('static', filename='images.advirt/' ~ f) }}" 
                   width="200" controls></video>
        {% else %}
            <img src="{{ url_for('static', filename='images.advirt/' ~ f) }}" 
                 width="200" style="border:2px solid #333;">
        {% endif %}
    {% endfor %}
    </div>
    <div style="text-align:center; margin-top:20px;">
        <a href="{{ url_for('admin') }}">? Back to Admin</a>
    </div>
    """, msg=msg, ad_files=ad_files)


@app.route('/', methods=['GET', 'POST']) 
@require_login
def main():
    # --- your context preparation as usual ---
    files = list_txt_files()
    filename = None
    event = None
    results = None
    match_msgs = get_today_matches()
    unread_count = Message.query.filter_by(receiver_id=current_user().id, is_read=False).count()

    if request.method == 'POST':
        filename = request.form['file']
        cached = CachedPrediction.query.filter_by(filename=filename).first()
        if not cached:
            flash("Prediction not available. Please contact admin.", "danger")
            return redirect(url_for('main'))
        event = get_latest_event_number(filename, start_ev=1)
        if not UserPredict.query.filter_by(
                user_id=current_user().id,
                filename=filename,
                event_no=event
        ).first():
            db.session.add(UserPredict(
                user_id=current_user().id,
                filename=filename,
                event_no=event
            ))
            db.session.commit()
        results = {
            'shared':    cached.shared(),
            'topX':      cached.topX(),
            'top2':      cached.top2(),
            'banker':    cached.banker,
            'top_label': f"Top Predictions ({len(cached.topX())})",
            'history':   cached.history(),
            'latest_match': None
        }

        # --- Save Prediction History ---
        try:
            events = parse_txt_file_events(filename, start_ev=1)
            if events:
                _, _, actual_draw = events[-1]
            else:
                actual_draw = []
        except Exception:
            actual_draw = []

        save_prediction_history(
            user_id=current_user().id,
            filename=filename,
            event_no=event,
            shared=results['shared'],
            topX=results['topX'],
            top2=results['top2'],
            banker=results['banker'],
            actual_draw=actual_draw
        )

    # --- Overlay history from REAL prediction records ---
    from sqlalchemy import desc

    if filename:
        last20 = (
            PredictionHistory.query
            .filter_by(filename=filename)
            .order_by(desc(PredictionHistory.timestamp))
            .limit(20)
            .all()
        )

        overlay_history = []
        for rec in last20:
            shared = json.loads(rec.shared) if isinstance(rec.shared, str) else rec.shared
            topX = json.loads(rec.topX) if isinstance(rec.topX, str) else rec.topX
            top2 = json.loads(rec.top2) if isinstance(rec.top2, str) else rec.top2
            actual_draw = json.loads(rec.actual_draw) if isinstance(rec.actual_draw, str) else rec.actual_draw
            overlay_history.append({
                "event":         rec.event_no,
                "actual":        actual_draw or [],
                "shared_pred":   shared or [],
                "top_pred":      topX or [],
                "two_sure_pred": top2 or [],
                "banker_pred":   rec.banker,
                "shared_hits":   sorted(list(set(shared) & set(actual_draw))),
                "top_hits":      sorted(list(set(topX) & set(actual_draw))),
                "two_sure_hits": sorted(list(set(top2) & set(actual_draw))),
                "banker_hit":    rec.banker if rec.banker and rec.banker in (actual_draw or []) else None,
            })

        if results is not None:
            results['history'] = overlay_history

    # --- Set up context dict ---
    context = dict(
        files=files,
        results=results,
        filename=filename,
        event=event,
        credits=[
            "A very big thank you to our sponsors: Mr Kaspa Antonio Afriyie,  Mr Emmanuel Kwame Dua an Engineer and a building contractor at Metcam Gh limited. Mawusi P. Kpegla of Revolution Ventures, Abigail Antwi of Kesty Queens Academy, Mr Noah Adai, Samuel Odame Alema Junior of 'Odame World Films production And  ALEMA FARMS. God bless you all..."
        ],
        match_msgs=match_msgs,
        user=current_user(),
        is_admin=is_admin(),
        unread_count=unread_count
    )

    # Add advert files to context
    import os
    ad_folder = ADS_DIR
    ad_files = [
        f for f in os.listdir(ad_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.ogg'))
    ]
    context['ad_files'] = ad_files

    # ----------- DEVICE DETECTION HERE -------------
    if is_mobile_request():
        return render_template_string(HTML_TEMPLATE_MOBILE, **context)
    else:
        return render_template_string(HTML_TEMPLATE, **context)





@app.route('/history')
@require_login
def history():
    if is_admin():
        records = PredictionHistory.query.order_by(PredictionHistory.timestamp.desc()).limit(100).all()
    else:
        records = PredictionHistory.query.filter_by(user_id=current_user().id).order_by(PredictionHistory.timestamp.desc()).limit(20).all()
    for r in records:
        # Convert JSON to list if necessary
        r.shared_list = json.loads(r.shared) if isinstance(r.shared, str) else r.shared
        r.topX_list = json.loads(r.topX) if isinstance(r.topX, str) else r.topX
        r.two_sure_list = json.loads(r.top2) if isinstance(r.top2, str) else r.top2
        r.actual_draw_list = json.loads(r.actual_draw) if isinstance(r.actual_draw, str) else r.actual_draw

        r.shared_matches = sorted(list(set(r.shared_list) & set(r.actual_draw_list)))
        r.topX_matches = sorted(list(set(r.topX_list) & set(r.actual_draw_list)))
        r.two_sure_matches = sorted(list(set(r.two_sure_list) & set(r.actual_draw_list)))
        if r.banker is not None:
            r.banker_match = r.banker if r.banker in r.actual_draw_list else None
        else:
            r.banker_match = None
    return render_template_string(HISTORY_TEMPLATE, records=records)

 
@app.route('/inbox')
@require_login
def inbox():
    # Mark all unread as read when inbox is opened
    Message.query.filter_by(receiver_id=current_user().id, is_read=False).update({'is_read': True})
    db.session.commit()
    msgs = Message.query.filter_by(receiver_id=current_user().id)\
                        .order_by(Message.timestamp.desc())\
                        .all()
    all_users = User.query.filter_by(is_admin=False).all()
    return render_template_string(
        INBOX_TEMPLATE,
        messages=msgs,
        user=current_user(),
        is_admin=is_admin(),
        all_users=all_users
    )


@app.route('/send_message', methods=['POST'])
@require_login
def send_message_route():
    if not is_admin():
        abort(403)
    to_id   = int(request.form['to_user_id'])
    content = request.form['content'].strip()
    if content:
        send_message(current_user().id, to_id, content)
    return redirect(url_for('inbox'))

@app.route('/online-users')
def online_users_api():
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    users = User.query.filter(User.last_active >= ten_min_ago, User.is_blocked == False).all()
    return {'users': [u.phone for u in users]}

@app.route('/reply_to_admin', methods=['POST'])
@require_login
def send_reply_to_admin():
    if is_admin():
        abort(403)
    admin_user = User.query.filter_by(is_admin=True).first()
    if not admin_user:
        flash("Admin account not found!", "danger")
        return redirect(url_for('inbox'))
    content = request.form['content'].strip()
    if content:
        send_message(current_user().id, admin_user.id, content)
    flash("Message sent to admin.", "success")
    return redirect(url_for('inbox'))



    # Template selection logic
    if is_mobile_request():
        brand = get_mobile_brand()
        template_name = f"mobile_{brand}.html"
        if not os.path.exists(os.path.join('templates', template_name)):
            template_name = "mobile_main.html"
    else:
        template_name = "desktop_main.html"

    return render_template(
        template_name,
        files=files,
        results=results,
        filename=filename,
        event=event,
        credits=CREDITS,
        match_msgs=match_msgs,
        user=current_user(),
        is_admin=is_admin()
    )
@app.route('/notification_api')
@require_login
def notification_api():
    rec = (
        PredictionHistory.query
        .filter_by(user_id=current_user().id)
        .order_by(PredictionHistory.timestamp.desc())
        .first()
    )
    if not rec:
        return jsonify({
            'message': "No prediction history yet.",
            'matched': [],
            'draw': [],
            'time': ""
        })

    shared = json.loads(rec.shared) if isinstance(rec.shared, str) else rec.shared
    topX = json.loads(rec.topX) if isinstance(rec.topX, str) else rec.topX
    top2 = json.loads(rec.top2) if isinstance(rec.top2, str) else rec.top2
    actual = json.loads(rec.actual_draw) if isinstance(rec.actual_draw, str) else rec.actual_draw

    matches = {
        'shared': sorted(set(shared) & set(actual)),
        'topX': sorted(set(topX) & set(actual)),
        'two_sure': sorted(set(top2) & set(actual)),
        'banker': rec.banker if rec.banker and rec.banker in actual else None
    }

    parts = []
    if matches['shared']:
        parts.append(f"Shared: {matches['shared']} ({len(matches['shared'])})")
    if matches['topX']:
        parts.append(f"TopX: {matches['topX']} ({len(matches['topX'])})")
    if matches['two_sure']:
        parts.append(f"Two-Sure: {matches['two_sure']} ({len(matches['two_sure'])})")
    if matches['banker']:
        parts.append(f"Banker: [{matches['banker']}] (1)")

    message = "?? " + "; ".join(parts) if parts else "No match found in your last prediction."

    return jsonify({
        'message': message,
        'matched': matches,
        'draw': actual,
        'time': rec.timestamp.strftime("%Y-%m-%d %H:%M"),
    })


from flask import request, session, Response, url_for

@app.route('/sitemap.xml')
def sitemap():
    pages = []
    # List all the important endpoints you want Google to index
    for rule in app.url_map.iter_rules():
        # Exclude special endpoints (static, etc.)
        if "GET" in rule.methods and not rule.arguments and not rule.endpoint.startswith("static"):
            url = url_for(rule.endpoint, _external=True)
            pages.append(url)
    sitemap_xml = render_template_string(
        '''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            {% for page in pages %}
            <url><loc>{{ page }}</loc></url>
            {% endfor %}
        </urlset>
        ''', pages=pages
    )
    return Response(sitemap_xml, mimetype='application/xml')

if __name__ == '__main__':
    from waitress import serve
    print(" * Running with Waitress server on http://0.0.0.0:5000")
    serve(app, host='0.0.0.0', port=5000)


# Secure cookies behind Cloudflare
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax', PREFERRED_URL_SCHEME='https')


# --- BEGIN PA_REFRESH_PATCH ---
def refresh_predictions():
    # TODO: replace with your actual pipeline (read .txt, build, cache)
    print("refresh_predictions(): placeholder ran")

try:
    import click
    @app.cli.command("refresh_predictions")
    def _cli_refresh_predictions():
        with app.app_context():
            refresh_predictions()
            click.echo("Predictions refreshed.")
except Exception:
    pass
# --- END PA_REFRESH_PATCH ---


### BEGIN_ALEMA_LANDING ###
# Minimal landing + disclaimer interstitial
from markupsafe import Markup

ALEMA_AD_DIR = os.path.join(app.root_path, "static", "images.advirt")

def _list_ads():
    files, videos = [], []
    try:
        for n in sorted(os.listdir(ALEMA_AD_DIR)):
            low = n.lower()
            if low.endswith((".jpg",".jpeg",".png")): files.append(n)
            if low.endswith((".mp4",".webm",".ogg")): videos.append(n)
    except FileNotFoundError:
        pass
    # fallback placeholder if none found
    if not files:
        files = ["facebook.png"] if os.path.exists(os.path.join(app.root_path,"static","facebook.png")) else []
    return files, videos

WELCOME_HTML = r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>Divine Brain Lotto — Welcome</title>
<style>
  html,body{height:100%} body{margin:0;background:#2a1f14;color:#fff;font-family:Georgia,serif;overflow:hidden}
  .wrap{height:100%;display:flex;flex-direction:column}
  .main{flex:1;display:flex;min-height:0}
  .show{flex:2;position:relative;display:flex;justify-content:center;align-items:center;background:#000;overflow:hidden}
  .slide{max-width:100%;max-height:100%;border-radius:20px;box-shadow:0 8px 20px rgba(0,0,0,.7);opacity:0;position:absolute;transition:opacity 1s;object-fit:contain;z-index:1}
  .slide.active{opacity:1;position:relative}
  #video-container{position:absolute;inset:0;display:none;justify-content:center;align-items:center;background:#000;z-index:5}
  #video-container video{max-width:100%;max-height:100%;border-radius:20px;box-shadow:0 8px 20px rgba(0,0,0,.7)}
  .numbers{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:2}
  .number{position:absolute;top:-10%;font-size:26px;font-weight:700;color:gold;opacity:.8;text-shadow:0 0 8px rgba(255,215,0,.85);animation:fall 14s linear forwards,sway 4s ease-in-out infinite}
  @keyframes fall{from{top:-10%}to{top:110%}}
  @keyframes sway{0%{transform:translateX(-20px)}50%{transform:translateX(20px)}100%{transform:translateX(-20px)}}
  .wm{position:absolute;bottom:10px;right:10px;opacity:.9;z-index:3}
  .wm img{width:90px;border-radius:8px}
  .info{flex:1;background:rgba(0,0,0,.72);padding:16px;border-left:3px solid gold;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;min-width:260px}
  .logo img{width:90px;border-radius:12px}
  .info h1{color:gold;margin:6px 0 8px;font-size:1.45em}
  .info p{margin:4px 0;font-size:1em;line-height:1.35}
  .btn{margin-top:14px;padding:10px 16px;background:gold;color:#000;border-radius:10px;font-weight:700;text-decoration:none;transition:background .3s}
  .btn:hover{background:#ffda47}
  .type{border-right:2px solid gold;animation:blink .8s infinite}@keyframes blink{50%{border-color:transparent}}
  .flash{animation:flash .55s ease-in-out 3}@keyframes flash{0%,100%{opacity:1}50%{opacity:0}}
  .bar{height:34px;background:#111;color:#ffd700;border-top:2px solid gold;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;white-space:nowrap;font-size:.95em}
  .track{position:absolute;left:0;right:0}
  .text{display:inline-block;padding-left:100%;animation:marq 45s linear infinite}@keyframes marq{0%{transform:translateX(0)}100%{transform:translateX(-100%)}}
  .hidden{display:none}
  .disc{color:#ffa2a2;text-align:center;padding-inline:8px}
  @media(max-width:768px){.main{flex-direction:column}.show{flex:none;height:64%}.info{flex:none;height:36%;border-left:none;border-top:3px solid gold}}
</style>
</head><body>
<div class="wrap">
  <div class="main">
    <div class="show">
      <div class="numbers" id="numbers"></div>
      {% for f in files %}
        <img src="{{ url_for('static', filename='images.advirt/'+f) }}" class="slide {% if loop.index0==0 %}active{% endif %}"
             data-owner="{{ 'christiana' if f.lower().startswith('cxk') else 'abigail' }}">
      {% endfor %}
      <div id="video-container">
        <video id="video" autoplay muted playsinline controls preload="auto"></video>
      </div>
      <div class="wm"><img src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo"></div>
    </div>
    <div class="info">
      <div class="logo"><img src="{{ url_for('static', filename='db_lotto_hall.png') }}" alt="Logo"></div>
      <h1 id="who">Hi, I am Abigail Antwi</h1>
      <div id="msg">
        <p>Welcome to the <strong>Divine Brain Lottery Forecast Centre</strong>.</p>
        <p><em>Don’t give up. Join the family that cares about your future. Your miracle could be just one prediction away.</em></p>
      </div>
      <div id="cts">
        <p>📞 +233 243 638 607</p>
        <p>📘 Divine Brain Lotto Forecast Centre</p>
        <p>📧 kakra4065@gmail.com</p>
        <p>📍 Madina La Nkwantanang</p>
      </div>
      <a class="btn" href="{{ url_for('disclaimer', next=request.args.get('next','/login')) }}">Enter the App</a>
    </div>
  </div>
  <div class="bar">
    <div class="track"><span class="text" id="credits">
      A very big thank you to our sponsors: Mr Kaspa Antonio Afriyie, Mr Emmanuel Kwame Dua (Engineer, Metcam GH), Mawusi P. Kpegla (Revolution Ventures),
      Abigail Antwi (Kesty Queens Academy), Mr Noah Adai, Samuel Odame Alema Junior (Odame World Films Production) and ALEMA FARMS. God bless you all...
    </span></div>
    <div id="disc" class="disc hidden">⚠️ 18+ only. We don’t encourage gambling — we teach you to gamble safe.</div>
  </div>
</div>
<script>
const slides=[...document.querySelectorAll(".slide")];
const abi=slides.filter(s=>s.dataset.owner==="abigail");
const chr=slides.filter(s=>s.dataset.owner==="christiana");
const who=document.getElementById("who"); const msg=document.getElementById("msg"); const cts=document.getElementById("cts");
let ai=0,ci=0,abiRuns=0;
function act(x){slides.forEach(s=>s.classList.remove("active")); if(x) x.classList.add("active");}
const greet="Welcome, I am Christiana Xoryesuse Kove.";
const concept="Why keep wasting data on loan apps you won’t benefit from? That little amount is enough to start a new life with our lotto app. Subscribe to our weekly packages: 20 GHS for 5 games each day or 100 GHS for all 42 games a week. Winning guaranteed!";
function type(el,t,s=20){return new Promise(r=>{el.innerHTML="";let i=0;const tick=()=>{if(i<t.length){el.innerHTML=t.slice(0,i+1)+'<span class=\"type\"></span>';i++;setTimeout(tick,s);}else{el.innerHTML=t;r();}};tick();});}
const ABI_MS=5500, CHR_HOLD=10000, ABI_BEFORE_CHR=6;

async function showAbi(){ if(!abi.length) return; who.textContent="Hi, I am Abigail Antwi"; cts.style.display="block";
  msg.innerHTML="<p>Welcome to the <strong>Divine Brain Lottery Forecast Centre</strong>.</p><p><em>Don’t give up. Join the family that cares about your future. Your miracle could be just one prediction away.</em></p>";
  act(abi[ai]); ai=(ai+1)%abi.length; abiRuns++; await new Promise(r=>setTimeout(r,ABI_MS)); }

async function showChr(){ if(!chr.length) return; abiRuns=0; act(chr[ci]); ci=(ci+1)%chr.length; who.textContent="Christiana Xoryesuse Kove"; cts.style.display="none";
  await type(msg,greet,18); await new Promise(r=>setTimeout(r,800)); await type(msg,concept,16); await new Promise(r=>setTimeout(r,CHR_HOLD));
  msg.classList.add("flash"); await new Promise(r=>setTimeout(r,1600)); msg.classList.remove("flash"); }

const vwrap=document.getElementById("video-container"); const video=document.getElementById("video");
const vids={{ videos|tojson }};
function tryAutoPlay(v){ v.muted=true; v.playsInline=true; const p=v.play(); if(p&&p.catch){p.catch(()=>{const kick=()=>{v.play().catch(()=>{});document.removeEventListener('click',kick);document.removeEventListener('touchstart',kick);};document.addEventListener('click',kick,{once:true});document.addEventListener('touchstart',kick,{once:true});});}}

async function runVids(){ if(!vids.length) return; vwrap.style.display="flex"; for(const n of vids){ video.src="{{ url_for('static', filename='images.advirt/') }}"+n; tryAutoPlay(video); await new Promise(res=>video.onended=()=>res()); } vwrap.style.display="none"; }

async function start(){ await runVids(); if(!abi.length && chr.length){ while(true){ await showChr(); } }
  while(true){ while(abiRuns<ABI_BEFORE_CHR || !chr.length){ await showAbi(); if(!chr.length && abiRuns>=ABI_BEFORE_CHR) abiRuns=0; } await showChr(); } }
start();

// Falling numbers
const layer=document.getElementById("numbers"); let num=90;
function spawn(){ const d=document.createElement("div"); d.className="number"; d.textContent=num; num=(num>1)?num-1:90;
  d.style.left=(Math.random()*98)+"%"; const sx=10+Math.random()*25, fall=12+Math.random()*10, sway=3+Math.random()*3;
  d.style.setProperty("animation","fall "+fall+"s linear forwards, sway "+sway+"s ease-in-out infinite");
  d.style.fontSize=(20+Math.random()*16)+"px"; d.style.opacity=(0.55+Math.random()*0.35).toFixed(2);
  layer.appendChild(d); if(layer.childElementCount>120) layer.removeChild(layer.firstElementChild); setTimeout(()=>d.remove(),(fall+0.2)*1000); }
setInterval(spawn,280);

// Credits ↔ disclaimer toggle
const credits=document.getElementById("credits"),disc=document.getElementById("disc");
credits.addEventListener("animationiteration",()=>{credits.classList.add("hidden");disc.classList.remove("hidden");setTimeout(()=>{disc.classList.add("hidden");credits.classList.remove("hidden");},12000);});
</script>
</body></html>
"""

DISCLAIMER_HTML = r'''<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>Disclaimer & Responsible Use — Divine Brain Lotto</title>
<style>
  body{margin:0;background:#0b1a33;color:#fff;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;padding:16px}
  .card{max-width:960px;background:#0f203f;border:1px solid #1f3f7a;border-radius:18px;box-shadow:0 10px 30px rgba(0,0,0,.45);padding:28px 26px}
  h1{margin:0 0 12px;color:#ffda47;font-size:1.6rem}
  h2{margin:18px 0 8px;font-size:1.1rem;color:#ffd768}
  p{line-height:1.55;margin:8px 0}
  .dim{color:#d0d7e1}
  form{margin-top:18px;display:flex;gap:12px;flex-wrap:wrap}
  .btn{background:#ffda47;color:#111;border:none;border-radius:10px;padding:10px 16px;font-weight:700;cursor:pointer}
  .btn:hover{background:#ffd12c}
  .link{color:#9dd1ff;text-decoration:none}
</style>
</head><body>
<div class="card">
  <h1>Disclaimer & Responsible Use</h1>

  <p class="dim"><strong>Divine Brain Lottery Forecast Centre (“DBLFC”)</strong> provides lottery number analyses and predictions generated by a proprietary framework that combines <strong>57 mathematical techniques</strong>. Our system publishes predictions for up to <strong>45 licensed Ghana lottery games</strong> each week and presents historical “match” evidence within the app’s History panel and in selected circled matches shown in promotional/ads images. We also share live demonstration videos that walk through how predictions are produced and how historical matches are evaluated.</p>

  <h2>Important limitations and definitions</h2>
  <p><strong>No guarantee of outcomes.</strong> Lottery results are uncertain by design. While our methods are advanced, no system can guarantee future results. Past patterns and historical “matches” do not predict future outcomes.</p>

  <p><strong>What “match” means.</strong> Any references to “matches” (e.g., “minimum 37 to 42 matches” or higher) refer to how the app defines and highlights overlaps between our published predictions and official draw results. See the Methodology section inside the app for the exact definition of a “match,” the scope of games covered, the time periods measured, and the rules used to count and display those matches.</p>

  <p><strong>Where to verify.</strong> You can verify historical performance inside your logged-in History panel and by reviewing circled matched predictions in the ads images. Our live videos further demonstrate how we generate and evaluate both historical and forward-looking predictions.</p>

  <p><strong>Scope may vary.</strong> Coverage of “up to 45 games per week” reflects current availability and may change with operator schedules, data access, or maintenance.</p>

  <p><strong>Independence.</strong> DBLFC is independent and not affiliated with, endorsed by, or sponsored by any lottery operator or regulator in Ghana or elsewhere. All operator names and draw machines referenced remain the property of their respective owners.</p>

  <h2>Responsible use</h2>
  <p>Our content is provided for informational and entertainment purposes and is not financial advice.</p>
  <p>You are solely responsible for any actions you take and for complying with the laws and age restrictions where you live. Service is for <strong>18+</strong> (or the legal age in your jurisdiction).</p>
  <p>Play responsibly. Never stake more than you can afford to lose. If gambling stops being fun, please seek help.</p>

  <h2>Acceptance of terms</h2>
  <p>By using this website/app, you agree to our Terms of Service and Privacy Policy, including the limitations above. For full technical details about our methodology—covering data sources, cleaning, “match” definitions, evaluation windows, and known limitations—please refer to the Methodology section inside the app.</p>

  <form method="post">
    <input type="hidden" name="next" value="{{ next_url }}">
    <button class="btn" type="submit">I Agree — Continue</button>
    <a class="link" href="{{ url_for('welcome') }}">Back</a>
  </form>
</div>
</body></html>
'''

# Interstitial gate: require disclaimer before main areas
PROTECTED_PREFIXES = ("/login", "/desktop", "/mobile", "/main", "/")
EXEMPT_PREFIXES = ("/welcome", "/disclaimer", "/static", "/me/ping")

@app.before_request
def _disclaimer_gate():
    p = request.path or "/"
    if any(p.startswith(x) for x in EXEMPT_PREFIXES):
        return
    if any(p.startswith(x) for x in PROTECTED_PREFIXES) and not session.get("disclaimer_ok"):
        nxt = request.full_path if request.query_string else p
        return redirect(url_for("disclaimer", next=nxt))

@app.route("/welcome")
def welcome():
    files, videos = _list_ads()
    return render_template_string(WELCOME_HTML, files=files, videos=videos)

@app.route("/disclaimer", methods=["GET","POST"])
def disclaimer():
    next_url = request.args.get("next") or request.form.get("next") or "/login"
    if request.method == "POST":
        session["disclaimer_ok"] = True
        return redirect(next_url)
    return render_template_string(DISCLAIMER_HTML, next_url=next_url)

# Make "/" go to welcome if nothing else already bound there
try:
    app.add_url_rule("/", "root_welcome_redirect", lambda: redirect(url_for("welcome")))
except Exception:
    pass
### END_ALEMA_LANDING ###

# --- BEGIN_ALEMA2_MOUNT ---
# (Exact Abii behavior mounted under /alema2, serving files only from /static/alema2)
import os
from flask import render_template, send_from_directory

ALEMA2_DIR = os.path.join(app.root_path, 'static', 'alema2')

@app.route('/alema2')
def _alema2_index():
    # EXACT behavior: list images & videos from the working dir (here: isolated ALEMA2_DIR)
    allnames = []
    try:
        allnames = sorted(os.listdir(ALEMA2_DIR))
    except FileNotFoundError:
        pass

    files  = [f for f in allnames if f.lower().endswith(('.jpg','.jpeg','.png'))]
    videos = [f for f in allnames if f.lower().endswith(('.mp4','.webm','.ogg'))]

    # Your original template HTML will be uploaded into templates/alema2.html verbatim
    # (Windows sync script extracts it from "alema 2.py" and pushes here).
    return render_template('alema2.html', files=files, videos=videos)

# Keep route name EXACTLY as original for media fetching
@app.route('/images/<path:filename>')
def images(filename):
    # Serve ONLY from ALEMA2_DIR (isolated from main app)
    return send_from_directory(ALEMA2_DIR, filename)
# --- END_ALEMA2_MOUNT ---

# --- DEMO route to push sample data to PA ---
@app.route('/admin/push_demo', methods=['GET'])
def _push_demo():
    games = {
        "National": {"numbers": [12,24,36], "message": "demo-push"},
        "Monday Special": {"numbers": [14,28,33], "message": "demo-push"}
    }
    ok = push_games_to_live(games, source="push_demo")
    return jsonify({"status": "ok" if ok else "error", "pushed": ok, "games": list(games.keys())})
# --- /DEMO route ---

