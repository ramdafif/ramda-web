import os
from pathlib import Path
from flask import Flask, jsonify, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
from .models import db, AdminUser

csrf = CSRFProtect()
login = LoginManager()
login.login_view = "admin.login_view"


def create_app(test_config=None):
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    app = Flask(__name__, instance_relative_config=True)
    root = Path(app.instance_path)
    root.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", ""),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///ramda.sqlite"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        UPLOAD_DIR=os.getenv("UPLOAD_DIR") or str(root / "uploads"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("APP_ENV") == "production",
        REMEMBER_COOKIE_SECURE=os.getenv("APP_ENV") == "production",
        REMEMBER_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=3600,
        WTF_CSRF_TIME_LIMIT=3600,
        SITE_URL=os.getenv("SITE_URL", "http://localhost:4321").rstrip("/"),
        REVALIDATE_URL=os.getenv("REVALIDATE_URL", "http://127.0.0.1:4321/__revalidate"),
        REVALIDATE_SECRET=os.getenv("REVALIDATE_SECRET", ""),
        TURNSTILE_SITE_KEY=os.getenv("TURNSTILE_SITE_KEY", ""),
        TURNSTILE_SECRET_KEY=os.getenv("TURNSTILE_SECRET_KEY", ""),
        DEV_ALLOW_UNVERIFIED_FORMS=os.getenv("DEV_ALLOW_UNVERIFIED_FORMS") == "true" and os.getenv("APP_ENV") != "production",
        AI_PROVIDER=os.getenv("AI_PROVIDER", "openai_compatible"),
        AI_MODEL=os.getenv("AI_MODEL", ""),
        AI_API_KEY=os.getenv("AI_API_KEY", ""),
        AI_BASE_URL=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
        AI_ALLOWED_MODELS=[x.strip() for x in os.getenv("AI_ALLOWED_MODELS", "").split(",") if x.strip()],
        AI_DAILY_BUDGET_USD=float(os.getenv("AI_DAILY_BUDGET_USD", "1")),
        AI_INPUT_USD_PER_MILLION=float(os.getenv("AI_INPUT_USD_PER_MILLION", "1")),
        AI_OUTPUT_USD_PER_MILLION=float(os.getenv("AI_OUTPUT_USD_PER_MILLION", "4")),
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID", ""),
        SMTP_HOST=os.getenv("SMTP_HOST", ""), SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USER=os.getenv("SMTP_USER", ""), SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_FROM=os.getenv("SMTP_FROM", ""), NOTIFY_EMAIL=os.getenv("NOTIFY_EMAIL", ""),
        TOTP_ENCRYPTION_KEY=os.getenv("TOTP_ENCRYPTION_KEY", ""),
    )
    if test_config:
        app.config.update(test_config)
    if len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("Set SECRET_KEY to at least 32 random characters")
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    Migrate(app, db, directory=str(Path(__file__).resolve().parents[1] / "migrations"))
    login.init_app(app)
    csrf.init_app(app)

    @login.user_loader
    def user_loader(user_id):
        user = db.session.get(AdminUser, int(user_id)) if user_id.isdigit() else None
        return user if user and user.active else None

    from .api import api
    from .admin import admin
    from .cli import register_cli
    app.register_blueprint(api)
    app.register_blueprint(admin)
    csrf.exempt(api)  # Public JSON endpoints use strict Origin, Turnstile and rate limits.
    register_cli(app)

    @app.before_request
    def backup_limits():
        if request.path.startswith('/api/public/') and request.method == 'POST':
            request.max_content_length = 64 * 1024
        if request.path == '/admin/backup/uploads-import':
            request.max_content_length = 64 * 1024 * 1024

    @app.get('/uploads/<path:filename>')
    def uploads(filename):
        from flask import send_from_directory
        response = send_from_directory(app.config['UPLOAD_DIR'], filename, max_age=31536000)
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'none'; sandbox"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify(error="Sesi formulir berakhir. Muat ulang halaman."), 400

    @app.after_request
    def security(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if request.path.startswith("/admin"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["Cache-Control"] = "private, no-store"
        return response

    return app
