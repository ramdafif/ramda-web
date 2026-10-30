# Verification — 30 October 2026

Implementation includes Phases 1–5. Optional Phase 6 (public EN toggle) is not included; localized schemas are present.

| Check | Observed result |
|---|---|
| Python tests | **46 passed**: models/public API, draft/public boundary, ETags, seed idempotency, auth/CSRF/login throttles, encrypted TOTP/replay, all editors, media/EXIF/SVG, reorder, backup validation/traversal, contact/notifications, AI inputs/turns/kill switch/injection rejection/retrieval, concurrent IP counters and budget reservations |
| Python lint | Ruff passed |
| Astro/TypeScript | `astro check`: 0 errors, 0 warnings, 0 hints |
| JavaScript/TypeScript lint | ESLint passed |
| Astro production build | Passed, Node standalone SSR |
| Migrations | Fresh initial migration and upgrade of an existing 47-record SQLite seed passed; `flask db check` finds no schema changes |
| CMS copy boundary | Passed: long seed marketing phrases absent from frontend source outside i18n |
| Compiled SSR HTTP smoke | Passed: home/projects/case study/articles/RSS/sitemap/robots; real 404s and draft isolation; protected revalidation; authenticated CSRF login/edit/publish; form save and inbox |
| Publish propagation | Latest measured compiled SSR update **45 ms** locally; independent runs ranged from 44 to 67 ms. This is loopback evidence, not a production network benchmark |
| Python audit | `pip-audit -r backend/requirements.lock`: no known vulnerabilities |
| npm audit | Full dependency tree including development packages: zero vulnerabilities after replacing old LHCI CLI with current Lighthouse APIs |
| Playwright discovery | 8 tests discovered: 4 scenarios × desktop/mobile |
| Playwright/axe execution | **Blocked, not passed.** Chromium download returned an empty/invalid ZIP; a direct test run stopped before opening a page because the Chromium executable is absent |
| Lighthouse 95+ / LCP / CLS | **Unverified.** Browser unavailable. CI runner enforces 95 in all four categories, mobile LCP ≤2s, CLS ≤0.05 on home and Gajiku case study |
| MySQL/MariaDB runtime | Portable schema and a MySQL CI service check are supplied. A live local MySQL/MariaDB server was not available for execution |
| Live provider/Turnstile/Telegram/SMTP | Not configured in this task. Adapter and mocked tests pass; real-domain verification/delivery remain deployment checks |
| VPS/Nginx/systemd/TLS/Brotli | Files/runbook supplied; shell/Python syntax checked. No user's VPS was modified, and Nginx/Brotli/systemd were not executed here |
| RAM target | Lightweight process architecture and service limits supplied; production idle/peak RSS remains to be measured on the real VPS |
| GitHub Actions | Workflow supplied with current official Actions pinned to commit SHAs. No claim of a remote green run: source push is blocked |
| GitHub push | Git CLI has no shell credential; authenticated GitHub write returned **403 Resource not accessible by integration**. No remote branch or main-branch content was modified |

The code is not presented as having met every production acceptance criterion. Browser, deployment and live integration checks above must pass before a production readiness claim.

## Phase history

- Foundation: new independent root, portable schema/migration/seed/API/SSR homepage; 9 tests and build passed.
- Admin: secure content studio, typed editors, media, reorder, preview, publish and backups; 19 tests and build passed.
- Conversion: contact/leads/notifications and guarded streaming AI; 35 tests and build passed.
- Content: index/detail pages, structured SEO and feeds; 38 tests and build passed.
- Hardening/deploy: public verification snapshots, concurrent safety tests, current dependency audits, compiled SSR smoke, CI/deploy/backup/runbooks; 46 tests and build passed. Browser acceptance is blocked as described above.
