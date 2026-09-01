# Architecture Walkthrough — Shroud's Lockin Crib

This document is written for beginners learning Python and web development. It explains **how every part of the application works**, why it was built that way, and what the code does at each layer.

---

## High-Level Architecture

```
Browser (User)
      │
      ▼ HTTP Request
  ┌─────────────────────────────────────────────────────┐
  │               NGINX (Reverse Proxy)                 │
  │   - Serves /static files directly (CSS, JS, images) │
  │   - Forwards all other requests to Gunicorn         │
  └─────────────────────────────────────────────────────┘
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │           Gunicorn (WSGI Server)                    │
  │   - Runs 3 Flask worker processes                   │
  └─────────────────────────────────────────────────────┘
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │               Flask Application                     │
  │                                                     │
  │  Routes (Blueprints) → Services → Models (SQLAlchemy│
  │                              ↓                      │
  │                       SQLite / PostgreSQL           │
  └─────────────────────────────────────────────────────┘
```

**The flow for every request:**
1. Browser sends HTTP request
2. NGINX receives it — serves static files directly, or forwards to Flask
3. Flask matches the URL to a route function (in `app/routes/`)
4. The route calls service functions (in `app/services/`) for business logic
5. Services interact with database **models** (in `app/models/`) via SQLAlchemy
6. The route returns an HTML response rendered from a Jinja2 template

---

## Directory Layout Explained

```
SLC-project/
│
├── app/                     ← Main Python package (the application)
│   ├── __init__.py          ← Application factory — creates and configures Flask
│   ├── config.py            ← Configuration classes (Dev, Test, Production)
│   ├── extensions.py        ← Initialised Flask extensions (db, migrate, csrf)
│   │
│   ├── models/              ← Database table definitions
│   ├── services/            ← Business logic (HOW things work)
│   ├── routes/              ← URL endpoints (WHERE requests go)
│   ├── utils/               ← Helpers and decorators
│   ├── templates/           ← HTML files (Jinja2)
│   └── static/              ← CSS, JavaScript, images
│
├── tests/                   ← Automated test suite
├── manage.py                ← CLI commands (init-db, create-admin)
├── run.py                   ← Runs the dev server
└── requirements.txt         ← Python packages needed
```

---

## Layer 1: Application Factory (`app/__init__.py`)

```python
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # ...
    db.init_app(app)
    csrf.init_app(app)
    # ...register blueprints...
    return app
```

**Why a factory?** Instead of creating a global `app = Flask(__name__)` at the top of a file, we wrap it in a function. This lets us create multiple different app instances — one for development, one for testing with a separate in-memory database. This is the standard Flask pattern for larger apps.

---

## Layer 2: Configuration (`app/config.py`)

```python
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////path/to/slc.sqlite3'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Erased after tests!

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
```

**Key idea:** Configuration is **environment-specific**. You never want debug mode on in production. Secrets like `SECRET_KEY` are read from environment variables (`.env` file), never hardcoded.

---

## Layer 3: Database Models (`app/models/`)

Models define your database tables using Python classes. SQLAlchemy converts them to SQL automatically.

```python
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    # ...
```

**Why not store passwords directly?** If your database is ever stolen, attackers would get everyone's passwords. Instead we store a `password_hash` — a scrambled version that's mathematically impossible to reverse. When a user logs in, we hash what they typed and compare to the stored hash.

### Relationships

```python
class LockInPost(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', back_populates='posts')
```

This creates a foreign key link: every post belongs to one user. SQLAlchemy then lets you do `post.author.username` instead of writing SQL JOIN queries manually.

### Object-Level Authorization

```python
def can_view(self, user) -> bool:
    if self.privacy == PostPrivacy.COMMUNITY:
        return True      # Public post — anyone can see it
    if not user:
        return False     # Not logged in — private posts denied
    if user.id == self.user_id:
        return True      # Your own post — always allowed
    if user.is_admin() or user.is_moderator():
        return True      # Admins/mods can see everything
    return False         # Someone else's private post — denied
```

This method is called on **every single request** that tries to view a post. It doesn't matter if the button is hidden in the UI — if an attacker manually constructs a URL to `/posts/42`, the route still calls `post.can_view(user)` and returns HTTP 403 if they're not allowed.

---

## Layer 4: Services (`app/services/`)

Services contain all the real business logic. Routes are kept thin — they just validate input, call a service, and render a template.

### AuthService
```python
AuthService.register_user(username, email, password)
AuthService.authenticate_user(identifier, password)
AuthService.validate_password_strength(password)
```

- `validate_password_strength()` checks length, uppercase, lowercase, numbers, and symbols before accepting a password
- `authenticate_user()` calls `db.session.expire_all()` before querying — this forces SQLAlchemy to fetch a **fresh** copy of the user from the database, so a suspended user cannot authenticate even if cached in memory

### StreakService
```python
StreakService.calculate_streaks(user_id, reference_date=today)
```

Returns: `{ current_streak, longest_streak, total_hours, is_active_today, today_hours }`

**How streaks work:**
1. Fetch all unique post dates for the user, sorted newest first
2. Walk backwards from today — count consecutive days where a post exists
3. If a gap of more than 1 day is found, stop counting
4. Track the longest consecutive run found in history

This is 100% deterministic — computed from actual post dates in the database. It cannot be faked.

### BadgeService
```python
BadgeService.seed_badges()          # Creates the 23 default badges in DB
BadgeService.evaluate_user_badges(user_id)  # Checks thresholds, awards new badges
```

**How badge evaluation works:**
1. Get the user's stats (streak, total hours, total days)
2. Load all badges from DB
3. For each badge the user has NOT already earned:
   - Check if `stats[badge.requirement_type] >= badge.threshold`
   - If yes → create a `UserBadge` record and return it
4. AI cannot call this function — badges are only awarded by the server evaluating real data

### UploadService
```python
UploadService.validate_and_save_image(file_storage, user_id)
```

Five-stage pipeline:
1. **Extension check** — `.php`, `.exe`, etc. are immediately rejected
2. **Magic bytes** — reads the first few bytes of the file and compares to known image signatures
3. **Pillow verification** — tries to open the image; malformed files are rejected
4. **EXIF stripping** — re-opens the raw pixel data without metadata, discarding GPS, device info
5. **WebP re-encode** — saves as `<uuid>.webp` — original filename never touches disk

### ModerationService
```python
is_allowed, cleaned_text, reason = ModerationService.check_content(text)
```

- Loads `BannedWord` rules from the database
- Each rule can be a plain keyword or a regex pattern
- Severity: `BLOCK` (reject), `FLAG` (log for review), `WARN` (replace with `***`)
- Called on every post creation, comment, and chat message

---

## Layer 5: Routes / Blueprints (`app/routes/`)

Blueprints are groups of related URL endpoints. Each blueprint gets a URL prefix:

| Blueprint | Prefix | Purpose |
|---|---|---|
| `auth_bp` | `/auth` | Register, login, logout |
| `dashboard_bp` | `/dashboard` | Personal dashboard |
| `posts_bp` | `/posts` | Create, view, edit, delete posts |
| `timer_bp` | `/timer` | Focus timer + session saving |
| `badges_bp` | `/badges` | Badge showcase |
| `challenges_bp` | `/challenges` | Community challenges |
| `community_bp` | `/community` | Public feed, reactions, comments |
| `chat_bp` | `/chat` | Live chatroom |
| `profile_bp` | `/profile` | Public/private user profiles |
| `ai_bp` | `/ai` | AI productivity assistant |
| `admin_bp` | `/admin` | Admin control panel |
| `uploads_bp` | `/uploads` | Secure file serving |

**Example route:**
```python
@posts_bp.route('/<int:post_id>')
def view_post(post_id: int):
    post = db.get_or_404(LockInPost, post_id)  # 404 if not found
    current_user = get_current_user()           # From session

    if not post.can_view(current_user):         # Object-level auth
        abort(403)                              # 403 Forbidden

    return render_template('posts/view.html', post=post, current_user=current_user)
```

---

## Layer 6: Utilities (`app/utils/`)

### Decorators (`decorators.py`)

```python
@login_required        # Redirects to login if no session
@role_required(['ADMIN', 'MODERATOR'])  # Returns 403 if wrong role
@rate_limit(limit=5, window=60)         # Blocks after 5 requests/minute
```

Decorators are Python functions that **wrap** other functions to add behaviour. The `@` symbol means "apply this wrapper to the function below it."

```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Please log in.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
```

### Security Headers (`security.py`)

```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "default-src 'self'; ..."
    return response
```

This function runs **after every single response**. It adds HTTP headers that tell browsers to behave more securely:
- `nosniff` — don't try to guess the file type; trust what the server says
- `SAMEORIGIN` — don't allow this page to be embedded in an iframe on another domain (prevents clickjacking)
- CSP — only load scripts/styles from our own domain

---

## Layer 7: Templates (`app/templates/`)

Jinja2 templates are HTML files with special `{{ }}` and `{% %}` syntax for dynamic content.

```html
{% extends "base.html" %}    <!-- Inherit the base layout -->
{% block content %}
  <h1>Hello, {{ current_user.username }}</h1>   <!-- Auto-escaped! -->
  {% for post in posts %}
    <a href="{{ url_for('posts.view_post', post_id=post.id) }}">{{ post.title }}</a>
  {% endfor %}
{% endblock %}
```

**Key Jinja2 safety rule:** `{{ var }}` is always HTML-escaped by default. If `var` contains `<script>alert(1)</script>`, it renders as `&lt;script&gt;alert(1)&lt;/script&gt;` — displayed as text, not executed. This is why XSS is prevented at the template level.

---

## Data Flow: Creating a Lock-In Post

Here's the full journey of a POST request to create a daily log:

```
1. User fills out form on /posts/create and clicks "Submit"

2. Browser sends:
   POST /posts/create
   Form data: { title, description, hours_worked, privacy, post_date, csrf_token }

3. Flask route (posts.py → create_post()):
   a. get_current_user() — loads user from session
   b. CSRF token validated by Flask-WTF
   c. Input sanitised (strip whitespace, validate hours 0-24)
   d. ModerationService.check_content(title + description) called
      - If BLOCK → flash error, re-render form
   e. LockInPost() object created and added to database
   f. BadgeService.evaluate_user_badges(user.id) called
      - New badges are awarded and stored in UserBadge
   g. Redirect to /dashboard

4. Browser follows redirect to /dashboard

5. Dashboard route calls StreakService.calculate_streaks(user.id)
   - Returns updated streak count
   - Streak is now 1 day higher because today has a post

6. Dashboard renders with new streak number and any newly unlocked badges
```

---

## The Focus Timer

The timer lives entirely in the browser (`static/js/timer.js`), but the **session is validated server-side** before being saved:

```python
# Timer save endpoint (routes/timer.py)
def save_session():
    data = request.get_json()
    start_time = parse_datetime(data['start_time'])
    end_time = parse_datetime(data['end_time'])
    claimed_seconds = int(data['duration_seconds'])

    # Anti-tamper check 1: claimed duration vs actual time window
    actual_seconds = (end_time - start_time).total_seconds()
    if abs(claimed_seconds - actual_seconds) > 60:  # 1 minute tolerance
        return jsonify({'error': 'Duration exceeds actual elapsed time'}), 400

    # Anti-tamper check 2: future timestamps
    if start_time > datetime.now(timezone.utc):
        return jsonify({'error': 'start_time is in the future'}), 400

    # Anti-tamper check 3: sessions too short to count
    if claimed_seconds < 60:
        return jsonify({'error': 'Session too short'}), 400
```

Even if a user modifies the JavaScript or sends a crafted API request claiming "I did 5 hours in 10 seconds", the server rejects it with HTTP 400.

---

## The Chat System

The chat uses **long-polling** (not WebSockets) for simplicity:

1. Browser loads `/chat/` — sees the last 50 messages
2. JavaScript sends `GET /chat/api/messages?after_id=<last_id>` every 3 seconds
3. If new messages exist, they're returned and added to the UI
4. To send a message, browser sends `POST /chat/api/send` with JSON body
5. Server checks: Is the user muted? Does the content pass moderation?
6. If all checks pass, message is saved to DB — next poll by all clients picks it up

---

## CLI Commands (`manage.py`)

```bash
python manage.py init-db       # Creates tables + seeds data
python manage.py create-admin  # Interactive admin creation
python manage.py seed-badges   # Re-seeds badge catalog
```

**Why not hardcode an admin?** If `ADMIN_PASSWORD=MyPassword123` was in the code, it would be in Git history forever. Using an interactive CLI command means the password is never stored anywhere except the database hash.

---

## Testing Strategy

29 automated tests across 10 modules, run with `pytest`:

| Module | What it tests |
|---|---|
| `test_auth.py` | Password policy, registration privilege escalation prevention, login, logout, suspended user |
| `test_posts_privacy.py` | IDOR protection — other users cannot view/edit/delete private posts |
| `test_timer.py` | Valid session save, spoofed duration rejection, future timestamp rejection |
| `test_streaks.py` | Consecutive day count, gap detection, longest streak preservation |
| `test_badges.py` | Badge unlock on first log, hours milestone, no duplicates |
| `test_community_chat.py` | Comments, reactions toggle, chat send/poll, muted user blocked |
| `test_moderation.py` | Content filter service, post with blocked language rejected |
| `test_admin_rbac.py` | Regular user blocked from admin routes, admin actions + audit logging |
| `test_security_owasp.py` | SQLi payloads don't crash app, XSS is escaped, security headers present |
| `test_uploads.py` | Valid image accepted, invalid extension rejected, fake magic bytes rejected |

Each test uses a **fresh in-memory SQLite database** created in `conftest.py`. Tests never affect each other or your real data.
