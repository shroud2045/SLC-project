#!/usr/bin/env python3
import os
import sys
import getpass
import click
from flask.cli import FlaskGroup
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditAction
from app.services.auth_service import AuthService
from app.services.badge_service import BadgeService
from app.services.moderation_service import ModerationService
from app.services.audit_service import AuditService


def create_cli_app():
    return create_app(os.environ.get('FLASK_ENV', 'development'))


@click.group(cls=FlaskGroup, create_app=create_cli_app)
def cli():
    """Management script for Shroud's Lockin Crib (SLC)."""
    pass


@cli.command('init-db')
def init_db_command():
    """Initializes database schema and seeds default badges and filter rules."""
    app = create_cli_app()
    with app.app_context():
        db.create_all()
        badges_count = BadgeService.seed_badges()
        filters_count = ModerationService.seed_default_filters()
        click.echo(" Database initialized successfully.")
        click.echo(f" Seeded {badges_count} achievement badges.")
        click.echo(f" Seeded {filters_count} moderation filter rules.")


@cli.command('create-admin')
def create_admin_command():
    """Securely creates an initial administrator account with interactive prompts."""
    app = create_cli_app()
    with app.app_context():
        db.create_all()
        click.echo("\n" + "="*50)
        click.echo(" SHROUD'S LOCKIN CRIB - INITIAL ADMIN SETUP")
        click.echo("="*50)

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
        click.echo("="*50 + "\n")


@cli.command('seed-badges')
def seed_badges_command():
    """Seeds default achievement badges."""
    app = create_cli_app()
    with app.app_context():
        count = BadgeService.seed_badges()
        click.secho(f" Seeded {count} badges.", fg='green')


if __name__ == '__main__':
    cli()
