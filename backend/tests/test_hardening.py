import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
import pyotp
from cryptography.fernet import Fernet
from ramda.models import db, AdminUser, Lead, AiBudget
from ramda.services.security import take_rate
from ramda.services.ai import reserve
from test_admin import login


def test_public_payload_size_bound(client):
    response = client.post('/api/public/contact', data=json.dumps({'message': 'x'*70000}), content_type='application/json', headers={'Origin':'http://localhost:4321'})
    assert response.status_code == 413


def test_totp_encrypted_and_replay_rejected(app, client):
    app.config['TOTP_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    login(app, client)
    assert client.get('/admin/security').status_code == 200
    with client.session_transaction() as session:
        secret = session['pending_totp']
    code = pyotp.TOTP(secret).now()
    assert client.post('/admin/security', data={'action':'enable-totp','password':'a-long-test-password','code':code}).status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(AdminUser))
        assert secret not in user.totp_secret_encrypted
        # Simulate setup in the preceding time step without a blocking sleep.
        user.totp_last_counter = int(time.time())//30 - 1
        db.session.commit()
    client.post('/admin/logout')
    assert client.post('/admin/login', data={'email':'admin@example.test','password':'a-long-test-password','totp':'000000'}).status_code == 401
    assert client.post('/admin/login', data={'email':'admin@example.test','password':'a-long-test-password','totp':code}).status_code == 302
    client.post('/admin/logout')
    assert client.post('/admin/login', data={'email':'admin@example.test','password':'a-long-test-password','totp':code}).status_code == 401


def test_csv_formula_escape_and_portable_backup_excludes_leads(app, client):
    login(app, client)
    with app.app_context():
        db.session.add(Lead(name='=1+1', contact='+62812345678', project_type='Test', budget_range='Test', message='Private lead message'))
        db.session.commit()
    response = client.get('/admin/leads/export.csv')
    assert "'=1+1" in response.data.decode('utf-8-sig')
    assert "'+62812345678" in response.data.decode('utf-8-sig')
    backup = json.loads(client.get('/admin/backup/content.json').data)
    assert len(backup['items']) == 47
    assert 'Private lead message' not in json.dumps(backup)
    assert 'password_hash' not in json.dumps(backup)


def test_zip_restore_rejects_traversal_before_writing(app, client):
    login(app, client)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.writestr('../outside.svg','<svg width="1" height="1"/>')
    buffer.seek(0)
    result=client.post('/admin/backup/uploads-import',data={'file':(buffer,'uploads.zip')},follow_redirects=True)
    assert 'Uploads ZIP tidak valid' in result.data.decode()
    from pathlib import Path
    assert not list(Path(app.config['UPLOAD_DIR']).iterdir())


def test_rate_counter_atomic_across_threads(app):
    def take(_):
        with app.app_context():
            return take_rate('thread-test','same-ip',5,3600)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(take,range(16))) == 5


def test_budget_reservation_atomic_across_threads(app):
    with app.app_context():
        db.session.add(AiBudget(day='2099-01-01',spent_micros=0))
        db.session.commit()
    def take(_):
        with app.app_context():
            accepted=reserve('2099-01-01',200,1000)
            db.session.commit()
            return accepted
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(take,range(16))) == 5
    with app.app_context():
        assert db.session.get(AiBudget,'2099-01-01').spent_micros == 1000
