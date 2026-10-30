# Vendored administrator assets

Copied from the exact npm packages in `frontend/package-lock.json`:

- HTMX `htmx.org` 2.0.11
- Alpine CSP build `@alpinejs/csp` 3.17.5 (avoids eval under the admin CSP)
- SortableJS 1.15.7
- EasyMDE 2.21.0

All assets are served locally from `/static/vendor/`. License notices are in `licenses/`. EasyMDE's external Font Awesome download and spell checker are disabled; local CSS provides text glyphs. No CDN is required for administrator pages. Cloudflare Turnstile is a separate, explicitly configured public form integration.
