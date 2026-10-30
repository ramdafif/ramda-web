import hashlib
import json
import math
import re
from datetime import datetime, timezone
from flask import current_app, make_response, request
from itsdangerous import URLSafeTimedSerializer, BadSignature
from markdown_it import MarkdownIt
import nh3
from .models import ContentItem, db
from .schemas import SCHEMAS

markdown = MarkdownIt("commonmark", {"html": False, "linkify": False})


def render_md(value):
    return nh3.clean(markdown.render(value or ""), tags={"p", "br", "strong", "em", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "pre", "code", "a", "hr"}, attributes={"a": {"href", "title"}}, url_schemes={"https", "http", "mailto"})


def preview_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="content-preview-v1")


def valid_preview(token):
    if not token:
        return False
    try:
        return preview_serializer().loads(token, max_age=600) == {"scope": "drafts"}
    except BadSignature:
        return False


def serialize(item, draft=False):
    data = dict(item.data if draft else item.public_data or {})
    data.update({"id": item.id, "slug": item.slug, "sort_order": item.sort_order if draft else item.public_order})
    for key in ("bio", "problem", "solution", "result", "body", "answer"):
        if isinstance(data.get(key), dict):
            data[key + "_html"] = {locale: render_md(text) for locale, text in data[key].items()}
    if item.kind == "article":
        data["reading_time"] = max(1, math.ceil(len(re.findall(r"\w+", data.get("body", {}).get("id", ""))) / 200))
    return data


def items(kind, draft=False):
    query = db.select(ContentItem).where(ContentItem.kind == kind)
    if not draft:
        query = query.where(ContentItem.public_visible.is_(True))
    results = db.session.scalars(query.order_by(ContentItem.sort_order if draft else ContentItem.public_order, ContentItem.id)).all()
    out = []
    for item in results:
        data = serialize(item, draft)
        if not draft:
            if data.get("visible") is False or data.get("enabled") is False:
                continue
            if kind == "stat" and item.public_is_placeholder:
                continue
            if kind == "testimonial" and (item.public_is_placeholder or not data.get("consent_given")):
                continue
            if kind == "article" and (data.get("status") != "published" or not data.get("published_at") or datetime.fromisoformat(data["published_at"].replace("Z", "+00:00")) > datetime.now(timezone.utc)):
                continue
        out.append(data)
    return out


def singleton(kind, draft=False):
    result = items(kind, draft)
    return result[0] if result else {}


def ai_public(draft=False):
    config = singleton("ai_config", draft)
    keys = {"enabled", "welcome_message", "suggestions", "disclaimer", "offline_message", "limit_message", "input_placeholder", "max_input_chars", "max_turns"}
    public = {k: v for k, v in config.items() if k in keys}
    # The kill switch and provider readiness also control rendering.
    public["enabled"] = bool(config.get("enabled") and not config.get("kill_switch") and current_app.config.get("AI_API_KEY") and current_app.config.get("AI_MODEL"))
    return public


def home(draft=False):
    data = {"settings": singleton("settings", draft), "hero": singleton("hero", draft), "about": singleton("about", draft), "ai": ai_public(draft)}
    kinds = {"stats": "stat", "projects": "project", "services": "service", "process": "process", "tech": "tech", "articles": "article", "pricing": "package", "testimonials": "testimonial", "faq": "faq"}
    for name, kind in kinds.items():
        values = items(kind, draft)
        if name == "projects":
            values = [x for x in values if x.get("featured")]
        if name == "tech":
            values = [x for x in values if x.get("show_on_home")]
        data[name] = values
    sections = items("section", draft)
    def present(section):
        key = section["key"]
        if key == "ai":
            return data["ai"].get("enabled")
        return key in {"navbar", "hero", "cta", "footer"} or bool(data.get(key))
    data["sections"] = [s for s in sections if s.get("enabled") and present(s)]
    data["turnstile_site_key"] = current_app.config["TURNSTILE_SITE_KEY"]
    return data


def json_response(data, private=False):
    body = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    response = make_response(body)
    response.mimetype = "application/json"
    response.set_etag(hashlib.sha256(body.encode()).hexdigest())
    response.headers["Cache-Control"] = "private, no-store" if private else "public, max-age=0, s-maxage=3, must-revalidate"
    if not private:
        response.make_conditional(request)
    return response


def validate_content(kind, data):
    if kind == "article" and data.get("status") == "published" and not data.get("published_at"):
        data = {**data, "published_at": datetime.now(timezone.utc).isoformat()}
    result = SCHEMAS[kind].model_validate(data).model_dump(mode="json")
    if kind == "ai_config":
        allowed = current_app.config["AI_ALLOWED_MODELS"]
        if result["model"] and result["model"] not in allowed:
            raise ValueError("Model must be in the environment allowlist")
    return result
