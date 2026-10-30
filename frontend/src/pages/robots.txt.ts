import type { APIRoute } from 'astro';
export const GET: APIRoute = ({url}) => new Response(`User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api\nDisallow: /__revalidate\nDisallow: /*?preview=\nSitemap: ${process.env.SITE_URL || url.origin}/sitemap.xml\n`, {headers:{'Content-Type':'text/plain; charset=utf-8'}});
