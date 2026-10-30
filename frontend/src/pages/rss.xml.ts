import type { APIRoute } from 'astro';
import { cms, text, type Home, type RecordData } from '../lib/cms';
import { xml } from '../lib/seo';
export const GET: APIRoute = async ({url}) => {
  const origin = process.env.SITE_URL || url.origin;
  const home = await cms<Home>('home');
  const data = await cms<{items:RecordData[]}>('articles?page=1');
  const body = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>${xml(home.settings.brand_name)}</title><link>${xml(origin)}</link><description>${xml(text(home.settings.seo_description))}</description><language>id</language>${data.items.map(a=>`<item><title>${xml(text(a.title))}</title><link>${xml(`${origin}/articles/${a.slug}`)}</link><guid>${xml(`${origin}/articles/${a.slug}`)}</guid><description>${xml(text(a.excerpt))}</description><pubDate>${new Date(a.published_at).toUTCString()}</pubDate></item>`).join('')}</channel></rss>`;
  return new Response(body,{headers:{'Content-Type':'application/rss+xml; charset=utf-8'}});
};
