# Deployment Guide — Shroud's Lockin Crib

This guide covers deploying SLC to a Linux VPS (Ubuntu 22.04+) with Gunicorn + NGINX, and also includes a quick Render.com / Railway cloud option.

---

## Option A: VPS Deployment (Ubuntu + NGINX + Gunicorn)

### 1. Server Setup

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3.12 python3.12-venv python3-pip nginx git

# Create a dedicated service user (no root privileges)
sudo useradd -m -s /bin/bash slc
sudo su - slc
```

### 2. Clone and Configure

```bash
# As the slc user
git clone https://github.com/shroud2045/SLC-project.git
cd SLC-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Set SECRET_KEY, DATABASE_URL, etc.
```

**Generate a production SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Database Initialisation

**SQLite (simple, single-server):**
```bash
python manage.py init-db
python manage.py create-admin
```

**PostgreSQL (recommended for production):**
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql -c "CREATE USER slcuser WITH PASSWORD 'strongpassword';"
sudo -u postgres psql -c "CREATE DATABASE slcdb OWNER slcuser;"

# Set DATABASE_URL in .env
# DATABASE_URL=postgresql://slcuser:strongpassword@localhost/slcdb

python manage.py init-db
python manage.py create-admin
```

### 4. Gunicorn Setup

```bash
# Test Gunicorn manually first
gunicorn --bind 127.0.0.1:5000 "app:create_app()" --workers 3
```

**Create systemd service file:**

```bash
sudo nano /etc/systemd/system/slc.service
```

```ini
[Unit]
Description=Shroud's Lockin Crib — Flask Application
After=network.target

[Service]
User=slc
Group=www-data
WorkingDirectory=/home/slc/SLC-project
Environment="PATH=/home/slc/SLC-project/venv/bin"
ExecStart=/home/slc/SLC-project/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 3 \
    --timeout 60 \
    --log-level info \
    --access-logfile /var/log/slc/access.log \
    --error-logfile /var/log/slc/error.log \
    "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/slc
sudo chown slc:www-data /var/log/slc

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable slc
sudo systemctl start slc
sudo systemctl status slc  # Should show "active (running)"
```

### 5. NGINX Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/slc
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Certificates (managed by Certbot)
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Upload size limit (matches MAX_CONTENT_LENGTH)
    client_max_body_size 5M;

    # Security headers (complement Flask's headers)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to Gunicorn
    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Serve static files directly via NGINX (faster than through Flask)
    location /static/ {
        alias /home/slc/SLC-project/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Block uploads directory from direct access
    location /uploads/ {
        deny all;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/slc /etc/nginx/sites-enabled/
sudo nginx -t  # Test config
sudo systemctl restart nginx
```

### 6. HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
```

### 7. Uploads Directory Permissions

```bash
# Uploads must be writable by the slc service user
sudo chown -R slc:www-data /home/slc/SLC-project/uploads/
sudo chmod 750 /home/slc/SLC-project/uploads/
```

---

## Option B: Cloud Deployment (Render.com)

1. Push your repo to GitHub (`github.com/shroud2045/SLC-project`)
2. Go to [render.com](https://render.com) → New Web Service → Connect GitHub repo
3. Set the following in Render's dashboard:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`
   - **Environment variables:** Add all `.env` values in the Render "Environment" tab
4. Add a **Render PostgreSQL** database and set `DATABASE_URL` to the connection string
5. Run `python manage.py init-db` once via Render's shell tab

---

## Production Environment Variables Checklist

```bash
SECRET_KEY=<64-char-random-hex>      # REQUIRED — must be unique and secret
DATABASE_URL=postgresql://...         # REQUIRED — use PostgreSQL in prod
FLASK_ENV=production
FLASK_DEBUG=0
MAX_CONTENT_LENGTH=5242880            # 5 MB
UPLOAD_FOLDER=/home/slc/SLC-project/uploads
OPENAI_API_KEY=sk-...                 # Optional — for AI study plans
GEMINI_API_KEY=...                    # Optional — for AI study plans
```

---

## Updating the Application

```bash
# As the slc user
cd ~/SLC-project
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Apply any new database migrations
flask db upgrade  # if using Flask-Migrate

# Restart the service
sudo systemctl restart slc
```

---

## Monitoring Logs

```bash
# Gunicorn error logs
sudo tail -f /var/log/slc/error.log

# Access logs
sudo tail -f /var/log/slc/access.log

# systemd journal
sudo journalctl -u slc -f
```
