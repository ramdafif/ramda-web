# RAMDA — personal website and content studio

Astro SSR frontend, Flask API and server-rendered CMS, portable SQLAlchemy storage, and a guarded single-model AI demo. This repository is a new implementation on `web-pribadi/NEW`; it does not reuse the old main-branch implementation.

## Requirements

- Python 3.12+, Node 24 LTS, npm, Git.
- SQLite for local work. MySQL 8.4 LTS or a supported MariaDB release for a VPS.
- No Redis, vector database or Docker runtime.
- All Python versions are in `backend/requirements.lock`; JavaScript versions are exact in `frontend/package.json` and its npm lockfile.

## Fresh local setup

Run from the repository root on Linux/macOS (on Windows use the corresponding virtualenv activation or `Scripts/python.exe`):

```bash
cp deploy/.env.example .env
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
npm --prefix frontend ci
```

Set `.env` values. Generate two independent keys locally with `python3 -c 'import secrets; print(secrets.token_hex(32))'` for `SECRET_KEY` and `REVALIDATE_SECRET`. Keep the output private. Use `SITE_URL=http://localhost:4321`, `DATABASE_URL=sqlite:///ramda.sqlite`. Leave `UPLOAD_DIR` blank for the default `backend/instance/uploads` directory. For local form testing only, set `DEV_ALLOW_UNVERIFIED_FORMS=true`. Production ignores that bypass.

```bash
backend/.venv/bin/python -m flask --app backend/wsgi.py db upgrade
backend/.venv/bin/python -m flask --app backend/wsgi.py seed
backend/.venv/bin/python -m flask --app backend/wsgi.py create-admin
npm run dev
```

Open `http://localhost:4321` and `/admin`. The combined development launcher targets Linux/macOS. On Windows, start Flask's development server and Astro in separate terminals with the same environment values, or use VS Code Remote SSH on the Ubuntu VPS. The development server proxies API/admin/uploads to Flask. There is no default administrator or production password. `seed` inserts missing entries and never overwrites existing edits. All 47 initial records are flagged as placeholders; unverified stats are suppressed. Review the seed's project statuses and biography before publishing them as verified facts.

For optional TOTP encryption, generate a Fernet key with `backend/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` and privately assign it to `TOTP_ENCRYPTION_KEY`. Keep that key available for account recovery.

## Content and publication

Content entities are selected by a strict Pydantic schema and stored in `content_item`. Operational models have their own tables. Editors write working data. Publish updates public snapshots in a single transaction and calls `POST /__revalidate` with a secret bearer token. The frontend fetch cache lasts two seconds; the provided Nginx HTML cache lasts one second. Draft preview tokens expire after ten minutes, bypass caches, and never enter sitemap/RSS. Slugs cannot be edited after publication.

Marketing text lives only in `backend/seed/content.json` initially and in the database thereafter. UI labels/status enums live in `frontend/src/i18n/ui.ts`. `node tests/content-boundary.mjs` checks that long seed phrases have not leaked into frontend source. All localized fields support `{id,en}`; the public language toggle is optional Phase 6 and is not enabled here.

The design uses the two supplied logo references, dark surfaces and bronze design tokens. No desktop/mobile website mockup or personal photo was supplied. Empty pricing, testimonials, FAQ, articles and disabled AI sections are omitted, not shown as fake content. Change design tokens in `frontend/src/styles/global.css`.

## Verification

```bash
backend/.venv/bin/ruff check backend/ramda backend/tests
backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run check
node tests/content-boundary.mjs
npm --prefix frontend run build
node tests/run-http-smoke.mjs
cd frontend
npx playwright install --with-deps chromium
npm test
npm run lighthouse
```

The test server creates and removes its own temporary SQLite database. Its known test-only administrator exists only inside that temporary test environment. Do not point it at production. Playwright covers home, a case study, contact, admin login/edit/publish, responsive overflow and axe on mobile/desktop. Lighthouse runs three times on the homepage and Gajiku case study and fails below 95 in any category, LCP above 2 seconds or CLS above 0.05. The workflow also tests migrations/seed/API/rate counters with MySQL. See `docs/VERIFICATION.md` for results and unverified acceptance targets; the existence of CI configuration is not a claim that CI ran.

## AI configuration

1. Configure `AI_PROVIDER=openai_compatible`, the provider's HTTPS `AI_BASE_URL`, one `AI_MODEL`, an `AI_ALLOWED_MODELS` list containing that model, and `AI_API_KEY` in `.env`.
2. Set the provider's actual current input/output prices per million tokens and a hard `AI_DAILY_BUDGET_USD`. Unknown prices are not a reliable budget; configure them before use.
3. Configure Turnstile site/secret keys for the deployed hostname. The first chat message must have action `ai`; contact uses action `contact`.
4. In CMS → Pengaturan AI, select the same allowlisted model, edit messages and suggestions, enable, save and Publish. Publish knowledge documents and accurate project/service content.
5. A kill switch takes effect immediately on the API, before Publish. The UI disappears after publishing the disabled configuration. There is no model dropdown.

BM25 retrieval uses public snapshots only. The provider receives bounded context/history. Visitor messages are untrusted, the assistant never impersonates the owner, and explicit prompt/key extraction requests are blocked before a provider call. The provider prompt is defense in depth, not a guarantee against every possible model behavior. The assistant has no tools and is never given application secrets.

No conversations are stored. AI sessions store a hashed IP, random ID and turn count; usage stores token bounds, reserved cost and outcome. Reservation uses atomic database updates before a provider call. Input UTF-8 bytes plus overhead conservatively bound input tokens; output reservations use the configured output limit. Failed/disconnected requests remain charged to the cap. Dashboard cost is a conservative reservation estimate, not an invoice. A session has at most six turns; IP rates and an environment-capped daily budget apply globally across workers. Run metadata pruning daily.

## Contact and notifications

Add a WhatsApp international number (digits only) and prefilled message in Settings to turn primary CTAs into WhatsApp links. No number means those links and the floating button disappear. Keep the separate contact form enabled with CMS-managed project/budget options.

Enable notifications in CMS Settings only after configuring either `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, or SMTP credentials/from/to addresses. SMTP uses certificate-verified STARTTLS. Lead capture commits before notification delivery; failure never discards the lead. Notification status appears in the inbox. Check actual delivery after deployment; mocked tests do not verify a live mailbox/bot.

Analytics is opt-in: set an HTTPS script URL and site ID in CMS, and the same origin in `.env` `ANALYTICS_ORIGIN`. The CSP only permits that environment-approved origin. Use Umami, or Plausible with the correct script/site configuration for your installation. No analytics request is made when unset. `data-track` values cover CTA clicks; successful forms emit `contact-submit`.

## Ubuntu VPS runbook

The example units use `/srv/ramda`, service user `ramda`, group `www-data`, Python 3.12 and Node at `/usr/bin/node`. On Ubuntu 22.04, arrange a supported Python 3.12 installation first; its default Python 3.10 is insufficient. Install Node 24 LTS, Nginx, certbot, `python3.12-venv`, a MySQL client, and a supported database through trusted OS/vendor repositories. This repository does not modify another application or install system packages automatically.

1. Create user `ramda`, clone this branch to `/srv/ramda`, and install the pinned dependencies. Set ownership to `ramda:www-data`. Create `backend/instance`, `frontend/.astro`, `var/uploads`, `var/backups`.
2. Create database `ramda` with `utf8mb4`. Create a localhost-only runtime DB account with SELECT/INSERT/UPDATE/DELETE on `ramda.*`; a separate migration account may have schema privileges on this one database. Configure runtime `DATABASE_URL=mysql+pymysql://.../ramda?charset=utf8mb4`. Use URL-encoded passwords. Set `MIGRATION_DATABASE_URL` for deploy-time schema changes if using separate accounts.
3. Put `.env` in the repo root, owned by the service user with mode 600. Set `APP_ENV=production`, the actual HTTPS `SITE_URL`, `UPLOAD_DIR=/srv/ramda/var/uploads`, `BACKEND_URL=http://127.0.0.1:8000`, the revalidation URL/secret and integration keys. Never place `.env` under the public directory. Set uploads directories to 750 and media to 640 so Nginx can read them through group `www-data`.
4. Run migrations, seed once, create the first administrator, and build the frontend. Review seed placeholders. Subsequent deploys migrate but do not reseed.
5. Copy the two service files to `/etc/systemd/system`, verify the Node path, then `sudo systemctl daemon-reload` and `sudo systemctl enable --now ramda-backend ramda-frontend`.
6. Replace `ramda.example.com` in the Nginx templates with the real domain. Use the HTTP bootstrap config first, create `/var/www/certbot`, validate with `nginx -t`, and reload Nginx. Issue the certificate using `certbot certonly --webroot -w /var/www/certbot -d YOUR_DOMAIN`.
7. Install `deploy/nginx.conf`, verify paths/certificate names with `nginx -t`, and reload. Ensure `/var/cache/nginx/ramda` is writable by the Nginx service user. The config uses the older-compatible `listen ... ssl http2` syntax. Current Nginx versions may print a deprecation notice; it remains compatible with the user's Ubuntu 22.04 Nginx. Test `certbot renew --dry-run` and enable renewal.
8. gzip works with standard Nginx. Brotli requires a compatible module supplied by the selected Nginx distribution; after loading it, install `deploy/brotli.conf.example` as `/etc/nginx/snippets/ramda-brotli.conf`. Do not enable unsupported directives. Brotli is optional until the module is installed; this environment did not validate it.
9. Restrict inbound traffic to SSH and HTTPS/HTTP as needed. The app services bind only to loopback. Configure the firewall according to the VPS's existing SSH access. Cloudflare is optional; do not force-cache dynamic HTML, preview, admin, API or SSE. If restoring client IPs through Cloudflare, use only Cloudflare's current trusted proxy ranges in Nginx, never arbitrary X-Forwarded-For.
10. Install `deploy/ramda.cron` for the service user. Replicate encrypted backups off-host. Run a restore drill, verify backup retention, notifications, live Turnstile, AI budgets and mobile Lighthouse against the real HTTPS site before release.

Subsequent deployments: run `deploy/deploy.sh` as the deployment user with narrowly scoped permission to restart only the two services. It rejects a dirty checkout or any branch other than `web-pribadi/NEW`, pulls with fast-forward only, installs lockfiles, builds, migrates, restarts and checks both loopback endpoints. It does not run a deployment from this task. Review backups before schema changes.

## Backups and recovery

CMS exports JSON content and a separate uploads ZIP. Import JSON as working data, restore uploads through the validated ZIP form, inspect previews and Publish. Portable CMS export excludes passwords, environment secrets and leads. Lead CSV export is separate and escapes spreadsheet formulas.

`deploy/backup.sh` uses SQLite's backup API or transactional `mysqldump` plus uploads in a mode-600 tar archive. MySQL passwords are passed in a temporary mode-600 defaults file, never process arguments. Retention defaults to 14 days via `BACKUP_RETENTION_DAYS`.

For a full restore: stop the two services, extract the archive to a private staging directory, inspect members, restore `database.sql` through the MySQL client or replace SQLite with `database.sqlite`, restore uploads with correct group/permissions, run migrations, restart and run the health check. Preserve the original `.env`; it is intentionally absent from backups. Use the same TOTP encryption key or reset 2FA through an authenticated recovery procedure. Do not extract untrusted archives directly over the application.

Troubleshoot with `journalctl -u ramda-backend -u ramda-frontend`, `nginx -t`, Nginx error logs and `/api/health`. The provided Nginx access format omits query strings so draft preview tokens are not written there. Logs must not contain provider keys or form bodies.

Idle RAM below roughly 400 MB excluding the database is a target, not an unmeasured guarantee. The units use one threaded gunicorn worker and one Node process; no Redis/vector service. Their memory limits protect the host. Measure idle and AI-stream/upload peaks on the actual VPS before tuning.
