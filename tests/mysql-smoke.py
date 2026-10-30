import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from ramda import create_app
from ramda.models import db, ContentItem
from ramda.services.security import take_rate
app=create_app()
with app.app_context():
    assert db.session.scalar(db.select(db.func.count()).select_from(ContentItem)) == 47
    client=app.test_client()
    assert client.get('/api/health').status_code == 200
    assert len(client.get('/api/public/projects').json['items']) == 4
    assert client.get('/api/public/articles').json['total'] == 0
    assert take_rate('mysql-test','identity',1,3600)
    assert not take_rate('mysql-test','identity',1,3600)
print('MySQL migration, seed, API snapshots, JSON and atomic rate counters passed.')
