# ========= EDIT THESE =========
$Local       = "$env:USERPROFILE\Desktop\jenni_new"     # your local project folder
$User        = "kakra4065"
$Host        = "ssh.pythonanywhere.com"
$RemoteRoot  = "/home/$User/jenni_new"
$Venv        = "/home/$User/myvenv"
$Domain      = "www.divinebrainlotteryforecastcentre.org"
# =============================

$Staging = Join-Path $env:TEMP "jenni_stage"
$Zip     = Join-Path $env:TEMP "jenni_upload.zip"

# --- prep staging (clean mirror of Local minus junk) ---
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging | Out-Null

# Mirror while excluding heavyweight/unwanted stuff
# /MIR = mirror; /XD exclude dirs; /XF exclude files
$rc = robocopy $Local $Staging /MIR `
  /XD "venv" ".venv" "__pycache__" "instance" `
  /XF "*.pyc" "*.pyo" "*.zip" "*.7z" "*.mp4" ".env" "lotto_users.db"
if ($LASTEXITCODE -ge 8) { throw "Robocopy failed with code $LASTEXITCODE" }

# Zip the staged copy
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "$Staging\*" -DestinationPath $Zip -Force

# Upload to PythonAnywhere (requires Windows OpenSSH: ssh/scp)
scp $Zip "$User@$Host:~/"

# Build a remote script to unpack, patch, install, migrate, reload
$ZipName = Split-Path $Zip -Leaf
$RemoteScript = @"
set -e
ROOT="$RemoteRoot"
VENV="$Venv"

# 1) Unpack without deleting your server DB/instance
TMP="\$HOME/deploy_tmp_\$(date +%s)"
mkdir -p "\$TMP"
unzip -q "~/$ZipName" -d "\$TMP"
rm -f "~/$ZipName"
mkdir -p "\$ROOT" "\$ROOT/instance" "\$ROOT/static/images.advirt"
cp -a "\$TMP/." "\$ROOT/"
rm -rf "\$TMP"

# 2) Patch app.py for Python 3.10 + stable paths (idempotent)
python3.10 - <<'PY'
import os, re
p = "$RemoteRoot/app.py"
if not os.path.exists(p):
    raise SystemExit("app.py not found at " + p)
s = open(p, encoding="utf-8", errors="ignore").read()
orig = s

# UTC import -> timezone / utcnow()
s = s.replace("from datetime import datetime, timedelta, UTC",
              "from datetime import datetime, timedelta, timezone")
s = re.sub(r"datetime\.now\(\s*UTC\s*\)", "datetime.utcnow()", s)

# force working dir to project root
if "os.chdir(os.path.dirname(__file__))" not in s:
    s = s.replace("app = Flask(__name__)",
                  "app = Flask(__name__)\nimport os\ntry:\n    os.chdir(os.path.dirname(__file__))\nexcept Exception:\n    pass", 1)

# robust absolute ads dir + helper once
if "ADS_DIR = os.path.join(app.static_folder, 'images.advirt')" not in s:
    anchor = "app = Flask(__name__)"
    helper = """
# --- Robust absolute ads dir (prevents FileNotFoundError) ---
ADS_DIR = os.path.join(app.static_folder, 'images.advirt')
os.makedirs(ADS_DIR, exist_ok=True)
def list_ad_images():
    try:
        names = os.listdir(ADS_DIR)
    except FileNotFoundError:
        names = []
    return [f"static/images.advirt/{n}" for n in names
            if n.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp'))]
"""
    s = s.replace(anchor, anchor + "\n" + helper, 1)

# rewrite common references to use ADS_DIR
s = re.sub(r"os\.listdir\(\s*['\"]static/images\.advirt['\"]\s*\)", "os.listdir(ADS_DIR)", s)
s = re.sub(r"os\.path\.join\(\s*['\"]static['\"]\s*,\s*['\"]images\.advirt['\"]\s*\)", "ADS_DIR", s)
s = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]static/images\.advirt['\"]", r"\1 = ADS_DIR", s)

if s != orig:
    open(p, "w", encoding="utf-8").write(s)
    print("Patched app.py")
else:
    print("app.py already good")
PY

# 3) Ensure ads folder has at least one small image
cp -n "$RemoteRoot/static/facebook.png"  "$RemoteRoot/static/images.advirt/placeholder1.png" 2>/dev/null || true
cp -n "$RemoteRoot/static/whatsapp.png" "$RemoteRoot/static/images.advirt/placeholder2.png" 2>/dev/null || true

# 4) Install requirements (disk-friendly)
if [ -d "$VENV" ] && [ -f "$RemoteRoot/requirements.txt" ]; then
  source "$VENV/bin/activate"
  pip install --no-cache-dir -r "$RemoteRoot/requirements.txt" || true
  deactivate
  rm -rf ~/.cache/pip || true
fi

# 5) Create tables (safe to run repeatedly)
source "$VENV/bin/activate" || true
python3.10 - <<'PY' || true
import sys; sys.path.insert(0, "$RemoteRoot")
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print("DB ready")
except Exception as e:
    print("DB init skipped:", e)
PY
deactivate || true

# 6) Reload the web app
/usr/local/bin/pa_reload_webapps || true

# 7) Quick smoke test from server side
curl -sI -L https://$Domain/login | head -n 1
"@

ssh "$User@$Host" $RemoteScript

Write-Host "`n✅ Deploy complete. Visit: https://$Domain"
