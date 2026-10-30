from pathlib import Path
import os
import subprocess
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'.env')
if os.environ.get('APP_ENV')!='production':
    raise SystemExit('Set APP_ENV=production before VPS deployment')
if not os.environ.get('DATABASE_URL') or len(os.environ.get('SECRET_KEY',''))<32 or len(os.environ.get('REVALIDATE_SECRET',''))<32:
    raise SystemExit('Configure DATABASE_URL, SECRET_KEY and REVALIDATE_SECRET first')
environment=dict(os.environ)
if environment.get('MIGRATION_DATABASE_URL'):environment['DATABASE_URL']=environment['MIGRATION_DATABASE_URL']
subprocess.run([str(root/'backend/.venv/bin/python'),'-m','flask','--app','backend/wsgi.py','db','upgrade'],cwd=root,env=environment,check=True)
