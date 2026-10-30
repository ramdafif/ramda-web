import { spawn } from 'node:child_process';
const server=spawn('node',['deploy/test-server.mjs'],{stdio:'inherit'});
let result=1;
try{
 let healthy=false;
 for(let i=0;i<60;i++){
  try{
   const response=await fetch('http://127.0.0.1:4321/');
   if(response.ok){healthy=true;break;}
  }catch{/* Startup is still in progress. */}
  await new Promise(resolve=>setTimeout(resolve,250));
 }
 if(!healthy)throw new Error('Test services did not become healthy');
 const smoke=spawn('node',['tests/http-smoke.mjs'],{stdio:'inherit'});
 result=await new Promise(resolve=>smoke.on('exit',code=>resolve(code||0)));
}finally{server.kill('SIGTERM');}
process.exitCode=result;
