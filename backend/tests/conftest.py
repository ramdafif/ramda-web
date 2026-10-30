import pytest
from ramda import create_app
from ramda.models import db


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "REVALIDATE_SECRET": "", "SECRET_KEY": "test-only-secret-that-is-at-least-32-characters", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}", "UPLOAD_DIR": str(tmp_path / "uploads"), "WTF_CSRF_ENABLED": False, "DEV_ALLOW_UNVERIFIED_FORMS": True, "SITE_URL": "http://localhost:4321"})
    with app.app_context():
        db.create_all()
        result = app.test_cli_runner().invoke(args=["seed"])
        assert result.exit_code == 0, result.output
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
