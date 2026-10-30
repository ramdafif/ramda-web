import io
import json
from argon2 import PasswordHasher
from PIL import Image
from ramda.models import db, AdminUser, ContentItem, MediaAsset, AuditLog


def login(app, client):
    with app.app_context():
        db.session.add(AdminUser(email='admin@example.test', password_hash=PasswordHasher().hash('a-long-test-password')))
        db.session.commit()
    return client.post('/admin/login', data={'email': 'admin@example.test', 'password': 'a-long-test-password'})


def test_auth_and_noindex(app, client):
    assert client.get('/admin/').status_code == 302
    assert login(app, client).status_code == 302
    response = client.get('/admin/')
    assert response.status_code == 200
    assert response.headers['X-Robots-Tag'] == 'noindex, nofollow'
    assert 'Set-Cookie' not in response.headers or 'HttpOnly' in response.headers['Set-Cookie']


def test_login_lockout(client):
    for _ in range(8):
        assert client.post('/admin/login', data={'email': 'x@example.test', 'password': 'wrong'}).status_code == 401
    assert client.post('/admin/login', data={'email': 'x@example.test', 'password': 'wrong'}).status_code == 429


def test_every_content_editor_renders(app, client):
    login(app, client)
    with app.app_context():
        rows = [(r.kind, r.id) for r in db.session.scalars(db.select(ContentItem))]
    for kind, item_id in rows:
        assert client.get(f'/admin/content/{kind}/{item_id}/edit').status_code == 200
    for route in ['/admin/media', '/admin/leads', '/admin/backup', '/admin/settings', '/admin/security', '/admin/audit']:
        assert client.get(route).status_code == 200


def test_edit_publish_public_update(app, client):
    login(app, client)
    with app.app_context():
        hero = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == 'hero'))
        payload = dict(hero.data)
        payload['headline'] = {'id': 'Published from admin', 'en': ''}
        item_id = hero.id
    assert client.post(f'/admin/content/hero/{item_id}/edit', data={'slug': 'main', 'content_json': json.dumps(payload), 'published': 'on', 'verified': 'on'}).status_code == 302
    assert client.get('/api/public/home').json['hero']['headline']['id'] != 'Published from admin'
    assert client.post('/admin/publish').status_code == 302
    assert client.get('/api/public/home').json['hero']['headline']['id'] == 'Published from admin'
    with app.app_context():
        assert db.session.scalar(db.select(AuditLog).where(AuditLog.action == 'publish'))


def test_reorder_rejects_partial_and_persists(app, client):
    login(app, client)
    with app.app_context():
        ids = list(db.session.scalars(db.select(ContentItem.id).where(ContentItem.kind == 'section').order_by(ContentItem.sort_order)))
    assert client.post('/admin/content/section/reorder', json={'ids': ids[:1]}).status_code == 400
    assert client.post('/admin/content/section/reorder', json={'ids': list(reversed(ids))}).status_code == 200
    client.post('/admin/publish')
    sections = client.get('/api/public/home').json['sections']
    assert sections[0]['key'] == 'footer'


def test_magic_bytes_and_alt_required(app, client):
    login(app, client)
    response = client.post('/admin/media', data={'alt': 'fake', 'file': (io.BytesIO(b'not-an-image'), 'x.png')})
    assert b'Invalid image' in response.data
    with app.app_context():
        assert db.session.query(MediaAsset).count() == 0


def test_media_pipeline_and_exif(app, client):
    login(app, client)
    buffer = io.BytesIO()
    Image.new('RGB', (600, 300), 'red').save(buffer, 'JPEG', exif=Image.Exif())
    buffer.seek(0)
    assert client.post('/admin/media', data={'alt': 'Gambar uji', 'file': (buffer, 'x.jpg')}).status_code == 302
    with app.app_context():
        asset = db.session.scalar(db.select(MediaAsset))
        assert asset.width == 600
        assert len(asset.variants) == 4
        assert {v['format'] for v in asset.variants} == {'webp', 'avif'}
        for variant in asset.variants:
            with Image.open(app.config['UPLOAD_DIR'] + '/' + variant['src'].split('/')[-1]) as image:
                assert not image.getexif()


def test_svg_sanitization():
    from ramda.services.media import sanitize_svg
    data, width, height = sanitize_svg(b'<svg width="20" height="20" onload="alert(1)"><script>alert(1)</script><image href="https://evil.test/x"/><path d="M0 0" fill="red"/></svg>')
    assert b'script' not in data and b'onload' not in data and b'href' not in data
    assert (width, height) == (20, 20)


def test_import_is_atomic_and_does_not_publish(app, client):
    login(app, client)
    with app.app_context():
        before = db.session.query(ContentItem).count()
    backup = {'version': 1, 'items': [{'kind': 'service', 'slug': 'valid-new', 'data': {'title': {'id': 'Test'}, 'description': {'id': 'Test'}}}, {'kind': 'service', 'slug': 'invalid', 'data': {'unknown': True}}]}
    client.post('/admin/backup/import', data={'file': (io.BytesIO(json.dumps(backup).encode()), 'backup.json')})
    with app.app_context():
        assert db.session.query(ContentItem).count() == before


def test_csrf_on_login_and_mutations(app):
    app.config['WTF_CSRF_ENABLED'] = True
    client = app.test_client()
    assert client.post('/admin/login', data={'email': 'x', 'password': 'x'}).status_code == 400
    assert client.post('/admin/publish').status_code == 400


def test_verification_is_not_public_before_publish(app, client):
    login(app, client)
    with app.app_context():
        stat = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == 'stat'))
        stat.data = {**stat.data, 'visible': True}
        stat.public_data = dict(stat.data)
        stat.public_visible = True
        stat.is_placeholder = False
        stat.public_is_placeholder = True
        db.session.commit()
    assert client.get('/api/public/home').json['stats'] == []
    client.post('/admin/publish')
    assert len(client.get('/api/public/home').json['stats']) == 1


def test_delete_published_content_requires_publish_boundary(app, client):
    login(app, client)
    with app.app_context():
        row = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == 'project'))
        row_id, slug = row.id, row.slug
    path = f'/admin/content/project/{row_id}/delete'
    client.post(path)
    assert client.get(f'/api/public/projects/{slug}').status_code == 200
    client.post('/admin/publish')
    assert client.get(f'/api/public/projects/{slug}').status_code == 404
    client.post(path)
    with app.app_context():
        assert db.session.get(ContentItem, row_id) is None
