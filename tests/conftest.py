import pytest
import os
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.post import LockInPost, PostPrivacy
from app.services.badge_service import BadgeService
from app.services.moderation_service import ModerationService


@pytest.fixture
def app():
    """Create application configured for testing."""
    test_app = create_app('testing')

    with test_app.app_context():
        db.create_all()
        BadgeService.seed_badges()
        ModerationService.seed_default_filters()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def regular_user(app):
    """Creates a regular test user."""
    user = User(
        username="lockin_user",
        email="user@lockin.com",
        role=Role.USER,
        is_active=True
    )
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_user(app):
    """Creates a second regular test user for IDOR testing."""
    user = User(
        username="other_warrior",
        email="other@lockin.com",
        role=Role.USER,
        is_active=True
    )
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    """Creates an administrator test user."""
    admin = User(
        username="shroud_admin",
        email="admin@lockin.com",
        role=Role.ADMIN,
        is_active=True
    )
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def mod_user(app):
    """Creates a moderator test user."""
    mod = User(
        username="crib_moderator",
        email="mod@lockin.com",
        role=Role.MODERATOR,
        is_active=True
    )
    mod.set_password("ModPass123!")
    db.session.add(mod)
    db.session.commit()
    return mod


@pytest.fixture
def auth_client(client, regular_user):
    """Client authenticated as regular_user."""
    with client.session_transaction() as sess:
        sess['user_id'] = regular_user.id
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Client authenticated as admin_user."""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
    return client
