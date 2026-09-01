# Security Policy — Shroud's Lockin Crib

## Supported Versions

| Version | Security Support |
|---------|-----------------|
| `main` branch | ✅ Actively maintained |
| Older tags | ❌ Not supported |

---

## Threat Model

This application is a personal/community productivity web app. The primary threat actors considered are:

1. **Malicious registered users** — attempting to view other users' private posts, manipulate their own streak/badge data, or send abusive messages.
2. **Unauthenticated attackers** — attempting to enumerate accounts, bypass auth, or scrape private content.
3. **Moderators** — must not be able to access admin-only functions (badge/challenge management, audit logs).
4. **Upload exploits** — attempting to upload malicious files (webshells, polyglot images, oversized files).

---

## Implemented Security Controls

### 1. Authentication & Session Management
- **Password Policy**: minimum 8 characters, must contain uppercase, lowercase, number, and special symbol — enforced server-side in `AuthService.validate_password_strength()`.
- **Hashing**: `werkzeug.security.generate_password_hash` using `pbkdf2:sha256` — no plaintext passwords stored anywhere.
- **Session**: Flask server-side signed session cookies (`SECRET_KEY`). Session is cleared on logout and on every request if the user is no longer active.
- **Account enumeration prevention**: Login errors use generic messaging ("Invalid credentials") regardless of whether the username or password was wrong.
- **Suspended user enforcement**: `authenticate_user()` reloads the user from DB fresh on every login attempt — a suspended user cannot log in even if already in session.

### 2. Authorization — Object-Level Access Control (IDOR Prevention)
Every protected resource enforces **object-level authorization** in the route handler, not just by hiding UI buttons:

| Resource | Authorization Rule |
|---|---|
| `LockInPost` | `post.can_view(user)` — COMMUNITY posts are public; PRIVATE requires ownership or mod/admin role |
| `LockInPost` edit/delete | `post.can_edit(user)` / `post.can_delete(user)` — owner or admin only |
| File uploads | `/uploads/<filename>` route checks post or avatar ownership before serving |
| Timer sessions | Only the owning user's sessions are returned in their dashboard |
| Admin endpoints | `@role_required(['ADMIN', 'MODERATOR'])` decorator — HTTP 403 returned for unauthorized roles |
| Audit logs | `@role_required(['ADMIN'])` only — moderators cannot view |

Tests: `test_posts_privacy.py::test_idor_private_post_protection` — verifies 403 for view, edit, and delete attempts from a different authenticated user.

### 3. SQL Injection Prevention
- All database queries use **Flask-SQLAlchemy ORM** with parametrized statements.
- No raw `db.engine.execute()` or f-string SQL anywhere in the codebase.
- Tested: `test_security_owasp.py::test_sqli_payload_resilience` — classic SQLi payloads (`' OR '1'='1`, `UNION SELECT`, etc.) in login form do not cause 500 errors or bypass auth.

### 4. Cross-Site Scripting (XSS) Prevention
- **Jinja2 auto-escaping** is enabled globally (`autoescape=True` default for `.html` templates).
- No `{{ var | safe }}` or `Markup()` used with user-controlled input.
- Tested: `test_security_owasp.py::test_xss_output_escaping` — `<script>alert("PWNED_XSS")</script>` submitted in post content is rendered as `&lt;script&gt;...` in the HTML response — never executable.

### 5. CSRF Protection
- Flask-WTF CSRF protection enabled globally via `WTF_CSRF_ENABLED = True`.
- Every state-changing form includes `{{ csrf_token() }}` hidden input.
- AJAX endpoints check the `X-CSRFToken` header.

### 6. Security Headers (OWASP)
Applied on every response via `app/utils/security.py`:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` |
| `Content-Security-Policy` | Strict CSP — `default-src 'self'`, nonces for inline scripts |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disables camera, microphone, geolocation |

Tested: `test_security_owasp.py::test_security_headers_present`.

### 7. Secure File Uploads
Pipeline in `app/services/upload_service.py`:

1. **Extension allowlist** — only `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` accepted.
2. **Magic byte inspection** — file signature bytes (e.g. `\x89PNG`, `\xff\xd8\xff`) verified regardless of extension to detect polyglot/renamed executables.
3. **Pillow image verification** — `Image.verify()` called to ensure parseable image data.
4. **EXIF stripping** — metadata (GPS location, device model, camera serial) removed by re-encoding through Pillow.
5. **UUID filename** — original filename discarded; saved as `<uuid4>.webp` to prevent path traversal.
6. **Size limits** — `MAX_CONTENT_LENGTH` enforced at Flask level (default 5MB).
7. **IDOR prevention** — upload serving route checks ownership before `send_from_directory`.

Tested: `test_uploads.py` (valid upload, invalid extension, fake magic bytes).

### 8. Rate Limiting
`@rate_limit(limit=5, window=60)` decorator applied to:
- `POST /auth/login` — 5 attempts per minute per IP
- `POST /auth/register` — 5 attempts per minute per IP

### 9. Content Moderation
Server-side `ModerationService` evaluates all user-submitted text (posts, comments, chat):
- **BLOCK** — submission rejected outright (abusive/threatening language)
- **FLAG** — logged for moderator review, submission passes
- **WARN** — content masked with `***`

AI assistant **cannot grant badges** — badge evaluation is 100% deterministic from the server-side `BadgeService`.

### 10. Admin & Audit Trail
- `AuditLog` table records every admin/moderator action with timestamp, admin ID, target type/ID, IP address, and action details.
- Audit logs are append-only — no delete endpoint exists.
- Admins cannot delete their own account or audit log entries.

---

## Responsible Disclosure

If you discover a security vulnerability, please:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Email details privately to the project maintainer.
3. Include steps to reproduce, impact assessment, and suggested fix if possible.
4. Allow reasonable time for the issue to be fixed before public disclosure.

---

## Known Limitations (Non-Production Notes)

- This is a learning/portfolio project. For production deployment, consider adding:
  - HTTPS/TLS termination at NGINX or Cloudflare level
  - Redis-backed sessions instead of cookie sessions for scalability
  - Full audit log immutability via append-only database or WORM storage
  - Automated dependency scanning (Dependabot / Snyk)
  - WAF (Web Application Firewall) in front of the application
