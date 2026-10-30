import type { APIRoute } from 'astro';
import { timingSafeEqual } from 'node:crypto';
import { revalidate } from '../lib/cms';
export const POST: APIRoute = async ({ request }) => {
  const expected = process.env.REVALIDATE_SECRET || '';
  const supplied = request.headers.get('Authorization')?.replace(/^Bearer /, '') || '';
  if (expected.length < 32 || Buffer.byteLength(supplied) !== Buffer.byteLength(expected) || !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) return new Response(null, { status: 401, headers: { 'Cache-Control': 'no-store' } });
  revalidate();
  return Response.json({ revalidated: true }, { headers: { 'Cache-Control': 'no-store' } });
};
