# Public API

Base `/api`, UTF-8 JSON. Same-origin through Nginx. Read endpoints only serialize published snapshots; signed preview headers are the single explicit exception. Errors do not reveal stack traces or configuration. Read cache: ETag with conditional 304, `max-age=0, s-maxage=3`; Nginx does not cache the API. HTML cache has a separate one-second TTL.

| Method | Route | Result |
|---|---|---|
| GET | `/api/health` | `{status:"ok"}` after a DB round trip |
| GET | `/api/public/home` | settings, enabled nonempty sections in sort order, hero, published featured projects/services/process/about/tech/articles/packages/testimonials/FAQ, safe AI messages, public Turnstile site key |
| GET | `/api/public/projects` | `{items:[...]}` |
| GET | `/api/public/projects/<slug>` | Project and sanitized study HTML, or 404 |
| GET | `/api/public/articles?page=1` | `{items:[...],page,total}`, twelve per page, publication date enforced |
| GET | `/api/public/articles/<slug>` | Published article, sanitized HTML and computed reading time, or 404 |
| GET | `/api/public/sitemap-data` | Published project/article slugs and dates only |
| POST | `/api/public/contact` | Persist lead; 201 `{ok:true}`; honeypot 202 without saving |
| POST | `/api/public/ai/chat` | SSE or a bounded JSON error |

No system prompt, provider key, model allowlist, private knowledge, lead, audit row or administrator is returned by the public home endpoint. A preview token from the authenticated CMS can be sent as `X-Preview-Token` to content GET endpoints; these responses are always private/no-store. Invalid/expired tokens behave as ordinary public reads. Preview URLs are noindex and never enter feeds.

## Contact

```json
{"name":"Visitor","contact":"visitor@example.com","project_type":"CMS option","budget_range":"CMS option","message":"At least ten characters","website":"","turnstile_token":"..."}
```

Exact `Origin` must equal `SITE_URL`; Content-Type must be application/json. Field limits: name 2–100, contact 5–254, message 10–4000. Project/budget values must be present in published CMS options. `website` is the honeypot. Turnstile checks hostname and action `contact`; only explicitly configured development bypasses it. Five attempts/IP/hour. Status 403 for origin/verification, 422 validation, 429 rate. The lead is committed before optional SMTP/Telegram notification. A delivery failure changes its inbox delivery state and does not delete it.

## AI chat

```json
{"message":"Max 500 characters","history":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}],"turnstile_token":"...","session_token":""}
```

The first message requires Turnstile action `ai`. The server returns a signed session token bound to hashed IP; use it on later turns. The metadata session expires after one hour and has at most six accepted turns. Client-provided history is bounded and untrusted; it is never stored. Roles cannot be system/tool. Messages are limited to 500 characters, ten history records and at most 5000 history characters used in a request.

SSE frames:

```text
event: session
data: {"token":"signed-token"}

event: token
data: {"text":"partial answer"}

event: done
data: {}
```

An `error` event with `{code:"offline"}` may occur after streaming begins. Pre-stream errors use JSON `{error:"offline|limit|verify|input|session|origin"}` and appropriate 400/403/422/429/503 statuses. SSE is private/no-store and buffering is disabled. No provider error body is exposed.

The enabled state, kill switch, environment model allowlist, IP allowance and atomic daily budget reservation are checked before provider calls. The environment cap is an upper bound on CMS budget. Usage is an estimate based on conservative input token bounds and reserved output, not provider billing. An explicit injection refusal does not call a provider. There is no endpoint for conversation histories.

## Internal revalidation

`POST /__revalidate` is an Astro endpoint registered through an integration, because Astro ignores underscore-prefixed page files. It requires `Authorization: Bearer REVALIDATE_SECRET` of at least 32 characters and uses a timing-safe comparison. Nginx denies public access; Flask calls the loopback Node port. Response `{revalidated:true}` clears the in-memory content cache. Missing/wrong credentials return 401. Failure falls back to the two-second frontend TTL.

## Admin

`/admin` uses Flask-Login with Argon2, optional encrypted TOTP, temporary login lockouts, CSRF on every mutation, secure cookies in production, and noindex/no-store. Every content payload is validated with its Pydantic schema. Content snapshots are updated atomically by Publish; media validation and backup restore do not execute untrusted scripts. Admin form endpoints are intentionally not a cross-origin JSON management API.
