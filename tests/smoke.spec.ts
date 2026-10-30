import { test, expect } from '../frontend/node_modules/@playwright/test';
import AxeBuilder from '../frontend/node_modules/@axe-core/playwright';

test('homepage: CMS content, honest visibility, responsive layout and axe',async({page},testInfo)=>{
 await page.goto('/');
 await expect(page.locator('h1')).toContainText('Teknologi');
 await expect(page.locator('#projects .project-card')).toHaveCount(4);
 for(const selector of ['#ai','#articles','#pricing','#testimonials','#faq','.stats'])await expect(page.locator(selector)).toHaveCount(0);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 expect(overflow).toBe(false);
 const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
 expect(results.violations).toEqual([]);
 await page.screenshot({path:`../docs/qa-home-${testInfo.project.name}.png`,fullPage:true});
});

test('project, metadata, feeds, 404 and draft isolation',async({page,request})=>{
 await page.goto('/projects/gajiku');
 await expect(page.locator('h1')).toHaveText('Gajiku');
 await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content',/Gajiku/);
 await expect(page.locator('script[type="application/ld+json"]')).toHaveCount(4);
 expect((await request.get('/rss.xml')).status()).toBe(200);
 expect((await request.get('/sitemap.xml')).status()).toBe(200);
 expect((await request.get('/robots.txt')).status()).toBe(200);
 expect((await request.get('/articles/catatan-1')).status()).toBe(404);
 const notFound=await page.goto('/missing-page');expect(notFound?.status()).toBe(404);
 await expect(page.locator('h1')).toHaveText('Halaman tidak ditemukan');
 await page.goto('/projects/gajiku');
 const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
 expect(results.violations).toEqual([]);
});

test('contact form saves validated lead',async({page})=>{
 await page.goto('/#contact');
 await page.getByLabel('Nama',{exact:true}).fill('E2E Visitor');
 await page.getByLabel('Email / WhatsApp').fill('visitor@example.test');
 await page.getByLabel('Jenis proyek').selectOption('Website & Landing Page');
 await page.getByLabel('Kisaran anggaran').selectOption('Belum ditentukan');
 await page.getByLabel('Ceritakan kebutuhan Anda').fill('Saya ingin membuat website perusahaan.');
 await page.getByRole('button',{name:'Kirim pesan'}).click();
 await expect(page.locator('.form-status')).toContainText('Pesan Anda sudah diterima');
});
