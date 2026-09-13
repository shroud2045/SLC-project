#!/usr/bin/env python3
"""
Management script for Shroud's Lockin Crib (SLC).

When used as --app with the Flask CLI, all commands below are available:

    flask --app manage.py db init               # Initialize migrations folder (once)
    flask --app manage.py db migrate -m "msg"   # Generate new migration
    flask --app manage.py db upgrade            # Apply pending migrations
    flask --app manage.py db-check              # Check database connectivity
    flask --app manage.py seed                  # Idempotent static data seed
    flask --app manage.py init-db               # Migrate + seed (first deploy)
    flask --app manage.py create-admin          # Create an admin account
    flask --app manage.py seed-badges           # Alias: seed badges only
"""
import os
import sys
import getpass
import click
from flask.cli import with_appcontext
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditAction
from app.services.auth_service import AuthService
from app.services.badge_service import BadgeService
from app.services.moderation_service import ModerationService
from app.services.audit_service import AuditService


# Flask discovers the app through this name when using --app manage.py
app = create_app(os.environ.get('FLASK_ENV', 'development'))


# ---------------------------------------------------------------------------
# db-check — safe database health probe (no credentials printed)
# ---------------------------------------------------------------------------

@app.cli.command('db-check')
@with_appcontext
def db_check_command():
    """
    Safely checks whether the configured database is reachable.

    Reports dialect and host without ever printing passwords or connection
    strings. Exit code 0 = healthy, 1 = unreachable.
    """
    from sqlalchemy import text
    url = db.engine.url
    dialect = url.get_dialect().name
    host = getattr(url, 'host', None) or '(local / in-memory)'
    database = getattr(url, 'database', None) or '(unknown)'

    click.echo("=== SLC Database Health Check ===")
    click.echo(f"  Dialect  : {dialect}")
    click.echo(f"  Host     : {host}")
    click.echo(f"  Database : {database}")

    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        click.secho("  Status   : CONNECTED ✓", fg='green')
        sys.exit(0)
    except Exception as exc:
        click.secho("  Status   : UNREACHABLE ✗", fg='red')
        click.echo(f"  Error    : {type(exc).__name__}: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# seed — idempotent static data seeding
# ---------------------------------------------------------------------------

@app.cli.command('seed')
@with_appcontext
def seed_command():
    """
    Seeds default achievement badges and moderation filter rules.

    Safe to run multiple times — existing records are never duplicated.
    Does NOT drop or wipe any tables.
    """
    badges_count = BadgeService.seed_badges()
    filters_count = ModerationService.seed_default_filters()
    click.secho(f"  Seeded {badges_count} achievement badges.", fg='green')
    click.secho(f"  Seeded {filters_count} moderation filter rules.", fg='green')
    click.echo("  Seed complete.")


# ---------------------------------------------------------------------------
# init-db — first-deploy helper: migrate + seed
# ---------------------------------------------------------------------------

@app.cli.command('init-db')
@with_appcontext
def init_db_command():
    """
    First-deploy initialiser: runs pending Alembic migrations then seeds
    static data (badges, filter rules).

    NEVER drops tables.  Safe to run on a fresh or existing database.
    """
    from flask_migrate import upgrade as migrate_upgrade
    click.echo("  Applying database migrations…")
    try:
        migrate_upgrade()
        click.secho("  Migrations applied successfully.", fg='green')
    except Exception as exc:
        click.secho(f"  Migration failed: {exc}", fg='red')
        click.echo(
            "  Hint: Run 'flask --app manage.py db init' and "
            "'flask --app manage.py db migrate' first if this is a fresh setup."
        )
        sys.exit(1)

    badges_count = BadgeService.seed_badges()
    filters_count = ModerationService.seed_default_filters()
    click.secho(f"  Seeded {badges_count} achievement badges.", fg='green')
    click.secho(f"  Seeded {filters_count} moderation filter rules.", fg='green')
    click.secho("  Database initialised successfully.", fg='green')


# ---------------------------------------------------------------------------
# create-admin — interactive admin account bootstrap
# ---------------------------------------------------------------------------

@app.cli.command('create-admin')
@with_appcontext
def create_admin_command():
    """Securely creates an initial administrator account with interactive prompts."""
    click.echo("\n" + "=" * 50)
    click.echo(" SHROUD'S LOCKIN CRIB - INITIAL ADMIN SETUP")
    click.echo("=" * 50)

    username = input("Enter Admin Username: ").strip()
    is_valid_u, u_err = AuthService.validate_username(username)
    if not is_valid_u:
        click.secho(f" Error: {u_err}", fg='red')
        sys.exit(1)

    if User.query.filter_by(username=username).first():
        click.secho(f" Error: Username '{username}' is already taken.", fg='red')
        sys.exit(1)

    email = input("Enter Admin Email: ").strip().lower()
    if User.query.filter_by(email=email).first():
        click.secho(f" Error: Email '{email}' is already registered.", fg='red')
        sys.exit(1)

    password = getpass.getpass("Enter Admin Password (min 8 chars, A-Z, a-z, 0-9, symbol): ")
    password_confirm = getpass.getpass("Confirm Admin Password: ")

    if password != password_confirm:
        click.secho(" Error: Passwords do not match.", fg='red')
        sys.exit(1)

    is_valid_p, p_err = AuthService.validate_password_strength(password)
    if not is_valid_p:
        click.secho(f" Error: {p_err}", fg='red')
        sys.exit(1)

    # Create administrator account
    admin_user = User(
        username=username,
        email=email,
        role=Role.ADMIN,
        is_active=True
    )
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()

    AuditService.log_action(
        admin_id=admin_user.id,
        action=AuditAction.ADMIN_LOGIN,
        target_type='SYSTEM',
        target_id=str(admin_user.id),
        details=f"Initial administrator account '{username}' created."
    )

    click.secho(f" Administrator '{username}' ({email}) created successfully!", fg='green')
    click.echo("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# seed-badges — legacy alias kept for backwards compatibility
# ---------------------------------------------------------------------------

@app.cli.command('seed-badges')
@with_appcontext
def seed_badges_command():
    """Seeds default achievement badges (idempotent). Alias for 'seed'."""
    count = BadgeService.seed_badges()
    click.secho(f" Seeded {count} badges.", fg='green')


if __name__ == '__main__':
    app.run()
