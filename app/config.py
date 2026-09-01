import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))

# Ensure instance and uploads directories exist
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(os.path.join(basedir, 'uploads'), exist_ok=True)


class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-fallback-dev-secret-key-do-not-use-in-prod'
    
    # SQLAlchemy configuration
    raw_db_url = os.environ.get('DATABASE_URL')
    if not raw_db_url or raw_db_url.startswith('sqlite:///instance'):
        db_url = f"sqlite:///{os.path.join(basedir, 'instance', 'slc.sqlite3')}"
    elif raw_db_url.startswith('postgres://'):
        db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
    else:
        db_url = raw_db_url

    SQLALCHEMY_DATABASE_URI = db_url
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
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing configuration with in-memory / fast test database."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Disable CSRF for simplified automated unit testing
    SESSION_COOKIE_SECURE = False
    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'test_uploads')


class ProductionConfig(Config):
    """Production configuration with strict security defaults."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Enforce HTTPS cookies in production


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
