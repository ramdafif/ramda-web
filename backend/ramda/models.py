from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, true

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class ContentItem(db.Model):
    """Typed CMS entities; working data and the public snapshot are separate."""
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(40), nullable=False, index=True)
    slug = db.Column(db.String(160), nullable=False)
    data = db.Column(db.JSON, nullable=False, default=dict)
    public_data = db.Column(db.JSON, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    public_order = db.Column(db.Integer, nullable=False, default=0)
    published = db.Column(db.Boolean, nullable=False, default=False)
    public_visible = db.Column(db.Boolean, nullable=False, default=False)
    is_placeholder = db.Column(db.Boolean, nullable=False, default=True)
    public_is_placeholder = db.Column(db.Boolean, nullable=False, default=True, server_default=true())
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("kind", "slug"),)


class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    totp_secret_encrypted = db.Column(db.Text)
    totp_last_counter = db.Column(db.BigInteger, default=-1, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    @property
    def is_active(self):
        return self.active


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_user.id"))
    action = db.Column(db.String(80), nullable=False)
    target = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)


class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(254), nullable=False)
    project_type = db.Column(db.String(100), nullable=False)
    budget_range = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")
    notes = db.Column(db.Text, nullable=False, default="")
    notification_status = db.Column(db.String(30), default="pending", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)


class MediaAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False, unique=True)
    variants = db.Column(db.JSON, nullable=False, default=list)
    alt = db.Column(db.String(300), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    usage = db.Column(db.String(200), default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)


class RateBucket(db.Model):
    key = db.Column(db.String(160), primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.BigInteger, nullable=False, index=True)


class AiBudget(db.Model):
    day = db.Column(db.String(10), primary_key=True)
    # Integer micro-USD avoids floating point races and rounding errors.
    spent_micros = db.Column(db.BigInteger, nullable=False, default=0)


class AiSession(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    ip_hash = db.Column(db.String(64), nullable=False)
    turns = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)


class AiUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_tokens = db.Column(db.Integer, nullable=False, default=0)
    output_tokens = db.Column(db.Integer, nullable=False, default=0)
    estimated_cost_micros = db.Column(db.BigInteger, nullable=False, default=0)
    outcome = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)
