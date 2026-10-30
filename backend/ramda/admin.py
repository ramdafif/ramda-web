import csv
import io
import json
import re
import tempfile
import time
import zipfile
from datetime import timedelta
from pathlib import Path
import httpx
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from cryptography.fernet import Fernet
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from .content import validate_content, preview_serializer, render_md
from .models import db, AdminUser, AuditLog, ContentItem, Lead, MediaAsset, Publication, AiUsage, now
from .schemas import SCHEMAS, SINGLETONS
from .services.security import take_rate, ip_hash
from .services.media import store_media

admin = Blueprint('admin', __name__, url_prefix='/admin')
passwords = PasswordHasher()
DUMMY_HASH = passwords.hash('unused-dummy-password-for-timing-only')
LABELS = {'settings': 'Pengaturan Situs', 'section': 'Section Beranda', 'hero': 'Hero', 'stat': 'Statistik', 'project': 'Proyek', 'service': 'Layanan', 'package': 'Paket Harga', 'process': 'Proses Kerja', 'tech': 'Tech Stack', 'about': 'Tentang', 'testimonial': 'Testimoni', 'article': 'Artikel', 'faq': 'FAQ', 'ai_config': 'Pengaturan AI', 'knowledge': 'Pengetahuan AI'}


def audit(action, target):
    db.session.add(AuditLog(user_id=current_user.id if current_user.is_authenticated else None, action=action, target=str(target)[:200]))


def ensure_kind(kind):
    if kind not in SCHEMAS:
        abort(404)


@admin.context_processor
def context():
    count = db.session.scalar(db.select(db.func.count()).select_from(ContentItem).where(ContentItem.is_placeholder.is_(True))) if current_user.is_authenticated else 0
    return {'entity_labels': LABELS, 'placeholder_count': count}


@admin.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()[:254]
        import hashlib
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        ip_ok = take_rate('login-ip', ip_hash(), 15, 900)
        account_ok = take_rate('login-account', email_hash, 8, 900)
        if not ip_ok or not account_ok:
            return render_template('admin/login.html', error='Terlalu banyak percobaan. Coba lagi dalam 15 menit.'), 429
        user = db.session.scalar(db.select(AdminUser).where(AdminUser.email == email))
        valid = False
        try:
            valid = passwords.verify(user.password_hash if user else DUMMY_HASH, request.form.get('password', '')[:1000])
        except (VerificationError, InvalidHashError):
            pass
        if valid and user and user.active:
            if user.totp_secret_encrypted:
                try:
                    secret = Fernet(current_app.config['TOTP_ENCRYPTION_KEY'].encode()).decrypt(user.totp_secret_encrypted.encode()).decode()
                    counter = int(time.time()) // 30
                    token = request.form.get('totp', '')
                    if counter <= user.totp_last_counter or not pyotp.TOTP(secret).verify(token):
                        return render_template('admin/login.html', error='Email, kata sandi, atau kode autentikator tidak valid.'), 401
                    used = db.session.execute(db.update(AdminUser).where(AdminUser.id == user.id, AdminUser.totp_last_counter < counter).values(totp_last_counter=counter))
                    if not used.rowcount:
                        db.session.rollback()
                        return render_template('admin/login.html', error='Kode autentikator sudah digunakan.'), 401
                except Exception:
                    return render_template('admin/login.html', error='Verifikasi autentikator tidak tersedia.'), 401
            session.clear()
            login_user(user, remember=False)
            session.permanent = True
            audit('login', user.email)
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        audit('login_failed', email_hash)
        db.session.commit()
        return render_template('admin/login.html', error='Email, kata sandi, atau kode autentikator tidak valid.'), 401
    return render_template('admin/login.html')


@admin.post('/logout')
@login_required
def logout_view():
    audit('logout', current_user.id)
    db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('admin.login_view'))


@admin.get('/')
@login_required
def dashboard():
    since = now() - timedelta(days=7)
    usage = db.session.execute(db.select(db.func.count(AiUsage.id), db.func.coalesce(db.func.sum(AiUsage.estimated_cost_micros), 0), db.func.coalesce(db.func.sum(AiUsage.input_tokens + AiUsage.output_tokens), 0)).where(AiUsage.created_at >= since)).one()
    counts = {'leads': db.session.scalar(db.select(db.func.count()).select_from(Lead).where(Lead.status == 'new')), 'drafts': db.session.scalar(db.select(db.func.count()).select_from(ContentItem).where(ContentItem.published.is_(False))), 'usage': usage[0], 'cost': f'{usage[1]/1_000_000:.4f}', 'tokens': usage[2]}
    return render_template('admin/dashboard.html', counts=counts)


@admin.get('/content/<kind>')
@login_required
def content_list(kind):
    ensure_kind(kind)
    query = db.select(ContentItem).where(ContentItem.kind == kind)
    if search := request.args.get('q', '').strip()[:100]:
        # Search serialized data in Python to keep SQLite and MySQL behavior identical.
        rows = [row for row in db.session.scalars(query.order_by(ContentItem.sort_order, ContentItem.id)) if search.casefold() in json.dumps(row.data, ensure_ascii=False).casefold() or search.casefold() in row.slug.casefold()]
    else:
        rows = list(db.session.scalars(query.order_by(ContentItem.sort_order, ContentItem.id)))
    state = request.args.get('state', '')
    if state:
        rows = [r for r in rows if (r.is_placeholder if state == 'placeholder' else r.published if state == 'published' else not r.published)]
    return render_template('admin/list.html', kind=kind, rows=rows, singleton=kind in SINGLETONS)


def editor_fields(kind, data):
    schema = SCHEMAS[kind].model_json_schema()
    fields = []
    for name, spec in schema['properties'].items():
        resolved = schema.get('$defs', {}).get(spec.get('$ref', '').split('/')[-1], spec)
        field_type = 'localized' if spec.get('$ref', '').endswith('/Localized') else resolved.get('type', 'object')
        fields.append({'name': name, 'label': name.replace('_', ' ').title(), 'type': field_type, 'spec': resolved, 'value': data.get(name, spec.get('default', None))})
    return fields, schema


@admin.route('/content/<kind>/new', methods=['GET', 'POST'])
@admin.route('/content/<kind>/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def content_edit(kind, item_id=None):
    ensure_kind(kind)
    item = db.get_or_404(ContentItem, item_id) if item_id else None
    if item and item.kind != kind:
        abort(404)
    if not item and kind in SINGLETONS and db.session.scalar(db.select(ContentItem).where(ContentItem.kind == kind)):
        abort(409)
    data = dict(item.data) if item else {}
    error = ''
    if request.method == 'POST':
        try:
            data = json.loads(request.form['content_json']) if 'content_json' in request.form else data
            if not isinstance(data, dict):
                raise ValueError('Content must be an object')
            # The no-JS form and the enhanced editor share the same validation boundary.
            if 'content_json' not in request.form:
                for field in editor_fields(kind, data)[0]:
                    name, field_type = field['name'], field['type']
                    if field_type == 'localized':
                        data[name] = {'id': request.form.get(f'{name}.id', ''), 'en': request.form.get(f'{name}.en', '')}
                    elif field_type == 'boolean':
                        data[name] = request.form.get(name) == 'on'
                    elif field_type in {'array', 'object'}:
                        data[name] = json.loads(request.form.get(name) or ('[]' if field_type == 'array' else '{}'))
                    elif field_type in {'integer', 'number'}:
                        data[name] = float(request.form.get(name) or 0) if field_type == 'number' else int(request.form.get(name) or 0)
                    else:
                        data[name] = request.form.get(name, '')
            data = validate_content(kind, data)
            slug = request.form.get('slug', '').strip()
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,159}', slug):
                raise ValueError('Slug: huruf kecil, angka, dan tanda - saja')
            if item is None:
                item = ContentItem(kind=kind, slug=slug)
                db.session.add(item)
            # Slugs are stable after publication to prevent drafts changing public routes.
            if item.public_data and item.slug != slug:
                raise ValueError('Slug yang sudah terbit tidak dapat diubah. Buat entri baru.')
            item.slug = slug
            item.data = data
            item.published = request.form.get('published') == 'on'
            item.is_placeholder = request.form.get('verified') != 'on'
            item.sort_order = int(request.form.get('sort_order', '0'))
            audit('content_save', f'{kind}:{slug}')
            db.session.commit()
            flash('Draf disimpan. Klik Publish agar perubahan tampil di situs.', 'success')
            return redirect(url_for('admin.content_edit', kind=kind, item_id=item.id))
        except (ValueError, KeyError, IntegrityError) as exc:
            db.session.rollback()
            error = str(exc)[:1500] if not isinstance(exc, IntegrityError) else 'Slug sudah digunakan.'
    fields, schema = editor_fields(kind, data)
    return render_template('admin/edit.html', kind=kind, item=item, data=data, fields=fields, schema=schema, error=error)


@admin.post('/content/<kind>/<int:item_id>/delete')
@login_required
def content_delete(kind, item_id):
    ensure_kind(kind)
    item = db.get_or_404(ContentItem, item_id)
    if item.kind != kind or kind in SINGLETONS:
        abort(400)
    if item.public_visible:
        # Published routes remain intact until the explicit Publish action.
        item.published = False
        audit('content_unpublish', f'{kind}:{item.slug}')
        flash('Entri dijadwalkan untuk ditarik saat Publish. Setelah itu, hapus dari draf jika tidak diperlukan.', 'success')
    else:
        audit('content_delete', f'{kind}:{item.slug}')
        db.session.delete(item)
        flash('Draf dihapus.', 'success')
    db.session.commit()
    return redirect(url_for('admin.content_list', kind=kind))


@admin.post('/content/<kind>/reorder')
@login_required
def reorder(kind):
    ensure_kind(kind)
    ids = request.get_json().get('ids', []) if request.is_json else request.form.getlist('ids', type=int)
    rows = list(db.session.scalars(db.select(ContentItem).where(ContentItem.kind == kind)))
    if len(ids) != len(rows) or set(ids) != {r.id for r in rows}:
        abort(400)
    order = {value: i for i, value in enumerate(ids)}
    for row in rows:
        row.sort_order = order[row.id]
    audit('reorder', kind)
    db.session.commit()
    return {'ok': True}


@admin.post('/publish')
@login_required
def publish():
    try:
        for item in db.session.scalars(db.select(ContentItem)):
            validate_content(item.kind, item.data)
            item.public_data = dict(item.data)
            item.public_visible = item.published
            item.public_is_placeholder = item.is_placeholder
            item.public_order = item.sort_order
    except ValueError:
        db.session.rollback()
        flash('Publish dibatalkan. Periksa validasi konten dan allowlist model AI.', 'error')
        return redirect(url_for('admin.dashboard'))
    db.session.add(Publication())
    audit('publish', 'all-content')
    db.session.commit()
    refreshed = False
    secret = current_app.config['REVALIDATE_SECRET']
    if len(secret) >= 32:
        try:
            response = httpx.post(current_app.config['REVALIDATE_URL'], headers={'Authorization': f'Bearer {secret}'}, timeout=2)
            refreshed = response.is_success
        except httpx.HTTPError:
            pass
    flash('Konten dipublikasikan.' if refreshed else 'Konten dipublikasikan. Cache otomatis berganti dalam beberapa detik.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.post('/preview')
@login_required
def preview():
    token = preview_serializer().dumps({'scope': 'drafts'})
    audit('preview', 'home')
    db.session.commit()
    return redirect(f"{current_app.config['SITE_URL']}/?preview={token}")


@admin.post('/markdown-preview')
@login_required
def markdown_preview():
    return {'html': render_md(request.get_json().get('text', '')[:100000])}


@admin.route('/media', methods=['GET', 'POST'])
@login_required
def media():
    error = ''
    if request.method == 'POST':
        try:
            asset = store_media(request.files['file'], request.form.get('alt', '').strip())
            audit('media_upload', asset.filename)
            db.session.commit()
            flash('Media diunggah dan dioptimasi.', 'success')
            return redirect(url_for('admin.media'))
        except (ValueError, KeyError) as exc:
            db.session.rollback()
            error = str(exc)
    assets = list(db.session.scalars(db.select(MediaAsset).order_by(MediaAsset.id.desc())))
    return render_template('admin/media.html', assets=assets, error=error)


@admin.post('/media/<int:asset_id>')
@login_required
def media_update(asset_id):
    asset = db.get_or_404(MediaAsset, asset_id)
    alt = request.form.get('alt', '').strip()
    if not alt or len(alt) > 300:
        abort(400)
    asset.alt = alt
    asset.usage = request.form.get('usage', '')[:200]
    audit('media_update', asset.filename)
    db.session.commit()
    return redirect(url_for('admin.media'))


@admin.post('/media/<int:asset_id>/delete')
@login_required
def media_delete(asset_id):
    asset = db.get_or_404(MediaAsset, asset_id)
    marker = asset.filename.split('-')[0].split('.')[0]
    for item in db.session.scalars(db.select(ContentItem)):
        if marker in json.dumps(item.data) or marker in json.dumps(item.public_data):
            flash('Media masih dipakai oleh konten. Hapus referensinya dan Publish terlebih dahulu.', 'error')
            return redirect(url_for('admin.media'))
    for file in Path(current_app.config['UPLOAD_DIR']).glob(f'{marker}*'):
        file.unlink()
    audit('media_delete', asset.filename)
    db.session.delete(asset)
    db.session.commit()
    return redirect(url_for('admin.media'))


@admin.get('/leads')
@login_required
def leads():
    query = db.select(Lead)
    if state := request.args.get('status'):
        query = query.where(Lead.status == state)
    rows = list(db.session.scalars(query.order_by(Lead.created_at.desc())))
    if q := request.args.get('q', '').casefold():
        rows = [r for r in rows if q in f'{r.name} {r.contact} {r.message}'.casefold()]
    return render_template('admin/leads.html', leads=rows)


@admin.post('/leads/<int:lead_id>')
@login_required
def lead_update(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    state = request.form.get('status')
    if state not in {'new', 'contacted', 'won', 'lost'}:
        abort(400)
    lead.status, lead.notes = state, request.form.get('notes', '')[:10000]
    audit('lead_update', lead.id)
    db.session.commit()
    return redirect(url_for('admin.leads'))


@admin.get('/leads/export.csv')
@login_required
def export_leads():
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['id', 'name', 'contact', 'project_type', 'budget_range', 'message', 'status', 'notes', 'created_at'])
    for row in db.session.scalars(db.select(Lead).order_by(Lead.id)):
        values = [row.id, row.name, row.contact, row.project_type, row.budget_range, row.message, row.status, row.notes, row.created_at.isoformat()]
        writer.writerow([("'" + v) if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    audit('leads_export', 'csv')
    db.session.commit()
    return send_file(io.BytesIO(('\ufeff'+stream.getvalue()).encode()), mimetype='text/csv', as_attachment=True, download_name='ramda-leads.csv')


@admin.get('/audit')
@login_required
def audit_view():
    rows = db.session.scalars(db.select(AuditLog).order_by(AuditLog.id.desc()).limit(300)).all()
    return render_template('admin/audit.html', rows=rows)


@admin.get('/settings')
@login_required
def settings():
    readiness = {key: bool(current_app.config.get(key)) for key in ['AI_API_KEY', 'AI_MODEL', 'TURNSTILE_SECRET_KEY', 'TELEGRAM_BOT_TOKEN', 'SMTP_HOST', 'TOTP_ENCRYPTION_KEY', 'REVALIDATE_SECRET']}
    return render_template('admin/settings.html', readiness=readiness, users=db.session.scalars(db.select(AdminUser)).all())


@admin.route('/security', methods=['GET', 'POST'])
@login_required
def security():
    error = ''
    configured = bool(current_app.config['TOTP_ENCRYPTION_KEY'])
    if request.method == 'POST':
        try:
            passwords.verify(current_user.password_hash, request.form.get('password', ''))
            action = request.form.get('action')
            if action == 'password':
                password = request.form.get('new_password', '')
                if len(password) < 12:
                    raise ValueError('Kata sandi minimal 12 karakter')
                current_user.password_hash = passwords.hash(password)
            elif action == 'disable-totp':
                if not current_user.totp_secret_encrypted:
                    raise ValueError('2FA belum aktif')
                secret = Fernet(current_app.config['TOTP_ENCRYPTION_KEY'].encode()).decrypt(current_user.totp_secret_encrypted.encode()).decode()
                if not pyotp.TOTP(secret).verify(request.form.get('code', '')):
                    raise ValueError('Kode autentikator tidak valid')
                current_user.totp_secret_encrypted = None
                current_user.totp_last_counter = -1
            elif action == 'enable-totp' and configured and not current_user.totp_secret_encrypted:
                secret = session.get('pending_totp', '')
                if not secret or not pyotp.TOTP(secret).verify(request.form.get('code', '')):
                    raise ValueError('Kode autentikator tidak valid')
                current_user.totp_secret_encrypted = Fernet(current_app.config['TOTP_ENCRYPTION_KEY'].encode()).encrypt(secret.encode()).decode()
                current_user.totp_last_counter = int(time.time()) // 30
                session.pop('pending_totp', None)
            else:
                raise ValueError('Tindakan tidak valid')
            audit('security_update', action)
            db.session.commit()
            flash('Pengaturan keamanan diperbarui.', 'success')
            return redirect(url_for('admin.security'))
        except (ValueError, VerificationError, InvalidHashError):
            error = 'Kata sandi / kode tidak valid, atau kata sandi baru terlalu pendek.'
    secret = ''
    if configured and not current_user.totp_secret_encrypted:
        # Only the pending setup secret is in this signed, HttpOnly session; active secrets are encrypted at rest.
        if 'pending_totp' not in session:
            session['pending_totp'] = pyotp.random_base32()
        secret = session['pending_totp']
    return render_template('admin/security.html', error=error, configured=configured, secret=secret)


@admin.post('/users')
@login_required
def user_create():
    email, password = request.form.get('email', '').strip().lower(), request.form.get('password', '')
    if '@' not in email or len(email) > 254 or len(password) < 12:
        abort(400)
    if db.session.scalar(db.select(AdminUser).where(AdminUser.email == email)):
        abort(409)
    db.session.add(AdminUser(email=email, password_hash=passwords.hash(password)))
    audit('user_create', email)
    db.session.commit()
    return redirect(url_for('admin.settings'))


@admin.post('/users/<int:user_id>/toggle')
@login_required
def user_toggle(user_id):
    if user_id == current_user.id:
        abort(400)
    user = db.get_or_404(AdminUser, user_id)
    user.active = not user.active
    audit('user_toggle', user.email)
    db.session.commit()
    return redirect(url_for('admin.settings'))


@admin.get('/backup')
@login_required
def backup():
    return render_template('admin/backup.html')


@admin.get('/backup/content.json')
@login_required
def backup_json():
    result = {'version': 1, 'items': [{'kind': x.kind, 'slug': x.slug, 'data': x.data, 'sort_order': x.sort_order, 'published': x.published, 'is_placeholder': x.is_placeholder} for x in db.session.scalars(db.select(ContentItem))], 'media': [{'filename': x.filename, 'variants': x.variants, 'alt': x.alt, 'width': x.width, 'height': x.height, 'usage': x.usage} for x in db.session.scalars(db.select(MediaAsset))]}
    audit('backup_export', 'content')
    db.session.commit()
    return send_file(io.BytesIO(json.dumps(result, ensure_ascii=False, indent=2).encode()), mimetype='application/json', as_attachment=True, download_name='ramda-content.json')


@admin.get('/backup/uploads.zip')
@login_required
def backup_uploads():
    temporary = tempfile.SpooledTemporaryFile(max_size=2*1024*1024)
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in Path(current_app.config['UPLOAD_DIR']).iterdir():
            if file.is_file():
                archive.write(file, file.name)
    temporary.seek(0)
    audit('backup_export', 'uploads')
    db.session.commit()
    return send_file(temporary, mimetype='application/zip', as_attachment=True, download_name='ramda-uploads.zip')


@admin.post('/backup/import')
@login_required
def backup_import():
    try:
        result = json.load(request.files['file'])
        if result.get('version') != 1 or not isinstance(result['items'], list) or len(result['items']) > 10000:
            raise ValueError('Invalid backup format')
        checked = []
        for entry in result['items']:
            ensure_kind(entry['kind'])
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,159}', entry['slug']):
                raise ValueError('Invalid slug')
            checked.append((entry, validate_content(entry['kind'], entry['data'])))
        for entry, data in checked:
            item = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == entry['kind'], ContentItem.slug == entry['slug']))
            if not item:
                item = ContentItem(kind=entry['kind'], slug=entry['slug'])
                db.session.add(item)
            item.data = data
            item.sort_order = int(entry.get('sort_order', 0))
            item.published = bool(entry.get('published', False))
            item.is_placeholder = bool(entry.get('is_placeholder', True))
        for media in result.get('media', []):
            if not re.fullmatch(r'[a-f0-9]{32}(?:-[0-9]{1,5})?\.(?:webp|avif|svg)', media['filename']) or not media.get('alt') or not 0 < int(media['width']) <= 10000 or not 0 < int(media['height']) <= 10000:
                raise ValueError('Invalid media metadata')
            asset = db.session.scalar(db.select(MediaAsset).where(MediaAsset.filename == media['filename']))
            if not asset:
                asset = MediaAsset(filename=media['filename'])
                db.session.add(asset)
            asset.alt = str(media['alt'])[:300]
            asset.width, asset.height = int(media['width']), int(media['height'])
            asset.variants = media.get('variants', [])
            asset.usage = str(media.get('usage', ''))[:200]
        audit('backup_import', f'{len(checked)} records')
        db.session.commit()
        flash('Konten diimpor sebagai draf kerja. Tinjau lalu Publish. Uploads dipulihkan melalui skrip restore VPS.', 'success')
    except (KeyError, ValueError, TypeError):
        db.session.rollback()
        flash('Berkas backup tidak valid. Tidak ada perubahan disimpan.', 'error')
    return redirect(url_for('admin.backup'))


@admin.post('/backup/uploads-import')
@login_required
def uploads_import():
    from PIL import Image
    from .services.media import sanitize_svg
    import os
    destination = Path(current_app.config['UPLOAD_DIR'])
    try:
        with zipfile.ZipFile(request.files['file']) as archive, tempfile.TemporaryDirectory(dir=destination.parent) as staging:
            members = archive.infolist()
            if len(members) > 1000 or sum(m.file_size for m in members) > 128*1024*1024:
                raise ValueError('Archive too large')
            for member in members:
                if not re.fullmatch(r'[a-f0-9]{32}(?:-[0-9]{1,5})?\.(?:webp|avif|svg)', member.filename) or member.file_size > 8*1024*1024 or member.flag_bits & 1:
                    raise ValueError('Invalid archive entry')
                raw = archive.read(member)
                target = Path(staging) / member.filename
                if target.suffix == '.svg':
                    clean, _, _ = sanitize_svg(raw)
                    target.write_bytes(clean)
                else:
                    with Image.open(io.BytesIO(raw)) as image:
                        if image.format not in {'WEBP', 'AVIF'} or image.width * image.height > 24_000_000:
                            raise ValueError('Invalid archive image')
                        image.load()
                        clean = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
                        clean.save(target, format=target.suffix[1:].upper(), quality=85, exif=b'')
            for file in Path(staging).iterdir():
                os.replace(file, destination / file.name)
        audit('backup_import', 'uploads')
        db.session.commit()
        flash('Uploads berhasil dipulihkan. Impor juga JSON konten untuk metadata media.', 'success')
    except (ValueError, KeyError, zipfile.BadZipFile, OSError, Image.DecompressionBombError):
        db.session.rollback()
        flash('Uploads ZIP tidak valid. Tidak ada berkas dipulihkan.', 'error')
    return redirect(url_for('admin.backup'))


@admin.post('/leads/<int:lead_id>/delete')
@login_required
def lead_delete(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    audit('lead_delete', lead.id)
    db.session.delete(lead)
    db.session.commit()
    return redirect(url_for('admin.leads'))
