import json
from pathlib import Path
import click
from argon2 import PasswordHasher
from .models import db, AdminUser, ContentItem, Publication
from .content import validate_content


def register_cli(app):
    @app.cli.command("seed")
    def seed():
        """Idempotently insert initial content without overwriting edits."""
        source = Path(__file__).resolve().parents[1] / "seed" / "content.json"
        count = 0
        for item in json.loads(source.read_text()):
            existing = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == item["kind"], ContentItem.slug == item["slug"]))
            if existing:
                continue
            data = validate_content(item["kind"], item["data"])
            published = item.get("published", False)
            db.session.add(ContentItem(kind=item["kind"], slug=item["slug"], data=data, public_data=data if published else None, published=published, public_visible=published, sort_order=item.get("sort_order", 0), public_order=item.get("sort_order", 0), is_placeholder=True))
            count += 1
        db.session.add(Publication())
        db.session.commit()
        click.echo(f"Inserted {count} placeholder records; existing content preserved.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(email, password):
        if len(password) < 12:
            raise click.ClickException("Use at least 12 characters")
        email = email.strip().lower()
        if "@" not in email:
            raise click.ClickException("Invalid email")
        if db.session.scalar(db.select(AdminUser).where(AdminUser.email == email)):
            raise click.ClickException("User already exists")
        db.session.add(AdminUser(email=email, password_hash=PasswordHasher().hash(password)))
        db.session.commit()
        click.echo("Admin created.")

    @app.cli.command("prune-metadata")
    def prune_metadata():
        import time
        from datetime import timedelta
        from .models import RateBucket, AiSession, now
        db.session.execute(db.delete(RateBucket).where(RateBucket.expires_at < int(time.time())))
        db.session.execute(db.delete(AiSession).where(AiSession.created_at < now() - timedelta(days=1)))
        db.session.commit()
        click.echo("Expired rate and session metadata removed.")
