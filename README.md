# Shroud's Lockin Crib 🔥

> **Lock In. Build Your Streak. Dominate Your Goals.**

A full-stack productivity and self-improvement web application built with Flask, SQLite, and a security-first architecture. Track your daily lock-in sessions, build a streak, earn badges, join challenges, connect with the community, and get AI-powered study plans.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [CLI Commands](#cli-commands)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Security](#security)

---

## Features

| Feature | Description |
|---|---|
| 🔐 Authentication | Register / login / logout with strong password policy (8+ chars, upper/lower/number/symbol) |
| 🔥 Streak Engine | Deterministic consecutive-day streak calculation from daily log dates |
| 📝 Lock-In Posts | Daily progress logs with privacy controls (PRIVATE / COMMUNITY) |
| ⏱️ Focus Timer | Pomodoro and custom timer with server-side session validation (rejects spoofed durations) |
| 🏆 Badge System | 23+ deterministic achievement badges (1→500 day streaks, hours milestones, first actions) |
| 🎯 Challenges | Community challenges with time-boxed goals and completion tracking |
| 🌍 Community Feed | Public lock-in posts with fire/clap/rocket reactions and comments |
| 💬 Live Chat | Real-time chatroom with long-polling, moderation filter integration |
| 🤖 AI Assistant | Offline heuristic + optional OpenAI/Gemini study planner |
| 🛡️ Admin Panel | User management, report resolution, word filter rules, badge/challenge creator, audit logs |
| 📁 Secure Uploads | Pillow-verified, EXIF-stripped, UUID WebP re-encoded avatar + proof image uploads |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, Flask 3.x |
| ORM | Flask-SQLAlchemy 3.x, SQLAlchemy 2.x |
| Database | SQLite (dev) / PostgreSQL (prod) via `psycopg[binary]` |
| Auth | Session-based, `werkzeug.security` pbkdf2-sha256 password hashing |
| CSRF | Flask-WTF |
| Images | Pillow — magic byte inspection, EXIF stripping, WebP conversion |
| Security | OWASP headers, CSP, X-Frame-Options, Referrer-Policy |
| Testing | pytest, pytest-flask (29 tests, 100% pass rate) |
| Deploy | Gunicorn + systemd, NGINX reverse proxy, optional Render/Railway |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/shroud2045/SLC-project.git
cd SLC-project

# 2. Create virtual environment
python3.14 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env
# Edit .env and set a strong SECRET_KEY at minimum

# 5. Initialise database, seed badges and content filters
python manage.py init-db

# 6. Create your admin account (never stored in code)
python manage.py create-admin

# 7. Run development server
python run.py
# Open http://127.0.0.1:5000
```

---

## Environment Variables

Copy `.env.example` → `.env` and fill in the values.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask session secret (use a 32+ byte random hex string) |
| `DATABASE_URL` | Optional | PostgreSQL URL for production. Defaults to SQLite for dev. |
| `UPLOAD_FOLDER` | Optional | Absolute path for uploaded files. Defaults to `uploads/` |
| `MAX_CONTENT_LENGTH` | Optional | Max upload size in bytes (default 5MB) |
| `OPENAI_API_KEY` | Optional | Enable GPT-powered study plans in the AI assistant |
| `GEMINI_API_KEY` | Optional | Enable Gemini-powered study plans in the AI assistant |
| `FLASK_ENV` | Optional | `development` / `production` |
| `FLASK_DEBUG` | Optional | `1` for debug mode (never in production) |

Generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## CLI Commands

All commands run via `python manage.py <command>`:

| Command | Description |
|---|---|
| `init-db` | Creates all tables, seeds 23 badges and default content filter rules |
| `create-admin` | Interactive prompt to create an admin account (password never in code) |
| `seed-badges` | Re-seeds badge catalog (safe to re-run, skips existing slugs) |

---

## Running Tests

```bash
# Run the full suite (29 tests)
./venv/bin/pytest -v

# Run a specific file
./venv/bin/pytest -v tests/test_security_owasp.py

# Run with coverage report
./venv/bin/pytest --cov=app --cov-report=term-missing
```

**Test coverage areas:**
- Auth: registration, login, session, suspended users, password policy
- Posts + Privacy: IDOR protection, community feed isolation, access control
- Timer: valid sessions, spoofed duration rejection, future timestamp rejection
- Streaks: consecutive day logic, reset after gaps, longest streak preservation
- Badges: first log, hours milestones, duplicate prevention
- Community & Chat: comments, reactions, muted user enforcement
- Moderation: content filter service, post rejection with blocked language
- Admin RBAC: regular user blocked from admin, admin actions + audit logging
- Security OWASP: SQLi resilience, XSS output escaping, security headers
- Uploads: valid image, invalid extension, fake magic bytes rejection

---

## Project Structure

```
SLC-project/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── config.py            # Dev / Test / Prod configs
│   ├── extensions.py        # Flask extensions (db, migrate, csrf)
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py          # User, Role enum
│   │   ├── post.py          # LockInPost, PostPrivacy, ProgressImage
│   │   ├── timer.py         # TimerSession
│   │   ├── badge.py         # Badge, UserBadge
│   │   ├── challenge.py     # Challenge, UserChallenge
│   │   ├── community.py     # Comment, PostReaction
│   │   ├── chat.py          # ChatMessage
│   │   ├── moderation.py    # BannedWord, Report
│   │   └── audit.py         # AuditLog, AuditAction
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py      # Registration, login, password policy
│   │   ├── upload_service.py    # Image sanitization pipeline
│   │   ├── streak_service.py    # Streak + hours calculation engine
│   │   ├── badge_service.py     # Badge seeding + deterministic evaluation
│   │   ├── moderation_service.py# Content filter (BLOCK/FLAG/WARN)
│   │   ├── ai_service.py        # Heuristic + API study planner
│   │   └── audit_service.py     # Admin action logging
│   ├── routes/              # Flask blueprints
│   │   ├── auth.py, main.py, dashboard.py, posts.py
│   │   ├── timer.py, badges.py, challenges.py
│   │   ├── community.py, chat.py, profile.py
│   │   ├── ai.py, admin.py, uploads.py, errors.py
│   ├── utils/
│   │   ├── decorators.py    # @login_required, @role_required, @rate_limit
│   │   ├── security.py      # OWASP security headers
│   │   └── helpers.py       # Time formatting, mindset archetypes
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, SVG assets
├── tests/                   # pytest test suite (29 tests)
├── manage.py                # Click CLI (init-db, create-admin, seed-badges)
├── run.py                   # Development entrypoint
├── requirements.txt
├── pytest.ini
├── .env.example
└── DEPLOYMENT.md
```

---

## Security

See [SECURITY.md](SECURITY.md) for the full threat model, controls, and disclosure process.

Key properties:
- **Object-level authorization** on every protected resource — no frontend-only hiding
- **Parametrized ORM queries** — no raw SQL, SQLi-resistant by design
- **Jinja2 auto-escaping** — XSS prevented at the template engine level
- **OWASP security headers** on every response
- **Server-side timer validation** — spoofed client durations are rejected
- **Secure image upload pipeline** — magic byte inspection, EXIF stripping, WebP re-encode

---

*Built with discipline & Python. — shroud2045*
