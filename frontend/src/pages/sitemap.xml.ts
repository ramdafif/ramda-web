import type { APIRoute } from 'astro';
import { cms } from '../lib/cms';
import { xml } from '../lib/seo';
export const GET: APIRoute = async ({url}) => {
  const origin = process.env.SITE_URL || url.origin;
  const data = await cms<{projects:{slug:string}[];articles:{slug:string;published_at:string}[]}>('sitemap-data');
  const paths = ['/', '/projects', '/articles', ...data.projects.map(p=>`/projects/${p.slug}`), ...data.articles.map(a=>`/articles/${a.slug}`)];
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${paths.map(path=>`<url><loc>${xml(new URL(path,origin).href)}</loc></url>`).join('')}</urlset>`,{headers:{'Content-Type':'application/xml; charset=utf-8'}});
};
