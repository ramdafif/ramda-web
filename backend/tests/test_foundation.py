from ramda.models import db, ContentItem
from ramda.content import render_md, preview_serializer


def test_health(client):
    assert client.get("/api/health").json == {"status": "ok"}


def test_home_is_database_driven_and_hides_unverified_stats(client):
    response = client.get("/api/public/home")
    assert response.status_code == 200
    assert response.json["settings"]["brand_name"] == "RAMDA"
    assert len(response.json["projects"]) == 4
    keys = [s["key"] for s in response.json["sections"]]
    assert all(k not in keys for k in ["stats", "articles", "testimonials", "pricing", "faq", "ai"])


def test_etag_conditional_request(client):
    response = client.get("/api/public/home")
    assert client.get("/api/public/home", headers={"If-None-Match": response.headers["ETag"]}).status_code == 304


def test_drafts_do_not_leak(client):
    assert client.get("/api/public/articles").json["total"] == 0
    assert client.get("/api/public/articles/catatan-1").status_code == 404


def test_publication_snapshot_isolated_from_edits(app, client):
    with app.app_context():
        item = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == "hero"))
        item.data = {**item.data, "headline": {"id": "Unpublished change", "en": ""}}
        db.session.commit()
    assert client.get("/api/public/home").json["hero"]["headline"]["id"] != "Unpublished change"


def test_preview_is_signed_and_private(app, client):
    with app.app_context():
        token = preview_serializer().dumps({"scope": "drafts"})
    response = client.get("/api/public/articles", headers={"X-Preview-Token": token})
    assert response.json["total"] == 4
    assert response.headers["Cache-Control"] == "private, no-store"
    assert client.get("/api/public/articles", headers={"X-Preview-Token": token + "x"}).json["total"] == 0


def test_markdown_sanitized():
    html = render_md('[x](javascript:alert(1)) <script>alert(1)</script>')
    assert '<script' not in html
    assert 'href="javascript:' not in html


def test_seed_idempotent(app):
    with app.app_context():
        before = db.session.query(ContentItem).count()
        assert app.test_cli_runner().invoke(args=["seed"]).exit_code == 0
        assert db.session.query(ContentItem).count() == before


def test_ai_secrets_never_exposed(client):
    public = client.get("/api/public/home").json["ai"]
    assert "system_prompt" not in public
    assert "model" not in public
