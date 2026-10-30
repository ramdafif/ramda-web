import { defineMiddleware } from 'astro:middleware';
import { createHash, randomBytes } from 'node:crypto';

export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();
  const nonce = randomBytes(18).toString('base64');
  const headers = new Headers(response.headers);
  const analytics = process.env.ANALYTICS_ORIGIN || '';
  let trustedAnalytics = '';
  try { trustedAnalytics = analytics ? new URL(analytics).origin : ''; } catch { /* fail closed */ }
  headers.set('Content-Security-Policy', `default-src 'self'; script-src 'self' 'nonce-${nonce}' https://challenges.cloudflare.com ${trustedAnalytics}; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ${trustedAnalytics}; frame-src https://challenges.cloudflare.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`);
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  const preview = context.url.searchParams.has('preview');
  if (preview) headers.set('X-Robots-Tag', 'noindex,nofollow');
  headers.set('Cache-Control', preview || context.url.pathname === '/__revalidate' || response.status !== 200 ? 'private, no-store' : 'public, max-age=0, s-maxage=1, must-revalidate');
  if (headers.get('Content-Type')?.includes('text/html')) {
    const html = (await response.text()).replace(/<script\b([^>]*)>/gi, (tag, attributes: string) => /\bsrc\s*=/i.test(attributes) ? tag : `<script nonce="${nonce}"${attributes}>`);
    headers.set('ETag', `"${createHash('sha256').update(html).digest('hex')}"`);
    headers.delete('Content-Length');
    return new Response(html, { status: response.status, statusText: response.statusText, headers });
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
});
