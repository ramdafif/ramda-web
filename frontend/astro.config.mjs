import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import react from '@astrojs/react';
import tailwind from '@tailwindcss/vite';

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [react(), {
    name: 'ramda-internal-revalidation',
    hooks: { 'astro:config:setup': ({ injectRoute }) => injectRoute({ pattern: '/__revalidate', entrypoint: './src/endpoints/revalidate.ts', prerender: false }) },
  }],
  vite: { plugins: [tailwind()], server: { proxy: { '/api': 'http://127.0.0.1:8000', '/admin': 'http://127.0.0.1:8000', '/static': 'http://127.0.0.1:8000', '/uploads': 'http://127.0.0.1:8000' } } },
  server: { host: true, port: 4321 },
  security: { checkOrigin: true },
});
