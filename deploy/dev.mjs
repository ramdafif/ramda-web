import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
const root = resolve(import.meta.dirname, '..');
const env = { ...process.env, NO_PROXY: [process.env.NO_PROXY, 'localhost', '127.0.0.1', '::1'].filter(Boolean).join(',') };
const backend = spawn(resolve(root, 'backend/.venv/bin/python'), ['-m','gunicorn','--chdir','backend','--bind','127.0.0.1:8000','--workers','1','--threads','4','--timeout','70','--no-control-socket','wsgi:app'], {cwd:root,env,stdio:'inherit'});
const frontend = spawn('npm', ['--prefix','frontend','run','dev'], {cwd:root,env,stdio:'inherit'});
const children = [backend, frontend];
function stop(code=0) { for (const child of children) child.kill('SIGTERM'); process.exitCode=code; }
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>stop());
for (const child of children) child.on('exit',code=>stop(code || 0));
