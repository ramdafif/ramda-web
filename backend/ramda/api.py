from flask import Blueprint, abort, request
from .content import home, items, json_response, valid_preview

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    from .models import db
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}


@api.get("/public/home")
def homepage():
    draft = valid_preview(request.headers.get("X-Preview-Token"))
    return json_response(home(draft), private=draft)


@api.get("/public/projects")
def projects():
    draft = valid_preview(request.headers.get("X-Preview-Token"))
    return json_response({"items": items("project", draft)}, private=draft)


@api.get("/public/projects/<slug>")
def project(slug):
    draft = valid_preview(request.headers.get("X-Preview-Token"))
    result = next((i for i in items("project", draft) if i["slug"] == slug), None)
    if result is None:
        abort(404)
    return json_response(result, private=draft)


@api.get("/public/articles")
def articles():
    draft = valid_preview(request.headers.get("X-Preview-Token"))
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        return {"error": "Invalid page"}, 400
    result = items("article", draft)
    return json_response({"items": result[(page-1)*12:page*12], "page": page, "total": len(result)}, private=draft)


@api.get("/public/articles/<slug>")
def article(slug):
    draft = valid_preview(request.headers.get("X-Preview-Token"))
    result = next((i for i in items("article", draft) if i["slug"] == slug), None)
    if result is None:
        abort(404)
    return json_response(result, private=draft)


@api.get("/public/sitemap-data")
def sitemap():
    return json_response({"projects": [{"slug": i["slug"]} for i in items("project")], "articles": [{"slug": i["slug"], "published_at": i["published_at"]} for i in items("article")]})


@api.post('/public/contact')
def contact():
    from pydantic import ValidationError
    from .schemas import ContactInput
    from .models import db, Lead
    from .content import singleton
    from .services.security import origin_allowed, take_rate, ip_hash, verify_turnstile
    from .services.notifications import notify_lead
    if not origin_allowed():
        return {'error': 'Origin tidak diizinkan.'}, 403
    if not take_rate('contact', ip_hash(), 5, 3600):
        return {'error': 'Batas pengiriman tercapai. Coba lagi nanti.'}, 429
    try:
        payload = ContactInput.model_validate(request.get_json())
    except ValidationError:
        return {'error': 'Periksa kembali isian formulir.'}, 422
    if payload.website:
        return {'ok': True}, 202
    if not verify_turnstile(payload.turnstile_token, 'contact'):
        return {'error': 'Verifikasi belum berhasil. Silakan coba lagi.'}, 403
    settings = singleton('settings')
    types = {x['id'] for x in settings.get('project_types', [])}
    budgets = {x['id'] for x in settings.get('budget_ranges', [])}
    if payload.project_type not in types or payload.budget_range not in budgets:
        return {'error': 'Pilihan formulir tidak valid.'}, 422
    lead = Lead(**payload.model_dump(exclude={'website', 'turnstile_token'}))
    db.session.add(lead)
    db.session.commit()
    lead.notification_status = notify_lead(lead) if settings.get('notifications_enabled') else 'disabled'
    db.session.commit()
    return {'ok': True}, 201


@api.post('/public/ai/chat')
def chat():
    from flask import Response, stream_with_context
    from pydantic import ValidationError
    from .schemas import ChatInput
    from .services.security import origin_allowed, take_rate, ip_hash, verify_turnstile
    from .services import ai
    if not origin_allowed():
        return {'error': 'origin'}, 403
    private, ready = ai.config()
    if not ready:
        return {'error': 'offline'}, 503
    identity = ip_hash()
    if not take_rate('ai', identity, private.get('requests_per_hour', 10), 3600):
        return {'error': 'limit'}, 429
    try:
        payload = ChatInput.model_validate(request.get_json())
    except ValidationError:
        return {'error': 'input'}, 422
    if not payload.session_token and not verify_turnstile(payload.turnstile_token, 'ai'):
        return {'error': 'verify'}, 403
    prepared, error = ai.prepare(payload, identity)
    if error:
        return {'error': error}, 429 if error == 'limit' else 503 if error == 'offline' else 400
    response = Response(stream_with_context(ai.stream(prepared)), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
