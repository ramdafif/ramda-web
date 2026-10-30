import assert from 'node:assert/strict';
const base='http://127.0.0.1:4321';
const backend='http://127.0.0.1:8000';
for(const path of ['/','/projects','/projects/gajiku','/articles','/rss.xml','/sitemap.xml','/robots.txt']) {
 const response=await fetch(base+path);assert.equal(response.status,200,path);
 const body=await response.text();assert(body.length>80,path);
 if(path==='/'){
   assert.match(body,/<h1/);assert.match(body,/Gajiku/);assert(!body.includes('id="testimonials"'));assert(!body.includes('id="stats"'));
   assert(response.headers.get('Content-Security-Policy').includes('frame-ancestors'));
 }
}
assert.equal((await fetch(base+'/projects/missing')).status,404);
assert.equal((await fetch(base+'/missing')).status,404);
assert.equal((await fetch(base+'/articles/catatan-1')).status,404);
assert.equal((await fetch(base+'/__revalidate',{method:'POST'})).status,401);
const publicData=await (await fetch(backend+'/api/public/home')).json();
assert.equal(publicData.settings.brand_name,'RAMDA');
let cookies='';
function updateCookies(response){
 const parsed=new Map(cookies.split('; ').filter(Boolean).map(x=>x.split(/=(.*)/s).slice(0,2)));
 for(const cookie of response.headers.getSetCookie()){
  const [key,value]=cookie.split(';')[0].split(/=(.*)/s);parsed.set(key,value);
 }
 cookies=[...parsed].map(([k,v])=>`${k}=${v}`).join('; ');
}
async function adminGet(path){const response=await fetch(backend+path,{headers:{Cookie:cookies}});updateCookies(response);return response;}
const login=await adminGet('/admin/login');
const token=(await login.text()).match(/name="csrf_token" value="([^"]+)"/)[1];
const auth=await fetch(backend+'/admin/login',{method:'POST',headers:{Cookie:cookies},body:new URLSearchParams({csrf_token:token,email:'e2e@example.test',password:process.env.E2E_PASSWORD || 'e2e-isolated-test-password'}),redirect:'manual'});
assert.equal(auth.status,302);updateCookies(auth);
const dashboard=await adminGet('/admin/');assert.equal(dashboard.status,200);assert.match(await dashboard.text(),/Ringkasan situs/);
const hero=publicData.hero;
const edit=await adminGet(`/admin/content/hero/${hero.id}/edit`);
const editToken=(await edit.text()).match(/name="csrf_token" value="([^"]+)"/)[1];
const data={...hero};delete data.id;delete data.slug;delete data.sort_order;
const original=data.headline;
data.headline={id:'HTTP publication verification',en:''};
const save=await fetch(backend+`/admin/content/hero/${hero.id}/edit`,{method:'POST',headers:{Cookie:cookies},body:new URLSearchParams({csrf_token:editToken,content_json:JSON.stringify(data),slug:hero.slug,published:'on'}),redirect:'manual'});
assert.equal(save.status,302);updateCookies(save);
assert.notEqual((await (await fetch(backend+'/api/public/home')).json()).hero.headline.id,data.headline.id);
const start=Date.now();
const publish=await fetch(backend+'/admin/publish',{method:'POST',headers:{Cookie:cookies},body:new URLSearchParams({csrf_token:editToken}),redirect:'manual'});
assert.equal(publish.status,302);updateCookies(publish);
let updated=false;
for(let i=0;i<15;i++){
 if((await (await fetch(base)).text()).includes(data.headline.id)){updated=true;break;}
 await new Promise(resolve=>setTimeout(resolve,200));
}
assert(updated);assert(Date.now()-start<5000);
console.log(`SSR publication update verified in ${Date.now()-start} ms.`);
const contact=await fetch(backend+'/api/public/contact',{method:'POST',headers:{'Content-Type':'application/json',Origin:base},body:JSON.stringify({name:'HTTP Smoke',contact:'smoke@example.test',project_type:'Website & Landing Page',budget_range:'Belum ditentukan',message:'Pesan pengujian formulir kontak.'})});
assert.equal(contact.status,201);
const inbox=await adminGet('/admin/leads');assert.match(await inbox.text(),/HTTP Smoke/);
const logout=await fetch(backend+'/admin/logout',{method:'POST',headers:{Cookie:cookies},body:new URLSearchParams({csrf_token:editToken}),redirect:'manual'});assert.equal(logout.status,302);
console.log('HTTP smoke passed: 7 public routes, genuine 404s, protected revalidation, CSRF login/edit/publish, lead capture and inbox.');
