export type Localized = { id: string; en?: string };
export type Cta = { label: Localized; url: string };
export type CmsImage = { src: string; alt: Localized; width: number; height: number; variants?: { src: string; width: number; format: string }[] };
export type RecordData = { id: number; slug: string; sort_order: number; [key: string]: any }; // Validated by the Python schema at every CMS boundary.
export type Home = {
  settings: RecordData; hero: RecordData; about: RecordData; ai: RecordData;
  sections: RecordData[]; projects: RecordData[]; services: RecordData[]; process: RecordData[];
  stats: RecordData[]; tech: RecordData[]; articles: RecordData[]; pricing: RecordData[];
  testimonials: RecordData[]; faq: RecordData[]; turnstile_site_key: string;
};
export const text = (value?: Localized | string): string => typeof value === 'string' ? value : value?.id || '';
const cache = new Map<string, { until: number; value: unknown }>();
let generation = 0;
export function revalidate() { generation++; cache.clear(); }
export async function cms<T>(path: string, preview = ''): Promise<T> {
  const hit = cache.get(path);
  if (!preview && hit && hit.until > Date.now()) return hit.value as T;
  const currentGeneration = generation;
  const res = await fetch(`${process.env.BACKEND_URL || 'http://127.0.0.1:8000'}/api/public/${path}`, {
    headers: preview ? { 'X-Preview-Token': preview } : {}, signal: AbortSignal.timeout(2500),
  });
  if (!res.ok) throw new Error(`CMS ${res.status}`);
  const value = await res.json() as T;
  if (!preview && generation === currentGeneration) cache.set(path, { until: Date.now() + 2000, value });
  return value;
}
export function whatsapp(settings: RecordData): string {
  return settings.whatsapp_number ? `https://wa.me/${settings.whatsapp_number}?text=${encodeURIComponent(text(settings.whatsapp_message))}` : '';
}
export function primaryUrl(settings: RecordData): string { return whatsapp(settings) || settings.primary_cta?.url || '/#contact'; }
export function absolute(path: string, origin: string): string { return new URL(path || '/', origin).href; }
