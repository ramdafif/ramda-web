import hashlib
import hmac
import time
from urllib.parse import urlsplit
import httpx
from flask import current_app, request
from sqlalchemy.exc import IntegrityError
from ..models import db, RateBucket


def ip_hash():
    # Nginx replaces X-Real-IP; direct clients must never control forwarded headers.
    ip = request.headers.get("X-Real-IP", request.remote_addr or "unknown") if request.remote_addr in {"127.0.0.1", "::1"} else request.remote_addr or "unknown"
    return hmac.new(current_app.config["SECRET_KEY"].encode(), ip.encode(), hashlib.sha256).hexdigest()


def take_rate(namespace, identity, limit, window):
    current = int(time.time())
    key = f"{namespace}:{identity}:{current // window}"
    result = db.session.execute(db.update(RateBucket).where(RateBucket.key == key, RateBucket.count < limit).values(count=RateBucket.count + 1))
    if result.rowcount:
        db.session.commit()
        return True
    if db.session.get(RateBucket, key):
        db.session.rollback()
        return False
    try:
        db.session.add(RateBucket(key=key, count=1, expires_at=current + window * 2))
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        result = db.session.execute(db.update(RateBucket).where(RateBucket.key == key, RateBucket.count < limit).values(count=RateBucket.count + 1))
        db.session.commit()
        return bool(result.rowcount)


def origin_allowed():
    return request.headers.get("Origin", "").rstrip("/") == current_app.config["SITE_URL"] and request.is_json


def verify_turnstile(token, action):
    if current_app.config["DEV_ALLOW_UNVERIFIED_FORMS"]:
        return True
    if not token or not current_app.config["TURNSTILE_SECRET_KEY"]:
        return False
    try:
        response = httpx.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data={"secret": current_app.config["TURNSTILE_SECRET_KEY"], "response": token}, timeout=8)
        response.raise_for_status()
        result = response.json()
        return bool(result.get("success") and result.get("action") == action and result.get("hostname") == urlsplit(current_app.config["SITE_URL"]).hostname)
    except (httpx.HTTPError, ValueError):
        return False
