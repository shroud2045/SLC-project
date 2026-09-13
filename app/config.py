import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))

# Ensure instance and uploads directories exist
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(os.path.join(basedir, 'uploads'), exist_ok=True)


def _resolve_db_url(raw, allow_sqlite=False):
    """
    Resolve the database URL, rewriting Render's legacy postgres:// scheme
    to the SQLAlchemy-compatible postgresql:// scheme.

    Args:
        raw: Raw DATABASE_URL string (may be None or empty).
        allow_sqlite: If True, a missing/empty URL falls back to local SQLite.
                      If False (production), a missing or SQLite URL raises ValueError
                      at the time the config is *used*, not at import time.
    """
    if not raw:
        if allow_sqlite:
            return "sqlite:///" + os.path.join(basedir, 'instance', 'slc.sqlite3')
        raise ValueError(
            "DATABASE_URL is not set. "
            "Production requires a PostgreSQL DATABASE_URL environment variable."
        )

    # Render historically provides postgres:// — SQLAlchemy requires postgresql://
    if raw.startswith('postgres://'):
        raw = raw.replace('postgres://', 'postgresql://', 1)

    if not allow_sqlite and raw.startswith('sqlite://'):
        raise ValueError(
            "DATABASE_URL is set to a SQLite path. "
            "Production must use a PostgreSQL DATABASE_URL. "
            "Set DATABASE_URL to your Render PostgreSQL connection string."
        )

    return raw


class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-fallback-dev-secret-key-do-not-use-in-prod'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload configurations
    UPLOAD_FOLDER = os.path.join(basedir, os.environ.get('UPLOAD_FOLDER', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB max
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,webp,gif').split(','))

    # Session & Cookie Security
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', 7)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')

    # Rate Limiting Settings
    RATE_LIMIT_LOGIN = os.environ.get('RATE_LIMIT_LOGIN', '5/minute')
    RATE_LIMIT_REGISTER = os.environ.get('RATE_LIMIT_REGISTER', '3/minute')
    RATE_LIMIT_CHAT = os.environ.get('RATE_LIMIT_CHAT', '1/second')
    RATE_LIMIT_AI = os.environ.get('RATE_LIMIT_AI', '10/minute')

    # AI Assistant Configuration
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'heuristic')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

    # Application Metadata
    APP_NAME = "Shroud's Lockin Crib"
    APP_TAGLINE = "Lock In. Build Your Streak. Dominate Your Goals."


class DevelopmentConfig(Config):
    """Development configuration — SQLite is the local default."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    # Fall back to local SQLite when DATABASE_URL is absent in development
    SQLALCHEMY_DATABASE_URI = _resolve_db_url(os.environ.get('DATABASE_URL'), allow_sqlite=True)


class TestingConfig(Config):
    """Testing configuration with in-memory SQLite for fast isolated unit tests."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Disable CSRF for simplified automated unit testing
    SESSION_COOKIE_SECURE = False
    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'test_uploads')


class ProductionConfig(Config):
    """
    Production configuration — PostgreSQL is mandatory.

    SQLALCHEMY_DATABASE_URI is intentionally NOT set as a class attribute here.
    It is resolved lazily at app-creation time inside create_app() so that:
      - Python can safely import this module in any environment
      - The validation only fires when production config is actually *used*
      - Development/testing imports never trigger the PostgreSQL requirement
    """
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Enforce HTTPS cookies in production

    @classmethod
    def get_sqlalchemy_uri(cls):
        """Return the validated production database URI."""
        return _resolve_db_url(os.environ.get('DATABASE_URL'), allow_sqlite=False)


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
