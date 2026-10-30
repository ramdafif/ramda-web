import {test,expect} from '../frontend/node_modules/@playwright/test';

test('admin login, edit working draft, publish and verify public snapshot',async({page,request},testInfo)=>{
 const base='http://127.0.0.1:8000';
 await page.goto(base+'/admin/login');
 await page.getByLabel('Email',{exact:true}).fill('e2e@example.test');
 await page.getByLabel('Kata sandi',{exact:true}).fill(process.env.E2E_PASSWORD || 'e2e-isolated-test-password');
 await page.getByRole('button',{name:'Masuk ke dashboard'}).click();
 await expect(page.locator('h1')).toHaveText('Ringkasan situs.');
 const hero=(await (await request.get(base+'/api/public/home')).json()).hero;
 const original=hero.headline.id;
 await page.goto(base+`/admin/content/hero/${hero.id}/edit`);
 const headline=page.locator('#enhanced-editor fieldset').filter({has:page.locator('legend', {hasText:/^Headline$/})}).getByLabel('Indonesia',{exact:true});
 const updated=`Headline diperbarui ${testInfo.project.name}`;
 await headline.fill(updated);
 await page.getByRole('button',{name:'Simpan draf',exact:true}).click();
 expect((await (await request.get(base+'/api/public/home')).json()).hero.headline.id).toBe(original);
 await page.getByRole('button',{name:'Publish',exact:true}).click();
 await expect.poll(async()=>{
   const response=await request.get('http://127.0.0.1:4321/');return response.text();
 },{timeout:5000}).toContain(updated);
 await page.goto(base+`/admin/content/hero/${hero.id}/edit`);
 await page.locator('#enhanced-editor fieldset').filter({has:page.locator('legend',{hasText:/^Headline$/})}).getByLabel('Indonesia',{exact:true}).fill(original);
 await page.getByRole('button',{name:'Simpan draf',exact:true}).click();
 await page.getByRole('button',{name:'Publish',exact:true}).click();
 await page.screenshot({path:`../docs/qa-admin-${testInfo.project.name}.png`,fullPage:true});
});
