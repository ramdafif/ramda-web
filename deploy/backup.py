"""Full database + uploads backup. Use filesystem permissions and off-host replication."""
import os
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import make_url
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'.env')
output=root/'var/backups'
output.mkdir(parents=True,exist_ok=True)
os.chmod(output,0o700)
url=make_url(os.environ['DATABASE_URL'])

def mysql_escape(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r')+'"'

with tempfile.TemporaryDirectory(dir=output) as temp:
    temp=Path(temp)
    if url.get_backend_name()=='sqlite':
        source=Path(url.database)
        if not source.is_absolute():source=root/'backend/instance'/source
        with sqlite3.connect(source) as src, sqlite3.connect(temp/'database.sqlite') as dst:src.backup(dst)
    elif url.get_backend_name() in {'mysql','mariadb'}:
        credentials=temp/'mysql.cnf'
        credentials.write_text('[client]\n'+''.join(f'{k}={mysql_escape(v)}\n' for k,v in {'user':url.username or '', 'password':url.password or '', 'host':url.host or '127.0.0.1', 'port':url.port or 3306}.items()))
        credentials.chmod(0o600)
        with (temp/'database.sql').open('wb') as dump:
            subprocess.run(['mysqldump',f'--defaults-extra-file={credentials}','--single-transaction','--no-tablespaces','--default-character-set=utf8mb4',url.database],stdout=dump,check=True)
        credentials.unlink()
    else:raise SystemExit('Unsupported backup database')
    name='ramda-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.tar.gz'
    partial=output/(name+'.partial')
    with tarfile.open(partial,'w:gz') as archive:
        for file in temp.iterdir():archive.add(file,arcname=file.name)
        uploads=Path(os.environ.get('UPLOAD_DIR') or root/'backend/instance/uploads')
        if uploads.exists():archive.add(uploads,arcname='uploads')
    partial.chmod(0o600)
    partial.replace(output/name)
    cutoff=datetime.now(timezone.utc)-timedelta(days=int(os.getenv('BACKUP_RETENTION_DAYS','14')))
    for file in output.glob('ramda-*.tar.gz'):
        if datetime.fromtimestamp(file.stat().st_mtime,timezone.utc)<cutoff:file.unlink()
print('Backup completed.')
