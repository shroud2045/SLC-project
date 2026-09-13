# Deployment Guide — Shroud's Lockin Crib (SLC)

This guide covers deploying SLC to **Render.com** with a persistent PostgreSQL
database, and also includes a VPS/NGINX option for self-hosted deployments.

---

## Production Architecture

```
Browser → HTTPS → Render Web Service (Gunicorn + Flask)
                         ↓
              Render PostgreSQL Database
              (persistent, survives restarts)
```

- **Application server**: Gunicorn (multi-worker)
- **Database**: Render PostgreSQL (external, persistent)
- **Migrations**: Flask-Migrate / Alembic (`flask --app manage.py db upgrade`)
- **Static data**: Seeded idempotently on first deploy

---

## Option A: Render.com (Recommended)

### Step 1 — Create a Render PostgreSQL Database

1. Go to [render.com](https://render.com) → **New** → **PostgreSQL**
2. Give it a name (e.g. `slcdb`) and choose a region
3. Click **Create Database**
4. On the database info page, copy the **Internal Database URL**
   - It looks like: `postgresql://user:password@dpg-xxxx.oregon-postgres.render.com/slcdb`
   - Render may show it as `postgres://...` — the app converts this automatically

### Step 2 — Create a Render Web Service

1. Go to **New** → **Web Service** → Connect your GitHub repo
2. Configure:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`

### Step 3 — Set Environment Variables

In the Render web service → **Environment** tab, add:

| Variable | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `False` |
| `SECRET_KEY` | `<64-char hex — see below>` |
| `DATABASE_URL` | `<Internal Database URL from Step 1>` |
| `SESSION_COOKIE_SECURE` | `True` |
| `UPLOAD_FOLDER` | `uploads` |
| `MAX_CONTENT_LENGTH` | `16777216` |
| `AI_PROVIDER` | `heuristic` |

**Generate SECRET_KEY** (run locally):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **NEVER** use the default `SECRET_KEY` from `.env` in production.

### Step 4 — Deploy

Push to GitHub. Render auto-deploys on push.

### Step 5 — Run Database Migration (First Deploy Only)

In the Render web service → **Shell** tab:

```bash
flask --app manage.py db upgrade
```

This creates all tables in PostgreSQL. **Never use `db.create_all()` or `db.drop_all()`.**

### Step 6 — Seed Static Data

```bash
flask --app manage.py seed
```

Seeds achievement badges and moderation filter rules. Safe to run multiple times.

### Step 7 — (Optional) Create Admin Account

```bash
flask --app manage.py create-admin
```

### Step 8 — Verify Database

```bash
flask --app manage.py db-check
```

Expected output:
```
=== SLC Database Health Check ===
  Dialect  : postgresql
  Host     : dpg-xxxx.oregon-postgres.render.com
  Database : slcdb
  Status   : CONNECTED ✓
```

---

## Final Render Deployment Summary

| Setting | Value |
|---|---|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn run:app` |
| **Migration Command** | `flask --app manage.py db upgrade` |
| **Seed Command** | `flask --app manage.py seed` |
| **Health Check** | `flask --app manage.py db-check` |

---

## Updating the Application

Every subsequent deployment runs automatically via git push. After pushing:

```bash
# Render runs this automatically on each deploy:
pip install -r requirements.txt

# If you added new models, run in Render Shell:
flask --app manage.py db upgrade
```

**`db upgrade` is always safe to re-run** — it's idempotent. It only applies
migrations not yet applied to the database.

---

## Database Persistence Guarantees

| Event | Data preserved? |
|---|---|
| Application restart | ✅ Yes — PostgreSQL is external |
| New Render deployment | ✅ Yes — DB is not wiped |
| Server crash | ✅ Yes — PostgreSQL persists independently |
| New user registers | ✅ Yes — written to PostgreSQL immediately |
| User earns badge | ✅ Yes — stored in `user_badges` table |
| Timer session completed | ✅ Yes — stored in `timer_sessions` table |

---

## Environment Variables Reference

```
# Required
SECRET_KEY=<64-char-random-hex>
DATABASE_URL=postgresql://user:pass@host/dbname
FLASK_ENV=production

# Optional — defaults shown
FLASK_DEBUG=False
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=png,jpg,jpeg,webp,gif
UPLOAD_FOLDER=uploads
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME_DAYS=7
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/minute
RATE_LIMIT_CHAT=1/second
RATE_LIMIT_AI=10/minute
AI_PROVIDER=heuristic
OPENAI_API_KEY=         # optional: 'openai' provider
GEMINI_API_KEY=         # optional: 'gemini' provider
```

---

## Option B: VPS/NGINX (Self-Hosted)

### 1. System Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv postgresql postgresql-contrib nginx git

# Create service user
sudo useradd -m -s /bin/bash slc
sudo su - slc
```

### 2. PostgreSQL Setup

```bash
sudo -u postgres psql -c "CREATE USER slcuser WITH PASSWORD 'strongpassword';"
sudo -u postgres psql -c "CREATE DATABASE slcdb OWNER slcuser;"
```

### 3. Application Setup

```bash
git clone https://github.com/shroud2045/SLC-project.git
cd SLC-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.render .env
nano .env  # Set SECRET_KEY, DATABASE_URL=postgresql://slcuser:strongpassword@localhost/slcdb
```

### 4. Database Initialization

```bash
flask --app manage.py db upgrade
flask --app manage.py seed
flask --app manage.py create-admin
flask --app manage.py db-check   # verify
```

### 5. Gunicorn systemd Service

```ini
# /etc/systemd/system/slc.service
[Unit]
Description=Shroud's Lockin Crib — Flask Application
After=network.target postgresql.service

[Service]
User=slc
Group=www-data
WorkingDirectory=/home/slc/SLC-project
Environment="PATH=/home/slc/SLC-project/venv/bin"
EnvironmentFile=/home/slc/SLC-project/.env
ExecStart=/home/slc/SLC-project/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 3 \
    --timeout 60 \
    run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable slc
sudo systemctl start slc
```

### 6. NGINX Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 16M;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/slc/SLC-project/app/static/;
        expires 7d;
    }
}
```

### 7. HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Management Commands Reference

```bash
# Check DB connectivity (never prints passwords)
flask --app manage.py db-check

# Apply all pending migrations
flask --app manage.py db upgrade

# Seed static data (badges, filters) — idempotent
flask --app manage.py seed

# First-deploy: upgrade + seed in one step
flask --app manage.py init-db

# Create admin account interactively
flask --app manage.py create-admin

# Generate a new migration after model changes
flask --app manage.py db migrate -m "description of change"
```
