"""Create an isolated test database. Never call this against an existing database."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from argon2 import PasswordHasher
from ramda import create_app
from ramda.models import db, AdminUser

if os.environ.get('RAMDA_E2E') != 'true':
    raise SystemExit('Requires RAMDA_E2E=true and a fresh test database')
app = create_app()
with app.app_context():
    db.create_all()
    result = app.test_cli_runner().invoke(args=['seed'])
    if result.exit_code:
        raise SystemExit(result.output)
    if not db.session.scalar(db.select(AdminUser).where(AdminUser.email == 'e2e@example.test')):
        db.session.add(AdminUser(email='e2e@example.test', password_hash=PasswordHasher().hash(os.environ['E2E_PASSWORD'])))
        db.session.commit()
