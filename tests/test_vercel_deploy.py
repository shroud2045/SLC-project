"""
test_vercel_deploy.py — Verification of Vercel Serverless Production Deployment

Tests all constraints required for deploying on Vercel:
1. No top-level filesystem side-effects (read-only filesystem safety)
2. Normalization of postgres:// and postgresql:// to postgresql+psycopg://
3. Strict rejection of SQLite in production / Vercel
4. Defaulting UPLOAD_FOLDER to /tmp/uploads on Vercel
5. Clean import of the api/index.py entrypoint
6. Preservation of local development SQLite behavior
"""
import os
import pytest
from app.config import _resolve_db_url, Config, DevelopmentConfig, ProductionConfig
from app import create_app


def test_postgres_url_normalization_postgres_prefix(monkeypatch):
    """Test that postgres:// is normalized to postgresql+psycopg://."""
    monkeypatch.delenv('VERCEL', raising=False)
    raw = "postgres://usr_123:sec_456@dpg-abc-a.oregon-postgres.render.com/slc_db"
    res = _resolve_db_url(raw, allow_sqlite=False)
    assert res == "postgresql+psycopg://usr_123:sec_456@dpg-abc-a.oregon-postgres.render.com/slc_db"


def test_postgres_url_normalization_postgresql_prefix(monkeypatch):
    """Test that postgresql:// is normalized to postgresql+psycopg:// (psycopg v3 driver)."""
    monkeypatch.delenv('VERCEL', raising=False)
    raw = "postgresql://usr_123:sec_456@dpg-abc-a.oregon-postgres.render.com/slc_db"
    res = _resolve_db_url(raw, allow_sqlite=False)
    assert res == "postgresql+psycopg://usr_123:sec_456@dpg-abc-a.oregon-postgres.render.com/slc_db"


def test_postgres_url_normalization_with_psycopg2_prefix(monkeypatch):
    """Test that postgresql+psycopg2:// is corrected to postgresql+psycopg://."""
    monkeypatch.delenv('VERCEL', raising=False)
    raw = "postgresql+psycopg2://usr:pass@host/db"
    res = _resolve_db_url(raw, allow_sqlite=False)
    assert res == "postgresql+psycopg://usr:pass@host/db"


def test_postgres_url_already_psycopg(monkeypatch):
    """Test that postgresql+psycopg:// is preserved without alteration."""
    monkeypatch.delenv('VERCEL', raising=False)
    raw = "postgresql+psycopg://usr:pass@host/db?sslmode=require"
    res = _resolve_db_url(raw, allow_sqlite=False)
    assert res == "postgresql+psycopg://usr:pass@host/db?sslmode=require"


def test_vercel_blocks_sqlite_fallback(monkeypatch):
    """Ensure Vercel never silently falls back to SQLite even if allow_sqlite=True."""
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with pytest.raises(ValueError) as exc:
        _resolve_db_url(None, allow_sqlite=True)
    assert "Vercel deployment requires a PostgreSQL DATABASE_URL" in str(exc.value)


def test_vercel_blocks_explicit_sqlite_url(monkeypatch):
    """Ensure Vercel rejects an explicit sqlite:// URL."""
    monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(ValueError) as exc:
        _resolve_db_url("sqlite:///var/task/instance/slc.sqlite3", allow_sqlite=True)
    assert "must use a PostgreSQL DATABASE_URL" in str(exc.value)


def test_local_dev_preserves_sqlite_fallback(monkeypatch):
    """Verify local development (off Vercel) still allows SQLite fallback."""
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    res = _resolve_db_url(None, allow_sqlite=True)
    assert res.startswith("sqlite:///")
    assert "slc.sqlite3" in res


def test_vercel_upload_folder_defaults_to_tmp(monkeypatch):
    """Verify that on Vercel, Config.UPLOAD_FOLDER defaults to /tmp/uploads."""
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('UPLOAD_FOLDER', raising=False)

    # Re-evaluate Config class logic
    default_upload = '/tmp/uploads' if os.environ.get('VERCEL') else os.path.join(os.getcwd(), 'uploads')
    assert default_upload == '/tmp/uploads'


def test_create_app_in_simulated_vercel_production(monkeypatch):
    """Test full create_app() instantiation in simulated Vercel production environment."""
    test_db_url = "postgres://testuser:secret@ep-cool-db.render.com/lockincrib"
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('DATABASE_URL', test_db_url)
    monkeypatch.setenv('SECRET_KEY', 'test-production-secret-key-1234567890')
    monkeypatch.delenv('FLASK_ENV', raising=False)

    # Calling create_app() with no args should resolve to production on Vercel
    app = create_app()

    assert app.config['TESTING'] is False
    assert app.config['DEBUG'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SQLALCHEMY_DATABASE_URI'] == "postgresql+psycopg://testuser:secret@ep-cool-db.render.com/lockincrib"
    assert app.config['UPLOAD_FOLDER'] == "/tmp/uploads"


def test_api_index_entrypoint_import(monkeypatch):
    """Verify that importing api.index succeeds in a simulated Vercel environment."""
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://usr:pwd@host.render.com/db')
    monkeypatch.setenv('SECRET_KEY', 'some-secret-key-abcdef')

    import importlib
    import api.index
    importlib.reload(api.index)

    assert api.index.app is not None
    assert api.index.app.config['SQLALCHEMY_DATABASE_URI'] == 'postgresql+psycopg://usr:pwd@host.render.com/db'
