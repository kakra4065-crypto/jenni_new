# replay_admin_upload.py
import os, sys
from pathlib import Path

# import your PA app
sys.path.insert(0, os.path.expanduser('~/jenni_new'))
from app import app

# allow test client posts (skips CSRF if your app uses it)
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

c = app.test_client()
src = Path(os.path.expanduser('~/jenni_new/admin_uploaded_txt'))

updated, failed = 0, []

for fp in sorted(src.glob('*.txt')):
    # Pretend admin session (adjust keys if your app uses different ones)
    with c.session_transaction() as s:
        s['is_admin'] = True
        s['admin']    = True
        s['user_id']  = 1

    with fp.open('rb') as f:
        rv = c.post(
            '/admin/predictions',
            data={'file': (f, fp.name)},
            content_type='multipart/form-data',
            follow_redirects=True
        )
    if rv.status_code in (200, 302):
        updated += 1
    else:
        failed.append((fp.name, rv.status_code))

print("UPDATED=%s FAILED=%s" % (updated, failed))
