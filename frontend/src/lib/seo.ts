import type { Home, RecordData } from './cms';
import { text } from './cms';
export function identity(home: Home, origin: string) {
  return [
    { '@context': 'https://schema.org', '@type': 'Person', '@id': `${origin}/#person`, name: home.about.name, jobTitle: text(home.about.role), url: origin, sameAs: Object.values(home.settings.social_links || {}).filter(Boolean) },
    { '@context': 'https://schema.org', '@type': 'Organization', '@id': `${origin}/#organization`, name: home.settings.brand_name, url: origin, founder: { '@id': `${origin}/#person` } },
  ];
}
export function breadcrumbs(parts: { name: string; path: string }[], origin: string) {
  return { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: parts.map((part, i) => ({ '@type': 'ListItem', position: i + 1, name: part.name, item: new URL(part.path, origin).href })) };
}
export function creativeWork(project: RecordData, origin: string) {
  return { '@context': 'https://schema.org', '@type': 'CreativeWork', name: text(project.title), description: text(project.summary), url: `${origin}/projects/${project.slug}`, keywords: project.stack_tags?.join(', '), creator: { '@id': `${origin}/#person` }, ...(project.cover?.src ? { image: new URL(project.cover.src, origin).href } : {}) };
}
export const xml = (value: string) => value.replace(/[<>&"']/g, char => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[char]!);
