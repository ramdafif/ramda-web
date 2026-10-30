import { spawn, spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { randomBytes } from 'node:crypto';
const root = resolve(import.meta.dirname,'..');
const temp = mkdtempSync(resolve(tmpdir(),'ramda-e2e-'));
const python = resolve(root,'backend/.venv/bin/python');
const env = {...process.env, APP_ENV:'development',RAMDA_E2E:'true',SECRET_KEY:randomBytes(32).toString('hex'),REVALIDATE_SECRET:randomBytes(32).toString('hex'),DATABASE_URL:`sqlite:///${temp}/test.sqlite`,UPLOAD_DIR:`${temp}/uploads`,SITE_URL:'http://127.0.0.1:4321',DEV_ALLOW_UNVERIFIED_FORMS:'true',AI_API_KEY:'',TURNSTILE_SITE_KEY:'',TURNSTILE_SECRET_KEY:'',BACKEND_URL:'http://127.0.0.1:8000',REVALIDATE_URL:'http://127.0.0.1:4321/__revalidate',E2E_PASSWORD:process.env.E2E_PASSWORD || 'e2e-isolated-test-password',NO_PROXY:[process.env.NO_PROXY,'127.0.0.1','localhost'].filter(Boolean).join(',')};
const setup=spawnSync(python,['deploy/prepare-e2e.py'],{cwd:root,env,stdio:'inherit'});
if(setup.status)process.exit(setup.status);
const backend=spawn(python,['-m','gunicorn','--chdir','backend','--bind','127.0.0.1:8000','--workers','1','--threads','4','--timeout','70','--no-control-socket','wsgi:app'],{cwd:root,env,stdio:'inherit'});
const frontend=spawn('node',['dist/server/entry.mjs'],{cwd:resolve(root,'frontend'),env:{...env,HOST:'127.0.0.1',PORT:'4321',ASTRO_NODE_LOGGING:'disabled'},stdio:'inherit'});
const children=[backend,frontend];
let stopping=false;
function stop(code=0){if(stopping)return;stopping=true;for(const child of children)child.kill('SIGTERM');rmSync(temp,{recursive:true,force:true});process.exitCode=code;}
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>stop());
for(const child of children)child.on('exit',code=>stop(code||0));

let announced=false;
const ready=setInterval(async()=>{
 if(announced)return;
 try{
  const [front,back]=await Promise.all([fetch('http://127.0.0.1:4321/'),fetch('http://127.0.0.1:8000/api/health')]);
  if(front.ok && back.ok && !announced){announced=true;clearInterval(ready);console.log('RAMDA test services ready');}
 }catch{/* Startup only. */}
},250);
process.on('exit',()=>clearInterval(ready));
