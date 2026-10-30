from datetime import timedelta
from ramda.models import db, ContentItem, now
from ramda.content import validate_content


def test_article_publication_reading_time_and_markdown(app, client):
    with app.app_context():
        item = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == 'article'))
        data = validate_content('article', {**item.data, 'body': {'id': '# Title\n\n' + 'word '*500, 'en': ''}, 'status': 'published'})
        item.data, item.public_data, item.public_visible = data, data, True
        slug = item.slug
        db.session.commit()
    response = client.get(f'/api/public/articles/{slug}')
    assert response.status_code == 200
    assert response.json['reading_time'] == 3
    assert '<p>' in response.json['body_html']['id']
    assert client.get('/api/public/sitemap-data').json['articles'][0]['slug'] == slug


def test_scheduled_article_not_visible_yet(app, client):
    with app.app_context():
        item = db.session.scalar(db.select(ContentItem).where(ContentItem.kind == 'article'))
        item.public_data = {**item.data, 'status': 'published', 'published_at': (now()+timedelta(days=1)).isoformat()}
        item.public_visible = True
        db.session.commit()
    assert client.get('/api/public/articles').json['total'] == 0


def test_missing_project_404_and_status_enum(app, client):
    assert client.get('/api/public/projects/no-such-project').status_code == 404
    allowed = {'live', 'in_development', 'in_planning', 'mvp', 'academic', 'archived'}
    assert all(item['status'] in allowed for item in client.get('/api/public/projects').json['items'])
